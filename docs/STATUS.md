# Current Status

Last updated: 2026-07-01

## Summary

The project is a FastAPI + SQLite random dungeon with a browser UI, structured
rule tables, visual map element editor, an advanced Expanded Edition procedural
loop, and partial Abyss and Forsaken Depths layers.

### Validation status (June/July 2026)

- **User-facing assets migration pass (2026-07-01):** Runtime user assets now live beside `game.db` under `DATA_DIR/assets`. The `/assets/...` route first serves `DATA_DIR/assets` and then falls back to bundled `/app/assets`, so user artwork/icons/tiles/module assets can be backed up from the appdata share while built-in defaults remain packaged. Installed/generated adventures continue to live under `DATA_DIR/Adventures`, and server-side adventure deletion remains blocked for in-progress sessions.
- **Go Adventure declutter pass (2026-07-01):** Start now shows a compact ready status and keeps Setup Check / Closeout Gate details hidden unless the selected party/adventure has warnings or blocks. The TAG Workflow Summary moved into Generate. The old numeric Generate Detail field is replaced by a **Random** checkbox: checked means the app randomly chooses both TAG lead family and result; unchecked means the selected Lead Type controls the family and the app rolls that family's result.
- **Exploration/Troupe follow-up pass (2026-07-01):** Exploration helper panels now default off, with **Ongoing Quests** added beside Current Objective, Text Commands, Exits, and Character Sheets. The right-side immediate-control column is now labelled **Action Rail** in markup. Modern Troupe Management folds the member list into the top troupe card and shows the selected member's full sheet on the right, removing the duplicate member-list card.
- **Exploration Narrative / Go Adventure tab pass (2026-07-01):** The live adventure Log is now labelled **Narrative** in exploration and combat focus. Exploration header controls can show/hide Current Objective, Text Commands, Exits, and Character Sheets to make the map and Narrative less cramped. Go Adventure is split into Start, Resume, Generate, Guild Jobs, and Reference tabs. Ongoing Quest cards now derive titles/sources from TAG/imported module context instead of labelling every imported quest as Lady in White. Underground Caves completion records the route automatically when the target-room Boss is defeated. Tables now includes `go_adventure_tabbed_workflow_table`, `exploration_narrative_layout_table`, and `user_artwork_placeholders_table`. Manual artwork placeholders are seeded to `DATA_DIR/assets/artwork/user/`.
- **TAG Treasure Map clarity pass (2026-06-30):** Generated Treasure Map modules now separate ordinary room treasure from Map Leads To destination procedure guidance. Underground caves prompts are labelled as room-target automation, side-room logs explain when to use Claim Treasure, the modern Treasure Map audit panel includes current-room treasure guidance, and Rules Reference/Tables wording documents the split.
- **TAG resumed Treasure Map compatibility pass (2026-06-30):** Older generated Treasure Map manifests and resumed session logs now translate legacy `Apply The Map Leads To...` notes into player-facing guidance. TAG Actions workflow text now starts with the Claim Treasure vs TAG procedure split, makes character selection optional for map procedure rolls, and names the Underground caves room-target branch directly.
- **TAG direct procedure prompt pass (2026-06-30):** Exploration TAG prompt rows now run safe procedure branches directly, so Underground caves room target and similar table/count rolls no longer require opening TAG Actions, choosing a character, selecting Branch, and finding a second run button. The TAG Actions dialog remains available for edits/character-specific choices and can be dragged away from the log.
- **TAG treasure-map quest procedure pass (2026-06-30):** Lady in White / active-quest Treasure Map procedures now get the same direct-run treatment as generated TAG prompt panels. Ongoing Quest cards detect TAG treasure-map Underground caves text, show **Run Underground caves room target**, and record the d6+3 result in the live session log as well as the TAG campaign log.
- **Priority update (2026-06-30):** Campaign/world-builder work is now low priority after the allocation foundation: campaigns can own a Guild, troupes, and settlements, with troublesome towns kept as placeholders. Near-term work should move back to Modern Dashboard completion and TAG support/signoff rather than hex-map or deeper campaign-map features.
- **TAG Thematic Dungeon playthrough audit pass (2026-06-30):** All six generated TAG Thematic Dungeon modules now carry app-authored theme focus, entry/complication/finale guidance, prompt checklists, and target-room/procedure closeout reminders. Go Adventure now adds dedicated TAG Thematic Dungeon Leads and Thematic Dungeon Signoff Checklist panels with direct Rules Reference/Table links, while exploration prompts show theme checklists beside room-aware TAG Action buttons. Tables now includes `tag_thematic_dungeon_playthrough_audit_table`.
- **TAG Treasure Map playthrough audit pass (2026-06-30):** All six generated TAG Treasure Map destination modules now carry app-authored destination focus, entry/complication/finale guidance, prompt checklists, and reward/storage closeout reminders. Go Adventure now adds dedicated TAG Treasure Map Leads and Treasure Map Signoff Checklist panels with direct Rules Reference/Table links, while exploration prompts show destination checklists beside room-aware TAG Action buttons. Tables now includes `tag_treasure_map_playthrough_audit_table`.
- **TAG Treasure Map active quest tracker (2026-06-30):** Lady in White Treasure Map quests now persist destination procedure state in the live session, show a destination-aware Ongoing Quest checklist, explain what each procedure button does, mark completed procedure rows, display stored room targets, and keep ordinary `Claim Treasure` separate from the `Map Leads To` destination work.
- **TAG Treasure Map objective/signoff pass (2026-06-30):** Exploration now shows a Current Objective banner that prioritizes combat, traps, ordinary room treasure, Treasure Map procedure actions, destination signoff, and reward claim. Treasure Map quest procedures can auto-complete only for closeout-level safe paths or be manually signed off after PDF/player confirmation; TAG Actions now adds context notes and dynamic Amount labels for map procedures.
- **TAG generated-lead objective/signoff pass (2026-06-30):** Rumor, Thematic Dungeon, Guild Job, and generated Treasure Map modules now feed the Current Objective banner from current-room prompt metadata. TAG Actions shows a Relevant Now shortcut panel for the current generated room, generated lead closeout signoff is stored on the active quest, and reusable generated-room prose was strengthened for entry, side clue, complication, finale, unlocked scene, and return-road closeout.
- **TAG Rumor playthrough audit pass (2026-06-30):** All twelve generated TAG Rumor modules now carry app-authored playthrough focus, entry/complication/finale guidance, prompt checklists, and signoff reminders. Go Adventure now adds dedicated TAG Rumor Leads and Rumor Signoff Checklist panels with direct Rules Reference/Table links, while exploration prompts show the checklist beside room-aware TAG Action buttons. Tables now includes `tag_rumor_playthrough_audit_table`.
- **TAG generated prompt playtest pass (2026-06-30):** Generated TAG modules now carry app-authored scene tone and "how to use this lead" guidance in room prompt metadata. Exploration TAG scene prompts display that guidance above room-aware action buttons, while Go Adventure now has a Generated TAG Leads panel with lead type/detail/prompt counts/signoff state and a filterable TAG Action Log for route, XP, finance, Guild, branch, generated-lead, and signoff review. Tables now includes `tag_generated_prompt_playtest_table`.
- **TAG Underground caves automation pass (2026-06-30):** Lady in White Treasure Map Underground caves now automates the d6+3 target after the target is recorded: the engine counts explored rooms, turns the target room into the Treasure Map final Boss room with +2 Life, dead-ends unopened exits there, and marks the objective complete when that Boss is defeated.
- **Generated TAG lifecycle polish pass (2026-06-30):** Live generated TAG sessions now show an Entry/Side lead/Complication/Finale/Route/Reward/XP/Closeout lifecycle strip in the Current Objective banner, TAG Actions now names the recommended current-room shortcut and explains why it matters, and Ongoing Quests includes a generated TAG closeout panel with route, pending XP, guidance, closeout, and one-click signoff review. Backend signoff now stores warnings for unresolved route, XP, guidance, or closeout work instead of silently treating the lead as clean.
- **Generated TAG director/wizard pass (2026-06-30):** Generated TAG play now adds a phase-aware Director panel to room prompts, Current Objective, TAG Actions Relevant Now, and generated quest closeout. The director gives lead-type playbooks for Rumor, Treasure Map, Thematic Dungeon, and Guild Job leads, focuses current-room action buttons by action family, and turns closeout into a five-step wizard for objective, route/reward, XP, Guild/banking/guidance, and signoff. New generated modules also have richer app-authored room prose while preserving the PDF/player boundary for exact rules text and rewards.
- **Generated TAG recovery hardening pass (2026-06-30):** Older/resumed generated TAG modules can now repair missing generic room prompts and legacy log wording through a dedicated session repair endpoint. Director panels show an "I think you are here" confidence line, link directly to Rules Reference/Tables, and TAG Actions keeps the full toolbox behind an Advanced TAG controls toggle when Relevant Now can guide the current room.
- **Generated TAG procedure idempotency fix (2026-06-30):** Direct generated TAG procedure buttons such as **Run Underground caves room target** now persist the rolled target on the generated lead, return the stored result on repeat clicks instead of rerolling, and render as recorded with next-step guidance.
- **TAG Treasure Map cave progress pass (2026-06-30):** Underground caves room targets now show a cave progress panel in the Current Objective and generated closeout areas. When the recorded target appears reached, the app moves from guidance to automation for active Lady in White Treasure Map quests: target room, final Boss, and objective completion are driven by play state.
- **TAG closeout automation pass (2026-06-30):** The Dashboard and Go Adventure now include an Adventure Closeout Checklist covering generated lead, route marker, XP, Guild obligations, banking/storage, and guidance actions. TAG signoff panels can record a generated-adventure review to the TAG log and Campaign Chronicle without falsely resolving printed-rule decisions. Closeout tasks now include action links to Guild, Banking, Go Adventure, and Rules Reference targets. Tables now includes `tag_closeout_checklist_automation_table`.
- **Modern TAG workflow completion pass (2026-06-30):** Troupe, Guild, Banking, Settlement, and Go Adventure now share a TAG Workflow Summary that surfaces troupe readiness, Guild benefits/coffers, TAG bank and hidden-trove state, generated TAG leads, route markers, pending XP, open closeout, and guidance counts. Each TAG-heavy page now also includes a signoff panel for generated TAG leads, latest route marker, pending XP markers, and recent TAG log review. Tables now includes `modern_tag_workflow_table` and `tag_generated_adventure_signoff_table`.
- **Modern dashboard default / campaign world-builder pass (2026-06-30):** `/` now opens the modern dashboard by default and `/legacy` preserves the old homepage. Modern sections return to the dashboard after completion flows. Campaign Management now owns app-level world-builder records for campaigns, guilds, troupes, friendly settlements, future troublesome towns, and hex-map planning notes. Existing characters, parties, guild, troupe, and settlements are normalized to the default campaign `Norindaal`, guild `Adventurers Guild`, troupe `Troupe1`, and friendly settlement `Hearthmere`. This is an app-level campaign feature, not a TAG PDF rule boundary.
- **Modern dashboard campaign polish pass (2026-06-30):** Campaign Management now has selected-campaign summaries, search/sort/filter controls across campaigns/guilds/troupes/friendly settlements/troublesome towns, inline editing, explicit assignment conflict hints, empty states, and safer delete warnings. Character Management now surfaces campaign/guild/troupe/party/home-settlement context with quick links to the relevant management pages. The Tables API includes `campaign_worldbuilder_schema_table` so the dashboard documents the world-builder entities and one-to-one/many-to-one assignment rules.
- **Modern dashboard management polish pass (2026-06-30):** Troupe, Guild, Party, and Settlement Management now share world-context panels with direct Campaign/Rules/Tables links. Troupe and Guild member lists are searchable/sortable with richer campaign/guild/home context. Party Management has saved-party search, troupe filtering, assignment warnings, and clearer banking/delete hover text. Settlement Management separates campaign settlement records from tracked TAG settlement state, filters friendly/troublesome records, and clarifies that troublesome towns remain placeholders. Tables now includes `modern_dashboard_management_table`.
- **Campaign World Builder release pass (2026-06-30):** Campaign assignment integrity is now enforced beyond the UI: guild/campaign uniqueness is validated, troupe campaign/guild/home selections are checked for same-campaign consistency, moving guilds or troupes propagates campaign/guild context to affected parties and characters, and character troupe reassignment removes incompatible party membership with a guidance message. The protected default friendly settlement is now `Hearthmere` while the stable internal id remains unchanged for migration. Tables now includes `campaign_assignment_integrity_table`.
- **Adventure Closeout and Campaign Chronicle release pass (2026-06-30):** Completing an adventure now creates a persistent campaign chronicle entry plus structured guidance tasks for closeout review. TAG closeout tasks also create matching guidance tasks, and resolving a closeout task completes the paired guidance item without deleting campaign history. The Dashboard now has a compact Needs Attention card for guidance, closeout, active sessions, roster health, and assignment warnings; the bottom Guidance / Log remains collapsible and supports Complete / Defer / Dismiss actions. Campaign Management now shows a Campaign Chronicle panel. Tables now includes `adventure_closeout_workflow_table`, `campaign_chronicle_event_table`, and `guidance_task_status_table`.
- **Campaign Command Center and Closeout Gates release pass (2026-06-30):** Campaign Management now starts with a command-center overview of selected-campaign guilds, troupes, settlements, troublesome-town placeholders, parties, characters, active sessions, open guidance, unresolved closeout prompts, and recent chronicle. Guidance Archive filters tasks by status/priority/category/search and can reopen completed/deferred/dismissed prompts. Chronicle export is available as JSON or Markdown. Go Adventure now calls a server-side closeout gate that separates hard blocks from explicit override warnings. Tables now includes `campaign_command_center_table` and `go_adventure_closeout_gate_table`.
- **Modern character / Go Adventure hardening pass (2026-06-30):** Character Management now has deep roster filters for campaign/guild/troupe/party/readiness, full-sheet readiness rows, weapon-slot assignment, armor/shield inventory detection, learned-skill/status summaries, world-context links, and warning summaries. Go Adventure setup now blocks critical start errors (missing/short party, fallen or locked members, missing imported/AI module, invalid map cap) while surfacing injured/equipment/context warnings for deliberate signoff. Tables now includes `character_management_readiness_table` and `go_adventure_setup_readiness_table`.
- **Modern dashboard phase 2 / artwork registry pass (2026-06-30):** Dashboard forms and buttons now use left-aligned, bounded controls more consistently. A local-only rules artwork registry feeds dashboard artwork panels, Rules Reference artwork filtering, and Tables artwork filtering. PDF-derived art is intentionally written under `DATA_DIR/assets/rules_art/local/`; commit only licensed/publication-approved art.
- **Modern dashboard guidance/reference pass (2026-06-30):** The Home Guidance / Log panel now sits at the bottom of the dashboard and is collapsed by default. Dashboard `?` links use exact Rules Reference `entry=` URLs where a specific entry exists, and fall back to targeted search links rather than copying full PDF text into the UI.
- **Modern dashboard workflow polish pass (2026-06-30):** Key management pages now include compact workflow guide panels with direct Rules Reference links. Go Adventure is split into Start New Adventure, Setup Check, TAG lead creation, Resume Adventure, and Saved Games so new starts are visually distinct from continuing old sessions.
- Full automated test suite: courtship + class pass regression green (`tests/test_courtship_classes.py`, 76 courtship tests); broader suite may include pre-existing failures unrelated to this pass — re-run before release tagging.
- Forsaken Depths river editing now uses Water as a persistent surface toggle:
  Walk/Block, Half, Slope, Long Slope, Curve, and Half Curve can paint the same
  geometry as blue water, with save/reload browser coverage.
