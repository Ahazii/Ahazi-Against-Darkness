from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ..schemas import (
    EnemyState,
    HirelingState,
    PartyMemberState,
    PendingAcolyteBlessingState,
    PendingBodyguardInterceptState,
    SessionState,
)
from .dice import roll_d6, roll_exploding_d6
from .expert_skill_effects import front_rank_has_commanding_presence, has_skill

_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_PATH = _ROOT / "data" / "rules" / "hirelings.json"

HIRELING_MARCHING_ORDERS = (1, 2, 3, 4, 5, 6)
MAX_MARCHING_ORDER = 6

_RETAINER_LOADOUT: dict[str, dict[str, str | bool]] = {
    "acolyte": {"weapon": "one_handed", "armor": "light", "no_shield": True},
    "dungeon_guide": {"weapon": "light", "armor": "light"},
    "lantern_bearer": {"weapon": "one_handed", "armor": "light"},
    "minstrel": {"weapon": "light", "armor": "none"},
    "porter": {"weapon": "light_crush_slash", "armor": "light"},
    "rat_exterminator": {"weapon": "one_handed", "armor": "light"},
    "spear_carrier": {"weapon": "one_handed", "armor": "light"},
    "spear_carrier_sidearm": {"weapon": "slashing_hand"},
    "surgeon": {"weapon": "light", "armor": "none", "no_shield": True},
}


def _is_slashing_hand_weapon(item: str) -> bool:
    from .weapons import weapon_profile

    profile = weapon_profile(item)
    return profile.kind == "melee" and profile.slashing and not profile.two_handed


def retainer_gear_violation(retainer_type: str, item: str) -> str | None:
    rules = _RETAINER_LOADOUT.get(retainer_type)
    if not rules:
        return None
    lower = item.lower()
    if rules.get("no_shield") and "shield" in lower:
        return f"{item} is not allowed for this retainer (no shield)."
    armor_rule = str(rules.get("armor", "any"))
    if armor_rule == "none":
        if "armor" in lower or "shield" in lower:
            return f"{item} is not allowed for this retainer (no armor or shield)."
    elif armor_rule == "light":
        if "heavy armor" in lower:
            return f"{item} is not light armor for this retainer."
    if "two-handed" in lower or "2-handed" in lower:
        return f"{item} is too heavy for this retainer (two-handed weapons are not allowed)."
    weapon_rule = str(rules.get("weapon", "any"))
    if weapon_rule == "slashing_hand":
        if not _is_slashing_hand_weapon(item):
            return f"{item} is not a slashing hand weapon for this retainer."
        return None
    if weapon_rule == "light_crush_slash":
        if any(token in lower for token in ("heavy", "bow", "crossbow", "rifle", "pistol", "two-handed", "2-handed")):
            return f"{item} is not a light weapon for this retainer."
        if "piercing" in lower and "crushing" not in lower and "slashing" not in lower:
            if not any(token in lower for token in ("dagger", "sword", "axe", "mace", "club", "hammer")):
                return f"{item} must be a light crushing or slashing weapon for this retainer."
        return None
    if weapon_rule == "light":
        if any(token in lower for token in ("heavy", "bow", "crossbow", "rifle", "pistol", "two-handed", "2-handed")):
            return f"{item} is not a light weapon for this retainer."
    if weapon_rule == "one_handed":
        if any(token in lower for token in ("bow", "crossbow", "rifle", "pistol", "two-handed", "2-handed")):
            return f"{item} is not a one-handed weapon for this retainer."
    return None


def is_bulky_carriable_item(item: str) -> bool:
    lower = item.lower().strip()
    if not lower:
        return False
    if "food ration" in lower:
        return False
    if "gp" in lower and any(char.isdigit() for char in lower):
        return False
    if lower.startswith("scroll") or "potion" in lower or "poison vial" in lower:
        return False
    return True


def offer_bodyguard_intercept(
    session: SessionState,
    protectee: PartyMemberState,
    hireling: HirelingState,
    enemy: EnemyState,
) -> list[str]:
    session.pending_bodyguard_intercept = PendingBodyguardInterceptState(
        protectee_id=protectee.character_id,
        hireling_id=hireling.id,
        enemy_id=enemy.id,
    )
    return [f"{hireling.name} may intercept the attack meant for {protectee.name}."]


def resolve_bodyguard_intercept(
    session: SessionState,
    *,
    choice: str | None,
    show_rolls: bool = True,
) -> list[str]:
    pending = session.pending_bodyguard_intercept
    if pending is None:
        return ["No bodyguard intercept choice is pending."]
    if choice not in {"intercept", "decline"}:
        return ["Choose whether the bodyguard intercepts or the hero faces the blow."]
    protectee = next((member for member in session.party if member.character_id == pending.protectee_id), None)
    hireling = _hireling_by_id(session, pending.hireling_id)
    if protectee is None or protectee.current_life <= 0 or hireling is None or hireling.life <= 0:
        session.pending_bodyguard_intercept = None
        return ["That bodyguard intercept is no longer possible."]
    tile = None
    if session.map_state and session.map_state.current_tile_id:
        tile = next(
            (item for item in session.map_state.tiles if item.id == session.map_state.current_tile_id),
            None,
        )
    enemy = None
    if tile is not None:
        enemy = next((foe for foe in tile.enemies if foe.id == pending.enemy_id and foe.life > 0), None)
    if enemy is None:
        session.pending_bodyguard_intercept = None
        return ["The attack that triggered the bodyguard choice has already ended."]
    session.pending_bodyguard_intercept = None
    log: list[str] = []
    if choice == "intercept":
        log.append(f"{hireling.name} steps in front of {protectee.name}.")
        passed, bg_log = resolve_hireling_defense(hireling, enemy, show_rolls=show_rolls)
        log.extend(bg_log)
        if not passed:
            apply_hireling_damage(hireling, 1, log, session=session, show_rolls=show_rolls)
        return log
    log.append(f"{protectee.name} faces {enemy.name} without bodyguard help.")
    living = [foe for foe in tile.enemies if foe.life > 0] if tile is not None else [enemy]
    from .combat import resolve_foe_melee_on_member

    log.extend(
        resolve_foe_melee_on_member(
            session,
            enemy,
            protectee,
            show_rolls=show_rolls,
            living_enemies=living,
        )
    )
    return log


def apply_foe_melee_hit_to_member(
    session: SessionState,
    enemy: EnemyState,
    target: PartyMemberState,
    *,
    show_rolls: bool = True,
) -> list[str]:
    from .class_combat import defense_modifier
    from .combat import defense_succeeds
    from .dice import roll_exploding_for_level

    log: list[str] = []
    total, rolls = roll_exploding_for_level(target)
    modifier = defense_modifier(target, enemy)
    final_total = total + modifier
    if show_rolls:
        log.append(
            f"Defense roll: {target.name} vs {enemy.name}: "
            f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final_total}."
        )
    if defense_succeeds(final_total, enemy.level, natural=rolls[0]):
        log.append(f"{target.name} avoids damage from {enemy.name}.")
        return log
    target.current_life = max(0, target.current_life - 1)
    log.append(f"{target.name} takes 1 damage from {enemy.name}.")
    if target.current_life <= 0:
        log.append(f"{target.name} falls.")
        log.extend(check_hireling_morale_after_casualty(session, reason=f"{target.name} fell", show_rolls=show_rolls))
    return log


def notify_hireling_morale_casualty(
    session: SessionState,
    *,
    reason: str,
    show_rolls: bool = True,
) -> list[str]:
    return check_hireling_morale_after_casualty(session, reason=reason, show_rolls=show_rolls)


