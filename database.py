import sqlite3
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS listings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                price TEXT,
                description TEXT,
                avito_url TEXT NOT NULL,
                brand TEXT,
                photo_id TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS guides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                text TEXT NOT NULL,
                photo_id TEXT
            )
            """
        )


# ---------- Listings ----------

def add_listing(title, price, description, avito_url, brand, photo_id):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO listings (title, price, description, avito_url, brand, photo_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (title, price, description, avito_url, brand, photo_id),
        )
        return cur.lastrowid


def list_listings(active_only=True):
    with get_conn() as conn:
        query = "SELECT * FROM listings"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY id DESC"
        return conn.execute(query).fetchall()


def get_listing(listing_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()


def delete_listing(listing_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM listings WHERE id = ?", (listing_id,))


def update_listing_field(listing_id, field, value):
    allowed_fields = {"title", "price", "description", "avito_url", "brand", "photo_id"}
    if field not in allowed_fields:
        raise ValueError(f"ÐÐµÐ´Ð¾Ð¿ÑÑÑÐ¸Ð¼Ð¾Ðµ Ð¿Ð¾Ð»Ðµ: {field}")
    with get_conn() as conn:
        conn.execute(f"UPDATE listings SET {field} = ? WHERE id = ?", (value, listing_id))


def set_listing_active(listing_id, active: bool):
    with get_conn() as conn:
        conn.execute(
            "UPDATE listings SET active = ? WHERE id = ?", (1 if active else 0, listing_id)
        )


# ---------- Size guides ----------

def add_guide(brand, text, photo_id=None):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO guides (brand, text, photo_id) VALUES (?, ?, ?)",
            (brand, text, photo_id),
        )
        return cur.lastrowid


def list_guides():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM guides ORDER BY brand").fetchall()


def get_guide_by_brand(brand):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM guides WHERE brand = ? LIMIT 1", (brand,)
        ).fetchone()


def delete_guide(guide_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM guides WHERE id = ?", (guide_id,))