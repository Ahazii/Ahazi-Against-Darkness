from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..rules.repository import RulesRepository
from ..schemas import PartyMemberState
from .class_combat import armor_defense_bonus, defense_modifier, save_modifier
from .dice import roll_2d6, roll_d6, roll_exploding_d6, roll_formula


@dataclass
class DoorOutcome:
    door_type: str
    door_level: int | None
    summary: str
    requires_open: bool = True
    treasure_bonus: int = 0


@dataclass
class TrapOutcome:
    trap_key: str
    trap_level: int
    summary: str
    log: list[str]


@dataclass
class TreasureOutcome:
    summary: str
    gold: int
    items: list[str]
    log: list[str]


@dataclass
class SearchOutcome:
    effect: str
    result: str


@dataclass
class RoomContentOutcome:
    key: str
    description: str
    objects: list[str]
    enemy_category: str | None
    roll: int


class DungeonTableRoller:
    def __init__(self, tables: dict[str, Any]) -> None:
        self.tables = tables

    @classmethod
    def from_rules(cls, rules: RulesRepository | None) -> DungeonTableRoller:
        if rules is None:
            path = Path(__file__).resolve().parents[3] / "data" / "rules" / "dungeon_tables.json"
            return cls(json.loads(path.read_text(encoding="utf-8")))
        return cls(rules.dungeon_tables())

    def lookup(self, table_name: str, roll: int) -> dict[str, Any] | None:
        table = self.tables.get(table_name, [])
        if not isinstance(table, list):
            return None
        for row in table:
            roll_value = row.get("roll")
            if roll_value is None or not isinstance(roll_value, str):
                continue
            if " " in roll_value:
                continue
            low, high = parse_roll_range(roll_value)
            if low <= roll <= high:
                return row
        return None

    def lookup_trap(self, trap_key: str) -> dict[str, Any] | None:
        for row in self.tables.get("trap_table", []):
            if row.get("trap_key") == trap_key:
                return row
        return None

    def roll_door(self, hcl: int) -> DoorOutcome:
        roll = roll_2d6()
        row = self.lookup("door_table", roll)
        if row is None:
            return DoorOutcome("unlocked", None, "Unlocked door.", requires_open=False)
        door_type = row["door_type"]
        level = resolve_level_formula(row["level"], hcl) if row.get("level") else None
        summary = format_summary(row, level=level, hcl=hcl)
        return DoorOutcome(
            door_type=door_type,
            door_level=level,
            summary=summary,
            requires_open=row.get("requires_open", True),
            treasure_bonus=int(row.get("treasure_bonus", 0)),
        )

    def roll_trap(self, hcl: int, *, show_rolls: bool, explain_math: bool) -> TrapOutcome:
        roll = roll_d6()
        log: list[str] = []
        if show_rolls:
            log.append(f"Trap roll: d6 = {roll}.")
        if explain_math:
            log.append("Trap lookup uses dungeon_tables.json trap_table.")
        row = self.lookup("trap_table", roll)
        if row is None:
            row = self.tables["trap_table"][-1]
        trap_key = row["trap_key"]
        level = resolve_level_formula(row["level"], hcl)
        flavor = row.get("flavor")
        if flavor:
            log.append(flavor)
        return TrapOutcome(trap_key, level, row["result"], log)

    def roll_treasure(self) -> TreasureOutcome:
        roll = roll_d6()
        log = [f"Treasure roll: d6 = {roll}."]
        row = self.lookup("treasure_table", roll)
        if row is None:
            return TreasureOutcome("No treasure found.", 0, [], log)
        gold = resolve_gold_formula(row["gold"], hcl=0) if row.get("gold") else 0
        items = list(row.get("items", []))
        if gold and roll in (2, 3):
            summary = f"Found {gold}gp."
        elif gold and roll == 4:
            summary = f"Found a gem worth {gold}gp."
        elif gold and roll == 5:
            summary = f"Found a chest with {gold}gp."
        else:
            summary = row["result"]
        return TreasureOutcome(summary, gold, items, log)

    def roll_hidden_treasure(self, hcl: int) -> TreasureOutcome:
        value_row = next(
            (row for row in self.tables.get("hidden_treasure_table", []) if row.get("roll") == "value"),
            None,
        )
        gold_formula = value_row["gold"] if value_row else "2d6*2d6+HCL"
        gold = resolve_gold_formula(gold_formula, hcl=hcl)
        complication = roll_d6()
        log = [
            f"Hidden treasure: ({gold}gp before complications).",
            f"Hidden treasure complication roll: d6 = {complication}.",
        ]
        items: list[str] = []
        complication_row = None
        for row in self.tables.get("hidden_treasure_table", []):
            roll_value = row.get("roll", "")
            if not roll_value.startswith("complication "):
                continue
            range_text = roll_value.removeprefix("complication ")
            low, high = parse_roll_range(range_text)
            if low <= complication <= high:
                complication_row = row
                break
        if complication_row:
            log.append(complication_row["result"])
            items.extend(complication_row.get("items", []))
        return TreasureOutcome(f"Hidden treasure worth {gold}gp.", gold, items, log)

    def lookup_search(self, roll: int) -> SearchOutcome:
        row = self.lookup("search_table", roll)
        if row is None:
            return SearchOutcome("nothing", "Nothing")
        return SearchOutcome(row["effect"], row["result"])

    def lookup_room_content(self, roll: int, tile_type: str) -> RoomContentOutcome | None:
        for row in self.tables.get("room_content_table", []):
            low, high = parse_roll_range(row["roll"])
            if not (low <= roll <= high):
                continue
            if row.get("rooms_only") and tile_type != "room":
                continue
            return RoomContentOutcome(
                key=row["key"],
                description=row["description"],
                objects=list(row.get("objects", [])),
                enemy_category=row.get("enemy_category"),
                roll=roll,
            )
        return None

    def search_table_summary(self) -> str:
        parts: list[str] = []
        for row in self.tables.get("search_table", []):
            parts.append(f"{row['roll']} {row['result'].lower()}")
        return ", ".join(parts)

    def resolve_trap(
        self,
        trap_key: str,
        trap_level: int,
        party: list[PartyMemberState],
        marching_order: list[str],
        *,
        show_rolls: bool,
        explain_math: bool,
    ) -> list[str]:
        row = self.lookup_trap(trap_key)
        if row is None:
            return [f"Unknown trap: {trap_key}."]
        living = [member for member in party if member.current_life > 0]
        if not living:
            return ["There is no one left to trigger the trap."]

        def pick_member(index: int) -> PartyMemberState:
            if index < len(marching_order):
                chosen = next((member for member in living if member.character_id == marching_order[index]), None)
                if chosen:
                    return chosen
            return living[index % len(living)]

        log: list[str] = []
        target = row.get("target", "lead")
        save_type = row.get("save", "defense")
        damage = int(row.get("damage", 1))
        label = trap_key.replace("_", " ")

        if target == "all":
            for member in living:
                log.extend(
                    self._apply_trap_hit(member, trap_level, label, save_type=save_type, damage=damage, show_rolls=show_rolls, explain_math=explain_math)
                )
            return log
        if target == "first_two":
            for index in range(min(2, len(living))):
                member = pick_member(index)
                log.extend(
                    self._apply_trap_hit(member, trap_level, label, save_type=save_type, damage=damage, show_rolls=show_rolls, explain_math=explain_math)
                )
            return log
        if target == "rear":
            member = pick_member(3 if len(marching_order) > 3 else len(living) - 1)
        else:
            member = pick_member(0)
        log.extend(
            self._apply_trap_hit(member, trap_level, label, save_type=save_type, damage=damage, show_rolls=show_rolls, explain_math=explain_math)
        )
        return log

    def _apply_trap_hit(
        self,
        member: PartyMemberState,
        trap_level: int,
        label: str,
        *,
        save_type: str,
        damage: int,
        show_rolls: bool,
        explain_math: bool,
    ) -> list[str]:
        if save_type == "save":
            return _save_trap_hit(member, trap_level, label, damage=damage, show_rolls=show_rolls, explain_math=explain_math)
        return _defense_trap_hit(member, trap_level, label, damage=damage, show_rolls=show_rolls, explain_math=explain_math)


