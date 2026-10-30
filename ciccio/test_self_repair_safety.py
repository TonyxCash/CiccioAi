import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ciccio.self_repair import (
    ALLOWED_WORKFLOWS,
    MAX_FILE_CHARS,
    complete_sources,
    sanitize_logs,
    validate_changes,
    validate_run_metadata,
    run,
)


class SelfRepairSafetyTests(unittest.TestCase):
    def test_empty_proposal_is_noop(self):
        self.assertEqual(validate_changes([]), [])

    def test_rejects_path_outside_allowlist(self):
        with self.assertRaises(RuntimeError):
            validate_changes([{"path": "README.md", "content": "unsafe"}])

    def test_rejects_non_string_content(self):
        with self.assertRaises(RuntimeError):
            validate_changes([{"path": "ciccio/app.py", "content": None}])

    def test_rejects_oversized_content(self):
        with self.assertRaises(RuntimeError):
            validate_changes([{"path": "ciccio/app.py", "content": "x" * (MAX_FILE_CHARS + 1)}])

    def test_rejects_duplicate_paths(self):
        change = {"path": "ciccio/app.py", "content": "print(1)"}
        with self.assertRaises(RuntimeError):
            validate_changes([change, change])

    def test_accepts_one_allowed_change(self):
        result = validate_changes([{"path": "ciccio/app.py", "content": "print(1)"}])
        self.assertEqual(result, [("ciccio/app.py", "print(1)")])

    def test_complete_sources_skips_oversized_files(self):
        with tempfile.TemporaryDirectory() as directory:
            small = Path(directory) / "small.py"
            large = Path(directory) / "large.py"
            small.write_text("print(1)", encoding="utf-8")
            large.write_text("x" * (MAX_FILE_CHARS + 1), encoding="utf-8")
            result = complete_sources([str(small), str(large)])
            self.assertIn(str(small), result)
            self.assertNotIn(str(large), result)

    def test_accepts_only_trusted_failed_main_run(self):
        data = {
            "head_repository": {"full_name": "TonyxCash/CiccioAi"},
            "head_branch": "main",
            "name": "Ciccio tests",
            "status": "completed",
            "conclusion": "failure",
        }
        self.assertTrue(validate_run_metadata(data, "TonyxCash/CiccioAi"))

    def test_rejects_untrusted_run_metadata(self):
        base = {
            "head_repository": {"full_name": "TonyxCash/CiccioAi"},
            "head_branch": "main",
            "name": "Ciccio tests",
            "status": "completed",
            "conclusion": "failure",
        }
        variants = [
            {**base, "head_repository": {"full_name": "attacker/fork"}},
            {**base, "head_branch": "feature"},
            {**base, "name": "Untrusted workflow"},
            {**base, "status": "in_progress"},
            {**base, "conclusion": "success"},
        ]
        for data in variants:
            with self.subTest(data=data), self.assertRaises(RuntimeError):
                validate_run_metadata(data, "TonyxCash/CiccioAi")

    def test_repair_subprocess_never_receives_secrets(self):
        secret_names = ("GITHUB_TOKEN", "GROQ_API_KEY", "GH_TOKEN", "SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY")
        with patch.dict(os.environ, {name: "test-secret" for name in secret_names}, clear=False):
            with patch("ciccio.self_repair.subprocess.run") as mocked:
                mocked.return_value.returncode = 0
                mocked.return_value.stdout = "ok"
                mocked.return_value.stderr = ""
                self.assertEqual(run(["python", "-c", "pass"]), "ok")
                child_env = mocked.call_args.kwargs["env"]
                for name in secret_names:
                    self.assertNotIn(name, child_env)

    def test_sanitizes_common_secret_values_and_environment_lines(self):
        raw = (
            "ordinary diagnostic line\n"
            "GROQ_API_KEY=gsk_abcdefghijklmnopqrstuvwxyz012345\n"
            "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456\n"
            "safe line with token ghp_abcdefghijklmnopqrstuvwxyz123456\n"
        )
        cleaned = sanitize_logs(raw)
        self.assertIn("ordinary diagnostic line", cleaned)
        self.assertNotIn("GROQ_API_KEY", cleaned)
        self.assertNotIn("ghp_abcdefghijklmnopqrstuvwxyz123456", cleaned)
        self.assertNotIn("gsk_abcdefghijklmnopqrstuvwxyz012345", cleaned)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", cleaned)


if __name__ == "__main__":
    unittest.main()
