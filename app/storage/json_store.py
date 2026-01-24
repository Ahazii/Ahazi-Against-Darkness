from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TypeVar, Callable
from uuid import uuid4

from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


class JsonStore:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _collection_dir(self, name: str) -> Path:
        path = self.base_dir / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def list(self, collection: str, parser: Callable[[dict], T]) -> list[T]:
        results: list[T] = []
        for file_path in self._collection_dir(collection).glob("*.json"):
            data = json.loads(file_path.read_text(encoding="utf-8"))
            results.append(parser(data))
        return results

    def get(self, collection: str, item_id: str, parser: Callable[[dict], T]) -> T | None:
        file_path = self._collection_dir(collection) / f"{item_id}.json"
        if not file_path.exists():
            return None
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return parser(data)

    def save(self, collection: str, item: T) -> None:
        file_path = self._collection_dir(collection) / f"{item.id}.json"
        file_path.write_text(item.model_dump_json(), encoding="utf-8")

    def new_id(self) -> str:
        return uuid4().hex


def now_utc() -> datetime:
    return datetime.utcnow()
