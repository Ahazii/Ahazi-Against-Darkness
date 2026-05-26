# Rule Coverage

Status labels:

- `missing` - not implemented
- `starter` - implemented approximately for engine scaffolding
- `validated` - checked against the owned rulebook and covered by tests

| Area | Status | Notes |
| --- | --- | --- |
| Character classes | validated | All 20 EE classes (p.24–69): Life offset, starting wealth dice, starting gear audited vs PDF; creation rolls gold and class rations. Combat modifiers in tests. |
| Character pool | starter | Create/list/heal/delete; roster transfer; weapon defaults; equipment shop. |
| Party creation | starter | Exactly four heroes; marching order; heal/edit/delete. |
| Inventory | starter | Carry limits in-dungeon (starting class gear exempt; extra gear encumbers); default weapons; combat swap; home shop; blade poison; roster sync on in-dungeon transfer. |
| Gold and XP | starter | Four XP systems; Final Boss check; XP rolls after fights; Old School/Slower tallies persist on clean exit. |
| Level-up | starter | EE p.117–118 + FD tier dice: Life formula, class benefits, spell slots, spell picker; L5+ **Level up vs expert skill** fork; tier training gates L10/L15/L20. |
| Expert skills | validated | Abyss catalog in `expert_skills.json`; eligibility, learning, roster persist; home tables (mechanic + status columns) + party sheet UI; **all catalog combat/exploration/between-adventure effects wired** (Whirlwind, Shield Bash, Combat Acrobatics, Acute Hearing, Super Logic, crafting skills, etc.). |
| Spells | starter | Basic wizard/cleric; druid and illusionist tables; Escape; MR on casters; cleric healing prayer d6+L; door magic in exploration; once per adventure per known spell. |
| Scrolls | starter | `scrolls_table`; burn to cast; wizard copy unknown spell to spellbook; barbarian cannot use scrolls. |
| Charged magic items | starter | Wand of Sleep / Fireball Staff (and `Staff of …` patterns); `use_magic_item` from party sheet; 1 charge per cast; no memorized slot; barbarian cannot use. |
| Saves | starter | Trap/poison saves with class modifiers; door attempts apply encumbrance; locked doors require Rogue or Warrior/Barbarian. |
| Random map generation | starter | d66 placement, truncation, reciprocal exits, walkable masks; optional 20×28 paper bounds. |
| Exact map element table | starter | 42 rows in `tiles.json`; editor validation workflow. |
| Door table | validated | 2d6 Expanded Edition p.109; entry inheritance; Open Door flow; sealed/illusion/lever/iron exploration magic. |
| Special events | starter | Ghost, trap, healer (once per adventure reroll), alchemist, Lady in White, wandering subtable; caverns/fungal environment tables. |
| Search table | validated | d6 p.107; corridor −1; search choice UI. |
| Wandering monsters | validated | Search, alarm, backtrack, special-event subtable. |
| Traps | validated | d6 p.164; environment variants p.165–166; marching-order targets; Resolve Trap action. |
| Treasure | validated | d6 p.157; environment magic/special items p.159–161; magic weapons roll d6 type (p.163), +1 Attack when wielded, class/magic restrictions, fixed resale. |
| Hidden treasure | validated | Formula and complications p.108. |
| Combat modifiers | starter | Blade poison, poison foes, two-step MR (connect + penetrate tiers), mirror-image absorption, subdual, bribes, missiles, weapon-type modifiers; troll regeneration (Fireball suppresses regen; acid/lightning/oil not yet), held/fog/specter combat effects. |
| Combat core | starter | p.91-97 attack/defense/morale/flee; p.146 round-0 initiative (surprise, attack-immediately, reactions-first); post-ranged unarmed (−2) / foe draw weapon; major-foe L drop; corridor rules; combat panel (hero rows, round plan, withdraw picker). |
| Reactions and morale | starter | Per-foe bestiary tables + bribes; p.146 attack-immediately vs Check Reactions (mutually exclusive); category fallback. |
| Fleeing | validated | Flee, withdraw, wandering pursuit. |
| Quests | starter | Quest Table, progress, Epic Rewards; bring-alive via subdual; bring-head requires lethal boss kill. |
| Potions | starter | Potion of Healing once per hero; alchemist purchase; home shop buy/sell. |
| Equipment shop | starter | `equipment_shop.json` + home UI; p.16 buy / p.19 sell; class restrictions. |
| Death and recovery | starter | Fallen on tiles; carry body (p.44 rearguard, auto-hit); deliver at entrance; 1000gp resurrection; body theft on retreat. |
| Rest | validated | Once/adventure (p.114): cleared room + cleared adjacent tiles, nail doors (Bag of nails, 4gp), per-PC 1 Life or spent ability recovery, 1-in-6 wanderers (nailed = party first). Halfling Nourishing Meal when resting. |
| Class abilities (Tier 1) | starter | Barbarian rage (3d6 best, double damage), halfling Luck (flee/reroll attack), swashbuckler Panache (+1 attack/defense), paladin prayer heal/reroll save; rest recovery for spent rage/luck/prayer. |
| Rules reference | validated | Searchable rulebook sections (116 entries): EE + Abyss topics with `implementation_status` badges; skill/spell catalogs and wiring live in Rules tables only. |
| Session rewards | starter | Clean exit persists party state via `roster_sync`; UI reloads roster; camp/retreat does not persist. |
| Rule table display | validated | Home lists all `dungeon_tables.json` keys + merged equipment/expert/tier tables + monster bestiary + monster reactions + map elements (`tiles.json`); test guards sync. |
| Expert spells | partial | L5+ fork adds spells to repertoire; six Abyss expert spells listed but cast effects not wired in combat/exploration. |
| Character positioning | starter | Marching order for traps and corridor combat. |
| Split party | missing | EE p.105: detached PCs roll 1-in-6 wanderers when main party does; p.79–80 stealth/scout can isolate a hero one turn from backup; Fiendish Foes p.180 simultaneous fights when Major + Minions share a tile. Single session tile / one party group only today. |
| Imported adventures | missing | PDFs listed; manifests required. |
| Authored map rendering | missing | Waiting on manifest schema. |
| Environment variants | starter | Secret passage → caverns/fungal grottoes; table routing; paper 20×28 mode; home lists seven environment tables. |

