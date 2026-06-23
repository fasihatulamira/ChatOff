# ChatOff build script — PyInstaller exe + optional Inno Setup installer
# Run: .\build.ps1
# Requires: pip install pyinstaller
# Optional: Inno Setup 6 (iscc.exe in PATH) for ChatOff_Setup.exe

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

Write-Host "=== ChatOff Build v2.2 ===" -ForegroundColor Cyan

Write-Host "`n[1/4] Installing build dependencies..."
python -m pip install pyinstaller -q
python -m pip install -r requirements.txt -q

Write-Host "`n[2/4] Running release check..."
python release_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Release check failed. Fix issues before building." -ForegroundColor Red
    exit 1
}

Write-Host "`n[3/4] Building ChatOff.exe with PyInstaller..."
python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name app `
    --hidden-import=mysql.connector `
    --hidden-import=bcrypt `
    --hidden-import=PIL `
    --hidden-import=fitz `
    --collect-all customtkinter `
    --collect-all ollama `
    app.py

if (-not (Test-Path "dist\app.exe")) {
    Write-Host "PyInstaller failed — dist\app.exe not found." -ForegroundColor Red
    exit 1
}
Write-Host "Built: dist\app.exe" -ForegroundColor Green

Write-Host "`n[4/4] Building installer (optional)..."
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $iscc = @{ Source = $c }; break }
    }
}
if ($iscc) {
    if ($iscc.Source) { & $iscc.Source "ChatOff_Setup.iss" } else { & iscc "ChatOff_Setup.iss" }
    if (Test-Path "Installer\ChatOff_Setup.exe") {
        Write-Host "Built: Installer\ChatOff_Setup.exe" -ForegroundColor Green
    }
} else {
    Write-Host "Inno Setup (iscc) not in PATH — skipped installer." -ForegroundColor Yellow
    Write-Host "Install Inno Setup 6 and add iscc to PATH, then re-run." -ForegroundColor Yellow
}

Write-Host "`nDone. Test with: dist\app.exe" -ForegroundColor Cyan
