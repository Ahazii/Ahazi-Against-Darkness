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


def test_all_packaged_map_elements_are_rulebook_validated() -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    tiles = json.loads((packaged / "tiles.json").read_text(encoding="utf-8"))
    statuses = {item["key"]: item.get("implementation_status") for item in tiles}

    assert set(statuses) == set(VALID_TILE_KEYS)
    assert all(status == "validated" for status in statuses.values())


def test_save_tiles_writes_override_without_mutating_packaged_rules(tmp_path: Path) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    override = tmp_path / "rules"
    before = (packaged / "tiles.json").read_text(encoding="utf-8")
    repo = RulesRepository(packaged, override)
    tiles = list(repo.tiles().values())
    tiles[0].implementation_status = "test-edited"

    repo.save_tiles(tiles)

    assert (packaged / "tiles.json").read_text(encoding="utf-8") == before
    assert (override / "tiles.json").exists()
    saved = json.loads((override / "tiles.json").read_text(encoding="utf-8"))
    assert saved[0]["implementation_status"] == "test-edited"


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


def test_partial_monsters_override_preserves_packaged_treasure_rolls(tmp_path: Path) -> None:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    override = tmp_path / "rules"
    override.mkdir()
    stub = {
        "boss": [
            {
                "name": "Young Dragon",
                "level_delta": 6,
                "count": "1",
                "life": 8,
                "attacks": 3,
                "tags": ["boss", "dragon"],
            },
            {
                "name": "Dragon",
                "level_delta": 6,
                "count": "1",
                "life": 8,
                "attacks": 3,
                "tags": ["boss", "dragon"],
            },
        ],
    }
    (override / "monsters.json").write_text(json.dumps(stub, indent=2), encoding="utf-8")

    repo = RulesRepository(packaged, override)
    monsters = repo.monsters()
    young_dragon = next(row for row in monsters["boss"] if row["name"] == "Young Dragon")
    assert young_dragon.get("treasure_rolls") == 3
    assert young_dragon.get("life") == 8
    dragon = next(row for row in monsters["boss"] if row["name"] == "Dragon")
    assert dragon.get("life") == 8
