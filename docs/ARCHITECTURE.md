# Architecture

## Goals

- Implement the game as a deterministic rules engine with explicit state.
- Keep copyrighted PDFs as source material, not runtime dependencies.
- Make every rule table and adventure definition structured, reviewable, and
  testable.
- Keep deployment simple for Docker and Unraid.

## Backend

The backend is FastAPI.

Key files:

- `src/app/main.py` - HTTP API and static file mounts
- `src/app/schemas.py` - API and session state models
- `src/app/db.py` - SQLite record store
- `src/app/rules/repository.py` - packaged and user-overridden rule loading
- `src/app/engine/random_dungeon.py` - procedural session engine
- `src/app/engine/treasure_awards.py` - reusable defeated-group roll planning, claim distribution, outcome merging, and Final Boss/secret-door treasure integrity helpers
- `src/app/engine/tier_skills.py` - tier-skill eligibility, XP-spend fork validation, and tier-skill learning
- `src/app/engine/adventure_manifest.py` - import validation (`validate_adventure_manifest`)
- `src/app/engine/adventure_import.py` - install manifests under `data/adventures/`
- `src/app/engine/adventure_session.py` - `create_session_from_manifest()`
- `src/app/engine/adventure_runtime.py` - imported triggers and quest hooks
- `src/app/engine/adventure_prompt.py` - external LLM prompt builder
- `src/app/engine/adventure_allowlists.py` - allowlisted names for prompts and validation
- `src/app/engine/combat.py` - combat resolution, encounter-end state cleanup, and temporary-effect expiry
- `src/app/engine/combat_modifiers.py` - poison foes, blade poison, magic resistance
- `src/app/engine/monster_template_effects.py` - bestiary encounter_start/on_hit/per-turn template effects
- `src/app/engine/weapons.py` - missile eligibility and weapon-type attack modifiers from inventory
- `src/app/engine/magic_weapons.py` - magic weapon d6 type roll (p.163), +1 Attack bonus, class wield checks, resale formula
- `src/app/engine/subdual.py` - subdual damage and capture at 0 Life
- `src/app/engine/reactions.py` - reaction and morale rolls plus peaceful-encounter state closure
- `src/app/engine/spells.py` - spell resolution and MR-aware target level
- `src/app/engine/scrolls.py` - scroll identification, burning, and wizard copy-to-spellbook
- `src/app/engine/magic_items.py` - charged wand/staff parsing, `use_magic_item` cast, charge consumption
- `src/app/engine/inventory.py` - item and gold transfer between heroes (session and roster)
- `src/app/engine/class_profiles.py` - class Life offsets, spell slots, level-up benefit notes
- `src/app/engine/experience.py` - XP awards, Classical XP spending, level-up application, spell-slot assignment
- `src/app/engine/rest.py` - rest eligibility, recovery, wandering-check resolution, and reusable between-foray resource reset
- `src/app/engine/camp.py` - shared camp-at-entrance preparation, recovery, fallen-hero lookup, refresh logging, and explored-map summaries
- `src/app/engine/death_recovery.py` - body carrying, unattended-body theft, resurrection, burial, and fallen-hero Clue/Secret inheritance
- `src/app/engine/banking.py` - camp-only home-bank access, deposits, withdrawals, party banking, and shared outside-funds payments
- `src/app/engine/tile_geometry.py` - rotation, exit spans, authored portal tracing, grid fallback, occupancy, visibility, bounds, scoring, and placement geometry shared by random and authored tiles
- `src/app/engine/map_connections.py` - entrance opening plus reciprocal exit creation, lookup, refresh, persistence, repair, and synchronized door/passage state for reusable map connections
- `src/app/engine/clues.py` - held-Clue ownership, grants, party spending, legacy migration, and session-total synchronization
- `src/app/engine/search.py` - standard search-roll adjustment, table lookup, and player-visible roll explanation before result application
- `src/app/engine/dice.py` - dice helpers

## Persistence

Runtime state is stored in SQLite:

```text
DATA_DIR/game.db
```

The current store uses a generic `records` table keyed by collection and id.
That keeps early iteration fast while still moving away from loose JSON files.
If querying becomes important, this can migrate to normalized tables while
preserving API models.

Collections:

- `characters`
- `parties`
- `sessions`

Editable rule overrides are seeded to:

```text
DATA_DIR/rules/
```

If an override file exists, it wins over the packaged file in `data/rules/`.

Current packaged rule files:

- `classes.json`
- `monsters.json`
- `dungeon_tables.json`
- `tiles.json`
- `equipment_shop.json`
- `expert_skills.json`
- `icons.json`
- `rulebook_reference.json`

Synthesized at API time (not separate JSON files):

- `class_profiles_table`, `equipment_shop_table`, `expert_skills_table`, `expert_spells_table`,
  `expert_skill_implementation_table`, `ee_class_trick_flags_table`,
  `tier_training_costs_table`

