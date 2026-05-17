# Ahazi Against Darkness

A local web app for playing a book-driven dungeon RPG with persistent character
pools, four-character parties, random dungeon sessions, and reviewed adventure
manifests built from owned PDFs.

This repository is being rebuilt around a rules-engine-first design. The current
state is a playable starter shell, not a complete implementation of every rule.
The documentation in `docs/` is part of the working product and should be kept
current with every rules or content change.

## Current Capabilities

- FastAPI backend
- SQLite persistence in `DATA_DIR/game.db`
- Data-driven starter class and monster definitions
- Character pool
- Character detail/delete controls
- Exactly four-character parties with detail/edit/delete controls
- Random dungeon session creation
- Active sessions reload after browser refresh, with explicit server-side saved games
- Basic map rendering with existing map element GIFs where available
- Grid-square footprints, walkable masks, edge exits, and rotation-aware random placement
- Visual map element metadata editor with image calibration, square grid cells,
  mouse-wheel zoom, drag-to-align artwork, rotation preview,
  direction-derived numbered exits, multi-square exit spans, and half-square
  walkable markers
- Dungeon-exit completion with starter character-state writeback
- Basic exploration, search, rest, and combat-round actions
- PDF adventure discovery with imported adventures marked as needing manifests

## Preserved Source Material

The folders below are intentionally kept out of git and Docker image builds:

- `Rules/`
- `Adventures/`

They contain the owned PDFs used for analysis and content extraction. Runtime
gameplay should use reviewed structured manifests, not live PDF scraping.

## Development

```powershell
docker compose -f docker-compose.dev.yml up --build
```

Then open:

```text
http://127.0.0.1:8000
```

Local test command:

```powershell
$env:PYTHONPATH="C:\Coding\4AD\src"; python -m pytest -q
```

For the Unraid deployment, the container should keep using:

```text
DATA_DIR=/data
Appdata=/mnt/user/appdata/ahazi-against-darkness
```

Your currently hosted instance is expected at:

```text
http://192.168.1.55:8001
```

## Project Layout

```text
src/app/                  FastAPI app, schemas, SQLite store, rules engine
src/app/static/           Browser UI
data/rules/               Packaged starter rule data
assets/tiles/             Reused dungeon map element images
docs/                     Architecture, roadmap, and content pipeline docs
tools/                    Offline PDF/content helper scripts
Rules/                    Local rule PDFs, ignored by git
Adventures/               Local adventure PDFs, ignored by git
```

## Documentation

- `docs/STATUS.md` - what works now and what does not
- `docs/ARCHITECTURE.md` - application design
- `docs/ROADMAP.md` - implementation phases
- `docs/CONTENT_PIPELINE.md` - PDF-to-manifest workflow
- `docs/RULE_COVERAGE.md` - rule implementation checklist

## Important Direction

The correct path is not to make the app read PDFs during play. PDFs are source
documents. The app should run from curated, structured rules and adventure data
that can be tested.
