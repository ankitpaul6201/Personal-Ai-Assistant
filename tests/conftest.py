"""
Pytest configuration and global test fixtures for JARVIS AI.
"""
import sys
from pathlib import Path

# Add project root and src directory to sys.path for test resolution
ROOT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT_DIR / "src"
JARVIS_DIR = SRC_DIR / "jarvis"

for path in (str(SRC_DIR), str(JARVIS_DIR), str(ROOT_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)
