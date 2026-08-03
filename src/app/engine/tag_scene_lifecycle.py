from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..schemas import SessionState


TagAutoStarter = Callable[[SessionState], bool]


TAG_GENERATED_CLOSEOUT_ACTION_LABEL = "Continue — return to town and finish"
TAG_GENERATED_CLOSEOUT_LOG_MESSAGE = (
    f"When you are ready, choose {TAG_GENERATED_CLOSEOUT_ACTION_LABEL}."
)
TAG_GENERATED_CLOSEOUT_REMINDER = (
    "Read the resolved Adventures Guild scene, then choose "
    f"{TAG_GENERATED_CLOSEOUT_ACTION_LABEL}."
)


@dataclass(frozen=True)
class TagActionLifecycle:
    auto_start: bool = False
    required_for_completion: bool = False
    starter: TagAutoStarter | None = None
    state_key: str = ""
    terminal_phases: frozenset[str] = frozenset()
    terminal_flags: frozenset[str] = frozenset()
    terminal_failure_phases: frozenset[str] = frozenset()

    def state(self, session: SessionState) -> dict[str, Any]:
        quest = session.active_quest
        if quest is None or not self.state_key:
            return {}
        value = (quest.tag_procedure_state or {}).get(self.state_key)
        return dict(value) if isinstance(value, dict) else {}

    def is_terminal(self, session: SessionState) -> bool:
        state = self.state(session)
        phase_terminal = (
            bool(self.terminal_phases)
            and str(state.get("phase") or "") in self.terminal_phases
        )
        flag_terminal = any(bool(state.get(flag)) for flag in self.terminal_flags)
        return phase_terminal or flag_terminal

    def is_terminal_failure(self, session: SessionState) -> bool:
        if not self.terminal_failure_phases:
            return False
        return str(self.state(session).get("phase") or "") in self.terminal_failure_phases


def _start_mutant_fish_scene12(session: SessionState) -> bool:
    from .tag_mutant_fish import begin_mutant_fish_scene, mutant_fish_state

    if mutant_fish_state(session):
        return False
    begin_mutant_fish_scene(session)
    return True


TAG_ACTION_LIFECYCLES: dict[str, TagActionLifecycle] = {
    "daroc_cat": TagActionLifecycle(
        required_for_completion=True,
        state_key="daroc_familiar",
        terminal_phases=frozenset({"resolved", "deferred"}),
        terminal_flags=frozenset({"resolved"}),
    ),
    "tag_repeatable_service_done": TagActionLifecycle(
        required_for_completion=True,
        state_key="tag_repeatable_service",
        terminal_phases=frozenset({"resolved"}),
    ),
    "mutant_fish_scene12": TagActionLifecycle(
        auto_start=True,
        required_for_completion=True,
        starter=_start_mutant_fish_scene12,
        state_key="mutant_fish_scene12",
        terminal_phases=frozenset({"resolved", "destroyed"}),
        terminal_failure_phases=frozenset({"destroyed"}),
    ),
    "mutant_fish_hypnosis": TagActionLifecycle(
        auto_start=True,
        required_for_completion=True,
        starter=_start_mutant_fish_scene12,
        state_key="mutant_fish_scene12",
        terminal_phases=frozenset({"resolved", "destroyed"}),
        terminal_failure_phases=frozenset({"destroyed"}),
    ),
}


def tag_action_lifecycle(action_value: str) -> TagActionLifecycle | None:
    return TAG_ACTION_LIFECYCLES.get(str(action_value or "").strip())


def tag_room_prompt(session: SessionState, room_id: str) -> dict[str, Any]:
    manifest = session.imported_manifest if isinstance(session.imported_manifest, dict) else {}
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    parameters = source.get("parameters") if isinstance(source.get("parameters"), dict) else {}
    reference = parameters.get("tag_reference") if isinstance(parameters, dict) else {}
    prompts = reference.get("room_prompts") if isinstance(reference, dict) else {}
    prompt = prompts.get(room_id) if isinstance(prompts, dict) else None
    return prompt if isinstance(prompt, dict) else {}


def auto_start_tag_room_actions(session: SessionState, room_id: str) -> bool:
    """Run each profile-declared automatic TAG room action once on entry."""
    prompt = tag_room_prompt(session, room_id)
    actions = prompt.get("actions") if isinstance(prompt, dict) else None
    changed = False
    for action in actions if isinstance(actions, list) else []:
        if not isinstance(action, dict) or not action.get("auto_start"):
            continue
        action_value = str(action.get("action_value") or "").strip()
        lifecycle = tag_action_lifecycle(action_value)
        if lifecycle is not None and lifecycle.auto_start and lifecycle.starter is not None:
            changed = lifecycle.starter(session) or changed
    return changed


def required_tag_room_action_lifecycles(
    session: SessionState,
    room_id: str,
) -> tuple[TagActionLifecycle, ...]:
    """Return registered lifecycle rules for required actions in one TAG room."""
    prompt = tag_room_prompt(session, room_id)
    actions = prompt.get("actions") if isinstance(prompt, dict) else None
    required: list[TagActionLifecycle] = []
    for action in actions if isinstance(actions, list) else []:
        if not isinstance(action, dict) or not action.get("required_for_completion"):
            continue
        lifecycle = tag_action_lifecycle(str(action.get("action_value") or ""))
        if lifecycle is not None and lifecycle.required_for_completion:
            required.append(lifecycle)
    return tuple(required)


def required_tag_room_actions_are_terminal(session: SessionState, room_id: str) -> bool:
    """Return whether every registered required action in this room is terminal."""
    required = required_tag_room_action_lifecycles(session, room_id)
    return bool(required) and all(lifecycle.is_terminal(session) for lifecycle in required)


def tag_room_has_required_action(session: SessionState, room_id: str) -> bool:
    """Return whether this room declares a registered completion-gating action."""
    return bool(required_tag_room_action_lifecycles(session, room_id))


def required_tag_room_action_has_failed_terminal(session: SessionState, room_id: str) -> bool:
    """Return whether a registered required action ended the adventure in failure."""
    for lifecycle in required_tag_room_action_lifecycles(session, room_id):
        if lifecycle.is_terminal_failure(session):
            return True
    return False


def generated_tag_rumor_entry_choice_pending(session: SessionState) -> bool:
    """Keep every generated Rumour at its shared opening until the player chooses."""
    if session.mode == "complete" or session.tag_generated_completion_pending:
        return False
    manifest = session.imported_manifest if isinstance(session.imported_manifest, dict) else {}
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    parameters = source.get("parameters") if isinstance(source.get("parameters"), dict) else {}
    reference = parameters.get("tag_reference") if isinstance(parameters, dict) else {}
    if not isinstance(reference, dict) or str(reference.get("lead_type") or "").casefold() != "rumor":
        return False
    current_tile_id = session.map_state.current_tile_id
    tile = next((item for item in session.map_state.tiles if item.id == current_tile_id), None)
    if tile is None:
        return False
    content_key = str(tile.content_key or "")
    room_id = (
        content_key.removeprefix("imported:")
        if content_key.startswith("imported:")
        else str(manifest.get("entrance_room_id") or "")
        if content_key == "entrance"
        else ""
    )
    return room_id == "tag-lead-entry"
