import unittest
from unittest.mock import patch
from app.ordinal_facts import parse_claim, compare_ordinal
from app.evidence import classify_evidence, aggregate_passages, RELATIONS
from app.relevance import rank_candidates


class OrdinalTests(unittest.TestCase):
    @patch('app.evidence.compare_pair', side_effect=AssertionError('Numbers must remain exact'))
    def test_screenshot_wording_and_paraphrases(self, nli):
        evidence = self.source('Prabowo Subianto merupakan Presiden Republik Indonesia ke-8.')
        for name in ('Prabowo', 'Prabowo subianto', 'Pa prabowo subianto', 'Pak Prabowo', 'Bapak Prabowo'):
            for prefix in ('', '- ', '* ', '\u2022 '):
                for number in (8, 10):
                    claim = f'{prefix}{name} merupakan presiden ke-{number}'
                    with self.subTest(claim=claim):
                        result = classify_evidence(claim, [evidence])
                        self.assertIsNotNone(result['claim_fact'])
                        self.assertEqual(result['counts']['support' if number == 8 else 'contradict'], 1)

    def test_equivalent_office_phrasing(self):
        for claim in ('Pak Prabowo ialah presiden RI kedelapan.',
                      'Presiden Indonesia ke-8 adalah Prabowo',
                      'Prabowo terpilih sebagai presiden ke\u20118 Indonesia'):
            for body in ('Prabowo Subianto ialah Presiden Republik Indonesia ke-8.',
                         'Presiden Indonesia kedelapan adalah Prabowo Subianto.',
                         'Prabowo Subianto terpilih sebagai Presiden RI ke\u20138.'):
                with self.subTest(claim=claim, body=body):
                    self.assertEqual(compare_ordinal(body, parse_claim(claim))['relation'], 'support')

    def test_normalization_does_not_remove_uncertainty_or_merge_claims(self):
        for claim in ('- Pak Prabowo bukan presiden ke-8',
                      '- Prabowo presiden ke-8\n- Gibran presiden ke-10',
                      'Benarkah Pak Prabowo presiden ke-8?',
                      'Presiden ke-8 adalah Prabowo atau Joko Widodo'):
            with self.subTest(claim=claim):
                self.assertIsNone(parse_claim(claim))

    def source(self, body, url='https://example.org/article'):
        return {'url': url, 'text': body, 'excerpt': body, 'purpose': 'Pemeriksaan fakta'}

    def test_correct_and_wrong_numbers_are_compared_exactly(self):
        source = 'Prabowo Subianto resmi menjabat sebagai Presiden ke-8 Republik Indonesia setelah dilantik pada 20 Oktober 2024.'
        for value in (1, 7, 8, 9, 10, 20, 80, 100):
            with self.subTest(value=value):
                result = compare_ordinal(source, parse_claim(f'Prabowo merupakan presiden ke {value}'))
                self.assertEqual(result['relation'], 'support' if value == 8 else 'contradict')
                self.assertEqual(result['observed_numbers'], [8])

    def test_number_is_not_hardcoded_to_eight_or_prabowo(self):
        result = compare_ordinal('Contoh Nama adalah presiden ke-12.', parse_claim('Contoh Nama merupakan presiden ke-8'))
        self.assertEqual(result['observed_numbers'], [12])
        self.assertEqual(result['relation'], 'contradict')
        result = compare_ordinal('Prabowo merupakan presiden ke-20.', parse_claim('Prabowo presiden ke-20'))
        self.assertEqual(result['relation'], 'support')

    def test_word_numbers_and_heading_order(self):
        for body in ('Prabowo Subianto merupakan Presiden kedelapan Republik Indonesia.',
                     'Presiden Ke-8 Republik Indonesia: Prabowo Subianto',
                     'Prabowo Subianto Presiden Republik Indonesia ke-8',
                     'Prabowo merupakan presiden ke delapan.'):
            with self.subTest(body=body):
                result = compare_ordinal(body, parse_claim('Prabowo merupakan presiden kedua puluh'))
                self.assertEqual(result['relation'], 'contradict')

    def test_published_perpusnas_sentence(self):
        # https://dev-kepustakaanpresiden.perpusnas.go.id/presiden/prabowo-subianto/biografi
        quote = 'Prabowo Subianto merupakan Presiden Republik Indonesia ke-8 untuk masa jabatan 2024-2029.'
        result = compare_ordinal(quote, parse_claim('Prabowo merupakan presiden ke 20'))
        self.assertEqual(result['relation'], 'contradict')
        self.assertEqual(result['observed_numbers'], [8])

    def test_unrelated_numbers_entities_roles_and_uncertain_text_abstain(self):
        claim = parse_claim('Prabowo presiden ke-20')
        examples = [
            'Prabowo dilantik sebagai presiden pada 20 Oktober 2024.',
            'Prabowo memimpin sidang kabinet ke-8.',
            'Joko Widodo merupakan presiden ke-7.',
            'Gibran merupakan wakil presiden ke-14.',
            'Prabowo bertemu Presiden ke-8 Republik Indonesia.',
            'Angga Raka Prabowo merupakan presiden ke-20.',
            'Prabowo adalah wakil presiden ke-20.',
            'Benarkah Prabowo merupakan presiden ke-20?',
            'Prabowo bukan presiden ke-20.',
            'Hoaks: Prabowo merupakan presiden ke-20.',
            'Jika Prabowo merupakan presiden ke-20, apa yang terjadi?',
            'Prabowo akan menjadi presiden ke-20.',
            'Prabowo dan Gibran merupakan Presiden ke-8 dan Wakil Presiden ke-14.',
        ]
        for body in examples:
            with self.subTest(body=body):
                self.assertEqual(compare_ordinal(body, claim)['relation'], 'unknown')

    def test_explicit_country_must_match(self):
        claim = parse_claim('Prabowo presiden Indonesia ke-20')
        for body in ('Prabowo presiden Amerika Serikat ke-8.', 'Prabowo presiden ke-8.'):
            self.assertEqual(compare_ordinal(body, claim)['relation'], 'unknown')

    def test_contradiction_within_one_source_abstains(self):
        result = compare_ordinal('Prabowo presiden ke-8. Prabowo presiden ke-20.', parse_claim('Prabowo presiden ke-20'))
        self.assertEqual(result['relation'], 'unknown')
        self.assertEqual(result['observed_numbers'], [8, 20])

    @patch('app.evidence.compare_pair', side_effect=AssertionError('NLI must not override explicit numbers'))
    def test_proportions_include_unknown_sources(self, nli):
        result = classify_evidence('Prabowo merupakan presiden ke 20', [
            self.source('Prabowo presiden ke-8.'),
            self.source('Prabowo dilantik pada 20 Oktober.', 'https://other.org/a'),
        ])
        self.assertEqual(result['counts'], {'contradict': 1, 'support': 0, 'unknown': 1})
        self.assertEqual(result['scores'], dict(zip(RELATIONS, [.5, 0., .5])))
        self.assertIn('ke-20', result['summary'])
        self.assertIn('ke-8', result['comparisons'][0]['facts'][0]['quote'])

    @patch('app.evidence.compare_pair', side_effect=AssertionError('No invented numerical inference'))
    def test_no_explicit_numbers_abstains(self, nli):
        for claim in ('Prabowo presiden ke-20',):
            result = classify_evidence(claim, [self.source('Prabowo merupakan presiden ke-8.' if 'dan' in claim else 'Prabowo dilantik pada 20 Oktober.')])
            self.assertEqual(result['counts']['unknown'], 1)
            self.assertEqual(result['scores'][RELATIONS[1]], 0)

    def test_tail_proof_is_found_despite_unrelated_narrative(self):
        body = 'Prabowo berpidato dalam acara yang dihadiri 20 orang. ' * 1000 + 'Prabowo Subianto merupakan presiden ke-8.'
        result = classify_evidence('Prabowo presiden ke-20', [self.source(body)])
        self.assertEqual(result['counts']['contradict'], 1)
        self.assertEqual(result['comparisons'][0]['characters_analyzed'], len(body))

    def test_different_sources_can_really_disagree(self):
        result = classify_evidence('Prabowo presiden ke-20', [self.source('Prabowo presiden ke-8.'), self.source('Prabowo presiden ke-20.', 'https://other.org')])
        self.assertEqual(result['counts'], {'contradict': 1, 'support': 1, 'unknown': 0})
        self.assertEqual(result['scores'][RELATIONS[0]], .5)
        self.assertEqual(result['scores'][RELATIONS[1]], .5)

    def test_no_mixing_extrema_from_different_sentences(self):
        scores = aggregate_passages([[.9, .05, .05], [.1, .6, .3]])
        self.assertAlmostEqual(scores[0], (.9 * .95 + .1 * .7) / 1.65)
        self.assertAlmostEqual(sum(scores), 1.)

    @patch('app.relevance.compare_pair', side_effect=AssertionError('Direct numeric metadata suffices'))
    def test_retrieval_keeps_disagreeing_numbers(self, nli):
        result = rank_candidates('Prabowo presiden ke-20', [{'href': 'https://example.org', 'title': 'Prabowo Subianto Presiden ke-8 Republik Indonesia'}])
        self.assertEqual(len(result['selected']), 1)
        self.assertTrue(result['selected'][0]['explicit_ordinal'])
