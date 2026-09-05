from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import CATALOG_PATH, DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    budget_json TEXT NOT NULL,
    status TEXT NOT NULL,
    receipt_json TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    name TEXT NOT NULL,
    price_paise INTEGER NOT NULL,
    is_upsell INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    input_json TEXT NOT NULL,
    reason TEXT NOT NULL,
    decision TEXT NOT NULL,
    outcome TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


_ready = False


def init_db(*, reseed: bool = False) -> None:
    global _ready
    if _ready and not reseed:
        return
    with _connect() as conn:
        conn.executescript(SCHEMA)
        _seed_products(conn)
        conn.commit()
    _ready = True


def _seed_products(conn: sqlite3.Connection) -> None:
    raw = json.loads(Path(CATALOG_PATH).read_text(encoding="utf-8"))
    conn.execute("DELETE FROM products")
    for product in raw["products"]:
        conn.execute(
            "INSERT INTO products (id, payload_json) VALUES (?, ?)",
            (product["id"], json.dumps(product)),
        )


@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()

