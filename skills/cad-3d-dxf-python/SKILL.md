---
name: cad-3d-dxf-python
description: >-
  Como gerar peças e montagens mecânicas por código Python: sólidos 3D (STEP, glTF/GLB,
  DXF 3D) e desenhos 2D de fabricação em DXF (chapa com tabela de furos, peça de torno,
  três vistas com ocultas), checagem de interferência entre peças, renders PNG sem
  Blender e caderno PDF para quem fabrica. Use sempre que o usuário pedir para projetar
  uma máquina, gabarito, ferramenta, móvel ou peça e quiser DXF, STEP, modelo 3D,
  "versão montada em 3D", desenho para laser/plasma/CNC/torno, vista explodida ou lista
  de peças com desenho — em qualquer projeto. Também para dúvidas como "dá para ter DXF
  3D editável?", "como exportar sólido", "build123d", "ezdxf cota", "3DSOLID". Não use
  para converter PDF de planta em DXF (isso é rastreio de vetor, outra coisa) nem para
  modelagem artística/orgânica (Blender).
---

# CAD por código: 3D (STEP/GLB/DXF) + DXF 2D de fabricação

Conhecimento consolidado no projeto de uma serra-fita (out/2026): 67 sólidos,
0 interferências, 35 DXF 2D, caderno de 41 páginas. Código pronto para copiar em
[`modelo_cad.py`](modelo_cad.py) (construtores, exportadores, interferência, renders,
DXF 2D). O projeto de referência foi dividido em três módulos: cálculos
(`*_calculos.py`), gerador 3D/2D e caderno PDF.

## Ferramentas

- **build123d ≥ 0.13** (OpenCascade): sólidos, booleanas, `export_step`, `export_gltf`,
  `tessellate`, `project_to_viewport`. Instalar no venv do projeto com pip
  (`.venv/bin/pip install build123d`); se o projeto usa `uv`, registrar no pyproject.
- **ezdxf**: DXF 2D e DXF 3D em malha; `ezdxf.addons.drawing` renderiza DXF → PNG.
- **matplotlib + numpy**: renders 3D (`Poly3DCollection`) sem Blender.
- **PyMuPDF (fitz)**: caderno PDF com `fitz.Story` + `DocumentWriter`.

## Verdades que custaram caro

1. **DXF não guarda sólido editável de forma livre.** `3DSOLID` exige dados ACIS
   (proprietário); nenhuma biblioteca livre grava. **DXF 3D = malha** (`MESH` via
   `ezdxf.render.MeshBuilder` a partir de `solido.tessellate()`): serve para ver, medir
   e posicionar. **O formato editável é STEP.** Diga isso ao usuário logo que ele pedir
   "DXF 3D", e entregue os dois (mais GLB para ver no navegador).
2. **Uma geometria, todas as saídas.** Cada peça nasce de um perfil 2D: chapa = perfil
   extrudado; torno = meio-perfil revolucionado; tubo = retângulo vazado. O mesmo perfil
   gera o DXF de corte, o desenho de torno e o sólido 3D — eles não divergem. Guarde
   `perfil`, `furos`, `esp`, `torno` na peça (dataclass `Peca`).
3. **Números de engenharia num módulo separado, puro** (`*_calculos.py`): constantes de
   requisito → escolhas por catálogo contra critérios escritos (tubo, eixo, rolamento,
   mola, polia) → `calculos.md` gerado. A geometria importa daí. Nunca digite número de
   cálculo à mão no README: copie do gerado.
4. **Face saída de booleana pode vir com normal invertida** e `extrude` vai para −Z. Já
   pôs uma lâmina 25 mm fora dos volantes. Corrija posicionando pelo bounding box
   (`_ext()` em `modelo_cad.py`). Mesmo motivo para polígono de lâmina/correia: use
   círculos verdadeiros, não polígonos, onde peças encostam (polígono corta a corda e
   gera interferência falsa).
5. **Rotações do build123d:** `Rot(90,0,0)` leva (x,y,z) → (x,−z,y). Perfil desenhado em
   XY vira plano XZ com `Pos(0, y0+t, 0) * Rot(90,0,0) * extrusão` (`chapa_xz`). Peça de
   torno: `revolve(Polygon(meio-perfil), Axis.Y)`.
6. **Lado do operador.** Defina o sistema da máquina no início (origem, onde fica o
   operador) e confira num render de frente antes de detalhar. Se a máquina saiu
   espelhada, espelhe tudo **uma vez no registro** (`sol.mirror(Plane.YZ)` em `peca()`,
   `ESPELHAR_X`); chapa e peça torneada espelhadas são a mesma peça virada, e os DXF 2D
   (que vêm do perfil) não mudam. Documente que o código e os arquivos 3D diferem em X.
7. **Checagem de interferência a cada execução**, todos os pares: filtro por bounding
   box, depois `(a & b).volume > 1 mm³`. Lista explícita de contatos permitidos (eixo no
   cubo, pneu no aro). Peças coladas face com face (pilha de compensado) entram num grupo
   ignorado — a booleana de faces coplanares pode lançar exceção, que conta como
   interferência. Meta: **0**, e o número vai para o README.
