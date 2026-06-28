"""TAG campaign shell — persistent settlement/downtime state (TAG p.9–15, p.23–24)."""

from __future__ import annotations

from math import ceil
from typing import TYPE_CHECKING
from uuid import uuid4

from ..db import now_utc
from ..schemas import (
    CampaignState,
    Character,
    SessionState,
    TagAvailabilityCheckState,
    TagDowntimeLogEntry,
    TagMagicLockerState,
    TagStoredItemState,
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
    {
        "key": "martial_arts_training",
        "name": "Martial arts training",
        "source_page": 15,
        "min_size": -3,
        "cost": "25 gp, or free for Adventurers' Guild members",
        "summary": "Next adventure barehanded attacks are at -1 instead of -2; guild training risks Tier die 1 injury.",
        "automation": "Reference row; next-adventure training state is not automated yet.",
    },
    {
        "key": "gambling_house",
        "name": "Gambling house",
        "source_page": 15,
        "min_size": -3,
        "cost": "Variable stake",
        "summary": "Choose a budget and roll d10 on the Gambling House Table; rogue-like gamblers add +1.",
        "automation": "Reference row; Gambling House Table resolution remains manual.",
    },
    {
        "key": "treasure_maps",
        "name": "Treasure maps",
        "source_page": 16,
        "min_size": -3,
        "cost": "5d6 gp, exploding sixes",
        "summary": "Buy a map of uncertain authenticity; following it rolls on the treasure map table.",
        "automation": "Price roll is automated; following-map table resolution remains manual.",
        "action": "treasure_map_price",
    },
    {
        "key": "moneylenders",
        "name": "Moneylenders",
        "source_page": 16,
        "min_size": -3,
        "cost": "20% interest; troupe credit limit is 2000 gp plus 200 gp per settlement size",
        "summary": "Borrow up to 1000 gp per character; missed repayment brings enforcers and possible pursuit after moving.",
        "automation": "Credit limit and pursuit chance are shown; loan ledger/combat enforcement remains manual.",
        "action": "moneylender_follow",
    },
    {
        "key": "good_boots",
        "name": "Good boots",
        "source_page": 17,
        "min_size": -3,
        "cost": "6 gp; 20 gp for very large creatures",
        "summary": "+2 Saves vs foot traps/dangers and +1 Defense vs monsters that attack feet.",
        "automation": "Reference row; boot wear/replacement after 20 adventures is not automated.",
    },
    {
        "key": "flammable_oil",
        "name": "Flask of flammable oil",
        "source_page": 17,
        "min_size": -3,
        "cost": "5 gp; one carried per character",
        "summary": "One action with a live flame; d6 throw can splash a friend, waste, or deal fire damage.",
        "automation": "Throw result roll is automated here; target selection/damage application remains manual.",
        "action": "flammable_oil_throw",
    },
    {
        "key": "horn",
        "name": "Horn",
        "source_page": 18,
        "min_size": -3,
        "cost": "2 gp; may be crafted from suitable horned creatures",
        "summary": "Sounding takes 1 turn; party gains +1 to next melee Attack, then roll 2-in-6 for wandering monsters.",
        "automation": "Wandering-monster attraction roll is automated; attack-bonus state remains manual.",
        "action": "horn_attract",
    },
    {
        "key": "wineskin",
        "name": "Wineskin",
        "source_page": 18,
        "min_size": -3,
        "cost": "First wineskin free; 4 gp refill per adventure",
        "summary": "+1 wooing and fear/terror Saves, but -1 spellcasting, -2 puzzles, and -1 other Saves while drinking.",
        "automation": "Reference row; tipsy status tracking is not automated yet.",
    },
    {
        "key": "flail_axe",
        "name": "Flail-Axe",
        "source_page": 18,
        "min_size": -3,
        "cost": "8 gp",
        "summary": "One-handed slashing weapon with two-handed +1 Attack advantage; natural 1 hits the user for 1 Life.",
        "automation": "Reference row; weapon purchase/combat self-hit automation remains deferred.",
    },
    {
        "key": "aspergillum",
        "name": "Aspergillum",
        "source_page": 19,
        "min_size": -3,
        "cost": "20 gp, plus holy water; 8 gp repair",
        "summary": "Light silver crushing weapon with holy-water reservoir; on Attack roll 1, roll 2-in-6 break chance.",
        "automation": "Break chance roll is automated; weapon/holy-water combat integration remains manual.",
        "action": "aspergillum_break",
    },
    {
        "key": "availability_rolls",
        "name": "Availability Rolls",
        "source_page": 19,
        "min_size": -3,
        "cost": "No cost unless item is available",
        "summary": "Special TAG items roll d6 plus settlement size vs difficulty; fail-by-1 adds 20% surcharge.",
        "automation": "Use the Check availability controls above or row-level availability buttons.",
    },
    {
        "key": "streetwise_rules",
        "name": "Streetwise Rules",
        "source_page": 20,
        "min_size": -3,
        "cost": "Depends on action; Look for Clues costs d6 gp bribes",
        "summary": "Town underworld Saves for clues, interrogation, rumors and similar actions, with class modifiers.",
        "automation": "Look for Clue is automated above; interrogation and other Streetwise actions remain future work.",
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

TAG_PURCHASABLE_SERVICES: dict[str, dict[str, object]] = {
    "resurrection_tag": {
        "label": "Resurrection tag",
        "cost_gp": 500,
        "inventory": "TAG Resurrection tag",
        "result": "prepaid resurrection tag added to inventory",
    },
    "blessing_tag": {
        "label": "Blessing tag",
        "cost_gp": 80,
        "inventory": "TAG Blessing tag",
        "result": "prepaid Blessing tag added to inventory",
    },
    "bag_of_carrying": {
        "label": "Bag of Carrying",
        "cost_gp": 200,
        "inventory": "Bag of Carrying",
        "result": "Bag of Carrying added to inventory",
    },
    "ten_foot_pole": {
        "label": "10-foot pole",
        "cost_gp": 2,
        "inventory": "10-foot pole",
        "result": "10-foot pole added to inventory",
    },
    "lantern_hook": {
        "label": "Lantern hook",
        "cost_gp": 2,
        "inventory": "Lantern hook",
        "result": "Lantern hook added to inventory",
    },
    "very_nutritious_food": {
        "label": "Very nutritious food",
        "cost_gp": 20,
        "inventory": "Very nutritious food",
        "result": "Very nutritious food added to inventory",
    },
    "poison_resistance_training": {
        "label": "Poison resistance training",
        "cost_gp": 20,
        "status": "TAG poison resistance training",
        "result": "next-adventure poison resistance training recorded",
    },
    "martial_arts_training": {
        "label": "Martial arts training",
        "cost_gp": 25,
        "status": "TAG martial arts training",
        "result": "next-adventure martial arts training recorded",
    },
    "good_boots": {
        "label": "Good boots",
        "cost_gp": 6,
        "inventory": "Good boots",
        "result": "good boots added to inventory",
    },
    "flammable_oil": {
        "label": "Flask of flammable oil",
        "cost_gp": 5,
        "inventory": "Flask of flammable oil",
        "result": "flammable oil added to inventory",
    },
    "horn": {
        "label": "Horn",
        "cost_gp": 2,
        "inventory": "Horn",
        "result": "horn added to inventory",
    },
    "wineskin": {
        "label": "Wineskin refill",
        "cost_gp": 4,
        "inventory": "Wineskin",
        "result": "wineskin/refill added to inventory",
    },
    "flail_axe": {
        "label": "Flail-Axe",
        "cost_gp": 8,
        "inventory": "Flail-Axe",
        "result": "Flail-Axe added to inventory",
    },
    "aspergillum": {
        "label": "Aspergillum",
        "cost_gp": 20,
        "inventory": "Aspergillum",
        "result": "aspergillum added to inventory",
    },
}

TAG_RUMORS: dict[int, str] = {
    1: "Bofto's strange star-shaped vineyard find: investigate Scene 9.",
    2: "Medusa in the hunter's cabin: investigate Scene 10.",
    3: "Stolen paladin sword at the old miller's farm: investigate Scene 11.",
    4: "Mutant fish under the bridge: investigate Scene 12.",
    5: "Dragon living in disguise: investigate Scene 13.",
    6: "Leprechauns at Blackbird Hill: investigate Scene 2.",
    7: "Secret temple stair under Tamas Zeya: investigate Scene 15.",
    8: "Shaura and the chaos cultists: investigate Scene 16.",
    9: "Daroc's lost cat familiar: investigate Scene 5.",
    10: "Winged things over the burgomaster's house: investigate Scene 8.",
    11: "Deoldyn's elven archery training: investigate Scene 3.",
    12: "Shinta's magic sword Agaratha: investigate Scene 4.",
}

TAG_RED_HERRINGS: dict[int, str] = {
    1: "Trap: single character ambushed by Riff-Raff; surrender carried goods or fight without withdrawal.",
    2: "Trap: single character ambushed by Riff-Raff; surrender carried goods or fight without withdrawal.",
    3: "Waste of time: lose d3 days.",
    4: "Waste of time: lose d3 days.",
    5: "False information: lose 1 Clue if possible, otherwise choose d6 gp or d3 days.",
    6: "Hidden-ruins detour: play a d6-room dungeon with no Final Boss and +1 minion/vermin counts.",
}

TAG_TREASURE_MAP_RESULTS: dict[int, str] = {
    1: "Deathtrap: party ambushed by Riff-Raff; surrender carried goods or fight, foes go first, no withdrawal.",
    2: "Deathtrap: party ambushed by Riff-Raff; surrender carried goods or fight, foes go first, no withdrawal.",
    3: "Waste of time: map leads nowhere; roll 3-in-6 for an Outside of Town Opposition encounter.",
    4: "Incomplete but accurate: gain a one-time +1 bonus for a future treasure-map roll.",
    5: "The Real Deal: roll on The Map Leads To table.",
    6: "The Real Deal: roll on The Map Leads To table.",
}

TAG_MAP_LEADS_TO: dict[int, str] = {
    1: "Underground caves: 4AD dungeon, d6+3 rooms, last room has a boosted Boss and double maximum treasure.",
    2: "Forgotten temple: chaos cultists, no withdrawal, golden idol worth 1d3x100 gp plus cultist treasure.",
    3: "Hostile humanoid camp: report for 4d6 gp or attempt stealth theft/fight the camp.",
    4: "Underground structure: 2d6 rooms/corridors, all generated treasure accumulates on the final Boss.",
    5: "Boss-only underground structure: as result 4, but every monster is a Boss; final treasure minimum 200 gp and 2 magic items.",
    6: "Lich sepulchral chamber: one-room undead fight with death-magic entry Save and phylactery attack option.",
}

TAG_MINOR_UNIQUE_QUESTS: dict[int, str] = {
    1: "Clean Up My Castle",
    2: "Gorungar the Mighty",
    3: "Griffin Omelets, Anyone?",
    4: "A Portrait in Red",
    5: "Sewers Search",
    6: "Monoceros Hunt",
}

TAG_THEMATIC_DUNGEONS: dict[int, str] = {
    1: "Ghastly Mine",
    2: "Giant's Lair",
    3: "Dragon's Lair",
    4: "Fiendish Abyss",
    5: "Minotaur Maze",
    6: "Bandit Hideout",
}


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


def roll_exploding_d6(count: int) -> tuple[int, list[int]]:
    rolls: list[int] = []
    total = 0
    for _ in range(count):
        roll = roll_d6()
        rolls.append(roll)
        total += roll
        while roll == 6:
            roll = roll_d6()
            rolls.append(roll)
            total += roll
    return total, rolls


def roll_d3() -> int:
    return ceil(roll_d6() / 2)


def roll_d10() -> int:
    value = 11
    while value > 10:
        value = ((roll_d6() - 1) * 2) + (1 if roll_d6() <= 3 else 2)
    return value


def roll_d12() -> int:
    return ((roll_d6() - 1) * 2) + (1 if roll_d6() <= 3 else 2)


def append_tag_log(
    campaign: CampaignState,
    *,
    action: str,
    result_text: str,
    character: Character | None = None,
    roll: int | None = None,
    modifier: int = 0,
    total: int | None = None,
    cost_gp: int = 0,
) -> TagDowntimeLogEntry:
    entry = TagDowntimeLogEntry(
        action=action,
        character_id=character.id if character is not None else None,
        character_name=character.name if character is not None else None,
        roll=roll,
        modifier=modifier,
        total=total,
        cost_gp=max(0, int(cost_gp)),
        result_text=result_text,
        created_at=now_utc(),
    )
    campaign.tag_downtime_log.append(entry)
    trim_tag_logs(campaign)
    return entry


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
        row = {
            **service,
            "status": status,
            "status_text": tag_service_status_text(key, status, size),
        }
        if key == "moneylenders":
            row["credit_limit_gp"] = 2000 + (200 * size)
        rows.append(
            row
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


def roll_treasure_map_price(campaign: CampaignState) -> TagDowntimeLogEntry:
    total, rolls = roll_exploding_d6(5)
    result = f"Treasure map price roll: {'+'.join(str(roll) for roll in rolls)} = {total} gp."
    entry = TagDowntimeLogEntry(
        action="treasure_map_price",
        roll=total,
        total=total,
        cost_gp=total,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_downtime_log.append(entry)
    trim_tag_logs(campaign)
    return entry


def roll_moneylender_follow_chance(campaign: CampaignState, *, debt_gp: int) -> TagDowntimeLogEntry:
    debt = max(0, int(debt_gp))
    chance = min(6, ceil(debt / 100)) if debt else 0
    roll = roll_d6()
    followed = bool(chance and roll <= chance)
    if debt <= 0:
        result = "Moneylender pursuit check skipped: enter a debt amount above 0 gp."
    else:
        result = (
            f"Moneylender pursuit after moving settlement: debt {debt} gp gives {chance}-in-6 chance; "
            f"d6={roll} — {'enforcers follow' if followed else 'no pursuit this move'}."
        )
    entry = TagDowntimeLogEntry(
        action="moneylender_follow",
        roll=roll,
        total=chance,
        cost_gp=debt,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_downtime_log.append(entry)
    trim_tag_logs(campaign)
    return entry


def roll_horn_wandering_attraction(campaign: CampaignState) -> TagDowntimeLogEntry:
    roll = roll_d6()
    attracted = roll <= 2
    result = (
        f"Horn wandering-monster attraction roll: d6={roll}; "
        f"{'wandering monsters are attracted before the party moves' if attracted else 'no wandering monsters are attracted'}."
    )
    entry = TagDowntimeLogEntry(
        action="horn_attract",
        roll=roll,
        total=roll,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_downtime_log.append(entry)
    trim_tag_logs(campaign)
    return entry


def roll_flammable_oil_throw(campaign: CampaignState) -> TagDowntimeLogEntry:
    roll = roll_d6()
    if roll == 1:
        result = "Flammable oil throw: d6=1; oil sprays a friend for 2 fire damage."
    elif roll == 2:
        result = "Flammable oil throw: d6=2; flask is wasted with no damage."
    else:
        result = "Flammable oil throw: d6>=3; deal 2 fire damage to a major foe or 3 to a horde/minor group."
    entry = TagDowntimeLogEntry(
        action="flammable_oil_throw",
        roll=roll,
        total=roll,
        result_text=result,
        created_at=now_utc(),
    )
    campaign.tag_downtime_log.append(entry)
    trim_tag_logs(campaign)
    return entry


def roll_aspergillum_break_chance(campaign: CampaignState) -> TagDowntimeLogEntry:
    roll = roll_d6()
    breaks = roll <= 2
    result = (
        f"Aspergillum break roll after natural 1 Attack: d6={roll}; "
        f"{'the aspergillum breaks and holy water is wasted' if breaks else 'the aspergillum survives'}."
    )
    entry = TagDowntimeLogEntry(
        action="aspergillum_break",
        roll=roll,
        total=roll,
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


def update_troupe(
    campaign: CampaignState,
    *,
    troupe_name: str | None = None,
    active_character_ids: list[str] | None = None,
    guild_member: bool | None = None,
    guild_coffers_gp: int | None = None,
) -> CampaignState:
    if troupe_name is not None:
        campaign.tag_troupe_name = (troupe_name.strip() or "Adventuring Troupe")[:80]
    if active_character_ids is not None:
        seen: set[str] = set()
        campaign.tag_troupe_active_character_ids = [
            str(character_id)
            for character_id in active_character_ids
            if str(character_id) and not (str(character_id) in seen or seen.add(str(character_id)))
        ][:4]
    if guild_member is not None:
        campaign.tag_guild_member = bool(guild_member)
    if guild_coffers_gp is not None:
        campaign.tag_guild_coffers_gp = max(0, int(guild_coffers_gp))
    return campaign


def store_tag_treasure(
    campaign: CampaignState,
    character: Character,
    *,
    storage: str = "trove",
    gold_gp: int = 0,
    item_name: str = "",
    quantity: int = 1,
    notes: str = "",
) -> TagDowntimeLogEntry:
    clean_storage = storage if storage in {"trove", "bank", "magic_locker"} else "trove"
    gold = max(0, int(gold_gp))
    qty = max(1, int(quantity))
    clean_item = item_name.strip()[:100]
    fee = ceil(gold * 0.1) if clean_storage == "bank" and gold else 0
    total_gold_needed = gold + fee
    if total_gold_needed > character.gold:
        return append_tag_log(
            campaign,
            action="store_treasure",
            character=character,
            result_text=f"{character.name} needs {total_gold_needed} gp to store {gold} gp in {clean_storage}.",
        )
    if gold:
        character.gold -= total_gold_needed
        campaign.tag_storage_gold_gp += gold
    if clean_item:
        campaign.tag_stored_items.append(
            TagStoredItemState(
                owner_character_id=character.id,
                owner_name=character.name,
                item_name=clean_item,
                quantity=qty,
                storage=clean_storage,  # type: ignore[arg-type]
                notes=notes.strip()[:200],
                created_at=now_utc(),
            )
        )
    character.updated_at = now_utc()
    parts: list[str] = []
    if gold:
        fee_text = f" plus {fee} gp bank fee" if fee else ""
        parts.append(f"{gold} gp{fee_text}")
    if clean_item:
        parts.append(f"{qty}x {clean_item}")
    stored = " and ".join(parts) if parts else "nothing"
    return append_tag_log(
        campaign,
        action="store_treasure",
        character=character,
        cost_gp=total_gold_needed,
        result_text=f"{character.name} stores {stored} in TAG {clean_storage}. Settlement storage now holds {campaign.tag_storage_gold_gp} gp.",
    )


def withdraw_tag_stored_gold(campaign: CampaignState, character: Character, *, gold_gp: int) -> TagDowntimeLogEntry:
    amount = min(max(0, int(gold_gp)), campaign.tag_storage_gold_gp)
    if amount <= 0:
        return append_tag_log(
            campaign,
            action="withdraw_stored_gold",
            character=character,
            result_text="No TAG stored gold was withdrawn.",
        )
    campaign.tag_storage_gold_gp -= amount
    character.gold += amount
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action="withdraw_stored_gold",
        character=character,
        result_text=f"{character.name} withdraws {amount} gp from TAG stored treasure.",
    )


def create_magic_locker(
    campaign: CampaignState,
    character: Character,
    *,
    contents: str,
    kind: str = "item",
    gold_gp: int = 0,
) -> TagDowntimeLogEntry:
    clean_kind = "gold" if kind == "gold" else "item"
    gold = min(5000, max(0, int(gold_gp)))
    label = contents.strip()[:100] or ("Gold pouch" if clean_kind == "gold" else "Stored item")
    cost = 50 + (gold if clean_kind == "gold" else 0)
    if campaign.settlement_size < 0:
        return append_tag_log(
            campaign,
            action="magic_locker_create",
            character=character,
            result_text="Magic lockers require a size 0 or larger settlement.",
        )
    if character.gold < cost:
        return append_tag_log(
            campaign,
            action="magic_locker_create",
            character=character,
            result_text=f"{character.name} needs {cost} gp for the magic locker setup.",
        )
    character.gold -= cost
    character.updated_at = now_utc()
    campaign.tag_magic_lockers.append(
        TagMagicLockerState(
            owner_character_id=character.id,
            owner_name=character.name,
            contents=label,
            kind=clean_kind,  # type: ignore[arg-type]
            gold_gp=gold if clean_kind == "gold" else 0,
            created_at=now_utc(),
        )
    )
    return append_tag_log(
        campaign,
        action="magic_locker_create",
        character=character,
        cost_gp=cost,
        result_text=f"{character.name} creates a magic locker for {label}. Cost {cost} gp.",
    )


def summon_magic_locker(campaign: CampaignState, *, locker_id: str) -> TagDowntimeLogEntry:
    locker = next((item for item in campaign.tag_magic_lockers if item.id == locker_id), None)
    if locker is None:
        return append_tag_log(campaign, action="magic_locker_summon", result_text="Magic locker not found.")
    total, rolls = roll_3d6()
    if total <= 6:
        locker.mishap_locked = True
        result = (
            f"{locker.owner_name}'s magic locker summon for {locker.contents}: "
            f"{'+'.join(str(roll) for roll in rolls)} = {total}; mishap, contents unavailable until visiting the bank."
        )
    else:
        result = (
            f"{locker.owner_name}'s magic locker summon for {locker.contents}: "
            f"{'+'.join(str(roll) for roll in rolls)} = {total}; contents appear ready to use."
        )
    return append_tag_log(campaign, action="magic_locker_summon", roll=total, total=total, result_text=result)


def purchase_tag_service(
    campaign: CampaignState,
    character: Character,
    *,
    service_key: str,
    quantity: int = 1,
) -> TagDowntimeLogEntry:
    qty = max(1, int(quantity))
    if service_key == "platinum_piece":
        cost = 20 * qty
        if campaign.settlement_size < 3:
            return append_tag_log(
                campaign,
                action="purchase_service",
                character=character,
                result_text="Buying platinum pieces requires a size +3 settlement.",
            )
        if character.gold < cost:
            return append_tag_log(
                campaign,
                action="purchase_service",
                character=character,
                result_text=f"{character.name} needs {cost} gp to buy {qty} PP.",
            )
        character.gold -= cost
        campaign.tag_platinum_pieces += qty
        character.updated_at = now_utc()
        return append_tag_log(
            campaign,
            action="purchase_service",
            character=character,
            cost_gp=cost,
            result_text=f"{character.name} buys {qty} PP for {cost} gp. Campaign PP now {campaign.tag_platinum_pieces}.",
        )
    service = TAG_PURCHASABLE_SERVICES.get(service_key)
    if service is None:
        return append_tag_log(
            campaign,
            action="purchase_service",
            character=character,
            result_text=f"Unknown TAG purchase service: {service_key}.",
        )
    cost = int(service["cost_gp"]) * qty
    if character.gold < cost:
        return append_tag_log(
            campaign,
            action="purchase_service",
            character=character,
            result_text=f"{character.name} needs {cost} gp for {qty}x {service['label']}.",
        )
    character.gold -= cost
    item = service.get("inventory")
    status = service.get("status")
    if isinstance(item, str):
        character.inventory.extend([item] * qty)
    if isinstance(status, str) and status not in character.statuses:
        character.statuses.append(status)
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action="purchase_service",
        character=character,
        cost_gp=cost,
        result_text=f"{character.name} buys {qty}x {service['label']} for {cost} gp; {service['result']}.",
    )


def roll_gambling_house(campaign: CampaignState, character: Character, *, stake_gp: int) -> TagDowntimeLogEntry:
    stake = max(0, int(stake_gp))
    if stake <= 0:
        return append_tag_log(campaign, action="gambling_house", character=character, result_text="Enter a gambling stake above 0 gp.")
    if character.gold < stake:
        return append_tag_log(
            campaign,
            action="gambling_house",
            character=character,
            result_text=f"{character.name} needs {stake} gp to gamble that stake.",
        )
    roll = roll_d10()
    class_id = (character.class_id or character.class_name or "").lower().replace(" ", "_").replace("-", "_")
    gambler_bonus = 1 if class_id in {"halfling", "rogue", "swashbuckler", "harlequin", "assassin"} else 0
    total = roll + gambler_bonus
    character.gold -= stake
    if total <= 4:
        result = f"{character.name} loses the {stake} gp stake at the gambling house."
    elif total <= 6:
        result = f"{character.name} loses {stake} gp but hears useful information: roll Rumors or a 3-in-6 chance for 1 Clue."
    elif total <= 8:
        win = ceil(stake * 1.1)
        character.gold += win
        result = f"{character.name} wins +10% and leaves with {win} gp from a {stake} gp stake."
    elif total == 9:
        win = ceil(stake * 1.2)
        character.gold += win
        result = f"{character.name} wins +20% and leaves with {win} gp from a {stake} gp stake."
    elif total == 10:
        win = ceil(stake * 1.5)
        character.gold += win
        result = f"{character.name} wins +50% and leaves with {win} gp from a {stake} gp stake."
    else:
        win = stake * 2
        character.gold += win
        result = f"{character.name} wins +100% and leaves with {win} gp; resolve the L6 temptation Save manually."
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action="gambling_house",
        character=character,
        roll=roll,
        modifier=gambler_bonus,
        total=total,
        cost_gp=stake,
        result_text=result,
    )


def run_streetwise_action(
    campaign: CampaignState,
    character: Character,
    *,
    action: str,
    target_level: int = 6,
    target_name: str = "",
) -> TagDowntimeLogEntry:
    clean_action = action if action in {"listen_rumors", "interrogate", "look_tough"} else "listen_rumors"
    target = max(1, int(target_level))
    roll = roll_d6()
    modifier = streetwise_modifier(character, action="interrogation" if clean_action == "interrogate" else clean_action)
    total = roll + modifier
    if clean_action == "listen_rumors":
        target = 4
        if roll == 1:
            red_roll = roll_d6()
            result = f"{character.name} hears a red herring: {TAG_RED_HERRINGS[red_roll]}"
        elif total >= target:
            rumor_roll = roll_d12()
            result = f"{character.name} hears rumor {rumor_roll}: {TAG_RUMORS[rumor_roll]}"
        else:
            result = f"{character.name} finds no useful rumor and may try again after one adventure."
    elif clean_action == "interrogate":
        target = target + 1
        label = target_name.strip()[:80] or "captured riff-raff"
        if roll == 1:
            result = f"{character.name} gets no information and is hated by all Riff-Raff in the next Riff-Raff encounter."
        elif total >= target:
            character.clues += 1
            result = f"{character.name} interrogates {label} and gains 1 Clue; same-type foes hate the interrogator next encounter."
        else:
            result = f"{character.name} interrogates {label} but gains no information."
    else:
        target = 6
        if roll == 1 or total < target:
            damage = roll_d3()
            character.current_life = max(0, character.current_life - damage)
            result = f"{character.name} fails to look tough and loses {damage} Life in a street brawl."
        else:
            if character.id not in campaign.tag_look_tough_character_ids:
                campaign.tag_look_tough_character_ids.append(character.id)
            result = f"{character.name} gains a tough reputation: Riff-Raff morale rolls take an extra -1 until the bonus is lost."
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action=clean_action,
        character=character,
        roll=roll,
        modifier=modifier,
        total=total,
        result_text=result,
    )


def follow_treasure_map(campaign: CampaignState, *, use_guild_cartographer: bool = False) -> TagDowntimeLogEntry:
    roll = roll_d6()
    bonus = campaign.tag_map_bonus + (1 if use_guild_cartographer and campaign.tag_guild_member else 0)
    total = roll if roll == 1 else roll + bonus
    table_key = max(1, min(6, total))
    result = TAG_TREASURE_MAP_RESULTS[table_key]
    extra = ""
    if table_key == 4:
        campaign.tag_map_bonus += 1
        extra = f" Stored map bonus is now +{campaign.tag_map_bonus}."
    elif table_key >= 5:
        lead_roll = roll_d6()
        extra = f" The Map Leads To {lead_roll}: {TAG_MAP_LEADS_TO[lead_roll]}"
    return append_tag_log(
        campaign,
        action="follow_treasure_map",
        roll=roll,
        modifier=bonus,
        total=total,
        result_text=f"Following Treasure Map roll d6={roll} {format_bonus(bonus)} = {total}: {result}{extra}",
    )


def format_bonus(value: int) -> str:
    if value > 0:
        return f"+{value}"
    if value < 0:
        return str(value)
    return "+0"


def _slug_part(value: str) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    clean = "-".join(part for part in clean.split("-") if part)
    return clean[:40] or "lead"


def _tag_adventure_id(lead_type: str, label: str) -> str:
    return f"tag-{_slug_part(lead_type)}-{_slug_part(label)}-{uuid4().hex[:8]}"


def _tag_manifest(
    *,
    adventure_id: str,
    title: str,
    synopsis: str,
    objective: str,
    lead_type: str,
    lead_detail: str,
    final_room_title: str,
    final_room_description: str,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": adventure_id,
        "title": title,
        "synopsis": synopsis,
        "source": {
            "type": "hand",
            "parameters": {
                "origin": "Tales from the Adventurers' Guild",
                "lead_type": lead_type,
                "lead_detail": lead_detail,
            },
        },
        "recommended_levels": [1, 5],
        "default_environment": "dungeon",
        "entrance_room_id": "tag-lead-entry",
        "exit_room_id": "tag-return-road",
        "quest": {
            "key": "tag_lead",
            "objective_text": objective,
            "giver_room_id": "tag-lead-entry",
            "complete_when": {
                "type": "boss_defeated",
                "boss_name": "Wraith",
                "room_id": "tag-final-scene",
            },
        },
        "npcs": [
            {
                "id": "tag-contact",
                "name": "Guild Contact",
                "room_id": "tag-lead-entry",
                "description": "A local contact points the troupe toward the lead recorded in the TAG settlement log.",
                "dialogue": objective,
            }
        ],
        "rooms": [
            {
                "id": "tag-lead-entry",
                "tile_key": "02",
                "title": "Lead Trail",
                "description": "The party follows a TAG campaign lead out of the settlement. The first signs point north, while a side clue lies east.",
                "environment": "dungeon",
                "exits": [
                    {
                        "id": "tag-lead-entry-north",
                        "direction": "north",
                        "to": "tag-complication",
                        "kind": "passage",
                        "status": "open",
                    },
                    {
                        "id": "tag-lead-entry-east",
                        "direction": "east",
                        "to": "tag-side-clue",
                        "kind": "door",
                        "status": "closed",
                    },
                ],
                "triggers": [],
            },
            {
                "id": "tag-side-clue",
                "tile_key": "12",
                "title": "Side Clue",
                "description": "Discarded gear and frightened local gossip confirm that the lead is real.",
                "exits": [
                    {
                        "id": "tag-side-clue-west",
                        "direction": "west",
                        "to": "tag-lead-entry",
                        "kind": "door",
                        "status": "closed",
                    }
                ],
                "triggers": [
                    {
                        "when": "on_search",
                        "once": True,
                        "log": "The party finds a small payment hidden with the clue.",
                        "treasure": {"gold": 12, "items": []},
                    }
                ],
            },
            {
                "id": "tag-complication",
                "tile_key": "13",
                "title": "Complication",
                "description": "Local troublemakers have reached the lead first.",
                "exits": [
                    {
                        "id": "tag-complication-south",
                        "direction": "south",
                        "to": "tag-lead-entry",
                        "kind": "door",
                        "status": "open",
                    },
                    {
                        "id": "tag-complication-north",
                        "direction": "north",
                        "to": "tag-final-scene",
                        "kind": "passage",
                        "status": "closed",
                    },
                    {
                        "id": "tag-complication-west",
                        "direction": "west",
                        "to": "tag-return-road",
                        "kind": "door",
                        "status": "open",
                    },
                ],
                "triggers": [
                    {
                        "when": "on_enter",
                        "once": True,
                        "encounter": {"foes": [{"name": "Goblins", "count": 4}]},
                    }
                ],
            },
            {
                "id": "tag-final-scene",
                "tile_key": "11",
                "title": final_room_title,
                "description": final_room_description,
                "exits": [
                    {
                        "id": "tag-final-scene-south",
                        "direction": "south",
                        "to": "tag-complication",
                        "kind": "door",
                        "status": "closed",
                    }
                ],
                "triggers": [
                    {
                        "when": "on_enter",
                        "once": True,
                        "encounter": {"foes": [{"name": "Wraith", "count": 1}]},
                    }
                ],
            },
            {
                "id": "tag-return-road",
                "tile_key": "06",
                "title": "Return Road",
                "description": "The road back to the settlement waits here.",
                "exits": [
                    {
                        "id": "tag-return-road-east",
                        "direction": "east",
                        "to": "tag-complication",
                        "kind": "door",
                        "status": "open",
                    }
                ],
                "triggers": [],
            },
        ],
        "ending": {
            "victory_text": "The party returns to the settlement with the TAG lead resolved.",
            "defeat_text": "The TAG lead remains unresolved in the settlement records.",
        },
    }


def build_tag_adventure_manifest(
    campaign: CampaignState,
    *,
    lead_type: str,
    detail: str = "",
) -> tuple[dict[str, object], TagDowntimeLogEntry]:
    clean_type = lead_type if lead_type in {"rumor", "treasure_map", "thematic_dungeon", "guild_job"} else "rumor"
    clean_detail = detail.strip()
    if clean_type == "rumor":
        rumor_number = int(clean_detail) if clean_detail.isdigit() else roll_d12()
        rumor_number = max(1, min(12, rumor_number))
        label = f"Rumor {rumor_number}"
        lead_detail = TAG_RUMORS[rumor_number]
        campaign.tag_used_rumor_numbers = sorted(set(campaign.tag_used_rumor_numbers + [rumor_number]))
        title = f"TAG {label}: {lead_detail.split(':', 1)[0]}"
        objective = f"Investigate TAG {label} from the settlement rumor list."
        final_title = f"{label} Resolution"
        final_description = f"This room represents the playable handoff for {lead_detail}"
    elif clean_type == "treasure_map":
        map_roll = int(clean_detail) if clean_detail.isdigit() else roll_d6()
        map_roll = max(1, min(6, map_roll))
        label = f"Treasure Map {map_roll}"
        lead_detail = TAG_MAP_LEADS_TO[map_roll]
        title = f"TAG Treasure Map: {lead_detail.split(':', 1)[0]}"
        objective = "Follow the purchased TAG treasure map and resolve the destination."
        final_title = "Mapped Treasure Site"
        final_description = lead_detail
    elif clean_type == "thematic_dungeon":
        theme_roll = int(clean_detail) if clean_detail.isdigit() else roll_d6()
        theme_roll = max(1, min(6, theme_roll))
        lead_detail = TAG_THEMATIC_DUNGEONS[theme_roll]
        label = lead_detail
        title = f"TAG Thematic Dungeon: {lead_detail}"
        objective = f"Resolve the TAG thematic dungeon lead: {lead_detail}."
        final_title = lead_detail
        final_description = f"This is the TAG adventure handoff for {lead_detail}. Expand with the full PDF table during later authoring."
    else:
        job_roll = roll_d6()
        if job_roll <= 3:
            quest_roll = roll_d6()
            lead_detail = f"Guild Job {job_roll}: Minor Unique Quest - {TAG_MINOR_UNIQUE_QUESTS[quest_roll]}"
        elif job_roll <= 5:
            rumor_roll = roll_d12()
            lead_detail = f"Guild Job {job_roll}: Rumor - {TAG_RUMORS[rumor_roll]}"
            campaign.tag_used_rumor_numbers = sorted(set(campaign.tag_used_rumor_numbers + [rumor_roll]))
        else:
            theme_roll = roll_d6()
            lead_detail = f"Guild Job {job_roll}: Thematic Dungeon - {TAG_THEMATIC_DUNGEONS[theme_roll]}"
        label = f"Guild Job {job_roll}"
        title = f"TAG {label}"
        objective = "Complete the work assigned by the Adventurers Guild job table."
        final_title = label
        final_description = lead_detail
    adventure_id = _tag_adventure_id(clean_type, label)
    manifest = _tag_manifest(
        adventure_id=adventure_id,
        title=title[:120],
        synopsis=f"Generated from TAG campaign downtime in {campaign.settlement_name}: {lead_detail}",
        objective=objective,
        lead_type=clean_type,
        lead_detail=lead_detail,
        final_room_title=final_title,
        final_room_description=final_description,
    )
    campaign.tag_generated_adventure_ids.append(adventure_id)
    entry = append_tag_log(
        campaign,
        action="create_tag_adventure",
        result_text=f"Created TAG adventure '{manifest['title']}' in the Adventure section with id {adventure_id}.",
    )
    return manifest, entry


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
