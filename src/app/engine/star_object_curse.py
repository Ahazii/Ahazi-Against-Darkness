from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ..schemas import CampaignState, EnemyState, Party, PartyMemberState, SessionState, TileState
from .cavern_features import template_surprise_tags
from .class_combat import save_modifier
from .combat_modifiers import SPELLCASTER_CLASS_IDS
from .dice import roll_d6, roll_exploding_for_level
from .madness import apply_madness_gain
from .foe_weapon_restrictions import template_weapon_allow_tags
from .monster_stats import parse_monster_attacks, parse_monster_life
from .monster_template_effects import (
    template_combat_tags,
    template_encounter_start_effects,
    template_on_hit_effects,
    template_per_turn_effects,
    template_special_attacks,
)

if TYPE_CHECKING:
    from ..db import Store


STAR_OBJECT_ITEM = "Bofto's Star-Shaped Cursed Object"
STAR_OBJECT_STATUS = "Bofto's Star-Shaped Object Curse"
LEGACY_STAR_OBJECT_STATUS = "TAG star-shaped object curse carrier"
STAR_SLAYER_NAME = "Star-Slayer from Beyond"
STAR_SLAYER_CHECKED_TAG = "star_slayer_replacement_checked"
STAR_SLAYER_SIGHT_APPLIED_TAG = "star_slayer_sight_applied"
STAR_SLAYER_TREASURE_SOURCE_PREFIX = "star_slayer_final_treasure_source:"


@dataclass(frozen=True)
class StarObjectWillResult:
    passed: bool
    roll: int
    rolls: list[int]
    modifier: int
    total: int
    log: list[str]

    @property
    def result_text(self) -> str:
        outcome = "passes" if self.passed else "fails"
        return (
            f"Scene 19: The selected carrier {outcome} the L8 Will Save. "
            f"{STAR_OBJECT_ITEM} is now carried and its curse remains operative."
        )


def is_star_object_item(item: str) -> bool:
    text = str(item or "").strip().lower()
    return text in {
        STAR_OBJECT_ITEM.lower(),
        "star-shaped object",
        "star shaped object",
        "bofto's star-shaped object",
    }


def is_star_object_status(status: str) -> bool:
    return str(status or "").strip().lower() in {
        STAR_OBJECT_STATUS.lower(),
        LEGACY_STAR_OBJECT_STATUS.lower(),
    }


def removable_inventory_items(items: list[str]) -> list[str]:
    """Return items eligible for ordinary loss, destruction, storage, or sacrifice."""
    from .item_disposition import ItemDisposition, eligible_inventory_items

    return eligible_inventory_items(items, ItemDisposition.ORDINARY_LOSS)


def _ordered_members(session: SessionState) -> list[PartyMemberState]:
    return sorted(session.party, key=lambda member: (member.marching_order, member.name))


def star_object_carrier(session: SessionState) -> PartyMemberState | None:
    ordered = _ordered_members(session)
    return next(
        (
            member
            for member in ordered
            if any(is_star_object_item(item) for item in member.inventory)
        ),
        None,
    ) or next(
        (
            member
            for member in ordered
            if any(is_star_object_status(status) for status in member.statuses)
        ),
        None,
    )


def _strip_star_object(member: PartyMemberState) -> bool:
    inventory = [item for item in member.inventory if not is_star_object_item(item)]
    statuses = [status for status in member.statuses if not is_star_object_status(status)]
    changed = inventory != member.inventory or statuses != member.statuses
    member.inventory = inventory
    member.statuses = statuses
    return changed


def give_star_object(session: SessionState, member: PartyMemberState) -> None:
    for candidate in session.party:
        _strip_star_object(candidate)
    member.inventory.append(STAR_OBJECT_ITEM)
    member.statuses.append(STAR_OBJECT_STATUS)
    session.tag_star_object_curse_active = True
    session.tag_star_object_curse_cleared = False
    session.tag_star_object_recovery_pending = False
    session.tag_star_object_assignment_pending = False


def remove_star_object(session: SessionState) -> None:
    for member in session.party:
        _strip_star_object(member)
    session.tag_star_object_curse_active = False
    session.tag_star_object_curse_cleared = True
    session.tag_star_object_recovery_pending = False
    session.tag_star_object_assignment_pending = False
    session.tag_star_object_gremlin_choice_pending = False


