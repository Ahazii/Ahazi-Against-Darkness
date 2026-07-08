from __future__ import annotations

from copy import deepcopy
from typing import Any

from .supplements import LOCKED_CORE_SUPPLEMENT_ID, known_supplement_ids
from .terrain import (
    ENTANGLE_TERRAINS,
    FOREST_PATHWAY_TERRAINS,
    VALID_ENVIRONMENTS,
    VALID_TERRAINS,
    WATER_TERRAINS,
)


TERRAIN_REGISTRY_VERSION = 1

LEGACY_TERRAIN_FIELDS: list[dict[str, str]] = [
    {
        "field": "TileState.environment",
        "status": "legacy_compatibility",
        "replacement": "terrain_instances.environment_id",
        "notes": "Current table-routing environment value, such as dungeon, caverns, or fungal_grottoes.",
    },
    {
        "field": "TileState.terrain",
        "status": "legacy_compatibility",
        "replacement": "terrain_instances.terrain_id",
        "notes": "Current biome/outdoor terrain value used by spells, class abilities, and map context.",
    },
    {
        "field": "SessionState.environment",
        "status": "legacy_compatibility",
        "replacement": "active_supplements + terrain_instances",
        "notes": "Current session default environment remains the fallback for generated map elements.",
    },
    {
        "field": "SessionState.alter_weather_active",
        "status": "legacy_compatibility",
        "replacement": "state_instances + terrain_modifiers",
        "notes": "Weather is currently a session flag layered over the resolved terrain context.",
    },
    {
        "field": "SessionState.forest_pathway_active",
        "status": "legacy_compatibility",
        "replacement": "state_instances + terrain_modifiers",
        "notes": "Forest Pathway is currently a session flag that changes movement/pathway handling.",
    },
]

