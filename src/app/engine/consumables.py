from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .class_combat import attack_modifier, save_modifier
from .combat import apply_enemy_damage, attack_hits, attack_damage
from .dice import roll_d6, roll_exploding_for_level

SLUMBER_AMANITA_STATUS = "Slumber Amanita +Tier Sleep"
PHOENIX_MUSHROOM_STATUS = "Phoenix Mushroom (3 tiles)"


def is_holy_water(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return lower in {"holy water vial", "holy water"} or "holy water" in lower


def is_undead_foe(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "undead" in tags or "skeleton" in name or "wight" in name or "wraith" in name


def is_lantern_oil(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return "lantern oil" in lower or "flammable oil" in lower or "flask of oil" in lower


def foe_has_regeneration(enemy: EnemyState) -> bool:
    return "regeneration" in {tag.lower() for tag in enemy.tags}


def throw_holy_water(
    thrower: PartyMemberState,
    target: EnemyState,
    *,
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    """Throw holy water at an undead foe (rulebook p.110 area / classic vial rules)."""
    log: list[str] = [f"{thrower.name} throws holy water at {target.name}."]
    if not is_undead_foe(target):
        log.append("Holy water only affects undead.")
        return log, False

    total, rolls = roll_exploding_for_level(thrower.level)
    modifier = attack_modifier(thrower, target)
    final_total = total + modifier
    if show_rolls:
        log.append(
            f"Holy water: {' + '.join(str(value) for value in rolls)} + {modifier} = "
            f"{final_total} vs L{target.level}."
        )
    if not attack_hits(final_total, target.level):
        log.append("The holy water misses.")
        return log, False

    if target.life <= 1 and target.category in {"vermin", "minions"}:
        apply_enemy_damage(target, target.life, damage_kind="fire")
        log.append(f"{target.name} is destroyed by the holy water.")
    else:
        damage = max(1, attack_damage(final_total, max(1, target.level)))
        apply_enemy_damage(target, damage, damage_kind="fire")
        log.append(f"Holy water burns {target.name} for {damage} damage.")
        if target.life <= 0:
            log.append(f"{target.name} is destroyed.")
    return log, True


def splash_lantern_oil(
    thrower: PartyMemberState,
    target: EnemyState,
    *,
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    """Splash and ignite lantern oil on a foe (EE p.99 / p.110; blocks troll regeneration)."""
    log: list[str] = [f"{thrower.name} splashes lantern oil on {target.name} and ignites it."]
    total, rolls = roll_exploding_for_level(thrower.level)
    modifier = attack_modifier(thrower, target)
    final_total = total + modifier
    if show_rolls:
        log.append(
            f"Oil splash: {' + '.join(str(value) for value in rolls)} + {modifier} = "
            f"{final_total} vs L{target.level}."
        )
    if not attack_hits(final_total, target.level):
        log.append("The burning oil misses.")
        return log, False

    if target.life <= 1 and target.category in {"vermin", "minions"}:
        apply_enemy_damage(target, target.life, damage_kind="oil")
        log.append(f"{target.name} is burned to ash.")
    else:
        apply_enemy_damage(target, 1, damage_kind="oil")
        log.append(f"Burning oil sears {target.name} for 1 Life (regeneration blocked).")
        if target.life <= 0:
            log.append(f"{target.name} is defeated.")
    return log, True


def is_acid_vial(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return lower in {"acid vial", "vial of acid"} or "acid vial" in lower


def mushroom_kind(item_name: str) -> str | None:
    lower = item_name.strip().lower()
    if (
        "mushroom" not in lower
        and "amanita" not in lower
        and "puffball" not in lower
        and "truffle" not in lower
        and "chanterelle" not in lower
        and "brown cap" not in lower
        and "morel" not in lower
    ):
        return None
    if "slumber amanita" in lower:
        return "slumber_amanita"
    if "puffball smokebomb" in lower:
        return "puffball_smokebomb"
    if "brown cap delight" in lower:
        return "brown_cap_delight"
    if "phoenix mushroom" in lower:
        return "phoenix_mushroom"
    if "purple truffle" in lower:
        return "purple_truffle"
    if "healer" in lower and "chanterelle" in lower:
        return "healers_chanterelle"
    if "morel crusher" in lower:
        return "morel_crusher"
    return None


def is_mushroom(item_name: str) -> bool:
    return mushroom_kind(item_name) is not None


def mushroom_resale_value(item_name: str, seller: PartyMemberState | None = None, *, show_rolls: bool = True) -> tuple[int | None, list[str]]:
    kind = mushroom_kind(item_name)
    if kind == "slumber_amanita":
        return 10, []
    if kind == "puffball_smokebomb":
        return 5, []
    if kind == "brown_cap_delight":
        return 15, []
    if kind == "phoenix_mushroom":
        return 15, []
    if kind == "healers_chanterelle":
        return None, [f"{item_name} has no listed resale value."]
    if kind == "morel_crusher":
        return 40, []
    if kind == "purple_truffle":
        chance = roll_d6()
        log: list[str] = []
        if show_rolls:
            log.append(f"Purple Truffle authenticity: d6 = {chance} (1-3 fake).")
        if chance <= 3 and seller is not None and seller.class_id.lower() == "halfling":
            reroll = roll_d6()
            if show_rolls:
                log.append(f"{seller.name} is a halfling and rerolls: d6 = {reroll}.")
            chance = reroll
        if chance <= 3:
            value = roll_d6()
            if show_rolls:
                log.append(f"The truffle is a lesser lookalike worth {value}gp.")
            return value, log
        value = sum(roll_d6() for _ in range(6))
        if show_rolls:
            log.append(f"The Purple Truffle is genuine and sells for {value}gp.")
        return value, log
    return None, [f"{item_name} is not a sellable rare mushroom."]


def use_mushroom(
    eater: PartyMemberState,
    item_name: str,
    *,
    mode: str = "exploration",
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    """Eat a rare mushroom (EE p.159 fungal grottoes table)."""
    kind = mushroom_kind(item_name)
    if kind is None:
        return [f"{item_name} is not a usable mushroom."], False
    if eater.class_id.lower() == "mushroom_monk":
        return [f"{eater.name} cannot use rare mushrooms."], False
    log: list[str] = [f"{eater.name} uses {item_name}."]
    if kind == "slumber_amanita":
        eater.statuses = [status for status in eater.statuses if status != SLUMBER_AMANITA_STATUS]
        eater.statuses.append(SLUMBER_AMANITA_STATUS)
        log.append(f"{eater.name}'s next Sleep spell gains +Tier, including from a scroll or Wand of Sleep.")
        return log, True
    if kind == "puffball_smokebomb":
        if mode != "combat":
            log.append("Puffball Smokebomb is dropped during combat to support fleeing.")
            return log, False
        log.append("Puffball Smokebomb is dropped as a free action; the party may flee without attacks.")
        return log, True
    if kind == "morel_crusher":
        if mode != "combat":
            log.append("Morel Crusher is broken during combat to frighten a foe.")
            return log, False
        log.append("Choose a foe to target with Morel Crusher.")
        return log, False
    if mode != "exploration":
        return ["It is not possible to eat mushrooms during combat."], False
    if eater.current_life <= 0:
        return [f"{eater.name} is not living and cannot eat mushrooms."], False
    if kind == "brown_cap_delight":
        eater.inventory.append("Food ration")
        log.append("Brown Cap Delight counts as 1 Food ration when eaten.")
        return log, True
    if kind == "phoenix_mushroom":
        eater.statuses = [status for status in eater.statuses if not status.lower().startswith("phoenix mushroom")]
        eater.statuses.append(PHOENIX_MUSHROOM_STATUS)
        log.append(f"{eater.name} gains +1 Defense and Saves for 3 tiles, then loses 1 Life.")
        return log, True
    if kind == "purple_truffle":
        log.append("Purple Truffle is sold rather than eaten; its value is checked when sold.")
        return log, False
    if kind == "healers_chanterelle":
        if eater.current_life >= eater.max_life:
            log.append(f"{eater.name} is already at full Life.")
            return log, False
        healed = eater.max_life - eater.current_life
        eater.current_life = eater.max_life
        log.append(f"Healer's Chanterelle heals all damage on {eater.name} ({healed} Life).")
        return log, True
    return log, False


def throw_acid_vial(
    thrower: PartyMemberState,
    target: EnemyState,
    *,
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    """Throw acid at a foe (suppresses troll regeneration)."""
    log: list[str] = [f"{thrower.name} throws acid at {target.name}."]
    total, rolls = roll_exploding_for_level(thrower.level)
    modifier = attack_modifier(thrower, target)
    final_total = total + modifier
    if show_rolls:
        log.append(
            f"Acid: {' + '.join(str(value) for value in rolls)} + {modifier} = "
            f"{final_total} vs L{target.level}."
        )
    if not attack_hits(final_total, target.level):
        log.append("The acid misses.")
        return log, False

    if target.life <= 1 and target.category in {"vermin", "minions"}:
        apply_enemy_damage(target, target.life, damage_kind="acid")
        log.append(f"{target.name} is dissolved by the acid.")
    else:
        damage = max(1, attack_damage(final_total, max(1, target.level)))
        apply_enemy_damage(target, damage, damage_kind="acid")
        log.append(f"Acid burns {target.name} for {damage} damage (regeneration blocked).")
        if target.life <= 0:
            log.append(f"{target.name} is defeated.")
    return log, True
