from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdventureDescriptor:
    id: str
    name: str
    adventure_type: str


def list_imported_adventures() -> list[AdventureDescriptor]:
    return []
