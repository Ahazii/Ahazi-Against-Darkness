from __future__ import annotations

from app.engine.tag_mutant_fish import (
    begin_mutant_fish_scene,
    mutant_fish_state,
    rescue_mutant_fish_victim,
    resolve_mutant_fish_reward,
    set_chaos_cultist_friendship,
    set_mutant_fish_state,
)
from app.schemas import (
    ActiveQuestState,
    CampaignState,
    MapState,
    PartyMemberState,
    SessionState,
    TileState,
)


def _member(
    character_id: str,
    *,
    name: str | None = None,
    life: int = 5,
    save_bonus: int = 0,
    statuses: list[str] | None = None,
    inventory: list[str] | None = None,
) -> PartyMemberState:
    return PartyMemberState(
        character_id=character_id,
        name=name or character_id.title(),
        class_id="warrior",
        class_name="Warrior",
        level=1,
        xp=0,
        gold=0,
        current_life=life,
        max_life=5,
        attack_bonus=0,
        defense_bonus=0,
        save_bonus=save_bonus,
        statuses=statuses or [],
        inventory=inventory or [],
    )


def _session(party: list[PartyMemberState]) -> SessionState:
    tile = TileState(
        id="pool",
        x=0,
        y=0,
        tile_key="11",
        tile_type="room",
        title="The Bridge Pool",
        description="Mutant fish chant beneath the bridge.",
    )
    return SessionState(
        id="mutant-fish-session",
        party_id="party",
        campaign_id="default",
        adventure_id="rumor-4",
        adventure_type="imported",
        party=party,
        map_state=MapState(tiles=[tile], current_tile_id=tile.id),
        active_quest=ActiveQuestState(
            tile_id=tile.id,
            key="tag_generated_scene",
            description="Resolve the Mutant Fish scene.",
        ),
        created_at="2026-07-29T00:00:00Z",
        updated_at="2026-07-29T00:00:00Z",
    )


def _campaign(*, friendly: bool = False) -> CampaignState:
    return CampaignState(
        id="default",
        tag_friendly_chaos_cultists=friendly,
        created_at="2026-07-29T00:00:00Z",
        updated_at="2026-07-29T00:00:00Z",
    )


def test_party_hypnosis_rolls_each_hero_and_chaos_taint_fails_automatically() -> None:
    party = [
        _member("safe", name="Safe Hero"),
        _member("failed", name="Failed Hero"),
        _member("tainted", name="Tainted Hero", statuses=["Chaos-tainted"]),
        _member("second-safe", name="Second Safe"),
    ]
    session = _session(party)
    rolls = {"safe": (5, [5]), "failed": (2, [2]), "second-safe": (6, [6])}

    begin_mutant_fish_scene(session, roller=lambda member: rolls[member.character_id])

    state = mutant_fish_state(session)
    assert state["phase"] == "rescue"
    assert state["in_water_character_ids"] == ["failed", "tainted"]
    assert len(state["initial_saves"]) == 4
    tainted = next(result for result in state["initial_saves"] if result["character_id"] == "tainted")
    assert tainted["automatic_failure"] is True
    assert tainted["rolls"] == []


def test_failed_rescuer_replaces_rescued_victim_in_water(monkeypatch) -> None:
    rescuer = _member("rescuer", name="Rescuer")
    victim = _member("victim", name="Victim")
    session = _session([rescuer, victim])
    set_mutant_fish_state(
        session,
        {
            "phase": "rescue",
            "initial_saves": [],
            "rescue_saves": [],
            "rescue_turns": 0,
            "in_water_character_ids": ["victim"],
        },
    )

    rescue_mutant_fish_victim(
        session,
        rescuer_id="rescuer",
        victim_id="victim",
        roller=lambda _member: (2, [2]),
    )

    state = mutant_fish_state(session)
    assert state["phase"] == "rescue"
    assert state["in_water_character_ids"] == ["rescuer"]
    assert victim.current_life == 4
    assert rescuer.current_life == 5
    assert state["rescue_saves"][0]["passed"] is False

    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_d6", lambda: 4)
    rescue_mutant_fish_victim(
        session,
        rescuer_id="victim",
        victim_id="rescuer",
        roller=lambda _member: (5, [5]),
    )

    state = mutant_fish_state(session)
    assert state["phase"] == "reward"
    assert state["in_water_character_ids"] == []
    assert state["ration_count"] == 7
    assert rescuer.current_life == 4
    assert session.minor_encounters_defeated == 2


def test_everyone_failing_initial_save_destroys_party() -> None:
    session = _session([_member("one"), _member("two")])

    begin_mutant_fish_scene(session, roller=lambda _member: (1, [1]))

    assert session.mode == "complete"
    assert all(member.current_life == 0 for member in session.party)
    assert mutant_fish_state(session)["phase"] == "destroyed"
    assert session.minor_encounters_defeated == 0


def test_survival_rolls_reward_once_and_kept_rations_respect_capacity(monkeypatch) -> None:
    preferred = _member(
        "preferred",
        name="Preferred",
        inventory=["Food ration"] * 8,
    )
    second = _member("second", name="Second")
    session = _session([preferred, second])
    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_d6", lambda: 6)

    begin_mutant_fish_scene(session, roller=lambda _member: (5, [5]))

    assert mutant_fish_state(session)["ration_count"] == 9
    assert session.minor_encounters_defeated == 2
    result = resolve_mutant_fish_reward(
        session,
        _campaign(),
        choice="keep",
        recipient_id="preferred",
    )

    assert "keeps 9" in result
    assert sum(item == "Food ration" for item in preferred.inventory) == 10
    assert sum(item == "Food ration" for item in second.inventory) == 7
    assert mutant_fish_state(session)["reward_claimed"] is True


def test_friendly_chaos_cultists_persist_and_raise_sale_price(monkeypatch) -> None:
    session = _session([_member("seller", name="Seller")])
    campaign = _campaign()
    set_chaos_cultist_friendship(campaign)
    monkeypatch.setattr("app.engine.tag_mutant_fish.roll_d6", lambda: 3)
    begin_mutant_fish_scene(session, roller=lambda _member: (5, [5]))

    result = resolve_mutant_fish_reward(
        session,
        campaign,
        choice="sell",
        recipient_id="seller",
    )

    assert campaign.tag_friendly_chaos_cultists is True
    assert "5gp each" in result
    assert session.party[0].gold == 30
    assert mutant_fish_state(session)["sale_total_gp"] == 30
