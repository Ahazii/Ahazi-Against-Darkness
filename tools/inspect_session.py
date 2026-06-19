#!/usr/bin/env python3
"""Inspect a saved session from game.db (Tower or local)."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    db = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"\\TOWER\appdata\ahazi-against-darkness\game.db")
    adventure = sys.argv[2] if len(sys.argv) > 2 else "haunted-mansion"
    conn = sqlite3.connect(db)
    rows = conn.execute(
        "SELECT id, data FROM records WHERE collection = 'sessions'"
    ).fetchall()
    conn.close()
    matches = []
    for sid, payload in rows:
        data = json.loads(payload)
        if data.get("adventure_id") == adventure and data.get("mode") != "complete":
            matches.append((sid, data))
    if not matches:
        print(f"No active sessions for {adventure!r}")
        return
    for sid, session in matches:
        print("SESSION", sid, "mode=", session.get("mode"))
        print("current_tile_id", session.get("map_state", {}).get("current_tile_id"))
        for tile in session.get("map_state", {}).get("tiles", []):
            if "Coal" in (tile.get("title") or "") or tile.get("id") == session["map_state"]["current_tile_id"]:
                print("TILE", tile.get("title"), "id", tile.get("id")[:8], "pos", tile.get("x"), tile.get("y"))
                print("  treasure_gold", tile.get("treasure_gold"), "items", tile.get("treasure_items"))
                print("  summary", tile.get("treasure_summary"), "claimed", tile.get("treasure_claimed"))
                print("  exits", [(e.get("direction"), e.get("destination_tile_id", "")[:8], e.get("x"), e.get("y")) for e in tile.get("exits", [])])
        print("--- recent log ---")
        for line in session.get("log", [])[-15:]:
            print(line)
        print("--- all tile positions ---")
        for tile in session.get("map_state", {}).get("tiles", []):
            print(f"  {tile.get('title')!r:40} ({tile.get('x')},{tile.get('y')}) key={tile.get('tile_key')} ck={tile.get('content_key')}")


if __name__ == "__main__":
    main()
