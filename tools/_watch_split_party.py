"""Snapshot split-party state of the active session (run repeatedly to watch)."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path

DB_CANDIDATES = [
    Path(r"\\TOWER\appdata\ahazi-against-darkness\game.db"),
    Path(__file__).resolve().parents[1] / ".data" / "game.db",
]
db_path = next((p for p in DB_CANDIDATES if p.exists()), None)
if not db_path:
    raise SystemExit("No game.db found")

conn = sqlite3.connect(db_path)
rows = conn.execute("SELECT id, data FROM records WHERE collection='sessions'").fetchall()

for sid, raw in rows:
    s = json.loads(raw)
    if s.get("mode") == "complete":
        continue
    ms = s.get("map_state", {})
    tiles = {t["id"]: t for t in ms.get("tiles", [])}
    cur_id = ms.get("current_tile_id")
    cur = tiles.get(cur_id, {})
    members = {m["character_id"]: m for m in s.get("party", [])}

    print(f"Session {sid[:8]}  mode={s.get('mode')}  round={s.get('combat_round')}  updated={s.get('updated_at')}")
    print(f"  current tile: {cur.get('title','?')} at ({cur.get('x')},{cur.get('y')})  [{len(tiles)} explored]")

    for m in s.get("party", []):
        print(f"  {m['name']:<16} L{m.get('level')} life={m.get('current_life')}/{m.get('max_life')} order={m.get('marching_order')}")

    groups = s.get("detached_groups") or []
    print(f"\n  detached_groups: {len(groups)}")
    for i, g in enumerate(groups, 1):
        tile = tiles.get(g.get("tile_id") or "", {})
        names = [members.get(cid, {}).get("name", cid[:8]) for cid in g.get("character_ids", [])]
        print(f"    group {i}: {names}  reason={g.get('reason')}  tile='{tile.get('title','?')}' ({tile.get('x')},{tile.get('y')})")
        extra = {k: v for k, v in g.items() if k not in ("character_ids", "tile_id", "reason")}
        if extra:
            print(f"      extra: {extra}")

    if s.get("scout_lag_character_id"):
        n = members.get(s["scout_lag_character_id"], {}).get("name", "?")
        print(f"  scout_lag_character_id: {n}")
    if s.get("detached_wandering_pending"):
        print(f"  detached_wandering_pending: {json.dumps(s['detached_wandering_pending'])[:400]}")
    if s.get("detached_combat_rounds"):
        print(f"  detached_combat_rounds: {s['detached_combat_rounds']}")

    # Tiles with living enemies
    for t in tiles.values():
        living = [e for e in (t.get("enemies") or []) if e.get("life", 0) > 0]
        if living:
            names = ", ".join(e.get("name", "?") for e in living)
            mark = " <CURRENT>" if t["id"] == cur_id else ""
            print(f"  enemies on '{t.get('title')}'{mark}: {names}")

    print(f"\n  last 5 log lines:")
    for line in (s.get("log") or [])[-5:]:
        text = line if isinstance(line, str) else json.dumps(line)
        print(f"    {text[:160]}")
    print()
