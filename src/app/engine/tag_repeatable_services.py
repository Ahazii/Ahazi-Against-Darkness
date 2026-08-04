from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..db import now_utc
from ..schemas import HirelingState, PartyMemberState, SessionState
from .banking import take_living_party_funds
from .dice import AdvancementRollResult, roll_advancement
from .equipment_shop import can_class_use_item
from .class_profiles import available_level_up_spells
from .combat_modifiers import is_spellcaster, mark_tag_leprechaun_illusion_spell
from .experience import (
    advancement_succeeds,
    apply_level_up,
    tier_for_level,
)
from .magic_weapons import can_member_wield_weapon
from .tier_advancement import level_up_gate_reason


TAG_REPEATABLE_SERVICE_STATE_KEY = "tag_repeatable_service"
TAG_REPEATABLE_SERVICE_DONE_ACTION = "tag_repeatable_service_done"
SHOES_OF_FAST_WALK = "Shoes of Fast Walk"
DEOLDYN_SOURCE_MARKER = "tag_deoldyn"
DEOLDYN_SKILLS: dict[str, tuple[str, str]] = {
    "deadly_accuracy": (
        "Deadly Accuracy",
        "+1 Attack whenever this Deoldyn-trained character attacks with a bow.",
    ),
    "dead_shot": (
        "Dead Shot",
        "Automatically reroll every failed ranged Attack once.",
    ),
}


def repeatable_service_kind(session: SessionState) -> str:
    manifest = session.imported_manifest if isinstance(session.imported_manifest, dict) else {}
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    parameters = source.get("parameters") if isinstance(source.get("parameters"), dict) else {}
    reference = parameters.get("tag_reference") if isinstance(parameters, dict) else {}
    if not isinstance(reference, dict):
        return ""
    try:
        rumor_number = int(reference.get("rumor_number") or 0)
    except (TypeError, ValueError):
        rumor_number = 0
    if rumor_number == 6:
        return "leprechaun"
    if rumor_number == 11:
        return "deoldyn"
    haystack = " ".join(
        str(value or "")
        for value in (
            manifest.get("title"),
            reference.get("title"),
            reference.get("lead_detail"),
            reference.get("scene"),
        )
    ).casefold()
    if "leprechaun" in haystack or "blackbird hill" in haystack:
        return "leprechaun"
    if "deoldyn" in haystack or "archery training" in haystack:
        return "deoldyn"
    return ""


def repeatable_service_state(session: SessionState) -> dict[str, Any]:
    quest = session.active_quest
    if quest is None:
        return {}
    value = (quest.tag_procedure_state or {}).get(TAG_REPEATABLE_SERVICE_STATE_KEY)
    return dict(value) if isinstance(value, dict) else {}


def set_repeatable_service_state(session: SessionState, state: dict[str, Any]) -> None:
    quest = session.active_quest
    if quest is None:
        raise ValueError("The generated Adventures Guild quest state is missing.")
    procedure_state = dict(quest.tag_procedure_state or {})
    procedure_state[TAG_REPEATABLE_SERVICE_STATE_KEY] = dict(state)
    quest.tag_procedure_state = procedure_state


def _open_state(session: SessionState, expected_kind: str) -> dict[str, Any]:
    kind = repeatable_service_kind(session)
    if kind != expected_kind:
        raise ValueError("This repeatable service is not active in the current Adventures Guild lead.")
    state = repeatable_service_state(session)
    if str(state.get("phase") or "open") == "resolved":
        raise ValueError("This Adventures Guild service visit is already finished.")
    state.setdefault("kind", kind)
    state.setdefault("phase", "open")
    state.setdefault("transactions", [])
    return state


def _living_member(session: SessionState, character_id: str) -> PartyMemberState:
    member = next(
        (
            item
            for item in session.party
            if item.character_id == str(character_id or "") and item.current_life > 0
        ),
        None,
    )
    if member is None:
        raise ValueError("Choose a living party member.")
    return member


