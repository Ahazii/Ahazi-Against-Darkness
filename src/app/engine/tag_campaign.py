"""TAG campaign shell — persistent settlement/downtime state (TAG p.9–15, p.23–24)."""

from __future__ import annotations

import json
import os
from math import ceil
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ..db import now_utc
from .adventure_import import ADVENTURE_MANIFEST_FILENAME, installed_adventure_dir
from ..schemas import (
    CampaignState,
    CampaignChronicleEntry,
    Character,
    GuidanceTaskState,
    Party,
    SessionState,
    TagAvailabilityCheckState,
    TagAdventureRouteState,
    TagBankAccountState,
    TagCloseoutTaskState,
    TagDowntimeLogEntry,
    TagMagicLockerState,
    TagSettlementState,
    TagStoredItemState,
    TagTravelLogEntry,
    TagXpMarkerState,
    WorldCampaignRecord,
    WorldGuildRecord,
    WorldSettlementRecord,
    WorldTroupeRecord,
)
from .abyss_tables import is_abyss_profile
from .dice import roll_d6
from .tier_advancement import level_tier_band

if TYPE_CHECKING:
    from ..db import Store

DEFAULT_CAMPAIGN_ID = "default"
DEFAULT_WORLD_CAMPAIGN_ID = "norindaal"
DEFAULT_WORLD_GUILD_ID = "adventurers-guild"
DEFAULT_WORLD_TROUPE_ID = "troupe1"
DEFAULT_WORLD_SETTLEMENT_ID = "brightwater-gate"
DEFAULT_WORLD_CAMPAIGN_NAME = "Norindaal"
DEFAULT_WORLD_GUILD_NAME = "Adventurers Guild"
DEFAULT_WORLD_TROUPE_NAME = "Troupe1"
DEFAULT_WORLD_SETTLEMENT_NAME = "Hearthmere"
TAG_NARRATIVE_OVERRIDES_FILENAME = "tag_scene_narrative_overrides.json"
TAG_LOG_LIMIT = 20
CAMPAIGN_CHRONICLE_LIMIT = 120
GUIDANCE_TASK_LIMIT = 80
TAG_GUILD_STARTING_COFFERS_GP = 5000


def _data_dir() -> Path:
    data_dir = Path(os.getenv("DATA_DIR", ".data"))
    if data_dir.is_absolute():
        return data_dir
    return (Path(__file__).resolve().parents[3] / data_dir).resolve()


def tag_narrative_overrides_path() -> Path:
    return _data_dir() / TAG_NARRATIVE_OVERRIDES_FILENAME


def load_tag_narrative_overrides() -> dict[str, Any]:
    path = tag_narrative_overrides_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _profile_override_candidates(lead_type: str, label: str, lead_detail: str, profile: dict[str, object]) -> list[str]:
    values = [
        profile.get("rumor_number"),
        profile.get("map_roll"),
        profile.get("thematic_dungeon_number"),
        profile.get("scene"),
        profile.get("title"),
        label,
        lead_detail,
    ]
    candidates: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        candidates.append(text)
        digits = "".join(ch for ch in text if ch.isdigit())
        if digits:
            candidates.append(digits)
    if lead_type == "guild_job":
        scene = str(profile.get("scene") or "").strip()
        if scene:
            candidates.append(scene)
    seen: set[str] = set()
    unique: list[str] = []
    for candidate in candidates:
        key = candidate.lower()
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _lookup_tag_narrative_override(lead_type: str, label: str, lead_detail: str, profile: dict[str, object]) -> dict[str, Any]:
    data = load_tag_narrative_overrides()
    tag_data = data.get("tag", {}) if isinstance(data.get("tag", {}), dict) else {}
    candidates = _profile_override_candidates(lead_type, label, lead_detail, profile)
    sections = [tag_data.get(lead_type, {})]
    if lead_type == "guild_job":
        sections.extend(tag_data.get(name, {}) for name in ("rumor", "thematic_dungeon", "treasure_map"))
    scene_overrides = tag_data.get("scene", {})
    if isinstance(scene_overrides, dict):
        sections.append(scene_overrides)
    for section in sections:
        if not isinstance(section, dict):
            continue
        for candidate in candidates:
            value = section.get(candidate) or section.get(candidate.lower())
            if isinstance(value, dict):
                return value
    return {}


def _apply_tag_narrative_override(
    profile: dict[str, object],
    *,
    lead_type: str,
    label: str,
    lead_detail: str,
) -> dict[str, object]:
    override = _lookup_tag_narrative_override(lead_type, label, lead_detail, profile)
    if not override:
        return profile
    merged: dict[str, object] = {**profile}
    for key in [
        "title",
        "objective",
        "entry",
        "side",
        "complication",
        "complication_guidance",
        "final_title",
        "final_description",
        "finale_instruction",
        "rewards",
        "side_reward_note",
        "final_reward_note",
    ]:
        if key in override:
            merged[key] = override[key]
    if isinstance(override.get("rooms"), dict):
        merged["room_narrative_overrides"] = override["rooms"]
    if isinstance(override.get("npcs"), dict):
        merged["npc_narrative_overrides"] = override["npcs"]
    if override.get("module_title"):
        merged["module_title"] = override["module_title"]
    return merged


def _room_override(profile: dict[str, object], room_id: str) -> dict[str, Any]:
    overrides = profile.get("room_narrative_overrides", {})
    if not isinstance(overrides, dict):
        return {}
    value = overrides.get(room_id)
    return value if isinstance(value, dict) else {}


def _room_title(profile: dict[str, object], room_id: str, fallback: str) -> str:
    override = _room_override(profile, room_id)
    return str(override.get("title") or fallback)


def _room_description(profile: dict[str, object], room_id: str, fallback: str) -> str:
    override = _room_override(profile, room_id)
    return str(override.get("description") or fallback)


def _room_log(profile: dict[str, object], room_id: str, fallback: str) -> str:
    override = _room_override(profile, room_id)
    return str(override.get("log") or override.get("on_enter_log") or fallback)


def _clean_pdf_text(text: str) -> str:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw.strip()
        if not line:
            continue
        if "James Banner" in line and "Order #" in line:
            continue
        if line in {"Tales from the Adventurers' Guild", "Tales from the Adventurers’ Guild"}:
            continue
        lines.append(line)
    joined = "\n".join(lines).replace("-\n", "")
    return "\n".join(line.strip() for line in joined.splitlines() if line.strip())


def _extract_tag_pdf_text(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pypdf is required to extract uploaded rule PDF text.") from exc
    reader = PdfReader(str(pdf_path))
    return _clean_pdf_text("\n".join(page.extract_text() or "" for page in reader.pages))


def _extract_numbered_blocks(text: str, start_marker: str, stop_markers: tuple[str, ...]) -> dict[int, str]:
    start = text.lower().find(start_marker.lower())
    if start < 0:
        return {}
    end = len(text)
    lower = text.lower()
    for marker in stop_markers:
        found = lower.find(marker.lower(), start + len(start_marker))
        if found >= 0:
            end = min(end, found)
    blocks: dict[int, list[str]] = {}
    current: int | None = None
    for line in text[start:end].splitlines():
        clean = line.strip()
        if clean.isdigit():
            value = int(clean)
            if 1 <= value <= 12:
                current = value
                blocks.setdefault(current, [])
            else:
                current = None
            continue
        if current is not None:
            blocks[current].append(clean)
    return {key: " ".join(value).strip() for key, value in blocks.items() if " ".join(value).strip()}


def _extract_tag_pdf_rumors(text: str) -> dict[int, str]:
    start = text.lower().find("rumors (d12)")
    if start < 0:
        return {}
    lower = text.lower()
    end = lower.find("\nscenes\n", start)
    if end < 0:
        end = len(text)
    blocks: dict[int, list[str]] = {}
    current: int | None = None
    for line in text[start:end].splitlines():
        clean = line.strip()
        if not clean:
            continue
        if clean.lower() == "scenes":
            break
        if clean.lower().startswith("red herring table"):
            current = None
            continue
        if clean.isdigit():
            value = int(clean)
            if 1 <= value <= 12:
                current = value
                blocks.setdefault(current, [])
            else:
                current = None
            continue
        if current is not None:
            blocks[current].append(clean)
    return {key: " ".join(value).strip() for key, value in blocks.items() if " ".join(value).strip()}


def _extract_tag_pdf_scenes(text: str) -> dict[int, str]:
    import re

    scenes: dict[int, str] = {}
    pattern = re.compile(r"(?is)\bScene\s+(\d+)\s+(.*?)(?=\bScene\s+\d+\b|\bThematic Dungeons\b|\bTreasure Maps\b|\bThe Map Leads To\b|\Z)")
    for match in pattern.finditer(text):
        number = int(match.group(1))
        body = " ".join(match.group(2).split()).strip()
        if body:
            scenes[number] = body
    return scenes


def _scene_number_from_profile(profile: dict[str, object]) -> int | None:
    import re

    match = re.search(r"Scene\s+(\d+)", str(profile.get("scene") or ""))
    return int(match.group(1)) if match else None


def _set_if_overwrite(target: dict[str, Any], key: str, value: Any, overwrite: bool) -> bool:
    if value in (None, ""):
        return False
    if overwrite or key not in target or target.get(key) in (None, ""):
        target[key] = value
        return True
    return False


def merge_tag_pdf_narrative_overrides(pdf_path: Path, *, overwrite: bool = False) -> dict[str, Any]:
    """Extract local TAG scene prose into the user-editable narrative override file."""
    text = _extract_tag_pdf_text(pdf_path)
    rumors = _extract_tag_pdf_rumors(text)
    scenes = _extract_tag_pdf_scenes(text)
    path = tag_narrative_overrides_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_tag_narrative_overrides() or {"schema_version": 1}
    data.setdefault("schema_version", 1)
    data.setdefault(
        "note",
        "User-editable local narrative overrides generated from uploaded local rule PDFs. This file lives beside game.db and is not committed.",
    )
    tag = data.setdefault("tag", {})
    if not isinstance(tag, dict):
        data["tag"] = {}
        tag = data["tag"]
    rumor_section = tag.setdefault("rumor", {})
    scene_section = tag.setdefault("scene", {})
    changed = 0
    skipped = 0
    for rumor_number, profile in TAG_RUMOR_PROFILES.items():
        if not isinstance(profile, dict):
            continue
        scene_number = _scene_number_from_profile(profile)
        rumor_text = rumors.get(rumor_number, "")
        scene_text = scenes.get(scene_number or -1, "")
        if not rumor_text and not scene_text:
            continue
        item = rumor_section.setdefault(str(rumor_number), {})
        if not isinstance(item, dict):
            rumor_section[str(rumor_number)] = {}
            item = rumor_section[str(rumor_number)]
        room_overrides = item.setdefault("rooms", {})
        if not isinstance(room_overrides, dict):
            item["rooms"] = {}
            room_overrides = item["rooms"]
        module_title = f"The Adventures Guild Rumor {rumor_number}: {_profile_title(profile, TAG_RUMORS.get(rumor_number, str(rumor_number)))}"
        objective = str(profile.get("objective") or rumor_text or scene_text)
        for key, value in [("module_title", module_title), ("objective", objective)]:
            if _set_if_overwrite(item, key, value, overwrite):
                changed += 1
            else:
                skipped += 1
        if rumor_text:
            entry = room_overrides.setdefault("tag-lead-entry", {})
            if not isinstance(entry, dict):
                room_overrides["tag-lead-entry"] = {}
                entry = room_overrides["tag-lead-entry"]
            for key, value in [
                ("title", str(profile.get("title") or "Lead")),
                ("description", rumor_text),
                ("log", f"Objective: {objective}"),
            ]:
                if _set_if_overwrite(entry, key, value, overwrite):
                    changed += 1
                else:
                    skipped += 1
        if scene_text:
            final = room_overrides.setdefault("tag-final-scene", {})
            if not isinstance(final, dict):
                room_overrides["tag-final-scene"] = {}
                final = room_overrides["tag-final-scene"]
            for key, value in [
                ("title", str(profile.get("final_title") or f"Scene {scene_number}")),
                ("description", scene_text),
                ("log", scene_text),
            ]:
                if _set_if_overwrite(final, key, value, overwrite):
                    changed += 1
                else:
                    skipped += 1
            scene_key = f"Scene {scene_number}"
            scene_item = scene_section.setdefault(scene_key, {})
            if isinstance(scene_item, dict):
                for key, value in [("description", scene_text), ("source_pdf", pdf_path.name)]:
                    if _set_if_overwrite(scene_item, key, value, overwrite):
                        changed += 1
                    else:
                        skipped += 1
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {
        "path": str(path),
        "pdf": pdf_path.name,
        "rumors_found": len(rumors),
        "scenes_found": len(scenes),
        "changed_fields": changed,
        "skipped_existing_fields": skipped,
    }


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
    "ghastly_mine_minion_replacement": "Ghastly Mine minion replacement",
    "ghastly_mine_major_replacement": "Ghastly Mine major-foe replacement",
    "ghastly_mine_treasure_conversion": "Ghastly Mine treasure conversion",
    "ghastly_mine_cave_in": "Ghastly Mine cave-in trap",
    "fiendish_abyss_prisoner": "Fiendish Abyss prisoner table",
    "minotaur_maze_lost_check": "Minotaur Maze lost check",
    "minotaur_maze_wandering": "Minotaur Maze wandering monsters",
    "minotaur_maze_event": "Minotaur Maze special event",
    "castle_cleanup_pay": "Clean Up My Castle pay tally",
    "griffin_mountain_check": "Griffin mountain check",
    "griffin_nest_search": "Griffin nest search",
    "griffin_egg_count": "Griffin egg count",
    "griffin_egg_break": "Griffin egg break check",
    "portrait_outbound_check": "Portrait outbound travel check",
    "portrait_persuasion": "Portrait persuasion save",
    "portrait_return_snatch": "Portrait return snatch check",
    "sewers_vermin": "Sewers vermin table",
    "sewers_minions": "Sewers minions table",
    "sewers_disease": "Sewers disease check",
    "monoceros_tracking": "Monoceros tracking roll",
    "monoceros_clue_encounter": "Monoceros Clue shortcut encounter",
    "monoceros_hide": "Monoceros hide check",
    "bandit_stolen_goods_check": "Bandit stolen-goods check",
    "bofto_scene_choice": "Bofto scene choice",
    "tag_ambush_chance": "TAG ambush chance",
    "medusa_assassin_ambush": "Medusa assassin ambush",
    "medusa_stealth_approach": "Medusa stealth approach",
    "medusa_reaction": "Medusa reaction roll",
    "leprechaun_shoes": "Leprechaun shoes purchase",
    "leprechaun_illusion_spell": "Leprechaun illusion spell",
    "mutant_fish_hypnosis": "Mutant fish hypnosis save",
    "gargoyle_count": "White gargoyle count",
    "gargoyle_surprise": "White gargoyle surprise",
    "gargoyle_skin": "White gargoyle stone skin",
    "bofto_theft_save": "Bofto theft save",
    "star_object_will_save": "Star object Will save",
    "star_slayer_check": "Star-Slayer replacement check",
    "treasure_map_follow": "Following Treasure Map roll",
    "map_cave_room_count": "Treasure cave room count",
    "map_temple_idol": "Treasure temple idol value",
    "map_temple_scroll": "Treasure temple scroll chance",
    "map_humanoid_report": "Humanoid camp report reward",
    "map_humanoid_stealth": "Humanoid camp stealth entry",
    "map_humanoid_forces": "Humanoid camp forces",
    "map_structure_rooms": "Underground structure rooms",
    "map_lich_death_magic": "Lich chamber death magic",
    "map_lich_life": "Lich Life total",
    "map_lich_treasure": "Lich treasure roll",
    "giant_lair_boulder": "Giant's Lair boulder throw",
    "giant_lair_treasure": "Giant's Lair treasure reminder",
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
        "summary": "Target heals 2 Life per day instead of 1 while resting in a settlement; it does not affect dungeon rests or immediate adventure healing.",
        "status": "TAG Speedy Recovery settlement healing 2/day",
    },
    "temporary_weapon_enchantment": {
        "name": "Temporary Weapon Enchantment",
        "summary": "Mark one weapon as temporarily magical for one week, or until it is used in an encounter against foes hit only by magic weapons. It gives no Attack bonus.",
        "status": "TAG Temporary Weapon Enchantment: choose one weapon; magical no Attack bonus",
    },
    "troupe_switch": {
        "name": "Troupe Switch",
        "summary": "Once per adventure with troupe rules: mark the pre-chosen recipient who can replace the caster like Escape; summoned character is stunned at -1 Attack/Defense/Save through the encounter.",
        "status": "TAG Troupe Switch pending",
    },
    "look_tough": {
        "name": "Look Tough",
        "summary": "Next Streetwise roll adds +Level; if the roll already adds +Level, add the character tier number instead. The marker is consumed on that roll.",
        "status": "TAG Look Tough next Streetwise bonus",
    },
    "silence_of_the_mouse": {
        "name": "Silence of the Mouse",
        "summary": "For the next hour or 6 rooms, switch Stealth skill/modifier between two characters and ignore negative Stealth modifiers from the adventure setting.",
        "status": "TAG Silence of the Mouse: 6 rooms ignore setting Stealth penalties",
    },
    "wizards_luck": {
        "name": "Wizard's Luck",
        "summary": "For Gambling House cheating: choose a table result and roll d6+Level against it; failure rolls the table at -2, natural 1 means jail/fine.",
        "status": "TAG Wizard's Luck gambling cheat pending",
    },
}

TAG_LOOK_TOUGH_MARKER = "TAG Look Tough next Streetwise bonus"
TAG_WIZARDS_LUCK_MARKER = "TAG Wizard's Luck gambling cheat pending"

