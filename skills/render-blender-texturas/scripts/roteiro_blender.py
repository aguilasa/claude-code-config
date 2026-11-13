# -*- coding: utf-8 -*-
"""Roteiro do Blender para render com textura de imagem, sem janela.

    flatpak run org.blender.Blender -b --python roteiro_blender.py -- cfg.json
    # ou: blender -b --python roteiro_blender.py -- cfg.json

cfg.json:
{
  "px": 1400, "aspecto": 0.72, "amostras": 64,
  "materiais": {                      # prefixo do nome do objeto -> material
    "M":  {"img": "/caminho/madeira.jpg", "rug": 0.62, "uv": true},
    "A":  {"img": "/caminho/preto.jpg",   "rug": 0.70, "uv": true},
    "F":  {"cor": [0.6, 0.62, 0.64], "rug": 0.35, "metal": 1.0}
  },
  "padrao": {"cor": [0.5, 0.5, 0.5], "rug": 0.5},
  "tex_mm": [900, 1950],              # tamanho real que a imagem cobre (largura, altura)
  "jobs": [
    {"glb": "/caminho/estado.glb", "png": "/caminho/vista.png",
     "yaw": -35, "pitch": 22, "dist": 3.0, "lente": 35,
     "ocultar": ["R1"]}                # prefixos que nao entram no render
  ]
}

O GLB vem do build123d: export_gltf(Compound(children=solidos), arq, binary=True), com
s.label = '<codigo>-<n>' em cada solido. O nome do objeto no Blender comeca pelo codigo, e
o prefixo mais longo que casar em "materiais" escolhe o material.

Veio: em cada objeto com "uv": true, o veio (eixo vertical da imagem) corre no maior lado
da peca, e a textura sai pela posicao real no mundo, sem costura entre pecas vizinhas.
"""
import json
import math
import sys

import bmesh
import bpy
from mathutils import Vector

cfg = json.loads(open(sys.argv[sys.argv.index('--') + 1]).read())
TL, TH = (v / 1000 for v in cfg.get('tex_mm', (900, 1950)))   # o glTF vem em metros


def material(nome, img=None, cor=(0.5, 0.5, 0.5), rug=0.5, metal=0.0):
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    n = m.node_tree.nodes
    b = next(x for x in n if x.type == 'BSDF_PRINCIPLED')       # por tipo: nome e traduzido
    b.inputs['Roughness'].default_value = rug
    b.inputs['Metallic'].default_value = metal
    if img:
        t = n.new('ShaderNodeTexImage')
        t.image = bpy.data.images.load(img)
        t.extension = 'REPEAT'
        m.node_tree.links.new(t.outputs['Color'], b.inputs['Base Color'])
    else:
        b.inputs['Base Color'].default_value = (*cor, 1)
    return m


def uv_veio(ob):
    """UV pela posicao real: v no maior lado da peca (o veio), u no outro eixo da face."""
    me, M = ob.data, ob.matrix_world
    pts = [M @ v.co for v in me.vertices]
    ext = [max(p[i] for p in pts) - min(p[i] for p in pts) for i in range(3)]
    veio = max(range(3), key=lambda i: ext[i])
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        nw = M.to_3x3() @ f.normal
        k = max(range(3), key=lambda i: abs(nw[i]))
        plano = [i for i in range(3) if i != k]
        a = veio if veio in plano else plano[1]
        b = next(i for i in plano if i != a)
        for lp in f.loops:
            p = M @ lp.vert.co
            lp[uv].uv = (p[b] / TL, p[a] / TH)
    bm.to_mesh(me)
    bm.free()


def escolhe(nome, mats):
    casam = [p for p in mats if nome.startswith(p)]
    return max(casam, key=len) if casam else None


def luzes(alvo, raio):
    """Tres luzes de area em multiplos do raio do modelo (valores que deram certo)."""
    for nome, pos, e, tam in (('chave', (-2.2, -2.6, 3.0), 380, 2.5),
                              ('enchimento', (2.6, -1.8, 1.6), 110, 3.0),
                              ('fundo', (0.5, 3.0, 2.6), 160, 2.5)):
        L = bpy.data.lights.new(nome, 'AREA')
        L.energy, L.size = e, tam
        o = bpy.data.objects.new(nome, L)
        bpy.context.scene.collection.objects.link(o)
        o.location = alvo + Vector(pos) * raio
        o.rotation_euler = (alvo - o.location).to_track_quat('-Z', 'Y').to_euler()
    w = bpy.data.worlds.new('mundo')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = next(x for x in w.node_tree.nodes if x.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.6, 0.59, 0.57, 1)
    bg.inputs['Strength'].default_value = 0.35


def chao():
    """Plano de 400 m da cor do mundo: o horizonte nao aparece."""
    bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
    bpy.context.object.data.materials.append(material('chao', cor=(0.6, 0.59, 0.57), rug=0.85))


def camera(alvo, raio, job):
    yaw, pitch = math.radians(job.get('yaw', -35)), math.radians(job.get('pitch', 22))
    d = raio * job.get('dist', 3.0)
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    bpy.context.scene.collection.objects.link(cam)
    cam.location = Vector((alvo.x + d * math.sin(yaw) * math.cos(pitch),
                           alvo.y - d * math.cos(yaw) * math.cos(pitch),
                           alvo.z + d * math.sin(pitch)))
    cam.rotation_euler = (alvo - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.lens = job.get('lente', 35)
    bpy.context.scene.camera = cam


for job in cfg['jobs']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=job['glb'])
    mats = {p: (material(p, img=m.get('img'), cor=m.get('cor', (0.5, 0.5, 0.5)),
                         rug=m.get('rug', 0.5), metal=m.get('metal', 0.0)), m.get('uv', False))
            for p, m in cfg['materiais'].items()}
    padrao = material('padrao', **{k: v for k, v in cfg.get('padrao', {}).items()
                                   if k in ('cor', 'rug', 'metal')})
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    for o in obs:
        if any(o.name.startswith(p) for p in job.get('ocultar', ())):
            o.hide_render = True
            continue
        p = escolhe(o.name, mats)
        m, com_uv = mats[p] if p else (padrao, False)
        if com_uv:
            uv_veio(o)
        o.data.materials.clear()
        o.data.materials.append(m)
        o.data.shade_flat()
    vis = [o for o in obs if not o.hide_render]
    pts = [o.matrix_world @ Vector(c) for o in vis for c in o.bound_box]
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    alvo, raio = (lo + hi) / 2, (hi - lo).length / 2
    chao()
    luzes(alvo, raio)
    camera(alvo, raio, job)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    s.cycles.device = 'CPU'
    s.cycles.samples = cfg.get('amostras', 64)
    s.cycles.use_denoising = True
    s.render.resolution_x = cfg.get('px', 1400)
    s.render.resolution_y = int(cfg.get('px', 1400) * cfg.get('aspecto', 0.72))
    s.view_settings.view_transform = 'Standard'     # AgX deixa o preto cinza e o marrom claro
    s.render.filepath = job['png']
    bpy.ops.render.render(write_still=True)
    print('feito', job['png'], flush=True)
