@echo off
echo ===================================================
echo   Building J.A.R.V.I.S. AI Production Executable
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
pyinstaller --noconfirm Jarvis.spec

echo Preparing release directory...
if not exist release mkdir release
xcopy /E /I /Y dist\Jarvis release\Jarvis

echo ===================================================
echo   Build Completed Successfully! Output in release/
echo ===================================================
pause
