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
  "capabilities": ["maps", "pins", "tables", "foes", "items", "states", "rules"],
  "nodes": [],
  "maps": [],
  "tables": [],
  "foes": [],
  "items": [],
  "states": [],
  "rules": [],
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
  "foe_ids": ["assassin-agent"],
  "item_ids": ["emerald-necklace"],
  "procedure_ids": ["stealth-save-ambush"],
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

## Location Preview And Editor

The PDF Import Review Workspace includes a Location Preview for each node.

The preview answers: "If this became a playable room/location, what would the player see and what would the app need to handle?"

It shows:

- title, id, type, source page, and review status
- player-facing description
- app/rules notes
- linked foes
- linked items, rewards, or services
- exits and choices from `branches`
- linked procedures such as saves, rolls, table lookups, or special handling
- linked map pins and map artwork when available

The Location Editor lets you edit:

- node id
- type
- title
- source page
- review status
- player description
- app/rules notes
- linked foe ids
- linked item ids
- linked procedure ids
- linked map pin id
- exits/choices JSON

Use linked ids when possible. For example, if a location contains a Black Knight, move or create a Foes record with id `black-knight`, then add `black-knight` to the location's `foe_ids`.

This composer-style data is intended to be reused by the future hand-authored adventure creator.

## Foes, Items, Classes, States, Rules, Tables, Trackers, And Procedures

The PDF Import Review Workspace also includes an Imported Record Editor for module-local records.

Use it before editing raw JSON directly. It lets you review and edit:

- foes
- items, rewards, services, or special equipment
- class candidates
- states or conditions that can apply to characters, parties, foes, or items
- module-local rules
- roll tables
- trackers
- app procedures

Foes, items, and classes use a flexible source-backed record:

```json
{
  "id": "assassin-agent",
  "name": "Assassin Agent",
  "source_page": 25,
  "notes": "HCL+2 minion armed with dagger.",
  "review_status": "needs_pdf_check"
}
```

Because different PDFs describe foes, classes, items, states, rules, and services differently, extra fields are allowed. Use the editor's Extra JSON box for module-specific details such as `level`, `hcl`, `attack`, `life`, `treasure`, `price_gp`, `equipment_tags`, `skill_options`, `class_features`, or publisher wording that still needs checking.

Item records have structured fields for the common cases:

```json
{
  "id": "emerald-necklace",
  "name": "Emerald Necklace",
  "source_page": 25,
  "description": "Reviewed summary of what the item is and what it does.",
  "modifiers": [],
  "states_applied": [],
  "sale_price_gp": 200,
  "sellable": true,
  "buyable": false,
  "review_status": "needs_pdf_check"
}
```

State records should describe the target, duration, modifiers, and removal method:

```json
{
  "id": "hypnotised",
  "name": "Hypnotised",
  "source_page": 14,
  "description": "Reviewed condition summary.",
  "applies_to": "character",
  "duration": "Until the printed recovery condition is met.",
  "modifiers": [],
  "removal": "Check the PDF scene.",
  "review_status": "needs_pdf_check"
}
```

Rule records should capture scope, trigger, and effect without executable code:

```json
{
  "id": "bridge-ambush-rule",
  "name": "Bridge Ambush Rule",
  "source_page": 9,
  "description": "Reviewed local rule summary.",
  "scope": "location",
  "trigger": "When the party crosses the bridge.",
  "effect": "Use the reviewed procedure or branch choices.",
  "review_status": "needs_pdf_check"
}
```

Tables should keep reviewed rows in `rows`:

```json
{
  "id": "hidden-door-table",
  "title": "Hidden Door Table",
  "source_page": 12,
  "dice": "d6",
  "rows": [
    { "result": "1-2", "outcome": "No hidden door found." }
  ],
  "review_status": "needs_pdf_check"
}
```

Procedures are declarative app instructions only. They may use allowlisted operations such as `roll_table`, `spawn_foes`, `test_save`, `grant_gold`, `grant_item`, `set_tracker`, `advance_tracker`, `branch_if`, `transition_to_node`, `complete_objective`, `pin_location`, and `show_choice`. Do not add script code.

Trackers are counters for local adventure state, for example doom, light, alarm, corruption, or elapsed turns. Keep the purpose in notes or app notes on the locations that use the tracker.

## Candidate Lists From PDFs

The PDF Import Review Workspace can extract candidate records from the source PDF text. These are shown in clickable lists:

- Locations
- Tables
- Foes
- Items
- Classes
- States
- Rules
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
  "role": "room",
  "node_id": "room-1",
  "x": 42.5,
  "y": 63,
  "shape": "point",
  "notes": "Numbered room marker on the level 1 map."
}
```

`node_id` should match a reviewed node id, then later a playable room id.

Use `role` to mark what the pin means during review:

- `location` or `room` for ordinary keyed areas
- `entrance` for the dungeon entrance or adventure start marker
- `exit` for an exit back to camp, settlement, or another map
- `stairs` for a level change or vertical route
- `secret` for hidden doors, secret rooms, or concealed routes
- `objective` for a keyed goal, boss, rescue, relic, or other focal site
- `camp`, `settlement`, or `other` when the map includes overland or non-dungeon sites

Pin roles are metadata until the reviewed location graph uses them. Do not infer playable exits from a marker unless the PDF text and reviewed node branches agree.

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
