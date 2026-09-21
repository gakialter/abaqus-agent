# -*- coding: utf-8 -*-
"""
Abaqus-side launcher. Run INSIDE Abaqus/CAE kernel via:
    abaqus cae script="C:/Users/27296/Desktop/abaqus-agent/abaqus_start_mcp.py"

It imports the MCP plugin, sets the isolated work directory, and starts the
polling loop (blocking, main-thread mode = most reliable per plugin README).

No Abaqus install-directory or License files are touched.
"""
import os
import sys

WORKSPACE = r"C:\Users\27296\Desktop\abaqus-agent"
WORKDIR = os.path.join(WORKSPACE, "work")

# Make sure the plugin module is importable and IPC home is isolated.
os.environ.setdefault("ABAQUS_MCP_HOME", os.path.join(WORKSPACE, "mcp_home"))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

os.makedirs(WORKDIR, exist_ok=True)
os.chdir(WORKDIR)

import abaqus_mcp_plugin as plugin  # noqa: E402

# Blocking loop: runs poll_once on the main kernel thread (recommended).
plugin.mcp_loop()
