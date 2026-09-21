# -*- coding: utf-8 -*-
"""
Abaqus-side launcher. Runs INSIDE Abaqus/CAE kernel via:
    abaqus cae script="<this file>"

setup_abaqus_agent.py fills __WORKSPACE__ at install time. It imports the MCP
plugin, sets the isolated work directory, and starts a blocking poll loop
(main-thread = most reliable). No Abaqus install-dir or License files touched.
"""
import os
import sys

WORKSPACE = r"__WORKSPACE__"
WORKDIR = os.path.join(WORKSPACE, "work")

os.environ.setdefault("ABAQUS_MCP_HOME", os.path.join(WORKSPACE, "mcp_home"))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

os.makedirs(WORKDIR, exist_ok=True)
os.chdir(WORKDIR)

import abaqus_mcp_plugin as plugin  # noqa: E402

# Blocking loop: poll_once runs on the main kernel thread (recommended).
plugin.mcp_loop()
