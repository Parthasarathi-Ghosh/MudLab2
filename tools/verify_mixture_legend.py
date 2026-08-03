#!/usr/bin/env python
"""#1 - the main-plot phase index (old app: plot_mixtures).

The pattern plot draws an upper-right legend of every mixture that owns a
displayed specimen: the mixture name, then one row per phase slot -
"<label>: <fraction %>" with a colour swatch per specimen-cell filling that
slot, in the phase's display_color. This drives the real PatternPlot head-less
and checks:

  - a legend (AnchoredOffsetbox) is drawn when a shown specimen is in a mixture,
    and it names exactly the mixtures that own the shown specimens;
  - it lists every phase slot's label + fraction (formatted as the app does),
    and one visible colour swatch per non-empty phase cell;
  - no legend is drawn for a specimen that belongs to no mixture;
  - the figure renders without error;
  - multi-select (the main window builds ONE PatternPlot for the whole
    selection): several specimens of one mixture show that mixture ONCE, a
    single-specimen subset still shows its mixture, and two specimens from
    different mixtures show BOTH blocks (each once).

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_mixture_legend.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no suitable fixture.
"""

from __future__ import annotations

import glob
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from matplotlib.offsetbox import AnchoredOffsetbox
from matplotlib.patches import FancyBboxPatch
from PySide6.QtWidgets import QApplication

from mudlab.file_parsers.mud_project import load_mud
from mudlab.models.mixture import Mixture
from mudlab.plot_controller import PatternPlot

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in [os.path.join(_REPO, "tools", "sample_projects", "308 r1.mud")] + \
            sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        if not os.path.isfile(path):
            continue
        project = load_mud(path)
        for mix in project.mixtures:
            shown = [s for s in mix.specimens if s is not None
                     and s.has_experimental_data]
            if mix.m >= 1 and shown:
                return path, project, mix, shown
    return None, None, None, None


PATH, PROJECT, MIX, SHOWN = _fixture()
if PROJECT is None:
    print("No fixture with a mixture + a specimen with data; skipping (exit 2).")
    raise SystemExit(2)


def _legend_of(plot):
    for art in plot.axes.artists:
        if isinstance(art, AnchoredOffsetbox):
            return art
    return None


def _collect(obj, texts, swatches):
    """Walk an offsetbox tree: gather TextArea strings and the visible colour
    swatches (FancyBboxPatch inside an AuxTransformBox, alpha == 1)."""
    if type(obj).__name__ == "AuxTransformBox":
        for child in obj.get_children():
            if isinstance(child, FancyBboxPatch) and (child.get_alpha() or 0) >= 1.0:
                swatches.append(child)
        return
    gt = getattr(obj, "get_text", None)
    if callable(gt):
        try:
            t = gt()
        except Exception:
            t = None
        if isinstance(t, str) and t:
            texts.append(t)
            return  # leaf: a TextArea also exposes its inner Text via
                    # get_children(), which would double-count the string
    gc = getattr(obj, "get_children", None)
    if callable(gc):
        for child in gc():
            _collect(child, texts, swatches)


def main():
    print("fixture: %s  mixture: %s  (%d slots, %d shown specimens)"
          % (os.path.basename(PATH), MIX.name, MIX.m, len(SHOWN)))

    plot = PatternPlot(SHOWN, PROJECT)
    legend = _legend_of(plot)
    check("a legend is drawn for a shown mixture", legend is not None)
    if legend is None:
        return _report()

    texts, swatches = [], []
    _collect(legend, texts, swatches)

    # names exactly the mixtures owning the shown specimens
    want_names = {m.name for m in PROJECT.mixtures
                  if any(s in m.specimens for s in SHOWN)}
    check("legend names every owning mixture",
          all(name in texts for name in want_names))

    # every phase slot label + fraction, formatted as the app does
    rows_ok = True
    for m in PROJECT.mixtures:
        if m.name not in want_names:
            continue
        for i, label in enumerate(m.phase_labels):
            frac = float(m.fractions[i]) if i < len(m.fractions) else 0.0
            rows_ok &= "{}: {:>5.1f}".format(label, frac * 100.0) in texts
    check("every phase slot shows its label + fraction%", rows_ok)

    # one visible swatch per non-empty phase cell across the owning mixtures
    want_swatches = sum(
        1 for m in PROJECT.mixtures if m.name in want_names
        for row in m.phase_matrix for cell in row if cell is not None
    )
    check("one colour swatch per non-empty phase cell (%d)" % want_swatches,
          len(swatches) == want_swatches)

    # renders without error
    try:
        plot.canvas.draw()
        drew = True
    except Exception as exc:  # pragma: no cover
        print("  draw() raised:", exc)
        drew = False
    check("the figure renders with the legend", drew)

    # a specimen in NO mixture gets no legend
    orphan = next((s for s in PROJECT.specimens
                   if s is not None and s.has_experimental_data
                   and not any(s in m.specimens for m in PROJECT.mixtures)), None)
    if orphan is not None:
        check("no legend for a specimen in no mixture",
              _legend_of(PatternPlot([orphan], PROJECT)) is None)
    else:
        print("  (no mixture-free specimen in this fixture; skipped that check)")

    _check_multi_select()
    return _report()


def _texts_of(plot):
    legend = _legend_of(plot)
    if legend is None:
        return []
    texts, _sw = [], []
    _collect(legend, texts, _sw)
    return texts


def _check_multi_select():
    """The main window builds ONE PatternPlot for the whole selection
    (show_specimen_plots), so a SHIFT/CTRL multi-select is just a longer
    specimens list. Verify the legend behaves across selections."""
    # Same mixture, several specimens selected -> one block, not one per specimen.
    if len(SHOWN) >= 2:
        multi = _texts_of(PatternPlot(SHOWN, PROJECT))
        check("multi-select of one mixture's specimens shows it ONCE",
              multi.count(MIX.name) == 1)
    else:
        print("  (mixture has <2 shown specimens; skipped the single-block check)")

    # A subset (one specimen of the mixture) still shows the mixture.
    one = _texts_of(PatternPlot([SHOWN[0]], PROJECT))
    check("a subset (one specimen) still shows its mixture", MIX.name in one)

    # Two specimens from DIFFERENT mixtures -> both blocks. Synthesize a second
    # mixture over a data specimen that MIX does not own (308 r1 has spares).
    proj2 = load_mud(PATH)
    mix1 = proj2.mixtures[0]
    spare = next((s for s in proj2.specimens
                  if s is not None and s.has_experimental_data
                  and s not in mix1.specimens), None)
    mix1_spec = next(s for s in mix1.specimens
                     if s is not None and s.has_experimental_data)
    if spare is None or not proj2.phases:
        print("  (no spare specimen / phase to build a 2nd mixture; skipped)")
        return
    mix2 = Mixture(name="Mix2-test")
    mix2.add_specimen_slot(spare, 1.0, 0.0)
    mix2.add_phase_slot("Q", 1.0)
    mix2.set_phase_at(0, 0, proj2.phases[0])
    proj2.add_mixture(mix2)

    both = _texts_of(PatternPlot([mix1_spec, spare], proj2))
    check("multi-select across two mixtures shows BOTH blocks",
          mix1.name in both and mix2.name in both)
    check("each of the two mixture blocks appears once",
          both.count(mix1.name) == 1 and both.count(mix2.name) == 1)


def _report():
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- mixture-legend (phase index) verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
