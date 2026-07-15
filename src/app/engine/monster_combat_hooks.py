"""Fiendish Foes and template-driven combat hooks wired from monsters.json."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ..schemas import EnemyState, PartyMemberState, SessionState, TileState
from .class_combat import save_modifier
from .combat_modifiers import poison_save_succeeds
from .dice import roll_d6, roll_exploding_for_level, roll_formula
from .combat_modifiers import poison_save_succeeds
from .monster_template_effects import (
    DOPPELGANGER_MIMIC_PREFIX,
    chance_roll_succeeds,
    monster_effect_save,
    party_hcl,
    resolve_effect_level,
)

if TYPE_CHECKING:
    from .combat import CombatContext
    from .random_dungeon import RandomDungeonEngine


PINNED_BY_MANTLEBEAST = "Pinned by mantlebeast"
ENGULFED_BY_ACID_CUBE = "Engulfed by acid cube"
CONFUSED_DOPPELGANGER = "Confused (doppelganger)"
MANTLEBEAST_FREE_STRIKE = "Mantlebeast free strike"
POSSESSED_REVIVED_TAG = "possessed_revived_once"
BLADEMASTERS_ARRIVED_TAG = "blademasters_arrived"

# Legacy DATA_DIR monster stubs use shorter names than the PDF bestiary rows.
MONSTER_TEMPLATE_ALIASES: dict[str, str] = {
    "Dragon": "Young Dragon",
    "Troll": "Large Troll",
    "Chaos Champion": "Chaos Lord",
}


def default_treasure_rolls_for_category(category: str) -> int:
    if category in {"boss", "weird"}:
        return 2
    return 1


def _eligible_defeated_for_treasure(
    defeated: list[EnemyState],
    *,
    log: list[str],
) -> list[EnemyState]:
    from .experience import defeated_mixed_major_minor, major_foes_defeated

    if not defeated:
        return []
    if defeated_mixed_major_minor(defeated):
        log.append(
            "Minor foe treasure suppressed (EE p.180: do not roll treasure for minors bundled with a major)."
        )
        return major_foes_defeated(defeated)
    return defeated


def fd_treasure_roll_bonuses_from_defeated(
    defeated: list[EnemyState],
    *,
    lookup_template,
    log: list[str],
) -> list[int]:
    """One Forsaken Depths d10 bonus per treasure roll (treasure_bonus + treasure_modifier)."""
    eligible = _eligible_defeated_for_treasure(defeated, log=log)
    seen_names: set[str] = set()
    bonuses: list[int] = []
    for enemy in eligible:
        if enemy.name in seen_names:
            continue
        seen_names.add(enemy.name)
        template = lookup_template(enemy)
        if template and template.get("no_treasure"):
            continue
        rolls = fd_template_treasure_rolls(template)
        if rolls <= 0:
            continue
        per_roll = 0
        if template:
            per_roll = int(template.get("treasure_bonus", 0)) + int(template.get("treasure_modifier", 0))
        bonuses.extend([per_roll] * rolls)
    return bonuses


def fd_template_treasure_rolls(template: dict | None) -> int:
    """FD rows with treasure modifiers/bonuses imply one FD treasure roll unless overridden."""
    if not template or template.get("no_treasure"):
        return 0
    try:
        rolls = int(template.get("treasure_rolls", 0) or 0)
    except (TypeError, ValueError):
        rolls = 0
    if rolls <= 0 and (
        "treasure_modifier" in template or "treasure_bonus" in template
    ):
        return 1
    return max(0, rolls)


def treasure_roll_count_from_defeated(
    defeated: list[EnemyState],
    *,
    lookup_template,
    log: list[str],
    fd_ruleset: bool = False,
) -> int:
    """Sum explicit treasure_rolls once per defeated foe name; suppress minors when mixed major+minor."""
    eligible = _eligible_defeated_for_treasure(defeated, log=log)
    seen_names: set[str] = set()
    total_rolls = 0
    for enemy in eligible:
        if enemy.name in seen_names:
            continue
        seen_names.add(enemy.name)
        template = lookup_template(enemy)
        if template and template.get("no_treasure"):
            continue
        if fd_ruleset:
            rolls = fd_template_treasure_rolls(template)
        else:
            rolls = int(template.get("treasure_rolls", 0)) if template else 0
        if rolls <= 0:
            if fd_ruleset:
                continue
            rolls = default_treasure_rolls_for_category(enemy.category)
        total_rolls += rolls
    return total_rolls


def _living_party(party: list[PartyMemberState]) -> list[PartyMemberState]:
    return [member for member in party if member.current_life > 0]


def _has_rogue(party: list[PartyMemberState]) -> bool:
    return any(member.class_id.lower() == "rogue" and member.current_life > 0 for member in party)


def _member_has_heavy_armor(member: PartyMemberState) -> bool:
    return any("heavy armor" in item.lower() for item in member.inventory)


def _is_lurking_mantlebeast(enemy: EnemyState) -> bool:
    return enemy.name == "Lurking Mantlebeast" and enemy.life > 0


def tile_has_lurking_mantlebeast(tile: TileState) -> bool:
    return any(_is_lurking_mantlebeast(enemy) for enemy in tile.enemies)


def apply_mantlebeast_spot_on_entry(
    session: SessionState,
    tile: TileState,
    party: list[PartyMemberState],
    *,
    show_rolls: bool,
) -> bool:
    """Roll spot when entering a tile with a lurking mantlebeast. Returns True if spotted."""
    if not tile_has_lurking_mantlebeast(tile) or tile.mantlebeast_spotted:
        return tile.mantlebeast_spotted
    chance = "4-in-6" if _has_rogue(party) else "2-in-6"
    succeeded, rolled, need, sides = chance_roll_succeeds(chance)
    log = [f"Event: Lurking Mantlebeast spot check ({chance})."]
    if show_rolls:
        log.append(f"Spot roll: d{sides} = {rolled} (need {need} or less).")
    if succeeded:
        tile.mantlebeast_spotted = True
        log.append(
            "You spot the lurking mantlebeast clinging to the ceiling. "
            "Use Turn Back to retreat the way you came without fighting, or Start Combat if you wish to engage."
        )
    else:
        log.append("The lurking mantlebeast remains hidden on the ceiling.")
    session.log.extend(log)
    return tile.mantlebeast_spotted


def apply_mantlebeast_ambush_drop(
    session: SessionState,
    tile: TileState,
    party: list[PartyMemberState],
    *,
    show_rolls: bool,
) -> list[str]:
    if tile.mantlebeast_ambush_resolved or not tile_has_lurking_mantlebeast(tile):
        return []
    tile.mantlebeast_ambush_resolved = True
    log = ["Event: The lurking mantlebeast drops from the ceiling!"]
    save_level = 3
    for member in _living_party(party):
        modifier = save_modifier(member, poison=False, trap=False)
        if _member_has_heavy_armor(member):
            modifier -= 1
        if member.class_id.lower() in {"elf", "rogue"}:
            modifier += 1
        total, rolls = roll_exploding_for_level(member)
        final = total + modifier
        if show_rolls:
            log.append(
                f"Mantlebeast drop save: {member.name} rolls "
                f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final} vs L{save_level}."
            )
        passed = rolls[0] != 1 and final >= save_level
        if passed:
            if MANTLEBEAST_FREE_STRIKE not in member.statuses:
                member.statuses.append(MANTLEBEAST_FREE_STRIKE)
            log.append(f"Effect: {member.name} may attack the mantlebeast without defending this round.")
        else:
            if PINNED_BY_MANTLEBEAST not in member.statuses:
                member.statuses.append(PINNED_BY_MANTLEBEAST)
            log.append(
                f"Effect: {member.name} is pinned — cannot attack or flee (may cast spells), "
                "loses 1 Life per turn until the mantlebeast is slain."
            )
    return log


def member_cannot_attack(member: PartyMemberState) -> bool:
    lowered = {status.lower() for status in member.statuses}
    return PINNED_BY_MANTLEBEAST.lower() in lowered or ENGULFED_BY_ACID_CUBE.lower() in lowered or CONFUSED_DOPPELGANGER.lower() in lowered


def member_cannot_flee(member: PartyMemberState) -> bool:
    return PINNED_BY_MANTLEBEAST.lower() in {status.lower() for status in member.statuses}


def apply_per_turn_monster_effects(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    *,
    context: CombatContext,
    show_rolls: bool,
) -> list[str]:
    log: list[str] = []
    hcl = party_hcl(party)
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if not living_enemies:
        return log

    for enemy in living_enemies:
        for effect in enemy.per_turn_effects:
            effect_type = str(effect.get("type", "")).lower()
            if effect_type == "attract_wandering_after_turns":
                turns = max(1, int(effect.get("turns", 2)))
                if context.combat_round >= turns and not context.shrieking_fungi_wandering_due:
                    context.shrieking_fungi_wandering_due = True
                    log.append(
                        f"{enemy.name} have shrieked for {turns} turns; Wandering Monsters are drawn here "
                        "and surprise the party (Abyss p.49)."
                    )
                continue
            if effect_type == "confusion_save":
                mimicked_id = _doppelganger_mimic_id(enemy)
                for member in _living_party(party):
                    if mimicked_id and member.character_id == mimicked_id:
                        continue
                    save_level = int(effect.get("save_level", 4))
                    passed, save_log = monster_effect_save(
                        member,
                        save_level,
                        str(effect.get("save_type", "magic")),
                        effect,
                        label=f"{enemy.name} confusion",
                        show_rolls=show_rolls,
                        session=context.session,
                    )
                    log.extend(save_log)
                    if not passed:
                        if CONFUSED_DOPPELGANGER not in member.statuses:
                            member.statuses.append(CONFUSED_DOPPELGANGER)
                        log.append(f"Effect: {member.name} is too confused to attack this round.")
                    elif CONFUSED_DOPPELGANGER in member.statuses:
                        member.statuses.remove(CONFUSED_DOPPELGANGER)
            elif effect_type == "engulf":
                if enemy.name != "Acid Cube":
                    continue
                for member in _living_party(party):
                    save_level = int(effect.get("save_level_base", 2))
                    if member.character_id in context.melee_attacked_enemy_ids.get(enemy.id, set()):
                        save_level = int(effect.get("save_level_if_melee_last_turn", save_level))
                    passed, save_log = monster_effect_save(
                        member,
                        save_level,
                        "magic",
                        effect,
                        label=f"{enemy.name} engulf",
                        show_rolls=show_rolls,
                        session=context.session,
                    )
                    log.extend(save_log)
                    if passed:
                        if ENGULFED_BY_ACID_CUBE in member.statuses:
                            member.statuses.remove(ENGULFED_BY_ACID_CUBE)
                        continue
                    if ENGULFED_BY_ACID_CUBE not in member.statuses:
                        member.statuses.append(ENGULFED_BY_ACID_CUBE)
                    log.append(f"Effect: {member.name} is engulfed and cannot attack until the cube is slain.")

    if any(_is_lurking_mantlebeast(enemy) for enemy in living_enemies):
        for member in _living_party(party):
            if PINNED_BY_MANTLEBEAST not in member.statuses:
                continue
            member.current_life = max(0, member.current_life - 1)
            log.append(f"Effect: {member.name} loses 1 Life while pinned by the mantlebeast.")
            if member.current_life <= 0:
                log.append(f"{member.name} falls.")

    for member in _living_party(party):
        if MANTLEBEAST_FREE_STRIKE in member.statuses:
            member.statuses.remove(MANTLEBEAST_FREE_STRIKE)

    if not any(enemy.life > 0 and enemy.name == "Acid Cube" for enemy in living_enemies):
        for member in _living_party(party):
            if ENGULFED_BY_ACID_CUBE in member.statuses:
                member.statuses.remove(ENGULFED_BY_ACID_CUBE)
                log.append(f"Effect: {member.name} is freed as the acid cube is gone.")

    context.melee_attacked_enemy_ids.clear()
    return log


def _doppelganger_mimic_id(enemy: EnemyState) -> str | None:
    for tag in enemy.tags:
        if str(tag).startswith(DOPPELGANGER_MIMIC_PREFIX):
            return str(tag).split(":", 1)[-1].strip()
    return None


def record_pc_damage(context: CombatContext, damage: int, *, member: PartyMemberState | None = None) -> None:
    if damage > 0:
        context.pc_damage_this_round += damage
        if context.session is not None and member is not None:
            from .party_life import record_character_life_loss

            record_character_life_loss(context.session, member.character_id)


def queue_skeleton_spawns_from_damage(context: CombatContext, enemies: list[EnemyState], damage: int) -> None:
    if damage <= 0:
        return
    if not any(enemy.life > 0 and enemy.name == "Skeletal Demon" for enemy in enemies):
        return
    context.pending_skeleton_spawns += damage


def spawn_skeleton_reinforcements(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    enemies: list[EnemyState],
    count: int,
    *,
    show_rolls: bool,
) -> list[str]:
    if count <= 0:
        return []
    hcl = party_hcl(session.party)
    spawned = engine._spawn_from_template_name(
        session,
        table_key="fiendish_foes_vermin",
        template_name="Armored Skeletons",
        count=count,
        hcl=hcl,
        category="vermin",
    )
    if spawned:
        tile.enemies.extend(spawned)
        enemies.extend(spawned)
        return [
            f"Skeletal Demon reinforcement: {len(spawned)} Armored Skeleton(s) join the fight "
            f"({count} Life lost by PCs this round)."
        ]
    return []


def try_rattleblade_summon(
    enemy: EnemyState,
    *,
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    hcl: int,
    show_rolls: bool,
) -> list[str]:
    if BLADEMASTERS_ARRIVED_TAG in enemy.tags or enemy.name != "Hobgoblin Leader":
        return []
    for attack in enemy.special_attacks:
        if str(attack.get("type", "")).lower() != "rattleblade_summon":
            continue
        chance = str(attack.get("chance", "3-in-6"))
        succeeded, rolled, need, sides = chance_roll_succeeds(chance)
        log = [f"Event: {enemy.name} rattleblade summon ({chance})."]
        if show_rolls:
            log.append(f"Rattleblade roll: d{sides} = {rolled} (need {need} or less).")
        if not succeeded:
            log.append("No Hobgoblin Blademasters arrive.")
            return log
        count = max(1, roll_formula("2d3+2"))
        spawned = engine._spawn_from_template_name(
            session,
            table_key=str(attack.get("summon_table", "fiendish_foes_minions")),
            template_name=str(attack.get("summon_name", "Hobgoblin Blademasters")),
            count=count,
            hcl=hcl,
            category="minions",
        )
        enemy.tags.append(BLADEMASTERS_ARRIVED_TAG)
        if context := getattr(engine, "_active_combat_context", None):
            context.reinforcement_enemies.extend(spawned)
        tile.enemies.extend(spawned)
        log.append(f"Hobgoblin Blademasters arrive: {len(spawned)} join the fight.")
        return log
    return []


def on_enemy_killed_by_pc(
    enemy: EnemyState,
    killer: PartyMemberState | None,
    *,
    context: CombatContext,
    show_rolls: bool,
    template: dict | None,
) -> list[str]:
    log: list[str] = []
    if template is None:
        return log
    for rule in template.get("special_rules", []):
        rule_type = str(rule.get("type", "")).lower()
        if rule_type == "death_burst_poison" and killer is not None:
            if context.last_attack_was_ranged.get(killer.character_id):
                log.append(f"{killer.name} used a ranged attack — giant toad death-burst poison is avoided.")
                continue
            save_level = resolve_effect_level(rule.get("save_level"), hcl=enemy.level, default=enemy.level)
            saved, save_log = poison_save_succeeds(
                killer,
                save_level,
                show_rolls=show_rolls,
                explain_math=False,
                session=context.session,
            )
            log.extend(save_log)
            if saved:
                continue
            killer.current_life = max(0, killer.current_life - int(rule.get("damage", 1)))
            log.append(f"Effect: {killer.name} takes 1 Life from the slain giant toad's poison burst.")
            if killer.current_life <= 0:
                log.append(f"{killer.name} falls.")
        elif rule_type == "hard_to_kill" and POSSESSED_REVIVED_TAG not in enemy.tags:
            roll = roll_d6()
            threshold = int(rule.get("revival_threshold", 3))
            if show_rolls:
                log.append(f"Possessed dwarf revival roll: d6 = {roll} (need {threshold}+ to rise again).")
            if roll >= threshold:
                enemy.life = 1
                enemy.tags.append(POSSESSED_REVIVED_TAG)
                log.append(f"Effect: {enemy.name} rises again to attack next turn!")
    return log


def check_doppelganger_flee(enemies: list[EnemyState], party: list[PartyMemberState], log: list[str]) -> None:
    for enemy in enemies:
        if enemy.life <= 0 or enemy.name != "Doppelganger":
            continue
        mimic_id = _doppelganger_mimic_id(enemy)
        if not mimic_id:
            continue
        mimic = next((member for member in party if member.character_id == mimic_id), None)
        if mimic is not None and mimic.current_life <= 0:
            enemy.life = 0
            log.append("The doppelganger flees as its mimicked form falls.")


def defeated_has_free_slaves_effect(defeated: list[EnemyState]) -> bool:
    return any(enemy.name == "Fiendish Chaos Lord" for enemy in defeated)


def apply_free_slaves_choice(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    accept: bool,
    show_rolls: bool,
) -> None:
    if session.pending_free_slaves_tile_id is None:
        session.log.append("There are no captured slaves to free here.")
        return
    tile_id = session.pending_free_slaves_tile_id
    session.pending_free_slaves_tile_id = None
    if not accept:
        session.log.append("The party leaves the Fiendish Chaos Lord's slaves captive.")
        return
    holder = engine._default_clue_holder(session)
    if holder is None:
        session.log.append("No hero is available to record the freed slaves' clue.")
        return
    holder.clues += 1
    engine._sync_clue_total(session)
    session.log.append(
        f"The party frees the chaos lord's slaves and gains 1 Clue ({holder.name} now carries {holder.clues}). "
        "Roll for Wandering Monsters!"
    )
    tile = engine._tile_by_id(session, tile_id)
    if tile is not None:
        engine._spawn_wandering_monsters(session, tile, show_rolls=show_rolls)
