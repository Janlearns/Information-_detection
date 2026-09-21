import unittest
import sys
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.evidence import classify_evidence, RELATIONS
from app.relevance import rank_candidates
from app.text_units import split_statements, search_units
from app.context_scan import scan


class GeneralTextTests(unittest.TestCase):
    def setUp(self):
        from app.search_session import SearchSession
        session = patch('app.context_scan.search_session', SearchSession(interval=0))
        session.start()
        self.addCleanup(session.stop)

    def source(self):
        return {'url': 'https://example.org/article', 'text': 'Dokumen sumber lengkap.',
                'purpose': 'Pemeriksaan fakta'}

    def test_sentence_boundaries_keep_decimals_titles_and_negation(self):
        self.assertEqual(split_statements('Dr. Maya mengukur 3.5 meter.\n- Benda itu tidak bergerak!'),
                         ['Dr. Maya mengukur 3.5 meter.', 'Benda itu tidak bergerak!'])

    def test_long_search_covers_end_and_reports_budget(self):
        text = ' '.join(f'Pernyataan tentang topik {i}.' for i in range(100))
        queries, total = search_units(text)
        self.assertEqual(total, 100)
        self.assertEqual(len(queries), 12)
        self.assertIn('topik 0.', queries[0])
        self.assertIn('topik 99.', queries[-1])

    @patch('app.evidence.compare_pair', side_effect=[[.02, .96, .02], [.95, .02, .03], [0., 0., 1.]])
    def test_independent_topics_preserve_different_outcomes(self, model):
        statements = ['Tanaman memerlukan cahaya.', 'Kereta itu memakai bahan bakar diesel.',
                      'Festival diselenggarakan besok.']
        result = classify_evidence(' '.join(statements), [self.source()])
        self.assertEqual([r['text'] for r in result['statements']], statements)
        self.assertEqual(result['statements'][0]['scores'][RELATIONS[1]], .96)
        self.assertEqual(result['statements'][1]['scores'][RELATIONS[0]], .95)
        self.assertEqual(result['statements'][2]['scores'][RELATIONS[2]], 1.)
        for statement in statements:
            model.assert_any_call('Dokumen sumber lengkap.', statement)

    @patch('app.evidence.compare_pair', return_value=[.1, .2, .7])
    def test_no_tail_loss_or_duplicate_weighting(self, model):
        text = 'Panel surya menghasilkan listrik. ' * 1000 + 'Jembatan ditutup untuk perbaikan.'
        result = classify_evidence(text, [self.source()])
        self.assertEqual(model.call_count, 2)
        self.assertEqual(result['statements'][-1]['text'], 'Jembatan ditutup untuk perbaikan.')
        self.assertFalse(result['truncated'])

    @patch('app.evidence.compare_pair', return_value=[.1, .8, .1])
    def test_unsupported_grammar_uses_semantics_instead_of_automatic_unknown(self, model):
        for text in ('Tokoh itu bukan presiden ke-20',
                     'Peringkat ke-3 diraih oleh tim tamu',
                     'Baterai ini bisa diisi ulang tanpa kabel',
                     'Pabrik ditutup karena kekurangan bahan baku'):
            with self.subTest(text=text):
                result = classify_evidence(text, [self.source()])
                self.assertEqual(result['method'], 'nli')
                model.assert_called_with('Dokumen sumber lengkap.', text)

    @patch('app.relevance.compare_pair', side_effect=[[.01, .01, .98], [.02, .95, .03]])
    def test_source_relevant_to_later_sentence_is_retained(self, model):
        result = rank_candidates('Tanaman memerlukan cahaya. Kereta memakai listrik.',
                                 [{'href': 'https://example.org/train', 'title': 'Transportasi rel'}])
        self.assertEqual(len(result['selected']), 1)
        self.assertAlmostEqual(result['selected'][0]['relevance'], .97)

    def test_scan_searches_multiple_topics_and_end(self):
        search = Mock()
        search.text.return_value = []
        text = 'Tanaman memerlukan cahaya. Kereta memakai listrik. Pabrik kekurangan bahan baku.'
        request = SimpleNamespace(kind='text', text=text)
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=Mock(return_value=search))}):
            result = scan(request)
        self.assertEqual(search.text.call_count, 6)
        search.text.assert_any_call('Pabrik kekurangan bahan baku.', max_results=12)
        self.assertEqual(result['search_coverage'], {'total_units': 3, 'searched_units': 3, 'limited': False})

    @patch('app.relevance.compare_pair', side_effect=[
        [.01, .98, .01], [0., 0., 1.],
        [.01, .97, .02], [0., 0., 1.],
        [0., 0., 1.], [.05, .8, .15],
    ])
    def test_source_budget_covers_different_topics(self, model):
        result = rank_candidates('Topik tanaman. Topik kereta.', [
            {'href': 'https://plants.org/a', 'title': 'Tanaman A'},
            {'href': 'https://plants2.org/a', 'title': 'Tanaman B'},
            {'href': 'https://trains.org/a', 'title': 'Kereta'},
        ], limit=2)
        self.assertEqual([item['url'] for item in result['selected']],
                         ['https://plants.org/a', 'https://trains.org/a'])
