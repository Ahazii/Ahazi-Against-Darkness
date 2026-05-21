from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .config import load_settings
from .db import Store, init_db, new_id, now_utc
from .engine.equipment_shop import buy_equipment, list_shop_for_class, sell_item, sell_quote
from .engine.inventory import transfer_character_gold, transfer_character_item
from .engine.random_dungeon import RandomDungeonEngine
from .engine.roster_sync import persist_session_to_roster
from .engine.weapons import infer_default_weapons, prune_weapon_defaults, set_weapon_default
from .rules.repository import RulesRepository, VALID_TILE_KEYS
from .schemas import (
    AdventureDescriptor,
    Character,
    CharacterBuyEquipment,
    CharacterCreate,
    CharacterClass,
    CharacterSellItem,
    CharacterTransfer,
    CharacterTransferResult,
    CharacterWeaponDefaults,
    EquipmentTransactionResult,
    IconDefinition,
    Party,
    PartyCreate,
    PartyMemberState,
    SessionAction,
    SessionState,
    TileDefinition,
)


settings = load_settings()
init_db(settings.db_path)
store = Store(settings.db_path)
rules = RulesRepository(settings.packaged_rules_dir, settings.rules_dir)
random_engine = RandomDungeonEngine(rules, settings.assets_dir)

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


@app.get("/api/rules/tables")
async def list_tables() -> dict:
    return _rules_tables_payload()


def _rules_tables_payload() -> dict:
    data = dict(rules.dungeon_tables())
    shop = rules.equipment_shop()
    rows: list[dict] = []
    for index, item in enumerate(shop.get("items", []), start=1):
        price = int(item["price_gp"])
        rows.append(
            {
                "roll": str(index),
                "result": f"{item['name']}: {price}gp buy; {price // 2}gp sell (half list).",
                "source_page": shop.get("source_page", 16),
            }
        )
    rows.append(
        {
            "roll": "sell",
            "result": (
                "Magic may be sold but not bought (p.19): potions/rings 50gp; "
                "wands/scrolls/staves 100gp per spell; other magic d6×d6 gp; "
                "gems +20% for dwarves."
            ),
            "source_page": 19,
        }
    )
    data["equipment_shop_table"] = rows
    return data


