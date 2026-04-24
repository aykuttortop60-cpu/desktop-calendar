"""
notifier.py — Arka plan bildirim zamanlayıcısı
Her dakika veritabanını kontrol eder; zamanı gelen notlar için
sistem tepsisi bildirimi gönderir.
"""

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QSystemTrayIcon
import database as db


class NotificationManager(QObject):
    def __init__(self, tray_icon: QSystemTrayIcon, parent=None):
        super().__init__(parent)
        self.tray = tray_icon
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)

    def start_checking(self):
        self._timer.start(60_000)   # Her 60 saniyede bir
        self._check()               # Başlangıçta da kontrol et

    def _check(self):
        try:
            for note in db.get_pending_notifications():
                self.tray.showMessage(
                    "📅 Takvim Hatırlatıcı",
                    f"⏰ {note['due_time']}  —  {note['title']}",
                    QSystemTrayIcon.MessageIcon.Information,
                    6000,
                )
                db.mark_notified(note["id"])
        except Exception:
            pass  # Arka plan görevinde sessizce hata yönet
