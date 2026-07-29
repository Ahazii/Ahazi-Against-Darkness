from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Literal

from ..schemas import Character, EnemyState, PartyMemberState, SessionState


TEMPORARY_WEAPON_ENCHANTMENT_PREFIX = "TAG Temporary Weapon Enchantment:"
TEMPORARY_WEAPON_ENCHANTMENT_SUFFIX = " is magical, no Attack bonus"
TEMPORARY_WEAPON_ENCHANTMENT_DURATION_DAYS = 7
TemporaryWeaponLossKind = Literal["stolen", "destroyed"]
_TIMED_MARKER_PATTERN = re.compile(
    rf"^{re.escape(TEMPORARY_WEAPON_ENCHANTMENT_PREFIX)}\s*"
    rf"(?P<weapon>.+?){re.escape(TEMPORARY_WEAPON_ENCHANTMENT_SUFFIX)}"
    r"(?:;\s*cast day\s+(?P<cast_day>\d+);\s*expires day\s+(?P<expires_day>\d+))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TemporaryWeaponLossChoice:
    character_id: str
    character_name: str
    item_name: str
    loss_kind: TemporaryWeaponLossKind
    source_name: str
    key: str


@dataclass(frozen=True)
class TemporaryWeaponEnchantment:
    item_name: str
    cast_day: int | None
    expires_day: int | None


def temporary_weapon_enchantment_marker(item_name: str, *, cast_day: int) -> str:
    expires_day = cast_day + TEMPORARY_WEAPON_ENCHANTMENT_DURATION_DAYS
    return (
        f"{TEMPORARY_WEAPON_ENCHANTMENT_PREFIX} {item_name}"
        f"{TEMPORARY_WEAPON_ENCHANTMENT_SUFFIX}; "
        f"cast day {cast_day}; expires day {expires_day}"
    )


def parse_temporary_weapon_enchantment(status: str) -> TemporaryWeaponEnchantment | None:
    match = _TIMED_MARKER_PATTERN.fullmatch(str(status).strip())
    if match is None:
        return None
    cast_day = match.group("cast_day")
    expires_day = match.group("expires_day")
    return TemporaryWeaponEnchantment(
        item_name=match.group("weapon").strip(),
        cast_day=int(cast_day) if cast_day is not None else None,
        expires_day=int(expires_day) if expires_day is not None else None,
    )


def temporary_weapon_enchantment_counts(member: PartyMemberState) -> Counter[str]:
    counts: Counter[str] = Counter()
    for status in member.statuses:
        enchantment = parse_temporary_weapon_enchantment(status)
        if enchantment is None:
            continue
        counts[enchantment.item_name.casefold()] += 1
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
    removed = False
    kept: list[str] = []
    for status in member.statuses:
        enchantment = parse_temporary_weapon_enchantment(status)
        if (
            not removed
            and enchantment is not None
            and enchantment.item_name.casefold() == item_name.casefold()
        ):
            removed = True
            continue
        kept.append(status)
    member.statuses = kept
    return removed


def replace_temporary_weapon_enchantment(
    member: Character | PartyMemberState,
    item_name: str,
    *,
    cast_day: int,
) -> None:
    while remove_temporary_weapon_enchantment_marker(member, item_name):
        pass
    member.statuses.append(temporary_weapon_enchantment_marker(item_name, cast_day=cast_day))


def advance_temporary_weapon_enchantments(
    member: Character | PartyMemberState,
    *,
    previous_day: int,
    current_day: int,
) -> list[str]:
    updated: list[str] = []
    expired: list[str] = []
    for status in member.statuses:
        enchantment = parse_temporary_weapon_enchantment(status)
        if enchantment is None:
            updated.append(status)
            continue
        cast_day = enchantment.cast_day
        expires_day = enchantment.expires_day
        if cast_day is None or expires_day is None:
            cast_day = previous_day
            expires_day = previous_day + TEMPORARY_WEAPON_ENCHANTMENT_DURATION_DAYS
        if current_day >= expires_day:
            expired.append(enchantment.item_name)
            continue
        updated.append(
            temporary_weapon_enchantment_marker(
                enchantment.item_name,
                cast_day=cast_day,
            )
        )
    member.statuses = updated
    return [
        f"{member.name}'s Temporary Weapon Enchantment on {item_name} expires after one week "
        f"(campaign day {current_day}; TAG p.65)."
        for item_name in expired
    ]


def _qualifying_magic_only_foe(enemy: EnemyState) -> bool:
    allowed = {
        tag.casefold().removeprefix("weapon_allow:")
        for tag in enemy.tags
        if tag.casefold().startswith("weapon_allow:")
    }
    return allowed == {"magic_weapons"}


def note_temporary_weapon_qualifying_use(
    session: SessionState,
    member: PartyMemberState,
    item_name: str,
    enemy: EnemyState,
) -> bool:
    if (
        not is_temporarily_enchanted_weapon(member, item_name)
        or not _qualifying_magic_only_foe(enemy)
    ):
        return False
    key = f"{member.character_id}|{item_name.casefold()}"
    session.temporary_weapon_enchantment_qualifying_uses[key] = item_name
    return True


def expire_qualifying_temporary_weapon_enchantments(session: SessionState) -> list[str]:
    log: list[str] = []
    for key, item_name in dict(session.temporary_weapon_enchantment_qualifying_uses).items():
        character_id = key.split("|", 1)[0]
        member = next(
            (item for item in session.party if item.character_id == character_id),
            None,
        )
        if member is None or not remove_temporary_weapon_enchantment_marker(member, item_name):
            continue
        log.append(
            f"{member.name}'s Temporary Weapon Enchantment on {item_name} expires at encounter end "
            "after use against a foe hit only by magic weapons (TAG p.65)."
        )
    session.temporary_weapon_enchantment_qualifying_uses = {}
    return log


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
