from __future__ import annotations

from typing import Any

from ..db import now_utc
from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_d6
from .gem_items import gem_item_value_gp, remove_inventory_item
from .inventory import spend_living_carried_gold

XASARTHA_PENDANT_ITEM = "Xasartha's Emerald Pendant (260gp)"
XASARTHA_NECROS_ITEM_PREFIX = "Crate of necros"


def xasartha_pendant_luck_points(member: PartyMemberState) -> int:
    if not any(item == XASARTHA_PENDANT_ITEM for item in member.inventory):
        return 0
    return 2 if member.class_id.strip().lower() == "halfling" else 1


def medusa_scene1_state(session: SessionState) -> dict[str, Any]:
    quest = session.active_quest
    if quest is None:
        return {}
    return dict((quest.tag_procedure_state or {}).get("medusa_scene1") or {})


def set_medusa_scene1_state(session: SessionState, state: dict[str, Any]) -> None:
    quest = session.active_quest
    if quest is None:
        return
    procedure_state = dict(quest.tag_procedure_state or {})
    procedure_state["medusa_scene1"] = state
    quest.tag_procedure_state = procedure_state


def initialize_medusa_reaction_state(session: SessionState, reaction_roll: int) -> dict[str, Any]:
    phase = "quest_choice" if reaction_roll == 2 else ("bribe_choice" if reaction_roll == 1 else "combat")
    state: dict[str, Any] = {
        "phase": phase,
        "reaction_roll": reaction_roll,
        "updated_at": now_utc(),
    }
    if reaction_roll == 1:
        state["bribe_gold"] = sum(roll_d6() for _ in range(6))
    set_medusa_scene1_state(session, state)
    return state


def pay_xasartha_gold_bribe(session: SessionState) -> str:
    state = medusa_scene1_state(session)
    if state.get("phase") != "bribe_choice":
        raise ValueError("Xasartha is not waiting for a bribe.")
    amount = int(state.get("bribe_gold") or 0)
    paid, payment_log = spend_living_carried_gold(session.party, amount)
    if not paid:
        available = sum(member.gold for member in session.party if member.current_life > 0)
        raise ValueError(f"The living party carries {available}gp but Xasartha demands {amount}gp.")
    state["phase"] = "resolved"
    state["resolution"] = "gold_bribe"
    state["updated_at"] = now_utc()
    set_medusa_scene1_state(session, state)
    session.log.extend(payment_log)
    return f"The party pays Xasartha's {amount}gp bribe. She accepts it and leaves peacefully."


def pay_xasartha_gem_bribe(
    session: SessionState,
    *,
    character_id: str,
    item_name: str,
) -> str:
    state = medusa_scene1_state(session)
    if state.get("phase") != "bribe_choice":
        raise ValueError("Xasartha is not waiting for a bribe.")
    member = next(
        (
            item
            for item in session.party
            if item.character_id == character_id and item.current_life > 0
        ),
        None,
    )
    if member is None:
        raise ValueError("Choose a living character carrying the offered gem or jewel.")
    value = gem_item_value_gp(item_name)
    if value < 15 or not remove_inventory_item(member, item_name):
        raise ValueError("Choose a carried jewel, gem, or jewelry item worth at least 15gp.")
    state["phase"] = "resolved"
    state["resolution"] = "gem_bribe"
    state["updated_at"] = now_utc()
    set_medusa_scene1_state(session, state)
    return (
        f"{member.name} gives Xasartha {item_name} as the bribe. "
        "She accepts it and leaves peacefully."
    )


def stage_xasartha_defeat_reward(
    session: SessionState,
    defeated: list[EnemyState],
) -> str | None:
    state = medusa_scene1_state(session)
    if state.get("phase") != "combat":
        return None
    if not any(enemy.name.strip().lower() in {"medusa", "xasartha", "xasartha the medusa"} for enemy in defeated):
        return None
    necros = sum(roll_d6() for _ in range(2))
    state["phase"] = "reward_choice"
    state["necros"] = necros
    state["updated_at"] = now_utc()
    set_medusa_scene1_state(session, state)
    return (
        f"Xasartha is defeated. The party finds her emerald pendant, worth 260gp, "
        f"and a crate containing {necros} necros. Choose a character to wear the pendant, "
        "or sell it without trying it on."
    )


def resolve_xasartha_reward(
    session: SessionState,
    *,
    character_id: str,
    wear_pendant: bool,
) -> str:
    state = medusa_scene1_state(session)
    if state.get("phase") != "reward_choice":
        raise ValueError("Xasartha's reward is not waiting for a decision.")
    member = next(
        (
            item
            for item in session.party
            if item.character_id == character_id and item.current_life > 0
        ),
        None,
    )
    if member is None:
        raise ValueError("Choose a living character to carry Xasartha's reward.")
    necros = int(state.get("necros") or 0)
    crate = f"{XASARTHA_NECROS_ITEM_PREFIX} ({necros})"
    if wear_pendant:
        from .equipment_shop import can_class_use_item

        allowed, _message = can_class_use_item(
            member.class_id,
            {"category": "magic_item", "magic": True},
        )
        if not allowed:
            raise ValueError(f"{member.name} cannot use magic items and may not wear the pendant.")
        member.inventory.append(crate)
        member.inventory.append(XASARTHA_PENDANT_ITEM)
        allowance = xasartha_pendant_luck_points(member)
        result = (
            f"{member.name} wears Xasartha's emerald pendant and carries the crate of {necros} necros. "
            f"The pendant grants {allowance} rechargeable Luck point"
            f"{'s' if allowance != 1 else ''} per adventure."
        )
        resolution = "pendant_worn"
    else:
        member.inventory.append(crate)
        member.gold += 260
        result = (
            f"The party sells Xasartha's emerald pendant without trying it on. "
            f"{member.name} receives 260gp and carries the crate of {necros} necros."
        )
        resolution = "pendant_sold"
    state["phase"] = "resolved"
    state["resolution"] = resolution
    state["reward_character_id"] = member.character_id
    state["updated_at"] = now_utc()
    set_medusa_scene1_state(session, state)
    return result