TAG_DRAGON_TYPE_FOES: dict[str, dict[str, object]] = {
    "small_dragon": {
        "name": "Small Dragon",
        "description": "Small Dragon revealed by TAG Dragon's Lair type table.",
        "foes": [{"name": "Young Dragon", "count": 1}],
    },
    "young_red_dragon": {
        "name": "Young Red Dragon",
        "description": "Young Red Dragon revealed by TAG Dragon's Lair type table. Use the printed fire-breath and reaction profile.",
        "foes": [{"name": "Young Dragon", "count": 1}],
    },
    "darkness_or_ghoul_dragon": {
        "name": "Darkness Dragon or Ghoul Dragon",
        "description": "Dragon's Lair type roll 6: roll the printed follow-up d6 for Darkness Dragon or Ghoul Dragon before combat.",
        "foes": [{"name": "Young Dragon", "count": 1}],
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
        "finale_mode": "choice",
        "finale_instruction": "Choose the Scene 9 resolution that actually applies: leave the object alone, question Bofto's family, steal it, or trigger the cursed-object follow-up.",
        "rewards": "Depends on the chosen Scene 9 resolution.",
        "final_prompt_actions": [
            {
                "label": "Record Bofto choice",
                "tooltip": "Prefill the Scene 9 choice: steal the object, talk to the family, or leave.",
                "action_type": "branch",
                "action_value": "bofto_scene_choice",
                "reference": "Bofto Scene 9 choice",
            },
            {
                "label": "Steal star object",
                "tooltip": "Prefill Scene 14 thievery Save vs L6 for stealing the star-shaped object.",
                "action_type": "branch",
                "action_value": "bofto_theft_save",
                "reference": "Scene 14 star-object theft",
            },
            {
                "label": "Star Will save",
                "tooltip": "Prefill Scene 19 Will Save vs L8 after taking the star-shaped object.",
                "action_type": "branch",
                "action_value": "star_object_will_save",
                "reference": "Scene 19 star-shaped object Will Save",
            },
            {
                "label": "Star-Slayer check",
                "tooltip": "Prefill the cursed object's 2-in-6 Boss/Weird replacement check.",
                "action_type": "branch",
                "action_value": "star_slayer_check",
                "reference": "Scene 19 Star-Slayer replacement check",
            }
        ],
        "rules": [
            "Rumor is crossed off once played.",
            "This is primarily a choice scene; do not install a proxy fight unless a later table result actually turns hostile.",
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
        "complication_prompt_actions": [
            {
                "label": "Resolve assassin approach",
                "tooltip": "Prefill Scene 10 assassin approach; set Amount 1 if any L6 Stealth Save failed.",
                "action_type": "branch",
                "action_value": "medusa_assassin_ambush",
                "reference": "Scene 10 assassin approach",
            }
        ],
        "final_prompt_actions": [
            {
                "label": "Medusa stealth approach",
                "tooltip": "Prefill the L6 Stealth roll to surprise Xasartha before her gaze.",
                "action_type": "branch",
                "action_value": "medusa_stealth_approach",
                "reference": "Scene 1 medusa stealth approach",
            },
            {
                "label": "Medusa reaction",
                "tooltip": "Prefill Xasartha's reaction roll if the party shouts from outside.",
                "action_type": "branch",
                "action_value": "medusa_reaction",
                "reference": "Scene 1 Xasartha reaction",
            },
            {
                "label": "Medusa pendant",
                "tooltip": "Prefill the Medusa pendant reward action after the pendant is taken.",
                "action_type": "scene",
                "action_value": "medusa_pendant",
                "reference": "Scene 1 Medusa pendant",
            },
        ],
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
        "finale_mode": "procedure",
        "finale_instruction": "This is a red herring. Use the ambush button if the optional 2-in-6 ambush is being checked; otherwise record the false trail and return to settlement play.",
        "rewards": "No sword; possible ambush rewards only.",
        "final_prompt_actions": [
            {
                "label": "Roll red-herring ambush",
                "tooltip": "Prefill Scene 11's 2-in-6 Riff-Raff or Outside of Town ambush chance.",
                "action_type": "branch",
                "action_value": "tag_ambush_chance",
                "reference": "Scene 11 Riff-Raff or Outside of Town Ambush Table",
                "amount": 2,
            }
        ],
        "rules": ["The ambush is optional procedure text; no proxy combat is installed unless the table result produces one."],
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
        "final_prompt_actions": [
            {
                "label": "Fish hypnosis save",
                "tooltip": "Prefill one L5 mutant fish hypnosis Save; repeat for each character as needed.",
                "action_type": "branch",
                "action_value": "mutant_fish_hypnosis",
                "reference": "Scene 12 mutant fish hypnosis",
            },
            {
                "label": "Fish rations",
                "tooltip": "Prefill the d6+3 mutant fish food-ration reward.",
                "action_type": "scene",
                "action_value": "mutant_fish_rations",
                "reference": "Scene 12 fish rations",
            },
            {
                "label": "Mark two minion XP",
                "tooltip": "Prefill the printed two-minion-encounter XP marker.",
                "action_type": "xp",
                "action_value": "mark_minor_encounters",
                "reference": "Scene 12 counts as two minion encounters",
                "amount": 2,
            },
        ],
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
        "clue_gate_cost": 2,
        "clue_gate_label": "Spend 2 Clues for the dragon route",
        "complication_prompt_actions": [
            {
                "label": "Reveal dragon type",
                "tooltip": "Prefill the Dragon's Lair type reveal after the 2-Clue spend.",
                "action_type": "scene",
                "action_value": "dragon_type_reveal",
                "reference": "Scene 13 dragon type reveal",
                "amount": 2,
            }
        ],
        "rules": ["Use the Dragon's Lair thematic notes in source.parameters for the full lair version."],
    },
    6: {
        "title": "Leprechauns at Blackbird Hill",
        "scene": "Scene 2",
        "pdf_pages": "TAG pp.23, 25",
        "objective": "Find the leprechauns and decide whether to buy Shoes of Fast Walk or learn their illusion spell.",
        "entry": "Blackbird Hill is dotted with tiny tracks and mocking laughter.",
        "side": "The leprechauns prefer bargaining to fighting.",
        "complication": "Tiny footprints loop around the stones in impossible circles. A laugh skips from one side of the hill to the other, always just behind the party. Bright scraps of green cloth hang from thorn branches like deliberate bait, and somewhere ahead coins clink in a pouch no honest traveller is carrying.",
        "complication_guidance": "No purchase or spell choice is due in this room; continue to the bargain scene when ready.",
        "final_title": "Blackbird Hill Bargain",
        "final_description": "The leprechaun rumor is real. Under the old oak at Blackbird Hill, the little folk are ready to bargain: shoes for gold, or one illusion lesson for a magically inclined hero.",
        "finale_mode": "vendor",
        "finale_instruction": "Choose who buys magical shoes, whether the party bought enough pairs to make spell teaching free, and which single eligible character learns one illusion spell.",
        "rewards": "Buy Shoes of Fast Walk for 200 gp per pair, up to one pair per character. One eligible character may learn one illusion spell for 100 gp, or free if at least three pairs of shoes were bought.",
        "final_prompt_actions": [
            {
                "label": "Buy Shoes of Fast Walk",
                "tooltip": "Buy up to one pair per character for 200 gp each. Only characters who can use magic items, and hirelings, may use them; animal companions may not.",
                "action_type": "branch",
                "action_value": "leprechaun_shoes",
                "reference": "Scene 2 Shoes of Fast Walk",
                "amount": 1,
            },
            {
                "label": "Learn illusion spell",
                "tooltip": "One eligible character learns one illusion spell automatically for 100 gp, or free if the party bought at least three pairs of magical shoes.",
                "action_type": "branch",
                "action_value": "leprechaun_illusion_spell",
                "reference": "Scene 2 illusion spell - choose spell",
                "amount": 100,
            },
        ],
        "rules": ["Scene 2 is a bargain/vendor scene; no proxy combat is required unless the table deliberately turns the encounter hostile."],
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
        "module_profile": {
            "target_rooms": "seven-room temple dungeon",
            "procedure": [
                "Scene 15 is a dungeon handoff, not a single room.",
                "Use the generated module as a compact play aid or expand it to seven rooms if playing the PDF literally.",
            ],
            "signoff_checks": [
                "Confirm whether your table used 4AD or Lost Temples support rules.",
                "Record any temple-specific treasure or finale changes manually.",
            ],
        },
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
        "clue_gate_cost": 2,
        "clue_gate_label": "Spend 2 Clues to find Shaura",
        "module_profile": {
            "target_rooms": "10-room dungeon",
            "procedure": [
                "Spend 2 Clues before the cult location is opened.",
                "Use the generated module as the ten-room cult dungeon handoff.",
                "Final encounter is Silent Scream Priestess plus nine cultists.",
            ],
            "signoff_checks": [
                "Confirm the 2-Clue gate is paid before opening the finale route.",
                "After victory, apply the 150 gp reward and pending XP handling.",
            ],
        },
        "final_prompt_actions": [
            {
                "label": "Apply Shaura reward",
                "tooltip": "Prefill the printed Shaura cult reward action.",
                "action_type": "scene",
                "action_value": "shaura_reward",
                "reference": "Shaura cult reward",
                "amount": 150,
            }
        ],
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
        "final_description": "The familiar is found after the party pays the required Clue cost or qualifies for the reduced cat/beast route.",
        "finale_mode": "procedure",
        "finale_instruction": "Confirm the Clue spend or reduced-Clue exception, then apply Daroc's reward. No fight is required by this scene unless your table adds one.",
        "rewards": "100 gp and 1 XP.",
        "clue_gate_cost": 2,
        "clue_gate_label": "Spend town Clues for Daroc's familiar",
        "final_prompt_actions": [
            {
                "label": "Apply Daroc reward",
                "tooltip": "Prefill Daroc's cat reward and pending XP marker.",
                "action_type": "scene",
                "action_value": "daroc_cat",
                "reference": "Scene 5 Daroc cat reward",
                "amount": 100,
            }
        ],
        "rules": ["This is a Clue-and-reward procedure; no mandatory proxy combat is installed."],
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
        "complication_prompt_actions": [
            {
                "label": "Roll gargoyle count",
                "tooltip": "Prefill Scene 8 d6+2 white gargoyle count.",
                "action_type": "branch",
                "action_value": "gargoyle_count",
                "reference": "Scene 8 gargoyle count",
            },
            {
                "label": "Roll gargoyle surprise",
                "tooltip": "Prefill the 3-in-6 white gargoyle camouflage surprise chance.",
                "action_type": "branch",
                "action_value": "gargoyle_surprise",
                "reference": "Scene 8 gargoyle surprise",
            },
        ],
        "final_prompt_actions": [
            {
                "label": "Stone skin check",
                "tooltip": "Prefill the 2-in-6 mundane-weapon bounce check.",
                "action_type": "branch",
                "action_value": "gargoyle_skin",
                "reference": "Scene 8 gargoyle stone skin",
            },
            {
                "label": "Gargoyle bounty",
                "tooltip": "Prefill the 15 gp per gargoyle head reward; Amount is head count.",
                "action_type": "scene",
                "action_value": "gargoyle_bounty",
                "reference": "Scene 8 gargoyle bounty",
            },
        ],
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
        "finale_mode": "service",
        "finale_instruction": "Choose the trainee, calculate the 60 gp x level payment, then mark the one qualifying archery XP roll.",
        "rewards": "One qualifying XP roll for the listed archery benefits.",
        "final_prompt_actions": [
            {
                "label": "Pay Deoldyn training",
                "tooltip": "Prefill Deoldyn's 60 gp x level training payment and XP-roll marker.",
                "action_type": "scene",
                "action_value": "deoldyn_training",
                "reference": "Scene 3 Deoldyn training",
            },
            {
                "label": "Mark training XP roll",
                "tooltip": "Prefill the training XP-roll marker if payment was handled separately.",
                "action_type": "xp",
                "action_value": "mark_training_xp_roll",
                "reference": "Scene 3 archery training XP roll",
            },
        ],
        "rules": ["This is a paid training service; no proxy interruption fight is installed."],
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
        "complication_prompt_actions": [
            {
                "label": "Record solo quest",
                "tooltip": "Prefill the printed solo restriction for Scene 7.",
                "action_type": "route",
                "action_value": "solo_restriction",
                "reference": "Scene 7 Agaratha solo quest",
            }
        ],
        "final_prompt_actions": [
            {
                "label": "Apply Agaratha",
                "tooltip": "Prefill Agaratha reward and Luck-on-major-kill marker.",
                "action_type": "scene",
                "action_value": "agaratha",
                "reference": "Scene 7 Agaratha reward",
            }
        ],
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
        "module_profile": {
            "target_rooms": "9-room dungeon",
            "procedure": [
                "Use standard vermin, but replace minions with Ghastly Mine undead on 4-in-6.",
                "Boss or Weird results have a 4-in-6 chance to become a Ghastly Mine major undead.",
                "All traps are cave-ins; after more than three cave-ins, later cave-ins are harsher and the mine collapses after exit.",
            ],
            "signoff_checks": [
                "For gp treasure, check the 3-in-6 gem/nugget conversion.",
                "Track the number of cave-ins and any fallen/paralyzed/petrified characters left behind.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Mine minions",
                "tooltip": "Roll the Ghastly Mine 4-in-6 minion replacement check, then the undead minion table if it replaces the normal result.",
                "action_type": "branch",
                "action_value": "ghastly_mine_minion_replacement",
                "reference": "Ghastly Mine minion replacement",
                "amount": 0,
            },
            {
                "label": "Mine major foe",
                "tooltip": "Roll the Ghastly Mine 4-in-6 Boss/Weird replacement check, then the major undead table if it replaces the normal result.",
                "action_type": "branch",
                "action_value": "ghastly_mine_major_replacement",
                "reference": "Ghastly Mine major-foe replacement",
                "amount": 0,
            },
            {
                "label": "Mine cave-in",
                "tooltip": "Log a Ghastly Mine cave-in trap. Put prior cave-ins in Amount so the app notes when later cave-ins become L6/2 damage.",
                "action_type": "branch",
                "action_value": "ghastly_mine_cave_in",
                "reference": "Ghastly Mine cave-in trap",
                "amount": 0,
            },
            {
                "label": "Mine treasure",
                "tooltip": "Roll the Ghastly Mine 3-in-6 check that gp treasure becomes one gem or nugget of the same value.",
                "action_type": "branch",
                "action_value": "ghastly_mine_treasure_conversion",
                "reference": "Ghastly Mine gp treasure conversion",
                "amount": 0,
            },
        ],
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
        "module_profile": {
            "target_rooms": "HCL+5 rooms",
            "procedure": [
                "Do not use the normal Final Boss check; the final room is automatically the hill giant room.",
                "Final room must be at least nine squares and not a corridor.",
                "The giant has a 4-in-6 boulder throw chance on its first turn; spells hit it at +2.",
            ],
            "signoff_checks": [
                "Dead-end unvisited doors/openings when the final room is drawn.",
                "Roll three treasure rolls and double all gp treasure.",
            ],
        },
        "final_prompt_actions": [
            {
                "label": "Giant boulder",
                "tooltip": "Prefill the Giant's Lair 4-in-6 first-turn hill giant boulder throw.",
                "action_type": "branch",
                "action_value": "giant_lair_boulder",
                "reference": "Giant's Lair boulder throw",
            },
            {
                "label": "Giant treasure",
                "tooltip": "Prefill the Giant's Lair final-room treasure and size reminder.",
                "action_type": "branch",
                "action_value": "giant_lair_treasure",
                "reference": "Giant's Lair final treasure",
            },
        ],
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
        "clue_gate_cost": 2,
        "clue_gate_label": "Spend 2 Clues to reveal dragon type",
        "module_profile": {
            "target_rooms": "4-room dungeon",
            "procedure": [
                "Complete exactly four rooms for this compact lair.",
                "Before the final room, the party may spend 2 Clues to reveal the dragon type.",
                "Final encounter uses the selected TAG dragon profile; Young Dragon remains the safe generated proxy until a type is chosen.",
            ],
            "signoff_checks": [
                "Check whether the party spent 2 Clues before revealing the final room.",
                "Record the dragon type reveal result before resolving the hoard.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Reveal dragon type",
                "tooltip": "Prefill the Dragon's Lair type reveal scene action; it spends 2 Clues and rolls the TAG dragon type.",
                "action_type": "scene",
                "action_value": "dragon_type_reveal",
                "reference": "Dragon's Lair type reveal",
                "amount": 2,
            }
        ],
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
        "clue_gate_cost": 2,
        "clue_gate_label": "Spend 2 Clues to learn the final boss",
        "module_profile": {
            "target_rooms": "HCL+5 rooms",
            "procedure": [
                "Use Fiendish Foes or Abyss content; otherwise raise danger levels by 2 and minor counts by 2.",
                "Spend 2 Clues if desired to reveal the Final Boss nature before the last room.",
                "Final Boss is a Weird Monsters Around Town boss raised by +1 level, with a prisoner in the lair.",
            ],
            "signoff_checks": [
                "Roll the Prisoner Table after the final boss is defeated.",
                "If the prisoner gives a map, create/follow the resulting treasure-map or thematic-dungeon lead.",
            ],
        },
        "final_prompt_actions": [
            {
                "label": "Prisoner table",
                "tooltip": "Roll the Fiendish Abyss Prisoner Table after defeating the final boss.",
                "action_type": "branch",
                "action_value": "fiendish_abyss_prisoner",
                "reference": "Fiendish Abyss Prisoner Table",
                "amount": 0,
            }
        ],
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
        "module_profile": {
            "target_rooms": "d6+5 rooms",
            "procedure": [
                "All minions are young minotaurs; all major foes are adult minotaurs.",
                "Backtracking has a 3-in-6 lost chance, reduced to 2-in-6 with a dungeon guide.",
                "Successful searching in an empty room/corridor can create a shortcut to the minotaur lord chamber.",
            ],
            "signoff_checks": [
                "Halflings cannot use Luck against minotaurs.",
                "Apply the first-attack charge/Defense penalty and special Minotaur Maze event table.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Maze lost",
                "tooltip": "Roll the Minotaur Maze backtracking lost check. Set Amount to 1 if a dungeon guide is present.",
                "action_type": "branch",
                "action_value": "minotaur_maze_lost_check",
                "reference": "Minotaur Maze backtracking lost check",
                "amount": 0,
            },
            {
                "label": "Maze wandering",
                "tooltip": "Roll the Minotaur Maze wandering monster subtype table.",
                "action_type": "branch",
                "action_value": "minotaur_maze_wandering",
                "reference": "Minotaur Maze wandering monster",
                "amount": 0,
            },
            {
                "label": "Maze event",
                "tooltip": "Roll the Minotaur Maze Special Event Table for a Special Event room result.",
                "action_type": "branch",
                "action_value": "minotaur_maze_event",
                "reference": "Minotaur Maze Special Event Table",
                "amount": 0,
            },
            {
                "label": "Open shortcut",
                "tooltip": "Prefill the route marker for a successful empty-room/corridor search that opens a shortcut to the minotaur lord chamber.",
                "action_type": "route",
                "action_value": "unlock_scene",
                "reference": "Minotaur Maze shortcut to lord chamber",
                "amount": 0,
            },
        ],
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
        "module_profile": {
            "target_rooms": "HCL+3 rooms",
            "procedure": [
                "Each room has a 1-in-6 stolen-goods chance in the printed theme.",
                "Rooms may include trapdoors; record any trapdoor result as a route/signoff note.",
                "Final encounter is Bandit Chieftain plus bandit guards.",
            ],
            "signoff_checks": [
                "Check stolen-goods chance room by room while playing the hideout.",
                "Decide whether the chieftain is killed or captured alive before applying reward.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Roll stolen goods",
                "tooltip": "Roll the Bandit Hideout stolen-goods room check: 1-in-6 goods, then 8d6 gp and trapdoor chance if found.",
                "action_type": "branch",
                "action_value": "bandit_stolen_goods_check",
                "reference": "Bandit Hideout stolen-goods room check",
                "amount": 0,
            }
        ],
        "final_prompt_actions": [
            {
                "label": "Capture chieftain alive",
                "tooltip": "Prefill the printed capture-alive branch for the Bandit Chieftain reward path.",
                "action_type": "branch",
                "action_value": "capture_alive",
                "reference": "Bandit Chieftain captured alive",
                "amount": 0,
            },
            {
                "label": "Bandit capture reward",
                "tooltip": "Prefill the Bandit Chieftain capture scene reward.",
                "action_type": "scene",
                "action_value": "bandit_chieftain_capture",
                "reference": "Bandit Chieftain capture reward",
                "amount": 0,
            },
        ],
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
        "clue_gate_cost": 1,
        "clue_gate_label": "Spend 1 Clue for portrait cache",
        "module_profile": {
            "target_rooms": "exactly 10 rooms",
            "procedure": [
                "Complete the cleanup in one session; leaving and re-entering forfeits the job pay.",
                "Track slain minions, vermin, Bosses, and Weird Monsters for payment.",
                "Spend 1 Clue to find the hidden ancestral portrait cache.",
            ],
            "signoff_checks": [
                "Base pay is 25 gp per character plus foe-count payments.",
                "Portrait cache adds 100 gp if found with the Clue spend.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Find portrait cache",
                "tooltip": "Prefill the 1-Clue hidden portrait cache route for Clean Up My Castle.",
                "action_type": "route",
                "action_value": "clue_gate_unlocked",
                "reference": "Clean Up My Castle portrait cache",
                "amount": 1,
            }
        ],
        "final_prompt_actions": [
            {
                "label": "Tally cleanup pay",
                "tooltip": "Calculate Clean Up My Castle job pay. Put slain minion/vermin count in Amount and Boss/Weird count in Reference as boss=number.",
                "action_type": "branch",
                "action_value": "castle_cleanup_pay",
                "reference": "Clean Up My Castle boss=0",
                "amount": 0,
            }
        ],
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
        "module_profile": {
            "target_rooms": "single guild-job encounter",
            "procedure": [
                "Printed encounter is Gorungar plus 2d6 goblin archers.",
                "Generated module uses eight archers as the fixed proxy; roll 2d6 manually if exact count is required.",
                "Archers use poison arrows and the printed surprise/morale notes.",
            ],
            "signoff_checks": [
                "Confirm whether Gorungar was killed or captured alive.",
                "Roll or record the coin bag and armband reward after victory.",
            ],
        },
        "final_prompt_actions": [
            {
                "label": "Claim head bounty",
                "tooltip": "Prefill the Gorungar head bounty scene reward.",
                "action_type": "scene",
                "action_value": "gorungar_head",
                "reference": "Gorungar head bounty",
                "amount": 0,
            },
            {
                "label": "Claim alive bounty",
                "tooltip": "Prefill the Gorungar alive bounty scene reward.",
                "action_type": "scene",
                "action_value": "gorungar_alive",
                "reference": "Gorungar alive bounty",
                "amount": 0,
            },
        ],
        "rules": ["Final encounter includes Gorungar and goblin archers; roll 2d6 archers manually if you want the exact count."],
    },
    3: {
        "title": "Griffin Omelets, Anyone?",
        "pdf_pages": "TAG p.56",
        "objective": "Recover griffin eggs for the guild patron.",
        "entry": "Claw marks and feathers lead to a high nesting site.",
        "side": "Roll five ascent encounter checks, then search repeatedly until the nest is found.",
        "complication": "A search roll of 1 risks griffin attack unless the worst-Stealth character passes L7.",
        "final_title": "Griffin Nest",
        "final_description": "The black-feathered griffins defend d3+1 eggs. Fleeing requires teleportation such as Escape.",
        "final_foe": "Griffin",
        "final_count": 1,
        "rewards": "70 gp per intact egg delivered; broken eggs are worth 2d6 gp.",
        "module_profile": {
            "target_rooms": "mountain approach and nest",
            "procedure": [
                "Roll five wandering-monster checks on the way up and five on the way down.",
                "Search until a 6 finds the nest; each search roll of 1 risks two griffins unless L7 Stealth succeeds.",
                "Nest contains d3+1 eggs; most characters carry two eggs, elves carry three, ogres carry none.",
            ],
            "signoff_checks": [
                "If an egg carrier dies, each carried egg has a 2-in-6 break chance.",
                "Pay 70 gp per intact egg; broken eggs pay 2d6 gp each.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Mountain check",
                "tooltip": "Roll one Griffin Omelets ascent/descent wandering-monster check. Set Amount to 1 for the reduced 1-in-6 chance.",
                "action_type": "branch",
                "action_value": "griffin_mountain_check",
                "reference": "Griffin Omelets mountain check",
                "amount": 0,
            },
            {
                "label": "Search nest",
                "tooltip": "Roll one Griffin Omelets nest-search check; 6 finds nest, 1 risks griffin attack unless L7 Stealth succeeds.",
                "action_type": "branch",
                "action_value": "griffin_nest_search",
                "reference": "Griffin Omelets nest search",
                "amount": 0,
            },
        ],
        "final_prompt_actions": [
            {
                "label": "Roll eggs",
                "tooltip": "Roll d3+1 black-feathered griffin eggs in the nest.",
                "action_type": "branch",
                "action_value": "griffin_egg_count",
                "reference": "Griffin Omelets egg count",
                "amount": 0,
            },
            {
                "label": "Egg break",
                "tooltip": "Roll break checks for carried griffin eggs after an egg carrier dies. Put carried egg count in Amount.",
                "action_type": "branch",
                "action_value": "griffin_egg_break",
                "reference": "Griffin Omelets egg break check",
                "amount": 1,
            },
        ],
        "rules": ["Griffin is a TAG-specific foe profile; resolve egg carrying and mountain checks from the printed quest."],
    },
    4: {
        "title": "A Portrait in Red",
        "pdf_pages": "TAG p.57",
        "objective": "Resolve the guild's bloody portrait commission.",
        "entry": "The party escorts a famous artist to a remote hermitage through monster-infested wilderness.",
        "side": "The nobleman must be persuaded with repeated L6 persuasion Saves and party composition modifiers.",
        "complication": "On the return journey, a surprised painting snatcher must be stopped within one turn or the portrait is lost.",
        "final_title": "Red Gallery",
        "final_description": "The painted commission must survive the return trip for the party to be paid.",
        "finale_mode": "procedure",
        "finale_instruction": "Track the outbound checks, persuasion, return checks, and painting-snatch risk. If the artist and portrait survive the route, apply the commission pay.",
        "rewards": "200 gp to each surviving party member if the artist and portrait return.",
        "module_profile": {
            "target_rooms": "outbound and return wilderness escort",
            "procedure": [
                "Roll six outbound wilderness encounter checks before the hermitage.",
                "Persuade the nobleman with repeated L6 persuasion Saves; natural 1 ejects a chosen character.",
                "Roll five return checks; if surprised, check whether a foe snatches the painting.",
            ],
            "signoff_checks": [
                "Track ejected characters and any 20 gp monk donation required to continue.",
                "If the painting is snatched, the party has one turn to stop the thief without Fireball or Lightning.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Outbound check",
                "tooltip": "Roll one A Portrait in Red outbound wilderness check. Put 1-6 in Amount for leg number; 5-6 use Weird Monster rules.",
                "action_type": "branch",
                "action_value": "portrait_outbound_check",
                "reference": "A Portrait in Red outbound check",
                "amount": 1,
            },
            {
                "label": "Persuade noble",
                "tooltip": "Roll the L6 persuasion attempt. Put positive modifier in Amount or write mod=-1 in Reference for penalties; natural 1 ejects a chosen character.",
                "action_type": "branch",
                "action_value": "portrait_persuasion",
                "reference": "A Portrait in Red persuasion",
                "amount": 0,
            },
            {
                "label": "Painting snatch",
                "tooltip": "Roll the 1-in-6 painting snatch check after a surprised return encounter.",
                "action_type": "branch",
                "action_value": "portrait_return_snatch",
                "reference": "A Portrait in Red painting snatch",
                "amount": 0,
            },
        ],
        "rules": ["The printed mission is primarily escort, persuasion, and painting-loss handling; no proxy final horror is installed."],
    },
    5: {
        "title": "Sewers Search",
        "pdf_pages": "TAG p.58",
        "objective": "Search the settlement sewers for the guild target.",
        "entry": "The trail drops below the street grates.",
        "side": "Ignore non-encounter/non-trap room content and treat special features as empty rooms.",
        "complication": "All empty rooms may be searched for Clues; 3 Clues reveal the thief in the next room.",
        "final_title": "Sewer Sump",
        "final_description": "The thief with the silk rolls is the Final Boss; capture alive for interrogation bonus.",
        "final_foe": "Sewer Thief",
        "final_count": 1,
        "rewards": "50 gp per character for the silk rolls, plus 100 gp if the thief is brought back alive.",
        "clue_gate_cost": 3,
        "clue_gate_label": "Spend 3 Clues to find the thief",
        "module_profile": {
            "target_rooms": "small sewer dungeon",
            "procedure": [
                "Use sewer vermin/minion tables for vermin and minion encounters.",
                "Bosses are HCL+2 thieves; Weird Monsters are two-headed huge rats.",
                "Wounded heroes below half Life must check for disease after the adventure.",
            ],
            "signoff_checks": [
                "Spend 3 Clues to place the thief with the silk rolls in the next room.",
                "Apply 50 gp per character and 100 gp alive-capture bonus if achieved.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Sewer vermin",
                "tooltip": "Roll the Sewers Search Vermin Table for a vermin encounter.",
                "action_type": "branch",
                "action_value": "sewers_vermin",
                "reference": "Sewers Search vermin",
                "amount": 0,
            },
            {
                "label": "Sewer minions",
                "tooltip": "Roll the Sewers Search Minions Table for a minion encounter.",
                "action_type": "branch",
                "action_value": "sewers_minions",
                "reference": "Sewers Search minions",
                "amount": 0,
            },
            {
                "label": "Find thief with Clues",
                "tooltip": "Prefill the 3-Clue route that finds the sewer thief in the next room.",
                "action_type": "route",
                "action_value": "clue_gate_unlocked",
                "reference": "Sewers Search thief found",
                "amount": 3,
            },
            {
                "label": "Disease save",
                "tooltip": "Roll the post-adventure Sewers Search disease check for a hero wounded below half Life.",
                "action_type": "branch",
                "action_value": "sewers_disease",
                "reference": "Sewers Search post-adventure disease",
                "amount": 0,
            },
        ],
        "final_prompt_actions": [
            {
                "label": "Capture thief alive",
                "tooltip": "Prefill a capture-alive marker for the sewer thief bonus.",
                "action_type": "branch",
                "action_value": "capture_alive",
                "reference": "Sewers Search thief captured alive",
                "amount": 0,
            }
        ],
        "rules": ["The thief with the silk rolls is the final boss; sewer vermin and minion tables are handled as room procedures before the finale."],
    },
    6: {
        "title": "Monoceros Hunt",
        "pdf_pages": "TAG p.59",
        "objective": "Track and resolve the monoceros hunt.",
        "entry": "The quarry's tracks leave deep, single-horn gouges.",
        "side": "Each hunter rolls a Tier die plus level modifiers to locate the monoceros.",
        "complication": "A roll of 1 causes a hunting accident save; 6+ finds the monoceros. Three Clues can skip the hunt after a possible Weird Monster encounter.",
        "final_title": "Monoceros Glade",
        "final_description": "The hunt catches up with the monoceros in a secluded glade.",
        "final_foe": "Monoceros",
        "final_count": 1,
        "rewards": "200 gp to the party if the monoceros is captured alive.",
        "clue_gate_cost": 3,
        "clue_gate_label": "Spend 3 Clues to find the monoceros",
        "module_profile": {
            "target_rooms": "wilderness hunt and capture encounter",
            "procedure": [
                "Roll one tracking die per character; successes find the monoceros, failures join after three turns.",
                "Rolls of 1 cause hunting-accident Saves and remove that character from the hunt.",
                "Capture requires Sleep or melee subdual at -1; Fireball and Lightning are forbidden.",
            ],
            "signoff_checks": [
                "If 3 Clues are spent, roll the 2-in-6 Weird Monster Around Town encounter chance first.",
                "Non-magical hits may be turned by the monoceros hide on d6 5-6.",
            ],
        },
        "complication_prompt_actions": [
            {
                "label": "Track hunt",
                "tooltip": "Roll one Monoceros Hunt tracker result. Put positive modifier in Amount or write mod=-1 in Reference for penalties.",
                "action_type": "branch",
                "action_value": "monoceros_tracking",
                "reference": "Monoceros Hunt tracking",
                "amount": 0,
            },
            {
                "label": "Find with 3 Clues",
                "tooltip": "Prefill the 3-Clue shortcut to locate the monoceros before the capture encounter.",
                "action_type": "route",
                "action_value": "clue_gate_unlocked",
                "reference": "Monoceros Hunt clue shortcut",
                "amount": 3,
            },
            {
                "label": "Clue encounter",
                "tooltip": "Roll the 2-in-6 Weird Monster Around Town encounter chance before using the 3-Clue shortcut.",
                "action_type": "branch",
                "action_value": "monoceros_clue_encounter",
                "reference": "Monoceros Hunt clue shortcut encounter",
                "amount": 0,
            },
        ],
        "final_prompt_actions": [
            {
                "label": "Capture monoceros alive",
                "tooltip": "Prefill a capture-alive marker for the Monoceros Hunt reward.",
                "action_type": "branch",
                "action_value": "capture_alive",
                "reference": "Monoceros captured alive",
                "amount": 0,
            },
            {
                "label": "Hide turns blow",
                "tooltip": "Roll the monoceros thick-hide check after a non-magical hit.",
                "action_type": "branch",
                "action_value": "monoceros_hide",
                "reference": "Monoceros hide check",
                "amount": 0,
            }
        ],
        "rules": ["Monoceros is a generated foe profile; resolve pursuit, hide turns, and capture reward from the printed quest."],
    },
}


def default_campaign() -> CampaignState:
    timestamp = now_utc()
    return CampaignState(
        id=DEFAULT_CAMPAIGN_ID,
        active_world_campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
        world_campaigns=[
            WorldCampaignRecord(
                id=DEFAULT_WORLD_CAMPAIGN_ID,
                name=DEFAULT_WORLD_CAMPAIGN_NAME,
                description="Default campaign world for existing characters, parties, troupe, guild, and friendly settlements.",
                guild_id=DEFAULT_WORLD_GUILD_ID,
                is_default=True,
                created_at=timestamp,
            )
        ],
        world_guilds=[
            WorldGuildRecord(
                id=DEFAULT_WORLD_GUILD_ID,
                name=DEFAULT_WORLD_GUILD_NAME,
                campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
                description="Default campaign Adventurers Guild.",
                created_at=timestamp,
            )
        ],
        world_troupes=[
            WorldTroupeRecord(
                id=DEFAULT_WORLD_TROUPE_ID,
                name=DEFAULT_WORLD_TROUPE_NAME,
                campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
                guild_id=DEFAULT_WORLD_GUILD_ID,
                home_settlement_id=DEFAULT_WORLD_SETTLEMENT_ID,
                description="Default troupe for existing roster characters and saved parties.",
                created_at=timestamp,
            )
        ],
        world_settlements=[
            WorldSettlementRecord(
                id=DEFAULT_WORLD_SETTLEMENT_ID,
                name=DEFAULT_WORLD_SETTLEMENT_NAME,
                campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
                kind="friendly",
                size=0,
                notes="Default friendly home settlement.",
                created_at=timestamp,
            )
        ],
        tag_banking_enabled=False,
        tag_troupe_name=DEFAULT_WORLD_TROUPE_NAME,
        settlement_name=DEFAULT_WORLD_SETTLEMENT_NAME,
        tag_settlements=[
            TagSettlementState(name=DEFAULT_WORLD_SETTLEMENT_NAME, size=0, notes="", created_at=timestamp),
        ],
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
    campaign.campaign_chronicle = campaign.campaign_chronicle[-CAMPAIGN_CHRONICLE_LIMIT:]
    campaign.guidance_tasks = campaign.guidance_tasks[-GUIDANCE_TASK_LIMIT:]
    return campaign


def append_campaign_chronicle(
    campaign: CampaignState,
    *,
    event_type: str,
    title: str,
    body: str = "",
    campaign_id: str | None = None,
    party_id: str | None = None,
    party_name: str | None = None,
    character: Character | None = None,
    guild_id: str | None = None,
    troupe_id: str | None = None,
    settlement_id: str | None = None,
    reference: str = "",
) -> CampaignChronicleEntry:
    entry = CampaignChronicleEntry(
        event_type=event_type[:80],
        title=title[:160],
        body=body[:1200],
        campaign_id=campaign_id or campaign.active_world_campaign_id,
        party_id=party_id,
        party_name=party_name,
        character_id=character.id if character is not None else None,
        character_name=character.name if character is not None else None,
        guild_id=guild_id,
        troupe_id=troupe_id,
        settlement_id=settlement_id,
        reference=reference[:300],
        created_at=now_utc(),
    )
    campaign.campaign_chronicle.append(entry)
    trim_tag_logs(campaign)
    return entry


def add_guidance_task(
    campaign: CampaignState,
    *,
    title: str,
    body: str,
    category: str = "campaign",
    priority: str = "recommended",
    reference: str = "",
    rules_reference_id: str = "",
    affected_entity_type: str = "",
    affected_entity_id: str = "",
    closeout_task_id: str | None = None,
) -> GuidanceTaskState | None:
    if closeout_task_id and any(task.closeout_task_id == closeout_task_id for task in campaign.guidance_tasks):
        return None
    task = GuidanceTaskState(
        title=title[:160],
        body=body[:1200],
        category=category if category in {"closeout", "campaign", "character", "finance", "guild", "settlement", "adventure"} else "campaign",
        priority=priority if priority in {"required", "recommended", "optional"} else "recommended",
        reference=reference[:300],
        rules_reference_id=rules_reference_id[:120],
        affected_entity_type=affected_entity_type[:80],
        affected_entity_id=affected_entity_id[:120],
        closeout_task_id=closeout_task_id,
        created_at=now_utc(),
    )
    campaign.guidance_tasks.append(task)
    trim_tag_logs(campaign)
    return task


def modern_title_from_action(action: str) -> str:
    return " ".join(part.capitalize() for part in str(action or "campaign_log").replace("-", "_").split("_") if part)


def update_guidance_task(campaign: CampaignState, *, task_id: str, status: str, note: str = "") -> TagDowntimeLogEntry:
    task = next((item for item in campaign.guidance_tasks if item.id == task_id), None)
    if task is None:
        return append_tag_log(campaign, action="guidance_task", result_text=f"No guidance task matched {task_id}.")
    if status not in {"open", "completed", "deferred", "dismissed"}:
        status = "completed"
    task.status = status
    task.resolved_at = None if status == "open" else now_utc()
    suffix = f" Note: {note.strip()}" if note.strip() else ""
    return append_tag_log(campaign, action="guidance_task", result_text=f"Guidance task {status}: {task.title}.{suffix}")


def ensure_worldbuilder_defaults(campaign: CampaignState, store: Store | None = None) -> tuple[CampaignState, bool]:
    timestamp = now_utc()
    changed = False

    if not any(item.id == DEFAULT_WORLD_CAMPAIGN_ID for item in campaign.world_campaigns):
        campaign.world_campaigns.append(
            WorldCampaignRecord(
                id=DEFAULT_WORLD_CAMPAIGN_ID,
                name=DEFAULT_WORLD_CAMPAIGN_NAME,
                description="Default campaign world for existing characters, parties, troupe, guild, and friendly settlements.",
                guild_id=DEFAULT_WORLD_GUILD_ID,
                is_default=True,
                created_at=timestamp,
            )
        )
        changed = True
    if not campaign.active_world_campaign_id:
        campaign.active_world_campaign_id = DEFAULT_WORLD_CAMPAIGN_ID
        changed = True
    for record in campaign.world_campaigns:
        if record.id == DEFAULT_WORLD_CAMPAIGN_ID:
            if record.name != DEFAULT_WORLD_CAMPAIGN_NAME:
                record.name = DEFAULT_WORLD_CAMPAIGN_NAME
                changed = True
            if not record.guild_id:
                record.guild_id = DEFAULT_WORLD_GUILD_ID
                changed = True
            if not record.is_default:
                record.is_default = True
                changed = True

    if not any(item.id == DEFAULT_WORLD_GUILD_ID for item in campaign.world_guilds):
        campaign.world_guilds.append(
            WorldGuildRecord(
                id=DEFAULT_WORLD_GUILD_ID,
                name=DEFAULT_WORLD_GUILD_NAME,
                campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
                description="Default campaign Adventurers Guild.",
                created_at=timestamp,
            )
        )
        changed = True
    for record in campaign.world_guilds:
        if record.id == DEFAULT_WORLD_GUILD_ID:
            if record.name != DEFAULT_WORLD_GUILD_NAME:
                record.name = DEFAULT_WORLD_GUILD_NAME
                changed = True
            if not record.campaign_id:
                record.campaign_id = DEFAULT_WORLD_CAMPAIGN_ID
                changed = True

    if not any(item.id == DEFAULT_WORLD_SETTLEMENT_ID for item in campaign.world_settlements):
        campaign.world_settlements.append(
            WorldSettlementRecord(
                id=DEFAULT_WORLD_SETTLEMENT_ID,
                name=DEFAULT_WORLD_SETTLEMENT_NAME,
                campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
                kind="friendly",
                size=campaign.settlement_size,
                notes=campaign.settlement_notes or "Default friendly home settlement.",
                created_at=timestamp,
            )
        )
        changed = True
    for record in campaign.world_settlements:
        if record.id == DEFAULT_WORLD_SETTLEMENT_ID:
            if record.name != DEFAULT_WORLD_SETTLEMENT_NAME:
                record.name = DEFAULT_WORLD_SETTLEMENT_NAME
                changed = True
            if not record.campaign_id:
                record.campaign_id = DEFAULT_WORLD_CAMPAIGN_ID
                changed = True

    if not any(item.id == DEFAULT_WORLD_TROUPE_ID for item in campaign.world_troupes):
        campaign.world_troupes.append(
            WorldTroupeRecord(
                id=DEFAULT_WORLD_TROUPE_ID,
                name=DEFAULT_WORLD_TROUPE_NAME,
                campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
                guild_id=DEFAULT_WORLD_GUILD_ID,
                home_settlement_id=DEFAULT_WORLD_SETTLEMENT_ID,
                description="Default troupe for existing roster characters and saved parties.",
                created_at=timestamp,
            )
        )
        changed = True
    for record in campaign.world_troupes:
        if record.id == DEFAULT_WORLD_TROUPE_ID:
            if record.name != DEFAULT_WORLD_TROUPE_NAME:
                record.name = DEFAULT_WORLD_TROUPE_NAME
                changed = True
            defaults = {
                "campaign_id": DEFAULT_WORLD_CAMPAIGN_ID,
                "guild_id": DEFAULT_WORLD_GUILD_ID,
                "home_settlement_id": DEFAULT_WORLD_SETTLEMENT_ID,
            }
            for field, value in defaults.items():
                if not getattr(record, field):
                    setattr(record, field, value)
                    changed = True

    if campaign.settlement_name in {"", "Home Settlement"}:
        campaign.settlement_name = DEFAULT_WORLD_SETTLEMENT_NAME
        changed = True
    if campaign.tag_troupe_name in {"", "Adventuring Troupe"}:
        campaign.tag_troupe_name = DEFAULT_WORLD_TROUPE_NAME
        changed = True
    if not any(item.name.lower() == DEFAULT_WORLD_SETTLEMENT_NAME.lower() for item in campaign.tag_settlements):
        campaign.tag_settlements.append(
            TagSettlementState(name=DEFAULT_WORLD_SETTLEMENT_NAME, size=campaign.settlement_size, notes=campaign.settlement_notes, created_at=timestamp)
        )
        changed = True
    for tag_settlement in campaign.tag_settlements:
        if tag_settlement.name == "Home Settlement":
            tag_settlement.name = DEFAULT_WORLD_SETTLEMENT_NAME
            changed = True
        if not any(row.name.lower() == tag_settlement.name.lower() for row in campaign.world_settlements):
            campaign.world_settlements.append(
                WorldSettlementRecord(
                    name=tag_settlement.name,
                    campaign_id=DEFAULT_WORLD_CAMPAIGN_ID,
                    kind="friendly",
                    size=tag_settlement.size,
                    notes=tag_settlement.notes,
                    created_at=tag_settlement.created_at,
                )
            )
            changed = True

    if store is not None:
        characters = store.list("characters", Character.model_validate)
        parties = store.list("parties", Party.model_validate)
        character_party: dict[str, str] = {}
        for party in parties:
            party_changed = False
            if not party.campaign_id:
                party.campaign_id = DEFAULT_WORLD_CAMPAIGN_ID
                party_changed = True
            if not party.troupe_id:
                party.troupe_id = DEFAULT_WORLD_TROUPE_ID
                party_changed = True
            if party_changed:
                party.updated_at = timestamp
                store.save("parties", party)
                changed = True
            for character_id in party.character_ids:
                character_party.setdefault(character_id, party.id)
        for character in characters:
            character_changed = False
            defaults = {
                "campaign_id": DEFAULT_WORLD_CAMPAIGN_ID,
                "guild_id": DEFAULT_WORLD_GUILD_ID,
                "troupe_id": DEFAULT_WORLD_TROUPE_ID,
            }
            for field, value in defaults.items():
                if not getattr(character, field):
                    setattr(character, field, value)
                    character_changed = True
            party_id = character_party.get(character.id)
            if party_id and character.party_id != party_id:
                character.party_id = party_id
                character_changed = True
            if character_changed:
                character.updated_at = timestamp
                store.save("characters", character)
                changed = True
        default_troupe = next((item for item in campaign.world_troupes if item.id == DEFAULT_WORLD_TROUPE_ID), None)
        if default_troupe is not None:
            member_ids = [character.id for character in characters]
            party_ids = [party.id for party in parties]
            if not default_troupe.member_character_ids:
                default_troupe.member_character_ids = member_ids
                changed = True
            if not default_troupe.party_ids:
                default_troupe.party_ids = party_ids
                changed = True

    return campaign, changed


def tag_guild_benefits_active(campaign: CampaignState) -> bool:
    return bool(campaign.tag_guild_member and campaign.tag_guild_coffers_gp > 0)


def _active_closeout_task_actions(campaign: CampaignState, adventure_number: int) -> set[str]:
    return {
        task.task_action
        for task in campaign.tag_closeout_tasks
        if task.adventure_number == adventure_number and not task.resolved
    }


def _add_closeout_task(
    campaign: CampaignState,
    *,
    adventure_number: int,
    category: str,
    task_action: str,
    title: str,
    result_text: str,
    reference: str = "",
) -> TagCloseoutTaskState | None:
    if task_action in _active_closeout_task_actions(campaign, adventure_number):
        return None
    task = TagCloseoutTaskState(
        adventure_number=adventure_number,
        category=category,
        task_action=task_action,
        title=title,
        result_text=result_text,
        reference=reference,
        created_at=now_utc(),
    )
    campaign.tag_closeout_tasks.append(task)
    priority = "required" if category in {"guild", "xp", "finance"} else "recommended"
    add_guidance_task(
        campaign,
        title=title,
        body=result_text,
        category="closeout",
        priority=priority,
        reference=reference,
        rules_reference_id="adventure_closeout_workflow",
        closeout_task_id=task.id,
        affected_entity_type=category,
    )
    return task


def resolve_tag_closeout_task(
    campaign: CampaignState,
    *,
    task_id: str | None = None,
    task_action: str | None = None,
    note: str = "",
    log_missing: bool = True,
) -> TagDowntimeLogEntry:
    matched = [
        task
        for task in campaign.tag_closeout_tasks
        if not task.resolved
        and ((task_id and task.id == task_id) or (task_action and task.task_action == task_action))
    ]
    if not matched:
        label = task_action or task_id or "closeout task"
        if not log_missing:
            return TagDowntimeLogEntry(
                action="closeout_task",
                result_text=f"No open TAG closeout task matched {label}.",
                created_at=now_utc(),
            )
        return append_tag_log(campaign, action="closeout_task", result_text=f"No open TAG closeout task matched {label}.")
    now = now_utc()
    for task in matched:
        task.resolved = True
        task.resolved_at = now
        if note:
            task.result_text = f"{task.result_text} Resolved note: {note.strip()}"
        for guidance in campaign.guidance_tasks:
            if guidance.closeout_task_id == task.id and guidance.status == "open":
                guidance.status = "completed"
                guidance.resolved_at = now
    title = matched[0].title if len(matched) == 1 else f"{len(matched)} tasks"
    return append_tag_log(campaign, action="closeout_task", result_text=f"TAG closeout task resolved: {title}.")


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
    append_campaign_chronicle(
        campaign,
        event_type=f"tag_{action}"[:80],
        title=modern_title_from_action(action),
        body=result_text,
        character=character,
        reference="TAG campaign log.",
    )
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
        stolen_items = [item for item in campaign.tag_stored_items if item.storage == "trove"]
        campaign.tag_hidden_trove_robbed = True
        campaign.tag_hidden_trove_stolen_gold_gp += campaign.tag_storage_gold_gp
        campaign.tag_hidden_trove_stolen_items.extend(stolen_items)
        campaign.tag_storage_gold_gp = 0
        campaign.tag_stored_items = [item for item in campaign.tag_stored_items if item.storage != "trove"]
        item_text = f" and {len(stolen_items)} stored item stack(s)" if stolen_items else ""
        result = (
            f"Hidden treasure trove risk roll {total} ({'+'.join(str(roll) for roll in rolls)}): "
            f"the cache is discovered and stolen. {campaign.tag_hidden_trove_stolen_gold_gp} gp{item_text} are marked stolen. "
            "Spend 4 Clues and pass Interrogation vs L6 to recover it."
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
    resolve_tag_closeout_task(campaign, task_action="hidden_trove_risk", log_missing=False)
    trim_tag_logs(campaign)
    return entry


def recover_hidden_treasure_trove(campaign: CampaignState, character: Character) -> TagDowntimeLogEntry:
    if not campaign.tag_hidden_trove_robbed:
        return append_tag_log(
            campaign,
            action="hidden_trove_recovery",
            character=character,
            result_text="No stolen hidden treasure trove is currently marked for recovery.",
        )
    if character.clues < 4:
        return append_tag_log(
            campaign,
            action="hidden_trove_recovery",
            character=character,
            result_text=f"{character.name} needs 4 Clues to recover the hidden treasure trove; current Clues {character.clues}.",
        )
    character.clues -= 4
    roll = roll_d6()
    modifier = streetwise_modifier(character, action="interrogation")
    total = roll + modifier
    if total >= 6:
        recovered_gold = campaign.tag_hidden_trove_stolen_gold_gp
        recovered_items = campaign.tag_hidden_trove_stolen_items
        campaign.tag_storage_gold_gp += recovered_gold
        campaign.tag_stored_items.extend(recovered_items)
        campaign.tag_hidden_trove_stolen_gold_gp = 0
        campaign.tag_hidden_trove_stolen_items = []
        campaign.tag_hidden_trove_robbed = False
        result = (
            f"{character.name} spends 4 Clues and passes Interrogation vs L6 "
            f"({roll} {modifier:+d} = {total}); hidden trove recovered: {recovered_gold} gp "
            f"and {len(recovered_items)} item stack(s)."
        )
        resolve_tag_closeout_task(campaign, task_action="hidden_trove_recovery", log_missing=False)
    else:
        result = (
            f"{character.name} spends 4 Clues but fails Interrogation vs L6 "
            f"({roll} {modifier:+d} = {total}); the trove remains stolen and the next Riff-Raff encounter hates the interrogator."
        )
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action="hidden_trove_recovery",
        character=character,
        roll=roll,
        modifier=modifier,
        total=total,
        result_text=result,
    )


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
    upsert_tag_settlement(campaign, name=campaign.settlement_name, size=campaign.settlement_size, notes=campaign.settlement_notes)
    return campaign


def upsert_tag_settlement(
    campaign: CampaignState,
    *,
    name: str,
    size: int = 0,
    notes: str = "",
) -> TagSettlementState:
    clean_name = (name or "").strip()[:80] or "Home Settlement"
    clean_size = max(-3, min(3, int(size)))
    clean_notes = (notes or "").strip()[:1000]
    existing = next((item for item in campaign.tag_settlements if item.name.lower() == clean_name.lower()), None)
    if existing is None:
        existing = TagSettlementState(name=clean_name, size=clean_size, notes=clean_notes, created_at=now_utc())
        campaign.tag_settlements.append(existing)
    else:
        existing.name = clean_name
        existing.size = clean_size
        existing.notes = clean_notes
    return existing


def select_tag_settlement(campaign: CampaignState, *, settlement_id: str = "", name: str = "") -> TagSettlementState | None:
    clean_id = (settlement_id or "").strip()
    clean_name = (name or "").strip().lower()
    settlement = next(
        (
            item
            for item in campaign.tag_settlements
            if (clean_id and item.id == clean_id) or (clean_name and item.name.lower() == clean_name)
        ),
        None,
    )
    if settlement is None:
        return None
    campaign.settlement_name = settlement.name
    campaign.settlement_size = settlement.size
    campaign.settlement_notes = settlement.notes
    return settlement


def delete_tag_settlement(campaign: CampaignState, *, settlement_id: str = "", name: str = "") -> bool:
    before = len(campaign.tag_settlements)
    clean_id = (settlement_id or "").strip()
    clean_name = (name or "").strip().lower()
    campaign.tag_settlements = [
        item
        for item in campaign.tag_settlements
        if not ((clean_id and item.id == clean_id) or (clean_name and item.name.lower() == clean_name))
    ]
    if not campaign.tag_settlements:
        upsert_tag_settlement(campaign, name=campaign.settlement_name, size=campaign.settlement_size, notes=campaign.settlement_notes)
    return len(campaign.tag_settlements) != before


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
    upsert_tag_settlement(campaign, name=to_name, size=new_size)
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


def reroll_guild_availability(
    campaign: CampaignState,
    *,
    item_name: str,
    difficulty: int = 6,
    base_price_gp: int | None = None,
) -> TagDowntimeLogEntry:
    if not tag_guild_benefits_active(campaign):
        return append_tag_log(
            campaign,
            action="guild_availability_reroll",
            result_text="Guild availability reroll unavailable: Guild benefits are inactive or coffers are empty.",
        )
    if campaign.tag_guild_availability_reroll_used:
        return append_tag_log(
            campaign,
            action="guild_availability_reroll",
            result_text="Guild availability reroll already used for this adventure/month. Reset it after the next closeout/upkeep window.",
        )
    check = check_item_availability(
        campaign,
        item_name=item_name,
        difficulty=difficulty,
        base_price_gp=base_price_gp,
    )
    campaign.tag_guild_availability_reroll_used = True
    return append_tag_log(
        campaign,
        action="guild_availability_reroll",
        roll=check.roll,
        modifier=check.settlement_size,
        total=check.total,
        result_text=f"Guild availability reroll used for {check.item_name}: {check.result_text}",
    )


def reset_guild_availability_reroll(campaign: CampaignState) -> TagDowntimeLogEntry:
    campaign.tag_guild_availability_reroll_used = False
    resolve_tag_closeout_task(campaign, task_action="guild_availability_reroll_reset", log_missing=False)
    return append_tag_log(
        campaign,
        action="guild_availability_reroll_reset",
        result_text="Guild availability reroll reset for the next adventure/month window.",
    )


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


def _tag_look_tough_bonus(character: Character, base_modifier: int) -> tuple[int, str]:
    if TAG_LOOK_TOUGH_MARKER not in character.statuses:
        return 0, ""
    bonus = level_tier_band(character.level) if base_modifier >= character.level else character.level
    character.statuses.remove(TAG_LOOK_TOUGH_MARKER)
    note = (
        f" TAG Look Tough spell consumed: +{bonus} "
        + ("tier-number bonus because this roll already added +Level." if base_modifier >= character.level else "Level bonus.")
    )
    return bonus, note


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
    spell_bonus, spell_note = _tag_look_tough_bonus(character, modifier)
    modifier += spell_bonus
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
    result = f"{result}{spell_note}"
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
    member_character_ids: list[str] | None = None,
    active_character_ids: list[str] | None = None,
    guild_member: bool | None = None,
    guild_coffers_gp: int | None = None,
) -> CampaignState:
    if troupe_name is not None:
        campaign.tag_troupe_name = (troupe_name.strip() or "Adventuring Troupe")[:80]
    if member_character_ids is not None:
        seen_members: set[str] = set()
        campaign.tag_troupe_member_character_ids = [
            str(character_id)
            for character_id in member_character_ids
            if str(character_id) and not (str(character_id) in seen_members or seen_members.add(str(character_id)))
        ]
    if active_character_ids is not None:
        seen: set[str] = set()
        member_ids = set(campaign.tag_troupe_member_character_ids)
        campaign.tag_troupe_active_character_ids = [
            str(character_id)
            for character_id in active_character_ids
            if str(character_id)
            and (not member_ids or str(character_id) in member_ids)
            and not (str(character_id) in seen or seen.add(str(character_id)))
        ][:4]
    if guild_member is not None:
        was_guild_member = campaign.tag_guild_member
        requested_guild_member = bool(guild_member)
        if was_guild_member and not requested_guild_member and campaign.tag_guild_coffers_gp < TAG_GUILD_STARTING_COFFERS_GP:
            campaign.tag_guild_member = True
            append_tag_log(
                campaign,
                action="guild_leaving_restriction",
                result_text=(
                    f"Guild leaving blocked: coffers are {campaign.tag_guild_coffers_gp} gp; "
                    f"restore coffers to at least {TAG_GUILD_STARTING_COFFERS_GP} gp before leaving the Adventurers Guild."
                ),
            )
        else:
            campaign.tag_guild_member = requested_guild_member
        if campaign.tag_guild_member and not was_guild_member and campaign.tag_guild_coffers_gp <= 0 and guild_coffers_gp in {None, 0}:
            campaign.tag_guild_coffers_gp = TAG_GUILD_STARTING_COFFERS_GP
    if guild_coffers_gp is not None:
        requested_coffers = max(0, int(guild_coffers_gp))
        if campaign.tag_guild_member and requested_coffers <= 0 and campaign.tag_guild_coffers_gp == TAG_GUILD_STARTING_COFFERS_GP:
            campaign.tag_guild_coffers_gp = TAG_GUILD_STARTING_COFFERS_GP
        else:
            campaign.tag_guild_coffers_gp = requested_coffers
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
    unit_cost = int(service["cost_gp"])
    free_guild_martial_arts = service_key == "martial_arts_training" and tag_guild_benefits_active(campaign)
    if free_guild_martial_arts:
        unit_cost = 0
    cost = unit_cost * qty
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
        result_text=(
            f"{character.name} buys {qty}x {service['label']} for {cost} gp; {service['result']}."
            + (" TAG Guild members train for free; roll Tier die before the adventure for the injury risk." if free_guild_martial_arts else "")
        ),
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
    class_id = (character.class_id or character.class_name or "").lower().replace(" ", "_").replace("-", "_")
    gambler_bonus = 1 if class_id in {"halfling", "rogue", "swashbuckler", "harlequin", "assassin"} else 0
    if TAG_WIZARDS_LUCK_MARKER in character.statuses:
        return _roll_gambling_house_wizards_luck(campaign, character, stake_gp=stake, gambler_bonus=gambler_bonus)
    roll = roll_d10()
    total = roll + gambler_bonus
    return _resolve_gambling_house_roll(
        campaign,
        character,
        stake_gp=stake,
        roll=roll,
        modifier=gambler_bonus,
        total=total,
    )


def _resolve_gambling_house_roll(
    campaign: CampaignState,
    character: Character,
    *,
    stake_gp: int,
    roll: int,
    modifier: int,
    total: int,
    prefix: str = "",
) -> TagDowntimeLogEntry:
    stake = max(0, int(stake_gp))
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
        modifier=modifier,
        total=total,
        cost_gp=stake,
        result_text=f"{prefix}{result}",
    )


