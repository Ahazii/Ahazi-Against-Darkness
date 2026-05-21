from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Callable

from ..schemas import EnemyState, PartyMemberState
from .class_combat import armor_defense_bonus, attack_modifier, defense_modifier, is_hated_by_foes
from .combat_modifiers import (
    apply_poison_status,
    consume_blade_poison,
    consume_mirror_image,
    enemy_has_poison,
    has_blade_poison,
    poison_save_succeeds,
    tick_poisoned_heroes,
)
from .dice import roll_d6, roll_exploding_d6
from .inventory import encumbrance_penalty

from .subdual import apply_subdual_damage, subdue_minor_foe
from .weapons import (
    can_fire_missile,
    select_melee_weapon,
    select_missile_weapon,
    weapon_attack_modifier,
    weapon_label,
)


@dataclass
class CombatContext:
    tile_type: str = "room"
    wandering_ambush: bool = False
    combat_round: int = 1
    cursed_character_id: str | None = None
    wielded_melee: dict[str, str] | None = None
    illusionary_fog_active: bool = False
    subdual_penalty_ignored: bool = False
    body_carrier_id: str | None = None
    rage_attackers: set[str] = field(default_factory=set)
    luck_reroll_attackers: set[str] = field(default_factory=set)
    panache_attack_bonus: set[str] = field(default_factory=set)
    panache_defense_bonus: set[str] = field(default_factory=set)
    on_foe_kill: Callable[[str], None] | None = None
    spend_rage: Callable[[PartyMemberState], bool] | None = None
    spend_luck: Callable[[PartyMemberState], bool] | None = None
    spend_panache: Callable[[PartyMemberState], bool] | None = None


@dataclass
class CombatRound:
    party: list[PartyMemberState]
    enemies: list[EnemyState]
    log: list[str]
    combat_over: bool
    morale_failed: bool = False
    fled: bool = False
    missile_used: set[str] | None = None


