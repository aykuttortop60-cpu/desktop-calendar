"""
dialogs.py — Not Ekle / Düzenle diyaloğu
Şeffaf, frameless, sürüklenebilir modal dialog.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QCheckBox, QPushButton,
    QTimeEdit, QDateEdit, QFrame,
)
from PyQt6.QtCore import Qt, QTime, QDate
from PyQt6.QtGui import QPainter, QColor, QBrush, QPainterPath


_CONTAINER_STYLE = """
QFrame#DlgContainer {
    background: rgba(14, 18, 38, 245);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,45);
}
QLabel {
    color: rgba(255,255,255,190);
    font-size: 11px;
    background: transparent;
}
QLineEdit, QTextEdit {
    background: rgba(255,255,255,12);
    border: 1px solid rgba(255,255,255,30);
    border-radius: 6px;
    color: white;
    padding: 6px;
    font-size: 12px;
}
QLineEdit:focus, QTextEdit:focus {
    border-color: rgba(100,160,255,200);
}
QCheckBox {
    color: rgba(255,255,255,200);
    font-size: 11px;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid rgba(255,255,255,50);
    background: rgba(255,255,255,10);
}
QCheckBox::indicator:checked {
    background: rgba(90,150,255,210);
    border-color: rgba(90,150,255,255);
}
QDateEdit, QTimeEdit {
    background: rgba(255,255,255,12);
    border: 1px solid rgba(255,255,255,30);
    border-radius: 6px;
    color: white;
    padding: 4px 6px;
    font-size: 12px;
}
QDateEdit::drop-down, QTimeEdit::drop-down {
    width: 18px;
    border: none;
}
QDateEdit::down-arrow, QTimeEdit::down-arrow {
    width: 8px;
    height: 8px;
}
QSpinBox { color: white; background: transparent; border: none; }
"""


class NoteDialog(QDialog):
    """Not ekle/düzenle modal diyaloğu"""

    def __init__(self, parent=None, note=None, date_str: str = None):
        super().__init__(parent)
        self.note = note
        self._drag_pos = None

        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(340)

        self._build_ui(date_str)

        if note:
            self._load_note(note)

        # Ebeveyne göre ortala
        if parent:
            self.adjustSize()
            pg = parent.geometry()
            self.move(
                pg.x() + (pg.width() - self.width()) // 2,
                pg.y() + (pg.height() - self.height()) // 2,
            )

    # ------------------------------------------------------------------ build
    def _build_ui(self, date_str: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self._container = QFrame()
        self._container.setObjectName("DlgContainer")
        self._container.setStyleSheet(_CONTAINER_STYLE)

        lay = QVBoxLayout(self._container)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        # Başlık çubuğu
        hdr = QHBoxLayout()
        title_lbl = QLabel("📝 " + ("Notu Düzenle" if self.note else "Yeni Not Ekle"))
        title_lbl.setStyleSheet(
            "color:white; font-size:14px; font-weight:bold; background:transparent;"
        )
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Başlık alanı
        lay.addWidget(QLabel("Başlık  *"))
        self._title = QLineEdit()
        self._title.setPlaceholderText("Not başlığını giriniz…")
        lay.addWidget(self._title)

        # Açıklama
        lay.addWidget(QLabel("Açıklama"))
        self._desc = QTextEdit()
        self._desc.setPlaceholderText("Detaylar (isteğe bağlı)…")
        self._desc.setFixedHeight(72)
        lay.addWidget(self._desc)

        # Tarih / Saat satırı
        row = QHBoxLayout()
        row.setSpacing(12)

        date_col = QVBoxLayout()
        date_col.addWidget(QLabel("Tarih"))
        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        from datetime import date
        if date_str:
            d = date.fromisoformat(date_str)
            self._date.setDate(QDate(d.year, d.month, d.day))
        else:
            self._date.setDate(QDate.currentDate())
        date_col.addWidget(self._date)
        row.addLayout(date_col)

        time_col = QVBoxLayout()
        time_col.addWidget(QLabel("Saat (isteğe bağlı)"))
        time_row = QHBoxLayout()
        self._has_time = QCheckBox()
        self._time = QTimeEdit()
        self._time.setTime(QTime.currentTime())
        self._time.setEnabled(False)
        self._has_time.toggled.connect(self._time.setEnabled)
        time_row.addWidget(self._has_time)
        time_row.addWidget(self._time)
        time_col.addLayout(time_row)
        row.addLayout(time_col)

        lay.addLayout(row)

        # Bildirim
        self._notify = QCheckBox("🔔  Bildirim gönder  (15 dakika önce)")
        lay.addWidget(self._notify)

        # Butonlar
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._cancel_btn = QPushButton("İptal")
        self._cancel_btn.setStyleSheet(
            "QPushButton{background:rgba(170,50,50,110);border:none;border-radius:6px;"
            "color:rgba(255,200,200,230);padding:7px 18px;font-size:12px;}"
            "QPushButton:hover{background:rgba(200,70,70,180);}"
        )
        self._cancel_btn.clicked.connect(self.reject)

        self._ok_btn = QPushButton("Kaydet  ✓")
        self._ok_btn.setStyleSheet(
            "QPushButton{background:rgba(50,140,100,140);border:none;border-radius:6px;"
            "color:rgba(200,255,220,230);padding:7px 18px;font-size:12px;}"
            "QPushButton:hover{background:rgba(70,180,130,210);}"
        )
        self._ok_btn.setDefault(True)
        self._ok_btn.clicked.connect(self._on_ok)

        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._ok_btn)
        lay.addLayout(btn_row)

        outer.addWidget(self._container)

    # ------------------------------------------------------------------ load
    def _load_note(self, note):
        self._title.setText(note["title"])
        self._desc.setPlainText(note["description"] or "")

        from datetime import date
        d = date.fromisoformat(note["date"])
        self._date.setDate(QDate(d.year, d.month, d.day))

        if note["due_time"]:
            self._has_time.setChecked(True)
            h, m = map(int, note["due_time"].split(":"))
            self._time.setTime(QTime(h, m))

        self._notify.setChecked(bool(note["notify"]))

    # ------------------------------------------------------------------ ok
    def _on_ok(self):
        if not self._title.text().strip():
            self._title.setStyleSheet(
                "QLineEdit{background:rgba(200,50,50,30);"
                "border:1px solid rgba(255,80,80,180);"
                "border-radius:6px;color:white;padding:6px;}"
            )
            self._title.setPlaceholderText("⚠  Başlık zorunludur!")
            return
        self.accept()

    # ------------------------------------------------------------------ data
    def get_data(self) -> dict:
        qd = self._date.date()
        due_time = None
        if self._has_time.isChecked():
            qt = self._time.time()
            due_time = f"{qt.hour():02d}:{qt.minute():02d}"

        return {
            "title": self._title.text().strip(),
            "description": self._desc.toPlainText().strip(),
            "date": f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}",
            "due_time": due_time,
            "notify": 1 if self._notify.isChecked() else 0,
        }

    # ------------------------------------------------------------------ drag
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(self.pos() + event.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
