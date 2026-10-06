from __future__ import annotations

import json
import hashlib
import hmac
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from passlib.hash import pbkdf2_sha256

from models import ProductCard, StockLevel


BACKEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = BACKEND_DIR.parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(ROOT_DIR / "data" / "campus_customs.db")))
PRODUCTS_DIR = Path(os.getenv("PRODUCTS_DIR", str(ROOT_DIR / "data" / "products")))
AUDIT_PATH = ROOT_DIR / "output" / "audit_trail.json"
AUDIT_LOCK = threading.Lock()

STOP_WORDS = {
    "a", "about", "an", "and", "are", "available", "can", "could", "do", "does",
    "for", "have", "hello", "help", "how", "i", "in", "is", "it", "know", "me",
    "my", "of", "our", "please", "show", "size", "sizes", "stock", "tell", "that",
    "the", "there", "this", "to", "us", "want", "we", "what", "with", "you", "your",
}
WORD_ALIASES = {
    "hoodies": "hoodie", "tees": "shirt", "tshirts": "shirt", "tshirt": "shirt",
    "sweatshirts": "sweatshirt", "crewnecks": "crewneck", "jackets": "jacket",
    "sweaters": "sweater", "quarterzips": "quarterzip", "quarter-zip": "quarterzip",
}
SIZE_PATTERN = re.compile(r"\b(XXS|XXL|XS|XL|S|M|L)\b", re.IGNORECASE)


