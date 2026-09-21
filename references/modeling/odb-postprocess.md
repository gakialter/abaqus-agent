# ODB post-processing (in the live kernel)

> Status: extraction of U / RF / S / PEEQ / CPRESS confirmed on Abaqus 2026.

Run this **inside the kernel** via `execute_script` (the kernel already opened the job;
you can also `openOdb` read-only). Open `readOnly=True` whenever you only read.

## Navigate

```python
from odbAccess import openOdb
import json
odb = openOdb('<job>.odb', readOnly=True)
step = odb.steps['<step>']
fr = step.frames[-1]                 # last frame
print(list(fr.fieldOutputs.keys()))
odb.close()
```

## Common output keys (3D)

| Key | Meaning |
|-----|---------|
| `U` | nodal displacement vector |
| `RF` | nodal reaction force vector |
| `S` | stress tensor (S11,S22,S33,S12,S13,S23) |
| `PE`, `PEEQ` | plastic strain / equivalent plastic strain |
| `CPRESS   <slave>/<master>` | contact pressure (per-interaction key!) |
| `COPEN ...` | contact opening |

> **There is no `MISES` field in the ODB.** The viewer computes it. Compute it from `S`
> (below) — do not request `MISES` in FieldOutputRequest.

## Max displacement

```python
u = fr.fieldOutputs['U']
umax = max((v.data[0]**2 + v.data[1]**2 + v.data[2]**2)**0.5 for v in u.values)
```

## Mises stress from S

```python
s = fr.fieldOutputs['S']; smax = 0.0
for v in s.values:
    s11,s22,s33,s12,s13,s23 = v.data
    mises = (((s11-s22)**2+(s22-s33)**2+(s33-s11)**2
             +6*(s12**2+s13**2+s23**2))/2.0)**0.5
    smax = max(smax, mises)
```
(The odbAccess `v.mises` property also works for a quick read.)

## Reaction force on a set (assembly-level)

```python
rf = fr.fieldOutputs['RF']
reg = odb.rootAssembly.nodeSets['FIXED']     # assembly-level set
tot = [0.0,0.0,0.0]
for v in rf.getSubset(region=reg).values:
    for i in range(3): tot[i] += v.data[i]
```
If `nodeSets['FIXED']` is missing at assembly level, try
`odb.rootAssembly.instances['B-1'].nodeSets['FIXED']` (instance-level).

## Contact pressure

```python
cp_key = [k for k in fr.fieldOutputs if k.startswith('CPRESS')][0]
cp = fr.fieldOutputs[cp_key]
max_cpress = max(abs(v.data) for v in cp.values)
n_on = sum(1 for v in cp.values if abs(v.data) > 1e-6)
```

## PEEQ

```python
peeq = fr.fieldOutputs['PEEQ']
max_peeq = max(v.data for v in peeq.values)
```

## History / energy (when needed)

```python
ar = step.historyRegions['Assembly ASSEMBLY']
out = {}
for k in ('ALLIE','ALLKE','ALLAE','ALLVD','ETOTAL'):
    if k in ar.historyOutputs:
        out[k] = ar.historyOutputs[k].data[-1].value
```

## Viewport contour screenshot

```python
from abaqus import session
from abaqusConstants import PNG
odb2 = session.openOdb('<job>.odb', readOnly=True)
vp = session.viewports[session.currentViewportName]
vp.setValues(displayedObject=odb2)
vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_DEF,))
session.printToFile(fileName='<out_basename_no_ext>', format=PNG, canvasObjects=(vp,))
# printToFile appends .png; do NOT include it in fileName.
```

## Pitfalls

- `KeyError 'S'` => the step's FieldOutputRequest did not ask for it.
- Empty `getSubset` => set lives at instance, not assembly level (try both).
- 2D results have 3 components (`S11,S22,S12`), not 6 — check `len(v.data)`.
- If the job aborted, the last frame may be partial; cross-check `.sta`.
