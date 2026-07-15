from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState, SessionState
from .combat import apply_enemy_damage, attack_damage, living_party
from .combat_modifiers import (
    enemy_has_magic_resistance,
    enemy_magic_resist_bonus,
    resolve_spell_effect,
    spell_mr_penetration_level,
    spell_target_level,
    spellcasting_modifier,
)
from .consumables import SLUMBER_AMANITA_STATUS
from .dice import roll_d6, roll_exploding_for_level
from .heroic_skill_effects import (
    eldritch_aim_bonus,
    eldritch_force_extra_damage,
    explosive_magic_extra_damage,
    support_casting_bonus,
)
from .subdual import apply_major_foe_level_drop
from .madness import heal_madness


SLEEP_IMMUNE_TAGS = {"undead", "dragon", "artificial", "clockwork", "elemental", "spirit", "construct", "sleep_immune"}
ILLUSION_IMMUNE_TAGS = {"vermin", "undead", "artificial", "clockwork", "elemental", "construct"}
WOOD_FOE_TAGS = {"plant", "tree", "wood", "dryad"}
HEALING_PRAYER_USES_PER_ADVENTURE = 3
REPEATABLE_PRAYERS = {"healing_prayer", "healing"}


@dataclass
class SpellOutcome:
    log: list[str]
    enemies: list[EnemyState]
    party: list[PartyMemberState]
    combat_over: bool = False
    spell_consumed: bool = True
    teleport_to_entrance: bool = False
    teleport_to_tile_id: str | None = None
    destroy_door: bool = False
    summon_beast: bool = False
    subdual_penalty_ignored: bool = False
    illusionary_fog: bool = False
    peaceful_bribe: bool = False
    flee_bonus: bool = False
    illusionary_servant: bool = False
    curse_break_target_id: str | None = None
    bear_form: bool = False
    bear_form_pre_life: int = 0
    alter_weather_active: bool = False
    forest_pathway_active: bool = False
    glamour_mask_character_id: str | None = None
    glamour_mask_reroll_available: bool = False
    banquet_rations: int = 0


def normalize_spell_name(name: str) -> str:
    return name.strip().lower().replace("'", "").replace(" ", "_")


def prepared_spell_count(member: PartyMemberState, spell_name: str) -> int:
    target = normalize_spell_name(spell_name)
    return sum(1 for item in member.spells if normalize_spell_name(item) == target)


def expended_spell_count(expended_spells: list[str] | None, spell_name: str) -> int:
    target = normalize_spell_name(spell_name)
    return sum(1 for item in expended_spells or [] if normalize_spell_name(item) == target)


def magical_power_bonus_uses(member: PartyMemberState, spell_name: str) -> int:
    target = normalize_spell_name(spell_name)
    total = 0
    for secret in member.secrets or []:
        raw = str(secret).strip()
        if ":" not in raw:
            continue
        prefix, value = raw.split(":", 1)
        if prefix.strip().lower() == "magical_power_increase" and normalize_spell_name(value) == target:
            total += 1
    return total


def knows_spell(member: PartyMemberState, spell_name: str) -> bool:
    return prepared_spell_count(member, spell_name) > 0


def is_spell_expended(
    spell_name: str,
    *,
    expended_spells: list[str] | None = None,
    healing_prayer_uses: int = 0,
    prepared_count: int = 1,
    prayer_limit: int = HEALING_PRAYER_USES_PER_ADVENTURE,
) -> bool:
    key = normalize_spell_name(spell_name)
    if key in REPEATABLE_PRAYERS:
        return healing_prayer_uses >= prayer_limit
    return expended_spell_count(expended_spells, spell_name) >= max(1, prepared_count)


def can_cast_spell(
    member: PartyMemberState,
    spell_name: str,
    *,
    expended_spells: list[str] | None = None,
    healing_prayer_uses: int = 0,
) -> bool:
    prepared_count = prepared_spell_count(member, spell_name)
    power_bonus = magical_power_bonus_uses(member, spell_name)
    key = normalize_spell_name(spell_name)
    if key in REPEATABLE_PRAYERS:
        prepared_count = max(1, prepared_count)
    else:
        prepared_count += power_bonus
    if prepared_count <= 0:
        return False
    return not is_spell_expended(
        spell_name,
        expended_spells=expended_spells,
        healing_prayer_uses=healing_prayer_uses,
        prepared_count=prepared_count,
        prayer_limit=HEALING_PRAYER_USES_PER_ADVENTURE + power_bonus,
    )


def mark_spell_expended(
    spell_name: str,
    *,
    expended_spells: list[str],
    healing_prayer_uses: int,
    prayer_limit: int = HEALING_PRAYER_USES_PER_ADVENTURE,
) -> tuple[list[str], int, list[str]]:
    log: list[str] = []
    key = normalize_spell_name(spell_name)
    if key in REPEATABLE_PRAYERS:
        healing_prayer_uses += 1
        remaining = prayer_limit - healing_prayer_uses
        if remaining > 0:
            log.append(f"Healing prayer used ({healing_prayer_uses}/{prayer_limit} this adventure).")
        else:
            log.append(f"Healing prayer used ({prayer_limit}/{prayer_limit} this adventure).")
        return expended_spells, healing_prayer_uses, log
    expended_spells.append(spell_name.strip())
    log.append(f"{spell_name} is expended until this adventure ends (still on your spell list).")
    return expended_spells, healing_prayer_uses, log


