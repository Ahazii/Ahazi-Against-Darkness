# Roadmap

## Campaign / World Builder

Status: foundation implemented; low-priority feature growth.

- The campaign layer is app-owned and is not a TAG PDF rule. TAG content can attach to it, but campaign/world ownership rules should be documented separately from printed mechanics.
- Default world records are seeded and migrated once: campaign `Norindaal`, guild `Adventurers Guild`, troupe `Troupe1`, and friendly settlement `Hearthmere`.
- Campaign Management now supports create/edit/delete campaign records, selected-campaign summaries, searchable/sortable/filterable world lists, one guild assignment per campaign, multiple troupes per campaign, multiple friendly settlements per campaign, and placeholder troublesome town records for the future Troublesome Towns supplements.
- Assignment integrity is enforced in the backend: one guild per campaign, one campaign/guild/home per troupe, one troupe per party, one party/troupe/guild per character, and automatic propagation when guilds or troupes move.
- Troupe, Guild, Party, and Settlement Management now reuse the same world-context model, with filtered management lists, assignment warnings, richer hover text, and Rules/Tables links back to the documented dashboard workflow.
- Character Management now exposes full-sheet readiness and Go Adventure setup blocks critical party/member/module/map-cap errors before creating a new session.
- Adventure completion now feeds a campaign chronicle and structured guidance tasks. Dashboard Needs Attention summarizes open tasks, closeout prompts, active sessions, roster health, and context warnings; Campaign Management shows recent chronicle entries.
- Campaign Management now has a command-center overview, guidance archive filters, safe orphan-assignment cleanup, and JSON/Markdown chronicle export. Go Adventure uses a server-side closeout gate so required guidance and unresolved TAG closeout prompts require explicit override before starting again.
- Characters are constrained to one party, one troupe, and one guild. Parties are assigned to one troupe. Assigning a character to an incompatible troupe removes them from the previous party with a user-facing alert/message.
- Priority note: campaign work is parked unless allocation/regression issues appear. The current requirement is that a campaign can hold a Guild, one or more troupes, and friendly/troublesome settlements. Hex-map editing, settlement placement, deeper campaign chronicle polish, and troublesome-town mechanics are deferred behind Modern Dashboard and TAG support.

## Modern Dashboard And TAG Support

Status: active priority.

- Release gate: deploy and complete the short `v0.39.36` campaign Rumor / two-Bag / ordinary Invisible Gremlins checklist in `docs/PLAYTEST_PLAN.md`. Once it passes, stop broad adventure regression testing; reopen only the exact failed workflow if a defect is found.
- First modularisation slice after that gate: finish extracting the repeated item-disposition eligibility checks (transfer, drop, storage, sale, sacrifice, confiscation, and random destruction) behind one reusable policy boundary. Preserve the TAG star-object prohibition, explicit Bag-container identity, and container-aware loss behavior with focused tests; do not combine this with a wider `random_dungeon.py` reorganization.
- Next TAG conversion slice: reuse `tag_scene_actions.py` for one PDF-backed scene procedure at a time, including required actor, modifiers, target, attempts, outcomes, and rewards. Bofto Scene 14 is the reference implementation. Do not build a generic prose interpreter or expose printed success/failure outcomes as player choices.
- Next dashboard work should focus on making every modern section complete enough to avoid falling back to the legacy homepage: clearer page summaries, denser lists, better hover explanations, tighter controls, and targeted rules-reference links.
- Next TAG work should focus on player-facing completeness: closeout workflows, Guild/banking/troupe/settlement actions, generated TAG adventure prompt/signoff coverage, and clearer post-adventure guidance.
- TAG-heavy modern pages now share a workflow summary and generated-adventure signoff panel; future TAG passes should deepen the underlying automation and playtest signoff rather than adding more campaign-map features.
- Dashboard and Go Adventure now have a TAG closeout checklist with action links, generated-adventure review logging, and clearer readiness state. Next TAG work should focus on playtesting the generated modules and converting more room prompts into direct TAG Actions where the PDF boundary allows it.
- Generated TAG playtest support now includes richer app-authored lead guidance, more interesting prompt prose, lead selector/status cards, and TAG log filtering. The next big TAG pass should be a module-family playthrough audit: start with Rumors, then Treasure Maps, then Thematic Dungeons, then Guild Jobs, and convert any still-manual procedure notes into safe action buttons.
- Go Adventure now uses Start, Resume, Generate, Guild Jobs, and Reference tabs. Exploration now calls the play text **Narrative** and lets the player show/hide Current Objective, Text Commands, Exits, and Character Sheets. Continue polishing toward an app-style shell, but avoid building a complex floating-window system until the docked controls are fully playtested.
- The PDF boundary remains: app workflow guidance can be expanded freely, but exact printed text should stay in Rules Reference links or source-page references unless explicitly signed off.
- Imported adventure package diagnostics now compare candidate states and terrain types with the State Registry and Terrain Registry as review-only hints. Future PDF package work should keep this boundary: diagnostics can guide review, but loaders should not promote imported rules, states, or terrain into active play until a trusted implementation explicitly owns that behavior.

