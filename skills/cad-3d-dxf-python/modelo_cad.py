# -*- coding: utf-8 -*-
"""Biblioteca minima: solidos build123d -> STEP/glTF/DXF 3D (malha) + DXF 2D de
fabricacao + checagem de interferencia + renders pelo SolidCraft (solidcraft-cli),
com matplotlib como reserva.

Extraido de um projeto real (gerador de uma serra-fita, 2026-10).
Copie para o projeto e ajuste. Unidades: mm. Requer: build123d>=0.13, ezdxf,
matplotlib, numpy.

Padrao de uso:
    PECAS = []
    peca('Q1', 'placa', 1, 'aco A36 12,7', 'laser', 'serralheiro',
         [chapa_xz(pts, 12.7, y0, furos)], perfil=pts, furos=furos, esp=12.7)
    ...
    print(interferencias(permitidos={frozenset(('E1', 'W1'))}))
    exporta_3d(BASE); exporta_2d(BASE); renders(BASE)
"""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import tempfile
import unicodedata
from dataclasses import dataclass, field

import ezdxf
from build123d import (Align, Axis, Box, Circle, Compound, Cylinder, Polygon, Pos,
                       Rot, export_step, export_gltf, extrude, revolve)
from build123d import Color, Plane


@dataclass
class Peca:
    codigo: str
    nome: str
    qtd: int
    material: str
    processo: str            # laser, serralheria, tornearia, marcenaria, compra...
    quem: str
    solidos: list            # instancias ja posicionadas no sistema da maquina
    cor: tuple = (0.7, 0.7, 0.7)
    perfil: list = None      # 2D (u, v) -> DXF de corte de chapa
    furos: list = field(default_factory=list)   # (u, v, diametro)
    esp: float = 0.0
    torno: list = None       # meio-perfil (r, s) -> desenho de torno
    notas: list = field(default_factory=list)
    dim: str = ''


PECAS: list[Peca] = []
ESPELHAR_X = False           # True se o modelo ficou do lado errado (ver SKILL.md)


def peca(*a, **k):
    p = Peca(*a, **k)
    if ESPELHAR_X:
        p.solidos = [s.mirror(Plane.YZ) for s in p.solidos]
    PECAS.append(p)
    return p


def face2d(pts, furos=()):
    f = Polygon(*pts, align=None)
    for u, v, d in furos:
        f = f - Pos(u, v) * Circle(d / 2)
    return f


def _ext(face, t):
    """Extrusao com posicao garantida em z 0..t. Face saida de booleana pode vir
    com a normal invertida e extrudar para -z; corrige pelo bounding box."""
    s = extrude(face, amount=t)
    return Pos(0, 0, -s.bounding_box().min.Z) * s


def chapa_xz(pts, t, y0, furos=()):
    """Perfil em (X, Z), espessura em Y de y0 a y0+t."""
    return Pos(0, y0 + t, 0) * (Rot(90, 0, 0) * _ext(face2d(pts, furos), t))


def chapa_xy(pts, t, z0, furos=()):
    """Perfil em (X, Y), espessura em Z de z0 a z0+t."""
    return Pos(0, 0, z0) * _ext(face2d(pts, furos), t)


def chapa_yz(pts, t, x0, furos=()):
    """Perfil em (Y, Z), espessura em X de x0 a x0+t."""
    s = _ext(face2d(pts, furos), t)                      # local x=Y, y=Z, z=X
    s = Rot(90, 0, 0) * s                                # -> X=Y, Z=Z, -Y=X
    s = Rot(0, 0, 90) * s                                # gira p/ x0..x0+t em X
    bb = s.bounding_box()
    return Pos(x0 - bb.min.X, 0, 0) * s


def caixa(x0, x1, y0, y1, z0, z1):
    return Pos(x0, y0, z0) * Box(x1 - x0, y1 - y0, z1 - z0, align=(Align.MIN,) * 3)


def tubo_ret(x0, x1, y0, y1, z0, z1, t, eixo):
    ext = caixa(x0, x1, y0, y1, z0, z1)
    if eixo == 'z':
        return ext - caixa(x0 + t, x1 - t, y0 + t, y1 - t, z0 - 1, z1 + 1)
    return ext - caixa(x0 - 1, x1 + 1, y0 + t, y1 - t, z0 + t, z1 - t)


