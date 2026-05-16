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
walkable mask, half-square cell shapes, and exits. Exits carry a local grid
coordinate, direction, kind, editable label, and optional dungeon-exit marker.
The random dungeon engine rotates candidate map elements and computes the origin
so the selected exit edge square lines up with the entry exit edge square.
Current overlap checks use the rectangular footprint; the walkable and
half-square masks are stored for movement/UI and future irregular placement
rules.

## Source PDFs

The source PDFs stay local:

- `Rules/`
- `Adventures/`

They are ignored by git and Docker. Structured rule/adventure data derived from
them belongs in `data/rules/` or future `data/adventures/` manifests.
