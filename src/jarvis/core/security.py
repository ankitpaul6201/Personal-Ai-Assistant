"""
J.A.R.V.I.S. AI Security Module

Provides path traversal verification, command argument sanitization,
input validation, and secret masking utilities.
"""

import os
import re
from pathlib import Path
from typing import Union, List
from .exceptions import SecurityViolationError

# Patterns for masking secrets in logs and UI labels
_API_KEY_PATTERN = re.compile(r'(MOCK_SECRET_[A-Za-z0-9_-]{16,64}|[a-zA-Z0-9]{39,64})')

def mask_secret(text: str) -> str:
    """
    Mask sensitive API keys or credentials in raw string output.
    
    Args:
        text: Raw input string containing possible secrets.
        
    Returns:
        String with secrets redacted.
    """
    if not text:
        return ""
    return _API_KEY_PATTERN.sub('[REDACTED_SECRET]', str(text))


def validate_safe_path(target_path: Union[str, Path], allowed_base: Union[str, Path] = None) -> Path:
    """
    Ensure target_path resolves strictly within allowed_base directory to prevent path traversal attacks.
    
    Args:
        target_path: Absolute or relative file path to check.
        allowed_base: Base directory boundary. Defaults to User Home directory if not specified.
        
    Returns:
        Resolved absolute Path object.
        
    Raises:
        SecurityViolationError: If target path escapes allowed_base boundary.
    """
    resolved_target = Path(target_path).expanduser().resolve()
    base_boundary = Path(allowed_base if allowed_base else Path.home()).expanduser().resolve()
    
    try:
        resolved_target.relative_to(base_boundary)
    except ValueError:
        raise SecurityViolationError(
            f"Path traversal detected: Path '{target_path}' is outside allowed boundary '{base_boundary}'."
        )
        
    return resolved_target


def sanitize_shell_args(args: List[str]) -> List[str]:
    """
    Sanitize list of command-line arguments to prevent subshell injection.
    
    Args:
        args: List of argument strings.
        
    Returns:
        List of sanitized strings safe for subprocess execution with shell=False.
    """
    forbidden_chars = re.compile(r'[;&|`$><]')
    sanitized = []
    for arg in args:
        arg_str = str(arg)
        if forbidden_chars.search(arg_str):
            raise SecurityViolationError(f"Command injection character detected in argument: {arg_str}")
        sanitized.append(arg_str)
    return sanitized
