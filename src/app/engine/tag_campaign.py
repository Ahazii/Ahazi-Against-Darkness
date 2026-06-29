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
    TagAdventureRouteState,
    TagBankAccountState,
    TagDowntimeLogEntry,
    TagMagicLockerState,
    TagStoredItemState,
    TagTravelLogEntry,
    TagXpMarkerState,
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
    {
        "key": "adventurers_guild_jobs",
        "name": "Adventurers Guild jobs",
        "source_page": 54,
        "min_size": -3,
        "cost": "Guild job table; payment depends on the rolled job.",
        "summary": "Rolls Minor Unique Quest, Rumor, or Thematic Dungeon work and can install it as an Adventure module.",
        "automation": "Use Maps and Adventure Leads > Guild Job to create a playable Adventure module with TAG source notes.",
    },
    {
        "key": "trinkets",
        "name": "Trinkets",
        "source_page": 61,
        "min_size": -3,
        "cost": "Not normally purchased; used for small-party starts and loot substitutions.",
        "summary": "Minor magic items for small parties: scrolls, healing potion, Power Cookie, enchanted shot, spheres, candy, and bauble.",
        "automation": "Use TAG Actions > Trinket to consume carried trinkets and apply safe healing/status markers.",
    },
    {
        "key": "guild_spells",
        "name": "Guild spells",
        "source_page": 65,
        "min_size": -3,
        "cost": "Learn or find as basic Guild spell scrolls when allowed by TAG.",
        "summary": "Guild spell table: Speedy Recovery, Temporary Weapon Enchantment, Troupe Switch, Look Tough, Silence of the Mouse, Wizard's Luck.",
        "automation": "Use TAG Actions > Guild spell to consume scrolls or log known-spell casts with status markers.",
    },
    {
        "key": "tag_special_foes",
        "name": "TAG special foes",
        "source_page": 25,
        "min_size": -3,
        "cost": "Used by generated TAG adventure modules",
        "summary": "TAG-specific foe profiles are available for assassins, white gargoyles, cultists, hill giant, bandits, Gorungar, griffin, monoceros, and other generated finales.",
        "automation": "Reference row; generated TAG adventures now spawn these named foes where their scene/theme calls for them.",
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

TAG_TRINKETS: dict[int, str] = {
    1: "Power Cookie",
    2: "Enchanted Sling Bullet",
    3: "Mist Sphere",
    4: "Darkness Sphere",
    5: "Candy of Hyperactivity",
    6: "Enchanted Bauble",
}

TAG_GUILD_SPELLS: dict[int, str] = {
    1: "Speedy Recovery",
    2: "Temporary Weapon Enchantment",
    3: "Troupe Switch",
    4: "Look Tough",
    5: "Silence of the Mouse",
    6: "Wizard's Luck",
}

TAG_BRANCH_ACTIONS: dict[str, str] = {
    "social_choice": "Resolve social/choice branch",
    "spend_clues": "Spend Clues for branch",
    "roll_variable_count": "Roll variable count",
    "capture_alive": "Capture-alive outcome",
    "claim_reward": "Claim printed reward",
}

TAG_ROUTE_ACTIONS: dict[str, str] = {
    "parley_success": "Parley/social branch succeeds",
    "parley_failed": "Parley/social branch fails",
    "clue_gate_unlocked": "Clue gate unlocked",
    "clue_gate_blocked": "Clue gate blocked",
    "hostile_branch": "Hostile branch chosen",
    "peaceful_branch": "Peaceful branch chosen",
    "skip_scene": "Scene skipped",
    "unlock_scene": "Scene unlocked",
    "solo_restriction": "Solo restriction noted",
    "final_route": "Finale route selected",
}

TAG_SCENE_ACTIONS: dict[str, str] = {
    "medusa_pendant": "Medusa pendant",
    "gargoyle_bounty": "Gargoyle bounty",
    "gorungar_head": "Gorungar head bounty",
    "gorungar_alive": "Gorungar alive bounty",
    "bandit_chieftain_capture": "Bandit Chieftain capture",
    "shaura_reward": "Shaura cult reward",
    "daroc_cat": "Daroc's cat reward",
    "mutant_fish_rations": "Mutant fish rations",
    "agaratha": "Agaratha recovered",
    "deoldyn_training": "Deoldyn training",
    "dragon_type_reveal": "Dragon type reveal",
}

TAG_XP_ACTIONS: dict[str, str] = {
    "mark_scene_xp": "Mark scene XP pending",
    "award_scene_xp": "Award scene XP",
    "mark_minor_encounters": "Mark minor encounter XP count",
    "mark_capture_xp": "Mark capture-alive XP",
    "mark_training_xp_roll": "Mark training XP roll",
}

TAG_TRINKET_EFFECTS: dict[str, dict[str, object]] = {
    "power_cookie": {
        "name": "Power Cookie",
        "item": "Power Cookie",
        "summary": "Mark the next appropriate roll or combat action as boosted by the Power Cookie; consume after use.",
        "status": "TAG Power Cookie boost pending",
    },
    "enchanted_sling_bullet": {
        "name": "Enchanted Sling Bullet",
        "item": "Enchanted Sling Bullet",
        "summary": "Use for the next sling shot; consume the bullet and apply the printed enchanted-shot effect manually.",
    },
    "mist_sphere": {
        "name": "Mist Sphere",
        "item": "Mist Sphere",
        "summary": "Break to create mist; log the escape/cover window and consume the sphere.",
        "status": "TAG Mist Sphere mist active",
    },
    "darkness_sphere": {
        "name": "Darkness Sphere",
        "item": "Darkness Sphere",
        "summary": "Break to create darkness; log the darkness window and consume the sphere.",
        "status": "TAG Darkness Sphere darkness active",
    },
    "candy_of_hyperactivity": {
        "name": "Candy of Hyperactivity",
        "item": "Candy of Hyperactivity",
        "summary": "Mark the character's next speed/action benefit and consume the candy.",
        "status": "TAG hyperactivity candy active",
    },
    "enchanted_bauble": {
        "name": "Enchanted Bauble",
        "item": "Enchanted Bauble",
        "summary": "Use as a minor magical decoy/charm per TAG; consume or mark spent after the scene.",
        "status": "TAG enchanted bauble active",
    },
    "potion_of_healing": {
        "name": "Potion of Healing",
        "item": "Potion of Healing",
        "summary": "Heal the character to full Life and remove ordinary poison/disease; does not cure dark plague.",
        "heal_full": True,
    },
}

TAG_GUILD_SPELL_EFFECTS: dict[str, dict[str, object]] = {
    "speedy_recovery": {
        "name": "Speedy Recovery",
        "summary": "Heal the selected character to full Life and mark fast recovery for the current between-adventure or recovery window.",
        "status": "TAG Speedy Recovery pending",
        "heal_full": True,
    },
    "temporary_weapon_enchantment": {
        "name": "Temporary Weapon Enchantment",
        "summary": "Mark the caster's chosen weapon as temporarily enchanted for this encounter/adventure window.",
        "status": "TAG temporary weapon enchantment",
    },
    "troupe_switch": {
        "name": "Troupe Switch",
        "summary": "Log that the troupe may switch an eligible active/home character according to the printed Guild spell.",
        "status": "TAG Troupe Switch pending",
    },
    "look_tough": {
        "name": "Look Tough",
        "summary": "Mark the caster with the Look Tough reputation effect used by TAG Streetwise/riff-raff handling.",
        "status": "TAG Look Tough spell",
    },
    "silence_of_the_mouse": {
        "name": "Silence of the Mouse",
        "summary": "Mark the caster/party for the printed stealth silence window; use this marker when resolving the next stealth or noise check.",
        "status": "TAG Silence of the Mouse active",
    },
    "wizards_luck": {
        "name": "Wizard's Luck",
        "summary": "Mark the caster with the printed Wizard's Luck reroll/luck window.",
        "status": "TAG Wizard's Luck pending",
    },
}

TAG_RUMOR_PROFILES: dict[int, dict[str, object]] = {
    1: {
        "title": "Bofto's Star-Shaped Find",
        "scene": "Scene 9, then Scene 17 if the family is questioned",
        "pdf_pages": "TAG pp.22, 29, 31",
        "objective": "Investigate Bofto's strange star-shaped object and decide whether to steal it, question the family, or leave it alone.",
        "entry": "Bofto's vineyard has been quiet since the star-shaped object appeared.",
        "side": "Questioning the family confirms Bofto has changed and points back to the object.",
        "complication": "Treat theft or confrontation as a manual TAG social choice before combat starts.",
        "final_title": "The Star Object",
        "final_description": "A star-shaped object hums in the vineyard. Use the TAG Scene 9 choices: steal, talk, or leave; record consequences manually.",
        "final_foe": "Goblins",
        "final_count": 4,
        "rewards": "Depends on the chosen Scene 9 resolution.",
        "rules": [
            "Rumor is crossed off once played.",
            "This is primarily a choice scene; the installed encounter is a proxy if the table result turns hostile.",
        ],
    },
    2: {
        "title": "Medusa in the Hunter's Cabin",
        "scene": "Scene 10 leading to Scene 1",
        "pdf_pages": "TAG pp.22, 25-26",
        "objective": "Survive or talk down the assassins, then resolve the medusa Xasartha.",
        "entry": "A hunter's cabin hides more than a monster story.",
        "side": "Streetwise or roleplay may reveal why the assassins want the medusa dead.",
        "complication": "Scene 10 calls for d3+2 agents at HCL+2 and a possible Streetwise L5 parley.",
        "final_title": "Xasartha's Cabin",
        "final_description": "Xasartha, the medusa, waits in the cabin. Apply her gaze and pendant rules from TAG Scene 1.",
        "final_foe": "Medusa",
        "final_count": 1,
        "rewards": "Pendant worth 260 gp and necros; trying it can grant Luck as described in Scene 1.",
        "rules": [
            "Assassin count and parley are not auto-rolled inside the module.",
            "Use the Medusa combat profile for the final encounter.",
        ],
    },
    3: {
        "title": "The Paladin's Sword",
        "scene": "Scene 11",
        "pdf_pages": "TAG pp.23, 30",
        "objective": "Check the old miller's farm and discover whether the sword rumor is true.",
        "entry": "The farm is watched by locals who have repeated the sword story too often.",
        "side": "Search the outbuildings for the false trail and any remaining tracks.",
        "complication": "Scene 11 is a red herring with a 2-in-6 Riff-Raff or Outside ambush chance.",
        "final_title": "False Sword Trail",
        "final_description": "No paladin sword is here. Roll the Scene 11 ambush chance manually if you want the printed resolution.",
        "final_foe": "Goblins",
        "final_count": 4,
        "rewards": "No sword; possible ambush rewards only.",
        "rules": ["Installed combat is a proxy for the optional ambush."],
    },
    4: {
        "title": "Mutant Fish Under the Bridge",
        "scene": "Scene 12",
        "pdf_pages": "TAG pp.23, 30",
        "objective": "Face the mutant fish's hypnosis at the bridge.",
        "entry": "The stream under the bridge is unnaturally still.",
        "side": "The banks show signs of travellers walking willingly into the water.",
        "complication": "All characters Save vs L5 hypnosis; chaos-tainted characters fail automatically.",
        "final_title": "The Bridge Pool",
        "final_description": "Resolve the mutant fish hypnosis and rescue timing from TAG Scene 12 before ending the scene.",
        "final_foe": "Mutant Fish",
        "final_count": 1,
        "rewards": "If the party survives, d6+3 food rations; counts as two minion encounters for XP.",
        "rules": ["Resolve the printed hypnosis sequence before ordinary combat if the table calls for it."],
    },
    5: {
        "title": "Dragon in Disguise",
        "scene": "Scene 13",
        "pdf_pages": "TAG pp.22, 31, 39-40",
        "objective": "Decide whether the disguised traveller is truly a dragon and spend Clues if the lair is pursued.",
        "entry": "A too-polished stranger keeps appearing in local accounts.",
        "side": "Clues can later reveal the dragon's lair and type.",
        "complication": "If the party pursues the real dragon, TAG uses the Dragon's Lair thematic dungeon.",
        "final_title": "The Disguised Dragon",
        "final_description": "The mask drops. Use Scene 13 to decide whether this becomes a Dragon's Lair hunt.",
        "final_foe": "Young Dragon",
        "final_count": 1,
        "rewards": "Dragon lair treasure if pursued; spend 2 Clues to learn dragon type before the final room.",
        "rules": ["Use the Dragon's Lair thematic notes in source.parameters for the full lair version."],
    },
    6: {
        "title": "Leprechauns at Blackbird Hill",
        "scene": "Scene 2",
        "pdf_pages": "TAG pp.23, 25",
        "objective": "Find the leprechauns and decide whether to buy Shoes of Fast Walk or learn their illusion spell.",
        "entry": "Blackbird Hill is dotted with tiny tracks and mocking laughter.",
        "side": "The leprechauns prefer bargaining to fighting.",
        "complication": "They sell Shoes of Fast Walk and may teach an illusion spell under the Scene 2 terms.",
        "final_title": "Blackbird Hill Bargain",
        "final_description": "Resolve the leprechaun bargain; fight only if your table turns the scene hostile.",
        "final_foe": "Goblins",
        "final_count": 4,
        "rewards": "Shoes of Fast Walk for 200 gp; illusion spell instruction per Scene 2.",
        "rules": ["Installed combat is only a hostile-scene proxy."],
    },
    7: {
        "title": "The Stair Under Tamas Zeya",
        "scene": "Scene 15",
        "pdf_pages": "TAG pp.24, 31",
        "objective": "Enter the hidden temple stair under Tamas Zeya and clear the small temple dungeon.",
        "entry": "A concealed stair descends below Tamas Zeya.",
        "side": "Old offerings mark this as a temple site rather than a normal cellar.",
        "complication": "Scene 15 calls for a small seven-room dungeon using 4AD or Lost Temples support.",
        "final_title": "Temple Below Tamas Zeya",
        "final_description": "Resolve this as the temple finale for the seven-room Scene 15 dungeon.",
        "final_foe": "Mummy",
        "final_count": 1,
        "rewards": "Temple treasure per the generated rooms.",
        "rules": ["This module is a compact handoff; expand to seven rooms if playing the PDF literally."],
    },
    8: {
        "title": "Shaura's Chaos Cult",
        "scene": "Scene 16",
        "pdf_pages": "TAG pp.24, 31",
        "objective": "Spend the needed Clues, find Shaura, and break the chaos cult.",
        "entry": "Names whispered in town all point to Shaura.",
        "side": "The cult signs require careful Streetwise work before the dungeon can be found.",
        "complication": "Scene 16 requires 2 Clues and a ten-room dungeon; final fight is Silent Scream cultists plus priestess.",
        "final_title": "Silent Scream Shrine",
        "final_description": "The cult gathers around Shaura's shrine. Use the printed cultist/priestess mix for the exact final fight.",
        "final_foe": "Silent Scream Priestess",
        "final_count": 1,
        "final_extra_foes": [{"name": "Silent Scream Cultists", "count": 9}],
        "rewards": "150 gp and XP after the cult is defeated.",
        "rules": ["Final encounter includes the priestess and nine Silent Scream cultists."],
    },
    9: {
        "title": "Daroc's Lost Familiar",
        "scene": "Scene 5",
        "pdf_pages": "TAG pp.24, 27",
        "objective": "Use town Clues to find Daroc's lost cat familiar.",
        "entry": "Daroc's familiar has vanished into the settlement alleys.",
        "side": "Beastmasters, druids, cat-like characters, or cat companions reduce the Clue burden.",
        "complication": "Scene 5 requires 2 Clues from town Streetwise, reduced to 1 with the listed cat/beast help.",
        "final_title": "The Familiar's Hiding Place",
        "final_description": "The familiar is cornered by rough locals. Resolve the Clue spend before claiming the reward.",
        "final_foe": "Goblins",
        "final_count": 4,
        "rewards": "100 gp and 1 XP.",
        "rules": ["Installed combat represents trouble around the familiar, not a mandatory PDF fight."],
    },
    10: {
        "title": "Winged Things Over the Burgomaster's House",
        "scene": "Scene 8",
        "pdf_pages": "TAG pp.24, 29",
        "objective": "Stop the white gargoyles above the burgomaster's house.",
        "entry": "Winged shapes circle the burgomaster's roof at dusk.",
        "side": "Witnesses disagree on how many creatures came down.",
        "complication": "Scene 8 uses d6+2 white gargoyles, surprise chance, and no escape until conditions are met.",
        "final_title": "Burgomaster's Roof",
        "final_description": "White gargoyles descend. Use Scene 8 for count, surprise, escape limits, and bounty.",
        "final_foe": "White Gargoyles",
        "final_count": 8,
        "rewards": "15 gp per gargoyle head.",
        "rules": ["Use d6+2 gargoyles at the table if you want to roll the exact count instead of the generated count."],
    },
    11: {
        "title": "Deoldyn's Archery Training",
        "scene": "Scene 3",
        "pdf_pages": "TAG pp.24, 25",
        "objective": "Meet Deoldyn and decide who pays for elven archery training.",
        "entry": "Targets split cleanly on Deoldyn's practice range.",
        "side": "The training is expensive but can unlock archery advancement.",
        "complication": "Training costs 60 gp x level and grants one XP roll for Deadly Accuracy or Dead Shot.",
        "final_title": "Deoldyn's Range",
        "final_description": "Resolve payment and training; the encounter is only used if the meeting is interrupted.",
        "final_foe": "Goblins",
        "final_count": 4,
        "rewards": "One qualifying XP roll for the listed archery benefits.",
        "rules": ["Installed combat is a proxy interruption, not required by the training scene."],
    },
    12: {
        "title": "Shinta and Agaratha",
        "scene": "Scene 4, then Scene 7",
        "pdf_pages": "TAG pp.24, 26-29",
        "objective": "Accept Shinta's request and recover the magic sword Agaratha from the bandit hideout.",
        "entry": "Shinta's story starts as a request and ends at a bandit hideout.",
        "side": "Agaratha is recovered through a solo ten-room Bandit Hideout quest in the printed scene.",
        "complication": "Scene 7 is a special solo quest with the Bandit Hideout theme.",
        "final_title": "Agaratha's Hideout",
        "final_description": "Bandits hold Agaratha. Use Scene 7 for the solo-quest restrictions and sword reward.",
        "final_foe": "Goblins",
        "final_count": 6,
        "rewards": "Agaratha, a magic masterwork sword with the printed Luck-on-major-kill rule.",
        "rules": ["This generated module supports normal party play; enforce solo restrictions manually if desired."],
    },
}

TAG_THEMATIC_DUNGEON_PROFILES: dict[int, dict[str, object]] = {
    1: {
        "title": "Ghastly Mine",
        "pdf_pages": "TAG pp.38, 41-42",
        "objective": "Clear nine rooms of undead mine workings and survive cave-ins.",
        "entry": "Rotten pit props and stale air identify the dungeon as a Ghastly Mine.",
        "side": "Gold results may become gems or nuggets.",
        "complication": "Minion, Boss, and Weird results are replaced by the Ghastly Mine undead tables on 4-in-6.",
        "final_title": "Collapsed Undead Shaft",
        "final_description": "The deepest shaft holds the mine's major undead. Track cave-in trap count manually.",
        "final_foe": "Wraith",
        "final_count": 1,
        "rewards": "Normal treasure, with gp-to-gem/nugget conversion where the theme says so.",
        "rules": ["Nine-room target.", "Cave-in traps affect all characters and become worse after repeated collapses."],
    },
    2: {
        "title": "Giant's Lair",
        "pdf_pages": "TAG p.43",
        "objective": "Reach the HCL+5 room count and defeat the hill giant finale.",
        "entry": "The ceiling rises and the furniture is built for giant hands.",
        "side": "The party can identify the lair before pressing deeper.",
        "complication": "No normal Final Boss check; the final room must be large enough for the giant.",
        "final_title": "Hill Giant Hall",
        "final_description": "A hill giant hurls a boulder before closing for melee. Use TAG p.43 for the exact giant profile.",
        "final_foe": "Hill Giant",
        "final_count": 1,
        "rewards": "Three treasure rolls and double gp in the final room.",
        "rules": ["Hill Giant is now a TAG-specific foe profile.", "Spells hit the hill giant at +2."],
    },
    3: {
        "title": "Dragon's Lair",
        "pdf_pages": "TAG pp.39-40",
        "objective": "Complete four rooms, spend Clues if desired, and defeat the dragon in the final room.",
        "entry": "Heat, claw marks, and old scales reveal a dragon lair.",
        "side": "Spend 2 Clues before the final room to learn the dragon type.",
        "complication": "Dragon type is rolled from the TAG table: Small, Young Red, Darkness, or Ghoul Dragon.",
        "final_title": "Dragon Hoard",
        "final_description": "The dragon waits on its hoard. Roll or choose the TAG dragon type before combat.",
        "final_foe": "Young Dragon",
        "final_count": 1,
        "rewards": "Dragon treasure per the selected dragon profile.",
        "rules": ["Four-room target.", "Use Young Red Dragon if the type roll selects that printed result."],
    },
    4: {
        "title": "Fiendish Abyss",
        "pdf_pages": "TAG p.45",
        "objective": "Resolve an Abyss-themed dungeon and free or exploit any lair prisoner result.",
        "entry": "Abyssal sigils mark the entrance.",
        "side": "Spend 2 Clues to learn the Final Boss nature before the ending.",
        "complication": "Use Fiendish Foes/Abyss monsters; if absent, raise monster levels and minor counts as printed.",
        "final_title": "Abyssal Lair",
        "final_description": "The abyssal final boss guards a prisoner or treasure hook. Roll the lair prisoner table manually.",
        "final_foe": "Wraith",
        "final_count": 1,
        "rewards": "Lair prisoner reward table: noble mission, merchant reward/rumor, or silver knife/holy water/map.",
        "rules": ["No normal Final Boss check; ends at HCL+5 rooms."],
    },
    5: {
        "title": "Minotaur Maze",
        "pdf_pages": "TAG pp.46-47",
        "objective": "Navigate d6+5 rooms, avoid getting lost, and defeat the minotaur lord.",
        "entry": "Passages turn back on themselves and hoofprints cross in every direction.",
        "side": "Searching empty rooms or corridors can reveal shortcuts.",
        "complication": "Truncated rooms can dead-end; backtracking may get the party lost on 3-in-6.",
        "final_title": "Minotaur Lord's Maze",
        "final_description": "The minotaur lord blocks the maze heart. Apply halfling and first-defense restrictions from TAG.",
        "final_foe": "Minotaur Lord",
        "final_count": 1,
        "rewards": "Treasure +1 from the minotaur lord.",
        "rules": ["d6+5-room target.", "Young/adult minotaur replacement tables are indexed as TAG foes but not auto-rolled for room replacement yet."],
    },
    6: {
        "title": "Bandit Hideout",
        "pdf_pages": "TAG p.48",
        "objective": "Clear the hideout after HCL+3 rooms and decide whether to capture the chieftain alive.",
        "entry": "Boot tracks and stolen goods point into the hideout.",
        "side": "Each room has a 1-in-6 stolen-goods chance in the printed theme.",
        "complication": "Rooms may have trapdoors; final boss is a chieftain with bandit guards.",
        "final_title": "Bandit Chieftain's Den",
        "final_description": "The chieftain and guards defend the loot. Capturing the chieftain alive changes the reward.",
        "final_foe": "Bandit Chieftain",
        "final_count": 1,
        "final_extra_foes": [{"name": "TAG Bandits", "count": 6}],
        "rewards": "8d6 gp, random magic item, plus bounty or free rumor if captured alive.",
        "rules": ["Final encounter includes the chieftain and TAG Bandits as guards."],
    },
}

TAG_MINOR_QUEST_PROFILES: dict[int, dict[str, object]] = {
    1: {
        "title": "Clean Up My Castle",
        "pdf_pages": "TAG p.55",
        "objective": "Clear the patron's ten-room castle without leaving and returning.",
        "entry": "The ruined castle is still legally owned by the patron.",
        "side": "A hidden portrait cache can be found by spending 1 Clue.",
        "complication": "No exit/re-enter; count slain minions, vermin, Weird Monsters, and Bosses for payment.",
        "final_title": "Castle Last Holdout",
        "final_description": "The last squatters make their stand. Track the printed per-foe payment manually.",
        "final_foe": "Wraith",
        "final_count": 1,
        "rewards": "25 gp per character, 2 gp per minion/vermin, 20 gp per Boss/Weird, possible 100 gp portrait cache.",
        "rules": ["Ten-room quest target."],
    },
    2: {
        "title": "Gorungar the Mighty",
        "pdf_pages": "TAG p.55",
        "objective": "Defeat or capture Gorungar and his goblin archers.",
        "entry": "Gorungar's archers choose ground with clear lines of fire.",
        "side": "The armband and coin bag can be claimed after victory.",
        "complication": "Printed encounter: 2d6 goblin archers plus Gorungar, with poison arrows and surprise chance.",
        "final_title": "Gorungar's Ambush",
        "final_description": "Gorungar bellows orders while archers fire from cover.",
        "final_foe": "Gorungar the Mighty",
        "final_count": 1,
        "final_extra_foes": [{"name": "Gorungar's Goblin Archers", "count": 8}],
        "rewards": "50 gp for his head or 100 gp alive, plus armband and coin bag.",
        "rules": ["Final encounter includes Gorungar and goblin archers; roll 2d6 archers manually if you want the exact count."],
    },
    3: {
        "title": "Griffin Omelets, Anyone?",
        "pdf_pages": "TAG p.54+",
        "objective": "Recover griffin eggs for the guild patron.",
        "entry": "Claw marks and feathers lead to a high nesting site.",
        "side": "The nest approach should be treated as a dangerous climb or wilderness scene.",
        "complication": "Exact extended text still needs PDF signoff beyond the available extraction.",
        "final_title": "Griffin Nest",
        "final_description": "The nest is guarded. Resolve the exact griffin/egg handling from the PDF during play.",
        "final_foe": "Griffin",
        "final_count": 1,
        "rewards": "Guild job reward per the printed quest.",
        "rules": ["Griffin is a TAG-specific foe profile; resolve egg handling from the printed quest."],
    },
    4: {
        "title": "A Portrait in Red",
        "pdf_pages": "TAG p.54+",
        "objective": "Resolve the guild's bloody portrait commission.",
        "entry": "A patron wants the party to recover or investigate a disturbing portrait.",
        "side": "Use town clues and scene text to identify the patron's real need.",
        "complication": "Exact extended text still needs PDF signoff beyond the available extraction.",
        "final_title": "Red Gallery",
        "final_description": "The portrait's secret is revealed in the gallery.",
        "final_foe": "Red Portrait Horror",
        "final_count": 1,
        "rewards": "Guild job reward per the printed quest.",
        "rules": ["Red Portrait Horror is a generated foe profile for the supernatural finale."],
    },
    5: {
        "title": "Sewers Search",
        "pdf_pages": "TAG p.54+",
        "objective": "Search the settlement sewers for the guild target.",
        "entry": "The trail drops below the street grates.",
        "side": "The sewer route can be handled as a compact dungeon.",
        "complication": "Exact extended text still needs PDF signoff beyond the available extraction.",
        "final_title": "Sewer Sump",
        "final_description": "The search ends in a foul sump chamber.",
        "final_foe": "Skeletons/Zombies",
        "final_count": 6,
        "rewards": "Guild job reward per the printed quest.",
        "rules": ["Skeletons/Zombies are a sewer-danger proxy."],
    },
    6: {
        "title": "Monoceros Hunt",
        "pdf_pages": "TAG p.54+",
        "objective": "Track and resolve the monoceros hunt.",
        "entry": "The quarry's tracks leave deep, single-horn gouges.",
        "side": "Treat pursuit as wilderness tracking before the final confrontation.",
        "complication": "Exact extended text still needs PDF signoff beyond the available extraction.",
        "final_title": "Monoceros Glade",
        "final_description": "The hunt catches up with the monoceros in a secluded glade.",
        "final_foe": "Monoceros",
        "final_count": 1,
        "rewards": "Guild job reward per the printed quest.",
        "rules": ["Monoceros is a generated foe profile; resolve pursuit and reward from the printed quest."],
    },
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


def resolve_tag_branch_action(
    campaign: CampaignState,
    character: Character | None = None,
    *,
    branch_action: str,
    reference: str = "",
    clue_cost: int = 0,
    reward_gp: int = 0,
) -> TagDowntimeLogEntry:
    clean_action = branch_action if branch_action in TAG_BRANCH_ACTIONS else "social_choice"
    label = reference.strip()[:120] or TAG_BRANCH_ACTIONS[clean_action]
    cost = max(0, int(clue_cost))
    reward = max(0, int(reward_gp))
    roll: int | None = None
    total: int | None = None
    parts: list[str] = [f"{TAG_BRANCH_ACTIONS[clean_action]}: {label}."]
    if clean_action == "spend_clues":
        if character is None:
            parts.append("Choose a character before spending Clues.")
        elif character.clues < cost:
            parts.append(f"{character.name} needs {cost} Clue(s) but has {character.clues}.")
        else:
            character.clues -= cost
            character.updated_at = now_utc()
            parts.append(f"{character.name} spends {cost} Clue(s); remaining Clues {character.clues}.")
    elif clean_action == "roll_variable_count":
        roll = roll_d6()
        total = roll + max(0, int(clue_cost))
        parts.append(f"Variable count roll d6={roll} plus modifier {max(0, int(clue_cost))} gives {total}. Apply the printed count formula.")
    elif clean_action == "capture_alive":
        if character is not None:
            character.clues += 1
            character.updated_at = now_utc()
            parts.append(f"{character.name} records the capture-alive information reward and gains 1 Clue.")
        else:
            parts.append("Capture-alive outcome logged; choose the receiving character manually if a Clue is awarded.")
    elif clean_action == "claim_reward":
        if character is not None and reward:
            character.gold += reward
            character.updated_at = now_utc()
            parts.append(f"{character.name} receives {reward} gp.")
        elif reward:
            campaign.tag_storage_gold_gp += reward
            parts.append(f"{reward} gp added to TAG settlement storage.")
        else:
            parts.append("Printed reward claimed; add non-gold items or XP manually where required.")
    else:
        parts.append("Choice branch logged. Apply any printed social consequence, hostility shift, or scene branch.")
    return append_tag_log(
        campaign,
        action=f"branch_{clean_action}",
        character=character,
        roll=roll,
        total=total,
        cost_gp=0,
        result_text=" ".join(parts),
    )


def resolve_tag_route_action(
    campaign: CampaignState,
    character: Character | None = None,
    *,
    route_action: str,
    reference: str = "",
    clue_cost: int = 0,
) -> TagDowntimeLogEntry:
    action = route_action if route_action in TAG_ROUTE_ACTIONS else "parley_success"
    cost = max(0, int(clue_cost))
    label = reference.strip()[:120] or TAG_ROUTE_ACTIONS[action]
    resolved = action != "clue_gate_blocked"
    parts = [f"{TAG_ROUTE_ACTIONS[action]}: {label}."]
    if action == "clue_gate_unlocked":
        if character is None:
            resolved = False
            parts.append("Choose the character spending Clues before unlocking this route.")
        elif character.clues < cost:
            resolved = False
            parts.append(f"{character.name} needs {cost} Clue(s) but has {character.clues}; route remains blocked.")
        else:
            character.clues -= cost
            character.updated_at = now_utc()
            parts.append(f"{character.name} spends {cost} Clue(s); route is unlocked and remaining Clues are {character.clues}.")
    elif action == "clue_gate_blocked":
        parts.append(f"Route remains blocked until {cost} Clue(s) are available.")
    elif action == "parley_success":
        parts.append("Peaceful/social path recorded; suppress hostile proxy combat unless a later printed scene calls for it.")
    elif action == "parley_failed":
        parts.append("Failed social path recorded; use the hostile scene or encounter proxy named in the TAG reference.")
    elif action == "hostile_branch":
        parts.append("Hostile path selected; keep final foe, escape limits, and no-withdrawal notes from the TAG reference visible.")
    elif action == "peaceful_branch":
        parts.append("Peaceful path selected; apply printed reward, information, or bypass notes without forcing combat.")
    elif action == "skip_scene":
        parts.append("Scene is skipped/crossed off for this TAG adventure.")
    elif action == "unlock_scene":
        parts.append("Follow-up scene is now unlocked for this TAG adventure.")
    elif action == "solo_restriction":
        parts.append("Printed solo restriction recorded; enforce it before starting or continuing the generated module if desired.")
    else:
        parts.append("Finale route selected; use the final foe/reward profile in the generated adventure reference.")
    result = " ".join(parts)
    campaign.tag_adventure_routes.append(
        TagAdventureRouteState(
            route_action=action,
            reference=label,
            character_id=character.id if character else None,
            character_name=character.name if character else None,
            clue_cost=cost,
            resolved=resolved,
            result_text=result,
            created_at=now_utc(),
        )
    )
    return append_tag_log(
        campaign,
        action=f"route_{action}",
        character=character,
        result_text=result,
    )


def resolve_tag_xp_action(
    campaign: CampaignState,
    character: Character | None = None,
    *,
    xp_action: str,
    reference: str = "",
    xp: int = 0,
) -> TagDowntimeLogEntry:
    action = xp_action if xp_action in TAG_XP_ACTIONS else "mark_scene_xp"
    amount = max(0, int(xp))
    label = reference.strip()[:120] or TAG_XP_ACTIONS[action]
    applied = False
    parts = [f"{TAG_XP_ACTIONS[action]}: {label}."]
    if action == "award_scene_xp":
        if character is None:
            parts.append("Choose a character before awarding XP.")
        elif amount <= 0:
            parts.append("Enter an XP amount above 0 before awarding XP.")
        else:
            character.xp += amount
            character.updated_at = now_utc()
            applied = True
            parts.append(f"{character.name} gains {amount} XP; total XP is {character.xp}.")
    elif action == "mark_minor_encounters":
        parts.append(f"Mark {amount or 1} minor encounter(s) for end-of-adventure XP accounting.")
    elif action == "mark_capture_xp":
        parts.append("Capture-alive XP/consequence marker recorded; apply the printed XP timing at closeout.")
    elif action == "mark_training_xp_roll":
        if character is not None and "TAG Deoldyn archery XP roll pending" not in character.statuses:
            character.statuses.append("TAG Deoldyn archery XP roll pending")
            character.updated_at = now_utc()
        parts.append("Training XP roll marker recorded for the printed archery advancement check.")
    else:
        parts.append("Scene XP marker recorded for end-of-adventure closeout.")
    result = " ".join(parts)
    campaign.tag_xp_markers.append(
        TagXpMarkerState(
            xp_action=action,
            reference=label,
            character_id=character.id if character else None,
            character_name=character.name if character else None,
            xp=amount,
            applied=applied,
            result_text=result,
            created_at=now_utc(),
        )
    )
    return append_tag_log(
        campaign,
        action=f"xp_{action}",
        character=character,
        total=amount if amount else None,
        result_text=result,
    )


def _tag_bank_account(campaign: CampaignState, character: Character) -> TagBankAccountState:
    account = next((item for item in campaign.tag_bank_accounts if item.owner_character_id == character.id), None)
    if account is None:
        account = TagBankAccountState(
            owner_character_id=character.id,
            owner_name=character.name,
            created_at=now_utc(),
        )
        campaign.tag_bank_accounts.append(account)
    account.owner_name = character.name
    return account


def resolve_tag_scene_action(
    campaign: CampaignState,
    character: Character,
    *,
    scene_action: str,
    amount: int = 0,
) -> TagDowntimeLogEntry:
    action = scene_action if scene_action in TAG_SCENE_ACTIONS else "medusa_pendant"
    value = max(0, int(amount))
    roll: int | None = None
    total: int | None = None
    result = ""
    if action == "medusa_pendant":
        character.inventory.append("Medusa pendant (260 gp, necros)")
        result = f"{character.name} receives the Medusa pendant item note (260 gp and necros value; Luck test remains per scene text)."
    elif action == "gargoyle_bounty":
        count = value or 1
        reward = 15 * count
        character.gold += reward
        result = f"{character.name} claims {reward} gp for {count} white gargoyle head(s)."
    elif action == "gorungar_head":
        character.gold += 50
        character.inventory.append("Gorungar armband")
        roll = roll_d6() + roll_d6()
        character.gold += roll
        result = f"{character.name} claims 50 gp for Gorungar's head, Gorungar's armband, and {roll} gp from his bag."
    elif action == "gorungar_alive":
        character.gold += 100
        character.inventory.append("Gorungar armband")
        roll = roll_d6() + roll_d6()
        character.gold += roll
        result = f"{character.name} claims 100 gp for bringing Gorungar alive, Gorungar's armband, and {roll} gp from his bag."
    elif action == "bandit_chieftain_capture":
        character.gold += 100
        character.clues += 1
        result = f"{character.name} claims the Bandit Chieftain alive bounty: 100 gp and 1 information Clue."
    elif action == "shaura_reward":
        character.gold += 150
        result = f"{character.name} claims the Shaura cult reward: 150 gp. Record XP from the final fight normally."
    elif action == "daroc_cat":
        character.gold += 100
        character.statuses.append("TAG Daroc cat XP pending")
        result = f"{character.name} receives Daroc's 100 gp reward and an XP-pending marker."
    elif action == "mutant_fish_rations":
        roll = roll_d6()
        total = roll + 3
        character.inventory.extend(["Food ration"] * total)
        result = f"{character.name} receives {total} food ration(s) from the mutant fish scene; count the scene as two minion encounters for XP."
    elif action == "agaratha":
        if "Agaratha" not in character.inventory:
            character.inventory.append("Agaratha")
        character.statuses.append("TAG Agaratha Luck-on-major-kill")
        result = f"{character.name} receives Agaratha, a magic masterwork sword; Luck-on-major-kill marker added."
    elif action == "deoldyn_training":
        cost = max(60 * max(1, character.level), value)
        if character.gold < cost:
            result = f"{character.name} needs {cost} gp for Deoldyn's archery training."
        else:
            character.gold -= cost
            character.statuses.append("TAG Deoldyn archery XP roll pending")
            result = f"{character.name} pays {cost} gp for Deoldyn training; archery XP roll marker added."
    elif action == "dragon_type_reveal":
        if character.clues < 2:
            result = f"{character.name} needs 2 Clues to reveal the TAG Dragon's Lair type."
        else:
            character.clues -= 2
            roll = roll_d6()
            dragon = {
                1: "Small Dragon",
                2: "Small Dragon",
                3: "Small Dragon",
                4: "Young Red Dragon",
                5: "Young Red Dragon",
                6: "Darkness Dragon or Ghoul Dragon; split by the printed d6 follow-up.",
            }[roll]
            result = f"{character.name} spends 2 Clues and reveals TAG Dragon's Lair type roll {roll}: {dragon}"
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action=f"scene_{action}",
        character=character,
        roll=roll,
        total=total,
        result_text=result,
    )


def use_tag_trinket(campaign: CampaignState, character: Character, *, trinket_key: str) -> TagDowntimeLogEntry:
    effect = TAG_TRINKET_EFFECTS.get(trinket_key)
    if effect is None:
        return append_tag_log(campaign, action="use_trinket", character=character, result_text=f"Unknown TAG trinket: {trinket_key}.")
    item = str(effect.get("item") or effect["name"])
    if item in character.inventory:
        character.inventory.remove(item)
        consumed = True
    else:
        consumed = False
    if effect.get("heal_full"):
        character.current_life = character.max_life
        character.statuses = [
            status
            for status in character.statuses
            if "poison" not in status.lower() and "disease" not in status.lower()
        ]
    status = effect.get("status")
    if isinstance(status, str) and status not in character.statuses:
        character.statuses.append(status)
    character.updated_at = now_utc()
    consume_text = "consumed from inventory" if consumed else "not found in inventory; effect logged without consuming an item"
    return append_tag_log(
        campaign,
        action="use_trinket",
        character=character,
        result_text=f"{character.name} uses {effect['name']} ({consume_text}). {effect['summary']}",
    )


def cast_tag_guild_spell(campaign: CampaignState, character: Character, *, spell_key: str) -> TagDowntimeLogEntry:
    effect = TAG_GUILD_SPELL_EFFECTS.get(spell_key)
    if effect is None:
        return append_tag_log(campaign, action="guild_spell", character=character, result_text=f"Unknown TAG Guild spell: {spell_key}.")
    spell_name = str(effect["name"])
    if spell_name not in character.spells and f"Scroll of {spell_name}" not in character.inventory:
        availability = "spell not found on character; effect logged for manual scroll/caster handling"
    elif f"Scroll of {spell_name}" in character.inventory:
        character.inventory.remove(f"Scroll of {spell_name}")
        availability = "scroll consumed"
    else:
        availability = "known spell cast; mark the spell slot manually if needed"
    status = effect.get("status")
    if effect.get("heal_full"):
        character.current_life = character.max_life
    if isinstance(status, str) and status not in character.statuses:
        character.statuses.append(status)
    if spell_key == "look_tough" and character.id not in campaign.tag_look_tough_character_ids:
        campaign.tag_look_tough_character_ids.append(character.id)
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action="guild_spell",
        character=character,
        result_text=f"{character.name} casts {spell_name}: {availability}. {effect['summary']}",
    )


