from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..schemas import EnemyState, PartyMemberState

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
    light = "light weapon" in lower or "dagger" in lower or "scimitar" in lower
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


def inventory_weapons(member: PartyMemberState) -> list[WeaponProfile]:
    weapons: list[WeaponProfile] = []
    for item in member.inventory:
        profile = _parse_weapon_item(item)
        if profile is not None:
            weapons.append(profile)
    return weapons


def select_missile_weapon(member: PartyMemberState) -> WeaponProfile | None:
    missiles = [weapon for weapon in inventory_weapons(member) if weapon.kind == "missile"]
    if not missiles:
        return None
    return missiles[0]


def select_melee_weapon(member: PartyMemberState, enemy: EnemyState | None = None) -> WeaponProfile | None:
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
