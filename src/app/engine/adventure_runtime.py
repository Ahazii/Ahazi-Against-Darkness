from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..schemas import ActiveQuestState, SessionState, TileState
from .adventure_foes import spawn_manifest_foes
from .tag_compat import normalize_tag_log_line

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


def imported_quest_return_hint_key() -> str:
    return "quest:return_hint"


def imported_quest_giver_resolution_key() -> str:
    return "quest:giver_resolution"


def _room_title(manifest: dict[str, Any], room_id: str) -> str:
    for room in manifest.get("rooms") or []:
        if isinstance(room, dict) and room.get("id") == room_id:
            return str(room.get("title") or room_id)
    return room_id


def _npc_at_room(manifest: dict[str, Any], room_id: str) -> dict[str, Any] | None:
    for npc in manifest.get("npcs") or []:
        if isinstance(npc, dict) and npc.get("room_id") == room_id:
            return npc
    return None


def log_imported_quest_return_hint(session: SessionState) -> None:
    """After the objective is met, nudge the party back to the quest giver when one is set."""
    manifest = session.imported_manifest or {}
    quest = manifest.get("quest") or {}
    giver_room_id = quest.get("giver_room_id")
    if not isinstance(giver_room_id, str) or not giver_room_id.strip():
        return
    complete_when = session.imported_quest_complete_when or {}
    objective_room = complete_when.get("room_id")
    if objective_room and objective_room == giver_room_id:
        return
    hint_key = imported_quest_return_hint_key()
    if hint_key in session.imported_fired_triggers:
        return
    npc = _npc_at_room(manifest, giver_room_id)
    room_title = _room_title(manifest, giver_room_id)
    if npc:
        name = str(npc.get("name") or "the quest giver").strip()
        session.log.append(
            f"Quest objective complete. Return to {name} in {room_title} to report."
        )
    else:
        session.log.append(f"Quest objective complete. Return to {room_title} to report.")
    session.imported_fired_triggers.append(hint_key)


def maybe_imported_quest_giver_resolution(
    session: SessionState,
    tile: TileState,
    manifest: dict[str, Any],
) -> None:
    """Log giver-room payoff when the party returns after the quest is already complete."""
    key = imported_quest_giver_resolution_key()
    if key in session.imported_fired_triggers:
        return
    quest = session.active_quest
    if quest is None or not quest.completed:
        return
    giver_room_id = (manifest.get("quest") or {}).get("giver_room_id")
    if not isinstance(giver_room_id, str):
        return
    room_id = manifest_room_id(tile, manifest)
    if room_id != giver_room_id:
        return
    npc = _npc_at_room(manifest, giver_room_id)
    ending = manifest.get("ending") or {}
    victory = str(ending.get("victory_text") or "").strip()
    if npc:
        name = str(npc.get("name") or "Someone").strip()
        dialogue = str(npc.get("dialogue") or "").strip()
        if dialogue:
            session.log.append(f'{name} says: "{dialogue}"')
        elif victory:
            session.log.append(f"{name}: {victory}")
        else:
            session.log.append(f"{name} acknowledges your success.")
    elif victory:
        session.log.append(victory)
    else:
        session.log.append("The quest giver hears your report and offers quiet thanks.")
    session.imported_fired_triggers.append(key)


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


def log_imported_departure_narrative(session: SessionState) -> None:
    """Narrate leaving an imported module, whether or not the quest was finished."""
    if session.adventure_type != "imported":
        return
    manifest = session.imported_manifest or {}
    ending = manifest.get("ending") or {}
    quest = session.active_quest
    quest_done = quest is None or quest.completed
    if quest_done:
        victory = str(ending.get("victory_text") or "").strip()
        if victory:
            session.log.append(victory)
        return
    objective = (quest.description if quest else "").strip() or "the quest objective"
    session.log.append(f"The party leaves without completing the quest: {objective}")
    defeat = str(ending.get("defeat_text") or "").strip()
    if defeat:
        session.log.append(defeat)


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
                quest.boss_slay_pending = False
                quest.completed = True
                if enemy.subdued:
                    quest.boss_capture_pending = False
                    quest.captured_boss_name = enemy.name
                    session.log.append(f"Quest complete: {enemy.name} has been subdued alive.")
                    session.log.append(
                        "Adventures Guild guidance: if the printed scene has a capture-alive reward, open Adventures Guild Actions and use the capture/reward prompt before leaving."
                    )
                else:
                    quest.boss_head_acquired = True
                    session.log.append(f"Quest complete: {enemy.name} has been destroyed.")
                    session.log.append(
                        "Adventures Guild guidance: if this generated Adventures Guild scene offered a kill/capture choice, record the final route in Adventures Guild Actions before applying rewards."
                    )
                log_imported_quest_return_hint(session)
    elif quest.key == "imported_item":
        for enemy in defeated:
            if enemy.category in {"weird", "boss"} and quest.item_name:
                quest.item_collected = True
                quest.completed = True
                session.log.append(f"Quest complete: {quest.item_name} obtained.")
                log_imported_quest_return_hint(session)


def _room_encounter_contains_target(room: dict[str, Any], target: str | None) -> bool:
    if not target:
        return False
    for trigger in room.get("triggers") or []:
        if not isinstance(trigger, dict):
            continue
        encounter = trigger.get("encounter")
        foes = encounter.get("foes") if isinstance(encounter, dict) else []
        for foe in foes or []:
            if isinstance(foe, dict) and foe.get("name") == target:
                return True
    return False


