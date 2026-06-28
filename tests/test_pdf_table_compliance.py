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
        ("Surgeon (Hireling Training)", "TCOTFD p.8-9"),
        ("Herbalist (Hireling Training)", "TCOTFD p.8-9"),
        ("Poison Expert (Hireling Training)", "TCOTFD p.8-9"),
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


def test_ee_p62_swashbuckler_traits_table_matches_pdf_rows() -> None:
    rows = _rows("swashbuckler_traits_table")
    assert [(row["roll"], row["trait"], row["source_page"]) for row in rows] == [
        ("1", "Flourishing Strike", 62),
        ("2", "Daring Escape", 62),
        ("3", "Riposte", 62),
        ("4", "Lucky Hat", 62),
        ("5", "Taunt", 62),
        ("6", "Blade Dance", 62),
    ]
    assert "second off-hand Attack" in rows[0]["result"]
    assert "disengage from melee without provoking an attack" in rows[1]["result"]
    assert "counterattack with your off-hand weapon" in rows[2]["result"]
    assert "plumed/tricorn hat is destroyed" in rows[3]["result"]
    assert "does not work on Weird Monsters" in rows[4]["result"]
    assert "spend any number of panache points" in rows[5]["result"]


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


def test_ee_clue_spends_table_details_match_pdf_text() -> None:
    rows = _rows("clue_spends_table")
    by_key = {row["key"]: row for row in rows}

    reveal = by_key["reveal_secret"]
    assert reveal["source_page"] == 123
    assert "3 held Clues" in reveal["result"]
    assert "p.123 list" in reveal["result"]
    assert "drains held Clues from that hero first" in reveal["result"]

    trade = by_key["trade_information"]
    assert trade["source_page"] == 102
    assert "25gp per held Clue" in trade["result"]
    assert "100gp" in trade["result"]
    assert "persist on that roster entry" in trade["result"]

    illusion = by_key["illusion_door"]
    assert illusion["source_page"] == 109
    assert "3 held Clues" in illusion["result"]
    assert "illusion door" in illusion["result"]

    lever = by_key["lever_door"]
    assert lever["source_page"] == 109
    assert "1 held Clue" in lever["result"]
    assert "lever door" in lever["result"]

    learning = by_key["spell_learning"]
    assert learning["source_page"] == 24
    assert 32 in learning.get("source_pages", [])
    assert "3 held Clues" in learning["result"]
    assert "Wizard/elf expert spells" in learning["result"]
    assert "druid spell table" in learning["result"]

    hideout = by_key["captive_hideout"]
    assert hideout["source_page"] == 102
    assert "3 held Clues" in hideout["result"]
    assert "2d6×2d6 cave" in hideout["result"]
    assert "double their normal count" in hideout["result"]
    assert "Level×10gp ransom" in hideout["result"]

    special = by_key["special_discovery"]
    assert special["source_page"] == 108
    assert "Kerrak Dar" in special["result"]


def test_ee_p152_tile_content_table_matches_pdf_rows() -> None:
    rows = _rows("room_content_table")
    assert [row["roll"] for row in rows] == ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    assert rows[0]["any"]["key"] == "treasure"
    assert rows[1]["any"]["key"] == "trap_treasure"
    assert rows[2]["corridor"]["key"] == "searchable"
    assert rows[2]["room"]["key"] == "special_event"
    assert rows[3]["corridor"]["key"] == "empty"
    assert rows[3]["room"]["key"] == "special_feature"
    assert rows[4]["any"]["enemy_category"] == "vermin"
    assert rows[5]["any"]["enemy_category"] == "minions"
    assert rows[6]["corridor"]["key"] == "empty"
    assert rows[6]["room"]["enemy_category"] == "minions"
    assert rows[7]["any"]["key"] == "searchable"
    assert rows[7]["any"]["choices"] == ["secret_passage_2_clues"]
    assert rows[8]["corridor"]["key"] == "searchable"
    assert rows[8]["room"]["enemy_category"] == "weird"
    assert rows[9]["any"]["enemy_category"] == "boss"
    assert rows[10]["corridor"]["key"] == "empty"
    assert rows[10]["room"]["enemy_tags"] == ["dragon"]


def test_ee_p153_p154_special_feature_and_event_tables_match_pdf_rows() -> None:
    assert [(row["roll"], row["key"]) for row in _rows("dungeon_special_features_table")] == [
        ("1", "fountain"),
        ("2", "blessed_temple"),
        ("3", "armory"),
        ("4", "cursed_altar"),
        ("5", "statue"),
        ("6", "puzzle_box"),
    ]
    assert [(row["roll"], row["key"]) for row in _rows("caverns_special_features_table")] == [
        ("1", "stalactites"),
        ("2", "stalagmites"),
        ("3", "boulders"),
        ("4", "echo"),
        ("5-6", "water_pools"),
    ]
    assert [(row["roll"], row["key"]) for row in _rows("caverns_water_pool_table")] == [
        ("1", "contaminated"),
        ("2-4", "no_effect"),
        ("5-6", "refreshing"),
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
        ("0", None, "No treasure found."),
        ("1", "1d6", "All environments: d6 gp."),
        ("2", None, "Dungeon/Caverns: 2d6 gp. Fungal Grottoes: choose 2d6 Food rations or 1 roll on the Rare Mushroom Table."),
        (
            "3",
            None,
            "Dungeon: a scroll with a random wizard spell. Fungal Grottoes: choose a piece of bark with a random druid spell or 1 roll on the Rare Mushroom Table. Cavern: a prism with a random illusionist spell.",
        ),
        ("4", None, "Dungeon: a jewel worth 2d6 x 5 gp. Fungal Grottoes: choose a gem worth 2d6 x 5 gp or 2 rolls on the Rare Mushroom Table. Cavern: a gem worth 3d6 x 5 gp."),
        ("5", None, "Dungeon: a treasure chest with 3d6 x 10 gp. Fungal Grottoes: choose a gem worth 2d6 x 10 gp or 3 rolls on the Rare Mushroom Table. Cavern: choose a gem worth 3d6 x 10 gp or a prism with a random illusionist spell."),
        ("6+", None, "Dungeon: roll on the Dungeon Magic Treasure Table. Caverns: roll on the Caverns Special Item Table. Fungal Grottoes: choose roll on the Dungeon Magic Treasure Table or roll on the Fungal Grottoes Rare Item Table."),
    ]
    assert [(row["roll"], row["items"][0]) for row in _rows("dungeon_magic_treasure_table")] == [
        ("1", "Wand of Sleep (3 charges)"),
        ("2", "Ring of Teleportation"),
        ("3", "Fools' Gold"),
        ("4", "Magic Weapon (+1 Attack)"),
        ("5", "Potion of Healing"),
        ("6", "Fireball Staff (2 charges)"),
    ]
    magic_rows = {row["roll"]: row for row in _rows("dungeon_magic_treasure_table")}
    assert "Only wizards, illusionists and elves may use it" in magic_rows["1"]["result"]
    assert "automatically pass a Defense roll" in magic_rows["2"]["result"]
    assert "automatically bribe the next Foe" in magic_rows["3"]["result"]
    assert magic_rows["4"]["weapon_type_roll"] == "d6"
    assert "bow with 12 arrows" in magic_rows["4"]["result"]
    assert "free action" in magic_rows["5"]["result"]
    assert magic_rows["6"]["fungal_table"] == "fungal_grottoes_rare_mushroom_table"
    assert "Fungal Grottoes: roll on the Rare Mushroom Table" in magic_rows["6"]["result"]


def test_ee_p162_p163_quest_and_epic_reward_tables_match_pdf_rows() -> None:
    assert [(row["roll"], row["key"]) for row in _rows("quest_table")] == [
        ("1", "bring_head"),
        ("2", "bring_gold"),
        ("3", "bring_alive"),
        ("4", "bring_item"),
        ("5", "peaceful_way"),
        ("6", "slay_all"),
    ]
    quest_rows = {row["roll"]: row for row in _rows("quest_table")}
    assert "Roll on any Boss Monster Table to select a target" in quest_rows["1"]["result"]
    assert "Bringing its head to the Quest-giver's tile completes the Quest" in quest_rows["1"]["result"]
    assert "bring d6x50gp worth of treasure to the Quest-giver's tile" in quest_rows["2"]["result"]
    assert "at least a 20x28 grid area" in quest_rows["6"]["result"]
    assert [(row["roll"], row["key"]) for row in _rows("epic_rewards_table")] == [
        ("1", "book_of_skalitos"),
        ("2", "gold_of_kerrak_dar"),
        ("3", "enchanted_weapon"),
        ("4", "shield_of_warning"),
        ("5", "arrow_of_slaying"),
        ("6", "holy_symbol"),
    ]
    epic_rows = {row["roll"]: row for row in _rows("epic_rewards_table")}
    assert "counts as 1 scroll of each of the 6 basic wizard spells" in epic_rows["1"]["reward"]
    assert "carrier is killed by dragon breath" in epic_rows["1"]["reward"]
    assert "If both dice roll an Explosion" in epic_rows["3"]["reward"]
    assert "hit Foes hit only by magic" in epic_rows["3"]["reward"]
    assert "surprised by Wandering Monsters" in epic_rows["4"]["reward"]
    assert "Foes that ignore shields" in epic_rows["4"]["reward"]
    assert "Roll on any Major Foe Table" in epic_rows["5"]["reward"]
    assert "only by a PC with a bow" in epic_rows["5"]["reward"]
    assert "cleric's body are delivered to the cleric's temple" in epic_rows["6"]["reward"]
    assert "church will pay for an attempt to resurrect" in epic_rows["6"]["reward"]


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
    assert "foot caught in the bear trap" in rows[3]["result"]
    assert "Save at -2 vs. other bear traps or trapdoors" in rows[3]["result"]
    assert "Spears come out of a wall and attack 2 random PCs" in rows[4]["result"]
    assert "bonus from armor applies, but the bonus from a shield does not" in rows[5]["result"]
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
    assert "acid_vial" not in by_key
    catalog = _equipment_shop()
    resale = {entry["match"].lower(): entry for entry in catalog.get("resale_overrides", [])}
    assert resale["acid vial"]["resale_gp"] == 15


