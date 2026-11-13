---
name: solidcraft
description: >-
  Como usar o SolidCraft (CAD paramétrico de código aberto, MCP `solidcraft` /
  `solidcraft-live` e o `solidcraft-cli`): modelar pelo MCP em batch, rodar roteiros e
  renders sem janela pelo CLI, convenção de câmera (yaw/pitch), raytrace de CPU com luz de
  área e chão, aparência por corpo, e as armadilhas já encontradas. Use antes de qualquer
  chamada ao SolidCraft, quando o usuário pedir para abrir um modelo "no SolidCraft" ou
  "live", gerar `.solidcraft` paramétrico, render com sombra sem Blender, ou quando um
  comando do SolidCraft falhar sem mensagem clara (cena preta, setup recusado, timeout).
---

# SolidCraft — o que já foi aprendido

CAD paramétrico de código aberto em Rust (https://solidcraft.io/), kernel B-rep próprio
(SolidCore). Salva `.solidcraft` (histórico editável), exporta STEP, STL, 3MF, OBJ, URDF.
Usado em duas máquinas; ver onde está antes de chamar:

- **Linux:** `/usr/bin/solidcraft` (app) e `/usr/bin/solidcraft-cli`.
- **Windows:** `C:\Program Files\SolidCraft\` (`solidcraft.exe` e `solidcraft-cli.exe`). O
  instalador pode não pôr a pasta no PATH; se o terminal não achar `solidcraft-cli`, usar o
  caminho completo. Arquivos de controle do app em `%LOCALAPPDATA%\SolidCraft\control\`
  (`current.port` diz a porta em uso).

## Pasta de trabalho do MCP (regra do usuário)

Os dois servidores MCP rodam com `--allow-path <pasta>`; fora dela `open`, `save`, `export`
e `screenshot path` são recusados. A pasta é a do `--allow-path` na configuração do MCP
(`claude mcp get solidcraft`); no Windows é `C:\solidcraft`.

- **Sempre que for abrir um projeto pelo MCP, mover o arquivo para essa pasta e abrir de
  lá.** Pode criar subpastas (ex.: `<pasta>/<projeto>/`). Mover também os arquivos de apoio
  que o modelo usa (STEP de entrada, roteiros).
- Avisar o usuário do caminho antigo e do novo depois de mover.
- Saídas novas (`save`, `export`, screenshots) também vão para `<pasta>/<projeto>/`.

## Dois servidores MCP

- `solidcraft-live`: conectado ao app aberto; o usuário vê o modelo aparecer. Usar só quando
  ele pedir "live"/quer ver ao vivo. Pré-requisito: app aberto com Preferences > Assistant >
  Agents through MCP > "Let AI agents connect" ligado (no Windows já ligado, porta 7878),
  ou subir com `solidcraft --control 7878` (Bash com `run_in_background`). Sem app as
  chamadas falham com "no SolidCraft app is listening"; depois de subir, a próxima chamada
  já conecta.
- `solidcraft`: roda com `--headless`, sessão sem janela dentro do próprio servidor; não
  precisa do app. Para lote e render, o `solidcraft-cli` direto pelo Bash (abaixo).
- Antes de modelar: `skill_reference {"skill":"solidcraft-modeling"}` (SKILL.md e
  reference.md trazem formato dos comandos, planos, ids e armadilhas) e
  `inspect_design {"measure":false,"sketches":false}`; perguntar antes de `new_design`/`open`
  se houver features (descarta trabalho).

### Abrir um arquivo no `solidcraft-live`

O `open` recusa caminhos fora das pastas permitidas (`--allow-path` do servidor); a
mensagem de erro lista as aceitas. Receita: mover o `.solidcraft` para
`<pasta>/<projeto>/` (seção acima), abrir de lá e tirar um `screenshot` com
`view: iso`. Se um roteiro externo regerar o modelo, fazê-lo gravar direto nessa pasta.
Se o app fechar no meio, pedir que o usuário o abra e esperar o aviso, sem insistir.

## Modelar pelo MCP (o que funcionou)

- Montar em poucos `batch` grandes com `"verbose": false`; batch é tudo-ou-nada
  (`failed.index`/`failed.error`, corrigir só aquele passo e reenviar).
- Primitivas são o caminho mais curto para peças mecânicas: `solid.box {length,width,height,
  center, operation, body_name, targets}` e `solid.cylinder {radius|diameter, height, base,
  axis: X|Y|Z|[x,y,z], operation, targets}`. Sempre passar `operation` e `targets`.
- Forma "língua com ponta redonda" = box + cylinder (join) + cylinder (intersect) para aparar.
- Barra de pontas redondas: `sketch.slot.center_to_center {p0, p1, width}` + `solid.extrude`.
- Furo escareado/rebaixado: `solid.hole {position:[x,y,z] na face, diameter, type:"counterbore",
  cb_diameter, cb_depth}`.
- Extrude de sketch cria corpo `BodyN` (N = próximo livre, mesmo depois de rollback); renomear
  com `body.rename` lendo o nome de `created_bodies` — não supor `Body1`.
- Plano XZ: sketch y = −Z mundial. Ver tabela de planos no reference.md.
- Conferir cada etapa com `measure`/`inspect.measure {"bodies":[...]}` contra volume calculado
  (bater com o STL do build123d foi o teste usado). Corte que erra o alvo dá "ok" mesmo assim.
- `save`/`export`/`screenshot path`: a pasta precisa existir (criar com mkdir antes).
- `screenshot {"source":"model","view":"iso","width":...,"height":...,"path":...}`.

## CLI sem janela (usado para os renders dos cadernos)

```bash
solidcraft-cli run roteiro.json --in modelo.step --save m.solidcraft --quiet   # aplica comandos
solidcraft-cli render m.solidcraft --setup vista --out img.png --overwrite     # render
solidcraft-cli exec <comando> '<json>'          # um comando avulso
solidcraft-cli exec engine.describe '{"command":"appearance.assign"}'   # docs de um comando
solidcraft-cli eval --in modelo.step            # mede corpos (volume, bbox, COM)
solidcraft-cli snapshot ...                     # imagem rápida com --view/--camera/--section
```

- `render` não aceita `--in`: primeiro `run ... --save`, depois `render` no `.solidcraft`.
- STEP exportado pelo build123d com `label` e `color` por sólido chega com as cores certas.
- Roteiro JSON = lista de `{"command","params"}`. Câmera/fundo/tamanho via
  `render.settings.set {"name":"vista","set":{"width","height","background":[255,255,255],
  "camera":{"target":[x,y,z],"yaw","pitch","distance","fov":0}}}` (radianos, mm; fov 0 =
  ortográfica).
- Convenção da câmera: yaw 0 olha de −Y, yaw +90° olha de −X; pitch = elevação.
  Equivalente ao matplotlib (elev, azim): `yaw = -radians(azim + 90)`, `pitch = radians(elev)`.
  Distância ≈ 2,65 × raio da caixa envolvente para enquadrar.
- Render rápido (cpu-raster) tem teto: `LimitExceeded: projected product exceeds 128000000
  pixel tests` em montagens grandes a 1600 px — tentar de novo com 75% e 50% do tamanho.
- Recortar o branco em volta depois (numpy/PIL).
- Implementação pronta e reutilizável: `render_solidcraft()` em `modelo_cad.py` da skill
  `cad-3d-dxf-python` (com volta ao matplotlib se o CLI faltar ou falhar).

## Render com sombra pelo CLI (raytrace de CPU) — usado em 2026-11-12

Funciona sem janela e sem GPU. Implementação de referência: uma função que, para cada
vista, grava o setup com `render.settings.set` no `.solidcraft` e dispara um
`solidcraft-cli render` por vista em paralelo (`subprocess.Popen`).

**Receita:** `render.settings.set {name, set: {width, height, background, camera, job, stage}}`
gravado no `.solidcraft` (`run roteiro.json --in m.solidcraft --save m.solidcraft`), depois
`solidcraft-cli render m.solidcraft --setup <name> --out img.png --overwrite --timeout 3000`.

- `job` é um enum com etiqueta `method`: `raster` | `cpu_raytrace` | `gpu_path`.
  `{"method":"cpu_raytrace","options":{...}}`. Campos de `options`: `primary_samples`,
  `shadows`, `budget` (`compact`|`studio`|`workstation`), `preset` (`neutral`|`warm_cool`|
  `key_rim`), `lights`, `punctual_lights`, `area_lights`, `area_samples`, `environment`,
  `hdr`, `seed`, `progressive`.
- **Não há documentação de esquema** (`engine.describe` devolve `input: null`). O jeito de
  descobrir campos é mandar um campo falso (`{"zz":1}`) e ler o erro "expected one of ...".
- Com `job` tipado, `render --samples` é recusado: as amostras vão em `options`.
- `lights`: até 8 direcionais `{direction, color, intensity}`. **`direction` aponta PARA a
  luz** (invertido deixa tudo preto). Intensidade na ordem de 0,3 a 1.
- `area_lights`: `{center_mm, edge_u_mm, edge_v_mm, color, intensity}`. **A luz só emite
  para o lado da normal `u × v`**: se ela olhar para fora, a cena sai toda preta, sem erro.
  Tem queda com a distância: a ~3 m da peça, intensidade 25 (principal) e 8 (preenchimento).
  É ela que dá sombra suave. `area_samples` só aceita **1, 4, 16 ou 64** e `primary_samples` só **1, 4 ou 16** (outro valor: erro só na hora de gravar o setup).
- `environment {color, intensity}` não clareou nada nos testes. O traçador é "direct/specular
  only; no diffuse interreflection": face que nenhuma luz vê fica preta. Por isso duas luzes
  de área em lados opostos + uma direcional fraca de cima.
- Chão: `render.stage.ground` aceita `margin_fraction` só até 10 e deixa o horizonte à mostra.
  Melhor escrever o painel direto em `set.stage`:
  `[{"id":"ground","center_mm":[0,0,-0.1],"half_u_mm":[30000,0,0],"half_v_mm":[0,30000,0],
  "reflectance_linear":[0.8,0.78,0.75]}]`. Com `pitch` ≥ ~0,38 e `fov` 0,5 o chão enche o quadro.
  `render.stage.backdrop` (ciclorama) pede `expected_revision` e não foi resolvido.
- Câmera em perspectiva: `fov` em radianos (0 = ortográfica). `yaw` positivo olha pela
  esquerda de quem está em −Y.
- Aparência antes do render: `appearance.assign {bodies:[nomes], appearance:"starter.wood.walnut-dark"}`
  ou `{color:[r,g,b]}`. Nomes dos corpos de um STEP = o `label` de cada sólido do build123d
  (`render.scene` lista). Biblioteca em `appearance.library` (madeiras `starter.wood.*`,
  metais `starter.metal.*`); são cores uniformes, sem veio.
- **Custo (o que mais dói):** um núcleo por render. 520 px com 4 × 16 amostras ≈ 1 min.
  1300 px com `primary_samples` 16, `area_samples` 16 e duas luzes de área levou **35 a 50 min**
  por imagem, e as cenas com mais faces iluminadas estouraram `--timeout 3000`. Acertar luz
  sempre a 520 px e 4 amostras, quatro variantes em paralelo numa folha; final a ~1000 px
  com 4 primárias e 16 de área (medido: ~8 min por imagem, duas em paralelo). Rodar vistas em paralelo (`Popen`), nunca em fila.
- Ao salvar por cima, o SolidCraft deixa um `.solidcraft.bak` ao lado.
- `find /` para achar documentação trava a sessão; não fazer.

Ainda não usado: `gpu_path` (o backend detectado neste PC é só CPU), presets
`NATIVE-STUDIO-001..025` (`render.preset.apply`, pedem setup de GPU), HDR, EXR.
