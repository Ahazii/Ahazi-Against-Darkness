from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.engine.tile_validation import validate_tile_catalog  # noqa: E402
from app.rules.repository import RulesRepository  # noqa: E402


def main() -> int:
    rules_dir = ROOT / "data" / "rules"
    repo = RulesRepository(rules_dir, rules_dir / "_override")
    issues = validate_tile_catalog(repo.tiles())
    if not issues:
        print(f"All {len(repo.tiles())} catalog tiles passed structural validation.")
        return 0
    print(json.dumps(issues, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
