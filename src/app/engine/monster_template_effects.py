from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..schemas import EnemyState, PartyMemberState, SessionState
from .class_combat import save_modifier
from .class_profiles import max_life_for_level
from .combat_modifiers import apply_poison_status, poison_save_succeeds
from .dice import roll_d6, roll_d3, roll_exploding_for_level

if TYPE_CHECKING:
    from .combat import CombatContext

LIFE_DRAIN_NOT_HIT_TAG = "life_drain_not_hit"
PETRIFIED_STATUS = "Petrified"
ASLEEP_STATUS = "Asleep"
ATTACK_PENALTY_POISON_STATUS = "Attack penalty (poison) -1"
NO_EXPLODING_ATTACKS_STATUS = "No exploding attacks (fear)"
ATTACK_PENALTY_MAGIC_STATUS = "Attack penalty (magic) -1"
TAR_COVERED_STATUS = "Tar covered"
TAR_IN_EYES_STATUS = "Tar in eyes -1"
SLIME_DISEASE_STATUS = "Slime disease"
DOPPELGANGER_MIMIC_PREFIX = "Doppelganger mimics:"
DISEASE_PENDING_PREFIX = "Disease pending:"
EVIL_EYE_DEFENSE_STATUS = "Defense penalty (evil eye) -1"
STIRGE_BLOOD_DRAIN_STATUS = "Stirge blood drain"
ANT_PEOPLE_MARKER_STATUS = "Ant People chemical marker"
FIRE_BREATH_USED_TAG = "fire_breath_used"
RANDOM_POWER_TAG_PREFIX = "random_power:"


def template_combat_tags(template: dict) -> list[str]:
    tags: list[str] = []
    for effect in template.get("per_turn_effects", []):
        if str(effect.get("type", "")).lower() != "life_drain":
            continue
        if str(effect.get("trigger", "")).lower() == "not_hit_this_turn":
            tags.append(LIFE_DRAIN_NOT_HIT_TAG)
    return tags


def template_on_hit_effects(template: dict) -> list[dict[str, Any]]:
    return [dict(effect) for effect in template.get("on_hit_effects", [])]


def template_encounter_start_effects(template: dict) -> list[dict[str, Any]]:
    return [dict(effect) for effect in template.get("encounter_start_effects", [])]


def template_per_turn_effects(template: dict) -> list[dict[str, Any]]:
    return [dict(effect) for effect in template.get("per_turn_effects", [])]


def template_special_attacks(template: dict) -> list[dict[str, Any]]:
    return [dict(effect) for effect in template.get("special_attacks", [])]


def enemy_has_life_drain_not_hit(enemy: EnemyState) -> bool:
    return LIFE_DRAIN_NOT_HIT_TAG in {tag.lower() for tag in enemy.tags}


def mark_enemy_hit(context: CombatContext, enemy_id: str) -> None:
    context.enemies_hit_this_round.add(enemy_id)


def party_hcl(party: list[PartyMemberState]) -> int:
    living = [member for member in party if member.current_life > 0]
    if not living:
        living = party
    return max(member.level for member in living)


def resolve_effect_level(value: int | str | None, *, hcl: int, default: int = 1) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    text = str(value).strip().upper().replace(" ", "")
    if text.startswith("HCL+"):
        return hcl + int(text[4:])
    if text.startswith("L") and text[1:].isdigit():
        return int(text[1:])
    if text.isdigit():
        return int(text)
    return default


def parse_chance(chance: str) -> tuple[int, int]:
    text = chance.strip().lower().replace(" ", "")
    if "-in-" in text:
        need, sides = text.split("-in-", 1)
        return int(need), int(sides)
    return 1, 6


def chance_roll_succeeds(chance: str, *, roll: int | None = None) -> tuple[bool, int, int, int]:
    need, sides = parse_chance(chance)
    rolled = roll if roll is not None else roll_d6()
    return rolled <= need, rolled, need, sides


def _effect_save_modifier(member: PartyMemberState, effect: dict[str, Any]) -> int:
    bonus = 0
    class_id = member.class_id.lower()
    modifiers = effect.get("save_modifier") or {}
    if isinstance(modifiers, dict):
        for key, value in modifiers.items():
            key_lower = str(key).lower()
            if key_lower == "all":
                text = str(value).replace(" ", "").lower()
                if text in {"+1/2l", "1/2l", "half_l"}:
                    bonus += member.level // 2
                elif text.lstrip("+").isdigit():
                    bonus += int(text)
                continue
            if key_lower in class_id or class_id in key_lower:
                text = str(value).replace(" ", "").lower()
                if text in {"l", "+l"}:
                    bonus += member.level
                elif text in {"+1/2l", "1/2l", "half_l"}:
                    bonus += member.level // 2
                elif text.lstrip("+").isdigit():
                    bonus += int(text)
    if effect.get("halfling_reroll") and class_id == "halfling":
        bonus += 0
    text_modifier = effect.get("save_modifier_text")
    if isinstance(text_modifier, str) and "+1/2" in text_modifier.lower():
        bonus += member.level // 2
    return bonus


