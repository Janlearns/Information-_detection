import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from app.relevance import rank_candidates
from app.context_scan import scan
from app.main import ScanRequest


class RelevanceTests(unittest.TestCase):
    @patch('app.relevance.compare_pair', side_effect=[[.01, .02, .97], [.95, .02, .03], [.02, .9, .08]])
    def test_keeps_contradiction_and_support_not_unrelated(self, model):
        hits = [{'href': f'https://site{i}.org/a', 'title': f'Title {i}', 'body': f'Snippet {i}'} for i in range(3)]
        result = rank_candidates('Klaim', hits)
        self.assertEqual([item['url'] for item in result['selected']], [hits[1]['href'], hits[2]['href']])
        model.assert_any_call('Title 1\nSnippet 1', 'Klaim')

    @patch('app.relevance.compare_pair', return_value=[.8, .1, .1])
    def test_missing_metadata_and_unsafe_urls_are_not_opened(self, model):
        result = rank_candidates('Klaim', [{'href': 'https://example.org'}, {'href': 'file:///file', 'title': 'Klaim'}])
        self.assertEqual(result['selected'], [])
        model.assert_not_called()

    @patch('app.relevance.compare_pair', side_effect=[[.5, .1, .4], [.8, .1, .1]] + [[.7, .1, .2]] * 6)
    def test_rank_before_host_limit(self, model):
        hits = [{'href': 'https://www.example.org/low', 'title': 'Low'}, {'href': 'https://example.org/high', 'title': 'High'}]
        hits += [{'href': f'https://site{i}.org', 'title': 'Candidate'} for i in range(6)]
        result = rank_candidates('Klaim', hits)
        self.assertEqual(len(result['selected']), 5)
        self.assertEqual(result['selected'][0]['url'], 'https://example.org/high')

    def test_all_candidates_ranked_before_any_crawl(self):
        events = []
        search = Mock()
        search.text.side_effect = [
            [{'href': 'https://unrelated.org', 'title': 'Unrelated'}],
            [{'href': 'https://relevant.org', 'title': 'Relevant'}]]
        def relevance(premise, claim):
            events.append('rank ' + premise)
            return [.01, .01, .98] if premise == 'Unrelated' else [.9, .05, .05]
        def read(url):
            events.append('crawl ' + url)
            return [], []
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=Mock(return_value=search))}), patch('app.relevance.compare_pair', side_effect=relevance), patch('app.context_scan.read_source', side_effect=read), patch('app.context_scan.classify_evidence', return_value=None):
            result = scan(ScanRequest(kind='text', text='Sebuah klaim'))
        self.assertEqual(events, ['rank Unrelated', 'rank Relevant', 'crawl https://relevant.org'])
        self.assertIsNone(result['analysis'])  # Search snippets never become evidence.

    @patch('app.context_scan.read_source')
    @patch('app.context_scan.rank_candidates', side_effect=RuntimeError('model failed'))
    def test_model_failure_does_not_crawl_unfiltered(self, rank, read):
        search = Mock()
        search.text.return_value = [{'href': 'https://example.org', 'title': 'Title'}]
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=Mock(return_value=search))}):
            result = scan(ScanRequest(kind='text', text='Klaim'))
        read.assert_not_called()
        self.assertEqual(result['selection']['status'], 'failed')
