from __future__ import annotations

"""Supplement-scoped terrain catalogue resolution."""

from typing import Any, Iterable

from .supplement_content_catalog import (
    ResolvedSupplementContentCatalog,
    resolve_supplement_content_catalog,
)


class ResolvedTerrainCatalog(ResolvedSupplementContentCatalog):
    """Terrain-named view of the reusable source catalogue."""

    @property
    def terrain_ids(self) -> tuple[str, ...]:
        return self.record_ids

    @property
    def excluded_terrain_ids(self) -> tuple[str, ...]:
        return self.excluded_record_ids

    def definitions(self) -> list[dict[str, Any]]:
        return self.records()


def resolve_terrain_catalog(
    definitions: Iterable[dict[str, Any]],
    active_supplement_ids: Iterable[str],
    *,
    default_provider_id: str = "",
) -> ResolvedTerrainCatalog:
    resolved = resolve_supplement_content_catalog(
        definitions,
        active_supplement_ids,
        default_provider_id=default_provider_id,
    )
    return ResolvedTerrainCatalog(
        active_supplement_ids=resolved.active_supplement_ids,
        provider_ids=resolved.provider_ids,
        record_ids=resolved.record_ids,
        excluded_record_ids=resolved.excluded_record_ids,
        _records=tuple(resolved.records()),
    )
