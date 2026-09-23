# Error Diagnosis — agent-decidable failure map

> Status: tables A/B/C/E adapted from upstream (static-reviewed) **plus** our own
> Abaqus 2026 log evidence (see "Confirmed on 2026" rows). Use this when a job ABORTs or
> stalls. Read logs FIRST, do not start by shrinking increments.

## 0. Where to look (in priority order)

| File | Tells you |
|------|-----------|
| `<job>.sta` | increment-by-increment convergence: cutbacks, `U`/`I` flags, final "analysis (not) completed" |
| `<job>.msg` | solver warnings/errors, `NUMERICAL SINGULARITY`, contact iterations, cutback reasons |
| `<job>.dat` | input echo, `***ERROR` blocks, element-set / surface errors |
| `<job>.log` | job lifecycle, license, pre-processor stage |
| `<job>.odb` | partial frames may diagnose a failed job; not a final validated result |

Quick kernel snippet to dump the tail:
```python
for fn in ('<job>.sta','<job>.msg','<job>.dat'):
    print('==== '+fn)
    with open(fn, 'r', errors='replace') as f:
        lines = f.readlines()
    print(''.join(lines[-25:]))
```

## 1. Decision tree (top-down)

```
Job ABORTED / stalled?
├─ leftover <job>.lck or .sim running  -> stale lock; analysis may have finished anyway.
│                                        Check .msg for "ANALYSIS HAS BEEN COMPLETED" before re-running.
├─ .dat ***ERROR at input stage        -> input/syntax/model-build error (section below).
│                                        (element set undefined, surface missing, bad keyword)
├─ .sta: exponential cutbacks + "U" flags, time->min
│   ├─ .msg NUMERICAL SINGULARITY / ZERO PIVOT at nodes  -> under-constraint / rigid body (§A)
│   ├─ contact in model?                                  -> contact not established (§C)
│   └─ nlgeom ON, snap-through / softening                 -> Riks or stabilization (§B)
├─ NEGATIVE EIGENVALUE                 -> rigid mode (first increment) or physical buckling (§A)
├─ ELEMENT DISTORTED EXCESSIVELY       -> large deformation / bad mesh (§D)
├─ NaN / overflow                      -> units, subroutine, stress level (§E)
└─ COMPLETED but numbers look wrong    -> units, mesh, wrong BC region (verification.md)
```

## A. Zero pivot / numerical singularity / negative eigenvalue

**Confirmed on Abaqus 2026** — free cube, point load, no BC:
- `.sta`: increments collapse 1.0 -> 0.25 -> 0.0625 -> 0.0156 -> 0.0039, every iteration
  carries a `U` flag, ends "THE ANALYSIS HAS NOT BEEN COMPLETED".
- `.msg`: `***WARNING: SOLVER PROBLEM. NUMERICAL SINGULARITY WHEN PROCESSING NODE B-1.x`
  repeated at free nodes.

| Symptom | Likely cause | Minimal fix |
|---------|--------------|-------------|
| NUMERICAL SINGULARITY / ZERO PIVOT at a free node | rigid-body mode, missing BC | add the BC/constraint the problem actually requires; tie or couple a loose part. **Do not** just lower minInc. |
| Singularity right after contact opens | parts separate and lose constraint | tie, or set contact to hold, or add a small preload step |
| NEGATIVE EIGENVALUE, first increment, static | rigid body or geometric instability | constrain the body; if physical, use Riks / stabilization |
| NEGATIVE EIGENVALUE mid-loading | physical buckling / snap-through | switch to `StaticRiksStep` or add stabilization; do not "fix" by changing load |

**Forbidden auto-"fixes":** do not change material strength, friction, geometry, applied load,
or BC values to force convergence unless the thing you are changing was itself a modeling
error (e.g. a BC applied to the wrong set).

## B. Convergence / cutbacks

