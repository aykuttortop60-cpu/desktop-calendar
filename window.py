"""
window.py — Ana takvim penceresi
• Şeffaf / frameless / sürüklenebilir widget
• Açılır/kapanır (compact ↔ full mod)
• Gün hücreleri: not sayısı kadar renkli nokta
• Not paneli: seçili güne ait notları listeler
"""

import calendar
import os
import sys
import winreg
from datetime import date, datetime

from PyQt6.QtCore import Qt, QDate, QRectF, pyqtSignal, QSettings
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QPainter, QPainterPath, QPen,
)
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

import database as db
from dialogs import NoteDialog


# ── Otomatik başlangıç yardımcıları (Registry) ───────────────────────────────
_REG_KEY  = r"Software\Microsoft\Windows\CurrentVersion\Run"
_REG_NAME = "MasaustuTakvim"


def _autostart_enabled() -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                             winreg.KEY_QUERY_VALUE)
        winreg.QueryValueEx(key, _REG_NAME)
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


def _set_autostart(enabled: bool) -> None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _REG_KEY, 0,
                             winreg.KEY_SET_VALUE)
        if enabled:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            venv_py = os.path.join(script_dir, ".venv", "Scripts", "pythonw.exe")
            if not os.path.exists(venv_py):
                venv_py = sys.executable
            main_py = os.path.join(script_dir, "main.py")
            cmd = f'"{venv_py}" "{main_py}"'
            winreg.SetValueEx(key, _REG_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, _REG_NAME)
            except OSError:
                pass
        winreg.CloseKey(key)
    except OSError:
        pass

# ── Türkçe ay / gün adları ────────────────────────────────────────────────
DAYS_TR   = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
MONTHS_TR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
             "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# ── Tema renk paleti ──────────────────────────────────────────────────────
THEMES = {
    "Mavi":   {"accent": (90,  145, 255), "bg": (11, 14, 28),  "sel": (110, 170, 255)},
    "Bordo":  {"accent": (155, 45,  80),  "bg": (22,  8, 14),  "sel": (185, 65,  95)},
    "Gri":    {"accent": (130, 140, 160), "bg": (18, 20, 26),  "sel": (150, 160, 180)},
    "Yeşil":  {"accent": (55,  145, 95),  "bg": (8,  20, 14),  "sel": (75,  170, 115)},
    "Turuncu":{"accent": (220, 130, 40),  "bg": (20, 14,  8),  "sel": (240, 155, 65)},
}
_THEME = dict(THEMES["Mavi"])   # aktif tema — tüm widget'lar bu sözlüğü okur


# ═══════════════════════════════════════════════════════════════════════════
class DayButton(QPushButton):
    """Tek bir takvim günü — gün numarası + not noktaları özel çizim."""

    def __init__(self, day: int, note_count: int = 0,
                 is_today: bool = False, is_overdue: bool = False):
        super().__init__()
        self.day         = day
        self.note_count  = note_count
        self.is_today    = is_today
        self.is_overdue  = is_overdue
        self.is_selected = False

        self.setFixedSize(62, 70)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

    def set_selected(self, val: bool):
        if self.is_selected != val:
            self.is_selected = val
            self.update()

    # ── custom paint ───────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        a      = _THEME["accent"]
        s      = _THEME["sel"]
        CELL_H = h - 14     # alt kısım noktalar için ayrıldı

        # arka plan rengi
        if self.is_selected:
            bg     = QColor(*s, 90)
            border = QColor(*s, 210)
        elif self.is_today:
            bg     = QColor(*a, 115)
            border = QColor(*a, 240)
        elif self.is_overdue:
            bg     = QColor(220, 60, 60, 28)
            border = QColor(255, 100, 100, 110)
        else:
            bg     = QColor(255, 255, 255, 10)
            border = QColor(255, 255, 255, 18)

        cell = QPainterPath()
        cell.addRoundedRect(QRectF(2, 2, w - 4, CELL_H), 8, 8)
        p.fillPath(cell, QBrush(bg))
        p.setPen(QPen(border, 1.0))
        p.drawPath(cell)

        # gün numarası
        if self.is_today:
            text_color = QColor(255, 255, 255)
        elif self.is_overdue and not self.is_selected:
            text_color = QColor(255, 150, 150, 230)
        else:
            text_color = QColor(255, 255, 255, 210)

        font = QFont("Segoe UI", 16)
        font.setBold(self.is_today)
        p.setFont(font)
        p.setPen(text_color)
        p.drawText(2, 2, w - 4, CELL_H, Qt.AlignmentFlag.AlignCenter, str(self.day))

        # not noktaları — hücrenin ALTINDA
        if self.note_count > 0:
            n_dots  = min(self.note_count, 5)
            dot_d   = 5
            spacing = 8
            total_w = n_dots * dot_d + (n_dots - 1) * (spacing - dot_d)
            start_x = (w - total_w) // 2
            dot_y   = h - 9     # hücre bitişinden 3 px aşağı

            dot_color = (QColor(255, 100, 100, 240)
                         if self.is_overdue
                         else QColor(*a, 230))
            p.setBrush(QBrush(dot_color))
            p.setPen(Qt.PenStyle.NoPen)
            for i in range(n_dots):
                p.drawEllipse(start_x + i * spacing, dot_y, dot_d, dot_d)

            if self.note_count > 5:
                p.setPen(QColor(255, 255, 255, 140))
                tiny = QFont("Segoe UI", 7)
                p.setFont(tiny)
                p.drawText(w - 12, dot_y - 1, 11, 8,
                           Qt.AlignmentFlag.AlignCenter, "+")
        p.end()