def acolyte_for_blessing_preservation(
    session: SessionState,
    cleric: PartyMemberState,
) -> HirelingState | None:
    hireling = _adjacent_hireling_for_member(session, cleric, "acolyte")
    if hireling is None or _ability_used(hireling, "acolyte_blessing"):
        return None
    return hireling


def offer_acolyte_blessing_preservation(
    session: SessionState,
    cleric: PartyMemberState,
    hireling: HirelingState,
) -> list[str]:
    session.pending_acolyte_blessing = PendingAcolyteBlessingState(
        cleric_id=cleric.character_id,
        hireling_id=hireling.id,
    )
    return [f"{hireling.name} may try to preserve {cleric.name}'s Blessing (d6+L, need 7+)."]


def resolve_acolyte_blessing(
    session: SessionState,
    *,
    choice: str | None,
    show_rolls: bool = True,
) -> list[str]:
    pending = session.pending_acolyte_blessing
    if pending is None:
        return ["No acolyte Blessing choice is pending."]
    if choice not in {"try", "skip"}:
        return ["Choose whether the acolyte tries to preserve Blessing or not."]
    cleric = next((member for member in session.party if member.character_id == pending.cleric_id), None)
    hireling = _hireling_by_id(session, pending.hireling_id)
    session.pending_acolyte_blessing = None
    if cleric is None or hireling is None or hireling.life <= 0:
        return ["That acolyte Blessing choice is no longer possible."]
    if choice == "skip":
        return [f"{cleric.name} does not call on {hireling.name} to preserve Blessing."]
    preserved, log = try_acolyte_preserve_blessing(session, cleric, show_rolls=show_rolls, hireling=hireling)
    if preserved:
        from .spells import normalize_spell_name

        expended = list(session.expended_spells.get(cleric.character_id, []))
        if expended and normalize_spell_name(expended[-1]) == "blessing":
            expended.pop()
            session.expended_spells[cleric.character_id] = expended
            log.append("Blessing remains available this adventure.")
    return log


def outside_party_gold(session: SessionState) -> int:
    return sum(member.gold + member.bank_gold for member in session.party if member.current_life > 0)


def spend_outside_party_gold(
    session: SessionState,
    amount: int,
    *,
    label: str,
) -> tuple[bool, list[str]]:
    if amount <= 0:
        return True, []
    if outside_party_gold(session) < amount:
        return False, []
    remaining = amount
    log: list[str] = []
    for member in sorted((item for item in session.party if item.current_life > 0), key=lambda item: item.marching_order):
        if remaining <= 0:
            break
        bank_take = min(member.bank_gold, remaining)
        if bank_take:
            member.bank_gold -= bank_take
            remaining -= bank_take
            log.append(f"{member.name} pays {bank_take}gp from home bank funds for {label}.")
        if remaining <= 0:
            break
        carry_take = min(member.gold, remaining)
        if carry_take:
            member.gold -= carry_take
            remaining -= carry_take
            log.append(f"{member.name} pays {carry_take}gp carried outside for {label}.")
    return True, log


def load_hirelings_catalog() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def retainer_definition(catalog: dict[str, Any], retainer_type: str) -> dict[str, Any] | None:
    key = retainer_type.strip().lower()
    for row in catalog.get("retainers", []):
        if str(row.get("id", "")).strip().lower() == key:
            return row
    return None


def professional_definition(catalog: dict[str, Any], professional_id: str) -> dict[str, Any] | None:
    key = professional_id.strip().lower()
    for row in catalog.get("professionals", []):
        if str(row.get("id", "")).strip().lower() == key:
            return row
    return None


def party_expert_trained(party: list[PartyMemberState]) -> bool:
    return any(getattr(member, "expert_trained", False) for member in party)


def living_hirelings(session: SessionState) -> list[HirelingState]:
    return [hireling for hireling in session.hirelings or [] if hireling.life > 0]


def active_hireling_count(session: SessionState) -> int:
    return len(session.hirelings or [])


def can_hire_retainers(session: SessionState, catalog: dict[str, Any] | None = None) -> tuple[bool, str]:
    catalog = catalog or load_hirelings_catalog()
    if not session.camped_outside:
        return False, "Hire retainers while camped outside the dungeon."
    if not party_expert_trained(session.party):
        return False, "Expert tier training is required to hire retainers (Four Against the Abyss p.27)."
    max_retainers = int(catalog.get("max_retainers", 2))
    if active_hireling_count(session) >= max_retainers:
        return False, f"The party already has the maximum of {max_retainers} retainers."
    return True, ""


def _party_has_warrior_barbarian_dwarf(party: list[PartyMemberState]) -> bool:
    return any(member.class_id.lower() in {"warrior", "barbarian", "dwarf"} for member in party if member.current_life > 0)


def _adjacent_marching_orders(left: int, right: int) -> bool:
    return abs(left - right) == 1


def _marching_occupants(
    session: SessionState,
    *,
    exclude_hireling_id: str | None = None,
    exclude_character_id: str | None = None,
) -> list[PartyMemberState | HirelingState]:
    occupants: list[PartyMemberState | HirelingState] = [
        member for member in session.party if member.character_id != exclude_character_id
    ]
    occupants.extend(
        hireling
        for hireling in session.hirelings or []
        if hireling.life > 0 and hireling.id != exclude_hireling_id
    )
    return occupants


def _marching_order_snapshot(session: SessionState) -> dict[str, int]:
    snapshot = {f"party:{member.character_id}": member.marching_order for member in session.party}
    snapshot.update({f"hireling:{hireling.id}": hireling.marching_order for hireling in session.hirelings or []})
    return snapshot


def _restore_marching_order_snapshot(session: SessionState, snapshot: dict[str, int]) -> None:
    for member in session.party:
        key = f"party:{member.character_id}"
        if key in snapshot:
            member.marching_order = snapshot[key]
    for hireling in session.hirelings or []:
        key = f"hireling:{hireling.id}"
        if key in snapshot:
            hireling.marching_order = snapshot[key]


def _first_open_marching_order(session: SessionState, *, exclude_hireling_id: str | None = None) -> int | None:
    taken = {item.marching_order for item in _marching_occupants(session, exclude_hireling_id=exclude_hireling_id)}
    for order in HIRELING_MARCHING_ORDERS:
        if order not in taken:
            return order
    return None


def repair_shared_marching_orders(session: SessionState) -> bool:
    """Move duplicate hireling slots to the next open #1–#6 position."""
    changed = False
    while True:
        occupants = _marching_occupants(session)
        by_order: dict[int, list[PartyMemberState | HirelingState]] = {}
        for item in occupants:
            by_order.setdefault(item.marching_order, []).append(item)
        duplicate = next(((order, items) for order, items in by_order.items() if len(items) > 1), None)
        if duplicate is None:
            break
        _, items = duplicate
        items.sort(key=lambda row: (0 if isinstance(row, PartyMemberState) else 1, row.name))
        moved = False
        for item in items[1:]:
            if not isinstance(item, HirelingState):
                continue
            slot = _first_open_marching_order(session, exclude_hireling_id=item.id)
            if slot is None:
                continue
            if _move_hireling_marching_order(session, item, slot):
                changed = True
                moved = True
                break
        if not moved:
            break
    return changed