def _living_hireling(session: SessionState, hireling_id: str) -> HirelingState:
    hireling = next(
        (
            item
            for item in session.hirelings or []
            if item.id == str(hireling_id or "") and item.life > 0
        ),
        None,
    )
    if hireling is None:
        raise ValueError("Choose a living hireling currently travelling with the party.")
    return hireling


def _gold_breakdown(member: PartyMemberState) -> dict[str, int]:
    carried_gold = max(0, int(member.gold or 0))
    bank_gold = max(0, int(member.bank_gold or 0))
    return {
        "carried_gold": carried_gold,
        "bank_gold": bank_gold,
        "available_gold": carried_gold + bank_gold,
    }


def _available_gold(member: PartyMemberState) -> int:
    return _gold_breakdown(member)["available_gold"]


def _shoe_count(member: PartyMemberState) -> int:
    return sum(
        1
        for item in member.inventory
        if str(item).strip().casefold() == SHOES_OF_FAST_WALK.casefold()
    )


def _shoe_assignments(state: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in state.get("shoe_assignments") or [] if isinstance(item, dict)]


def _assigned_recipient(state: dict[str, Any], recipient_kind: str, recipient_id: str) -> bool:
    return any(
        str(item.get("recipient_kind") or "") == recipient_kind
        and str(item.get("recipient_id") or "") == recipient_id
        for item in _shoe_assignments(state)
    )


def _active_hireling_shoe_count(
    session: SessionState,
    state: dict[str, Any],
    owner_character_id: str,
) -> int:
    return len(
        _active_hireling_shoe_assignments(
            session,
            state,
            owner_character_id=owner_character_id,
        )
    )


def _active_hireling_shoe_assignments(
    session: SessionState,
    state: dict[str, Any],
    *,
    owner_character_id: str | None = None,
) -> list[dict[str, Any]]:
    """Return living-hireling assignments that still reserve party-owned pairs."""
    living_hireling_ids = {
        hireling.id
        for hireling in session.hirelings or []
        if hireling.life > 0
    }
    return [
        item
        for item in _shoe_assignments(state)
        if str(item.get("recipient_kind") or "") == "hireling"
        and str(item.get("recipient_id") or "") in living_hireling_ids
        and (
            owner_character_id is None
            or str(item.get("owner_character_id") or "") == owner_character_id
        )
    ]


def _hireling_assignment_has_accessible_pair(
    session: SessionState,
    state: dict[str, Any],
    hireling_id: str,
) -> bool:
    """Allocate each living assignment to one loose pair in its owner's inventory."""
    assignments = _active_hireling_shoe_assignments(session, state)
    target = next(
        (
            item
            for item in assignments
            if str(item.get("recipient_id") or "") == hireling_id
        ),
        None,
    )
    if target is None:
        return False
    owner_id = str(target.get("owner_character_id") or "")
    owner = next(
        (member for member in session.party if member.character_id == owner_id),
        None,
    )
    if owner is None:
        return False
    owner_assignments = [
        item
        for item in assignments
        if str(item.get("owner_character_id") or "") == owner_id
    ]
    assignment_index = next(
        (
            index
            for index, item in enumerate(owner_assignments)
            if str(item.get("recipient_id") or "") == hireling_id
        ),
        -1,
    )
    return assignment_index >= 0 and assignment_index < _shoe_count(owner)


def _current_party_tier(session: SessionState) -> int:
    levels = [member.level for member in session.party if member.current_life > 0]
    if not levels:
        levels = [member.level for member in session.party]
    return tier_for_level(max(levels, default=1))


def _has_wearable_shoes(
    member: PartyMemberState,
    session: SessionState,
    state: dict[str, Any],
) -> bool:
    """Return whether one party-owned pair is currently available to this hero."""
    return _shoe_count(member) > _active_hireling_shoe_count(
        session,
        state,
        member.character_id,
    )