def test_ee_p155_caverns_special_events_match_pdf_rows() -> None:
    rows = _rows("caverns_special_events_table")
    assert [(row["roll"], row["key"]) for row in rows] == [
        ("1", "cave_goblin_scout"),
        ("2", "cavemen_explorers"),
        ("3", "morlock_spy"),
        ("4", "trap"),
        ("5", "dwarf_party_gem"),
        ("6", "dwarf_miner"),
    ]
    assert "dwarf miner" in rows[5]["result"]
    assert "d6 gems worth 25gp each" in rows[5]["result"]
    assert "lantern-bearer" not in " ".join(row["result"] for row in rows).lower()


def test_ee_p156_fungal_special_events_match_pdf_rows() -> None:
    rows = _rows("fungal_grottoes_special_events_table")
    assert [(row["roll"], row["key"]) for row in rows] == [
        ("1", "halfling_scout"),
        ("2", "fungal_cavemen"),
        ("3", "spore_cloud"),
        ("4", "trap_rare_item"),
        ("5", "mycelial_warning"),
        ("6", "fungal_merchant"),
    ]
    assert "Equipment list" in rows[5]["result"]
    assert "mushroom monk" in rows[4]["result"]


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
    assert "no value outside of the Caverns section of the current adventure" in rows[2]["result"]
    assert "Bribe Reaction while in the Caverns" in rows[2]["result"]
    assert "Magic Weapon" not in " ".join(row["result"] for row in rows)


def test_ee_p161_fungal_rare_item_table_matches_pdf_rows() -> None:
    rows = _rows("fungal_grottoes_rare_item_table")
    assert [(row["roll"], row["items"][0]) for row in rows] == [
        ("1", "Small gemstone (2d6+2gp) or Leafsteel Armor"),
        ("2", "Xicthul’s Cap"),
        ("3", "Red Death"),
        ("4", "Adventurer’s Dead Body"),
        ("5", "Mushroom Gatherer’s Basket"),
        ("6", "Morel Crusher"),
    ]
    assert "user takes 1 damage" in rows[1]["result"]
    assert "choose the effect when the mushroom is found" in rows[2]["result"]
    assert "When broken" in rows[5]["result"]
    assert "Morale roll at -1" in rows[5]["result"]
    assert "Fungal-hilted magic weapon" not in " ".join(row["result"] for row in rows)


def test_ee_p159_rare_mushroom_table_matches_pdf_rows() -> None:
    rows = _rows("fungal_grottoes_rare_mushroom_table")
    assert [(row["roll"], row["items"][0]) for row in rows] == [
        ("1", "Slumber Amanita"),
        ("2", "Puffball Smokebomb"),
        ("3", "Brown Cap Delight"),
        ("4", "Phoenix Mushroom"),
        ("5", "Purple Truffle"),
        ("6", "Healer's Chanterelle"),
    ]
    assert "+Tier bonus when casting the Sleep spell" in rows[0]["result"]
    assert "flee a combat encounter without receiving any attacks" in rows[1]["result"]
    assert "counts as 1 Food Ration" in rows[2]["result"]
    assert "3 tiles" in rows[3]["result"]
    assert "Halflings may reroll" in rows[4]["result"]
    assert "heal all damage" in rows[5]["result"]


def test_ee_p165_p166_environment_trap_tables_use_pdf_trap_keys() -> None:
    assert [(row["roll"], row["trap_key"]) for row in _rows("caverns_trap_table")] == [
        ("1", "stalactite"),
        ("2", "rockslide"),
        ("3", "hidden_pit"),
        ("4", "swinging_log"),
        ("5", "toxic_mushrooms"),
        ("6", "rolling_boulder"),
    ]
    cavern_rows = {row["roll"]: row for row in _rows("caverns_trap_table")}
    assert "Loose stones are dislodged" in cavern_rows["2"]["result"]
    assert "needs the help of another to climb out" in cavern_rows["3"]["result"]
    assert "large wooden log, bound with vines" in cavern_rows["4"]["result"]
    assert "Rogues and foresters add +L" in cavern_rows["5"]["result"]
    assert "Mushroom" in cavern_rows["5"]["result"] and "immune" in cavern_rows["5"]["result"].lower()
    assert "1d3 PCs in Marching Order" in cavern_rows["6"]["result"]
    assert "That opening is now blocked and cannot be accessed" in cavern_rows["6"]["result"]
    assert [(row["roll"], row["trap_key"]) for row in _rows("fungal_grottoes_trap_table")] == [
        ("1", "sleep_spores"),
        ("2", "spore_cloud"),
        ("3", "slime_patch"),
        ("4", "mycelium_snare"),
        ("5", "shrieking_mushroom"),
        ("6", "cordyceps_trap"),
    ]
    fungal_rows = {row["roll"]: row for row in _rows("fungal_grottoes_trap_table")}
    assert "whole party dies" in fungal_rows["1"]["notes"]
    assert "Halflings and barbarians add +L" in fungal_rows["2"]["notes"]
    assert "Wandering Monsters" in fungal_rows["3"]["result"]
    assert "player's choice" in fungal_rows["4"]["result"]
    assert "forester (druid, ranger" in fungal_rows["5"]["result"]
    assert "rise as an undead Boss Monster" in fungal_rows["6"]["result"]


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


def test_ee_p167_dungeon_vermin_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["vermin"]}

    rats = by_name["Rats"]
    assert rats["count"] == "3d6"
    assert rats["level_delta"] == 0
    assert rats["max_level"] == 4
    assert rats["no_treasure"] is True
    assert rats["post_combat_effects"][0]["type"] == "infection"
    assert rats["post_combat_effects"][0]["chance"] == "1-in-6"
    assert "Food ration" in rats["notes"]
    assert any(r["roll"] == "1-3" and r["key"] == "flee" for r in rats["reactions"])
    assert any(r["roll"] == "4-6" and r["key"] == "fight" for r in rats["reactions"])

    bats = by_name["Vampire Bats"]
    assert bats["count"] == "3d6"
    assert bats["level_delta"] == 0
    assert bats["max_level"] == 3
    assert bats["no_treasure"] is True
    assert any(m["type"] == "spellcasting_penalty" and m["value"] == -1 for m in bats["combat_modifiers"])
    assert "animals, not undead" in bats["notes"]
    assert any(r["roll"] == "1-3" and r["key"] == "flee" for r in bats["reactions"])

    swarmlings = by_name["Goblin Swarmlings"]
    assert swarmlings["count"] == "2d6"
    assert swarmlings["level_delta"] == 1
    assert swarmlings["max_level"] == 4
    assert swarmlings["treasure_modifier"] == -1
    assert swarmlings["morale_modifier"] == -1
    assert any(m["attacker_class"] == "dwarf" for m in swarmlings["combat_modifiers"])
    assert any(r["roll"] == "4" and r["key"] == "bribe" and r["gold_per_foe"] == 5 for r in swarmlings["reactions"])

    centipedes = by_name["Giant Centipedes"]
    assert centipedes["count"] == "d6"
    assert centipedes["level_delta"] == 1
    assert centipedes["max_level"] == 3
    assert centipedes["no_treasure"] is True
    assert centipedes["on_hit_effects"][0]["type"] == "poison"
    assert centipedes["on_hit_effects"][0]["save_level"] == 2
    assert any(r["roll"] == "2-3" and r["key"] == "flee_if_outnumbered" for r in centipedes["reactions"])

    frogs = by_name["Vampire Frogs"]
    assert frogs["count"] == "d6"
    assert frogs["level_delta"] == 3
    assert frogs["max_level"] == 5
    assert frogs["treasure_modifier"] == -1
    assert any(r["roll"] == "2-3" and r["key"] == "blood_offering" for r in frogs["reactions"])
    assert any(r["roll"] == "5-6" and r["key"] == "fight_to_death" for r in frogs["reactions"])

    skeletal = by_name["Skeletal Rats"]
    assert skeletal["count"] == "2d6"
    assert skeletal["level_delta"] == 2
    assert skeletal["max_level"] == 5
    assert skeletal["no_treasure"] is True
    assert "sleep" in skeletal["immunities"]
    assert "ranged_weapons" in skeletal["immunities"]
    assert any(v["type"] == "crushing_weapons" for v in skeletal["vulnerabilities"])
    assert any(v["type"] == "holy_water" and v["kills"] == 2 for v in skeletal["vulnerabilities"])
    assert any(r["roll"] == "1-2" and r["key"] == "flee" for r in skeletal["reactions"])


def test_ee_p168_dungeon_minions_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["minions"]}

    skel_zom = by_name["Skeletons/Zombies"]
    assert skel_zom["count"] == "d6+2"
    assert skel_zom["count_formula"] == "1-3: d6+2 Skeletons, 4-6: d6 Zombies"
    assert skel_zom["level_delta"] == 2
    assert skel_zom["max_level"] == 6
    assert skel_zom["no_treasure"] is True
    assert skel_zom["never_test_morale"] is True
    assert "sleep" in skel_zom["immunities"]
    assert any(v["type"] == "holy_water" for v in skel_zom["vulnerabilities"])
    assert skel_zom["reactions"][0]["key"] == "fight_to_death"

    goblins = by_name["Goblins"]
    assert goblins["count"] == "d6+3"
    assert goblins["level_delta"] == 2
    assert goblins["max_level"] == 6
    assert goblins["treasure_modifier"] == -1
    assert goblins["surprise_chance"] == "1-in-6"
    assert any(m["attacker_class"] == "dwarf" for m in goblins["combat_modifiers"])
    assert any(r["roll"] == "2-3" and r["key"] == "bribe" and r["gold_per_foe"] == 5 for r in goblins["reactions"])

    hobgoblins = by_name["Hobgoblins"]
    assert hobgoblins["count"] == "d6"
    assert hobgoblins["level_delta"] == 3
    assert hobgoblins["treasure_modifier"] == 1
    assert any(r["roll"] == "2-3" and r["key"] == "bribe" and r["gold_per_foe"] == 10 for r in hobgoblins["reactions"])
    assert any(r["roll"] == "6" and r["key"] == "fight_to_death" for r in hobgoblins["reactions"])

    orcs = by_name["Orcs"]
    assert orcs["count"] == "d6+1"
    assert orcs["level_delta"] == 3
    assert orcs["max_level"] == 10
    assert any(m["attacker_class"] == "elf" for m in orcs["combat_modifiers"])
    assert any(m["type"] == "fear_magic" for m in orcs["combat_modifiers"])
    assert orcs["loot_special"]["no_magic_items"] is True
    assert orcs["loot_special"]["replacement"] == "d6xd6gp"
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" for r in orcs["reactions"])

    trolls = by_name["Trolls"]
    assert trolls["count"] == "d3"
    assert trolls["level_delta"] == 4
    assert trolls["max_level"] == 7
    assert any(m["defender_class"] == "halfling" for m in trolls["combat_modifiers"])
    assert trolls["regeneration"]["revival_chance"] == "2-in-6"
    assert "slashing_hack" in trolls["regeneration"]["blocked_by"]
    assert "dwarves" in trolls["notes"].lower()

    mushrooms = by_name["Mushroom Men"]
    assert mushrooms["count"] == "2d6"
    assert mushrooms["level_delta"] == 2
    assert mushrooms["max_level"] == 10
    assert mushrooms["on_hit_effects"][0]["save_level"] == 3
    assert mushrooms["on_hit_effects"][0]["save_modifier"]["halfling"] == "L"
    assert "mushroom" in mushrooms["on_hit_effects"][0]["immune_classes"]
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" and r["gold_per_foe"] == 6 for r in mushrooms["reactions"])


