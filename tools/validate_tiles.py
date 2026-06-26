from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.engine.tile_catalogs import TILE_CATALOG_KEYS  # noqa: E402
from app.engine.tile_validation import validate_tile_catalog  # noqa: E402
from app.rules.repository import RulesRepository  # noqa: E402


def main() -> int:
    rules_dir = ROOT / "data" / "rules"
    repo = RulesRepository(rules_dir, rules_dir / "_override")
    exit_code = 0
    for catalog in TILE_CATALOG_KEYS:
        tiles = repo.tiles(catalog)
        issues = validate_tile_catalog(tiles, catalog=catalog)
        if not issues:
            print(f"All {len(tiles)} {catalog} catalog tiles passed structural validation.")
            continue
        print(f"{catalog} validation issues:")
        print(json.dumps(issues, indent=2))
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
