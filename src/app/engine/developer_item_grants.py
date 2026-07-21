from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..schemas import Character, PartyMemberState
from .equipment_shop import can_class_use_item
from .item_containers import BAG_OF_CARRYING, add_bag_of_carrying
from .supplement_content_catalog import packaged_rules_dir
from .supplements import LOCKED_CORE_SUPPLEMENT_ID


TABLE_SOURCES: dict[str, tuple[tuple[str, str], ...]] = {
    LOCKED_CORE_SUPPLEMENT_ID: (
        ("dungeon_tables.json", "dungeon_magic_treasure_table"),
        ("dungeon_tables.json", "caverns_special_item_table"),
        ("dungeon_tables.json", "fungal_grottoes_rare_item_table"),
        ("dungeon_tables.json", "fungal_grottoes_rare_mushroom_table"),
        ("dungeon_tables.json", "fiendish_foes_magic_treasure_table"),
    ),
    "four-against-the-abyss": (
        ("abyss_tables.json", "abyss_useful_stuff_table"),
        ("abyss_tables.json", "abyss_magic_treasure_table"),
        ("abyss_tables.json", "abyss_magical_defense_table"),
        ("abyss_tables.json", "abyss_scroll_table"),
    ),
    "forsaken-depths": (
        ("forsaken_depths_tables.json", "fd_heroic_magic_item_table"),
        ("forsaken_depths_tables.json", "fd_legendary_magic_item_table"),
    ),
    "courtship": (
        ("courtship_blossoms_tables.json", "courtship_blossoms_magic_item_table"),
        ("courtship_blossoms_tables.json", "courtship_blossoms_spell_scrolls_table"),
        ("courtship_apothecary_recipes.json", "recipes"),
    ),
}


EXCLUDED_ITEM_FRAGMENTS = (
    "adventurer's dead body",
    "adventurer’s dead body",
    "magic weapon (+1 attack)",
    "magic weapon (+1 or +2 attack)",
    "magic armor (+1 or +2 defense)",
    "wand of power (2d3 charges)",
    "necklace with d6 prayer beads",
    "small gemstone",
    "1d3+1 vials",
    "d3 humming crystals",
    "d6 humming crystals",
    "legendary weapon",
    "legendary armor",
    "rope, lantern, or hand weapon",
)


