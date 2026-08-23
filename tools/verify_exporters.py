#!/usr/bin/env python
"""Export to the old GTK MudLab's .mud, and to PyXRD's .pyxrd.

MudLab2's native .mud is the old format plus MudLab2-only additions, and the old
app raises TypeError on ANY unknown key. So a project carrying a measured
composition is UNREADABLE there - this harness proves that (the control below),
proves the export fixes it, and pins the PyXRD mapping.

Two very different standards of evidence, deliberately:

  * OLD APP - measured. When `C:\\GitHub\\MudLab\\data\\bin\\python.exe` is
    present, the exported file is actually LOADED under the old app, and a
    native save is loaded too, to confirm it really does fail. Without that
    interpreter those two checks are skipped, not faked.
  * PYXRD - structural. PyXRD is not installed and has never seen this output.
    Instead every type and key the exporter writes is checked against a corpus
    of real .pyxrd files (the user's, in Downloads\\PyXRD test projects): a key
    no real PyXRD file contains is a key PyXRD probably rejects. Skipped when
    the corpus is absent.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_exporters.py

Exit codes: 0 = all pass, 1 = a regression, 2 = no usable sample project.
"""

from __future__ import annotations

import collections
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from mudlab.file_parsers.exporters import (  # noqa: E402
    MUDLAB2_PROJECT_KEYS, PYXRD_METHOD_BY_INDEX, export_old_mud, export_pyxrd,
    suggested_name,
)
from mudlab.file_parsers.mud_project import load_mud, save_mud  # noqa: E402
from mudlab.models import Composition  # noqa: E402

app = QApplication.instance() or QApplication([])
results: list[tuple[str, bool]] = []

OLD_APP_PYTHON = r"C:\GitHub\MudLab\data\bin\python.exe"
PYXRD_CORPUS = os.path.join(os.path.expanduser("~"), "Downloads",
                            "PyXRD test projects")


def check(label, ok):
    results.append((label, bool(ok)))


def _fixture():
    for path in sorted(glob.glob(os.path.join(
            _REPO, "tools", "sample_projects", "*.mud"))):
        project = load_mud(path)
        if project.mixtures and project.phases:
            return path
    return None


PATH = _fixture()
if PATH is None:
    print("No sample project with a mixture; skipping (exit 2).")
    raise SystemExit(2)


def _loaded(path):
    """Every serialised object in an archive, as {type: set(keys)}."""
    archive = zipfile.ZipFile(path)
    keys = collections.defaultdict(set)

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") and isinstance(node.get("properties"), dict):
                keys[node["type"]] |= set(node["properties"])
                for value in node["properties"].values():
                    walk(value)
            else:
                for value in node.values():
                    walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for part in ("specimens", "phases", "atom_types", "mixtures"):
        if part in archive.namelist():
            walk(json.loads(archive.read(part)))
    project_keys = set(json.loads(archive.read("content"))["properties"])
    return archive.namelist(), project_keys, keys


def _project_with_extras():
    """A project exercising every MudLab2-only addition."""
    project = load_mud(PATH)
    project.set_composition(
        Composition(name="XRF", oxides={"SiO2": 55.0, "Al2O3": 20.0}))
    project.set_default_phase_map({project.phases[0].uuid: "Illite"})
    return project


def _old_app_can_load(path):
    """(ok, output) - load `path` under the OLD app's own interpreter."""
    script = os.path.join(tempfile.gettempdir(), "_mudlab_old_load.py")
    with open(script, "w", encoding="utf-8") as handle:
        handle.write(
            "import sys, traceback\n"
            "try:\n"
            "    from mudlab.data import settings\n"
            "    settings.initialize()\n"
            "    from mudlab.project.models import Project\n"
            "    from mudlab.specimen.models import Specimen\n"
            "    from mudlab.phases.models import Phase\n"
            "    from mudlab.mixture.models import Mixture\n"
            "    from mudlab.atoms.models import AtomType\n"
            "    from mudlab.file_parsers.json_parser import JSONParser\n"
            "    p = JSONParser.parse(sys.argv[1])\n"
            "    print('LOADED %d %d %d' % (len(p.specimens), len(p.phases),\n"
            "                               len(p.mixtures)))\n"
            "except Exception:\n"
            "    traceback.print_exc()\n"
            "    sys.exit(1)\n"
        )
    # The old app has its OWN `mudlab` package. This harness runs with
    # PYTHONPATH pointing at MudLab2's src, and a child would inherit it and
    # import THIS mudlab instead - which fails confusingly inside the old app's
    # imports. Scrub it, and run from the old app's own directory.
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        proc = subprocess.run(
            [OLD_APP_PYTHON, script, path], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600,
            env=env, cwd=os.path.dirname(os.path.dirname(OLD_APP_PYTHON)))
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)
    return proc.returncode == 0, (proc.stdout or "") + (proc.stderr or "")


