@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
"%ROOT%python\python.exe" -X utf8 -m PyInstaller --noconfirm --clean --distpath "%ROOT%dist" --workpath "%ROOT%build" "%ROOT%MudLab.spec"
