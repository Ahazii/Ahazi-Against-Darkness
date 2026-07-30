from app.engine.adventure_completion import (
    AdventureCompletionCallbacks,
    complete_adventure,
    repair_completed_explored_summary,
)
from app.schemas import AlchemistOrderState, MapState, PartyMemberState, SessionState, TileState


def _session(*, xp_system: str = "classical") -> SessionState:
    hero = PartyMemberState(
        character_id="hero",
        name="Hero",
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=1,
        max_life=4,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=0,
    )
    tile = TileState(
        id="entrance",
        x=0,
        y=0,
        tile_key="01",
        tile_type="room",
        title="Entrance",
        description="Entrance",
        content_key="entrance",
    )
    return SessionState(
        id="session",
        party_id="party",
        adventure_id="random",
        adventure_type="random",
        party=[hero],
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        xp_system=xp_system,
    )


def _callbacks(calls: list[str]) -> AdventureCompletionCallbacks:
    return AdventureCompletionCallbacks(
        apply_prisoner_exit_reward=lambda _session: calls.append("prisoner"),
        trigger_exit_ambush=lambda _session: calls.append("ambush") and False,
        complete_level_up=lambda _session, member: calls.append(f"level:{member.name}"),
        reset_between_foray_resources=lambda _session: calls.append("reset"),
    )


def test_complete_adventure_blocks_pending_classical_xp_before_callbacks() -> None:
    session = _session()
    session.xp_rolls_pending = 1
    calls: list[str] = []

    assert not complete_adventure(session, callbacks=_callbacks(calls))
    assert calls == []
    assert session.mode == "exploration"
    assert any("XP roll" in line and "before completing" in line for line in session.log)


def test_complete_adventure_applies_standard_exit_sequence() -> None:
    session = _session(xp_system="slow_and_sure")
    calls: list[str] = []

    assert complete_adventure(session, callbacks=_callbacks(calls))
    assert calls == ["ambush", "level:Hero", "reset"]
    assert session.mode == "complete"
    assert session.party[0].current_life == session.party[0].max_life
    assert session.summary[0] == "Explored 1 map element."
    assert any("Slow and Sure" in line for line in session.log)


def test_complete_adventure_puts_commission_delivery_in_summary() -> None:
    session = _session()
    session.alchemist_order = AlchemistOrderState(
        potion_id="potion_of_healing",
        potion_name="Potion of Healing",
        character_id="hero",
        difficulty=0,
        material_gp=10,
    )

    assert complete_adventure(session, callbacks=_callbacks([]))

    assert "Potion of Healing" in session.party[0].inventory
    assert "Town return: Hero receives Potion of Healing." in session.summary


def test_complete_adventure_counts_visited_imported_elements_not_prebuilt_manifest() -> None:
    session = _session()
    session.adventure_type = "imported"
    session.map_state.tiles.extend(
        [
            TileState(
                id=f"prebuilt-{index}",
                x=index,
                y=0,
                tile_key="01",
                tile_type="room",
                title=f"Prebuilt {index}",
                description="Not visited.",
                content_key=f"imported:prebuilt-{index}",
            )
            for index in range(1, 7)
        ]
    )
    session.visited_tile_ids = ["entrance", "prebuilt-1"]
    session.map_state.current_tile_id = "prebuilt-1"

    assert complete_adventure(session, callbacks=_callbacks([]))

    assert "Explored 2 map elements." in session.summary


def test_completed_session_repairs_stored_prebuilt_manifest_count() -> None:
    session = _session()
    session.mode = "complete"
    session.visited_tile_ids = ["entrance", "visited-room"]
    session.map_state.current_tile_id = "visited-room"
    session.summary = ["Quest objective complete.", "Explored 7 map elements."]

    assert repair_completed_explored_summary(session)
    assert session.summary == ["Quest objective complete.", "Explored 2 map elements."]
    assert not repair_completed_explored_summary(session)
