"""Regression tests for clue_spends_table (EE p.24, p.32, p.102, p.107–109, p.123)."""
from __future__ import annotations

import json
from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import MapState, PartyMemberState, SessionState, TileState

# Each catalog row maps to an engine advance action (or reaction flow for trade_information).
CLUE_SPEND_ENGINE_ACTIONS: dict[str, str | None] = {
    "reveal_secret": "reveal_secret_with_clues",
    "trade_information": None,
    "illusion_door": "spend_clues_on_door",
    "lever_door": "spend_clues_on_door",
    "spell_learning": "learn_spell_with_clues",
    "captive_hideout": "find_captive_hideout",
    "special_discovery": "claim_kerrak_dar_hoard",
}


def _clue_spends() -> list[dict]:
    path = Path(__file__).resolve().parents[1] / "data" / "rules" / "dungeon_tables.json"
    return json.loads(path.read_text(encoding="utf-8"))["clue_spends_table"]


def _engine() -> RandomDungeonEngine:
    root = Path(__file__).resolve().parents[1]
    repo = RulesRepository(root / "data" / "rules", root / "data" / "rules" / "_override")
    return RandomDungeonEngine(repo, root / "assets")


def test_clue_spends_table_rows_match_pdf_catalog() -> None:
    rows = _clue_spends()
    assert [row["key"] for row in rows] == list(CLUE_SPEND_ENGINE_ACTIONS.keys())
    assert all(str(row.get("source_page", "")).strip() for row in rows)
    assert all(str(row.get("result", "")).strip() for row in rows)


def test_clue_spends_table_documents_clue_costs() -> None:
    by_key = {row["key"]: row for row in _clue_spends()}

    assert "3 held Clues" in by_key["reveal_secret"]["result"]
    assert "100gp" in by_key["trade_information"]["result"]
    assert "3 held Clues" in by_key["illusion_door"]["result"]
    assert "1 held Clue" in by_key["lever_door"]["result"]
    assert "3 held Clues" in by_key["spell_learning"]["result"]
    assert "3 held Clues" in by_key["captive_hideout"]["result"]
    assert "Kerrak Dar" in by_key["special_discovery"]["result"]


def test_clue_spend_engine_actions_are_registered() -> None:
    from typing import get_args

    from app.schemas import SessionAction

    registered = set(get_args(SessionAction.model_fields["action"].annotation))
    for key, action in CLUE_SPEND_ENGINE_ACTIONS.items():
        if action is None:
            continue
        assert action in registered, f"{key} -> {action}"


def test_special_discovery_kerrak_dar_hoard_spends_one_clue(monkeypatch) -> None:
    engine = _engine()
    hero = PartyMemberState(
        character_id="h1",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        clues=1,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        statuses=["Kerrak Dar Hoard"],
    )
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Hall",
        description="Hall",
    )
    session = SessionState(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        mode="exploration",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        clues_found=1,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    engine.advance(session, "claim_kerrak_dar_hoard", show_rolls=False)

    assert hero.clues == 0
    assert session.clues_found == 0
    assert hero.gold == 200
    assert tile.treasure_gold == 300
    assert "Kerrak Dar Hoard" not in hero.statuses
    assert any("Kerrak Dar's hoard found" in line for line in session.log)
