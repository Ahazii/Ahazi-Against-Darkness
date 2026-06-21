from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from ..schemas import EnemyState, HirelingState, PartyMemberState, SessionState
from .dice import roll_d6, roll_exploding_d6
from .expert_skill_effects import front_rank_has_commanding_presence, has_skill

_ROOT = Path(__file__).resolve().parents[3]
_CATALOG_PATH = _ROOT / "data" / "rules" / "hirelings.json"

HIRELING_MARCHING_ORDERS = (5, 6)


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
    taken_orders = {member.marching_order for member in session.party}
    taken_orders.update(hireling.marching_order for hireling in session.hirelings or [])
    slot = next((order for order in HIRELING_MARCHING_ORDERS if order not in taken_orders), None)
    if slot is None:
        return ["No marching slots (#5–#6) are free for a retainer."]
    paid, payment_log = spend_outside_party_gold(session, fee, label=f"{row['name']} retainer fee")
    if not paid:
        return payment_log or [f"Could not pay the {fee}gp retainer fee."]
    log.extend(payment_log)
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
    valid, note = assignment_valid(hireling, session.party, catalog=catalog)
    if not valid:
        return [note]
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
        return ["Retainers use marching slots #5 or #6."]
    hireling = next((item for item in session.hirelings or [] if item.id == hireling_id), None)
    if hireling is None:
        return ["Choose a retainer to reposition."]
    occupant = next(
        (
            item
            for item in (session.hirelings or [])
            if item.marching_order == position and item.id != hireling_id
        ),
        None,
    )
    if occupant:
        occupant.marching_order = hireling.marching_order
    hireling.marching_order = position
    valid, note = assignment_valid(hireling, session.party)
    if not valid:
        return [f"Marching order updated, but assignment is invalid: {note}"]
    return [f"{hireling.name} moves to marching slot #{position}."]


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


def apply_hireling_damage(hireling: HirelingState, damage: int, log: list[str]) -> None:
    if damage <= 0:
        return
    hireling.life = max(0, hireling.life - damage)
    log.append(f"Effect: {hireling.name} takes {damage} Life (now {hireling.life}/{hireling.max_life}).")
    if hireling.life <= 0:
        log.append(f"{hireling.name} is slain.")
        handle_hireling_removed(hireling, log)


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
        buffs["storyteller_morale"] = True
        log.append("Storyteller: +1 on the first retainer morale roll next foray.")
    elif key == "tailor":
        buffs["tailor_reaction"] = True
        log.append("Tailor: alter the first reaction roll ±1 if it would change a bribe next foray.")
    elif key == "silversmith":
        buffs["silversmith_pending"] = True
        log.append("Silversmith: silver-coat a slashing weapon or 5 arrows before the next foray (apply when gearing up).")
    elif key == "fortune_teller":
        member = _pick_member(session, character_id)
        from .dice import roll_d8

        rolls = [roll_d8(), roll_d8()]
        buffs[f"fortune_{member.character_id}"] = rolls
        log.append(f"Fortune-Teller rolls 2d8 = {rolls[0]} and {rolls[1]} for {member.name} (bank one for a reroll next foray).")
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
) -> tuple[bool, list[str]]:
    log: list[str] = []
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
    return ["Unknown retainer ability."]


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
    lower = item_name.lower()
    if "arrow" in lower:
        member.inventory = [item for item in member.inventory if item != item_name]
        member.inventory.extend([f"Arrow {index + 1} (silvered)" for index in range(5)])
        note = f"Silversmith coats 5 arrows for {member.name} (+1 vs lycanthropes)."
    elif any(token in lower for token in ("sword", "scimitar", "dagger", "hand weapon", "light weapon", "slashing")):
        from .weapon_finishes import apply_weapon_finish

        coated = apply_weapon_finish(item_name, "silvered")
        member.inventory = [coated if item == item_name else item for item in member.inventory]
        note = f"Silversmith silver-coats {item_name} for {member.name} (+1 vs lycanthropes)."
    else:
        return ["Silver-coat a slashing weapon or a quiver of arrows."]
    buffs = dict(session.professional_buffs)
    buffs.pop("silversmith_pending", None)
    session.professional_buffs = buffs
    return [note]


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


def clear_hirelings_on_dungeon_exit(session: SessionState) -> None:
    if session.hirelings:
        session.log.append("Retainers return home when the party leaves the dungeon.")
    session.hirelings = []
    session.professional_buffs = {}
    session.professional_services_used = 0


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
    return rows
