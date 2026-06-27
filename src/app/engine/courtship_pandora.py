"""PANDORA hostility after the Queen's vault betrayal (BoS entry 2, TCOTFD)."""

from __future__ import annotations

from ..schemas import EnemyState, SessionState

# Flower demons that ignore PANDORA vindication (TCOTFD p.49).
PANDORA_HOSTILITY_EXEMPT: frozenset[str] = frozenset(
    {
        "Lady of Lament",
        "Lady of Lament (illusion)",
        "Occlith",
        "Lex the Cambion",
        "Stone Roper",
        "Stone Fiend",
        "Stone Fiends",
        "Necrogaunt",
        "Mirror Demon",
    }
)

PANDORA_REACTION_EXEMPT: frozenset[str] = frozenset({"Lady of Lament", "Lady of Lament (illusion)"})

PANDORA_REACTION_PENALTY = 6


def has_pandora(session: SessionState) -> bool:
    return "PANDORA" in {keyword.upper() for keyword in session.courtship_keywords}


def pandora_reaction_penalty(session: SessionState, template: str) -> int:
    if not has_pandora(session):
        return 0
    if template in PANDORA_REACTION_EXEMPT:
        return 0
    return PANDORA_REACTION_PENALTY


def pandora_forces_fight_to_death(session: SessionState, template: str) -> bool:
    return has_pandora(session) and template not in PANDORA_HOSTILITY_EXEMPT


def pandora_blocks_wooing(session: SessionState, template: str) -> bool:
    return pandora_forces_fight_to_death(session, template)


def prepare_pandora_fight(session: SessionState, enemies: list[EnemyState] | None = None) -> None:
    session.reaction_key = "fight_to_death"
    if enemies is None:
        return
    from .courtship_combat import _courtship_template

    for enemy in enemies:
        if enemy.life <= 0:
            continue
        template = _courtship_template(enemy)
        if pandora_forces_fight_to_death(session, template) and "fight_to_death" not in enemy.tags:
            enemy.tags.append("fight_to_death")


def pandora_status_label(session: SessionState) -> str:
    if not has_pandora(session):
        return ""
    return "PANDORA — flower demons fight to the death (+6 Reaction penalty; Lady of Lament exempt, TCOTFD)."