def assigned_hireling_shoes_lock_reason(
    session: SessionState | None,
    owner_character_id: str,
) -> str:
    if session is None:
        return ""
    state = repeatable_service_state(session)
    assigned = _active_hireling_shoe_count(session, state, owner_character_id)
    if assigned <= 0:
        return ""
    owner = next(
        (member for member in session.party if member.character_id == owner_character_id),
        None,
    )
    # One loose pair must remain available for every living hireling assignment.
    # Identical extra pairs may still be transferred, sold, or stored.
    if owner is not None and _shoe_count(owner) - 1 >= assigned:
        return ""
    pair_text = "pair is" if assigned == 1 else f"{assigned} pairs are"
    return (
        f"Shoes of Fast Walk cannot be transferred or sold, or put out of reach in storage, while "
        f"{pair_text} assigned to a living hireling. "
        "The Shoes remain party property and become available again when that hireling leaves."
    )


def _record_transaction(state: dict[str, Any], transaction: dict[str, Any]) -> None:
    transactions = [dict(item) for item in state.get("transactions") or [] if isinstance(item, dict)]
    transactions.append({**transaction, "recorded_at": now_utc()})
    state["transactions"] = transactions
    state["updated_at"] = now_utc()


def buy_shoes_of_fast_walk(
    session: SessionState,
    *,
    payer_character_id: str,
    recipient_kind: str,
    recipient_id: str,
) -> dict[str, Any]:
    state = _open_state(session, "leprechaun")
    payer = _living_member(session, payer_character_id)
    clean_kind = str(recipient_kind or "hero").strip().casefold()
    if clean_kind not in {"hero", "hireling"}:
        raise ValueError("Shoes may be assigned to a living hero or hireling, not an animal companion.")
    if _assigned_recipient(state, clean_kind, recipient_id):
        raise ValueError("That recipient already has a pair from this Blackbird Hill visit.")

    owner: PartyMemberState
    recipient_name: str
    hireling: HirelingState | None = None
    if clean_kind == "hero":
        owner = _living_member(session, recipient_id)
        allowed, reason = can_class_use_item(
            owner.class_id,
            {"category": "magic_item", "magic": True},
        )
        if not allowed:
            raise ValueError(reason or f"{owner.name} cannot use magic items and may not wear these shoes.")
        if _has_wearable_shoes(owner, session, state):
            raise ValueError(f"{owner.name} already owns Shoes of Fast Walk; each character may have at most one pair.")
        recipient_name = owner.name
    else:
        hireling = _living_hireling(session, recipient_id)
        owner = payer
        recipient_name = hireling.name

    paid, available, contributions = take_living_party_funds([payer], 200)
    if not paid:
        raise ValueError(f"{payer.name} needs 200 gp in carried and banked funds (has {available} gp).")

    owner.inventory.append(SHOES_OF_FAST_WALK)
    if hireling is not None:
        marker = f"{SHOES_OF_FAST_WALK} (party-owned; {payer.name})"
        if marker not in hireling.statuses:
            hireling.statuses.append(marker)
    assignment = {
        "recipient_kind": clean_kind,
        "recipient_id": recipient_id,
        "recipient_name": recipient_name,
        "owner_character_id": owner.character_id,
        "owner_name": owner.name,
        "payer_character_id": payer.character_id,
        "payer_name": payer.name,
        "party_tier": _current_party_tier(session),
    }
    assignments = _shoe_assignments(state)
    assignments.append(assignment)
    state["shoe_assignments"] = assignments
    _record_transaction(
        state,
        {
            "type": "shoes",
            "cost_gp": 200,
            **assignment,
            "payment": [
                {
                    "name": item.name,
                    "bank_gold": item.bank_gold,
                    "carried_gold": item.carried_gold,
                }
                for item in contributions
            ],
        },
    )
    result_text = (
        f"{payer.name} pays 200 gp and assigns one pair of Shoes of Fast Walk to {recipient_name}. "
        f"The wearer adds +Tier to Defense when withdrawing or fleeing melee. "
        f"Pairs bought this visit: {len(assignments)}."
    )
    state["result_text"] = result_text
    set_repeatable_service_state(session, state)
    session.log.append(f"Blackbird Hill bargain (TAG pp.25-26, Scene 2): {result_text}")
    return {
        "result_text": result_text,
        "changed_character_ids": sorted({payer.character_id, owner.character_id}),
        "state": state,
    }


