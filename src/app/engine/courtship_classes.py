"""TCOTFD playable classes and cross-book Courtship class hooks (TCOTFD p.7-14, p.31)."""

from __future__ import annotations

from ..schemas import PartyMemberState

MERRY_WOO_CLASS_IDS = frozenset({"halfling", "swashbuckler", "wandering_alchemist", "wandering alchemist"})
NO_WOO_BONUS_CLASS_IDS = frozenset({"cleric", "elf", "paladin", "goblin", "xwart"})
GREEDY_SNEAKY_CLASS_IDS = frozenset({"rogue", "assassin"})
HALF_WOO_CLASS_IDS = frozenset({"wizard", "druid", "demonologist", "conservationist"})
HIDDEN_PATHWAY_CLASS_IDS = frozenset({"paladin", "cambion", "succubus", "cleric"})
MADNESS_SAVE_BONUS_CLASS_IDS = frozenset({"cambion", "succubus"})

BLOSSOMS_SPELL_KEYS = frozenset(
    {
        "aetheric_conversion",
        "bountiful_harvest",
        "flower_portal",
        "fools_gold",
        "libidinal_enhancement",
        "song_of_charm",
    }
)

CONSERVATIONIST_EXTRA_SPELLS = frozenset(
    {
        "blessing",
        "escape",
        "protection",
        "magic_mist",
        "lifeforce_control",
        "healing_surge",
        "mass_teleport",
        "reverse_gaze",
    }
)
CONSERVATIONIST_FORBIDDEN_SPELLS = frozenset(
    {
        "sleep",
        "fireball",
        "lightning",
        "infallible_missile",
        "aura_of_terror",
    }
)


def _class_id(member: PartyMemberState | str) -> str:
    if isinstance(member, str):
        return member.lower().strip()
    return member.class_id.lower().strip()


def is_wandering_alchemist(member: PartyMemberState) -> bool:
    return _class_id(member) in {"wandering_alchemist", "wandering alchemist"}


def is_satyr(member: PartyMemberState) -> bool:
    return _class_id(member) == "satyr"


def is_conservationist(member: PartyMemberState) -> bool:
    return _class_id(member) == "conservationist"


def effective_save_class_id(member: PartyMemberState) -> str:
    """TCOTFD p.8-12 — alchemists save as halflings; satyrs save as barbarians."""
    class_id = _class_id(member)
    if is_wandering_alchemist(member):
        return "halfling"
    if is_satyr(member):
        return "barbarian"
    return class_id


def hidden_pathway_eligible(member: PartyMemberState) -> bool:
    """BoS entry 14 — Riverside shortcut (TCOTFD)."""
    return _class_id(member) in HIDDEN_PATHWAY_CLASS_IDS


def party_has_hidden_pathway_guide(party: list[PartyMemberState]) -> bool:
    return any(member.current_life > 0 and hidden_pathway_eligible(member) for member in party)


def madness_save_level_bonus(member: PartyMemberState) -> int:
    """BoS vault horror — cambions and succubi add level to Madness saves (TCOTFD p.49)."""
    return member.level if _class_id(member) in MADNESS_SAVE_BONUS_CLASS_IDS else 0


def courtship_woo_giving_bonus(member: PartyMemberState) -> int:
    """TCOTFD p.31 class modifiers for Giving rolls."""
    class_id = _class_id(member)
    if class_id == "satyr":
        return member.level * 2
    if class_id in MERRY_WOO_CLASS_IDS:
        return member.level
    if class_id in NO_WOO_BONUS_CLASS_IDS:
        return 0
    if class_id in HALF_WOO_CLASS_IDS or class_id not in MERRY_WOO_CLASS_IDS.union(NO_WOO_BONUS_CLASS_IDS):
        return member.level // 2
    return 0


def courtship_woo_withholding_bonus(member: PartyMemberState) -> int:
    """TCOTFD p.31 — greedy/sneaky classes also add level to Withholding."""
    bonus = courtship_woo_giving_bonus(member)
    if _class_id(member) in GREEDY_SNEAKY_CLASS_IDS:
        bonus += member.level
    return bonus


def courtship_flower_demon_mesmerize_bonus(member: PartyMemberState) -> int:
    """Satyrs add twice their level vs flower-demon mesmerize (TCOTFD p.10)."""
    return member.level * 2 if is_satyr(member) else 0


def satyr_auto_fails_mesmerize(label: str) -> bool:
    lower = label.lower()
    return any(token in lower for token in ("maiden", "lady", "matron"))


def conservationist_allowed_spell(spell_name: str) -> bool:
    from .spells import normalize_spell_name

    key = normalize_spell_name(spell_name)
    if key in CONSERVATIONIST_FORBIDDEN_SPELLS:
        return False
    if key in CONSERVATIONIST_EXTRA_SPELLS:
        return True
    return key in BLOSSOMS_SPELL_KEYS


def is_blossoms_spell_name(spell_name: str) -> bool:
    from .spells import normalize_spell_name

    return normalize_spell_name(spell_name) in BLOSSOMS_SPELL_KEYS


def conservationist_can_cast_spell(spell_name: str) -> tuple[bool, str | None]:
    if conservationist_allowed_spell(spell_name):
        return True, None
    return False, f"Conservationists cannot cast harmful spells such as {spell_name} (TCOTFD p.13)."


def conservationist_spell_slot_count(level: int) -> int:
    """One more slot than wizards (TCOTFD p.13)."""
    return level + 3
