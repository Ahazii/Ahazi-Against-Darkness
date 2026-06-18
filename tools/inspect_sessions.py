"""Inspect sessions in a game.db copy."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / ".data" / "game-tower-copy.db"


def main() -> int:
    if not DB.exists():
        print(f"Missing {DB}")
        return 1
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id, updated_at, length(data) FROM records WHERE collection='sessions' ORDER BY updated_at DESC LIMIT 12"
    ).fetchall()
    print("Recent sessions (full ids):")
    for sid, updated, plen in rows:
        print(f"  {sid}  {updated}  {plen} bytes")

    for sid, payload in conn.execute(
        "SELECT id, data FROM records WHERE collection='sessions' ORDER BY updated_at DESC LIMIT 6"
    ):
        data = json.loads(payload)
        tiles = data.get("map_state", {}).get("tiles", [])
        print("\n---", sid[:24])
        print(
            "mode", data.get("mode"),
            "env", data.get("environment"),
            "adventure", data.get("adventure_type"),
            "camped", data.get("camped_outside"),
        )
        print("party", len(data.get("party", [])), "tiles", len(tiles))
        print("pending_secret_passage", data.get("pending_secret_passage_tile_id"))
        print("detached_groups", json.dumps(data.get("detached_groups") or [], indent=2)[:500])
        print("active_group_tile_id", data.get("active_group_tile_id"))
        for tile in tiles:
            if tile.get("environment") == "caverns" or "cavern" in (tile.get("title") or "").lower():
                print(
                    "  cavern tile", tile.get("id")[:12], tile.get("title"),
                    "env", tile.get("environment"),
                    "exits", len(tile.get("exits", [])),
                )
        for member in data.get("party") or []:
            missing = [k for k in ("character_id", "name", "class_name", "marching_order", "current_life", "max_life", "level") if k not in member]
            if missing:
                print("  BAD member missing", missing, member.get("name"))
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
