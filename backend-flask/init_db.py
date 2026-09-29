"""
Optional: run this once if you ever want to reset the database back to the
original seed data (15 papers, 6 themes, etc.) — deletes and recreates
database/research_dashboard.db from database/schema.sql.

Usage:  python init_db.py
"""
from pathlib import Path

from database import DB_PATH, ensure_database

if __name__ == "__main__":
    if DB_PATH.exists():
        confirm = input(f"This will DELETE and rebuild {DB_PATH.name}, losing any edits you made. Continue? [y/N] ")
        if confirm.strip().lower() != "y":
            print("Cancelled.")
            raise SystemExit(0)
        Path(DB_PATH).unlink()
    ensure_database()
    print("Done.")