def _roll_gambling_house_wizards_luck(
    campaign: CampaignState,
    character: Character,
    *,
    stake_gp: int,
    gambler_bonus: int,
) -> TagDowntimeLogEntry:
    desired = 10
    spell_roll = roll_d6()
    character.statuses.remove(TAG_WIZARDS_LUCK_MARKER)
    if spell_roll == 1:
        fine = 50 * max(1, character.level) + (3 * stake_gp)
        paid = min(character.gold, fine)
        character.gold -= paid
        if paid < fine:
            debt = fine - paid
            debt_status = f"TAG Wizard's Luck jail fine debt {debt} gp"
            if debt_status not in character.statuses:
                character.statuses.append(debt_status)
        character.updated_at = now_utc()
        return append_tag_log(
            campaign,
            action="gambling_house",
            character=character,
            roll=spell_roll,
            modifier=character.level,
            total=spell_roll + character.level,
            cost_gp=paid,
            result_text=(
                f"{character.name} uses Wizard's Luck to cheat at the Gambling House but rolls a natural 1. "
                f"The caster is caught and owes a {fine} gp fine; {paid} gp paid now."
            ),
        )
    spell_total = spell_roll + max(1, character.level)
    if spell_total >= desired:
        character.gold -= stake_gp
        win = ceil(stake_gp * 1.5)
        character.gold += win
        character.updated_at = now_utc()
        return append_tag_log(
            campaign,
            action="gambling_house",
            character=character,
            roll=spell_roll,
            modifier=character.level,
            total=spell_total,
            cost_gp=stake_gp,
            result_text=(
                f"{character.name} uses Wizard's Luck to choose Gambling House result 10. "
                f"Spellcasting d6={spell_roll}+L{character.level}={spell_total} succeeds; wins +50% and leaves with {win} gp from a {stake_gp} gp stake."
            ),
        )
    fallback_roll = roll_d10()
    fallback_modifier = gambler_bonus - 2
    fallback_total = fallback_roll + fallback_modifier
    prefix = (
        f"{character.name} uses Wizard's Luck to choose Gambling House result 10, but spellcasting "
        f"d6={spell_roll}+L{character.level}={spell_total} fails; rolling Gambling House at -2. "
    )
    return _resolve_gambling_house_roll(
        campaign,
        character,
        stake_gp=stake_gp,
        roll=fallback_roll,
        modifier=fallback_modifier,
        total=fallback_total,
        prefix=prefix,
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
    spell_bonus, spell_note = _tag_look_tough_bonus(character, modifier)
    modifier += spell_bonus
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
    result = f"{result}{spell_note}"
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


def _tag_reference_int(reference: str, key: str, default: int = 0) -> int:
    clean_key = key.lower().strip()
    for raw_part in reference.replace(",", " ").replace(";", " ").split():
        if "=" not in raw_part:
            continue
        left, right = raw_part.split("=", 1)
        if left.lower().strip() != clean_key:
            continue
        try:
            return int(right.strip())
        except ValueError:
            return default
    return default


def _tag_reference_flag(reference: str, key: str) -> bool:
    clean_key = key.lower().strip()
    for raw_part in reference.replace(",", " ").replace(";", " ").split():
        if raw_part.lower().strip() == clean_key:
            return True
        if "=" in raw_part:
            left, right = raw_part.split("=", 1)
            if left.lower().strip() == clean_key and right.lower().strip() in {"1", "true", "yes", "y"}:
                return True
    return False


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
    elif clean_action == "ghastly_mine_minion_replacement":
        roll = roll_d6()
        if roll <= 4:
            table_roll = roll_d6()
            total = table_roll
            result = {
                1: "d6+1 Skeletons, HCL+2 undead minions; no treasure; crushing +1, arrows -1, no morale.",
                2: "d6+1 Skeletons, HCL+2 undead minions; no treasure; crushing +1, arrows -1, no morale.",
                3: "d6+1 Skeletons, HCL+2 undead minions; no treasure; crushing +1, arrows -1, no morale.",
                4: "d6+2 Zombies, HCL+2 undead minions; no treasure; arrows -1, no morale.",
                5: "d6+2 Zombies, HCL+2 undead minions; no treasure; arrows -1, no morale.",
                6: "2d6+1 minor ghouls, HCL+3 undead; normal treasure; wounds force HCL+1 poison save or paralysis.",
            }[table_roll]
            parts.append(f"Replacement roll d6={roll}: replace normal minions. Ghastly Mine Minions d6={table_roll}: {result}")
        else:
            parts.append(f"Replacement roll d6={roll}: keep the normal minion result.")
    elif clean_action == "ghastly_mine_major_replacement":
        roll = roll_d6()
        if roll <= 4:
            table_roll = roll_d6()
            total = table_roll
            result = {
                1: "Minor Mummy, HCL+3 undead Boss, 4 Life, 2 attacks, treasure +2; fire spells +2.",
                2: "Minor Mummy, HCL+3 undead Boss, 4 Life, 2 attacks, treasure +2; fire spells +2.",
                3: "Minor Skeletal Demon, HCL+5 undead, 7 Life, 2 attacks, 3 treasure rolls; blood spawns armored skeletons.",
                4: "Minor Wraith, HCL+5 undead, 6 Life, 2 treasure rolls; possible lantern extinction and level drain.",
                5: "Minor Vampire, HCL+6 undead, 6 Life; level drain save and Abyss vampirism handling where used.",
                6: "Minor Ghoul King, HCL+4 undead, 7 Life, 4 attacks, treasure +1 or secret document worth 3 Clues.",
            }[table_roll]
            parts.append(f"Replacement roll d6={roll}: replace Boss/Weird result. Ghastly Mine Major Foe d6={table_roll}: {result}")
        else:
            parts.append(f"Replacement roll d6={roll}: keep the normal Boss/Weird result.")
    elif clean_action == "ghastly_mine_treasure_conversion":
        roll = roll_d6()
        if roll <= 3:
            parts.append(f"Treasure conversion d6={roll}: gp treasure becomes one gem or nugget of the same gp value.")
        else:
            parts.append(f"Treasure conversion d6={roll}: keep gp treasure as normal.")
    elif clean_action == "ghastly_mine_cave_in":
        prior = max(0, int(clue_cost))
        total = prior + 1
        if prior >= 3:
            parts.append(
                f"Cave-in count becomes {total}. This cave-in is L6 and deals 2 damage on a failed Save; after the party exits, the mine collapses and traps any character left dead, paralyzed, or petrified."
            )
        else:
            parts.append(f"Cave-in count becomes {total}. All characters Save vs L5 trap or take 1 wound; dwarves and rogues add +L, gnomes add +1/2 L.")
    elif clean_action == "fiendish_abyss_prisoner":
        roll = roll_d6()
        if roll <= 3:
            parts.append(f"Prisoner Table d6={roll}: noble prisoner offers a mission; roll on the Minor Unique Quest Table if accepted.")
        elif roll <= 5:
            encounter_roll = roll_d6()
            total = 50
            encounter_text = "Riff-Raff encounter occurs on the escort home" if encounter_roll <= 2 else "no Riff-Raff encounter on the escort home"
            parts.append(
                f"Prisoner Table d6={roll}: merchant pays 50 gp if escorted home and then shares information. Escort risk d6={encounter_roll}: {encounter_text}. Roll Rumors, or Minor Unique Quest if all rumors are used."
            )
        else:
            parts.append(
                "Prisoner Table d6=6: prisoner gives a silver knife, one vial of holy water, and a treasure map. Follow it now or after resting; create a standard/thematic dungeon and roll Map Leads To."
            )
    elif clean_action == "minotaur_maze_lost_check":
        guide = cost > 0
        target = 2 if guide else 3
        roll = roll_d6()
        result = "lost" if roll <= target else "not lost"
        guide_note = " with dungeon guide" if guide else ""
        parts.append(f"Backtracking lost check{guide_note}: d6={roll} vs {target}-in-6, party is {result}.")
        if roll <= target:
            parts.append("Move into another connected room; if the room has only one exit, remain there and test for wandering monsters.")
    elif clean_action == "minotaur_maze_wandering":
        roll = roll_d6()
        if roll <= 3:
            count = roll_d6()
            total = count
            parts.append(f"Wandering subtype d6={roll}: {count} immature goatmen, HCL+2 minions max L5, morale +1, first attack as HCL+3.")
        elif roll <= 5:
            count = roll_d6()
            total = count
            parts.append(f"Wandering subtype d6={roll}: {count} immature minotaurs, HCL+3 minions max L6, morale +1, treasure -1, charge first attack as HCL+4.")
        else:
            gold_a = roll_d6()
            gold_b = roll_d6()
            total = gold_a * gold_b
            gem_roll = roll_d6()
            if gem_roll == 1:
                gem_value = sum(roll_d6() for _ in range(4))
                parts.append(
                    f"Wandering subtype d6=6: one greedy adult minotaur with {gold_a}x{gold_b}={total} gp and gem chance d6=1: gem worth 4d6={gem_value} gp. May be bribed with any gem worth 150 gp or more."
                )
            else:
                parts.append(
                    f"Wandering subtype d6=6: one greedy adult minotaur with {gold_a}x{gold_b}={total} gp. Gem chance d6={gem_roll}: no gem. May be bribed with any gem worth 150 gp or more."
                )
    elif clean_action == "minotaur_maze_event":
        roll = roll_d6()
        result = {
            1: "Ghost passes through the party; all characters Save vs L4 fear or lose 1 Life, clerics add +L.",
            3: "Lady in Orange offers a quest; accept and roll Quest Table, refuse to ignore later appearances, or gain never-lost benefit after completing her quest.",
            4: "Trap; roll on a traps table appropriate to the party's experience tier.",
            5: "Choose alchemist/healer special event or hire a dungeon guide for HCL x 5 gp.",
            6: "Choose alchemist/healer special event or hire a dungeon guide for HCL x 5 gp.",
        }
        if roll == 2:
            subtype = roll_d6()
            total = subtype
            if subtype <= 2:
                parts.append(f"Special Event d6=2: wandering monsters attack; subtype d6={subtype}: roll on the 4AD Vermin Table.")
            elif subtype <= 4:
                count = roll_d6()
                total = count
                parts.append(f"Special Event d6=2: wandering monsters attack; subtype d6={subtype}: {count} young minotaurs.")
            else:
                parts.append(f"Special Event d6=2: wandering monsters attack; subtype d6={subtype}: one adult minotaur.")
        else:
            parts.append(f"Special Event d6={roll}: {result[roll]}")
    elif clean_action == "castle_cleanup_pay":
        minion_vermin = cost
        party_count = _tag_reference_int(reference, "party", 4)
        boss_weird = _tag_reference_int(reference, "boss", _tag_reference_int(reference, "major", 0))
        cache = 100 if _tag_reference_flag(reference, "cache") else 0
        total = (25 * max(0, party_count)) + (2 * minion_vermin) + (20 * max(0, boss_weird)) + cache
        parts.append(
            f"Castle pay tally: party {party_count} x25 gp + minion/vermin {minion_vermin} x2 gp + Boss/Weird {boss_weird} x20 gp"
            f"{' + portrait cache 100 gp' if cache else ''} = {total} gp. Job pays only if completed in one session without leaving and returning."
        )
    elif clean_action == "griffin_mountain_check":
        reduced = cost > 0
        target = 1 if reduced else 2
        roll = roll_d6()
        result = "wandering monster" if roll <= target else "no encounter"
        parts.append(f"Griffin mountain check d6={roll} vs {target}-in-6: {result}. Roll five checks up and five down.")
    elif clean_action == "griffin_nest_search":
        roll = roll_d6()
        if roll == 6:
            parts.append("Nest search d6=6: the griffin nest is found.")
        elif roll == 1:
            parts.append("Nest search d6=1: griffins attack unless the worst-Stealth character passes a L7 Stealth roll.")
        else:
            parts.append(f"Nest search d6={roll}: nest not found; continue searching.")
    elif clean_action == "griffin_egg_count":
        roll = roll_d3()
        total = roll + 1
        parts.append(f"Griffin eggs d3={roll}+1: {total} eggs in the nest. Most characters carry 2 eggs; elves carry 3; ogres carry none.")
    elif clean_action == "griffin_egg_break":
        eggs = max(1, cost)
        broken = 0
        rolls: list[int] = []
        value = 0
        for _ in range(eggs):
            egg_roll = roll_d6()
            rolls.append(egg_roll)
            if egg_roll <= 2:
                broken += 1
                value += roll_d6() + roll_d6()
        total = value
        parts.append(
            f"Egg break checks for {eggs} egg(s): rolls {rolls}; {broken} broken. Broken egg salvage value is {value} gp total from 2d6 each."
        )
    elif clean_action == "portrait_outbound_check":
        leg = max(1, min(6, cost or 1))
        roll = roll_d6()
        if leg <= 4:
            result = "Outside of Town Ambush Table encounter" if roll <= 2 else "no encounter"
            parts.append(f"Portrait outbound leg {leg} d6={roll}: {result}. First four checks use Outside of Town Ambush on 1-2.")
        else:
            elf_lead = _tag_reference_flag(reference, "elf")
            target = 1 if elf_lead else 2
            result = "Weird Monsters Around Town encounter" if roll <= target else "no encounter"
            parts.append(f"Portrait outbound leg {leg} d6={roll} vs {target}-in-6: {result}. Last two checks use Weird Monsters Around Town.")
    elif clean_action == "portrait_persuasion":
        modifier = _tag_reference_int(reference, "mod", cost)
        roll = roll_d6()
        total = roll + modifier
        if roll == 1:
            parts.append(f"Persuasion roll natural 1 with modifier {modifier}: chosen character is kicked out of the hermitage.")
        elif total >= 6:
            parts.append(f"Persuasion roll d6={roll}+{modifier}={total}: nobleman agrees to pose.")
        else:
            parts.append(f"Persuasion roll d6={roll}+{modifier}={total}: failed; may try again. If all characters are ejected, donate 20 gp or mission fails.")
    elif clean_action == "portrait_return_snatch":
        roll = roll_d6()
        if roll == 1:
            parts.append("Painting snatch d6=1: a foe grabs the painting. The party has one turn to stop the snatcher with ranged weapon or Sleep; Fireball/Lightning forbidden.")
        else:
            parts.append(f"Painting snatch d6={roll}: painting is not snatched in this surprised return encounter.")
    elif clean_action == "sewers_vermin":
        roll = roll_d6()
        if roll <= 3:
            count = roll_d6() + roll_d6()
            total = count
            parts.append(f"Sewers Vermin d6={roll}: {count} rats, HCL animal vermin, morale -1, no treasure; bribe 2 food for all rats on reaction 2-4.")
        else:
            parts.append(f"Sewers Vermin d6={roll}: Horde of sewer rats, L4 animal horde, 4 Life, no treasure; fire-based spell destroys it automatically.")
    elif clean_action == "sewers_minions":
        roll = roll_d6()
        if roll <= 3:
            count = roll_d6() + roll_d6()
            total = count
            parts.append(f"Sewers Minions d6={roll}: {count} ratmen, HCL+1 minions, morale -1, treasure -1; bribe 5 gp each on reaction 2-3.")
        else:
            count = roll_d6()
            total = count
            parts.append(f"Sewers Minions d6={roll}: {count} crocodile men, HCL+2 minions, no treasure; bribe 6 gp each on reaction 1-2.")
    elif clean_action == "sewers_disease":
        roll = roll_d6()
        modifier = cost
        total = roll + modifier
        if total >= 4:
            parts.append(f"Disease Save d6={roll}+{modifier}={total} vs L4: success; no post-adventure sewer infection.")
        else:
            parts.append(f"Disease Save d6={roll}+{modifier}={total} vs L4: infection; -1 Defense until Blessing or end of adventure.")
    elif clean_action == "monoceros_tracking":
        modifier = _tag_reference_int(reference, "mod", cost)
        roll = roll_d6()
        total = roll + modifier
        if roll == 1:
            parts.append(
                f"Tracking roll natural 1 with modifier {modifier}: hunting accident. Character must Save vs L5 danger or lose Tier Life and is out of the hunt."
            )
        elif total >= 6:
            parts.append(f"Tracking roll d6={roll}+{modifier}={total}: hunter finds the monoceros. Multiple successes cooperate; failures arrive after three turns.")
        else:
            parts.append(f"Tracking roll d6={roll}+{modifier}={total}: hunter does not find it yet and joins successful hunters after three turns.")
    elif clean_action == "monoceros_clue_encounter":
        roll = roll_d6()
        if roll <= 2:
            parts.append(f"3-Clue shortcut risk d6={roll}: roll a random Weird Monster Around Town encounter before meeting the monoceros.")
        else:
            parts.append(f"3-Clue shortcut risk d6={roll}: no Weird Monster encounter before the monoceros.")
    elif clean_action == "monoceros_hide":
        roll = roll_d6()
        if roll <= 4:
            parts.append(f"Monoceros hide d6={roll}: non-magical hit lands normally.")
        else:
            parts.append(f"Monoceros hide d6={roll}: thick hide turns the blow; ignore the wound.")
    elif clean_action == "bandit_stolen_goods_check":
        roll = roll_d6()
        if roll == 1:
            total = sum(roll_d6() for _ in range(8))
            trap_roll = roll_d6()
            trap_text = "trapdoor protection is present" if trap_roll <= 3 else "no trapdoor protection"
            parts.append(f"Stolen goods found: 8d6={total} gp. Trapdoor roll d6={trap_roll}: {trap_text}. Claim the gp only after resolving the room.")
        else:
            parts.append(f"Stolen-goods roll d6={roll}: no stolen goods in this room.")
    elif clean_action == "bofto_scene_choice":
        choice = (reference.strip()[:80] or "steal object / talk to family / leave").lower()
        parts.append(
            f"Scene 9 choice recorded: {choice}. If stealing the star-shaped object, resolve Scene 14; if talking to Bofto's family, resolve Scene 17; if leaving, return to normal TAG settlement activity."
        )
    elif clean_action == "tag_ambush_chance":
        target = max(1, min(6, cost or 2))
        roll = roll_d6()
        table = reference.strip()[:80] or "Riff-Raff or Outside of Town Ambush Table"
        if roll <= target:
            parts.append(f"Ambush chance d6={roll} vs {target}-in-6: encounter occurs. Roll on {table}.")
        else:
            parts.append(f"Ambush chance d6={roll} vs {target}-in-6: no encounter.")
    elif clean_action == "medusa_assassin_ambush":
        failed = cost > 0
        if failed:
            count = roll_d3() + 2
            roll = count - 2
            total = count
            parts.append(
                f"At least one L6 Stealth Save failed on the way to the hunter's cabin: d3+2={count} assassin agents ambush the party. Convince them with L5 Streetwise or fight HCL+2 dagger minions with 4d6 gp total treasure."
            )
        else:
            parts.append("All characters passed L6 Stealth on the way to the hunter's cabin; the party reaches the cabin undisturbed.")
    elif clean_action == "medusa_stealth_approach":
        modifier = _tag_reference_int(reference, "mod", cost)
        roll = roll_d6()
        total = roll + modifier
        if total >= 6:
            parts.append(f"Medusa cabin stealth d6={roll}+{modifier}={total} vs L6: success. Party attacks once before Xasartha uses her gaze.")
        else:
            parts.append(
                f"Medusa cabin stealth d6={roll}+{modifier}={total} vs L6: failed. The scouting character is turned to stone with no Save; remaining party fights normally and must Save vs gaze."
            )
    elif clean_action == "medusa_reaction":
        roll = roll_d6()
        if roll == 1:
            parts.append("Xasartha reaction d6=1: bribe, 6d6 gp or one jewel/gem worth at least 15 gp.")
        elif roll == 2:
            parts.append("Xasartha reaction d6=2: quest branch. Resolve the printed medusa quest text before deciding combat/reward.")
        elif roll <= 5:
            parts.append(f"Xasartha reaction d6={roll}: fight.")
        else:
            parts.append("Xasartha reaction d6=6: fight to the death.")
    elif clean_action == "leprechaun_shoes":
        pairs = max(1, cost or 1)
        total = pairs * 200
        if character is not None and character.gold >= total:
            character.gold -= total
            for _ in range(pairs):
                character.inventory.append("Shoes of Fast Walk")
            character.updated_at = now_utc()
            parts.append(f"{character.name} buys {pairs} pair(s) of Shoes of Fast Walk for {total} gp; add +Tier to Defense when withdrawing or fleeing melee.")
        elif character is not None:
            parts.append(f"{character.name} needs {total} gp for {pairs} pair(s) of Shoes of Fast Walk but has {character.gold}.")
        else:
            parts.append(f"Record purchase of {pairs} pair(s) of Shoes of Fast Walk at {total} gp total; assign only to eligible characters or hirelings.")
    elif clean_action == "leprechaun_illusion_spell":
        free = _tag_reference_flag(reference, "free")
        total = 0 if free else 100
        spell_note = reference.strip()[:80] or "chosen illusion spell"
        if character is not None and character.gold >= total:
            character.gold -= total
            marker = f"TAG leprechaun illusion spell pending: {spell_note}"
            if marker not in character.statuses:
                character.statuses.append(marker)
            character.updated_at = now_utc()
            price = "free after buying at least three pairs of magical shoes" if free else "100 gp"
            parts.append(f"{character.name} learns or records {spell_note} from the leprechauns for {price}.")
        elif character is not None:
            parts.append(f"{character.name} needs {total} gp to learn the leprechaun illusion spell but has {character.gold}.")
        else:
            parts.append("Record one eligible character learning an illusion spell from the leprechauns; cost is 100 gp or free after buying at least three pairs of magical shoes.")
    elif clean_action == "mutant_fish_hypnosis":
        modifier = _tag_reference_int(reference, "mod", cost)
        chaos = _tag_reference_flag(reference, "chaos")
        if chaos:
            parts.append("Mutant fish hypnosis: chaos-tainted character fails automatically per Scene 12.")
        else:
            roll = roll_d6()
            total = roll + modifier
            result = "resists the chanting" if total >= 5 else "fails and is drawn toward the water"
            parts.append(f"Mutant fish hypnosis Save d6={roll}+{modifier}={total} vs L5: character {result}. Resolve rescue timing from Scene 12.")
    elif clean_action == "gargoyle_count":
        roll = roll_d6()
        total = roll + 2
        parts.append(f"White gargoyle count d6={roll}+2: {total} gargoyles in the lair.")
    elif clean_action == "gargoyle_surprise":
        roll = roll_d6()
        if roll <= 3:
            parts.append(f"White gargoyle camouflage d6={roll}: gargoyles surprise the party; roll reactions before combat.")
        else:
            parts.append(f"White gargoyle camouflage d6={roll}: no surprise.")
    elif clean_action == "gargoyle_skin":
        roll = roll_d6()
        if roll <= 2:
            parts.append(f"White gargoyle stone-hard skin d6={roll}: this mundane-weapon hit bounces off with no effect.")
        else:
            parts.append(f"White gargoyle stone-hard skin d6={roll}: hit affects the gargoyle normally. Magic and masterwork weapons ignore this check.")
    elif clean_action == "bofto_theft_save":
        modifier = _tag_reference_int(reference, "mod", cost)
        roll = roll_d6()
        total = roll + modifier
        if total >= 6:
            parts.append(f"Scene 14 thievery Save d6={roll}+{modifier}={total} vs L6: success. Go to Scene 19 and resolve the star-shaped object Will Save.")
        else:
            parts.append(f"Scene 14 thievery Save d6={roll}+{modifier}={total} vs L6: failed. Go to Scene 18; delete Rumor 1 from the Rumors Table.")
    elif clean_action == "star_object_will_save":
        modifier = _tag_reference_int(reference, "mod", cost)
        roll = roll_d6()
        total = roll + modifier
        if total >= 8:
            parts.append(f"Scene 19 Will Save d6={roll}+{modifier}={total} vs L8: success; no Madness from picking up the star-shaped object.")
        else:
            if character is not None and "TAG star-shaped object curse carrier" not in character.statuses:
                character.statuses.append("TAG star-shaped object curse carrier")
                character.updated_at = now_utc()
            parts.append(
                f"Scene 19 Will Save d6={roll}+{modifier}={total} vs L8: failed. Character gains 1 Madness and carries the star-shaped object curse; add the Madness/status effect manually if not already tracked."
            )
    elif clean_action == "star_slayer_check":
        roll = roll_d6()
        if roll <= 2:
            parts.append("Star-shaped object curse d6={}: replace this Boss/Weird Monster with a Star-Slayer from Beyond; it always fights to the death.".format(roll))
        else:
            parts.append(f"Star-shaped object curse d6={roll}: no Star-Slayer replacement for this major foe.")
    elif clean_action == "treasure_map_follow":
        bonus = cost
        roll = roll_d6()
        total = roll + bonus
        natural_note = " Natural 1 remains a Deathtrap even with bonuses." if roll == 1 and bonus else ""
        if roll <= 2:
            result = "Deathtrap: roll Riff-Raff, foes go first, no withdrawal unless they flee."
        elif total == 3:
            result = "Waste of time: roll 3-in-6 Outside of Town Opposition chance."
        elif total == 4:
            result = "Accurate but incomplete: add one stored +1 bonus for a future treasure-map roll."
            campaign.tag_map_bonus += 1
        else:
            lead_roll = roll_d6()
            result = f"The Real Deal: Map Leads To d6={lead_roll}: {TAG_MAP_LEADS_TO[lead_roll]}"
        parts.append(f"Following Treasure Map d6={roll}{format_bonus(bonus)}={total}: {result}{natural_note}")
    elif clean_action == "map_cave_room_count":
        roll = roll_d6()
        total = roll + 3
        parts.append(f"Map cave complex room count d6={roll}+3: dungeon ends after {total} rooms. Last room has a Boss with +2 Life and double maximum treasure.")
    elif clean_action == "map_temple_idol":
        roll = roll_d3()
        total = roll * 100
        parts.append(f"Forgotten temple idol value d3={roll} x100 gp: golden idol is worth {total} gp after the chaos cultists are defeated.")
    elif clean_action == "map_temple_scroll":
        roll = roll_d6()
        if roll <= 3:
            parts.append(f"Forgotten temple leader scroll chance d6={roll}: leader carries one random scroll. Roll on any spell list you choose.")
        else:
            parts.append(f"Forgotten temple leader scroll chance d6={roll}: no scroll.")
    elif clean_action == "map_humanoid_report":
        total = sum(roll_d6() for _ in range(4))
        parts.append(f"Humanoid camp report reward 4d6={total} gp. Adventure ends here and the party gains no XP rolls for the camp.")
    elif clean_action == "map_humanoid_stealth":
        modifier = _tag_reference_int(reference, "mod", cost)
        roll = roll_d6()
        total = roll + modifier
        if total >= 4:
            parts.append(f"Humanoid camp group Stealth d6={roll}+{modifier}={total} vs L4: success. Steal camp loot; roll 4AD Treasure with minimum 25 gp and avoid the fight.")
        else:
            parts.append(f"Humanoid camp group Stealth d6={roll}+{modifier}={total} vs L4: failed. Camp detects intruders and attacks the entering characters with initiative.")
    elif clean_action == "map_humanoid_forces":
        orcs = roll_d6() + roll_d6() + 3
        bosses = roll_d3()
        ogre_roll = roll_d6()
        total = orcs
        ogre_text = "black ogre present" if ogre_roll <= 2 else "no black ogre"
        parts.append(f"Humanoid camp forces: 2d6+3={orcs} orcs, 1d3={bosses} Orc Boss(es), black ogre chance d6={ogre_roll}: {ogre_text}.")
    elif clean_action == "map_structure_rooms":
        total = roll_d6() + roll_d6()
        parts.append(f"Underground structure room count 2d6={total}. Roll content in the first room; all treasure is tracked and moved to the final Boss.")
    elif clean_action == "map_lich_death_magic":
        modifier = _tag_reference_int(reference, "mod", cost)
        roll = roll_d6()
        total = roll + modifier
        if total >= 7:
            parts.append(f"Lich chamber death-magic Save d6={roll}+{modifier}={total} vs L7: success; no Life lost at entry.")
        else:
            parts.append(f"Lich chamber death-magic Save d6={roll}+{modifier}={total} vs L7: failed; character loses 1 Life. Necromancers add +L; undead/artificial characters are immune.")
    elif clean_action == "map_lich_life":
        lost_life = max(0, cost)
        total = lost_life + 4
        parts.append(f"Lich Life total: party Life lost to entry death magic {lost_life}+4 = {total} Life.")
    elif clean_action == "map_lich_treasure":
        total = sum(roll_d6() for _ in range(10))
        parts.append(f"Lich treasure: 10d6={total} gp, 1 treasure map, and 3 random scrolls from spell lists you choose.")
    elif clean_action == "giant_lair_boulder":
        roll = roll_d6()
        if roll <= 4:
            parts.append(
                f"Giant's Lair first-turn boulder d6={roll}: the hill giant throws a boulder before melee. Resolve the printed boulder attack before normal combat; spells hit the giant at +2."
            )
        else:
            parts.append(f"Giant's Lair first-turn boulder d6={roll}: no boulder throw before melee. Spells still hit the giant at +2.")
    elif clean_action == "giant_lair_treasure":
        parts.append("Giant's Lair finale: roll three treasure rolls and double all gp treasure. The final room must be at least nine squares and not a corridor.")
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


def _tag_room_by_id(rooms: list[Any], room_id: str) -> dict[str, Any] | None:
    return next((room for room in rooms if isinstance(room, dict) and room.get("id") == room_id), None)


def _append_room_note(room: dict[str, Any], note: str) -> None:
    description = str(room.get("description") or "")
    if note not in description:
        room["description"] = f"{description} {note}".strip()


def _remove_encounter_triggers(room: dict[str, Any]) -> int:
    triggers = room.get("triggers")
    if not isinstance(triggers, list):
        return 0
    kept = [trigger for trigger in triggers if not isinstance(trigger, dict) or "encounter" not in trigger]
    removed = len(triggers) - len(kept)
    room["triggers"] = kept
    return removed


def _ensure_complication_encounter(room: dict[str, Any], tag_reference: dict[str, Any]) -> bool:
    triggers = room.setdefault("triggers", [])
    if not isinstance(triggers, list):
        room["triggers"] = []
        triggers = room["triggers"]
    if any(isinstance(trigger, dict) and "encounter" in trigger for trigger in triggers):
        return False
    pages = tag_reference.get("pdf_pages") or "TAG scene"
    triggers.append(
        {
            "when": "on_enter",
            "once": True,
            "log": f"TAG hostile branch {pages}: resolve the lead complication or proxy fight.",
            "encounter": {"foes": [{"name": "Goblins", "count": 4}]},
        }
    )
    return True


def _set_exit_status(room: dict[str, Any], to_room: str, status: str) -> int:
    changed = 0
    for exit_data in room.get("exits") or []:
        if isinstance(exit_data, dict) and exit_data.get("to") == to_room and exit_data.get("status") != status:
            exit_data["status"] = status
            changed += 1
    return changed


def _retarget_exit(room: dict[str, Any], from_room: str, to_room: str, *, status: str = "open") -> bool:
    for exit_data in room.get("exits") or []:
        if isinstance(exit_data, dict) and exit_data.get("to") == from_room:
            exit_data["to"] = to_room
            exit_data["status"] = status
            return True
    return False


def _remove_exits_to(room: dict[str, Any], to_room: str) -> int:
    exits = room.get("exits")
    if not isinstance(exits, list):
        return 0
    kept = [exit_data for exit_data in exits if not isinstance(exit_data, dict) or exit_data.get("to") != to_room]
    removed = len(exits) - len(kept)
    room["exits"] = kept
    return removed


def _ensure_unlocked_scene_room(
    rooms: list[Any],
    route: TagAdventureRouteState,
    tag_reference: dict[str, Any],
) -> bool:
    if _tag_room_by_id(rooms, "tag-unlocked-scene") is not None:
        room = _tag_room_by_id(rooms, "tag-unlocked-scene")
        if room is not None:
            _append_room_note(room, f"TAG route update: {route.result_text}")
        return False
    rooms.append(
        {
            "id": "tag-unlocked-scene",
            "tile_key": "13",
            "title": "Unlocked TAG Scene",
            "description": (
                "A follow-up scene is now available because of a TAG branch choice. "
                f"{route.result_text}"
            ),
            "environment": "dungeon",
            "exits": [
                {
                    "id": "tag-unlocked-scene-south",
                    "direction": "south",
                    "to": "tag-complication",
                    "kind": "door",
                    "status": "open",
                },
                {
                    "id": "tag-unlocked-scene-north",
                    "direction": "north",
                    "to": "tag-final-scene",
                    "kind": "passage",
                    "status": "open",
                },
            ],
            "triggers": [
                {
                    "when": "on_enter",
                    "once": True,
                    "log": (
                        "TAG unlocked scene: resolve the printed follow-up, clue gate, or branch before the finale. "
                        f"Source: {tag_reference.get('pdf_pages') or route.reference}."
                    ),
                }
            ],
        }
    )
    return True


def _remove_optional_side_scene(rooms: list[Any], entry: dict[str, Any] | None) -> bool:
    before = len(rooms)
    rooms[:] = [room for room in rooms if not isinstance(room, dict) or room.get("id") != "tag-side-clue"]
    if entry is not None:
        _remove_exits_to(entry, "tag-side-clue")
    return len(rooms) != before


def _latest_tag_manifest_path(data_dir: Path, campaign: CampaignState) -> tuple[str, Path] | tuple[str, None]:
    adventure_id = next((item for item in reversed(campaign.tag_generated_adventure_ids) if item), "")
    if not adventure_id:
        return "", None
    manifest_path = installed_adventure_dir(data_dir, adventure_id) / ADVENTURE_MANIFEST_FILENAME
    if not manifest_path.exists():
        return adventure_id, None
    return adventure_id, manifest_path


def apply_latest_tag_route_to_adventure(data_dir: Path, campaign: CampaignState) -> str:
    route = campaign.tag_adventure_routes[-1] if campaign.tag_adventure_routes else None
    if route is None:
        return "No TAG route marker is available to apply to a generated adventure."
    adventure_id, manifest_path = _latest_tag_manifest_path(data_dir, campaign)
    if not adventure_id:
        return "No generated TAG adventure is available for route rewrite."
    if manifest_path is None:
        return f"Generated TAG adventure {adventure_id} is not installed yet; route marker was saved only in campaign state."
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = manifest.setdefault("source", {})
    parameters = source.setdefault("parameters", {})
    tag_reference = parameters.setdefault("tag_reference", {})
    markers = tag_reference.setdefault("route_markers", [])
    markers.append(
        {
            "action": route.route_action,
            "reference": route.reference,
            "character": route.character_name,
            "clue_cost": route.clue_cost,
            "resolved": route.resolved,
            "result": route.result_text,
            "created_at": route.created_at,
        }
    )
    tag_reference["route_status"] = route.result_text
    rewrite_log = tag_reference.setdefault("route_rewrites", [])
    rooms = manifest.get("rooms") if isinstance(manifest.get("rooms"), list) else []
    entry = _tag_room_by_id(rooms, "tag-lead-entry")
    complication = _tag_room_by_id(rooms, "tag-complication")
    final = _tag_room_by_id(rooms, "tag-final-scene")
    changed_detail = "source reference"
    if isinstance(complication, dict):
        suffix = f"TAG route marker: {route.result_text}"
        _append_room_note(complication, suffix)
        if route.route_action in {"parley_success", "peaceful_branch"}:
            removed = _remove_encounter_triggers(complication)
            _set_exit_status(complication, "tag-final-scene", "open")
            changed_detail = "complication proxy combat suppressed"
            if removed:
                changed_detail += f"; {removed} hostile trigger(s) removed"
        elif route.route_action in {"clue_gate_unlocked", "unlock_scene"}:
            inserted = _ensure_unlocked_scene_room(rooms, route, tag_reference)
            retargeted = _retarget_exit(complication, "tag-final-scene", "tag-unlocked-scene", status="open")
            if not retargeted:
                _set_exit_status(complication, "tag-unlocked-scene", "open")
            changed_detail = "follow-up scene inserted and route opened" if inserted else "follow-up scene route opened"
        elif route.route_action == "clue_gate_blocked":
            _set_exit_status(complication, "tag-final-scene", "closed")
            _set_exit_status(complication, "tag-unlocked-scene", "closed")
            changed_detail = "Clue-gated route kept closed"
        elif route.route_action in {"parley_failed", "hostile_branch"}:
            restored = _ensure_complication_encounter(complication, tag_reference)
            _set_exit_status(complication, "tag-final-scene", "closed")
            _set_exit_status(complication, "tag-unlocked-scene", "closed")
            changed_detail = "hostile route preserved"
            if restored:
                changed_detail += "; hostile trigger restored"
    if route.route_action == "skip_scene":
        removed = _remove_optional_side_scene(rooms, entry if isinstance(entry, dict) else None)
        for room in rooms:
            if isinstance(room, dict):
                _append_room_note(room, "TAG route marker: optional side scene skipped/crossed off.")
        changed_detail = "optional side scene removed" if removed else "scene skip marker added to generated rooms"
    if route.route_action in {"final_route", "solo_restriction"} and isinstance(final, dict):
        _append_room_note(final, f"TAG route marker: {route.result_text}")
        if route.route_action == "final_route" and isinstance(complication, dict):
            _set_exit_status(complication, "tag-final-scene", "open")
        changed_detail = "finale/solo route marker added"
    rewrite_log.append(
        {
            "route_id": route.id,
            "action": route.route_action,
            "reference": route.reference,
            "resolved": route.resolved,
            "change": changed_detail,
            "created_at": now_utc(),
        }
    )
    tag_reference["latest_route_rewrite"] = changed_detail
    if markers and isinstance(markers[-1], dict):
        markers[-1]["rewrite"] = changed_detail
    if "Module update:" not in route.result_text:
        route.result_text = f"{route.result_text} Module update: {changed_detail}."
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return f"Applied route marker to {adventure_id}: {changed_detail}."


def apply_tag_dragon_reveal_to_latest_adventure(
    data_dir: Path,
    campaign: CampaignState,
    *,
    dragon_key: str,
    dragon_label: str,
) -> str:
    adventure_id, manifest_path = _latest_tag_manifest_path(data_dir, campaign)
    if not adventure_id:
        return "No generated TAG adventure is available for Dragon's Lair update."
    if manifest_path is None:
        return f"Generated TAG adventure {adventure_id} is not installed yet; dragon reveal was logged only in campaign state."
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source = manifest.setdefault("source", {})
    parameters = source.setdefault("parameters", {})
    tag_reference = parameters.setdefault("tag_reference", {})
    if str(tag_reference.get("title") or "") != "Dragon's Lair":
        return f"Latest generated TAG adventure {adventure_id} is not Dragon's Lair; dragon reveal was logged only in campaign state."
    dragon_data = TAG_DRAGON_TYPE_FOES.get(dragon_key, TAG_DRAGON_TYPE_FOES["darkness_or_ghoul_dragon"])
    final = _tag_room_by_id(manifest.get("rooms") if isinstance(manifest.get("rooms"), list) else [], "tag-final-scene")
    if isinstance(final, dict):
        final["title"] = str(dragon_data["name"])
        final["description"] = f"{dragon_data['description']} TAG route update: {dragon_label}."
        triggers = final.get("triggers")
        if isinstance(triggers, list):
            for trigger in triggers:
                if isinstance(trigger, dict) and isinstance(trigger.get("encounter"), dict):
                    trigger["encounter"]["foes"] = dragon_data["foes"]
                    trigger["log"] = f"TAG Dragon's Lair reveal: {dragon_label}. Resolve the printed dragon profile before claiming treasure."
    tag_reference["dragon_type_revealed"] = dragon_label
    tag_reference["final_foe_proxy"] = dragon_data["foes"][0]["name"]
    tag_reference["final_foes"] = dragon_data["foes"]
    updates = tag_reference.setdefault("module_updates", [])
    updates.append(
        {
            "action": "dragon_type_reveal",
            "result": dragon_label,
            "created_at": now_utc(),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return f"Updated {adventure_id} final scene for Dragon's Lair reveal: {dragon_label}."


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


def convert_character_gold_to_tag_bank(
    campaign: CampaignState,
    character: Character,
    *,
    include_legacy_bank: bool = False,
    legacy_bank_gold: int = 0,
    apply_deposit_fee: bool = False,
    note: str = "",
) -> TagDowntimeLogEntry:
    carried = max(0, int(character.gold or 0))
    legacy = max(0, int(legacy_bank_gold)) if include_legacy_bank else 0
    gross = carried + legacy
    if gross <= 0:
        return append_tag_log(
            campaign,
            action="tag_bank_migration",
            character=character,
            result_text=f"{character.name} has no roster or selected legacy bank gold to move into TAG banking.",
        )
    fee = ceil(gross * 0.1) if apply_deposit_fee else 0
    deposited = max(0, gross - fee)
    account = _tag_bank_account(campaign, character)
    account.gold_gp += deposited
    account.notes = note.strip()[:120] or account.notes
    character.gold = 0
    if include_legacy_bank and hasattr(character, "bank_gold"):
        character.bank_gold = 0
    character.updated_at = now_utc()
    fee_text = f" after {fee} gp TAG deposit fee" if fee else " with no migration fee"
    legacy_text = "carried and legacy bank gold" if include_legacy_bank else "carried roster gold"
    return append_tag_log(
        campaign,
        action="tag_bank_migration",
        character=character,
        cost_gp=fee,
        result_text=(
            f"{character.name} converts {gross} gp of {legacy_text} into TAG bank account credit"
            f"{fee_text}. Account balance {account.gold_gp} gp."
        ),
    )


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
            if roll <= 3:
                dragon_key = "small_dragon"
            elif roll <= 5:
                dragon_key = "young_red_dragon"
            else:
                dragon_key = "darkness_or_ghoul_dragon"
            dragon = str(TAG_DRAGON_TYPE_FOES[dragon_key]["name"])
            if dragon_key == "darkness_or_ghoul_dragon":
                dragon = f"{dragon}; split by the printed d6 follow-up"
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


TAG_GUILD_MARKERS: dict[str, str] = {
    "temporary_weapon_enchantment": "TAG Temporary Weapon Enchantment: choose one weapon; magical no Attack bonus",
    "troupe_switch": "TAG Troupe Switch pending",
    "look_tough": TAG_LOOK_TOUGH_MARKER,
    "silence_of_the_mouse": "TAG Silence of the Mouse: 6 rooms ignore setting Stealth penalties",
    "wizards_luck": TAG_WIZARDS_LUCK_MARKER,
    "speedy_recovery": "TAG Speedy Recovery settlement healing 2/day",
}


def _weapon_candidates(character: Character) -> list[str]:
    tokens = ("weapon", "bow", "crossbow", "sling", "stake", "crowbar", "handgun", "rifle", "throwing star", "flail-axe", "axe", "sword", "dagger", "mace", "spear")
    return [item for item in character.inventory if any(token in item.lower() for token in tokens)]


def _target_name(character: Character | None) -> str:
    return character.name if character is not None else "chosen target"


def cast_tag_guild_spell(
    campaign: CampaignState,
    character: Character,
    *,
    spell_key: str,
    target_character: Character | None = None,
    target_weapon: str = "",
) -> TagDowntimeLogEntry:
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
    result_extra = ""
    if spell_key == "temporary_weapon_enchantment":
        weapon = target_weapon.strip()
        if not weapon:
            candidates = _weapon_candidates(character)
            weapon = candidates[0] if candidates else ""
        if weapon and weapon in character.inventory:
            status = f"TAG Temporary Weapon Enchantment: {weapon} is magical, no Attack bonus"
            result_extra = f" Target weapon: {weapon}."
        elif weapon:
            status = str(status)
            result_extra = f" Target weapon '{weapon}' is not in {character.name}'s inventory; choose the weapon manually."
        else:
            status = str(status)
            result_extra = " No carried weapon was selected; choose the weapon manually."
    elif spell_key == "troupe_switch":
        target = _target_name(target_character)
        status = f"TAG Troupe Switch caster: may swap with {target} once this adventure"
        if target_character is not None:
            target_status = (
                f"TAG Troupe Switch recipient for {character.name}: if summoned in combat, -1 Attack/Defense/Save until encounter ends; "
                "roll 2-in-6 for no armor and 2-in-6 for one missing spell slot if applicable"
            )
            if target_status not in target_character.statuses:
                target_character.statuses.append(target_status)
            target_character.updated_at = now_utc()
        result_extra = f" Recipient: {target}. This spell may be used only once per adventure."
    elif spell_key == "silence_of_the_mouse":
        target = _target_name(target_character)
        status = f"TAG Silence of the Mouse: Stealth switched with {target}; ignore setting Stealth penalties for 6 rooms"
        if target_character is not None:
            target_status = (
                f"TAG Silence of the Mouse: Stealth switched with {character.name}; ignore setting Stealth penalties for 6 rooms"
            )
            if target_status not in target_character.statuses:
                target_character.statuses.append(target_status)
            target_character.updated_at = now_utc()
        result_extra = f" Paired character: {target}."
    if isinstance(status, str) and status not in character.statuses:
        character.statuses.append(status)
    if spell_key == "look_tough" and character.id not in campaign.tag_look_tough_character_ids:
        campaign.tag_look_tough_character_ids.append(character.id)
    character.updated_at = now_utc()
    return append_tag_log(
        campaign,
        action="guild_spell",
        character=character,
        result_text=f"{character.name} casts {spell_name}: {availability}. {effect['summary']}{result_extra}",
    )


def _remove_tag_guild_markers(character: Character, marker_key: str, marker: str) -> list[str]:
    if marker_key == "temporary_weapon_enchantment":
        prefixes = ("TAG Temporary Weapon Enchantment:",)
    elif marker_key == "troupe_switch":
        prefixes = ("TAG Troupe Switch",)
    elif marker_key == "silence_of_the_mouse":
        prefixes = ("TAG Silence of the Mouse:",)
    elif marker_key == "wizards_luck":
        prefixes = (TAG_WIZARDS_LUCK_MARKER,)
    elif marker_key == "look_tough":
        prefixes = (TAG_LOOK_TOUGH_MARKER,)
    elif marker_key == "speedy_recovery":
        prefixes = ("TAG Speedy Recovery settlement healing 2/day",)
    else:
        prefixes = (marker,)
    removed: list[str] = []
    kept: list[str] = []
    for status in character.statuses:
        if any(status.startswith(prefix) for prefix in prefixes):
            removed.append(status)
        else:
            kept.append(status)
    character.statuses = kept
    return removed


def consume_tag_guild_marker(campaign: CampaignState, character: Character, *, marker_key: str) -> TagDowntimeLogEntry:
    marker = TAG_GUILD_MARKERS.get(marker_key, marker_key)
    removed = _remove_tag_guild_markers(character, marker_key, marker)
    if removed:
        if marker_key == "look_tough" and character.id in campaign.tag_look_tough_character_ids:
            campaign.tag_look_tough_character_ids.remove(character.id)
        result = f"{character.name} clears TAG Guild marker: {', '.join(removed)}."
    else:
        result = f"{character.name} does not currently have TAG Guild marker: {marker}."
    character.updated_at = now_utc()
    return append_tag_log(campaign, action="guild_marker_clear", character=character, result_text=result)


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
        "guild_loot_share",
        "guild_resurrection_fund",
        "guild_availability_reroll_reset",
    } else "loan_enforcement"
    if action == "bank_deposit":
        if character is None:
            return append_tag_log(campaign, action="bank_deposit", result_text="Choose a character for TAG bank deposit.")
        guild_ledger_active = tag_guild_benefits_active(campaign)
        fee = 0 if guild_ledger_active else (ceil(amount * 0.1) if amount else 0)
        total_cost = amount + fee
        ledger_label = "TAG Guild ledger account" if guild_ledger_active else "TAG bank account"
        if amount <= 0:
            result = "Enter a bank deposit amount above 0 gp."
        elif character.gold < total_cost:
            result = f"{character.name} needs {total_cost} gp for a {amount} gp {ledger_label} deposit plus {fee} gp fee."
        else:
            account = _tag_bank_account(campaign, character)
            character.gold -= total_cost
            account.gold_gp += amount
            account.notes = clean_note or account.notes
            character.updated_at = now_utc()
            fee_text = "for free under the TAG Guild ledger rule" if guild_ledger_active else f"and pays {fee} gp fee"
            result = f"{character.name} deposits {amount} gp into a {ledger_label} {fee_text}. Account balance {account.gold_gp} gp."
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
        account = _tag_bank_account(campaign, character) if character is not None else None
        if robbed and account is not None:
            account.robbed = True
        result = (
            f"Bank/hidden-storage robbery risk {total} ({'+'.join(str(roll) for roll in rolls)}): "
            + (
                "robbery or theft occurs; selected TAG bank account is marked robbed and recovery can create the Bandit Hideout lead."
                if robbed and account is not None
                else "robbery or theft occurs; use recovery action if pursuing it."
                if robbed
                else "storage remains safe."
            )
        )
        return append_tag_log(campaign, action="bank_robbery_risk", character=character, roll=total, total=total, result_text=result)
    if action == "robbery_recovery":
        cost_clues = 3
        if character is not None and character.clues >= cost_clues:
            character.clues -= cost_clues
            account = _tag_bank_account(campaign, character)
            account.robbed = False
            character.updated_at = now_utc()
            result = f"{character.name} spends 3 Clues to learn who stole TAG bank funds. Play the Bandit Hideout lead and recover the stolen money as Final Boss treasure."
            resolve_tag_closeout_task(campaign, task_action="bank_robbery_recovery", log_missing=False)
        else:
            result = "Bank robbery recovery requires 3 Clues on a chosen character, then the Bandit Hideout lead."
        return append_tag_log(campaign, action="bank_robbery_recovery", character=character, result_text=result)
    if action == "guild_upkeep":
        upkeep = ceil(max(0, campaign.tag_guild_coffers_gp) * 0.1)
        paid = min(upkeep, campaign.tag_guild_coffers_gp)
        campaign.tag_guild_coffers_gp -= paid
        campaign.tag_guild_availability_reroll_used = False
        result = f"Guild upkeep charged 10%: {paid} gp paid from coffers. Coffers now {campaign.tag_guild_coffers_gp} gp."
        if campaign.tag_guild_coffers_gp <= 0:
            result += " Guild benefits are suspended until coffers are restored."
        else:
            result += " Guild availability reroll reset for the next adventure/month window."
        resolve_tag_closeout_task(campaign, task_action="guild_upkeep", log_missing=False)
        resolve_tag_closeout_task(campaign, task_action="guild_availability_reroll_reset", log_missing=False)
        return append_tag_log(campaign, action="guild_upkeep", character=character, cost_gp=paid, result_text=result)
    if action == "guild_loot_share":
        if not campaign.tag_guild_member:
            result = "Guild loot share skipped: the troupe is not marked as Adventurers Guild members."
        elif amount <= 0:
            result = "Enter the total monetary loot above 0 gp before applying the Guild 50% share."
        else:
            share = amount // 2
            party_keeps = amount - share
            campaign.tag_guild_coffers_gp += share
            result = (
                f"Guild 50% monetary loot share recorded: {share} gp to Guild coffers, "
                f"{party_keeps} gp remains for the party. Coffers now {campaign.tag_guild_coffers_gp} gp."
            )
            resolve_tag_closeout_task(campaign, task_action="guild_loot_share", log_missing=False)
        return append_tag_log(campaign, action="guild_loot_share", character=character, cost_gp=amount, result_text=result)
    if action == "guild_resurrection_fund":
        if character is None:
            result = "Choose the character receiving Guild resurrection funding."
        elif not tag_guild_benefits_active(campaign):
            result = "Guild resurrection funding unavailable: Guild benefits are inactive or coffers are empty."
        elif character.level < 2:
            result = f"{character.name} is Level {character.level}; Guild resurrection funding is for Level 2+ members."
        elif amount <= 0:
            result = "Enter the resurrection attempt cost paid from Guild coffers."
        else:
            paid = min(amount, campaign.tag_guild_coffers_gp)
            campaign.tag_guild_coffers_gp -= paid
            result = (
                f"Guild pays {paid} gp toward {character.name}'s resurrection attempt. "
                f"Coffers now {campaign.tag_guild_coffers_gp} gp."
            )
            if paid < amount:
                result += f" Shortfall {amount - paid} gp remains."
            if campaign.tag_guild_coffers_gp <= 0:
                result += " Guild benefits are suspended until coffers are restored."
        return append_tag_log(campaign, action="guild_resurrection_fund", character=character, cost_gp=amount, result_text=result)
    if action == "guild_availability_reroll_reset":
        return reset_guild_availability_reroll(campaign)
    entry = roll_moneylender_follow_chance(campaign, debt_gp=amount)
    entry.action = "loan_enforcement"
    if clean_note:
        entry.result_text += f" Note: {clean_note}."
    return entry


def follow_treasure_map(campaign: CampaignState, *, use_guild_cartographer: bool = False) -> TagDowntimeLogEntry:
    roll = roll_d6()
    bonus = campaign.tag_map_bonus + (1 if use_guild_cartographer and tag_guild_benefits_active(campaign) else 0)
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


def _tag_prompt_action(
    label: str,
    tooltip: str,
    *,
    action_type: str = "dialog",
    action_value: str = "",
    reference: str = "",
    amount: int = 0,
) -> dict[str, object]:
    return {
        "label": label,
        "tooltip": tooltip,
        "action_type": action_type,
        "action_value": action_value,
        "reference": reference,
        "amount": max(0, int(amount or 0)),
    }


def _tag_lead_how_to(lead_type: str) -> str:
    lead_labels = {
        "rumor": "Rumor leads begin as settlement talk. Use the entry room to record the party's approach, then let the side clue and complication rooms capture which branch the players chose.",
        "treasure_map": "Treasure Map leads are about uncertainty before payoff. Use the prompt buttons to log follow-map rolls, false trails, destination procedures, and reward/XP signoff.",
        "thematic_dungeon": "Thematic Dungeons change ordinary dungeon expectations. Use the room prompts to record replacement rolls, special procedures, and final-route decisions.",
        "guild_job": "Guild Jobs are obligations as much as adventures. Use the prompts to record job conditions, capture-alive choices, Guild payment consequences, and closeout checks.",
    }
    return lead_labels.get(lead_type, "Use room prompts to record the branch, reward, route, XP, and closeout decisions that the app cannot infer from movement alone.")


def _tag_scene_mood(lead_type: str, profile: dict[str, object], lead_detail: str) -> str:
    title = str(profile.get("title") or lead_detail)
    scene = str(profile.get("scene") or "")
    if lead_type == "treasure_map":
        return (
            "The map is creased, greasy at the folds, and just convincing enough to be dangerous. "
            "Every landmark feels like a promise made by someone who expected another fool to do the walking."
        )
    if lead_type == "guild_job":
        return (
            "The Guild seal makes the work official, but not comfortable. "
            "Someone wants this handled cleanly, and the payment will only matter if the party survives the fine print."
        )
    if lead_type == "thematic_dungeon":
        return (
            f"The place carries the mood of {title}: wrong sounds behind stone, stale air, and evidence that ordinary dungeon habits may betray the party."
        )
    return (
        f"The rumor has teeth now. {scene or title} has left enough tracks to follow, enough contradictions to worry over, and enough danger to make the settlement suddenly feel far away."
    )


TAG_RUMOR_AUDIT_GUIDANCE: dict[int, dict[str, str]] = {
    1: {
        "focus": "Choice-heavy lead: make the object feel tempting, wrong, and politically awkward before the player chooses how far to push Bofto's family.",
        "entry": "Start in the settlement with gossip that does not quite agree: a prize find, a changed farmer, and neighbours who are suddenly careful with their words.",
        "complication": "Pause before violence. The important state is whether the party steals, questions, leaves, or forces the issue.",
        "finale": "Close by recording the exact choice and any cursed-object follow-up before another adventure buries the consequence.",
    },
    2: {
        "focus": "Two-sided monster lead: make the assassins and Xasartha feel like competing dangers rather than a simple bounty notice.",
        "entry": "Frame the cabin as a place people avoid in daylight; the story should feel hunted before the medusa appears.",
        "complication": "Resolve the assassins' approach, ambush, or parley first so the final scene is not just an isolated fight.",
        "finale": "Record stealth, reaction, pendant, and any gaze consequences before awarding the lead.",
    },
    3: {
        "focus": "Red-herring lead: give the players enough texture that the disappointment still feels like a played scene.",
        "entry": "Let the old farm look plausible: old tracks, over-told local claims, and someone who insists the sword was seen recently.",
        "complication": "The audit point is the ambush/red-herring resolution, not finding a sword.",
        "finale": "Sign off days, ambush, and no-sword outcome so the rumor is crossed off cleanly.",
    },
    4: {
        "focus": "Creature-feature lead: the bridge should feel wet, hungry, and watched before the mutant fish rule calls matter.",
        "entry": "Use spoiled nets, missing livestock, and villagers who avoid the water to give the fight a reason to exist.",
        "complication": "Track hypnosis, food/ration handling, and any minor encounter count that affects XP.",
        "finale": "Close by confirming rations, reward, and XP markers rather than just clearing the final room.",
    },
    5: {
        "focus": "Suspicion lead: the dragon is hidden in town life, so the procedure should reward investigation before confrontation.",
        "entry": "Make the clues domestic and unsettling: heat where it should be cold, missing wealth, and witnesses who change their story.",
        "complication": "Use the reveal action before the final route; the lead is about proving what is underneath the disguise.",
        "finale": "Record reveal, route, treasure, and any fallout from exposing a disguised dragon.",
    },
    6: {
        "focus": "Trickster lead: Blackbird Hill should feel like a bargain with smiling terms and sharp hooks.",
        "entry": "Present the leprechauns as charming first, inconvenient second, and dangerous only when the players push the wrong angle.",
        "complication": "Track shoes, illusion spell, and peaceful/hostile route separately.",
        "finale": "Sign off whether the lead ended as trade, trick, or fight before applying reward text.",
    },
    7: {
        "focus": "Hidden-temple lead: turn the town clue into a small expedition with a clear seven-room target.",
        "entry": "Make the stair feel deliberately hidden: dust, old repairs, and locals who pretend not to know why the place is avoided.",
        "complication": "Watch target-room and route state because the generated dungeon is standing in for a specific temple procedure.",
        "finale": "Before closing, check final route, temple reward, XP, and any unresolved route rewrites.",
    },
    8: {
        "focus": "Cult lead: Shaura works best when the party feels pressure from recruitment, secrecy, and the 2-Clue gate.",
        "entry": "Seed whispered devotion, missing townsfolk, and the feeling that the cult is already inside ordinary life.",
        "complication": "Make the Clue spend explicit; if the party lacks Clues, record the blocked route instead of silently skipping it.",
        "finale": "Confirm cultist groups, Shaura reward, route, and ten-room target signoff.",
    },
    9: {
        "focus": "Clue-gated rescue lead: Daroc's familiar is small stakes emotionally, but the Clue cost is the mechanical hinge.",
        "entry": "Let the missing familiar leave traces that matter: scratches, alley witnesses, and people trying to profit from Daroc's worry.",
        "complication": "Record whether cat/beast help reduced the Clue burden before spending anything.",
        "finale": "Apply Daroc's reward and XP only after the Clue route is settled.",
    },
    10: {
        "focus": "Rooftop threat lead: the white gargoyles should feel like a public emergency with variable count and surprise pressure.",
        "entry": "Open with dusk, roof tiles, frightened guards, and townspeople arguing over how many shapes they saw.",
        "complication": "Roll count and surprise before the fight is treated as ordinary combat.",
        "finale": "Record stone-skin checks and bounty head count before banking the reward.",
    },
    11: {
        "focus": "Training lead: make the player decide whether the cost and XP-roll opportunity are worth the interruption.",
        "entry": "Deoldyn's range should feel precise and expensive: split shafts, measured criticism, and no patience for vague promises.",
        "complication": "The payment and qualifying character matter more than the proxy encounter.",
        "finale": "Sign off training payment, eligible XP roll, and who actually trained.",
    },
    12: {
        "focus": "Solo-sword lead: Agaratha needs a clear restriction note before the generated module becomes normal party play.",
        "entry": "Let Shinta's request feel personal and risky before it becomes a bandit hideout problem.",
        "complication": "Record whether the table is enforcing the solo restriction or deliberately treating this as a party handoff.",
        "finale": "Apply Agaratha only after route, solo note, and sword consequence are logged.",
    },
}


def _tag_rumor_number_from_profile(profile: dict[str, object]) -> int | None:
    title = str(profile.get("title") or "")
    for number, rumor in TAG_RUMORS.items():
        if title and title.lower() in rumor.lower():
            return number
        if title and title == str(TAG_RUMOR_PROFILES.get(number, {}).get("title") or ""):
            return number
    return None


def _tag_enrich_rumor_profile(profile: dict[str, object], lead_detail: str) -> dict[str, object]:
    rumor_number = _tag_rumor_number_from_profile(profile)
    if not rumor_number:
        return profile
    guidance = TAG_RUMOR_AUDIT_GUIDANCE.get(rumor_number, {})
    title = str(profile.get("title") or lead_detail)
    signoff_checks = [
        "Confirm the printed scene/result was checked before accepting any generated-room shortcut.",
        "Record the chosen route, blocked route, Clue spend, or social result in TAG Actions.",
        "Review reward, XP, Guild/finance, and closeout tasks before starting the next lead.",
    ]
    module_profile = dict(profile.get("module_profile") or {})
    module_signoff = list(module_profile.get("signoff_checks") or [])
    module_profile["signoff_checks"] = [*module_signoff, *[item for item in signoff_checks if item not in module_signoff]]
    module_procedure = list(module_profile.get("procedure") or [])
    module_profile["procedure"] = [
        *module_procedure,
        f"Rumor audit focus: {guidance.get('focus') or f'Play {title} as a settlement lead with explicit route and reward signoff.'}",
    ]
    return {
        **profile,
        "rumor_number": rumor_number,
        "audit_family": "rumor_playthrough",
        "playthrough_focus": guidance.get("focus", f"Audit {title} as a settlement rumor handoff with visible route, reward, and XP signoff."),
        "entry_guidance": guidance.get("entry", "Open with settlement evidence and a player-facing reason to follow this rumor now."),
        "side_guidance": "Use the side room as a clue, witness, or pressure beat; if it changes reward, Clues, or XP, record that before moving on.",
        "complication_guidance": guidance.get("complication", "Resolve the printed branch deliberately and log the player choice in TAG Actions."),
        "finale_guidance": guidance.get("finale", "Before closing the lead, verify final foe/procedure, reward, XP, and campaign closeout state."),
        "signoff_checks": signoff_checks,
        "module_profile": module_profile,
    }


TAG_TREASURE_MAP_AUDIT_GUIDANCE: dict[int, dict[str, str]] = {
    1: {
        "title": "Underground caves",
        "focus": "Classic treasure promise: make the map feel accurate enough to trust, then make the cave count and final Boss payoff matter.",
        "entry": "Open with cold air from a split in the earth, scraped stone, and a route that matches the map too well for comfort.",
        "side": "Use side clues as old camp marks, broken tools, or a half-buried waymarker that confirms the map is not a tavern fraud.",
        "complication": "Roll the cave room count before the party settles into ordinary exploration; the deadline changes how much they risk before the Boss room.",
        "finale": "Close with the boosted Boss and treasure signoff: room count, dead-ended passages, maximum treasure, XP, and any storage/banking choice.",
    },
    2: {
        "title": "Forgotten temple",
        "focus": "Dangerous relic hunt: make the temple feel holy, abandoned, and occupied by people who know exactly what the idol is worth.",
        "entry": "The map points to moss-choked stone, a cracked lintel, and old offerings gone black with weather.",
        "side": "Use side clues to foreshadow the cultists' discipline, the idol's value, or why withdrawal will not be simple once blades are drawn.",
        "complication": "Resolve cult ability/leader scroll checks deliberately so the fight does not become a generic temple brawl.",
        "finale": "Sign off idol value, leader scroll chance, cultist treasure, XP, and how the heavy prize is carried or stored.",
    },
    3: {
        "title": "Hostile humanoid camp",
        "focus": "Choice lead: the map reveals a camp, but the important decision is report, steal, or fight.",
        "entry": "Let the party see smoke between trees, patrol paths, and loot stacked carelessly enough to invite bad decisions.",
        "side": "Use side clues to show camp strength and give the players a fair reason to report it instead of rushing the tents.",
        "complication": "Record report/stealth/fight before rolling camp forces; this lead is about the chosen approach.",
        "finale": "Close with report reward or theft/fight consequences, delayed reinforcements, loot, XP, and any unresolved camp threat.",
    },
    4: {
        "title": "Underground structure",
        "focus": "Treasure escrow lead: the party can see wealth accumulating, but the final Boss holds the purse until the end.",
        "entry": "The map ends at worked stone under wild ground: squared blocks, stale dust, and a silence that feels built rather than natural.",
        "side": "Use side clues as tally marks for treasure already found but not yet claimable.",
        "complication": "Track every treasure result as deferred state; the map destination changes accounting as much as monsters.",
        "finale": "Move the running treasure total to the final Boss, then sign off XP, storage, Guild share, and banking.",
    },
    5: {
        "title": "Boss-only underground structure",
        "focus": "Escalated treasure escrow: every monster result is serious, and the final reward floor must be checked.",
        "entry": "The mapped entrance feels deliberately sealed, as if every room beyond it was built to hold one dangerous guardian.",
        "side": "Use side clues to remind the player that ordinary vermin/minion habits do not apply here.",
        "complication": "Convert monster results before resolving rooms and keep treasure deferred for the final Boss.",
        "finale": "Confirm boss-only conversion, final treasure minimum, magic-item minimum, XP, Guild share, and storage/banking closeout.",
    },
    6: {
        "title": "Lich sepulchral chamber",
        "focus": "One-room high-risk lead: make the entrance feel like a bad bargain before the death-magic save is rolled.",
        "entry": "The map does not lead to a dungeon so much as a sealed answer: stone dust, cold script, and a door no one local admits exists.",
        "side": "Use side clues to warn that the chamber is short, lethal, and decided by preparation rather than exploration depth.",
        "complication": "Resolve entry death magic and lich Life calculation before the final fight starts.",
        "finale": "Sign off Life loss, lich Life, phylactery attempts, skeleton defenders, treasure, XP, and any follow-up map/scroll reward.",
    },
}


def _tag_enrich_treasure_map_profile(profile: dict[str, object], lead_detail: str) -> dict[str, object]:
    map_roll = max(1, min(6, int(profile.get("map_roll") or 1)))
    guidance = TAG_TREASURE_MAP_AUDIT_GUIDANCE.get(map_roll, TAG_TREASURE_MAP_AUDIT_GUIDANCE[1])
    signoff_checks = [
        "Confirm the Follow Treasure Map result and destination number were checked before using the generated module.",
        "Record destination procedure rolls, deferred treasure, report/stealth choices, or death-magic setup in TAG Actions.",
        "Review reward, XP, Guild share, banking/storage, and closeout tasks before creating another map lead.",
    ]
    module_profile = dict(profile.get("module_profile") or {})
    module_signoff = list(module_profile.get("signoff_checks") or [])
    module_profile["signoff_checks"] = [*module_signoff, *[item for item in signoff_checks if item not in module_signoff]]
    module_procedure = list(module_profile.get("procedure") or [])
    module_profile["procedure"] = [
        *module_procedure,
        f"Treasure Map audit focus: {guidance['focus']}",
    ]
    return {
        **profile,
        "title": profile.get("title") or guidance["title"],
        "audit_family": "treasure_map_playthrough",
        "treasure_map_destination": map_roll,
        "playthrough_focus": guidance["focus"],
        "entry_guidance": guidance["entry"],
        "side_guidance": guidance["side"],
        "complication_guidance": guidance["complication"],
        "finale_guidance": guidance["finale"],
        "lead_result_label": "printed treasure-map destination",
        "signoff_checks": signoff_checks,
        "module_profile": module_profile,
    }


TAG_THEMATIC_DUNGEON_AUDIT_GUIDANCE: dict[int, dict[str, str]] = {
    1: {
        "title": "Ghastly Mine",
        "focus": "Attrition and collapse lead: the mine should feel unstable before the undead tables and cave-in count start changing decisions.",
        "entry": "Open with rotten timbers, breath-thin air, and pick marks that vanish under old grave dust. The party is not just entering a mine; they are stepping into a place that wants to close behind them.",
        "side": "Use side clues as warning signs: splintered supports, cold veins in the rock, old miners' marks, or gold dust that may become something stranger when checked.",
        "complication": "Make every replacement roll and cave-in count visible. The danger is cumulative, so log undead replacements, treasure conversion, and prior cave-ins before the next room blurs the record.",
        "finale": "Close with the mine's debts paid: final undead, cave-in severity, trapped or fallen characters, gp-to-gem/nugget conversion, XP, storage, and closeout.",
    },
    2: {
        "title": "Giant's Lair",
        "focus": "Scale and deadline lead: ordinary dungeon habits should feel too small for the halls, furniture, and final-room requirements.",
        "entry": "Let the party feel the lair's size immediately: gouged doorframes, huge bowls used as troughs, and a ceiling that makes torches look timid.",
        "side": "Use side clues to confirm they are in a giant's territory before the final room arrives: oversized tracks, thrown stones, or bones cracked like kindling.",
        "complication": "Track the HCL+5 endpoint and final-room shape. The giant finale is a room-design constraint as much as a monster encounter.",
        "finale": "Sign off the large final room, boulder throw, spell modifier, three treasure rolls, doubled gp, XP, Guild share, and storage.",
    },
    3: {
        "title": "Dragon's Lair",
        "focus": "Compressed reveal lead: four rooms means every clue should build pressure toward the dragon type choice.",
        "entry": "Start with heat in the stone, claw scores at shoulder height, and old scales caught where something too large squeezed through.",
        "side": "Use side clues to tempt the 2-Clue reveal: scorch marks, darkness stains, grave-cold scratches, or hoard scraps that make the unknown dragon feel knowable.",
        "complication": "Make the Clue spend explicit before the final room. If the party will not or cannot pay, record that the reveal stayed hidden.",
        "finale": "Record dragon type, route, hoard/reward, XP, and any update to the generated finale before another lead overwrites the context.",
    },
    4: {
        "title": "Fiendish Abyss",
        "focus": "Escalation and prisoner lead: the dungeon is not just harder; it changes what the final boss means after the prisoner table is rolled.",
        "entry": "Open with sigils that look scratched from the other side, candle soot on the floor, and air that tastes like old iron.",
        "side": "Use side clues to remind players that ordinary foes may be raised in danger and that a prisoner or bargain may wait at the end.",
        "complication": "Track any Clue reveal, raised monster assumptions, and Abyss/Fiendish substitutions before the final boss.",
        "finale": "Roll the prisoner table after the final boss, then sign off rescue, reward, map/rumor follow-up, XP, Guild/finance, and closeout.",
    },
    5: {
        "title": "Minotaur Maze",
        "focus": "Navigation pressure lead: the map should feel unreliable and every backtrack/search should have a visible consequence.",
        "entry": "Open with passages that bend too soon, hoofprints crossing themselves, and scratches where someone counted turns until they stopped.",
        "side": "Use side clues as possible shortcuts, guide marks, or warnings that minotaur rules change Luck, charge pressure, and wandering danger.",
        "complication": "Log lost checks, wandering subtype, special events, and shortcut unlocks as they happen. Maze state is the adventure.",
        "finale": "Close with minotaur lord route, first-attack penalties, halfling Luck restriction, treasure, XP, and any unresolved shortcut or lost marker.",
    },
    6: {
        "title": "Bandit Hideout",
        "focus": "Loot and capture lead: room-by-room stolen goods and the chieftain alive/dead choice should drive the audit.",
        "entry": "Start with boot tracks, wagon splinters, and a guard fire burning low enough to prove the hideout was used recently.",
        "side": "Use side clues to show stolen goods, trapdoor risks, and whether the party wants proof, loot, or a living chieftain.",
        "complication": "Roll stolen-goods checks room by room and record trapdoor results. The hideout's value is discovered before the final den.",
        "finale": "Decide kill/capture before reward handling, then sign off bounty/free rumor, random magic item, 8d6 gp, XP, Guild share, and storage.",
    },
}


def _tag_thematic_number_from_profile(profile: dict[str, object]) -> int | None:
    title = str(profile.get("title") or "")
    for number, name in TAG_THEMATIC_DUNGEONS.items():
        if title == name:
            return number
    return None


def _tag_enrich_thematic_profile(profile: dict[str, object], lead_detail: str) -> dict[str, object]:
    theme_number = _tag_thematic_number_from_profile(profile)
    if not theme_number:
        return profile
    guidance = TAG_THEMATIC_DUNGEON_AUDIT_GUIDANCE.get(theme_number, TAG_THEMATIC_DUNGEON_AUDIT_GUIDANCE[1])
    signoff_checks = [
        "Confirm the Thematic Dungeon result and target-room procedure before treating the generated module like a normal dungeon.",
        "Record theme-specific procedure rolls, route changes, Clue spends, replacement checks, or treasure handling in TAG Actions.",
        "Review final reward, XP, Guild share, banking/storage, and closeout tasks before creating another lead.",
    ]
    module_profile = dict(profile.get("module_profile") or {})
    module_signoff = list(module_profile.get("signoff_checks") or [])
    module_profile["signoff_checks"] = [*module_signoff, *[item for item in signoff_checks if item not in module_signoff]]
    module_procedure = list(module_profile.get("procedure") or [])
    module_profile["procedure"] = [
        *module_procedure,
        f"Thematic Dungeon audit focus: {guidance['focus']}",
    ]
    return {
        **profile,
        "audit_family": "thematic_dungeon_playthrough",
        "thematic_dungeon_number": theme_number,
        "playthrough_focus": guidance["focus"],
        "entry_guidance": guidance["entry"],
        "side_guidance": guidance["side"],
        "complication_guidance": guidance["complication"],
        "finale_guidance": guidance["finale"],
        "lead_result_label": "printed thematic dungeon result",
        "signoff_checks": signoff_checks,
        "module_profile": module_profile,
    }


def _tag_prompt_action_from_profile(action: object) -> dict[str, object] | None:
    if not isinstance(action, dict) or not action.get("label"):
        return None
    return _tag_prompt_action(
        str(action.get("label") or "TAG action"),
        str(action.get("tooltip") or "Open TAG Actions with this generated-module prompt prefilled."),
        action_type=str(action.get("action_type") or "dialog"),
        action_value=str(action.get("action_value") or ""),
        reference=str(action.get("reference") or ""),
        amount=max(0, int(action.get("amount") or 0)),
    )


def _extend_prompt_actions(prompt: dict[str, object], actions: object) -> None:
    if not isinstance(actions, list):
        return
    prompt_actions = prompt.setdefault("actions", [])
    if not isinstance(prompt_actions, list):
        prompt["actions"] = []
        prompt_actions = prompt["actions"]
    for action in actions:
        clean = _tag_prompt_action_from_profile(action)
        if clean:
            prompt_actions.append(clean)


def _tag_finale_mode(profile: dict[str, object]) -> str:
    return str(profile.get("finale_mode") or "combat").strip().lower()


def _tag_profile_actions(profile: dict[str, object], key: str) -> list[dict[str, object]]:
    actions = profile.get(key)
    if not isinstance(actions, list):
        return []
    cleaned: list[dict[str, object]] = []
    for action in actions:
        clean = _tag_prompt_action_from_profile(action)
        if clean:
            cleaned.append(clean)
    return cleaned


def _tag_final_prompt_body(profile: dict[str, object], finale_guidance: str) -> str:
    mode = _tag_finale_mode(profile)
    instruction = str(profile.get("finale_instruction") or "").strip()
    rewards = str(profile.get("rewards") or "").strip()
    if mode in {"vendor", "service"}:
        return (
            f"{profile.get('final_description') or 'The final scene is a bargain, service, or purchase opportunity.'} "
            f"{instruction or 'Choose the purchase or service the party wants, pick the receiving character, and confirm payment before leaving.'} "
            f"{finale_guidance}".strip()
        )
    if mode in {"social", "choice", "procedure"}:
        return (
            f"{profile.get('final_description') or 'The final scene is resolved by a printed choice or procedure.'} "
            f"{instruction or 'Use the scene-specific buttons for the decision that is actually happening now.'} "
            f"{finale_guidance}".strip()
        )
    capture_actions = [
        action for action in _tag_profile_actions(profile, "final_prompt_actions")
        if "alive" in str(action.get("action_value", "")).lower() or "capture" in str(action.get("action_value", "")).lower()
    ]
    capture_text = ""
    if capture_actions:
        capture_text = "If this scene requires the foe alive, tick Subdual damage before Resolve Round, then use the capture/reward action shown here. "
    return (
        f"{profile.get('final_description') or 'Resolve the final foe or printed procedure.'} "
        f"{capture_text}"
        f"{instruction or 'Use the buttons shown here for this lead; review rewards, XP, Guild share, banking/storage, and closeout after the scene is resolved.'} "
        f"{finale_guidance} "
        f"{rewards}".strip()
    )


def _tag_final_prompt_title(profile: dict[str, object]) -> str:
    if profile.get("final_prompt_title"):
        return str(profile["final_prompt_title"])
    mode = _tag_finale_mode(profile)
    if mode == "vendor":
        return "Bargain choices"
    if mode == "service":
        return "Service choices"
    if mode in {"choice", "social"}:
        return "Scene choices"
    if mode == "procedure":
        return "Scene procedure"
    return str(profile.get("final_title") or "Final scene")


def _tag_room_prompts(*, title: str, lead_detail: str, profile: dict[str, object]) -> dict[str, object]:
    profile_title = str(profile.get("title") or lead_detail)
    base_ref = title or profile_title
    lead_type = str(profile.get("lead_type") or "")
    how_to = str(profile.get("how_to") or _tag_lead_how_to(lead_type))
    mood = str(profile.get("mood") or _tag_scene_mood(lead_type, profile, lead_detail))
    entry_guidance = str(profile.get("entry_guidance") or "")
    side_guidance = str(profile.get("side_guidance") or "")
    complication_guidance = str(profile.get("complication_guidance") or "")
    finale_guidance = str(profile.get("finale_guidance") or "")
    signoff_checks = list(profile.get("signoff_checks") or [])
    lead_result_label = str(profile.get("lead_result_label") or "printed rumor/result")
    clue_cost = max(0, int(profile.get("clue_gate_cost") or 0))
    clue_label = str(profile.get("clue_gate_label") or "Unlock Clue route")
    final_actions = _tag_profile_actions(profile, "final_prompt_actions")
    prompts: dict[str, object] = {
        "tag-lead-entry": {
            "title": "Lead entry choices",
            "body": (
                f"{mood} {how_to} {entry_guidance} "
                "This is the handoff from settlement rumor, job, map, or patron into a playable dungeon thread: decide why the party trusts the lead, what they risk by following it, and which printed approach or refusal should be recorded before the doors start closing behind them."
            ),
            "checklist": [
                f"Confirm which {lead_result_label} produced this module.",
                "Record the party's first approach or refusal in TAG Actions.",
                "Check whether a side scene or Clue route should be pursued before the complication.",
            ],
            "actions": [
                _tag_prompt_action("TAG Actions", "Open the full TAG Actions dialog without changing any values."),
                _tag_prompt_action(
                    "Record lead choice",
                    "Prefill a social/choice branch marker for this TAG lead.",
                    action_type="branch",
                    action_value="social_choice",
                    reference=f"{base_ref}: lead choice",
                ),
                _tag_prompt_action(
                    "Skip side scene",
                    "Prefill a route marker for choosing not to pursue the optional side clue.",
                    action_type="route",
                    action_value="skip_scene",
                    reference=f"{base_ref}: skipped side scene",
                ),
            ],
        },
        "tag-side-clue": {
            "title": "Side clue and reward",
            "body": (
                f"{profile.get('side') or 'The side path offers a useful clue, but it should feel like a choice rather than housekeeping.'} "
                f"{side_guidance} "
                "Treat this as the lead breathing at the edge of the map: a torn sign, nervous witness, half-hidden cache, or too-clean footprint that tells the players this job has teeth. Check the printed scene for reward, Clue, or XP handling before confirming an action."
            ),
            "checklist": [
                "Check whether the side clue changes Clues, reward, XP, or route options.",
                "Record any reward or skipped-scene decision before leaving the room.",
            ],
            "actions": [
                _tag_prompt_action(
                    "Claim printed reward",
                    "Prefill the printed reward action. Enter the exact gp/item amount from the TAG scene before applying.",
                    action_type="branch",
                    action_value="claim_reward",
                    reference=f"{base_ref}: side clue reward",
                ),
                _tag_prompt_action(
                    "Mark scene XP",
                    "Prefill a pending scene XP marker for end-of-adventure closeout.",
                    action_type="xp",
                    action_value="mark_scene_xp",
                    reference=f"{base_ref}: side clue XP",
                ),
            ],
        },
        "tag-complication": {
            "title": "Complication route",
            "body": (
                f"{profile.get('complication') or 'The lead tightens here: a bargain can sour, a shortcut can close, or a fight can turn the room into evidence.'} "
                f"{complication_guidance} "
                "If this room has no scene-specific button, no procedure is due here; keep moving and let the next scene surface the actual bargain, fight, Clue spend, reward, or route choice."
            ),
            "checklist": [
                "Resolve only the branch, Clue cost, or procedure that the current printed scene actually asks for.",
                "If no current-scene choice is due, move to the finale and make the scene-specific choice there.",
                "Use route markers for peaceful, hostile, blocked, skipped, or unlocked paths.",
            ],
            "actions": [
                _tag_prompt_action(
                    "Parley succeeds",
                    "Prefill the route marker for a successful parley or peaceful branch.",
                    action_type="route",
                    action_value="parley_success",
                    reference=f"{base_ref}: complication parley success",
                ),
                _tag_prompt_action(
                    "Parley fails",
                    "Prefill the route marker for a failed parley or hostile branch.",
                    action_type="route",
                    action_value="parley_failed",
                    reference=f"{base_ref}: complication parley failed",
                ),
                _tag_prompt_action(
                    clue_label,
                    "Prefill the Clue-gate route marker with the known profile cost where one is available.",
                    action_type="route",
                    action_value="clue_gate_unlocked",
                    reference=f"{base_ref}: {clue_label}",
                    amount=clue_cost,
                ),
                _tag_prompt_action(
                    "Clue route blocked",
                    "Prefill the blocked Clue-gate route marker when the party cannot or will not pay the printed cost.",
                    action_type="route",
                    action_value="clue_gate_blocked",
                    reference=f"{base_ref}: clue route blocked",
                    amount=clue_cost,
                ),
            ],
        },
        "tag-final-scene": {
            "title": _tag_final_prompt_title(profile),
            "body": _tag_final_prompt_body(profile, finale_guidance),
            "checklist": [
                "Resolve only the choice, purchase, combat, or procedure that this lead actually offers.",
                "Use the scene-specific action button for the receiving character, amount, route, XP, or reward.",
                "After the scene is resolved, review Guild, banking/storage, XP, and closeout tasks.",
                *signoff_checks,
            ],
            "actions": final_actions or [
                _tag_prompt_action(
                    "Final route",
                    "Prefill a final-route marker such as capture, kill, parley, escape, or solo restriction.",
                    action_type="route",
                    action_value="final_route",
                    reference=f"{base_ref}: final route",
                ),
                _tag_prompt_action(
                    "Apply reward",
                    "Prefill the printed reward action. Enter the exact gp/item amount from the TAG scene before applying.",
                    action_type="branch",
                    action_value="claim_reward",
                    reference=f"{base_ref}: final reward",
                ),
                _tag_prompt_action(
                    "Mark final XP",
                    "Prefill a TAG XP marker for completing the final generated scene.",
                    action_type="xp",
                    action_value="mark_scene_xp",
                    reference=f"{base_ref}: final XP",
                ),
            ],
        },
        "tag-unlocked-scene": {
            "title": "Unlocked scene",
            "body": "This room was inserted by a TAG route rewrite. Treat it like a door the story only opens because of an earlier choice: the party paid a clue cost, spared someone, followed a dangerous hint, or refused the obvious road. Record arrival, reward, and XP against the printed branch.",
            "checklist": [
                "Confirm which earlier route unlocked this scene.",
                "Record arrival, reward, XP, and any closeout note before moving on.",
            ],
            "actions": [
                _tag_prompt_action(
                    "Mark unlocked scene",
                    "Prefill the route marker showing the unlocked scene has been reached.",
                    action_type="route",
                    action_value="unlock_scene",
                    reference=f"{base_ref}: unlocked scene",
                ),
                _tag_prompt_action(
                    "Claim unlocked reward",
                    "Prefill the printed reward action for the unlocked branch.",
                    action_type="branch",
                    action_value="claim_reward",
                    reference=f"{base_ref}: unlocked reward",
                ),
            ],
        },
    }
    _extend_prompt_actions(prompts["tag-complication"], profile.get("complication_prompt_actions"))
    return prompts


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
    profile = {**profile, "lead_type": lead_type}
    if lead_type == "rumor":
        profile = _tag_enrich_rumor_profile(profile, lead_detail)
    if lead_type == "treasure_map":
        profile = _tag_enrich_treasure_map_profile(profile, lead_detail)
    if lead_type == "thematic_dungeon":
        profile = _tag_enrich_thematic_profile(profile, lead_detail)
    profile = _apply_tag_narrative_override(profile, lead_type=lead_type, label=title, lead_detail=lead_detail)
    title = str(profile.get("module_title") or title)
    objective = str(profile.get("objective") or objective)
    final_room_title = str(profile.get("final_title") or final_room_title)
    final_room_description = str(profile.get("final_description") or final_room_description)
    finale_mode = _tag_finale_mode(profile)
    noncombat_finale = finale_mode in {"vendor", "service", "social", "choice", "procedure"} and not profile.get("final_foe")
    final_foe = "" if noncombat_finale else str(profile.get("final_foe") or "Wraith")
    final_count = 0 if noncombat_finale else max(1, int(profile.get("final_count") or 1))
    final_extra_foes = [
        {"name": str(foe.get("name")), "count": max(1, int(foe.get("count", 1)))}
        for foe in profile.get("final_extra_foes", [])
        if isinstance(foe, dict) and foe.get("name")
    ]
    final_foes = ([] if noncombat_finale else [{"name": final_foe, "count": final_count}]) + final_extra_foes
    source_parameters = {
        "origin": "Tales from the Adventurers' Guild",
        "lead_type": lead_type,
        "lead_detail": lead_detail,
            "tag_reference": {
                "title": profile.get("title", lead_detail),
                "scene": profile.get("scene", ""),
                "pdf_pages": profile.get("pdf_pages", ""),
                "lead_type": lead_type,
                "lead_detail": lead_detail,
                "how_to": profile.get("how_to") or _tag_lead_how_to(lead_type),
                "mood": profile.get("mood") or _tag_scene_mood(lead_type, profile, lead_detail),
                "audit_family": profile.get("audit_family", ""),
                "rumor_number": profile.get("rumor_number", 0),
                "treasure_map_destination": profile.get("treasure_map_destination", 0),
                "thematic_dungeon_number": profile.get("thematic_dungeon_number", 0),
                "playthrough_focus": profile.get("playthrough_focus", ""),
                "signoff_checks": profile.get("signoff_checks", []),
            "rules": profile.get("rules", []),
            "rewards": profile.get("rewards", ""),
            "side_reward_note": profile.get("side_reward_note", ""),
            "final_reward_note": profile.get("final_reward_note", ""),
            "finale_mode": finale_mode,
            "finale_instruction": profile.get("finale_instruction", ""),
            "final_foe_proxy": final_foe,
            "final_foe_count": final_count,
            "final_foes": final_foes,
            "module_profile": profile.get("module_profile", {}),
            "room_prompts": _tag_room_prompts(title=title, lead_detail=lead_detail, profile=profile),
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
                "type": "room_reached",
                "room_id": "tag-final-scene",
            } if noncombat_finale else {
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
                "title": _room_title(profile, "tag-lead-entry", "Lead Trail"),
                "description": _room_description(profile, "tag-lead-entry", (
                    f"{profile.get('entry') or 'The party follows a TAG campaign lead out of the settlement.'} "
                    "The last warmth of the home settlement is behind them now: boot-mud, market smoke, and the contact's warning all narrow into one uneasy trail. "
                    "The main lead presses north, while a side clue lies east for players who want leverage before the trouble shows its teeth."
                )),
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
                "title": _room_title(profile, "tag-side-clue", "Side Clue"),
                "description": _room_description(profile, "tag-side-clue", (
                    f"{profile.get('side') or 'Discarded gear and frightened local gossip confirm that the lead is real.'} "
                    "This is not the heart of the job; it is the thing half-buried beside it. A torn strap, sour candle smoke, a nervous witness mark, or a cache tucked too neatly away can turn a blind advance into an informed risk."
                )),
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
                        "log": _room_log(profile, "tag-side-clue", f"TAG guidance: {profile.get('side_reward_note') or profile.get('rewards') or 'Record any printed reward from the source scene.'}"),
                        "treasure": {"gold": 12, "items": []},
                    }
                ],
            },
            {
                "id": "tag-complication",
                "tile_key": "13",
                "title": _room_title(profile, "tag-complication", "Complication"),
                "description": _room_description(profile, "tag-complication", (
                    f"{profile.get('complication') or 'Local troublemakers have reached the lead first.'} "
                    f"{profile.get('complication_guidance') or 'The pressure rises here, but no bookkeeping is needed unless this room presents a specific choice, roll, or procedure.'}"
                )),
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
                        "log": _room_log(profile, "tag-complication", f"TAG source {profile.get('pdf_pages') or 'page ?'}: {profile.get('complication') or 'Resolve the lead complication.'}"),
                    }
                ],
            },
            {
                "id": "tag-final-scene",
                "tile_key": "11",
                "title": _room_title(profile, "tag-final-scene", final_room_title),
                "description": _room_description(profile, "tag-final-scene", (
                    f"{final_room_description} "
                    "This is where the lead comes due: steel, spell, bargain, capture, or proof must turn into a recorded result before the party drags the story back to town."
                )),
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
                        "log": _room_log(profile, "tag-final-scene", str(profile.get("final_log") or profile.get("finale_instruction") or "Resolve the final scene choices shown in Current Objective and Adventures Guild Actions.")),
                        **({} if noncombat_finale else {"encounter": {"foes": final_foes}}),
                    }
                ],
            },
            {
                "id": "tag-return-road",
                "tile_key": "06",
                "title": _room_title(profile, "tag-return-road", "Return Road"),
                "description": _room_description(profile, "tag-return-road", "The road back to the settlement is quiet in the wrong way: every coin, clue, oath, injury, rumor, and Guild expectation from this lead now has to survive the journey home and the accounting that follows."),
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
            "victory_text": f"The party returns to the settlement with the TAG lead resolved. Review any scene choices, rewards, XP, Guild share, banking/storage, and closeout tasks before starting another lead.",
            "defeat_text": "The TAG lead remains unresolved in the settlement records.",
        },
    }


