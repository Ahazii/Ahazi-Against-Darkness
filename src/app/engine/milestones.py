from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..schemas import EnemyState, MilestonesProgress, PartyMemberState
from .magic_armor import is_magic_armor
from .magic_weapons import is_magic_weapon
from .scrolls import is_scroll_item, scroll_spell_name
from .spells import normalize_spell_name

_ROOT = Path(__file__).resolve().parents[3]
_MILESTONES_PATH = _ROOT / "data" / "rules" / "milestones.json"
_GEM_VALUE_RE = re.compile(r"(\d+)\s*gp", re.IGNORECASE)

_CASTER_CLASS_IDS = frozenset(
    {"wizard", "elf", "cleric", "druid", "illusionist", "acolyte", "shaman"}
)


def _load_catalog() -> list[dict[str, Any]]:
    return json.loads(_MILESTONES_PATH.read_text(encoding="utf-8"))


def milestone_catalog() -> list[dict[str, Any]]:
    return _load_catalog()


def milestones_table_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for row in _load_catalog():
        notes: list[str] = []
        if row.get("requires_caster"):
            notes.append("Spellcasters only.")
        if row.get("requires_exploding_lightning"):
            notes.append("Needs exploding Lightning.")
        if row.get("bind_on_complete"):
            notes.append("Complete at camp: Bind grimoire.")
        if row.get("craft_on_complete"):
            notes.append("Complete at camp: Craft jewelry.")
        if row.get("manual_complete"):
            notes.append("Complete at camp when ready.")
        rows.append(
            {
                "id": str(row.get("id", "")),
                "name": str(row.get("name", "")),
                "page": str(row.get("source_page", "")),
                "goal": str(row.get("goal", "")),
                "progress": str(row.get("progress_label", "")),
                "reward": str(row.get("reward", "")),
                "how_to": str(row.get("how_to", "")),
                "notes": " ".join(notes),
            }
        )
    return rows


def milestone_by_id(milestone_id: str) -> dict[str, Any] | None:
    needle = milestone_id.strip().lower()
    for row in _load_catalog():
        if row["id"].lower() == needle:
            return row
    return None


def available_milestones(member: PartyMemberState) -> list[dict[str, Any]]:
    completed = {item.lower() for item in member.milestones.completed_ids}
    out: list[dict[str, Any]] = []
    for row in _load_catalog():
        if row["id"].lower() in completed:
            continue
        if row.get("requires_caster") and member.class_id.lower() not in _CASTER_CLASS_IDS:
            continue
        out.append(row)
    return out


def _progress_value(progress: MilestonesProgress, key: str) -> int:
    if key == "panoplia_ready":
        return 1 if progress.panoplia_ready_inventory else 0
    return int(getattr(progress, key, 0))


def milestone_progress_row(member: PartyMemberState, row: dict[str, Any]) -> dict[str, Any]:
    key = row["progress_key"]
    current = _progress_value(member.milestones, key)
    goal = int(row["goal"])
    return {
        "id": row["id"],
        "name": row["name"],
        "goal": goal,
        "current": current,
        "progress_label": row["progress_label"],
        "reward": row["reward"],
        "complete": row["id"] in member.milestones.completed_ids,
        "active": member.milestones.active_id == row["id"],
    }


def assign_milestone(member: PartyMemberState, milestone_id: str | None) -> list[str]:
    if milestone_id is None:
        member.milestones.active_id = None
        return [f"{member.name} clears their active Milestone."]
    row = milestone_by_id(milestone_id)
    if row is None:
        return [f"Unknown Milestone: {milestone_id}."]
    completed = {item.lower() for item in member.milestones.completed_ids}
    if row["id"].lower() in completed:
        return [f"{member.name} has already completed {row['name']}."]
    if row.get("requires_caster") and member.class_id.lower() not in _CASTER_CLASS_IDS:
        return [f"Only spellcasters may take {row['name']}."]
    member.milestones.active_id = row["id"]
    return [f"{member.name} takes the Milestone: {row['name']} ({row['reward']})"]


def _complete_milestone(member: PartyMemberState, milestone_id: str) -> list[str]:
    row = milestone_by_id(milestone_id)
    if row is None:
        return []
    if milestone_id in member.milestones.completed_ids:
        return []
    member.milestones.completed_ids.append(milestone_id)
    member.milestones.active_id = None
    logs = [f"Milestone complete — {member.name} finishes {row['name']}: {row['reward']}"]
    if milestone_id == "thrice_blessed":
        member.milestones.thrice_blessed_unlocked = True
    return logs


