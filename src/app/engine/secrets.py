from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState, SessionState


@dataclass(frozen=True)
class SecretDefinition:
    id: str
    label: str
    summary: str
    timing: str
    implementation: str = "recorded"


SECRETS: dict[str, SecretDefinition] = {
    "weakness_of_a_foe": SecretDefinition(
        "weakness_of_a_foe",
        "Weakness of a Foe",
        "+2 party Attack against one chosen Major Foe for one combat.",
        "Declare when the chosen Major Foe is met.",
        "wired",
    ),
    "deal_with_a_foe": SecretDefinition(
        "deal_with_a_foe",
        "Deal with a Foe",
        "One non-vermin, non-Final-Boss foe lets the party pass without treasure; the deal persists on that tile.",
        "Declare when the foe is encountered; invoke again when returning to the same tile.",
        "wired",
    ),
    "hidden_treasure_location": SecretDefinition(
        "hidden_treasure_location",
        "Location of a Hidden Treasure",
        "Reveal 3d6x10gp in a valid empty room.",
        "May be applied immediately in the current empty room.",
        "wired",
    ),
    "magic_item_location": SecretDefinition(
        "magic_item_location",
        "Location of a Magic Item",
        "Discover a magic item from an appropriate random magic item table.",
        "Use after entering a non-entrance room.",
        "wired",
    ),
    "true_name_spiritual_entity": SecretDefinition(
        "true_name_spiritual_entity",
        "True Name of a Spiritual Entity",
        "Angel: heal one PC to full or rescue one PC from a trapdoor. Demon: 4 Life to one Major Foe or slay up to 6 minions.",
        "Lock angel or demon on first use; one use per campaign.",
        "wired",
    ),
    "new_spell": SecretDefinition(
        "new_spell",
        "New Spell",
        "A spellcaster adds a spell from any list/table and gains one temporary slot for it.",
        "Choose the spell when applying the Secret.",
        "wired",
    ),
    "magical_power_increase": SecretDefinition(
        "magical_power_increase",
        "Increase of Magical or Spiritual Power",
        "A cleric or spellcaster gains one permanent use of a specific spell or prayer.",
        "Choose the spell/prayer when applying the Secret.",
        "wired",
    ),
    "scroll_location": SecretDefinition(
        "scroll_location",
        "Location of a Scroll",
        "Find a basic spell scroll; the scroll can be burned or copied by a wizard.",
        "Apply in a non-entrance room; automated basic-scroll support is wired.",
        "wired",
    ),
    "potion_recipe": SecretDefinition(
        "potion_recipe",
        "Recipe for a Potion",
        "After 2 Major Foes and 50gp components, unlock a 50gp healing potion before adventures.",
        "Reveal between fights once the prerequisites are met.",
        "wired",
    ),
    "terrifying_secret": SecretDefinition(
        "terrifying_secret",
        "Terrifying Secret",
        "Force the next morale roll to fail automatically.",
        "Declare in combat before a foe tests morale (not Final Bosses).",
        "wired",
    ),
    "big_money_buyer": SecretDefinition(
        "big_money_buyer",
        "Someone Will Pay Big Money for That",
        "One carried jewel, gem, or jewelry item sells for triple value.",
        "Apply after carrying a valuable item out.",
        "wired",
    ),
    "enemy_in_dungeon": SecretDefinition(
        "enemy_in_dungeon",
        "Your Enemy Is in the Dungeon",
        "Swap a Major Foe for a chaos lord and fight it at +1 Attack.",
        "Declare when a Major Foe is met.",
        "wired",
    ),
    "prisoner": SecretDefinition(
        "prisoner",
        "The Prisoner",
        "Break chains in a guarded room (Attack vs L4, +L rogue/barbarian), escort the NPC to the exit, then claim magic+treasure or double held gp.",
        "Auto-spotted in Minion/Boss rooms; reward when leaving the dungeon alive.",
        "wired",
    ),
    "dragonslayer_bloodline": SecretDefinition(
        "dragonslayer_bloodline",
        "Bloodline of Dragon-Slayers",
        "A barbarian or dwarf gains +1 Attack and Defense against dragons.",
        "Persistent character trait.",
        "wired",
    ),
    "secret_diet": SecretDefinition(
        "secret_diet",
        "Secret Diet",
        "Pay food costs before an adventure to gain 1 extra Life for that adventure.",
        "Use while camped outside; costs 100gp (50gp for halflings).",
        "wired",
    ),
    "someone_imprisoned": SecretDefinition(
        "someone_imprisoned",
        "Someone Has Been Imprisoned",
        "Spend 3 Clues when a hero is captive to locate their hideout.",
        "Spend when one or more heroes are held captive by foes.",
        "wired",
    ),
    "chaos_fanatics": SecretDefinition(
        "chaos_fanatics",
        "Chaos Fanatics",
        "Party Defense +1 against chaos fanatics for one encounter.",
        "Declare when chaos fanatics are met.",
        "wired",
    ),
    "corridor_leads": SecretDefinition(
        "corridor_leads",
        "I Know Where This Corridor Leads",
        "Reroll one room content table roll on the current tile; the reroll is final.",
        "Use in exploration before the tile is resolved.",
        "wired",
    ),
    "yummy_meal": SecretDefinition(
        "yummy_meal",
        "I Can Cook This, and It's Yummy",
        "Halfling cooks rare ingredients; party +1 vs Madness, fear, and disease saves until leaving the dungeon.",
        "Requires a halfling in the party; use while camped or in exploration.",
        "wired",
    ),
}

