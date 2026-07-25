from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from ..schemas import (
    EnemyState,
    GremlinProtectedItemState,
    PartyMemberState,
    PendingGremlinEventState,
    SessionState,
)
from .dice import roll_d6
from .equipment_effects import scroll_protected_by_tube
from .item_containers import (
    bag_for_inventory_index,
    contained_loss_suffix,
    is_bag_of_carrying,
    item_container,
    remove_inventory_item_with_contents,
)
from .magic_armor import is_magic_armor
from .magic_items import is_charged_magic_item
from .magic_weapons import is_magic_weapon
from .star_object_curse import (
    is_star_object_item,
    reconcile_star_object_carrier,
    remove_star_object,
    star_object_carrier,
)
from .tag_temporary_weapon_enchantment import (
    is_temporarily_enchanted_weapon,
    remove_temporary_weapon_enchantment_marker,
    temporarily_enchanted_inventory_indices,
    temporary_weapon_loss_decision,
)


GREMLIN_REPELLANT_SOURCE = "Gremlin Repellant"


@dataclass(frozen=True)
class StealableItem:
    member: PartyMemberState
    bucket: str
    item_name: str
    inventory_index: int | None = None
    kukla_compartment_index: int | None = None
    theft_cost: int = 1
    temporarily_enchanted: bool = False


def has_gremlin_repellant(member: PartyMemberState) -> bool:
    return any("gremlin repellant" in item.lower() for item in member.inventory)


def gremlin_protection_active(session: SessionState, party: list[PartyMemberState]) -> bool:
    """Whole-event protection is Miners' Ointment; repellant protects selected items."""
    del party
    return session.gremlin_wm_protection_pending


def consume_gremlin_protection(session: SessionState, party: list[PartyMemberState]) -> list[str]:
    del party
    if not session.gremlin_wm_protection_pending:
        return []
    session.gremlin_wm_protection_pending = False
    session.pending_gremlin_event = None
    session.tag_star_object_gremlin_choice_pending = False
    return ["Miners' Ointment lets the party ignore the Invisible Gremlins event (EE p.160)."]


def apply_gremlin_repellant(
    session: SessionState,
    *,
    repellant_owner: PartyMemberState,
    target: PartyMemberState,
    item_name: str | None = None,
    item_container_id: str | None = None,
) -> list[str]:
    if not session.camped_outside:
        return ["Gremlin Repellant must be smeared on an item before the adventure (EE p.87)."]
    repellant = next(
        (item for item in repellant_owner.inventory if "gremlin repellant" in item.lower()),
        None,
    )
    if repellant is None:
        return [f"{repellant_owner.name} has no Gremlin Repellant."]
    if item_container_id:
        bag = item_container(target, item_container_id)
        if bag is None:
            return ["Choose a Bag of Carrying to protect."]
        if any(item.item_container_id == bag.id for item in session.gremlin_protected_items):
            return [f"{bag.name} is already protected for this adventure."]
        protection = GremlinProtectedItemState(
            character_id=target.character_id,
            item_container_id=bag.id,
            item_name=bag.name,
        )
        label = bag.name
    else:
        if not item_name or item_name not in target.inventory:
            return ["Choose one loose carried item to protect."]
        if "gremlin repellant" in item_name.lower():
            return ["Choose an item other than the Gremlin Repellant dose itself."]
        existing = sum(
            1
            for item in session.gremlin_protected_items
            if item.character_id == target.character_id
            and item.item_name == item_name
            and item.item_container_id is None
        )
        carried = sum(1 for item in target.inventory if item == item_name)
        if existing >= carried:
            return [f"Every carried {item_name} is already protected for this adventure."]
        protection = GremlinProtectedItemState(
            character_id=target.character_id,
            item_name=item_name,
        )
        label = item_name
    repellant_owner.inventory.remove(repellant)
    session.gremlin_protected_items.append(protection)
    return [
        f"{repellant_owner.name} uses {repellant} on {target.name}'s {label}. "
        "That one item is protected from Invisible Gremlins until this adventure ends (EE p.87)."
    ]


