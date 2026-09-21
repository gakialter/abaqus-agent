# Mesh — element choice and seeding (Abaqus 2026)

> Status: structured hex + C3D8R validated on 2026 (cantilever, EPP compression, contact).

## Required import

```python
import mesh   # 'from abaqus import *' does NOT bind 'mesh' in 2026
```

## Solid element choice

| Code | Use |
|------|-----|
| C3D8R | general hex, reduced integration. Enable `hourglassControl=ENHANCED` (we do). |
| C3D8I | bending on a coarse mesh, shear-locking free |
| C3D20R | second-order hex, stress concentrations |
| C3D10 | complex free-geometry tet, quadratic (avoid linear C3D4) |

```python
part.setMeshControls(regions=part.cells, elemShape=HEX, technique=STRUCTURED)
et = mesh.ElemType(elemCode=C3D8R, elemLibrary=STANDARD, hourglassControl=ENHANCED)
part.setElementType(regions=(part.cells,), elemTypes=(et,))
part.seedPart(size=2.0)
part.generateMesh()
```

For free tet mesh on complex geometry: `technique=FREE, elemShape=TET`, element `C3D10`.

## Rigid parts still need a mesh (VALIDATED the hard way)

A **discrete rigid** part (e.g. a platen) must be seeded and meshed too — it produces
R3D4 rigid elements. If you skip it, `.dat` reports
`ELEMENT SET ..._BODY HAS NOT BEEN DEFINED` and `THE MAIN SURFACE ... DOES NOT EXIST`.

```python
rigid_part.seedPart(size=3.0)
rigid_part.generateMesh()
```

## Quality / convergence

- >= 3–4 element layers through the thickness where bending or stress gradient matters.
- avoid large aspect ratios; `part.verifyMesh()` to inspect quality.
- Check mesh convergence only when the result drives a decision (verification.md).
