from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ..rules.repository import RulesRepository
from ..schemas import PartyMemberState
from .class_abilities import lockpick_door_bonus, member_has_lockpicks
from .class_combat import armor_defense_bonus, defense_modifier, save_modifier
from .inventory import encumbrance_penalty
from .dice import roll_2d6, roll_d6, roll_exploding_for_level, roll_formula

EnvironmentKind = Literal["dungeon", "caverns", "fungal_grottoes"]

ENVIRONMENT_MAGIC_TABLES: dict[str, str] = {
    "dungeon": "dungeon_magic_treasure_table",
    "caverns": "caverns_special_item_table",
    "fungal_grottoes": "fungal_grottoes_rare_item_table",
}


def environment_trap_table(environment: EnvironmentKind) -> str:
    if environment == "caverns":
        return "caverns_trap_table"
    if environment == "fungal_grottoes":
        return "fungal_grottoes_trap_table"
    return "trap_table"


def environment_special_events_table(environment: EnvironmentKind) -> str:
    if environment == "caverns":
        return "caverns_special_events_table"
    if environment == "fungal_grottoes":
        return "fungal_grottoes_special_events_table"
    return "dungeon_special_events_table"


def environment_label(environment: EnvironmentKind) -> str:
    if environment == "caverns":
        return "caverns"
    if environment == "fungal_grottoes":
        return "fungal grottoes"
    return "dungeon"


@dataclass
class DoorOutcome:
    door_type: str
    door_level: int | None
    summary: str
    roll: int | None = None
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
    complication_effect: str | None = None


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
    enemy_tags: list[str]
    roll: int


@dataclass
class SubtableOutcome:
    key: str
    result: str
    enemy_category: str | None = None
    items: list[str] | None = None
    reroll_as: str | None = None