## Validation references

- Source PDF: `Rules/Four_Against_Darkness_Expanded_Edition.pdf`
- Automated checks: `tests/test_rulebook_validation.py`, `tests/test_combat.py`,
  `tests/test_combat_modifiers.py`, `tests/test_reactions.py`, `tests/test_class_profiles_audit.py`, `tests/test_weapons.py`,
  `tests/test_magic_weapons.py`, `tests/test_spells.py`, `tests/test_spells_extended.py`, `tests/test_spell_expended.py`,
  `tests/test_inventory_transfer.py`, `tests/test_carry_limits.py`,
  `tests/test_equipment.py`, `tests/test_session_persist.py`,
  `tests/test_equipment_shop.py`, `tests/test_exploration.py`, `tests/test_economy.py`, `tests/test_level_up.py`,
  `tests/test_door_sync.py`,   `tests/test_initiative.py`, `tests/test_rest.py`, `tests/test_class_abilities.py`, `tests/test_rulebook_reference.py`, `tests/test_bandage.py`, `tests/test_tier1_combat.py`,
  `tests/test_class_combat.py`, `tests/test_death_recovery.py`, `tests/test_doors.py`, `tests/test_tier3_map.py`,
  `tests/test_tier_dice.py`, `tests/test_tier_training.py`, `tests/test_expert_skills.py`, `tests/test_expert_skill_effects.py`
- Last validation pass: 2026-05-19 (class profiles Life/wealth/gear vs EE p.24–69; combat panel UI; rules reference sync)

## Next depth (planned)

1. ~~Class profile data audit (`classes.json` vs rulebook starting gear/Life).~~ Done 2026-05-19.
2. ~~Expert skill catalog, L5+ fork, tier training, and core effect wiring.~~ Done 2026-05-19.
3. ~~Remaining expert skill / expert spell effects (crafting, Whirlwind, Shield Bash, etc.).~~ Done 2026-05-19.
4. Expert spell cast effects; troll regen acid/lightning/oil sources; combat round log summary; multi-target spell UI.
5. Named save labels for Saved Games.