def _profile_title(profile: dict[str, object], fallback: str) -> str:
    return str(profile.get("title") or fallback)


def _profile_synopsis(campaign: CampaignState, lead_detail: str, profile: dict[str, object]) -> str:
    pages = profile.get("pdf_pages")
    page_text = f" Source: {pages}." if pages else ""
    return f"Generated from The Adventures Guild campaign downtime in {campaign.settlement_name}: {lead_detail}.{page_text}"


def _treasure_map_prompt_actions(map_roll: int) -> list[dict[str, object]]:
    if map_roll == 1:
        return [
            {
                "label": "Underground caves: room target",
                "tooltip": "Roll/log the d6+3 target-room count for Map Leads To 1. This is separate from Claim Treasure in the current room.",
                "action_type": "branch",
                "action_value": "map_cave_room_count",
                "reference": "Map Leads To 1 underground caves",
            },
        ]
    if map_roll == 2:
        return [
            {"label": "Idol value", "tooltip": "Prefill 1d3 x 100 gp golden idol value.", "action_type": "branch", "action_value": "map_temple_idol", "reference": "Map Leads To 2 golden idol"},
            {"label": "Leader scroll chance", "tooltip": "Prefill the chaos cult leader's 3-in-6 random scroll chance.", "action_type": "branch", "action_value": "map_temple_scroll", "reference": "Map Leads To 2 leader scroll"},
        ]
    if map_roll == 3:
        return [
            {"label": "Report reward", "tooltip": "Prefill 4d6 gp reward for reporting the hostile humanoid camp.", "action_type": "branch", "action_value": "map_humanoid_report", "reference": "Map Leads To 3 report to authorities"},
            {"label": "Camp stealth", "tooltip": "Prefill L4 worst-Stealth group check for stealing camp loot.", "action_type": "branch", "action_value": "map_humanoid_stealth", "reference": "Map Leads To 3 camp stealth"},
            {"label": "Camp forces", "tooltip": "Prefill hostile camp force rolls: orcs, bosses, black ogre chance.", "action_type": "branch", "action_value": "map_humanoid_forces", "reference": "Map Leads To 3 hostile camp forces"},
        ]
    if map_roll in {4, 5}:
        label = "Map Leads To 5 boss-only structure" if map_roll == 5 else "Map Leads To 4 underground structure"
        return [{"label": "Structure rooms", "tooltip": "Prefill 2d6 underground structure room count.", "action_type": "branch", "action_value": "map_structure_rooms", "reference": label}]
    return [
        {"label": "Death magic save", "tooltip": "Prefill one L7 death-magic entry Save for the lich chamber.", "action_type": "branch", "action_value": "map_lich_death_magic", "reference": "Map Leads To 6 death magic"},
        {"label": "Lich Life", "tooltip": "Prefill lich Life calculation from total party Life lost plus 4.", "action_type": "branch", "action_value": "map_lich_life", "reference": "Map Leads To 6 lich Life"},
        {"label": "Lich treasure", "tooltip": "Prefill 10d6 gp lich treasure and reminder for map/scroll rewards.", "action_type": "branch", "action_value": "map_lich_treasure", "reference": "Map Leads To 6 lich treasure"},
    ]


