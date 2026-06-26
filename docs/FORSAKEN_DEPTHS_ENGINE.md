# Forsaken Depths Engine

Live-play support for **Four Against the Forsaken Depths** (`ruleset=forsaken_depths`). Source PDF: `Rules/Four_Against_the_Forsaken_Depths.pdf`.

Tile editor workflow: [FD_MAP_ELEMENT_EDITOR.md](FD_MAP_ELEMENT_EDITOR.md).

## Session setup

- Choose **Four Against the Forsaken Depths** in the Adventure ruleset dropdown (Random Dungeon only).
- Optional **Courtship of Flower Demons** checkbox (on by default with FD) gates Portal→Demesne.
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
| **MR suspended** | Magic Citadel — foe magic resistance ignored on side sheet |
| **Demesne** | Active Courtship of Flower Demons exploration (region, Melancholy, keywords) |

Hover any badge for rulebook page references.

## Party sheet & room panel (FD)

| UI | When | Action |
|----|------|--------|
| **Oblivion: remove 1 Madness** | Oblivion river, pending offer, hero has Madness | `fd_oblivion_redeem_madness` |
| **Forgotten spells** line | Spell forgotten on natural 1 | Display only (hover for rule) |
| **Revelation** buttons (5) | `fd_hallucination_revelation_available` | `fd_spend_hallucination_revelation` |
| **Enter … sheet** | Ru or ETC tile, exploration | `enter_fd_side_sheet` |
| **Return to main map** | On side-sheet tile | `exit_fd_side_sheet` |
| **Secret passage** | Ruins roll 12 tile | `fd_secret_passage_unlock_clues` / `choose_fd_secret_passage_destination` |
| **Escape citadel (4 Clues)** | Prisoners citadel side sheet | `fd_prisoners_escape` |
| **Citadel of Dead** banner | Dead Things side sheet | Bandages only (hover) |
| **MR suspended** badge | Magic Citadel side sheet | Spells ignore MR tiers |
| **Treasure choice** buttons | Pending FD treasure choice on tile | `choose_treasure_outcome` |
| **Roll Demesne encounter** | `courtship_demesne_active`, exploration | `courtship_roll_encounter` |
| **Woo / Fight / Giving / Withholding** | Pending woo or active wooing | `courtship_woo_encounter`, `courtship_fight_encounter`, `courtship_woo_giving`, `courtship_woo_withholding`, `courtship_woo_abort_fight` |
| **Damsel penalty choice** | After Giving success vs Damsel of Teeming Roses | `courtship_damsel_penalty` (Life or Madness on next Withholding fail) |
| **Seduce reaction** | After choosing Fight on seduce-eligible spawn | `courtship_seduce_reaction` |
| **Book of Secrets choices** | Disturbing Altar, Queen's vault, Lex shop (pick 3), Matron head quest, Lady TRUELOVE, maze | `courtship_book_choice`, `courtship_lady_keepsake` |
| **Pathway / Flower Portal home** | Demesne pathways or Seaside | `courtship_choose_pathway` / `courtship_leave_demesne` |
| **Interact with Cyclopean Idol** | Idol on tile or citadel final | `resolve_fd_cyclopean_idol` |
| **Idol outcome choices** | Secret door / Lady in Black / spell relief | `choose_fd_idol_outcome` |
| **Report Cyclopean Idol visit** | Pilgrimage quest | `report_fd_idol_visit` |
| **Lady in Gray** | Ongoing Quests panel on event tile | `accept_fd_quest` / `refuse_fd_lady_in_gray` |
| **Quest progress** | Active FD quest (room + Ongoing Quests) | `fd_quest_spend_clue_enemy`, `fd_quest_spend_clues_servitor`, `recover_fd_lost_page`, `turn_in_fd_quest_item`, `enter_fd_dark_pits` |
| **Claim FD Quest reward** | Return to quest-giver tile when ready | `claim_fd_quest_reward` |

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
| `fd_cyclopean_idol_table` | d6 | p.52 |
| `fd_quest_table` | d6 | p.54 |
| `fd_heroic_magic_item_table` | d6 | p.49 |
| `fd_legendary_magic_item_table` | d10 | p.50 |
| `fd_legendary_spell_table` | d6 | p.47 |
| `courtship_seaside_encounter_table` | 2d6 | TCOTFD p.62 |
| `courtship_riverside_encounter_table` | 2d6 | TCOTFD p.64 |
| `courtship_woods_encounter_table` | 2d6 | TCOTFD p.65 |
| `courtship_mountain_encounter_table` | 2d6 | TCOTFD p.66 |
| `courtship_meadows_encounter_table` | 2d6 | TCOTFD p.67 |
| `courtship_palace_encounter_table` | 2d6 | TCOTFD p.68 |
| `courtship_book_of_secrets_table` | entry # | TCOTFD BoS cross-references |
| `courtship_blossoms_magic_item_table` | d6 | TCOTFD p.69 |
| `courtship_blossoms_spell_scrolls_table` | d6 | TCOTFD p.27 |
| `courtship_lex_shop_table` | catalog | Lex shop (BoS entry 32) |

