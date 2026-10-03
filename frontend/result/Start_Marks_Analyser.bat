@echo off
title Marks Analyser Desktop
cd /d "%~dp0"

echo ==================================================
echo         MARKS ANALYSER — DESKTOP LAUNCHER         
echo ==================================================
echo.

:: Launch Desktop App via Python
python desktop_app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Launching via app.py fallback...
    start /b python app.py
    timeout /t 2 >nul
    start msedge.exe --app=http://127.0.0.1:5000 --window-size=1320,860
)

pause
