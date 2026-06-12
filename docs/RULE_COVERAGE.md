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
| Doors | starter | Door Table, lock-pick/bash, iron/sealed/illusion/lever; iron cannot bash; Fireball/Lightning destroy iron when no foes; no-Rogue spell highlight on Exits panel; warrior roll-door/Bash labels. |
| Saves | starter | Trap/poison saves with class modifiers; door attempts apply encumbrance; locked doors require Rogue or Warrior/Barbarian; Stable Mind on mushroom madness. |
| Random map generation | starter | d66 placement, truncation, reciprocal exits, walkable masks, no-hard-stop reroll/fallback placement; optional 20×28 paper bounds. |
| Exact map element table | starter | 42 rows in `tiles.json`; structural validation passes for all keys (`map_elements_validation_table`, `tools/validate_tiles.py`); gif/rulebook layout audit ongoing. |
| Door table | validated | 2d6 Expanded Edition p.109; entry inheritance; Open Door flow; sealed/illusion/lever/iron exploration magic. |
| Special events | starter | Ghost, trap, healer (once per adventure reroll), alchemist, Lady in White, wandering subtable; caverns/fungal environment tables. |
| Search table | validated | d6 p.107; corridor -1; search choice UI; Clue rewards are assigned to an individual character and persisted on that roster entry. |
| Clues system | starter | Clues earned on Search 5–6 or bought via Trade Information (100gp); spent on illusion doors (3), lever doors (1), Secrets (3), wizard/druid spell learning (3). Individual hero tracking + party total. Prompt shown at 3+ Clues. **Completed 2026-06-05: "Someone Has Been Imprisoned" (p.102) wired** — spend 3 Clues when a hero is captive to generate and reveal the hideout tile with doubled guards. Rescue by combat or ransom (Level×10 gp per captive). |
| Secrets | starter | Expanded Edition p.123 Secret picker/table; selected Secret records on the discoverer and shows on home/party sheets. Hidden treasure, Weakness of a Foe, Deal with a Foe, Terrifying Secret, Secret Diet, potion recipe 50gp shop price, Big Money Buyer sale, dragon-slayer, and **Someone Has Been Imprisoned** are wired; remaining timed-use Secrets are recorded for manual timing. |
| Wandering monsters | validated | Search, alarm, backtrack, special-event subtable. |
| Traps | validated | d6 p.164; environment variants p.165–166; marching-order targets; Resolve Trap action. |
| Treasure | validated | d6 p.157; environment magic/special items p.159–161; magic weapons roll d6 type (p.163), +1 Attack when wielded, class/magic restrictions, fixed resale. |
| Hidden treasure | validated | Formula and complications p.108. |
| Combat modifiers | starter | Blade poison, poison foes, two-step MR (connect + penetrate tiers), mirror-image absorption, subdual, bribes, missiles, weapon-type modifiers; troll regeneration (fire, acid vials, lightning, lantern oil suppress regen), held/fog/specter combat effects; post-round log summary; multi-target spell/ability UI (Double Attack, Double Kick, Protective Incense, Infallible L8+). |
| Combat core | starter | p.91-97 attack/defense/morale/flee; p.146 round-0 initiative (surprise, attack-immediately, reactions-first); living foes auto-enter encounter state; immediate party actions forfeit Reactions; surprise auto-rolls mandatory Reactions first; post-ranged unarmed (−2) / foe draw weapon; major-foe L drop; corridor rules; Combat Focus layout + legacy combat panel. |
| Reactions and morale | starter | Per-foe bestiary tables + bribes; p.146 immediate action vs Check Reactions (mutually exclusive); category fallback. **Capture reaction (p.102) wired 2026-06-05**: minions may roll "capture" (roll=1); foes attack non-lethally; heroes reaching 0 Life are taken prisoner (one foe escorts each captive); rescue via 3-Clue hideout or ransom. |
| Fleeing | validated | Flee, withdraw, wandering pursuit. |
| Quests | starter | Quest Table, progress, Epic Rewards; bring-alive via subdual; bring-head requires lethal boss kill. |
| Potions | starter | Potion of Healing once per hero; alchemist purchase; home shop buy/sell; Recipe for a Potion unlocks 50gp shop price. |
| Equipment shop | starter | `equipment_shop.json` + home UI; p.16 buy / p.19 sell; class restrictions; lantern oil and acid vials; Big Money Buyer triples one gem/jewel sale. |
| Consumables | starter | Mushrooms (fungal grottoes p.159), lantern oil splash, acid vial throw; shop + party-sheet actions. |
| Death and recovery | starter | Fallen on tiles; carry body (p.44 rearguard, auto-hit); deliver at entrance; 1000gp resurrection; body theft on retreat. |
| Rest | validated | Once/adventure (p.114): cleared room + cleared adjacent tiles, nail doors (Bag of nails, 4gp), per-PC 1 Life or spent ability recovery, 1-in-6 wanderers (nailed = party first). Halfling Nourishing Meal when resting. |
| Class abilities (Tier 1) | starter | Barbarian rage (3d6 best, double damage), halfling Luck (flee, attack/defense/save/search/treasure reroll), swashbuckler Panache (+1 attack/defense), paladin prayer heal/reroll save with explicit target UI; rest recovery for spent rage/luck/prayer. |
| Class tricks (Tiers 1–4) | full | Tier 1–4 class tricks wired per `class_tricks_implementation_table` (incl. targeted paladin healing, Combat Acrobatics, Lesser Necromancy, gnome free restraints, and kukla rings/compartment). Split party uses `combat_party` for reactions and combat on tile. |
| Combat Focus | starter | Tactical map, command rail (Exits/Encounter/Log), hero drawer (expert + heroic ability picks), slim deck, cinema view; one-viewport layout. |
| Druid companion | starter | Wilderness auto-summon (Food ration); wolf/bear/panther; 1 attack/round; foe retaliation; Madness on death. |
| Rules reference | validated | Searchable curated implementation reference (124 entries): EE + Abyss + FD topics with `implementation_status` badges. It is not a full PDF corpus; rules exposed by the engine should appear here or in structured Rules tables. Skill/spell/trick catalogs and wiring live in Rules tables. Fortress of the Warlord PDF is present for later extraction, but no Fortress-specific rows are indexed yet. |
| Session rewards | starter | Every advance action saves the session (`store.save`). `persist_session_to_roster` fires on `mode == "complete"` AND on `camped_outside` — retreat sets `camped_outside = True`, so retreat also triggers roster sync. The session survives browser close at any point; characters are locked to the session and unlocked on completion. *(Note: an earlier doc version incorrectly stated "camp/retreat does not persist" — corrected 2026-06-12.)* |
| Rule table display | validated | Home lists all `dungeon_tables.json` keys + merged equipment/expert/tier/heroic/legendary tables + class-trick and map-element validation tables + monster bestiary + reactions + map elements + generated/custom icon registry; test guards sync. |
| Expert spells | validated | L5+ fork adds wizard/elf expert spells to repertoire; all six Abyss cast effects wired; druid 3-Clue spell learning uses `druid_spells_table`; Mass Teleport / Lifeforce UI in combat; home **expert_spells_table** documents mechanics. |
| Character positioning | starter | Marching order for traps and corridor combat. |
| Split party | validated | EE p.105: detach/reattach heroes on a tile, scouting ahead (two-step UI, open-exit selection, solo forward exploration with Stealth Save; Stealth Training expert skill), active detached-group navigation, detached 1-in-6 wandering rolls, simultaneous front/rear vs major/minion fights when mixed encounters occur. Reactions, bribes, Trade Information, puzzle saves, flee/withdraw, spellcasting, common consumables, and class abilities are scoped to heroes physically on the current tile. Pending detached wandering fights expose a Detached combat panel that resolves rounds remotely without moving the main party. Combat UI (hero chips, tactical tokens, legacy rows, bulwark guard targets) shows only heroes physically in the fight. |
| Capture reaction | starter | EE p.102: **wired 2026-06-05**. Minion foes may roll Capture (d6=1 on minion reaction table); attacks become non-lethal; heroes reaching 0 Life are captured (one foe escort per captive, stripped of gold). Spend 3 Clues on "Someone Has Been Imprisoned" to locate and generate the hideout tile (doubled guards, 2d6×2d6 cave adjacent to origin). Rescue by winning the hideout fight (captives revive with d3 Life) or paying a ransom (Level×10 gp each). Captured hero status shown prominently in the party sheet with contextual Find-Hideout and Pay-Ransom buttons. Tests: `tests/test_capture.py`. See gap table below for deferred items (inventory strip, ranger Clue reduction). |
| Imported adventures | missing | PDFs listed; manifests required. |
| Authored map rendering | missing | Waiting on manifest schema. |
| Environment variants | starter | Secret passage → caverns/fungal grottoes; table routing; paper 20×28 mode; home lists seven environment tables. |