@dataclass
class WanderingOutcome:
    enemy_category: str
    result: str
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
        for table_name in ("trap_table", "caverns_trap_table", "fungal_grottoes_trap_table"):
            for row in self.tables.get(table_name, []):
                if row.get("trap_key") == trap_key:
                    return row
        return None

    def roll_door(self, hcl: int) -> DoorOutcome:
        roll = roll_2d6()
        row = self.lookup("door_table", roll)
        if row is None:
            return DoorOutcome("unlocked", None, "Unlocked door.", roll=roll, requires_open=False)
        door_type = row["door_type"]
        level = resolve_level_formula(row["level"], hcl) if row.get("level") else None
        summary = format_summary(row, level=level, hcl=hcl)
        return DoorOutcome(
            door_type=door_type,
            door_level=level,
            summary=summary,
            roll=roll,
            requires_open=row.get("requires_open", True),
            treasure_bonus=int(row.get("treasure_bonus", 0)),
        )

    def roll_trap(
        self,
        hcl: int,
        *,
        show_rolls: bool,
        explain_math: bool,
        environment: EnvironmentKind = "dungeon",
    ) -> TrapOutcome:
        roll = roll_d6()
        log: list[str] = []
        table_name = environment_trap_table(environment)
        if show_rolls:
            log.append(f"Trap roll ({environment_label(environment)}): d6 = {roll}.")
        if explain_math:
            log.append(f"Trap lookup uses dungeon_tables.json {table_name}.")
        row = self.lookup(table_name, roll)
        if row is None:
            row = self.lookup("trap_table", roll)
        if row is None:
            row = self.tables["trap_table"][-1]
        trap_key = row["trap_key"]
        level = resolve_level_formula(row["level"], hcl)
        flavor = row.get("flavor")
        if flavor:
            log.append(flavor)
        return TrapOutcome(trap_key, level, row["result"], log)

    def roll_treasure(self, environment: EnvironmentKind = "dungeon") -> TreasureOutcome:
        roll = roll_d6()
        log = [f"Treasure roll ({environment_label(environment)}): d6 = {roll}."]
        row = self.lookup("treasure_table", roll)
        if row is None:
            return TreasureOutcome("No treasure found.", 0, [], log)
        if roll == 6 or row.get("magic_table"):
            magic = self.roll_magic_treasure(environment=environment)
            log.extend(magic.log)
            return TreasureOutcome(magic.summary, magic.gold, magic.items, log)
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

    def roll_magic_treasure(self, environment: EnvironmentKind = "dungeon") -> TreasureOutcome:
        roll = roll_d6()
        table_name = ENVIRONMENT_MAGIC_TABLES.get(environment, "dungeon_magic_treasure_table")
        log = [f"Magic treasure roll ({environment_label(environment)}): d6 = {roll}."]
        row = self.lookup(table_name, roll)
        if row is None:
            row = self.lookup("dungeon_magic_treasure_table", roll)
        if row is None:
            return TreasureOutcome("Unknown magic treasure.", 0, ["Magic treasure"], log)
        items = list(row.get("items", []))
        summary = row["result"]
        if row.get("magic_table"):
            sub_roll = roll_d6()
            log.append(f"Sub-table roll ({row['magic_table']}): d6 = {sub_roll}.")
            sub_row = self.lookup(row["magic_table"], sub_roll)
            if sub_row:
                items = list(sub_row.get("items", []))
                summary = sub_row["result"]
        return TreasureOutcome(summary, 0, items, log)

    def roll_wandering_monsters(self, *, special_event: bool = False) -> WanderingOutcome:
        table_name = "special_event_wandering_table" if special_event else "wandering_monsters_table"
        roll = roll_d6()
        row = self.lookup(table_name, roll)
        if row is None:
            return WanderingOutcome("vermin", "Wandering Vermin attack!", roll)
        return WanderingOutcome(row["enemy_category"], row.get("result", row["enemy_category"]), roll)

    def roll_reaction(self, table_name: str, roll: int) -> dict[str, Any] | None:
        return self.lookup(table_name, roll)

    def roll_random_basic_spell(self) -> dict[str, Any] | None:
        roll = roll_d6()
        return self.lookup("basic_spells_table", roll)

    def roll_special_event(
        self,
        *,
        healer_met: bool = False,
        alchemist_met: bool = False,
        lady_in_white_refused: bool = False,
        environment: EnvironmentKind = "dungeon",
    ) -> SubtableOutcome:
        roll = roll_d6()
        table_name = environment_special_events_table(environment)
        row = self.lookup(table_name, roll)
        if row is None:
            row = self.lookup("dungeon_special_events_table", roll)
        if row is None:
            return SubtableOutcome("nothing", "Nothing happens.")
        key = row["key"]
        if key == "alchemist" and alchemist_met:
            return SubtableOutcome("trap", "The alchemist has already passed; a trap triggers instead.", reroll_as="trap")
        if key == "healer" and healer_met:
            return SubtableOutcome(
                "wandering_monsters",
                "The healer has already passed; Wandering Monsters attack!",
                reroll_as="wandering_monsters",
            )
        if key == "lady_in_white" and lady_in_white_refused:
            return SubtableOutcome("trap", "The Lady in White will not return; a trap triggers instead.", reroll_as="trap")
        return SubtableOutcome(key, row["result"], reroll_as=row.get("reroll_as"))

    def roll_quest(self) -> dict[str, Any] | None:
        roll = roll_d6()
        return self.lookup("quest_table", roll)

    def roll_epic_reward(self) -> dict[str, Any] | None:
        roll = roll_d6()
        return self.lookup("epic_rewards_table", roll)

    def roll_special_feature(self) -> SubtableOutcome:
        roll = roll_d6()
        row = self.lookup("dungeon_special_features_table", roll)
        if row is None:
            return SubtableOutcome("nothing", "The feature is unremarkable.")
        return SubtableOutcome(row["key"], row["result"])

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
        return TreasureOutcome(
            f"Hidden treasure worth {gold}gp.",
            gold,
            items,
            log,
            complication_effect=complication_row.get("effect") if complication_row else None,
        )

    def lookup_search(self, roll: int) -> SearchOutcome:
        if roll <= 1:
            return SearchOutcome("wandering_monsters", "Wandering Monsters attack!")
        row = self.lookup("search_table", roll)
        if row is None:
            return SearchOutcome("nothing", "Nothing")
        if row.get("corridor_only"):
            return SearchOutcome("nothing", "Nothing")
        return SearchOutcome(row["effect"], row["result"])

    def lookup_room_content(self, roll: int, tile_type: str) -> RoomContentOutcome | None:
        for row in self.tables.get("room_content_table", []):
            low, high = parse_roll_range(row["roll"])
            if not (low <= roll <= high):
                continue
            payload = row.get("any") or row.get(tile_type)
            if payload is None:
                continue
            return RoomContentOutcome(
                key=payload["key"],
                description=payload["description"],
                objects=list(payload.get("objects", [])),
                enemy_category=payload.get("enemy_category"),
                enemy_tags=list(payload.get("enemy_tags", [])),
                roll=roll,
            )
        return None

    def apply_hidden_complication(
        self,
        effect: str,
        *,
        hcl: int,
        party: list[PartyMemberState],
        marching_order: list[str],
        show_rolls: bool,
        explain_math: bool,
    ) -> list[str]:
        if effect == "save_trap":
            row = next(
                (item for item in self.tables.get("hidden_treasure_table", []) if item.get("effect") == "save_trap"),
                None,
            )
            level = resolve_level_formula(row["level"], hcl) if row else hcl + 1
            rogue = next((member for member in party if member.class_id.lower() == "rogue" and member.current_life > 0), None)
            if rogue:
                return self._rogue_disarm_attempt(rogue, level, show_rolls=show_rolls)
            target = self._pick_random_member(party)
            if target is None:
                return ["There is no one left to trigger the trap."]
            return _save_trap_hit(
                target,
                level,
                "hidden treasure trap",
                damage=1,
                show_rolls=show_rolls,
                explain_math=explain_math,
                double_on_natural_1=True,
            )
        if effect == "ghost":
            cleric = next((member for member in party if member.class_id.lower() == "cleric" and member.current_life > 0), None)
            level = hcl
            if cleric:
                total, rolls = roll_exploding_for_level(cleric.level)
                modifier = cleric.level
                log: list[str] = []
                if show_rolls:
                    log.append(f"Ghost ban attempt: {cleric.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}.")
                if rolls[0] != 1 and total + modifier >= level:
                    log.append("The cleric banishes the ghost.")
                    return log
            log = ["No cleric banishes the ghost."]
            for member in party:
                if member.current_life > 0:
                    member.current_life = max(0, member.current_life - 1)
                    log.append(f"{member.name} loses 1 Life to the ghost.")
            return log
        return []

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
        boulder_origin: Literal["front", "back"] = "front",
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

        if target == "marching_order_until_fail":
            for member in self._living_in_marching_order(living, marching_order):
                hit_log = self._apply_trap_hit(
                    member,
                    trap_level,
                    label,
                    row=row,
                    save_type=save_type,
                    damage=damage,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    trap_key=trap_key,
                )
                log.extend(hit_log)
                if any(" takes " in entry or " falls." in entry for entry in hit_log):
                    break
            return log
        if target == "1d3_marching_order":
            count = (roll_d6() + 1) // 2
            ordered = self._living_in_marching_order(living, marching_order)
            if boulder_origin == "back":
                ordered = list(reversed(ordered))
            picks = ordered[:count]
            log.append(f"Rolling Boulder comes from the {boulder_origin}; {count} PC(s) in marching order must Save.")
            for member in picks:
                log.extend(
                    self._apply_trap_hit(
                        member,
                        trap_level,
                        label,
                        row=row,
                        save_type=save_type,
                        damage=damage,
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                        trap_key=trap_key,
                    )
                )
            return log
        if target == "random_then_all" and save_type == "trap_poison":
            trigger = self._pick_random_member(living)
            if trigger is None:
                return ["There is no one left to trigger the trap."]
            failed, trigger_log = self._trap_save_check(
                trigger,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
            )
            log.extend(trigger_log)
            if not failed:
                return log
            log.append(f"{trigger.name} releases the sleep spores.")
            asleep: list[PartyMemberState] = []
            for member in living:
                if self._fungal_spore_immune(member):
                    log.append(f"{member.name} is immune to the sleep spores.")
                    continue
                failed_poison, poison_log = self._trap_save_check(
                    member,
                    trap_level,
                    label,
                    poison=True,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    trap_key=trap_key,
                )
                log.extend(poison_log)
                if failed_poison:
                    self._add_status(member, "Asleep (sleep spores)")
                    asleep.append(member)
                    log.append(f"{member.name} falls asleep.")
            vulnerable = [member for member in living if not self._fungal_spore_immune(member)]
            if vulnerable and len(asleep) == len(vulnerable):
                for member in asleep:
                    member.current_life = 0
                log.append("All vulnerable PCs fall asleep; the party is slain by the sleep-spore trap.")
            return log
        if save_type == "trap_poison" and trap_key == "spore_cloud":
            member = self._pick_random_member(living)
            if member is None:
                return ["There is no one left to trigger the trap."]
            failed, trap_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
            )
            log.extend(trap_log)
            if failed:
                poison_level = trap_level + 2
                failed_poison, poison_log = self._trap_save_check(
                    member,
                    poison_level,
                    label,
                    poison=True,
                    show_rolls=show_rolls,
                    explain_math=explain_math,
                    trap_key=trap_key,
                )
                log.extend(poison_log)
                if failed_poison:
                    member.current_life = max(0, member.current_life - damage)
                    log.append(f"{member.name} loses {damage} Life to the spore cloud.")
                    if member.current_life == 0:
                        log.append(f"{member.name} falls.")
                log.append("Spore Cloud triggers a 1-in-6 Wandering Monsters check.")
            return log
        if trap_key == "toxic_mushrooms":
            lead = pick_member(0)
            if lead.class_id.lower() == "mushroom_monk":
                log.append("A mushroom monk leads the party; the toxic mushrooms are ignored.")
                return log
        if target == "lead" and trap_key == "slime_patch":
            member = pick_member(0)
            failed, hit_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
            )
            log.extend(hit_log)
            if failed:
                self._add_status(member, "Fallen prone (slime patch)")
                log.append(f"{member.name} falls down; if Wandering Monsters arrive, this PC skips 1 turn.")
                log.append("Slime Patch triggers a 1-in-6 Wandering Monsters check.")
            return log
        if target == "random" and trap_key == "mycelium_snare":
            member = self._pick_random_member(living)
            if member is None:
                return ["There is no one left to trigger the trap."]
            failed, hit_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
            )
            log.extend(hit_log)
            if failed:
                lost = self._lose_held_object(member)
                log.append(f"{member.name}'s {lost} is snatched away forever by the mycelium.")
            return log
        if target == "lead" and save_type == "chance" and trap_key == "shrieking_mushroom":
            member = pick_member(0)
            chance = 4
            class_id = member.class_id.lower()
            if class_id in {"halfling", "ranger"}:
                chance = max(0, chance - 2)
            if class_id in {"rogue", "assassin"}:
                chance = max(0, chance - 1)
            roll = roll_d6()
            log.append(f"Shrieking Mushroom chance: d6 = {roll}; Wandering Monsters on {chance}-in-6.")
            if roll <= chance:
                log.append("The shrieking mushroom calls Wandering Monsters.")
            else:
                log.append(f"{member.name} avoids disturbing the shrieking mushroom.")
            return log
        if target == "random" and trap_key == "cordyceps_trap":
            member = self._pick_random_member(living)
            if member is None:
                return ["There is no one left to trigger the trap."]
            failed, hit_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=True,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
            )
            log.extend(hit_log)
            if failed:
                self._add_status(member, "Cordyceps infected (6 turns)")
                target_ally = min(
                    (ally for ally in living if ally.character_id != member.character_id),
                    key=lambda ally: ally.current_life,
                    default=None,
                )
                if target_ally:
                    log.append(f"{member.name} is infected and must attack {target_ally.name}, the ally with the fewest Life.")
                else:
                    log.append(f"{member.name} is infected by cordyceps, but has no ally to attack.")
            return log
        if target == "all":
            for member in living:
                log.extend(
                    self._apply_trap_hit(
                        member,
                        trap_level,
                        label,
                        row=row,
                        save_type=save_type,
                        damage=damage,
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                        trap_key=trap_key,
                    )
                )
            return log
        if target in {"first_two", "two_random"}:
            picks = self._pick_random_members(living, 2)
            for member in picks:
                log.extend(
                    self._apply_trap_hit(
                        member,
                        trap_level,
                        label,
                        row=row,
                        save_type=save_type,
                        damage=damage,
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                        trap_key=trap_key,
                    )
                )
            return log
        if target == "random":
            member = self._pick_random_member(living)
            if member is None:
                return ["There is no one left to trigger the trap."]
        elif target == "rear":
            member = pick_member(3 if len(marching_order) > 3 else len(living) - 1)
        else:
            member = pick_member(0)
        log.extend(
            self._apply_trap_hit(
                member,
                trap_level,
                label,
                row=row,
                save_type=save_type,
                damage=damage,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
            )
        )
        return log

    def _pick_random_member(self, party: list[PartyMemberState]) -> PartyMemberState | None:
        living = [member for member in party if member.current_life > 0]
        if not living:
            return None
        return random.choice(living)

    def _pick_random_members(self, party: list[PartyMemberState], count: int) -> list[PartyMemberState]:
        living = [member for member in party if member.current_life > 0]
        if not living:
            return []
        if len(living) <= count:
            return living
        return random.sample(living, count)

    def _rogue_disarm_attempt(self, rogue: PartyMemberState, trap_level: int, *, show_rolls: bool) -> list[str]:
        total, rolls = roll_exploding_for_level(rogue.level)
        modifier = rogue.level
        log: list[str] = []
        if show_rolls:
            log.append(f"Disarm attempt: {rogue.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}.")
        if rolls[0] != 1 and total + modifier >= trap_level:
            log.append("The rogue disarms the trap.")
            return log
        log.append("The rogue fails to disarm the trap.")
        return log

    def _apply_trap_hit(
        self,
        member: PartyMemberState,
        trap_level: int,
        label: str,
        *,
        row: dict[str, Any],
        save_type: str,
        damage: int,
        show_rolls: bool,
        explain_math: bool,
        trap_key: str = "",
    ) -> list[str]:
        shield_applies = row.get("shield_applies", True)
        if save_type == "poison":
            return _save_trap_hit(
                member,
                trap_level,
                label,
                damage=damage,
                show_rolls=show_rolls,
                explain_math=explain_math,
                poison=True,
                trap_key=trap_key,
            )
        if save_type in {"trapdoor", "bear_trap"}:
            return _save_trap_hit(
                member,
                trap_level,
                label,
                damage=damage,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trapdoor=(save_type == "trapdoor"),
                bear_trap=(save_type == "bear_trap"),
                trap_key=trap_key,
            )
        if save_type in {"save", "trap"}:
            return _save_trap_hit(
                member,
                trap_level,
                label,
                damage=damage,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
            )
        return _defense_trap_hit(
            member,
            trap_level,
            label,
            damage=damage,
            show_rolls=show_rolls,
            explain_math=explain_math,
            include_shield=shield_applies,
            trap_key=trap_key,
        )

    def _living_in_marching_order(
        self,
        living: list[PartyMemberState],
        marching_order: list[str],
    ) -> list[PartyMemberState]:
        ordered: list[PartyMemberState] = []
        for character_id in marching_order:
            member = next((item for item in living if item.character_id == character_id), None)
            if member and member not in ordered:
                ordered.append(member)
        ordered.extend(member for member in living if member not in ordered)
        return ordered

    def _trap_save_check(
        self,
        member: PartyMemberState,
        trap_level: int,
        label: str,
        *,
        poison: bool,
        show_rolls: bool,
        explain_math: bool,
        trap_key: str,
    ) -> tuple[bool, list[str]]:
        from .heroic_skill_effects import trap_save_bonus

        total, rolls = roll_exploding_for_level(member.level)
        modifier = save_modifier(member, trap=True, poison=poison) + encumbrance_penalty(member)
        modifier += trap_save_bonus(member, trap_key, label)
        log: list[str] = []
        save_label = "poison save" if poison else "trap save"
        if show_rolls:
            log.append(f"Trap {save_label}: {member.name} vs {label}: {' + '.join(str(value) for value in rolls)} + {modifier}.")
        if explain_math:
            log.append(f"Trap {save_label} math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need >= {trap_level}.")
        failed = rolls[0] == 1 or total + modifier < trap_level
        log.append(f"{member.name} {'fails' if failed else 'passes'} the {save_label} vs {label}.")
        return failed, log

    def _add_status(self, member: PartyMemberState, status: str) -> None:
        if status not in member.statuses:
            member.statuses.append(status)

    def _fungal_spore_immune(self, member: PartyMemberState) -> bool:
        class_id = member.class_id.lower()
        return class_id == "mushroom_monk" or any(
            tag in class_id for tag in ("undead", "elemental", "construct", "artificial")
        )

    def _lose_held_object(self, member: PartyMemberState) -> str:
        for attr in ("default_melee_weapon", "default_missile_weapon", "default_melee_weapon_secondary"):
            item = getattr(member, attr, None)
            if item:
                setattr(member, attr, None)
                try:
                    member.inventory.remove(item)
                except ValueError:
                    pass
                return item
        if member.inventory:
            return member.inventory.pop(0)
        return "held object"


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
    if normalized.startswith("(HCL+D6)*(HCL+D6)"):
        left = hcl + roll_d6()
        right = hcl + roll_d6()
        return left * right
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


