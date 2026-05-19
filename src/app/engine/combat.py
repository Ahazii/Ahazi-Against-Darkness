from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState
from .class_combat import armor_defense_bonus, attack_modifier, defense_modifier
from .dice import roll_d6, roll_exploding_d6


@dataclass
class CombatRound:
    party: list[PartyMemberState]
    enemies: list[EnemyState]
    log: list[str]
    combat_over: bool
    morale_failed: bool = False


def attack_damage(total: int, foe_level: int) -> int:
    if total < foe_level:
        return 0
    return max(1, total // foe_level)


def attack_hits(total: int, foe_level: int) -> bool:
    return total >= foe_level


def defense_succeeds(total: int, foe_level: int, *, natural: int) -> bool:
    if natural == 1:
        return False
    return total > foe_level


def resolve_combat_round(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
    explain_math: bool = False,
    initial_minor_count: int | None = None,
) -> CombatRound:
    log: list[str] = []
    living_party = [pc for pc in party if pc.current_life > 0]
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    morale_failed = False

    for pc in living_party:
        if not living_enemies:
            break
        target = living_enemies[0]
        total, rolls = roll_exploding_d6()
        modifier = attack_modifier(pc, target)
        final_total = total + modifier
        if show_rolls:
            log.append(
                f"Attack roll: {pc.name} vs {target.name}: "
                f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total}."
            )
        if explain_math:
            log.append(f"Attack math: need total >= enemy level {target.level} to hit.")
        if not attack_hits(final_total, target.level):
            log.append(f"{pc.name} misses {target.name}.")
            continue

        if target.life <= 1 and target.category in {"vermin", "minions"}:
            kills = attack_damage(final_total, max(1, target.level))
            target.life -= kills
            log.append(f"{pc.name} slays {kills} {target.name}.")
            if target.life <= 0:
                living_enemies = [enemy for enemy in living_enemies if enemy.life > 0]
            continue

        damage = attack_damage(final_total, max(1, target.level))
        target.life -= damage
        log.append(f"{pc.name} hits {target.name} for {damage} damage.")
        if target.life <= target.max_life // 2 and target.max_life > 1:
            target.level = max(1, target.level - 1)
        if target.life <= 0:
            log.append(f"{target.name} is defeated.")
            living_enemies = [enemy for enemy in living_enemies if enemy.life > 0]

    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if living_enemies and living_party:
        minor_enemies = [enemy for enemy in living_enemies if enemy.life <= 1 and enemy.category in {"vermin", "minions"}]
        if minor_enemies and initial_minor_count:
            if len(minor_enemies) <= initial_minor_count // 2 and not morale_failed:
                morale_roll = roll_d6()
                if show_rolls:
                    log.append(f"Morale roll: d6 = {morale_roll}.")
                if morale_roll <= 3:
                    log.append("The remaining foes flee.")
                    for enemy in living_enemies:
                        enemy.life = 0
                    morale_failed = True
                    living_enemies = []

    if not morale_failed:
        for enemy in [enemy for enemy in enemies if enemy.life > 0]:
            for attack_index in range(max(1, enemy.attacks)):
                target = next((pc for pc in party if pc.current_life > 0), None)
                if target is None:
                    break
                total, rolls = roll_exploding_d6()
                modifier = defense_modifier(target, enemy) + armor_defense_bonus(target)
                final_total = total + modifier
                attack_label = f" attack {attack_index + 1}" if enemy.attacks > 1 else ""
                if show_rolls:
                    log.append(
                        f"Defense roll: {target.name} vs {enemy.name}{attack_label}: "
                        f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total}."
                    )
                if explain_math:
                    log.append(f"Defense math: need total > enemy level {enemy.level} to avoid damage.")
                if defense_succeeds(final_total, enemy.level, natural=rolls[0]):
                    log.append(f"{target.name} defends against {enemy.name}.")
                else:
                    target.current_life = max(0, target.current_life - 1)
                    log.append(f"{target.name} takes 1 damage from {enemy.name}.")
                    if target.current_life == 0:
                        log.append(f"{target.name} falls.")

    combat_over = not any(enemy.life > 0 for enemy in enemies) or not any(pc.current_life > 0 for pc in party)
    return CombatRound(
        party=party,
        enemies=enemies,
        log=log,
        combat_over=combat_over,
        morale_failed=morale_failed,
    )
