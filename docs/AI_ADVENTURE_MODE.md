# AI Adventure Mode — Design & Implementation Plan

**Status:** Phases 1–5 MVP implemented (validate, prompt, import, play imported adventures).  
**Audience:** Developers, contributors, and anyone authoring or importing AI-generated adventures.

This document is the **single source of truth** for the **AI Adventure** play mode. It records product decisions, architecture boundaries, file formats, validation rules, and the implementation sequence. Read this before writing schema code, UI, or engine hooks.

---

## 1. Summary

**AI Adventure** is a second adventure mode alongside **Random Dungeon** (the only playable mode today).

| Mode | Map | Content source | Rules & dice |
|------|-----|----------------|--------------|
| **Random Dungeon** | Procedural growth (d66 tiles, tables) | Engine + `data/rules/` | Engine |
| **AI Adventure** | Pre-authored **open graph** loaded at session start | External LLM → strict JSON manifest | Engine (unchanged) |

**Core principle:** The external AI generates **narrative and layout references**. The game engine generates **all mechanics** (combat, reactions, dice, treasure resolution, quests mechanics, roster sync). The AI must never output HP, attack rolls, custom stat blocks, or house rules.

**v1 interaction model:** Copy-paste prompt to any external LLM (ChatGPT, Claude, Gemini, Copilot, Grok, local LLM). No in-app LLM API in v1.

---

## 2. Product goals

1. Let the player specify adventure **parameters** (theme, difficulty, length, style, map environment, boss type, party level range).
2. Produce a **tightly defined prompt** the player copies into an external AI.
3. Accept a **strictly defined JSON** adventure file via paste or file upload.
4. **Validate** the JSON against schema and Four Against Darkness allowlists.
5. **Play** the adventure using existing systems (`SessionState`, combat, reactions, traps, treasure, quests, exit flow).
6. **Save** adventure modules under `DATA_DIR/Adventures/` (beside `game.db`) and **export** as a JSON package for re-import.
7. **Save games** in the normal save list with an **AI Adventure** indicator.

---

## 3. Locked product decisions

These decisions are **final for v1 planning**. Do not implement alternatives without updating this document.

### 3.1 Map topology and exploration

- The manifest defines a **full room graph** (branching allowed; not a linear railroad).
- The map does **not** dictate play order: players discover objectives by exploring.
- **Fog of war:** Unvisited rooms are **not visible** on the map until the party enters them (same exploration model as random mode).
- Movement is only along **defined exits** (doors, passages, etc.) with statuses the engine already supports (`open`, `closed`, `locked`, …).
- No teleportation across the graph unless a future manifest trigger explicitly wires an existing engine action (out of v1 scope).

### 3.2 Encounter and event triggers

Rooms may attach **multiple triggers** with different timings. v1 schema must support at least:

| Trigger | When it fires |
|---------|----------------|
| `on_enter` | Party enters the room (first time or every time — see per-trigger `once` flag) |
| `on_search` | Successful search on this tile |
| `on_treasure` | Treasure claim / treasure interaction on this tile |
| `on_feature` | Special feature resolution (statue, puzzle box, etc.) — when wired |

Each trigger references **allowlisted** engine content (foe names, trap keys, event keys, item names), not free-form mechanics.

### 3.3 Storage and packages