def _treasure_map_module_profile(map_roll: int) -> dict[str, object]:
    profiles = {
        1: {
            "target_rooms": "d6+3-room standard dungeon",
            "procedure": ["Do not roll content in the entrance room.", "After d6+3 rooms, unopened doors/passages become dead ends.", "Last room has a Boss with +2 Life and double maximum treasure."],
            "signoff_checks": ["Roll cave room count before play and check the finale Boss treasure boost."],
        },
        2: {
            "target_rooms": "forgotten wilderness temple",
            "procedure": ["No withdrawal from the chaos-cultist fight.", "Roll the Chaos Cult Table for cultist abilities.", "Leader is L4 Boss, 4 Life, 2 attacks, 3d6 gp, and 3-in-6 scroll chance."],
            "signoff_checks": ["Roll idol value and leader scroll chance after victory."],
        },
        3: {
            "target_rooms": "hostile humanoid camp",
            "procedure": ["Choose report-to-authorities for 4d6 gp and no XP, or try a daytime stealth theft.", "Stealth theft uses the worst modifier among entering characters against L4.", "On failure, entering characters are attacked with initiative; outside PCs join two turns later."],
            "signoff_checks": ["Choose report or stealth before rolling; if combat starts, roll camp forces."],
        },
        4: {
            "target_rooms": "2d6-room underground structure",
            "procedure": ["Roll content in the first room too.", "Track all generated treasure instead of taking it.", "Final Boss has all tracked treasure plus its own treasure."],
            "signoff_checks": ["Keep a running treasure total and move it to the final Boss."],
        },
        5: {
            "target_rooms": "2d6-room boss-only underground structure",
            "procedure": ["As Map Leads To 4, but every monster is a Boss.", "No Vermin/minions; reroll dragons.", "Final treasure has minimum 200 gp and 2 random magic items."],
            "signoff_checks": ["Confirm every monster result was converted to Boss and final treasure minimum was applied."],
        },
        6: {
            "target_rooms": "one-room lich sepulchral chamber",
            "procedure": ["All PCs Save vs L7 death magic or lose 1 Life.", "Lich Life equals total Life lost to death magic plus 4.", "Lich is defended by 7 dark skeletons; phylactery can be destroyed with a ranged attack vs L6."],
            "signoff_checks": ["Track entry Life loss, lich Life, phylactery attempts, and 10d6 gp plus map/scroll treasure."],
        },
    }
    return profiles.get(map_roll, profiles[1])