def _maybe_complete(member: PartyMemberState) -> list[str]:
    active = member.milestones.active_id
    if not active:
        return []
    row = milestone_by_id(active)
    if row is None:
        return []
    current = _progress_value(member.milestones, row["progress_key"])
    goal = int(row["goal"])
    if row.get("requires_exploding_lightning") and not member.milestones.lightning_exploded:
        return []
    if row.get("manual_complete") or row.get("bind_on_complete") or row.get("craft_on_complete"):
        return []
    if current < goal:
        return []
    return _complete_milestone(member, active)


def _is_goblin(enemy: EnemyState) -> bool:
    name = enemy.name.lower()
    return "goblin" in name and "hobgoblin" not in name


def _is_orc(enemy: EnemyState) -> bool:
    name = enemy.name.lower()
    return "orc" in name and "goblin" not in name


def _is_hobgoblin(enemy: EnemyState) -> bool:
    return "hobgoblin" in enemy.name.lower()


def _is_kobold(enemy: EnemyState) -> bool:
    return "kobold" in enemy.name.lower()


def _is_witch_family(enemy: EnemyState) -> bool:
    name = enemy.name.lower()
    return any(word in name for word in ("witch", "hag", "warlock"))


def _is_witch_encounter(enemies: list[EnemyState]) -> bool:
    return any(_is_witch_family(enemy) for enemy in enemies)


def foe_matches_slayer(milestone_id: str, enemy: EnemyState) -> bool:
    if milestone_id == "goblinslayer":
        return _is_goblin(enemy)
    if milestone_id == "orcslayer":
        return _is_orc(enemy)
    if milestone_id == "scourge_hobgoblins":
        return _is_hobgoblin(enemy)
    if milestone_id == "scourge_kobolds":
        return _is_kobold(enemy)
    if milestone_id == "witchfinder":
        return _is_witch_family(enemy)
    if milestone_id == "vermin_exterminator":
        return enemy.category == "vermin"
    return False


def has_completed(member: PartyMemberState, milestone_id: str) -> bool:
    return milestone_id in member.milestones.completed_ids


def record_defeated_foes(
    party: list[PartyMemberState],
    defeated: list[EnemyState],
) -> list[str]:
    logs: list[str] = []
    for enemy in defeated:
        if enemy.life > 0:
            continue
        for member in party:
            if member.current_life <= 0:
                continue
            active = member.milestones.active_id
            if not active or not foe_matches_slayer(active, enemy):
                continue
            if active in {"goblinslayer", "orcslayer", "scourge_hobgoblins", "scourge_kobolds"}:
                key = {
                    "goblinslayer": "levels_goblins",
                    "orcslayer": "levels_orcs",
                    "scourge_hobgoblins": "levels_hobgoblins",
                    "scourge_kobolds": "levels_kobolds",
                }[active]
                setattr(member.milestones, key, getattr(member.milestones, key) + enemy.level)
            elif active == "witchfinder":
                member.milestones.witches_slayed += 1
            elif active == "vermin_exterminator":
                member.milestones.vermin_slayed += 1
            logs.extend(_maybe_complete(member))
    return logs


def record_lightning_damage(
    caster: PartyMemberState,
    damage: int,
    *,
    exploded: bool,
) -> list[str]:
    if caster.milestones.active_id != "thundermaster":
        return []
    if exploded:
        caster.milestones.lightning_exploded = True
    if damage > 0:
        caster.milestones.lightning_damage += damage
    return _maybe_complete(caster)


def record_sleep_levels(caster: PartyMemberState, levels: int) -> list[str]:
    if caster.milestones.active_id != "slumbermaster" or levels <= 0:
        return []
    caster.milestones.sleep_levels += levels
    return _maybe_complete(caster)


def record_gaze_save(member: PartyMemberState, *, label: str) -> list[str]:
    if member.milestones.active_id != "gaze_resistance":
        return []
    lower = label.lower()
    if "gaze" not in lower and "petrif" not in lower:
        return []
    member.milestones.gaze_saves += 1
    return _maybe_complete(member)


def gem_item_value_gp(item: str) -> int:
    from .gem_items import gem_item_value_gp as _value

    return _value(item)


def record_inventory_item_acquired(member: PartyMemberState, item: str) -> list[str]:
    logs: list[str] = []
    if is_scroll_item(item):
        member.milestones.scrolls_collected += 1
        logs.extend(_maybe_complete(member))
    value = gem_item_value_gp(item)
    if value >= 50 and member.milestones.active_id == "gem_collector" and not member.milestones.gem_collector_crafted:
        member.milestones.gems_50gp += 1
        logs.extend(_maybe_complete(member))
    if member.milestones.active_id == "panoplia":
        logs.extend(update_panoplia_readiness(member))
    return logs


