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
| Four Against the Abyss | partial | Expert tier, expert skills/spells, three Secrets, retainers and professionals; **Abyss profile** with 2d6 room-content routing, Abyss monster/event tables, claimable Abyss treasure, and Abyss wandering spawns | Exact automation for long-form traps/features/events, Trial of Champions/hordes/multiple bosses, full diseases/transformations, campaign plots |
| Forsaken Depths | advanced partial | Tier entry/dice, 45 Heroic skills, 20 Legendary skills, **6 Heroic spells (catalog + cast)** including Fire of Truth chaos-hit bonus, Teleport Enemy return tracking with occupied-room reaction rolls, and Mass Blessing party/hireling condition choices; Legendary spell cast path, **72 validated tiles**, FD dungeon/river runtime, quests, citadels, TCOTFD branch | Remaining FD content families and manual sign-off |
| Adventurers' Guild | foundation + shell | Persistent roster, multiple parties, banking, **campaign state** (`days_passed`, TAG banking toggle, `/api/campaign`) | Settlements UI, troupe rules, downtime, availability/Streetwise, rumors, treasure maps, Guild jobs |
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

- minion leaders, multiple bosses, hordes and Trial of Champions rules;
- detailed trap, special feature, unique event, banquet/useful-stuff and magical defense effects;
- vampirism, Dark Plague, lycanthropy and campaign plots.

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

The roster and banking systems are reusable foundations, but there is no
Guild-sourced structured rules catalog yet.

The first implementation slice should be the campaign shell:

- home settlement identity and size;
- troupe ownership and party selection;
- passage of time and downtime actions;
- settlement availability and Streetwise;
- banks/magic lockers and treasure storage.

Later slices can add rumors, treasure maps, scenes, thematic dungeons, solo
missions, trinkets and Guild spells.

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
