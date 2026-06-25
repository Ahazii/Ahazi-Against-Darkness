# Master Rule Coverage

Last reviewed: 2026-06-25

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
| Four Against the Abyss | partial | Expert tier, expert skills/spells, three Secrets, retainers and professionals | Abyss dungeon tables, bestiary, leaders/multiple bosses, diseases/transformations, campaign plots and later tables |
| Forsaken Depths | partial foundations | Tier entry/dice, 45 Heroic skills, 20 Legendary skills, tile catalogs/editor and room-code metadata | Heroic/Legendary spells, FD dungeon/river runtime, encounters, hazards, hordes, items, quests, traps, events, Citadels, ruins and Secrets |
| Adventurers' Guild | foundation only | Persistent roster, multiple parties, banking and some between-adventure services | Settlements, troupe rules, downtime, availability/Streetwise, rumors, treasure maps, Guild jobs, thematic dungeons, trinkets, Guild spells and solo missions |
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

The existing audit currently covers expert advancement, skills, spells, Secrets
and hirelings. It is not yet a whole-book audit. A second phase must index and
implement the remaining PDF sections, especially:

- deeper/Abyss dungeon generation and content tables;
- minion leaders, multiple bosses, hordes and Trial of Champions rules;
- traps, treasure, hidden treasure, scrolls and magical defenses;
- Abyss vermin, minions, bosses, weird monsters and dragons;
- unique events and enchanted banquet/useful-stuff tables;
- vampirism, Dark Plague, lycanthropy and campaign plots.

## Four Against the Forsaken Depths

The tier/skill layer is implemented independently of the actual Forsaken Depths
adventure environment.

Current tile status:

- 36 dungeon definitions exist but remain placeholder/unvalidated;
- 35 river definitions exist; river 17 art is missing;
- runtime FD dungeon/river placement is not implemented.

Required content families include Heroic and Legendary spells, magic items,
river hazards/features/encounters, FD foes and hordes, quests, hallucinations,
ruins, traps, room content, Citadels, treasure, events and higher-tier Secrets.

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

- extensible ruleset profiles;
- registered environment/table families;
- reusable hex/overland travel state;
- currency/resource abstraction beyond gold;
- class and spell catalogs selectable by ruleset.

After those foundations, implement Netherworld classes, soul trade, food,
planar gates, terrain, shrines/strongholds, reactions, objectives, encounters,
spells, merchants and treasure.

## Cross-book architecture priorities

1. Add explicit session ruleset profiles and enabled source books.
2. Replace fixed environment literals with registered environment definitions.
3. Extract table routing and supplement actions from `random_dungeon.py`.
4. Split the browser UI by feature surface instead of extending one `app.js`.
5. Add schema/database migrations before introducing new persistent campaign
   state.
6. Require every completed rule family to link source rows, engine actions, UI,
   persistence and behavior tests.

