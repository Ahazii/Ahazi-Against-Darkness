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
- Random sessions: map element rolls, placement, truncation, exploration, search,
  rest, combat, reactions, traps, treasure, wandering monsters, special events.
- **Quests:** Lady in White offer, Quest Table, progress tracking, Ongoing Quests
  panel, quest map marker, Epic Rewards on claim.
- **Economy:** Classical / Slow and Sure / Old School / Slower Advancement XP;
  wandering healer and alchemist (potion + blade poison); potions in combat or
  exploration (once per hero per adventure).
- **Final Boss:** d6 + major-foe tally spawns boss; triple treasure; extra XP roll.
- **Combat:** exploding-d6 attack/defense, armor/shield, corridor ranks, wandering
  rear ambush, class modifiers, minor multi-kill, major-foe level drop, morale,
  flee/withdraw, blade poison (+1 damage, consumed), poisonous foe follow-up saves,
  magic resistance on casters, once-per-adventure spell consumption.
- **Treasure:** room-content rolls logged on entry; empty hoards clear map marker;
  claim tooltips explain disabled state.
- **Map UI:** viewport zoom/pan, room-state markers (scaled/centered), icon key,
  ongoing quests, exit labels, door open/closed state.
- **Map Element Editor:** validation panel, export/import, save reload; stale
  partial Docker tile overrides no longer shadow packaged metadata.
- **Home screen:** all dungeon tables plus monster bestiary categories.

## Known Gaps

- Per-foe bestiary reaction rows (generic reaction tables only).
- Scroll burning, expanded MR tiers, and dedicated spell-slot tracking UI.
- Inventory carry limits; explicit weapon-type modifiers beyond blade poison.
- Quest bring-alive subdual and full slay-all grid verification.
- Body carrying for fallen heroes; resurrection rules.
- Caverns/fungal grottoes table variants.
- Map element metadata: many rows still need full rulebook calibration in editor.
- Curved/long-slope masks are approximations; paint-mask tool not built.
- Fixed 20×28 paper size option not implemented.
- Rulebook scan snippets beside structured tables.
- Imported adventure manifests and authored map play.
- Session-to-character-pool XP/gold persistence beyond manual heal/export.
- Per-square tactical positioning (marching order only).
- Ruleset/theme profiles for non-fantasy books.
- Noun Project icon attribution completeness for public release.

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.
