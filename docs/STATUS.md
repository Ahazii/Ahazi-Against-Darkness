# Current Status

Last updated: 2026-06-18

## Summary

The project is a FastAPI + SQLite random dungeon with a browser UI, structured
rule tables, visual map element editor, and a starter faithful loop for level-1
Four Against Darkness play.

### Home screen layout (May 2026)

- **Create character:** collapsible section; class name and role overlay the
  portrait (art visible beneath a top gradient); hover shows rulebook summary.
- **Character roster:** scrollable list (~4 heroes visible) to keep the left
  column compact; drag handles feed the party builder.
- **Party builder:** four marching-order slots (drag from roster, double-click,
  or Add to party); replaces the old checkbox grid.
- **Rules reference:** searchable summaries (rest, flee, class abilities, split party, heroic/legendary skills, Combat Focus,
  camp regroup/bank/transfer, consumables, etc.) from
  `rulebook_reference.json` (140 curated implementation/reference sections),
  with category and implementation-status filters (exploration, combat, classes,
  economy, equipment, spells, quests).
- **Rules tables:** collapsible panels listing all dungeon/adventure tables,
  equipment shop rows, **expert/heroic/legendary skills**, **class-trick implementation status**, **map-element validation summary**, tier training costs (Abyss/FD),
  monster bestiary spawn templates, per-foe reaction tables, **map element definitions
  (`tiles.json`)**, **generated/custom icon registry (API defaults + `icons.json`)**, and class profiles from
  `classes.json` — each group collapses independently; automated test keeps
  `RULES_TABLE_ORDER` in sync with `dungeon_tables.json`.

## Working

- App starts from `src/app/main.py`; runtime state in `DATA_DIR/game.db`.
- Starter rules load from `data/rules/` with editable overrides in `DATA_DIR/rules/`.
- Character pool, four-hero parties, marching order, export/import, saved games.
- **Adventure lock:** heroes in an active session cannot start another; lock clears on complete or session delete.
- **Camp / saved regroup:** swap party members while camped outside or from a saved game (Regroup Party on party sheet).
- **Camp panel / bank:** camped sessions expose Return to Dungeon, Bank, Transfer,
  Equipment Shop, and Abandon Dungeon actions. The bank deposits carried dungeon
  gold into home funds and withdraws up to the dungeon carry limit. The Home
  Screen Bank button opens the same camp bank when an active session is camped
  outside.
- **Gear transfer:** give inventory items or gold between heroes on the home
  screen (roster), during exploration (party sheet), or between the camped party
  and available roster heroes; blocked in combat. Home roster inventory is
  labelled as stored gear, and roster gold is home-bank gold.
- **Equipment shop (home):** buy Expanded Edition gear before/between adventures (pp.81-88), including quantity buys such as 5x Bandage;
  sell loot for gold (half list price; listed/fixed magic resale); class restrictions;
  weapon-default dialog on roster and party sheets. Roster gold is home bank
  gold; camped active adventurers can spend carried + banked gold; 200gp carry
  limit applies only in the dungeon.
- **Inventory:** carry limits (200gp; starting class gear free; +3 extra weapon slots,
  2 shields max; two-handed = 2 slots); default melee/missile weapons; combat weapon
  swap (1 turn); over-encumbrance −1 Defense/Saves for extra gear or excess gold;
  transfer respects capacity in-dungeon; roster sync after in-dungeon transfers.
- **Session → roster:** clean dungeon exit persists gold, loot, levels, spells,
  XP tallies, and default weapons to the character pool; UI reloads roster.
  When the completed party leaves the dungeon and ends the adventure, the UI
  returns to the home screen after the roster save completes.
  Camped active sessions also refresh spells/resources and mirror roster-visible
  fields for healing, equipment shopping, and regrouping before re-entry.