def _treasure_map_reward_notes(map_roll: int, destination_title: str) -> dict[str, str]:
    notes = {
        1: {
            "rewards": "Underground caves procedure: roll/log the d6+3 room target. In live play the app counts rooms, turns the target room into the Treasure Map final Boss room, dead-ends unopened exits there, and completes the objective when that Boss is defeated.",
            "side": "This side-room treasure is ordinary room treasure; use Claim Treasure if you want to collect it now. The map destination procedure is separate: for Underground caves, roll/log the d6+3 room target, then keep exploring while the app counts rooms and handles the target-room final Boss.",
            "final": "Underground caves closeout: after the app reaches the target room and the final Boss is defeated, review double maximum treasure handling, XP, Guild share, banking, and storage before claiming the Treasure Map quest reward.",
        },
        2: {
            "rewards": "Forgotten temple procedure: resolve the idol value, cult leader scroll chance, cultist treasure, XP, and how the heavy idol is carried or stored.",
            "side": "This side-room treasure is ordinary room treasure; use Claim Treasure if it exists. The map destination procedure is separate: for the Forgotten temple, record idol value and leader scroll chance when those printed steps become relevant.",
            "final": "Forgotten temple closeout: confirm idol value, leader scroll chance, cultist treasure, XP, Guild share, banking, and storage.",
        },
        3: {
            "rewards": "Hostile humanoid camp procedure: choose report, stealth theft, or fight before reward and XP handling.",
            "side": "This side-room treasure is ordinary room treasure; use Claim Treasure if it exists. The camp procedure is separate: record whether the party reports the camp, sneaks for loot, or fights it.",
            "final": "Hostile camp closeout: confirm report reward or theft/fight consequences, loot, reinforcements, XP, Guild share, banking, and storage.",
        },
        4: {
            "rewards": "Underground structure procedure: track generated treasure as deferred state and move it to the final Boss before closeout.",
            "side": "This side-room treasure is ordinary room treasure unless the destination procedure says to defer it. Use the structure prompts to record deferred treasure before final Boss handling.",
            "final": "Underground structure closeout: move deferred treasure to the final Boss, then confirm XP, Guild share, banking, and storage.",
        },
        5: {
            "rewards": "Boss-only underground structure procedure: convert all monster results to Boss encounters, defer treasure to the final Boss, and enforce final reward minimums.",
            "side": "This side-room treasure is ordinary room treasure unless the destination procedure says to defer it. Use the boss-only structure prompts to record monster conversion and deferred treasure.",
            "final": "Boss-only structure closeout: confirm Boss-only conversion, deferred treasure, final reward minimums, XP, Guild share, banking, and storage.",
        },
        6: {
            "rewards": "Lich chamber procedure: resolve entry death magic, lich Life, defenders, lich treasure, and any map/scroll follow-up before closeout.",
            "side": "This side-room treasure is ordinary room treasure; use Claim Treasure if it exists. The lich chamber procedure is separate: record death magic, lich Life, and lich treasure when the one-room destination is resolved.",
            "final": "Lich chamber closeout: confirm death-magic Life loss, lich Life, defenders, treasure, XP, Guild share, banking, storage, and any map/scroll follow-up.",
        },
    }
    return notes.get(map_roll, notes[1])


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
        title = f"The Adventures Guild {label}: {_profile_title(profile, TAG_RUMORS[rumor_number])}"
        objective = str(profile.get("objective") or f"Investigate TAG {label} from the settlement rumor list.")
        final_title = str(profile.get("final_title") or f"{label} Resolution")
        final_description = str(profile.get("final_description") or f"This room represents the playable handoff for {lead_detail}")
    elif clean_type == "treasure_map":
        map_roll = int(clean_detail) if clean_detail.isdigit() else roll_d6()
        map_roll = max(1, min(6, map_roll))
        label = f"Treasure Map {map_roll}"
        lead_detail = TAG_MAP_LEADS_TO[map_roll]
        guidance = TAG_TREASURE_MAP_AUDIT_GUIDANCE[map_roll]
        destination_title = guidance["title"]
        reward_notes = _treasure_map_reward_notes(map_roll, destination_title)
        profile = {
            "title": destination_title,
            "map_roll": map_roll,
            "pdf_pages": "TAG pp.32-33",
            "objective": f"Follow the purchased TAG treasure map to the {destination_title.lower()} and resolve its destination procedure.",
            "entry": guidance["entry"],
            "side": guidance["side"],
            "complication": guidance["complication"],
            "final_title": f"{destination_title} closeout",
            "final_description": guidance["finale"],
            "final_foe": "Wraith" if map_roll in {4, 5, 6} else "Goblins",
            "final_count": 1 if map_roll in {4, 5, 6} else 4,
            "rewards": reward_notes["rewards"],
            "side_reward_note": reward_notes["side"],
            "final_reward_note": reward_notes["final"],
            "module_profile": _treasure_map_module_profile(map_roll),
            "complication_prompt_actions": _treasure_map_prompt_actions(map_roll),
            "final_prompt_actions": _treasure_map_prompt_actions(map_roll),
            "rules": ["This generator uses The Map Leads To destinations, not the preliminary fake-map outcomes."],
        }
        title = f"The Adventures Guild Treasure Map {map_roll}: {destination_title}"
        objective = str(profile["objective"])
        final_title = str(profile["final_title"])
        final_description = str(profile["final_description"])
    elif clean_type == "thematic_dungeon":
        theme_roll = int(clean_detail) if clean_detail.isdigit() else roll_d6()
        theme_roll = max(1, min(6, theme_roll))
        lead_detail = TAG_THEMATIC_DUNGEONS[theme_roll]
        profile = TAG_THEMATIC_DUNGEON_PROFILES[theme_roll]
        label = lead_detail
        title = f"The Adventures Guild Thematic Dungeon: {_profile_title(profile, lead_detail)}"
        objective = str(profile.get("objective") or f"Resolve the TAG thematic dungeon lead: {lead_detail}.")
        final_title = str(profile.get("final_title") or lead_detail)
        final_description = str(profile.get("final_description") or f"This is the TAG adventure handoff for {lead_detail}.")
    else:
        label, lead_detail, profile = _guild_job_profile(campaign, clean_detail)
        player_label = label.replace("Guild Job", "Job")
        title = f"The Adventures Guild {player_label}: {_profile_title(profile, lead_detail)}"
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
    campaign, changed = ensure_worldbuilder_defaults(campaign, store)
    if changed:
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


