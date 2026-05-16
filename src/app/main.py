from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .config import load_settings
from .db import Store, init_db, new_id, now_utc
from .engine.random_dungeon import RandomDungeonEngine
from .rules.repository import RulesRepository, VALID_TILE_KEYS
from .schemas import (
    AdventureDescriptor,
    Character,
    CharacterCreate,
    CharacterClass,
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

app = FastAPI(title="Ahazi Against Darkness", version="0.5.0")
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


@app.get("/api/rules/classes")
async def list_classes() -> list[CharacterClass]:
    return rules.classes()


@app.get("/api/rules/tiles")
async def list_tiles() -> list[TileDefinition]:
    return list(rules.tiles().values())


@app.put("/api/rules/tiles")
async def save_tiles(payload: list[TileDefinition]) -> dict[str, str | int]:
    if len({tile.key for tile in payload}) != len(payload):
        raise HTTPException(status_code=400, detail="Duplicate tile keys are not allowed.")
    invalid_keys = sorted({tile.key for tile in payload} - _valid_tile_keys())
    if invalid_keys:
        raise HTTPException(status_code=400, detail=f"Invalid map element keys: {', '.join(invalid_keys)}.")
    rules.save_tiles(payload)
    return {"status": "ok", "count": len(payload)}


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
    store.save("characters", character)
    return character


@app.delete("/api/characters/{character_id}")
async def delete_character(character_id: str) -> dict[str, bool]:
    return {"deleted": store.delete("characters", character_id)}


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
    session = random_engine.create_session(new_id(), party.id, [_member_state(character) for character in characters])
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
    return session


@app.post("/api/sessions/{session_id}/advance")
async def advance_session(session_id: str, payload: SessionAction) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = random_engine.advance(session, payload.action, payload.exit_id, payload.direction)
    if session.mode == "complete":
        _persist_party_state(session.party)
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
        inventory=list(character.inventory),
        spells=list(character.spells),
        abilities=list(character.abilities),
        statuses=list(character.statuses),
    )


def _persist_party_state(party: list[PartyMemberState]) -> None:
    timestamp = now_utc()
    for member in party:
        character = store.get("characters", member.character_id, Character.model_validate)
        if character is None:
            continue
        character.level = member.level
        character.xp = member.xp
        character.gold = member.gold
        character.current_life = member.current_life
        character.max_life = member.max_life
        character.attack_bonus = member.attack_bonus
        character.defense_bonus = member.defense_bonus
        character.save_bonus = member.save_bonus
        character.inventory = list(member.inventory)
        character.spells = list(member.spells)
        character.abilities = list(member.abilities)
        character.statuses = list(member.statuses)
        character.updated_at = timestamp
        store.save("characters", character)


def _valid_tile_keys() -> set[str]:
    return set(VALID_TILE_KEYS)


def _title_from_pdf_name(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ").title()
