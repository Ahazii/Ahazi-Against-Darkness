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
    overridden_keys = {item["key"] for item in partial}

    assert len(tiles) == len(VALID_TILE_KEYS)
    for key in overridden_keys:
        packaged_status = next(item["implementation_status"] for item in packaged_tiles if item["key"] == key)
        assert tiles[key].implementation_status == packaged_status
        assert tiles[key].implementation_status != "placeholder-needs-rulebook-validation"


def test_partial_classes_override_includes_new_packaged_classes(tmp_path: Path) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    override = tmp_path / "rules"
    override.mkdir()
    stale = [
        {"id": "warrior", "name": "Warrior", "base_life": 5, "attack_bonus": 1, "defense_bonus": 0, "save_bonus": 0,
         "starting_gold": 10, "starting_inventory": ["Hand weapon"], "starting_spells": [], "abilities": []},
        {"id": "cleric", "name": "Cleric", "base_life": 4, "attack_bonus": 0, "defense_bonus": 1, "save_bonus": 0,
         "starting_gold": 10, "starting_inventory": ["Mace"], "starting_spells": ["Blessing"], "abilities": []},
    ]
    (override / "classes.json").write_text(json.dumps(stale, indent=2), encoding="utf-8")

    repo = RulesRepository(packaged, override)
    class_ids = {profile.id for profile in repo.classes()}

    assert "druid" in class_ids
    assert "paladin" in class_ids
    assert len(class_ids) >= 20
    warrior = repo.class_by_id("warrior")
    assert warrior is not None
    assert warrior.starting_inventory == ["Hand weapon"]
    assert warrior.description.strip()
    assert warrior.image.startswith("classes/")
