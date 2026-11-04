import os
import unittest
from unittest.mock import patch

from agent_runner import (
    collect_task_sources,
    collect_google_places,
    extract_public_contacts,
    normalize_public_url,
    parse_osm_clothing_stores,
    parse_google_places_response,
    task_search_queries,
)


class OpenStreetMapLeadTests(unittest.TestCase):
    def test_parses_independent_stores_and_skips_known_chains(self):
        payload = {"elements": [
            {"type": "node", "id": 101, "tags": {
                "name": "Boutique Aurora", "shop": "clothes",
                "addr:city": "Napoli", "addr:street": "Via Roma",
                "website": "https://aurora.example",
                "phone": "+39 02 1234567",
                "email": "info@aurora.example"
            }},
            {"type": "node", "id": 102, "tags": {
                "name": "Boutique Aurora", "shop": "clothes", "addr:city": "Napoli"
            }},
            {"type": "way", "id": 103, "tags": {
                "name": "Zara", "shop": "clothes", "addr:city": "Caserta"
            }},
            {"type": "node", "id": 104, "tags": {
                "name": "Atelier Stella", "shop": "boutique", "addr:city": "Caserta"
            }},
        ]}
        rows = parse_osm_clothing_stores(payload, ["Napoli", "Caserta"], limit=10)
        self.assertEqual(len(rows), 2)
        self.assertEqual(
            {row["business_name"] for row in rows},
            {"Boutique Aurora", "Atelier Stella"},
        )
        self.assertTrue(all(row["record_verified"] for row in rows))
        aurora = next(row for row in rows if row["business_name"] == "Boutique Aurora")
        self.assertEqual(aurora["website_tag"], "https://aurora.example")
        self.assertEqual(aurora["phone"], "+39 02 1234567")
        self.assertEqual(aurora["email"], "info@aurora.example")
        self.assertIn("OpenStreetMap contributors", aurora["page_excerpt"])

    def test_uses_queried_municipality_when_osm_address_is_missing(self):
        payload = {"elements": [{
            "type": "node", "id": 205,
            "tags": {"name": "Atelier Campania", "shop": "clothes"}
        }]}
        rows = parse_osm_clothing_stores(payload, ["Giugliano in Campania"], limit=10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["city"], "Giugliano in Campania")

    def test_search_queries_are_limited_to_campania_and_cover_all_business_sectors(self):
        queries = task_search_queries(
            "Ricerca clienti — Campania — lotto 001",
            "Trova negozi di abbigliamento, ristoranti e pizzerie indipendenti in Campania per proporre siti web",
        )
        joined = " ".join(queries).casefold()
        self.assertIn("giugliano", joined)
        self.assertNotIn("milano", joined)
        self.assertIn("caserta", joined)
        self.assertIn("napoli", joined)
        self.assertIn("ristoranti", joined)
        self.assertIn("pizzerie", joined)



    @patch("agent_runner.collect_osm_clothing_stores", return_value=[])
    @patch("agent_runner.collect_google_places", return_value=[])
    @patch("agent_runner.fetch_public_page_text", return_value="Boutique abbigliamento Arlington Texas")
    @patch("agent_runner.search_web")
    def test_rejects_business_results_outside_campania(self, search, fetch_page, google, osm):
        search.return_value = [{
            "title": "Boutique abbigliamento Arlington",
            "url": "https://boutique.example",
            "snippet": "Clothing boutique in Arlington, Texas",
        }]
        rows = collect_task_sources(
            "Ricerca clienti — Campania — lotto 001",
            "Trova boutique indipendenti in Campania per siti web",
            max_results=24,
        )
        self.assertFalse(any("boutique.example" in row.get("url", "") for row in rows))

    def test_extracts_only_public_email_and_italian_phone(self):
        contacts = extract_public_contacts(
            "Contatti: info@atelier.example - Tel. 081 1234567"
        )
        self.assertEqual(contacts["email"], "info@atelier.example")
        self.assertEqual(contacts["phone"], "081 1234567")

    def test_ignores_non_italian_phone_patterns(self):
        contacts = extract_public_contacts("Call 555-123-4567 or visit our store")
        self.assertEqual(contacts, {"phone": "", "email": ""})


    def test_google_places_requires_explicit_zero_cost_opt_in(self):
        from unittest.mock import patch
        with patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "test-key"}, clear=True):
            self.assertEqual(collect_google_places("negozio abbigliamento Napoli"), [])

    def test_parses_google_places_business_data(self):
        rows = parse_google_places_response({
            "places": [{
                "id": "place-123",
                "displayName": {"text": "Trattoria Aurora"},
                "formattedAddress": "Via Roma 10, Bologna BO",
                "websiteUri": "https://aurora.example",
                "nationalPhoneNumber": "+39 051 123456",
                "googleMapsUri": "https://maps.google.com/?cid=123",
                "businessStatus": "OPERATIONAL",
            }]
        }, "Bologna", limit=5)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["business_name"], "Trattoria Aurora")
        self.assertEqual(rows[0]["phone"], "+39 051 123456")
        self.assertEqual(rows[0]["website_tag"], "https://aurora.example")
        self.assertEqual(rows[0]["source_type"], "google_places_record")

    def test_rejects_private_urls(self):
        self.assertEqual(normalize_public_url("https://example.com/path"), "https://example.com/path")
        self.assertEqual(normalize_public_url("http://127.0.0.1/admin"), "")
        self.assertEqual(normalize_public_url("http://localhost/admin"), "")
        self.assertEqual(normalize_public_url("http://192.168.1.5"), "")

    @patch("agent_runner.collect_osm_clothing_stores")
    @patch("agent_runner.search_web")
    @patch("agent_runner.fetch_public_page_text")
    def test_verifies_exact_name_before_adding_official_website(self, fetch_page, search, osm):
        osm.return_value = [{
            "title": "Atelier Aurora — Napoli",
            "url": "https://www.openstreetmap.org/node/101",
            "query": "OpenStreetMap Campania — Napoli",
            "snippet": "Atelier Aurora; Città: Napoli",
            "page_verified": False,
            "record_verified": True,
            "source_type": "openstreetmap_record",
            "business_name": "Atelier Aurora",
            "city": "Napoli",
            "website_tag": "",
            "page_excerpt": "Atelier Aurora; Città: Napoli",
        }]
        search.return_value = [{
            "title": "Atelier Aurora",
            "url": "https://aurora.example",
            "snippet": "",
        }]
        fetch_page.return_value = "Atelier Aurora — abbigliamento donna, Napoli"
        rows = collect_task_sources(
            "Ricerca clienti — Campania — lotto 001",
            "Trova negozi di abbigliamento indipendenti in Campania per siti web",
            max_results=24,
        )
        self.assertTrue(any(row.get("record_verified") for row in rows))
        self.assertTrue(any(row.get("source_type") == "official_website" for row in rows))


if __name__ == "__main__":
    unittest.main()
