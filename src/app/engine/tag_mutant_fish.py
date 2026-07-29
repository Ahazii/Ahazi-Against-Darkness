from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..db import now_utc
from ..schemas import CampaignState, PartyMemberState, SessionState
from .class_combat import save_modifier
from .dice import roll_d6, roll_exploding_for_level
from .experience import record_minor_encounter_progress

MUTANT_FISH_STATE_KEY = "mutant_fish_scene12"
MUTANT_FISH_SAVE_LEVEL = 5
MUTANT_FISH_NORMAL_SALE_GP = 2
MUTANT_FISH_FRIENDLY_CULTIST_SALE_GP = 5


def mutant_fish_state(session: SessionState) -> dict[str, Any]:
    quest = session.active_quest
    if quest is None:
        return {}
    return dict((quest.tag_procedure_state or {}).get(MUTANT_FISH_STATE_KEY) or {})


def set_mutant_fish_state(session: SessionState, state: dict[str, Any]) -> None:
    quest = session.active_quest
    if quest is None:
        raise ValueError("The Mutant Fish generated quest state is missing.")
    procedure_state = dict(quest.tag_procedure_state or {})
    procedure_state[MUTANT_FISH_STATE_KEY] = dict(state)
    quest.tag_procedure_state = procedure_state


def character_is_chaos_tainted(member: PartyMemberState) -> bool:
    text = " ".join(
        [
            str(member.class_id or ""),
            str(member.class_name or ""),
            *(str(value) for value in member.class_traits or []),
            *(str(value) for value in member.statuses or []),
        ]
    ).casefold()
    return any(marker in text for marker in ("chaos-tainted", "chaos tainted", "chaos_tainted"))


def _living_member(session: SessionState, character_id: str) -> PartyMemberState | None:
    return next(
        (
            member
            for member in session.party
            if member.character_id == character_id and member.current_life > 0
        ),
        None,
    )


def _roll_hypnosis_save(
    session: SessionState,
    member: PartyMemberState,
    *,
    roller: Callable[[PartyMemberState], tuple[int, list[int]]] | None = None,
) -> dict[str, Any]:
    if character_is_chaos_tainted(member):
        return {
            "character_id": member.character_id,
            "name": member.name,
            "rolls": [],
            "modifier": 0,
            "total": 0,
            "passed": False,
            "automatic_failure": True,
        }
    roll_save = roller or (lambda actor: roll_exploding_for_level(actor, session=session))
    total, rolls = roll_save(member)
    modifier = save_modifier(
        member,
        save_label="Mutant Fish hypnosis",
        session=session,
    )
    passed = bool(rolls and rolls[0] != 1 and total + modifier >= MUTANT_FISH_SAVE_LEVEL)
    return {
        "character_id": member.character_id,
        "name": member.name,
        "rolls": list(rolls),
        "modifier": modifier,
        "total": total + modifier,
        "passed": passed,
        "automatic_failure": False,
    }


def _save_text(result: dict[str, Any]) -> str:
    if result.get("automatic_failure"):
        return f"{result['name']} is chaos-tainted and automatically fails."
    rolls = " + ".join(str(value) for value in result.get("rolls") or [])
    modifier = int(result.get("modifier") or 0)
    modifier_text = f" {modifier:+d}" if modifier else ""
    outcome = "passes" if result.get("passed") else "fails"
    return (
        f"{result['name']} rolls {rolls}{modifier_text} = {int(result.get('total') or 0)} "
        f"vs L{MUTANT_FISH_SAVE_LEVEL}: {outcome}."
    )


def _mark_party_destroyed(session: SessionState, state: dict[str, Any], reason: str) -> str:
    for member in session.party:
        if member.current_life > 0:
            member.current_life = 0
    state.update(
        {
            "phase": "destroyed",
            "in_water_character_ids": [],
            "result_text": reason,
            "updated_at": now_utc(),
        }
    )
    set_mutant_fish_state(session, state)
    session.mode = "complete"
    session.summary = [
        "The entire party was destroyed by the mutant fish hypnosis.",
        "No mutant-fish rations or Scene 12 XP progress were awarded.",
    ]
    session.log.append(reason)
    return reason


