from __future__ import annotations

from .dice import roll_formula

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

# Buffs that do not count as "attack immediately" on the initiative flowchart (p.146).
REACTION_SAFE_COMBAT_SPELLS = frozenset(
    {
        "blessing",
        "healing_prayer",
        "healing",
        "protection",
        "illusionary_armor",
        "illusionary_mirror_image",
        "illusionary_fog",
        "barkskin",
        "bear_form",
    }
)


def spell_commits_to_attack(spell_key: str) -> bool:
    """True when casting skips the optional Reaction roll (Expanded Edition p.146)."""
    if spell_key in EXPLORATION_SPELLS or spell_key in REACTION_SAFE_COMBAT_SPELLS:
        return False
    return True

# Expanded Edition Life: offset + Level (EE class descriptions, p.24–69).
LIFE_OFFSET: dict[str, int] = {
    "warrior": 6,
    "barbarian": 7,
    "bulwark": 7,
    "cleric": 4,
    "rogue": 3,
    "wizard": 2,
    "ranger": 6,
    "dwarf": 5,
    "elf": 4,
    "halfling": 3,
    "druid": 3,
    "illusionist": 2,
    "assassin": 3,
    "acrobat": 3,
    "paladin": 6,
    "swashbuckler": 4,
    "gnome": 4,
    "kukla": 5,
    "light_gladiator": 5,
    "mushroom_monk": 4,
}

# Starting wealth dice (EE p.24–69).
STARTING_WEALTH_ROLL: dict[str, str] = {
    "acrobat": "1d6",
    "assassin": "5d6",
    "barbarian": "1d6",
    "bulwark": "1d6",
    "cleric": "1d6",
    "dwarf": "3d6",
    "druid": "2d6",
    "elf": "2d6",
    "gnome": "4d6",
    "halfling": "2d6",
    "illusionist": "3d6",
    "kukla": "3d6",
    "light_gladiator": "1d6",
    "mushroom_monk": "1d6",
    "paladin": "1d6",
    "ranger": "2d6",
    "rogue": "3d6",
    "swashbuckler": "2d6",
    "warrior": "2d6",
    "wizard": "4d6",
}


def max_life_for_level(class_id: str, level: int) -> int:
    offset = LIFE_OFFSET.get(class_id.lower(), 4)
    return offset + max(1, level)


def roll_starting_wealth(class_id: str) -> int:
    formula = STARTING_WEALTH_ROLL.get(class_id.lower(), "1d6")
    return roll_formula(formula)


def build_starting_inventory(class_id: str, template: list[str]) -> list[str]:
    """Apply rulebook starting-gear rolls where the book uses dice."""
    class_id = class_id.lower()
    if class_id == "halfling":
        rations = roll_formula("1d6+3")
        return [f"Food rations ({rations})", "Sling", "Light hand weapon"]
    if class_id == "ranger":
        rations = roll_formula("1d3")
        return [
            "Hand weapon",
            "Hand weapon",
            "Light hand weapon",
            "Bow",
            "Light armor",
            f"Food rations ({rations})",
        ]
    if class_id == "kukla":
        return ["Dagger", "Doll clothes", "Red ring", "Green ring"]
    return list(template)


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
    if class_id == "paladin":
        return ["Blessing"]
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
    if class_id in {"warrior", "barbarian", "dwarf", "elf", "ranger", "paladin", "assassin", "light_gladiator", "kukla"}:
        notes.append(f"+L melee/ranged attack is now +{level}.")
    elif class_id in {"cleric", "rogue", "druid", "bulwark", "acrobat", "swashbuckler", "illusionist", "gnome", "mushroom_monk"}:
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
    if class_id == "paladin":
        notes.append("Immune to ghost fear events.")
    if class_id == "kukla":
        notes.append("Construct: cannot use bandages; starter gear is built-in.")
    if class_id == "gnome":
        notes.append("May spend Gadget points on lever doors (1 point) when implemented.")
    if class_id in {"rogue", "acrobat"}:
        notes.append(f"+L Defense is now +{level}.")
    return notes
