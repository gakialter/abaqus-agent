# -*- coding: utf-8 -*-
"""Tiny file-based driver: send a kernel script file or submit a job through the live bridge.
Usage:
  python ksend.py script <kernel_script.py> [timeout]
  python ksend.py submit <job_name> [timeout]
Prints the raw JSON result from the bridge.
"""
import sys, os, json
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from client import send  # noqa: E402

kind = sys.argv[1]
if kind == 'script':
    path = sys.argv[2]
    to = float(sys.argv[3]) if len(sys.argv) > 3 else 120.0
    with open(path, 'r', encoding='utf-8') as f:
        script = f.read()
    res = send('execute_script', script=script, timeout=to)
elif kind == 'submit':
    jn = sys.argv[2]
    to = float(sys.argv[3]) if len(sys.argv) > 3 else 600.0
    res = send('submit_job', job_name=jn, timeout=to)
else:
    raise SystemExit('unknown kind: ' + kind)
print(json.dumps(res, ensure_ascii=False))
