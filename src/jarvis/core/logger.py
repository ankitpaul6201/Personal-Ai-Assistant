"""
J.A.R.V.I.S. AI Structured Logging Module

Provides thread-safe, structured logging with automatic secret redaction.
"""

import logging
import sys
from .security import mask_secret

class RedactingFormatter(logging.Formatter):
    """Logging Formatter that redacts sensitive API keys and tokens from log messages."""
    
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        return mask_secret(original)


def get_logger(name: str = "JarvisAI") -> logging.Logger:
    """
    Retrieve configured logger instance with redacting formatter.
    
    Args:
        name: Module or component logger name.
        
    Returns:
        Configured Logger instance.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = RedactingFormatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s", datefmt="%H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger
