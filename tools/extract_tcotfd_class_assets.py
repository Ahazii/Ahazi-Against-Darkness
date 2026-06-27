"""Extract TCOTFD and Netherworld class portraits for the character creation UI."""

from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
TCOTFD_PDF = ROOT / "Rules" / "The_Courtship_of_Flower_Demons.pdf"
NETHERWORLD_PDF = ROOT / "Rules" / "Four Against_the_Netherworld.pdf"
CLASSES_PATH = ROOT / "data" / "rules" / "classes.json"
ASSETS_DIR = ROOT / "assets" / "classes"

# PDF page index (0-based) -> portrait image on that page.
TCOTFD_PORTRAITS: dict[str, int] = {
    "wandering_alchemist": 7,
    "satyr": 12,
    "conservationist": 14,
}

NETHERWORLD_PORTRAITS: dict[str, int] = {
    "demonologist": 6,
}

# Crop (left, top, right, bottom) as fractions of width/height on Netherworld p.13 collage.
NETHERWORLD_CROPS: dict[str, tuple[float, float, float, float]] = {
    "cambion": (0.28, 0.30, 0.72, 0.78),
    "succubus": (0.0, 0.0, 1.0, 0.48),
}

NETHERWORLD_COLLAGE_PAGE = 12


def _best_portrait(page) -> Image.Image | None:
    candidates: list[tuple[float, int, Image.Image]] = []
    for _name, img in page.images.items():
        try:
            pil = Image.open(io.BytesIO(img.data))
        except Exception:
            continue
        width, height = pil.size
        if width < 200 or height < 300:
            continue
        ratio = height / width
        if ratio < 0.9:
            continue
        candidates.append((ratio, width * height, pil))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return candidates[0][2]


def _largest_image(page) -> Image.Image | None:
    best: tuple[int, Image.Image] | None = None
    for _name, img in page.images.items():
        try:
            pil = Image.open(io.BytesIO(img.data))
        except Exception:
            continue
        area = pil.size[0] * pil.size[1]
        if best is None or area > best[0]:
            best = (area, pil)
    return best[1] if best else None


def _crop_fractions(image: Image.Image, box: tuple[float, float, float, float]) -> Image.Image:
    width, height = image.size
    left, top, right, bottom = box
    return image.crop(
        (
            int(width * left),
            int(height * top),
            int(width * right),
            int(height * bottom),
        )
    )


def extract_portraits() -> dict[str, str]:
    if not TCOTFD_PDF.exists():
        raise SystemExit(f"Rulebook not found: {TCOTFD_PDF}")
    if not NETHERWORLD_PDF.exists():
        raise SystemExit(f"Rulebook not found: {NETHERWORLD_PDF}")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    extracted: dict[str, str] = {}

    tcotfd = PdfReader(str(TCOTFD_PDF))
    for class_id, page_index in TCOTFD_PORTRAITS.items():
        portrait = _best_portrait(tcotfd.pages[page_index])
        if portrait is None:
            print(f"{class_id}: no portrait on TCOTFD page {page_index + 1}")
            continue
        out = ASSETS_DIR / f"{class_id}.png"
        portrait.save(out, format="PNG")
        extracted[class_id] = f"classes/{class_id}.png"
        print(f"{class_id}: TCOTFD p{page_index + 1} -> {portrait.size}")

    netherworld = PdfReader(str(NETHERWORLD_PDF))
    for class_id, page_index in NETHERWORLD_PORTRAITS.items():
        page = netherworld.pages[page_index]
        portrait = _best_portrait(page) or _largest_image(page)
        if portrait is None:
            print(f"{class_id}: no portrait on Netherworld page {page_index + 1}")
            continue
        out = ASSETS_DIR / f"{class_id}.png"
        portrait.save(out, format="PNG")
        extracted[class_id] = f"classes/{class_id}.png"
        print(f"{class_id}: Netherworld p{page_index + 1} -> {portrait.size}")

    collage = _largest_image(netherworld.pages[NETHERWORLD_COLLAGE_PAGE])
    if collage is None:
        raise SystemExit(f"No collage on Netherworld page {NETHERWORLD_COLLAGE_PAGE + 1}")
    for class_id, box in NETHERWORLD_CROPS.items():
        portrait = _crop_fractions(collage, box)
        out = ASSETS_DIR / f"{class_id}.png"
        portrait.save(out, format="PNG")
        extracted[class_id] = f"classes/{class_id}.png"
        print(f"{class_id}: Netherworld p{NETHERWORLD_COLLAGE_PAGE + 1} crop -> {portrait.size}")

    return extracted


def main() -> None:
    extracted = extract_portraits()
    classes = json.loads(CLASSES_PATH.read_text(encoding="utf-8"))
    for profile in classes:
        class_id = profile.get("id", "")
        if class_id in extracted:
            profile["image"] = extracted[class_id]
    CLASSES_PATH.write_text(json.dumps(classes, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {len(extracted)} class image paths in {CLASSES_PATH.name}")


if __name__ == "__main__":
    main()
