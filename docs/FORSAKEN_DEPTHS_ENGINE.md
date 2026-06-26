# Forsaken Depths Engine

Live-play support for **Four Against the Forsaken Depths** (`ruleset=forsaken_depths`). Source PDF: `Rules/Four_Against_the_Forsaken_Depths.pdf`.

Tile editor workflow: [FD_MAP_ELEMENT_EDITOR.md](FD_MAP_ELEMENT_EDITOR.md).

## Session setup

- Choose **Four Against the Forsaken Depths** in the Adventure ruleset dropdown (Random Dungeon only).
- Map elements draw from catalog `forsaken_depths` (dungeon) or `forsaken_depths_rivers` (underground river).
- **ETR** rooms transition to the river catalog when explored; river type is rolled once (FD p.32).

## Map panel badges

| Badge | Meaning |
|-------|---------|
| **FD · Dungeon / Underground river** | Active map layer |
| **River type** | Oblivion, Tears, Death, Flame, Conjuration, or Serpent (FD p.32) |
| **Boat** | OK / Damaged / Destroyed (FD p.30) |
| **Travel** | Boat vs on foot |
| **Citadel** | Rolled citadel type and room count (ETC or Passage event) |
| **Stirs** | *Something Stirs in the Darkness* event — river encounters in empty rooms for N areas |
| **Side sheet** | Active citadel or river ruins side dungeon — rooms entered / budget |
| **Revelation** | Hallucination Revelation benefit ready to spend |
| **Oblivion offer** | One-time Madness redemption on River of Oblivion |

Hover any badge for rulebook page references.

## Party sheet & room panel (FD)

| UI | When | Action |
|----|------|--------|
| **Oblivion: remove 1 Madness** | Oblivion river, pending offer, hero has Madness | `fd_oblivion_redeem_madness` |
| **Forgotten spells** line | Spell forgotten on natural 1 | Display only (hover for rule) |
| **Revelation** buttons (5) | `fd_hallucination_revelation_available` | `fd_spend_hallucination_revelation` |
| **Enter … sheet** | Ru or ETC tile, exploration | `enter_fd_side_sheet` |
| **Return to main map** | On side-sheet tile | `exit_fd_side_sheet` |
| **Treasure choice** buttons | Pending FD treasure choice on tile | `choose_treasure_outcome` |

## Gameplay tables (Home → Rules tables)

All rows are in `data/rules/forsaken_depths_tables.json` and appear on the home **Rules tables** panel:

| Table key | Roll | PDF |
|-----------|------|-----|
| `fd_room_content_table` | 2d6 | p.59 |
| `fd_river_type_table` | d6 | p.32 |
| `fd_river_hazard_table` | d6 (2-in-6 first) | p.30 |
| `fd_river_encounter_table` | d6 | p.36 |
| `fd_vermin_table` | d6 | p.38 |
| `fd_minions_table` | d6 | p.40 |
| `fd_horde_table` | d6 | p.42 |
| `fd_boss_table` | d6 | p.44 |
| `fd_weird_table` | d6 | p.45 |
| `fd_citadel_weird_table` | d6 | p.61 |
| `fd_trap_table` | d6 (level HCL+Tier+2) | p.58 |
| `fd_hallucination_table` | d6 | p.55 |
| `fd_ruins_content_table` | 2d6 | p.56 |
| `fd_event_table` | d10 | p.63 |
| `fd_citadel_table` | d6 | p.60 |
| `fd_treasure_table` | d10 (0–10) | p.62 |
| `fd_wandering_monsters_table` | d6 | p.30 |

Bestiary: `data/rules/fd_monsters.json` (`fd_vermin`, `fd_minions`, `fd_boss`, `fd_weird`, `fd_horde`).

## Engine modules

| Module | Role |
|--------|------|
| `forsaken_depths_map.py` | Catalog selection, ETR helpers |
| `forsaken_depths_river.py` | River type, hazards, boat, room codes (END/Ru/Ca/B/ETC), NC combat |
| `forsaken_depths_content.py` | Events, hallucinations, ruins (Ru), citadel rolls |
| `random_dungeon.py` | FD content rolls, trap seeding, tile generation |
| `forsaken_depths_side_sheet.py` | Citadel / river ruins side-dungeon entry, room budget, return to main map |

## Room codes at play time

| Code | Behavior |
|------|----------|
| **ETR** | Transition to river catalog |
| **ETC** | Roll `fd_citadel_table`; **Enter Citadel sheet** on map panel (separate color) |
| **Ru** | **Enter Forsaken Ruins sheet** (d6+2 rooms, `fd_ruins_content_table` per room) |
| **Ca** | Cairn energy (log + manual resolution) |
| **B** | Bridge — 2-in-6 river encounter guard |
| **END** | River end (log) |
| **NC** | Narrow corridor — ranged/combat mods |

## Traps and events

- **fd_trap** room content seeds an FD trap (`fd_trap_table`); resolve with **Resolve trap** like EE traps. Room traps have a 2-in-6 FD treasure roll after clearing.
- **Monster treasure** uses `fd_treasure_table` when `ruleset=forsaken_depths`. Rolls with a choice (gold/masterwork, potions/scrolls, etc.) show **Treasure** map markers with pick buttons before claim. Roll **10** (jackpot) offers **roll twice** or **roll four times** (4-in-6 wandering monsters when claiming loot).
- **Something Stirs** (`fd_stirs_in_darkness_remaining`): empty areas may roll 3-in-6 river encounters until the counter reaches 0.
- **River of Oblivion**: natural 1 on spellcasting or puzzle Saves forgets a spell (party sheet lists forgotten spells). Once per adventure, remove 1 Madness from one hero via **Oblivion: remove 1 Madness** on the party sheet when the offer is pending.
- **River travel**: while boating, only water-channel exits are valid; bank exits disembark the party to foot travel. On foot, water-channel exits are blocked (FD p.28).
- **Wandering monsters** on FD sessions use `fd_wandering_monsters_table` (including Waste of Time river hazards).
- **Beast Cage** spawns a surprise weird monster if the lead hero fails the Save.
- **fd_event** rolls d10 on `fd_event_table` when the tile is first entered.
- **fd_hallucination** rolls `fd_hallucination_table`; roll 5–6 grants a **Revelation** (party sheet / room panel buttons). After two hallucinations in one adventure, roll 4 redirects to an Event.
- **fd_weird** (roll 9): d6 1–3 → `fd_weird_table`, 4–6 → `fd_citadel_weird_table`.
- **Side sheets** — Ru (`d6+2` rooms) or Citadel (`fd_citadel_room_count` rooms): **Enter … sheet** on the map panel places procedural side rooms (purple dashed outline). **Return to main map** when done. Room budget blocks further expansion when exhausted.

## Validation

```bash
python tools/validate_tiles.py
```

Validates EE, `forsaken_depths`, and `forsaken_depths_rivers` catalogs.

## Deferred

- Rulebook validation → `validated` on all 72 tiles
- Full citadel type modifiers (crowded double-spawn, prisoners 4 Clues escape, magic citadel MR suspend UI)