SPELLCASTER_CLASSES = {"wizard", "elf", "druid", "illusionist"}


def secret_options() -> list[SecretDefinition]:
    return list(SECRETS.values())


def secret_by_id(secret_id: str | None) -> SecretDefinition | None:
    key = (secret_id or "").strip().lower()
    return SECRETS.get(key)


def secret_label(secret_id: str) -> str:
    return SECRETS.get(secret_id, SecretDefinition(secret_id, secret_id.replace("_", " ").title(), "", "")).label


def member_secret_ids(member: PartyMemberState) -> set[str]:
    return {str(item).strip().lower().split(":", 1)[0] for item in member.secrets or []}


def has_secret(member: PartyMemberState, secret_id: str) -> bool:
    return secret_id.strip().lower() in member_secret_ids(member)


def record_secret(member: PartyMemberState, secret_id: str) -> bool:
    secret = secret_by_id(secret_id)
    if secret is None:
        return False
    if has_secret(member, secret.id):
        return False
    member.secrets.append(secret.id)
    return True


def consume_secret(member: PartyMemberState, secret_id: str) -> bool:
    normalized = secret_id.strip().lower()
    for index, item in enumerate(member.secrets or []):
        if str(item).strip().lower().split(":", 1)[0] == normalized:
            member.secrets.pop(index)
            return True
    return False


def is_dragon(enemy: EnemyState | None) -> bool:
    if enemy is None:
        return False
    tags = {tag.strip().lower() for tag in enemy.tags}
    return "dragon" in tags or "dragon" in enemy.name.strip().lower()


def is_chaos_fanatic(enemy: EnemyState | None) -> bool:
    if enemy is None:
        return False
    tags = {tag.strip().lower() for tag in enemy.tags}
    if "chaos" not in tags:
        return False
    name = enemy.name.strip().lower()
    return "fanatic" in name or "goatman" in name or "goatmen" in name


def secret_attack_bonus(member: PartyMemberState, enemy: EnemyState | None) -> int:
    if has_secret(member, "dragonslayer_bloodline") and is_dragon(enemy):
        return 1
    return 0


def secret_weakness_attack_bonus(session: SessionState | None, enemy: EnemyState | None) -> int:
    if session is None or enemy is None:
        return 0
    if session.secret_enemy_foe_id == enemy.id:
        return 1
    return 2 if session.secret_weakness_foe_id == enemy.id else 0


def secret_defense_bonus(
    member: PartyMemberState,
    enemy: EnemyState | None,
    session: SessionState | None = None,
) -> int:
    bonus = 0
    if has_secret(member, "dragonslayer_bloodline") and is_dragon(enemy):
        bonus += 1
    if session is not None and getattr(session, "secret_chaos_fanatics_active", False) and is_chaos_fanatic(enemy):
        bonus += 1
    return bonus


def secret_save_bonus(
    member: PartyMemberState,
    session: SessionState | None = None,
    *,
    save_label: str = "",
) -> int:
    from .expert_skill_effects import wears_arcane_garment

    bonus = 0
    if session is not None and getattr(session, "secret_yummy_meal_active", False):
        label = save_label.lower()
        if any(keyword in label for keyword in ("madness", "fear", "disease", "terror")):
            bonus += 1
    if wears_arcane_garment(member, dragon=True) and "breath" in save_label.lower():
        bonus += 1
    return bonus


def normalize_deal_foe_name(name: str) -> str:
    return name.strip().lower()


def deal_entry_matches_foe(entry_tile_id: str, entry_foe_name: str, tile_id: str, foe_name: str) -> bool:
    return entry_tile_id == tile_id and normalize_deal_foe_name(entry_foe_name) == normalize_deal_foe_name(foe_name)


TRUE_NAME_ALIGNMENT_PREFIX = "true_name_alignment:"


def true_name_alignment(member: PartyMemberState) -> str | None:
    for item in member.secrets or []:
        normalized = str(item).strip().lower()
        if normalized.startswith(TRUE_NAME_ALIGNMENT_PREFIX):
            value = normalized.split(":", 1)[1]
            if value in {"angel", "demon"}:
                return value
    return None


def set_true_name_alignment(member: PartyMemberState, alignment: str) -> None:
    normalized = alignment.strip().lower()
    if normalized not in {"angel", "demon"}:
        return
    tag = f"{TRUE_NAME_ALIGNMENT_PREFIX}{normalized}"
    secrets = [item for item in member.secrets or [] if not str(item).strip().lower().startswith(TRUE_NAME_ALIGNMENT_PREFIX)]
    secrets.append(tag)
    member.secrets = secrets


def true_name_mode_family(mode: str | None) -> str | None:
    normalized = (mode or "").strip().lower()
    if normalized.startswith("angel"):
        return "angel"
    if normalized.startswith("demon"):
        return "demon"
    return None