def door_opening_hint(door_type: str, *, door_level: int | None = None, hcl: int | None = None) -> str:
    level_text = f"L{door_level}" if door_level is not None else "door level"
    hcl_text = f"HCL {hcl}" if hcl is not None else "HCL"
    hints = {
        "locked": (
            f"Locked door ({level_text}). Rogue lock-picks (+Level) or Warrior/Barbarian bashes (+Level). "
            "Exploding d6 + modifier vs door level; natural 1 fails noisily."
        ),
        "iron": (
            f"Iron door ({level_text}). Rogue lock-picks, or destroy with Fireball/Lightning. Cannot be bashed."
        ),
        "sealed": (
            f"Magically sealed ({level_text}). Any caster: spellcasting roll vs door level. "
            "One attempt per door; natural 1 on the roll causes 2 damage to the caster."
        ),
        "illusion": (
            f"Illusionary door ({hcl_text}). Spend 3 Clues, or an Illusionist spellcasting roll vs {hcl_text}."
        ),
        "lever": "Lever door. Spend 1 character-held Clue, or 1 gnome Gadget point.",
        "trap_door": (
            f"Trap door ({level_text}). Opens easily but triggers a trap unless a Rogue disarms it first (vs trap level)."
        ),
        "unlocked": "Unlocked door. Opens easily.",
    }
    return hints.get(door_type, "Work the door during exploration.")


