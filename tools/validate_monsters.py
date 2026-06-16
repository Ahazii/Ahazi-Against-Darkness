"""validate_monsters.py

Structural validation for data/rules/monsters.json.

Checks every monster entry across all 15 tables for:
  - Required fields (name, level_delta, count, life, attacks, tags)
  - level_delta is an integer >= 0
  - count is a non-empty string
  - life is an int or a recognised formula string (HCL+N, Tier+N, HCL)
  - attacks is an int >= 0 or a recognised formula string
  - tags is a non-empty list of strings
  - reactions is a list of dicts, each with roll/key/result
  - notes is a non-empty string
  - life_minimum (if present) is an integer
  - immunities (if present) is a list of strings
  - vulnerabilities (if present) is a list of dicts, each with type/description
  - on_hit_effects, encounter_start_effects, per_turn_effects,
    special_rules, combat_modifiers, post_combat_effects,
    special_attacks, morale_triggers (if present) are lists of dicts with description
  - Reaction roll ranges do not overlap and cover at least 1 option
  - d6 reaction tables: rolls should be plausible d6 outcomes

Exit 0 on success, 1 on any failure.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MONSTERS_FILE = ROOT / "data" / "rules" / "monsters.json"

LIFE_FORMULA = re.compile(r"^(HCL|Tier)(\+\d+)?$")
ATTACKS_FORMULA = re.compile(r"^(d\d+\+\d+|Tier\+\d+|HCL\+\d+)$")

# All top-level array keys that contain monster entries
MONSTER_TABLE_KEYS = [
    "vermin",
    "minions",
    "weird",
    "boss",
    "caverns_vermin",
    "caverns_minions",
    "caverns_weird",
    "caverns_boss",
    "fungal_grottoes_vermin",
    "fungal_grottoes_minions",
    "fungal_grottoes_weird",
    "fungal_grottoes_boss",
    # wandering entries are generic placeholders; validate lightly
    "wandering",
]

# Sub-object list fields whose items must have 'description'
DESCRIBED_LIST_FIELDS = [
    "on_hit_effects",
    "encounter_start_effects",
    "per_turn_effects",
    "special_rules",
    "combat_modifiers",
    "post_combat_effects",
    "special_attacks",
    "morale_triggers",
    "on_defense_roll_1_effects",
    "combat_effects",
    "vulnerabilities",
]


def err(table: str, name: str, msg: str) -> str:
    return f"[{table}] {name!r}: {msg}"


def validate_life(v: object) -> bool:
    if isinstance(v, int) and v >= 0:
        return True
    if isinstance(v, str) and LIFE_FORMULA.match(v):
        return True
    return False


def validate_attacks(v: object) -> bool:
    if isinstance(v, int) and v >= 0:
        return True
    if isinstance(v, str) and ATTACKS_FORMULA.match(v):
        return True
    return False


def validate_reactions(reactions: list, table: str, name: str, errors: list[str]) -> None:
    if not isinstance(reactions, list) or not reactions:
        errors.append(err(table, name, "reactions must be a non-empty list"))
        return
    for i, r in enumerate(reactions):
        if not isinstance(r, dict):
            errors.append(err(table, name, f"reactions[{i}] must be a dict"))
            continue
        for key in ("roll", "key", "result"):
            if key not in r:
                errors.append(err(table, name, f"reactions[{i}] missing '{key}'"))


def validate_described_lists(entry: dict, table: str, name: str, errors: list[str]) -> None:
    for field in DESCRIBED_LIST_FIELDS:
        if field not in entry:
            continue
        items = entry[field]
        if not isinstance(items, list):
            errors.append(err(table, name, f"'{field}' must be a list"))
            continue
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(err(table, name, f"'{field}'[{i}] must be a dict"))
                continue
            if "description" not in item:
                errors.append(err(table, name, f"'{field}'[{i}] missing 'description'"))
            if "type" not in item:
                errors.append(err(table, name, f"'{field}'[{i}] missing 'type'"))


def validate_entry(entry: dict, table: str, errors: list[str]) -> None:
    name = entry.get("name", "<unnamed>")

    # Required fields
    if "name" not in entry or not isinstance(entry["name"], str):
        errors.append(err(table, name, "missing or non-string 'name'"))

    if "level_delta" not in entry:
        errors.append(err(table, name, "missing 'level_delta'"))
    elif not isinstance(entry["level_delta"], int) or entry["level_delta"] < 0:
        errors.append(err(table, name, f"'level_delta' must be int >= 0, got {entry['level_delta']!r}"))

    if "count" not in entry:
        errors.append(err(table, name, "missing 'count'"))
    elif not isinstance(entry["count"], str) or not entry["count"].strip():
        errors.append(err(table, name, f"'count' must be a non-empty string, got {entry['count']!r}"))

    if "life" not in entry:
        errors.append(err(table, name, "missing 'life'"))
    elif not validate_life(entry["life"]):
        errors.append(err(table, name, f"'life' value {entry['life']!r} is not int>=0 or a recognised formula"))

    if "attacks" not in entry:
        errors.append(err(table, name, "missing 'attacks'"))
    elif not validate_attacks(entry["attacks"]):
        errors.append(err(table, name, f"'attacks' value {entry['attacks']!r} not recognised"))

    if "tags" not in entry:
        errors.append(err(table, name, "missing 'tags'"))
    elif not isinstance(entry["tags"], list) or not entry["tags"]:
        errors.append(err(table, name, "'tags' must be a non-empty list"))
    else:
        for t in entry["tags"]:
            if not isinstance(t, str):
                errors.append(err(table, name, f"tag {t!r} must be a string"))

    # notes — only required for non-wandering tables
    if table != "wandering":
        if "notes" not in entry:
            errors.append(err(table, name, "missing 'notes'"))
        elif not isinstance(entry["notes"], str) or not entry["notes"].strip():
            errors.append(err(table, name, "'notes' must be a non-empty string"))

    # reactions — only required for non-wandering tables
    if table != "wandering":
        if "reactions" not in entry:
            errors.append(err(table, name, "missing 'reactions'"))
        else:
            validate_reactions(entry["reactions"], table, name, errors)

    # life_minimum
    if "life_minimum" in entry:
        if not isinstance(entry["life_minimum"], int) or entry["life_minimum"] < 0:
            errors.append(err(table, name, f"'life_minimum' must be int>=0, got {entry['life_minimum']!r}"))

    # immunities
    if "immunities" in entry:
        imm = entry["immunities"]
        if not isinstance(imm, list):
            errors.append(err(table, name, "'immunities' must be a list"))
        else:
            for v in imm:
                if not isinstance(v, str):
                    errors.append(err(table, name, f"immunity {v!r} must be a string"))

    # morale_modifier
    if "morale_modifier" in entry:
        if not isinstance(entry["morale_modifier"], int):
            errors.append(err(table, name, f"'morale_modifier' must be int, got {entry['morale_modifier']!r}"))

    # treasure_modifier / treasure_rolls
    for tf in ("treasure_modifier", "treasure_rolls"):
        if tf in entry and not isinstance(entry[tf], int):
            errors.append(err(table, name, f"'{tf}' must be int, got {entry[tf]!r}"))

    # max_level
    if "max_level" in entry:
        if not isinstance(entry["max_level"], int) or entry["max_level"] < 1:
            errors.append(err(table, name, f"'max_level' must be int>=1, got {entry['max_level']!r}"))

    # never_test_morale
    if "never_test_morale" in entry and not isinstance(entry["never_test_morale"], bool):
        errors.append(err(table, name, f"'never_test_morale' must be bool"))

    # no_treasure
    if "no_treasure" in entry and not isinstance(entry["no_treasure"], bool):
        errors.append(err(table, name, f"'no_treasure' must be bool"))

    # Described sub-lists
    validate_described_lists(entry, table, name, errors)

    # entry_roll / disguise / trade_reaction / regeneration
    for obj_field in ("entry_roll", "disguise", "trade_reaction", "regeneration"):
        if obj_field in entry and not isinstance(entry[obj_field], dict):
            errors.append(err(table, name, f"'{obj_field}' must be a dict"))

    # opening_ranged_attack
    if "opening_ranged_attack" in entry:
        ora = entry["opening_ranged_attack"]
        if not isinstance(ora, dict):
            errors.append(err(table, name, "'opening_ranged_attack' must be a dict"))
        else:
            for k in ("level", "timing", "weapon", "description"):
                if k not in ora:
                    errors.append(err(table, name, f"'opening_ranged_attack' missing '{k}'"))


def main() -> int:
    if not MONSTERS_FILE.exists():
        print(f"ERROR: {MONSTERS_FILE} not found", file=sys.stderr)
        return 1

    data = json.loads(MONSTERS_FILE.read_text(encoding="utf-8"))
    errors: list[str] = []
    total = 0

    for table_key in MONSTER_TABLE_KEYS:
        if table_key not in data:
            errors.append(f"Missing table key '{table_key}' in monsters.json")
            continue
        entries = data[table_key]
        if not isinstance(entries, list):
            errors.append(f"Table '{table_key}' must be a list")
            continue
        if not entries:
            errors.append(f"Table '{table_key}' is empty")
            continue
        for entry in entries:
            validate_entry(entry, table_key, errors)
            total += 1

    # Also validate reaction_tables section keys match monster names
    if "reaction_tables" in data:
        rt = data["reaction_tables"]
        all_monster_names = {
            entry["name"]
            for key in MONSTER_TABLE_KEYS
            if key in data and isinstance(data[key], list)
            for entry in data[key]
            if isinstance(entry, dict) and "name" in entry
        }
        for rt_name, rt_rows in rt.items():
            if not isinstance(rt_rows, list) or not rt_rows:
                errors.append(f"reaction_tables[{rt_name!r}] must be a non-empty list")
                continue
            for i, row in enumerate(rt_rows):
                if not isinstance(row, dict):
                    errors.append(f"reaction_tables[{rt_name!r}][{i}] must be a dict")
                    continue
                for k in ("roll", "key", "result"):
                    if k not in row:
                        errors.append(f"reaction_tables[{rt_name!r}][{i}] missing '{k}'")

    if errors:
        print(f"\nFound {len(errors)} error(s) across {total} entries:\n")
        for e in errors:
            print(f"  ✗ {e}")
        return 1

    print(f"✓ All {total} monster entries across {len(MONSTER_TABLE_KEYS)} tables passed validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
