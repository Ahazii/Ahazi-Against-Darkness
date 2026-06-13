from __future__ import annotations

from pathlib import Path

from app.engine.combat import CombatRound
from app.engine.experience import MINOR_ENCOUNTERS_FOR_XP
from app.engine.random_dungeon import RandomDungeonEngine
from app.engine.secrets import secret_attack_bonus, secret_defense_bonus, secret_weakness_attack_bonus
from app.engine.spells import can_cast_spell
from app.rules.repository import RulesRepository
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def engine() -> RandomDungeonEngine:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RandomDungeonEngine(RulesRepository(packaged, packaged / "_override"), Path())


def _secret_session(member: PartyMemberState, *, tile: TileState, mode: str = "exploration") -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode=mode,
        party=[member],
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_minor_encounter_tracks_toward_xp() -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    defeated = [
        EnemyState(id="1", name="Rat", category="vermin", level=2, life=0, max_life=1),
        EnemyState(id="2", name="Rat", category="vermin", level=2, life=0, max_life=1),
    ]
    for _ in range(MINOR_ENCOUNTERS_FOR_XP):
        eng._award_encounter_xp(session, defeated, show_rolls=False)
    assert session.xp_rolls_pending == 1
    assert session.minor_encounters_defeated == 0


def test_major_foe_grants_xp_roll() -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng._award_encounter_xp(
        session,
        [EnemyState(id="b", name="Ogre", category="boss", level=5, life=0, max_life=6)],
        show_rolls=False,
    )
    assert session.xp_rolls_pending == 1


def test_xp_roll_levels_up_on_six(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_rolls_pending=1,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    monkeypatch.setattr("app.engine.random_dungeon.perform_advancement_roll", lambda member_or_level, bonus=0, purpose="level_up": __import__("app.engine.dice", fromlist=["AdvancementRollResult"]).AdvancementRollResult(natural=6, total=6, sides=6, modifier=bonus))
    eng.advance(session, "xp_roll", character_id="h", advancement_fork="level_up")
    assert hero.level == 2
    assert hero.max_life == 8
    assert hero.current_life == 4
    assert session.xp_rolls_pending == 0


def test_expert_tier_xp_roll_levels_up(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Veteran",
        class_id="warrior",
        class_name="Warrior",
        level=6,
        xp=0,
        gold=0,
        current_life=8,
        max_life=12,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_rolls_pending=1,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    from app.engine.dice import AdvancementRollResult

    monkeypatch.setattr(
        "app.engine.random_dungeon.perform_advancement_roll",
        lambda member_or_level, bonus=0, purpose="level_up": AdvancementRollResult(natural=8, total=10, sides=8, modifier=2),
    )
    eng.advance(session, "xp_roll", character_id="h", advancement_fork="level_up")
    assert hero.level == 7
    assert session.xp_rolls_pending == 0


def test_buy_healing_costs_gold() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=20,
        current_life=2,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        healer_available=True,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id="t"),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "buy_healing", character_id="h")
    assert hero.current_life == 3
    assert hero.gold == 10


def test_old_school_xp_and_level_up() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_system="old_school",
        old_school_xp_tally=300,
        party=[hero],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng.advance(session, "old_school_level_up", character_id="h")
    assert hero.level == 2
    assert session.old_school_xp_tally == 0


def test_slower_advancement_banks_xp() -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        xp_system="slower_advancement",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    eng._grant_xp_credit(session, 1, "Test:")
    assert session.slower_xp_bank == 1
    assert session.xp_rolls_pending == 0


