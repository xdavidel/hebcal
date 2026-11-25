import os
import sqlite3


def init(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            hebrew_month INTEGER NOT NULL,
            hebrew_day INTEGER NOT NULL,
            notes TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()
    conn.close()


def _conn(db_path):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    return c


def list_entries(db_path):
    with _conn(db_path) as c:
        return [dict(r) for r in c.execute("SELECT * FROM entries ORDER BY name")]


def get_entry(db_path, eid):
    with _conn(db_path) as c:
        r = c.execute("SELECT * FROM entries WHERE id = ?", (eid,)).fetchone()
        return dict(r) if r else None


def add_entry(db_path, data):
    with _conn(db_path) as c:
        cur = c.execute(
            "INSERT INTO entries (name, event_type, hebrew_month, hebrew_day, notes) VALUES (?, ?, ?, ?, ?)",
            (
                data["name"],
                data["event_type"],
                data["hebrew_month"],
                data["hebrew_day"],
                data.get("notes", ""),
            ),
        )
        c.commit()
        return cur.lastrowid


def update_entry(db_path, eid, data):
    with _conn(db_path) as c:
        c.execute(
            "UPDATE entries SET name=?, event_type=?, hebrew_month=?, hebrew_day=?, notes=? WHERE id=?",
            (
                data["name"],
                data["event_type"],
                data["hebrew_month"],
                data["hebrew_day"],
                data.get("notes", ""),
                eid,
            ),
        )
        c.commit()


def delete_entry(db_path, eid):
    with _conn(db_path) as c:
        c.execute("DELETE FROM entries WHERE id=?", (eid,))
        c.commit()


def get_setting(db_path, key, default=None):
    with _conn(db_path) as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return r["value"] if r else default


def set_setting(db_path, key, value):
    with _conn(db_path) as c:
        c.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        c.commit()
