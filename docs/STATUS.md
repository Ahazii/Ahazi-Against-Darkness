# Current Status

Last updated: 2026-05-19

## Summary

The project is a FastAPI + SQLite random dungeon with a browser UI, structured
rule tables, visual map element editor, and a starter faithful loop for level-1
Four Against Darkness play.

### Home screen layout (May 2026)

- **Create character:** collapsible section; class name and role overlay the
  portrait (art visible beneath a top gradient); hover shows rulebook summary.
- **Character roster:** scrollable list (~4 heroes visible) to keep the left
  column compact; drag handles feed the party builder.
- **Party builder:** four marching-order slots (drag from roster, double-click,
  or Add to party); replaces the old checkbox grid.
- **Rules reference:** searchable summaries (rest, flee, class abilities, etc.)
  from `rulebook_reference.json`, with category filter (exploration, combat,
  classes, economy, equipment, spells, quests).
- **Rules tables:** collapsible panels listing all dungeon/adventure tables,
  equipment shop rows, monster bestiary categories, and per-foe reaction tables
  — each group and each table is independently collapsible; automated test
  keeps `RULES_TABLE_ORDER` in sync with `dungeon_tables.json`.

## Working

- App starts from `src/app/main.py`; runtime state in `DATA_DIR/game.db`.
- Starter rules load from `data/rules/` with editable overrides in `DATA_DIR/rules/`.
- Character pool, four-hero parties, marching order, export/import, saved games.
- **Gear transfer:** give inventory items or gold between heroes on the home
  screen (roster) or during exploration (party sheet); blocked in combat.
- **Equipment shop (home):** buy rulebook gear before/between adventures (p.16);
  sell loot for gold (half list price; magic resale p.19); class restrictions;
  weapon-default dialog on roster and party sheets. No bank — roster gold uncapped;
  200gp carry limit applies only in the dungeon.
- **Inventory:** carry limits (200gp, 3 weapon slots, 2 shields; two-handed = 2
  slots); default melee/missile weapons; combat weapon swap (1 turn);
  over-encumbrance −1 Defense/Saves; transfer respects capacity in-dungeon.
- **Session → roster:** clean dungeon exit persists gold, loot, levels, spells,
  XP tallies, and default weapons to the character pool; UI reloads roster.
- Random sessions: map element rolls, placement, truncation, exploration, search,
  rest (rulebook p.114: once/adventure, cleared room + adjacent tiles, nail doors, Life or ability recovery, 1-in-6 wanderers), combat, reactions, traps, treasure, wandering monsters, special events.
- **Entrance doors:** chosen entrance path stays open when the party backtracks
  (rulebook p.25).
- **Closed doors (Exits panel):** one action dropdown per door (lock-pick, bash,
  spellcast, Clues, Fireball/Lightning, Warp Wood) plus Go — replaces per-hero buttons.
- **Barbarians:** cannot use potions, scrolls, or magic items (may carry for allies).
- **Quests:** Lady in White offer, Quest Table, progress tracking, Ongoing Quests
  panel, quest map marker, Epic Rewards on claim; bring-alive via subdual.
- **Economy:** Classical / Slow and Sure / Old School / Slower Advancement XP;
  wandering healer and alchemist (potion + blade poison); potions in combat or
  exploration (once per hero per adventure).
- **Level-up:** Expanded Edition mid-adventure advancement — d6 > Level (6 always
  succeeds), +1 Life and max Life via class offset, immediate class benefits,
  caster spell-slot growth with in-session spell picker; same-PC-twice rule enforced.
- **Final Boss:** d6 + major-foe tally on room encounters (not wandering majors);
  triple treasure; extra XP roll.
- **Spells:** basic wizard/cleric prayers; druid and illusionist class tables;
  Escape; once-per-adventure expended tracking; spell tooltips on party sheets;
  exploration casting (door magic, Clues on illusion doors); scroll burn and wizard
  copy-to-spellbook.
- **Combat:** exploding-d6 attack/defense, armor/shield, corridor ranks, wandering
  rear ambush, p.146 round-0 initiative (surprise / attack-immediately / reactions-first),
  post-ranged unarmed (−2) and foe draw-weapon turn economy, class modifiers,
  minor multi-kill, major-foe level drop, morale, flee/withdraw, blade poison,
  poisonous foes (lingering poison), mirror-image absorption, two-step magic
  resistance (connect vs L, penetrate vs L+MR), troll regeneration, held/fog/specter
  combat effects, subdual damage, missile combat (opening volley + corridor rear rank),
  weapon-type modifiers, once-per-adventure spell consumption.
