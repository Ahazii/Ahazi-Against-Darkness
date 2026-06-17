"""Integration-style flow tests for Secrets gameplay."""
from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _engine() -> RandomDungeonEngine:
    root = Path(__file__).resolve().parents[1]
    return RandomDungeonEngine(_rules(), root / "assets")


def _member(cid: str, name: str, order: int, *, level: int = 3, life: int = 6, clues: int = 0) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=level,
        xp=0,
        gold=30,
        clues=clues,
        current_life=life,
        max_life=life,
        attack_bonus=1,
        defense_bonus=1,
        save_bonus=0,
        marching_order=order,
    )


def _enemy(eid: str, name: str, *, category: str = "boss", level: int = 4, life: int = 6) -> EnemyState:
    return EnemyState(
        id=eid,
        name=name,
        category=category,
        level=level,
        life=life,
        max_life=life,
        attacks=1,
        tags=[],
    )


def _session(
    *,
    party: list[PartyMemberState],
    tile: TileState | None = None,
    mode: str = "exploration",
) -> SessionState:
    current = tile or TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Hall",
        description="A room",
    )
    return SessionState(
        id="s1",
        party_id="p1",
        adventure_id="a1",
        adventure_type="random",
        mode=mode,
        party=party,
        map_state=MapState(tiles=[current], current_tile_id=current.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_reveal_secret_uses_selected_discoverer_and_awards_xp_roll_credit() -> None:
    engine = _engine()
    clue_holder = _member("h1", "Halvar", 1, clues=3)
    discoverer = _member("h2", "Brynn", 2, clues=0)
    session = _session(party=[clue_holder, discoverer])
    session.clues_found = 3

    engine.advance(
        session,
        "reveal_secret_with_clues",
        character_id="h2",
        secret_id="weakness_of_a_foe",
        show_rolls=False,
    )

    assert "weakness_of_a_foe" in discoverer.secrets
    assert session.clues_found == 0
    assert session.xp_rolls_pending == 1
    assert any("brynn reveals weakness of a foe" in line.lower() for line in session.log)


def test_weakness_secret_flow_reveals_then_targets_major_foe() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1, clues=3)
    boss = _enemy("b1", "Chaos Champion", category="boss")
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Boss Room",
        description="A threat",
        enemies=[boss],
        initial_enemy_count=1,
    )
    session = _session(party=[hero], tile=tile, mode="exploration")
    session.clues_found = 3

    engine.advance(
        session,
        "reveal_secret_with_clues",
        character_id="h1",
        secret_id="weakness_of_a_foe",
        show_rolls=False,
    )
    engine.advance(session, "start_combat", show_rolls=False)
    engine.advance(
        session,
        "use_secret",
        character_id="h1",
        secret_id="weakness_of_a_foe",
        foe_id="b1",
        show_rolls=False,
    )

    assert session.secret_weakness_foe_id == "b1"
    assert "weakness_of_a_foe" not in hero.secrets
    assert any("uses weakness of a foe" in line.lower() for line in session.log)


def test_deal_with_a_foe_requires_eligible_target_then_ends_encounter() -> None:
    engine = _engine()
    hero = _member("h1", "Halvar", 1)
    hero.secrets = ["deal_with_a_foe"]
    vermin = _enemy("v1", "Rats", category="vermin", level=1, life=2)
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Nest",
        description="Skittering",
        enemies=[vermin],
        initial_enemy_count=1,
    )
    session = _session(party=[hero], tile=tile, mode="combat")

    engine.advance(
        session,
        "use_secret",
        character_id="h1",
        secret_id="deal_with_a_foe",
        foe_id="v1",
        show_rolls=False,
    )
    assert "deal_with_a_foe" in hero.secrets
    assert session.mode == "combat"

    minion = _enemy("m1", "Cultists", category="minions", level=2, life=3)
    tile.enemies = [minion]
    tile.initial_enemy_count = 1
    engine.advance(
        session,
        "use_secret",
        character_id="h1",
        secret_id="deal_with_a_foe",
        foe_id="m1",
        show_rolls=False,
    )

    assert "deal_with_a_foe" not in hero.secrets
    assert session.mode == "exploration"
    assert not any(enemy.life > 0 for enemy in tile.enemies)
    assert any("uses deal with a foe on cultists" in line.lower() for line in session.log)


def test_fallen_transfer_blocks_other_actions_until_resolved() -> None:
    engine = _engine()
    fallen = _member("h1", "Halvar", 1, life=0, clues=2)
    fallen.current_life = 0
    heir = _member("h2", "Brynn", 2)
    session = _session(party=[fallen, heir], mode="exploration")

    before_count = len(session.log)
    engine.advance(session, "search", show_rolls=False)

    assert session.pending_fallen_transfer is not None
    assert session.pending_fallen_transfer.kind == "clues"
    assert len(session.log) > before_count
    assert any("choose a living hero to inherit their clues" in line.lower() for line in session.log)

    engine.advance(
        session,
        "resolve_fallen_transfer",
        target_character_id="h2",
        fallen_transfer_kind="clues",
        show_rolls=False,
    )

    assert session.pending_fallen_transfer is None
    assert heir.clues == 2
    assert fallen.clues == 0