def resolve_scene19_pickup(
    session: SessionState,
    member: PartyMemberState,
    *,
    roll_save: Callable[[PartyMemberState], tuple[int, list[int]]] | None = None,
    show_rolls: bool = True,
) -> StarObjectWillResult:
    """Assign Scene 19's object and resolve its printed L8 Will Save."""
    give_star_object(session, member)
    roller = roll_save or (
        lambda target: roll_exploding_for_level(target, session=session, log=session.log)
    )
    total_roll, rolls = roller(member)
    modifier = save_modifier(
        member,
        save_label="Bofto star-shaped object Will Save",
        session=session,
    )
    if member.class_id.lower() in SPELLCASTER_CLASS_IDS:
        modifier += member.level
    total = total_roll + modifier
    passed = bool(rolls and rolls[0] != 1 and total >= 8)
    log: list[str] = [
        f"{member.name} picks up {STAR_OBJECT_ITEM}; the curse becomes operative (TAG p.30, Scene 19)."
    ]
    if show_rolls:
        log.append(
            f"Scene 19 Will Save: {member.name} rolls {' + '.join(str(value) for value in rolls)} "
            f"+ {modifier} = {total} vs L8."
        )
    if not passed and member.class_id.lower() == "halfling":
        total_roll, rolls = roller(member)
        total = total_roll + modifier
        passed = bool(rolls and rolls[0] != 1 and total >= 8)
        if show_rolls:
            log.append(
                f"Halfling reroll: {member.name} rolls {' + '.join(str(value) for value in rolls)} "
                f"+ {modifier} = {total} vs L8."
            )
    if passed:
        log.append(f"{member.name} passes the Will Save and gains no Madness; the curse still remains.")
    else:
        log.append(f"{member.name} fails the Will Save.")
        log.extend(
            apply_madness_gain(
                session,
                member,
                source="Bofto's star-shaped object",
                show_rolls=show_rolls,
                allow_damage_choice=False,
            )
        )
    return StarObjectWillResult(
        passed=passed,
        roll=rolls[0] if rolls else total_roll,
        rolls=list(rolls),
        modifier=modifier,
        total=total,
        log=log,
    )


def reconcile_star_object_carrier(session: SessionState) -> bool:
    """Repair legacy markers and enforce automatic transfer when a carrier dies."""
    before = (
        session.tag_star_object_curse_active,
        session.tag_star_object_curse_cleared,
        session.tag_star_object_recovery_pending,
        session.tag_star_object_assignment_pending,
        tuple((member.character_id, tuple(member.inventory), tuple(member.statuses)) for member in session.party),
    )
    if session.tag_star_object_curse_cleared:
        for member in session.party:
            _strip_star_object(member)
        session.tag_star_object_curse_active = False
        session.tag_star_object_recovery_pending = False
        session.tag_star_object_assignment_pending = False
    else:
        carrier = star_object_carrier(session)
        living = [member for member in _ordered_members(session) if member.current_life > 0]
        if carrier is not None and carrier.current_life > 0:
            for candidate in session.party:
                if candidate.character_id != carrier.character_id:
                    _strip_star_object(candidate)
            carrier.inventory = [item for item in carrier.inventory if not is_star_object_item(item)]
            carrier.statuses = [status for status in carrier.statuses if not is_star_object_status(status)]
            carrier.inventory.append(STAR_OBJECT_ITEM)
            carrier.statuses.append(STAR_OBJECT_STATUS)
            session.tag_star_object_curse_active = True
            session.tag_star_object_curse_cleared = False
            session.tag_star_object_recovery_pending = False
            session.tag_star_object_assignment_pending = False
        elif carrier is not None and living:
            successor = living[0]
            give_star_object(session, successor)
            session.log.append(
                f"{carrier.name} has died; {successor.name} automatically picks up {STAR_OBJECT_ITEM} "
                "and the curse continues (TAG p.31)."
            )
        elif carrier is not None:
            for member in session.party:
                _strip_star_object(member)
            session.tag_star_object_curse_active = False
            session.tag_star_object_recovery_pending = True
            session.tag_star_object_assignment_pending = False
            session.log.append(
                "The entire party has fallen. The star-shaped object remains in the campaign and may be "
                "found with a future treasure (TAG p.31)."
            )
        elif session.tag_star_object_recovery_pending:
            session.tag_star_object_curse_active = False
        elif session.tag_star_object_curse_active and living:
            successor = living[0]
            give_star_object(session, successor)
            session.log.append(
                f"Recovered missing curse state: {successor.name} carries {STAR_OBJECT_ITEM}."
            )
        elif session.tag_star_object_curse_active:
            session.tag_star_object_curse_active = False
            session.tag_star_object_recovery_pending = True
    after = (
        session.tag_star_object_curse_active,
        session.tag_star_object_curse_cleared,
        session.tag_star_object_recovery_pending,
        session.tag_star_object_assignment_pending,
        tuple((member.character_id, tuple(member.inventory), tuple(member.statuses)) for member in session.party),
    )
    return before != after


