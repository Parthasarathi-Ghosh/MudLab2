#!/usr/bin/env python
"""Run every `tools/verify_*.py` and report the roll-up.

Exit codes mirror the harnesses themselves: 0 = everything that could run
passed, 1 = at least one regression. A harness that exits 2 has decided it has
nothing to test here (usually: no sample project) and is reported as SKIPPED,
not as a failure - that is the normal state in CI, where the `.mud` fixtures are
deliberately absent from the repository.

    ./python/python.exe tools/run_all.py            # everything
    ./python/python.exe tools/run_all.py peaks plot # only matching names
"""

from __future__ import annotations

import glob
import os
import subprocess
import sys
import time

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv):
    patterns = [a.lower() for a in argv[1:] if not a.startswith("-")]
    harnesses = sorted(glob.glob(os.path.join(_REPO, "tools", "verify_*.py")))
    if patterns:
        harnesses = [h for h in harnesses
                     if any(p in os.path.basename(h).lower() for p in patterns)]
    if not harnesses:
        print("No harnesses matched.")
        return 1

    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.join(_REPO, "src")
    # Head-less: these drive real dialogs and must never open a window.
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env["PYTHONIOENCODING"] = "utf-8"

    passed, skipped, failed = [], [], []
    started = time.time()
    for path in harnesses:
        name = os.path.basename(path)
        t0 = time.time()
        try:
            proc = subprocess.run(
                [sys.executable, path], cwd=_REPO, env=env, timeout=900,
                capture_output=True, text=True,
                encoding="utf-8", errors="replace")
            code, output = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
        except subprocess.TimeoutExpired:
            code, output = -9, "TIMED OUT after 900 s"
        label = {0: "OK", 2: "SKIP", -9: "TIMEOUT"}.get(code, "FAIL")
        print("%-8s %-46s %6.1fs" % (label, name, time.time() - t0), flush=True)
        if code == 0:
            passed.append(name)
        elif code == 2:
            skipped.append(name)
        else:
            failed.append((name, code, output))

    print()
    print("=" * 72)
    print("%d harnesses in %.0fs: %d passed, %d skipped, %d FAILED"
          % (len(harnesses), time.time() - started,
             len(passed), len(skipped), len(failed)))
    if skipped:
        print("skipped (nothing to test here): %s" % ", ".join(skipped))
    for name, code, output in failed:
        print()
        print("---- %s (exit %s) ----" % (name, code))
        lines = [ln for ln in output.splitlines()
                 if "FAIL" in ln or "Error" in ln or "Traceback" in ln
                 or "REGRESSION" in ln]
        print("\n".join(lines[-25:]) or output[-2000:])
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
