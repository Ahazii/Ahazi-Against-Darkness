from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re

from ..schemas import EnemyState, PartyMemberState, SessionState, TileState
from .class_abilities import FOOD_RATION_NAMES, count_food_rations, consume_food_rations
from .consumables import mushroom_kind
from .equipment_effects import consume_fools_gold, party_has_fools_gold
from .dice import roll_d6
from .magic_weapons import is_magic_weapon
from .dungeon_table_roller import parse_roll_range

REACTION_NAME_ALIASES: dict[str, str] = {}

BRIBE_WEAPON_SKIP = (
    "armor",
    "shield",
    "bandage",
    "rope",
    "lockpick",
    "holy",
    "spellbook",
    "ink",
    "ration",
    "potion",
    "poison",
    "lantern",
    "symbol",
    "crystal",
    "treasure",
    "gold",
    "coin",
    "key",
    "scroll",
)

BRIBE_WEAPON_KEYWORDS = (
    "weapon",
    "sword",
    "dagger",
    "mace",
    "staff",
    "bow",
    "axe",
    "scimitar",
    "spear",
    "hammer",
    "club",
    "blade",
    "crossbow",
    "sling",
    "whip",
    "flail",
)


@dataclass
class ReactionOutcome:
    key: str
    result: str
    foes_first: bool = False
    bribe_gold: int = 0
    bribe_weapons: int = 0
    bribe_gold_per_foe: int = 0
    bribe_weapons_per_foe: int = 0
    ends_combat: bool = False
    peaceful: bool = False


@dataclass
class ReactionSource:
    table_name: str | None
    inline_rows: list[dict] | None
    label: str


def end_peaceful_encounter(
    session: SessionState,
    tile: TileState,
    *,
    record_progress: Callable[[SessionState], None],
) -> None:
    """Close a non-hostile reaction and clear its encounter-only state."""
    tile.enemies = []
    session.reaction_pending = False
    session.reaction_checked = False
    session.reaction_key = None
    session.reaction_bribe_gold = 0
    session.reaction_bribe_weapons = 0
    session.reaction_bribe_gold_per_foe = 0
    session.reaction_bribe_weapons_per_foe = 0
    session.reaction_bribe_foe_count = 0
    session.reaction_trade_stock = []
    session.reaction_trade_active = False
    session.reaction_no_fools_gold = False
    session.reaction_sleep_attack_bonus = 0
    session.foes_strike_first = False
    session.foe_flee_strike_pending = False
    session.secret_weakness_foe_id = None
    session.secret_weakness_character_id = None
    session.secret_enemy_foe_id = None
    session.secret_enemy_character_id = None
    session.secret_chaos_fanatics_active = False
    session.terrifying_secret_pending_character_id = None
    session.combat_round = 0
    session.mode = "exploration"
    session.log.append("The encounter ends peacefully.")
    record_progress(session)


def is_bribe_weapon(item: str) -> bool:
    lower = item.lower()
    if "blade poison" in lower:
        return False
    if is_magic_weapon(item):
        return True
    if any(skip in lower for skip in BRIBE_WEAPON_SKIP):
        if "hand weapon" in lower or "heavy weapon" in lower or "light weapon" in lower:
            return True
        return False
    return any(keyword in lower for keyword in BRIBE_WEAPON_KEYWORDS)


def count_bribe_food_value(party: list[PartyMemberState]) -> int:
    total = count_food_rations(party)
    for member in party:
        if member.current_life <= 0:
            continue
        for item in member.inventory:
            if mushroom_kind(item) == "brown_cap_delight":
                total += 3
    return total


def consume_bribe_food_value(party: list[PartyMemberState], count: int) -> bool:
    if count <= 0:
        return True
    if count_bribe_food_value(party) < count:
        return False
    remaining = count
    for member in party:
        if remaining <= 0:
            break
        if member.current_life <= 0:
            continue
        kept: list[str] = []
        for item in member.inventory:
            if remaining > 0 and any(name in item.lower() for name in FOOD_RATION_NAMES):
                remaining -= 1
                continue
            kept.append(item)
        member.inventory = kept
    if remaining <= 0:
        return True
    for member in party:
        if remaining <= 0:
            break
        if member.current_life <= 0:
            continue
        index = 0
        while index < len(member.inventory) and remaining > 0:
            item = member.inventory[index]
            if mushroom_kind(item) == "brown_cap_delight":
                member.inventory.pop(index)
                remaining -= 3
                continue
            index += 1
    return remaining <= 0


