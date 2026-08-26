@echo off
REM Build the portable Windows package:
REM   clean PyInstaller build -> frozen self-test -> bundle README -> zip.
REM Output: MudLab-<version>-win64-portable.zip (a no-install folder, zipped).
REM Run from the repo root:  package.cmd
setlocal enableextensions
cd /d "%~dp0"

set "PY=python\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo === [1/6] Clean PyInstaller build ===
"%PY%" -m PyInstaller --noconfirm --clean MudLab.spec
if errorlevel 1 goto :err

echo.
echo === [2/6] Frozen self-test (bundled data must resolve) ===
REM The app is windowed (no console); redirect so its output is captured.
dist\MudLab\MudLab.exe --selftest > "%TEMP%\mudlab_selftest.txt" 2>&1
set "ST=%ERRORLEVEL%"
type "%TEMP%\mudlab_selftest.txt"
if not "%ST%"=="0" goto :err
findstr /c:"SELFTEST PASS" "%TEMP%\mudlab_selftest.txt" >nul || goto :err

echo.
echo === [3/6] Bundle must be self-contained (no system runtime) ===
REM 1.0.0 started on every development machine and failed on a clean one: the
REM package leaned on a Microsoft runtime DLL that dev machines have in System32.
REM Running the app here cannot catch that, so the bundle's PE imports are
REM audited instead. This gate is the reason 1.0.1 exists.
"%PY%" tools\verify_bundle_dependencies.py
if errorlevel 1 goto :err

echo.
echo === [4/6] Bundle the README and the licence ===
REM The BSD-3 licence REQUIRES its notice to travel with a binary distribution,
REM so LICENSE is part of the package, not just the repo.
copy /Y "README-PORTABLE.md" "dist\MudLab\README.md" >nul || goto :err
copy /Y "LICENSE" "dist\MudLab\LICENSE" >nul || goto :err

echo.
echo === [5/6] Read version ===
REM Write the version to a temp file (no trailing newline) to dodge cmd's
REM nested-quote parsing inside for /f.
"%PY%" -c "import sys;sys.path.insert(0,'src');import mudlab;sys.stdout.write(mudlab.__version__)" > "%TEMP%\mudlab_ver.txt"
if errorlevel 1 goto :err
set "VER="
set /p VER=<"%TEMP%\mudlab_ver.txt"
if "%VER%"=="" goto :err
set "ZIP=MudLab-%VER%-win64-portable.zip"

echo.
echo === [6/6] Zip -^> %ZIP% ===
if exist "%ZIP%" del /f /q "%ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\MudLab' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 goto :err

echo.
echo === DONE ===
echo Portable package: %ZIP%
echo Users extract it and run  MudLab\MudLab.exe
exit /b 0

:err
echo.
echo *** PACKAGE FAILED ***
exit /b 1
