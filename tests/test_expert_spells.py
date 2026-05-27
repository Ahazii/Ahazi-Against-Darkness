from __future__ import annotations

from pathlib import Path

from app.engine import expert_spells, spells
from app.engine.combat import apply_enemy_damage, tick_enemy_regeneration
from app.engine.random_dungeon import RandomDungeonEngine
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def wizard(*, level: int = 6, life: int = 8, spell_list: list[str] | None = None) -> PartyMemberState:
    return PartyMemberState(
        character_id="wiz",
        name="Marius",
        class_id="wizard",
        class_name="Wizard",
        level=level,
        xp=0,
        gold=0,
        current_life=life,
        max_life=life,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        spells=spell_list or ["Healing Surge", "Infallible Missile", "Lifeforce Control", "Mass Teleport", "Aura of Terror", "Reverse Gaze"],
    )


def ally(**kwargs) -> PartyMemberState:
    defaults = dict(
        character_id="ally",
        name="Ally",
        class_id="warrior",
        class_name="Warrior",
        level=5,
        xp=0,
        gold=0,
        current_life=4,
        max_life=6,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    defaults.update(kwargs)
    return PartyMemberState(**defaults)


def goblin(*, foe_id: str = "g1") -> EnemyState:
    return EnemyState(
        id=foe_id,
        name="Goblin",
        category="minions",
        level=3,
        life=1,
        max_life=1,
    )


def vampire() -> EnemyState:
    return EnemyState(
        id="vamp",
        name="Vampire",
        category="boss",
        level=7,
        life=6,
        max_life=6,
        tags=["vampire", "undead"],
    )


def medusa() -> EnemyState:
    return EnemyState(
        id="med",
        name="Medusa",
        category="boss",
        level=8,
        life=5,
        max_life=5,
        tags=["gaze"],
    )


def test_healing_surge_heals_allies_and_harms_vampires() -> None:
    caster = wizard(life=6)
    partner = ally(current_life=2, max_life=6)
    vamp = vampire()
    log: list[str] = []
    outcome = expert_spells.cast_healing_surge(caster, [caster, partner], [vamp], log)
    assert partner.current_life == 4
    assert vamp.life == 4
    assert outcome.spell_consumed is True


def test_infallible_missile_slays_minion(monkeypatch) -> None:
    monkeypatch.setattr(expert_spells, "roll_exploding_for_level", lambda level: (2, [2]))
    caster = wizard()
    foe = goblin()
    outcome = expert_spells.cast_infallible_missile(
        caster,
        [caster],
        [foe],
        [],
        show_rolls=False,
        target_foe_id="g1",
    )
    assert foe.life == 0
    assert outcome.combat_over is True


def test_infallible_missile_dual_at_level_eight(monkeypatch) -> None:
    rolls = iter([(2, [2]), (2, [2])])
    monkeypatch.setattr(expert_spells, "roll_exploding_for_level", lambda level: next(rolls))
    caster = wizard(level=8)
    foes = [goblin(foe_id="g1"), goblin(foe_id="g2")]
    log: list[str] = []
    expert_spells.cast_infallible_missile(
        caster,
        [caster],
        foes,
        log,
        show_rolls=False,
        target_foe_id="g1",
    )
    assert any("two infallible missiles" in line.lower() for line in log)


def test_lifeforce_control_transfers_life_to_ally() -> None:
    caster = wizard(life=6)
    partner = ally(current_life=2, max_life=6)
    outcome = expert_spells.cast_lifeforce_control(
        caster,
        [caster, partner],
        [],
        [],
        target_character_id="ally",
        target_foe_id=None,
        life_transfer_amount=3,
    )
    assert caster.current_life == 3
    assert partner.current_life == 5
    assert outcome.spell_consumed is True


def test_lifeforce_control_drains_vampire() -> None:
    caster = wizard(life=6)
    vamp = vampire()
    outcome = expert_spells.cast_lifeforce_control(
        caster,
        [caster],
        [vamp],
        [],
        target_character_id=None,
        target_foe_id="vamp",
        life_transfer_amount=2,
    )
    assert caster.current_life == 4
    assert vamp.life == 4
    assert outcome.spell_consumed is True


def test_mass_teleport_costs_life_and_teleports(monkeypatch) -> None:
    caster = wizard(life=6)
    partner = ally()
    log: list[str] = []
    outcome = expert_spells.cast_mass_teleport(
        caster,
        [caster, partner],
        [],
        log,
        teleport_tile_id="room-b",
        teleport_character_ids=["wiz", "ally"],
    )
    assert caster.current_life == 5
    assert outcome.teleport_to_tile_id == "room-b"
    assert outcome.combat_over is True


def test_aura_of_terror_flees_on_low_morale(monkeypatch) -> None:
    monkeypatch.setattr(expert_spells, "roll_d6", lambda: 2)
    caster = wizard()
    foe = goblin()
    outcome = expert_spells.cast_aura_of_terror(
        caster,
        [caster],
        [foe],
        [],
        show_rolls=False,
        target_foe_id="g1",
        final_boss=False,
    )
    assert foe.life == 0
    assert outcome.combat_over is True


def test_aura_of_terror_immune_undead() -> None:
    caster = wizard()
    foe = vampire()
    outcome = expert_spells.cast_aura_of_terror(
        caster,
        [caster],
        [foe],
        [],
        show_rolls=False,
        target_foe_id="vamp",
        final_boss=False,
    )
    assert foe.life == 6
    assert outcome.spell_consumed is True


def test_reverse_gaze_petrifies_medusa(monkeypatch) -> None:
    monkeypatch.setattr(expert_spells, "roll_die", lambda sides: 6)
    caster = wizard(level=6)
    foe = medusa()
    outcome = expert_spells.cast_reverse_gaze(
        caster,
        [caster],
        [foe],
        [],
        show_rolls=False,
        target_foe_id="med",
    )
    assert foe.life == 0
    assert "petrified" in {tag.lower() for tag in foe.tags}
    assert outcome.combat_over is True


def test_resolve_spell_cast_routes_expert_spell() -> None:
    caster = wizard(spell_list=["Healing Surge"])
    partner = ally(current_life=2, max_life=6)
    outcome = spells.resolve_spell_cast("Healing Surge", caster, [caster, partner], [], show_rolls=False)
    assert partner.current_life == 4
    assert outcome.spell_consumed is True


def test_mass_teleport_in_session() -> None:
    from app.rules.repository import RulesRepository

    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    engine = RandomDungeonEngine(
        RulesRepository(packaged, packaged / "_override"),
        Path(__file__).resolve().parents[1] / "assets",
    )
    caster = wizard(spell_list=["Mass Teleport"])
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        mode="exploration",
        party=[caster],
        map_state=MapState(
            tiles=[
                TileState(
                    id="room-a",
                    x=0,
                    y=0,
                    tile_key="11",
                    tile_type="room",
                    title="Start",
                    description="Start",
                ),
                TileState(
                    id="room-b",
                    x=1,
                    y=0,
                    tile_key="12",
                    tile_type="room",
                    title="Hall",
                    description="Hall",
                ),
            ],
            current_tile_id="room-a",
        ),
        created_at="2026-05-19T00:00:00+00:00",
        updated_at="2026-05-19T00:00:00+00:00",
    )
    engine.advance(
        session,
        "cast_spell",
        character_id="wiz",
        spell_name="Mass Teleport",
        teleport_tile_id="room-b",
    )
    assert session.map_state.current_tile_id == "room-b"
    assert "Mass Teleport" in session.expended_spells.get("wiz", [])


