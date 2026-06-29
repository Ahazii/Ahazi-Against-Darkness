from __future__ import annotations

from pathlib import Path
from typing import Any

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
from .engine.adventure_skeleton import generate_adventure_skeleton
from .engine.adventure_tile_catalog import build_tile_catalog
from .engine.adventure_prompt import LENGTH_ROOM_HINTS, adventure_prompt_defaults, build_adventure_prompt
from .engine.adventure_import import (
    build_adventure_export_zip,
    import_adventure_manifest,
    list_installed_adventures,
    remove_installed_adventure,
    load_installed_manifest,
    seed_bundled_adventures,
)
from .engine.adventure_allowlists import build_adventure_allowlists
from .engine.adventure_manifest import validate_adventure_manifest
from .engine.adventure_session import create_session_from_manifest
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
from .engine.expert_skills import (
    expert_skills_catalog_with_summaries,
    expert_skills_table_rows,
    expert_spells_table_rows,
)
from .engine.expert_skill_effects import expert_skill_implementation_rows
from .engine.hirelings import hirelings_table_rows, load_hirelings_catalog
from .engine.milestones import milestones_table_rows
from .engine.tier_skills import (
    class_tricks_implementation_rows,
    ee_class_trick_flags_table_rows,
    tier_skills_catalog_with_summaries,
    tier_skills_table_rows,
)
from .engine.tile_catalogs import room_codes_table_rows
from .engine.tile_validation import map_elements_validation_table_rows
from .engine.tier_advancement import TIER_ENTRY
from .engine.weapons import infer_default_weapons, prune_weapon_defaults, set_weapon_default
from .rules.repository import RulesRepository, VALID_TILE_KEYS
from .schemas import (
    AdventureDescriptor,
    AdventurePromptParameters,
    AdventurePromptResponse,
    AdventureSkeletonResponse,
    CampaignState,
    Character,
    CharacterBuyEquipment,
    CharacterCreate,
    CharacterClass,
    CharacterMilestoneRequest,
    CharacterMilestoneResult,
    CharacterPanopliaFavorRequest,
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
    SessionListSummary,
    SessionPartyUpdate,
    SessionState,
    TileState,
    TileDefinition,
)


settings = load_settings()
init_db(settings.db_path)
seed_bundled_adventures(settings.root_dir, settings.data_dir)
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
    from .engine.terrain import resolve_play_context
    from .schemas import PlayContextView

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
    ctx = resolve_play_context(tile, session)
    session.play_context = PlayContextView(**ctx.as_dict())
    return session


def session_to_summary(session: SessionState) -> SessionListSummary:
    manifest = session.imported_manifest or {}
    quest = session.active_quest
    return SessionListSummary(
        id=session.id,
        party_id=session.party_id,
        adventure_id=session.adventure_id,
        adventure_type=session.adventure_type,
        mode=session.mode,
        camped_outside=session.camped_outside,
        save_label=session.save_label,
        saved_at=session.saved_at,
        updated_at=session.updated_at,
        created_at=session.created_at,
        tile_count=len(session.map_state.tiles),
        imported_title=str(manifest.get("title") or "").strip() or None
        if session.adventure_type == "imported"
        else None,
        imported_room_count=len(manifest.get("rooms") or [])
        if session.adventure_type == "imported" and isinstance(manifest.get("rooms"), list)
        else None,
        active_quest_description=(quest.description or "").strip() or None if quest else None,
    )


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
app.mount("/docs", StaticFiles(directory=settings.root_dir / "docs"), name="docs")


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


@app.get("/api/rules/milestones")
async def list_milestones() -> list[dict]:
    from .engine.milestones import milestone_catalog

    return milestone_catalog()


@app.get("/api/rules/hirelings")
async def list_hirelings() -> dict:
    from .engine.hirelings import load_hirelings_catalog

    return load_hirelings_catalog()


@app.get("/api/rules/profiles")
async def list_ruleset_profiles(adventure_id: str = "random") -> list[dict[str, object]]:
    from .engine.ruleset_profiles import profiles_for_adventure

    return [
        {
            "id": profile.id,
            "label": profile.label,
            "description": profile.description,
            "ruleset": profile.ruleset,
            "courtship_enabled": profile.courtship_enabled,
            "fiendish_foes_default": profile.fiendish_foes_default,
            "source_books": profile.source_books,
        }
        for profile in profiles_for_adventure(adventure_id)
    ]


@app.get("/api/rules/classes")
async def list_classes(ruleset_profile_id: str | None = None) -> list[CharacterClass]:
    classes = rules.classes()
    if not ruleset_profile_id:
        return classes
    from .engine.ruleset_profiles import filter_classes_for_profile, profile_by_id

    profile = profile_by_id(ruleset_profile_id)
    if profile is None:
        raise HTTPException(status_code=400, detail=f"Unknown ruleset profile: {ruleset_profile_id}")
    return filter_classes_for_profile(classes, profile)


@app.get("/api/campaign")
async def get_campaign() -> CampaignState:
    from .engine.tag_campaign import load_campaign

    return load_campaign(store)


