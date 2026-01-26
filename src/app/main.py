from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi import UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import load_config
from .logging_config import configure_logging
from .game.classes import load_class_profiles
from .game.random_adventure import RandomAdventure
from .game.dice import roll_d6
from .game.tables import DungeonTables, list_implemented_tables, load_table_data, save_table_data
from .game.combat import resolve_combat_round
from .game.adventures import list_imported_adventures
from .models import (
    Character,
    CharacterCreate,
    Party,
    PartyCreate,
    PartyStatus,
    SessionState,
)
from .storage.json_store import JsonStore, now_utc


configure_logging()
config = load_config()
store = JsonStore(config.data_dir)
class_profiles = load_class_profiles(config.tables_dir)

app = FastAPI()
static_path = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=static_path), name="static")


def _character_from_create(payload: CharacterCreate) -> Character:
    profile = class_profiles.get(payload.class_name.lower())
    if not profile:
        raise HTTPException(status_code=400, detail="Unknown class name.")
    max_life = profile.base_life + payload.level * profile.life_per_level
    return Character(
        id=store.new_id(),
        name=payload.name.strip(),
        class_name=profile.name,
        level=payload.level,
        max_life=max_life,
        attack_bonus=payload.level * profile.attack_bonus_per_level,
        defense_bonus=payload.level * profile.defense_bonus_per_level,
        created_at=now_utc(),
    )


def _party_from_create(payload: PartyCreate) -> Party:
    return Party(
        id=store.new_id(),
        name=payload.name.strip(),
        character_ids=payload.character_ids,
        created_at=now_utc(),
    )


def _party_status_for_session(characters: list[Character]) -> list[PartyStatus]:
    status: list[PartyStatus] = []
    for char in characters:
        status.append(
            PartyStatus(
                character_id=char.id,
                name=char.name,
                class_name=char.class_name,
                level=char.level,
                current_life=char.max_life,
                max_life=char.max_life,
                attack_bonus=char.attack_bonus,
                defense_bonus=char.defense_bonus,
            )
        )
    return status


def _hcl(party_status: list[PartyStatus]) -> int:
    return max((pc.level for pc in party_status), default=1)


def _load_characters(ids: list[str]) -> list[Character]:
    characters: list[Character] = []
    for char_id in ids:
        char = store.get("characters", char_id, Character.model_validate)
        if not char:
            raise HTTPException(status_code=404, detail=f"Character {char_id} not found.")
        characters.append(char)
    return characters


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = (static_path / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html)


@app.get("/api/characters")
async def list_characters() -> list[Character]:
    return store.list("characters", Character.model_validate)


@app.post("/api/characters")
async def create_character(payload: CharacterCreate) -> Character:
    character = _character_from_create(payload)
    store.save("characters", character)
    return character


@app.get("/api/parties")
async def list_parties() -> list[Party]:
    return store.list("parties", Party.model_validate)


@app.post("/api/parties")
async def create_party(payload: PartyCreate) -> Party:
    _load_characters(payload.character_ids)
    party = _party_from_create(payload)
    store.save("parties", party)
    return party


@app.get("/api/adventures")
async def list_adventures() -> dict[str, Any]:
    return {
        "random": [{"id": "random", "name": "Random Dungeon"}],
        "imported": [adventure.__dict__ for adventure in list_imported_adventures()],
    }


@app.get("/api/tables")
async def list_tables() -> list[str]:
    return list_implemented_tables()


@app.get("/api/tables/details")
async def table_details() -> dict:
    return load_table_data(config.tables_dir)


@app.get("/api/tiles/{filename}")
async def get_tile(filename: str) -> FileResponse:
    tile_path = config.tiles_dir / filename
    if tile_path.exists():
        return FileResponse(tile_path)
    raise HTTPException(status_code=404, detail="Tile not found.")


@app.post("/api/tiles/{filename}")
async def upload_tile(filename: str, file: UploadFile = File(...)) -> dict:
    if not filename.lower().endswith((".gif", ".png", ".jpg", ".jpeg")):
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    destination = config.tiles_dir / filename
    contents = await file.read()
    destination.write_bytes(contents)
    return {"status": "ok", "filename": filename}


@app.put("/api/tables/details")
async def save_table_details(payload: dict) -> dict:
    save_table_data(config.tables_dir, payload)
    return {"status": "ok"}


