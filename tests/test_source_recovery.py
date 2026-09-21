import unittest
import ssl
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.context_scan import read_candidates, read_source, scan


class SourceRecoveryTests(unittest.TestCase):
    def setUp(self):
        from app.search_session import SearchSession
        session = patch('app.context_scan.search_session', SearchSession(interval=0))
        session.start()
        self.addCleanup(session.stop)

    def selection(self, count):
        candidates = [{'url': f'https://site{i}.org/article', 'title': f'Artikel {i}',
                       'relevance': .9, 'selected': i < 5, 'reason': 'Relevan'}
                      for i in range(count)]
        return {'selected': candidates[:5], 'candidates': candidates}

    def article(self, url):
        return [{'url': url, 'title': 'Sumber', 'text': 'Teks sumber tentang ' + url}], []

    def test_failed_hosts_replaced_until_five_are_read(self):
        selection = self.selection(9)

        def read(url):
            if url.startswith(('https://site0.', 'https://site1.')):
                return [], [{'url': url, 'error': 'robots.txt HTTP 403'}]
            return self.article(url)

        with patch('app.context_scan.read_source', side_effect=read) as reader:
            sources, errors = read_candidates(selection, 'Klaim')
        self.assertEqual(len(sources), 5)
        self.assertEqual(reader.call_count, 7)
        self.assertEqual(len(selection['selected']), 7)
        self.assertEqual(selection['reading']['attempted_hosts'], 7)
        self.assertEqual(selection['reading']['read_hosts'], 5)
        self.assertFalse(selection['reading']['limit_reached'])
        self.assertEqual(selection['candidates'][0]['read_status'], 'failed')
        self.assertIn('https://site0.org/article', errors[0])
        self.assertFalse(selection['candidates'][7]['selected'])

    def test_all_failures_stop_at_budget_not_all_search_hits(self):
        selection = self.selection(15)
        with patch('app.context_scan.read_source', return_value=([], [{'error': 'HTTP 403'}])) as reader:
            sources, errors = read_candidates(selection, 'Klaim')
        self.assertEqual(reader.call_count, 10)
        self.assertEqual(sources, [])
        self.assertTrue(selection['reading']['limit_reached'])
        self.assertEqual(len(errors), 10)

    def test_irrelevant_and_repeated_hosts_never_fill_slots(self):
        selection = self.selection(3)
        selection['candidates'][1]['relevance'] = .1
        selection['candidates'][2]['url'] = 'https://www.site0.org/duplicate'
        selection['selected'] = selection['candidates'][:1]
        with patch('app.context_scan.read_source', return_value=([], [])) as reader:
            sources, _ = read_candidates(selection, 'Klaim')
        reader.assert_called_once_with('https://site0.org/article')
        self.assertFalse(selection['reading']['limit_reached'])
        self.assertEqual(sources, [])

    def test_initial_success_does_not_fetch_reserves(self):
        selection = self.selection(12)
        with patch('app.context_scan.read_source', side_effect=self.article) as reader:
            sources, _ = read_candidates(selection, 'Klaim')
        self.assertEqual(reader.call_count, 5)
        self.assertEqual(len(sources), 5)

    def test_redirect_duplicates_cannot_count_twice(self):
        selection = self.selection(7)

        def read(url):
            if url.startswith('https://site1.'):
                return self.article('https://www.site0.org/article')
            return self.article(url)

        with patch('app.context_scan.read_source', side_effect=read) as reader:
            sources, _ = read_candidates(selection, 'Klaim')
        self.assertEqual(reader.call_count, 6)
        self.assertEqual(len(sources), 5)

    def test_transient_http_failure_retries_once(self):
        with patch('app.context_scan.crawl', side_effect=[
            ([], [{'error': 'HTTP 503', 'retryable': True}]), self.article('https://example.org')
        ]) as crawler:
            sources, errors = read_source('https://example.org')
        self.assertEqual(crawler.call_count, 2)
        self.assertEqual(len(sources), 1)
        self.assertEqual(errors, [])

    def test_access_denial_does_not_retry(self):
        with patch('app.context_scan.crawl', return_value=([], [{'error': 'HTTP 403', 'retryable': False}])) as crawler:
            sources, _ = read_source('https://example.org')
        self.assertEqual(crawler.call_count, 1)
        self.assertEqual(sources, [])

    def test_certificate_failure_does_not_retry(self):
        with patch('app.context_scan.crawl', side_effect=ssl.SSLCertVerificationError('certificate failed')) as crawler:
            sources, errors = read_source('https://example.org')
        self.assertEqual(crawler.call_count, 1)
        self.assertFalse(errors[0]['retryable'])
        self.assertEqual(sources, [])

    def test_scan_recovers_after_blocked_source_without_new_search(self):
        search = Mock()
        search.text.return_value = [{'href': f'https://site{i}.org/article', 'title': 'Artikel terkait'}
                                   for i in range(6)]

        def read(url):
            if url.startswith('https://site0.'):
                return [], [{'url': url, 'error': 'robots.txt HTTP 403'}]
            return self.article(url)

        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=Mock(return_value=search))}), \
                patch('app.relevance.compare_pair', return_value=[.05, .9, .05]), \
                patch('app.context_scan.read_source', side_effect=read), \
                patch('app.context_scan.classify_evidence', return_value=None):
            result = scan(SimpleNamespace(kind='text', text='Panel surya menghasilkan listrik.'))
        self.assertEqual(len(result['sources']), 5)
        self.assertEqual(result['selection']['reading']['attempted_hosts'], 6)
        self.assertEqual(search.text.call_count, 2)
        self.assertIn('6 dari 6 kandidat dicoba', result['reason'])
        self.assertIn('site0.org', result['errors'][0])