- Door and passage exits can use all eight compass directions. Diagonal exits
  persist their angle/span and place connected tiles through reciprocal
  NE/SW or NW/SE links.
- Exit markers may use one blocked padding square beyond a traversable opening;
  the connecting tile can overwrite that padding during placement.
- Forsaken Depths river metadata accepts ETC (Entrance to Citadel), matching
  the river hazard and printed tile usage.
- **Courtship of Flower Demons (TCOTFD)** — Blossoms' Demesne portal branch, woo/fight, Book of Secrets, Blossoms spells/items, Apothecary Cookbook brewing, and **six playable TCOTFD classes** (Wandering Alchemist, Satyr, Conservationist, Demonologist, Cambion, Succubus). See `docs/FORSAKEN_DEPTHS_ENGINE.md` and rulebook entry `tcotfd_playable_classes`.
- **Program Phase 4 (2026-06-24):** ruleset profiles (`ruleset_profiles.json`, `/api/rules/profiles`), FD Heroic spell catalog + cast resolver (`heroic_spells.json`, `forsaken_depths_heroic_spells.py`), Abyss Phase B table index (`abyss_tables.json`), TAG campaign shell (`/api/campaign`, days passed on adventure complete).
- **Stabilization pass (2026-06-28):** EE spell resolver coverage promoted to validated (`tests/test_ee_spells_audit.py`), puzzle-box attempts can target the chosen hero, Living Statue stats/treasure are covered, TCOTFD/FD icon rows are expanded, and FD Fire of Truth applies its +1 chaos-creature bonus to the actual spell roll with matching UI hover text.
- **FD/TAG rules pass (2026-06-28):** Teleport Enemy now persists returning foes, ticks them back room-by-room unless blocked, and rolls occupied-room reactions when a returning foe crosses living occupants; Mass Blessing targets living party members and hirelings with explicit condition-removal choices and Life-cost accounting; TAG settlement Apothecary brewing has its own UI/action separate from camp outside the dungeon.
- **TAG settlement phase 1 (2026-06-28):** Persistent TAG settlement name/size/notes are on the Adventure panel; settlement-size random roll, special item availability checks (d6 + settlement size, fail-by-1 surcharge), and Streetwise Look for Clues are wired with rule math, logs, and hover hints.
- **TAG travel phase (2026-06-28):** Moving to a different settlement now updates the current TAG home settlement, rolls random settlement size, advances campaign days, and logs either simple 3d6-3 travel or optional hex-map direction/distance/road/tithe/encounter-check math.
- **TAG services phase 1 (2026-06-28):** The Adventure-panel TAG settlement UI now lists the first six treasure/service options from TAG pp.9-11: bank accounts, bank inheritance, magic lockers, platinum exchange, hidden treasure troves, and resurrection/blessing tags. Rows show settlement-size availability, costs, implementation status, hover hints, and hidden-trove risk rolls.
- **TAG services phase 2 (2026-06-28):** The settlement service catalog continues with gems/jewelry conversion, Bag of Carrying, 10-foot pole, lantern hook, very nutritious food, and poison resistance training, including service-row availability buttons where the PDF calls for availability rolls.
- **TAG services phase 3 (2026-06-28):** The service catalog adds martial arts training, gambling house, treasure maps, moneylenders, good boots, and flammable oil, with treasure-map price and moneylender pursuit rolls surfaced as settlement UI actions.
- **TAG services phase 4 (2026-06-28):** The catalog adds horn, wineskin, flail-axe, aspergillum, Availability Rolls, and Streetwise Rules rows. Horn attraction, flammable-oil throw, and aspergillum break checks are exposed as service UI actions with hover hints.
- **TAG campaign phase 5 (2026-06-28):** The settlement panel now tracks troupe name, active party selection, guild membership/coffers, settlement storage gold/items, campaign platinum pieces, magic lockers, treasure-map bonuses, and Look Tough state. New UI actions with hover hints cover TAG storage/withdrawal, fixed service purchases, Gambling House gp outcomes, magic locker creation/summoning, Listen to Rumors, Interrogate, Look Tough, and Following the Treasure Map / Map Leads To roll summaries.
- **TAG adventure lead phase (2026-06-28):** Rumor Scenes, Treasure Map leads, Thematic Dungeons, and Guild Jobs can now be converted from the TAG settlement panel into normal installed adventure modules. The generated adventure is written under the app-data Adventure library, appears in the existing Adventure section/dropdown, is selected automatically, and has hover-hinted controls.
- **TAG home help pass (2026-06-28):** The home Adventure panel TAG settlement tools are split into collapsible Settlement, Troupe, Travel, Availability, Streetwise, Storage, Buyer, Magic Lockers, Maps/Adventure Leads, and Services/Log sections. Each section has a compact `?` help button with hover text and a modal summary explaining what the controls do and how to check the result against TAG.
- **TAG adventure content phase (2026-06-28):** TAG generated adventures now use structured profiles for all 12 Rumor Scenes, six Thematic Dungeons, and six Guild Job minor quests. Installed modules carry source pages, scene/thematic notes, reward notes, and encounter-proxy metadata in `source.parameters.tag_reference`, with profile-specific room text and finale spawns where an existing foe profile is available. TAG service rows also document Adventurers Guild jobs, Trinkets, and Guild spells with hoverable service UI.
- **TAG special foe phase (2026-06-28):** TAG generated adventures now have a separate TAG monster supplement and can spawn named TAG foes without altering the locked EE monster tables: White Gargoyles, Mutant Fish, Silent Scream Priestess/Cultists, Hill Giant, Minotaur Lord, Bandit Chieftain/TAG Bandits, Gorungar and archers, Griffin, Red Portrait Horror, Monoceros, and related maze minotaurs. Mixed finale encounters are now written into the generated adventure manifests.
- **TAG action automation phase (2026-06-28):** The TAG settlement panel now has a TAG Actions section with hover-hinted controls for generated-adventure branch resolution, Clue spends, variable counts, capture-alive outcomes, reward claims, trinket use, Guild spell use, inheritance notes, bank/hidden-storage robbery risk and recovery, moneylender enforcement, and guild upkeep. Safe state changes such as Clue spend, gp reward, potion healing, scroll/trinket consumption, status markers, and coffer upkeep are applied and logged.
- **TAG scene rewards and bank ledger phase (2026-06-28):** TAG Actions now includes a Scene result selector for printed outcomes such as Medusa pendant, gargoyle bounty, Gorungar bounty, bandit capture, Shaura reward, Daroc's cat, mutant-fish rations, Agaratha, Deoldyn training, and Dragon's Lair type reveal. TAG bank accounts are tracked per character with deposit/withdrawal, 10% deposit fee, heir notes, inheritance transfer, and 20% inheritance tax logging.
- **TAG route/XP/Guild spell phase (2026-06-29):** TAG Actions now has route controls for parley success/failure, Clue gates, peaceful/hostile branches, skipped/unlocked scenes, solo restrictions, and finale route selection, all persisted as structured campaign signoff state. XP controls track pending scene XP, minor encounter counts, capture XP, training XP-roll markers, and immediate XP awards. Guild spell automation applies safe markers for Troupe Switch, Look Tough, stealth/luck, weapon enchantment, and later corrected Speedy Recovery timing.
- **TAG Guild spell correction pass (2026-06-29):** Guild spell handling was corrected against `Tales_from_the_adventurers_guild.pdf` pp.65-66. Speedy Recovery no longer heals to full immediately; it marks settlement healing at 2 Life/day. Look Tough is consumed on the next Streetwise roll and adds +Level or tier-number bonus as printed. Wizard's Luck now hooks into the Gambling House workflow, consumes its marker, resolves spellcasting against desired result 10, applies the -2 fallback on failure, and records natural-1 jail/fine debt.
- **TAG Guild spell targeting pass (2026-06-29):** TAG Actions now has optional Guild spell target fields. Temporary Weapon Enchantment records the chosen carried weapon as magical with no Attack bonus; Troupe Switch records both caster and pre-chosen recipient markers, including the summoned-character combat penalties and 2-in-6 armor/spell-slot checks; Silence of the Mouse records the paired Stealth-swap characters and six-room setting-penalty window. Marker clearing removes exact target-specific markers.
- **TAG Guild leaving / modern reference pass (2026-06-29):** Turning off Adventurers Guild membership is now blocked while Guild coffers are below the 5000 gp requirement, with a TAG log entry explaining the restriction. Modern Rules Reference no longer truncates matches and includes summary/source metadata; Modern Tables now includes monster bestiary, monster reactions, map elements, and icon registry groups, with expandable row previews.
- **TAG guide/checking/rewrite phase (2026-06-29):** The TAG panel links to `docs/Checking/TAG_SECTION_GUIDE.html`, which covers before/during/after-adventure workflow and TAG banking. Player-actionable checking docs and spreadsheet outputs are consolidated under `docs/Checking/`; compliance audits remain in `docs/` as internal engineering records. TAG route markers now rewrite the latest generated TAG module where safe by recording route metadata, opening/closing Clue-gated routes, suppressing peaceful proxy combat, and annotating finale/solo/skip routes. The TAG panel shows a route/XP/bank summary and can clear Guild spell markers after use.
- **TAG troupe/banking UX pass (2026-06-29):** TAG branch, route, scene reward, XP, Guild spell, and finance controls now open from a TAG Actions dialog during exploration instead of occupying the Home settlement panel. Home keeps settlement/downtime controls plus compact **Troupe manager** and **Bank transfers** buttons. Troupe management now tracks persistent troupe members separately from the active party, lists member status/gold/TAG bank balances, and limits active party selection to troupe members. Legacy camp banking and TAG settlement banking coexist; explicit transfer controls move carried and optionally legacy-bank gold into per-character TAG bank accounts with a logged fee/no-fee ruling.
- **TAG PDF compliance correction (2026-06-29):** Banking/troupe/Guild behavior was checked against `Rules/Tales_from_the_adventurers_guild.pdf`: banks are available in any settlement size (TAG p.9), banked money is available when needed, normal bank deposits pay the one-time 10% fee, Guild ledger deposits are free (TAG p.68), bank-robber recovery costs 3 Clues, hidden-trove recovery costs 4 Clues, Guild martial arts training is free, Guild coffers default to 5000 gp when Guild membership starts, and the equipment shop applies the 10% Guild mundane equipment discount.
- **New home routed pages / TAG recovery pass (2026-06-29):** The existing home screen remains the default, with a compact topbar icon opening `/modern`. The new home now routes to standalone pages for Character, Troupe, Guild, Party, Equipment, Finance, Settlement, Campaign, Settings, AI Adventure, Go Adventure, Rules, Tables, Library, Guides, and Developer tools without sending those sections back to the legacy home page. `modern-pages.js` starts the frontend split by calling existing APIs directly for roster, party, TAG banking/trove, Guild upkeep/job, settlement, equipment, AI import, rules/tables, and session-start workflows. Large future surfaces are visibly marked in progress.
- **Modern dashboard feedback pass (2026-06-29):** The standalone modern pages now use reusable character/equipment/reference filters and sorting. Character Management shows the roster first and caps the create form. Troupe Management has filtered add/remove, member listing, and clearer travel/home settlement controls. Party Management has collapsible party rows, expand/collapse all, richer member details, and party TAG banking. Equipment, Banking, Rules Reference, and Tables have search/sort/filter controls. Settlement Management now persists a tracked TAG settlement list with create/select/delete/travel actions and searchable availability checks. Settings stores dashboard preferences for enabled rulesets, default ruleset, map mode/limit, XP system, and TAG banking. Go Adventure uses those preferences, remembers the last party, separates Random/Imported/AI module lists, and exposes resume/load/delete session management. Developer unlock is remembered for the browser session.
- **TAG Guild management pass (2026-06-29):** Guild benefits now use a single active-benefits rule: the troupe must be marked as Adventurers Guild members and Guild coffers must be above 0 gp. The rule gates free Guild ledger deposits, the mundane equipment discount, free martial arts training, cartographer map help, resurrection funding, and the once-per-adventure/month availability reroll. The standalone `/modern/guild` page now exposes Save Guild, upkeep, 50% monetary loot share, resurrection funding, availability reroll/reset, and Guild Job lead controls with hover hints. Upkeep resets the availability reroll and suspends benefits at 0 gp.
- **TAG adventure closeout pass (2026-06-29):** Completing an adventure now creates persisted TAG closeout tasks in campaign state. Guild members receive prompts for 50% monetary loot share, Guild upkeep, used availability-reroll reset, and leaving-restriction signoff. Stored hidden troves prompt for the between-adventures risk roll or stolen-trove recovery; robbed bank accounts prompt for robbery recovery; pending TAG XP markers prompt for closeout resolution. The `/modern/guild` and `/modern/banking` pages show these prompts with hover text and a **Mark Done** action, while the relevant real actions clear matching prompts automatically.
- **TAG generated-adventure route rewrite pass (2026-06-29):** TAG route actions now make concrete safe edits to the latest installed TAG module. Peaceful/parley routes suppress the proxy combat and open the route, hostile routes restore/keep the proxy fight, Clue unlocks insert an **Unlocked TAG Scene** room before the finale, blocked Clue gates close the route, skip-scene removes the optional side-clue room, and final/solo routes annotate the finale. Each rewrite is recorded in `source.parameters.tag_reference.route_rewrites` and surfaced in the TAG route summary.
- **TAG Guild/Finance/Branch workflow pass (2026-06-29):** `/modern/guild` is now split into membership/coffers, Guild finance, jobs/members, benefits, closeout, and recent-log sections. `/modern/banking` now shows the TAG bank ledger, robbed-account flags, hidden-trove stolen state, finance logs, and explicit inheritance/loan/robbery-risk controls. Bank robbery risk marks the selected TAG account robbed; successful 3-Clue recovery clears it and the exploration TAG Actions finance dropdown routes robbery recovery through the Bandit Hideout creation workflow. The TAG Actions dialog now includes an in-dialog workflow guide for branch/route/reward/XP/Guild/finance decisions.
- **TAG contextual exploration / modern dashboard pass (2026-06-29):** Generated TAG imported adventures now show a room-aware **TAG scene prompt** panel in exploration room details. The shortcuts prefill the TAG Actions dialog for lead entry choices, side rewards/XP, complication parley/Clue routes, finale routes, and unlocked scenes while leaving the player to confirm the exact printed amount/result. Modern Character Management now shows class artwork, core stats, starting equipment/spells, abilities, implementation status, and full class text before creation. Modern Troupe Management now has clearer create/save, add/remove, active-member, member-list, and travel/home settlement sections with hover text.
- **TAG generated prompt metadata pass (2026-06-29):** New generated TAG modules now embed `source.parameters.tag_reference.room_prompts` for lead entry, side clue, complication, final scene, and unlocked-scene rooms. The exploration prompt panel consumes that metadata, including known 2-Clue gates for Dragon's Lair, Shaura, Daroc's familiar, and Fiendish Abyss, while retaining fallback prompts for older generated saves.
- **TAG module fidelity pass (2026-06-29):** Dragon's Lair, Bandit Hideout, Shaura's Chaos Cult, and Gorungar now carry structured generated-module profiles with target room counts, procedure notes, signoff checks, and exact supported prompt actions such as Dragon type reveal, Bandit Chieftain capture, Shaura reward, and Gorungar head/alive bounty. Exploration room prompts display these module-profile notes with hover text.
- **TAG remaining generated-profile pass (2026-06-29):** Ghastly Mine, Giant's Lair, Fiendish Abyss, Minotaur Maze, Clean Up My Castle, Griffin Omelets, A Portrait in Red, Sewers Search, and Monoceros Hunt now carry PDF-based generated-module profiles. Placeholder "exact extended text needs signoff" notes were replaced with target/procedure/signoff metadata and prefilled actions where the current TAG Actions dialog supports them.
- **TAG generated-profile action pass (2026-06-29):** Dragon's Lair type reveal now updates the latest installed Dragon's Lair module finale with the revealed dragon title/result while retaining a valid Young Dragon encounter proxy. Bandit Hideout now has a dedicated hover-hinted stolen-goods branch action and contextual room button that rolls the 1-in-6 room check, 8d6 gp value, and trapdoor chance without auto-claiming the loot.
- **TAG theme procedure action pass (2026-06-29):** Ghastly Mine, Fiendish Abyss, and Minotaur Maze now expose hover-hinted TAG Actions and contextual generated-room buttons for their printed procedure rolls: undead minion/major-foe replacement, gp treasure conversion, cave-in count severity, Fiendish Abyss Prisoner Table, Minotaur Maze lost checks, wandering subtype rolls, and Special Event Table results.
- **TAG Guild Job procedure action pass (2026-06-29):** Clean Up My Castle, Griffin Omelets, A Portrait in Red, Sewers Search, and Monoceros Hunt now expose hover-hinted TAG Actions and contextual prompt buttons for their printed job bookkeeping: cleanup pay tally, mountain/nest/egg rolls, portrait outbound/persuasion/snatch checks, sewer vermin/minion/disease rolls, and monoceros tracking/clue-risk/hide checks.
- **TAG Actions UX hardening pass (2026-06-29):** The TAG Actions dialog now includes a hover-hinted Branch action helper row that changes with the selected branch action and explains exactly what to put in Reference and Amount, including compact syntaxes such as `party=4 boss=1 cache` and `mod=-1`.
- **TAG generated adventure manual test pass (2026-06-29):** `docs/Checking/TAG_SECTION_GUIDE.md` and `.html` now include a generated-adventure manual test checklist covering lead creation, adventure dropdown installation, room prompt checking, hover/prefill verification, route rewrites, closeout prompts, and per-family coverage order. The legacy TAG panel and modern Guides page link directly to the checklist.
- **TAG Rumor procedure prompt pass (2026-06-29):** Rumor-generated modules now expose contextual TAG Actions for the printed Rumor scene procedures that were still generic: Bofto Scene 9 choices, Scene 11 ambush chance, Scene 10 assassin approach, Xasartha stealth/reactions, leprechaun shoes/spell teaching, mutant fish hypnosis, white gargoyle count/surprise/stone-skin checks, Daroc reward, Deoldyn training, and Agaratha solo/reward handling. Each new action has a visible dropdown option and hover hint.
- **TAG Bofto/Treasure Map procedure pass (2026-06-29):** Bofto's follow-up Scene 14/19 procedures now have UI-backed TAG Actions for theft Save, star-object Will Save, and Star-Slayer replacement checks. Treasure Map generated modules now carry destination-specific module profiles and contextual prompt buttons for Following Treasure Map, cave/structure room counts, forgotten-temple idol/scroll rolls, humanoid camp report/stealth/forces, and lich chamber death-magic/Life/treasure handling, with matching hover hints.
- **TAG Thematic prompt completion pass (2026-06-29):** Giant's Lair now has UI-backed TAG Actions and generated-room prompt buttons for the hill giant's 4-in-6 first-turn boulder throw and final-room treasure/size reminder. The TAG section guide now lists the expanded Rumor, Treasure Map, Thematic Dungeon, and Guild Job prompt coverage for manual PDF signoff.
- **Modern Go Adventure TAG lead UI pass (2026-06-29):** `/modern/go-adventure` now has a player-facing **Create TAG Adventure Lead** card for Rumor Scenes, Treasure Map destinations, Thematic Dungeons, and Guild Jobs. Created leads refresh and select the installed imported module immediately, and the selector now displays adventure `name` values instead of raw generated IDs.
- **FD playtest stabilization (2026-06-28):** Forsaken Depths random delves continue to start from the FD tile catalog per FD p.27; start tiles that lack a printed outside exit now receive one open Dungeon Exit and existing saves are repaired on load. The Passage event logs Citadel entry, room count, and the Tier-in-6 trap chance, and FD trap resolution logs the named FD trap row before saves.
- Abyss hireling marching order now uses a shared #1-#6 line for heroes and
  retainers; party sheets show assigned bodyguard/acolyte protection.
