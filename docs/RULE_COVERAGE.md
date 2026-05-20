# Rule Coverage

Status labels:

- `missing` - not implemented
- `starter` - implemented approximately for engine scaffolding
- `validated` - checked against the owned rulebook and covered by tests

| Area | Status | Notes |
| --- | --- | --- |
| Character classes | starter | Warrior, cleric, wizard, elf, druid, illusionist in data; needs full rulebook validation. |
| Character pool | starter | Create/list/detail/heal/delete; roster item and gold transfer. Full editing/retirement missing. |
| Party creation | starter | Exactly four heroes; marching order; heal/edit/delete. |
| Inventory | starter | Carry limits, default weapons, combat swap, transfer; armor/shield defense; blade poison. |
| Gold and XP | starter | Four XP systems; Final Boss check; XP rolls after fights; Old School/Slower tallies persist on clean exit. |
| Level-up | starter | Expanded Edition p.117–118: Life formula, class benefits, spell slots (wizard L+2, elf L, druid 2+L, illusionist L+3), spell picker UI, cleric d6+L healing. |
| Spells | starter | Basic wizard/cleric; druid and illusionist tables; Escape; MR on casters; cleric healing prayer d6+L; door magic in exploration; once per adventure per known spell. |
| Scrolls | starter | `scrolls_table`; burn to cast; wizard copy unknown spell to spellbook; barbarian cannot use scrolls. |
| Saves | starter | Trap/poison saves with class modifiers; door saves partial. |
| Random map generation | starter | d66 placement, truncation, reciprocal exits, walkable masks. |
| Exact map element table | starter | 42 rows in `tiles.json`; editor validation workflow. |
| Door table | validated | 2d6 Expanded Edition p.109; entry inheritance; Open Door flow; sealed/illusion/lever/iron exploration magic. |
| Special events | starter | Ghost, trap, healer, alchemist, Lady in White, wandering subtable. |
| Search table | validated | d6 p.107; corridor −1; search choice UI. |
| Wandering monsters | validated | Search, alarm, backtrack, special-event subtable. |
| Traps | validated | d6 p.164; marching-order targets; Resolve Trap action. |
| Treasure | validated | d6 p.157; magic subtable; entry logging; empty-roll UX. |
| Hidden treasure | validated | Formula and complications p.108. |
| Combat modifiers | starter | Blade poison, poison foes, magic resistance, subdual damage, weapon bribes, missile combat, weapon-type modifiers. |
| Combat core | starter | p.91-97 attack/defense/morale/flee; major-foe L drop; corridor rules. |
| Reactions and morale | starter | Per-foe bestiary reaction tables + weapon bribes; generic category fallback. |
| Fleeing | validated | Flee, withdraw, wandering pursuit. |
| Quests | starter | Quest Table, progress, Epic Rewards; bring-alive via subdual; bring-head requires lethal boss kill. |
| Potions | starter | Potion of Healing once per hero; alchemist purchase. |
| Death and recovery | starter | Fallen on tiles; camp/retreat; survivor heal on clean exit. |
| Session rewards | starter | Clean exit persists party state via `roster_sync`; UI reloads roster; camp/retreat does not persist. |
| Rule table display | validated | Home lists all `dungeon_tables.json` keys + monster bestiary + monster reactions; test guards sync. |
| Character positioning | starter | Marching order for traps and corridor combat. |
| Imported adventures | missing | PDFs listed; manifests required. |
| Authored map rendering | missing | Waiting on manifest schema. |

## Validation references

- Source PDF: `Rules/Four_Against_Darkness_Expanded_Edition.pdf`
- Automated checks: `tests/test_rulebook_validation.py`, `tests/test_combat.py`,
  `tests/test_combat_modifiers.py`, `tests/test_reactions.py`, `tests/test_weapons.py`,
  `tests/test_spells.py`, `tests/test_spells_extended.py`, `tests/test_spell_expended.py`,
  `tests/test_inventory_transfer.py`, `tests/test_carry_limits.py`,
  `tests/test_equipment.py`, `tests/test_session_persist.py`,
  `tests/test_exploration.py`, `tests/test_economy.py`, `tests/test_level_up.py`,
  `tests/test_door_sync.py`
- Last validation pass: 2026-05-19 (inventory, roster sync, equipment, entrance doors)

## Next combat depth (planned)

1. Dedicated combat panel with per-hero targeting (weapon defaults and swap are implemented on party sheets).
2. Full rulebook fidelity for partial spells (outdoor-only, MR two-step, mirror images).
3. Poison status persistence across rounds (optional refinement).
