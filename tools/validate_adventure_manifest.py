"""Validate an adventure manifest JSON file."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.engine.adventure_manifest import load_adventure_manifest


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tools/validate_adventure_manifest.py <path-to-adventure.json>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    manifest, result = load_adventure_manifest(path)
    if result.warnings:
        for warning in result.warnings:
            print(f"warning: {warning}")
    if result.errors:
        for error in result.errors:
            print(f"error: {error}")
    if result.valid:
        title = manifest["title"] if manifest else path.name
        room_count = len(manifest["rooms"]) if manifest else 0
        print(f"OK: {title!r} ({room_count} rooms)")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