- **Bundled modules** (shipped with the app): `data/adventures/{adventure_id}/adventure.json` — e.g. `crypt-of-whispers`.
- **Installed modules** (runtime, beside `game.db`): `DATA_DIR/Adventures/{adventure_id}/adventure.json` — on Tower this is `\\TOWER\appdata\ahazi-against-darkness\Adventures\`.
- On startup the app **seeds** bundled adventures into `DATA_DIR/Adventures/` when missing (same pattern as rules DB beside `game.db`).
- Optional metadata sidecar: `adventure.meta.json` (import timestamp, prompt parameters, validator version — not required for play).
- **Export:** Single downloadable `.json` file (the adventure module). User can re-import elsewhere.
- **Evolution:** When custom images or multiple files are needed, add `.zip` packages **without changing the inner schema** (zip contains `adventure.json` + `assets/`). See §8.

### 3.4 Saved games

- Imported AI adventures use the **same session save** machinery as random mode.
- Saved games list shows an **AI Adventure** (or similar) badge when `adventure_type === "imported"`.
- Session metadata should record `adventure_id` and module `schema_version` for support/debug.

### 3.5 Quest and victory

- Every AI adventure manifest includes a **defined quest** (story objective).
- **Winning** requires:
  1. Quest marked **complete** per manifest rules (e.g. boss defeated, item obtained, room reached).
  2. Party **leaves the dungeon** or **reaches the designated exit room** and uses the normal exit flow (equivalent to random mode: camp outside / complete adventure → roster sync).
- Quest completion alone does **not** end the adventure; exit is required, matching random-mode expectations.

### 3.6 Content allowlists (Four Against Darkness)

- AI output must use **only names the engine knows**.
- **Runtime source of truth:** `build_adventure_allowlists(rules_repo)` in `adventure_allowlists.py`, using the same `RulesRepository` as validation (`DATA_DIR/rules` overrides packaged `data/rules/` on Tower).
- **Prompt and validator stay in sync:** the prompt builder always embeds live allowlists — it does **not** read packaged `allowlists.json` at runtime.
- **`allowlists.json`** is an exported snapshot for docs, diffing, and offline tools (`tools/export_adventure_allowlists.py`). Regenerate after rules changes; do not hand-edit.
- Validator **rejects** unknown references with actionable messages and a grouped **`error_summary`** (import UI shows summary + capped detail list).
- Tone/flavor text may be original; **mechanical references** must be allowlisted.

**Allowlist payload (v1):**

| Key | Purpose |
|-----|---------|
| `schema_enums` / top-level mirrors | Closed sets: `exit_directions` (cardinal only), `exit_kinds`, `exit_statuses`, `trigger_when`, `source_types`, `quest_complete_when_types`, `environments` |
| `monster_spawn_names` | All spawn-table foe names from `monsters.json` |
| `boss_spawn_names` | Boss-table names (UI boss picker) |
| `foe_spawn_names` | Union used for encounters and `quest.complete_when.boss_name` |
| `monsters_by_table` | Spawn names grouped by table key (minions, vermin, …) |
| `equipment_items` / `equipment_by_category` | Shop item names |
| `trap_keys` / `traps_by_table` | Trap keys per environment table |
| `special_event_keys` / `events_by_table` | Event keys per environment table |
| `tile_keys` | Map element keys (`01`–`06`, `11`–`66`) |
| `environment_packs` | Per-environment `foe_names`, `trap_keys`, `special_event_keys` |
| `for_environment` | Same as one pack when prompt is built (matches form `environment`) |

**API:** `GET /api/adventures/allowlists?environment=dungeon` returns the live payload for debugging.

### 3.7 Environments (v1)

Per-room or adventure-default environment:

- `dungeon`
- `caverns`
- `fungal_grottoes`

**Not in v1:** overland, hex map, Fortress-style wilderness (deferred until outdoor navigation exists — see `docs/ROADMAP.md` Phase 4).

### 3.8 PDF-authored adventures (parallel track)

`docs/CONTENT_PIPELINE.md` describes **human-reviewed manifests extracted from owned PDFs**. AI Adventure uses the **same manifest schema and engine path** where possible; only the **authoring source** differs (`source.type`: `"ai"` vs `"pdf"`). PDF import remains a separate content-creation workflow.

---

## 4. Architecture

```
┌──────────────────────┐
│  Setup UI            │  theme, length, boss, levels, …
│  "AI Adventure"      │
└──────────┬───────────┘
           │ builds
           ▼
┌──────────────────────┐
│  Prompt text         │  schema + allowlists + example + rules for LLM
│  (copy to clipboard) │
└──────────┬───────────┘
           │ user runs external LLM
           ▼
┌──────────────────────┐
│  adventure.json      │
└──────────┬───────────┘
           │ import / validate
           ▼
┌──────────────────────┐
│  data/adventures/    │
│  {id}/adventure.json │
└──────────┬───────────┘
           │ start session
           ▼
┌──────────────────────┐
│  SessionState        │  adventure_type: "imported"
│  MapState (full graph)│  no procedural tile growth
└──────────┬───────────┘
           │ POST …/advance
           ▼
