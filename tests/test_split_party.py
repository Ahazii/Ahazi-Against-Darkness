from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.split_party import (
    combat_party,
    detach_heroes,
    mixed_encounter,
    present_party,
    reattach_heroes,
    split_enemy_groups,
    split_party_ranks,
    stealth_modifier,
    wandering_check_detached_groups,
)
from app.rules.repository import RulesRepository
from app.schemas import DetachedGroupState, EnemyState, MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def _member(cid: str, name: str, order: int) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=name,
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=order,
    )


def _druid(cid: str = "d", name: str = "Druid", order: int = 2, level: int = 10) -> PartyMemberState:
    member = _member(cid, name, order)
    member.class_id = "druid"
    member.class_name = "Druid"
    member.level = level
    return member


def _session(*, party: list[PartyMemberState], current: str = "t1", tiles: list[TileState] | None = None) -> SessionState:
    tile_list = tiles or [
        TileState(id="t1", x=0, y=0, tile_key="11", tile_type="room", title="Room A", description="A"),
        TileState(id="t2", x=1, y=0, tile_key="12", tile_type="room", title="Room B", description="B"),
    ]
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=party,
        map_state=MapState(tiles=tile_list, current_tile_id=current),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_detach_and_present_party() -> None:
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2), _member("c", "Gamma", 3)]
    session = _session(party=party)
    logs = detach_heroes(session, ["b"], reason="guard")
    assert any("Beta" in line for line in logs)
    assert len(present_party(session, "t1")) == 2
    assert len(present_party(session, "t2")) == 2


def test_reattach_on_same_tile() -> None:
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2)]
    session = _session(party=party)
    detach_heroes(session, ["b"])
    logs = reattach_heroes(session, ["b"])
    assert any("rejoin" in line.lower() for line in logs)
    assert len(present_party(session)) == 2
    assert not session.detached_groups


def test_mixed_encounter_splits_ranks() -> None:
    party = [_member("a", "A", 1), _member("b", "B", 2), _member("c", "C", 3), _member("d", "D", 4)]
    enemies = [
        EnemyState(id="boss", name="Ogre", category="boss", level=6, life=8, max_life=8),
        EnemyState(id="m1", name="Goblin", category="minions", level=3, life=2, max_life=2),
    ]
    assert mixed_encounter(enemies)
    front, rear = split_party_ranks(party)
    major, minor = split_enemy_groups(enemies)
    assert len(front) == 2
    assert len(rear) == 2
    assert len(major) == 1
    assert len(minor) == 1


def test_detached_wandering_roll(monkeypatch) -> None:
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2)]
    session = _session(party=party)
    session.detached_groups = [DetachedGroupState(tile_id="t2", character_ids=["b"], reason="guard")]
    monkeypatch.setattr("app.engine.split_party.roll_d6", lambda: 1)
    triggered, logs = wandering_check_detached_groups(session, show_rolls=True, exclude_tile_id="t1")
    assert triggered == ["t2"]
    assert logs


def test_call_of_the_wild_detaches_l10_druid_and_blocks_actions(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    warrior = _member("a", "Alpha", 1)
    druid = _druid("d", "Oak", 2)
    session = _session(party=[warrior, druid])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)

    engine.advance(session, "call_of_the_wild", character_id="d", show_rolls=True)

    assert session.druid_call_of_wild_turns == {"d": 2}
    assert session.druid_call_of_wild_used == ["d"]
    assert any(group.reason == "call_of_the_wild" and group.character_ids == ["d"] for group in session.detached_groups)
    assert [member.character_id for member in present_party(session)] == ["a"]
    assert [member.character_id for member in combat_party(session)] == ["a"]
    assert any("Call of the Wild duration" in entry for entry in session.log)


