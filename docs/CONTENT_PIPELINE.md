# Content Pipeline

## Principle

Do not interpret PDFs live during gameplay.

PDFs are source documents. Gameplay should run from structured, reviewed data
that can be validated and tested.

## Rulebook Pipeline

1. Extract text from the owned rulebook.
2. Convert mechanics into structured data:
   - classes
   - equipment
   - spells
   - monsters
   - dungeon tables
   - map element definitions
   - treasure
   - traps
   - reactions
   - level-up and campaign rules
3. Review each item against the PDF.
4. Mark each item as validated in the rule coverage tracker.
5. Add engine tests for each rule.

Map element definition rows should be updated in `data/rules/tiles.json`.
Preserve the `implementation_status` field so incomplete rows remain obvious.
On a live Unraid deployment, edited metadata is stored under the appdata rules
override, for example
`\\TOWER\appdata\ahazi-against-darkness\rules\tiles.json`. To bake reviewed
metadata into a fresh deployment, copy that file into
`C:\Coding\4AD\data\rules\tiles.json` and commit it. The editor can also export
and import the same metadata as JSON, which is the safest portable backup before
rebuilding or moving a server.

The preferred way to edit element data is the in-app Map Element Metadata
Editor. Mark each element in its canonical orientation; the engine will rotate
it during play. Set `footprint_width` and `footprint_height` in grid squares,
then calibrate the image against the overlay with `editor_cell_size`,
`image_scale`, `image_offset_x`, and `image_offset_y` from the overlay toolbar.
The editor keeps grid cells square; larger elements extend the editable canvas
instead of stretching the cells. Use the image move tool or Ctrl+drag to drag
the artwork under the grid, the clustered directional offset controls for fine
movement, and the mouse wheel over the element to zoom. Image scale supports
up to 2000 percent for awkward source art. Keep the image lock enabled while
painting masks so the mouse wheel cannot change calibration by mistake. The
original scan preview is shown beside the calibrated overlay to make exits and
edges easier to compare. Rotation preview is read-only and exists to verify how
labels and masks will look during play.

Use the editor validation panel while working through the elements. The sidebar
counts and filters show which entries have hard errors, which still need review,
and which are ready. The selected-element checklist catches missing room type,
missing exits, blocked exit anchors, duplicate exit anchors, invalid dungeon
exit placement, grid problems, and whether the row has been marked validated
against the rulebook.

Use the `?` buttons in the editor to show the current meaning of the manual
Validation Status field and the calculated Ready, Needs work, and Errors tags.

Icon artwork should be treated like other source content. Do not paste random
web icons directly into the app without a local asset file, source URL, license,
and attribution entry. Noun Project free icons are allowed when the icon is used
black-only and the artist is attributed; paid/subscription downloads can remove
that attribution requirement under their license terms. The Icon Editor reads
and writes `icons.json`, while `GET /api/rules/icons` also synthesizes default
rows for room states, playable classes, monster categories, and each named
monster. User-downloaded files should go under
`DATA_DIR/assets/icons/user/` beside `game.db`. Bundled fallback icons still ship
under `/app/assets/icons/user/`. The Icon Editor lists
supported files from both places and stores paths as `icons/user/name.svg`, so
normally you should assign internal files from the dropdown rather than upload
from your PC. The play screen uses these definitions for marker hover text and
the Map Icon Key. Existing `icons.json` rows override generated defaults; leave
generated rows unassigned when a CSS fallback glyph is enough.

Modern dashboard page artwork is separate from map icons. Page-level Relevant
Artwork slots are registered in `data/rules/artwork_registry.json` and seeded as
dimension-labelled text placeholders under `DATA_DIR/assets/Application Artwork`.
Replace the placeholder text file with the matching image filename, for example
`troupe_management_1600x900.gif`. The Developer section Artwork Manager shows
which slots are missing or present and links the related Rules Reference entry.
Keep copied PDF art local unless publication rights are secured.

Starting elements use keys `01-06`; generated elements use two d6 faces as
`11-66`. Each exit stores its canonical local `x`, `y`, `direction`, `kind`,
`span`, and optional `dungeon_exit` flag. Direction means the side of the grid
square, not necessarily the outer footprint border, so entrance/exit passages
inside a starting map element can still be marked as south-facing. Do not store
direction words such as "north left" in labels; the UI derives labels from the
user-chosen direction and the exit's row order, for example `North 1 Door`,
`South 1 Door`, or `North 2 Passage`. In play, labels are derived again after
rotation, so a canonical north exit can become east, south, or west. Mark
exactly the edge square shown on the map element. Dungeon exits are valid only
on starting elements. Numbered markers in the overlay correspond to numbered
rows in the exit list.

