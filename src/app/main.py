from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
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
from .engine.adventure_pdf_sources import (
    adventure_pdf_source_dirs,
    load_adventure_pdf_assessments,
    scan_new_adventure_pdfs,
)
from .engine.adventure_packages import (
    create_or_refresh_package_from_pdf,
    delete_adventure_package,
    delete_map_pin,
    extract_adventure_package_artwork,
    extract_adventure_package_candidates,
    list_adventure_packages,
    package_detail,
    package_artwork_asset_path,
    package_map_asset_path,
    update_adventure_package_review,
    upsert_map_pin,
)
from .engine.adventure_allowlists import build_adventure_allowlists
from .engine.adventure_foes import spawn_manifest_foes
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
from .engine.tag_compat import generated_tag_manifest_diagnostics, normalize_tag_log_lines, upgrade_tag_manifest
from .engine.tag_campaign import merge_tag_pdf_narrative_overrides, tag_narrative_overrides_path
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
    AppPreferences,
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
    WorldCampaignRecord,
    WorldGuildRecord,
    WorldSettlementRecord,
    WorldTroupeRecord,
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
    normalize_tag_log_lines(session.log)
    if isinstance(session.imported_manifest, dict):
        session.imported_manifest = upgrade_tag_manifest(session.imported_manifest)
    tile = random_engine._current_tile(session)
    active_tag_state = (
        dict(session.active_quest.tag_generated_lead_state or {})
        if session.active_quest is not None
        else {}
    )
    session.generated_tag_diagnostics = generated_tag_manifest_diagnostics(
        session.imported_manifest,
        current_room_id=_imported_room_id_for_tile(session, tile),
        active_quest_state=active_tag_state,
    )
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


def _imported_room_id_for_tile(session: SessionState, tile: TileState | None) -> str:
    if tile is None:
        return ""
    content_key = str(tile.content_key or "")
    if content_key.startswith("imported:"):
        return content_key.removeprefix("imported:")
    if content_key == "entrance" and isinstance(session.imported_manifest, dict):
        return str(session.imported_manifest.get("entrance_room_id") or "")
    return ""


def _refresh_generated_tag_manifest_on_resume(session: SessionState) -> bool:
    if not _is_generated_tag_session(session) or not isinstance(session.imported_manifest, dict):
        return False
    before = repr(session.imported_manifest)
    session.imported_manifest = upgrade_tag_manifest(session.imported_manifest)
    changed = repr(session.imported_manifest) != before
    log_changed = normalize_tag_log_lines(session.log)
    changed = changed or log_changed
    if session.active_quest is not None:
        state = dict(session.active_quest.tag_generated_lead_state or {})
        if changed:
            tag_ref = ((session.imported_manifest.get("source") or {}).get("parameters") or {}).get("tag_reference") or {}
            fields = tag_ref.get("local_narrative_override_changed_fields") if isinstance(tag_ref, dict) else []
            summary = [str(field) for field in fields[:8]] if isinstance(fields, list) else []
            state["auto_refreshed_at"] = now_utc()
            state["repair_summary"] = summary or ["Generated Adventures Guild narrative and prompt metadata refreshed on resume."]
            state["next_action"] = "Continue from Current Objective; use visible scene buttons first and manual actions only if diagnostics ask for them."
            session.active_quest.tag_generated_lead_state = state
        elif "auto_refresh_checked_at" not in state:
            state["auto_refresh_checked_at"] = now_utc()
            session.active_quest.tag_generated_lead_state = state
    return changed


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
        active_supplement_ids=list(session.active_supplement_ids),
        supplement_registry_version=session.supplement_registry_version,
        state_registry_version=session.state_registry_version,
        terrain_registry_version=session.terrain_registry_version,
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
RULE_PDF_EXTENSIONS = {".pdf"}


app = FastAPI(title="Ahazi Against Darkness", version="0.26.0")
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
app.mount("/docs", StaticFiles(directory=settings.root_dir / "docs"), name="docs")
app.mount("/Rules", StaticFiles(directory=settings.root_dir / "Rules", check_dir=False), name="rules-pdfs")


def _safe_relative_asset_path(asset_path: str) -> Path:
    candidate = Path(asset_path)
    if candidate.is_absolute() or any(part in {"", ".", ".."} for part in candidate.parts):
        raise HTTPException(status_code=404, detail="Asset not found.")
    return candidate


def _resolve_asset_file(asset_path: str) -> tuple[Path, str] | tuple[None, None]:
    relative = _safe_relative_asset_path(asset_path)
    for root, source in (
        (settings.user_assets_dir, "user"),
        (settings.packaged_assets_dir, "bundled"),
    ):
        base = root.resolve()
        resolved = (base / relative).resolve()
        if not resolved.is_relative_to(base):
            continue
        if resolved.is_file():
            return resolved, source
    return None, None


def _asset_exists(asset_path: str) -> bool:
    resolved, _source = _resolve_asset_file(asset_path)
    return resolved is not None


def _safe_rule_pdf_filename(filename: str) -> str:
    name = Path(filename or "").name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Missing PDF filename.")
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", Path(name).stem).strip(" ._")
    if not stem:
        stem = "uploaded_rules"
    return f"{stem[:120]}.pdf"


def _resolve_user_rule_pdf(filename: str) -> Path:
    safe = _safe_rule_pdf_filename(filename)
    base = settings.rules_dir.resolve()
    resolved = (base / safe).resolve()
    if not resolved.is_relative_to(base):
        raise HTTPException(status_code=400, detail="Invalid PDF path.")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Uploaded rule PDF not found.")
    return resolved


def _tag_narrative_override_status() -> dict[str, Any]:
    path = tag_narrative_overrides_path()
    status: dict[str, Any] = {
        "path": str(path),
        "exists": path.exists(),
        "modified_at": "",
        "rumors": 0,
        "scenes": 0,
        "scene_branches": 0,
        "extraction_warnings": [],
        "schema_version": 0,
        "note": "",
        "error": "",
    }
    if not path.exists():
        return status
    try:
        from datetime import datetime, timezone

        stat = path.stat()
        status["modified_at"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z")
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        status["error"] = str(exc)
        return status
    tag = data.get("tag") if isinstance(data, dict) else {}
    rumor = tag.get("rumor") if isinstance(tag, dict) else {}
    scene = tag.get("scene") if isinstance(tag, dict) else {}
    extraction_warnings = tag.get("last_extraction_warnings") if isinstance(tag, dict) else []
    status["schema_version"] = data.get("schema_version", 0) if isinstance(data, dict) else 0
    status["note"] = str(data.get("note") or "") if isinstance(data, dict) else ""
    status["rumors"] = len(rumor) if isinstance(rumor, dict) else 0
    status["scenes"] = len(scene) if isinstance(scene, dict) else 0
    status["extraction_warnings"] = extraction_warnings if isinstance(extraction_warnings, list) else []
    if isinstance(scene, dict):
        status["scene_branches"] = sum(
            len(item.get("branches") or [])
            for item in scene.values()
            if isinstance(item, dict) and isinstance(item.get("branches"), list)
        )
    return status


@app.get("/assets/{asset_path:path}")
async def serve_asset(asset_path: str) -> FileResponse:
    resolved, _source = _resolve_asset_file(asset_path)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Asset not found.")
    return FileResponse(resolved)


@app.get("/api/rules/pdfs")
async def list_rule_pdfs() -> dict[str, Any]:
    settings.rules_dir.mkdir(parents=True, exist_ok=True)
    uploaded = [
        {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "source": "DATA_DIR/rules",
        }
        for path in sorted(settings.rules_dir.glob("*.pdf"))
        if path.is_file()
    ]
    packaged = [
        {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "source": "Rules",
        }
        for path in sorted((settings.root_dir / "Rules").glob("*.pdf"))
        if path.is_file()
    ]
    return {
        "uploaded": uploaded,
        "packaged": packaged,
        "rules_dir": str(settings.rules_dir),
        "override_path": str(tag_narrative_overrides_path()),
        "override_status": _tag_narrative_override_status(),
    }


@app.post("/api/rules/upload-pdf")
async def upload_rule_pdf(request: Request) -> dict[str, Any]:
    raw_filename = request.query_params.get("filename") or request.headers.get("x-filename") or "rules.pdf"
    if Path(raw_filename).suffix.lower() not in RULE_PDF_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Upload a .pdf file.")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty.")
    filename = _safe_rule_pdf_filename(raw_filename)
    settings.rules_dir.mkdir(parents=True, exist_ok=True)
    target = (settings.rules_dir / filename).resolve()
    if not target.is_relative_to(settings.rules_dir.resolve()):
        raise HTTPException(status_code=400, detail="Invalid PDF target.")
    target.write_bytes(body)
    return {
        "filename": filename,
        "size_bytes": target.stat().st_size,
        "rules_dir": str(settings.rules_dir),
        "message": f"Uploaded {filename} to DATA_DIR/rules.",
    }


