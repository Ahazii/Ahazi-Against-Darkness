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
- Character detail, heal, and delete controls
- Exactly four-character parties with detail/edit/delete controls
- Party heal control for between-session upkeep
- Player data export/import for character and party backups
- Local icon registry and Icon Editor for assigning downloaded SVG/PNG files,
  source URLs, licenses, and attribution, with automatic discovery of files in
  `DATA_DIR/assets/icons/user`
- Random dungeon session creation
- Active sessions reload after browser refresh, with explicit server-side saved games
- Session play opens in its own game view, with a return path to setup
- Basic map rendering with existing map element GIFs where available
- Grid-square footprints, walkable masks, eight-direction exits, rotation-aware random
  placement, unresolved-exit reservation, and logical truncation
- Play map state markers for active monsters, treasure, traps, dead-end exits,
  defeated monsters, and fallen party members
- Visual map element metadata editor with image calibration, square grid cells,
  original-scan comparison, mouse-wheel zoom, drag-to-align artwork, rotation preview,
  direction-derived numbered exits, multi-square exit spans, half-square,
  shallow-slope, long-slope, and curved-corner walkable markers
- Editor validation help explaining manual validation status and Ready/Needs
  work/Errors list tags, with selected-element warnings/errors shown directly
  on the editor page
- Map element metadata export/import from the editor
- Play map zoom/pan controls, current-room and whole-map zoom shortcuts,
  mouse-wheel zoom around the pointer, and mouse-drag panning
- Dungeon-exit completion with survivor healing and starter character-state writeback
- Basic exploration, search, rulebook Rest (p.114: once/adventure, nail doors, ability recovery, wanderer roll, halfling Nourishing Meal), and combat-round actions, with optional roll
  and table-lookup log detail for supported starter actions
- Tier 1 class abilities: barbarian rage, halfling Luck (flee / attack / defense / save / search / treasure reroll), swashbuckler Panache, paladin prayer heal and save reroll
- Tier 1–4 class tricks: acrobat/gnome/illusionist/assassin/mushroom monk/paladin/light gladiator/swashbuckler/bulwark/kukla abilities per home `class_tricks_implementation_table`
- Combat Focus layout (tactical map, command rail, hero drawer, multi-target planning)
- Quests (Lady in White, Quest Table, Ongoing Quests panel, Epic Rewards, bring-alive subdual)
- Economy (four campaign modes, tier dice, tier training, L5+ expert-skill fork, wandering healer/alchemist, potions, Final Boss)
- Magic weapons from treasure (d6 type roll, +1 Attack when wielded, class restrictions for use, carrier fallback for loot pickup)
- Clue Secrets for hidden treasure, magic item locations, and basic scroll locations
- Combat modifiers (blade poison, poisonous foes, magic resistance, subdual damage, missile combat, weapon-type modifiers)
- Reactions (per-foe bestiary tables, weapon bribes, category fallback)
- Split party support: leave behind, rejoin, true scout-ahead with Stealth Save, immediate scout Final Boss reveal, failed-scout rescue/flee choices, detached combat rounds, active detached-group navigation from map doors or the Exits panel
- Combat foe chips above the map/tactical stage, with category colors, grouped minor foes, and clear Final Boss emphasis
- Searchable curated rules reference (rest, combat, Combat Focus, class abilities, camp/bank/transfer, tier training, expert skills chapter) plus home-screen viewer for structured tables: expert skill catalogs and implementation status, tier training costs, monster bestiary, reaction tables, map elements, icon registry, and class profiles
- Expanded spells (druid, illusionist, Escape, scrolls, exploration door magic) with spell tooltips; outdoor **play context** (environment + terrain + weather flags) gates EE outdoor spells and ranger double missile without a hex map
- Item and gold transfer between heroes (home roster and in-adventure party sheet)
- In-game map icon key with hover text and attribution/license display
- PDF adventure discovery with imported adventures marked as needing manifests
- Developer Rules PDF Import for owned Tales from The Adventures Guild PDFs:
  uploaded PDFs live in `DATA_DIR/rules`, extracted local narrative lives in
  `DATA_DIR/tag_scene_narrative_overrides.json`, and generated Adventures Guild
  modules can refresh older saved sessions from that local-only prose without
  committing copied PDF text to the repository
