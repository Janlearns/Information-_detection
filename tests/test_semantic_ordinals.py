import unittest
from unittest.mock import patch
from app.evidence import classify_evidence
from app.ordinal_facts import parse_claim, semantic_candidates


class SemanticOrdinalTests(unittest.TestCase):
    joint = 'Aruna Putri dan Bima Surya resmi menjabat sebagai Presiden ke-12 dan Wakil Presiden ke-15 Republik Indonesia.'

    def compare(self, claim, body):
        return classify_evidence(claim, [{'url': 'https://example.org', 'text': body, 'purpose': 'Pemeriksaan fakta'}])

    @patch('app.evidence.compare_pair', return_value=[.01, .98, .01])
    def test_parallel_offices_do_not_exchange_numbers(self, model):
        for claim, expected, number in (
            ('Aruna Putri presiden ke-12', 'support', 12),
            ('Aruna Putri presiden ke-15', 'contradict', 12),
            ('Bima Surya wakil presiden ke-15', 'support', 15),
            ('Bima Surya presiden ke-12', 'unknown', None),
        ):
            with self.subTest(claim=claim):
                result = self.compare(claim, self.joint)
                self.assertEqual(result['counts'][expected], 1)
                self.assertEqual(result['observed_numbers'], [] if number is None else [number])

    @patch('app.evidence.compare_pair', return_value=[.01, .98, .01])
    def test_apposition_is_checked_with_original_sentence(self, model):
        body = 'Aruna Putri, yang sebelumnya menjabat menteri, dilantik sebagai Presiden ke-12 Republik Indonesia.'
        result = self.compare('Aruna Putri presiden ke-12', body)
        self.assertEqual(result['counts']['support'], 1)
        self.assertEqual(model.call_args.args[0], body)
        self.assertNotIn('12', model.call_args.args[1])

    @patch('app.evidence.compare_pair', side_effect=AssertionError('Must not ask NLI to invent attachment'))
    def test_meeting_negation_and_wrong_person_are_not_promoted(self, model):
        for body in ('Aruna Putri bertemu Presiden ke-12 Republik Indonesia.',
                     'Aruna Putri menghadiri pelantikan Presiden ke-12 Republik Indonesia.',
                     'Aruna Putri bukan Presiden ke-12.',
                     'Aruna Putri menyaksikan Bima Surya dilantik sebagai Presiden ke-12.',
                     'Aruna Putri dan Bima Surya menjadi Presiden ke-12.'):
            with self.subTest(body=body):
                self.assertEqual(self.compare('Aruna Putri presiden ke-12', body)['counts']['unknown'], 1)

    @patch('app.evidence.compare_pair', return_value=[.02, .70, .28])
    def test_uncertain_semantics_still_abstains(self, model):
        result = self.compare('Aruna Putri presiden ke-12', self.joint)
        self.assertEqual(result['counts']['unknown'], 1)
        self.assertFalse(result['comparisons'][0]['semantic_checks'][0]['accepted'])

    @patch('app.evidence.compare_pair', return_value=[.01, .98, .01])
    def test_conflicting_direct_and_semantic_facts_still_abstain(self, model):
        result = self.compare('Aruna Putri presiden ke-12', 'Aruna Putri presiden ke-10. ' + self.joint)
        self.assertEqual(result['counts']['unknown'], 1)
        self.assertEqual(result['observed_numbers'], [10, 12])