def _immune_to_effect(member: PartyMemberState, effect: dict[str, Any]) -> bool:
    class_id = member.class_id.lower()
    for token in effect.get("immune_classes", []):
        if str(token).lower() in class_id:
            return True
    return False


def monster_effect_save(
    member: PartyMemberState,
    save_level: int,
    save_type: str,
    effect: dict[str, Any],
    *,
    label: str,
    show_rolls: bool,
    explain_math: bool = False,
    session: SessionState | None = None,
) -> tuple[bool, list[str]]:
    """Return True when the PC passes the save."""
    log: list[str] = []
    save_kind = str(save_type or "magic").lower()
    poison = save_kind == "poison" or save_kind == "trap_poison"
    total, rolls = roll_exploding_for_level(member)
    tile_enemies: list[EnemyState] = []
    if session is not None and session.map_state and session.map_state.current_tile_id:
        tile = next(
            (item for item in session.map_state.tiles if item.id == session.map_state.current_tile_id),
            None,
        )
        if tile is not None:
            tile_enemies = [enemy for enemy in tile.enemies if enemy.life > 0]
    modifier = save_modifier(
        member,
        poison=poison,
        trap=save_kind == "trap",
        save_label=label,
        enemies=tile_enemies,
        session=session,
    ) + _effect_save_modifier(member, effect)
    if save_kind == "magic" and member.class_id.lower() in {"wizard", "elf"}:
        modifier += member.level
    final_total = total + modifier
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} "
            f"= {final_total} vs L{save_level}."
        )
    if explain_math:
        log.append(f"{label} math: need total >= {save_level} (natural 1 fails).")
    if rolls[0] == 1:
        passed = False
    else:
        passed = final_total >= save_level
    if (
        not passed
        and effect.get("halfling_reroll")
        and member.class_id.lower() == "halfling"
    ):
        total, rolls = roll_exploding_for_level(member)
        final_total = total + modifier
        if show_rolls:
            log.append(
                f"{member.name} rerolls the halfling save: {' + '.join(str(value) for value in rolls)} "
                f"+ {modifier} = {final_total} vs L{save_level}."
            )
        passed = rolls[0] != 1 and final_total >= save_level
    if passed:
        log.append(f"{member.name} passes the {label}.")
        from .milestones import record_gaze_save

        log.extend(record_gaze_save(member, label=label))
    else:
        log.append(f"{member.name} fails the {label}.")
    return passed, log


def apply_member_level_loss(
    member: PartyMemberState,
    amount: int = 1,
    *,
    source: str = "level drain",
) -> list[str]:
    if amount <= 0:
        return []
    if "level drain" in source.lower():
        old_level = member.level
        old_max_life = member.max_life
        member.level = max(0, member.level - amount)
        member.max_life = max(0, member.max_life - amount)
        member.current_life = max(0, min(member.current_life - amount, member.max_life))
        log = [
            f"{member.name} fails the save — Level drops from L{old_level} to L{member.level} "
            f"and max Life drops from {old_max_life} to {member.max_life} due to {source}."
        ]
        if member.level <= 0 or member.current_life <= 0:
            from .abyss_afflictions import mark_vampire_rise_pending

            member.current_life = 0
            mark_vampire_rise_pending(member)
            log.append(
                f"{member.name} is slain by vampire level drain and will rise as a vampire unless the sire is destroyed."
            )
        return log
    if member.level <= 1:
        return [f"{member.name} is already at minimum Level and cannot lose another Level to {source}."]
    old_level = member.level
    member.level = max(1, member.level - amount)
    member.max_life = max_life_for_level(member.class_id, member.level)
    if member.current_life > member.max_life:
        member.current_life = member.max_life
    return [
        f"{member.name} fails the save — Level drops from L{old_level} to L{member.level} "
        f"({member.current_life}/{member.max_life} Life) due to {source}."
    ]


def _add_status(member: PartyMemberState, status: str) -> None:
    if status not in member.statuses:
        member.statuses.append(status)


def _living_targets(party: list[PartyMemberState], target: str) -> list[PartyMemberState]:
    key = str(target or "hit_pcs").lower()
    if key in {"all_pcs", "all_living_pcs"}:
        return [member for member in party if member.current_life > 0]
    return [member for member in party if member.current_life > 0]