Use the editor grid to maintain:

- `tile_type` as `room`, `corridor`, or `unknown`
- `implementation_status` as review metadata only; it does not affect gameplay.
  Current expected values are `placeholder-needs-rulebook-validation`,
  `starter-needs-rulebook-validation`, `edited-needs-rulebook-validation`, and
  `validated`
- `walkable` rows, where `1` is usable space and `0` is blocked space
- `cell_shapes` rows, where `F` is full square, `A`/`B`/`C`/`D` are diagonal
  half-square masks, `E`/`G`/`H`/`I` are shallow-slope masks, and
  `J`/`K`/`L`/`M` are curved-corner masks. `N`/`O`/`P`/`Q` and
  `R`/`S`/`T`/`U` are two-square long slopes in vertical and horizontal
  orientations. These are per-square approximations; circular rooms and other
  irregular scanned shapes should move to a future paint-mask layer if exact
  geometry or later line-of-sight rules require more precision.
- draggable exit markers for passages, doors, and starting-element dungeon exits
- `span` for doors/passages that cover more than one adjacent square edge

The packaged `data/rules/tiles.json` catalog is the PDF-validated source copy.
Tile editor/API saves write to the configured override data directory only, so
runtime edits cannot silently change the committed rulebook catalog.

Future AI-assisted room descriptions should be an authoring aid, not an
unreviewed gameplay dependency. They need a structured ruleset/theme profile
first, so prompts can be driven by terms such as stone, brick, sci-fi bulkhead,
or wilderness without hard-coding one fantasy style into the engine.

Sessions are auto-persisted as server-side SQLite records whenever they are
created or advanced. The browser stores only the active session id so a refresh
can reload the current server record. The Saved Games list shows only sessions
that the player explicitly saves.

Characters and parties can be exported/imported from the home screen as a
single JSON file. This is intended for personal backup/restore and for moving a
player pool between deployments. Sessions remain server records; saved-game
backup should be handled through the appdata volume until a dedicated save-game
export format is added.

Heroes can transfer stored gear and home-bank gold to other roster members from
the home screen (`POST /api/characters/{id}/transfer`). During play, the same
transfers use session advance actions `transfer_item` and `transfer_gold`
(exploration only). While a session is camped outside, the Home Screen Bank
button and Camp panel Bank dialog deposit carried gold into home funds or
withdraw banked gold up to the dungeon carry cap.

The structured rules table viewer on the home screen reads from
`data/rules/dungeon_tables.json` or its override. Every table key used by the
engine should appear in that file and in `RULES_TABLE_ORDER` inside
`src/app/static/app.js`. Meta keys (`ruleset_status`, `validation`, `open_items`)
are excluded from the list. Additional home **Rules tables** groups are fed by
`GET /api/rules/monsters`, `GET /api/rules/monster-reactions`,
`GET /api/rules/tiles`, `GET /api/rules/icons`, and `GET /api/rules/classes`.
Supplemental monster files such as `fd_monsters.json`, `courtship_monsters.json`,
and `tag_monsters.json` are merged by `RulesRepository` so supplement-specific
foes can be spawnable without changing the locked Expanded Edition rows in
`monsters.json`.
The icon registry group should explain that the API returns generated defaults
plus `icons.json` overrides, not just rows physically present in the JSON file.
Keep `rulebook_reference.json` in sync when player-facing mechanics change.
Add or update **play_context** and **play_context_table** when outdoor/terrain
behavior changes. `rulebook_reference.json` is a curated implementation reference, not a full
transcription of every owned PDF. Every rule the engine exposes to the player
should be discoverable either in the searchable reference or in a structured
home Rules table. Large catalogs, roll tables, skill lists, spell lists,
bestiary rows, map elements, icon metadata, and class profiles normally belong
in structured JSON plus Rules tables; the reference should summarize the
mechanic, where it is used, and any implementation limits. Every PDF present in
`Rules/` is an approved source of truth, but a rule should not be exposed in the
app until it has been extracted into structured data or explicit engine behavior
with regression coverage.

