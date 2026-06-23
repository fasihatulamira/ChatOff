# ChatOff one-time setup script (Windows PowerShell)
# Run: .\setup.ps1

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

Write-Host "=== ChatOff Setup ===" -ForegroundColor Cyan

Write-Host "`n[1/5] Installing Python packages..."
python -m pip install -r requirements.txt

Write-Host "`n[2/5] Checking .env..."
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env"; Write-Host "Created .env" } else { Write-Host ".env exists" }

Write-Host "`n[3/5] MySQL setup (enter root password when prompted)..."
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS chatdb;"
Get-Content schema.sql -Raw | mysql -u root -p chatdb

Write-Host "`n[4/5] Ollama models..."
if (Get-Command ollama -ErrorAction SilentlyContinue) { ollama pull llama3.2:3b; ollama pull nomic-embed-text }

Write-Host "`n[5/5] Smoke test..."
python test.py
Write-Host "`nDone. Run: python app.py"
