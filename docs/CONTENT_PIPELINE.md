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

The preferred way to edit element data is the in-app Map Element Metadata
Editor. Mark each element in its canonical orientation; the engine will rotate
it during play. Set `footprint_width` and `footprint_height` in grid squares,
then calibrate the image against the overlay with `editor_cell_size`,
`image_scale`, `image_offset_x`, and `image_offset_y` from the overlay toolbar.
The editor keeps grid cells square; larger elements extend the editable canvas
instead of stretching the cells. Use the image move tool or Ctrl+drag to drag
the artwork under the grid, the clustered directional offset controls for fine
movement, and the mouse wheel over the element to zoom. Image scale supports
up to 2000 percent for awkward source art. Rotation preview is read-only and
exists to verify how labels and masks will look during play.

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
  `J`/`K`/`L`/`M` are curved-corner masks. These are per-square approximations;
  exact arbitrary polygon masks are future tooling if line-of-sight requires
  more precision.
- draggable exit markers for passages, doors, and starting-element dungeon exits
- `span` for doors/passages that cover more than one adjacent square edge

Future AI-assisted room descriptions should be an authoring aid, not an
unreviewed gameplay dependency. They need a structured ruleset/theme profile
first, so prompts can be driven by terms such as stone, brick, sci-fi bulkhead,
or wilderness without hard-coding one fantasy style into the engine.

The Erase Exit tool only removes an exit from the clicked edge. It does not
change walkable squares or half-square shapes.

Sessions are auto-persisted as server-side SQLite records whenever they are
created or advanced. The browser stores only the active session id so a refresh
can reload the current server record. The Saved Games list shows only sessions
that the player explicitly saves.

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
