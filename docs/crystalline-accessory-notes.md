# Crystalline accessory phases — treatment, background, and a path to structural refinement

Methodology and design notes for handling non-clay **crystalline accessory**
minerals (quartz, feldspar, calcite, an internal standard) in a clay-dominated
mixture. Today these enter as **raw-pattern phases** (a fixed measured curve);
this note records how that works, the background question, why it is physically
sound, and what it would take to later import a *structure* and refine it beside
the clays. It is a developer/methodology note, kept separate from the end-user
manual. (The goniometer behaviour discussed alongside this lives in the user
manual, "Which goniometer the calculation uses".)

Related: `docs/non-clay-analysis-notes.md` (the residual-targeted, EXPERIMENTAL
sibling on the `feature/non-clay-analysis` branch — a *measured* reference fit to
the clay-subtracted residual, rather than refined jointly in the mixture).

---

## 1. How a raw-pattern accessory is calculated

A `RawPatternPhase` carries a fixed measured curve (`raw_pattern_x/y`) and has no
structure — the pattern *is* the phase (`src/mudlab/models/raw_pattern_phase.py`).
In the calc it is treated verbatim:

- Its stored curve is **resampled onto the specimen's 2θ grid** (`np.interp`, zero
  outside the stored range) — `calculations/phases.py` `_get_raw_intensity`.
- `apply_lpf = False`, `apply_correction = False`: **no Lorentz-polarisation
  factor and no machine/geometry correction** (unlike a modelled clay `Phase`).
  Taken exactly as measured.
- The **wavelength distribution is still applied** uniformly, like every phase
  (`calculations/specimen.py` `apply_wavelength_distribution`; a single-line
  spectrum doubles the intensity, absorbed by `scale`).
- It is then scaled by **its fraction × the specimen scale** and summed into the
  total next to the modelled phases and the specimen's single background term:
  `total = Σ (fraction_j · scale · I_j) + bgshift · correction`
  (`calculations/specimen.py` `calculate_scaled_intensities`).
- Only its **fraction** (plus the shared scale/background) is refinable — there is
  no internal structure to fit.
- Like every phase, it is computed through **that specimen's own goniometer**
  (wavelength, range) — see the goniometer note in the manual.

So whatever is in `raw_pattern_y` — peaks **and** any background it contains — is
what enters the total, scaled by fraction × scale.

## 2. Should the accessory's background be retained?

Not required by the code — MudLab uses the stored curve as-is. But for a
**crystalline** accessory you should generally **strip the background** first:

- The specimen already carries **one** background term (`bgshift · correction`).
  A background inside the reference is **added on top of it → double-counted**.
- That background **scales with the accessory's fraction**, so it entangles the
  fraction with background-matching: the global-Rp optimiser can move the fraction
  to fit flat regions instead of the peaks, **biasing the quantification**.
- `bgshift` is a single scalar × the machine correction curve — a rigid, near-flat
  background. It **cannot subtract an arbitrary curved background** the reference
  brings, so that misfit cannot be cleaned up by the fit.
- → Flatten/subtract the reference's background before importing, so it
  contributes **net peaks only**.

The exception is an **amorphous / broad-hump** component (glass, poorly ordered
material): there the broad shape *is* the physical signal, so keep it. The
distinguishing principle: does the background belong to the *component you are
representing* (keep) or is it *instrument/shared background already handled by
`bgshift`* (strip)?

There is no "remove raw-phase background" action in the app — **Remove Background**
acts on *specimens*. Prepare the reference (background-subtracted for a crystalline
accessory, intact for an amorphous hump) **before** importing it.

## 3. Is it physically correct to add a background-removed crystalline accessory?

Yes — and it is not just a convenience, it is what makes the model valid.

**Linear superposition.** Quantitative phase analysis rests on the total being a
linear sum of per-phase contributions plus one background — exactly what MudLab
computes. For that to hold, each `I_j` must be the phase's **diffracted
contribution only**, and there must be **one** background for the whole pattern.

**Why the reference background must come out.** A measured pattern of pure quartz
= quartz's Bragg peaks **plus** an *instrumental/environmental* background (air
scatter, holder, slits, Compton of the mount). That background is **not a
phase-proportional physical quantity** — it belonged to the reference measurement,
not to "how quartz diffracts", and it does not scale with quartz content. It is
also **already modelled once** by the mixture's `bgshift`. Leaving it in adds a
second, fraction-scaled background → double-counting and a biased fraction.
Removing it restores the correct linear model.

**The one real caveat — *which* background.**
- *Instrumental/environmental* background (air, holder, slits, Compton) → not part
  of the phase's scattering → remove it. Correct.
