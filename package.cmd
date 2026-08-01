@echo off
REM Build the portable Windows package for testers:
REM   clean PyInstaller build -> frozen self-test -> bundle README -> zip.
REM Output: MudLab-<version>-win64-portable.zip (a no-install folder, zipped).
REM Run from the repo root:  package.cmd
setlocal enableextensions
cd /d "%~dp0"

set "PY=python\python.exe"
if not exist "%PY%" set "PY=python"

echo.
echo === [1/5] Clean PyInstaller build ===
"%PY%" -m PyInstaller --noconfirm --clean MudLab.spec
if errorlevel 1 goto :err

echo.
echo === [2/5] Frozen self-test (bundled data must resolve) ===
REM The app is windowed (no console); redirect so its output is captured.
dist\MudLab\MudLab.exe --selftest > "%TEMP%\mudlab_selftest.txt" 2>&1
set "ST=%ERRORLEVEL%"
type "%TEMP%\mudlab_selftest.txt"
if not "%ST%"=="0" goto :err
findstr /c:"SELFTEST PASS" "%TEMP%\mudlab_selftest.txt" >nul || goto :err

echo.
echo === [3/5] Bundle the tester README ===
copy /Y "README-TESTERS.md" "dist\MudLab\README-TESTERS.md" >nul || goto :err

echo.
echo === [4/5] Read version ===
REM Write the version to a temp file (no trailing newline) to dodge cmd's
REM nested-quote parsing inside for /f.
"%PY%" -c "import sys;sys.path.insert(0,'src');import mudlab;sys.stdout.write(mudlab.__version__)" > "%TEMP%\mudlab_ver.txt"
if errorlevel 1 goto :err
set "VER="
set /p VER=<"%TEMP%\mudlab_ver.txt"
if "%VER%"=="" goto :err
set "ZIP=MudLab-%VER%-win64-portable.zip"

echo.
echo === [5/5] Zip -^> %ZIP% ===
if exist "%ZIP%" del /f /q "%ZIP%"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\MudLab' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 goto :err

echo.
echo === DONE ===
echo Portable package: %ZIP%
echo Testers extract it and run  MudLab\MudLab.exe
exit /b 0

:err
echo.
echo *** PACKAGE FAILED ***
exit /b 1
