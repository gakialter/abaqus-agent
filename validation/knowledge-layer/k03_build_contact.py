# Kernel script: rigid flat platen + deformable cube, frictionless contact. v2
import os, json
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from abaqus import *
from abaqusConstants import *
import regionToolset
import mesh
M = 'ContactPress'; Jb = 'ContactJob'
if M in mdb.models: del mdb.models[M]
if Jb in mdb.jobs: del mdb.jobs[Jb]
m = mdb.Model(name=M)

# --- Deformable cube: x[0,10] y[0,10] z[0,10], elastic ---
s = m.ConstrainedSketch(name='__c__', sheetSize=50.0)
s.rectangle((0.0, 0.0), (10.0, 10.0))
c = m.Part(name='Cube', dimensionality=THREE_D, type=DEFORMABLE_BODY)
c.BaseSolidExtrude(sketch=s, depth=10.0)
del m.sketches['__c__']
mat = m.Material(name='Steel')
mat.Elastic(table=((210000.0, 0.3),))
m.HomogeneousSolidSection(name='SecC', material='Steel', thickness=None)
c.SectionAssignment(region=regionToolset.Region(cells=c.cells), sectionName='SecC',
    offset=0.0, offsetType=MIDDLE_SURFACE, offsetField='', thicknessAssignment=FROM_SECTION)

# --- Discrete rigid flat platen (planar shell) in XY plane z=0 ---
s2 = m.ConstrainedSketch(name='__p__', sheetSize=50.0)
s2.rectangle((-15.0, -15.0), (15.0, 15.0))
p = m.Part(name='Platen', dimensionality=THREE_D, type=DISCRETE_RIGID_SURFACE)
p.BaseShell(sketch=s2)
del m.sketches['__p__']

a = m.rootAssembly; a.DatumCsysByDefault(CARTESIAN)
a.Instance(name='C-1', part=c, dependent=ON)
a.Instance(name='P-1', part=p, dependent=ON)

rp = a.ReferencePoint(point=(0.0, 0.0, 0.0))
rpid = a.referencePoints[rp.id]
rpSet = a.Set(name='PlatenRP', referencePoints=(rpid,))
bodySet = a.Set(name='PlatenBody', faces=a.instances['P-1'].faces)
m.RigidBody(name='PlatenRB', refPointRegion=rpSet, bodyRegion=bodySet)
m.EncastreBC(name='FixRP', createStepName='Initial', region=rpSet)

m.StaticStep(name='S1', previous='Initial', timePeriod=1.0, nlgeom=ON,
    initialInc=0.05, minInc=1e-8, maxInc=0.1, maxNumInc=1000)
m.FieldOutputRequest(name='F1', createStepName='S1',
    variables=('S', 'U', 'RF', 'CSTRESS'), frequency=5)

# Cube: driven top, symmetry to stop x/y rigid drift
top = a.Set(faces=a.instances['C-1'].faces.getByBoundingBox(-0.1,-0.1,9.9, 10.1,10.1,10.1), name='TOP')
m.DisplacementBC(name='Press', createStepName='S1', region=top, u3=-0.2)
x0 = a.Set(faces=a.instances['C-1'].faces.getByBoundingBox(-0.1,-0.1,-0.1, 0.1,10.1,10.1), name='X0')
m.DisplacementBC(name='FixX', createStepName='Initial', region=x0, u1=0.0)
y0 = a.Set(faces=a.instances['C-1'].faces.getByBoundingBox(-0.1,-0.1,-0.1, 10.1,0.1,10.1), name='Y0')
m.DisplacementBC(name='FixY', createStepName='Initial', region=y0, u2=0.0)

# Frictionless normal contact: cube bottom (slave) -> rigid platen (master)
m.ContactProperty(name='IntProp')
m.interactionProperties['IntProp'].NormalBehavior(allowSeparation=ON)
slave = a.Surface(name='CubeBottom',
    side1Faces=a.instances['C-1'].faces.getByBoundingBox(-0.1,-0.1,-0.1, 10.1,10.1,0.1))
master = a.Surface(name='PlatenTop',
    side1Faces=a.instances['P-1'].faces.getByBoundingBox(-15.1,-15.1,-0.1, 15.1,15.1,0.1))
m.SurfaceToSurfaceContactStd(name='Cont1', createStepName='S1',
    main=master, secondary=slave, sliding=FINITE, interactionProperty='IntProp')

c.setMeshControls(regions=c.cells, elemShape=HEX, technique=STRUCTURED)
et = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD, hourglassControl=ENHANCED)
c.setElementType(regions=(c.cells,), elemTypes=(et,))
c.seedPart(size=2.0); c.generateMesh()
# discrete rigid platen MUST be meshed -> creates R3D4 elements used by RigidBody + contact surface
p.seedPart(size=3.0); p.generateMesh()
mdb.Job(name=Jb, model=M, type=ANALYSIS, numCpus=1, numDomains=1)
print(json.dumps({'built': True, 'nelem': len(c.elements)}))
