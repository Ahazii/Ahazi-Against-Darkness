# Adventure Module File Format

This guide explains the user-facing adventure module folder used by Ahazi Against Darkness.

All user-created, generated, imported, or PDF-reviewed modules should live under:

```text
DATA_DIR/Adventures/<module_id>/
```

On the Unraid install, `DATA_DIR` is the appdata folder beside `game.db`.

## Folder Layout

```text
DATA_DIR/Adventures/<module_id>/
  adventure.json      # playable module manifest
  package.json        # PDF/import review package, maps, pins, local additions
  maps/               # map images extracted from or supplied for the module
  artwork/            # local/private artwork for this module
  tables/             # optional user notes or table source files
  notes/              # reviewer notes, playtest notes, source notes
```

`adventure.json` is the playable module. The app can start it from Go Adventure once it validates.

`package.json` is the review workspace. It is where PDF importer guesses, manually reviewed scenes, map pins, local foes, tables, procedures, and notes are held before conversion.

## adventure.json

Use `adventure.json` when the module is ready to play.

Required top-level fields:

```json
{
  "schema_version": 1,
  "id": "example-module",
  "title": "Example Module",
  "synopsis": "Short player-facing summary.",
  "source": {
    "type": "pdf",
    "source_pdf": "Adventure PDFs/example.pdf"
  },
  "recommended_levels": [1, 2],
  "default_environment": "dungeon",
  "entrance_room_id": "room-1",
  "exit_room_id": "room-exit",
  "quest": {
    "key": "main_objective",
    "objective_text": "What the party is trying to do.",
    "complete_when": {
      "type": "room_reached",
      "room_id": "room-exit"
    }
  },
  "rooms": [],
  "ending": {
    "victory_text": "What happens if the party wins.",
    "defeat_text": "What happens if the party fails."
  }
}
```

Rooms need:

```json
{
  "id": "room-1",
  "tile_key": "02",
  "title": "Entrance Hall",
  "description": "Player-facing room text.",
  "environment": "dungeon",
  "exits": [
    {
      "id": "room-1-north",
      "direction": "north",
      "to": "room-2",
      "kind": "door",
      "status": "closed"
    }
  ],
  "triggers": []
}
```

Important limits:

- `id` must be a lowercase slug using letters, digits, and hyphens.
- `tile_key` must be an existing map element key such as `01`, `12`, or `66`.
- `default_environment` must currently be `dungeon`, `caverns`, or `fungal_grottoes`.
- Exits must point to real room ids.
- Foes, items, traps, and events should use names/keys the app knows, unless they are declared in package data and later supported by conversion code.

## package.json

Use `package.json` while reviewing an imported PDF or preparing a module with custom local material.

Packages are declarative. They must not contain scripts, Python, JavaScript, shell commands, or arbitrary expressions.

Typical package:

```json
{
  "schema_version": 1,
  "package_id": "example-module",
  "title": "Example Module",
  "source": {
    "type": "pdf",
    "source_pdf": "Adventure PDFs/example.pdf",
    "source_pages": [1, 2, 3],
    "license_note": "Private-use package from a user-owned PDF."
  },
  "capabilities": ["maps", "pins", "tables", "foes"],
  "nodes": [],
  "maps": [],
  "tables": [],
  "foes": [],
  "items": [],
  "trackers": [],
  "procedures": [],
  "review": {
    "status": "draft_review_needed",
    "notes": "What has been checked and what still needs review."
  }
}
```

## Review Nodes

`nodes` are the best place to manually check imported PDF content. A node can be a room, scene, numbered location, hex, camp, settlement, or ending.

```json
{
  "id": "scene-10",
  "type": "scene",
  "title": "The Hunter's Cabin",
  "source_page": 25,
  "player_text": "Reviewed player-facing text from the source.",
  "app_notes": "Stealth save, possible assassin ambush, then branch to scene-1 or return to town.",
  "branches": [
    {
      "label": "Go to the cabin",
      "condition": "After resolving the assassins",
      "to": "scene-1",
      "source_text": "Once this encounter is over, you may reach the cabin by playing Scene 1."
    }
  ],
  "review_status": "ready_for_manifest"
}
```

Use `player_text` for what the player should read.

Use `app_notes` for dice, saves, monster handling, rewards, procedure notes, and anything the app should automate later.

Use `branches` for printed choices, doors, scene jumps, save results, routes, or endings.

## Candidate Lists From PDFs

The PDF Import Review Workspace can extract candidate records from the source PDF text. These are shown in clickable lists:

- Locations
- Tables
- Foes
- Items
- Classes
- Procedures

Candidate records are guesses. They normally start with `review_status: "needs_pdf_check"`.

Use the detail pane to inspect:

- source page
- source text
- branches
- table rows
- procedure steps
- notes
- raw JSON for that record

Only change a record to `checked` or `ready_for_manifest` after comparing it with the source PDF.

Common fixes after extraction:

- Rename noisy candidate titles.
- Split a long location into multiple nodes.
- Remove table rows that were actually numbered room entries.
- Move monster stat text from `items` to `foes`.
- Add missing branch targets when the PDF says "go to Scene X".
- Add app notes for saves, rolls, rewards, and choices the app should automate later.

## Correcting Misclassified Records

The review browser lets you correct candidate records without editing the whole JSON file by hand.

Use **Move Record** when the candidate is useful but in the wrong list. For example:

- move a monster from Items to Foes
- move a numbered room from Tables to Locations
- move a choice/save instruction from Locations to Procedures

Use **Mark Wrong / Ignore** when the candidate is not useful. For example:

- page headers
- copyright/footer text
- repeated table titles
- examples that are not part of the adventure
- numbering that is not a room, table row, or procedure

Ignored records are preserved in `ignored_records` so future importer improvements can see what was classified incorrectly. They are not used for playable conversion.

Moved records keep `original_extraction` metadata showing the original detected list and source text.

## Maps And Pins

Map images belong in:

```text
DATA_DIR/Adventures/<module_id>/maps/
```

Pins use percent coordinates so they survive resizing:

```json
{
  "id": "pin-room-1",
  "label": "1",
  "node_id": "room-1",
  "x": 42.5,
  "y": 63,
  "shape": "point"
}
```

`node_id` should match a reviewed node id, then later a playable room id.

## Procedures

Procedures are small declarative steps the app can later automate. Allowed operations include:

- `roll_table`
- `spawn_foes`
- `test_save`
- `grant_gold`
- `grant_item`
- `set_tracker`
- `advance_tracker`
- `branch_if`
- `transition_to_node`
- `complete_objective`
- `pin_location`
- `show_choice`

If the PDF says the player chooses, represent it as a visible choice. If the PDF says to roll, let the app roll and report the result.

## Safe Editing Workflow

1. Put the PDF in `DATA_DIR/Adventure PDFs`.
2. Use Adventure Management -> PDF Module Importer -> Scan new PDFs.
3. Create or refresh the package.
4. Review and edit package details, nodes, maps, pins, tables, foes, items, and procedures.
5. Mark nodes `ready_for_manifest` only after checking the source PDF.
6. Convert to `adventure.json` only after validation reports no structural errors.
7. Playtest, then correct the package or manifest as needed.

## Copyright Boundary

Keep private-use PDF prose and extracted artwork in your local `DATA_DIR`.

Do not commit or distribute long verbatim PDF text or PDF-derived artwork unless you have publishing rights.
