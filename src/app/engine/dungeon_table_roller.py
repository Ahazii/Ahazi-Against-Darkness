from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from ..rules.repository import RulesRepository
from ..schemas import PartyMemberState, SessionState
from .class_abilities import lockpick_door_bonus, member_has_lockpicks
from .special_items import can_bash_door, extra_door_modifier
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


def environment_special_features_table(environment: EnvironmentKind) -> str:
    if environment == "caverns":
        return "caverns_special_features_table"
    return "dungeon_special_features_table"


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
class TrapResolveResult:
    log: list[str]
    pending_mycelium_snare_character_id: str | None = None

    def __iter__(self):
        return iter(self.log)


@dataclass
class TreasureOutcome:
    summary: str
    gold: int
    items: list[str]
    log: list[str]
    complication_effect: str | None = None
    choice_key: str | None = None
    clues_granted: int = 0
    jackpot_wandering_on_claim: bool = False


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
    choices: list[str]
    subtable: str | None = None


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
        for table_name in ("trap_table", "caverns_trap_table", "fungal_grottoes_trap_table", "fd_trap_table"):
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

    def roll_fd_trap(
        self,
        hcl: int,
        *,
        show_rolls: bool,
        explain_math: bool,
        tier: int | None = None,
    ) -> TrapOutcome:
        roll = roll_d6()
        log: list[str] = []
        party_tier = tier if tier is not None else max(1, (hcl + 2) // 3)
        if show_rolls:
            log.append(f"Forsaken Depths trap roll: d6 = {roll} (FD p.58).")
        if explain_math:
            log.append("Trap lookup uses forsaken_depths_tables.json fd_trap_table.")
        row = self.lookup("fd_trap_table", roll)
        if row is None:
            row = self.tables.get("fd_trap_table", [{}])[-1]
        trap_key = row["trap_key"]
        level = hcl + party_tier + 2
        flavor = row.get("flavor") or row.get("result")
        if flavor:
            log.append(str(flavor))
        if explain_math:
            log.append(f"Trap level = HCL ({hcl}) + Tier ({party_tier}) + 2 = {level}.")
        return TrapOutcome(trap_key, level, row.get("result", flavor or trap_key), log)

    def roll_fd_treasure(
        self,
        *,
        show_rolls: bool,
        treasure_bonus: int = 0,
        silk_already_found: bool = False,
        _depth: int = 0,
        allow_jackpot: bool = True,
    ) -> TreasureOutcome:
        if _depth > 8:
            return TreasureOutcome("Treasure roll limit reached.", 0, [], [])
        raw_roll = random.randint(0, 10)
        roll = max(0, min(10, raw_roll + treasure_bonus))
        log: list[str] = []
        if show_rolls:
            bonus_text = f" + {treasure_bonus}" if treasure_bonus else ""
            log.append(f"Forsaken Depths treasure roll: d10 = {raw_roll}{bonus_text} → {roll} (FD p.62).")
        if roll == 10:
            if allow_jackpot and _depth == 0:
                if show_rolls:
                    session_log = (
                        "Jackpot! Choose: roll twice on this table OR roll four times "
                        "(4-in-6 wandering monsters while looting) (FD p.62)."
                    )
                    log.append(session_log)
                return TreasureOutcome(
                    "Jackpot: roll twice OR roll four times (4-in-6 wanderers while looting).",
                    0,
                    [],
                    log,
                    choice_key="fd_double_or_jackpot",
                )
            if show_rolls:
                log.append("Sub-roll 10 — rerolling (jackpot choice only on the initial roll, FD p.62).")
            return self.roll_fd_treasure(
                show_rolls=show_rolls,
                treasure_bonus=0,
                silk_already_found=silk_already_found,
                _depth=_depth + 1,
                allow_jackpot=False,
            )
        row = self.lookup("fd_treasure_table", roll)
        if row is None:
            return TreasureOutcome("No treasure found.", 0, [], log)
        key = row.get("key", "")
        if key == "food_and_wine":
            food = roll_formula("d6") * 10
            wine = roll_formula("d6")
            gold = wine * 10
            items = [f"{food} Food points", f"{wine} bottles of fine wine"]
            return TreasureOutcome(
                f"{food} Food points and {wine} bottles of fine wine ({gold}gp wine value).",
                gold,
                items,
                log,
            )
        if key == "common_equipment":
            return TreasureOutcome("Common equipment worth up to 50 gp.", 50, ["Common equipment (≤50gp)"], log)
        if key == "precious_silk":
            if silk_already_found:
                if show_rolls:
                    log.append("Precious silk already found this adventure — rerolling (FD p.62).")
                return self.roll_fd_treasure(
                    show_rolls=show_rolls,
                    treasure_bonus=0,
                    silk_already_found=True,
                    _depth=_depth + 1,
                )
            gold = roll_formula("d20") + 20
            return TreasureOutcome(f"Precious silk worth {gold}gp.", gold, ["Precious silk"], log)
        if key == "gold_or_masterwork":
            gold = roll_formula("10d6") + 10
            return TreasureOutcome(
                f"{gold}gp OR a Masterwork weapon (choose).",
                gold,
                ["Masterwork weapon (optional instead of gold)"],
                log,
                choice_key="fd_gold_or_masterwork",
            )
        if key == "gem":
            gold = roll_formula("5d6") * 5
            from .gem_items import format_gem_item

            return TreasureOutcome(f"Gem worth {gold}gp.", 0, [format_gem_item(gold)], log)
        if key == "jewelry":
            gold = roll_formula("5d6") * 6
            from .gem_items import format_jewelry_item

            return TreasureOutcome(f"Jewelry worth {gold}gp.", 0, [format_jewelry_item(gold)], log)
        if key == "masks_of_thar_tizan":
            count = roll_formula("d6")
            items = [f"Mask of Thar-Tizan ({idx + 1})" for idx in range(count)]
            return TreasureOutcome(f"{count} Masks of Thar-Tizan (50 gp each).", count * 50, items, log)
        if key == "silver_weapons_or_arrows":
            return TreasureOutcome(
                "Choose: 10 silvered melee weapons, 5 Legendary magic missiles, or masterwork bow + 24 silver arrows.",
                0,
                [],
                log,
                choice_key="fd_silver_weapons_or_arrows",
            )
        if key == "potions_or_scrolls":
            return TreasureOutcome(
                "Choose: 2 potions of healing OR 2 random spell scrolls.",
                0,
                ["Potion of Healing", "Potion of Healing"],
                log,
                choice_key="fd_potions_or_scrolls",
            )
        if key == "clues_or_magic":
            magic = self.roll_magic_treasure(table_name="dungeon_magic_treasure_table")
            log.extend(magic.log)
            return TreasureOutcome(
                f"Choose: secret information (2 Clues) OR {magic.summary}.",
                magic.gold,
                list(magic.items),
                log,
                choice_key="fd_clues_or_magic",
            )
        return TreasureOutcome(str(row.get("result", "Treasure")), 0, [], log)

    def roll_treasure(self, environment: EnvironmentKind = "dungeon", *, treasure_bonus: int = 0) -> TreasureOutcome:
        raw_roll = roll_d6()
        roll = raw_roll - 1 + treasure_bonus
        log = [f"Treasure roll ({environment_label(environment)}): d6 = {raw_roll} - 1 + {treasure_bonus} = {roll}."]
        row = self.lookup("treasure_table", roll)
        if row is None:
            return TreasureOutcome("No treasure found.", 0, [], log)
        if roll == 2:
            if environment == "fungal_grottoes":
                rations = roll_formula("2d6")
                log.append("Fungal treasure: choose Food rations or roll on the Rare Mushroom Table.")
                return TreasureOutcome(
                    "Choose: Food rations or Rare Mushroom.",
                    0,
                    [],
                    log,
                    choice_key="fungal_rations_or_mushroom",
                )
            gold = roll_formula("2d6")
            return TreasureOutcome(f"Found {gold}gp.", gold, [], log)
        if roll == 3:
            if environment == "fungal_grottoes":
                log.append("Fungal treasure: choose druid bark or Rare Mushroom Table.")
                return TreasureOutcome(
                    "Choose: druid bark or Rare Mushroom.",
                    0,
                    [],
                    log,
                    choice_key="fungal_bark_or_mushroom",
                )
            item, spell_log = self.roll_random_spell_loot(environment)
            log.extend(spell_log)
            return TreasureOutcome(f"Found {item}.", 0, [item], log)
        if roll == 4:
            if environment == "caverns":
                gold = roll_formula("3d6") * 5
                from .gem_items import format_gem_item

                return TreasureOutcome(
                    f"Found a gem worth {gold}gp.",
                    0,
                    [format_gem_item(gold)],
                    log,
                )
            if environment == "fungal_grottoes":
                log.append("Fungal treasure: choose gem or Rare Mushroom Table.")
                return TreasureOutcome(
                    "Choose: gem or Rare Mushroom.",
                    0,
                    [],
                    log,
                    choice_key="fungal_gem_or_mushroom_4",
                )
            gold = roll_formula("2d6") * 5
            from .gem_items import format_gem_item

            return TreasureOutcome(
                f"Found a jewel worth {gold}gp.",
                0,
                [format_gem_item(gold)],
                log,
            )
        if roll == 5:
            if environment == "caverns":
                log.append("Cavern treasure: choose gem or prism with a random illusionist spell.")
                return TreasureOutcome(
                    "Choose: gem or prism.",
                    0,
                    [],
                    log,
                    choice_key="caverns_gem_or_prism",
                )
            if environment == "fungal_grottoes":
                log.append("Fungal treasure: choose gem or Rare Mushroom Table.")
                return TreasureOutcome(
                    "Choose: gem or Rare Mushroom.",
                    0,
                    [],
                    log,
                    choice_key="fungal_gem_or_mushroom_5",
                )
            gold = roll_formula("3d6") * 10
            return TreasureOutcome(f"Found a chest with {gold}gp.", gold, [], log)
        if roll >= 6:
            if row.get("magic_table"):
                if environment == "fungal_grottoes":
                    log.append(
                        "Fungal treasure: choose Fungal Grottoes Rare Item Table or Dungeon Magic Treasure Table."
                    )
                    return TreasureOutcome(
                        "Choose: Fungal rare item or dungeon magic treasure.",
                        0,
                        [],
                        log,
                        choice_key="fungal_rare_or_dungeon_magic",
                    )
                magic = self.roll_magic_treasure(environment=environment)
                log.extend(magic.log)
                return TreasureOutcome(magic.summary, magic.gold, magic.items, log)
        gold = resolve_gold_formula(row["gold"], hcl=0) if row.get("gold") else 0
        items = list(row.get("items", []))
        if gold and roll == 2:
            summary = f"Found {gold}gp."
        else:
            summary = row["result"]
        return TreasureOutcome(summary, gold, items, log)

    def roll_fiendish_foes_treasure(self, *, treasure_bonus: int = 0) -> TreasureOutcome:
        raw_roll = roll_d6()
        roll = raw_roll - 1 + treasure_bonus
        log = [f"Fiendish Foes treasure roll: d6 = {raw_roll} - 1 + {treasure_bonus} = {roll}."]
        row = self.lookup("fiendish_foes_treasure_table", roll)
        if row is None or roll <= 0:
            return TreasureOutcome("No treasure found.", 0, [], log)
        if row.get("magic_table"):
            table_name = str(row["magic_table"])
            if not table_name.endswith("_table"):
                table_name = f"{table_name}_table"
            magic = self.roll_magic_treasure(table_name=table_name)
            log.extend(magic.log)
            return TreasureOutcome(magic.summary, magic.gold, magic.items, log)
        gold = resolve_gold_formula(row["gold"], hcl=0) if row.get("gold") else 0
        items = list(row.get("items", []))
        from .gem_items import materialize_treasure_gem_items

        items = materialize_treasure_gem_items(items, log)
        if roll == 3:
            log.append("Fiendish treasure: choose random spell loot or a non-magical weapon.")
            return TreasureOutcome(
                "Choose: scroll/bark/prism or non-magical weapon.",
                0,
                [],
                log,
                choice_key="fiendish_scroll_or_weapon",
            )
        return TreasureOutcome(row["result"], gold, items, log)

    def resolve_environment_treasure_choice(
        self,
        choice_key: str,
        pick: str,
        *,
        environment: EnvironmentKind = "dungeon",
    ) -> TreasureOutcome:
        log = [f"Treasure choice ({choice_key}): {pick}."]
        if choice_key == "fungal_rations_or_mushroom":
            if pick == "food_rations":
                rations = roll_formula("2d6")
                return TreasureOutcome(f"Found {rations} Food rations.", 0, [f"Food rations ({rations})"], log)
            mushroom = self.roll_rare_mushroom_loot(count=1)
            log.extend(mushroom.log)
            return TreasureOutcome(mushroom.summary, mushroom.gold, mushroom.items, log)
        if choice_key == "fungal_bark_or_mushroom":
            if pick == "bark":
                item, spell_log = self.roll_random_spell_loot("fungal_grottoes")
                log.extend(spell_log)
                return TreasureOutcome(f"Found {item}.", 0, [item], log)
            if pick == "rare_mushroom":
                mushroom = self.roll_rare_mushroom_loot(count=1)
                log.extend(mushroom.log)
                return TreasureOutcome(mushroom.summary, mushroom.gold, mushroom.items, log)
            return TreasureOutcome("Unknown fungal treasure choice.", 0, [], log)
        if choice_key in {"fungal_gem_or_mushroom_4", "fungal_gem_or_mushroom_5"}:
            if pick == "gem":
                multiplier = 5 if choice_key.endswith("_4") else 10
                gold = roll_formula("2d6") * multiplier
                from .gem_items import format_gem_item

                return TreasureOutcome(
                    f"Found a gem worth {gold}gp.",
                    0,
                    [format_gem_item(gold)],
                    log,
                )
            roll_count = 2 if choice_key.endswith("_4") else 3
            mushroom = self.roll_rare_mushroom_loot(count=roll_count)
            log.extend(mushroom.log)
            return TreasureOutcome(mushroom.summary, mushroom.gold, mushroom.items, log)
        if choice_key == "caverns_gem_or_prism":
            if pick == "gem":
                gold = roll_formula("3d6") * 10
                from .gem_items import format_gem_item

                return TreasureOutcome(
                    f"Found a gem worth {gold}gp.",
                    0,
                    [format_gem_item(gold)],
                    log,
                )
            item, spell_log = self.roll_random_spell_loot("caverns")
            log.extend(spell_log)
            return TreasureOutcome(f"Found {item}.", 0, [item], log)
        if choice_key == "fungal_rare_or_dungeon_magic":
            if pick == "dungeon_magic":
                magic = self.roll_magic_treasure(environment="dungeon")
            else:
                magic = self.roll_magic_treasure(environment="fungal_grottoes")
            log.extend(magic.log)
            return TreasureOutcome(magic.summary, magic.gold, magic.items, log)
        if choice_key == "fiendish_scroll_or_weapon":
            if pick == "scroll":
                item, spell_log = self.roll_random_spell_loot(environment)
                log.extend(spell_log)
                return TreasureOutcome(f"Found {item}.", 0, [item], log)
            if pick == "weapon":
                log.append("Choose a non-magical weapon; then roll 2-in-6 for silvered.")
                return TreasureOutcome(
                    "Choose a non-magical weapon.",
                    0,
                    [],
                    log,
                    choice_key="fiendish_weapon_pick",
                )
            return TreasureOutcome("Unknown fiendish treasure choice.", 0, [], log)
        if choice_key == "fiendish_weapon_pick":
            from .weapon_finishes import build_fiendish_treasure_weapon, roll_two_in_six

            silvered, silver_roll, silver_log = roll_two_in_six()
            log.extend(silver_log)
            weapon, weapon_log = build_fiendish_treasure_weapon(pick, silvered=silvered)
            log.extend(weapon_log)
            if not weapon:
                return TreasureOutcome("Unknown weapon choice.", 0, [], log)
            summary = f"Found {weapon}."
            if silvered:
                summary += " The weapon is silvered (+20gp resale, or +40gp if two-handed)."
            return TreasureOutcome(summary, 0, [weapon], log)
        if choice_key == "fungal_gem_or_leafsteel":
            if pick == "gem":
                gold = roll_formula("2d6") + 2
                from .gem_items import format_gem_item

                return TreasureOutcome(
                    f"Found a small gemstone worth {gold}gp.",
                    0,
                    [format_gem_item(gold, kind="Small gemstone")],
                    log,
                )
            from .weapon_finishes import format_leafsteel_armor

            armor = format_leafsteel_armor(3)
            log.append("Leafsteel armor: +2 Defense, light armor, decays after 3 adventures.")
            return TreasureOutcome(f"Found {armor}.", 0, [armor], log)
        if choice_key in {"fungal_adventurer_body", "caverns_adventurer_body"}:
            from .adventurer_body import resolve_adventurer_body_loot

            variant = "fungal" if choice_key == "fungal_adventurer_body" else "caverns"
            items, gold, body_log, summary = resolve_adventurer_body_loot(
                variant,
                pick,
                environment=environment,
                roll_random_spell_loot=self.roll_random_spell_loot,
            )
            log.extend(body_log)
            if not summary:
                return TreasureOutcome("Unknown Adventurer's Dead Body choice.", 0, [], log)
            return TreasureOutcome(summary, gold, items, log)
        if choice_key == "fungal_red_death":
            from .fungal_rare_items import resolve_red_death_treasure

            summary, gold, items, extra_log = resolve_red_death_treasure(pick, log)
            return TreasureOutcome(summary, gold, items, extra_log)
        if choice_key.startswith("fd_"):
            return self.resolve_fd_treasure_choice(
                choice_key,
                pick,
                staged_gold=0,
                staged_items=[],
                show_rolls=True,
            )
        return TreasureOutcome("Unknown treasure choice.", 0, [], log)

    def _merge_fd_treasure_outcomes(self, outcomes: list[TreasureOutcome]) -> TreasureOutcome:
        for outcome in outcomes:
            if outcome.choice_key:
                return outcome
        gold = sum(outcome.gold for outcome in outcomes)
        items: list[str] = []
        for outcome in outcomes:
            items.extend(outcome.items)
        summaries = [outcome.summary for outcome in outcomes if outcome.summary]
        log: list[str] = []
        for outcome in outcomes:
            log.extend(outcome.log)
        count = len(outcomes)
        default_summary = (
            "Four-roll Forsaken Depths jackpot treasure."
            if count >= 4
            else "Double-roll Forsaken Depths jackpot treasure."
        )
        summary = "; ".join(summaries) if summaries else default_summary
        merged = TreasureOutcome(summary, gold, items, log)
        merged.jackpot_wandering_on_claim = any(outcome.jackpot_wandering_on_claim for outcome in outcomes)
        return merged

    def _roll_fd_treasure_batch(
        self,
        count: int,
        *,
        show_rolls: bool,
        silk_already_found: bool,
        jackpot_wandering_on_claim: bool = False,
        treasure_bonus: int = 0,
        _depth: int = 1,
    ) -> TreasureOutcome:
        return self.roll_fd_treasure_batch_with_bonuses(
            [treasure_bonus] * count,
            show_rolls=show_rolls,
            silk_already_found=silk_already_found,
            jackpot_wandering_on_claim=jackpot_wandering_on_claim,
            _depth=_depth,
        )

    def roll_fd_treasure_batch_with_bonuses(
        self,
        bonuses: list[int],
        *,
        show_rolls: bool,
        silk_already_found: bool,
        jackpot_wandering_on_claim: bool = False,
        _depth: int = 1,
    ) -> TreasureOutcome:
        silk = silk_already_found
        outcomes: list[TreasureOutcome] = []
        for bonus in bonuses:
            outcome = self.roll_fd_treasure(
                show_rolls=show_rolls,
                treasure_bonus=bonus,
                silk_already_found=silk,
                _depth=_depth,
                allow_jackpot=False,
            )
            if "Precious silk" in outcome.summary or any("silk" in item.lower() for item in outcome.items):
                silk = True
            outcomes.append(outcome)
        if not outcomes:
            return TreasureOutcome("No treasure found.", 0, [], [])
        merged = self._merge_fd_treasure_outcomes(outcomes)
        if jackpot_wandering_on_claim:
            merged.jackpot_wandering_on_claim = True
        return merged

    def resolve_fd_treasure_choice(
        self,
        choice_key: str,
        pick: str,
        *,
        staged_gold: int = 0,
        staged_items: list[str] | None = None,
        silk_already_found: bool = False,
        show_rolls: bool = True,
    ) -> TreasureOutcome:
        log = [f"Forsaken Depths treasure choice ({choice_key}): {pick}."]
        staged_items = list(staged_items or [])
        if choice_key == "fd_double_or_jackpot":
            if pick == "double_roll":
                merged = self._roll_fd_treasure_batch(
                    2,
                    show_rolls=show_rolls,
                    silk_already_found=silk_already_found,
                )
                merged.log = log + merged.log
                return merged
            if pick == "quad_roll_wanderers":
                if show_rolls:
                    log.append(
                        "Four treasure rolls — 4-in-6 wandering monsters while looting (FD p.62)."
                    )
                merged = self._roll_fd_treasure_batch(
                    4,
                    show_rolls=show_rolls,
                    silk_already_found=silk_already_found,
                    jackpot_wandering_on_claim=True,
                )
                merged.log = log + merged.log
                return merged
        if choice_key == "fd_gold_or_masterwork":
            if pick == "gold":
                return TreasureOutcome(f"Took {staged_gold}gp.", staged_gold, [], log)
            if pick == "masterwork":
                return TreasureOutcome(
                    "Masterwork weapon of your choice.",
                    0,
                    ["Masterwork weapon"],
                    log,
                )
        if choice_key == "fd_silver_weapons_or_arrows":
            if pick == "silver_melee":
                items = [f"Silvered melee weapon ({index + 1})" for index in range(10)]
                return TreasureOutcome("10 silvered melee weapons.", 0, items, log)
            if pick == "magic_missiles":
                items = [f"Legendary magic missile ({index + 1})" for index in range(5)]
                return TreasureOutcome("5 Legendary magic missiles.", 0, items, log)
            if pick == "bow_arrows":
                items = ["Masterwork bow"] + [f"Silver-tipped arrow ({index + 1})" for index in range(24)]
                return TreasureOutcome("Masterwork bow with 24 silver-tipped arrows.", 0, items, log)
        if choice_key == "fd_potions_or_scrolls":
            if pick == "potions":
                return TreasureOutcome(
                    "2 potions of healing.",
                    0,
                    ["Potion of Healing", "Potion of Healing"],
                    log,
                )
            if pick == "scrolls":
                scroll_one, scroll_log_one = self.roll_random_spell_loot("dungeon")
                scroll_two, scroll_log_two = self.roll_random_spell_loot("dungeon")
                log.extend(scroll_log_one)
                log.extend(scroll_log_two)
                return TreasureOutcome(
                    f"2 random scrolls: {scroll_one}; {scroll_two}.",
                    0,
                    [scroll_one, scroll_two],
                    log,
                )
        if choice_key == "fd_clues_or_magic":
            if pick == "clues":
                return TreasureOutcome(
                    "Secret information worth 2 Clues (FD p.62).",
                    0,
                    [],
                    log,
                    clues_granted=2,
                )
            if pick == "magic":
                summary = staged_items[0] if len(staged_items) == 1 else "; ".join(staged_items)
                if not summary and staged_gold:
                    summary = f"Magic treasure worth {staged_gold}gp."
                return TreasureOutcome(
                    summary or "Tier-appropriate magic item.",
                    staged_gold,
                    staged_items,
                    log,
                )
        return TreasureOutcome("Unknown Forsaken Depths treasure choice.", 0, [], log)

    def roll_random_spell_loot(self, environment: EnvironmentKind = "dungeon") -> tuple[str, list[str]]:
        if environment == "caverns":
            roll = roll_formula("d12")
            row = self.lookup("illusionist_spells_table", roll)
            spell = str(row.get("spell", "Illusionary Armor")) if row else "Illusionary Armor"
            return f"Prism of {spell}", [f"Prism spell roll: d12 = {roll} -> {spell}."]
        if environment == "fungal_grottoes":
            roll = roll_formula("d12")
            row = self.lookup("druid_spells_table", roll)
            spell = str(row.get("spell", "Disperse Vermin")) if row else "Disperse Vermin"
            return f"Bark of {spell}", [f"Bark spell roll: d12 = {roll} -> {spell}."]
        roll = roll_d6()
        row = self.lookup("basic_spells_table", roll)
        spell = str(row.get("spell", "Blessing")) if row else "Blessing"
        return f"Scroll of {spell}", [f"Scroll spell roll: d6 = {roll} -> {spell}."]

    def roll_rare_mushroom_loot(self, *, count: int = 1) -> TreasureOutcome:
        count = max(1, int(count))
        log: list[str] = []
        items: list[str] = []
        table_name = "fungal_grottoes_rare_mushroom_table"
        for index in range(count):
            sub_roll = roll_d6()
            row = self.lookup(table_name, sub_roll)
            if row is None:
                row = self.lookup(table_name, 6) or {}
            item = str((row.get("items") or ["Unknown mushroom"])[0])
            items.append(item)
            log.append(f"Rare Mushroom Table roll {index + 1}/{count}: d6 = {sub_roll} -> {item}.")
        if count == 1:
            summary = f"Found {items[0]}."
        else:
            summary = f"Found {count} rare mushrooms: {', '.join(items)}."
        return TreasureOutcome(summary, 0, items, log)

    def roll_magic_treasure(
        self,
        environment: EnvironmentKind = "dungeon",
        *,
        table_name: str | None = None,
    ) -> TreasureOutcome:
        roll = roll_d6()
        table_name = table_name or ENVIRONMENT_MAGIC_TABLES.get(environment, "dungeon_magic_treasure_table")
        log = [f"Magic treasure roll ({environment_label(environment)}): d6 = {roll}."]
        row = self.lookup(table_name, roll)
        if row is None:
            row = self.lookup("dungeon_magic_treasure_table", roll)
        if row is None:
            return TreasureOutcome("Unknown magic treasure.", 0, ["Magic treasure"], log)
        if table_name == "fungal_grottoes_rare_item_table" and roll == 1:
            log.append("Fungal rare item: choose gemstone or Leafsteel armor.")
            return TreasureOutcome(
                "Choose: small gemstone or Leafsteel armor.",
                0,
                [],
                log,
                choice_key="fungal_gem_or_leafsteel",
            )
        if table_name == "fungal_grottoes_rare_item_table" and roll == 3:
            log.append("Fungal rare item: Red Death — choose damage or Level reduction when thrown.")
            return TreasureOutcome(
                "Choose Red Death effect: 1 damage or -1 Level on a living foe.",
                0,
                [],
                log,
                choice_key="fungal_red_death",
            )
        if table_name == "fungal_grottoes_rare_item_table" and roll == 5:
            from .fungal_rare_items import roll_white_angel_mushrooms

            items, extra_log = roll_white_angel_mushrooms()
            log.extend(extra_log)
            summary = f"Found Mushroom Gatherer's Basket with {len(items)} white angel mushroom(s)."
            return TreasureOutcome(summary, 0, items, log)
        if table_name == "fungal_grottoes_rare_item_table" and roll == 4:
            log.append("Fungal rare item: Adventurer's Dead Body — choose one piece of gear.")
            return TreasureOutcome(
                "Choose gear from the Adventurer's Dead Body.",
                0,
                [],
                log,
                choice_key="fungal_adventurer_body",
            )
        if table_name == "caverns_special_item_table" and roll == 1:
            gold = roll_formula("3d6") + 3
            from .gem_items import format_gem_item

            log.append(f"Caverns item: small gemstone worth {gold}gp (3d6+3).")
            return TreasureOutcome(
                f"Found a small gemstone worth {gold}gp.",
                0,
                [format_gem_item(gold, kind="Small gemstone")],
                log,
            )
        if table_name == "caverns_special_item_table" and roll == 4:
            log.append("Caverns item: Adventurer's Dead Body — choose one piece of gear.")
            return TreasureOutcome(
                "Choose gear from the Adventurer's Dead Body.",
                0,
                [],
                log,
                choice_key="caverns_adventurer_body",
            )
        if (
            table_name == "dungeon_magic_treasure_table"
            and environment == "fungal_grottoes"
            and row.get("fungal_table")
        ):
            sub_roll = roll_d6()
            fungal_table = str(row["fungal_table"])
            log.append(f"Fungal Grottoes row 6 uses {fungal_table}: d6 = {sub_roll}.")
            fungal_row = self.lookup(fungal_table, sub_roll)
            if fungal_row:
                return TreasureOutcome(
                    fungal_row["result"],
                    0,
                    list(fungal_row.get("items", [])),
                    log,
                )
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

    def roll_fd_wandering_monsters(self) -> WanderingOutcome:
        roll = roll_d6()
        row = self.lookup("fd_wandering_monsters_table", roll)
        if row is None:
            return WanderingOutcome("vermin", "Forsaken Depths wandering vermin attack!", roll)
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
        table_name = environment_special_events_table(environment)
        for _ in range(6):
            roll = roll_d6()
            row = self.lookup(table_name, roll)
            if row is None:
                row = self.lookup("dungeon_special_events_table", roll)
            if row is None:
                return SubtableOutcome("nothing", "Nothing happens.")
            key = row["key"]
            if key == "alchemist" and alchemist_met:
                return SubtableOutcome(
                    "trap",
                    "The alchemist has already passed; a trap triggers instead.",
                    reroll_as="trap",
                )
            if key == "healer" and healer_met:
                continue
            if key == "lady_in_white" and lady_in_white_refused:
                return SubtableOutcome(
                    "trap",
                    "The Lady in White will not return; a trap triggers instead.",
                    reroll_as="trap",
                )
            return SubtableOutcome(key, row["result"], reroll_as=row.get("reroll_as"))
        return SubtableOutcome(
            "trap",
            "The special event keeps repeating unavailable results; a trap triggers instead.",
            reroll_as="trap",
        )

    def roll_quest(self) -> dict[str, Any] | None:
        roll = roll_d6()
        return self.lookup("quest_table", roll)

    def roll_epic_reward(self) -> dict[str, Any] | None:
        roll = roll_d6()
        return self.lookup("epic_rewards_table", roll)

    def roll_special_feature(self, *, environment: EnvironmentKind = "dungeon") -> SubtableOutcome:
        roll = roll_d6()
        table_name = environment_special_features_table(environment)
        row = self.lookup(table_name, roll)
        if row is None:
            return SubtableOutcome("nothing", "The feature is unremarkable.")
        return SubtableOutcome(row["key"], row["result"])

    def roll_caverns_water_pool(self) -> SubtableOutcome:
        roll = roll_d6()
        row = self.lookup("caverns_water_pool_table", roll)
        if row is None:
            return SubtableOutcome("no_effect", "No effect.")
        return SubtableOutcome(row["key"], row["result"])

    def lookup_hidden_treasure_complication(self, complication: int) -> tuple[str | None, str, list[str]]:
        log: list[str] = []
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
        if complication_row is None:
            return None, "", log
        return (
            complication_row.get("effect"),
            str(complication_row.get("result", "")),
            log,
        )

    def roll_hidden_treasure(self, hcl: int) -> TreasureOutcome:
        value_row = next(
            (row for row in self.tables.get("hidden_treasure_table", []) if row.get("roll") == "value"),
            None,
        )
        complication = roll_d6()
        log = [f"Hidden treasure complication roll: d6 = {complication}."]
        effect, result_text, _ = self.lookup_hidden_treasure_complication(complication)
        if result_text:
            log.append(result_text)
        gold_formula = value_row["gold"] if value_row else "2d6*2d6+HCL"
        gold = resolve_gold_formula(gold_formula, hcl=hcl)
        log.append(f"Hidden treasure value: {gold}gp.")
        items: list[str] = []
        return TreasureOutcome(
            f"Hidden treasure worth {gold}gp.",
            gold,
            items,
            log,
            complication_effect=effect,
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
                choices=list(payload.get("choices", [])),
                subtable=payload.get("subtable"),
            )
        return None

    def lookup_fd_room_content(self, roll: int, tile_type: str) -> RoomContentOutcome | None:
        for row in self.tables.get("fd_room_content_table", []):
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
                choices=list(payload.get("choices", [])),
                subtable=payload.get("subtable"),
            )
        return None

    def lookup_fd_subtable_row(self, table_name: str, roll: int) -> dict[str, Any] | None:
        row = self.lookup(table_name, roll)
        return row if isinstance(row, dict) else None

    def lookup_fd_river_hazard(self, roll: int) -> dict[str, Any] | None:
        return self.lookup("fd_river_hazard_table", roll)

    def lookup_fd_river_type(self, roll: int) -> dict[str, Any] | None:
        return self.lookup("fd_river_type_table", roll)

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
            log: list[str] = []
            if cleric:
                total, rolls = roll_exploding_for_level(cleric)
                modifier = cleric.level
                if show_rolls:
                    log.append(f"Ghost ban attempt: {cleric.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}.")
                if rolls[0] != 1 and total + modifier >= level:
                    log.append("The cleric banishes the ghost.")
                    return log
                log.append(f"{cleric.name} fails to banish the ghost.")
            else:
                log.append("No cleric is present to banish the ghost.")
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
        snare_item_name: str | None = None,
        session: SessionState | None = None,
    ) -> TrapResolveResult:
        row = self.lookup_trap(trap_key)
        if row is None:
            return TrapResolveResult([f"Unknown trap: {trap_key}."])
        living = [member for member in party if member.current_life > 0]
        if not living:
            return TrapResolveResult(["There is no one left to trigger the trap."])

        def finish(pending_mycelium_snare_character_id: str | None = None) -> TrapResolveResult:
            return TrapResolveResult(log, pending_mycelium_snare_character_id=pending_mycelium_snare_character_id)

        def pick_member(index: int) -> PartyMemberState:
            if index < len(marching_order):
                chosen = next((member for member in living if member.character_id == marching_order[index]), None)
                if chosen:
                    return chosen
            return living[index % len(living)]

        log: list[str] = []
        result_text = str(row.get("result", "")).strip()
        if result_text and trap_key in CAVERNS_TRAP_KEYS:
            log.append(result_text)
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
                    session=session,
                )
                log.extend(hit_log)
                if any(" takes " in entry or " falls." in entry for entry in hit_log):
                    break
            return finish()
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
            return finish()
        if target == "random_then_all" and save_type == "trap_poison":
            trigger = self._pick_random_member(living)
            if trigger is None:
                return TrapResolveResult(["There is no one left to trigger the trap."])
            if self._fungal_spore_immune(trigger):
                log.append(f"{trigger.name} is immune; the sleep spores do not trigger.")
                return finish()
            failed, trigger_log = self._trap_save_check(
                trigger,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
                session=session,
            )
            log.extend(trigger_log)
            if not failed:
                return finish()
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
                    session=session,
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
            return finish()
        if save_type == "trap_poison" and trap_key == "spore_cloud":
            member = self._pick_random_member(living)
            if member is None:
                return TrapResolveResult(["There is no one left to trigger the trap."])
            if self._fungal_spore_immune(member):
                log.append(f"{member.name} is immune to the spore cloud.")
                return finish()
            failed, trap_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
                session=session,
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
                    session=session,
                )
                log.extend(poison_log)
                if failed_poison:
                    member.current_life = max(0, member.current_life - damage)
                    log.append(f"{member.name} loses {damage} Life to the spore cloud.")
                    if member.current_life == 0:
                        log.append(f"{member.name} falls.")
                log.append("Spore Cloud triggers a 1-in-6 Wandering Monsters check.")
            return finish()
        if trap_key == "toxic_mushrooms":
            from .cavern_traps import (
                caverns_toxic_mushroom_immune,
                caverns_toxic_mushroom_lead_ignores_trap,
            )

            lead = pick_member(0)
            if caverns_toxic_mushroom_lead_ignores_trap(lead):
                log.append("A mushroom-class PC leads the party; the toxic mushrooms are ignored.")
                return finish()
            member = self._pick_random_member(living)
            if member is None:
                return TrapResolveResult(["There is no one left to trigger the trap."])
            if caverns_toxic_mushroom_immune(member):
                log.append(f"{member.name} is a mushroom-class PC and is immune to the toxic mushrooms.")
                return finish()
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
                    session=session,
                )
            )
            return finish()
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
                session=session,
            )
            log.extend(hit_log)
            if failed:
                self._add_status(member, "Fallen prone (slime patch)")
                log.append(f"{member.name} falls down; if Wandering Monsters arrive, this PC skips 1 turn.")
                log.append("Slime Patch triggers a 1-in-6 Wandering Monsters check.")
            return finish()
        if target == "random" and trap_key == "mycelium_snare":
            from .fungal_traps import (
                lose_mycelium_snare_object,
                mycelium_snare_held_objects,
                resolve_mycelium_snare_item_choice,
            )

            member = self._pick_random_member(living)
            if member is None:
                return TrapResolveResult(["There is no one left to trigger the trap."])
            failed, hit_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
                session=session,
            )
            log.extend(hit_log)
            if failed:
                choices = mycelium_snare_held_objects(member)
                if not choices:
                    log.append(f"{member.name} fails the mycelium snare but has nothing in hand to snatch.")
                    return finish()
                if not snare_item_name:
                    log.append(
                        f"{member.name} fails the mycelium snare — choose which held object is snatched."
                    )
                    return finish(pending_mycelium_snare_character_id=member.character_id)
                chosen = resolve_mycelium_snare_item_choice(choices, snare_item_name)
                if chosen is None:
                    log.append(
                        f"Choose a held object for {member.name}: {', '.join(choices)}."
                    )
                    return finish(pending_mycelium_snare_character_id=member.character_id)
                lost = lose_mycelium_snare_object(member, chosen)
                log.append(f"{member.name}'s {lost} is snatched away forever by the mycelium.")
            return finish()
        if target == "lead" and save_type == "chance" and trap_key == "shrieking_mushroom":
            from .fungal_traps import shrieking_mushroom_chance_reduction

            member = pick_member(0)
            chance = max(0, 4 - shrieking_mushroom_chance_reduction(member))
            roll = roll_d6()
            log.append(f"Shrieking Mushroom chance: d6 = {roll}; Wandering Monsters on {chance}-in-6.")
            if roll <= chance:
                log.append("The shrieking mushroom calls Wandering Monsters.")
            else:
                log.append(f"{member.name} avoids disturbing the shrieking mushroom.")
            return finish()
        if target == "random" and trap_key == "cordyceps_trap":
            from .fungal_traps import resolve_cordyceps_mind_control_attack

            member = self._pick_random_member(living)
            if member is None:
                return TrapResolveResult(["There is no one left to trigger the trap."])
            failed, hit_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=True,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
                session=session,
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
                    log.append(
                        f"{member.name} is infected and must attack {target_ally.name}, "
                        f"the ally with the fewest Life."
                    )
                    attack_log, _killed = resolve_cordyceps_mind_control_attack(
                        member,
                        target_ally,
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                    )
                    log.extend(attack_log)
                else:
                    log.append(f"{member.name} is infected by cordyceps, but has no ally to attack.")
            return finish()
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
            return finish()
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
            return finish()
        if target == "random":
            member = self._pick_random_member(living)
            if member is None:
                return TrapResolveResult(["There is no one left to trigger the trap."])
        elif target == "rear":
            member = pick_member(3 if len(marching_order) > 3 else len(living) - 1)
        else:
            member = pick_member(0)
        if trap_key == "hidden_pit":
            from .special_items import mark_pit_trapped

            failed, hit_log = self._trap_save_check(
                member,
                trap_level,
                label,
                poison=False,
                show_rolls=show_rolls,
                explain_math=explain_math,
                trap_key=trap_key,
                session=session,
            )
            log.extend(hit_log)
            if failed:
                member.current_life = max(0, member.current_life - damage)
                log.append(f"{member.name} falls into the hidden pit and loses {damage} Life.")
                if member.current_life == 0:
                    log.append(f"{member.name} falls.")
                else:
                    mark_pit_trapped(member)
                    log.append(f"{member.name} is trapped in the pit and needs help or a rope to climb out.")
            return finish()
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
                session=session,
            )
        )
        return finish()

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
        total, rolls = roll_exploding_for_level(rogue)
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
                session=session,
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
                session=session,
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
                session=session,
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
        session: SessionState | None = None,
    ) -> tuple[bool, list[str]]:
        if session is not None:
            from .forsaken_depths_revelation import consume_fd_revelation_auto_save

            if consume_fd_revelation_auto_save(session, show_rolls=show_rolls):
                return False, [f"{member.name} automatically passes the save (Revelation, FD p.55)."]
        from .heroic_skill_effects import trap_save_bonus

        total, rolls = roll_exploding_for_level(member)
        modifier = _trap_save_modifier(member, trap_key, label, poison=poison) + encumbrance_penalty(member)
        modifier += trap_save_bonus(member, trap_key, label)
        log: list[str] = []
        save_label = "poison save" if poison else "trap save"
        if show_rolls:
            log.append(f"Trap {save_label}: {member.name} vs {label}: {' + '.join(str(value) for value in rolls)} + {modifier}.")
        if explain_math:
            log.append(f"Trap {save_label} math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need >= {trap_level}.")
        failed = rolls[0] == 1 or total + modifier < trap_level
        if failed and _caverns_halfling_reroll_applies(member, trap_key):
            total, rolls = roll_exploding_for_level(member)
            if show_rolls:
                log.append(
                    f"Caverns halfling reroll: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}."
                )
            if explain_math:
                log.append(
                    f"Caverns halfling reroll math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need >= {trap_level}."
                )
            failed = rolls[0] == 1 or total + modifier < trap_level
        log.append(f"{member.name} {'fails' if failed else 'passes'} the {save_label} vs {label}.")
        from .equipment_effects import finalize_talisman_after_save

        log.extend(finalize_talisman_after_save(member))
        return failed, log

    def _add_status(self, member: PartyMemberState, status: str) -> None:
        if status not in member.statuses:
            member.statuses.append(status)

    def _fungal_spore_immune(self, member: PartyMemberState) -> bool:
        from .fungal_traps import is_fungal_spore_immune

        return is_fungal_spore_immune(member)

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
    if value.endswith("+"):
        number = int(value[:-1].strip())
        return number, 999
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
    normalized = expression.replace("X", "*").replace("x", "*")
    total = 1
    for part in normalized.split("*"):
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
                result = roller.resolve_trap(
                        trap.trap_key,
                        trap.trap_level,
                        party,
                        marching_order or [],
                        show_rolls=show_rolls,
                        explain_math=explain_math,
                    )
                log.extend(result.log)
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

    if door_type == "locked" and not can_bash_door(member, door_type) and member.class_id.lower() not in {
        "rogue",
        "kukla",
        "assassin",
    }:
        log.append("Only a Rogue can lock-pick or a Warrior/Barbarian (or anyone with a crowbar) can bash a locked door.")
        return False, log
    if door_type == "stuck" and not can_bash_door(member, door_type) and member.class_id.lower() not in {
        "warrior",
        "barbarian",
        "rogue",
        "kukla",
        "assassin",
    }:
        log.append("Only a Warrior/Barbarian (or anyone with a crowbar) can force a stuck door.")
        return False, log
    if door_type == "locked" and member.class_id.lower() in {"kukla", "assassin"} and not member_has_lockpicks(member):
        log.append(f"{member.name} needs lock-picks to work this door.")
        return False, log

    bashing = can_bash_door(member, door_type)
    lockpicking = member.class_id.lower() in {"rogue", "kukla", "assassin"} and door_type in {"locked", "iron"}
    log.append(door_attempt_label(member, door_type))
    total, rolls = roll_exploding_for_level(member)
    modifier = save_modifier(member) + encumbrance_penalty(member, servant_active=servant_active)
    if member.class_id.lower() in {"warrior", "barbarian"} and door_type == "locked":
        modifier += member.level
    elif member.class_id.lower() in {"rogue", "kukla", "assassin"}:
        modifier += lockpick_door_bonus(member)
    modifier += extra_door_modifier(
        member,
        door_type=door_type,
        bashing=bashing,
        lockpicking=lockpicking,
    )
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
    total, rolls = roll_exploding_for_level(member)
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
    total, rolls = roll_exploding_for_level(member)
    modifier = _trap_save_modifier(member, trap_key, label, poison=poison) + encumbrance_penalty(member)
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
    if failed and _caverns_halfling_reroll_applies(member, trap_key):
        total, rolls = roll_exploding_for_level(member)
        if show_rolls:
            log.append(f"Caverns halfling reroll: {member.name} rolls {' + '.join(str(value) for value in rolls)} + {modifier}.")
        if explain_math:
            log.append(f"Caverns halfling reroll math: {' + '.join(str(value) for value in rolls)} + {modifier} = {total + modifier}; need >= {trap_level}.")
        failed = rolls[0] == 1 or total + modifier < trap_level
    if failed:
        applied = damage * 2 if double_on_natural_1 and rolls[0] == 1 else damage
        applied, reduction_log = trap_damage_after_reduction(member, trap_key, label, applied)
        log.extend(reduction_log)
        member.current_life = max(0, member.current_life - applied)
        log.append(f"{member.name} takes {applied} damage from the {label}.")
        if bear_trap and applied > 0 and "Bear Trap Wound" not in member.statuses:
            member.statuses.append("Bear Trap Wound")
            log.append(
                f"{member.name}'s foot is caught: -2 vs bear traps/trapdoors and -1 Attack/Defense until healed."
            )
        if trap_key == "toxic_mushrooms" and applied == 0 and not any(
            status.lower().startswith("toxic spores") for status in member.statuses
        ):
            member.statuses.append("Toxic Spores (-1 Saves, 6 rooms)")
            log.append(f"{member.name} suffers toxic spores: -1 on all Saves for 6 rooms.")
        if member.current_life == 0:
            log.append(f"{member.name} falls.")
    else:
        log.append(f"{member.name} resists the {label}.")
    return log


