"""
Release Packager Script for JARVIS AI
Runs PyInstaller to compile desktop binaries.
"""
import subprocess
import sys
from pathlib import Path

def build_release():
    root_dir = Path(__file__).resolve().parents[1]
    main_script = root_dir / "src" / "jarvis" / "main.py"
    icon_file = root_dir / "assets" / "icons" / "jarvis.ico"
    assets_dir = root_dir / "assets"
    
    print("🔨 Building JARVIS AI Release Executable...")
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--icon={icon_file}",
        f"--add-data={assets_dir};assets",
        "--name=JARVIS-AI",
        str(main_script)
    ]
    
    subprocess.run(cmd, check=True)
    print("\n✅ Build complete! Check dist/JARVIS-AI/ directory.")

if __name__ == "__main__":
    build_release()
