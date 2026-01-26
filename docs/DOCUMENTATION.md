# Documentation

## Architecture Overview
The app is split into:
- **Backend (FastAPI)** for sessions, rules, tables, and persistence.
- **Frontend (static)** for UI, map rendering, and table editor.
- **Data layer (JSON)** for tables, tiles, and future adventure content.

## Key Paths
- Backend entry: `app/main.py`
- Rules + tables: `app/game/`
- Table data: `app/game/data/`
- Static UI: `static/`

## API Summary
- `GET /api/characters` — list characters
- `POST /api/characters` — create character
- `GET /api/parties` — list parties
- `POST /api/parties` — create party
- `POST /api/sessions` — start session
- `GET /api/sessions/{id}` — get session
- `POST /api/sessions/{id}/advance` — actions (explore/search/reaction)
- `GET /api/tables` — list implemented tables
- `GET /api/tables/details` — full table data
- `PUT /api/tables/details` — save edited table data

## Tables & Tiles
Data is stored as JSON to keep the rules editable:

- `dungeon_tables.json` — monster/door/loot tables
- `tile_shapes.json` — tile metadata (doors + type)
- `tile_table.json` — d66 mapping to tile IDs and images

Tile images are loaded from:
```
static/tiles/
```
Update `tile_table.json` to point to those image files.

## Session UI
Sessions open in a dedicated window:
- Map + tile visual
- Room description + encounter state
- Character sheets (Life/Attack/Defense)
- Action controls (Explore, Search, Reactions, Combat)

## Persistence
Data is stored in `DATA_DIR`. On Unraid, use:
- `PUID=99`
- `PGID=100`

## Development
```
docker compose -f docker-compose.dev.yml up --build
```

## Editing Tables
Open the Tables page from the main UI:
- View full table values and roll ranges
- Edit JSON and save to `/data`

## Open Questions
- Final d66 tile table image set
- Full class list and progression
- Exact loot/trap implementations
