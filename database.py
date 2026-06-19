import os
import sqlite3
from contextlib import contextmanager

from config import DB_PATH

_db_dir = os.path.dirname(DB_PATH)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)


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
                category TEXT,
                size TEXT,
                photo_id TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        # Для базы, созданной до появления категорий/размеров — добавляем
        # колонки отдельно (SQLite не поддерживает ADD COLUMN IF NOT EXISTS).
        for column in ("category", "size"):
            try:
                conn.execute(f"ALTER TABLE listings ADD COLUMN {column} TEXT")
            except sqlite3.OperationalError:
                pass  # колонка уже существует

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

def add_listing(title, price, description, avito_url, brand, category, size, photo_id):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO listings
               (title, price, description, avito_url, brand, category, size, photo_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (title, price, description, avito_url, brand, category, size, photo_id),
        )
        return cur.lastrowid


def list_listings(active_only=True):
    with get_conn() as conn:
        query = "SELECT * FROM listings"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY id DESC"
        return conn.execute(query).fetchall()


def list_categories(active_only=True):
    with get_conn() as conn:
        query = (
            "SELECT DISTINCT category FROM listings "
            "WHERE category IS NOT NULL AND category != ''"
        )
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY category"
        return [row["category"] for row in conn.execute(query).fetchall()]


def list_sizes_in_category(category, active_only=True):
    with get_conn() as conn:
        query = (
            "SELECT DISTINCT size FROM listings "
            "WHERE category = ? AND size IS NOT NULL AND size != ''"
        )
        params = [category]
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY size"
        return [row["size"] for row in conn.execute(query, params).fetchall()]


def list_listings_filtered(category=None, size=None, active_only=True):
    with get_conn() as conn:
        query = "SELECT * FROM listings WHERE 1=1"
        params = []
        if category:
            query += " AND category = ?"
            params.append(category)
        if size:
            query += " AND size = ?"
            params.append(size)
        if active_only:
            query += " AND active = 1"
        query += " ORDER BY id DESC"
        return conn.execute(query, params).fetchall()


def get_listing(listing_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()


def delete_listing(listing_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM listings WHERE id = ?", (listing_id,))


def update_listing_field(listing_id, field, value):
    allowed_fields = {
        "title", "price", "description", "avito_url",
        "brand", "category", "size", "photo_id",
    }
    if field not in allowed_fields:
        raise ValueError(f"Недопустимое поле: {field}")
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