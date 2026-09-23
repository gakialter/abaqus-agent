# -*- coding: utf-8 -*-
"""
Stop Abaqus MCP loop.

Run this script from any Python environment to signal the MCP plugin to stop.
Respects the ABAQUS_MCP_HOME environment variable.
"""
import json
import os
from pathlib import Path

MCP_HOME = Path(os.environ.get('ABAQUS_MCP_HOME',
                               str(Path(__file__).resolve().parent / 'mcp_home')))
owner = json.loads((MCP_HOME / 'owner.json').read_text(encoding='utf-8'))
session_id = owner['session_id']
if not isinstance(session_id, str) or len(session_id) != 32:
    raise SystemExit('Invalid owner session')
from client import send
result = send('stop', timeout=10, session_id=session_id)
print(json.dumps(result, ensure_ascii=False))
raise SystemExit(0 if result.get('success') else 1)
