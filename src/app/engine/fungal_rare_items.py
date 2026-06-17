from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState, SessionState
from .combat import apply_enemy_damage
from .consumables import is_undead_or_demon
from .dice import roll_d3, roll_d6, roll_formula
from .hunger import feed_member_hunger
from .subdual import reduce_foe_level

RED_DEATH_DAMAGE_ITEM = "Red Death (1 damage)"
RED_DEATH_LEVEL_ITEM = "Red Death (-1 Level)"
XICTHUL_CAP_ITEM = "Xicthul's Cap"
WHITE_ANGEL_MUSHROOM_ITEM = "White Angel Mushroom"
WHITE_ANGEL_SPENT_ITEM = "White Angel Mushroom (10gp resale)"


def is_red_death_item(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return lower.startswith("red death")


def is_xicthul_cap(item_name: str) -> bool:
    return "xicthul" in item_name.strip().lower()


def is_white_angel_mushroom(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return lower.startswith("white angel mushroom") and "resale" not in lower


def red_death_mode(item_name: str) -> str:
    lower = item_name.strip().lower()
    if "level" in lower:
        return "level_drop"
    return "damage"


def roll_white_angel_mushrooms() -> tuple[list[str], list[str]]:
    count = roll_formula("d6")
    items = [WHITE_ANGEL_MUSHROOM_ITEM] * count
    return items, [f"Mushroom Gatherer's Basket: d6 = {count} white angel mushroom(s)."]


def resolve_red_death_treasure(pick: str, log: list[str]) -> tuple[str, int, list[str], list[str]]:
    if pick == "red_death_level":
        log.append("Red Death will reduce a living foe's Level by 1 when thrown.")
        return f"Found {RED_DEATH_LEVEL_ITEM}.", 0, [RED_DEATH_LEVEL_ITEM], log
    log.append("Red Death will inflict 1 automatic damage on a living foe when thrown.")
    return f"Found {RED_DEATH_DAMAGE_ITEM}.", 0, [RED_DEATH_DAMAGE_ITEM], log


def fungal_throwable_kind(item_name: str) -> str | None:
    if is_red_death_item(item_name):
        return "red_death"
    if is_xicthul_cap(item_name):
        return "xicthul"
    return None


def is_unliving_foe(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    if tags.intersection({"undead", "unliving", "spirit", "artificial", "construct"}):
        return True
    return any(token in name for token in ("skeleton", "zombie", "wight", "wraith", "ghost", "golem"))


def throw_red_death(
    thrower: PartyMemberState,
    target: EnemyState,
    item_name: str,
    *,
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    log = [f"{thrower.name} throws {item_name} at {target.name}."]
    if is_unliving_foe(target):
        log.append("Red Death has no effect on unliving foes.")
        return log, False
    mode = red_death_mode(item_name)
    if mode == "level_drop":
        if reduce_foe_level(target, 1):
            log.append(f"{target.name}'s Level drops to L{target.level}.")
        else:
            log.append(f"{target.name} is already at minimum Level.")
        return log, True
    apply_enemy_damage(target, 1, damage_kind="normal")
    log.append(f"{target.name} takes 1 automatic damage from Red Death.")
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    return log, True


def throw_xicthuls_cap(
    thrower: PartyMemberState,
    target: EnemyState,
    *,
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    damage_roll = roll_d3()
    if show_rolls:
        log = [
            f"{thrower.name} throws Xicthul's Cap at {target.name}: d3 chaos damage = {damage_roll}.",
        ]
    else:
        log = [f"{thrower.name} throws Xicthul's Cap at {target.name}."]
    thrower.current_life = max(0, thrower.current_life - 1)
    log.append(f"The chaotic blast costs {thrower.name} 1 Life ({thrower.current_life}/{thrower.max_life}).")
    apply_enemy_damage(target, damage_roll, damage_kind="normal")
    log.append(f"{target.name} takes {damage_roll} damage from Xicthul's Cap.")
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    return log, True


def eat_white_angel_mushroom(
    eater: PartyMemberState,
    *,
    session: SessionState | None = None,
) -> tuple[list[str], bool]:
    if eater.class_id.lower() == "mushroom_monk":
        return [f"{eater.name} cannot use rare mushrooms."], False
    if eater.current_life <= 0:
        return [f"{eater.name} is not living and cannot eat mushrooms."], False
    log = [f"{eater.name} eats a White Angel Mushroom (counts as 1 Food ration)."]
    if session is not None:
        feed_member_hunger(session, eater)
    healed = min(2, eater.max_life - eater.current_life)
    if healed <= 0:
        log.append(f"{eater.name} is already at full Life.")
        return log, True
    eater.current_life += healed
    log.append(f"{eater.name} heals {healed} Life ({eater.current_life}/{eater.max_life}).")
    return log, True


def expire_white_angel_mushrooms(party: list[PartyMemberState]) -> list[str]:
    logs: list[str] = []
    for member in party:
        updated: list[str] = []
        converted = 0
        for item in member.inventory:
            if is_white_angel_mushroom(item):
                updated.append(WHITE_ANGEL_SPENT_ITEM)
                converted += 1
            else:
                updated.append(item)
        if converted:
            member.inventory = updated
            logs.append(
                f"{member.name}'s {converted} white angel mushroom(s) lose their healing power "
                f"(sell for 10gp each at settlement)."
            )
    return logs


def white_angel_resale_gp(item_name: str) -> int | None:
    if "white angel mushroom" in item_name.lower() and "resale" in item_name.lower():
        return 10
    return None
