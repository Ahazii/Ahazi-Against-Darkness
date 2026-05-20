# Current Status

Last updated: 2026-05-19

## Summary

The project is a FastAPI + SQLite random dungeon with a browser UI, structured
rule tables, visual map element editor, and a starter faithful loop for level-1
Four Against Darkness play.

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
  rest, combat, reactions, traps, treasure, wandering monsters, special events.
- **Entrance doors:** chosen entrance path stays open when the party backtracks
  (rulebook p.25).
- **Barbarians:** cannot use potions, scrolls, or magic items (may carry for allies).
- **Quests:** Lady in White offer, Quest Table, progress tracking, Ongoing Quests
  panel, quest map marker, Epic Rewards on claim; bring-alive via subdual.
- **Economy:** Classical / Slow and Sure / Old School / Slower Advancement XP;
  wandering healer and alchemist (potion + blade poison); potions in combat or
  exploration (once per hero per adventure).
- **Level-up:** Expanded Edition mid-adventure advancement — d6 > Level (6 always
  succeeds), +1 Life and max Life via class offset, immediate class benefits,
  caster spell-slot growth with in-session spell picker; same-PC-twice rule enforced.
- **Final Boss:** d6 + major-foe tally spawns boss; triple treasure; extra XP roll.
- **Spells:** basic wizard/cleric prayers; druid and illusionist class tables;
  Escape; once-per-adventure expended tracking; spell tooltips on party sheets;
  exploration casting (door magic, Clues on illusion doors); scroll burn and wizard
  copy-to-spellbook.
- **Combat:** exploding-d6 attack/defense, armor/shield, corridor ranks, wandering
  rear ambush, class modifiers, minor multi-kill, major-foe level drop, morale,
  flee/withdraw, blade poison, poisonous foes (lingering poison), mirror-image
  absorption, magic resistance, subdual damage, missile combat (opening volley +
  corridor rear rank), weapon-type modifiers, once-per-adventure spell consumption.
- **Combat panel (sidebar):** foe list, per-hero targets, potions/spells, expected
  foe-attack preview, status chips, shield/ambush notes; Resolve Round and offensive
  spells skip Reactions per p.146; defensive buffs may precede Check Reactions.
- **Reactions:** per-foe bestiary reaction tables with gp-or-weapon bribes;
  category fallback for mixed groups; attack-immediately vs Check Reactions enforced.
- **Treasure:** room-content rolls logged on entry; empty hoards clear map marker;
  claim tooltips explain disabled state.
- **Map UI:** viewport zoom/pan, room-state markers (scaled/centered), icon key,
  ongoing quests, exit labels, door open/closed state.
- **Map Element Editor:** validation panel, export/import, save reload; stale
  partial Docker tile overrides no longer shadow packaged metadata.
- **Home screen:** all `dungeon_tables.json` keys plus merged `equipment_shop_table`,
  monster bestiary spawn templates, and per-foe reaction tables (all collapsed by
  default); automated test ensures table list stays in sync.

## Known Gaps

- Per-foe reaction tables still missing for some bestiary entries.
- Partial/stub spells (outdoor-only, illusionary servant, MR two-step).
- Combat panel round log summary; multi-target spell UI.
- Slay-all full grid verification.
- Body carrying for fallen heroes; resurrection rules.
- Caverns/fungal grottoes table variants.
- Map element metadata: many rows still need full rulebook calibration in editor.
- Curved/long-slope masks are approximations; paint-mask tool not built.
- Fixed 20×28 paper size option not implemented.
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
