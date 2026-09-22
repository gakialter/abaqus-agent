# -*- coding: utf-8 -*-
"""
Abaqus-side launcher. Run INSIDE Abaqus/CAE kernel via:
    abaqus cae script="<repo>/abaqus_start_mcp.py"

It imports the MCP plugin, sets the isolated work directory, and starts the
polling loop (blocking, main-thread mode = most reliable per plugin README).

Workspace resolution is portable and does NOT rely on ``__file__`` (Abaqus does
not define ``__file__`` for scripts run via ``cae script=``). start_abaqus_agent.bat
sets ABAQUS_MCP_HOME to <workspace>\\mcp_home; we derive the workspace from that.
If launched manually without the env var, fall back to the current directory.
No Abaqus install-directory or License files are touched.
"""
import os
import sys

_MCP_HOME = os.environ.get("ABAQUS_MCP_HOME", "").strip()
WORKSPACE = os.path.dirname(_MCP_HOME) if _MCP_HOME else os.getcwd()
WORKDIR = os.path.join(WORKSPACE, "work")

# Make sure the plugin module is importable and IPC home is isolated.
os.environ.setdefault("ABAQUS_MCP_HOME", os.path.join(WORKSPACE, "mcp_home"))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

os.makedirs(WORKDIR, exist_ok=True)
os.chdir(WORKDIR)

import abaqus_mcp_plugin as plugin  # noqa: E402

# Blocking loop: poll_once runs on the main kernel thread (recommended).
plugin.mcp_loop()
