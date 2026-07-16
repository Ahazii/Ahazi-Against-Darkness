"""Template combat_modifiers, special_rules, and vulnerabilities from monsters.json."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..schemas import EnemyState, PartyMemberState, SessionState
from .combat_modifiers import poison_save_succeeds
from .dice import roll_d6
from .expert_skill_effects import expert_morale_modifier
from .magic_weapons import is_magic_weapon
from .monster_template_effects import chance_roll_succeeds, party_hcl, resolve_effect_level
from .weapons import WeaponProfile, _is_skeleton

if TYPE_CHECKING:
    from .combat import CombatContext


ORC_LOOTER_NAME = "Orc Looters"
BLADEMASTER_NAME = "Hobgoblin Blademasters"
FIENDISH_SPIDER_NAME = "Fiendish Spiders"
ARMORED_SKELETON_NAME = "Armored Skeletons"


def template_combat_modifiers(template: dict | None) -> list[dict[str, Any]]:
    if not template:
        return []
    return [dict(mod) for mod in template.get("combat_modifiers", [])]


def template_has_combat_modifier(template: dict | None, modifier_type: str) -> bool:
    wanted = modifier_type.lower()
    return any(str(mod.get("type", "")).lower() == wanted for mod in template_combat_modifiers(template))


def armor_neutralizes_crushing_bonus(template: dict | None) -> bool:
    return template_has_combat_modifier(template, "armor_neutralize_crushing_bonus")


def pc_attack_modifier_from_template(
    weapon: WeaponProfile | None,
    enemy: EnemyState,
    template: dict | None,
    *,
    member: PartyMemberState | None,
) -> tuple[int, list[str]]:
    """Adjust PC attack modifier from foe template vulnerabilities and combat_modifiers."""
    if template is None or weapon is None:
        return 0, []
    adj = 0
    notes: list[str] = []
    for vuln in template.get("vulnerabilities", []):
        if str(vuln.get("type", "")).lower() != "crushing_weapons" or not weapon.crushing:
            continue
        bonus = int(vuln.get("modifier", 1))
        adj += bonus
        notes.append(f"Effect: crushing weapons gain +{bonus} Attack vs {enemy.name}.")
    for mod in template_combat_modifiers(template):
        mod_type = str(mod.get("type", "")).lower()
        if mod_type == "armor_neutralize_crushing_bonus" and weapon.crushing and _is_skeleton(enemy):
            adj -= 1
            notes.append(f"Effect: {enemy.name}'s armor negates the crushing weapon bonus.")
        elif mod_type == "ranged_penalty":
            weapon_key = str(mod.get("weapon", "")).lower()
            if weapon.kind != "missile":
                continue
            lower = weapon.item.lower()
            if weapon_key == "arrows" and "bow" in lower and "crossbow" not in lower:
                if member is None or any("arrow" in item.lower() for item in member.inventory):
                    penalty = int(mod.get("value", -1))
                    adj += penalty
                    notes.append(f"Effect: arrows hit {enemy.name} at {penalty}.")
    return adj, notes


def armor_deflection_rule(template: dict | None) -> dict[str, Any] | None:
    if not template:
        return None
    for rule in template.get("special_rules", []) or []:
        if str(rule.get("type", "")).lower() == "armor_deflection":
            return dict(rule)
    return None


def armor_deflects_pc_blow(
    enemy: EnemyState,
    weapon: WeaponProfile | None,
    template: dict | None,
    *,
    attack_label: str,
    show_rolls: bool,
) -> tuple[bool, list[str]]:
    rule = armor_deflection_rule(template)
    if rule is None:
        return False, []
    applies_to = str(rule.get("applies_to") or rule.get("source") or "non_magical_attacks").lower()
    if "non_magical" in applies_to and weapon is not None and is_magic_weapon(weapon.item):
        return False, []
    chance = str(rule.get("chance", "1-in-6"))
    deflected, rolled, need, sides = chance_roll_succeeds(chance)
    log: list[str] = []
    if show_rolls:
        log.append(f"{enemy.name} armor deflection: d{sides} = {rolled} (deflects on {need} or less).")
    if deflected:
        log.append(f"{enemy.name}'s armor deflects the non-magical {attack_label}; no damage is dealt.")
    return deflected, log


def foe_frenzy_attack_bonus(
    enemy: EnemyState,
    target: PartyMemberState,
    *,
    lookup_template: Any,
) -> int:
    if target.current_life >= target.max_life:
        return 0
    template = lookup_template(enemy) if lookup_template else None
    for mod in template_combat_modifiers(template):
        if str(mod.get("type", "")).lower() != "frenzy_vs_wounded":
            continue
        return int(mod.get("attack_bonus", 1))
    return 0


def blademaster_riposte_applies(
    enemy: EnemyState,
    *,
    missile: bool,
    first_die: int,
    lookup_template: Any,
) -> bool:
    if missile or first_die != 1 or enemy.life <= 0:
        return False
    if enemy.name != BLADEMASTER_NAME:
        return False
    template = lookup_template(enemy) if lookup_template else None
    for mod in template_combat_modifiers(template):
        if str(mod.get("type", "")).lower() == "riposte":
            return True
    return enemy.name == BLADEMASTER_NAME


def resolve_blademaster_riposte(
    enemy: EnemyState,
    pc: PartyMemberState,
    *,
    party: list[PartyMemberState],
    context: CombatContext,
    show_rolls: bool,
    explain_math: bool,
) -> list[str]:
    from .combat import _resolve_attacks

    if pc.current_life <= 0:
        return []
    log = [f"Effect: {enemy.name} ripostes after {pc.name} rolls a 1 in melee!"]
    attack_log, _paused = _resolve_attacks(
        [(enemy, pc)],
        party=party,
        show_rolls=show_rolls,
        explain_math=explain_math,
        context=context,
    )
    log.extend(attack_log)
    return log


def queue_end_of_combat_poison(
    context: CombatContext,
    target: PartyMemberState,
    save_level: int,
    source: str,
) -> None:
    if context.session is None:
        return
    context.session.pending_end_of_combat_poison.append((target.character_id, save_level, source))


def apply_end_of_combat_poison(
    session: SessionState,
    party: list[PartyMemberState],
    log: list[str],
    *,
    show_rolls: bool,
) -> None:
    if not session.pending_end_of_combat_poison:
        return
    for character_id, save_level, source in session.pending_end_of_combat_poison:
        member = next((item for item in party if item.character_id == character_id), None)
        if member is None or member.current_life <= 0:
            continue
        log.append(f"Event: {member.name} must Save vs. L{save_level} poison from {source} (end of combat).")
        saved, save_log = poison_save_succeeds(
            member,
            save_level,
            show_rolls=show_rolls,
            explain_math=False,
            session=session,
        )
        log.extend(save_log)
        if saved:
            continue
        member.current_life = max(0, member.current_life - 1)
        log.append(f"Effect: {member.name} loses 1 Life from fiendish spider venom.")
        if member.current_life <= 0:
            log.append(f"{member.name} falls.")
    session.pending_end_of_combat_poison.clear()


def tile_has_web_entanglement(enemies: list[EnemyState]) -> bool:
    return any(enemy.life > 0 and enemy.name == FIENDISH_SPIDER_NAME for enemy in enemies)


def withdraw_blocked_by_webs(enemies: list[EnemyState], *, webs_burned: bool) -> bool:
    return tile_has_web_entanglement(enemies) and not webs_burned


def mark_spider_webs_burned(tile, enemies: list[EnemyState] | None = None) -> bool:
    """Mark webs burned when Fireball is cast. Returns True if webs were present."""
    foe_list = enemies if enemies is not None else tile.enemies
    if not tile_has_web_entanglement(foe_list):
        return False
    tile.spider_webs_burned = True
    return True


def _living_orcs(enemies: list[EnemyState]) -> list[EnemyState]:
    return [enemy for enemy in enemies if enemy.life > 0 and enemy.name == ORC_LOOTER_NAME]


def orc_looter_spell_morale_check(
    enemies_before: list[EnemyState],
    enemies_after: list[EnemyState],
    *,
    initial_orc_count: int,
    session: SessionState,
    party: list[PartyMemberState],
    log: list[str],
    show_rolls: bool,
) -> bool:
    """Test morale when spell kills orc looters. Returns True if foes flee."""
    before_orcs = _living_orcs(enemies_before)
    after_orcs = _living_orcs(enemies_after)
    if not before_orcs:
        return False
    killed = len(before_orcs) - len(after_orcs)
    if killed <= 0:
        return False
    if not after_orcs:
        return False
    modifier = 0
    if initial_orc_count > 0 and len(after_orcs) <= initial_orc_count // 2:
        modifier -= 1
        log.append("Orc looters are below half strength from spell casualties (Morale -1).")
    morale_roll = roll_d6() + modifier + expert_morale_modifier(session, party)
    if show_rolls:
        log.append(f"Orc looter spell-casualty Morale roll: d6 = {morale_roll}.")
    if morale_roll <= 3:
        log.append("The remaining orc looters flee after spell casualties.")
        for enemy in enemies_after:
            if enemy.life > 0 and enemy.name == ORC_LOOTER_NAME:
                enemy.life = 0
        return True
    log.append("The orc looters hold their ground.")
    return False


def resolve_on_hit_poison_timing(
    effect: dict[str, Any],
    enemy: EnemyState,
    target: PartyMemberState,
    *,
    context: CombatContext,
    show_rolls: bool,
    explain_math: bool,
    session: SessionState | None,
) -> list[str] | None:
    """Return log lines when poison is deferred to end of combat; None to resolve immediately."""
    timing = str(effect.get("timing", "immediate")).lower()
    if timing not in {"end_of_combat", "end_of_encounter"}:
        return None
    from .monster_template_effects import _immune_to_effect

    if _immune_to_effect(target, effect):
        return [f"{target.name} is immune to {enemy.name}'s poison."]
    save_level = resolve_effect_level(effect.get("save_level"), hcl=party_hcl(context.session.party if context.session else [target]), default=enemy.level)
    queue_end_of_combat_poison(context, target, save_level, enemy.name)
    return [f"Effect: {target.name} must Save vs. L{save_level} poison when combat ends."]