def _resolve_save_damage_encounter_effect(
    enemy: EnemyState,
    effect: dict[str, Any],
    party: list[PartyMemberState],
    *,
    hcl: int,
    label: str,
    show_rolls: bool,
    session: SessionState | None,
) -> list[str]:
    log: list[str] = []
    save_level = resolve_effect_level(effect.get("save_level") or effect.get("level"), hcl=hcl, default=enemy.level)
    save_type = str(effect.get("save_type", "magic"))
    damage = int(effect.get("damage", 1))
    effect_name = str(effect.get("type", "effect")).replace("_", " ")
    log.append(f"Event: {enemy.name} — {effect_name}.")
    for member in _living_targets(party, str(effect.get("target", "all_pcs"))):
        if _immune_to_effect(member, effect):
            log.append(f"{member.name} is immune to {enemy.name}'s {effect_name}.")
            continue
        passed, save_log = monster_effect_save(
            member,
            save_level,
            save_type,
            effect,
            label=label,
            show_rolls=show_rolls,
            session=session,
        )
        log.extend(save_log)
        if passed:
            continue
        if str(effect.get("effect", "")).lower() == "sleep":
            _add_status(member, ASLEEP_STATUS)
            log.append(f"Effect: {member.name} falls asleep.")
            continue
        if str(effect.get("effect", "")).lower() in {"turned_to_stone", "petrified"}:
            _add_status(member, PETRIFIED_STATUS)
            log.append(f"Effect: {member.name} is turned to stone.")
            if session is not None:
                from .hirelings import notify_hireling_morale_casualty

                log.extend(
                    notify_hireling_morale_casualty(
                        session,
                        reason=f"{member.name} was turned to stone",
                    )
                )
            continue
        if damage > 0:
            member.current_life = max(0, member.current_life - damage)
            log.append(f"Effect: {member.name} loses {damage} Life ({member.current_life}/{member.max_life}).")
            if member.current_life <= 0:
                log.append(f"{member.name} falls.")
    return log


def apply_pre_party_turn_effects(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    session: SessionState,
    *,
    show_rolls: bool,
) -> list[str]:
    """Resolve template effects explicitly timed before any party action each round."""
    log: list[str] = []
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        for effect in enemy.per_turn_effects:
            if str(effect.get("timing", "")).lower() != "before_party_actions":
                continue
            if str(effect.get("type", "")).lower() != "save_damage_madness":
                continue
            label = str(effect.get("label") or f"{enemy.name} effect")
            save_level = resolve_effect_level(effect.get("save_level"), hcl=party_hcl(party), default=enemy.level)
            save_type = str(effect.get("save_type") or "magic")
            damage = max(0, int(effect.get("damage", 0)))
            madness = max(0, int(effect.get("madness", 0)))
            log.append(f"Event: {enemy.name} acts before the party can attack.")
            for member in _living_targets(party, str(effect.get("target", "all_pcs"))):
                passed, save_log = monster_effect_save(
                    member,
                    save_level,
                    save_type,
                    effect,
                    label=label,
                    show_rolls=show_rolls,
                    session=session,
                )
                log.extend(save_log)
                if passed:
                    continue
                if damage:
                    member.current_life = max(0, member.current_life - damage)
                    log.append(f"Effect: {member.name} loses {damage} Life ({member.current_life}/{member.max_life}).")
                    if member.current_life <= 0:
                        log.append(f"{member.name} falls.")
                for _ in range(madness):
                    from .madness import apply_madness_gain

                    log.extend(
                        apply_madness_gain(
                            session,
                            member,
                            source=enemy.name,
                            show_rolls=show_rolls,
                            allow_damage_choice=False,
                        )
                    )
    return log


