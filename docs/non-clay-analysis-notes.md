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

## Finding 13 — reference-space (LP) gate on the real references (experiment E1, 2026-08-06)

Re-ran the Finding-11 gate now that the 9 local references are UTF-8. Two are
measured (`quartz.txt`, `talc.txt`); seven are CALCULATED — the "Large/Small CS"
crystallite-size variants of albite, corundum, orthoclase, clinoptilolite.
`check_reference_space` (slope of ratio(ref/standard) vs 2theta; ~0 =
observed-space with LP present, strong POSITIVE = LP missing):

| reference | standard | slope /deg | read |
|---|---|---|---|
| quartz.txt (measured) | ICDD 46-1045 (HIGH) | −0.0006 | observed-space — **CLEARED** |
| talc.txt (measured) | approx | −0.009 | provisionally OK |
| Albite L / S (calc) | approx | +0.006 / +0.001 | inconclusive |
| Corundum L / S (calc) | ICDD 46-1212 (HIGH) | −0.017 / −0.017 | inconclusive |
| Orthoclase L / S (calc) | approx | +0.016 / +0.028 | inconclusive |
| Clinoptilolite (calc) | approx | −0.027 | inconclusive |

**Only `quartz.txt` is decisively cleared.** The 6 calculated references are
NOT cleared and NOT proven bad: the gate is inconclusive because the non-quartz
standards were hand-entered/approximate, and the one high-confidence calculated
anchor (corundum) shows peak-by-peak scatter (ratios 0.25–1.79) with a NEGATIVE
slope — the wrong sign for LP-missing (a truly LP-free |F|² calc ramps strongly
POSITIVE, since LP falls ~5× over 25–68°). Cross-mineral sign inconsistency
(some +, some −) confirms the flags are standard-quality noise, not a shared LP
defect (all 7 came from one pipeline → a real absence would be same-sign);
Large/Small pairs agree within each mineral. So the gate METHOD is validated on
quartz, but certifying the calculated references needs either a proper
per-mineral standard (a CIF-derived, LP-included pattern) or an import-time
"measured / calculated-with-LP" provenance flag. **Finding 11's precondition is
currently UNMET for the calculated references** — do not trust quantification
built on them yet.

Data facts recorded this session: the provided fixtures may contain quartz as
their ONLY non-clay; a Si-standard measurement for a future RIR / internal-
standard test (E4 / Q1) is at `~/Downloads/Si std 18-12-2025.xrdml` (instrument
possibly the same as `308 r1.mud`, to be confirmed).

## Finding 14 — cross-specimen sharing is not the real lever; the error is LOCAL bias (E2 / E2b)

Tested the open question "share one non-clay fraction across AD/EG/400". Spiked
all three Dh537A specimens with the SAME absolute quartz amplitude c (truth
genuinely shared), re-ran the shipped clay optimize, recovered c per-specimen vs
jointly. The per-specimen error is a CONSTANT OFFSET, not scatter: AD ≈ 0,
EG ≈ −0.50, 400 ≈ −0.10 (amplitude units) at every spike level — Finding-4 bias
(clay misfit projected onto quartz at its peak), deterministic per treatment.

- Shared-unweighted joint fit → constant ≈ −0.19 bias = the (energy-weighted)
  AVERAGE of the offsets. HELPS the worst specimen (EG −0.50→−0.19), lowers
  aggregate RMSE at ≥5% spikes (won 3/4), but HURTS the best (AD 0→−0.19).
  Averaging cuts variance, not bias — and the error here IS bias.
- **Global Rp does NOT identify the low-bias specimen**: AD and EG have nearly
  equal global Rp (~14) but opposite bias. So 1/Rp² weighting (slightly WORSE,
  −0.23) and "best global Rp" specimen (unreliable — ties AD/EG) both fail.

Verdict: REJECT naive per-specimen mean, global-Rp weighting, and global-Rp
best-specimen. KEEP shared-unweighted as the robust default (bounded averaged
bias). The discriminating quality is LOCAL (clay-fit quality at the reference's
peaks), which the per-specimen MIS-REGISTRATION NULL (Finding 8) already
measures — weighting/gating by the null, not global Rp, is the principled fix
(open experiment E2c). **This supersedes the "shared cross-specimen fraction"
open question**: sharing alone is not the win; local-quality weighting is.

## Finding 15 — collinearity is benign at the real level; the guard is a reporting convenience (E3 / E3b)

The Large/Small-CS pairs are the collinearity worst case. On the AD grid: albite
Large/Small cosine 0.979, reference Gram condition number 140 — genuinely
collinear.

- Un-spiked good-fit AD residual, fit [quartz | albite_L | albite_S] +
  nuisances: stable ZEROS, no invented minerals. Finding 5's "invented minerals"
  was a plain-NNLS-without-nuisance artifact — the nuisance formulation cures it.
- Spiked with a known albite amount (as LargeCS): bvls + non-negativity put the
  mass on the CORRECT variant (albite_L 105.7, albite_S 0.0), quartz exactly 0,
  allocation std 0.1% of total — NO sloshing. The guard (merge cosine>0.97
  columns to their mean) gives one stable "albite" number (112.6, true 111.9).
  Both carry the same ~5% underestimate = the E2/Finding-4 local bias.

