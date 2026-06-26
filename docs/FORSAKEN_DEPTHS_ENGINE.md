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

Hover any badge for rulebook page references.

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

Bestiary: `data/rules/fd_monsters.json` (`fd_vermin`, `fd_minions`, `fd_boss`, `fd_weird`, `fd_horde`).

## Engine modules

| Module | Role |
|--------|------|
| `forsaken_depths_map.py` | Catalog selection, ETR helpers |
| `forsaken_depths_river.py` | River type, hazards, boat, room codes (END/Ru/Ca/B/ETC), NC combat |
| `forsaken_depths_content.py` | Events, hallucinations, ruins (Ru), citadel rolls |
| `random_dungeon.py` | FD content rolls, trap seeding, tile generation |
| `dungeon_table_roller.py` | `roll_fd_trap`, table lookups |

## Room codes at play time

| Code | Behavior |
|------|----------|
| **ETR** | Transition to river catalog |
| **ETC** | Roll `fd_citadel_table`; map citadel on a separate sheet |
| **Ru** | Roll `fd_ruins_content_table` on entry |
| **Ca** | Cairn energy (log + manual resolution) |
| **B** | Bridge — 2-in-6 river encounter guard |
| **END** | River end (log) |
| **NC** | Narrow corridor — ranged/combat mods |

## Traps and events

- **fd_trap** room content seeds an FD trap (`fd_trap_table`); resolve with **Resolve trap** like EE traps.
- **Beast Cage** spawns a surprise weird monster if the lead hero fails the Save.
- **fd_event** rolls d10 on `fd_event_table` when the tile is first entered.
- **fd_hallucination** rolls `fd_hallucination_table`; after two hallucinations in one adventure, roll 4 redirects to an Event.
- **fd_weird** (roll 9): d6 1–3 → `fd_weird_table`, 4–6 → `fd_citadel_weird_table`.

## Validation

```bash
python tools/validate_tiles.py
```

Validates EE, `forsaken_depths`, and `forsaken_depths_rivers` catalogs.

## Deferred

- Full citadel / Ru side-dungeon map auto-generation on separate sheets
- `fd_treasure_table` rolls on monsters and trap rooms
- Oblivion river: forget spell on natural 1 while casting
- Boat movement blocking non-water exits
- Rulebook validation → `validated` on all 72 tiles