## Gap analysis: remaining party-split mechanics (EE PDF survey 2026-06-05)

The following party-splitting mechanics were identified in the EE rulebook but are **not yet implemented**:

| Mechanic | EE Location | Status | Notes |
| --- | --- | --- | --- |
| Capture — inventory strip | p.102 | deferred | Rules say "stripped of equipment." Gold is stripped on capture. Full item/weapon strip is deferred: a Transfer Items mechanism exists for mid-dungeon handoffs, but without a "hold stripped items for return on rescue" store, items would be lost permanently. Implementing properly requires a `stripped_items` field on `SessionState`, moving weapons and inventory there on capture, and restoring them on rescue/ransom. Not done yet; the gold strip covers the sting in most sessions. |
| Capture — ranger Clue reduction | p.62 | deferred | The gap analysis cited p.62 but the ranger's `classes.json` description does not mention a Clue cost reduction; no verbatim rule text was confirmed. Trivially implementable if confirmed (check for `class_id == "ranger"` in party and subtract 1 from `CLUES_FOR_SECRET_XP` in `_find_captive_hideout`). Deferred until the rule can be verified against the PDF. |
| Magic Challenge reaction | p.102 | missing | Foes present a spell puzzle; success = peaceful, fail = fight. Defined as reaction key but no current foe table uses it. |
| Trade Information reaction | p.102 | starter | Sell information for 25gp/Clue without losing Clues, or buy 1 Clue for 100gp. Wired in engine, but "sell" path gold calculation may need audit vs PDF. |
| Puzzle reaction | p.102 | starter | Wired for L-based Save; no table currently references it. |
| Druid forced split (Call of the Wild) | p.38 | missing | At L10+ the druid may be compelled to leave the party for 1d6 turns to commune with nature. |
| Bard Song of Elidra full range | p.30 | starter | Wired for reaction roll bonus; multi-tile application and full "allies in adjacent rooms" range not implemented. |
| Active group switching (detached movement) | p.105 | **wired 2026-06-12** | "Navigate" button on each detached group heading makes that group active for navigation. The Exits panel routes movement through the active group's tile instead of the main party and the API forwards `detached_tile_id` for browser actions. Encounters at the destination queue as detached combat rounds. Dungeon exit blocked for detached groups. Active group auto-resets on reattach. Tests: `tests/test_active_group.py`. |

