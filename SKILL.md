---
name: abaqus-agent
description: Wire an AI agent to a local Windows Abaqus/CAE (tested on 2026, Python 3.10) so the agent can really control it — build models, submit analysis jobs, wait for completion, read the .odb, verify the physics, and take viewport screenshots — not just generate Abaqus scripts. Use when the user wants to connect/integrate Abaqus with an AI agent or MCP, automate Abaqus from an LLM, run FEM jobs programmatically, or "让 AI 控制 Abaqus / 接入 Abaqus MCP / 用 Agent 跑有限元". Uses file-based IPC with zero pip installs into Abaqus's bundled Python and no changes to the install dir or License.
---

# Abaqus Agent (Windows)

Lets an AI agent **drive** a local Abaqus/CAE over a file-based bridge, then model,
diagnose, verify and report. Two layers:

- **Execution layer (this repo's scripts):** Agent → `client.send` → `mcp_home` file IPC
  → Abaqus/CAE 2026 kernel plugin → Job / ODB / screenshot. Validated end-to-end. **Do not
  redesign this.**
- **Knowledge layer (`references/`):** Abaqus modeling, analysis, diagnosis and verification
  recipes, progressively disclosed. Read only what the task needs.

```
Agent / MCP client
   │  write commands/*.json, read results/*.json   (file IPC, no sockets)
   ▼
Abaqus/CAE kernel plugin  (mcp_loop, blocking)
   ▼
Part → Material → Section → Assembly → Step → BC → Load → Mesh → Job → ODB → verify → screenshot
```

## One-time install

```bash
python scripts/setup_abaqus_agent.py
# optional: --workspace D:\abaqus-agent  --abaqus-cmd abaqus
```
Do **not** install into Abaqus's bundled Python and do **not** touch
`C:\Program Files\SIMULIA` or the License.

## Daily startup (3 steps)

1. Start Abaqus with the bridge:
   ```
   set ABAQUS_MCP_HOME=<workspace>\mcp_home
   abaqus cae script="<workspace>\abaqus_start_mcp.py"
   ```
   Wait ~20–40 s until `mcp_home\status.json` shows `"status": "running"`.
2. Verify the round-trip: `<workspace>\.venv\Scripts\python.exe <workspace>\client.py` (expect pong).
3. Drive Abaqus:
   ```python
   import sys; sys.path.insert(0, r"<workspace>")
   from client import send
   send("execute_script", script="from abaqus import mdb; print(mdb.models.keys())", timeout=60)
   send("submit_job", job_name="MyJob", timeout=600)
   ```
   For an MCP client (Cursor/Claude Desktop): `<workspace>\.venv\Scripts\python.exe <workspace>\mcp_server.py`.

## Bridge commands

`ping`, `check_abaqus_connection`, `execute_script`, `get_model_info`, `list_jobs`,
`submit_job`, `get_odb_info`, `get_viewport_image`. `execute_script` runs in the kernel with
`mdb`/`session` injected; `print()` output returns to you.

---

## Task router — read only what you need

First always skim **[references/gotchas.md](references/gotchas.md)** (2026 API/Windows pitfalls)
and **[references/execution/workflow.md](references/execution/workflow.md)** (the loop + units +
the hard parameter rule). Then read the slice for the task:

| Task | Read |
|------|------|
| Run the end-to-end loop | [execution/workflow.md](references/execution/workflow.md) |
| Job ABORTED / won't converge | [execution/error-diagnosis.md](references/execution/error-diagnosis.md) |
| Prove the result is right | [execution/verification.md](references/execution/verification.md) |
| Material / plasticity / section | [modeling/material.md](references/modeling/material.md) |
| Mesh & elements | [modeling/mesh.md](references/modeling/mesh.md) |
| Contact / rigid body / coupling | [modeling/contact.md](references/modeling/contact.md) |
| Read the ODB / extract RF, S, PEEQ, CPRESS | [modeling/odb-postprocess.md](references/modeling/odb-postprocess.md) |
| Linear static (beam/bracket/truss) | [analysis/linear-static.md](references/analysis/linear-static.md) |
| Plasticity / large deformation / displacement control | [analysis/nonlinear-static.md](references/analysis/nonlinear-static.md) |
| Smoke-test the link on any machine | [references/validation_recipe.md](references/validation_recipe.md) |

Proven recipes live in `validation/knowledge-layer/` (Abaqus 2026 micro-tests + results).

## Hard rules for an engineering / course task

1. **The problem statement is the only fact source.** If it gives a PDF/DOCX/image/drawing
   /parameter table, use those numbers. Never substitute Q235, never invent a missing
   material/geometry/load, never "guess" illegible values, never change the problem because
   another approach "seems more reasonable". Defaults are allowed only when the user
   explicitly asks for a demo/example or permits them.
   - Never repeat the mistake of rebuilding a 4-node truss as a 6-node, 9-bar model.
2. **COMPLETED ≠ correct.** Run the smallest sufficient verification (RF balance and/or an
   analytical check) before reporting numbers.
3. **Read logs before shrinking increments.** On failure go to
   execution/error-diagnosis.md.
4. **Do not auto-"fix" convergence by changing the problem** (material strength, friction,
   geometry, load, BC values) unless the original choice was itself a modeling error.

## Safety / scope

- Only run trusted scripts; `execute_script` is arbitrary kernel code. Never expose to the public internet.
- Leave Abaqus install dirs and License untouched; everything lives in the isolated workspace.
- Prefer blocking `mcp_loop()`; background-thread mode is experimental.
- Out of scope this round: UMAT/VUMAT, fatigue, XFEM, composites, full thermal. Treat
  these as extensions that need local single-element validation before production use.
