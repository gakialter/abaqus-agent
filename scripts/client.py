# -*- coding: utf-8 -*-
"""
Direct file-IPC driver for the Abaqus MCP plugin (no MCP stdio layer).

Talks to the Abaqus/CAE kernel plugin by writing command JSON files into
$ABAQUS_MCP_HOME/commands/ and polling $ABAQUS_MCP_HOME/results/. The real
mcp_server.py uses the exact same protocol for MCP clients.

Usage:
    from client import send, status
    send("ping")
    send("execute_script", script="print(1+1)", timeout=60)
"""
import json
import os
import time
import uuid
from pathlib import Path

MCP_HOME = Path(os.environ.get(
    "ABAQUS_MCP_HOME",
    str(Path.home() / "abaqus-agent" / "mcp_home"),
))
COMMANDS_DIR = MCP_HOME / "commands"
RESULTS_DIR = MCP_HOME / "results"
STATUS_FILE = MCP_HOME / "status.json"


def send(cmd_type, timeout=30.0, **kwargs):
    """Write one command and block until its result file appears."""
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    cmd_id = uuid.uuid4().hex[:8]
    command = {"id": cmd_id, "type": cmd_type, "timestamp": time.time(), **kwargs}
    cmd_path = COMMANDS_DIR / f"cmd_{cmd_id}.json"
    result_path = RESULTS_DIR / f"{cmd_id}.json"
    with open(cmd_path, "w", encoding="utf-8") as f:
        json.dump(command, f)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if result_path.exists():
            try:
                with open(result_path, "r", encoding="utf-8") as f:
                    result = json.load(f)
                result_path.unlink(missing_ok=True)
                return result
            except Exception:
                pass
        time.sleep(0.05)
    cmd_path.unlink(missing_ok=True)
    return {"success": False, "error": f"Timeout after {timeout}s (cmd={cmd_type})"}


def status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("STATUS:", json.dumps(status(), ensure_ascii=False))
    print("PING:", json.dumps(send("ping", timeout=15.0), ensure_ascii=False))
