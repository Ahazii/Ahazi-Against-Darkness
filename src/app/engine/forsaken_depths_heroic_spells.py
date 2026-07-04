"""Forsaken Depths Heroic spell catalog and cast resolver (FD p.19)."""

from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..schemas import EnemyState, HirelingState, PartyMemberState, SessionState
from .combat import apply_enemy_damage, living_party
from .combat_modifiers import resolve_spell_effect, spellcasting_modifier
from .dice import roll_d6, roll_exploding_for_level
from .experience import tier_for_level
from .spells import (
    SpellOutcome,
    _cast_fireball,
    normalize_spell_name,
    spell_hits,
)

UNLIVING_TAGS = frozenset({"undead", "artificial", "elemental", "construct", "clockwork", "spirit"})
INVISIBLE_IMMUNE_TAGS = frozenset({"undead", "artificial", "elemental", "construct", "clockwork"})
ELDRITCH_FIST_MODES = frozenset({"withdraw", "strike", "door", "lift", "grab"})


def _catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "rules" / "heroic_spells.json"


@lru_cache(maxsize=1)
def load_heroic_spells_catalog() -> dict[str, Any]:
    return json.loads(_catalog_path().read_text(encoding="utf-8"))


def heroic_spell_rows() -> list[dict[str, Any]]:
    return [row for row in load_heroic_spells_catalog().get("spells", []) if isinstance(row, dict)]


def heroic_spell_names() -> list[str]:
    return [str(row.get("name", "")).strip() for row in heroic_spell_rows() if row.get("name")]


def heroic_spell_row_for_roll(roll: int) -> dict[str, Any] | None:
    token = str(roll).strip()
    return next((row for row in heroic_spell_rows() if str(row.get("roll", "")).strip() == token), None)


def heroic_spell_name_for_roll(roll: int) -> str:
    row = heroic_spell_row_for_roll(roll)
    if row is None:
        return random_heroic_spell_name()
    return str(row.get("name", "Heroic spell")).strip()


def random_heroic_spell_name() -> str:
    roll = roll_d6()
    return heroic_spell_name_for_roll(roll)


def heroic_spell_id(name: str) -> str:
    token = normalize_spell_name(name)
    for row in heroic_spell_rows():
        if normalize_spell_name(str(row.get("name", ""))) == token:
            return str(row.get("id", token))
    return token


def is_fd_heroic_spell(spell_name: str) -> bool:
    token = normalize_spell_name(spell_name)
    return any(normalize_spell_name(str(row.get("name", ""))) == token for row in heroic_spell_rows())


def _tier(caster: PartyMemberState) -> int:
    return max(1, tier_for_level(caster.level))


def _is_unliving(enemy: EnemyState) -> bool:
    if enemy.category == "undead":
        return True
    return any(tag in UNLIVING_TAGS for tag in enemy.tags)


def _is_chaos_creature(enemy: EnemyState) -> bool:
    if "chaos" in enemy.name.lower():
        return True
    return "chaos" in {tag.lower() for tag in enemy.tags}


def _pick_foe(enemies: list[EnemyState], foe_id: str | None) -> EnemyState | None:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return None
    if foe_id:
        return next((enemy for enemy in living if enemy.id == foe_id), None)
    return living[0]


