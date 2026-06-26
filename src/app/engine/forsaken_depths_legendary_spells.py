"""Forsaken Depths Legendary spell effects (FD p.47)."""

from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState, SessionState
from .combat import apply_enemy_damage, living_party
from .combat_modifiers import resolve_spell_effect, spellcasting_modifier
from .dice import roll_d6, roll_exploding_for_level
from .experience import tier_for_level
from .madness import apply_madness_gain
from .spells import SpellOutcome, normalize_spell_name
from .subdual import reduce_foe_level


FD_LEGENDARY_SPELL_KEYS = frozenset(
    {
        "contact_forgotten_god",
        "eldritch_storm",
        "illusionary_distractions",
        "furnace_of_the_amulet",
        "blinding_lightning",
        "destroy_invincible_fiend",
    }
)


def is_fd_legendary_spell(spell_name: str) -> bool:
    return normalize_spell_name(spell_name) in FD_LEGENDARY_SPELL_KEYS


def _tier_damage(caster: PartyMemberState) -> int:
    return max(1, tier_for_level(caster.level))


def _pick_foe(enemies: list[EnemyState], foe_id: str | None) -> EnemyState | None:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return None
    if foe_id:
        return next((enemy for enemy in living if enemy.id == foe_id), None)
    return living[0]


def _is_final_boss(enemy: EnemyState, *, final_boss: bool) -> bool:
    if final_boss:
        return True
    return "final_boss" in enemy.tags or enemy.category == "final_boss"


def _is_major_or_minor(enemy: EnemyState) -> bool:
    return enemy.category in {"minions", "vermin", "weird", "boss", "horde"}


def _remove_permanently_lost(session: SessionState | None, character_id: str) -> None:
    if session is None:
        return
    if character_id in session.permanently_lost_character_ids:
        session.permanently_lost_character_ids.remove(character_id)


def _party_has_magic_weapons(party: list[PartyMemberState]) -> bool:
    for member in party:
        for item in member.inventory:
            lower = item.lower()
            if "magic weapon" in lower or lower.startswith("legendary ") and "weapon" in lower:
                return True
    return False


def try_resolve_fd_legendary_spell(
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
    door_type: str | None = None,
    show_rolls: bool = True,
    final_boss: bool = False,
    session: SessionState | None = None,
) -> SpellOutcome | None:
    if spell_key not in FD_LEGENDARY_SPELL_KEYS:
        return None

    living_enemies = [enemy for enemy in enemies if enemy.life > 0]

    if spell_key == "contact_forgotten_god":
        return _cast_contact_forgotten_god(
            caster,
            party,
            living_enemies,
            log,
            session=session,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            final_boss=final_boss,
            show_rolls=show_rolls,
        )
    if spell_key == "eldritch_storm":
        return _cast_eldritch_storm(
            caster,
            party,
            living_enemies,
            log,
            target_foe_id=target_foe_id,
            spell_target_mode=spell_target_mode,
            door_type=door_type,
            session=session,
            show_rolls=show_rolls,
        )
    if spell_key == "illusionary_distractions":
        return _cast_illusionary_distractions(
            caster,
            party,
            living_enemies,
            log,
            spell_target_mode=spell_target_mode,
            session=session,
            show_rolls=show_rolls,
        )
    if spell_key == "furnace_of_the_amulet":
        return _cast_furnace_of_the_amulet(
            caster,
            party,
            living_enemies,
            log,
            target_foe_id=target_foe_id,
            session=session,
            show_rolls=show_rolls,
        )
    if spell_key == "blinding_lightning":
        return _cast_blinding_lightning(
            caster,
            party,
            living_enemies,
            log,
            target_foe_id=target_foe_id,
            session=session,
            show_rolls=show_rolls,
        )
    if spell_key == "destroy_invincible_fiend":
        return _cast_destroy_invincible_fiend(
            caster,
            party,
            living_enemies,
            log,
            target_foe_id=target_foe_id,
            session=session,
            show_rolls=show_rolls,
            final_boss=final_boss,
        )
    return None


def _apply_contact_forgotten_god_cost(
    session: SessionState | None,
    caster: PartyMemberState,
    log: list[str],
    *,
    show_rolls: bool,
) -> None:
    caster.current_life = max(0, caster.current_life - 2)
    if show_rolls:
        log.append(f"{caster.name} loses 2 Life casting Contact Forgotten God ({caster.current_life} remaining, FD p.47).")
    if session is not None:
        log.extend(apply_madness_gain(session, caster, source="Contact Forgotten God"))