def _insert_marching_occupant(
    session: SessionState,
    occupant: PartyMemberState | HirelingState,
    position: int,
    *,
    exclude_hireling_id: str | None = None,
) -> bool:
    if position not in HIRELING_MARCHING_ORDERS:
        return False
    others = _marching_occupants(session, exclude_hireling_id=exclude_hireling_id)
    if len(others) >= MAX_MARCHING_ORDER:
        return False
    taken = {item.marching_order for item in others}
    if position not in taken:
        occupant.marching_order = position
        return True
    for item in sorted(others, key=lambda row: row.marching_order, reverse=True):
        if item.marching_order >= position:
            item.marching_order += 1
            if item.marching_order > MAX_MARCHING_ORDER:
                return False
    occupant.marching_order = position
    return True


def _move_marching_occupant(
    session: SessionState,
    occupant: PartyMemberState | HirelingState,
    position: int,
    *,
    exclude_hireling_id: str | None = None,
    exclude_character_id: str | None = None,
) -> bool:
    if position not in HIRELING_MARCHING_ORDERS:
        return False
    previous = occupant.marching_order
    if previous == position:
        return True
    others = _marching_occupants(
        session,
        exclude_hireling_id=exclude_hireling_id,
        exclude_character_id=exclude_character_id,
    )
    if position < previous:
        for item in sorted(others, key=lambda row: row.marching_order, reverse=True):
            if position <= item.marching_order < previous:
                item.marching_order += 1
    else:
        for item in sorted(others, key=lambda row: row.marching_order):
            if previous < item.marching_order <= position:
                item.marching_order -= 1
    occupant.marching_order = position
    return True


def _move_hireling_marching_order(session: SessionState, hireling: HirelingState, position: int) -> bool:
    return _move_marching_occupant(session, hireling, position, exclude_hireling_id=hireling.id)


def _default_marching_order_for_retainer(
    session: SessionState,
    row: dict[str, Any],
    assigned_character_id: str | None,
) -> int | None:
    assignment = str(row.get("assignment", "none"))
    taken = {item.marching_order for item in _marching_occupants(session)}
    if assignment in {"cleric", "protectee", "gear_owner"} and assigned_character_id:
        assignee = next((member for member in session.party if member.character_id == assigned_character_id), None)
        if assignee is not None:
            for candidate in (assignee.marching_order + 1, assignee.marching_order - 1):
                if candidate in HIRELING_MARCHING_ORDERS and candidate not in taken:
                    return candidate
            if assignee.marching_order in HIRELING_MARCHING_ORDERS:
                return assignee.marching_order
            for candidate in HIRELING_MARCHING_ORDERS:
                if candidate not in taken and _adjacent_marching_orders(candidate, assignee.marching_order):
                    return candidate
    return _first_open_marching_order(session)


def assignment_valid(
    hireling: HirelingState,
    party: list[PartyMemberState],
    *,
    catalog: dict[str, Any] | None = None,
) -> tuple[bool, str]:
    catalog = catalog or load_hirelings_catalog()
    row = retainer_definition(catalog, hireling.retainer_type)
    if row is None:
        return False, "Unknown retainer type."
    assignment = str(row.get("assignment", "none"))
    if assignment == "none":
        return True, ""
    if not hireling.assigned_character_id:
        if assignment in {"cleric", "protectee", "gear_owner"}:
            return False, f"{row['name']} requires an assigned hero."
        return True, ""
    assignee = next((member for member in party if member.character_id == hireling.assigned_character_id), None)
    if assignee is None or assignee.current_life <= 0:
        return False, "Choose a living hero for this retainer assignment."
    if assignment == "cleric" and assignee.class_id.lower() != "cleric":
        return False, "An Acolyte must be assigned to a cleric."
    if not _adjacent_marching_orders(hireling.marching_order, assignee.marching_order):
        return False, f"{row['name']} must occupy a marching slot adjacent to the assigned hero."
    return True, ""


def hire_retainer(
    session: SessionState,
    retainer_type: str,
    *,
    name: str | None = None,
    assigned_character_id: str | None = None,
    marching_order: int | None = None,
    catalog: dict[str, Any] | None = None,
) -> list[str]:
    catalog = catalog or load_hirelings_catalog()
    log: list[str] = []
    ok, reason = can_hire_retainers(session, catalog)
    if not ok:
        return [reason]
    row = retainer_definition(catalog, retainer_type)
    if row is None:
        return ["Choose a retainer type from the catalog."]
    if row.get("requires_cleric") and not any(
        member.class_id.lower() == "cleric" and member.current_life > 0 for member in session.party
    ):
        return ["An Acolyte requires a living cleric in the party."]
    if row.get("requires_no_warrior_barbarian_dwarf") and _party_has_warrior_barbarian_dwarf(session.party):
        return ["A Man-At-Arms may be hired only when no warrior, barbarian, or dwarf is in the party."]
    fee = int(row.get("fee_gp", 0))
    if outside_party_gold(session) < fee:
        return [f"Hiring a {row['name']} costs {fee}gp from party or home-bank funds."]
    assignment = str(row.get("assignment", "none"))
    if assignment in {"cleric", "protectee", "gear_owner"} and not assigned_character_id:
        return [f"{row['name']} must be assigned to a hero when hired."]
    slot = marching_order or _default_marching_order_for_retainer(session, row, assigned_character_id)
    if slot is None:
        return ["No marching slots (#1–#6) are free for a retainer."]
    if slot not in HIRELING_MARCHING_ORDERS:
        return ["Retainers use marching slots #1 through #6."]
    display_name = (name or "").strip() or row["name"]
    hireling = HirelingState(
        id=uuid.uuid4().hex,
        retainer_type=str(row["id"]),
        name=display_name,
        life=int(row.get("life", 2)),
        max_life=int(row.get("life", 2)),
        marching_order=slot,
        fee_paid_gp=fee,
        assigned_character_id=assigned_character_id,
        lantern_lit=str(row["id"]) == "lantern_bearer",
    )
    snapshot = _marching_order_snapshot(session)
    if not _insert_marching_occupant(session, hireling, slot):
        _restore_marching_order_snapshot(session, snapshot)
        return ["No marching slots (#1–#6) are free for a retainer."]
    valid, note = assignment_valid(hireling, session.party, catalog=catalog)
    if not valid:
        _restore_marching_order_snapshot(session, snapshot)
        return [note]
    paid, payment_log = spend_outside_party_gold(session, fee, label=f"{row['name']} retainer fee")
    if not paid:
        _restore_marching_order_snapshot(session, snapshot)
        return payment_log or [f"Could not pay the {fee}gp retainer fee."]
    log.extend(payment_log)
    session.hirelings = list(session.hirelings or []) + [hireling]
    log.append(
        f"Hired {display_name} ({row['name']}) for {fee}gp. Marching order #{slot}. "
        "Retainer fee is spent for this adventure even if the hireling dies."
    )
    return log


def dismiss_hireling(session: SessionState, hireling_id: str | None) -> list[str]:
    if not session.camped_outside:
        return ["Dismiss retainers while camped outside."]
    hireling = next((item for item in session.hirelings or [] if item.id == hireling_id), None)
    if hireling is None:
        return ["Choose a retainer to dismiss."]
    session.hirelings = [item for item in session.hirelings if item.id != hireling_id]
    note = f"{hireling.name} is dismissed before the next foray."
    if hireling.retainer_type == "bodyguard":
        note += " Bodyguard gear is returned; no refund of the hiring fee."
    return [note]


def set_hireling_assignment(
    session: SessionState,
    hireling_id: str | None,
    assigned_character_id: str | None,
) -> list[str]:
    hireling = next((item for item in session.hirelings or [] if item.id == hireling_id), None)
    if hireling is None:
        return ["Choose a retainer to reassign."]
    hireling.assigned_character_id = assigned_character_id or None
    valid, note = assignment_valid(hireling, session.party)
    if not valid:
        return [note]
    assignee = next((member for member in session.party if member.character_id == assigned_character_id), None)
    label = assignee.name if assignee else "no one"
    return [f"{hireling.name} is now assigned to {label}."]


