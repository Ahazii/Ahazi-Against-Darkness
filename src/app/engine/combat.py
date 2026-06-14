from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Callable

from ..schemas import EnemyState, PartyMemberState, SessionState
from .class_combat import (
    armor_defense_bonus,
    attack_modifier,
    defense_modifier,
    is_hated_by_foes,
    light_gladiator_weapon_bonus,
)
from .combat_modifiers import (
    apply_poison_status,
    consume_blade_poison,
    consume_mirror_image,
    enemy_has_poison,
    has_blade_poison,
    poison_save_succeeds,
    tick_poisoned_heroes,
)
from .dice import roll_d6, roll_die, roll_exploding_for_member, tier_die_sides

roll_exploding_for_level = roll_exploding_for_member
from .inventory import encumbrance_penalty
from .secrets import secret_attack_bonus, secret_defense_bonus, secret_weakness_attack_bonus
from .subdual import apply_major_foe_level_drop, apply_subdual_damage, subdue_minor_foe

from .class_abilities import effective_foe_level, paladin_mounted_attack_bonus
from .expert_skill_effects import (
    _is_demon,
    _is_undead,
    adjust_incoming_damage,
    culling_extra_minion_kills,
    deadly_strike_multiplier,
    dragonslayer_damage_multiplier,
    encounter_spent,
    expert_attack_bonus,
    expert_defense_bonus,
    expert_morale_modifier,
    gladiator_fight,
    has_skill,
    knife_throw_weapon,
    mark_encounter_spent,
    member_carries_shield,
    spot_weakness_extra_damage,
    stabbing_attack_follow_up,
    sworn_enemy_target_preference,
    unarmed_attack_penalty,
)
from .heroic_skill_effects import (
    apply_mass_blessing,
    apply_restore_healing,
    cleave_follow_up_count,
    consume_carnage_bonus,
    deadly_stab_extra_damage,
    deep_wound_extra_damage,
    grant_carnage_bonus,
    heroic_attack_bonus,
    heroic_defense_bonus,
    master_strike_extra_damage,
    mass_blessing_attack_bonus,
    try_sacrifice_shield,
    try_survive_killing_blow,
    wrath_follow_up_penalty,
)
from .heroic_skill_effects import has_heroic_skill
from .weapons import (
    WeaponProfile,
    can_fire_missile,
    light_gladiator_dual_pair,
    mushroom_monk_flurry_eligible,
    mushroom_monk_full_attack_item,
    mushroom_monk_unarmed_penalty,
    ranger_dual_wield_pair,
    swashbuckler_dual_pair,
    ranger_outdoor_bow,
    select_melee_weapon,
    select_missile_weapon,
    weapon_attack_modifier,
    weapon_label,
)
from .experience import tier_for_level


@dataclass(frozen=True)
class PlannedAttack:
    wielded: str | None = None
    missile: bool = False
    half_level_class_bonus: bool = False
    no_explode: bool = False
    label: str = ""
    force_unarmed: bool = False
    extra_modifier: int = 0
    ignore_weapon_mod: bool = False


@dataclass
class CombatContext:
    tile_type: str = "room"
    wandering_ambush: bool = False
    combat_round: int = 1
    outdoors: bool = False
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
    foe_level_penalties: dict[str, int] = field(default_factory=dict)
    luck_reroll_defenders: set[str] = field(default_factory=set)
    gnome_gadget_attackers: set[str] = field(default_factory=set)
    flip_kick_attackers: set[str] = field(default_factory=set)
    parrying_character_ids: set[str] = field(default_factory=set)
    sacrifice_guards: dict[str, str] = field(default_factory=dict)
    sacrifice_used: set[str] = field(default_factory=set)
    evading_character_ids: set[str] = field(default_factory=set)
    double_kick_attackers: set[str] = field(default_factory=set)
    gladiator_counter_pending: dict[str, dict[str, str | int]] = field(default_factory=dict)
    gladiator_counter_used: set[str] = field(default_factory=set)
    assassin_striker_id: str | None = None
    assassin_mark_enemy_id: str | None = None
    on_assassin_strike_used: Callable[[], None] | None = None
    spend_gnome_gadget: Callable[[PartyMemberState], bool] | None = None
    spend_acrobat_trick: Callable[[PartyMemberState], bool] | None = None
    acrobat_skip_attack: dict[str, bool] = field(default_factory=dict)
    session: SessionState | None = None
    deadly_strike_attackers: set[str] = field(default_factory=set)
    divine_smite_attackers: set[str] = field(default_factory=set)
    sacrifice_shield_users: set[str] = field(default_factory=set)
    sacrifice_shield_used: set[str] = field(default_factory=set)
    double_attack_attackers: set[str] = field(default_factory=set)
    double_shot_attackers: set[str] = field(default_factory=set)
    restore_users: set[str] = field(default_factory=set)
    restore_targets: dict[str, str] = field(default_factory=dict)
    ward_targets: dict[str, str] = field(default_factory=dict)
    mass_blessing_users: set[str] = field(default_factory=set)
    whirlwind_attackers: set[str] = field(default_factory=set)
    master_strike_attackers: set[str] = field(default_factory=set)
    aggressive_stance_attackers: set[str] = field(default_factory=set)
    defensive_stance_attackers: set[str] = field(default_factory=set)
    knife_throw_attackers: set[str] = field(default_factory=set)
    acrobat_knife_throw_attackers: set[str] = field(default_factory=set)
    illusionist_knife_throw_attackers: set[str] = field(default_factory=set)
    continual_light_casters: set[str] = field(default_factory=set)
    spend_caster_spell_slot: Callable[[PartyMemberState], bool] | None = None
    round_show_rolls: bool = True
    round_explain_math: bool = False
    round_party_attack_bonus: int = 0
    round_attack_targets: dict[str, str] | None = None
    round_attack_secondary_targets: dict[str, str] | None = None
    double_kick_targets: dict[str, list[str]] = field(default_factory=dict)
    withdrawing: bool = False


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


def suppress_enemy_regeneration(enemy: EnemyState) -> None:
    if enemy_has_regeneration(enemy):
        enemy.regen_suppressed = True


REGEN_SUPPRESSING_DAMAGE_KINDS = frozenset({"fire", "acid", "lightning", "oil"})


def apply_enemy_damage(
    enemy: EnemyState,
    amount: int,
    *,
    damage_kind: str = "normal",
) -> None:
    """Apply damage; fire, acid, lightning, or oil suppress troll regeneration (EE p.99)."""
    if amount <= 0:
        return
    enemy.life -= amount
    if damage_kind in REGEN_SUPPRESSING_DAMAGE_KINDS:
        suppress_enemy_regeneration(enemy)


