# Master Rule Coverage

Last reviewed: 2026-06-28

This is the program-level tracker for the current target books:

1. Four Against Darkness Expanded Edition (EE)
2. Four Against the Abyss
3. Four Against the Forsaken Depths
4. Tales from the Adventurers' Guild
5. Four Against the Netherworld

Book-specific compliance percentages must state their exclusions. A focused
audit such as expert skills or procedural dungeon play must not be presented as
whole-book completion.

## Status definitions

| Status | Meaning |
| --- | --- |
| validated | Structured source data, engine behavior, player UI/reference, persistence where required, and regression coverage are present |
| implemented | Playable behavior exists, but complete PDF/manual validation is still outstanding |
| foundation | Reusable supporting systems exist, but the book's actual rules are not substantially implemented |
| missing | No meaningful implementation yet |
| excluded | Intentionally outside the product goal, with the exclusion documented |

## Program overview

| Book | Current position | Major completed areas | Major missing areas |
| --- | --- | --- | --- |
| Expanded Edition | advanced | Procedural dungeon loop, classes, combat, equipment, dungeon/cavern/fungal tables, bestiary, reactions, Secrets, quests, Fiendish Foes, EE map catalog | Remaining manual sign-off, selected UI/fidelity edges, roleplaying/adventure-authoring scope decisions |
| Four Against the Abyss | partial | Expert tier, expert skills/spells, three Secrets, retainers and professionals; **Abyss profile** with 2d6 room-content routing, exact Abyss traps/features/events phase, claimable/choice Abyss treasure, Useful Stuff/magical defense item rows, Abyss wandering spawns, Abyss minion reaction/Trial routing, tactical targeting for minion leaders, multiple bosses, and hordes, core Abyss item use-actions/passive item math, Abyss affliction lifecycles for Dark Plague/lycanthropy/vampire-drain resurrection blocking, persistent playable campaign plots, vampire sire hunt/re-encounter, and large-room dragon-lair routing | Manual playtest sign-off for rare optional extended-campaign chaining and broader frontend decomposition |
| Forsaken Depths | advanced partial | Tier entry/dice, 45 Heroic skills, 20 Legendary skills, **6 Heroic spells (catalog + cast)** including Fire of Truth chaos-hit bonus, Teleport Enemy return tracking with occupied-room reaction rolls, and Mass Blessing party/hireling condition choices; Legendary spell cast path, **72 validated tiles**, FD dungeon/river runtime, quests, citadels, TCOTFD branch | Remaining FD content families and manual sign-off |
| Adventurers' Guild | partial campaign | Persistent roster, multiple parties, banking, **campaign state** (`days_passed`, TAG banking toggle, `/api/campaign`), home settlement identity/size/notes, troupe/guild/coffer state, active party selection, settlement storage, per-character TAG bank ledgers, magic lockers, platinum pieces, special-item availability, Streetwise Look for Clues/rumors/interrogation/Look Tough, travel to new settlements with simple or hex-route logging, treasure-map follow rolls, Gambling House gp outcomes, first twenty-eight treasure/service/procedure rows from TAG pp.9-20, p.54, and pp.61-66, TAG special foe supplement, TAG lead generation into normal installed adventures, TAG guide/checking docs, and TAG Actions for branch/clue/count/capture/reward/route/XP/trinket/Guild-spell/finance plus exact scene reward handling, safe generated-module route rewrites, Clue-gate follow-up scene insertion, optional side-scene removal, Speedy Recovery settlement-healing marker, Look Tough Streetwise bonus consumption, Wizard's Luck Gambling House workflow, and target-specific Troupe Switch/Silence/weapon enchantment markers | Broader playtest sign-off and stricter Guild leaving-restriction enforcement |
| Netherworld | missing/foundation only | Generic Madness/combat/economy primitives can be reused | Classes, expert skills, soul economy, food, planar gates, hex exploration, terrain, reactions, objectives, bestiary, spells, merchants and treasure |

## Expanded Edition

Primary audit: [EE_COMPLIANCE_AUDIT.md](EE_COMPLIANCE_AUDIT.md).

The current EE audit measures the random-dungeon solo application scope. It
excludes printed sample adventures, lore, roleplaying guidance and adventure
authoring. Those exclusions are acceptable only while they remain explicit.

Next work:

- complete and record the manual validation checklist;
- keep behavior tests paired with table/source locks;
- decide whether printed EE adventures are product targets or explicit
  exclusions handled through the authored-adventure pipeline.

## Four Against the Abyss

Primary audit: [ABYSS_COMPLIANCE_AUDIT.md](ABYSS_COMPLIANCE_AUDIT.md).

The existing audit covers expert advancement, skills, spells, Secrets and
hirelings. Phase B adds a playable Abyss random-dungeon profile and table
routing. It is still not a whole-book audit; remaining PDF sections needing
full automation include:

- remaining edge-case item polish after the core Abyss item actions/passive item math pass;
- manual playtest sign-off for optional extended-campaign chaining and the broader `app.js` decomposition.

## Four Against the Forsaken Depths

The tier/skill layer is implemented independently of the actual Forsaken Depths
adventure environment.

Current tile status:

- 36 dungeon + 36 river definitions validated in tile catalogs;
- runtime FD dungeon/river placement is implemented (see `FORSAKEN_DEPTHS_ENGINE.md`).

Heroic spells: 6-spell d6 table in `heroic_spells.json` with full cast resolver in `forsaken_depths_heroic_spells.py` (Cyclopean Idol bas-relief, Dark Pits scroll rewards, river/combat hooks). Legendary spells: catalog + cast resolver in `forsaken_depths_legendary_spells.py`.

Remaining content families include river hazards/features/encounters polish, FD hordes, hallucinations,
ruins, traps, room content sign-off, Citadels, treasure, events and higher-tier Secrets.

## Tales from the Adventurers' Guild

The roster and banking systems are reusable foundations. The first settlement
campaign slice is now playable, but there is no whole-book Guild-sourced
structured rules catalog yet.

Implemented first slice:

- home settlement identity, size, notes and random settlement-size roll;
- moving to a different settlement by simple 3d6-3 travel days or optional hex-map route logging;
- special-item availability with settlement-size modifier and fail-by-1 surcharge;
- Streetwise Look for Clues with character choice, bribe cost, class modifier and natural-1 consequence;
- first twenty-eight TAG treasure/service/procedure rows (through Streetwise Rules plus Adventurers Guild jobs, Trinkets, Guild spells, and TAG special foes), with hidden-trove risk roll, treasure-map price, moneylender pursuit, horn attraction, flammable-oil throw, aspergillum break, and row-level availability checks;
- TAG settlement Apothecary hook when TCOTFD is also in use;
- troupe name/active party/guild coffer state, settlement storage, fixed service purchases, magic lockers, Gambling House gp outcomes, Streetwise Listen to Rumors/Interrogate/Look Tough, and Following the Treasure Map / Map Leads To roll summaries;
- TAG Rumor Scene, Treasure Map, Thematic Dungeon, and Guild Job leads create normal installed adventure modules in the Adventure section/dropdown.
- TAG lead modules carry `source.parameters.tag_reference` with PDF pages, scene/theme notes, reward notes, and the current finale foes; all 12 Rumor Scenes, six Thematic Dungeons, and six Guild Job minor quests have structured profiles.
- TAG-specific monster supplement adds named finale/minion spawns for white gargoyles, mutant fish, Silent Scream cultists/priestess, hill giant, minotaur lord, bandit chieftain/guards, Gorungar/archers, griffin, red portrait horror, monoceros, and maze minotaurs without changing the locked EE bestiary rows.
- TAG Actions section resolves/logs social branches, Clue spends, variable counts, capture-alive outcomes, printed rewards, exact scene rewards, structured route markers, safe route rewrites to the latest generated module, Clue-gate follow-up scene insertion, optional side-scene removal, structured XP markers/awards, trinket use, Guild spell use/marker clearing, Speedy Recovery settlement-healing markers, Look Tough Streetwise bonus consumption, Wizard's Luck Gambling House resolution, per-character bank deposit/withdrawal, inheritance notes/transfers, storage robbery risk/recovery, moneylender enforcement, and guild upkeep with hover hints.
- Home-panel TAG tools are grouped into collapsible sections with compact `?` help summaries for settlement, troupe, travel, availability, Streetwise, storage, buyer, magic lockers, maps/adventure leads, and services/log.

Next slices:

- broader playtest signoff and stricter Guild leaving-restriction enforcement.

Later slices can deepen exact branch-specific item handling, robbery recovery,
and Guild spell math if playtesting shows those surfaces are needed.

## Four Against the Netherworld

Netherworld requires an overland/planar campaign mode. It should not be added as
special cases to the existing dungeon environment enum.

Prerequisites:

- ~~extensible ruleset profiles~~ (done 2026-06-24 — `ruleset_profiles.json`, session `ruleset_profile_id`);
- registered environment/table families;
- reusable hex/overland travel state;
- currency/resource abstraction beyond gold;
- class and spell catalogs selectable by ruleset.

After those foundations, implement Netherworld classes, soul trade, food,
planar gates, terrain, shrines/strongholds, reactions, objectives, encounters,
spells, merchants and treasure.

## Cross-book architecture priorities

1. ~~Add explicit session ruleset profiles and enabled source books.~~ (2026-06-24)
2. Replace fixed environment literals with registered environment definitions.
3. Extract table routing and supplement actions from `random_dungeon.py`.
4. Split the browser UI by feature surface instead of extending one `app.js`.
5. Add schema/database migrations before introducing new persistent campaign
   state.
6. Require every completed rule family to link source rows, engine actions, UI,
   persistence and behavior tests.