def begin_mutant_fish_scene(
    session: SessionState,
    *,
    roller: Callable[[PartyMemberState], tuple[int, list[int]]] | None = None,
) -> str:
    current = mutant_fish_state(session)
    if current:
        raise ValueError("Scene 12's party hypnosis Saves have already been rolled.")
    living = [member for member in session.party if member.current_life > 0]
    if not living:
        raise ValueError("No living party member can approach the bridge pool.")
    results = [_roll_hypnosis_save(session, member, roller=roller) for member in living]
    in_water = [str(result["character_id"]) for result in results if not result["passed"]]
    state: dict[str, Any] = {
        "phase": "rescue" if in_water else "reward",
        "initial_saves": results,
        "rescue_saves": [],
        "rescue_turns": 0,
        "in_water_character_ids": in_water,
        "updated_at": now_utc(),
    }
    lines = [f"Mutant Fish hypnosis (TAG p.29, Scene 12): {_save_text(result)}" for result in results]
    session.log.extend(lines)
    if len(in_water) == len(living):
        return _mark_party_destroyed(
            session,
            state,
            "Every living hero fails the hypnosis Save. TAG p.29, Scene 12 destroys the party.",
        )
    if in_water:
        names = ", ".join(
            member.name for member in living if member.character_id in set(in_water)
        )
        result_text = (
            f"{names} {'is' if len(in_water) == 1 else 'are'} in the water. "
            "Choose a safe hero to spend one turn rescuing one victim."
        )
        state["result_text"] = result_text
        set_mutant_fish_state(session, state)
        session.log.append(result_text)
        return result_text
    return _open_mutant_fish_reward(session, state)


def rescue_mutant_fish_victim(
    session: SessionState,
    *,
    rescuer_id: str,
    victim_id: str,
    roller: Callable[[PartyMemberState], tuple[int, list[int]]] | None = None,
) -> str:
    state = mutant_fish_state(session)
    if state.get("phase") != "rescue":
        raise ValueError("Scene 12 is not waiting for a rescue turn.")
    in_water = [str(value) for value in state.get("in_water_character_ids") or []]
    if victim_id not in in_water:
        raise ValueError("Choose a living hypnotized character to rescue.")
    if rescuer_id in in_water:
        raise ValueError("A hypnotized character cannot rescue another hero.")
    rescuer = _living_member(session, rescuer_id)
    victim = _living_member(session, victim_id)
    if rescuer is None:
        raise ValueError("Choose a living, non-hypnotized rescuer.")
    if victim is None:
        raise ValueError("The selected victim is no longer alive to rescue.")

    state["rescue_turns"] = int(state.get("rescue_turns") or 0) + 1
    damage_lines: list[str] = []
    for character_id in list(in_water):
        trapped = _living_member(session, character_id)
        if trapped is None:
            continue
        trapped.current_life = max(0, trapped.current_life - 1)
        damage_lines.append(
            f"{trapped.name} loses 1 Life in the water ({trapped.current_life}/{trapped.max_life})."
        )
    in_water = [
        character_id
        for character_id in in_water
        if (member := next((item for item in session.party if item.character_id == character_id), None))
        is not None
        and member.current_life > 0
    ]
    victim_survived = victim_id in in_water
    if victim_survived:
        in_water.remove(victim_id)
        rescue_text = f"{rescuer.name} spends the turn moving {victim.name} out of the water."
    else:
        rescue_text = f"{victim.name} falls before {rescuer.name} can move them out of the water."

    rescue_save = _roll_hypnosis_save(session, rescuer, roller=roller)
    state.setdefault("rescue_saves", []).append(
        {
            **rescue_save,
            "rescuer_id": rescuer_id,
            "victim_id": victim_id,
            "turn": state["rescue_turns"],
        }
    )
    if not rescue_save["passed"] and rescuer.current_life > 0:
        in_water.append(rescuer_id)
    state["in_water_character_ids"] = list(dict.fromkeys(in_water))
    state["updated_at"] = now_utc()
    lines = [
        f"Mutant Fish rescue turn {state['rescue_turns']} (TAG p.29, Scene 12):",
        *damage_lines,
        rescue_text,
        _save_text(rescue_save),
    ]
    session.log.extend(lines)

    if not state["in_water_character_ids"]:
        return _open_mutant_fish_reward(session, state)
    safe = [
        member
        for member in session.party
        if member.current_life > 0 and member.character_id not in set(state["in_water_character_ids"])
    ]
    if not safe:
        return _mark_party_destroyed(
            session,
            state,
            "No living hero remains outside the water to continue the rescue. The party is destroyed.",
        )
    trapped_names = ", ".join(
        member.name
        for member in session.party
        if member.character_id in set(state["in_water_character_ids"])
    )
    result_text = (
        f"{' '.join(damage_lines)} {rescue_text} {_save_text(rescue_save)} "
        f"Still in the water: {trapped_names}."
    )
    state["result_text"] = result_text
    set_mutant_fish_state(session, state)
    return result_text


