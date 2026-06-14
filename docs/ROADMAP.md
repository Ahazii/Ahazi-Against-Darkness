# Roadmap

## Phase 1 - Clean Foundation

Status: in progress

- Replace prototype code with FastAPI + SQLite foundation.
- Preserve local PDFs and tile assets.
- Add documentation and content pipeline.
- Add character pool, exact four-character parties, and starter random sessions.
- Add a structured placeholder map element definition file.
- Add first-pass map element rotation and metadata editing.
- Add smoke tests and deployment verification.

## Phase 2 - Faithful Random Dungeon MVP

Goal: one complete legal level-1 random dungeon loop.

Status: in progress — core loop playable; combat depth and editor validation ongoing.

Completed or starter-complete:

- Doors as explicit state (Open Door flow, entry inheritance).
- Room content, search, wandering monsters, traps, treasure, special events.
- Core combat, saves, reactions, morale, fleeing, death, blade poison, poison foes, magic resistance, missile combat, weapon-type modifiers.
- XP systems (four variants), gold, potions, Final Boss, quests and Epic Rewards.
- Home-screen rule tables (all `dungeon_tables.json` keys) plus monster bestiary.
- Searchable rules reference (`rulebook_reference.json`) on home screen.
- Rulebook Rest (EE p.114) and Tier 1 class abilities (rage, Luck, Panache, paladin prayer).
- Tier 1–4 class tricks wired (`class_tricks_implementation_table`, including kukla rings/compartment).
- Class profile audit (EE p.24–69): Life, wealth, starting gear; `tools/audit_class_profiles.py`.
- Inventory carry limits, default weapons, session-to-roster persistence on clean exit.
- Home equipment shop (buy p.16 / sell p.19) and weapon-default dialogs.
- Generated/custom icon registry for room states, playable classes, monster
  categories, and named monsters; Icon Editor can assign art for each row.
- Dice trace on exploration and many combat actions.
- Tests for tables, combat modifiers, weapons, exploration, economy, reactions, spells,
  carry limits, equipment, equipment shop, session persist, door sync.

Still open:

- ~~Tier 1–4 class tricks~~ — done (see `class_tricks_implementation_table`, including kukla rings/compartment).
- ~~Expand Luck reroll hooks (defense, saves, treasure, search)~~ — done (hero drawer + party sheet).
- ~~Named save labels~~ — done (user labels on save; `sessionDisplayTitle()` in UI).
- ~~Expert spell cast effects~~ — done (6 Abyss spells + combat/exploration UI for Mass Teleport / Lifeforce).
- ~~Combat round summary~~ — one-line recap appended after each Fight Round.
- ~~Mushroom consumables, lantern oil & acid vial in shop~~ — eat mushrooms (p.159); shop sells oil and acid.
- ~~Druid animal companion~~ — auto-summon on wilderness entry (1 Food ration).
- ~~Druid Call of the Wild~~ — L10+ forced split countdown using detached-party model.
- Replace placeholder `tiles.json` rows with exact starting (`01-06`) and
  generated (`11-66`) map element metadata.
- Validate map element footprints and multiple exits through the visual metadata
  editor and `tools/validate_tiles.py` / `GET /api/rules/tiles/validation`.
  Exits are placed on grid squares (not necessarily the outer footprint border).
- Continue validating walkable-space placement and truncation against more
  rulebook examples, especially cases where other exits would be covered.
- ~~Placement no-hard-stop fallback~~ — done: failed generated elements reroll
  through remaining valid keys; a 1x1 dead end is drawn only if every candidate
  fails.
- ~~Add optional fixed paper size~~ — done: unlimited (default) or 20×28 at session start.
- ~~Caverns/fungal grottoes table variants~~ — starter tables wired; validate row text against PDF.
- **Clue economy cleanup:** core behavior is wired: Search rolls first and
  successful searches present the four p.107 reward choices; found Clues are
  held by individual characters and persist on those roster entries between
  adventures; 3-Clue Secret/XP reveal is explicit;
  Trade Information reactions can sell clue information or buy a Clue, scoped
  to heroes physically in the encounter;
  wizard/elf expert-spell learning and Expert-trained druid spell learning can
  spend 3 Clues; special door clue spends remain explicit; the p.123 Secret
  picker/catalog is present, with hidden treasure, Location of a Magic Item,
  Location of a Scroll, Weakness of a Foe, Deal with a Foe, Terrifying Secret,
  Secret Diet, potion recipe shop pricing, big-money sale, and dragon-slayer
  effects wired.
  Remaining work: authored special clue spends such as Kerrak Dar-style hoards.
  New Spell, Magical/Spiritual Power, True Name, Enemy in the Dungeon, and
  Prisoner hooks are wired.
- Refine visual truncation beyond cell clipping if later rules require more
  precise pixel/vector masks.
- Add paint-mask or arbitrary polygon mask authoring if the per-square
  shallow-slope, two-square long-slope, and curved-corner masks are not precise
  enough for circular rooms or later line-of-sight needs.
- ~~Per-foe reaction tables / MR tier display~~ — current indexed bestiary names
  resolve through per-foe tables; foe chips show stacked MR tiers. Reaction
  outcome logs, Combat Focus outstanding-choice blocks, named Puzzle/Trade
  Information/Magic Challenge rows, and fight-to-the-death morale suppression
  wired in the reactions polish pass.
