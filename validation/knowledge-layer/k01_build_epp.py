# Kernel script: build EPP uniaxial compression micro-test.
import os, json
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from abaqus import *
from abaqusConstants import *
import regionToolset
import mesh
M = 'EppCompress'; Jb = 'EppJob'
if M in mdb.models: del mdb.models[M]
if Jb in mdb.jobs: del mdb.jobs[Jb]
m = mdb.Model(name=M)
s = m.ConstrainedSketch(name='__p__', sheetSize=50.0)
s.rectangle((0.0, 0.0), (10.0, 10.0))
p = m.Part(name='Block', dimensionality=THREE_D, type=DEFORMABLE_BODY)
p.BaseSolidExtrude(sketch=s, depth=10.0)
del m.sketches['__p__']
# EPP: E=210000 MPa, nu=0.3, yield=250 MPa. First plastic point MUST be (250.0, 0.0).
mat = m.Material(name='SteelEPP')
mat.Elastic(table=((210000.0, 0.3),))
mat.Plastic(table=((250.0, 0.0), (250.0, 0.5)))
m.HomogeneousSolidSection(name='Sec', material='SteelEPP', thickness=None)
p.SectionAssignment(region=regionToolset.Region(cells=p.cells), sectionName='Sec',
    offset=0.0, offsetType=MIDDLE_SURFACE, offsetField='', thicknessAssignment=FROM_SECTION)
a = m.rootAssembly; a.DatumCsysByDefault(CARTESIAN)
a.Instance(name='B-1', part=p, dependent=ON)
m.StaticStep(name='S1', previous='Initial', timePeriod=1.0, nlgeom=ON,
    initialInc=0.05, minInc=1e-8, maxInc=0.1, maxNumInc=1000)
m.FieldOutputRequest(name='F1', createStepName='S1',
    variables=('S', 'E', 'PEEQ', 'U', 'RF'), frequency=5)
bot = a.Set(faces=a.instances['B-1'].faces.getByBoundingBox(-0.1,-0.1,-0.1, 10.1,10.1,0.1), name='FIXED')
m.EncastreBC(name='Base', createStepName='Initial', region=bot)
top = a.Set(faces=a.instances['B-1'].faces.getByBoundingBox(-0.1,-0.1,9.9, 10.1,10.1,10.1), name='TOP')
m.DisplacementBC(name='Press', createStepName='S1', region=top, u3=-0.5)
p.setMeshControls(regions=p.cells, elemShape=HEX, technique=STRUCTURED)
et = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD, hourglassControl=ENHANCED)
p.setElementType(regions=(p.cells,), elemTypes=(et,))
p.seedPart(size=2.0); p.generateMesh()
mdb.Job(name=Jb, model=M, type=ANALYSIS, numCpus=1, numDomains=1)
print(json.dumps({'built': True, 'nelem': len(p.elements), 'nnode': len(p.nodes)}))