- **Combat panel (sidebar):** foe list, per-hero targets, **Cast spell** buttons (combat panel and party sheet), potions/spells, expected
  foe-attack preview, status chips, shield/ambush notes; corridor Resolve Round
  status explains full round (rear missiles + front melee + foe attacks); offensive
  spells skip Reactions per p.146; defensive buffs may precede Check Reactions.
- **Illusionary Servant:** extra carry capacity (200gp + weapon slots) until trapped;
  **Illusionary Sword/Fog** turn tracking and combat effects wired.
- **Bandages (p.89):** use once per hero per adventure in exploration (+1 Life).
- **Fallen heroes (p.44–45):** carry body (rearguard, auto-hit), deliver at exit,
  redistribute gear, 1000gp resurrection (d6 ≤ Level); recovery panel in session UI.
- **Door saves:** encumbrance on lock-pick/bash; locked doors require Rogue or Warrior/Barbarian.
- **Rogue traps:** any living rogue may attempt disarm.
- **Loot:** claim treasure splits gold evenly among survivors (200gp carry cap).
  **Magic weapons (p.163):** generic treasure entry rolls d6 for weapon type at
  award; +1 Attack when wielded as default; class/magic restrictions; fixed resale
  (100gp + 2× weapon cost).
- **Reactions:** per-foe bestiary reaction tables (full coverage for current spawn
  names) with gp-or-weapon bribes; category fallback for mixed groups.
- **Treasure:** room-content rolls logged on entry; empty hoards clear map marker;
  claim tooltips explain disabled state.
- **Map UI:** viewport zoom/pan, room-state markers (scaled/centered), icon key,
  ongoing quests, exit labels, door open/closed state; environment badge (dungeon /
  caverns / fungal grottoes) and paper vs unlimited map mode.
- **Environments (EE p.112–113):** secret passage search switches to caverns or
  fungal grottoes; trap, special-event, treasure-roll-6, and spawn tables route by
  environment; starter table rows on home screen (seven new keys — see below).
- **Paper map mode:** optional 20×28 grid at session start; placement blocked outside bounds.
- **Map Element Editor:** validation panel, export/import, save reload; stale
  partial Docker tile overrides no longer shadow packaged metadata.
- **Home screen:** **Rules reference** search plus unified collapsible **Rules
  tables** panel — all `dungeon_tables.json` keys plus merged
  `equipment_shop_table`, monster bestiary spawn templates (incl. `caverns_*` /
  `fungal_grottoes_*` categories), and per-foe reaction tables in three nested
  groups; each table row collapses independently.
- **Home screen — character UI:** collapsible create-character block; class labels
  on card tops; scrollable roster (~4 rows); drag-and-drop party slots.

### Home rules tables — environment keys (Tier 3)

| Key | Rulebook ref |
| --- | --- |
| `caverns_special_events_table` | p.155 |
| `fungal_grottoes_special_events_table` | p.156 |
| `caverns_special_item_table` | p.160 |
| `fungal_grottoes_rare_item_table` | p.161 |
| `fungal_grottoes_rare_mushroom_table` | p.159 |
| `caverns_trap_table` | p.165 |
| `fungal_grottoes_trap_table` | p.166 |

## Known Gaps

- Partial/stub spells (outdoor-only terrain flag for druid spells).
- Combat panel round log summary; multi-target spell UI.
- Class abilities Tiers 2–4 (tricks, gadgets, advanced skills, etc.); Luck on defense/saves/treasure not yet wired in UI.
- Validate cavern/fungal table row text against owned PDF (starter tables wired).
- Map element metadata: many rows still need full rulebook calibration in editor.
- Curved/long-slope masks are approximations; paint-mask tool not built.
- Rulebook scan snippets beside structured tables.
- Imported adventure manifests and authored map play.
- Per-square tactical positioning (marching order only).
- Ruleset/theme profiles for non-fantasy books.
- Noun Project icon attribution completeness for public release.

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.

## Maintenance scripts

- `scripts/patch_character_spells.py` — repair prepared spell lists on character
  records in `game.db` (all sessions or a named hero).