def test_ee_p169_dungeon_weird_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["weird"]}

    minotaur = by_name["Minotaur"]
    assert minotaur["life"] == "Tier+3"
    assert minotaur["level_delta"] == 4
    assert minotaur["attacks"] == 2
    assert any(m["type"] == "charge" for m in minotaur["combat_modifiers"])
    assert any(m["type"] == "luck_restriction" and m["blocked_class"] == "halfling" for m in minotaur["combat_modifiers"])
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" and r["gold"] == 60 for r in minotaur["reactions"])

    iron_eater = by_name["Iron Eater"]
    assert iron_eater["life"] == "Tier+3"
    assert iron_eater["level_delta"] == 2
    assert iron_eater["attacks"] == 3
    assert iron_eater["no_treasure"] is True
    destroy = iron_eater["on_hit_effects"][0]
    assert destroy["type"] == "destroy_metal_items"
    assert destroy["damage"] == 0
    assert destroy["priority_order"] == ["armor", "shield", "main_weapon", "3d6gp"]
    assert any(r["roll"] == "2-3" and r["key"] == "bribe" and r["no_fools_gold"] is True for r in iron_eater["reactions"])

    chimera = by_name["Chimera"]
    assert chimera["life"] == "Tier+5"
    assert chimera["level_delta"] == 4
    assert "chaos" in chimera["tags"]
    breath = chimera["special_attacks"][0]
    assert breath["type"] == "fire_breath"
    assert breath["chance"] == "2-in-6"
    assert breath["save_level"] == 4
    assert any(r["roll"] == "1" and r["key"] == "bribe" and r["gold"] == 50 for r in chimera["reactions"])

    catoblepas = by_name["Catoblepas"]
    assert catoblepas["life"] == "Tier+3"
    assert catoblepas["level_delta"] == 3
    assert catoblepas["treasure_modifier"] == 1
    gaze = catoblepas["encounter_start_effects"][0]
    assert gaze["type"] == "death_gaze"
    assert gaze["save_level"] == 4
    assert any(r["roll"] == "1" and r["key"] == "flee" for r in catoblepas["reactions"])

    spider = by_name["Giant Spider"]
    assert spider["life"] == "Tier+2"
    assert spider["level_delta"] == 4
    assert spider["attacks"] == 2
    assert spider["treasure_rolls"] == 2
    assert spider["on_hit_effects"][0]["save_level"] == 3
    web = spider["combat_restrictions"][0]
    assert web["type"] == "web_prevents_flee"
    assert "fireball_cast" in web["unblock_methods"]
    assert "torch_spent" in web["unblock_methods"]
    assert spider["reactions"][0]["key"] == "fight"

    gremlins = by_name["Invisible Gremlins"]
    assert gremlins["is_event"] is True
    assert gremlins["cannot_be_final_boss"] is True
    assert gremlins["attacks"] == 0
    steal = gremlins["event_effects"][0]
    assert steal["type"] == "steal_items"
    assert steal["count"] == "d6+3"
    assert steal["steal_all_reward"] == "1_clue"
    assert "gremlin_repellant" in steal["protected_by"]
    assert gremlins["reactions"][0]["key"] == "ignore"


def test_ee_p170_dungeon_boss_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["boss"]}

    mummy = by_name["Mummy"]
    assert mummy["life"] == "Tier+3"
    assert mummy["level_delta"] == 4
    assert mummy["attacks"] == 2
    assert mummy["treasure_modifier"] == 2
    assert mummy["never_test_morale"] is True
    assert "sleep" in mummy["immunities"]
    assert mummy["on_kill_effects"][0]["type"] == "turn_to_mummy"
    fire = next(v for v in mummy["vulnerabilities"] if v["type"] == "fire")
    assert fire["fire_attacks_bonus"] == 2
    assert mummy["reactions"][0]["key"] == "fight_to_death"

    orc_brute = by_name["Orc Brute"]
    assert orc_brute["life"] == "Tier+4"
    assert orc_brute["level_delta"] == 4
    assert orc_brute["treasure_modifier"] == 1
    assert any(m["attacker_class"] == "elf" for m in orc_brute["combat_modifiers"])
    assert orc_brute["loot_special"]["replacement"] == "d6xd6gp"
    assert any(r["roll"] == "1" and r["key"] == "bribe" and r["gold"] == 50 for r in orc_brute["reactions"])

    ogre = by_name["Ogre"]
    assert ogre["life"] == "Tier+4"
    assert ogre["level_delta"] == 4
    assert ogre["damage_per_attack"] == "Tier+1"
    assert any(r["roll"] == "1" and r["key"] == "bribe" and r["gold"] == 30 for r in ogre["reactions"])
    assert any(r["roll"] == "4-6" and r["key"] == "fight_to_death" for r in ogre["reactions"])

    medusa = by_name["Medusa"]
    assert medusa["life"] == "Tier+3"
    assert medusa["level_delta"] == 3
    assert medusa["treasure_modifier"] == 1
    petrify = medusa["encounter_start_effects"][0]
    assert petrify["type"] == "petrification_gaze"
    assert petrify["timing"] == "beginning_of_encounter_before_ranged"
    assert petrify["save_modifier"]["rogue"] == "+1/2L"
    assert any(r["roll"] == "1" and r["key"] == "bribe" and r["gold"] == "6d6" for r in medusa["reactions"])
    assert any(r["roll"] == "2" and r["key"] == "quest" for r in medusa["reactions"])

    chaos_lord = by_name["Chaos Lord"]
    assert chaos_lord["life"] == "Tier+3"
    assert chaos_lord["level_delta"] == 5
    assert chaos_lord["attacks"] == 3
    assert chaos_lord["treasure_rolls"] == 2
    assert chaos_lord["treasure_modifier"] == 1
    assert chaos_lord["clue_chance"] == "2-in-6"
    assert "chaos" in chaos_lord["tags"]
    powers = {p["key"] for p in chaos_lord["random_powers"]["powers"]}
    assert powers == {"no_power", "evil_eye", "energy_drain", "hellfire_blast"}
    assert any(r["roll"] == "1" and r["key"] == "flee_if_outnumbered" for r in chaos_lord["reactions"])

    dragon = by_name["Young Dragon"]
    assert dragon["life"] == "Tier+4"
    assert dragon["level_delta"] == 5
    assert dragon["treasure_rolls"] == 3
    assert dragon["treasure_modifier"] == 1
    assert "sleep" in dragon["immunities"]
    assert dragon["never_wandering"] is True
    breath = dragon["breath_weapon"]
    assert breath["save_level"] == 6
    assert breath["damage"] == 2
    assert breath["chance"] == "1-2_on_d6"
    assert any(r["roll"] == "1" and r["key"] == "sleep" for r in dragon["reactions"])
    assert any(
        r["roll"] == "2-3" and r["key"] == "bribe" and r["gold"] == "all_min_100gp_or_magic_item"
        for r in dragon["reactions"]
    )
    assert any(r["roll"] == "4" and r["key"] == "quest" for r in dragon["reactions"])


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
        "Rat Men of the Deep",
        "Cave Orcs",
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


def test_ee_p171_p174_caverns_vermin_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["caverns_vermin"]}

    echo_bats = by_name["Echo Bats"]
    assert echo_bats["count"] == "2d6"
    assert echo_bats["level_delta"] == 1
    assert echo_bats["max_level"] == 4
    assert echo_bats["morale_modifier"] == 1
    assert echo_bats["no_treasure"] is True
    assert any(
        r["key"] == "blood_offering" and r["roll"] == "3-5"
        for r in echo_bats["reactions"]
    ), "Echo Bats reactions: 3-5 Blood Offering"
    assert "Echo rule" in echo_bats["notes"]
    assert "increase their L by 1" in echo_bats["notes"]

    mud = by_name["Mud Centipedes"]
    assert mud["count"] == "2d6+1"
    assert mud["level_delta"] == 0
    assert mud["max_level"] == 4
    assert mud["no_treasure"] is True
    assert "always Fight to protect their eggs" in mud["notes"]

    cockroaches = by_name["Vengeance Cockroaches"]
    assert cockroaches["count"] == "3d6"
    assert cockroaches["level_delta"] == 1
    assert cockroaches["max_level"] == 3
    assert "sleep" in cockroaches["immunities"]
    assert "to those encountered" in cockroaches["notes"]
    assert any(r["key"] == "bribe_food" and r["roll"] == "3" for r in cockroaches["reactions"])

    stalactomimics = by_name["Stalactomimics"]
    assert stalactomimics["count"] == "d6+1"
    assert stalactomimics["level_delta"] == 2
    assert "sleep" in stalactomimics["immunities"]
    assert "poison" in stalactomimics["immunities"]
    assert "plummeting on their victims" in stalactomimics["notes"]
    assert "attacks only once" in stalactomimics["notes"]
    assert "always surprising the PCs" in stalactomimics["notes"]

    toads = by_name["Screaming Toads"]
    assert toads["count"] == "d6+2"
    assert toads["level_delta"] == 3
    assert toads["morale_modifier"] == 1
    assert toads["no_treasure"] is True
    assert "spellcasting" in toads["notes"]
    assert "at the end of the encounter" in toads["notes"]
    assert any(r["key"] == "bribe_food" and r["roll"] == "3" for r in toads["reactions"])

    spiders = by_name["Red Cave Spiders"]
    assert spiders["count"] == "d6"
    assert spiders["level_delta"] == 2
    assert spiders["morale_modifier"] == -1
    assert "poison" in spiders["immunities"]
    # 'poison' tag is intentionally absent: the paralysis mechanic is NOT a standard
    # poison save — it is stored in on_damage_effects and must not trigger _resolve_poison_rider
    assert "poison" not in spiders["tags"]
    assert "roll d6, 1-3 arm, 4-6 leg" in spiders["notes"]
    assert "paralyzed arm" in spiders["notes"]
    assert "paralyzed leg cannot flee" in spiders["notes"]
    assert "Healing or Blessing removes the paralysis" in spiders["notes"]
    assert "delicacy" in spiders["notes"]
    assert any(r["key"] == "fight_to_death" and r["roll"] == "5-6" for r in spiders["reactions"])
    # Bribe reactions on food-only monsters must use bribe_food (matches engine reaction_tables)
    cockroach = by_name["Vengeance Cockroaches"]
    assert any(r["key"] == "bribe_food" and r["roll"] == "3" for r in cockroach["reactions"])
    toad = by_name["Screaming Toads"]
    assert any(r["key"] == "bribe_food" and r["roll"] == "3" for r in toad["reactions"])


