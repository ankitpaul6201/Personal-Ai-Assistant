"""
JARVIS AI Package CLI Launcher (`python -m jarvis`)
"""
import sys
from pathlib import Path

# Ensure src directory is in sys.path
src_dir = Path(__file__).resolve().parents[1]
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from jarvis.main import main

if __name__ == "__main__":
    main()
