"""
SQLite connection helpers for the Research Recommendation Dashboard.

The database is a single file: database/research_dashboard.db, sitting next
to this backend. It's created automatically (from database/schema.sql) the
first time the Flask app starts, so there is no separate "run migrations"
step — just `python app.py`.
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "research_dashboard.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_database():
    """Create + seed the SQLite file from schema.sql if it doesn't exist yet."""
    is_new = not DB_PATH.exists()
    if is_new:
        print(f"[init] No database found at {DB_PATH} — creating it from schema.sql ...")
        conn = sqlite3.connect(DB_PATH)
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

        # Replace the placeholder password hash with a real one for the seeded admin user.
        from werkzeug.security import generate_password_hash

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (generate_password_hash("password"), "admin@dashboard.test"),
        )
        conn.commit()
        conn.close()
        print("[init] Database created and seeded (15 papers, 6 themes, findings, etc.)")

    run_migrations()


def run_migrations():
    """
    Lightweight, additive migrations so an existing database.db from an
    earlier version of this project still works after an update — no manual
    ALTER TABLE, no data loss. Safe to call on every startup.
    """
    conn = sqlite3.connect(DB_PATH)
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(research_papers)")}

    if "citation_count" not in existing_columns:
        print("[migrate] Adding citation_count column to research_papers ...")
        conn.execute("ALTER TABLE research_papers ADD COLUMN citation_count INTEGER")

    if "citations_updated_at" not in existing_columns:
        print("[migrate] Adding citations_updated_at column to research_papers ...")
        conn.execute("ALTER TABLE research_papers ADD COLUMN citations_updated_at TEXT")

    existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if "reading_list" not in existing_tables:
        print("[migrate] Creating reading_list table ...")
        conn.execute("""
            CREATE TABLE reading_list (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,
              authors TEXT,
              venue TEXT,
              year INTEGER,
              doi TEXT,
              url TEXT,
              abstract TEXT,
              source TEXT,
              tags TEXT DEFAULT '',
              notes TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'unread' CHECK (status IN ('unread','read')),
              bookmarked_at TEXT
            )
        """)

    conn.commit()
    conn.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row) if row is not None else None


def rows_to_list(rows) -> list:
    return [dict(r) for r in rows]