Combat modifier rows live in `combat_modifiers_table` with supporting notes in
`combat_notes` (including `missile_combat` and `weapon_modifiers`). Per-foe
reaction tables live in `monsters.json` under `reaction_tables` and are exposed
at `GET /api/rules/monster-reactions`. Subdual damage is implemented in
`src/app/engine/subdual.py` and wired through combat and bring-alive quests.
Missile combat and weapon-type modifiers are implemented in
`src/app/engine/weapons.py` and applied in `combat.py`. Round-0 initiative
follows p.146 (`initiative_phases` in `combat.py`; session flags in
`random_dungeon.py`). Default weapons and combat swap (1 turn) follow rulebook
p.94; carry limits and over-encumbrance follow p.99 (`carry_limits` row in
`combat_modifiers_table`; starting class gear is snapshotted at session start and
does not count toward encumbrance). Bandages (p.89), even gold split on treasure claim,
and illusionary servant carry bonuses live in `inventory.py` / session actions.
Two-step MR and monster specials (regeneration, held, fog, specter swarm) are
in `combat_modifiers.py` and `combat.py`. Per-foe reaction tables are in
`monsters.json` (home monster-reactions panel); `dungeon_tables.json` category
fallback tables remain in `RULES_TABLE_ORDER` on the home page. Spell connect rolls,
damage text, and foe-specific modifiers (e.g. Fireball +2 vs mummies) belong in
`basic_spells_table` and should be mirrored in `rulebook_reference.json` (`wizard_spells`)
when engine behavior changes.

Clean adventure exit persists party rewards to the character pool via
`src/app/engine/roster_sync.py` (see `docs/ARCHITECTURE.md`).

Between-adventure gear uses `data/rules/equipment_shop.json` and the home
Equipment Shop UI (`docs/ARCHITECTURE.md`).

To show PDF scans or artwork beside each dashboard section/table, add an entry
to `data/rules/artwork_registry.json` or the override at
`DATA_DIR/rules/artwork_registry.json`. Asset paths should normally point under
`rules_art/local/` and the actual file should live at
`DATA_DIR/assets/rules_art/local/`. The `/assets/<path>` route prefers
`DATA_DIR/assets` and then falls back to bundled `/app/assets`, letting local
personal copies use PDF-derived artwork without pushing extracted art to GitHub.
Use `.png` paths for extractor-rendered PDF pages unless a separate image
conversion step is added.

Generate a configured local artwork slot with:

```bash
python tools/extract_rules_artwork.py tag_guild_workflow --force
```

The helper renders the configured PDF page from `Rules/` and writes the image to
the registry's `asset_path`. If an entry later needs an exact crop, add a
`crop_pct` object with percentage bounds (`x`, `y`, `right`, `bottom`) and rerun
the helper.

The rulebook PDF needs PDF.js or OCR-style handling for reliable extraction.
Simple Python PDF extraction is not enough for that file.

Rules Reference links should target a specific `rulebook_reference.json` entry
with `/modern/rules-reference?entry=<id>` whenever a precise entry exists. If a
specific entry does not exist yet, link to a targeted search with
`/modern/rules-reference?help=<query>` and add a concise reference entry later.
Do not paste full PDF sections into dashboard help text; use summaries, source
page citations, and short implementation notes.

## Adventure Pipelines

Two authoring paths share **one manifest schema** and the same imported-session
engine path. Full semantics: [`docs/AI_ADVENTURE_MODE.md`](AI_ADVENTURE_MODE.md).

| Path | Source | `source.type` | Primary doc section |
|------|--------|---------------|---------------------|
| **AI Adventure** | External LLM from app-generated prompt | `"ai"` | §5–9 in AI_ADVENTURE_MODE |
| **PDF extraction** | Human-reviewed import from owned PDF | `"pdf"` | below |

Schema file: `data/adventures/schema/adventure_manifest.v1.json`  
Example module: `data/adventures/examples/crypt-of-whispers/adventure.json`  
Storage: `data/adventures/{adventure_id}/adventure.json`
User editing guide: [`docs/ADVENTURE_MODULE_FORMAT.md`](ADVENTURE_MODULE_FORMAT.md)

### AI Adventure pipeline (planned)

