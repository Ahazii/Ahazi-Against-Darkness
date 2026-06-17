from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .config import load_settings
from .db import Store, init_db, new_id, now_utc
from .engine.dice import roll_formula
from .engine.equipment_shop import buy_equipment, list_shop_for_class, sell_item, sell_quote
from .engine.inventory import (
    MAX_CARRIED_GOLD,
    carry_baseline,
    snapshot_carry_baseline,
    transfer_character_gold,
    transfer_character_item,
)
from .engine.random_dungeon import RandomDungeonEngine
from .engine.rest import rest_eligibility
from .engine.roster_sync import (
    character_busy_session_id,
    lock_characters_for_session,
    persist_session_to_roster,
    reconcile_stale_character_locks,
    replace_session_party,
    session_allows_party_edit,
    sync_minor_encounters_to_roster,
    sync_party_members_to_roster,
    unlock_characters_for_session,
)
from .engine.class_profiles import build_starting_inventory, class_profiles_table_rows, max_life_for_level, roll_starting_wealth
from .engine.expert_skills import expert_skills_table_rows, expert_spells_table_rows
from .engine.expert_skill_effects import expert_skill_implementation_rows
from .engine.tier_skills import class_tricks_implementation_rows, ee_class_trick_flags_table_rows, tier_skills_table_rows
from .engine.tile_validation import map_elements_validation_table_rows
from .engine.tier_advancement import TIER_ENTRY
from .engine.weapons import infer_default_weapons, prune_weapon_defaults, set_weapon_default
from .rules.repository import RulesRepository, VALID_TILE_KEYS
from .schemas import (
    AdventureDescriptor,
    Character,
    CharacterBuyEquipment,
    CharacterCreate,
    CharacterClass,
    CharacterSellItem,
    CharacterSpendXp,
    CharacterSpendXpResult,
    CharacterTransfer,
    CharacterTransferResult,
    CharacterWeaponDefaults,
    EquipmentTransactionResult,
    IconDefinition,
    MapState,
    Party,
    PartyCreate,
    PartyMemberState,
    SessionAction,
    SaveSessionRequest,
    SessionPartyUpdate,
    SessionState,
    TileState,
    TileDefinition,
)


settings = load_settings()
init_db(settings.db_path)
store = Store(settings.db_path)
rules = RulesRepository(settings.packaged_rules_dir, settings.rules_dir)
random_engine = RandomDungeonEngine(rules, settings.assets_dir)


SWASHBUCKLER_TRAITS = {
    "flourishing_strike": "Flourishing Strike",
    "daring_escape": "Daring Escape",
    "riposte": "Riposte",
    "lucky_hat": "Lucky Hat",
    "taunt": "Taunt",
    "blade_dance": "Blade Dance",
}


def _swashbuckler_trait_for_create(payload: CharacterCreate, profile: CharacterClass) -> list[str]:
    if profile.id != "swashbuckler":
        if payload.trait_id:
            raise HTTPException(status_code=400, detail="Only Swashbucklers may select a Swashbuckler trait.")
        return []
    trait_id = (payload.trait_id or "").strip().lower()
    if not trait_id or trait_id == "roll":
        trait_id = list(SWASHBUCKLER_TRAITS)[roll_formula("d6") - 1]
    if trait_id not in SWASHBUCKLER_TRAITS:
        raise HTTPException(status_code=400, detail="Unknown Swashbuckler trait.")
    return [SWASHBUCKLER_TRAITS[trait_id]]


def _icon_slug(value: str) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "item"