Verdict: at the real collinearity level (cosine ≤0.98, cond ~140) collinearity
is NOT a numerical hazard with the current formulation. KEEP a lightweight guard
only as (a) a REPORTING convenience — merge same-mineral variants into one
number so the user isn't shown "albite-LargeCS + albite-SmallCS" — and (b) a
WARNING above a high-collinearity threshold. Not a core algorithm. Open
experiment E3c: sweep synthetic near-duplicates (cosine→0.999) to locate where
allocation destabilizes, to set that threshold. **This supersedes the "reference
collinearity" open question**: it's a guard-rail, not a blocker.

**Net (E1–E3):** the two risks the notes flagged (collinearity invention; needing
cross-specimen sharing) are LESS severe than assumed — the nuisance formulation +
non-negativity already handle collinearity, and sharing is a modest robustness
gain. The real accuracy limiters are (1) the LOCAL clay-misfit bias at the
accessory's peaks (E2) and (2) the UNVERIFIED reference intensity space of the
calculated references (E1).

## Finding 16 — a mineral structure (CIF) can be obtained and used here to make observed-space references (experiment E1b, 2026-08-06)

Motivated by E1: the calculated CS references' intensity space is unverified and
the hand-entered standards were too rough to certify them. Checked whether a
crystal structure can be obtained and used to compute a proper LP-included
pattern *inside* MudLab.

- **Obtainable (free):** α-quartz CIF fetched from the Crystallography Open
  Database (COD 9000775, ambient, P3₂21, a=4.916 c=5.4054). Free mineral-structure
  sources: **COD and AMCSD** (both open); **BGMN** ships `.str` files. ICSD is
  subscription; the CCDC/CSD holds organics / metal-organics, not minerals (the
  "CCD" asked about was most likely COD).
- **Usable here (no external library):** no powder-pattern package is bundled
  (no pymatgen / gemmi / ASE), but MudLab ships Waasmaier-Kirfel scattering
  factors. A ~150-line calculator (parse cell + symmetry ops + atoms → expand to
  3 Si + 6 O → reciprocal metric tensor d(hkl) → F(hkl)=Σ f_j(s)·DW·exp(2πi(hx+
  ky+lz)) → I=|F|²·LP) reproduces quartz: 101 at 26.63°=100, 100 at 20.85°=19.9
  (ICDD 16, measured 19.1), 112 at 50.12°=12.8 (ICDD 13). Ratio-vs-2θ slope
  computed/ICDD = **−0.004** (flat), matching quartz.txt/ICDD (−0.0006). LP is
  applied explicitly, so the result is observed-space BY CONSTRUCTION and it
  tracks both ICDD and the measured curve.

**Consequences:**
1. **E1 can be made decisive** — generate LP-included standards for the uncertain
   references (corundum, albite, orthoclase, clinoptilolite) from their COD CIFs
   and re-run the gate with real standards (open E1c; cross-check the calculator
   on corundum first, where a HIGH-confidence ICDD standard exists).
2. **Reference generation (Case-B seed)** — the same calculator can GENERATE
   clean observed-space reference curves from structures, sidestepping the
   provided files' unverified provenance entirely. This directly resolves the E1
   blocker: don't depend on the CS files — generate references from CIFs.
3. A structure-factor engine is also the first brick of Case B (calculated-
   structure accessory + Rietveld-on-residual, Finding 12).

Calculator lives this session in scratchpad `exp_e1b_quartz_from_cif.py` — worth
graduating to a tracked prototype (`tools/`).

## Finding 17 — the calculated CS references ARE observed-space; the E1 "suspect" flags were standard artifacts (experiment E1c, corundum, 2026-08-06)

Turned the from-CIF calculator (Finding 16) into a decisive E1 gate: compute a
mineral from a COD CIF (LP applied explicitly → observed-space by construction)
and compare the PROVIDED file to it. On corundum (COD 1000032, R-3c, 12 Al +
18 O):

- provided `Corundum_LargeCS.txt` vs from-CIF: ratios 0.85–1.04, slope **−0.0055
  (flat)** → the PROVIDED FILE IS OBSERVED-SPACE (LP present) → **CLEARED**.
- The from-CIF calc and the provided file AGREE with each other (both put 43.36°
  strongest, both ~40 at 37.78°); my hand-entered ICDD 46-1212 intensities
  disagreed with BOTH (43.36=66, 37.78=21) — my approximate ICDD standard was the
  outlier that produced E1's original "suspect" flag, not the files.

**This SUPERSEDES Finding 13's "hold the calculated references": the CS files
carry LP and are usable.** The E1 slope test is only as good as its standard; a
CIF-derived standard makes it decisive, and it clears corundum. Also validates
the calculator on a second crystal system (trigonal R-3c) beyond quartz.

## Finding 18 — albite corroborates (not LP-missing), but feldspar reference intensities are structure-model dependent (E1d)

Provided Albite Large/Small vs from-CIF albite (COD 9000525, triclinic C-1,
disordered Al/Si): positions match; the provided/fromCIF slope is **−0.0146**
(both variants) — NEGATIVE, the wrong sign for LP-absence (LP-missing would ramp
POSITIVE), so albite too is consistent with observed-space. The residual
deviation (22°: fromCIF 100 vs provided 65; a 35.6° peak fromCIF 29 vs provided
2.5) traces to the ALBITE STRUCTURE MODEL — feldspar relative intensities depend
strongly on Al/Si ordering, and the two sides used different albite structures.
(C-centering absences h+k odd are handled correctly by the structure-factor sum.)

