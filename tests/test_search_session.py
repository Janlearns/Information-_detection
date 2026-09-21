import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.search_session import SearchSession, SearchPaused
from app.context_scan import scan


class SearchSessionTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.
        self.waits = []
        self.session = SearchSession(clock=lambda: self.now, sleep=self.sleep)
        self.engine = Mock()
        self.engine.text.return_value = [{'href': 'https://example.org', 'title': 'Sumber'}]

    def sleep(self, seconds):
        self.waits.append(seconds)
        self.now += seconds

    def test_more_than_four_scans_reuse_metadata_not_network(self):
        for _ in range(10):
            rows, cached = self.session.query(self.engine, 'klaim yang sama')
            rows[0]['title'] = 'Mutation must not corrupt cached metadata'
        self.engine.text.assert_called_once()
        rows, cached = self.session.query(self.engine, 'KLAIM  yang sama')
        self.assertTrue(cached)
        self.assertEqual(rows[0]['title'], 'Sumber')

    def test_cache_expires_and_distinct_queries_are_paced(self):
        self.session.query(self.engine, 'klaim A')
        self.session.query(self.engine, 'klaim B')
        self.assertEqual(self.waits, [2.])
        self.now += 301
        _, cached = self.session.query(self.engine, 'klaim A')
        self.assertFalse(cached)
        self.assertEqual(self.engine.text.call_count, 3)

    def test_rate_limit_pauses_new_queries_but_cache_survives(self):
        self.session.query(self.engine, 'cached')
        self.engine.text.side_effect = RuntimeError('429 rate limit')
        with self.assertRaises(RuntimeError):
            self.session.query(self.engine, 'new')
        self.assertEqual(self.session.retry_after(), 60)
        with self.assertRaises(SearchPaused):
            self.session.query(self.engine, 'another')
        self.assertTrue(self.session.query(self.engine, 'cached')[1])
        self.assertEqual(self.engine.text.call_count, 2)
        self.now += 60
        self.engine.text.side_effect = None
        self.assertFalse(self.session.query(self.engine, 'new')[1])
        self.assertEqual(self.session.rate_strikes, 0)

    def test_repeated_rate_limits_increase_cooldown_without_extra_retries(self):
        self.engine.text.side_effect = RuntimeError('rate limit')
        for expected in (60, 120, 240, 300):
            with self.assertRaises(RuntimeError):
                self.session.query(self.engine, 'new')
            self.assertEqual(self.session.retry_after(), expected)
            self.now += expected
        self.assertEqual(self.engine.text.call_count, 4)

    def test_transport_breaker_recovers_after_pause(self):
        self.engine.text.side_effect = TimeoutError('timed out')
        for _ in range(3):
            with self.assertRaises(TimeoutError):
                self.session.query(self.engine, 'new')
        with self.assertRaises(SearchPaused) as exc:
            self.session.query(self.engine, 'new')
        self.assertEqual(exc.exception.kind, 'timeout')
        self.assertEqual(self.session.retry_after(), 15)
        self.now += 15
        self.engine.text.side_effect = None
        self.session.query(self.engine, 'new')
        self.assertEqual(self.session.transport_failures, 0)

    def test_empty_and_failed_results_not_cached_and_capacity_is_bounded(self):
        self.engine.text.return_value = []
        self.session.query(self.engine, 'empty')
        self.session.query(self.engine, 'empty')
        self.assertEqual(self.engine.text.call_count, 2)
        self.session.capacity = 2
        self.engine.text.return_value = [{'href': 'https://example.org'}]
        for key in ('a', 'b', 'c'):
            self.session.query(self.engine, key)
        self.assertEqual(list(self.session.cache), ['b', 'c'])

    def test_scan_reports_wait_and_does_not_call_provider_for_deferred_query(self):
        self.engine.text.side_effect = RuntimeError('429 rate limit')
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=Mock(return_value=self.engine))}), \
                patch('app.context_scan.search_session', self.session):
            result = scan(SimpleNamespace(kind='text', text='Panel surya menghasilkan listrik.'))
        self.engine.text.assert_called_once()
        self.assertEqual(result['search']['retry_after_seconds'], 60)
        self.assertTrue(result['search']['attempts'][1]['deferred'])
        self.assertIn('60 detik', result['analysis_error'])
