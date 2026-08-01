#!/usr/bin/env python
"""Guard the release / frozen-build self-check (`MudLab --selftest`).

`__main__._selftest` runs the real data loaders (icons, scattering + composition
CSVs, the default catalog / .cmp components) and returns 0 iff they all resolve.
It is the gate used to confirm a PyInstaller build bundled its data correctly;
this keeps the function itself honest from a source run.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_selftest.py

Exit codes: 0 = pass, 1 = a regression.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication

QApplication.instance() or QApplication([])

from mudlab.__main__ import _selftest

rc = _selftest()
ok = rc == 0
print("\n--- selftest gate verification ---")
print("  [%s] _selftest() returns 0 (all bundled data resolves)" % ("PASS" if ok else "FAIL"))
print("1/1 checks passed" if ok else "0/1 checks passed")
sys.exit(0 if ok else 1)
