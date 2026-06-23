from __future__ import annotations

import random
from typing import TYPE_CHECKING

from .dice import roll_d6, roll_exploding_for_level

if TYPE_CHECKING:
    from ..schemas import EnemyState, PartyMemberState, SessionState


def cavern_contamination_save_penalty(session: SessionState | None, member: PartyMemberState) -> int:
    if session is None:
        return 0
    if member.character_id in session.cavern_contaminated_character_ids:
        return -1
    return 0


def cleanse_cavern_water_contamination(session: SessionState, character_id: str) -> bool:
    if character_id not in session.cavern_contaminated_character_ids:
        return False
    session.cavern_contaminated_character_ids = [
        entry for entry in session.cavern_contaminated_character_ids if entry != character_id
    ]
    return True


def cavern_stealth_modifier(cavern_feature_key: str | None) -> int:
    if cavern_feature_key == "echo":
        return -1
    if cavern_feature_key == "boulders":
        return 1
    return 0


def cavern_pc_ranged_attack_modifier(cavern_feature_key: str | None, *, missile: bool) -> int:
    if missile and cavern_feature_key == "boulders":
        return -1
    return 0


def cavern_pc_defense_vs_ranged_modifier(cavern_feature_key: str | None, *, enemy_ranged: bool) -> int:
    if enemy_ranged and cavern_feature_key == "boulders":
        return 1
    return 0


def cavern_blocks_pc_attack_explode(cavern_feature_key: str | None) -> bool:
    return cavern_feature_key == "stalagmites"


def wandering_check_triggers(
    cavern_feature_key: str | None,
    *,
    roll_bonus: int = 0,
) -> tuple[bool, int]:
    roll = roll_d6()
    threshold = 1 + max(0, roll_bonus)
    if cavern_feature_key == "echo":
        return roll <= min(2 + roll_bonus, 6), roll
    return roll <= threshold, roll


def enemy_has_surprise_chance(enemy: EnemyState) -> bool:
    return "surprise" in enemy.tags or any("surprise" in tag for tag in enemy.tags)


def boulder_surprise_triggers(cavern_feature_key: str | None, enemies: list[EnemyState]) -> tuple[bool, int]:
    if cavern_feature_key != "boulders":
        return False, 0
    if not any(enemy.life > 0 and enemy_has_surprise_chance(enemy) for enemy in enemies):
        return False, 0
    roll = roll_d6()
    return roll <= 2, roll


def template_surprise_tags(template: dict) -> list[str]:
    tags = list(template.get("tags", []))
    if template.get("surprise_chance") or template.get("surprise"):
        if "surprise" not in tags:
            tags.append("surprise")
    return tags


def maybe_stalactite_fall_after_explosive_two_handed_hit(
    *,
    cavern_feature_key: str | None,
    attacker: PartyMemberState,
    weapon,
    missile: bool,
    attack_rolls: list[int] | None,
    hcl: int,
    party: list[PartyMemberState],
    living_enemies: list[EnemyState],
    log: list[str],
    show_rolls: bool,
) -> None:
    from .combat import attack_damage, attack_hits, defense_succeeds

    if cavern_feature_key != "stalactites":
        return
    if missile or weapon is None or not getattr(weapon, "two_handed", False):
        return
    if not attack_rolls or len(attack_rolls) <= 1:
        return
    trigger_roll = roll_d6()
    if show_rolls:
        log.append(f"Stalactites: explosive two-handed hit — trigger roll d6 = {trigger_roll} (need 1-3).")
    if trigger_roll > 3:
        return
    target_roll = roll_d6()
    if show_rolls:
        log.append(f"Stalactites: falling stalactite target roll d6 = {target_roll}.")
    if target_roll <= 3:
        living_party = [member for member in party if member.current_life > 0]
        if not living_party:
            return
        victim = random.choice(living_party)
        defense_total, defense_rolls = roll_exploding_for_level(victim)
        if show_rolls:
            log.append(
                f"Stalactites: {victim.name} Defense vs HCL {hcl}: "
                f"{' + '.join(str(value) for value in defense_rolls)} = {defense_total}."
            )
        if defense_succeeds(defense_total, hcl, natural=defense_rolls[0]):
            log.append(f"Effect: {victim.name} dodges the falling stalactite.")
            return
        from .party_life import apply_party_life_loss

        apply_party_life_loss(None, victim, 1)
        log.append(f"Effect: {victim.name} loses 1 Life to a falling stalactite.")
        return
    if not living_enemies:
        log.append("Stalactites: the stalactite falls but no foe is struck.")
        return
    foe = random.choice(living_enemies)
    attack_total, attack_rolls_stal = roll_exploding_for_level(attacker)
    attack_total += hcl
    if show_rolls:
        log.append(
            f"Stalactites: stalactite Attack vs {foe.name} (+HCL {hcl}): "
            f"{' + '.join(str(value) for value in attack_rolls_stal)} + {hcl} = {attack_total}."
        )
    if not attack_hits(attack_total, foe.level):
        log.append(f"Stalactites: the stalactite misses {foe.name}.")
        return
    damage = 1
    foe.life = max(0, foe.life - damage)
    log.append(f"Effect: Stalactite hits {foe.name} for {damage} damage.")


def echo_spell_repeats(cavern_feature_key: str | None, *, echo_repeat: bool) -> tuple[bool, int]:
    if echo_repeat or cavern_feature_key != "echo":
        return False, 0
    roll = roll_d6()
    return roll == 6, roll
