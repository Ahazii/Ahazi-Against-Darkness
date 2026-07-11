from __future__ import annotations

import pytest

from app.engine.content_registry import CONTENT_REGISTRY_VERSION, resolve_content_registry
from app.engine.states import resolve_state_registry
from app.engine.terrain_registry import resolve_terrain_registry
from app.engine.table_catalog import resolve_table_catalog
from app.engine.foe_catalog import resolve_foe_catalog
from app.engine.tile_catalog import resolve_tile_catalog


def test_resolved_content_registry_separates_runtime_and_review_only_supplements() -> None:
    context = resolve_content_registry(
        None,
        None,
        ["forsaken-depths", "imported-adventures"],
    )

    assert context.registry_version == CONTENT_REGISTRY_VERSION
    assert context.active_supplement_ids == (
        "expanded-edition-core",
        "forsaken-depths",
        "imported-adventures",
    )
    assert context.runtime_supplement_ids == ("expanded-edition-core", "forsaken-depths")
    assert context.review_only_supplement_ids == ("imported-adventures",)
    assert context.capability_providers["room_tiles"] == ("expanded-edition-core", "forsaken-depths")
    assert context.provides("terrain_types") is True
    assert context.legacy_mappings["ruleset"] == ("ee", "forsaken_depths")
    assert context.state_provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "protection" in context.active_state_ids
    assert "fd-psychic-residue-save" in context.active_state_ids
    assert "dark-plague" not in context.active_state_ids
    assert context.payload()["state_registry_version"] == 1
    assert context.terrain_provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "forest" in context.active_terrain_ids
    assert "fd-river-bank" in context.active_terrain_ids
    assert "courtship-demesne-water" not in context.active_terrain_ids
    assert context.table_provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "trap_table" in context.active_table_ids
    assert "fd_room_content_table" in context.active_table_ids
    assert "abyss_room_content_table" not in context.active_table_ids
    assert context.foe_provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert any(foe_id.startswith("expanded-edition-core-vermin-rats") for foe_id in context.active_foe_ids)
    assert any(foe_id.startswith("forsaken-depths-fd-vermin-shadowbats") for foe_id in context.active_foe_ids)
    assert not any(foe_id.startswith("four-against-the-abyss") for foe_id in context.active_foe_ids)
    assert context.tile_provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "ee:01" in context.active_tile_ids
    assert "forsaken_depths:11" in context.active_tile_ids
    assert "forsaken_depths_rivers:11" in context.active_tile_ids
    assert "review-only" in context.diagnostics[0]


def test_resolved_content_registry_rejects_unknown_supplements() -> None:
    with pytest.raises(ValueError, match="Unknown supplement id"):
        resolve_content_registry(None, None, ["missing-supplement"])


def test_state_registry_scopes_definitions_to_the_locked_supplement_snapshot() -> None:
    catalog = resolve_state_registry(["expanded-edition-core", "four-against-the-abyss"])

    assert catalog.provider_ids == ("four-against-the-abyss", "expanded-edition-core")
    assert "dark-plague" in catalog.state_ids
    assert "protection" in catalog.state_ids
    assert "fd-my-fingers-are-worms" in catalog.excluded_state_ids
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.state_ids)


def test_terrain_registry_scopes_definitions_to_the_locked_supplement_snapshot() -> None:
    catalog = resolve_terrain_registry(["expanded-edition-core", "courtship"])

    assert catalog.provider_ids == ("expanded-edition-core", "courtship")
    assert "forest" in catalog.terrain_ids
    assert "courtship-demesne-water" in catalog.terrain_ids
    assert "fd-river-bank" in catalog.excluded_terrain_ids
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.terrain_ids)


def test_table_catalog_scopes_packaged_table_providers_to_the_locked_snapshot() -> None:
    catalog = resolve_table_catalog(None, ["expanded-edition-core", "courtship"])

    assert catalog.provider_ids == ("expanded-edition-core", "courtship")
    assert "trap_table" in catalog.table_ids
    assert "courtship_seaside_encounter_table" in catalog.table_ids
    assert "abyss_room_content_table" in catalog.excluded_table_ids
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.table_ids)


def test_foe_catalog_scopes_file_and_table_backed_foes_to_the_locked_snapshot() -> None:
    catalog = resolve_foe_catalog(None, ["expanded-edition-core", "four-against-the-abyss"])

    assert catalog.provider_ids == ("expanded-edition-core", "four-against-the-abyss")
    assert any(foe_id.startswith("expanded-edition-core-vermin-rats") for foe_id in catalog.foe_ids)
    assert any(foe_id.startswith("four-against-the-abyss-abyss-vermin-table-black-orc-bandits") for foe_id in catalog.foe_ids)
    assert any(foe_id.startswith("forsaken-depths") for foe_id in catalog.excluded_foe_ids)
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.foe_ids)


def test_tile_catalog_keeps_random_tiles_separate_from_authored_maps() -> None:
    catalog = resolve_tile_catalog(None, ["expanded-edition-core", "forsaken-depths"])

    assert catalog.provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "ee:01" in catalog.tile_ids
    assert "forsaken_depths:11" in catalog.tile_ids
    assert "forsaken_depths_rivers:11" in catalog.tile_ids
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.tile_ids)