Bestiary: `data/rules/fd_monsters.json` (`fd_vermin`, `fd_minions`, `fd_boss`, `fd_weird`, `fd_horde`); `data/rules/courtship_monsters.json` (`courtship_demons`).

**Gem/jewelry items** — pocket gems use `Gem (Ngp)` / `Jewelry (Ngp)` item names; `gem_items.py` parses value for bribes, milestones, and Furnace imbue (200+ gp).

## Engine modules

| Module | Role |
|--------|------|
| `forsaken_depths_map.py` | Catalog selection, ETR helpers |
| `forsaken_depths_river.py` | River type, hazards, boat, room codes (END/Ru/Ca/B/ETC), NC combat |
| `forsaken_depths_content.py` | Events, hallucinations, ruins (Ru), citadel rolls |
| `random_dungeon.py` | FD content rolls, trap seeding, tile generation |
| `forsaken_depths_citadel.py` | Citadel type modifiers (crowded, traps, prisoners escape, dead healing, magic MR, final bosses) |
| `forsaken_depths_side_sheet.py` | Citadel / river ruins side-dungeon entry, room budget, return to main map |
| `forsaken_depths_secret_passage.py` | Ruins secret passage unlock (Clues / traps / weirds) and destination choice |
| `forsaken_depths_cyclopean_idol.py` | Cyclopean Idol table outcomes (FD p.52) |
| `courtship_demesne.py` | Blossoms' Demesne via Portal (TCOTFD p.62–68) |
| `courtship_combat.py` | Flower-demon combat specials (TCOTFD p.64–68) |
| `courtship_book_of_secrets.py` | Book of Secrets entry handlers |
| `gem_items.py` | Gem/jewelry `(Ngp)` parsing and Furnace eligibility |
| `forsaken_depths_legendary_spells.py` | FD Legendary spell casts including Furnace gem imbue |
| `forsaken_depths_events.py` | FD events including Portal branches |
| `forsaken_depths_quest.py` | Lady in Gray quests (up to 2 concurrent), oracle-bound quests, pilgrimage |
| `forsaken_depths_spell_scrolls.py` | Dark Pits scroll rewards (Scroll/Bark/Prism by spell class) |

## Ruins secret passage (FD p.56)

**Unlock** (any one path, tracked adventure-wide while the passage is pending):

| Path | Requirement |
|------|-------------|
| Clues | Spend **3** held Clues on the passage tile |
| Traps | Clear **3** traps of level **HCL+3** or higher (anywhere) |
| Weirds | Defeat **2** Weird Monsters (anywhere) |

**Destinations** (map panel buttons when unlocked):

| Choice | Effect |
|--------|--------|
| **Abyss** | Opens a **fungal grottoes** environment branch |
| **Netherworld** | Opens a **caverns** environment branch |
| **Citadel** | Rolls `fd_citadel_table` if needed; **Enter Citadel sheet** on this tile |

## Room codes at play time

