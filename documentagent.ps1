# documentagent.ps1 - run the coopagent CLI via .venv
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "Virtual environment not found. Run .\setup.ps1 first." -ForegroundColor Red
    exit 1
}

$env:PYTHONPATH = Join-Path $Root "src"
& $Python -m documentation_agent.cli @args
