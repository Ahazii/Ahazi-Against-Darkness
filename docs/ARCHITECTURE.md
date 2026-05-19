# Architecture

## Goals

- Implement the game as a deterministic rules engine with explicit state.
- Keep copyrighted PDFs as source material, not runtime dependencies.
- Make every rule table and adventure definition structured, reviewable, and
  testable.
- Keep deployment simple for Docker and Unraid.

## Backend

The backend is FastAPI.

Key files:

- `src/app/main.py` - HTTP API and static file mounts
- `src/app/schemas.py` - API and session state models
- `src/app/db.py` - SQLite record store
- `src/app/rules/repository.py` - packaged and user-overridden rule loading
- `src/app/engine/random_dungeon.py` - procedural session engine
- `src/app/engine/combat.py` - combat resolution
- `src/app/engine/combat_modifiers.py` - poison foes, blade poison, magic resistance
- `src/app/engine/reactions.py` - reaction and morale rolls
- `src/app/engine/spells.py` - spell resolution and MR-aware target level
- `src/app/engine/dice.py` - dice helpers

## Persistence

Runtime state is stored in SQLite:

```text
DATA_DIR/game.db
```

The current store uses a generic `records` table keyed by collection and id.
That keeps early iteration fast while still moving away from loose JSON files.
If querying becomes important, this can migrate to normalized tables while
preserving API models.

Collections:

- `characters`
- `parties`
- `sessions`

Editable rule overrides are seeded to:

```text
DATA_DIR/rules/
```

If an override file exists, it wins over the packaged file in `data/rules/`.

Current packaged rule files:

- `classes.json`
- `monsters.json`
- `dungeon_tables.json`
- `tiles.json`

## Frontend

The UI is a static browser app:

- `src/app/static/index.html`
- `src/app/static/app.js`
- `src/app/static/styles.css`

The frontend does not implement game rules. It renders state returned by the API
and sends action requests to the backend.

Home screen rule browsing:

- `GET /api/rules/tables` returns all keys from `dungeon_tables.json` except
  meta keys (`validation`, `open_items`, `ruleset_status`).
- `GET /api/rules/monsters` returns monster categories from `monsters.json` for
  the bestiary panel beside the table list.
- `RULES_TABLE_ORDER` in `app.js` controls display order; any new table used by
  the engine should be added there and to `dungeon_tables.json`.

## Map Assets

Map element GIFs live in:

```text
assets/tiles/
```

The backend serves these at:

```text
/assets/tiles/<tile>.gif
```

Map element metadata is separate from image files. Starting elements are
`01-06`; generated elements use two d6 faces as `11-66`. Fill in `tiles.json`
as rows are validated from the rulebook.

Placement state stores the element key, grid-square origin, rotation,
rectangular footprint, editor cell size, image scale/offset calibration,
walkable mask, per-square cell-shape masks, and exits. Exits carry a local grid
coordinate, direction, kind, and optional dungeon-exit marker. Cell-shape masks
currently cover full, half-square, shallow-slope, vertical and horizontal
two-square long-slope, and curved-corner approximations; arbitrary vector masks
are not implemented yet.
User-facing exit labels are derived from direction and row order, then
recalculated after rotation during play. Exit direction is the side of the local
grid square, and `span` allows a single door or passage to cover multiple
adjacent square edges.
The random dungeon engine rotates candidate map elements and computes the origin
so the selected exit edge square lines up with the entry exit edge square.
Overlap checks use occupied walkable cells and also reserve the squares
immediately outside unconnected exits, so a newly placed element cannot cover
other available doors from the same room. Rotation transforms walkable masks,
cell-shape orientation, exits, and image calibration offsets together. If an
authored exit points back into the same placed element, the engine refuses the
move and reports the metadata issue instead of changing the current tile to
itself.

The current play model is tile-level plus Marching Order. Character sheets do
not yet store exact square coordinates inside a map element; that should be a
future tactical layer for authored maps, line-of-sight, or rulesets that need it.

The rulebook fallback for a map element that cannot fit is truncation, not a
reroll. The current engine reports the condition and leaves the exit unexplored;
future truncation needs to clip walkable masks, exits, and rendered images
without losing the rolled room/corridor content.

## Source PDFs

The source PDFs stay local:

- `Rules/`
- `Adventures/`

They are ignored by git and Docker. Structured rule/adventure data derived from
them belongs in `data/rules/` or future `data/adventures/` manifests.