@app.post("/api/rules/extract-tag-narrative")
async def extract_tag_narrative(payload: dict[str, Any]) -> dict[str, Any]:
    filename = str(payload.get("filename") or "").strip()
    overwrite = bool(payload.get("overwrite"))
    if not filename:
        candidates = sorted(settings.rules_dir.glob("*Tales*Adventurers*Guild*.pdf")) or sorted(settings.rules_dir.glob("*.pdf"))
        if not candidates:
            raise HTTPException(status_code=404, detail="Upload Tales_from_the_adventurers_guild.pdf first.")
        pdf_path = candidates[0]
    else:
        pdf_path = _resolve_user_rule_pdf(filename)
    try:
        result = merge_tag_pdf_narrative_overrides(pdf_path, overwrite=overwrite)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Could not extract TAG narrative: {exc}") from exc
    return {
        **result,
        "overwrite": overwrite,
        "override_status": _tag_narrative_override_status(),
        "message": f"Extracted TAG narrative from {pdf_path.name} into DATA_DIR/{tag_narrative_overrides_path().name}.",
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    if not request.query_params.get("session") and request.query_params.get("view") != "game":
        return RedirectResponse(url="/modern", status_code=307)
    return HTMLResponse(
        (settings.static_dir / "index.html").read_text(encoding="utf-8"),
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/legacy", response_class=HTMLResponse)
async def legacy_index() -> HTMLResponse:
    return HTMLResponse(
        (settings.static_dir / "index.html").read_text(encoding="utf-8"),
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.get("/modern", response_class=HTMLResponse)
@app.get("/modern/{page_name}", response_class=HTMLResponse)
async def modern_home(page_name: str = "home") -> HTMLResponse:
    return HTMLResponse(
        (settings.static_dir / "modern.html").read_text(encoding="utf-8"),
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


@app.get("/api/supplements")
async def list_supplements() -> dict[str, Any]:
    from .engine.supplements import supplement_payload

    return supplement_payload()


@app.get("/api/states")
async def list_states() -> dict[str, Any]:
    from .engine.states import state_payload

    return state_payload()


@app.get("/api/terrain")
async def list_terrain() -> dict[str, Any]:
    from .engine.terrain_registry import terrain_payload

    return terrain_payload()


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


def _load_app_preferences() -> AppPreferences:
    return store.get("preferences", "ui", AppPreferences.model_validate) or AppPreferences()


@app.get("/api/preferences")
async def get_preferences() -> AppPreferences:
    return _load_app_preferences()


@app.put("/api/preferences")
async def update_preferences(payload: dict[str, Any]) -> AppPreferences:
    prefs = _load_app_preferences()
    if "show_tag_fixed_result_selector" in payload:
        prefs.show_tag_fixed_result_selector = _parse_bool(payload.get("show_tag_fixed_result_selector"))
    store.save("preferences", prefs)
    return prefs


@app.put("/api/campaign")
async def update_campaign(payload: dict[str, Any]) -> CampaignState:
    from .engine.tag_campaign import load_campaign, save_campaign, update_settlement

    campaign = load_campaign(store)
    if "tag_banking_enabled" in payload:
        campaign.tag_banking_enabled = _parse_bool(payload.get("tag_banking_enabled"))
    if "world_map_notes" in payload:
        campaign.world_map_notes = str(payload.get("world_map_notes") or "").strip()[:4000]
    update_settlement(
        campaign,
        name=payload.get("settlement_name") if "settlement_name" in payload else None,
        size=payload.get("settlement_size") if "settlement_size" in payload else None,
        notes=payload.get("settlement_notes") if "settlement_notes" in payload else None,
    )
    return save_campaign(store, campaign)


def _world_name(payload: dict[str, Any], default: str = "") -> str:
    return str(payload.get("name") or default).strip()[:100]


def _world_description(payload: dict[str, Any]) -> str:
    return str(payload.get("description") or payload.get("notes") or "").strip()[:2000]


def _party_name(party_id: str) -> str:
    party = store.get("parties", party_id, Party.model_validate)
    return party.name if party else party_id


def _remove_character_from_party(character: Character, *, reason: str) -> str:
    if not character.party_id:
        return ""
    party = store.get("parties", character.party_id, Party.model_validate)
    if party is None or character.id not in party.character_ids:
        character.party_id = None
        return ""
    old_name = party.name
    party.character_ids = [item for item in party.character_ids if item != character.id]
    party.updated_at = now_utc()
    store.save("parties", party)
    character.party_id = None
    return f"{character.name} was removed from {old_name}: {reason}"


def _world_record_exists(rows: list[Any], record_id: str) -> bool:
    return bool(record_id and any(item.id == record_id for item in rows))


def _world_troupe(campaign: CampaignState, troupe_id: str) -> WorldTroupeRecord | None:
    return next((item for item in campaign.world_troupes if item.id == troupe_id), None)


def _world_guild(campaign: CampaignState, guild_id: str) -> WorldGuildRecord | None:
    return next((item for item in campaign.world_guilds if item.id == guild_id), None)


def _world_settlement(campaign: CampaignState, settlement_id: str) -> WorldSettlementRecord | None:
    return next((item for item in campaign.world_settlements if item.id == settlement_id), None)


def _sync_troupe_assignments(campaign: CampaignState, troupe: WorldTroupeRecord, *, timestamp: str) -> None:
    for party in store.list("parties", Party.model_validate):
        if party.troupe_id != troupe.id:
            continue
        party.campaign_id = troupe.campaign_id
        party.updated_at = timestamp
        store.save("parties", party)
        for character_id in party.character_ids:
            if character_id not in troupe.member_character_ids:
                troupe.member_character_ids.append(character_id)
    for character in store.list("characters", Character.model_validate):
        if character.troupe_id != troupe.id:
            continue
        character.campaign_id = troupe.campaign_id
        character.guild_id = troupe.guild_id
        character.updated_at = timestamp
        store.save("characters", character)


def _sync_guild_assignments(campaign: CampaignState, guild: WorldGuildRecord, *, timestamp: str) -> None:
    for troupe in campaign.world_troupes:
        if troupe.guild_id == guild.id:
            troupe.campaign_id = guild.campaign_id
            _sync_troupe_assignments(campaign, troupe, timestamp=timestamp)


def _campaign_record_name(rows: list[Any], record_id: str | None, fallback: str = "Unassigned") -> str:
    return next((item.name for item in rows if item.id == record_id), fallback)


def _character_equipment_warnings(character: Character) -> list[str]:
    inventory = [str(item) for item in character.inventory]
    weapon_pattern = ("weapon", "sword", "dagger", "axe", "mace", "spear", "scimitar", "club", "hammer", "staff", "bow", "sling", "crossbow", "javelin")
    missile_pattern = ("bow", "sling", "crossbow", "javelin", "arrow", "missile")
    weapons = [item for item in inventory if any(token in item.lower() for token in weapon_pattern)]
    melee = [item for item in weapons if not any(token in item.lower() for token in missile_pattern)]
    missile = [item for item in weapons if any(token in item.lower() for token in missile_pattern)]
    warnings: list[str] = []
    if not melee:
        warnings.append("No melee weapon detected in inventory.")
    if melee and not character.default_melee_weapon:
        warnings.append("Melee slot is not assigned.")
    if missile and not character.default_missile_weapon:
        warnings.append("Missile weapon carried but missile slot is not assigned.")
    for field, label in [
        ("default_melee_weapon", "Assigned melee weapon"),
        ("default_melee_weapon_secondary", "Assigned off-hand weapon"),
        ("default_missile_weapon", "Assigned missile weapon"),
    ]:
        value = getattr(character, field, None)
        if value and value not in inventory:
            warnings.append(f"{label} is no longer in inventory.")
    return warnings


def _character_context_warnings(campaign: CampaignState, character: Character, party: Party | None = None) -> list[str]:
    warnings: list[str] = []
    troupe = _world_troupe(campaign, character.troupe_id or "")
    if party and party.troupe_id and character.troupe_id and party.troupe_id != character.troupe_id:
        warnings.append(
            f"Party {party.name} belongs to {_campaign_record_name(campaign.world_troupes, party.troupe_id)}, "
            f"but {character.name} points to {_campaign_record_name(campaign.world_troupes, character.troupe_id)}."
        )
    if party and party.campaign_id and character.campaign_id and party.campaign_id != character.campaign_id:
        warnings.append(
            f"Party campaign {_campaign_record_name(campaign.world_campaigns, party.campaign_id)} differs from "
            f"{character.name}'s campaign {_campaign_record_name(campaign.world_campaigns, character.campaign_id)}."
        )
    if troupe and troupe.campaign_id and character.campaign_id and troupe.campaign_id != character.campaign_id:
        warnings.append(
            f"Troupe campaign {_campaign_record_name(campaign.world_campaigns, troupe.campaign_id)} differs from "
            f"{character.name}'s campaign {_campaign_record_name(campaign.world_campaigns, character.campaign_id)}."
        )
    if troupe and troupe.guild_id and character.guild_id and troupe.guild_id != character.guild_id:
        warnings.append(
            f"Troupe guild {_campaign_record_name(campaign.world_guilds, troupe.guild_id)} differs from "
            f"{character.name}'s guild {_campaign_record_name(campaign.world_guilds, character.guild_id)}."
        )
    if not character.party_id:
        warnings.append(f"{character.name} has no saved party assignment.")
    if not character.troupe_id:
        warnings.append(f"{character.name} has no troupe assignment.")
    if not character.guild_id:
        warnings.append(f"{character.name} has no guild assignment.")
    if not character.campaign_id:
        warnings.append(f"{character.name} has no campaign assignment.")
    return warnings


def campaign_closeout_gate(campaign: CampaignState, party_id: str | None = None) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    party = store.get("parties", party_id, Party.model_validate) if party_id else None
    if not party_id:
        issues.append({"code": "party_required", "severity": "block", "title": "Choose party", "body": "Pick a saved party before starting a new adventure."})
    elif party is None:
        issues.append({"code": "party_missing", "severity": "block", "title": "Party not found", "body": f"No saved party matched {party_id}."})
    if party is not None:
        members = [store.get("characters", character_id, Character.model_validate) for character_id in party.character_ids]
        characters = [character for character in members if character is not None]
        if len(characters) != 4:
            issues.append({"code": "party_size", "severity": "block", "title": "Party size", "body": f"{party.name} has {len(characters)}/4 available member(s)."})
        fallen = [character.name for character in characters if character.current_life <= 0]
        if fallen:
            issues.append({"code": "fallen_members", "severity": "block", "title": "Fallen members", "body": ", ".join(fallen)})
        locked = [character.name for character in characters if character_busy_session_id(character, store)]
        if locked:
            issues.append({"code": "active_locks", "severity": "block", "title": "Active locks", "body": f"Already in an active adventure: {', '.join(locked)}."})
        injured = [f"{character.name} {character.current_life}/{character.max_life}" for character in characters if 0 < character.current_life < character.max_life]
        if injured:
            issues.append({"code": "injured_members", "severity": "warn", "title": "Injured members", "body": ", ".join(injured)})
        equipment = [f"{character.name}: {' '.join(_character_equipment_warnings(character))}" for character in characters if _character_equipment_warnings(character)]
        if equipment:
            issues.append({"code": "equipment_warnings", "severity": "warn", "title": "Equipment warnings", "body": " ".join(equipment)})
        context = [warning for character in characters for warning in _character_context_warnings(campaign, character, party)]
        if context:
            issues.append({"code": "context_warnings", "severity": "warn", "title": "Context warnings", "body": " ".join(context)})
    open_required = [task for task in campaign.guidance_tasks if task.status == "open" and task.priority == "required"]
    if open_required:
        issues.append({
            "code": "required_guidance",
            "severity": "override",
            "title": "Required guidance open",
            "body": f"{len(open_required)} required guidance task(s) remain open: {', '.join(task.title for task in open_required[:4])}.",
        })
    unresolved_closeout = [task for task in campaign.tag_closeout_tasks if not task.resolved]
    if unresolved_closeout:
        issues.append({
            "code": "unresolved_closeout",
            "severity": "override",
            "title": "Unresolved closeout",
            "body": f"{len(unresolved_closeout)} TAG closeout prompt(s) remain unresolved.",
        })
    return {
        "party_id": party_id,
        "can_start": not any(issue["severity"] == "block" for issue in issues),
        "requires_override": any(issue["severity"] == "override" for issue in issues),
        "issues": issues,
    }


def campaign_command_center_payload(campaign: CampaignState, campaign_id: str | None = None) -> dict[str, Any]:
    active_id = campaign_id or campaign.active_world_campaign_id
    selected = next((item for item in campaign.world_campaigns if item.id == active_id), None)
    parties = store.list("parties", Party.model_validate)
    campaign_parties = [item for item in parties if item.campaign_id == active_id]
    campaign_party_ids = {item.id for item in campaign_parties}
    characters = store.list("characters", Character.model_validate)
    sessions = store.list("sessions", SessionState.model_validate)
    return {
        "campaign_id": active_id,
        "campaign_name": selected.name if selected else "Unassigned",
        "campaign": selected.model_dump() if selected else None,
        "guilds": [item for item in campaign.world_guilds if item.campaign_id == active_id],
        "troupes": [item for item in campaign.world_troupes if item.campaign_id == active_id],
        "settlements": [item for item in campaign.world_settlements if item.campaign_id == active_id],
        "troublesome_towns": [item for item in campaign.world_troublesome_towns if item.campaign_id == active_id],
        "parties": campaign_parties,
        "characters": [item for item in characters if item.campaign_id == active_id],
        "active_sessions": [item for item in sessions if item.mode != "complete" and item.party_id in campaign_party_ids],
        "open_guidance": [item for item in campaign.guidance_tasks if item.status == "open"],
        "unresolved_closeout": [item for item in campaign.tag_closeout_tasks if not item.resolved],
        "recent_chronicle": list(reversed(campaign.campaign_chronicle[-12:])),
    }


@app.post("/api/campaign/world")
async def campaign_world_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import (
        DEFAULT_WORLD_CAMPAIGN_ID,
        DEFAULT_WORLD_CAMPAIGN_NAME,
        DEFAULT_WORLD_GUILD_ID,
        DEFAULT_WORLD_GUILD_NAME,
        DEFAULT_WORLD_SETTLEMENT_ID,
        DEFAULT_WORLD_SETTLEMENT_NAME,
        DEFAULT_WORLD_TROUPE_ID,
        DEFAULT_WORLD_TROUPE_NAME,
        load_campaign,
        save_campaign,
    )

    campaign = load_campaign(store)
    action = str(payload.get("action") or "").strip()
    entity = str(payload.get("entity") or "").strip()
    timestamp = now_utc()
    messages: list[str] = []

    if action == "create" and entity == "campaign":
        record = WorldCampaignRecord(name=_world_name(payload, "New Campaign"), description=_world_description(payload), created_at=timestamp)
        campaign.world_campaigns.append(record)
        campaign.active_world_campaign_id = record.id
    elif action == "update" and entity == "campaign":
        record_id = str(payload.get("id") or "")
        for record in campaign.world_campaigns:
            if record.id == record_id:
                record.name = DEFAULT_WORLD_CAMPAIGN_NAME if record.id == DEFAULT_WORLD_CAMPAIGN_ID else _world_name(payload, record.name)
                record.description = _world_description(payload)
                break
        else:
            raise HTTPException(status_code=404, detail="Campaign not found.")
    elif action == "delete" and entity == "campaign":
        record_id = str(payload.get("id") or "")
        if record_id == DEFAULT_WORLD_CAMPAIGN_ID:
            raise HTTPException(status_code=400, detail="The default Norindaal campaign cannot be deleted.")
        campaign.world_campaigns = [item for item in campaign.world_campaigns if item.id != record_id]
        for collection in [campaign.world_guilds, campaign.world_troupes, campaign.world_settlements, campaign.world_troublesome_towns]:
            for item in collection:
                if item.campaign_id == record_id:
                    item.campaign_id = None
        if campaign.active_world_campaign_id == record_id:
            campaign.active_world_campaign_id = DEFAULT_WORLD_CAMPAIGN_ID
    elif action == "select" and entity == "campaign":
        record_id = str(payload.get("id") or "")
        if not any(item.id == record_id for item in campaign.world_campaigns):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        campaign.active_world_campaign_id = record_id
    elif action == "create" and entity == "guild":
        campaign_id = str(payload.get("campaign_id") or campaign.active_world_campaign_id or DEFAULT_WORLD_CAMPAIGN_ID)
        if not _world_record_exists(campaign.world_campaigns, campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if any(item.campaign_id == campaign_id for item in campaign.world_guilds):
            raise HTTPException(status_code=400, detail="A campaign may have only one assigned guild.")
        record = WorldGuildRecord(name=_world_name(payload, "New Guild"), campaign_id=campaign_id, description=_world_description(payload), created_at=timestamp)
        campaign.world_guilds.append(record)
        for world in campaign.world_campaigns:
            if world.id == campaign_id:
                world.guild_id = record.id
    elif action == "update" and entity == "guild":
        guild_id = str(payload.get("guild_id") or payload.get("id") or "")
        campaign_id = str(payload.get("campaign_id") or "")
        if campaign_id and not _world_record_exists(campaign.world_campaigns, campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if campaign_id and any(item.id != guild_id and item.campaign_id == campaign_id for item in campaign.world_guilds):
            raise HTTPException(status_code=400, detail="A campaign may have only one assigned guild.")
        for guild in campaign.world_guilds:
            if guild.id == guild_id:
                guild.name = DEFAULT_WORLD_GUILD_NAME if guild.id == DEFAULT_WORLD_GUILD_ID else _world_name(payload, guild.name)
                guild.description = _world_description(payload)
                if campaign_id:
                    guild.campaign_id = campaign_id
                for world in campaign.world_campaigns:
                    if world.id == guild.campaign_id:
                        world.guild_id = guild.id
                    elif world.guild_id == guild.id:
                        world.guild_id = None
                _sync_guild_assignments(campaign, guild, timestamp=timestamp)
                break
        else:
            raise HTTPException(status_code=404, detail="Guild not found.")
    elif action == "delete" and entity == "guild":
        record_id = str(payload.get("id") or "")
        if record_id == DEFAULT_WORLD_GUILD_ID:
            raise HTTPException(status_code=400, detail="The default Adventurers Guild cannot be deleted.")
        campaign.world_guilds = [item for item in campaign.world_guilds if item.id != record_id]
        for world in campaign.world_campaigns:
            if world.guild_id == record_id:
                world.guild_id = None
        for troupe in campaign.world_troupes:
            if troupe.guild_id == record_id:
                troupe.guild_id = None
    elif action == "assign" and entity == "guild":
        guild_id = str(payload.get("guild_id") or payload.get("id") or "")
        campaign_id = str(payload.get("campaign_id") or campaign.active_world_campaign_id or DEFAULT_WORLD_CAMPAIGN_ID)
        if not _world_record_exists(campaign.world_campaigns, campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if any(item.id != guild_id and item.campaign_id == campaign_id for item in campaign.world_guilds):
            raise HTTPException(status_code=400, detail="A campaign may have only one assigned guild.")
        for guild in campaign.world_guilds:
            if guild.id == guild_id:
                guild.campaign_id = campaign_id
                _sync_guild_assignments(campaign, guild, timestamp=timestamp)
                break
        else:
            raise HTTPException(status_code=404, detail="Guild not found.")
        for world in campaign.world_campaigns:
            if world.id == campaign_id:
                world.guild_id = guild_id
            elif world.guild_id == guild_id:
                world.guild_id = None
    elif action == "create" and entity == "troupe":
        campaign_id = str(payload.get("campaign_id") or campaign.active_world_campaign_id or DEFAULT_WORLD_CAMPAIGN_ID)
        guild_id = str(payload.get("guild_id") or DEFAULT_WORLD_GUILD_ID)
        home_settlement_id = str(payload.get("home_settlement_id") or DEFAULT_WORLD_SETTLEMENT_ID)
        if not _world_record_exists(campaign.world_campaigns, campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if not _world_record_exists(campaign.world_guilds, guild_id):
            raise HTTPException(status_code=404, detail="Guild not found.")
        if not _world_record_exists(campaign.world_settlements, home_settlement_id):
            raise HTTPException(status_code=404, detail="Settlement not found.")
        record = WorldTroupeRecord(
            name=_world_name(payload, "New Troupe"),
            campaign_id=campaign_id,
            guild_id=guild_id,
            home_settlement_id=home_settlement_id,
            description=_world_description(payload),
            created_at=timestamp,
        )
        campaign.world_troupes.append(record)
    elif action == "update" and entity == "troupe":
        troupe_id = str(payload.get("troupe_id") or payload.get("id") or "")
        for troupe in campaign.world_troupes:
            if troupe.id == troupe_id:
                troupe.name = DEFAULT_WORLD_TROUPE_NAME if troupe.id == DEFAULT_WORLD_TROUPE_ID else _world_name(payload, troupe.name)
                troupe.description = _world_description(payload)
                if payload.get("campaign_id"):
                    campaign_id = str(payload.get("campaign_id"))
                    if not _world_record_exists(campaign.world_campaigns, campaign_id):
                        raise HTTPException(status_code=404, detail="Campaign not found.")
                    troupe.campaign_id = campaign_id
                if payload.get("guild_id"):
                    guild_id = str(payload.get("guild_id"))
                    guild = _world_guild(campaign, guild_id)
                    if guild is None:
                        raise HTTPException(status_code=404, detail="Guild not found.")
                    if guild.campaign_id and troupe.campaign_id and guild.campaign_id != troupe.campaign_id:
                        raise HTTPException(status_code=400, detail="Troupe guild must belong to the same campaign.")
                    troupe.guild_id = guild_id
                if payload.get("home_settlement_id"):
                    settlement_id = str(payload.get("home_settlement_id"))
                    settlement = _world_settlement(campaign, settlement_id)
                    if settlement is None:
                        raise HTTPException(status_code=404, detail="Settlement not found.")
                    if settlement.campaign_id and troupe.campaign_id and settlement.campaign_id != troupe.campaign_id:
                        raise HTTPException(status_code=400, detail="Troupe home settlement must belong to the same campaign.")
                    troupe.home_settlement_id = settlement_id
                _sync_troupe_assignments(campaign, troupe, timestamp=timestamp)
                break
        else:
            raise HTTPException(status_code=404, detail="Troupe not found.")
    elif action == "delete" and entity == "troupe":
        record_id = str(payload.get("id") or "")
        if record_id == DEFAULT_WORLD_TROUPE_ID:
            raise HTTPException(status_code=400, detail="The default Troupe1 cannot be deleted.")
        campaign.world_troupes = [item for item in campaign.world_troupes if item.id != record_id]
        for party in store.list("parties", Party.model_validate):
            if party.troupe_id == record_id:
                party.troupe_id = None
                party.updated_at = timestamp
                store.save("parties", party)
        for character in store.list("characters", Character.model_validate):
            if character.troupe_id == record_id:
                character.troupe_id = None
                character.updated_at = timestamp
                store.save("characters", character)
    elif action == "assign" and entity == "troupe":
        troupe_id = str(payload.get("troupe_id") or payload.get("id") or "")
        campaign_id = str(payload.get("campaign_id") or campaign.active_world_campaign_id or DEFAULT_WORLD_CAMPAIGN_ID)
        if not _world_record_exists(campaign.world_campaigns, campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        for troupe in campaign.world_troupes:
            if troupe.id == troupe_id:
                troupe.campaign_id = campaign_id
                _sync_troupe_assignments(campaign, troupe, timestamp=timestamp)
                break
        else:
            raise HTTPException(status_code=404, detail="Troupe not found.")
    elif action == "create" and entity in {"settlement", "troublesome_town"}:
        record = WorldSettlementRecord(
            name=_world_name(payload, "New Settlement"),
            campaign_id=str(payload.get("campaign_id") or campaign.active_world_campaign_id or DEFAULT_WORLD_CAMPAIGN_ID),
            kind="troublesome" if entity == "troublesome_town" else "friendly",
            size=int(payload.get("size") or 0),
            notes=_world_description(payload),
            created_at=timestamp,
        )
        if record.campaign_id and not _world_record_exists(campaign.world_campaigns, record.campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        if record.kind == "troublesome":
            campaign.world_troublesome_towns.append(record)
        else:
            campaign.world_settlements.append(record)
    elif action == "update" and entity in {"settlement", "troublesome_town"}:
        record_id = str(payload.get("settlement_id") or payload.get("id") or "")
        collections = [campaign.world_troublesome_towns] if entity == "troublesome_town" else [campaign.world_settlements]
        for collection in collections:
            for record in collection:
                if record.id == record_id:
                    record.name = DEFAULT_WORLD_SETTLEMENT_NAME if record.id == DEFAULT_WORLD_SETTLEMENT_ID else _world_name(payload, record.name)
                    if payload.get("campaign_id"):
                        campaign_id = str(payload.get("campaign_id"))
                        if not _world_record_exists(campaign.world_campaigns, campaign_id):
                            raise HTTPException(status_code=404, detail="Campaign not found.")
                        record.campaign_id = campaign_id
                    record.size = int(payload.get("size") or 0)
                    record.notes = _world_description(payload)
                    for troupe in campaign.world_troupes:
                        if troupe.home_settlement_id == record.id:
                            _sync_troupe_assignments(campaign, troupe, timestamp=timestamp)
                    break
            else:
                continue
            break
        else:
            raise HTTPException(status_code=404, detail="Settlement not found.")
    elif action == "delete" and entity in {"settlement", "troublesome_town"}:
        record_id = str(payload.get("id") or "")
        if record_id == DEFAULT_WORLD_SETTLEMENT_ID:
            raise HTTPException(status_code=400, detail="The default Hearthmere settlement cannot be deleted.")
        campaign.world_settlements = [item for item in campaign.world_settlements if item.id != record_id]
        campaign.world_troublesome_towns = [item for item in campaign.world_troublesome_towns if item.id != record_id]
        for troupe in campaign.world_troupes:
            if troupe.home_settlement_id == record_id:
                troupe.home_settlement_id = DEFAULT_WORLD_SETTLEMENT_ID
    elif action == "assign" and entity in {"settlement", "troublesome_town"}:
        record_id = str(payload.get("settlement_id") or payload.get("id") or "")
        campaign_id = str(payload.get("campaign_id") or campaign.active_world_campaign_id or DEFAULT_WORLD_CAMPAIGN_ID)
        if not _world_record_exists(campaign.world_campaigns, campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        for collection in [campaign.world_settlements, campaign.world_troublesome_towns]:
            for record in collection:
                if record.id == record_id:
                    record.campaign_id = campaign_id
                    for troupe in campaign.world_troupes:
                        if troupe.home_settlement_id == record.id:
                            _sync_troupe_assignments(campaign, troupe, timestamp=timestamp)
                    break
            else:
                continue
            break
        else:
            raise HTTPException(status_code=404, detail="Settlement not found.")
    elif action == "bulk_assign_campaign":
        campaign_id = str(payload.get("campaign_id") or campaign.active_world_campaign_id or DEFAULT_WORLD_CAMPAIGN_ID)
        if not _world_record_exists(campaign.world_campaigns, campaign_id):
            raise HTTPException(status_code=404, detail="Campaign not found.")
        target_guild = next((guild for guild in campaign.world_guilds if guild.campaign_id == campaign_id), None)
        target_troupe = next((troupe for troupe in campaign.world_troupes if troupe.campaign_id == campaign_id), None)
        target_settlement = next((settlement for settlement in campaign.world_settlements if settlement.campaign_id == campaign_id), None)
        counts = {"guilds": 0, "troupes": 0, "settlements": 0, "parties": 0, "characters": 0}
        for guild in campaign.world_guilds:
            if not guild.campaign_id and target_guild is None:
                guild.campaign_id = campaign_id
                target_guild = guild
                counts["guilds"] += 1
        for settlement in [*campaign.world_settlements, *campaign.world_troublesome_towns]:
            if not settlement.campaign_id:
                settlement.campaign_id = campaign_id
                if settlement.kind == "friendly" and target_settlement is None:
                    target_settlement = settlement
                counts["settlements"] += 1
        for troupe in campaign.world_troupes:
            if not troupe.campaign_id:
                troupe.campaign_id = campaign_id
                if not troupe.guild_id and target_guild is not None:
                    troupe.guild_id = target_guild.id
                if not troupe.home_settlement_id and target_settlement is not None:
                    troupe.home_settlement_id = target_settlement.id
                if target_troupe is None:
                    target_troupe = troupe
                counts["troupes"] += 1
        for party in store.list("parties", Party.model_validate):
            if not party.campaign_id:
                party.campaign_id = campaign_id
                if not party.troupe_id and target_troupe is not None:
                    party.troupe_id = target_troupe.id
                    if party.id not in target_troupe.party_ids:
                        target_troupe.party_ids.append(party.id)
                party.updated_at = timestamp
                store.save("parties", party)
                counts["parties"] += 1
        for character in store.list("characters", Character.model_validate):
            if not character.campaign_id or not character.troupe_id or not character.guild_id:
                if not character.campaign_id:
                    character.campaign_id = campaign_id
                if not character.troupe_id and target_troupe is not None:
                    character.troupe_id = target_troupe.id
                    if character.id not in target_troupe.member_character_ids:
                        target_troupe.member_character_ids.append(character.id)
                if not character.guild_id and target_guild is not None:
                    character.guild_id = target_guild.id
                character.updated_at = timestamp
                store.save("characters", character)
                counts["characters"] += 1
        messages.append(
            "Bulk assignment cleanup: "
            + ", ".join(f"{count} {name}" for name, count in counts.items() if count)
            + (" updated." if any(counts.values()) else "no orphaned records found.")
        )
    elif action == "assign_party_troupe":
        party_id = str(payload.get("party_id") or "")
        troupe_id = str(payload.get("troupe_id") or DEFAULT_WORLD_TROUPE_ID)
        party = store.get("parties", party_id, Party.model_validate)
        if party is None:
            raise HTTPException(status_code=404, detail="Party not found.")
        troupe = _world_troupe(campaign, troupe_id)
        if troupe is None:
            raise HTTPException(status_code=404, detail="Troupe not found.")
        party.troupe_id = troupe_id
        party.campaign_id = troupe.campaign_id or DEFAULT_WORLD_CAMPAIGN_ID
        party.updated_at = timestamp
        store.save("parties", party)
        troupe_campaign_id = party.campaign_id
        troupe_guild_id = troupe.guild_id or DEFAULT_WORLD_GUILD_ID
        for character_id in party.character_ids:
            character = store.get("characters", character_id, Character.model_validate)
            if character is None:
                continue
            character.troupe_id = troupe_id
            character.campaign_id = troupe_campaign_id
            character.guild_id = troupe_guild_id
            character.updated_at = timestamp
            store.save("characters", character)
        for troupe in campaign.world_troupes:
            if troupe.id == troupe_id and party.id not in troupe.party_ids:
                troupe.party_ids.append(party.id)
            if troupe.id == troupe_id:
                for character_id in party.character_ids:
                    if character_id not in troupe.member_character_ids:
                        troupe.member_character_ids.append(character_id)
            elif troupe.id != troupe_id and party.id in troupe.party_ids:
                troupe.party_ids = [item for item in troupe.party_ids if item != party.id]
                troupe.member_character_ids = [item for item in troupe.member_character_ids if item not in party.character_ids]
    elif action == "assign_character_troupe":
        character_id = str(payload.get("character_id") or "")
        troupe_id = str(payload.get("troupe_id") or DEFAULT_WORLD_TROUPE_ID)
        character = store.get("characters", character_id, Character.model_validate)
        if character is None:
            raise HTTPException(status_code=404, detail="Character not found.")
        troupe = _world_troupe(campaign, troupe_id)
        if troupe is None:
            raise HTTPException(status_code=404, detail="Troupe not found.")
        if character.party_id:
            party = store.get("parties", character.party_id, Party.model_validate)
            if party is not None and party.troupe_id and party.troupe_id != troupe_id:
                note = _remove_character_from_party(character, reason=f"assignment to troupe {troupe.name}")
                if note:
                    messages.append(note)
        character.troupe_id = troupe_id
        character.guild_id = troupe.guild_id or DEFAULT_WORLD_GUILD_ID
        character.campaign_id = troupe.campaign_id or DEFAULT_WORLD_CAMPAIGN_ID
        character.updated_at = timestamp
        store.save("characters", character)
        for troupe in campaign.world_troupes:
            if troupe.id == troupe_id and character.id not in troupe.member_character_ids:
                troupe.member_character_ids.append(character.id)
            elif troupe.id != troupe_id and character.id in troupe.member_character_ids:
                troupe.member_character_ids = [item for item in troupe.member_character_ids if item != character.id]
    else:
        raise HTTPException(status_code=400, detail="Unknown campaign world action.")

    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "messages": messages}


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


@app.post("/api/campaign/tag/guild-availability-reroll")
async def campaign_tag_guild_availability_reroll(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, reroll_guild_availability, save_campaign

    campaign = load_campaign(store)
    item_name = str(payload.get("item_name") or "").strip()
    if not item_name:
        raise HTTPException(status_code=400, detail="Item name is required.")
    base_price = payload.get("base_price_gp")
    entry = reroll_guild_availability(
        campaign,
        item_name=item_name,
        difficulty=int(payload.get("difficulty") or 6),
        base_price_gp=None if base_price in (None, "") else int(base_price),
    )
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


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


@app.post("/api/campaign/tag/hidden-trove-recovery")
async def campaign_tag_hidden_trove_recovery(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, recover_hidden_treasure_trove, save_campaign

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = recover_hidden_treasure_trove(campaign, character)
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


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


@app.post("/api/campaign/tag/settlement")
async def campaign_tag_settlement(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import delete_tag_settlement, load_campaign, save_campaign, select_tag_settlement, upsert_tag_settlement

    campaign = load_campaign(store)
    action = str(payload.get("action") or "create")
    if action == "delete":
        deleted = delete_tag_settlement(
            campaign,
            settlement_id=str(payload.get("settlement_id") or ""),
            name=str(payload.get("name") or ""),
        )
        campaign = save_campaign(store, campaign)
        return {"campaign": campaign, "deleted": deleted}
    if action == "select":
        settlement = select_tag_settlement(
            campaign,
            settlement_id=str(payload.get("settlement_id") or ""),
            name=str(payload.get("name") or ""),
        )
        if settlement is None:
            raise HTTPException(status_code=404, detail="Settlement not found.")
        campaign = save_campaign(store, campaign)
        return {"campaign": campaign, "settlement": settlement}
    settlement = upsert_tag_settlement(
        campaign,
        name=str(payload.get("name") or ""),
        size=int(payload.get("size") or 0),
        notes=str(payload.get("notes") or ""),
    )
    campaign.settlement_name = settlement.name
    campaign.settlement_size = settlement.size
    campaign.settlement_notes = settlement.notes
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "settlement": settlement}


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


def _sync_character_to_session_party(session: SessionState, character: Character | None) -> None:
    if character is None:
        return
    for member in session.party:
        if member.character_id != character.id:
            continue
        member.gold = character.gold
        member.clues = character.clues
        member.secrets = list(character.secrets)
        member.current_life = character.current_life
        member.max_life = character.max_life
        member.inventory = list(character.inventory)
        member.spells = list(character.spells)
        member.statuses = list(character.statuses)
        member.learned_expert_skills = list(character.learned_expert_skills)
        member.learned_heroic_skills = list(character.learned_heroic_skills)
        member.learned_legendary_skills = list(character.learned_legendary_skills)
        member.expert_skill_targets = dict(character.expert_skill_targets)
        member.expert_trained = character.expert_trained
        member.heroic_trained = character.heroic_trained
        member.legendary_trained = character.legendary_trained
        member.epic_trained = character.epic_trained
        break


TAG_SESSION_PAYMENT_BRANCHES = {"leprechaun_shoes", "leprechaun_illusion_spell"}
TAG_SESSION_PAYMENT_SCENE_ACTIONS = {"deoldyn_training"}


def _prepare_session_tag_payment_character(
    session: SessionState,
    character: Character | None,
    branch_action: str,
) -> tuple[PartyMemberState | None, int]:
    if character is None or branch_action not in TAG_SESSION_PAYMENT_BRANCHES | TAG_SESSION_PAYMENT_SCENE_ACTIONS:
        return None, 0
    member = next((item for item in session.party if item.character_id == character.id), None)
    if member is None:
        return None, 0
    carried_gold = max(0, member.gold)
    character.gold = max(0, member.gold) + max(0, member.bank_gold)
    character.clues = member.clues
    character.secrets = list(member.secrets)
    character.current_life = member.current_life
    character.max_life = member.max_life
    character.inventory = list(member.inventory)
    character.spells = list(member.spells)
    character.statuses = list(member.statuses)
    character.default_melee_weapon = member.default_melee_weapon
    character.default_melee_weapon_secondary = member.default_melee_weapon_secondary
    character.default_missile_weapon = member.default_missile_weapon
    return member, carried_gold


def _sync_session_tag_payment_character(
    session: SessionState,
    character: Character | None,
    member: PartyMemberState | None,
    carried_gold_before: int,
) -> None:
    if character is None or member is None:
        return
    total_gold = max(0, character.gold)
    member.gold = min(max(0, carried_gold_before), total_gold)
    member.bank_gold = max(0, total_gold - member.gold)
    member.clues = character.clues
    member.secrets = list(character.secrets)
    member.current_life = character.current_life
    member.max_life = character.max_life
    member.inventory = list(character.inventory)
    member.spells = list(character.spells)
    member.statuses = list(character.statuses)
    member.default_melee_weapon = character.default_melee_weapon
    member.default_melee_weapon_secondary = character.default_melee_weapon_secondary
    member.default_missile_weapon = character.default_missile_weapon
    prune_weapon_defaults(member)


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
        _sync_character_to_session_party(session, character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry, "rewrite_result": rewrite_result}


@app.post("/api/campaign/tag/scene-action")
async def campaign_tag_scene_action(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import apply_tag_dragon_reveal_to_latest_adventure, load_campaign, resolve_tag_scene_action, save_campaign

    character = _optional_campaign_character(payload)
    if character is None:
        raise HTTPException(status_code=400, detail="Character is required.")
    campaign = load_campaign(store)
    entry = resolve_tag_scene_action(
        campaign,
        character,
        scene_action=str(payload.get("scene_action") or ""),
        amount=int(payload.get("amount") or 0),
        reference=str(payload.get("reference") or ""),
    )
    module_update = ""
    if str(payload.get("scene_action") or "") == "dragon_type_reveal" and entry.roll:
        if entry.roll <= 3:
            dragon_key = "small_dragon"
        elif entry.roll <= 5:
            dragon_key = "young_red_dragon"
        else:
            dragon_key = "darkness_or_ghoul_dragon"
        module_update = apply_tag_dragon_reveal_to_latest_adventure(
            settings.data_dir,
            campaign,
            dragon_key=dragon_key,
            dragon_label=entry.result_text,
        )
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry, "module_update": module_update}


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
        _sync_character_to_session_party(session, character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/guild-spell")
async def campaign_tag_guild_spell(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import cast_tag_guild_spell, load_campaign, save_campaign

    character = _optional_campaign_character(payload)
    if character is None:
        raise HTTPException(status_code=400, detail="Character is required.")
    target_character = None
    target_character_id = str(payload.get("target_character_id") or "").strip()
    if target_character_id and target_character_id != character.id:
        target_character = store.get("characters", target_character_id, Character.model_validate)
        if target_character is None:
            raise HTTPException(status_code=404, detail="Target character not found.")
    campaign = load_campaign(store)
    entry = cast_tag_guild_spell(
        campaign,
        character,
        spell_key=str(payload.get("spell_key") or ""),
        target_character=target_character,
        target_weapon=str(payload.get("target_weapon") or ""),
    )
    store.save("characters", character)
    if target_character is not None:
        store.save("characters", target_character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "target_character": target_character, "entry": entry}


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
        _sync_character_to_session_party(session, character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry}


@app.post("/api/campaign/tag/closeout-task")
async def campaign_tag_closeout_task(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, resolve_tag_closeout_task, save_campaign

    campaign = load_campaign(store)
    entry = resolve_tag_closeout_task(
        campaign,
        task_id=str(payload.get("task_id") or "").strip() or None,
        task_action=str(payload.get("task_action") or "").strip() or None,
        note=str(payload.get("note") or "").strip(),
    )
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/tag/signoff-review")
async def campaign_tag_signoff_review(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, record_tag_signoff_review, save_campaign

    campaign = load_campaign(store)
    entry = record_tag_signoff_review(campaign, note=str(payload.get("note") or "").strip())
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.post("/api/campaign/guidance-task")
async def campaign_guidance_task(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, save_campaign, update_guidance_task

    campaign = load_campaign(store)
    entry = update_guidance_task(
        campaign,
        task_id=str(payload.get("task_id") or "").strip(),
        status=str(payload.get("status") or "completed").strip(),
        note=str(payload.get("note") or "").strip(),
    )
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "entry": entry}


@app.get("/api/campaign/guidance-tasks")
async def campaign_guidance_tasks(request: Request) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign

    campaign = load_campaign(store)
    status = str(request.query_params.get("status") or "")
    priority = str(request.query_params.get("priority") or "")
    category = str(request.query_params.get("category") or "")
    search = str(request.query_params.get("search") or "").lower()
    rows = campaign.guidance_tasks
    if status:
        rows = [task for task in rows if task.status == status]
    if priority:
        rows = [task for task in rows if task.priority == priority]
    if category:
        rows = [task for task in rows if task.category == category]
    if search:
        rows = [
            task
            for task in rows
            if search in f"{task.title} {task.body} {task.reference} {task.priority} {task.status} {task.category}".lower()
        ]
    return {"tasks": list(reversed(rows)), "count": len(rows)}


@app.get("/api/campaign/command-center")
async def campaign_command_center(request: Request) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign

    campaign = load_campaign(store)
    return campaign_command_center_payload(campaign, request.query_params.get("campaign_id"))


@app.get("/api/campaign/closeout-gate")
async def campaign_closeout_gate_api(request: Request) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign

    campaign = load_campaign(store)
    return campaign_closeout_gate(campaign, request.query_params.get("party_id"))


@app.get("/api/campaign/chronicle/export", response_model=None)
async def campaign_chronicle_export(request: Request) -> Any:
    from .engine.tag_campaign import load_campaign

    campaign = load_campaign(store)
    campaign_id = request.query_params.get("campaign_id")
    export_format = str(request.query_params.get("format") or "json").lower()
    entries = [
        entry
        for entry in campaign.campaign_chronicle
        if not campaign_id or not entry.campaign_id or entry.campaign_id == campaign_id
    ]
    if export_format == "markdown":
        campaign_name = _campaign_record_name(campaign.world_campaigns, campaign_id or campaign.active_world_campaign_id, "Campaign")
        lines = [f"# {campaign_name} Chronicle", ""]
        for entry in reversed(entries):
            context = " · ".join(item for item in [entry.created_at, entry.party_name, entry.character_name, entry.reference] if item)
            lines.extend([f"## {entry.title}", context, "", entry.body or "", ""])
        return Response("\n".join(lines), media_type="text/markdown")
    return {"exported_at": now_utc(), "campaign_id": campaign_id or campaign.active_world_campaign_id, "entries": list(reversed(entries))}


@app.post("/api/campaign/tag/bank-robbery-recovery")
async def campaign_tag_bank_robbery_recovery(payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.adventure_import import import_adventure_manifest
    from .engine.tag_campaign import build_tag_adventure_manifest, load_campaign, resolve_tag_finance_action, save_campaign

    character_id = str(payload.get("character_id") or "").strip()
    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    campaign = load_campaign(store)
    entry = resolve_tag_finance_action(campaign, character, finance_action="robbery_recovery")
    adventure_payload: dict[str, Any] | None = None
    if "spends 3 Clues" in entry.result_text:
        manifest, adventure_entry = build_tag_adventure_manifest(campaign, lead_type="thematic_dungeon", detail="6")
        path, result = import_adventure_manifest(
            settings.root_dir,
            settings.data_dir,
            manifest,
            rules_repo=rules,
            overwrite=True,
        )
        if not result.valid or path is None:
            raise HTTPException(status_code=400, detail="; ".join(result.errors) or "Bandit Hideout creation failed.")
        adventure_payload = {
            "entry": adventure_entry,
            "adventure_id": manifest["id"],
            "title": manifest["title"],
            "room_count": len(manifest.get("rooms", [])),
            "quest_objective": (manifest.get("quest") or {}).get("objective_text"),
            "warnings": result.warnings,
        }
    store.save("characters", character)
    campaign = save_campaign(store, campaign)
    return {"campaign": campaign, "character": character, "entry": entry, "adventure": adventure_payload}


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


@app.get("/api/rules/artwork")
async def rules_artwork() -> dict:
    entries = []
    for row in rules.artwork_registry():
        item = dict(row)
        asset_path = str(item.get("asset_path") or "").strip()
        resolved, source = _resolve_asset_file(asset_path) if asset_path else (None, None)
        item["asset_exists"] = resolved is not None
        item["asset_source"] = source or ""
        item["user_asset_path"] = f"assets/{asset_path}" if asset_path else ""
        entries.append(item)
    return {"entries": entries}


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
    data["item_tooltip_coverage_table"] = [
        {
            "surface": "Equipment Shop buy list",
            "hover_behavior": "Rows explain price, category, class block, sale value, and known mechanical use for the item before purchase.",
            "player_use": "Check what an item affects before spending gold.",
            "rules_boundary": "App summary only; exact printed item text remains in the relevant Rules Reference/source pages.",
        },
        {
            "surface": "Equipment Shop sell list",
            "hover_behavior": "Carried item options explain item purpose plus the sale-quote rule shown beside the selector.",
            "player_use": "Avoid selling a tool, weapon, magic item, or clue-bearing item without understanding its use.",
            "rules_boundary": "Sell payout still comes from the backend shop/resale resolver.",
        },
        {
            "surface": "Character and party inventory",
            "hover_behavior": "Inventory labels and stored-gear spans explain common equipment, magic/charged items, valuables, TAG rewards, and known special items.",
            "player_use": "Browse a sheet and understand what carried items do without opening a separate lookup first.",
            "rules_boundary": "Hover text is explanatory guidance, not a replacement for PDF-specific scene text.",
        },
        {
            "surface": "Item choice dialogs",
            "hover_behavior": "Transfer, stash/retrieve, sacrifice, professional coating, and generic inventory pickers attach the same item descriptions to their options.",
            "player_use": "Understand the consequence of choosing an item during play.",
            "rules_boundary": "Backend validation remains authoritative for whether the chosen item can be used.",
        },
    ]
    data["class_profiles_table"] = class_profiles_table_rows(rules.classes())
    data["expert_skills_table"] = expert_skills_table_rows(expert_catalog)
    data["expert_spells_table"] = expert_spells_table_rows(expert_catalog)
    data["expert_skill_implementation_table"] = expert_skill_implementation_rows(expert_catalog)
    data["heroic_skills_table"] = tier_skills_table_rows(rules.heroic_skills(), "heroic")
    data["legendary_skills_table"] = tier_skills_table_rows(rules.legendary_skills(), "legendary")
    data["class_tricks_implementation_table"] = class_tricks_implementation_rows()
    data["ee_class_trick_flags_table"] = ee_class_trick_flags_table_rows(rules.ee_class_tricks())
    data["artwork_registry_table"] = [
        {
            "id": row.get("id", ""),
            "title": row.get("title", ""),
            "category": row.get("category", ""),
            "status": row.get("status", ""),
            "source_pdf": row.get("source_pdf", ""),
            "source_page": row.get("source_page", ""),
            "asset_path": row.get("asset_path", ""),
            "summary": row.get("summary", ""),
        }
        for row in rules.artwork_registry()
    ]
    data["campaign_worldbuilder_schema_table"] = [
        {
            "entity": "Campaign",
            "allowed_per_campaign": "1 selected world record",
            "assignment_rule": "Owns one guild, multiple troupes, multiple friendly settlements, and multiple troublesome-town placeholders.",
            "default_record": "Norindaal",
            "rules_boundary": "App world-builder bookkeeping, not a TAG PDF rule.",
        },
        {
            "entity": "Guild",
            "allowed_per_campaign": "1 guild assigned to each campaign",
            "assignment_rule": "A guild can belong to only one campaign. The backend blocks assigning two guilds to the same campaign.",
            "default_record": "Adventurers Guild",
            "rules_boundary": "App assignment layer; TAG Guild mechanics remain separate and linked through Guild Management.",
        },
        {
            "entity": "Troupe",
            "allowed_per_campaign": "Multiple troupes",
            "assignment_rule": "A troupe belongs to one campaign, can point to one guild, and has one friendly home settlement.",
            "default_record": "Troupe1",
            "rules_boundary": "App assignment layer; TAG troupe activity uses this context where relevant.",
        },
        {
            "entity": "Friendly Settlement",
            "allowed_per_campaign": "Multiple settlements",
            "assignment_rule": "A friendly settlement belongs to one campaign and may be used as a troupe home settlement.",
            "default_record": "Hearthmere",
            "rules_boundary": "App world record; TAG size modifiers affect supported availability/service checks.",
        },
        {
            "entity": "Troublesome Town",
            "allowed_per_campaign": "Multiple placeholders",
            "assignment_rule": "Reserved for future Treacheries of the Troublesome Town supplements. Current records are campaign placeholders only.",
            "default_record": "None",
            "rules_boundary": "No supplement mechanics are claimed as implemented yet.",
        },
        {
            "entity": "Character",
            "allowed_per_campaign": "One campaign, one guild, one troupe, one party",
            "assignment_rule": "Assigning a character to a conflicting troupe warns in the UI and removes incompatible party membership in the backend.",
            "default_record": "Defaults through Troupe1 / Adventurers Guild / Norindaal",
            "rules_boundary": "App roster consistency rule.",
        },
    ]
    data["modern_dashboard_management_table"] = [
        {
            "page": "Dashboard",
            "primary_controls": "Section launcher tiles, linked artwork, status-icon snapshot, collapsed needs-attention and closeout panels.",
            "assignment_model": "App navigation and status summary only; underlying records remain owned by their management pages.",
            "hover_focus": "Snapshot rows open exact issue lists without increasing header height, such as missing artwork paths, open guidance, active sessions, fallen characters, and setup warnings.",
            "rules_reference": "modern_dashboard_management_polish",
        },
        {
            "page": "Troupe Management",
            "primary_controls": "World context, member filters, add/remove member, active members, assigned party filter, settlement travel.",
            "assignment_model": "Troupe1 remains the TAG-focused default; world troupes are edited in Campaign Management. Characters belong to one troupe.",
            "hover_focus": "Explains party removal risk, active member meaning, home settlement use, and travel logging.",
            "rules_reference": "campaign_membership_boundaries",
        },
        {
            "page": "Guild Management",
            "primary_controls": "World context, Guild active/coffers, member filters, Guild finance, Guild jobs, benefits, closeout.",
            "assignment_model": "One guild per campaign in the world-builder layer; TAG benefits require active membership and coffers above 0 gp.",
            "hover_focus": "Explains coffers, loot share, upkeep, availability reroll, resurrection funding, and Guild Job creation.",
            "rules_reference": "tag_guild_closeout_guidance",
        },
        {
            "page": "Party Management",
            "primary_controls": "World context, create party, party search, troupe filter, assignment warning, heal, bank, delete.",
            "assignment_model": "A party belongs to one troupe. Assigning a party syncs party characters to the selected troupe context.",
            "hover_focus": "Explains one-party/one-troupe boundaries, character sync, TAG banking migration, and delete behavior.",
            "rules_reference": "party_troupe_management",
        },
        {
            "page": "Settlement Management",
            "primary_controls": "World context, settlement fields, availability picker, campaign settlement filters, tracked settlement list.",
            "assignment_model": "Friendly settlements are campaign records; tracked TAG settlements drive current downtime, services, travel, and availability.",
            "hover_focus": "Explains settlement size modifier, friendly/troublesome boundary, travel logging, and active settlement selection.",
            "rules_reference": "settlement_management_workflow",
        },
    ]
    data["campaign_assignment_integrity_table"] = [
        {
            "assignment": "Guild -> Campaign",
            "limit": "A campaign may have one assigned guild; a guild may belong to one campaign.",
            "automatic_update": "Moving a guild updates linked troupes, parties, and characters that inherit that guild context.",
            "user_warning": "The API blocks a second guild from being assigned to the same campaign.",
        },
        {
            "assignment": "Troupe -> Campaign/Guild/Home",
            "limit": "A troupe belongs to one campaign, one guild, and one friendly home settlement.",
            "automatic_update": "Moving a troupe updates assigned parties and characters to the troupe campaign/guild context.",
            "user_warning": "The API rejects guild or home-settlement choices from a different campaign.",
        },
        {
            "assignment": "Party -> Troupe",
            "limit": "A party belongs to one troupe and has exactly four character members.",
            "automatic_update": "Assigning a party to a troupe syncs all party characters to that troupe, campaign, and guild.",
            "user_warning": "Party Management shows mismatch warnings before resyncing.",
        },
        {
            "assignment": "Character -> Party/Troupe/Guild",
            "limit": "A character belongs to one party, one troupe, and one guild.",
            "automatic_update": "Assigning a character to another troupe removes incompatible party membership and returns a guidance message.",
            "user_warning": "Troupe Management asks for confirmation before triggering party removal.",
        },
        {
            "assignment": "Friendly/Troublesome Settlement -> Campaign",
            "limit": "Each settlement record belongs to one campaign; friendly settlements can be troupe homes.",
            "automatic_update": "Moving a home settlement refreshes affected troupe, party, and character context.",
            "user_warning": "Troublesome-town records remain placeholders until supplement mechanics are implemented.",
        },
    ]
    data["adventure_closeout_workflow_table"] = [
        {
            "stage": "Adventure completion",
            "created_records": "Campaign chronicle entry plus closeout guidance task.",
            "required_review": "Party rewards, fallen/injured members, XP, banking, storage, Guild obligations.",
            "rules_boundary": "App workflow; specific TAG tasks cite TAG references where automated.",
        },
        {
            "stage": "TAG closeout task creation",
            "created_records": "Guild loot share/upkeep/leaving/reroll, XP markers, storage risk/recovery, bank robbery recovery.",
            "required_review": "Open tasks remain visible on Dashboard, Guild, Banking, and closeout panels.",
            "rules_boundary": "TAG references are linked in task reference text; full PDF text is not copied.",
        },
        {
            "stage": "Task resolution",
            "created_records": "Resolved closeout task, completed guidance task, and campaign log entry.",
            "required_review": "Use real controls where available; Mark Done is for manual signoff.",
            "rules_boundary": "Manual signoff records player decision rather than resolving hidden mechanics.",
        },
        {
            "stage": "Closeout complete",
            "created_records": "No open required closeout guidance for the completed adventure.",
            "required_review": "Optional/deferred tasks may remain in the campaign log and guidance list.",
            "rules_boundary": "Starting another adventure remains allowed when user intentionally accepts remaining optional tasks.",
        },
    ]
    data["campaign_chronicle_event_table"] = [
        {
            "event_type": "adventure_completed",
            "source": "Session completion hook.",
            "shown_in": "Dashboard Guidance / Log and Campaign Management chronicle.",
            "retention": "Latest 120 campaign chronicle entries.",
        },
        {
            "event_type": "tag_*",
            "source": "TAG downtime, Guild, banking, settlement, storage, route, and closeout logs.",
            "shown_in": "Campaign chronicle filters and dashboard recent log.",
            "retention": "Latest 120 campaign chronicle entries; TAG compact log still keeps its shorter existing limit.",
        },
        {
            "event_type": "guidance_task",
            "source": "Completing, deferring, dismissing, or reopening a guidance task.",
            "shown_in": "Campaign chronicle and guidance task history.",
            "retention": "Chronicle entry remains even when the guidance task leaves the active list.",
        },
    ]
    data["guidance_task_status_table"] = [
        {
            "status": "open",
            "meaning": "Needs attention and appears in Dashboard guidance.",
            "safe_use": "Use for required or recommended work before the next adventure.",
        },
        {
            "status": "completed",
            "meaning": "Handled through a real control or manual signoff.",
            "safe_use": "Completion does not delete the campaign chronicle entry.",
        },
        {
            "status": "deferred",
            "meaning": "Acknowledged but intentionally left for later.",
            "safe_use": "Useful for optional campaign bookkeeping that should not block play.",
        },
        {
            "status": "dismissed",
            "meaning": "Hidden from active guidance without erasing history.",
            "safe_use": "Use only for prompts that are irrelevant to this campaign.",
        },
    ]
    data["campaign_command_center_table"] = [
        {
            "surface": "Campaign overview",
            "shows": "Selected campaign, assigned Guild, troupes, settlements, troublesome-town placeholders, parties, characters, active sessions, open guidance, unresolved closeout, and recent chronicle.",
            "source": "/api/campaign/command-center",
            "rules_boundary": "App world-builder bookkeeping, not printed TAG rule text.",
        },
        {
            "surface": "Guidance archive",
            "shows": "Status, priority, category, and search filters for all structured guidance tasks.",
            "source": "CampaignState.guidance_tasks",
            "rules_boundary": "Prompt history remains separate from the campaign chronicle.",
        },
        {
            "surface": "Chronicle export",
            "shows": "JSON or Markdown export of campaign chronicle entries.",
            "source": "/api/campaign/chronicle/export",
            "rules_boundary": "Exports app-owned play history only.",
        },
        {
            "surface": "Assign orphans",
            "shows": "Bulk assignment cleanup for records without campaign/guild/troupe context.",
            "source": "/api/campaign/world action bulk_assign_campaign",
            "rules_boundary": "Only fills missing app assignment fields where safe.",
        },
    ]
    data["go_adventure_closeout_gate_table"] = [
        {
            "issue": "Hard block",
            "examples": "Missing party, wrong party size, fallen members, active character locks.",
            "start_behavior": "Start Adventure is blocked until resolved.",
            "override": "No override.",
        },
        {
            "issue": "Override warning",
            "examples": "Open required guidance or unresolved TAG closeout prompts.",
            "start_behavior": "Start Adventure requires explicit Start Anyway confirmation.",
            "override": "Allowed after player confirmation.",
        },
        {
            "issue": "Warning",
            "examples": "Injured members, equipment-slot warnings, campaign/guild/troupe context mismatches.",
            "start_behavior": "Shown for review but does not block.",
            "override": "Not required.",
        },
    ]
    data["go_adventure_tabbed_workflow_table"] = [
        {
            "tab": "Start",
            "contains": "Start New Adventure controls plus setup and closeout status icons. Clicking an icon opens the exact issue list; full Setup Check and Closeout Gate panels are no longer shown.",
            "player_use": "Choose party/module/rules and start; click the status icons only when the app reports setup, closeout, or guidance issues.",
            "rules_boundary": "Start checks remain enforced by the backend; printed rules still control adventure resolution.",
        },
        {
            "tab": "Resume",
            "contains": "Active sessions and saved games.",
            "player_use": "Continue existing play without confusing it with creating a fresh adventure.",
            "rules_boundary": "No rules automation; this is session management.",
        },
        {
            "tab": "Generate",
            "contains": "TAG Workflow Summary, Adventures Guild lead creation, and Rumor, Treasure Map, and Thematic Dungeon audit/signoff panels.",
            "player_use": "Use Random to let the app choose the lead family and result, or uncheck it to choose the family and let the app roll within that family.",
            "rules_boundary": "The app rolls fixed lead family/result values when requested; printed choices remain player choices.",
        },
        {
            "tab": "Guild Jobs",
            "contains": "Guild Job guidance and a shortcut to select the Guild Job generator.",
            "player_use": "Use when the adventure comes from Guild work rather than a normal random start.",
            "rules_boundary": "Guild Job procedure support is app-authored workflow around TAG source references.",
        },
        {
            "tab": "Reference",
            "contains": "Closeout, generated-lead signoff, Adventures Guild Action Log, Rules Reference, and Tables links.",
            "player_use": "Review after play or before creating another lead.",
            "rules_boundary": "Reference links point to implementation notes and source pages; they do not copy full PDF text.",
        },
    ]
    data["exploration_narrative_layout_table"] = [
        {
            "control": "Narrative",
            "affects": "The live adventure text stream formerly labelled Log.",
            "player_use": "Read room prose, procedure results, combat summaries, treasure notices, and closeout guidance.",
            "automation": "Summary/Verbose changes how much roll and lookup detail is visible.",
        },
        {
            "control": "Current Objective",
            "affects": "The next-step guidance banner.",
            "player_use": "Show it when you want the app to say what to do next; hide it when the map needs more room.",
            "automation": "For supported Adventures Guild procedures it can run stored/idempotent rolls or show the exact next play-state target.",
        },
        {
            "control": "Ongoing Quests",
            "affects": "Quest cards in the Action Rail.",
            "player_use": "Open when checking active objectives, source, turn-in state, Adventures Guild procedure progress, and reward buttons.",
            "automation": "Quest cards expose supported reward, Adventures Guild procedure, and signoff actions while keeping player choices explicit.",
        },
        {
            "control": "Text Commands",
            "affects": "Typed exploration command entry.",
            "player_use": "Toggles a slim bottom command palette. Use commands such as look, search, claim, rest, or go north 1; press ? for examples and Escape to close.",
            "automation": "Commands call the same session actions as buttons while the palette overlays the play surface instead of taking map height.",
        },
        {
            "control": "Exits",
            "affects": "Door and passage list beside the Narrative.",
            "player_use": "Open while choosing where to move; hide when the map and Narrative need the space.",
            "automation": "Exit buttons use the app's current legal exit state.",
        },
        {
            "control": "Character Sheets",
            "affects": "Party sheet panel in the exploration side rail.",
            "player_use": "Open for Life, inventory, equipment, spells, statuses, transfer, and character actions.",
            "automation": "Sheet actions use the same validated backend endpoints as the older controls.",
        },
    ]
    data["application_artwork_slots_table"] = [
        {
            "page": "New Home Dashboard",
            "slot": "home_dashboard_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/home_dashboard_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Home dashboard Relevant Artwork panel.",
        },
        {
            "page": "Character Management",
            "slot": "character_management_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/character_management_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Character sheet and roster management artwork.",
        },
        {
            "page": "Troupe Management",
            "slot": "troupe_management_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/troupe_management_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Troupe member, party, travel, and home settlement artwork.",
        },
        {
            "page": "Guild Management",
            "slot": "guild_management_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/guild_management_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Guild member, coffers, jobs, and closeout artwork.",
        },
        {
            "page": "Party Management",
            "slot": "party_management_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/party_management_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Saved party and troupe assignment artwork.",
        },
        {
            "page": "Equipment Shop",
            "slot": "equipment_shop_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/equipment_shop_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Equipment and shop artwork.",
        },
        {
            "page": "Banking and Finance",
            "slot": "banking_finance_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/banking_finance_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Accounts, troves, storage, and recovery artwork.",
        },
        {
            "page": "Settlement Management",
            "slot": "settlement_management_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/settlement_management_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Friendly settlement, services, and travel artwork.",
        },
        {
            "page": "Campaign Management",
            "slot": "campaign_management_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/campaign_management_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Campaign world-builder artwork.",
        },
        {
            "page": "Adventure Management",
            "slot": "adventure_management_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/adventure_management_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Generated/imported module management artwork.",
        },
        {
            "page": "Go Adventure!",
            "slot": "go_adventure_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/go_adventure_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Start, resume, and generation workflow artwork.",
        },
        {
            "page": "Camp Screen",
            "slot": "camp_screen_2400x1000.gif",
            "path": "DATA_DIR/assets/Application Artwork/camp_screen_2400x1000.gif",
            "recommended_size": "2400x1000",
            "use": "Large camp screen artwork while the party is camped outside a dungeon.",
        },
        {
            "page": "Rules Reference",
            "slot": "rules_reference_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/rules_reference_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Rules Reference artwork.",
        },
        {
            "page": "Tables List",
            "slot": "tables_list_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/tables_list_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Tables browser artwork.",
        },
        {
            "page": "Credits / History / Background",
            "slot": "library_background_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/library_background_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "PDF library and background artwork.",
        },
        {
            "page": "Game Guides",
            "slot": "game_guides_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/game_guides_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Guide section artwork.",
        },
        {
            "page": "Settings / Options",
            "slot": "settings_options_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/settings_options_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Settings and profile artwork.",
        },
        {
            "page": "Developer Section",
            "slot": "developer_section_1600x900.gif",
            "path": "DATA_DIR/assets/Application Artwork/developer_section_1600x900.gif",
            "recommended_size": "1600x900",
            "use": "Developer tooling and Artwork Manager artwork.",
        },
    ]
    data["developer_preferences_table"] = [
        {
            "preference": "show_tag_fixed_result_selector",
            "default": "false",
            "stored_in": "game.db records/preferences/ui",
            "developer_ui": "Developer Playtest Preferences",
            "effect": "Shows the fixed Adventures Guild result selector in module generators for repeatable playtests.",
            "rules_boundary": "Normal play should leave this off so generated Adventures Guild modules roll from the printed tables.",
        },
        {
            "preference": "button_design_baseline",
            "default": "shared CSS",
            "stored_in": "src/app/static/styles.css",
            "developer_ui": "All panels and screens",
            "effect": "Normal command buttons share a 40px hit target, consistent padding, radius, focus, hover, disabled, primary, secondary, danger, and link-button styling.",
            "rules_boundary": "UI-only; does not change any PDF mechanic.",
        },
    ]
    data["playtest_triage_workflow_table"] = [
        {
            "field": "Area",
            "purpose": "Classifies whether the report concerns Exploration, Current Objective, TAG generated modules, Adventure Management, Go Adventure, Rules Reference/Tables, or other app flow.",
            "rules_boundary": "A report can identify a rule concern, but mechanics are changed only after checking the relevant PDF/table/reference.",
        },
        {
            "field": "Severity",
            "purpose": "Separates blocked play from confusing-but-playable wording and polish issues.",
            "rules_boundary": "Blocked play can be fixed immediately when it is UI/state handling; rules amounts or outcomes still need source verification.",
        },
        {
            "field": "What happened / Expected / Steps",
            "purpose": "Produces a copyable Markdown report while the session/module context is fresh.",
            "rules_boundary": "The report captures observations; it does not assert printed rule text.",
        },
    ]
    data["exploration_objective_clarity_table"] = [
        {
            "surface": "Current Objective",
            "shows": "Target, Next, Handled by app, and Quest reward status when relevant.",
            "player_use": "Use it to answer what you are trying to do, what button to press next, what the app will update, or when an Adventures Guild complication is just telling you to move to the next scene-specific choice.",
            "rules_boundary": "The app explains current state and supported automation; source-specific player choices remain explicit.",
        },
        {
            "surface": "Quest Details",
            "shows": "Quest title/source, guidance, journal rows, Adventures Guild procedure panel, closeout checklist, and reward button state.",
            "player_use": "Open when the compact Narrative chip is not enough.",
            "rules_boundary": "Exact PDF procedure text remains referenced by source/page or Rules Reference rather than copied wholesale.",
        },
        {
            "surface": "Narrative chips",
            "shows": "Compact objective and quest status buttons in the Narrative title bar.",
            "player_use": "Toggle objective or quest details without losing map space.",
            "rules_boundary": "Chips summarize app state only.",
        },
    ]
    data["adventure_management_browser_table"] = [
        {
            "area": "Modules tab",
            "purpose": "Single list of all rules, PDF source, imported, AI, and Adventures Guild modules with module name, source, lifecycle status, export actions, and delete safety.",
            "safety": "Deletion is disabled for protected modules and active-session modules.",
        },
        {
            "area": "Global import actions",
            "purpose": "JSON import lives at the top of the Modules tab because import creates a new module rather than acting on an existing row. ZIP import is reserved for full adventure-folder packages.",
            "safety": "Imported modules must validate before they are installed into DATA_DIR/Adventures.",
        },
        {
            "area": "Source tabs",
            "purpose": "Generate Modules owns The Adventures Guild and AI generators; PDF Module Importer owns scan/package/map-pin review; Create Module is a placeholder for hand-authored modules.",
            "safety": "Generated modules still start from Go Adventure after readiness checks.",
        },
    ]
    data["adventure_pdf_source_scan_table"] = [
        {
            "field": "Source folders",
            "records": "DATA_DIR/Adventure PDFs plus the legacy repository Adventures folder.",
            "purpose": "Find newly added owned PDF adventure sources without making them playable automatically.",
            "pdf_boundary": "The scanner stores metadata only; it does not copy long PDF prose or rules text into app data.",
        },
        {
            "field": "Assessment",
            "records": "File name, title guess, page count, encryption flag, text extractability, likely module type, package signals, confidence, warnings, and recommended conversion path.",
            "purpose": "Decide whether the PDF needs a room-manifest converter, collection split, campaign bundle, scene route, hex-crawl workflow, map pins, package tables/foes/classes, or manual review.",
            "pdf_boundary": "Detected type is a workflow hint, not a rules ruling.",
        },
        {
            "field": "Playable status",
            "records": "PDF source rows stay playable=false until a validated adventure.json manifest exists.",
            "purpose": "Prevent source PDFs from appearing as broken modules in Go Adventure.",
            "pdf_boundary": "A reviewed manifest remains the source of playable room graph data.",
        },
    ]
    data["adventure_package_schema_table"] = [
        {
            "area": "Declarative package",
            "purpose": "Adds local PDF module content as data: foes, classes, items, states, rules, tables, trackers, map assets, pins, and extracted artwork.",
            "safety": "Packages do not execute scripts; they use engine-approved operations only.",
        },
        {
            "area": "Map assets and pins",
            "purpose": "Stores imported PDF map images under DATA_DIR assets and ties rooms, hexes, or locations to percentage-based map pins.",
            "safety": "The PDF remains the source of truth; pins are reviewable metadata, not hidden rules.",
        },
        {
            "area": "Local tables and foes",
            "purpose": "Lets an imported module bring its own roll tables, monsters, rewards, and item references without changing global rulebooks.",
            "safety": "Rows must keep source page references and stay inside the package unless explicitly promoted later.",
        },
        {
            "area": "States, rules, trackers, and procedures",
            "purpose": "Models common adventure logic such as character states, local module rules, doom clocks, route counters, save checks, table rolls, and branch transitions.",
            "safety": "Only allowlisted operation names are valid; arbitrary code is intentionally excluded.",
        },
        {
            "area": "Class extensions",
            "purpose": "Records candidate new character classes from module PDFs for later rules review and UI support.",
            "safety": "Classes stay experimental until every ability, equipment rule, and advancement hook is checked against the PDF.",
        },
        {
            "area": "Artwork library",
            "purpose": "Stores all PDF-exposed images under DATA_DIR/Adventures/<adventure_id>/artwork/extracted for local review and later assignment as cover, scene, foe, item, or location art.",
            "safety": "Extracted PDF artwork is private/local data unless publishing rights are secured; images may include junk page furniture and must be reviewed before use.",
        },
    ]
    data["adventure_package_map_pinning_table"] = [
        {
            "area": "Package files",
            "path": "DATA_DIR/Adventures/<adventure_id>/package.json",
            "purpose": "Stores reviewed package metadata, map records, and room/location pins beside the adventure manifest.",
            "boundary": "Package files prepare import data; they do not make a source PDF playable by themselves.",
        },
        {
            "area": "Map assets",
            "path": "DATA_DIR/Adventures/<adventure_id>/maps/",
            "purpose": "Stores extracted embedded map images, rendered PDF map pages, or manually supplied map images from user-owned PDFs.",
            "boundary": "Keep private-use PDF-derived art local unless publishing rights are secured.",
        },
        {
            "area": "Pin coordinates",
            "path": "maps[].pins[] x/y/width/height as percent",
            "purpose": "Links a room, scene, hex, or location id to a position on the imported map image. Pin role marks ordinary locations, rooms, dungeon entrances, exits, stairs, secrets, objectives, camps, settlements, or other markers.",
            "boundary": "Pins are review metadata; exact room/key rules still come from the PDF and reviewed manifest.",
        },
        {
            "area": "Pin roles",
            "path": "maps[].pins[].role",
            "purpose": "Lets the graphical review screen distinguish location pins from entrances, exits, stairs, objectives, secrets, camp, and settlement markers.",
            "boundary": "A role documents the map review decision; it does not auto-create playable movement until the location graph is reviewed.",
        },
        {
            "area": "Refresh behavior",
            "path": "Create / Refresh Package",
            "purpose": "Re-extracts candidate map images while preserving existing pins with matching map ids.",
            "boundary": "A refresh should not erase manual review work.",
        },
    ]
    data["adventure_package_review_workspace_table"] = [
        {
            "area": "Review workspace",
            "purpose": "Lets the user inspect and edit PDF-imported package data as human-readable candidate lists and structured sections instead of raw JSON only.",
            "stored_in": "DATA_DIR/Adventures/<module_id>/package.json",
            "fields": "title, reviewed pages, rights note, review status, review notes, nodes, foes, classes, items, states, rules, tables, trackers, procedures",
            "safety": "Package diagnostics report structural errors and warnings before conversion to a playable adventure.json manifest.",
        },
        {
            "area": "Candidate browser",
            "purpose": "Shows clickable lists of imported locations/nodes, tables, foes, items, classes, states, rules, and procedures with a detail pane.",
            "stored_in": "package.json nodes[], tables[], foes[], items[], classes[], states[], rules[], procedures[], ignored_records[]",
            "fields": "record id, title/name, source page, review status, source text, branches, rows, procedure steps, original extraction metadata",
            "safety": "Extractor output is marked needs_pdf_check and must be confirmed against the PDF before being used for play. Misclassified records can be moved; junk records can be ignored and preserved for future importer improvement.",
        },
        {
            "area": "Review nodes",
            "purpose": "Human-reviewed rooms, scenes, hexes, locations, camps, settlements, and endings extracted from the source PDF. The Location Preview shows player text, app notes, exits, linked foes/items/procedures, and any linked map pin or room image.",
            "stored_in": "package.json nodes[]",
            "fields": "id, type, title, source_page, player_text, app_notes, branches, foe_ids, item_ids, procedure_ids, map_pin_id, review_status",
            "safety": "Branches and linked ids should point to reviewed package records; source_page remains visible for PDF audit.",
        },
        {
            "area": "Location editor",
            "purpose": "Lets a reviewer create or update a single room/scene/location in a structured form that can later be reused by the hand-authored Create Module workflow.",
            "stored_in": "package.json nodes[] plus linked package lists",
            "fields": "linked foes, linked items, linked procedures, map pin id, exits/choices JSON, player description, app/rules notes",
            "safety": "The editor saves explicit ids instead of copying full records into the node, keeping generated/imported package data reusable and easier to audit.",
        },
        {
            "area": "Imported record editor",
            "purpose": "Lets the user preview and edit module-local foes, items, classes, states, rules, tables, trackers, and procedures without starting in raw JSON.",
            "stored_in": "package.json foes[], items[], classes[], states[], rules[], tables[], trackers[], procedures[]",
            "fields": "id, name/title/label, source page, review status, notes/source text, item modifiers/states/pricing/buyable/sellable flags, state modifiers/removal, rule trigger/effect, table rows, tracker ranges, procedure steps, extra JSON",
            "safety": "Records remain PDF-review package data until a manifest uses them; procedure steps are still sanitized to allowlisted operations only.",
        },
        {
            "area": "User guide",
            "purpose": "Documents the editable module-folder format for users and playtesters.",
            "stored_in": "docs/ADVENTURE_MODULE_FORMAT.md",
            "fields": "adventure.json, package.json, maps, pins, procedures, safe editing workflow",
            "safety": "Private-use PDF prose and artwork stay local in DATA_DIR unless publishing rights are secured.",
        },
    ]
    data["artwork_expansion_plan_table"] = [
        {
            "slot": "Module cover art",
            "path": "DATA_DIR/assets/artwork/user/adventures/<module_id>_cover_1600x900.*",
            "use": "Adventure Management selected-module detail and future module cards.",
        },
        {
            "slot": "Character portraits",
            "path": "DATA_DIR/assets/artwork/user/portraits/<character_or_portrait_id>.*",
            "use": "Roster rows, character sheets, party sheets, and selected-member panels.",
        },
        {
            "slot": "Settlement art",
            "path": "DATA_DIR/assets/artwork/user/locations/<settlement_id>_1600x900.*",
            "use": "Settlement records and campaign world-builder views.",
        },
        {
            "slot": "Adventures Guild lead-family art",
            "path": "DATA_DIR/assets/artwork/user/adventures/tag_<lead_family>_1600x900.*",
            "use": "Rumor, Treasure Map, Thematic Dungeon, and Guild Job generation/signoff panels.",
        },
        {
            "slot": "Finance state art",
            "path": "DATA_DIR/assets/artwork/user/items/<bank_trove_loan_state>.*",
            "use": "Bank, hidden trove, robbed account, inheritance, and loan status rows.",
        },
    ]
    data["user_artwork_placeholders_table"] = [
        {
            "slot": "tag_treasure_map_underground_caves_1600x900",
            "path": "DATA_DIR/assets/artwork/user/adventures/",
            "recommended_size": "1600x900",
            "use": "Scene art for TAG Treasure Map: Underground Caves.",
        },
        {
            "slot": "generated_adventure_scene_1600x900",
            "path": "DATA_DIR/assets/artwork/user/adventures/",
            "recommended_size": "1600x900",
            "use": "Overview art for generated or imported adventures.",
        },
        {
            "slot": "camp_1600x900 / settlement_1600x900",
            "path": "DATA_DIR/assets/artwork/user/locations/",
            "recommended_size": "1600x900",
            "use": "Camp and friendly settlement scene art.",
        },
        {
            "slot": "final_boss_1024x1024",
            "path": "DATA_DIR/assets/artwork/user/monsters/",
            "recommended_size": "1024x1024",
            "use": "Final Boss portrait or encounter image.",
        },
        {
            "slot": "treasure_map_1024x768 / character_portrait_768x1024",
            "path": "DATA_DIR/assets/artwork/user/items/ and DATA_DIR/assets/artwork/user/portraits/",
            "recommended_size": "1024x768 or 768x1024",
            "use": "Treasure map item art and character portrait art.",
        },
        {
            "slot": "asset resolution",
            "path": "/assets/<relative-path>",
            "recommended_size": "n/a",
            "use": "The app serves DATA_DIR/assets first, then falls back to bundled /app/assets defaults.",
        },
    ]
    data["modern_tag_workflow_table"] = [
        {
            "surface": "TAG Workflow Summary",
            "shown_on": "Troupe, Guild, Banking, Settlement, and Go Adventure modern pages.",
            "tracks": "Troupe membership/active count, Guild benefits/coffers, bank accounts, robbed accounts, hidden trove, generated Adventures Guild leads, route markers, XP markers, closeout prompts, guidance tasks.",
            "player_use": "First scan before and after TAG adventures.",
        },
        {
            "surface": "TAG Signoff panel",
            "shown_on": "Troupe, Guild, Banking, Settlement, and Go Adventure modern pages.",
            "tracks": "Latest generated lead, latest route marker, pending XP markers, latest TAG log.",
            "player_use": "Review generated-adventure branch/reward/XP/Guild/banking consequences before closeout.",
        },
        {
            "surface": "Guild workflow",
            "shown_on": "Guild Management.",
            "tracks": "Membership, coffers, benefits, loot share, upkeep, availability reroll, resurrection funding, Guild job lead creation, Guild closeout prompts.",
            "player_use": "Run Guild obligations without falling back to the legacy homepage.",
        },
        {
            "surface": "Finance workflow",
            "shown_on": "Banking and Finance.",
            "tracks": "TAG bank ledgers, hidden troves, robbed accounts, inheritance, loans, bulk migration, closeout recovery prompts.",
            "player_use": "Resolve banking/storage consequences after adventures.",
        },
        {
            "surface": "Settlement workflow",
            "shown_on": "Settlement Management.",
            "tracks": "Settlement name, size modifier, notes, tracked settlements, availability checks, travel logs.",
            "player_use": "Understand what settlement size affects and keep service/travel context visible.",
        },
    ]
    data["tag_generated_adventure_signoff_table"] = [
        {
            "checkpoint": "Lead created",
            "review": "Confirm the generated Adventures Guild module came from the intended Rumor, Treasure Map, Thematic Dungeon, or Guild Job.",
            "where": "Go Adventure, Guild Job Lead, TAG guide.",
        },
        {
            "checkpoint": "Room prompt used",
            "review": "Use the generated Adventures Guild director, room prompt buttons, the Current Objective banner, lifecycle strip, or Adventures Guild Actions Relevant Now shortcuts to prefill branch, reward, route, XP, or finance markers; confirm exact printed amount/result manually where needed.",
            "where": "Exploration TAG prompt, Current Objective banner, and Adventures Guild Actions dialog.",
        },
        {
            "checkpoint": "Director step",
            "review": "Read the phase-specific director text first. It explains whether the current room is Entry, Side lead, Complication, Finale, Unlocked scene, or Closeout, says what kind of Adventures Guild action matters now, and links to the matching Rules Reference/Tables workflow entry.",
            "where": "Exploration prompt, Current Objective banner, Adventures Guild Actions Relevant Now, and Ongoing Quest closeout panel.",
        },
        {
            "checkpoint": "Recovery / repair",
            "review": "For old or resumed generated modules, check the I think you are here recovery line. Use Refresh narrative to reload local PDF-derived scene text, rebuild missing app prompts, normalize legacy log wording, and report what changed.",
            "where": "Current Objective banner, generated Adventures Guild Director panels, and /api/sessions/{id}/tag-repair-guidance.",
        },
        {
            "checkpoint": "Lifecycle visible",
            "review": "Check Entry, Side lead, Complication, Finale, Route, Reward, XP, and Closeout chips so the player knows what has actually been seen or recorded.",
            "where": "Current Objective banner and Ongoing Quest generated closeout panel.",
        },
        {
            "checkpoint": "Route marker recorded",
            "review": "Record parley, hostile branch, Clue gate, skip, unlocked scene, solo restriction, or final route before closing the lead.",
            "where": "TAG Signoff panel and campaign route log.",
        },
        {
            "checkpoint": "Closeout resolved",
            "review": "Use the five-step closeout wizard: objective, route/reward, XP, Guild/banking/guidance, then signoff. Signoff stores warnings if any remain.",
            "where": "Ongoing Quest generated closeout panel, Dashboard Guidance, Guild Management, Banking and Finance, Go Adventure Closeout Gate.",
        },
    ]
    data["tag_closeout_checklist_automation_table"] = [
        {
            "check": "Generated lead",
            "status_source": "CampaignState.tag_generated_adventure_ids",
            "action": "Create an Adventures Guild module from Go Adventure or Guild Management, then confirm it is the intended lead.",
            "rules_boundary": "App records the lead id; the player/PDF remains authority for exact scene interpretation.",
        },
        {
            "check": "Route / branch marker",
            "status_source": "CampaignState.tag_adventure_routes",
            "action": "Use Adventures Guild Actions to record parley, Clue gates, skipped scenes, unlocked scenes, final route, or solo restrictions.",
            "rules_boundary": "Markers summarize the branch choice; they do not replace printed room text.",
        },
        {
            "check": "XP markers",
            "status_source": "CampaignState.tag_xp_markers",
            "action": "Award, roll, dismiss, or manually sign off pending XP before the next adventure.",
            "rules_boundary": "Manual signoff records player review when the printed scene controls the exact award.",
        },
        {
            "check": "Guild obligations",
            "status_source": "CampaignState.tag_closeout_tasks category guild",
            "action": "Open Guild Management for loot share, upkeep, reroll reset, resurrection funding, and leaving restrictions.",
            "rules_boundary": "Guild controls automate supported arithmetic; manual signoff is for rules already checked by the player.",
        },
        {
            "check": "Banking / storage",
            "status_source": "CampaignState.tag_closeout_tasks category finance/storage",
            "action": "Open Banking and Finance for bank robbery, hidden trove risk, stolen trove recovery, inheritance, and storage consequences.",
            "rules_boundary": "App workflow points to the relevant action; exact PDF text is not copied into the checklist.",
        },
        {
            "check": "Guidance actions",
            "status_source": "CampaignState.guidance_tasks",
            "action": "Complete, defer, dismiss, or reopen guidance from Dashboard Guidance / Log or Campaign Management.",
            "rules_boundary": "Guidance is app-owned campaign bookkeeping and remains in the campaign chronicle.",
        },
    ]
    data["tag_generated_prompt_playtest_table"] = [
        {
            "surface": "Generated room prompt guide",
            "shown_in": "Exploration Adventures Guild scene prompt panel and Current Objective banner.",
            "player_use": "Explains why the lead exists, how to use the room prompt, which immediate action matters, and which Adventures Guild Action buttons can prefill the exact branch, route, XP, reward, service, purchase, or finance state for that lead. The director panel gives phase-specific next-step guidance and a lead-type playbook; the lifecycle strip shows entry, side lead, complication, finale, route, reward, XP, and closeout status.",
            "pdf_boundary": "Guide text is app-authored; exact printed scene text and reward values stay with the PDF/player signoff.",
        },
        {
            "surface": "Local narrative override file",
            "shown_in": "Generated The Adventures Guild module creation.",
            "player_use": "DATA_DIR/tag_scene_narrative_overrides.json can override generated objectives, room titles, room descriptions, and room logs with user-edited local text. It also stores all extracted Scenes separately, records inline go-to Scene branch targets, and can add a per-rumor scene_graph to generated modules so branch choices remain separate scenes instead of one flattened spoiler block.",
            "pdf_boundary": "The committed app seeds a template only. Exact copied PDF prose belongs in the user's local DATA_DIR file and is not redistributed by the repository.",
        },
        {
            "surface": "Rules PDF extraction status",
            "shown_in": "Developer > Rules PDF Import.",
            "player_use": "Shows uploaded PDF count, override-file path, extracted rumor count, extracted scene count, extracted branch count, suspected cut-off extraction warnings, last override-file modified time, and whether the local file has a parse error.",
            "pdf_boundary": "The status reads local user data beside game.db. Exact copied PDF prose is not committed, bundled, or redistributed.",
        },
        {
            "surface": "Extracted scene branch buttons",
            "shown_in": "Generated Adventures Guild room prompts, Current Objective, and Relevant Now actions.",
            "player_use": "When local scene_graph metadata contains go-to Scene branches, the final/current scene prompt shows those branches as route buttons. Clicking a branch records the route, updates the active session manifest, opens or refreshes the unlocked scene room with the extracted target Scene text, and exposes any next branches from that target scene.",
            "pdf_boundary": "The app follows the branch the player selected; it does not auto-choose between printed options. Exact rewards, saves, combat consequences, and optional choices still require the player/PDF decision.",
        },
        {
            "surface": "Prompt action buttons and Relevant Now shortcuts",
            "shown_in": "Generated Adventures Guild rooms and Adventures Guild Actions dialog.",
            "player_use": "Prefills Adventures Guild Actions for lead-specific choices, purchases, services, side rewards, Clue gates, route rewrites, XP markers, and profile-specific procedure rolls. Specific lead actions now replace generic final-route/reward/XP boilerplate when the profile knows what the scene offers; older modules still get repaired fallback metadata.",
            "pdf_boundary": "Buttons prefill state only; the player still confirms exact amounts/results.",
        },
        {
            "surface": "Fixed-result playtest selector",
            "shown_in": "The Adventures Guild Maps and Adventure Leads generator.",
            "player_use": "Result defaults to Random for normal rules play. During playtesting, choose a specific Rumor 1-12, Treasure Map 1-6, Thematic Dungeon 1-6, or Guild Job 1-6 to regenerate the exact PDF branch being checked.",
            "pdf_boundary": "This is a testing convenience only. Random remains the rules-faithful default, and printed choices inside the selected result are still explicit player/PDF decisions.",
        },
        {
            "surface": "Finale mode profiles",
            "shown_in": "Generated Rumor and Guild Job modules.",
            "player_use": "Marks choice, procedure, service, and vendor finales so Bofto's star object, the false paladin-sword trail, Mutant Fish Under the Bridge, Daroc's familiar, Deoldyn's training, the leprechaun bargain, and A Portrait in Red resolve through scene-specific buttons instead of proxy foes. Sewer Search now uses the named thief final boss instead of a sewer-danger proxy. Generated Adventures Guild imports block the core Epic Rewards table; use the scene reward/action buttons and closeout signoff instead.",
            "pdf_boundary": "The app may name supported choices and checked costs from indexed scene metadata, but the player still confirms receiver, spell, eligibility, exact optional ambush/hostile turns, and any printed consequence before applying it. Do not add a core Epic Reward unless a non-TAG quest source explicitly grants one.",
        },
        {
            "surface": "Recovery and repair",
            "shown_in": "Current Objective banner and generated Adventures Guild Director panels.",
            "player_use": "Shows I think you are here with confidence, warns when generic prompt metadata was repaired, and offers Refresh narrative for older generated modules. Refresh reports whether local PDF narrative, prompt metadata, scene branches, contact text, or legacy log wording changed. Resumed sessions auto-refresh generated Adventures Guild prompt metadata where safe.",
            "pdf_boundary": "Refresh uses only the local override file and app metadata. It does not choose printed branches, invent scene text, or resolve rewards.",
        },
        {
            "surface": "Generated adventure diagnostics",
            "shown_in": "Adventure View toolbar and Ongoing Quest generated closeout panel.",
            "player_use": "Shows prompt coverage, current room prompt/action status, local narrative extraction status, scene-branch counts, missing prompt errors, missing branch-target errors, and why the Advanced / Manual Actions fallback is visible. A recursive generated-module audit covers all 12 Rumors, 6 Treasure Maps, 6 Thematic Dungeons, and 6 Guild Jobs for scene-specific actions and stale duplicate text. Copy Narrative Report copies the exact player-facing Narrative first and debugging context afterwards.",
            "pdf_boundary": "Diagnostics report app metadata only. They do not reveal copied PDF prose or choose between printed branch options.",
        },
        {
            "surface": "Generated reward policy",
            "shown_in": "Exploration Adventures Guild scene prompt panel and Copy Narrative Report.",
            "player_use": "Every generated Adventures Guild module declares one reward class: No loot, Scene reward button, Purchase/service only, No automatic room loot, or Handoff dungeon loot. This makes it clear when a compact imported module will not roll ordinary 4AD combat treasure and which visible button or handoff should supply the reward instead.",
            "pdf_boundary": "The policy is an app-authored audit label. It does not invent rewards; exact treasure, gp, item, XP, purchase, or service outcomes still come from the PDF/player choice.",
        },
        {
            "surface": "Generated lead signoff",
            "shown_in": "Current Objective banner and Ongoing Quest generated closeout panel after generated Adventures Guild objective completion.",
            "player_use": "Records player review of route, reward, XP, Guild share, banking/storage, and closeout checks before another lead is started. The closeout panel is a five-step wizard; if route, XP, guidance, or closeout work remains, signoff records warnings instead of silently pretending the lead is clean.",
            "pdf_boundary": "Signoff records app/player review only; it does not resolve printed-rule decisions without player confirmation.",
        },
        {
            "surface": "Generated Adventures Guild Leads panel",
            "shown_in": "Go Adventure.",
            "player_use": "Lists installed Adventures Guild modules with lead type, source detail, prompt count, route markers, open closeout, and pending XP before selecting a module.",
            "pdf_boundary": "Shows metadata from generated manifests, not copied rule text.",
        },
        {
            "surface": "Adventures Guild Action Log filter",
            "shown_in": "Go Adventure.",
            "player_use": "Searches and filters route, XP, finance, Guild, branch, generated-lead, and signoff events during generated-adventure review.",
            "pdf_boundary": "Displays app logs and player-entered notes.",
        },
        {
            "surface": "Advanced / Manual Actions fallback",
            "shown_in": "Adventure View toolbar only when generated-adventure diagnostics find a missing prompt, missing scene branch target, or manual-only action.",
            "player_use": "Keeps the old full toolbox available for recovery and ambiguous PDF/player decisions, but hides it during normal play so direct Current Objective, Quest Details, and room-prompt buttons remain the primary workflow.",
            "pdf_boundary": "Manual fallback records player/app decisions; it does not automate a PDF choice that says choose.",
        },
    ]
    data["tag_generated_lead_structure_table"] = [
        {
            "structure": "dungeon",
            "when_to_use": "The PDF result tells the party to explore a dungeon, lair, cave, hideout, mine, maze, sewer, castle, or fixed room count.",
            "required_profile_fields": "module_profile.target_rooms, module_profile.procedure, final foes where printed, final_prompt_actions for rewards/capture/XP.",
            "ui_expectation": "Adventure View may use map exploration, room counters, final foe automation, and closeout signoff.",
            "checking_notes": "Verify target room count, final foe groups, treasure/reward source, and whether the objective completes by boss defeat or procedure.",
        },
        {
            "structure": "scene_chain",
            "when_to_use": "The PDF says choose/go to another Scene and the route can branch before any dungeon exists.",
            "required_profile_fields": "scene_graph, room_prompts, route actions, terminal scene actions.",
            "ui_expectation": "Current Objective and room prompts show branch buttons; the app follows selected routes but does not choose for the player.",
            "checking_notes": "Check extracted Scene targets for page-wrap completeness and keep branch choices separate, not flattened into spoilers.",
        },
        {
            "structure": "procedure",
            "when_to_use": "The PDF gives a compact resolution procedure rather than a normal dungeon, vendor, trainer, or handoff.",
            "required_profile_fields": "finale_mode procedure, module_profile procedure/signoff notes, prompt actions for each supported roll/check/reward.",
            "ui_expectation": "Current Objective shows the procedure buttons and status, while Narrative explains the situation without pretending every step is a room crawl.",
            "checking_notes": "Use for red herrings, escorts, clue spends, return-road checks, and other printed procedures that should not spawn fake proxy foes.",
        },
        {
            "structure": "vendor",
            "when_to_use": "The PDF offers items, spells, or paid bargains such as Shoes of Fast Walk or an illusion lesson.",
            "required_profile_fields": "finale_mode vendor, exact purchase actions, item/spell choice UI, cost/free-condition hover text.",
            "ui_expectation": "No proxy combat. Buttons open guided purchase/spell pickers and pay/apply only after the player confirms the choice.",
            "checking_notes": "Check item effects, price, maximum quantity, eligible receiver, and whether any free condition is printed.",
        },
        {
            "structure": "trainer",
            "when_to_use": "The PDF leads to a trainer/service rather than an exploration site, such as Deoldyn Scene 3.",
            "required_profile_fields": "lead_structure trainer, finale_mode service, entry_prompt_actions, final_prompt_actions, cost formula, eligible character rule, skill/spell choices.",
            "ui_expectation": "Training is offered immediately in the first prompt; the app filters eligible characters, pays the service cost, rolls the printed check, and applies only successful choices.",
            "checking_notes": "For Deoldyn, check TAG Scene 3: bow-capable trainee, 60 gp x Level, once per character between adventures, Deadly Accuracy or Dead Shot choice, and money spent even on failure.",
        },
        {
            "structure": "handoff",
            "when_to_use": "The PDF result tells the player to generate or play a separate adventure/dungeon outside the compact lead.",
            "required_profile_fields": "module_profile.target_rooms, handoff action, route/signoff checks, no fake proxy finale.",
            "ui_expectation": "The generated lead records the handoff and closeout state; the actual expanded dungeon is generated or played separately.",
            "checking_notes": "For Shinta/Agaratha, check Scene 4 champion eligibility and Scene 7 solo ten-room Bandit Hideout procedure: minion counts -1 minimum 1, Riff-Raff Final Boss with no count reduction, and Agaratha only after return.",
        },
    ]
    data["tag_rumor_playthrough_audit_table"] = [
        {
            "surface": "Rumor audit metadata",
            "shown_in": "Generated Adventures Guild Rumor manifests and exploration prompt panels.",
            "player_use": "Carries rumor number, play focus, entry guidance, complication narrative, finale mode, scene-specific action buttons, and signoff reminders for all twelve Rumor Scene leads.",
            "pdf_boundary": "App-authored atmosphere and workflow notes only; exact scene text, rolls, rewards, and consequences remain with the PDF/player signoff.",
        },
        {
            "surface": "TAG Rumor Leads panel",
            "shown_in": "Go Adventure.",
            "player_use": "Lists installed Rumor modules, scene/page metadata, prompt counts, route/reward/XP signoff reminders, and quick Select Rumor/Rules/Table actions.",
            "pdf_boundary": "Displays generated manifest metadata and app checklist text, not copied scene prose.",
        },
        {
            "surface": "Rumor Signoff Checklist",
            "shown_in": "Go Adventure.",
            "player_use": "Guides the post-adventure review: entry choice, complication branch, final reward, XP, Guild obligations, banking/storage, and closeout tasks.",
            "pdf_boundary": "Checklist points to what the player should verify; it does not quote or replace the printed Adventures Guild scene.",
        },
        {
            "surface": "Prompt checklist",
            "shown_in": "Exploration room detail panel.",
            "player_use": "Shows room-specific reminders beside Adventures Guild Action buttons so the player knows why a branch, Clue cost, route rewrite, reward, or XP marker matters.",
            "pdf_boundary": "Buttons and reminders prefill app state only; the player confirms exact values/results.",
        },
    ]
    data["tag_treasure_map_playthrough_audit_table"] = [
        {
            "surface": "Treasure Map audit metadata",
            "shown_in": "Generated Adventures Guild Treasure Map manifests and exploration prompt panels.",
            "player_use": "Carries destination number, play focus, entry guidance, complication guidance, finale guidance, destination procedure reminders, closeout checks, player-facing separation between current-room Claim Treasure and Map Leads To procedure handling, and compatibility translation for older generated notes.",
            "pdf_boundary": "App-authored atmosphere and workflow notes only; exact map results, room counts, rewards, and special procedures remain with the PDF/player signoff.",
        },
        {
            "surface": "TAG Treasure Map Leads panel",
            "shown_in": "Go Adventure.",
            "player_use": "Lists installed Treasure Map modules with destination metadata, prompt counts, procedure/reward/XP signoff reminders, and quick Select Map/Rules/Table actions.",
            "pdf_boundary": "Displays generated manifest metadata and app checklist text, not copied table prose.",
        },
        {
            "surface": "Treasure Map Signoff Checklist",
            "shown_in": "Go Adventure.",
            "player_use": "Guides review of Follow Map result, Map Leads To destination, destination procedure, treasure transfer, XP, Guild share, banking/storage, and closeout tasks.",
            "pdf_boundary": "Checklist points to what the player should verify; it does not quote or replace the printed TAG tables.",
        },
        {
            "surface": "Destination prompt checklist",
            "shown_in": "Exploration room detail panel.",
            "player_use": "Shows room-specific reminders beside Adventures Guild Action buttons for cave count, temple reward, camp approach, deferred structure treasure, boss-only conversion, lich setup, and whether ordinary room treasure should simply be claimed. Safe procedure prompts can run directly from the room prompt while Adventures Guild Actions remains available for edits.",
            "pdf_boundary": "Buttons and reminders prefill app state only; the player confirms exact values/results.",
        },
        {
            "surface": "Active quest procedure tracker",
            "shown_in": "Ongoing Quests during Lady in White Treasure Map play.",
            "player_use": "Shows the selected Map Leads To procedure as a guided checklist, explains why the player is pressing the action, records the result on the active quest, marks completed procedure rows, displays any room target, separates ordinary Claim Treasure from the destination procedure, and lets automated destination procedures complete from play state where possible.",
            "pdf_boundary": "Buttons and reminders prefill app state only; the player confirms exact values/results.",
        },
        {
            "surface": "Current objective banner",
            "shown_in": "Exploration log/command area.",
            "player_use": "Puts the next useful action beside the Narrative: resolve combat/traps first, claim ordinary room treasure with Claim Treasure, run or review the current Treasure Map procedure, sign off destination choices, or claim the quest reward once the procedure is complete.",
            "pdf_boundary": "Buttons and reminders prefill app state only; the player confirms exact values/results.",
        },
    ]
    data["tag_thematic_dungeon_playthrough_audit_table"] = [
        {
            "surface": "Thematic Dungeon audit metadata",
            "shown_in": "Generated Adventures Guild Thematic Dungeon manifests and exploration prompt panels.",
            "player_use": "Carries theme number, play focus, entry guidance, complication guidance, finale guidance, target-room procedure reminders, and closeout checks for all six Thematic Dungeon results.",
            "pdf_boundary": "App-authored atmosphere and workflow notes only; exact room targets, replacement rolls, rewards, and special procedures remain with the PDF/player signoff.",
        },
        {
            "surface": "TAG Thematic Dungeon Leads panel",
            "shown_in": "Go Adventure.",
            "player_use": "Lists installed Thematic Dungeon modules with theme metadata, prompt counts, procedure/reward/XP signoff reminders, and quick Select Theme/Rules/Table actions.",
            "pdf_boundary": "Displays generated manifest metadata and app checklist text, not copied table prose.",
        },
        {
            "surface": "Thematic Dungeon Signoff Checklist",
            "shown_in": "Go Adventure.",
            "player_use": "Guides review of target rooms, theme procedure rolls, final-room exceptions, reward, XP, Guild share, banking/storage, and closeout tasks.",
            "pdf_boundary": "Checklist points to what the player should verify; it does not quote or replace the printed TAG theme rules.",
        },
        {
            "surface": "Theme prompt checklist",
            "shown_in": "Exploration room detail panel.",
            "player_use": "Shows room-specific reminders beside Adventures Guild Action buttons for cave-ins, undead replacement, boulder throw, dragon reveal, prisoner table, maze checks, stolen goods, and capture-alive choices.",
            "pdf_boundary": "Buttons and reminders prefill app state only; the player confirms exact values/results.",
        },
    ]
    data["character_management_readiness_table"] = [
        {
            "area": "Roster filters",
            "ui_behavior": "Search by name, class, party, campaign, guild, troupe, home settlement, inventory, spells, statuses, gold, Clues, and setup warnings.",
            "setup_value": "Find injured, fallen, active-session locked, under-equipped, or context-mismatched characters before starting an adventure.",
            "rules_boundary": "App dashboard workflow; printed character rules remain in class/equipment references.",
        },
        {
            "area": "Weapon slots",
            "ui_behavior": "Melee, off-hand, and missile defaults are saved through the existing weapon-defaults endpoint.",
            "setup_value": "Go Adventure flags carried missile weapons without missile defaults and stale assigned weapons no longer in inventory.",
            "rules_boundary": "Backend weapon legality remains the authority during play.",
        },
        {
            "area": "Armor and shield",
            "ui_behavior": "Detected from inventory and shown on the full sheet.",
            "setup_value": "Visible before play without adding new persistent armor/shield slot fields.",
            "rules_boundary": "Existing combat/save systems still apply inventory-based armor and shield rules.",
        },
        {
            "area": "World context",
            "ui_behavior": "Full sheets show campaign, guild, troupe, party, and home settlement with links to management pages.",
            "setup_value": "Warnings flag party/troupe/campaign/guild mismatches before Go Adventure.",
            "rules_boundary": "App world-builder bookkeeping; not a printed TAG rule.",
        },
    ]
    data["go_adventure_setup_readiness_table"] = [
        {
            "check": "Party",
            "blocking": "No party selected or party does not have exactly four members.",
            "warning": "",
            "resolution": "Create or edit a saved party in Party Management.",
        },
        {
            "check": "Adventure module",
            "blocking": "Imported or AI adventure type selected without an installed module.",
            "warning": "",
            "resolution": "Select an installed module or create an Adventures Guild lead first.",
        },
        {
            "check": "Character state",
            "blocking": "Fallen character or active-session lock in selected party.",
            "warning": "Injured members, equipment warnings, and context mismatches.",
            "resolution": "Heal/resurrect, delete/resume active sessions, or use Character/Party/Troupe Management to clean up.",
        },
        {
            "check": "Map settings",
            "blocking": "Map element cap is zero or negative.",
            "warning": "",
            "resolution": "Set a positive map cap in Go Adventure or Settings.",
        },
    ]
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
    monster_data = rules.monsters()
    data["monster_bestiary_table"] = [
        {
            "category": table_key,
            "name": row.get("name", ""),
            "level": row.get("level", ""),
            "life": row.get("life", ""),
            "tags": ", ".join(row.get("tags", [])) if isinstance(row.get("tags"), list) else "",
            "source_page": row.get("source_page", ""),
        }
        for table_key, rows in monster_data.items()
        if table_key != "reaction_tables" and isinstance(rows, list)
        for row in rows
        if isinstance(row, dict)
    ]
    reaction_tables = monster_data.get("reaction_tables", {})
    data["monster_reaction_tables"] = [
        {"table": table_name, "roll": row.get("roll", ""), "result": row.get("result", "")}
        for table_name, rows in reaction_tables.items()
        if isinstance(rows, list)
        for row in rows
        if isinstance(row, dict)
    ] if isinstance(reaction_tables, dict) else []
    data["map_elements_table"] = [
        {
            "catalog": catalog,
            "key": tile.key,
            "name": tile.name,
            "native_exits": ", ".join(exit_def.direction for exit_def in tile.exits),
            "room_codes": ", ".join(tile.room_codes),
            "implementation_status": tile.implementation_status,
        }
        for catalog in ("ee", "forsaken_depths", "forsaken_depths_rivers")
        for tile in rules.tiles(catalog).values()
    ]
    data["icon_registry_table"] = [
        {
            "id": icon.id,
            "label": icon.label,
            "category": icon.category,
            "file": icon.file,
            "description": icon.description,
        }
        for icon in _icons_payload()
    ]
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
    from .engine.tag_campaign import load_campaign, tag_guild_benefits_active

    catalog = rules.equipment_shop()
    campaign = load_campaign(store)
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
                tag_guild_discount=tag_guild_benefits_active(campaign),
            ),
            "notes": (
                "Buy before or between adventures (Expanded Edition pp.81-88). "
                "Sell equipment at half list price unless a fixed resale value is listed. "
                "Roster gold is home bank gold; only dungeon-carried gold is limited to 200gp per hero. "
                "TAG Guild members receive the TAG p.68 10% mundane equipment discount."
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
    files: set[str] = set()
    for root in (settings.packaged_assets_dir, settings.user_assets_dir):
        icon_dir = root / "icons" / "user"
        if not icon_dir.exists():
            continue
        files.update(
            f"icons/user/{path.relative_to(icon_dir).as_posix()}"
            for path in icon_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in ICON_FILE_EXTENSIONS
        )
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
    from .engine.tag_campaign import DEFAULT_WORLD_CAMPAIGN_ID, DEFAULT_WORLD_GUILD_ID, DEFAULT_WORLD_TROUPE_ID, load_campaign

    load_campaign(store)
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
        campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
        guild_id=DEFAULT_WORLD_GUILD_ID,
        troupe_id=DEFAULT_WORLD_TROUPE_ID,
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
    if payload.default_melee_weapon == "":
        character.default_melee_weapon = None
        messages.append(f"{character.name} clears default melee weapon.")
    elif payload.default_melee_weapon is not None:
        ok, message = set_weapon_default(
            character,
            item_name=payload.default_melee_weapon,
            weapon_kind="melee",
            melee_slot="primary",
        )
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        messages.append(message)
    if payload.default_melee_weapon_secondary == "":
        character.default_melee_weapon_secondary = None
        messages.append(f"{character.name} clears default secondary melee weapon.")
    elif payload.default_melee_weapon_secondary is not None:
        ok, message = set_weapon_default(
            character,
            item_name=payload.default_melee_weapon_secondary,
            weapon_kind="melee",
            melee_slot="secondary",
        )
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        messages.append(message)
    if payload.default_missile_weapon == "":
        character.default_missile_weapon = None
        messages.append(f"{character.name} clears default missile weapon.")
    elif payload.default_missile_weapon is not None:
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
    from .engine.tag_campaign import load_campaign

    character = store.get("characters", character_id, Character.model_validate)
    if character is None:
        raise HTTPException(status_code=404, detail="Character not found.")
    session, member, carried_gold = _prepare_roster_service_character(character, service_label="Equipment shopping")
    catalog = rules.equipment_shop()
    from .engine.tag_campaign import tag_guild_benefits_active

    campaign = load_campaign(store)
    ok, message = buy_equipment(
        character,
        catalog,
        item_key=payload.item_key,
        quantity=payload.quantity,
        potion_recipe_available=_secret_available_for_character(character, "potion_recipe"),
        tag_guild_discount=tag_guild_benefits_active(campaign),
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
    from .engine.tag_campaign import DEFAULT_WORLD_CAMPAIGN_ID, DEFAULT_WORLD_GUILD_ID, DEFAULT_WORLD_TROUPE_ID, load_campaign, save_campaign

    campaign = load_campaign(store)
    troupe_id = payload.troupe_id or DEFAULT_WORLD_TROUPE_ID
    characters = _load_characters(payload.character_ids)
    if len({character.id for character in characters}) != 4:
        raise HTTPException(status_code=400, detail="Choose four different characters.")
    busy: list[str] = []
    for character in characters:
        busy_session_id = character_busy_session_id(character, store)
        if busy_session_id:
            busy.append(f"{character.name} is already in an active adventure.")
        if character.party_id:
            busy.append(f"{character.name} is already in party {_party_name(character.party_id)}. Remove them from that party first.")
        if character.troupe_id and character.troupe_id != troupe_id:
            busy.append(f"{character.name} belongs to another troupe. Assign them to this troupe first; the app will warn before removing them from any party.")
    if busy:
        raise HTTPException(status_code=409, detail=" ".join(busy))
    timestamp = now_utc()
    party = Party(
        id=new_id(),
        name=payload.name.strip(),
        character_ids=payload.character_ids,
        campaign_id=next((item.campaign_id for item in campaign.world_troupes if item.id == troupe_id), DEFAULT_WORLD_CAMPAIGN_ID),
        troupe_id=troupe_id,
        created_at=timestamp,
        updated_at=timestamp,
    )
    store.save("parties", party)
    troupe_guild_id = next((item.guild_id for item in campaign.world_troupes if item.id == troupe_id), DEFAULT_WORLD_GUILD_ID)
    for character in characters:
        character.party_id = party.id
        character.campaign_id = party.campaign_id
        character.guild_id = troupe_guild_id
        character.troupe_id = troupe_id
        character.updated_at = timestamp
        store.save("characters", character)
    for troupe in campaign.world_troupes:
        if troupe.id == troupe_id and party.id not in troupe.party_ids:
            troupe.party_ids.append(party.id)
        if troupe.id == troupe_id:
            for character in characters:
                if character.id not in troupe.member_character_ids:
                    troupe.member_character_ids.append(character.id)
    save_campaign(store, campaign)
    return party


@app.put("/api/parties/{party_id}")
async def update_party(party_id: str, payload: PartyCreate) -> Party:
    from .engine.tag_campaign import DEFAULT_WORLD_CAMPAIGN_ID, DEFAULT_WORLD_GUILD_ID, DEFAULT_WORLD_TROUPE_ID, load_campaign, save_campaign

    campaign = load_campaign(store)
    existing = store.get("parties", party_id, Party.model_validate)
    if existing is None:
        raise HTTPException(status_code=404, detail="Party not found.")
    troupe_id = payload.troupe_id or existing.troupe_id or DEFAULT_WORLD_TROUPE_ID
    characters = _load_characters(payload.character_ids)
    if len({character.id for character in characters}) != 4:
        raise HTTPException(status_code=400, detail="Choose four different characters.")
    busy: list[str] = []
    for character in characters:
        busy_session_id = character_busy_session_id(character, store)
        if busy_session_id:
            busy.append(f"{character.name} is already in an active adventure.")
        if character.party_id and character.party_id != party_id:
            busy.append(f"{character.name} is already in party {_party_name(character.party_id)}. Remove them from that party first.")
        if character.troupe_id and character.troupe_id != troupe_id:
            busy.append(f"{character.name} belongs to another troupe. Assign them to this troupe first; the app will warn before removing them from any party.")
    if busy:
        raise HTTPException(status_code=409, detail=" ".join(busy))
    previous_ids = set(existing.character_ids)
    existing.name = payload.name.strip()
    existing.character_ids = payload.character_ids
    existing.campaign_id = next((item.campaign_id for item in campaign.world_troupes if item.id == troupe_id), DEFAULT_WORLD_CAMPAIGN_ID)
    existing.troupe_id = troupe_id
    existing.updated_at = now_utc()
    store.save("parties", existing)
    troupe_guild_id = next((item.guild_id for item in campaign.world_troupes if item.id == troupe_id), DEFAULT_WORLD_GUILD_ID)
    for old_id in previous_ids - set(payload.character_ids):
        old = store.get("characters", old_id, Character.model_validate)
        if old is not None and old.party_id == existing.id:
            old.party_id = None
            old.updated_at = existing.updated_at
            store.save("characters", old)
    for character in characters:
        character.party_id = existing.id
        character.campaign_id = existing.campaign_id
        character.guild_id = troupe_guild_id
        character.troupe_id = troupe_id
        character.updated_at = existing.updated_at
        store.save("characters", character)
    for troupe in campaign.world_troupes:
        if troupe.id == troupe_id and existing.id not in troupe.party_ids:
            troupe.party_ids.append(existing.id)
        if troupe.id == troupe_id:
            for character in characters:
                if character.id not in troupe.member_character_ids:
                    troupe.member_character_ids.append(character.id)
        elif troupe.id != troupe_id and existing.id in troupe.party_ids:
            troupe.party_ids = [item for item in troupe.party_ids if item != existing.id]
            troupe.member_character_ids = [item for item in troupe.member_character_ids if item not in payload.character_ids]
    save_campaign(store, campaign)
    return existing


@app.delete("/api/parties/{party_id}")
async def delete_party(party_id: str) -> dict[str, bool]:
    from .engine.tag_campaign import load_campaign, save_campaign

    party = store.get("parties", party_id, Party.model_validate)
    if party is not None:
        for character_id in party.character_ids:
            character = store.get("characters", character_id, Character.model_validate)
            if character is not None and character.party_id == party_id:
                character.party_id = None
                character.updated_at = now_utc()
                store.save("characters", character)
        campaign = load_campaign(store)
        for troupe in campaign.world_troupes:
            if party_id in troupe.party_ids:
                troupe.party_ids = [item for item in troupe.party_ids if item != party_id]
        save_campaign(store, campaign)
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
    pdf_assessments = load_adventure_pdf_assessments(settings.data_dir)
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
    seen_pdf_ids: set[str] = set()
    for source_kind, directory in adventure_pdf_source_dirs(settings.root_dir, settings.data_dir):
        for pdf in sorted(directory.glob("*.pdf")):
            key = f"{source_kind}:{pdf.name}"
            assessment = pdf_assessments.get(key, {})
            pdf_id = str(assessment.get("id") or _safe_pdf_adventure_id(pdf, source_kind))
            if pdf_id in seen_pdf_ids:
                continue
            seen_pdf_ids.add(pdf_id)
            notes = "PDF source found; scan it, then create a reviewed adventure manifest before play."
            if assessment:
                detected = str(assessment.get("detected_type") or "unknown").replace("_", " ")
                status = str(assessment.get("conversion_status") or "source_pdf_assessed").replace("_", " ")
                action = str(assessment.get("recommended_action") or "Create a reviewed manifest before play.")
                notes = f"PDF source assessed: {detected} ({status}). {action}"
            adventures.append(
                AdventureDescriptor(
                    id=pdf_id,
                    name=str(assessment.get("title") or _title_from_pdf_name(pdf)),
                    source=str(assessment.get("source_path") or _relative_source_path(pdf)),
                    playable=False,
                    notes=notes,
                    pdf_source=True,
                    pdf_detected_type=str(assessment.get("detected_type") or ""),
                    pdf_confidence=str(assessment.get("confidence") or ""),
                    pdf_conversion_status=str(assessment.get("conversion_status") or "source_pdf_unscanned"),
                    pdf_recommended_action=str(assessment.get("recommended_action") or ""),
                    pdf_page_count=int(assessment.get("page_count") or 0),
                    pdf_text_extractable=bool(assessment.get("text_extractable") or False),
                    pdf_source_kind=str(assessment.get("source_kind") or source_kind),
                    pdf_warnings=[str(item) for item in assessment.get("warnings", []) if item],
                    pdf_map_signals=int(assessment.get("map_signals") or 0),
                    pdf_table_signals=int(assessment.get("table_signals") or 0),
                    pdf_foe_signals=int(assessment.get("foe_signals") or 0),
                    pdf_class_signals=int(assessment.get("class_signals") or 0),
                    pdf_numbered_location_signals=int(assessment.get("numbered_location_signals") or 0),
                    pdf_package_recommendation=str(assessment.get("package_recommendation") or ""),
                )
            )
    return adventures


@app.post("/api/adventures/pdf-sources/scan")
async def scan_adventure_pdf_sources(payload: dict | None = None) -> dict[str, Any]:
    force = bool((payload or {}).get("force"))
    try:
        return scan_new_adventure_pdfs(settings.root_dir, settings.data_dir, force=force)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/adventures/packages")
async def adventure_packages() -> dict[str, Any]:
    return {"packages": list_adventure_packages(settings.data_dir)}


@app.get("/api/adventures/packages/{package_id}")
async def adventure_package_detail(package_id: str) -> dict[str, Any]:
    try:
        package = package_detail(settings.data_dir, package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"package": package}


@app.post("/api/adventures/packages/{package_id}/review")
async def save_adventure_package_review(package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        package = update_adventure_package_review(settings.data_dir, package_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"package": package}


@app.post("/api/adventures/packages/{package_id}/extract-candidates")
async def extract_adventure_package_candidate_records(package_id: str) -> dict[str, Any]:
    try:
        package = extract_adventure_package_candidates(settings.root_dir, settings.data_dir, package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"package": package}


@app.post("/api/adventures/packages/{package_id}/extract-artwork")
async def extract_adventure_package_artwork_library(package_id: str) -> dict[str, Any]:
    try:
        package = extract_adventure_package_artwork(settings.root_dir, settings.data_dir, package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"package": package}


@app.delete("/api/adventures/packages/{package_id}")
async def remove_adventure_package_review(package_id: str) -> dict[str, Any]:
    try:
        return delete_adventure_package(settings.data_dir, package_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/adventures/pdf-sources/{pdf_id}/package")
async def create_adventure_package_from_pdf(pdf_id: str, payload: dict | None = None) -> dict[str, Any]:
    extract_maps = bool((payload or {}).get("extract_maps", True))
    try:
        package = create_or_refresh_package_from_pdf(
            settings.root_dir,
            settings.data_dir,
            pdf_id,
            extract_maps=extract_maps,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"package": package}


@app.post("/api/adventures/packages/{package_id}/pins")
async def save_adventure_package_pin(package_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        package = upsert_map_pin(settings.data_dir, package_id, payload)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"package": package}


@app.get("/api/adventures/packages/{package_id}/maps/{filename}")
async def adventure_package_map_asset(package_id: str, filename: str) -> FileResponse:
    safe_filename = Path(filename).name
    path = package_map_asset_path(settings.data_dir, package_id, safe_filename)
    try:
        resolved = path.resolve()
        adventure_root = (settings.installed_adventures_dir / package_id).resolve()
        legacy_root = (settings.user_assets_dir / "adventures" / package_id / "maps").resolve()
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Map asset not found.") from exc
    try:
        resolved.relative_to(adventure_root)
        allowed = True
    except ValueError:
        try:
            resolved.relative_to(legacy_root)
            allowed = True
        except ValueError:
            allowed = False
    if not allowed:
        raise HTTPException(status_code=400, detail="Invalid map asset path.")
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Map asset not found.")
    return FileResponse(resolved)


@app.get("/api/adventures/packages/{package_id}/artwork/{filename}")
async def adventure_package_artwork_asset(package_id: str, filename: str) -> FileResponse:
    safe_filename = Path(filename).name
    path = package_artwork_asset_path(settings.data_dir, package_id, safe_filename)
    try:
        resolved = path.resolve()
        adventure_root = (settings.installed_adventures_dir / package_id).resolve()
    except OSError as exc:
        raise HTTPException(status_code=404, detail="Artwork asset not found.") from exc
    try:
        resolved.relative_to(adventure_root)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid artwork asset path.") from exc
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Artwork asset not found.")
    return FileResponse(resolved)


@app.delete("/api/adventures/packages/{package_id}/maps/{map_id}/pins/{pin_id}")
async def remove_adventure_package_pin(package_id: str, map_id: str, pin_id: str) -> dict[str, Any]:
    try:
        package = delete_map_pin(settings.data_dir, package_id, map_id, pin_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"package": package}


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
    allow_start_anyway = _parse_bool(payload.get("allow_start_anyway"), default=False)
    gate = campaign_closeout_gate(campaign, party.id)
    hard_blocks = [issue for issue in gate["issues"] if issue["severity"] == "block"]
    if hard_blocks:
        raise HTTPException(status_code=409, detail=" ".join(f"{issue['title']}: {issue['body']}" for issue in hard_blocks))
    if gate["requires_override"] and not allow_start_anyway:
        raise HTTPException(
            status_code=409,
            detail="Closeout review requires explicit override before starting: "
            + " ".join(f"{issue['title']}: {issue['body']}" for issue in gate["issues"] if issue["severity"] == "override"),
        )
    tag_banking_enabled = campaign.tag_banking_enabled
    profile = None
    if adventure_id in {"random", "courtship-demesne"}:
        try:
            profile = resolve_profile_for_adventure(
                adventure_id,
                profile_id=ruleset_profile_id,
                ruleset=ruleset if adventure_id == "random" else None,
                courtship_enabled=courtship_enabled if adventure_id == "random" else None,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if "fiendish_foes_enabled" not in payload and adventure_id == "random":
        assert profile is not None
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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
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
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        assert profile is not None
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
    if _refresh_generated_tag_manifest_on_resume(session):
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


TAG_TREASURE_MAP_DESTINATIONS: dict[str, dict[str, Any]] = {
    "map_cave_room_count": {
        "destination": 1,
        "label": "Underground caves room target",
        "next_action": "Target recorded. Explore normally; the app counts rooms, makes the target room the Treasure Map final Boss room, and completes the objective after that Boss is defeated.",
    },
    "map_temple_idol": {
        "destination": 2,
        "label": "Forgotten temple idol reward",
        "next_action": "Record the idol reward, then resolve any separate temple scroll or final treasure handling called for by your printed procedure.",
    },
    "map_temple_scroll": {
        "destination": 2,
        "label": "Forgotten temple scroll",
        "next_action": "Record the scroll result and finish the temple destination closeout before turning in the quest reward.",
    },
    "map_humanoid_report": {
        "destination": 3,
        "label": "Hostile camp report",
        "next_action": "The camp was handled as a report reward. Record the result, then close out storage, Guild share, XP, and quest reward only if your table result allows it.",
    },
    "map_humanoid_stealth": {
        "destination": 3,
        "label": "Hostile camp stealth raid",
        "next_action": "Apply the stealth raid outcome from Adventures Guild Actions, then record any loot, danger, or XP consequences before the quest reward.",
    },
    "map_humanoid_forces": {
        "destination": 3,
        "label": "Hostile camp battle forces",
        "next_action": "Add or resolve the camp forces generated by the procedure, then close out reward, XP, and storage after the fight.",
    },
    "map_structure_rooms": {
        "destination": 4,
        "label": "Abandoned structure room target",
        "next_action": "Use the rolled room count as the structure target. Continue exploring until the target room, then resolve the destination closeout.",
    },
    "map_lich_death_magic": {
        "destination": 6,
        "label": "Lich death magic check",
        "next_action": "Resolve the lich's death-magic risk before the final treasure closeout.",
    },
    "map_lich_life": {
        "destination": 6,
        "label": "Lich Life adjustment",
        "next_action": "Apply the lich Life adjustment to the final foe, then resolve the chamber and treasure closeout.",
    },
    "map_lich_treasure": {
        "destination": 6,
        "label": "Lich treasure closeout",
        "next_action": "Record the lich treasure result, then finish storage, Guild share, XP, and quest reward checks.",
    },
}


TAG_TREASURE_MAP_AUTO_COMPLETE_ACTIONS = {
    "map_humanoid_report",
    "map_lich_treasure",
}

TAG_SINGLE_RUN_BRANCH_ACTIONS = {
    "map_cave_room_count",
    "map_structure_rooms",
}


def _is_tag_treasure_map_quest(quest: Any) -> bool:
    if quest is None:
        return False
    quest_text = f"{getattr(quest, 'key', '')} {getattr(quest, 'description', '')}".lower()
    return "treasure map" in quest_text


def _is_generated_tag_session(session: SessionState) -> bool:
    params = ((session.imported_manifest or {}).get("source") or {}).get("parameters") or {}
    if not isinstance(params, dict):
        return False
    tag_ref = params.get("tag_reference") if isinstance(params, dict) else None
    return isinstance(tag_ref, dict) or params.get("origin") == "Tales from the Adventurers' Guild"


def _update_session_tag_procedure_state(session: SessionState, branch_action: str, entry: Any) -> None:
    quest = session.active_quest
    if not _is_tag_treasure_map_quest(quest):
        return
    procedure = TAG_TREASURE_MAP_DESTINATIONS.get(branch_action)
    if procedure is None:
        return
    state = dict(quest.tag_procedure_state or {})
    result_text = str(getattr(entry, "result_text", "") or "")
    total = getattr(entry, "total", None)
    state[branch_action] = {
        "completed": True,
        "label": procedure["label"],
        "result": result_text,
        "roll": getattr(entry, "roll", None),
        "total": total,
        "updated_at": now_utc(),
    }
    state["latest"] = branch_action
    state["next_action"] = procedure["next_action"]
    if total is not None:
        state["latest_total"] = total
    if branch_action in {"map_cave_room_count", "map_structure_rooms"} and total is not None:
        state["room_target"] = total
    if branch_action == "map_cave_room_count" and total is not None:
        state["next_action"] = (
            f"Underground caves target recorded as room {total}. "
            "Explore normally; the app counts rooms, makes that room the Treasure Map final Boss room, and completes the objective when that Boss is defeated."
        )
    quest.tag_treasure_map_destination = int(procedure["destination"])
    quest.tag_procedure_state = state
    temple_complete = all(
        dict(state.get(action) or {}).get("completed")
        for action in ("map_temple_idol", "map_temple_scroll")
    )
    if branch_action in TAG_TREASURE_MAP_AUTO_COMPLETE_ACTIONS or temple_complete:
        quest.completed = True
        quest.tag_procedure_signoff = True
        if not any("TAG Treasure Map objective complete" in line for line in session.log):
            session.log.append(
                "TAG Treasure Map objective complete: destination procedure logged. Claim the Treasure Map quest reward when ready, after any treasure, Guild share, banking, and XP signoff."
            )


def _stored_single_run_procedure(session: SessionState, branch_action: str) -> dict[str, Any] | None:
    quest = session.active_quest
    if quest is None or branch_action not in TAG_SINGLE_RUN_BRANCH_ACTIONS:
        return None
    if _is_tag_treasure_map_quest(quest):
        procedure_state = dict(quest.tag_procedure_state or {})
        stored = procedure_state.get(branch_action)
        if isinstance(stored, dict) and stored.get("completed"):
            if "next_action" not in stored and procedure_state.get("next_action"):
                stored = {**stored, "next_action": procedure_state.get("next_action")}
            return stored
    state = dict(quest.tag_generated_lead_state or {})
    procedures = state.get("procedures")
    if not isinstance(procedures, dict):
        return None
    stored = procedures.get(branch_action)
    if isinstance(stored, dict) and stored.get("completed"):
        if "next_action" not in stored and state.get("next_action"):
            stored = {**stored, "next_action": state.get("next_action")}
        return stored
    return None


def _update_generated_tag_procedure_state(session: SessionState, branch_action: str, entry: Any) -> None:
    quest = session.active_quest
    if quest is None or not _is_generated_tag_session(session):
        return
    if branch_action not in TAG_TREASURE_MAP_DESTINATIONS:
        return
    procedure = TAG_TREASURE_MAP_DESTINATIONS[branch_action]
    state = dict(quest.tag_generated_lead_state or {})
    procedures = dict(state.get("procedures") or {})
    total = getattr(entry, "total", None)
    result_text = str(getattr(entry, "result_text", "") or "")
    procedures[branch_action] = {
        "completed": True,
        "label": procedure["label"],
        "result": result_text,
        "roll": getattr(entry, "roll", None),
        "total": total,
        "next_action": procedure["next_action"],
        "updated_at": now_utc(),
    }
    state["procedures"] = procedures
    state["latest_procedure"] = branch_action
    state["next_action"] = procedure["next_action"]
    if total is not None:
        state["room_target"] = total
        state["route_recorded"] = True
    if branch_action == "map_cave_room_count" and total is not None:
        state["next_action"] = (
            f"Underground caves target recorded as room {total}. "
            "Explore normally; the app counts rooms, makes that room the Treasure Map final Boss room, and completes the objective when that Boss is defeated."
        )
    quest.tag_generated_lead_state = state


def _spawn_generated_tag_foes_from_choice(session: SessionState, branch_action: str, entry: Any) -> bool:
    if not _is_generated_tag_session(session):
        return False
    if branch_action not in {"medusa_stealth_approach", "medusa_reaction"}:
        return False
    tile = random_engine._current_tile(session)
    room_id = _imported_room_id_for_tile(session, tile)
    if room_id != "tag-final-scene" or any(enemy.life > 0 for enemy in tile.enemies):
        return False
    tag_ref = (((session.imported_manifest or {}).get("source") or {}).get("parameters") or {}).get("tag_reference") or {}
    if not isinstance(tag_ref, dict) or int(tag_ref.get("rumor_number") or 0) != 2:
        return False
    should_fight = branch_action == "medusa_stealth_approach" or int(getattr(entry, "roll", 0) or 0) >= 3
    if not should_fight:
        return False
    foes = tag_ref.get("final_foes") or [{"name": "Medusa", "count": 1}]
    spawned = spawn_manifest_foes(random_engine.rules.monsters(), foes, random_engine._highest_character_level(session.party))
    if not spawned:
        return False
    tile.enemies.extend(spawned)
    tile.initial_enemy_count = len(tile.enemies)
    session.log.append("Scene 1: Xasartha enters the fight after the printed approach/reaction result.")
    random_engine._begin_combat(
        session,
        "Medusa combat begins from the printed Scene 1 result.",
        tile=tile,
        show_rolls=True,
        allow_final_boss_check=False,
        party_strikes_first=branch_action == "medusa_stealth_approach" and "success" in str(getattr(entry, "result_text", "")).lower(),
    )
    session.reaction_pending = False
    session.reaction_checked = True
    session.reaction_key = "fight_to_death" if int(getattr(entry, "roll", 0) or 0) == 6 else "fight"
    if session.log and session.log[-1] == "Choose: Check Reactions, or attack immediately (Fight Round or any voluntary combat spell).":
        session.log.pop()
    return True


@app.post("/api/sessions/{session_id}/tag-treasure-map-signoff")
async def session_tag_treasure_map_signoff(session_id: str, payload: dict[str, Any]) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    quest = session.active_quest
    if not _is_tag_treasure_map_quest(quest):
        raise HTTPException(status_code=400, detail="No active TAG Treasure Map quest is available for signoff.")
    state = dict(quest.tag_procedure_state or {})
    note = str(payload.get("note") or "").strip()[:240]
    state["manual_signoff"] = {
        "completed": True,
        "label": "Player procedure signoff",
        "result": note or "Player confirmed the destination procedure, treasure handling, and closeout checks.",
        "updated_at": now_utc(),
    }
    state["latest"] = "manual_signoff"
    state["next_action"] = "Destination procedure signed off. Claim the Treasure Map quest reward when the party is ready, then finish Guild share, banking/storage, XP, and closeout review."
    quest.tag_procedure_state = state
    quest.tag_procedure_signoff = True
    quest.completed = True
    session.log.append(
        f"TAG Treasure Map signoff: {state['manual_signoff']['result']}"
    )
    store.save("sessions", session)
    return enrich_session(session)


@app.post("/api/sessions/{session_id}/tag-generated-lead-signoff")
async def session_tag_generated_lead_signoff(session_id: str, payload: dict[str, Any]) -> SessionState:
    from .engine.tag_campaign import load_campaign

    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not _is_generated_tag_session(session):
        raise HTTPException(status_code=400, detail="This session is not a generated Adventures Guild lead.")
    quest = session.active_quest
    if quest is None:
        raise HTTPException(status_code=400, detail="No active generated Adventures Guild quest is available for signoff.")
    params = ((session.imported_manifest or {}).get("source") or {}).get("parameters") or {}
    tag_ref = params.get("tag_reference") if isinstance(params, dict) else {}
    lead_type = str((tag_ref or {}).get("lead_type") or params.get("lead_type") or "generated_tag")
    lead_detail = str((tag_ref or {}).get("lead_detail") or params.get("lead_detail") or session.imported_title or "Adventures Guild lead")
    state = dict(quest.tag_generated_lead_state or {})
    note = str(payload.get("note") or "").strip()[:300]
    result = note or "Player confirmed route, reward, XP, Guild share, banking/storage, and closeout checks."
    campaign = load_campaign(store)
    pending_xp = [marker for marker in campaign.tag_xp_markers if not marker.applied]
    open_closeout = [task for task in campaign.tag_closeout_tasks if not task.resolved]
    open_guidance = [task for task in campaign.guidance_tasks if task.status == "open"]
    warnings: list[str] = []
    if not quest.completed:
        warnings.append("Lead objective is not complete yet.")
    if not campaign.tag_adventure_routes:
        warnings.append("No structured route marker is recorded for this generated lead.")
    if pending_xp:
        warnings.append(f"{len(pending_xp)} pending TAG XP marker(s) still need award/dismiss/signoff.")
    if open_closeout:
        warnings.append(f"{len(open_closeout)} TAG closeout task(s) are still unresolved.")
    if open_guidance:
        warnings.append(f"{len(open_guidance)} open guidance item(s) remain in the campaign log.")
    state["lead_type"] = lead_type
    state["lead_detail"] = lead_detail
    state["route_recorded"] = bool(campaign.tag_adventure_routes)
    state["xp_reviewed"] = not pending_xp
    state["reward_recorded"] = bool(quest.completed or quest.reward_claimed)
    state["closeout_warnings"] = warnings
    state["closeout"] = {
        "completed": True,
        "result": result,
        "warnings": warnings,
        "updated_at": now_utc(),
    }
    state["next_action"] = "Generated Adventures Guild lead signed off. Return to the Dashboard/Go Adventure closeout panels before starting another lead."
    quest.tag_generated_lead_state = state
    quest.tag_generated_lead_signoff = True
    if quest.completed:
        session.log.append(f"TAG generated lead signoff: {lead_detail}: {result}")
    else:
        session.log.append(
            f"TAG generated lead closeout noted before objective completion: {lead_detail}: {result}"
        )
    if warnings:
        session.log.append(f"TAG generated lead signoff warnings: {'; '.join(warnings)}")
    store.save("sessions", session)
    return enrich_session(session)


@app.post("/api/sessions/{session_id}/tag-repair-guidance")
async def session_tag_repair_guidance(session_id: str) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not _is_generated_tag_session(session):
        raise HTTPException(status_code=400, detail="This session is not a generated Adventures Guild lead.")
    changed = False
    repair_details: list[str] = []
    if isinstance(session.imported_manifest, dict):
        before = repr(session.imported_manifest)
        session.imported_manifest = upgrade_tag_manifest(session.imported_manifest)
        changed = changed or repr(session.imported_manifest) != before
        params = session.imported_manifest.get("source", {}).get("parameters", {})
        tag_ref = params.get("tag_reference") if isinstance(params, dict) else {}
        if isinstance(tag_ref, dict):
            fields = tag_ref.get("local_narrative_override_changed_fields")
            if isinstance(fields, list) and fields:
                repair_details.append("local PDF narrative: " + ", ".join(str(field) for field in fields[:8]))
                if len(fields) > 8:
                    repair_details[-1] += f", +{len(fields) - 8} more"
            if tag_ref.get("prompt_repair_note"):
                repair_details.append("prompt metadata repaired")
    log_changed = normalize_tag_log_lines(session.log)
    changed = log_changed or changed
    if log_changed and not any("legacy log wording normalized" == item for item in repair_details):
        repair_details.append("legacy log wording normalized")
    if session.active_quest is not None:
        state = dict(session.active_quest.tag_generated_lead_state or {})
        state["guidance_repaired"] = True
        state["repaired_at"] = now_utc()
        state["repair_summary"] = repair_details or ["No stale generated narrative or prompt metadata needed changing."]
        state["next_action"] = "Adventures Guild narrative refreshed. Continue from the Current Objective and use visible scene buttons before manual Actions."
        session.active_quest.tag_generated_lead_state = state
        changed = True
    session.log.append(
        "Adventures Guild narrative refresh: "
        + ("; ".join(repair_details) if repair_details else "checked local PDF narrative, prompt metadata, and legacy log wording; no changes were needed.")
    )
    store.save("sessions", session)
    return enrich_session(session)


@app.post("/api/sessions/{session_id}/tag-branch-action")
async def session_tag_branch_action(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, resolve_tag_branch_action, save_campaign

    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    campaign = load_campaign(store)
    character = _optional_campaign_character(payload)
    branch_action = str(payload.get("branch_action") or "social_choice")
    payment_member, carried_gold_before = _prepare_session_tag_payment_character(session, character, branch_action)
    stored = _stored_single_run_procedure(session, branch_action)
    if stored is not None and not payload.get("force_reroll"):
        result_text = (
            f"{stored.get('label') or 'Adventures Guild procedure'} already recorded: {stored.get('result') or 'result stored'}. "
            f"Next: {stored.get('next_action') or 'continue from the stored procedure result.'}"
        )
        if result_text not in session.log:
            session.log.append(result_text)
            store.save("sessions", session)
        return {
            "campaign": campaign,
            "character": character,
            "entry": {
                "action": branch_action,
                "result_text": result_text,
                "total": stored.get("total"),
                "roll": stored.get("roll"),
            },
            "session": enrich_session(session),
        }
    entry = resolve_tag_branch_action(
        campaign,
        character,
        branch_action=branch_action,
        reference=str(payload.get("reference") or ""),
        clue_cost=int(payload.get("clue_cost") or 0),
        reward_gp=int(payload.get("reward_gp") or 0),
    )
    if character is not None:
        store.save("characters", character)
        if payment_member is not None:
            _sync_session_tag_payment_character(session, character, payment_member, carried_gold_before)
        else:
            _sync_character_to_session_party(session, character)
    campaign = save_campaign(store, campaign)
    _update_session_tag_procedure_state(session, branch_action, entry)
    _update_generated_tag_procedure_state(session, branch_action, entry)
    if entry.result_text and entry.result_text not in session.log:
        session.log.append(f"Adventures Guild procedure: {entry.result_text}")
    _spawn_generated_tag_foes_from_choice(session, branch_action, entry)
    if branch_action == "map_cave_room_count":
        next_action = (
            session.active_quest.tag_generated_lead_state.get("next_action")
            if session.active_quest is not None
            else ""
        ) or (
            session.active_quest.tag_procedure_state.get("next_action")
            if session.active_quest is not None
            else ""
        )
        if next_action:
            session.log.append(f"TAG next: {next_action}")
    store.save("sessions", session)
    return {"campaign": campaign, "character": character, "entry": entry, "session": enrich_session(session)}


@app.post("/api/sessions/{session_id}/tag-route-action")
async def session_tag_route_action(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import apply_tag_route_to_manifest, load_campaign, resolve_tag_route_action, save_campaign

    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    campaign = load_campaign(store)
    character = _optional_campaign_character(payload)
    entry = resolve_tag_route_action(
        campaign,
        character,
        route_action=str(payload.get("route_action") or "parley_success"),
        reference=str(payload.get("reference") or ""),
        clue_cost=int(payload.get("clue_cost") or 0),
    )
    rewrite_result = ""
    if isinstance(session.imported_manifest, dict):
        changed_detail = apply_tag_route_to_manifest(session.imported_manifest, campaign)
        rewrite_result = f"Applied route marker to active session: {changed_detail}."
    if character is not None:
        store.save("characters", character)
        _sync_character_to_session_party(session, character)
    campaign = save_campaign(store, campaign)
    if entry.result_text and entry.result_text not in session.log:
        session.log.append(f"TAG route: {entry.result_text}")
    store.save("sessions", session)
    return {
        "campaign": campaign,
        "character": character,
        "entry": entry,
        "rewrite_result": rewrite_result,
        "session": enrich_session(session),
    }


@app.post("/api/sessions/{session_id}/tag-scene-action")
async def session_tag_scene_action(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    from .engine.tag_campaign import load_campaign, resolve_tag_scene_action, save_campaign

    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    character = _optional_campaign_character(payload)
    if character is None:
        raise HTTPException(status_code=400, detail="Character is required.")
    scene_action = str(payload.get("scene_action") or "")
    payment_member, carried_gold_before = _prepare_session_tag_payment_character(session, character, scene_action)
    campaign = load_campaign(store)
    entry = resolve_tag_scene_action(
        campaign,
        character,
        scene_action=scene_action,
        amount=int(payload.get("amount") or 0),
        reference=str(payload.get("reference") or ""),
    )
    store.save("characters", character)
    if payment_member is not None:
        _sync_session_tag_payment_character(session, character, payment_member, carried_gold_before)
    else:
        _sync_character_to_session_party(session, character)
    campaign = save_campaign(store, campaign)
    if entry.result_text and entry.result_text not in session.log:
        session.log.append(f"Adventures Guild scene: {entry.result_text}")
    store.save("sessions", session)
    return {"campaign": campaign, "character": character, "entry": entry, "session": enrich_session(session)}


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
        fd_ruins_machinery_reward_choice=payload.fd_ruins_machinery_reward_choice,
        fd_ruins_psychic_choice=payload.fd_ruins_psychic_choice,
        fd_winds_choice=payload.fd_winds_choice,
        fd_disintegration_choice=payload.fd_disintegration_choice,
        fd_soulbinding_choice=payload.fd_soulbinding_choice,
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

        record_adventure_complete(store, session)
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


def _safe_pdf_adventure_id(path: Path, source_kind: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or "pdf-source"
    return base if source_kind == "legacy" else f"{base}-pdf"


def _relative_source_path(path: Path) -> str:
    for base in (settings.root_dir, settings.data_dir):
        try:
            return str(path.relative_to(base)).replace("\\", "/")
        except ValueError:
            continue
    return str(path)
