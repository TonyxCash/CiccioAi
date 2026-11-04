import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from offer_page import build_offer_page


class OfferPageTests(unittest.TestCase):
    def test_builds_website_service_page_with_safe_default_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {}, clear=True):
                result = build_offer_page(tmp)
            page = (Path(tmp) / "offer-page.html").read_text(encoding="utf-8")
        self.assertTrue(result["created"])
        self.assertEqual(result["contact_email"], "ciccio.servizi@proton.me")
        self.assertIn("Siti web per piccole attività", page)
        self.assertIn("negozi indipendenti, boutique, ristoranti e pizzerie", page)
        self.assertIn("mailto:ciccio.servizi@proton.me", page)
        self.assertNotIn("5 annunci", page)
        self.assertNotIn("15 €", page)
        self.assertNotIn("paypal.com", page)

    def test_invalid_contact_secret_falls_back_to_valid_public_address(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"CICCIO_CONTACT_EMAIL": "ciccio.servizi@proton.m"}, clear=True):
                result = build_offer_page(tmp)
            page = (Path(tmp) / "offer-page.html").read_text(encoding="utf-8")
        self.assertEqual(result["contact_email"], "ciccio.servizi@proton.me")
        self.assertIn("mailto:ciccio.servizi@proton.me", page)
        self.assertNotIn("proton.m", page)

    def test_uses_valid_custom_contact_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict("os.environ", {"CICCIO_CONTACT_EMAIL": "hello@example.org"}, clear=True):
                result = build_offer_page(tmp)
            page = (Path(tmp) / "offer-page.html").read_text(encoding="utf-8")
        self.assertEqual(result["contact_email"], "hello@example.org")
        self.assertIn("mailto:hello@example.org", page)

    def test_page_is_created_with_sufficient_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = build_offer_page(tmp)
            self.assertTrue(Path(result["path"]).is_file())
            self.assertGreater(result["bytes"], 1000)


if __name__ == "__main__":
    unittest.main()
