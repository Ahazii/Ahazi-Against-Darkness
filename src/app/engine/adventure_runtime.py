from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..schemas import ActiveQuestState, SessionState, TileState
from .adventure_foes import spawn_manifest_foes

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

IMPORTED_ROOM_PREFIX = "imported:"


def manifest_room_id(tile: TileState, manifest: dict[str, Any] | None = None) -> str | None:
    if tile.content_key.startswith(IMPORTED_ROOM_PREFIX):
        return tile.content_key[len(IMPORTED_ROOM_PREFIX) :]
    if tile.content_key == "entrance" and isinstance(manifest, dict):
        entrance = manifest.get("entrance_room_id")
        if isinstance(entrance, str) and entrance.strip():
            return entrance
    return None


def imported_trigger_key(room_id: str, when: str, index: int) -> str:
    return f"{room_id}:{when}:{index}"


def imported_npc_dialogue_key(npc_id: str) -> str:
    return f"npc:{npc_id}"


def announce_imported_npcs_on_enter(
    session: SessionState,
    tile: TileState,
    manifest: dict[str, Any],
) -> None:
    room_id = manifest_room_id(tile, manifest)
    if not room_id:
        return
    for npc in manifest.get("npcs") or []:
        if not isinstance(npc, dict) or npc.get("room_id") != room_id:
            continue
        npc_id = npc.get("id")
        if not isinstance(npc_id, str) or not npc_id.strip():
            continue
        key = imported_npc_dialogue_key(npc_id)
        if key in session.imported_fired_triggers:
            continue
        name = str(npc.get("name") or "Someone").strip()
        description = str(npc.get("description") or "").strip()
        dialogue = str(npc.get("dialogue") or "").strip()
        if description:
            session.log.append(f"{name}: {description}")
        if dialogue:
            session.log.append(f'{name} says: "{dialogue}"')
        if description or dialogue:
            session.imported_fired_triggers.append(key)


def quest_from_manifest(
    manifest: dict[str, Any],
    *,
    giver_tile_id: str,
) -> ActiveQuestState:
    quest = manifest["quest"]
    complete_when = quest["complete_when"]
    complete_type = complete_when.get("type")
    description = quest.get("objective_text", "Complete the adventure objective.")
    if complete_type == "boss_defeated":
        return ActiveQuestState(
            tile_id=giver_tile_id,
            key="imported_boss",
            description=description,
            boss_slay_pending=True,
            boss_target_name=complete_when.get("boss_name"),
        )
    if complete_type == "item_collected":
        return ActiveQuestState(
            tile_id=giver_tile_id,
            key="imported_item",
            description=description,
            item_name=complete_when.get("item_name"),
        )
    if complete_type == "room_reached":
        return ActiveQuestState(
            tile_id=giver_tile_id,
            key="imported_room",
            description=description,
        )
    if complete_type == "peaceful_count":
        required = int(complete_when.get("peaceful_required", 3))
        return ActiveQuestState(
            tile_id=giver_tile_id,
            key="imported_peaceful",
            description=description,
            peaceful_required=required,
        )
    return ActiveQuestState(tile_id=giver_tile_id, key="imported_generic", description=description)


def imported_quest_complete(session: SessionState) -> bool:
    quest = session.active_quest
    if quest is None:
        return True
    if session.adventure_type != "imported":
        return True
    return quest.completed


def update_imported_quest_on_combat_end(session: SessionState, defeated: list, tile: TileState) -> None:
    quest = session.active_quest
    if quest is None or quest.completed:
        return
    room_id = manifest_room_id(tile, session.imported_manifest)
    complete_when = session.imported_quest_complete_when or {}
    if quest.key == "imported_boss":
        target = quest.boss_target_name
        required_room = complete_when.get("room_id")
        for enemy in defeated:
            if target and enemy.name != target:
                continue
            if required_room and room_id != required_room:
                continue
            if enemy.category == "boss" or (target and enemy.name == target):
                if not enemy.subdued:
                    quest.boss_slay_pending = False
                    quest.boss_head_acquired = True
                    quest.completed = True
                    session.log.append(f"Quest complete: {enemy.name} has been destroyed.")
    elif quest.key == "imported_item":
        for enemy in defeated:
            if enemy.category in {"weird", "boss"} and quest.item_name:
                quest.item_collected = True
                quest.completed = True
                session.log.append(f"Quest complete: {quest.item_name} obtained.")


def update_imported_quest_on_enter(session: SessionState, tile: TileState) -> None:
    quest = session.active_quest
    if quest is None or quest.completed or quest.key != "imported_room":
        return
    complete_when = session.imported_quest_complete_when or {}
    target_room = complete_when.get("room_id")
    room_id = manifest_room_id(tile, session.imported_manifest)
    if target_room and room_id == target_room:
        quest.completed = True
        session.log.append("Quest complete: objective location reached.")


def fire_imported_triggers(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    when: str,
    *,
    show_rolls: bool = True,
) -> None:
    if session.adventure_type != "imported":
        return
    manifest = session.imported_manifest or {}
    room_id = manifest_room_id(tile, manifest)
    if not room_id:
        return
    room = next((item for item in manifest.get("rooms", []) if item.get("id") == room_id), None)
    if not isinstance(room, dict):
        return

    triggers = room.get("triggers") or []
    monsters = engine.rules.monsters()
    hcl = engine._highest_character_level(session.party)

    for index, trigger in enumerate(triggers):
        if not isinstance(trigger, dict) or trigger.get("when") != when:
            continue
        key = imported_trigger_key(room_id, when, index)
        if trigger.get("once", True) and key in session.imported_fired_triggers:
            continue

        encounter = trigger.get("encounter")
        if isinstance(encounter, dict) and encounter.get("foes"):
            if not any(enemy.life > 0 for enemy in tile.enemies):
                spawned = spawn_manifest_foes(monsters, encounter.get("foes", []), hcl)
                if spawned:
                    tile.enemies.extend(spawned)
                    tile.initial_enemy_count = len(tile.enemies)
                    session.log.append(f"Encounter: {len(spawned)} foe(s) appear in {tile.title}.")
                    if session.mode == "exploration":
                        engine._announce_encounter(session, tile, show_rolls=show_rolls)

        treasure = trigger.get("treasure")
        if isinstance(treasure, dict):
            gold = int(treasure.get("gold", 0) or 0)
            items = treasure.get("items") or []
            if gold > 0:
                tile.treasure_gold += gold
            for item_name in items:
                if isinstance(item_name, str) and item_name not in tile.treasure_items:
                    tile.treasure_items.append(item_name)
            if gold > 0 or items:
                tile.treasure_summary = f"{tile.treasure_gold}gp" + (
                    f", {', '.join(tile.treasure_items)}" if tile.treasure_items else ""
                )
                tile.treasure_claimed = False
                if not any("treasure" in str(obj).lower() for obj in tile.objects):
                    tile.objects.append("Treasure")

        log_line = trigger.get("log")
        if isinstance(log_line, str) and log_line.strip():
            session.log.append(log_line.strip())

        if trigger.get("once", True):
            session.imported_fired_triggers.append(key)

    if when == "on_enter":
        announce_imported_npcs_on_enter(session, tile, manifest)
        update_imported_quest_on_enter(session, tile)
