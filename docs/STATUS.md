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
- **Rules reference:** searchable summaries (rest, flee, class abilities, split party, heroic/legendary skills, Combat Focus,
  camp regroup, consumables, etc.) from `rulebook_reference.json` (122 rulebook
  sections), with category and implementation-status filters (exploration,
  combat, classes, economy, equipment, spells, quests).
- **Rules tables:** collapsible panels listing all dungeon/adventure tables,
  equipment shop rows, **expert/heroic/legendary skills**, **class-trick implementation status**, **map-element validation summary**, tier training costs (Abyss/FD),
  monster bestiary spawn templates, per-foe reaction tables, **map element definitions
  (`tiles.json`)**, **icon registry (`icons.json`)**, and class profiles from
  `classes.json` — each group collapses independently; automated test keeps
  `RULES_TABLE_ORDER` in sync with `dungeon_tables.json`.

## Working

- App starts from `src/app/main.py`; runtime state in `DATA_DIR/game.db`.
- Starter rules load from `data/rules/` with editable overrides in `DATA_DIR/rules/`.
- Character pool, four-hero parties, marching order, export/import, saved games.
- **Adventure lock:** heroes in an active session cannot start another; lock clears on complete or session delete.
- **Camp / saved regroup:** swap party members while camped outside or from a saved game (Regroup Party on party sheet).
- **Gear transfer:** give inventory items or gold between heroes on the home
  screen (roster) or during exploration (party sheet); blocked in combat.
- **Equipment shop (home):** buy rulebook gear before/between adventures (p.16);
  sell loot for gold (half list price; magic resale p.19); class restrictions;
  weapon-default dialog on roster and party sheets. No bank — roster gold uncapped;
  200gp carry limit applies only in the dungeon.
- **Inventory:** carry limits (200gp; starting class gear free; +3 extra weapon slots,
  2 shields max; two-handed = 2 slots); default melee/missile weapons; combat weapon
  swap (1 turn); over-encumbrance −1 Defense/Saves for extra gear or excess gold;
  transfer respects capacity in-dungeon; roster sync after in-dungeon transfers.
- **Session → roster:** clean dungeon exit persists gold, loot, levels, spells,
  XP tallies, and default weapons to the character pool; UI reloads roster.
- Random sessions: map element rolls, placement, truncation, exploration, search,
  rest (rulebook p.114: once/adventure, cleared room + adjacent tiles, nail doors, Life or ability recovery, 1-in-6 wanderers), combat, reactions, traps, treasure, wandering monsters, special events.
- **Entrance doors:** chosen entrance path stays open when the party backtracks
  (rulebook p.25).
- **Closed doors (Exits panel):** unified per-exit list — each exit shows status plus
  travel or door actions; iron doors show “no bash”, highlight Fireball/Lightning when no Rogue,
  unrolled doors show 2d6 roll hint; warrior Bash/roll-door labels; shortcut buttons
  (Lock-pick, Bash, Open, Spellcast, Spend clues) with hero dropdown when needed.
- **Barbarians:** cannot use potions, scrolls, or magic items (may carry for allies).
- **Quests:** Lady in White offer, Quest Table, progress tracking, Ongoing Quests
  panel, quest map marker, Epic Rewards on claim; bring-alive via subdual.
- **Economy:** Classical / Slow and Sure / Old School / Slower Advancement XP;
  wandering healer and alchemist (potion + blade poison); potions in combat or
  exploration (once per hero per adventure).
- **Level-up:** Expanded Edition mid-adventure advancement — Basic d6 > Level (6 always
  succeeds); Expert+ tier dice (d8+2 … d20+10 per Forsaken Depths). L5+ classical
  fork: **Level up** or **Learn expert skill/spell** on the party sheet (monster-type
  prompt for Impervious / Sworn Enemy). Tier training
  (Expert/Heroic/Legendary) between adventures. +1 Life and max Life, spell slots,
  caster spell picker; same-PC-twice rule enforced.
- **Expert skill effects:** 25+ Abyss skills wired in combat/exploration — Brawler,
  Orcslayer, Deadly Accuracy, Gladiator, Impervious, Withstand Pain, Culling, Dead
  Shot, Deadly Strike, Double Attack, Stabbing Attack, Protective Incense, Danger
  Sense, Negotiator (reaction adjust), search helpers (Detective, Intuition, Stone
  Mastery), Turn Undead, Berserk Fury, and more; home **expert_skill_implementation_table**
  lists wired vs planned.
- **Final Boss:** d6 + major-foe tally on room encounters (not wandering majors);
  triple treasure; extra XP roll.
- **Expert spells:** all six Abyss expert spells wired; Mass Teleport ally/destination picker and Lifeforce amount in combat and exploration; home **expert_spells_table** lists mechanics.
- **Named save labels:** optional label when saving; shown in active/saved game lists.
- **Consumables:** lantern oil and acid vials (shop + combat party sheet); rare mushrooms edible in exploration (fungal grottoes p.159).
- **Druid animal companion:** auto-summon on wilderness entry (1 Food ration); fights each round; Madness if slain.
- **Halfling Luck:** reroll search and treasure on current tile; combat attack/defense rerolls; failed save reroll; flee without parting blows.
  Escape; once-per-adventure expended tracking; spell tooltips on party sheets;
  **basic_spells_table** on home screen lists connect rolls and damage/effect text;
  Fireball minion mass-kill uses max(1, spell total − minion Level); **mummy +2**
  on Fireball connect; exploration casting (door magic, Clues on illusion doors);
  scroll burn and wizard copy-to-spellbook; **charged wands and staves** (use from
  party sheet, 1 charge per cast, no memorized slot).
