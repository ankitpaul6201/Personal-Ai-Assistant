@echo off
title JARVIS AI Assistant
cd /d "%~dp0"
echo Starting JARVIS AI...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo JARVIS exited with error code %ERRORLEVEL%.
    pause
)