def torneado_y(perfil, x=0.0, y0=0.0, z=0.0):
    """Meio-perfil (r, s) revolucionado em torno de Y; s=0 em y0."""
    pts = [(r, s) for r, s in perfil]
    s = revolve(Polygon(*pts, align=None), Axis.Y)
    return Pos(x, y0, z) * s


def cil_y(r, y0, y1, x, z, ri=0.0):
    c = Pos(x, y0, z) * (Rot(-90, 0, 0) * Cylinder(r, y1 - y0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    if ri:
        c = c - Pos(x, y0 - 1, z) * (Rot(-90, 0, 0) * Cylinder(ri, y1 - y0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return c


def cil_z(r, z0, z1, x, y, ri=0.0):
    c = Pos(x, y, z0) * Cylinder(r, z1 - z0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if ri:
        c = c - Pos(x, y, z0 - 1) * Cylinder(ri, z1 - z0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return c


def cil_x(r, x0, x1, y, z, ri=0.0):
    c = Pos(x0, y, z) * (Rot(0, 90, 0) * Cylinder(r, x1 - x0, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    if ri:
        c = c - Pos(x0 - 1, y, z) * (Rot(0, 90, 0) * Cylinder(ri, x1 - x0 + 2, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    return c


def ret(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def arco(cx, cy, r, a0, a1, n=24):
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]



def ascii_(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()


def malha_dxf(msp, solido, camada, tol=0.6):
    from ezdxf.render import MeshBuilder
    v, f = solido.tessellate(tol, 0.3)
    m = MeshBuilder()
    m.vertices = [(p.X, p.Y, p.Z) for p in v]
    m.faces = [tuple(t) for t in f]
    m.render_mesh(msp, dxfattribs={'layer': camada})


def doc_dxf():
    d = ezdxf.new('R2010', setup=True)
    d.units = ezdxf.units.MM
    d.header['$INSUNITS'] = 4
    d.header['$MEASUREMENT'] = 1
    return d


def cor_aci(rgb):
    return ezdxf.colors.rgb2int(tuple(int(255 * c) for c in rgb))


def exporta_3d(BASE, rotulo='montagem'):
    p3 = os.path.join(BASE, '3d', 'pecas')
    os.makedirs(p3, exist_ok=True)
    todos = []
    dm = doc_dxf()
    msp = dm.modelspace()
    for p in PECAS:
        cam = ascii_(p.codigo + ' ' + p.nome)[:60].replace('/', '-')
        lay = dm.layers.add(cam)
        lay.rgb = tuple(int(255 * c) for c in p.cor)
        # peca avulsa: primeira instancia
        s0 = p.solidos[0]
        s0.label = p.codigo
        export_step(s0, os.path.join(p3, p.codigo.lower() + '.step'))
        d1 = doc_dxf()
        malha_dxf(d1.modelspace(), s0, '0')
        d1.saveas(os.path.join(p3, p.codigo.lower() + '.dxf'))
        for i, s in enumerate(p.solidos):
            s.label = '%s-%d %s' % (p.codigo, i + 1, ascii_(p.nome))
            s.color = Color(*p.cor)
            todos.append(s)
            malha_dxf(msp, s, cam, tol=1.0)
    dm.saveas(os.path.join(BASE, '3d', 'montagem.dxf'))
    comp = Compound(label=rotulo, children=todos)
    export_step(comp, os.path.join(BASE, '3d', 'montagem.step'))
    try:
        export_gltf(comp, os.path.join(BASE, '3d', 'montagem.glb'), binary=True)
    except Exception as e:                       # visualizador web e opcional
        print('glb nao exportado:', e)
    return todos


def interferencias(permitidos=frozenset(), grupos_colados=()):
    """Pares de instancias com volume comum > 1 mm3. permitidos: frozensets de
    codigos que se tocam de proposito (eixo no cubo, pneu no aro...).
    grupos_colados: conjuntos de codigos que so encostam face com face (chapas
    coladas) - pular, porque a booleana de faces coplanares pode lancar erro."""
    inst = [(p.codigo, s) for p in PECAS for s in p.solidos]
    achados = []
    for i in range(len(inst)):
        ci, si = inst[i]
        bi = si.bounding_box()
        for j in range(i + 1, len(inst)):
            cj, sj = inst[j]
            if ci == cj or frozenset((ci, cj)) in permitidos:
                continue
            if any(ci in g and cj in g for g in grupos_colados):
                continue
            bj = sj.bounding_box()
            if (bi.max.X < bj.min.X or bj.max.X < bi.min.X or bi.max.Y < bj.min.Y or
                    bj.max.Y < bi.min.Y or bi.max.Z < bj.min.Z or bj.max.Z < bi.min.Z):
                continue
            try:
                comum = si & sj
                v = comum.volume if comum is not None else 0.0   # None = nada em comum
            except Exception:
                v = -1
            if v > 1.0 or v < 0:
                achados.append((ci, cj, v))
    return achados


def _tris(solidos_cores, tol=1.2, explode=None):
    import numpy as np
    tris, cores = [], []
    luz = np.array([0.45, 0.75, 0.6])
    luz = luz / np.linalg.norm(luz)
    for s, cor, desloc in solidos_cores:
        v, f = s.tessellate(tol, 0.4)
        V = np.array([(p.X, p.Y, p.Z) for p in v]) + np.array(desloc)
        for a, b, c in f:
            t = V[[a, b, c]]
            n = np.cross(t[1] - t[0], t[2] - t[0])
            nn = np.linalg.norm(n)
            k = 0.55 + 0.45 * abs(np.dot(n / nn, luz)) if nn > 0 else 0.8
            tris.append(t)
            cores.append(tuple(min(1, ch * k) for ch in cor))
    return tris, cores


SOLIDCRAFT = shutil.which('solidcraft-cli')


def render_solidcraft(itens, arq, elev, azim, px=1600, margem=15):
    """Render pelo SolidCraft (solidcraft-cli, sem janela): exporta os sólidos num
    STEP com cor, renderiza em vista ortográfica e recorta o branco em volta.
    itens: [(sólido, cor, deslocamento)]. Câmera no mesmo sentido do matplotlib
    (elev, azim). Devolve False se o SolidCraft não estiver instalado ou falhar."""
    if not SOLIDCRAFT:
        return False
    import numpy as np
    from PIL import Image
    filhos = []
    for i, (s, cor, d) in enumerate(itens):
        t = Pos(*d) * s if any(d) else s.moved(Pos(0, 0, 0))
        t.label, t.color = 'b%d' % i, Color(*cor)
        filhos.append(t)
    comp = Compound(children=filhos)
    bb = comp.bounding_box()
    c = ((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2)
    r = math.dist((bb.min.X, bb.min.Y, bb.min.Z), (bb.max.X, bb.max.Y, bb.max.Z)) / 2
    # SolidCraft: yaw 0 olha de -Y, yaw 90° de -X; matplotlib: azim 0 olha de +X
    cam = {'target': list(c), 'yaw': -math.radians(azim + 90), 'pitch': math.radians(elev),
           'distance': 2.2 * r / 0.83, 'fov': 0}
    with tempfile.TemporaryDirectory() as tmp:
        step, roteiro = os.path.join(tmp, 'm.step'), os.path.join(tmp, 'r.json')
        projeto, png = os.path.join(tmp, 'm.solidcraft'), os.path.join(tmp, 'm.png')
        export_step(comp, step)
        # o render rápido tem teto de trabalho (LimitExceeded) em montagens com muitas
        # peças: tenta de novo com imagem menor antes de desistir
        for lado in (px, int(px * 0.75), px // 2):
            with open(roteiro, 'w') as f:
                json.dump([{'command': 'render.settings.set', 'params': {'name': 'vista', 'set': {
                    'width': lado, 'height': lado, 'background': [255, 255, 255], 'camera': cam}}}], f)
            try:
                subprocess.run([SOLIDCRAFT, 'run', roteiro, '--in', step, '--save', projeto,
                                '--quiet'], check=True, capture_output=True, timeout=600)
                subprocess.run([SOLIDCRAFT, 'render', projeto, '--setup', 'vista', '--out', png,
                                '--overwrite'], check=True, capture_output=True, timeout=600)
                break
            except (subprocess.SubprocessError, OSError) as e:
                erro = (getattr(e, 'stderr', b'') or b'').decode(errors='replace').strip().splitlines()
                erro = erro[-1] if erro else str(e)
                if 'LimitExceeded' in erro and lado > px // 2:
                    continue
                print('SolidCraft falhou em %s (%s): render pelo matplotlib'
                      % (os.path.basename(arq), erro))
                return False
        im = np.asarray(Image.open(png).convert('RGB'))
    m = np.where(im.min(axis=2) < 250)
    if len(m[0]):
        y0, y1, x0, x1 = m[0].min(), m[0].max(), m[1].min(), m[1].max()
        im = im[max(0, y0 - margem):y1 + margem, max(0, x0 - margem):x1 + margem]
    Image.fromarray(im).save(arq)
    return True


def render(BASE, nome, elev, azim, explodida=False, ocultar=(), recorte=None, larg=7.0, alt=9.0):
    sc = []
    for p in PECAS:
        if p.codigo in ocultar:
            continue
        d = (0, 0, 0)
        if explodida:
            d = EXPLODE.get(p.codigo[0], (0, 0, 0))
            d = EXPLODE.get(p.codigo, d)
        sc += [(s, p.cor, d) for s in p.solidos]
    pasta = os.path.join(BASE, '3d', 'vistas')
    os.makedirs(pasta, exist_ok=True)
    if render_solidcraft(sc, os.path.join(pasta, nome + '.png'), elev, azim):
        return
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    itens = []
    for p in PECAS:
        if p.codigo in ocultar:
            continue
        d = (0, 0, 0)
        if explodida:
            d = EXPLODE.get(p.codigo[0], (0, 0, 0))
            d = EXPLODE.get(p.codigo, d)
        for s in p.solidos:
            itens.append((s, p.cor, d))
    tris, cores = _tris(itens)
    fig = plt.figure(figsize=(larg, alt))
    ax = fig.add_axes([0, 0, 1, 1], projection='3d')
    ax.add_collection3d(Poly3DCollection(tris, facecolors=cores, edgecolors='none',
                                         linewidths=0, zsort='average'))
    import numpy as np
    pts = np.concatenate(tris)
    lo, hi = pts.min(0), pts.max(0)
    c, r = (lo + hi) / 2, (hi - lo).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=elev, azim=azim)
    ax.set_proj_type('ortho')
    ax.axis('off')
    pasta = os.path.join(BASE, '3d', 'vistas')
    os.makedirs(pasta, exist_ok=True)
    arq = os.path.join(pasta, nome + '.png')
    fig.savefig(arq, dpi=150, facecolor='white', bbox_inches='tight', pad_inches=0.05)
    plt.close(fig)
    # eixos 3D sao quadrados: recorta o branco em volta da maquina
    im = plt.imread(arq)
    m = np.where(im[:, :, :3].min(axis=2) < 0.98)
    if len(m[0]):
        y0, y1, x0, x1 = m[0].min(), m[0].max(), m[1].min(), m[1].max()
        plt.imsave(arq, im[max(0, y0 - 15):y1 + 15, max(0, x0 - 15):x1 + 15])


EXPLODE = {}                 # {'Q': (0, -250, 0), 'E1': (0, 60, 0)} por prefixo ou codigo


def renders(BASE):
    # camera matplotlib: azim 90 = olhando de +Y; azim 0 = de +X
    render(BASE, 'frente', 0, 90)
    render(BASE, 'lateral', 0, 0)
    render(BASE, 'isometrica', 18, 55)
    render(BASE, 'explodida', 15, 55, explodida=True, larg=9, alt=10)


def _doc2d():
    d = doc_dxf()
    d.layers.add('CONTORNO', color=7)
    d.layers.add('FUROS', color=5)
    d.layers.add('OCULTO', color=8, linetype='DASHED')
    d.layers.add('EIXO', color=4, linetype='CENTER')
    d.layers.add('COTAS', color=3)
    d.layers.add('NOTAS', color=1)
    return d


def _cota(msp, p1, p2, base, angulo=0, s=4.0, prefixo=''):
    # texto explicito: o override de casas decimais (dimdec=0) e ignorado pelo
    # ezdxf e o desenho saia '23000' p/ 230,00
    ov = {'dimtxt': s, 'dimasz': s * 0.8, 'dimexe': s * 0.4, 'dimexo': s * 0.5}
    a = math.radians(angulo)
    dist = abs((p2[0] - p1[0]) * math.cos(a) + (p2[1] - p1[1]) * math.sin(a))
    txt = prefixo + ('%.0f' % dist if abs(dist - round(dist)) < 0.05 else ('%.1f' % dist).replace('.', ','))
    msp.add_linear_dim(base=base, p1=p1, p2=p2, angle=angulo, dimstyle='EZDXF', override=ov,
                       text=txt, dxfattribs={'layer': 'COTAS'}).render()


def _texto(msp, linhas, x, y, s):
    for ln in linhas:
        msp.add_text(ascii_(ln), height=s, dxfattribs={'layer': 'NOTAS'}).set_placement((x, y))
        y -= s * 1.6


def _arestas(msp, arestas, camada, dx=0, dy=0):
    for e in arestas:
        if e.geom_type.name == 'LINE':
            a, b = e.start_point(), e.end_point()
            msp.add_line((a.X + dx, a.Y + dy), (b.X + dx, b.Y + dy), dxfattribs={'layer': camada})
        else:
            pts = [e.position_at(i / 32) for i in range(33)]
            msp.add_lwpolyline([(p.X + dx, p.Y + dy) for p in pts], dxfattribs={'layer': camada})


def _cabecalho(p, s):
    return ['%s - %s  (%d pc)' % (p.codigo, p.nome.upper(), p.qtd), 'material: %s' % p.material,
            'quem faz: %s' % p.quem] + ([p.dim] if p.dim else [])


def dxf_chapa(p, msp):
    xs = [q[0] for q in p.perfil]
    ys = [q[1] for q in p.perfil]
    x0, y0 = min(xs), min(ys)
    pts = [(u - x0, v - y0) for u, v in p.perfil]
    w, h = max(xs) - x0, max(ys) - y0
    s = max(3.0, min(12.0, max(w, h) / 40))
    msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': 'CONTORNO'})
    tab = []
    for u, v, d in p.furos:
        msp.add_circle((u - x0, v - y0), d / 2, dxfattribs={'layer': 'FUROS'})
        tab.append('furo O%g em x=%.1f y=%.1f' % (d, u - x0, v - y0))
    _cota(msp, (0, 0), (w, 0), (0, -3 * s), s=s)
    _cota(msp, (w, 0), (w, h), (w + 3 * s, 0), 90, s=s)
    lin = _cabecalho(p, s) + ['chapa %.1f mm' % p.esp] + p.notas + tab
    _texto(msp, lin, 0, h + 6 * s + len(lin) * s * 1.6, s)


def dxf_torno(p, msp):
    pr = p.torno
    L = max(z for _, z in pr) - min(z for _, z in pr)
    s = max(3.0, min(10.0, max(L, 2 * max(r for r, _ in pr)) / 35))
    # silhueta: eixo da peca na horizontal (s -> x, r -> y)
    msp.add_lwpolyline([(z, r) for r, z in pr], close=True, dxfattribs={'layer': 'CONTORNO'})
    msp.add_lwpolyline([(z, -r) for r, z in pr], close=True, dxfattribs={'layer': 'CONTORNO'})
    msp.add_line((-10, 0), (L + 10, 0), dxfattribs={'layer': 'EIXO'})
    feitos = set()
    for (r1, z1), (r2, z2) in zip(pr, pr[1:]):
        if abs(r1 - r2) < 1e-6 and r1 > 0 and z2 != z1 and round(r1, 2) not in feitos:
            feitos.add(round(r1, 2))
            _cota(msp, ((z1 + z2) / 2, -r1), ((z1 + z2) / 2, r1),
                  (min(z for _, z in pr) - 4 * s * len(feitos), 0), 90, s=s, prefixo='Ø')
    zs = sorted({round(z, 2) for _, z in pr})
    rmax = max(r for r, _ in pr)
    if len(zs) > 2:                      # trechos em cadeia + comprimento total
        for za, zb in zip(zs, zs[1:]):
            _cota(msp, (za, 0), (zb, 0), (0, -rmax - 3 * s), s=s * 0.85)
    _cota(msp, (zs[0], 0), (zs[-1], 0), (0, -rmax - 7 * s), s=s)
    lin = _cabecalho(p, s) + p.notas + ['peça torneada - eixo na horizontal, medidas em mm']
    _texto(msp, lin, 0, max(r for r, _ in pr) + 6 * s + len(lin) * s * 1.6, s)


def dxf_vistas(p, msp):
    sol = p.solidos[0]
    bb = sol.bounding_box()
    c = bb.center()
    big = 10000
    vistas = [('FRENTE', (c.X, c.Y + big, c.Z), (0, 0, 1)),
              ('VISTA DE CIMA', (c.X, c.Y, c.Z + big), (0, 1, 0)),
              ('LADO DIREITO', (c.X - big, c.Y, c.Z), (0, 0, 1))]
    dx = 0.0
    s = max(3.0, min(12.0, max(bb.size.X, bb.size.Y, bb.size.Z) / 40))
    alturas = []
    for nome, orig, up in vistas:
        vis, hid = sol.project_to_viewport(orig, up, (c.X, c.Y, c.Z))
        xs = [v.X for e in vis for v in (e.start_point(), e.end_point())]
        ys = [v.Y for e in vis for v in (e.start_point(), e.end_point())]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
        ox, oy = dx - bx0, -by0
        _arestas(msp, vis, 'CONTORNO', ox, oy)
        _arestas(msp, hid, 'OCULTO', ox, oy)
        _cota(msp, (dx, 0), (dx + bx1 - bx0, 0), (dx, -3 * s), s=s)
        _cota(msp, (dx + bx1 - bx0, 0), (dx + bx1 - bx0, by1 - by0), (dx + bx1 - bx0 + 3 * s, 0), 90, s=s)
        msp.add_text(ascii_(nome), height=s, dxfattribs={'layer': 'NOTAS'}).set_placement((dx, by1 - by0 + 2 * s))
        dx += bx1 - bx0 + 12 * s
        alturas.append(by1 - by0)
    lin = _cabecalho(p, s) + p.notas
    _texto(msp, lin, 0, max(alturas) + 6 * s + len(lin) * s * 1.6, s)


def exporta_2d(BASE):
    pasta = os.path.join(BASE, 'dxf')
    os.makedirs(pasta, exist_ok=True)
    feitos = []
    for p in PECAS:
        if p.processo == 'compra':
            continue
        d = _doc2d()
        msp = d.modelspace()
        if p.perfil is not None:
            dxf_chapa(p, msp)
            tipo = 'chapa'
        elif p.torno is not None:
            dxf_torno(p, msp)
            tipo = 'torno'
        else:
            dxf_vistas(p, msp)
            tipo = 'vistas'
        nome = p.codigo.lower() + '-' + ascii_(p.nome).lower().replace(' ', '-').replace('(', '').replace(')', '').replace('/', '-')
        p.arquivo2d = nome[:60] + '.dxf'
        d.saveas(os.path.join(pasta, p.arquivo2d))
        feitos.append((p, tipo))
    return feitos


def renderiza_desenhos(BASE, feitos):
    """PNG de cada DXF 2D (so geometria e cotas; notas vao em texto no caderno)."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import Frontend, RenderContext
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    pasta = os.path.join(BASE, 'figuras')
    os.makedirs(pasta, exist_ok=True)
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE, color_policy=ColorPolicy.BLACK)
    for p, tipo in feitos:
        d = ezdxf.readfile(os.path.join(BASE, 'dxf', p.arquivo2d))
        msp = d.modelspace()
        for e in list(msp.query('TEXT[layer=="NOTAS"]')):
            if tipo != 'vistas' or not any(k in e.dxf.text for k in ('FRENTE', 'VISTA DE CIMA', 'LADO')):
                msp.delete_entity(e)
        fig = plt.figure(figsize=(8, 5))
        ax = fig.add_axes([0, 0, 1, 1])
        Frontend(RenderContext(d), MatplotlibBackend(ax), config=cfg).draw_layout(msp)
        ax.set_aspect('equal')
        ax.axis('off')
        fig.savefig(os.path.join(pasta, p.codigo.lower() + '.png'), dpi=170, facecolor='white',
                    bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)