MANUAL_ITEMS: dict[str, tuple[dict[str, Any], ...]] = {
    LOCKED_CORE_SUPPLEMENT_ID: (
        {"id": "basic-scroll-blessing", "name": "Blessing spell scroll", "category": "magic_scroll", "magic": True, "page": 69, "topic": "Basic spells"},
        {"id": "basic-scroll-escape", "name": "Escape spell scroll", "category": "magic_scroll", "magic": True, "page": 69, "topic": "Basic spells"},
        {"id": "basic-scroll-lightning", "name": "Lightning spell scroll", "category": "magic_scroll", "magic": True, "page": 69, "topic": "Basic spells"},
        {"id": "basic-scroll-fireball", "name": "Fireball spell scroll", "category": "magic_scroll", "magic": True, "page": 69, "topic": "Basic spells"},
        {"id": "basic-scroll-protection", "name": "Protection spell scroll", "category": "magic_scroll", "magic": True, "page": 69, "topic": "Basic spells"},
        {"id": "basic-scroll-sleep", "name": "Sleep spell scroll", "category": "magic_scroll", "magic": True, "page": 69, "topic": "Basic spells"},
        {"id": "magic-club-plus-1", "name": "Magic Club (Light weapon, +1 Attack)", "category": "light_weapon", "magic": True, "page": 158, "topic": "Magic Treasure"},
        {"id": "magic-dagger-plus-1", "name": "Magic Dagger (Light weapon, +1 Attack)", "category": "light_weapon", "magic": True, "page": 158, "topic": "Magic Treasure"},
        {"id": "magic-mace-plus-1", "name": "Magic Mace (Hand weapon, +1 Attack)", "category": "hand_weapon", "magic": True, "page": 158, "topic": "Magic Treasure"},
        {"id": "magic-sword-plus-1", "name": "Magic Sword (Hand weapon, +1 Attack)", "category": "hand_weapon", "magic": True, "page": 158, "topic": "Magic Treasure"},
        {"id": "magic-greatsword-plus-1", "name": "Magic Greatsword (Heavy weapon, +1 Attack)", "category": "two_handed_weapon", "magic": True, "page": 158, "topic": "Magic Treasure"},
        {"id": "magic-bow-plus-1", "name": "Magic Bow (Bow, +1 Attack)", "category": "bow", "magic": True, "page": 158, "topic": "Magic Treasure"},
        {"id": "magic-shield-plus-1", "name": "Magic Shield (+1 Defense)", "category": "shield", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "magic-light-armor-plus-1", "name": "Magic Light Armor (+1 Defense)", "category": "light_armor", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "magic-heavy-armor-plus-1", "name": "Magic Heavy Armor (+1 Defense)", "category": "heavy_armor", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "ring-protection-plus-1", "name": "Ring of Protection (+1 Defense)", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "magic-shield-plus-2", "name": "Magic Shield (+2 Defense)", "category": "shield", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "magic-light-armor-plus-2", "name": "Magic Light Armor (+2 Defense)", "category": "light_armor", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "magic-heavy-armor-plus-2", "name": "Magic Heavy Armor (+2 Defense)", "category": "heavy_armor", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "ring-protection-plus-2", "name": "Ring of Protection (+2 Defense)", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "wand-power-2", "name": "Wand of Power (2 charges)", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "wand-power-3", "name": "Wand of Power (3 charges)", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "wand-power-4", "name": "Wand of Power (4 charges)", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "wand-power-5", "name": "Wand of Power (5 charges)", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "wand-power-6", "name": "Wand of Power (6 charges)", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "prayer-beads-1", "name": "Necklace with 1 prayer bead", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "prayer-beads-2", "name": "Necklace with 2 prayer beads", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "prayer-beads-3", "name": "Necklace with 3 prayer beads", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "prayer-beads-4", "name": "Necklace with 4 prayer beads", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "prayer-beads-5", "name": "Necklace with 5 prayer beads", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "prayer-beads-6", "name": "Necklace with 6 prayer beads", "category": "magic_item", "magic": True, "page": 187, "topic": "Fiendish Foes Magic Treasure"},
        {"id": "epic-book-skalitos", "name": "Book of Skalitos (6 pages)", "category": "magic_item", "magic": True, "page": 163, "topic": "Epic Rewards"},
        {"id": "epic-shield-warning", "name": "Shield of Warning", "category": "shield", "magic": True, "page": 163, "topic": "Epic Rewards"},
        {"id": "epic-holy-symbol", "name": "Holy symbol of healing", "category": "magic_item", "magic": True, "page": 163, "topic": "Epic Rewards"},
        {"id": "fungal-leafsteel", "name": "Leafsteel Armor", "category": "light_armor", "magic": False, "page": 161, "topic": "Fungal Grottoes Rare Items"},
    ),
    "tag": (
        {"id": "bag-of-carrying", "name": BAG_OF_CARRYING, "category": "magic_item", "magic": True, "page": 13, "topic": "Bag of Carrying"},
        {"id": "resurrection-tag", "name": "TAG Resurrection tag", "category": "magic_item", "magic": True, "page": 11, "topic": "Temple tags"},
        {"id": "blessing-tag", "name": "TAG Blessing tag", "category": "magic_item", "magic": True, "page": 11, "topic": "Temple tags"},
    ),
    "forsaken-depths": (
        {"id": "fd-humming-crystal", "name": "Humming Crystal", "category": "magic_item", "magic": True, "page": 49, "topic": "Heroic Magic Items"},
        {"id": "fd-legendary-bow", "name": "Legendary bow", "category": "bow", "magic": True, "page": 50, "topic": "Legendary Magic Items"},
        {"id": "fd-legendary-sling", "name": "Legendary sling", "category": "sling", "magic": True, "page": 50, "topic": "Legendary Magic Items"},
        {"id": "fd-legendary-light-weapon", "name": "Legendary light weapon", "category": "light_weapon", "magic": True, "page": 50, "topic": "Legendary Magic Items"},
        {"id": "fd-legendary-hand-weapon", "name": "Legendary hand weapon", "category": "hand_weapon", "magic": True, "page": 50, "topic": "Legendary Magic Items"},
        {"id": "fd-legendary-two-handed-weapon", "name": "Legendary two-handed weapon", "category": "two_handed_weapon", "magic": True, "page": 50, "topic": "Legendary Magic Items"},
        {"id": "fd-legendary-light-armor", "name": "Legendary light armor", "category": "light_armor", "magic": True, "page": 50, "topic": "Legendary Magic Items"},
        {"id": "fd-legendary-heavy-armor", "name": "Legendary heavy armor", "category": "heavy_armor", "magic": True, "page": 50, "topic": "Legendary Magic Items"},
    ),
}