_ILLUSION_NAME_MARKERS = ("illusion", "phantasm", "glamour", "mirage")


def _qualifies_as_illusion(spell_name: str, description: str, source_table: str) -> bool:
    if source_table == "illusionist_spells_table":
        return True
    text = f"{spell_name} {description}".casefold()
    return any(marker in text for marker in _ILLUSION_NAME_MARKERS)


def tag_illusion_spell_options(
    session: SessionState,
    dungeon_tables: dict[str, Any],
    expert_catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    active = {str(value) for value in session.active_supplement_ids or []}
    expert_by_name = {
        str(row.get("name") or "").strip().casefold(): dict(row)
        for row in expert_catalog.get("expert_spells") or []
        if isinstance(row, dict) and row.get("name")
    }
    options: dict[str, dict[str, Any]] = {}
    for table_key, rows in dungeon_tables.items():
        if "spell" not in str(table_key) or not isinstance(rows, list):
            continue
        if str(table_key).startswith("fd_") and "forsaken-depths" not in active:
            continue
        if str(table_key).startswith("courtship_") and "courtship" not in active:
            continue
        if str(table_key) == "expert_spells_table" and "four-against-the-abyss" not in active:
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("spell") or row.get("name") or "").strip()
            description = str(row.get("result") or row.get("description") or "").strip()
            if not name or not _qualifies_as_illusion(name, description, str(table_key)):
                continue
            key = name.casefold()
            option = options.setdefault(
                key,
                {
                    "name": name,
                    "description": description,
                    "source_tables": [],
                    "native_class_ids": [],
                    "expert_requirements": {},
                },
            )
            if str(table_key) not in option["source_tables"]:
                option["source_tables"].append(str(table_key))
            native = set(option["native_class_ids"])
            native.add("illusionist")
            if table_key == "illusionist_spells_table":
                native.add("gnome")
            elif table_key == "basic_spells_table":
                native.update({"wizard", "elf"})
            elif table_key == "druid_spells_table":
                native.add("druid")
            elif table_key == "courtship_blossoms_spell_scrolls_table":
                native.update({"wizard", "conservationist"})
            elif table_key == "expert_spells_table":
                expert = expert_by_name.get(key, {})
                codes = {str(value) for value in expert.get("classes") or []}
                if "Wi" in codes:
                    native.add("wizard")
                if "E" in codes:
                    native.add("elf")
                for class_id in ("wizard", "elf"):
                    if class_id in native:
                        option["expert_requirements"][class_id] = {
                            "min_level": int(expert.get("min_level") or expert_catalog.get("min_level_default") or 5),
                            "expert_trained": True,
                        }
            option["native_class_ids"] = sorted(native)
    return sorted(options.values(), key=lambda item: str(item.get("name") or "").casefold())


def _spell_option(options: list[dict[str, Any]], spell_name: str) -> dict[str, Any]:
    normalized = str(spell_name or "").strip().casefold()
    option = next(
        (item for item in options if str(item.get("name") or "").strip().casefold() == normalized),
        None,
    )
    if option is None:
        raise ValueError("Choose an indexed illusion-type spell from an owned rules table.")
    return option


def _spell_learner_block(member: PartyMemberState, option: dict[str, Any]) -> str:
    class_id = str(member.class_id or "").casefold()
    if class_id == "barbarian":
        return f"{member.name} is a Barbarian and cannot learn or cast the leprechauns' illusion spell."
    if any(str(spell).casefold() == str(option["name"]).casefold() for spell in member.spells):
        return f"{member.name} already knows {option['name']}."
    return ""


