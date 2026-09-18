"""Run separately after installing requirements-desktop.txt."""
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.desktop import Companion, Selection
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

app = QApplication([])
companion = Companion(app)
assert not companion.active
assert companion.panel.isVisible()
selection = Selection(app.primaryScreen())
selection.selected.connect(companion.set_region)
selection.show()
QTest.mousePress(selection, Qt.MouseButton.LeftButton, pos=QPoint(40, 40))
QTest.mouseMove(selection, QPoint(300, 180))
QTest.mouseRelease(selection, Qt.MouseButton.LeftButton, pos=QPoint(300, 180))
assert companion.region.width() == 261
assert companion.region.height() == 141
companion.toggle_active()
generation = companion.generation
assert companion.timer.isActive()
companion.show_result(generation, {"label": "Belum terverifikasi", "text": "Contoh berita", "indication": "Perlu verifikasi", "reason": "Bukti belum cukup", "sources": [], "errors": []})
assert companion.popup.isVisible()
companion.toggle_active()
assert not companion.timer.isActive()
assert not companion.popup.isVisible()
companion.show_result(generation, {})
assert not companion.popup.isVisible()
companion.quit()
print("Desktop smoke passed: toggle, popup, stale-result rejection.")
