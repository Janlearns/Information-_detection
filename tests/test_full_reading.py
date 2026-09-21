import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import urlsplit
from app.context_scan import scan
from app.main import ScanRequest
from app.crawler import crawl
from app.evidence import token_windows, aggregate_passages, classify_evidence


class FullReadingTests(unittest.TestCase):
    def setUp(self):
        from app.search_session import SearchSession
        session = patch('app.context_scan.search_session', SearchSession(interval=0))
        session.start()
        self.addCleanup(session.stop)

    @patch('app.relevance.compare_pair', return_value=[.8, .1, .1])
    def test_five_hosts_including_term_search(self, relevance):
        search = Mock()
        search.return_value.text.return_value = [{'title': 'Notokorda', 'href': f'https://site{i}.org/article'} for i in range(9)]
        def read(url, limit):
            return [{'url': url, 'title': 'Sumber', 'text': 'Notokorda adalah struktur tubuh.'}], []
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}), patch('app.context_scan.crawl', side_effect=read) as crawler, patch('app.context_scan.classify_evidence', return_value=None):
            result = scan(ScanRequest(kind='text', text='notokorda'))
        self.assertEqual(crawler.call_count, 5)
        self.assertEqual(len(result['sources']), 5)
        self.assertIn('struktur tubuh', result['terms'][0]['meaning'])

    def test_extraction_keeps_tail_beyond_old_limit(self):
        body = 'Isi artikel. ' * 3000 + 'BUKTI DI BAGIAN AKHIR'
        with patch('app.crawler.validate_url', return_value=(urlsplit('https://example.org/a'), '8.8.8.8')), patch('app.crawler.fetch', side_effect=[('https://example.org/robots.txt', 404, ''), ('https://example.org/a', 200, '<title>Artikel</title>')]), patch('app.crawler.time.sleep'), patch('app.crawler.trafilatura.extract', return_value=body):
            articles, errors = crawl('https://example.org/a')
        self.assertFalse(errors)
        self.assertEqual(articles[0]['text'], body)
        self.assertFalse(articles[0]['extraction_truncated'])

    def test_every_token_including_tail_is_covered(self):
        tokens = list(range(5000))
        windows = list(token_windows(tokens, 340))
        self.assertEqual(set(tokens), {token for window in windows for token in window})
        self.assertEqual(windows[-1][-1], 4999)
        self.assertTrue(all(len(window) <= 340 for window in windows))

    @patch('app.evidence.compare_pair', return_value=[.98, .01, .01])
    def test_entire_article_sent_to_model(self, compare):
        body = 'Pendahuluan ' * 4000 + 'Bukti pada akhir.'
        result = classify_evidence('Klaim', [{'url': 'https://example.org', 'purpose': 'Pemeriksaan fakta', 'excerpt': 'Pendahuluan', 'text': body}])
        compare.assert_called_once_with(body, 'Klaim')
        self.assertEqual(result['comparisons'][0]['characters_analyzed'], len(body))

    def test_tail_evidence_not_diluted_by_unrelated_passages(self):
        scores = aggregate_passages([[.01, .01, .98]] * 100 + [[.98, .01, .01]])
        self.assertGreater(scores[0], .95)
        conflict = aggregate_passages([[.98, .01, .01], [.01, .98, .01]])
        self.assertAlmostEqual(conflict[0], conflict[1])
