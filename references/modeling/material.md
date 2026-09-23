# Material & sections — API recipes (Abaqus 2026)

> Status: **Elastic + Plastic (EPP) validated on Abaqus 2026** (first plastic point = 0,
> PEEQ reads out, plateau at yield). Other templates are **upstream reference /
> static-reviewed** — validate before trusting a new material model.

## N-mm-MPa system (use consistently)

- E in MPa, nu dimensionless, density in tonne/mm^3 (= kg/m^3 * 1e-9).
- Steel: E=210000, nu=0.3, rho=7.85e-9.

## Isotropic elastic (+optional density)

`Density(table=((7.85e-9,),))` was **Validated on Abaqus/CAE 2026** in a scratch model. The other material recipes below retain their stated evidence labels.

```python
m.Material(name='Steel')
m.materials['Steel'].Elastic(table=((210000.0, 0.3),))
m.materials['Steel'].Density(table=((7.85e-9,),))   # note: rows of rows
```

## Elastic-plastic — the correct table (VALIDATED)

First plastic data point **must** be (yield_stress, **0.0**) — zero plastic strain.
Using `(sy, sy/E)` (total strain) here is a known upstream bug; do not copy it.

```python
mat = m.Material(name='SteelEPP')
mat.Elastic(table=((210000.0, 0.3),))
# row = (true stress, plastic strain). First row plastic strain = 0.0.
mat.Plastic(table=((250.0, 0.0),     # yield onset
                   (250.0, 0.5)))    # ideal-plastic plateau
```

For bilinear hardening, second and later rows carry the *plastic* strain, not total:
`(sy, 0.0), (sy + Ht*(eps_total - sy/E), eps_total - sy/E)`.

## Solid section assignment (VALIDATED pattern)

```python
m.HomogeneousSolidSection(name='Sec', material='SteelEPP', thickness=None)
import regionToolset
part.SectionAssignment(region=regionToolset.Region(cells=part.cells),
    sectionName='Sec', offset=0.0, offsetType=MIDDLE_SURFACE,
    offsetField='', thicknessAssignment=FROM_SECTION)
```

## When to request what

- Static without inertia/gravity: density is optional.
- If the task needs plasticity, request field output `PEEQ` (equivalent plastic strain)
  to confirm yield actually happened.
- Temperature-dependent / hyperelastic / orthotropic / subroutine materials: **out of
  scope for this round** — upstream has templates but they are not yet validated here.
  Treat any such request as an extension; flag that the recipe needs local validation.

## Material library note

Upstream ships a hard-coded Q235/default library. We do **not** auto-pick a material:
the problem statement names the material and gives its curve. If it is missing, ask.
