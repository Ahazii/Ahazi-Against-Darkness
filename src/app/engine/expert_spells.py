"""Expert (Abyss) spell cast effects — Four Against the Abyss pp.24–25."""

from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState
from .combat import apply_enemy_damage, enemy_uses_gaze
from .combat_modifiers import spellcasting_modifier
from .dice import roll_d6, roll_die, roll_exploding_for_level
from .expert_skill_effects import _is_vampire
from .spells import SpellOutcome, normalize_spell_name


EXPERT_SPELL_KEYS = frozenset(
    {
        "healing_surge",
        "infallible_missile",
        "lifeforce_control",
        "mass_teleport",
        "aura_of_terror",
        "reverse_gaze",
    }
)


def is_expert_spell(spell_name: str) -> bool:
    return normalize_spell_name(spell_name) in EXPERT_SPELL_KEYS


def aura_of_terror_immune(enemy: EnemyState, *, final_boss: bool = False) -> bool:
    tags = {tag.lower() for tag in enemy.tags}
    if "undead" in tags:
        return True
    if final_boss:
        return True
    if "no_morale" in tags or "fear_attack" in tags:
        return True
    if "fear" in enemy.name.lower():
        return True
    return False


def _pick_foe(enemies: list[EnemyState], foe_id: str | None) -> EnemyState | None:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return None
    if foe_id:
        return next((enemy for enemy in living if enemy.id == foe_id), None)
    return living[0]


def _heal_member(member: PartyMemberState, amount: int, log: list[str]) -> None:
    if member.current_life <= 0:
        return
    before = member.current_life
    member.current_life = min(member.max_life, member.current_life + amount)
    gained = member.current_life - before
    if gained:
        log.append(f"{member.name} heals {gained} Life.")


def cast_healing_surge(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
) -> SpellOutcome:
    for member in party:
        if member.character_id == caster.character_id:
            continue
        _heal_member(member, 2, log)
    for enemy in enemies:
        if enemy.life > 0 and _is_vampire(enemy):
            apply_enemy_damage(enemy, 2, damage_kind="normal")
            log.append(f"{enemy.name} loses 2 Life (vampire).")
    log.append("Healing Surge restores allies; vampires in play suffer 2 Life.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def _infallible_wound(
    target: EnemyState,
    log: list[str],
) -> None:
    if target.life <= 0:
        return
    if target.category in {"vermin", "minions"} and target.life <= 1:
        target.life = 0
        log.append(f"Infallible Missile slays {target.name}.")
    else:
        apply_enemy_damage(target, 1, damage_kind="normal")
        log.append(f"Infallible Missile wounds {target.name} for 1 Life.")
        if target.life <= 0:
            log.append(f"{target.name} is defeated.")


def _chain_target(
    living: list[EnemyState],
    preferred: EnemyState | None,
) -> EnemyState | None:
    if preferred is not None and preferred.life > 0:
        return preferred
    if not living:
        return None
    bosses = [enemy for enemy in living if enemy.category in {"boss", "weird"}]
    if bosses:
        return bosses[0]
    return living[0]


def _run_infallible_missile(
    caster: PartyMemberState,
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_foe_id: str | None,
    label: str,
) -> None:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return
    target = _pick_foe(living, target_foe_id) or living[0]
    log.append(f"{label} strikes {target.name}.")
    _infallible_wound(target, log)
    preferred = target if target.category in {"boss", "weird"} else None
    while any(enemy.life > 0 for enemy in enemies):
        _total, rolls = roll_exploding_for_level(caster.level)
        if show_rolls:
            log.append(
                f"Infallible Missile chain: {caster.name} rolls "
                f"{' + '.join(str(value) for value in rolls)}."
            )
        if len(rolls) <= 1:
            break
        living = [enemy for enemy in enemies if enemy.life > 0]
        chain_target = _chain_target(living, preferred if preferred and preferred.life > 0 else None)
        if chain_target is None:
            break
        _infallible_wound(chain_target, log)
        if chain_target.category in {"boss", "weird"}:
            preferred = chain_target


