# Recreates the bundled Python runtime in ..\python from scratch.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$pythonVersion = "3.14.6"
$root = Split-Path -Parent $PSScriptRoot
$pythonDir = Join-Path $root "python"

if (Test-Path $pythonDir) {
    throw "$pythonDir already exists. Delete it first to rebuild the runtime."
}

$env:PYTHONUTF8 = "1"

$temp = Join-Path $env:TEMP ("mudlab-setup-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null

try {
    # Official portable CPython build for Windows (full distribution,
    # no installer, no registry entries) published on nuget.org.
    $url = "https://api.nuget.org/v3-flatcontainer/python/$pythonVersion/python.$pythonVersion.nupkg"
    $zip = Join-Path $temp "python.zip"
    Write-Host "Downloading Python $pythonVersion ..."
    Invoke-WebRequest -Uri $url -OutFile $zip

    Write-Host "Extracting ..."
    Expand-Archive -Path $zip -DestinationPath (Join-Path $temp "extracted")
    Move-Item (Join-Path $temp "extracted\tools") $pythonDir

    $python = Join-Path $pythonDir "python.exe"
    & $python -m ensurepip --upgrade
    & $python -m pip install --upgrade pip --no-warn-script-location
    & $python -m pip install --no-warn-script-location -r (Join-Path $root "requirements.txt")

    Write-Host "Done. Runtime ready at $pythonDir"
}
finally {
    Remove-Item -Recurse -Force $temp -ErrorAction SilentlyContinue
}
