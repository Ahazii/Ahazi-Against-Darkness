from __future__ import annotations

import json
from pathlib import Path

from app.engine.class_profiles import max_life_for_level, spell_list_for_class
from app.engine.equipment_shop import can_class_use_item, list_shop_for_class
from app.rules.repository import RulesRepository

# Expanded Edition roster (rulebook table of contents, p.19–64).
EXPANDED_EDITION_CLASS_IDS = frozenset(
    {
        "acrobat",
        "assassin",
        "barbarian",
        "bulwark",
        "cleric",
        "dwarf",
        "druid",
        "elf",
        "gnome",
        "halfling",
        "illusionist",
        "kukla",
        "light_gladiator",
        "mushroom_monk",
        "paladin",
        "ranger",
        "rogue",
        "swashbuckler",
        "warrior",
        "wizard",
    }
)


def _rules() -> RulesRepository:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override")


def test_all_expanded_edition_classes_are_selectable() -> None:
    rules = _rules()
    class_ids = {profile.id for profile in rules.classes()}
    assert EXPANDED_EDITION_CLASS_IDS.issubset(class_ids), sorted(EXPANDED_EDITION_CLASS_IDS - class_ids)


def test_classes_expose_rulebook_summaries() -> None:
    rules = _rules()
    for profile in rules.classes():
        assert profile.description.strip(), profile.id
        assert profile.image.startswith("classes/"), profile.id


def test_druid_has_spell_list_and_life_progression() -> None:
    assert "Summon Beast" in spell_list_for_class("druid")
    assert max_life_for_level("druid", 1) == 4


def test_new_classes_have_shop_catalog_rows() -> None:
    catalog = json.loads(
        (Path(__file__).resolve().parents[1] / "data" / "rules" / "equipment_shop.json").read_text(encoding="utf-8")
    )
    for class_id in ("paladin", "acrobat", "kukla", "gnome"):
        rows = list_shop_for_class(catalog, class_id)
        assert rows
        shield = next(item for item in catalog["items"] if item["key"] == "shield")
        allowed, _ = can_class_use_item(class_id, shield)
        assert allowed is (class_id in {"paladin"})
