"""
database.py — SQLite veri katmanı
Notları ~/.desktop_calendar/notes.db içinde saklar.
"""

import sqlite3
import os
from datetime import date, datetime

DB_PATH = os.path.join(os.path.expanduser("~"), ".desktop_calendar", "notes.db")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                description TEXT    DEFAULT '',
                date        TEXT    NOT NULL,        -- YYYY-MM-DD
                due_time    TEXT,                    -- HH:MM veya NULL
                completed   INTEGER DEFAULT 0,
                notify      INTEGER DEFAULT 0,
                notified    INTEGER DEFAULT 0,
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def _row_factory(conn):
    conn.row_factory = sqlite3.Row
    return conn


def add_note(title: str, description: str, note_date: str,
             due_time: str = None, notify: int = 0) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO notes (title, description, date, due_time, notify) VALUES (?,?,?,?,?)",
            (title, description, note_date, due_time, notify),
        )
        return cur.lastrowid


def get_notes_for_date(date_str: str):
    with _row_factory(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(
            "SELECT * FROM notes WHERE date=? ORDER BY due_time IS NULL, due_time, created_at",
            (date_str,),
        ).fetchall()


def get_dot_counts_for_month(year: int, month: int) -> dict:
    """Her gün için toplam not sayısını döner  {date_str: count}"""
    prefix = f"{year:04d}-{month:02d}"
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT date, COUNT(*) FROM notes WHERE date LIKE ? GROUP BY date",
            (f"{prefix}-%",),
        ).fetchall()
    return {r[0]: r[1] for r in rows}


def get_overdue_dates_for_month(year: int, month: int) -> set:
    """Geçmiş & tamamlanmamış not olan günlerin kümesi"""
    today = date.today().isoformat()
    now_t = datetime.now().strftime("%H:%M")
    prefix = f"{year:04d}-{month:02d}"
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            """SELECT DISTINCT date FROM notes
               WHERE date LIKE ? AND completed=0
                 AND (date < ?
                      OR (date=? AND due_time IS NOT NULL AND due_time < ?))""",
            (f"{prefix}-%", today, today, now_t),
        ).fetchall()
    return {r[0] for r in rows}


def get_overdue_notes():
    """Tüm geçmiş ve tamamlanmamış notları döner"""
    today = date.today().isoformat()
    now_t = datetime.now().strftime("%H:%M")
    with _row_factory(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(
            """SELECT * FROM notes
               WHERE completed=0
                 AND (date < ?
                      OR (date=? AND due_time IS NOT NULL AND due_time < ?))
               ORDER BY date, due_time IS NULL, due_time""",
            (today, today, now_t),
        ).fetchall()


def update_note(note_id: int, title: str, description: str, note_date: str,
                due_time: str = None, notify: int = 0):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """UPDATE notes
               SET title=?, description=?, date=?, due_time=?, notify=?, notified=0
               WHERE id=?""",
            (title, description, note_date, due_time, notify, note_id),
        )


def toggle_complete(note_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE notes SET completed = 1 - completed WHERE id=?", (note_id,)
        )


def delete_note(note_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))


def get_pending_notifications():
    """Önümüzdeki 15 dakika içinde zamanı gelen bildirimleri döner"""
    from datetime import timedelta
    today = date.today().isoformat()
    now_t = datetime.now().strftime("%H:%M")
    window_t = (datetime.now() + timedelta(minutes=15)).strftime("%H:%M")
    with _row_factory(sqlite3.connect(DB_PATH)) as conn:
        return conn.execute(
            """SELECT * FROM notes
               WHERE notify=1 AND completed=0 AND notified=0
                 AND date=? AND due_time BETWEEN ? AND ?""",
            (today, now_t, window_t),
        ).fetchall()


def mark_notified(note_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE notes SET notified=1 WHERE id=?", (note_id,))
