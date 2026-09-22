# Verification — "COMPLETED" is not "correct"

> Status: analytical checks adapted from upstream; **RF balance + plastic-plateau check
> confirmed on Abaqus 2026** (validation/knowledge-layer/). Run the *smallest sufficient*
> check for the task — do not mechanically run every check on every model.

## Golden rule

A job that ends `COMPLETED` only means the solver reached the end. It can still be wrong
because of wrong BCs, wrong units, coarse mesh, or a contact that never engaged. Before
reporting numbers, prove at least one physical check.

## Verification Gate — run BEFORE writing any "% agreement"

A numerical match is meaningless if the two sides are not actually comparable. Confirm
all of:

1. **same Job** (not a re-run with changed material/BC),
2. **same frame** (last frame, or the frame the theory applies to),
3. **same physical quantity**,
4. **same spatial region** (bulk, not a constraint corner; support set, not whole body),
5. **same units**,
6. **same boundary-condition assumptions**,
7. **the analytical model is applicable to this FE model.**

If (7) fails (e.g. FE has barreling / end triaxiality / friction the formula ignores),
the comparison is only a **sanity check**, never a "high-precision analytical validation".

**Never back-fit a theory to the FE number.** A formula built after the run so that it
lands within 1% is not validation. If you cannot derive the expected value *before* the
run, say it is a sanity check.

## Local extremum vs representative value

Do not quote `max S / max PEEQ / max CPRESS / max U` as the state of the whole model.
For each field record `max`, `min`, `mean`, and the **location of the maximum**; judge
whether the max sits at a constraint, contact edge, or singularity (e.g. PEEQ peaked at
an encastred corner while the body mean was the representative strain). Any "average"
must state its averaging definition (nodal arithmetic mean, area-weighted mean, or path
average) — an undefined "average" is not a result.

Press force (summed RF on a driven RP/face) is **not** contact pressure (CPRESS field).
Report them as separate quantities; CPRESS-averaged is a separate derived number.

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
reaction (we measured 27.56 kN EPP and 413 kN elastic). The elastic 413 kN matched
`E*strain*A = 420 kN` tightly; the EPP 27.56 kN is only order-of-magnitude because the
specimen barreled (see the plastic-plateau caveat below) — its tight check is PEEQ, not force.

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
area. **Caveat learned the hard way:** if the specimen ends are encastred / friction-
locked, it barrels and the ends are triaxially stressed, so `sy*A` is only an
**order-of-magnitude** check — NOT a tight benchmark. The tight check is then the
**field-mean PEEQ vs the theoretical plastic strain**, not the force. In our 5% EPP
cube, `mean PEEQ = 0.0506` matched theory `ln(9.5/10) - sy/E = 0.0501` to ~1.1%, while
`max PEEQ = 0.100` at the constrained corner must not be quoted as the global strain,
and `sy*A` carried a ~10% gap from end triaxiality (explain it, do not "fix" it with a
back-fit — never manufacture a "theoretical" force that lands near the measured RF).

**Interference / press-fit compatibility.** Do not judge "it fits" from one radial number
alone. The closure is `ring inward radial displacement + bore outward radial displacement
≈ radial interference`, both measured at the mating interface in the same frame; report
both sides and their sum.

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