def spell_hits(
    member: PartyMemberState,
    enemy: EnemyState,
    *,
    show_rolls: bool,
    label: str,
    modifier_override: int | None = None,
    ally_target: PartyMemberState | None = None,
    session: SessionState | None = None,
) -> tuple[bool, list[str], bool]:
    modifier = modifier_override
    if modifier is None:
        modifier = spellcasting_modifier(member)
    modifier += support_casting_bonus(member, ally_target)
    hit, log, _, exploded = resolve_spell_effect(
        member,
        enemy,
        show_rolls=show_rolls,
        label=label,
        modifier_override=modifier,
        session=session,
    )
    return hit, log, exploded


MINOR_FOE_CATEGORIES = frozenset({"vermin", "minions"})


def is_minor_foe(enemy: EnemyState) -> bool:
    return enemy.life > 0 and enemy.category in MINOR_FOE_CATEGORIES


def is_mass_kill_minor(enemy: EnemyState) -> bool:
    return is_minor_foe(enemy)


def fireball_modifier_bonus(enemy: EnemyState) -> int:
    if "mummy" in enemy.name.lower():
        return 2
    if "fireball_penalty:-1" in {str(tag).lower() for tag in enemy.tags}:
        return -1
    return 0


def fireball_needs_aim_choice(enemies: list[EnemyState]) -> bool:
    living = [enemy for enemy in enemies if enemy.life > 0]
    minors = [enemy for enemy in living if is_mass_kill_minor(enemy)]
    singles = [enemy for enemy in living if not is_mass_kill_minor(enemy)]
    return bool(minors and singles)


def _pick_foe_by_id(enemies: list[EnemyState], foe_id: str | None) -> EnemyState | None:
    if not foe_id:
        return None
    return next((enemy for enemy in enemies if enemy.id == foe_id and enemy.life > 0), None)


def _resolve_fireball_target(
    living: list[EnemyState],
    *,
    foe_id: str | None,
    target_mode: str | None,
    log: list[str],
) -> tuple[EnemyState | None, bool | None]:
    """Return (target, use_mass_kill). use_mass_kill None means caller should abort."""
    minors = [enemy for enemy in living if is_mass_kill_minor(enemy)]
    singles = [enemy for enemy in living if not is_mass_kill_minor(enemy)]

    if target_mode == "minions":
        if not minors:
            log.append("No minions or vermin to target with Fireball.")
            return None, None
        target = _pick_foe_by_id(minors, foe_id) or minors[0]
        log.append("Fireball aimed at minions.")
        return target, True

    if target_mode == "single":
        pool = singles or living
        target = _pick_foe_by_id(pool, foe_id) or (pool[0] if pool else None)
        if target is None:
            log.append("Choose a foe for Fireball.")
            return None, None
        log.append(f"Fireball aimed at {target.name}.")
        return target, False

    if minors and singles:
        log.append(
            "Choose Fireball aim: minions (area slay) or a single boss/weird foe — "
            "it cannot hit both groups."
        )
        return None, None
    if minors:
        target = _pick_foe_by_id(minors, foe_id) or minors[0]
        log.append("Fireball aimed at minions.")
        return target, True
    if living:
        target = _pick_foe_by_id(living, foe_id) or living[0]
        log.append(f"Fireball aimed at {target.name}.")
        return target, False
    log.append("There are no targets for Fireball.")
    return None, None


