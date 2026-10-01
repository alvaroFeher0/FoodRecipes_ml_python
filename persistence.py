import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "foodml.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS receipts (
    id          INTEGER PRIMARY KEY,
    image_hash  TEXT NOT NULL UNIQUE,
    uploaded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY,
    receipt_id INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    line       TEXT,
    ingredient TEXT
);
CREATE TABLE IF NOT EXISTS recipes (
    id          INTEGER PRIMARY KEY,
    receipt_id  INTEGER NOT NULL REFERENCES receipts(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    ingredients TEXT NOT NULL,  -- JSON list
    steps       TEXT NOT NULL,  -- JSON list
    approx_cost REAL
);
"""


@contextmanager
def connect():
    """Open the database, create the tables if needed, commit on success and always close."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts: row["name"]
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    # databases created before approx_cost existed don't get it from CREATE TABLE IF NOT EXISTS
    if "approx_cost" not in [col["name"] for col in conn.execute("PRAGMA table_info(recipes)")]:
        conn.execute("ALTER TABLE recipes ADD COLUMN approx_cost REAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_image(file):
    """SHA-256 of the image bytes, used to recognise a receipt that was already uploaded."""
    if isinstance(file, (str, Path)):
        data = Path(file).read_bytes()
    else:
        data = file.read()
        file.seek(0)  # leave the upload readable for the next step
    return hashlib.sha256(data).hexdigest()


def save_receipt(image_hash, mapping, recipes):
    """Store a receipt with its item -> ingredient mapping and generated recipes. Returns its id."""
    with connect() as conn:
        receipt_id = conn.execute(
            "INSERT INTO receipts (image_hash, uploaded_at) VALUES (?, ?)",
            (image_hash, datetime.now(timezone.utc).isoformat()),
        ).lastrowid
        conn.executemany(
            "INSERT INTO items (receipt_id, line, ingredient) VALUES (?, ?, ?)",
            [(receipt_id, row.line, row.ingredient) for row in mapping.itertuples()],
        )
        conn.executemany(
            "INSERT INTO recipes (receipt_id, name, ingredients, steps, approx_cost) VALUES (?, ?, ?, ?, ?)",
            [
                (receipt_id, r["name"], json.dumps(r["ingredients"]), json.dumps(r["steps"]), r.get("cost"))
                for r in recipes
            ],
        )
    return receipt_id


def load_receipt(image_hash):
    """Return (ingredients, recipes) for a saved receipt, or None if it was never uploaded."""
    with connect() as conn:
        receipt = conn.execute("SELECT id FROM receipts WHERE image_hash = ?", (image_hash,)).fetchone()
        if receipt is None:
            return None
        ingredients = [row["ingredient"] for row in conn.execute(
            "SELECT DISTINCT lower(ingredient) AS ingredient FROM items "
            "WHERE receipt_id = ? AND ingredient IS NOT NULL ORDER BY 1",
            (receipt["id"],),
        )]
        recipes = [
            {
                "name": row["name"],
                "ingredients": json.loads(row["ingredients"]),
                "steps": json.loads(row["steps"]),
                "cost": row["approx_cost"],
            }
            for row in conn.execute("SELECT * FROM recipes WHERE receipt_id = ? ORDER BY id", (receipt["id"],))
        ]
    return ingredients, recipes


def list_receipts():
    """Return every saved receipt as dicts with image_hash, uploaded_at and recipe_count, newest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.image_hash, r.uploaded_at, count(re.id) AS recipe_count FROM receipts r "
            "LEFT JOIN recipes re ON re.receipt_id = r.id GROUP BY r.id ORDER BY r.uploaded_at DESC"
        ).fetchall()
    return [dict(row) for row in rows]
