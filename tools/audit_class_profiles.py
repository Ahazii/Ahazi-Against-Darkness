from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from app.engine.class_profiles import LIFE_OFFSET, STARTING_WEALTH_ROLL, max_life_for_level  # noqa: E402
from tools.extract_class_assets import CLASS_PAGES  # noqa: E402

PDF_PATH = ROOT / "Rules" / "Four_Against_Darkness_Expanded_Edition.pdf"
CLASSES_PATH = ROOT / "data" / "rules" / "classes.json"


def life_offset_from_text(life_text: str) -> tuple[int, int]:
    text = re.sub(r"\s+", "", life_text.strip())
    l1_match = re.search(r"A L1 .+ has (\d+) Life", text, re.I)
    l1_life = int(l1_match.group(1)) if l1_match else None
    if re.search(r"^L\+", text):
        offset = int(re.search(r"^L\+(\d+)", text).group(1))
    elif re.search(r"^\d+\+L", text):
        offset = int(re.search(r"^(\d+)\+L", text).group(1))
    else:
        offset = (l1_life - 1) if l1_life is not None else 4
    if l1_life is None:
        l1_life = offset + 1
    return offset, l1_life


def normalize_wealth_roll(value: str) -> str:
    return value.strip().lower().replace("gp", "").replace(" ", "").replace("1d", "d")


def is_class_life_line(life_text: str) -> bool:
    text = re.sub(r"\s+", "", life_text.strip())
    return bool(re.search(r"^(L\+|\d+\+L)", text)) or bool(re.search(r"A L1 .+ has \d+ Life", text, re.I))


def extract_pdf_class_stats(reader: PdfReader) -> dict[str, dict[str, str | int]]:
    stats: dict[str, dict[str, str | int]] = {}
    for class_id, start_page in CLASS_PAGES.items():
        for page_num in range(start_page, start_page + 4):
            if page_num < 1 or page_num > len(reader.pages):
                continue
            text = reader.pages[page_num - 1].extract_text() or ""
            life_text = ""
            for match in re.finditer(r"Life:\s*([^\n]+)", text):
                candidate = match.group(1).strip()
                if is_class_life_line(candidate):
                    life_text = candidate
                    break
            if not life_text:
                continue
            wealth_match = re.search(r"Starting wealth:\s*([^\n\.]+)", text, re.I)
            offset, l1_life = life_offset_from_text(life_text)
            stats[class_id] = {
                "page": page_num,
                "life_offset": offset,
                "l1_life": l1_life,
                "starting_wealth": wealth_match.group(1).strip() if wealth_match else "",
            }
            break
    return stats


def main() -> None:
    reader = PdfReader(str(PDF_PATH))
    pdf_stats = extract_pdf_class_stats(reader)
    classes = {row["id"]: row for row in json.loads(CLASSES_PATH.read_text(encoding="utf-8"))}
    mismatches: list[str] = []

    for class_id in sorted(classes):
        pdf = pdf_stats.get(class_id)
        if not pdf:
            mismatches.append(f"{class_id}: missing PDF stats")
            continue
        if LIFE_OFFSET[class_id] != pdf["life_offset"]:
            mismatches.append(
                f"{class_id}: life offset engine={LIFE_OFFSET[class_id]} pdf={pdf['life_offset']}"
            )
        if max_life_for_level(class_id, 1) != pdf["l1_life"]:
            mismatches.append(
                f"{class_id}: L1 life engine={max_life_for_level(class_id, 1)} pdf={pdf['l1_life']}"
            )
        pdf_wealth = normalize_wealth_roll(str(pdf["starting_wealth"]))
        engine_wealth = normalize_wealth_roll(STARTING_WEALTH_ROLL[class_id])
        if engine_wealth != pdf_wealth:
            mismatches.append(
                f"{class_id}: wealth engine={STARTING_WEALTH_ROLL[class_id]} pdf={pdf['starting_wealth']}"
            )

    if mismatches:
        print("AUDIT FAILED")
        for line in mismatches:
            print(" ", line)
        raise SystemExit(1)
    print(f"All {len(classes)} classes match Expanded Edition PDF life and wealth rolls.")


if __name__ == "__main__":
    main()