- Expert-skill learning keeps class-ineligible options visible but disabled with
  hover explanations.
- Inset map exits keep their authored editor position during gameplay placement;
  adjacent tiles may overlap the one-square blocked padding outside the exit.

### Release scope

Include:

- the inset/multi-cell exit persistence correction;
- Forsaken Depths river water as a surface toggle for every existing shape tool;
- true 45-degree door/passage exits and diagonal connected-tile placement;
- save/reload and browser regression coverage for water geometry;
- tile-editor cache version `0.40.2`;
- corrected map-editor save-path documentation and the five-book master coverage
  tracker.

Recent deeper-rule work:

- **Abyss runtime pass (2026-06-28):** Four Against the Abyss profile added to setup; Abyss 2d6 room content, monster subtables, claimable treasure payloads, unique-feature/event summaries, and Abyss wandering spawns are routed through `abyss_tables.json`.
- **Abyss phase 1 exact effects (2026-06-28):** Abyss traps, special-feature choices, unique-event choices, Enchanted Banquet, Useful Stuff choices, and magical-defense item names now resolve through existing trap/feature/treasure UI.
- **Abyss phase 2 tactical reactions (2026-06-28):** Abyss minion reaction tables from p.53 are wired, including exact bribes, fight-to-the-death fallback, Trial of Champions champion choice, and tagged leader priority.
- **Abyss phase 3 targeting (2026-06-28):** leader-lock targeting is enforced server-side and mirrored in the combat UI; multiple Abyss bosses get default split targets and lone-hero secondary-boss Defense penalties; tagged hordes attack once or twice per living character as specified.
- **Abyss item actions (2026-06-28):** Elven Bread, Blessed Horseshoe, Parchment of Banishing, Medallion of Snake Charming, Philter of Fire Breathing, and Ring of Three Wishes have party-sheet use buttons with hover hints; passive Abyss armor, undead/vampire defenses, silver weapons, blessed stakes, and Baton of Righteousness are in combat math.
- **Abyss afflictions (2026-06-28):** Dark Plague L10 exposure, room-entry harm/spread, Blessing/Elven Bread immunity, lycanthropy exposure/treatment/transformation, and vampire-drain resurrection blocking are implemented with focused regression coverage.
- **Abyss campaign plots (2026-06-28):** Six campaign plots now have persistent playable state, setup/room-panel controls with hover hints, key gold/Clue/Life/Madness costs, finale triggers, rewards, vampire sire hunt/re-encounter, one Entity artefact piece per dungeon, and large-room Dragon Lair routing.

