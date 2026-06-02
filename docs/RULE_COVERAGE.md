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
| Spells | starter | Basic wizard/cleric; druid and illusionist tables; Escape; MR on casters; cleric healing prayer d6+L; door magic in exploration; once per adventure per known spell; home **basic_spells_table** documents connect + damage; Fireball mummy +2 wired. |
| Scrolls | starter | `scrolls_table`; burn to cast; wizard copy unknown spell to spellbook; barbarian cannot use scrolls. |
| Charged magic items | starter | Wand of Sleep / Fireball Staff (and `Staff of …` patterns); `use_magic_item` from party sheet; 1 charge per cast; no memorized slot; barbarian cannot use. |
| Saves | starter | Trap/poison saves with class modifiers; door attempts apply encumbrance; locked doors require Rogue or Warrior/Barbarian. |
| Random map generation | starter | d66 placement, truncation, reciprocal exits, walkable masks; optional 20×28 paper bounds. |
| Exact map element table | starter | 42 rows in `tiles.json`; structural validation passes for all keys (`map_elements_validation_table`, `tools/validate_tiles.py`); gif/rulebook layout audit ongoing. |
| Door table | validated | 2d6 Expanded Edition p.109; entry inheritance; Open Door flow; sealed/illusion/lever/iron exploration magic. |
| Special events | starter | Ghost, trap, healer (once per adventure reroll), alchemist, Lady in White, wandering subtable; caverns/fungal environment tables. |
| Search table | validated | d6 p.107; corridor −1; search choice UI. |
| Wandering monsters | validated | Search, alarm, backtrack, special-event subtable. |
| Traps | validated | d6 p.164; environment variants p.165–166; marching-order targets; Resolve Trap action. |
| Treasure | validated | d6 p.157; environment magic/special items p.159–161; magic weapons roll d6 type (p.163), +1 Attack when wielded, class/magic restrictions, fixed resale. |
| Hidden treasure | validated | Formula and complications p.108. |
| Combat modifiers | starter | Blade poison, poison foes, two-step MR (connect + penetrate tiers), mirror-image absorption, subdual, bribes, missiles, weapon-type modifiers; troll regeneration (fire, acid vials, lightning, lantern oil suppress regen), held/fog/specter combat effects; post-round log summary; multi-target spell/ability UI (Double Attack, Double Kick, Protective Incense, Infallible L8+). |
| Combat core | starter | p.91-97 attack/defense/morale/flee; p.146 round-0 initiative (surprise, attack-immediately, reactions-first); pre-combat encounter hint (Exits vs Start Combat); post-ranged unarmed (−2) / foe draw weapon; major-foe L drop; corridor rules; Combat Focus layout + legacy combat panel. |
| Reactions and morale | starter | Per-foe bestiary tables + bribes; p.146 attack-immediately vs Check Reactions (mutually exclusive); category fallback. |
| Fleeing | validated | Flee, withdraw, wandering pursuit. |
| Quests | starter | Quest Table, progress, Epic Rewards; bring-alive via subdual; bring-head requires lethal boss kill. |
| Potions | starter | Potion of Healing once per hero; alchemist purchase; home shop buy/sell. |
| Equipment shop | starter | `equipment_shop.json` + home UI; p.16 buy / p.19 sell; class restrictions; lantern oil and acid vials. |
| Consumables | starter | Mushrooms (fungal grottoes p.159), lantern oil splash, acid vial throw; shop + party-sheet actions. |
| Death and recovery | starter | Fallen on tiles; carry body (p.44 rearguard, auto-hit); deliver at entrance; 1000gp resurrection; body theft on retreat. |
| Rest | validated | Once/adventure (p.114): cleared room + cleared adjacent tiles, nail doors (Bag of nails, 4gp), per-PC 1 Life or spent ability recovery, 1-in-6 wanderers (nailed = party first). Halfling Nourishing Meal when resting. |
| Class abilities (Tier 1) | starter | Barbarian rage (3d6 best, double damage), halfling Luck (flee, attack/defense/save/search/treasure reroll), swashbuckler Panache (+1 attack/defense), paladin prayer heal/reroll save; rest recovery for spent rage/luck/prayer. |
| Class tricks (Tiers 2–4) | partial | Tier 2–4 tricks wired per `class_tricks_implementation_table`. Heroic/legendary learning + wired combat/rest subset (Battle/Ballistic Training, Dodge, Master Strike, Courage, Hero's Rest). Remaining heroic/legendary skills catalog-only. |
| Combat Focus | starter | Tactical map, command rail (Exits/Encounter/Log), hero drawer, slim deck, cinema view; one-viewport layout. |
| Druid companion | starter | Wilderness auto-summon (Food ration); wolf/bear/panther; 1 attack/round; foe retaliation; Madness on death. |
| Rules reference | validated | Searchable rulebook sections (122 entries): EE + Abyss topics with `implementation_status` badges; skill/spell/trick catalogs and wiring live in Rules tables. |
| Session rewards | starter | Clean exit persists party state via `roster_sync`; UI reloads roster; camp/retreat does not persist. |
| Rule table display | validated | Home lists all `dungeon_tables.json` keys + merged equipment/expert/tier/heroic/legendary tables + class-trick and map-element validation tables + monster bestiary + reactions + map elements + icon registry; test guards sync. |
| Expert spells | validated | L5+ fork adds spells to repertoire; all six Abyss cast effects wired; Mass Teleport / Lifeforce UI in combat; home **expert_spells_table** documents mechanics. |
| Character positioning | starter | Marching order for traps and corridor combat. |
| Split party | starter | EE p.105: detach/reattach heroes on a tile, scout-ahead lag, detached 1-in-6 wandering rolls, simultaneous front/rear vs major/minion fights when mixed encounters occur. Remote detached combat UI and full combat-path split coverage still partial. |
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
  `tests/test_tier_dice.py`, `tests/test_tier_training.py`, `tests/test_expert_skills.py`, `tests/test_expert_skill_effects.py`,   `tests/test_expert_spells.py`, `tests/test_tier_skills.py`, `tests/test_tier15_effects.py`, `tests/test_split_party.py`, `tests/test_tiles_validation.py`
- Last validation pass: 2026-05-19 (split party, tile validation, tables/reference docs)

## Next depth (planned)

1. ~~Class profile data audit (`classes.json` vs rulebook starting gear/Life).~~ Done 2026-05-19.
2. ~~Expert skill catalog, L5+ fork, tier training, and core effect wiring.~~ Done 2026-05-19.
3. ~~Remaining expert skill / expert spell effects (crafting, Whirlwind, Shield Bash, etc.).~~ Done 2026-05-19.
4. ~~Combat round log summary; multi-target spell UI.~~ Done 2026-05-19.
5. ~~Named save labels for Saved Games.~~ Done 2026-05-19.
6. ~~Class tricks Tiers 3–4 and heroic/legendary skill learning UI.~~ Partial 2026-05-19 — catalogs, learning forks, Tier 3–4 wiring, and home implementation tables done; remaining heroic/legendary effects open.
7. ~~Split party session model (EE p.105) and simultaneous sub-fight UI.~~ — starter 2026-05-19: detach/reattach/scout, detached wandering checks, mixed-encounter simultaneous rounds; polish remote detached combat and flee/reaction paths.
8. ~~Validate placeholder `tiles.json` rows (01–06, 11–66).~~ — structural validation 2026-05-19; gif assets and rulebook layout audit ongoing.
9. First adventure manifest (`caves-of-the-kobold-slave-masters.pdf`).