def test_three_clues_stay_held_until_secret_revealed(monkeypatch) -> None:
    eng = engine()
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        party=[
            PartyMemberState(
                character_id="h",
                name="Hero",
                class_id="warrior",
                class_name="Warrior",
                level=1,
                xp=0,
                gold=0,
                current_life=3,
                max_life=3,
                attack_bonus=0,
                defense_bonus=0,
                save_bonus=0,
            )
        ],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    tile = session.map_state.tiles[0]
    for _ in range(3):
        eng._grant_clue(session, tile)
    assert session.xp_rolls_pending == 0
    assert session.clues_found == 3
    assert session.party[0].clues == 3

    eng.advance(session, "reveal_secret_with_clues", character_id="h")
    assert session.xp_rolls_pending == 0
    assert session.clues_found == 3
    assert session.party[0].clues == 3
    assert "Choose which Secret" in session.log[-1]

    rolls = iter([1, 2, 3])
    monkeypatch.setattr("app.engine.random_dungeon.roll_d6", lambda: next(rolls))
    eng.advance(session, "reveal_secret_with_clues", character_id="h", secret_id="hidden_treasure_location")
    assert session.xp_rolls_pending == 1
    assert session.clues_found == 0
    assert session.party[0].clues == 0
    assert session.party[0].gold == 60
    assert session.party[0].secrets == ["hidden_treasure_location"]
    assert "Secret Hidden Treasure" in tile.objects


def test_magic_item_location_secret_creates_claimable_magic_treasure(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        clues=3,
    )
    tile = TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")
    session = _secret_session(hero, tile=tile)
    session.clues_found = 3
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 4)
    monkeypatch.setattr("app.engine.magic_weapons.roll_d6", lambda: 6)

    eng.advance(session, "reveal_secret_with_clues", character_id="h", secret_id="magic_item_location")

    assert session.clues_found == 0
    assert hero.clues == 0
    assert "magic_item_location" not in hero.secrets
    assert tile.treasure_items == ["Magic Bow (Bow, +1 Attack)"]
    assert tile.treasure_claimed is False
    assert "Secret Magic Item" in tile.objects
    assert any("Magic weapon type" in line and "Magic Bow" in line for line in session.log)
    assert any("Use Claim Treasure" in line for line in session.log)


def test_scroll_location_secret_adds_basic_scroll(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        clues=3,
    )
    tile = TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")
    session = _secret_session(hero, tile=tile)
    session.clues_found = 3
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 6)

    eng.advance(session, "reveal_secret_with_clues", character_id="h", secret_id="scroll_location")

    assert session.clues_found == 0
    assert hero.clues == 0
    assert "scroll_location" not in hero.secrets
    assert "Scroll of Sleep" in hero.inventory
    assert any("burned or copied" in line for line in session.log)


def test_use_recorded_scroll_location_secret_can_choose_basic_scroll() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["scroll_location"],
    )
    tile = TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")
    session = _secret_session(hero, tile=tile)

    eng.advance(session, "use_secret", character_id="h", secret_id="scroll_location", expert_skill_id="fireball")

    assert hero.secrets == []
    assert "Scroll of Fireball" in hero.inventory


def test_new_spell_secret_adds_temporary_spell_slot() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        clues=3,
    )
    tile = TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")
    session = _secret_session(hero, tile=tile)
    session.clues_found = 3

    eng.advance(session, "reveal_secret_with_clues", character_id="h", secret_id="new_spell", spell_name="Fireball")

    assert "Fireball" in hero.spells
    assert session.secret_temporary_spells == {"h": ["Fireball"]}
    assert "new_spell" not in hero.secrets
    assert can_cast_spell(hero, "Fireball", expended_spells=[], healing_prayer_uses=0)


def test_magical_power_secret_grants_permanent_extra_use() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="wizard",
        class_name="Wizard",
        level=1,
        xp=0,
        gold=0,
        current_life=3,
        max_life=3,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        clues=3,
        spells=["Fireball"],
    )
    tile = TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")
    session = _secret_session(hero, tile=tile)
    session.clues_found = 3

    eng.advance(
        session,
        "reveal_secret_with_clues",
        character_id="h",
        secret_id="magical_power_increase",
        spell_name="Fireball",
    )

    assert "magical_power_increase:Fireball" in hero.secrets
    assert can_cast_spell(hero, "Fireball", expended_spells=["Fireball"], healing_prayer_uses=0)
    assert not can_cast_spell(hero, "Fireball", expended_spells=["Fireball", "Fireball"], healing_prayer_uses=0)


