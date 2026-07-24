"""
J.A.R.V.I.S. AI Exception Hierarchy

Defines custom exception classes for domain-specific error handling,
graceful fallbacks, and security boundary violations.
"""

class JarvisBaseException(Exception):
    """Base exception for all J.A.R.V.I.S. application errors."""
    def __init__(self, message: str, code: str = "JARVIS_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code

class ConfigurationError(JarvisBaseException):
    """Raised when configuration values are missing, invalid, or corrupted."""
    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")

class SecurityViolationError(JarvisBaseException):
    """Raised when a path traversal, injection attack, or permission violation is detected."""
    def __init__(self, message: str):
        super().__init__(message, code="SECURITY_VIOLATION")

class CameraStreamError(JarvisBaseException):
    """Raised when hardware camera capture fails or hardware filter is busy."""
    def __init__(self, message: str):
        super().__init__(message, code="CAMERA_ERROR")

class AudioDeviceError(JarvisBaseException):
    """Raised when audio capture or playback device fails."""
    def __init__(self, message: str):
        super().__init__(message, code="AUDIO_ERROR")

class APIConnectionError(JarvisBaseException):
    """Raised when Gemini API or external HTTP service connections fail."""
    def __init__(self, message: str):
        super().__init__(message, code="API_ERROR")

class SystemControlError(JarvisBaseException):
    """Raised when OS-level computer setting adjustments or shortcuts fail."""
    def __init__(self, message: str):
        super().__init__(message, code="SYSTEM_CONTROL_ERROR")
