from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..schemas import Character, EnemyState, PartyMemberState
from .magic_weapons import can_member_wield_weapon, magic_weapon_attack_bonus

WeaponKind = Literal["missile", "melee"]


@dataclass(frozen=True)
class WeaponProfile:
    item: str
    kind: WeaponKind
    two_handed: bool = False
    light: bool = False
    crushing: bool = False
    slashing: bool = False


def _parse_weapon_item(item: str) -> WeaponProfile | None:
    lower = item.lower()
    if "blade poison" in lower:
        return None
    if any(skip in lower for skip in ("armor", "shield", "bandage", "rope", "lockpick", "holy", "spellbook", "ink", "ration", "potion", "lantern", "symbol", "crystal", "charm")):
        if "hand weapon" not in lower and "heavy weapon" not in lower and "light weapon" not in lower:
            return None

    if "bow" in lower or "crossbow" in lower:
        return WeaponProfile(item=item, kind="missile", two_handed=True)
    if "sling" in lower:
        return WeaponProfile(item=item, kind="missile", light=True)

    two_handed = "heavy weapon" in lower or "two-handed" in lower or "two handed" in lower
    light = any(token in lower for token in ("light hand weapon", "light weapon", "dagger", "scimitar"))
    crushing = any(word in lower for word in ("mace", "hammer", "club", "flail", "staff"))
    slashing = any(word in lower for word in ("sword", "axe", "scimitar", "dagger", "blade", "spear", "whip"))
    if "hand weapon" in lower or "heavy weapon" in lower or "light weapon" in lower:
        slashing = True
    if not any((two_handed, light, crushing, slashing)) and "weapon" not in lower:
        if lower in {"staff", "mace", "axe", "sword", "spear", "hammer", "club", "dagger", "scimitar", "whip", "flail"}:
            slashing = lower in {"axe", "sword", "spear", "dagger", "scimitar", "whip"}
            crushing = lower in {"staff", "mace", "hammer", "club", "flail"}
            two_handed = lower in {"axe", "spear", "hammer", "staff"}
            light = lower == "dagger"
        else:
            return None

    return WeaponProfile(
        item=item,
        kind="melee",
        two_handed=two_handed,
        light=light,
        crushing=crushing,
        slashing=slashing or not crushing,
    )


def weapon_item_slots(item: str) -> int:
    profile = _parse_weapon_item(item)
    if profile is None:
        return 0
    return 2 if profile.two_handed else 1


def infer_default_weapons(inventory: list[str]) -> tuple[str | None, str | None]:
    default_melee: str | None = None
    default_missile: str | None = None
    for item in inventory:
        profile = _parse_weapon_item(item)
        if profile is None:
            continue
        if profile.kind == "missile" and default_missile is None:
            default_missile = item
        elif profile.kind == "melee" and default_melee is None:
            default_melee = item
    return default_melee, default_missile


def infer_secondary_melee_default(
    inventory: list[str],
    *,
    class_id: str,
    primary: str | None,
) -> str | None:
    class_key = class_id.lower()
    if class_key not in {"ranger", "light_gladiator", "swashbuckler"}:
        return None
    primary_profile = _parse_weapon_item(primary) if primary else None
    candidates: list[str] = []
    for item in inventory:
        if item == primary:
            continue
        profile = _parse_weapon_item(item)
        if profile is None or profile.kind != "melee":
            continue
        if class_key == "light_gladiator" and not profile.light:
            continue
        if class_key == "swashbuckler":
            if not profile.light:
                continue
            if primary_profile and not _swashbuckler_pair_valid(primary_profile, profile):
                continue
        if class_key == "ranger" and primary_profile and not _ranger_weapons_compatible(primary_profile, profile):
            continue
        candidates.append(item)
    return candidates[0] if candidates else None


