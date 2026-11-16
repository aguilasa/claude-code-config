# CAD, 3D and rendering

Pointers for mechanical parts, jigs, machines and furniture designed by code.

- Part, machine, jig or furniture with DXF, STEP or 3D output: use the
  `cad-3d-dxf-python` skill (method plus the reusable `modelo_cad.py`). Main reminder: a
  3D DXF only exists as a mesh; the editable 3D format is STEP.
- SolidCraft (parametric CAD; MCP `solidcraft` / `solidcraft-live` and `solidcraft-cli`):
  load the `solidcraft` skill before using it. It holds the commands that worked, the
  camera convention, headless rendering through the CLI and the traps already hit.
- SolidCraft working folder is the MCP's `--allow-path` (`C:\solidcraft` on Windows,
  `~/solidcraft` on Linux). Before opening any project through the MCP, **copy** it (never
  move) into that folder (subfolders allowed, e.g. `<folder>/<project>/`) together with its
  supporting files, and open the copy; the original stays where it is. Tell the user where
  the copy is. Saves, exports and screenshots go there too; to keep edits made in the app,
  copy back to the original (ask before overwriting it).
- Render with an image texture (a supplier's real board pattern, wood grain), or anything
  better looking than flat colour: use the `render-blender-texturas` skill (headless
  Blender, Cycles on an OptiX GPU or the CPU).
- Example MCP configuration for these tools: `mcp/cad.mcp.json`.
