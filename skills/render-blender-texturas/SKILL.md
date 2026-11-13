---
name: render-blender-texturas
description: >-
  Render fotográfico de peças e móveis modelados por código (build123d) com textura de
  imagem real, como o padrão de um fornecedor de MDF ou o veio de madeira, no Blender sem
  janela (Cycles na GPU OptiX, ou na CPU). Traz o pipeline build123d → GLB → UV pela posição real com o veio
  no comprimento da peça, os valores de luz, câmera e cor que funcionaram e um roteiro
  pronto. Use quando o usuário pedir render "com textura", "com o padrão da chapa", "mais
  bonito/realista" que cor chapada, comparar padrões de acabamento, ou quando o SolidCraft
  não servir porque só aplica cor uniforme.
---

# Render com textura real no Blender, sem janela

Esta é a receita que funcionou em 2026-11-13, num móvel de MDF com o padrão real do fornecedor (4 combinações de cor × 5 vistas). O roteiro genérico do Blender está em [`scripts/roteiro_blender.py`](scripts/roteiro_blender.py): ele lê um `cfg.json` com os GLB, as texturas por prefixo de peça e as vistas.

## Quando usar o Blender e quando usar o SolidCraft

- **Cor chapada:** o raytrace do SolidCraft basta. A receita está na skill `solidcraft` ([`../solidcraft/SKILL.md`](../solidcraft/SKILL.md)).
- **Textura de imagem** (o padrão real de um fornecedor de MDF, um veio de madeira): só o Blender faz.
  - O `appearance.assign` do SolidCraft não aceita imagem.
  - Os `starter.wood.*` do SolidCraft são cor, não veio.
- **O MCP `blender-mcp`** só funciona com o Blender aberto e o addon ligado. Para rodar em lote, use a linha de comando.

## Ambiente (duas máquinas)

- **Linux:** Blender no flatpak: `flatpak run org.blender.Blender -b --python roteiro.py -- cfg.json`.
  Não existe `blender` no PATH. O flatpak tem `filesystems=host` (caminhos absolutos na home
  servem) e só `devices=dri`: **não enxerga a NVIDIA**, então o roteiro cai na CPU (16
  núcleos). 1400 × 1008 px, 64 amostras e denoise: ≈ 2 min por imagem; 600 px e 16
  amostras: ≈ 5 s.
- **Windows 11:** Blender 5.3 (winget `BlenderFoundation.Blender`) em
  `C:\Program Files\Blender Foundation\Blender 5.3\blender.exe`. Não está no PATH: usar o
  caminho completo (`-b` para rodar sem janela).
  - GPU **RTX 3060 Laptop (6 GB)**; o Cycles sem janela enxerga OptiX e CUDA (testado em
    2026-11-13). CPU i7-11800H, 8 núcleos / 16 threads.
  - Medido em 2026-11-13 (cubo de 1,6 m, sem textura): 1400 × 1008 px, 64 amostras e
    denoise na OptiX levou **≈ 13 s no total**, contando a abertura do Blender. Cena com
    textura e muitas peças deve demorar mais.
  - 6 GB de VRAM: com cena grande ou textura muito pesada, se der falta de memória, usar
    `"dispositivo": "CPU"`.
- O roteiro usa `"dispositivo": "OPTIX"` por padrão e cai sozinho na CPU sem GPU desse tipo.

## Escala da luz e da câmera

- **Escala:** luz e câmera acompanham o tamanho do modelo. Energia × (raio/1,05 m)²,
    tamanho da luz × raio/1,05 m, recorte da câmera pela distância. 1,05 m é o raio medido
    da escrivaninha 140 × 70 baixa-aberta (repositório Luthieria, `ferramentas/render_texturas_escrivaninha.py`,
    que tem roteiro próprio com as mesmas regras), onde as energias foram acertadas. Testado em 2026-11-13
    com cubos de 5 cm, 0,5 m, 1,6 m e 4 m: mesma exposição e enquadramento. Antes, peça
    pequena saía estourada de branco e a de 5 cm aparecia cortada pela câmera.
    Ajuste fino: `"luz": 0.8` no `cfg.json` multiplica todas as luzes.

