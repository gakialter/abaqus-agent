# Verification — "COMPLETED" is not "correct"

> Status: analytical checks adapted from upstream; **RF balance + plastic-plateau check
> confirmed on Abaqus 2026** (validation/knowledge-layer/). Run the *smallest sufficient*
> check for the task — do not mechanically run every check on every model.

## Golden rule

A job that ends `COMPLETED` only means the solver reached the end. It can still be wrong
because of wrong BCs, wrong units, coarse mesh, or a contact that never engaged. Before
reporting numbers, prove at least one physical check.

## Minimum sufficient verification (pick by task type)

| Task type | Minimum check |
|-----------|---------------|
| any static model | **reaction balance**: sum |RF| on supports ≈ applied load (vector sum) |
| beam / simple structure | analytical comparison (deflection / stress) within a few % |
| plasticity | stress must plateau at (or follow) the stated yield; PEEQ > 0 after yield |
| contact | max CPRESS > 0 and order-of-magnitude sane; RF on support ≈ driven reaction |
| nonlinear / large strain | trend + energy ratios (below) |

## 1. Reaction (static equilibrium) balance

Sum the reaction on every constrained set; it must equal the applied load vector.

```python
from odbAccess import openOdb
odb = openOdb('<job>.odb', readOnly=True)
fr = odb.steps['<step>'].frames[-1]
rf = fr.fieldOutputs['RF']
tot = [0.0, 0.0, 0.0]
# iterate the constrained node set(s)
for v in rf.getSubset(region=odb.rootAssembly.nodeSets['FIXED']).values:
    for i in range(3): tot[i] += v.data[i]
print('sum RF =', tot)   # compare with applied load
```
For a displacement-driven compression, the driven face's RF3 equals the contact/support
reaction (we measured 27.56 kN EPP and 413 kN elastic — both matched hand calc).

## 2. Analytical benchmarks (use when the geometry admits it)

**Cantilever in bending** (tip load P, length L, section b×h, E in MPa):
```
I = b*h^3/12
delta_tip = P*L^3 / (3*E*I)
sigma_fixed = (P*L)*(h/2) / I
```
Expect 1–5% agreement with C3D8R (better with C3D8I/C3D20R).

**Uniaxial plastic plateau** (cross-section area A, yield sy):
```
F_plateau = sy * A_current
```
With `nlgeom=ON` and large strain, use the **current** (deformed) area, not the initial
area. At 5% true compression the area grows ~5% (plastic incompressibility); our FE force
27.56 kN matched the true-stress estimate 27.7 kN to 0.5%. A 5–10% gap vs `sy*A_initial`
is expected, not an error — explain it rather than "fix" it.

**Thick-walled cylinder (Lame)**: hoop at inner wall = p*(a^2+b^2)/(b^2-a^2).

## 3. Energy checks (only when they are meaningful)

From `odb.steps[<step>].historyRegions['Assembly ASSEMBLY'].historyOutputs`:

| Ratio | OK when |
|-------|---------|
| ALLKE / ALLIE | << 1 (quasi-static implicit) |
| ALLAE / ALLIE | < 5% (hourglass, reduced-integration elements) |
| ALLVD / ALLIE | < 5% (stabilization damping did not dominate) |

Skip these for a simple linear elastic run — they add no signal there.

## 4. Mesh convergence (only when the result matters)

Run coarse/medium/fine (halve element size). Converged when
`|fine - medium| / fine < 2–5%`. If it oscillates, suspect a singularity or element
choice, not just coarseness.

## 5. Unit sanity (before trusting numbers)

E = 210000 MPa (not 2.1e11); density = 7.85e-9 tonne/mm^3 (not 7850);
gravity = 9800 mm/s^2 (actual acceleration). Displacements/stresses must land in the
order of magnitude the hand calc predicts.

## Report the check, not just the result

Always state: what you compared, the FE number, the expected number, and the % difference.
If you could not run a check, say so and why — never imply a verified result that was not.