def member_has_magic_weapon(member: PartyMemberState) -> bool:
    return any(is_magic_weapon(item) for item in member.inventory)


def member_has_magic_shield(member: PartyMemberState) -> bool:
    return any("magic shield" in item.lower() or "ring of protection" in item.lower() for item in member.inventory)


def member_has_magic_body_armor(member: PartyMemberState) -> bool:
    return any(
        is_magic_armor(item) and "shield" not in item.lower() and "ring of protection" not in item.lower()
        for item in member.inventory
    )


def update_panoplia_readiness(member: PartyMemberState) -> list[str]:
    if member.milestones.active_id != "panoplia" or member.milestones.panoplia_styled:
        return []
    ready = member_has_magic_weapon(member) and member_has_magic_shield(member) and member_has_magic_body_armor(member)
    member.milestones.panoplia_ready_inventory = ready
    return _maybe_complete(member) if ready else []


def bind_scroll_librarian(member: PartyMemberState, spell_name: str) -> list[str]:
    row = milestone_by_id("scroll_librarian")
    if row is None:
        return ["Scroll Librarian is not configured."]
    if member.class_id.lower() not in _CASTER_CLASS_IDS:
        return ["Only spellcasters may complete Scroll Librarian."]
    if member.milestones.active_id != "scroll_librarian":
        return [f"{member.name} is not working on Scroll Librarian."]
    if member.milestones.scrolls_collected < int(row["goal"]):
        return [f"Need {row['goal']} scrolls collected ({member.milestones.scrolls_collected} so far)."]
    scrolls = [item for item in member.inventory if is_scroll_item(item)]
    if len(scrolls) < int(row["goal"]):
        return [f"Need at least {row['goal']} scrolls in inventory to bind the grimoire."]
    spells_found = [scroll_spell_name(item) for item in scrolls]
    spells_found = [spell for spell in spells_found if spell]
    if not spells_found:
        return ["No readable spells on the scrolls to bind."]
    chosen = spell_name.strip() or spells_found[0]
    normalized = normalize_spell_name(chosen)
    if not any(normalize_spell_name(spell) == normalized for spell in spells_found):
        return [f"Choose a spell present on the sacrificed scrolls ({', '.join(sorted(set(spells_found)))})."]
    for item in scrolls:
        member.inventory.remove(item)
    member.milestones.scroll_librarian_spell = chosen
    if chosen not in member.milestones.extra_spell_slots:
        member.milestones.extra_spell_slots.append(chosen)
    if chosen not in member.spells:
        member.spells.append(chosen)
    logs = [f"{member.name} binds {len(scrolls)} scrolls into a grimoire, gaining a permanent {chosen} slot."]
    logs.extend(_complete_milestone(member, "scroll_librarian"))
    return logs


def craft_gem_collector_jewelry(member: PartyMemberState) -> list[str]:
    if member.milestones.active_id != "gem_collector":
        return [f"{member.name} is not working on Gem Collector."]
    row = milestone_by_id("gem_collector")
    if row is None:
        return ["Gem Collector is not configured."]
    if member.milestones.gems_50gp < int(row["goal"]):
        return [f"Need {row['goal']} gems worth at least 50gp each."]
    gems = [item for item in member.inventory if gem_item_value_gp(item) >= 50]
    if len(gems) < int(row["goal"]):
        return [f"Need at least {row['goal']} qualifying gems in inventory."]
    total = sum(gem_item_value_gp(item) for item in gems[: int(row["goal"])])
    for item in gems[: int(row["goal"])]:
        member.inventory.remove(item)
    jewelry_value = int(total * 1.5)
    jewelry = f"Jewelry (milestone, {jewelry_value}gp)"
    member.inventory.append(jewelry)
    member.milestones.gem_collector_crafted = True
    logs = [
        f"{member.name} crafts {jewelry} from {int(row['goal'])} gems "
        f"(150% of {total}gp gem value)."
    ]
    logs.extend(_complete_milestone(member, "gem_collector"))
    return logs


def create_panoplia(member: PartyMemberState) -> list[str]:
    if member.milestones.active_id != "panoplia":
        return [f"{member.name} is not working on Panoplia."]
    if not (member_has_magic_weapon(member) and member_has_magic_shield(member) and member_has_magic_body_armor(member)):
        return ["Panoplia requires 1 magic weapon, 1 magic shield, and 1 magic armor."]
    if member.gold < 100:
        return ["Panoplia styling costs 100gp."]
    member.gold -= 100
    member.milestones.panoplia_styled = True
    member.milestones.panoplia_favor_available = True
    logs = [f"{member.name} spends 100gp to style a panoplia and earns a campaign favor."]
    logs.extend(_complete_milestone(member, "panoplia"))
    return logs


