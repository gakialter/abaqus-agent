# Linear static analysis (Static General, nlgeom=OFF)

> Status: validated path (existing cantilever E2E: tip disp ~0.40 mm, fixed-end Mises
> ~100 MPa, matches hand calc). Use for: bracket/beam stress, trusses, small-stress
> parts where the problem says linear/elastic.

## When to use

- Small deformation, linear elastic material, no contact, no buckling.
- The problem asks for stress / deflection under a stated load.

## Recipe skeleton (via execute_script)

```python
m.StaticStep(name='S1', previous='Initial', timePeriod=1.0)
m.FieldOutputRequest(name='F1', createStepName='S1', variables=('S','U','RF'), frequency=1)
# BC: EncastreBC on the fixed face; ConcentratedForce / Pressure / Gravity on the loaded set
```

## Validation checklist

- job COMPLETED.
- reaction balance: sum |RF| on supports ~ applied load (verification.md).
- for a beam/truss, compare max deflection or max stress to the hand formula within a few %.
- units in N-mm-MPa.

## Do not over-declare

If the problem actually involves large displacement, yielding, or touching bodies,
**route to nonlinear-static / contact instead** — a linear elastic run will silently give
wrong numbers.
