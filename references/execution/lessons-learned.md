# Lessons Learned — what real Abaqus 2026 tasks taught this agent

> Status: retrospective of REAL tasks run on Abaqus/CAE 2026 through this bridge.
> Each entry is a closed-loop `failure/success → root cause → fix → general rule`.
> **Do not copy the case numbers as defaults.** They are evidence; the General Rule
> is what becomes future behavior. Numbers from a specific course problem are NOT a
> template for the next problem.
>
> Evidence legend:
> - **[A]** Confirmed by a live Abaqus 2026 run / kernel API
> - **[B]** Confirmed by the ODB / `result.json` of that run
> - **[C]** Reasoned engineering lesson (no single oracle, but solid mechanics)
> - **[D]** Documentation / reporting lesson

---

## Case 1 — "Solved the wrong problem perfectly" (truss task)

**What happened.** The problem statement specified a 4-node truss. The agent rebuilt it
as a 6-node, 9-bar truss. Abaqus ran to `COMPLETED`, displacement and stress were
internally correct, reactions balanced — but every number belonged to a different model
than the one asked.

**Failure.** Solver correctness was mistaken for problem correctness. The model was
never checked against the statement before meshing.

**Root cause.** No fidelity checkpoint between "read the PDF/DOCX" and "build the part".
The agent reached for a familiar truss skeleton instead of transcribing the stated topology.

**Fix (then).** Rebuilt to the stated node/bar count; discarded the wrong model.

**General rule.** **Solver correctness ≠ problem correctness.** A green job on the wrong
geometry is still the wrong answer.

**Agent behavior (Problem Fidelity Gate, run BEFORE any build).** Transcribe and list,
from the original statement only:
1. node / part count, 2. geometric topology (which bars/faces touch), 3. dimensions,
4. material, 5. load locations, 6. load directions, 7. supports, 8. contacts/interferences,
9. the analysis objective. If any item is missing or illegible → **stop and ask**, do
not fill it from "what a truss usually looks like". Never invent a missing bar, never
swap in a standard example because it is more familiar, never edit the model "because
it would be more reasonable".
**Evidence status: [C] (failure mode); rule enforced by [A]/[B] runs after the fix.**

---

## Case 2 — A back-fitted "theory" that made a wrong benchmark look accurate

**What happened.** In the EPP micro-validation, a reaction of 27557 N was compared
against a hand-built "theoretical" 27683 N, reported as a 0.5% match. On recheck
the 27683 N had no derivation — it was reverse-fit to the FE number. Separately,
`max PEEQ = 0.100` was quoted as the global plastic strain; the true global value was
the field **mean ≈ 0.0506**, which matched the uniaxial theory 0.0501 to ~1.1%.

**Failure.** (a) An analytical comparison was manufactured to land near the FE result.
(b) A local extremum was reported as the whole-field state.

**Root cause.** Verification was done "toward" the number: once a close formula was
found, its assumptions were never checked. Max values were pulled without asking
*where* they occurred.

**Fix.** `k08_recheck.py` reopened the same ODB, same step, same last frame, and
recomputed PEEQ min/mean/max; the bottom face was `ENCASTRE`, so the specimen
barreled and the bottom corner triaxial — `max PEEQ` sits at that constrained corner
and is NOT representative. The tight check became **mean PEEQ vs theory**; `σ·A` was
demoted to order-of-magnitude only; 27683 N was deleted.

**General rule.** **Good numerical agreement does not prove a valid benchmark.**
Verification may never:
- hunt for a formula that lands near the FE output (no back-fitting),
- quote `max X` as the whole-field state without checking its location,
- mix numbers from different jobs / frames / regions,
- compare two numbers without comparing their underlying assumptions.

**Agent behavior (Verification Gate, run BEFORE writing any "% agreement"):** confirm
the two sides share — (1) same Job, (2) same frame, (3) same physical quantity,
(4) same spatial region, (5) same units, (6) same boundary-condition assumptions,
(7) the analytical model is actually applicable to this FE boundary. If (7) fails, the
comparison is only a **sanity check**, never a "high-precision analytical validation".
**Evidence status: [B] (ODB recheck values), [A] (re-run on 2026), [C] (principle).**

---

## Case 3 — Local extremum ≠ global representative value

**What happened.** `max PEEQ = 0.1004` was quoted as the specimen's plastic strain.
It occurred exactly at the bottom constrained corner (barreling / triaxial frozen
lateral expansion), while the body mean was 0.0506.

**Failure.** Interpreting a singular/edge peak as the material's bulk response.

**Root cause.** Extraction code took `max()` and reported it; no location/region check.

