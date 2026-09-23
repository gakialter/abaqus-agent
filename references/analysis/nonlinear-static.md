# Nonlinear static analysis (nlgeom=ON)

> Status: **VALIDATED on Abaqus 2026** — EPP compression, displacement control,
> `nlgeom=ON`, Job COMPLETED, PEEQ out, RF balanced. See validation/knowledge-layer/.

## When to use

- Large deformation (deformation > ~5% of a characteristic dimension).
- Material plasticity.
- Contact (see modeling/contact.md).
- Post-buckling / snap-through (use Riks).

## Step setup (validated)

```python
m.StaticStep(name='S1', previous='Initial', timePeriod=1.0, nlgeom=ON,
             initialInc=0.05, minInc=1e-8, maxInc=0.1, maxNumInc=1000)
m.FieldOutputRequest(name='F1', createStepName='S1',
                     variables=('S','LE','PEEQ','U','RF'), frequency=5)
```

## Displacement control (preferred for forming / compression)

Drive a face/reference point with `DisplacementBC(u3=...)` rather than a force. It is far
more robust once the material yields or contact engages — load control can dive through a
limit point. We drove u3=-0.5 mm on a 10 mm cube and it converged in 13 frames.

## Increments

| Parameter | Starting point |
|-----------|----------------|
| initialInc | 0.05–0.1 |
| minInc | 1e-8 |
| maxInc | 0.1 (cap growth) |
| maxNumInc | 1000 |

Start conservative; shrink `initialInc` only if the first increment cuts back. Do not start
with a tiny increment as a ritual.

## Material

Use modeling/material.md: elastic + `Plastic(table=((sy,0.0), ...))`. Under near-incompressible
plastic flow, C3D8R/C3D20R (reduced integration) beat fully-integrated C3D8.

## Stabilization (use with discipline)

```python
m.StaticStep(..., stabilizationMethod=DAMPING_FACTOR, stabilizationMagnitude=2e-4)
```
Only when convergence genuinely stalls. After convergence, check `ALLVD/ALLIE < 5%`; if
stabilization energy is large, you are reading damped-down physics, not the real result.
For physical snap-through/buckling prefer `StaticRiksStep`.

## Verify (minimum)

- max Mises follows the stated yield (plasticity) or grows monotonically (elastic).
- PEEQ > 0 where yielding is expected.
- RF on supports balances the driven reaction (with nlgeom, use deformed area for the
  hand comparison — see verification.md).
- no exponential cutbacks in `.sta` at the converged end.

## Out of scope this round

UMAT/VUMAT, creep, viscoelastic, damage/XFEM — upstream has templates but they are not
validated here; treat as an extension requiring a single-element validation first.