def parse_roll_range(value: str) -> tuple[int, int]:
    value = value.strip()
    if "-" in value:
        low, high = value.split("-", 1)
        return int(low.strip()), int(high.strip())
    number = int(value)
    return number, number


def resolve_level_formula(formula: str, hcl: int) -> int:
    normalized = formula.replace(" ", "").upper()
    if normalized == "HCL":
        return hcl
    if normalized.startswith("HCL+"):
        suffix = normalized[4:]
        if suffix == "D6":
            return hcl + roll_d6()
        return hcl + int(suffix)
    raise ValueError(f"Unsupported level formula: {formula}")


def resolve_gold_formula(formula: str, *, hcl: int) -> int:
    normalized = formula.replace(" ", "").upper()
    if "+HCL" in normalized:
        base, _ = normalized.split("+HCL", 1)
        return _eval_gold_expression(base) + hcl
    return _eval_gold_expression(normalized)


def _eval_gold_expression(expression: str) -> int:
    total = 1
    for part in expression.split("*"):
        total *= roll_formula(part.lower())
    return total


def format_summary(row: dict[str, Any], *, level: int | None, hcl: int) -> str:
    template = row.get("summary") or row["result"]
    return template.format(level=level, hcl=hcl)


def attempt_open_door(
    exit_state,
    member: PartyMemberState,
    *,
    hcl: int,
    show_rolls: bool,
    explain_math: bool,
    roller: DungeonTableRoller,
) -> tuple[bool, list[str]]:
    log: list[str] = []
    if exit_state.door_type is None:
        outcome = roller.roll_door(hcl)
        exit_state.door_type = outcome.door_type
        exit_state.door_level = outcome.door_level
        exit_state.door_result = outcome.summary
        exit_state.door_treasure_bonus = outcome.treasure_bonus
        log.append(f"Door: {outcome.summary}")

    if exit_state.door_open:
        return True, log

    door_type = exit_state.door_type or "unlocked"
    if door_type == "unlocked":
        exit_state.door_open = True
        log.append("The door opens easily.")
        return True, log
    if door_type == "sealed":
        log.append("The door is magically sealed and cannot be forced open yet.")
        return False, log
    if door_type == "illusion":
        log.append("An illusion hides this door; it cannot be opened without clues or an illusionist.")
        return False, log
    if door_type == "lever":
        log.append("A lever mechanism opens the door.")
        exit_state.door_open = True
        return True, log

    level = exit_state.door_level or hcl
    total, rolls = roll_exploding_d6()
    modifier = save_modifier(member)
    if member.class_id.lower() in {"warrior", "barbarian", "dwarf"}:
        modifier += member.level
    if show_rolls:
        log.append(f"Door attempt: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}.")
    if explain_math:
        log.append(f"Door math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier} vs L{level}.")
    if rolls[0] == 1:
        log.append("The attempt fails noisily.")
        return False, log
    if total + modifier >= level:
        exit_state.door_open = True
        if door_type == "trapped":
            trap = roller.roll_trap(hcl, show_rolls=show_rolls, explain_math=explain_math)
            log.extend(trap.log)
        log.append("The door opens.")
        return True, log
    log.append("The door holds firm.")
    return False, log