def teach_leprechaun_illusion_spell(
    session: SessionState,
    *,
    payer_character_id: str,
    learner_character_id: str,
    spell_name: str,
    spell_options: list[dict[str, Any]],
) -> dict[str, Any]:
    state = _open_state(session, "leprechaun")
    if isinstance(state.get("illusion_lesson"), dict) and state["illusion_lesson"].get("spell_name"):
        raise ValueError("The leprechauns teach only one illusion spell during this visit.")
    payer = _living_member(session, payer_character_id)
    learner = _living_member(session, learner_character_id)
    option = _spell_option(spell_options, spell_name)
    blocked = _spell_learner_block(learner, option)
    if blocked:
        raise ValueError(blocked)
    shoe_count = len(_shoe_assignments(state))
    cost = 0 if shoe_count >= 3 else 100
    paid, available, contributions = take_living_party_funds([payer], cost)
    if not paid:
        raise ValueError(f"{payer.name} needs {cost} gp in carried and banked funds (has {available} gp).")
    learner.spells.append(str(option["name"]))
    mark_tag_leprechaun_illusion_spell(learner, str(option["name"]))
    class_id = str(learner.class_id or "").casefold()
    spellcasting_class = is_spellcaster(learner) or class_id == "gnome"
    non_spellcaster = not spellcasting_class
    modifier_label = "+1" if non_spellcaster else "applicable class modifier"
    lesson = {
        "spell_name": str(option["name"]),
        "learner_character_id": learner.character_id,
        "learner_name": learner.name,
        "payer_character_id": payer.character_id,
        "payer_name": payer.name,
        "cost_gp": cost,
        "free_after_three_pairs": cost == 0,
        "source_tables": list(option.get("source_tables") or []),
        "non_spellcaster": non_spellcaster,
        "uses_per_adventure": 1,
        "spellcasting_modifier": modifier_label,
    }
    state["illusion_lesson"] = lesson
    _record_transaction(
        state,
        {
            "type": "illusion_lesson",
            **lesson,
            "payment": [
                {
                    "name": item.name,
                    "bank_gold": item.bank_gold,
                    "carried_gold": item.carried_gold,
                }
                for item in contributions
            ],
        },
    )
    price_text = "free after three shoe purchases" if cost == 0 else "100 gp"
    casting_text = (
        "As a non-spellcaster, the learner may cast this spell once per adventure at +1."
        if non_spellcaster
        else (
            "The spell uses the learner's applicable class modifier and prepared-spell lifecycle, "
            "including the EE p.76 Cleric Blessing-only exception."
        )
    )
    result_text = (
        f"{learner.name} automatically learns {option['name']} from the leprechauns for {price_text}; "
        f"no learning roll is required. {casting_text}"
    )
    state["result_text"] = result_text
    set_repeatable_service_state(session, state)
    session.log.append(f"Blackbird Hill lesson (TAG pp.25-26, Scene 2): {result_text}")
    return {
        "result_text": result_text,
        "changed_character_ids": sorted({payer.character_id, learner.character_id}),
        "state": state,
    }


def _learned_skill_ids(member: PartyMemberState) -> set[str]:
    return {
        str(item).strip().casefold().split(":", 1)[0]
        for item in member.learned_expert_skills or []
    }


def _deoldyn_outcome_block(
    session: SessionState,
    member: PartyMemberState,
    outcome: str,
    new_spell: str,
) -> str:
    allowed, reason = can_member_wield_weapon(member, "Bow")
    if not allowed:
        return reason or f"{member.name} cannot wield a bow."
    if outcome in DEOLDYN_SKILLS:
        if outcome in _learned_skill_ids(member):
            return f"{member.name} already knows {DEOLDYN_SKILLS[outcome][0]}."
        return ""
    if outcome != "level_up":
        return "Choose Deadly Accuracy, Dead Shot, or the base Elf level-up option."
    if str(member.class_id or "").casefold() != "elf":
        return "Only a normal Elf—not a Wood Elf or Fire Elf—may use Deoldyn's roll to advance a Level."
    if session.last_leveled_character_id == member.character_id:
        return f"{member.name} cannot level twice in succession in this adventure."
    gate = level_up_gate_reason(member, member.level + 1)
    if gate:
        return gate
    allowed_spells = {name.casefold(): name for name in available_level_up_spells(member.class_id)}
    if str(new_spell or "").strip().casefold() not in allowed_spells:
        return f"Choose the spell {member.name} will prepare if the level-up roll succeeds."
    return ""


