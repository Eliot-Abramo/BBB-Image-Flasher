Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
$VenvDir = Join-Path $RootDir ".bbb-image-forge\windows-venv"
$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Host "BBB Image Forge for Windows"
Write-Host "This launcher supports flashing on native Windows."
Write-Host "Use Ubuntu/Linux or WSL to build .img.xz artifacts." -ForegroundColor Yellow

if (-not (Test-IsAdministrator)) {
    Write-Host ""
    Write-Host "Warning: PowerShell is not elevated." -ForegroundColor Yellow
    Write-Host "Raw SD-card writes may fail until you restart PowerShell as Administrator." -ForegroundColor Yellow
}

if (-not (Test-Path $PythonExe)) {
    New-Item -ItemType Directory -Force -Path $VenvDir | Out-Null
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $VenvDir
    }
    elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv $VenvDir
    }
    else {
        throw "Python 3 was not found on PATH. Install Python for Windows, then re-run this script."
    }
}

& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install -e $RootDir

Write-Host ""
Write-Host "Starting BBB Image Forge on http://127.0.0.1:8000" -ForegroundColor Green
Write-Host "Build actions are disabled on native Windows. Use WSL/Linux for builds, then flash here." -ForegroundColor Cyan

& $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