def connect() -> sqlite3.Connection:
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(
            f"Course database was not found at {DATABASE_PATH}. Place campus_customs.db in data/."
        )
    connection = sqlite3.connect(DATABASE_PATH, timeout=8)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_chat_table() -> None:
    with connect() as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                products_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )"""
        )
        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_lower ON users(lower(email))"
        )


def _parse_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return [str(item) for item in parsed] if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _inventory(connection: sqlite3.Connection, product_id: str) -> list[StockLevel]:
    rows = connection.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ? ORDER BY id",
        (product_id,),
    ).fetchall()
    return [StockLevel(size=str(row["size"]), quantity=int(row["quantity"])) for row in rows]


def _product_card(connection: sqlite3.Connection, row: sqlite3.Row) -> ProductCard:
    levels = _inventory(connection, str(row["product_id"]))
    image_path = str(row["image_file_path"])
    filename = Path(image_path).name
    return ProductCard(
        product_id=str(row["product_id"]),
        name=str(row["name"]),
        garment_type=str(row["garment_type"]),
        description=str(row["description"]),
        colors=_parse_json_list(row["colors"]),
        search_tags=_parse_json_list(row["search_tags"]),
        image_file_path=image_path,
        image_url=f"/media/products/{filename}",
        price=float(row["price"]),
        inventory=levels,
        total_stock=sum(level.quantity for level in levels),
    )


def list_products(search: str = "", limit: int = 120) -> list[ProductCard]:
    safe_limit = max(1, min(int(limit), 120))
    with connect() as connection:
        if not search.strip():
            rows = connection.execute(
                "SELECT * FROM catalogue ORDER BY name LIMIT ?", (safe_limit,)
            ).fetchall()
            return [_product_card(connection, row) for row in rows]
        return _search_products(connection, search, safe_limit)


def search_products(search: str, limit: int = 8) -> list[ProductCard]:
    safe_limit = max(1, min(int(limit), 8))
    with connect() as connection:
        return _search_products(connection, search, safe_limit)


def _search_products(
    connection: sqlite3.Connection, search: str, limit: int
) -> list[ProductCard]:
    normalized = re.sub(r"[^a-z0-9-]+", " ", search.lower()).strip()
    tokens = [
        WORD_ALIASES.get(token, token)
        for token in normalized.split()
        if token not in STOP_WORDS and len(token) > 1
    ]
    if not tokens:
        return []
    rows = connection.execute("SELECT * FROM catalogue").fetchall()
    ranked: list[tuple[int, str, sqlite3.Row]] = []
    category_terms = {
        "hoodie", "shirt", "crewneck", "sweatshirt", "sweater", "jacket", "quarterzip",
    }
    has_category = any(token in category_terms for token in tokens)
    for row in rows:
        product_id = str(row["product_id"]).lower()
        name = str(row["name"]).lower()
        garment = str(row["garment_type"]).lower()
        tags = " ".join(_parse_json_list(row["search_tags"])).lower()
        colors = " ".join(_parse_json_list(row["colors"])).lower()
        description = str(row["description"]).lower()
        score = 0
        matched = 0
        for token in tokens:
            if token in name or token.replace("-", " ") in name:
                score += 6
                matched += 1
            elif token in garment:
                score += 5
                matched += 1
            elif token in product_id:
                score += 5
                matched += 1
            elif token in tags:
                score += 3
                matched += 1
            elif token in colors:
                score += 3
                matched += 1
            elif token in description:
                score += 1
                matched += 1
        if has_category and any(token in garment or token in name for token in tokens if token in category_terms):
            score += 6
        if normalized and normalized in name:
            score += 8
        if score and matched:
            ranked.append((score, name, row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [_product_card(connection, row) for _, _, row in ranked[:limit]]


def get_product(product_id: str) -> ProductCard | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM catalogue WHERE product_id = ?", (product_id,)
        ).fetchone()
        return _product_card(connection, row) if row else None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT id, first_name, last_name, name, email, password_hash "
            "FROM users WHERE lower(email) = lower(?)",
            (email.strip(),),
        ).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT id, first_name, last_name, name, email FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(row) if row else None


def create_user(first_name: str, last_name: str, email: str, password: str) -> dict[str, Any]:
    full_name = f"{first_name.strip()} {last_name.strip()}".strip()
    password_hash = pbkdf2_sha256.using(rounds=600_000).hash(password)
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) "
            "VALUES (?, ?, ?, ?, ?)",
            (full_name, email.strip().lower(), password_hash, first_name.strip(), last_name.strip()),
        )
        user_id = int(cursor.lastrowid)
    return {
        "id": user_id,
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "name": full_name,
        "email": email.strip().lower(),
    }


def verify_password(password: str, password_hash: str) -> bool:
    try:
        parts = password_hash.split("$")
        if len(parts) == 3 and parts[0] == "pbkdf2_sha256" and len(parts[2]) == 64:
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), parts[1].encode("utf-8"), 120_000
            ).hex()
            return hmac.compare_digest(actual, parts[2])
        return bool(pbkdf2_sha256.verify(password, password_hash))
    except (ValueError, TypeError):
        return False


def save_chat_message(
    user_id: int, role: str, content: str, products: list[ProductCard] | None = None
) -> None:
    products_json = json.dumps([item.model_dump() for item in products or []])
    with connect() as connection:
        connection.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, ?, ?, ?)",
            (user_id, role, content[:4000], products_json),
        )


def load_chat_history(user_id: int, limit: int = 40) -> list[dict[str, Any]]:
    safe_limit = max(1, min(int(limit), 80))
    with connect() as connection:
        rows = connection.execute(
            "SELECT id, role, content, products_json, created_at FROM chat_messages "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, safe_limit),
        ).fetchall()
    items: list[dict[str, Any]] = []
    for row in reversed(rows):
        try:
            products = [ProductCard.model_validate(x) for x in json.loads(row["products_json"] or "[]")]
        except (TypeError, ValueError, json.JSONDecodeError):
            products = []
        items.append(
            {
                "id": int(row["id"]),
                "role": str(row["role"]),
                "content": str(row["content"]),
                "products": products,
                "created_at": str(row["created_at"]),
            }
        )
    return items


def record_audit(
    tool_name: str,
    arguments: dict[str, Any],
    result_summary: str,
    stop_reason: str,
) -> None:
    """Keep a logical append-only JSON list; never include passwords or full chat text."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result_summary[:240],
        "stop_reason": stop_reason,
    }
    with AUDIT_LOCK:
        try:
            entries = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            entries = []
        entries.append(entry)
        temporary = AUDIT_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
        temporary.replace(AUDIT_PATH)


def ensure_audit_file() -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not AUDIT_PATH.exists():
        AUDIT_PATH.write_text("[]\n", encoding="utf-8")
