from __future__ import annotations

from pathlib import Path

from app.rules.repository import RulesRepository


def _tables() -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override").dungeon_tables()


def _rows(table_name: str) -> list[dict]:
    return _tables()[table_name]


def _monsters() -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override").monsters()


def _icons() -> list[dict]:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return RulesRepository(packaged, packaged / "_override").icons()


def test_ee_p155_caverns_special_events_match_pdf_rows() -> None:
    rows = _rows("caverns_special_events_table")
    assert [(row["roll"], row["key"]) for row in rows] == [
        ("1", "trap"),
        ("2", "cavemen_explorers"),
        ("3", "morlock_spy"),
        ("4", "cave_goblin_scout"),
        ("5", "dwarf_miner"),
        ("6", "dwarf_party_gem"),
    ]
    assert "dwarf miner" in rows[4]["result"]
    assert "d6 gems worth 25gp each" in rows[4]["result"]
    assert "lantern-bearer" not in " ".join(row["result"] for row in rows).lower()


def test_ee_p156_fungal_special_events_match_pdf_rows() -> None:
    rows = _rows("fungal_grottoes_special_events_table")
    assert [(row["roll"], row["key"]) for row in rows] == [
        ("1", "trap_rare_item"),
        ("2", "fungal_cavemen"),
        ("3", "spore_cloud"),
        ("4", "halfling_scout"),
        ("5", "fungal_merchant"),
        ("6", "mycelial_warning"),
    ]
    assert "Equipment list" in rows[4]["result"]
    assert "mushroom monk" in rows[5]["result"]


def test_ee_p160_caverns_special_item_table_matches_pdf_rows() -> None:
    rows = _rows("caverns_special_item_table")
    assert [(row["roll"], row["items"][0]) for row in rows] == [
        ("1", "Small gemstone (3d6+3gp)"),
        ("2", "Glittering Crystal"),
        ("3", "Map Fragment"),
        ("4", "Adventurer’s Dead Body"),
        ("5", "Miners’ Ointment"),
        ("6", "Miners’ Amulet"),
    ]
    assert "Magic Weapon" not in " ".join(row["result"] for row in rows)


def test_ee_p161_fungal_rare_item_table_matches_pdf_rows() -> None:
    rows = _rows("fungal_grottoes_rare_item_table")
    assert [(row["roll"], row["items"][0]) for row in rows] == [
        ("1", "Small gemstone (2d6+2gp) or Leafsteel Armor"),
        ("2", "Red Death"),
        ("3", "Xicthul’s Cap"),
        ("4", "Adventurer’s Dead Body"),
        ("5", "Mushroom Gatherer’s Basket"),
        ("6", "Morel Crusher"),
    ]
    assert "Fungal-hilted magic weapon" not in " ".join(row["result"] for row in rows)


def test_ee_p165_p166_environment_trap_tables_use_pdf_trap_keys() -> None:
    assert [(row["roll"], row["trap_key"]) for row in _rows("caverns_trap_table")] == [
        ("1", "stalactite"),
        ("2", "rockslide"),
        ("3", "hidden_pit"),
        ("4", "swinging_log"),
        ("5", "toxic_mushrooms"),
        ("6", "rolling_boulder"),
    ]
    assert [(row["roll"], row["trap_key"]) for row in _rows("fungal_grottoes_trap_table")] == [
        ("1", "sleep_spores"),
        ("2", "spore_cloud"),
        ("3", "slime_patch"),
        ("4", "mycelium_snare"),
        ("5", "shrieking_mushroom"),
        ("6", "cordyceps_trap"),
    ]


def test_ee_p167_p170_dungeon_monster_table_names_match_pdf_rows() -> None:
    monsters = _monsters()
    assert [row["name"] for row in monsters["vermin"]] == [
        "Rats",
        "Vampire Bats",
        "Goblin Swarmlings",
        "Giant Centipedes",
        "Vampire Frogs",
        "Skeletal Rats",
    ]
    assert [row["name"] for row in monsters["minions"]] == [
        "Skeletons/Zombies",
        "Goblins",
        "Hobgoblins",
        "Orcs",
        "Trolls",
        "Mushroom Men",
    ]
    assert [row["name"] for row in monsters["weird"]] == [
        "Minotaur",
        "Iron Eater",
        "Chimera",
        "Catoblepas",
        "Giant Spider",
        "Invisible Gremlins",
    ]
    assert [row["name"] for row in monsters["boss"]] == [
        "Mummy",
        "Orc Brute",
        "Ogre",
        "Medusa",
        "Chaos Lord",
        "Young Dragon",
    ]


def test_ee_p171_p174_caverns_monster_table_names_match_pdf_rows() -> None:
    monsters = _monsters()
    assert [row["name"] for row in monsters["caverns_vermin"]] == [
        "Echo Bats",
        "Mud Centipedes",
        "Vengeance Cockroaches",
        "Stalactomimics",
        "Screaming Toads",
        "Red Cave Spiders",
    ]
    assert [row["name"] for row in monsters["caverns_minions"]] == [
        "Morlocks",
        "Cave Goblins",
        "Cave Skeletons",
        "Cave Orcs",
        "Rat Men of the Deep",
        "Cavemen",
    ]
    assert [row["name"] for row in monsters["caverns_boss"]] == [
        "Manataur",
        "Caveman Champion",
        "Hoary Ogre of the Caverns",
        "Cavern Werebear",
        "Land Siren",
        "Fire Bear",
    ]
    assert [row["name"] for row in monsters["caverns_weird"]] == [
        "Drillworm",
        "Cavern Wraith",
        "Cavern Sludge",
        "Minosaur",
        "Cornucopia of Chaos",
        "Cave Dragon",
    ]


def test_ee_p175_p178_fungal_monster_table_names_match_pdf_rows() -> None:
    monsters = _monsters()
    assert [row["name"] for row in monsters["fungal_grottoes_vermin"]] == [
        "Spore Mites",
        "Glowmaggots",
        "Fungus Leeches",
        "Myco-Gnats",
        "Spore Toads",
        "Boneworms",
    ]
    assert [row["name"] for row in monsters["fungal_grottoes_minions"]] == [
        "Spore Men",
        "Halfling Mushroom Pickers",
        "Moldspawn",
        "Myceliarchs",
        "Cave Locusts",
        "Toadstool Knights",
    ]
    assert [row["name"] for row in monsters["fungal_grottoes_boss"]] == [
        "Myco-Tyrant",
        "Fungus Hag",
        "Spore Lord",
        "Rot Ogre",
        "Caplord Knight",
        "Fungal Dragon",
    ]
    assert [row["name"] for row in monsters["fungal_grottoes_weird"]] == [
        "Shroom Colossus",
        "Spore Swarm",
        "Myco-Mimic",
        "Hallucinogenic Horror",
        "Fungus-infected Hydra",
        "Spore Phantom",
    ]


def test_monster_icon_overrides_do_not_expose_non_pdf_monsters() -> None:
    monster_names = {
        row["name"]
        for rows in _monsters().values()
        if isinstance(rows, list)
        for row in rows
        if isinstance(row, dict) and row.get("name")
    }
    invalid = [
        icon.label
        for icon in _icons()
        if icon.category == "monster"
        and not icon.id.startswith("monster-category-")
        and icon.label not in monster_names
    ]
    assert invalid == []
