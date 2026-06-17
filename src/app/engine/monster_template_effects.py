from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .combat import CombatContext

LIFE_DRAIN_NOT_HIT_TAG = "life_drain_not_hit"


def template_combat_tags(template: dict) -> list[str]:
    tags: list[str] = []
    for effect in template.get("per_turn_effects", []):
        if str(effect.get("type", "")).lower() != "life_drain":
            continue
        if str(effect.get("trigger", "")).lower() == "not_hit_this_turn":
            tags.append(LIFE_DRAIN_NOT_HIT_TAG)
    return tags


def enemy_has_life_drain_not_hit(enemy: EnemyState) -> bool:
    return LIFE_DRAIN_NOT_HIT_TAG in {tag.lower() for tag in enemy.tags}


def mark_enemy_hit(context: CombatContext, enemy_id: str) -> None:
    context.enemies_hit_this_round.add(enemy_id)


def apply_life_drain_after_party_turn(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    *,
    context: CombatContext,
    show_rolls: bool = True,
) -> list[str]:
    log: list[str] = []
    living_party = [member for member in party if member.current_life > 0]
    if not living_party:
        return log
    for enemy in enemies:
        if enemy.life <= 0 or not enemy_has_life_drain_not_hit(enemy):
            continue
        if enemy.id in context.enemies_hit_this_round:
            if show_rolls:
                log.append(f"{enemy.name} was hit this round — its life drain does not trigger.")
            continue
        for member in living_party:
            member.current_life = max(0, member.current_life - 1)
        names = ", ".join(member.name for member in living_party)
        log.append(
            f"{enemy.name} was not hit this round — {names} "
            f"{'each lose' if len(living_party) > 1 else 'loses'} 1 Life to life drain."
        )
    return log
