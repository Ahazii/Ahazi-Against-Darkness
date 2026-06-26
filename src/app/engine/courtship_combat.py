"""Courtship of Flower Demons — foe-specific combat rules (TCOTFD p.64–68)."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_d6, roll_exploding_for_level
from .class_combat import save_modifier

if TYPE_CHECKING:
    from .combat import CombatContext

COURTSHIP_PARALYZED = "Paralyzed (Blessing cures)"
COURTSHIP_POISON_NAILS = "Poisoned nails (Queen's Maids)"
COURTSHIP_CANNOT_FLEE = "Cannot flee (Maypole)"
COURTSHIP_ATTACK_PENALTY = "Courtship mesmerize penalty"
COURTSHIP_DRY_PLAGUE = "Dark Plague (Courtship)"


def _courtship_template(enemy: EnemyState) -> str:
    for tag in enemy.tags:
        if str(tag).startswith("courtship:"):
            return str(tag).split(":", 1)[1]
    return enemy.name


def _living(party: list[PartyMemberState]) -> list[PartyMemberState]:
    return [member for member in party if member.current_life > 0]


def _hcl(party: list[PartyMemberState]) -> int:
    return max((member.level for member in party if member.current_life > 0), default=1)


def _poison_save(
    member: PartyMemberState,
    level: int,
    *,
    label: str,
    show_rolls: bool,
    session: SessionState | None = None,
    bonus: int = 0,
) -> tuple[bool, list[str]]:
    from .combat_modifiers import poison_save_succeeds

    modifier = save_modifier(member, trap=True) + bonus
    if member.class_id.lower() in {"halfling", "druid"}:
        modifier += member.level * (2 if member.class_id.lower() == "druid" else 1)
    elif member.class_id.lower() != "elf":
        modifier += member.level
    total, rolls = roll_exploding_for_level(member)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs L{level}."
        )
    ok = poison_save_succeeds(rolls, total + modifier, level)
    log.append(f"{member.name} {'passes' if ok else 'fails'} the {label}.")
    return ok, log


def apply_courtship_spawn_adjustments(
    session: SessionState,
    enemies: list[EnemyState],
    *,
    hcl: int,
    show_rolls: bool,
) -> None:
    living_count = len(_living(session.party))
    for enemy in enemies:
        template = _courtship_template(enemy)
        enemy.tags.append(f"courtship:{template}")
        if template == "Corrosive Shrub":
            enemy.attacks = max(1, living_count)
            enemy.tags.append("courtship_no_damage")
            enemy.tags.append("mesmerize_plus_2")
        elif template == "Dryads":
            enemy.attacks = 2
        elif template == "Mistress of Black Lashes":
            enemy.tags.append("courtship_disarm_whip")
        elif template == "Death Orchid":
            enemy.attacks = 3
            enemy.tags.append("courtship_orchid_seeds")
        elif template == "Matron of Summer":
            enemy.attacks = 4
        elif template == "Queen's Maids":
            enemy.tags.append("courtship_poison_nails")
        elif template == "Queen's Handmaidens":
            enemy.tags.append("courtship_blur_ranged")
            enemy.tags.append("courtship_spoil_ingredients")
        elif template == "Damsel of Teeming Roses":
            enemy.tags.append("courtship_thorn_retaliation")
        elif template == "Giant Sundew":
            enemy.tags.append("courtship_sundew_paralysis")
        elif template == "Stone Fiends":
            enemy.tags.append("immune_slashing")
        elif template == "Stone Roper":
            enemy.tags.append("courtship_roper_tendril")
        elif template == "Necrogaunt":
            enemy.tags.append("courtship_necrogaunt")
        elif template == "Baobhan Sith":
            enemy.tags.append("courtship_baobhan")
        if show_rolls and template:
            session.log.append(f"Courtship foe: {template} (TCOTFD combat rules active).")


def apply_courtship_combat_start(
    session: SessionState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool,
) -> list[str]:
    if not session.courtship_demesne_active:
        return []
    log: list[str] = []
    pending = session.courtship_combat_entry
    if pending:
        from .courtship_book_of_secrets import apply_book_of_secrets_combat_entry

        log.extend(apply_book_of_secrets_combat_entry(session, party, enemies, pending, show_rolls=show_rolls))
        session.courtship_combat_entry = None
    for enemy in enemies:
        if enemy.life <= 0:
            continue
        if "courtship_baobhan" in enemy.tags:
            for member in _living(party):
                ok, save_log = _mesmerize_save(member, 4, show_rolls=show_rolls, label="Baobhan Sith gaze")
                log.extend(save_log)
                if not ok:
                    member.statuses.append(COURTSHIP_PARALYZED)
                    log.append(f"{member.name} is paralyzed for d3 turns by the Baobhan Sith (TCOTFD).")
    return log


def _mesmerize_save(
    member: PartyMemberState,
    level: int,
    *,
    label: str,
    show_rolls: bool,
    bonus: int = 0,
) -> tuple[bool, list[str]]:
    from .dice import roll_exploding_for_level

    modifier = save_modifier(member, trap=False) + bonus + 2
    total, rolls = roll_exploding_for_level(member)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs L{level}."
        )
    ok = rolls[0] != 1 and total + modifier >= level
    log.append(f"{member.name} {'resists' if ok else 'succumbs to'} {label}.")
    return ok, log


def apply_courtship_per_turn(
    session: SessionState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool,
) -> list[str]:
    if not session.courtship_demesne_active:
        return []
    log: list[str] = []
    hcl = _hcl(party)
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if any(_courtship_template(enemy) == "Giant Purple Pitcherplant" for enemy in living_enemies):
        for member in _living(party):
            if member.current_life < member.max_life:
                member.current_life = max(0, member.current_life - 1)
                log.append(f"{member.name} loses 1 Life to pitcherplant ichor at round start (TCOTFD).")
    for enemy in living_enemies:
        if "courtship_orchid_seeds" not in enemy.tags:
            continue
        roll = roll_d6()
        if show_rolls:
            log.append(f"Death Orchid d6 = {roll} (1–2 seeds, TCOTFD).")
        if roll > 2:
            continue
        for member in _living(party):
            ok, save_log = _poison_save(
                member,
                hcl + 3,
                label="Death Orchid seeds",
                show_rolls=show_rolls,
                session=session,
            )
            log.extend(save_log)
            if not ok and COURTSHIP_DRY_PLAGUE not in member.statuses:
                member.statuses.append(COURTSHIP_DRY_PLAGUE)
                log.append(f"{member.name} is infected with Dark Plague (TCOTFD).")
    for member in _living(party):
        if COURTSHIP_PARALYZED in member.statuses:
            log.append(f"{member.name} is paralyzed and cannot act (TCOTFD).")
    matron = next(
        (enemy for enemy in living_enemies if _courtship_template(enemy) == "Matron of Summer"),
        None,
    )
    if matron is not None and session is not None:
        from .party_life import apply_party_life_loss

        front = sorted(
            [member for member in _living(party) if member.marching_order in {1, 2}],
            key=lambda item: item.marching_order,
        )
        for member in front[:2]:
            apply_party_life_loss(session, member, 1)
            log.append(f"{member.name} is lashed by the Matron of Summer (TCOTFD).")
    return log


def courtship_skip_foe_damage(enemy: EnemyState) -> bool:
    return "courtship_no_damage" in enemy.tags


def apply_courtship_on_foe_hit(
    enemy: EnemyState,
    target: PartyMemberState,
    party: list[PartyMemberState],
    *,
    session: SessionState | None,
    show_rolls: bool,
    defense_total: int | None = None,
    defense_rolls: list[int] | None = None,
) -> list[str]:
    if session is None or not session.courtship_demesne_active:
        return []
    log: list[str] = []
    template = _courtship_template(enemy)
    hcl = _hcl(party)

    if template == "Corrosive Shrub" or "courtship_no_damage" in enemy.tags:
        roll = roll_d6()
        if show_rolls:
            log.append(f"Corrosive Shrub d6 = {roll} (TCOTFD).")
        if roll <= 2:
            ok, save_log = _poison_save(target, hcl + 4, label="Corrosive Shrub", show_rolls=show_rolls, session=session)
            log.extend(save_log)
            if not ok and COURTSHIP_PARALYZED not in target.statuses:
                target.statuses.append(COURTSHIP_PARALYZED)
                log.append(f"{target.name} is paralyzed until a Blessing is cast (TCOTFD).")
        else:
            if target.inventory:
                lost = target.inventory.pop(random.randrange(len(target.inventory)))
                log.append(f"{target.name}'s {lost} is destroyed by corrosive sap (TCOTFD).")
            else:
                log.append(f"{target.name} has no gear to destroy (TCOTFD).")
        return log

    if "courtship_sundew_paralysis" in enemy.tags:
        ok, save_log = _poison_save(target, hcl + 4, label="Giant Sundew", show_rolls=show_rolls, session=session)
        log.extend(save_log)
        if not ok and COURTSHIP_PARALYZED not in target.statuses:
            target.statuses.append(COURTSHIP_PARALYZED)
            log.append(f"{target.name} is paralyzed for the combat (Blessing cancels, TCOTFD).")

    if "courtship_disarm_whip" in enemy.tags and defense_total is not None and defense_total < 4:
        for index, item in enumerate(target.inventory):
            lower = item.lower()
            if any(word in lower for word in ("weapon", "bow", "crossbow", "sling", "dagger", "sword", "mace")):
                disarmed = target.inventory.pop(index)
                session.courtship_disarmed_items.setdefault(target.character_id, []).append(disarmed)
                log.append(f"{target.name} is disarmed of {disarmed} by the whip (TCOTFD).")
                break

    if "courtship_poison_nails" in enemy.tags and COURTSHIP_POISON_NAILS not in target.statuses:
        ok, save_log = _poison_save(target, 3, label="Queen's Maids poison", show_rolls=show_rolls, bonus=1 if target.class_id.lower() in {"halfling", "barbarian"} else 0)
        log.extend(save_log)
        if not ok:
            target.statuses.append(COURTSHIP_POISON_NAILS)
            log.append(f"{target.name} is poisoned by the Queen's Maids (TCOTFD).")

    if template == "Mirror Demon" and session.courtship_mirror_first_hit_pending:
        session.courtship_mirror_first_hit_pending = False
        from .courtship_book_of_secrets import apply_book_of_secrets_entry

        log.extend(apply_book_of_secrets_entry(session, 18, party, show_rolls=show_rolls))

    return log


def apply_courtship_on_pc_attack_hit(
    enemy: EnemyState,
    attacker: PartyMemberState,
    *,
    session: SessionState | None,
    attack_total: int,
    show_rolls: bool,
) -> list[str]:
    if session is None or not session.courtship_demesne_active:
        return []
    log: list[str] = []
    if "courtship_thorn_retaliation" in enemy.tags and attack_total > 0:
        wounds = attack_total // 5
        if wounds:
            attacker.current_life = max(0, attacker.current_life - wounds)
            log.append(
                f"{attacker.name} suffers {wounds} Life from thorns (Attack {attack_total}, TCOTFD)."
            )
    if _courtship_template(enemy) == "Queen's Handmaidens" and attack_total > 0 and session is not None:
        session.courtship_handmaiden_blur_cancelled = True
        log.append("Queen's Handmaidens lose their blur as they are struck (TCOTFD).")
    if _courtship_template(enemy) == "Mirror Demon" and session.courtship_mirror_first_hit_pending:
        session.courtship_mirror_first_hit_pending = False
        from .courtship_book_of_secrets import apply_book_of_secrets_entry

        log.extend(apply_book_of_secrets_entry(session, 18, [attacker], show_rolls=show_rolls))
    return log


def maybe_courtship_matron_respawn(
    enemy: EnemyState,
    party: list[PartyMemberState],
    *,
    session: SessionState | None,
    log: list[str],
) -> None:
    if session is None or not session.courtship_demesne_active:
        return
    if enemy.life > 0:
        return
    if _courtship_template(enemy) != "Matron of Summer":
        return
    if session.courtship_matron_respawned:
        return
    hcl = _hcl(party)
    enemy.life = enemy.max_life = max(1, hcl + 6)
    enemy.attacks = 6
    session.courtship_matron_respawned = True
    log.append("The Matron of Summer rises again, furious (+6 reactions, TCOTFD).")


def courtship_restore_disarmed(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    log: list[str] = []
    for member in party:
        items = session.courtship_disarmed_items.pop(member.character_id, [])
        for item in items:
            member.inventory.append(item)
            log.append(f"{member.name} retrieves {item} after combat (TCOTFD).")
    return log


def courtship_attack_penalty(member: PartyMemberState) -> int:
    if COURTSHIP_ATTACK_PENALTY in member.statuses:
        return -1
    if COURTSHIP_POISON_NAILS in member.statuses:
        return 0
    return 0


def courtship_ranged_penalty(session: SessionState) -> int:
    if session.courtship_handmaiden_blur_cancelled:
        return 0
    return -1 if session.courtship_handmaiden_blur_active else 0


def member_cannot_act_courtship(member: PartyMemberState) -> bool:
    return COURTSHIP_PARALYZED in member.statuses


def clear_courtship_combat_statuses(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    log: list[str] = []
    log.extend(courtship_restore_disarmed(session, party))
    for member in party:
        for status in (
            COURTSHIP_PARALYZED,
            COURTSHIP_POISON_NAILS,
            COURTSHIP_CANNOT_FLEE,
            COURTSHIP_ATTACK_PENALTY,
        ):
            if status in member.statuses:
                member.statuses.remove(status)
    session.courtship_handmaiden_blur_active = False
    session.courtship_handmaiden_blur_cancelled = False
    return log