@app.put("/api/campaign")
async def update_campaign(payload: dict[str, Any]) -> CampaignState:
    from .engine.tag_campaign import load_campaign, save_campaign, update_settlement

    campaign = load_campaign(store)
    if "tag_banking_enabled" in payload:
        campaign.tag_banking_enabled = _parse_bool(payload.get("tag_banking_enabled"))
    update_settlement(
        campaign,
        name=payload.get("settlement_name") if "settlement_name" in payload else None,
        size=payload.get("settlement_size") if "settlement_size" in payload else None,
        notes=payload.get("settlement_notes") if "settlement_notes" in payload else None,
    )
    return save_campaign(store, campaign)


@app.post("/api/campaign/settlement/roll-size")
async def campaign_roll_settlement_size() -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_settlement_size, save_campaign

    campaign = load_campaign(store)
    campaign, roll = roll_settlement_size(campaign)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "roll": roll}


@app.post("/api/campaign/tag/availability")
async def campaign_tag_availability(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import check_item_availability, load_campaign, save_campaign

    campaign = load_campaign(store)
    item_name = str(payload.get("item_name") or "").strip()
    if not item_name:
        raise HTTPException(status_code=400, detail="Item name is required.")
    base_price = payload.get("base_price_gp")
    check = check_item_availability(
        campaign,
        item_name=item_name,
        difficulty=int(payload.get("difficulty") or 6),
        base_price_gp=None if base_price in (None, "") else int(base_price),
    )
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "check": check}


@app.get("/api/campaign/tag/services")
async def campaign_tag_services() -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, settlement_service_rows

    campaign = load_campaign(store)
    return {"campaign": campaign, "services": settlement_service_rows(campaign)}


@app.post("/api/campaign/tag/hidden-trove-risk")
async def campaign_tag_hidden_trove_risk() -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_hidden_treasure_trove_risk, save_campaign

    campaign = load_campaign(store)
    entry = roll_hidden_treasure_trove_risk(campaign)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/treasure-map-price")
async def campaign_tag_treasure_map_price() -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_treasure_map_price, save_campaign

    campaign = load_campaign(store)
    entry = roll_treasure_map_price(campaign)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/moneylender-follow")