def set_hireling_marching_order(
    session: SessionState,
    hireling_id: str | None,
    position: int | None,
) -> list[str]:
    if session.mode != "exploration":
        return ["Change retainer marching order during exploration."]
    if position not in HIRELING_MARCHING_ORDERS:
        return ["Retainers use marching slots #1 through #6."]
    hireling = next((item for item in session.hirelings or [] if item.id == hireling_id), None)
    if hireling is None:
        return ["Choose a retainer to reposition."]
    snapshot = _marching_order_snapshot(session)
    if not _move_hireling_marching_order(session, hireling, position):
        _restore_marching_order_snapshot(session, snapshot)
        return ["No marching slots (#1–#6) are free for a retainer."]
    valid, note = assignment_valid(hireling, session.party)
    if not valid:
        _restore_marching_order_snapshot(session, snapshot)
        return [note]
    return [f"{hireling.name} moves to marching slot #{position}."]


def set_party_member_marching_order(
    session: SessionState,
    character_id: str | None,
    position: int | None,
) -> list[str]:
    if session.mode != "exploration":
        return ["Change marching order during combat."]
    if not character_id or position is None or position not in HIRELING_MARCHING_ORDERS:
        return ["Choose a hero and position 1-6."]
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None:
        return ["That hero is not in the party."]
    if member.current_life <= 0:
        return [f"{member.name} cannot move in marching order while fallen."]
    old_position = member.marching_order
    if old_position == position:
        return [f"{member.name} is already in position {position}."]
    snapshot = _marching_order_snapshot(session)
    if not _move_marching_occupant(session, member, position, exclude_character_id=member.character_id):
        _restore_marching_order_snapshot(session, snapshot)
        return ["No marching slots (#1–#6) are free."]
    for hireling in living_hirelings(session):
        valid, note = assignment_valid(hireling, session.party)
        if not valid:
            _restore_marching_order_snapshot(session, snapshot)
            return [note]
    return [f"Marching order: {member.name} moves from #{old_position} to #{position}."]


def pay_hireling_treasure_share(session: SessionState, hireling_id: str | None) -> list[str]:
    if not session.camped_outside:
        return ["Pay retainer treasure shares while camped outside."]
    hireling = next((item for item in session.hirelings or [] if item.id == hireling_id), None)
    if hireling is None:
        return ["Choose a retainer for a treasure share."]
    if hireling.treasure_share_paid:
        return [f"{hireling.name} already received a treasure share this camp."]
    share = hireling.fee_paid_gp * 2
    if outside_party_gold(session) < share:
        return [f"A treasure share of {share}gp (2× hiring fee) is required."]
    paid, payment_log = spend_outside_party_gold(session, share, label=f"{hireling.name} treasure share")
    if not paid:
        return payment_log or [f"Could not pay the {share}gp treasure share."]
    hireling.treasure_share_paid = True
    return payment_log + [f"{hireling.name} receives {share}gp treasure share (+1 morale next adventure)."]


def resurrect_hireling(session: SessionState, hireling_id: str | None) -> list[str]:
    if not session.camped_outside:
        return ["Resurrect retainers while camped outside."]
    fallen = next((item for item in session.hirelings or [] if item.id == hireling_id and item.life <= 0), None)
    if fallen is None:
        return ["Choose a slain retainer to resurrect."]
    cost = max(50, fallen.fee_paid_gp * 2)
    if outside_party_gold(session) < cost:
        return [f"Retainer resurrection costs {cost}gp."]
    paid, payment_log = spend_outside_party_gold(session, cost, label=f"{fallen.name} resurrection")
    if not paid:
        return payment_log or ["Could not pay for retainer resurrection."]
    fallen.life = fallen.max_life
    fallen.fanatical = True
    return payment_log + [
        f"{fallen.name} is resurrected automatically and becomes fanatically loyal (never tests morale)."
    ]


def hireling_morale_target(session: SessionState, hireling: HirelingState, catalog: dict[str, Any] | None = None) -> int:
    if hireling.fanatical:
        return 99
    catalog = catalog or load_hirelings_catalog()
    row = retainer_definition(catalog, hireling.retainer_type) or {}
    base = int(catalog.get("morale_success", 4))
    if front_rank_has_commanding_presence(session.party) or any(
        has_skill(member, "commanding_presence") for member in session.party if member.current_life > 0
    ):
        base = int(catalog.get("morale_success_commanding_presence", 3))
    if session.professional_buffs.get("storyteller_morale") and not hireling.morale_storyteller_used:
        patron_id = session.professional_buffs.get("storyteller_patron_id")
        patron = (
            next((member for member in session.party if member.character_id == patron_id), None)
            if patron_id
            else None
        )
        if patron is not None and patron.current_life > 0:
            base -= 1
            hireling.morale_storyteller_used = True
    base -= int(row.get("morale_mod", 0))
    if hireling.treasure_share_paid:
        base -= int(catalog.get("treasure_share_morale_bonus", 1))
    return max(1, base)


def bodyguard_for_protectee(session: SessionState, protectee_id: str) -> HirelingState | None:
    protectee = next((member for member in session.party if member.character_id == protectee_id), None)
    if protectee is None:
        return None
    for hireling in living_hirelings(session):
        if hireling.retainer_type != "bodyguard":
            continue
        if hireling.assigned_character_id != protectee_id:
            continue
        if _adjacent_marching_orders(hireling.marching_order, protectee.marching_order):
            return hireling
    return None


def _hireling_by_id(session: SessionState, hireling_id: str | None) -> HirelingState | None:
    if not hireling_id:
        return None
    return next((item for item in session.hirelings or [] if item.id == hireling_id), None)


def _living_hireling_by_type(session: SessionState, retainer_type: str) -> HirelingState | None:
    return next((item for item in living_hirelings(session) if item.retainer_type == retainer_type), None)


def _adjacent_hireling_for_member(
    session: SessionState,
    member: PartyMemberState,
    retainer_type: str,
) -> HirelingState | None:
    catalog = load_hirelings_catalog()
    row = retainer_definition(catalog, retainer_type) or {}
    requires_assignment = str(row.get("assignment", "none")) in {"cleric", "protectee", "gear_owner"}
    for hireling in living_hirelings(session):
        if hireling.retainer_type != retainer_type:
            continue
        if requires_assignment:
            if hireling.assigned_character_id != member.character_id:
                continue
        elif hireling.assigned_character_id and hireling.assigned_character_id != member.character_id:
            continue
        if _adjacent_marching_orders(hireling.marching_order, member.marching_order):
            return hireling
    return None


def _ability_used(hireling: HirelingState, key: str) -> bool:
    return int(hireling.uses_spent.get(key, 0)) > 0


def _mark_ability_used(hireling: HirelingState, key: str) -> None:
    hireling.uses_spent[key] = int(hireling.uses_spent.get(key, 0)) + 1


def hireling_lantern_active(session: SessionState) -> bool:
    return any(
        hireling.lantern_lit and hireling.life > 0
        for hireling in session.hirelings or []
    )


