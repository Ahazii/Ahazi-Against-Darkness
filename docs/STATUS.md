# Current Status

Last updated: 2026-05-19

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
- Character creation uses data-driven class profiles. Characters can be selected
  for detail display, healed to full life, and deleted when not assigned to a
  party.
- Parties require exactly four distinct characters and can be selected,
  inspected, healed to full life, edited, or deleted.
- The home screen now supports class/level filtering and field sorting for
  characters, plus class/average-level filtering and sorting for parties.
  Party cards show average level and class mix, and party-pick character cards
  show level and gold.
- The home screen can export/import player data for character and party
  backups.
- The home screen links to an Icon Editor. Icons are loaded from structured
  rule data and can store a local file path, fallback marker, source URL,
  attribution, license, category, description, and notes. The editor lists
  files found in `assets/icons/user`, can add registry rows for discovered
  files, and can auto-assign obvious filenames such as monster, grave, skull,
  dungeon, and exit to the current map markers.
- Random sessions can be started from a saved party.
- Sessions are auto-persisted for refresh recovery. Explicit saved games are
  marked separately so old started sessions do not flood the Saved Games list.
- The UI renders the dungeon map and the current map element image when an
  asset exists.
- The session view replaces the setup workspace while playing. Setup can be
  reopened and the current game resumed. Browser refresh preserves the current
  view, so refreshing the home screen no longer jumps back into the dungeon.
- The current map element renders one navigation button for each available exit.
- The engine rolls starting elements from `01-06` and generated elements from
  two d6 faces (`11-66`).
- The engine stores map element rotation, rectangular footprint in grid squares,
  walkable masks, cell-shape masks, and exits anchored to exact grid-square
  edges.
- Rotated map elements now rotate both half-square masks and calibrated image
  offsets so the preview/game overlay remains aligned.
- Random placement uses walkable squares as the collision surface, allows a new
  element to use only the connecting throat of a recessed exit, reserves the
  squares immediately outside still-unconnected exits, and applies
  rulebook-style truncation when a rolled element would overlap explored
  walkable space, visible blocked artwork, or another unresolved exit.
  Truncated elements still receive room content and carry a visible-cell mask
  so removed cells also clip the bitmap on the play map.
- Exploration refuses exits that resolve back into the current map element and
  logs a metadata warning instead of recording a false move.
- Starting map elements can have a marked dungeon exit. Taking that exit
  completes the session, fully heals surviving heroes between adventures, and
  writes current character state back to the pool.
- A visual Map Element Metadata Editor is available from the main UI. The
  walkable grid overlay is directly clickable, supports half-square,
  shallow-slope, and curved-corner walkable masks, an explicit add-exit control,
  direction-derived exit labels, numbered visual exit markers, centered edge
  markers, draggable exits, multi-square exit spans, image scale/offset
  calibration beside the overlay, an original-scan comparison preview,
  mouse-wheel zoom up to 2000 percent,
  move-tool or Ctrl+drag image alignment, square grid-cell sizing, read-only
  rotation preview, and dungeon-exit marking limited to starting map elements.
  Exit labels are derived from the chosen direction and list order, then from
  the current rotation in play, so a canonical north exit can correctly become
  east, south, or west.
- Session actions exist for directional exploration, search, rest, combat rounds,
  check reactions, pay/refuse bribe, cast spell, flee, withdraw, open door,
  resolve trap, and claim treasure. Entrance/map-element selection,
  doors, room content, search, traps, treasure, and combat can log dice rolls
  and optional lookup/rule math.
- Marching order (positions 1–4) is set when saving a party via the Marching Order panel (↑↓). During exploration, party sheets also allow reordering; changes sync back to the saved party.
- The current party location is called out more strongly on the play map, and
  visible exit markers now carry compact labels that match the exit buttons.
- The play map uses a fixed viewport with scrollable map content. It supports
  button zoom/pan controls, Ctrl+mouse-wheel zoom, left-click drag panning,
  zoom shortcuts for the current room and full discovered map, auto-center when
  entering a new room, and zoom-out down to 8% for large dungeons.
- The map editor now keeps Home Screen navigation in the same browser tab,
  restores the Room Type selector beside Validation Status, adds a lock for
  image scaling/alignment controls, improves curved masks so the curve reaches
  grid edges, combines the walkable/blocked and mask tools into click-to-cycle
  brushes, removes the redundant erase-exit brush, and adds vertical plus
  horizontal two-square long slope masks. Curved-corner masks paint only the
  blocked outside corner instead of filling the whole square.
- The Map Element Metadata Editor now has validation tooling: global counts,
  list filtering for all/needs-work/errors/ready, per-element badges, and a
  checklist for missing type, missing exits, dungeon-exit mistakes, blocked
  exit anchors, duplicate exit anchors, grid shape, and rulebook validation
  status. When the selected element has warnings or errors, they are also shown
  in a dedicated issues panel above the checklist.
