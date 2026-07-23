"""Unit tests for config_manager module."""
import json
import unittest
import tempfile
from pathlib import Path
from memory import config_manager

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.config_dir = Path(self.tmp_dir.name) / "config"
        self.config_file = self.config_dir / "api_keys.json"
        
        # Patch module paths for isolated testing
        self.orig_dir = config_manager.CONFIG_DIR
        self.orig_file = config_manager.CONFIG_FILE
        config_manager.CONFIG_DIR = self.config_dir
        config_manager.CONFIG_FILE = self.config_file

    def tearDown(self):
        config_manager.CONFIG_DIR = self.orig_dir
        config_manager.CONFIG_FILE = self.orig_file
        self.tmp_dir.cleanup()

    def test_save_and_read_api_key(self):
        config_manager.save_api_keys("AIzaSyD0123456789TestKey")
        assert config_manager.config_exists()
        
        # Verify JSON file written
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("gemini_api_key") == "AIzaSyD0123456789TestKey"

if __name__ == "__main__":
    unittest.main()
