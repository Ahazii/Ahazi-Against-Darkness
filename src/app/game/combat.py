from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .dice import roll_d6
from ..models import Enemy, PartyStatus


@dataclass
class CombatResult:
    log: list[str]
    party: list[PartyStatus]
    enemies: list[Enemy]
    combat_over: bool


def resolve_combat_round(party: List[PartyStatus], enemies: List[Enemy]) -> CombatResult:
    log: list[str] = []
    living_party = [pc for pc in party if pc.current_life > 0]
    living_enemies = [foe for foe in enemies if foe.life > 0]

    for pc in living_party:
        if not living_enemies:
            break
        target = living_enemies[0]
        attack_roll = roll_d6() + pc.attack_bonus
        if attack_roll > target.level:
            target.life -= 1
            log.append(f"{pc.name} hits {target.name} (L{target.level}).")
            if target.life <= 0:
                log.append(f"{target.name} is defeated.")
                living_enemies = [foe for foe in living_enemies if foe.life > 0]
        else:
            log.append(f"{pc.name} misses {target.name}.")

    living_enemies = [foe for foe in living_enemies if foe.life > 0]

    for foe in living_enemies:
        for _ in range(max(1, foe.attacks)):
            target = next((pc for pc in living_party if pc.current_life > 0), None)
            if not target:
                break
            defense_roll = roll_d6() + target.defense_bonus
            if defense_roll <= foe.level:
                target.current_life -= 1
                log.append(f"{target.name} is hit by {foe.name}.")
                if target.current_life <= 0:
                    log.append(f"{target.name} falls!")
            else:
                log.append(f"{target.name} blocks {foe.name}.")

    combat_over = not any(foe.life > 0 for foe in living_enemies) or not any(
        pc.current_life > 0 for pc in party
    )

    return CombatResult(log=log, party=party, enemies=enemies, combat_over=combat_over)
