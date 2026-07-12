from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..schemas import PartyMemberState, SessionState
from .adventure_runtime import log_imported_departure_narrative
from .forsaken_depths_quest import resolve_fd_lady_in_black_oracle_on_exit
from .fungal_rare_items import expire_unused_healers_chanterelle, expire_white_angel_mushrooms
from .hirelings import clear_hirelings_on_dungeon_exit
from .madness import heal_madness_on_dungeon_exit
from .weapon_finishes import tick_leafsteel_after_adventure


@dataclass(frozen=True)
class AdventureCompletionCallbacks:
    """Engine-owned actions needed while closing an adventure session."""

    apply_prisoner_exit_reward: Callable[[SessionState], None]
    trigger_exit_ambush: Callable[[SessionState], bool]
    complete_level_up: Callable[[SessionState, PartyMemberState], None]
    reset_between_foray_resources: Callable[[SessionState], None]


def complete_adventure(
    session: SessionState,
    *,
    callbacks: AdventureCompletionCallbacks,
) -> bool:
    """Apply the normal dungeon-exit sequence and return whether it completed."""
    if session.level_up_spell_pending_character_id:
        pending = next(
            (item for item in session.party if item.character_id == session.level_up_spell_pending_character_id),
            None,
        )
        name = pending.name if pending else "the hero"
        session.log.append(f"Choose a spell for {name} before completing or abandoning the adventure.")
        return False
    if session.xp_rolls_pending > 0 and session.xp_system == "classical":
        session.log.append(
            f"{session.xp_rolls_pending} unassigned XP roll(s) remain. Bank them to a hero "
            "or spend them before completing or abandoning the adventure."
        )
        return False
    if session.rescued_prisoner_active and session.prisoner_reward_choice is None:
        session.log.append(
            "The rescued prisoner must reach the surface. Choose their reward "
            "(magic item + treasure roll, or double held gp) before leaving the dungeon."
        )
        return False
    if session.rescued_prisoner_active:
        callbacks.apply_prisoner_exit_reward(session)

    resolve_fd_lady_in_black_oracle_on_exit(session, show_rolls=True)
    if callbacks.trigger_exit_ambush(session):
        return False

    session.mode = "complete"
    session.camped_outside = False
    explored = len(session.map_state.tiles)
    survivors = [member for member in session.party if member.current_life > 0]
    if session.xp_system == "slow_and_sure" and survivors:
        target = survivors[0]
        callbacks.complete_level_up(session, target)
        session.log.append(f"Slow and Sure: {target.name} gains 1 Level for completing the adventure.")
    callbacks.reset_between_foray_resources(session)
    clear_hirelings_on_dungeon_exit(session)
    for member in survivors:
        member.current_life = member.max_life

    boss_note = " Final Boss slain." if session.final_boss_defeated else ""
    session.summary = [
        f"Explored {explored} map element{'s' if explored != 1 else ''}.{boss_note}",
        f"{len(survivors)} of {len(session.party)} party members left the dungeon.",
        "Between adventures, surviving heroes fully heal and keep treasure already recorded on their sheets.",
    ]
    if session.adventure_type == "imported":
        quest = session.active_quest
        if quest and not quest.completed:
            session.summary.insert(0, "Quest left incomplete.")
        elif quest and quest.completed:
            session.summary.insert(0, "Quest objective complete.")
        log_imported_departure_narrative(session)

    for member in session.party:
        session.log.extend(tick_leafsteel_after_adventure(member))
    session.log.extend(expire_white_angel_mushrooms(session.party))
    session.log.extend(expire_unused_healers_chanterelle(session.party))
    session.log.append("The party leaves the dungeon. Surviving heroes fully heal between adventures.")
    session.secret_yummy_meal_active = False
    session.log.extend(heal_madness_on_dungeon_exit(session))
    session.log.append("Spells, prayers, rest, and per-adventure class resources refresh between adventures.")
    return True
