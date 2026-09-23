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
import re
import tempfile
import time
import uuid
from pathlib import Path

# Single source of truth: <workspace>/mcp_home, where workspace = this file's dir.
# Override with the ABAQUS_MCP_HOME env var if needed.
MCP_HOME = Path(os.environ.get(
    "ABAQUS_MCP_HOME",
    str(Path(__file__).resolve().parent / "mcp_home"),
))
COMMANDS_DIR = MCP_HOME / "commands"
RESULTS_DIR = MCP_HOME / "results"
CLAIMS_DIR = MCP_HOME / "claims"
STATUS_FILE = MCP_HOME / "status.json"
_COMMAND_ID = re.compile(r"[0-9a-f]{32}\Z")


def _valid_command_id(value):
    return isinstance(value, str) and _COMMAND_ID.fullmatch(value) is not None


def _publish_command(path, command):
    """Publish a complete command only after its temporary file is closed."""
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".tmp-command-", delete=False) as f:
            temp_path = Path(f.name)
            json.dump(command, f)
            f.flush()
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def send(cmd_type, timeout=30.0, **kwargs):
    """Write one command and block until its result file appears."""
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CLAIMS_DIR.mkdir(parents=True, exist_ok=True)
    cmd_id = uuid.uuid4().hex
    if not _valid_command_id(cmd_id):
        raise ValueError("Invalid command ID")
    command = {"type": cmd_type, "timestamp": time.time(), **kwargs, "id": cmd_id}
    cmd_path = COMMANDS_DIR / f"cmd_{cmd_id}.json"
    result_path = RESULTS_DIR / f"{cmd_id}.json"
    _publish_command(cmd_path, command)
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
    # A rename to a private cancellation name proves that no worker claimed it.
    # If the source vanished, execution may already be underway or complete.
    cancelled = COMMANDS_DIR / (".cancelled-" + cmd_id)
    try:
        os.replace(cmd_path, cancelled)
    except OSError:
        state = "UNKNOWN_MAY_CONTINUE"
    else:
        cancelled.unlink(missing_ok=True)
        state = "CANCELLED_BEFORE_CLAIM"
    return {"success": False, "error": f"Timeout after {timeout}s (cmd={cmd_type})",
            "execution_state": state, "command_id": cmd_id}


def status():
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    print("STATUS:", json.dumps(status(), ensure_ascii=False))
    print("PING:", json.dumps(send("ping", timeout=15.0), ensure_ascii=False))
