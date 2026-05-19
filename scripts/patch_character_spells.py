"""One-off repair: restore prepared spell lists on character records in game.db."""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.engine.class_profiles import (  # noqa: E402
    available_level_up_spells,
    spell_slot_count,
)

CLASSES = json.loads((ROOT / "data" / "rules" / "classes.json").read_text(encoding="utf-8"))
STARTING_SPELLS = {item["id"]: list(item.get("starting_spells") or []) for item in CLASSES}

DEFAULT_DB = "//TOWER/appdata/ahazi-against-darkness/game.db"


def restore_prepared_spells(class_id: str, level: int, current: list[str]) -> list[str]:
    slots = spell_slot_count(class_id, level)
    if slots is None:
        if class_id == "cleric":
            restored = list(STARTING_SPELLS.get("cleric", []))
            for spell in current:
                if spell not in restored:
                    restored.append(spell)
            return restored
        return []
    starting = STARTING_SPELLS.get(class_id, [])
    pool: list[str] = []
    for spell in starting + [spell for spell in current if spell] + available_level_up_spells(class_id):
        if spell and spell not in pool:
            pool.append(spell)
    restored: list[str] = []
    for spell in pool:
        if len(restored) >= slots:
            break
        restored.append(spell)
    return restored[:slots]


def _member_levels_by_character(conn: sqlite3.Connection) -> dict[str, int]:
    levels: dict[str, int] = {}
    for row in conn.execute("SELECT data FROM records WHERE collection = 'characters'"):
        data = json.loads(row["data"])
        levels[data["id"]] = int(data["level"])
    for row in conn.execute("SELECT data FROM records WHERE collection = 'sessions'"):
        session = json.loads(row["data"])
        for member in session.get("party") or []:
            character_id = member["character_id"]
            levels[character_id] = max(levels.get(character_id, 1), int(member["level"]))
    return levels


def _merged_spells_by_character(conn: sqlite3.Connection) -> dict[str, list[str]]:
    merged: dict[str, list[str]] = {}
    for row in conn.execute("SELECT data FROM records WHERE collection = 'characters'"):
        data = json.loads(row["data"])
        merged[data["id"]] = list(data.get("spells") or [])
    for row in conn.execute("SELECT data FROM records WHERE collection = 'sessions'"):
        session = json.loads(row["data"])
        for member in session.get("party") or []:
            character_id = member["character_id"]
            spells = merged.setdefault(character_id, [])
            for spell in member.get("spells") or []:
                if spell not in spells:
                    spells.append(spell)
    return merged


def patch_db(conn: sqlite3.Connection) -> list[str]:
    logs: list[str] = []
    timestamp = datetime.now(UTC).isoformat()
    member_levels = _member_levels_by_character(conn)
    merged_spells = _merged_spells_by_character(conn)

    char_rows = conn.execute(
        "SELECT id, data FROM records WHERE collection = 'characters'",
    ).fetchall()
    updated_characters: dict[str, dict] = {}

    for row in char_rows:
        item_id = row["id"]
        data = json.loads(row["data"])
        original_level = int(data["level"])
        level = member_levels.get(item_id, original_level)
        merged = list(merged_spells.get(item_id) or [])
        if level != original_level:
            logs.append(f"character {data['name']}: level {original_level} -> {level}")
            data["level"] = level
        before = list(data.get("spells") or [])
        after = restore_prepared_spells(data["class_id"], level, merged)
        if after != before or level != original_level:
            data["spells"] = after
            conn.execute(
                "UPDATE records SET data = ?, updated_at = ? WHERE collection = 'characters' AND id = ?",
                (json.dumps(data), timestamp, item_id),
            )
            if after != before:
                logs.append(f"character {data['name']}: {before} -> {after}")
        updated_characters[item_id] = data

    session_rows = conn.execute(
        "SELECT id, data FROM records WHERE collection = 'sessions'",
    ).fetchall()
    for row in session_rows:
        session_id = row["id"]
        session_data = json.loads(row["data"])
        changed = False
        if session_data.get("expended_spells") or session_data.get("healing_prayer_uses"):
            session_data["expended_spells"] = {}
            session_data["healing_prayer_uses"] = {}
            changed = True
        for member in session_data.get("party") or []:
            char = updated_characters.get(member["character_id"])
            if char is None:
                continue
            target = list(char.get("spells") or [])
            if list(member.get("spells") or []) != target:
                member["spells"] = target
                changed = True
                logs.append(f"session {session_id[:8]} {member['name']}: spells -> {target}")
        if changed:
            conn.execute(
                "UPDATE records SET data = ?, updated_at = ? WHERE collection = 'sessions' AND id = ?",
                (json.dumps(session_data), timestamp, session_id),
            )
            if session_data.get("expended_spells") == {} and not any(
                line.startswith(f"session {session_id[:8]}") for line in logs
            ):
                logs.append(f"session {session_id[:8]}: cleared expended spell tracking")
    return logs


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DB
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        logs = patch_db(conn)
        conn.commit()
    finally:
        conn.close()
    if not logs:
        print("No spell lists needed changes.")
        return
    print("Patched game.db:")
    for line in logs:
        print(f"  - {line}")


if __name__ == "__main__":
    main()
