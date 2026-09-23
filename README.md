# abaqus-agent

File IPC bridge for local Abaqus/CAE 2026. External Python 3.11 uses `mcp==1.30.0` and stays separate from Abaqus Python. The Abaqus consumer runs the blocking `mcp_loop()`.

## Install and use

Download the ZIP, extract it to a writable location, then run `install.bat`, `doctor.bat`, and `start_abaqus_agent.bat` in that order. `doctor.bat` reports `INSTALLED`, `BRIDGE_READY`, and `INTEGRATION_READY` separately. Before startup, `INSTALLED=true` can coexist with `BRIDGE_READY=false`.

Import `SKILL.md` with its `references/` directory through the MCP host's supported Skill UI. Configure a local STDIO MCP connector with:

| Field | Value |
|---|---|
| command | `<repo>\.venv\Scripts\python.exe` |
| argument | `<repo>\mcp_server.py` |
| environment | `ABAQUS_MCP_HOME=<repo>\mcp_home` |

Verify tool discovery and a real ping from that host. Doubao Work integration remains **Unverified** until tested in its real UI. No hidden product directories are written by the installer.

The canonical config is `<repo>/.abaqus-agent.json` with only `schema_version: 1` and `ABAQUS_CMD`. The repo location determines venv, work and IPC paths. Old config files are read only as migration inputs and retained.

## Behavior

Commands are atomically published in `commands/`, atomically claimed into `claims/`, and results are atomically published in `results/`. One OS locked consumer owns an IPC home. A queued command can be cancelled before claim; a timeout after claim has unknown outcome and may leave a late result. Side-effecting commands are never retried automatically. There is no cross-publisher FIFO or exactly-once guarantee after a crash.

`submit_job` reporting Abaqus status `COMPLETED` proves solver completion only. Task completion requires the eight gates in [workflow](references/execution/workflow.md). RF is a force and CPRESS is a contact pressure; select the exact contact interaction/key and region. The historical elastic-plastic micro-test had local maximum PEEQ ~0.10; ~0.05064 was an unweighted arithmetic mean of field values, not a proven volume average. A reported RF ~27557 N has no established 0.5% analytical agreement. Historical 27683 N was a back-fit anti-example. See [errata](validation/knowledge-layer/ERRATA.md).

## References and license

[SKILL.md](SKILL.md) routes knowledge recipes. The [knowledge layer](references/execution/workflow.md) marks API evidence at recipe level. `execute_script` runs trusted Python in the Abaqus kernel; do not expose this bridge to the public internet. Abaqus and its license are not included. MIT; see [NOTICE](NOTICE.md).
