"""Hallucination Revelation mechanical benefits (FD p.55)."""

from __future__ import annotations

from ..schemas import SessionState
from .forsaken_depths_content import FD_REVELATION_CHOICES


def spend_fd_hallucination_revelation(
    session: SessionState,
    choice: str,
    *,
    show_rolls: bool = True,
) -> bool:
    if not session.fd_hallucination_revelation_available:
        session.log.append("No Hallucination Revelation benefit is available.")
        return False
    label = FD_REVELATION_CHOICES.get(choice)
    if label is None:
        session.log.append("Unknown Revelation benefit.")
        return False
    session.fd_hallucination_revelation_available = False
    if choice == "negate_ambush":
        session.fd_revelation_negate_ambush = True
    elif choice == "auto_defend":
        session.fd_revelation_auto_defend = True
    elif choice == "auto_save":
        session.fd_revelation_auto_save = True
    elif choice == "auto_search":
        session.fd_revelation_auto_search = True
    elif choice == "preview_room":
        session.fd_revelation_preview_explore = True
    if show_rolls:
        session.log.append(f"Revelation spent: {label} (FD p.55).")
    return True


def consume_fd_revelation_negate_ambush(session: SessionState, *, show_rolls: bool = True) -> bool:
    if not session.fd_revelation_negate_ambush:
        return False
    session.fd_revelation_negate_ambush = False
    if show_rolls:
        session.log.append("Revelation: ambush negated — the party is not surprised (FD p.55).")
    return True


def consume_fd_revelation_auto_defend(session: SessionState, *, show_rolls: bool = True) -> bool:
    if not session.fd_revelation_auto_defend:
        return False
    session.fd_revelation_auto_defend = False
    if show_rolls:
        session.log.append("Revelation: automatic defense success (FD p.55).")
    return True


def consume_fd_revelation_auto_save(session: SessionState, *, show_rolls: bool = True) -> bool:
    if not session.fd_revelation_auto_save:
        return False
    session.fd_revelation_auto_save = False
    if show_rolls:
        session.log.append("Revelation: automatic Save success (FD p.55).")
    return True


def consume_fd_revelation_auto_search(session: SessionState, *, show_rolls: bool = True) -> bool:
    if not session.fd_revelation_auto_search:
        return False
    session.fd_revelation_auto_search = False
    if show_rolls:
        session.log.append("Revelation: automatic search success (FD p.55).")
    return True


def consume_fd_revelation_preview_explore(
    session: SessionState,
    tile,
    *,
    show_rolls: bool = True,
    foe_summary: str = "",
) -> bool:
    if not session.fd_revelation_preview_explore:
        return False
    session.fd_revelation_preview_explore = False
    bits = [tile.content_key or "unknown content"]
    if foe_summary:
        bits.append(foe_summary)
    if tile.trap_key:
        bits.append(f"trap {tile.trap_key}")
    if tile.special_event_key:
        bits.append(f"event {tile.special_event_key}")
    if show_rolls:
        session.log.append(
            f"Revelation preview — {tile.title}: {', '.join(bits)} (FD p.55)."
        )
    return True