# ═══════════════════════════════════════════════════════════════════════════
class NoteItem(QFrame):
    """Bir not satırı widget'ı — düzenle / sil / tamamla."""

    edit_requested   = pyqtSignal(int)
    delete_requested = pyqtSignal(int)
    toggle_requested = pyqtSignal(int)

    def __init__(self, note):
        super().__init__()
        self.note_id   = note["id"]
        self.completed = bool(note["completed"])

        today  = date.today().isoformat()
        now_t  = datetime.now().strftime("%H:%M")
        self.overdue = (
            not self.completed and (
                note["date"] < today or
                (note["date"] == today
                 and note["due_time"]
                 and note["due_time"] < now_t)
            )
        )
        self._build(note)

    def _build(self, note):
        if self.completed:
            # ✔ Tamamlandı — yeşil
            self.setStyleSheet(
                "QFrame{background:rgba(30,110,55,38);"
                "border:1px solid rgba(80,200,110,90);"
                "border-radius:7px;}"
            )
        elif self.overdue:
            # ✘ Geçmiş & tamamlanmamış — kırmızı
            self.setStyleSheet(
                "QFrame{background:rgba(200,40,40,35);"
                "border:1px solid rgba(255,90,90,100);"
                "border-radius:7px;}"
            )
        else:
            # ○ Normal bekleyen — turuncu
            self.setStyleSheet(
                "QFrame{background:rgba(190,110,20,30);"
                "border:1px solid rgba(255,170,60,80);"
                "border-radius:7px;}"
            )

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(7)

        # Checkbox — rengi duruma göre
        if self.completed:
            cb_checked_bg    = "rgba(60,190,100,220)"
            cb_checked_bdr   = "rgba(60,190,100,255)"
        else:
            cb_checked_bg    = "rgba(90,150,255,210)"
            cb_checked_bdr   = "rgba(90,150,255,255)"

        cb = QCheckBox()
        cb.setChecked(self.completed)
        cb.setStyleSheet(
            "QCheckBox::indicator{width:14px;height:14px;border-radius:3px;"
            "border:1px solid rgba(255,255,255,55);background:rgba(255,255,255,8);}"
            f"QCheckBox::indicator:checked{{background:{cb_checked_bg};"
            f"border-color:{cb_checked_bdr};}}"
        )
        cb.stateChanged.connect(lambda: self.toggle_requested.emit(self.note_id))
        row.addWidget(cb, 0, Qt.AlignmentFlag.AlignTop)

        # Metin alanı
        txt = QVBoxLayout()
        txt.setSpacing(2)

        title_f = QFont("Segoe UI", 11)
        if self.completed:
            title_f.setStrikeOut(True)
        title_lbl = QLabel(note["title"])
        title_lbl.setFont(title_f)
        title_lbl.setWordWrap(True)
        if self.completed:
            title_lbl.setStyleSheet("color:rgba(130,230,150,220);background:transparent;")
        elif self.overdue:
            title_lbl.setStyleSheet("color:rgba(255,140,140,240);background:transparent;")
        else:
            title_lbl.setStyleSheet("color:rgba(255,210,140,240);background:transparent;")
        txt.addWidget(title_lbl)

        if note["due_time"]:
            suffix = "  ⚠ GEÇMİŞ" if (self.overdue and not self.completed) else ""
            if self.completed:
                tc = "rgba(100,210,130,180)"
            elif self.overdue:
                tc = "rgba(255,100,100,200)"
            else:
                tc = "rgba(255,185,80,190)"
            t_lbl = QLabel(f"⏰  {note['due_time']}{suffix}")
            t_lbl.setStyleSheet(f"color:{tc};font-size:10px;background:transparent;")
            txt.addWidget(t_lbl)

        if note["description"]:
            d_lbl = QLabel(note["description"])
            d_lbl.setWordWrap(True)
            d_lbl.setStyleSheet("color:rgba(255,255,255,130);font-size:10px;background:transparent;")
            txt.addWidget(d_lbl)

        row.addLayout(txt, stretch=1)

        # Eylem butonları
        btns = QVBoxLayout()
        btns.setSpacing(3)
        for symbol, signal, color in [
            ("✏", self.edit_requested,   "rgba(100,150,255,180)"),
            ("✕", self.delete_requested, "rgba(255,120,120,180)"),
        ]:
            b = QPushButton(symbol)
            b.setFixedSize(22, 22)
            b.setStyleSheet(
                f"QPushButton{{background:rgba(255,255,255,18);border:none;"
                f"border-radius:5px;color:{color};}}"
                "QPushButton:hover{background:rgba(255,255,255,38);}"
            )
            b.clicked.connect(lambda _, sig=signal: sig.emit(self.note_id))
            btns.addWidget(b)
        row.addLayout(btns)


