# NOTICE

This repository bundles code from the upstream project
**[Cai-aa/abaqus-mcp](https://github.com/Cai-aa/abaqus-mcp) v4.0** (MIT License):

- `abaqus_mcp_plugin.py` (Abaqus kernel bridge) — modified for Abaqus 2026:
  - `get_viewport_image` uses extensionless basename with `abaqusConstants.PNG/SVG/TIFF`
    and discovers the actual on-disk file.
  - `submit_job` returns `success=true` only when the final job status is `COMPLETED`.
  - `mcp_loop()` stop instructions use the real `MCP_HOME/stop.flag`, not a hardcoded path.
  - Recommended mode is blocking `mcp_loop()` (validated on Abaqus/CAE 2026).
- `mcp_server.py` (FastMCP stdio wrapper) — unchanged in behavior; default
  `ABAQUS_MCP_HOME` resolved next to the script instead of `~/.abaqus-mcp`.

New code added here — `scripts/bootstrap_windows.py`, `client.py`,
`abaqus_start_mcp.py`, references and docs — is also released under the MIT
License. See `LICENSE`.

This repository does NOT include Abaqus, any Abaqus license, or commercial model data.
You must supply your own legally licensed Abaqus installation.

---

## Knowledge / reference layer

The `references/` documentation and the diagnosis/verification methodology were adapted in
part from:

  https://github.com/jasonanewcoder/abaqus_skills
  MIT License, Copyright (c) 2025 Abaqus Skills Library Contributors

We did not vendor the upstream tree wholesale. We audited its main branch, selectively
rewrote the parts relevant to general / nonlinear-static / contact / error-diagnosis /
verification / ODB post-processing, and **re-validated the API examples on this machine's
Abaqus/CAE 2026** (see `validation/knowledge-layer/`). Items upstream itself marks as
unverified or version-dependent are kept flagged as such rather than claimed proven.

Notably, the upstream "use Q235 / default geometry / default load when parameters are
missing" convention is intentionally NOT adopted here: in a course/engineering task the
problem statement is the only source of truth.
