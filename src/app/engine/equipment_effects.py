from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState, SessionState

AMULET_LUCK_STATUS = "Amulet luck available"
TALISMAN_SAVE_STATUS = "Talisman +1 save available"
TALISMAN_ARMED_STATUS = "Talisman +1 save armed"
PREP_HOLY_WATER_PURCHASED = "Prep: holy water purchased"


def is_ten_foot_pole(item: str) -> bool:
    lower = item.lower()
    return "10' pole" in lower or "ten foot pole" in lower or "10 foot pole" in lower


def has_ten_foot_pole_in_inventories(inventories: list[list[str]]) -> bool:
    return any(is_ten_foot_pole(item) for inventory in inventories for item in inventory)


def pole_carrier(party: list[PartyMemberState]) -> PartyMemberState | None:
    for member in party:
        if any(is_ten_foot_pole(item) for item in member.inventory):
            return member
    return None


def enforce_single_pole_carrier(party: list[PartyMemberState], *, session: SessionState | None = None) -> list[str]:
    """Only one PC may carry a 10' pole; strip extras from non-carriers."""
    carrier = pole_carrier(party)
    if carrier is None:
        if session is not None:
            session.pole_carrier_id = None
        return []
    if session is not None:
        session.pole_carrier_id = carrier.character_id
    log: list[str] = []
    for member in party:
        if member.character_id == carrier.character_id:
            continue
        removed = [item for item in member.inventory if is_ten_foot_pole(item)]
        for item in removed:
            member.inventory.remove(item)
            log.append(f"{item} cannot be carried while {carrier.name} holds the party's pole.")
    return log


SCROLL_TUBE_PROTECTED_SCROLLS = 3


def member_has_scroll_tube(member: PartyMemberState) -> bool:
    return any("scroll tube" in item.lower() for item in member.inventory)


def is_scroll_item(item: str) -> bool:
    lower = item.strip().lower()
    if "scroll tube" in lower:
        return False
    return lower.startswith("scroll") or "prism of" in lower or "bark of" in lower


def scroll_protected_by_tube(member: PartyMemberState, item: str) -> bool:
    if not member_has_scroll_tube(member) or not is_scroll_item(item):
        return False
    protected = 0
    for inventory_item in member.inventory:
        if is_scroll_item(inventory_item):
            if inventory_item == item:
                return protected < SCROLL_TUBE_PROTECTED_SCROLLS
            protected += 1
    return False


def is_fools_gold(item: str) -> bool:
    lower = item.lower()
    return "fool" in lower and "gold" in lower


def party_has_fools_gold(party: list[PartyMemberState]) -> bool:
    return any(is_fools_gold(item) for member in party for item in member.inventory)


def consume_fools_gold(party: list[PartyMemberState]) -> tuple[bool, str]:
    for member in party:
        for index, item in enumerate(member.inventory):
            if is_fools_gold(item):
                member.inventory.pop(index)
                return True, f"{member.name} uses Fools' Gold to satisfy the bribe."
    return False, "No Fools' Gold is available."


def member_has_silvered_weapons(member: PartyMemberState) -> bool:
    if any("silvered weapons" in status.lower() for status in member.statuses):
        return True
    from .weapon_finishes import is_weapon_item_silvered

    return any(is_weapon_item_silvered(item) for item in member.inventory)


def member_has_gilded_weapons(member: PartyMemberState) -> bool:
    if any("gilded weapons" in status.lower() for status in member.statuses):
        return True
    from .weapon_finishes import is_weapon_item_gilded

    return any(is_weapon_item_gilded(item) for item in member.inventory)