# ═══════════════════════════════════════════════════════════════════════════
class DateBubble(QWidget):
    """
    Takvim küçültüldüğünde ekranda duran yuvarlak tarih baloncuğu.
    Tıklandığında takvim tekrar açılır; sürükleyerek konumu değiştirilebilir.
    """
    expand_requested = pyqtSignal()
    SIZE = 76

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos  = None
        self._drag_start = None
        self._settings  = QSettings("DesktopCalendar", "Bubble")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Takvimi aç")

    def paintEvent(self, _):
        today = date.today()
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        S = self.SIZE

        # Dış yumuşak glow
        glow = QPainterPath()
        glow.addEllipse(QRectF(1, 1, S - 2, S - 2))
        p.fillPath(glow, QBrush(QColor(55, 115, 255, 35)))

        # Ana daire
        circle = QPainterPath()
        circle.addEllipse(QRectF(5, 5, S - 10, S - 10))
        p.fillPath(circle, QBrush(QColor(11, 16, 38, 225)))
        a = _THEME["accent"]
        p.strokePath(circle, QPen(QColor(*a, 170), 1.5))

        # Ay adı — üst
        p.setPen(QColor(*a, 210))
        f_mon = QFont("Segoe UI", 9)
        p.setFont(f_mon)
        p.drawText(QRectF(5, 13, S - 10, 16),
                   Qt.AlignmentFlag.AlignCenter,
                   MONTHS_TR[today.month - 1][:3].upper())

        # Gün numarası — orta
        p.setPen(QColor(255, 255, 255, 245))
        f_day = QFont("Segoe UI", 26)
        f_day.setBold(True)
        p.setFont(f_day)
        p.drawText(QRectF(5, 22, S - 10, 34),
                   Qt.AlignmentFlag.AlignCenter, str(today.day))

        # Haftanın günü — alt
        p.setPen(QColor(*_THEME["sel"], 170))
        f_wd = QFont("Segoe UI", 8)
        p.setFont(f_wd)
        p.drawText(QRectF(5, S - 20, S - 10, 15),
                   Qt.AlignmentFlag.AlignCenter,
                   DAYS_TR[today.weekday()])
        p.end()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos   = e.globalPosition().toPoint()
            self._drag_start = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._drag_start:
                delta = e.globalPosition().toPoint() - self._drag_start
                if abs(delta.x()) < 6 and abs(delta.y()) < 6:
                    self.expand_requested.emit()
            self._settings.setValue("bubble_pos", self.pos())
        self._drag_pos   = None
        self._drag_start = None