@app.get("/api/rules/equipment-shop")
async def equipment_shop_catalog(class_id: str | None = None) -> dict:
    catalog = rules.equipment_shop()
    if class_id:
        return {
            "catalog": catalog,
            "items": list_shop_for_class(catalog, class_id),
            "notes": (
                "Buy before or between adventures (p.16). Magic may be sold but not bought (p.19). "
                "Roster gold is not capped; the 200gp carry limit applies only inside the dungeon."
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
    return rules.icons()


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
    return store.list("characters", Character.model_validate)


@app.post("/api/characters")
async def create_character(payload: CharacterCreate) -> Character:
    profile = rules.class_by_id(payload.class_id)
    if profile is None:
        raise HTTPException(status_code=400, detail="Unknown class.")
    timestamp = now_utc()
    character = Character(
        id=new_id(),
        name=payload.name.strip(),
        class_id=profile.id,
        class_name=profile.name,
        level=1,
        xp=0,
        gold=profile.starting_gold,
        max_life=profile.base_life,
        current_life=profile.base_life,
        attack_bonus=profile.attack_bonus,
        defense_bonus=profile.defense_bonus,
        save_bonus=profile.save_bonus,
        inventory=list(profile.starting_inventory),
        spells=list(profile.starting_spells),
        abilities=list(profile.abilities),
        statuses=[],
        created_at=timestamp,
        updated_at=timestamp,
    )
    default_melee, default_missile = infer_default_weapons(character.inventory)
    character.default_melee_weapon = default_melee
    character.default_missile_weapon = default_missile
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
    _heal_character(character)
    store.save("characters", character)
    return character


@app.post("/api/characters/{character_id}/transfer")
async def transfer_character_gear(character_id: str, payload: CharacterTransfer) -> CharacterTransferResult:
    source = store.get("characters", character_id, Character.model_validate)
    if source is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    target = store.get("characters", payload.target_character_id, Character.model_validate)
    if target is None:
        raise HTTPException(status_code=404, detail="Target character not found.")
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
    return CharacterTransferResult(message=message, source=source, target=target)


@app.post("/api/characters/{character_id}/weapon-defaults")
async def set_character_weapon_defaults(character_id: str, payload: CharacterWeaponDefaults) -> Character:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    if payload.default_melee_weapon is None and payload.default_missile_weapon is None:
        raise HTTPException(status_code=400, detail="Provide at least one default weapon to set.")
    messages: list[str] = []
    if payload.default_melee_weapon is not None:
        ok, message = set_weapon_default(
            character,
            item_name=payload.default_melee_weapon,
            weapon_kind="melee",
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
    catalog = rules.equipment_shop()
    ok, message = buy_equipment(character, catalog, item_key=payload.item_key)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    character.updated_at = now_utc()
    store.save("characters", character)
    return EquipmentTransactionResult(message=message, character=character)


@app.get("/api/characters/{character_id}/sell-quote")
async def quote_character_sale(character_id: str, item_name: str) -> dict:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    return sell_quote(character, rules.equipment_shop(), item_name=item_name)


@app.post("/api/characters/{character_id}/sell-item")
async def sell_character_item(character_id: str, payload: CharacterSellItem) -> EquipmentTransactionResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    ok, message, gold_received = sell_item(
        character,
        rules.equipment_shop(),
        item_name=payload.item_name,
    )
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    character.updated_at = now_utc()
    store.save("characters", character)
    return EquipmentTransactionResult(message=message, character=character, gold_received=gold_received)


@app.get("/api/parties")
async def list_parties() -> list[Party]:
    return store.list("parties", Party.model_validate)


@app.post("/api/parties")
async def create_party(payload: PartyCreate) -> Party:
    characters = _load_characters(payload.character_ids)
    if len({character.id for character in characters}) != 4:
        raise HTTPException(status_code=400, detail="Choose four different characters.")
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
        _heal_character(character)
        store.save("characters", character)
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
    xp_system = payload.get("xp_system", "classical")
    map_bounds_mode = payload.get("map_bounds_mode", "unlimited")
    session = random_engine.create_session(
        new_id(),
        party.id,
        [_member_state(character) for character in characters],
        xp_system=xp_system,
        map_bounds_mode=map_bounds_mode,
    )
    store.save("sessions", session)
    return session


@app.get("/api/sessions")
async def list_sessions() -> list[SessionState]:
    return store.list("sessions", SessionState.model_validate)


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    session, changed = random_engine.normalize_session(session)
    if changed:
        store.save("sessions", session)
    return session


@app.post("/api/sessions/{session_id}/save")
async def save_session(session_id: str) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    timestamp = now_utc()
    session.saved_at = timestamp
    session.updated_at = timestamp
    store.save("sessions", session)
    return session


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, bool]:
    return {"deleted": store.delete("sessions", session_id)}


@app.post("/api/sessions/{session_id}/advance")
async def advance_session(session_id: str, payload: SessionAction) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = random_engine.advance(
        session,
        payload.action,
        payload.exit_id,
        payload.direction,
        payload.character_id,
        show_rolls=payload.show_rolls,
        explain_math=payload.explain_math,
        search_choice=payload.search_choice,
        spell_name=payload.spell_name,
        pay_bribe=payload.pay_bribe,
        subdual=payload.subdual,
        marching_order=payload.marching_order,
        alchemist_item=payload.alchemist_item,
        xp_spent=payload.xp_spent,
        target_character_id=payload.target_character_id,
        item_name=payload.item_name,
        gold_amount=payload.gold_amount,
        weapon_kind=payload.weapon_kind,
        attack_targets=payload.attack_targets,
    )
    if payload.action == "set_marching_order":
        _sync_party_marching_order(session)
    if session.mode == "complete":
        roster_notes = persist_session_to_roster(session, store)
        if roster_notes:
            if not any("Character roster updated" in line for line in session.summary or []):
                session.summary = list(session.summary or [])
                session.summary.append("Character roster updated with adventure rewards.")
            for line in roster_notes:
                if line not in session.log:
                    session.log.append(line)
    store.save("sessions", session)
    return session


def _load_characters(character_ids: list[str]) -> list[Character]:
    characters: list[Character] = []
    for character_id in character_ids:
        character = store.get("characters", character_id, Character.model_validate)
        if character is None:
            raise HTTPException(status_code=404, detail=f"Character {character_id} not found.")
        characters.append(character)
    return characters


def _member_state(character: Character) -> PartyMemberState:
    return PartyMemberState(
        character_id=character.id,
        name=character.name,
        class_id=character.class_id,
        class_name=character.class_name,
        level=character.level,
        xp=character.xp,
        gold=character.gold,
        current_life=character.current_life,
        max_life=character.max_life,
        attack_bonus=character.attack_bonus,
        defense_bonus=character.defense_bonus,
        save_bonus=character.save_bonus,
        marching_order=1,
        inventory=list(character.inventory),
        spells=list(character.spells),
        abilities=list(character.abilities),
        statuses=list(character.statuses),
        default_melee_weapon=character.default_melee_weapon,
        default_missile_weapon=character.default_missile_weapon,
    )


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