def use_panoplia_favor(member: PartyMemberState, favor_kind: str) -> list[str]:
    if not member.milestones.panoplia_favor_available or member.milestones.panoplia_favor_used:
        return ["No Panoplia favor is available."]
    kind = favor_kind.strip().lower()
    if kind == "gold":
        member.gold += 300
        member.milestones.panoplia_favor_used = True
        return [f"{member.name} calls in the Panoplia favor for 300gp."]
    if kind == "fine":
        member.milestones.panoplia_favor_used = True
        return [f"{member.name} calls in the Panoplia favor to ignore a fine."]
    if kind == "jail":
        member.milestones.panoplia_favor_used = True
        return [f"{member.name} calls in the Panoplia favor to get out of jail."]
    if kind == "resurrection":
        member.milestones.panoplia_favor_used = True
        return [
            f"{member.name} calls in the Panoplia favor for resurrection "
            "(requires the hero's body to be carried home)."
        ]
    return ["Unknown Panoplia favor."]


def record_resurrection(member: PartyMemberState) -> list[str]:
    member.milestones.resurrection_count += 1
    logs: list[str] = []
    if member.milestones.active_id == "thrice_blessed":
        logs.extend(_maybe_complete(member))
    if member.milestones.thrice_blessed_unlocked or has_completed(member, "thrice_blessed"):
        member.milestones.thrice_blessed_sacrifice_paid = False
    return logs


def pay_thrice_blessed_sacrifice(member: PartyMemberState) -> list[str]:
    if not (member.milestones.thrice_blessed_unlocked or has_completed(member, "thrice_blessed")):
        return [f"{member.name} has not unlocked Thrice Blessed."]
    cost = member.level * 10
    if member.gold < cost:
        return [f"Thrice Blessed requires {cost}gp in sacrifices before this adventure."]
    member.gold -= cost
    member.milestones.thrice_blessed_sacrifice_paid = True
    return [f"{member.name} offers {cost}gp in sacrifices to the gods (Thrice Blessed)."]


def thrice_blessed_save_active(member: PartyMemberState) -> bool:
    if not (member.milestones.thrice_blessed_unlocked or has_completed(member, "thrice_blessed")):
        return False
    return member.milestones.thrice_blessed_sacrifice_paid


def milestone_attack_bonus(member: PartyMemberState, enemy: EnemyState) -> int:
    bonus = 0
    if has_completed(member, "goblinslayer") and _is_goblin(enemy):
        bonus += 1
    if has_completed(member, "orcslayer") and _is_orc(enemy):
        bonus += 1
    if has_completed(member, "scourge_hobgoblins") and _is_hobgoblin(enemy):
        bonus += 1
    if has_completed(member, "scourge_kobolds") and _is_kobold(enemy):
        bonus += 1
    if has_completed(member, "vermin_exterminator") and enemy.category == "vermin":
        bonus += 1
    return bonus


def milestone_defense_bonus(member: PartyMemberState, enemy: EnemyState) -> int:
    bonus = 0
    if has_completed(member, "goblinslayer") and _is_goblin(enemy):
        bonus += 1
    if has_completed(member, "orcslayer") and _is_orc(enemy):
        bonus += 1
    if has_completed(member, "scourge_hobgoblins") and _is_hobgoblin(enemy):
        bonus += 1
    if has_completed(member, "scourge_kobolds") and _is_kobold(enemy):
        bonus += 1
    return bonus


def milestone_save_bonus(
    member: PartyMemberState,
    *,
    save_label: str = "",
    enemies: list[EnemyState] | None = None,
) -> int:
    bonus = 0
    label = save_label.lower()
    if has_completed(member, "witchfinder") and enemies and _is_witch_encounter(enemies):
        if any(word in label for word in ("spell", "curse", "magic")):
            bonus += 1
    if has_completed(member, "gaze_resistance") and ("gaze" in label or "petrif" in label):
        bonus += 2
    if thrice_blessed_save_active(member):
        bonus += 1
    return bonus


def milestone_spellcasting_bonus(member: PartyMemberState, spell_key: str) -> int:
    key = spell_key.strip().lower()
    bonus = 0
    if has_completed(member, "thundermaster") and key == "lightning":
        bonus += 1
    if has_completed(member, "slumbermaster") and key == "sleep":
        bonus += 1
    return bonus
