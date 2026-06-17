from __future__ import annotations

from ..schemas import EnemyState


def is_major_foe(enemy: EnemyState) -> bool:
    return enemy.category in {"weird", "boss"} or enemy.max_life > 1


def apply_major_foe_level_drop(enemy: EnemyState) -> bool:
    """Apply the one-time half-Life level drop for major foes."""
    if enemy.life <= 0 or enemy.max_life <= 1 or not is_major_foe(enemy):
        return False
    if enemy.level_drop_applied or enemy.life > enemy.max_life // 2:
        return False
    enemy.level = max(1, enemy.level - 1)
    enemy.level_drop_applied = True
    return True


def reduce_foe_level(enemy: EnemyState, amount: int = 1) -> bool:
    if enemy.life <= 0 or amount <= 0:
        return False
    if enemy.level <= 1:
        return False
    enemy.level = max(1, enemy.level - amount)
    return True


def apply_subdual_damage(enemy: EnemyState, damage: int) -> bool:
    """Apply subdual damage. Returns True if the foe is now subdued."""
    if damage <= 0:
        return False
    enemy.life = max(0, enemy.life - damage)
    if enemy.life <= 0:
        enemy.life = 0
        enemy.subdued = True
        return True
    apply_major_foe_level_drop(enemy)
    return False


def subdue_minor_foe(enemy: EnemyState) -> None:
    enemy.life = 0
    enemy.subdued = True
