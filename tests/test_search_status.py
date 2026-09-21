import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.context_scan import scan
from app.search_status import error_kind, summarize_search


class SearchStatusTests(unittest.TestCase):
    def setUp(self):
        from app.search_session import SearchSession
        session = patch('app.context_scan.search_session', SearchSession(interval=0))
        session.start()
        self.addCleanup(session.stop)

    def test_failure_categories(self):
        for exc, expected in ((TimeoutError('timed out'), 'timeout'),
                              (RuntimeError('429 rate limit'), 'rate_limit'),
                              (RuntimeError('certificate validation failed'), 'certificate'),
                              (RuntimeError('No results found.'), 'empty'),
                              (OSError('connection refused'), 'connection')):
            self.assertEqual(error_kind(exc), expected)

    def test_partial_search_keeps_successful_hits(self):
        result = summarize_search([{'status': 'timeout'}, {'status': 'success'}], 4)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['candidate_count'], 4)

    def test_no_candidates_does_not_run_ranker_or_claim_success(self):
        for failure, expected in ((TimeoutError('timed out'), 'failed'),
                                  (RuntimeError('No results found.'), 'empty')):
            search = Mock()
            search.text.side_effect = failure
            with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=Mock(return_value=search))}), \
                    patch('app.context_scan.rank_candidates') as rank:
                result = scan(SimpleNamespace(kind='text', text='Panel surya menghasilkan listrik.'))
            rank.assert_not_called()
            self.assertEqual(result['search']['status'], expected)
            self.assertEqual(result['selection']['status'], 'search_' + expected)
            self.assertNotIn('0 dari 0', result['reason'])
            self.assertEqual(result['analysis_error'], result['search']['message'])
            self.assertIsNone(result['analysis'])

    def test_constructor_failure_is_reported(self):
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=Mock(side_effect=OSError('offline')))}):
            result = scan(SimpleNamespace(kind='text', text='Contoh klaim.'))
        self.assertEqual(result['search']['status'], 'failed')
        self.assertIn('gagal terhubung', result['analysis_error'])
