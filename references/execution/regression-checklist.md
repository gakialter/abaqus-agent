# Regression checklist — static self-test of the new gates

> Purpose: prove the new rules actually change behavior **without re-running a large
> Abaqus job**. Each scenario states a trigger, the correct agent action, and the rule
> that enforces it. Run through this list after editing `references/`.
> Result column filled in at authoring time; re-run mentally on every change.

| # | Scenario (trigger) | Required agent action | Enforced by | Result |
|---|--------------------|-----------------------|-------------|--------|
| A | Problem statement omits a parameter (no material / missing dimension) | **Stop and ask**; do not fill a familiar default, do not build a "reasonable" model | workflow G1; SKILL hard rule 1; lessons-learned Case 1 | PASS |
| B | Job `COMPLETED` but summed support RF does not balance the applied load | Do **not** write "validated". Write "solver completed", report the imbalance, route to verification.md / error-diagnosis.md | workflow G4+G6; verification.md Golden rule; SKILL hard rule 2 | PASS |
| C | Task asks for `CPRESS` over time | Before `submit_job`, confirm a contact interaction **and** `CPRESS` (plus history) are in the output request; if absent, add and rebuild. Never start and hope | workflow G3; lessons-learned Case 6 | PASS |
| D | `max PEEQ` is at the encastred / fixed end | Record its location; judge it a boundary singularity; quote field **mean/representative** (with averaging definition), not the max | verification.md "Local extremum vs representative"; lessons-learned Case 3 | PASS |
| E | Statement gives `E = 21000` MPa, which looks like a typo for 210000 | Keep `E = 21000`, mark the doubt, offer an alternate rerun — do **not** silently change it to "common steel" | SKILL hard rule 1; lessons-learned project4 note ("suspicious input != permission") | PASS |
| F | Task requires rigid-punch RP reaction force | Build a real discrete rigid punch + RP + contact (or state the simplification and get user acceptance); do **not** substitute a plain top-face displacement BC summed as "contact force" | workflow G2; lessons-learned Case 4 | PASS |
| G (extra) | Agent wants to claim "0.5% vs theory" | Verify same job/frame/quantity/region/units/BC + that the theory applies; no back-fitting. If any fail, label it a sanity check | verification.md Verification Gate; lessons-learned Case 2 | PASS |
| H (extra) | Task involves radial interference | Report ring-inward + bore-outward displacement sum vs interference, not just one side | verification.md interference closure; lessons-learned Case 8 | PASS |
| I (extra) | Writing the final report | Re-check signs, units, radius-vs-diameter, engineering-vs-true strain, directions against model variables | workflow G7; lessons-learned Case 5 | PASS |
| J (extra) | A recipe in references/ is not tagged "Validated on Abaqus 2026" | Treat it as static-reviewed/unverified; run a tiny scratch build before trusting it in production | lessons-learned closing list; material.md convention | PASS |

## How to run this list after a future edit

1. Re-read the scenario column for A–J.
2. Grep the rules for their enforcement file and confirm the sentence still exists and
   still says the right thing (no softening to "usually" / "when convenient").
3. If a rule was weakened, restore it. No Abaqus job is needed for this static check.

This is a **behavior** regression test, not a numerical one. It deliberately does not
re-run project 3 / project 4; their numbers are evidence, not fixtures to re-baseline.
