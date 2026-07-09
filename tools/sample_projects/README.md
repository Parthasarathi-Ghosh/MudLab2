# Sample projects (calc-engine fixtures)

Two real MudLab `.mud` projects used as the gold-standard fixtures for the
pattern-calculation engine. Each already contains the **calculated pattern
the old GTK MudLab produced**, so `tools/verify_calc_engine.py` can
recompute the pattern from scratch and diff it against that stored
reference - validating batches 1-6 end to end.

**These `.mud` files are intentionally NOT committed.** They are the user's
own data, kept for testing only, and are gitignored (`tools/sample_projects/
*.mud`) so they never reach `origin` or a release. This README is the only
tracked file in this folder. To run the harness, drop the two files here (or
in `~/Downloads/`, the fallback location) - they are not distributed with the
repo.

| File | Contents | What it exercises |
|---|---|---|
| `308 r1.mud` | 3-specimen mixture (illite / kaolinite / chlorite / mixed-layer I-S), air-dried + glycolated + heated | multi-phase mixture, R0G1 + R0G2 stacking, the AD/EG/heat expandable-clay sequence |
| `Dh2040A.mud` | 2-specimen mixture of Ca-smectite (AD/EG/350 C) | single-component phases, smectite 15 -> 17 -> 10 A collapse |

Run the check (bundled interpreter, from the repo root):

```
./python/python.exe tools/verify_calc_engine.py
```

The harness prefers a local copy in this folder; if absent it falls back to
`~/Downloads/`. Keep them byte-for-byte as loaded - the stored calculated
patterns are the regression baseline, so do not re-save them through MudLab2
(which would rewrite the JSON formatting).