def _session_party_gold(session: SessionState | None) -> int:
    if session is None:
        return 0
    return sum(max(0, int(member.gold)) for member in session.party)


def add_adventure_closeout_tasks(campaign: CampaignState, session: SessionState | None = None) -> list[TagCloseoutTaskState]:
    adventure_number = campaign.adventures_completed
    created: list[TagCloseoutTaskState] = []
    party_gold = _session_party_gold(session)
    if campaign.tag_guild_member:
        created_task = _add_closeout_task(
            campaign,
            adventure_number=adventure_number,
            category="guild",
            task_action="guild_loot_share",
            title="Apply Guild 50% monetary loot share",
            result_text=(
                "If this was a Guild adventure or the troupe is under Guild obligations, enter the total monetary loot on the Guild page "
                "and use Apply 50% Loot Share. The app records the Guild share in coffers and logs the party remainder."
            ),
            reference=f"TAG Guild closeout; current party carried gold estimate {party_gold} gp.",
        )
        if created_task is not None:
            created.append(created_task)
        created_task = _add_closeout_task(
            campaign,
            adventure_number=adventure_number,
            category="guild",
            task_action="guild_upkeep",
            title="Run Guild upkeep",
            result_text="Run Guild upkeep after the adventure/month window. This charges 10% of coffers, resets the availability reroll, and suspends benefits if coffers reach 0 gp.",
            reference="TAG p.68 Guild coffers and benefits.",
        )
        if created_task is not None:
            created.append(created_task)
        created_task = _add_closeout_task(
            campaign,
            adventure_number=adventure_number,
            category="guild",
            task_action="guild_leaving_restriction",
            title="Check Guild leaving restrictions",
            result_text="Before removing a member from the Guild, check whether the Guild coffers meet the printed requirement. This is a manual signoff task for now.",
            reference="TAG p.68 Guild membership restriction.",
        )
        if created_task is not None:
            created.append(created_task)
        if campaign.tag_guild_availability_reroll_used:
            created_task = _add_closeout_task(
                campaign,
                adventure_number=adventure_number,
                category="guild",
                task_action="guild_availability_reroll_reset",
                title="Reset Guild availability reroll",
                result_text="The Guild availability reroll was used. Run Guild upkeep or press Reset Reroll before the next adventure/month window.",
                reference="TAG p.68 Guild availability reroll.",
            )
            if created_task is not None:
                created.append(created_task)
    if any(not marker.applied for marker in campaign.tag_xp_markers):
        created_task = _add_closeout_task(
            campaign,
            adventure_number=adventure_number,
            category="xp",
            task_action="tag_xp_closeout",
            title="Resolve pending TAG XP markers",
            result_text="One or more TAG XP markers are still pending. Use TAG Actions or the printed scene text to award, roll, or dismiss them before starting the next adventure.",
            reference="TAG scene XP closeout.",
        )
        if created_task is not None:
            created.append(created_task)
    has_hidden_trove = campaign.tag_storage_gold_gp > 0 or any(item.storage == "trove" for item in campaign.tag_stored_items)
    if has_hidden_trove and not campaign.tag_hidden_trove_robbed:
        created_task = _add_closeout_task(
            campaign,
            adventure_number=adventure_number,
            category="storage",
            task_action="hidden_trove_risk",
            title="Roll hidden treasure trove risk",
            result_text="A hidden treasure trove has stored treasure. Roll the between-adventures trove risk on the Banking and Finance page.",
            reference="TAG p.11 Hidden Treasure Trove.",
        )
        if created_task is not None:
            created.append(created_task)
    if campaign.tag_hidden_trove_robbed:
        created_task = _add_closeout_task(
            campaign,
            adventure_number=adventure_number,
            category="storage",
            task_action="hidden_trove_recovery",
            title="Recover stolen hidden treasure trove",
            result_text="The hidden treasure trove is marked stolen. Choose a character with 4 Clues and use Recover Trove.",
            reference="TAG p.11 Hidden Treasure Trove recovery.",
        )
        if created_task is not None:
            created.append(created_task)
    if any(account.robbed for account in campaign.tag_bank_accounts):
        created_task = _add_closeout_task(
            campaign,
            adventure_number=adventure_number,
            category="finance",
            task_action="bank_robbery_recovery",
            title="Recover TAG bank robbery",
            result_text="A TAG bank account is marked robbed. Choose a character with 3 Clues and use Recover Bank Robbery to create the Bandit Hideout lead.",
            reference="TAG bank robbery recovery.",
        )
        if created_task is not None:
            created.append(created_task)
    if created:
        append_tag_log(
            campaign,
            action="adventure_closeout",
            result_text=f"TAG closeout created {len(created)} task(s) for adventure {adventure_number}.",
        )
    return created