def repair_imported_boss_quest_from_resolved_room(session: SessionState) -> None:
    quest = session.active_quest
    if quest is None or quest.completed or quest.key != "imported_boss":
        return
    complete_when = session.imported_quest_complete_when or {}
    room_id = complete_when.get("room_id")
    if not isinstance(room_id, str) or not room_id:
        return
    manifest = session.imported_manifest or {}
    room = next(
        (item for item in manifest.get("rooms", []) if isinstance(item, dict) and item.get("id") == room_id),
        None,
    )
    if room is None or not _room_encounter_contains_target(room, quest.boss_target_name):
        return
    if imported_trigger_key(room_id, "on_enter", 0) not in session.imported_fired_triggers:
        return
    tile = next(
        (
            item
            for item in session.map_state.tiles
            if manifest_room_id(item, manifest) == room_id
        ),
        None,
    )
    if tile is None or not tile.resolved or any(enemy.life > 0 for enemy in tile.enemies):
        return
    quest.boss_slay_pending = False
    quest.boss_head_acquired = True
    quest.completed = True
    session.log.append(
        f"Quest complete: {quest.boss_target_name or 'the imported boss'} has been defeated; objective repaired from the resolved boss room."
    )
    session.log.append(
        "Adventures Guild guidance: record the final route and printed reward in Adventures Guild Actions before applying closeout rewards."
    )
    log_imported_quest_return_hint(session)


def update_imported_quest_on_enter(session: SessionState, tile: TileState) -> None:
    quest = session.active_quest
    if quest is None or quest.completed:
        return
    repair_imported_boss_quest_from_resolved_room(session)
    if quest.completed or quest.key != "imported_room":
        return
    complete_when = session.imported_quest_complete_when or {}
    target_room = complete_when.get("room_id")
    room_id = manifest_room_id(tile, session.imported_manifest)
    if target_room and room_id == target_room:
        quest.completed = True
        session.log.append("Quest complete: objective location reached.")
        log_imported_quest_return_hint(session)


def _normalize_trigger_treasure(treasure: dict[str, Any]) -> tuple[int, list[str]]:
    gold = int(treasure.get("gold", 0) or 0)
    items_raw = treasure.get("items")
    items: list[str] = []
    if isinstance(items_raw, list):
        items = [item for item in items_raw if isinstance(item, str) and item.strip()]
    single_item = treasure.get("item")
    if isinstance(single_item, str) and single_item.strip():
        items.append(single_item.strip())
    return gold, items


def _tag_reference_from_session(session: SessionState) -> dict[str, Any]:
    manifest = session.imported_manifest or {}
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    parameters = source.get("parameters") if isinstance(source.get("parameters"), dict) else {}
    tag_reference = parameters.get("tag_reference")
    return tag_reference if isinstance(tag_reference, dict) else {}


def _log_tag_room_action_guidance(session: SessionState, room_id: str) -> None:
    tag_reference = _tag_reference_from_session(session)
    if not tag_reference:
        return
    key = f"tag_guidance:{room_id}"
    if key in session.imported_fired_triggers:
        return
    prompts = tag_reference.get("room_prompts") if isinstance(tag_reference.get("room_prompts"), dict) else {}
    prompt = prompts.get(room_id) if isinstance(prompts.get(room_id), dict) else {}
    title = str(prompt.get("title") or "Adventures Guild scene").strip()
    body = str(prompt.get("body") or "").strip()
    actions = prompt.get("actions") if isinstance(prompt.get("actions"), list) else []
    labels = [
        str(action.get("label") or "").strip()
        for action in actions
        if isinstance(action, dict) and str(action.get("label") or "").strip()
    ]
    if body:
        session.log.append(f"Adventures Guild guidance - {title}: {body}")
    if labels:
        session.log.append(
            "Adventures Guild actions here: "
            + ", ".join(labels[:5])
            + ". Use one only when this scene asks for that branch, Clue spend, route change, capture result, reward, or XP marker."
        )
    if room_id == "tag-final-scene":
        session.log.append(
            "TAG final-scene reminder: decide kill, capture, parley, escape, rewards, and XP before leaving. "
            "To capture a foe alive, tick Subdual damage before Resolve Round."
        )
    session.imported_fired_triggers.append(key)


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
            gold, items = _normalize_trigger_treasure(treasure)
            if gold > 0:
                tile.treasure_gold += gold
            for item_name in items:
                if item_name not in tile.treasure_items:
                    tile.treasure_items.append(item_name)
            if gold > 0 or items:
                tile.treasure_summary = f"{tile.treasure_gold}gp" + (
                    f", {', '.join(tile.treasure_items)}" if tile.treasure_items else ""
                )
                tile.treasure_claimed = False
                if not any("treasure" in str(obj).lower() for obj in tile.objects):
                    tile.objects.append("Treasure")
                if when == "on_search":
                    session.log.append("Hidden treasure found — use Claim Treasure to collect it.")

        log_line = trigger.get("log")
        if isinstance(log_line, str) and log_line.strip():
            session.log.append(normalize_tag_log_line(log_line.strip()))

        if trigger.get("once", True):
            session.imported_fired_triggers.append(key)

    if when == "on_enter":
        _log_tag_room_action_guidance(session, room_id)
        announce_imported_npcs_on_enter(session, tile, manifest)
        update_imported_quest_on_enter(session, tile)
        maybe_imported_quest_giver_resolution(session, tile, manifest)
