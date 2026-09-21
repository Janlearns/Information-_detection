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
for content in ('Kesepakatan bukti nomor urut', 'ke-20', 'ke-8', '1 sumber membantah', 'Kutipan angka:'):
    assert content in window.output.text(), content
sources = [dict(source, url='https://first.org', text='Contoh Nama presiden ke-12.'),
           dict(source, url='https://second.org', text='Contoh Nama adalah presiden ke-12.'),
           dict(source, url='https://third.org', text='Laporan kegiatan tahunan.'),
           dict(source, url='https://fourth.org', text='Jadwal rapat mingguan.')]
analysis = classify_evidence('Contoh Nama presiden ke-12', sources)
window.show_result({'label': 'Sumber terkait ditemukan', 'text': 'Contoh Nama presiden ke-12',
    'reason': analysis['reason'], 'terms': [], 'sources': sources, 'limitation': '',
    'errors': [], 'analysis': analysis})
for content in ('Kesepakatan mendukung: <b>100.0%', '2 dari 4 sumber unik', '2 belum cukup/ambigu'):
    assert content in window.output.text(), content
assert '50.0%' not in window.output.text()
window.show_error('Coba ulang')
with patch('app.evidence.compare_pair', side_effect=[[.01, .98, .01], [.96, .02, .02]]):
    analysis = classify_evidence('Tanaman memerlukan cahaya. Kereta memakai diesel.', [source])
window.show_result({'label': 'Sumber terkait ditemukan', 'text': 'Teks multikalimat',
    'reason': analysis['reason'], 'terms': [], 'sources': [source], 'limitation': '',
    'errors': [], 'analysis': analysis})
for content in ('Kalimat 1', 'Kalimat 2', 'Tanaman memerlukan cahaya.', 'Kereta memakai diesel.', '98.0%', '96.0%'):
    assert content in window.output.text(), content
assert window.file_button.isEnabled()
window.close()
print('Local desktop smoke passed: idle without scanning, popup, escaped content, retry.')
