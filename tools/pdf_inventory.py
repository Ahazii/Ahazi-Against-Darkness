from __future__ import annotations

import argparse
from pathlib import Path

from pypdf import PdfReader


def inventory(path: Path) -> None:
    reader = PdfReader(str(path))
    print(f"{path}")
    print(f"  pages: {len(reader.pages)}")
    print(f"  encrypted: {reader.is_encrypted}")
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            print(f"  decrypt: failed ({exc})")

    text_pages = 0
    image_pages: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            text_pages += 1
        try:
            image_count = len(page.images)
        except Exception:
            image_count = 0
        if image_count:
            image_pages.append(f"{index}:{image_count}")
    print(f"  text_pages: {text_pages}/{len(reader.pages)}")
    print(f"  image_pages: {', '.join(image_pages[:20])}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inventory local RPG PDFs.")
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.paths:
        if path.is_dir():
            for pdf in sorted(path.glob("*.pdf")):
                inventory(pdf)
        else:
            inventory(path)


if __name__ == "__main__":
    main()
