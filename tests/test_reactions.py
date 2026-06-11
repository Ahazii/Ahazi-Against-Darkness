from __future__ import annotations

from pathlib import Path

from app.engine.dungeon_table_roller import DungeonTableRoller
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.reactions import (
    bribe_requirements_met,
    build_reaction_outcome,
    is_bribe_weapon,
    pay_bribe_cost,
    reaction_table_for_category,
    resolve_reaction_source,
)
from app.rules.repository import RulesRepository
from app.schemas import DetachedGroupState, EnemyState, MapState, PartyMemberState, SessionState, TileState


def packaged_rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def combat_session(*, enemies: list[EnemyState], party_gold: int = 100) -> SessionState:
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=party_gold,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon", "Dagger"],
    )
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_pending=True,
        party=[hero],
        map_state=MapState(
            tiles=[
                TileState(
                    id="tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Room",
                    description="Room",
                    enemies=enemies,
                    initial_enemy_count=len(enemies),
                )
            ],
            current_tile_id="tile",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def _split_party_combat_session(
    *,
    enemies: list[EnemyState],
    remote_gold: int = 0,
    present_gold: int = 0,
    remote_clues: int = 0,
    present_clues: int = 0,
) -> SessionState:
    remote = PartyMemberState(
        character_id="remote",
        name="Remote",
        class_id="wizard",
        class_name="Wizard",
        level=3,
        xp=0,
        gold=remote_gold,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=1,
        spells=["Fireball"],
        clues=remote_clues,
    )
    present = PartyMemberState(
        character_id="present",
        name="Present",
        class_id="warrior",
        class_name="Warrior",
        level=3,
        xp=0,
        gold=present_gold,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=2,
        clues=present_clues,
    )
    return SessionState(
        id="split-session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        reaction_pending=False,
        reaction_checked=True,
        party=[remote, present],
        detached_groups=[
            DetachedGroupState(tile_id="remote-tile", character_ids=["remote"], reason="scout")
        ],
        map_state=MapState(
            tiles=[
                TileState(
                    id="current-tile",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Current Room",
                    description="Current",
                    enemies=enemies,
                    initial_enemy_count=len(enemies),
                ),
                TileState(
                    id="remote-tile",
                    x=1,
                    y=0,
                    tile_key="12",
                    tile_type="room",
                    title="Remote Room",
                    description="Remote",
                ),
            ],
            current_tile_id="current-tile",
        ),
        clues_found=remote_clues + present_clues,
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )


def test_reaction_table_selection() -> None:
    assert (
        reaction_table_for_category([EnemyState(id="1", name="Rat", category="vermin", level=2, life=1, max_life=1)])
        == "vermin_reaction_table"
    )
    assert (
        reaction_table_for_category([EnemyState(id="2", name="Goblin", category="minions", level=3, life=1, max_life=1)])
        == "minion_reaction_table"
    )
    assert (
        reaction_table_for_category([EnemyState(id="3", name="Dragon", category="boss", level=8, life=8, max_life=8)])
        == "major_reaction_table"
    )


def test_goblins_use_per_foe_reaction_table() -> None:
    tables = packaged_rules().monsters()["reaction_tables"]
    enemies = [EnemyState(id=f"g{i}", name="Goblins", category="minions", level=3, life=1, max_life=1) for i in range(4)]
    source = resolve_reaction_source(enemies, tables)
    assert source.inline_rows is not None
    assert source.label == "Goblins"
    bribe_row = next(row for row in source.inline_rows if row["key"] == "bribe")
    assert bribe_row["gold_per_foe"] == 5
    assert bribe_row["weapons_per_foe"] == 1


def test_mixed_foes_fall_back_to_category_table() -> None:
    tables = packaged_rules().monsters()["reaction_tables"]
    enemies = [
        EnemyState(id="g1", name="Goblins", category="minions", level=3, life=1, max_life=1),
        EnemyState(id="o1", name="Orcs", category="minions", level=4, life=1, max_life=1),
    ]
    source = resolve_reaction_source(enemies, tables)
    assert source.inline_rows is None
    assert source.table_name == "minion_reaction_table"


def test_bribe_gold_and_weapons_scale_with_foes() -> None:
    row = {"key": "bribe", "result": "Pay up.", "gold_per_foe": 5, "weapons_per_foe": 1}
    outcome = build_reaction_outcome(row, hcl=3, foe_count=4)
    assert outcome.bribe_gold == 20
    assert outcome.bribe_weapons == 4
    assert outcome.bribe_gold_per_foe == 5
    assert outcome.bribe_weapons_per_foe == 1


def test_is_bribe_weapon() -> None:
    assert is_bribe_weapon("Hand weapon")
    assert is_bribe_weapon("Dagger")
    assert not is_bribe_weapon("Light armor")
    assert not is_bribe_weapon("Blade poison")


def test_bribe_requirements_allow_mixed_payment() -> None:
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=10,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon", "Dagger"],
    )
    assert bribe_requirements_met([hero], foe_count=4, gold_per_foe=5, weapons_per_foe=1)
    broke = hero.model_copy(update={"gold": 5, "inventory": []})
    assert not bribe_requirements_met([broke], foe_count=4, gold_per_foe=5, weapons_per_foe=1)


