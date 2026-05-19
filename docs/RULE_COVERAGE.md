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
| Spells | starter | Basic wizard/cleric prayers (Blessing, Escape, Lightning, Fireball, Protection, Sleep, Healing prayer) resolve in combat via Cast Spell; spell slots and MR not modeled yet. |
| Saves | starter | Bonus stored; trap/door save flows partially implemented. |
| Random map generation | starter | Uses start rolls `01-06`, generated rolls `11-66`, rotates placed elements, aligns exact grid-square edge exits, reserves unconnected exit approaches, carries walkable/cell-shape metadata into sessions, logically truncates elements that would overlap explored space or unresolved exits, and exposes one button per available exit. |
| Exact map element table | starter | `tiles.json` has 42 rows and editable metadata; user-validated for current play. |
| Door table | validated | 2d6 table matches Expanded Edition p.109; entry connections inherit passage/open-door state; other doors stay closed until Open Door succeeds. |
| Room content table | validated | 2d6 dungeon table matches p.152 with corridor/room splits; `enemy_tags` filter spawned foes (dragon's lair -> Dragon). Special Events/Features wired on room enter. |
| Search table | validated | d6 table matches p.107 including corridor -1; search 5-6 choice supports hidden treasure, secret door/passage, and clue. |
| Wandering monsters | validated | Search, hidden-treasure alarm, backtrack d6=1, and special-event subtable use the Wandering Monsters d6 categories. |
| Traps | validated | Dungeon Traps d6 table matches p.164 with marching-order targets and save/defense types; rogue pre-disarm on room traps only partially wired. |
| Treasure | validated | Dungeon Treasure d6 table matches p.157; empty rolls do not enable Claim Treasure; Magic Treasure subtable resolves items. |
| Hidden treasure | validated | `(2d6+HCL) x (2d6+HCL)` and complication table match p.108; secret door/passage search options implemented. |
| Combat | starter | Exploding-d6 attack/defense, armor, corridor front rank, wandering rear ambush, class modifiers, flee/withdraw, and minor morale match p.91-97; weapon modifiers and per-foe bestiary rules remain starter-only. |
| Reactions and morale | starter | Generic vermin/minion/major reaction tables plus Check Reactions / Pay Bribe UI; per-foe bestiary reaction rows not yet wired. |
| Fleeing | validated | Flee and withdraw actions implemented with defense modifiers and wandering check. |
| Death and recovery | starter | Fallen heroes tracked on tiles; survivor healing on dungeon exit. Body carrying and resurrection missing. |
| Session rewards | starter | Character state writes back on dungeon exit. Claim Treasure logs hoard summary, per-hero gold split, and items awarded. |
| Rule table display | validated | Home screen lists all packaged dungeon tables in order, including reactions, spells, wandering monsters, and special-event subtables. |
| Character positioning | starter | Marching order set and used for traps and corridor combat rear/front assignment. |
| Imported adventures | missing | PDFs discovered, manifests required. |
| Authored map rendering | missing | Waiting on adventure manifest schema. |

## Validation references

- Source PDF: `Rules/Four_Against_Darkness_Expanded_Edition.pdf`
- Automated table checks: `tests/test_rulebook_validation.py`, `tests/test_door_sync.py`, `tests/test_combat.py`, `tests/test_reactions.py`, `tests/test_spells.py`
- Last validation pass: 2026-05-19 (dungeon environment)