def test_call_of_the_wild_countdown_blocks_then_allows_rejoin(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    warrior = _member("a", "Alpha", 1)
    druid = _druid("d", "Oak", 2)
    session = _session(party=[warrior, druid])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    engine.advance(session, "call_of_the_wild", character_id="d", show_rolls=False)

    engine.advance(session, "reattach_heroes", detached_character_ids=["d"])
    assert session.detached_groups
    assert any("must finish Call of the Wild" in entry for entry in session.log)

    engine._advance_call_of_the_wild(session)
    assert session.druid_call_of_wild_turns == {"d": 1}
    engine._advance_call_of_the_wild(session)
    assert session.druid_call_of_wild_turns == {}
    assert any("may now rejoin" in entry for entry in session.log)

    engine.advance(session, "reattach_heroes", detached_character_ids=["d"])
    assert not session.detached_groups
    assert [member.character_id for member in present_party(session)] == ["a", "d"]


def test_call_of_the_wild_group_does_not_roll_detached_wanderers(monkeypatch) -> None:
    warrior = _member("a", "Alpha", 1)
    druid = _druid("d", "Oak", 2)
    session = _session(party=[warrior, druid])
    session.detached_groups = [DetachedGroupState(tile_id="t1", character_ids=["d"], reason="call_of_the_wild")]
    session.druid_call_of_wild_turns = {"d": 1}
    monkeypatch.setattr("app.engine.split_party.roll_d6", lambda: 1)

    triggered, logs = wandering_check_detached_groups(session, show_rolls=True)

    assert triggered == []
    assert logs == []


def test_combat_party_includes_detached_on_same_tile() -> None:
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2), _member("c", "Gamma", 3)]
    session = _session(party=party)
    detach_heroes(session, ["b", "c"], reason="guard")
    assert len(present_party(session, "t1")) == 1
    assert len(combat_party(session, "t1")) == 3
    session.map_state.current_tile_id = "t2"
    assert len(combat_party(session, "t1")) == 2
    assert len(combat_party(session, "t2")) == 1


def test_detached_combat_round_resolves_remote_fight_without_moving_main_party(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2)]
    tiles = [
        TileState(id="t1", x=0, y=0, tile_key="11", tile_type="room", title="Main", description="Main"),
        TileState(
            id="t2",
            x=1,
            y=0,
            tile_key="12",
            tile_type="room",
            title="Guard Room",
            description="Guard",
            enemies=[EnemyState(id="rat", name="Rat", category="vermin", level=1, life=1, max_life=1)],
            initial_enemy_count=1,
        ),
    ]
    session = _session(party=party, current="t1", tiles=tiles)
    session.detached_groups = [DetachedGroupState(tile_id="t2", character_ids=["b"], reason="guard")]
    session.detached_wandering_pending = ["t2"]
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda *args, **kwargs: (6, [6]))

    engine.advance(session, "detached_combat_round", detached_tile_id="t2", show_rolls=True)

    assert session.mode == "exploration"
    assert session.map_state.current_tile_id == "t1"
    assert not session.detached_wandering_pending
    assert "t2" not in session.detached_combat_rounds
    assert not any(enemy.life > 0 for enemy in tiles[1].enemies)
    assert any("Detached combat at Guard Room ends" in entry for entry in session.log)


def test_detached_combat_round_keeps_pending_state_when_fight_continues(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    party = [_member("a", "Alpha", 1), _member("b", "Beta", 2)]
    party[1].current_life = 5
    tiles = [
        TileState(id="t1", x=0, y=0, tile_key="11", tile_type="room", title="Main", description="Main"),
        TileState(
            id="t2",
            x=1,
            y=0,
            tile_key="12",
            tile_type="room",
            title="Guard Room",
            description="Guard",
            enemies=[EnemyState(id="ogre", name="Ogre", category="boss", level=12, life=6, max_life=6)],
            initial_enemy_count=1,
        ),
    ]
    session = _session(party=party, current="t1", tiles=tiles)
    session.detached_groups = [DetachedGroupState(tile_id="t2", character_ids=["b"], reason="guard")]
    session.detached_wandering_pending = ["t2"]
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda *args, **kwargs: (1, [1]))

    engine.advance(session, "detached_combat_round", detached_tile_id="t2", show_rolls=True)

    assert session.mode == "exploration"
    assert session.map_state.current_tile_id == "t1"
    assert session.detached_wandering_pending == ["t2"]
    assert session.detached_combat_rounds["t2"] == 1
    assert any(enemy.life > 0 for enemy in tiles[1].enemies)
    assert any("Detached combat at Guard Room continues" in entry for entry in session.log)


