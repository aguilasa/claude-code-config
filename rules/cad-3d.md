# CAD, 3D and rendering

Pointers for mechanical parts, jigs, machines and furniture designed by code.

- Part, machine, jig or furniture with DXF, STEP or 3D output: use the
  `cad-3d-dxf-python` skill (method plus the reusable `modelo_cad.py`). Main reminder: a
  3D DXF only exists as a mesh; the editable 3D format is STEP.
- SolidCraft (parametric CAD; MCP `solidcraft` / `solidcraft-live` and `solidcraft-cli`):
  load the `solidcraft` skill before using it. It holds the commands that worked, the
  camera convention, headless rendering through the CLI and the traps already hit.
- Render with an image texture (a supplier's real board pattern, wood grain), or anything
  better looking than flat colour: use the `render-blender-texturas` skill (headless
  Blender, Cycles on CPU).
- Example MCP configuration for these tools: `mcp/cad.mcp.json`.
