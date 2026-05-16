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
`image_scale`, `image_offset_x`, and `image_offset_y`. The editor keeps grid
cells square; larger elements extend the editable canvas instead of stretching
the cells.

Starting elements use keys `01-06`; generated elements use two d6 faces as
`11-66`. Each exit stores a local `x`, `y`, `direction`, `kind`, and optional
`dungeon_exit` flag. Mark exactly the edge square shown on the map element.
Dungeon exits are valid only on starting elements.

Use the editor grid to maintain:

- `tile_type` as `room`, `corridor`, or `unknown`
- `walkable` rows, where `1` is usable space and `0` is blocked space
- `cell_shapes` rows, where `F` is full square and `A`/`B`/`C`/`D` are diagonal
  half-square walkable shapes for future line-of-sight and movement rules
- draggable exit markers for passages, doors, and starting-element dungeon exits

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
