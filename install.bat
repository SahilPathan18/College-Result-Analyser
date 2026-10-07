@echo off
setlocal
title Result Analyzer Setup

echo ====================================================
echo           Installing Result Analyzer
echo ====================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$appDir = [System.IO.Path]::Combine($env:LOCALAPPDATA, 'ResultAnalyzer');" ^
    "Write-Host '1. Setting up application files in: ' $appDir;" ^
    "New-Item -ItemType Directory -Path $appDir -Force | Out-Null;" ^
    "if (Test-Path 'dist\ResultAnalyzer') { Copy-Item -Path 'dist\ResultAnalyzer\*' -Destination $appDir -Recurse -Force };" ^
    "Write-Host '2. Creating Desktop and Start Menu shortcuts...';" ^
    "$wshell = New-Object -ComObject WScript.Shell;" ^
    "$desktopLnk = [System.IO.Path]::Combine([Environment]::GetFolderPath('Desktop'), 'Result Analyzer.lnk');" ^
    "$startLnk = [System.IO.Path]::Combine($env:APPDATA, 'Microsoft\Windows\Start Menu\Programs', 'Result Analyzer.lnk');" ^
    "foreach ($p in @($desktopLnk, $startLnk)) {" ^
    "    $sc = $wshell.CreateShortcut($p);" ^
    "    $sc.TargetPath = 'D:\projects\result-analyzer\venv\Scripts\pythonw.exe';" ^
    "    $sc.Arguments = 'src\main.py';" ^
    "    $sc.WorkingDirectory = 'D:\projects\result-analyzer';" ^
    "    $sc.IconLocation = 'D:\projects\result-analyzer\assets\logo.ico,0';" ^
    "    $sc.Description = 'Result Analyzer';" ^
    "    $sc.Save();" ^
    "};" ^
    "Write-Host 'Installation completed successfully!';"

echo.
echo ====================================================
echo Setup Finished! You can launch Result Analyzer from
echo your Desktop shortcut or Start Menu.
echo ====================================================
pause
