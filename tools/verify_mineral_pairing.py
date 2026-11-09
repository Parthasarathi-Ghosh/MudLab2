#!/usr/bin/env python
"""Durable harness for the scorer's two pairing modes, run head-less.

score_minerals pairs each mineral's (up to 15) reference lines with the
observed peaks before scoring. Two modes:

  * greedy (the default and the original): from the largest d down, each line
    takes its NEAREST peak if no earlier line took it - so a line whose nearest
    peak is taken gives up, and an earlier line wins a peak a later line is
    closer to;
  * one-to-one: the pairing with the most matches, then the least total
    deviation, found as an assignment problem.

Pinned here: greedy is the default and is byte-for-byte the original loop (a
frozen copy of it lives below); one-to-one is a genuine one-to-one pairing,
inside the window, never fewer matches than greedy, independent of order, and
OPTIMAL - checked against brute force on random small cases; and the two known
greedy failures are fixed by it. Only the pairing differs between the modes.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_mineral_pairing.py

Exit codes: 0 = all pass, 1 = a regression.
"""

from __future__ import annotations

import glob
import itertools
import os
import random
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

import numpy as np  # noqa: E402

from mudlab.calculations import get_nm_from_2t, peak_detection as pd  # noqa: E402

results: list[tuple[str, bool]] = []
W = 0.01


def check(label, ok):
    results.append((label, bool(ok)))


_MINERALS = pd.load_mineral_references()


def _card(prefix):
    return next(m for m in _MINERALS if m[0].startswith(prefix))


def _frozen_greedy_score(peak_list, minerals):
    """The scorer exactly as it was before pairing modes existed (2026-08-15
    formula, greedy loop inline). Greedy mode must reproduce it bit for bit."""
    if not len(peak_list):
        return []
    need = max(1, min(2, len(peak_list)))
    scores = []
    for mineral, abbreviation, mpeaks in minerals:
        mpeaks = sorted(mpeaks, key=lambda peak: peak[0], reverse=True)[:15]
        p_matches, i_matches, already = [], [], []
        for mpos, mint in mpeaks:
            epos, eint = pd.find_closest(mpos, peak_list)
            if abs(epos - mpos) / mpos <= W and epos not in already:
                p_matches.append([mpos, epos])
                i_matches.append([mint, eint])
                already.append(epos)
        if len(p_matches) < need:
            continue
        p_matches = np.array(p_matches, dtype=float)
        i_matches = np.array(i_matches, dtype=float)
        n = p_matches.shape[0]
        pos_dev = np.mean(np.abs(p_matches[:, 1] - p_matches[:, 0]) / p_matches[:, 0])
        pos_factor = max(0.0, 1.0 - pos_dev / W)
        mint, eint = i_matches[:, 0], i_matches[:, 1]
        if n >= 2 and np.unique(mint).size >= 2 and np.unique(eint).size >= 2:
            corr = np.corrcoef(mint, eint)[0, 1]
            int_factor = max(0.0, corr) if np.isfinite(corr) else 0.5
        else:
            int_factor = 0.5
        score = n * pos_factor * int_factor
        if score > 0:
            scores.append((mineral, abbreviation, mpeaks, p_matches, score))
    scores.sort(key=lambda s: s[-1], reverse=True)
    return scores


def _same_result(a, b):
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x[0] != y[0] or x[1] != y[1] or x[2] != y[2] or x[4] != y[4]:
            return False
        if not np.array_equal(np.asarray(x[3]), np.asarray(y[3])):
            return False
    return True


def _peak_lists():
    """Synthetic lists (every 7th card's 8 strongest lines, scaled to counts)
    plus, when the sample projects are present, auto-detected real ones."""
    lists = [[(d, 40.0 * i) for d, i in sorted(p, key=lambda q: q[1], reverse=True)[:8]]
             for _n, _a, p in _MINERALS[::7]]
    for path in sorted(glob.glob(os.path.join(_REPO, "tools", "sample_projects", "*.mud"))):
        from mudlab.file_parsers.mud_project import load_mud
        for spec in load_mud(path).specimens:
            if spec is None or not spec.has_experimental_data:
                continue
            x, y = spec.experimental_pattern
            for prom in (0.02, 0.005):
                tab = pd.scipy_peakdetect(y, x, min_prominence=prom, min_distance_samples=5)
                lists.append([(get_nm_from_2t(px, spec.wavelength) * 10.0,
                               float(np.interp(px, x, y))) for px, _h in tab if px > 0])
            break
    return [pk for pk in lists if pk]


# ----------------------------------------------------------------------
def check_greedy_unchanged(lists):
    check("greedy is the default pairing",
          all(_same_result(pd.score_minerals(pk, _MINERALS),
                           pd.score_minerals(pk, _MINERALS, pairing=pd.PAIRING_GREEDY))
              for pk in lists[:12]))
    check("greedy == the original scorer, bit for bit (%d peak lists)" % len(lists),
          all(_same_result(pd.score_minerals(pk, _MINERALS),
                           _frozen_greedy_score(pk, _MINERALS)) for pk in lists))


def _pairs_ok(pairs, mpeaks, peak_list):
    refs = [p[0] for p in pairs]
    obs = [p[1] for p in pairs]
    one_to_one = len(set(map(float, refs))) == len(refs) and len(obs) == len(set(map(float, obs)))
    inside = all(abs(e - m) / m <= W for m, e in pairs)
    return one_to_one and inside


