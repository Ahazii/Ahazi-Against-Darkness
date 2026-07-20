from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from ..schemas import PartyMemberState, SessionState


TEMPORARY_WEAPON_ENCHANTMENT_PREFIX = "TAG Temporary Weapon Enchantment:"
TEMPORARY_WEAPON_ENCHANTMENT_SUFFIX = " is magical, no Attack bonus"
TemporaryWeaponLossKind = Literal["stolen", "destroyed"]


@dataclass(frozen=True)
class TemporaryWeaponLossChoice:
    character_id: str
    character_name: str
    item_name: str
    loss_kind: TemporaryWeaponLossKind
    source_name: str
    key: str


def temporary_weapon_enchantment_counts(member: PartyMemberState) -> Counter[str]:
    counts: Counter[str] = Counter()
    prefix = TEMPORARY_WEAPON_ENCHANTMENT_PREFIX.casefold()
    suffix = TEMPORARY_WEAPON_ENCHANTMENT_SUFFIX.casefold()
    for status in member.statuses:
        raw = str(status).strip()
        folded = raw.casefold()
        if not folded.startswith(prefix) or not folded.endswith(suffix):
            continue
        weapon_name = raw[
            len(TEMPORARY_WEAPON_ENCHANTMENT_PREFIX) : -len(TEMPORARY_WEAPON_ENCHANTMENT_SUFFIX)
        ].strip()
        if weapon_name:
            counts[weapon_name.casefold()] += 1
    return counts


def temporarily_enchanted_inventory_indices(member: PartyMemberState) -> set[int]:
    counts = temporary_weapon_enchantment_counts(member)
    indices: set[int] = set()
    for index, item_name in enumerate(member.inventory):
        key = item_name.casefold()
        if counts[key] <= 0:
            continue
        counts[key] -= 1
        indices.add(index)
    return indices


def is_temporarily_enchanted_weapon(member: PartyMemberState, item_name: str) -> bool:
    return temporary_weapon_enchantment_counts(member)[item_name.casefold()] > 0


def remove_temporary_weapon_enchantment_marker(
    member: PartyMemberState,
    item_name: str,
) -> bool:
    expected = (
        f"{TEMPORARY_WEAPON_ENCHANTMENT_PREFIX} {item_name}"
        f"{TEMPORARY_WEAPON_ENCHANTMENT_SUFFIX}"
    ).casefold()
    removed = False
    kept: list[str] = []
    for status in member.statuses:
        if not removed and str(status).strip().casefold() == expected:
            removed = True
            continue
        kept.append(status)
    member.statuses = kept
    return removed


def temporary_weapon_loss_choice_key(
    member: PartyMemberState,
    item_name: str,
    loss_kind: TemporaryWeaponLossKind,
) -> str:
    return f"{member.character_id}|{item_name.casefold()}|{loss_kind}"


def temporary_weapon_loss_decision(
    session: SessionState,
    member: PartyMemberState,
    item_name: str,
    loss_kind: TemporaryWeaponLossKind,
) -> str | None:
    key = temporary_weapon_loss_choice_key(member, item_name, loss_kind)
    return session.temporary_weapon_loss_choices.get(key)


def pending_temporary_weapon_loss_choice(
    session: SessionState,
) -> TemporaryWeaponLossChoice | None:
    if session.mode != "combat":
        return None
    tile = next(
        (item for item in session.map_state.tiles if item.id == session.map_state.current_tile_id),
        None,
    )
    if tile is None:
        return None
    sources: list[tuple[TemporaryWeaponLossKind, str]] = []
    seen_kinds: set[str] = set()
    for enemy in tile.enemies:
        if enemy.life <= 0:
            continue
        for effect in enemy.on_hit_effects:
            effect_type = str(effect.get("type", "")).casefold()
            if effect_type == "steal_item":
                loss_kind: TemporaryWeaponLossKind = "stolen"
            elif effect_type == "destroy_metal_items":
                loss_kind = "destroyed"
            else:
                continue
            if loss_kind in seen_kinds:
                continue
            seen_kinds.add(loss_kind)
            sources.append((loss_kind, enemy.name))
    for loss_kind, source_name in sources:
        for member in session.party:
            if member.current_life <= 0:
                continue
            for index in temporarily_enchanted_inventory_indices(member):
                item_name = member.inventory[index]
                key = temporary_weapon_loss_choice_key(member, item_name, loss_kind)
                if key in session.temporary_weapon_loss_choices:
                    continue
                return TemporaryWeaponLossChoice(
                    character_id=member.character_id,
                    character_name=member.name,
                    item_name=item_name,
                    loss_kind=loss_kind,
                    source_name=source_name,
                    key=key,
                )
    return None


def resolve_temporary_weapon_loss_choice(
    session: SessionState,
    choice: str | None,
) -> list[str]:
    pending = pending_temporary_weapon_loss_choice(session)
    if pending is None:
        return ["No Temporary Weapon Enchantment loss choice is pending."]
    if choice not in {"keep", "allow"}:
        return ["Choose whether to keep the temporarily enchanted weapon or allow the loss."]
    session.temporary_weapon_loss_choices[pending.key] = choice
    if choice == "keep":
        return [
            f"{pending.character_name} keeps the temporarily enchanted {pending.item_name}; "
            f"{pending.source_name} may not take or destroy it (TAG p.65, Temporary Weapon Enchantment)."
        ]
    loss_verb = "steal" if pending.loss_kind == "stolen" else "destroy"
    return [
        f"{pending.character_name} allows {pending.source_name} to {loss_verb} "
        f"the temporarily enchanted {pending.item_name} if its effect reaches that weapon "
        "(TAG p.65, Temporary Weapon Enchantment)."
    ]
