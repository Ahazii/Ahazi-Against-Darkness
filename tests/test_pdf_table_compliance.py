from __future__ import annotations

import json
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


def _equipment_shop() -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return json.loads((packaged / "equipment_shop.json").read_text(encoding="utf-8"))


def _catalog(name: str) -> dict:
    packaged = Path(__file__).resolve().parents[1] / "data" / "rules"
    return json.loads((packaged / name).read_text(encoding="utf-8"))


def test_ee_p68_p76_spell_and_scroll_tables_match_pdf_rows() -> None:
    assert [(row["roll"], row["spell"], row["source_page"]) for row in _rows("basic_spells_table")] == [
        ("1", "Blessing", 69),
        ("2", "Escape", 69),
        ("3", "Lightning", 69),
        ("4", "Fireball", 69),
        ("5", "Protection", 69),
        ("6", "Sleep", 69),
        ("—", "Healing prayer", 28),
    ]
    assert [(row["roll"], row["spell"], row["source_page"]) for row in _rows("druid_spells_table")] == [
        ("1", "Disperse Vermin", 70),
        ("2", "Summon Beast", 70),
        ("3", "Water Jet", 70),
        ("4", "Bear Form", 70),
        ("5", "Warp Wood", 71),
        ("6", "Barkskin", 71),
        ("7", "Lightning Strike", 71),
        ("8", "Spiderweb", 71),
        ("9", "Entangle", 71),
        ("10", "Subdual", 71),
        ("11", "Forest Pathway", 72),
        ("12", "Alter Weather", 72),
    ]
    assert [(row["roll"], row["spell"], row["source_page"]) for row in _rows("illusionist_spells_table")] == [
        ("1", "Illusionary Armor", 73),
        ("2", "Illusionary Mirror Image", 73),
        ("3", "Illusionary Servant", 74),
        ("4", "Disbelief", 74),
        ("5", "Phantasmal Binding", 74),
        ("6", "Illusionary Fog", 74),
        ("7", "Glamour Mask", 74),
        ("8", "Shadow Strike", 75),
        ("9", "Specter Swarm", 75),
        ("10", "Mirage of Fortune", 75),
        ("11", "Illusionary Banquet", 75),
        ("12", "Illusionary Sword", 75),
    ]
    assert [(row["key"], row["source_page"]) for row in _rows("scrolls_table")] == [
        ("burn", 76),
        ("who", 76),
        ("barbarian_magic", 12),
        ("modifier", 76),
        ("copy", 76),
        ("forms", 76),
    ]


def test_abyss_p15_p25_expert_skill_catalog_has_pdf_rows_and_pages() -> None:
    catalog = _catalog("expert_skills.json")
    expected_skills = [
        ("Acute Hearing", 15),
        ("Arcane Tanner", 15),
        ("Berserk Fury", 15),
        ("Brawler", 15),
        ("Combat Acrobatics", 16),
        ("Commanding Presence", 16),
        ("Continual Light", 16),
        ("Create Holy Water", 16),
        ("Culling of the Weak", 16),
        ("Danger Sense", 18),
        ("Deadly Accuracy", 18),
        ("Dead Shot", 18),
        ("Deadly Strike", 18),
        ("Detective", 18),
        ("Double Attack", 18),
        ("Dragonslayer's Strike", 18),
        ("Dying Action", 19),
        ("Gladiator", 19),
        ("Impervious", 19),
        ("Intuition", 19),
        ("Knife Throwing", 19),
        ("Lesser Necromancy", 19),
        ("Negotiator", 20),
        ("Orcslayer", 20),
        ("Poison Resistance", 20),
        ("Protective Incense", 20),
        ("Quick Footed", 20),
        ("Scroll Maker", 20),
        ("Shield Bash", 20),
        ("Spore Alchemy", 21),
        ("Spot Weakness", 21),
        ("Stabbing Attack", 21),
        ("Stone Mastery", 21),
        ("Strong Will", 21),
        ("Super Logic", 21),
        ("Sworn Enemy", 21),
        ("Terrifying Savagery", 22),
        ("Turn Undead", 22),
        ("Vampire Hunter", 22),
        ("Withstand Pain", 22),
        ("Whirlwind of Steel", 22),
    ]
    assert [(row["name"], row["source_page"]) for row in catalog["skills"]] == expected_skills
    assert [(row["name"], row["source_page"]) for row in catalog["expert_spells"]] == [
        ("Healing Surge", 24),
        ("Infallible Missile", 24),
        ("Lifeforce Control", 25),
        ("Mass Teleport", 25),
        ("Aura of Terror", 25),
        ("Reverse Gaze", 25),
    ]


