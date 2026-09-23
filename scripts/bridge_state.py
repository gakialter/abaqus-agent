# -*- coding: utf-8 -*-
"""Shared readiness predicate for launcher and doctor."""
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MCP_HOME = REPO / 'mcp_home'
STATUS_FILE = MCP_HOME / 'status.json'


def _read(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _locked():
    path = MCP_HOME / '.owner.lock'
    if not path.exists():
        return False
    import msvcrt
    with open(path, 'a+b') as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        return False


def state(ping_timeout=3):
    if not _locked():
        return 'STOPPED'
    owner = _read(MCP_HOME / 'owner.json')
    status = _read(STATUS_FILE)
    sid = owner.get('session_id')
    stamp = status.get('timestamp')
    if (not isinstance(sid, str) or len(sid) != 32 or
            status.get('status') != 'running' or status.get('session_id') != sid or
            not isinstance(stamp, (int, float)) or not 0 <= time.time() - stamp <= 15):
        return 'BUSY_UNRESPONSIVE'
    os.environ['ABAQUS_MCP_HOME'] = str(MCP_HOME)
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    try:
        import client
        pong = client.send('ping', timeout=ping_timeout)
        if pong.get('success') and pong.get('data', {}).get('session_id') == sid:
            return 'BRIDGE_READY'
    except Exception:
        pass
    return 'BUSY_UNRESPONSIVE'


def main():
    print(state())


if __name__ == '__main__':
    main()
