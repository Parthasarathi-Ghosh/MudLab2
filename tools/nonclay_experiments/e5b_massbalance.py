#!/usr/bin/env python
"""E5b - XRF mass-balance quantification of quartz (the hybrid's quant leg).

For each sample solve, by non-negative least squares over the oxides:
    XRF_oxide  ~=  W_clay * clay_composition + W_quartz * quartz(SiO2=100)
The clay composition comes from the shipped mixture_composition (7 oxides). This
quantifies quartz (orientation-independent) AND its per-oxide residual exposes
the clay-composition gap (Finding 22: Mg/Na/Ti missing, Al over / Fe under).

Compares to the XRD detection (Finding 23: quartz detected in all) and the crude
Al-tracer proxy. Keep the mass-balance approach if quartz is sensible and the
residual is informative; note that the clay-composition bias limits accuracy
until the clay atom types are improved.
"""
from __future__ import annotations

import csv
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from scipy.optimize import nnls  # noqa: E402
from mudlab.calculations.composition import mixture_composition  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

DIR = os.path.join(os.path.expanduser("~"), "Downloads", "MudLab Test")
PROJECTS = [("348.mud", "AT-348/4"), ("416.mud", "AT-416/1"),
            ("AT460 r1.mud", "AT-460/1")]


def load_xrf():
    rows = list(csv.reader(open(os.path.join(DIR, "XRF compositions.csv"), encoding="utf-8")))
    hdr = rows[0]
    out, cur = {}, None
    for r in rows[1:]:
        if not r or not r[0].strip():
            continue
        if r[0].strip() in ("XRF", "MudLab"):
            cur = r[0].strip(); out[cur] = {}; continue
        if cur and len(r) >= 11:
            try:
                vals = {hdr[i]: (float(r[i]) if r[i].strip() else 0.0) for i in range(1, 11)}
                out[cur][r[0].replace(" ", "").upper()] = vals
            except ValueError:
                pass
    return out


def main():
    xrf = load_xrf()["XRF"]
    for proj, sample in PROJECTS:
        mix = load_mud(os.path.join(DIR, proj)).mixtures[0]
        mix.calculate()
        _names, oxide_rows = mixture_composition(mix)
        order = [o for o, _ in oxide_rows]                       # 7 oxides
        clay = np.array([pcts[0] for _o, pcts in oxide_rows])    # specimen 0
        xr = xrf.get(sample.replace(" ", "").upper())
        if xr is None:
            print("%s: no XRF row for %s" % (proj, sample)); continue
        xvec = np.array([xr.get(o, 0.0) for o in order])
        quartz = np.array([100.0 if o == "SiO2" else 0.0 for o in order])

        A = np.column_stack([clay, quartz])
        W, rnorm = nnls(A, xvec)
        W_clay, W_quartz = W
        recon = A @ W
        # renormalise the two-phase weights to 100% (the modelled part)
        tot = W_clay + W_quartz
        wq_pct = 100.0 * W_quartz / tot if tot else 0.0

        print("\n" + "=" * 64)
        print("%s (%s):  QUARTZ = %.1f wt%% of (clay+quartz)   [W_clay=%.3f W_q=%.3f]"
              % (proj, sample, wq_pct, W_clay, W_quartz))
        print("  %-6s %8s %8s %8s" % ("oxide", "XRF", "model", "resid"))
        for i, o in enumerate(order):
            print("  %-6s %8.2f %8.2f %+8.2f" % (o, xvec[i], recon[i], xvec[i] - recon[i]))
        # oxides the model structurally cannot explain (clay has 0 there)
        unexp = sum(xvec[i] for i, o in enumerate(order) if clay[i] == 0 and o != "SiO2")
        print("  unexplained (clay comp = 0 for these oxides): %.2f wt%%" % unexp)
    print("\nNOTE: quartz here is orientation-independent (chemistry). Accuracy is "
          "limited by the clay-composition bias (Al over / Fe under / Mg-Na-Ti "
          "missing); improving the clay atom types tightens it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