| Code | Behavior |
|------|----------|
| **ETR** | Transition to river catalog |
| **ETC** | Roll `fd_citadel_table`; **Enter Citadel sheet** on map panel (separate color) |
| **Ru** | **Enter Forsaken Ruins sheet** (d6+2 rooms, `fd_ruins_content_table` per room) |
| **Ca** | Cairn energy — **Tap Cairn** on room panel (HCL+5 spellcasting roll; cast without expending spell, pay 1 Life; nat 1 choice, FD p.40) |
| **B** | Bridge — 2-in-6 river encounter guard |
| **END** | River end (log) |
| **NC** | Narrow corridor — ranged/combat mods |

## Traps and events

- **fd_trap** room content seeds an FD trap (`fd_trap_table`); resolve with **Resolve trap** like EE traps. Room traps have a 2-in-6 FD treasure roll after clearing.
- **Monster treasure** uses `fd_treasure_table` when `ruleset=forsaken_depths`. Gem/jewelry rows add pocket items as `Gem (Ngp)` rather than raw gold. Rolls with a choice (gold/masterwork, potions/scrolls, etc.) show **Treasure** map markers with pick buttons before claim. Roll **10** (jackpot) offers **roll twice** or **roll four times** (4-in-6 wandering monsters when claiming loot).
- **Something Stirs** (`fd_stirs_in_darkness_remaining`): empty areas may roll 3-in-6 river encounters until the counter reaches 0.
- **River of Oblivion**: natural 1 on spellcasting or puzzle Saves forgets a spell (party sheet lists forgotten spells). Once per adventure, remove 1 Madness from one hero via **Oblivion: remove 1 Madness** on the party sheet when the offer is pending.
- **River travel**: while boating, only water-channel exits are valid; bank exits disembark the party to foot travel. On foot, water-channel exits are blocked (FD p.28).
- **Wandering monsters** on FD sessions use `fd_wandering_monsters_table` (including Waste of Time river hazards).
- **Beast Cage** spawns a surprise weird monster if the lead hero fails the Save.
- **fd_event** rolls d10 on `fd_event_table` when the tile is first entered.
- **fd_hallucination** rolls `fd_hallucination_table`; roll 5–6 grants a **Revelation** (party sheet / room panel buttons). After two hallucinations in one adventure, roll 4 redirects to an Event.
- **fd_weird** (roll 9): d6 1–3 → `fd_weird_table`, 4–6 → `fd_citadel_weird_table`.
- **Side sheets** — Ru (`d6+2` rooms) or Citadel (`fd_citadel_room_count` rooms): **Enter … sheet** on the map panel places procedural side rooms (purple dashed outline). **Return to main map** when done. Room budget blocks further expansion when exhausted. Citadel types apply their FD p.60 modifiers (crowded double minions/−1 Reaction, traps replacing minions, prisoners 4-Clue escape, dead-citadel bandages-only healing, magic citadel MR suspended, ghost final boss; **magic citadel final** places a Cyclopean Idol to interact with).

## Portal → Courtship Demesne (TCOTFD)

