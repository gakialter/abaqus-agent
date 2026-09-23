# Contact, rigid bodies, couplings (Abaqus 2026)

> Status: **frictionless rigid-platen / deformable-cube contact validated on 2026**
> (CPRESS extracted, RF balanced). The keyword names below are the 2026-correct ones —
> they DIFFER from the upstream templates.

## Abaqus 2026 keyword changes (learned by failure)

- `SurfaceToSurfaceContactStd(...)` takes **`main=`** and **`secondary=`**, NOT
  `master=`/`slave=`. The old names raise `TypeError: 关键字错误: master`.
- Contact pressure/displacement outputs are **per-contact-pair field keys**:
  `CPRESS   <SECONDARY>/<MAIN>`, `COPEN ...`, `CSHEAR...`. There is no key named
  `CSTRESS`.
- **Validated on Abaqus/CAE 2026:** a scratch model with `Cont1` and `Cont2` produced two distinct CPRESS and COPEN keys in one frame. Keys used the named surface pairs, not the interaction names. Enumerate keys and select the exact surface pair and region; never take `[0]`.
- A discrete rigid part must be **meshed** (R3D4) before a `RigidBody` region or a
  contact surface resolves.

## Canonical validated setup: cube on a rigid platen

```python
import mesh, regionToolset
# deformable cube (z=0..10) ... material elastic ...
# discrete rigid flat platen: planar shell in the z=0 plane
p = m.Part(name='Platen', dimensionality=THREE_D, type=DISCRETE_RIGID_SURFACE)
s2 = m.ConstrainedSketch(name='__p__', sheetSize=50.0); s2.rectangle((-15,-15),(15,15))
p.BaseShell(sketch=s2); del m.sketches['__p__']

a = m.rootAssembly
a.Instance(name='C-1', part=cube, dependent=ON)
a.Instance(name='P-1', part=p, dependent=ON)

# reference point + rigid body on the platen shell
rp = a.ReferencePoint(point=(0.0, 0.0, 0.0))
rpid = a.referencePoints[rp.id]
rpSet = a.Set(name='PlatenRP', referencePoints=(rpid,))
bodySet = a.Set(name='PlatenBody', faces=a.instances['P-1'].faces)
m.RigidBody(name='PlatenRB', refPointRegion=rpSet, bodyRegion=bodySet)
m.EncastreBC(name='FixRP', createStepName='Initial', region=rpSet)

m.StaticStep(name='S1', previous='Initial', nlgeom=ON, timePeriod=1.0,
             initialInc=0.05, minInc=1e-8, maxInc=0.1, maxNumInc=1000)
m.FieldOutputRequest(name='F1', createStepName='S1',
                     variables=('S','U','RF','CPRESS','COPEN'), frequency=5)

# driven face + symmetry to stop rigid drift
top = a.Set(name='TOP', faces=a.instances['C-1'].faces.getByBoundingBox(-.1,-.1,9.9, 10.1,10.1,10.1))
m.DisplacementBC(name='Press', createStepName='S1', region=top, u3=-0.2)
# ...fix x=0 face u1=0, y=0 face u2=0...

# frictionless normal contact
m.ContactProperty(name='IntProp')
m.interactionProperties['IntProp'].NormalBehavior(allowSeparation=ON)
slave = a.Surface(name='CubeBottom',
    side1Faces=a.instances['C-1'].faces.getByBoundingBox(-.1,-.1,-.1, 10.1,10.1,.1))
master = a.Surface(name='PlatenTop',
    side1Faces=a.instances['P-1'].faces.getByBoundingBox(-15.1,-15.1,-.1, 15.1,15.1,.1))
m.SurfaceToSurfaceContactStd(name='Cont1', createStepName='S1',
    main=master, secondary=slave, sliding=FINITE, interactionProperty='IntProp')

# mesh BOTH the deformable cube and the rigid platen
cube.seedPart(size=2.0); cube.generateMesh()
p.seedPart(size=3.0); p.generateMesh()
```

Results we got on this model: max CPRESS 4086 MPa vs expected elastic 4200 MPa (3%),
36 contact nodes loaded, driven RF ~413 kN balanced.

## Friction

Add Coulomb friction to the same property:
```python
m.interactionProperties['IntProp'].TangentialBehavior(formulation=PENALTY, frictionCoeff=0.2)
```
A frictionless model simply omits `TangentialBehavior`.

## Coupling (drive a whole face through a reference point)

```python
rp = a.ReferencePoint(point=(50.0, 50.0, 0.0)); rpid = a.referencePoints[rp.id]
rpSet = a.Set(name='RP-Set', referencePoints=(rpid,))
m.Coupling(name='C1', controlPoint=rpSet,
    surface=a.Surface(name='Loaded', side1Faces=loaded_faces),
    influenceRadius=WHOLE_SURFACE, couplingType=KINEMATIC,
    u1=ON, u2=ON, u3=ON, ur1=ON, ur2=ON, ur3=ON)
# then ConcentratedForce / DisplacementBC on rpSet
```

## Choosing sides and normals

- secondary = finer / softer / smaller face; main = the rigid or coarse face.
- If contact never engages, suspect flipped normals (check `.dat` and re-pick side1/side2).
- Press-fit / interference: set up the interference explicitly (`interferenceFit`) — do
  not rely on accidental overlap.

## Verify contact engaged

Request `CPRESS`/`COPEN`; in post-process confirm `max(CPRESS) > 0` and that the support
reaction equals the driven load. A run that "completes" but CPRESS=0 everywhere means the
bodies never touched.