def test_ee_class_trick_flags_catalog_has_pdf_sources() -> None:
    catalog = _catalog("ee_class_tricks.json")
    assert [(row["name"], row["source_page"]) for row in catalog["flags"]] == [
        ("Stealth Training", 79),
        ("Sacrifice Defense", 26),
        ("Sacrifice Shield", 26),
        ("Army of Dolls", 44),
        ("Divine Smite", 55),
    ]


def test_fd_p6_p21_heroic_and_legendary_catalogs_have_pdf_rows_and_pages() -> None:
    heroic = _catalog("heroic_skills.json")
    legendary = _catalog("legendary_skills.json")
    assert [(row["name"], row["source_page"]) for row in heroic["skills"]] == [
        ("Aggressive Stance", 6),
        ("Ambition", 6),
        ("Ballistic Training", 6),
        ("Battle Training", 7),
        ("Beast Leadership", 7),
        ("Boatman", 7),
        ("Carnage", 7),
        ("Catfall", 7),
        ("Copy Grimoire", 8),
        ("Deadly Stab", 8),
        ("Deep Strike", 9),
        ("Deep Wound", 9),
        ("Charge Breaker", 9),
        ("Cleave", 9),
        ("Defensive Stance", 9),
        ("Double Shot", 10),
        ("Druidic Training", 10),
        ("Eldritch Aim", 10),
        ("Eldritch Force", 10),
        ("Explosive Magic", 10),
        ("Heroic Accuracy", 10),
        ("Heroic Climber", 12),
        ("Heroic Courage", 12),
        ("Heroic Dodge", 12),
        ("Heroic Shield Bash", 12),
        ("Heroic Swimmer", 12),
        ("Hero's Banquet", 12),
        ("Hero's Rest", 13),
        ("Knife Master", 13),
        ("Mass Blessing", 13),
        ("Master Strike", 13),
        ("Preserve Corpse", 13),
        ("Prodigious Memory", 13),
        ("Protected by Fate", 15),
        ("Protected by Divine Forces", 15),
        ("Restore", 15),
        ("Restore Mental Capacity", 15),
        ("Song of Elidra", 15),
        ("Spite", 16),
        ("Stable Mind", 16),
        ("Support Casting", 16),
        ("Training Focus", 16),
        ("Ward of Protection", 16),
        ("Wrath of the Berserker", 17),
        ("Yogic Preservation", 17),
    ]
    assert [(row["name"], row["source_page"]) for row in legendary["skills"]] == [
        ("Legendary Ballistic Training", 20),
        ("Legendary Battle Training", 20),
        ("Legendary Beast Leadership", 20),
        ("Legendary Carnage", 20),
        ("Legendary Deep Strike", 20),
        ("Legendary Deep Wound", 20),
        ("Legendary Cleave", 20),
        ("Legendary Eldritch Aim", 20),
        ("Legendary Accuracy", 20),
        ("Legendary Climber", 21),
        ("Legendary Courage", 21),
        ("Legendary Dodge", 21),
        ("Legendary Swimmer", 21),
        ("Legendary Memory", 21),
        ("Legendary Song of Elidra", 21),
        ("Legendary Spite", 21),
        ("Legendary Stable Mind", 21),
        ("Legendary Training Focus", 21),
        ("Legendary Ward of Protection", 21),
        ("Legendary Wrath of the Berserker", 21),
    ]


def test_generated_skill_tables_preserve_source_pages() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    payload = TestClient(app).get("/api/rules/tables").json()
    for table_name, name_key in (
        ("expert_skills_table", "skill"),
        ("expert_spells_table", "spell"),
        ("heroic_skills_table", "skill"),
        ("legendary_skills_table", "skill"),
        ("class_tricks_implementation_table", "ability"),
        ("ee_class_trick_flags_table", "flag"),
    ):
        rows = payload[table_name]
        assert rows
        assert all(str(row.get("source_page", "")).strip() for row in rows), table_name
        assert rows[0][name_key]


def test_ee_p107_search_and_wandering_tables_match_pdf_rows() -> None:
    assert [(row["roll"], row["effect"]) for row in _rows("search_table")] == [
        ("0-1", "wandering_monsters"),
        ("1", "wandering_monsters"),
        ("2-4", "nothing"),
        ("5-6", "found_something"),
    ]
    assert _rows("search_table")[3]["choices"] == [
        "hidden_treasure",
        "secret_door",
        "secret_passage",
        "clue",
    ]
    assert [(row["roll"], row["enemy_category"]) for row in _rows("wandering_monsters_table")] == [
        ("1-2", "vermin"),
        ("3-4", "minions"),
        ("5", "weird"),
        ("6", "boss"),
    ]


