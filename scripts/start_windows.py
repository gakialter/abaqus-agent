"""Launch the configured Abaqus command and wait for session verified IPC."""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bridge_state
import local_config
import runtime_detection

REPO = Path(__file__).resolve().parent.parent


def main():
    try:
        cfg, _ = local_config.load_or_migrate(REPO, write=False)
        if not cfg:
            raise ValueError('No Abaqus config. Run install.bat first')
        command = runtime_detection.validate_abaqus_cmd(cfg['ABAQUS_CMD'])
    except (OSError, ValueError, KeyError) as exc:
        print('[!!] Config: ' + str(exc))
        return 1
    before = bridge_state.state()
    if before == 'BRIDGE_READY':
        print('BRIDGE_READY: existing session')
        return 0
    if before != 'STOPPED':
        print('BUSY/UNRESPONSIVE: owner exists; second session was not launched')
        return 1
    env = os.environ.copy()
    env['ABAQUS_MCP_HOME'] = str(REPO / 'mcp_home')
    script = str(REPO / 'abaqus_start_mcp.py')
    (REPO / 'work').mkdir(exist_ok=True)
    try:
        subprocess.Popen([command, 'cae', 'script=' + script], cwd=str(REPO / 'work'), env=env,
                         creationflags=getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
    except OSError as exc:
        print('[!!] Launch failed: ' + str(exc))
        return 1
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        state = bridge_state.state()
        if state == 'BRIDGE_READY':
            print('BRIDGE_READY: real ping matched owner and status session')
            return 0
        time.sleep(2)
    print('[!!] Bridge did not become ready within 90 seconds: ' + bridge_state.state())
    return 1


if __name__ == '__main__':
    sys.exit(main())
