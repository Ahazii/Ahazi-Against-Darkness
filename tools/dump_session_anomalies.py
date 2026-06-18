"""Find session JSON anomalies that could break the party-sheet renderer."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / ".data" / "game-tower-copy.db"


def check_session(data: dict, sid: str) -> None:
    print(f"\n==== {sid} ====")
    print("mode", data.get("mode"), "env", data.get("environment"))
    print("current_tile", (data.get("map_state") or {}).get("current_tile_id", "")[:12])
    for key in (
        "pending_secret_passage_tile_id",
        "pending_search_reward_tile_id",
        "active_group_tile_id",
        "level_up_spell_pending_character_id",
        "cursed_character_id",
    ):
        if data.get(key):
            print(f"  {key}:", data[key])

    for i, m in enumerate(data.get("party") or []):
        for field in ("statuses", "secrets", "spells", "inventory", "learned_expert_skills"):
            val = m.get(field)
            if val is None:
                continue
            if not isinstance(val, list):
                print(f"  party[{i}] {m.get('name')}: {field} is {type(val).__name__}, not list")
            else:
                for j, item in enumerate(val):
                    if isinstance(item, (dict, list)):
                        print(f"  party[{i}] {m.get('name')}: {field}[{j}] is {type(item).__name__}")

    for t in (data.get("map_state") or {}).get("tiles") or []:
        env = t.get("environment")
        if env and env != "dungeon":
            print(
                "  tile", t.get("id", "")[:12], t.get("title"),
                "env", env, "exits", len(t.get("exits") or []),
            )


def main() -> None:
    conn = sqlite3.connect(DB)
    for sid, payload in conn.execute(
        "SELECT id, data FROM records WHERE collection='sessions' ORDER BY updated_at DESC LIMIT 4"
    ):
        check_session(json.loads(payload), sid)
    conn.close()


if __name__ == "__main__":
    main()
