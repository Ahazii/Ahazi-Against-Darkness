"""TCOTFD playable classes and cross-book Courtship class hooks (TCOTFD p.7-14, p.31)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState

if TYPE_CHECKING:
    from ..schemas import SessionState

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


def can_spend_luck_on_woo(member: PartyMemberState) -> bool:
    """Lucky Wooers — halflings may spend Luck on Giving/Withholding (TCOTFD p.31)."""
    return _class_id(member) == "halfling"


def flower_portal_innate_cast(member: PartyMemberState, *, from_scroll: bool) -> bool:
    """Innate Flower Portal by a wandering alchemist (scroll reads do not count as casting)."""
    return is_wandering_alchemist(member) and not from_scroll


def flower_portal_cast_limit(member: PartyMemberState) -> int | None:
    """Wandering alchemists may innately cast Flower Portal once per adventure (TCOTFD p.7-8)."""
    if is_wandering_alchemist(member):
        return 1
    return None


def flower_portal_casts_used(session: SessionState, member: PartyMemberState) -> int:
    return int(session.courtship_flower_portal_casts.get(member.character_id, 0))


def flower_portal_casts_remaining(session: SessionState, member: PartyMemberState) -> int | None:
    limit = flower_portal_cast_limit(member)
    if limit is None:
        return None
    return max(0, limit - flower_portal_casts_used(session, member))


def note_flower_portal_cast(
    session: SessionState,
    member: PartyMemberState,
    *,
    from_scroll: bool = False,
) -> None:
    if not flower_portal_innate_cast(member, from_scroll=from_scroll):
        return
    session.courtship_flower_portal_casts[member.character_id] = 1


def satyr_blossoms_cast_limit(member: PartyMemberState) -> int | None:
    """Once per level, satyrs may cast a single Blossoms spell (TCOTFD p.11)."""
    return member.level if is_satyr(member) else None


def satyr_blossoms_casts_used(session: SessionState, member: PartyMemberState) -> int:
    return int(session.courtship_satyr_blossoms_casts.get(member.character_id, 0))


def satyr_blossoms_casts_remaining(session: SessionState, member: PartyMemberState) -> int | None:
    limit = satyr_blossoms_cast_limit(member)
    if limit is None:
        return None
    return max(0, limit - satyr_blossoms_casts_used(session, member))


def note_satyr_blossoms_cast(session: SessionState, member: PartyMemberState) -> None:
    if satyr_blossoms_cast_limit(member) is None:
        return
    used = satyr_blossoms_casts_used(session, member) + 1
    session.courtship_satyr_blossoms_casts[member.character_id] = used


def conservationist_forbidden_spell_attempt(
    session: SessionState,
    member: PartyMemberState,
    spell_name: str,
    *,
    engine=None,
    show_rolls: bool = True,
) -> tuple[bool, str | None]:
    """Breaking the vow triggers the Curse of Tamas Zeya (BoS entry 16, TCOTFD p.14)."""
    allowed, reason = conservationist_can_cast_spell(spell_name)
    if allowed:
        return True, None
    from .courtship_book_of_secrets import apply_curse_of_tamas_zeya

    apply_curse_of_tamas_zeya(session, member, engine=engine, show_rolls=show_rolls)
    return False, reason or f"Conservationists cannot cast harmful spells such as {spell_name} (TCOTFD p.13)."