def _trapdoor_modifier(member: PartyMemberState) -> int:
    from .class_combat import has_active_bear_trap_wound

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
    if has_active_bear_trap_wound(member):
        modifier -= 2
    return modifier


def _bear_trap_modifier(member: PartyMemberState) -> int:
    from .class_combat import has_active_bear_trap_wound

    modifier = 0
    if member.class_id.lower() in {"halfling", "elf"}:
        modifier += 1
    if member.class_id.lower() == "rogue":
        modifier += member.level
    if has_active_bear_trap_wound(member):
        modifier -= 2
    return modifier


CAVERNS_TRAP_KEYS = frozenset(
    {"stalactite", "rockslide", "hidden_pit", "swinging_log", "toxic_mushrooms", "rolling_boulder"}
)


def _trap_save_modifier(member: PartyMemberState, trap_key: str, label: str, *, poison: bool) -> int:
    from .equipment_effects import armor_swim_climb_penalty, talisman_save_bonus, trap_swim_climb_flags
    from .fungal_traps import FUNGAL_TRAP_KEYS, fungal_trap_save_bonus

    swim, climb = trap_swim_climb_flags(trap_key, label)
    if trap_key in FUNGAL_TRAP_KEYS:
        fungal_bonus = fungal_trap_save_bonus(member, trap_key)
        if fungal_bonus is not None:
            modifier = fungal_bonus + talisman_save_bonus(member)
            if swim or climb:
                modifier -= armor_swim_climb_penalty(member)
            return modifier
    if trap_key in CAVERNS_TRAP_KEYS:
        modifier = _caverns_trap_save_modifier(member, trap_key) + talisman_save_bonus(member)
        if swim or climb:
            modifier -= armor_swim_climb_penalty(member)
        return modifier
    return save_modifier(member, trap=True, poison=poison, swim=swim, climb=climb)


def _caverns_trap_save_modifier(member: PartyMemberState, trap_key: str) -> int:
    from .cavern_traps import is_caverns_forester_class

    class_id = member.class_id.lower()
    half_level = member.level // 2
    if trap_key == "rockslide" and class_id in {"rogue", "gnome", "dwarf"}:
        return member.level
    if trap_key == "toxic_mushrooms" and (class_id == "rogue" or is_caverns_forester_class(class_id)):
        return member.level
    if trap_key in {"stalactite", "hidden_pit", "swinging_log", "rolling_boulder"} and class_id == "rogue":
        return member.level
    return half_level


def _caverns_halfling_reroll_applies(member: PartyMemberState, trap_key: str) -> bool:
    return trap_key in CAVERNS_TRAP_KEYS and member.class_id.lower() == "halfling"
