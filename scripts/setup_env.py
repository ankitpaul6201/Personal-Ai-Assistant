"""
Development Environment Bootstrap Script for JARVIS AI
"""
import subprocess
import sys
from pathlib import Path

def setup_environment():
    root_dir = Path(__file__).resolve().parents[1]
    print("🚀 Bootstrapping JARVIS AI Development Environment...")
    
    # 1. Install production requirements
    print("\n📦 Installing production requirements...")
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(root_dir / "requirements.txt")], check=True)
    
    # 2. Install dev requirements
    print("\n🛠️ Installing development tools...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(root_dir / "requirements-dev.txt")], check=True)
    
    # 3. Install package in editable mode
    print("\n⚙️ Installing jarvis-ai package in editable mode...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-e", str(root_dir)], check=True)
    
    # 4. Install Playwright browsers
    print("\n🌐 Installing Playwright browsers...")
    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
    
    print("\n✅ Environment Setup Complete!")

if __name__ == "__main__":
    setup_environment()
