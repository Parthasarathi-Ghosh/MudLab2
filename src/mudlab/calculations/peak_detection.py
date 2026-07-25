"""Peak detection and mineral scoring, ported as-is from the old
``mudlab/calculations/peak_detection.py`` plus the threshold/prominence
histogram helpers that lived on the old ``ExperimentalLine``
(``generic/models/lines/mudlab_line.py``).

The old helpers were methods on the line model and read ``self.data_x`` /
``self.data_y[:, 0]``.  Here they are free functions taking plain 1-D numpy
arrays, so the Detect Peaks / Match Minerals dialogs can call them straight on
a Specimen's ``(x, y)`` pattern with no model layer in between.  The numerics
are unchanged.
"""

from __future__ import annotations

import os

import numpy as np
from scipy import stats

from mudlab.calculations.math_tools import smooth

_MINERALS_CSV = os.path.join(
    os.path.dirname(__file__), os.pardir, "data", "mineral_references.csv"
)


# ----------------------------------------------------------------------
# Peak detection (billauer peakdet + scipy prominence)
# ----------------------------------------------------------------------
def find_closest(value, array, col=0):
    """Find the element of `array` whose `col`-th entry is closest to `value`."""
    nparray = np.array(list(zip(*array))[col])
    idx = (np.abs(nparray - value)).argmin()
    return array[idx]


def scipy_peakdetect(y_axis, x_axis, min_prominence=0.0, min_distance_samples=1):
    """Peak detection via ``scipy.signal.find_peaks`` with prominence filtering.

    ``y_axis`` is normalised internally so ``min_prominence`` is a fraction of
    the maximum intensity (same scale as the threshold algorithm).  Returns a
    list of ``(x_position, normalised_height)`` maxima - same shape as the
    ``maxtab`` returned by :func:`peakdetect`.
    """
    from scipy.signal import find_peaks as _sp_find_peaks
    y_axis = np.asarray(y_axis, dtype=float)
    y_norm = y_axis / np.max(y_axis) if y_axis.size and np.max(y_axis) > 0 else y_axis.copy()
    kw = dict(distance=max(1, int(min_distance_samples)))
    if min_prominence > 0:
        kw["prominence"] = min_prominence
    peaks, _ = _sp_find_peaks(y_norm, **kw)
    return [(x_axis[i], float(y_norm[i])) for i in peaks]


def peakdetect(y_axis, x_axis=None, lookahead=500, delta=0):
    """Single-delta run of :func:`multi_peakdetect`."""
    maxtabs, mintabs = multi_peakdetect(y_axis, x_axis, lookahead, [delta])
    return maxtabs[0], mintabs[0]


def multi_peakdetect(y_axis, x_axis=None, lookahead=500, deltas=[0]):
    """Detect local maxima/minima at several `deltas` in one pass.

    Converted from the MATLAB peakdet script (http://billauer.co.il/peakdet.html):
    a peak is a value surrounded by lower values, confirmed by looking
    `lookahead` points ahead.  `deltas` is the minimum rise/fall before a
    candidate counts, as a fraction of the (normalised) maximum.

    Returns ``(maxtab, mintab)``: two lists (one per delta) of ``(position,
    peak_value)`` tuples.
    """
    rlen = list(range(len(deltas)))
    maxtab = [[] for _ in rlen]
    mintab = [[] for _ in rlen]
    dump = [[] for _ in rlen]  # pops the always-false first hit

    length = len(y_axis)
    y_axis = y_axis / np.max(y_axis)
    if x_axis is None:
        x_axis = list(range(length))

    if length != len(x_axis):
        raise ValueError("Input vectors y_axis and x_axis must have same length")
    if lookahead < 1:
        raise ValueError("Lookahead must be above '1' in value")

    y_axis = np.asarray(y_axis)

    for j, delta in enumerate(deltas):
        mn, mx = np.inf, -np.inf
        mnpos, mxpos = np.nan, np.nan

        for index, (x, y) in enumerate(zip(x_axis[:-lookahead], y_axis[:-lookahead])):
            if y > mx:
                mx = y
                mxpos = x
            if y < mn:
                mn = y
                mnpos = x
            # look for max
            if y < mx - delta and mx != np.inf:
                if y_axis[index:index + lookahead].max() < mx:
                    maxtab[j].append((mxpos, mx))
                    dump[j].append(True)
                    mx = np.inf
                    mn = np.inf
            # look for min
            if y > mn + delta and mn != -np.inf:
                if y_axis[index:index + lookahead].min() > mn:
                    mintab[j].append((mnpos, mn))
                    dump[j].append(False)
                    mn = -np.inf
                    mx = -np.inf

    # Remove the false hit on the first value of the y_axis
    for j in rlen:
        try:
            if dump[j][0]:
                maxtab[j].pop(0)
            else:
                mintab[j].pop(0)
        except IndexError:
            pass  # no peaks found

    return maxtab, mintab


