# NOTICE

This repository bundles code from the upstream project
**[Cai-aa/abaqus-mcp](https://github.com/Cai-aa/abaqus-mcp) v4.0** (MIT License):

- `scripts/abaqus_mcp_plugin.py` (Abaqus kernel bridge) — modified for Abaqus 2026:
  - `get_viewport_image` uses extensionless basename with `abaqusConstants.PNG/SVG/TIFF`
    and discovers the actual on-disk file.
  - `submit_job` returns `success=true` only when the final job status is `COMPLETED`.
  - `mcp_loop()` stop instructions use the real `MCP_HOME/stop.flag`, not a hardcoded path.
  - Recommended mode is blocking `mcp_loop()` (validated on Abaqus/CAE 2026).
- `scripts/mcp_server.py` (FastMCP stdio wrapper) — unchanged in behavior; default
  `ABAQUS_MCP_HOME` resolved next to the script instead of `~/.abaqus-mcp`.

New code added here — `scripts/setup_abaqus_agent.py`, `scripts/client.py`,
`scripts/abaqus_start_mcp.py`, references and docs — is also released under the MIT
License. See `LICENSE`.

This repository does NOT include Abaqus, any Abaqus license, or commercial model data.
You must supply your own legally licensed Abaqus installation.