def resolve_tag_finance_action(
    campaign: CampaignState,
    character: Character | None = None,
    *,
    finance_action: str,
    amount_gp: int = 0,
    note: str = "",
) -> TagDowntimeLogEntry:
    amount = max(0, int(amount_gp))
    clean_note = note.strip()[:120]
    action = finance_action if finance_action in {
        "bank_deposit",
        "bank_withdraw",
        "inheritance",
        "inheritance_transfer",
        "robbery_risk",
        "robbery_recovery",
        "loan_enforcement",
        "guild_upkeep",
    } else "loan_enforcement"
    if action == "bank_deposit":
        if character is None:
            return append_tag_log(campaign, action="bank_deposit", result_text="Choose a character for TAG bank deposit.")
        fee = ceil(amount * 0.1) if amount else 0
        total_cost = amount + fee
        if amount <= 0:
            result = "Enter a bank deposit amount above 0 gp."
        elif character.gold < total_cost:
            result = f"{character.name} needs {total_cost} gp for a {amount} gp TAG bank deposit plus {fee} gp fee."
        else:
            account = _tag_bank_account(campaign, character)
            character.gold -= total_cost
            account.gold_gp += amount
            account.notes = clean_note or account.notes
            character.updated_at = now_utc()
            result = f"{character.name} deposits {amount} gp into a TAG bank account and pays {fee} gp fee. Account balance {account.gold_gp} gp."
        return append_tag_log(campaign, action="bank_deposit", character=character, cost_gp=total_cost if amount else 0, result_text=result)
    if action == "bank_withdraw":
        if character is None:
            return append_tag_log(campaign, action="bank_withdraw", result_text="Choose a character for TAG bank withdrawal.")
        account = _tag_bank_account(campaign, character)
        withdrawn = min(amount, account.gold_gp)
        if withdrawn <= 0:
            result = f"{character.name}'s TAG bank account has no gold to withdraw."
        else:
            account.gold_gp -= withdrawn
            character.gold += withdrawn
            character.updated_at = now_utc()
            result = f"{character.name} withdraws {withdrawn} gp from TAG bank account. Account balance {account.gold_gp} gp."
        return append_tag_log(campaign, action="bank_withdraw", character=character, result_text=result)
    if action == "inheritance":
        if character is not None:
            account = _tag_bank_account(campaign, character)
            account.heir_name = clean_note
        result = (
            f"Bank inheritance recorded for {character.name}: {clean_note or 'heir noted in campaign log'}. "
            "Apply the 20% inheritance tax when transferred."
            if character is not None
            else "Bank inheritance note recorded. Choose an account owner for exact transfer handling."
        )
        return append_tag_log(campaign, action="bank_inheritance", character=character, result_text=result)
    if action == "inheritance_transfer":
        if character is None:
            return append_tag_log(campaign, action="bank_inheritance_transfer", result_text="Choose the heir/recipient character for inheritance transfer.")
        donor = next((account for account in campaign.tag_bank_accounts if account.heir_name and account.heir_name.lower() in character.name.lower()), None)
        if donor is None:
            result = f"No TAG bank account names {character.name} as heir. Record an inheritance note first or transfer manually."
        elif donor.gold_gp <= 0:
            result = f"{donor.owner_name}'s TAG bank account has no gold to inherit."
        else:
            tax = ceil(donor.gold_gp * 0.2)
            transferred = max(0, donor.gold_gp - tax)
            character.gold += transferred
            donor.gold_gp = 0
            donor.notes = f"Inherited by {character.name}; tax {tax} gp."
            character.updated_at = now_utc()
            result = f"{character.name} inherits {transferred} gp from {donor.owner_name}'s TAG bank account after {tax} gp inheritance tax."
        return append_tag_log(campaign, action="bank_inheritance_transfer", character=character, result_text=result)
    if action == "robbery_risk":
        total, rolls = roll_3d6()
        robbed = total <= 5
        result = (
            f"Bank/hidden-storage robbery risk {total} ({'+'.join(str(roll) for roll in rolls)}): "
            + ("robbery or theft occurs; use recovery action if pursuing it." if robbed else "storage remains safe.")
        )
        return append_tag_log(campaign, action="bank_robbery_risk", character=character, roll=total, total=total, result_text=result)
    if action == "robbery_recovery":
        cost_clues = 4
        if character is not None and character.clues >= cost_clues:
            character.clues -= cost_clues
            character.updated_at = now_utc()
            result = f"{character.name} spends 4 Clues to pursue stolen TAG funds. Resolve Interrogation vs L6 and restore recovered holdings on success."
        else:
            result = "Robbery recovery requires 4 Clues on a chosen character, then Interrogation vs L6."
        return append_tag_log(campaign, action="bank_robbery_recovery", character=character, result_text=result)
    if action == "guild_upkeep":
        upkeep = ceil(max(0, campaign.tag_guild_coffers_gp) * 0.1)
        paid = min(upkeep, campaign.tag_guild_coffers_gp)
        campaign.tag_guild_coffers_gp -= paid
        result = f"Guild upkeep charged 10%: {paid} gp paid from coffers. Coffers now {campaign.tag_guild_coffers_gp} gp."
        if campaign.tag_guild_coffers_gp <= 0:
            result += " Guild benefits are suspended until coffers are restored."
        return append_tag_log(campaign, action="guild_upkeep", character=character, cost_gp=paid, result_text=result)
    entry = roll_moneylender_follow_chance(campaign, debt_gp=amount)
    entry.action = "loan_enforcement"
    if clean_note:
        entry.result_text += f" Note: {clean_note}."
    return entry


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
    profile: dict[str, object],
    final_room_title: str,
    final_room_description: str,
) -> dict[str, object]:
    final_foe = str(profile.get("final_foe") or "Wraith")
    final_count = max(1, int(profile.get("final_count") or 1))
    final_extra_foes = [
        {"name": str(foe.get("name")), "count": max(1, int(foe.get("count", 1)))}
        for foe in profile.get("final_extra_foes", [])
        if isinstance(foe, dict) and foe.get("name")
    ]
    final_foes = [{"name": final_foe, "count": final_count}, *final_extra_foes]
    source_parameters = {
        "origin": "Tales from the Adventurers' Guild",
        "lead_type": lead_type,
        "lead_detail": lead_detail,
        "tag_reference": {
            "title": profile.get("title", lead_detail),
            "scene": profile.get("scene", ""),
            "pdf_pages": profile.get("pdf_pages", ""),
            "rules": profile.get("rules", []),
            "rewards": profile.get("rewards", ""),
            "final_foe_proxy": final_foe,
            "final_foe_count": final_count,
            "final_foes": final_foes,
        },
    }
    return {
        "schema_version": 1,
        "id": adventure_id,
        "title": title,
        "synopsis": synopsis,
        "source": {
            "type": "hand",
            "parameters": source_parameters,
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
                "boss_name": final_foe,
                "room_id": "tag-final-scene",
            },
        },
        "npcs": [
            {
                "id": "tag-contact",
                "name": "Guild Contact",
                "room_id": "tag-lead-entry",
                "description": str(profile.get("entry") or "A local contact points the troupe toward the lead recorded in the TAG settlement log."),
                "dialogue": objective,
            }
        ],
        "rooms": [
            {
                "id": "tag-lead-entry",
                "tile_key": "02",
                "title": "Lead Trail",
                "description": str(profile.get("entry") or "The party follows a TAG campaign lead out of the settlement. The first signs point north, while a side clue lies east."),
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
                "description": str(profile.get("side") or "Discarded gear and frightened local gossip confirm that the lead is real."),
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
                        "log": f"TAG note: {profile.get('rewards') or 'Record any printed reward from the source scene.'}",
                        "treasure": {"gold": 12, "items": []},
                    }
                ],
            },
            {
                "id": "tag-complication",
                "tile_key": "13",
                "title": "Complication",
                "description": str(profile.get("complication") or "Local troublemakers have reached the lead first."),
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
                        "log": f"TAG source {profile.get('pdf_pages') or 'page ?'}: {profile.get('complication') or 'Resolve the lead complication.'}",
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
                        "log": f"TAG final note: {profile.get('rewards') or 'Apply printed reward text after victory.'}",
                        "encounter": {"foes": final_foes},
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
            "victory_text": f"The party returns to the settlement with the TAG lead resolved. Reward note: {profile.get('rewards') or 'see source scene.'}",
            "defeat_text": "The TAG lead remains unresolved in the settlement records.",
        },
    }


