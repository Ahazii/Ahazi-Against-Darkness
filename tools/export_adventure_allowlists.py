"""Export allowlisted names for AI Adventure prompts and manifest validation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from app.engine.adventure_allowlists import build_adventure_allowlists
from app.rules.repository import RulesRepository


def main() -> int:
    packaged = ROOT / "data" / "rules"
    repo = RulesRepository(packaged, packaged / "_override")
    allowlists = build_adventure_allowlists(repo)
    output = ROOT / "data" / "adventures" / "allowlists.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(allowlists, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(
        f"  foes={len(allowlists['foe_spawn_names'])} "
        f"monsters={len(allowlists['monster_spawn_names'])} "
        f"bosses={len(allowlists['boss_spawn_names'])} "
        f"tiles={len(allowlists['tile_keys'])} "
        f"items={len(allowlists['equipment_items'])} "
        f"traps={len(allowlists['trap_keys'])} "
        f"events={len(allowlists['special_event_keys'])} "
        f"exit_dirs={len(allowlists['exit_directions'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