def test_ee_p171_p174_caverns_minions_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["caverns_minions"]}

    morlocks = by_name["Morlocks"]
    assert morlocks["count"] == "d6+1"
    assert morlocks["level_delta"] == 3
    assert morlocks["morale_modifier"] == -1
    assert any(
        m["type"] == "light_weakness" and m["defender_bonus"] == 2
        for m in morlocks["combat_modifiers"]
    ), "Morlocks: light_weakness +2 Defense modifier"
    assert "lantern" in morlocks["notes"] or "light source" in morlocks["notes"]
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" for r in morlocks["reactions"])
    assert any(r["roll"] == "3" and r["key"] == "offer_information" for r in morlocks["reactions"])

    goblins = by_name["Cave Goblins"]
    assert goblins["count"] == "d6+1"
    assert goblins["level_delta"] == 2
    assert goblins["max_level"] == 5
    assert goblins["morale_modifier"] == -1
    assert goblins["treasure_modifier"] == -1
    assert goblins["surprise_chance"] == "2-in-6"
    assert any(
        m["type"] == "heavy_armor_bonus" and m["defender_bonus"] == 1
        for m in goblins["combat_modifiers"]
    ), "Cave Goblins: Heavy Armor +1 Defense"
    assert "poor quality clubs" in goblins["notes"]
    assert any(r["roll"] == "1" and r["key"] == "flee" for r in goblins["reactions"])

    skeletons = by_name["Cave Skeletons"]
    assert skeletons["count"] == "2d6"
    assert skeletons["level_delta"] == 2
    assert skeletons["never_test_morale"] is True
    assert skeletons["surprise_chance"] == "1-in-6"
    assert "sleep" in skeletons["immunities"]
    assert any(v["type"] == "crushing_weapons" and v["modifier"] == 1 for v in skeletons["vulnerabilities"])
    assert any(v["type"] == "holy_water" and v["kills"] == 2 for v in skeletons["vulnerabilities"])
    assert "camouflage" in skeletons["notes"]
    assert "pickaxes" in skeletons["notes"]
    assert skeletons["reactions"][0]["key"] == "fight_to_death"

    rat_men = by_name["Rat Men of the Deep"]
    assert rat_men["count"] == "d6+1"
    assert rat_men["level_delta"] == 2
    assert rat_men["opening_ranged_attack"]["level"] == "HCL+3"
    assert rat_men["opening_ranged_attack"]["weapon"] == "crossbow"
    assert any(m["type"] == "shield_bypass" for m in rat_men["combat_modifiers"])
    assert "crossbow" in rat_men["notes"]
    assert "flails" in rat_men["notes"]
    assert "shield" in rat_men["notes"]
    assert any(r["roll"] == "1-3" and r["key"] == "bribe" for r in rat_men["reactions"])

    cave_orcs = by_name["Cave Orcs"]
    assert cave_orcs["count"] == "d6+1"
    assert cave_orcs["level_delta"] == 3
    charge = next(m for m in cave_orcs["combat_modifiers"] if m["type"] == "charge")
    assert charge["first_turn_defense_penalty"] == -1
    heavy = next(m for m in cave_orcs["combat_modifiers"] if m["type"] == "heavy_armor_bonus")
    assert heavy["turn_from"] == 2
    assert heavy["defender_bonus"] == 1
    assert "charge" in cave_orcs["notes"]
    assert "Heavy Armor" in cave_orcs["notes"]
    assert any(r["roll"] == "1-3" and r["key"] == "buy_weapons" for r in cave_orcs["reactions"])

    cavemen = by_name["Cavemen"]
    assert cavemen["count"] == "d6+3"
    assert cavemen["level_delta"] == 2
    assert cavemen["max_level"] == 5
    assert cavemen["no_treasure"] is True
    assert cavemen["weapon"] == "two-handed clubs"
    assert any(t["type"] == "fire_kill" for t in cavemen["morale_triggers"])
    assert "fire-based attack" in cavemen["notes"]
    assert "once per encounter" in cavemen["notes"]
    assert any(r["roll"] == "1" and r["key"] == "flee" for r in cavemen["reactions"])
    assert any(r["roll"] == "2-3" and r["key"] == "bribe" for r in cavemen["reactions"])


def test_ee_p171_p174_caverns_weird_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["caverns_weird"]}

    drillworm = by_name["Drillworm"]
    assert drillworm["life"] == "HCL+3"
    assert drillworm["level_delta"] == 4
    assert drillworm["treasure_rolls"] == 2
    assert "sleep" in drillworm["immunities"]
    assert drillworm["damage_per_attack"] == "Tier"
    assert "3-in-6" in drillworm["entry_roll"]["description"]
    item_loss = drillworm["on_defense_roll_1_effects"][0]
    assert item_loss["type"] == "item_loss"
    assert item_loss["non_magic_fate"] == "destroyed"
    assert item_loss["magic_fate"] == "retrieved after combat"
    assert "shield" in item_loss["targets"]
    assert drillworm["reactions"][0]["key"] == "fight_to_death"

    wraith = by_name["Cavern Wraith"]
    assert wraith["life"] == "HCL+2"
    assert wraith["life_minimum"] == 4
    assert wraith["level_delta"] == 3
    assert wraith["never_test_morale"] is True
    assert wraith["treasure_rolls"] == 2
    assert "sleep" in wraith["immunities"]
    assert "poison" in wraith["immunities"]
    hw = next(v for v in wraith["vulnerabilities"] if v["type"] == "holy_water")
    assert hw["damage"] == 2
    drain = wraith["per_turn_effects"][0]
    assert drain["type"] == "life_drain"
    assert drain["trigger"] == "not_hit_this_turn"
    assert drain["damage"] == 1
    assert "not hit" in wraith["notes"]
    assert any(r["key"] == "blood_offering" and r["roll"] == "2-3" for r in wraith["reactions"])

    sludge = by_name["Cavern Sludge"]
    assert sludge["life"] == "Tier+3"
    assert sludge["level_delta"] == 2
    assert sludge["attacks_scope"] == "per_pc"
    assert sludge["never_test_morale"] is True
    assert sludge["treasure_rolls"] == 1
    assert sludge["surprise_chance"] == "4-in-6"
    assert "sleep" in sludge["immunities"]
    lightning = next(v for v in sludge["vulnerabilities"] if v["type"] == "lightning")
    assert lightning["bonus_damage"] == 2
    assert any(r["type"] == "destruction_at_L0" for r in sludge["special_rules"])
    assert "animals and hirelings" in sludge["notes"]
    assert sludge["reactions"][0]["key"] == "fight_to_death"

    minosaur = by_name["Minosaur"]
    assert minosaur["life"] == "HCL+4"
    assert minosaur["level_delta"] == 4
    assert minosaur["attacks"] == 3
    assert minosaur["weapon"] == "two-handed weapon"
    lvl_up = next(r for r in minosaur["special_rules"] if r["type"] == "level_increase_first_turn")
    assert lvl_up["amount"] == 1
    assert "ranged" in lvl_up["exception"]
    knockdown = next(r for r in minosaur["special_rules"] if r["type"] == "knockdown")
    assert knockdown["recovery_turns"] == 1
    assert "ranged attacks" in minosaur["notes"]
    assert "knocked down" in minosaur["notes"]

    cornucopia = by_name["Cornucopia of Chaos"]
    assert cornucopia["life"] == "Tier+2"
    assert cornucopia["level_delta"] == 6
    assert cornucopia["attacks"] == 0
    assert cornucopia["never_test_morale"] is True
    assert cornucopia["treasure_rolls"] == 2
    assert "sleep" in cornucopia["immunities"]
    gen = cornucopia["special_rules"][0]
    assert gen["type"] == "gremlin_generator"
    assert gen["gremlin_level"] == 2
    assert gen["per_turn"] == "d6"
    assert gen["starting_guard"] == "d6+1"
    assert "lumps of coal" in gen["on_destroy"]
    assert "gremlins" in cornucopia["notes"]
    assert cornucopia["reactions"][0]["key"] == "fight_to_death"

    dragon = by_name["Cave Dragon"]
    assert dragon["life"] == "HCL+4"
    assert dragon["level_delta"] == 5
    assert dragon["attacks"] == 2
    assert dragon["morale_modifier"] == -1
    assert dragon["treasure_rolls"] == 3
    tar = next(e for e in dragon["encounter_start_effects"] if e["type"] == "tar_spit")
    assert tar["level"] == "HCL+3"
    assert tar["roll_1_penalty"] == -1
    assert tar["tar_remove_spell"] == "Water Jet"
    fire = next(c for c in dragon["combat_effects"] if c["type"] == "fire_breath")
    assert fire["save_level"] == "HCL+3"
    assert fire["halfling_reroll"] is True
    assert fire["tar_covered_no_save_bonus"] is True
    assert "Water Jet" in dragon["notes"]
    assert any(r["roll"] == "1" and r["key"] == "flee" for r in dragon["reactions"])
    assert any(r["roll"] == "2-3" and r["key"] == "quest" for r in dragon["reactions"])
    assert any(r["roll"] == "4" and r["key"] == "bribe" for r in dragon["reactions"])