def _profile_title(profile: dict[str, object], fallback: str) -> str:
    return str(profile.get("title") or fallback)


def _profile_synopsis(campaign: CampaignState, lead_detail: str, profile: dict[str, object]) -> str:
    pages = profile.get("pdf_pages")
    page_text = f" Source: {pages}." if pages else ""
    return f"Generated from TAG campaign downtime in {campaign.settlement_name}: {lead_detail}.{page_text}"


def _guild_job_profile(campaign: CampaignState, detail: str) -> tuple[str, str, dict[str, object]]:
    job_roll = int(detail) if detail.isdigit() else roll_d6()
    job_roll = max(1, min(6, job_roll))
    if job_roll <= 3:
        quest_roll = roll_d6()
        profile = TAG_MINOR_QUEST_PROFILES[quest_roll]
        lead_detail = f"Guild Job {job_roll}: Minor Unique Quest {quest_roll} - {_profile_title(profile, TAG_MINOR_UNIQUE_QUESTS[quest_roll])}"
    elif job_roll <= 5:
        rumor_roll = roll_d12()
        profile = TAG_RUMOR_PROFILES[rumor_roll]
        lead_detail = f"Guild Job {job_roll}: Rumor {rumor_roll} - {_profile_title(profile, TAG_RUMORS[rumor_roll])}"
        campaign.tag_used_rumor_numbers = sorted(set(campaign.tag_used_rumor_numbers + [rumor_roll]))
    else:
        theme_roll = roll_d6()
        profile = TAG_THEMATIC_DUNGEON_PROFILES[theme_roll]
        lead_detail = f"Guild Job {job_roll}: Thematic Dungeon {theme_roll} - {_profile_title(profile, TAG_THEMATIC_DUNGEONS[theme_roll])}"
    return f"Guild Job {job_roll}", lead_detail, profile


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
        profile = TAG_RUMOR_PROFILES[rumor_number]
        lead_detail = f"{_profile_title(profile, TAG_RUMORS[rumor_number])}: {profile.get('scene', 'TAG scene')}"
        campaign.tag_used_rumor_numbers = sorted(set(campaign.tag_used_rumor_numbers + [rumor_number]))
        title = f"TAG {label}: {_profile_title(profile, TAG_RUMORS[rumor_number])}"
        objective = str(profile.get("objective") or f"Investigate TAG {label} from the settlement rumor list.")
        final_title = str(profile.get("final_title") or f"{label} Resolution")
        final_description = str(profile.get("final_description") or f"This room represents the playable handoff for {lead_detail}")
    elif clean_type == "treasure_map":
        map_roll = int(clean_detail) if clean_detail.isdigit() else roll_d6()
        map_roll = max(1, min(6, map_roll))
        label = f"Treasure Map {map_roll}"
        lead_detail = TAG_MAP_LEADS_TO[map_roll]
        profile = {
            "title": lead_detail.split(":", 1)[0],
            "pdf_pages": "TAG p.16",
            "objective": "Follow the purchased TAG treasure map and resolve the destination.",
            "entry": "The map marks a route away from the settlement.",
            "side": "Old notes in the margin hint at danger and possible false trails.",
            "complication": "Following the map can reveal a deathtrap, a waste of time, a partial clue, or a real destination.",
            "final_title": "Mapped Treasure Site",
            "final_description": lead_detail,
            "final_foe": "Wraith" if map_roll in {4, 5, 6} else "Goblins",
            "final_count": 1 if map_roll in {4, 5, 6} else 4,
            "rewards": "Apply The Map Leads To reward text for the rolled destination.",
            "rules": ["This generator uses The Map Leads To destinations, not the preliminary fake-map outcomes."],
        }
        title = f"TAG Treasure Map: {lead_detail.split(':', 1)[0]}"
        objective = str(profile["objective"])
        final_title = str(profile["final_title"])
        final_description = str(profile["final_description"])
    elif clean_type == "thematic_dungeon":
        theme_roll = int(clean_detail) if clean_detail.isdigit() else roll_d6()
        theme_roll = max(1, min(6, theme_roll))
        lead_detail = TAG_THEMATIC_DUNGEONS[theme_roll]
        profile = TAG_THEMATIC_DUNGEON_PROFILES[theme_roll]
        label = lead_detail
        title = f"TAG Thematic Dungeon: {_profile_title(profile, lead_detail)}"
        objective = str(profile.get("objective") or f"Resolve the TAG thematic dungeon lead: {lead_detail}.")
        final_title = str(profile.get("final_title") or lead_detail)
        final_description = str(profile.get("final_description") or f"This is the TAG adventure handoff for {lead_detail}.")
    else:
        label, lead_detail, profile = _guild_job_profile(campaign, clean_detail)
        title = f"TAG {label}: {_profile_title(profile, lead_detail)}"
        objective = str(profile.get("objective") or "Complete the work assigned by the Adventurers Guild job table.")
        final_title = str(profile.get("final_title") or label)
        final_description = str(profile.get("final_description") or lead_detail)
    adventure_id = _tag_adventure_id(clean_type, label)
    manifest = _tag_manifest(
        adventure_id=adventure_id,
        title=title[:120],
        synopsis=_profile_synopsis(campaign, lead_detail, profile),
        objective=objective,
        lead_type=clean_type,
        lead_detail=lead_detail,
        profile=profile,
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
