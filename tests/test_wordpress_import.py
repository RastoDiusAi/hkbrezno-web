import unittest
from unittest.mock import patch

from scripts.import_wordpress import (
    extract_content_blocks,
    fetch,
    import_contact,
    import_ice_schedule,
    sanitize_content,
    slugify,
)


class WordPressImportSecurityTests(unittest.TestCase):
    def test_sanitizer_removes_active_content_and_event_handlers(self):
        source = (
            '<p onclick="alert(1)">Bezpečný text<script>alert(1)</script></p>'
            '<iframe src="https://example.com"></iframe>'
            '<a href="javascript:alert(1)">zlý odkaz</a>'
            '<img src="javascript:alert(1)" onerror="alert(1)">'
        )

        cleaned = sanitize_content(source)

        self.assertIn("Bezpečný text", cleaned)
        self.assertNotIn("script", cleaned.lower())
        self.assertNotIn("iframe", cleaned.lower())
        self.assertNotIn("onclick", cleaned.lower())
        self.assertNotIn("onerror", cleaned.lower())
        self.assertNotIn("javascript:", cleaned.lower())
        self.assertNotIn("<img", cleaned.lower())

    def test_blank_target_always_gets_noopener(self):
        cleaned = sanitize_content(
            '<a href="https://example.com" target="_blank" rel="opener">Odkaz</a>'
        )
        self.assertIn('rel="noopener noreferrer"', cleaned)
        self.assertNotIn('rel="opener"', cleaned)

    def test_fetch_rejects_non_https_and_other_hosts_before_network(self):
        with self.assertRaises(ValueError):
            fetch("http://www.hkbrezno.sk/test", "www.hkbrezno.sk")
        with self.assertRaises(ValueError):
            fetch("https://example.com/test", "www.hkbrezno.sk")

    def test_slugify_creates_safe_article_path(self):
        self.assertEqual(
            slugify("🏒 Naše dievčatá uspeli!"),
            "nase-dievcata-uspeli",
        )

    def test_history_extraction_stops_before_partners(self):
        blocks = extract_content_blocks(
            "<h1>História</h1><p>Prvý oddiel.</p><h2>Partneri</h2><p>Logo</p>",
            stop_heading="Partneri",
        )
        self.assertEqual(
            blocks,
            [
                {"tag": "h1", "text": "História"},
                {"tag": "p", "text": "Prvý oddiel."},
            ],
        )

    @patch("scripts.import_wordpress.download_asset", return_value="/documents/wordpress/rozpis-ladu/rozpis.pdf")
    def test_ice_schedule_prefers_same_host_pdf(self, download_asset):
        page = {
            "date": "2026-01-01T10:00:00",
            "modified": "2026-01-02T10:00:00",
            "link": "https://www.hkbrezno.sk/rozpis-ladu/",
            "title": {"rendered": "Rozpis ľadu"},
            "content": {"rendered": (
                '<img src="https://www.hkbrezno.sk/wp-content/uploads/rozpis.png">'
                '<a href="https://www.hkbrezno.sk/wp-content/uploads/rozpis.pdf">PDF</a>'
            )},
        }
        result = import_ice_schedule(page, "https://www.hkbrezno.sk")
        self.assertEqual(result["assetType"], "pdf")
        self.assertTrue(result["asset"].endswith("rozpis.pdf"))
        download_asset.assert_called_once()

    def test_ice_schedule_rejects_external_media(self):
        page = {
            "date": "2026-01-01T10:00:00",
            "link": "https://www.hkbrezno.sk/rozpis-ladu/",
            "title": {"rendered": "Rozpis ľadu"},
            "content": {"rendered": '<img src="https://example.com/rozpis.png">'},
        }
        result = import_ice_schedule(page, "https://www.hkbrezno.sk")
        self.assertEqual(result["asset"], "")
        self.assertEqual(result["assetType"], "")

    def test_contact_fields_are_read_from_wordpress_content(self):
        page = {
            "modified": "2026-01-02T10:00:00",
            "link": "https://www.hkbrezno.sk/klub/kontakt/",
            "content": {"rendered": (
                "<p>Hokejový klub Brezno</p><h5>Štvrť Testovacia 12</h5>"
                "<h5>977 01 Brezno</h5><h5>IČO</h5><h5>12345678</h5>"
                "<h5>DIČ</h5><h5>1234567890</h5>"
                "<h5>IČ DPH</h5><h5>SK1234567890</h5>"
                "<p>VVS/1-900/90-99999</p>"
            )},
        }
        result = import_contact(page)
        self.assertEqual(result["address"][0], "Štvrť Testovacia 12")
        self.assertEqual(result["companyId"], "12345678")
        self.assertEqual(result["vatId"], "SK1234567890")
        self.assertEqual(result["registryNumber"], "VVS/1-900/90-99999")


if __name__ == "__main__":
    unittest.main()
