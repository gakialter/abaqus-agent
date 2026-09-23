# Historical knowledge-layer errata

This note preserves original validation artifacts. `validation/result.json`, historical `validation_results.json`, and images are not corrected in place.

- Solver `COMPLETED` establishes G4 only. G1–G8 are required for task completion.
- The EPP RF near 27557 N does not have a demonstrated 0.5% analytical agreement. The 27683 N comparator was historically reverse-fit and must not be reused as a benchmark.
- PEEQ near 0.10 was a local maximum. Approximately 0.05064 was an unweighted arithmetic mean of field values; it was not established as a volume-weighted average or representative global plastic strain.
- Contact output requires exact interaction/key/region selection. RF (force) and CPRESS (pressure) are distinct quantities.
- A release scratch model with two named contact interactions generated two distinct CPRESS and COPEN surface-pair keys. The keys did not contain the interaction names; selection by `Cont2` string would have failed.
- Partial ODB frames from failed jobs can aid diagnosis, but are not final validated results.
- In the release scratch EPP run, requesting both E and LE produced LE and PEEQ but no E field in the final frame. Recipes must enumerate actual ODB keys before claiming E availability.

Evidence labels for recipes and API claims: Validated on Abaqus/CAE 2026, Static-reviewed, Upstream-derived, Version-sensitive, Unverified. Existing historical records retain their original provenance and limitations.
