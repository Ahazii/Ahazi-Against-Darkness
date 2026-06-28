"""TAG campaign shell — persistent settlement/downtime state (TAG p.9–15, p.23–24)."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING

from ..db import now_utc
from ..schemas import (
    CampaignState,
    Character,
    SessionState,
    TagAvailabilityCheckState,
    TagDowntimeLogEntry,
    TagTravelLogEntry,
)
from .abyss_tables import is_abyss_profile
from .dice import roll_d6

if TYPE_CHECKING:
    from ..db import Store

DEFAULT_CAMPAIGN_ID = "default"
TAG_LOG_LIMIT = 20

FIGHTING_CLASS_IDS = {
    "barbarian",
    "dwarf",
    "halfling",
    "monk",
    "paladin",
    "ranger",
    "warrior",
}
ROGUE_SAVE_CLASS_IDS = {"assassin", "rogue", "swashbuckler"}
INTERROGATION_CLASS_IDS = {"atrocity", "cambion", "inquisitor", "investigator", "sleuth", "witch_hunter"}


def default_campaign() -> CampaignState:
    timestamp = now_utc()
    return CampaignState(
        id=DEFAULT_CAMPAIGN_ID,
        tag_banking_enabled=False,
        days_passed=0,
        adventures_completed=0,
        created_at=timestamp,
        updated_at=timestamp,
    )


def settlement_size_from_roll(roll: int) -> int:
    """TAG p.9 d6 settlement size: 1=-2, 2=-1, 3=0, 4=+1, 5=+2, 6=+3."""
    if roll <= 1:
        return -2
    if roll >= 6:
        return 3
    return roll - 3


def trim_tag_logs(campaign: CampaignState) -> CampaignState:
    campaign.tag_availability_checks = campaign.tag_availability_checks[-TAG_LOG_LIMIT:]
    campaign.tag_downtime_log = campaign.tag_downtime_log[-TAG_LOG_LIMIT:]
    campaign.tag_travel_log = campaign.tag_travel_log[-TAG_LOG_LIMIT:]
    return campaign


def roll_3d6() -> tuple[int, list[int]]:
    rolls = [roll_d6(), roll_d6(), roll_d6()]
    return sum(rolls), rolls


def update_settlement(
    campaign: CampaignState,
    *,
    name: str | None = None,
    size: int | None = None,
    notes: str | None = None,
) -> CampaignState:
    if name is not None:
        campaign.settlement_name = (name.strip() or "Home Settlement")[:80]
    if size is not None:
        campaign.settlement_size = max(-3, min(3, int(size)))
    if notes is not None:
        campaign.settlement_notes = notes.strip()[:1000]
    return campaign


def roll_settlement_size(campaign: CampaignState) -> tuple[CampaignState, int]:
    roll = roll_d6()
    campaign.settlement_size = settlement_size_from_roll(roll)
    return campaign, roll


def travel_to_new_settlement(
    campaign: CampaignState,
    *,
    destination_name: str | None = None,
    use_hex_map: bool = False,
    pay_road_tithe: bool = False,
) -> TagTravelLogEntry:
    from_name = campaign.settlement_name or "Home Settlement"
    to_name = (destination_name or "").strip()[:80] or "New Settlement"
    size_roll = roll_d6()
    new_size = settlement_size_from_roll(size_roll)
    direction_roll = None
    distance_hexes = None
    road_roll = None
    road_exists = None
    road_tithe = 0
    if use_hex_map:
        direction_roll = roll_d6()
        distance_total, distance_rolls = roll_3d6()
        distance_hexes = max(1, distance_total - 2)
        road_total, road_rolls = roll_3d6()
        road_roll = road_total
        road_exists = road_total > distance_hexes
        travel_rolls = distance_rolls + road_rolls
        days = distance_hexes
        if road_exists and pay_road_tithe:
            road_tithe = ceil(distance_hexes / 3)
            encounter_checks = ceil(distance_hexes / 3)
            route_text = (
                f"road exists on {road_total} > {distance_hexes}; road tithe cost is {road_tithe} gp, "
                f"check 1-in-6 encounter every 3 hexes ({encounter_checks} check(s))"
            )
        else:
            encounter_checks = distance_hexes
            route_text = (
                f"{'road exists' if road_exists else 'no road'}; traveling as wilderness, "
                f"check 1-in-6 encounter per hex ({encounter_checks} check(s))"
            )
        result = (
            f"Moved from {from_name} to {to_name}: direction roll {direction_roll}, "
            f"{distance_hexes} hex/day(s), {route_text}. New settlement size {new_size:+d}."
        )
    else:
        total, rolls = roll_3d6()
        travel_rolls = rolls
        days = max(1, total - 3)
        encounter_checks = 0
        result = f"Moved from {from_name} to {to_name}: {days} day(s) travel. New settlement size {new_size:+d}."
    campaign.settlement_name = to_name
    campaign.settlement_size = new_size
    campaign.days_passed += days
    entry = TagTravelLogEntry(
        from_settlement=from_name,
        to_settlement=to_name,
        days=days,
        travel_rolls=travel_rolls,
        settlement_size_roll=size_roll,
        new_settlement_size=new_size,
        use_hex_map=use_hex_map,
        direction_roll=direction_roll,
        distance_hexes=distance_hexes,
        road_roll=road_roll,
        road_exists=road_exists,
        road_tithe_paid_gp=road_tithe,
        encounter_checks=encounter_checks,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_travel_log.append(entry)
    trim_tag_logs(campaign)
    return entry


def check_item_availability(
    campaign: CampaignState,
    *,
    item_name: str,
    difficulty: int = 6,
    base_price_gp: int | None = None,
) -> TagAvailabilityCheckState:
    clean_name = (item_name.strip() or "Unnamed item")[:100]
    target = max(1, int(difficulty))
    price = None if base_price_gp is None else max(0, int(base_price_gp))
    roll = roll_d6()
    total = roll + campaign.settlement_size
    final_price = price
    if total >= target:
        outcome = "available"
        result = f"{clean_name} is available at the standard asking price."
    elif total == target - 1:
        outcome = "surcharge"
        final_price = ceil(price * 1.2) if price is not None else None
        result = f"{clean_name} is available with a 20% surcharge."
    else:
        outcome = "unavailable"
        final_price = None
        result = f"{clean_name} is unavailable; try again after one adventure."
    check = TagAvailabilityCheckState(
        item_name=clean_name,
        difficulty=target,
        base_price_gp=price,
        final_price_gp=final_price,
        roll=roll,
        settlement_size=campaign.settlement_size,
        total=total,
        outcome=outcome,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_availability_checks.append(check)
    trim_tag_logs(campaign)
    return check


def streetwise_modifier(character: Character, *, action: str = "look_for_clues") -> int:
    class_id = (character.class_id or character.class_name or "").lower().replace(" ", "_").replace("-", "_")
    class_name = (character.class_name or "").lower()
    if class_id in ROGUE_SAVE_CLASS_IDS or any(name in class_name for name in ("rogue", "swashbuckler", "assassin")):
        return character.level
    if action == "interrogation" and (
        class_id in INTERROGATION_CLASS_IDS
        or any(name in class_name for name in ("witch", "cambion", "atrocity", "sleuth", "investigator", "inquisitor"))
    ):
        return character.level
    if class_id == "halfling" or "halfling" in class_name:
        return -1
    if class_id in FIGHTING_CLASS_IDS or character.attack_bonus > 0:
        return 1
    return 0


def look_for_clues(
    campaign: CampaignState,
    character: Character,
    *,
    natural_one_consequence: str = "gold",
) -> TagDowntimeLogEntry:
    bribe_cost = roll_d6()
    character.gold = max(0, character.gold - bribe_cost)
    roll = roll_d6()
    modifier = streetwise_modifier(character, action="look_for_clues")
    total = roll + modifier
    if roll == 1:
        if character.clues > 0:
            character.clues -= 1
            result = f"{character.name} rolled a natural 1 and lost 1 Clue."
        elif natural_one_consequence == "life":
            character.current_life = max(0, character.current_life - 1)
            result = f"{character.name} rolled a natural 1 and lost 1 Life."
        else:
            extra_loss = roll_d6() + roll_d6() + roll_d6()
            character.gold = max(0, character.gold - extra_loss)
            result = f"{character.name} rolled a natural 1 and lost {extra_loss} gp."
    elif total >= 6:
        character.clues += 1
        result = f"{character.name} gained 1 Clue."
    else:
        result = f"{character.name} found no useful clue."
    character.updated_at = now_utc()
    entry = TagDowntimeLogEntry(
        action="look_for_clues",
        character_id=character.id,
        character_name=character.name,
        roll=roll,
        modifier=modifier,
        total=total,
        cost_gp=bribe_cost,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_downtime_log.append(entry)
    trim_tag_logs(campaign)
    return entry


def load_campaign(store: Store) -> CampaignState:
    campaign = store.get("campaigns", DEFAULT_CAMPAIGN_ID, CampaignState.model_validate)
    if campaign is None:
        campaign = default_campaign()
        store.save("campaigns", campaign)
    return campaign


def save_campaign(store: Store, campaign: CampaignState) -> CampaignState:
    campaign.updated_at = now_utc()
    store.save("campaigns", campaign)
    return campaign


def apply_abyss_campaign_to_session(store: Store, session: SessionState) -> SessionState:
    if not is_abyss_profile(session):
        return session
    campaign = load_campaign(store)
    if campaign.abyss_campaign_plot is not None:
        plot = campaign.abyss_campaign_plot.model_copy(deep=True)
        if not plot.completed:
            plot.entity_piece_claimed_this_adventure = False
            session.abyss_campaign_plot = plot
    if campaign.abyss_vampire_sire is not None:
        session.abyss_vampire_sire = campaign.abyss_vampire_sire.model_copy(deep=True)
    return session


def sync_abyss_campaign_from_session(store: Store, session: SessionState) -> CampaignState:
    campaign = load_campaign(store)
    if not is_abyss_profile(session):
        return campaign
    plot = session.abyss_campaign_plot
    if plot is not None:
        copied = plot.model_copy(deep=True)
        if copied.completed:
            already_recorded = any(
                existing.key == copied.key
                and existing.completed
                and existing.progress == copied.progress
                and existing.final_bosses_defeated == copied.final_bosses_defeated
                and existing.gold_contributed == copied.gold_contributed
                and existing.artifact_clues_spent == copied.artifact_clues_spent
                for existing in campaign.abyss_campaign_completed_plots
            )
            if not already_recorded:
                campaign.abyss_campaign_completed_plots.append(copied)
            campaign.abyss_campaign_plot = None
        else:
            campaign.abyss_campaign_plot = copied
    campaign.abyss_vampire_sire = (
        session.abyss_vampire_sire.model_copy(deep=True)
        if session.abyss_vampire_sire is not None
        else None
    )
    return save_campaign(store, campaign)


def record_adventure_complete(store: Store) -> CampaignState:
    campaign = load_campaign(store)
    campaign.adventures_completed += 1
    campaign.days_passed += 1
    return save_campaign(store, campaign)
