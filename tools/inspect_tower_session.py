"""Inspect Tower save for camped sessions with hirelings."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / ".data" / "game-tower-copy.db"


def main() -> None:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print("tables:", tables)
    for table in tables:
        cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
        print(f"  {table}: {cols[:8]}")
    session_table = next((t for t in tables if "session" in t.lower()), None)
    if session_table is None and "records" in tables:
        rows = conn.execute(
            "SELECT id, data, updated_at FROM records WHERE collection = ? ORDER BY updated_at DESC LIMIT 50",
            ("sessions",),
        ).fetchall()
        for row in rows:
            session = json.loads(row["data"])
            hirelings = session.get("hirelings") or []
            if session.get("mode") == "complete":
                continue
            print(
                "session",
                row["id"],
                "mode",
                session.get("mode"),
                "camped",
                session.get("camped_outside"),
                "hirelings",
                len(hirelings),
                "updated",
                row["updated_at"],
            )
            for hireling in hirelings:
                print("  hireling", hireling.get("name"), "#", hireling.get("marching_order"), hireling.get("retainer_type"))
            for member in session.get("party") or []:
                print("  hero", member.get("name"), "#", member.get("marching_order"))
        return
    if not session_table:
        return
    rows = conn.execute(f"SELECT * FROM {session_table} ORDER BY rowid DESC LIMIT 5").fetchall()
    for row in rows:
        data = dict(row)
        payload_key = next((k for k in data if "payload" in k.lower() or k == "state" or k == "data"), None)
        print("row keys", list(data.keys())[:10])
        if payload_key:
            session = json.loads(data[payload_key])
            print(
                "session",
                session.get("id"),
                "camped",
                session.get("camped_outside"),
                "hirelings",
                len(session.get("hirelings") or []),
            )
            for hireling in session.get("hirelings") or []:
                print("  hireling", hireling.get("name"), "#", hireling.get("marching_order"))
            for member in session.get("party") or []:
                print("  hero", member.get("name"), "#", member.get("marching_order"))


if __name__ == "__main__":
    main()
