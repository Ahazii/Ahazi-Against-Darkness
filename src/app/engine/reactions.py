from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState
from .dice import roll_d6


@dataclass
class ReactionOutcome:
    key: str
    result: str
    foes_first: bool = False
    bribe_gold: int = 0
    ends_combat: bool = False
    peaceful: bool = False


def reaction_table_for_enemies(enemies: list[EnemyState]) -> str:
    if not enemies:
        return "default_reaction_table"
    categories = {enemy.category for enemy in enemies}
    if categories <= {"vermin"}:
        return "vermin_reaction_table"
    if categories <= {"minions"} or "minion" in categories:
        return "minion_reaction_table"
    if any(enemy.category in {"boss", "weird"} for enemy in enemies):
        return "major_reaction_table"
    return "default_reaction_table"


def resolve_bribe_gold(row: dict, *, hcl: int, foe_count: int) -> int:
    if row.get("gold_per_foe"):
        return int(row["gold_per_foe"]) * max(1, foe_count)
    if row.get("gold"):
        formula = str(row["gold"])
        if formula == "HCL*5":
            return hcl * 5
    return hcl * 5


def build_reaction_outcome(row: dict, *, hcl: int, foe_count: int) -> ReactionOutcome:
    key = row["key"]
    bribe_gold = resolve_bribe_gold(row, hcl=hcl, foe_count=foe_count) if key == "bribe" else 0
    ends_combat = key in {"flee", "peaceful", "ignore", "offer_food"}
    peaceful = key in {"peaceful", "ignore", "offer_food"}
    return ReactionOutcome(
        key=key,
        result=row["result"],
        foes_first=bool(row.get("foes_first")) or key in {"fight", "fight_to_death", "puzzle"},
        bribe_gold=bribe_gold,
        ends_combat=ends_combat,
        peaceful=peaceful,
    )


def flee_if_outnumbered(enemies: list[EnemyState], party: list[PartyMemberState]) -> bool:
    living = sum(1 for member in party if member.current_life > 0)
    return len(enemies) < living
