from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ClassProfile:
    name: str
    base_life: int
    life_per_level: int
    attack_bonus_per_level: int
    defense_bonus_per_level: int


def load_class_profiles() -> dict[str, ClassProfile]:
    data_path = Path(__file__).resolve().parent / "data" / "classes.json"
    raw = json.loads(data_path.read_text(encoding="utf-8"))
    profiles: dict[str, ClassProfile] = {}
    for entry in raw:
        profiles[entry["name"].lower()] = ClassProfile(
            name=entry["name"],
            base_life=entry["base_life"],
            life_per_level=entry["life_per_level"],
            attack_bonus_per_level=entry["attack_bonus_per_level"],
            defense_bonus_per_level=entry["defense_bonus_per_level"],
        )
    return profiles
