from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterator, TypeVar
from uuid import uuid4

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)

COLLECTIONS = {"characters", "parties", "sessions"}


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def new_id() -> str:
    return uuid4().hex


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
                collection TEXT NOT NULL,
                id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (collection, id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_records_collection_updated
            ON records(collection, updated_at)
            """
        )
        conn.commit()
    finally:
        conn.close()


class Store:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def list(self, collection: str, parser: Callable[[dict], T]) -> list[T]:
        self._validate_collection(collection)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT data FROM records WHERE collection = ? ORDER BY created_at",
                (collection,),
            ).fetchall()
        return [parser(json.loads(row["data"])) for row in rows]

    def get(self, collection: str, item_id: str, parser: Callable[[dict], T]) -> T | None:
        self._validate_collection(collection)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM records WHERE collection = ? AND id = ?",
                (collection, item_id),
            ).fetchone()
        if row is None:
            return None
        return parser(json.loads(row["data"]))

    def save(self, collection: str, item: BaseModel) -> None:
        self._validate_collection(collection)
        payload = item.model_dump_json()
        timestamp = now_utc()
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT created_at FROM records WHERE collection = ? AND id = ?",
                (collection, item.id),
            ).fetchone()
            created_at = existing["created_at"] if existing else timestamp
            conn.execute(
                """
                INSERT INTO records(collection, id, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(collection, id) DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at
                """,
                (collection, item.id, payload, created_at, timestamp),
            )

    def delete(self, collection: str, item_id: str) -> bool:
        self._validate_collection(collection)
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM records WHERE collection = ? AND id = ?",
                (collection, item_id),
            )
            return cursor.rowcount > 0

    def _validate_collection(self, collection: str) -> None:
        if collection not in COLLECTIONS:
            raise ValueError(f"Unknown collection: {collection}")
