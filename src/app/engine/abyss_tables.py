"""Four Against the Abyss Phase B table catalog."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _tables_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "rules" / "abyss_tables.json"


@lru_cache(maxsize=1)
def load_abyss_tables_raw() -> dict[str, Any]:
    return json.loads(_tables_path().read_text(encoding="utf-8"))


def abyss_table_rows(table_key: str) -> list[dict[str, Any]]:
    rows = load_abyss_tables_raw().get(table_key)
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def abyss_table_roll_keys(table_key: str) -> list[str]:
    return [str(row.get("roll", "")).strip() for row in abyss_table_rows(table_key) if row.get("roll")]
