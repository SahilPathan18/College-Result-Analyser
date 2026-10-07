# build.ps1
# Professional Build Script for Result Analyzer

$ErrorActionPreference = "Stop"

Write-Host "=========================================="
Write-Host "1. Stopping running processes & cleaning..."
Write-Host "=========================================="
Get-Process -Name "*ResultAnalyzer*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

if (Test-Path "build") { Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue }
if (Test-Path "dist\ResultAnalyzer") { Remove-Item -Recurse -Force "dist\ResultAnalyzer" -ErrorAction SilentlyContinue }
if (Test-Path "dist\ResultAnalyzer-Portable") { Remove-Item -Recurse -Force "dist\ResultAnalyzer-Portable" -ErrorAction SilentlyContinue }
if (Test-Path "dist\ResultAnalyzerSetup.exe") { Remove-Item -Force "dist\ResultAnalyzerSetup.exe" -ErrorAction SilentlyContinue }
if (Test-Path "dist\ResultAnalyzer-Portable.zip") { Remove-Item -Force "dist\ResultAnalyzer-Portable.zip" -ErrorAction SilentlyContinue }

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
Write-Host "4. Packaging Portable Edition..."
Write-Host "=========================================="
Copy-Item -Path "dist/ResultAnalyzer" -Destination "dist/ResultAnalyzer-Portable" -Recurse -Force
Copy-Item -Path "assets" -Destination "dist/ResultAnalyzer-Portable/assets" -Recurse -Force

# Create Portable Launchers
$runBat = @"
@echo off
start "" "%~dp0ResultAnalyzer.exe"
"@
Set-Content -Path "dist\ResultAnalyzer-Portable\Start Result Analyzer.bat" -Value $runBat

$shortcutBat = @"
@echo off
setlocal
echo Creating Desktop shortcut for Result Analyzer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "`$ws = New-Object -ComObject WScript.Shell; `$sc = `$ws.CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Result Analyzer.lnk')); `$sc.TargetPath = [IO.Path]::Combine('%~dp0', 'ResultAnalyzer.exe'); `$sc.WorkingDirectory = '%~dp0'; `$sc.IconLocation = [IO.Path]::Combine('%~dp0', 'assets\logo.ico,0'); `$sc.Save()"
echo Done! Shortcut created on your Desktop.
pause
"@
Set-Content -Path "dist\ResultAnalyzer-Portable\Create Desktop Shortcut.bat" -Value $shortcutBat

Compress-Archive -Path "dist/ResultAnalyzer-Portable/*" -DestinationPath "dist/ResultAnalyzer-Portable.zip" -Force

Write-Host ""
Write-Host "=========================================="
Write-Host "Build Complete!"
Write-Host "Installer: dist\ResultAnalyzerSetup.exe"
Write-Host "Portable Zip: dist\ResultAnalyzer-Portable.zip"
Write-Host "=========================================="
