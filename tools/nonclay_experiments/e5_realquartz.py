#!/usr/bin/env python
"""E5 - run the Slice-1 non-clay decomposition on the 3 real quartz-rich projects
with a MEASURED quartz reference, and compare to the XRF chemistry proxy.

Each project: keep the user's stored clay fit (calculate), decompose against the
measured quartz.txt, report per-specimen quartz share + detection + the shared
cross-specimen estimate. The engine's nonclay_pct is an integrated-INTENSITY
share (semi-quantitative), NOT weight % - the Si standard (E4) converts it; here
we compare qualitatively to the Al-tracer chemistry proxy (weight %).
"""
from __future__ import annotations

import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402
from mudlab import nonclay  # noqa: E402
from mudlab.nonclay import estimator  # noqa: E402
from mudlab.file_parsers.mud_project import load_mud  # noqa: E402

DIR = os.path.join(os.path.expanduser("~"), "Downloads", "MudLab Test")
REF = os.path.join(os.path.expanduser("~"), "Downloads", "Raw pattern phases", "quartz.txt")
PROJECTS = [("348.mud", "AT-348/4", 14.4),
            ("416.mud", "AT-416/1", 17.4),
            ("AT460 r1.mud", "AT-460/1", 15.8)]


def main():
    quartz = nonclay.load_reference(REF, name="quartz")
    qx = np.asarray(quartz.raw_pattern_x)
    print("reference quartz.txt: %d pts  2th %.1f-%.1f  Imax %.0f"
          % (qx.size, qx.min(), qx.max(), np.max(quartz.raw_pattern_y)))

    for proj_name, sample, chem in PROJECTS:
        proj = load_mud(os.path.join(DIR, proj_name))
        mix = proj.mixtures[0]
        mix.calculate()  # respect the user's stored clay fit
        res = nonclay.decompose_mixture(mix, [quartz], detect=True)
        print("\n" + "=" * 66)
        print("%s  (sample %s)   XRF chemistry proxy ~%.1f wt%% quartz"
              % (proj_name, sample, chem))
        for sr in res.specimens:
            rr = sr.references[0]
            print("  %-22s Rp=%5.2f  quartz %5.2f%% (intensity)  null=%.2f%%  detected=%s"
                  % (sr.name, sr.rp, rr.pct, rr.null_pct, rr.detected))
        # shared amplitude -> intensity share, on the first specimen's scale
        s0 = [s for s in mix.specimens if s is not None][0]
        x, _r, clay, _c = estimator.specimen_residual(s0)
        a_clay = estimator.area(clay, x)
        q_row = estimator.reference_intensities(s0, [quartz])[0]
        a_shared = estimator.area(res.shared_amps[0] * q_row, x)
        pct_shared = 100.0 * a_shared / (a_clay + a_shared) if a_clay else 0.0
        print("  SHARED across specimens: quartz %.2f%% (intensity share)" % pct_shared)
    print("\nNOTE: intensity share != weight %%; the Si standard (E4) gives the "
          "absolute conversion. Chemistry proxy is an upper-ish bound (clay Al "
          "over-predicted).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