def _resolve_encounter_start_effect(
    enemy: EnemyState,
    effect: dict[str, Any],
    party: list[PartyMemberState],
    session: SessionState,
    *,
    hcl: int,
    show_rolls: bool,
) -> list[str]:
    effect_type = str(effect.get("type", "")).lower()
    if effect_type == "chance_status":
        chance = str(effect.get("chance", "1-in-6"))
        status = str(effect.get("status", "")).strip()
        if not status:
            return []
        label = str(effect.get("label") or status)
        log = [f"Event: {enemy.name} uses {label} before combat."]
        for member in _living_targets(party, str(effect.get("target", "all_pcs"))):
            if status in member.statuses:
                log.append(f"{member.name} is already marked; {enemy.name} does not spray them again.")
                continue
            succeeded, rolled, need, sides = chance_roll_succeeds(chance)
            if show_rolls:
                log.append(
                    f"{label}: {member.name} rolls d{sides} = {rolled} "
                    f"(marked on {need} or less)."
                )
            if succeeded:
                _add_status(member, status)
                log.append(
                    f"Effect: {member.name} is marked: -1 Defense in this and later combats against ant people. "
                    "Blessing or immersion in water removes the marker."
                )
            else:
                log.append(f"{member.name} avoids the {label}.")
        return log
    if effect_type == "extinguish_lanterns":
        chance = str(effect.get("chance", "2-in-6"))
        succeeded, rolled, need, sides = chance_roll_succeeds(chance)
        log = [f"Event: {enemy.name} may extinguish lanterns ({chance})."]
        if show_rolls:
            log.append(f"Lantern extinguish roll: d{sides} = {rolled} (need {need} or less).")
        if succeeded:
            session.combat_lanterns_extinguished = True
            log.append("All lanterns are extinguished until the end of this fight.")
        else:
            log.append("The party's lanterns stay lit.")
        return log
    if effect_type in {"death_gaze", "poison_burst", "save_damage"}:
        return _resolve_save_damage_encounter_effect(
            enemy,
            effect,
            party,
            hcl=hcl,
            label=str(effect.get("label") or effect_type.replace("_", " ").title()),
            show_rolls=show_rolls,
            session=session,
        )
    if effect_type == "petrification_gaze":
        return _resolve_save_damage_encounter_effect(
            enemy,
            effect,
            party,
            hcl=hcl,
            label="Petrification gaze",
            show_rolls=show_rolls,
            session=session,
        )
    if effect_type == "battle_cry":
        from .heroic_skill_effects import resolve_fear_save

        log = [f"Event: {enemy.name} utters a battle cry."]
        save_level = resolve_effect_level(effect.get("save_level"), hcl=hcl, default=enemy.level)
        for member in _living_targets(party, str(effect.get("target", "all_pcs"))):
            if _immune_to_effect(member, effect):
                log.append(f"{member.name} is immune to the battle cry.")
                continue
            if session is None:
                passed, save_log = monster_effect_save(
                    member,
                    save_level,
                    str(effect.get("save_type", "fear")),
                    effect,
                    label="Fear save",
                    show_rolls=show_rolls,
                    session=session,
                )
            else:
                passed, save_log = resolve_fear_save(
                    session,
                    member,
                    save_level,
                    party=party,
                    show_rolls=show_rolls,
                    label="fear",
                )
            log.extend(save_log)
            if not passed:
                _add_status(member, NO_EXPLODING_ATTACKS_STATUS)
                log.append(f"Effect: {member.name} cannot explode Attack rolls until the encounter ends.")
        return log
    if effect_type == "sleep_song":
        effect_copy = dict(effect)
        effect_copy.setdefault("effect", "sleep")
        return _resolve_save_damage_encounter_effect(
            enemy,
            effect_copy,
            party,
            hcl=hcl,
            label="Sleep song",
            show_rolls=show_rolls,
            session=session,
        )
    if effect_type == "charge":
        bonus = int(effect.get("level_delta_bonus", 0))
        if bonus:
            enemy.tags = [tag for tag in enemy.tags if not str(tag).startswith("charge_level_bonus:")]
            enemy.tags.append(f"charge_level_bonus:{bonus}")
            return [f"Event: {enemy.name} charges: +{bonus} effective Level in round 1."]
        return [f"Event: {enemy.name} charges."]
    if effect_type == "shapeshift":
        targets = _living_targets(party, str(effect.get("target", "random_pc")))
        if not targets:
            return [f"Event: {enemy.name} shifts form, but there is no living target to mimic."]
        target = targets[(roll_d6() - 1) % len(targets)]
        enemy.tags = [tag for tag in enemy.tags if not str(tag).startswith(DOPPELGANGER_MIMIC_PREFIX)]
        enemy.tags.append(f"{DOPPELGANGER_MIMIC_PREFIX} {target.character_id}")
        return [f"Event: {enemy.name} shapeshifts into {target.name}'s form."]
    if effect_type == "surprise":
        chance = str(effect.get("chance", "2-in-6"))
        succeeded, rolled, need, sides = chance_roll_succeeds(chance)
        log = [f"Event: {enemy.name} attempts surprise ({chance})."]
        if show_rolls:
            log.append(f"Surprise roll: d{sides} = {rolled} (need {need} or less).")
        if succeeded:
            session.party_surprised = True
            session.foes_strike_first = True
            log.append("The party is surprised by the encounter-start effect.")
        else:
            log.append("The party avoids surprise from the encounter-start effect.")
        return log
    if effect_type == "tar_spit":
        log: list[str] = [f"Event: {enemy.name} spits tar."]
        save_level = resolve_effect_level(effect.get("level") or effect.get("save_level"), hcl=hcl, default=enemy.level)
        save_type = str(effect.get("save_type", "defense"))
        for member in _living_targets(party, str(effect.get("target", "all_pcs"))):
            passed, save_log = monster_effect_save(
                member,
                save_level,
                save_type,
                effect,
                label="Tar spit save",
                show_rolls=show_rolls,
                session=session,
            )
            log.extend(save_log)
            if passed:
                continue
            _add_status(member, TAR_COVERED_STATUS)
            log.append(f"Effect: {member.name} is covered in tar.")
        return log
    if effect_type == "preset_trap":
        if any("wandering_spawn" in {tag.lower() for tag in enemy.tags} for enemy in [enemy]):
            return [f"Event: {enemy.name}'s preset trap is not set for wandering encounters."]
        trap_key = str(effect.get("trap_type", "bear_trap"))
        trap_level = resolve_effect_level(effect.get("trap_level"), hcl=hcl, default=4)
        log: list[str] = [f"Event: {enemy.name} — preset {trap_key.replace('_', ' ')} (L{trap_level}) before the fight."]
        if effect.get("rogue_can_spot"):
            spotted, spot_log = _rogue_spots_preset_trap(party, trap_level, show_rolls=show_rolls)
            log.extend(spot_log)
            if spotted:
                return log
        lead = sorted(
            [member for member in party if member.current_life > 0],
            key=lambda member: member.marching_order,
        )
        if not lead:
            return log
        target = lead[0]
        from .dungeon_table_roller import _save_trap_hit

        log.extend(
            _save_trap_hit(
                target,
                trap_level,
                trap_key.replace("_", " "),
                damage=1,
                show_rolls=show_rolls,
                explain_math=False,
                bear_trap=(trap_key == "bear_trap"),
                trap_key=trap_key,
            )
        )
        return log
    description = str(effect.get("description", effect_type))
    return [f"Event: {enemy.name} — {description} (automated hook pending for {effect_type})."]


