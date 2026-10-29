import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from offer_page import build_offer_page


class OfferPageTests(unittest.TestCase):
    def test_builds_clean_public_page_without_faking_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.dict("os.environ", {}, clear=True):
                result = build_offer_page(root)
            self.assertTrue(result["created"])
            page = (root / "offer-page.html").read_text(encoding="utf-8")
            self.assertIn("Mini-audit SEO gratuito", page)
            self.assertIn("Gratuito per i primi 5 progetti pilota", page)
            self.assertIn("Contatto non ancora configurato", page)
            self.assertNotIn("example.org/pay", page)
            self.assertNotIn("Acquista", page)

    def test_adds_contact_and_payment_actions_only_for_valid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kit-di-lancio-offerta.md").write_text("# Offerta\n\nDettagli.", encoding="utf-8")
            env = {
                "CICCIO_CONTACT_EMAIL": "hello@example.org",
                "CICCIO_PAYMENT_URL": "https://checkout.example.org/pay",
            }
            with patch.dict("os.environ", env, clear=True):
                result = build_offer_page(root)
            self.assertTrue(result["created"])
            page = (root / "offer-page.html").read_text(encoding="utf-8")
            self.assertIn("mailto:hello@example.org", page)
            self.assertIn('href="https://checkout.example.org/pay"', page)
            self.assertIn("Vai al pagamento", page)

    def test_ignores_invalid_payment_url_and_contact_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "kit-di-lancio-offerta.md").write_text("# Offerta\n\nDettagli.", encoding="utf-8")
            env = {
                "CICCIO_CONTACT_EMAIL": "not-an-email",
                "CICCIO_PAYMENT_URL": "javascript:alert(1)",
            }
            with patch.dict("os.environ", env, clear=True):
                build_offer_page(root)
            page = (root / "offer-page.html").read_text(encoding="utf-8")
            self.assertNotIn("mailto:", page)
            self.assertNotIn("javascript:", page)
            self.assertIn("Contatto non ancora configurato", page)

    def test_creates_default_page_without_launch_kit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_offer_page(tmp)
            self.assertTrue(result["created"])
            self.assertTrue((Path(tmp) / "offer-page.html").is_file())


if __name__ == "__main__":
    unittest.main()
