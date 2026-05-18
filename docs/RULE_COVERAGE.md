# Rule Coverage

Status labels:

- `missing` - not implemented
- `starter` - implemented approximately for engine scaffolding
- `validated` - checked against the owned rulebook and covered by tests

| Area | Status | Notes |
| --- | --- | --- |
| Character classes | starter | Data exists, needs rulebook validation. |
| Character pool | starter | Create/list/detail/heal/delete works. Full character editing and retirement missing. |
| Party creation | starter | Exactly four distinct characters required. Party detail/heal/edit/delete works. |
| Inventory | starter | Stored as text items, no item rules yet. |
| Gold and XP | starter | Stored, not fully awarded or spent. |
| Level-up | missing | Needs campaign rules. |
| Spells | starter | Stored as names only. Effects missing. |
| Saves | starter | Bonus stored, full save flow missing. |
| Random map generation | starter | Uses start rolls `01-06`, generated rolls `11-66`, rotates placed elements, aligns exact grid-square edge exits, reserves unconnected exit approaches, carries walkable/cell-shape metadata into sessions, logically truncates elements that would overlap explored space or unresolved exits, and exposes one button per available exit. |
| Exact map element table | starter | `tiles.json` has 42 rows and editable type, image calibration, direction-derived exits, multi-square exit spans, footprints, walkable masks, and half-square/shallow-slope/curved-corner shapes, but most are placeholders needing validation. Rotation preview rotates masks and image offsets for validation. |
| Door table | starter | Door result and optional roll/math detail logged, not fully enforced. |
| Room content table | starter | Approximate 2d6 flow with optional roll/math detail. |
| Search table | starter | Approximate search results with optional roll/math detail. |
| Wandering monsters | starter | Search can spawn them. |
| Traps | missing | Objects exist, resolution missing. |
| Treasure | missing | Objects exist, loot table missing. |
| Combat | starter | Basic attack/defense loop only. |
| Reactions and morale | missing | Not implemented. |
| Fleeing | missing | Not implemented. |
| Death and recovery | starter | Characters can fall in session and the current tile records fallen character ids for map markers. Surviving heroes heal when leaving the dungeon, and manual heal controls exist for upkeep. Body carrying, resurrection, theft, and permanent effects missing. |
| Session rewards | starter | Current character state writes back when leaving through a dungeon exit; XP/loot award rules are incomplete. |
| Rule table display | starter | Home screen shows structured starter tables. PDF scan snippets need table page/coordinate metadata. |
| Character positioning | missing | Core rules checked so far use Marching Order and tile type rather than exact square occupancy. Per-square positions remain a future tactical/map feature. |
| Imported adventures | missing | PDFs discovered, manifests required. |
| Authored map rendering | missing | Waiting on adventure manifest schema. |
