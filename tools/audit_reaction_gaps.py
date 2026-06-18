#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
monsters = json.loads((ROOT / "data/rules/monsters.json").read_text(encoding="utf-8"))
dt = json.loads((ROOT / "data/rules/dungeon_tables.json").read_text(encoding="utf-8"))

HANDLED = {
    "blood_offering", "bribe", "bribe_food", "bribe_food_or_gem", "bribe_food_per_foe",
    "bribe_gem", "bribe_gem_or_two_handed_weapon", "bribe_gold_or_food", "bribe_magic_item",
    "bribe_ration_gold_or_mushroom", "bribe_scrolls_or_potions", "bribe_treasure_or_magic_item",
    "buy_weapons", "challenge_of_champions", "fight", "fight_to_death", "flee", "flee_if_outnumbered",
    "ignore", "magic_challenge", "offer_food", "offer_information", "peaceful", "puzzle", "quest",
    "sleep", "trade", "trade_information", "trial_of_champions", "capture",
}

WIRED_FIELDS = {"gold", "gold_per_foe", "gold_dice", "weapons_per_foe", "no_fools_gold", "bribe_magic_item", "source_page"}

keys: set[str] = set()
field_gaps: list[str] = []
special_no_test = []

for tname, trows in monsters.get("reaction_tables", {}).items():
    for row in trows:
        keys.add(row["key"])
        extra = {k: v for k, v in row.items() if k not in ("roll", "key", "result", "foes_first")}
        unknown = set(extra) - WIRED_FIELDS
        if unknown:
            field_gaps.append(f"{tname} roll {row['roll']} key {row['key']}: {unknown}")

for t in ["default_reaction_table", "vermin_reaction_table", "minion_reaction_table", "major_reaction_table"]:
    for row in dt.get(t, []):
        keys.add(row["key"])
        extra = {k: v for k, v in row.items() if k not in ("roll", "key", "result", "foes_first")}
        unknown = set(extra) - WIRED_FIELDS
        if unknown:
            field_gaps.append(f"{t} roll {row['roll']} key {row['key']}: {unknown}")

unhandled = sorted(keys - HANDLED)
print("UNHANDLED KEYS:", unhandled or "none")
print("\nUNWIRED ROW FIELDS:")
for line in field_gaps:
    print(" ", line)
if not field_gaps:
    print("  none")
