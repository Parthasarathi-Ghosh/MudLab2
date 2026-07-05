@echo off
cd /d "%~dp0"
if not exist "python\Scripts\pyside6-designer.exe" (
    echo PySide6 Designer was not found in the bundled runtime.
    echo Run:
    echo   powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
    pause
    exit /b 1
)
start "" "python\Scripts\pyside6-designer.exe" %*
