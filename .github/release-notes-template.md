**MudLab {{VERSION}}** — X-ray diffraction analysis of disordered layered minerals.

## Download

**[MudLab-{{VERSION}}-win64-portable.zip](../../releases/download/v{{VERSION}}/MudLab-{{VERSION}}-win64-portable.zip)** — 64-bit Windows 10 or later.

Portable, not an installer: nothing is installed, nothing is written to the
registry, no administrator rights needed.

1. **Unzip** the folder anywhere — Desktop, Documents, a USB stick.
2. Open the extracted **`MudLab`** folder and double-click **`MudLab.exe`**.

> **Keep the folder together.** `MudLab.exe` needs the `_internal` folder beside
> it. Move or copy the whole `MudLab` folder, never just the `.exe`.

{{HIGHLIGHTS}}

## The manual

Press **F1** in MudLab, or **Help → Manual**. It ships inside the folder and
works offline: a short walkthrough from importing a scan to saving a result,
with the full reference a click away.

## If MudLab does not start

**Your antivirus has probably removed one of its files.** This has genuinely
happened: Quick Heal flagged `ft2font…pyd` — part of the graphing library — as
`Trojan.Agent` and quarantined it. It is a **false positive**. MudLab is not
code-signed, and packaged Python applications are periodically flagged by
mistake.

To fix it:

1. Open your antivirus and find its **quarantine** (Quick Heal:
   *More → Settings → View Quarantine Files*).
2. Select the MudLab file it took and choose **Restore**.
3. Add the whole `MudLab` folder to the antivirus **exclusions**, so it is not
   removed again.
4. Start MudLab again.

While you are there, **Submit for analysis** helps: it tells the vendor the
detection was wrong, so the next update stops flagging it for everyone.

**Windows SmartScreen** may also say *"unknown publisher"*. This build is not
code-signed — choose **More info → Run anyway**.

## Requirements

64-bit Windows 10 or later. Nothing else — Python, Qt, NumPy, SciPy and
Matplotlib are all inside the folder.

BSD 3-Clause. MudLab descends from PyXRD / MudLab by Mathijs Dumon; that
copyright notice travels with this release, as the licence requires.
