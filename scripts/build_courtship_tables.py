"""One-off builder for courtship_tables.json from the Courtship PDF."""
from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "Rules" / "The_Courtship_of_Flower_Demons.pdf"
OUT = ROOT / "data" / "rules" / "courtship_tables.json"

REGION_PATTERNS = [
    ("seaside", re.compile(r"Seaside Encounter table", re.I)),
    ("riverside", re.compile(r"Riverside Encounter table", re.I)),
    ("woods", re.compile(r"Woods Encounter table", re.I)),
    ("mountain", re.compile(r"Mountain Encounter table", re.I)),
    ("meadows", re.compile(r"Meadows Encounter table", re.I)),
    ("palace", re.compile(r"Queen.?s Garden Palace Encounter table", re.I)),
]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:48] or "encounter"


def _parse_rows(body: str) -> list[dict]:
    rows: list[dict] = []
    chunks = re.split(r"\n(?=\d)", body)
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk or chunk.startswith("*"):
            continue
        m = re.match(r"^(\d+(?:-\d+)?)\s*(.*)", chunk, re.S)
        if not m:
            continue
        roll, rest = m.group(1), re.sub(r"\s+", " ", m.group(2).strip())
        name = rest.split(":")[0].strip() if ":" in rest else rest[:80].strip()
        rows.append(
            {
                "roll": roll,
                "key": _slug(name) or f"roll_{roll.replace('-', '_')}",
                "name": name[:120],
                "summary": rest[:800],
            }
        )
    return rows


def main() -> None:
    reader = PdfReader(str(PDF))
    text = ""
    for page_idx in range(61, 68):
        text += "\n" + (reader.pages[page_idx].extract_text() or "")

    tables: dict[str, list[dict]] = {}
    for region_key, pattern in REGION_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        start = match.end()
        next_start = len(text)
        for _, other_pat in REGION_PATTERNS:
            other = other_pat.search(text, start)
            if other and other.start() < next_start:
                next_start = other.start()
        body = text[start:next_start]
        table_key = f"courtship_{region_key}_encounter_table"
        tables[table_key] = _parse_rows(body)

    payload = {
        "ruleset_status": (
            "Courtship of Flower Demons encounter tables (TCOTFD p.62–68). "
            "Forsaken Depths portal to the Demesne begins at Seaside."
        ),
        "validation": {
            "source": "Rules/The_Courtship_of_Flower_Demons.pdf",
            "courtship_encounter_tables": "p.62-68",
        },
        **tables,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for k, v in tables.items() if k.endswith("_table"))
    print(f"Wrote {OUT} ({total} rows across {len(tables)} tables)")


if __name__ == "__main__":
    main()
