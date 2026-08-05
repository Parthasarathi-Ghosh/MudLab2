# Non-clay decomposition — prototype findings

**Status: EXPERIMENTAL, branch `feature/non-clay-analysis` only. No shipped code
changed.** This records what a throwaway Stage 1 + Stage 2 prototype measured on
Dh537A + the measured quartz reference, so the design can be committed on
evidence rather than on assumption. The prototype is `tools/prototype_nonclay.py`.

The goal of the feature: on top of the existing clay fit, (1) estimate the
clay : non-clay proportion and (2) quantify individual non-clay phases — without
touching the clay calc / optimize / refine path.

## Setup

Dh537A: 3 specimens (AD / EG / 400), 2θ 4.59–34.99°, ~2316 points at 0.0131°.
3 phase slots (Illite, Kaolinite, IS R1 Ca-*), stored fit mean Rp 19.13
(per specimen Rp 11.8 / 15.1 / 30.5). Non-clay references are the measured
curves in the user's local "Raw pattern phases" folder, loaded as
`RawPatternPhase` and pushed through the shipped calc path
(`calculate_phase_intensities`), so a reference contributes exactly what it
would contribute from a mixture slot.

Validation is a **spike test**: add a known `c · I_quartz` to each specimen's
experimental pattern (sized so the added area is a known fraction of that
specimen's fitted clay area), re-run the *unmodified* clay `optimize`, then see
how much Stage 1 + Stage 2 recover. Truth is therefore exact.

## Finding 1 — the crude Stage-1 estimator is unusable

Area of the positive residual, as a share of clay + positive residual:

| specimen | "non-clay" from +residual | quartz actually found (Stage 2) |
|---|---|---|
| AD  | 10.51 % | 0.06 % |
| EG  | 11.05 % | 0.00 % |
| 400 | 30.07 % | 0.00 % |

The residual is large and roughly symmetric — |residual| is 19.5 / 26.5 / 69.6 %
of the clay area, split +131/−87, +124/−140, +337/−208. Half of a symmetric
misfit is positive, so "positive residual area" measures **fit quality, not
mineralogy**. It must not be shipped as the clay : non-clay number. The
clay : non-clay proportion has to come from the Stage-2 model (the fitted
reference curves), not from the raw residual.

## Finding 2 — the assumed bias mechanism is wrong

The prior assumption was that the clay fit absorbs non-clay peaks, and that
excluding the non-clay peak windows from the clay Rp fit would de-bias the
residual. Measured: **excluding the quartz windows (20.45–21.27°, 26.13–27.15°)
changes recovery by less than 0.3 pp at every spike level.** It is not the
mechanism.

The clay model *cannot* absorb a sharp quartz peak — it has 3 phase fractions
and no freedom to grow a narrow line. The spike shows up directly in the fit
quality instead: mean Rp goes 19.13 → 19.07 → 19.62 → 21.26 → 24.74 as the spike
goes 0 → 2 → 5 → 10 → 20 %.

What the clay fit *does* absorb is the two global knobs the optimizer is free to
move: the specimen `scale` (multiplies the clay shape) and `bgshift` (multiplies
the machine-correction shape). Across the spike series specimen 400's scale ran
1.032 → 1.202. So the Stage-1 residual is not (non-clay + noise), it is

    residual = δscale · clay_shape + δbg · correction_shape + Σ aᵢ · refᵢ

## Finding 3 — put the clay and background shapes in as free nuisance columns

Fitting the references against the residual with `clay_shape` and
`correction_shape` added as **sign-unconstrained** columns (reference amplitudes
still ≥ 0, solved with `scipy.optimize.lsq_linear`, method `bvls`) is the exact
inverse of that re-adjustment. Recovered vs true, clipped rows excluded:

| specimen | slope | intercept | plain NNLS slope / intercept |
|---|---|---|---|
| AD  | 0.995 | +0.000 | 0.993 / +0.066 |
| EG  | 1.026 | −3.667 | 1.020 / −3.781 |
| 400 | 0.887 | −0.665 | 0.880 / −0.928 |

It also kills the **false positives**: at 0 % spike every specimen returns
exactly 0.00 %, where plain NNLS returned up to 0.06 % and the morphological
variant up to 0.81 %. Cost is one bounded linear least-squares per specimen —
milliseconds, no optimizer, no threading.

## Finding 4 — the residual bias is measurable (but it is a bias, not a threshold)

The remaining error is dominated by a per-specimen **offset**, not a slope: the
clay misfit projected onto the reference curve. Re-running the nuisance fit with
the non-negativity dropped gives that displacement directly from the *unspiked*
pattern, and it matches the spike-test intercepts almost exactly:

| specimen | signed quartz, unspiked | spike-test intercept |
|---|---|---|
| AD  | −0.01 % | +0.000 |
| EG  | −3.60 % | −3.667 |
| 400 | −0.87 % | −0.665 |

Where the clay model over-predicts under a reference's peaks, that much of that
mineral is cancelled before any is seen — which is why EG reads 0.00 % quartz
until the spike passes ~5 %.

**Do not use this number as a detection threshold** (an earlier draft of this
work did, and it was wrong). The unclipped signed fit *equals the fitted
amplitude itself* whenever that amplitude is positive, so a rule like
`value > k × signed` can never fire for a genuine detection — it produced a 100 %
false-negative rate on the spike test. It measures bias; the threshold has to be
built separately (Finding 8).

The residual slope deficit tracks clay-fit quality: 400 (Rp 30.5, R² 0.61) loses
~11 % of added quartz; AD (Rp 11.8, R² 0.97) loses none. **Non-clay accuracy is
governed by the clay fit at the non-clay peak positions**, not by the Stage-2
algorithm.

## Finding 5 — multi-reference selectivity needs the nuisance terms

With 5 references (quartz, talc, albite, orthoclase, corundum) against the
unspiked residual, plain NNLS invents minerals — corundum 0.26 % on EG, albite
1.08 % on 400 — with *negative* explained-residual, i.e. it is chasing misfit.
With the nuisance columns nearly all collapse to 0.00 %. Reference collinearity
is a real risk and a detection threshold is mandatory before a mineral is
reported at all.

## Finding 6 — morphological baseline (#1B) does not pay off

A rolling-min/max opening of the residual (the cheap stand-in for ORPL
`bubblefill`) was tried at 0.79 / 1.51 / 3.02° widths. It partially removes the
offset but **introduces** positive spurious signal at zero spike (0.17 % AD,
0.81 % 400) and makes multi-reference selectivity distinctly worse (2.84 % and
4.70 % of invented minerals). The nuisance-column formulation dominates it on
every metric. Recommend dropping #1B rather than keeping it as a complement.

## Finding 7 — Dh537A genuinely has ~no quartz

Stage 2 returns 0.00–0.06 % quartz on all three specimens. This confirms the
earlier read that Optimize driving the quartz fraction to zero was correct
behaviour, not a sensitivity failure — there is no quartz signal in 4.6–35° to
find. A clay-fraction oriented mount is expected to be quartz-poor.

## Finding 8 — the detection threshold: a mis-registration null

A textbook least-squares standard error is not usable here: the Stage-1 residual
is the clay misfit, which is smooth and strongly autocorrelated, so a σ that
assumes white noise over ~2300 points is wildly optimistic.

What works is non-parametric — **shift the reference to where its peaks do not
belong and fit it identically**. Any amplitude that comes back is spurious: it is
what this particular misfit can manufacture for a curve with these peak shapes.
The 95th percentile over offsets of ±0.6…4.0° 2θ is the threshold
(`null_threshold_pct`). It behaves like a real noise band — roughly constant per
specimen and independent of how much quartz is actually present:

| specimen | null-95 threshold | spike 0 % | spike 5 % | spike 20 % |
|---|---|---|---|---|
| AD  | ~0.5 % | 0.49 | 0.54 | 0.76 |
| EG  | ~0.5 % | 0.51 | 0.47 | 0.46 |
| 400 | ~1.3 % | 1.30 | 1.24 | 1.37 |

## Finding 9 — the calibrated rule, and what it costs

Report a mineral only when **all three** hold:

1. the specimen's clay fit is good enough to quantify against — Rp ≤ 40;
2. the estimate clears its mis-registration null (Finding 8);
3. the estimate clears an absolute 0.5 % of the modelled signal.

Rule 3 is not decoration: on the synthetic goldens the fit is near-perfect, so
the null band collapses to 0.03–0.10 % and bare interpolation residue
(0.02–0.09 %) reads as a detection without it. It is also the honest limit —
integrated-intensity XRD without RIRs cannot defend a sub-0.5 % accessory.

Resulting sensitivity on the Dh537A quartz spike (detection limit):

| specimen | clay fit | limit |
|---|---|---|
| AD  | Rp 11.8, R² 0.97 | **1 %** |
| 400 | Rp 30.5, R² 0.61 | **3 %** |
| EG  | Rp 15.1, R² 0.92 | **5 %** (bias-limited, not threshold-limited) |

## Finding 10 — specificity survey: no false positives

Ran the full estimator + rule over all 13 fixtures / 26 specimens
(`tools/prototype_nonclay_survey.py`).

- **Every real sample returns clay 100.0 % : non-clay 0.0 %.** The largest raw
  reading anywhere is 0.89 % talc against a 3.43 % null — correctly withheld.
  Quartz never exceeds its null in any specimen.
- **9 of 26 specimens are gated out** by rule 1 (Rp 42–66). All are 400 °C
  specimens plus the whole of `Dh2040A 14Jul26.mud` (R² 0.11–0.47). That is the
  correct answer, not a failure: those clay fits cannot support accessory
  quantification.
- **The synthetic Illite-Smectite goldens are the decisive control** — single
  calculated phase, R² = 1.000, exactly zero non-clay by construction. All eight
  return 0.0 % non-clay. An earlier version of the rule flagged talc/albite/
  clinoptilolite at 0.06–0.09 % on these; that is what forced rule 3.

So on samples expected to be non-clay-poor, the method says so. The
proportions are realistic.

## Finding 11 — intensity space: the LP factor does NOT cancel in the residual

Raised as a challenge to the whole approach: if the residual is a subtraction,
does the θ-dependent Lorentz-polarisation factor cancel out, leaving something
that is no longer a valid experimental pattern?

**It does not cancel.** Subtraction is linear — it removes the clay *term*, not a
factor common to both terms:

    I_exp  = LP·S_clay + LP·S_nonclay + bg
    I_calc = LP·S_clay_model + bg_model
    resid  = LP·S_nonclay + LP·(S_clay − S_clay_model) + δbg

LP multiplies the non-clay term as well and survives into the residual. It would
only cancel under division, or if it were additive. The residual is therefore
still in observed-intensity space, which is precisely what makes it comparable
to a measured reference pattern.

**But the underlying concern is the right one**, and it is make-or-break: the
reference curve must be in the *same* space as the residual. MudLab's LP varies
by **35.6×** over 4.6–35° 2θ on this instrument (5.14 at 5°, 0.29 at the quartz
101 peak), so a space mismatch would misweight the fit severely.

Verified for `quartz.txt` against the standard powder pattern (ICDD 46-1045
relative intensities already include LP), over 20–68° where LP itself varies ~5×:

| 2θ | standard | file (normalised) | ratio |
|---|---|---|---|
| 20.86 | 16 | 19.1 | 1.20 |
| 26.64 | 100 | 100.0 | 1.00 |
| 50.14 | 13 | 13.8 | 1.06 |
| 68.14 | 8 | 8.5 | 1.07 |

Ratios sit near 1.0 with **no trend against 2θ**; were LP missing, the 20.86°
peak would read ~5× weak relative to 68.14°. So the file is observed-space and
`RawPatternPhase.apply_lpf = False` is correct — applying MudLab's LP on top
would double-count it.

A second reason that flag is right: MudLab's LP is **clay-specific**. `T(θ)`
carries σ* (preferred orientation) and the Soller geometry. A randomly-oriented
accessory does not share the clay's σ*, so MudLab's LP would be the *wrong* LP
for it even if one wanted to apply one. Taking the reference as measured is the
correct design.

**Limitation this exposes in the spike test (Findings 3–4, 9):** the spike was
generated through the same non-LP reference path it was then fitted with. That
is self-consistent, so it validates the *estimator* — but it is **blind to a
reference/residual space mismatch by construction**. The peak-ratio check above,
not the spike test, is what rules that out. "The reference is observed-space" is
therefore an unchecked precondition: a user importing a calculated
structure-factor pattern would get silently wrong numbers.

Benign related asymmetry: clay phases here have `apply_correction = True` while
`RawPatternPhase.apply_correction` is hard-coded `False`. On this instrument the
machine correction is identically 1.0 (fixed slits, no absorption correction) so
it does not bite — but under automatic divergence slits it becomes sin θ and the
two paths would diverge.

## Finding 12 — is fitting the residual a "Rietveld refinement on the residual"?

Two candidate Stage-2 engines, and they are **not the same kind of method**:

- **Empirical references (the prototype above).** Each `RawPatternPhase`
  contributes one scalar amplitude, profile frozen; nothing structural — no
  lattice, peak shape, or peak position is refined. This is **not Rietveld**; it
  is full-pattern *summation* QPA with measured standards (the PONKCS /
  observed-pattern family), solved as one bounded linear least-squares.
- **Calculated-structure accessory (CIF / BGMN).** Compute the accessory pattern
  from structure factors and refine its scale / lattice / profile (± preferred
  orientation, atom params) against the target. Refining a *calculated* pattern
  against data **is** a Rietveld refinement — of the accessory, run on the
  residual rather than on the raw scan. "Rietveld on the residual" describes only
  this case.

**When is residual-Rietveld the same answer as a proper joint (clay + accessory)
Rietveld?** Frisch–Waugh–Lovell gives the exact condition. Linearise as
`y = A·x_clay + B·x_acc + ε` with fit weights `W`. The accessory block of the
*joint* solution regresses `M_A·y` on `M_A·B`, where
`M_A = I − A(AᵀWA)⁻¹AᵀW` projects out the clay column space — i.e. you fit the
accessory to the clay-subtracted residual **but with the clay directions also
projected out of the accessory columns**. The sequential "fit accessory to the
residual" regresses `M_A·y` on the *raw* `B`. They coincide **exactly iff
`BᵀW A = 0`** — accessory basis W-orthogonal to clay basis (no peak overlap, the
clay cannot re-absorb accessory intensity).

Three conditions for equivalence, and whether they hold on Dh537A:

| condition | holds? |
|---|---|
| accessory ⊥ clay under `W` | ✗ — quartz-101 sits under clay intensity; the clay `scale`/`bgshift` re-absorb it (Findings 2–4) |
| else: partial the clay directions out of the accessory columns too (FWL residualise both sides) | partly — the `clay_shape` + `correction_shape` free nuisance columns ARE that Gauss–Newton residualisation, but only for the clay's two *global* DOF (scale, bgshift), not its structural params (σ*, CSDS, probabilities, d001) |
| Rietveld weights `wᵢ ≈ 1/yᵢ_obs`; residual noise white | ✗ — the residual fit is unweighted OLS, and the residual noise is smooth, autocorrelated clay *misfit*, not counting noise (Finding 8), so Rietveld ESD / GoF do not transfer (→ the mis-registration null replaces textbook σ) |

The prototype's own recovery slopes **are** this theorem measured: **0.995** where
the clay fit is good (AD, Rp 11.8) → near-exact equivalence; **0.887** where it is
poor (400, Rp 30.5) → the residual non-equivalence, because the clay's
*structural* misfit under the quartz peak was never residualised out. To make the
calculated-structure case a genuine one-step joint-Rietveld equivalent, add the
clay Jacobian columns `∂clay_calc/∂θ_clay` (structural, not just scale) as
nuisance terms and carry `wᵢ = 1/yᵢ_obs` — that converges to the joint accessory
scale **without touching the frozen clay optimize / refine**.

**What no version escapes.** Rietveld's standardless weight % needs
`Wₚ ∝ Sₚ·(ZMV)ₚ` — a crystal structure (Z, cell volume) for *every* phase, the
clays included. MudLab's clays have no ZMV (disordered mixed-layer formalism, not
a single-structure phase), so even a perfect residual-Rietveld yields the
accessory's structure but leaves the **clay : non-clay ratio integrated-intensity
/ semi-quantitative** until RIRs or an internal standard are added. Empirical
(Case A) and calculated (Case B) are identical on this limit.

