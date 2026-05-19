# Rule Coverage

Status labels:

- `missing` - not implemented
- `starter` - implemented approximately for engine scaffolding
- `validated` - checked against the owned rulebook and covered by tests

| Area | Status | Notes |
| --- | --- | --- |
| Character classes | starter | Data exists; needs full rulebook validation. |
| Character pool | starter | Create/list/detail/heal/delete. Full editing/retirement missing. |
| Party creation | starter | Exactly four heroes; marching order; heal/edit/delete. |
| Inventory | starter | Text items; armor/shield defense; blade poison consumed on hit. No carry limits. |
| Gold and XP | starter | Four XP systems; Final Boss check; XP rolls after fights. |
| Level-up | starter | Classical and alternate XP wired; Slower Advancement training costs partial. |
| Spells | starter | Basic wizard/cleric spells in combat; once per adventure per known spell; MR on casters. |
| Saves | starter | Trap/poison saves with class modifiers; door saves partial. |
| Random map generation | starter | d66 placement, truncation, reciprocal exits, walkable masks. |
| Exact map element table | starter | 42 rows in `tiles.json`; editor validation workflow. |
| Door table | validated | 2d6 Expanded Edition p.109; entry inheritance; Open Door flow. |
| Special events | starter | Ghost, trap, healer, alchemist, Lady in White, wandering subtable. |
| Search table | validated | d6 p.107; corridor −1; search choice UI. |
| Wandering monsters | validated | Search, alarm, backtrack, special-event subtable. |
| Traps | validated | d6 p.164; marching-order targets; Resolve Trap action. |
| Treasure | validated | d6 p.157; magic subtable; entry logging; empty-roll UX. |
| Hidden treasure | validated | Formula and complications p.108. |
| Combat modifiers | starter | Blade poison, poison foes, magic resistance (`combat_modifiers_table`). |
| Combat core | starter | p.91-97 attack/defense/morale/flee; major-foe L drop; corridor rules. |
| Reactions and morale | starter | Generic vermin/minion/major tables + bribe UI. |
| Fleeing | validated | Flee, withdraw, wandering pursuit. |
| Quests | starter | Quest Table, progress, Epic Rewards; bring-alive partial. |
| Potions | starter | Potion of Healing once per hero; alchemist purchase. |
| Death and recovery | starter | Fallen on tiles; camp/retreat; survivor heal on clean exit. |
| Session rewards | starter | Claim Treasure; character pool heal; full persistence partial. |
| Rule table display | validated | Home lists all `dungeon_tables.json` keys + monster bestiary. |
| Character positioning | starter | Marching order for traps and corridor combat. |
| Imported adventures | missing | PDFs listed; manifests required. |
| Authored map rendering | missing | Waiting on manifest schema. |

## Validation references

- Source PDF: `Rules/Four_Against_Darkness_Expanded_Edition.pdf`
- Automated checks: `tests/test_rulebook_validation.py`, `tests/test_combat.py`,
  `tests/test_combat_modifiers.py`, `tests/test_reactions.py`, `tests/test_spells.py`,
  `tests/test_exploration.py`, `tests/test_economy.py`
- Last validation pass: 2026-05-19 (dungeon environment)

## Next combat depth (planned)

1. Per-foe reaction rows from `monsters.json` bestiary metadata.
2. Scroll burning and magic-item spell sources separate from memorized spells.
3. Inventory weapon modifiers (two-handed, missile, silver) from equipment strings.
4. Poison status persistence across rounds (currently immediate extra damage).