def _defense_trap_hit(
    member: PartyMemberState,
    trap_level: int,
    label: str,
    *,
    damage: int,
    show_rolls: bool,
    explain_math: bool,
) -> list[str]:
    log: list[str] = []
    total, rolls = roll_exploding_d6()
    modifier = defense_modifier(member) + armor_defense_bonus(member)
    if show_rolls:
        log.append(f"Trap defense: {member.name} vs {label}: {' + '.join(str(value) for value in rolls)} + {modifier}.")
    if explain_math:
        log.append(f"Trap defense math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need > {trap_level}.")
    if rolls[0] == 1 or total + modifier <= trap_level:
        member.current_life = max(0, member.current_life - damage)
        log.append(f"{member.name} takes {damage} damage from the {label}.")
        if member.current_life == 0:
            log.append(f"{member.name} falls.")
    else:
        log.append(f"{member.name} avoids the {label}.")
    return log


def _save_trap_hit(
    member: PartyMemberState,
    trap_level: int,
    label: str,
    *,
    damage: int,
    show_rolls: bool,
    explain_math: bool,
) -> list[str]:
    log: list[str] = []
    total, rolls = roll_exploding_d6()
    modifier = save_modifier(member, trap=True)
    if show_rolls:
        log.append(f"Trap save: {member.name} vs {label}: {' + '.join(str(value) for value in rolls)} + {modifier}.")
    if explain_math:
        log.append(f"Trap save math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need >= {trap_level}.")
    if rolls[0] == 1 or total + modifier < trap_level:
        member.current_life = max(0, member.current_life - damage)
        log.append(f"{member.name} takes {damage} damage from the {label}.")
        if member.current_life == 0:
            log.append(f"{member.name} falls.")
    else:
        log.append(f"{member.name} resists the {label}.")
    return log
