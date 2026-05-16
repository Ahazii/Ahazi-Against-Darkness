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
- The d66 tile table now has a structured placeholder file at
  `data/rules/tiles.json`.
- Character creation uses data-driven class profiles.
- Parties require exactly four distinct characters.
- Random sessions can be started from a saved party.
- The UI renders the dungeon map and the current tile image when an asset exists.
- Session actions exist for exploration, search, rest, and combat rounds.
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
- Tile GIFs are incomplete. Missing files are expected for some tile keys.
- Random tile metadata is data-driven, but most rows are placeholders and still
  need exact d66 validation against the rulebook.
- Imported adventure play requires curated adventure manifests.
- Character progression and session rewards are not yet written back to the
  permanent character pool.

## Data Safety

The local rebuild did not modify `\\TOWER\appdata\ahazi-against-darkness`.
Before deploying this rebuild over the Unraid app, back up that appdata folder.
