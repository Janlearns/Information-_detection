import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.main import AnalyzeRequest, analyze, health, index

class ApiTests(unittest.TestCase):
    def test_internal_errors_do_not_expose_credentials(self):
        for failure in (RuntimeError('private-token-sentinel'), OSError('private-token-sentinel')):
            with self.subTest(failure=type(failure).__name__), patch('app.main.classify', side_effect=failure):
                with self.assertRaises(HTTPException) as ctx:
                    analyze(AnalyzeRequest(text='contoh berita ' * 20))
                self.assertNotIn('private-token-sentinel', ctx.exception.detail)

    def test_static_and_health(self):
        self.assertEqual(health()['status'], 'ok')
        self.assertTrue(index().path.is_file())

    def test_missing_or_conflicting_input(self):
        for request in [AnalyzeRequest(), AnalyzeRequest(url='https://example.com', text='x' * 100)]:
            with self.assertRaises(HTTPException) as ctx:
                analyze(request)
            self.assertEqual(ctx.exception.status_code, 422)

    @patch('app.main.classify', return_value={'label': 'Perlu verifikasi'})
    def test_text_analysis(self, classifier):
        result = analyze(AnalyzeRequest(text='contoh berita ' * 20))
        self.assertEqual(len(result['articles']), 1)
        classifier.assert_called_once()

    @patch('app.main.classify', side_effect=RuntimeError('Model belum siap'))
    def test_model_failure_releases_job_lock(self, classifier):
        for _ in range(2):
            with self.assertRaises(HTTPException) as ctx:
                analyze(AnalyzeRequest(text='contoh berita ' * 20))
            self.assertEqual(ctx.exception.status_code, 503)