Design consequence: for RIGID, ORDERED accessories (quartz, corundum) a
reference/standard is robust; for FELDSPARS the reference carries structure-model
(ordering) uncertainty — an extra accuracy limit for feldspar quantification
specifically, independent of the LP-space question.

**E1 RESOLVED:** all provided references are observed-space (quartz measured +
matched; corundum decisive; albite corroborating; orthoclase / clinoptilolite by
same-pipeline inference). The feature can use them. Separately, CIF-generated
references remain the cleaner long-term route (guaranteed LP, no provenance
doubt) and are the Case-B seed. The from-CIF calculator now spans quartz
(P3₂21), corundum (R-3c) and albite (triclinic C-1) — general enough to be the
reference/standard generator.

## Finding 19 — do we need raw-pattern references? (design, 2026-08-06)

Raised after the from-CIF calculator (Findings 16-18) + a BGMN `QUARTZ.STR` made
structure-computed references possible. Conclusion: KEEP raw (measured)
references, but as ONE of two complementary SOURCES behind a common fit-time
container; and for the non-clay feature they are residual-fit curves, NOT
mixture phases.

- **Measured references stay PREFERRED for accuracy.** A same-instrument
  measurement carries true peak widths, real crystallite-size broadening, real
  (partial) preferred orientation, and exact LP/geometry — which a structure
  pattern must MODEL (profile + PO + thermal). E1d showed calculated feldspar
  intensities are ordering-dependent and can be materially off. The from-CIF
  calculator gives correct positions + relative intensities but STICK heights
  with no real widths, so a computed reference still needs a profile convolution
  to fit the measured residual. Measured also covers poorly-crystalline /
  structure-unknown accessories.
- **Structure-computed references ADD what measured cannot:** composition
  (derived from atoms), guaranteed LP-space (no provenance doubt), refinable
  crystallography (Case B).
- **Architecture:** `RawPatternPhase` remains the fit-time CONTAINER (a curve +
  name); its curve is SOURCED from either an imported measurement OR the
  structure calculator. The Case-A residual fit is source-agnostic. Composition
  is available only when a structure backs the reference.
- **Not mixture phases:** the feature fits references to the RESIDUAL (separate
  problem); a raw accessory placed IN the mixture is zeroed by global Rp (earlier
  F5/Rp test). So: reference-as-residual-curve, not mixture-slot.

**BGMN `.str` notes (`QUARTZ.STR`):** it DOES list atoms (`SI+4`, `O-2` +
`Wyckoff=a/c`), so composition IS derivable by expanding Wyckoff multiplicities
(SG 154: a→3 Si, c→6 O = SiO2) — "no composition" = no explicit formula field,
not truly absent. BUT `.str` gives a space-group NUMBER + Wyckoff, not explicit
symmetry ops, so computing a pattern from it needs a space-group ops table
(more than a CIF, which lists ops). `.str` is Rietveld-oriented
(`GEWICHT`/`GOAL`/`SPHAR0`/`RP`) = a ready Case-B model, and uses ionic species
(MudLab's scattering CSV has charged entries). RECOMMENDATION: use CIF
(COD/AMCSD, explicit ops) as the structural source for our calculator; BGMN
`.str` is a future Case-B import that would need a space-group table.

## Finding 20 — null-weighting fails too; the per-specimen bias is unobservable → shared-unweighted stands, the Si standard is the accuracy path (E2c)

Tested weighting/gating the cross-specimen fit by the per-specimen
mis-registration null (Finding 8). It does NOT help — it is WORSE than
shared-unweighted (bias −0.25…−0.34 vs −0.19), and null-selection is worst.
Reason: the null measures what the misfit manufactures at SHIFTED (wrong)
positions, but the bias is the misfit at the reference's TRUE peak. These
differ — EG has a LOW null (~0.46) yet the LARGEST bias (−0.50), because its
glycolated-clay reflection sits under quartz's true 26.6° peak but not at random
offsets. So null-weighting up-weights exactly the wrong specimen.

Conclusion: NEITHER global Rp NOR the mis-registration null identifies the
low-bias specimen; the per-specimen bias (clay misfit projected onto the
reference at its true position) is confounded with the accessory signal itself
and is essentially UNOBSERVABLE from the specimen alone. Therefore:
- **shared-unweighted is the robust default** (won E2c 3/3, E2b 3/4); no clever
  weighting beats it.
- the accuracy ceiling is set by clay-fit quality at the accessory peaks and is
  NOT rescuable by specimen weighting.
- the null remains valid as a DETECTION threshold (Finding 8), just not as a
  bias predictor.
- ⇒ the real accuracy lever is an **internal standard (Si, E4)** giving ABSOLUTE
  quant, sidestepping the clay-relative bias. This elevates E4 from
  "nice-to-have" to the primary accuracy path.

**E1–E3 PROGRAM COMPLETE.** Net: reference space RESOLVED (E1, via the from-CIF
calculator); collinearity BENIGN (E3, guard = convenience + warning); cross-
specimen combination = shared-unweighted with an unobservable clay-relative bias
whose only real cure is the Si internal standard (E2/E2c). Ready to assemble the
isolated `nonclay/` Slice-1 engine (shared-unweighted Case A + null detection +
semi-quant labels + optional CIF reference generation). Follow-ons: E4 (Si
internal standard, now the accuracy priority) and E3c (collinearity threshold).

## Finding 21 — the Si SRM 640f standard + structure validate the calculator on the REAL instrument and seed E4 (2026-08-06)

Files supplied: the NIST **SRM 640f** Si CIF (certified a=5.431144, Si 8a,
B_iso=0.556, Fd-3m #227; the 2.1 MB is NIST's certified Cu-Kα emission profile)
and the user's measured `Si std ….xrdml` on their PANalytical Empyrean (fixed
slits ½° div + 1° AS, X'Celerator, Cu, **no monochromator**, 240 mm radius,
4–80°). The CIF's `Ge 111` monochromator fields describe NIST's own
characterisation rig, not the user's instrument.

Computed Si from the certified structure (from-CIF calculator + conventional LP)
vs the measured Si standard:

| hkl | measured | computed | ratio |
|---|---|---|---|
| 111 | 100 | 100 | 1.00 |
| 220 | 61.6 | 64.0 | 0.96 |
| 311 | 35.2 | 37.0 | 0.95 |
| 400 | 9.7 | 9.5 | 1.03 |
| 331 | 14.6 | 13.9 | 1.05 |

Ratios 0.95–1.05, slope +0.001 (flat). Mean 2θ offset +0.208° (constant across
peaks = sample-displacement/zero, exactly what a Si standard calibrates).

DECISIVE: first end-to-end validation of the from-CIF calculator + LP against a
REAL measurement on the user's OWN instrument (Findings 16–18 used only
ICDD/other-calc). It confirms (a) the conventional LP is correct for this rig
(fixed slits, no monochromator — empirically verified), so from-CIF REFERENCE
GENERATION is trustworthy for the user's data; (b) the measured-Si /
computed-|F|²·LP ratio is the instrument SCALE constant — the E4 seed for
RIR-free ABSOLUTE quantification of accessories (their own |F|² from a CIF ×
this scale → wt%), the only cure for the unobservable clay-relative bias
(Finding 20). The measured Si peak widths also give the instrumental resolution
function (Caglioti U,V,W) to broaden calculated stick references into fittable
profiles (the Finding-19 gap), and the CIF carries NIST's certified emission
profile for fundamental-parameters fitting.