def try_resolve_fd_heroic_spell(
    spell_key: str,
    spell_name: str,
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_character_id: str | None = None,
    target_foe_id: str | None = None,
    spell_target_mode: str | None = None,
    mass_blessing_target_ids: list[str] | None = None,
    mass_blessing_condition_choices: dict[str, list[str]] | None = None,
    door_type: str | None = None,
    show_rolls: bool = True,
    session: SessionState | None = None,
    from_scroll: bool = False,
) -> SpellOutcome | None:
    if not is_fd_heroic_spell(spell_name):
        return None

    living_enemies = [enemy for enemy in enemies if enemy.life > 0]

    if spell_key == "boatmans_luck":
        return _cast_boatmans_luck(caster, party, living_enemies, log, session=session, show_rolls=show_rolls)
    if spell_key == "eldritch_fist":
        return _cast_eldritch_fist(
            caster,
            party,
            living_enemies,
            log,
            spell_target_mode=spell_target_mode,
            target_foe_id=target_foe_id,
            door_type=door_type,
            session=session,
            show_rolls=show_rolls,
        )
    if spell_key == "mass_blessing":
        return _cast_mass_blessing(
            caster,
            party,
            living_enemies,
            log,
            session=session,
            show_rolls=show_rolls,
            from_scroll=from_scroll,
            target_ids=mass_blessing_target_ids,
            condition_choices=mass_blessing_condition_choices,
        )
    if spell_key == "fire_of_truth":
        return _cast_fire_of_truth(
            caster,
            party,
            living_enemies,
            log,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            session=session,
            show_rolls=show_rolls,
        )
    if spell_key == "teleport_enemy":
        return _cast_teleport_enemy(
            caster,
            party,
            living_enemies,
            log,
            target_foe_id=target_foe_id,
            show_rolls=show_rolls,
            session=session,
        )
    if spell_key == "mass_invisibility":
        return _cast_mass_invisibility(
            caster,
            party,
            living_enemies,
            log,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            show_rolls=show_rolls,
        )
    return None