# ---------------------------------------------------------------------------
# Stealth modifier tests
# ---------------------------------------------------------------------------

def _member_class(cid: str, class_id: str, level: int = 3) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=cid,
        class_id=class_id,
        class_name=class_id.title(),
        level=level,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
    )


def test_stealth_modifier_by_class() -> None:
    """Rogue/Assassin/Halfling: +L; half-stealth classes: +½L; others: 0."""
    assert stealth_modifier(_member_class("r", "rogue", 4)) == 4
    assert stealth_modifier(_member_class("a", "assassin", 4)) == 4
    assert stealth_modifier(_member_class("h", "halfling", 4)) == 4
    assert stealth_modifier(_member_class("e", "elf", 4)) == 2
    assert stealth_modifier(_member_class("c", "cleric", 4)) == 2
    assert stealth_modifier(_member_class("ra", "ranger", 4)) == 2
    assert stealth_modifier(_member_class("sw", "swashbuckler", 4)) == 2
    assert stealth_modifier(_member_class("w", "warrior", 4)) == 0
    assert stealth_modifier(_member_class("b", "barbarian", 4)) == 0
    assert stealth_modifier(_member_class("d", "dwarf", 4)) == 0


def test_stealth_training_grants_half_level_bonus() -> None:
    """Stealth Training grants +½L to classes with no native stealth."""
    warrior = _member_class("w", "warrior", 6)
    assert stealth_modifier(warrior) == 0
    warrior.learned_expert_skills = ["stealth_training"]
    assert stealth_modifier(warrior) == 3  # floor(6/2)


def test_stealth_modifier_half_level_floors_down() -> None:
    """½L is always floor: L3 → 1, L5 → 2."""
    assert stealth_modifier(_member_class("c", "cleric", 3)) == 1
    assert stealth_modifier(_member_class("c", "cleric", 5)) == 2


# ---------------------------------------------------------------------------
# Scout-ahead moves scout FORWARD (not backward)
# ---------------------------------------------------------------------------

def _make_engine():
    return RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")


def test_scout_ahead_with_exit_id_detaches_scout_at_destination(monkeypatch) -> None:
    """scout_ahead action with exit_id must move the scout to the destination
    tile while keeping the main party at the origin tile."""
    from app.schemas import ExitState

    engine = _make_engine()
    scout = _member_class("scout", "rogue", 3)
    main = _member_class("main", "warrior", 3)
    origin = TileState(
        id="origin",
        x=0, y=0,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Start",
        exits=[ExitState(id="ex1", direction="north", kind="passage", status="open", destination_tile_id="dest")],
    )
    dest = TileState(
        id="dest",
        x=0, y=-1,
        tile_key="12",
        tile_type="room",
        title="Dest",
        description="Dest",
    )
    session = _session(party=[scout, main], current="origin", tiles=[origin, dest])

    # Stealth roll: guarantee success (roll=6, mod=3 for L3 rogue, total=9 > any target)
    monkeypatch.setattr("app.engine.split_party.roll_d6", lambda: 6)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 6)

    engine.advance(session, "scout_ahead", character_id="scout", exit_id="ex1", show_rolls=True)

    assert session.map_state.current_tile_id == "origin", "main party must stay at origin"
    detached_ids = {cid for g in session.detached_groups for cid in g.character_ids if g.tile_id == "dest"}
    assert "scout" in detached_ids, "scout must be detached at destination"
    # Empty room → automatic success message; enemies present → stealth success message.
    assert any(
        "no enemies" in entry or "Success" in entry or "unseen" in entry
        for entry in session.log
    )


