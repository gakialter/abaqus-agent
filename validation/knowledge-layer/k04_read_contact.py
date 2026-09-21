# Kernel: read ContactJob.odb -> CPRESS + contact RF.
import os, json
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from odbAccess import openOdb
odb = openOdb('ContactJob.odb', readOnly=True)
step = odb.steps['S1']
fr = step.frames[-1]
out = {'nframes': len(step.frames), 'frame_time': fr.frameValue,
       'fields': list(fr.fieldOutputs.keys())}
# CPRESS is the first component of CSTRESS (contact pressure)
try:
    cs = fr.fieldOutputs['CSTRESS']
    vals = cs.values
    maxcp = 0.0; ncontact = 0
    for v in vals:
        # CPRESS is component 0 of CSTRESS; magnitude
        cpress = abs(v.data[0]) if len(v.data) > 0 else 0.0
        if cpress > 1e-6: ncontact += 1
        if cpress > maxcp: maxcp = cpress
    out['max_CPRESS_MPa'] = round(float(maxcp), 3)
    out['n_active_contact_nodes'] = ncontact
except Exception as e:
    out['cstress_error'] = repr(e)
# Reaction on driven TOP set
try:
    rf = fr.fieldOutputs['RF']
    reg = odb.rootAssembly.nodeSets['TOP']
    rfs = rf.getSubset(region=reg)
    tot3 = 0.0
    for v in rfs.values:
        tot3 += v.data[2]
    out['top_RF3_N'] = round(tot3, 2)
except Exception as e:
    out['rf_error'] = repr(e)
# Platen RP reaction (should balance)
try:
    rp = odb.rootAssembly.nodeSets['PLatenRP']
except Exception:
    rp = None
odb.close()
print(json.dumps(out))