def _cast_contact_forgotten_god(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    session: SessionState | None,
    target_character_id: str | None,
    target_foe_id: str | None,
    spell_target_mode: str | None,
    final_boss: bool,
    show_rolls: bool,
) -> SpellOutcome:
    mode = (spell_target_mode or "resurrect").strip().lower()
    _apply_contact_forgotten_god_cost(session, caster, log, show_rolls=show_rolls)
    if mode == "slay_foe":
        target = _pick_foe(enemies, target_foe_id)
        if target is None:
            log.append("Choose a living foe to slay with Contact Forgotten God.")
            return SpellOutcome(log, enemies, party, spell_consumed=False)
        if _is_final_boss(target, final_boss=final_boss):
            log.append("Contact Forgotten God cannot slay a Final Boss (FD p.47).")
            return SpellOutcome(log, enemies, party, spell_consumed=True)
        if not _is_major_or_minor(target):
            log.append("Contact Forgotten God may only slay a minor or Major foe (FD p.47).")
            return SpellOutcome(log, enemies, party, spell_consumed=True)
        target.life = 0
        log.append(f"{target.name} is destroyed — all its treasure is lost (FD p.47).")
        combat_over = not any(enemy.life > 0 for enemy in enemies)
        return SpellOutcome(log, enemies, party, combat_over=combat_over)

    if not target_character_id:
        log.append("Choose which fallen hero to resurrect with Contact Forgotten God.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    target = next((m for m in party if m.character_id == target_character_id), None)
    if target is None or target.current_life > 0:
        log.append("Contact Forgotten God can only resurrect a fallen party member (FD p.47).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if session is not None:
        used = session.fd_contact_forgotten_god_resurrected
        if target.character_id in used:
            log.append(f"{target.name} was already resurrected by Contact Forgotten God once (FD p.47).")
            return SpellOutcome(log, enemies, party, spell_consumed=True)
        used.append(target.character_id)
    tier = tier_for_level(max(m.level for m in living_party(party) if m.current_life > 0) or caster.level)
    min_level = max(1, (tier - 1) * 5 + 1)
    target.level = max(min_level, target.level)
    target.max_life = max(target.max_life, target.level + 4)
    target.current_life = max(1, target.max_life // 2)
    _remove_permanently_lost(session, target.character_id)
    log.append(
        f"{target.name} returns at half Life ({target.current_life}/{target.max_life}) "
        f"at minimum Tier level (FD p.47)."
    )
    return SpellOutcome(log, enemies, party)


def _cast_eldritch_storm(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_foe_id: str | None,
    spell_target_mode: str | None,
    door_type: str | None,
    session: SessionState | None,
    show_rolls: bool,
) -> SpellOutcome:
    mode = (spell_target_mode or "withdraw").strip().lower()
    if mode == "knock_door":
        if door_type and door_type.lower() == "immune_to_magic":
            log.append("This door is immune to magic (FD p.47).")
            return SpellOutcome(log, enemies, party, spell_consumed=True)
        if not enemies and door_type:
            log.append("Eldritch Storm shatters the door (FD p.47).")
            return SpellOutcome(log, enemies, party, spell_consumed=True, destroy_door=True)
        log.append("Eldritch Storm can knock down a door when no foes block the caster (FD p.47).")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if mode == "withdraw":
        log.append("Eldritch Storm covers the party's withdrawal — no foe attacks as you leave (FD p.47).")
        return SpellOutcome(log, enemies, party, spell_consumed=True, flee_bonus=True, combat_over=True)
    target = _pick_foe(enemies, target_foe_id)
    if target is None:
        log.append("Choose a foe to target with Eldritch Storm.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    modifier = spellcasting_modifier(caster)
    if mode == "ranged_plus3":
        modifier += 3
    elif mode == "ranged":
        modifier += caster.level
    hit, hit_log, final_total, _ = resolve_spell_effect(
        caster,
        target,
        show_rolls=show_rolls,
        label="Eldritch Storm",
        modifier_override=modifier,
        session=session,
    )
    log.extend(hit_log)
    if not hit:
        return SpellOutcome(log, enemies, party)
    damage = 1 if mode == "ranged_plus3" else 4
    apply_enemy_damage(target, damage)
    log.append(f"Eldritch Storm hits {target.name} for {damage} damage (FD p.47).")
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_illusionary_distractions(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    spell_target_mode: str | None,
    session: SessionState | None,
    show_rolls: bool,
) -> SpellOutcome:
    mode = (spell_target_mode or "combat").strip().lower()
    if mode == "flee":
        if not enemies:
            log.append("No foes remain — the party withdraws (FD p.47).")
            return SpellOutcome(log, enemies, party, spell_consumed=True, combat_over=True)
        sample = enemies[0]
        hit, hit_log, _, _ = resolve_spell_effect(
            caster,
            sample,
            show_rolls=show_rolls,
            label="Illusionary Distractions (flee)",
            session=session,
        )
        log.extend(hit_log)
        if hit:
            log.append("Illusions cover the retreat — the party flees without attacks (FD p.47).")
            return SpellOutcome(log, enemies, party, spell_consumed=True, flee_bonus=True, combat_over=True)
        log.append("The illusion fails — the party cannot flee safely (FD p.47).")
        return SpellOutcome(log, enemies, party)
    distracted = 0
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        hit, hit_log, _, _ = resolve_spell_effect(
            caster,
            enemy,
            show_rolls=show_rolls,
            label=f"Illusionary Distractions vs {enemy.name}",
            session=session,
        )
        log.extend(hit_log)
        if hit:
            if "illusionary_distracted" not in enemy.tags:
                enemy.tags.append("illusionary_distracted")
            distracted += 1
    if session is not None and distracted:
        session.fd_illusionary_distraction_active = True
    log.append(
        f"Illusionary Distractions enchant {distracted} foe(s) — rogues/assassins gain +L Attack, "
        f"untrained heroes gain +½L until combat ends (FD p.47)."
    )
    return SpellOutcome(log, enemies, party)


def _cast_furnace_of_the_amulet(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_foe_id: str | None,
    session: SessionState | None,
    show_rolls: bool,
) -> SpellOutcome:
    target = _pick_foe(enemies, target_foe_id)
    if target is None:
        log.append("Choose a foe to target with Furnace of the Amulet.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    modifier = spellcasting_modifier(caster)
    hit, hit_log, _, _ = resolve_spell_effect(
        caster,
        target,
        show_rolls=show_rolls,
        label="Furnace of the Amulet",
        modifier_override=modifier,
        session=session,
    )
    log.extend(hit_log)
    if not hit:
        return SpellOutcome(log, enemies, party)
    damage = _tier_damage(caster)
    apply_enemy_damage(target, damage, damage_kind="fire")
    log.append(f"Furnace of the Amulet hits {target.name} for Tier {damage} fire damage (FD p.47).")
    if target.life <= 0 and target.category in {"weird", "boss"}:
        gem = next(
            (
                item
                for member in party
                for item in member.inventory
                if "gem" in item.lower() and any(ch.isdigit() for ch in item)
            ),
            None,
        )
        if gem and session is not None:
            hit2, logs2, _, _ = resolve_spell_effect(
                caster,
                target,
                show_rolls=show_rolls,
                label="Furnace imbue",
                modifier_override=modifier,
                session=session,
            )
            log.extend(logs2)
            if hit2:
                charges = max(1, target.level)
                amulet = f"Legendary Amulet ({charges} charges)"
                caster.inventory.append(amulet)
                log.append(f"Imbued {amulet} from {target.name}'s power (FD p.47).")
            else:
                log.append(f"The gem cracks — worth 50 gp only (FD p.47).")
        elif show_rolls:
            log.append("Major foe slain — a gem worth 200+ gp in pocket is required to imbue an amulet (FD p.47).")
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_blinding_lightning(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_foe_id: str | None,
    session: SessionState | None,
    show_rolls: bool,
) -> SpellOutcome:
    target = _pick_foe(enemies, target_foe_id)
    if target is None:
        log.append("Choose a foe to target with Blinding Lightning.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    modifier = spellcasting_modifier(caster)
    if any(tag in target.tags for tag in ("automaton", "iron", "metal", "clockwork")):
        modifier += 3
        log.append("Blinding Lightning gains +3 vs metallic foe (FD p.47).")
    if "electricity_immune" in target.tags or "lightning_elemental" in target.tags:
        log.append("Blinding Lightning has no effect on this foe (FD p.47).")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    hit, hit_log, _, _ = resolve_spell_effect(
        caster,
        target,
        show_rolls=show_rolls,
        label="Blinding Lightning",
        modifier_override=modifier,
        session=session,
    )
    log.extend(hit_log)
    if not hit:
        return SpellOutcome(log, enemies, party)
    damage = _tier_damage(caster)
    apply_enemy_damage(target, damage, damage_kind="electricity")
    log.append(f"Blinding Lightning hits {target.name} for Tier {damage} damage (FD p.47).")
    blind_immune = any(tag in target.tags for tag in ("blind_immune", "no_eyes", "colossal_worm"))
    if not blind_immune and reduce_foe_level(target, 2):
        log.append(f"{target.name} is blinded — effective Level reduced by 2 (FD p.47).")
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)


def _cast_destroy_invincible_fiend(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_foe_id: str | None,
    session: SessionState | None,
    show_rolls: bool,
    final_boss: bool,
) -> SpellOutcome:
    target = _pick_foe(enemies, target_foe_id)
    if target is None:
        log.append("Choose the invincible foe to target.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    eligible_attacks = target.party_attacks_received >= 12
    magic_only = not _party_has_magic_weapons(party)
    if not eligible_attacks and not magic_only:
        log.append(
            f"Destroy Invincible Fiend requires 12 party attacks aimed at {target.name} "
            f"({target.party_attacks_received} so far) or magic-only weapons (FD p.47)."
        )
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    hit, hit_log, _, _ = resolve_spell_effect(
        caster,
        target,
        show_rolls=show_rolls,
        label="Destroy Invincible Fiend",
        session=session,
    )
    log.extend(hit_log)
    if not hit:
        log.append("Destroy Invincible Fiend fails — no effect (FD p.47).")
        return SpellOutcome(log, enemies, party)
    target.life = 0
    log.append(f"{target.name} is destroyed — all possessions and treasure are lost (FD p.47).")
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over)