def train_with_deoldyn(
    session: SessionState,
    *,
    trainings: list[dict[str, Any]],
    roller: Callable[[PartyMemberState], AdvancementRollResult] | None = None,
) -> dict[str, Any]:
    state = _open_state(session, "deoldyn")
    if state.get("training_batch_resolved") or state.get("training_results"):
        raise ValueError(
            "Deoldyn's simultaneous training batch has already been paid and rolled. Choose Done to finish the visit."
        )
    if not trainings:
        raise ValueError("Select at least one bow-capable character for Deoldyn's training batch.")
    prior_ids = {str(value) for value in state.get("trained_character_ids") or []}
    normalized: list[tuple[PartyMemberState, str, str, int]] = []
    seen: set[str] = set()
    for row in trainings:
        if not isinstance(row, dict):
            raise ValueError("Each Deoldyn training selection must name a character and outcome.")
        character_id = str(row.get("character_id") or "").strip()
        if not character_id or character_id in seen:
            raise ValueError("Each selected character may appear only once in a Deoldyn training batch.")
        if character_id in prior_ids:
            raise ValueError("Each character may train with Deoldyn only once between adventures.")
        member = _living_member(session, character_id)
        outcome = str(row.get("outcome") or "").strip().casefold()
        new_spell = str(row.get("new_spell") or "").strip()
        blocked = _deoldyn_outcome_block(session, member, outcome, new_spell)
        if blocked:
            raise ValueError(blocked)
        cost = 60 * max(1, int(member.level or 1))
        if _available_gold(member) < cost:
            raise ValueError(
                f"{member.name} needs {cost} gp for Deoldyn's training "
                f"(has {_available_gold(member)} gp in carried and banked funds)."
            )
        normalized.append((member, outcome, new_spell, cost))
        seen.add(character_id)

    payment_records: dict[str, list[dict[str, Any]]] = {}
    for member, _outcome, _new_spell, cost in normalized:
        paid, _available, contributions = take_living_party_funds([member], cost)
        if not paid:  # All affordability checks ran before any payment.
            raise RuntimeError("Validated Deoldyn payment unexpectedly failed.")
        payment_records[member.character_id] = [
            {
                "name": item.name,
                "bank_gold": item.bank_gold,
                "carried_gold": item.carried_gold,
            }
            for item in contributions
        ]

    roll_for = roller or (
        lambda member: roll_advancement(
            member.level,
            member=member,
            purpose="level_up",
        )
    )
    rolled = [
        (member, outcome, new_spell, cost, roll_for(member))
        for member, outcome, new_spell, cost in normalized
    ]
    results: list[dict[str, Any]] = []
    narrative: list[str] = []
    for member, outcome, new_spell, cost, roll in rolled:
        success = advancement_succeeds(roll, member.level)
        outcome_name = "normal Elf level advancement" if outcome == "level_up" else DEOLDYN_SKILLS[outcome][0]
        if success and outcome == "level_up":
            level_result = apply_level_up(member, new_spell=new_spell)
            session.log.extend(level_result.log)
            session.last_leveled_character_id = member.character_id
        elif success:
            if outcome not in _learned_skill_ids(member):
                member.learned_expert_skills.append(outcome)
            label = DEOLDYN_SKILLS[outcome][0]
            if label not in member.abilities:
                member.abilities.append(label)
            targets = dict(member.expert_skill_targets or {})
            targets[outcome] = DEOLDYN_SOURCE_MARKER
            member.expert_skill_targets = targets
        roll_text = (
            f"{roll.die_label}={roll.natural}"
            + (f"{roll.modifier:+d}={roll.total}" if roll.modifier else "")
            + f" vs Level {member.level - 1 if success and outcome == 'level_up' else member.level}"
        )
        result = {
            "character_id": member.character_id,
            "name": member.name,
            "outcome": outcome,
            "outcome_name": outcome_name,
            "cost_gp": cost,
            "roll": {
                "die_label": roll.die_label,
                "natural": roll.natural,
                "modifier": roll.modifier,
                "total": roll.total,
            },
            "success": success,
            "new_spell": new_spell if outcome == "level_up" else "",
            "payment": payment_records[member.character_id],
        }
        results.append(result)
        narrative.append(
            f"{member.name} pays {cost} gp and {('succeeds' if success else 'fails')} "
            f"the {outcome_name} XP roll ({roll_text})."
        )
        _record_transaction(state, {"type": "deoldyn_training", **result})

    state["trained_character_ids"] = sorted(
        prior_ids | {member.character_id for member, *_rest in normalized}
    )
    state["training_results"] = [
        *[dict(item) for item in state.get("training_results") or [] if isinstance(item, dict)],
        *results,
    ]
    state["training_batch_resolved"] = True
    result_text = (
        "Deoldyn takes every selected payment before rolling the batch. "
        + " ".join(narrative)
    )
    state["result_text"] = result_text
    set_repeatable_service_state(session, state)
    session.log.append(f"Deoldyn's range (TAG p.26, Scene 3): {result_text}")
    return {
        "result_text": result_text,
        "changed_character_ids": sorted(seen),
        "results": results,
        "state": state,
    }