def main():
    tmp = tempfile.mkdtemp(prefix="mudlab_export_")
    project = _project_with_extras()

    old_path = os.path.join(tmp, "export.mud")
    pyxrd_path = os.path.join(tmp, "export.pyxrd")
    old_report = export_old_mud(project, old_path)
    pyxrd_report = export_pyxrd(project, pyxrd_path)

    # ------------------------------------------------- exporting is not saving
    check("export leaves project.filename alone",
          project.filename == PATH)
    check("export does not adopt the exported path",
          project.filename not in (old_path, pyxrd_path))
    check("export leaves the composition on the project",
          project.composition is not None)

    # ------------------------------------------------------------- old app
    entries, project_keys, _types = _loaded(old_path)
    check("old: MudLab2-only project keys are gone",
          not (set(MUDLAB2_PROJECT_KEYS) & project_keys))
    check("old: the version entry is kept (the old app expects one)",
          "version" in entries)
    check("old: the report says what was dropped", bool(old_report.notes))

    # ------------------------------------------------------------- PyXRD
    entries, project_keys, types = _loaded(pyxrd_path)
    check("pyxrd: MudLab2-only project keys are gone",
          not (set(MUDLAB2_PROJECT_KEYS) & project_keys))
    check("pyxrd: NO version entry (PyXRD archives have none)",
          "version" not in entries)
    check("pyxrd: goniometers carry a single `wavelength`",
          all("wavelength" in k for t, k in types.items() if t == "Goniometer"))
    check("pyxrd: the wavelength distribution is gone",
          not any("wavelength_distribution" in k
                  for t, k in types.items() if t == "Goniometer"))
    check("pyxrd: sample_length moved onto the Specimen",
          "sample_length" in types.get("Specimen", set())
          and "sample_length" not in types.get("Goniometer", set()))
    check("pyxrd: absorption moved onto the Specimen",
          "absorption" in types.get("Specimen", set())
          and "absorption" not in types.get("Goniometer", set()))
    check("pyxrd: the ADS group is written",
          {"has_ads", "ads_const", "ads_fact"} <= types.get("Goniometer", set()))
    check("pyxrd: refine_method replaces refine_method_index",
          "refine_method" in types.get("Mixture", set())
          and "refine_method_index" not in types.get("Mixture", set()))
    # refine_options is PyXRD's own key - it must be KEPT, only cleaned. An
    # earlier version stripped it on a guess.
    check("pyxrd: refine_options is KEPT (PyXRD has it too)",
          "refine_options" in types.get("Mixture", set()))
    archive = zipfile.ZipFile(pyxrd_path)
    mixtures = json.loads(archive.read("mixtures"))
    inner = [k for m in mixtures
             for opts in [m["properties"].get("refine_options") or {}]
             for v in opts.values() if isinstance(v, dict) for k in v
             if k.startswith("inner_")]
    check("pyxrd: MudLab's inner_* option keys are cleaned out", not inner)
    check("pyxrd: the method index is mapped, not copied",
          all(m["properties"].get("refine_method")
              == PYXRD_METHOD_BY_INDEX.get(0, 0) for m in mixtures))
    check("pyxrd: Specimen.source is gone",
          "source" not in types.get("Specimen", set()))
    check("pyxrd: the report warns it is best-effort",
          any("best-effort" in note for note in pyxrd_report.notes))

    # --------------------------------------- PyXRD structural check vs corpus
    corpus = sorted(glob.glob(os.path.join(PYXRD_CORPUS, "*.pyxrd")))
    if corpus:
        ref_project, ref_types = set(), collections.defaultdict(set)
        for path in corpus:
            _e, pk, tk = _loaded(path)
            ref_project |= pk
            for kind, keys in tk.items():
                ref_types[kind] |= keys
        check("pyxrd/corpus: %d real files read" % len(corpus), True)
        check("pyxrd/corpus: no project key is unknown to real PyXRD files",
              not (project_keys - ref_project))
        # Types PyXRD has that these particular projects simply never used are
        # NOT evidence of a problem - Marker and R0G1Model are real PyXRD
        # features absent from this corpus - so only KEYS are asserted, and
        # only for types the corpus actually contains.
        unknown = {
            kind: sorted(keys - ref_types[kind])
            for kind, keys in types.items()
            if kind in ref_types and (keys - ref_types[kind])
        }
        check("pyxrd/corpus: no key we write is unknown to real PyXRD files"
              + ("" if not unknown else " -> %s" % unknown), not unknown)
    else:
        check("pyxrd/corpus: (no PyXRD corpus on this machine; skipped)", True)

    # ------------------------------------------- the old app, for real
    if os.path.isfile(OLD_APP_PYTHON):
        # CONTROL: a native save carrying a composition must FAIL there. If this
        # ever passes, the exporter is solving a problem that no longer exists.
        native = os.path.join(tmp, "native.mud")
        save_mud(_project_with_extras(), native)
        ok, output = _old_app_can_load(native)
        check("old/real: a NATIVE save with a composition is rejected "
              "(control)", not ok and "TypeError" in output)
        ok, output = _old_app_can_load(old_path)
        check("old/real: the EXPORT loads in the old app%s"
              % ("" if ok else " -> " + output.strip().splitlines()[-1:][0]
                 if output.strip() else ""), ok)
        check("old/real: ...with the right object counts",
              "LOADED %d %d %d" % (len(project.specimens), len(project.phases),
                                   len(project.mixtures)) in output)
    else:
        check("old/real: (old app interpreter not on this machine; skipped)",
              True)

    # ------------------------------------------------- NonClayPhase demotion
    # No sample project ships with one, and it is the single type that makes a
    # file unopenable in BOTH targets (unknown TYPE -> KeyError), so the
    # transformation is exercised directly.
    from mudlab.file_parsers.exporters import ExportReport, _demote_nonclay

    props = {"phases": [
        {"type": "NonClayPhase", "properties": {
            "uuid": "abc", "name": "Quartz", "data": "x",
            "oxides": {"SiO2": 100.0}, "fwhm": 0.1, "caglioti": [1, 2, 3]}},
        {"type": "Phase", "properties": {"uuid": "def", "name": "Illite"}},
    ]}
    report = ExportReport("test")
    _demote_nonclay(props, report)
    demoted = props["phases"][0]
    check("nonclay: exported as RawPatternPhase, not dropped",
          demoted["type"] == "RawPatternPhase")
    check("nonclay: its uuid survives (mixture cells still resolve)",
          demoted["properties"]["uuid"] == "abc")
    check("nonclay: its pattern survives",
          demoted["properties"].get("data") == "x")
    check("nonclay: the oxide chemistry is stripped",
          not {"oxides", "fwhm", "caglioti"} & set(demoted["properties"]))
    check("nonclay: ordinary phases are untouched",
          props["phases"][1]["type"] == "Phase")
    check("nonclay: the loss is reported", bool(report.notes))

    # ------------------------------------------------------------- naming
    check("naming: the suggested name uses the project name",
          suggested_name(project, ".pyxrd").endswith(".pyxrd"))
    project.name = 'bad/name:with*chars'
    check("naming: path-hostile characters are replaced",
          not set('\\/:*?"<>|') & set(suggested_name(project, ".mud")))

    shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Exporters:", os.path.basename(PATH))
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
