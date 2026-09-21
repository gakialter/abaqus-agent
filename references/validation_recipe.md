# 最小验证配方：3D 悬臂梁 → Job → ODB → 截图

用这套脚本确认"Agent 真的控制了 Abaqus"，而不只是生成脚本。
所有内容通过 `client.send("execute_script", script=...)` 在 Abaqus 内核里跑。

## 模型参数
100×10×10 mm，Steel（E=210000 MPa, ν=0.3），x=0 端 Encastre，自由端 4 个角节点各 -50 N (Z)，
Static General。网格 seed=2 mm。

## 1) 建模脚本（在 Abaqus 内跑）
```python
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
```

## 2) 提交并等待
```python
r = send("submit_job", timeout=600.0, job_name="CantileverJob")
# expect r['data']['status'] == 'COMPLETED'
```

## 3) 读 ODB 提数（在 Abaqus 内跑，结果 print 回来）
```python
from odbAccess import openOdb
import json
odb = openOdb(r"<work>\CantileverJob.odb", readOnly=True)
fr = odb.steps['Step-1'].frames[-1]
U = fr.fieldOutputs['U']; dmax = 0.0
for v in U.values:
    d = v.data; dmax = max(dmax, (d[0]**2+d[1]**2+d[2]**2)**0.5)
S = fr.fieldOutputs['S']; smax = max((v.mises for v in S.values), default=0.0)
odb.close()
print('RESULT ' + json.dumps({'max_disp': round(dmax,4), 'max_mises': round(smax,2)}))
```
手算参考：tip 位移≈0.38 mm，固定端 Mises≈100–120 MPa。量级对得上即链路正确。

## 4) 视口云图截图（在 Abaqus 内跑）
```python
from abaqus import session
from abaqusConstants import PNG, CONTOURS_ON_DEF, ELEMENT_NODAL, INVARIANT
odb = session.openOdb(r"<work>\CantileverJob.odb", readOnly=True)
vp = session.viewports[session.currentViewportName]
vp.setValues(displayedObject=odb)
vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
try: vp.odbDisplay.setPrimaryVariable(outputPosition=ELEMENT_NODAL, variableLabel='S', refinement=INVARIANT)
except Exception: pass
session.printToFile(fileName=r"<work>\viewport", format=PNG, canvasObjects=(vp,))
```
生成 `<work>\viewport.png`。注意 printToFile 会自动加扩展名，fileName 不要带 `.png`。

## 工具清单（mcp_server 也暴露同样命令）
`ping / check_abaqus_connection / execute_script / get_model_info / list_jobs /
submit_job / get_odb_info / get_viewport_image`。