**Design consequence.** Case A (empirical amplitudes + the two nuisance columns)
is the evidence-backed default: cheap, robust, slope ≈ 1 on good clay fits,
honestly semi-quantitative. Reserve Case B (a real accessory Rietveld engine) for
when refinable accessory crystallography or internal-standard absolute quant is
specifically wanted — the only regime where it buys something Case A cannot.

## Proposed design (evidence-based)

- **Stage 0** unchanged clay optimize. Clay path stays frozen.
- **Stage 1** residual = exp − calc, from the existing
  `SpecimenStatistics.residual_pattern`. Report it as a *diagnostic curve only* —
  never as the clay : non-clay number (Finding 1).
- **Stage 2** per specimen, one `lsq_linear` (bvls) of
  `[ref₁ … ref_k | clay_shape | correction_shape]` against the residual,
  reference amplitudes ≥ 0, nuisance columns free. Non-clay area per mineral =
  amplitude × area of the un-modified reference curve.
- **Clay : non-clay proportion** derived from the Stage-2 areas, not the residual.
  Any `RawPatternPhase` already in the mixture counts as non-clay, not clay.
- **Detection rule** as Finding 9 (quality gate + mis-registration null +
  0.5 % absolute floor). Report the null threshold next to every number, and the
  signed displacement (Finding 4) as the bias estimate — they are different
  quantities and must not be conflated.