## Dashboard Artwork And Help

Status: dashboard support implemented; asset population is local/licensing-dependent.

- Rules artwork is tracked in `data/rules/artwork_registry.json` and displayed on relevant modern dashboard pages, Rules Reference entries, and Tables rows.
- Generated or extracted PDF artwork belongs under `DATA_DIR/assets/rules_art/local/` unless a publishing agreement allows it to be committed.
- Manual player-provided adventure/scene artwork placeholders live under `DATA_DIR/assets/artwork/user/`. Replace the dimension-labelled text files locally with licensed or personal-use PNG/JPG/GIF/WebP art.
- Modern dashboard page artwork placeholders live under `DATA_DIR/assets/Application Artwork/` and are surfaced by the Developer Artwork Manager.
- `/assets/<path>` now resolves from `DATA_DIR/assets` first, then bundled app assets. Bundled defaults can stay in the container; user-facing art/icons/tiles/module assets should be placed beside `game.db`.
- Application artwork now has a planned expansion list in `docs/ARTWORK_IDEAS.md`: character portraits, module cover art, settlement record images, Adventures Guild lead-family art, exploration objective art, and small state art for bank/trove/robbery/inheritance/loan records.
- Next artwork work: choose exact crops per PDF section, add `crop_pct` bounds where useful, render with `tools/extract_rules_artwork.py`, then review each slot visually before deciding whether any image can be distributed. Separately, add app-owned/user-supplied artwork slots from `docs/ARTWORK_IDEAS.md` only where the image helps scanning or play decisions.

## Phase 1 - Clean Foundation

Status: substantially complete; retained for foundation maintenance.

- Replace prototype code with FastAPI + SQLite foundation.
- Preserve local PDFs and tile assets.
- Add documentation and content pipeline.
- Add character pool, exact four-character parties, and starter random sessions.
- Add a structured placeholder map element definition file.
- Add first-pass map element rotation and metadata editing.
- Add smoke tests and deployment verification.

## Phase 2 - Faithful Random Dungeon MVP

Goal: one complete legal level-1 random dungeon loop.

Status: advanced — core loop and broad EE table coverage are playable; manual
validation and selected fidelity/UI work continue.

Top priority:

- **Rules PDF compliance: one-table-at-a-time audit.** Work through the exposed
  home Rules tables one table at a time, starting with core tables. For each
  table, record the PDF file/page, current row text, expected status per row
  (`verified`, `recently fixed`, `partial`, `suspect`, `not implemented`),
  then patch only that table's data/engine/UI/tests after the row is checked.
  **`treasure_table` (EE p.157) + `dungeon_magic_treasure_table` (p.158):** table
  rows verified against PDF; engine fix for fungal grottoes Rare Mushroom vs Rare
  Item routing (rolls 2–5 choices + roll 3 bark/mushroom fork).
  **`hidden_treasure_table` (EE p.108):** rows verified; engine fixes for
  complication-before-gold roll order, halfling Luck reroll on complication,
  deferred complication on claim, and ghost banish log messaging.
  **`search_table` + `wandering_monsters_table` (EE p.107):** rows verified;
  engine fixes for backtrack wandering on d6 1–2, table result log text, and
  halfling/pole search rerolls clearing a pending reward choice.
  **`room_content_table` (EE p.152):** rows verified; `_roll_content` driven by
  table lookup for all corridor/room splits; fungal roll-5 auto secret passage
  and roll-9 2-Clue choice covered by tests; foray reset clears pending tile
  content choice. Next target: **`door_table` (EE p.109)**: rows verified; 2d6 door
  types, levels, treasure bonus (+1 sealed/iron), clue/spell/gadget paths, trap
  doors, and entry treasure bonus covered by tests; iron lock-picks now receive
  good-lockpick bonus. **`dungeon_special_features_table` (EE p.153)**: rows verified;
  fountain heals only PCs who lost Life on the first fountain per adventure; Blessed
  Temple is player-chosen and breaks curses;   Living Statue carries spell immunity;
  statue and puzzle box remain pending choices. **`dungeon_special_events_table` (EE p.154)**:
  rows verified; ghost fear saves, special-event wandering table (1–3 vermin / 4 minions /
  5 weird / 6 boss), Lady in White quest gating, trap on repeat healer/alchemist/refused lady.
  **`caverns_special_features_table` (EE p.112)** and **`caverns_water_pool_table`**: rows
  verified; stalactites/stalagmites/boulders/echo combat hooks and water-pool dip UI;
  contamination applies -1 to all Saves until Blessing or Healing prayer cleanses it;
  refreshing heal once per hero per adventure. **`caverns_special_events_table` (EE p.155)**:
  scout/morlock payments, cavemen feed/fight, dwarf gem seam, dwarf miner d6 gem stock
  and next-tile reveal on trade, cavern trap routing covered by tests.
  **`fungal_grottoes_special_events_table` (EE p.156):** rows verified; halfling
  scout paid no-surprise/+1 Saves, fungal cavemen feed/fight/passage, spore-cloud
  event saves (monk immune; halfling/barbarian +L), trap-then-rare-item auto-resolve,
  mycelial warning ignore-next-trap/wander, fungal merchant +20% buys (including
  weapon services with target weapon), repeat merchant → halfling scout reroute.
  **`fungal_grottoes_rare_mushroom_table` (EE p.159):** rows verified; all six
  mushrooms wired with PDF resale/use rules, Puffball partial flee (mushroom/artificial
  foes still strike), Healer's Chanterelle expires unused at adventure end.
  **`fungal_grottoes_rare_item_table` (EE p.161):** rows verified; gem/leafsteel choice,
  Xicthul's Cap throw, Red Death choice, adventurer dead-body loot, d6 White Angel basket,
  Morel Crusher morale at −1 plus foe Morale modifier; trap-then-rare-item event staging.
  **`fungal_grottoes_trap_table` (EE p.166):** rows verified; sleep spores random-then-all
  with immunities and party wipe, spore cloud poison follow-up, slime patch prone skip when
  wanderers arrive, mycelium snare player-held-object choice UI, shrieking mushroom forester/druid chance mods,
  cordyceps infection attack plus undead boss rise; PDF save bonuses (+L / +½L).
  **`caverns_special_item_table` (EE p.160):** rows verified; 3d6+3 gemstone gold on roll,
  Glittering Crystal auto-equip, map fragment preview + 30gp caverns bribe value, adventurer
  dead-body choice (incl. chicken blood), Miners' Ointment and Amulet wired.
  **`trap_table` (EE p.164):** rows verified; dart random defense, poison gas all-PC poison
  saves (+L barbarian/halfling), trapdoor/bear trap lead saves with wound penalties,
  spears two-random defense, falling stone position-4 defense without shield bonus.
  **`caverns_trap_table` (EE p.165):** rows verified; stalactite/rockslide saves,
  hidden pit climb + optional 1-Clue passage (dungeon/fungal only), swinging log
  marching-order chain, toxic mushrooms (mushroom-class immunity, forester +L),
  rolling boulder front/back + blocked exit; `tests/test_caverns_trap_table.py`.
  **`dungeon monster tables` (EE p.167–170):** rows verified; vermin/minions/weird/boss
  stat, reaction, immunity, and special-effect fields locked in
  `tests/test_pdf_table_compliance.py` (four detail tests + name-order test).
  Next target: **TAG generated-adventure playtest signoff**, especially contextual scene prompts, branch/reward accuracy against the PDF, and module-import groundwork for PDF-authored adventures.

Completed or starter-complete:

- Doors as explicit state (Open Door flow, entry inheritance).
- Room content, search, wandering monsters, traps, treasure, special events.
- Core combat, saves, reactions, morale, fleeing, death, blade poison, poison foes, magic resistance, missile combat, weapon-type modifiers.
- XP systems (four variants), gold, potions, Final Boss, quests and Epic Rewards.
- Quest journal and map-marker turn-in status for Lady in White quests.
- Home-screen rule tables (all `dungeon_tables.json` keys) plus monster bestiary.
- Searchable rules reference (`rulebook_reference.json`) on home screen.
- Rulebook Rest (EE p.114) and Tier 1 class abilities (rage, Luck, Panache, paladin prayer).
- Tier 1–4 class tricks wired (`class_tricks_implementation_table`, including kukla rings/compartment); EE ability flags used by the shared expert/ability UI are separated in `ee_class_trick_flags_table`.
- Class profile audit (EE p.24–69): Life, wealth, starting gear; `tools/audit_class_profiles.py`.
- Inventory carry limits, default weapons, session-to-roster persistence on clean exit.
- Home equipment shop (EE pp.81-88 buy list / listed resale rules) and weapon-default dialogs.
- Generated/custom icon registry for room states, playable classes, monster
  categories, and named monsters; Icon Editor can assign art for each row.