INSTRUMENT MATCH — RESOLVED (user's correction: the Si-standard rig is NOT
`308 r1` but the `343 2 r3.mud` family). `343 2 r3.mud` goniometer: radius 24.0
(the `.mud` stores radius in **cm**, so 24 cm = 240 mm = the xrdml — the earlier
24-vs-240 was a cm/mm artifact, no mismatch), fixed divergence 0.5° (= the Si ½°
slit), step 0.0167° (= Si), Cu. Only difference = stored wavelength convention:
343 uses Cu Kα-average 1.54187 Å, the Si xrdml Kα1 1.540598 Å — both Cu,
reconcile for absolute work, negligible for LP. So the instrument/geometry MATCH
and the Si validation + E4 scale apply to this instrument's samples. CAVEAT: the
Si calibration is instrument-specific — it applies to the 343 family (0.0167°
step, 24 cm / 0.5° div), NOT to Dh537A (0.0131° step = a different instrument).

## Finding 22 — XRF cross-check: clay model captures structure but not full chemistry; the samples are quartz-rich (E5 setup, 2026-08-07)

User supplied XRF bulk chemistry + 3 new `.mud` projects (`348`, `416`,
`AT460 r1`) on the Si-standard instrument (step 0.0167°, Cu Kα1 — so the E4
absolute leg applies). `XRF compositions.csv` has two blocks: measured XRF (10
oxides) + MudLab clay-model composition (5 oxides). Mapping: 348→AT-348/4,
416→AT-416/1, AT460→AT-460/1. (Raw oxide values are the user's local data — kept
out of this tracked doc; only conclusions/magnitudes recorded.)

1. **The clay MODEL matches structure but NOT full chemistry.** Consistently
   across the three: MudLab OVER-predicts Al2O3 (by ~6-9 wt%), UNDER-predicts
   Fe2O3 (by ~5-9 wt%; these are Fe-rich clays, XRF Fe2O3 10-14%), and MISSES
   ~4.3% of oxides entirely (MgO ~3, TiO2 ~0.9, Na2O, MnO, P2O5 all read 0 -
   those atom types are absent from the phases). So the pattern fit captures
   stacking/spacing but the atom types are idealized Al-clays. A real limitation
   XRF exposes; it biases any chemistry-based mass balance.
2. **The samples are quartz-rich.** An Al-tracer proxy (quartz = XRF SiO2 -
   MudLab SiO2/Al2O3 x XRF Al2O3) gives ~14-17 wt% quartz for all three - real
   test cases (unlike Dh537A ~0%). BUT this proxy is biased UPWARD by the Al
   over-prediction (MudLab Al too high -> SiO2/Al2O3 too low -> quartz too high),
   so 14-17% is an upper-ish bound.

Consequence: the XRD-RESIDUAL quartz estimate (Slice-1, independent of the clay
COMPOSITION) is likely more reliable here than the chemistry proxy; comparing the
two is the cross-check, and their gap also measures the clay-composition error.
These projects have quartz visible but NO quartz reference imported yet.
NEXT (E5): generate a quartz reference (BGMN QUARTZ.STR / COD CIF / measured) on
these grids, run the Slice-1 decomposition, reconcile XRD-residual vs
XRF-chemistry quartz, and use the Si standard for the absolute (E4) scale.

