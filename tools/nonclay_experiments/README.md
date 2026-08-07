# Non-clay decomposition — experiment scripts (EXPERIMENTAL)

Throwaway-tier reproducibility scripts behind the non-clay decomposition
findings. **The science is written up in [`docs/non-clay-analysis-notes.md`](../../docs/non-clay-analysis-notes.md)
(Findings 1–20)** — these scripts just let those numbers be re-run and re-argued.
They read LOCAL, gitignored data (the `.mud` fixtures, the user's
`~/Downloads/Raw pattern phases/` references) and some fetch structures from the
Crystallography Open Database (need internet). They will not run on a clean
clone. Nothing here is shipped code; `src/mudlab/` imports none of it and the
clay calc/optimize/refine path is untouched.

Run head-less with the bundled interpreter from the repo root, e.g.
`./python/python.exe tools/nonclay_experiments/e1_refspace.py`.

| script | finding | what it does |
|---|---|---|
| `structure_pattern.py` | 16, 17 | **The from-CIF stick calculator** (COD CIF + Waasmaier–Kirfel factors + LP). Reusable parser + `stick()`; demo = corundum vs ICDD + the E1 gate on the provided file. The reference/standard generator + Case-B seed. |
| `e1b_quartz_from_cif.py` | 16 | Quartz from a COD CIF vs ICDD 46-1045 + the measured `quartz.txt`. |
| `e1_refspace.py` | 13 | Reference-space (LP) slope gate on the 9 local references. |
| `e1d_albite.py` | 18 | E1 gate on triclinic albite (imports `structure_pattern`). |
| `e2_shared.py` | 14 | Shared vs per-specimen quartz amplitude (the local-bias result). |
| `e2b_weighted.py` | 14 | Global-Rp weighting / best-Rp selection (both fail). |
| `e2c_nullweight.py` | 20 | Null-weighting (also fails; bias is unobservable). |
| `e3_collinearity.py` | 15 | Collinearity diagnostics + guard on the un-spiked residual. |
| `e3b_collinearity.py` | 15 | Collinearity with a known albite spike (bvls is stable). |
| `e4_si_validate.py` | 21 | NIST SRM 640f Si structure vs the measured Si standard - validates the calculator + LP on the real instrument (E4 seed). |
| `e5_realquartz.py` | 23 | Slice-1 decomposition on 3 real quartz-rich projects (oriented-mount intensity share is ~10x below wt%). |
| `e5b_massbalance.py` | 24 | XRF mass-balance quartz quantification + the clay-composition gap (Fe/Mg). |
| `e5c_feoxide.py` | 26 | XRD-detect leg: hematite/goethite (from CIF) not confidently detected -> Fe is in-clays. |

The `e5*` scripts read the local `~/Downloads/MudLab Test/` folder (3 `.mud`
projects + XRF + Si + a quartz `.STR`). See also the tracked prototypes
`tools/prototype_nonclay.py` (Stage 1+2 engine) and
`tools/prototype_nonclay_survey.py`.
