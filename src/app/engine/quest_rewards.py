from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..schemas import SessionState, TileState
from .inventory import can_add_item
from .quests import epic_reward_item, quest_from_row, quest_ready_to_complete

KERRAK_DAR_STATUS = "Kerrak Dar Hoard"
ENCHANTED_WEAPON_STATUS = "Enchanted weapon"


@dataclass(frozen=True)
class QuestRewardCallbacks:
    lookup_epic_reward: Callable[[int], dict | None]
    roll_d6: Callable[[], int]
    roll_major_foe_target: Callable[[SessionState], str | None]
    generated_tag_session: Callable[[SessionState], bool]


@dataclass(frozen=True)
class QuestAcceptanceCallbacks:
    speaker: Callable[[SessionState], object | None]
    highest_character_level: Callable[[list], int]
    social_save: Callable[[SessionState, object, int, bool], tuple[bool, list[str]]]
    lookup_table: Callable[[str, int], dict | None]
    roll_d6: Callable[[], int]
    roll_boss_target: Callable[[SessionState], str | None]


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


def accept_quest(session: SessionState, tile: TileState, *, show_rolls: bool, callbacks: QuestAcceptanceCallbacks) -> None:
    if session.mode == "combat":
        session.log.append("Deal with the fight before speaking to the Lady in White.")
        return
    if not tile.lady_in_white_available:
        session.log.append("The Lady in White is not here.")
        return
    if session.active_quest is not None:
        session.log.append("A Quest is already in progress.")
        return
    speaker = callbacks.speaker(session)
    if speaker is None:
        session.log.append("No hero is available to speak with the Lady in White.")
        return
    ok, social_log = callbacks.social_save(session, speaker, callbacks.highest_character_level(session.party), show_rolls)
    session.log.extend(social_log)
    if not ok:
        session.log.append("The Lady in White withdraws without offering a Quest.")
        return
    roll = callbacks.roll_d6()
    if show_rolls:
        session.log.append(f"Quest roll: d6 = {roll}.")
    row = callbacks.lookup_table("quest_table", roll)
    if row is None:
        session.log.append("Quest table lookup failed.")
        return
    gold_required = None
    item_name = None
    if row["key"] == "bring_gold":
        gold_required = roll * 50
        party_gold = sum(member.gold for member in session.party if member.current_life > 0)
        if party_gold >= gold_required:
            gold_required *= 2
            session.log.append(f"Party already has {party_gold}gp; quest gold doubled to {gold_required}gp.")
    if row["key"] == "bring_item":
        magic_row = callbacks.lookup_table("dungeon_magic_treasure_table", callbacks.roll_d6())
        item_name = (magic_row.get("items") or [magic_row.get("result", "Magic item")])[0] if magic_row else "Magic item"
    quest = quest_from_row(row, tile_id=tile.id, gold_required=gold_required, item_name=item_name, boss_target_name=callbacks.roll_boss_target(session) if row["key"] == "bring_head" else None)
    session.active_quest = quest
    tile.lady_in_white_available = False
    session.log.append(f"Quest accepted: {quest.description}")
    progress = {
        "bring_alive": "Quest progress: subdue a Boss alive with Subdual damage, then return to this tile.",
        "bring_item": f"Quest progress: find {quest.item_name} from a defeated Major Foe, then return to this tile.",
        "peaceful_way": f"Quest progress: complete {quest.peaceful_required} peaceful encounters by bribe, peaceful reaction, or Sleep.",
        "slay_all": "Quest progress: defeat the Final Boss and clear all remaining foes.",
    }
    if quest.gold_required:
        session.log.append(f"Quest progress: deliver {quest.gold_required}gp to this tile to complete the Quest.")
    elif quest.key == "bring_head":
        target = f" Quest target: {quest.boss_target_name}." if quest.boss_target_name else ""
        session.log.append(f"Quest progress: slay the Quest Boss, take its head, then return to this tile to claim the Epic reward.{target}")
    elif quest.key in progress:
        session.log.append(progress[quest.key])