Defer to later releases:

- Abyss optional extended-campaign chaining playtest sign-off;
- TAG remaining full adventure content expansion for broader playtest sign-off;
- large `app.js` / `random_dungeon.py` decomposition.

### Home screen layout (June 2026)

- **Create character:** collapsed by default; class name and role overlay the
  portrait (art visible beneath a top gradient); hover shows rulebook summary.
- **Character roster:** scrollable list (~4 heroes visible); drag handles feed the
  party builder. Expanded cards show expert, heroic, and legendary skills learned.
  Party builder and saved-party member names link to the roster card.
- **Party builder:** four marching-order slots (drag from roster, double-click,
  or Add to party). When the party matches an active camped session, **Feed hungry**
  and **Bank carried gold** actions appear. Expanded saved parties show **Last adventure**
  (summary / closeout / full log tabs) until the next adventure completes anywhere.
- **Adventure start:** optional **Begin camped outside** (browser preference
  remembered) for hirelings, bank, shop, and regroup before the first foray.
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
- **Camp panel / bank:** camped sessions expose **(Re)enter Dungeon**, Bank, Transfer,
  Equipment Shop, and Abandon Dungeon actions. Optional **Begin camped outside**
  at session start (home Adventure panel) opens camp before the first foray;
  imported adventures defer entrance triggers until (Re)enter. The bank deposits
  carried dungeon gold into home funds and withdraws up to the dungeon carry limit.
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
  miner next-tile preview after trade, fungal merchant +20% equipment buys/resale
  (including silvering/gilding with per-weapon picks), repeat merchant reroutes to
  halfling scout, trap-then-rare-item and spore-cloud events auto-resolve,
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
  scout-ahead reveals/checks room Final Boss status immediately; session panel shows
  major foes met, next check threshold, and active **Milestone** progress per hero;
  Summary log always records check outcomes; unlimited maps use a **session-start
  map-element cap** (default 60; presets 80/100 or custom whole number 1–999) as
  the grid-full equivalent and force Final Boss on the last element when needed;
  triple treasure; extra XP roll; prominent Final Boss foe chips/cards; a completion
  banner appears after the Final Boss dies so the player knows the main dungeon
  objective is done.
