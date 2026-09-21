# Kernel: deliberately under-constrained cube (load, NO BC) -> expect singular abort.
import os, json
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from abaqus import *
from abaqusConstants import *
import regionToolset
import mesh
M = 'UnderCon'; Jb = 'UnderConJob'
if M in mdb.models: del mdb.models[M]
if Jb in mdb.jobs: del mdb.jobs[Jb]
m = mdb.Model(name=M)
s = m.ConstrainedSketch(name='__p__', sheetSize=50.0)
s.rectangle((0.0, 0.0), (10.0, 10.0))
p = m.Part(name='Blk', dimensionality=THREE_D, type=DEFORMABLE_BODY)
p.BaseSolidExtrude(sketch=s, depth=10.0)
del m.sketches['__p__']
mat = m.Material(name='Steel'); mat.Elastic(table=((210000.0, 0.3),))
m.HomogeneousSolidSection(name='Sec', material='Steel', thickness=None)
p.SectionAssignment(region=regionToolset.Region(cells=p.cells), sectionName='Sec',
    offset=0.0, offsetType=MIDDLE_SURFACE, offsetField='', thicknessAssignment=FROM_SECTION)
a = m.rootAssembly; a.DatumCsysByDefault(CARTESIAN)
a.Instance(name='B-1', part=p, dependent=ON)
m.StaticStep(name='S1', previous='Initial', timePeriod=1.0)
m.FieldOutputRequest(name='F1', createStepName='S1', variables=('U',), frequency=1)
# NO boundary condition at all -> rigid body modes unconstrained
m.ConcentratedForce(name='F', createStepName='S1',
    region=a.Set(name='CORNER', vertices=a.instances['B-1'].vertices.getByBoundingBox(9,-1,-1,11,11,11)), cf3=-1000.0)
p.seedPart(size=5.0); p.generateMesh()
mdb.Job(name=Jb, model=M, type=ANALYSIS, numCpus=1, numDomains=1)
print(json.dumps({'built': True, 'nelem': len(p.elements)}))