## Frontend

The UI is a static browser app:

- `src/app/static/index.html`
- `src/app/static/app.js`
- `src/app/static/styles.css`
- `src/app/static/modern.html`
- `src/app/static/modern-pages.js`

The frontend does not implement game rules. It renders state returned by the API
and sends action requests to the backend.

New routed home:

- `/modern` and `/modern/{page_name}` serve `modern.html`, backed by
  `modern-pages.js`.
- The new home is a section router, not a shortcut panel back into the legacy
  home screen. Current routed pages cover characters, troupes, Guild,
  parties, equipment, banking/finance, settlement, campaign placeholders,
  settings, AI adventure import, adventure start, rules reference, tables,
  PDF library, guides, and password-gated developer links.
- Modern pages share client-side filter/sort helpers for characters,
  equipment/services, rules, tables, and adventure/session lists. Preferences
  for enabled rulesets, default random ruleset, XP system, map mode, map limit,
  and last selected party are kept in browser local storage; developer unlock is
  kept in browser session storage.
- `modern-pages.js` is the first split from the monolithic `app.js`; it calls
  existing backend APIs directly and should be expanded into smaller modules as
  each page matures.

Home screen rule browsing:

### Runtime content boundary

- `app.engine.content_registry` resolves the session's locked
  `active_supplement_ids` through the file-backed supplement registry. Its
  `ResolvedContentRegistry` separates active runtime providers from selected
  `review_only` supplements, exposes capability providers and legacy mappings,
  resolves the source-backed **State Catalogue** for that exact snapshot, and
  never executes source-workbench data.
- `app.engine.state_catalog` is the first content-provider resolver. It filters
  state definitions by their source supplement, exposes active state/provider
  ids, and keeps source-backed metadata separate from legacy status-string
  mechanics. New sessions save `active_state_ids` with their supplement
  snapshot; it does not yet execute effects or migrate saved statuses.
- `app.engine.terrain_catalog` uses the same shared supplement-content
  catalogue boundary for environments, terrain, and derived map terrain. New
  sessions save `active_terrain_ids`; existing terrain helpers remain the
  authority for table routing, spell gates, and movement until migrated.
- `app.engine.table_catalog` records the packaged rule-table identities and
  their source supplement. New sessions save `active_table_ids`, but
  `RulesRepository` and the table rollers remain unchanged until table routing
  is migrated one provider family at a time with parity tests.
- `app.rules.table_providers` now owns the legacy-compatible packaged table
  merge order. `RulesRepository` calls it without a supplement filter, so game
  behaviour remains identical. The provider function also accepts a locked
  supplement set for the next, table-family-by-table-family runtime migration.
- `app.engine.runtime_content` is a Developer Workbench adapter. It exposes
  read-only structured runtime states, terrain, tables, foe groups, classes,
  items, tiles, and allowlisted source modules for one registered supplement.
  It is intentionally separate from editable PDF Source Review records and
  does not promote or execute local import data.
- New sessions pass their final supplement snapshot through this resolver before
  saving. Existing random, combat, terrain, and class modules retain their
  current behaviour; later migrations can take this context as an explicit
  dependency instead of branching on scattered legacy profile fields.
- This is intentionally not the promotion pipeline. Reviewed foes, locations,
  classes, tables, states, tiles, and rules remain local data until a later
  validator converts them into trusted runtime records.

- `resolve_play_context()` in `terrain.py` is the single backend entry point for
  outdoor/terrain gates (spells, ranger missile, druid companion, combat weather).
  `session.play_context` is enriched on each API read (`exclude=True`, not persisted).
- `GET /api/rules/tables` returns all keys from `dungeon_tables.json` except
  meta keys (`validation`, `open_items`, `ruleset_status`), plus merged
  `equipment_shop_table` rows from `equipment_shop.json`.
- `GET /api/rules/monsters` and `GET /api/rules/monster-reactions` feed the
  home **Rules tables** panel (bestiary spawn templates and per-foe reactions).
  `RulesRepository` merges supplement files such as `fd_monsters.json`,
  `courtship_monsters.json`, and `tag_monsters.json` into the live bestiary
  without altering the locked Expanded Edition `monsters.json` rows.
- `GET /api/rules/tiles` and `GET /api/rules/icons` feed map element and icon
  registry groups on the home **Rules tables** panel. The icon endpoint merges
  `icons.json` overrides with generated defaults for room states, class icons,
  monster categories, and every named monster.
- The home UI renders one collapsible **Rules tables** section with nested
  groups (dungeon/adventure, monster bestiary, monster reactions, map elements,
  class profiles, icon registry); each table is its own collapsed `<details>` row.
- `RULES_TABLE_ORDER` in `app.js` controls dungeon-table display order; any new
  table used by the engine should be added there and to `dungeon_tables.json`.
