"""Manual desktop scans and Explorer file entry point."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from html import escape
import sys
from types import SimpleNamespace

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QScrollArea, QInputDialog

from app.context_scan import scan
from app.local_scan import prepare_file


def consensus_html(consensus):
    parts = ['<p><b>' + escape(consensus['status']) + '</b></p>']
    if consensus['scores'] is not None:
        for label, value in consensus['scores'].items():
            parts.append('<p>Kesepakatan ' + escape(label.lower()) + ': <b>' + f'{value * 100:.1f}%' + '</b></p>')
    parts.append('<p>' + escape(consensus['coverage']) + '</p>')
    parts.append('<p><small>' + escape(consensus['note']) + '</small></p>')
    return ''.join(parts)


class Events(QObject):
    done = Signal(object)
    failed = Signal(str)


class LocalScanner(QWidget):
    def __init__(self):
        super().__init__(None, Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle('CekFakta — Scan Lokal')
        self.resize(410, 500)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.events = Events()
        self.events.done.connect(self.show_result)
        self.events.failed.connect(self.show_error)
        self.busy = False
        layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.output = QLabel('Pilih file lokal, atau salin teks dari aplikasi lalu klik Scan teks clipboard.')
        self.output.setWordWrap(True)
        self.output.setTextFormat(Qt.TextFormat.RichText)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.output.setOpenExternalLinks(True)
        self.output.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.output)
        layout.addWidget(scroll)
        self.file_button = QPushButton('Scan file lokal…')
        self.file_button.clicked.connect(self.choose_file)
        layout.addWidget(self.file_button)
        self.clipboard_button = QPushButton('Scan teks clipboard')
        self.clipboard_button.clicked.connect(self.scan_clipboard)
        layout.addWidget(self.clipboard_button)
        close = QPushButton('Tutup')
        close.clicked.connect(self.close)
        layout.addWidget(close)
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 20, area.bottom() - self.height() - 20)

    def set_busy(self, value):
        self.busy = value
        self.file_button.setEnabled(not value)
        self.clipboard_button.setEnabled(not value)

    def submit(self, prepare):
        if self.busy:
            return
        self.set_busy(True)
        self.output.setText('Membaca pilihan dan mencari sumber…<br>Proses pertama dapat memerlukan unduhan model OCR.')
        def work():
            try:
                self.events.done.emit(scan(prepare()))
            except Exception as exc:
                self.events.failed.emit(str(exc))
        self.pool.submit(work)

    def scan_file(self, path, seconds=0):
        self.submit(lambda: prepare_file(path, seconds))

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Pilih file untuk Scan', '',
            'File yang didukung (*.txt *.md *.srt *.vtt *.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.mp4 *.mkv *.webm *.mov *.avi *.m4v)')
        if path:
            from pathlib import Path
            from app.local_scan import VIDEO_TYPES
            seconds = 0
            if Path(path).suffix.lower() in VIDEO_TYPES:
                seconds, ok = QInputDialog.getDouble(self, 'Posisi video', 'Ambil frame pada detik:', 0, 0, 86400, 1)
                if not ok:
                    return
            self.scan_file(path, seconds)

    def scan_clipboard(self):
        text = QApplication.clipboard().text()
        if not text.strip() or len(text) > 30000:
            self.show_error('Salin teks yang ingin diperiksa terlebih dahulu (maksimal 30.000 karakter).')
            return
        self.submit(lambda: SimpleNamespace(kind='text', text=text, frame='', media_note=''))

    def show_error(self, message):
        self.set_busy(False)
        self.output.setText('<b>Scan belum berhasil</b><p>' + escape(message) + '</p>')

    def show_result(self, result):
        self.set_busy(False)
        parts = ['<h3>' + escape(result['label']) + '</h3>', '<p>' + escape(result['text']) + '</p>', '<p>' + escape(result['reason']) + '</p>']
        analysis = result.get('analysis')
        classification = ['<h3>' + escape((analysis or {}).get('label', 'Persentase hubungan bukti')) + '</h3>']
        if analysis and analysis.get('summary'):
            classification.append('<p>' + escape(analysis['summary']) + '</p>')
        if analysis and analysis.get('consensus'):
            classification.append(consensus_html(analysis['consensus']))
        elif analysis and analysis.get('scores'):
            for label, value in analysis['scores'].items():
                classification.append('<p>' + escape(label) + ': <b>' + f'{value * 100:.1f}%' + '</b></p>')
            classification.append('<p><small>' + escape(analysis['warning']) + '</small></p>')
            if analysis.get('truncated'):
                classification.append('<p>Teks panjang: persentase hanya mencakup bagian teks yang dianalisis model.</p>')
        else:
            classification.append('<p>' + escape(result.get('analysis_error') or 'Persentase hubungan bukti belum tersedia.') + '</p>')
        parts = classification + parts
        for index, statement in enumerate((analysis or {}).get('statements', []), 1):
            parts.append('<h3>Kalimat ' + str(index) + '</h3><p>' + escape(statement['text']) + '</p>')
            if statement.get('consensus'):
                parts.append(consensus_html(statement['consensus']))
            else:
                parts.append('<p>' + '<br>'.join(escape(label) + f': {value * 100:.1f}%'
                             for label, value in statement['scores'].items()) + '</p>')
            for item in statement.get('comparisons', []):
                parts.append('<p><a href="' + escape(item['url'], quote=True) + '">Sumber</a>: ' +
                             escape(item.get('explanation') or 'Perbandingan semantik dengan kalimat ini.') + '<br>' +
                             '<br>'.join(escape(label) + f': {value * 100:.1f}%'
                                         for label, value in item['scores'].items()) + '</p>')
        selection = result.get('selection', {})
        if selection.get('status') == 'done':
            parts.append('<p><small>Website disaring terlebih dahulu oleh transformer melalui judul dan ringkasan pencarian. Ringkasan tidak dipakai sebagai bukti.</small></p>')
        for term in result['terms']:
            parts.append('<p><b>' + escape(term['term']) + '</b>: ' + escape(term['meaning']) + '</p>')
        parts.append('<h3>Sumber &amp; kutipan</h3>')
        for source in result['sources']:
            if source['url'].startswith(('https://', 'http://')):
                parts.append('<p><a href="' + escape(source['url'], quote=True) + '">' + escape(source['title']) + '</a><br>' + escape(source['excerpt']) + '</p>')
                comparison = next((item for item in (analysis or {}).get('comparisons', []) if item['url'] == source['url']), None)
                if comparison:
                    if comparison.get('explanation'):
                        parts.append('<p><b>' + escape(comparison['explanation']) + '</b></p>')
                    for fact in comparison.get('facts', []):
                        parts.append('<p>Kutipan angka: ' + escape(fact['quote']) + '</p>')
                    parts.append('<p><small>Selesai dianalisis: ' + str(comparison.get('characters_analyzed', source.get('characters_read', 0))) + ' karakter teks artikel.</small></p>')
                    parts.append('<p><small>' + '<br>'.join(escape(label) + f': {value * 100:.1f}%' for label, value in comparison['scores'].items()) + '</small></p>')
        if not result['sources']:
            parts.append('<p>Belum ada sumber yang berhasil dibaca.</p>')
        if result['limitation']:
            parts.append('<p>' + escape(result['limitation']) + '</p>')
        if result['errors']:
            parts.append('<h3>Catatan pencarian dan akses</h3>')
            parts.extend('<p><small>' + escape(error) + '</small></p>' for error in result['errors'])
        self.output.setToolTip('\n'.join(result['errors']))
        self.output.setText(''.join(parts))

    def closeEvent(self, event):
        self.pool.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file')
    parser.add_argument('--seconds', type=float, default=0)
    args = parser.parse_args()
    app = QApplication(sys.argv)
    window = LocalScanner()
    window.show()
    if args.file:
        window.scan_file(args.file, args.seconds)
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
