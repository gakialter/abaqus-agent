# Kernel: read CPRESS from the namespaced contact field.
import os, json
os.chdir(r"C:\Users\27296\Desktop\abaqus-agent\validation\knowledge-layer\work")
from odbAccess import openOdb
odb = openOdb('ContactJob.odb', readOnly=True)
fr = odb.steps['S1'].frames[-1]
out = {}
cp_key = [k for k in fr.fieldOutputs.keys() if k.startswith('CPRESS')]
co_key = [k for k in fr.fieldOutputs.keys() if k.startswith('COPEN')]
if cp_key:
    cp = fr.fieldOutputs[cp_key[0]]
    vals = cp.values
    maxcp = max((abs(v.data) for v in vals), default=0.0)
    n_on = sum(1 for v in vals if abs(v.data) > 1e-6)
    out['CPRESS_key'] = cp_key[0]
    out['max_CPRESS_MPa'] = round(float(maxcp), 2)
    out['n_contact_pressure_nodes'] = n_on
    out['expected_contact_MPa'] = 4200.0  # E*(0.2/10)*100 /100
if co_key:
    co = fr.fieldOutputs[co_key[0]]
    maxopen = max((abs(v.data) for v in co.values), default=0.0)
    out['max_COPEN_mm'] = round(float(maxopen), 5)
odb.close()
print(json.dumps(out))