## Finding 23 — E5 on real quartz-rich samples: pipeline works, but oriented-mount intensity share is ~10x below quartz weight% (orientation, not RIR) (2026-08-07)

Ran the Slice-1 decomposition on 348 / 416 / AT460 with the measured quartz.txt
(user chose "measured curve first").
- Clay fits are EXCELLENT (Rp 3.85-5.68) - well inside the quality gate.
- Quartz is DETECTED in ALL 6 specimens (clears the null; nulls 0.12-0.31%).
- Shared cross-specimen quartz estimate stable: ~1.36 / 1.49 / 1.52% (intensity
  share) for 348 / 416 / AT460.

BUT the intensity share (~1.5%) is ~10x SMALLER than the XRF chemistry weight%
(~14-17%). Cause: these are ORIENTED Ca-mounts - the clay basal reflections are
massively preferred-orientation-enhanced (sigma*), while quartz is randomly
oriented (apply_lpf=False). So area(quartz)/area(clay) in intensity heavily
under-represents quartz MASS. This is NOT an RIR-size factor - it is the clay
orientation enhancement (~5-20x on basals). The shares are also nearly FLAT
(~1.5%) while chemistry ranges 14-17%, so intensity share is not even a clean
RELATIVE measure across samples if orientation varies.

Consequence (important, reframes "semi-quantitative"): on oriented clay mounts,
integrated-intensity share is off from weight % by the clay ORIENTATION factor
(~10x here), not merely by an RIR. Converting to weight % needs the clay
preferred-orientation correction (sigma*, which MudLab's clay LP T(theta)
already models) PLUS the instrument scale (Si). Si alone gives quartz absolute
(quartz is random) but the clay-relative normalisation needs the sigma*
correction. So the honest oriented-mount readout is: reliable DETECTION +
qualitative trend, with absolute wt% requiring an orientation-corrected
calibration (E5b/E4). A randomly-oriented (bulk powder) mount removes the
orientation factor - the classic reason bulk QPA uses random powders.

## Finding 24 — E5b XRF mass balance: quartz ~9-14 wt%, and a large Fe2O3 deficit flags Fe-clays or an Fe-oxide accessory (2026-08-07)

NNLS of XRF oxides onto [clay composition (shipped `mixture_composition`) |
quartz (SiO2=100)] per sample:
- QUARTZ = 11.1 / 9.3 / 13.7 wt% (of clay+quartz) for 348 / 416 / AT460 -
  orientation-INDEPENDENT (chemistry), LOWER than the crude Al-tracer proxy
  (14-17%) because the multi-oxide fit tempers the Al bias.
- The fit pins SiO2 exactly via quartz (the only SiO2-flexible phase), so
  quartz = the SiO2 the clay does not explain, and W_clay is set by Al2O3.
  Al2O3 is over-predicted (Finding 22), so quartz still carries that bias;
  improving the clay Al/Fe atom types is the key to tightening it.
- BIG residual: Fe2O3 UNDER-explained by ~5-9 wt% (model ~4.7, XRF 9.7-13.6) +
  MgO by ~2-3. Either the clays are Fe/Mg-bearing (model uses idealised
  Al-clays) OR a separate Fe-OXIDE ACCESSORY (hematite ~33.2/35.6 deg, goethite
  ~21.2 deg) - a second non-clay.

The hybrid working as designed: XRF quantifies quartz + FLAGS the Fe/Mg gaps; the
XRD-detect leg can resolve whether the Fe deficit is Fe-in-clays or an Fe-oxide
accessory (fit a hematite/goethite reference to the residual). NEXT: (E5c)
XRD-check the residual for an Fe-oxide accessory; then improve the clay
composition (Fe/Mg/Al atom types) to tighten the quartz number.

## Finding 25 — domain considerations, experimental-design physics, and data requirements (user input, 2026-08-07)

**PLANNED OUTPUT: a scientific paper.** When the trials are done, draft a paper
covering everything considered/tried, each option's merits/demerits, what does
and does NOT violate the physics, and the final recommendation. Findings 1-24+
are the evidence base - keep them COMPLETE and PHYSICS-EXPLICIT so the paper can
be written from them.

**Domain observations (user manual inspection of the 348/416/AT460 specimens):**
- Confirmed: a little hematite/goethite is present (matches the Finding-24 Fe
  deficit); possibly some non-clay DETRITAL MICA; the clay-fraction modelling was
  done hastily (matches the Finding-22 composition bias).
- DETRITAL-MICA CAVEAT (physics): detrital muscovite 002 = 10 Å = the SAME
  spacing as illite, so in the residual it is largely ABSORBED by the illite fit
  and is nearly invisible to the residual method. Separating detrital mica from
  authigenic illite by oriented XRD is intrinsically hard (both 10 Å; mica is
  sharper/larger-crystallite) - a real limitation to state in the paper.

**Experimental-design physics:**
- A SINGLE PROJECT = TREATMENT VARIANTS of ONE physical sample. A non-clay
  present in one specimen is present in ALL (AD / EG / heated) at the same
  amount - the physical basis for the SHARED cross-specimen fraction (Finding
  14). Confirmed correct by the mineralogy, not just the statistics.
- HEAT TREATMENT (350-550 C) destroys/modifies many clay species (smectite &
  kaolinite collapse / dehydroxylate), so the HEATED specimen shows a HIGHER
  relative % of non-clay minerals -> the heated pattern is the MOST SENSITIVE
  for non-clay detection/quantification. (348/416/AT460 have only AD+GL, no
  heated -> recommend including a heated specimen for non-clay work.)

