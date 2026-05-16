from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState
from .dice import roll_d6


@dataclass
class CombatRound:
    party: list[PartyMemberState]
    enemies: list[EnemyState]
    log: list[str]
    combat_over: bool


def resolve_combat_round(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
) -> CombatRound:
    log: list[str] = []
    living_party = [pc for pc in party if pc.current_life > 0]
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]

    for pc in living_party:
        if not living_enemies:
            break
        target = living_enemies[0]
        roll = roll_d6()
        total = roll + pc.attack_bonus
        if roll == 6 or total > target.level:
            target.life -= 1
            log.append(f"{pc.name} hits {target.name}.")
            if target.life <= 0:
                log.append(f"{target.name} is defeated.")
                living_enemies = [enemy for enemy in living_enemies if enemy.life > 0]
        else:
            log.append(f"{pc.name} misses {target.name}.")

    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    for enemy in living_enemies:
        for _ in range(max(1, enemy.attacks)):
            target = next((pc for pc in party if pc.current_life > 0), None)
            if target is None:
                break
            roll = roll_d6()
            total = roll + target.defense_bonus
            if roll == 1 or total <= enemy.level:
                target.current_life = max(0, target.current_life - 1)
                log.append(f"{target.name} takes 1 damage from {enemy.name}.")
                if target.current_life == 0:
                    log.append(f"{target.name} falls.")
            else:
                log.append(f"{target.name} defends against {enemy.name}.")

    combat_over = not any(enemy.life > 0 for enemy in enemies) or not any(
        pc.current_life > 0 for pc in party
    )
    return CombatRound(party=party, enemies=enemies, log=log, combat_over=combat_over)
