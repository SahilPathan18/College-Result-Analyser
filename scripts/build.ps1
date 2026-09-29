# build.ps1
# Professional Build Script for Result Analyzer

Write-Host "=========================================="
Write-Host "Building Result Analyzer App (Directory)"
Write-Host "=========================================="
.\venv\Scripts\pyinstaller --noconsole --name ResultAnalyzer src\main.py -y

Write-Host ""
Write-Host "=========================================="
Write-Host "Building Result Analyzer Setup (Installer)"
Write-Host "=========================================="
.\venv\Scripts\pyinstaller --onefile --noconsole --add-data "dist\ResultAnalyzer;ResultAnalyzer" --name ResultAnalyzerSetup scripts\installer.py -y

Write-Host ""
Write-Host "=========================================="
Write-Host "Build Complete!"
Write-Host "The fast installer can be found here:"
Write-Host "dist\ResultAnalyzerSetup.exe"
Write-Host "=========================================="