def door_discovery_log(outcome: DoorOutcome, *, hcl: int, show_rolls: bool) -> list[str]:
    log: list[str] = []
    if show_rolls and outcome.roll is not None:
        log.append(f"Door roll: 2d6 = {outcome.roll}.")
    log.append(f"Door: {outcome.summary}")
    hint = door_opening_hint(outcome.door_type, door_level=outcome.door_level, hcl=hcl)
    if show_rolls and hint.rstrip(".") != outcome.summary.rstrip("."):
        log.append(hint)
    return log


def door_attempt_label(member: PartyMemberState, door_type: str) -> str:
    class_id = member.class_id.lower()
    if door_type == "iron" and class_id in {"rogue", "kukla", "assassin"}:
        if class_id == "kukla":
            return f"{member.name} lock-picks with prehensile hair (+½L)"
        if class_id == "assassin":
            return f"{member.name} lock-picks"
        return f"{member.name} lock-picks (Rogue +L{member.level})"
    if door_type == "locked" and class_id in {"warrior", "barbarian"}:
        return f"{member.name} bashes (Warrior +L{member.level})"
    if class_id == "rogue":
        return f"{member.name} lock-picks (Rogue +L{member.level})"
    if class_id == "kukla":
        return f"{member.name} lock-picks with prehensile hair (+½L)"
    if class_id == "assassin":
        return f"{member.name} lock-picks"
    if class_id in {"warrior", "barbarian"} and door_type == "locked":
        return f"{member.name} bashes (Warrior +L{member.level})"
    return f"{member.name} forces the door"