def test_pay_bribe_cost_uses_weapons_before_gold() -> None:
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=10,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Hand weapon", "Dagger"],
    )
    gold_paid, weapons_paid, log = pay_bribe_cost(
        [hero],
        foe_count=4,
        gold_per_foe=5,
        weapons_per_foe=1,
    )
    assert weapons_paid == 2
    assert gold_paid == 10
    assert hero.gold == 0
    assert hero.inventory == []


def test_check_reaction_flee_ends_combat(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)]
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 1)
    monkeypatch.setattr(
        engine.table_roller,
        "roll_reaction",
        lambda table_name, roll: {"key": "flee", "result": "The goblins flee."},
    )
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda level: (6, [6]))
    engine.advance(session, "check_reaction")
    assert session.mode == "exploration"
    assert not any(enemy.life > 0 for enemy in session.map_state.tiles[0].enemies)
    assert any("flee" in entry.lower() for entry in session.log)


def test_check_reaction_peaceful_ends_combat(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)]
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 2)
    monkeypatch.setattr(
        engine.table_roller,
        "roll_reaction",
        lambda table_name, roll: {"key": "peaceful", "result": "The goblins ignore you."},
    )
    engine.advance(session, "check_reaction")
    assert session.mode == "exploration"
    assert any("peacefully" in entry.lower() for entry in session.log)


def test_goblin_bribe_uses_bestiary_table(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id=f"g{i}", name="Goblins", category="minions", level=3, life=1, max_life=1) for i in range(4)]
    )
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 3)
    engine.advance(session, "check_reaction")
    assert session.reaction_key == "bribe"
    assert session.reaction_bribe_gold == 20
    assert session.reaction_bribe_weapons == 4
    assert any("Goblins reaction table" in entry for entry in session.log)


def test_pay_bribe_deducts_gold(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)],
        party_gold=20,
    )
    session.reaction_checked = True
    session.reaction_key = "bribe"
    session.reaction_bribe_gold = 15
    session.reaction_bribe_foe_count = 1
    session.reaction_bribe_gold_per_foe = 15
    engine.advance(session, "pay_bribe", pay_bribe=True)
    assert session.mode == "exploration"
    assert session.party[0].gold == 5


def test_pay_bribe_with_weapons_only() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id=f"g{i}", name="Goblins", category="minions", level=3, life=1, max_life=1) for i in range(2)],
        party_gold=0,
    )
    session.party[0].inventory = ["Hand weapon", "Dagger"]
    session.reaction_checked = True
    session.reaction_key = "bribe"
    session.reaction_bribe_gold = 10
    session.reaction_bribe_weapons = 2
    session.reaction_bribe_gold_per_foe = 5
    session.reaction_bribe_weapons_per_foe = 1
    session.reaction_bribe_foe_count = 2
    engine.advance(session, "pay_bribe", pay_bribe=True)
    assert session.mode == "exploration"
    assert session.party[0].inventory == []
    assert any("surrenders" in entry for entry in session.log)


def test_split_party_bribe_uses_only_heroes_on_current_tile() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = _split_party_combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)],
        remote_gold=100,
        present_gold=0,
    )
    session.reaction_key = "bribe"
    session.reaction_bribe_gold = 100
    session.reaction_bribe_gold_per_foe = 100
    session.reaction_bribe_foe_count = 1

    engine.advance(session, "pay_bribe", pay_bribe=True)

    assert session.party[0].gold == 100
    assert session.party[1].gold == 0
    assert session.mode == "combat"
    assert session.foes_strike_first
    assert any("0gp here" in entry for entry in session.log)


def test_trade_information_sells_without_spending_clues(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="t1", name="Travellers", category="minions", level=3, life=1, max_life=1)],
        party_gold=0,
    )
    session.party[0].inventory = []
    session.clues_found = 2
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 4)
    monkeypatch.setattr(
        engine.table_roller,
        "roll_reaction",
        lambda table_name, roll: {"key": "trade_information", "result": "They want to trade information."},
    )

    engine.advance(session, "check_reaction")
    assert session.reaction_key == "trade_information"

    engine.advance(session, "trade_information", trade_information_choice="sell")

    assert session.mode == "exploration"
    assert session.clues_found == 2
    assert session.party[0].clues == 2
    assert session.party[0].gold == 50
    assert any("Clues are not spent" in entry for entry in session.log)


