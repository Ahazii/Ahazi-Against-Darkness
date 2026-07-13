from __future__ import annotations

import json
import hashlib
from pathlib import Path

from app.engine.combat import enemy_has_regeneration
from app.engine.combat_modifiers import enemy_has_magic_resistance, enemy_has_poison
from app.engine.reactions import lookup_reaction_row, resolve_reaction_source
from app.engine.reactions import REACTION_NAME_ALIASES
from app.schemas import EnemyState


MONSTERS_PATH = Path(__file__).resolve().parents[1] / "data" / "rules" / "monsters.json"

EXPECTED_MONSTER_STATS_SIGNATURE = "1764eb230614cc9b457b3dc299bd3c4c7a151ca014c9f3a36811c8973d769b2e"
EXPECTED_REACTION_ROWS_SIGNATURE = "91c145a924f592e93929ec8f1a1ccc24065cfe1f9e913763462f9a93ba8b49fe"
EXPECTED_MONSTER_TABLE_COUNT = 17
EXPECTED_MONSTER_ROW_COUNT = 100
EXPECTED_REACTION_TABLE_COUNT = 123
EXPECTED_REACTION_ROW_COUNT = 285


def _monster_rules() -> dict:
    return json.loads(MONSTERS_PATH.read_text(encoding="utf-8"))


def _monster_rows() -> list[tuple[str, dict]]:
    data = _monster_rules()
    rows: list[tuple[str, dict]] = []
    for category, entries in data.items():
        if category == "reaction_tables":
            continue
        rows.extend((category, entry) for entry in entries)
    return rows


def _signature(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _coerce_stat(value: object) -> int:
    """Return a usable integer from a monster stat (int or formula string)."""
    if isinstance(value, int):
        return max(1, value)
    try:
        return max(1, int(str(value)))
    except (ValueError, TypeError):
        return 1


def _monster_stats_snapshot(data: dict) -> dict:
    return {
        table: [
            {
                "name": row.get("name"),
                "level_delta": row.get("level_delta"),
                "count": row.get("count"),
                "life": row.get("life"),
                "attacks": row.get("attacks"),
                "tags": row.get("tags", []),
            }
            for row in rows
        ]
        for table, rows in data.items()
        if isinstance(rows, list)
    }


def test_monsters_json_exact_pdf_stat_snapshot_locked() -> None:
    data = _monster_rules()
    snapshot = _monster_stats_snapshot(data)
    assert len(snapshot) == EXPECTED_MONSTER_TABLE_COUNT
    assert sum(len(rows) for rows in snapshot.values()) == EXPECTED_MONSTER_ROW_COUNT
    assert _signature(snapshot) == EXPECTED_MONSTER_STATS_SIGNATURE


def test_monsters_json_exact_pdf_reaction_rows_locked() -> None:
    data = _monster_rules()
    reactions = data["reaction_tables"]
    assert len(reactions) == EXPECTED_REACTION_TABLE_COUNT
    assert sum(len(rows) for rows in reactions.values()) == EXPECTED_REACTION_ROW_COUNT
    assert _signature(reactions) == EXPECTED_REACTION_ROWS_SIGNATURE


def test_all_indexed_monsters_resolve_named_reaction_source() -> None:
    data = _monster_rules()
    reaction_tables = data["reaction_tables"]
    missing: list[str] = []
    for category, row in _monster_rows():
        enemy = EnemyState(
                id=row["name"].lower().replace(" ", "-"),
                name=row["name"],
                category="weird" if category.endswith("weird") else "boss" if category.endswith("boss") else category.split("_")[-1],
                level=5,
                life=_coerce_stat(row["life"]),
                max_life=_coerce_stat(row["life"]),
                attacks=_coerce_stat(row["attacks"]),
                tags=list(row.get("tags", [])),
            )
        source = resolve_reaction_source([enemy], reaction_tables)
        if not source.inline_rows:
            missing.append(row["name"])
            continue
        for roll in range(1, 7):
            assert lookup_reaction_row(source.inline_rows, roll), f"{row['name']} reaction table misses roll {roll}"
    assert not missing


def test_indexed_monsters_use_direct_named_reaction_tables() -> None:
    """Every indexed bestiary row should resolve through its own PDF reaction table."""
    data = _monster_rules()
    monster_names = {row["name"] for _, row in _monster_rows()}
    direct_named_tables = monster_names & set(data["reaction_tables"])
    alias_names = set(REACTION_NAME_ALIASES)

    assert direct_named_tables == monster_names
    assert alias_names == set()


def test_named_reaction_rows_match_extracted_pdf_examples() -> None:
    data = _monster_rules()
    reactions = data["reaction_tables"]

    assert [(row["roll"], row["key"], row.get("gold_per_foe")) for row in reactions["Goblins"]] == [
        ("1", "flee_if_outnumbered", None),
        ("2-3", "bribe", 5),
        ("4-6", "fight", None),
    ]
    assert [(row["roll"], row["key"], row.get("gold")) for row in reactions["Medusa"]] == [
        ("1", "bribe", None),
        ("2", "quest", None),
        ("3-5", "fight", None),
        ("6", "fight_to_death", None),
    ]
    assert reactions["Medusa"][0]["gold_dice"] == "6d6"
    assert [(row["roll"], row["key"]) for row in reactions["Cave Orcs"]] == [
        ("1-3", "buy_weapons"),
        ("4-6", "fight"),
    ]
    assert [(row["roll"], row["key"]) for row in reactions["Fungal Dragon"]] == [
        ("1-3", "quest"),
        ("4-6", "fight"),
    ]


def test_bestiary_rows_have_combat_special_metadata_wired() -> None:
    for category, row in _monster_rows():
        enemy = EnemyState(
            id=row["name"].lower().replace(" ", "-"),
            name=row["name"],
            category="weird" if category.endswith("weird") else "boss" if category.endswith("boss") else category.split("_")[-1],
            level=5,
            life=_coerce_stat(row["life"]),
            max_life=_coerce_stat(row["life"]),
            attacks=_coerce_stat(row["attacks"]),
            tags=list(row.get("tags", [])),
        )
        tags = {tag.lower() for tag in row.get("tags", [])}
        if "poison" in tags:
            assert enemy_has_poison(enemy), row["name"]
        if {"magic_resist", "caster", "dragon"} & tags:
            assert enemy_has_magic_resistance(enemy), row["name"]
        if "regeneration" in tags:
            assert enemy_has_regeneration(enemy), row["name"]
        if category.endswith("boss") or category == "boss":
            assert "boss" in tags or row["name"] == "Minotaur", row["name"]
        if category.endswith("vermin") or category == "vermin":
            assert "vermin" in tags, row["name"]