**Data requirements (essential vs optional) - toward the UI design ("what do we
want from the user?"):**
- ESSENTIAL: a `.mud` with a GOOD clay fit (low Rp - the residual is only as
  clean as the clay fit); the XRD pattern(s); at least one non-clay REFERENCE
  (a measured curve or a structure) to identify/fit against.
- OPTIONAL, each unlocking a capability: XRF oxides -> mass-balance
  QUANTIFICATION (weight %) + flags missing phases (the Fe deficit); a Si
  standard on the same instrument -> ABSOLUTE scale; a CIF/STR structure ->
  generate references without a measurement + composition for the mass balance;
  a HEATED specimen -> better non-clay sensitivity.
- WHAT TO ASK THE USER (UI): required = choose a well-fit mixture + load
  reference pattern(s) for the suspected non-clays; optional = paste/import XRF
  oxides, load a Si standard, load CIF/STR structures.

## Finding 26 — E5c: hematite/goethite not confidently detected; the Fe deficit is mostly Fe-in-clays (2026-08-07)

Generated hematite (COD 9000139, Fe2O3, a=5.038 c=13.772) + goethite (COD
9002158, FeOOH) references from CIF (from-CIF calculator, broadened to ~0.12 deg
FWHM), fit to the AD residuals with the detection rule:
- Quartz DETECTED all 3 (1.4-1.6% intensity, clears null).
- Hematite NOT detected (0.15-0.31%, at/below null 0.15-0.33%) - marginal.
- Goethite NOT detected (0.03-0.23%, below null).

No confident discrete Fe-oxide accessory - consistent with the user's "little
hematite/goethite." BUT: (1) ORIENTED-MOUNT SUPPRESSION (Finding 23) means a
randomly-oriented Fe-oxide is ~10x suppressed, so even a few % hematite shows
only ~0.2-0.5% intensity - exactly where these marginal signals sit; oriented-
mount non-detection does NOT rule out a few % hematite. (2) So the ~5-9% Fe2O3
deficit (Finding 24) is most likely dominated by Fe-IN-CLAYS (idealised Al-only
clay atom types missing octahedral Fe), with possibly a little hematite the
oriented mount cannot confirm. Definitive resolution needs a HEATED specimen or
a RANDOM-POWDER mount (Finding 25). Detrital mica not fittable (muscovite 002 =
10 A = illite; micas orient like clays -> absorbed by the illite fit).

Conclusion -> (b): the Fe deficit is a CLAY-COMPOSITION problem, so improving the
mass-balance accuracy requires editing the CLAY atom types (Fe/Mg-bearing
illite/smectite) - a USER modelling task; the non-clay feature only READS the
clay composition and stays frozen w.r.t. the clay model.

## Finding 27 — clarifications (Q1-Q4) + E5 must be REDONE with heated specimens (2026-08-08)

User clarifying questions after E5; ANSWERS (to be shown at the start of the next
session):
1. RAW vs STRUCTURE/CIF quartz reference: worth trying from-CIF quartz as METHOD
   VALIDATION - it will NOT change the quartz QUANTITY (that comes from XRF via
   the orientation factor, Finding 23) but it validates the from-CIF reference-
   generation path so we can make references for minerals with NO measured
   standard (feldspar, etc.). Use the COD CIF (validated E1b) + Si-resolution
   broadening; the BGMN `.str` needs a space-group/Wyckoff table (deferred to
   Case B).
2. MICA: NOT tried, deliberately. Detrital muscovite 002 = 10 A = illite
   (absorbed by the illite fit) AND micas orient like clays (not a random
   accessory); XRF also cannot separate them (both K-Al-silicates). So detrital
   mica is INDISTINGUISHABLE from illite by BOTH legs of the hybrid - a hard
   limitation for the paper. (Can fit a muscovite reference to demonstrate.)
3. IRON OXIDES: a SINGLE FREE-AMPLITUDE fit per sample (NOT varying fractions /
   not a spike series) - the fit finds the best hematite/goethite amount in the
   actual residual and tests it vs the null. Notation "0.15% (null 0.20) X" =
   best-fit 0.15% intensity share, detection floor (null) 0.20%; 0.15 < 0.20 ->
   below the floor -> NOT detected. A hematite SPIKE-SENSITIVITY test would bound
   the oriented-mount detection limit (how much hematite hides below the floor).
4. HEATED vs AD/GL: 348/416/AT460 had ONLY AD+GL (no heated). AD vs GL: quartz
   detected in both, shares similar (1.3-2.0%), scatter from glycol expanding the
   smectite basal (changes the clay area). Heated UNTESTED on quartz-bearing data
   (only Dh537A 400C, E2, which had the worst clay fit Rp 30.5). "Heated enhances
   non-clay detection" (Finding 25) is sound physics but UNTESTED -> gap.

**ACTION: E5 MUST BE REDONE.** The user forgot to include HEATED variants in
348/416/AT460 and will update the `.mud` files. Once done, re-run E5/E5b/E5c with
the heated specimens - the heated pattern should show a HIGHER relative non-clay %
(Finding 25), directly testing that hypothesis and improving non-clay detection.
Findings 23-26 are AD+GL-only and PROVISIONAL until the heated re-run.

Three exposed follow-ups: (a) from-CIF quartz vs measured; (b) muscovite fit to
demonstrate the mica limitation; (c) hematite spike-sensitivity (detection limit).

## Finding 28 — heated variants (K-saturated, loose); the two quartz peaks + the illite-003 overlap; heating helps (2026-08-08)

Re-examined 348/416/AT460: each has 5 specimens. The heated variants (400, 550 C)
are K-SATURATED and LOOSE (not in the mixture); the AD/EG (Ca-saturated) are in
the mixture. Full set per sample: Ca-AD, Ca-EG(GL), K-AD, K-400, K-550 (files
have 400+550, no 500).

Measured both quartz peaks per specimen - 101 (d=3.343 A = 0.334 nm, 26.66) and
100 (d=4.257 A = 0.426 nm, 20.86):
- QUARTZ 101 (0.334) OVERLAPS the illite/mica 003 (3.33 A = 26.75) - a CLASSIC
  clay-XRD collision - plus glycol-smectite 005. So 101 is CONTAMINATED: it swings
  with the clay (348 K: 5.0/5.5/6.8 across AD/400/550) and is grossly inflated in
  glycolated (348 Ca-GL 14.1 = quartz + smectite 005 + illite 003).
- QUARTZ 100 (0.426) is CLEAN and ~CONSTANT across each heating series (348 K:
  0.8/0.7/0.8; 416 K: 0.9/0.7/0.7) - the RELIABLE quartz measure.
- 100/101 RATIO = a quartz-purity diagnostic (pure quartz ~0.18-0.22). Measured
  mostly BELOW (0.08-0.16), lowest in glycolated (Ca-GL 0.08-0.11) = most 101
  contamination.

Can the two peaks + treatments improve quartz determination? YES:
1. PREFER the clean 0.426 (100) over the illite-003-contaminated 0.334 (101).
2. Fit the FULL quartz reference (both peaks, fixed 100/101 ratio): the clean 100
   ANCHORS the amplitude, so an illite-003-inflated 101 cannot over-estimate
   quartz. (Concrete reason the residual method resists the overlap.)
3. HEATING helps: K-550 collapses expandable clays -> removes the glycol-smectite
   004/005 overlaps -> cleaner quartz region; K-550 is the best quartz specimen.
   Realizes Finding 25.
4. QUARTZ IS CONSTANT within each cation-mount heating series (same mount
   re-heated) = an internal consistency check.

CAVEATS: heated = K-saturated (SEPARATE mounts from the Ca-AD/EG in the mixture),
so "quartz constant" holds WITHIN the K series and WITHIN the Ca series, not
across; and heated are UNMODELED (loose) -> to DECOMPOSE them the collapsed-clay
state must be modeled + added to the mixture (user task), or use the direct
two-peak analysis. This UPDATES the Q4 answer (Finding 27): heated variants DO
exist (loose, K-saturated), and they materially help.

GENERAL COMMENT (user, design scope): which non-clay phases to include is the
USER's choice (like clay phases). Quartz is the most common + usually dominant
non-clay; the headline deliverable is QUARTZ FRACTION vs TOTAL CLAY FRACTION.

Q1 (user's call): construct the quartz reference from the CIF via the SPECIMEN
GONIOMETER (wavelength distribution / Soller, not a generic Gaussian); use both
measured + CIF today, CIF preferred.

## Finding 29 — Q1 result: CIF quartz reference (via the goniometer) beats the measured curve (2026-08-08)

Goniometer here is single-wavelength Ka1 (0.154056 nm), so the clays were computed
without a Ka2 doublet. Constructed the quartz reference the SAME way: from-CIF
structure factors (LP incl.) at the goniometer Ka1, broadened to the Si 0.11 deg
FWHM. On 348 Ca-AD (clay Rp 4.58):
- measured quartz.txt: quartz 1.61%, null 0.25%, detected, 100/101 = 0.19.
- CIF (via goniometer): quartz 1.08%, null 0.12%, detected, 100/101 = 0.20.

Both detect quartz with the textbook 100/101 (~0.19-0.20). The CIF reference is
CLEANER: lower null (0.12 vs 0.25 -> better signal-to-null), textbook ratio, built
in the SAME Ka1 space as the clay model with the Si-derived instrumental width ->
matched to THIS instrument, and available for ANY mineral with no measured
standard. The share differs (1.08 vs 1.61) because it depends on the reference
peak WIDTH (measured curve is from an unknown instrument) - affects the intensity
share but NOT the XRF quantity. RECOMMENDATION: use CIF-constructed references
(goniometer Ka1 + Si width) as the default; validates the from-CIF generation path
for the feature. (BGMN .str would give the same once a SG/Wyckoff table is added.)

## Finding 30 — (c): baseline removal doesn't help the modeled fit; heated helps ID not quant for illite-rich samples; the quartz strategy (2026-08-08)

Part 1 - BASELINE REMOVAL on the modeled Ca-AD residual: fitting quartz with a
morphological baseline strip vs the standard nuisance-column fit changes the
quartz area by only +1 / -3 / -2% (348/416/AT460) - NEGLIGIBLE. Confirms
Finding 6: the nuisance columns already absorb the broad clay-shape drift, so a
baseline strip adds nothing on a MODELED residual. (Baseline removal is only
relevant when fitting WITHOUT a clay model - e.g. a heated specimen with no
model - to isolate sharp peaks from a broad hump.)

Part 2 - HEATED K-series (K-AD/400/550), clean quartz 100 (0.426) share of the
baseline-stripped pattern:
- Q100 share stays ~2-3% across AD->400->550 (does NOT rise toward weight%).
  These are ILLITE-rich (ISK-dominated) samples, and ILLITE (mica) is thermally
  STABLE - its 10 A basal survives 550 C and stays strong/oriented. So heating
  does NOT convert them to random powder for the total-pattern share; the
  orientation suppression PERSISTS. (The random-powder advantage is real for
  KAOLINITE/SMECTITE-rich samples - basals weaken/vanish - but LIMITED for
  illite-rich.)
- Q101 share (12-22%) INCREASES with heating, 100/101 FALLS (0.16->0.11):
  collapsed-smectite 003 piles onto illite 003 at 26.6 -> 101 MORE contaminated
  when heated. The 101 share (~15%) coincidentally matching the XRF weight%
  (~15%) is a TRAP (101 = quartz + clay 003), not a quartz measure.

RECOMMENDATION (quartz):
1. Reference: CIF via the goniometer + Si width (F29).
2. Fit locus: the residual (Pattern - total clays) on AD/EG (clays intact,
   Rp<6). Use both peaks with the CLEAN 100 (0.426) as the ANCHOR; never trust
   the 101 (0.334) alone (illite/smectite 003 overlap, worse when heated).
3. Baseline removal: SKIP on modeled residuals (<3%); only for model-less fits.
4. Heated specimens: use for IDENTIFICATION (clean quartz, no glycol-smectite
   overlap) - but for illite-rich samples they do NOT deliver quartz weight%
   (the illite basal survives).
5. Quartz weight%: XRF mass balance is the quantifier (orientation-independent,
   F24); XRD identifies + gives the orientation-biased intensity ratio. Headline
   deliverable (quartz fraction vs total-clay fraction): the XRD residual gives
   it in INTENSITY (biased low for quartz by orientation), XRF gives it in
   WEIGHT.

For OTHER non-clays: mineral-specific strategies (user's point) - each has its
own overlaps / orientation / thermal behaviour.

## Finding 31 — what we ask from the user + the non-clay UI spec (toward Slice 2, 2026-08-08)

The feature decomposes a clay-dominated pattern into clay vs non-clay and
quantifies the non-clays (headline: QUARTZ FRACTION vs TOTAL CLAY FRACTION).
Which non-clays to include is the USER's choice, exactly like clay phases (today:
quartz only; more later, each with a mineral-specific strategy).

**INPUTS - tiered by what they unlock:**

ESSENTIAL (detection + relative intensity):
- A `.mud` with a GOOD clay fit (low Rp) - the residual is only as clean as the
  clay fit. Analyse the AD/EG specimens (clays intact); heated = identification.
- The user SELECTS the non-clay phases to look for (quartz default/dominant;
  feldspar, calcite, Fe-oxide, ... optional).
- Per non-clay: a REFERENCE PATTERN, source = either
  (i) a MEASURED curve (import), or
  (ii) a STRUCTURE (CIF preferred, or BGMN `.str`) -> the app CONSTRUCTS the
       reference via the SPECIMEN GONIOMETER + instrumental width (F29). CIF
       better.

OPTIONAL - for QUANTIFICATION in WEIGHT % (the XRF route):
- The sample's XRF BULK OXIDE composition (the mass-balance constraint; without
  it -> intensity-share only, orientation-biased, F23).
- Each non-clay's COMPOSITION for the mass balance:
  known mineral -> formula -> oxides (quartz = SiO2); or from the CIF/`.str`
  atoms x Wyckoff multiplicities; or user-entered oxide wt% (EPMA/literature).

OPTIONAL - for ABSOLUTE scale + reference broadening (the Si route):
- A Si standard MEASUREMENT on the SAME instrument (+ its CIF) -> the
  instrumental resolution (FWHM for reference construction) + the absolute scale
  (E4).

FROM THE `.mud` ALREADY (no user action): the goniometer (wavelength, Soller,
radius, divergence mode) - used to construct references and set the LP.

**NON-CLAY UI (Slice 2 - what the dialog collects):**
- A NON-CLAY PHASE MANAGER (mirrors the clay phase editor): add/remove non-clay
  phases; per phase: name/mineral; reference source
  [Import measured curve] | [Load CIF/.str -> construct via the goniometer];
  composition (for the mass balance) [pick mineral -> auto oxides] |
  [from CIF/Wyckoff] | [enter oxide wt%].
- An XRF INPUT: paste/import the sample's bulk oxide composition.
- A Si-STANDARD input (optional): load the Si measurement + CIF.
- A RESULTS panel: per phase x specimen detection (clears the null?), the XRD
  intensity share, the XRF mass-balance weight %, quartz-vs-total-clay; with
  SEMI-QUANT labelling + FLAGS (XRF-vs-model oxide residuals -> improve the clay
  atom types; the orientation caveat; the illite-003 overlap on the 101).

**Design notes carried from the trials:** CIF reference via goniometer + Si width
(F29); use both quartz peaks, anchor on the clean 100 / 0.426, not the 101
(F28/F30); fit locus = residual on AD/EG, no baseline strip on modeled residuals
(F30); weight % from the XRF mass balance, intensity share is orientation-biased
low (F23); the UI FLAGS XRF-vs-model oxide gaps to prompt clay-atom-type fixes
(F22/F26); non-clays are RESIDUAL-fit curves, NOT mixture phases (F19); the
engine stays READ-ONLY over the clay path.

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
