@echo off
echo ===================================================
echo   Building J.A.R.V.I.S. AI Standalone Executable
echo ===================================================

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install pyinstaller -r requirements.txt

echo Cleaning old build artifacts...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist release rmdir /s /q release

echo Running PyInstaller...
pyinstaller --noconfirm --distpath release Jarvis.spec

echo ===================================================
echo   Build Completed Successfully! Output: release/Jarvis.exe
echo ===================================================
pause