# ----------------------------------------------------------------------
# Threshold / prominence histograms (# of peaks vs cut-off)
# ----------------------------------------------------------------------
def calculate_npeaks_for(data_x, data_y, max_threshold, steps):
    """# of peaks for `steps` threshold values in ``[0, max_threshold]``.

    Returns ``(deltas, numpeaks)`` - the classic (billauer) histogram used by
    the Threshold algorithm.
    """
    data_x = np.asarray(data_x, dtype=float)
    data_y = np.asarray(data_y, dtype=float)

    steps = max(steps, 2) - 1
    factor = max_threshold / steps

    deltas = [i * factor for i in range(0, steps)]

    maxtabs, mintabs = multi_peakdetect(data_y, data_x, 5, deltas)
    numpeaks = [float(len(maxtab)) for maxtab, _ in zip(maxtabs, mintabs)]

    return deltas, numpeaks


def calculate_npeaks_for_scipy(data_x, data_y, max_prominence, steps, min_distance_deg=0.1):
    """# of scipy peaks for `steps` prominence values in ``[0, max_prominence]``.

    ``min_distance_deg`` - minimum peak separation in degrees 2theta, converted
    to samples with the data resolution.  Returns ``(prominences, numpeaks)`` -
    same shape as :func:`calculate_npeaks_for`.
    """
    from scipy.signal import find_peaks as _sp_find_peaks
    data_x = np.asarray(data_x, dtype=float)
    data_y = np.asarray(data_y, dtype=float)
    length = data_x.size
    if length < 2:
        return [], []
    y_max = np.max(data_y)
    y_norm = data_y / y_max if y_max > 0 else data_y.copy()
    resolution = (length - 1) / (data_x[-1] - data_x[0])
    min_dist_samples = max(1, int(min_distance_deg * resolution))
    steps = max(steps, 2) - 1
    proms = [i * max_prominence / steps for i in range(steps + 1)]
    numpeaks = []
    for p in proms:
        kw = dict(distance=min_dist_samples)
        if p > 0:
            kw["prominence"] = p
        peaks, _ = _sp_find_peaks(y_norm, **kw)
        numpeaks.append(float(len(peaks)))
    return proms, numpeaks


