from __future__ import annotations

from ..schemas import PartyMemberState

# EE p.165 toxic mushrooms: rogues and foresters (+L). Include supplement outdoor class ids.
CAVERNS_FORESTER_TRAP_CLASSES = frozenset(
    {
        "ranger",
        "druid",
        "wood_elf",
        "wilderness_scout",
        "conservationist",
    }
)


def is_mushroom_class(class_id: str) -> bool:
    """Any PC class with 'mushroom' in the id (monk + supplement mushroom classes)."""
    return "mushroom" in class_id.lower()


def is_caverns_forester_class(class_id: str) -> bool:
    return class_id.lower() in CAVERNS_FORESTER_TRAP_CLASSES


def caverns_toxic_mushroom_lead_ignores_trap(lead: PartyMemberState) -> bool:
    return is_mushroom_class(lead.class_id)


def caverns_toxic_mushroom_immune(member: PartyMemberState) -> bool:
    return is_mushroom_class(member.class_id)
