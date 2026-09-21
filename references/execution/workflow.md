# Execution Workflow — how the agent drives a real Abaqus task

> Status: **Validated on Abaqus 2026** (live kernel, file-IPC bridge v4.0.0).
> This is OUR runbook. It adapts the upstream playbook loop to the MCP architecture —
> it does **not** use `abaqus cae noGUI=` as the primary path.

## Architecture (do not redesign)

```
Agent  ->  client.send(...)  ->  mcp_home/commands/*.json
                                      |
                          Abaqus/CAE 2026 kernel plugin (mcp_loop, blocking)
                                      |
                          mdb / session / ODB / viewport
```

Bridge commands you actually have:
`ping`, `check_abaqus_connection`, `execute_script`, `get_model_info`, `list_jobs`,
`submit_job`, `get_odb_info`, `get_viewport_image`.

- `execute_script(script=...)` runs Python **in the live Abaqus kernel**; `mdb`, `session`
  are pre-injected. Use `print(json.dumps(...))` to return values.
- `submit_job(job_name=...)` calls `job.submit(); job.waitForCompletion()` and returns
  `status` (COMPLETED / ABORTED). It is **blocking** — call it with a generous timeout.
- Jobs write their `.odb/.sta/.msg/.dat` to the kernel CWD. **Start every build script
  with `os.chdir(<your scratch dir>)`** so outputs land where you can read them back.

## The execution loop (mandatory)

```
1. PARSE         read the problem (PDF/DOCX/image/参数表). Identify geometry, material,
                 boundary conditions, loads, analysis type. The problem statement is the
                 ONLY source of truth — see "Hard rule: parameters" below.
2. CONFIRM       if a key input is missing/illegible, STOP and ask. Never guess a number.
3. ROUTE         pick the references (see SKILL.md router) and read them.
4. BUILD         send one model-building script via execute_script. Delete any prior model
                 of the same name first. Keep every line unit-labelled (N-mm-MPa).
5. MESH/JOB      create the mdb.Job; call submit_job.
6. DIAGNOSE      if ABORTED: read .sta/.msg/.dat/.log -> error-diagnosis.md. Apply the
                 MINIMAL fix. Re-run (max ~3 attempts, then report honestly).
7. POSTPROCESS   read the ODB in-kernel (odb-postprocess.md), compute Mises from S,
                 pull RF / PEEQ / CPRESS as needed.
8. VERIFY        run the smallest sufficient check (verification.md): RF balance and/or
                 analytical comparison. COMPLETED != correct.
9. REPORT        model summary, key results, verification numbers, warnings, files.
```

## Hard rule: parameters come from the problem, never from defaults

This repo does **not** adopt the upstream "default Q235 / default 100 mm block / default
1000 N" rule. In a course / engineering task:

- The problem's original data (PDF, DOCX, image, drawing, parameter table) is the sole
  fact source.
- **Never** replace the structure, **never** invent a missing material/geometry/load,
  **never** substitute Q235 for the stated material, **never** "guess" an illegible value,
  **never** change the problem because "the other way is more reasonable".
- If a value is unreadable or absent, stop and state exactly what is missing.
- Defaults are allowed **only** when the user explicitly asks for a demo / example, or
  explicitly permits reasonable defaults.

> Counter-example we must never repeat: a 4-node truss problem was once silently rebuilt
> as a 6-node, 9-bar model. That is wrong. The topology in the problem statement is fixed.

## Units: N-mm-MPa only

| Quantity | Value for steel | Common mistake |
|----------|-----------------|----------------|
| E | 210000 MPa | 2.1e11 (that is Pa) |
| density | 7.85e-9 tonne/mm^3 | 7850 (kg/m^3) |
| gravity | 9800 mm/s^2 | 9.81 (m/s^2) — Gravity components are actual accelerations |
| stress | MPa | Pa |

## noGUI / headless status

`abaqus cae noGUI=xxx.py` and `abaqus python xxx.py` are **fallbacks**, not the default:

- **Primary:** the live MCP kernel (this is what is validated).
- Headless is acceptable for: batch sweeps, independent re-runs, regression tests, or a
  pure `odbAccess` post-process script when the kernel is busy.

## Gotchas that already bit us in Abaqus 2026

- `getByBoundingBox(...)` takes **6 separate floats**, not a tuple.
- Kernel scripts must be UTF-8 **without BOM** (a BOM makes `exec` fail with U+FEFF).
- `import mesh` is required; `from abaqus import *` does not bind `mesh`.
- Model/job name collisions error out; delete before recreating.
- `printToFile(fileName=...)` wants an extensionless base name + `from abaqusConstants import PNG`.
