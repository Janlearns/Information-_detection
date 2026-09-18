import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from fastapi import HTTPException
from app.main import ScanRequest, context_scan
from app.context_scan import scan, term_candidates


class ContextTests(unittest.TestCase):
    def setUp(self):
        relevance = patch('app.relevance.compare_pair', return_value=[.8, .1, .1])
        relevance.start()
        self.addCleanup(relevance.stop)
        classifier = patch('app.context_scan.classify_evidence', return_value={
            'label': 'Persentase klasifikasi',
            'scores': {'hoaks': .2, 'faktual': .5, 'opini': .3},
            'warning': 'Skor model, bukan probabilitas kebenaran.',
            'reason': 'Klaim dibandingkan dengan kutipan.',
        })
        self.classifier = classifier.start()
        self.addCleanup(classifier.stop)

    def test_classification_survives_search_failure(self):
        search = Mock(side_effect=RuntimeError('offline'))
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}):
            result = scan(ScanRequest(kind='text', text='Klaim untuk diperiksa'))
        self.classifier.assert_called_once_with('Klaim untuk diperiksa', [])
        self.assertEqual(len(result['analysis']['scores']), 3)
        self.assertEqual(result['analysis_error'], '')

    def test_model_failure_is_explicit_without_fake_scores(self):
        self.classifier.side_effect = RuntimeError('model unavailable')
        search = Mock()
        search.return_value.text.return_value = []
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}):
            result = scan(ScanRequest(kind='text', text='Klaim untuk diperiksa'))
        self.assertIsNone(result['analysis'])
        self.assertIn('gagal dijalankan', result['analysis_error'])

    def test_short_claim_is_not_a_term(self):
        self.assertEqual(term_candidates('Prabowo merupakan presiden ke 9'), [])

    def test_fallback_and_complete_output(self):
        search = Mock()
        search.return_value.text.side_effect = [
            [{'title': 'Artikel terkait', 'href': 'https://blocked.example/blocked'}],
            [{'title': 'Artikel terkait', 'href': 'https://example.com/readable'}],
        ]
        paragraph = 'Klaim diperiksa. ' + ('Penjelasan lengkap sumber. ' * 50) + 'Kalimat penutup.'
        article = {'title': 'Sumber', 'url': 'https://example.com/readable', 'text': paragraph}
        selected = 'Teks klaim yang panjang untuk diperiksa. ' * 60
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}), patch(
            'app.context_scan.crawl', side_effect=[([], [{'error': 'Dilarang oleh robots.txt.'}]), ([article], [])]
        ):
            result = scan(ScanRequest(kind='text', text=selected))
        self.assertEqual(result['sources'][0]['excerpt'], paragraph)
        self.assertEqual(result['text'], selected.strip())
        self.assertEqual(search.return_value.text.call_count, 2)

    def test_transient_timeout_is_retried(self):
        from app.context_scan import read_source
        article = {'text': 'Artikel utuh'}
        with patch('app.context_scan.crawl', side_effect=[TimeoutError('timed out'), ([article], [])]) as crawler:
            self.assertEqual(read_source('https://example.com'), ([article], []))
        self.assertEqual(crawler.call_count, 2)

    def test_empty_selection_rejected(self):
        with self.assertRaises(HTTPException) as error:
            context_scan(ScanRequest(kind='text', text=' '))
        self.assertEqual(error.exception.status_code, 422)

    @patch('app.main.scan', side_effect=RuntimeError('failed'))
    def test_failure_releases_lock(self, service):
        for _ in range(2):
            with self.assertRaises(RuntimeError):
                context_scan(ScanRequest(kind='text', text='fomo'))

    def test_terms_evidence_and_no_false_verdict(self):
        search = Mock()
        search.return_value.text.return_value = [{'title': 'Artikel terkait', 'href': 'https://example.com/news'}]
        article = {'title': 'Sumber', 'url': 'https://example.com/news', 'text': 'Pembukaan. FOMO berarti takut tertinggal.'}
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}), patch('app.context_scan.crawl', return_value=([article], [])):
            result = scan(ScanRequest(kind='text', text='fomo'))
        self.assertEqual(result['terms'][0]['term'], 'fomo')
        self.assertIn('FOMO', result['sources'][0]['excerpt'])
        self.assertEqual(result['label'], 'Sumber terkait ditemukan')
        self.assertEqual(result['verification_status'], 'evidence_compared')

    def test_scientific_terms_and_markdown_links(self):
        text = '[*Haikouichthys*](https://id.wikipedia.org/wiki/Haikouichthys) memiliki notokorda saat ledakan Kambrium.'
        self.assertEqual(set(term_candidates(text)), {'Haikouichthys', 'notokorda', 'ledakan Kambrium'})
        self.assertEqual(term_candidates('Ini adalah kalimat biasa yang dibaca manusia.'), [])
        self.assertEqual(term_candidates('Istilah fotosintesis dalam artikel ini dijelaskan secara rinci.', ['fotosintesis', 'tidak ada']), ['fotosintesis'])

    def test_definition_requires_readable_source_not_search_snippet(self):
        search = Mock()
        search.return_value.text.return_value = [{'title': 'Artikel terkait', 'href': 'https://example.com/term', 'body': 'notokorda adalah klaim snippet'}]
        article = {'title': 'Istilah', 'url': 'https://example.com/term', 'text': 'Notokorda adalah struktur penunjang tubuh.'}
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}), patch('app.context_scan.crawl', return_value=([article], [])):
            result = scan(ScanRequest(kind='text', text='notokorda'))
        self.assertIn('struktur penunjang', result['terms'][0]['meaning'])
        self.assertNotIn('snippet', result['terms'][0]['meaning'])
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}), patch('app.context_scan.crawl', side_effect=ValueError('robots.txt gagal')):
            result = scan(ScanRequest(kind='text', text='notokorda'))
        self.assertEqual(result['label'], 'Bukti belum tersedia')
        self.assertIn('belum ditemukan', result['terms'][0]['meaning'])

    def test_media_without_text_does_not_invent_search(self):
        search = Mock()
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}):
            result = scan(ScanRequest(kind='video', media_note='Browser membatasi media'))
        search.assert_not_called()
        self.assertTrue(result['errors'])
        self.assertIn('frame', result['limitation'])

    def test_ocr_used_for_media_query(self):
        search = Mock()
        search.return_value.text.return_value = []
        with patch.dict(sys.modules, {'ddgs': SimpleNamespace(DDGS=search)}), patch('app.context_scan.read_frame', return_value='klaim dari foto') as ocr:
            result = scan(ScanRequest(kind='image', frame='image-data'))
        ocr.assert_called_once_with('image-data')
        self.assertIn('klaim dari foto', search.return_value.text.call_args.args[0])
        self.assertEqual(result['text'], 'klaim dari foto')