def test_ee_p171_p174_caverns_boss_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["caverns_boss"]}

    manataur = by_name["Manataur"]
    assert manataur["life"] == "HCL+3"
    assert manataur["attacks"] == 3
    assert manataur["level_delta"] == 4
    assert manataur["treasure_modifier"] == 1
    assert manataur["weapon"] == "two-handed axe"
    assert any(r["type"] == "magic_absorption" for r in manataur["special_rules"])
    assert "scrolls or items" in manataur["notes"]
    assert "adds +1 to its Life" in manataur["notes"]
    assert any(r["roll"] == "1-4" and r["key"] == "bribe" for r in manataur["reactions"])

    champion = by_name["Caveman Champion"]
    assert champion["life"] == "HCL+3"
    assert champion["attacks"] == 4
    assert champion["level_delta"] == 4
    assert champion["morale_modifier"] == 1
    assert champion["weapon"] == "two-handed club"
    assert any(r["roll"] == "1-2" and r["key"] == "challenge_of_champions" for r in champion["reactions"])
    assert any(r["roll"] == "3" and r["key"] == "bribe" for r in champion["reactions"])

    ogre = by_name["Hoary Ogre of the Caverns"]
    assert ogre["life"] == "HCL+3"
    assert ogre["attacks"] == 4
    assert ogre["level_delta"] == 4
    assert ogre["treasure_modifier"] == 1
    battle_cry = next(e for e in ogre["encounter_start_effects"] if e["type"] == "battle_cry")
    assert battle_cry["save_level"] == 4
    assert battle_cry["save_type"] == "fear"
    assert battle_cry["effect"] == "no_exploding_attacks"
    assert "paladin" in battle_cry["immune_classes"]
    assert any(m["type"] == "racial_defense_bonus" and m["defender_class"] == "halfling" for m in ogre["combat_modifiers"])
    assert "battle cry" in ogre["notes"]
    assert "Paladins are immune" in ogre["notes"]
    assert "Halflings" in ogre["notes"]

    werebear = by_name["Cavern Werebear"]
    assert werebear["life"] == "HCL+4"
    assert werebear["level_delta"] == 3
    assert werebear["morale_modifier"] == 1
    assert werebear["regeneration"]["amount"] == 1
    assert werebear["regeneration"]["interval_turns"] == 3
    assert any(v["type"] == "silver_weapons" for v in werebear["vulnerabilities"])
    assert any(r["type"] == "non_contagious" for r in werebear["special_rules"])
    assert "every 3 turns" in werebear["notes"]
    assert "not contagious" in werebear["notes"]
    assert any(r["roll"] == "6" and r["key"] == "fight_to_death" for r in werebear["reactions"])

    siren = by_name["Land Siren"]
    assert siren["life"] == "HCL"
    assert siren["life_minimum"] == 3
    assert siren["level_delta"] == 5
    assert siren["treasure_rolls"] == 2
    sleep_song = next(e for e in siren["encounter_start_effects"] if e["type"] == "sleep_song")
    assert sleep_song["save_level"] == "HCL+2"
    assert sleep_song["halfling_reroll"] is True
    assert sleep_song["attack_bonus_per_sleeping_pc"] == 1
    sleeping_rules = next(r for r in siren["special_rules"] if r["type"] == "sleeping_pc_rules")
    assert sleeping_rules["wake_action_turns"] == 1
    assert sleeping_rules["revived_attack_penalty"] == -1
    glands = next(r for r in siren["special_rules"] if r["type"] == "loot_glands")
    assert glands["value"] == "d6x5gp"
    assert "no Defense roll" in siren["notes"]
    assert any(r["roll"] == "1-4" and r["key"] == "quest" for r in siren["reactions"])

    bear = by_name["Fire Bear"]
    assert bear["life"] == "HCL+4"
    assert bear["level_delta"] == 2
    assert bear["attacks"] == 2
    assert bear["never_test_morale"] is True
    assert bear["treasure_rolls"] == 2
    breath = next(a for a in bear["special_attacks"] if a["type"] == "fire_breath")
    assert breath["level"] == "HCL+3"
    assert breath["damage"] == 2
    assert breath["timing"] == "first_turn"
    assert breath["retrigger"] == "after_pc_fire_attack"
    assert "HCL+3" in bear["notes"]
    assert "2 claw attacks" in bear["notes"]
    assert bear["reactions"][0]["key"] == "fight_to_death"


def test_ee_p175_p178_fungal_grottoes_vermin_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fungal_grottoes_vermin"]}

    mites = by_name["Spore Mites"]
    assert mites["count"] == "2d6"
    assert mites["level_delta"] == 0
    assert mites["max_level"] == 3
    assert mites["no_treasure"] is True
    hit_eff = mites["on_hit_effects"][0]
    assert hit_eff["save_level"] == 2
    assert hit_eff["attack_penalty"] == -1
    assert hit_eff["cumulative"] is False
    assert "coughing" in mites["notes"]

    maggots = by_name["Glowmaggots"]
    assert maggots["count"] == "d6"
    assert maggots["level_delta"] == 0
    assert maggots["max_level"] == 2
    assert maggots["no_treasure"] is True
    biolum = next(r for r in maggots["special_rules"] if r["type"] == "bioluminescence")
    assert "illuminates" in biolum["description"]
    edible = next(r for r in maggots["special_rules"] if r["type"] == "edible")
    assert edible["food_value"] == 1
    assert edible["save_level"] == 1
    assert edible["save_fail_damage"] == 1
    light = next(r for r in maggots["special_rules"] if r["type"] == "slain_light_source")
    assert light["duration_rooms"] == 3
    assert light["duration_minutes"] == 30
    assert any(r["roll"] == "1-3" and r["key"] == "ignore" for r in maggots["reactions"])

    leeches = by_name["Fungus Leeches"]
    assert leeches["count"] == "d6+1"
    assert leeches["level_delta"] == 1
    assert leeches["max_level"] == 4
    assert leeches["no_treasure"] is True
    assert "poison" in leeches["immunities"]
    leech_hit = leeches["on_hit_effects"][0]
    assert leech_hit["save_level"] == 4
    assert leech_hit["damage"] == 1
    assert leech_hit["save_modifier"]["halfling"] == "+L"
    assert leech_hit["save_modifier"]["barbarian"] == "+L"
    salt = next(r for r in leeches["special_rules"] if r["type"] == "salt_kills")
    assert salt["kills"] == 2
    assert salt["cost_gp"] == 2
    assert "barbarian" in leeches["notes"]

    gnats = by_name["Myco-Gnats"]
    assert gnats["count"] == "3d6"
    assert gnats["level_delta"] == 0
    assert gnats["max_level"] == 4
    assert gnats["no_treasure"] is True
    distraction = next(m for m in gnats["combat_modifiers"] if m["type"] == "distraction")
    assert distraction["spellcasting_penalty"] == -1
    assert distraction["ranged_attack_penalty"] == -1
    assert any(r["type"] == "fireball_kills_all" for r in gnats["special_rules"])
    assert any(r["roll"] == "1-4" and r["key"] == "flee" for r in gnats["reactions"])

    toads = by_name["Spore Toads"]
    assert toads["count"] == "d6"
    assert toads["level_delta"] == 2
    assert toads["max_level"] == 4
    assert toads["treasure_modifier"] == -1
    spore = toads["per_turn_effects"][0]
    assert spore["type"] == "spore_belch"
    assert spore["chance"] == "1-in-6"
    assert spore["save_level"] == 2
    assert spore["save_type"] == "magic"
    assert spore["defense_penalty"] == -1
    assert "hallucinogenic" in toads["notes"]

    boneworms = by_name["Boneworms"]
    assert boneworms["count"] == "2d6"
    assert boneworms["level_delta"] == 2
    assert boneworms["max_level"] == 5
    assert boneworms["treasure_rolls"] == 1
    assert any(r["type"] == "no_resurrection" for r in boneworms["special_rules"])
    hw_morale = next(r for r in boneworms["special_rules"] if r["type"] == "holy_water_morale")
    assert hw_morale["damage"] == 0
    assert hw_morale["effect"] == "morale_roll"
    assert "cannot be resurrected" in boneworms["notes"]
    assert boneworms["reactions"][0]["key"] == "fight"


def test_ee_p175_p178_fungal_grottoes_minions_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fungal_grottoes_minions"]}

    spore_men = by_name["Spore Men"]
    assert spore_men["count"] == "d6+2"
    assert spore_men["level_delta"] == 2
    assert spore_men["max_level"] == 8
    assert spore_men["treasure_modifier"] == -1
    assert "poison" in spore_men["immunities"]
    hit = spore_men["on_hit_effects"][0]
    assert hit["save_level"] == 3
    assert hit["damage"] == 1
    assert "mushroom" in hit["immune_classes"]
    assert hit["halfling_reroll"] is True
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" for r in spore_men["reactions"])

    pickers = by_name["Halfling Mushroom Pickers"]
    assert pickers["count"] == "d6+1"
    assert pickers["level_delta"] == 1
    assert pickers["max_level"] == 5
    assert pickers["weapon"] == "knives and slings"
    trade = pickers["trade_reaction"]
    assert "rare mushrooms" in trade["goods"]
    assert trade["halfling_discount"] == "10%"
    assert any(r["roll"] == "2-3" and r["key"] == "offer_food" for r in pickers["reactions"])
    assert any(r["roll"] == "4-5" and r["key"] == "trade" for r in pickers["reactions"])

    moldspawn = by_name["Moldspawn"]
    assert moldspawn["count"] == "d6"
    assert moldspawn["level_delta"] == 3
    assert moldspawn["no_treasure"] is True
    assert "poison" in moldspawn["immunities"]
    disease = moldspawn["on_hit_effects"][0]
    assert disease["type"] == "disease"
    assert disease["save_level"] == 2
    assert disease["timing"] == "end_of_encounter"
    assert disease["once_per_encounter"] is True
    assert "not 1 Life per hit" in moldspawn["notes"]
    assert any(r["roll"] == "1-3" and r["key"] == "bribe" for r in moldspawn["reactions"])

    myceliarchs = by_name["Myceliarchs"]
    assert myceliarchs["count"] == "d6+1"
    assert myceliarchs["level_delta"] == 3
    assert myceliarchs["morale_modifier"] == 1
    assert myceliarchs["treasure_modifier"] == 1
    assert "poison" in myceliarchs["immunities"]
    spore_cloud = myceliarchs["encounter_start_effects"][0]
    assert spore_cloud["type"] == "sleep_spore_cloud"
    assert spore_cloud["save_level"] == 3
    assert spore_cloud["effect"] == "skip_next_turn"
    assert "He Who Lies Below" in myceliarchs["notes"]
    assert any(r["roll"] == "2-4" and r["key"] == "blood_offering" for r in myceliarchs["reactions"])

    locusts = by_name["Cave Locusts"]
    assert locusts["count"] == "2d6+2"
    assert locusts["level_delta"] == 0
    assert locusts["max_level"] == 5
    armor = next(m for m in locusts["combat_modifiers"] if m["type"] == "armor_doubles_defense")
    assert armor["light_armor_bonus"] == 2
    assert armor["heavy_armor_bonus"] == 4
    food = locusts["post_combat_effects"][0]
    assert food["type"] == "consume_food"
    assert food["food_lost"] == "d6"
    assert "d6 Food rations" in locusts["notes"]
    assert any(r["roll"] == "1-2" and r["key"] == "ignore" for r in locusts["reactions"])

    knights = by_name["Toadstool Knights"]
    assert knights["count"] == "d6"
    assert knights["level_delta"] == 4
    assert knights["morale_modifier"] == 1
    assert "poison" in knights["immunities"]
    cap = knights["special_rules"][0]
    assert cap["type"] == "fungal_shield_cap"
    assert cap["first_hit_breaks_shield"] is True
    assert cap["knight_survives_first_hit"] is True
    assert cap["warp_wood_destroys_all_caps"] is True
    assert "Warp Wood" in knights["notes"]
    assert any(r["roll"] == "2" and r["key"] == "bribe" for r in knights["reactions"])


