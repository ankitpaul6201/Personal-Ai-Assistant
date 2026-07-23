"""Unit tests for memory_manager module."""
import json
import unittest
import tempfile
from pathlib import Path
from memory import memory_manager

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.memory_path = Path(self.tmp_dir.name) / "long_term.json"
        
        # Patch memory path for isolated testing
        self.orig_path = memory_manager.MEMORY_PATH
        memory_manager.MEMORY_PATH = self.memory_path

    def tearDown(self):
        memory_manager.MEMORY_PATH = self.orig_path
        self.tmp_dir.cleanup()

    def test_save_and_load_memory(self):
        memory_manager.save_memory({
            "identity": {
                "user_name": {"value": "Ankit"}
            }
        })
        mem = memory_manager.load_memory()
        assert "identity" in mem
        assert mem["identity"]["user_name"].get("value") == "Ankit"

    def test_update_memory(self):
        memory_manager.update_memory({
            "preferences": {
                "theme": {"value": "dark"}
            }
        })
        mem = memory_manager.load_memory()
        assert mem.get("preferences", {}).get("theme", {}).get("value") == "dark"

if __name__ == "__main__":
    unittest.main()
