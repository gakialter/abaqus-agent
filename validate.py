# -*- coding: utf-8 -*-
"""End-to-end validation: build cantilever beam, submit job, read ODB, screenshot."""
import base64
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\27296\Desktop\abaqus-agent")
from client import send  # noqa: E402

WORK = Path(r"C:\Users\27296\Desktop\abaqus-agent")
WORKDIR = WORK / "work"
WORKDIR.mkdir(exist_ok=True)

BUILD_SCRIPT = r'''
from abaqus import *
from abaqusConstants import *
import regionToolset, os, json

# Clean any previous validation model/job
if 'BeamModel' in mdb.models.keys():
    del mdb.models['BeamModel']
if 'CantileverJob' in mdb.jobs.keys():
    del mdb.jobs['CantileverJob']

# Fresh model
mdb.Model(name='BeamModel')
m = mdb.models['BeamModel']

# Sketch: rectangle in X-Y, length 100 (X), width 10 (Y)
s = m.ConstrainedSketch(name='__profile__', sheetSize=200.0)
s.rectangle(point1=(0.0, -5.0), point2=(100.0, 5.0))
part = m.Part(name='Beam', dimensionality=THREE_D, type=DEFORMABLE_BODY)
part.BaseSolidExtrude(sketch=s, depth=10.0)   # extrude Z = height 10

# Material Steel
m.Material(name='Steel')
m.materials['Steel'].Elastic(table=((210000.0, 0.3),))

# Solid section + assignment
m.HomogeneousSolidSection(name='SolidSec', material='Steel', thickness=None)
region = regionToolset.Region(cells=part.cells)
part.SectionAssignment(region=region, sectionName='SolidSec', offset=0.0,
                       offsetType=MIDDLE_SURFACE, offsetField='',
                       thicknessAssignment=FROM_SECTION)

# Assembly instance
a = m.rootAssembly
a.DatumCsysByDefault(CARTESIAN)
a.Instance(name='Beam-1', part=part, dependent=ON)

# Static general step
m.StaticStep(name='Step-1', previous='Initial',
              description='Cantilever bending',
              timePeriod=1.0, initialInc=0.1, minInc=1e-5, maxInc=1.0)

# Encastre BC on the face at x=0 (6 float args, not a tuple)
fixed_face = a.instances['Beam-1'].faces.getByBoundingBox(
    -1.0, -6.0, -1.0, 1.0, 6.0, 11.0)
m.EncastreBC(name='Fix', createStepName='Initial',
             region=a.Set(faces=fixed_face, name='Fixed'))

# Concentrated transverse load (-Z) on the 4 free-end vertices (x~100)
tip_verts = a.instances['Beam-1'].vertices.getByBoundingBox(
    99.0, -6.0, -1.0, 101.0, 6.0, 11.0)
m.ConcentratedForce(name='TipLoad', createStepName='Step-1',
                    region=a.Set(vertices=tip_verts, name='Tip'),
                    cf3=-50.0)

# Mesh
part.seedPart(size=2.0, deviationFactor=0.1, minSizeFactor=0.1)
part.generateMesh()

# Job
mdb.Job(name='CantileverJob', model='BeamModel', description='agent validation',
        type=ANALYSIS, numCpus=1, numDomains=1,
        memory=50, memoryUnits=PERCENTAGE,
        explicitPrecision=SINGLE, nodalOutputPrecision=SINGLE,
        echoPrint=OFF, modelPrint=OFF, contactPrint=OFF, historyPrint=OFF)

print('BUILD_OK cells=%d nodes_approx' % len(part.cells))
'''

ODB_SCRIPT = r'''
from odbAccess import openOdb
import json, os
odb_path = r"C:\Users\27296\Desktop\abaqus-agent\work\CantileverJob.odb"
odb = openOdb(path=odb_path, readOnly=True)
step = odb.steps['Step-1']
frame = step.frames[-1]

U = frame.fieldOutputs['U']
max_mag = 0.0
for v in U.values:
    d = v.data
    mag = (d[0]*d[0] + d[1]*d[1] + d[2]*d[2]) ** 0.5
    if mag > max_mag:
        max_mag = mag

S = frame.fieldOutputs['S']
max_mises = 0.0
for v in S.values:
    if v.mises > max_mises:
        max_mises = v.mises
odb.close()
print('ODB_RESULT ' + json.dumps({'max_disp_mag': round(max_mag, 6),
                                 'max_vonMises': round(max_mises, 3)}))
'''


def main():
    print("=" * 60)
    print("[1/4] Building cantilever beam model ...")
    r = send("execute_script", timeout=120.0, script=BUILD_SCRIPT)
    print(" success:", r.get("success"))
    print(" output:", r.get("output"))
    if not r.get("success"):
        print(" ERROR:", r.get("error"), r.get("traceback"))
        return
    print("=" * 60)
    print("[2/4] Submitting CantileverJob and waiting for completion ...")
    r = send("submit_job", timeout=600.0, job_name="CantileverJob")
    print(" ", json.dumps(r, ensure_ascii=False))
    print("=" * 60)
    print("[3/4] Opening ODB and extracting max displacement / von Mises ...")
    r = send("execute_script", timeout=120.0, script=ODB_SCRIPT)
    print(" success:", r.get("success"))
    print(" output:", r.get("output"))
    if not r.get("success"):
        print(" ERROR:", r.get("error"), r.get("traceback"))
    print("=" * 60)
    print("[4/4] Capturing viewport screenshot ...")
    r = send("get_viewport_image", timeout=60.0, format="PNG")
    if r.get("success") and r.get("data", {}).get("image_base64"):
        b64 = r["data"]["image_base64"]
        img_path = WORK / "viewport_cantilever.png"
        img_path.write_bytes(base64.b64decode(b64))
        print(" screenshot saved:", img_path, "(%d bytes)" % img_path.stat().st_size)
    else:
        print(" screenshot failed:", json.dumps(r, ensure_ascii=False))
    print("=" * 60)
    print("DONE")


if __name__ == "__main__":
    main()
