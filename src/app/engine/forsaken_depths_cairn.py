"""Cairn (Ca) river room code — tap precursor energy (FD p.35 / p.40)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..schemas import PartyMemberState, SessionState, TileState
from .combat_modifiers import is_spellcaster, spellcasting_modifier
from .dice import roll_exploding_for_level

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

LIFE_FOR_SPELL_STATUSES = (
    "life for spell",
    "casts with life",
)


def tile_has_cairn(tile: TileState | None) -> bool:
    return bool(tile and "Ca" in (tile.room_codes or []))


def cairn_eligible_caster(member: PartyMemberState) -> bool:
    if member.current_life <= 0 or not is_spellcaster(member):
        return False
    if any(token in status.lower() for status in member.statuses for token in LIFE_FOR_SPELL_STATUSES):
        return False
    return True


def tap_fd_cairn_energy(
    engine: RandomDungeonEngine,
    session: SessionState,
    character_id: str | None,
    spell_name: str | None,
    *,
    show_rolls: bool = True,
    natural_one_choice: str | None = None,
) -> bool:
    if session.mode != "exploration":
        session.log.append("Tap cairn energy during exploration.")
        return False
    tile = engine._current_tile(session)
    if not tile_has_cairn(tile):
        session.log.append("No Cairn (Ca) energy is available on this river stretch (FD p.40).")
        return False
    if not character_id or not spell_name:
        session.log.append("Choose a spellcaster and spell to channel through the Cairn.")
        return False
    member = next((row for row in session.party if row.character_id == character_id), None)
    if member is None:
        session.log.append("That hero is not in the party.")
        return False
    if not cairn_eligible_caster(member):
        session.log.append(
            f"{member.name} cannot tap the Cairn — need a spellcaster who does not already cast using Life (FD p.40)."
        )
        return False
    if spell_name not in member.spells:
        session.log.append(f"{member.name} does not know {spell_name}.")
        return False
    if "life" in spell_name.lower() and "transfer" not in spell_name.lower():
        session.log.append("Spells that cost Life to cast may not use Cairn energy (FD p.40).")
        return False
    hcl = engine._highest_character_level(session.party)
    target = hcl + 5
    total, rolls = roll_exploding_for_level(member)
    modifier = spellcasting_modifier(member)
    if show_rolls:
        session.log.append(
            f"Cairn channel: {member.name} spellcasting {' + '.join(str(v) for v in rolls)} + {modifier} vs {target} (FD p.40)."
        )
    if rolls[0] == 1:
        if natural_one_choice == "spell":
            if member.spells:
                lost = member.spells.pop()
                session.log.append(f"Natural 1 on the Cairn roll — {member.name} loses {lost} as if cast (FD p.40).")
            return True
        if natural_one_choice == "life":
            member.current_life = max(0, member.current_life - 1)
            session.log.append(
                f"Natural 1 on the Cairn roll — {member.name} loses 1 Life ({member.current_life}/{member.max_life}, FD p.40)."
            )
            return True
        session.log.append(
            "Natural 1 on the Cairn roll — choose Lose 1 Life or lose the spell as if cast (FD p.40)."
        )
        session.pending_fd_cairn_natural_one = {
            "character_id": character_id,
            "spell_name": spell_name,
            "tile_id": tile.id,
        }
        return False
    if total + modifier >= target:
        member.current_life = max(0, member.current_life - 1)
        session.log.append(
            f"Cairn success — {member.name} casts {spell_name} without expending it but loses 1 Life "
            f"({member.current_life}/{member.max_life}, FD p.40)."
        )
        return True
    session.log.append(f"Cairn failed — {member.name} may still cast {spell_name} normally (FD p.40).")
    return True
