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
    two_slot: bool = False
    light: bool = False
    crushing: bool = False
    slashing: bool = False


def weapon_profile(item: str) -> WeaponProfile | None:
    return _parse_weapon_item(item)


def _parse_weapon_item(item: str) -> WeaponProfile | None:
    lower = item.lower()
    if "blade poison" in lower:
        return None
    if any(skip in lower for skip in ("armor", "shield", "bandage", "rope", "lockpick", "holy", "spellbook", "ink", "ration", "potion", "lantern", "symbol", "crystal", "charm")):
        if "hand weapon" not in lower and "heavy weapon" not in lower and "light weapon" not in lower:
            return None

    if "crossbow" in lower:
        return WeaponProfile(item=item, kind="missile", two_slot=True, slashing=True)
    if "bow" in lower:
        return WeaponProfile(item=item, kind="missile", two_slot=True, slashing=True)
    if "handgun" in lower or "black powder rifle" in lower:
        return WeaponProfile(item=item, kind="missile", two_handed=True, two_slot=True)
    if "sling" in lower:
        return WeaponProfile(item=item, kind="missile", light=True, crushing=True)
    if "throwing star" in lower or "shuriken" in lower:
        return WeaponProfile(item=item, kind="missile", light=True, slashing=True)
    if is_ten_foot_pole_item(lower):
        return WeaponProfile(item=item, kind="melee", two_handed=True, two_slot=True, crushing=True)
    if "crowbar" in lower:
        return WeaponProfile(item=item, kind="melee", crushing=True)
    if "wooden stake" in lower or lower == "stake":
        return WeaponProfile(item=item, kind="melee", light=True, slashing=True)
    if "magic shovel" in lower:
        return WeaponProfile(item=item, kind="melee", light=True, crushing=True)

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


def is_ten_foot_pole_item(lower: str) -> bool:
    return "10' pole" in lower or "ten foot pole" in lower or "10 foot pole" in lower


def weapon_item_slots(item: str) -> int:
    profile = _parse_weapon_item(item)
    if profile is None:
        return 0
    if profile.two_slot or profile.two_handed:
        return 2
    return 1


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
    from .firearm import can_member_use_firearm, is_firearm_item

    def allowed(profile: WeaponProfile) -> bool:
        if is_firearm_item(profile.item):
            return can_member_use_firearm(member)
        return True

    chosen = _profile_from_inventory(member, member.default_missile_weapon, kind="missile")
    if chosen is not None and allowed(chosen):
        return chosen
    missiles = [weapon for weapon in inventory_weapons(member) if weapon.kind == "missile" and allowed(weapon)]
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


def weapon_attack_modifier(
    weapon: WeaponProfile | None,
    enemy: EnemyState | None = None,
    *,
    member: PartyMemberState | None = None,
) -> int:
    if weapon is None:
        return -2
    modifier = 0
    lower = weapon.item.lower()
    if weapon.kind == "melee" and weapon.two_handed:
        modifier += 1
    if "crossbow" in lower:
        modifier += 1
    if weapon.light:
        modifier -= 1
    if weapon.crushing and enemy is not None and _is_skeleton(enemy):
        modifier += 1
    modifier += magic_weapon_attack_bonus(weapon.item)
    if member is not None and "bow" in lower and "crossbow" not in lower:
        if any("arrow" in item.lower() for item in member.inventory):
            modifier += 1
    if member is not None and enemy is not None:
        from .equipment_effects import silver_gild_attack_bonus
        from .firearm import firearm_attack_bonus, is_firearm_item

        modifier += silver_gild_attack_bonus(member, enemy, weapon_item=weapon.item)
        if is_firearm_item(weapon.item):
            modifier += firearm_attack_bonus(weapon.item)
    return modifier


def weapon_label(weapon: WeaponProfile | None) -> str:
    if weapon is None:
        return "unarmed"
    return weapon.item


def _item_lower(name: str | None) -> str:
    return (name or "").strip().lower()


def mushroom_monk_full_attack_item(name: str | None) -> bool:
    lower = _item_lower(name)
    if not lower:
        return True
    if any(token in lower for token in ("nunchaku", "throwing star", "shuriken", "sai")):
        return True
    if lower == "bo" or lower.startswith("bo ") or " bo" in lower:
        return True
    return False


def mushroom_monk_flurry_item(name: str | None) -> bool:
    lower = _item_lower(name)
    if not lower:
        return True
    if "nunchaku" in lower:
        return True
    if "throwing star" in lower or "shuriken" in lower:
        return True
    return False


def mushroom_monk_flurry_eligible(
    member: PartyMemberState,
    *,
    wielded: str | None = None,
    force_unarmed: bool = False,
) -> bool:
    if member.class_id.lower() != "mushroom_monk":
        return False
    if force_unarmed:
        return True
    chosen = wielded or member.default_melee_weapon
    if not chosen:
        return True
    profile = _profile_from_inventory(member, chosen, kind="melee")
    item_name = profile.item if profile else chosen
    return mushroom_monk_flurry_item(item_name)


def mushroom_monk_unarmed_penalty(member: PartyMemberState) -> int:
    if member.class_id.lower() != "mushroom_monk":
        return -2
    return 0 if member.level >= 5 else -1


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
    lower = weapon.item.lower()
    if "bow" not in lower or "crossbow" in lower:
        return None
    return weapon


def ranger_outdoor_sling(member: PartyMemberState) -> WeaponProfile | None:
    weapon = select_missile_weapon(member)
    if weapon is None or "sling" not in weapon.item.lower():
        return None
    return weapon


def crossbow_needs_reload(session, member: PartyMemberState) -> bool:
    return member.character_id in getattr(session, "crossbow_needs_reload", [])


def mark_crossbow_needs_reload(session, member: PartyMemberState) -> None:
    ids = list(getattr(session, "crossbow_needs_reload", []))
    if member.character_id not in ids:
        ids.append(member.character_id)
    session.crossbow_needs_reload = ids


def clear_crossbow_reload(session, member: PartyMemberState) -> None:
    ids = [cid for cid in getattr(session, "crossbow_needs_reload", []) if cid != member.character_id]
    session.crossbow_needs_reload = ids
