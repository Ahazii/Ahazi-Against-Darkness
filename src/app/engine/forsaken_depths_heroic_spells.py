"""Forsaken Depths Heroic spell catalog (FD p.19)."""

from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from .spells import normalize_spell_name


def _catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "rules" / "heroic_spells.json"


@lru_cache(maxsize=1)
def load_heroic_spells_catalog() -> dict[str, Any]:
    return json.loads(_catalog_path().read_text(encoding="utf-8"))


def heroic_spell_rows() -> list[dict[str, Any]]:
    return [row for row in load_heroic_spells_catalog().get("spells", []) if isinstance(row, dict)]


def heroic_spell_names() -> list[str]:
    return [str(row.get("name", "")).strip() for row in heroic_spell_rows() if row.get("name")]


def random_heroic_spell_name() -> str:
    names = heroic_spell_names()
    if not names:
        return "Heroic spell"
    return random.choice(names)


def heroic_spell_id(name: str) -> str:
    token = normalize_spell_name(name)
    for row in heroic_spell_rows():
        if normalize_spell_name(str(row.get("name", ""))) == token:
            return str(row.get("id", token))
    return token


def is_fd_heroic_spell(spell_name: str) -> bool:
    token = normalize_spell_name(spell_name)
    return any(normalize_spell_name(str(row.get("name", ""))) == token for row in heroic_spell_rows())