def finish_repeatable_service(session: SessionState) -> dict[str, Any]:
    kind = repeatable_service_kind(session)
    if kind not in {"leprechaun", "deoldyn"}:
        raise ValueError("No repeatable Adventures Guild service is active.")
    state = repeatable_service_state(session)
    if str(state.get("phase") or "") == "resolved":
        return state
    state.setdefault("kind", kind)
    state.setdefault("transactions", [])
    if kind == "leprechaun":
        shoes = len(_shoe_assignments(state))
        lesson = state.get("illusion_lesson") if isinstance(state.get("illusion_lesson"), dict) else {}
        lesson_text = (
            f" {lesson.get('learner_name')} learned {lesson.get('spell_name')}."
            if lesson.get("spell_name")
            else " No spell lesson was taken."
        )
        result_text = (
            f"The party finishes the Blackbird Hill bargain after buying {shoes} pair(s) of Shoes of Fast Walk."
            f"{lesson_text}"
        )
    else:
        results = [dict(item) for item in state.get("training_results") or [] if isinstance(item, dict)]
        successes = sum(1 for item in results if item.get("success"))
        result_text = (
            f"The party finishes at Deoldyn's range after {len(results)} training attempt(s); "
            f"{successes} succeeded."
        )
    state.update(
        {
            "phase": "resolved",
            "resolved": True,
            "result_text": result_text,
            "updated_at": now_utc(),
        }
    )
    set_repeatable_service_state(session, state)
    session.log.append(result_text)
    return state


def shoes_of_fast_walk_defense_bonus(
    member: PartyMemberState,
    session: SessionState | None,
    *,
    escaping_melee: bool,
) -> int:
    if not escaping_melee:
        return 0
    allowed, _reason = can_class_use_item(
        member.class_id,
        {"category": "magic_item", "magic": True},
    )
    if not allowed:
        return 0
    if session is not None:
        state = repeatable_service_state(session)
        if not _has_wearable_shoes(member, session, state):
            return 0
    elif _shoe_count(member) <= 0:
        return 0
    return tier_for_level(member.level)


def shoes_of_fast_walk_hireling_defense_bonus(
    hireling: HirelingState,
    session: SessionState | None,
    *,
    escaping_melee: bool,
) -> int:
    """Apply the player-confirmed party Tier when an assigned hireling defends while escaping."""
    if not escaping_melee or session is None or hireling.life <= 0:
        return 0
    state = repeatable_service_state(session)
    if not _hireling_assignment_has_accessible_pair(session, state, hireling.id):
        return 0
    return _current_party_tier(session)


