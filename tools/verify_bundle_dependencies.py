#!/usr/bin/env python
"""Every DLL a bundled binary needs must be resolvable INSIDE the package.

WHY THIS EXISTS. MudLab 1.0.0 shipped a "portable" build that started on every
development machine and failed on a user's with

    ImportError: cannot import name 'ft2font' from partially initialized
    module 'matplotlib' (most likely due to a circular import)

which is what PyInstaller's importer reports when a compiled extension cannot be
LOADED. The package was complete; what was missing was a Microsoft runtime DLL
that development machines happen to have in System32 and clean machines do not.
PyInstaller treats the Visual C++ runtime as a system library, so `MSVCP140.dll`
only arrived incidentally inside PySide6's own folder - leaving the eight Qt
plugin DLLs that need it, `platforms/qwindows.dll` among them, resolving it from
the system or not at all.

A build that calls itself portable cannot be checked by running it on the
machine that built it. This walks the PE import table of every binary in the
bundle and asks a question the build machine cannot answer by accident: could
this dependency be found with nothing but the package itself?

Resolution follows the Windows loader: a DLL's own directory, plus the bundle
root (PyInstaller puts `_internal` on the DLL search path). Windows' own
libraries are excluded - the OS provides those - but the MSVC runtime is
deliberately NOT treated as an OS library, because it is exactly the thing a
user may not have.

Run head-less with the bundled interpreter from the repo root:

    ./python/python.exe tools/verify_bundle_dependencies.py [path-to-bundle]

Default bundle: dist/MudLab. Exit codes: 0 = all pass, 1 = a regression,
2 = no build present to check.
"""

from __future__ import annotations

import os
import struct
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Windows' own libraries. Anything here is provided by the OS, so it does not
#: have to be in the package. `api-ms-win-*` / `ext-ms-*` are API sets, resolved
#: by the loader through the API-set schema rather than as files on disk.
_OS_DLLS = {
    "kernel32.dll", "kernelbase.dll", "ntdll.dll", "user32.dll", "gdi32.dll",
    "advapi32.dll", "ole32.dll", "oleaut32.dll", "shell32.dll", "shlwapi.dll",
    "ws2_32.dll", "crypt32.dll", "comdlg32.dll", "comctl32.dll", "winmm.dll",
    "version.dll", "userenv.dll", "netapi32.dll", "bcrypt.dll", "ncrypt.dll",
    "secur32.dll", "iphlpapi.dll", "wintrust.dll", "imm32.dll", "dwmapi.dll",
    "uxtheme.dll", "msimg32.dll", "mpr.dll", "rpcrt4.dll", "setupapi.dll",
    "powrprof.dll", "propsys.dll", "dnsapi.dll", "avrt.dll", "psapi.dll",
    "d3d9.dll", "d3d11.dll", "d3d12.dll", "dxgi.dll", "d2d1.dll",
    "dwrite.dll", "windowscodecs.dll", "opengl32.dll", "glu32.dll",
    "gdiplus.dll", "winspool.drv", "wtsapi32.dll", "cfgmgr32.dll",
    "authz.dll", "msvcrt.dll", "ucrtbase.dll", "normaliz.dll",
    "mfplat.dll", "mf.dll", "mfreadwrite.dll", "mfcore.dll", "evr.dll",
    "winhttp.dll", "urlmon.dll", "wininet.dll", "oleacc.dll", "usp10.dll",
    "sechost.dll", "combase.dll", "bcryptprimitives.dll",
    "uiautomationcore.dll", "dcomp.dll", "d3dcompiler_47.dll",
    "winmmbase.dll", "textshaping.dll", "textinputframework.dll",
    # Windows has shipped ICU since Win10 1703, and imagehlp is core;
    # both verified present in System32. Our stated floor is Win10+.
    "icuuc.dll", "icuin.dll", "imagehlp.dll",
}

#: The MSVC runtime. Deliberately NOT in `_OS_DLLS`: it is not part of Windows,
#: it ships with the Visual C++ Redistributable, and a portable build must
#: carry its own. This set exists so the message can say so.
_MSVC_RUNTIME = {
    "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "concrt140.dll",
    "vcruntime140.dll", "vcruntime140_1.dll", "vccorlib140.dll",
}

results: list[tuple[str, bool]] = []


def check(label, ok):
    results.append((label, bool(ok)))


# ---------------------------------------------------------------------------
# A minimal PE import-table reader. No third-party dependency: the point of
# this check is that it runs in the same environment that builds the package.
# ---------------------------------------------------------------------------
def _rva_to_offset(sections, rva):
    for va, vsize, raw, rsize in sections:
        if va <= rva < va + max(vsize, rsize):
            return raw + (rva - va)
    return None