- **Milestones (EE p.120):** catalog in `milestones.json` with `how_to` hints; home
  **milestones_table** on Rules tables panel; choose on the **home roster** character
  sheet (expand a hero → Milestones → Take Milestone) when not in an active adventure,
  or while **camped outside** from the party sheet. Milestone picker shows hover/hint
  text. Progress tallies during play and appears in the session panel and party sheets;
  completion actions (Scroll Librarian grimoire, Gem Collector jewelry, Panoplia,
  Thrice Blessed sacrifice) at camp. Optional **Begin camped outside** at session start.
- **Home Party start/camp polish:** start-adventure setup persists adventure, XP
  system, map bounds/cap, and Begin camped outside preferences. Home Party cards show
  bank totals and hunger timers, expose Party Eat / Feed Hungry / Bank all characters
  gold for matching active camped parties, and explain unavailable camp actions. Start
  failures now show field-level API validation messages. Legacy `Rations` inventory
  labels are treated as Food rations for hunger reset flows.
- **Expert spells:** all six Abyss expert spells wired; Mass Teleport ally/destination picker and Lifeforce amount in combat and exploration; home **expert_spells_table** lists mechanics.
- **Hirelings (Abyss):** Expert tier unlocks the collapsible camp hirelings panel — max 2 retainers inserted into the shared #1–#6 marching order, with marching reorder at camp or in dungeon, max 3 professional services/camp, combat attacks, morale (hero/retainer death, petrify, insanity), treasure share, resurrection, porter cargo return on clean exit, loadout enforcement, spear sidearm, adjacency-filtered assign for bodyguard/acolyte/spear carrier, optional bodyguard intercept and acolyte Blessing preservation (combat pauses until chosen; Fight Round disabled; hire validates assignment before charging gold). Required-assignment retainer hires preserve the selected hero across slot/type refreshes, auto-select the only adjacent hero, and fall back to that hero on Hire before showing any adjacency alert; party sheets show assigned bodyguards/acolytes and the Retainers panel shows combined marching order. **Alchemist professional:** 8 potions, commission at camp (50gp + material), d6 completion on adventure exit. **Poison Expert:** rogue L5+, 25gp, coat weapon/arrow for +1 vs minion or boss level drop. Home **hirelings_table** (10 retainers + 11 professionals + 8 potions).
- **Named save labels:** optional label when saving; shown in active/saved game lists.
- **Fiendish Foes (EE p.180):** per-adventure-type enable checkboxes (default on); when enabled and 2+ heroes are L3+, d6 1–3 standard / 4–6 fiendish monster table rolls; eligibility checked at roll time.
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
- **Unlimited map mode:** no fixed sheet; choose a map-element limit at session start
  (default 60, or 80/100/custom up to 999) before exploration is blocked at grid full.