def attack_damage(total: int, foe_level: int) -> int:
    if total < foe_level:
        return 0
    return max(1, total // foe_level)


def attack_hits(total: int, foe_level: int) -> bool:
    return total >= foe_level


def defense_succeeds(total: int, foe_level: int, *, natural: int) -> bool:
    if natural == 1:
        return False
    return total > foe_level


def illusionary_sword_turns(member: PartyMemberState) -> int | None:
    for status in member.statuses:
        lower = status.lower()
        if not lower.startswith("illusionary sword"):
            continue
        if "(" in status:
            try:
                return int(status.split("(", 1)[1].split()[0])
            except ValueError:
                pass
        return member.level + 3
    return None


def tick_illusionary_sword_turns(party: list[PartyMemberState]) -> None:
    for member in party:
        new_statuses: list[str] = []
        for status in member.statuses:
            lower = status.lower()
            if not lower.startswith("illusionary sword"):
                new_statuses.append(status)
                continue
            turns = illusionary_sword_turns(member)
            if turns is None:
                continue
            remaining = turns - 1
            if remaining > 0:
                new_statuses.append(f"Illusionary Sword ({remaining} turns)")
        member.statuses = new_statuses


def enemy_has_regeneration(enemy: EnemyState) -> bool:
    return "regeneration" in {tag.lower() for tag in enemy.tags}


def enemy_uses_gaze(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    return "gaze" in tags or "gaze" in enemy.name.lower()


def enemy_is_held(enemy: EnemyState) -> bool:
    return "Held" in enemy.tags or "held" in {tag.lower() for tag in enemy.tags}


def living_party(party: list[PartyMemberState]) -> list[PartyMemberState]:
    return [pc for pc in party if pc.current_life > 0]
    return [pc for pc in party if pc.current_life > 0]


def foe_display_labels(enemies: list[EnemyState]) -> dict[str, str]:
    living = [enemy for enemy in enemies if enemy.life > 0]
    totals: dict[str, int] = {}
    for enemy in living:
        totals[enemy.name] = totals.get(enemy.name, 0) + 1
    seen: dict[str, int] = {}
    labels: dict[str, str] = {}
    for enemy in living:
        if totals[enemy.name] > 1:
            seen[enemy.name] = seen.get(enemy.name, 0) + 1
            labels[enemy.id] = f"{enemy.name} ({seen[enemy.name]})"
        elif enemy.subdued:
            labels[enemy.id] = f"{enemy.name} (subdued)"
        else:
            labels[enemy.id] = enemy.name
    return labels


def sorted_party(party: list[PartyMemberState]) -> list[PartyMemberState]:
    return sorted(living_party(party), key=lambda pc: pc.marching_order)


def select_attack_target(
    pc: PartyMemberState,
    living_enemies: list[EnemyState],
    attack_targets: dict[str, str] | None,
) -> EnemyState:
    if attack_targets and pc.character_id in attack_targets:
        preferred_id = attack_targets[pc.character_id]
        match = next((enemy for enemy in living_enemies if enemy.id == preferred_id), None)
        if match is not None:
            return match
    return living_enemies[0]


def can_melee_attack(member: PartyMemberState, context: CombatContext) -> bool:
    if context.tile_type != "corridor":
        return True
    if context.wandering_ambush:
        return member.marching_order in {3, 4}
    return member.marching_order in {1, 2}


def corridor_defense_positions(context: CombatContext) -> set[int]:
    if context.tile_type != "corridor":
        return {1, 2, 3, 4}
    if context.wandering_ambush:
        return {3, 4}
    return {1, 2}


def assign_enemy_attacks(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    *,
    context: CombatContext,
    once_per_foe: bool = False,
) -> list[tuple[EnemyState, PartyMemberState]]:
    living = sorted_party(party)
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if not living or not living_enemies:
        return []

    attack_pairs: list[tuple[EnemyState, PartyMemberState]] = []
    if context.tile_type == "corridor":
        positions = corridor_defense_positions(context)
        eligible = [pc for pc in living if pc.marching_order in positions] or living[:2]
        attackers = living_enemies[:2]
        for enemy in attackers:
            repeat = 1 if once_per_foe else max(1, enemy.attacks)
            for attack_index in range(repeat):
                target = eligible[attack_index % len(eligible)]
                attack_pairs.append((enemy, target))
        return attack_pairs

    strikes: list[EnemyState] = []
    for enemy in living_enemies:
        repeat = 1 if once_per_foe else max(1, enemy.attacks)
        strikes.extend([enemy] * repeat)

    if len(strikes) <= len(living):
        for index, enemy in enumerate(strikes):
            attack_pairs.append((enemy, living[index % len(living)]))
        return attack_pairs

    targets: list[PartyMemberState] = []
    for pc in living:
        targets.extend([pc] * (len(strikes) // len(living)))
    hated = [pc for pc in living if is_hated_by_foes(pc, living_enemies)]
    pool = hated or living
    while len(targets) < len(strikes):
        targets.append(pool[len(targets) % len(pool)])
    for enemy, target in zip(strikes, targets, strict=False):
        attack_pairs.append((enemy, target))
    return attack_pairs


def assign_flee_attacks(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
) -> list[tuple[EnemyState, PartyMemberState]]:
    living = sorted_party(party)
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if not living or not living_enemies:
        return []
    if len(living_enemies) >= len(living):
        ordered = sorted(living, key=lambda pc: (pc.current_life, pc.marching_order))
        return [(enemy, ordered[index % len(ordered)]) for index, enemy in enumerate(living_enemies)]
    hated = [pc for pc in living if is_hated_by_foes(pc, living_enemies)]
    low_life = sorted(living, key=lambda pc: (pc.current_life, pc.marching_order))
    targets: list[PartyMemberState] = []
    for enemy in living_enemies:
        if low_life:
            targets.append(low_life[0])
        elif hated:
            targets.append(hated[0])
        else:
            targets.append(random.choice(living))
    return list(zip(living_enemies, targets, strict=False))


def _defense_bonus(
    member: PartyMemberState,
    enemy: EnemyState,
    *,
    context: CombatContext,
    withdraw: bool = False,
) -> tuple[int, int]:
    modifier = defense_modifier(member, enemy)
    if member.character_id == context.cursed_character_id:
        modifier -= 1
    include_shield = not (context.wandering_ambush and context.combat_round == 1)
    armor_bonus = armor_defense_bonus(member, include_shield=include_shield)
    if withdraw:
        modifier += 1
    protection_bonus = 1 if any(status.lower() == "protection" for status in member.statuses) else 0
    barkskin_bonus = 2 if any(status.lower() == "barkskin" for status in member.statuses) else 0
    illusion_armor = 0
    if any(status.lower() == "illusionary armor" for status in member.statuses):
        if enemy.category != "vermin" and not any(tag in {"undead", "artificial", "elemental", "construct"} for tag in enemy.tags):
            illusion_armor = member.level
    encumbered = encumbrance_penalty(member)
    return (
        modifier + armor_bonus + protection_bonus + barkskin_bonus + illusion_armor + encumbered,
        armor_bonus,
    )


def _apply_pc_hit(
    pc: PartyMemberState,
    target: EnemyState,
    *,
    final_total: int,
    living_enemies: list[EnemyState],
    log: list[str],
    subdual: bool,
    attack_label: str,
    rage_hit: bool = False,
    on_foe_kill: Callable[[str], None] | None = None,
) -> list[EnemyState]:
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        if subdual:
            subdue_minor_foe(target)
            log.append(f"{pc.name} subdues {target.name} with {attack_label}.")
            return [enemy for enemy in living_enemies if enemy.life > 0]
        kills = attack_damage(final_total, max(1, target.level))
        if rage_hit:
            kills *= 2
            log.append(f"{pc.name}'s rage attack inflicts double damage ({kills} slain).")
        target.life -= kills
        log.append(f"{pc.name} slays {kills} {target.name} with {attack_label}.")
        if target.life <= 0:
            if on_foe_kill is not None:
                on_foe_kill(pc.character_id)
            return [enemy for enemy in living_enemies if enemy.life > 0]
        return living_enemies

    damage = attack_damage(final_total, max(1, target.level))
    if rage_hit:
        damage *= 2
        log.append(f"{pc.name}'s rage attack inflicts double damage ({damage}).")
    if has_blade_poison(pc) and "melee" in attack_label:
        damage += 1
        consume_blade_poison(pc)
        log.append(f"{pc.name}'s blade poison adds 1 damage.")
    if subdual:
        if apply_subdual_damage(target, damage):
            log.append(f"{pc.name} subdues {target.name} with {attack_label}.")
        else:
            log.append(f"{pc.name} hits {target.name} for {damage} subdual damage with {attack_label}.")
        return [enemy for enemy in living_enemies if enemy.life > 0]
    target.life -= damage
    log.append(f"{pc.name} hits {target.name} for {damage} damage with {attack_label}.")
    if target.life <= target.max_life // 2 and target.max_life > 1:
        target.level = max(1, target.level - 1)
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
        if on_foe_kill is not None:
            on_foe_kill(pc.character_id)
        return [enemy for enemy in living_enemies if enemy.life > 0]
    return living_enemies


def _resolve_pc_attack(
    pc: PartyMemberState,
    target: EnemyState,
    *,
    show_rolls: bool,
    explain_math: bool,
    party_attack_bonus: int,
    subdual: bool,
    missile: bool,
    living_enemies: list[EnemyState],
    log: list[str],
    wielded_melee: dict[str, str] | None = None,
    force_unarmed: bool = False,
    context: CombatContext | None = None,
) -> list[EnemyState]:
    context = context or CombatContext()
    wielded = (wielded_melee or {}).get(pc.character_id)
    weapon = (
        select_missile_weapon(pc)
        if missile
        else select_melee_weapon(pc, target, wielded=wielded, force_unarmed=force_unarmed)
    )
    attack_label = f"a {weapon_label(weapon)} {'missile' if missile else 'melee'} attack"
    use_rage = pc.character_id in context.rage_attackers
    use_luck_reroll = pc.character_id in context.luck_reroll_attackers
    use_panache = pc.character_id in context.panache_attack_bonus

    if use_rage and context.spend_rage and not context.spend_rage(pc):
        use_rage = False
        log.append(f"{pc.name} cannot rage (no uses remaining).")
    elif use_rage:
        log.append(f"{pc.name} enters a rage attack (3d6, keep best; double damage on hit).")

    if use_panache and context.spend_panache and not context.spend_panache(pc):
        use_panache = False
        log.append(f"{pc.name} cannot spend Panache (none available).")

    if use_rage:
        from .class_abilities import roll_rage_attack_d6

        total, rolls = roll_rage_attack_d6()
        rage_note = f"rage 3d6 best: {'/'.join(str(value) for value in rolls)} = {total}"
    else:
        total, rolls = roll_exploding_d6()
        rage_note = ""

    modifier = (
        attack_modifier(pc, target)
        + party_attack_bonus
        + weapon_attack_modifier(weapon, target)
        + (2 if enemy_is_held(target) else 0)
        + (pc.level if illusionary_sword_turns(pc) is not None else 0)
        + (1 if use_panache else 0)
    )
    use_subdual = subdual or illusionary_sword_turns(pc) is not None
    final_total = total + modifier
    if show_rolls:
        bonus_note = f" + {party_attack_bonus} flee bonus" if party_attack_bonus else ""
        panache_note = " +1 Panache" if use_panache else ""
        weapon_note = f" ({weapon_label(weapon)}"
        weapon_mod = weapon_attack_modifier(weapon, target)
        if weapon_mod:
            weapon_note += f" {'+' if weapon_mod > 0 else ''}{weapon_mod}"
        weapon_note += ")"
        roll_text = rage_note or " + ".join(str(value) for value in rolls)
        log.append(
            f"{'Missile' if missile else 'Attack'} roll: {pc.name} vs {target.name}: "
            f"{roll_text} + {modifier - party_attack_bonus - (1 if use_panache else 0)}{bonus_note}{panache_note}{weapon_note} = {final_total}."
        )
    if explain_math:
        log.append(f"Attack math: need total >= enemy level {target.level} to hit.")
    if not attack_hits(final_total, target.level):
        if use_luck_reroll and context.spend_luck and context.spend_luck(pc):
            log.append(f"{pc.name} spends 1 Luck point to reroll the attack.")
            total, rolls = roll_exploding_d6()
            final_total = total + modifier
            if show_rolls:
                log.append(
                    f"Luck reroll: {' + '.join(str(value) for value in rolls)} + {modifier - party_attack_bonus - (1 if use_panache else 0)} = {final_total}."
                )
        if not attack_hits(final_total, target.level):
            log.append(f"{pc.name} misses {target.name} with {attack_label}.")
            return living_enemies
    return _apply_pc_hit(
        pc,
        target,
        final_total=final_total,
        living_enemies=living_enemies,
        log=log,
        subdual=use_subdual and not missile,
        attack_label=attack_label,
        rage_hit=use_rage,
        on_foe_kill=context.on_foe_kill,
    )


def _resolve_attacks(
    attack_pairs: list[tuple[EnemyState, PartyMemberState]],
    *,
    show_rolls: bool,
    explain_math: bool,
    context: CombatContext,
    withdraw: bool = False,
    defense_bonus: int = 0,
) -> list[str]:
    log: list[str] = []
    for enemy, target in attack_pairs:
        if target.current_life <= 0:
            continue
        if context.body_carrier_id and target.character_id == context.body_carrier_id:
            if consume_mirror_image(target):
                log.append(f"A mirror image absorbs {enemy.name}'s attack on {target.name}.")
                continue
            target.current_life = max(0, target.current_life - 1)
            log.append(
                f"{target.name} is hit automatically while carrying a fallen comrade ({enemy.name})."
            )
            if target.current_life == 0:
                log.append(f"{target.name} falls.")
            elif enemy_has_poison(enemy):
                saved, poison_log = poison_save_succeeds(
                    target,
                    enemy.level,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
                log.extend(poison_log)
                if not saved:
                    target.current_life = max(0, target.current_life - 1)
                    log.append(f"{target.name} takes 1 extra damage from poison.")
                    if target.current_life == 0:
                        log.append(f"{target.name} falls.")
                    else:
                        apply_poison_status(target, enemy.level)
            continue
        total, rolls = roll_exploding_d6()
        modifier, _ = _defense_bonus(target, enemy, context=context, withdraw=withdraw)
        use_panache = target.character_id in context.panache_defense_bonus
        if use_panache and context.spend_panache and not context.spend_panache(target):
            use_panache = False
        modifier += defense_bonus + (1 if use_panache else 0)
        final_total = total + modifier
        if show_rolls:
            panache_note = " +1 Panache" if use_panache else ""
            log.append(
                f"Defense roll: {target.name} vs {enemy.name}: "
                f"{' + '.join(str(value) for value in rolls)} + {modifier}{panache_note} = {final_total}."
            )
        if explain_math:
            log.append(f"Defense math: need total > enemy level {enemy.level} to avoid damage.")
        if defense_succeeds(final_total, enemy.level, natural=rolls[0]):
            log.append(f"{target.name} defends against {enemy.name}.")
        else:
            if consume_mirror_image(target):
                log.append(f"A mirror image absorbs {enemy.name}'s attack on {target.name}.")
                continue
            target.current_life = max(0, target.current_life - 1)
            log.append(f"{target.name} takes 1 damage from {enemy.name}.")
            if target.current_life == 0:
                log.append(f"{target.name} falls.")
            elif enemy_has_poison(enemy):
                saved, poison_log = poison_save_succeeds(
                    target,
                    enemy.level,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                )
                log.extend(poison_log)
                if not saved:
                    target.current_life = max(0, target.current_life - 1)
                    log.append(f"{target.name} takes 1 extra damage from poison.")
                    if target.current_life == 0:
                        log.append(f"{target.name} falls.")
                    else:
                        apply_poison_status(target, enemy.level)
    return log


def initiative_phases(
    *,
    encounter_round: int,
    party_surprised: bool,
    party_attacked_immediately: bool,
    foes_strike_first: bool,
) -> list[str]:
    """Expanded Edition p.146 initiative flowchart."""
    if encounter_round != 0:
        return ["pc_ranged", "foe_ranged", "pc_melee", "foe_melee"]
    if party_surprised or foes_strike_first:
        return ["foe_ranged", "pc_ranged", "foe_melee", "pc_melee"]
    if party_attacked_immediately:
        return ["pc_ranged", "foe_ranged", "pc_melee", "foe_melee"]
    return ["foe_ranged", "pc_melee", "foe_melee"]


def enemy_can_fire_ranged(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    name = enemy.name.lower()
    return bool(tags.intersection({"ranged", "missile", "javelin"})) or "javelin" in name


def enemy_uses_natural_attacks(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    if "natural" in tags:
        return True
    if enemy.category in {"vermin", "animal"}:
        return True
    name = enemy.name.lower()
    return any(word in name for word in ("bite", "claw", "tail", "gaze"))


def _resolve_foe_ranged(
    enemies: list[EnemyState],
    party: list[PartyMemberState],
    *,
    context: CombatContext,
    show_rolls: bool,
    explain_math: bool,
    foe_ranged_this_round: set[str],
) -> list[str]:
    log: list[str] = []
    for enemy in enemies:
        if enemy.life <= 0 or not enemy_can_fire_ranged(enemy):
            continue
        pairs = assign_enemy_attacks([enemy], party, context=context, once_per_foe=True)
        if not pairs:
            continue
        _, target = pairs[0]
        if target.current_life <= 0:
            continue
        if context.body_carrier_id and target.character_id == context.body_carrier_id:
            if consume_mirror_image(target):
                log.append(f"A mirror image absorbs {enemy.name}'s ranged attack on {target.name}.")
            else:
                target.current_life = max(0, target.current_life - 1)
                log.append(
                    f"{target.name} is hit automatically while carrying a fallen comrade ({enemy.name}'s ranged attack)."
                )
                if target.current_life == 0:
                    log.append(f"{target.name} falls.")
            foe_ranged_this_round.add(enemy.id)
            continue
        total, rolls = roll_exploding_d6()
        modifier, _ = _defense_bonus(target, enemy, context=context)
        final_total = total + modifier
        if show_rolls:
            log.append(
                f"Foe ranged: {enemy.name} vs {target.name}: "
                f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total}."
            )
        if explain_math:
            log.append(f"Defense math: need total > enemy level {enemy.level} to avoid damage.")
        if defense_succeeds(final_total, enemy.level, natural=rolls[0]):
            log.append(f"{target.name} defends against {enemy.name}'s ranged attack.")
        else:
            if consume_mirror_image(target):
                log.append(f"A mirror image absorbs {enemy.name}'s ranged attack on {target.name}.")
            else:
                target.current_life = max(0, target.current_life - 1)
                log.append(f"{target.name} takes 1 damage from {enemy.name}'s ranged attack.")
                if target.current_life == 0:
                    log.append(f"{target.name} falls.")
        foe_ranged_this_round.add(enemy.id)
    return log


def resolve_combat_round(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
    explain_math: bool = False,
    initial_minor_count: int | None = None,
    context: CombatContext | None = None,
    foes_first: bool = False,
    party_surprised: bool = False,
    party_attacked_immediately: bool = False,
    foes_strike_first: bool | None = None,
    party_attack_bonus: int = 0,
    party_phase_only: bool = False,
    foe_phase_only: bool = False,
    subdual: bool = False,
    encounter_round: int = 0,
    missile_used: set[str] | None = None,
    attack_targets: dict[str, str] | None = None,
) -> CombatRound:
    context = context or CombatContext()
    missile_used = set(missile_used or [])
    if foes_strike_first is None:
        foes_strike_first = foes_first
    missile_fired_this_round: set[str] = set()
    foe_ranged_this_round: set[str] = set()
    log: list[str] = []
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    morale_failed = False
    wielded_melee = dict(context.wielded_melee or {})

    if context.tile_type == "corridor" and context.wandering_ambush:
        log.append("Wandering Monsters ambush the rear guard.")
        if encounter_round == 0:
            log.append("Surprised party: foes act first in the opening round (p.146).")
    elif context.tile_type == "corridor":
        if context.wandering_ambush:
            log.append("Wandering ambush in a corridor: rear rank (#3–#4) is attacked this round (p.54).")
        else:
            log.append(
                "Corridor round: rear missiles (#3–#4), front melee (#1–#2); "
                "foes attack front rank (#1–#2) (p.94)."
            )

    if subdual:
        log.append("The party uses subdual attacks (foes are knocked out at 0 Life, not slain).")

    phases = initiative_phases(
        encounter_round=encounter_round,
        party_surprised=party_surprised,
        party_attacked_immediately=party_attacked_immediately,
        foes_strike_first=foes_strike_first,
    )
    if encounter_round == 0 and show_rolls:
        log.append(f"Initiative: {' → '.join(phase.replace('_', ' ') for phase in phases)}.")

    def run_pc_ranged_phase() -> None:
        nonlocal living_enemies
        if context.tile_type == "corridor":
            eligible = [
                pc
                for pc in sorted_party(party)
                if can_fire_missile(
                    pc,
                    tile_type=context.tile_type,
                    encounter_round=encounter_round,
                    missile_used=missile_used,
                )
            ]
            if not eligible:
                return
            log.append("Party ranged phase.")
            for pc in eligible:
                if not living_enemies:
                    break
                living_enemies = _resolve_pc_attack(
                    pc,
                    select_attack_target(pc, living_enemies, attack_targets),
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    party_attack_bonus=party_attack_bonus,
                    subdual=False,
                    missile=True,
                    living_enemies=living_enemies,
                    log=log,
                    wielded_melee=wielded_melee,
                    context=context,
                )
                missile_fired_this_round.add(pc.character_id)
                wielded_melee.pop(pc.character_id, None)
            return

        if encounter_round != 0:
            return
        allow_opening = party_attacked_immediately or party_surprised
        if not allow_opening:
            return
        eligible = [
            pc
            for pc in sorted_party(party)
            if select_missile_weapon(pc) and pc.character_id not in missile_used
        ]
        if not eligible:
            return
        log.append("Opening missile volley before close combat.")
        for pc in eligible:
            if not living_enemies:
                break
            living_enemies = _resolve_pc_attack(
                pc,
                select_attack_target(pc, living_enemies, attack_targets),
                show_rolls=show_rolls,
                explain_math=explain_math,
                party_attack_bonus=0,
                subdual=False,
                missile=True,
                living_enemies=living_enemies,
                log=log,
                wielded_melee=wielded_melee,
                context=context,
            )
            missile_used.add(pc.character_id)
            missile_fired_this_round.add(pc.character_id)
            wielded_melee.pop(pc.character_id, None)

    def run_foe_ranged_phase() -> None:
        if context.illusionary_fog_active:
            log.append("Illusionary fog suspends foe ranged and gaze attacks this round.")
            return
        ranged_log = _resolve_foe_ranged(
            enemies,
            party,
            context=context,
            show_rolls=show_rolls,
            explain_math=explain_math,
            foe_ranged_this_round=foe_ranged_this_round,
        )
        if ranged_log:
            log.append("Foe ranged phase.")
            log.extend(ranged_log)

    def run_party_melee_phase() -> None:
        nonlocal living_enemies, morale_failed
        for pc in sorted_party(party):
            if not living_enemies:
                break
            if not can_melee_attack(pc, context):
                if show_rolls:
                    log.append(f"{pc.name} cannot reach melee in this corridor.")
                continue
            force_unarmed = pc.character_id in missile_fired_this_round
            if force_unarmed and show_rolls:
                log.append(f"{pc.name} fights unarmed (-2) after shooting; draw a weapon to avoid this.")
            living_enemies = _resolve_pc_attack(
                pc,
                select_attack_target(pc, living_enemies, attack_targets),
                show_rolls=show_rolls,
                explain_math=explain_math,
                party_attack_bonus=party_attack_bonus,
                subdual=subdual,
                missile=False,
                living_enemies=living_enemies,
                log=log,
                wielded_melee=wielded_melee,
                force_unarmed=force_unarmed,
                context=context,
            )

        living_enemies = [enemy for enemy in enemies if enemy.life > 0]
        if living_enemies and living_party(party):
            minor_enemies = [
                enemy for enemy in living_enemies if enemy.life <= 1 and enemy.category in {"vermin", "minions"}
            ]
            if minor_enemies and initial_minor_count:
                if len(minor_enemies) <= initial_minor_count // 2 and not morale_failed:
                    morale_roll = roll_d6()
                    if show_rolls:
                        log.append(f"Morale roll: d6 = {morale_roll}.")
                    if morale_roll <= 3:
                        log.append("The remaining foes flee.")
                        for enemy in living_enemies:
                            enemy.life = 0
                        morale_failed = True
                        living_enemies = []

    def run_foe_melee_phase() -> None:
        nonlocal living_enemies
        living_enemies = [enemy for enemy in enemies if enemy.life > 0]
        if morale_failed or not living_enemies or not living_party(party):
            return
        for enemy in living_enemies:
            if enemy_has_regeneration(enemy) and enemy.life < enemy.max_life:
                enemy.life += 1
                if show_rolls:
                    log.append(f"{enemy.name} regenerates 1 Life.")
        log.extend(tick_poisoned_heroes(party, show_rolls=show_rolls, explain_math=explain_math))
        living_enemies = [enemy for enemy in enemies if enemy.life > 0]
        if not living_party(party):
            return
        attack_pairs: list[tuple[EnemyState, PartyMemberState]] = []
        specter_casters = {
            member.character_id
            for member in party
            if member.current_life > 0 and any(status.lower() == "specter swarm" for status in member.statuses)
        }
        for enemy, target in assign_enemy_attacks(enemies, party, context=context):
            if enemy.id in foe_ranged_this_round and not enemy_uses_natural_attacks(enemy):
                if show_rolls:
                    log.append(f"{enemy.name} spends the turn drawing a melee weapon.")
                continue
            if enemy_is_held(enemy):
                if show_rolls:
                    log.append(f"{enemy.name} is held and cannot act.")
                continue
            if context.illusionary_fog_active and enemy_uses_gaze(enemy):
                if show_rolls:
                    log.append(f"{enemy.name}'s gaze attack is lost in the illusionary fog.")
                continue
            if "Specter Distracted" in enemy.tags and target.character_id in specter_casters:
                if show_rolls:
                    log.append(f"{enemy.name} is distracted by specters and cannot reach {target.name}.")
                continue
            attack_pairs.append((enemy, target))
        log.extend(
            _resolve_attacks(
                attack_pairs,
                show_rolls=show_rolls,
                explain_math=explain_math,
                context=context,
            )
        )

    def run_party_phase() -> None:
        run_pc_ranged_phase()
        run_party_melee_phase()

    def run_foe_phase() -> None:
        run_foe_ranged_phase()
        run_foe_melee_phase()

    if foe_phase_only:
        run_foe_melee_phase()
    elif party_phase_only:
        run_party_melee_phase()
    else:
        phase_runners = {
            "pc_ranged": run_pc_ranged_phase,
            "foe_ranged": run_foe_ranged_phase,
            "pc_melee": run_party_melee_phase,
            "foe_melee": run_foe_melee_phase,
        }
        for phase in phases:
            phase_runners[phase]()

    if context.wielded_melee is not None:
        context.wielded_melee.clear()
        context.wielded_melee.update(wielded_melee)

    tick_illusionary_sword_turns(party)

    combat_over = not any(enemy.life > 0 for enemy in enemies) or not living_party(party)
    return CombatRound(
        party=party,
        enemies=enemies,
        log=log,
        combat_over=combat_over,
        morale_failed=morale_failed,
        missile_used=missile_used,
    )


def resolve_flee_strike(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
    explain_math: bool = False,
    context: CombatContext | None = None,
) -> CombatRound:
    context = context or CombatContext()
    log = ["The party strikes fleeing foes at +1."]
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if living_enemies and living_party(party):
        for pc in sorted_party(party):
            if pc.current_life <= 0:
                continue
            target = living_enemies[0]
            weapon = select_melee_weapon(pc, target, wielded=(context.wielded_melee or {}).get(pc.character_id))
            total, rolls = roll_exploding_d6()
            modifier = attack_modifier(pc, target) + 1 + weapon_attack_modifier(weapon, target)
            final_total = total + modifier
            if show_rolls:
                weapon_note = ""
                weapon_mod = weapon_attack_modifier(weapon, target)
                if weapon_mod:
                    weapon_note = f" ({weapon_label(weapon)} {'+' if weapon_mod > 0 else ''}{weapon_mod})"
                log.append(
                    f"Flee strike: {pc.name} vs {target.name}: "
                    f"{' + '.join(str(value) for value in rolls)} + {modifier}{weapon_note} = {final_total}."
                )
            if explain_math:
                log.append(f"Attack math: need total >= enemy level {target.level} to hit.")
            if attack_hits(final_total, target.level):
                if target.life <= 1 and target.category in {"vermin", "minions"}:
                    kills = attack_damage(final_total, max(1, target.level))
                    target.life -= kills
                    log.append(f"{pc.name} slays {kills} {target.name} as they flee.")
                else:
                    damage = attack_damage(final_total, max(1, target.level))
                    if has_blade_poison(pc):
                        damage += 1
                        consume_blade_poison(pc)
                        log.append(f"{pc.name}'s blade poison adds 1 damage.")
                    target.life -= damage
                    log.append(f"{pc.name} hits fleeing {target.name} for {damage} damage.")
            else:
                log.append(f"{pc.name} misses the fleeing {target.name}.")
            break
    for enemy in enemies:
        enemy.life = 0
    log.append("The fleeing foes disappear.")
    return CombatRound(
        party=party,
        enemies=enemies,
        log=log,
        combat_over=True,
        morale_failed=True,
    )


def resolve_flee(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
    explain_math: bool = False,
    context: CombatContext | None = None,
    skip_parting_attacks: bool = False,
) -> CombatRound:
    context = context or CombatContext()
    log = ["The party flees."]
    if skip_parting_attacks:
        log.append("A halfling spends Luck to escape without parting blows.")
    else:
        attack_pairs = assign_flee_attacks(enemies, party)
        log.extend(
            _resolve_attacks(
                attack_pairs,
                show_rolls=show_rolls,
                explain_math=explain_math,
                context=context,
                defense_bonus=2 if context.illusionary_fog_active else 0,
            )
        )
    survivors = living_party(party)
    if survivors:
        log.append("The party escapes the immediate fight.")
    else:
        log.append("The party has fallen.")
    return CombatRound(
        party=party,
        enemies=enemies,
        log=log,
        combat_over=True,
        fled=bool(survivors),
    )


def resolve_withdraw(
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
    explain_math: bool = False,
    context: CombatContext | None = None,
) -> CombatRound:
    context = context or CombatContext()
    log = ["The party withdraws through a door."]
    attack_pairs = assign_enemy_attacks(enemies, party, context=context, once_per_foe=True)
    log.extend(
        _resolve_attacks(
            attack_pairs,
            show_rolls=show_rolls,
            explain_math=explain_math,
            context=context,
            withdraw=True,
        )
    )
    survivors = living_party(party)
    if survivors:
        log.append("The party slams the door and retreats.")
    else:
        log.append("The party has fallen during the withdrawal.")
    return CombatRound(
        party=party,
        enemies=enemies,
        log=log,
        combat_over=True,
        fled=bool(survivors),
    )
