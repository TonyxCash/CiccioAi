"""Offline end-to-end simulation of Ciccio's guarded repair path."""
import json
import os
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch

import ciccio.self_repair as repair


class FakeGroq:
    def __init__(self, api_key):
        self.chat = MagicMock()
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps({
            "summary": "Simulated minimal correction",
            "changes": [{"path": "ciccio/app.py", "content": "SIMULATED_REPAIR = True\\n"}],
        })
        self.chat.completions.create.return_value = response


class SelfRepairSimulationTests(unittest.TestCase):
    def test_full_offline_repair_path_creates_review_branch_without_publishing(self):
        metadata = {
            "head_repository": {"full_name": "TonyxCash/CiccioAi"},
            "head_branch": "main",
            "name": "Ciccio tests",
            "status": "completed",
            "conclusion": "failure",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ciccio").mkdir()
            target = root / "ciccio" / "app.py"
            target.write_text("ORIGINAL = True\\n", encoding="utf-8")
            original_cwd = Path.cwd()
            try:
                os.chdir(root)
                with ExitStack() as stack:
                    stack.enter_context(patch.dict(os.environ, {
                        "GITHUB_REPOSITORY": "TonyxCash/CiccioAi",
                        "CICCIO_FAILED_RUN_ID": "123456",
                        "GITHUB_TOKEN": "fake-github-token",
                        "GROQ_API_KEY": "fake-groq-key",
                    }, clear=False))
                    stack.enter_context(patch.object(repair, "github_api_json", return_value=metadata))
                    stack.enter_context(patch.object(repair, "fetch_logs", return_value="AssertionError: simulated failure"))
                    stack.enter_context(patch.object(repair, "complete_sources", return_value={"ciccio/app.py": "ORIGINAL = True\\n"}))
                    stack.enter_context(patch.object(repair, "Groq", FakeGroq))
                    mocked_run = stack.enter_context(patch.object(
                        repair, "run", return_value="diff --git a/ciccio/app.py b/ciccio/app.py\\n"
                    ))
                    repair.main()
            finally:
                os.chdir(original_cwd)

            self.assertEqual(target.read_text(encoding="utf-8"), "SIMULATED_REPAIR = True\\n")
            commands = [call.args[0] for call in mocked_run.call_args_list]
            self.assertTrue(any(command[:3] == ["git", "checkout", "-b"] for command in commands))
            self.assertTrue(any(command[:2] == ["git", "commit"] for command in commands))
            self.assertFalse(any("push" in command for command in commands))
            self.assertFalse(any("gh" in command for command in commands))


if __name__ == "__main__":
    unittest.main()
