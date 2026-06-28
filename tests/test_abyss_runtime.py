from __future__ import annotations

from pathlib import Path

from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, PartyMemberState


def _engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _member() -> PartyMemberState:
    return PartyMemberState.model_validate(
        {
            "character_id": "hero-1",
            "name": "Abyss Hero",
            "class_id": "warrior",
            "class_name": "Warrior",
            "level": 5,
            "expert_trained": True,
            "max_life": 12,
            "current_life": 12,
            "gold": 0,
            "xp": 0,
            "inventory": ["Hand weapon", "Light armor"],
            "attack_bonus": 0,
            "defense_bonus": 0,
            "save_bonus": 0,
            "marching_order": 1,
        }
    )


def test_abyss_profile_routes_room_content_to_abyss_minions(monkeypatch) -> None:
    eng = _engine()
    session = eng.create_session("abyss-1", "party-1", [_member()], ruleset_profile_id="abyss")
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 7)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    monkeypatch.setattr("app.engine.random_dungeon.roll_formula", lambda formula: 4 if formula == "4d6" else 1)

    content = eng._roll_content(session, "room", 5)

    assert content["key"] == "abyss_minions"
    assert "Abyss Minions" in content["description"]
    assert len(content["enemies"]) == 5
    assert content["enemies"][0].name == "Hairy Goblins"
    assert any(enemy.name == "Goblin Leader" for enemy in content["enemies"])


def test_abyss_treasure_content_uses_claimable_payload(monkeypatch) -> None:
    eng = _engine()
    session = eng.create_session("abyss-2", "party-1", [_member()], ruleset_profile_id="abyss")
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 2)
    monkeypatch.setattr("app.engine.random_dungeon.roll_die", lambda sides: 4 if sides == 8 else 1)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    monkeypatch.setattr(
        "app.engine.random_dungeon.roll_formula",
        lambda formula: 3 if formula == "3d6" else int(formula),
    )

    content = eng._roll_content(session, "room", 5)

    assert content["key"] == "abyss_treasure"
    assert content["treasure_gold"] == 60
    assert "Abyss Treasure d8=4" in content["treasure_summary"]
    assert content["enemies"] == []


def test_abyss_treasure_choice_can_take_useful_stuff(monkeypatch) -> None:
    eng = _engine()
    session = eng.create_session("abyss-2b", "party-1", [_member()], ruleset_profile_id="abyss")
    monkeypatch.setattr("app.engine.random_dungeon.roll_2d6", lambda: 2)
    monkeypatch.setattr("app.engine.random_dungeon.roll_die", lambda sides: 2 if sides == 8 else 1)
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 3)
    monkeypatch.setattr("app.engine.random_dungeon.roll_formula", lambda formula: 4 if formula == "4d6" else 1)

    content = eng._roll_content(session, "room", 5)
    tile = session.map_state.tiles[0]
    tile.treasure_summary = content["treasure_summary"]
    tile.treasure_gold = content["treasure_gold"]
    tile.pending_treasure_choice = content["pending_treasure_choice"]

    assert tile.pending_treasure_choice == "abyss_gold_or_useful"
    eng.advance(session, "choose_treasure_outcome", show_rolls=False, treasure_outcome_choice="useful")

    assert tile.pending_treasure_choice is None
    assert tile.treasure_items == ["Wolvesbane"]
    assert tile.treasure_gold == 0


def test_abyss_wandering_uses_abyss_monster_rows(monkeypatch) -> None:
    eng = _engine()
    session = eng.create_session("abyss-3", "party-1", [_member()], ruleset_profile_id="abyss")
    tile = session.map_state.tiles[0]
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 5)
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 5)
    monkeypatch.setattr("app.engine.random_dungeon.roll_formula", lambda formula: 1)

    eng._spawn_wandering_monsters(session, tile, show_rolls=True, start_combat=False)

    assert tile.enemies
    assert tile.enemies[0].name == "Phasing Panther"
    assert any("Abyss Wandering Monsters table" in line for line in session.log)


def test_abyss_trap_resolves_with_abyss_effects(monkeypatch) -> None:
    eng = _engine()
    member = _member()
    session = eng.create_session("abyss-4", "party-1", [member], ruleset_profile_id="abyss")
    tile = session.map_state.tiles[0]
    tile.trap_key = "abyss_electrical_blast"
    tile.trap_level = 7
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda hero: (1, [1]))

    eng.advance(session, "resolve_trap", show_rolls=True)

    assert tile.trap_resolved is True
    assert session.party[0].current_life == 11
    assert any("Electrical blast" in line for line in session.log)


