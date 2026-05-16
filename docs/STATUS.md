# Current Status

Last updated: 2026-05-16

## Summary

The old prototype has been removed. The project now has a clean FastAPI +
SQLite foundation with a browser UI and a starter random dungeon engine.

This is not yet a faithful full implementation of the rulebook. It is the
foundation for implementing the rulebook safely.

## Working

- App starts from `src/app/main.py`.
- Runtime state is stored in `DATA_DIR/game.db`.
- Starter rules are loaded from `data/rules/`, with editable overrides seeded to
  `DATA_DIR/rules/` in Docker.
- The map element table now has a structured placeholder file at
  `data/rules/tiles.json`.
- Character creation uses data-driven class profiles.
- Parties require exactly four distinct characters.
- Random sessions can be started from a saved party.
- The UI renders the dungeon map and the current map element image when an
  asset exists.
- The current map element renders one navigation button for each available exit.
- The engine rolls starting elements from `01-06` and generated elements from
  two d6 faces (`11-66`).
- The engine stores map element rotation, rectangular footprint in grid squares,
  walkable masks, and exits anchored to exact grid-square edges.
- Starting map elements can have a marked dungeon exit. Taking that exit
  completes the session and writes current character state back to the pool.
- A visual Map Element Metadata Editor is available from the main UI.
- Session actions exist for directional exploration, search, rest, and combat rounds.
- Adventure PDFs are discovered and listed as not-yet-playable.
- The app shell sends no-cache headers and versioned static assets to avoid
  stale browser JavaScript after replacing the old prototype.

## Known Gaps

- Class data is a starter implementation and must be validated against the
  owned rulebook.
- Combat is intentionally basic and does not yet implement every class ability,
  spell, reaction, morale, fleeing, poison, special foe rule, or campaign rule.
- Search, door, trap, treasure, and wandering monster behavior are starter
  mechanics only.
- Random map element metadata is data-driven, but most rows are placeholders and
  still need exact exit/footprint/walkable validation through the metadata
  editor.
- Imported adventure play requires curated adventure manifests.
- Character progression and session rewards are starter-only; writeback exists
  when the dungeon is completed, but XP/loot award rules are incomplete.

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.
