from __future__ import annotations

WIZARD_BASIC_SPELLS = ("Blessing", "Escape", "Lightning", "Fireball", "Protection", "Sleep")
ELF_BASIC_SPELLS = tuple(spell for spell in WIZARD_BASIC_SPELLS if spell != "Blessing")
DRUID_SPELLS = (
    "Disperse Vermin",
    "Summon Beast",
    "Water Jet",
    "Bear Form",
    "Warp Wood",
    "Barkskin",
    "Lightning Strike",
    "Spiderweb",
    "Entangle",
    "Subdual",
    "Forest Pathway",
    "Alter Weather",
)
ILLUSIONIST_SPELLS = (
    "Illusionary Armor",
    "Illusionary Mirror Image",
    "Illusionary Servant",
    "Disbelief",
    "Phantasmal Binding",
    "Illusionary Fog",
    "Glamour Mask",
    "Shadow Strike",
    "Specter Swarm",
    "Mirage of Fortune",
    "Illusionary Banquet",
    "Illusionary Sword",
)
EXPLORATION_SPELLS = frozenset(
    {
        "escape",
        "blessing",
        "healing_prayer",
        "healing",
        "protection",
        "warp_wood",
        "glamour_mask",
        "forest_pathway",
        "alter_weather",
        "illusionary_servant",
        "illusionary_banquet",
    }
)

# Expanded Edition Life: offset + Level (wizard uses 2 + Level).
LIFE_OFFSET: dict[str, int] = {
    "warrior": 6,
    "barbarian": 7,
    "bulwark": 7,
    "cleric": 4,
    "rogue": 3,
    "wizard": 2,
    "ranger": 4,
    "dwarf": 5,
    "elf": 4,
    "halfling": 3,
    "druid": 3,
    "illusionist": 2,
    "assassin": 3,
    "acrobat": 3,
    "paladin": 5,
    "swashbuckler": 4,
}


def max_life_for_level(class_id: str, level: int) -> int:
    offset = LIFE_OFFSET.get(class_id.lower(), 4)
    return offset + max(1, level)


def spell_slot_count(class_id: str, level: int) -> int | None:
    class_id = class_id.lower()
    if class_id == "wizard":
        return level + 2
    if class_id == "elf":
        return level
    if class_id == "druid":
        return level + 2
    if class_id == "illusionist":
        return level + 3
    return None


def level_up_grants_spell_slot(class_id: str) -> bool:
    return spell_slot_count(class_id, 2) is not None


def available_level_up_spells(class_id: str) -> list[str]:
    class_id = class_id.lower()
    if class_id == "elf":
        return list(ELF_BASIC_SPELLS)
    if class_id == "druid":
        return list(DRUID_SPELLS)
    if class_id == "illusionist":
        return list(ILLUSIONIST_SPELLS)
    if class_id == "wizard":
        return list(WIZARD_BASIC_SPELLS)
    return []


def spell_list_for_class(class_id: str) -> list[str]:
    class_id = class_id.lower()
    if class_id == "cleric":
        return ["Blessing", "Healing prayer"]
    if class_id == "druid":
        return list(DRUID_SPELLS)
    if class_id == "illusionist":
        return list(ILLUSIONIST_SPELLS)
    if class_id == "elf":
        return list(ELF_BASIC_SPELLS)
    if class_id == "wizard":
        return list(WIZARD_BASIC_SPELLS)
    return []


def barbarian_rage_uses(level: int) -> int:
    return 1 + level // 2


def halfling_luck_points(level: int) -> int:
    return level + 1


def level_up_benefit_notes(class_id: str, level: int) -> list[str]:
    class_id = class_id.lower()
    notes: list[str] = []
    if class_id in {"warrior", "barbarian", "dwarf", "elf", "ranger", "paladin", "assassin"}:
        notes.append(f"+L melee/ranged attack is now +{level}.")
    elif class_id in {"cleric", "rogue", "druid", "bulwark", "acrobat", "swashbuckler", "illusionist"}:
        notes.append(f"+1/2 L combat bonuses are now +{level // 2}.")
    if class_id == "cleric":
        notes.append(f"Healing prayer restores d6+{level} Life (3 uses per adventure).")
    if class_id == "wizard":
        notes.append(f"Wizard spell slots: {spell_slot_count(class_id, level)} (L+2).")
    if class_id == "elf":
        notes.append(f"Elf spell slots: {spell_slot_count(class_id, level)} (1 per Level).")
    if class_id == "druid":
        notes.append(f"Druid spell slots: {spell_slot_count(class_id, level)} (2+L).")
    if class_id == "illusionist":
        notes.append(f"Illusionist spell slots: {spell_slot_count(class_id, level)} (L+3).")
    if class_id == "barbarian":
        notes.append(f"Rage attacks per adventure: {barbarian_rage_uses(level)}.")
        notes.append("May not use magic items, scrolls, or potions (may carry for allies).")
    if class_id == "halfling":
        notes.append(f"Luck points per adventure: {halfling_luck_points(level)}.")
    if class_id in {"rogue", "acrobat"}:
        notes.append(f"+L Defense is now +{level}.")
    return notes
