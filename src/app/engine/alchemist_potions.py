from __future__ import annotations

from typing import Any

from ..schemas import AlchemistOrderState, EnemyState, PartyMemberState, SessionState
from .dice import roll_d6
from .equipment_effects import is_vampire, is_werecreature
from .hirelings import load_hirelings_catalog, outside_party_gold, spend_outside_party_gold

ALCHEMIST_FEE_GP = 50

STATUS_DARKSIGHT = "Alchemist: Darksight"
STATUS_VIGOR = "Alchemist: Vigor"
STATUS_GARLIC = "Alchemist: Garlic Poultice"
STATUS_POWDERED_SILVER = "Alchemist: Powdered Silver"
STATUS_ELFBLOOD = "Alchemist: Elfblood Ointment"
STATUS_MINDWORTH = "Alchemist: Mindworth Extract"
STATUS_ELIXIR = "Alchemist: Elixir of Long Life"

POTION_STATUS_BY_ID: dict[str, str] = {
    "potion_of_darksight": STATUS_DARKSIGHT,
    "potion_of_vigor": STATUS_VIGOR,
    "garlic_poultice": STATUS_GARLIC,
    "powdered_silver": STATUS_POWDERED_SILVER,
    "elfblood_ointment": STATUS_ELFBLOOD,
    "mindworth_extract": STATUS_MINDWORTH,
    "elixir_of_long_life": STATUS_ELIXIR,
}