- `tests/test_rulebook_validation.py::test_home_page_lists_all_dungeon_tables`
  guards that every non-meta key in `dungeon_tables.json` appears in
  `RULES_TABLE_ORDER`.
- `rulebook_reference.json` is the searchable implementation reference, not a
  full PDF transcription. Player-facing rules implemented by the engine should
  be discoverable there or in a structured Rules table; large catalogs belong in
  structured JSON plus the home Rules tables panel.
- `DATA_DIR/rules/rule_text_index.json` is optional local/private user data.
  The Developer PDF / Supplement Workbench can build it from manually uploaded PDFs in
  `DATA_DIR/rules/`; `GET /api/rules/reference` merges those exact page-text
  entries into the player Rules Reference search. The file is never packaged in
  git and should be backed up with the rest of the appdata folder.
- `DATA_DIR/Supplements/_sources/<source_id>/source_blocks.json` is the first
  supplement workbench capture format. It stores unassigned exact PDF text
  blocks with source page and extraction method so a human reviewer can later
  classify them as rules, adventure narrative, foes, equipment, locations,
  states, terrain, tables, maps, room tiles, ignored text, or manual-entry work.
  The local exact-text index remains the verbatim page-search source. Review
  blocks are separately built from column-aware positioned text, which ignores
  zero-coordinate full-page visitor artefacts and footer/page-number furniture
  so one scan does not create both complete prose and a second set of line
  fragments. Existing local scans retain their review history; a guarded cleanup
  can hide only short blocks proven to be contained in a longer block on the
  same PDF page.
  Each reviewed block may also carry a reviewer-created `title`. This is a
  navigational label for an identified rule or other content record and never
  replaces the exact extracted text. The workbench presents its source controls
  and PDF preview in a sticky, independently scrollable rail so the viewer
  controls remain available during long document review.
  Table drafting follows the same selection-first workflow: the reviewer selects
  the printed table text, and the workbench merges adjacent selected fragments
  when necessary, records the resulting block as `table`, and opens its local
  machine-row draft. This avoids a separate hidden assignment prerequisite.
  Source tables are typed local review records. Every table stores a readable
  title, stable machine id, optional roll expression, exact source wording, and
  review notes; its row payload is selected by `table_type`. The initial
  specialised type, `foe_encounter`, stores roll/range, foe name, a concise
  description, quantity, Level, Attack, Defence, category, states, weaknesses,
  named or inline reaction data, special rules, exact row text, reviewer notes,
  and review-only modifiers.
  Each modifier stores a target, adjustment, scope/condition, and exact printed
  wording. Saving a complete Foe Encounter row creates a
  local `reviewed_foes[]` profile linked to the source table/block/page. These
  profiles are explicitly `provisional`, visible in the source tree, and cannot
  affect gameplay until a future validated supplement loader promotes them.
  The same common source-backed profile record supports `mount`,
  `companion_animal`, `character_class`, and `location` assignments. Mount profiles capture
  combat details plus riding requirements, movement, and carrying capacity;
  companion-animal profiles add ownership/training; class profiles add
  eligibility, abilities, progression, and equipment restrictions. The shared
  source evidence, exact text, review status, state/weakness fields, and
  inactive-promotion boundary avoid creating disconnected import formats.
  Location profiles add a location type plus optional direct/table foe references,
  reward and hazard source notes, structured exits, friendly-character services,
  quest hooks, and map/pin/tile references.
  Character-class profiles may also link a reviewed local portrait artwork asset;
  the workbench prioritises candidates extracted from the same PDF page.
  Rendered-page and embedded artwork candidates can create local `masked_crop`
  PNG records under `DATA_DIR/Supplements/_sources/<source>/artwork/crops/`.
  A crop retains its parent artwork id and can be linked directly to a reviewed
  Character Class profile without becoming a tile or active game asset.
  The same cropper can save a `room_tile` child with its printed tile/die id;
  these children remain nested under a `room_tile_sheet` source candidate until
  later map-geometry and runtime-tile review. The workbench groups separately
  imported PDFs and image sheets under one supplement contents root without
  merging their independent source pages or offsets.
  PDF viewer navigation changes the physical preview page without rebuilding the
  source-content tree; this preserves the sticky viewer toolbar's active scroll
  position during repeated Previous/Next review. Render failures are reported
  in the viewer rather than silently leaving an unchanged image.
  Table row import is a separate, review-first candidate step. A source block
  can be analysed for the selected `table_type`, with proposed rows imported
  into the editable draft only after reviewer confirmation. `foe_encounter`
  recognises roll markers plus quantity/name/Level patterns in flattened PDF
  prose, preserves the entire exact row, and proposes only confident structural
  values. The same candidate-import boundary is reusable for future treasure,
  class, mount, companion, and other PDF-specific formats without treating an
  extraction guess as an active game rule.
  The Developer PDF / Supplement Workbench lists these local scans and opens a
  read-only searchable block browser before any assignment is written.
  Uploaded PDF source settings are stored in
  `DATA_DIR/Supplements/_sources/source_settings.json`; the printed-page offset
  is reused by both exact text indexing and source block scanning. The same
  settings file also stores `supplement_id` and `supplement_title`, because a
  playable supplement may be assembled from several source PDFs: a main book,
  map sheet, extra adventure booklet, errata file, or bonus document. Each
  source document keeps its own offset, raw blocks, reviewed blocks,
  reviewed table drafts, and artwork, while the workbench groups them under one
  supplement package id for later manifest/export work.
  `PATCH /api/supplements/source-metadata` can correct a source's package id,
  title, and printed-page offset after extraction. It recalculates page labels
  from immutable `pdf_page` values across raw/reviewed blocks, assigned and
  unassigned content, continuation metadata, artwork, reviewed tables, and the
  local exact-text index. Stable block ids and human review edits are retained.
  If the source was the final member of a mistaken package, package assets are
  moved into the corrected package and duplicate filenames are consolidated.
  Non-PDF source assets such as PNG/JPG/WebP maps or handouts are stored under
  `DATA_DIR/Supplements/_sources/_package_assets/<supplement_id>/` and listed
  with the same package id. These files are package-level evidence/source
  material rather than page-scanned rule text. Package source assets carry
  reviewer metadata such as title, category, status, and notes. The current
  workbench can delete unwanted imported/cropped assets one at a time or via
  selected ranges, split equal-grid tile sheets in the browser, or save one
  masked crop at a time for hand-drawn sheets that do not align to a grid. The
  mask cropper currently supports additive rectangles/squares and
  circles/ovals; each saved mask uploads back as a transparent PNG package
  asset. The cropper draws at the source image aspect ratio and uses explicit
  draw/pan modes plus zoom controls so reviewers can inspect large pages without
  distorting crop coordinates. D66 label helpers support tile names such as
  `01`, `02`, `11`, `12`, etc. Extracted child tiles are grouped as a
  collapsible list under the parent tile-sheet asset rather than cluttering the
  package's top-level source asset list. Package asset rows keep tools separate
  from review data: row-level buttons open a single active tool area for Manual
  Mask or Auto Split, while the whole source asset and extracted child assets
  remain in the data area below. Field-like status summaries in the workbench
  use collapsed compact info panels instead of long stacks of status rows; this
  keeps uploaded-PDF/index/package counts available without pushing review work
  down the page. Source block and artwork candidate rows follow the same
  separation: rows show compact previews and an Edit/Inspect command, while the
  selected block or artwork opens in one active review tool panel above the
  page-led lists. Blocks assigned as `table` can be drafted into editable
  machine rows beside the exact source text; reviewed table drafts are stored in
  `reviewed_tables` and are not active rules until a later trusted loader
  promotes them.
  Scans also record page-boundary candidates by joining the last block of one
  PDF page with the first block of the next so text split across pages can be
  found and reviewed without silently changing the original extracted blocks.
  The block review view shows the uploaded PDF beside page-led extracted text
  and artwork. Without a search term it follows the current PDF page; with a
  search term it searches the whole selected source document. A human reviewer
  can save assignments, split oversized blocks at the cursor, and merge
  selected adjacent blocks before later conversion into structured supplement
  data. Re-scans update `raw_blocks`; human-reviewed edits and assignments live
  in `reviewed_blocks` and are preserved separately. Reviewed block order is
  user-controlled with move up/down actions because PDF text extraction can
  interleave columns, captions, boxed text, and artwork.
  The block tree is category-then-PDF-page navigation. Page branches lazily
  create their block previews when expanded, so the workbench exposes the
  entire document without a fixed block cap or thousands of always-rendered
  text nodes. `POST /api/supplements/source-scans/<source_id>/blocks/bulk-update`
  applies one assignment/status change to a selected set with one load and one
  save. Select Shown is based on expanded rendered rows, not merely the current
  data filter. Direct split stores the caret from the displayed block text and
  does not require checkbox selection or a second editor. Selected-range merge
  remains strict about non-ignored intervening blocks. Merge Page is the
  page-cleanup path: using any selected block as the physical-page anchor, it
  merges every non-ignored reviewed block on that PDF page in document order,
  preserves ignored page furniture, and does not alter adjacent pages. If the
  page fragments had mixed assignments, the merged block returns to Unassigned
  so the reviewer must choose its category deliberately.
  The source review controls are sticky and compact, the PDF navigation controls
  overlay the preview, and a session-persisted draggable divider resizes the
  source/PDF column against the module-content tree. Assignment dropdowns carry
  category-specific hover descriptions so introduction, title pages, covers,
  playable tables, and ignored page furniture have explicit review boundaries.
  Package records in `source_settings.json` may also contain `requirements[]`.
  A requirement links immutable exact wording and source page/block references
  to an editable machine interpretation: eligibility scope/level, dependency,
  environment, enforcement, trigger, replaced tables, and retained core tables.
  This lets introduction prose remain categorised as introduction while also
  supplying conditional table-routing data for a future trusted supplement
  loader. Requirement records are review data and do not activate gameplay yet.
  Primary PDF text selection rejects extraction variants that mostly repeat a
  shorter clean variant, avoiding doubled contents/column text. Text visible in
  rendered artwork but absent from the PDF text layer is not fabricated; the
  reviewer must correct it manually until a visual OCR candidate workflow is
  implemented.
  Workbench artwork extraction stores raw embedded image candidates under the
  same source folder and keeps reviewed artwork names, categories, and notes in
  `reviewed_artwork` so useful illustrations can later be promoted into the
  user asset library. When a PDF exposes no embedded image objects, the
  extractor renders full PDF pages as `rendered_page` candidates for later
  crop/review work.
  Workbench session state retains the inner source-tree scroll, open page and
  category branches, selected blocks, and the active package asset/tool. Asset
  saves and mask/grid extraction reopen the same asset and compensate for DOM
  layout changes so the reviewer is not returned to the top of the module.
  Workbench scans can store both `pdf_page` and the offset-adjusted printed
  `source_page`; use `page_offset` when a PDF cover/front matter shifts the
  viewer page number away from the printed book page. The offset is editable
  after import; re-indexing, rescanning, and artwork re-extraction are not
  required merely to correct printed page references.