def is_werecreature(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "were" in tags or "lycanthrope" in tags or "werewolf" in name or "were-" in name


def is_elemental(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "elemental" in tags or "elemental" in name


def is_demon(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "demon" in tags or "demon" in name


def is_golem(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "golem" in tags or "golem" in name


def is_vampire(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "vampire" in tags or "vampire" in name


def silver_gild_attack_bonus(
    member: PartyMemberState | None,
    enemy: EnemyState | None,
    *,
    weapon_item: str | None = None,
) -> int:
    if member is None or enemy is None:
        return 0
    from .weapon_finishes import member_wields_gilded_weapon, member_wields_silvered_weapon

    bonus = 0
    if member_wields_silvered_weapon(member, weapon_item) and is_werecreature(enemy):
        bonus += 1
    if member_wields_gilded_weapon(member, weapon_item) and is_elemental(enemy):
        bonus += 2
    return bonus


def silver_gild_attack_notes(
    member: PartyMemberState | None,
    enemy: EnemyState | None,
    *,
    weapon_item: str | None = None,
) -> str:
    if member is None or enemy is None:
        return ""
    from .weapon_finishes import member_wields_gilded_weapon, member_wields_silvered_weapon

    notes: list[str] = []
    if member_wields_silvered_weapon(member, weapon_item) and is_werecreature(enemy):
        notes.append("silvered weapon +1 vs lycanthrope")
    if member_wields_gilded_weapon(member, weapon_item) and is_elemental(enemy):
        notes.append("gilded weapon +2 vs elemental")
    if not notes:
        return ""
    return "; ".join(notes)


def has_good_lockpicks(member: PartyMemberState) -> bool:
    return any("good lockpicks" in item.lower() for item in member.inventory)


def has_crowbar(member: PartyMemberState) -> bool:
    return any("crowbar" in item.lower() for item in member.inventory)


def has_wooden_stake(member: PartyMemberState) -> bool:
    return any("wooden stake" in item.lower() or item.lower() == "stake" for item in member.inventory)


def armor_stealth_penalty(member: PartyMemberState) -> int:
    inventory = " ".join(item.lower() for item in member.inventory)
    penalty = 0
    if "shield" in inventory:
        penalty += 1
    if "heavy armor" in inventory:
        penalty += 1
    return penalty


def armor_swim_climb_penalty(member: PartyMemberState) -> int:
    inventory = " ".join(item.lower() for item in member.inventory)
    return 2 if "heavy armor" in inventory else 0


def talisman_save_bonus(member: PartyMemberState) -> int:
    if any(status == TALISMAN_ARMED_STATUS for status in member.statuses):
        return 1
    return 0


def arm_talisman_save(member: PartyMemberState) -> tuple[bool, str]:
    if not any(status == TALISMAN_SAVE_STATUS for status in member.statuses):
        return False, f"{member.name} has no talisman available."
    if any(status == TALISMAN_ARMED_STATUS for status in member.statuses):
        return False, f"{member.name} already armed a talisman for the next save."
    member.statuses.append(TALISMAN_ARMED_STATUS)
    return True, f"{member.name} arms the talisman (+1 on the next save roll, then it is consumed)."


def consume_armed_talisman(member: PartyMemberState) -> tuple[int, list[str]]:
    if TALISMAN_ARMED_STATUS not in member.statuses:
        return 0, []
    member.statuses = [
        status
        for status in member.statuses
        if status not in {TALISMAN_SAVE_STATUS, TALISMAN_ARMED_STATUS}
    ]
    for index, item in enumerate(member.inventory):
        if "talisman" in item.lower():
            member.inventory.pop(index)
            break
    return 1, [f"{member.name}'s talisman grants +1 on this save and is consumed."]


def apply_service_purchase_statuses(character, shop_key: str) -> None:
    if shop_key == "amulet":
        if not any("amulet luck" in status.lower() for status in character.statuses):
            character.statuses.append(AMULET_LUCK_STATUS)
    if shop_key == "talisman":
        if not any("talisman +1 save" in status.lower() for status in character.statuses):
            character.statuses.append(TALISMAN_SAVE_STATUS)


def food_ration_cap_exceeded(inventory: list[str], add: int = 0) -> bool:
    current = sum(1 for item in inventory if "food ration" in item.lower())
    return current + add > 10


def flammable_oil_cap_exceeded(inventory: list[str], add: int = 0) -> bool:
    current = sum(
        1
        for item in inventory
        if any(token in item.lower() for token in ("flammable oil", "lantern oil", "flask of oil"))
    )
    return current + add > 1


def enemy_is_flammable(enemy: EnemyState) -> bool:
    return "flammable" in {tag.lower() for tag in enemy.tags}


def mark_enemy_flammable(enemy: EnemyState) -> None:
    tags = {tag.lower() for tag in enemy.tags}
    if "flammable" not in tags:
        enemy.tags.append("flammable")


def fire_damage_bonus_vs_flammable(enemy: EnemyState, *, damage_kind: str) -> int:
    if damage_kind == "fire" and enemy_is_flammable(enemy):
        return 2
    return 0


def finalize_talisman_after_save(member: PartyMemberState) -> list[str]:
    if TALISMAN_ARMED_STATUS not in member.statuses:
        return []
    _, logs = consume_armed_talisman(member)
    return logs


def trap_swim_climb_flags(trap_key: str, label: str) -> tuple[bool, bool]:
    text = f"{trap_key} {label}".lower()
    swim = any(token in text for token in ("water", "swim", "drown", "flood", "pool"))
    climb = any(token in text for token in ("climb", "pit", "fall", "slide", "boulder", "log", "stalactite"))
    return swim, climb
