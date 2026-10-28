import tempfile
import unittest
import zipfile
from pathlib import Path

from package_artifacts import package_artifacts


class PackageArtifactsTests(unittest.TestCase):
    def test_builds_index_and_valid_zip_with_markdown_products(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "offerta-e-prova.md").write_text("# Offerta\n\nContenuto.", encoding="utf-8")
            (root / "secondo.md").write_text("# Secondo\n", encoding="utf-8")
            result = package_artifacts(root)

            self.assertEqual(result["files"], 2)
            self.assertTrue(result["index"].is_file())
            self.assertTrue(result["zip"].is_file())
            page = result["index"].read_text(encoding="utf-8")
            self.assertIn("offerta-e-prova.md", page)
            self.assertIn("Verifica contenuti e fonti", page)
            with zipfile.ZipFile(result["zip"]) as bundle:
                self.assertIsNone(bundle.testzip())
                self.assertEqual(set(bundle.namelist()), {
                    "index.html", "offerta-e-prova.md", "secondo.md"
                })

    def test_empty_output_still_produces_valid_downloadable_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = package_artifacts(tmp)
            self.assertEqual(result["files"], 0)
            self.assertIn("nessun deliverable Markdown", result["index"].read_text(encoding="utf-8"))
            with zipfile.ZipFile(result["zip"]) as bundle:
                self.assertEqual(set(bundle.namelist()), {"index.html"})


if __name__ == "__main__":
    unittest.main()
