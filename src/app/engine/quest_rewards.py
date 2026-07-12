from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..schemas import SessionState, TileState
from .inventory import can_add_item
from .quests import epic_reward_item, quest_ready_to_complete

KERRAK_DAR_STATUS = "Kerrak Dar Hoard"
ENCHANTED_WEAPON_STATUS = "Enchanted weapon"


@dataclass(frozen=True)
class QuestRewardCallbacks:
    lookup_epic_reward: Callable[[int], dict | None]
    roll_d6: Callable[[], int]
    roll_major_foe_target: Callable[[SessionState], str | None]
    generated_tag_session: Callable[[SessionState], bool]


def claim_quest_reward(session: SessionState, tile: TileState, *, show_rolls: bool, callbacks: QuestRewardCallbacks) -> None:
    quest = session.active_quest
    if quest is None:
        session.log.append("No active Quest.")
        return
    if callbacks.generated_tag_session(session):
        session.log.append("Quest reward blocked: generated Adventures Guild scenes use their printed scene rewards and TAG Action buttons, not the core Epic Rewards table.")
        session.log.append("Use the current room prompt or Adventures Guild Actions for purchases, services, bounties, route rewards, XP markers, Guild share, banking, and closeout signoff.")
        return
    if quest.reward_claimed:
        session.log.append("Quest reward already claimed.")
        return
    if quest.key in {"bring_gold", "bring_item", "bring_head", "bring_alive"} or not quest.completed:
        ready, message = quest_ready_to_complete(tile.id, quest, session)
        if not ready:
            session.log.append(f"Quest turn-in blocked: {message}")
            return
        if quest.key == "bring_gold":
            remaining = quest.gold_required
            for member in sorted(session.party, key=lambda item: item.marching_order):
                if member.current_life > 0 and remaining > 0:
                    paid = min(member.gold, remaining)
                    member.gold -= paid
                    remaining -= paid
        quest.completed = True
    reward_roll = callbacks.roll_d6()
    if show_rolls:
        session.log.append(f"Epic reward roll: d6 = {reward_roll}.")
    row = callbacks.lookup_epic_reward(reward_roll)
    if row is None:
        session.log.append("Epic Rewards table lookup failed.")
        return
    reward_text = epic_reward_item(row)
    survivors = [member for member in session.party if member.current_life > 0]
    if not survivors:
        session.log.append("There is no survivor to receive the Quest reward.")
        return
    key = row.get("key", "")
    item_label = "Book of Skalitos (6 pages)" if key == "book_of_skalitos" else reward_text.split(".")[0]
    if key not in {"gold_of_kerrak_dar", "enchanted_weapon"}:
        ok, message = can_add_item(survivors[0], item_label)
        if not ok:
            session.log.append(message)
            return
    quest.reward_claimed = True
    session.log.append(f"Quest complete! Epic reward: {reward_text}")
    if key == "gold_of_kerrak_dar":
        if KERRAK_DAR_STATUS not in survivors[0].statuses:
            survivors[0].statuses.append(KERRAK_DAR_STATUS)
        session.log.append(f"{survivors[0].name} marks Kerrak Dar's hoard; spend 1 held Clue while exploring to find 500gp.")
    elif key == "enchanted_weapon":
        if ENCHANTED_WEAPON_STATUS not in survivors[0].statuses:
            survivors[0].statuses.append(ENCHANTED_WEAPON_STATUS)
        session.log.append(f"{survivors[0].name}'s weapon is enchanted until adventure end.")
    else:
        if key == "arrow_of_slaying":
            target = callbacks.roll_major_foe_target(session) or "Major Foe"
            item_label = f"Arrow of Slaying (target: {target})"
            session.log.append(f"Arrow of Slaying target rolled: {target}.")
        survivors[0].inventory.append(item_label)
        session.log.append(f"{item_label} added to {survivors[0].name}'s inventory.")
    session.active_quest = None