def _default_icon_definitions() -> list[IconDefinition]:
    def icon(icon_id: str, label: str, category: str, description: str, fallback: str) -> IconDefinition:
        return IconDefinition(
            id=icon_id,
            label=label,
            category=category,  # type: ignore[arg-type]
            description=description,
            file="",
            fallback=fallback,
            attribution="Built-in CSS marker",
            license="Project-local CSS",
        )

    def monster_icon(icon_id: str, label: str, description: str) -> IconDefinition:
        return IconDefinition(
            id=icon_id,
            label=label,
            category="monster",
            description=description,
            file="icons/user/game-icons/monster-grasp.svg",
            fallback="monster",
            source_url="https://game-icons.net/1x1/lorc/monster-grasp.html",
            attribution="Icons made by Lorc from game-icons.net",
            license="CC BY 3.0",
            notes="Generated fallback for PDF-backed monster entries without a custom icon override.",
        )

    definitions = [
        icon("monster", "Active Enemy", "map", "Enemies are still alive in this room.", "monster"),
        icon("defeated", "Defeated Enemy", "map", "Enemies were defeated and remain remembered in this room.", "defeated"),
        icon("searched", "Searched Room", "map", "This room has already been searched.", "searched"),
        icon("treasure", "Full Treasure", "map", "Treasure is present and can still be claimed.", "treasure"),
        icon("treasure-claimed", "Looted Treasure", "map", "Treasure was found and has already been claimed.", "treasure-claimed"),
        icon("treasure-empty", "Empty Treasure", "map", "A chest or treasure result is present but no loot remains.", "treasure-empty"),
        icon("trap", "Active Trap", "map", "A trap is unresolved in this room.", "trap"),
        icon("trap-resolved", "Resolved Trap", "map", "A trap was found and has been resolved.", "trap-resolved"),
        icon("fallen", "Fallen Character", "map", "A party member fell in this room.", "fallen"),
        icon("detached", "Detached Hero", "map", "A living hero has been left behind in this room.", "detached"),
        icon("vendor", "Vendor", "map", "A healer, alchemist, or other trader is available here.", "vendor"),
        icon("event", "Room Event", "map", "A special room feature or encounter is remembered here.", "event"),
        icon(
            "wandering-monsters",
            "Wandering Monsters Event",
            "map",
            "A special event resolved as wandering monsters.",
            "wandering-monsters",
        ),
        icon("quest", "Quest Giver", "map", "A quest giver or active quest marker is here.", "quest"),
        icon("door", "Door", "map", "A door exit.", "door"),
        icon("passage", "Passage", "map", "An open passage exit.", "passage"),
        icon("dungeon-exit", "Dungeon Exit", "map", "The marked exit that leaves the dungeon.", "dungeon-exit"),
    ]

    for profile in rules.classes():
        definitions.append(
            icon(
                f"class-{profile.id}",
                profile.name,
                "class",
                f"Map and sheet icon for the {profile.name} class.",
                f"class-{profile.id}",
            )
        )
        if profile.id == "mushroom_monk":
            definitions.append(
                icon("class-monk", profile.name, "class", f"Map and sheet icon for the {profile.name} class.", "class-monk")
            )
        if profile.id == "light_gladiator":
            definitions.append(
                icon(
                    "class-gladiator",
                    profile.name,
                    "class",
                    f"Map and sheet icon for the {profile.name} class.",
                    "class-gladiator",
                )
            )
    definitions.append(icon("class-hero", "Generic Hero", "class", "Fallback class icon.", "class-hero"))

    monster_names: set[str] = set()
    for table_key, rows in rules.monsters().items():
        if table_key == "reaction_tables" or not isinstance(rows, list):
            continue
        definitions.append(
            icon(
                f"monster-category-{_icon_slug(table_key)}",
                table_key.replace("_", " ").title(),
                "monster",
                f"Fallback icon for {table_key.replace('_', ' ')} encounters.",
                "monster",
            )
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            monster_id = f"monster-{_icon_slug(name)}"
            if monster_id in monster_names:
                continue
            monster_names.add(monster_id)
            definitions.append(monster_icon(monster_id, name, f"Map icon for {name} encounters."))
    return definitions


def _icons_payload() -> list[IconDefinition]:
    merged = {definition.id: definition for definition in _default_icon_definitions()}
    for definition in rules.icons():
        merged[definition.id] = definition
    return [merged[icon_id] for icon_id in sorted(merged)]


def enrich_session(session: SessionState) -> SessionState:
    _restore_missing_recovery_members(session)
    tile = random_engine._current_tile(session)
    ok, reason = rest_eligibility(session, tile)
    session.rest_available = ok
    session.rest_block_reason = reason
    session.party_editable = session_allows_party_edit(session)
    for member in session.party:
        if member.starting_weapon_slots is None or member.starting_shields is None:
            baseline_weapons, baseline_shields = carry_baseline(member)
            if member.starting_weapon_slots is None:
                member.starting_weapon_slots = baseline_weapons
            if member.starting_shields is None:
                member.starting_shields = baseline_shields
    return session


def _recovery_character_ids(session: SessionState) -> list[str]:
    ids: list[str] = []
    for tile in session.map_state.tiles:
        for character_id in tile.fallen_character_ids or []:
            if character_id not in ids:
                ids.append(character_id)
    for character_id in session.fallen_outside_character_ids or []:
        if character_id not in ids:
            ids.append(character_id)
    if session.carried_body_id and session.carried_body_id not in ids:
        ids.append(session.carried_body_id)
    return ids


def _restore_missing_recovery_members(session: SessionState) -> bool:
    existing_ids = {member.character_id for member in session.party}
    missing_ids = [character_id for character_id in _recovery_character_ids(session) if character_id not in existing_ids]
    if not missing_ids:
        return False

    party = store.get("parties", session.party_id, Party.model_validate)
    party_ids = list(party.character_ids) if party is not None else []
    changed = False
    for character_id in missing_ids:
        character = store.get("characters", character_id, Character.model_validate)
        if character is None:
            continue
        if character.active_session_id != session.id and character_id not in party_ids:
            continue
        member = _member_state(character)
        member.current_life = 0
        if "fallen" not in {status.lower() for status in member.statuses}:
            member.statuses.append("fallen")
        if character_id in party_ids:
            member.marching_order = party_ids.index(character_id) + 1
        else:
            member.marching_order = min(4, len(session.party) + 1)
        session.party.append(member)
        existing_ids.add(character_id)
        changed = True
        session.log.append(f"{member.name}'s fallen body is restored to the active party record.")
    if changed:
        session.party = sorted(session.party, key=lambda item: item.marching_order)
        session.updated_at = now_utc()
    return changed


ICON_FILE_EXTENSIONS = {".svg", ".png", ".jpg", ".jpeg", ".webp"}


app = FastAPI(title="Ahazi Against Darkness", version="0.26.0")
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
app.mount("/assets", StaticFiles(directory=settings.assets_dir), name="assets")


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(
        (settings.static_dir / "index.html").read_text(encoding="utf-8"),
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/rules/classes")
async def list_classes() -> list[CharacterClass]:
    return rules.classes()


@app.get("/api/rules/tiles")
async def list_tiles() -> list[TileDefinition]:
    return list(rules.tiles().values())


@app.get("/api/rules/tiles/validation")
async def validate_tiles() -> dict:
    from .engine.tile_validation import validate_tile_catalog

    issues = validate_tile_catalog(rules.tiles())
    return {"valid": not issues, "issues": issues}


@app.get("/api/rules/tables")
async def list_tables() -> dict:
    return _rules_tables_payload()


@app.get("/api/rules/reference")
async def rules_reference(q: str | None = None, category: str | None = None, implementation_status: str | None = None) -> dict:
    return rules.search_reference(q=q, category=category, implementation_status=implementation_status)


def _rules_tables_payload() -> dict:
    data = dict(rules.dungeon_tables())
    shop = rules.equipment_shop()
    expert_catalog = rules.expert_skills()
    rows: list[dict] = []
    for index, item in enumerate(shop.get("items", []), start=1):
        price = int(item["price_gp"])
        rows.append(
            {
                "roll": str(index),
                "result": f"{item['name']}: {price}gp buy; {price // 2}gp sell (half list).",
                "source_page": item.get("source_page", shop.get("source_page", 81)),
            }
        )
    rows.append(
        {
            "roll": "sell",
            "result": (
                "Sell equipment at half list price unless a fixed resale value is listed. "
                "Potions/rings 50gp; wands/scrolls/staves 100gp per spell; "
                "other magic d6×d6 gp; gems +20% for dwarves."
            ),
            "source_page": 19,
        }
    )
    data["equipment_shop_table"] = rows
    data["class_profiles_table"] = class_profiles_table_rows(rules.classes())
    data["expert_skills_table"] = expert_skills_table_rows(expert_catalog)
    data["expert_spells_table"] = expert_spells_table_rows(expert_catalog)
    data["expert_skill_implementation_table"] = expert_skill_implementation_rows(expert_catalog)
    data["heroic_skills_table"] = tier_skills_table_rows(rules.heroic_skills(), "heroic")
    data["legendary_skills_table"] = tier_skills_table_rows(rules.legendary_skills(), "legendary")
    data["class_tricks_implementation_table"] = class_tricks_implementation_rows()
    data["ee_class_trick_flags_table"] = ee_class_trick_flags_table_rows(rules.ee_class_tricks())
    data["map_elements_validation_table"] = map_elements_validation_table_rows(rules.tiles())
    data["tier_training_costs_table"] = [
        {
            "tier": tier.title(),
            "min_level": str(spec["min_level"]),
            "gold": str(spec["gold"]),
            "banked_xp": (
                f"0, or {spec.get('xp_alt', 0)} instead of gold"
                if tier == "expert" and spec.get("xp_alt")
                else str(spec.get("xp", 0))
            ),
            "notes": (
                "Unlocks Expert advancement; learning an Expert skill later spends a separate XP roll."
                if tier == "expert"
                else "Required before advancing into this tier."
            ),
            "source_page": 9,
        }
        for tier, spec in TIER_ENTRY.items()
    ]
    return data


@app.get("/api/rules/expert-skills")
async def expert_skills_catalog() -> dict:
    return rules.expert_skills()


@app.get("/api/rules/heroic-skills")
async def heroic_skills_catalog() -> dict:
    return rules.heroic_skills()


@app.get("/api/rules/legendary-skills")
async def legendary_skills_catalog() -> dict:
    return rules.legendary_skills()


@app.get("/api/rules/equipment-shop")
async def equipment_shop_catalog(class_id: str | None = None, character_id: str | None = None) -> dict:
    catalog = rules.equipment_shop()
    character = None
    potion_recipe_available = False
    if character_id:
        character = store.get("characters", character_id, Character.model_validate)
        if character is not None:
            class_id = character.class_id
            potion_recipe_available = _secret_available_for_character(character, "potion_recipe")
    if class_id:
        return {
            "catalog": catalog,
            "items": list_shop_for_class(
                catalog,
                class_id,
                character=character,
                potion_recipe_available=potion_recipe_available,
            ),
            "notes": (
                "Buy before or between adventures (Expanded Edition pp.81-88). "
                "Sell equipment at half list price unless a fixed resale value is listed. "
                "Roster gold is home bank gold; only dungeon-carried gold is limited to 200gp per hero."
            ),
        }
    return catalog


@app.get("/api/rules/monster-reactions")
async def list_monster_reactions() -> dict[str, list[dict]]:
    data = rules.monsters()
    reaction_tables = data.get("reaction_tables", {})
    return reaction_tables if isinstance(reaction_tables, dict) else {}


@app.get("/api/rules/monsters")
async def list_monsters() -> dict[str, list[dict]]:
    data = rules.monsters()
    return {key: value for key, value in data.items() if key != "reaction_tables" and isinstance(value, list)}


@app.get("/api/assets/icon-files")
async def list_icon_files() -> list[str]:
    icon_dir = settings.assets_dir / "icons" / "user"
    if not icon_dir.exists():
        return []
    files = [
        f"icons/user/{path.relative_to(icon_dir).as_posix()}"
        for path in icon_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in ICON_FILE_EXTENSIONS
    ]
    return sorted(files)


@app.get("/api/rules/icons")
async def list_icons() -> list[IconDefinition]:
    return _icons_payload()


@app.put("/api/rules/icons")
async def save_icons(payload: list[IconDefinition]) -> dict[str, str | int]:
    if len({icon.id for icon in payload}) != len(payload):
        raise HTTPException(status_code=400, detail="Duplicate icon ids are not allowed.")
    rules.save_icons(payload)
    return {"status": "ok", "count": len(payload)}


@app.put("/api/rules/tiles")
async def save_tiles(payload: list[TileDefinition]) -> dict[str, str | int]:
    if len({tile.key for tile in payload}) != len(payload):
        raise HTTPException(status_code=400, detail="Duplicate tile keys are not allowed.")
    invalid_keys = sorted({tile.key for tile in payload} - _valid_tile_keys())
    if invalid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid map element keys: {', '.join(invalid_keys)}.")
    invalid_dungeon_exits = [
        tile.key
        for tile in payload
        if not tile.key.startswith("0") and any(exit_state.dungeon_exit for exit_state in tile.exits)
    ]
    if invalid_dungeon_exits:
        raise HTTPException(
            status_code=400,
            detail=f"Dungeon exits are only allowed on starting map elements: {', '.join(invalid_dungeon_exits)}.",
        )
    rules.save_tiles(payload)
    return {"status": "ok", "count": len(payload)}


@app.get("/api/export/player-data")
async def export_player_data() -> dict:
    return {
        "version": 1,
        "exported_at": now_utc(),
        "characters": [character.model_dump(mode="json") for character in store.list("characters", Character.model_validate)],
        "parties": [party.model_dump(mode="json") for party in store.list("parties", Party.model_validate)],
    }


@app.post("/api/import/player-data")
async def import_player_data(payload: dict) -> dict[str, int | str]:
    raw_characters = payload.get("characters")
    raw_parties = payload.get("parties")
    if not isinstance(raw_characters, list) or not isinstance(raw_parties, list):
        raise HTTPException(status_code=400, detail="Import file must contain characters and parties lists.")

    try:
        characters = [Character.model_validate(item) for item in raw_characters]
        parties = [Party.model_validate(item) for item in raw_parties]
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Import data is invalid: {exc.errors()[0]['msg']}.") from exc
    imported_character_ids = {character.id for character in characters}
    existing_character_ids = {character.id for character in store.list("characters", Character.model_validate)}
    available_character_ids = imported_character_ids | existing_character_ids
    invalid_parties = [
        party.name
        for party in parties
        if len(set(party.character_ids)) != 4 or any(character_id not in available_character_ids for character_id in party.character_ids)
    ]
    if invalid_parties:
        raise HTTPException(status_code=400, detail=f"Imported parties reference missing or duplicate characters: {', '.join(invalid_parties)}.")

    for character in characters:
        store.save("characters", character)
    for party in parties:
        store.save("parties", party)
    return {"status": "ok", "characters": len(characters), "parties": len(parties)}


@app.get("/api/characters")
async def list_characters() -> list[Character]:
    reconcile_stale_character_locks(store)
    return store.list("characters", Character.model_validate)


@app.post("/api/characters")
async def create_character(payload: CharacterCreate) -> Character:
    profile = rules.class_by_id(payload.class_id)
    if profile is None:
        raise HTTPException(status_code=400, detail="Unknown class.")
    timestamp = now_utc()
    starting_life = max_life_for_level(profile.id, 1)
    inventory = build_starting_inventory(profile.id, profile.starting_inventory)
    class_traits = _swashbuckler_trait_for_create(payload, profile)
    character = Character(
        id=new_id(),
        name=payload.name.strip(),
        class_id=profile.id,
        class_name=profile.name,
        level=1,
        xp=0,
        gold=roll_starting_wealth(profile.id),
        clues=0,
        max_life=starting_life,
        current_life=starting_life,
        attack_bonus=profile.attack_bonus,
        defense_bonus=profile.defense_bonus,
        save_bonus=profile.save_bonus,
        inventory=inventory,
        spells=list(profile.starting_spells),
        abilities=list(profile.abilities),
        class_traits=class_traits,
        statuses=[],
        created_at=timestamp,
        updated_at=timestamp,
    )
    default_melee, default_missile = infer_default_weapons(character.inventory)
    character.default_melee_weapon = default_melee
    character.default_missile_weapon = default_missile
    prune_weapon_defaults(character)
    store.save("characters", character)
    return character


@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: str) -> dict[str, bool]:
    for party in store.list("parties", Party.model_validate):
        if character_id in party.character_ids:
            raise HTTPException(status_code=400, detail=f"Character is still in party: {party.name}.")
    return {"deleted": store.delete("characters", character_id)}


@app.post("/api/characters/{character_id}/heal")
async def heal_character(character_id: str) -> Character:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _prepare_roster_service_character(character, service_label="Healing")
    _heal_character(character)
    store.save("characters", character)
    _sync_roster_service_to_session(character, session, member, carried_gold)
    return character


@app.post("/api/characters/{character_id}/transfer")
async def transfer_character_gear(character_id: str, payload: CharacterTransfer) -> CharacterTransferResult:
    source = store.get("characters", character_id, Character.model_validate)
    if source is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    target = store.get("characters", payload.target_character_id, Character.model_validate)
    if target is None:
        raise HTTPException(status_code=404, detail="Target character not found.")

    active_sessions: dict[str, SessionState] = {}

    def active_session_for(character: Character) -> SessionState | None:
        session_id = character_busy_session_id(character, store)
        if not session_id:
            return None
        if session_id not in active_sessions:
            session = store.get("sessions", session_id, SessionState.model_validate)
            if session is not None and session.mode != "complete":
                active_sessions[session_id] = session
        return active_sessions.get(session_id)

    source_session = active_session_for(source)
    target_session = active_session_for(target)
    if source_session is not None and target_session is not None and source_session.id != target_session.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot transfer gear between heroes in different active adventures.",
        )
    if any(session is not None and not session.camped_outside for session in (source_session, target_session)):
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot transfer gear on the home screen while a hero is in an active adventure. "
                "Use Transfer Items on the party sheet during exploration, or return to camp first."
            ),
        )

    def prepare_active_character(
        character: Character,
        session: SessionState | None,
        *,
        label: str,
    ) -> tuple[SessionState | None, PartyMemberState | None, int]:
        if session is None:
            return None, None, 0
        member = next((item for item in session.party if item.character_id == character.id), None)
        if member is None:
            raise HTTPException(status_code=400, detail=f"{character.name} is not in the active session party.")
        if member.current_life <= 0:
            raise HTTPException(status_code=400, detail=f"{member.name} cannot {label} while fallen.")
        carried_gold = max(0, min(member.gold, MAX_CARRIED_GOLD))
        character.gold = member.gold + member.bank_gold
        character.current_life = member.current_life
        character.max_life = member.max_life
        character.inventory = list(member.inventory)
        character.default_melee_weapon = member.default_melee_weapon
        character.default_melee_weapon_secondary = member.default_melee_weapon_secondary
        character.default_missile_weapon = member.default_missile_weapon
        return session, member, carried_gold

    source_context = prepare_active_character(source, source_session, label="give gear")
    target_context = prepare_active_character(target, target_session, label="receive gear")
    has_item = bool(payload.item_name and payload.item_name.strip())
    has_gold = payload.gold_amount is not None
    if has_item == has_gold:
        raise HTTPException(status_code=400, detail="Provide either item_name or gold_amount.")
    if has_item:
        ok, message = transfer_character_item(source, target, item_name=payload.item_name or "")
    else:
        ok, message = transfer_character_gold(source, target, amount=payload.gold_amount or 0)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    timestamp = now_utc()
    source.updated_at = timestamp
    target.updated_at = timestamp
    store.save("characters", source)
    store.save("characters", target)
    _sync_roster_service_to_session(source, *source_context)
    _sync_roster_service_to_session(target, *target_context)
    return CharacterTransferResult(message=message, source=source, target=target)


