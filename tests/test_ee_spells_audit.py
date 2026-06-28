"""EE Magic chapter (PDF pp.72–84) — table rows + cast resolver coverage."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.engine import spells
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _caster(*, class_id: str, spell_list: list[str], current_life: int = 4, max_life: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id="c1",
        name="Caster",
        class_id=class_id,
        class_name=class_id.title(),
        level=4,
        xp=0,
        gold=0,
        current_life=current_life,
        max_life=max_life,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=spell_list,
    )


def _session(*, terrain: str = "indoor") -> SessionState:
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="Room",
        terrain=terrain,
    )
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=[],
        map_state=MapState(tiles=[tile], current_tile_id="t1"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def _foe() -> EnemyState:
    return EnemyState(id="e1", name="Goblin", category="minions", level=3, life=1, max_life=1)


EE_BASIC_SPELLS = [
    "Blessing",
    "Escape",
    "Lightning",
    "Fireball",
    "Protection",
    "Sleep",
    "Healing prayer",
]

EE_DRUID_SPELLS = [
    "Disperse Vermin",
    "Summon Beast",
    "Water Jet",
    "Bear Form",
    "Warp Wood",
    "Barkskin",
    "Lightning Strike",
    "Spiderweb",
    "Entangle",
    "Subdual",
    "Forest Pathway",
    "Alter Weather",
]

EE_ILLUSIONIST_SPELLS = [
    "Illusionary Armor",
    "Illusionary Mirror Image",
    "Illusionary Servant",
    "Disbelief",
    "Phantasmal Binding",
    "Illusionary Fog",
    "Glamour Mask",
    "Shadow Strike",
    "Specter Swarm",
    "Mirage of Fortune",
    "Illusionary Banquet",
    "Illusionary Sword",
]

EE_OUTDOOR_ONLY = frozenset({"Forest Pathway", "Alter Weather", "Glamour Mask", "Illusionary Banquet"})


@pytest.mark.parametrize("spell_name", EE_BASIC_SPELLS)
def test_basic_spell_resolves_without_unknown(spell_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    class_id = "cleric" if spell_name == "Healing prayer" else "wizard"
    life = 2 if spell_name == "Healing prayer" else 4
    caster = _caster(class_id=class_id, spell_list=[spell_name], current_life=life)
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    outcome = spells.resolve_spell_cast(
        spell_name,
        caster,
        [caster],
        [_foe()] if spell_name not in {"Escape", "Blessing", "Protection", "Healing prayer"} else [],
        show_rolls=False,
        target_character_id=caster.character_id if spell_name in {"Blessing", "Protection", "Healing prayer"} else None,
    )
    assert not any("Unknown spell" in line for line in outcome.log)
    if spell_name == "Healing prayer":
        assert outcome.party[0].current_life > life or any("full Life" in line for line in outcome.log)
    else:
        assert outcome.spell_consumed is True


@pytest.mark.parametrize("spell_name", EE_DRUID_SPELLS)
def test_druid_spell_resolves_without_unknown(spell_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    caster = _caster(class_id="druid", spell_list=[spell_name])
    terrain = {
        "Entangle": "jungle",
        "Forest Pathway": "forest",
    }.get(spell_name, "outdoor" if spell_name in EE_OUTDOOR_ONLY else "indoor")
    session = _session(terrain=terrain)
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    outcome = spells.resolve_spell_cast(
        spell_name,
        caster,
        [caster],
        [_foe()] if spell_name not in {"Summon Beast", "Forest Pathway", "Alter Weather", "Bear Form"} else [],
        show_rolls=False,
        session=session,
        terrain=terrain,
        target_character_id=caster.character_id if spell_name == "Bear Form" else None,
    )
    assert not any("Unknown spell" in line for line in outcome.log)
    context_blocked = spell_name in {
        "Disperse Vermin",
        "Water Jet",
        "Warp Wood",
        "Lightning Strike",
    } or (spell_name == "Entangle" and terrain not in {"forest", "swamp", "jungle"})
    if context_blocked or (spell_name in EE_OUTDOOR_ONLY and terrain == "indoor"):
        assert outcome.spell_consumed is False
    else:
        assert outcome.spell_consumed is True


@pytest.mark.parametrize("spell_name", EE_ILLUSIONIST_SPELLS)
def test_illusionist_spell_resolves_without_unknown(spell_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    caster = _caster(class_id="illusionist", spell_list=[spell_name])
    session = _session(terrain="outdoor" if spell_name in EE_OUTDOOR_ONLY else "indoor")
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    outcome = spells.resolve_spell_cast(
        spell_name,
        caster,
        [caster],
        [_foe()] if spell_name not in {"Illusionary Servant", "Glamour Mask", "Illusionary Banquet"} else [],
        show_rolls=False,
        session=session,
        terrain=session.map_state.tiles[0].terrain or "indoor",
    )
    assert not any("Unknown spell" in line for line in outcome.log)
    if spell_name in EE_OUTDOOR_ONLY and (session.map_state.tiles[0].terrain or "indoor") == "indoor":
        assert outcome.spell_consumed is False
    else:
        assert outcome.spell_consumed is True


def test_ee_spell_tables_list_all_castable_spells() -> None:
    tables = _rules().dungeon_tables()
    basic = [row["spell"] for row in tables["basic_spells_table"]]
    druid = [row["spell"] for row in tables["druid_spells_table"]]
    illusionist = [row["spell"] for row in tables["illusionist_spells_table"]]
    assert basic == EE_BASIC_SPELLS
    assert druid == EE_DRUID_SPELLS
    assert illusionist == EE_ILLUSIONIST_SPELLS


def test_outdoor_only_spells_block_indoor_cast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))
    for spell_name in ("Forest Pathway", "Alter Weather"):
        caster = _caster(class_id="druid", spell_list=[spell_name])
        outcome = spells.resolve_spell_cast(
            spell_name,
            caster,
            [caster],
            [],
            show_rolls=False,
            terrain="indoor",
        )
        assert outcome.spell_consumed is False
        assert any("outdoor" in line.lower() for line in outcome.log)