┌──────────────────────┐
│  RandomDungeonEngine │  existing rules, dice, combat, reactions
│  (or ImportedEngine) │
└──────────────────────┘
```

### 4.1 What the AI generates

| Yes | No |
|-----|-----|
| Title, synopsis, room titles/descriptions | HP, AC, attack bonuses |
| Room graph (ids, exits, connections) | Dice roll results |
| NPC flavor names and dialogue hooks | Custom monster stat blocks |
| References to allowlisted foe names + counts | New rules or reaction keys |
| Trap/event **keys** from tables | Arbitrary item mechanics |
| Treasure **templates** (gold, item names) | Spell outcomes |
| Quest objective text and completion conditions | |

### 4.2 What the engine owns

- All dice rolls, combat, reactions, morale, fleeing, death, capture.
- Spawning `EnemyState` from bestiary rows referenced by name.
- Trap/event resolution from table keys.
- Treasure claim, carry limits, roster sync on clean exit.
- Quest state machine (`ActiveQuestState`) driven by manifest completion rules.

### 4.3 Schema hook in code (today)

```python
# src/app/schemas.py (existing)
SessionState.adventure_type: Literal["random", "imported"]
```

AI Adventure sessions use `adventure_type="imported"`. `adventure_id` matches the module folder name. Random sessions use `adventure_type="random"` and `adventure_id="random"`.

`POST /api/sessions` currently rejects non-random adventures (`main.py`). Implementation will add a manifest-backed path.

---

## 5. Player flows

### 5.1 Create prompt

1. Player selects **AI Adventure (build prompt)** on setup.
2. Player fills parameters (§6).
3. App displays **prompt preview** + **Copy prompt** button.
4. Player pastes prompt into external LLM.

The generated prompt includes an **authoring checklist**, **common mistakes** (invented foe names, missing `tile_key`, diagonal exits, markdown fences, stale cached allowlists, copying example tile chains, text that does not match map geometry, wrong portal directions, using dungeon tiles for entrance, etc.), **min/max room counts**, inline **room/npc templates**, **live allowlists** (built from your server rules), a **TILE CATALOG** (`shape_summary`, `walkable_map`, `native_exit_ports` with edge positions, and `tile_role` entrance vs dungeon per `tile_key` from `tiles.json`), a **SKELETON TO FILL** (pre-wired room graph with assigned `tile_key`s — the LLM must keep ids, exits, and tile keys), a **per-environment foe/trap/event subset**, and the **crypt-of-whispers** example. The LLM must return raw JSON only.

`POST /api/adventures/ai/skeleton` returns the same skeleton JSON for debugging; **Copy skeleton JSON** in the UI copies it without the full prompt wrapper.

### 5.2 Import module (not yet implemented)

1. Player pastes JSON or uploads `{id}.json`.
2. Validator runs (§7).
3. Preview: title, synopsis, room count, quest summary, validation warnings.
4. On success: write `data/adventures/{id}/adventure.json` (and optional `.meta.json`).
5. Adventure appears in adventure picker as **playable**.

### 5.3 Play (not yet implemented)

1. Player selects party + imported adventure → `POST /api/sessions`.
2. Engine calls `create_session_from_manifest()` (name TBD): builds full `MapState.tiles[]`, sets quest, entrance room, environments.
3. Play proceeds like random mode: explore, fight, search, rest, etc.
4. Triggers fire per room definitions.
5. On quest complete + exit: same roster persistence as random clean exit.

### 5.4 Remove installed module

1. Home screen → adventure list shows installed modules with a **Remove** button when `removable` is true (`GET /api/adventures` — installed copy under `DATA_DIR/Adventures/`).
2. Confirm removal. API: `DELETE /api/adventures/{adventure_id}`.
3. Deletes `DATA_DIR/Adventures/{adventure_id}/` (manifest + optional meta). Does **not** delete saved games; end in-progress sessions for that module first (409 if any remain).
4. Shipped defaults under `data/adventures/` are never deleted from the image. If a bundled copy exists (e.g. `crypt-of-whispers`), the module may still appear in the list after removal; startup seeding can copy it back into `DATA_DIR/Adventures/` when missing.

### 5.5 Export / share (not yet implemented)

1. From adventure library UI: **Export** → download `adventure.json`.
2. Another installation: **Import** → validate → install under `data/adventures/`.

---

## 6. Prompt parameters (UI form)

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `theme` | Setting / mood | "undead crypt", "goblin warren" |
| `difficulty` | Foe density and levels hint | `easy` \| `standard` \| `hard` |
| `length` | Target room count | `short` (6–8), `medium` (10–14), `long` (16–20) |
| `style` | Narrative tone | `grim`, `pulpy`, `mystery` |
| `environment` | Default environment | `dungeon`, `caverns`, `fungal_grottoes` |
| `map_type` | Same as environment for v1; reserved for overland later | |
| `boss_type` | Allowlisted major foe name | `Young Dragon`, `Necromancer`, … |
| `party_level_min` / `party_level_max` | Recommended hero levels | 1–3 |

Prompt output must include:

1. JSON Schema summary or link to `data/adventures/schema/adventure_manifest.v1.json`
2. **Live allowlists** from `build_adventure_allowlists(repo)` — same data as `GET /api/adventures/allowlists` and the import validator (not a stale `allowlists.json` snapshot)
3. **Environment pack** (`for_environment`) highlighting foes/traps/events for the selected environment
4. Minimal **example adventure** (`data/adventures/examples/`)
5. Instruction: **Return only valid JSON. No markdown fences. No commentary.**

---

## 7. Validation rules

Validation runs on import and in CI (`tests/test_adventure_manifest.py`).

### 7.1 Structural

- `schema_version` must be supported (start with `1`).
- `id` matches `^[a-z0-9]+(-[a-z0-9]+)*$` and folder name.
- Required top-level keys: `id`, `title`, `synopsis`, `schema_version`, `entrance_room_id`, `exit_room_id`, `quest`, `rooms`, `ending`.
- `rooms` is non-empty; each room has unique `id`.

### 7.2 Graph

- `entrance_room_id` and `exit_room_id` reference existing rooms.
- Every exit `to` references an existing room id.
- Graph is **connected**: all rooms reachable from entrance via undirected edges.
- `exit_room_id` is reachable from entrance (player must be able to finish).
- **Warnings** (import still allowed): one-way exit links without a reciprocal exit on the target room — the engine repairs layout at play time, but maps may misalign.
- Recommended: at least one path from entrance to boss/quest target without requiring undefined keys (warn if soft-gated).

### 7.3 Allowlists

For each reference field, value must exist in **live** allowlists from `build_adventure_allowlists(rules_repo)`:

- `rooms[].tile_key` → `tile_keys`
- Each `rooms[].exits[].direction` must appear in that room's **native exits** from `tiles.json` (see `build_tile_catalog()` / `GET /api/adventures/tiles`). Extra surface/leave portals on entrance and exit rooms are added at play time on an unused direction.
- Each `rooms[].exits[].kind` must match the native portal kind (`door` vs `passage`) for that direction on the chosen tile.
- Entrance/exit rooms should use **entrance surface** tiles (`01`–`06`); interior rooms use dungeon tiles (`11`–`66`).
- `rooms[].exits[].direction` → `exit_directions` only (`north`, `south`, `east`, `west` — no diagonals)
- `rooms[].exits[].kind` / `.status` → `exit_kinds` / `exit_statuses`
- `rooms[].encounter.foes[].name` and `quest.complete_when.boss_name` → `foe_spawn_names`
- `rooms[].trap.key` → `trap_keys` (environment-specific subset in `for_environment`)
- `rooms[].special_event.key` → `special_event_keys`
- `treasure.items[]` → `equipment_items`
- `quest.complete_when` type → `quest_complete_when_types`

Unknown references = **hard error** on import. The API returns `errors` (full list), `error_summary` (grouped checklist), and `warnings` (non-blocking, e.g. missing reciprocal exits).

### 7.4 Quest and victory

- `quest` block present with `objective_text` and `complete_when`.
- `complete_when` is one of: `boss_defeated`, `item_collected`, `room_reached`, `peaceful_count` (extensible enum — document additions here).
- `exit_room_id` required; party must use normal dungeon exit from that tile (or adjacent policy — implement to match random entrance/exit UX).

### 7.5 AI safety

- Reject nodes containing stat-like fields (`hp`, `attack`, `level` on custom objects) outside allowlisted foe references.
- Reject `rules`, `dice`, `roll` top-level keys.

---

## 8. File formats

### 8.1 v1 — Single JSON file

```
data/adventures/
  README.md
  allowlists.json              # generated; do not hand-edit
  schema/
    adventure_manifest.v1.json # JSON Schema
  examples/
    crypt-of-whispers/
      adventure.json
  {adventure_id}/
    adventure.json               # playable module
    adventure.meta.json          # optional