- The phase's own *diffuse* scattering (thermal diffuse, and especially any
  amorphous / short-range-order content travelling with the material) **does**
  scale with amount and is legitimate; a crude spline/linear subtraction can strip
  it too. For well-crystallised quartz the Bragg peaks dominate, so "subtract the
  background, keep the net peaks" is an excellent approximation; for a
  poorly-crystalline accessory it degrades.

**Other conditions for it to be *quantitatively* correct:**
1. **Same intensity space.** The reference must already be observed-intensity space
   with the same LP treatment as the sample — MudLab applies no LP/correction to
   raw phases, so it trusts the file to carry it (verified for `quartz.txt`).
2. **Same geometry/texture.** Clays are fitted with preferred orientation (σ\*); a
   randomly-oriented accessory has different texture and should be measured under
   comparable optics.
3. **Clean subtraction** — no clipped peak tails, no negative intensities (they
   distort peak *areas*, which set the fraction).
4. **Semi-quantitative without RIR** — integrated-intensity fractions ≠ weight %
   without reference-intensity ratios or an internal standard.

## 4. Fixing an accessory's fraction and excluding it from Optimize/Refine

The per-phase refine checkbox (Edit Mixtures) lets you pin an accessory's fraction
and exclude it from refinement. When you then **run Optimize/Refine**:

- The excluded fraction is **held exactly** at your value (it is "static").
- The remaining **checked** phases are re-fitted **and renormalised to fill
  `1 − Σ(fixed)`**, so the whole vector still sums to 1
  (`calculations/mixture.py` `_Problem` + `parse_solution`).

Qualifications:
- **Manual editing alone does not adjust the others** — `Mixture.calculate` uses
  the fraction vector verbatim; the rebalancing happens only during Optimize/Refine
  (or F5 on an auto-run mixture). Before optimising, the vector may not sum to 1
  (the specimen `scale` absorbs the overall level, so the pattern is still valid).
- **A fixed value > 1** (or several fixed fractions summing > 1) is infeasible; a
  guard renormalises *all* fractions (including the "fixed" one) to restore
  feasibility. Keep fixed values ≤ 1 (and their sum ≤ 1) to preserve them exactly.
- **Excluding every phase** leaves no free fraction to move — Optimize then adjusts
  only scale/background.

This is exactly the desired behaviour for the physics in §3: pin the accessory at
a known amount and let the remaining phases redistribute over the leftover
`1 − fixed`, keeping the total normalised.

## 5. Future — importing a structure (CIF/BGMN/ICDD) and refining side-by-side

**Feasible and additive.** The refinement machinery is phase-type-agnostic with two
explicit plug-in seams, so a Rietveld-style crystalline phase type can be refined
in the *same* parameter vector as the clays, without touching the clay path.

**The two seams:**
1. **Intensity dispatch is already a `type` switch** — `calculations/phases.py`
   `get_diffracted_intensity` routes `"Phase"` → clay calc, `"RawPatternPhase"` →
   measured curve, else raises. Add a `"CrystallinePhase"` branch → a new
   structure-based calc. Everything downstream (`calculate_scaled_intensities`,
   the fraction/scale/bg optimiser) sums `fraction · I · scale` linearly for any
   `I`, so a crystalline phase mixes with the clays unchanged.
2. **Refinables are generic getter/setter wrappers** — `calculations/refinement.py`
   `enumerate_refinables` → `_phase_refinables` builds `Refinable(name, getter,
   setter, bounds)` objects. A `_crystalline_refinables(phase)` returning cell
   `a,b,c,α,β,γ`, profile `U,V,W`, scale, B-factors, preferred orientation drops
   straight in; the `Refiner` flattens all refinables into one L-BFGS-B vector, so
   a quartz cell edge and a clay σ\* refine in the same step.

**The additional calculations (the new engine):**
- Parsers CIF/BGMN/ICDD → unit cell, space group, asymmetric-unit atoms (x,y,z,
  occupancy, ADP/B).
- Reflection generation (hkl in the 2θ range from cell + the specimen's goniometer
  wavelength), d-spacings, multiplicities.
- Structure factors
  $F_{hkl} = \sum_j f_j(Q)\,\mathrm{occ}_j\,e^{2\pi i (h x_j + k y_j + l z_j)}\,e^{-B_j \sin^2\theta / \lambda^2}$.
  **Head start:** MudLab already ships Waasmaier–Kirfel scattering factors
  (`data/atomic_scattering_factors.csv` + the atom-type library), so $f_j(Q)$ is in
  hand.
