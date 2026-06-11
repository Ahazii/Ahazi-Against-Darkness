"""Dump raw key structure of the active session to find split-party fields."""
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
for sid, raw in conn.execute("SELECT id, data FROM records WHERE collection='sessions'"):
    s = json.loads(raw)
    if s.get("mode") == "complete":
        continue
    print(f"Session {sid}")
    print("\nSESSION KEYS:")
    for k in sorted(s.keys()):
        v = s[k]
        if isinstance(v, (dict, list)):
            print(f"  {k}: {type(v).__name__} len={len(v)}")
        else:
            print(f"  {k} = {v!r}")
    print("\nMEMBER 0 FULL:")
    m = s["party"][0]
    for k in sorted(m.keys()):
        print(f"  {k} = {repr(m[k])[:100]}")
    # Look for split-related keys anywhere
    text = json.dumps(s)
    for word in ("detach", "scout", "split", "group", "left_behind"):
        count = text.lower().count(word)
        print(f"\noccurrences of '{word}': {count}")
    break