def check_one_to_one_properties(lists):
    proper = fewer = order_dep = 0
    total = 0
    rng = random.Random(7)
    for pk in lists:
        for _name, _abbr, lines in _MINERALS:
            mpeaks = sorted(lines, key=lambda q: q[0], reverse=True)[:15]
            gp, _gi = pd._pair_greedy(mpeaks, pk, W)
            op, _oi = pd._pair_one_to_one(mpeaks, pk, W)
            total += 1
            proper += _pairs_ok(op, mpeaks, pk)
            fewer += len(op) < len(gp)
            if op and rng.random() < 0.05:  # order independence, sampled
                shuffled = pk[:]
                rng.shuffle(shuffled)
                sp, _si = pd._pair_one_to_one(mpeaks, shuffled, W)
                order_dep += sorted(map(tuple, sp)) != sorted(map(tuple, op))
    check("one-to-one: every pairing is one-to-one and inside the 1%% window (%d)" % total,
          proper == total)
    check("one-to-one never matches fewer lines than greedy", fewer == 0)
    check("one-to-one does not depend on the order of the peaks", order_dep == 0)


def _brute_best(mpeaks, peak_list):
    """(most matches, least total deviation) over every one-to-one pairing."""
    best = (0, 0.0)
    m, n = len(mpeaks), len(peak_list)
    for k in range(min(m, n), 0, -1):
        found = None
        for rows in itertools.combinations(range(m), k):
            for cols in itertools.permutations(range(n), k):
                devs = [abs(peak_list[c][0] - mpeaks[r][0]) / mpeaks[r][0]
                        for r, c in zip(rows, cols)]
                if max(devs) <= W:
                    total = sum(devs)
                    if found is None or total < found:
                        found = total
        if found is not None:
            return (k, found)
    return best


def check_one_to_one_optimal():
    rng = random.Random(2026)
    ok = True
    bad = None
    for _trial in range(300):
        m, n = rng.randint(1, 5), rng.randint(1, 5)
        base = rng.uniform(2.0, 6.0)
        # crowd everything into ~3% so the window makes real conflicts
        mpeaks = sorted(((base * (1 + rng.uniform(-0.015, 0.015)), rng.uniform(1, 100))
                         for _ in range(m)), key=lambda q: q[0], reverse=True)
        peaks = [(base * (1 + rng.uniform(-0.015, 0.015)), rng.uniform(1, 100))
                 for _ in range(n)]
        op, _oi = pd._pair_one_to_one(mpeaks, peaks, W)
        got = (len(op), sum(abs(e - r) / r for r, e in op))
        want = _brute_best(mpeaks, peaks)
        if got[0] != want[0] or abs(got[1] - want[1]) > 1e-12:
            ok, bad = False, (mpeaks, peaks, got, want)
            break
    check("one-to-one is OPTIMAL: most matches, then least deviation "
          "(300 crowded random cases vs brute force)", ok)
    if bad:
        print("counter-example:", bad)


def check_known_cases():
    # Greedy gives up: line 3.38's nearest peak is taken by 3.40, though 3.36
    # is free and inside its window.
    card = [("Hand", "H", [(3.40, 100.0), (3.38, 50.0)])]
    obs = [(3.385, 900.0), (3.36, 400.0)]
    g = pd.score_minerals(obs, card)
    o = pd.score_minerals(obs, card, pairing=pd.PAIRING_ONE_TO_ONE)
    check("hand case: greedy gives up on a line whose nearest peak is taken", not g)
    check("hand case: one-to-one pairs both lines",
          len(o) == 1 and o[0][3].tolist() == [[3.40, 3.385], [3.38, 3.36]])

    # The known-answer greedy failure: Muscovite-2M1 on its own lines.
    mus = _card("Muscovite-2M1")
    own = sorted(mus[2], key=lambda q: q[1], reverse=True)[:8]
    rank = {mode: [r[0] for r in pd.score_minerals(own, _MINERALS, pairing=mode)]
            .index(mus[0]) + 1 for mode in pd.PAIRINGS}
    check("Muscovite-2M1 on its own lines: greedy ranks it below 1st (%d)"
          % rank[pd.PAIRING_GREEDY], rank[pd.PAIRING_GREEDY] > 1)
    check("Muscovite-2M1 on its own lines: one-to-one ranks it 1st",
          rank[pd.PAIRING_ONE_TO_ONE] == 1)

    # Only the pairing differs: same pairs -> same score in both modes.
    q = _card("Quartz")
    own_q = sorted(q[2], key=lambda p: p[1], reverse=True)[:8]
    gq = pd.score_minerals(own_q, [q])
    oq = pd.score_minerals(own_q, [q], pairing=pd.PAIRING_ONE_TO_ONE)
    check("same pairs give the same score in both modes (quartz on its own lines)",
          gq and oq and gq[0][4] == oq[0][4])

    check("an empty peak list scores nothing in either mode",
          all(pd.score_minerals([], _MINERALS, pairing=m) == [] for m in pd.PAIRINGS))
    try:
        pd.score_minerals(obs, card, pairing="best")
        raised = False
    except ValueError:
        raised = True
    check("an unknown pairing is refused", raised)


def main():
    lists = _peak_lists()
    check_greedy_unchanged(lists)
    check_one_to_one_properties(lists)
    check_one_to_one_optimal()
    check_known_cases()

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("\n--- Mineral pairing verification ---")
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