**General rule.** Every reported `max S`, `max PEEQ`, `max CPRESS`, `max U` must carry
its **location** and a judgment of whether it is a boundary/contact/singularity artifact.

**Agent behavior (Result Interpretation Checklist).** For any field, record:
`maximum, minimum, mean` (and median/representative where the field is non-uniform),
plus the **location of the maximum**, its **distance from a constraint/contact edge**,
and a singularity plausibility note. Never headline a max value without its location
unless the field is demonstrably uniform. Always state the **averaging definition**
for any "average" (nodal arithmetic mean vs area-weighted vs path average) — an
undefined "average" is not a result.
**Evidence status: [B] (PEEQ min/max/mean from k08), [C] (rule).**

---

## Case 4 — A physically valid model that still failed task compliance

**What happened.** The cylindrical compression task needed the platen contact force /
platen reaction. For stability the agent modeled the top face with a plain
displacement BC and summed its nodal RF instead of building a rigid platen + RP +
contact. For a frictionless, well-lubricated compression the numbers are nearly
equivalent, but the requested observable (platen reaction through contact) was not
produced by a real contact interaction.

**Failure.** "Equivalent model" substituted for the actually-requested entity.

**Root cause.** Stability was optimized at the cost of the task's required output;
compliance was never checked against the statement.

**General rule.** **Equivalent physics does not waive requirement compliance.** If the
statement asks for `CPRESS`, an RP reaction, a contact force, or a specific component,
the model must contain the entity that produces it. A simplification is allowed only
when the report explicitly labels it as such and the user accepts it.

**Agent behavior (Requirement Compliance Gate, at model-plan time).** List every
quantity the statement asks for (e.g. contact pressure, punch RP RF, specific stress
component, opening). For each, confirm there is a real interaction/body/BC producing it.
A pure top-face BC that yields a force does NOT count as "platen contact reaction".
**Evidence status: [B] (project4 result.json/report), [C] (principle).**

---

## Case 5 — Correct numbers, wrong words in the report

**What happened.** In the compression report:
- the log-strain step was written `ln(15/30) = 0.693`. Mathematically `ln(0.5) = -0.693`;
  the agent actually used the magnitude (true compressive strain `|ln(H0/H1)|`), but
  the printed formula was signed wrong.
- `14.01 mm` was written as the mid "outer diameter" of the barreled specimen. The ODB
  value was the **mid radius** (14.014 mm); the outer diameter is ~28.02 mm.

**Failure.** The solver was right; the report's symbols and geometry names were wrong.

**Root cause.** Assumed that because the FE computation checked out, the prose was also
correct. No formula/unit/geometry-name pass.

**General rule.** **A verified computation does not certify its own write-up.**

**Agent behavior (Report Consistency Gate).** Before declaring done, cross-check every
reported number against (a) the model variable, (b) its unit, (c) sign convention,
(d) radius vs diameter, (e) engineering vs true strain, (f) displacement/force
direction. A formula printed in a report must be algebraically correct as written,
not merely "using the right magnitude somewhere".
**Evidence status: [D] (report text), [B] (result.json confirms 14.014 is radius).**

---

## Case 6 — Job COMPLETED, but the required field output was never requested

**What happened.** First press-fit run: contact was built, RF was present, job
`COMPLETED`, but `CPRESS` came back empty/null — and the task's central result was
"contact pressure over time".

**Failure.** Discovered a missing output request only after the solve.

**Root cause.** No pre-run check that every required observable actually has an ODB
output path.

**General rule.** **A required observable must be requested before/while solving; it
cannot be "inferred" afterward.**

**Agent behavior (Pre-run Output Gate, BEFORE submitting the final job).** Map each
task-required quantity to an ODB key and confirm the `FieldOutputRequest`/
`HistoryOutput` includes it:
stress→`S`, displacement→`U`, reaction→`RF`, plastic strain→`PEEQ`,
contact pressure→`CPRESS`, opening→`COPEN`, a time history→`HistoryOutput`.
If a key is missing, add it and rebuild — do not start the run and hope.
**Evidence status: [A] (real missing-CPRESS run), [B] (later re-run with CPRESS out).**

---

## Case 7 — Press force is NOT contact pressure

**What happened.** Early drafts conflated the punch reaction with contact pressure.

**Root cause.** RF = total axial press force (integral over the whole driven body).
CPRESS = local normal contact stress field. With friction and an entry/funnel effect,
the press force is the sum of normal contact action AND friction AND geometry-entry
effects; it is not equal to CPRESS, nor to a simple average of it.

