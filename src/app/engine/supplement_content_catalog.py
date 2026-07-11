from __future__ import annotations

"""Reusable supplement-snapshot filtering for reviewed runtime catalogues."""

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ResolvedSupplementContentCatalog:
    """Immutable source-record scope for one locked supplement snapshot."""

    active_supplement_ids: tuple[str, ...]
    provider_ids: tuple[str, ...]
    record_ids: tuple[str, ...]
    excluded_record_ids: tuple[str, ...]
    _records: tuple[dict[str, Any], ...]

    def records(self) -> list[dict[str, Any]]:
        """Return copies so callers cannot mutate the shared catalogue."""
        return deepcopy(list(self._records))

    def payload(self) -> dict[str, Any]:
        return {
            "active_supplement_ids": list(self.active_supplement_ids),
            "provider_ids": list(self.provider_ids),
            "record_ids": list(self.record_ids),
            "excluded_record_ids": list(self.excluded_record_ids),
        }


def source_provider_id(record: dict[str, Any], default_provider_id: str = "") -> str:
    """Read a content provider from an existing source reference."""
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    return str(source.get("supplement_id") or default_provider_id or "").strip()


def resolve_supplement_content_catalog(
    records: Iterable[dict[str, Any]],
    active_supplement_ids: Iterable[str],
    *,
    default_provider_id: str = "",
) -> ResolvedSupplementContentCatalog:
    """Filter source records to their active supplement providers.

    This resolves catalogue ownership only. It does not execute an effect or
    change the legacy rule helper that currently implements the record.
    """
    active_ids = tuple(dict.fromkeys(str(item).strip() for item in active_supplement_ids if str(item).strip()))
    active_set = set(active_ids)
    active_records: list[dict[str, Any]] = []
    excluded_record_ids: list[str] = []
    provider_ids: list[str] = []
    for record in records:
        record_id = str(record.get("id") or "").strip()
        provider_id = source_provider_id(record, default_provider_id)
        if provider_id and provider_id in active_set:
            active_records.append(deepcopy(record))
            if provider_id not in provider_ids:
                provider_ids.append(provider_id)
        elif record_id:
            excluded_record_ids.append(record_id)
    return ResolvedSupplementContentCatalog(
        active_supplement_ids=active_ids,
        provider_ids=tuple(provider_ids),
        record_ids=tuple(str(item.get("id") or "") for item in active_records if item.get("id")),
        excluded_record_ids=tuple(excluded_record_ids),
        _records=tuple(active_records),
    )