- Dice trace on exploration and many combat actions.
- Tests for tables, combat modifiers, weapons, exploration, economy, reactions, spells,
  carry limits, equipment, equipment shop, session persist, door sync.

Still open:

- ~~Tier 1–4 class tricks~~ — done (see `class_tricks_implementation_table`, including kukla rings/compartment, plus separated `ee_class_trick_flags_table`).
- ~~Expand Luck reroll hooks (defense, saves, treasure, search)~~ — done (hero drawer + party sheet).
- ~~Named save labels~~ — done (user labels on save; `sessionDisplayTitle()` in UI).
- ~~Expert spell cast effects~~ — done (6 Abyss spells + combat/exploration UI for Mass Teleport / Lifeforce).
- ~~Epic Reward follow-up~~ — Arrow of Slaying targeted combat item and Book of
  Skalitos scroll-page bundle wired.
- ~~Combat round summary~~ — one-line recap appended after each Fight Round.
- ~~Mushroom consumables, lantern oil & acid vial in shop~~ — rare mushrooms use p.159 timing/effects; shop sells oil and acid.
- ~~Druid animal companion~~ — auto-summon on wilderness entry (1 Food ration).
- ~~Druid Call of the Wild~~ — L10+ forced split countdown using detached-party model.
- ~~Replace placeholder `tiles.json` rows with exact starting (`01-06`) and
  generated (`11-66`) map element metadata.~~ — done; all 42 manually validated.
- ~~Validate map element footprints and multiple exits through the visual metadata
  editor and `tools/validate_tiles.py` / `GET /api/rules/tiles/validation`.~~ —
  done; exits are placed on grid squares (not necessarily the outer footprint border).
- ~~Continue validating walkable-space placement and truncation against more
  rulebook examples, especially cases where other exits would be covered.~~ —
  done for the 42 catalog map elements; truncation regression tests remain.
- ~~Placement no-hard-stop fallback~~ — done: failed generated elements reroll
  through remaining valid keys; a 1x1 dead end is drawn only if every candidate
  fails.
- ~~Add optional fixed paper size~~ — done: unlimited (default) or 20×28 at session start.
- ~~Caverns/fungal grottoes table variants~~ — starter tables wired; validate row text against PDF.
- ~~**Clue economy cleanup:**~~ done — Search reward choices, per-hero held Clues,
  3-Clue Secret/XP reveal, Trade Information scoping, spell learning (3 Clues),
  illusion/lever door spends, captive hideout (3 Clues), Kerrak Dar Epic Reward
  hoard (`claim_kerrak_dar_hoard`), and all p.123 Secret hooks wired.
  Regression: `tests/test_clue_spends_table.py`, `tests/test_secrets_reactions_table_family.py`,
  `tests/test_capture.py`, `tests/test_quests.py`.
- Refine visual truncation beyond cell clipping if later rules require more
  precise pixel/vector masks.
- Add paint-mask or arbitrary polygon mask authoring if the per-square
  shallow-slope, two-square long-slope, and curved-corner masks are not precise
  enough for circular rooms or later line-of-sight needs.
- ~~Per-foe reaction tables / MR tier display~~ — 116 named reaction tables (265 rows) plus category fallbacks; every indexed `monsters.json` row resolves through its own d6 table. Foe chips show stacked MR tiers. **Reactions polish completed 2026-06-17:** special-bribe per-item UI, Wraith magic-item bribe, Dwarf Miser, scout special-bribe parity, sleep `attack_bonus_first_round`, gem counted value; `tests/test_special_bribe_reactions.py` table-driven matrix. `tests/test_bestiary_coverage.py` guards reaction-table signatures.
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
- **Quest gameplay polish** — done: Quest progress logs, wrong-outcome
  bring-head/bring-alive feedback, and Ongoing Quests disabled turn-in reasons.