**General rule.** Keep the three distinct: (1) driven body reaction (RF on a set/RP),
(2) local contact pressure field (CPRESS), (3) derived contact force (area-weighted
integral of CPRESS over the contact patch). When quoting an average CPRESS, state the
averaging definition (Case 3).
**Evidence status: [C] (mechanics), [B] (project3 RF 122.8 kN vs max CPRESS 79.8 MPa).**

---

## Case 8 — Interference-fit compatibility check

**What happened.** An early summary said "inner ring contracts ~0.056 mm, close to the
0.07 mm interference, so it fits". That is incomplete.

**Root cause.** Compatibility is a closure, not a single number check.

**General rule.** For a radial interference, the closure is
`ring inward radial displacement + bore outward radial displacement ≈ radial interference`
(both measured at the mating interface, same frame). Neither side alone proves fit.
**Agent behavior:** report both sides of the displacement balance and their sum vs the
interference value.
**Evidence status: [B] (project3: ring inward 0.0557 mm), [C] (compatibility condition).**

---

## What worked — keep these patterns

- **[C] Axisymmetric simplification when geometry and loading are axisymmetric.**
  A 2D `CAX4R` model (with `RAX2`/`RAX2` rigid) solved both the press fit and the
  cylinder compression at a fraction of 3D DOF. Route to axisymmetry when the problem
  is genuinely axisymmetric; do not default to it for non-axisymmetric loads.
- **[A/B] Displacement control over force control** for plasticity / contact /
  forming: both compression and press-fit ran cleanly (22–24 increments, no cutback)
  when the platen/punch was driven by prescribed displacement.
- **[A] `nlgeom=ON` is mandatory** for large deformation (50% height reduction) and
  for press-fit contact evolution.
- **[A/B] Real rigid punch + RP + real contact** (press fit): `CAX4R` deformable +
  `RAX2` discrete rigid, punch–ring frictionless, ring–base μ=0.2, geometric radial
  interference built directly, displacement-driven. This produced RF-time, CPRESS-time,
  Mises, radial displacement as self-consistent observables. (Use as a *workflow*
  reference, not a parameter template.)
- **[B] Multi-evidence cross-check beats any single number.** Compression task closed
  on: final height target, PEEQ vs log-strain theory, flow stress vs the input table,
  force vs σ·current area, mid-radius vs volume conservation — agreeing across five
  independent relations.
- **[A] Micro-validation exposes version drift.** Deliberately small builds (1-element /
  cube) caught the 2026 API renames (`main=`/`secondary=`) before they infected a big run.
- **[C] Deliberate fault injection helps.** Running a known under-constrained model
  produced the exact `NUMERICAL SINGULARITY` cutback signature, so the diagnosis table
  rests on real logs.
- **[B] Persist `result.json`** (job status, key numbers, units, convergence notes) so
  later audits and re-derivation are possible — this is what made Case 2's correction
  traceable.
- **[C] Label confidence.** Every recipe in `references/` is tagged
  `Validated on Abaqus 2026` / static-reviewed / unverified. Never mix an unverified API
  into the "validated" tier.

---

## Abaqus 2026 — confirmed kernel behavior (consolidated, do not re-derive)

These are already enforced across `gotchas.md`, `modeling/contact.md`,
`execution/error-diagnosis.md`, `modeling/odb-postprocess.md`. Listed here so a future
failure does not get "rediscovered":

- **[A]** `SurfaceToSurfaceContactStd(...)` uses **`main=` / `secondary=`**, not
  `master=`/`slave=` (2026 renames the parameters).
- **[A]** A discrete rigid part must be **meshed** (R3D4/RAX2) before a `RigidBody`
  body region or a contact surface resolves.
- **[A]** Contact pressure output is a **per-interaction key** `CPRESS   <secondary>/<main>`
  (plus `COPEN`, `CSHEAR...`); there is no field key named `CSTRESS`.
- **[A]** `import mesh` is required; `from abaqus import *` does not bind `mesh`.
- **[A]** Kernel scripts must be **UTF-8 without BOM** (U+FEFF breaks `exec`).
- **[A]** `session.printToFile(...)` needs `from abaqusConstants import PNG` and an
  extensionless base name (it appends `.png` itself).
- **[A]** `region.getByBoundingBox(...)` takes **six separate floats**, not a tuple.
- **[A]** A job is `success` only when its status is `COMPLETED`; anything else
  (including a leftover `.lck`) must not be reported as done.
- **[C] / bridge** Screenshots must come from the current viewport render, never a
  stale historical image file; `ABAQUS_MCP_HOME` must point at the one IPC dir; the
  blocking `mcp_loop()` is the stable path (background-thread mode is experimental).

Anything NOT on this list and NOT explicitly tagged "Validated on Abaqus 2026" is
static-reviewed at best — validate it on a tiny scratch model before trusting it in a
real task.