## Pipeline

1. **build123d → GLB por estado:** `export_gltf(Compound(children=solidos), arq, binary=True)`, com `s.label = '<codigo>-<n>'` em cada sólido.
   - O nome do objeto no Blender começa com o código da peça. É ele que escolhe o material.
   - O glTF sai em metros e o importador já põe Z para cima.
2. **No Blender:**
   - `bpy.ops.wm.read_factory_settings(use_empty=True)` e `bpy.ops.import_scene.gltf(filepath=...)`.
   - Um material Principled por padrão, com um nó `ShaderNodeTexImage` ligado ao Base Color e `extension='REPEAT'`.
3. **UV pela posição real**, com bmesh.
   - **O veio corre no maior lado da peça.** Calcule o eixo de maior extensão do objeto no mundo.
   - Em cada face, ache o eixo da normal.
   - Se o eixo do veio estiver no plano da face, ele vira o `v`, e o outro eixo do plano vira o `u`. Nas faces de topo da chapa, use um eixo qualquer.
   - Faça `uv = (p[b]/tam_largura, p[a]/tam_altura)`, com `p` em coordenadas de mundo (`ob.matrix_world @ v.co`).
   - Assim, peças vizinhas continuam o veio sem costura visível.
   - ⚠️ Não use projeção BOX com o nó Mapping girado: numa das faces o eixo some e a textura vira listras.
4. **Escala da textura:** o fornecedor não diz quantos milímetros a imagem cobre.
   - A Berneck manda imagens de 1062 × 2300 px; usei 900 × 1950 mm, pelo tamanho das catedrais do veio.
   - Diga ao usuário que a escala é estimativa.

## Luz, câmera e cor que deram certo

| Item | Valor |
| --- | --- |
| Transformação de cor | **`Standard`**. Com o AgX o preto virou cinza e o marrom ficou claro e alaranjado |
| Luzes de área | três, posicionadas em múltiplos do raio do modelo: chave (−2,2, −2,6, 3,0)·R, 380 W, tamanho 2,5; enchimento (2,6, −1,8, 1,6)·R, 110 W; fundo (0,5, 3,0, 2,6)·R, 160 W |
| Mundo | cor (0,6, 0,59, 0,57), força 0,35 |
| Chão | plano de **400 m**, da mesma cor do mundo e com rugosidade 0,85, para o horizonte não aparecer |
| Câmera | lente de 35 mm, distância de **3,0 × o raio** do modelo, inclinação de 22°, ±35° de cada lado |
| Rugosidade | melamínico madeirado 0,62, preto texturizado 0,7, preto fosco 0,5 (a olho) |

**Tentativas que deram errado:**
- Lente de 50 mm a 2,25 × o raio corta o modelo.
- Luz de 900 W com o AgX lava a cor.
- Um chão de 40 m mostra uma linha de horizonte.

## Saída

- Um PNG por combinação × estado × vista, e uma folha JPG com as miniaturas (PIL).
- Use `--so <combinação>` para refazer só uma.
- Olhe a folha antes de mostrar ao usuário.
- `Material.use_nodes` e `World.use_nodes` dão aviso de descontinuado no Blender 5.2, mas ainda funcionam.

## Roteiro pronto

```bash
# Linux
flatpak run org.blender.Blender -b --python scripts/roteiro_blender.py -- cfg.json
# Windows (Git Bash)
"/c/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b --python scripts/roteiro_blender.py -- cfg.json
```

O formato do `cfg.json` está no cabeçalho do roteiro. Do lado do Python do projeto, basta:

1. exportar um GLB por estado da montagem, com `label = '<codigo>-<n>'` em cada sólido;
2. escrever o `cfg.json`, com um material por prefixo de código e um job por vista;
3. rodar o Blender;
4. juntar as imagens numa folha com PIL e olhar a folha antes de mostrar ao usuário.

O chão fica em z = 0, então o modelo tem de estar apoiado nele.