def move_gremlin_item_protection(
    session: SessionState,
    *,
    from_character_id: str,
    to_character_id: str,
    item_name: str,
    item_container_id: str | None = None,
) -> bool:
    """Keep item-level Repellant attached when the protected object changes carrier."""
    protection = next(
        (
            item
            for item in session.gremlin_protected_items
            if item.character_id == from_character_id
            and (
                item.item_container_id == item_container_id
                if item_container_id
                else item.item_container_id is None and item.item_name == item_name
            )
        ),
        None,
    )
    if protection is None:
        return False
    protection.character_id = to_character_id
    return True


def _is_scroll(item: str) -> bool:
    lower = item.lower()
    if "scroll tube" in lower:
        return False
    return lower.startswith("scroll") or "prism of" in lower or "bark of" in lower


def _is_potion(item: str) -> bool:
    return "potion" in item.lower() or "vial" in item.lower()


def _is_weapon_item(item: str) -> bool:
    from .inventory import is_carried_weapon

    lower = item.lower()
    return is_carried_weapon(item) or "swashbuckler" in lower and "hat" in lower


def _is_gem(item: str) -> bool:
    lower = item.lower()
    return "gem" in lower or "jewel" in lower


def _is_temple_tag(item: str) -> bool:
    return item.strip().lower() in {"tag resurrection tag", "tag blessing tag"}


def _is_magic_item(item: str) -> bool:
    lower = item.lower()
    if is_bag_of_carrying(item) or is_magic_weapon(item) or is_magic_armor(item) or is_charged_magic_item(item):
        return True
    return any(
        token in lower
        for token in (
            "magic ",
            "amulet",
            "ring",
            "talisman",
            "garment",
            "shoes of fast walk",
            "book of skalitos",
            "kukla miniature",
        )
    )


def _item_bucket(item: str) -> str | None:
    if _is_magic_item(item):
        return "magic_items"
    if _is_scroll(item):
        return "scrolls"
    if _is_potion(item):
        return "potions"
    if _is_weapon_item(item):
        return "weapons"
    if _is_gem(item):
        return "gems"
    return None


def _protected_loose_counts(session: SessionState, member: PartyMemberState) -> Counter[str]:
    return Counter(
        item.item_name
        for item in session.gremlin_protected_items
        if item.character_id == member.character_id
        and item.item_container_id is None
        and item.item_name
    )


def _stealable_items(
    session: SessionState,
    member: PartyMemberState,
    *,
    temporary_weapon_loss_kind: str | None = None,
) -> list[StealableItem]:
    candidates: list[StealableItem] = []
    protected_loose = _protected_loose_counts(session, member)
    temporary_enchantments = temporarily_enchanted_inventory_indices(member)
    skipped: Counter[str] = Counter()
    for index, item in enumerate(member.inventory):
        lower = item.lower()
        if (
            "gremlin repellant" in lower
            or is_star_object_item(item)
            or _is_temple_tag(item)
        ):
            continue
        temporarily_enchanted = index in temporary_enchantments
        if temporarily_enchanted:
            if temporary_weapon_loss_kind != "stolen":
                continue
            if temporary_weapon_loss_decision(session, member, item, "stolen") != "allow":
                continue
        bag = bag_for_inventory_index(member, index) if is_bag_of_carrying(item) else None
        if bag is not None and any(
            protection.item_container_id == bag.id
            for protection in session.gremlin_protected_items
        ):
            continue
        if bag is None and skipped[item] < protected_loose[item]:
            skipped[item] += 1
            continue
        theft_cost = 2 if "clockwork armor" in lower else 1
        bucket = "magic_items" if temporarily_enchanted else _item_bucket(item)
        if bucket == "scrolls":
            if scroll_protected_by_tube(member, item):
                continue
        if bucket is None:
            continue
        candidates.append(
            StealableItem(
                member=member,
                bucket=bucket,
                item_name=item,
                inventory_index=index,
                theft_cost=theft_cost,
                temporarily_enchanted=temporarily_enchanted,
            )
        )
    if member.class_id.lower() == "kukla" and member.current_life <= 0:
        for index, item in enumerate(member.kukla_compartment_items):
            bucket = _item_bucket(item)
            if bucket is None:
                continue
            candidates.append(
                StealableItem(
                    member=member,
                    bucket=bucket,
                    item_name=item,
                    kukla_compartment_index=index,
                )
            )
    return candidates


