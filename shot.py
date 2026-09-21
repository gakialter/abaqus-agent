# -*- coding: utf-8 -*-
"""Capture an ODB von-Mises contour screenshot via execute_script."""
import base64
import sys
from pathlib import Path
sys.path.insert(0, r"C:\Users\27296\Desktop\abaqus-agent")
from client import send  # noqa: E402

WORK = Path(r"C:\Users\27296\Desktop\abaqus-agent")
ODB = str(WORK / "work" / "CantileverJob.odb")
OUT = str(WORK / "work" / "viewport_cantilever")

SHOT_SCRIPT = r'''
from abaqus import session
from abaqusConstants import PNG, CONTOURS_ON_DEF, INVARIANT, ELEMENT_NODAL
odb_path = r"__ODB__"
out_base = r"__OUT__"
odb = session.openOdb(odb_path, readOnly=True)
vp = session.viewports[session.currentViewportName]
vp.setValues(displayedObject=odb)
vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
try:
    vp.odbDisplay.setPrimaryVariable(outputPosition=ELEMENT_NODAL,
                                     variableLabel='S',
                                     refinement=INVARIANT)
except Exception as e:
    print('var warn: ' + str(e))
session.printToFile(fileName=out_base, format=PNG, canvasObjects=(vp,))
print('SHOT_OK')
'''.replace("__ODB__", ODB).replace("__OUT__", OUT)

r = send("execute_script", timeout=90.0, script=SHOT_SCRIPT)
print("success:", r.get("success"))
print("output:", r.get("output"))
if not r.get("success"):
    print("error:", r.get("error"), r.get("traceback"))

png = WORK / "work" / "viewport_cantilever.png"
if png.exists():
    print("PNG:", png, png.stat().st_size, "bytes")
else:
    print("PNG not found at", png)
