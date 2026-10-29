@echo off
title Launch Global Index Predictor GUI
cd /d "%~dp0"
echo ========================================================
echo   Launching Global Index Predictor Dashboard
echo ========================================================
echo.
echo Opening server at http://localhost:8085 ...
start http://localhost:8085
python server.py
if errorlevel 1 (
    echo Trying alternative Python path...
    "%LOCALAPPDATA%\Python\bin\python3.14.exe" server.py
)
pause
