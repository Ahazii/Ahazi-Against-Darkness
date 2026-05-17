# Current Status

Last updated: 2026-05-17

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
- Random sessions can be started from a saved party.
- Sessions are auto-persisted for refresh recovery. Explicit saved games are
  marked separately so old started sessions do not flood the Saved Games list.
- The UI renders the dungeon map and the current map element image when an
  asset exists.
- The session view replaces the setup workspace while playing. Setup can be
  reopened and the current game resumed.
- The current map element renders one navigation button for each available exit.
- The engine rolls starting elements from `01-06` and generated elements from
  two d6 faces (`11-66`).
- The engine stores map element rotation, rectangular footprint in grid squares,
  walkable masks, cell-shape masks, and exits anchored to exact grid-square
  edges.
- Rotated map elements now rotate both half-square masks and calibrated image
  offsets so the preview/game overlay remains aligned.
- Random placement uses the full map-element footprint as the paper area,
  reserves the squares immediately outside still-unconnected exits, and applies
  rulebook-style logical truncation when a rolled element would overlap explored
  space or cover another unresolved exit. Truncated elements still receive room
  content.
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
- Session actions exist for directional exploration, search, rest, and combat
  rounds. Entrance/map-element selection, doors, room content, search, and
  combat can log dice rolls and optional lookup/rule math.
- The current party location is called out more strongly on the play map, and
  visible exit markers now carry compact labels that match the exit buttons.
- The play map supports button zoom/pan controls, Ctrl+mouse-wheel zoom, and
  Shift/middle-button drag panning.
- The map editor now keeps Home Screen navigation in the same browser tab,
  restores the Room Type selector beside Validation Status, adds a lock for
  image scaling/alignment controls, improves curved masks so the curve reaches
  grid edges, combines the walkable/blocked and mask tools into click-to-cycle
  brushes, removes the redundant erase-exit brush, and adds vertical plus
  horizontal two-square long slope masks. Curved-corner masks paint only the
  blocked outside corner instead of filling the whole square.
- The play screen keeps Home Screen and Save Game in the top right, puts compact
  map controls and the log above the map, keeps current-location details, exits,
  actions, and party sheets in the side panel, auto-fits the map by default, and
  allows clicking visible exits on the current map element to explore them.
- The home screen exposes the currently structured rule tables used by the
  starter engine.
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
  still need exact type, image calibration, exit, footprint, walkable, and
  cell-shape validation through the metadata editor.
- Curved, shallow-slope, and starter long-slope masks are still approximations.
  True arbitrary vector masks are still a future content-tooling improvement.
- The rulebook says the usual map is a 20 by 28 square grid, but the current UI
  uses an effectively expanding map area. A selectable fixed paper size is not
  implemented yet.
- Logical truncation is implemented for collision and exit availability, but
  visual truncation/clipping of map element images is not implemented yet.
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

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.
