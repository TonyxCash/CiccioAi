import tempfile
import unittest
from pathlib import Path
from ciccio.self_repair import validate_changes, complete_sources, MAX_FILE_CHARS

class SelfRepairSafetyTests(unittest.TestCase):
    def test_empty_proposal_is_noop(self):
        self.assertEqual(validate_changes([]), [])

    def test_rejects_path_outside_allowlist(self):
        with self.assertRaises(RuntimeError):
            validate_changes([{"path":"README.md","content":"unsafe"}])

    def test_rejects_non_string_content(self):
        with self.assertRaises(RuntimeError):
            validate_changes([{"path":"ciccio/app.py","content":None}])

    def test_rejects_oversized_content(self):
        with self.assertRaises(RuntimeError):
            validate_changes([{"path":"ciccio/app.py","content":"x"*(MAX_FILE_CHARS+1)}])

    def test_rejects_duplicate_paths(self):
        change={"path":"ciccio/app.py","content":"print(1)"}
        with self.assertRaises(RuntimeError):
            validate_changes([change,change])

    def test_accepts_one_allowed_change(self):
        result=validate_changes([{"path":"ciccio/app.py","content":"print(1)"}])
        self.assertEqual(result,[("ciccio/app.py","print(1)")])

    def test_complete_sources_skips_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            small=Path(directory)/"small.py"
            large=Path(directory)/"large.py"
            small.write_text("print(1)",encoding="utf-8")
            large.write_text("x"*(MAX_FILE_CHARS+1),encoding="utf-8")
            result=complete_sources([str(small),str(large)])
            self.assertIn(str(small),result)
            self.assertNotIn(str(large),result)

if __name__ == "__main__":
    unittest.main()
