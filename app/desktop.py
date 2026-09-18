"""Windows tray companion. Run with python -m app.desktop."""
import ctypes
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from html import escape

from PySide6.QtCore import Qt, QTimer, Signal, QObject, QRect
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap, QImage
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QWidget, QVBoxLayout, QLabel, QPushButton

from app.screen_check import normalize, changed, check_text


class Signals(QObject):
    result = Signal(int, object)
    failure = Signal(int, str)
    status = Signal(int, str)


class Selection(QWidget):
    selected = Signal(object)

    def __init__(self, screen):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.snapshot = screen.grabWindow(0)
        self.origin = None
        self.selection = QRect()
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(self.rect(), self.snapshot)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        if not self.selection.isNull():
            painter.save()
            painter.setClipRect(self.selection)
            painter.drawPixmap(self.rect(), self.snapshot)
            painter.restore()
            painter.setPen(QColor("#31d88b"))
            painter.drawRect(self.selection)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.origin is not None:
            self.selection = QRect(self.origin, event.position().toPoint()).normalized().intersected(self.rect())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.origin is None:
            return
        rect = QRect(self.origin, event.position().toPoint()).normalized().intersected(self.rect())
        if rect.width() >= 30 and rect.height() >= 30:
            self.selected.emit(rect)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()


