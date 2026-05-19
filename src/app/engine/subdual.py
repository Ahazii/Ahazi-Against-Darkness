from __future__ import annotations

from ..schemas import EnemyState


def is_major_foe(enemy: EnemyState) -> bool:
    return enemy.category in {"weird", "boss"} or enemy.max_life > 1


def apply_subdual_damage(enemy: EnemyState, damage: int) -> bool:
    """Apply subdual damage. Returns True if the foe is now subdued."""
    if damage <= 0:
        return False
    enemy.life = max(0, enemy.life - damage)
    if enemy.life <= 0:
        enemy.life = 0
        enemy.subdued = True
        return True
    if enemy.life <= enemy.max_life // 2 and enemy.max_life > 1:
        enemy.level = max(1, enemy.level - 1)
    return False


def subdue_minor_foe(enemy: EnemyState) -> None:
    enemy.life = 0
    enemy.subdued = True