1. Player sets parameters in the app (theme, length, boss, levels, …).
2. App builds prompt: schema summary + **live allowlists** (`build_adventure_allowlists` from server rules) + per-environment pack + example + “JSON only” rule.
3. Player copies prompt to an external LLM.
4. Player imports returned JSON → validator → preview → `data/adventures/{id}/`.
5. Player starts session → `create_session_from_manifest()` → normal play.

The AI must reference **allowlisted** monster/tile/trap/item names only; the engine
resolves all dice and combat.

### PDF extraction pipeline

0. Place owned source PDFs in `DATA_DIR/Adventure PDFs` (the legacy repo `Adventures/` folder is still scanned for local development copies), then use Adventure Management -> Modules -> **Scan new PDFs**. The scan writes metadata only to `DATA_DIR/adventure_pdf_sources.json`: title guess, page count, encryption/text-extraction status, likely module type, map/pin signals, table/foe/class package signals, confidence, warnings, and recommended conversion path.
1. Inventory PDF pages, text length, and embedded images.
2. If the PDF adds module-local content, use Adventure Management -> PDF Module Importer -> **Create / Update Package from PDF** to create a declarative package matching `data/adventures/schema/adventure_package.v1.json`. Packages live inside the adventure folder at `DATA_DIR/Adventures/<adventure_id>/package.json` and can record reviewed nodes, local tables, foes, items, class candidates, trackers, procedures, imported map assets, and map pins. They cannot execute scripts.
3. Extracted map images are stored in `DATA_DIR/Adventures/<adventure_id>/maps/`. If no embedded PDF image can be extracted, the package creates a manual map slot; place a cropped map image at the displayed `DATA_DIR/Adventures/<adventure_id>/maps/...` path. Use the package map preview to click/fill percent coordinates and tie room/hex/location ids to pins. Keep the source PDF and source page on every map/pin set so the player can audit it.
4. Use the PDF Import Review Workspace to extract and inspect candidate lists for locations/nodes, tables, foes, items, classes, and procedures. Click any candidate to inspect source page, source text, branches, table rows, procedure steps, and raw JSON. If a candidate is useful but misclassified, move it to the correct list. If it is junk, mark it wrong/ignored so it is preserved under `ignored_records` for future importer improvement.
5. Edit structured review nodes in the Location Preview / Location Editor: rooms, scenes, locations, hexes, branches, linked foes, linked items, linked procedures, map pins, app notes, and source pages. Use the Imported Record Editor for foes, items, classes, tables, trackers, and procedures before falling back to raw JSON. Keep uncertain text as `needs_pdf_check` until the PDF has been checked.
6. Create a manifest matching the v1 schema:

```json
{
  "schema_version": 1,
  "id": "example-adventure",
  "title": "Example Adventure",
  "synopsis": "Short player-facing summary (original wording).",
  "source": {
    "type": "pdf",
    "source_pdf": "Adventures/example.pdf"
  },
  "recommended_levels": [1, 2],
  "default_environment": "dungeon",
  "entrance_room_id": "room-1",
  "exit_room_id": "room-exit",
  "quest": { "key": "…", "objective_text": "…", "complete_when": { "type": "…" } },
  "rooms": [],
  "ending": { "victory_text": "…", "defeat_text": "…" }
}
```

7. Review the manifest and any package data manually against the source PDF.
8. Run automated validation (`validate_adventure_manifest()` plus the package diagnostics shown in Adventure Management).
9. Make the adventure playable only after validation passes.

Package notes:

- Use an adventure package when a PDF introduces its own maps, numbered locations, custom roll tables, new foes, new items, new classes, doom/event trackers, or branch procedures that do not fit the base manifest.
- Keep package assets in the adventure's user-facing `DATA_DIR/Adventures/<adventure_id>/` folder. Do not store user-supplied map images or private PDF-derived artwork inside the container image.
- Use percent coordinates for pins so a map can be resized without losing room/area alignment.
- If a PDF says the player chooses, represent that as a visible choice. If the PDF says to roll, let the app roll and report the result.

## First Adventure Target

Use `caves-of-the-kobold-slave-masters.pdf` first. It is short, text-extractable,
and has clear map pages.

## Copyright Handling

The app should store concise mechanical data and references needed for personal
play. Avoid embedding long verbatim passages from the PDFs in source files,
docs, or UI.