@app.post("/api/characters/{character_id}/weapon-defaults")
async def set_character_weapon_defaults(character_id: str, payload: CharacterWeaponDefaults) -> Character:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    if (
        payload.default_melee_weapon is None
        and payload.default_melee_weapon_secondary is None
        and payload.default_missile_weapon is None
    ):
        raise HTTPException(status_code=400, detail="Provide at least one default weapon to set.")
    messages: list[str] = []
    if payload.default_melee_weapon is not None:
        ok, message = set_weapon_default(
            character,
            item_name=payload.default_melee_weapon,
            weapon_kind="melee",
            melee_slot="primary",
        )
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        messages.append(message)
    if payload.default_melee_weapon_secondary is not None:
        ok, message = set_weapon_default(
            character,
            item_name=payload.default_melee_weapon_secondary,
            weapon_kind="melee",
            melee_slot="secondary",
        )
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        messages.append(message)
    if payload.default_missile_weapon is not None:
        ok, message = set_weapon_default(
            character,
            item_name=payload.default_missile_weapon,
            weapon_kind="missile",
        )
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        messages.append(message)
    prune_weapon_defaults(character)
    character.updated_at = now_utc()
    store.save("characters", character)
    return character


@app.post("/api/characters/{character_id}/buy-equipment")
async def buy_character_equipment(character_id: str, payload: CharacterBuyEquipment) -> EquipmentTransactionResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _prepare_roster_service_character(character, service_label="Equipment shopping")
    catalog = rules.equipment_shop()
    ok, message = buy_equipment(
        character,
        catalog,
        item_key=payload.item_key,
        quantity=payload.quantity,
        potion_recipe_available=_secret_available_for_character(character, "potion_recipe"),
    )
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    character.updated_at = now_utc()
    store.save("characters", character)
    _sync_roster_service_to_session(character, session, member, carried_gold)
    return EquipmentTransactionResult(message=message, character=character)