- ~~**Split party (EE p.105, p.79–80, Fiendish Foes p.180)**~~ — validated:
  detach/reattach on the current tile, scout-ahead into the next room with Stealth Save,
  immediate scout Final Boss reveal, failed-scout reaction / one solo round / Rush to Scout flow,
  map/Exits navigation parity, detached wandering rolls,
  simultaneous combat when major foes and minions share a tile. Reactions,
  bribes, Trade Information, puzzle saves, flee/withdraw, spellcasting, common
  consumables, and class abilities use only heroes physically on the current
  tile. Pending detached wandering fights now expose a Detached combat panel
  that resolves rounds remotely without moving the main party. Combat UI
  surfaces (hero chips, tactical room tokens, legacy combat rows, bulwark guard
  targets) hide heroes detached elsewhere via `combatPartyMembers()`
  (2026-06-11 playtest fix; true scout-ahead, active-group API/UI fix, map marker
  parity, detached navigation prompts, scout rescue flow, and foe chips 2026-06-12).
- Dedicated combat panel with per-hero targeting — done (Combat Focus hero drawer + legacy sidebar panel).
- **Combat Focus polish** — done: command rail log filters, hero drawer, slim deck, multi-target planning rows.
- **Undead / holy combat clarity** — done: cleric full-Level Attack logs,
  crushing weapon bonus logs, Turn Undead per-foe results and combat completion,
  holy water barbarian exception, Blessed Temple/Shrine expiry, foe-chip rules
  hints, disabled-state action hints, and home rules-table/reference updates.
- **Session UI polish** (in progress):
  - Done: map pan/zoom overlay pinned to viewport; wheel zoom around pointer;
    **Rm** current-room zoom and **All** visible-map fit; hero actions on party sheets;
    equipment/inventory header icons; ally bandage targeting; room panel and **exits dock
    beside the log** (scrollable when many exits); icon key as map overlay; resizable log/map, side-panel, and map-height
    splits (double-click reset, fill-remaining-space default); compact expandable session log;
    unified per-exit list with door shortcuts; top foe chip strip; party sheet accordion; **2×2 party grid**
    (container-query responsive); sticky session action bar; **Fight Round** label; exits
    default open with persisted layout prefs; **combat panel** phase steps, round plan,
    withdraw door picker; spell fail logs show roll vs target; Mass Teleport ally picker + Lifeforce amount in combat.
  - Planned:
    - Rulebook scan snippets beside structured tables (ongoing).
    - **Interaction latency pass:** add immediate pending/disabled button feedback
      for session actions; avoid full `refreshSessions()` after every
      `/api/sessions/{id}/advance` call; add lightweight session-list summary
      data for active/saved games; make `renderSession()` skip map, party-sheet,
      and setup-list rebuilds when those surfaces did not change; review
      synchronous SQLite/file work inside async FastAPI routes; ensure production
      deployments do not run Uvicorn with `--reload`.
- ~~Expert spell cast effects~~ — done (learning via L5+ fork + full cast effects).
- ~~Extend the local icon registry beyond room-state markers~~ — done for room
  states, playable class icons, monster categories, and named monster ids; item
  icons can continue to use the same registry pattern when item-specific map
  markers are introduced.
- Broader test coverage for edge cases not yet covered by table/action tests.

## Phase 3 - Adventure Manifests

Goal: play one authored adventure end to end.

- Choose `caves-of-the-kobold-slave-masters.pdf` as the first import target.
- Extract map images and text.
- Build a reviewed JSON manifest with map nodes, keyed rooms, scripted events,
  adventure-specific tables, and win/loss conditions.
- Add imported adventure session mode.
- Render the authored map in the UI.
- Extend the map editor workflow for authored maps once manifests exist.
- Add per-character square positions only where authored maps, line-of-sight,
  or variant rules require them; keep core 4AD Marching Order rules as the
  baseline combat model.

## Phase 4 - Expanded Rules and Supplements

Goal: broaden rule coverage safely.

- Treat `Four-against-the-abyss.pdf` as an expansion/supplement source.
- Add deeper dungeon rules and higher-level content after the base loop is
  stable.
- Add ruleset/theme profiles for alternate books so shared engine concepts can
  be reused while theme, tables, and allowed mechanics vary.
- Add a low-priority Settings / Rules Profile screen that can enable a coherent
  rules bundle rather than isolated one-off toggles. Candidate presets:
  - Expanded Edition only.
  - Expanded Edition + Four Against the Abyss.
  - Expanded Edition + Four Against the Abyss + Four Against the Forsaken Depths.
  The profile should gate available tables, character options, tier dice,
  expert/heroic/legendary skills, spells, economy services, and UI actions so a
  session cannot accidentally mix disabled supplement rules.
- Track a possible product rename from **Ahazi Against Darkness** to **Four
  Against Darkness**. Technically this is a small branding/configuration pass
  across the app title, API title, package text, docs, and deployment labels;
  public release naming should be reviewed separately before changing it.
- Consider AI-assisted room description generation as a reviewed authoring tool
  after ruleset/theme profiles exist.
- Add manifest validation tools.
- Add an admin/content review screen.

## Phase 5 - Quality and Deployment

- Add migration scripts for database changes.
- Extend export/import beyond characters and parties to include saved games,
  icon metadata, and optional full appdata snapshots.
- Add backup/restore guidance for Unraid.
- Add CI checks for formatting, tests, and Docker builds.