def test_split_party_trade_information_sells_only_clues_on_current_tile() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = _split_party_combat_session(
        enemies=[EnemyState(id="t1", name="Travellers", category="minions", level=3, life=1, max_life=1)],
        remote_clues=3,
        present_clues=1,
    )
    session.reaction_key = "trade_information"

    engine.advance(session, "trade_information", trade_information_choice="sell")

    assert session.mode == "exploration"
    assert session.clues_found == 4
    assert session.party[0].gold == 0
    assert session.party[1].gold == 25
    assert any("1 Clue" in entry for entry in session.log)
    assert not any("4 Clues" in entry for entry in session.log)


def test_trade_information_buys_clue_for_gold() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="t1", name="Travellers", category="minions", level=3, life=1, max_life=1)],
        party_gold=100,
    )
    session.reaction_checked = True
    session.reaction_key = "trade_information"

    engine.advance(session, "trade_information", trade_information_choice="buy")

    assert session.mode == "exploration"
    assert session.clues_found == 1
    assert session.party[0].clues == 1
    assert session.party[0].gold == 0


def test_split_party_fleeing_foes_are_struck_only_by_heroes_on_current_tile(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = _split_party_combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=12, life=1, max_life=1)]
    )
    tile = session.map_state.tiles[0]
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda level: (1, [1]))

    engine._resolve_foe_flee_strike(session, tile, show_rolls=True)

    assert any("Present vs Goblin" in entry for entry in session.log)
    assert not any("Remote vs Goblin" in entry for entry in session.log)
    assert not any("Remote misses" in entry for entry in session.log)


def test_split_party_detached_hero_cannot_cast_into_current_fight() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = _split_party_combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=12, life=1, max_life=1)]
    )

    engine.advance(session, "cast_spell", character_id="remote", spell_name="Fireball")

    assert session.mode == "combat"
    assert session.map_state.tiles[0].enemies[0].life == 1
    assert any("Remote is not on the current map element" in entry for entry in session.log)


def test_basic_spells_table_has_six_entries() -> None:
    roller = DungeonTableRoller.from_rules(packaged_rules())
    for roll in range(1, 7):
        row = roller.lookup("basic_spells_table", roll)
        assert row is not None
        assert row["spell"]


def test_offensive_spell_skips_reaction_roll(monkeypatch) -> None:
    from app.engine import spells

    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    wizard = PartyMemberState(
        character_id="wiz",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball"],
    )
    foe = EnemyState(id="ogre", name="Ogre", category="boss", level=5, life=6, max_life=6)
    session = combat_session(enemies=[foe])
    session.party = [wizard]
    session.reaction_pending = True
    session.reaction_checked = False
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda level: (6, [6]))
    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Fireball")
    assert session.mode == "combat"
    assert session.reaction_checked
    assert not session.reaction_pending
    assert any("without waiting for a Reaction roll" in entry for entry in session.log)

    session.log.clear()
    engine.advance(session, "check_reaction")
    assert any("already checked" in entry.lower() for entry in session.log)


def test_protection_spell_before_reactions_commits_to_immediate_action() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    wizard = PartyMemberState(
        character_id="wiz",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Protection"],
    )
    foe = EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)
    session = combat_session(enemies=[foe])
    session.party = [wizard]
    session.reaction_pending = True
    session.reaction_checked = False
    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Protection")
    assert session.reaction_checked
    assert not session.reaction_pending
    assert session.party_attacked_immediately
    assert any("without waiting for a Reaction roll" in entry for entry in session.log)


def test_surprised_party_must_check_reactions_before_round() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)]
    )
    session.party_surprised = True
    session.reaction_pending = True
    session.reaction_checked = False

    engine.advance(session, "combat_round")

    assert session.combat_round == 0
    assert session.reaction_pending
    assert not session.reaction_checked
    assert any("surprised" in entry.lower() and "check reactions" in entry.lower() for entry in session.log)