def resolve_spell_cast(
    spell_name: str,
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    target_character_id: str | None = None,
    target_foe_id: str | None = None,
    secondary_foe_id: str | None = None,
    spell_target_mode: str | None = None,
    show_rolls: bool = True,
    terrain: str = "indoor",
    door_type: str | None = None,
    from_scroll: bool = False,
    from_magic_item: bool = False,
    life_transfer_amount: int | None = None,
    teleport_tile_id: str | None = None,
    teleport_character_ids: list[str] | None = None,
    mass_blessing_target_ids: list[str] | None = None,
    mass_blessing_condition_choices: dict[str, list[str]] | None = None,
    final_boss: bool = False,
    session: SessionState | None = None,
    spellcasting_bonus: int = 0,
    item_name: str | None = None,
) -> SpellOutcome:
    from .terrain import resolve_play_context

    play_ctx = resolve_play_context(None, session, terrain=terrain)
    tile_terrain = play_ctx.terrain
    outdoors = play_ctx.outdoors
    key = normalize_spell_name(spell_name)
    source_note = ""
    if from_scroll:
        source_note = " (from scroll)"
    elif from_magic_item:
        source_note = " (from magic item)"
    target_name = next((member.name for member in party if member.character_id == target_character_id), None)
    target_name = target_name or next((enemy.name for enemy in enemies if enemy.id == target_foe_id), None)
    target_note = f" on {target_name}" if target_name else ""
    log: list[str] = [f"{caster.name} casts {spell_name}{target_note}.{source_note}"]
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    from .forsaken_depths_legendary_spells import is_fd_legendary_spell, try_resolve_fd_legendary_spell

    if is_fd_legendary_spell(spell_name):
        legendary = try_resolve_fd_legendary_spell(
            key,
            spell_name,
            caster,
            party,
            living_enemies,
            log,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            mass_blessing_target_ids=mass_blessing_target_ids,
            mass_blessing_condition_choices=mass_blessing_condition_choices,
            door_type=door_type,
            show_rolls=show_rolls,
            final_boss=final_boss,
            session=session,
            item_name=item_name,
        )
        if legendary is not None:
            return legendary
    from .forsaken_depths_heroic_spells import (
        heroic_spell_id,
        is_fd_heroic_spell,
        try_resolve_fd_heroic_spell,
    )

    if is_fd_heroic_spell(spell_name):
        heroic = try_resolve_fd_heroic_spell(
            heroic_spell_id(spell_name),
            spell_name,
            caster,
            party,
            living_enemies,
            log,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            door_type=door_type,
            show_rolls=show_rolls,
            session=session,
            from_scroll=from_scroll,
        )
        if heroic is not None:
            return heroic
    if key in {"fireball", "fire_ball"}:
        if door_type == "iron" and not living_enemies:
            outcome = SpellOutcome(log, living_enemies, party, spell_consumed=True, destroy_door=True)
            outcome.log.append("Fireball destroys the iron door.")
            return outcome
        outcome = _cast_fireball(
            caster,
            party,
            living_enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            session=session,
        )
        return outcome
    if key == "lightning":
        if door_type == "iron" and not living_enemies:
            outcome = SpellOutcome(log, living_enemies, party, spell_consumed=True, destroy_door=True)
            outcome.log.append("Lightning destroys the iron door.")
            return outcome
        outcome = _cast_lightning(
            caster,
            party,
            living_enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id,
            session=session,
        )
        return outcome
    if key == "sleep":
        return _cast_sleep(
            caster,
            party,
            living_enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id,
        )
    if key == "protection":
        return _cast_protection(caster, party, living_enemies, target_character_id, log)
    if key == "blessing":
        return _cast_blessing(
            caster,
            party,
            living_enemies,
            target_character_id,
            log,
            session=session,
            show_rolls=show_rolls,
        )
    if key in {"healing_prayer", "healing"}:
        return _cast_healing_prayer(
            caster,
            party,
            living_enemies,
            target_character_id,
            log,
            show_rolls=show_rolls,
            session=session,
        )
    if key == "escape":
        log.append(f"{caster.name} teleports to the adventure entrance.")
        return SpellOutcome(
            log,
            living_enemies,
            party,
            combat_over=True,
            spell_consumed=True,
            teleport_to_entrance=True,
        )
    if key == "disperse_vermin":
        return _cast_disperse_vermin(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "summon_beast":
        log.append(
            "The druid summons a large animal (boar, large cat, bear) to fight for the party "
            "(L3, 5 Life, 1 damage per round)."
        )
        return SpellOutcome(log, living_enemies, party, spell_consumed=True, summon_beast=True)
    if key == "water_jet":
        return _cast_water_jet(
            caster,
            party,
            living_enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            terrain=tile_terrain,
        )
    if key == "bear_form":
        return _cast_bear_form(caster, party, living_enemies, log)
    if key == "warp_wood":
        return _cast_warp_wood(caster, party, living_enemies, log, door_type=door_type)
    if key == "barkskin":
        return _cast_barkskin(caster, party, living_enemies, target_character_id, log)
    if key == "lightning_strike":
        if not outdoors:
            log.append("Lightning Strike cannot be used indoors.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        return _cast_lightning(
            caster,
            party,
            living_enemies,
            log,
            show_rolls=show_rolls,
            label="Lightning Strike",
            session=session,
        )
    if key in {"spiderweb", "entangle"}:
        if key == "entangle" and not play_ctx.entangle_ok:
            log.append("Entangle requires forest, swamp, or jungle terrain.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        return _cast_spiderweb(caster, party, living_enemies, log, label=spell_name)
    if key == "subdual":
        log.append("All allies ignore the -1 subdual attack penalty until combat ends.")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True, subdual_penalty_ignored=True)
    if key == "forest_pathway":
        if not play_ctx.forest_pathway_ok:
            log.append("Forest Pathway works only outdoors in woodland.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        minutes = caster.level * 10
        log.append(
            f"Vegetation parts for the party to pass ({minutes} minutes; woodland travel ignores undergrowth)."
        )
        return SpellOutcome(
            log,
            living_enemies,
            party,
            spell_consumed=True,
            forest_pathway_active=True,
        )
    if key == "alter_weather":
        if not play_ctx.alter_weather_ok:
            log.append("Alter Weather works only outdoors.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        log.append(
            "Weather shifts for 10 minutes; ranged attacks at -1, druid Lightning Strike at +1 "
            "(until the party rests)."
        )
        return SpellOutcome(
            log,
            living_enemies,
            party,
            spell_consumed=True,
            alter_weather_active=True,
        )
    if key == "illusionary_armor":
        return _cast_illusionary_armor(caster, party, living_enemies, log)
    if key == "illusionary_mirror_image":
        return _cast_mirror_image(caster, party, living_enemies, log)
    if key == "illusionary_servant":
        log.append(
            "An illusionary servant appears to carry treasure (200gp, weapons, armor) until slain or trapped."
        )
        return SpellOutcome(log, living_enemies, party, spell_consumed=True, illusionary_servant=True)
    if key == "disbelief":
        return _cast_disbelief(caster, party, living_enemies, log)
    if key == "phantasmal_binding":
        return _cast_phantasmal_binding(
            caster,
            party,
            living_enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id,
        )
    if key == "illusionary_fog":
        log.append("Illusionary fog surrounds the party; ranged/gaze attacks suspended, +2 Defense when fleeing.")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True, illusionary_fog=True, flee_bonus=True)
    if key == "glamour_mask":
        hours = caster.level
        log.append(
            f"Glamour Mask alters {caster.name}'s appearance for {hours} hour(s); "
            "one Reaction or social Save may be rerolled."
        )
        return SpellOutcome(
            log,
            living_enemies,
            party,
            spell_consumed=True,
            glamour_mask_character_id=caster.character_id,
            glamour_mask_reroll_available=True,
        )
    if key == "shadow_strike":
        return _cast_shadow_strike(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "specter_swarm":
        return _cast_specter_swarm(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "mirage_of_fortune":
        return _cast_mirage_of_fortune(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "illusionary_banquet":
        ration_count = min(caster.level + 3, 7)
        log.append(
            f"Illusionary Banquet creates {ration_count} illusionary food ration(s) "
            "(max 7 days sustenance)."
        )
        return SpellOutcome(
            log,
            living_enemies,
            party,
            spell_consumed=True,
            banquet_rations=ration_count,
        )
    if key == "illusionary_sword":
        target = caster
        if "Illusionary Sword" not in target.statuses:
            target.statuses.append(f"Illusionary Sword ({caster.level + 3} turns)")
        log.append(f"{target.name} wields an illusionary sword (+L Attack, subdual) for {caster.level + 3} turns.")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True)
    from .expert_spells import cast_expert_spell, is_expert_spell

    if is_expert_spell(spell_name):
        expert_outcome = cast_expert_spell(
            spell_name,
            caster,
            party,
            living_enemies,
            log,
            show_rolls=show_rolls,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            secondary_foe_id=secondary_foe_id,
            life_transfer_amount=life_transfer_amount,
            teleport_tile_id=teleport_tile_id,
            teleport_character_ids=teleport_character_ids,
            final_boss=final_boss,
        )
        if expert_outcome is not None:
            return expert_outcome
    log.append(f"Unknown or unsupported spell: {spell_name}.")
    return SpellOutcome(log, living_enemies, party, spell_consumed=False)


def _offensive_spell_damage_bonus(
    session: SessionState | None,
    caster: PartyMemberState,
    spell_key: str,
) -> tuple[int, list[str]]:
    log: list[str] = []
    damage = eldritch_force_extra_damage(caster)
    if damage:
        log.append(f"Eldritch Force adds {damage} spell damage.")
    if session is not None:
        extra, notes = explosive_magic_extra_damage(session, caster, spell_key)
        damage += extra
        log.extend(notes)
    return damage, log


def combat_spellcasting_penalty(enemies: list[EnemyState], log: list[str]) -> int:
    """Return the strongest printed casting penalty imposed by living foes."""
    penalties: list[int] = []
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        for tag in enemy.tags:
            text = str(tag).lower()
            if not text.startswith("spellcasting_penalty:"):
                continue
            try:
                penalties.append(int(text.split(":", 1)[1]))
            except ValueError:
                continue
    penalty = min(penalties, default=0)
    if penalty:
        log.append(f"Effect: distracting foes impose {penalty} on this spellcasting roll.")
    return penalty


def _cast_fireball(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_foe_id: str | None = None,
    spell_target_mode: str | None = None,
    session: SessionState | None = None,
    label: str = "Fireball",
    modifier_bonus: int = 0,
) -> SpellOutcome:
    if not enemies:
        log.append(f"There are no targets for {label}.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target, use_mass_kill = _resolve_fireball_target(
        enemies,
        foe_id=target_foe_id,
        target_mode=spell_target_mode,
        log=log,
    )
    if target is None or use_mass_kill is None:
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if "dragon" in target.tags and "undead" not in target.tags:
        log.append(f"{label} has no effect on this dragon.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    bonus = fireball_modifier_bonus(target)
    modifier = (
        spellcasting_modifier(caster)
        + bonus
        + modifier_bonus
        + eldritch_aim_bonus(caster)
        + combat_spellcasting_penalty(enemies, log)
    )
    if bonus:
        log.append(f"{label} gains +{bonus} vs {target.name}.")
    hit, hit_log, final_total, _ = resolve_spell_effect(
        caster,
        target,
        show_rolls=show_rolls,
        label=label,
        modifier_override=modifier,
        session=session,
    )
    log.extend(hit_log)
    if not hit:
        log.append(f"{label} misses — the once-per-adventure slot is still expended.")
        return SpellOutcome(log, enemies, party)
    if use_mass_kill:
        capacity = max(1, final_total - target.level)
        kill_capacity = capacity
        slain = 0
        for enemy in enemies:
            if kill_capacity <= 0:
                break
            if is_minor_foe(enemy):
                enemy.life = 0
                kill_capacity -= 1
                slain += 1
                log.append(f"{label} slays {enemy.name}.")
        remaining = sum(1 for enemy in enemies if enemy.life > 0)
        log.append(
            f"{label} kills up to {capacity} minion(s) at 1 Life; "
            f"{slain} slain{f'; {remaining} foe(s) remain' if remaining else ''}."
        )
    else:
        bonus_damage, bonus_log = _offensive_spell_damage_bonus(session, caster, "fireball")
        log.extend(bonus_log)
        total_damage = 1 + bonus_damage
        wound_applied = apply_enemy_damage(
            target,
            total_damage,
            damage_kind="fire",
            courtship_spell_session=session,
            courtship_spell_party=party,
            courtship_spell_log=log,
            combat_log=log,
        )
        if wound_applied:
            log.append(f"{label} hits {target.name} for {total_damage} damage.")
        if wound_applied and apply_major_foe_level_drop(target):
            log.append(f"{target.name} is bloodied; its effective Level drops to L{target.level}.")
        if target.life <= 0:
            log.append(f"{target.name} is defeated.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_lightning(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    label: str = "Lightning",
    target_foe_id: str | None = None,
    session: SessionState | None = None,
) -> SpellOutcome:
    if not enemies:
        log.append(f"There are no targets for {label}.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = _pick_foe_by_id(enemies, target_foe_id) or enemies[0]
    if "elemental" in target.tags and "lightning" in target.name.lower():
        log.append(f"{label} has no effect on this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    weather_bonus = 0
    if label == "Lightning Strike" and session is not None and session.alter_weather_active:
        weather_bonus = 1
        log.append("Alter Weather adds +1 to Lightning Strike.")
    modifier = spellcasting_modifier(caster, spell_key="lightning") + weather_bonus + combat_spellcasting_penalty(enemies, log)
    hit, hit_log, exploded = spell_hits(
        caster,
        target,
        show_rolls=show_rolls,
        label=label,
        modifier_override=modifier,
    )
    log.extend(hit_log)
    if not hit:
        log.append(f"{label} misses — the once-per-adventure slot is still expended.")
        return SpellOutcome(log, enemies, party)
    damage_dealt = 0
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        damage_dealt = target.life
        wound_applied = apply_enemy_damage(
            target,
            target.life,
            damage_kind="lightning",
            courtship_spell_session=session,
            courtship_spell_party=party,
            courtship_spell_log=log,
            combat_log=log,
        )
        if wound_applied:
            log.append(f"Lightning slays {target.name}.")
        else:
            damage_dealt = 0
    else:
        bonus_damage, bonus_log = _offensive_spell_damage_bonus(session, caster, "lightning")
        log.extend(bonus_log)
        total_damage = 2 + bonus_damage
        damage_dealt = total_damage
        wound_applied = apply_enemy_damage(
            target,
            total_damage,
            damage_kind="lightning",
            courtship_spell_session=session,
            courtship_spell_party=party,
            courtship_spell_log=log,
            combat_log=log,
        )
        if wound_applied:
            log.append(f"Lightning hits {target.name} for {total_damage} damage.")
        else:
            damage_dealt = 0
        if wound_applied and apply_major_foe_level_drop(target):
            log.append(f"{target.name} is bloodied; its effective Level drops to L{target.level}.")
    from .milestones import record_lightning_damage

    log.extend(record_lightning_damage(caster, damage_dealt, exploded=exploded))
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
    target_foe_id: str | None = None,
) -> SpellOutcome:
    if not enemies:
        log.append("There are no targets for Sleep.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = _pick_foe_by_id(enemies, target_foe_id) or enemies[0]
    slumber_bonus = 0
    if SLUMBER_AMANITA_STATUS in caster.statuses:
        slumber_bonus = max(1, (caster.level - 1) // 4 + 1)
        caster.statuses = [status for status in caster.statuses if status != SLUMBER_AMANITA_STATUS]
        log.append(f"Slumber Amanita adds +{slumber_bonus} to this Sleep spell.")
    if target.level >= 11 or any(tag in SLEEP_IMMUNE_TAGS for tag in target.tags):
        log.append(
            f"Effect: Sleep has no effect on {target.name} "
            "(immune by Level 11+ or undead/dragon/artificial/construct/elemental/spirit trait)."
        )
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    modifier = spellcasting_modifier(caster, spell_key="sleep") + slumber_bonus + combat_spellcasting_penalty(enemies, log)
    hit, hit_log, _ = spell_hits(caster, target, show_rolls=show_rolls, label="Sleep", modifier_override=modifier)
    log.extend(hit_log)
    if not hit:
        log.append("Sleep fails.")
        return SpellOutcome(log, enemies, party)
    sleep_levels = 0
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        affected = roll_d6() + caster.level
        remaining = affected
        for enemy in enemies:
            if remaining <= 0:
                break
            if enemy.life <= 1 and enemy.category in {"vermin", "minions"}:
                sleep_levels += enemy.level
                enemy.life = 0
                remaining -= 1
        log.append(f"Sleep knocks out {affected - remaining} minor foes.")
    else:
        sleep_levels = target.level
        target.life = 0
        log.append(f"{target.name} falls asleep and is defeated.")
    from .milestones import record_sleep_levels

    log.extend(record_sleep_levels(caster, sleep_levels))
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def cast_sleep_effect(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
) -> SpellOutcome:
    log: list[str] = []
    return _cast_sleep(caster, party, enemies, log, show_rolls=show_rolls)


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
    *,
    session: SessionState | None = None,
    show_rolls: bool = True,
) -> SpellOutcome:
    target = _pick_target(party, target_character_id) or caster
    from .monster_template_effects import FD_CORROSIVE_MUCUS_STATUS, PETRIFIED_STATUS
    from .fungal_traps import cordyceps_infected_turns
    from .abyss_afflictions import apply_blessing_to_dark_plague

    dark_plague_result = apply_blessing_to_dark_plague(
        caster,
        target,
        log=log,
        show_rolls=show_rolls,
        session=session,
    )
    if dark_plague_result is False:
        # Abyss p.37: a failed Dark Plague cure wastes this Blessing.
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    before_statuses = list(target.statuses)
    session_curse = bool(
        session is not None and session.cursed_character_id == target.character_id
    )
    had_cordyceps = cordyceps_infected_turns(target) is not None
    target.statuses = [
        item
        for item in target.statuses
        if item.lower() not in {
            "ant people chemical marker",
            "cursed",
            "paralyzed",
            "petrified",
            "slime disease",
            FD_CORROSIVE_MUCUS_STATUS.lower(),
        }
        and item != PETRIFIED_STATUS
        and not item.lower().startswith("cordyceps infected")
    ]
    removed_statuses = [status for status in before_statuses if status not in target.statuses]
    if session_curse:
        removed_statuses.append("Cursed")
    if had_cordyceps:
        log.append(f"Blessing clears cordyceps from {target.name}.")
    healed = heal_madness(target, 1)
    if healed:
        log.append(f"Blessing heals 1 Madness from {target.name}.")
    if removed_statuses:
        log.append(f"Blessing heals {target.name}: {', '.join(removed_statuses)}.")
    else:
        log.append(f"Blessing finds no additional curse, petrification, disease, or Madness effect on {target.name}.")
    if session is not None:
        from .cavern_features import cleanse_cavern_water_contamination

        if cleanse_cavern_water_contamination(session, target.character_id):
            log.append(f"Blessing cleanses contaminated water from {target.name}.")
        from .forsaken_depths_content import clear_fd_hallucination_with_blessing

        log.extend(clear_fd_hallucination_with_blessing(target))
        from .forsaken_depths_hordes import clear_lizardman_horde_poison_with_blessing

        log.extend(clear_lizardman_horde_poison_with_blessing(target))
    if dark_plague_result is True:
        log.append("Dark Plague uses the Abyss d8+L cure check; other Blessing effects resolve normally.")
    return SpellOutcome(
        log,
        enemies,
        party,
        spell_consumed=True,
        curse_break_target_id=target.character_id if session_curse else None,
    )


def _cast_healing_prayer(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    target_character_id: str | None,
    log: list[str],
    *,
    show_rolls: bool = True,
    session: SessionState | None = None,
) -> SpellOutcome:
    target = _pick_target(party, target_character_id) or caster
    if target.current_life >= target.max_life:
        log.append(f"{target.name} is already at full Life.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if session is not None:
        from .class_abilities import bulwark_magical_healing_blocked

        blocked = bulwark_magical_healing_blocked(session, target)
        if blocked:
            log.append(blocked)
            return SpellOutcome(log, enemies, party, spell_consumed=False)
    total, rolls = roll_exploding_for_level(caster)
    modifier = (
        spellcasting_modifier(caster)
        + support_casting_bonus(caster, target if target.character_id != caster.character_id else None)
        + combat_spellcasting_penalty(enemies, log)
    )
    healed = total + modifier
    holy_symbol_bonus = 2 if any("holy symbol of healing" in item.lower() for item in caster.inventory) else 0
    if holy_symbol_bonus:
        healed += holy_symbol_bonus
        log.append(f"Effect: Holy symbol of healing adds +{holy_symbol_bonus} Life to Healing prayer.")
    if show_rolls:
        bonus_text = f" + {holy_symbol_bonus} holy symbol" if holy_symbol_bonus else ""
        log.append(
            f"Healing prayer: {' + '.join(str(value) for value in rolls)} + {modifier}{bonus_text} = {healed} Life restored."
        )
    target_life_before = target.current_life
    target.current_life = min(target.max_life, target.current_life + max(1, healed))
    log.append(
        f"Healing prayer restores {max(1, healed)} Life to {target.name} "
        f"({target_life_before}->{target.current_life}/{target.max_life} HP)."
    )
    from .fungal_traps import clear_cordyceps_infection

    if clear_cordyceps_infection(target):
        log.append(f"Healing prayer clears cordyceps from {target.name}.")
    if session is not None:
        from .cavern_features import cleanse_cavern_water_contamination

        if cleanse_cavern_water_contamination(session, target.character_id):
            log.append(f"Healing prayer cleanses contaminated water from {target.name}.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _pick_target(party: list[PartyMemberState], target_character_id: str | None) -> PartyMemberState | None:
    living = living_party(party)
    if not living:
        return None
    if target_character_id:
        return next((member for member in living if member.character_id == target_character_id), living[0])
    return living[0]


def _foe_immune_to_illusions(enemy: EnemyState) -> bool:
    return enemy.category == "vermin" or any(tag in ILLUSION_IMMUNE_TAGS for tag in enemy.tags)


def _cast_disperse_vermin(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
) -> SpellOutcome:
    vermin = [enemy for enemy in enemies if enemy.category == "vermin"]
    if not vermin:
        log.append("There are no vermin to disperse.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = vermin[0]
    if any(tag in {"undead", "artificial", "clockwork", "elemental"} for tag in target.tags):
        log.append("Disperse Vermin has no effect on these vermin.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    modifier = spellcasting_modifier(caster) * 2 + combat_spellcasting_penalty(enemies, log)
    hit, hit_log, _ = spell_hits(caster, target, show_rolls=show_rolls, label="Disperse Vermin", modifier_override=modifier)
    log.extend(hit_log)
    if not hit:
        log.append("Disperse Vermin fails.")
        return SpellOutcome(log, enemies, party)
    dispersed = 0
    for enemy in vermin:
        if enemy.life > 0:
            enemy.life = 0
            dispersed += 1
    log.append(f"Disperse Vermin drives off {dispersed} vermin (no bodies to loot).")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_water_jet(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_foe_id: str | None = None,
    spell_target_mode: str | None = None,
    terrain: str = "indoor",
) -> SpellOutcome:
    if not enemies:
        log.append("Water Jet provides enough water for the party, mounts, and hirelings for a full day.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        log.append("Water Jet provides enough water for the party, mounts, and hirelings for a full day.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    mode = (spell_target_mode or "").strip().lower()
    if mode not in {"fire", "vermin", "minion", "distract"}:
        log.append(
            "Choose Water Jet effect: fire damage, disperse 2 Vermin, knock out 1 Minion, or distract 1 Major Foe."
        )
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = next((enemy for enemy in living if enemy.id == target_foe_id), living[0])
    if mode == "fire" and not ("fire" in target.tags or "fire" in target.name.lower()):
        log.append("Water Jet fire-damage effect requires a fire-based creature or natural fire target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if mode == "vermin" and target.category != "vermin":
        log.append("Water Jet disperse effect requires a Vermin target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if mode == "minion" and target.category != "minions":
        log.append("Water Jet knock-out effect requires a Minion target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if mode == "distract" and target.category not in {"boss", "weird"}:
        log.append("Water Jet distract effect requires a Major Foe target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    modifier = spellcasting_modifier(caster) + combat_spellcasting_penalty(enemies, log)
    from .terrain import WATER_TERRAINS, resolve_play_context

    play_ctx = resolve_play_context(None, session=None, terrain=terrain)
    if play_ctx.terrain == "desert":
        modifier -= 2
        log.append("Water Jet is cast at -2 in desert terrain.")
    elif play_ctx.terrain in WATER_TERRAINS:
        modifier += 1
        log.append("Water Jet is cast at +1 near a body of water.")
    hit, hit_log, _ = spell_hits(
        caster,
        target,
        show_rolls=show_rolls,
        label="Water Jet",
        modifier_override=modifier,
    )
    log.extend(hit_log)
    if not hit:
        log.append("Water Jet misses.")
        return SpellOutcome(log, enemies, party)
    if mode == "fire":
        target.life = max(0, target.life - 2)
        log.append(f"Water Jet inflicts 2 damage on {target.name}.")
    elif mode == "vermin":
        dispersed = min(2, sum(1 for enemy in enemies if enemy.category == "vermin" and enemy.life > 0))
        remaining = dispersed
        for enemy in enemies:
            if remaining <= 0:
                break
            if enemy.category == "vermin" and enemy.life > 0:
                enemy.life = 0
                remaining -= 1
        log.append(f"Water Jet disperses {dispersed} vermin.")
    elif mode == "minion":
        target.life = 0
        log.append(f"Water Jet knocks out {target.name}.")
    else:
        log.append("Water Jet distracts the Major Foe; the party can flee from this combat without being attacked.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over, flee_bonus=(mode == "distract"))


def _cast_bear_form(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
) -> SpellOutcome:
    if "Bear Form" in caster.statuses:
        log.append(f"{caster.name} is already in bear form.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    pre_life = caster.current_life
    caster.statuses.append("Bear Form")
    caster.current_life = 8
    log.append(
        f"{caster.name} becomes a bear (8 Life, attacks as warrior L{caster.level}) until combat ends."
    )
    return SpellOutcome(
        log,
        enemies,
        party,
        spell_consumed=True,
        bear_form=True,
        bear_form_pre_life=pre_life,
    )


def _cast_warp_wood(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    door_type: str | None,
) -> SpellOutcome:
    if door_type in {"locked", "lever", "unlocked", "trap_door"}:
        log.append("Warp Wood destroys the wooden door.")
        return SpellOutcome(log, enemies, party, spell_consumed=True, destroy_door=True)
    wood_foes = [
        enemy
        for enemy in enemies
        if enemy.life > 0
        and (
            any(tag in WOOD_FOE_TAGS for tag in enemy.tags)
            or "tree" in enemy.name.lower()
            or "wood" in enemy.name.lower()
            or "dryad" in enemy.name.lower()
        )
    ]
    if wood_foes:
        target = wood_foes[0]
        target.life = max(0, target.life - 2)
        log.append(f"Warp Wood inflicts 2 damage on {target.name}.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    log.append("Warp Wood has no wooden target here.")
    return SpellOutcome(log, enemies, party, spell_consumed=False)


def _cast_barkskin(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    target_character_id: str | None,
    log: list[str],
) -> SpellOutcome:
    target = _pick_target(party, target_character_id) or caster
    if "Barkskin" not in target.statuses:
        target.statuses.append("Barkskin")
    log.append(f"{target.name} gains Barkskin (+2 Defense until combat ends).")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_spiderweb(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    label: str,
) -> SpellOutcome:
    if not enemies:
        log.append(f"{label} has no targets.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    entangled = 0
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        if enemy.category == "vermin" or any(tag in {"fire", "spider", "elemental"} for tag in enemy.tags):
            continue
        enemy.level = max(1, enemy.level - 1)
        if "Webbed" not in enemy.tags:
            enemy.tags.append("Webbed")
        entangled += 1
        if enemy.category != "vermin" and enemy.category != "minions":
            break
        if entangled >= roll_d6():
            break
    log.append(f"{label} entangles {entangled} foe(s) (-1 effective L this encounter).")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_illusionary_armor(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
) -> SpellOutcome:
    if "Illusionary Armor" not in caster.statuses:
        caster.statuses.append("Illusionary Armor")
    log.append(f"{caster.name} gains Illusionary Armor (+L Defense vs non-illusion-immune foes).")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_mirror_image(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
) -> SpellOutcome:
    images = caster.level + 1
    caster.statuses.append(f"Mirror Image x{images}")
    log.append(f"{images} mirror images appear around {caster.name}.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_disbelief(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
) -> SpellOutcome:
    for member in party:
        member.statuses = [item for item in member.statuses if "illusion" not in item.lower() and "mirror" not in item.lower()]
    revealed = 0
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        if "invisible" in enemy.tags or "illusion" in enemy.tags:
            enemy.level = max(1, enemy.level - 2)
            enemy.tags = [tag for tag in enemy.tags if tag not in {"invisible", "illusion"}]
            revealed += 1
    log.append(f"Disbelief dispels illusions and reveals {revealed} hidden foe(s).")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_phantasmal_binding(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_foe_id: str | None = None,
) -> SpellOutcome:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        log.append("Phantasmal Binding has no target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = next((enemy for enemy in living if enemy.id == target_foe_id), living[0])
    if _foe_immune_to_illusions(target):
        log.append("Phantasmal Binding has no effect on this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log, _ = spell_hits(caster, target, show_rolls=show_rolls, label="Phantasmal Binding")
    log.extend(hit_log)
    if not hit:
        log.append("Phantasmal Binding fails.")
        return SpellOutcome(log, enemies, party)
    target.tags.append("Held")
    target.level = max(1, target.level - 1)
    log.append(f"{target.name} is held by phantasmal chains for {caster.level} turns (+2 to hit; subdual).")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_shadow_strike(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
) -> SpellOutcome:
    if not enemies:
        log.append("Shadow Strike has no target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = enemies[0]
    if _foe_immune_to_illusions(target):
        log.append("Shadow Strike cannot harm this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log, connect_total, _ = resolve_spell_effect(
        caster, target, show_rolls=show_rolls, label="Shadow Strike"
    )
    log.extend(hit_log)
    if not hit:
        return SpellOutcome(log, enemies, party)
    damage = max(1, connect_total - target.level + 1)
    target.life = max(0, target.life - damage)
    log.append(f"Shadow Strike inflicts {damage} subdual damage on {target.name}.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_specter_swarm(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
) -> SpellOutcome:
    if "Specter Swarm" in caster.statuses:
        log.append("Specter Swarm is already active.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    caster.statuses.append("Specter Swarm")
    affected = 0
    for enemy in enemies:
        if enemy.life <= 0 or _foe_immune_to_illusions(enemy):
            continue
        roll = roll_d6()
        if show_rolls:
            log.append(f"{enemy.name} Morale vs specters: d6 = {roll}.")
        if roll <= 3:
            enemy.tags.append("Specter Distracted")
            affected += 1
    log.append(f"Specter Swarm distracts {affected} foe(s) from attacking {caster.name}.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_mirage_of_fortune(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
) -> SpellOutcome:
    if not enemies:
        log.append("Mirage of Fortune has no audience.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = enemies[0]
    if _foe_immune_to_illusions(target):
        log.append("Mirage of Fortune fails against this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log, _ = spell_hits(caster, target, show_rolls=show_rolls, label="Mirage of Fortune")
    log.extend(hit_log)
    if not hit:
        log.append("Mirage of Fortune fails.")
        return SpellOutcome(log, enemies, party)
    log.append("The foes accept the illusory treasure as a bribe.")
    return SpellOutcome(log, enemies, party, spell_consumed=True, combat_over=True, peaceful_bribe=True)


def spellcasting_roll_vs_level(
    caster: PartyMemberState,
    target_level: int,
    *,
    show_rolls: bool,
    label: str,
    modifier_override: int | None = None,
) -> tuple[bool, list[str]]:
    total, rolls = roll_exploding_for_level(caster)
    modifier = spellcasting_modifier(caster) if modifier_override is None else modifier_override
    modifier += eldritch_aim_bonus(caster)
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {caster.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{target_level}."
        )
    if rolls[0] == 1 and label.lower().startswith("sealed"):
        log.append("Magic feedback! The caster takes 2 damage.")
    return final_total >= target_level, log