def repeatable_service_view(
    session: SessionState,
    dungeon_tables: dict[str, Any],
    expert_catalog: dict[str, Any],
) -> dict[str, Any]:
    kind = repeatable_service_kind(session)
    if not kind:
        return {}
    state = repeatable_service_state(session)
    phase = str(state.get("phase") or "open")
    living = [member for member in session.party if member.current_life > 0]
    view: dict[str, Any] = {
        **state,
        "kind": kind,
        "phase": phase,
        "resolved": phase == "resolved",
        "payers": [
            {
                "character_id": member.character_id,
                "name": member.name,
                **_gold_breakdown(member),
            }
            for member in living
        ],
    }
    if kind == "leprechaun":
        assignments = _shoe_assignments(state)
        view.update(
            {
                "shoe_pair_count": len(assignments),
                "lesson_cost_gp": 0 if len(assignments) >= 3 else 100,
                "lesson_used": bool(
                    isinstance(state.get("illusion_lesson"), dict)
                    and state["illusion_lesson"].get("spell_name")
                ),
                "hero_recipients": [],
                "hireling_recipients": [],
            }
        )
        for member in living:
            allowed, reason = can_class_use_item(
                member.class_id,
                {"category": "magic_item", "magic": True},
            )
            already = _has_wearable_shoes(member, session, state) or _assigned_recipient(
                state, "hero", member.character_id
            )
            view["hero_recipients"].append(
                {
                    "recipient_kind": "hero",
                    "recipient_id": member.character_id,
                    "name": member.name,
                    "eligible": bool(allowed and not already),
                    "blocked_reason": (
                        f"{member.name} already has a pair."
                        if already
                        else (reason or "")
                    ),
                }
            )
        for hireling in session.hirelings or []:
            if hireling.life <= 0:
                continue
            already = _assigned_recipient(state, "hireling", hireling.id)
            view["hireling_recipients"].append(
                {
                    "recipient_kind": "hireling",
                    "recipient_id": hireling.id,
                    "name": hireling.name,
                    "eligible": not already,
                    "blocked_reason": "This hireling already has a pair." if already else "",
                }
            )
        options = tag_illusion_spell_options(session, dungeon_tables, expert_catalog)
        for option in options:
            option["eligible_character_ids"] = [
                member.character_id
                for member in living
                if not _spell_learner_block(member, option)
            ]
        view["spell_options"] = options
    else:
        trained = {str(value) for value in state.get("trained_character_ids") or []}
        batch_resolved = bool(state.get("training_batch_resolved") or state.get("training_results"))
        view["training_batch_resolved"] = batch_resolved
        trainees: list[dict[str, Any]] = []
        for member in living:
            allowed, reason = can_member_wield_weapon(member, "Bow")
            outcomes: list[dict[str, Any]] = []
            if not batch_resolved and allowed and member.character_id not in trained:
                for skill_id, (label, summary) in DEOLDYN_SKILLS.items():
                    if skill_id not in _learned_skill_ids(member):
                        outcomes.append({"id": skill_id, "label": label, "summary": summary})
                if str(member.class_id or "").casefold() == "elf":
                    gate = level_up_gate_reason(member, member.level + 1)
                    if session.last_leveled_character_id == member.character_id:
                        gate = f"{member.name} cannot level twice in succession in this adventure."
                    if not gate:
                        outcomes.append(
                            {
                                "id": "level_up",
                                "label": "Normal Elf level advancement",
                                "summary": "Use Deoldyn's XP roll to advance one Level instead of learning an archery skill.",
                                "spell_choices": available_level_up_spells(member.class_id),
                            }
                        )
            cost = 60 * max(1, int(member.level or 1))
            blocked = ""
            if batch_resolved:
                blocked = "The simultaneous training batch has already been paid and rolled; choose Done."
            elif not allowed:
                blocked = reason or f"{member.name} cannot wield a bow."
            elif member.character_id in trained:
                blocked = "Already trained with Deoldyn in this adventure."
            elif not outcomes:
                blocked = "No new eligible Deoldyn outcome remains for this character."
            elif _available_gold(member) < cost:
                blocked = f"Needs {cost} gp; has {_available_gold(member)} gp."
            trainees.append(
                {
                    "character_id": member.character_id,
                    "name": member.name,
                    "class_id": member.class_id,
                    "level": member.level,
                    "cost_gp": cost,
                    **_gold_breakdown(member),
                    "eligible": not blocked,
                    "blocked_reason": blocked,
                    "outcomes": outcomes,
                }
            )
        view["trainees"] = trainees
    return view
