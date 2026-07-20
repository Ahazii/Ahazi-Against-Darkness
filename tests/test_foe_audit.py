from __future__ import annotations

from tools.audit_foe_rules import FOE_TABLE_SOURCES, REVIEWED_ROWS, UNHANDLED_DECLARATIONS, foe_rows


def test_all_shipped_foe_tables_have_a_source_crosswalk() -> None:
    records = foe_rows()
    assert len(records) == 184
    assert {record["file"] for record in records} == set(FOE_TABLE_SOURCES)
    assert all(record["source"].get("book") and record["source"].get("source") for record in records)


def test_reviewed_foes_are_present_in_the_audit_index() -> None:
    indexed = {(record["file"], record["table"], record["name"]) for record in foe_rows()}
    assert REVIEWED_ROWS <= indexed


def test_foe_audit_does_not_misclassify_procedure_tables_as_foes() -> None:
    records = foe_rows()
    abyss_names = {record["name"] for record in records if record["file"] == "abyss_tables.json"}
    assert "Abyss Treasure" not in abyss_names
    assert "Abyss Trap and Treasure" not in abyss_names
    assert "Phasing Panther" in abyss_names


def test_known_unhandled_declarations_remain_explicit_in_the_audit() -> None:
    declarations = {mechanic for record in foe_rows() for mechanic in record["unhandled"]}
    assert declarations == UNHANDLED_DECLARATIONS
