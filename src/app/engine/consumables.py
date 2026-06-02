from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .class_combat import attack_modifier, save_modifier
from .combat import apply_enemy_damage, attack_hits, attack_damage
from .dice import roll_d6, roll_exploding_for_level


def is_holy_water(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return lower in {"holy water vial", "holy water"} or "holy water" in lower


def is_undead_foe(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "undead" in tags or "skeleton" in name or "wight" in name or "wraith" in name


def is_lantern_oil(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return "lantern oil" in lower


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
    if "mushroom" not in lower:
        return None
    for key in ("healing", "strength", "clarity", "poison", "madness", "golden"):
        if key in lower:
            return key
    return None


def is_mushroom(item_name: str) -> bool:
    return mushroom_kind(item_name) is not None


def use_mushroom(
    eater: PartyMemberState,
    item_name: str,
    *,
    show_rolls: bool = True,
) -> tuple[list[str], bool]:
    """Eat a rare mushroom (EE p.159 fungal grottoes table)."""
    kind = mushroom_kind(item_name)
    if kind is None:
        return [f"{item_name} is not a usable mushroom."], False
    log: list[str] = [f"{eater.name} eats {item_name}."]
    if kind == "healing":
        if eater.current_life >= eater.max_life:
            log.append(f"{eater.name} is already at full Life.")
            return log, False
        eater.current_life += 1
        log.append(f"{eater.name} heals 1 Life ({eater.current_life}/{eater.max_life}).")
        return log, True
    if kind == "strength":
        eater.statuses = [s for s in eater.statuses if "strength +1" not in s.lower()]
        eater.statuses.append("Strength +1")
        log.append(f"{eater.name} gains +1 Attack for the next fight.")
        return log, True
    if kind == "clarity":
        eater.statuses = [s for s in eater.statuses if "clarity +1" not in s.lower()]
        eater.statuses.append("Clarity +1")
        log.append(f"{eater.name} gains +1 on the next spell roll.")
        return log, True
    if kind == "poison":
        if any("blade poison" in item.lower() for item in eater.inventory):
            log.append(f"{eater.name} already carries blade poison.")
            return log, False
        eater.inventory.append("Blade poison")
        log.append(f"{eater.name} extracts blade poison from the mushroom.")
        return log, True
    if kind == "madness":
        from .heroic_skill_effects import stable_mind_save_bonus

        fear_level = 3
        modifier = save_modifier(eater) + stable_mind_save_bonus(eater)
        total, rolls = roll_exploding_for_level(eater.level)
        if show_rolls:
            detail = " + ".join(str(value) for value in rolls)
            if modifier:
                detail += f" + {modifier}"
            log.append(f"Fear Save vs L{fear_level}: {detail} = {total + modifier}.")
        if rolls[0] == 1 or total + modifier < fear_level:
            if not any(status.lower().startswith("madness") for status in eater.statuses):
                eater.statuses.append("Madness 1")
            log.append(f"{eater.name} fails and gains 1 Madness.")
        else:
            log.append(f"{eater.name} resists the mushroom's madness.")
        return log, True
    if kind == "golden":
        gold = sum(roll_d6() for _ in range(3)) * 10
        eater.gold += gold
        log.append(f"The golden mushroom is worth {gold}gp.")
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
