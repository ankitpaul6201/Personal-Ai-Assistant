"""Security unit tests covering path traversal, secret masking, and injection prevention."""
import unittest
import tempfile
from pathlib import Path
from core.security import mask_secret, validate_safe_path, sanitize_shell_args
from core.exceptions import SecurityViolationError

class TestSecurity(unittest.TestCase):
    def test_secret_masking(self):
        # Dynamically build mock secret string to prevent static scanner false positives
        raw_key = ("AI" + "zaSy") + "D01234567890123456789012345678901"
        masked = mask_secret(f"Config loaded with key {raw_key}")
        assert raw_key not in masked
        assert "[REDACTED_SECRET]" in masked

    def test_path_traversal_prevention(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            safe_root = tmp_path / "user_home"
            safe_root.mkdir()
            safe_file = safe_root / "documents" / "notes.txt"
            safe_file.parent.mkdir()
            safe_file.write_text("hello")
            
            # Valid path inside boundary
            resolved = validate_safe_path(safe_file, allowed_base=safe_root)
            assert resolved == safe_file.resolve()
            
            # Path traversal attack attempting to break out
            unauthorized_file = tmp_path / "etc" / "passwd"
            with self.assertRaises(SecurityViolationError):
                validate_safe_path(unauthorized_file, allowed_base=safe_root)

    def test_command_injection_sanitization(self):
        safe_args = ["echo", "hello_world"]
        assert sanitize_shell_args(safe_args) == safe_args
        
        unsafe_args = ["echo", "hello; rm -rf /"]
        with self.assertRaises(SecurityViolationError):
            sanitize_shell_args(unsafe_args)

if __name__ == "__main__":
    unittest.main()
