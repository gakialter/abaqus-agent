# D6 regression harness and D8 acceptance gates

Run offline unit tests from the repository root:

```powershell
py -3.11 -m tests.run
```

`PASS` is an observed passing contract. `EXPECTED_FAIL_CONFIRMED_BUG` uses
`unittest.expectedFailure`: it encodes the desired D7 behavior and must stay red
on this baseline. An unexpected success fails the suite so the marker is removed
after the fix. `MANUAL_ACCEPTANCE_REQUIRED` is not counted as a pass. Tests use
temporary directories; the optional Python matrix command may download packages
but never changes the checkout `.venv`:

```powershell
py -3.11 -m tests.accept_python --candidates
```

Observed after D6.1 contract correction: **54** automated tests, **19 PASS**, **35
EXPECTED_FAIL_CONFIRMED_BUG**, zero ordinary failures. The Python matrix was
rerun in fresh disposable venvs with `mcp==1.30.0`; the exact JSON output is
saved in [`python_matrix_d61.json`](python_matrix_d61.json):

| Interpreter | Result | Evidence |
| --- | --- | --- |
| 3.11 | PROJECT_TESTED_PASS | venv, exact MCP version, `FastMCP`, canonical server load, STDIO handshake and tool discovery |
| 3.10 | NOT_AVAILABLE | `py -3.10` unavailable |
| 3.12 | NOT_AVAILABLE | `py -3.12` unavailable |
| 3.13 | NOT_AVAILABLE | `py -3.13` unavailable |
| 3.14 | PROJECT_TESTED_PASS | venv, exact MCP version, `FastMCP`, canonical server load, STDIO handshake and tool discovery |

The tested release baseline remains 3.11. The 3.14 result is local evidence,
not a change to the supported-version policy. No external Python is rejected
solely for being 3.10; D7 must identify Abaqus's bundled interpreter by its
actual executable/path.

## Finding to regression mapping

The D0–D5 source reports were not supplied with D6. The table maps the findings
explicitly named in the D6 request; it does not invent report numbers or claim a
one-to-one correspondence to unseen D0–D5 records.

| D6 finding / contract | Test IDs |
| --- | --- |
| Clean archive, source inventory, runtime/generated path exclusion, copied workspace, personal paths | `L1_*`, `L6_archive_copy_paths_and_missing_runtime` |
| Current knowledge guidance vs historical validation evidence, gate names, facts, inference, output/units/back-fit claims | `L2_*` |
| Command/result IPC, timeout, late result, queued B/C after long A | `L3_*` |
| Plugin atomicity, stale cleanup, ownership, stop flag, screenshot behavior | `L4_*` |
| Status/PID/ping/start path | `L5_*` |
| Clean-machine bootstrap, venv/config/path cases | `L6_*`, `L8_*` |
| Python and MCP version/platform | `accept_python.py` (optional, networked) |
| Skill artifact integrity and connector values | `L9_*`, `L10_*` |

Current P0 exposures include clean-archive preflight requiring generated
`mcp_home`, loss of queued B/C after the 120 s stale cleanup, no exclusive
consumer claim, and the batch start path reporting success without a ping.

## D7 production seams required to turn red tests green

- One canonical runtime path and a source-only preflight that creates runtime
  directories after source verification.
- Atomic command/result publish (`.tmp` plus same-directory replace), command
  claim/lease and ownership with a session ID; cleanup must distinguish queued
  valid work from abandoned work.
- A queued timeout may cancel before claim. A timeout after claim must say
  execution outcome is unknown and may continue; it does not promise
  cancellation. Late results need not disappear immediately. A bounded cleanup
  policy, if adopted in D7, needs a separate eventual-cleanup test.
- Session-scoped status, exact PID check, timestamp bounds, and a ping bound to
  that same session before start success.
- One config reader for non-derivable choices, repo-relative derived paths,
  legacy JSON/BAT migration and malformed-config reporting.
