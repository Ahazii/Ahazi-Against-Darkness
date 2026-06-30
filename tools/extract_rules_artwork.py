from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "rules" / "artwork_registry.json"


def load_entries() -> list[dict]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return payload.get("entries", [])


def find_entry(entry_id: str) -> dict:
    for entry in load_entries():
        if entry.get("id") == entry_id:
            return entry
    raise SystemExit(f"Artwork entry not found: {entry_id}")


def render_page(pdf_path: Path, page: int, output_prefix: Path) -> Path:
    if shutil.which("pdftoppm") is None:
        raise SystemExit("pdftoppm was not found. Install Poppler or use the bundled runtime that includes it.")
    subprocess.run(
        ["pdftoppm", "-png", "-f", str(page), "-singlefile", str(pdf_path), str(output_prefix)],
        check=True,
    )
    rendered = output_prefix.with_suffix(".png")
    if not rendered.exists():
        raise SystemExit(f"Expected rendered page was not created: {rendered}")
    return rendered


def crop_if_requested(rendered: Path, entry: dict, output_path: Path) -> None:
    crop = entry.get("crop_pct")
    if not crop:
        shutil.copyfile(rendered, output_path)
        return
    try:
        from PIL import Image
    except ImportError as exc:
        raise SystemExit("crop_pct requires Pillow. Install pillow or remove crop_pct for a full-page render.") from exc
    with Image.open(rendered) as image:
        width, height = image.size
        left = int(width * float(crop.get("x", 0)) / 100)
        top = int(height * float(crop.get("y", 0)) / 100)
        right = int(width * float(crop.get("right", 100)) / 100)
        bottom = int(height * float(crop.get("bottom", 100)) / 100)
        image.crop((left, top, right, bottom)).save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a local rules-artwork slot from an owned PDF.")
    parser.add_argument("entry_id", help="Artwork registry id to render.")
    parser.add_argument("--force", action="store_true", help="Overwrite the existing local asset file.")
    args = parser.parse_args()

    entry = find_entry(args.entry_id)
    source_pdf = str(entry.get("source_pdf") or "")
    source_page = int(entry.get("source_page") or 0)
    asset_path = str(entry.get("asset_path") or "")
    if not source_pdf.endswith(".pdf") or source_page <= 0:
        raise SystemExit("This entry does not point at a concrete PDF page.")
    if not asset_path.startswith("rules_art/local/"):
        raise SystemExit("Refusing to write outside assets/rules_art/local/.")

    pdf_path = ROOT / "Rules" / source_pdf
    if not pdf_path.exists():
        raise SystemExit(f"PDF not found: {pdf_path}")
    output_path = ROOT / "assets" / asset_path
    if output_path.exists() and not args.force:
        raise SystemExit(f"Asset already exists. Re-run with --force to overwrite: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rules-art-") as tmp:
        rendered = render_page(pdf_path, source_page, Path(tmp) / "page")
        crop_if_requested(rendered, entry, output_path)
    print(output_path)


if __name__ == "__main__":
    main()