def test_magical_power_secret_extends_healing_prayer_uses() -> None:
    eng = engine()
    cleric = PartyMemberState(
        character_id="c",
        name="Cleric",
        class_id="cleric",
        class_name="Cleric",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        clues=3,
    )
    tile = TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")
    session = _secret_session(cleric, tile=tile)
    session.clues_found = 3

    eng.advance(
        session,
        "reveal_secret_with_clues",
        character_id="c",
        secret_id="magical_power_increase",
        spell_name="Healing prayer",
    )

    assert "magical_power_increase:Healing prayer" in cleric.secrets
    assert can_cast_spell(cleric, "Healing prayer", expended_spells=[], healing_prayer_uses=3)
    assert not can_cast_spell(cleric, "Healing prayer", expended_spells=[], healing_prayer_uses=4)


def test_dragonslayer_secret_grants_dragon_modifiers_only() -> None:
    dwarf = PartyMemberState(
        character_id="d",
        name="Dorin",
        class_id="dwarf",
        class_name="Dwarf",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["dragonslayer_bloodline"],
    )
    dragon = EnemyState(id="dragon", name="Dragon", category="boss", level=6, life=6, max_life=6, tags=["dragon"])
    ogre = EnemyState(id="ogre", name="Ogre", category="boss", level=5, life=4, max_life=4)

    assert secret_attack_bonus(dwarf, dragon) == 1
    assert secret_defense_bonus(dwarf, dragon) == 1
    assert secret_attack_bonus(dwarf, ogre) == 0
    assert secret_defense_bonus(dwarf, ogre) == 0


def test_weakness_secret_targets_major_foe_for_this_combat() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["weakness_of_a_foe"],
    )
    ogre = EnemyState(id="ogre", name="Ogre", category="boss", level=5, life=4, max_life=4)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[ogre],
    )
    session = _secret_session(hero, tile=tile, mode="combat")

    eng.advance(session, "use_secret", character_id="h", secret_id="weakness_of_a_foe", foe_id="ogre")

    assert hero.secrets == []
    assert session.secret_weakness_foe_id == "ogre"
    assert secret_weakness_attack_bonus(session, ogre) == 2


def test_enemy_in_dungeon_secret_replaces_major_foe_and_grants_bonus() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=2,
        xp=0,
        gold=0,
        current_life=6,
        max_life=6,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["enemy_in_dungeon"],
    )
    ogre = EnemyState(id="ogre", name="Ogre", category="boss", level=5, life=4, max_life=4)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[ogre],
    )
    session = _secret_session(hero, tile=tile, mode="combat")

    eng.advance(session, "use_secret", character_id="h", secret_id="enemy_in_dungeon", foe_id="ogre")

    assert hero.secrets == []
    assert ogre.name == "Chaos Champion"
    assert ogre.category == "boss"
    assert ogre.life == ogre.max_life
    assert session.secret_enemy_foe_id == "ogre"
    assert secret_weakness_attack_bonus(session, ogre) == 1


def test_prisoner_secret_adds_guarded_room_reward(monkeypatch) -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["prisoner"],
    )
    guard = EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[guard],
    )
    session = _secret_session(hero, tile=tile, mode="combat")
    monkeypatch.setattr("app.engine.dungeon_table_roller.roll_d6", lambda: 4)
    monkeypatch.setattr("app.engine.magic_weapons.roll_d6", lambda: 6)

    eng.advance(session, "use_secret", character_id="h", secret_id="prisoner", spell_name="magic")

    assert hero.secrets == []
    assert "Prisoner Reward" in tile.objects
    assert tile.treasure_claimed is False
    assert tile.treasure_items
    assert any("rescued NPC reward" in line for line in session.log)


def test_prisoner_secret_can_double_current_gold() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["prisoner"],
    )
    guard = EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[guard],
        treasure_gold=40,
    )
    session = _secret_session(hero, tile=tile, mode="combat")

    eng.advance(session, "use_secret", character_id="h", secret_id="prisoner", spell_name="gold")

    assert tile.treasure_gold == 80
    assert hero.secrets == []