def get_best_threshold(data_x, data_y, max_threshold=None, steps=None, status_dict=None):
    """Estimate a good peak-detection threshold (classic algorithm).

    Assumes noise contributes a linear ramp to the # of peaks vs threshold
    curve; fits lines of growing length to the low-threshold part and stops
    where the fit stops being linear (``|R| < 0.98``), then refines the
    resolution and repeats until the answer settles.

    Returns ``((deltas, numpeaks), threshold, max_threshold)``.
    """
    data_x = np.asarray(data_x, dtype=float)
    data_y = np.asarray(data_y, dtype=float)
    length = data_x.size
    steps = 20 if steps is None else steps
    threshold = 0.1
    max_threshold = threshold * 3.2 if max_threshold is None else max_threshold

    def get_new_threshold(deltas, num_peaks, ln):
        x = deltas[:ln]
        y = num_peaks[:ln]
        slope, intercept, R, _, _ = stats.linregress(x, y)
        return R, -intercept / slope

    if length > 2:
        deltas, num_peaks = calculate_npeaks_for(data_x, data_y, max_threshold, steps)

        last_threshold = None
        solution = False
        max_iters = 10
        min_iters = 3
        itercount = 0
        if status_dict is not None:
            status_dict["progress"] = 0

        while not solution:
            ln = 4
            max_ln = len(deltas)
            stop = False
            while not stop:
                R, threshold = get_new_threshold(deltas, num_peaks, ln)
                max_threshold = threshold * 3.2
                if abs(R) < 0.98 or ln >= max_ln:
                    stop = True
                else:
                    ln += 1
            itercount += 1
            if last_threshold:
                solution = bool(
                    itercount > min_iters and not (
                        itercount <= max_iters and
                        last_threshold - threshold >= 0.001
                    )
                )
                if not solution:
                    deltas, num_peaks = calculate_npeaks_for(
                        data_x, data_y, max_threshold, steps)
            last_threshold = threshold
            if status_dict is not None:
                status_dict["progress"] = float(itercount / max_iters)

        return (deltas, num_peaks), threshold, max_threshold
    return ([], []), threshold, max_threshold


def get_best_prominence(data_x, data_y, max_prominence=None, steps=None,
                        min_distance_deg=0.1, status_dict=None):
    """Estimate a good minimum prominence for the scipy algorithm.

    Same iterative linear-regression elbow-finder as :func:`get_best_threshold`.
    Returns ``((prominences, numpeaks), prominence, max_prominence)``.
    """
    data_x = np.asarray(data_x, dtype=float)
    data_y = np.asarray(data_y, dtype=float)
    length = data_x.size
    steps = 20 if steps is None else steps
    prominence = 0.1
    max_prominence = prominence * 3.2 if max_prominence is None else max_prominence

    def get_new_prominence(prominence, proms, num_peaks, ln):
        x = proms[:ln]
        y = num_peaks[:ln]
        slope, intercept, R, _, _ = stats.linregress(x, y)
        if slope == 0:
            return R, prominence  # no gradient - keep current value
        return R, -intercept / slope

    if length > 2:
        proms, num_peaks = calculate_npeaks_for_scipy(
            data_x, data_y, max_prominence, steps, min_distance_deg)

        last_prominence = None
        solution = False
        max_iters = 10
        min_iters = 3
        itercount = 0
        if status_dict is not None:
            status_dict["progress"] = 0

        while not solution:
            ln = 4
            max_ln = len(proms)
            stop = False
            while not stop:
                R, prominence = get_new_prominence(prominence, proms, num_peaks, ln)
                max_prominence = prominence * 3.2
                if abs(R) < 0.98 or ln >= max_ln:
                    stop = True
                else:
                    ln += 1
            itercount += 1
            if last_prominence:
                solution = bool(
                    itercount > min_iters and not (
                        itercount <= max_iters and
                        last_prominence - prominence >= 0.001
                    )
                )
                if not solution:
                    proms, num_peaks = calculate_npeaks_for_scipy(
                        data_x, data_y, max_prominence, steps, min_distance_deg)
            last_prominence = prominence
            if status_dict is not None:
                status_dict["progress"] = float(itercount / max_iters)

        return (proms, num_peaks), prominence, max_prominence
    return ([], []), prominence, max_prominence