- **Gate the whole readout** on specimen Rp: above ~40 report nothing.
- **Guard the reference intensity space** (Finding 11). References must be
  observed-space (measured, or calculated *with* LP and powder geometry). Keep
  `apply_lpf = False`, and warn on import when a curve's peak ratios do not match
  its standard powder pattern — this precondition is currently unchecked and
  fails silently.
- **Drop** the exclusion-window iteration (Finding 2) and the bubble baseline
  (Finding 6).

Unchanged honesty flag: integrated intensity is not weight %. Without RIRs or an
internal standard every number here is **semi-quantitative / relative** and must
be labelled as such.

## Reference-file encoding

7 of the 9 reference curves in the local "Raw pattern phases" folder (Albite ×2,
Clinoptilolite, Corundum ×2, Orthoclase ×2) are **UTF-16 LE**, which
`file_parsers/csv_io._read_lines` (hardcoded `utf-8-sig`) cannot read. Per the
project owner these files will simply be **replaced with UTF-8 exports**, so no
app change is planned. The prototype carries its own tolerant loader
(`_read_text`) purely so the survey could use all six reference minerals.

## Open questions for the real implementation

- **Reference collinearity.** The survey deliberately used one variant per
  mineral; the Large/Small-CS pairs are near-duplicates and would be severely
  collinear in one design matrix. A real UI lets the user load both. Needs
  either a collinearity guard or a documented restriction.
- **Cross-specimen consistency.** Quartz content is a property of the sample,
  not of the AD/EG/400 prep, yet each specimen is currently fitted
  independently (Dh537A: 0.00 / 0.00 / 0.00, but under spike 16.58 / 13.43 /
  14.08). Fitting one shared non-clay fraction across a mixture's specimens
  would use all three patterns and cut the per-specimen bias — worth testing.
- **Rp ≤ 40 gate** is calibrated on 26 specimens from 5 real samples. Thin
  evidence; revisit as more projects are seen.