- **Environment table compliance repair** — done: Caverns/Fungal special events,
  special items, rare items, and traps now match the owned EE p.155-161 PDF rows;
  tests guard against placeholder drift. Detailed environment traps and the
  choice-heavy cavemen/scout/miner/merchant/mycelial-warning rows now have
  dedicated map UI and regression coverage.
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
    **Interaction latency pass (2026-06-24):** pending/disabled button feedback on session
    actions; `/advance` updates cached session without full list refresh; `GET /api/sessions/summaries`
    for Home active/saved lists; map/icon-key/log render cache; deferred setup roster rebuild
    while in game view (`syncSessionListFromSession`, `markSetupRosterDirty`).
  - Planned:
    - Rulebook scan snippets beside structured tables (ongoing).
    - Review synchronous SQLite/file work inside async FastAPI routes; ensure production
      deployments do not run Uvicorn with `--reload`.
- ~~Expert spell cast effects~~ — done (learning via L5+ fork + full cast effects).
- ~~Extend the local icon registry beyond room-state markers~~ — done for room
  states, playable class icons, monster categories, and named monster ids; item
  icons can continue to use the same registry pattern when item-specific map
  markers are introduced.
- Broader test coverage for edge cases not yet covered by table/action tests.

## Phase 3 - Adventure Manifests

Goal: play **authored adventures** end to end — both **AI-generated modules** and
**PDF-extracted** modules using one shared manifest format.

**Specification (read first):** [`docs/AI_ADVENTURE_MODE.md`](AI_ADVENTURE_MODE.md)

### 3A — AI Adventure mode (player-authored content)

External LLM generates narrative + layout; the engine owns all mechanics.

- [x] Product spec, manifest schema draft, example module (`data/adventures/`)
- [x] `validate_adventure_manifest()` + `tests/test_adventure_manifest.py` + CLI
- [x] `tools/export_adventure_allowlists.py` → `data/adventures/allowlists.json` (snapshot; runtime uses `build_adventure_allowlists` from live rules)
- [x] Live allowlist sync: prompt builder and validator share `RulesRepository`; `GET /api/adventures/allowlists`
- [x] Setup UI: parameters form + **copy prompt** (no in-app LLM in v1)
- [x] Import UI: paste/upload JSON → validate → preview → install
- [x] `create_session_from_manifest()` — full room graph at session start, no procedural growth
- [x] Triggers: `on_enter`, `on_search`, `on_treasure`, `on_feature`
- [x] Quest + victory: quest complete **and** leave via `exit_room_id` → roster sync
- [x] Saved games / in-progress label shows **AI Adventure** for imported sessions
- [x] Export single `.json` package (`GET /api/adventures/{id}/export`) and `.zip` with assets; Setup UI exposes both

**Locked v1 decisions:** open branching graph; fog of war until visited; movement
only via manifest exits; 4AD allowlists only; environments
`dungeon` / `caverns` / `fungal_grottoes`; no overland.

### 3B — PDF-authored adventures (reviewed extraction)

- Choose `caves-of-the-kobold-slave-masters.pdf` as the first import target.
- Extract map images and text.
- Build a reviewed JSON manifest (same schema as 3A; `source.type: "pdf"`).
- See [`docs/CONTENT_PIPELINE.md`](CONTENT_PIPELINE.md) for the extraction workflow.

### 3C — Engine and UI (shared)

- [x] Imported adventure session mode (`POST /api/sessions` from installed manifest).
- [x] Authored map in UI with fog of war (`visited_tile_ids`; tile art from `tiles.json`).
- [ ] Extend the map editor workflow for authored maps once manifests exist.
- Add per-character square positions only where authored maps, line-of-sight,
  or variant rules require them; keep core 4AD Marching Order rules as the
  baseline combat model.

## Phase 4 - Expanded Rules and Supplements

Goal: broaden rule coverage safely.

- Use [`MASTER_RULE_COVERAGE.md`](MASTER_RULE_COVERAGE.md) as the program-level
  source of truth for EE, Four Against the Abyss, Four Against the Forsaken
  Depths, Tales from the Adventurers' Guild, and Four Against the Netherworld.
- Plan a shared **ruleset package** architecture after the PDF adventure package
  workflow is stable. Core 4AD, Expanded Edition, Abyss, and later supplements
  should gradually move toward the same inspectable content shape used by
  imported adventures: tables, foes, items, classes, states, trackers, and
  allowlisted procedures. This is a migration direction, not a big-bang rewrite:
  start with read-only package viewers and one small table family, then prove
  tests and behavior are unchanged before converting more content.
- Keep a clear boundary between package data and engine mechanics. Monster
  tables, treasure lists, item catalogs, class records, state flags, and numeric
  trackers are good ruleset-package candidates. Rules that alter combat flow,
  advancement, map generation, reactions, or session lifecycle should become
  named engine hooks with declarative configuration only where the PDF rule can
  be represented cleanly.
