from __future__ import annotations

import re
from collections.abc import Callable

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_d3, roll_d6
from .equipment_effects import has_crowbar, has_good_lockpicks, is_werecreature

WAND_OF_POWER_RE = re.compile(r"^wand of power\s*\((\d+)\s*charges?\)\s*$", re.IGNORECASE)
BERSERKER_MUSHROOM_STATUS = "Berserker's Mushroom (next combat)"
PIT_TRAPPED_STATUS = "Trapped in pit"


def party_has_rope(party: list[PartyMemberState]) -> bool:
    return any("rope" in item.lower() for member in party for item in member.inventory)


def member_has_torch(member: PartyMemberState) -> bool:
    return any("torch" in item.lower() for item in member.inventory)


def member_has_lantern(member: PartyMemberState, *, session: SessionState | None = None) -> bool:
    if session is not None and session.combat_lanterns_extinguished:
        return False
    return any("lantern" in item.lower() and "oil" not in item.lower() for item in member.inventory)


def member_has_light_source(member: PartyMemberState, *, session: SessionState | None = None) -> bool:
    if member_has_torch(member) or member_has_lantern(member, session=session):
        return True
    return any(
        status.lower() in {"continual light", "glittering crystal"}
        or status.lower().startswith("phoenix mushroom")
        for status in member.statuses
    )


def party_has_light_source(party: list[PartyMemberState], *, session: SessionState | None = None) -> bool:
    return any(member_has_light_source(member, session=session) for member in party if member.current_life > 0)


def consume_torch(member: PartyMemberState) -> tuple[bool, str | None]:
    for index, item in enumerate(member.inventory):
        if "torch" in item.lower():
            member.inventory.pop(index)
            return True, item
    return False, None


def consume_rope_from_party(party: list[PartyMemberState]) -> tuple[bool, str | None]:
    for member in party:
        for index, item in enumerate(member.inventory):
            if "rope" in item.lower():
                member.inventory.pop(index)
                return True, item
    return False, None


def extra_door_modifier(member: PartyMemberState, *, door_type: str, bashing: bool, lockpicking: bool) -> int:
    bonus = 0
    if lockpicking and has_good_lockpicks(member):
        bonus += 1
    if bashing and has_crowbar(member) and door_type in {"locked", "stuck"}:
        bonus += 1
    return bonus


def can_bash_door(member: PartyMemberState, door_type: str) -> bool:
    if door_type not in {"locked", "stuck"}:
        return False
    if member.class_id.lower() in {"warrior", "barbarian"}:
        return True
    return has_crowbar(member)


def enemy_dislikes_light(enemy: EnemyState) -> bool:
    name = enemy.name.lower()
    tags = {tag.lower() for tag in enemy.tags}
    if "light_averse" in tags or "dislikes_light" in tags:
        return True
    return any(token in name for token in ("morlock", "cave goblin", "drow", "dark elf"))


def light_source_defense_bonus(
    defender: PartyMemberState,
    attacker: EnemyState,
    *,
    session: SessionState | None = None,
) -> int:
    if enemy_dislikes_light(attacker) and member_has_light_source(defender, session=session):
        return 2
    return 0


def torch_fire_attack_bonus(
    attacker: PartyMemberState,
    target: EnemyState,
    *,
    damage_kind: str,
    session: SessionState | None = None,
) -> int:
    if damage_kind != "fire":
        return 0
    if "mummy" not in target.name.lower():
        return 0
    if member_has_torch(attacker) or member_has_lantern(attacker, session=session):
        return 2
    return 0


def flee_blocked_by_web(enemies: list[EnemyState], *, torch_spent: bool) -> tuple[bool, str]:
    if torch_spent:
        return False, ""
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        name = enemy.name.lower()
        tags = {tag.lower() for tag in enemy.tags}
        if "spider" in name and ("web" in tags or "giant spider" in name):
            return True, "Giant spider webs block fleeing until a torch is spent or Fireball burns the web."
    return False, ""


def is_map_fragment(item: str) -> bool:
    return "map fragment" in item.lower()


def is_enchanted_paint(item: str) -> bool:
    return "enchanted paint" in item.lower()


def is_glittering_crystal(item: str) -> bool:
    return "glittering crystal" in item.lower()


def is_miners_ointment(item: str) -> bool:
    return "miners' ointment" in item.lower() or "miners ointment" in item.lower()


def is_miners_amulet(item: str) -> bool:
    return "miners' amulet" in item.lower() or "miners amulet" in item.lower()


def is_herbal_tonic(item: str) -> bool:
    return "herbal tonic" in item.lower()


def is_prayer_bead_necklace(item: str) -> bool:
    return "prayer bead" in item.lower() and "necklace" in item.lower()


def prayer_bead_count(item: str) -> int:
    import re

    match = re.search(r"(\d+)\s*prayer bead", item.lower())
    return int(match.group(1)) if match else 0


