# Non-clay decomposition — the algorithm (as implemented)

A methods-section description of how MudLab2 estimates the non-clay (accessory)
minerals in a clay-dominated, oriented-mount XRD pattern, on top of an existing
clay model. The headline output is the **quartz fraction vs the total clay
fraction**; the user chooses which non-clay minerals to include (as with clay
phases). This is the paper-ready statement of the shipped feature
(`src/mudlab/nonclay/`); the supporting evidence is in
[`non-clay-analysis-notes.md`](non-clay-analysis-notes.md) (Findings 1–31).

The method is **additive and read-only**: it never changes the clay
optimize/refine/calc path; it only *reads* the fitted clay pattern.

---

## Inputs

- A **mixture with a fitted clay model** — for each specimen: the measured pattern
  `exp(2θ)`, the calculated pattern `calc(2θ)`, and the per-phase clay patterns.
  The clay fit should be good (low Rp); air-dried / glycolated specimens (clays
  intact) are the quantification locus.
- One or more **non-clay reference patterns**, each either a measured curve or one
  built from a crystal structure (CIF).
- **Optional:** the sample's **XRF bulk oxide composition** (for weight %); a
  **Si-standard** measurement (for the reference peak width); a per-reference
  **oxide composition** (auto from CIF, a built-in mineral table, or typed).

---

## Stage 0 — clay fit (existing, unchanged)

The mixture's clay phases are fit to each specimen by the shipped optimizer
(phase fractions, specimen scale, background shift), giving the calculated
pattern `calc = LP·S_clay·scale + bg`. This stage is untouched.

## Stage 1 — the residual

Per specimen:

    residual(2θ) = exp(2θ) − calc(2θ)

with the **clay shape** = Σ (per-phase clay patterns) and the **machine-correction
shape** = the carrier the background shift multiplies. The residual contains the
non-clay reflections plus the clay-model misfit plus background.

## Stage 2 — reference fit (Case A)

The clay optimizer cannot grow a sharp accessory peak, but it *does* re-absorb
part of an accessory through the two global knobs it is free to move — the
specimen **scale** (multiplies the clay shape) and the **background shift**
(multiplies the correction shape). So the residual is modelled as

    residual  ≈  Σ_i a_i · ref_i(2θ)  +  d_scale · clay_shape  +  d_bg · correction

and solved as a **bounded linear least-squares** (SciPy `lsq_linear`, method
`bvls`) with the **reference amplitudes a_i ≥ 0** and the two nuisance
coefficients `d_scale, d_bg` **free (sign-unconstrained)**. The free nuisance
columns are the exact inverse of the clay optimizer's re-adjustment, so the a_i
come out unbiased **without touching a line of the clay code**.

Reference intensities are placed on the specimen's own 2θ grid through the
shipped calc path (the goniometer wavelength distribution is applied; a
random-oriented accessory reference gets **no Lorentz-polarisation factor and no
machine correction**, matching a measured powder).

**Shared cross-specimen fit.** Because the treatment variants (AD / EG / heated)
are one physical sample, the same non-clay is present in all of them at the same
amount. One amplitude per reference is therefore fit **shared** across the
mixture's specimens, each specimen keeping its own free clay/correction nuisance
columns (this is the robust default; per-specimen weighting by fit quality does
not help — the per-specimen error is a systematic local bias, not variance).

## Stage 3 — detection (the mis-registration null)

A textbook least-squares σ is useless here (the residual is the clay misfit,
smooth and strongly autocorrelated). Instead the detection threshold is
non-parametric: **shift the reference by ±0.6…4.0° 2θ**, to positions where its
peaks do not belong, and fit it identically (this time *without* the
non-negativity, to read the signed noise floor). The **95th percentile** of the
spurious amplitude over those offsets is the null — what this particular misfit
can manufacture for a curve with these peak shapes.

