# -*- coding: utf-8 -*-
"""Real E2E against Abaqus 2026. Writes validation/result.json."""
import base64, json, sys, time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, r"C:\Users\27296\Desktop\abaqus-agent")
from client import send, status  # noqa

LIVE = Path(r"C:\Users\27296\Desktop\abaqus-agent")
WORK = LIVE / "work"
VALDIR = LIVE / "validation"
VALDIR.mkdir(exist_ok=True)

BUILD = r'''
from abaqus import *
from abaqusConstants import *
import regionToolset
if 'BeamModel' in mdb.models: del mdb.models['BeamModel']
if 'CantileverJob' in mdb.jobs: del mdb.jobs['CantileverJob']
mdb.Model(name='BeamModel'); m = mdb.models['BeamModel']
s = m.ConstrainedSketch(name='__p__', sheetSize=200.0)
s.rectangle((0.0,-5.0),(100.0,5.0))
part = m.Part(name='Beam', dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=s, depth=10.0)
m.Material(name='Steel'); m.materials['Steel'].Elastic(table=((210000.0,0.3),))
m.HomogeneousSolidSection(name='S', material='Steel', thickness=None)
part.SectionAssignment(region=regionToolset.Region(cells=part.cells), sectionName='S',
    offset=0.0, offsetType=MIDDLE_SURFACE, offsetField='', thicknessAssignment=FROM_SECTION)
a = m.rootAssembly; a.DatumCsysByDefault(CARTESIAN)
a.Instance(name='B-1', part=part, dependent=ON)
m.StaticStep(name='Step-1', previous='Initial', timePeriod=1.0)
m.EncastreBC(name='Fix', createStepName='Initial',
    region=a.Set(faces=a.instances['B-1'].faces.getByBoundingBox(-1,-6,-1,1,6,11), name='F'))
m.ConcentratedForce(name='L', createStepName='Step-1',
    region=a.Set(vertices=a.instances['B-1'].vertices.getByBoundingBox(99,-6,-1,101,6,11), name='T'),
    cf3=-50.0)
part.seedPart(size=2.0); part.generateMesh()
mdb.Job(name='CantileverJob', model='BeamModel', type=ANALYSIS, numCpus=1, numDomains=1)
print('BUILD_OK')
'''

ODB = r'''
from odbAccess import openOdb
import json
odb = openOdb(r"__ODB__", readOnly=True)
fr = odb.steps['Step-1'].frames[-1]
dmax = 0.0
for v in fr.fieldOutputs['U'].values:
    d = v.data; dmax = max(dmax, (d[0]**2+d[1]**2+d[2]**2)**0.5)
smax = 0.0
for v in fr.fieldOutputs['S'].values:
    smax = max(smax, v.mises)
odb.close()
print('ODB_RESULT ' + json.dumps({'max_disp': round(dmax,5), 'max_mises': round(smax,3)}))
'''.replace("__ODB__", str(WORK / "CantileverJob.odb"))

CONTOUR = r'''
from abaqus import session
from abaqusConstants import PNG, CONTOURS_ON_DEF, ELEMENT_NODAL, INVARIANT
odb = session.openOdb(r"__ODB__", readOnly=True)
vp = session.viewports[session.currentViewportName]
vp.setValues(displayedObject=odb)
vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
try:
    vp.odbDisplay.setPrimaryVariable(outputPosition=ELEMENT_NODAL, variableLabel='S', refinement=INVARIANT)
except Exception as e:
    print('contour warn: ' + str(e))
print('CONTOUR_OK')
'''.replace("__ODB__", str(WORK / "CantileverJob.odb"))

result = {"timestamp": datetime.now(timezone.utc).isoformat()}
result["abaqus"] = "2026"
result["bridge_status_before"] = status()

# 1 ping
r = send("ping", timeout=15)
result["ping"] = r
assert r.get("success"), "ping failed: " + str(r)

# 2 build
r = send("execute_script", timeout=120, script=BUILD)
result["build_success"] = r.get("success")
result["build_output"] = r.get("output")
if not r.get("success"):
    result["build_error"] = r.get("error")
    result["build_trace"] = r.get("traceback")
    (VALDIR / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit("build failed")

# 3 submit
r = send("submit_job", timeout=600, job_name="CantileverJob")
result["submit"] = r
job_status = (r.get("data") or {}).get("status")
result["job_status"] = job_status
result["job_success_flag"] = r.get("success")

# 4 odb
r = send("execute_script", timeout=120, script=ODB)
result["odb_output"] = r.get("output")
result["odb_success"] = r.get("success")
od = None
for line in (r.get("output") or "").splitlines():
    if line.startswith("ODB_RESULT "):
        od = json.loads(line.split("ODB_RESULT ", 1)[1])
if od:
    result["max_disp"] = od["max_disp"]
    result["max_mises"] = od["max_mises"]

# 5 contour + screenshot via FIXED get_viewport_image
r = send("execute_script", timeout=60, script=CONTOUR)
result["contour_output"] = r.get("output")
r = send("get_viewport_image", timeout=60, viewport_name="", image_format="PNG")
result["viewport_success"] = r.get("success")
if r.get("success") and isinstance(r.get("data"), dict):
    b64 = r["data"].get("image_base64", "")
    png = VALDIR / "result_screenshot.png"
    png.write_bytes(base64.b64decode(b64))
    result["screenshot_path"] = str(png)
    result["screenshot_bytes"] = png.stat().st_size
else:
    result["viewport_error"] = r.get("error") or r.get("data")

# sanity vs beam theory: expect tip ~0.2-0.6 mm, mises ~80-140 MPa
ok = (job_status == "COMPLETED"
      and result.get("max_disp", 0) > 0.05
      and result.get("max_disp", 0) < 2.0
      and result.get("max_mises", 0) > 50
      and result.get("max_mises", 0) < 250
      and result.get("screenshot_bytes", 0) > 1000)
result["physics_sane"] = bool(ok)
result["overall_pass"] = bool(ok) and result.get("viewport_success")

(VALDIR / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))
print(json.dumps(result, indent=2, ensure_ascii=False))