class Companion:
    def __init__(self, app):
        self.app = app
        self.active = False
        self.generation = 0
        self.cancel = threading.Event()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.reader = None
        self.previous = ""
        self.last_check = 0
        self.signals = Signals()
        self.signals.result.connect(self.show_result)
        self.signals.failure.connect(self.show_failure)
        self.signals.status.connect(self.show_status)
        self.region = None
        self.selector = None
        self.manual = False
        self.tray = QSystemTrayIcon()
        self.menu = QMenu()
        self.toggle = self.menu.addAction("Aktifkan pemindaian")
        self.toggle.triggered.connect(self.toggle_active)
        self.menu.addAction("Hasil terakhir", self.show_last)
        self.menu.addSeparator()
        self.menu.addAction("Keluar", self.quit)
        self.tray.setContextMenu(self.menu)
        self.popup = QWidget(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.popup.setWindowTitle("CekFakta AI")
        self.popup.setFixedWidth(380)
        layout = QVBoxLayout(self.popup)
        self.label = QLabel("Belum ada hasil.")
        self.label.setWordWrap(True)
        self.label.setOpenExternalLinks(True)
        layout.addWidget(self.label)
        close = QPushButton("Tutup")
        close.clicked.connect(self.popup.hide)
        layout.addWidget(close)
        # Exclude our own popup from subsequent Windows screen captures.
        if sys.platform == "win32":
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.popup.winId()), 0x11)
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.popup.hide)
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.capture)
        self.panel = QWidget(None, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.panel.setWindowTitle("CekFakta - Layar")
        self.panel.setFixedWidth(340)
        panel_layout = QVBoxLayout(self.panel)
        self.status_label = QLabel("Siap - pilih area layar")
        self.status_label.setWordWrap(True)
        panel_layout.addWidget(self.status_label)
        select = QPushButton("Pilih area screenshot")
        select.clicked.connect(self.select_area)
        panel_layout.addWidget(select)
        once = QPushButton("Cek sekali")
        once.clicked.connect(self.check_once)
        panel_layout.addWidget(once)
        self.auto_button = QPushButton("Aktifkan otomatis")
        self.auto_button.clicked.connect(self.toggle_active)
        panel_layout.addWidget(self.auto_button)
        privacy = QLabel("Potongan teks dikirim untuk pencarian sumber.")
        privacy.setWordWrap(True)
        panel_layout.addWidget(privacy)
        exit_button = QPushButton("Keluar")
        exit_button.clicked.connect(self.quit)
        panel_layout.addWidget(exit_button)
        self.menu.addAction("Tampilkan kontrol", self.panel.show)
        area = self.app.primaryScreen().availableGeometry()
        self.panel.move(area.right() - 360, area.top() + 60)
        if sys.platform == "win32":
            ctypes.windll.user32.SetWindowDisplayAffinity(int(self.panel.winId()), 0x11)
        self.panel.show()
        self.update_icon()
        self.tray.show()

    def show_status(self, generation, text):
        if generation == self.generation:
            self.status_label.setText(text)

    def select_area(self):
        if self.active:
            self.toggle_active()
        self.panel.hide()
        self.popup.hide()
        QTimer.singleShot(200, self.open_selection)

    def open_selection(self):
        self.selector = Selection(self.app.primaryScreen())
        self.selector.selected.connect(self.set_region)
        self.selector.destroyed.connect(self.panel.show)
        self.selector.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.selector.show()
        self.selector.activateWindow()

    def set_region(self, rect):
        self.region = rect
        self.previous = ""
        self.status_label.setText(f"Area {rect.width()} x {rect.height()} - siap")

    def check_once(self):
        if self.future and not self.future.done():
            self.status_label.setText("Masih memproses. Tunggu sebentar.")
            return
        if self.region is None:
            self.select_area()
            return
        if not self.active:
            self.toggle_active()
        self.timer.stop()
        self.manual = True
        self.capture()

    def update_icon(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor("#16834b" if self.active else "#777777"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.setPen(QColor("white"))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "C")
        painter.end()
        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip("CekFakta AI - " + ("Aktif" if self.active else "Nonaktif"))

    def toggle_active(self):
        self.active = not self.active
        self.generation += 1
        self.cancel.set()
        self.cancel = threading.Event()
        self.previous = ""
        self.last_check = 0
        self.toggle.setText("Nonaktifkan pemindaian" if self.active else "Aktifkan pemindaian")
        self.auto_button.setText("Nonaktifkan" if self.active else "Aktifkan otomatis")
        self.status_label.setText("Memantau layar..." if self.active else "Nonaktif")
        self.manual = False
        self.update_icon()
        if self.active:
            self.timer.start()
        else:
            self.timer.stop()
            self.popup.hide()

    def capture(self):
        if not self.active or (self.future and not self.future.done()):
            return
        screen = self.app.primaryScreen()
        if not screen:
            return
        r = self.region or screen.geometry()
        pixmap = screen.grabWindow(0, r.x() if self.region else 0, r.y() if self.region else 0, r.width(), r.height())
        frame = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
        if frame.isNull():
            return
        self.status_label.setText("Membaca screenshot...")
        self.future = self.pool.submit(self.process, frame, self.generation, self.cancel, self.manual)

    def process(self, frame, generation, cancel, manual=False):
        try:
            import easyocr
            import numpy as np
            if self.reader is None:
                self.reader = easyocr.Reader(["id", "en"], gpu=False)
            if cancel.is_set():
                return
            pixels = np.frombuffer(frame.bits(), dtype=np.uint8).reshape(frame.height(), frame.bytesPerLine())
            pixels = pixels[:, :frame.width() * 3].reshape(frame.height(), frame.width(), 3).copy()
            text = normalize(" ".join(self.reader.readtext(pixels, detail=0, paragraph=True)))[:30000]
            if cancel.is_set():
                return
            if len(text) < 100:
                self.signals.status.emit(generation, "Teks kurang terbaca. Pilih area dengan teks lebih panjang.")
                return
            if not manual and (not changed(self.previous, text) or time.monotonic() - self.last_check < 20):
                self.signals.status.emit(generation, "Memantau - belum ada teks baru")
                return
            self.signals.status.emit(generation, "Mencari sumber dan menganalisis...")
            self.last_check = time.monotonic()
            result = check_text(text, cancel.is_set)
            if result and not cancel.is_set():
                self.previous = text
                self.signals.result.emit(generation, result)
        except Exception as exc:
            if not cancel.is_set():
                self.signals.failure.emit(generation, str(exc))

    def show_result(self, generation, result):
        if generation != self.generation or not self.active:
            return
        links = "<br>".join('<a href="{}">{}</a>'.format(escape(s["url"], quote=True), escape(s["title"][:100])) for s in result["sources"])
        self.label.setText("<b>" + escape(result["label"]) + "</b><p>" + escape(result["text"][:220]) + "</p><p>Indikasi model: " + escape(result["indication"]) + "</p><p>" + escape(result["reason"]) + "</p>" + (links or "Tidak ada sumber yang berhasil diambil.") + ("<p>Pencarian sebagian/gagal.</p>" if result["errors"] else ""))
        self.show_last()
        self.status_label.setText("Selesai - " + result["label"])
        self.hide_timer.start(15000)

    def show_failure(self, generation, message):
        if generation != self.generation or not self.active:
            return
        self.toggle_active()
        self.status_label.setText("Gagal: " + message[:180])
        self.tray.showMessage("Pemindaian dihentikan", message[:240])

    def show_last(self):
        self.popup.adjustSize()
        area = self.app.primaryScreen().availableGeometry()
        self.popup.move(area.right() - self.popup.width() - 16, area.bottom() - self.popup.height() - 16)
        self.popup.show()

    def quit(self):
        self.panel.hide()
        self.timer.stop()
        self.cancel.set()
        self.tray.hide()
        self.popup.hide()
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.app.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    companion = Companion(app)
    app.aboutToQuit.connect(companion.cancel.set)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
