# Roadmap

## Phase 1 - Clean Foundation

Status: in progress

- Replace prototype code with FastAPI + SQLite foundation.
- Preserve local PDFs and tile assets.
- Add documentation and content pipeline.
- Add character pool, exact four-character parties, and starter random sessions.
- Add a structured placeholder map element definition file.
- Add first-pass map element rotation and metadata editing.
- Add smoke tests and deployment verification.

## Phase 2 - Faithful Random Dungeon MVP

Goal: one complete legal level-1 random dungeon loop.

- Encode exact class profiles from the rulebook.
- Replace placeholder `tiles.json` rows with exact starting (`01-06`) and
  generated (`11-66`) map element metadata.
- Validate map element footprints and multiple exits on the same edge through
  the visual metadata editor. Exits are anchored to exact grid-square edges.
- Validate full-footprint placement and logical truncation against more
  rulebook examples, especially cases where other exits would be covered.
- Add optional fixed paper size, defaulting to the rulebook's 20 by 28 squares,
  while keeping an unlimited map mode for screen play.
- Implement visual truncation when a rolled map element would overlap existing
  explored space, including clipping its visible image/mask while preserving
  content generation on the remaining squares.
- Add paint-mask or arbitrary polygon mask authoring if the per-square
  shallow-slope, two-square long-slope, and curved-corner masks are not precise
  enough for circular rooms or later line-of-sight needs.
- Implement doors as explicit state.
- Implement room content, search, wandering monsters, traps, treasure, clues,
  and special features.
- Implement a dedicated combat panel/window with per-character actions,
  spells, healing, inventory, weapon selection, and enemy targeting.
- Implement core combat rules, saves, reactions, morale, fleeing, and death.
- Expand dice trace coverage so combat, treasure, traps, reactions, morale, and
  saves can show the same roll/math detail as the starter exploration actions.
- Add XP, gold, equipment, spells, detailed healing/recovery, and level-up.
- Add a structured table source map so home-screen rule tables can show scanned
  snippets from the rulebook beside the reviewed text data.
- Add a local icon registry and assignment editor for character classes,
  monsters, treasure, traps, and room-state markers, with license and
  attribution fields for imported SVGs.
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
- Extend the map editor workflow for authored maps once manifests exist.
- Add per-character square positions only where authored maps, line-of-sight,
  or variant rules require them; keep core 4AD Marching Order rules as the
  baseline combat model.

## Phase 4 - Expanded Rules and Supplements

Goal: broaden rule coverage safely.

- Treat `Four-against-the-abyss.pdf` as an expansion/supplement source.
- Add deeper dungeon rules and higher-level content after the base loop is
  stable.
- Add ruleset/theme profiles for alternate books so shared engine concepts can
  be reused while theme, tables, and allowed mechanics vary.
- Consider AI-assisted room description generation as a reviewed authoring tool
  after ruleset/theme profiles exist.
- Add manifest validation tools.
- Add an admin/content review screen.

## Phase 5 - Quality and Deployment

- Add migration scripts for database changes.
- Extend export/import beyond characters and parties to include saved games,
  icon metadata, and optional full appdata snapshots.
- Add backup/restore guidance for Unraid.
- Add CI checks for formatting, tests, and Docker builds.
