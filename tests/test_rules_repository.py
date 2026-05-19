from __future__ import annotations

import json
from pathlib import Path

from app.rules.repository import RulesRepository, VALID_TILE_KEYS


def test_partial_tile_override_does_not_shadow_packaged_status(tmp_path: Path) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    override = tmp_path / "rules"
    override.mkdir()
    packaged_tiles = json.loads((packaged / "tiles.json").read_text(encoding="utf-8"))
    partial = []
    for item in packaged_tiles[:21]:
        copy = dict(item)
        copy["implementation_status"] = "placeholder-needs-rulebook-validation"
        partial.append(copy)
    (override / "tiles.json").write_text(json.dumps(partial, indent=2), encoding="utf-8")

    repo = RulesRepository(packaged, override)
    tiles = repo.tiles()

    assert len(tiles) == len(VALID_TILE_KEYS)
    assert all(tile.implementation_status == "validated" for tile in tiles.values())