- Unique screenshot names and explicit format validation. Preserve the actual
  format/extension returned by Abaqus.

## Manual Abaqus 2026 acceptance (D8; not executed in D6)

Record workspace, Abaqus version, session ID, start/finish time, command IDs,
status/result files and observed output for each case. Use scratch models/jobs.

1. IPC/session: start one consumer; attempt a second and verify rejection;
   crash/restart and verify ownership release. Run a long `submit_job`, queue B/C,
   check both complete once in order. Time out a caller during execution, then
   record whether work continues, whether a late result is retained, and how a
   retry avoids duplicate execution.
2. Startup: launch a fresh bridge and require an actual ping before success.
   Open a normal CAE window alongside launcher CAE; verify session ownership and
   that status/ping cannot be mixed across the two.
3. Output/API: build two **named** contact interactions; request CPRESS/COPEN,
   map each per-interaction key explicitly, compare RF with contact outputs as
   separate quantities. Exercise field versus history requests, E/LE/PEEQ
   availability, Density tuple and Gravity region. Re-run any retained
   `StaticStep` / `verifyMesh` calls after D7.
4. Screenshots: capture PNG, SVG, TIFF and TIF; inspect actual bytes, extension,
   MIME/format report and requested dimensions where supported. Request an
   unsupported format and require a clear failure. Capture twice under a fixed
   clock to confirm unique results.

## Manual Doubao Work acceptance (D8; not executed in D6)

`DOUBAO_INTEGRATION = UNVERIFIED` until every applicable UI item is observed.
Do not save or overwrite product configuration during D6.

1. Locate Skill import entry and record accepted artifact type (zip/folder/file).
   Import package with `SKILL.md` at its root; open every linked reference.
   Re-import an upgraded package and record replacement/version behavior.
2. Locate custom connector entry, select STDIO, enter command
   `<repo>\.venv\Scripts\python.exe`, argument `<repo>\mcp_server.py`, and
   `ABAQUS_MCP_HOME=<repo>\mcp_home`; record working-directory requirement.
3. Exercise absolute Windows paths including spaces and Chinese characters.
   Enable/restart connector, discover tools and invoke ping. A connected MCP
   host alone is not `BRIDGE_READY`.
4. Restart the Abaqus bridge, then restart or reconnect the connector and
   verify fresh tool discovery and ping against the new session.

## Determinism boundary

The repository has no D7 canonical config reader or session/claim API, so
legacy config migration and cross-session ownership are acceptance contracts
against current entry points. D6.1 exercises the actual `install.bat` and
`start_abaqus_agent.bat` boundaries with fake downstream processes in isolated
archive copies. An exact Doubao import artifact format, Abaqus CAE output APIs and
interpreter/version compatibility beyond locally installed candidates require
separate D8/platform verification. No fake Abaqus solver is used.

## D6.1 contract correction

- The passing filename checks use the ID generated by the client and MCP
  server. Full 32-character UUID4 hex is a separate expected-fail target; no
  passing check blesses the current eight-character truncation.
- Claimed timeout checks require an **unknown/may continue** outcome. They do
  not demand execution cancellation or immediate deletion of a late result.
- Readiness tests distinguish status X/ping X, X/Y and legacy sessionless
  status; fake ping results carry explicit `session_id` values.
- One fake Abaqus candidate may be selected; multiple candidates and command
  strings with unexpected arguments are expected-fail targets.
- README, portable public instructions, local RUNBOOK provenance and all four
  public installer entry documents have explicit tests.
- Windows BAT tests cover spaces, Chinese text, parentheses and `&` using
  isolated archive copies, disposable venvs without pip, and fake downstream
  executables. They never invoke Abaqus or user configuration.
- Passing tests that required partial final-path JSON retries or merely
  exercised JSON fixture parsing were removed. Atomic publish and configuration
  behavior remain target contracts.
