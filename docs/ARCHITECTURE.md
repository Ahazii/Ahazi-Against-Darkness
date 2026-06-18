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
- `src/app/engine/adventure_manifest.py` - import validation (`validate_adventure_manifest`)
- `src/app/engine/adventure_import.py` - install manifests under `data/adventures/`
- `src/app/engine/adventure_session.py` - `create_session_from_manifest()`
- `src/app/engine/adventure_runtime.py` - imported triggers and quest hooks
- `src/app/engine/adventure_prompt.py` - external LLM prompt builder
- `src/app/engine/adventure_allowlists.py` - allowlisted names for prompts and validation
- `src/app/engine/combat.py` - combat resolution
- `src/app/engine/combat_modifiers.py` - poison foes, blade poison, magic resistance
- `src/app/engine/monster_template_effects.py` - bestiary encounter_start/on_hit/per-turn template effects
- `src/app/engine/weapons.py` - missile eligibility and weapon-type attack modifiers from inventory
- `src/app/engine/magic_weapons.py` - magic weapon d6 type roll (p.163), +1 Attack bonus, class wield checks, resale formula
- `src/app/engine/subdual.py` - subdual damage and capture at 0 Life
- `src/app/engine/reactions.py` - reaction and morale rolls
- `src/app/engine/spells.py` - spell resolution and MR-aware target level
- `src/app/engine/scrolls.py` - scroll identification, burning, and wizard copy-to-spellbook
- `src/app/engine/magic_items.py` - charged wand/staff parsing, `use_magic_item` cast, charge consumption
- `src/app/engine/inventory.py` - item and gold transfer between heroes (session and roster)
- `src/app/engine/class_profiles.py` - class Life offsets, spell slots, level-up benefit notes
- `src/app/engine/experience.py` - XP awards, level-up application, spell-slot assignment
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

The frontend does not implement game rules. It renders state returned by the API
and sends action requests to the backend.

Home screen rule browsing:

- `GET /api/rules/tables` returns all keys from `dungeon_tables.json` except
  meta keys (`validation`, `open_items`, `ruleset_status`), plus merged
  `equipment_shop_table` rows from `equipment_shop.json`.
- `GET /api/rules/monsters` and `GET /api/rules/monster-reactions` feed the
  home **Rules tables** panel (bestiary spawn templates and per-foe reactions).
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

Map element GIFs live in:

```text
assets/tiles/
```

The backend serves these at:

```text
/assets/tiles/<tile>.gif
```

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
exploration), even gold distribution on treasure claim (200gp carry cap), and
illusionary servant carry bonuses on the caster.

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
| Content authoring | Tables in `data/rules/` | `data/adventures/{id}/adventure.json` |
| AI / LLM | N/A | External only in v1 (copy-paste prompt + import UI) |
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
