from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState
from .combat import attack_damage, living_party
from .combat_modifiers import (
    enemy_has_magic_resistance,
    enemy_magic_resist_bonus,
    resolve_spell_effect,
    spell_mr_penetration_level,
    spell_target_level,
    spellcasting_modifier,
)
from .dice import roll_d6, roll_exploding_d6


SLEEP_IMMUNE_TAGS = {"undead", "dragon", "artificial", "clockwork", "elemental", "spirit", "construct"}
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
    destroy_door: bool = False
    summon_beast: bool = False
    subdual_penalty_ignored: bool = False
    illusionary_fog: bool = False
    peaceful_bribe: bool = False
    flee_bonus: bool = False
    illusionary_servant: bool = False


def normalize_spell_name(name: str) -> str:
    return name.strip().lower().replace("'", "").replace(" ", "_")


def knows_spell(member: PartyMemberState, spell_name: str) -> bool:
    target = normalize_spell_name(spell_name)
    return any(normalize_spell_name(item) == target or target in normalize_spell_name(item) for item in member.spells)


def is_spell_expended(
    spell_name: str,
    *,
    expended_spells: list[str] | None = None,
    healing_prayer_uses: int = 0,
) -> bool:
    key = normalize_spell_name(spell_name)
    if key in REPEATABLE_PRAYERS:
        return healing_prayer_uses >= HEALING_PRAYER_USES_PER_ADVENTURE
    expended = {normalize_spell_name(item) for item in expended_spells or []}
    return key in expended


def can_cast_spell(
    member: PartyMemberState,
    spell_name: str,
    *,
    expended_spells: list[str] | None = None,
    healing_prayer_uses: int = 0,
) -> bool:
    if not knows_spell(member, spell_name):
        return False
    return not is_spell_expended(
        spell_name,
        expended_spells=expended_spells,
        healing_prayer_uses=healing_prayer_uses,
    )


def mark_spell_expended(
    spell_name: str,
    *,
    expended_spells: list[str],
    healing_prayer_uses: int,
) -> tuple[list[str], int, list[str]]:
    log: list[str] = []
    key = normalize_spell_name(spell_name)
    if key in REPEATABLE_PRAYERS:
        healing_prayer_uses += 1
        remaining = HEALING_PRAYER_USES_PER_ADVENTURE - healing_prayer_uses
        if remaining > 0:
            log.append(f"Healing prayer used ({healing_prayer_uses}/{HEALING_PRAYER_USES_PER_ADVENTURE} this adventure).")
        else:
            log.append(f"Healing prayer used ({HEALING_PRAYER_USES_PER_ADVENTURE}/{HEALING_PRAYER_USES_PER_ADVENTURE} this adventure).")
        return expended_spells, healing_prayer_uses, log
    if key not in {normalize_spell_name(item) for item in expended_spells}:
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
) -> tuple[bool, list[str]]:
    hit, log, _ = resolve_spell_effect(
        member,
        enemy,
        show_rolls=show_rolls,
        label=label,
        modifier_override=modifier_override,
    )
    return hit, log


