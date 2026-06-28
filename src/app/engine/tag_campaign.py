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
TAG_SETTLEMENT_SERVICES = [
    {
        "key": "bank_account",
        "name": "Bank account",
        "source_page": 9,
        "min_size": -3,
        "cost": "10% one-time deposit fee, rounded up",
        "summary": "Coins, gems, jewelry and magic treasure may be banked under one character's name.",
        "automation": "Use existing home/camp bank controls; TAG fee/robbery roll still needs per-account automation.",
    },
    {
        "key": "bank_inheritance",
        "name": "Bank inheritance setup",
        "source_page": 9,
        "min_size": -3,
        "cost": "20% inheritance tax, rounded up, when transferred",
        "summary": "Sane characters may set heirs for bank savings if the account owner dies.",
        "automation": "Reference only; per-account inheritance transfer is not automated yet.",
    },
    {
        "key": "magic_locker",
        "name": "Magic locker",
        "source_page": 10,
        "min_size": 0,
        "cost": "50 gp per locker",
        "summary": "Store one item or up to 5000 gp; summon during an adventure on 3d6, mishap on 6 or less.",
        "automation": "Availability shown here; locker inventory/summon workflow is not automated yet.",
    },
    {
        "key": "platinum_exchange",
        "name": "Platinum exchange",
        "source_page": 10,
        "min_size": 3,
        "cost": "1 PP = 20 gp",
        "summary": "Size +3 settlements sell platinum; size +2 accepts it; smaller settlements accept only for church donations.",
        "automation": "Reference only; PP currency is not tracked separately yet.",
    },
    {
        "key": "hidden_treasure_trove",
        "name": "Hidden treasure trove",
        "source_page": 11,
        "min_size": -3,
        "cost": "No bank fee; risk roll between adventures",
        "summary": "Cache treasure outside a bank; roll 3d6 between adventures, stolen on 3-5.",
        "automation": "Risk roll is automated; cache contents are tracked manually for now.",
    },
    {
        "key": "resurrection_blessing_tags",
        "name": "Resurrection and Blessing tags",
        "source_page": 11,
        "min_size": -3,
        "cost": "500 gp resurrection tag; 80 gp Blessing tag",
        "summary": "Prepaid temple tags tied to the wearer; not subject to availability rolls.",
        "automation": "Reference only; tag inventory redemption is not automated yet.",
    },
    {
        "key": "gems_jewelry_conversion",
        "name": "Gems and jewelry conversion",
        "source_page": 13,
        "min_size": -3,
        "cost": "10% value loss unless the buyer is a dwarf",
        "summary": "Convert gold into negligible-weight gems or jewelry; jewelry above 500 gp requires L6 availability.",
        "automation": "Reference row; use Check availability here for single jewelry pieces above 500 gp.",
        "availability_difficulty": 6,
        "availability_price_gp": 501,
        "availability_item_name": "Jewelry above 500 gp",
    },
    {
        "key": "bag_of_carrying",
        "name": "Bag of Carrying",
        "source_page": 13,
        "min_size": -3,
        "cost": "200 gp",
        "summary": "Magic bag carries any weight that fits through the opening; lost bag loses all contents.",
        "automation": "Availability roll is automated; purchase/contents tracking remains manual.",
        "availability_difficulty": 6,
        "availability_price_gp": 200,
        "availability_item_name": "Bag of Carrying",
    },
    {
        "key": "ten_foot_pole",
        "name": "10-foot pole",
        "source_page": 14,
        "min_size": -3,
        "cost": "2 gp",
        "summary": "Two-handed pole; trap/Search benefits when held, one pole-user at a time in dungeons.",
        "automation": "Reference row; item can be purchased in any settlement and may be crafted in forested areas.",
    },
    {
        "key": "lantern_hook",
        "name": "Lantern hook",
        "source_page": 14,
        "min_size": -3,
        "cost": "2 gp",
        "summary": "Shield hook lets a lantern hang without occupying a hand while the shield is wielded.",
        "automation": "Reference row; shield/lantern equipment workflow remains manual.",
    },
    {
        "key": "very_nutritious_food",
        "name": "Very nutritious food",
        "source_page": 14,
        "min_size": -3,
        "cost": "20 gp feeds 4 characters and a 5th companion/henchman",
        "summary": "First failed Save, Attack or Defense roll in the first combat after eating may be rerolled.",
        "automation": "Reference row; L4 availability is needed only in desert or frozen/Arctic environments.",
        "availability_difficulty": 4,
        "availability_price_gp": 20,
        "availability_item_name": "Very nutritious food in desert/frozen environment",
    },
    {
        "key": "poison_resistance_training",
        "name": "Poison resistance training",
        "source_page": 15,
        "min_size": -3,
        "cost": "20 gp per character",
        "summary": "Reroll first failed Save vs poison next adventure; before play, Tier die 1 starts at -1 Life.",
        "automation": "Reference row; next-adventure training state is not automated yet.",
    },
]

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


def settlement_service_rows(campaign: CampaignState) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    size = campaign.settlement_size
    for service in TAG_SETTLEMENT_SERVICES:
        key = str(service["key"])
        status = "available" if size >= int(service["min_size"]) else "unavailable"
        if key == "platinum_exchange" and size == 2:
            status = "accepted_only"
        if key == "platinum_exchange" and size < 2:
            status = "church_only"
        rows.append(
            {
                **service,
                "status": status,
                "status_text": tag_service_status_text(key, status, size),
            }
        )
    return rows


def tag_service_status_text(key: str, status: str, size: int) -> str:
    if key == "platinum_exchange":
        if status == "available":
            return f"Available in this size {size:+d} settlement: gold may be converted to PP."
        if status == "accepted_only":
            return "Limited: PP is accepted here, but cannot be bought."
        return "Limited: PP accepted only for church donations such as resurrection or Blessing."
    if status == "available":
        return f"Available in this size {size:+d} settlement."
    return f"Unavailable: requires settlement size {next(s['min_size'] for s in TAG_SETTLEMENT_SERVICES if s['key'] == key):+d} or larger."


def roll_hidden_treasure_trove_risk(campaign: CampaignState) -> TagDowntimeLogEntry:
    total, rolls = roll_3d6()
    if total <= 5:
        result = (
            f"Hidden treasure trove risk roll {total} ({'+'.join(str(roll) for roll in rolls)}): "
            "the cache is discovered and stolen. Spend 4 Clues and pass Interrogation vs L6 to recover it."
        )
    else:
        result = f"Hidden treasure trove risk roll {total} ({'+'.join(str(roll) for roll in rolls)}): the cache remains safe."
    entry = TagDowntimeLogEntry(
        action="hidden_treasure_trove_risk",
        roll=total,
        total=total,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_downtime_log.append(entry)
    trim_tag_logs(campaign)
    return entry


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
