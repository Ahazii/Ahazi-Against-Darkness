from __future__ import annotations

from ..schemas import PartyMemberState, SessionState


def is_firearm_item(item: str) -> bool:
    lower = item.lower()
    return "handgun" in lower or "black powder rifle" in lower


def firearm_attack_bonus(item: str) -> int:
    lower = item.lower()
    if "black powder rifle" in lower:
        return 4
    if "handgun" in lower:
        return 2
    return 0


def can_member_use_firearm(member: PartyMemberState) -> bool:
    from .equipment_shop import can_class_use_item

    return can_class_use_item(member.class_id, {"category": "firearm", "magic": False})[0]


def firearm_broken(session: SessionState, member: PartyMemberState) -> bool:
    return bool(session.firearm_broken.get(member.character_id))


def firearm_reloading(session: SessionState, member: PartyMemberState) -> bool:
    return int(session.firearm_reload_turns.get(member.character_id, 0)) > 0


def can_fire_firearm(session: SessionState, member: PartyMemberState, item: str) -> tuple[bool, str]:
    if not is_firearm_item(item):
        return True, ""
    if firearm_broken(session, member):
        return False, f"{member.name}'s {item} is broken for this adventure."
    remaining = int(session.firearm_reload_turns.get(member.character_id, 0))
    if remaining > 0:
        return False, f"{member.name} is reloading ({remaining} round(s) remaining)."
    return True, ""


def start_firearm_reload(session: SessionState, member: PartyMemberState) -> None:
    session.firearm_reload_turns[member.character_id] = 2


def tick_firearm_reload(session: SessionState, member: PartyMemberState) -> list[str]:
    remaining = int(session.firearm_reload_turns.get(member.character_id, 0))
    if remaining <= 0:
        return []
    remaining -= 1
    if remaining <= 0:
        session.firearm_reload_turns.pop(member.character_id, None)
        return [f"{member.name} finishes reloading."]
    session.firearm_reload_turns[member.character_id] = remaining
    return [f"{member.name} reloads ({remaining} round(s) remaining)."]


def misfire_firearm(session: SessionState, member: PartyMemberState, item: str) -> list[str]:
    session.firearm_broken[member.character_id] = True
    member.current_life = max(0, member.current_life - 1)
    return [
        f"{member.name}'s {item} misfires! {member.name} takes 1 Life "
        f"({member.current_life}/{member.max_life}) and the firearm is broken for this adventure."
    ]


def gnome_repair_firearm(
    session: SessionState,
    gnome: PartyMemberState,
    target: PartyMemberState,
) -> list[str]:
    from .class_abilities import spend_gnome_gadgets

    if gnome.class_id.lower() != "gnome":
        return ["Only a gnome may repair a broken firearm with gadgets."]
    firearm = next((item for item in target.inventory if is_firearm_item(item)), None)
    if firearm is None:
        return [f"{target.name} does not carry a firearm."]
    if not firearm_broken(session, target):
        return [f"{target.name}'s {firearm} is not broken."]
    if not spend_gnome_gadgets(session, gnome, 1):
        return [f"{gnome.name} has no gadget points remaining."]
    session.firearm_broken.pop(target.character_id, None)
    session.firearm_reload_turns.pop(target.character_id, None)
    return [f"{gnome.name} repairs {target.name}'s {firearm} with a gadget."]
