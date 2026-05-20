# Rule Coverage

Status labels:

- `missing` - not implemented
- `starter` - implemented approximately for engine scaffolding
- `validated` - checked against the owned rulebook and covered by tests

| Area | Status | Notes |
| --- | --- | --- |
| Character classes | starter | Warrior, cleric, wizard, elf, druid, illusionist in data; needs full rulebook validation. |
| Character pool | starter | Create/list/heal/delete; roster transfer; weapon defaults; equipment shop. |
| Party creation | starter | Exactly four heroes; marching order; heal/edit/delete. |
| Inventory | starter | Carry limits in-dungeon; default weapons; combat swap; home shop; blade poison. |
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
| Combat modifiers | starter | Blade poison, poison foes (lingering Poisoned status), magic resistance, mirror-image hit absorption, subdual, bribes, missiles, weapon-type modifiers. |
| Combat core | starter | p.91-97 attack/defense/morale/flee; p.146 round-0 initiative (surprise, attack-immediately, reactions-first); post-ranged unarmed (−2) / foe draw weapon; major-foe L drop; corridor rules; combat sidebar. |
| Reactions and morale | starter | Per-foe bestiary tables + bribes; p.146 attack-immediately vs Check Reactions (mutually exclusive); category fallback. |
| Fleeing | validated | Flee, withdraw, wandering pursuit. |
| Quests | starter | Quest Table, progress, Epic Rewards; bring-alive via subdual; bring-head requires lethal boss kill. |
| Potions | starter | Potion of Healing once per hero; alchemist purchase; home shop buy/sell. |
| Equipment shop | starter | `equipment_shop.json` + home UI; p.16 buy / p.19 sell; class restrictions. |
| Death and recovery | starter | Fallen on tiles; camp/retreat; survivor heal on clean exit. |
| Session rewards | starter | Clean exit persists party state via `roster_sync`; UI reloads roster; camp/retreat does not persist. |
| Rule table display | validated | Home lists all `dungeon_tables.json` keys + monster bestiary + monster reactions (collapsed by default); test guards sync. |
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
  `tests/test_equipment_shop.py`, `tests/test_exploration.py`, `tests/test_economy.py`, `tests/test_level_up.py`,
  `tests/test_door_sync.py`, `tests/test_initiative.py`, `tests/test_bandage.py`
- Last validation pass: 2026-05-19 (p.146 initiative phases, bandages, gold split on claim)

## Next combat depth (planned)

1. Combat panel polish: round log summary, spell targets on multi-foe spells.
2. Combat rule gaps: full MR two-step, partial outdoor/illusionary servant spells.
3. Full rulebook fidelity for remaining stub spells.
