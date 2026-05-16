# Roadmap

## Phase 1 - Clean Foundation

Status: in progress

- Replace prototype code with FastAPI + SQLite foundation.
- Preserve local PDFs and tile assets.
- Add documentation and content pipeline.
- Add character pool, exact four-character parties, and starter random sessions.
- Add a structured placeholder d66 tile definition file.
- Add smoke tests and deployment verification.

## Phase 2 - Faithful Random Dungeon MVP

Goal: one complete legal level-1 random dungeon loop.

- Encode exact class profiles from the rulebook.
- Replace placeholder `tiles.json` rows with exact d66 tile table and exit
  metadata.
- Implement doors as explicit state.
- Implement room content, search, wandering monsters, traps, treasure, clues,
  and special features.
- Implement core combat rules, saves, reactions, morale, fleeing, and death.
- Add XP, gold, equipment, spells, healing, and level-up.
- Persist session rewards back to the character pool.
- Add tests for each table and action flow.

## Phase 3 - Adventure Manifests

Goal: play one authored adventure end to end.

- Choose `caves-of-the-kobold-slave-masters.pdf` as the first import target.
- Extract map images and text.
- Build a reviewed JSON manifest with map nodes, keyed rooms, scripted events,
  adventure-specific tables, and win/loss conditions.
- Add imported adventure session mode.
- Render the authored map in the UI.

## Phase 4 - Expanded Rules and Supplements

Goal: broaden rule coverage safely.

- Treat `Four-against-the-abyss.pdf` as an expansion/supplement source.
- Add deeper dungeon rules and higher-level content after the base loop is
  stable.
- Add manifest validation tools.
- Add an admin/content review screen.

## Phase 5 - Quality and Deployment

- Add migration scripts for database changes.
- Add export/import for character pools.
- Add backup/restore guidance for Unraid.
- Add CI checks for formatting, tests, and Docker builds.