## Validation references

- Source PDFs currently used by implemented data/rules:
  `Rules/Four_Against_Darkness_Expanded_Edition.pdf`,
  `Rules/Four-Against-the-Abyss.pdf`,
  `Rules/Four_Against_the_Forsaken_Depths.pdf`
- Available for later extraction, not yet indexed/implemented:
  `Rules/Fortress_of_the_Warlord_ebook_final.pdf`
- Automated checks: `tests/test_rulebook_validation.py`, `tests/test_combat.py`,
  `tests/test_combat_modifiers.py`, `tests/test_reactions.py`, `tests/test_class_profiles_audit.py`, `tests/test_weapons.py`,
  `tests/test_magic_weapons.py`, `tests/test_spells.py`, `tests/test_spells_extended.py`, `tests/test_spell_expended.py`,
  `tests/test_inventory_transfer.py`, `tests/test_carry_limits.py`,
  `tests/test_equipment.py`, `tests/test_session_persist.py`,
  `tests/test_equipment_shop.py`, `tests/test_exploration.py`, `tests/test_economy.py`, `tests/test_level_up.py`,
  `tests/test_door_sync.py`,   `tests/test_initiative.py`, `tests/test_rest.py`, `tests/test_class_abilities.py`, `tests/test_rulebook_reference.py`, `tests/test_bandage.py`, `tests/test_tier1_combat.py`,
  `tests/test_class_combat.py`, `tests/test_death_recovery.py`, `tests/test_doors.py`, `tests/test_tier3_map.py`,
  `tests/test_tier_dice.py`, `tests/test_tier_training.py`, `tests/test_expert_skills.py`, `tests/test_expert_skill_effects.py`,   `tests/test_expert_spells.py`, `tests/test_tier_skills.py`, `tests/test_tier15_effects.py`, `tests/test_heroic_skill_effects.py`, `tests/test_split_party.py`, `tests/test_tiles_validation.py`, `tests/test_capture.py`
- Last validation pass: 2026-06-05 (capture reaction, clues system completion, gap analysis)

## Next depth (planned)

1. ~~Class profile data audit (`classes.json` vs rulebook starting gear/Life).~~ Done 2026-05-19.
2. ~~Expert skill catalog, L5+ fork, tier training, and core effect wiring.~~ Done 2026-05-19.
3. ~~Remaining expert skill / expert spell effects (crafting, Whirlwind, Shield Bash, etc.).~~ Done 2026-05-19.
4. ~~Combat round log summary; multi-target spell UI.~~ Done 2026-05-19.
5. ~~Named save labels for Saved Games.~~ Done 2026-05-19.
6. ~~Class tricks Tiers 3–4 and heroic/legendary skill learning UI.~~ Done 2026-05-19 — **45/45 heroic + 20/20 legendary** effects wired; split-party flee uses present heroes on tile.
7. ~~Split party session model (EE p.105) and simultaneous sub-fight UI.~~ — validated 2026-06-12: detach/reattach, true scout-ahead, active detached navigation, detached wandering checks, remote detached combat rounds, mixed-encounter simultaneous rounds, and current-tile scoping for reactions/flee/spell/consumable/class actions.
8. ~~Validate placeholder `tiles.json` rows (01–06, 11–66).~~ — structural validation 2026-05-19; gif assets and rulebook layout audit ongoing.
9. ~~Capture reaction (EE p.102) and clues system completion.~~ Done 2026-06-05 — capture wired for minion encounters; 3-Clue hideout generation; rescue/ransom flow; "Someone Has Been Imprisoned" secret.
10. ~~Active group switching — allow detached group to be made "Active" for navigation.~~ Done 2026-06-12 — "Navigate" button per detached group; Exits panel routes movement + door actions through active group; encounter queuing; API pass-through for `detached_tile_id`; 68 targeted split/frontend tests.
11. First adventure manifest (`caves-of-the-kobold-slave-masters.pdf`).
12. Ranger Clue-reduction for hideout searches.