- A profile function (pseudo-Voigt/TCH `U,V,W,X,Y`, or fundamental-parameters /
  BGMN-style) convolved over `range_theta`, plus the **conventional
  Bragg–Brentano LP** — *not* MudLab's clay LP (which bakes in σ\* preferred
  orientation + Soller geometry). Optional March–Dollase PO.
- Uses the **same per-specimen goniometer** as everything else.

**Reusable vs genuinely new:**

| Reusable as-is | Genuinely new |
|---|---|
| Waasmaier–Kirfel scattering factors, atom-type model | 3D crystallography: space groups, general hkl, 3D structure factors (clay components are 2D *layers*, not 3D cells) |
| `Refinable`/`Refiner`, L-BFGS-B, fraction + per-parameter masks | Conventional profile + Bragg–Brentano LP |
| Linear phase sum, per-specimen goniometer | CIF/BGMN/ICDD parsers |

**Why the clay 1-D engine can't be reused — projection onto c\* vs the spherical
average.** A natural idea is to reduce the accessory to a 1-D problem along c\* and
reuse the clay engine. It does not work, and it is worth being precise about why.

The clay engine is 1-D along c\* *because the clay is oriented*: platy crystallites
lie flat, so only the 00l reflections are seen, and a 00l structure factor uses
only the atoms' $z$ (the layer's electron density projected onto c):

$$F(00l) = \sum_j f_j\, e^{2\pi i\, l z_j}$$

A crystalline accessory (quartz) is a **random powder** — its grains do not
co-orient with the clay, so it shows *every* reflection at its own scattering
magnitude

$$|Q| = \frac{2\sin\theta}{\lambda} = \frac{1}{d_{hkl}}$$

(quartz: 100, 101, 110, …, none of them 00l). Projecting the accessory's atoms
onto c\* — keep $z$, collapse $x, y$ — would yield only quartz's **00l series**:
peaks at the wrong positions, with the real reflections gone. So projection would
*misrepresent* the accessory, not improve compatibility.

The correct 3-D → 1-D reduction for a random powder is the **spherical (Debye)
average** over orientations — a reduction over the *magnitude* $|Q|$ that places
every hkl at its own $2\theta$ — which is a different operation from projecting the
structure onto one axis. That is what a powder calculation does, and its output
$I(2\theta)$ then sums linearly with the clay's.

So **compatibility lives at the shared observable $I(2\theta)$, not at the
structure-factor method**: the clay computes $I(2\theta)$ via its 1-D c\* engine,
the accessory via a 3-D powder engine, and MudLab sums them on the common $2\theta$
axis. They are already compatible there — which is exactly why the raw-pattern
reference and the linear mixture sum work today, and why a structural accessory
needs the *new* 3-D engine: it cannot be shortcut by reusing the clay's c\*
projection. It is also why their orientation/LP treatments differ — the σ\*
preferred-orientation correction applies to the oriented clay, not to a random
accessory.

*Caveat:* a genuinely platy, co-oriented accessory could take a 00l-only treatment
— but with its **own** c-repeat, still a separate calculation, not a projection
onto the *clay's* c\* (the two c\* axes are different d-spacings, so projecting one
structure onto the other's axis has no physical meaning).

**The two hard parts — physics/numerics, not plumbing:**
1. **Intensity-space / scale commensurability (the crux).** For the linear sum to
   be *quantitatively* correct, the crystalline phase's intensities and the clays'
   must land on the **same absolute scale** — the clays carry a clay-specific LP,
   the accessory the conventional one. This is the RIR / scale-factor problem (same
   issue flagged for the reference-pattern approach). Get it wrong and the pattern
   *shape* is fine but the *quantification* is off.
2. **Conditioning.** A minor accessory (quartz at a few %) contributes little to
   the full-pattern global Rp — its peaks barely move it. So refining its
   *crystallography* jointly is ill-constrained; a flat vector mixing clay
   σ\*/CSDS with quartz cell/atoms/PO can be poorly conditioned. In practice **fix
   the structure from the database and refine only scale (± a peak width / PO)** —
   exactly how accessory and internal-standard phases are treated in mainstream
   Rietveld QPA. The existing per-parameter refine flags + the fraction mask make
   that selective refinement natural.

**Constraint honoured.** All of the above is purely additive — a new `type` branch
+ a new refinable builder + new parsers — so the existing clay calc / optimize /
refine are untouched.

**When to prefer the residual approach instead.** For a *minor* accessory, the
residual-targeted fit (`docs/non-clay-analysis-notes.md`: fit a reference to the
clay-subtracted residual) is better-conditioned than joint global-Rp refinement —
worth weighing against "side-by-side in the same mixture" when this lands.
