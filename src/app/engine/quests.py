from __future__ import annotations

from ..schemas import ActiveQuestState


def quest_from_row(
    row: dict,
    *,
    tile_id: str,
    gold_required: int | None = None,
    item_name: str | None = None,
) -> ActiveQuestState:
    key = row["key"]
    if key == "bring_gold":
        amount = gold_required if gold_required is not None else 50
        return ActiveQuestState(
            tile_id=tile_id,
            key=key,
            description=row["result"],
            gold_required=amount,
        )
    if key in {"bring_head", "bring_alive"}:
        return ActiveQuestState(tile_id=tile_id, key=key, description=row["result"], boss_slay_pending=True)
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
    if quest.completed or quest.reward_claimed:
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
        if not session.final_boss_defeated:
            return False, "The Final Boss must be slain."
        for tile in session.map_state.tiles:
            if any(enemy.life > 0 for enemy in tile.enemies):
                return False, "Clear all remaining foes from the dungeon."
        return True, ""
    if quest.boss_slay_pending:
        return False, "The quest target is not yet defeated."
    if session_tile_id != quest.tile_id and quest.key in {"bring_head", "bring_alive"}:
        return False, "Return to the Quest-giver's tile."
    return quest.completed, "Quest not complete."


def epic_reward_item(row: dict) -> str:
    return row.get("reward", row.get("result", "Epic reward"))