def test_ee_p175_p178_fungal_grottoes_weird_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fungal_grottoes_weird"]}

    colossus = by_name["Shroom Colossus"]
    assert colossus["life"] == "Tier+5"
    assert colossus["attacks"] == 3
    assert colossus["level_delta"] == 5
    assert colossus["no_treasure"] is True
    assert colossus["damage_per_attack"] == "Tier"
    assert "sleep" in colossus["immunities"]
    assert any(r["type"] == "corridor_restriction" for r in colossus["special_rules"])
    assert any(r["type"] == "no_resurrection_on_digestion" for r in colossus["special_rules"])
    assert "digested into spores" in colossus["notes"]

    swarm = by_name["Spore Swarm"]
    assert swarm["life"] == "Tier+3"
    assert swarm["level_delta"] == 3
    assert swarm["no_treasure"] is True
    assert "sleep" in swarm["immunities"]
    fire_vuln = swarm["vulnerabilities"][0]
    assert fire_vuln["type"] == "fire"
    assert fire_vuln["modifier"] == "Tier"
    assert swarm["reactions"][0]["key"] == "fight_to_death"

    mimic = by_name["Myco-Mimic"]
    assert mimic["life"] == "Tier+2"
    assert mimic["level_delta"] == 4
    assert mimic["attacks"] == "d3+1"
    assert mimic["treasure_rolls"] == 2
    assert mimic["surprise"] == "always"
    assert "sleep" in mimic["immunities"]
    assert "mushroom-covered treasure chest" in mimic["disguise"]["forms"]
    hit = mimic["on_hit_effects"][0]
    assert hit["save_level"] == 3
    assert hit["effect"] == "paralyzed"
    assert hit["duration_turns"] == 1
    assert hit["halfling_reroll"] is True
    assert "automatic surprise" in mimic["notes"]

    horror = by_name["Hallucinogenic Horror"]
    assert horror["life"] == "Tier+4"
    assert horror["level_delta"] == 3
    assert horror["treasure_modifier"] == 1
    assert horror["never_test_morale"] is True
    assert "sleep" in horror["immunities"]
    halluc = horror["per_turn_effects"][0]
    assert halluc["type"] == "hallucination"
    assert halluc["save_level"] == 3
    assert halluc["effect"] == "attack_ally"
    assert horror["reactions"][0]["key"] == "fight_to_death"

    hydra = by_name["Fungus-infected Hydra"]
    assert hydra["life"] == "Tier+4"
    assert hydra["level_delta"] == 4
    assert hydra["attacks"] == "Tier+4"
    assert hydra["attacks_minimum"] == 1
    assert hydra["treasure_rolls"] == 2
    hydra_rule = next(r for r in hydra["special_rules"] if r["type"] == "hydra_attacks")
    assert hydra_rule["lose_attack_per_life_lost"] is True
    assert hydra_rule["minimum_attacks"] == 1
    regen = next(r for r in hydra["special_rules"] if r["type"] == "head_regeneration")
    assert regen["regrow_turns"] == 2
    assert "fire" in regen["blocked_by"]
    assert any(r["roll"] == "2-3" and r["key"] == "blood_offering" for r in hydra["reactions"])

    phantom = by_name["Spore Phantom"]
    assert phantom["life"] == "Tier+3"
    assert phantom["attacks"] == 2
    assert phantom["level_delta"] == 3
    assert phantom["treasure_modifier"] == 1
    assert phantom["never_test_morale"] is True
    assert "sleep" in phantom["immunities"]
    hw = next(v for v in phantom["vulnerabilities"] if v["type"] == "holy_water")
    assert hw["damage"] == 2
    hit = phantom["on_hit_effects"][0]
    assert hit["save_level"] == 3
    assert hit["timing"] == "end_of_turn"
    druid = next(m for m in phantom["combat_modifiers"] if m["type"] == "attacker_bonus")
    assert druid["attacker_class"] == "druid"
    assert druid["value"] == "L"
    assert "Druids" in phantom["notes"]
    assert phantom["reactions"][0]["key"] == "fight_to_death"


def test_ee_p175_p178_fungal_grottoes_boss_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fungal_grottoes_boss"]}

    tyrant = by_name["Myco-Tyrant"]
    assert tyrant["life"] == "Tier+3"
    assert tyrant["attacks"] == 3
    assert tyrant["morale_modifier"] == 1
    assert tyrant["treasure_rolls"] == 1
    assert "sleep" in tyrant["immunities"]
    assert "poison" in tyrant["immunities"]
    burst = tyrant["encounter_start_effects"][0]
    assert burst["save_level"] == 4
    assert "halfling" in burst["immune_classes"]
    assert "mushroom" in burst["immune_classes"]
    assert tyrant["reactions"][0]["key"] == "fight"

    hag = by_name["Fungus Hag"]
    assert hag["life"] == "Tier+2"
    assert hag["attacks"] == 2
    assert hag["treasure_modifier"] == 1
    assert hag["damage_per_attack"] == "Tier"
    assert "sleep" in hag["immunities"]
    hit = hag["on_hit_effects"][0]
    assert hit["save_level"] == 3
    assert hit["attack_penalty"] == -1
    assert hit["cumulative"] is False
    assert any(r["roll"] == "1" and r["key"] == "blood_offering" for r in hag["reactions"])
    assert any(r["roll"] == "2-3" and r["key"] == "quest" for r in hag["reactions"])

    spore_lord = by_name["Spore Lord"]
    assert spore_lord["life"] == "Tier+3"
    assert spore_lord["attacks"] == 3
    assert spore_lord["treasure_rolls"] == 2
    storm = spore_lord["special_attacks"][0]
    assert storm["type"] == "spore_storm"
    assert storm["timing"] == "first_turn_only"
    assert storm["save_level"] == 5
    assert storm["halfling_reroll"] is True
    assert storm["effect"] == "blinded"
    assert storm["blind_penalty"]["attack"] == -1
    assert storm["blind_penalty"]["defense"] == -1
    assert any(r["roll"] == "2-3" and r["key"] == "bribe" for r in spore_lord["reactions"])

    rot_ogre = by_name["Rot Ogre"]
    assert rot_ogre["life"] == "Tier+4"
    assert rot_ogre["attacks"] == 2
    assert rot_ogre["treasure_rolls"] == 2
    disease = rot_ogre["on_hit_effects"][0]
    assert disease["type"] == "disease"
    assert disease["save_level"] == 3
    assert disease["save_modifier"]["halfling"] == "+L"
    assert disease["save_modifier"]["barbarian"] == "+L"
    assert disease["timing"] == "end_of_combat"
    halfling_def = next(m for m in rot_ogre["combat_modifiers"] if m["type"] == "racial_defense_bonus")
    assert halfling_def["defender_class"] == "halfling"
    assert rot_ogre["reactions"][0]["key"] == "fight_to_death"

    knight = by_name["Caplord Knight"]
    assert knight["life"] == "Tier+4"
    assert knight["attacks"] == 4
    assert "sleep" in knight["immunities"]
    assert "poison" in knight["immunities"]
    assert "sporeblade" in knight["weapon"]
    hit = knight["on_hit_effects"][0]
    assert hit["save_level"] == 3
    assert hit["halfling_reroll"] is True
    deflect = next(r for r in knight["special_rules"] if r["type"] == "armor_deflection")
    assert deflect["chance"] == "2-in-6"
    warp = next(r for r in knight["special_rules"] if r["type"] == "warp_wood_vulnerability")
    assert warp["level_reduction"] == 2
    assert "sporeblade" in warp["destroys"]
    assert "Warp Wood" in knight["notes"]
    assert any(r["roll"] == "1-3" and r["key"] == "trial_of_champions" for r in knight["reactions"])

    dragon = by_name["Fungal Dragon"]
    assert dragon["life"] == "Tier+3"
    assert dragon["attacks"] == 4
    assert dragon["treasure_modifier"] == 2
    assert "sleep" in dragon["immunities"]
    breath = dragon["special_attacks"][0]
    assert breath["type"] == "spore_breath"
    assert breath["chance"] == "2-in-6"
    assert breath["save_level"] == 5
    assert breath["halfling_reroll"] is True
    assert breath["damage"] == 1
    assert any(r["roll"] == "1-3" and r["key"] == "quest" for r in dragon["reactions"])


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