@app.get("/api/characters/{character_id}/sell-quote")
async def quote_character_sale(character_id: str, item_name: str) -> dict:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    _prepare_roster_service_character(character, service_label="Equipment shopping")
    return sell_quote(character, rules.equipment_shop(), item_name=item_name)


@app.post("/api/characters/{character_id}/sell-item")
async def sell_character_item(character_id: str, payload: CharacterSellItem) -> EquipmentTransactionResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _prepare_roster_service_character(character, service_label="Equipment shopping")
    ok, message, gold_received = sell_item(
        character,
        rules.equipment_shop(),
        item_name=payload.item_name,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    character.updated_at = now_utc()
    store.save("characters", character)
    _sync_roster_service_to_session(character, session, member, carried_gold)
    return EquipmentTransactionResult(message=message, character=character, gold_received=gold_received)


@app.post("/api/characters/{character_id}/spend-xp")
async def spend_character_xp(character_id: str, payload: CharacterSpendXp) -> CharacterSpendXpResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    if character_busy_session_id(character, store):
        raise HTTPException(
            status_code=400,
            detail="Spend XP for active adventurers from the party sheet or camp XP panel.",
        )
    if character.xp <= 0:
        raise HTTPException(status_code=400, detail=f"{character.name} has no banked XP rolls.")

    member = _member_state(character)
    session = SessionState(
        id=f"roster-xp-{character.id}",
        party_id="roster",
        adventure_id="roster",
        adventure_type="random",
        party=[member],
        map_state=MapState(
            tiles=[TileState(id="roster", x=0, y=0, tile_key="00", tile_type="room", title="Roster", description="Roster")],
            current_tile_id="roster",
        ),
        created_at=now_utc(),
        updated_at=now_utc(),
        xp_system="classical",
    )
    random_engine._spend_banked_xp(
        session,
        character.id,
        show_rolls=payload.show_rolls,
        explain_math=payload.explain_math,
        new_spell=payload.spell_name,
        advancement_fork=payload.advancement_fork,
        expert_skill_id=payload.expert_skill_id,
        expert_skill_target=payload.expert_skill_target,
        heroic_skill_id=payload.heroic_skill_id,
        legendary_skill_id=payload.legendary_skill_id,
        heroic_skill_target=payload.heroic_skill_target,
    )
    if session.level_up_spell_pending_character_id:
        raise HTTPException(status_code=400, detail="Choose a spell for the new level before spending roster XP.")
    if member.xp == character.xp:
        detail = session.log[-1] if session.log else "XP was not spent."
        raise HTTPException(status_code=400, detail=detail)
    _apply_member_state_to_character(character, member)
    store.save("characters", character)
    return CharacterSpendXpResult(
        message=session.log[-1] if session.log else f"{character.name} spends 1 banked XP roll.",
        character=character,
        log=session.log,
    )


@app.get("/api/parties")
async def list_parties() -> list[Party]:
    return store.list("parties", Party.model_validate)


@app.post("/api/parties")
async def create_party(payload: PartyCreate) -> Party:
    characters = _load_characters(payload.character_ids)
    if len({character.id for character in characters}) != 4:
        raise HTTPException(status_code=400, detail="Choose four different characters.")
    busy: list[str] = []
    for character in characters:
        busy_session_id = character_busy_session_id(character, store)
        if busy_session_id:
            busy.append(f"{character.name} is already in an active adventure.")
    if busy:
        raise HTTPException(status_code=409, detail=" ".join(busy))
    timestamp = now_utc()
    party = Party(
        id=new_id(),
        name=payload.name.strip(),
        character_ids=payload.character_ids,
        created_at=timestamp,
        updated_at=timestamp,
    )
    store.save("parties", party)
    return party


@app.put("/api/parties/{party_id}")
async def update_party(party_id: str, payload: PartyCreate) -> Party:
    existing = store.get("parties", party_id, Party.model_validate)
    if existing is None:
        raise HTTPException(status_code=404, detail="Party not found.")
    characters = _load_characters(payload.character_ids)
    if len({character.id for character in characters}) != 4:
        raise HTTPException(status_code=400, detail="Choose four different characters.")
    busy: list[str] = []
    for character in characters:
        busy_session_id = character_busy_session_id(character, store)
        if busy_session_id:
            busy.append(f"{character.name} is already in an active adventure.")
    if busy:
        raise HTTPException(status_code=409, detail=" ".join(busy))
    existing.name = payload.name.strip()
    existing.character_ids = payload.character_ids
    existing.updated_at = now_utc()
    store.save("parties", existing)
    return existing


@app.delete("/api/parties/{party_id}")
async def delete_party(party_id: str) -> dict[str, bool]:
    return {"deleted": store.delete("parties", party_id)}


@app.post("/api/parties/{party_id}/heal")
async def heal_party(party_id: str) -> list[Character]:
    party = store.get("parties", party_id, Party.model_validate)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found.")
    characters = _load_characters(party.character_ids)
    for character in characters:
        session, member, carried_gold = _prepare_roster_service_character(character, service_label="Healing")
        _heal_character(character)
        store.save("characters", character)
        _sync_roster_service_to_session(character, session, member, carried_gold)
    return characters


@app.get("/api/adventures")
async def list_adventures() -> list[AdventureDescriptor]:
    adventures = [
        AdventureDescriptor(
            id="random",
            name="Random Dungeon",
            source="rules",
            playable=True,
            notes="Procedural dungeon using the starter rules engine.",
        )
    ]
    for pdf in sorted(settings.adventures_dir.glob("*.pdf")):
        adventures.append(
            AdventureDescriptor(
                id=pdf.stem,
                name=_title_from_pdf_name(pdf),
                source=str(pdf.relative_to(settings.root_dir)).replace("\\", "/"),
                playable=False,
                notes="PDF found; a reviewed adventure manifest is still required.",
            )
        )
    return adventures


@app.post("/api/sessions")
async def create_session(payload: dict[str, str]) -> SessionState:
    party_id = payload.get("party_id")
    adventure_id = payload.get("adventure_id", "random")
    if not party_id:
        raise HTTPException(status_code=400, detail="party_id is required.")
    if adventure_id != "random":
        raise HTTPException(status_code=400, detail="Imported adventures need manifests before play.")

    party = store.get("parties", party_id, Party.model_validate)
    if party is None:
        raise HTTPException(status_code=404, detail="Party not found.")
    characters = _load_characters(party.character_ids)
    busy: list[str] = []
    for character in characters:
        busy_session_id = character_busy_session_id(character, store)
        if busy_session_id:
            busy.append(f"{character.name} is already in an active adventure.")
    if busy:
        raise HTTPException(status_code=409, detail=" ".join(busy))

    xp_system = payload.get("xp_system", "classical")
    map_bounds_mode = payload.get("map_bounds_mode", "unlimited")
    session = random_engine.create_session(
        new_id(),
        party.id,
        [_member_state(character) for character in characters],
        xp_system=xp_system,
        map_bounds_mode=map_bounds_mode,
    )
    session.minor_encounters_defeated = max(
        (character.minor_encounters_cleared for character in characters),
        default=0,
    )
    lock_characters_for_session(session, store)
    store.save("sessions", session)
    return session


@app.get("/api/sessions")
async def list_sessions() -> list[SessionState]:
    reconcile_stale_character_locks(store)
    return store.list("sessions", SessionState.model_validate)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    session, changed = random_engine.normalize_session(session)
    if _restore_missing_recovery_members(session):
        changed = True
    if session.mode != "complete":
        lock_characters_for_session(session, store)
    if changed:
        store.save("sessions", session)
    return enrich_session(session)


@app.post("/api/sessions/{session_id}/save")
async def save_session(session_id: str, payload: SaveSessionRequest | None = None) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    timestamp = now_utc()
    session.saved_at = timestamp
    session.updated_at = timestamp
    if payload and payload.label is not None:
        label = payload.label.strip()
        session.save_label = label or None
    store.save("sessions", session)
    sync_minor_encounters_to_roster(session, store)
    return enrich_session(session)


@app.put("/api/sessions/{session_id}/party")
async def update_session_party(session_id: str, payload: SessionPartyUpdate) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    try:
        replace_session_party(
            session,
            payload.character_ids,
            store,
            member_state=_member_state,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    _sync_party_marching_order(session)
    party = store.get("parties", session.party_id, Party.model_validate)
    if party is not None:
        party.character_ids = list(payload.character_ids)
        party.updated_at = now_utc()
        store.save("parties", party)
    session.log.append("The camp party roster is updated.")
    store.save("sessions", session)
    return enrich_session(session)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, bool]:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is not None:
        unlock_characters_for_session(session, store)
    return {"deleted": store.delete("sessions", session_id)}


@app.post("/api/sessions/{session_id}/advance")
async def advance_session(session_id: str, payload: SessionAction) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    camped_before = session.camped_outside
    _restore_missing_recovery_members(session)
    session = random_engine.advance(
        session,
        payload.action,
        payload.exit_id,
        payload.direction,
        payload.character_id,
        show_rolls=payload.show_rolls,
        explain_math=payload.explain_math,
        search_choice=payload.search_choice,
        special_feature_choice=payload.special_feature_choice,
        tile_content_choice=payload.tile_content_choice,
        secret_passage_environment=payload.secret_passage_environment,
        environment_event_choice=payload.environment_event_choice,
        secret_id=payload.secret_id,
        spell_name=payload.spell_name,
        pay_bribe=payload.pay_bribe,
        trade_information_choice=payload.trade_information_choice,
        reaction_choice=payload.reaction_choice,
        subdual=payload.subdual,
        marching_order=payload.marching_order,
        alchemist_item=payload.alchemist_item,
        xp_spent=payload.xp_spent,
        target_character_id=payload.target_character_id,
        item_name=payload.item_name,
        gold_amount=payload.gold_amount,
        weapon_kind=payload.weapon_kind,
        attack_targets=payload.attack_targets,
        attack_secondary_targets=payload.attack_secondary_targets,
        double_kick_targets=payload.double_kick_targets,
        protective_incense_targets=payload.protective_incense_targets,
        nail_doors=payload.nail_doors,
        rest_choices=payload.rest_choices,
        combat_abilities=payload.combat_abilities,
        guard_targets=payload.guard_targets,
        gadget_points=payload.gadget_points,
        use_luck_flee=payload.use_luck_flee,
        class_ability=payload.class_ability,
        nourishing_meal=payload.nourishing_meal,
        nourishing_meal_eaters=payload.nourishing_meal_eaters,
        foe_id=payload.foe_id,
        secondary_foe_id=payload.secondary_foe_id,
        spell_target_mode=payload.spell_target_mode,
        tier_training=payload.tier_training,
        use_xp_for_tier=payload.use_xp_for_tier,
        advancement_fork=payload.advancement_fork,
        expert_skill_id=payload.expert_skill_id,
        expert_skill_target=payload.expert_skill_target,
        heroic_skill_id=payload.heroic_skill_id,
        legendary_skill_id=payload.legendary_skill_id,
        heroic_skill_target=payload.heroic_skill_target,
        reaction_adjust=payload.reaction_adjust,
        life_transfer_amount=payload.life_transfer_amount,
        teleport_tile_id=payload.teleport_tile_id,
        teleport_character_ids=payload.teleport_character_ids,
        dungeon_exit_intent=payload.dungeon_exit_intent,
        detached_character_ids=payload.detached_character_ids,
        detached_tile_id=payload.detached_tile_id,
        trap_boulder_origin=payload.trap_boulder_origin,
        trap_boulder_block_exit_id=payload.trap_boulder_block_exit_id,
    )
    _restore_missing_recovery_members(session)
    if payload.action == "set_marching_order":
        _sync_party_marching_order(session)
    if payload.action in {"transfer_gold", "transfer_item"} and payload.character_id and payload.target_character_id:
        sync_party_members_to_roster(
            session,
            store,
            {payload.character_id, payload.target_character_id},
        )
    if session.mode == "complete":
        roster_notes = persist_session_to_roster(session, store)
        unlock_characters_for_session(session, store)
        session.saved_at = None
        if roster_notes:
            if not any("Character roster updated" in line for line in session.summary or []):
                session.summary = list(session.summary or [])
                session.summary.append("Character roster updated with adventure rewards.")
            for line in roster_notes:
                if line not in session.log:
                    session.log.append(line)
    elif session.camped_outside:
        persist_session_to_roster(session, store)
        if not camped_before:
            sync_minor_encounters_to_roster(session, store)
    if session.mode != "complete":
        lock_characters_for_session(session, store)
    store.save("sessions", session)
    return enrich_session(session)


def _load_characters(character_ids: list[str]) -> list[Character]:
    characters: list[Character] = []
    for character_id in character_ids:
        character = store.get("characters", character_id, Character.model_validate)
        if character is None:
            raise HTTPException(status_code=404, detail=f"Character {character_id} not found.")
        characters.append(character)
    return characters


def _member_state(character: Character) -> PartyMemberState:
    carried_gold = min(character.gold, MAX_CARRIED_GOLD)
    member = PartyMemberState(
        character_id=character.id,
        name=character.name,
        class_id=character.class_id,
        class_name=character.class_name,
        level=character.level,
        xp=character.xp,
        gold=carried_gold,
        bank_gold=max(0, character.gold - carried_gold),
        clues=character.clues,
        secrets=list(character.secrets),
        current_life=character.current_life,
        max_life=character.max_life,
        attack_bonus=character.attack_bonus,
        defense_bonus=character.defense_bonus,
        save_bonus=character.save_bonus,
        marching_order=1,
        inventory=list(character.inventory),
        spells=list(character.spells),
        abilities=list(character.abilities),
        class_traits=list(character.class_traits),
        statuses=list(character.statuses),
        default_melee_weapon=character.default_melee_weapon,
        default_melee_weapon_secondary=character.default_melee_weapon_secondary,
        default_missile_weapon=character.default_missile_weapon,
        expert_trained=character.expert_trained,
        heroic_trained=character.heroic_trained,
        legendary_trained=character.legendary_trained,
        epic_trained=character.epic_trained,
        learned_expert_skills=list(character.learned_expert_skills),
        learned_heroic_skills=list(character.learned_heroic_skills),
        learned_legendary_skills=list(character.learned_legendary_skills),
        expert_skill_targets=dict(character.expert_skill_targets or {}),
    )
    snapshot_carry_baseline(member)
    return member


def _prepare_roster_service_character(
    character: Character,
    *,
    service_label: str,
) -> tuple[SessionState | None, PartyMemberState | None, int]:
    session_id = character.active_session_id
    if not session_id:
        return None, None, 0
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None or session.mode == "complete":
        return None, None, 0
    if not session.camped_outside:
        raise HTTPException(
            status_code=400,
            detail=f"{service_label} for active adventurers is available only while camped outside the dungeon.",
        )
    member = next((item for item in session.party if item.character_id == character.id), None)
    if member is None:
        raise HTTPException(status_code=400, detail=f"{character.name} is not in the active session party.")
    if member.current_life <= 0:
        raise HTTPException(
            status_code=400,
            detail=f"{member.name} is fallen and must use recovery options before roster services.",
        )
    carried_gold = max(0, min(member.gold, MAX_CARRIED_GOLD))
    character.gold = member.gold + member.bank_gold
    character.current_life = member.current_life
    character.max_life = member.max_life
    character.inventory = list(member.inventory)
    character.class_traits = list(member.class_traits)
    character.secrets = list(member.secrets)
    character.default_melee_weapon = member.default_melee_weapon
    character.default_melee_weapon_secondary = member.default_melee_weapon_secondary
    character.default_missile_weapon = member.default_missile_weapon
    return session, member, carried_gold


def _secret_available_for_character(character: Character, secret_id: str) -> bool:
    normalized = secret_id.strip().lower()
    if any(str(item).strip().lower().split(":", 1)[0] == normalized for item in character.secrets or []):
        return True
    session_id = character.active_session_id
    if not session_id:
        return False
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None or session.mode == "complete" or not session.camped_outside:
        return False
    return any(
        any(str(secret).strip().lower().split(":", 1)[0] == normalized for secret in member.secrets or [])
        for member in session.party
        if member.current_life > 0
    )


def _sync_roster_service_to_session(
    character: Character,
    session: SessionState | None,
    member: PartyMemberState | None,
    carried_gold_before: int,
) -> None:
    if session is None or member is None:
        return
    total_gold = max(0, character.gold)
    carried_gold = min(carried_gold_before, total_gold, MAX_CARRIED_GOLD)
    member.gold = carried_gold
    member.bank_gold = max(0, total_gold - carried_gold)
    member.current_life = character.current_life
    member.max_life = character.max_life
    member.inventory = list(character.inventory)
    member.class_traits = list(character.class_traits)
    member.secrets = list(character.secrets)
    member.default_melee_weapon = character.default_melee_weapon
    member.default_melee_weapon_secondary = character.default_melee_weapon_secondary
    member.default_missile_weapon = character.default_missile_weapon
    prune_weapon_defaults(member)
    session.updated_at = now_utc()
    store.save("sessions", session)


def _apply_member_state_to_character(character: Character, member: PartyMemberState) -> None:
    character.level = member.level
    character.xp = member.xp
    character.gold = member.gold + member.bank_gold
    character.current_life = member.current_life
    character.max_life = member.max_life
    character.attack_bonus = member.attack_bonus
    character.defense_bonus = member.defense_bonus
    character.save_bonus = member.save_bonus
    character.inventory = list(member.inventory)
    character.spells = list(member.spells)
    character.abilities = list(member.abilities)
    character.class_traits = list(member.class_traits)
    character.learned_expert_skills = list(member.learned_expert_skills)
    character.learned_heroic_skills = list(member.learned_heroic_skills)
    character.learned_legendary_skills = list(member.learned_legendary_skills)
    character.expert_skill_targets = dict(member.expert_skill_targets or {})
    character.secrets = list(member.secrets)
    character.statuses = list(member.statuses)
    character.default_melee_weapon = member.default_melee_weapon
    character.default_melee_weapon_secondary = member.default_melee_weapon_secondary
    character.default_missile_weapon = member.default_missile_weapon
    character.expert_trained = member.expert_trained
    character.heroic_trained = member.heroic_trained
    character.legendary_trained = member.legendary_trained
    character.epic_trained = member.epic_trained
    character.updated_at = now_utc()


def _sync_party_marching_order(session: SessionState) -> None:
    party = store.get("parties", session.party_id, Party.model_validate)
    if party is None:
        return
    ordered_ids = [
        member.character_id for member in sorted(session.party, key=lambda item: item.marching_order)
    ]
    if len(ordered_ids) != 4:
        return
    if ordered_ids == party.character_ids:
        return
    party.character_ids = ordered_ids
    party.updated_at = now_utc()
    store.save("parties", party)


def _heal_character(character: Character) -> None:
    character.current_life = character.max_life
    character.updated_at = now_utc()


def _valid_tile_keys() -> set[str]:
    return set(VALID_TILE_KEYS)


def _title_from_pdf_name(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()