def _gremlin_property_remains(member: PartyMemberState) -> bool:
    for item in member.inventory:
        lower = item.lower()
        if "gremlin repellant" in lower or is_star_object_item(item) or _is_temple_tag(item):
            continue
        if _item_bucket(item) is not None:
            return True
    return any(_item_bucket(item) is not None for item in member.kukla_compartment_items) or (
        member.class_id.lower() == "kukla"
        and member.current_life <= 0
        and member.kukla_compartment_gold >= 10
    )


def _remove_stolen_item(candidate: StealableItem) -> str:
    member = candidate.member
    if candidate.kukla_compartment_index is not None:
        member.kukla_compartment_items.pop(candidate.kukla_compartment_index)
        return f"{member.name}'s exposed secret compartment loses {candidate.item_name}."
    if candidate.inventory_index is None:
        return f"{member.name} loses {candidate.item_name}."
    removed, contents = remove_inventory_item_with_contents(
        member,
        inventory_index=candidate.inventory_index,
    )
    if candidate.temporarily_enchanted:
        remove_temporary_weapon_enchantment_marker(member, candidate.item_name)
    return f"{member.name} loses {removed or candidate.item_name}{contained_loss_suffix(contents)}."


def _pending_prompt(session: SessionState) -> list[str]:
    pending = session.pending_gremlin_event
    if pending is None:
        return []
    return [
        f"Invisible Gremlins will steal {pending.theft_count} item(s). Cast Disbelief to reveal them, "
        "volunteer an eligible temple tag or temporarily enchanted weapon, or resolve the theft in "
        "printed priority order (EE pp.74, 169; TAG pp.11, 65)."
    ]


def begin_invisible_gremlins(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    tile_id: str,
    roll_fn: Callable[[], int] | None = None,
) -> list[str]:
    if session.pending_gremlin_event is None:
        session.pending_gremlin_event = PendingGremlinEventState(
            tile_id=tile_id,
            theft_count=max(1, (roll_fn or roll_d6)() + 3),
        )
    tally_log: list[str] = []
    if not session.pending_gremlin_event.major_tally_counted:
        session.pending_gremlin_event.major_tally_counted = True
        session.major_foes_encountered += 1
        tally_log.append(
            f"Major Foe tally: {session.major_foes_encountered} encountered this adventure. "
            "Invisible Gremlins count toward the tally but cannot be the Final Boss (EE pp.105, 169)."
        )
    return tally_log + resolve_invisible_gremlins(
        session,
        party,
        defer_theft=True,
    )


def resolve_invisible_gremlins(
    session: SessionState,
    party: list[PartyMemberState],
    *,
    roll_fn: Callable[[], int] | None = None,
    star_object_choice: str | None = None,
    defer_theft: bool = False,
) -> list[str]:
    log = ["Invisible Gremlins are an event, not a Foe (EE p.169)."]
    living = [member for member in party if member.current_life > 0]
    if not living:
        session.pending_gremlin_event = None
        return log + ["There is no living party to rob."]
    if session.pending_gremlin_event is None:
        tile_id = session.map_state.current_tile_id or "unknown"
        session.pending_gremlin_event = PendingGremlinEventState(
            tile_id=tile_id,
            theft_count=max(1, (roll_fn or roll_d6)() + 3),
        )
    reconcile_star_object_carrier(session)
    carrier = star_object_carrier(session)
    if carrier is not None:
        if star_object_choice not in {"release", "keep"}:
            session.tag_star_object_gremlin_choice_pending = True
            return log + [
                f"{carrier.name} may let the Invisible Gremlins take Bofto's cursed star-shaped object. "
                "Choose Let them take it to break the curse, or Keep it to continue the normal event "
                "(TAG p.30)."
            ]
        session.tag_star_object_gremlin_choice_pending = False
        if star_object_choice == "release":
            remove_star_object(session)
            session.pending_gremlin_event = None
            return log + [
                f"{carrier.name} lets the Invisible Gremlins take Bofto's star-shaped object. "
                "The curse is broken; Gremlin protection is bypassed (TAG p.30)."
            ]
        log.append(f"{carrier.name} keeps the cursed star-shaped object; the normal Gremlin event continues.")
    else:
        session.tag_star_object_gremlin_choice_pending = False
    if gremlin_protection_active(session, party):
        log.extend(consume_gremlin_protection(session, party))
        return log
    if defer_theft:
        return log + _pending_prompt(session)
    log.extend(resolve_pending_gremlin_theft(session, party))
    return log


