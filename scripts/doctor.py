"""Read-only installation, bridge and external integration diagnostics."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bootstrap_windows
import bridge_state
import local_config
import runtime_detection

REPO = Path(__file__).resolve().parent.parent


def check_venv_py():
    path = REPO / '.venv' / 'Scripts' / 'python.exe'
    return path if path.is_file() else None


def main():
    faults = []
    missing = bootstrap_windows.verify_repo_files()
    if missing:
        faults.append('missing source: ' + ', '.join(missing))
    venv_py = check_venv_py()
    if venv_py is None or not bootstrap_windows.venv_is_ready(venv_py.parents[1]):
        faults.append('venv requires Python 3.11, mcp==1.30.0 and FastMCP')
    try:
        cfg, source = local_config.load_or_migrate(REPO, write=False)
        if not cfg:
            faults.append('Abaqus config missing')
        else:
            runtime_detection.validate_abaqus_cmd(cfg['ABAQUS_CMD'])
    except (OSError, ValueError, KeyError) as exc:
        faults.append('Abaqus config: ' + str(exc))
    if not (REPO / 'mcp_home').is_dir():
        faults.append('mcp_home missing')
    print('INSTALLED=' + ('true' if not faults else 'false'))
    for fault in faults:
        print(' - ' + fault)
    bridge = bridge_state.state() if (REPO / 'mcp_home').is_dir() else 'STOPPED'
    print('BRIDGE_READY=' + ('true' if bridge == 'BRIDGE_READY' else 'false') + ' (' + bridge + ')')
    print('INTEGRATION_READY=EXTERNAL/UNVERIFIED (requires real MCP host test)')
    return 0 if not faults and bridge == 'BRIDGE_READY' else 1


if __name__ == '__main__':
    sys.exit(main())