- **Map Element Editor:** validation panel, export/import, save reload; Delete
  Exit tool plus per-row Remove buttons for mistaken door/passage markers; exit
  placement help documents inset blocked-padding overlap; stale partial Docker
  tile overrides no longer shadow packaged metadata.
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
| `trap_table` | p.164 |
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
  wired for live play; **authored-adventure-only** special clue spends (custom
  manifest triggers) remain a Phase 3 item — Kerrak Dar-style hoards use
  `claim_kerrak_dar_hoard` via Epic Rewards.
- **Heroic/legendary skills:** **45/45 heroic + 20/20 legendary** wired (combat, exploration, reactions, rest, traps, resurrection).
- Validate cavern/fungal table row text against owned PDF (starter tables wired). **p.160 caverns special items**, **p.164 dungeon traps**, **p.165 caverns traps**, **p.161 fungal rare items**, and **p.166 fungal traps** audited with row locks and regression tests.
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
- **Adventure history journal (planned):** persist multiple completed runs per party in `game.db` (party, adventure, completed_at, summary, closeout log, stats) with a home **Recent adventures** list. Current ship stores only the **last** completed run in browser `localStorage` until the next adventure completes anywhere.

## Data Safety

The local rebuild does not modify `\\TOWER\appdata\ahazi-against-darkness`.
Replacement deployment can be done without a backup if rollback is not needed.

## Maintenance scripts

- `scripts/patch_character_spells.py` — repair prepared spell lists on character
  records in `game.db` (all sessions or a named hero).
- `tools/validate_tiles.py` — structural validation for all 01–06 and 11–66 tiles.