- Complete the whole-book Abyss audit. The profile, dedicated procedural
  runtime, exact trap/feature/event pass, reaction routing, tactical
  leader-lock/multiple-boss/horde targeting, and core item use-actions are now
  started; diseases/transformations and campaign plots remain before treating
  Abyss as complete.
- Complete Forsaken Depths tile metadata, then add its dungeon/river runtime and
  remaining spells, encounters, items, tables, Citadels, ruins and Secrets.
- Build Adventurers' Guild as the reusable campaign/downtime layer: settlement,
  troupe, passage-of-time, availability, Streetwise, storage and jobs.
- Build Netherworld only after ruleset profiles and reusable overland/hex
  navigation exist; do not encode it as scattered exceptions in the EE dungeon
  engine.
- Treat every PDF in `Rules/` as an approved source of truth, including
  Four Against the Abyss, Four Against the Forsaken Depths, Fortress of the
  Warlord.
- Defer Fortress of the Warlord as mainly an authored adventure, but keep its
  outdoor rules on the plan. Its wilderness/hex-map material should be handled
  by a future outdoor map/navigation layer before Fortress-specific adventure
  content is made playable.
- Add deeper dungeon rules and higher-level content after the base loop is
  stable.
- Add ruleset/theme profiles before implementing the remaining full-book
  supplements. Profiles must gate available tables, character options, tier
  dice, skills, spells, economy services, and UI actions so a session cannot
  accidentally mix disabled supplement rules.
