import unittest
from unittest.mock import patch
from app.evidence import classify_evidence, RELATIONS
from app.context_scan import related_excerpt


class EvidenceTests(unittest.TestCase):
    def source(self, url='https://example.com/a', excerpt='Prabowo adalah presiden ke-8.'):
        return {'url': url, 'excerpt': excerpt, 'purpose': 'Pemeriksaan fakta'}

    @patch('app.evidence.compare_pair')
    def test_no_evidence_no_percentage(self, compare):
        self.assertIsNone(classify_evidence('Klaim', []))
        self.assertIsNone(classify_evidence('Klaim', [dict(self.source(), purpose='Makna istilah')]))
        compare.assert_not_called()

    @patch('app.evidence.compare_pair', return_value=[.97, .02, .01])
    def test_passes_claim_and_evidence_and_deduplicates(self, compare):
        source = self.source()
        result = classify_evidence('Prabowo menjabat presiden', [source, self.source('https://example.com/b'), self.source('https://copy.org/a')])
        compare.assert_called_once_with(source['excerpt'], 'Prabowo menjabat presiden')
        self.assertEqual(result['scores'][RELATIONS[0]], .97)
        self.assertEqual(len(result['comparisons']), 1)

    @patch('app.evidence.compare_pair', side_effect=[[.9, .05, .05], [.05, .9, .05]])
    def test_conflicting_evidence_is_preserved(self, compare):
        result = classify_evidence('Klaim', [self.source(), self.source('https://other.org/a', 'Kutipan berbeda')])
        self.assertAlmostEqual(result['scores'][RELATIONS[0]], .475)
        self.assertAlmostEqual(result['scores'][RELATIONS[1]], .475)

    def test_ordinal_passage_beats_incidental_biography(self):
        body = 'Prabowo merupakan calon presiden dalam pemilu.\nPrabowo Subianto adalah Presiden ke-8 Republik Indonesia.'
        self.assertIn('ke-8', related_excerpt(body, 'Prabowo merupakan presiden ke 10'))
