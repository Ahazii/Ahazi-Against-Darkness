from __future__ import annotations

from pathlib import Path

from app.rules.table_providers import merge_packaged_dungeon_tables


def _rules_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "rules"


def test_default_table_provider_merge_keeps_all_existing_packaged_sources() -> None:
    tables = merge_packaged_dungeon_tables(_rules_dir())

    assert "trap_table" in tables
    assert "fd_room_content_table" in tables
    assert "abyss_room_content_table" in tables
    assert "courtship_seaside_encounter_table" in tables
    assert tables["courtship_book_of_secrets_table"]
    assert tables["courtship_apothecary_recipes_table"]


def test_scoped_table_provider_merge_is_ready_for_snapshot_migration_without_affecting_default() -> None:
    tables = merge_packaged_dungeon_tables(_rules_dir(), ["expanded-edition-core", "forsaken-depths"])

    assert "trap_table" in tables
    assert "fd_room_content_table" in tables
    assert "abyss_room_content_table" not in tables
    assert "courtship_seaside_encounter_table" not in tables
