from __future__ import annotations

from pathlib import Path

import pytest

from app.engine.content_registry import CONTENT_REGISTRY_VERSION, resolve_content_registry
from app.engine.states import resolve_state_registry
from app.engine.terrain_registry import resolve_terrain_registry
from app.engine.table_catalog import resolve_table_catalog
from app.engine.foe_catalog import resolve_foe_catalog
from app.engine.tile_catalog import resolve_tile_catalog
from app.engine.class_catalog import resolve_class_catalog
from app.engine.item_catalog import resolve_item_catalog
from app.engine.supplements import declared_content_sources


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
    assert context.class_provider_ids == ("expanded-edition-core",)
    assert "warrior" in context.active_class_ids
    assert "satyr" not in context.active_class_ids
    assert context.item_provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "bow" in context.active_item_ids
    assert any(item_id.startswith("forsaken-depths-fd-heroic-magic-item-table") for item_id in context.active_item_ids)
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


def test_table_catalog_reads_declared_manifest_table_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = resolve_table_catalog(root, ["expanded-edition-core", "four-against-the-abyss"])

    assert "trap_table" in catalog.table_ids
    assert "abyss_room_content_table" in catalog.table_ids
    assert "fd_room_content_table" in catalog.excluded_table_ids


def test_foe_catalog_scopes_file_and_table_backed_foes_to_the_locked_snapshot() -> None:
    catalog = resolve_foe_catalog(None, ["expanded-edition-core", "four-against-the-abyss"])

    assert catalog.provider_ids == ("expanded-edition-core", "four-against-the-abyss")
    assert any(foe_id.startswith("expanded-edition-core-vermin-rats") for foe_id in catalog.foe_ids)
    assert any(foe_id.startswith("four-against-the-abyss-abyss-vermin-table-black-orc-bandits") for foe_id in catalog.foe_ids)
    assert any(foe_id.startswith("forsaken-depths") for foe_id in catalog.excluded_foe_ids)
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.foe_ids)


def test_foe_catalog_reads_declared_manifest_foe_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = resolve_foe_catalog(root, ["expanded-edition-core", "four-against-the-abyss"])

    assert any(foe_id.startswith("expanded-edition-core-vermin-rats") for foe_id in catalog.foe_ids)
    assert any(foe_id.startswith("four-against-the-abyss-abyss-vermin-table") for foe_id in catalog.foe_ids)
    assert not any("abyss-room-content" in foe_id for foe_id in catalog.foe_ids)


def test_tile_catalog_keeps_random_tiles_separate_from_authored_maps() -> None:
    catalog = resolve_tile_catalog(None, ["expanded-edition-core", "forsaken-depths"])

    assert catalog.provider_ids == ("expanded-edition-core", "forsaken-depths")
    assert "ee:01" in catalog.tile_ids
    assert "forsaken_depths:11" in catalog.tile_ids
    assert "forsaken_depths_rivers:11" in catalog.tile_ids
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.tile_ids)


def test_tile_catalog_reads_declared_manifest_tile_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    declared = declared_content_sources(root, None, "room_tiles")
    catalog = resolve_tile_catalog(root, ["expanded-edition-core", "forsaken-depths"])

    assert {entry["path"] for entry in declared} >= {
        "data/rules/tiles.json",
        "data/rules/forsaken_depths_tiles.json",
        "data/rules/forsaken_depths_rivers_tiles.json",
    }
    assert "ee:01" in catalog.tile_ids
    assert "forsaken_depths_rivers:11" in catalog.tile_ids


def test_class_catalog_reads_existing_supplement_ownership_metadata() -> None:
    catalog = resolve_class_catalog(None, ["expanded-edition-core", "courtship"])

    assert catalog.provider_ids == ("expanded-edition-core", "courtship")
    assert "warrior" in catalog.class_ids
    assert "satyr" in catalog.class_ids
    assert "satyr" not in catalog.excluded_class_ids


def test_class_catalog_requires_declared_manifest_class_source() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = resolve_class_catalog(root, ["expanded-edition-core", "courtship"])

    assert catalog.provider_ids == ("expanded-edition-core", "courtship")
    assert "warrior" in catalog.class_ids
    assert "satyr" in catalog.class_ids


def test_item_catalog_keeps_direct_equipment_and_table_backed_rewards_distinct() -> None:
    catalog = resolve_item_catalog(None, ["expanded-edition-core", "four-against-the-abyss"])

    assert catalog.provider_ids == ("expanded-edition-core", "four-against-the-abyss")
    assert "bow" in catalog.item_ids
    assert any(item_id.startswith("four-against-the-abyss-abyss-useful-stuff-table") for item_id in catalog.item_ids)
    assert {definition["id"] for definition in catalog.definitions()} == set(catalog.item_ids)


def test_item_catalog_reads_declared_manifest_item_sources() -> None:
    root = Path(__file__).resolve().parents[1]
    catalog = resolve_item_catalog(root, ["expanded-edition-core", "courtship"])

    assert "bow" in catalog.item_ids
    assert any(item_id.startswith("courtship-courtship-blossoms-magic-item-table") for item_id in catalog.item_ids)
