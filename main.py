"""
J.A.R.V.I.S. AI - Root Launcher Script
Delegates execution to src.jarvis.main
"""
import sys
from pathlib import Path

# Add src to sys.path so jarvis package is importable
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis.main import main

if __name__ == "__main__":
    main()