def cast_infallible_missile(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_foe_id: str | None,
    secondary_foe_id: str | None = None,
) -> SpellOutcome:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        log.append("There are no targets for Infallible Missile.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    missiles = 2 if caster.level >= 8 else 1
    if missiles > 1:
        log.append(f"{caster.name} creates two infallible missiles (L8+).")
    for missile_index in range(missiles):
        if not any(enemy.life > 0 for enemy in enemies):
            break
        label = "Infallible Missile" if missiles == 1 else f"Infallible Missile #{missile_index + 1}"
        _run_infallible_missile(
            caster,
            enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id if missile_index == 0 else secondary_foe_id,
            label=label,
        )
    combat_over = not any(enemy.life > 0 for enemy in enemies)
    return SpellOutcome(log, enemies, party, combat_over=combat_over, spell_consumed=True)


def cast_lifeforce_control(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    target_character_id: str | None,
    target_foe_id: str | None,
    life_transfer_amount: int | None,
) -> SpellOutcome:
    amount = life_transfer_amount or 0
    if amount <= 0:
        log.append("Choose how much Life to transfer with Lifeforce Control.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if amount > caster.current_life:
        log.append(f"{caster.name} cannot transfer more Life than they currently have.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    foe = _pick_foe(enemies, target_foe_id)
    if foe is not None and _is_vampire(foe):
        apply_enemy_damage(foe, amount, damage_kind="normal")
        caster.current_life -= amount
        log.append(f"Lifeforce Control drains {amount} Life from {caster.name} and {foe.name} each.")
        combat_over = not any(enemy.life > 0 for enemy in enemies)
        if foe.life <= 0:
            log.append(f"{foe.name} is defeated.")
        return SpellOutcome(log, enemies, party, combat_over=combat_over, spell_consumed=True)
    ally = next(
        (member for member in party if member.character_id == target_character_id and member.current_life > 0),
        None,
    )
    if ally is None:
        log.append("Choose a living ally or a vampire foe for Lifeforce Control.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    caster.current_life -= amount
    _heal_member(ally, amount, log)
    log.append(f"{caster.name} transfers {amount} Life to {ally.name}.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def cast_mass_teleport(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    teleport_tile_id: str | None,
    teleport_character_ids: list[str] | None,
) -> SpellOutcome:
    if not teleport_tile_id:
        log.append("Choose a visited room for Mass Teleport.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    living = [member for member in party if member.current_life > 0]
    if teleport_character_ids:
        selected = [member for member in living if member.character_id in teleport_character_ids]
    else:
        selected = list(living)
    if caster.current_life > 0 and caster not in selected:
        selected.insert(0, caster)
    if not selected:
        log.append("No one is alive to teleport.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    others = [member for member in selected if member.character_id != caster.character_id]
    cost = len(others)
    if cost and caster.current_life <= cost:
        log.append(f"{caster.name} needs at least {cost + 1} Life to teleport the chosen allies.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if cost:
        caster.current_life -= cost
        log.append(f"{caster.name} takes {cost} Life moving {len(others)} ally/allies.")
    left_behind = [member for member in living if member not in selected]
    if left_behind:
        log.append(
            "Left behind: "
            + ", ".join(member.name for member in left_behind)
            + " — the dangers of the dungeon claim them (Abyss p.25)."
        )
        for member in left_behind:
            member.current_life = 0
    log.append(
        "Mass Teleport carries "
        + ", ".join(member.name for member in selected)
        + " to the chosen room."
    )
    return SpellOutcome(
        log,
        enemies,
        party,
        combat_over=True,
        spell_consumed=True,
        teleport_to_tile_id=teleport_tile_id,
    )


def cast_aura_of_terror(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_foe_id: str | None,
    final_boss: bool,
) -> SpellOutcome:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        log.append("There are no foes to terrify.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    bosses = [enemy for enemy in living if enemy.category in {"boss", "weird"}]
    minors = [enemy for enemy in living if enemy.category in {"vermin", "minions"}]
    if bosses and minors:
        target = _pick_foe(bosses, target_foe_id) or bosses[0]
        log.append("Aura of Terror targets the boss leading the minions.")
    elif bosses:
        target = _pick_foe(bosses, target_foe_id) or bosses[0]
    else:
        target = _pick_foe(minors, target_foe_id) or minors[0]
    if aura_of_terror_immune(target, final_boss=final_boss):
        log.append(f"{target.name} is immune to Aura of Terror.")
        if bosses and minors and target in bosses:
            log.append("The minions do not roll morale while their boss holds.")
        return SpellOutcome(log, enemies, party, spell_consumed=True)
    morale_roll = roll_d6()
    if show_rolls:
        log.append(f"Aura of Terror morale roll: d6 = {morale_roll}.")
    if morale_roll <= 3:
        log.append(f"{target.name} flees from Aura of Terror!")
        if bosses and minors and target in bosses:
            for enemy in living:
                enemy.life = 0
            log.append("The minions flee with their boss.")
        elif target.category in {"vermin", "minions"}:
            for enemy in living:
                if enemy.category in {"vermin", "minions"}:
                    enemy.life = 0
            log.append("The minion group flees.")
        else:
            target.life = 0
        combat_over = not any(enemy.life > 0 for enemy in enemies)
        return SpellOutcome(log, enemies, party, combat_over=combat_over, spell_consumed=True)
    log.append(f"{target.name} stands firm against Aura of Terror.")
    if bosses and minors and target in bosses:
        log.append("The minions do not roll morale while their boss is unaffected.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def cast_reverse_gaze(
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_foe_id: str | None,
) -> SpellOutcome:
    target = _pick_foe(enemies, target_foe_id)
    if target is None:
        log.append("Choose a gaze foe for Reverse Gaze.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    if not enemy_uses_gaze(target):
        log.append(f"{target.name} does not use a gaze attack.")
        return SpellOutcome(log, enemies, party, spell_consumed=False)
    log.append(f"{caster.name} is safe from {target.name}'s gaze this encounter.")
    total = roll_die(8) + spellcasting_modifier(caster)
    if show_rolls:
        log.append(f"Reverse Gaze: d8 + L{caster.level} = {total} vs L{target.level}.")
    if total >= target.level:
        if "medusa" in target.name.lower():
            target.life = 0
            target.tags = list({*target.tags, "petrified"})
            log.append(f"{target.name} is turned to stone by its own gaze.")
        else:
            apply_enemy_damage(target, 2, damage_kind="normal")
            log.append(f"{target.name} is wounded by its own gaze.")
        combat_over = not any(enemy.life > 0 for enemy in enemies)
        return SpellOutcome(log, enemies, party, combat_over=combat_over, spell_consumed=True)
    log.append("Reverse Gaze fails to turn the gaze back.")
    return SpellOutcome(log, enemies, party, spell_consumed=True)


def cast_expert_spell(
    spell_name: str,
    caster: PartyMemberState,
    party: list[PartyMemberState],
    enemies: list[EnemyState],
    log: list[str],
    *,
    show_rolls: bool,
    target_character_id: str | None = None,
    target_foe_id: str | None = None,
    secondary_foe_id: str | None = None,
    life_transfer_amount: int | None = None,
    teleport_tile_id: str | None = None,
    teleport_character_ids: list[str] | None = None,
    final_boss: bool = False,
) -> SpellOutcome | None:
    key = normalize_spell_name(spell_name)
    if key == "healing_surge":
        return cast_healing_surge(caster, party, enemies, log)
    if key == "infallible_missile":
        return cast_infallible_missile(
            caster,
            party,
            enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id,
            secondary_foe_id=secondary_foe_id,
        )
    if key == "lifeforce_control":
        return cast_lifeforce_control(
            caster,
            party,
            enemies,
            log,
            target_character_id=target_character_id,
            target_foe_id=target_foe_id,
            life_transfer_amount=life_transfer_amount,
        )
    if key == "mass_teleport":
        return cast_mass_teleport(
            caster,
            party,
            enemies,
            log,
            teleport_tile_id=teleport_tile_id,
            teleport_character_ids=teleport_character_ids,
        )
    if key == "aura_of_terror":
        return cast_aura_of_terror(
            caster,
            party,
            enemies,
            log,
            show_rolls=show_rolls,
            target_foe_id=target_foe_id,
            final_boss=final_boss,
        )
    if key == "reverse_gaze":
        return cast_reverse_gaze(
            caster, party, enemies, log, show_rolls=show_rolls, target_foe_id=target_foe_id
        )
    return None