- Random sessions: map element rolls, placement, truncation, reroll/fallback placement, exploration, search,
  rest (rulebook p.114: once/adventure, cleared room + adjacent tiles, nail doors, Life or ability recovery, 1-in-6 wanderers), combat, reactions, traps, treasure, wandering monsters, special events.
- **AI Adventure (imported manifests):** prompt builder, validate/import UI, play installed modules (`crypt-of-whispers` bundled and seeded to `DATA_DIR/Adventures/`). Fog of war on main map and combat minimap, manifest-driven exits with surface entrance and dungeon leave markers. **Live allowlists:** prompt and validator both use `build_adventure_allowlists()` from the server rules path (fixes false “unknown monster” when packaged `allowlists.json` differed from Tower). Expanded allowlist payload includes exit directions/kinds/statuses, `foe_spawn_names`, per-environment packs, and grouped validation `error_summary` in the import UI (`app.js` v0.68.38+).
- **Party sheets:** exploration consumable actions (herbal tonic, miners' ointment, gremlin repellant) no longer crash rendering (`inExploration` ReferenceError fixed in v0.68.31+).
- **Entrance doors:** chosen entrance path stays open when the party backtracks
  (rulebook p.25).
- **Closed doors (Exits panel):** unified per-exit list — each exit shows status plus
  travel or door actions; iron doors show “no bash”, highlight Fireball/Lightning when no Rogue,
  unrolled doors show 2d6 roll hint; warrior Bash/roll-door labels; shortcut buttons
  (Lock-pick, Bash, Open, Spellcast, Spend clues) with hero dropdown when needed.
- **Clues:** Search rolls first, then on 5–6 the player chooses hidden treasure,
  secret door, secret passage, or 1 Clue held by a selected character. Held
  Clues persist on individual roster characters between adventures; the party
  total is derived from those holders. They can be spent deliberately on
  a selected 3-Clue p.123 Secret reveal, wizard/elf expert spell learning,
  Expert-trained druid spell learning, illusion doors, lever doors, and special
  clue uses as wired. The Secret picker records chosen Secrets on the discoverer;
  hidden treasure, Location of a Magic Item, Location of a Scroll, Weakness of
  a Foe, Deal with a Foe, True Name of a Spiritual Entity, New Spell,
  Increase of Magical or Spiritual Power, Your Enemy Is in the Dungeon,
  The Prisoner, Terrifying Secret, Secret Diet, and dragon-slayer are wired; potion recipe prerequisites/payment
  unlock the 50gp shop potion price; Big Money Buyer triples one gem/jewel sale
  and is consumed. Future-timing Secrets now show timing prompts on home/live
  character sheets, encounter-start log hints, and the combat status strip;
  foe-targeted Secrets can be applied from foe menus. Any
  still-unwired Secret entry remains recorded for manual timing. Trade Information
  reactions can sell information for 25gp per held Clue without spending them
  or buy 1 Clue for 100gp, using only heroes physically in the encounter.
- **Barbarians:** cannot use potions, scrolls, or magic items (may carry for allies).
- **Quests:** Lady in White offer, Quest Table, progress tracking, Ongoing Quests
  panel, quest map marker, Epic Rewards on claim; bring-alive via subdual.
  Quest progress logs now explain accepted objectives, wrong boss outcomes
  (slain instead of subdued, subdued instead of slain), and turn-in blockers.
  The Ongoing Quests journal shows objective/progress/turn-in/reward rows, keeps
  Claim visible with disabled-state reasons until the reward can be claimed, and
  the quest map marker opens the same status with a legal Claim action when ready.
  Epic Rewards now apply concrete table effects for Kerrak Dar's 1-Clue 500gp
  hoard, Enchanted Weapon's keep-best attack roll until adventure end, Shield of
  Warning's shield protection during surprise/fleeing/shield-ignored combat,
  Holy Symbol of Healing's +2 Healing prayer bonus plus temple-paid cleric
  resurrection attempt, Arrow of Slaying's rolled-target/bow-only 3 automatic
  damage, and Book of Skalitos as a six-page basic wizard scroll bundle.
- **Economy:** Classical / Slow and Sure / Old School / Slower Advancement XP;
  wandering healer and alchemist (potion + blade poison); potions in combat or
  exploration (once per hero per adventure); Recipe for a Potion unlocks the
  50gp shop potion price; Big Money Buyer triples one gem/jewel sale.
- **Special events/features:** room event and feature table results always add
  player-visible Event/Feature log lines; targeted effects such as ghost fear,
  spore-cloud damage, puzzle-box damage, healing, blessings, and curses name the affected
  hero and remain visible in Summary log mode. Statue and puzzle-box features
  now present the PDF choices explicitly: touch/leave the statue, or attempt/leave
  the puzzle box, with failed puzzle attempts keeping the box pending; the map
  marker is visually distinct and focuses those choice controls from the tile.
  Caverns and fungal grottoes special-event/item/trap tables have been reset to
  the owned PDF rows (EE p.155-161), replacing earlier placeholder rows. Fungal
  spore cloud is wired; environment-trap rows now resolve their PDF target/save
  shapes, including sleep spores, slime patch, mycelium snare, shrieking mushroom,
  and cordyceps infection. Rolling Boulder now requires the PDF front/back and
  blocked-opening choices from the map trap menu. Spore Cloud, Slime Patch, and
  Shrieking Mushroom now perform their PDF wandering-monster follow-up checks.
  Hidden Pit exposes the PDF 1-Clue Secret Passage option in the Clues panel after
  the trap is triggered. Caverns/fungal cavemen, scout, dwarf miner, dwarf-party
  gem, fungal merchant, and mycelial-warning event rows now expose
  map-marker choices with hover hints and apply their PDF effects, including
  paid no-surprise/+1 Save warnings, feed/fight branches, dwarf gem risk, dwarf
  miner next-tile preview after trade, fungal merchant +20% equipment buys/resale,
  and ignore-next-trap/wanderer mycelial warning. Ghost events log immunity, failed fear saves, and Life loss per hero; repeated healer,
  alchemist, and refused Lady in White events show their substitution reason and
  route to the proper wandering-monster or trap UI. Regression coverage now
  asserts the corrected environment tables do not drift from the PDF rows.
- **Level-up:** Expanded Edition mid-adventure advancement — Basic d6 > Level (6 always
  succeeds); Expert+ tier dice (d8+2 … d20+10 per Forsaken Depths). L5+ classical
  fork: **Level up** or **Learn expert skill/spell** on the party sheet (monster-type
  prompt for Impervious / Sworn Enemy). Tier training
  (Expert/Heroic/Legendary) between adventures. +1 Life and max Life, spell slots,
  caster spell picker; same-PC-twice rule enforced.
- **Class catalog compliance:** all 20 `classes.json` profiles are guarded by an
  exact canonical signature covering Life, wealth, starting gear/spells, ability
  labels, status, and descriptions. Home **class_profiles_table** is generated
  from that same locked catalog.
- **Economy/XP/reward table compliance:** the related home tables for XP modes,
  economy services, equipment shop, treasure, hidden treasure, magic/special
  treasure, quests, epic rewards, and tier training are locked together by a
  family API signature. Generated equipment-shop and tier-training rows are
  parity-checked against their source catalogs, and tier-training rows now carry
  Forsaken Depths source page 9.
- **Exploration/doors/traps/generation table compliance:** door, dungeon trap,
  caverns/fungal trap, search, wandering-monster, room-content, special-event,
  special-feature, environment event, and map-element validation tables are
  locked together by a family API signature. Static rows are parity-checked
  against `dungeon_tables.json`; map-element validation rows are generated from
  the locked `tiles.json` catalog.
- **Spells/skills/class-abilities/combat reference compliance:** spell, scroll,
  expert/heroic/legendary skill, expert implementation, class trick, EE ability
  flag, combat modifier, and combat note tables are locked together by a family
  API signature. Generated skill tables are parity-checked against their source
  catalogs, expert implementation rows are now Abyss-only with source pages, and
  EE ability flags remain separated in **ee_class_trick_flags_table**.
- **Expert skill effects:** Abyss-only expert-skill catalog wired in combat/exploration — Brawler,
  Orcslayer, Deadly Accuracy, Gladiator, Impervious, Withstand Pain, Culling, Dead
  Shot, Deadly Strike, Double Attack, Stabbing Attack, Protective Incense, Danger
  Sense, Negotiator (reaction adjust), search helpers (Detective, Intuition, Stone
  Mastery), Turn Undead, Berserk Fury, and more; home **expert_skill_implementation_table**
  lists wired vs planned. EE class-trick/ability flags that share the ability UI
  are separated into **ee_class_trick_flags_table** so the Abyss catalog remains
  PDF-pure.
- **Final Boss:** d6 + major-foe tally on room encounters (not wandering majors);
  scout-ahead reveals/checks room Final Boss status immediately; triple treasure;
  extra XP roll; prominent Final Boss foe chips/cards; a completion banner appears
  after the Final Boss dies so the player knows the main dungeon objective is done.
- **Expert spells:** all six Abyss expert spells wired; Mass Teleport ally/destination picker and Lifeforce amount in combat and exploration; home **expert_spells_table** lists mechanics.
- **Named save labels:** optional label when saving; shown in active/saved game lists.
- **Consumables:** flammable oil/lantern oil (10gp shop + combat splash); acid vials (Fiendish loot / 15gp resale — not shop buy); wolfsbane vs lycanthropes; berserker mushroom pre-combat rage; spend torch to burn spider webs; map fragment (caverns treasure); wand of power (Fiendish); enchanted paint (gear/rations + paint doors); rare mushrooms (fungal p.159); fungal rare items (p.161 — Red Death, Xicthul's Cap, White Angel basket, Morel Crusher, leafsteel/dead-body choices). **Cavern Wraith** per-turn life drain if not hit each round. **Fiendish Wraith** boss: 2-in-6 lantern extinguish at fight start, on-hit level drain.
- **Play context (outdoor terrain):** `PlayContext` in `terrain.py` combines per-tile **environment** (dungeon/caverns/fungal_grottoes table routing) and **terrain** (indoor/outdoor/forest/swamp/jungle/water/desert). Entrance tiles are outdoor at the dungeon mouth. Session flags `alter_weather_active` and `forest_pathway_active` clear on rest. Gates druid outdoor spells, illusionist Glamour Mask/Banquet, ranger double bow/sling, and druid companion wilderness entry. Home **play_context_table** and searchable **play_context** rules reference; live `session.play_context` on API reads.
- **Druid animal companion / Call of the Wild:** auto-summon on wilderness entry
  (1 Food ration); fights each round; Madness if slain. L10+ druids can answer
  Call of the Wild, leaving the party for d6 dungeon-time turns before rejoining.
- **Halfling Luck:** reroll search and treasure on current tile; combat attack/defense rerolls; failed save reroll; flee without parting blows.
  Escape; once-per-adventure expended tracking; spell tooltips on party sheets;
  **basic_spells_table** on home screen lists connect rolls and damage/effect text;
  Fireball minion mass-kill uses max(1, spell total − minion Level); **mummy +2**
  on Fireball connect; exploration casting (door magic, Clues on illusion doors);
  scroll burn and wizard copy-to-spellbook; **charged wands and staves** (use from
  party sheet, 1 charge per cast, no memorized slot).
- **Combat:** exploding-d6 attack/defense, armor/shield, corridor ranks, wandering
  rear ambush, p.146 round-0 initiative (surprise / attack-immediately / reactions-first),
  post-ranged unarmed (−2) and foe draw-weapon turn economy, class modifiers,
  minor multi-kill, major-foe level drop, morale, flee/withdraw, blade poison,
  poisonous foes (named poison threat/save/extra damage + lingering poison), **monster template effects** (encounter-start charge/surprise/shapeshift/tar spit; on-hit disease/petrification/slime disease/level drain/magic penalties from bestiary rows), mirror-image absorption, two-step magic
  resistance (connect vs L, penetrate vs L+MR), troll regeneration (summary-visible Life recovery or blocked recovery; fire, acid vials, lightning,
  and lantern oil suppress regen), held/fog/specter combat effects, subdual damage, missile combat (opening volley + corridor rear rank),
  weapon-type modifiers, once-per-adventure spell consumption; **round summary**
  line after each Fight Round names hero/foe damage, kills, wounds taken, regeneration
  blocks, and truly quiet rounds. Undead/holy interactions are explicit in the
  log: clerics show full-Level Attack vs undead, crushing weapons show their
  skeleton/undead bonus, Blessed Temple/Shrine attack bonuses apply and end when
  an undead or demon foe is slain, holy water remains valid for barbarians, and
  Sleep immunity names the affected foe. Turn Undead now logs per-foe
  success/failure, completes combat when it destroys the last foe, and its UI
  explains no-undead and already-used states.
- **Status hover text:** hero and foe status chips explain Shield, blessed
  undead/demon bonuses, poison, MR, regeneration, bloodied/subdued, multiple
  attacks, caster/dragon/construct traits, and Final Boss tags wherever those chips are rendered.
- **Combat Focus:** default layout during combat and pending encounters — tactical room map,
  top foe chip strip (category colors, grouped minor foes, Final Boss emphasis,
  hover/click traits such as undead, poison, MR, caster, dragon, construct, regeneration, and attacks),
  command rail (Exits / Encounter / Log following Summary/Verbose mode), hero drawer for targets,
  abilities, spells, class tricks, and Luck rerolls; slim action deck; optional cinema view.
  Summary log mode preserves round-summary outcome lines and targeted state/effect
  changes (curses, healing, poison, buffs) while filtering extra rolls, table
  lookups, and modifier totals into Verbose mode.
  Combat status also calls out active foe specials such as poison saves, MR tiers,
  regeneration, undead/holy rules, construct immunities, and multiple attacks before a round resolves.
  The encounter panel expands those live foe specials into rule reminders for poison,
  MR, regeneration, multiple attacks, constructs, undead, and dragons; undead foe
  chips call out cleric full-Level Attack, holy water, Turn Undead, and common
  sleep/illusion immunity.
  Expected foe attacks group multi-attack foes into one row while preserving repeated targets.
- **Monster and reaction compliance:** `monsters.json` is guarded by exact
  canonical signatures for all 76 indexed monster stat rows and all 217 reaction
  rows across 93 reaction tables. The home Rules table API also has a compliance
  allowlist so new tables fail tests until classified as PDF-locked, generated
  from locked data, or app validation.
- **Mechanic regression map:** `data/rules/mechanic_regression_map.json` now
  links the major implemented gameplay families (Secrets, Reactions, Quests,
  Special Events, Traps, Treasure, Class Abilities) to their structured tables,
  Rules Reference entries, backend actions, UI markers, persistence fields,
  split-party scope expectations, and test files. The guard also lists
  indexed-but-not-playable rules so partial rows cannot masquerade as fully
  implemented gameplay.
- **Multi-target combat UI:** Double Attack second foe, Double Kick minor picks,
  Protective Incense ally, Infallible Missile L8+ second target, Phantasmal Binding / Water Jet foe rows.
- **Class tricks (Tiers 1–4, full):** acrobat tricks (incl. Knife Throw), assassin hide, illusionist distract/light/knife,
  gnome smokescreen/gadget/door/trap/free prisoner, mushroom spores/hyphae (four choices),
  paladin steed (+1 mounted outdoors), light gladiator/swashbuckler combat styles, bulwark limited healing,
  kukla hair lockpick; see `class_tricks_implementation_table`.
  kukla Army of Dolls, bulwark Sacrifice Defense/Shield, paladin Summon Steed and Divine Smite,
  acrobat Graceful Move social-save reroll. Targeted class abilities expose party-sheet
  selectors where needed, including paladin healing, Combat Acrobatics, Lesser
  Necromancy, gnome free restraints, and kukla rings. Ability flags used by the
  shared expert/ability UI live in **ee_class_trick_flags_table**, separate from
  the Abyss expert-skill catalog.
- **Swashbuckler traits:** EE p.61-62 optional trait table is exposed as
  `swashbuckler_traits_table`; new Swashbucklers pick or roll a trait at creation.
  All six traits are wired: Flourishing Strike / Riposte (combat abilities),
  Taunt / Lucky Hat / Blade Dance (hero-sheet buttons), Daring Escape (flee).
- **Heroic/Legendary skills:** **45/45 heroic + 20/20 legendary** wired; catalogs, classical/slower XP learning forks; home tables show full status.
- **Split party:** Party sheets separate **Group 1 - Main Group** from **Group 2+ - Detached Group** blocks; Leave behind / Rejoin / Scout ahead; detached wandering checks; Detached combat panel for remote wandering fights; simultaneous front/rear vs major/minion fights; reactions, flee/withdraw, spellcasting, common consumables, and class abilities use heroes on the current tile. Scout ahead is a two-step flow: select a scout on the party sheet, then choose an open exit from the map door marker menu or Exits panel. The scout enters the next map element alone, immediately reveals room Final Boss checks for major foes, rolls a Stealth Save if foes are present, and can either wait for the party to follow or navigate back to rejoin. Failed scouts can check reactions or fight one forced solo round with foe initiative; scout Bribes spend only the scout group's carried gold/weapons. After that the main party can **Rush to Scout** or the scout can flee back. L10+ druid Call of the Wild uses the same detached-group display but blocks navigation/combat until its d6-turn countdown ends. Selecting a scout auto-opens Exits with status guidance; closed doors explain that they must be opened before scouting; detached scout rows expose Navigate back / Wait here controls. Combat UI surfaces (foe chips, hero chips, tactical room tokens, legacy combat rows, bulwark guard targets) show only combatants physically in the fight via `combatPartyMembers()`, mirroring the engine's `combat_party()` scope.
- **Illusionary Servant:** extra carry capacity (200gp + weapon slots) until trapped;
  **Illusionary Sword/Fog** turn tracking and combat effects wired.
- **Bandages (p.89):** use once per hero per adventure in exploration (+1 Life); may
  target self or a wounded ally.
- **Fallen heroes (p.44–45):** carry body (rearguard, auto-hit), deliver at exit,
  redistribute gear, 1000gp resurrection (d6 ≤ Level); recovery panel in session UI.
- **Door saves:** encumbrance on lock-pick/bash; locked doors require Rogue or Warrior/Barbarian.
- **Rogue traps:** a rogue in marching-order position 1 or 2 may attempt to detect and disarm a trap before it goes off.
- **Loot:** claim treasure splits gold evenly among survivors (200gp carry cap),
  redistributes capped shares to heroes with capacity, and logs capped heroes plus item recipients.
  **Magic weapons (p.163):** generic treasure entry rolls d6 for weapon type at
  award; +1 Attack when wielded as default; class/magic restrictions apply to
  wielding/use while treasure pickup can assign restricted magic weapons to any
  legal carrier with capacity; fixed resale
  (100gp + 2× weapon cost).
- **Reactions:** 116 named per-foe d6 reaction tables (265 rows) plus four category fallbacks; direct named coverage for all indexed `monsters.json` rows with PDF signature locks in `tests/test_bestiary_coverage.py`. Standard gp/weapon bribes, Fools' Gold, Capture, Puzzle, Trade Information, Magic Challenge, Blood Offering, Quest, Offer Information, Sleep (data-driven `attack_bonus_first_round`), Buy Weapons, Halfling Mushroom Picker trade, Trial/Challenge of Champions, and all special `bribe_*` keys are actionable. **2026-06-17 polish:** per-item give/sell buttons for gems, scrolls/potions, weapons, and magic items; compound food/gold/mushroom mode buttons; Wraith `bribe_magic_item` normalization; Dwarf Miser blocks all bribes; scout path parity for special outcomes; gem bribe counted resale log. Combat Focus and legacy reaction controls show Miser notes and disabled Pay Bribe when applicable. Failed-scout reactions use scout-local gear/gold only. Regression: `tests/test_reactions.py`, `tests/test_special_bribe_reactions.py`, `tests/test_secrets_reactions_table_family.py`. Index: `docs/REACTION_TABLES_LIST.txt`.
- **Treasure:** room-content rolls logged on entry; empty hoards clear map marker;
  claim tooltips explain disabled state.
- **Map UI:** viewport zoom/pan (overlay pinned to viewport), wheel zooms around
  the pointer, drag pans, **Rm** centers the current visible room, and **All** fits
  the visible explored map; new/current rooms auto-center on entry; draggable
  home roster height; compact icon controls for party-sheet expand/collapse;
  transfer blocks explain exact carry-slot limits; active camped heroes show
  In hand/Bank gold and can bank carried gold from their sheet. Collapsible
  **room panel** (top-right), **exits overlay** (bottom-right, scrollable when many
  exits), and **icon key** (bottom-left) on the map; draggable log/map and
  side-panel splits; expandable compact session log; room-state markers; ongoing
  quests; exit labels; door open/closed state; environment badge and paper vs
  unlimited map mode. Room-state markers now distinguish searched rooms,
  defeated/live foes, full/claimed/empty treasure, active/resolved traps,
  fallen/detached heroes, active detached navigation groups, vendors/events/quest
  givers, and current-party class icons. Map door/passage context menus mirror
  the Exits overlay, including scout-through and active detached navigation.
  Pending encounters and combat show a top foe chip strip above the map/tactical stage.
- **Session UI:** sticky action bar (Search, Rest, Claim Treasure, etc.) at top of
  side panel; **strict encounter entry** when living foes are on the current tile
  (p.146: Check Reactions or immediate action; surprise auto-rolls mandatory Reactions first);
  legacy Start Combat fallback for older paused saves; **2×2 party sheet grid** on wide screens; **party sheet accordion**
  with equipment/inventory header icons, visible Expert/Heroic/Legendary tier
  labels, expand/collapse-all controls, and per-hero exploration/combat actions;
  compact **Regroup Party** panel (collapsed by default) with swap instructions;
  ally bandage targeting; **Fight Round** combat button label.
- **Environments (EE p.112–113):** secret passage discovery prompts the player to choose dungeon, caverns, or fungal grottoes; trap, special-event, treasure-roll-6, and spawn tables route by environment; map tiles tint brown (caverns) or green (fungal grottoes); starter table rows on home screen (nine environment keys — see below).
- **Paper map mode:** optional 20×28 grid at session start; placement blocked outside bounds.
- **Map Element Editor:** validation panel, export/import, save reload; stale
  partial Docker tile overrides no longer shadow packaged metadata.
- **Home screen:** resizable saved-character roster with tier badges; **Rules reference** search plus unified collapsible **Rules
  tables** panel — all `dungeon_tables.json` keys plus merged
  `equipment_shop_table`, monster bestiary spawn templates (incl. `caverns_*` /
  `fungal_grottoes_*` categories), per-foe reaction tables, **map elements
  (`tiles.json`)**, **map_elements_validation_table**, **generated/custom icon
  registry**, class profiles, expert/heroic/legendary skills/spells, expert skill and class-trick implementation status/source pages, and
  tier training costs in nested groups; each table row collapses independently. Compliance tests now guard spell/scroll row order, class/monster catalog signatures, skill/trick source-page propagation, and Rules Reference table-key coverage.
- **Rules reference scope:** the searchable reference is not a full extraction of
  every owned PDF. It is the player-facing index for rules the app implements or
  exposes; dense catalogs and roll tables live in the structured Rules tables
  instead. New PDF rules should be added to `rulebook_reference.json` and/or
  structured tables when they become engine-visible behavior.
- **Home screen — character UI:** collapsible create-character block; class labels
  on card tops; scrollable roster (~4 rows); drag-and-drop party slots.

### Home rules tables — environment keys (Tier 3)

| Key | Rulebook ref |
| --- | --- |
| `caverns_special_events_table` | p.155 |
| `caverns_special_features_table` | p.112 |
| `caverns_water_pool_table` | p.112 |
| `fungal_grottoes_special_events_table` | p.156 |
| `caverns_special_item_table` | p.160 |
| `fungal_grottoes_rare_item_table` | p.161 |
| `fungal_grottoes_rare_mushroom_table` | p.159 |
| `caverns_trap_table` | p.165 |
| `fungal_grottoes_trap_table` | p.166 |

### Home rules tables — clue economy

| Key | Rulebook ref |
| --- | --- |
| `clue_spends_table` | p.24, p.32, p.102, p.107, p.108, p.109, p.123 |
| `secrets_table` | p.123-124 |

`clue_spends_table`, `secrets_table`, the category reaction tables, and all
named monster reaction tables from `monsters.json` are locked together by
`tests/test_secrets_reactions_table_family.py`, including the Capture, Puzzle,
Magic Challenge, and Trade Information encounter-decision rows.

## Known Gaps

- Remaining p.123 Secret hooks: the indexed Expanded Edition Secret catalog is
  wired for live play; authored adventure-specific special clue spends remain.
- **Heroic/legendary skills:** **45/45 heroic + 20/20 legendary** wired (combat, exploration, reactions, rest, traps, resurrection).
- Validate cavern/fungal table row text against owned PDF (starter tables wired).
- **Split party** (EE p.105): validated — detached groups, true scout-ahead with Stealth Save, immediate scout Final Boss reveal, one-round failed-scout branch with Rush to Scout / scout flee, map/Exits navigation parity, active detached navigation with map marker, detached wandering checks, remote detached combat rounds, druid Call of the Wild countdown, simultaneous sub-fights, current-tile reaction/flee/action scoping, and combat UI scoped to heroes physically in the fight.
- **Tile validation**: structural checks for all 01–06 and 11–66 tiles via API and `tools/validate_tiles.py`.
- **AI Adventure mode:** MVP playable — prompt, import, `crypt-of-whispers`. Live allowlists synced between prompt builder and validator; `GET /api/adventures/allowlists`. Details and limits: [`docs/AI_ADVENTURE_MODE.md`](AI_ADVENTURE_MODE.md).
- PDF-authored adventures (human extraction) share the same manifest schema; not automated yet.
- Every PDF in `Rules/` is an approved source of truth for future extraction,
  including Fortress of the Warlord. Fortress is mainly an authored adventure
  and is not a current implementation priority; its outdoor and hex-map rules
  are planned for a later outdoor map/navigation phase.
- Per-square tactical positioning (marching order only).
- Ruleset/theme profiles for non-fantasy books.
- Noun Project icon attribution completeness for public release.
- Exact map elements are validated: all 42 `tiles.json` rows (01–06, 11–66) have been manually checked against the rulebook layouts, with structural validation and regression tests retained.

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.

## Maintenance scripts

- `scripts/patch_character_spells.py` — repair prepared spell lists on character
  records in `game.db` (all sessions or a named hero).
- `tools/validate_tiles.py` — structural validation for all 01–06 and 11–66 tiles.
