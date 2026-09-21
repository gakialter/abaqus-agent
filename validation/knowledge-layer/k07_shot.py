# Kernel: viewport CPRESS contour on ContactJob.odb -> PNG.
import os
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from abaqus import session
from abaqusConstants import PNG, CONTOURS_ON_UNDEF, ELEMENT_NODAL
odb = session.openOdb('ContactJob.odb', readOnly=True)
vp = session.viewports[session.currentViewportName]
vp.setValues(displayedObject=odb)
vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_UNDEF,))
cp_key = [k for k in odb.steps['S1'].frames[-1].fieldOutputs.keys() if k.startswith('CPRESS')][0]
try:
    vp.odbDisplay.setPrimaryVariable(outputPosition=ELEMENT_NODAL,
        variableLabel=cp_key.split()[0],
        refinement=INVARIANT)
except Exception as e:
    print('vpwarn', e)
session.printToFile(fileName='cpress_contour', format=PNG, canvasObjects=(vp,))
print('SHOT_OK')