def format_prayer_bead_necklace(count: int) -> str:
    word = "bead" if count == 1 else "beads"
    return f"Necklace with {count} prayer {word}"


def member_has_prayer_bead_necklace(member: PartyMemberState) -> bool:
    return any(is_prayer_bead_necklace(item) and prayer_bead_count(item) > 0 for item in member.inventory)


def consume_prayer_bead(member: PartyMemberState) -> tuple[bool, bool, list[str]]:
    """Returns used, prayer_saved, log."""
    necklace = next((item for item in member.inventory if is_prayer_bead_necklace(item)), None)
    if necklace is None:
        return False, False, []
    count = prayer_bead_count(necklace)
    if count <= 0:
        return False, False, []
    roll = roll_d6()
    log = [f"{member.name} rolls d6 on a prayer bead: {roll}."]
    count -= 1
    if count <= 0:
        member.inventory = [item for item in member.inventory if item != necklace]
        log.append("The last prayer bead crumbles; the necklace is gone.")
    else:
        member.inventory = [
            format_prayer_bead_necklace(count) if item == necklace else item for item in member.inventory
        ]
        log.append(f"1 prayer bead is destroyed ({count} remain).")
    saved = roll >= 4
    if saved:
        log.append("The Prayer takes effect but is not expended.")
    else:
        log.append("The Prayer is cast normally.")
    return True, saved, log


def equip_glittering_crystal(member: PartyMemberState) -> list[str]:
    if "Glittering Crystal" in member.statuses:
        return [f"{member.name} already wears the Glittering Crystal."]
    member.statuses.append("Glittering Crystal")
    return [f"{member.name} wears the Glittering Crystal like a lantern."]


def use_miners_ointment(member: PartyMemberState, item_name: str) -> tuple[list[str], bool]:
    member.inventory = [item for item in member.inventory if item != item_name]
    return [f"{member.name} applies Miners' Ointment (wards off Wandering Monsters or invisible gremlins once)."], True


def use_herbal_tonic(member: PartyMemberState, item_name: str) -> list[str]:
    member.inventory = [item for item in member.inventory if item != item_name]
    member.current_life = min(member.max_life, member.current_life + 1)
    return [
        f"{member.name} drinks {item_name} and recovers 1 Life "
        f"({member.current_life}/{member.max_life})."
    ]


def is_wolfsbane(item: str) -> bool:
    return "wolfsbane" in item.lower()


def is_berserkers_mushroom(item: str) -> bool:
    lower = item.lower()
    return "berserker" in lower and "mushroom" in lower


def is_wand_of_power(item: str) -> bool:
    return WAND_OF_POWER_RE.match(item.strip()) is not None


def parse_wand_of_power_charges(item: str) -> int | None:
    match = WAND_OF_POWER_RE.match(item.strip())
    if not match:
        return None
    return int(match.group(1))


def format_wand_of_power(charges: int) -> str:
    word = "charge" if charges == 1 else "charges"
    return f"Wand of Power ({charges} {word})"


def roll_wand_of_power_charges(*, roll_fn: Callable[[int], list[int]] | None = None) -> tuple[str, int, list[str]]:
    roller = roll_fn or (lambda _count: [roll_d3(), roll_d3()])
    rolls = roller(2)
    total = sum(rolls)
    charges = max(1, total)
    return format_wand_of_power(charges), charges, [f"Wand of Power charges: 2d3 = {' + '.join(str(v) for v in rolls)} = {charges}."]


def consume_wand_power_charges(item: str, count: int) -> str | None:
    charges = parse_wand_of_power_charges(item)
    if charges is None or count <= 0 or count > charges:
        return None
    remaining = charges - count
    if remaining <= 0:
        return None
    return format_wand_of_power(remaining)


def eat_berserkers_mushroom(member: PartyMemberState, item_name: str) -> list[str]:
    if BERSERKER_MUSHROOM_STATUS in member.statuses:
        return [f"{member.name} already has a Berserker's Mushroom effect pending."]
    member.statuses.append(BERSERKER_MUSHROOM_STATUS)
    member.inventory = [item for item in member.inventory if item != item_name]
    return [
        f"{member.name} eats {item_name}; the next combat allows a 3d6-keep-best rage attack once (barbarian-style)."
    ]


def throw_wolfsbane(thrower: PartyMemberState, target: EnemyState, item_name: str) -> tuple[list[str], bool]:
    log: list[str] = [f"{thrower.name} throws Wolfsbane at {target.name}."]
    if not is_werecreature(target):
        log.append("Wolfsbane only affects lycanthropes.")
        return log, False
    thrower.inventory = [item for item in thrower.inventory if item != item_name]
    apply_damage = 2 if target.life > 2 else target.life
    from .combat import apply_enemy_damage

    apply_enemy_damage(target, apply_damage, damage_kind="normal")
    log.append(f"Wolfsbane burns {target.name} for {apply_damage} Life.")
    if target.life <= 0:
        log.append(f"{target.name} is destroyed.")
    return log, True


