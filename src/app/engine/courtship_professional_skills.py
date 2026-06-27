"""TCOTFD p.8-9 / p.13-14 — Surgeon, Herbalist, and Poison Expert hireling training for alchemists."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState
from .courtship_classes import is_conservationist, is_wandering_alchemist
from .expert_skills import has_skill

if TYPE_CHECKING:
    pass

TRAINED_SURGEON = "trained_surgeon"
TRAINED_HERBALIST = "trained_herbalist"
TRAINED_POISON_EXPERT = "trained_poison_expert"

TRAINED_PROFESSIONAL_SKILL_IDS = frozenset(
    {TRAINED_SURGEON, TRAINED_HERBALIST, TRAINED_POISON_EXPERT}
)


def member_has_trained_surgeon(member: PartyMemberState) -> bool:
    return has_skill(member, TRAINED_SURGEON)


def member_has_trained_herbalist(member: PartyMemberState) -> bool:
    return has_skill(member, TRAINED_HERBALIST)


def member_has_trained_poison_expert(member: PartyMemberState) -> bool:
    return has_skill(member, TRAINED_POISON_EXPERT)


def eligible_trained_professional_skill(member: PartyMemberState, skill_id: str) -> bool:
    normalized = skill_id.strip().lower()
    if normalized == TRAINED_POISON_EXPERT:
        return is_wandering_alchemist(member) and member_has_trained_poison_expert(member)
    if normalized == TRAINED_SURGEON:
        return (is_wandering_alchemist(member) or is_conservationist(member)) and member_has_trained_surgeon(
            member
        )
    if normalized == TRAINED_HERBALIST:
        return (is_wandering_alchemist(member) or is_conservationist(member)) and member_has_trained_herbalist(
            member
        )
    return False


def _provider(session: SessionState, provider_id: str | None) -> PartyMemberState | None:
    if not provider_id:
        return None
    return next((member for member in session.party if member.character_id == provider_id), None)


def _ability_used(session: SessionState, provider_id: str, ability: str) -> bool:
    used = session.professional_skill_uses.get(provider_id, [])
    return ability in used


def _mark_ability_used(session: SessionState, provider_id: str, ability: str) -> None:
    used = dict(session.professional_skill_uses or {})
    entries = list(used.get(provider_id, []))
    if ability not in entries:
        entries.append(ability)
    used[provider_id] = entries
    session.professional_skill_uses = used


def clear_professional_skill_uses(session: SessionState) -> None:
    session.professional_skill_uses = {}


def member_has_arsenic(member: PartyMemberState) -> bool:
    return any("arsenic" in item.lower() for item in member.inventory)


def consume_arsenic(member: PartyMemberState) -> bool:
    for index, item in enumerate(member.inventory):
        if "arsenic" in item.lower():
            member.inventory.pop(index)
            return True
    return False


def use_trained_surgeon_heal(session: SessionState, provider_id: str | None) -> list[str]:
    if session.mode != "exploration":
        return ["Use field surgery during exploration."]
    provider = _provider(session, provider_id)
    if provider is None or provider.current_life <= 0:
        return ["Choose a living hero trained as a surgeon."]
    if not member_has_trained_surgeon(provider):
        return [f"{provider.name} is not trained as a surgeon (TCOTFD)."]
    if _ability_used(session, provider.character_id, "surgeon_heal"):
        return [f"{provider.name} already tended the party this adventure."]
    _mark_ability_used(session, provider.character_id, "surgeon_heal")
    log = [f"{provider.name} stitches wounds beyond bandages (+2 Life each, TCOTFD)."]
    for member in session.party:
        if member.current_life <= 0:
            continue
        before = member.current_life
        member.current_life = min(member.max_life, member.current_life + 2)
        gained = member.current_life - before
        if gained:
            log.append(f"{member.name} recovers {gained} Life.")
    return log


def use_trained_herbalist(session: SessionState, provider_id: str | None) -> list[str]:
    if not session.camped_outside:
        return ["Apply herbalist training while camped outside the dungeon."]
    provider = _provider(session, provider_id)
    if provider is None or provider.current_life <= 0:
        return ["Choose a living hero trained as an herbalist."]
    if not member_has_trained_herbalist(provider):
        return [f"{provider.name} is not trained as an herbalist (TCOTFD)."]
    if _ability_used(session, provider.character_id, "herbalist_camp"):
        return [f"{provider.name} already prepared herbal remedies this camp."]
    buffs = dict(session.professional_buffs or {})
    if buffs.get("herbalist_saves"):
        return ["The party already has herbalist save bonuses for the next foray."]
    _mark_ability_used(session, provider.character_id, "herbalist_camp")
    buffs["herbalist_saves"] = True
    session.professional_buffs = buffs
    return [
        f"{provider.name} brews herbal remedies for the party (free; +1 saves vs poison and disease next foray, TCOTFD)."
    ]


def use_trained_poison_expert(
    session: SessionState,
    provider_id: str | None,
    *,
    target_character_id: str | None,
    item_name: str | None,
) -> list[str]:
    if not session.camped_outside:
        return ["Coat weapons with expert poison while camped outside the dungeon."]
    provider = _provider(session, provider_id)
    if provider is None or provider.current_life <= 0:
        return ["Choose a living hero trained as a poison expert."]
    if not member_has_trained_poison_expert(provider):
        return [f"{provider.name} is not trained as a poison expert (TCOTFD)."]
    if not member_has_arsenic(provider):
        return [f"{provider.name} needs arsenic (a mineral ingredient) in inventory to serve as Poison Expert (TCOTFD p.9)."]
    target = _provider(session, target_character_id)
    if target is None or target.current_life <= 0:
        return ["Choose a living hero whose weapon or arrow should be envenomed."]
    from .poison_expert import apply_trained_poison_expert_coating

    log = apply_trained_poison_expert_coating(session, provider, target, item_name=item_name)
    if log and any(token in log[0].lower() for token in ("coats", "envenoms")):
        consume_arsenic(provider)
        log.append(f"{provider.name} uses arsenic from inventory.")
    return log