TERRAIN_DEFINITIONS: list[dict[str, Any]] = [
    {
        "id": "dungeon",
        "name": "Dungeon",
        "kind": "environment",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Standard dungeon environment"},
        "legacy_mappings": {"environment": ["dungeon"]},
        "interactions": ["Default table routing", "Standard indoor assumptions when no terrain overrides are present"],
        "examples": ["A normal random dungeon room uses the dungeon environment and indoor terrain."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Default generated dungeon environment. Used when no Caverns or Fungal Grottoes environment is selected."},
    },
    {
        "id": "caverns",
        "name": "Caverns",
        "kind": "environment",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Caverns environment"},
        "legacy_mappings": {"environment": ["caverns"]},
        "interactions": ["Routes room content to cavern-specific tables", "Hidden pit and cavern special-event logic can apply"],
        "examples": ["A cavern map can still contain indoor-like rooms, but its environment changes which tables and special events are used."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Environment value that tells generation and events to use Caverns rules."},
    },
    {
        "id": "fungal_grottoes",
        "name": "Fungal Grottoes",
        "kind": "environment",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Fungal Grottoes environment"},
        "legacy_mappings": {"environment": ["fungal_grottoes"]},
        "interactions": ["Routes room content to fungal-specific tables", "Fungal merchants, spores, and grotto events can apply"],
        "examples": ["A random dungeon tile can be generated under the Fungal Grottoes environment without becoming outdoor terrain."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Environment value that tells generation and events to use Fungal Grottoes rules."},
    },
    {
        "id": "indoor",
        "name": "Indoor",
        "kind": "terrain",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Indoor/default terrain"},
        "legacy_mappings": {"terrain": ["indoor"]},
        "interactions": ["Default non-outdoor terrain", "Outdoor-only spells and class bonuses do not apply"],
        "examples": ["Most standard dungeon rooms are indoor terrain even when the broader environment is dungeon, caverns, or fungal grottoes."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Default terrain when a tile is not forest, swamp, water, or another outdoor/biome type."},
    },
    {
        "id": "outdoor",
        "name": "Outdoor",
        "kind": "terrain",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Outdoor terrain"},
        "legacy_mappings": {"terrain": ["outdoor"]},
        "interactions": ["Allows outdoor-only effects", "Alter Weather, Lightning Strike, ranger outdoor missile bonuses, and druid companion checks can apply"],
        "examples": ["A wilderness location pinned to a map can use outdoor terrain even if it is not a forest or swamp."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Generic outdoor terrain used when a map location is outside but no more specific biome is recorded."},
    },
    {
        "id": "forest",
        "name": "Forest",
        "kind": "terrain",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Forest terrain"},
        "legacy_mappings": {"terrain": ["forest"]},
        "interactions": ["Counts as outdoor", "Entangle can be used", "Forest Pathway can be used"],
        "examples": ["A forest clearing location can allow Entangle and Forest Pathway while still using a fixed adventure map pin."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Outdoor terrain that supports Entangle and Forest Pathway."},
    },
    {
        "id": "swamp",
        "name": "Swamp",
        "kind": "terrain",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Swamp terrain"},
        "legacy_mappings": {"terrain": ["swamp"]},
        "interactions": ["Counts as outdoor", "Entangle can be used"],
        "examples": ["A swamp hex can allow Entangle but not Forest Pathway under current helper rules."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Outdoor terrain that supports Entangle."},
    },
    {
        "id": "jungle",
        "name": "Jungle",
        "kind": "terrain",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Jungle terrain"},
        "legacy_mappings": {"terrain": ["jungle"]},
        "interactions": ["Counts as outdoor", "Entangle can be used", "Forest Pathway can be used"],
        "examples": ["A jungle trail behaves like outdoor terrain and can satisfy both Entangle and Forest Pathway checks."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Outdoor terrain that supports Entangle and Forest Pathway."},
    },
    {
        "id": "desert",
        "name": "Desert",
        "kind": "terrain",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Desert terrain"},
        "legacy_mappings": {"terrain": ["desert"]},
        "interactions": ["Counts as outdoor", "Water Jet is cast at -2 in current spell logic"],
        "examples": ["A desert ruin still counts as outdoor, but water-based spell handling is penalized."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Outdoor terrain with a current Water Jet penalty."},
    },
    {
        "id": "water",
        "name": "Water",
        "kind": "terrain_group",
        "source": {"supplement_id": LOCKED_CORE_SUPPLEMENT_ID, "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf", "page": 0, "topic": "Water terrain"},
        "legacy_mappings": {"terrain": ["water", "pond", "stream", "river", "lake", "seashore"]},
        "interactions": ["Counts as outdoor", "Water Jet gains water-terrain handling", "Flower Portal can use water terrain or nearby water landscape checks"],
        "examples": ["A river bank, lake shore, seashore, or FD river channel can satisfy water landscape checks for Flower Portal."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Water terrain group used by current spell and Flower Portal logic."},
    },
    {
        "id": "fd-river-bank",
        "name": "Forsaken Depths River Bank",
        "kind": "derived_terrain",
        "source": {"supplement_id": "forsaken-depths", "source_pdf": "Four_Against_the_Forsaken_Depths.pdf", "page": 0, "topic": "Underground river tiles"},
        "legacy_mappings": {"tile_grid_codes": ["1 bank", "2 water channel"], "tile_catalog": ["forsaken_depths_rivers"]},
        "interactions": ["Derived from tile walkable grid", "Can satisfy Flower Portal water landscape checks"],
        "examples": ["An FD river tile with bank cells beside channel cells is treated as a water landscape even if the tile terrain value is not simply water."],
        "review_status": "needs_pdf_page",
        "ui": {"hover": "Derived terrain context for Forsaken Depths underground river maps."},
    },
    {
        "id": "courtship-demesne-water",
        "name": "Courtship Demesne Seaside/Riverside",
        "kind": "derived_terrain",
        "source": {"supplement_id": "courtship", "source_pdf": "The_Courtship_of_Flower_Demons.pdf", "page": 27, "topic": "Flower Portal"},
        "legacy_mappings": {"fields": ["SessionState.courtship_demesne_active", "SessionState.courtship_demesne_region"]},
        "interactions": ["Seaside and Riverside regions satisfy Flower Portal water requirements"],
        "examples": ["Inside the Demesne, Seaside and Riverside count as valid water landscapes for Flower Portal departure."],
        "review_status": "source_backed",
        "ui": {"hover": "Courtship Demesne derived water context for Flower Portal."},
    },
]


def terrain_registry() -> list[dict[str, Any]]:
    return deepcopy(TERRAIN_DEFINITIONS)


def registry_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item or "").strip()]
    if isinstance(value, dict):
        values: list[str] = []
        for item in value.values():
            values.extend(registry_text_list(item))
        return values
    text = str(value).strip()
    return [text] if text else []


def terrain_definitions_for_context(
    *,
    environment: str | None = None,
    terrain: str | None = None,
    tile_catalog: str | None = None,
    terrain_registry_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    values = {
        str(item).strip().lower()
        for item in (environment, terrain, tile_catalog)
        if str(item or "").strip()
    }
    if not values:
        return []
    registry = terrain_registry_records if terrain_registry_records is not None else TERRAIN_DEFINITIONS
    matches: list[dict[str, Any]] = []
    for definition in registry:
        mappings = definition.get("legacy_mappings") if isinstance(definition.get("legacy_mappings"), dict) else {}
        mapped_values = [
            str(definition.get("id") or ""),
            *registry_text_list(mappings.get("environment")),
            *registry_text_list(mappings.get("terrain")),
            *registry_text_list(mappings.get("tile_catalog")),
        ]
        normalized = {item.strip().lower() for item in mapped_values if item.strip()}
        if values.intersection(normalized):
            matches.append(deepcopy(definition))
    return matches


def terrain_registry_diagnostics(terrain: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    registry = terrain if terrain is not None else TERRAIN_DEFINITIONS
    diagnostics: list[dict[str, str]] = []
    seen: set[str] = set()
    supplements = known_supplement_ids()
    for index, record in enumerate(registry):
        terrain_id = str(record.get("id") or "").strip()
        path = terrain_id or f"terrain[{index}]"
        if not terrain_id:
            diagnostics.append({"severity": "error", "path": path, "message": "Terrain record is missing id."})
            continue
        if terrain_id in seen:
            diagnostics.append({"severity": "warning", "path": terrain_id, "message": f"Duplicate terrain id {terrain_id!r}."})
        seen.add(terrain_id)
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        supplement_id = str(source.get("supplement_id") or "").strip()
        if supplement_id and supplement_id not in supplements:
            diagnostics.append({"severity": "warning", "path": terrain_id, "message": f"Terrain {terrain_id!r} references unknown supplement {supplement_id!r}."})
        if record.get("review_status") == "source_backed" and int(source.get("page") or 0) <= 0:
            diagnostics.append({"severity": "warning", "path": terrain_id, "message": f"Terrain {terrain_id!r} is source_backed but has no positive source page."})
        if not record.get("legacy_mappings"):
            diagnostics.append({"severity": "info", "path": terrain_id, "message": f"Terrain {terrain_id!r} has no legacy mapping yet."})
    return diagnostics


def terrain_payload() -> dict[str, Any]:
    terrain = terrain_registry()
    return {
        "schema_version": TERRAIN_REGISTRY_VERSION,
        "read_only": True,
        "terrain": terrain,
        "diagnostics": terrain_registry_diagnostics(terrain),
        "legacy_fields": deepcopy(LEGACY_TERRAIN_FIELDS),
        "environment_values": sorted(VALID_ENVIRONMENTS),
        "terrain_values": sorted(VALID_TERRAINS),
        "water_values": sorted(WATER_TERRAINS),
        "entangle_values": sorted(ENTANGLE_TERRAINS),
        "forest_pathway_values": sorted(FOREST_PATHWAY_TERRAINS),
        "kinds": sorted({item["kind"] for item in terrain}),
    }