def handle_hireling_removed(hireling: HirelingState, log: list[str]) -> None:
    if hireling.retainer_type == "lantern_bearer" and hireling.lantern_lit:
        hireling.lantern_lit = False
        log.append(f"{hireling.name} drops the party lantern; it shatters on the stones.")
    if hireling.retainer_type == "porter" and (hireling.cargo_gp or hireling.cargo_items):
        if hireling.cargo_gp:
            log.append(f"{hireling.name} drops {hireling.cargo_gp}gp of treasure in the scramble.")
            hireling.cargo_gp = 0
        if hireling.cargo_items:
            dropped = ", ".join(hireling.cargo_items)
            log.append(f"{hireling.name} drops {dropped}.")
            hireling.cargo_items = []
    if hireling.retainer_type == "spear_carrier" and hireling.carried_gear:
        log.append(f"{hireling.name} drops {hireling.carried_gear}.")
        hireling.carried_gear = None


def apply_hireling_damage(
    hireling: HirelingState,
    damage: int,
    log: list[str],
    *,
    session: SessionState | None = None,
    show_rolls: bool = True,
) -> None:
    if damage <= 0:
        return
    hireling.life = max(0, hireling.life - damage)
    log.append(f"Effect: {hireling.name} takes {damage} Life (now {hireling.life}/{hireling.max_life}).")
    if hireling.life <= 0:
        log.append(f"{hireling.name} is slain.")
        handle_hireling_removed(hireling, log)
        if session is not None:
            log.extend(
                check_hireling_morale_after_casualty(
                    session,
                    reason=f"{hireling.name} fell",
                    show_rolls=show_rolls,
                )
            )


def check_hireling_morale_after_casualty(session: SessionState, *, reason: str, show_rolls: bool = True) -> list[str]:
    log: list[str] = []
    catalog = load_hirelings_catalog()
    remaining: list[HirelingState] = []
    for hireling in list(session.hirelings or []):
        if hireling.life <= 0:
            continue
        if hireling.fanatical:
            remaining.append(hireling)
            continue
        target = hireling_morale_target(session, hireling, catalog)
        roll = roll_d6()
        if show_rolls:
            log.append(f"{hireling.name} morale after {reason}: d6 = {roll} (need {target}+).")
        if roll >= target:
            log.append(f"{hireling.name} holds steady.")
            remaining.append(hireling)
            continue
        log.append(f"{hireling.name} flees into the darkness and is never seen again.")
        handle_hireling_removed(hireling, log)
    session.hirelings = remaining + [item for item in session.hirelings or [] if item.life <= 0]
    return log


def hireling_attack_modifier(hireling: HirelingState, enemy: EnemyState, catalog: dict[str, Any] | None = None) -> int:
    catalog = catalog or load_hirelings_catalog()
    row = retainer_definition(catalog, hireling.retainer_type) or {}
    bonus = int(row.get("attack_mod", 0))
    if hireling.retainer_type == "rat_exterminator" and _is_rat(enemy):
        return bonus
    return bonus


def hireling_defense_modifier(hireling: HirelingState, enemy: EnemyState | None, catalog: dict[str, Any] | None = None) -> int:
    catalog = catalog or load_hirelings_catalog()
    row = retainer_definition(catalog, hireling.retainer_type) or {}
    bonus = int(row.get("defense_mod", 0))
    if hireling.retainer_type == "rat_exterminator" and enemy is not None and _is_rat(enemy):
        bonus += int(row.get("vs_rats_defense", 2))
    return bonus


def _is_rat(enemy: EnemyState) -> bool:
    name = enemy.name.lower()
    tags = {tag.lower() for tag in enemy.tags}
    return "rat" in name or "rat" in tags or enemy.category == "vermin" and "rat" in name


def apply_hireling_combat_round(
    session: SessionState,
    enemies: list[EnemyState],
    *,
    show_rolls: bool = True,
) -> list[str]:
    catalog = load_hirelings_catalog()
    log: list[str] = []
    living_enemies = [enemy for enemy in enemies if enemy.life > 0]
    if not living_enemies:
        return log
    for hireling in living_hirelings(session):
        if hireling.retainer_type == "spear_carrier" and not hireling.carried_gear:
            sidearm = hireling.equipped_weapon
            if not sidearm or retainer_gear_violation("spear_carrier_sidearm", sidearm):
                log.append(f"{hireling.name} cannot fight without a slashing hand weapon.")
                continue
        target = living_enemies[0]
        if hireling.retainer_type == "rat_exterminator":
            rat_target = next((enemy for enemy in living_enemies if _is_rat(enemy)), None)
            if rat_target is not None:
                target = rat_target
        row = retainer_definition(catalog, hireling.retainer_type) or {}
        if hireling.retainer_type == "rat_exterminator" and _is_rat(target):
            rats_killed = roll_d6()
            if show_rolls:
                log.append(f"{hireling.name} exterminates d6 = {rats_killed} rats.")
            for _ in range(rats_killed):
                if not living_enemies:
                    break
                victim = living_enemies[0]
                victim.life = 0
                log.append(f"{victim.name} is slain.")
                living_enemies = [enemy for enemy in enemies if enemy.life > 0]
            continue
        attack_total, attack_rolls = roll_exploding_d6()
        attack_mod = hireling_attack_modifier(hireling, target, catalog)
        final_attack = attack_total + attack_mod
        if show_rolls:
            log.append(
                f"{hireling.name} attacks {target.name}: "
                f"{' + '.join(str(value) for value in attack_rolls)} + {attack_mod} = {final_attack} vs L{target.level}."
            )
        if attack_rolls[0] != 1 and final_attack >= target.level:
            target.life = max(0, target.life - 1)
            log.append(f"{hireling.name} hits {target.name} for 1 Life.")
            if target.life <= 0:
                log.append(f"{target.name} is defeated.")
                living_enemies = [enemy for enemy in enemies if enemy.life > 0]
        else:
            log.append(f"{hireling.name} misses {target.name}.")
    return log


def resolve_hireling_defense(
    hireling: HirelingState,
    enemy: EnemyState,
    *,
    show_rolls: bool = True,
) -> tuple[bool, list[str]]:
    log: list[str] = []
    total, rolls = roll_exploding_d6()
    modifier = hireling_defense_modifier(hireling, enemy)
    final = total + modifier
    if show_rolls:
        log.append(
            f"{hireling.name} defends vs {enemy.name}: "
            f"{' + '.join(str(value) for value in rolls)} + {modifier} = {final} vs L{enemy.level}."
        )
    passed = rolls[0] != 1 and final > enemy.level
    if passed:
        log.append(f"{hireling.name} holds against {enemy.name}.")
    else:
        log.append(f"{hireling.name} is hit by {enemy.name}.")
    return passed, log


