from __future__ import annotations

from ..schemas import ActiveQuestState


def quest_from_row(
    row: dict,
    *,
    tile_id: str,
    gold_required: int | None = None,
    item_name: str | None = None,
    boss_target_name: str | None = None,
) -> ActiveQuestState:
    key = row["key"]
    if key == "bring_gold":
        amount = gold_required if gold_required is not None else 50
        return ActiveQuestState(
            tile_id=tile_id,
            key=key,
            description=f"Bring {amount}gp to the Quest-giver's tile.",
            gold_required=amount,
        )
    if key == "bring_head":
        return ActiveQuestState(
            tile_id=tile_id,
            key=key,
            description=row["result"],
            boss_slay_pending=True,
            boss_target_name=boss_target_name,
        )
    if key == "bring_alive":
        return ActiveQuestState(
            tile_id=tile_id,
            key=key,
            description=row["result"],
            boss_capture_pending=True,
        )
    if key == "bring_item":
        return ActiveQuestState(
            tile_id=tile_id,
            key=key,
            description=row["result"],
            item_name=item_name or "Magic item",
        )
    if key == "peaceful_way":
        return ActiveQuestState(tile_id=tile_id, key=key, description=row["result"], peaceful_required=3)
    return ActiveQuestState(tile_id=tile_id, key=key, description=row["result"])


def quest_ready_to_complete(session_tile_id: str, quest: ActiveQuestState, session) -> tuple[bool, str]:
    if quest.reward_claimed:
        return False, "Quest reward already handled."
    if quest.key == "bring_gold":
        if session_tile_id != quest.tile_id:
            return False, "Return to the Quest-giver's tile with the gold."
        total_gold = sum(member.gold for member in session.party if member.current_life > 0)
        if total_gold < quest.gold_required:
            return False, f"Need {quest.gold_required}gp total (party has {total_gold}gp)."
        return True, ""
    if quest.key == "bring_item":
        if session_tile_id != quest.tile_id:
            return False, "Return to the Quest-giver's tile with the item."
        if not quest.item_collected:
            return False, f"Still seeking: {quest.item_name}."
        return True, ""
    if quest.key == "peaceful_way":
        if quest.peaceful_count < quest.peaceful_required:
            return False, f"Peaceful progress: {quest.peaceful_count}/{quest.peaceful_required}."
        return True, ""
    if quest.key == "slay_all":
        if session.map_bounds_mode == "unlimited":
            width = getattr(session.map_state, "width", 0)
            height = getattr(session.map_state, "height", 0)
            if width < 20 or height < 28:
                return False, "Infinite-map slay-all Quest needs at least a 20x28 map area."
        if not session.final_boss_defeated:
            return False, "The Final Boss must be slain."
        for tile in session.map_state.tiles:
            if any(enemy.life > 0 for enemy in tile.enemies):
                return False, "Clear all remaining foes from the dungeon."
        return True, ""
    if quest.key == "bring_head":
        if not quest.boss_head_acquired:
            target = f" {quest.boss_target_name}" if quest.boss_target_name else ""
            return False, f"The quest Boss{target} has not yet been slain and claimed."
        if session_tile_id != quest.tile_id:
            return False, "Return to the Quest-giver's tile with the Boss head."
        return True, ""
    if quest.boss_slay_pending or quest.boss_capture_pending:
        return False, "The quest target is not yet subdued or slain."
    if quest.key == "bring_alive":
        if not quest.completed:
            return False, "The quest target is not yet subdued alive."
        if session_tile_id != quest.tile_id:
            return False, "Return to the Quest-giver's tile with the living captive."
        return True, ""
    return quest.completed, "Quest not complete."


def epic_reward_item(row: dict) -> str:
    return row.get("reward", row.get("result", "Epic reward"))
