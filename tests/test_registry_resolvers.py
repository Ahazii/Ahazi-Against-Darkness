from __future__ import annotations

from app.engine.states import state_definition_for_status, state_definitions_for_statuses
from app.engine.terrain_registry import terrain_definitions_for_context


def test_state_resolver_matches_legacy_status_shapes() -> None:
    assert state_definition_for_status("Dark Plague")["id"] == "dark-plague"
    assert state_definition_for_status("Cursed (-1 Def)")["id"] == "cursed"
    assert state_definition_for_status("Poisoned L5")["id"] == "poisoned-lingering"
    assert state_definition_for_status("Longsword (poisoned)")["id"] == "envenomed-weapon"


def test_state_resolver_deduplicates_multiple_visible_labels() -> None:
    matches = state_definitions_for_statuses(["Poisoned", "Poisoned L5", "Dark Plague"])
    assert [match["id"] for match in matches] == ["poisoned-lingering", "dark-plague"]


def test_terrain_resolver_matches_environment_terrain_and_catalog() -> None:
    dungeon = terrain_definitions_for_context(environment="dungeon", terrain="indoor")
    assert {entry["id"] for entry in dungeon} >= {"dungeon", "indoor"}

    fd_river = terrain_definitions_for_context(tile_catalog="forsaken_depths_rivers")
    assert [entry["id"] for entry in fd_river] == ["fd-river-bank"]

    assert terrain_definitions_for_context(environment="", terrain=None, tile_catalog=None) == []