- **Combat:** exploding-d6 attack/defense, armor/shield, corridor ranks, wandering
  rear ambush, p.146 round-0 initiative (surprise / attack-immediately / reactions-first),
  post-ranged unarmed (−2) and foe draw-weapon turn economy, class modifiers,
  minor multi-kill, major-foe level drop, morale, flee/withdraw, blade poison,
  poisonous foes (lingering poison), mirror-image absorption, two-step magic
  resistance (connect vs L, penetrate vs L+MR), troll regeneration (fire, acid vials, lightning,
  and lantern oil suppress regen), held/fog/specter combat effects, subdual damage, missile combat (opening volley + corridor rear rank),
  weapon-type modifiers, once-per-adventure spell consumption; **round summary** line after each Fight Round.
- **Combat Focus:** default layout during combat and pending encounters — tactical room map,
  command rail (Exits / Encounter / Log with Rolls/Math filters), hero drawer for targets,
  abilities, spells, class tricks, and Luck rerolls; slim action deck; optional cinema view.
- **Multi-target combat UI:** Double Attack second foe, Double Kick minor picks,
  Protective Incense ally, Infallible Missile L8+ second target, Phantasmal Binding / Water Jet foe rows.
- **Class tricks (Tiers 2–4, partial):** acrobat shift/distract/evade/kick, assassin hide,
  illusionist distract (minion group), gnome smokescreen/gadget door/trap bonus, mushroom spores/hyphae,
  kukla Army of Dolls, bulwark Sacrifice Defense/Shield, paladin Summon Steed and Divine Smite,
  acrobat Graceful Move social-save reroll.
- **Heroic/Legendary skills:** **45/45 heroic + 20/20 legendary** wired; catalogs, classical/slower XP learning forks; home tables show full status.
- **Split party (starter):** Leave behind / Rejoin / Scout ahead; detached wandering checks; simultaneous front/rear vs major/minion fights; flee uses heroes on the tile.
- **Illusionary Servant:** extra carry capacity (200gp + weapon slots) until trapped;
  **Illusionary Sword/Fog** turn tracking and combat effects wired.
- **Bandages (p.89):** use once per hero per adventure in exploration (+1 Life); may
  target self or a wounded ally.
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
- **Map UI:** viewport zoom/pan (overlay pinned to viewport); collapsible **room
  panel** (top-right), **exits overlay** (bottom-right, scrollable when many exits),
  and **icon key**
  (bottom-left) on the map; draggable log/map and side-panel splits; expandable
  compact session log; room-state markers; ongoing quests; exit labels; door
  open/closed state; environment badge and paper vs unlimited map mode.
- **Session UI:** sticky action bar (Search, Rest, Claim Treasure, etc.) at top of
  side panel; **encounter hint** when foes are on the tile (Exits to leave or
  Start Combat, p.146); **2×2 party sheet grid** on wide screens; **party sheet accordion**
  with equipment/inventory header icons and per-hero exploration/combat actions;
  compact **Regroup Party** panel (collapsed by default) with swap instructions;
  ally bandage targeting; **Fight Round** combat button label.
- **Environments (EE p.112–113):** secret passage search switches to caverns or
  fungal grottoes; trap, special-event, treasure-roll-6, and spawn tables route by
  environment; starter table rows on home screen (seven new keys — see below).
- **Paper map mode:** optional 20×28 grid at session start; placement blocked outside bounds.
- **Map Element Editor:** validation panel, export/import, save reload; stale
  partial Docker tile overrides no longer shadow packaged metadata.
- **Home screen:** **Rules reference** search plus unified collapsible **Rules
  tables** panel — all `dungeon_tables.json` keys plus merged
  `equipment_shop_table`, monster bestiary spawn templates (incl. `caverns_*` /
  `fungal_grottoes_*` categories), per-foe reaction tables, **map elements
  (`tiles.json`)**, **map_elements_validation_table**, **icon registry (`icons.json`)**, expert/heroic/legendary skills/spells, expert skill and class-trick implementation status, and
  tier training costs in nested groups; each table row collapses independently.
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
- **Heroic/legendary skills:** **45/45 heroic + 20/20 legendary** wired (combat, exploration, reactions, rest, traps, resurrection).
- Class tricks **Tiers 3–4** wired: Sacrifice Shield, Army of Dolls, Hyphae, Graceful Move, Divine Smite, Hero's Rest, and expanded heroic combat passives.
- Validate cavern/fungal table row text against owned PDF (starter tables wired).
- **Split party** (EE p.105): starter — detached groups, scout lag, detached wandering checks, simultaneous sub-fights; flee uses heroes present on the tile.
- **Tile validation**: structural checks for all 01–06 and 11–66 tiles via API and `tools/validate_tiles.py`.
- Imported adventure manifests and authored map play.
- Per-square tactical positioning (marching order only).
- Ruleset/theme profiles for non-fantasy books.
- Noun Project icon attribution completeness for public release.
- Replace placeholder `tiles.json` metadata with fully validated rulebook rows (structural validation passes; gif assets and rulebook layout audit ongoing).

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.

## Maintenance scripts

- `scripts/patch_character_spells.py` — repair prepared spell lists on character
  records in `game.db` (all sessions or a named hero).
- `tools/validate_tiles.py` — structural validation for all 01–06 and 11–66 tiles.