def count_party_weapons(party: list[PartyMemberState]) -> int:
    total = 0
    for member in party:
        if member.current_life <= 0:
            continue
        total += sum(1 for item in member.inventory if is_bribe_weapon(item))
    return total


def collect_party_weapons(party: list[PartyMemberState]) -> list[tuple[PartyMemberState, int]]:
    found: list[tuple[PartyMemberState, int]] = []
    for member in sorted(party, key=lambda item: item.marching_order):
        if member.current_life <= 0:
            continue
        for index, item in enumerate(member.inventory):
            if is_bribe_weapon(item):
                found.append((member, index))
    return found


def dwarf_miser_blocks_bribe(party: list[PartyMemberState]) -> bool:
    return sum(1 for member in party if member.current_life > 0 and member.class_id.lower() == "dwarf") >= 2


def is_bribe_reaction(key: str | None) -> bool:
    if not key:
        return False
    return key == "bribe" or key.startswith("bribe_")


def normalize_reaction_row(row: dict) -> dict:
    if row.get("bribe_magic_item"):
        return {**row, "key": "bribe_magic_item"}
    return row


def reaction_table_for_category(enemies: list[EnemyState]) -> str:
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


def reaction_table_for_enemies(enemies: list[EnemyState]) -> str:
    return reaction_table_for_category(enemies)


def resolve_reaction_source(
    enemies: list[EnemyState],
    reaction_tables: dict[str, list[dict]],
) -> ReactionSource:
    living = [enemy for enemy in enemies if enemy.life > 0]
    if not living:
        return ReactionSource("default_reaction_table", None, "default")

    tagged_tables = {
        tag.split(":", 1)[1]
        for enemy in living
        for tag in enemy.tags
        if tag.startswith("reaction_table:")
    }
    if len(tagged_tables) == 1:
        resolved = next(iter(tagged_tables))
        inline_rows = reaction_tables.get(resolved)
        if inline_rows:
            return ReactionSource(None, inline_rows, resolved)

    names = {enemy.name for enemy in living}
    if len(names) == 1:
        name = next(iter(names))
        resolved = REACTION_NAME_ALIASES.get(name, name)
        inline_rows = reaction_tables.get(resolved)
        if inline_rows:
            return ReactionSource(None, inline_rows, resolved)

    table_name = reaction_table_for_category(living)
    return ReactionSource(table_name, None, table_name)


def lookup_reaction_row(rows: list[dict], roll: int) -> dict | None:
    for row in rows:
        low, high = parse_roll_range(str(row["roll"]))
        if low <= roll <= high:
            return row
    return None


def apply_reaction_overlays(row: dict | None, enemies: list[EnemyState], roll: int) -> dict | None:
    """Apply global reaction rules that sit above bestiary-specific rows."""
    if row is None:
        return None
    living = [enemy for enemy in enemies if enemy.life > 0]
    if any("abyss" in {tag.lower() for tag in enemy.tags} for enemy in living):
        return row
    categories = {enemy.category for enemy in living}
    if roll == 1 and categories and categories <= {"minions"} and row.get("key") != "capture":
        overlaid = dict(row)
        overlaid["key"] = "capture"
        overlaid["result"] = "The minions try to take captives! Their attacks are non-lethal."
        overlaid["foes_first"] = True
        overlaid["source_page"] = 102
        overlaid["overrides_reaction_key"] = row.get("key")
        return overlaid
    return row


def resolve_bribe_gold(row: dict, *, hcl: int, foe_count: int) -> int:
    if row.get("gold_per_foe"):
        return int(row["gold_per_foe"]) * max(1, foe_count)
    if row.get("gold"):
        if isinstance(row["gold"], int):
            return row["gold"]
        formula = str(row["gold"])
        if formula == "HCL*5":
            return hcl * 5
        if formula.isdigit():
            return int(formula)
        dice_match = re.fullmatch(r"(\d+)d6([+-]\d+)?", formula.replace(" ", "").lower())
        if dice_match:
            dice_count = int(dice_match.group(1))
            modifier = int(dice_match.group(2) or 0)
            return sum(roll_d6() for _ in range(dice_count)) + modifier
    if row.get("gold_dice"):
        dice = str(row["gold_dice"]).lower()
        if dice == "d6":
            return roll_d6()
        if dice.endswith("d6") and dice[:-2].isdigit():
            return sum(roll_d6() for _ in range(int(dice[:-2])))
    return hcl * 5