Home screen character UI:

- **Create character** is a collapsible `<details>` block (class picker labels
  above portraits; hover tooltips show rulebook summaries).
- The saved **roster list** scrolls after ~4 heroes (`max-height: 22rem`) so the
  column stays compact on screen.
- Expanded roster sheets show home-bank gold, banked XP rolls, stored gear, and
  nested **Rules & abilities** details without collapsing the selected row.
- **Party builder** uses four drag-and-drop marching-order slots fed from the
  roster (no duplicate checkbox list).

## Character gear transfer

- **In adventure:** `POST /api/sessions/{id}/advance` with `transfer_item` or
  `transfer_gold` (exploration mode only; both heroes must be alive).
- **Roster:** `POST /api/characters/{id}/transfer` with `target_character_id` and
  either `item_name` or `gold_amount`. Updates both character records immediately.
  Roster inventory is the stored-gear model; roster gold is home-bank gold.
- **Camp bank:** `deposit_bank_gold`, `withdraw_bank_gold`, and
  `deposit_party_bank_gold` session actions are available only while camped
  outside. The Camp panel and Home Screen Bank button open the same dialog.
- **TAG bank:** `CampaignState.tag_bank_accounts` is a separate settlement
  ledger for Tales from the Adventurers' Guild. TAG bank deposits/withdrawals,
  inheritance notes/transfers, and migration from roster gold plus matching
  session `bank_gold` are explicit player actions under `/api/campaign/tag/*`;
  the app does not silently spend TAG bank funds from the equipment shop or camp
  bank. Normal bank deposits pay TAG p.9's 10% fee; when Guild membership is
  enabled and `tag_guild_coffers_gp > 0`, the same ledger uses TAG p.68's free
  Guild storage rule instead. Guild-facing benefits use
  `tag_guild_benefits_active(campaign)` so the equipment discount, free martial
  arts training, free ledger deposits, cartographer bonus, resurrection funding,
  and availability reroll all suspend consistently when coffers reach 0 gp.