ITEM_CLASS_ALLOWLISTS: dict[str, set[str]] = {
    "wand of sleep (3 charges)": {"wizard", "illusionist", "elf"},
    "fireball staff (2 charges)": {"wizard"},
    "wand of power (2d3 charges)": {"wizard"},
    "legendary wizard's staff": {"wizard"},
}


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _infer_category(name: str) -> tuple[str, bool]:
    lower = name.casefold()
    magic = any(word in lower for word in (
        "magic", "enchanted", "legendary", "scroll", "wand", "staff", "ring", "amulet",
        "talisman", "gauntlets", "humming crystal", "fools' gold", "lucky boat", "deepbane",
        "pavilion", "calcinator", "mortar of souls",
    ))
    if "scroll" in lower or "parchment" in lower:
        return "magic_scroll", True
    if "potion" in lower or "philter" in lower:
        return "magic_potion", True
    if "crossbow" in lower:
        return "crossbow", magic
    if "bow" in lower and "crossbow" not in lower:
        return "bow", magic
    if "sling" in lower:
        return "sling", magic
    if "shield" in lower:
        return "shield", magic
    if "heavy armor" in lower or "suit of enchanted armor" in lower:
        return "heavy_armor", magic
    if "light armor" in lower or "chain mail" in lower or "leafsteel" in lower:
        return "light_armor", magic
    if any(word in lower for word in ("greatsword", "two-handed weapon")):
        return "two_handed_weapon", magic
    if any(word in lower for word in ("mace", "sword", "baton")) and "greatsword" not in lower:
        return "hand_weapon", magic
    if any(word in lower for word in ("dagger", "club", "stick", "shovel", "stake")):
        return "light_weapon", magic
    return ("magic_item", True) if magic else ("supply", False)


def _row_names(table_id: str, row: dict[str, Any]) -> list[str]:
    if table_id == "abyss_scroll_table" and row.get("name"):
        return [f"Scroll of {row['name']}"]
    if table_id == "recipes" and row.get("item"):
        return [str(row["item"])]
    items = [str(item).strip() for item in row.get("items", []) if str(item).strip()]
    if items:
        return items
    name = str(row.get("item") or row.get("name") or "").strip()
    return [name] if name else []


def _excluded_name(name: str) -> bool:
    lower = name.casefold()
    return " or " in lower or any(fragment in lower for fragment in EXCLUDED_ITEM_FRAGMENTS)