def _rogue_spots_preset_trap(
    party: list[PartyMemberState],
    trap_level: int,
    *,
    show_rolls: bool,
) -> tuple[bool, list[str]]:
    log: list[str] = []
    for member in party:
        if member.current_life <= 0 or member.class_id.lower() != "rogue":
            continue
        total, rolls = roll_exploding_for_level(member)
        modifier = member.level
        final = total + modifier
        if show_rolls:
            log.append(
                f"{member.name} searches for traps: {' + '.join(str(value) for value in rolls)} + {modifier} "
                f"= {final} vs L{trap_level}."
            )
        if rolls[0] != 1 and final >= trap_level:
            return True, log
    return False, log


def _pick_random_power(powers_spec: dict, roll: int) -> dict | None:
    for entry in powers_spec.get("powers", []):
        roll_text = str(entry.get("roll", ""))
        if "-" in roll_text:
            low, high = roll_text.split("-", 1)
            if int(low) <= roll <= int(high):
                return entry
        elif roll_text.isdigit() and int(roll_text) == roll:
            return entry
    return None


def roll_random_power_tag(template: dict) -> str | None:
    spec = template.get("random_powers")
    if not spec:
        return None
    roll = roll_d6()
    power = _pick_random_power(spec, roll)
    if power is None:
        return None
    return f"{RANDOM_POWER_TAG_PREFIX}{power.get('key', 'unknown')}"