- **TAG troupe:** `CampaignState.tag_troupe_member_character_ids` stores the
  wider troupe roster, while `tag_troupe_active_character_ids` stores the current
  active party subset. The Home troupe manager can add/remove/list members and
  choose up to four active adventurers from troupe members only.
- **TAG settlements:** `CampaignState.tag_settlements` stores named TAG
  settlements with size modifier and notes. The current `settlement_name`,
  `settlement_size`, and `settlement_notes` remain the selected settlement used
  by availability/travel/service rules; `/api/campaign/tag/settlement` creates,
  selects, and deletes tracked settlements.
- **TAG closeout:** `CampaignState.tag_closeout_tasks` stores unresolved
  between-adventure prompts created by `record_adventure_complete(store,
  session)`. Real actions such as Guild loot share, Guild upkeep, Guild reroll
  reset, hidden-trove risk/recovery, and bank-robbery recovery resolve their
  matching task automatically; `/api/campaign/tag/closeout-task` can mark a
  task done when the player handled it manually.
- Shared logic lives in `src/app/engine/inventory.py` (carry limits, transfers).

## Session roster sync

On clean dungeon exit (`mode == complete`), `src/app/engine/roster_sync.py`
writes surviving heroes' gold, inventory, levels, spells, XP tallies, default
weapons, and filtered statuses back to `Character` records in SQLite. The UI
reloads `/api/characters` after completion, clears the active session id, and
returns to the home screen.