def record_adventure_complete(store: Store, session: SessionState | None = None) -> CampaignState:
    campaign = load_campaign(store)
    campaign.adventures_completed += 1
    campaign.days_passed += 1
    party_name = None
    party_id = None
    if session is not None:
        party_id = session.party_id
        party = store.get("parties", session.party_id, Party.model_validate)
        party_name = party.name if party is not None else session.party_id
    append_campaign_chronicle(
        campaign,
        event_type="adventure_completed",
        title=f"Adventure {campaign.adventures_completed} completed",
        body=(
            f"{party_name or 'A party'} completed {session.adventure_id if session is not None else 'an adventure'}. "
            f"Review rewards, injuries, banking, storage, Guild obligations, and XP before the next start."
        ),
        party_id=party_id,
        party_name=party_name,
        reference="Adventure closeout app workflow.",
    )
    created = add_adventure_closeout_tasks(campaign, session)
    add_guidance_task(
        campaign,
        title=f"Review adventure {campaign.adventures_completed} closeout",
        body=(
            f"Adventure completion created {len(created)} specific closeout task(s). "
            "Review party rewards, fallen/injured members, TAG bank/storage, Guild finance, and XP markers before starting the next adventure."
        ),
        category="closeout",
        priority="required" if created else "recommended",
        reference="App closeout checklist.",
        rules_reference_id="adventure_closeout_workflow",
        affected_entity_type="party",
        affected_entity_id=party_id or "",
    )
    return save_campaign(store, campaign)


def record_tag_signoff_review(campaign: CampaignState, *, note: str = "") -> TagDowntimeLogEntry:
    open_closeout = [task for task in campaign.tag_closeout_tasks if not task.resolved]
    pending_xp = [marker for marker in campaign.tag_xp_markers if not marker.applied]
    latest_lead = next((item for item in reversed(campaign.tag_generated_adventure_ids) if item), "")
    latest_route = campaign.tag_adventure_routes[-1] if campaign.tag_adventure_routes else None
    if not open_closeout and not pending_xp:
        now = now_utc()
        for task in campaign.guidance_tasks:
            if task.status == "open" and task.category == "closeout" and "closeout" in task.title.lower():
                task.status = "completed"
                task.resolved_at = now
    summary = (
        f"TAG generated-adventure signoff reviewed"
        f"{f' for {latest_lead}' if latest_lead else ''}: "
        f"{len(open_closeout)} open closeout task(s), {len(pending_xp)} pending XP marker(s)"
        f"{f', latest route: {latest_route.result_text}' if latest_route is not None else ', no route marker recorded'}."
    )
    if note.strip():
        summary += f" Note: {note.strip()}"
    return append_tag_log(campaign, action="tag_signoff_review", result_text=summary)