def pe_imports(path):
    """The DLL names a PE file imports, as the loader sees them."""
    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return []
    if data[:2] != b"MZ":
        return []
    try:
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0":
            return []
        coff = pe + 4
        n_sections = struct.unpack_from("<H", data, coff + 2)[0]
        opt_size = struct.unpack_from("<H", data, coff + 16)[0]
        opt = coff + 20
        magic = struct.unpack_from("<H", data, opt)[0]
        directories = opt + (112 if magic == 0x20B else 96)
        import_rva = struct.unpack_from("<I", data, directories + 8)[0]
        if not import_rva:
            return []
        section_table = opt + opt_size
        sections = []
        for i in range(n_sections):
            off = section_table + i * 40
            vsize, va, rsize, raw = struct.unpack_from("<IIII", data, off + 8)
            sections.append((va, vsize, raw, rsize))
        base = _rva_to_offset(sections, import_rva)
        if base is None:
            return []
        names, i = [], 0
        while True:
            fields = struct.unpack_from("<IIIII", data, base + i * 20)
            if not any(fields):
                break
            name_off = _rva_to_offset(sections, fields[3])
            if name_off is None:
                break
            end = data.index(b"\0", name_off)
            names.append(data[name_off:end].decode("ascii", "replace"))
            i += 1
        return names
    except (struct.error, ValueError, IndexError):
        return []


def _is_os_provided(name):
    return (name in _OS_DLLS
            or name.startswith("api-ms-win-")
            or name.startswith("ext-ms-"))


def audit(bundle):
    """(unresolvable, scanned) for a PyInstaller onedir bundle."""
    internal = os.path.join(bundle, "_internal")
    search_root = internal if os.path.isdir(internal) else bundle

    # Where every DLL in the package lives, by lowercase name.
    present = {}
    for base, _dirs, files in os.walk(bundle):
        for name in files:
            if name.lower().endswith(".dll"):
                rel = os.path.relpath(base, search_root).replace("\\", "/")
                present.setdefault(name.lower(), set()).add(rel)

    # PRESENT ANYWHERE is the right test for most dependencies. A Qt plugin in
    # PySide6/plugins/platforms/ imports Qt6Core.dll, which lives one level up
    # in PySide6/ - and resolves because Qt6Core is already loaded into the
    # process by the time any plugin is asked for. numpy's private
    # numpy.libs/msvcp140-<hash>.dll is the same story. Demanding that every
    # dependency sit in the importer's own directory or the bundle root reports
    # a dozen of those as failures, and a check that cries wolf is one people
    # learn to ignore - which is how 1.0.0 shipped.
    #
    # The MSVC runtime is checked STRICTLY and separately below, because that
    # is the dependency that actually escaped: nothing in the package loads it
    # early, so it has to be at the root where the loader will find it.
    unresolvable, scanned = {}, 0
    for base, _dirs, files in os.walk(bundle):
        for name in files:
            if not name.lower().endswith((".dll", ".pyd", ".exe")):
                continue
            scanned += 1
            path = os.path.join(base, name)
            for dep in pe_imports(path):
                dep = dep.lower()
                if _is_os_provided(dep) or dep in present:
                    continue
                unresolvable.setdefault(dep, []).append(
                    os.path.relpath(path, bundle).replace("\\", "/"))
    return unresolvable, scanned


def main(argv):
    bundle = argv[1] if len(argv) > 1 else os.path.join(_REPO, "dist", "MudLab")
    if not os.path.isdir(bundle):
        print("No bundle at %s; skipping (exit 2)." % bundle)
        return 2

    unresolvable, scanned = audit(bundle)
    check("scanned %d binaries in %s" % (scanned, os.path.basename(bundle)),
          scanned > 0)

    msvc = {d: f for d, f in unresolvable.items() if d in _MSVC_RUNTIME}
    other = {d: f for d, f in unresolvable.items() if d not in _MSVC_RUNTIME}

    check("the MSVC runtime is carried by the package, not the user's system",
          not msvc)
    for dep, users in sorted(msvc.items()):
        print("      %s is needed by %d bundled binaries but is not in the "
              "package root:" % (dep, len(users)))
        for u in users[:6]:
            print("        %s" % u)

    check("no other bundled binary depends on a DLL outside the package",
          not other)
    for dep, users in sorted(other.items()):
        print("      %s missing, needed by: %s" % (dep, ", ".join(users[:4])))

    # The runtime really is at the root, not merely somewhere.
    root = os.path.join(bundle, "_internal")
    if os.path.isdir(root):
        for name in ("MSVCP140.dll", "VCRUNTIME140.dll", "VCRUNTIME140_1.dll"):
            check("%s sits at the bundle root" % name,
                  os.path.isfile(os.path.join(root, name)))

    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print("=" * 72)
    print("Bundle dependencies: %s" % bundle)
    print("=" * 72)
    for label, ok in results:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    print("%d/%d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