def resolve_bribe_weapons(row: dict, *, foe_count: int) -> int:
    if row.get("weapons_per_foe"):
        return int(row["weapons_per_foe"]) * max(1, foe_count)
    return 0


def build_reaction_outcome(row: dict, *, hcl: int, foe_count: int) -> ReactionOutcome:
    key = row["key"]
    gold_per_foe = int(row.get("gold_per_foe", 0)) if key == "bribe" else 0
    weapons_per_foe = int(row.get("weapons_per_foe", 0)) if key == "bribe" else 0
    bribe_gold = resolve_bribe_gold(row, hcl=hcl, foe_count=foe_count) if key == "bribe" else 0
    bribe_weapons = resolve_bribe_weapons(row, foe_count=foe_count) if key == "bribe" else 0
    ends_combat = key in {"flee", "peaceful", "ignore", "offer_food"}
    peaceful = key in {"peaceful", "ignore", "offer_food"}
    return ReactionOutcome(
        key=key,
        result=row["result"],
        foes_first=bool(row.get("foes_first")) or key in {"fight", "fight_to_death", "puzzle", "magic_challenge"},
        bribe_gold=bribe_gold,
        bribe_weapons=bribe_weapons,
        bribe_gold_per_foe=gold_per_foe,
        bribe_weapons_per_foe=weapons_per_foe,
        ends_combat=ends_combat,
        peaceful=peaceful,
    )


def bribe_requirements_met(
    party: list[PartyMemberState],
    *,
    foe_count: int,
    gold_per_foe: int,
    weapons_per_foe: int,
) -> bool:
    if foe_count <= 0:
        return True
    total_gold = sum(member.gold for member in party if member.current_life > 0)
    total_weapons = count_party_weapons(party)
    if weapons_per_foe <= 0:
        return total_gold >= foe_count * gold_per_foe
    if gold_per_foe <= 0:
        return total_weapons >= foe_count * weapons_per_foe

    max_weapon_slots = total_weapons // weapons_per_foe
    remaining_foes = foe_count - max_weapon_slots
    if remaining_foes <= 0:
        return True
    return total_gold >= remaining_foes * gold_per_foe


def pay_bribe_cost(
    party: list[PartyMemberState],
    *,
    foe_count: int,
    gold_per_foe: int,
    weapons_per_foe: int,
) -> tuple[int, int, list[str]]:
    log: list[str] = []
    if foe_count <= 0:
        return 0, 0, log

    foes_remaining = foe_count
    weapons_paid = 0
    gold_paid = 0

    if weapons_per_foe > 0:
        while foes_remaining > 0:
            slots = collect_party_weapons(party)
            if len(slots) < weapons_per_foe:
                break
            for _ in range(weapons_per_foe):
                slots = collect_party_weapons(party)
                if not slots:
                    break
                member, index = slots[0]
                removed = member.inventory.pop(index)
                weapons_paid += 1
                log.append(f"{member.name} surrenders {removed}.")
            foes_remaining -= 1

    if foes_remaining > 0 and gold_per_foe > 0:
        gold_needed = foes_remaining * gold_per_foe
        remaining = gold_needed
        for member in sorted(party, key=lambda item: item.marching_order):
            if remaining <= 0:
                break
            if member.current_life <= 0:
                continue
            take = min(member.gold, remaining)
            if take <= 0:
                continue
            member.gold -= take
            gold_paid += take
            remaining -= take
        if remaining > 0:
            return gold_paid, weapons_paid, log

    return gold_paid, weapons_paid, log


def flee_if_outnumbered(enemies: list[EnemyState], party: list[PartyMemberState]) -> bool:
    living = sum(1 for member in party if member.current_life > 0)
    return len(enemies) < living
