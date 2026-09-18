import unittest
from unittest.mock import patch, Mock
from app.classifier import classify, LABELS
from app.crawler import validate_url, fetch

class CoreTests(unittest.TestCase):
    def test_all_scores_without_verdict(self):
        model = Mock()
        model.tokenizer.encode.return_value = [1, 2]
        model.tokenizer.decode.return_value = 'contoh teks'
        for values in ([.8, .1, .1], [.1, .8, .1], [.1, .1, .8]):
            model.return_value = [{'labels': LABELS, 'scores': values}]
            with patch('app.classifier._pipeline', model):
                result = classify('contoh teks')
            self.assertEqual(result['label'], 'Persentase klasifikasi')
            self.assertEqual(result['scores'], dict(zip(LABELS, values)))
            self.assertAlmostEqual(sum(result['scores'].values()), 1)

    def test_reject_unsafe_urls(self):
        for url in ['file:///etc/passwd', 'http://user:pass@example.com', 'https://example.com:8000']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_url(url)

    @patch('app.crawler.socket.getaddrinfo')
    def test_reject_private_dns(self, dns):
        for address in ['127.0.0.1', '10.0.0.1', '169.254.169.254', '::1']:
            dns.return_value = [(2, 1, 6, '', (address, 80))]
            with self.subTest(address=address), self.assertRaises(ValueError):
                validate_url('http://example.com')

    @patch('app.crawler.validate_url')
    def test_robots_denial_prevents_connection(self, validate):
        with self.assertRaises(ValueError):
            fetch('https://example.com/private', lambda _: False)
        validate.assert_not_called()

if __name__ == '__main__':
    unittest.main()