def test_true_name_angel_rescues_and_heals() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=2,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["true_name_spiritual_entity"],
    )
    fallen = PartyMemberState(
        character_id="f",
        name="Fallen",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=0,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    tile = TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=[hero, fallen],
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    eng.advance(session, "use_secret", character_id="h", secret_id="true_name_spiritual_entity", spell_name="angel")

    assert hero.secrets == []
    assert hero.current_life == 5
    assert fallen.current_life > 0


def test_true_name_demon_damages_combat_foe() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
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
        secrets=["true_name_spiritual_entity"],
    )
    foe = EnemyState(id="d", name="Demon", category="boss", level=5, life=5, max_life=5)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[foe],
    )
    session = _secret_session(hero, tile=tile, mode="combat")

    eng.advance(
        session,
        "use_secret",
        character_id="h",
        secret_id="true_name_spiritual_entity",
        spell_name="demon",
        foe_id="d",
    )

    assert hero.secrets == []
    assert foe.life == 2


def test_true_name_demon_can_end_combat() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
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
        secrets=["true_name_spiritual_entity"],
    )
    foe = EnemyState(id="d", name="Demon", category="boss", level=5, life=3, max_life=3)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[foe],
        initial_enemy_count=1,
    )
    session = _secret_session(hero, tile=tile, mode="combat")

    eng.advance(
        session,
        "use_secret",
        character_id="h",
        secret_id="true_name_spiritual_entity",
        spell_name="demon",
        foe_id="d",
    )

    assert session.mode == "exploration"
    assert tile.resolved is True
    assert session.xp_rolls_pending == 1


def test_deal_with_a_foe_ends_eligible_encounter_without_rewards() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        secrets=["deal_with_a_foe"],
    )
    goblin = EnemyState(id="g", name="Goblin", category="minions", level=3, life=1, max_life=1)
    tile = TileState(
        id="t",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="R",
        description="R",
        enemies=[goblin],
    )
    session = _secret_session(hero, tile=tile, mode="combat")

    eng.advance(session, "use_secret", character_id="h", secret_id="deal_with_a_foe")

    assert hero.secrets == []
    assert session.mode == "exploration"
    assert tile.enemies == []
    assert tile.defeated_enemies == []
    assert session.xp_rolls_pending == 0
    assert any("no treasure or XP" in line for line in session.log)


def test_secret_diet_consumes_ration_for_temporary_life_bonus() -> None:
    eng = engine()
    hero = PartyMemberState(
        character_id="h",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        inventory=["Food ration"],
        secrets=["secret_diet"],
    )
    tile = TileState(id="t", x=0, y=0, tile_key="01", tile_type="room", title="E", description="E")
    session = _secret_session(hero, tile=tile)
    session.camped_outside = True

    eng.advance(session, "use_secret", character_id="h", secret_id="secret_diet")

    assert hero.secrets == []
    assert hero.inventory == []
    assert hero.current_life == 6
    assert hero.max_life == 6
    assert session.secret_diet_character_ids == ["h"]


def test_clues_can_teach_eligible_expert_spell() -> None:
    eng = engine()
    wizard = PartyMemberState(
        character_id="wiz",
        name="Magus",
        class_id="wizard",
        class_name="Wizard",
        level=5,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
        spells=[],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        clues_found=3,
        party=[wizard],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    eng.advance(session, "learn_spell_with_clues", character_id="wiz", expert_skill_id="healing_surge")

    assert session.clues_found == 0
    assert wizard.clues == 0
    assert "healing_surge" in wizard.learned_expert_skills
    assert "Healing Surge" in wizard.spells


def test_clues_can_teach_eligible_druid_spell() -> None:
    eng = engine()
    druid = PartyMemberState(
        character_id="d",
        name="Oak",
        class_id="druid",
        class_name="Druid",
        level=5,
        xp=0,
        gold=0,
        current_life=5,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        expert_trained=True,
        spells=[],
    )
    session = SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        clues_found=3,
        party=[druid],
        map_state=MapState(
            tiles=[TileState(id="t", x=0, y=0, tile_key="11", tile_type="room", title="R", description="R")],
            current_tile_id="t",
        ),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )

    eng.advance(session, "learn_spell_with_clues", character_id="d", expert_skill_id="barkskin")

    assert session.clues_found == 0
    assert druid.clues == 0
    assert druid.learned_expert_skills == ["barkskin"]
    assert "Barkskin" in druid.spells