def _open_mutant_fish_reward(session: SessionState, state: dict[str, Any]) -> str:
    if not state.get("xp_recorded"):
        record_minor_encounter_progress(
            session,
            2,
            reason="Mutant Fish scene (TAG p.29, Scene 12)",
            show_rolls=True,
        )
        state["xp_recorded"] = True
    if not state.get("ration_count"):
        state["ration_roll"] = roll_d6()
        state["ration_count"] = int(state["ration_roll"]) + 3
    state["phase"] = "reward"
    state["in_water_character_ids"] = []
    state["updated_at"] = now_utc()
    result_text = (
        f"Everyone has passed or been rescued. The fish yield d6+3 = "
        f"{state['ration_roll']}+3 = {state['ration_count']} Food rations. "
        "Choose whether to keep or sell them."
    )
    state["result_text"] = result_text
    set_mutant_fish_state(session, state)
    session.log.append(result_text)
    return result_text


def _food_ration_count(member: PartyMemberState) -> int:
    return sum(1 for item in member.inventory if "food ration" in str(item).casefold())


def _distribute_rations(
    session: SessionState,
    count: int,
    *,
    preferred_character_id: str,
) -> list[tuple[str, int]]:
    living = [member for member in session.party if member.current_life > 0]
    preferred = next(
        (member for member in living if member.character_id == preferred_character_id),
        None,
    )
    if preferred is None:
        raise ValueError("Choose a living hero to carry the mutant-fish rations.")
    ordered = [preferred, *(member for member in living if member is not preferred)]
    capacity = sum(max(0, 10 - _food_ration_count(member)) for member in ordered)
    if capacity < count:
        raise ValueError(
            f"The living party has room for only {capacity} more Food ration(s); "
            f"Scene 12 produced {count}. Sell them instead or free carrying capacity."
        )
    remaining = count
    allocations: list[tuple[str, int]] = []
    for member in ordered:
        amount = min(remaining, max(0, 10 - _food_ration_count(member)))
        if amount <= 0:
            continue
        member.inventory.extend(["Food ration"] * amount)
        allocations.append((member.name, amount))
        remaining -= amount
        if remaining <= 0:
            break
    return allocations


def resolve_mutant_fish_reward(
    session: SessionState,
    campaign: CampaignState,
    *,
    choice: str,
    recipient_id: str,
) -> str:
    state = mutant_fish_state(session)
    if state.get("phase") != "reward":
        raise ValueError("Resolve the hypnosis and rescue sequence before taking the fish.")
    if state.get("reward_claimed"):
        raise ValueError("The mutant-fish reward has already been claimed.")
    recipient = _living_member(session, recipient_id)
    if recipient is None:
        raise ValueError("Choose a living hero to receive the kept rations or sale proceeds.")
    count = int(state.get("ration_count") or 0)
    if count <= 0:
        raise ValueError("The mutant-fish ration roll is missing.")

    clean_choice = str(choice or "").strip().casefold()
    if clean_choice == "keep":
        allocations = _distribute_rations(
            session,
            count,
            preferred_character_id=recipient_id,
        )
        allocation_text = ", ".join(f"{name} {amount}" for name, amount in allocations)
        result_text = f"The party keeps {count} mutant-fish Food rations ({allocation_text})."
        state["reward_kind"] = "kept"
        state["ration_allocations"] = [
            {"name": name, "count": amount} for name, amount in allocations
        ]
    elif clean_choice == "sell":
        unit_price = (
            MUTANT_FISH_FRIENDLY_CULTIST_SALE_GP
            if campaign.tag_friendly_chaos_cultists
            else MUTANT_FISH_NORMAL_SALE_GP
        )
        total = count * unit_price
        recipient.gold += total
        result_text = (
            f"The party sells {count} mutant-fish ration(s) for {unit_price}gp each. "
            f"{recipient.name} receives {total}gp."
        )
        state["reward_kind"] = "sold"
        state["sale_unit_gp"] = unit_price
        state["sale_total_gp"] = total
        state["recipient_id"] = recipient_id
    else:
        raise ValueError("Choose whether to keep or sell the mutant fish.")

    state.update(
        {
            "phase": "resolved",
            "reward_claimed": True,
            "result_text": result_text,
            "updated_at": now_utc(),
        }
    )
    set_mutant_fish_state(session, state)
    session.log.append(result_text)
    return result_text


def set_chaos_cultist_friendship(campaign: CampaignState, friendly: bool = True) -> None:
    campaign.tag_friendly_chaos_cultists = bool(friendly)