def test_fiendish_foes_monster_table_names_match_pdf_rows() -> None:
    monsters = _monsters()
    assert [row["name"] for row in monsters["fiendish_foes_vermin"]] == [
        "Fiendish Spiders",
        "Stirges",
        "Giant Snakes",
        "Giant Toads",
        "Armored Skeletons",
        "Goatmen",
    ]
    assert [row["name"] for row in monsters["fiendish_foes_minions"]] == [
        "Orc Looters",
        "Cockatrices",
        "Possessed Dwarves",
        "Gnolls",
        "Hobgoblin Blademasters",
        "Chaos Slavers",
    ]
    assert [row["name"] for row in monsters["fiendish_foes_boss"]] == [
        "Fiendish Chaos Lord",
        "Skeletal Demon",
        "Hobgoblin Leader",
        "Wraith",
        "Large Troll",
        "Young Red Dragon",
    ]
    assert [row["name"] for row in monsters["fiendish_foes_weird"]] == [
        "Doppelganger",
        "Scimitar Monster",
        "Green Slime",
        "Acid Cube",
        "Flesh Golem",
        "Lurking Mantlebeast",
    ]


def test_fiendish_foes_vermin_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fiendish_foes_vermin"]}

    spiders = by_name["Fiendish Spiders"]
    assert spiders["count"] == "3d6+3"
    assert spiders["level_delta"] == 0
    assert spiders["treasure_modifier"] == -1
    web = next(r for r in spiders["special_rules"] if r["type"] == "web_entanglement")
    assert "Fireball" in web["description"]
    assert "withdraw" in web["description"]
    hit = spiders["on_hit_effects"][0]
    assert hit["type"] == "poison"
    assert hit["save_level"] == "HCL+2"
    assert hit["timing"] == "end_of_combat"
    vuln = spiders["vulnerabilities"][0]
    assert vuln["type"] == "crushing_weapons"
    assert vuln["modifier"] == 1
    assert "poison" not in spiders["tags"]  # not a standard poison tag; end-of-combat save
    assert spiders["reactions"][0]["key"] == "fight"

    stirges = by_name["Stirges"]
    assert stirges["count"] == "2d6+2"
    assert stirges["level_delta"] == 3
    assert stirges["no_treasure"] is True
    drain = stirges["per_turn_effects"][0]
    assert drain["type"] == "blood_drain"
    assert drain["damage"] == 1
    assert any(r["roll"] == "1-3" and r["key"] == "blood_offering" for r in stirges["reactions"])
    assert any(r["roll"] == "4-6" and r["key"] == "fight" for r in stirges["reactions"])

    snakes = by_name["Giant Snakes"]
    assert snakes["count"] == "d6+4"
    assert snakes["level_delta"] == 2
    assert snakes["treasure_rolls"] == 1
    hit = snakes["on_hit_effects"][0]
    assert hit["save_level"] == "HCL+1"
    assert hit["halfling_reroll"] is True
    assert any(r["roll"] == "1-2" and r["key"] == "ignore" for r in snakes["reactions"])
    assert any(r["roll"] == "3-6" and r["key"] == "fight" for r in snakes["reactions"])

    toads = by_name["Giant Toads"]
    assert toads["count"] == "d6+4"
    assert toads["level_delta"] == 2
    assert toads["no_treasure"] is True
    burst = next(r for r in toads["special_rules"] if r["type"] == "death_burst_poison")
    assert "ranged" in burst["exempt_if"]
    assert burst["save_level"] == "HCL"
    assert any(r["roll"] == "1-3" and r["key"] == "ignore" for r in toads["reactions"])

    skeletons = by_name["Armored Skeletons"]
    assert skeletons["count"] == "2d3+4"
    assert skeletons["level_delta"] == 3
    assert skeletons["treasure_modifier"] == -1
    assert skeletons["never_test_morale"] is True
    assert "sleep" in skeletons["immunities"]
    assert "poison" in skeletons["immunities"]
    crush = next(m for m in skeletons["combat_modifiers"] if m["type"] == "armor_neutralize_crushing_bonus")
    assert "crushing weapons" in crush["description"] and "bonus" in crush["description"]
    arrow = next(m for m in skeletons["combat_modifiers"] if m["type"] == "ranged_penalty")
    assert arrow["value"] == -1
    assert skeletons["reactions"][0]["key"] == "fight_to_death"

    goatmen = by_name["Goatmen"]
    assert goatmen["count"] == "2d3+1"
    assert goatmen["level_delta"] == 3
    assert goatmen["treasure_rolls"] == 1
    assert goatmen["morale_modifier"] == 2
    charge = goatmen["encounter_start_effects"][0]
    assert charge["type"] == "charge"
    assert charge["level_delta_bonus"] == 2
    assert any(r["roll"] == "1" and r["key"] == "bribe" and r["gold_per_foe"] == 30 for r in goatmen["reactions"])
    assert any(r["roll"] == "6" and r["key"] == "fight_to_death" for r in goatmen["reactions"])


def test_fiendish_foes_minions_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fiendish_foes_minions"]}

    looters = by_name["Orc Looters"]
    assert looters["count"] == "d6+6"
    assert looters["level_delta"] == 2
    assert looters["treasure_rolls"] == 3
    assert looters["treasure_modifier"] == -1
    spell_casualty = next(t for t in looters["morale_triggers"] if t["type"] == "spell_casualties")
    assert "spell" in spell_casualty["description"]
    spell_half = next(t for t in looters["morale_triggers"] if t["type"] == "spell_half_strength")
    assert spell_half["modifier"] == -1
    assert any(r["roll"] == "1" and r["key"] == "bribe" and r["gold_per_foe"] == 40 for r in looters["reactions"])
    assert any(r["roll"] == "3-6" and r["key"] == "fight_to_death" for r in looters["reactions"])

    cockatrices = by_name["Cockatrices"]
    assert cockatrices["count"] == "d3+4"
    assert cockatrices["level_delta"] == 3
    assert cockatrices["treasure_rolls"] == 1
    assert cockatrices["never_test_morale"] is True
    petrif = cockatrices["on_hit_effects"][0]
    assert petrif["type"] == "petrification"
    assert petrif["save_level"] == 2
    assert petrif["cure"] == "blessing"
    assert cockatrices["reactions"][0]["key"] == "fight_to_death"

    dwarves = by_name["Possessed Dwarves"]
    assert dwarves["count"] == "d6+3"
    assert dwarves["level_delta"] == 3
    assert dwarves["treasure_rolls"] == 1
    htk = dwarves["special_rules"][0]
    assert htk["type"] == "hard_to_kill"
    assert htk["revival_threshold"] == 3
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" and r["gold_per_foe"] == 30 for r in dwarves["reactions"])
    assert any(r["roll"] == "6" and r["key"] == "fight_to_death" for r in dwarves["reactions"])

    gnolls = by_name["Gnolls"]
    assert gnolls["count"] == "2d3+4"
    assert gnolls["level_delta"] == 3
    assert gnolls["treasure_rolls"] == 1
    assert gnolls["morale_modifier"] == 1
    frenzy = gnolls["combat_modifiers"][0]
    assert frenzy["type"] == "frenzy_vs_wounded"
    assert frenzy["attack_bonus"] == 1
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" and r["gold_per_foe"] == 20 for r in gnolls["reactions"])
    assert any(r["roll"] == "5-6" and r["key"] == "fight_to_death" for r in gnolls["reactions"])

    blademasters = by_name["Hobgoblin Blademasters"]
    assert blademasters["count"] == "2d3+2"
    assert blademasters["level_delta"] == 3
    assert blademasters["treasure_rolls"] == 1
    assert blademasters["treasure_modifier"] == 1
    riposte = blademasters["combat_modifiers"][0]
    assert riposte["type"] == "riposte"
    assert "melee" in riposte["description"]
    assert "1" in riposte["description"]  # rolling 1 triggers counter-attack
    assert "hand weapon" in blademasters["notes"]
    assert any(r["roll"] == "1-3" and r["key"] == "bribe" and r["gold_per_foe"] == 30 for r in blademasters["reactions"])
    assert any(r["roll"] == "6" and r["key"] == "fight_to_death" for r in blademasters["reactions"])
    assert "inferred" in blademasters["notes"]  # truncated PDF text noted

    slavers = by_name["Chaos Slavers"]
    assert slavers["count"] == "2d3+2"
    assert slavers["level_delta"] == 4
    assert slavers["treasure_rolls"] == 2
    assert slavers["morale_modifier"] == 1
    trap = slavers["encounter_start_effects"][0]
    assert trap["type"] == "preset_trap"
    assert trap["trap_level"] == 4
    assert trap["rogue_can_spot"] is True
    assert trap["not_if_wandering"] is True
    assert any(r["roll"] == "1-3" and r["key"] == "bribe" and r["gold_per_foe"] == 40 for r in slavers["reactions"])
    assert any(r["roll"] == "4-6" and r["key"] == "fight" for r in slavers["reactions"])


