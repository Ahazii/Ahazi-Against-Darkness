"""Satyr outdoor seduction and woo (TCOTFD p.11-12)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..schemas import EnemyState, PartyMemberState, SessionState, TileState
from .courtship_classes import is_satyr
from .dice import roll_d6

if TYPE_CHECKING:
    from .random_dungeon import RandomDungeonEngine

IMMUNE_NAME_TOKENS: tuple[str, ...] = (
    "dragon",
    "ghost",
    "chimera",
    "gremlin",
    "golem",
    "construct",
    "automaton",
    "undead",
    "skeleton",
    "zombie",
    "wraith",
    "specter",
    "phantom",
)

ALWAYS_FEMALE_NAME_TOKENS: tuple[str, ...] = (
    "medusa",
    "she-orc",
    "she orc",
    "ogress",
    "salamandrine oracle",
)

SEX_ROLL_FEMALE_NAME_TOKENS: tuple[str, ...] = (
    "vampire",
    "orc",
    "ogre",
    "hag",
    "witch",
    "amazon",
    "nymph",
    "harpy",
    "succubus",
)

NEAR_HUMANOID_CATEGORIES: frozenset[str] = frozenset({"minions", "vermin", "boss", "weird"})


def _living_satyr(party: list[PartyMemberState]) -> PartyMemberState | None:
    for member in party:
        if member.current_life <= 0:
            continue
        if not is_satyr(member):
            continue
        if any("undead" in status.lower() for status in member.statuses):
            continue
        return member
    return None


def _foe_sex_roll(session: SessionState, enemy: EnemyState) -> int:
    rolls = session.satyr_foe_sex_rolls
    if enemy.id not in rolls:
        rolls[enemy.id] = roll_d6()
    return int(rolls[enemy.id])


def satyr_pheromone_immune(enemy: EnemyState) -> bool:
    name = enemy.name.lower()
    if any(token in name for token in IMMUNE_NAME_TOKENS):
        return True
    if enemy.category.lower() in {"trap", "event", "plant"}:
        return True
    return False


def satyr_pheromone_eligible_female(
    session: SessionState,
    enemy: EnemyState,
    *,
    show_rolls: bool = False,
    log: list[str] | None = None,
) -> bool:
    if satyr_pheromone_immune(enemy):
        return False
    name = enemy.name.lower()
    if any(token in name for token in ALWAYS_FEMALE_NAME_TOKENS):
        return True
    if enemy.category.lower() not in NEAR_HUMANOID_CATEGORIES:
        return False
    sex_roll = _foe_sex_roll(session, enemy)
    if show_rolls and log is not None:
        log.append(f"{enemy.name} sex roll d6 = {sex_roll} (1–3 female, TCOTFD p.11).")
    return sex_roll <= 3


def group_eligible_for_satyr_woo(session: SessionState, enemies: list[EnemyState]) -> bool:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return False
    return all(satyr_pheromone_eligible_female(session, enemy) for enemy in living)


def try_satyr_auto_seduce_on_encounter(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    *,
    show_rolls: bool = True,
) -> bool:
    """Automatic pheromone seduction outside the Demesne (TCOTFD p.11). Returns True if woo starts."""
    if session.courtship_demesne_active or session.courtship_woo_active:
        return False
    if session.mode != "exploration":
        return False
    satyr = _living_satyr(session.party)
    if satyr is None:
        return False
    living = [enemy for enemy in tile.enemies if enemy.life > 0]
    if not living:
        return False
    if all(enemy.name in session.satyr_peaceful_foe_names for enemy in living):
        session.log.append(
            "Former lovers greet the satyr peacefully — no fight while he remains in the party (TCOTFD p.11)."
        )
        tile.enemies.clear()
        tile.initial_enemy_count = 0
        tile.resolved = True
        return True
    log: list[str] = []
    if not group_eligible_for_satyr_woo(session, living):
        return False
    for enemy in living:
        satyr_pheromone_eligible_female(session, enemy, show_rolls=show_rolls, log=log)
    target_level = max(enemy.level for enemy in living)
    roll = roll_d6()
    total = roll + satyr.level
    if show_rolls:
        log.append(
            f"Satyr pheromone: {satyr.name} rolls d6 = {roll} + L{satyr.level} = {total} "
            f"vs L{target_level} ({living[0].name} and company, TCOTFD p.11)."
        )
    session.log.extend(log)
    if total < target_level:
        if show_rolls:
            session.log.append("The pheromones fail to sway them — combat as usual (TCOTFD p.11).")
        return False
    session.log.append(
        f"{satyr.name}'s pheromones overwhelm the group — reaction seduce (automatic, TCOTFD p.11)."
    )
    return start_outdoor_satyr_woo(engine, session, tile, satyr, living, show_rolls=show_rolls)


def start_outdoor_satyr_woo(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    satyr: PartyMemberState,
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
) -> bool:
    from .courtship_demesne import COURTSHIP_WOO_SUCCESSES_REQUIRED, _clear_courtship_woo

    _clear_courtship_woo(session)
    label = enemies[0].name if len(enemies) == 1 else f"{enemies[0].name} and company"
    category = enemies[0].category or "minions"
    session.courtship_woo_active = True
    session.courtship_woo_outdoor = True
    session.courtship_woo_template = label
    session.courtship_woo_category = category
    session.courtship_woo_speaker_id = satyr.character_id
    session.courtship_woo_dominant_blocked = False
    session.courtship_woo_dominant_stance = False
    session.courtship_woo_passionate_stance = False
    session.courtship_woo_giving_penalty = 0
    session.courtship_woo_withholding_penalty = 0
    session.courtship_woo_successes = 0
    for member in session.party:
        if member.current_life <= 0 or member.character_id == satyr.character_id:
            continue
        if is_satyr(member):
            continue
        member.current_life = min(member.max_life, member.current_life + 1)
        if show_rolls:
            session.log.append(f"{member.name} rests on guard (+1 Life, TCOTFD p.29).")
    if show_rolls:
        session.log.append(
            f"{satyr.name} seduces {label} outside the Demesne — "
            f"{COURTSHIP_WOO_SUCCESSES_REQUIRED} successful Giving rolls win her treasure peacefully (TCOTFD p.11)."
        )
    return True


def complete_outdoor_satyr_woo(
    engine: RandomDungeonEngine,
    session: SessionState,
    tile: TileState,
    satyr: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    """Pleased she-monsters grant treasure and part peacefully (TCOTFD p.11)."""
    log: list[str] = []
    label = session.courtship_woo_template or "she-monsters"
    for enemy in list(tile.enemies):
        if enemy.life > 0 and enemy.name not in session.satyr_peaceful_foe_names:
            session.satyr_peaceful_foe_names.append(enemy.name)
        enemy.life = 0
    tile.defeated_enemies = list(tile.enemies)
    engine._award_treasure(session, tile, show_rolls=show_rolls)
    tile.resolved = True
    log.append(
        f"{label} is pleased by {satyr.name} — she freely gives her treasure and departs in tears "
        "(outdoor treasure, not Demesne gift, TCOTFD p.11)."
    )
    if tile.treasure_summary:
        log.append(f"Treasure: {tile.treasure_summary}")
    tile.enemies.clear()
    tile.initial_enemy_count = 0
    session.courtship_woo_outdoor = False
    return log


def outdoor_withholding_exhaustion(session: SessionState) -> bool:
    """Failed Withholding outside the Demesne costs 1 Life, not Melancholy (TCOTFD p.11)."""
    return not session.courtship_demesne_active