# ----------------------------------------------------------------------
# Mineral matching
# ----------------------------------------------------------------------
def score_minerals(peak_list, minerals):
    """Score reference minerals against an observed peak list.

    ``peak_list`` - ``(position_in_angstrom, absolute_intensity)`` observed peaks.
    ``minerals`` - ``(name, abbreviation, peaks)`` where ``peaks`` is a list of
    ``(d_angstrom, relative_intensity)``.

    For each mineral, its (up to 15) strongest reflections are matched to the
    nearest observed peak within 1% of position; a mineral with at least the
    required number of matches is scored on how well matched positions and
    intensities line up (via linear regression) and how many matched.  Returns
    ``(name, abbreviation, mpeaks, p_matches, score)`` tuples, best first.
    """
    max_pos_dev = 0.01  # fraction
    min_peaks_needed = max(1, min(2, len(peak_list)))
    scores = []
    for mineral, abbreviation, mpeaks in minerals:
        tot_score = 0
        p_matches = []
        i_matches = []
        already_matched = []
        mpeaks = sorted(mpeaks, key=lambda peak: peak[0], reverse=True)
        if len(mpeaks) > 15:
            mpeaks = mpeaks[:15]

        for i, (mpos, mint) in enumerate(mpeaks):
            epos, eint = find_closest(mpos, peak_list)
            if abs(epos - mpos) / mpos <= max_pos_dev and epos not in already_matched:
                p_matches.append([mpos, epos])
                i_matches.append([mint, eint])
                already_matched.append(epos)

        if len(p_matches) >= min_peaks_needed:
            p_matches = np.array(p_matches)
            i_matches = np.array(i_matches)

            i_matches[:, 1] = i_matches[:, 1] / np.max(i_matches[:, 1])

            if len(p_matches) >= 2:
                p_slope, p_intercept, p_r_value, p_value, p_std_err = stats.linregress(
                    p_matches[:, 0], p_matches[:, 1])
                p_factor = (p_r_value ** 2) * min(1.0 / (abs(1.0 - p_slope) + 1E-50), 1000.) / 1000.0
                if np.unique(i_matches[:, 0]).size >= 2:
                    i_slope, i_intercept, i_r_value, p_value, i_std_err = stats.linregress(
                        i_matches[:, 0], i_matches[:, 1])
                    i_factor = (1.0 - min(i_std_err / 0.25, 5.0) / 5.0) * min(
                        1.0 / (abs(1.0 - i_slope) + 1E-50), 1000.) / 1000.0
                else:
                    i_factor = 0.5  # all reference intensities identical, skip intensity regression
            else:
                # Single observed peak: score by positional accuracy alone
                p_dev = abs(p_matches[0, 1] - p_matches[0, 0]) / p_matches[0, 0]
                p_factor = 1.0 - p_dev / max_pos_dev
                i_factor = 0.5  # neutral weight for single-peak match
            tot_score = len(p_matches) * p_factor * i_factor

        if tot_score > 0:
            scores.append((mineral, abbreviation, mpeaks, p_matches, tot_score))

    scores = sorted(scores, key=lambda score: score[-1], reverse=True)
    return scores


def load_mineral_references(path=None):
    """Parse the bundled ``mineral_references.csv`` into the ``score_minerals``
    mineral list: ``[(name, abbreviation, [(d_angstrom, intensity), ...]), ...]``.

    Format (old app): a header line ``name[:24] ... card ... abbr[49:]`` is
    followed by alternating d-spacing (angstrom) / relative-intensity numeric
    lines, one per line, until the next header.  Sorted by name.
    """
    if path is None:
        path = _MINERALS_CSV
    minerals = []
    with open(path, encoding="utf-8") as f:
        mineral = ""
        abbreviation = ""
        position_flag = True
        position = 0.0
        peaks = []
        for line in f:
            line = line.rstrip("\r\n")  # keep leading columns intact
            try:
                number = float(line)
                if position_flag:
                    position = number
                else:
                    peaks.append((position, number))
                position_flag = not position_flag
            except ValueError:
                if mineral != "":
                    minerals.append((mineral, abbreviation, peaks))
                position_flag = True
                if len(line) > 25:
                    mineral = line[:24].strip()
                if len(line) > 49:
                    abbreviation = line[49:].strip()
                peaks = []
        # The old loader appended a mineral only when it hit the NEXT header, so
        # the final mineral (the file ends on numeric data) was silently
        # dropped. Flush it here so no reference is lost.
        if mineral != "":
            minerals.append((mineral, abbreviation, peaks))
    return sorted(minerals, key=lambda m: m[0])
