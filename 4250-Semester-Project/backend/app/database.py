import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "lender_tracker.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity >= 0)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS checkouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            borrower TEXT NOT NULL,
            checkout_date TEXT NOT NULL,
            due_date TEXT,
            returned INTEGER NOT NULL DEFAULT 0,
            return_date TEXT,
            FOREIGN KEY (item_id) REFERENCES items(id)
        )
    """)

    conn.commit()
    conn.close()