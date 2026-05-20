from __future__ import annotations

import io
import json
import re
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "Rules" / "Four_Against_Darkness_Expanded_Edition.pdf"
CLASSES_PATH = ROOT / "data" / "rules" / "classes.json"
ASSETS_DIR = ROOT / "assets" / "classes"

CLASS_PAGES: dict[str, int] = {
    "acrobat": 24,
    "assassin": 27,
    "barbarian": 29,
    "bulwark": 31,
    "cleric": 33,
    "dwarf": 35,
    "druid": 37,
    "elf": 39,
    "gnome": 41,
    "halfling": 45,
    "illusionist": 47,
    "kukla": 49,
    "light_gladiator": 54,
    "mushroom_monk": 56,
    "paladin": 60,
    "ranger": 62,
    "rogue": 65,
    "swashbuckler": 66,
    "warrior": 68,
    "wizard": 69,
}

CLASS_TITLES = {class_id: class_id.replace("_", " ").title() for class_id in CLASS_PAGES}
CLASS_TITLES["kukla"] = "Kukla"
CLASS_TITLES["light_gladiator"] = "Light Gladiator"
CLASS_TITLES["mushroom_monk"] = "Mushroom Monk"

TEMPLATE_SIZE = (587, 880)
WATERMARK_RE = re.compile(r"James Banner \(Order #\d+\)")


def _clean_text(text: str) -> str:
    text = WATERMARK_RE.sub("", text)
    text = text.replace("\ufffd", "'")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_description(page_text: str, class_title: str) -> str:
    text = _clean_text(page_text)
    match = re.search(rf"{re.escape(class_title)}\s*\n(.+)", text, flags=re.DOTALL)
    if not match:
        return ""
    body = match.group(1)
    body = re.split(r"\n(?:Optional (?:Character )?Trait|(?:\w+ )*Traits Table)", body, maxsplit=1)[0]
    body = re.sub(r"\n(?=[a-z(])", " ", body)
    body = re.sub(r"\s{2,}", " ", body)
    body = body.replace("\ufffd", "½")
    return body.strip()


def extract_portrait(page) -> Image.Image | None:
    candidates: list[tuple[float, int, Image.Image]] = []
    for _name, img in page.images.items():
        try:
            pil = Image.open(io.BytesIO(img.data))
        except Exception:
            continue
        if pil.size == TEMPLATE_SIZE:
            continue
        width, height = pil.size
        if width <= 0:
            continue
        portrait_score = height / width
        candidates.append((portrait_score, width * height, pil))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(f"Rulebook not found: {PDF_PATH}")

    reader = PdfReader(str(PDF_PATH))
    classes = json.loads(CLASSES_PATH.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in classes}

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    for class_id, page_number in CLASS_PAGES.items():
        title = CLASS_TITLES[class_id]
        page = reader.pages[page_number - 1]
        page_text = page.extract_text() or ""
        description = extract_description(page_text, title)
        portrait = extract_portrait(page)
        image_path = ""
        if portrait is not None:
            out = ASSETS_DIR / f"{class_id}.png"
            portrait.save(out, format="PNG")
            image_path = f"classes/{class_id}.png"

        profile = by_id.get(class_id)
        if profile is None:
            print(f"skip missing class id: {class_id}")
            continue
        profile["description"] = description
        profile["image"] = image_path
        print(f"{class_id}: {len(description)} chars, image={'yes' if image_path else 'no'}")

    CLASSES_PATH.write_text(json.dumps(classes, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
