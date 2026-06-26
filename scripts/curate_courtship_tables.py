"""Build courtship_tables.json with structured effect payloads (TCOTFD p.62–68)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "rules" / "courtship_tables.json"

REGIONS = {
    "courtship_seaside_encounter_table": [
        {"roll": "2", "key": "heartbreaking_sunset", "name": "Heartbreaking Sunset", "effect": "melancholy_gain", "amount": 1, "elf_madness": True},
        {"roll": "3-4", "key": "strangling_seaweed", "name": "Strangling Seaweed", "effect": "strangling_seaweed"},
        {"roll": "5", "key": "strange_marks_in_the_sand", "name": "Strange Marks in the Sand", "effect": "clues", "formula": "d3"},
        {"roll": "6", "key": "lorelei", "name": "Lorelei (Maidens)", "effect": "spawn", "spawn": {"template": "Lorelei", "count": "d6+3", "category": "minions", "level_delta": 2}},
        {"roll": "7", "key": "harvest", "name": "Harvest", "effect": "harvest", "save_level": "HCL+4", "reward": "pearls", "fail_spawn": "Strangling Seaweed", "fail_count": "d3"},
        {"roll": "8", "key": "pathway", "name": "Pathway", "effect": "pathway", "pathways": ["riverside", "meadows"]},
        {"roll": "9", "key": "naiads", "name": "Naiads (Maidens)", "effect": "spawn", "spawn": {"template": "Naiads", "count": "d3+2", "category": "minions", "level_delta": 3}},
        {"roll": "10", "key": "princess_of_tides", "name": "Princess of Tides (Lady)", "effect": "spawn", "spawn": {"template": "Princess of Tides", "count": "1", "category": "boss", "level_delta": 3, "life_delta": 4}},
        {"roll": "11", "key": "cracked_skull", "name": "Cracked Skull (unique)", "effect": "unique_clues", "formula": "d6", "reroll_as": "strange_marks_in_the_sand"},
        {"roll": "12", "key": "love_letter", "name": "Love Letter (unique)", "effect": "keyword", "keyword": "KEEPSAKE", "reroll_as": "cracked_skull"},
    ],
    "courtship_riverside_encounter_table": [
        {"roll": "2-3", "key": "wistful_waterfall", "name": "Wistful Waterfall", "effect": "melancholy_check"},
        {"roll": "4", "key": "corrosive_shrub", "name": "Corrosive Shrub", "effect": "spawn", "spawn": {"template": "Corrosive Shrub", "count": "1", "category": "horde", "level_delta": 4, "life_delta": 4}},
        {"roll": "5", "key": "giant_purple_pitcherplants", "name": "Giant Purple Pitcherplants", "effect": "spawn", "spawn": {"template": "Giant Purple Pitcherplant", "count": "d6+2", "category": "minions", "level_delta": 2}},
        {"roll": "6", "key": "giggling_gingers", "name": "Giggling Gingers (Maidens)", "effect": "spawn", "spawn": {"template": "Giggling Gingers", "count": "d3+2", "category": "minions", "level_delta": 2}},
        {"roll": "7", "key": "harvest", "name": "Harvest", "effect": "harvest", "save_level": "HCL+3", "reward": "ingredients", "fail_spawn": "Giant Purple Pitcherplant", "fail_count": "d6+2"},
        {"roll": "8", "key": "pathway", "name": "Pathway", "effect": "pathway", "pathways": ["seaside", "woods"]},
        {"roll": "9", "key": "ominous_omen", "name": "Ominous Omen", "effect": "ominous_omen"},
        {"roll": "10", "key": "colleen_of_lilies", "name": "Colleen of Lilies (Lady)", "effect": "spawn", "spawn": {"template": "Colleen of Lilies", "count": "1", "category": "boss", "level_delta": 3, "life_delta": 5}},
        {"roll": "11", "key": "inexplicable_marks", "name": "Inexplicable Marks", "effect": "search_clues", "target": 5, "success": "d3", "fail": 0},
        {"roll": "12", "key": "disturbing_altar", "name": "Disturbing Altar (unique)", "effect": "book_secret", "entry": 22, "reroll_as": "inexplicable_marks"},
    ],
    "courtship_woods_encounter_table": [
        {"roll": "2-3", "key": "enchanting_cascade", "name": "Enchanting Cascade", "effect": "heal_melancholy", "heal": "d6", "melancholy": 1},
        {"roll": "4", "key": "grisly_findings", "name": "Grisly Findings", "effect": "clues", "formula": "d3"},
        {"roll": "5", "key": "death_orchid", "name": "Death Orchid", "effect": "spawn", "spawn": {"template": "Death Orchid", "count": "1", "category": "weird", "level_delta": 4, "life_delta": 6}},
        {"roll": "6", "key": "giant_sundews", "name": "Giant Sundews", "effect": "spawn", "spawn": {"template": "Giant Sundew", "count": "d6+4", "category": "minions", "level_delta": 3}},
        {"roll": "7", "key": "harvest", "name": "Harvest", "effect": "harvest", "save_level": "HCL+4", "reward": "common_ingredients", "fail_spawn": "Giant Sundew", "fail_count": "d6+4"},
        {"roll": "8", "key": "pathway", "name": "Pathway", "effect": "pathway", "pathways": ["riverside", "mountain"], "clue_secret_trail": True},
        {"roll": "9", "key": "dryads", "name": "Dryads (Maidens)", "effect": "spawn", "spawn": {"template": "Dryads", "count": "d3+2", "category": "minions", "level_delta": 3}},
        {"roll": "10", "key": "mistress_of_black_lashes", "name": "Mistress of Black Lashes (Lady)", "effect": "spawn", "spawn": {"template": "Mistress of Black Lashes", "count": "1", "category": "boss", "level_delta": 4, "life_delta": 3}},
        {"roll": "11", "key": "macabre_art", "name": "Macabre Art", "effect": "search_clues", "target": 5, "success": "d6", "fail": 1},
        {"roll": "12", "key": "lady_of_lament", "name": "Lady of Lament (Lady)", "effect": "lady_of_lament"},
    ],
    "courtship_mountain_encounter_table": [
        {"roll": "2-3", "key": "deadly_fall", "name": "Deadly Fall", "effect": "agility_save", "level": 4, "damage": "d6"},
        {"roll": "4", "key": "necrogaunts", "name": "Necrogaunts", "effect": "spawn", "spawn": {"template": "Necrogaunt", "count": "d6+2", "category": "minions", "level_delta": 2}},
        {"roll": "5", "key": "rockslide", "name": "Rockslide", "effect": "rockslide", "save_level": "HCL+2"},
        {"roll": "6", "key": "harvest_and_pathway", "name": "Harvest and Pathway", "effect": "harvest_pathway", "save_level": "HCL+4", "pathways": ["woods"], "fail_spawn": "Stone Fiend", "fail_count": "d6+2"},
        {"roll": "7", "key": "hue_less_mineral_spring", "name": "Hue-Less Mineral Spring", "effect": "acid_spring", "save_level": "HCL+5", "keyword": "ACERBIC"},
        {"roll": "8", "key": "stone_fiends", "name": "Stone Fiends", "effect": "spawn", "spawn": {"template": "Stone Fiend", "count": "d6+2", "category": "minions", "level_delta": 3}},
        {"roll": "9", "key": "harvest", "name": "Harvest", "effect": "harvest", "save_level": "HCL+5", "reward": "mineral_ingredients", "fail_spawn": "Necrogaunt", "fail_count": "d6+2"},
        {"roll": "10", "key": "stone_roper", "name": "Stone Roper", "effect": "spawn", "spawn": {"template": "Stone Roper", "count": "1", "category": "weird", "level_delta": 5, "life_delta": 5}},
        {"roll": "11", "key": "ancient_runes", "name": "Ancient Runes", "effect": "search_clues", "target": 5, "success": "d3+1", "fail": 1, "stone_mastery": True},
        {"roll": "12", "key": "the_occlith", "name": "The Occlith", "effect": "occlith"},
    ],
    "courtship_meadows_encounter_table": [
        {"roll": "2-3", "key": "haunting_vision", "name": "Haunting Vision", "effect": "fear_save", "level": 5},
        {"roll": "4", "key": "baobhan_sith", "name": "Baobhan Sith", "effect": "spawn", "spawn": {"template": "Baobhan Sith", "count": "1", "category": "weird", "level_delta": 4, "life_delta": 3}},
        {"roll": "5", "key": "venus_flytraps", "name": "Venus Flytraps", "effect": "spawn", "spawn": {"template": "Venus Flytrap", "count": "d6+d3+1", "category": "minions", "level_delta": 4}},
        {"roll": "6", "key": "maypole_dancers", "name": "Maypole Dancers (Maidens)", "effect": "spawn", "spawn": {"template": "Maypole Dancers", "count": "d6+2", "category": "minions", "level_delta": 2}},
        {"roll": "7", "key": "harvest", "name": "Harvest", "effect": "harvest", "save_level": "HCL+2", "reward": "meadow_ingredients", "fail_spawn": "Venus Flytrap", "fail_count": "d6+d3+1"},
        {"roll": "8", "key": "netherworld_cromlech", "name": "Netherworld Cromlech", "effect": "search_clues", "target": 5, "success": "d3+1", "fail": 1},
        {"roll": "9", "key": "matron_of_summer", "name": "Matron of Summer (Lady)", "effect": "spawn", "spawn": {"template": "Matron of Summer", "count": "1", "category": "boss", "level_delta": 4, "life_delta": 3}},
        {"roll": "10", "key": "hidden_pathway", "name": "Hidden Pathway", "effect": "pathway", "pathways": ["seaside", "palace"]},
        {"roll": "11", "key": "frost_roses", "name": "Frost Roses", "effect": "frost_roses"},
        {"roll": "12", "key": "lex_the_cambion", "name": "Lex the Cambion (unique)", "effect": "unique_reroll", "reroll": True},
    ],
    "courtship_palace_encounter_table": [
        {"roll": "2-3", "key": "mirror_demon", "name": "Mirror Demon", "effect": "spawn", "spawn": {"template": "Mirror Demon", "count": "1", "category": "weird", "level_delta": 5, "life_delta": 0, "fixed_life": 6}},
        {"roll": "4-5", "key": "maze_of_wondrous_awe", "name": "Maze of Wondrous Awe", "effect": "book_secret", "entry": 33},
        {"roll": "6", "key": "ballroom_of_countless_reflections", "name": "Ballroom of Countless Reflections", "effect": "ballroom", "save_level": "HCL+5"},
        {"roll": "7", "key": "queens_maids", "name": "Queen's Maids (Maidens)", "effect": "spawn", "spawn": {"template": "Queen's Maids", "count": "d6+1", "category": "minions", "level_delta": 3}},
        {"roll": "8", "key": "queens_handmaidens", "name": "Queen's Handmaidens (Maidens)", "effect": "spawn", "spawn": {"template": "Queen's Handmaidens", "count": "d3+3", "category": "minions", "level_delta": 5}},
        {"roll": "9", "key": "damsel_of_teeming_roses", "name": "Damsel of Teeming Roses (Lady)", "effect": "spawn", "spawn": {"template": "Damsel of Teeming Roses", "count": "1", "category": "boss", "level_delta": 2, "life_delta": 5}},
        {"roll": "10", "key": "blue_haired_queen", "name": "Blue-Haired Queen of Flowers (Lady)", "effect": "spawn", "spawn": {"template": "Blue-Haired Queen of Flowers", "count": "1", "category": "boss", "level_delta": 6, "life_delta": 7}},
        {"roll": "11", "key": "strange_follies", "name": "Strange Follies", "effect": "strange_follies"},
        {"roll": "12", "key": "queens_locked_vault", "name": "Queen's Locked Vault", "effect": "queens_locked_vault"},
    ],
}

SUMMARIES = {
    "heartbreaking_sunset": "Gain 1 Melancholy. Elves gain 1 Madness instead (TCOTFD p.62).",
    "strangling_seaweed": "Attacks d3 random characters — save vs HCL+d3 or lose d3 Life (TCOTFD p.62).",
    "pathway": "One-way path to another Demesne region (TCOTFD).",
    "the_occlith": "Ancient alien intelligence — see Book of Secrets entries 5–6 (TCOTFD p.66).",
    "lady_of_lament": "Lady of Lament — KEEPSAKE/TRUELOVE keywords affect reactions; may reveal Riverside passage (TCOTFD p.65).",
    "queens_locked_vault": "Silver-chained vault — ACERBIC/TRUELOVE keywords; wooing characters make Melancholy checks (TCOTFD p.68).",
}


def main() -> None:
    payload: dict = {
        "ruleset_status": (
            "Courtship of Flower Demons — Blossoms' Demesne encounter tables (TCOTFD p.62–68). "
            "Enter via Forsaken Depths Portal → Demesne (begins at Seaside)."
        ),
        "validation": {
            "source": "Rules/The_Courtship_of_Flower_Demons.pdf",
            "courtship_encounter_tables": "p.62-68",
        },
    }
    for table_key, rows in REGIONS.items():
        enriched = []
        for row in rows:
            item = dict(row)
            item["summary"] = SUMMARIES.get(row["key"], f"{row['name']} (TCOTFD).")
            item["source_page"] = 62 + list(REGIONS.keys()).index(table_key)
            enriched.append(item)
        payload[table_key] = enriched
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT} ({sum(len(v) for v in REGIONS.values())} rows)")


if __name__ == "__main__":
    main()
