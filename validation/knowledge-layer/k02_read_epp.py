# Kernel script: read EppJob.odb -> RF balance + PEEQ.
import os, json
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from odbAccess import openOdb
odb = openOdb('EppJob.odb', readOnly=True)
step = odb.steps['S1']
fr = step.frames[-1]
out = {'step': 'S1', 'nframes': len(step.frames), 'frame_time': fr.frameValue}
# Reaction force on FIXED set (assembly-level node set)
try:
    rf = fr.fieldOutputs['RF']
    # FIXED set created at assembly root level
    reg = odb.rootAssembly.nodeSets['FIXED']
    rfs = rf.getSubset(region=reg)
    tot = [0.0, 0.0, 0.0]
    n = 0
    for v in rfs.values:
        n += 1
        for i in range(3):
            tot[i] += v.data[i]
    out['rf_nodes'] = n
    out['RF_total'] = [round(x, 3) for x in tot]
    out['RF3_mag'] = round(abs(tot[2]), 3)
except Exception as e:
    out['rf_error'] = repr(e)
# PEEQ
try:
    peeq = fr.fieldOutputs['PEEQ']
    maxp = max((v.data for v in peeq.values), default=0.0)
    out['max_PEEQ'] = round(float(maxp), 6)
except Exception as e:
    out['peeq_error'] = repr(e)
# Max mises via S
try:
    s = fr.fieldOutputs['S']
    mx = 0.0
    for v in s.values:
        m = v.mises
        if m > mx: mx = m
    out['max_mises'] = round(float(mx), 3)
except Exception as e:
    out['s_error'] = repr(e)
# analytical: sigma_y * area = 250 MPa * 100 mm^2 = 25000 N
out['expected_RF3_plateau'] = 25000.0
if 'RF3_mag' in out:
    out['rf_error_pct'] = round(abs(out['RF3_mag'] - 25000.0) / 25000.0 * 100.0, 2)
odb.close()
print(json.dumps(out))