def test_abyss_room_of_horrors_applies_madness_and_resolves(monkeypatch) -> None:
    eng = _engine()
    member = _member()
    member.level = 5
    session = eng.create_session("abyss-5", "party-1", [member], ruleset_profile_id="abyss")
    tile = session.map_state.tiles[0]
    tile.content_key = "abyss_special_feature"
    tile.special_event_key = "room_of_horrors"
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda hero: (1, [1]))
    monkeypatch.setattr(
        "app.engine.heroic_skill_effects.resolve_fear_save",
        lambda *args, **kwargs: (False, ["Room of Horrors fear: forced failure."]),
    )

    eng._prepare_tile_features(session, tile, show_rolls=True, explain_math=False)

    assert tile.resolved is True
    assert session.party[0].madness >= 1
    assert "Abyss Room of Horrors -1 Attack" in session.party[0].statuses


def test_abyss_minion_reaction_uses_abyss_table_and_minion_bribe_count(monkeypatch) -> None:
    eng = _engine()
    member = _member()
    member.gold = 100
    session = eng.create_session("abyss-6", "party-1", [member], ruleset_profile_id="abyss")
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(
            id=f"goblin-{index}",
            name="Hairy Goblins",
            category="minions",
            level=6,
            life=1,
            max_life=1,
            tags=["abyss", "reaction_table:Abyss Hairy Goblins"],
        )
        for index in range(4)
    ]
    tile.enemies.append(
        EnemyState(
            id="leader",
            name="Goblin Leader",
            category="boss",
            level=10,
            life=4,
            max_life=4,
            tags=["abyss", "abyss_leader", "reaction_table:Abyss Hairy Goblins"],
        )
    )
    session.mode = "combat"
    session.reaction_pending = True
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    eng.advance(session, "check_reaction", show_rolls=True)

    assert session.reaction_key == "bribe"
    assert session.reaction_bribe_foe_count == 4
    assert session.reaction_bribe_gold == 40
    assert "capture" not in "\n".join(session.log).lower()


def test_abyss_trial_of_champions_prefers_tagged_leader(monkeypatch) -> None:
    eng = _engine()
    session = eng.create_session("abyss-7", "party-1", [_member()], ruleset_profile_id="abyss")
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(
            id="rat-1",
            name="Chaotic Ratmen",
            category="minions",
            level=7,
            life=1,
            max_life=1,
            tags=["abyss", "reaction_table:Abyss Chaotic Ratmen"],
        ),
        EnemyState(
            id="rat-leader",
            name="Ratman Leader",
            category="boss",
            level=9,
            life=1,
            max_life=1,
            tags=["abyss", "abyss_leader", "reaction_table:Abyss Chaotic Ratmen"],
        ),
    ]
    session.mode = "combat"
    session.reaction_pending = True
    rolls = iter([6, 1, 1])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))
    monkeypatch.setattr("app.engine.random_dungeon.roll_exploding_for_level", lambda hero: (12, [12]))

    eng.advance(session, "check_reaction", show_rolls=True)
    assert session.reaction_key == "trial_of_champions"

    eng.advance(session, "reaction_choice", show_rolls=True, reaction_choice="accept", character_id="hero-1")

    assert session.mode == "exploration"
    assert any("Abyss Hero defeats Ratman Leader" in entry for entry in session.log)


def test_abyss_flying_skulls_fight_to_death_when_not_outnumbered(monkeypatch) -> None:
    eng = _engine()
    session = eng.create_session("abyss-8", "party-1", [_member()], ruleset_profile_id="abyss")
    tile = session.map_state.tiles[0]
    tile.enemies = [
        EnemyState(
            id=f"skull-{index}",
            name="Flying Skulls",
            category="minions",
            level=9,
            life=1,
            max_life=1,
            tags=["abyss", "reaction_table:Abyss Flying Skulls"],
        )
        for index in range(2)
    ]
    session.mode = "combat"
    session.reaction_pending = True
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)

    eng.advance(session, "check_reaction", show_rolls=True)

    assert session.reaction_key == "fight_to_death"
    assert any("fight to the death" in entry.lower() for entry in session.log)