def _table_records(rules_dir: Path, supplement_id: str, filename: str, table_id: str) -> list[dict[str, Any]]:
    path = rules_dir / filename
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get(table_id, []) if isinstance(payload, dict) else []
    records: list[dict[str, Any]] = []
    for index, row in enumerate(rows if isinstance(rows, list) else []):
        if not isinstance(row, dict):
            continue
        for name in _row_names(table_id, row):
            if _excluded_name(name):
                continue
            category, magic = _infer_category(name)
            records.append({
                "id": f"{supplement_id}:{table_id}:{row.get('key') or row.get('roll') or index + 1}:{_slug(name)}",
                "name": name,
                "category": category,
                "magic": magic,
                "summary": str(row.get("summary") or row.get("result") or "").strip(),
                "source": {
                    "supplement_id": supplement_id,
                    "rule_file": filename,
                    "table_id": table_id,
                    "source_page": int(row.get("source_page") or 0),
                },
            })
    return records


def developer_grantable_items(root_dir: Path | None, active_supplement_ids: list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
    rules_dir = packaged_rules_dir(root_dir)
    active = list(dict.fromkeys([LOCKED_CORE_SUPPLEMENT_ID, *active_supplement_ids]))
    records: list[dict[str, Any]] = []
    shop = json.loads((rules_dir / "equipment_shop.json").read_text(encoding="utf-8"))
    for item in shop.get("items", []):
        if item.get("category") == "service":
            continue
        records.append({
            "id": f"{LOCKED_CORE_SUPPLEMENT_ID}:shop:{item['key']}",
            "name": str(item["name"]),
            "category": str(item.get("category") or "supply"),
            "magic": bool(item.get("magic")),
            "summary": str(item.get("notes") or ""),
            "source": {
                "supplement_id": LOCKED_CORE_SUPPLEMENT_ID,
                "rule_file": "equipment_shop.json",
                "table_id": "equipment_shop_table",
                "source_page": int(item.get("source_page") or 0),
            },
        })
    for supplement_id in active:
        for filename, table_id in TABLE_SOURCES.get(supplement_id, ()):
            records.extend(_table_records(rules_dir, supplement_id, filename, table_id))
        for item in MANUAL_ITEMS.get(supplement_id, ()):
            records.append({
                "id": f"{supplement_id}:manual:{item['id']}",
                "name": item["name"],
                "category": item["category"],
                "magic": item["magic"],
                "summary": "",
                "source": {
                    "supplement_id": supplement_id,
                    "rule_file": "structured manual expansion",
                    "table_id": item["topic"],
                    "source_page": item["page"],
                },
            })
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = (record["source"]["supplement_id"], record["name"].casefold())
        unique.setdefault(key, record)
    return sorted(unique.values(), key=lambda row: (row["source"]["supplement_id"], row["category"], row["name"].casefold()))


def item_grant_eligibility(character: Character | PartyMemberState, item: dict[str, Any]) -> tuple[bool, str]:
    allowed, message = can_class_use_item(
        character.class_id,
        {"category": item.get("category"), "magic": bool(item.get("magic"))},
    )
    if not allowed:
        return False, message
    allowlist = ITEM_CLASS_ALLOWLISTS.get(str(item.get("name") or "").casefold())
    if str(item.get("name") or "").casefold().startswith("wand of power ("):
        allowlist = {"wizard"}
    if str(item.get("name") or "").casefold().startswith("necklace with ") and "prayer bead" in str(item.get("name") or "").casefold():
        allowlist = {"cleric"}
    if allowlist is not None and character.class_id.casefold() not in allowlist:
        return False, f"{item['name']} is restricted to {', '.join(sorted(name.title() for name in allowlist))}."
    return True, ""


def grant_inventory_item(character: Character | PartyMemberState, item: dict[str, Any]) -> tuple[bool, str]:
    allowed, message = item_grant_eligibility(character, item)
    if not allowed:
        return False, message
    from .inventory import can_add_item

    item_name = str(item["name"])
    can_carry, message = can_add_item(character, item_name)
    if not can_carry:
        return False, message
    if item_name.casefold() == BAG_OF_CARRYING.casefold():
        add_bag_of_carrying(character)
    else:
        character.inventory.append(item_name)
    return True, f"Developer override: granted {item_name} to {character.name}."