def use_professional_service(
    session: SessionState,
    professional_id: str,
    *,
    character_id: str | None = None,
    item_name: str | None = None,
    catalog: dict[str, Any] | None = None,
) -> list[str]:
    catalog = catalog or load_hirelings_catalog()
    if not session.camped_outside:
        return ["Use professional services while camped outside the dungeon."]
    if not party_expert_trained(session.party):
        return ["Expert tier training is required to hire professionals."]
    max_uses = int(catalog.get("max_professional_services_per_camp", 3))
    if int(session.professional_services_used or 0) >= max_uses:
        return [f"The party has already used {max_uses} professional services this camp."]
    row = professional_definition(catalog, professional_id)
    if row is None:
        return ["Choose a professional service from the catalog."]
    if str(row.get("id")) == "alchemist":
        return ["Use Commission Alchemist to choose a potion and pay material costs."]
    fee = int(row.get("fee_gp", 0))
    if outside_party_gold(session) < fee:
        return [f"{row['name']} costs {fee}gp."]
    key = str(row["id"])
    if key == "confessor":
        member = _pick_member(session, character_id)
        if member is None:
            return ["Choose a hero for the Confessor."]
    elif key == "fortune_teller":
        member = _pick_member(session, character_id)
        if member is None:
            return ["Choose a hero for the Fortune-Teller (barbarians forbidden)."]
        if member.class_id.lower() == "barbarian":
            return ["Barbarians will not consult the Fortune-Teller."]
    elif key == "poison_expert":
        from .poison_expert import member_has_active_poison_source, rogue_meets_poison_expert_requirement

        member = _pick_member(session, character_id)
        if member is None:
            return ["Choose the rogue who hires the Poison Expert."]
        if not rogue_meets_poison_expert_requirement(member):
            return ["Poison Expert requires a rogue of Level 5 or higher."]
        if member_has_active_poison_source(member):
            return [f"{member.name} already has poison ready; only one dose at a time."]
        if not item_name:
            return ["Choose a slashing weapon or single arrow to coat with poison."]
        if item_name not in member.inventory:
            return ["Choose an item from that rogue's inventory."]
        lower = item_name.lower()
        arrow_ok = "arrow" in lower
        slash_ok = any(
            token in lower for token in ("sword", "scimitar", "dagger", "hand weapon", "light weapon", "slashing")
        )
        if not arrow_ok and not slash_ok:
            return ["Coat a slashing hand weapon or a single arrow."]
    elif key == "silversmith":
        member = _pick_member(session, character_id)
        if member is None:
            return ["Choose a hero for the Silversmith."]
        if not item_name:
            return ["Choose a slashing weapon or arrows to silver-coat."]
        if item_name not in member.inventory:
            return ["Choose an item from that hero's inventory."]
        lower = item_name.lower()
        arrow_ok = "arrow" in lower
        slash_ok = any(
            token in lower for token in ("sword", "scimitar", "dagger", "hand weapon", "light weapon", "slashing")
        )
        if not arrow_ok and not slash_ok:
            return ["Silver-coat a slashing weapon or a quiver of arrows."]
    paid, payment_log = spend_outside_party_gold(session, fee, label=row["name"])
    if not paid:
        return payment_log or [f"Could not pay {fee}gp for {row['name']}."]
    session.professional_services_used = int(session.professional_services_used or 0) + 1
    buffs = dict(session.professional_buffs or {})
    log = list(payment_log)
    if key == "confessor":
        from .madness import heal_madness

        member = _pick_member(session, character_id)
        healed = heal_madness(member, 1)
        if healed:
            log.append(f"Confessor removes 1 Madness from {member.name}.")
        else:
            log.append(f"{member.name} has no Madness to remove.")
    elif key == "bladesmith":
        buffs["bladesmith_attack"] = True
        log.append("Bladesmith: +1 Attack with main slashing weapon in the first combat of the next foray.")
    elif key == "herbalist":
        buffs["herbalist_saves"] = True
        log.append("Herbalist: party gains +1 saves vs poison and disease next foray.")
    elif key == "sage":
        buffs["sage_clue_double"] = True
        log.append("Sage: the first Clue spent next foray counts as two.")
    elif key == "shieldmaker":
        buffs["shieldmaker_reroll"] = True
        log.append("Shieldmaker: reroll the first failed shield Defense next foray.")
    elif key == "storyteller":
        member = _pick_member(session, character_id)
        if member is None:
            return ["Choose which hero patronizes the storyteller."]
        buffs["storyteller_morale"] = True
        buffs["storyteller_patron_id"] = member.character_id
        log.append(
            f"Storyteller: +1 on the first retainer morale roll next foray while {member.name} lives."
        )
    elif key == "tailor":
        buffs["tailor_reaction"] = True
        log.append("Tailor: alter the first reaction roll ±1 if it would change a bribe next foray.")
    elif key == "silversmith":
        member = _pick_member(session, character_id)
        coat_log = _apply_silversmith_coating_to_member(member, item_name or "")
        if coat_log:
            log.extend(coat_log)
    elif key == "fortune_teller":
        member = _pick_member(session, character_id)
        from .dice import roll_d8

        rolls = [roll_d8(), roll_d8()]
        buffs[f"fortune_{member.character_id}"] = rolls
        log.append(f"Fortune-Teller rolls 2d8 = {rolls[0]} and {rolls[1]} for {member.name} (bank one for a reroll next foray).")
    elif key == "poison_expert":
        member = _pick_member(session, character_id)
        from .poison_expert import apply_poison_expert_coating_inline

        coat_log = apply_poison_expert_coating_inline(session, member, item_name=item_name)
        log.extend(coat_log)
    else:
        log.append(f"{row['name']} service recorded for the next foray.")
    session.professional_buffs = buffs
    log.append(f"Professional services used this camp: {session.professional_services_used}/{max_uses}.")
    return log


def _pick_member(session: SessionState, character_id: str | None) -> PartyMemberState | None:
    if character_id:
        return next((member for member in session.party if member.character_id == character_id), None)
    living = [member for member in session.party if member.current_life > 0]
    return living[0] if living else None


def spear_carrier_for_owner(session: SessionState, owner_id: str) -> HirelingState | None:
    owner = next((member for member in session.party if member.character_id == owner_id), None)
    if owner is None:
        return None
    for hireling in living_hirelings(session):
        if hireling.retainer_type != "spear_carrier":
            continue
        if hireling.assigned_character_id != owner_id:
            continue
        if _adjacent_marching_orders(hireling.marching_order, owner.marching_order):
            return hireling
    return None


def try_acolyte_preserve_blessing(
    session: SessionState,
    cleric: PartyMemberState,
    *,
    show_rolls: bool = True,
    hireling: HirelingState | None = None,
) -> tuple[bool, list[str]]:
    log: list[str] = []
    if hireling is None:
        hireling = _adjacent_hireling_for_member(session, cleric, "acolyte")
    if hireling is None or _ability_used(hireling, "acolyte_blessing"):
        return False, log
    _mark_ability_used(hireling, "acolyte_blessing")
    roll = roll_d6()
    total = roll + cleric.level
    if show_rolls:
        log.append(
            f"{hireling.name} aids {cleric.name}'s Blessing: d6+L = {roll}+{cleric.level} = {total} (need 7+)."
        )
    if total >= 7:
        log.append(f"{hireling.name} preserves Blessing — it is not expended.")
        return True, log
    log.append(f"{hireling.name} fails to preserve Blessing.")
    return False, log