def test_surprised_party_must_check_reactions_before_spell(monkeypatch) -> None:
    from app.engine import spells

    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    wizard = PartyMemberState(
        character_id="wiz",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=2,
        xp=0,
        gold=0,
        current_life=4,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball"],
    )
    session = combat_session(
        enemies=[EnemyState(id="g1", name="Goblin", category="minions", level=3, life=1, max_life=1)]
    )
    session.party = [wizard]
    session.party_surprised = True
    session.reaction_pending = True
    session.reaction_checked = False
    monkeypatch.setattr(spells, "roll_exploding_for_level", lambda level: (6, [6]))

    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Fireball")

    assert session.reaction_pending
    assert not session.reaction_checked
    assert "Fireball" not in session.expended_spells.get("wiz", [])
    assert any("surprised" in entry.lower() and "check reactions" in entry.lower() for entry in session.log)


def test_surprised_encounter_auto_rolls_mandatory_reactions(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="rat", name="Rat", category="vermin", level=1, life=1, max_life=1)]
    )
    session.mode = "exploration"
    session.reaction_pending = False
    session.reaction_checked = False
    tile = session.map_state.tiles[0]
    tile.wandering_ambush = True
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 4)

    engine._begin_combat(session, "Wandering Monsters attack!", show_rolls=True)

    assert session.mode == "combat"
    assert session.party_surprised
    assert session.reaction_checked
    assert not session.reaction_pending
    assert session.reaction_key == "fight"
    assert session.foes_strike_first
    assert any("mandatory" in entry.lower() and "reactions" in entry.lower() for entry in session.log)
    assert any("Reaction roll: d6 = 4" in entry for entry in session.log)
    assert not any("Choose: Check Reactions" in entry for entry in session.log)


def test_normalize_auto_rolls_stale_surprise_reaction(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="rat", name="Rat", category="vermin", level=1, life=1, max_life=1)]
    )
    session.party_surprised = True
    session.reaction_pending = True
    session.reaction_checked = False
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 4)

    normalized, changed = engine.normalize_session(session)

    assert normalized is session
    assert changed
    assert session.reaction_checked
    assert not session.reaction_pending
    assert session.reaction_key == "fight"
    assert session.foes_strike_first
    assert any("mandatory" in entry.lower() and "reactions" in entry.lower() for entry in session.log)


def test_combat_round_skips_reaction_roll() -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="ogre", name="Ogre", category="boss", level=5, life=6, max_life=6)]
    )
    session.reaction_pending = True
    session.reaction_checked = False
    engine.advance(session, "combat_round")
    assert session.mode == "combat"
    assert session.reaction_checked
    assert not session.reaction_pending
    assert any("without waiting for a Reaction roll" in entry for entry in session.log)


def test_reaction_choice_cleared_after_first_combat_round(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    session = combat_session(
        enemies=[EnemyState(id="ogre", name="Ogre", category="boss", level=5, life=6, max_life=6)]
    )
    session.reaction_pending = True
    session.reaction_checked = False
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda level: (1, [1]))
    engine.advance(session, "combat_round", show_rolls=False)
    assert session.combat_round == 1
    assert not session.reaction_pending
    session.reaction_pending = True
    session.reaction_checked = False
    engine.advance(session, "combat_round", show_rolls=False)
    assert session.combat_round == 2
    assert not session.reaction_pending
    assert not any("without waiting for a Reaction roll" in entry for entry in session.log[-3:])


def test_one_spell_per_combat_round(monkeypatch) -> None:
    engine = RandomDungeonEngine(packaged_rules(), Path(__file__).resolve().parents[1] / "assets")
    wizard = PartyMemberState(
        character_id="wiz",
        name="Wizard",
        class_id="wizard",
        class_name="Wizard",
        level=7,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=["Fireball", "Lightning"],
    )
    foes = [
        EnemyState(id=f"o{i}", name="Orc", category="minions", level=7, life=1, max_life=1)
        for i in range(3)
    ]
    session = combat_session(enemies=foes)
    session.party = [wizard]
    session.reaction_pending = False
    session.reaction_checked = True
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda level: (1, [1]))
    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Fireball")
    assert session.mode == "combat"
    assert "wiz" in session.spell_used_character_ids
    assert "Fireball" in session.expended_spells.get("wiz", [])

    session.log.clear()
    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Lightning")
    assert any("already cast a spell this combat round" in entry.lower() for entry in session.log)
    assert "Lightning" not in session.expended_spells.get("wiz", [])

    session.log.clear()
    monkeypatch.setattr("app.engine.combat.roll_exploding_for_level", lambda level: (1, [1]))
    engine.advance(session, "combat_round", show_rolls=False)
    assert session.spell_used_character_ids == []
    monkeypatch.setattr("app.engine.combat_modifiers.roll_exploding_for_level", lambda level: (1, [1]))
    engine.advance(session, "cast_spell", character_id="wiz", spell_name="Lightning")
    assert "Lightning" in session.expended_spells.get("wiz", [])
