"""Dump session party/tile details for party-sheet debugging."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / ".data" / "game-tower-copy.db"
TARGETS = [
    "5e3106ab0759481ab33c6aa9cce5c97a",
    "29583a3c4934425898e643c22a028674",
]


def main() -> None:
    conn = sqlite3.connect(DB)
    for sid in TARGETS:
        row = conn.execute(
            "SELECT data FROM records WHERE collection='sessions' AND id=?",
            (sid,),
        ).fetchone()
        if not row:
            print("missing", sid)
            continue
        data = json.loads(row[0])
        print("\n====", sid, "====")
        print("mode", data.get("mode"), "env", data.get("environment"))
        for i, m in enumerate(data.get("party") or []):
            print(f"party[{i}]", m.get("name"))
            for field in ("character_id", "statuses", "inventory", "marching_order", "class_id"):
                val = m.get(field)
                print(f"  {field}: {type(val).__name__}", val if field != "inventory" else f"len={len(val or [])}")
        for t in data.get("map_state", {}).get("tiles") or []:
            print("tile", t.get("id", "")[:12], t.get("title"), "env", t.get("environment"))
    conn.close()


if __name__ == "__main__":
    main()
