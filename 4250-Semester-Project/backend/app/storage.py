from .database import get_connection


def read_items():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def write_items(items):
    # Kept so old imports do not break
    pass


def read_checkouts():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM checkouts ORDER BY id")
    rows = cur.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def write_checkouts(checkouts):
    # Kept so old imports do not break
    pass


def next_id(records):
    # SQLite handles IDs automatically
    return None