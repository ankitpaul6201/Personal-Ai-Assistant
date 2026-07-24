"""
J.A.R.V.I.S. AI Resource and Exception Management Module

Provides PyInstaller-safe resource path resolution, automatic logs directory setup,
and unhandled crash exception logging.
"""

import os
import sys
import logging
import traceback
from pathlib import Path

def resource_path(relative_path: str | Path) -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    
    Args:
        relative_path: Relative file path within the project.
        
    Returns:
        Absolute Path object.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except AttributeError:
        # File is at src/jarvis/core/resource_manager.py -> parents[3] is project root
        base_path = Path(__file__).resolve().parents[3]

    path = Path(relative_path)
    if path.is_absolute():
        return path
    return (base_path / path).resolve()

def get_logs_dir() -> Path:
    """Returns absolute path to logs directory, creating it if necessary."""
    try:
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parents[3]
    except Exception:
        base_dir = Path.cwd()
        
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def setup_crash_logging() -> None:
    """Sets up crash logging handlers to record unhandled exceptions in logs/crash.log."""
    logs_dir = get_logs_dir()
    crash_log_file = logs_dir / "crash.log"
    
    logging.basicConfig(
        filename=str(crash_log_file),
        level=logging.ERROR,
        format="[%(asctime)s] [%(levelname)s]: %(message)s",
        encoding="utf-8",
    )

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logging.error(f"Unhandled Exception:\n{error_msg}")
        print(f"[CRASH] Unhandled Exception: {exc_value}", file=sys.stderr)

    sys.excepthook = handle_exception