def test_ee_p108_hidden_treasure_table_matches_pdf_rows() -> None:
    rows = _rows("hidden_treasure_table")
    assert rows[0]["gold"] == "(HCL+d6)*(HCL+d6)"
    assert [(row["roll"], row["effect"]) for row in rows[1:]] == [
        ("complication 1-2", "alarm"),
        ("complication 3-5", "save_trap"),
        ("complication 6", "ghost"),
    ]
    assert rows[2]["level"] == "HCL+1"
    assert rows[3]["level"] == "HCL"


def test_ee_p109_door_table_matches_pdf_rows() -> None:
    rows = _rows("door_table")
    assert [(row["roll"], row["door_type"]) for row in rows] == [
        ("2", "sealed"),
        ("3", "iron"),
        ("4", "illusion"),
        ("5-6", "locked"),
        ("7-10", "unlocked"),
        ("11", "trap_door"),
        ("12", "lever"),
    ]
    assert rows[0]["level"] == "HCL"
    assert rows[0]["treasure_bonus"] == 1
    assert rows[1]["level"] == "HCL+d6"
    assert rows[1]["treasure_bonus"] == 1
    assert rows[2]["requires_clues"] == 3
    assert rows[6]["requires_clue"] == 1


def test_ee_p152_tile_content_table_matches_pdf_rows() -> None:
    rows = _rows("room_content_table")
    assert [row["roll"] for row in rows] == ["2", "3", "4", "5", "6", "7-8", "9", "10", "11", "12"]
    assert rows[0]["any"]["key"] == "treasure"
    assert rows[1]["any"]["key"] == "trap_treasure"
    assert rows[2]["corridor"]["key"] == "searchable"
    assert rows[2]["room"]["key"] == "special_event"
    assert rows[3]["corridor"]["key"] == "searchable"
    assert rows[3]["room"]["key"] == "special_feature"
    assert rows[4]["any"]["enemy_category"] == "vermin"
    assert rows[5]["any"]["enemy_category"] == "minions"
    assert rows[6]["corridor"]["key"] == "searchable"
    assert rows[6]["room"]["enemy_category"] == "minions"
    assert rows[7]["corridor"]["key"] == "searchable"
    assert rows[7]["room"]["key"] == "searchable"
    assert rows[7]["room"]["choices"] == ["secret_passage_2_clues"]
    assert "Weird" not in rows[7]["room"]["description"]
    assert rows[8]["any"]["enemy_category"] == "boss"
    assert rows[9]["corridor"]["key"] == "empty"
    assert rows[9]["room"]["enemy_tags"] == ["dragon"]


def test_ee_p153_p154_special_feature_and_event_tables_match_pdf_rows() -> None:
    assert [(row["roll"], row["key"]) for row in _rows("dungeon_special_features_table")] == [
        ("1", "fountain"),
        ("2", "blessed_temple"),
        ("3", "armory"),
        ("4", "cursed_altar"),
        ("5", "statue"),
        ("6", "puzzle_box"),
    ]
    assert [(row["roll"], row["key"]) for row in _rows("dungeon_special_events_table")] == [
        ("1", "ghost"),
        ("2", "wandering_monsters"),
        ("3", "lady_in_white"),
        ("4", "trap"),
        ("5", "healer"),
        ("6", "alchemist"),
    ]
    assert [(row["roll"], row["enemy_category"]) for row in _rows("special_event_wandering_table")] == [
        ("1-3", "vermin"),
        ("4", "minions"),
        ("5", "weird"),
        ("6", "boss"),
    ]


def test_ee_p157_p158_treasure_tables_match_pdf_rows() -> None:
    assert [(row["roll"], row.get("gold"), row["result"]) for row in _rows("treasure_table")] == [
        ("1", None, "No treasure found."),
        ("2", "1d6", "1d6 gp."),
        ("3", "2d6", "2d6 gp."),
        ("4", "2d6*5", "Jewel worth 2d6 x 5 gp."),
        ("5", "3d6*10", "Treasure chest with 3d6 x 10 gp."),
        ("6", None, "Roll on the Dungeon Magic Treasure Table."),
    ]
    assert [(row["roll"], row["items"][0]) for row in _rows("dungeon_magic_treasure_table")] == [
        ("1", "Wand of Sleep (3 charges)"),
        ("2", "Ring of Teleportation"),
        ("3", "Fools' Gold"),
        ("4", "Magic Weapon (+1 Attack)"),
        ("5", "Potion of Healing"),
        ("6", "Fireball Staff (2 charges)"),
    ]