def _can_lockpick_door(member: PartyMemberState) -> bool:
    class_id = member.class_id.lower()
    if class_id == "rogue":
        return True
    if class_id in {"kukla", "assassin"}:
        return member_has_lockpicks(member)
    return False


def attempt_open_door(
    exit_state,
    member: PartyMemberState,
    *,
    hcl: int,
    show_rolls: bool,
    explain_math: bool,
    roller: DungeonTableRoller,
    party: list[PartyMemberState] | None = None,
    marching_order: list[str] | None = None,
    servant_active: bool = False,
) -> tuple[bool, list[str]]:
    log: list[str] = []
    if exit_state.door_type is None:
        outcome = roller.roll_door(hcl)
        exit_state.door_type = outcome.door_type
        exit_state.door_level = outcome.door_level
        exit_state.door_result = outcome.summary
        exit_state.door_treasure_bonus = outcome.treasure_bonus
        log.extend(door_discovery_log(outcome, hcl=hcl, show_rolls=show_rolls))

    if exit_state.door_open:
        if not log:
            log.append("The door is already open.")
        return True, log

    door_type = exit_state.door_type or "unlocked"
    level = exit_state.door_level or hcl
    if door_type == "unlocked":
        exit_state.door_open = True
        log.append("The door opens easily.")
        return True, log
    if door_type == "trap_door":
        level = exit_state.door_level or hcl
        if member.class_id.lower() == "rogue":
            log.extend(roller._rogue_disarm_attempt(member, level, show_rolls=show_rolls))
            if log[-1].startswith("The rogue disarms"):
                exit_state.door_open = True
                log.append("The door opens.")
                return True, log
            log.extend(_save_trap_hit(member, level, "trap door", damage=1, show_rolls=show_rolls, explain_math=explain_math))
        else:
            trap = roller.roll_trap(hcl, show_rolls=show_rolls, explain_math=explain_math)
            log.extend(trap.log)
            if party:
                log.extend(
                    roller.resolve_trap(
                        trap.trap_key,
                        trap.trap_level,
                        party,
                        marching_order or [],
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                    )
                )
        exit_state.door_open = True
        log.append("The door opens.")
        return True, log
    if door_type == "sealed":
        log.append(
            "Use Spellcast on this door (not a physical Open Door attempt)."
            if show_rolls
            else "The sealed door resists physical opening."
        )
        return False, log
    if door_type == "illusion":
        log.append(
            "The illusion blocks the way until the party spends 3 Clues or an Illusionist dispels it."
            if show_rolls
            else "The illusion blocks the way."
        )
        return False, log
    if door_type == "lever":
        log.append(
            "The lever mechanism waits for 1 Clue or a gnome Gadget point."
            if show_rolls
            else "The lever door remains closed."
        )
        return False, log
    if door_type == "iron":
        if not _can_lockpick_door(member):
            log.append(
                "This iron door needs a Rogue lock-pick attempt or Fireball/Lightning."
                if show_rolls
                else "The iron door resists this hero."
            )
            return False, log

    if door_type == "locked" and member.class_id.lower() not in {
        "rogue",
        "warrior",
        "barbarian",
        "kukla",
        "assassin",
    }:
        log.append("Only a Rogue can lock-pick or a Warrior/Barbarian can bash a locked door.")
        return False, log
    if door_type == "locked" and member.class_id.lower() in {"kukla", "assassin"} and not member_has_lockpicks(member):
        log.append(f"{member.name} needs lock-picks to work this door.")
        return False, log

    log.append(door_attempt_label(member, door_type))
    total, rolls = roll_exploding_for_level(member.level)
    modifier = save_modifier(member) + encumbrance_penalty(member, servant_active=servant_active)
    if member.class_id.lower() in {"warrior", "barbarian"} and door_type == "locked":
        modifier += member.level
    elif member.class_id.lower() in {"rogue", "kukla", "assassin"}:
        modifier += lockpick_door_bonus(member)
    if show_rolls:
        log.append(f"Door attempt: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}.")
    if explain_math:
        log.append(f"Door math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier} vs L{level}.")
    if rolls[0] == 1:
        log.append("The attempt fails noisily.")
        return False, log
    if total + modifier >= level:
        exit_state.door_open = True
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
    include_shield: bool = True,
    trap_key: str = "",
) -> list[str]:
    from .heroic_skill_effects import trap_damage_after_reduction, trap_save_bonus

    log: list[str] = []
    total, rolls = roll_exploding_for_level(member.level)
    modifier = (
        defense_modifier(member)
        + armor_defense_bonus(member, include_shield=include_shield)
        + encumbrance_penalty(member)
        + trap_save_bonus(member, trap_key, label)
    )
    if show_rolls:
        log.append(f"Trap defense: {member.name} vs {label}: {' + '.join(str(value) for value in rolls)} + {modifier}.")
    if explain_math:
        log.append(f"Trap defense math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need > {trap_level}.")
    if rolls[0] == 1 or total + modifier <= trap_level:
        applied, reduction_log = trap_damage_after_reduction(member, trap_key, label, damage)
        log.extend(reduction_log)
        member.current_life = max(0, member.current_life - applied)
        log.append(f"{member.name} takes {applied} damage from the {label}.")
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
    poison: bool = False,
    trapdoor: bool = False,
    bear_trap: bool = False,
    double_on_natural_1: bool = False,
    trap_key: str = "",
) -> list[str]:
    from .heroic_skill_effects import trap_damage_after_reduction, trap_save_bonus

    log: list[str] = []
    total, rolls = roll_exploding_for_level(member.level)
    modifier = save_modifier(member, trap=True, poison=poison) + encumbrance_penalty(member)
    modifier += trap_save_bonus(member, trap_key, label)
    if trapdoor:
        modifier += _trapdoor_modifier(member)
    if bear_trap:
        modifier += _bear_trap_modifier(member)
    if show_rolls:
        log.append(f"Trap save: {member.name} vs {label}: {' + '.join(str(value) for value in rolls)} + {modifier}.")
    if explain_math:
        log.append(f"Trap save math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need >= {trap_level}.")
    failed = rolls[0] == 1 or total + modifier < trap_level
    if failed:
        applied = damage * 2 if double_on_natural_1 and rolls[0] == 1 else damage
        applied, reduction_log = trap_damage_after_reduction(member, trap_key, label, applied)
        log.extend(reduction_log)
        member.current_life = max(0, member.current_life - applied)
        log.append(f"{member.name} takes {applied} damage from the {label}.")
        if member.current_life == 0:
            log.append(f"{member.name} falls.")
    else:
        log.append(f"{member.name} resists the {label}.")
    return log


def _trapdoor_modifier(member: PartyMemberState) -> int:
    inventory = " ".join(item.lower() for item in member.inventory)
    modifier = 0
    if "heavy armor" in inventory:
        modifier -= 2
    elif "light armor" in inventory:
        modifier -= 1
    if member.class_id.lower() in {"halfling", "elf"}:
        modifier += 1
    if member.class_id.lower() == "rogue":
        modifier += member.level
    return modifier


def _bear_trap_modifier(member: PartyMemberState) -> int:
    modifier = 0
    if member.class_id.lower() in {"halfling", "elf"}:
        modifier += 1
    if member.class_id.lower() == "rogue":
        modifier += member.level
    return modifier
