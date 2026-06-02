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
and writes `icons.json`, and user-downloaded files should go under
`assets/icons/user/`. The Docker image copies committed project assets to
`/app/assets/icons/user/` automatically during deployment. The Icon Editor lists
supported files in that folder and stores paths as `icons/user/name.svg`, so
normally you should assign internal files from the dropdown rather than upload
from your PC. The play screen uses these definitions for marker hover text and
the Map Icon Key. Class, monster-type, item, and room-feature icon assignment
can extend the same registry.

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

Heroes can transfer inventory items and gold to other roster members from the
home screen (`POST /api/characters/{id}/transfer`). During play, the same
transfers use session advance actions `transfer_item` and `transfer_gold`
(exploration only).

The structured rules table viewer on the home screen reads from
`data/rules/dungeon_tables.json` or its override. Every table key used by the
engine should appear in that file and in `RULES_TABLE_ORDER` inside
`src/app/static/app.js`. Meta keys (`ruleset_status`, `validation`, `open_items`)
are excluded from the list. Additional home **Rules tables** groups are fed by
`GET /api/rules/monsters`, `GET /api/rules/monster-reactions`,
`GET /api/rules/tiles`, `GET /api/rules/icons`, and `GET /api/rules/classes`.
Keep `rulebook_reference.json` in sync when player-facing mechanics change.

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

To show PDF scans beside each table, add source page and crop coordinates to
the structured table data, then generate cached images from the rulebook PDF.

The rulebook PDF needs PDF.js or OCR-style handling for reliable extraction.
Simple Python PDF extraction is not enough for that file.

## Adventure Pipeline

1. Inventory PDF pages, text length, and embedded images.
2. Extract map images into a local working folder.
3. Extract room/key text.
4. Create a manifest:

```json
{
  "id": "example-adventure",
  "name": "Example Adventure",
  "source_pdf": "Adventures/example.pdf",
  "recommended_levels": [1, 2],
  "maps": [
    {
      "id": "chapter-one",
      "image": "assets/adventures/example/chapter-one-map.png",
      "nodes": []
    }
  ],
  "rooms": [],
  "tables": [],
  "victory": {}
}
```

5. Review the manifest manually.
6. Add automated validation.
7. Make the adventure playable only after validation.

## First Adventure Target

Use `caves-of-the-kobold-slave-masters.pdf` first. It is short, text-extractable,
and has clear map pages.

## Copyright Handling

The app should store concise mechanical data and references needed for personal
play. Avoid embedding long verbatim passages from the PDFs in source files,
docs, or UI.
