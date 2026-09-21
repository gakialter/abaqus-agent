# abaqus-agent

Let an AI agent (or MCP client like Cursor / Claude Desktop) **actually control your local
Abaqus/CAE on Windows** — build models, submit analysis jobs, wait for completion, read the
`.odb`, and take viewport screenshots. Not just generating Abaqus scripts.

Tested on **Abaqus 2026** (bundled Python 3.10). Uses a **file-based bridge**: the Abaqus
kernel polls JSON command files, so there are no open sockets and **nothing is installed into
Abaqus's bundled Python** and **no files in `Program Files\SIMULIA` or the License are touched**.

```
Agent / MCP client
   │  write commands/*.json, read results/*.json   (file IPC)
   ▼
Abaqus/CAE kernel plugin  (mcp_loop, blocking)
   │
   ▼
Part → Material → Section → Assembly → Step → BC → Load → Mesh → Job → ODB → screenshot
```

## Install (one command)

Clone this repo, then run the installer on the machine that has Abaqus:

```bash
git clone https://github.com/gakialter/abaqus-agent.git
cd abaqus-agent
python scripts/setup_abaqus_agent.py
```

The installer auto-detects the `abaqus` command, creates an isolated workspace
(`~/Desktop/abaqus-agent` by default) with its own venv, pins `mcp<2`, and prints the exact
next commands. Optional flags: `--workspace D:\abaqus-agent --abaqus-cmd abaqus`.

## Use it

1. Start Abaqus with the bridge (printed by the installer):
   ```
   set ABAQUS_MCP_HOME=<workspace>\mcp_home
   abaqus cae script="<workspace>\abaqus_start_mcp.py"
   ```
   Wait until `<workspace>\mcp_home\status.json` shows `"status": "running"`.
2. Verify the round-trip: `<workspace>\.venv\Scripts\python.exe <workspace>\client.py` (expect pong).
3. Drive Abaqus from Python:
   ```python
   from client import send
   send("execute_script", script="from abaqus import mdb; print(mdb.models.keys())")
   send("submit_job", timeout=600, job_name="MyJob")
   ```
   For a standard MCP client, run `<workspace>\.venv\Scripts\python.exe <workspace>\mcp_server.py`.

## Layout

```
abaqus-agent/
├── SKILL.md                     # agent-facing instructions (load as a skill)
├── scripts/
│   ├── setup_abaqus_agent.py    # one-click installer
│   ├── abaqus_mcp_plugin.py     # Abaqus kernel bridge (patched for 2026)
│   ├── mcp_server.py            # stdio MCP server for MCP clients
│   ├── client.py                # direct file-IPC driver
│   └── abaqus_start_mcp.py      # Abaqus-side launcher template
└── references/
    ├── gotchas.md               # Abaqus 2026 / Windows pitfalls
    └── validation_recipe.md     # cantilever beam → job → ODB → screenshot recipe
```

## Available commands

`ping`, `check_abaqus_connection`, `execute_script`, `get_model_info`, `list_jobs`,
`submit_job`, `get_odb_info`, `get_viewport_image`.

## Adaptation & changelog (validated on Abaqus 2026)

Bundles [Cai-aa/abaqus-mcp v4.0](https://github.com/Cai-aa/abaqus-mcp) (MIT) with fixes
validated end-to-end on Abaqus/CAE 2026 (Python 3.10):

- `get_viewport_image`: extensionless basename (printToFile adds its own extension) +
  `abaqusConstants.PNG/SVG/TIFF`; the real on-disk file is discovered and returned.
- `submit_job`: returns `success=true` only when the final status is `COMPLETED`;
  ABORTED/TERMINATED/ERROR return `success=false` with the final status kept.
- `mcp_loop()` stop instruction points at the real `<workspace>/mcp_home/stop.flag`.
- `ABAQUS_MCP_HOME` has a single source of truth: `<workspace>/mcp_home` for the plugin,
  client and MCP server. The installer writes `mcp_client_config.json` with that env embedded.
- Recommended mode is blocking `mcp_loop()` (background thread mode is experimental).
- External server pins `mcp<2` (the bundled code uses FastMCP v1).

Validation: a 100x10x10 mm cantilever ran build -> mesh -> job -> ODB -> contour screenshot;
job COMPLETED, max displacement 0.403 mm, max von Mises 100.2 MPa.

## Disclaimer / safety

- `execute_script` runs arbitrary Python in the Abaqus kernel - only use with trusted scripts
  and never expose this to the public internet.
- Does not include Abaqus, a license, or any commercial model data. You need your own legal
  Abaqus install and license.

## License

MIT. Bundles upstream MIT code from Cai-aa/abaqus-mcp; see `LICENSE` and `NOTICE.md`.
