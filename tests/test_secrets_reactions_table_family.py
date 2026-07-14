from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.engine.reactions import lookup_reaction_row
from app.main import app
from app.rules.repository import RulesRepository


SECRETS_REACTIONS_TABLE_KEYS = [
    "clue_spends_table",
    "secrets_table",
    "default_reaction_table",
    "vermin_reaction_table",
    "minion_reaction_table",
    "major_reaction_table",
]

EXPECTED_SECRETS_REACTIONS_SIGNATURE = "3e81c2c2aad51263410f55ba76354c3c6b94a794cf1537ce9a5e822d70c3ef6d"
EXPECTED_SECRETS_REACTIONS_ROW_COUNTS = {
    "clue_spends_table": 7,
    "secrets_table": 19,
    "default_reaction_table": 3,
    "vermin_reaction_table": 2,
    "minion_reaction_table": 3,
    "major_reaction_table": 3,
    "named_monster_reaction_tables": 123,
}

EXPECTED_SECRET_IDS = {
    "weakness_of_a_foe",
    "deal_with_a_foe",
    "hidden_treasure_location",
    "magic_item_location",
    "true_name_spiritual_entity",
    "new_spell",
    "magical_power_increase",
    "scroll_location",
    "potion_recipe",
    "terrifying_secret",
    "big_money_buyer",
    "enemy_in_dungeon",
    "prisoner",
    "dragonslayer_bloodline",
    "secret_diet",
    "someone_imprisoned",
    "chaos_fanatics",
    "corridor_leads",
    "yummy_meal",
}

EXPECTED_CLUE_SPEND_IDS = {
    "reveal_secret",
    "trade_information",
    "illusion_door",
    "lever_door",
    "spell_learning",
    "captive_hideout",
    "special_discovery",
}


def _rules_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "rules"


def _repo() -> RulesRepository:
    packaged = _rules_dir()
    return RulesRepository(packaged, packaged / "_override")


def _tables_payload() -> dict:
    return TestClient(app).get("/api/rules/tables").json()


def _monster_rules() -> dict:
    return json.loads((_rules_dir() / "monsters.json").read_text(encoding="utf-8"))


def _signature(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _family_snapshot() -> dict:
    payload = _tables_payload()
    family = {key: payload[key] for key in SECRETS_REACTIONS_TABLE_KEYS}
    family["named_monster_reaction_tables"] = _monster_rules()["reaction_tables"]
    return family


def test_secrets_clues_reactions_encounter_decisions_family_exact_snapshot_locked() -> None:
    family = _family_snapshot()

    row_counts = {key: len(rows) for key, rows in family.items()}
    assert row_counts == EXPECTED_SECRETS_REACTIONS_ROW_COUNTS
    assert sum(len(rows) for rows in family["named_monster_reaction_tables"].values()) == 285
    assert _signature(family) == EXPECTED_SECRETS_REACTIONS_SIGNATURE


def test_secrets_clues_reactions_family_rows_keep_source_pages() -> None:
    family = _family_snapshot()

    for key in SECRETS_REACTIONS_TABLE_KEYS:
        rows = family[key]
        assert rows, key
        assert all(str(row.get("source_page", "")).strip() for row in rows), key

    for table_name, rows in family["named_monster_reaction_tables"].items():
        assert rows, table_name
        for row in rows:
            if row.get("key") in {"puzzle", "trade_information", "magic_challenge"}:
                assert str(row.get("source_page", "")).strip(), f"{table_name} {row['key']}"


def test_clue_secret_and_category_reaction_api_rows_match_packaged_catalog_rows() -> None:
    packaged_tables = _repo().dungeon_tables()
    payload = _tables_payload()

    for key in SECRETS_REACTIONS_TABLE_KEYS:
        assert payload[key] == packaged_tables[key]


def test_secret_and_clue_spend_catalogs_keep_expected_pdf_keys() -> None:
    payload = _tables_payload()

    secrets = payload["secrets_table"]
    clue_spends = payload["clue_spends_table"]

    assert {row["key"] for row in secrets} == EXPECTED_SECRET_IDS
    assert all(row.get("implementation") == "wired" for row in secrets)
    assert {row["key"] for row in clue_spends} == EXPECTED_CLUE_SPEND_IDS


def test_category_reaction_tables_keep_pdf_decision_rows() -> None:
    payload = _tables_payload()

    assert [(row["roll"], row["key"]) for row in payload["default_reaction_table"]] == [
        ("1", "flee"),
        ("2-4", "bribe"),
        ("5-6", "fight"),
    ]
    assert [(row["roll"], row["key"]) for row in payload["vermin_reaction_table"]] == [
        ("1-3", "flee"),
        ("4-6", "fight"),
    ]
    assert [(row["roll"], row["key"]) for row in payload["minion_reaction_table"]] == [
        ("1", "capture"),
        ("2-3", "bribe"),
        ("4-6", "fight"),
    ]
    assert [(row["roll"], row["key"]) for row in payload["major_reaction_table"]] == [
        ("1", "bribe"),
        ("2-5", "fight"),
        ("6", "fight_to_death"),
    ]


def test_named_monster_reaction_tables_cover_every_d6_roll() -> None:
    reactions = _monster_rules()["reaction_tables"]

    for table_name, rows in reactions.items():
        for roll in range(1, 7):
            assert lookup_reaction_row(rows, roll), f"{table_name} reaction table misses roll {roll}"


def test_encounter_decision_reaction_keys_remain_available() -> None:
    reactions = _monster_rules()["reaction_tables"]
    keyed_rows = {
        (table_name, row["key"])
        for table_name, rows in reactions.items()
        for row in rows
        if row.get("key") in {"puzzle", "trade_information", "magic_challenge"}
    }

    assert ("Kobolds", "puzzle") in keyed_rows
    assert ("Cultists", "trade_information") in keyed_rows
    assert ("Necromancer", "magic_challenge") in keyed_rows
    assert any(row["key"] == "capture" for row in _tables_payload()["minion_reaction_table"])