def use_hireling_ability(
    session: SessionState,
    hireling_id: str | None,
    ability: str,
    *,
    character_id: str | None = None,
    item_name: str | None = None,
    gold_amount: int | None = None,
    show_rolls: bool = True,
) -> list[str]:
    if session.mode != "exploration":
        return ["Use retainer abilities during exploration."]
    hireling = _hireling_by_id(session, hireling_id)
    if hireling is None or hireling.life <= 0:
        return ["Choose a living retainer."]
    if ability == "minstrel_song":
        if hireling.retainer_type != "minstrel":
            return ["Only a minstrel can perform this song."]
        if _ability_used(hireling, "minstrel_song"):
            return ["The minstrel already performed this adventure."]
        _mark_ability_used(hireling, "minstrel_song")
        from .madness import heal_madness

        log = [f"{hireling.name} sings away the party's woes."]
        for member in session.party:
            if member.current_life <= 0:
                continue
            healed = heal_madness(member, 1)
            if healed:
                log.append(f"{member.name} loses 1 Madness.")
        return log
    if ability == "surgeon_heal":
        if hireling.retainer_type != "surgeon":
            return ["Only a surgeon can perform field surgery."]
        if _ability_used(hireling, "surgeon_heal"):
            return ["The surgeon already tended the party this adventure."]
        _mark_ability_used(hireling, "surgeon_heal")
        log = [f"{hireling.name} stitches wounds beyond bandages (+2 Life each)."]
        for member in session.party:
            if member.current_life <= 0:
                continue
            before = member.current_life
            member.current_life = min(member.max_life, member.current_life + 2)
            gained = member.current_life - before
            if gained:
                log.append(f"{member.name} recovers {gained} Life.")
        return log
    if ability in {"guide_reroll_room", "guide_reroll_search", "guide_reroll_wandering"}:
        if hireling.retainer_type != "dungeon_guide":
            return ["Only a dungeon guide can reroll tables."]
        if _ability_used(hireling, "guide_reroll"):
            return ["The dungeon guide already spent their reroll this adventure."]
        kind = ability.removeprefix("guide_reroll_")
        return [f"GUIDE_REROLL:{kind}"]
    if ability == "porter_load_gold":
        if hireling.retainer_type != "porter":
            return ["Only a porter can carry extra treasure."]
        amount = int(gold_amount or 0)
        if amount <= 0:
            return ["Choose how much gold the porter should carry (max 400gp total)."]
        if hireling.cargo_gp + amount > 400:
            return ["A porter carries at most 400gp of treasure."]
        member = _pick_member(session, character_id)
        if member is None or member.gold < amount:
            return ["Choose a hero carrying enough gold for the porter."]
        member.gold -= amount
        hireling.cargo_gp += amount
        return [f"{hireling.name} takes {amount}gp from {member.name} (now carrying {hireling.cargo_gp}gp)."]
    if ability == "porter_load_item":
        if hireling.retainer_type != "porter":
            return ["Only a porter can carry bulky objects."]
        if len(hireling.cargo_items) >= 2:
            return ["The porter already carries two bulky objects."]
        member = _pick_member(session, character_id)
        if member is None or not item_name or item_name not in member.inventory:
            return ["Choose a hero and bulky item for the porter to carry."]
        if not is_bulky_carriable_item(item_name):
            return [f"{item_name} is too small to count as a bulky object for the porter."]
        member.inventory.remove(item_name)
        hireling.cargo_items.append(item_name)
        return [f"{hireling.name} takes {item_name} from {member.name}."]
    if ability == "spear_hand_gear":
        if hireling.retainer_type != "spear_carrier":
            return ["Only a spear carrier can hold gear."]
        owner = next(
            (member for member in session.party if member.character_id == hireling.assigned_character_id),
            None,
        )
        if owner is None:
            return ["Assign the spear carrier to a hero first."]
        if hireling.carried_gear:
            return [f"{hireling.name} already carries {hireling.carried_gear}."]
        if not item_name or item_name not in owner.inventory:
            return ["Choose a shield or weapon from the assigned hero's inventory."]
        violation = retainer_gear_violation("spear_carrier", item_name)
        if violation:
            return [violation]
        lower = item_name.lower()
        if "shield" not in lower and "weapon" not in lower:
            return ["Spear carriers carry shields or weapons only."]
        owner.inventory.remove(item_name)
        hireling.carried_gear = item_name
        return [f"{hireling.name} takes {item_name} from {owner.name}."]
    if ability == "spear_return_gear":
        if hireling.retainer_type != "spear_carrier":
            return ["Only a spear carrier can return gear."]
        if not hireling.carried_gear:
            return ["The spear carrier carries nothing to return."]
        owner = next(
            (member for member in session.party if member.character_id == hireling.assigned_character_id),
            None,
        )
        if owner is None:
            return ["Assign the spear carrier to a hero first."]
        gear = hireling.carried_gear
        hireling.carried_gear = None
        owner.inventory.append(gear)
        return [f"{hireling.name} returns {gear} to {owner.name}."]
    if ability in {"equip_retainer_weapon", "equip_retainer_armor"}:
        if not item_name:
            return ["Choose an item to equip on the retainer."]
        member = _pick_member(session, character_id)
        if member is None or item_name not in member.inventory:
            return ["Choose a hero carrying the item to hand to the retainer."]
        slot = "weapon" if ability == "equip_retainer_weapon" else "armor"
        violation = retainer_gear_violation(hireling.retainer_type, item_name)
        if violation:
            return [violation]
        if slot == "weapon":
            if "weapon" not in item_name.lower() and not any(
                token in item_name.lower() for token in ("sword", "dagger", "axe", "mace", "spear", "scimitar")
            ):
                return ["Choose a weapon for the retainer."]
            hireling.equipped_weapon = item_name
        else:
            if "armor" not in item_name.lower() and "shield" not in item_name.lower():
                return ["Choose armor or a shield for the retainer."]
            hireling.equipped_armor = item_name
        member.inventory.remove(item_name)
        return [f"{member.name} equips {hireling.name} with {item_name}."]
    return ["Unknown retainer ability."]


def _apply_silversmith_coating_to_member(member: PartyMemberState, item_name: str) -> list[str]:
    lower = item_name.lower()
    if "arrow" in lower:
        member.inventory = [item for item in member.inventory if item != item_name]
        member.inventory.extend([f"Arrow {index + 1} (silvered)" for index in range(5)])
        return [f"Silversmith coats 5 arrows for {member.name} (+1 vs lycanthropes)."]
    if any(token in lower for token in ("sword", "scimitar", "dagger", "hand weapon", "light weapon", "slashing")):
        from .weapon_finishes import apply_weapon_finish

        coated = apply_weapon_finish(item_name, "silvered")
        member.inventory = [coated if item == item_name else item for item in member.inventory]
        return [f"Silversmith silver-coats {item_name} for {member.name} (+1 vs lycanthropes)."]
    return ["Silver-coat a slashing weapon or a quiver of arrows."]


def apply_silversmith_coating(
    session: SessionState,
    *,
    item_name: str | None,
    character_id: str | None = None,
) -> list[str]:
    if not session.professional_buffs.get("silversmith_pending"):
        return ["No silversmith coating is pending."]
    member = _pick_member(session, character_id)
    if member is None:
        return ["Choose a hero to silver-coat gear."]
    if not item_name or item_name not in member.inventory:
        return ["Choose a slashing weapon or arrows from that hero's inventory."]
    note = _apply_silversmith_coating_to_member(member, item_name)
    if note[0].startswith("Silver-coat"):
        return note
    buffs = dict(session.professional_buffs)
    buffs.pop("silversmith_pending", None)
    session.professional_buffs = buffs
    return note


def use_fortune_reroll(
    session: SessionState,
    character_id: str | None,
    *,
    roll_value: int | None,
) -> list[str]:
    if not character_id:
        return ["Choose the hero who consulted the Fortune-Teller."]
    key = f"fortune_{character_id}"
    rolls = session.professional_buffs.get(key)
    if not isinstance(rolls, list) or len(rolls) != 2:
        return ["No Fortune-Teller rolls are banked for this hero."]
    if roll_value not in rolls:
        return [f"Choose one of the banked rolls: {rolls[0]} or {rolls[1]}."]
    buffs = dict(session.professional_buffs)
    buffs.pop(key, None)
    buffs[f"fortune_reroll_{character_id}"] = roll_value
    session.professional_buffs = buffs
    member = _pick_member(session, character_id)
    name = member.name if member else "the hero"
    return [f"{name} banks Fortune-Teller reroll value {roll_value} for the next d8 this adventure."]


