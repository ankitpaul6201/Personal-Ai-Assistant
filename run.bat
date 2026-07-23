@echo off
if exist release\Jarvis.exe (
    start "" "release\Jarvis.exe"
) else if exist release\Jarvis\Jarvis.exe (
    start "" "release\Jarvis\Jarvis.exe"
) else (
    echo Running python main.py...
    python main.py
)
