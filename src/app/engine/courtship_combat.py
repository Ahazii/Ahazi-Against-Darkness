"""Courtship of Flower Demons — foe-specific combat rules (TCOTFD p.64–68)."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from ..schemas import EnemyState, PartyMemberState, SessionState
from .dice import roll_d3, roll_d6, roll_exploding_for_level
from .class_combat import save_modifier

if TYPE_CHECKING:
    from .combat import CombatContext

COURTSHIP_PARALYZED = "Paralyzed (Blessing cures)"
COURTSHIP_POISON_NAILS = "Poisoned nails (Queen's Maids)"
COURTSHIP_CANNOT_FLEE = "Cannot flee (Maypole)"
COURTSHIP_ATTACK_PENALTY = "Courtship mesmerize penalty"
COURTSHIP_DRY_PLAGUE = "Dark Plague (Courtship)"
COURTSHIP_ENTANGLED = "Entangled (Stone Roper tendrils)"
COURTSHIP_SWEPT_AWAY = "Swept away (Necrogaunt)"
COURTSHIP_SKIP_ATTACK = "Skip next attack (Colleen of Lilies)"


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


def _magic_save(
    member: PartyMemberState,
    level: int,
    *,
    label: str,
    show_rolls: bool,
) -> tuple[bool, list[str]]:
    modifier = save_modifier(member, trap=False)
    if member.class_id.lower() in {"wizard", "cambion", "demonologist"}:
        modifier += member.level
    total, rolls = roll_exploding_for_level(member)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs L{level}."
        )
    ok = rolls[0] != 1 and total + modifier >= level
    log.append(f"{member.name} {'passes' if ok else 'fails'} the {label}.")
    return ok, log


def _defense_save(
    member: PartyMemberState,
    level: int,
    *,
    label: str,
    show_rolls: bool,
) -> tuple[bool, list[str]]:
    from .combat_modifiers import defense_succeeds

    modifier = save_modifier(member, trap=False)
    total, rolls = roll_exploding_for_level(member)
    log: list[str] = []
    if show_rolls:
        log.append(
            f"{label}: {member.name} rolls {' + '.join(str(v) for v in rolls)} + {modifier} vs L{level}."
        )
    ok = defense_succeeds(total + modifier, level, natural=rolls[0])
    log.append(f"{member.name} {'resists' if ok else 'fails'} {label}.")
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
            enemy.tags.append("courtship_plant_crushing_penalty")
        elif template == "Venus Flytrap":
            enemy.tags.append("courtship_plant_crushing_penalty")
        elif template in {"Stone Fiend", "Stone Fiends"}:
            enemy.tags.append("courtship_stone_fiend_acid")
            enemy.tags.append("immune_slashing")
        elif template == "Stone Roper":
            enemy.tags.append("courtship_roper_tendril")
        elif template == "Necrogaunt":
            enemy.tags.append("courtship_necrogaunt")
            enemy.tags.append("courtship_no_damage")
        elif template == "Baobhan Sith":
            enemy.tags.append("courtship_baobhan")
            enemy.tags.append("courtship_baobhan_bite")
        elif template == "Lex the Cambion":
            enemy.tags.append("courtship_lex_sleep")
            enemy.tags.append("courtship_lex_insects")
        if show_rolls and template:
            session.log.append(f"Courtship foe: {template} (TCOTFD combat rules active).")


def courtship_lady_flee_before_combat(
    session: SessionState,
    enemies: list[EnemyState],
    *,
    show_rolls: bool,
) -> list[str]:
    """BoS entry 21 — Lady flees combat, leaving illusion doubles (TCOTFD p.57)."""
    log: list[str] = []
    has_lady = any(
        _courtship_template(enemy) == "Lady of Lament" and enemy.life > 0 for enemy in enemies
    )
    has_doubles = any("illusion" in enemy.name.lower() for enemy in enemies if enemy.life > 0)
    if not has_lady or not has_doubles:
        return log
    for enemy in enemies:
        if _courtship_template(enemy) == "Lady of Lament" and "illusion" not in enemy.name.lower():
            enemy.life = 0
            if show_rolls:
                log.append(
                    "The Lady of Lament flees at the first opportunity, leaving her doubles to fight "
                    "(BoS entry 21, TCOTFD)."
                )
            break
    return log


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
    from .courtship_pandora import has_pandora, prepare_pandora_fight

    if has_pandora(session):
        prepare_pandora_fight(session, enemies)
    from .courtship_blossoms_items import apply_satyr_talisman_wounds

    log.extend(apply_satyr_talisman_wounds(session, party, show_rolls=show_rolls))
    log.extend(courtship_lady_flee_before_combat(session, enemies, show_rolls=show_rolls))
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

    from .courtship_blossoms_items import talisman_mesmerize_bonus
    from .courtship_classes import (
        courtship_flower_demon_mesmerize_bonus,
        satyr_auto_fails_mesmerize,
    )

    if member.class_id.lower() == "satyr" and satyr_auto_fails_mesmerize(label):
        log = [
            f"{label}: {member.name} cannot resist a Maiden or Lady (satyr, TCOTFD p.10).",
            f"{member.name} succumbs to {label}.",
        ]
        return False, log

    modifier = (
        save_modifier(member, trap=False)
        + bonus
        + 2
        + talisman_mesmerize_bonus(member)
        + courtship_flower_demon_mesmerize_bonus(member)
    )
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
    roper_alive = any(_courtship_template(enemy) == "Stone Roper" for enemy in living_enemies)
    if roper_alive:
        for member in _living(party):
            if COURTSHIP_ENTANGLED in member.statuses:
                member.current_life = max(0, member.current_life - 1)
                log.append(f"{member.name} loses 1 Life to Stone Roper tendrils (TCOTFD).")
    elif session is not None:
        for member in party:
            if COURTSHIP_ENTANGLED in member.statuses:
                member.statuses.remove(COURTSHIP_ENTANGLED)
    if session is not None and session.courtship_necrogaunt_rescue_active:
        log.extend(finalize_necrogaunt_rescue_window(session, party, living_enemies, show_rolls=show_rolls))
    colleen_alive = any(
        _courtship_template(enemy) == "Colleen of Lilies" for enemy in living_enemies
    )
    if colleen_alive:
        for member in _living(party):
            ok, save_log = _mesmerize_save(
                member,
                4,
                label="Colleen of Lilies",
                show_rolls=show_rolls,
            )
            log.extend(save_log)
            if not ok and COURTSHIP_SKIP_ATTACK not in member.statuses:
                member.statuses.append(COURTSHIP_SKIP_ATTACK)
                log.append(f"{member.name} must skip their next attack (Colleen of Lilies, TCOTFD).")
    return log


def finalize_necrogaunt_rescue_window(
    session: SessionState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool,
) -> list[str]:
    log: list[str] = []
    deadline = session.courtship_necrogaunt_rescue_deadline_round
    if deadline is None or (session.combat_round or 0) < deadline:
        return log
    necrogaunts_alive = any(
        enemy.life > 0 and "courtship_necrogaunt" in enemy.tags for enemy in enemies
    )
    if not necrogaunts_alive:
        for member in party:
            if COURTSHIP_SWEPT_AWAY in member.statuses:
                member.statuses.remove(COURTSHIP_SWEPT_AWAY)
                member.current_life = max(1, member.max_life // 2)
                log.append(f"{member.name} is rescued from the Necrogaunts (TCOTFD).")
        session.courtship_necrogaunt_rescue_active = False
        session.courtship_necrogaunt_rescue_deadline_round = None
        session.courtship_necrogaunt_carried = []
        return log
    for member in party:
        if member.character_id not in session.courtship_necrogaunt_carried:
            continue
        member.current_life = 0
        if COURTSHIP_SWEPT_AWAY in member.statuses:
            member.statuses.remove(COURTSHIP_SWEPT_AWAY)
        log.append(f"{member.name} is lost forever to the Necrogaunts (TCOTFD p.66).")
    session.courtship_necrogaunt_rescue_active = False
    session.courtship_necrogaunt_rescue_deadline_round = None
    session.courtship_necrogaunt_carried = []
    return log


def courtship_clear_entangle_on_escape(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    log: list[str] = []
    cleared = False
    for member in party:
        if COURTSHIP_ENTANGLED in member.statuses:
            member.statuses.remove(COURTSHIP_ENTANGLED)
            cleared = True
    if cleared:
        log.append("Stone Roper tendrils release the party on escape or teleport (TCOTFD p.66).")
    return log


def courtship_after_spell_damage_to_enemy(
    session: SessionState,
    enemy: EnemyState,
    party: list[PartyMemberState],
    *,
    log: list[str] | None = None,
) -> None:
    if _courtship_template(enemy) != "Stone Roper":
        return
    courtship_roper_entangled_life_loss(party, log=log)


def courtship_skip_foe_damage(enemy: EnemyState) -> bool:
    return "courtship_no_damage" in enemy.tags


def _strip_gear_to_acid(
    target: PartyMemberState,
    session: SessionState | None,
    *,
    show_rolls: bool,
    log: list[str],
) -> None:
    """Stone Fiend acid spittle — shield then armour (TCOTFD p.66)."""
    shield_words = ("shield",)
    armor_words = ("armor", "armour", "mail", "plate")
    magic_words = ("magic", "enchanted", "+1", "+2", "+3", "scroll", "wand", "potion")
    for pass_words, label in ((shield_words, "shield"), (armor_words, "armour")):
        for index, item in enumerate(target.inventory):
            lower = item.lower()
            if not any(word in lower for word in pass_words):
                continue
            if any(word in lower for word in magic_words):
                ok, save_log = _poison_save(target, 3, label="Stone Fiend acid (magic gear)", show_rolls=show_rolls)
                log.extend(save_log)
                if ok:
                    log.append(f"{target.name}'s {item} resists the acid (TCOTFD).")
                    break
            lost = target.inventory.pop(index)
            log.append(f"{target.name} loses {lost} to Stone Fiend acid spittle (TCOTFD).")
            break


def courtship_combat_round_start(session: SessionState) -> None:
    session.courtship_necrogaunt_hits = {}
    from .courtship_lex import begin_lex_combat_turn

    begin_lex_combat_turn(session)


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

    if template == "Lex the Cambion":
        if COURTSHIP_SKIP_ATTACK not in target.statuses:
            target.statuses.append(COURTSHIP_SKIP_ATTACK)
            log.append(
                f"{target.name} falls into magical sleep from Lex's touch — skip the next attack (BoS entry 7, TCOTFD)."
            )
        return log

    if template == "Corrosive Shrub":
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
            from .star_object_curse import removable_inventory_items

            eligible = removable_inventory_items(target.inventory)
            if eligible:
                lost = random.choice(eligible)
                from .item_containers import contained_loss_suffix, remove_inventory_item_with_contents

                _removed, contents = remove_inventory_item_with_contents(target, item_name=lost)
                log.append(
                    f"{target.name}'s {lost}{contained_loss_suffix(contents)} is destroyed by corrosive sap (TCOTFD)."
                )
            else:
                log.append(f"{target.name} has no eligible gear to destroy (TCOTFD; cursed objects remain bound).")
        return log

    if "courtship_necrogaunt" in enemy.tags and session is not None:
        hits = session.courtship_necrogaunt_hits
        hits[target.character_id] = hits.get(target.character_id, 0) + 1
        if hits[target.character_id] >= 2:
            ok, save_log = _defense_save(target, 4, label="Necrogaunt sweep", show_rolls=show_rolls)
            log.extend(save_log)
            if not ok:
                target.current_life = 0
                target.statuses.append(COURTSHIP_SWEPT_AWAY)
                session.courtship_necrogaunt_carried.append(target.character_id)
                session.courtship_necrogaunt_rescue_active = True
                session.courtship_necrogaunt_rescue_deadline_round = (session.combat_round or 0) + 1
                log.append(f"{target.name} is swept away by the Necrogaunts (TCOTFD).")
                log.append(
                    "Rescue window: one combat turn — slay the Necrogaunts with bow, sling, or spell only; "
                    "attack 1 hits the swept hero (TCOTFD p.66)."
                )
            hits[target.character_id] = 0
        return log

    if "courtship_stone_fiend_acid" in enemy.tags:
        _strip_gear_to_acid(target, session, show_rolls=show_rolls, log=log)
        return log

    if "courtship_roper_tendril" in enemy.tags:
        if COURTSHIP_ENTANGLED not in target.statuses:
            target.statuses.append(COURTSHIP_ENTANGLED)
            log.append(f"{target.name} is caught in Stone Roper tendrils (TCOTFD).")
        return log

    if "courtship_baobhan_bite" in enemy.tags:
        ok, save_log = _magic_save(target, 4, label="Baobhan Sith bite", show_rolls=show_rolls)
        log.extend(save_log)
        if not ok:
            target.max_life = max(0, target.max_life - 1)
            target.current_life = min(target.current_life, target.max_life)
            log.append(f"{target.name} loses 1 permanent Life to the Baobhan Sith bite (TCOTFD).")
        return log

    if "courtship_spoil_ingredients" in enemy.tags and defense_rolls and defense_rolls[0] == 1:
        from .courtship_ingredients import spoil_random_ingredients

        spoiled = spoil_random_ingredients(party, roll_d3())
        if spoiled:
            log.append(
                f"Queen's Handmaidens spoil {', '.join(spoiled)} (Defense 1, TCOTFD)."
            )
        else:
            log.append("Queen's Handmaidens find no ingredients to spoil (TCOTFD).")
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


def consume_courtship_skip_attack(member: PartyMemberState) -> bool:
    if COURTSHIP_SKIP_ATTACK not in member.statuses:
        return False
    member.statuses.remove(COURTSHIP_SKIP_ATTACK)
    return True


def courtship_crushing_attack_penalty(enemy: EnemyState, *, crushing: bool) -> int:
    if crushing and "courtship_plant_crushing_penalty" in enemy.tags:
        return -1
    return 0


def courtship_baobhan_iron_bonus(enemy: EnemyState, weapon_item: str | None) -> int:
    if "courtship_baobhan" not in enemy.tags or not weapon_item:
        return 0
    lower = weapon_item.lower()
    if "iron" not in lower:
        return 0
    if any(word in lower for word in ("magic", "enchanted", "+1", "+2", "+3", "silver")):
        return 0
    return 1


def courtship_roper_entangled_life_loss(
    party: list[PartyMemberState],
    *,
    log: list[str] | None = None,
) -> None:
    """Magic attacks on the roper also damage entangled targets (TCOTFD p.66)."""
    for member in _living(party):
        if COURTSHIP_ENTANGLED in member.statuses:
            member.current_life = max(0, member.current_life - 1)
            if log is not None:
                log.append(f"{member.name} takes 1 Life from roper tendril backlash (TCOTFD).")


def clear_courtship_combat_statuses(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    log: list[str] = []
    log.extend(courtship_restore_disarmed(session, party))
    for member in party:
        for status in (
            COURTSHIP_PARALYZED,
            COURTSHIP_POISON_NAILS,
            COURTSHIP_CANNOT_FLEE,
            COURTSHIP_ATTACK_PENALTY,
            COURTSHIP_ENTANGLED,
            COURTSHIP_SWEPT_AWAY,
            COURTSHIP_SKIP_ATTACK,
        ):
            if status in member.statuses:
                member.statuses.remove(status)
    session.courtship_handmaiden_blur_active = False
    session.courtship_handmaiden_blur_cancelled = False
    session.courtship_necrogaunt_hits = {}
    session.courtship_necrogaunt_carried = []
    session.courtship_necrogaunt_rescue_active = False
    session.courtship_necrogaunt_rescue_deadline_round = None
    session.courtship_vault_combat_no_flee = False
    return log


def necrogaunt_rescue_blocks_melee(session: SessionState, *, missile: bool, from_spell: bool) -> bool:
    if not session.courtship_necrogaunt_rescue_active:
        return False
    return not missile and not from_spell


def necrogaunt_rescue_friendly_fire(
    session: SessionState,
    party: list[PartyMemberState],
    attacker: PartyMemberState,
    *,
    natural_one: bool,
    targeting_necrogaunt: bool,
    show_rolls: bool,
) -> list[str]:
    if not session.courtship_necrogaunt_rescue_active or not natural_one or not targeting_necrogaunt:
        return []
    log: list[str] = []
    for carried_id in session.courtship_necrogaunt_carried:
        victim = next((member for member in party if member.character_id == carried_id), None)
        if victim is None or victim.current_life <= 0:
            continue
        victim.current_life = max(0, victim.current_life - 1)
        log.append(
            f"Rescue shot goes wide — {attacker.name}'s attack 1 hits {victim.name} for 1 Life (TCOTFD p.66)."
        )
        break
    return log