def resolve_spell_cast(
    spell_name: str,
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    target_character_id: str | None = None,
    show_rolls: bool = True,
    indoors: bool = True,
    outdoors: bool = False,
    door_type: str | None = None,
    from_scroll: bool = False,
) -> SpellOutcome:
    key = normalize_spell_name(spell_name)
    log: list[str] = [f"{caster.name} casts {spell_name}." + (" (from scroll)" if from_scroll else "")]
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if key in {"fireball", "fire_ball"}:
        outcome = _cast_fireball(caster, party, living_enemies, log, show_rolls=show_rolls)
        if door_type == "iron" and not living_enemies:
            outcome.destroy_door = True
            outcome.spell_consumed = True
            outcome.log.append("Fireball destroys the iron door.")
        return outcome
    if key == "lightning":
        outcome = _cast_lightning(caster, party, living_enemies, log, show_rolls=show_rolls)
        if door_type == "iron" and not living_enemies:
            outcome.destroy_door = True
            outcome.spell_consumed = True
            outcome.log.append("Lightning destroys the iron door.")
        return outcome
    if key == "sleep":
        return _cast_sleep(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "protection":
        return _cast_protection(caster, party, living_enemies, target_character_id, log)
    if key == "blessing":
        return _cast_blessing(caster, party, living_enemies, target_character_id, log)
    if key in {"healing_prayer", "healing"}:
        return _cast_healing_prayer(caster, party, living_enemies, target_character_id, log, show_rolls=show_rolls)
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
        log.append("A summoned beast joins the fight (5 Life, 1 damage per round).")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True, summon_beast=True)
    if key == "water_jet":
        return _cast_water_jet(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "bear_form":
        return _cast_bear_form(caster, party, living_enemies, log)
    if key == "warp_wood":
        return _cast_warp_wood(caster, party, living_enemies, log, door_type=door_type)
    if key == "barkskin":
        return _cast_barkskin(caster, party, living_enemies, target_character_id, log)
    if key == "lightning_strike":
        if indoors and not outdoors:
            log.append("Lightning Strike cannot be used indoors.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        return _cast_lightning(caster, party, living_enemies, log, show_rolls=show_rolls, label="Lightning Strike")
    if key in {"spiderweb", "entangle"}:
        if key == "entangle" and indoors and not outdoors:
            log.append("Entangle requires forest, swamp, or jungle terrain.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        return _cast_spiderweb(caster, party, living_enemies, log, label=spell_name)
    if key == "subdual":
        log.append("All allies ignore the -1 subdual attack penalty until combat ends.")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True, subdual_penalty_ignored=True)
    if key == "forest_pathway":
        if indoors and not outdoors:
            log.append("Forest Pathway works only outdoors in woodland.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        log.append("Vegetation parts for the party to pass (10 minutes × druid level).")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True)
    if key == "alter_weather":
        if indoors and not outdoors:
            log.append("Alter Weather works only outdoors.")
            return SpellOutcome(log, living_enemies, party, spell_consumed=False)
        log.append("Weather shifts for 10 minutes; ranged attacks at -1, druid Lightning Strike at +1.")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True)
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
        return _cast_phantasmal_binding(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "illusionary_fog":
        log.append("Illusionary fog surrounds the party; ranged/gaze attacks suspended, +2 Defense when fleeing.")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True, illusionary_fog=True, flee_bonus=True)
    if key == "glamour_mask":
        log.append("Glamour Mask alters appearance for level hours (reroll one Reaction or social Save).")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True)
    if key == "shadow_strike":
        return _cast_shadow_strike(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "specter_swarm":
        return _cast_specter_swarm(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "mirage_of_fortune":
        return _cast_mirage_of_fortune(caster, party, living_enemies, log, show_rolls=show_rolls)
    if key == "illusionary_banquet":
        log.append(f"Illusionary Banquet creates {caster.level + 3} illusionary food rations.")
        return SpellOutcome(log, living_enemies, party, spell_consumed=True)
    if key == "illusionary_sword":
        target = caster
        if "Illusionary Sword" not in target.statuses:
            target.statuses.append(f"Illusionary Sword ({caster.level + 3} turns)")
        log.append(f"{target.name} wields an illusionary sword (+L Attack, subdual) for {caster.level + 3} turns.")
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
    hit, hit_log, final_total = resolve_spell_effect(
        caster, target, show_rolls=show_rolls, label="Fireball"
    )
    log.extend(hit_log)
    if not hit:
        return SpellOutcome(log, enemies, party)
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        capacity = max(1, final_total - target.level)
        kill_capacity = capacity
        slain = 0
        for enemy in enemies:
            if kill_capacity <= 0:
                break
            if enemy.life <= 1 and enemy.category in {"vermin", "minions"} and enemy.life > 0:
                enemy.life = 0
                kill_capacity -= 1
                slain += 1
                log.append(f"Fireball slays {enemy.name}.")
        remaining = sum(1 for enemy in enemies if enemy.life > 0)
        log.append(
            f"Fireball kills up to {capacity} minion(s) at 1 Life; "
            f"{slain} slain{f'; {remaining} foe(s) remain' if remaining else ''}."
        )
    else:
        target.life -= 1
        log.append(f"Fireball hits {target.name} for 1 damage.")
        if target.life <= target.max_life // 2 and target.max_life > 1:
            target.level = max(1, target.level - 1)
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
) -> SpellOutcome:
    if not enemies:
        log.append(f"There are no targets for {label}.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = enemies[0]
    if "elemental" in target.tags and "lightning" in target.name.lower():
        log.append(f"{label} has no effect on this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log = spell_hits(caster, target, show_rolls=show_rolls, label=label)
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
    *,
    show_rolls: bool = True,
) -> SpellOutcome:
    target = _pick_target(party, target_character_id) or caster
    if target.current_life >= target.max_life:
        log.append(f"{target.name} is already at full Life.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    total, rolls = roll_exploding_d6()
    modifier = spellcasting_modifier(caster)
    healed = total + modifier
    if show_rolls:
        log.append(
            f"Healing prayer: {' + '.join(str(value) for value in rolls)} + {modifier} = {healed} Life restored."
        )
    target.current_life = min(target.max_life, target.current_life + max(1, healed))
    log.append(f"Healing prayer restores {max(1, healed)} Life to {target.name}.")
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
    modifier = spellcasting_modifier(caster) * 2
    hit, hit_log = spell_hits(caster, target, show_rolls=show_rolls, label="Disperse Vermin", modifier_override=modifier)
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
) -> SpellOutcome:
    if not enemies:
        log.append("Water Jet can provide water for the party today.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    target = enemies[0]
    hit, hit_log = spell_hits(caster, target, show_rolls=show_rolls, label="Water Jet")
    log.extend(hit_log)
    if not hit:
        log.append("Water Jet misses.")
        return SpellOutcome(log, enemies, party)
    if "fire" in target.tags or "fire" in target.name.lower():
        target.life = max(0, target.life - 2)
        log.append(f"Water Jet inflicts 2 damage on {target.name}.")
    elif target.category == "vermin":
        dispersed = min(2, sum(1 for enemy in enemies if enemy.category == "vermin" and enemy.life > 0))
        remaining = dispersed
        for enemy in enemies:
            if remaining <= 0:
                break
            if enemy.category == "vermin" and enemy.life > 0:
                enemy.life = 0
                remaining -= 1
        log.append(f"Water Jet disperses {dispersed} vermin.")
    elif target.category == "minions" and target.life <= 1:
        target.life = 0
        log.append(f"Water Jet knocks out {target.name}.")
    else:
        log.append("Water Jet distracts the foe; the party could flee without pursuit.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over, flee_bonus=True)


def _cast_bear_form(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
) -> SpellOutcome:
    if "Bear Form" in caster.statuses:
        log.append(f"{caster.name} is already in bear form.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    caster.statuses.append("Bear Form")
    bear_life = max(8, caster.current_life)
    caster.current_life = min(bear_life, caster.max_life + 5)
    log.append(f"{caster.name} becomes a bear (8 Life, fights as warrior L{caster.level}) until combat ends.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


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
) -> SpellOutcome:
    if not enemies:
        log.append("Phantasmal Binding has no target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = enemies[0]
    if _foe_immune_to_illusions(target):
        log.append("Phantasmal Binding has no effect on this foe.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log = spell_hits(caster, target, show_rolls=show_rolls, label="Phantasmal Binding")
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
    hit, hit_log, connect_total = resolve_spell_effect(
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
    hit, hit_log = spell_hits(caster, target, show_rolls=show_rolls, label="Mirage of Fortune")
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
    total, rolls = roll_exploding_d6()
    modifier = spellcasting_modifier(caster) if modifier_override is None else modifier_override
    final_total = total + modifier
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {caster.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total} vs L{target_level}."
        )
    if rolls[0] == 1 and label.lower().startswith("sealed"):
        log.append("Magic feedback! The caster takes 2 damage.")
    return final_total >= target_level, log
