import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.screen_check import changed, normalize, check_text


class ScreenTests(unittest.TestCase):
    def test_deduplicate_and_ignore_short_text(self):
        self.assertFalse(changed("", "menu"))
        self.assertFalse(changed("berita " * 30, "berita " * 30))
        self.assertTrue(changed("", "berita baru " * 30))
        self.assertEqual(normalize("a\n  b"), "a b")

    @patch("app.screen_check.classify")
    @patch("app.screen_check.crawl")
    def test_sources_do_not_prove_truth(self, crawl, classify):
        search = Mock()
        search.return_value.text.return_value = [{"href": "https://example.com"}]
        crawl.return_value = ([{"title": "Artikel", "url": "https://example.com", "text": "isi"}], [])
        classify.return_value = {"label": "Indikasi tidak hoaks"}
        with patch.dict(sys.modules, {"ddgs": SimpleNamespace(DDGS=search)}):
            result = check_text("berita " * 30)
        self.assertEqual(result["label"], "Belum terverifikasi")
        self.assertEqual(len(result["sources"]), 1)

    @patch("app.screen_check.classify")
    def test_cancel_prevents_search(self, classify):
        search = Mock()
        with patch.dict(sys.modules, {"ddgs": SimpleNamespace(DDGS=search)}):
            self.assertIsNone(check_text("berita " * 30, lambda: True))
        search.assert_not_called()
        classify.assert_not_called()
