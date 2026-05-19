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
| Inventory | starter | Stored as text items; armor strings affect defense. Claim Treasure adds loot. No equip slots or carry limits yet. |
| Gold and XP | starter | Gold awarded via Claim Treasure; XP not yet awarded from encounters. |
| Level-up | missing | Needs campaign rules. |
| Spells | starter | Stored as names only. Effects missing. |
| Saves | starter | Bonus stored, full save flow missing. |
| Random map generation | starter | Uses start rolls `01-06`, generated rolls `11-66`, rotates placed elements, aligns exact grid-square edge exits, reserves unconnected exit approaches, carries walkable/cell-shape metadata into sessions, logically truncates elements that would overlap explored space or unresolved exits, and exposes one button per available exit. |
| Exact map element table | starter | `tiles.json` has 42 rows and editable type, image calibration, direction-derived exits, multi-square exit spans, footprints, walkable masks, and half-square/shallow-slope/curved-corner shapes, but most are placeholders needing validation. Rotation preview rotates masks and image offsets for validation. |
| Door table | starter | 2d6 door types with open rolls; shown on home screen and used by exploration engine. |
| Room content table | starter | Approximate 2d6 flow with optional roll/math detail. |
| Search table | starter | Approximate search results with optional roll/math detail. |
| Wandering monsters | starter | Search can spawn them. |
| Traps | starter | d6 dungeon trap table, marching-order targets, rogue disarm attempt, Resolve Trap action. Hidden-treasure complications logged only. |
| Treasure | starter | d6 treasure table after combat/treasure tiles; hidden treasure on search 6; Claim Treasure splits gold/items to party sheets. Magic treasure not resolved. |
| Combat | starter | 4AD exploding-d6 attack/defense, class modifiers, armor from inventory strings, minor multi-kill, morale at half strength. Class abilities, spells, reactions, and fleeing still missing. Defeated enemies are remembered on the room for map markers. |
| Reactions and morale | starter | Minor-foe morale check implemented. Full reaction rules missing. |
| Fleeing | missing | Not implemented. |
| Death and recovery | starter | Characters can fall in session and the current tile records fallen character ids for map markers. Surviving heroes heal when leaving the dungeon, and manual heal controls exist for upkeep. Body carrying, resurrection, theft, and permanent effects missing. |
| Session rewards | starter | Current character state writes back when leaving the dungeon exit. Gold/items from Claim Treasure persist; XP award rules incomplete. |
| Rule table display | starter | Home screen and engine share `dungeon_tables.json` via `DungeonTableRoller`. PDF scan snippets need table page/coordinate metadata. |
| Character positioning | missing | Core rules checked so far use Marching Order and tile type rather than exact square occupancy. Per-square positions remain a future tactical/map feature. |
| Imported adventures | missing | PDFs discovered, manifests required. |
| Authored map rendering | missing | Waiting on adventure manifest schema. |