def prune_weapon_defaults(member: PartyMemberState | Character) -> None:
    if member.default_melee_weapon and member.default_melee_weapon not in member.inventory:
        member.default_melee_weapon = None
    if member.default_melee_weapon_secondary and member.default_melee_weapon_secondary not in member.inventory:
        member.default_melee_weapon_secondary = None
    if member.default_missile_weapon and member.default_missile_weapon not in member.inventory:
        member.default_missile_weapon = None
    inferred_melee, inferred_missile = infer_default_weapons(member.inventory)
    if member.default_melee_weapon is None:
        member.default_melee_weapon = inferred_melee
    if member.default_missile_weapon is None:
        member.default_missile_weapon = inferred_missile
    if member.default_melee_weapon_secondary is None:
        member.default_melee_weapon_secondary = infer_secondary_melee_default(
            member.inventory,
            class_id=member.class_id,
            primary=member.default_melee_weapon,
        )


def set_weapon_default(
    holder: PartyMemberState | Character,
    *,
    item_name: str,
    weapon_kind: WeaponKind,
    melee_slot: Literal["primary", "secondary"] = "primary",
) -> tuple[bool, str]:
    if item_name not in holder.inventory:
        return False, f"{holder.name} does not carry {item_name}."
    profile = _parse_weapon_item(item_name)
    if profile is None or profile.kind != weapon_kind:
        return False, f"{item_name} is not a valid {weapon_kind} weapon for {holder.name}."
    if isinstance(holder, PartyMemberState):
        allowed, message = can_member_wield_weapon(holder, item_name)
        if not allowed:
            return False, message
    if weapon_kind == "melee":
        if melee_slot == "secondary":
            holder.default_melee_weapon_secondary = item_name
        else:
            holder.default_melee_weapon = item_name
    else:
        holder.default_missile_weapon = item_name
    slot_label = "secondary melee" if melee_slot == "secondary" else weapon_kind
    return True, f"{holder.name} sets default {slot_label} weapon to {item_name}."


def inventory_weapons(member: PartyMemberState) -> list[WeaponProfile]:
    weapons: list[WeaponProfile] = []
    for item in member.inventory:
        profile = _parse_weapon_item(item)
        if profile is None:
            continue
        allowed, _ = can_member_wield_weapon(member, item)
        if allowed:
            weapons.append(profile)
    return weapons


def _profile_from_inventory(
    member: PartyMemberState,
    item_name: str | None,
    *,
    kind: WeaponKind,
) -> WeaponProfile | None:
    if not item_name or item_name not in member.inventory:
        return None
    profile = _parse_weapon_item(item_name)
    if profile is None or profile.kind != kind:
        return None
    return profile


def select_missile_weapon(member: PartyMemberState) -> WeaponProfile | None:
    chosen = _profile_from_inventory(member, member.default_missile_weapon, kind="missile")
    if chosen is not None:
        return chosen
    missiles = [weapon for weapon in inventory_weapons(member) if weapon.kind == "missile"]
    if not missiles:
        return None
    return missiles[0]


def select_melee_weapon(
    member: PartyMemberState,
    enemy: EnemyState | None = None,
    *,
    wielded: str | None = None,
    force_unarmed: bool = False,
) -> WeaponProfile | None:
    if force_unarmed:
        return None
    chosen = _profile_from_inventory(member, wielded, kind="melee")
    if chosen is not None:
        return chosen
    chosen = _profile_from_inventory(member, member.default_melee_weapon, kind="melee")
    if chosen is not None:
        return chosen
    melee = [weapon for weapon in inventory_weapons(member) if weapon.kind == "melee"]
    if not melee:
        return None
    return max(melee, key=lambda weapon: weapon_attack_modifier(weapon, enemy))


def weapon_attack_modifier(weapon: WeaponProfile | None, enemy: EnemyState | None = None) -> int:
    if weapon is None:
        return -2
    modifier = 0
    if weapon.kind == "melee" and weapon.two_handed:
        modifier += 1
    if weapon.light:
        modifier -= 1
    if weapon.crushing and enemy is not None and _is_skeleton(enemy):
        modifier += 1
    modifier += magic_weapon_attack_bonus(weapon.item)
    return modifier


def weapon_label(weapon: WeaponProfile | None) -> str:
    if weapon is None:
        return "unarmed"
    return weapon.item


