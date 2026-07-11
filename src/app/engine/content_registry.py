from __future__ import annotations

"""Resolved, session-safe supplement content context.

This is the migration seam between supplement manifests and the existing
rule-family modules. It deliberately exposes declarations only: reviewed PDF
records cannot affect play until a later promotion step creates validated
runtime content records.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .supplements import (
    SUPPLEMENT_REGISTRY_VERSION,
    enabled_supplement_ids_from_selection,
    supplement_registry,
)
from .states import STATE_REGISTRY_VERSION, resolve_state_registry
from .terrain_registry import TERRAIN_REGISTRY_VERSION, resolve_terrain_registry


CONTENT_REGISTRY_VERSION = 3


@dataclass(frozen=True)
class ResolvedContentRegistry:
    """Immutable view of the supplement declarations locked for one session."""

    registry_version: int
    supplement_registry_version: int
    active_supplement_ids: tuple[str, ...]
    runtime_supplement_ids: tuple[str, ...]
    review_only_supplement_ids: tuple[str, ...]
    capability_providers: dict[str, tuple[str, ...]]
    legacy_mappings: dict[str, tuple[str, ...]]
    state_registry_version: int
    state_provider_ids: tuple[str, ...]
    active_state_ids: tuple[str, ...]
    terrain_registry_version: int
    terrain_provider_ids: tuple[str, ...]
    active_terrain_ids: tuple[str, ...]
    diagnostics: tuple[str, ...]

    def payload(self) -> dict[str, Any]:
        return {
            "registry_version": self.registry_version,
            "supplement_registry_version": self.supplement_registry_version,
            "active_supplement_ids": list(self.active_supplement_ids),
            "runtime_supplement_ids": list(self.runtime_supplement_ids),
            "review_only_supplement_ids": list(self.review_only_supplement_ids),
            "capability_providers": {key: list(value) for key, value in self.capability_providers.items()},
            "legacy_mappings": {key: list(value) for key, value in self.legacy_mappings.items()},
            "state_registry_version": self.state_registry_version,
            "state_provider_ids": list(self.state_provider_ids),
            "active_state_ids": list(self.active_state_ids),
            "terrain_registry_version": self.terrain_registry_version,
            "terrain_provider_ids": list(self.terrain_provider_ids),
            "active_terrain_ids": list(self.active_terrain_ids),
            "diagnostics": list(self.diagnostics),
        }

    def provides(self, capability: str) -> bool:
        return bool(self.capability_providers.get(capability))


def resolve_content_registry(
    root_dir: Path | None,
    data_dir: Path | None,
    active_supplement_ids: list[str] | tuple[str, ...] | None,
) -> ResolvedContentRegistry:
    """Resolve one supplement snapshot without executing any supplement rules."""
    manifests = supplement_registry(root_dir, data_dir)
    selected_ids = enabled_supplement_ids_from_selection(list(active_supplement_ids or []), manifests)
    by_id = {str(manifest["id"]): manifest for manifest in manifests}
    selected = [by_id[supplement_id] for supplement_id in selected_ids]
    runtime_ids: list[str] = []
    review_only_ids: list[str] = []
    capability_providers: dict[str, list[str]] = {}
    legacy_mappings: dict[str, list[str]] = {}
    diagnostics: list[str] = []

    for manifest in selected:
        supplement_id = str(manifest["id"])
        if manifest.get("status") != "active":
            review_only_ids.append(supplement_id)
            diagnostics.append(
                f"{supplement_id} is selected for this session but remains review-only; it contributes no runtime rules yet."
            )
            continue
        runtime_ids.append(supplement_id)
        for capability in manifest.get("capabilities") or []:
            capability_providers.setdefault(str(capability), []).append(supplement_id)
        for field, values in (manifest.get("legacy_mappings") or {}).items():
            for value in values or []:
                if str(value) not in legacy_mappings.setdefault(str(field), []):
                    legacy_mappings[str(field)].append(str(value))

    state_catalog = resolve_state_registry(selected_ids)
    terrain_catalog = resolve_terrain_registry(selected_ids)

    return ResolvedContentRegistry(
        registry_version=CONTENT_REGISTRY_VERSION,
        supplement_registry_version=SUPPLEMENT_REGISTRY_VERSION,
        active_supplement_ids=tuple(selected_ids),
        runtime_supplement_ids=tuple(runtime_ids),
        review_only_supplement_ids=tuple(review_only_ids),
        capability_providers={key: tuple(value) for key, value in sorted(capability_providers.items())},
        legacy_mappings={key: tuple(value) for key, value in sorted(legacy_mappings.items())},
        state_registry_version=STATE_REGISTRY_VERSION,
        state_provider_ids=state_catalog.provider_ids,
        active_state_ids=state_catalog.state_ids,
        terrain_registry_version=TERRAIN_REGISTRY_VERSION,
        terrain_provider_ids=terrain_catalog.provider_ids,
        active_terrain_ids=terrain_catalog.terrain_ids,
        diagnostics=tuple(diagnostics),
    )