```

**Export package (v1):** the same `adventure.json` bytes, downloaded as `adventure.json` (single-file roundtrip for re-import).

### 8.2 v2 — Zip package (future)

```
{campaign_id}.zip
  adventure.json      # identical schema to v1
  assets/             # optional images, author notes
    cover.png
```

Import extracts to `data/adventures/{adventure_id}/`. Validator only reads `adventure.json` until asset support is added.

---

## 9. Manifest schema (v1 draft)

> **Implementation note:** Formal JSON Schema lives at `data/adventures/schema/adventure_manifest.v1.json` (to be added in Step 1). This section defines semantics for authors and implementers.

### 9.1 Root document

```json
{
  "schema_version": 1,
  "id": "crypt-of-whispers",
  "title": "Crypt of Whispers",
  "synopsis": "A branching crypt beneath the old chapel…",
  "source": {
    "type": "ai",
    "parameters": {
      "theme": "undead crypt",
      "difficulty": "standard",
      "length": "medium",
      "style": "grim",
      "environment": "dungeon",
      "boss_type": "Wraith",
      "party_level_min": 2,
      "party_level_max": 4
    }
  },
  "recommended_levels": [2, 4],
  "default_environment": "dungeon",
  "entrance_room_id": "chapel-entry",
  "exit_room_id": "surface-stairs",
  "quest": { },
  "npcs": [ ],
  "rooms": [ ],
  "ending": { }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `schema_version` | yes | Integer; currently `1` |
| `id` | yes | Stable slug; directory name |
| `title` | yes | Display name |
| `synopsis` | yes | Player-facing blurb (no PDF verbatim text) |
| `source` | yes | `type`: `"ai"` \| `"pdf"` \| `"hand"`; optional `parameters` or `source_pdf` |
| `recommended_levels` | yes | `[min, max]` hero levels |
| `default_environment` | yes | Default for rooms without override |
| `entrance_room_id` | yes | Starting tile |
| `exit_room_id` | yes | Victory exit tile (leave dungeon here) |
| `quest` | yes | See §9.2 |
| `npcs` | no | Flavor NPCs tied to rooms |
| `rooms` | yes | See §9.3 |
| `ending` | yes | Victory/defeat narrative text |

### 9.2 Quest block

```json
{
  "key": "defeat_boss",
  "objective_text": "Destroy the Wraith binding the crypt.",
  "giver_room_id": "chapel-entry",
  "complete_when": {
    "type": "boss_defeated",
    "boss_name": "Wraith",
    "room_id": "ossuary-throne"
  }
}
```

| `complete_when.type` | Meaning |
|----------------------|---------|
| `boss_defeated` | Named boss slain in `room_id` (or anywhere if `room_id` omitted) |
| `item_collected` | Party holds `item_name` |
| `room_reached` | Party enters `room_id` |
| `peaceful_count` | N peaceful encounters (engine counter) |

Engine maps this to `ActiveQuestState` at session start. `completed` flips when condition met; session wins only after exit flow at `exit_room_id`.

### 9.3 Room node

```json
{
  "id": "ossuary-hall",
  "tile_key": "22",
  "title": "Ossuary Hall",
  "description": "Bones line the walls…",
  "environment": "dungeon",
  "exits": [
    {
      "id": "ossuary-hall-north",
      "direction": "north",
      "to": "ossuary-throne",
      "kind": "door",
      "status": "closed"
    }
  ],
  "triggers": [
    {
      "when": "on_enter",
      "once": true,
      "encounter": {
        "foes": [{ "name": "Skeletons", "count": 4 }]
      }
    },
    {
      "when": "on_search",
      "once": true,
      "log": "A hidden niche holds old coins.",
      "treasure": { "gold": 15, "items": [] }
    }
  ],
  "trap": { "key": "pit", "level": 3 },
  "special_event": null,
  "starts_resolved": false
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | yes | Unique graph node id |
| `tile_key` | yes | Map element from `tiles.json` (layout/footprint) |
| `title` | yes | Room name in UI |
| `description` | yes | Flavor text on enter |
| `environment` | no | Overrides adventure default |
| `exits` | yes | Connections; `to` = target room id |
| `triggers` | no | List of timed events (§9.4) |
| `trap` | no | Allowlisted trap key + level |
| `special_event` | no | Allowlisted feature/event |
| `starts_resolved` | no | If true, foes already cleared (story state) |

**Layout:** Engine maps `tile_key` → footprint, walkable mask, and art from `tiles.json` (same as random mode). AI does **not** author grid coordinates in v1.

### 9.4 Trigger object

```json
{
  "when": "on_enter",
  "once": true,
  "encounter": { "foes": [{ "name": "Goblins", "count": 3 }] },
  "treasure": null,
  "special_event": null,
  "log": null
}
```

| `when` | Engine action |
|--------|----------------|
| `on_enter` | On party entering tile (respect `once`) |
| `on_search` | After successful search on tile |
| `on_treasure` | When treasure claimed / generated on tile |
| `on_feature` | Special feature resolution |

### 9.5 NPC (optional)

```json
{
  "id": "broken-acolyte",
  "name": "Brother Cade",
  "room_id": "chapel-entry",
  "description": "A frightened acolyte hides behind a pew.",
  "dialogue": "The Wraith… it took them all."
}
```

NPCs are **narrative only** in v1 unless later wired to events.

### 9.6 Ending

```json
{
  "victory_text": "You climb into daylight as the crypt falls silent behind you.",
  "defeat_text": "The crypt claims another party."
}
```

Shown when adventure completes or party wipes (wording TBD in UI).

---

## 10. Allowlist export

**Tool:** `tools/export_adventure_allowlists.py`  
**Output:** `data/adventures/allowlists.json` (snapshot for docs/CI — **not** used at runtime for prompts)

**Runtime builder:** `build_adventure_allowlists(repo, environment=…)` in `adventure_allowlists.py`

Contents (snapshot mirrors runtime):

| Key | Source |
|-----|--------|
| `exit_directions`, `exit_kinds`, `exit_statuses`, … | Schema enums (shared with validator) |
| `monster_spawn_names` | `data/rules/monsters.json` spawn tables |
| `boss_spawn_names` | Boss tables in `monsters.json` |
| `foe_spawn_names` | Union of monster + boss spawn names |
| `monsters_by_table` | Spawn names grouped by table key |
| `tile_keys` | `data/rules/tiles.json` |
| `equipment_items` / `equipment_by_category` | `data/rules/equipment_shop.json` |
| `trap_keys` / `traps_by_table` | Trap tables in `dungeon_tables.json` |
| `special_event_keys` / `events_by_table` | Special event tables |
| `environment_packs` / `for_environment` | Per-environment foe/trap/event subsets |
| `quest_keys` | Quest table keys |
| `environments` | `dungeon`, `caverns`, `fungal_grottoes` |

Regenerate the snapshot when rules data changes: `python tools/export_adventure_allowlists.py`

---

## 11. UI surfaces (planned)

| Surface | Purpose |
|---------|---------|
| Setup: adventure type | Random Dungeon \| AI Adventure |
| AI parameters form | §6 fields |
| Prompt preview + copy | External LLM input |
| Import adventure | Paste / upload JSON |
| Adventure library | List modules in `data/adventures/`; export button |
| Saved games badge | "AI Adventure" on `imported` sessions |
| Rules reference entry | Player-facing summary (after implementation) |

---

## 12. Engine work (planned)

| Component | Responsibility |
|-----------|----------------|
| `adventure_manifest.py` | Parse, validate, normalize |
| `create_session_from_manifest()` | Build `SessionState` + full `MapState` |
| Trigger dispatcher | On explore/search/claim, run room `triggers[]` |
| Quest adapter | Manifest `quest` → `ActiveQuestState` |
| Victory checker | Quest complete + at `exit_room_id` + exit intent |
| `GET /api/adventures` | List random + installed modules (`playable: true` when valid) |
| `POST /api/adventures/import` | Validate + write files |
| `GET /api/adventures/{id}/export` | Return JSON package |

**Explicit non-goals for v1:**

- Procedural room generation during play
- In-app LLM API calls
- Overland / hex maps
- Custom foe stat blocks in JSON
- AI-authored walkable geometry

---

## 13. Implementation phases

Execute in order. Do not skip validation (Phase 0–1).

| Phase | Deliverable | Playable? |
|-------|-------------|-----------|
| **0** | This document + schema file + example JSON | No |
| **1** | `adventure_manifest.py` validator + `tests/test_adventure_manifest.py` + CLI | **Validate only** |
| **2** | `export_adventure_allowlists.py` + `allowlists.json` | No |
| **3** | Prompt builder UI (copy only) | **Build prompt in app** |
| **4** | Import UI + install to `data/adventures/` | **Import in app** |
| **5** | `create_session_from_manifest()` + branching MVP | **Yes** |
| **6** | Quest completion + exit + roster sync | **Yes** |
| **7** | Save-game AI badge + export JSON | **Yes** |
| **8** | NPC polish, more trigger types, zip packages | Optional |

**MVP definition:** Import a branching dungeon JSON, play through with fog of war, complete quest, exit to surface, roster saves, module exportable.

### What you can do today (Phases 1–5 MVP)

**Build → import → play:**

1. Adventure → **AI Adventure (build prompt)** → generate and copy prompt.
2. Paste LLM JSON in **Import adventure JSON** → **Validate** → **Import** → **Export adventure.json** (optional backup).
3. Select the imported adventure (e.g. **Crypt of Whispers (imported)**) → **Start Session**.

Pre-installed example: `crypt-of-whispers` (from `data/adventures/examples/`).

**Win flow:** complete the quest objective (e.g. slay the Wraith), then leave via the dungeon exit on the exit room.

Saved games show **AI Adventure** when `adventure_type` is `imported`. Map uses fog of war (visited tiles only).

### Playtest guide (Crypt of Whispers)

Pre-installed module: `data/adventures/crypt-of-whispers/adventure.json` (copy of the golden example).

1. Home → Adventure → party → **Crypt of Whispers (imported)** → **Start Session**.
2. You begin in **Ruined Chapel**. Open closed doors before moving through them.
3. Explore branches; `on_enter` triggers spawn fights (e.g. Goblins, Skeletons/Zombies, Wraith).
4. **Quest:** destroy the **Wraith** in **Throne of Bones**.
5. **Win:** after the log shows the quest complete, go to **Stairs to Daylight** and use the **dungeon exit** (complete adventure, not camp outside).

Alternate path: **AI Adventure (build prompt)** → external LLM → Import JSON → select your module → play.

CLI validation (optional): `python tools/validate_adventure_manifest.py path/to/adventure.json`

### Implementation map (Phases 1–5)

| Area | Location |
|------|----------|
| Validator | `src/app/engine/adventure_manifest.py`, `tools/validate_adventure_manifest.py` |
| Allowlists | `src/app/engine/adventure_allowlists.py`, `tools/export_adventure_allowlists.py`, `data/adventures/allowlists.json` (snapshot) |
| Allowlists API | `GET /api/adventures/allowlists` |
| Prompt builder | `src/app/engine/adventure_prompt.py`, `GET/POST /api/adventures/ai/*` |
| Import/install | `src/app/engine/adventure_import.py`, `POST /api/adventures/validate`, `POST /api/adventures/import` |
| Session bootstrap | `src/app/engine/adventure_session.py` → `create_session_from_manifest()` |
| Triggers / quest | `src/app/engine/adventure_runtime.py`, `src/app/engine/adventure_foes.py` |
| Engine hooks | `src/app/engine/random_dungeon.py` (imported enter/search/complete guards) |
| UI | `src/app/static/index.html`, `app.js` (prompt, import, fog of war, adventure picker) |
| Tests | `tests/test_adventure_manifest.py`, `tests/test_adventure_allowlists.py`, `test_adventure_prompt.py`, `test_adventure_import_play.py` |

### Home UI tooltips (AI Adventure panel)

All AI Adventure controls expose browser hover hints via `AI_ADVENTURE_TOOLTIPS` in `app.js` (`applyAiAdventureTooltips()` runs on setup load and after defaults load):

| Control | Hint covers |
|---------|-------------|
| Theme, Style | Prompt flavour text for the external LLM |
| Difficulty, Length | Balance and room-count band |
| Environment, Boss type | Allowlisted environment and major-foe hint |
| Min/Max level | Party level band for authored balance |
| Generate / Copy prompt | Build and copy the LLM prompt |
| Import JSON textarea | Paste raw `adventure.json` |
| Validate / Import / Upload | Schema check, install, file load |
| Overwrite checkbox | Replace same `adventure_id` |

The adventure dropdown and map-size selector also have setup tooltips (`SETUP_TOOLTIPS.adventureSelect`, `mapBounds`).

### Exploration command bar (play UI)

During **exploration**, a command field appears below the session log (random and imported adventures). Type a command and press **Enter** or **Go**. Exit numbers match the map labels (**North 1**, **East 2**, compact **N1**, **E2**).

| Command | Action |
|---------|--------|
| `look` / `l` | Log room title, description, exits, treasure/trap hints (`action: look`) |
| `exits` | List numbered exits visible from the current tile (client-side) |
| `go north 1` / `n1` / `north1` | Move through that exit (open doors/passages only) |
| `open west 2` / `open w2` | First available hero tries the door (lock-pick, bash, etc.) |
| `listen east 1` | Listen at a closed door |
| `search` | Search the room (imported: manifest `on_search` triggers) |
| `claim` | Claim treasure |
| `fight` | Start combat when foes are present |
| `rest` | Rest in the room |
| `help` | Show command summary in the log |

Hover the input for a short hint line; `SETUP_TOOLTIPS` / `EXPLORATION_COMMAND_HINT` in `app.js`.

**After combat:** the engine repeats the room title, description, and any unclaimed treasure at the end of the combat log so you do not need to scroll back past fight rounds.

**Imported adventures:** combat no longer rolls procedural dungeon treasure (only manifest triggers). Search **before** claiming if a room has both combat loot and `on_search` treasure — or reload after deploy so `repair_stuck_imported_treasure` can unstick a bad claim state.

### MVP limits (known gaps)

These are intentional shortcuts for the first playable import; see Phase 6–8 for follow-up.

| Topic | Current behavior | Planned |
|-------|------------------|---------|
| Search | Manifest `on_search` triggers only; skips procedural Search table | Optional hybrid per room |
| Combat treasure | Imported fights no longer roll procedural post-combat treasure (manifest `on_search` / triggers only) | — |
| `on_treasure` | Not wired on treasure claim yet | Phase 8 |
| Quest giver | Boss-kill sets `quest.completed`; no return-to-giver step | Optional narrative at giver tile |
| Victory | Quest complete **and** dungeon exit from `exit_room_id` | Same; roster sync uses existing complete flow |
| Room layout | Auto-placed graph from BFS + portal snap + walkable truncation (same carving as procedural placement) | No hand-tuned coordinates in v1 |
| Doors | Manifest `closed`/`locked` doors get fixed `door_type` (no procedural illusion/iron roll); reciprocal passage links do not force doors open | Locked doors may need richer rules later |
| Export | `GET /api/adventures/{id}/export` + **Export** button (Setup list + import preview) | Zip packages later |
| NPCs | First visit to an NPC's room logs description + dialogue in the session log | Full dialogue UI in Phase 8 |
| PDF import | Same schema; extraction workflow not automated | Phase 3B |
| Post-combat recap | Room description + treasure hint repeated in log after combat | — |
| Command bar | Text commands for look / go / open / search / claim (see §13) | More verbs, combat-mode commands |

### Remaining phases (6–8)

| Phase | Status | Notes |
|-------|--------|-------|
| **6** | Partial | Quest + exit work; epic rewards / claim-at-giver not imported-specific |
| **7** | Partial | Export JSON from Setup; save list badge polish |
| **8** | Open | `on_treasure`, full NPC UI, zip packages |

## 14. Testing strategy

| Layer | Tests |
|-------|--------|
| Schema | `tests/test_adventure_manifest.py` — golden `examples/` fixtures, graph errors, allowlist errors, tile native-exit checks |
| Tile catalog / skeleton | `tests/test_adventure_skeleton.py` — skeleton validates, tile catalog, imported door type, portal alignment |
| Allowlists | Snapshot or count checks vs rules files |
| Session bootstrap | Manifest → `MapState` tile count, exits, entrance id |
| Integration | `tests/test_adventure_import_play.py` — import API, session bootstrap, exit wiring, layout |

API tests that touch `DATA_DIR` use the shared `client` fixture in `tests/conftest.py` (isolated temp `DATA_DIR` + `game.db` per test). Do not import `app.main` at module scope in new API tests — use that fixture instead.

Random dungeon tests remain unchanged; imported mode adds parallel test module.

---

## 15. Copyright and content

- Store **concise mechanical data** and original narrative text.
- Do **not** embed long verbatim passages from copyrighted PDFs in manifests or prompts.
- AI-generated modules are **player-local** content under `data/adventures/`.
- Prompt instructs LLM to use **Four Against Darkness tone** and **allowlisted names** only.

---

## 16. Related documents

| Document | Relationship |
|----------|--------------|
| `docs/ROADMAP.md` | Phase 3 — Adventure Manifests + AI Adventure track |
| `docs/CONTENT_PIPELINE.md` | PDF extraction pipeline; shares manifest schema |
| `docs/ARCHITECTURE.md` | Engine overview; links here for imported sessions |
| `docs/RULE_COVERAGE.md` | Coverage status for imported adventures |
| `data/adventures/README.md` | Directory layout and quick start |

---

## 17. Open implementation details (not product blockers)

Track during Step 1 implementation:

- Exact mapping from manifest exits to `ExitState` ids for reciprocal links.
- Whether `on_enter` with `once: false` re-fires on re-entry.
- Search/trap defaults on imported tiles vs random `_seed_tile_features`.
- `AdventureDescriptor.playable` logic when manifest invalid vs missing.

Update this section as decisions are made during implementation.
