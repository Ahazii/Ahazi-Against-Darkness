from __future__ import annotations

from copy import deepcopy
from typing import Any


SUPPLEMENT_REGISTRY_VERSION = 1
LOCKED_CORE_SUPPLEMENT_ID = "expanded-edition-core"

LEGACY_SUPPLEMENT_FIELDS: list[dict[str, str]] = [
    {
        "field": "ruleset",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Kept for existing saves and random-adventure setup while supplements become the activation model.",
    },
    {
        "field": "ruleset_profile_id",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Still chooses current random-generation profiles; future sessions should snapshot enabled supplement ids.",
    },
    {
        "field": "tile_catalog",
        "status": "legacy_compatibility",
        "replacement": "active_supplements + room_tiles",
        "notes": "Current map generation uses this field until room-tile packs are supplement-owned.",
    },
    {
        "field": "courtship_enabled",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Existing Forsaken Depths profile switch; future behavior should come from supplement activation.",
    },
    {
        "field": "fiendish_foes_enabled",
        "status": "legacy_compatibility",
        "replacement": "active_supplements",
        "notes": "Current optional foe-family flag; future behavior should come from supplement activation.",
    },
    {
        "field": "tag_banking_enabled",
        "status": "legacy_compatibility",
        "replacement": "campaign_supplements",
        "notes": "Campaign preference remains in use until TAG is modeled as an enabled campaign supplement.",
    },
]

SUPPLEMENTS: list[dict[str, Any]] = [
    {
        "id": LOCKED_CORE_SUPPLEMENT_ID,
        "title": "Four Against Darkness Expanded Edition",
        "kind": "core_rules",
        "status": "active",
        "locked": True,
        "enabled_by_default": True,
        "source": {
            "type": "pdf",
            "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "states",
            "rules",
            "room_tiles",
            "terrain_types",
            "generators",
            "rules_reference",
        ],
        "dependencies": [],
        "conflicts": [],
        "legacy_mappings": {
            "ruleset": ["ee"],
            "ruleset_profile_id": ["ee_random"],
            "tile_catalog": ["ee"],
        },
        "notes": "Locked-on base game content. Gameplay still reads current data/rules files during migration.",
    },
    {
        "id": "four-against-the-abyss",
        "title": "Four Against the Abyss",
        "kind": "rules_expansion",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "Four-Against-the-Abyss.pdf",
        },
        "capabilities": [
            "foes",
            "items",
            "tables",
            "states",
            "rules",
            "campaign_state",
            "procedures",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "ruleset_profile_id": ["abyss"],
        },
        "notes": "Abyss-specific tables, afflictions, items, and campaign-state behavior remain wired through existing modules.",
    },
    {
        "id": "forsaken-depths",
        "title": "Four Against the Forsaken Depths",
        "kind": "rules_expansion",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "Four_Against_the_Forsaken_Depths.pdf",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "states",
            "rules",
            "room_tiles",
            "terrain_types",
            "generators",
            "procedures",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "ruleset": ["forsaken_depths"],
            "ruleset_profile_id": ["forsaken_depths", "forsaken_depths_no_courtship"],
            "tile_catalog": ["forsaken_depths", "forsaken_depths_rivers"],
        },
        "notes": "Current terrain, river, tile, and profile behavior stays in existing Forsaken Depths modules.",
    },
    {
        "id": "courtship",
        "title": "The Courtship of Flower Demons",
        "kind": "rules_expansion",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "The_Courtship_of_Flower_Demons.pdf",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "states",
            "rules",
            "terrain_types",
            "locations",
            "procedures",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "courtship_enabled": ["true"],
            "ruleset_profile_id": ["forsaken_depths"],
        },
        "notes": "Courtship content is currently enabled through the Forsaken Depths profile switch.",
    },
    {
        "id": "tag",
        "title": "Tales from the Adventurers' Guild",
        "kind": "campaign",
        "status": "active",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "pdf",
            "source_pdf": "Tales_from_the_adventurers_guild.pdf",
        },
        "capabilities": [
            "tables",
            "states",
            "rules",
            "procedures",
            "locations",
            "campaign_state",
            "generators",
            "narrative",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "tag_banking_enabled": ["true"],
            "adventure_type": ["tag_generated"],
        },
        "notes": "TAG guild, finance, generated-lead, and closeout behavior remains in current campaign/adventure modules.",
    },
    {
        "id": "imported-adventures",
        "title": "Imported Adventure Packages",
        "kind": "imported_pdf",
        "status": "review_only",
        "locked": False,
        "enabled_by_default": False,
        "source": {
            "type": "local_user",
            "source_path": "DATA_DIR/Adventures",
        },
        "capabilities": [
            "foes",
            "classes",
            "items",
            "tables",
            "maps",
            "locations",
            "states",
            "rules",
            "trackers",
            "procedures",
            "artwork",
            "narrative",
        ],
        "dependencies": [LOCKED_CORE_SUPPLEMENT_ID],
        "conflicts": [],
        "legacy_mappings": {
            "adventure_type": ["imported"],
        },
        "notes": "Local reviewed packages can contain exact PDF narrative text. They are not executable rule code.",
    },
]


def supplement_registry() -> list[dict[str, Any]]:
    return deepcopy(SUPPLEMENTS)


def supplement_payload() -> dict[str, Any]:
    return {
        "schema_version": SUPPLEMENT_REGISTRY_VERSION,
        "read_only": True,
        "locked_core_id": LOCKED_CORE_SUPPLEMENT_ID,
        "supplements": supplement_registry(),
        "legacy_fields": deepcopy(LEGACY_SUPPLEMENT_FIELDS),
    }
