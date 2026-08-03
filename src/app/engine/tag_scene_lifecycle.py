from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from ..schemas import SessionState


TagAutoStarter = Callable[[SessionState], bool]


@dataclass(frozen=True)
class TagActionLifecycle:
    auto_start: bool = False
    required_for_completion: bool = False
    starter: TagAutoStarter | None = None
    state_key: str = ""
    terminal_phases: frozenset[str] = frozenset()
    terminal_failure_phases: frozenset[str] = frozenset()

    def state(self, session: SessionState) -> dict[str, Any]:
        quest = session.active_quest
        if quest is None or not self.state_key:
            return {}
        value = (quest.tag_procedure_state or {}).get(self.state_key)
        return dict(value) if isinstance(value, dict) else {}

    def is_terminal(self, session: SessionState) -> bool:
        if not self.terminal_phases:
            return False
        return str(self.state(session).get("phase") or "") in self.terminal_phases

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


def required_tag_room_actions_are_terminal(session: SessionState, room_id: str) -> bool:
    """Return whether every registered required action in this room is terminal."""
    prompt = tag_room_prompt(session, room_id)
    actions = prompt.get("actions") if isinstance(prompt, dict) else None
    required: list[TagActionLifecycle] = []
    for action in actions if isinstance(actions, list) else []:
        if not isinstance(action, dict) or not action.get("required_for_completion"):
            continue
        lifecycle = tag_action_lifecycle(str(action.get("action_value") or ""))
        if lifecycle is not None and lifecycle.required_for_completion:
            required.append(lifecycle)
    return bool(required) and all(lifecycle.is_terminal(session) for lifecycle in required)


def required_tag_room_action_has_failed_terminal(session: SessionState, room_id: str) -> bool:
    """Return whether a registered required action ended the adventure in failure."""
    prompt = tag_room_prompt(session, room_id)
    actions = prompt.get("actions") if isinstance(prompt, dict) else None
    for action in actions if isinstance(actions, list) else []:
        if not isinstance(action, dict) or not action.get("required_for_completion"):
            continue
        lifecycle = tag_action_lifecycle(str(action.get("action_value") or ""))
        if (
            lifecycle is not None
            and lifecycle.required_for_completion
            and lifecycle.is_terminal_failure(session)
        ):
            return True
    return False
