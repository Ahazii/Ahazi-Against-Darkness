from __future__ import annotations

from typing import Any
from uuid import uuid4

from ..schemas import EnemyState
from .adventure_allowlists import MONSTER_TABLE_KEYS
from .cavern_features import template_surprise_tags
from .foe_weapon_restrictions import template_weapon_allow_tags
from .monster_template_effects import template_combat_tags, template_encounter_start_effects, template_on_hit_effects
from .monster_stats import parse_monster_attacks, parse_monster_life

CATEGORY_BY_TABLE = {
    "vermin": "vermin",
    "minions": "minions",
    "weird": "weird",
    "boss": "boss",
    "caverns_vermin": "vermin",
    "caverns_minions": "minions",
    "caverns_weird": "weird",
    "caverns_boss": "boss",
    "fungal_grottoes_vermin": "vermin",
    "fungal_grottoes_minions": "minions",
    "fungal_grottoes_weird": "weird",
    "fungal_grottoes_boss": "boss",
    "fiendish_foes_vermin": "vermin",
    "fiendish_foes_minions": "minions",
    "fiendish_foes_weird": "weird",
    "fiendish_foes_boss": "boss",
    "tag_minions": "minions",
    "tag_weird": "weird",
    "tag_boss": "boss",
    "wandering": "minions",
}


def find_monster_template(monsters: dict[str, Any], name: str) -> tuple[str, dict[str, Any]] | None:
    for table_key in MONSTER_TABLE_KEYS:
        for entry in monsters.get(table_key, []):
            if isinstance(entry, dict) and entry.get("name") == name:
                return table_key, entry
    return None


def spawn_manifest_foes(monsters: dict[str, Any], foes: list[dict[str, Any]], hcl: int) -> list[EnemyState]:
    enemies: list[EnemyState] = []
    for foe_ref in foes:
        name = foe_ref.get("name")
        count = int(foe_ref.get("count", 1))
        if not isinstance(name, str):
            continue
        located = find_monster_template(monsters, name)
        if located is None:
            continue
        table_key, template = located
        category = CATEGORY_BY_TABLE.get(table_key, "minions")
        level = max(1, hcl + int(template.get("level_delta", 0)))
        life = parse_monster_life(template.get("life", 1), hcl)
        attacks = parse_monster_attacks(template.get("attacks", 1), hcl)
        tags = (
            template_surprise_tags(template)
            + template_weapon_allow_tags(template)
            + template_combat_tags(template)
        )
        for _ in range(max(1, count)):
            enemies.append(
                EnemyState(
                    id=uuid4().hex,
                    name=template["name"],
                    category=category,
                    level=level,
                    life=life,
                    max_life=life,
                    attacks=attacks,
                    tags=tags,
                    on_hit_effects=template_on_hit_effects(template),
                    encounter_start_effects=template_encounter_start_effects(template),
                )
            )
    return enemies