def test_save_session_accepts_label(monkeypatch) -> None:
    import importlib
    from tempfile import TemporaryDirectory

    from fastapi.testclient import TestClient

    with TemporaryDirectory() as data_dir:
        monkeypatch.setenv("DATA_DIR", data_dir)
        main = importlib.import_module("app.main")
        main = importlib.reload(main)
        client = TestClient(main.app)

        classes = client.get("/api/rules/classes").json()
        character_ids = []
        for index, class_id in enumerate([item["id"] for item in classes[:4]], start=1):
            response = client.post(
                "/api/characters",
                json={"name": f"Save Hero {index}", "class_id": class_id},
            )
            assert response.status_code == 200
            character_ids.append(response.json()["id"])

        party_id = client.post(
            "/api/parties",
            json={"name": "Save Party", "character_ids": character_ids},
        ).json()["id"]

        from app.engine import random_dungeon

        monkeypatch.setattr(random_dungeon, "roll_start_tile_key", lambda: "01")

        session_id = client.post(
            "/api/sessions",
            json={"party_id": party_id, "adventure_id": "random"},
        ).json()["id"]

        response = client.post(
            f"/api/sessions/{session_id}/save",
            json={"label": "Floor 3 — boss room"},
        )
        assert response.status_code == 200
        saved = response.json()
        assert saved["save_label"] == "Floor 3 — boss room"