def test_scout_ahead_failure_triggers_detached_combat(monkeypatch) -> None:
    """On a failed Stealth Save the destination tile appears in
    detached_wandering_pending so the solo combat panel is shown."""
    from app.schemas import ExitState

    engine = _make_engine()
    scout = _member_class("scout", "warrior", 1)  # no stealth bonus
    main = _member_class("main", "warrior", 3)
    origin = TileState(
        id="origin",
        x=0, y=0,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Start",
        exits=[ExitState(id="ex1", direction="north", kind="passage", status="open", destination_tile_id="dest")],
    )
    dest = TileState(
        id="dest",
        x=0, y=-1,
        tile_key="12",
        tile_type="room",
        title="Dest",
        description="Dest",
        enemies=[EnemyState(id="ogre", name="Ogre", category="boss", level=5, life=6, max_life=6)],
        initial_enemy_count=1,
    )
    session = _session(party=[scout, main], current="origin", tiles=[origin, dest])

    # Stealth roll: guarantee failure (roll=1 + 0 mod = 1 ≤ level 5 foe)
    monkeypatch.setattr("app.engine.split_party.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    engine.advance(session, "scout_ahead", character_id="scout", exit_id="ex1", show_rolls=True)

    assert session.map_state.current_tile_id == "origin", "main party must stay at origin"
    assert "dest" in session.detached_wandering_pending, "failure must trigger detached combat"
    assert any("Spotted" in entry or "fight alone" in entry for entry in session.log)


def test_scout_ahead_marks_final_boss_immediately_and_only_once(monkeypatch) -> None:
    from app.schemas import ExitState

    engine = _make_engine()
    scout = _member_class("scout", "halfling", 1)
    main = _member_class("main", "warrior", 3)
    origin = TileState(
        id="origin",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Start",
        exits=[ExitState(id="ex1", direction="north", kind="passage", status="open", destination_tile_id="dest")],
    )
    dest = TileState(
        id="dest",
        x=0,
        y=-1,
        tile_key="12",
        tile_type="room",
        title="Dest",
        description="Dest",
        enemies=[EnemyState(id="spider", name="Giant Spider", category="weird", level=8, life=3, max_life=3)],
        initial_enemy_count=1,
    )
    session = _session(party=[scout, main], current="origin", tiles=[origin, dest])

    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 6)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    engine.advance(session, "scout_ahead", character_id="scout", exit_id="ex1", show_rolls=True)

    assert session.major_foes_encountered == 1
    assert session.final_boss_designated is True
    assert dest.final_boss_treasure is True
    assert "final_boss" in dest.enemies[0].tags
    assert any("Final Boss check" in line for line in session.log)
    assert any("scout sees" in line.lower() for line in session.log)

    before = len([line for line in session.log if "Final Boss check" in line])
    engine.advance(session, "rush_to_scout", detached_tile_id="dest", show_rolls=True)
    after = len([line for line in session.log if "Final Boss check" in line])

    assert session.map_state.current_tile_id == "dest"
    assert session.major_foes_encountered == 1
    assert before == after
    assert session.mode == "combat"
    assert session.reaction_checked is True
    assert not session.reaction_pending


def test_failed_scout_gets_one_solo_round_then_must_choose_followup(monkeypatch) -> None:
    from app.schemas import ExitState

    engine = _make_engine()
    scout = _member_class("scout", "warrior", 1)
    scout.current_life = 20
    scout.max_life = 20
    main = _member_class("main", "warrior", 3)
    origin = TileState(
        id="origin",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Origin",
        description="Start",
        exits=[ExitState(id="ex1", direction="north", kind="passage", status="open", destination_tile_id="dest")],
    )
    dest = TileState(
        id="dest",
        x=0,
        y=-1,
        tile_key="12",
        tile_type="room",
        title="Dest",
        description="Dest",
        enemies=[EnemyState(id="ogre", name="Ogre", category="boss", level=9, life=6, max_life=6)],
        initial_enemy_count=1,
    )
    session = _session(party=[scout, main], current="origin", tiles=[origin, dest])

    monkeypatch.setattr("app.engine.experience.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    engine.advance(session, "scout_ahead", character_id="scout", exit_id="ex1", show_rolls=True)
    engine.advance(session, "detached_combat_round", detached_tile_id="dest", show_rolls=True)

    assert session.detached_combat_rounds["dest"] == 1
    assert any("scout survives the first round" in line.lower() for line in session.log)

    log_before = len(session.log)
    engine.advance(session, "detached_combat_round", detached_tile_id="dest", show_rolls=True)
    new_log = session.log[log_before:]

    assert session.detached_combat_rounds["dest"] == 1
    assert any("already held out for one round" in line for line in new_log)
