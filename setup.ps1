# setup.ps1 - one-click setup for coopagent
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "== coopagent setup ==" -ForegroundColor Cyan

# 1) virtual environment
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
}
$venvPython = Join-Path $Root ".venv\Scripts\python.exe"

# 2) dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r requirements.txt -r requirements-dev.txt --quiet

# 3) .env / OPENAI_API_KEY check
if (-not (Test-Path ".env")) {
    Write-Host "WARN: .env not found. Create it with: OPENAI_API_KEY=sk-..." -ForegroundColor Yellow
} elseif (-not (Select-String -Path ".env" -Pattern "^OPENAI_API_KEY=" -Quiet)) {
    Write-Host "WARN: .env is missing the line 'OPENAI_API_KEY=...'" -ForegroundColor Yellow
} else {
    Write-Host ".env OK" -ForegroundColor Green
}

Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Usage: .\documentagent.ps1 `"your task`"" -ForegroundColor Cyan
