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

## The execution loop (mandatory) — 8 phases, gated

Each phase ends at a gate. A failed gate stops the loop; do not pass through it by
"the job ran fine". Gate names map to the rules in `lessons-learned.md`.

```
PHASE 1 PROBLEM FIDELITY
   read the original statement (PDF/DOCX/image/参数表). List FACTS, UNKNOWNS, AMBIGUITIES, and MODEL INFERENCES.
   G1 Problem Fidelity (lessons-learned Case 1): nodes/parts, topology, dims,
     material, load location, load direction, supports, contacts, objective all
     transcribed from the statement. Missing/illegible -> STOP and ask. No guessing.
PHASE 2 MODEL PLAN
   dimensionality (3D vs axisymmetry when truly axisymmetric), element, material,
   BC, load, contact, expected outputs.
   G2 Requirement Compliance (Case 4): every observable the statement asks for
     (CPRESS, punch RP RF, specific component, opening ...) maps to a real entity in
     this plan. No "equivalent BC" standing in for a requested contact/RP result.
PHASE 3 PREFLIGHT
   units (N-mm-MPa), geometry, topology, output requests, job path, scratch chdir.
   G3 Pre-run Output (Case 6): each required observable has an ODB output path
     (S/U/RF/PEEQ/CPRESS/COPEN/HistoryOutput) in the FieldOutput/HistoryOutput request.
     A required-but-unrequested quantity -> add it now, do not start the run.
   G1 input check Suspicious input (Case: keep E=21000 as written): a parameter that "looks
     wrong" vs common knowledge is NOT permission to edit it. Mark the doubt, use the
     stated value, offer an alternate rerun.
PHASE 4 RUN
   build via one execute_script (delete same-named model first); submit_job with a
   generous timeout; if ABORTED read .sta/.msg/.dat/.log -> error-diagnosis.md, apply
   the MINIMAL fix, re-run (max ~3 attempts, then report honestly).
   G4 Solver completion: status == COMPLETED. This alone is NOT success.
PHASE 5 RESULT EXTRACTION
   read ODB in-kernel (odb-postprocess.md), compute Mises from S, pull field + history.
   G5 Result Interpretation (Cases 2/3/7): for every reported extrema record
     location, region, proximity to a constraint/contact edge, singularity plausibility,
     and a representative mean/path value with its averaging definition.
PHASE 6 VERIFICATION
   smallest sufficient check (verification.md): RF balance, analytical/sanity check,
     interference compatibility, trends, mesh sensitivity when needed.
   G6 Verification (Cases 2/7): same Job/frame/quantity/region/units/BC/assumptions;
     no back-fitting; benchmark applicable to this FE model; press force kept distinct
     from CPRESS.
PHASE 7 REPORTING
   model summary, key results, verification numbers, warnings, files.
   G7 Report Consistency (Case 5): numbers/units/signs/radius-vs-diameter/
     engineering-vs-true strain/direction checked against model variables and formulas.
PHASE 8 COMPLETION GATE
   G8 Completion: only when G1..G7 all pass may you write
     "analysis completed and validated".
   COMPLETED is not task complete. If the solver merely returned COMPLETED, write "solver completed" and list the
   gates that did NOT pass.
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

## Units: N-mm-MPa preferred consistent system

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

## Required-observable → ODB key quick map (G3)

| Statement asks for | Must request in the job |
|--------------------|--------------------------|
| stress / Mises | `S` (Mises is computed post, never requested) |
| displacement / deformation | `U` |
| reaction / press force | `RF` (on the set/RP you drive) |
| plastic strain / yield | `PEEQ` (and `PE`) |
| contact pressure | `CPRESS` (per-interaction key!) |
| contact opening / slip | `COPEN`, `CSHEAR` |
| a quantity vs time (force–time, CPRESS–time) | `HistoryOutput` for that interaction/RP |

If the task lists an observable above and the `FieldOutputRequest`/`HistoryOutput` does
not include it, **stop and add it before `submit_job`** — an unrequested result cannot
be reconstructed later.

## Where the failure stories live

Closed-loop `failure/success → root cause → rule` entries are in
[lessons-learned.md](lessons-learned.md); read it when a gate fires. Static regression
scenarios are in [regression-checklist.md](regression-checklist.md).