| Symptom (.sta/.msg) | Cause | Fix |
|---------------------|-------|-----|
| cutbacks from the very first increment | contact not established / unstable start / wrong initial geometry | shrink `initialInc`; check contact clearance/overclosure; check BCs first |
| cutbacks late in loading | snap-through, softening material, instability | `StaticRiksStep`; or add `stabilizationMethod=DAMPING_FACTOR` with a small magnitude, then confirm ALLVD/ALLIE < 5% |
| 16+ iterations per increment, barely converging | hard nonlinearity (plasticity, contact) | smaller `initialInc`; check the actual contact/material data, not a blanket smaller step |
| "TIME INCREMENT IS LESS THAN THE MINIMUM" | cannot converge at all | not an increment problem — fix root cause (BC/contact/material/mesh) |
| MAX PLASTIC STRAIN INCREMENT exceeded | too much plastic strain per increment | shrink increment; check hardening table starts at (sy, 0.0) |

## C. Contact & interactions

**Confirmed on Abaqus 2026** — two real input-stage failures we hit:
1. Discrete rigid part **not meshed** -> `.dat`:
   `***ERROR: ELEMENT SET ASSEMBLY_..._BODY HAS NOT BEEN DEFINED` and
   `***ERROR: THE MAIN SURFACE ASSEMBLY_..._TOP DOES NOT EXIST`.
   Fix: mesh the rigid part (creates R3D4 elements) before `RigidBody`/contact resolves.
2. `SurfaceToSurfaceContactStd(master=..., slave=...)` -> keyword error in 2026.
   Fix: use `main=...` / `secondary=...` (2026 renamed the parameters).

| Symptom | Cause | Fix |
|---------|-------|-----|
| element set / main surface undefined | rigid part not meshed, or surface built before mesh | mesh rigid part; rebuild surfaces after meshing |
| contact never engages | surface normals face the wrong way | flip normals on the rigid/slave face; re-check master->secondary direction |
| initial overclosure warning | surfaces overlap by a gap | adjust geometry so they just touch; use interference fit only if intended |
| chattering / oscillation | contact stiffness / too-large step | penalty contact, smaller increment, contact damping |
| high friction not converging | mu too large for the load path | reduce mu only if it was an arbitrary value you introduced; otherwise smaller increments |

Contact results are read as **per-interaction fields**: `CPRESS   <slave>/<master>`,
`COPEN ...`, `CSHEAR...`. There is no field key literally named `CSTRESS`.

## D. Mesh / elements

| Symptom | Cause | Fix |
|---------|-------|-----|
| ELEMENT DISTORTED EXCESSIVELY | extreme deformation on C3D8R | refine; use better aspect ratio; check distortion control |
| hourglass (ALLAE high) | C3D8R in bending | `hourglassControl=ENHANCED`, or C3D8I / C3D20R |
| volumetric locking (over-stiff, plasticity) | fully integrated in near-incompressible plastic flow | reduced-integration C3D8R/C3D20R (hybrid for truly incompressible) |
| NEGATIVE JACOBIAN | inverted / bad-quality elements | `part.verifyMesh()`, refine, kill high aspect ratios |

## E. Material & units

| Symptom | Cause | Fix |
|---------|-------|-----|
| absurdly small/large displacement | unit mismatch (Pa vs MPa) | re-check E, density, load magnitudes (N-mm-MPa table in workflow.md) |
| yield never reached | yield stress unit error | stress is in MPa; plastic first row is (sy, 0.0) |
| "TOO MUCH PLASTIC STRAIN" | plastic table starts wrong | first plastic point MUST be (sy, 0.0), not (sy, sy/E) |
| NaN early in run | units / subroutine / division by zero | check magnitudes; guard subroutines |

## Recipe: a step that needs to converge

```python
m.StaticStep(name='S1', previous='Initial', nlgeom=ON,
              timePeriod=1.0, initialInc=0.05, minInc=1e-8,
              maxInc=0.1, maxNumInc=1000,
              stabilizationMethod=DAMPING_FACTOR, stabilizationMagnitude=2e-4)
```
Use stabilization only when convergence proves unstable; after convergence confirm
`ALLVD/ALLIE < 5%`, otherwise the result is trust-damping, not physics.
