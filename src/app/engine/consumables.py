from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .class_combat import attack_modifier
from .combat import attack_hits, attack_damage
from .dice import roll_exploding_for_level


def is_holy_water(item_name: str) -> bool:
    lower = item_name.strip().lower()
    return lower in {"holy water vial", "holy water"} or "holy water" in lower


def is_undead_foe(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return "undead" in tags or "skeleton" in name or "wight" in name or "wraith" in name


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
        target.life = 0
        log.append(f"{target.name} is destroyed by the holy water.")
    else:
        damage = max(1, attack_damage(final_total, max(1, target.level)))
        target.life = max(0, target.life - damage)
        log.append(f"Holy water burns {target.name} for {damage} damage.")
        if target.life <= 0:
            log.append(f"{target.name} is destroyed.")
    return log, True
