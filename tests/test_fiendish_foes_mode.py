from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.engine.fiendish_foes import (
    normalize_fiendish_foes_mode,
    party_fiendish_foes_eligible,
    resolve_monster_table_key,
    resolve_use_fiendish_foes_table,
)
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import PartyMemberState, SessionState

ROOT = Path(__file__).resolve().parents[1]


def _member(*, character_id: str, level: int = 1) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=f"Hero {character_id}",
        class_id="warrior",
        class_name="Warrior",
        level=level,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )


def _engine() -> RandomDungeonEngine:
    rules_dir = ROOT / "data" / "rules"
    return RandomDungeonEngine(
        rules=RulesRepository(rules_dir, rules_dir / "_override"),
        asset_dir=Path(),
    )


def _session(**overrides) -> SessionState:
    data = {
        "id": "s1",
        "party_id": "p1",
        "adventure_id": "random",
        "adventure_type": "random",
        "party": [],
        "map_state": {"width": 31, "height": 31, "tiles": [], "current_tile_id": "t1"},
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "environment": "caverns",
        "fiendish_foes_mode": "always",
    }
    data.update(overrides)
    return SessionState.model_validate(data)


def test_party_fiendish_foes_eligible_requires_two_l3_pdf_p180() -> None:
    assert not party_fiendish_foes_eligible([_member(character_id="a", level=3)])
    assert not party_fiendish_foes_eligible(
        [_member(character_id="a", level=3), _member(character_id="b", level=2)]
    )
    assert party_fiendish_foes_eligible(
        [_member(character_id="a", level=3), _member(character_id="b", level=3)]
    )


def test_normalize_fiendish_foes_mode() -> None:
    assert normalize_fiendish_foes_mode("always") == "always"
    assert normalize_fiendish_foes_mode("mixed") == "mixed"
    assert normalize_fiendish_foes_mode("bogus") == "off"
    assert normalize_fiendish_foes_mode(None) == "off"


def test_resolve_use_fiendish_foes_table_mixed_pdf_p180() -> None:
    assert resolve_use_fiendish_foes_table("off") == (False, None)
    assert resolve_use_fiendish_foes_table("always") == (True, None)
    use, roll = resolve_use_fiendish_foes_table("mixed", roll_fn=lambda: 3)
    assert use is False and roll == 3
    use, roll = resolve_use_fiendish_foes_table("mixed", roll_fn=lambda: 4)
    assert use is True and roll == 4


def test_resolve_monster_table_key_fiendish_overrides_environment() -> None:
    rules_dir = ROOT / "data" / "rules"
    monsters = RulesRepository(rules_dir, rules_dir / "_override").monsters()
    session = _session(environment="caverns", fiendish_foes_mode="always")
    key = resolve_monster_table_key(monsters, session, "vermin", use_fiendish=True)
    assert key == "fiendish_foes_vermin"
    key = resolve_monster_table_key(monsters, session, "vermin", use_fiendish=False)
    assert key == "caverns_vermin"


def test_create_session_rejects_fiendish_when_ineligible() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=2), _member(character_id="b", level=2)]
    with pytest.raises(ValueError, match="2\\+ heroes at Level 3"):
        engine.create_session("s1", "p1", party, fiendish_foes_mode="always")


def test_create_session_fiendish_always_logs_pdf_mode() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=3), _member(character_id="b", level=4)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_mode="always")
    assert session.fiendish_foes_mode == "always"
    assert any("Fiendish Foes replace standard" in line for line in session.log)


def test_roll_enemy_always_uses_fiendish_table_and_tags() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=3), _member(character_id="b", level=3)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_mode="always")
    with patch("app.engine.random_dungeon.random.choice") as choose:
        choose.return_value = engine.rules.monsters()["fiendish_foes_vermin"][0]
        enemies = engine._roll_enemy(session, "vermin", hcl=3)
    assert enemies[0].name == "Fiendish Spiders"
    assert "fiendish" in enemies[0].tags


def test_roll_enemy_mixed_mode_respects_d6_pdf_p180() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=3), _member(character_id="b", level=3)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_mode="mixed")
    fiendish_template = engine.rules.monsters()["fiendish_foes_vermin"][0]
    standard_template = engine.rules.monsters()["vermin"][0]
    with patch("app.engine.fiendish_foes.roll_d6", return_value=4), patch(
        "app.engine.random_dungeon.random.choice", return_value=fiendish_template
    ):
        fiendish = engine._roll_enemy(session, "vermin", hcl=3)
    assert fiendish[0].name == "Fiendish Spiders"
    with patch("app.engine.fiendish_foes.roll_d6", return_value=2), patch(
        "app.engine.random_dungeon.random.choice", return_value=standard_template
    ):
        standard = engine._roll_enemy(session, "vermin", hcl=3)
    assert standard[0].name != "Fiendish Spiders"
    assert "fiendish" not in standard[0].tags


def test_fiendish_treasure_after_fiendish_spawn() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=3), _member(character_id="b", level=3)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_mode="always")
    tile = session.map_state.tiles[0]
    with patch("app.engine.random_dungeon.random.choice") as choose:
        choose.return_value = engine.rules.monsters()["fiendish_foes_vermin"][0]
        tile.enemies = engine._roll_enemy(session, "vermin", hcl=3)
    with patch("app.engine.dungeon_table_roller.roll_d6", return_value=6):
        outcome = engine._roll_treasure(session)
    assert "Fiendish Foes treasure roll" in " ".join(outcome.log)