8. **Validar o STEP reimportando** (`import_step`): contar sólidos (= soma das
   instâncias) e conferir o bounding box total contra as cotas de projeto.

## DXF 2D de fabricação (ezdxf)

- `ezdxf.new('R2010', setup=True)`, `doc.units = MM`, `$INSUNITS = 4`, `$MEASUREMENT = 1`.
- Camadas: `CONTORNO`, `FUROS`, `OCULTO` (DASHED), `EIXO` (CENTER), `COTAS`, `NOTAS`;
  em trabalho com incerteza, `INCERTO` tracejado para o que não foi lido de cota.
- **Cota linear com `text=` explícito.** O override `dimdec` é ignorado e a cota sai
  "23000" para 230,00. Formate o texto você mesmo.
- Três tipos de desenho, escolhidos pela peça:
  - **chapa**: perfil plano + furos + **tabela de furos por coordenada** a partir do
    canto inferior esquerdo (laser/plasma/CNC);
  - **torno**: silhueta com eixo horizontal, Ø cotados uma vez por diâmetro, comprimentos
    em cadeia + total;
  - **vistas**: `solido.project_to_viewport(origem, up, alvo)` → arestas visíveis e
    ocultas; frente, cima e lado.
- Texto DXF em ASCII (`unicodedata.normalize('NFKD')`), porque nem todo CAD lê acento.
- PNG de conferência: `ezdxf.addons.drawing` com `BackgroundPolicy.WHITE` e
  `ColorPolicy.BLACK`, removendo a camada `NOTAS` (as notas vão em texto no PDF).
- Para imprimir 1:1 (gabarito), um conversor DXF → SVG com `width`/`height` em mm.

## Renders sem Blender

`render_solidcraft()` em `modelo_cad.py` usa o `solidcraft-cli` quando ele está instalado
(ver a skill `solidcraft`) e volta ao matplotlib se faltar ou falhar. Para render com
textura de imagem (padrão real de MDF, veio), ver a skill `render-blender-texturas`.

Tessela cada sólido, sombreia por `|n·luz|`, `Poly3DCollection(zsort='average')`,
projeção ortográfica, eixos com aspecto 1:1 e **recorte automático do branco** depois de
salvar (o eixo 3D é quadrado). Câmera matplotlib: `azim=90` olha de +Y, `azim=0` de +X.
Vistas: frente, lateral, isométrica, aberta (sem carenagens), explodida (deslocamento
por prefixo de código). O z-sort do matplotlib erra em peças que se cruzam; para algo
bonito, Blender. Para conferir montagem, basta.

## Caderno PDF para quem fabrica

- **Sem jargão de software**: nada de nome de arquivo, script, DXF, coordenada, camada,
  polegada. "Ø64", não "O64". Tolerâncias por extenso ("entre 49,984 e 50,000 mm").
- Capítulos por quem faz (marceneiro / serralheiro / torneiro / compras / montagem),
  **uma ficha por página**.
- Imagem com **largura absoluta em pt** calculada pela proporção para não passar da
  altura útil; largura em `%` encolhe figuras estreitas a um selo no `fitz.Story`.
- Fontes Carlito/P052 via `fitz.Archive`; `doc.subset_fonts()` antes de salvar.
- Depois de gerar, buscar no texto do PDF por `dxf|script|\.py|polegada|\bO\d` = zero.

## Erros de engenharia já cometidos (confira sempre)

- **Carga real no tensionador**: volante/polia que recebe dois trechos de correia ou
  lâmina carrega **2T**, não T. Mola dimensionada para T fica achatada.
- **Madeira é decidida pela torção, não pela flexão** (G do compensado ≈ 500 MPa, ~160×
  menor que o do aço): estimativa feita só por flexão subestima a seção 2–3×. Madeira
  sob carga constante flui (EC5 k_def); fixar aço nela só com parafuso passante e chapa
  dos dois lados; furar cada chapa antes de colar a pilha.
- Ponto de fixação aparafusado em vez de soldado muda o caminho de carga: redesenhe o
  suporte (console, contraplaca), não só o material.
- Massa: some chapas de fixação antes de prometer que "fica mais leve".

## Ordem de trabalho que funcionou

1. Requisitos com origem de cada número → módulo de cálculo → revisar números antes de
   desenhar (seção, eixo, rolamento saem daí).
2. Sistema de coordenadas + uma vista de frente cedo, para pegar espelhamento.
3. Peças por grupo, rodando a checagem de interferência a cada grupo.
4. Exportar 3D (STEP/GLB/DXF malha por peça e montagem), 2D, CSV de peças (código, nome,
   qtd, material, processo, quem faz, medidas, massa), renders, PNG dos DXF.
5. README técnico (para o usuário) + caderno PDF (para quem fabrica) + orçamento só se
   pedido.
6. Verificação: interferências = 0, STEP reimportado, figuras olhadas, PDF sem jargão.
