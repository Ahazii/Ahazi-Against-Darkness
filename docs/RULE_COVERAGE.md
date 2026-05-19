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
| Inventory | starter | Stored as text items; armor/shield strings affect defense. Claim Treasure adds loot. No carry limits yet. |
| Gold and XP | starter | Gold awarded via Claim Treasure; XP not yet awarded from encounters. |
| Level-up | missing | Needs campaign rules. |
| Spells | starter | Stored as names only. Effects missing. |
| Saves | starter | Bonus stored; trap/door save flows partially implemented. |
| Random map generation | starter | Uses start rolls `01-06`, generated rolls `11-66`, rotates placed elements, aligns exact grid-square edge exits, reserves unconnected exit approaches, carries walkable/cell-shape metadata into sessions, logically truncates elements that would overlap explored space or unresolved exits, and exposes one button per available exit. |
| Exact map element table | starter | `tiles.json` has 42 rows and editable metadata; user-validated for current play. |
| Door table | validated | 2d6 table matches Expanded Edition p.109; iron/lever/sealed/illusion edge cases partially enforced. |
| Room content table | validated | 2d6 dungeon table matches p.152 with corridor/room splits; Special Events/Features subtables still stubbed. |
| Search table | validated | d6 table matches p.107 including corridor -1; search 5-6 choice defaults to hidden treasure until UI supports all four options. |
| Wandering monsters | starter | Search and hidden-treasure alarm spawn them; full Wandering Monsters d6 subtable not wired. |
| Traps | validated | Dungeon Traps d6 table matches p.164 with marching-order targets and save/defense types; rogue pre-disarm on room traps only partially wired. |
| Treasure | validated | Dungeon Treasure d6 table matches p.157; Magic Treasure subtable logged only. |
| Hidden treasure | validated | `(2d6+HCL) x (2d6+HCL)` and complication table match p.108; secret door/passage search options not implemented. |
| Combat | starter | Core exploding-d6 attack/defense, armor, minor multi-kill, and morale match p.91-97; reactions, initiative, corridor assignment, and weapon modifiers missing. |
| Reactions and morale | starter | Minor-foe morale check implemented. Full reaction tables missing. |
| Fleeing | missing | Not implemented. |
| Death and recovery | starter | Fallen heroes tracked on tiles; survivor healing on dungeon exit. Body carrying and resurrection missing. |
| Session rewards | starter | Character state writes back on dungeon exit. Gold/items from Claim Treasure persist; XP rules incomplete. |
| Rule table display | validated | Home screen and engine share validated `dungeon_tables.json` via `DungeonTableRoller`. |
| Character positioning | starter | Marching order set and used for traps; corridor combat rules not enforced. |
| Imported adventures | missing | PDFs discovered, manifests required. |
| Authored map rendering | missing | Waiting on adventure manifest schema. |

## Validation references

- Source PDF: `Rules/Four_Against_Darkness_Expanded_Edition.pdf`
- Automated table checks: `tests/test_rulebook_validation.py`
- Last validation pass: 2026-05-19 (dungeon environment)
