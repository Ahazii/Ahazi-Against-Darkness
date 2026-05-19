from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState
from .combat import attack_damage, living_party
from .combat_modifiers import enemy_magic_resist_bonus, spell_target_level
from .dice import roll_d6, roll_exploding_d6


SLEEP_IMMUNE_TAGS = {"undead", "dragon", "artificial", "clockwork", "elemental", "spirit", "construct"}


@dataclass
class SpellOutcome:
    log: list[str]
    enemies: list[EnemyState]
    party: list[PartyMemberState]
    combat_over: bool = False
    spell_consumed: bool = True


def normalize_spell_name(name: str) -> str:
    return name.strip().lower().replace("'", "").replace(" ", "_")


def can_cast_spell(member: PartyMemberState, spell_name: str) -> bool:
    target = normalize_spell_name(spell_name)
    return any(normalize_spell_name(item) == target or target in normalize_spell_name(item) for item in member.spells)


def spellcasting_modifier(member: PartyMemberState) -> int:
    class_id = member.class_id.lower()
    if class_id in {"wizard", "elf", "illusionist", "druid", "cleric"}:
        return member.level
    return 0


def spell_hits(
    member: PartyMemberState,
    enemy: EnemyState,
    *,
    show_rolls: bool,
    label: str,
) -> tuple[bool, list[str]]:
    target_level = spell_target_level(enemy)
    total, rolls = roll_exploding_d6()
    modifier = spellcasting_modifier(member)
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        mr = enemy_magic_resist_bonus(enemy)
        mr_note = f" (MR +{mr}, effective L{target_level})" if mr else ""
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} "
            f"vs L{target_level}{mr_note}."
        )
    return final_total >= target_level, log


def resolve_spell_cast(
    spell_name: str,
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    target_character_id: str | None = None,
    show_rolls: bool = True,
) -> SpellOutcome:
    key = normalize_spell_name(spell_name)
    log: list[str] = [f"{caster.name} casts {spell_name}."]
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if key in {"fireball", "fire_ball"}:
        return _cast_fireball(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "lightning":
        return _cast_lightning(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "sleep":
        return _cast_sleep(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "protection":
        return _cast_protection(caster, party, living_enemies, target_character_id, log)
    if key == "blessing":
        return _cast_blessing(caster, party, living_enemies, target_character_id, log)
    if key in {"healing_prayer", "healing"}:
        return _cast_healing_prayer(caster, party, living_enemies, target_character_id, log)
    if key == "escape":
        log.append("Escape teleports the caster toward the entrance (resolve movement manually).")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True)
    log.append(f"Unknown or unsupported spell: {spell_name}.")
    return SpellOutcome(log, living_enemies, party, spell_consumed=False)


def _cast_fireball(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
) -> SpellOutcome:
    if not enemies:
        log.append("There are no targets for Fireball.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = enemies[0]
    if "dragon" in target.tags and "undead" not in target.tags:
        log.append("Fireball has no effect on this dragon.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    effective_level = spell_target_level(target)
    total, rolls = roll_exploding_d6()
    modifier = spellcasting_modifier(caster)
    final_total = total + modifier
    if show_rolls:
        mr = enemy_magic_resist_bonus(target)
        mr_note = f" (MR +{mr}, effective L{effective_level})" if mr else ""
        log.append(
            f"Fireball: {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{effective_level}{mr_note}."
        )
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        kills = max(1, final_total - effective_level)
        for enemy in enemies:
            if kills <= 0:
                break
            if enemy.life <= 1 and enemy.category in {"vermin", "minions"} and enemy.life > 0:
                enemy.life = 0
                kills -= 1
                log.append(f"Fireball slays {enemy.name}.")
    else:
        if final_total >= effective_level:
            target.life -= 1
            log.append(f"Fireball hits {target.name} for 1 damage.")
            if target.life <= target.max_life // 2 and target.max_life > 1:
                target.level = max(1, target.level - 1)
        else:
            log.append(f"Fireball misses {target.name}.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_lightning(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
) -> SpellOutcome:
    if not enemies:
        log.append("There are no targets for Lightning.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = enemies[0]
    if "elemental" in target.tags and "lightning" in target.name.lower():
        log.append("Lightning has no effect on this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log = spell_hits(caster, target, show_rolls=show_rolls, label="Lightning")
    log.extend(hit_log)
    if not hit:
        log.append("Lightning misses.")
        return SpellOutcome(log, enemies, party)
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        target.life = 0
        log.append(f"Lightning slays {target.name}.")
    else:
        target.life -= 2
        log.append(f"Lightning hits {target.name} for 2 damage.")
        if target.life <= target.max_life // 2 and target.max_life > 1:
            target.level = max(1, target.level - 1)
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_sleep(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
) -> SpellOutcome:
    if not enemies:
        log.append("There are no targets for Sleep.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = enemies[0]
    if target.level >= 11 or any(tag in SLEEP_IMMUNE_TAGS for tag in target.tags):
        log.append("Sleep has no effect on this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log = spell_hits(caster, target, show_rolls=show_rolls, label="Sleep")
    log.extend(hit_log)
    if not hit:
        log.append("Sleep fails.")
        return SpellOutcome(log, enemies, party)
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        affected = roll_d6() + caster.level
        remaining = affected
        for enemy in enemies:
            if remaining <= 0:
                break
            if enemy.life <= 1 and enemy.category in {"vermin", "minions"}:
                enemy.life = 0
                remaining -= 1
        log.append(f"Sleep knocks out {affected - remaining} minor foes.")
    else:
        target.life = 0
        log.append(f"{target.name} falls asleep and is defeated.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_protection(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    target_character_id: str | None,
    log: list[str],
) -> SpellOutcome:
    target = _pick_target(party, target_character_id) or caster
    if "Protection" not in target.statuses:
        target.statuses.append("Protection")
    log.append(f"{target.name} gains +1 Defense until combat ends.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_blessing(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    target_character_id: str | None,
    log: list[str],
) -> SpellOutcome:
    target = _pick_target(party, target_character_id) or caster
    target.statuses = [item for item in target.statuses if item.lower() != "cursed"]
    log.append(f"Blessing removes curses and petrification effects from {target.name}.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_healing_prayer(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    target_character_id: str | None,
    log: list[str],
) -> SpellOutcome:
    target = _pick_target(party, target_character_id) or caster
    if target.current_life >= target.max_life:
        log.append(f"{target.name} is already at full Life.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target.current_life += 1
    log.append(f"Healing prayer restores 1 Life to {target.name}.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _pick_target(party: list[PartyMemberState], target_character_id: str | None) -> PartyMemberState | None:
    living = living_party(party)
    if not living:
        return None
    if target_character_id:
        return next((member for member in living if member.character_id == target_character_id), living[0])
    return living[0]
