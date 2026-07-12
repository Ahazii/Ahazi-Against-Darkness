from app.engine.combat_lifecycle import consume_sleeping_foe_attack_bonus, merge_party_outcome
from app.schemas import MapState, PartyMemberState, SessionState, TileState


def _member(character_id: str, order: int, *, life: int = 4) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=character_id,
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=life,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
        marching_order=order,
    )


def test_merge_party_outcome_preserves_party_order_and_noncombat_members() -> None:
    first = _member("first", 1)
    second = _member("second", 2)
    updated_second = second.model_copy(deep=True)
    updated_second.current_life = 2

    merged = merge_party_outcome([first, second], [updated_second])

    assert [member.character_id for member in merged] == ["first", "second"]
    assert merged[0].current_life == 4
    assert merged[1].current_life == 2


def test_sleeping_foe_bonus_applies_once_to_current_combat_group() -> None:
    first = _member("first", 1)
    first.statuses = ["Sleeping foe +2 first Attack", "Other effect"]
    elsewhere = _member("elsewhere", 2)
    tile = TileState(
        id="tile",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Room",
        description="Room",
        content_key="empty",
    )
    session = SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[first, elsewhere],
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        detached_groups=[],
        reaction_sleep_attack_bonus=2,
    )

    assert consume_sleeping_foe_attack_bonus(session, tile) == 2
    assert first.statuses == ["Other effect"]
    assert consume_sleeping_foe_attack_bonus(session, tile) == 0