A mineral is **reported as detected** only when all three hold:
1. the specimen's clay fit is good enough — **Rp ≤ 40**;
2. the estimate **clears its mis-registration null**;
3. the estimate **clears an absolute 0.5 %** of the modelled signal.

## Reporting — two numbers, deliberately distinct

- **XRD intensity share** = area(a_i·ref_i) / (clay area + Σ non-clay area), per
  reference and specimen. This is **semi-quantitative**: on an *oriented* clay
  mount the clay basal reflections are enormously preferred-orientation-enhanced
  while a random accessory is not, so the intensity share **under-represents the
  accessory's weight fraction** (empirically ~10× low). Reported with that caveat,
  and with the detection flag.

- **Weight % (when XRF is supplied)** = an **oxide mass balance**, orientation-
  independent. Solve, by non-negative least squares over the reporting oxides,

      XRF_oxide  ≈  W_clay · clay_comp  +  Σ_i W_i · nonclay_comp_i

  where `clay_comp` is the clay model's oxide composition and `nonclay_comp_i` is
  each accessory's oxide composition (derived from its CIF atoms, a built-in
  mineral table, or typed by hand). The phase weight fractions `W` give the
  **quartz fraction vs total clay fraction** directly. The per-oxide residual is
  reported as a flag — a large Fe/Mg deficit means the clay atom types are
  idealised and should be improved (this is what limits the weight-% accuracy).

The **XRD leg identifies and detects** the non-clays; the **XRF leg quantifies**
them. Each dataset is used for its strength.

---

## Reference construction

- **Measured curve** — imported as-is (observed-intensity space by construction).
- **From a CIF** — parse the unit cell + explicit symmetry operations + atoms;
  build the structure factors `F(hkl) = Σ_j f_j(s)·occ_j·e^{-B s²}·e^{2πi(hx+ky+lz)}`
  using MudLab's Waasmaier–Kirfel scattering factors; the stick intensity is
  `|F|²·LP` at the **specimen goniometer's wavelength**; broaden each stick to the
  **instrumental FWHM** (measured from a Si standard, else a 0.10° default). The
  same atom list yields the mineral's **oxide composition** for the mass balance.
  (A CIF with only a space-group *number*, or a BGMN `.str` with Wyckoff letters,
  needs a space-group operations table — not yet supported.)

The reference must be **observed-intensity space** (LP included): the residual
keeps its LP weighting (subtraction removes the clay *term*, not a common
factor), so an LP-free reference would be misweighted (LP spans ~35× over
4.6–35°). A measured curve satisfies this; the from-CIF construction applies LP
explicitly.

---

## What is physically sound, and what is not

- **Sound:** the residual is still observed-intensity space; the nuisance-column
  fit recovers the accessory amplitude unbiased *to the extent the clay fit is
  good at the accessory's peaks*; the mis-registration null is a defensible,
  non-parametric detection threshold; the XRF mass balance is orientation-
  independent.
- **The accuracy ceiling** is the clay-fit quality *at the accessory's peak
  positions* (a systematic per-specimen bias that is not observable from the
  specimen alone), and — for weight % — the clay model's oxide composition.
- **Not usable as-is:** the oriented-mount intensity *share* as a weight fraction
  (orientation bias); the quartz 101 (d ≈ 0.334 nm) peak alone (it overlaps the
  illite/mica 003 at ~26.6°, worse on heating) — the fit is anchored by the clean
  quartz 100 (d ≈ 0.426 nm) via the reference's fixed 100/101 ratio.

## Limitations (to state)

- Detrital **mica is indistinguishable from illite** by both XRD (muscovite 002 =
  10 Å = illite) and XRF (same K-Al-silicate chemistry).
- Integrated intensity is not weight % without an internal standard; every XRD
  number is labelled semi-quantitative, and weight % comes from the XRF balance.
- For **illite-rich** samples, heating (which collapses smectite/kaolinite but not
  thermally-stable illite) gives only limited "random-powder" benefit for the
  accessory intensity.