- **Portal** event (`fd_event_table` roll 7): choose **Demesne** on the map panel (1 Life per living hero).
- Enters **Seaside** with `courtship_demesne_active`; roll **2d6** on the current region's `courtship_*_encounter_table`.
- **Pathway** results offer travel to linked regions (one-way); stay or move via pathway buttons.
- **Woo or Fight** on Maidens/Ladies before combat; **Giving/Withholding** social rolls with template-specific rules.
- **Damsel of Teeming Roses**: after a successful Giving roll, choose whether the next Withholding failure costs Life or Madness.
- **Book of Secrets** entries from encounters (`courtship_book_of_secrets_table`) offer UI choices (altar, vault, Lex shop, maze, Matron wooing, etc.).
- **Lady of Lament** (Woods) — Woo or Fight; Keepsake +3 Giving; romantic stance −1; pleased wooing → BoS entry 9 **TRUELOVE** (wooing character only; satyrs blocked). Slay her in combat while the Matron's head quest is active to claim **Lady of Lament's head**.
- **Matron head quest** (BoS entry 8) — After pleased Matron wooing, bring the Lady's head and deliver at the Matron for **Epic Rewards (d6)** or a **Blossoms Magic Item** of your choice.
- **Lex the Cambion** (BoS entry 32) — Pay **300gp + oath** or trade a **soul cube**, then pick **any three** items from `courtship_lex_shop_table` (Blossoms magic, Blossoms scrolls, 4AD magic treasure).
- **Combat specials** for flower demons (mesmerize, paralysis, Corrosive Shrub sap, whip disarm, thorns, Matron lash/respawn, Maypole no-flee, Handmaiden blur) via `courtship_combat.py`.
- **Flower Portal home** from **Seaside only** (`courtship_leave_demesne`).
- Spend **1 Clue** to re-roll or shift an encounter (up to party's highest Melancholy in Clues spent, TCOTFD).
- Source PDF: `Rules/The_Courtship_of_Flower_Demons.pdf`.

## Cyclopean Idol (FD p.52)

Roll **d6** on `fd_cyclopean_idol_table`:

| Roll | Outcome |
|------|---------|
| 1 | Climb for gems (HCL+1 saves; 3-in-6 for d3 gems) |
| 2 | **Walking Idol** spawns (HCL+4 weird, fights to death) |
| 3 | Pedestal secret door — 1 Clue or Search → d6+3 ruins side sheet |
| 4 | Life sap (−1 Life; 1-in-6 Clue per hero damaged) |
| 5 | **Lady in Black** — sacrifice Heroic item for **1 Clue + Quest**, or roll `fd_quest_table` with oracle enchantment on a random hero (dies if that Quest incomplete at exit) |
| 6 | Heroic spell bas-relief — learn random heroic spell with XP roll |

- **Pilgrimage** quest: **Report Cyclopean Idol visit** on the room panel.
- **Magic Citadel** final room: **Interact with Cyclopean Idol** (no auto-spawn on room entry).
- If the Walking Idol flees, the next idol roll shifts +1.

## Lady in Gray / Quest Table (FD p.54)

Event roll **1** on `fd_event_table` offers the Lady in Gray. **Accept** rolls d6 on `fd_quest_table` after a social Save; **Refuse** sends her away for the adventure (FD p.63).

| Roll | Quest | Progress | Reward |
|------|-------|----------|--------|
| 1 | **Servitor** | Spend **2 Clues** → servitor in next room; **1-in-6** in Major Foe lair; capture with Sleep/subdual | 1 XP roll + magic item |
| 2 | **Defeat enemy** | Random Weird/Boss ambush after **5 areas** or spend **1 Clue** now | 1 XP roll + magic item |
| 3 | **Lost pages** | Count **scroll** finds as pages (treasure menu or inventory; 4 total) | 1 XP roll + magic item |
| 4 | **Three items** | Turn in **3 newly found** magic items at the Lady's tile (inventory snapshotted at accept) | **3 Clues** + 1 XP roll |
| 5 | **Pilgrimage** | Visit **3** Cyclopean Idols (`report_fd_idol_visit` / idol interact) | 1 XP roll per hero **or** 1 Heroic magic item |
| 6 | **Dark Pits** | Side sheet **d6+3** rooms (`enter_fd_dark_pits`); clear all occupants | 1 XP roll + player-chosen scroll (Basic/Expert/Heroic/Legendary spell) |

Quest foes are tagged `fd_quest_enemy` / `fd_quest_servitor` for combat-end tracking. Turn-in readiness shows on the **Ongoing Quests** card; clue spends and item turn-in appear on the **room panel** and quest card.

## Validation

```bash
python tools/validate_tiles.py
```

Validates EE, `forsaken_depths`, and `forsaken_depths_rivers` catalogs.

## Deferred

- Remaining Courtship combat nuance (Necrogaunt rescue window, Stone Roper teleport clears, Baobhan Sith permanent Life loss wiring, etc.).
- Lex item use side effect (BoS entry 4 — d6 soul tax on first use).
- Rulebook validation → `validated` on all 72 tiles