def maybe_find_star_object_in_treasure(
    session: SessionState,
    tile: TileState,
    *,
    roll_fn: Callable[[], int] = roll_d6,
) -> bool:
    if not session.tag_star_object_recovery_pending or tile.tag_star_object_recovery_checked:
        return False
    tile.tag_star_object_recovery_checked = True
    roll = roll_fn()
    session.log.append(
        f"Star-shaped object recovery check: d6 = {roll}; it is found on 1 (TAG p.31)."
    )
    if roll == 1:
        session.tag_star_object_assignment_pending = True
        session.log.append(
            f"{STAR_OBJECT_ITEM} is among this treasure. Choose a living hero to carry it; the curse resumes."
        )
    return True


def assign_recovered_star_object(session: SessionState, character_id: str | None) -> list[str]:
    if not session.tag_star_object_assignment_pending:
        return ["No recovered star-shaped object is waiting for assignment."]
    member = next(
        (
            candidate
            for candidate in session.party
            if candidate.character_id == character_id and candidate.current_life > 0
        ),
        None,
    )
    if member is None:
        return ["Choose a living hero to carry the recovered star-shaped object."]
    give_star_object(session, member)
    return [
        f"{member.name} takes {STAR_OBJECT_ITEM}. The curse is operative again (TAG p.31)."
    ]


def apply_star_object_campaign_to_session(store: Store, session: SessionState) -> SessionState:
    from .tag_campaign import STAR_OBJECT_EFFECT_KEY, campaign_effect, load_campaign

    campaign = load_campaign(store)
    party = store.get("parties", session.party_id, Party.model_validate) if not session.campaign_id else None
    campaign_id = session.campaign_id or (party.campaign_id if party is not None else None) or campaign.active_world_campaign_id
    session.campaign_id = campaign_id
    effect = campaign_effect(
        campaign,
        campaign_id=campaign_id,
        key=STAR_OBJECT_EFFECT_KEY,
    )
    carrier = star_object_carrier(session)
    if effect is not None and effect.status == "cleared":
        remove_star_object(session)
        return session
    if effect is not None and effect.status == "recovery_pending":
        for member in session.party:
            _strip_star_object(member)
        session.tag_star_object_curse_cleared = False
        session.tag_star_object_curse_active = False
        session.tag_star_object_recovery_pending = True
        session.tag_star_object_assignment_pending = False
        return session
    if effect is not None and effect.status == "active":
        expected = next(
            (
                member
                for member in session.party
                if member.character_id == effect.carrier_character_id
            ),
            None,
        )
        if expected is None:
            for member in session.party:
                _strip_star_object(member)
            session.tag_star_object_curse_active = False
            session.tag_star_object_curse_cleared = False
            session.tag_star_object_recovery_pending = False
            session.tag_star_object_assignment_pending = False
            return session
        if carrier is None or carrier.character_id != expected.character_id:
            give_star_object(session, expected)
    reconcile_star_object_carrier(session)
    return session


def sync_star_object_campaign_from_session(store: Store, session: SessionState) -> CampaignState:
    from .tag_campaign import (
        STAR_OBJECT_EFFECT_KEY,
        campaign_effect,
        load_campaign,
        save_campaign,
        set_campaign_effect,
    )

    campaign = load_campaign(store)
    campaign_id = session.campaign_id or campaign.active_world_campaign_id
    session.campaign_id = campaign_id
    reconcile_star_object_carrier(session)
    carrier = star_object_carrier(session)
    desired_status: str | None = None
    desired_carrier_id: str | None = None
    if session.tag_star_object_curse_cleared:
        desired_status = "cleared"
    elif session.tag_star_object_recovery_pending or session.tag_star_object_assignment_pending:
        desired_status = "recovery_pending"
    elif carrier is not None and carrier.current_life > 0:
        desired_status = "active"
        desired_carrier_id = carrier.character_id
    current = campaign_effect(
        campaign,
        campaign_id=campaign_id,
        key=STAR_OBJECT_EFFECT_KEY,
    )
    changed = False
    if desired_status is not None and (
        current is None
        or current.status != desired_status
        or current.carrier_character_id != desired_carrier_id
    ):
        set_campaign_effect(
            campaign,
            campaign_id=campaign_id,
            key=STAR_OBJECT_EFFECT_KEY,
            status=desired_status,
            source="TAG pp.30-31, Bofto's Star-Shaped Object",
            carrier_character_id=desired_carrier_id,
            details={"item": STAR_OBJECT_ITEM},
        )
        changed = True
    if changed:
        save_campaign(store, campaign)
    return campaign


