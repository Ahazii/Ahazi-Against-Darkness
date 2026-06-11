from __future__ import annotations

from dataclasses import dataclass

from ..schemas import EnemyState, PartyMemberState


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
    ),
    "deal_with_a_foe": SecretDefinition(
        "deal_with_a_foe",
        "Deal with a Foe",
        "One non-vermin, non-Final-Boss foe lets the party pass without treasure.",
        "Declare when the foe is encountered.",
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
    ),
    "true_name_spiritual_entity": SecretDefinition(
        "true_name_spiritual_entity",
        "True Name of a Spiritual Entity",
        "One angelic rescue/heal or demonic damage/kill effect.",
        "Record angel or demon choice when used.",
    ),
    "new_spell": SecretDefinition(
        "new_spell",
        "New Spell",
        "A spellcaster adds a spell from any list/table and gains one temporary slot for it.",
        "Choose the spell when applying the Secret.",
    ),
    "magical_power_increase": SecretDefinition(
        "magical_power_increase",
        "Increase of Magical or Spiritual Power",
        "A cleric or spellcaster gains one permanent use of a specific spell or prayer.",
        "Choose the spell/prayer when applying the Secret.",
    ),
    "scroll_location": SecretDefinition(
        "scroll_location",
        "Location of a Scroll",
        "Find a scroll, bark, or prism with a spell of choice.",
        "Add the chosen spell item when applying the Secret.",
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
        "Force one eligible morale roll to fail.",
        "Declare when foes must test morale.",
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
    ),
    "prisoner": SecretDefinition(
        "prisoner",
        "The Prisoner",
        "Rescue an important NPC from a Minion/Boss room for a major reward.",
        "Declare in a guarded room.",
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
        "Record for between-adventure upkeep.",
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


def is_dragon(enemy: EnemyState | None) -> bool:
    if enemy is None:
        return False
    tags = {tag.strip().lower() for tag in enemy.tags}
    return "dragon" in tags or "dragon" in enemy.name.strip().lower()


def secret_attack_bonus(member: PartyMemberState, enemy: EnemyState | None) -> int:
    if has_secret(member, "dragonslayer_bloodline") and is_dragon(enemy):
        return 1
    return 0


def secret_defense_bonus(member: PartyMemberState, enemy: EnemyState | None) -> int:
    if has_secret(member, "dragonslayer_bloodline") and is_dragon(enemy):
        return 1
    return 0