When an active session is camped outside, the session remains locked/resumable
but roster-visible hero fields are mirrored so home-screen services (heal,
equipment shop, party regroup) operate on current gold, Life, inventory, and
training state. Leaving to camp refreshes spells, prayers, rest, and per-foray
class resources while preserving the explored dungeon map and quest state.
Roster services for active heroes are blocked unless their session is camped
outside.

The frontend treats `session.camped_outside` as a separate Camp screen state, not
as a dungeon entrance tile. The camp screen hides dungeon exploration panels,
shows the large user-facing camp artwork slot, and gathers re-enter, abandon,
bank, shop, transfer, recovery/resurrection, and troupe-restricted party regroup
controls beside the active party sheets.

Default melee/missile weapons and combat swap live in `weapons.py` and
`random_dungeon.py` (`set_default_weapon`, `swap_weapon` actions).

## Equipment shop (between adventures)

`data/rules/equipment_shop.json` and `src/app/engine/equipment_shop.py` implement
the Expanded Edition pp.81-88 equipment buy list and listed/half-price resale
rules on the home screen. API:

- `GET /api/rules/equipment-shop?class_id=…` — catalog filtered by class
- `POST /api/characters/{id}/buy-equipment` — `{ item_key, quantity }`, with
  quantity defaulting to 1
- `GET /api/characters/{id}/sell-quote`
- `POST /api/characters/{id}/sell-item`

The shop is also exposed on the home rules list as `equipment_shop_table` (merged
into `/api/rules/tables`). Roster gold transfers ignore the 200gp dungeon cap.
When a hero is locked to an active session and camped outside, roster services
prepare a temporary character view with carried + banked gold so the shop spends
from the same home-bank pool and syncs the remaining total back to carried/banked
session fields. The frontend clamps quantity buys to the selected hero's
spendable gold and the API enforces the total price.

Map element GIFs and other assets resolve through a two-layer asset path:

```text
DATA_DIR/assets/      user-facing overrides and additions, backed up with game.db
assets/               bundled fallback assets inside the app/container
```

The backend serves these at:

```text
/assets/tiles/<tile>.gif
```

The `/assets/...` route checks `DATA_DIR/assets` first and then falls back to
bundled `assets`. This keeps built-in tiles/icons available while allowing
user-provided artwork, icons, tiles, and module assets to live in the appdata
folder.

Application page artwork uses `DATA_DIR/assets/Application Artwork` and is
declared in `data/rules/artwork_registry.json`. The Developer Artwork Manager
reads that registry, reports missing/present status, and links present files
through `/assets/...`. Map icons remain managed separately by the Icon Editor
under `DATA_DIR/assets/icons/user`.

Map element metadata is separate from image files. Starting elements are
`01-06`; generated elements use two d6 faces as `11-66`. Fill in `tiles.json`
as rows are validated from the rulebook.

Placement state stores the element key, grid-square origin, rotation,
rectangular footprint, editor cell size, image scale/offset calibration,
walkable mask, per-square cell-shape masks, and exits. Exits carry a local grid
coordinate, direction, kind, and optional dungeon-exit marker. Cell-shape masks
currently cover full, half-square, shallow-slope, vertical and horizontal
two-square long-slope, and curved-corner approximations; arbitrary vector masks
are not implemented yet.
User-facing exit labels are derived from direction and row order, then
recalculated after rotation during play. Exit direction is the side of the local
grid square, and `span` allows a single door or passage to cover multiple
adjacent square edges.
The random dungeon engine rotates candidate map elements and computes the origin
so the selected exit edge square lines up with the entry exit edge square.
Overlap checks use occupied walkable cells and reserve exit portals for every
unconnected door or passage, including inset doors with one or more blocked
throat squares before open map space. A newly placed element may connect to an
older reserved exit if its final connected walkable mask reaches that portal; the
engine then adds/uses a reciprocal exit on the new element while preserving
closed-door state until the player opens the door. If the candidate cannot
connect, truncation clips the new element before that portal so the older exit
remains usable later. If the rolled element still cannot be legally placed, the
engine tries the remaining generated map element keys in random order and logs
the skipped rolls/candidates when roll display is enabled. Only the placed
element receives a room-content roll. If every generated element fails, the
engine draws a 1x1 dead-end fallback so exploration does not hard-stop. Rotation
transforms walkable masks, cell-shape orientation, exits, and image calibration
offsets together. If an authored exit points back into the same placed element,
the engine refuses the move and reports the metadata issue instead of changing
the current tile to itself.

