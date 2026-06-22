#!/usr/bin/env python3
"""Grant minimum Final Boss treasure on tiles that were missed due to no_treasure foes."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

sys.path.insert(0, str(ROOT / "src"))

from app.engine.experience import apply_final_boss_treasure_bonus
from app.schemas import SessionState

db = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"\\TOWER\appdata\ahazi-against-darkness\game.db")
sid = sys.argv[2] if len(sys.argv) > 2 else None

conn = sqlite3.connect(db)
rows = conn.execute("SELECT id, data FROM records WHERE collection='sessions'").fetchall()
updated = 0
for session_id, payload in rows:
    if sid and session_id != sid:
        continue
    session = SessionState.model_validate(json.loads(payload))
    changed = False
    for tile in session.map_state.tiles:
        if not tile.final_boss_treasure:
            continue
        if tile.treasure_gold or tile.treasure_items:
            continue
        if tile.treasure_claimed:
            continue
        gold = apply_final_boss_treasure_bonus(0)
        tile.treasure_gold = gold
        tile.treasure_summary = f"Final Boss treasure: {gold}gp"
        tile.treasure_claimed = False
        session.log.append(
            f"Final Boss bounty repaired: {gold}gp available to claim on {tile.title}."
        )
        changed = True
    if changed:
        conn.execute(
            "UPDATE records SET data=? WHERE id=?",
            (session.model_dump_json(), session_id),
        )
        updated += 1
        print("repaired", session_id)
conn.commit()
conn.close()
print("sessions updated:", updated)
