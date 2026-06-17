from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.engine.tier_advancement import TIER_ENTRY
from app.main import app


ECONOMY_REWARD_TABLE_KEYS = [
    "experience_classical_table",
    "experience_slow_sure_table",
    "experience_old_school_table",
    "experience_slower_table",
    "economy_services_table",
    "equipment_shop_table",
    "treasure_table",
    "hidden_treasure_table",
    "dungeon_magic_treasure_table",
    "caverns_special_item_table",
    "fungal_grottoes_rare_item_table",
    "fungal_grottoes_rare_mushroom_table",
    "quest_table",
    "epic_rewards_table",
    "tier_training_costs_table",
]

EXPECTED_ECONOMY_REWARD_SIGNATURE = "cb268e704419ef014cb65103cd0f77440cf5eef37232357f57cd03d20541933e"
EXPECTED_ECONOMY_REWARD_ROW_COUNTS = {
    "experience_classical_table": 5,
    "experience_slow_sure_table": 1,
    "experience_old_school_table": 4,
    "experience_slower_table": 2,
    "economy_services_table": 3,
    "equipment_shop_table": 40,
    "treasure_table": 7,
    "hidden_treasure_table": 4,
    "dungeon_magic_treasure_table": 6,
    "caverns_special_item_table": 6,
    "fungal_grottoes_rare_item_table": 6,
    "fungal_grottoes_rare_mushroom_table": 6,
    "quest_table": 6,
    "epic_rewards_table": 6,
    "tier_training_costs_table": 4,
}


def _rules_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "rules"


def _tables_payload() -> dict:
    return TestClient(app).get("/api/rules/tables").json()


def _signature(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_economy_xp_reward_table_family_exact_api_snapshot_locked() -> None:
    payload = _tables_payload()
    family = {key: payload[key] for key in ECONOMY_REWARD_TABLE_KEYS}

    assert {key: len(rows) for key, rows in family.items()} == EXPECTED_ECONOMY_REWARD_ROW_COUNTS
    assert _signature(family) == EXPECTED_ECONOMY_REWARD_SIGNATURE


def test_economy_xp_reward_table_family_rows_keep_source_pages() -> None:
    payload = _tables_payload()
    for key in ECONOMY_REWARD_TABLE_KEYS:
        rows = payload[key]
        assert rows, key
        assert all(str(row.get("source_page", "")).strip() for row in rows), key


def test_equipment_shop_api_rows_match_locked_shop_catalog() -> None:
    shop = json.loads((_rules_dir() / "equipment_shop.json").read_text(encoding="utf-8"))
    payload_rows = _tables_payload()["equipment_shop_table"]

    expected = [
        {
            "roll": str(index),
            "result": f"{item['name']}: {int(item['price_gp'])}gp buy; {int(item['price_gp']) // 2}gp sell (half list).",
            "source_page": item.get("source_page", shop.get("source_page", 81)),
        }
        for index, item in enumerate(shop["items"], start=1)
    ]
    expected.append(
        {
            "roll": "sell",
            "result": (
                "Sell equipment at half list price unless a fixed resale value is listed. "
                "Potions/rings 50gp; wands/scrolls/staves 100gp per spell; "
                "other magic d6×d6 gp; gems +20% for dwarves."
            ),
            "source_page": 19,
        }
    )

    assert payload_rows == expected


def test_tier_training_api_rows_match_forsaken_depths_entry_catalog() -> None:
    rows = _tables_payload()["tier_training_costs_table"]
    expected = [
        {
            "tier": tier.title(),
            "min_level": str(spec["min_level"]),
            "gold": str(spec["gold"]),
            "banked_xp": (
                f"0, or {spec.get('xp_alt', 0)} instead of gold"
                if tier == "expert" and spec.get("xp_alt")
                else str(spec.get("xp", 0))
            ),
            "notes": (
                "Unlocks Expert advancement; learning an Expert skill later spends a separate XP roll."
                if tier == "expert"
                else "Required before advancing into this tier."
            ),
            "source_page": 9,
        }
        for tier, spec in TIER_ENTRY.items()
    ]

    assert rows == expected
