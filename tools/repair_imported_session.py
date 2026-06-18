"""Repair imported adventure session tile layout in game.db (fixes hidden exits from overlap)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.engine.adventure_session import repair_imported_map_layout
from app.engine.random_dungeon import RandomDungeonEngine
from app.rules.repository import RulesRepository
from app.schemas import SessionState

DB = Path(r"\\TOWER\appdata\ahazi-against-darkness\game.db")
RULES = ROOT / "data" / "rules"


def main() -> None:
    session_id = sys.argv[1] if len(sys.argv) > 1 else None
    repo = RulesRepository(RULES, RULES / "_override")
    engine = RandomDungeonEngine(repo, ROOT / "assets")
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, data, updated_at FROM records WHERE collection = 'sessions' ORDER BY updated_at DESC"
    ).fetchall()
    repaired = 0
    for row in rows:
        session = SessionState.model_validate(json.loads(row["data"]))
        if session_id and session.id != session_id:
            continue
        if session.adventure_type != "imported" or session.mode == "complete":
            continue
        if session_id is None and session.mode == "complete":
            continue
        before = [(t.title, t.x, t.y) for t in session.map_state.tiles]
        if not repair_imported_map_layout(engine, session):
            continue
        after = [(t.title, t.x, t.y) for t in session.map_state.tiles]
        if before == after:
            continue
        payload = session.model_dump(mode="json")
        conn.execute(
            "UPDATE records SET data = ?, updated_at = ? WHERE collection = 'sessions' AND id = ?",
            (json.dumps(payload), session.updated_at, session.id),
        )
        repaired += 1
        print(f"Repaired {session.id} ({session.adventure_id})")
        current = next(t for t in session.map_state.tiles if t.id == session.map_state.current_tile_id)
        print(f"  Current room: {current.title}")
        for ex in current.exits:
            w = current.walkable[ex.y][ex.x] if ex.y < len(current.walkable) else "?"
            print(f"  {ex.direction}: ({ex.x},{ex.y}) walkable={w} -> {ex.destination_tile_id is not None}")
    conn.commit()
    conn.close()
    print(f"Done. Repaired {repaired} session(s).")


if __name__ == "__main__":
    main()