def tick_enemy_regeneration(enemy: EnemyState, log: list[str], *, show_rolls: bool) -> None:
    if not enemy_has_regeneration(enemy) or enemy.life >= enemy.max_life:
        enemy.regen_suppressed = False
        return
    if enemy.regen_suppressed:
        log.append(f"Effect: {enemy.name} cannot regenerate (fire, acid, lightning, or oil wound).")
    else:
        enemy.life += 1
        log.append(f"Effect: {enemy.name} regenerates 1 Life.")
    enemy.regen_suppressed = False


def enemy_uses_gaze(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    return "gaze" in tags or "gaze" in enemy.name.lower()


def enemy_is_held(enemy: EnemyState) -> bool:
    return "Held" in enemy.tags or "held" in {tag.lower() for tag in enemy.tags}


def living_party(party: list[PartyMemberState]) -> list[PartyMemberState]:
    return [pc for pc in party if pc.current_life > 0]


def _counter_pending(context: CombatContext, character_id: str) -> tuple[str, int] | None:
    pending = context.gladiator_counter_pending.get(character_id)
    if not pending:
        return None
    enemy_id = str(pending.get("enemy_id", ""))
    bonus = int(pending.get("bonus", 0))
    if not enemy_id or bonus <= 0:
        return None
    return enemy_id, bonus


def _set_counter_pending(context: CombatContext, character_id: str, enemy_id: str, bonus: int) -> None:
    context.gladiator_counter_pending[character_id] = {"enemy_id": enemy_id, "bonus": bonus}


def _clear_counter_pending(context: CombatContext, character_id: str) -> None:
    context.gladiator_counter_pending.pop(character_id, None)


def _blocks_multi_attack_style(pc: PartyMemberState, context: CombatContext) -> bool:
    return pc.character_id in context.rage_attackers or pc.character_id in context.flip_kick_attackers


def _class_attack_bonus(
    pc: PartyMemberState,
    target: EnemyState,
    weapon: WeaponProfile | None,
    *,
    half_level: bool,
    force_unarmed: bool = False,
) -> int:
    class_id = pc.class_id.lower()
    if class_id == "mushroom_monk":
        item_name = weapon.item if weapon else None
        if force_unarmed or mushroom_monk_full_attack_item(item_name):
            return pc.level
        return pc.level // 2
    if class_id == "light_gladiator":
        return light_gladiator_weapon_bonus(pc, bool(weapon and weapon.light))
    if class_id == "ranger":
        return attack_modifier(pc, target, half_level=half_level)
    return attack_modifier(pc, target)


def plan_ranged_attacks(pc: PartyMemberState, context: CombatContext) -> list[PlannedAttack]:
    if pc.character_id in context.continual_light_casters and (
        has_skill(pc, "continual_light") or pc.class_id.lower() == "illusionist"
    ):
        return []
    if pc.character_id in context.illusionist_knife_throw_attackers and pc.class_id.lower() == "illusionist":
        tier = tier_for_level(pc.level)
        return [
            PlannedAttack(
                missile=True,
                extra_modifier=tier + pc.level,
                ignore_weapon_mod=True,
                label="illusionary knife throw",
            )
        ]
    if pc.character_id in context.acrobat_knife_throw_attackers and pc.class_id.lower() == "acrobat":
        weapon_name = knife_throw_weapon(pc)
        if weapon_name:
            tier = tier_for_level(pc.level)
            return [
                PlannedAttack(
                    missile=True,
                    wielded=weapon_name,
                    extra_modifier=tier,
                    ignore_weapon_mod=True,
                    label="acrobat knife throw",
                )
            ]
    if pc.character_id in context.knife_throw_attackers and has_skill(pc, "knife_throwing"):
        weapon_name = knife_throw_weapon(pc)
        if weapon_name:
            return [
                PlannedAttack(
                    missile=True,
                    wielded=weapon_name,
                    extra_modifier=-1,
                    label="knife throw",
                )
            ]
    if (
        pc.class_id.lower() == "ranger"
        and context.outdoors
        and ranger_outdoor_bow(pc) is not None
        and not _blocks_multi_attack_style(pc, context)
    ):
        half = pc.level // 2
        return [
            PlannedAttack(
                missile=True,
                half_level_class_bonus=True,
                no_explode=True,
                label=f"outdoor bow (+{half})",
            ),
            PlannedAttack(
                missile=True,
                half_level_class_bonus=True,
                no_explode=True,
                label=f"outdoor bow (+{half})",
            ),
            ]
    if pc.character_id in context.double_shot_attackers and has_heroic_skill(pc, "double_shot"):
        return [
            PlannedAttack(missile=True, label="double shot"),
            PlannedAttack(missile=True, label="double shot"),
        ]
    return [PlannedAttack(missile=True)]


def plan_melee_attacks(pc: PartyMemberState, context: CombatContext) -> list[PlannedAttack]:
    if pc.character_id in context.continual_light_casters and (
        has_skill(pc, "continual_light") or pc.class_id.lower() == "illusionist"
    ):
        return []
    if pc.character_id in context.parrying_character_ids:
        return []
    class_id = pc.class_id.lower()
    if class_id == "ranger" and not _blocks_multi_attack_style(pc, context):
        pair = ranger_dual_wield_pair(pc)
        if pair:
            first, second = pair
            half = pc.level // 2
            note = f"dual wield (+{half})"
            return [
                PlannedAttack(wielded=first, half_level_class_bonus=True, no_explode=True, label=note),
                PlannedAttack(wielded=second, half_level_class_bonus=True, no_explode=True, label=note),
            ]
    if class_id == "light_gladiator":
        pair = light_gladiator_dual_pair(pc)
        if pair:
            first, second = pair
            return [
                PlannedAttack(wielded=first, label="dual light"),
                PlannedAttack(wielded=second, label="dual light"),
            ]
    if class_id == "swashbuckler" and not _blocks_multi_attack_style(pc, context):
        pair = swashbuckler_dual_pair(pc)
        if pair:
            first, second = pair
            return [
                PlannedAttack(wielded=first, label="main hand"),
                PlannedAttack(wielded=second, label="off-hand"),
            ]
    if class_id == "mushroom_monk" and not _blocks_multi_attack_style(pc, context):
        wielded = (context.wielded_melee or {}).get(pc.character_id) or pc.default_melee_weapon
        if mushroom_monk_flurry_eligible(pc, wielded=wielded):
            profile = select_melee_weapon(pc, wielded=wielded)
            use_unarmed = profile is None
            attacks = tier_for_level(pc.level)
            return [
                PlannedAttack(
                    wielded=None if use_unarmed else wielded,
                    force_unarmed=use_unarmed,
                    label="flurry",
                )
                for _ in range(attacks)
            ]
    if pc.character_id in context.double_attack_attackers and has_skill(pc, "double_attack"):
        return [
            PlannedAttack(label="double attack"),
            PlannedAttack(label="double attack"),
        ]
    wielded = (context.wielded_melee or {}).get(pc.character_id)
    weapon = select_melee_weapon(pc, wielded=wielded)
    plans = [PlannedAttack()]
    if stabbing_attack_follow_up(pc, weapon):
        plans.append(PlannedAttack(label="stabbing"))
    return plans


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
    living = [
        pc
        for pc in sorted_party(party)
        if pc.character_id not in context.evading_character_ids
    ]
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
            preferred = sworn_enemy_target_preference(living, enemy)
            target = preferred if preferred and preferred in living else living[index % len(living)]
            attack_pairs.append((enemy, target))
        return attack_pairs

    targets: list[PartyMemberState] = []
    for pc in living:
        targets.extend([pc] * (len(strikes) // len(living)))
    hated = [pc for pc in living if is_hated_by_foes(pc, living_enemies)]
    pool = hated or living
    while len(targets) < len(strikes):
        targets.append(pool[len(targets) % len(pool)])
    for enemy, target in zip(strikes, targets, strict=False):
        preferred = sworn_enemy_target_preference(living, enemy)
        attack_pairs.append((enemy, preferred if preferred and preferred in living else target))
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


def _log_multi_attack_assignments(
    attack_pairs: list[tuple[EnemyState, PartyMemberState]],
    log: list[str],
) -> None:
    grouped: dict[str, tuple[EnemyState, list[PartyMemberState]]] = {}
    for enemy, target in attack_pairs:
        if enemy.attacks <= 1:
            continue
        if enemy.id not in grouped:
            grouped[enemy.id] = (enemy, [])
        grouped[enemy.id][1].append(target)
    for enemy, targets in grouped.values():
        if len(targets) <= 1:
            continue
        target_text = ", ".join(f"#{target.marching_order} {target.name}" for target in targets)
        log.append(f"Event: {enemy.name} makes {len(targets)} attacks this round: {target_text}.")


def _is_skeleton_or_undead(enemy: EnemyState) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    return "undead" in tags or "skeleton" in tags or "skeleton" in enemy.name.lower()


def _defense_bonus(
    member: PartyMemberState,
    enemy: EnemyState,
    *,
    context: CombatContext,
    withdraw: bool = False,
    melee: bool = True,
    living_foe_count: int = 1,
    melee_attacks_on_target: int = 1,
) -> tuple[int, int]:
    modifier = defense_modifier(member, enemy)
    if member.character_id == context.cursed_character_id:
        modifier -= 1
    include_shield = not (context.wandering_ambush and context.combat_round == 1)
    armor_bonus = armor_defense_bonus(member, include_shield=include_shield)
    if withdraw:
        modifier += 1
    parry_bonus = 1 if melee and member.character_id in context.parrying_character_ids else 0
    protection_bonus = 1 if any(status.lower() == "protection" for status in member.statuses) else 0
    barkskin_bonus = 2 if any(status.lower() == "barkskin" for status in member.statuses) else 0
    illusion_armor = 0
    if any(status.lower() == "illusionary armor" for status in member.statuses):
        if enemy.category != "vermin" and not any(tag in {"undead", "artificial", "elemental", "construct"} for tag in enemy.tags):
            illusion_armor = member.level
    encumbered = encumbrance_penalty(member)
    session = context.session
    expert_bonus = 0
    if session is not None:
        expert_bonus = expert_defense_bonus(
            member,
            enemy,
            session,
            withdrawing=withdraw or context.withdrawing,
            gladiator_match=gladiator_fight([enemy]) if enemy else False,
        )
    heroic_bonus = heroic_defense_bonus(
        member,
        single_attacker=living_foe_count == 1,
        defensive_stance=member.character_id in context.defensive_stance_attackers,
        aggressive_stance_penalty=session is not None
        and member.character_id in getattr(session, "aggressive_stance_penalty", []),
        melee_attacks_on_target=melee_attacks_on_target if melee else 0,
        enemy=enemy if melee else None,
        session=session,
    )
    secret_bonus = secret_defense_bonus(member, enemy)
    return (
        modifier
        + armor_bonus
        + parry_bonus
        + protection_bonus
        + barkskin_bonus
        + illusion_armor
        + encumbered
        + expert_bonus
        + heroic_bonus
        + secret_bonus,
        armor_bonus,
    )


def _apply_pc_hit(
    pc: PartyMemberState,
    target: EnemyState,
    *,
    final_total: int,
    foe_level: int,
    living_enemies: list[EnemyState],
    log: list[str],
    subdual: bool,
    attack_label: str,
    rage_hit: bool = False,
    on_foe_kill: Callable[[str], None] | None = None,
    context: CombatContext | None = None,
    attack_rolls: list[int] | None = None,
    weapon: WeaponProfile | None = None,
) -> list[EnemyState]:
    context = context or CombatContext()
    session = context.session
    assassin_triple = (
        context.assassin_striker_id == pc.character_id
        and context.assassin_mark_enemy_id == target.id
    )
    deadly_multiplier = 1
    if session is not None:
        deadly_multiplier = deadly_strike_multiplier(
            pc,
            session,
            pc.character_id in context.deadly_strike_attackers,
        )
    if deadly_multiplier > 1:
        log.append(f"{pc.name} uses Deadly Strike (double wounds).")
    if target.life <= 1 and target.category in {"vermin", "minions"}:
        if subdual:
            subdue_minor_foe(target)
            log.append(f"{pc.name} subdues {target.name} with {attack_label}.")
            return [enemy for enemy in living_enemies if enemy.life > 0]
        kills = attack_damage(final_total, max(1, foe_level))
        if session and has_skill(pc, "culling_of_the_weak") and not encounter_spent(
            session, pc.character_id, "culling_of_the_weak"
        ):
            mark_encounter_spent(session, pc.character_id, "culling_of_the_weak")
            extra = culling_extra_minion_kills(final_total, max(1, foe_level))
            if extra:
                culled = 0
                for other in living_enemies:
                    if culled >= extra or other.id == target.id:
                        continue
                    if other.category in {"vermin", "minions"} and other.life > 0:
                        other.life = 0
                        culled += 1
                if culled:
                    log.append(f"{pc.name}'s Culling of the Weak slays {culled} extra minions.")
        if rage_hit:
            kills *= 2
            log.append(f"{pc.name}'s rage attack inflicts double damage ({kills} slain).")
        if deadly_multiplier > 1:
            kills *= deadly_multiplier
        if assassin_triple:
            kills *= 3
            log.append(f"{pc.name}'s assassination strike inflicts triple damage ({kills} slain).")
            if context.on_assassin_strike_used:
                context.on_assassin_strike_used()
        if session is not None:
            kills *= dragonslayer_damage_multiplier(pc, session, target)
        target.life -= kills
        log.append(f"{pc.name} slays {kills} {target.name} with {attack_label}.")
        if target.life <= 0:
            if (
                session is not None
                and session.blessed_undead_bonus_character_id
                and (_is_undead(target) or _is_demon(target))
            ):
                session.blessed_undead_bonus_character_id = None
                log.append("Effect: Blessed Temple bonus ends after an undead or demon foe is slain.")
            if on_foe_kill is not None:
                on_foe_kill(pc.character_id)
            updated = [enemy for enemy in living_enemies if enemy.life > 0]
            if session:
                updated, chain_log = _heroic_minion_kill_followups(
                    pc,
                    context,
                    updated,
                    log,
                    subdual=subdual,
                )
                log.extend(chain_log)
            if (
                session
                and context
                and pc.character_id in context.whirlwind_attackers
                and has_skill(pc, "whirlwind_of_steel")
                and not encounter_spent(session, pc.character_id, "whirlwind_of_steel")
            ):
                mark_encounter_spent(session, pc.character_id, "whirlwind_of_steel")
                log.append(f"{pc.name} unleashes Whirlwind of Steel.")
                for penalty in (-1, -2):
                    minors = [
                        enemy
                        for enemy in updated
                        if enemy.category in {"vermin", "minions"} and enemy.life > 0
                    ]
                    if not minors:
                        break
                    updated = _resolve_pc_attack(
                        pc,
                        minors[0],
                        show_rolls=context.round_show_rolls,
                        explain_math=context.round_explain_math,
                        party_attack_bonus=context.round_party_attack_bonus,
                        subdual=subdual,
                        missile=False,
                        living_enemies=updated,
                        log=log,
                        wielded_melee=context.wielded_melee,
                        context=context,
                        attack_plan=PlannedAttack(
                            no_explode=True,
                            extra_modifier=penalty,
                            label="whirlwind",
                        ),
                    )
            return updated
        return living_enemies

    damage = attack_damage(final_total, max(1, foe_level))
    if (
        session is not None
        and pc.character_id in context.divine_smite_attackers
        and has_skill(pc, "divine_smite")
        and pc.character_id not in session.divine_smite_used
        and target.category in {"weird", "boss"}
    ):
        session.divine_smite_used.append(pc.character_id)
        damage = 3
        log.append(f"{pc.name} invokes Divine Smite — 3 damage to {target.name}.")
    elif session is not None and attack_rolls:
        extra = spot_weakness_extra_damage(attack_rolls, target)
        if extra:
            damage += extra
            log.append(f"{pc.name}'s Spot Weakness adds {extra} wound.")
    if rage_hit:
        damage *= 2
        log.append(f"{pc.name}'s rage attack inflicts double damage ({damage}).")
    if deadly_multiplier > 1:
        damage *= deadly_multiplier
    if assassin_triple:
        damage *= 3
        log.append(f"{pc.name}'s assassination strike inflicts triple damage ({damage}).")
        if context.on_assassin_strike_used:
            context.on_assassin_strike_used()
    if session is not None:
        damage *= dragonslayer_damage_multiplier(pc, session, target)
    extra, master_log = master_strike_extra_damage(
        pc,
        session,
        missile="missile" in attack_label.lower(),
        declared=pc.character_id in context.master_strike_attackers,
    )
    if extra:
        damage += extra
        log.extend(master_log)
    wound_extra, wound_log = deep_wound_extra_damage(pc, target)
    if wound_extra:
        damage += wound_extra
        log.extend(wound_log)
    stab_extra, stab_log = deadly_stab_extra_damage(pc, weapon, missile="missile" in attack_label.lower())
    if stab_extra:
        damage += stab_extra
        log.extend(stab_log)
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
    apply_enemy_damage(target, damage, damage_kind="normal")
    log.append(f"{pc.name} hits {target.name} for {damage} damage with {attack_label}.")
    if apply_major_foe_level_drop(target):
        log.append(f"{target.name} is bloodied; its effective Level drops to L{target.level}.")
    if target.life <= 0:
        log.append(f"{target.name} is defeated.")
        if (
            session is not None
            and session.blessed_undead_bonus_character_id
            and (_is_undead(target) or _is_demon(target))
        ):
            session.blessed_undead_bonus_character_id = None
            log.append("Effect: Blessed Temple bonus ends after an undead or demon foe is slain.")
        if on_foe_kill is not None:
            on_foe_kill(pc.character_id)
        updated = [enemy for enemy in living_enemies if enemy.life > 0]
        if session and target.category in {"vermin", "minions"}:
            chain_log: list[str] = []
            updated, chain_log = _heroic_minion_kill_followups(
                pc,
                context,
                updated,
                log,
                subdual=subdual,
            )
            log.extend(chain_log)
        return updated
    return living_enemies


def _heroic_minion_kill_followups(
    pc: PartyMemberState,
    context: CombatContext,
    living_enemies: list[EnemyState],
    log: list[str],
    *,
    subdual: bool,
) -> tuple[list[EnemyState], list[str]]:
    session = context.session
    notes: list[str] = []
    if session is None:
        return living_enemies, notes
    notes.extend(grant_carnage_bonus(session, pc))
    updated = living_enemies
    for _ in range(cleave_follow_up_count(pc)):
        minors = [
            enemy
            for enemy in updated
            if enemy.category in {"vermin", "minions"} and enemy.life > 0
        ]
        if not minors:
            break
        notes.append(f"{pc.name} Cleaves at −1.")
        updated = _resolve_pc_attack(
            pc,
            minors[0],
            show_rolls=context.round_show_rolls,
            explain_math=context.round_explain_math,
            party_attack_bonus=context.round_party_attack_bonus,
            subdual=subdual,
            missile=False,
            living_enemies=updated,
            log=log,
            wielded_melee=context.wielded_melee,
            context=context,
            attack_plan=PlannedAttack(no_explode=True, extra_modifier=-1, label="cleave"),
        )
    wrath_penalty = wrath_follow_up_penalty(
        session,
        pc,
        raging=pc.character_id in context.rage_attackers,
    )
    if wrath_penalty is not None:
        minors = [
            enemy
            for enemy in updated
            if enemy.category in {"vermin", "minions"} and enemy.life > 0
        ]
        if minors:
            label = "Wrath of the Berserker"
            if wrath_penalty == 0:
                notes.append(f"{pc.name} unleashes {label} (no penalty).")
            else:
                notes.append(f"{pc.name} follows with {label} at −1.")
            updated = _resolve_pc_attack(
                pc,
                minors[0],
                show_rolls=context.round_show_rolls,
                explain_math=context.round_explain_math,
                party_attack_bonus=context.round_party_attack_bonus,
                subdual=subdual,
                missile=False,
                living_enemies=updated,
                log=log,
                wielded_melee=context.wielded_melee,
                context=context,
                attack_plan=PlannedAttack(
                    no_explode=True,
                    extra_modifier=wrath_penalty,
                    label="wrath",
                ),
            )
    return updated, notes


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
    attack_plan: PlannedAttack | None = None,
) -> list[EnemyState]:
    context = context or CombatContext()
    plan = attack_plan or PlannedAttack(missile=missile)
    missile = plan.missile
    force_unarmed = force_unarmed or plan.force_unarmed
    wielded = plan.wielded if plan.wielded else (wielded_melee or {}).get(pc.character_id)
    if missile and plan.wielded:
        from .weapons import weapon_profile

        weapon = weapon_profile(plan.wielded)
    elif missile:
        weapon = select_missile_weapon(pc)
    else:
        weapon = select_melee_weapon(pc, target, wielded=wielded, force_unarmed=force_unarmed)
    attack_label = f"a {weapon_label(weapon)} {'missile' if missile else 'melee'} attack"
    if plan.label:
        attack_label = f"{attack_label} ({plan.label})"
    if (
        plan.label == "knife throw"
        and plan.wielded
        and context.session is not None
        and plan.wielded in pc.inventory
    ):
        pc.inventory.remove(plan.wielded)
        thrown = dict(context.session.expert_knife_thrown or {})
        thrown[pc.character_id] = plan.wielded
        context.session.expert_knife_thrown = thrown
    use_rage = pc.character_id in context.rage_attackers and not plan.half_level_class_bonus
    use_luck_reroll = pc.character_id in context.luck_reroll_attackers
    use_panache = pc.character_id in context.panache_attack_bonus
    use_flip_kick = pc.character_id in context.flip_kick_attackers and not missile
    use_gnome_gadget = pc.character_id in context.gnome_gadget_attackers
    use_acrobat_knife = pc.character_id in context.acrobat_knife_throw_attackers and missile
    use_illusion_knife = pc.character_id in context.illusionist_knife_throw_attackers and missile
    target_level = effective_foe_level(target, context.foe_level_penalties)

    pending_counter = _counter_pending(context, pc.character_id)
    if pending_counter:
        pending_enemy_id, pending_bonus = pending_counter
        if pending_enemy_id != target.id:
            log.append(f"{pc.name} forfeits counter-strike (+{pending_bonus}).")
            _clear_counter_pending(context, pc.character_id)
            context.gladiator_counter_used.add(pc.character_id)
            pending_counter = None

    if use_acrobat_knife:
        if context.spend_acrobat_trick and not context.spend_acrobat_trick(pc):
            log.append(f"{pc.name} cannot Knife Throw (no Trick points).")
            return living_enemies
        log.append(f"{pc.name} throws a blade with a Trick (+{tier_for_level(pc.level)} Attack).")
    if use_illusion_knife:
        if context.spend_caster_spell_slot and not context.spend_caster_spell_slot(pc):
            log.append(f"{pc.name} cannot throw an illusionary knife (no spell slots).")
            return living_enemies
        log.append(f"{pc.name} spends 1 spell slot on an illusionary knife (+Tier +L).")

    if use_flip_kick:
        force_unarmed = True
        weapon = None
        attack_label = f"Flip Kick ({plan.label})" if plan.label else "Flip Kick"
        if context.spend_acrobat_trick and not context.spend_acrobat_trick(pc):
            log.append(f"{pc.name} cannot Flip Kick (no Trick points).")
            return living_enemies
        log.append(f"{pc.name} uses Flip Kick (no unarmed penalty).")

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
    elif plan.no_explode:
        sides = tier_die_sides(pc.level)
        roll = roll_die(sides)
        total, rolls = roll, [roll]
        rage_note = ""
    else:
        total, rolls = roll_exploding_for_level(pc)
        rage_note = ""

    class_bonus = _class_attack_bonus(
        pc, target, weapon, half_level=plan.half_level_class_bonus, force_unarmed=force_unarmed
    )
    weapon_mod = (
        0
        if plan.ignore_weapon_mod
        else (
            unarmed_attack_penalty(pc)
            if weapon is None
            else weapon_attack_modifier(weapon, target)
        )
    )
    if pc.class_id.lower() == "cleric" and _is_undead(target):
        log.append(f"Effect: {pc.name} uses full Level Attack vs undead {target.name}.")
    if weapon is not None and weapon.crushing and _is_skeleton_or_undead(target):
        log.append(f"Effect: {weapon_label(weapon)} gains +1 Attack vs skeleton/undead {target.name}.")
    session = context.session
    gladiator_match = gladiator_fight(living_enemies)
    expert_bonus = 0
    carnage_bonus = 0
    if session is not None:
        carnage_bonus = consume_carnage_bonus(session, pc.character_id)
        expert_bonus = expert_attack_bonus(
            pc,
            target,
            session,
            missile=missile,
            weapon=weapon,
            gladiator_match=gladiator_match,
        )
        living_foe_count = len(living_enemies)
        expert_bonus += heroic_attack_bonus(
            pc,
            missile=missile,
            living_foe_count=living_foe_count,
            weapon=weapon,
            target=target,
            aggressive_stance=pc.character_id in context.aggressive_stance_attackers,
            carnage_bonus=carnage_bonus,
        )
        if carnage_bonus:
            log.append(f"{pc.name} spends Carnage (+{carnage_bonus} Attack).")
        if session is not None and pc.class_id.lower() == "paladin":
            mounted_bonus = paladin_mounted_attack_bonus(session, pc, outdoors=context.outdoors, target=target)
            if mounted_bonus:
                expert_bonus += mounted_bonus
                log.append(f"{pc.name} attacks from horseback (+{mounted_bonus}).")
        if (
            session.blessed_undead_bonus_character_id == pc.character_id
            and (_is_undead(target) or _is_demon(target))
        ):
            expert_bonus += 1
            log.append(f"Effect: Blessed Temple bonus gives {pc.name} +1 Attack vs {target.name}.")
    personal_secret_bonus = secret_attack_bonus(pc, target)
    weakness_secret_bonus = secret_weakness_attack_bonus(session, target)
    if weakness_secret_bonus:
        log.append(f"Secret knowledge adds +{weakness_secret_bonus} Attack against {target.name}.")
    modifier = (
        class_bonus
        + party_attack_bonus
        + weapon_mod
        + expert_bonus
        + personal_secret_bonus
        + weakness_secret_bonus
        + (2 if enemy_is_held(target) else 0)
        + (pc.level if illusionary_sword_turns(pc) is not None else 0)
        + (1 if use_panache else 0)
        + (2 if use_flip_kick else 0)
        + plan.extra_modifier
    )
    if pending_counter and pending_counter[0] == target.id:
        counter_bonus = pending_counter[1]
        modifier += counter_bonus
        log.append(f"{pc.name} adds +{counter_bonus} from counter-strike.")
        _clear_counter_pending(context, pc.character_id)
        context.gladiator_counter_used.add(pc.character_id)
    if use_gnome_gadget:
        if context.spend_gnome_gadget and context.spend_gnome_gadget(pc):
            modifier += pc.level
            log.append(f"{pc.name} uses a mechanical gadget (+{pc.level} to this attack).")
        else:
            log.append(f"{pc.name} cannot use a gadget (none remaining).")
    if force_unarmed and pc.character_id in context.double_kick_attackers:
        modifier += 1
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
        log.append(f"Attack math: need total >= enemy level {target_level} to hit.")
    if not attack_hits(final_total, target_level):
        if (
            missile
            and session is not None
            and has_skill(pc, "dead_shot")
            and not encounter_spent(session, pc.character_id, "dead_shot")
        ):
            mark_encounter_spent(session, pc.character_id, "dead_shot")
            log.append(f"{pc.name} uses Dead Shot to reroll the ranged attack.")
            total, rolls = roll_exploding_for_level(pc)
            final_total = total + modifier
            if show_rolls:
                log.append(
                    f"Dead Shot reroll: {' + '.join(str(value) for value in rolls)} + "
                    f"{modifier - party_attack_bonus - (1 if use_panache else 0) - (2 if use_flip_kick else 0)} = {final_total}."
                )
        if not attack_hits(final_total, target_level):
            if use_luck_reroll and context.spend_luck and context.spend_luck(pc):
                log.append(f"{pc.name} spends 1 Luck point to reroll the attack.")
                if plan.no_explode:
                    sides = tier_die_sides(pc.level)
                    roll = roll_die(sides)
                    total, rolls = roll, [roll]
                else:
                    total, rolls = roll_exploding_for_level(pc)
                final_total = total + modifier
                if show_rolls:
                    log.append(
                        f"Luck reroll: {' + '.join(str(value) for value in rolls)} + {modifier - party_attack_bonus - (1 if use_panache else 0) - (2 if use_flip_kick else 0)} = {final_total}."
                    )
        if not attack_hits(final_total, target_level):
            if use_flip_kick and rolls[0] == 1:
                context.acrobat_skip_attack[pc.character_id] = True
                log.append(f"{pc.name} loses balance on a 1 — skips the next attack.")
            log.append(f"{pc.name} misses {target.name} with {attack_label}.")
            return living_enemies
    if use_flip_kick and rolls[0] == 1:
        context.acrobat_skip_attack[pc.character_id] = True
        log.append(f"{pc.name} loses balance on a 1 — skips the next attack.")
    return _apply_pc_hit(
        pc,
        target,
        final_total=final_total,
        foe_level=target_level,
        living_enemies=living_enemies,
        log=log,
        subdual=use_subdual and not missile,
        attack_label=attack_label,
        rage_hit=use_rage,
        on_foe_kill=context.on_foe_kill,
        context=context,
        attack_rolls=rolls,
        weapon=weapon,
    )


def _resolve_attacks(
    attack_pairs: list[tuple[EnemyState, PartyMemberState]],
    *,
    party: list[PartyMemberState],
    show_rolls: bool,
    explain_math: bool,
    context: CombatContext,
    withdraw: bool = False,
    defense_bonus: int = 0,
    living_enemies: list[EnemyState] | None = None,
) -> list[str]:
    log: list[str] = []
    living_foe_count = len(living_enemies or [])
    target_melee_counts: dict[str, int] = {}
    for _, target in attack_pairs:
        target_melee_counts[target.character_id] = target_melee_counts.get(target.character_id, 0) + 1
    for enemy, target in attack_pairs:
        if target.current_life <= 0:
            continue
        if context.body_carrier_id and target.character_id == context.body_carrier_id:
            if consume_mirror_image(target):
                log.append(f"A mirror image absorbs {enemy.name}'s attack on {target.name}.")
                continue
            log.append(
                f"{target.name} is hit automatically while carrying a fallen comrade ({enemy.name})."
            )
            if try_sacrifice_shield(context, target, log):
                continue
            target.current_life = max(0, target.current_life - 1)
            if target.current_life == 0:
                log.append(f"{target.name} falls.")
            elif enemy_has_poison(enemy):
                _resolve_poison_rider(
                    enemy,
                    target,
                    log,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    context=context,
                )
            continue
        total, rolls = roll_exploding_for_level(target)
        modifier, _ = _defense_bonus(
            target,
            enemy,
            context=context,
            withdraw=withdraw,
            living_foe_count=living_foe_count,
            melee_attacks_on_target=target_melee_counts.get(target.character_id, 1),
        )
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
            log.append(f"Defense math: need total > enemy level {effective_foe_level(enemy, context.foe_level_penalties)} to avoid damage.")
        enemy_level = effective_foe_level(enemy, context.foe_level_penalties)
        if defense_succeeds(final_total, enemy_level, natural=rolls[0]):
            if (
                target.class_id.lower() == "light_gladiator"
                and len(rolls) > 1
                and target.character_id not in context.gladiator_counter_used
                and _counter_pending(context, target.character_id) is None
            ):
                margin = final_total - enemy_level
                if margin > 0:
                    _set_counter_pending(context, target.character_id, enemy.id, margin)
                    log.append(
                        f"{target.name} banks +{margin} for the next attack vs {enemy.name} (counter-strike)."
                    )
            if (
                len(rolls) > 1
                and living_enemies is not None
                and member_carries_shield(target)
                and context.session is not None
            ):
                skill_flag: str | None = None
                if has_heroic_skill(target, "heroic_shield_bash") and not encounter_spent(
                    context.session, target.character_id, "heroic_shield_bash"
                ):
                    skill_flag = "heroic_shield_bash"
                elif has_skill(target, "shield_bash") and not encounter_spent(
                    context.session, target.character_id, "shield_bash"
                ):
                    skill_flag = "shield_bash"
                if skill_flag:
                    mark_encounter_spent(context.session, target.character_id, skill_flag)
                    bash_label = "Heroic Shield Bash" if skill_flag == "heroic_shield_bash" else "Shield Bash"
                    log.append(f"{target.name} follows the exploding Defense with {bash_label} vs {enemy.name}.")
                    living_enemies[:] = _resolve_pc_attack(
                        target,
                        enemy,
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                        party_attack_bonus=0,
                        subdual=False,
                        missile=False,
                        living_enemies=living_enemies,
                        log=log,
                        wielded_melee=context.wielded_melee,
                        context=context,
                        attack_plan=PlannedAttack(extra_modifier=-1, label=bash_label.lower()),
                    )
            log.append(f"{target.name} defends against {enemy.name}.")
        else:
            use_luck_defense = target.character_id in context.luck_reroll_defenders
            if use_luck_defense and context.spend_luck and context.spend_luck(target):
                log.append(f"{target.name} spends 1 Luck point to reroll Defense.")
                total, rolls = roll_exploding_for_level(target)
                modifier, _ = _defense_bonus(
            target,
            enemy,
            context=context,
            withdraw=withdraw,
            living_foe_count=living_foe_count,
            melee_attacks_on_target=target_melee_counts.get(target.character_id, 1),
        )
                modifier += defense_bonus + (1 if use_panache else 0)
                final_total = total + modifier
                if show_rolls:
                    log.append(
                        f"Luck Defense reroll: {' + '.join(str(value) for value in rolls)} + {modifier} = {final_total}."
                    )
            if defense_succeeds(final_total, enemy_level, natural=rolls[0]):
                if (
                    target.class_id.lower() == "light_gladiator"
                    and len(rolls) > 1
                    and target.character_id not in context.gladiator_counter_used
                    and _counter_pending(context, target.character_id) is None
                ):
                    margin = final_total - enemy_level
                    if margin > 0:
                        _set_counter_pending(context, target.character_id, enemy.id, margin)
                        log.append(
                            f"{target.name} banks +{margin} for the next attack vs {enemy.name} (counter-strike)."
                        )
                log.append(f"{target.name} defends against {enemy.name}.")
                continue
            if consume_mirror_image(target):
                log.append(f"A mirror image absorbs {enemy.name}'s attack on {target.name}.")
                continue
            damage_target = target
            guardian_id = next(
                (
                    bulwark_id
                    for bulwark_id, ally_id in context.sacrifice_guards.items()
                    if ally_id == target.character_id and bulwark_id not in context.sacrifice_used
                ),
                None,
            )
            if guardian_id:
                guardian = next((member for member in party if member.character_id == guardian_id), None)
                if guardian and guardian.current_life > 0 and has_skill(guardian, "sacrifice_defense"):
                    guard_total, guard_rolls = roll_exploding_for_level(guardian)
                    guard_modifier, _ = _defense_bonus(
                        guardian, enemy, context=context, living_foe_count=living_foe_count
                    )
                    guard_final = guard_total + guard_modifier
                    if show_rolls:
                        log.append(
                            f"Sacrifice Defense: {guardian.name} rolls "
                            f"{' + '.join(str(value) for value in guard_rolls)} + {guard_modifier} = {guard_final} "
                            f"vs {enemy.name} (L{enemy_level}) for {target.name}."
                        )
                    if defense_succeeds(guard_final, enemy_level, natural=guard_rolls[0]):
                        damage_target = guardian
                        log.append(f"{guardian.name} intercepts the blow meant for {target.name}.")
                    else:
                        log.append(f"{guardian.name}'s Sacrifice Defense fails; {target.name} is still hit.")
                    context.sacrifice_used.add(guardian_id)
            if try_sacrifice_shield(context, damage_target, log):
                continue
            damage = 1
            if context.session is not None:
                damage, pain_log = adjust_incoming_damage(context.session, damage_target, damage)
                log.extend(pain_log)
            if damage:
                damage_target.current_life = max(0, damage_target.current_life - damage)
                log.append(f"{damage_target.name} takes {damage} damage from {enemy.name}.")
            else:
                log.append(f"{damage_target.name} avoids damage from {enemy.name}.")
            if damage_target.current_life == 0 and context.session is not None:
                try_survive_killing_blow(context.session, damage_target, log)
            if damage_target.current_life == 0:
                if (
                    living_enemies is not None
                    and context.session is not None
                    and has_skill(damage_target, "dying_action")
                    and not encounter_spent(context.session, damage_target.character_id, "dying_action")
                ):
                    mark_encounter_spent(context.session, damage_target.character_id, "dying_action")
                    log.append(f"{damage_target.name} strikes back with Dying Action.")
                    living_enemies[:] = _resolve_pc_attack(
                        damage_target,
                        enemy,
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                        party_attack_bonus=0,
                        subdual=False,
                        missile=False,
                        living_enemies=living_enemies,
                        log=log,
                        wielded_melee=context.wielded_melee,
                        context=context,
                        attack_plan=PlannedAttack(extra_modifier=1, label="dying action"),
                    )
                log.append(f"{damage_target.name} falls.")
            elif enemy_has_poison(enemy):
                _resolve_poison_rider(
                    enemy,
                    damage_target,
                    log,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    context=context,
                )
    return log


def _resolve_poison_rider(
    enemy: EnemyState,
    target: PartyMemberState,
    log: list[str],
    *,
    show_rolls: bool,
    explain_math: bool,
    context: CombatContext,
) -> None:
    log.append(f"Event: {enemy.name}'s poison threatens {target.name}.")
    saved, poison_log = poison_save_succeeds(
        target,
        enemy.level,
        show_rolls=show_rolls,
        explain_math=explain_math,
        session=context.session,
    )
    log.extend(poison_log)
    if saved:
        log.append(f"{target.name} resists {enemy.name}'s poison.")
        return
    target.current_life = max(0, target.current_life - 1)
    log.append(f"Effect: {enemy.name} poisons {target.name}.")
    log.append(f"Effect: {target.name} takes 1 extra damage from {enemy.name}'s poison.")
    if target.current_life == 0:
        log.append(f"{target.name} falls.")
        return
    before = set(target.statuses)
    apply_poison_status(target, enemy.level)
    if set(target.statuses) != before:
        log.append(f"Effect: {target.name} is poisoned (L{enemy.level}).")


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
    living_foe_count = len([enemy for enemy in enemies if enemy.life > 0])
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
                log.append(
                    f"{target.name} is hit automatically while carrying a fallen comrade ({enemy.name}'s ranged attack)."
                )
                if try_sacrifice_shield(context, target, log):
                    foe_ranged_this_round.add(enemy.id)
                    continue
                target.current_life = max(0, target.current_life - 1)
                if target.current_life == 0:
                    log.append(f"{target.name} falls.")
            foe_ranged_this_round.add(enemy.id)
            continue
        total, rolls = roll_exploding_for_level(target)
        modifier, _ = _defense_bonus(
            target, enemy, context=context, melee=False, living_foe_count=living_foe_count
        )
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
            elif try_sacrifice_shield(context, target, log):
                pass
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
    attack_secondary_targets: dict[str, str] | None = None,
) -> CombatRound:
    context = context or CombatContext()
    context.round_show_rolls = show_rolls
    context.round_explain_math = explain_math
    context.round_party_attack_bonus = party_attack_bonus
    context.round_attack_targets = attack_targets
    context.round_attack_secondary_targets = attack_secondary_targets
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

    session = context.session
    if session is not None:
        for cid in context.mass_blessing_users:
            member = next((item for item in party if item.character_id == cid), None)
            if member is not None:
                log.extend(apply_mass_blessing(session, member, context.combat_round))
        blessing_bonus = mass_blessing_attack_bonus(session, context.combat_round)
        if blessing_bonus:
            party_attack_bonus += blessing_bonus
            context.round_party_attack_bonus = party_attack_bonus
        for warder_id, ally_id in context.ward_targets.items():
            session.ward_of_protection_targets[ally_id] = warder_id

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
                ranged_plans = plan_ranged_attacks(pc, context)
                if (
                    ranged_plans
                    and ranged_plans[0].label == "double shot"
                    and context.session is not None
                    and encounter_spent(context.session, pc.character_id, "double_shot")
                ):
                    log.append(f"{pc.name} already used Double Shot this encounter.")
                    continue
                for plan_index, plan in enumerate(ranged_plans):
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
                        attack_plan=plan,
                    )
                if (
                    ranged_plans
                    and ranged_plans[0].label == "double shot"
                    and plan_index == len(ranged_plans) - 1
                    and context.session is not None
                    and has_heroic_skill(pc, "double_shot")
                ):
                    mark_encounter_spent(context.session, pc.character_id, "double_shot")
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
            opening_plans = plan_ranged_attacks(pc, context)
            if (
                opening_plans
                and opening_plans[0].label == "double shot"
                and context.session is not None
                and encounter_spent(context.session, pc.character_id, "double_shot")
            ):
                log.append(f"{pc.name} already used Double Shot this encounter.")
                continue
            for plan_index, plan in enumerate(opening_plans):
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
                    attack_plan=plan,
                )
            if (
                opening_plans
                and opening_plans[0].label == "double shot"
                and plan_index == len(opening_plans) - 1
                and context.session is not None
                and has_heroic_skill(pc, "double_shot")
            ):
                mark_encounter_spent(context.session, pc.character_id, "double_shot")
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
            if pc.character_id in context.continual_light_casters and (
                has_skill(pc, "continual_light") or pc.class_id.lower() == "illusionist"
            ):
                if "Continual Light" not in pc.statuses:
                    pc.statuses.append("Continual Light")
                log.append(f"{pc.name} casts Continual Light (forfeits melee attacks this round).")
        for pc in sorted_party(party):
            if not living_enemies:
                break
            if context.acrobat_skip_attack.get(pc.character_id):
                log.append(f"{pc.name} skips attacking (off balance).")
                context.acrobat_skip_attack.pop(pc.character_id, None)
                continue
            if not can_melee_attack(pc, context):
                if show_rolls:
                    log.append(f"{pc.name} cannot reach melee in this corridor.")
                continue
            if pc.character_id in context.evading_character_ids:
                log.append(f"{pc.name} evades and does not attack this round.")
                continue
            if pc.character_id in context.parrying_character_ids:
                log.append(f"{pc.name} parries instead of attacking (+1 Defense vs melee).")
                continue
            if pc.character_id in context.restore_users and context.session is not None:
                ally_id = context.restore_targets.get(pc.character_id)
                ally = next((item for item in party if item.character_id == ally_id), None) if ally_id else None
                if ally is None:
                    log.append(f"{pc.name} must choose an ally for Restore.")
                else:
                    log.extend(apply_restore_healing(context.session, pc, ally))
                continue
            force_unarmed = pc.character_id in missile_fired_this_round
            if force_unarmed and show_rolls:
                log.append(f"{pc.name} fights unarmed (-2) after shooting; draw a weapon to avoid this.")
            if pc.character_id in context.double_kick_attackers:
                minors = [
                    enemy
                    for enemy in living_enemies
                    if enemy.category in {"vermin", "minions"} and enemy.life > 0
                ]
                chosen_ids = context.double_kick_targets.get(pc.character_id) or []
                if len(chosen_ids) >= 2:
                    picked = [
                        enemy for enemy in living_enemies if enemy.id in chosen_ids[:2] and enemy.life > 0
                    ]
                    if len(picked) >= 2:
                        minors = picked
                if len(minors) < 2:
                    log.append(f"{pc.name} cannot Double Kick — need two minor foes.")
                    continue
                if context.spend_acrobat_trick and not context.spend_acrobat_trick(pc):
                    log.append(f"{pc.name} cannot Double Kick (no Trick points).")
                    continue
                log.append(f"{pc.name} uses Double Kick on two minor foes (-1 unarmed each).")
                for foe in minors[:2]:
                    if not living_enemies:
                        break
                    living_enemies = _resolve_pc_attack(
                        pc,
                        foe,
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                        party_attack_bonus=party_attack_bonus,
                        subdual=subdual,
                        missile=False,
                        living_enemies=living_enemies,
                        log=log,
                        wielded_melee=wielded_melee,
                        force_unarmed=True,
                        context=context,
                        attack_plan=PlannedAttack(label="Double Kick"),
                    )
                continue
            attack_plans = plan_melee_attacks(pc, context)
            if not attack_plans:
                continue
            if (
                attack_plans
                and attack_plans[0].label == "double attack"
                and context.session is not None
                and encounter_spent(context.session, pc.character_id, "double_attack")
            ):
                log.append(f"{pc.name} already used Double Attack this encounter.")
                continue
            if len(attack_plans) > 1 and attack_plans[0].label == "flurry":
                log.append(f"{pc.name} unleashes Flurry of Blows ({len(attack_plans)} attacks).")
            for plan_index, plan in enumerate(attack_plans):
                if not living_enemies:
                    break
                target_map = attack_targets
                if plan.label == "double attack" and plan_index > 0 and context.round_attack_secondary_targets:
                    target_map = context.round_attack_secondary_targets
                living_enemies = _resolve_pc_attack(
                    pc,
                    select_attack_target(pc, living_enemies, target_map),
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    party_attack_bonus=party_attack_bonus,
                    subdual=subdual,
                    missile=False,
                    living_enemies=living_enemies,
                    log=log,
                    wielded_melee=wielded_melee,
                    force_unarmed=force_unarmed and not plan.wielded,
                    context=context,
                    attack_plan=plan,
                )
                if (
                    plan.label == "double attack"
                    and plan_index == len(attack_plans) - 1
                    and context.session is not None
                    and has_skill(pc, "double_attack")
                ):
                    mark_encounter_spent(context.session, pc.character_id, "double_attack")

        living_enemies = [enemy for enemy in enemies if enemy.life > 0]
        if living_enemies and living_party(party):
            minor_enemies = [
                enemy for enemy in living_enemies if enemy.life <= 1 and enemy.category in {"vermin", "minions"}
            ]
            if minor_enemies and initial_minor_count:
                if len(minor_enemies) <= initial_minor_count // 2 and not morale_failed:
                    terrifying_secret = (
                        context.session.terrifying_secret_pending_character_id
                        if context.session is not None
                        else None
                    )
                    if terrifying_secret:
                        actor = next(
                            (member for member in party if member.character_id == terrifying_secret),
                            None,
                        )
                        if show_rolls:
                            label = actor.name if actor is not None else "A hero"
                            log.append(f"Terrifying Secret: {label} forces this morale test to fail.")
                        context.session.terrifying_secret_pending_character_id = None
                        log.append("The remaining foes flee.")
                        for enemy in living_enemies:
                            enemy.life = 0
                        morale_failed = True
                        living_enemies = []
                    else:
                        morale_roll = roll_d6()
                        if context.session is not None:
                            morale_roll += expert_morale_modifier(context.session, party)
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
            tick_enemy_regeneration(enemy, log, show_rolls=show_rolls)
        log.extend(
            tick_poisoned_heroes(
                party,
                show_rolls=show_rolls,
                explain_math=explain_math,
                session=context.session,
            )
        )
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
        _log_multi_attack_assignments(attack_pairs, log)
        log.extend(
            _resolve_attacks(
                attack_pairs,
                party=party,
                show_rolls=show_rolls,
                explain_math=explain_math,
                context=context,
                living_enemies=living_enemies,
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
            total, rolls = roll_exploding_for_level(pc)
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
                party=party,
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
            party=party,
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
