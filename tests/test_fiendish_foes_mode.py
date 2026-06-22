from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.engine.fiendish_foes import (
    migrate_legacy_fiendish_foes_mode,
    normalize_fiendish_foes_enabled,
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
        "mode": "exploration",
        "party": [_member(character_id="a", level=3), _member(character_id="b", level=3)],
        "map_state": {
            "width": 31,
            "height": 31,
            "tiles": [],
            "current_tile_id": "t1",
        },
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "fiendish_foes_enabled": True,
        "environment": "dungeon",
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


def test_normalize_fiendish_foes_enabled_defaults_on() -> None:
    assert normalize_fiendish_foes_enabled(None) is True
    assert normalize_fiendish_foes_enabled(False) is False
    assert migrate_legacy_fiendish_foes_mode("off") is False
    assert migrate_legacy_fiendish_foes_mode("mixed") is True
    assert migrate_legacy_fiendish_foes_mode("always") is True


def test_resolve_use_fiendish_foes_table_disabled_or_ineligible() -> None:
    assert resolve_use_fiendish_foes_table(False) == (False, None)
    assert resolve_use_fiendish_foes_table(True, eligible=False) == (False, None)
    use, roll = resolve_use_fiendish_foes_table(True, eligible=True, roll_fn=lambda: 3)
    assert use is False and roll == 3
    use, roll = resolve_use_fiendish_foes_table(True, eligible=True, roll_fn=lambda: 4)
    assert use is True and roll == 4


def test_resolve_monster_table_key_caverns_fiendish() -> None:
    engine = _engine()
    session = _session(environment="caverns", fiendish_foes_enabled=True)
    monsters = engine.rules.monsters()
    key = resolve_monster_table_key(monsters, session, "vermin", use_fiendish=True)
    assert key == "fiendish_foes_vermin"


def test_create_session_allows_low_level_party_when_fiendish_enabled() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=1), _member(character_id="b", level=2)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_enabled=True)
    assert session.fiendish_foes_enabled is True
    assert any("standard tables until 2+ heroes reach L3" in line for line in session.log)


def test_create_session_logs_fiendish_when_eligible() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=3), _member(character_id="b", level=4)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_enabled=True)
    assert session.fiendish_foes_enabled is True
    assert any("d6 1-3 standard, 4-6 fiendish" in line for line in session.log)


def test_roll_enemy_uses_fiendish_when_enabled_and_roll_high() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=3), _member(character_id="b", level=3)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_enabled=True)
    fiendish_template = engine.rules.monsters()["fiendish_foes_vermin"][0]
    with patch("app.engine.fiendish_foes.roll_d6", return_value=4), patch(
        "app.engine.random_dungeon.random.choice", return_value=fiendish_template
    ):
        enemies = engine._roll_enemy(session, "vermin", hcl=3)
    assert enemies
    assert "fiendish" in enemies[0].tags


def test_roll_enemy_uses_standard_when_fiendish_disabled() -> None:
    engine = _engine()
    party = [_member(character_id="a", level=3), _member(character_id="b", level=3)]
    session = engine.create_session("s1", "p1", party, fiendish_foes_enabled=False)
    standard = engine.rules.monsters()["vermin"][0]
    with patch("app.engine.random_dungeon.random.choice", return_value=standard) as choose:
        engine._roll_enemy(session, "vermin", hcl=3)
    assert choose.called


def test_session_migrates_legacy_fiendish_foes_mode() -> None:
    session = SessionState.model_validate(
        {
            "id": "s1",
            "party_id": "p1",
            "adventure_id": "random",
            "adventure_type": "random",
            "mode": "exploration",
            "party": [_member(character_id="a")],
            "map_state": {"width": 31, "height": 31, "tiles": [], "current_tile_id": "t1"},
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "fiendish_foes_mode": "mixed",
        }
    )
    assert session.fiendish_foes_enabled is True