def alchemist_potion_catalog(catalog: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    catalog = catalog or load_hirelings_catalog()
    return list(catalog.get("alchemist_potions", []))


def alchemist_potion_definition(potion_id: str, catalog: dict[str, Any] | None = None) -> dict[str, Any] | None:
    return next((row for row in alchemist_potion_catalog(catalog) if str(row.get("id")) == potion_id), None)


def member_has_alchemist_status(member: PartyMemberState, status: str) -> bool:
    return any(item.strip() == status for item in member.statuses)


def commission_alchemist(
    session: SessionState,
    *,
    potion_id: str,
    character_id: str | None,
    catalog: dict[str, Any] | None = None,
    show_rolls: bool = True,
) -> list[str]:
    catalog = catalog or load_hirelings_catalog()
    if not session.camped_outside:
        return ["Commission the Alchemist while camped outside the dungeon."]
    if session.alchemist_order is not None:
        return ["An alchemist is already preparing a potion for the next adventure."]
    if not any(member.expert_trained for member in session.party if member.current_life > 0):
        return ["Expert tier training is required to hire professionals."]
    max_uses = int(catalog.get("max_professional_services_per_camp", 3))
    if int(session.professional_services_used or 0) >= max_uses:
        return [f"The party has already used {max_uses} professional services this camp."]
    row = alchemist_potion_definition(potion_id, catalog)
    if row is None:
        return ["Choose a potion from the alchemist catalog."]
    member = next((item for item in session.party if item.character_id == character_id), None)
    if member is None or member.current_life <= 0:
        return ["Choose a living hero to receive the alchemist's work."]
    material_gp = int(row.get("material_gp", 0))
    total_cost = ALCHEMIST_FEE_GP + material_gp
    if outside_party_gold(session) < total_cost:
        return [f"The Alchemist costs {ALCHEMIST_FEE_GP}gp plus {material_gp}gp materials ({total_cost}gp total)."]
    paid, payment_log = spend_outside_party_gold(
        session,
        total_cost,
        label=f"Alchemist ({row['name']})",
    )
    if not paid:
        return payment_log or ["Could not pay the alchemist."]
    session.professional_services_used = int(session.professional_services_used or 0) + 1
    session.alchemist_order = AlchemistOrderState(
        potion_id=str(row["id"]),
        potion_name=str(row["name"]),
        character_id=member.character_id,
        difficulty=int(row.get("difficulty", 0)),
        material_gp=material_gp,
    )
    log = list(payment_log)
    log.append(
        f"Alchemist begins brewing {row['name']} for {member.name} "
        f"({ALCHEMIST_FEE_GP}gp fee + {material_gp}gp materials)."
    )
    difficulty = int(row.get("difficulty", 0))
    if difficulty <= 0:
        log.append("This brew succeeds automatically when the party returns home.")
    else:
        log.append(f"On returning home, the alchemist rolls d6 (need {difficulty}+) to finish the potion.")
    log.append(f"Professional services used this camp: {session.professional_services_used}/{max_uses}.")
    return log


def resolve_alchemist_on_dungeon_exit(session: SessionState, *, show_rolls: bool = True) -> list[str]:
    order = session.alchemist_order
    if order is None:
        return []
    session.alchemist_order = None
    member = next((item for item in session.party if item.character_id == order.character_id), None)
    if member is None:
        return [f"The alchemist's {order.potion_name} brew fails — {order.character_id} is not in the party."]
    log: list[str] = [f"The alchemist delivers results for {order.potion_name} ({member.name})."]
    if order.difficulty > 0:
        roll = roll_d6()
        if show_rolls:
            log.append(f"Alchemist completion roll: d6 = {roll} (need {order.difficulty}+).")
        if roll < order.difficulty:
            log.append(f"The brew fails; {order.potion_name} is lost.")
            return log
    log.extend(_deliver_alchemist_potion(member, order.potion_id, order.potion_name))
    return log


def _deliver_alchemist_potion(member: PartyMemberState, potion_id: str, potion_name: str) -> list[str]:
    if potion_id == "potion_of_healing":
        member.inventory.append("Potion of Healing")
        return [f"{member.name} receives {potion_name}."]
    status = POTION_STATUS_BY_ID.get(potion_id)
    if status is None:
        return [f"{potion_name} is ready, but its effect is not wired yet."]
    if status not in member.statuses:
        member.statuses.append(status)
    return [f"{member.name} receives {potion_name} (active next adventure)."]


def alchemist_darkness_penalty(
    session: SessionState | None,
    member: PartyMemberState,
    party: list[PartyMemberState],
) -> int:
    if member_has_alchemist_status(member, STATUS_DARKSIGHT):
        return 0
    if session is None:
        return 0
    from .special_items import party_has_light_source

    if party_has_light_source(party, session=session):
        return 0
    return -2


def alchemist_defense_bonus(member: PartyMemberState, enemy: EnemyState | None) -> int:
    bonus = 0
    if enemy is not None and member_has_alchemist_status(member, STATUS_POWDERED_SILVER) and is_werecreature(enemy):
        bonus += 1
    if enemy is not None and member_has_alchemist_status(member, STATUS_MINDWORTH):
        name = enemy.name.lower()
        tags = {tag.lower() for tag in enemy.tags}
        if "mind screamer" in name or "psychic" in tags or "psychic" in name:
            bonus += 2
    return bonus


def alchemist_save_bonus(member: PartyMemberState, *, save_label: str = "", poison: bool = False, gas: bool = False) -> int:
    label = save_label.lower()
    bonus = 0
    if member_has_alchemist_status(member, STATUS_VIGOR) and (poison or gas or "poison" in label or "gas" in label):
        bonus += 1
    if member_has_alchemist_status(member, STATUS_MINDWORTH) and (
        "tentacled brain" in label or "tentacle" in label or "brain" in label
    ):
        bonus += 2
    return bonus


def alchemist_blocks_vampire_level_drain(member: PartyMemberState, enemy: EnemyState) -> bool:
    return member_has_alchemist_status(member, STATUS_GARLIC) and is_vampire(enemy)


def alchemist_blocks_ghoul_paralysis(member: PartyMemberState, enemy: EnemyState) -> bool:
    if not member_has_alchemist_status(member, STATUS_ELFBLOOD):
        return False
    name = enemy.name.lower()
    tags = {tag.lower() for tag in enemy.tags}
    return "ghoul" in name or "ghoul" in tags


def alchemist_immune_dark_plague(member: PartyMemberState) -> bool:
    return member_has_alchemist_status(member, STATUS_VIGOR)


def try_elixir_of_long_life(
    session: SessionState,
    member: PartyMemberState,
    log: list[str],
    *,
    show_rolls: bool = True,
) -> bool:
    if not member_has_alchemist_status(member, STATUS_ELIXIR):
        return False
    roll = roll_d6()
    total = roll + member.level
    if show_rolls:
        log.append(f"Elixir of Long Life: {member.name} rolls d6+L = {roll}+{member.level} = {total} (need 6+).")
    member.statuses = [status for status in member.statuses if status != STATUS_ELIXIR]
    if total < 6:
        log.append(f"{member.name}'s Elixir of Long Life fails to preserve life.")
        return False
    healed = roll_d6()
    member.current_life = min(member.max_life, healed)
    if show_rolls:
        log.append(f"Elixir of Long Life restores {member.current_life} Life to {member.name} (rolled {healed}).")
    else:
        log.append(f"Elixir of Long Life restores {member.current_life} Life to {member.name}.")
    return True