def _star_slayer_template(monsters: dict[str, Any]) -> dict[str, Any]:
    for template in monsters.get("tag_weird", []):
        if isinstance(template, dict) and template.get("name") == STAR_SLAYER_NAME:
            return template
    raise ValueError(f"{STAR_SLAYER_NAME} is missing from tag_weird.")


def spawn_star_slayer(
    session: SessionState,
    monsters: dict[str, Any],
    *,
    enemy_id: str | None = None,
    final_boss: bool = False,
    final_treasure_source: str | None = None,
) -> EnemyState:
    template = _star_slayer_template(monsters)
    hcl = max((member.level for member in session.party if member.current_life > 0), default=1)
    life = parse_monster_life(template.get("life", "HCL+5"), hcl)
    tags = list(
        dict.fromkeys(
            template_surprise_tags(template)
            + template_weapon_allow_tags(template)
            + template_combat_tags(template)
        )
    )
    if final_boss:
        if "final_boss" not in tags:
            tags.append("final_boss")
        if final_treasure_source:
            tags.append(f"{STAR_SLAYER_TREASURE_SOURCE_PREFIX}{final_treasure_source}")
    return EnemyState(
        id=enemy_id or uuid4().hex,
        name=STAR_SLAYER_NAME,
        category="weird",
        level=max(1, hcl + int(template.get("level_delta", 6))),
        life=life,
        max_life=life,
        attacks=parse_monster_attacks(template.get("attacks", 4), hcl),
        tags=tags,
        initial_count=1,
        on_hit_effects=template_on_hit_effects(template),
        encounter_start_effects=template_encounter_start_effects(template),
        per_turn_effects=template_per_turn_effects(template),
        special_attacks=template_special_attacks(template),
    )


def maybe_replace_major_foes(
    session: SessionState,
    tile: TileState,
    monsters: dict[str, Any],
    *,
    roll_fn: Callable[[], int] = roll_d6,
    show_rolls: bool = True,
) -> bool:
    reconcile_star_object_carrier(session)
    if not session.tag_star_object_curse_active or star_object_carrier(session) is None:
        return False
    changed = False
    for index, enemy in enumerate(list(tile.enemies)):
        tags = {str(tag).lower() for tag in enemy.tags}
        if enemy.life <= 0 or enemy.category not in {"boss", "weird"}:
            continue
        if enemy.name == STAR_SLAYER_NAME or STAR_SLAYER_CHECKED_TAG in tags:
            continue
        roll = roll_fn()
        if show_rolls:
            session.log.append(
                f"Star-shaped object major-foe check for {enemy.name}: d6 = {roll}; "
                "Star-Slayer replaces it on 1-2 (TAG p.30)."
            )
        if roll > 2:
            enemy.tags.append(STAR_SLAYER_CHECKED_TAG)
            changed = True
            continue
        is_final = "final_boss" in tags
        tile.enemies[index] = spawn_star_slayer(
            session,
            monsters,
            enemy_id=enemy.id,
            final_boss=is_final,
            final_treasure_source=enemy.name if is_final else None,
        )
        session.log.append(
            f"The curse replaces {enemy.name} with {STAR_SLAYER_NAME}."
            + (" It retains that Final Boss's treasure." if is_final else " It carries no treasure.")
        )
        changed = True
    return changed


def star_slayer_final_treasure_source(enemy: EnemyState) -> str | None:
    for tag in enemy.tags:
        text = str(tag)
        if text.lower().startswith(STAR_SLAYER_TREASURE_SOURCE_PREFIX):
            return text.split(":", 1)[1].strip() or None
    return None
