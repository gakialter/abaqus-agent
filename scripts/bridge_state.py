# -*- coding: utf-8 -*-
"""
Bridge state probe used by start_abaqus_agent.bat.

Prints RUNNING only when the bridge is TRULY communicable:
    status.json status == "running"
    AND (the pid is alive OR the timestamp is fresh)
    AND a real client ping round-trip succeeds.
Otherwise prints STOPPED.

A stale status.json left by a previous (crashed) Abaqus is NOT enough on its
own: we always require an actual ping so the launcher can recover/restart
instead of skipping startup.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
MCP_HOME = REPO / "mcp_home"
STATUS_FILE = MCP_HOME / "status.json"


def _pid_alive(pid):
    if not pid:
        return False
    try:
        out = subprocess.run(["tasklist", "/FI", "PID eq " + str(pid)],
                             capture_output=True, text=True).stdout
        return str(pid) in out
    except Exception:
        return False


def main():
    st = {}
    if STATUS_FILE.exists():
        try:
            st = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except Exception:
            st = {}

    pid = st.get("pid")
    alive = _pid_alive(pid)
    fresh = (time.time() - float(st.get("timestamp", 0))) < 15
    claimed = st.get("status") == "running" and (alive or fresh)

    ping_ok = False
    if claimed:
        os.environ["ABAQUS_MCP_HOME"] = str(MCP_HOME)
        if str(REPO) not in sys.path:
            sys.path.insert(0, str(REPO))
        try:
            import client
            ping_ok = bool(client.send("ping", timeout=10).get("success"))
        except Exception:
            ping_ok = False

    print("RUNNING" if (claimed and ping_ok) else "STOPPED")


if __name__ == "__main__":
    main()
