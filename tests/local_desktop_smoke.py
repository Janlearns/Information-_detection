import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from app.local_desktop import LocalScanner

app = QApplication([])
window = LocalScanner()
window.show()
assert not window.busy
with patch('app.local_desktop.scan') as service:
    app.processEvents()
    service.assert_not_called()
window.show_result({'label': 'Belum terverifikasi', 'text': '<script>claim</script>',
    'reason': 'Periksa sumber', 'terms': [{'term': 'fomo', 'meaning': 'takut tertinggal'}],
    'sources': [], 'limitation': '', 'errors': [],
    'analysis': {'scores': {'Hoaks': .2, 'Faktual': .5, 'Opini': .3},
                 'warning': 'Skor model, bukan probabilitas kebenaran.'}})
assert '&lt;script&gt;' in window.output.text()
assert 'fomo' in window.output.text()
for percentage in ('20.0%', '50.0%', '30.0%'):
    assert percentage in window.output.text()
from app.evidence import classify_evidence
source = {'title': 'Sumber', 'url': 'https://example.org', 'text': 'Prabowo presiden ke-8.',
          'excerpt': 'Prabowo presiden ke-8.', 'purpose': 'Pemeriksaan fakta'}
analysis = classify_evidence('Prabowo presiden ke-20', [source])
window.show_result({'label': 'Sumber terkait ditemukan', 'text': 'Prabowo presiden ke-20',
    'reason': analysis['reason'], 'terms': [], 'sources': [source], 'limitation': '',
    'errors': [], 'analysis': analysis})
for content in ('Komposisi bukti nomor urut', 'ke-20', 'ke-8', '1 sumber membantah', 'Kutipan angka:'):
    assert content in window.output.text(), content
window.show_error('Coba ulang')
assert window.file_button.isEnabled()
window.close()
print('Local desktop smoke passed: idle without scanning, popup, escaped content, retry.')
