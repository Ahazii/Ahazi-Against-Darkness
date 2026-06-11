"""Dump the full adventure log of the active session."""
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
    print(f"Session {sid[:8]}  ({len(s.get('log') or [])} log lines)\n")
    for i, line in enumerate(s.get("log") or []):
        text = line if isinstance(line, str) else json.dumps(line)
        print(f"{i:4} | {text}")
    break
