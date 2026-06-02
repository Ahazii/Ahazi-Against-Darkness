from __future__ import annotations

from app.engine.class_abilities import (
    kukla_compartment_retrieve,
    kukla_compartment_stash,
    kukla_green_ring_revive,
    kukla_red_ring_poison,
)
from app.schemas import EnemyState, MapState, PartyMemberState, SessionState, TileState


def _kukla(cid: str, name: str, *, life: int = 5, inventory: list[str] | None = None) -> PartyMemberState:
    return PartyMemberState(
        character_id=cid,
        name=name,
        class_id="kukla",
        class_name="Kukla",
        level=4,
        xp=0,
        gold=20,
        current_life=life,
        max_life=9,
        attack_bonus=1,
        defense_bonus=2,
        save_bonus=0,
        marching_order=1,
        inventory=inventory or ["Dagger", "Green ring", "Red ring"],
    )


def _session(*, party: list[PartyMemberState], tile: TileState) -> SessionState:
    return SessionState(
        id="s",
        party_id="p",
        adventure_id="a",
        adventure_type="random",
        mode="exploration",
        party=party,
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )


def test_kukla_green_ring_revives_fallen() -> None:
    tile = TileState(
        id="t1",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="Room",
        description="",
        fallen_character_ids=["k2"],
    )
    actor = _kukla("k1", "Dolly")
    fallen = _kukla("k2", "Broken", life=0, inventory=["Green ring"])
    session = _session(party=[actor, fallen], tile=tile)
    logs = kukla_green_ring_revive(session, actor, fallen, tile, show_rolls=False)
    assert fallen.current_life == 4
    assert "k2" not in tile.fallen_character_ids
    assert any("restored" in line.lower() for line in logs)


def test_kukla_compartment_stash_and_retrieve() -> None:
    kukla = _kukla("k1", "Dolly", inventory=["Dagger", "Bandage"])
    logs = kukla_compartment_stash(kukla, "Bandage")
    assert "hide" in logs[0].lower()
    assert "Bandage" in kukla.kukla_compartment_items
    assert "Bandage" not in kukla.inventory
    logs = kukla_compartment_retrieve(kukla, "Bandage")
    assert "retrieve" in logs[0].lower()
    assert "Bandage" in kukla.inventory


def test_kukla_red_ring_poison_damages_foe(monkeypatch) -> None:
    monkeypatch.setattr("app.engine.class_abilities.roll_exploding_for_level", lambda _level: (1, [1]))
    kukla = _kukla("k1", "Dolly")
    foe = EnemyState(id="g1", name="Guard", category="minions", level=3, life=4, max_life=4)
    logs = kukla_red_ring_poison(None, kukla, foe, show_rolls=False)
    assert foe.life == 2
    assert "poisoned" in foe.tags
    assert not any("red ring" in item.lower() for item in kukla.inventory)
    assert any("poison" in line.lower() for line in logs)