def offer_gremlin_temple_tag(
    session: SessionState,
    *,
    character_id: str | None,
    item_name: str | None,
) -> list[str]:
    pending = session.pending_gremlin_event
    if pending is None:
        return ["No Invisible Gremlins event is waiting for a temple-tag choice."]
    if pending.theft_count <= 0:
        return ["The Gremlins have no theft slots left."]
    member = next(
        (
            item
            for item in session.party
            if item.character_id == character_id and item.current_life > 0
        ),
        None,
    )
    if member is None or not item_name or not _is_temple_tag(item_name) or item_name not in member.inventory:
        return ["Choose a living hero's Resurrection tag or Blessing tag to surrender voluntarily."]
    member.inventory.remove(item_name)
    pending.theft_count -= 1
    log = [
        f"{member.name} voluntarily lets the Invisible Gremlins take {item_name}; "
        f"{pending.theft_count} theft slot(s) remain (TAG p.11)."
    ]
    if pending.theft_count <= 0 and not session.tag_star_object_gremlin_choice_pending:
        session.pending_gremlin_event = None
        log.append("The Invisible Gremlins event is resolved.")
    return log


def offer_gremlin_temporary_weapon(
    session: SessionState,
    *,
    character_id: str | None,
    item_name: str | None,
) -> list[str]:
    pending = session.pending_gremlin_event
    if pending is None:
        return ["No Invisible Gremlins event is waiting for a temporary-weapon choice."]
    if pending.theft_count <= 0:
        return ["The Gremlins have no theft slots left."]
    member = next(
        (
            item
            for item in session.party
            if item.character_id == character_id and item.current_life > 0
        ),
        None,
    )
    if (
        member is None
        or not item_name
        or item_name not in member.inventory
        or not is_temporarily_enchanted_weapon(member, item_name)
    ):
        return ["Choose a living hero's temporarily enchanted weapon."]
    removed, contents = remove_inventory_item_with_contents(member, item_name=item_name)
    if removed is None:
        return [f"{member.name} no longer carries {item_name}."]
    remove_temporary_weapon_enchantment_marker(member, item_name)
    pending.theft_count -= 1
    log = [
        f"{member.name} chooses to let the Invisible Gremlins take the temporarily enchanted "
        f"{item_name}{contained_loss_suffix(contents)}; {pending.theft_count} theft slot(s) remain "
        "(TAG p.65, Temporary Weapon Enchantment)."
    ]
    if pending.theft_count <= 0 and not session.tag_star_object_gremlin_choice_pending:
        session.pending_gremlin_event = None
        log.append("The Invisible Gremlins event is resolved.")
    return log