The current play model is tile-level plus Marching Order. Character sheets do
not yet store exact square coordinates inside a map element; that should be a
future tactical layer for authored maps, line-of-sight, or rulesets that need it.

## Quest State

Lady in White quests are stored as `SessionState.active_quest` and resolved in
`random_dungeon.py` through `quests.py` helpers. Combat completion updates boss,
item, peaceful, and slay-all objectives; accepted objectives and partial results
log `Quest progress:` lines so Summary mode preserves them. The frontend
`renderOngoingQuests()` mirrors backend turn-in checks with `questClaimStatus()`,
keeping the Claim button visible but disabled with the practical blocker the
backend will enforce. `questObjectiveRows()` feeds both the Ongoing Quests
journal and the clickable map quest marker, so objective/progress/turn-in/reward
status is consistent wherever the active quest is inspected. Epic Reward effects
live in the same session layer: Kerrak Dar is a temporary status that unlocks a
1-Clue Explore action, Enchanted Weapon is an adventure-only combat status, and
carried reward items use normal inventory/resale persistence. Book of Skalitos
uses the scroll-burn path with page-count inventory text; Arrow of Slaying uses a
combat item action and then normal combat cleanup if the encounter ends.

## Combat

`combat.py` resolves exploding-d6 attack/defense, morale, corridor rank rules,
and Expanded Edition p.146 round-0 initiative:

- **Attack immediately** — PC opening missile volley, then foe ranged, then melee.
- **Surprised / foes strike first** — foe ranged, PC ranged, foe melee, PC melee.
- **Reactions first** (chosen before any voluntary party action) —
  foe ranged, PC melee, foe melee (no PC opening volley).
- **Post-ranged economy** — PCs who shoot fight unarmed (−2) in the same round unless
  they drew a weapon; foes that used ranged spend their melee turn drawing unless
  they have natural attacks.

Strict p.146 encounter flow lives in `random_dungeon.py`: entering a tile with
living foes immediately opens combat round 0. The party then chooses **Check
Reactions** or an immediate party action (Fight Round, combat spell, attack item,
draw weapon, flee, or withdraw). Any voluntary party action before reactions are
resolved forfeits the Reaction roll; if the party is surprised, the mandatory
Reaction roll is made automatically before any party actions are offered. The
`start_combat` action remains only as a compatibility fallback for older saves
that were already paused at an encounter.

Reaction resolution records a short `Reaction outcome:` log entry for every
branch so Summary mode keeps the player-facing consequence: flee, peaceful,
bribe, Trade Information, Puzzle/Magic Challenge, Capture, fight, or fight to
the death. `fight_to_death` is carried through `CombatContext.suppress_morale`
so the normal vermin/minion half-strength morale check is skipped for that
encounter. Combat Focus renders the same outstanding choice as a compact
reaction outcome block beside the round controls, including current encounter
gold/weapons/clues for bribes and Trade Information.

Session flags `party_surprised`, `party_attacked_immediately`, and tile
`surprise_party` are set in `random_dungeon.py` (wandering ambush, secret-door
peek, immediate attack action). `weapons.py` supplies missile eligibility,
weapon-type modifiers, and `force_unarmed` melee selection.

`inventory.py` also implements bandage use (p.89, once per hero per adventure in
exploration), party-order carried-gold spending, even gold distribution on treasure
claim (200gp carry cap), and illusionary servant carry bonuses on the caster.

Special events and features are resolved in `random_dungeon.py` from
`dungeon_tables.json`. Event/Feature/Effect log prefixes are preserved in Summary
mode. Caverns/fungal environment tables are guarded by PDF row compliance tests;
choice-heavy cavemen/scout/miner/merchant/mycelial-warning rows keep their choice
state on the tile and expose clickable map-marker menus. Pending statue/puzzle-box
features keep their choice state on the tile and expose a distinct clickable map
marker that focuses the shared choice controls.

`combat_modifiers.py` implements two-step magic resistance (p.97): spell connect
vs base Level, then penetrate vs Level + MR tiers (`magic_resist`, `caster`,
`dragon` tags). `spells.py` uses `resolve_spell_effect` for offensive spells.

Monster specials in `combat.py` include troll regeneration (always logged as a
state effect when recovery happens or is blocked), held foes (Phantasmal
Binding), illusionary fog (suspend foe ranged/gaze, +2 Defense when fleeing),
specter swarm distraction, poisonous foe riders (named threat/save/extra damage
and lingering `Poisoned Lx` state), and illusionary sword (+L subdual melee with
turn decay).
Per-foe reaction tables live in `data/rules/monsters.json` and are shown on the
home screen via `GET /api/rules/monster-reactions` (not in `RULES_TABLE_ORDER`).
Variant encounter names that share a rules table, such as wandering, cavern, and
fungal foes, are mapped through `REACTION_NAME_ALIASES`; regression tests require
every indexed monster row to resolve to inline d6 rows 1-6 and validate core
combat-special metadata such as poison, MR, regeneration, vermin, and boss tags.

