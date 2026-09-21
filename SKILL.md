---
name: abaqus-agent
description: Wire an AI agent to a local Windows Abaqus/CAE (tested on 2026, Python 3.10) so the agent can really control it — build models, submit analysis jobs, wait for completion, read the .odb, and take viewport screenshots — not just generate Abaqus scripts. Use when the user wants to connect/integrate Abaqus with an AI agent or MCP, automate Abaqus from an LLM, run FEM jobs programmatically, or "让 AI 控制 Abaqus / 接入 Abaqus MCP / 用 Agent 跑有限元". Uses file-based IPC with zero pip installs into Abaqus's bundled Python and no changes to the install dir or License.
---

# Abaqus Agent (Windows)

Lets an AI agent actually drive a local Abaqus/CAE over a file-based bridge.

```
Agent / MCP client
   │  write commands/*.json, read results/*.json   (file IPC, no sockets)
   ▼
Abaqus/CAE kernel plugin  (mcp_loop, blocking)
   │
   ▼
Part → Material → Section → Assembly → Step → BC → Load → Mesh → Job → ODB → screenshot
```

## One-time install

Run the bundled installer (detects Abaqus command, creates an isolated workspace + venv,
installs `mcp<2`, writes launcher/client). Works on a fresh machine:

```bash
python scripts/setup_abaqus_agent.py
# optional: --workspace D:\abaqus-agent  --abaqus-cmd abaqus
```

It prints the exact two commands to run next. Do **not** install into Abaqus's bundled
Python and do **not** touch `C:\Program Files\SIMULIA` or the License.

## Daily startup (3 steps)

1. Start Abaqus with the bridge (from the installer's output):
   ```
   set ABAQUS_MCP_HOME=<workspace>\mcp_home
   abaqus cae script="<workspace>\abaqus_start_mcp.py"
   ```
   Wait ~20–40 s until `<workspace>\mcp_home\status.json` shows `"status": "running"`.
2. Verify the round-trip: `<workspace>\.venv\Scripts\python.exe <workspace>\client.py`
   (expect a pong).
3. Drive Abaqus. From Python:
   ```python
   import sys; sys.path.insert(0, r"<workspace>")
   from client import send
   send("execute_script", script="from abaqus import mdb; print(mdb.models.keys())", timeout=60)
   send("submit_job", timeout=600, job_name="MyJob")
   ```
   For a standard MCP client (Cursor/Claude Desktop), run
   `<workspace>\.venv\Scripts\python.exe <workspace>\mcp_server.py`.

## Available commands

`ping`, `check_abaqus_connection`, `execute_script`, `get_model_info`, `list_jobs`,
`submit_job`, `get_odb_info`, `get_viewport_image`. `execute_script` runs in the Abaqus
kernel with `mdb`/`session` injected; `print()` output is returned to you.

## Before writing any Abaqus Python, read

- **[references/gotchas.md](references/gotchas.md)** — Abaqus 2026 / Windows API and
  process pitfalls (getByBoundingBox takes 6 floats, printToFile needs abaqusConstants.PNG,
  pin `mcp<2`, use blocking loop). Read this first — these are the bugs that cost time.
- **[references/validation_recipe.md](references/validation_recipe.md)** — a copy-paste
  cantilever-beam recipe (build → job → ODB max displacement/von Mises → PNG contour)
  you can use to confirm the link on any machine.

## Rules

- Only run trusted scripts; `execute_script` is arbitrary kernel code. Never expose to the public internet.
- Leave Abaqus install dirs and License untouched; everything lives in the isolated workspace.
- Prefer blocking `mcp_loop()`; the background-thread mode is experimental.
