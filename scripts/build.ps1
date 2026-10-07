# build.ps1
# Professional Build Script for Result Analyzer

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "1. Cleaning previous build artifacts..."
Write-Host "=========================================="
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host ""
Write-Host "=========================================="
Write-Host "2. Building Application (Directory Mode)..."
Write-Host "=========================================="
.\venv\Scripts\python -m PyInstaller `
    --noconsole `
    --name ResultAnalyzer `
    --icon "assets/logo.ico" `
    --add-data "assets;assets" `
    --collect-all customtkinter `
    --collect-all tkinterdnd2 `
    --hidden-import matplotlib.backends.backend_tkagg `
    --hidden-import openpyxl `
    --distpath dist `
    --workpath build `
    src/main.py -y

# Ensure assets directory is also available directly in root of dist/ResultAnalyzer
Copy-Item -Path "assets" -Destination "dist/ResultAnalyzer/assets" -Recurse -Force

Write-Host ""
Write-Host "=========================================="
Write-Host "3. Building Standalone Setup Installer..."
Write-Host "=========================================="
.\venv\Scripts\python -m PyInstaller `
    --onefile `
    --noconsole `
    --name ResultAnalyzerSetup `
    --icon "assets/logo.ico" `
    --add-data "dist/ResultAnalyzer;ResultAnalyzer" `
    --add-data "assets;assets" `
    --distpath dist `
    --workpath build `
    scripts/installer.py -y

Write-Host ""
Write-Host "=========================================="
Write-Host "Build Complete!"
Write-Host "Installer Location:"
Write-Host "dist\ResultAnalyzerSetup.exe"
Write-Host "=========================================="
