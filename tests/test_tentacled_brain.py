from pathlib import Path

from app.engine.combat import CombatContext, assign_enemy_attacks
from app.engine.combat_modifiers import ranged_or_spell_target_level, spell_target_level
from app.engine.monster_template_effects import apply_pre_party_turn_effects
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def hero(*, class_id: str = "warrior", level: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id=class_id,
        name=class_id.title(),
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
    )


def session_with(*party: PartyMemberState) -> SessionState:
    tile = TileState(id="room", x=0, y=0, tile_key="11", tile_type="room", title="Room", description="Room")
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="combat",
        party=list(party),
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="now",
        updated_at="now",
    )


def engine() -> RandomDungeonEngine:
    rules_dir = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(rules_dir, rules_dir / "_override"), Path())


def tentacled_brain() -> EnemyState:
    return EnemyState(
        id="brain",
        name="Tentacled Brain",
        category="boss",
        level=9,
        life=8,
        max_life=8,
        attacks=0,
        tags=["abyss", "ranged_spell_target_level:6"],
        per_turn_effects=[
            {
                "type": "save_damage_madness",
                "timing": "before_party_actions",
                "label": "Tentacled Brain save",
                "target": "all_pcs",
                "save_level": 5,
                "save_type": "mind",
                "save_modifier": {"wizard": "+L"},
                "damage": 1,
                "madness": 1,
            }
        ],
    )


def test_tentacled_brain_has_no_normal_attack_and_uses_ranged_spell_level() -> None:
    brain = tentacled_brain()
    assert assign_enemy_attacks([brain], [hero()], context=CombatContext()) == []
    assert ranged_or_spell_target_level(brain) == 6
    assert spell_target_level(brain) == 6


def test_tentacled_brain_aura_precedes_party_actions_and_wizards_add_level(monkeypatch) -> None:
    warrior = hero()
    wizard = hero(class_id="wizard", level=4)
    current = session_with(warrior, wizard)
    brain = tentacled_brain()
    current.map_state.tiles[0].enemies = [brain]

    monkeypatch.setattr(
        "app.engine.monster_template_effects.roll_exploding_for_level",
        lambda member: (1 if member.class_id == "warrior" else 2, [1 if member.class_id == "warrior" else 2]),
    )

    log = apply_pre_party_turn_effects([brain], current.party, current, show_rolls=True)

    assert log[0] == "Event: Tentacled Brain acts before the party can attack."
    assert warrior.current_life == 4
    assert warrior.madness == 1
    assert wizard.current_life == 5
    assert wizard.madness == 0
    assert any("Wizard rolls 2 + 4 = 6 vs L5" in line for line in log)


def test_tentacled_brain_final_boss_keeps_its_printed_reaction_table(monkeypatch) -> None:
    current = session_with(hero())
    brain = tentacled_brain()
    brain.tags.extend(["final_boss", "allow_final_boss_reaction", "reaction_table:Tentacled Brain"])
    current.map_state.tiles[0].enemies = [brain]
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: 3)

    engine()._check_reaction(current, show_rolls=True)

    assert current.reaction_key == "bribe"
    assert current.reaction_bribe_gold == 300
    assert any("Tentacled Brain reaction table" in line for line in current.log)
