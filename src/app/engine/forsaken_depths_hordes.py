"""Forsaken Depths horde-specific combat helpers (FD p.42)."""

from __future__ import annotations

from ..schemas import EnemyState, PartyMemberState, SessionState, TileState
from .combat import CombatContext, _defense_bonus, defense_succeeds, party_life_change_text
from .dice import roll_exploding_for_level
from .experience import tier_for_level
from .party_life import apply_party_life_loss

FD_HORDE_VOLLEY_USED_TAG = "fd_horde_opening_volley_used"
FD_HORDE_WEAPON_SALVAGE_OBJECT = "FD horde weapons: light weapon and hand weapon for each party member"


def _tags(enemy: EnemyState) -> set[str]:
    return {str(tag).lower() for tag in enemy.tags}


def _living_party(session: SessionState, tile: TileState) -> list[PartyMemberState]:
    present = set(getattr(tile, "party_character_ids", []) or [])
    members = session.party
    if present:
        members = [member for member in members if member.character_id in present]
    return [member for member in members if member.current_life > 0]


def _volley_targets(enemy: EnemyState, party: list[PartyMemberState]) -> list[PartyMemberState]:
    tags = _tags(enemy)
    if "fd_horde_dark_elf_volley" in tags:
        max_level = max((member.level for member in party), default=1)
        attacks = 3 if tier_for_level(max_level) >= 3 else 2
        return [member for member in party for _ in range(attacks)]
    if "fd_horde_goblin_javelins" in tags:
        targets = list(party)
        highest = max(party, key=lambda member: (member.current_life, -member.marching_order), default=None)
        if highest is not None:
            targets.append(highest)
        return targets
    return []


def apply_fd_horde_opening_volleys(
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    log: list[str] = []
    party = _living_party(session, tile)
    if not party:
        return log
    context = CombatContext(session=session, tile_type=tile.tile_type)
    for enemy in tile.enemies:
        if enemy.life <= 0 or FD_HORDE_VOLLEY_USED_TAG in enemy.tags:
            continue
        targets = _volley_targets(enemy, party)
        if not targets:
            continue
        enemy.tags.append(FD_HORDE_VOLLEY_USED_TAG)
        if "fd_horde_dark_elf_volley" in _tags(enemy):
            log.append(
                f"FD horde volley: {enemy.name} fires hand-crossbow bolts before melee (FD p.42)."
            )
        else:
            log.append(f"FD horde volley: {enemy.name} throws javelins before melee (FD p.42).")
        deaths_before = {member.character_id for member in party if member.current_life <= 0}
        for target in targets:
            if target.current_life <= 0:
                continue
            total, rolls = roll_exploding_for_level(target, session=session, log=log)
            modifier, _ = _defense_bonus(target, enemy, context=context)
            final_total = total + modifier
            if show_rolls:
                log.append(
                    f"Volley Defense: {target.name} vs {enemy.name}: "
                    f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total}."
                )
            if defense_succeeds(final_total, enemy.level, natural=rolls[0]):
                log.append(f"{target.name} avoids the volley.")
                continue
            before = target.current_life
            applied = apply_party_life_loss(session, target, 1, log=log)
            log.append(
                f"{target.name} takes {applied} damage from the volley "
                f"{party_life_change_text(target, before)}."
            )
            if target.current_life == 0:
                log.append(f"{target.name} falls.")
        if "fd_horde_dark_elf_volley" in _tags(enemy):
            deaths_after = {member.character_id for member in party if member.current_life <= 0}
            if deaths_after - deaths_before and "fd_dark_elf_morale_plus_1" not in enemy.tags:
                enemy.tags.append("fd_dark_elf_morale_plus_1")
                log.append("Dark elf horde morale marker: +1 Morale because the volley killed a character (FD p.42).")
    return log


def add_fd_horde_weapon_salvage(tile: TileState, defeated: list[EnemyState]) -> list[str]:
    if not any("horde" in _tags(enemy) and "forsaken_depths" in _tags(enemy) for enemy in defeated):
        return []
    if FD_HORDE_WEAPON_SALVAGE_OBJECT not in tile.objects:
        tile.objects.append(FD_HORDE_WEAPON_SALVAGE_OBJECT)
    return [
        "FD horde salvage: after defeating a Horde, the party may pick up one Light weapon and one hand weapon for each party member (FD p.42)."
    ]
