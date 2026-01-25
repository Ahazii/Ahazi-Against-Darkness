from __future__ import annotations

import json
import logging
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
    try:
        raw = json.loads(data_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        logging.warning("Class data file missing at %s, using defaults.", data_path)
        raw = [
            {
                "name": "Warrior",
                "base_life": 5,
                "life_per_level": 1,
                "attack_bonus_per_level": 1,
                "defense_bonus_per_level": 0,
            },
            {
                "name": "Cleric",
                "base_life": 4,
                "life_per_level": 1,
                "attack_bonus_per_level": 0,
                "defense_bonus_per_level": 1,
            },
            {
                "name": "Rogue",
                "base_life": 4,
                "life_per_level": 1,
                "attack_bonus_per_level": 0,
                "defense_bonus_per_level": 1,
            },
            {
                "name": "Wizard",
                "base_life": 3,
                "life_per_level": 1,
                "attack_bonus_per_level": 0,
                "defense_bonus_per_level": 0,
            },
            {
                "name": "Barbarian",
                "base_life": 5,
                "life_per_level": 1,
                "attack_bonus_per_level": 1,
                "defense_bonus_per_level": 0,
            },
            {
                "name": "Ranger",
                "base_life": 4,
                "life_per_level": 1,
                "attack_bonus_per_level": 1,
                "defense_bonus_per_level": 0,
            },
            {
                "name": "Dwarf",
                "base_life": 5,
                "life_per_level": 1,
                "attack_bonus_per_level": 1,
                "defense_bonus_per_level": 0,
            },
            {
                "name": "Elf",
                "base_life": 4,
                "life_per_level": 1,
                "attack_bonus_per_level": 1,
                "defense_bonus_per_level": 0,
            },
            {
                "name": "Halfling",
                "base_life": 4,
                "life_per_level": 1,
                "attack_bonus_per_level": 0,
                "defense_bonus_per_level": 1,
            },
        ]
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
