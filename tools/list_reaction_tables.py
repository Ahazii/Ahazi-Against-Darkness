#!/usr/bin/env python3
"""Print all reaction tables for manual review."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
monsters = json.loads((ROOT / "data/rules/monsters.json").read_text(encoding="utf-8"))
dt = json.loads((ROOT / "data/rules/dungeon_tables.json").read_text(encoding="utf-8"))

print("=== CATEGORY FALLBACK TABLES ===")
for t in ["default_reaction_table", "vermin_reaction_table", "minion_reaction_table", "major_reaction_table"]:
    print(f"\n## {t}")
    for row in dt.get(t, []):
        extra = {k: v for k, v in row.items() if k not in ("roll", "key", "result")}
        ex = f" {extra}" if extra else ""
        print(f"  {row['roll']:6} {row['key']:28} {row['result'][:70]}{ex}")

tables = monsters.get("reaction_tables", {})
for name in sorted(tables.keys()):
    print(f"\n## {name}")
    for row in tables[name]:
        extra = {k: v for k, v in row.items() if k not in ("roll", "key", "result", "foes_first")}
        ff = " [foes_first]" if row.get("foes_first") else ""
        ex = f" {extra}" if extra else ""
        print(f"  {str(row['roll']):6} {row['key']:28} {row['result'][:65]}{ff}{ex}")