def professional_attack_bonus(session: SessionState, member: PartyMemberState, weapon_item: str | None) -> int:
    if not session.professional_buffs.get("bladesmith_attack"):
        return 0
    if not weapon_item:
        return 0
    from .weapons import _parse_weapon_item

    profile = _parse_weapon_item(weapon_item)
    if profile is None or not profile.slashing or profile.kind != "melee":
        return 0
    return 1


def consume_bladesmith_buff(session: SessionState) -> None:
    buffs = dict(session.professional_buffs or {})
    if buffs.pop("bladesmith_attack", None):
        session.professional_buffs = buffs


def professional_save_bonus(session: SessionState, *, poison: bool = False, disease: bool = False) -> int:
    if not session.professional_buffs.get("herbalist_saves"):
        return 0
    if poison or disease:
        return 1
    return 0


def sage_clue_discount(session: SessionState, amount: int) -> int:
    if amount <= 0 or not session.professional_buffs.get("sage_clue_double"):
        return amount
    buffs = dict(session.professional_buffs)
    buffs.pop("sage_clue_double", None)
    session.professional_buffs = buffs
    return max(1, amount - 1)


def tailor_reaction_adjust_available(session: SessionState) -> bool:
    return bool(session.professional_buffs.get("tailor_reaction"))


def consume_tailor_reaction_buff(session: SessionState) -> None:
    buffs = dict(session.professional_buffs or {})
    if buffs.pop("tailor_reaction", None):
        session.professional_buffs = buffs


def consume_fortune_d8_reroll(session: SessionState, character_id: str) -> tuple[int | None, str | None]:
    key = f"fortune_reroll_{character_id}"
    value = session.professional_buffs.get(key)
    if value is None:
        return None, None
    buffs = dict(session.professional_buffs)
    buffs.pop(key, None)
    session.professional_buffs = buffs
    member = _pick_member(session, character_id)
    name = member.name if member else "the hero"
    roll_value = int(value)
    return roll_value, f"{name} uses Fortune-Teller reroll: banked d8 = {roll_value}."


def apply_tailor_to_reaction_roll(
    session: SessionState,
    roll: int,
    *,
    source,
    living_enemies,
    table_roller,
) -> tuple[int, list[str]]:
    from .reactions import (
        apply_reaction_overlays,
        is_bribe_reaction,
        lookup_reaction_row,
        normalize_reaction_row,
    )

    if not tailor_reaction_adjust_available(session):
        return roll, []

    def row_for(base_roll: int) -> dict:
        if source.inline_rows:
            row = lookup_reaction_row(source.inline_rows, base_roll)
        else:
            table_name = source.table_name or "default_reaction_table"
            row = table_roller.roll_reaction(table_name, base_roll)
        if row is None:
            row = table_roller.roll_reaction("default_reaction_table", base_roll)
        if row is None:
            row = {"key": "fight"}
        row = apply_reaction_overlays(row, living_enemies, base_roll)
        return normalize_reaction_row(row)

    base_bribe = is_bribe_reaction(row_for(roll).get("key"))
    changes: list[tuple[int, int, bool]] = []
    for delta in (-1, 1):
        adjusted = max(1, min(6, roll + delta))
        if adjusted == roll:
            continue
        adj_bribe = is_bribe_reaction(row_for(adjusted).get("key"))
        if adj_bribe != base_bribe:
            changes.append((delta, adjusted, adj_bribe))
    if not changes:
        return roll, []

    if len(changes) == 1:
        delta, adjusted, _ = changes[0]
    else:
        toward_bribe = next((entry for entry in changes if entry[2]), changes[0])
        delta, adjusted, _ = toward_bribe

    consume_tailor_reaction_buff(session)
    direction = f"+{delta}" if delta > 0 else str(delta)
    return adjusted, [f"Tailor adjusts the reaction roll {direction} ({roll} -> {adjusted}) to change the bribe outcome."]


def spear_carrier_has_shield(session: SessionState, owner_id: str) -> bool:
    from .inventory import is_carried_shield

    carrier = spear_carrier_for_owner(session, owner_id)
    return bool(carrier and carrier.carried_gear and is_carried_shield(carrier.carried_gear))


def can_ready_spear_shield(session: SessionState, owner_id: str) -> bool:
    if not spear_carrier_has_shield(session, owner_id):
        return False
    return owner_id not in (session.spear_shield_readied or [])


def shieldmaker_reroll_available(session: SessionState) -> bool:
    return bool(session.professional_buffs.get("shieldmaker_reroll"))


def consume_shieldmaker_buff(session: SessionState) -> None:
    buffs = dict(session.professional_buffs or {})
    if buffs.pop("shieldmaker_reroll", None):
        session.professional_buffs = buffs


def reset_hirelings_for_new_foray(session: SessionState) -> None:
    for hireling in session.hirelings or []:
        hireling.treasure_share_paid = False
        hireling.morale_storyteller_used = False
        hireling.uses_spent = {}
    session.professional_services_used = 0


def return_porter_cargo(session: SessionState) -> list[str]:
    log: list[str] = []
    lead = next(
        (member for member in sorted(session.party, key=lambda item: item.marching_order) if member.current_life > 0),
        None,
    )
    if lead is None:
        return log
    for hireling in session.hirelings or []:
        if hireling.retainer_type != "porter":
            continue
        if hireling.cargo_gp:
            lead.gold += hireling.cargo_gp
            log.append(f"{hireling.name} returns {hireling.cargo_gp}gp to {lead.name}.")
            hireling.cargo_gp = 0
        if hireling.cargo_items:
            items = list(hireling.cargo_items)
            for item in items:
                lead.inventory.append(item)
            log.append(f"{hireling.name} returns {', '.join(items)} to {lead.name}.")
            hireling.cargo_items = []
    return log


def clear_hirelings_on_dungeon_exit(session: SessionState) -> None:
    from .alchemist_potions import resolve_alchemist_on_dungeon_exit

    session.log.extend(resolve_alchemist_on_dungeon_exit(session))
    cargo_log = return_porter_cargo(session)
    session.log.extend(cargo_log)
    if session.hirelings:
        session.log.append("Retainers return home when the party leaves the dungeon.")
    session.hirelings = []
    session.professional_buffs = {}
    session.professional_services_used = 0
    from .courtship_professional_skills import clear_professional_skill_uses

    clear_professional_skill_uses(session)


def hirelings_table_rows(catalog: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for index, retainer in enumerate(catalog.get("retainers", []), start=1):
        rows.append(
            {
                "roll": str(index),
                "kind": "Retainer",
                "name": str(retainer.get("name", "")),
                "fee_gp": str(retainer.get("fee_gp", "")),
                "life": str(retainer.get("life", "")),
                "result": str(retainer.get("summary", "")),
                "source_page": "27",
            }
        )
    for index, professional in enumerate(catalog.get("professionals", []), start=1):
        rows.append(
            {
                "roll": f"P{index}",
                "kind": "Professional",
                "name": str(professional.get("name", "")),
                "fee_gp": str(professional.get("fee_gp", "")),
                "life": "—",
                "result": str(professional.get("summary", "")),
                "source_page": "27",
            }
        )
    for index, potion in enumerate(catalog.get("alchemist_potions", []), start=1):
        difficulty = int(potion.get("difficulty", 0))
        diff_label = "auto" if difficulty <= 0 else str(difficulty)
        rows.append(
            {
                "roll": f"A{index}",
                "kind": "Alchemist potion",
                "name": str(potion.get("name", "")),
                "fee_gp": str(int(potion.get("material_gp", 0)) + 50),
                "life": diff_label,
                "result": str(potion.get("summary", "")),
                "source_page": "31",
            }
        )
    return rows