def resolve_pending_gremlin_theft(
    session: SessionState,
    party: list[PartyMemberState],
) -> list[str]:
    pending = session.pending_gremlin_event
    if pending is None:
        return ["No Invisible Gremlins theft is waiting to resolve."]
    living = [member for member in party if member.current_life > 0]
    remaining = pending.theft_count
    log = [f"Invisible Gremlins steal up to {remaining} item(s) in printed priority order."]
    priority = ("magic_items", "scrolls", "potions", "weapons", "gems")
    stolen = 0
    while remaining > 0:
        candidates = [
            candidate
            for member in party
            if member.current_life > 0 or member.class_id.lower() == "kukla"
            for candidate in _stealable_items(session, member)
            if candidate.theft_cost <= remaining
        ]
        chosen = next(
            (
                candidate
                for bucket in priority
                for candidate in candidates
                if candidate.bucket == bucket
            ),
            None,
        )
        if chosen is not None:
            log.append(_remove_stolen_item(chosen))
            remaining -= chosen.theft_cost
            stolen += chosen.theft_cost
            continue
        gold_holder = next((member for member in living if member.gold >= 10), None)
        dead_kukla = next(
            (
                member
                for member in party
                if member.class_id.lower() == "kukla"
                and member.current_life <= 0
                and member.kukla_compartment_gold >= 10
            ),
            None,
        )
        if gold_holder is None and dead_kukla is None:
            break
        if gold_holder is not None:
            gold_holder.gold -= 10
            log.append(f"{gold_holder.name} loses 10gp to the Gremlins.")
        else:
            assert dead_kukla is not None
            dead_kukla.kukla_compartment_gold -= 10
            log.append(f"{dead_kukla.name}'s exposed secret compartment loses 10gp to the Gremlins.")
        remaining -= 1
        stolen += 1
    pending.theft_count = remaining
    session.pending_gremlin_event = None
    property_left = any(
        _gremlin_property_remains(member)
        for member in party
        if member.current_life > 0 or member.class_id.lower() == "kukla"
    ) or any(member.gold >= 10 for member in living)
    if stolen and not property_left:
        session.clues_found += 1
        log.append("The Gremlins steal everything eligible and leave a thank-you note (1 Clue, EE p.169).")
    elif remaining:
        log.append(f"No eligible item or 10gp unit remains; {remaining} theft slot(s) go unused.")
    return log


def reveal_invisible_gremlins(
    session: SessionState,
    *,
    roll_fn: Callable[[], int] = roll_d6,
) -> tuple[list[EnemyState], list[str]]:
    if session.pending_gremlin_event is None:
        return [], ["Disbelief finds no pending Invisible Gremlins event."]
    count = max(1, roll_fn() + 1)
    enemies = [
        EnemyState(
            id=uuid4().hex,
            name="Revealed Invisible Gremlins",
            category="minions",
            level=3,
            life=1,
            max_life=1,
            attacks=1,
            tags=[
                "gremlin",
                "revealed_by_disbelief",
                "minor_group:revealed_invisible_gremlins",
                "damage_per_hit:0",
                "morale_modifier:-1",
            ],
            on_hit_effects=[{"type": "steal_item", "source": "Invisible Gremlins"}],
        )
        for _ in range(count)
    ]
    session.pending_gremlin_event = None
    session.tag_star_object_gremlin_choice_pending = False
    return enemies, [
        f"Disbelief reveals {count} Invisible Gremlin(s): L3 Minions, -1 Morale, one attack, "
        "and one Treasure roll for the encounter (EE p.74). Failed Defense lets a Gremlin steal "
        "one eligible object instead of causing Life loss."
    ]


def steal_one_revealed_gremlin_item(
    session: SessionState,
    target: PartyMemberState,
) -> list[str]:
    priority = ("magic_items", "scrolls", "potions", "weapons", "gems")
    candidates = _stealable_items(
        session,
        target,
        temporary_weapon_loss_kind="stolen",
    )
    chosen = next(
        (
            candidate
            for bucket in priority
            for candidate in candidates
            if candidate.bucket == bucket
        ),
        None,
    )
    if chosen is not None:
        return [f"Effect: {_remove_stolen_item(chosen)}"]
    if target.gold >= 10:
        target.gold -= 10
        return [f"Effect: {target.name} loses 10gp to a revealed Invisible Gremlin."]
    return [f"{target.name} has no eligible object or 10gp unit for the revealed Gremlin to steal."]