def test_ee_p162_p163_quest_and_epic_reward_tables_match_pdf_rows() -> None:
    assert [(row["roll"], row["key"]) for row in _rows("quest_table")] == [
        ("1", "bring_head"),
        ("2", "bring_gold"),
        ("3", "bring_alive"),
        ("4", "bring_item"),
        ("5", "peaceful_way"),
        ("6", "slay_all"),
    ]
    assert [(row["roll"], row["key"]) for row in _rows("epic_rewards_table")] == [
        ("1", "book_of_skalitos"),
        ("2", "gold_of_kerrak_dar"),
        ("3", "enchanted_weapon"),
        ("4", "shield_of_warning"),
        ("5", "arrow_of_slaying"),
        ("6", "holy_symbol"),
    ]


def test_ee_p164_dungeon_trap_table_matches_pdf_rows() -> None:
    rows = _rows("trap_table")
    assert [(row["roll"], row["trap_key"]) for row in rows] == [
        ("1", "dart"),
        ("2", "poison_gas"),
        ("3", "trapdoor"),
        ("4", "bear_trap"),
        ("5", "spears"),
        ("6", "falling_stone"),
    ]
    assert [(row["level"], row["target"], row["damage"]) for row in rows] == [
        ("HCL+1", "random", 1),
        ("HCL+2", "all", 1),
        ("HCL+3", "lead", 1),
        ("HCL+3", "lead", 1),
        ("HCL+4", "two_random", 1),
        ("HCL+4", "rear", 2),
    ]
    assert rows[5]["shield_applies"] is False


def test_ee_p81_p88_equipment_shop_contains_pdf_rows() -> None:
    items = _equipment_shop()["items"]
    by_key = {item["key"]: item for item in items}
    expected = [
        ("bow", "Bow", 15, 81),
        ("arrows", "Arrows (12)", 6, 81),
        ("hand_weapon", "Hand weapon", 6, 81),
        ("light_hand_weapon", "Light hand weapon", 5, 81),
        ("two_handed_weapon", "Two-handed weapon", 15, 82),
        ("shield", "Shield", 5, 82),
        ("crossbow", "Crossbow", 15, 82),
        ("sling", "Sling", 4, 82),
        ("light_armor", "Light armor", 10, 83),
        ("heavy_armor", "Heavy armor", 30, 83),
        ("lantern", "Lantern", 4, 83),
        ("torches", "Torches (12)", 1, 83),
        ("holy_water", "Holy water vial", 30, 83),
        ("rope", "Rope", 4, 84),
        ("bandage", "Bandage", 5, 84),
        ("potion", "Potion of Healing", 100, 84),
        ("food_ration", "Food ration", 1, 84),
        ("lantern_hook", "Lantern hook", 2, 84),
        ("ten_foot_pole", "10' pole", 2, 85),
        ("flammable_oil", "Flask of flammable oil", 10, 85),
        ("blessing_scroll", "Blessing spell scroll", 100, 85),
        ("resurrection", "Resurrection ritual", 1000, 85),
        ("bag_of_nails", "Bag of nails", 4, 85),
        ("silvering_light", "Silvering (light/hand/quiver)", 20, 86),
        ("silvering_two_handed", "Silvering (two-handed weapon)", 40, 86),
        ("amulet", "Amulet", 15, 86),
        ("talisman", "Talisman", 10, 86),
        ("herbal_tonic", "Herbal tonic", 20, 86),
        ("scroll_tube", "Scroll tube", 4, 86),
        ("gilding", "Gilding", 50, 87),
        ("gremlin_repellant", "Gremlin repellant", 5, 87),
        ("handgun", "Handgun", 30, 87),
        ("black_powder_rifle", "Black powder rifle", 90, 87),
        ("wolfsbane", "Wolfsbane", 10, 87),
        ("throwing_star", "Throwing star", 2, 88),
        ("good_lockpicks", "Good lock-picks", 25, 88),
        ("stake", "Stake", 6, 88),
        ("crowbar", "Crowbar", 10, 88),
        ("berserkers_mushroom", "Berserker's Mushroom", 15, 88),
    ]
    for key, name, price, page in expected:
        assert key in by_key
        assert by_key[key]["name"] == name
        assert by_key[key]["price_gp"] == price
        assert by_key[key]["source_page"] == page
    assert by_key["acid_vial"]["name"] == "Acid vial"


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
