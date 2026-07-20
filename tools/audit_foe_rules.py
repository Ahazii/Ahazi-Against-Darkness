"""Generate the source-to-runtime audit index for the shipped bestiaries.

This is deliberately an audit aid, not a content importer.  A row is only
marked reviewed after its printed entry and runtime effect have both been
checked.  The report makes the remaining work visible instead of treating a
short summary string as an implemented rule.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "docs" / "audits" / "FOE_RULE_AUDIT.md"

FOE_TABLE_SOURCES: dict[str, dict[str, dict[str, str | int]]] = {
    "monsters.json": {
        "vermin": {"book": "Expanded Edition", "source": "EE core Vermin table"},
        "minions": {"book": "Expanded Edition", "source": "EE core Minions table"},
        "weird": {"book": "Expanded Edition", "source": "EE core Weird Monsters table"},
        "boss": {"book": "Expanded Edition", "source": "EE core Boss Monsters table"},
        "caverns_vermin": {"book": "Expanded Edition", "source": "EE Caverns Vermin table"},
        "caverns_minions": {"book": "Expanded Edition", "source": "EE Caverns Minions table"},
        "caverns_weird": {"book": "Expanded Edition", "source": "EE Caverns Weird Monsters table"},
        "caverns_boss": {"book": "Expanded Edition", "source": "EE Caverns Boss Monsters table"},
        "fungal_grottoes_vermin": {"book": "Expanded Edition", "source": "EE Fungal Grottoes Vermin table"},
        "fungal_grottoes_minions": {"book": "Expanded Edition", "source": "EE Fungal Grottoes Minions table"},
        "fungal_grottoes_weird": {"book": "Expanded Edition", "source": "EE Fungal Grottoes Weird Monsters table"},
        "fungal_grottoes_boss": {"book": "Expanded Edition", "source": "EE Fungal Grottoes Boss Monsters table"},
        "fiendish_foes_vermin": {"book": "Expanded Edition", "source": "EE Fiendish Foes Vermin table"},
        "fiendish_foes_minions": {"book": "Expanded Edition", "source": "EE Fiendish Foes Minions table"},
        "fiendish_foes_weird": {"book": "Expanded Edition", "source": "EE Fiendish Foes Weird Monsters table"},
        "fiendish_foes_boss": {"book": "Expanded Edition", "source": "EE Fiendish Foes Boss Monsters table"},
        "wandering": {"book": "Expanded Edition", "source": "EE wandering-monster table"},
    },
    "fd_monsters.json": {
        "fd_vermin": {"book": "Forsaken Depths", "source": "Forsaken Depths Vermin table", "page": 38},
        "fd_minions": {"book": "Forsaken Depths", "source": "Forsaken Depths Minions table", "page": 40},
        "fd_horde": {"book": "Forsaken Depths", "source": "Forsaken Depths Horde table", "page": 42},
        "fd_boss": {"book": "Forsaken Depths", "source": "Forsaken Depths Boss Monster table", "page": 44},
        "fd_weird": {"book": "Forsaken Depths", "source": "Forsaken Depths Weird Monster and Citadel Weird Monster tables", "page": 45},
    },
    "abyss_tables.json": {
        "abyss_vermin_table": {"book": "Abyss", "source": "Abyss Vermin table", "page": 49},
        "abyss_minions_table": {"book": "Abyss", "source": "Abyss Minions table", "page": 52},
        "abyss_boss_table": {"book": "Abyss", "source": "Abyss Boss table", "page": 55},
        "abyss_weird_table": {"book": "Abyss", "source": "Abyss Weird Monster table", "page": 56},
        "abyss_dragon_table": {"book": "Abyss", "source": "Abyss Dragon table", "page": 58},
    },
    "tag_monsters.json": {
        "tag_minions": {"book": "Tales from the Adventurers Guild", "source": "TAG Rumor/Thematic/Guild Job minion profiles"},
        "tag_weird": {"book": "Tales from the Adventurers Guild", "source": "TAG Weird Monster and generated-lead profiles"},
        "tag_boss": {"book": "Tales from the Adventurers Guild", "source": "TAG Rumor/Thematic/Guild Job Boss profiles"},
    },
}

MECHANIC_FIELDS = (
    "combat_modifiers",
    "encounter_start_effects",
    "on_hit_effects",
    "per_turn_effects",
    "special_attacks",
    "special_rules",
    "vulnerabilities",
)

# These rows have been compared to their precise PDF text and have focused
# runtime tests.  Everything else remains explicit review work.
REVIEWED_ROWS = {
    ("abyss_tables.json", "abyss_vermin_table", "Shrieking Fungi"),
    ("abyss_tables.json", "abyss_minions_table", "Flying Skulls"),
    ("abyss_tables.json", "abyss_boss_table", "Dragon Man"),
    ("abyss_tables.json", "abyss_weird_table", "Phasing Panther"),
    ("tag_monsters.json", "tag_weird", "Star-Slayer from Beyond"),
}

# This set records any deliberate placeholder declaration. It should normally
# remain empty: a prose reminder is not an executable foe rule.
UNHANDLED_DECLARATIONS: set[str] = set()


def _load(filename: str) -> dict[str, Any]:
    return json.loads((ROOT / "data" / "rules" / filename).read_text(encoding="utf-8"))


def foe_rows() -> list[dict[str, Any]]:
    """Return all actual encounter foes, excluding procedure and reaction rows."""
    records: list[dict[str, Any]] = []
    for filename, table_sources in FOE_TABLE_SOURCES.items():
        payload = _load(filename)
        for table, source in table_sources.items():
            for row in payload.get(table, []):
                if not isinstance(row, dict) or not row.get("name"):
                    continue
                mechanics = [
                    f"{field}:{effect.get('type', 'declared')}"
                    for field in MECHANIC_FIELDS
                    for effect in row.get(field, [])
                    if isinstance(effect, dict)
                ]
                records.append({
                    "file": filename,
                    "table": table,
                    "name": str(row["name"]),
                    "source": source,
                    "mechanics": mechanics,
                    "reaction": bool(row.get("reactions") or row.get("reaction_table")),
                    "reviewed": (filename, table, str(row["name"])) in REVIEWED_ROWS,
                    "summary_only": bool((row.get("summary") or row.get("notes")) and not mechanics),
                    "unhandled": [mechanic for mechanic in mechanics if mechanic in UNHANDLED_DECLARATIONS],
                })
    return records


def render_report(records: list[dict[str, Any]]) -> str:
    totals = Counter(record["source"]["book"] for record in records)
    modeled = sum(bool(record["mechanics"]) for record in records)
    reviewed = sum(bool(record["reviewed"]) for record in records)
    summary_only = sum(bool(record["summary_only"]) for record in records)
    unhandled = sum(len(record["unhandled"]) for record in records)
    lines = [
        "# Foe Rule Audit",
        "",
        "**Source of truth:** the owned Expanded Edition, Four Against the Abyss, and Four Against the Forsaken Depths PDFs in `DATA_DIR/rules`.  This index is generated by `python tools/audit_foe_rules.py`.",
        "",
        "## Status",
        "",
        f"- Encounter foe rows in scope: **{len(records)}** ({', '.join(f'{book}: {count}' for book, count in sorted(totals.items()))}).",
        f"- Rows with structured mechanics beyond base stats/reactions: **{modeled}**.",
        f"- Rows fully source-compared with focused runtime tests: **{reviewed}**.",
        f"- Rows that currently have prose notes/summary but no structured mechanic: **{summary_only}**.",
        f"- Declared mechanics with no matching runtime handler: **{unhandled}**.",
        "",
        "A prose summary is not evidence that its full rule is executed. Rows not marked **reviewed** remain open audit work, even when they have a spawn row, a reaction, or basic statistics.",
        "",
        "## Source Table Coverage",
        "",
        "| Book | Source table | Printed page | Rows | Structured mechanics | Reviewed |", 
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault((record["file"], record["table"]), []).append(record)
    for key, group in grouped.items():
        source = group[0]["source"]
        page = source.get("page", "PDF table crosswalk pending")
        lines.append(
            f"| {source['book']} | {source['source']} | {page} | {len(group)} | "
            f"{sum(bool(item['mechanics']) for item in group)} | {sum(bool(item['reviewed']) for item in group)} |"
        )
    lines += ["", "## Row Index", "", "| Book | Foe | Table | Source | Runtime declaration | Review status |", "| --- | --- | --- | --- | --- | --- |"]
    for record in records:
        source = record["source"]
        page = source.get("page")
        reference = f"{source['source']}" + (f" p.{page}" if page else "")
        mechanics = ", ".join(record["mechanics"]) or ("summary only" if record["summary_only"] else "stats/reaction only")
        if record["unhandled"]:
            status = "declared but not runtime-handled"
        else:
            status = "reviewed" if record["reviewed"] else "pending PDF/runtime comparison"
        lines.append(
            f"| {source['book']} | {record['name']} | `{record['table']}` | {reference} | {mechanics} | {status} |"
        )
    lines += [
        "",
        "## Audit Method",
        "",
        "1. Check each printed row against the recorded statistics, count, treasure, morale, reaction, and special wording.",
        "2. Encode every executable instruction as structured foe data and point it at a reusable engine hook; do not leave an executable rule only in `summary` or `notes`.",
        "3. Add a focused regression test for the hook and one row-level test for the printed rule.",
        "4. Move the row into the reviewed set only after steps 1-3 are complete. Update this document and the player Rules Reference/Tables List if the printed source text changes.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    records = foe_rows()
    REPORT_PATH.write_text(render_report(records), encoding="utf-8")
    print(f"Wrote {REPORT_PATH.relative_to(ROOT)} ({len(records)} foe rows).")


if __name__ == "__main__":
    main()
