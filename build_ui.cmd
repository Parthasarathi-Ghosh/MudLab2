@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
for %%F in ("%ROOT%src\mudlab\ui\*.ui") do (
    echo Compiling %%~nxF to ui_%%~nF.py
    "%ROOT%python\Scripts\pyside6-uic.exe" "%%F" -o "%ROOT%src\mudlab\ui\ui_%%~nF.py"
)