# ═══════════════════════════════════════════════════════════════════════════
class CalendarWindow(QWidget):
    """
    Ana takvim penceresi.
    • Frameless + şeffaf arka plan
    • Üst başlık çubuğundan sürükle-bırak
    • "–" butonu ile compact moda kısaltılır, "+" ile tekrar açılır
    """

    def __init__(self):
        super().__init__()
        today = date.today()
        self.cur_year  = today.year
        self.cur_month = today.month
        self.sel_date  = today
        self._drag_pos = None
        self._day_btns: dict[int, DayButton] = {}
        self._compact   = False

        self._settings   = QSettings("DesktopCalendar", "App")
        self._theme_name = self._settings.value("theme", "Mavi")
        self._cal_name   = self._settings.value("cal_name", "Takvim")
        _THEME.update(THEMES.get(self._theme_name, THEMES["Mavi"]))

        self._setup_window()
        self._build_ui()
        self._refresh_calendar()

        # Küçültme baloncuğu
        self._bubble = DateBubble()
        self._bubble.expand_requested.connect(self._expand_from_bubble)
        bubble_pos = self._settings.value("bubble_pos")
        if bubble_pos:
            self._bubble.move(bubble_pos)

        # Önceki konumu geri yükle
        pos = self._settings.value("pos")
        if pos:
            self.move(pos)

    # ── pencere ayarları ──────────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool          # görev çubuğunda görünmez
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumWidth(506)

        # Varsayılan konum: ekranın sağ üstü
        from PyQt6.QtWidgets import QApplication
        geo = QApplication.primaryScreen().availableGeometry()
        self.move(geo.width() - 526, 40)

    # ── UI inşası ────────────────────────────────────────────────────────
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(0)

        # Dış container — paintEvent ile çizilir, sadece layout tutar
        self._inner = QWidget(self)
        self._inner.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        lay = QVBoxLayout(self._inner)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)

        # ── Başlık çubuğu ─────────────────────────────────────────────
        hdr = QHBoxLayout()
        self._title_lbl = QLabel(f"📅  {self._cal_name}")
        self._title_lbl.setStyleSheet(
            "color:rgba(255,255,255,210);font-size:13px;font-weight:bold;"
        )
        hdr.addWidget(self._title_lbl)
        hdr.addStretch()

        for label, style, slot in [
            ("Bugün",   "rgba(90,140,255,80)",  self._go_today),
            ("⚠ Geçmiş","rgba(190,70,70,80)",   self._show_overdue),
        ]:
            b = QPushButton(label)
            b.setStyleSheet(
                f"QPushButton{{background:{style};border:none;border-radius:5px;"
                f"color:rgba(255,255,255,210);font-size:11px;padding:3px 9px;}}"
                "QPushButton:hover{background:rgba(255,255,255,40);}"
            )
            b.clicked.connect(slot)
            hdr.addWidget(b)

        settings_btn = QPushButton("⚙")
        settings_btn.setFixedSize(22, 22)
        settings_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,22);border:none;border-radius:11px;"
            "color:rgba(200,220,255,200);font-size:14px;}"
            "QPushButton:hover{background:rgba(100,160,255,120);}"
        )
        settings_btn.clicked.connect(self._show_settings)
        hdr.addWidget(settings_btn)

        self._toggle_btn = QPushButton("–")
        self._toggle_btn.setFixedSize(22, 22)
        self._toggle_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,22);border:none;border-radius:11px;"
            "color:rgba(255,255,255,200);font-size:15px;font-weight:bold;}"
            "QPushButton:hover{background:rgba(255,200,80,120);}"
        )
        self._toggle_btn.clicked.connect(self._toggle_compact)
        hdr.addWidget(self._toggle_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,22);border:none;border-radius:11px;"
            "color:rgba(255,200,200,200);font-size:12px;}"
            "QPushButton:hover{background:rgba(200,50,50,160);color:white;}"
        )
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)

        lay.addLayout(hdr)

        # ── Genişleyebilir alan ───────────────────────────────────────
        self._expandable = QWidget()
        exp_lay = QVBoxLayout(self._expandable)
        exp_lay.setContentsMargins(0, 4, 0, 0)
        exp_lay.setSpacing(6)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background:rgba(255,255,255,18);max-height:1px;")
        exp_lay.addWidget(sep1)

        # Ay navigasyon
        nav = QHBoxLayout()
        for text, slot in [("‹", self._prev_month), ("›", self._next_month)]:
            b = QPushButton(text)
            b.setFixedSize(28, 28)
            b.setStyleSheet(
                "QPushButton{background:rgba(255,255,255,14);border:none;"
                "border-radius:14px;color:rgba(255,255,255,200);font-size:20px;}"
                "QPushButton:hover{background:rgba(255,255,255,32);}"
            )
            b.clicked.connect(slot)
            nav.addWidget(b) if text == "‹" else nav.addWidget(b)
            if text == "‹":
                nav.addStretch()
                self._month_lbl = QLabel()
                self._month_lbl.setStyleSheet(
                    "color:white;font-size:14px;font-weight:bold;"
                )
                self._month_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                nav.addWidget(self._month_lbl)
                nav.addStretch()
        exp_lay.addLayout(nav)

        # Gün başlıkları
        day_hdr = QHBoxLayout()
        day_hdr.setSpacing(3)
        for d in DAYS_TR:
            lbl = QLabel(d)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setFixedWidth(62)
            lbl.setStyleSheet(
                "color:rgba(255,255,255,110);font-size:11px;font-weight:bold;"
            )
            day_hdr.addWidget(lbl)
        exp_lay.addLayout(day_hdr)

        # Takvim grid
        from PyQt6.QtWidgets import QGridLayout
        self._grid = QGridLayout()
        self._grid.setSpacing(4)
        exp_lay.addLayout(self._grid)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background:rgba(255,255,255,14);max-height:1px;")
        exp_lay.addWidget(sep2)

        # Not paneli başlığı
        note_hdr = QHBoxLayout()
        self._date_lbl = QLabel("Notlar")
        self._date_lbl.setStyleSheet(
            "color:rgba(255,255,255,180);font-size:12px;font-weight:bold;"
        )
        note_hdr.addWidget(self._date_lbl)
        note_hdr.addStretch()

        add_btn = QPushButton("＋ Not Ekle")
        add_btn.setStyleSheet(
            "QPushButton{background:rgba(60,145,90,120);border:none;border-radius:5px;"
            "color:rgba(200,255,215,225);font-size:11px;padding:4px 10px;}"
            "QPushButton:hover{background:rgba(80,180,115,200);}"
        )
        add_btn.clicked.connect(self._add_note)
        note_hdr.addWidget(add_btn)
        exp_lay.addLayout(note_hdr)

        # Notlar scroll alanı
        self._notes_scroll = QScrollArea()
        self._notes_scroll.setWidgetResizable(True)
        self._notes_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._notes_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:rgba(255,255,255,8);width:5px;border-radius:3px;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,60);border-radius:3px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )
        self._notes_scroll.setMinimumHeight(140)
        self._notes_scroll.setMaximumHeight(340)

        self._notes_cont = QWidget()
        self._notes_cont.setStyleSheet("background:transparent;")
        self._notes_lay = QVBoxLayout(self._notes_cont)
        self._notes_lay.setContentsMargins(0, 0, 0, 0)
        self._notes_lay.setSpacing(5)
        self._notes_lay.addStretch()

        self._notes_scroll.setWidget(self._notes_cont)
        exp_lay.addWidget(self._notes_scroll)

        lay.addWidget(self._expandable)
        outer.addWidget(self._inner)

    # ── paintEvent — şeffaf cam görünümü ──────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(6, 6, -6, -6)
        path = QPainterPath()
        path.addRoundedRect(QRectF(r), 14, 14)
        bg = _THEME["bg"]
        p.fillPath(path, QBrush(QColor(*bg, 215)))
        p.strokePath(path, QPen(QColor(255, 255, 255, 22), 1.0))
        p.end()

    # ── sürükleme ─────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        self._settings.setValue("pos", self.pos())

    # ── compact modu ──────────────────────────────────────────────────────
    def _toggle_compact(self):
        """Takvimi gizleyip yuvarlak tarih baloncuğuna küçültür."""
        self._compact = True
        # Baloncuğu takvim penceresinin ortasına yerleştir
        geo    = self.geometry()
        bsize  = DateBubble.SIZE
        bx     = geo.x() + (geo.width()  - bsize) // 2
        by     = geo.y() + (geo.height() - bsize) // 2
        self._bubble.move(bx, by)
        self._settings.setValue("bubble_pos", self._bubble.pos())
        self.hide()
        self._bubble.show()
        self._bubble.raise_()

    def _expand_from_bubble(self):
        """Baloncuğa tıklanınca takvimi tekrar açar."""
        self._compact = False
        bp    = self._bubble.pos()
        bsize = DateBubble.SIZE
        self._bubble.hide()
        self.adjustSize()
        # Baloncuğun sağına yerleştir; sığmazsa soluna
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        wx = bp.x() + bsize + 10
        wy = bp.y()
        if wx + self.width() > screen.right():
            wx = bp.x() - self.width() - 10
        wy = max(screen.top(), min(wy, screen.bottom() - self.height()))
        wx = max(screen.left(), wx)
        self.move(wx, wy)
        self._settings.setValue("pos", self.pos())
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_visibility(self):
        if self._compact:
            if self._bubble.isVisible():
                self._bubble.hide()
            else:
                self._bubble.show()
                self._bubble.raise_()
        else:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    # ── navigasyon ────────────────────────────────────────────────────────
    def _go_today(self):
        t = date.today()
        self.cur_year, self.cur_month, self.sel_date = t.year, t.month, t
        self._refresh_calendar()

    def _prev_month(self):
        if self.cur_month == 1:
            self.cur_month, self.cur_year = 12, self.cur_year - 1
        else:
            self.cur_month -= 1
        self._refresh_calendar()

    def _next_month(self):
        if self.cur_month == 12:
            self.cur_month, self.cur_year = 1, self.cur_year + 1
        else:
            self.cur_month += 1
        self._refresh_calendar()

    # ── takvim yenileme ───────────────────────────────────────────────────
    def _refresh_calendar(self):
        self._month_lbl.setText(
            f"{MONTHS_TR[self.cur_month - 1]}  {self.cur_year}"
        )

        # Grid temizle
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._day_btns.clear()

        today         = date.today()
        note_counts   = db.get_dot_counts_for_month(self.cur_year, self.cur_month)
        overdue_dates = db.get_overdue_dates_for_month(self.cur_year, self.cur_month)

        for row, week in enumerate(calendar.monthcalendar(self.cur_year, self.cur_month)):
            for col, day in enumerate(week):
                if day == 0:
                    placeholder = QWidget()
                    placeholder.setFixedSize(62, 70)
                    self._grid.addWidget(placeholder, row, col)
                    continue

                ds = f"{self.cur_year:04d}-{self.cur_month:02d}-{day:02d}"
                btn = DayButton(
                    day,
                    note_count = note_counts.get(ds, 0),
                    is_today   = (self.cur_year == today.year
                                  and self.cur_month == today.month
                                  and day == today.day),
                    is_overdue = ds in overdue_dates,
                )
                btn.clicked.connect(lambda _, d=day: self._on_day_click(d))
                self._day_btns[day] = btn
                self._grid.addWidget(btn, row, col)

        self._update_selection()

        if (self.sel_date.year == self.cur_year
                and self.sel_date.month == self.cur_month):
            self._refresh_notes()

    def _update_selection(self):
        for day, btn in self._day_btns.items():
            btn.set_selected(
                self.sel_date.year  == self.cur_year
                and self.sel_date.month == self.cur_month
                and self.sel_date.day   == day
            )

    def _on_day_click(self, day: int):
        self.sel_date = date(self.cur_year, self.cur_month, day)
        self._update_selection()
        self._refresh_notes()

    # ── not paneli ───────────────────────────────────────────────────────
    def _refresh_notes(self):
        while self._notes_lay.count() > 1:
            item = self._notes_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._date_lbl.setText(
            f"{self.sel_date.day} {MONTHS_TR[self.sel_date.month - 1]}"
            f" {self.sel_date.year}"
        )

        notes = db.get_notes_for_date(self.sel_date.isoformat())
        if not notes:
            empty = QLabel("Bu gün için henüz not yok…")
            empty.setStyleSheet(
                "color:rgba(255,255,255,75);font-size:11px;"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._notes_lay.insertWidget(0, empty)
            return

        for i, note in enumerate(notes):
            wi = NoteItem(note)
            wi.edit_requested.connect(self._edit_note)
            wi.delete_requested.connect(self._delete_note)
            wi.toggle_requested.connect(self._toggle_note)
            self._notes_lay.insertWidget(i, wi)

    # ── not işlemleri ─────────────────────────────────────────────────────
    def _add_note(self):
        dlg = NoteDialog(self, date_str=self.sel_date.isoformat())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            db.add_note(d["title"], d["description"],
                        d["date"], d["due_time"], d["notify"])
            self._refresh_calendar()

    def _edit_note(self, note_id: int):
        notes = db.get_notes_for_date(self.sel_date.isoformat())
        note  = next((n for n in notes if n["id"] == note_id), None)
        if not note:
            return
        dlg = NoteDialog(self, note=note)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            db.update_note(note_id, d["title"], d["description"],
                           d["date"], d["due_time"], d["notify"])
            self._refresh_calendar()

    def _delete_note(self, note_id: int):
        from PyQt6.QtWidgets import QMessageBox
        ans = QMessageBox.question(
            self, "Notu Sil",
            "Bu notu silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            db.delete_note(note_id)
            self._refresh_calendar()

    def _toggle_note(self, note_id: int):
        db.toggle_complete(note_id)
        self._refresh_notes()
        # Nokta / overdue durumunu güncelle
        counts  = db.get_dot_counts_for_month(self.cur_year, self.cur_month)
        overdues = db.get_overdue_dates_for_month(self.cur_year, self.cur_month)
        for day, btn in self._day_btns.items():
            ds = f"{self.cur_year:04d}-{self.cur_month:02d}-{day:02d}"
            btn.note_count = counts.get(ds, 0)
            btn.is_overdue = ds in overdues
            btn.update()

    # ── tema ve ayarlar ───────────────────────────────────────────────────
    def _apply_theme(self, theme_name: str, save: bool = True):
        self._theme_name = theme_name
        _THEME.update(THEMES.get(theme_name, THEMES["Mavi"]))
        if save:
            self._settings.setValue("theme", theme_name)
        self.update()
        self._refresh_calendar()

    def _show_settings(self):
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dlg.setModal(True)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 0)

        box = QFrame()
        box.setStyleSheet(
            "QFrame{background:rgba(12,16,34,248);"
            "border-radius:12px;border:1px solid rgba(255,255,255,42);}"
        )
        bl = QVBoxLayout(box)
        bl.setContentsMargins(22, 18, 22, 18)
        bl.setSpacing(12)

        # Başlık
        hdr_lbl = QLabel("⚙  Ayarlar")
        hdr_lbl.setStyleSheet(
            "color:white;font-size:15px;font-weight:bold;"
            "background:transparent;border:none;"
        )
        bl.addWidget(hdr_lbl)

        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet("background:rgba(255,255,255,22);max-height:1px;border:none;")
        bl.addWidget(sep1)

        # Takvim adı
        lbl_name = QLabel("Takvim Adı")
        lbl_name.setStyleSheet(
            "color:rgba(255,255,255,180);font-size:11px;background:transparent;border:none;"
        )
        bl.addWidget(lbl_name)
        name_edit = QLineEdit(self._cal_name)
        name_edit.setStyleSheet(
            "QLineEdit{background:rgba(255,255,255,12);border:1px solid rgba(255,255,255,30);"
            "border-radius:6px;color:white;padding:6px;font-size:12px;}"
            "QLineEdit:focus{border-color:rgba(100,160,255,200);}"
        )
        bl.addWidget(name_edit)

        # Tema seçimi
        lbl_theme = QLabel("Tema Rengi")
        lbl_theme.setStyleSheet(
            "color:rgba(255,255,255,180);font-size:11px;background:transparent;border:none;"
        )
        bl.addWidget(lbl_theme)

        theme_combo = QComboBox()
        theme_combo.addItems(list(THEMES.keys()))
        idx = theme_combo.findText(self._theme_name)
        if idx >= 0:
            theme_combo.setCurrentIndex(idx)
        theme_combo.setStyleSheet(
            "QComboBox{background:rgba(255,255,255,12);border:1px solid rgba(255,255,255,30);"
            "border-radius:6px;color:white;padding:5px 10px;font-size:12px;}"
            "QComboBox::drop-down{border:none;width:22px;}"
            "QComboBox QAbstractItemView{background:rgba(18,22,44,252);color:white;"
            "border:1px solid rgba(255,255,255,40);"
            "selection-background-color:rgba(90,140,255,120);}"
        )
        bl.addWidget(theme_combo)

        # Otomatik başlangıç
        sep_auto = QFrame()
        sep_auto.setFrameShape(QFrame.Shape.HLine)
        sep_auto.setStyleSheet("background:rgba(255,255,255,16);max-height:1px;border:none;")
        bl.addWidget(sep_auto)

        auto_cb = QCheckBox("Bilgisayar açılışında otomatik başlat")
        auto_cb.setChecked(_autostart_enabled())
        auto_cb.setStyleSheet(
            "QCheckBox{color:rgba(255,255,255,200);font-size:12px;background:transparent;border:none;}"
            "QCheckBox::indicator{width:15px;height:15px;border-radius:4px;"
            "border:1px solid rgba(255,255,255,50);background:rgba(255,255,255,10);}"
            "QCheckBox::indicator:checked{background:rgba(90,150,255,210);"
            "border-color:rgba(90,150,255,255);}"
        )
        bl.addWidget(auto_cb)

        # Ayırıcı ve geliştirici bilgisi
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet("background:rgba(255,255,255,16);max-height:1px;border:none;")
        bl.addWidget(sep2)

        dev_lbl = QLabel("Geliştirici: Aykut TORTOP")
        dev_lbl.setStyleSheet(
            "color:rgba(180,200,255,130);font-size:10px;"
            "background:transparent;border:none;"
        )
        dev_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(dev_lbl)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.setStyleSheet(
            "QPushButton{background:rgba(170,50,50,110);border:none;border-radius:6px;"
            "color:rgba(255,200,200,230);padding:7px 18px;font-size:12px;}"
            "QPushButton:hover{background:rgba(200,70,70,180);}"
        )
        cancel_btn.clicked.connect(dlg.reject)

        ok_btn = QPushButton("Kaydet  ✓")
        ok_btn.setStyleSheet(
            "QPushButton{background:rgba(50,140,100,140);border:none;border-radius:6px;"
            "color:rgba(200,255,220,230);padding:7px 18px;font-size:12px;}"
            "QPushButton:hover{background:rgba(70,180,130,210);}"
        )
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(dlg.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        bl.addLayout(btn_row)

        outer.addWidget(box)

        dlg.adjustSize()
        pg = self.geometry()
        dlg.move(
            pg.x() + (pg.width()  - dlg.width())  // 2,
            pg.y() + (pg.height() - dlg.height()) // 2,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_name = name_edit.text().strip() or "Takvim"
            self._cal_name = new_name
            self._settings.setValue("cal_name", new_name)
            self._title_lbl.setText(f"📅  {new_name}")
            self._apply_theme(theme_combo.currentText())
            _set_autostart(auto_cb.isChecked())

    # ── geçmiş notlar penceresi ───────────────────────────────────────────
    def _show_overdue(self):
        dlg = QDialog(self)
        dlg.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dlg.setModal(True)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 0)

        box = QFrame()
        box.setStyleSheet(
            "QFrame{background:rgba(12,16,34,245);"
            "border-radius:12px;border:1px solid rgba(255,255,255,38);}"
        )
        bl = QVBoxLayout(box)
        bl.setContentsMargins(16, 14, 16, 14)
        bl.setSpacing(8)

        hdr_lbl = QLabel("⚠  Geçmiş ve Tamamlanmamış Notlar")
        hdr_lbl.setStyleSheet(
            "color:rgba(255,200,140,235);font-size:14px;font-weight:bold;"
            "background:transparent;border:none;"
        )
        bl.addWidget(hdr_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{background:rgba(255,255,255,8);width:5px;border-radius:3px;}"
            "QScrollBar::handle:vertical{background:rgba(255,255,255,55);border-radius:3px;}"
            "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}"
        )

        sc_w = QWidget()
        sc_w.setStyleSheet("background:transparent;")
        sc_l = QVBoxLayout(sc_w)
        sc_l.setSpacing(5)

        overdue = db.get_overdue_notes()
        if not overdue:
            ok_lbl = QLabel("🎉  Geçmiş notunuz yok, harikasınız!")
            ok_lbl.setStyleSheet(
                "color:rgba(140,255,160,210);font-size:12px;"
                "background:transparent;border:none;"
            )
            ok_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sc_l.addWidget(ok_lbl)
        else:
            for note in overdue:
                f = QFrame()
                f.setStyleSheet(
                    "QFrame{background:rgba(200,50,50,22);"
                    "border:1px solid rgba(255,100,100,70);border-radius:6px;}"
                )
                fl = QHBoxLayout(f)
                fl.setContentsMargins(10, 7, 10, 7)

                info = QVBoxLayout()
                parts = note["date"].split("-")
                ds = f"{int(parts[2])} {MONTHS_TR[int(parts[1])-1]} {parts[0]}"
                if note["due_time"]:
                    ds += f"  {note['due_time']}"

                t_l = QLabel(note["title"])
                t_l.setStyleSheet(
                    "color:rgba(255,185,185,240);font-weight:bold;"
                    "background:transparent;border:none;"
                )
                d_l = QLabel(ds)
                d_l.setStyleSheet(
                    "color:rgba(255,145,145,160);font-size:10px;"
                    "background:transparent;border:none;"
                )
                info.addWidget(t_l)
                info.addWidget(d_l)
                fl.addLayout(info, stretch=1)

                goto = QPushButton("Git →")
                goto.setStyleSheet(
                    "QPushButton{background:rgba(90,140,255,80);border:none;"
                    "border-radius:4px;color:rgba(200,220,255,210);"
                    "font-size:10px;padding:3px 9px;}"
                    "QPushButton:hover{background:rgba(90,140,255,160);}"
                )
                nd = note["date"]
                goto.clicked.connect(
                    lambda _, d=nd: (self._goto_date(d), dlg.accept())
                )
                fl.addWidget(goto)
                sc_l.addWidget(f)

        sc_l.addStretch()
        scroll.setWidget(sc_w)
        scroll.setMinimumWidth(320)
        scroll.setMinimumHeight(160)
        scroll.setMaximumHeight(380)
        bl.addWidget(scroll)

        close = QPushButton("Kapat")
        close.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,18);border:none;border-radius:6px;"
            "color:rgba(255,255,255,210);padding:6px 22px;}"
            "QPushButton:hover{background:rgba(255,255,255,38);}"
        )
        close.clicked.connect(dlg.accept)
        bl.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)

        outer.addWidget(box)

        # Ortala
        dlg.adjustSize()
        pg = self.geometry()
        dlg.move(
            pg.x() + (pg.width()  - dlg.width())  // 2,
            pg.y() + (pg.height() - dlg.height()) // 2,
        )
        dlg.exec()

    def _goto_date(self, date_str: str):
        d = date.fromisoformat(date_str)
        self.cur_year, self.cur_month, self.sel_date = d.year, d.month, d
        self._refresh_calendar()
