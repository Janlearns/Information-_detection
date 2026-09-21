import unittest
from unittest.mock import patch
from app.evidence import classify_evidence, RELATIONS, summarize_decisive_evidence
from app.context_scan import related_excerpt


class EvidenceTests(unittest.TestCase):
    def test_agreement_and_coverage_have_different_denominators(self):
        result = summarize_decisive_evidence({'support': 2, 'contradict': 0, 'unknown': 2})
        self.assertEqual(result['scores'], {'Mendukung': 1., 'Membantah': 0.})
        self.assertEqual(result['decisive_sources'], 2)
        self.assertEqual(result['total_sources'], 4)
        self.assertIn('2 dari 4', result['coverage'])

    def test_five_sources_do_not_force_agreement(self):
        for support, contradict, unknown, expected in (
            (5, 0, 0, 1.), (4, 1, 0, .8), (1, 1, 3, .5), (0, 5, 0, 0.),
        ):
            with self.subTest(support=support, contradict=contradict):
                result = summarize_decisive_evidence(dict(support=support, contradict=contradict, unknown=unknown))
                self.assertEqual(result['scores']['Mendukung'], expected)
                self.assertEqual(result['total_sources'], 5)
                if support and contradict:
                    self.assertEqual(result['status'], 'Bukti saling bertentangan')

    def test_no_decisive_evidence_has_no_agreement_percentage(self):
        for unknown in (0, 5):
            result = summarize_decisive_evidence(dict(support=0, contradict=0, unknown=unknown))
            self.assertIsNone(result['scores'])
            self.assertEqual(result['status'], 'Belum cukup bukti')

    def test_consensus_uses_deduplicated_evidence_not_five_slot_target(self):
        result = classify_evidence('Contoh Nama presiden ke-12', [
            self.source('https://example.org/a', 'Contoh Nama presiden ke-12.'),
            self.source('https://copy.org/a', 'Contoh Nama presiden ke-12.'),
            self.source('https://www.example.org/b', 'Contoh Nama adalah presiden ke-12.'),
            self.source('https://other.org/a', 'Laporan kegiatan tahunan.'),
        ])
        self.assertEqual(result['consensus']['total_sources'], 2)
        self.assertEqual(result['consensus']['decisive_sources'], 1)
        self.assertEqual(result['consensus']['scores']['Mendukung'], 1.)
        # Retain raw distribution for audit and existing API consumers.
        self.assertEqual(result['scores'][RELATIONS[1]], .5)

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