- PDF / Supplement Workbench source scans under `DATA_DIR/Supplements/_sources`
  support manual block assignment, page-offset metadata, package assets,
  explicit overwrite/rebuild of reviewed source blocks, and a review-first
  duplicate cleanup tool for local imported PDFs. The workbench also has a
  guarded source reset that removes reviewed blocks, reviewed tables, extracted
  artwork, package assets, and rendered PDF page cache for a selected source so
  a PDF can be reimported from a genuinely clean local state. Printed-page
  offsets and package membership can also be corrected after indexing and
  extraction; existing assignments, edited blocks, artwork review, table
  drafts, and exact-text index entries are relabelled without rescanning.
  The review tree groups every block by category and PDF page without a hard
  block limit, applies multi-block assignments in one operation, splits at a
  caret placed directly in the displayed block text, and restores open pages,
  scroll position, and package asset tools after saves. Compact sticky controls,
  an overlaid PDF toolbar, and a persistent draggable column divider keep the
  source page and content tree usable together. Import fields, source actions,
  summary chips, and PDF controls wrap at reduced widths; the review columns
  stack automatically when the available workbench width becomes too narrow.
  A dedicated Merge Page command combines every non-ignored fragment from one
  physical PDF page without requiring the reviewer to select dozens of blocks.
  Reviewed blocks can also create
  package-level supplement requirements that preserve exact source wording while
  separately recording editable party eligibility, dependencies, triggers, and
  conditional table routing for future activation.

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
python -m pytest -q
```

(`pytest.ini` adds `src` to the import path; Docker dev compose still sets `PYTHONPATH=/app/src`.)

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
assets/                   Bundled fallback image/icon/tile assets
DATA_DIR/assets/          User-facing artwork, icons, tiles, and module assets
DATA_DIR/assets/Application Artwork/
                           Modern dashboard page artwork slots
docs/                     Architecture, roadmap, and content pipeline docs
tools/                    Offline PDF/content helper scripts
Rules/                    Local rule PDFs, ignored by git
Adventures/               Local adventure PDFs, ignored by git
```

Runtime user data that should be backed up lives under `DATA_DIR`, including
`game.db`, `Adventures/`, `rules/`, and `assets/`. In Docker/Unraid this is the
appdata share, for example `\\TOWER\appdata\ahazi-against-darkness`.
Use `DATA_DIR/assets/Application Artwork` for the modern dashboard Relevant
Artwork slots, `DATA_DIR/assets/artwork/user` for adventure/scene/portrait
artwork, and `DATA_DIR/assets/icons/user` for Icon Editor files.

## Documentation

- `docs/STATUS.md` - what works now and what does not
- `docs/ARCHITECTURE.md` - application design
- `docs/ROADMAP.md` - implementation phases
- `docs/SUPPLEMENTS_AND_STATES.md` - target architecture for optional
  supplements, state definitions, terrain, maps, room tiles, and rule hooks
- `docs/PROJECT_RELEVANCE_AUDIT.md` - cleanup/relevance audit before the
  supplement/state refactor
- `docs/CONTENT_PIPELINE.md` - PDF-to-manifest workflow
- `docs/ARTWORK_IDEAS.md` - dashboard and gameplay artwork placement ideas
- `docs/RULE_COVERAGE.md` - rule implementation checklist
- `docs/MASTER_RULE_COVERAGE.md` - program-level status across EE, Abyss,
  Forsaken Depths, Adventurers' Guild, and Netherworld
- `docs/reference/equipment-matrix.csv` - per-item shop/treasure/engine wiring audit (dev reference; not loaded by the app)

## Important Direction

The correct path is not to make the app read PDFs during play. PDFs are source
documents. The app should run from curated, structured rules and adventure data
that can be tested.