def _cast_boatmans_luck(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    session: SessionState | None,
    show_rolls: bool,
) -> SpellOutcome:
    if session is None or session.tile_catalog != "forsaken_depths_rivers":
        log.append("Boatman's Luck must be cast while navigating a Forsaken Depths river by boat (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if session.fd_travel_mode != "boat" or session.fd_boat_status == "destroyed":
        log.append("Boatman's Luck requires an intact boat on the underground river (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    session.fd_boatman_luck_active = True
    session.fd_boatman_luck_combat_tier = _tier(caster)
    session.fd_boat_fireproof = True
    log.append(
        "Boatman's Luck protects this boat: the first river hazard is avoided, "
        "and the vessel is fireproof through the River of Flame (FD p.19)."
    )
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _cast_eldritch_fist(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    spell_target_mode: str | None,
    target_foe_id: str | None,
    door_type: str | None,
    session: SessionState | None,
    show_rolls: bool,
) -> SpellOutcome:
    mode = (spell_target_mode or "strike").strip().lower()
    if mode not in ELDRITCH_FIST_MODES:
        log.append("Choose an Eldritch Fist effect: withdraw, strike, door, lift, or grab (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    tier = _tier(caster)

    if mode == "withdraw":
        log.append("Eldritch Fist blocks enemy attacks while the party withdraws from combat (FD p.19).")
        return SpellOutcome(log, enemies, party, combat_over=True, spell_consumed=True)

    if mode == "door":
        if door_type is None:
            log.append("Eldritch Fist can knock down a door when cast on a door exit (FD p.19).")
            return SpellOutcome(log, enemies, party, spell_consumed=False)
        log.append("The Eldritch Fist knocks down the door (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=True, destroy_door=True)

    target = _pick_foe(enemies, target_foe_id)
    if target is None and mode in {"strike", "lift", "grab"}:
        log.append("Choose a living foe for Eldritch Fist (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)

    if mode == "strike" and target is not None:
        modifier = spellcasting_modifier(caster) + caster.level
        hit, hit_log, _, _ = resolve_spell_effect(
            caster,
            target,
            show_rolls=show_rolls,
            label="Eldritch Fist strike",
            modifier_override=modifier,
            session=session,
        )
        log.extend(hit_log)
        if hit:
            apply_enemy_damage(
                target,
                tier,
                damage_kind="normal",
                courtship_spell_session=session,
                courtship_spell_party=party,
                courtship_spell_log=log,
            )
            log.append(f"Eldritch Fist strikes {target.name} for {tier} damage (FD p.19).")
            if target.life <= 0:
                log.append(f"{target.name} is defeated.")
        else:
            log.append("Eldritch Fist misses.")
        combat_over = not any(enemy.life > 0 for enemy in enemies)
        return SpellOutcome(log, enemies, party, combat_over=combat_over, spell_consumed=True)

    if mode == "lift":
        log.append(
            f"Eldritch Fist lifts {target.name if target else 'the target'} across the hazard (FD p.19)."
        )
        return SpellOutcome(log, enemies, party, spell_consumed=True)

    if mode == "grab" and target is not None:
        if session is not None:
            session.fd_eldritch_fist_held_foe_id = target.id
            session.fd_eldritch_fist_tier = tier
        log.append(
            f"Eldritch Fist holds {target.name} — melee attacks against it are at +{tier} until you cast another spell (FD p.19)."
        )
        return SpellOutcome(log, enemies, party, spell_consumed=True)

    return SpellOutcome(log, enemies, party, spell_consumed=False)


def _cast_mass_blessing(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    session: SessionState | None,
    show_rolls: bool,
    from_scroll: bool,
    target_ids: list[str] | None = None,
    condition_choices: dict[str, list[str]] | None = None,
) -> SpellOutcome:
    if caster.class_id.lower() == "elf" and not from_scroll:
        log.append("Elves may not learn Mass Blessing but may cast it from a scroll (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)

    party_targets = [member for member in living_party(party)]
    hireling_targets = [item for item in (session.hirelings if session is not None else []) if item.life > 0]
    selected_ids = set(target_ids or [])
    if selected_ids:
        party_targets = [
            member
            for member in party_targets
            if member.character_id in selected_ids or f"hero:{member.character_id}" in selected_ids
        ]
        hireling_targets = [
            hireling
            for hireling in hireling_targets
            if hireling.id in selected_ids or f"hireling:{hireling.id}" in selected_ids
        ]
    targets = [*party_targets, *hireling_targets]
    if not targets:
        log.append("No one is alive to receive Mass Blessing.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)

    life_cost = max(0, len(targets) - 1)
    condition_plan = _mass_blessing_condition_plan(targets, condition_choices)
    condition_cost = sum(len(items) for items in condition_plan.values())
    life_cost += condition_cost
    if hireling_targets:
        log.append(f"Mass Blessing includes {len(hireling_targets)} hireling(s) (FD p.19).")
    if condition_cost:
        log.append(f"Mass Blessing will remove {condition_cost} chosen condition(s) (FD p.19).")
    if life_cost and caster.current_life <= life_cost:
        log.append(f"{caster.name} needs at least {life_cost + 1} Life to bless everyone (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if life_cost:
        caster.current_life -= life_cost
        log.append(f"{caster.name} loses {life_cost} Life straining to bless {len(targets)} recipients (FD p.19).")

    for target in party_targets:
        _apply_mass_blessing_to_party_target(log, target, session, condition_plan)
    for hireling in hireling_targets:
        _apply_mass_blessing_to_hireling(log, hireling, condition_plan)
    log.append("Mass Blessing completes (FD p.19).")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


BLESSING_STATUS_NAMES = {
    "cursed",
    "fd my fingers are worms",
    "fd no danger here",
    "petrified",
    "slime disease",
}


def _target_choice_ids(target: PartyMemberState | HirelingState) -> set[str]:
    if isinstance(target, HirelingState):
        return {target.id, f"hireling:{target.id}"}
    return {target.character_id, f"hero:{target.character_id}"}


def _mass_blessing_condition_plan(
    targets: list[PartyMemberState | HirelingState],
    choices: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    plan: dict[str, list[str]] = {}
    for target in targets:
        keys = _target_choice_ids(target)
        selected: list[str] = []
        if choices is None:
            selected = _blessing_removable_condition_keys(target)
        else:
            for key in keys:
                selected = list(choices.get(key, []))
                if selected:
                    break
        if selected:
            plan[next(iter(keys))] = selected
    return plan


def _plan_for_target(
    target: PartyMemberState | HirelingState,
    plan: dict[str, list[str]],
) -> list[str]:
    for key in _target_choice_ids(target):
        if key in plan:
            return plan[key]
    return []


def _blessing_removable_condition_keys(target: PartyMemberState | HirelingState) -> list[str]:
    keys: list[str] = []
    from .monster_template_effects import PETRIFIED_STATUS
    from .fungal_traps import cordyceps_infected_turns

    statuses = target.statuses
    for status in statuses:
        lower = status.lower()
        if lower in BLESSING_STATUS_NAMES or status == PETRIFIED_STATUS or lower.startswith("cordyceps infected"):
            keys.append(f"status:{status}")
    if isinstance(target, PartyMemberState) and target.madness > 0:
        keys.append("madness")
    return keys


def _apply_mass_blessing_to_party_target(
    log: list[str],
    target: PartyMemberState,
    session: SessionState | None,
    condition_plan: dict[str, list[str]],
) -> None:
    selected = _plan_for_target(target, condition_plan)
    if not selected:
        log.append(f"Mass Blessing covers {target.name}; no conditions were chosen for removal (FD p.19).")
        return
    _remove_selected_conditions(target, selected, log)
    if "madness" in selected:
        from .madness import heal_madness

        if heal_madness(target, 1):
            log.append(f"Mass Blessing heals 1 Madness from {target.name} (FD p.19).")
    if session is not None and "cavern_water" in selected:
        from .cavern_features import cleanse_cavern_water_contamination

        if cleanse_cavern_water_contamination(session, target.character_id):
            log.append(f"Mass Blessing cleanses contaminated water from {target.name} (FD p.19).")


def _apply_mass_blessing_to_hireling(
    log: list[str],
    hireling: HirelingState,
    condition_plan: dict[str, list[str]],
) -> None:
    selected = _plan_for_target(hireling, condition_plan)
    if selected:
        _remove_selected_conditions(hireling, selected, log)
    else:
        log.append(f"Mass Blessing covers {hireling.name}; no conditions were chosen for removal (FD p.19).")


def _remove_selected_conditions(
    target: PartyMemberState | HirelingState,
    selected: list[str],
    log: list[str],
) -> None:
    removals = {item.removeprefix("status:") for item in selected if item.startswith("status:")}
    if not removals:
        return
    before = list(target.statuses)
    target.statuses = [status for status in target.statuses if status not in removals]
    removed = [status for status in before if status not in target.statuses]
    if removed:
        log.append(f"Mass Blessing removes {', '.join(removed)} from {target.name} (FD p.19).")


def _cast_fire_of_truth(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_foe_id: str | None,
    spell_target_mode: str | None,
    session: SessionState | None,
    show_rolls: bool,
) -> SpellOutcome:
    if not enemies:
        log.append("There are no targets for Fire of Truth.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = _pick_foe(enemies, target_foe_id) or enemies[0]
    if _is_unliving(target):
        log.append(f"Fire of Truth cannot target unliving foes such as {target.name} (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=True)

    chaos_bonus = 1 if _is_chaos_creature(target) else 0
    if chaos_bonus:
        log.append(f"Fire of Truth gains +1 vs chaos creature {target.name} (FD p.19).")

    outcome = _cast_fireball(
        caster,
        party,
        enemies,
        log,
        show_rolls=show_rolls,
        target_foe_id=target.id,
        spell_target_mode=spell_target_mode,
        session=session,
        label="Fire of Truth",
        modifier_bonus=chaos_bonus,
    )
    if not outcome.spell_consumed:
        return outcome

    if target.life <= 0:
        total, rolls = roll_exploding_for_level(caster)
        save_total = total + spellcasting_modifier(caster) + caster.level
        if show_rolls:
            log.append(
                f"Fire of Truth insight: {' + '.join(str(v) for v in rolls)} + L{caster.level} "
                f"= {save_total} vs L{target.level} (FD p.19)."
            )
        if rolls[0] == 1:
            log.append("The dying screams trigger a Wandering Monster roll (FD p.19).")
            if session is not None:
                session.next_wandering_roll_bonus = max(session.next_wandering_roll_bonus, 1)
        elif save_total >= target.level:
            if session is not None:
                session.clues_found += 1
            log.append("Supernatural insight grants 1 Clue (FD p.19).")
        else:
            log.append("Fire of Truth fails to yield insight.")
    return outcome


def _cast_teleport_enemy(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_foe_id: str | None,
    show_rolls: bool,
    session: SessionState | None,
) -> SpellOutcome:
    target = _pick_foe(enemies, target_foe_id)
    if target is None:
        log.append("Choose a foe to teleport away (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    hit, hit_log, _, _ = spell_hits(
        caster,
        target,
        show_rolls=show_rolls,
        label="Teleport Enemy",
        session=None,
    )
    log.extend(hit_log)
    if not hit:
        log.append("Teleport Enemy fails (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    distance = roll_d6()
    if session is not None and session.map_state.current_tile_id:
        from .fd_teleport_enemy import queue_teleport_enemy_return

        queue_teleport_enemy_return(
            session,
            target,
            origin_tile_id=session.map_state.current_tile_id,
            distance=distance,
            log=log,
        )
    target.life = 0
    target.tags = list({*target.tags, "fd_teleported_away"})
    log.append(
        f"{target.name} is teleported {distance} room(s) away into a visited area and leaves this fight (FD p.19)."
    )
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over, spell_consumed=True)


def _cast_mass_invisibility(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_foe_id: str | None,
    spell_target_mode: str | None,
    show_rolls: bool,
) -> SpellOutcome:
    target = _pick_foe(enemies, target_foe_id)
    if target is None:
        log.append("Choose a foe to hide the party from (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if target.category == "final_boss" or "final_boss" in target.tags:
        log.append("Mass Invisibility does not work on Final Bosses (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    if _is_unliving(target) or "magic_immune" in target.tags:
        log.append(f"Mass Invisibility fails against {target.name} (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=True)

    hit, hit_log, _, _ = spell_hits(
        caster,
        target,
        show_rolls=show_rolls,
        label="Mass Invisibility",
    )
    log.extend(hit_log)
    if not hit:
        log.append("Mass Invisibility fails — the foe sees the party (FD p.19).")
        return SpellOutcome(log, enemies, party, spell_consumed=True)

    mode = (spell_target_mode or "skulk").strip().lower()
    if mode == "steal":
        rogue = next(
            (
                member
                for member in living_party(party)
                if member.class_id.lower() == "rogue"
            ),
            None,
        )
        if rogue is None:
            log.append("Mass Invisibility steal requires a living rogue (FD p.19).")
            return SpellOutcome(log, enemies, party, spell_consumed=True)
        from .split_party import stealth_modifier

        roll = roll_d6()
        modifier = stealth_modifier(rogue, None, None) + rogue.level
        total = roll + modifier
        if show_rolls:
            log.append(
                f"{rogue.name} Stealth Save: d6={roll} + L{rogue.level} = {total} vs L{target.level} (FD p.19)."
            )
        if total >= target.level:
            gold = min(rogue.level * 10, rogue.gold + 50)
            rogue.gold += gold
            log.append(f"{rogue.name} steals up to {gold} gp while unseen (FD p.19).")
        else:
            log.append("The theft fails and Mass Invisibility breaks (FD p.19).")
            return SpellOutcome(log, enemies, party, spell_consumed=True)

    log.append("The party fades from the foe's sight and may withdraw unseen (FD p.19).")
    return SpellOutcome(
        log,
        enemies,
        party,
        combat_over=True,
        spell_consumed=True,
        flee_bonus=True,
    )


def clear_eldritch_fist_on_cast(session: SessionState, caster_id: str) -> list[str]:
    if not session.fd_eldritch_fist_held_foe_id:
        return []
    session.fd_eldritch_fist_held_foe_id = None
    session.fd_eldritch_fist_tier = 0
    return ["Eldritch Fist releases its hold when another spell is cast (FD p.19)."]


def fd_boatman_luck_melee_bonus(session: SessionState | None) -> tuple[int, bool]:
    """Return +Tier attack on the first river fight after Boatman's Luck, then consume."""
    if session is None or session.fd_boatman_luck_combat_tier <= 0:
        return 0, False
    from .forsaken_depths_river import session_tile_catalog

    if session_tile_catalog(session) != "forsaken_depths_rivers":
        return 0, False
    tier = session.fd_boatman_luck_combat_tier
    session.fd_boatman_luck_combat_tier = 0
    return tier, True


def fd_eldritch_fist_melee_bonus(session: SessionState | None, foe_id: str) -> int:
    if session is None or session.fd_eldritch_fist_held_foe_id != foe_id:
        return 0
    return max(1, session.fd_eldritch_fist_tier)