def test_fiendish_foes_boss_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fiendish_foes_boss"]}

    lord = by_name["Fiendish Chaos Lord"]
    assert lord["life"] == 7
    assert lord["attacks"] == 3
    assert lord["level_delta"] == 3
    assert lord["treasure_rolls"] == 3
    assert "boss" in lord["tags"]
    powers = lord["random_powers"]["powers"]
    evil_eye = next(p for p in powers if p["key"] == "evil_eye")
    assert evil_eye["roll"] == "1-4"
    energy = next(p for p in powers if p["key"] == "energy_drain")
    assert energy["roll"] == "5"
    hellfire = next(p for p in powers if p["key"] == "hellfire_blast")
    assert hellfire["roll"] == "6"
    assert "L5" in hellfire["result"]
    post = lord["post_combat_effects"][0]
    assert post["type"] == "free_slaves"
    assert post["clue_reward"] == 1
    assert post["wandering_monster_roll"] is True
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" and r["gold"] == 200 for r in lord["reactions"])
    assert any(r["roll"] == "3-6" and r["key"] == "fight_to_death" for r in lord["reactions"])

    demon = by_name["Skeletal Demon"]
    assert demon["life"] == 8
    assert demon["attacks"] == 2
    assert demon["level_delta"] == 4
    assert demon["treasure_rolls"] == 3
    assert demon["morale_modifier"] == 1
    assert "undead" in demon["tags"]
    summon = demon["per_turn_effects"][0]
    assert summon["type"] == "summon_reinforcements"
    assert summon["summon_name"] == "Armored Skeletons"
    assert summon["count_per_damage_point"] == 1
    assert any(r["roll"] == "1-2" and r["key"] == "magic_challenge" for r in demon["reactions"])
    assert any(r["roll"] == "6" and r["key"] == "quest" for r in demon["reactions"])

    leader = by_name["Hobgoblin Leader"]
    assert leader["life"] == 8
    assert leader["attacks"] == 2
    assert leader["level_delta"] == 4
    assert leader["treasure_rolls"] == 2
    rattle = leader["special_attacks"][0]
    assert rattle["type"] == "rattleblade_summon"
    assert rattle["chance"] == "3-in-6"
    assert rattle["one_time"] is True
    assert rattle["summon_name"] == "Hobgoblin Blademasters"
    assert any(r["roll"] == "1-3" and r["key"] == "bribe" and r["gold"] == 400 for r in leader["reactions"])
    assert any(r["roll"] == "4-6" and r["key"] == "fight_to_death" for r in leader["reactions"])

    wraith = by_name["Wraith"]
    assert wraith["life"] == 6
    assert wraith["level_delta"] == 4
    assert wraith["treasure_rolls"] == 2
    assert "undead" in wraith["tags"]
    lantern = wraith["encounter_start_effects"][0]
    assert lantern["type"] == "extinguish_lanterns"
    assert lantern["chance"] == "2-in-6"
    drain = wraith["on_hit_effects"][0]
    assert drain["type"] == "level_drain"
    assert drain["save_level"] == 4
    assert drain["levels_lost"] == 1
    restriction = next(r for r in wraith["special_rules"] if r["type"] == "weapon_restriction")
    assert "silvered_weapons" in restriction["allowed"]
    assert "holy_water" in restriction["allowed"]
    assert "two_plus_damage_single_blow" in restriction["allowed"]
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" for r in wraith["reactions"])
    assert any(r["roll"] == "3" and r["key"] == "quest" for r in wraith["reactions"])

    troll = by_name["Large Troll"]
    assert troll["life"] == 7
    assert troll["attacks"] == 2
    assert troll["level_delta"] == 5
    assert troll["treasure_rolls"] == 4
    assert "regeneration" in troll["tags"]
    crush_mod = troll["combat_modifiers"][0]
    assert crush_mod["type"] == "damage_reduction"
    assert crush_mod["weapon_type"] == "crushing"
    assert crush_mod["value"] == -1
    regen = troll["regeneration"]
    assert regen["amount"] == 1
    assert "fire" in regen["suppressed_by"]
    assert "acid" in regen["suppressed_by"]
    assert any(r["roll"] == "1-4" and r["key"] == "bribe" and r["gold"] == 250 for r in troll["reactions"])
    assert any(r["roll"] == "5-6" and r["key"] == "fight_to_death" for r in troll["reactions"])

    dragon = by_name["Young Red Dragon"]
    assert dragon["life"] == 8
    assert dragon["attacks"] == 2
    assert dragon["level_delta"] == 6
    assert dragon["treasure_rolls"] == 4
    assert dragon["treasure_modifier"] == 1
    assert dragon["never_test_morale"] is True
    assert "dragon" in dragon["tags"]
    breath = dragon["special_attacks"][0]
    assert breath["type"] == "fire_breath"
    assert breath["save_level"] == 7
    assert breath["timing"] == "first_turn"
    assert "Never" in dragon["notes"]
    assert any(r["roll"] == "1" and r["key"] == "sleep" for r in dragon["reactions"])
    assert any(r["roll"] == "2-3" and r["key"] == "bribe" and r["gold"] == 300 for r in dragon["reactions"])
    assert any(r["roll"] == "6" and r["key"] == "quest" for r in dragon["reactions"])


def test_fiendish_foes_weird_details_match_pdf_text() -> None:
    monsters = _monsters()
    by_name = {row["name"]: row for row in monsters["fiendish_foes_weird"]}

    doppelganger = by_name["Doppelganger"]
    assert doppelganger["life"] == 5
    assert doppelganger["attacks"] == 1
    assert doppelganger["level_delta"] == 2
    assert doppelganger["treasure_rolls"] == 1
    shapeshift = doppelganger["encounter_start_effects"][0]
    assert shapeshift["type"] == "shapeshift"
    confusion = doppelganger["per_turn_effects"][0]
    assert confusion["type"] == "confusion_save"
    assert confusion["save_level"] == 4
    mimicry = next(r for r in doppelganger["special_rules"] if r["type"] == "mimicry_targeting")
    assert "mimicked PC" in mimicry["description"]
    assert doppelganger["reactions"][0]["key"] == "fight"

    scimitar = by_name["Scimitar Monster"]
    assert scimitar["life"] == 12
    assert scimitar["attacks"] == 2
    assert scimitar["level_delta"] == 5
    assert scimitar["treasure_rolls"] == 2
    assert scimitar["treasure_modifier"] == 1
    assert "sleep" in scimitar["immunities"]
    dwarf = next(r for r in scimitar["special_rules"] if r["type"] == "dwarf_hatred")
    assert "dwarf" in dwarf["description"]
    assert any(r["roll"] == "1-2" and r["key"] == "bribe" and r["gold"] == 250 for r in scimitar["reactions"])
    assert any(r["roll"] == "5-6" and r["key"] == "fight_to_death" for r in scimitar["reactions"])

    slime = by_name["Green Slime"]
    assert slime["life"] == 8
    assert slime["attacks"] == 3
    assert slime["level_delta"] == 3
    assert slime["no_treasure"] is True
    assert slime["never_test_morale"] is True
    disease = slime["on_hit_effects"][0]
    assert disease["type"] == "slime_disease"
    assert disease["save_level"] == 4
    assert disease["halfling_bonus"] == "half_level"
    assert disease["cure"] == "blessing"
    transform = next(r for r in slime["special_rules"] if r["type"] == "infection_transformation")
    assert "green slime" in transform["description"]
    assert slime["reactions"][0]["key"] == "fight_to_death"

    cube = by_name["Acid Cube"]
    assert cube["life"] == 6
    assert cube["attacks"] == 0
    assert cube["level_delta"] == 3
    assert cube["treasure_rolls"] == 3
    assert cube["never_test_morale"] is True
    assert "sleep" in cube["immunities"]
    assert "lightning" in cube["immunities"]
    surprise = cube["encounter_start_effects"][0]
    assert surprise["chance"] == "3-in-6"
    engulf = cube["per_turn_effects"][0]
    assert engulf["type"] == "engulf"
    assert engulf["save_level_base"] == 2
    assert engulf["save_level_if_melee_last_turn"] == 4
    assert cube["reactions"][0]["key"] == "fight_to_death"

    golem = by_name["Flesh Golem"]
    assert golem["life"] == 8
    assert golem["attacks"] == 2
    assert golem["level_delta"] == 4
    assert golem["treasure_rolls"] == 1
    assert golem["morale_modifier"] == 2
    assert "crushing_weapons" in golem["immunities"]
    crush_immune = next(r for r in golem["special_rules"] if r["type"] == "crushing_weapon_immunity")
    assert "crushing" in crush_immune["description"]
    spell_immune = next(r for r in golem["special_rules"] if r["type"] == "spell_immunity_except_fire")
    assert "fire" in spell_immune["description"]
    fist = golem["on_defense_roll_1_effects"][0]
    assert fist["type"] == "bonus_damage"
    assert fist["damage"] == 2
    assert any(r["roll"] == "1-2" and r["key"] == "ignore" for r in golem["reactions"])

    mantlebeast = by_name["Lurking Mantlebeast"]
    assert mantlebeast["life"] == 5
    assert mantlebeast["attacks"] == 0
    assert mantlebeast["level_delta"] == 3
    assert mantlebeast["no_treasure"] is True
    assert mantlebeast["never_test_morale"] is True
    no_wm = next(r for r in mantlebeast["special_rules"] if r["type"] == "no_wandering_monster")
    assert "Wandering" in no_wm["description"]
    ambush = next(r for r in mantlebeast["special_rules"] if r["type"] == "ambush_drop")
    assert ambush["spot_chance"] == "2-in-6"
    assert ambush["rogue_spot_chance"] == "4-in-6"
    assert ambush["save_level"] == 3
    assert ambush["save_modifiers"]["heavy_armor"] == -1
    assert ambush["save_modifiers"]["elf"] == 1
    assert ambush["save_modifiers"]["rogue"] == 1
    assert mantlebeast["reactions"][0]["key"] == "fight_to_death"


def test_fiendish_foes_treasure_tables_match_pdf_rows() -> None:
    tables = _tables()

    # Fiendish Foes Treasure Table
    ff_treasure = tables["fiendish_foes_treasure_table"]
    assert len(ff_treasure) == 7
    assert all(row.get("source_page") == 186 for row in ff_treasure)
    assert ff_treasure[0]["roll"] == "0"
    assert "No treasure" in ff_treasure[0]["result"]
    assert ff_treasure[1]["roll"] == "1"
    assert "2d6" in ff_treasure[1]["result"] and "2" in ff_treasure[1]["result"]
    assert ff_treasure[3]["roll"] == "3"
    assert "silvered" in ff_treasure[3]["result"]
    assert "non-magical weapon" in ff_treasure[3]["result"]
    assert ff_treasure[4]["roll"] == "4"
    assert "gem" in ff_treasure[4]["result"]
    assert ff_treasure[5]["roll"] == "5"
    assert "jewelry" in ff_treasure[5]["result"]
    assert ff_treasure[6]["roll"] == "6+"
    assert ff_treasure[6]["magic_table"] == "fiendish_foes_magic_treasure"

    # Fiendish Foes Magic Treasure Table
    ff_magic = tables["fiendish_foes_magic_treasure_table"]
    assert len(ff_magic) == 6
    assert all(row.get("source_page") == 187 for row in ff_magic)
    assert "Magic" in ff_magic[0]["result"] and ("weapon" in ff_magic[0]["result"].lower())
    assert "+2" in ff_magic[0]["result"]
    assert "armor" in ff_magic[1]["result"].lower()
    assert "ring of protection" in ff_magic[1]["result"]
    assert "Healing" in ff_magic[2]["result"]
    assert "Acid" in ff_magic[2]["result"]
    assert "Holy Water" in ff_magic[2]["result"]
    assert "Wand of Power" in ff_magic[3]["result"]
    assert "wizard" in ff_magic[3]["result"]
    assert "Enchanted" in ff_magic[4]["result"]
    assert "door" in ff_magic[4]["result"]
    assert "Prayer" in ff_magic[5]["result"]
    assert "bead" in ff_magic[5]["result"]


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