@app.post("/api/sessions")
async def create_session(payload: dict[str, Any]) -> SessionState:
    party_id = payload.get("party_id")
    adventure_type = payload.get("adventure_type", "random")
    adventure_id = payload.get("adventure_id")
    party = store.get("parties", party_id, Party.model_validate)
    if not party:
        raise HTTPException(status_code=404, detail="Party not found.")

    characters = _load_characters(party.character_ids)
    party_status = _party_status_for_session(characters)

    if adventure_type != "random":
        raise HTTPException(status_code=400, detail="Imported adventures are not available yet.")

    adventure = RandomAdventure(tables_dir=config.tables_dir)
    map_state = adventure.create_map()

    session = SessionState(
        id=store.new_id(),
        party_id=party.id,
        mode="exploration",
        adventure_type="random",
        adventure_id=adventure_id,
        map_state=map_state,
        party_status=party_status,
        log=["Adventure begins at the entrance."],
        created_at=now_utc(),
        updated_at=now_utc(),
    )
    store.save("sessions", session)
    return session


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@app.post("/api/sessions/{session_id}/advance")
async def advance_session(session_id: str, payload: dict[str, Any]) -> SessionState:
    session = store.get("sessions", session_id, SessionState.model_validate)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    action = payload.get("action", "explore")
    adventure = RandomAdventure(tables_dir=config.tables_dir)

    if session.mode == "exploration" and action == "explore":
        map_state, new_tile = adventure.generate_next_tile(session.map_state, _hcl(session.party_status))
        session.map_state = map_state
        if new_tile.enemies:
            session.mode = "combat"
            session.log.append(f"Encounter: {new_tile.content}.")
        else:
            session.log.append(f"Entered: {new_tile.content}.")

    elif session.mode == "exploration" and action == "search":
        current_tile = next(
            tile for tile in session.map_state.tiles if tile.id == session.map_state.current_tile_id
        )
        if current_tile.searched:
            session.log.append("This tile has already been searched.")
        else:
            search_roll = roll_d6() + (-1 if current_tile.tile_type == "corridor" else 0)
            if search_roll <= 1:
                tables = DungeonTables(config.tables_dir)
                encounter_roll = roll_d6()
                if encounter_roll <= 2:
                    foe = tables.roll_foe("vermin", _hcl(session.party_status))
                elif encounter_roll <= 4:
                    foe = tables.roll_foe("minions", _hcl(session.party_status))
                elif encounter_roll == 5:
                    foe = tables.roll_foe("weird", _hcl(session.party_status))
                else:
                    foe = tables.roll_foe("boss", _hcl(session.party_status))
                current_tile.enemies.extend(adventure._expand_foes(foe))
                session.mode = "combat"
                current_tile.search_result = "Wandering Monsters"
                session.log.append("Search triggered wandering monsters!")
            elif search_roll <= 4:
                current_tile.search_result = "Empty"
                session.log.append("Search found nothing of interest.")
            else:
                reward = ["Hidden Treasure", "Secret Door", "Secret Passage", "Clue"][roll_d6() - 1]
                current_tile.objects.append(reward)
                current_tile.search_result = reward
                session.log.append(f"Search discovered: {reward}.")
            current_tile.searched = True

    elif session.mode == "exploration" and action == "open_treasure":
        current_tile = next(
            tile for tile in session.map_state.tiles if tile.id == session.map_state.current_tile_id
        )
        if "Treasure" in current_tile.objects:
            current_tile.objects = [obj for obj in current_tile.objects if obj != "Treasure"]
            session.log.append("You open the treasure and secure the contents.")
        else:
            session.log.append("There is no treasure to open here.")

    elif session.mode == "exploration" and action == "reaction":
        roll = roll_d6()
        session.log.append(f"Reaction roll: {roll}. Consult the foe's reaction table.")

    elif session.mode == "combat" and action == "combat_round":
        current_tile = next(
            tile for tile in session.map_state.tiles if tile.id == session.map_state.current_tile_id
        )
        result = resolve_combat_round(session.party_status, current_tile.enemies)
        session.party_status = result.party
        current_tile.enemies = result.enemies
        session.log.extend(result.log)
        if result.combat_over:
            if any(pc.current_life > 0 for pc in session.party_status):
                session.mode = "exploration"
                session.log.append("Combat ends.")
            else:
                session.mode = "complete"
                session.log.append("The party has fallen.")

    session.updated_at = now_utc()
    store.save("sessions", session)
    return session


@app.websocket("/ws/sessions/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        session = store.get("sessions", session_id, SessionState.model_validate)
        if not session:
            await websocket.send_text(json.dumps({"error": "Session not found."}))
            return
        await websocket.send_text(session.model_dump_json())
        while True:
            await websocket.receive_text()
            session = store.get("sessions", session_id, SessionState.model_validate)
            if session:
                await websocket.send_text(session.model_dump_json())
    except WebSocketDisconnect:
        return
