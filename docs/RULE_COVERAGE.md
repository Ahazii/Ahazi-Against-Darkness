# Rule Coverage

Status labels:

- `missing` - not implemented
- `starter` - implemented approximately for engine scaffolding
- `validated` - checked against the owned rulebook and covered by tests

| Area | Status | Notes |
| --- | --- | --- |
| Character classes | starter | Data exists, needs rulebook validation. |
| Character pool | starter | Create/list/detail/delete works. Full character editing and retirement missing. |
| Party creation | starter | Exactly four distinct characters required. Party detail/edit/delete works. |
| Inventory | starter | Stored as text items, no item rules yet. |
| Gold and XP | starter | Stored, not fully awarded or spent. |
| Level-up | missing | Needs campaign rules. |
| Spells | starter | Stored as names only. Effects missing. |
| Saves | starter | Bonus stored, full save flow missing. |
| Random map generation | starter | Uses start rolls `01-06`, generated rolls `11-66`, rotates placed elements, aligns exact grid-square edge exits, carries walkable/half-square metadata into sessions, and exposes one button per available exit. |
| Exact map element table | starter | `tiles.json` has 42 rows and editable type, calibration, exits, footprints, walkable masks, and half-square shapes, but most are placeholders needing validation. |
| Door table | starter | Door result logged, not fully enforced. |
| Room content table | starter | Approximate 2d6 flow. |
| Search table | starter | Approximate search results. |
| Wandering monsters | starter | Search can spawn them. |
| Traps | missing | Objects exist, resolution missing. |
| Treasure | missing | Objects exist, loot table missing. |
| Combat | starter | Basic attack/defense loop only. |
| Reactions and morale | missing | Not implemented. |
| Fleeing | missing | Not implemented. |
| Death and recovery | starter | Characters can fall in session. Permanent effects missing. |
| Session rewards | starter | Current character state writes back when leaving through a dungeon exit; XP/loot award rules are incomplete. |
| Imported adventures | missing | PDFs discovered, manifests required. |
| Authored map rendering | missing | Waiting on adventure manifest schema. |