- **Ruleset profiles (2026-06-24):** `data/rules/ruleset_profiles.json`, `GET /api/rules/profiles`, session `ruleset_profile_id`, TCOTFD class gating via `source_books`, home profile dropdown.
- **File-backed supplement registry (2026-07-07):** Built-in supplement metadata now lives in `data/supplements/<supplement_id>/supplement.json`, `/api/supplements` reports manifest origins and diagnostics, and `DATA_DIR/Supplements/` is created for future local reviewed supplements without changing current rules loaders.
- **Supplement manifest validation (2026-07-07):** Supplement metadata now has `data/supplements/schema/supplement_manifest.v1.json` plus app runtime validation, so packaged/local manifests fail into diagnostics instead of silently becoming bad session options.
- **Supplement dependency/conflict validation (2026-07-07):** Registry diagnostics now flag unknown references and asymmetric conflicts; Settings, Go Adventure, and backend validation prevent conflicting supplement snapshots while preserving dependency auto-add.
- **Supplement reference filtering (2026-07-07):** Rules Reference and Tables List now have Supplement filters, Enabled defaults filtering, and inferred supplement badges so players can navigate reference material by active/default book context without changing mechanics.
- **State Registry navigation (2026-07-07):** Settings now exposes State Registry search, family/scope/supplement/review filters, source supplement badges, highlighted matches, and expanded legacy mapping values for future state-instance migration.
- **Terrain Registry navigation (2026-07-07):** Settings now exposes Terrain Registry search, kind/supplement/review/interaction filters, source supplement badges, highlighted matches, and expanded legacy mapping values for future terrain-instance migration.
- **Active registry context (2026-07-08):** Adventure View room details now include a visible Registry Context block plus status-chip and Play Context hovers, so playtesters can see State/Terrain Registry source, scope, and migration context without changing current mechanics.
- **Party Sheet state context (2026-07-08):** Party Sheet summaries and expanded hero sheets now surface whether visible effects map to State Registry rows, keeping state discovery in the normal play surface while legacy save fields remain authoritative.
- **Narrative report registry context (2026-07-08):** Copy Narrative Report now records terrain registry matches, active state registry matches, and visible party effect chips in Debug Context, preserving exact player Narrative while improving playtest reproduction.
- **Registry resolver helpers (2026-07-08):** Backend State and Terrain Registry modules now have read-only matching helpers plus diagnostic resolver APIs for legacy status labels and terrain context, giving future supplement loaders a tested reuse point before state-instance mutation exists.
- **Settings collapsible panels (2026-07-08):** Settings / Options now treats major settings and registry areas as collapsed-by-default sections, keeping dense supplement/state/terrain tooling scannable while preserving the same explicit save actions.
- **Reference/table collapsed navigation (2026-07-08):** Rules Reference and Tables List now follow the same collapsed-by-default section pattern, with trimmed search input so trailing spaces do not erase matches.
- **TAG Guild Job playthrough audit (2026-07-08):** Guild Jobs now have the same generated-lead audit/signoff surface as Rumors, Treasure Maps, and Thematic Dungeons, including manifest audit metadata, Go Adventure panels, Tables, and Rules Reference entries.
- **Go Adventure collapsed panels (2026-07-08):** Start, Resume, and Reference / Playtest panels now default collapsed, with generated lead audit rows collapsed inside the panels to keep review-heavy pages scannable.
- **Supplement session snapshot (2026-07-07):** Settings stores the default enabled supplement IDs, and Go Adventure now shows per-session supplement checkboxes before session start. New sessions lock the validated `active_supplement_ids` list while legacy ruleset profiles continue to drive the random-generation mechanics during migration; supplement-only random starts infer the matching legacy profile when one is not sent explicitly.
- **Adventure package supplement vocabulary (2026-07-07):** `adventure_package.v1.json` and package diagnostics now accept supplement-shaped capabilities for locations, room tiles, terrain types, generators, campaign state, and narrative while keeping imported PDF data declarative and review-only.
- **FD Heroic spells (2026-06-24):** PDF-accurate 6-spell d6 table in `heroic_spells.json`; full cast resolver in `forsaken_depths_heroic_spells.py` wired through `resolve_spell_cast`, river hazards, combat bonuses, scroll rewards, and Cyclopean Idol bas-relief.
- **Abyss runtime pass (2026-06-28):** `abyss` ruleset profile, Abyss 2d6 room-content routing, monster subtables, claimable treasure payloads, unique/event summaries, and Abyss wandering spawns are implemented and tested.
- **Abyss phase 1 exact effects (2026-06-28):** Abyss traps, special features, unique events, Enchanted Banquet, Useful Stuff, and magical-defense item rows are exposed and wired through trap/feature/treasure UI.
- **Abyss phase 2 tactical reactions (2026-06-28):** Abyss minion reaction tables from p.53 are wired, including exact bribe amounts, Flying Skull fight-to-the-death fallback, Trial of Champions champion picker UI, and tagged minion leaders as Trial champions.
- **Abyss phase 3 tactical targeting (2026-06-28):** Abyss minion leaders enforce corridor/room leader-lock targeting, combat target selectors disable illegal choices with hover hints, multiple-boss rooms spread unset party targets and apply the lone-hero secondary-boss Defense penalty, and tagged hordes multiply attacks by living characters.
- **Abyss item actions (2026-06-28):** Party-sheet use buttons and engine actions are wired for Elven Bread, Blessed Horseshoe, Parchment of Banishing, Medallion of Snake Charming, Philter of Fire Breathing, Ring of Three Wishes, and passive Abyss armor/weapon/defense items.
- **Abyss afflictions (2026-06-28):** Dark Plague uses L10 saves, room-entry d8 harm, room-by-room spread, Blessing/Elven Bread cures, and adventure immunity; lycanthropy resolves werewolf wound exposure at encounter end, drops silver/lantern gear, offers 400gp monastery treatment from camp, and transforms Madness-over-Level heroes into werewolf foes; vampire level-drain death blocks ordinary resurrection pending sire destruction.
- **Abyss campaign plots (2026-06-28):** Assassination, Rebellion, Entity, Invasion, Kidnap, and Enchantment have persistent playable plot state, setup/room-panel UI, finale triggers, vampire sire hunt/re-encounter, one Entity artefact piece per dungeon, and large-room Dragon Lair routing.
- **TAG campaign shell (2026-06-24):** `CampaignState`, `GET/PUT /api/campaign`, `days_passed` on adventure complete, TAG banking toggle on session start.
- **FD/TAG rules pass (2026-06-28):** Teleport Enemy return tracking with occupied-room reaction rolls, Mass Blessing target/condition UI including hirelings, and TAG Settlement Apothecary brew panel/action are implemented and tested.
- **TAG campaign downtime phase (2026-06-28):** troupe name/active-party/guild-coffer state, settlement storage, fixed service purchases, PP tracking, magic locker creation/summoning, Gambling House gp outcomes, Streetwise rumors/interrogation/Look Tough, and treasure-map follow summaries are implemented with home-panel UI and hover hints.
- **TAG adventure lead phase (2026-06-28):** Rumor Scenes, Treasure Map leads, Thematic Dungeons, and Guild Jobs can be converted from the TAG settlement panel into normal installed adventure modules under the existing Adventure section/dropdown.
- **TAG route/XP/action phase (2026-06-29):** TAG Actions now handles exact route markers, Clue gates, printed scene rewards, XP markers/awards, per-character bank ledgers, safe generated-module route rewrites, Guild marker clearing, Speedy Recovery settlement-healing markers, Look Tough Streetwise bonus consumption, and Wizard's Luck Gambling House handling with hover-hinted UI. The TAG guide and player-actionable checking docs live under `docs/Checking/`. Next TAG targets are broader playtest signoff.
- **TAG Guild/Finance workflow phase (2026-06-29):** Modern Guild and Banking pages now expose separate Guild membership/coffers, finance, jobs/member ledger, bank ledger, hidden-trove, robbed-account, closeout, and recent-log surfaces. Bank robbery risk marks the selected account robbed; 3-Clue recovery clears it and creates the Bandit Hideout lead. The exploration TAG Actions dialog includes workflow guidance and routes robbery recovery through the full lead-creation action.
- **TAG Rumor playthrough audit phase (2026-06-30):** All twelve generated Rumor leads now carry app-owned scene guidance, prompt checklists, and route/reward/XP closeout reminders. Go Adventure has dedicated Rumor audit/signoff panels and Tables/Rules Reference entries.
- **TAG Treasure Map playthrough audit phase (2026-06-30):** All six generated Treasure Map destinations now carry app-owned destination guidance, prompt checklists, procedure/reward/storage closeout reminders, dedicated Go Adventure map audit/signoff panels, and Tables/Rules Reference entries.
- **TAG Thematic Dungeon playthrough audit phase (2026-06-30):** Ghastly Mine, Giant's Lair, Dragon's Lair, Fiendish Abyss, Minotaur Maze, and Bandit Hideout now carry app-owned theme guidance, prompt checklists, procedure/reward/storage closeout reminders, dedicated Go Adventure theme audit/signoff panels, and Tables/Rules Reference entries. Next large TAG chunk should apply the same audit depth to Guild Jobs.
- **Courtship of Flower Demons — planned sequence:**
  1. ~~Small courtship gaps~~ — virile might +1 breeding saves, Flower Portal water-adjacent validation, rulebook status (done).
  2. ~~**Apothecary Cookbook (medium scope)**~~ — TCOTFD appendix recipes, brew-between-encounters UI, difficulty rolls, Wandering Alchemist gating, Karmic Calcinator duration doubling, portable brewed items (done).
  3. ~~**TCOTFD class pass**~~ — Wandering Alchemist, Satyr, Conservationist, and cross-book cambion/succubus/demonologist hooks; satyr outdoor seduce/treasure/exhaustion, halfling Lucky Wooers, Conservationist vow→BoS 16, Flower Portal innate once/adventure (scrolls unlimited), satyr innate Blossoms, Expert Surgeon/Herbalist/Poison Expert training, Wandering Alchemist L1 expert skills and halfling-skill expansion at Expert tier (done).
  4. ~~**FD treasure on monsters**, citadel auto-gen, and river edge cases~~ (done).
  5. ~~**Lex opposition, alchemist expert skills, FD tile validation, apothecary camp/forage**~~ (done 2026-06-24).
  6. ~~**TCOTFD polish**~~ — Lex sleep-on-hit and insect-fear combat; BoS entries 2/5/6/7; soul-tax Meadows reroll (done 2026-06-24).
  7. ~~**TAG settlement apothecary**~~ — separate town/village downtime panel and `tag_settlement_brew_apothecary` action wired (done 2026-06-28).
- **Apothecary Cookbook — broad scope:** camp brewing and outdoor Norindaal foraging wired (2026-06-24); TAG settlement brewing wired separately from camp outside the dungeon (2026-06-28).
- Track a possible product rename from **Ahazi Against Darkness** to **Four
  Against Darkness**. Technically this is a small branding/configuration pass
  across the app title, API title, package text, docs, and deployment labels;
  public release naming should be reviewed separately before changing it.
- Consider AI-assisted room description generation as a reviewed authoring tool
  after ruleset/theme profiles exist. **AI Adventure mode** (full branching dungeons
  from external LLM JSON) is specified separately in [`docs/AI_ADVENTURE_MODE.md`](AI_ADVENTURE_MODE.md)
  and tracked under Roadmap Phase 3A.
- Add manifest validation tools.
- Add an admin/content review screen.

## Phase 5 - Quality and Deployment

- Add migration scripts for database changes.
- Extend export/import beyond characters and parties to include saved games,
  icon metadata, and optional full appdata snapshots.
- Add backup/restore guidance for Unraid.
- Add CI checks for formatting, tests, and Docker builds.