async def campaign_tag_moneylender_follow(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_moneylender_follow_chance, save_campaign

    campaign = load_campaign(store)
    entry = roll_moneylender_follow_chance(campaign, debt_gp=int(payload.get("debt_gp") or 0))
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/horn-attract")
async def campaign_tag_horn_attract() -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_horn_wandering_attraction, save_campaign

    campaign = load_campaign(store)
    entry = roll_horn_wandering_attraction(campaign)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/flammable-oil-throw")
async def campaign_tag_flammable_oil_throw() -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_flammable_oil_throw, save_campaign

    campaign = load_campaign(store)
    entry = roll_flammable_oil_throw(campaign)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/aspergillum-break")
async def campaign_tag_aspergillum_break() -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_aspergillum_break_chance, save_campaign

    campaign = load_campaign(store)
    entry = roll_aspergillum_break_chance(campaign)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/travel-settlement")
async def campaign_tag_travel_settlement(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, save_campaign, travel_to_new_settlement

    campaign = load_campaign(store)
    entry = travel_to_new_settlement(
        campaign,
        destination_name=str(payload.get("destination_name") or ""),
        use_hex_map=_parse_bool(payload.get("use_hex_map")),
        pay_road_tithe=_parse_bool(payload.get("pay_road_tithe")),
    )
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/look-for-clues")
async def campaign_tag_look_for_clues(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, look_for_clues, save_campaign

    character_id = str(payload.get("character_id") or "").strip()
    if not character_id:
        raise HTTPException(status_code=400, detail="Character is required.")
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = look_for_clues(
        campaign,
        character,
        natural_one_consequence=str(payload.get("natural_one_consequence") or "gold"),
    )
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/troupe")
async def campaign_tag_troupe(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, save_campaign, update_troupe

    raw_ids = payload.get("active_character_ids")
    active_ids = raw_ids if isinstance(raw_ids, list) else []
    raw_member_ids = payload.get("member_character_ids")
    member_ids = raw_member_ids if isinstance(raw_member_ids, list) else None
    campaign = load_campaign(store)
    update_troupe(
        campaign,
        troupe_name=str(payload.get("troupe_name") or ""),
        member_character_ids=[str(character_id) for character_id in member_ids] if member_ids is not None else None,
        active_character_ids=[str(character_id) for character_id in active_ids],
        guild_member=_parse_bool(payload.get("guild_member")),
        guild_coffers_gp=int(payload.get("guild_coffers_gp") or 0),
    )
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign}


@app.post("/api/campaign/tag/bank-migration")
async def campaign_tag_bank_migration(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import convert_character_gold_to_tag_bank, load_campaign, save_campaign

    campaign = load_campaign(store)
    include_legacy_bank = _parse_bool(payload.get("include_legacy_bank"))
    apply_deposit_fee = _parse_bool(payload.get("apply_deposit_fee"))
    character_id = str(payload.get("character_id") or "").strip()
    character_ids = [character_id] if character_id else [item.id for item in store.list("characters", Character.model_validate)]
    entries = []
    characters = []
    for current_id in character_ids:
        character = store.get("characters", current_id, Character.model_validate)
        if character is None:
            continue
        legacy_bank_gold = 0
        changed_sessions: list[SessionState] = []
        if include_legacy_bank:
            for session in store.list("sessions", SessionState.model_validate):
                changed = False
                for member in session.party:
                    if member.character_id == current_id and member.bank_gold > 0:
                        legacy_bank_gold += member.bank_gold
                        member.bank_gold = 0
                        changed = True
                if changed:
                    changed_sessions.append(session)
        entry = convert_character_gold_to_tag_bank(
            campaign,
            character,
            include_legacy_bank=include_legacy_bank,
            legacy_bank_gold=legacy_bank_gold,
            apply_deposit_fee=apply_deposit_fee,
            note=str(payload.get("note") or "TAG banking migration"),
        )
        store.save("characters", character)
        for session in changed_sessions:
            store.save("sessions", session)
        entries.append(entry)
        characters.append(character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "characters": characters, "entries": entries}


@app.post("/api/campaign/tag/store-treasure")
async def campaign_tag_store_treasure(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, save_campaign, store_tag_treasure

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = store_tag_treasure(
        campaign,
        character,
        storage=str(payload.get("storage") or "trove"),
        gold_gp=int(payload.get("gold_gp") or 0),
        item_name=str(payload.get("item_name") or ""),
        quantity=int(payload.get("quantity") or 1),
        notes=str(payload.get("notes") or ""),
    )
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/withdraw-stored-gold")
async def campaign_tag_withdraw_stored_gold(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, save_campaign, withdraw_tag_stored_gold

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = withdraw_tag_stored_gold(campaign, character, gold_gp=int(payload.get("gold_gp") or 0))
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/magic-locker")
async def campaign_tag_magic_locker(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import create_magic_locker, load_campaign, save_campaign

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = create_magic_locker(
        campaign,
        character,
        contents=str(payload.get("contents") or ""),
        kind=str(payload.get("kind") or "item"),
        gold_gp=int(payload.get("gold_gp") or 0),
    )
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/magic-locker-summon")
async def campaign_tag_magic_locker_summon(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, save_campaign, summon_magic_locker

    campaign = load_campaign(store)
    entry = summon_magic_locker(campaign, locker_id=str(payload.get("locker_id") or ""))
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/purchase-service")
async def campaign_tag_purchase_service(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, purchase_tag_service, save_campaign

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = purchase_tag_service(
        campaign,
        character,
        service_key=str(payload.get("service_key") or ""),
        quantity=int(payload.get("quantity") or 1),
    )
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/gambling-house")
async def campaign_tag_gambling_house(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, roll_gambling_house, save_campaign

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = roll_gambling_house(campaign, character, stake_gp=int(payload.get("stake_gp") or 0))
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/streetwise-action")
async def campaign_tag_streetwise_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, run_streetwise_action, save_campaign

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = run_streetwise_action(
        campaign,
        character,
        action=str(payload.get("action") or "listen_rumors"),
        target_level=int(payload.get("target_level") or 6),
        target_name=str(payload.get("target_name") or ""),
    )
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/follow-treasure-map")
async def campaign_tag_follow_treasure_map(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import follow_treasure_map, load_campaign, save_campaign

    campaign = load_campaign(store)
    entry = follow_treasure_map(campaign, use_guild_cartographer=_parse_bool(payload.get("use_guild_cartographer")))
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


def _optional_campaign_character(payload: dict[str, Any]) -> Character | None:
    character_id = str(payload.get("character_id") or "").strip()
    if not character_id:
        return None
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    return character


@app.post("/api/campaign/tag/branch-action")
async def campaign_tag_branch_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, resolve_tag_branch_action, save_campaign

    campaign = load_campaign(store)
    character = _optional_campaign_character(payload)
    entry = resolve_tag_branch_action(
        campaign,
        character,
        branch_action=str(payload.get("branch_action") or "social_choice"),
        reference=str(payload.get("reference") or ""),
        clue_cost=int(payload.get("clue_cost") or 0),
        reward_gp=int(payload.get("reward_gp") or 0),
    )
    if character is not None:
        store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/use-trinket")
async def campaign_tag_use_trinket(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, save_campaign, use_tag_trinket

    character = _optional_campaign_character(payload)
    if character is None:
        raise HTTPException(status_code=400, detail="Character is required.")
    campaign = load_campaign(store)
    entry = use_tag_trinket(campaign, character, trinket_key=str(payload.get("trinket_key") or ""))
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/route-action")
async def campaign_tag_route_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import apply_latest_tag_route_to_adventure, load_campaign, resolve_tag_route_action, save_campaign

    campaign = load_campaign(store)
    character = _optional_campaign_character(payload)
    entry = resolve_tag_route_action(
        campaign,
        character,
        route_action=str(payload.get("route_action") or "parley_success"),
        reference=str(payload.get("reference") or ""),
        clue_cost=int(payload.get("clue_cost") or 0),
    )
    rewrite_result = apply_latest_tag_route_to_adventure(settings.data_dir, campaign)
    if character is not None:
        store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry, "rewrite_result": rewrite_result}


@app.post("/api/campaign/tag/scene-action")
async def campaign_tag_scene_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, resolve_tag_scene_action, save_campaign

    character = _optional_campaign_character(payload)
    if character is None:
        raise HTTPException(status_code=400, detail="Character is required.")
    campaign = load_campaign(store)
    entry = resolve_tag_scene_action(
        campaign,
        character,
        scene_action=str(payload.get("scene_action") or ""),
        amount=int(payload.get("amount") or 0),
    )
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/xp-action")
async def campaign_tag_xp_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, resolve_tag_xp_action, save_campaign

    campaign = load_campaign(store)
    character = _optional_campaign_character(payload)
    entry = resolve_tag_xp_action(
        campaign,
        character,
        xp_action=str(payload.get("xp_action") or "mark_scene_xp"),
        reference=str(payload.get("reference") or ""),
        xp=int(payload.get("xp") or 0),
    )
    if character is not None:
        store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/guild-spell")
async def campaign_tag_guild_spell(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import cast_tag_guild_spell, load_campaign, save_campaign

    character = _optional_campaign_character(payload)
    if character is None:
        raise HTTPException(status_code=400, detail="Character is required.")
    campaign = load_campaign(store)
    entry = cast_tag_guild_spell(campaign, character, spell_key=str(payload.get("spell_key") or ""))
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/guild-marker")
async def campaign_tag_guild_marker(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import consume_tag_guild_marker, load_campaign, save_campaign

    character = _optional_campaign_character(payload)
    if character is None:
        raise HTTPException(status_code=400, detail="Character is required.")
    campaign = load_campaign(store)
    entry = consume_tag_guild_marker(campaign, character, marker_key=str(payload.get("marker_key") or ""))
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/finance-action")
async def campaign_tag_finance_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, resolve_tag_finance_action, save_campaign

    campaign = load_campaign(store)
    character = _optional_campaign_character(payload)
    entry = resolve_tag_finance_action(
        campaign,
        character,
        finance_action=str(payload.get("finance_action") or "loan_enforcement"),
        amount_gp=int(payload.get("amount_gp") or 0),
        note=str(payload.get("note") or ""),
    )
    if character is not None:
        store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/create-adventure")
async def campaign_tag_create_adventure(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.adventure_import import import_adventure_manifest
    from .engine.tag_campaign import build_tag_adventure_manifest, load_campaign, save_campaign

    campaign = load_campaign(store)
    manifest, entry = build_tag_adventure_manifest(
        campaign,
        lead_type=str(payload.get("lead_type") or "rumor"),
        detail=str(payload.get("detail") or ""),
    )
    path, result = import_adventure_manifest(
        settings.root_dir,
        settings.data_dir,
        manifest,
        rules_repo=rules,
        overwrite=True,
    )
    if not result.valid or path is None:
        raise HTTPException(status_code=400, detail="; ".join(result.errors) or "TAG adventure creation failed.")
    campaign = save_campaign(store, campaign)
    return {
        "campaign": campaign,
        "entry": entry,
        "adventure_id": manifest["id"],
        "title": manifest["title"],
        "room_count": len(manifest.get("rooms", [])),
        "quest_objective": (manifest.get("quest") or {}).get("objective_text"),
        "warnings": result.warnings,
    }


@app.get("/api/rules/tiles")
async def list_tiles(catalog: str = "ee") -> list[TileDefinition]:
    try:
        return list(rules.tiles(catalog).values())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/rules/tiles/validation")
async def validate_tiles(catalog: str = "ee") -> dict:
    from .engine.tile_validation import validate_tile_catalog

    try:
        issues = validate_tile_catalog(rules.tiles(catalog), catalog=catalog)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"catalog": catalog, "valid": not issues, "issues": issues}


@app.get("/api/rules/tiles/room-codes")
async def tile_room_code_reference(catalog: str = "ee") -> dict:
    from .engine.tile_catalogs import ROOM_CODE_DESCRIPTIONS, normalize_catalog_id, room_codes_for_catalog

    try:
        catalog_id = normalize_catalog_id(catalog)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    codes = room_codes_for_catalog(catalog_id)
    return {
        "catalog": catalog_id,
        "codes": [{ "code": code, "description": ROOM_CODE_DESCRIPTIONS[code] } for code in codes],
    }


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
    data["forsaken_depths_map_elements_validation_table"] = map_elements_validation_table_rows(
        rules.tiles("forsaken_depths"), catalog="forsaken_depths"
    )
    data["forsaken_depths_rivers_map_elements_validation_table"] = map_elements_validation_table_rows(
        rules.tiles("forsaken_depths_rivers"), catalog="forsaken_depths_rivers"
    )
    data["forsaken_depths_room_codes_table"] = room_codes_table_rows()
    data["hirelings_table"] = hirelings_table_rows(load_hirelings_catalog())
    data["milestones_table"] = milestones_table_rows()
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
    return expert_skills_catalog_with_summaries(rules.expert_skills())


@app.get("/api/rules/heroic-skills")
async def heroic_skills_catalog() -> dict:
    return tier_skills_catalog_with_summaries(rules.heroic_skills(), "heroic")


@app.get("/api/rules/legendary-skills")
async def legendary_skills_catalog() -> dict:
    return tier_skills_catalog_with_summaries(rules.legendary_skills(), "legendary")


@app.get("/api/rules/enchanted-paint-options")
async def enchanted_paint_options() -> dict:
    from .engine.special_items import MAX_ENCHANTED_PAINT_ITEM_PRICE_GP, paintable_shop_items

    catalog = rules.equipment_shop()
    items = paintable_shop_items(catalog)
    return {
        "max_price_gp": MAX_ENCHANTED_PAINT_ITEM_PRICE_GP,
        "source_page": 186,
        "notes": (
            "EE p.186: paint non-magical equipment worth 15gp or less; no liquids; "
            "up to 8 Food rations; or draw a door on a wall (then explore as usual)."
        ),
        "food_rations_max": 8,
        "items": items,
    }


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
async def save_tiles(payload: list[TileDefinition], catalog: str = "ee") -> dict[str, str | int]:
    from .engine.tile_catalogs import TILE_CATALOG_KEYS, normalize_catalog_id

    try:
        catalog_id = normalize_catalog_id(catalog)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if len({tile.key for tile in payload}) != len(payload):
        raise HTTPException(status_code=400, detail="Duplicate tile keys are not allowed.")
    allowed_keys = TILE_CATALOG_KEYS[catalog_id]
    invalid_keys = sorted({tile.key for tile in payload} - allowed_keys)
    if invalid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid map element keys: {', '.join(invalid_keys)}.")
    if catalog_id == "ee":
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
    else:
        invalid_dungeon_exits = [tile.key for tile in payload if any(exit_state.dungeon_exit for exit_state in tile.exits)]
        if invalid_dungeon_exits:
            raise HTTPException(
                status_code=400,
                detail=f"Dungeon exits are not used in {catalog_id} tiles: {', '.join(invalid_dungeon_exits)}.",
            )
    rules.save_tiles(payload, catalog=catalog_id)
    return {"status": "ok", "catalog": catalog_id, "count": len(payload)}


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
        party_inventories=[member.inventory for member in session.party] if session else None,
        target_weapon=payload.target_weapon,
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


def _character_milestone_context(
    character: Character,
    *,
    service_label: str,
) -> tuple[SessionState | None, PartyMemberState, int]:
    session_id = character.active_session_id
    if session_id:
        session = store.get("sessions", session_id, SessionState.model_validate)
        if session is not None and session.mode != "complete":
            if not session.camped_outside:
                raise HTTPException(
                    status_code=400,
                    detail=f"{service_label} for active adventurers is available only while camped outside the dungeon.",
                )
            member = next((item for item in session.party if item.character_id == character.id), None)
            if member is None:
                raise HTTPException(status_code=400, detail=f"{character.name} is not in the active session party.")
            carried_gold = max(0, min(member.gold, MAX_CARRIED_GOLD))
            return session, member, carried_gold
    return None, _member_state(character), 0


def _finish_character_milestone(
    character: Character,
    member: PartyMemberState,
    session: SessionState | None,
    carried_gold: int,
    logs: list[str],
) -> CharacterMilestoneResult:
    if session is not None:
        total_gold = member.gold + member.bank_gold
        carried_gold = min(carried_gold or member.gold, total_gold, MAX_CARRIED_GOLD)
        member.gold = carried_gold
        member.bank_gold = max(0, total_gold - carried_gold)
        session.updated_at = now_utc()
        store.save("sessions", session)
    _apply_member_state_to_character(character, member)
    store.save("characters", character)
    return CharacterMilestoneResult(
        message=logs[-1] if logs else f"{character.name} milestone updated.",
        character=character,
        log=logs,
    )


@app.post("/api/characters/{character_id}/milestone")
async def set_character_milestone(character_id: str, payload: CharacterMilestoneRequest) -> CharacterMilestoneResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _character_milestone_context(character, service_label="Milestone selection")
    from .engine.milestones import assign_milestone

    logs = assign_milestone(member, payload.milestone_id)
    return _finish_character_milestone(character, member, session, carried_gold, logs)


@app.post("/api/characters/{character_id}/milestone/bind-grimoire")
async def bind_character_scroll_librarian(
    character_id: str,
    payload: CharacterMilestoneRequest,
) -> CharacterMilestoneResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _character_milestone_context(character, service_label="Scroll Librarian")
    from .engine.milestones import bind_scroll_librarian

    logs = bind_scroll_librarian(member, payload.scroll_librarian_spell or "")
    return _finish_character_milestone(character, member, session, carried_gold, logs)


@app.post("/api/characters/{character_id}/milestone/craft-jewelry")
async def craft_character_gem_jewelry(character_id: str) -> CharacterMilestoneResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _character_milestone_context(character, service_label="Gem Collector")
    from .engine.milestones import craft_gem_collector_jewelry

    logs = craft_gem_collector_jewelry(member)
    return _finish_character_milestone(character, member, session, carried_gold, logs)


@app.post("/api/characters/{character_id}/milestone/panoplia")
async def create_character_panoplia(character_id: str) -> CharacterMilestoneResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _character_milestone_context(character, service_label="Panoplia")
    from .engine.milestones import create_panoplia

    logs = create_panoplia(member)
    return _finish_character_milestone(character, member, session, carried_gold, logs)


@app.post("/api/characters/{character_id}/milestone/panoplia-favor")
async def use_character_panoplia_favor(
    character_id: str,
    payload: CharacterPanopliaFavorRequest,
) -> CharacterMilestoneResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _character_milestone_context(character, service_label="Panoplia favor")
    from .engine.milestones import use_panoplia_favor

    logs = use_panoplia_favor(member, payload.favor_kind)
    return _finish_character_milestone(character, member, session, carried_gold, logs)


@app.post("/api/characters/{character_id}/milestone/thrice-blessed-sacrifice")
async def pay_character_thrice_blessed_sacrifice(character_id: str) -> CharacterMilestoneResult:
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _character_milestone_context(character, service_label="Thrice Blessed sacrifice")
    from .engine.milestones import pay_thrice_blessed_sacrifice

    logs = pay_thrice_blessed_sacrifice(member)
    return _finish_character_milestone(character, member, session, carried_gold, logs)


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
        ),
        AdventureDescriptor(
            id="courtship-demesne",
            name="Courtship of Flower Demons — Blossoms' Demesne",
            source="rules",
            playable=True,
            notes="Standalone TCOTFD Demesne visit — roll regional encounters, woo or fight demons, return via Flower Portal from Seaside.",
        ),
        AdventureDescriptor(
            id="ai-adventure",
            name="AI Adventure",
            source="ai",
            playable=False,
            notes="Build a copy-paste prompt for an external LLM, then import the returned JSON below.",
        ),
    ]
    adventures.extend(list_installed_adventures(settings.root_dir, settings.data_dir))
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


@app.get("/api/adventures/tiles")
async def adventure_tile_catalog() -> dict:
    return build_tile_catalog(rules)


@app.post("/api/adventures/ai/skeleton")
async def adventure_ai_skeleton(payload: AdventurePromptParameters) -> AdventureSkeletonResponse:
    try:
        skeleton = generate_adventure_skeleton(payload, repo=rules)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    check = {k: v for k, v in skeleton.items() if not str(k).startswith("_")}
    result = validate_adventure_manifest(check, rules_repo=rules)
    return AdventureSkeletonResponse(skeleton=skeleton, valid=result.valid, errors=result.errors)


@app.get("/api/adventures/allowlists")
async def adventure_allowlists(environment: str | None = None) -> dict:
    env = environment if environment in {"dungeon", "caverns", "fungal_grottoes"} else None
    return build_adventure_allowlists(rules, environment=env)


@app.get("/api/adventures/ai/defaults")
async def adventure_ai_defaults() -> dict:
    return adventure_prompt_defaults(rules)


@app.post("/api/adventures/ai/prompt")
async def adventure_ai_prompt(payload: AdventurePromptParameters) -> AdventurePromptResponse:
    try:
        prompt = build_adventure_prompt(payload, repo=rules)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AdventurePromptResponse(
        prompt=prompt,
        parameters=payload,
        room_count_hint=LENGTH_ROOM_HINTS[payload.length],
    )


@app.post("/api/adventures/validate")
async def validate_adventure(payload: dict) -> dict:
    manifest = payload.get("manifest", payload)
    if not isinstance(manifest, dict):
        raise HTTPException(status_code=400, detail="manifest must be a JSON object.")
    result = validate_adventure_manifest(manifest, rules_repo=rules)
    return {
        "valid": result.valid,
        "errors": result.errors,
        "error_summary": result.error_summary,
        "warnings": result.warnings,
        "warning_summary": result.warning_summary,
        "title": manifest.get("title"),
        "id": manifest.get("id"),
        "room_count": len(manifest.get("rooms", [])) if isinstance(manifest.get("rooms"), list) else 0,
        "quest_objective": (manifest.get("quest") or {}).get("objective_text"),
    }


@app.post("/api/adventures/import")
async def import_adventure(payload: dict) -> dict:
    manifest = payload.get("manifest", payload)
    if not isinstance(manifest, dict):
        raise HTTPException(status_code=400, detail="manifest must be a JSON object.")
    overwrite = bool(payload.get("overwrite", False))
    path, result = import_adventure_manifest(
        settings.root_dir,
        settings.data_dir,
        manifest,
        rules_repo=rules,
        overwrite=overwrite,
    )
    if not result.valid or path is None:
        raise HTTPException(status_code=400, detail="; ".join(result.errors) or "Import failed.")
    return {
        "adventure_id": manifest["id"],
        "title": manifest.get("title"),
        "path": str(path.relative_to(settings.data_dir)).replace("\\", "/"),
        "room_count": len(manifest.get("rooms", [])),
        "quest_objective": (manifest.get("quest") or {}).get("objective_text"),
        "warnings": result.warnings,
    }


@app.get("/api/adventures/{adventure_id}/export")
async def export_adventure(adventure_id: str) -> dict:
    if adventure_id in {"random", "ai-adventure", "courtship-demesne"}:
        raise HTTPException(status_code=404, detail="Adventure not found.")
    try:
        return load_installed_manifest(settings.root_dir, settings.data_dir, adventure_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"Could not read adventure manifest: {exc}") from exc


@app.get("/api/adventures/{adventure_id}/export.zip")
async def export_adventure_zip(adventure_id: str) -> Response:
    if adventure_id in {"random", "ai-adventure", "courtship-demesne"}:
        raise HTTPException(status_code=404, detail="Adventure not found.")
    try:
        payload = build_adventure_export_zip(settings.root_dir, settings.data_dir, adventure_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not build adventure export: {exc}") from exc
    filename = f"{adventure_id}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.delete("/api/adventures/{adventure_id}")
async def remove_adventure(adventure_id: str) -> dict:
    blocking = [
        session
        for session in store.list("sessions", SessionState.model_validate)
        if session.adventure_id == adventure_id and session.mode != "complete"
    ]
    if blocking:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Cannot remove {adventure_id!r}: {len(blocking)} game(s) in progress. "
                "End or complete those sessions first."
            ),
        )
    result = remove_installed_adventure(settings.root_dir, settings.data_dir, adventure_id)
    if not result.removed:
        status = 404 if "not installed" in (result.error or "").lower() else 400
        raise HTTPException(status_code=status, detail=result.error or "Remove failed.")
    message = f"Removed {adventure_id} from your installed adventures."
    if result.bundled_still_available:
        message += " A shipped default copy may still appear in the list; it will re-seed on restart if removed again."
    return {
        "deleted": True,
        "adventure_id": adventure_id,
        "bundled_still_available": result.bundled_still_available,
        "message": message,
    }


@app.post("/api/sessions")
async def create_session(payload: dict[str, Any]) -> SessionState:
    party_id = payload.get("party_id")
    adventure_id = payload.get("adventure_id", "random")
    if not party_id:
        raise HTTPException(status_code=400, detail="party_id is required.")
    if adventure_id == "ai-adventure":
        raise HTTPException(
            status_code=400,
            detail="AI Adventure prompt mode does not start a session. Import a module, then select it here to play.",
        )

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
    from .engine.experience import DEFAULT_UNLIMITED_MAP_ELEMENT_CAP, normalize_unlimited_map_element_cap

    unlimited_map_element_cap = normalize_unlimited_map_element_cap(
        payload.get("unlimited_map_element_cap", DEFAULT_UNLIMITED_MAP_ELEMENT_CAP)
    )
    fiendish_foes_enabled = payload.get("fiendish_foes_enabled", True)
    if "fiendish_foes_enabled" not in payload and "fiendish_foes_mode" in payload:
        from .engine.fiendish_foes import migrate_legacy_fiendish_foes_mode

        fiendish_foes_enabled = migrate_legacy_fiendish_foes_mode(payload.get("fiendish_foes_mode"))
    start_camped_outside = _parse_bool(payload.get("start_camped_outside"), default=False)
    ruleset_profile_id = payload.get("ruleset_profile_id")
    ruleset = payload.get("ruleset", "ee")
    courtship_enabled_raw = payload.get("courtship_enabled")
    courtship_enabled = (
        _parse_bool(courtship_enabled_raw)
        if courtship_enabled_raw is not None
        else None
    )
    from .engine.ruleset_profiles import resolve_profile_for_adventure
    from .engine.tag_campaign import load_campaign

    campaign = load_campaign(store)
    tag_banking_enabled = campaign.tag_banking_enabled
    profile = resolve_profile_for_adventure(
        adventure_id,
        profile_id=ruleset_profile_id,
        ruleset=ruleset if adventure_id == "random" else None,
        courtship_enabled=courtship_enabled if adventure_id == "random" else None,
    )
    if "fiendish_foes_enabled" not in payload and adventure_id == "random":
        fiendish_foes_enabled = profile.fiendish_foes_default
    members = [_member_state(character) for character in characters]

    if adventure_id == "courtship-demesne":
        try:
            session = random_engine.create_courtship_demesne_session(
                new_id(),
                party.id,
                members,
                xp_system=xp_system,
                map_bounds_mode=map_bounds_mode,
                unlimited_map_element_cap=unlimited_map_element_cap,
                tag_banking_enabled=tag_banking_enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    elif adventure_id != "random":
        try:
            manifest = load_installed_manifest(settings.root_dir, settings.data_dir, adventure_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=400, detail="Imported adventure not found. Import it first.") from exc
        session = create_session_from_manifest(
            random_engine,
            new_id(),
            party.id,
            members,
            manifest,
            adventure_id=adventure_id,
            xp_system=xp_system,
            map_bounds_mode=map_bounds_mode,
            unlimited_map_element_cap=unlimited_map_element_cap,
            fiendish_foes_enabled=fiendish_foes_enabled,
            start_camped_outside=start_camped_outside,
        )
    else:
        try:
            session = random_engine.create_session(
                new_id(),
                party.id,
                members,
                xp_system=xp_system,
                map_bounds_mode=map_bounds_mode,
                unlimited_map_element_cap=unlimited_map_element_cap,
                fiendish_foes_enabled=fiendish_foes_enabled,
                start_camped_outside=start_camped_outside,
                ruleset=profile.ruleset,
                courtship_enabled=profile.courtship_enabled,
                ruleset_profile_id=profile.id,
                tag_banking_enabled=tag_banking_enabled,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    from .engine.tag_campaign import apply_abyss_campaign_to_session

    session = apply_abyss_campaign_to_session(store, session)
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


@app.get("/api/sessions/summaries", response_model=list[SessionListSummary])
async def list_session_summaries() -> list[SessionListSummary]:
    reconcile_stale_character_locks(store)
    sessions = store.list("sessions", SessionState.model_validate)
    return [session_to_summary(session) for session in sessions]


@app.post("/api/maintenance/reconcile-locks")
async def reconcile_adventure_locks() -> dict[str, int]:
    """Clear character active_session_id when the linked session is missing or complete."""
    cleared = reconcile_stale_character_locks(store)
    return {"cleared": cleared}


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
        reaction_bribe_mode=payload.reaction_bribe_mode,
        subdual=payload.subdual,
        marching_order=payload.marching_order,
        alchemist_item=payload.alchemist_item,
        xp_spent=payload.xp_spent,
        target_character_id=payload.target_character_id,
        item_name=payload.item_name,
        target_weapon=payload.target_weapon,
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
        use_daring_escape=payload.use_daring_escape,
        panache_spend=payload.panache_spend,
        class_ability=payload.class_ability,
        nourishing_meal=payload.nourishing_meal,
        nourishing_meal_eaters=payload.nourishing_meal_eaters,
        everyone_eats=payload.everyone_eats,
        feed_character_ids=payload.feed_character_ids,
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
        glamour_mask_reroll=payload.glamour_mask_reroll,
        life_transfer_amount=payload.life_transfer_amount,
        teleport_tile_id=payload.teleport_tile_id,
        teleport_character_ids=payload.teleport_character_ids,
        mass_blessing_target_ids=payload.mass_blessing_target_ids,
        mass_blessing_condition_choices=payload.mass_blessing_condition_choices,
        dungeon_exit_intent=payload.dungeon_exit_intent,
        detached_character_ids=payload.detached_character_ids,
        detached_tile_id=payload.detached_tile_id,
        trap_boulder_origin=payload.trap_boulder_origin,
        trap_boulder_block_exit_id=payload.trap_boulder_block_exit_id,
        trap_snare_item_name=payload.trap_snare_item_name,
        madness_choice=payload.madness_choice,
        bodyguard_intercept_choice=payload.bodyguard_intercept_choice,
        acolyte_blessing_choice=payload.acolyte_blessing_choice,
        envenom_weapon_kind=payload.envenom_weapon_kind,
        fallen_transfer_kind=payload.fallen_transfer_kind,
        free_slaves_choice=payload.free_slaves_choice,
        paint_choice=payload.paint_choice,
        paint_direction=payload.paint_direction,
        paint_quantity=payload.paint_quantity,
        paint_item_key=payload.paint_item_key,
        wand_power_charges=payload.wand_power_charges,
        use_prayer_bead=payload.use_prayer_bead,
        treasure_outcome_choice=payload.treasure_outcome_choice,
        fd_revelation_choice=payload.fd_revelation_choice,
        fd_secret_passage_destination=payload.fd_secret_passage_destination,
        fd_portal_destination=payload.fd_portal_destination,
        fd_cairn_natural_one_choice=payload.fd_cairn_natural_one_choice,
        fd_quest_reward_choice=payload.fd_quest_reward_choice,
        fd_quest_from_treasure=payload.fd_quest_from_treasure,
        fd_quest_id=payload.fd_quest_id,
        courtship_region=payload.courtship_region,
        courtship_encounter_shift=payload.courtship_encounter_shift,
        courtship_choice=payload.courtship_choice,
        abyss_plot_choice=payload.abyss_plot_choice,
        courtship_dominant_stance=payload.courtship_dominant_stance,
        courtship_passionate_stance=payload.courtship_passionate_stance,
        courtship_use_luck=payload.courtship_use_luck,
        fd_idol_choice=payload.fd_idol_choice,
        milestone_id=payload.milestone_id,
        scroll_librarian_spell=payload.scroll_librarian_spell,
        panoplia_favor_kind=payload.panoplia_favor_kind,
        hireling_id=payload.hireling_id,
        retainer_type=payload.retainer_type,
        professional_id=payload.professional_id,
        trained_professional_skill=payload.trained_professional_skill,
        professional_provider_id=payload.professional_provider_id,
        hireling_marching_order=payload.hireling_marching_order,
        hireling_ability=payload.hireling_ability,
        fortune_roll_value=payload.fortune_roll_value,
        alchemist_potion_id=payload.alchemist_potion_id,
    )
    _restore_missing_recovery_members(session)
    from .engine.tag_campaign import sync_abyss_campaign_from_session

    sync_abyss_campaign_from_session(store, session)
    if payload.action == "set_marching_order":
        _sync_party_marching_order(session)
    if payload.action in {"transfer_gold", "transfer_item"} and payload.character_id and payload.target_character_id:
        sync_party_members_to_roster(
            session,
            store,
            {payload.character_id, payload.target_character_id},
        )
    if session.mode == "complete":
        from .engine.tag_campaign import record_adventure_complete

        record_adventure_complete(store)
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


def _parse_bool(value: object, *, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    if value is None:
        return default
    return bool(value)


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
        madness=character.madness,
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
        milestones=character.milestones.model_copy(deep=True),
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
    character.milestones = member.milestones.model_copy(deep=True)
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