def apply_enchanted_paint(
    member: PartyMemberState,
    *,
    choice: str,
    quantity: int = 1,
    direction: str | None = None,
    show_rolls: bool = True,
) -> tuple[list[str], bool, bool]:
    """Returns log, consumed paint use, paint depleted."""
    paint = next((item for item in member.inventory if is_enchanted_paint(item)), None)
    if paint is None:
        return [f"{member.name} has no Enchanted Paint."], False, False
    log: list[str] = [f"{member.name} uses Enchanted Paint to create {choice.replace('_', ' ')}."]
    depleted = False
    roll = roll_d6()
    if show_rolls:
        log.append(f"Enchanted Paint durability: d6 = {roll} (1 = runs out).")
    if choice == "food_rations":
        count = max(1, min(8, quantity))
        member.inventory.extend(["Food ration"] * count)
        log.append(f"The paint becomes {count} Food ration(s).")
    elif choice == "hand_weapon":
        member.inventory.append("Hand weapon")
        log.append("The paint becomes a Hand weapon.")
    elif choice == "light_armor":
        member.inventory.append("Light armor")
        log.append("The paint becomes Light armor.")
    elif choice == "heavy_armor":
        member.inventory.append("Heavy armor")
        log.append("The paint becomes Heavy armor.")
    elif choice == "shield":
        member.inventory.append("Shield")
        log.append("The paint becomes a Shield.")
    elif choice == "paint_door":
        if not direction:
            return ["Choose north, south, east, or west for the painted door."], False, False
        log.append(f"The paint becomes an unlocked door on the {direction} wall.")
    else:
        return [f"Unknown Enchanted Paint choice: {choice}."], False, False
    member.inventory = [item for item in member.inventory if item != paint]
    if roll == 1:
        depleted = True
        log.append("The Enchanted Paint runs out.")
    else:
        member.inventory.append(paint)
        log.append("Some Enchanted Paint remains.")
    return log, True, depleted


def consume_wand_cast_bonus(member: PartyMemberState) -> None:
    member.statuses = [status for status in member.statuses if not status.startswith(WAND_CAST_STATUS_PREFIX)]


def wand_cast_bonus(member: PartyMemberState) -> int:
    for status in member.statuses:
        if status.startswith(WAND_CAST_STATUS_PREFIX):
            try:
                return int(status[len(WAND_CAST_STATUS_PREFIX) :])
            except ValueError:
                return 0
    return 0


def apply_wand_cast_bonus(member: PartyMemberState, charges: int) -> None:
    consume_wand_cast_bonus(member)
    if charges > 0:
        member.statuses.append(f"{WAND_CAST_STATUS_PREFIX}{charges}")


WAND_CAST_STATUS_PREFIX = "Wand of Power cast +"


def mark_pit_trapped(member: PartyMemberState) -> None:
    if PIT_TRAPPED_STATUS not in member.statuses:
        member.statuses.append(PIT_TRAPPED_STATUS)


def clear_pit_trapped(member: PartyMemberState) -> None:
    member.statuses = [status for status in member.statuses if status != PIT_TRAPPED_STATUS]


def is_pit_trapped(member: PartyMemberState) -> bool:
    return PIT_TRAPPED_STATUS in member.statuses


def climb_from_pit(
    session: SessionState,
    helper: PartyMemberState,
    trapped: PartyMemberState,
    party: list[PartyMemberState],
) -> list[str]:
    if not is_pit_trapped(trapped):
        return [f"{trapped.name} is not trapped in a pit."]
    if party_has_rope(party):
        consume_rope_from_party(party)
        clear_pit_trapped(trapped)
        return [f"{trapped.name} climbs out using the party's rope."]
    if helper.character_id == trapped.character_id:
        return [f"{trapped.name} needs another hero's help or a rope to climb out of the pit."]
    if helper.current_life <= 0:
        return [f"{helper.name} cannot help while fallen."]
    clear_pit_trapped(trapped)
    return [f"{helper.name} helps {trapped.name} climb out of the pit."]


def resolve_special_treasure_items(
    items: list[str],
    *,
    roll_fn: Callable[[], int] | None = None,
) -> tuple[list[str], list[str]]:
    from .magic_weapons import resolve_treasure_item_list

    resolved, log = resolve_treasure_item_list(items, roll_fn=roll_fn)
    output: list[str] = []
    for item in resolved:
        if parse_wand_of_power_charges(item) is not None:
            output.append(item)
            continue
        lowered = item.lower()
        if lowered.startswith("wand of power"):
            name, _, charge_log = roll_wand_of_power_charges()
            output.append(name)
            log.extend(charge_log)
            continue
        if is_prayer_bead_necklace(item) and "d6" in lowered:
            bead_roll = roll_d6() if roll_fn is None else roll_fn()
            name = format_prayer_bead_necklace(bead_roll)
            output.append(name)
            log.append(f"Prayer beads: d6 = {bead_roll}.")
            continue
        output.append(item)
    return output, log