def apply_random_power_effects(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    log: list[str] = []
    hcl = party_hcl(party)
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        power_key = None
        for tag in enemy.tags:
            if str(tag).startswith(RANDOM_POWER_TAG_PREFIX):
                power_key = str(tag).split(":", 1)[1]
                break
        if not power_key:
            continue
        if power_key == "evil_eye":
            log.append(f"Event: {enemy.name} uses evil eye — all PCs Save vs. L4 magic or suffer -1 Defense until it is slain.")
            for member in _living_targets(party, "all_pcs"):
                passed, save_log = monster_effect_save(
                    member,
                    4,
                    "magic",
                    {},
                    label=f"{enemy.name} evil eye",
                    show_rolls=show_rolls,
                    session=session,
                )
                log.extend(save_log)
                if not passed:
                    _add_status(member, EVIL_EYE_DEFENSE_STATUS)
                    log.append(f"Effect: {member.name} suffers -1 on all Defense rolls until {enemy.name} is slain.")
            continue
        if power_key == "energy_drain":
            enemy.on_hit_effects.append(
                {
                    "type": "level_drain",
                    "save_level": 4,
                    "save_type": "magic",
                    "levels_lost": 1,
                    "description": "Any PC hit must Save vs. L4 magic or lose 1 level.",
                }
            )
            log.append(f"Event: {enemy.name} wields energy drain — hits may drain 1 Level (Save vs. L4 magic).")
            continue
        if power_key == "hellfire_blast":
            effect = {
                "type": "hellfire_blast",
                "save_level": 5,
                "save_type": "magic",
                "damage": 2,
                "save_modifier": {"cleric": "+1/2L"},
            }
            log.extend(
                _resolve_save_damage_encounter_effect(
                    enemy,
                    effect,
                    party,
                    hcl=hcl,
                    label=f"{enemy.name} hellfire blast",
                    show_rolls=show_rolls,
                    session=session,
                )
            )
    return log


def _parse_damage_value(value: int | str) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text == "d3":
        return roll_d3()
    if text.isdigit():
        return int(text)
    return 1


def apply_first_turn_special_attacks(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    log: list[str] = []
    hcl = party_hcl(party)
    for enemy in enemies:
        if enemy.life <= 0 or FIRE_BREATH_USED_TAG in enemy.tags:
            continue
        for attack in enemy.special_attacks:
            if str(attack.get("timing", "")).lower() != "first_turn":
                continue
            attack_type = str(attack.get("type", "")).lower()
            if attack_type != "fire_breath":
                continue
            save_level = int(attack.get("save_level", enemy.level))
            damage_spec = attack.get("damage", 1)
            log.append(f"Event: {enemy.name} breathes fire on its first turn.")
            for member in _living_targets(party, "all_pcs"):
                total, rolls = roll_exploding_for_level(member)
                half_level = member.level // 2
                modifier = save_modifier(
                    member,
                    poison=False,
                    trap=False,
                    save_label="fire breath",
                    session=session,
                ) + half_level
                final = total + modifier
                if show_rolls:
                    log.append(
                        f"{enemy.name} fire breath: {member.name} rolls "
                        f"{' + '.join(str(value) for value in rolls)} + {modifier} (+½L) = {final} vs L{save_level}."
                    )
                passed = rolls[0] != 1 and final >= save_level
                if passed:
                    log.append(f"{member.name} resists the fire breath.")
                    continue
                damage = _parse_damage_value(damage_spec)
                member.current_life = max(0, member.current_life - damage)
                log.append(f"Effect: {member.name} takes {damage} Life from {enemy.name}'s fire breath.")
                if member.current_life <= 0:
                    log.append(f"{member.name} falls.")
            enemy.tags.append(FIRE_BREATH_USED_TAG)
    return log


def mark_stirge_blood_drain(target: PartyMemberState, enemy: EnemyState) -> None:
    if enemy.life <= 0 or "stirge" not in enemy.name.lower():
        return
    if any(str(effect.get("type", "")).lower() == "blood_drain" for effect in enemy.per_turn_effects):
        if STIRGE_BLOOD_DRAIN_STATUS not in target.statuses:
            _add_status(target, STIRGE_BLOOD_DRAIN_STATUS)


def apply_blood_drain_after_foe_turn(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    *,
    show_rolls: bool = True,
) -> list[str]:
    log: list[str] = []
    stirges_alive = any(
        enemy.life > 0
        and "stirge" in enemy.name.lower()
        and any(str(effect.get("type", "")).lower() == "blood_drain" for effect in enemy.per_turn_effects)
        for enemy in enemies
    )
    if not stirges_alive:
        return log
    drained: list[str] = []
    for member in party:
        if member.current_life <= 0 or STIRGE_BLOOD_DRAIN_STATUS not in member.statuses:
            continue
        member.current_life = max(0, member.current_life - 1)
        drained.append(member.name)
        if member.current_life <= 0:
            log.append(f"{member.name} falls to stirge blood drain.")
    if drained:
        names = ", ".join(drained)
        log.append(
            f"Stirge blood drain: {names} "
            f"{'each lose' if len(drained) > 1 else 'loses'} 1 Life (proboscis drain)."
        )
    return log


def apply_encounter_start_effects(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    if session.monster_encounter_start_applied:
        return []
    log: list[str] = []
    hcl = party_hcl(party)
    log.extend(apply_random_power_effects(enemies, party, session, show_rolls=show_rolls))
    applied: set[tuple[str, str]] = set()
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        for effect in enemy.encounter_start_effects:
            key = (enemy.name, str(effect.get("type", "")))
            if key in applied:
                continue
            applied.add(key)
            log.extend(
                _resolve_encounter_start_effect(
                    enemy,
                    effect,
                    party,
                    session,
                    hcl=hcl,
                    show_rolls=show_rolls,
                )
            )
    session.monster_encounter_start_applied = True
    return log


def _resolve_on_hit_poison(
    enemy: EnemyState,
    target: PartyMemberState,
    effect: dict[str, Any],
    *,
    show_rolls: bool,
    explain_math: bool,
    session: SessionState | None,
) -> list[str]:
    if _immune_to_effect(target, effect):
        return [f"{target.name} is immune to {enemy.name}'s poison."]
    save_level = resolve_effect_level(effect.get("save_level"), hcl=enemy.level, default=enemy.level)
    effect_key = str(effect.get("effect", "damage")).lower()
    if effect_key == "attack_penalty":
        passed, log = monster_effect_save(
            target,
            save_level,
            str(effect.get("save_type", "poison")),
            effect,
            label=f"{enemy.name} poison",
            show_rolls=show_rolls,
            explain_math=explain_math,
            session=session,
        )
        if passed:
            return log
        if ATTACK_PENALTY_POISON_STATUS not in target.statuses:
            _add_status(target, ATTACK_PENALTY_POISON_STATUS)
        log.append(f"Effect: {target.name} suffers -1 Attack rolls until the encounter ends.")
        return log
    saved, log = poison_save_succeeds(
        target,
        save_level,
        show_rolls=show_rolls,
        explain_math=explain_math,
        session=session,
    )
    if saved:
        return log
    damage = int(effect.get("damage", 1))
    if damage > 0:
        target.current_life = max(0, target.current_life - damage)
        log.append(f"Effect: {target.name} takes {damage} extra damage from poison.")
        if target.current_life <= 0:
            log.append(f"{target.name} falls.")
            return log
    before = set(target.statuses)
    apply_poison_status(target, save_level)
    if set(target.statuses) != before:
        log.append(f"Effect: {target.name} is poisoned (L{save_level}).")
    return log


def _resolve_on_hit_level_drain(
    enemy: EnemyState,
    target: PartyMemberState,
    effect: dict[str, Any],
    *,
    show_rolls: bool,
    explain_math: bool,
    session: SessionState | None,
) -> list[str]:
    save_level = resolve_effect_level(effect.get("save_level"), hcl=enemy.level, default=4)
    passed, log = monster_effect_save(
        target,
        save_level,
        str(effect.get("save_type", "magic")),
        effect,
        label=f"{enemy.name} level drain",
        show_rolls=show_rolls,
        explain_math=explain_math,
        session=session,
    )
    if passed:
        return log
    if session is not None:
        from .alchemist_potions import alchemist_blocks_vampire_level_drain

        if alchemist_blocks_vampire_level_drain(target, enemy):
            log.append(f"{target.name}'s Garlic Poultice blocks {enemy.name}'s level drain.")
            return log
    levels = int(effect.get("levels_lost", 1))
    log.extend(apply_member_level_loss(target, levels, source=f"{enemy.name}'s level drain"))
    if target.current_life <= 0 and session is not None:
        from .abyss_afflictions import has_vampire_rise_pending
        from .abyss_campaign import queue_vampire_sire

        if has_vampire_rise_pending(target):
            log.extend(queue_vampire_sire(session, enemy))
    return log


def _destroy_metal_item(member: PartyMemberState, priority: list[str]) -> str | None:
    inventory = list(member.inventory)
    for kind in priority:
        kind_lower = kind.lower()
        for item in inventory:
            lower = item.lower()
            if kind_lower in {"armor", "shield"} and kind_lower in lower:
                member.inventory.remove(item)
                return item
            if kind_lower in {"weapon", "hand weapon", "light weapon", "two-handed weapon"} and any(
                token in lower for token in ("weapon", "sword", "axe", "mace", "bow", "dagger", "knife")
            ):
                if "armor" not in lower and "shield" not in lower:
                    member.inventory.remove(item)
                    return item
    for item in inventory:
        lower = item.lower()
        if any(token in lower for token in ("weapon", "armor", "shield", "sword", "axe", "mace", "bow")):
            member.inventory.remove(item)
            return item
    return None


def _queue_disease_damage(target: PartyMemberState, damage: int, source: str) -> str:
    status = f"{DISEASE_PENDING_PREFIX} {damage} ({source})"
    if status not in target.statuses:
        _add_status(target, status)
    return status


def _resolve_on_hit_disease(
    enemy: EnemyState,
    target: PartyMemberState,
    effect: dict[str, Any],
    *,
    show_rolls: bool,
    explain_math: bool,
    session: SessionState | None,
) -> list[str]:
    save_level = resolve_effect_level(effect.get("save_level"), hcl=enemy.level, default=enemy.level)
    passed, log = monster_effect_save(
        target,
        save_level,
        str(effect.get("save_type", "disease")),
        effect,
        label=f"{enemy.name} disease",
        show_rolls=show_rolls,
        explain_math=explain_math,
        session=session,
    )
    if passed:
        return log
    damage = int(effect.get("damage", 1))
    timing = str(effect.get("timing", "end_of_encounter")).lower()
    if "end_of" in timing:
        _queue_disease_damage(target, damage, enemy.name)
        log.append(f"Effect: {target.name} contracts disease (pending {damage} Life loss at encounter end).")
        return log
    target.current_life = max(0, target.current_life - damage)
    log.append(f"Effect: {target.name} loses {damage} Life from disease.")
    if target.current_life <= 0:
        log.append(f"{target.name} falls.")
    return log


def _resolve_on_hit_petrification(
    enemy: EnemyState,
    target: PartyMemberState,
    effect: dict[str, Any],
    *,
    show_rolls: bool,
    explain_math: bool,
    session: SessionState | None,
) -> list[str]:
    save_level = resolve_effect_level(effect.get("save_level"), hcl=enemy.level, default=enemy.level)
    passed, log = monster_effect_save(
        target,
        save_level,
        str(effect.get("save_type", "petrification")),
        effect,
        label=f"{enemy.name} petrification",
        show_rolls=show_rolls,
        explain_math=explain_math,
        session=session,
    )
    if passed:
        return log
    _add_status(target, PETRIFIED_STATUS)
    log.append(f"Effect: {target.name} is turned to stone.")
    if session is not None:
        from .hirelings import notify_hireling_morale_casualty

        log.extend(
            notify_hireling_morale_casualty(
                session,
                reason=f"{target.name} was turned to stone",
            )
        )
    return log


def apply_on_hit_effects(
    enemy: EnemyState,
    target: PartyMemberState,
    *,
    context: CombatContext,
    show_rolls: bool = True,
    explain_math: bool = False,
) -> list[str]:
    if target.current_life <= 0 or not enemy.on_hit_effects:
        return []
    session = context.session
    log: list[str] = []
    for effect in enemy.on_hit_effects:
        effect_type = str(effect.get("type", "")).lower()
        if effect_type == "poison":
            if context is not None:
                from .monster_combat_modifiers import resolve_on_hit_poison_timing

                deferred = resolve_on_hit_poison_timing(
                    effect,
                    enemy,
                    target,
                    context=context,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    session=session,
                )
                if deferred is not None:
                    log.extend(deferred)
                    continue
            log.extend(
                _resolve_on_hit_poison(
                    enemy,
                    target,
                    effect,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    session=session,
                )
            )
        elif effect_type == "level_drain":
            log.extend(
                _resolve_on_hit_level_drain(
                    enemy,
                    target,
                    effect,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    session=session,
                )
            )
        elif effect_type == "destroy_metal_items":
            priority = [str(item) for item in effect.get("priority_order", ["weapon", "armor", "shield"])]
            destroyed = _destroy_metal_item(target, priority)
            if destroyed:
                log.append(f"Effect: {enemy.name} destroys {target.name}'s {destroyed}.")
            else:
                log.append(f"{enemy.name} finds no metal items on {target.name} to destroy.")
        elif effect_type == "magic":
            if str(effect.get("effect", "")).lower() == "attack_penalty":
                save_level = resolve_effect_level(effect.get("save_level"), hcl=enemy.level, default=enemy.level)
                passed, save_log = monster_effect_save(
                    target,
                    save_level,
                    str(effect.get("save_type", "magic")),
                    effect,
                    label=f"{enemy.name} magic",
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    session=session,
                )
                log.extend(save_log)
                if not passed:
                    _add_status(target, ATTACK_PENALTY_MAGIC_STATUS)
                    log.append(f"Effect: {target.name} suffers -1 Attack rolls until the encounter ends.")
            elif int(effect.get("damage", 0)) > 0:
                save_level = resolve_effect_level(effect.get("save_level"), hcl=enemy.level, default=enemy.level)
                passed, save_log = monster_effect_save(
                    target,
                    save_level,
                    str(effect.get("save_type", "magic")),
                    effect,
                    label=f"{enemy.name} {effect_type}",
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    session=session,
                )
                log.extend(save_log)
                if not passed:
                    damage = int(effect.get("damage", 1))
                    target.current_life = max(0, target.current_life - damage)
                    log.append(f"Effect: {target.name} loses {damage} Life from {enemy.name}.")
            else:
                description = str(effect.get("description", effect_type))
                log.append(f"Event: {enemy.name} — {description} (timing {effect.get('timing', 'immediate')} pending).")
        elif effect_type == "disease":
            log.extend(
                _resolve_on_hit_disease(
                    enemy,
                    target,
                    effect,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    session=session,
                )
            )
        elif effect_type == "petrification":
            log.extend(
                _resolve_on_hit_petrification(
                    enemy,
                    target,
                    effect,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    session=session,
                )
            )
        elif effect_type == "slime_disease":
            save_level = resolve_effect_level(effect.get("save_level"), hcl=enemy.level, default=enemy.level)
            passed, save_log = monster_effect_save(
                target,
                save_level,
                str(effect.get("save_type", "disease")),
                effect,
                label=f"{enemy.name} slime disease",
                show_rolls=show_rolls,
                explain_math=explain_math,
                session=session,
            )
            log.extend(save_log)
            if not passed:
                _add_status(target, SLIME_DISEASE_STATUS)
                log.append(f"Effect: {target.name} is infected with slime disease.")
        elif effect_type == "status":
            status = str(effect.get("status", "")).strip()
            if status.lower().startswith("lycanthropy exposure"):
                from .abyss_afflictions import mark_lycanthropy_exposure

                mark_lycanthropy_exposure(target)
                log.append(
                    f"Effect: {target.name} is exposed to lycanthropy; save at encounter end."
                )
            elif status:
                save_level = effect.get("save_level") or effect.get("level")
                if save_level is not None:
                    passed, save_log = monster_effect_save(
                        target,
                        resolve_effect_level(save_level, hcl=enemy.level, default=enemy.level),
                        str(effect.get("save_type", "magic")),
                        effect,
                        label=str(effect.get("label") or f"{enemy.name} {status} save"),
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                        session=session,
                    )
                    log.extend(save_log)
                    if passed:
                        continue
                _add_status(target, status)
                log.append(f"Effect: {target.name} gains status: {status}.")
        elif effect_type in {"magic", "disease", "petrification", "slime_disease"}:
            description = str(effect.get("description", effect_type))
            log.append(f"Event: {enemy.name} — {description} (timing {effect.get('timing', 'immediate')} pending).")
        else:
            description = str(effect.get("description", effect_type))
            log.append(f"Event: {enemy.name} on-hit effect ({effect_type}): {description}")
    return log


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
