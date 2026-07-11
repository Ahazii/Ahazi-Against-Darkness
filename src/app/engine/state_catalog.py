from __future__ import annotations

"""Supplement-scoped state catalogue resolution.

The live game still uses legacy status strings and counters. This module only
answers which source-backed state definitions belong to a locked supplement
snapshot, so later state-effect migrations have one reusable boundary.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ResolvedStateCatalog:
    """Immutable state-definition scope for one supplement snapshot."""

    active_supplement_ids: tuple[str, ...]
    provider_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    excluded_state_ids: tuple[str, ...]
    _definitions: tuple[dict[str, Any], ...]

    def definitions(self) -> list[dict[str, Any]]:
        """Return copies so callers cannot mutate the shared catalogue."""
        return deepcopy(list(self._definitions))

    def payload(self) -> dict[str, Any]:
        return {
            "active_supplement_ids": list(self.active_supplement_ids),
            "provider_ids": list(self.provider_ids),
            "state_ids": list(self.state_ids),
            "excluded_state_ids": list(self.excluded_state_ids),
        }


def state_provider_id(definition: dict[str, Any], default_provider_id: str = "") -> str:
    """Read a state provider from its existing source reference."""
    source = definition.get("source") if isinstance(definition.get("source"), dict) else {}
    return str(source.get("supplement_id") or default_provider_id or "").strip()


def resolve_state_catalog(
    definitions: Iterable[dict[str, Any]],
    active_supplement_ids: Iterable[str],
    *,
    default_provider_id: str = "",
) -> ResolvedStateCatalog:
    """Filter source-backed definitions to the active supplement snapshot.

    This is intentionally a catalogue operation, not an effect executor. A
    state can be visible here while its current behaviour remains implemented
    through the existing legacy rule helper.
    """
    active_ids = tuple(dict.fromkeys(str(item).strip() for item in active_supplement_ids if str(item).strip()))
    active_set = set(active_ids)
    active_definitions: list[dict[str, Any]] = []
    excluded_state_ids: list[str] = []
    provider_ids: list[str] = []
    for definition in definitions:
        state_id = str(definition.get("id") or "").strip()
        provider_id = state_provider_id(definition, default_provider_id)
        if provider_id and provider_id in active_set:
            active_definitions.append(deepcopy(definition))
            if provider_id not in provider_ids:
                provider_ids.append(provider_id)
        elif state_id:
            excluded_state_ids.append(state_id)
    return ResolvedStateCatalog(
        active_supplement_ids=active_ids,
        provider_ids=tuple(provider_ids),
        state_ids=tuple(str(item.get("id") or "") for item in active_definitions if item.get("id")),
        excluded_state_ids=tuple(excluded_state_ids),
        _definitions=tuple(active_definitions),
    )
