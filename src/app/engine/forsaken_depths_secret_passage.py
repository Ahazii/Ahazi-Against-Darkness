"""Forsaken Depths ruins secret passage (fd_ruins_content_table roll 12, FD p.56)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ..schemas import EnemyState, SessionState, TileState
from .forsaken_depths_map import is_fd_ruleset

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

FD_SECRET_PASSAGE_CLUES = 3
FD_SECRET_PASSAGE_TRAPS_REQUIRED = 3
FD_SECRET_PASSAGE_WEIRD_REQUIRED = 2

FdSecretPassageDestination = Literal["abyss", "netherworld", "citadel"]


def fd_secret_passage_active(session: SessionState) -> bool:
    return bool(is_fd_ruleset(session) and session.fd_secret_passage_tile_id)


def fd_secret_passage_on_tile(session: SessionState, tile: TileState | None) -> bool:
    return bool(tile and session.fd_secret_passage_tile_id == tile.id and is_fd_ruleset(session))


def offer_fd_ruins_secret_passage(session: SessionState, tile: TileState, *, show_rolls: bool = True) -> None:
    tile.fd_secret_passage_room = True
    if "Secret Passage" not in tile.objects:
        tile.objects.append("Secret Passage")
    session.fd_secret_passage_tile_id = tile.id
    session.fd_secret_passage_traps_cleared = 0
    session.fd_secret_passage_weird_defeated = 0
    session.fd_secret_passage_unlocked = False
    if show_rolls:
        session.log.append(
            "Forsaken Ruins secret passage (FD p.56): leads to the Abyss, Netherworld, or Citadel. "
            f"Unlock with {FD_SECRET_PASSAGE_CLUES} Clues, "
            f"{FD_SECRET_PASSAGE_TRAPS_REQUIRED} cleared traps of level HCL+3+, "
            f"or {FD_SECRET_PASSAGE_WEIRD_REQUIRED} defeated Weird Monsters."
        )


def fd_secret_passage_progress_label(session: SessionState) -> str:
    if not fd_secret_passage_active(session):
        return ""
    if session.fd_secret_passage_unlocked:
        return "Secret passage unlocked — choose destination"
    traps = session.fd_secret_passage_traps_cleared
    weird = session.fd_secret_passage_weird_defeated
    return (
        f"Secret passage: {traps}/{FD_SECRET_PASSAGE_TRAPS_REQUIRED} HCL+3 traps · "
        f"{weird}/{FD_SECRET_PASSAGE_WEIRD_REQUIRED} weirds · "
        f"or {FD_SECRET_PASSAGE_CLUES} Clues"
    )


def _unlock_fd_secret_passage(session: SessionState, *, show_rolls: bool, reason: str) -> None:
    session.fd_secret_passage_unlocked = True
    if show_rolls:
        session.log.append(
            f"The Forsaken secret passage opens ({reason}). "
            "Choose Abyss, Netherworld, or Citadel (FD p.56)."
        )


def try_fd_secret_passage_unlock(session: SessionState, *, show_rolls: bool = True) -> bool:
    if not fd_secret_passage_active(session) or session.fd_secret_passage_unlocked:
        return False
    if session.fd_secret_passage_traps_cleared >= FD_SECRET_PASSAGE_TRAPS_REQUIRED:
        _unlock_fd_secret_passage(session, show_rolls=show_rolls, reason="traps cleared")
        return True
    if session.fd_secret_passage_weird_defeated >= FD_SECRET_PASSAGE_WEIRD_REQUIRED:
        _unlock_fd_secret_passage(session, show_rolls=show_rolls, reason="weird monsters defeated")
        return True
    return False


def note_fd_secret_passage_trap_cleared(
    session: SessionState,
    *,
    trap_level: int,
    hcl: int,
    show_rolls: bool = True,
) -> None:
    if not fd_secret_passage_active(session) or session.fd_secret_passage_unlocked:
        return
    if trap_level < hcl + 3:
        return
    session.fd_secret_passage_traps_cleared += 1
    if show_rolls:
        session.log.append(
            f"Secret passage progress: {session.fd_secret_passage_traps_cleared}/"
            f"{FD_SECRET_PASSAGE_TRAPS_REQUIRED} HCL+3+ traps cleared (FD p.56)."
        )
    try_fd_secret_passage_unlock(session, show_rolls=show_rolls)


def note_fd_secret_passage_weird_defeated(
    session: SessionState,
    enemy: EnemyState,
    *,
    show_rolls: bool = True,
) -> None:
    if not fd_secret_passage_active(session) or session.fd_secret_passage_unlocked:
        return
    if enemy.category != "weird":
        return
    session.fd_secret_passage_weird_defeated += 1
    if show_rolls:
        session.log.append(
            f"Secret passage progress: {session.fd_secret_passage_weird_defeated}/"
            f"{FD_SECRET_PASSAGE_WEIRD_REQUIRED} Weird Monsters defeated (FD p.56)."
        )
    try_fd_secret_passage_unlock(session, show_rolls=show_rolls)


def unlock_fd_secret_passage_with_clues(
    engine: RandomDungeonEngine,
    session: SessionState,
    *,
    show_rolls: bool = True,
) -> bool:
    if not fd_secret_passage_active(session):
        session.log.append("No Forsaken secret passage is awaiting unlock.")
        return False
    if session.fd_secret_passage_unlocked:
        session.log.append("The secret passage is already open.")
        return False
    if session.clues_found < FD_SECRET_PASSAGE_CLUES:
        session.log.append(
            f"Need {FD_SECRET_PASSAGE_CLUES} Clues to open the passage (party has {session.clues_found}, FD p.56)."
        )
        return False
    if not engine._spend_clues(session, FD_SECRET_PASSAGE_CLUES):
        session.log.append(
            f"Need {FD_SECRET_PASSAGE_CLUES} Clues to open the passage (party has {session.clues_found})."
        )
        return False
    _unlock_fd_secret_passage(session, show_rolls=show_rolls, reason=f"{FD_SECRET_PASSAGE_CLUES} Clues spent")
    return True


def choose_fd_secret_passage_destination(
    engine: RandomDungeonEngine,
    session: SessionState,
    destination: str | None,
    *,
    show_rolls: bool = True,
    explain_math: bool = False,
) -> bool:
    if session.mode != "exploration":
        session.log.append("Choose a secret-passage destination during exploration.")
        return False
    tile_id = session.fd_secret_passage_tile_id
    if not tile_id or not session.fd_secret_passage_unlocked:
        session.log.append("The Forsaken secret passage is not ready for a destination choice.")
        return False
    tile = engine._tile_by_id(session, tile_id)
    if tile is None:
        clear_fd_secret_passage_state(session)
        session.log.append("The secret passage tile is no longer on the map.")
        return False
    if destination not in {"abyss", "netherworld", "citadel"}:
        session.log.append("Choose Abyss, Netherworld, or Citadel for the secret passage.")
        return False

    previous = session.environment
    if destination == "abyss":
        ok = engine._open_secret_passage_destination(
            session,
            tile,
            "fungal_grottoes",
            previous_environment=previous,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if ok and show_rolls:
            session.log.append("Secret passage to the Abyss — fungal grottoes environment (FD p.56).")
    elif destination == "netherworld":
        ok = engine._open_secret_passage_destination(
            session,
            tile,
            "caverns",
            previous_environment=previous,
            show_rolls=show_rolls,
            explain_math=explain_math,
        )
        if ok and show_rolls:
            session.log.append("Secret passage to the Netherworld — caverns environment (FD p.56).")
    else:
        from .forsaken_depths_content import roll_fd_citadel

        if not session.fd_citadel_type:
            roll_fd_citadel(engine, session, tile, show_rolls=show_rolls)
        session.fd_citadel_entry_tile_id = tile.id
        if show_rolls:
            session.log.append(
                "Secret passage to a Citadel — use Enter Citadel sheet on this map element (FD p.56)."
            )
        ok = True

    if ok:
        clear_fd_secret_passage_state(session)
    return ok


def clear_fd_secret_passage_state(session: SessionState) -> None:
    session.fd_secret_passage_tile_id = None
    session.fd_secret_passage_traps_cleared = 0
    session.fd_secret_passage_weird_defeated = 0
    session.fd_secret_passage_unlocked = False
