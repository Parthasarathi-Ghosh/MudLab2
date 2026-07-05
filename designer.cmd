@echo off
setlocal
set "ROOT=%~dp0"
set "PYTHONUTF8=1"
start "Qt Designer" "%ROOT%python\Scripts\pyside6-designer.exe" %*