## Combat Focus (session UI)

During combat or when foes are present on the tile, `app.js` switches to **Combat
Focus** (`shouldUseCombatFocus`): tactical room map, command rail (Exits /
Encounter / Log), foe chips with hover/click trait summaries, hero chips with a
drawer for targets/abilities/spells/class tricks, and a slim action deck.
The encounter status line also summarizes active foe specials such as poison,
MR, regeneration, undead/holy interactions, dragon/construct traits, and multiple attacks when no
higher-priority reaction/bribe/trade prompt is active.
The encounter preview also renders a compact live rules reference for those specials,
so players can read the effect without relying on chip hover text. Undead chips
and action tooltips deliberately duplicate the key rules that affect immediate
choices: cleric full-Level Attack, holy water, Turn Undead, blessed shrine
bonuses, and sleep/illusion immunity.
Expected foe attacks are grouped per foe in the preview, so multi-attack foes show
one target list with the attack count instead of disconnected duplicate rows.
Cinema view optionally maximizes the map. The
legacy sidebar combat panel remains for layout fallbacks; most planning UI lives
in the hero drawer. Multi-target payloads (`attack_secondary_targets`,
`double_kick_targets`, `protective_incense_targets`, spell secondary foe ids)
are sent with `resolve_combat_round` from the drawer before Fight Round.

Unavailable combat actions must be represented consistently across the sticky
bar, Combat Focus deck, legacy combat panel, hero sheet, and token context menus:
the underlying button/menu item is disabled, the visual state is dimmed/blocked,
and the hover tooltip explains the rule reason. Disabled buttons are wrapped by
`syncButtonTooltip` so hover text still works even though the button itself is
not clickable.

Adventure logging is controlled by one UI mode. **Summary** hides rolls, lookup
detail, table-result plumbing, and modifier math while preserving round-summary
outcome lines plus state/effect lines such as curses, poison, healing, and buffs;
**Verbose** sends `show_rolls=true` and
`explain_math=true` so the engine includes rolls, table lookups, and math lines.
Door discovery uses this split too: Summary records the door result and outcome,
while Verbose also includes the 2d6 door roll and opening-method hint.
Fight Round summaries are generated by `combat_summary.py`; they should report
party hits, defeated foes, party Life loss, and regeneration blocks separately so
foe damage is not mistaken for a party hit.

Map-element exits may be inset from the outer footprint edge when the live tile
metadata represents a corridor bend or throat. Engine placement and frontend map
markers both trace from the exit anchor in its direction through connected
walkable/visible cells until the path leaves the visible element; that traced
portal cell, not the immediate adjacent cell, is used for movement, reciprocal
links, reserved-exit matching, and marker placement.

The placement fallback sequence is now: rotate to align an entry, truncate to
avoid overlap or reserved exits, try another generated element if no legal
placement remains, then use the 1x1 dead-end safety fallback only if every
generated element fails.

## Imported adventures

**Random Dungeon** grows the map procedurally during play. **AI Adventure** and
**PDF-authored** modules load a **complete room graph** from a manifest at session
start; the engine does not add tiles via d66 placement.

| Concern | Random | Imported |
|---------|--------|----------|
| `adventure_type` | `"random"` | `"imported"` |
| Map source | `random_dungeon.create_session()` | `adventure_session.create_session_from_manifest()` |
| Content authoring | Tables in `data/rules/` | `DATA_DIR/Adventures/{id}/adventure.json` (imports) + shipped `data/adventures/` defaults |
| AI / LLM | N/A | External only in v1 (copy-paste prompt + import UI) |
| Allowlists | N/A | `build_adventure_allowlists(rules_repo)` — same live rules for prompt, `GET /api/adventures/allowlists`, and import validation |
| Triggers | Procedural tables | Manifest `on_enter` / `on_search` via `adventure_runtime.py` |
| Fog of war | All placed tiles visible | Visited tiles only (`visited_tile_ids`) |

Key modules: `adventure_import.py`, `adventure_session.py`, `adventure_runtime.py`, `adventure_manifest.py`, `adventure_prompt.py`.

Full spec, playtest guide, and MVP limits: [`docs/AI_ADVENTURE_MODE.md`](AI_ADVENTURE_MODE.md).

## Source PDFs

The source PDFs stay local:

- `Rules/`
- `Adventures/`

They are ignored by git and Docker. Structured rule/adventure data derived from
them belongs in `data/rules/` or future `data/adventures/` manifests.
Every PDF in `Rules/` is an approved rules source for extraction. Engine-visible
rules still need structured data, player-facing reference coverage, and tests
before they are treated as implemented behavior.
