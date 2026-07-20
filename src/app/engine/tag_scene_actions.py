from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Protocol


class TagSceneActor(Protocol):
    class_id: str
    class_name: str
    level: int


@dataclass(frozen=True)
class TagSceneModifierRule:
    match_any: tuple[str, ...]
    scaling: Literal["level", "half_level", "fixed"]
    fixed_value: int = 0


@dataclass(frozen=True)
class TagSceneCheckOutcome:
    target_scene: str
    result_label: str
    player_text: str


@dataclass(frozen=True)
class TagSceneActionDefinition:
    key: str
    scene: str
    label: str
    tooltip: str
    source_reference: str
    check_kind: Literal["save"]
    difficulty: int
    actor_required: bool
    once_only: bool
    natural_one_fails: bool
    modifier_rules: tuple[TagSceneModifierRule, ...]
    success: TagSceneCheckOutcome
    failure: TagSceneCheckOutcome


TAG_SCENE_ACTION_DEFINITIONS: dict[str, TagSceneActionDefinition] = {
    "bofto_theft_save": TagSceneActionDefinition(
        key="bofto_theft_save",
        scene="Scene 14",
        label="Choose thief and roll",
        tooltip=(
            "Choose the party member trying to steal Bofto's star-shaped object. The app rolls the "
            "printed thievery Save vs L6 once and follows the resulting Scene automatically."
        ),
        source_reference="TAG pp.29, 31, Scene 14",
        check_kind="save",
        difficulty=6,
        actor_required=True,
        once_only=True,
        natural_one_fails=True,
        modifier_rules=(
            TagSceneModifierRule(match_any=("rogue", "halfling"), scaling="level"),
            TagSceneModifierRule(match_any=("swashbuckler", "assassin"), scaling="half_level"),
            TagSceneModifierRule(match_any=("elf",), scaling="fixed", fixed_value=1),
        ),
        success=TagSceneCheckOutcome(
            target_scene="Scene 19",
            result_label="theft succeeds",
            player_text="Resolve the star-shaped object's Will Save.",
        ),
        failure=TagSceneCheckOutcome(
            target_scene="Scene 18",
            result_label="theft fails",
            player_text="The attempted theft ends the rumor.",
        ),
    ),
}


def tag_scene_action_definition(action_key: str) -> TagSceneActionDefinition | None:
    return TAG_SCENE_ACTION_DEFINITIONS.get(str(action_key or "").strip())


def tag_scene_action_modifier(definition: TagSceneActionDefinition, actor: TagSceneActor) -> int:
    class_text = f"{actor.class_id} {actor.class_name}".casefold()
    level = max(1, int(actor.level or 1))
    for rule in definition.modifier_rules:
        if not any(term.casefold() in class_text for term in rule.match_any):
            continue
        if rule.scaling == "level":
            return level
        if rule.scaling == "half_level":
            return level // 2
        return int(rule.fixed_value)
    return 0


def tag_scene_action_succeeded(
    definition: TagSceneActionDefinition,
    *,
    natural_roll: int,
    total: int,
) -> bool:
    if definition.natural_one_fails and natural_roll == 1:
        return False
    return total >= definition.difficulty


def tag_scene_action_manifest(action_key: str) -> dict[str, object] | None:
    definition = tag_scene_action_definition(action_key)
    return asdict(definition) if definition is not None else None