def can_fire_missile(
    member: PartyMemberState,
    *,
    tile_type: str,
    encounter_round: int,
    missile_used: set[str],
) -> bool:
    if select_missile_weapon(member) is None:
        return False
    if tile_type == "corridor":
        return member.marching_order in {3, 4}
    if encounter_round != 0:
        return False
    return member.character_id not in missile_used


def _is_skeleton(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "skeleton" in tags or "undead" in tags or "skeleton" in name


def weapon_style_category(profile: WeaponProfile) -> str:
    if profile.kind != "melee":
        return ""
    if profile.two_handed:
        return "two_handed"
    if profile.light:
        return "light_slashing" if profile.slashing else "light_blunt"
    if profile.crushing:
        return "hand_blunt"
    return "hand_slashing"


def _ranger_weapons_compatible(first: WeaponProfile, second: WeaponProfile) -> bool:
    left = weapon_style_category(first)
    right = weapon_style_category(second)
    if left == right and left in {"hand_slashing", "hand_blunt"}:
        return True
    return {left, right} == {"hand_slashing", "light_slashing"}


def _swashbuckler_pair_valid(main: WeaponProfile, off: WeaponProfile) -> bool:
    return not main.light and not main.two_handed and off.light


def ranger_dual_wield_pair(member: PartyMemberState) -> tuple[str, str] | None:
    primary = member.default_melee_weapon
    secondary = member.default_melee_weapon_secondary
    if primary and secondary:
        first = _profile_from_inventory(member, primary, kind="melee")
        second = _profile_from_inventory(member, secondary, kind="melee")
        if first and second and _ranger_weapons_compatible(first, second):
            return primary, secondary
    melee = [weapon for weapon in inventory_weapons(member) if weapon.kind == "melee" and not weapon.two_handed]
    if len(melee) < 2:
        return None
    preferred = member.default_melee_weapon
    ordered = sorted(
        melee,
        key=lambda weapon: (weapon.item != preferred, weapon.item),
    )
    for index, first in enumerate(ordered):
        for second in ordered[index + 1 :]:
            if _ranger_weapons_compatible(first, second):
                return first.item, second.item
    return None


def light_gladiator_dual_pair(member: PartyMemberState) -> tuple[str, str] | None:
    primary = member.default_melee_weapon
    secondary = member.default_melee_weapon_secondary
    if primary and secondary:
        first = _profile_from_inventory(member, primary, kind="melee")
        second = _profile_from_inventory(member, secondary, kind="melee")
        if first and second and first.light and second.light:
            return primary, secondary
    lights = [weapon for weapon in inventory_weapons(member) if weapon.kind == "melee" and weapon.light]
    if len(lights) < 2:
        return None
    preferred = member.default_melee_weapon
    ordered = sorted(lights, key=lambda weapon: (weapon.item != preferred, weapon.item))
    return ordered[0].item, ordered[1].item


def swashbuckler_dual_pair(member: PartyMemberState) -> tuple[str, str] | None:
    primary = member.default_melee_weapon
    secondary = member.default_melee_weapon_secondary
    if primary and secondary:
        first = _profile_from_inventory(member, primary, kind="melee")
        second = _profile_from_inventory(member, secondary, kind="melee")
        if first and second and _swashbuckler_pair_valid(first, second):
            return primary, secondary
    melee = [weapon for weapon in inventory_weapons(member) if weapon.kind == "melee"]
    hands = [weapon for weapon in melee if not weapon.light and not weapon.two_handed]
    lights = [weapon for weapon in melee if weapon.light]
    if not hands or not lights:
        return None
    preferred = member.default_melee_weapon
    main = sorted(hands, key=lambda weapon: (weapon.item != preferred, weapon.item))[0]
    off = sorted(lights, key=lambda weapon: (weapon.item == preferred, weapon.item))[0]
    return main.item, off.item


def ranger_outdoor_bow(member: PartyMemberState) -> WeaponProfile | None:
    weapon = select_missile_weapon(member)
    if weapon is None:
        return None
    if "bow" not in weapon.item.lower():
        return None
    return weapon
