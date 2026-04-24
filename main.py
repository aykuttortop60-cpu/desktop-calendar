"""
main.py — Masaüstü Takvim uygulaması giriş noktası
Başlatma: python main.py
"""

import sys
from datetime import date

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

import database as db
from notifier import NotificationManager
from window import CalendarWindow


def _make_icon() -> QIcon:
    """Bugünün tarihini gösteren yuvarlak tepsi ikonu üretir."""
    px = QPixmap(32, 32)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(70, 130, 235))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(1, 1, 30, 30)
    p.setPen(QColor(255, 255, 255))
    f = QFont("Segoe UI", 12)
    f.setBold(True)
    p.setFont(f)
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, str(date.today().day))
    p.end()
    return QIcon(px)


def main():
    # Yüksek DPI desteği
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Masaüstü Takvim")

    # Veritabanını başlat
    db.init_db()

    icon = _make_icon()

    # Ana pencere
    window = CalendarWindow()
    window.setWindowIcon(icon)

    # ── Sistem tepsisi ──────────────────────────────────────────────────
    tray = QSystemTrayIcon(icon, app)

    menu = QMenu()
    act_toggle = menu.addAction("📅   Takvimi Göster / Gizle")
    menu.addSeparator()
    act_quit   = menu.addAction("✕   Çıkış")

    act_toggle.triggered.connect(window.toggle_visibility)
    act_quit.triggered.connect(app.quit)

    tray.activated.connect(
        lambda reason: (
            window.toggle_visibility()
            if reason == QSystemTrayIcon.ActivationReason.Trigger
            else None
        )
    )
    tray.setContextMenu(menu)
    tray.setToolTip("Masaüstü Takvim")
    tray.show()

    # ── Bildirim yöneticisi ─────────────────────────────────────────────
    notifier = NotificationManager(tray, app)
    notifier.start_checking()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