- Editor `?` help explains that Validation Status is a manual review flag and
  how the Ready, Needs work, and Errors tags are calculated.
- The Map Element Metadata Editor can export/import all map element metadata as
  JSON. The current reviewed metadata has been copied into
  `data/rules/tiles.json` so new deployments start with that baseline.
- The app serves a no-content favicon response so browsers do not log a local
  favicon 404.
- The play screen keeps Home Screen and Save Game in the top right, puts compact
  map controls and the log above the map, keeps current-location details, exits,
  actions, and party sheets in the side panel, and allows clicking visible exits
  on the current map element to explore them.
- The play map shows large square icon-style room state markers for active
  monsters, defeated monsters, treasure, traps, fallen party members, and
  blocked exits/dead ends created by rulebook-style truncation.
- The current-room highlight, current-party marker, and room-state icon markers
  use the post-truncation visible mask instead of the original rectangular
  footprint.
- The play screen includes a Map Icon Key. Icon hover text explains the marker,
  and the key shows source/attribution/license metadata when configured.
- The home screen exposes all structured dungeon rule tables from packaged
  `dungeon_tables.json` through `DungeonTableRoller`, including wandering monsters,
  special events/features, magic treasure, reaction tables, and basic wizard spells.
  A stale `DATA_DIR` rules override can no longer hide table groups; only table
  metadata fields are merged from overrides.
- Entry connections inherit the passage or open-door state used to enter; return paths no longer re-roll as new closed doors.
- Closed doors must be opened with Open Door before Explore/Go. Map clicks on a
  closed door attempt to open it; side-panel Go buttons stay disabled until the
  door is open.
- Post-combat treasure rolls only offer Claim Treasure when gold or items are
  present. Empty treasure rolls log "No treasure found." instead of a false
  claim prompt. Claim Treasure logs the hoard summary, per-hero gold split, and
  items awarded.
- Room content rolls can specify `enemy_tags` (for example dragon's lair roll 12
  spawns a Dragon, not a random boss).
- Open Door always writes feedback to the session log, including the working hero,
  door roll/attempt detail, and the final open/closed result.
- The play map marks door exits on the current room as open or closed (color,
  label suffix, and tooltip).
- Adventure PDFs are discovered and listed as not-yet-playable.
- The app shell sends no-cache headers and versioned static assets to avoid
  stale browser JavaScript after replacing the old prototype.

## Known Gaps

- Class data is a starter implementation and must be validated against the
  owned rulebook.
- Combat implements starter 4AD exploding-d6 attack/defense with class modifiers,
  armor-from-inventory defense bonuses, corridor front/rear assignment, wandering
  ambush, minor-foe multi-kill, morale checks, flee/withdraw, generic reaction
  tables, and basic wizard/cleric spell resolution in combat. Spell slots, magic
  resistance, per-foe bestiary reactions, poison, and special foe rules are still
  starter-only or missing.
- Doors, traps, and treasure use starter tables (2d6 doors, d6 traps/treasure,
  hidden treasure on search 6). Resolve Trap and Claim Treasure actions exist in
  the session UI. Magic treasure, carry limits, and full hidden-treasure
  complications are not fully resolved yet.
- Random map element metadata is data-driven, but most rows are placeholders and
  still need exact type, image calibration, exit, footprint, walkable, and
  cell-shape validation through the metadata editor.
- Curved, shallow-slope, and starter long-slope masks are still approximations.
  Circular rooms probably need a future paint-mask or arbitrary polygon mask
  tool if exact geometry becomes important.
- The rulebook says the usual map is a 20 by 28 square grid, but the current UI
  uses an effectively expanding map area. A selectable fixed paper size is not
  implemented yet.
- Truncation now clips removed grid cells in the play-map bitmap, but it is
  still cell-based rather than arbitrary pixel/vector clipping.
- Rule table scans are not yet shown beside structured tables. This needs page
  and coordinate metadata for each table.
- Imported adventure play requires curated adventure manifests.
- Character progression and session rewards are starter-only; manual full-heal
  controls and dungeon-exit survivor healing exist, but XP/loot award rules are
  incomplete.
- Per-character tactical square occupancy is not implemented. The checked core
  rules currently model party order with Marching Order and tile type; exact
  square positions should be added later only if needed for authored maps,
  line-of-sight, or variant rules.
- Ruleset/theme profiles are not implemented yet. They are needed before adding
  AI-assisted room description generation for non-fantasy or variant rulebooks.
- Bundled Noun Project icon files still need complete creator attribution in
  the Icon Editor before any public distribution. The source URL can be inferred
  from Noun Project filenames, but the app cannot infer the artist name.

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.
