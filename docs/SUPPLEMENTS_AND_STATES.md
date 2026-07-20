# Supplements And States

Date: 2026-07-07

Purpose: define the target architecture for turning rules books, adventures, imported PDFs, terrain packs, tile packs, and campaign expansions into one coherent Supplement model, with States as a central game primitive.

This is an architecture note. It does not require immediate code changes, file moves, or data deletion.

## Goals

- Treat the Expanded Edition as the locked-on core supplement.
- Treat adventures, rules expansions, campaign books, terrain packs, tile packs, and imported PDFs as optional supplements.
- Make states first-class so new rules can usually apply, read, modify, expire, or remove states instead of adding one-off fields.
- Keep exact PDF narrative text local and unchanged when a module/adventure requires it.
- Allow supplements to be turned on or off safely for new campaigns and new sessions.
- Keep fixed maps, locations, room tiles, and terrain as separate concepts.
- Keep the current `data/rules/`, `data/adventures/`, `Rules/`, and `Adventures/` layout working during migration.

## Source Of Truth

For rules behavior, the owned rules PDFs remain the source of truth.

When implementing or changing rules:

- Check the relevant PDF page/section first.
- Record source PDF, page, and topic on the supplement record where practical.
- Challenge any requested behavior that contradicts the PDF.
- Use reviewed summaries for rules data.
- Preserve printed narrative/location text exactly only inside local/private module data, not in public/shared source.

## Current Starting Point

The app already has pieces of this model:

- `data/adventures/schema/adventure_package.v1.json` has `capabilities`, `states`, `rules`, `maps`, `pins`, `trackers`, `procedures`, `foes`, `classes`, `items`, `tables`, and `artwork`.
- `docs/ADVENTURE_MODULE_FORMAT.md` already describes module-local states and rules.
- `data/rules/` contains active packaged content for Expanded Edition, Abyss, Forsaken Depths, Courtship, TAG, tiles, tables, monsters, classes, and the rules reference.
- `SessionState`, `PartyMemberState`, `Character`, and several engine modules already use status strings, madness counters, pending choices, campaign plot state, quest state, and supplement-specific flags.

The architecture problem is not that states do not exist. The problem is that states are spread across strings, counters, booleans, pending objects, and supplement-specific fields.

## Definitions

### Supplement

A Supplement is a loadable package of game content and behavior metadata.

Examples:

- Expanded Edition core
- Four Against the Abyss
- Four Against the Forsaken Depths
- The Courtship of Flower Demons
- Tales from the Adventurers' Guild
- a single programmed adventure PDF
- a user-imported adventure package
- a terrain pack
- a random tile catalog pack

A supplement can be rules-heavy, adventure-heavy, map-heavy, tile-heavy, terrain-heavy, or a hybrid.

### State

A State is a named condition, flag, counter, pending choice, temporary modifier, persistent consequence, or campaign fact that can be applied to an entity or scope.

States answer questions like:

- Does this hero have Dark Plague?
- Is this foe stunned, subdued, asleep, undead, or armored?
- Is this item cursed, broken, enchanted, silvered, or consumed?
- Has this location been searched, sealed, pinned, entered, claimed, or revealed?
- Is this map region haunted, flooded, frozen, urban, fungal, or outdoors?
- Is this adventure using madness rules?
- Is this campaign tracking a vampire sire, Guild debt, or an Abyss plot?

### Rule

A Rule is behavior that reads state, applies state, removes state, changes rolls, prompts choices, or advances procedures.

Rules should be code only when behavior must be automated. Imported PDF package rules should remain declarative/review data until manually implemented.

### Procedure

A Procedure is a guided sequence of app actions: roll a table, make a save, choose a consequence, spawn foes, branch to a node, grant an item, mark a state, or complete an objective.

Procedures are safer than arbitrary imported code.

## Supplement Capabilities

Target capability names:

| Capability | Meaning |
|---|---|
| `foes` | Monsters, bosses, minions, vermin, special enemies, and local foe variants. |
| `classes` | Character classes and class-like options. |
| `items` | Equipment, treasure, consumables, services, and special objects. |
| `tables` | Roll tables and lookup tables. |
| `states` | Conditions, flags, counters, trackers, pending choices, and persistent effects. |
| `rules` | Rule metadata and implemented rule hooks. |
| `procedures` | Declarative app workflows for choices, rolls, saves, branching, and rewards. |
| `maps` | Fixed authored maps and image-backed map sheets. |
| `locations` | Rooms, scenes, hexes, settlements, camps, endings, map pins, and linked places. |
| `room_tiles` | Reusable random dungeon tile catalogs. |
| `terrain_types` | Terrain/environment definitions used by maps, locations, room tiles, and rules. |
| `generators` | Random generation profiles: which tile catalogs, tables, terrain, and rules apply. |
| `campaign_state` | Persistent state that can span adventures and sessions. |
| `artwork` | Local/private or packaged art metadata. |
| `narrative` | Exact local PDF text blocks, player-facing scene prose, and source references. |

The current package schema already includes many of these. The main additions to design explicitly are `locations`, `room_tiles`, `terrain_types`, `generators`, `campaign_state`, and `narrative`.

## Supplement Types

Supplement type should describe intent, not restrict capabilities too tightly.

| Type | Typical capabilities |
|---|---|
| `core_rules` | rules, states, foes, classes, items, tables, room_tiles, terrain_types |
| `rules_expansion` | rules, states, foes, classes, items, tables, terrain_types |
| `adventure` | maps, locations, narrative, foes, items, procedures, states, rules |
| `campaign` | campaign_state, locations, procedures, tables, rules, states |
| `tile_pack` | room_tiles, terrain_types, generators |
| `terrain_pack` | terrain_types, rules, states, tables |
| `imported_pdf` | source-backed package data awaiting review |
| `local_user` | user-authored or user-imported local supplement |

One supplement can act as several types. For example, Forsaken Depths is a rules expansion, terrain pack, tile pack, and adventure-framework supplement.

## Enable And Disable Model

Supplement activation should be scoped.

| Scope | Meaning |
|---|---|
| Library enabled | Supplement appears in content lists and can be selected for new campaigns/sessions. |
| Campaign enabled | Supplement rules/content are allowed in a campaign. |
| Session active | Supplement set is locked for a session at creation time. |
| Review only | Supplement/package exists for PDF review but is not playable or active. |

Rules:

- Expanded Edition core is locked on.
- Existing sessions keep the supplement set they started with.
- Disabling a supplement should prevent it from appearing in new sessions; it should not corrupt existing saves.
- A supplement can declare dependencies and conflicts.
- A supplement can be present but inactive if PDF review is incomplete.

Example:

```json
{
  "id": "four-against-the-abyss",
  "title": "Four Against the Abyss",
  "type": "rules_expansion",
  "enabled_by_default": false,
  "locked": false,
  "depends_on": ["expanded-edition-core"],
  "conflicts_with": [],
  "capabilities": ["foes", "items", "tables", "states", "rules", "campaign_state"]
}
```

## Maps, Locations, Room Tiles, And Terrain

These should stay separate.

### Maps

Maps are authored spatial artifacts. They can be images, fixed layouts, wilderness sheets, settlement plans, or dungeon maps.

Maps can have:

- source PDF and page
- image asset path
- coordinate system
- pins
- regions
- linked locations
- narrative/room labels

### Locations

Locations are playable or reviewable places.

Examples:

- room
- scene
- hex
- settlement
- camp
- ending
- shop
- shrine
- lair

Locations can link to each other, contain foes/items/procedures, apply states, and include exact local PDF narrative text.

### Room Tiles

Room tiles are reusable random generation elements. They are not the same as fixed maps.

Room tiles can have:

- catalog id
- tile key
- image
- exits
- walkable cells
- water cells
- room codes
- compatible terrain
- generator weights
- special placement rules

### Terrain Types

Terrain is the environmental/rules layer applied to tiles, map regions, locations, or whole sessions.

Examples:

- dungeon
- caverns
- fungal_grottoes
- wilderness
- forest
- swamp
- river
- lava
- icy
- urban
- haunted
- demesne
- citadel
- ruins
- dark_pits

Terrain can affect:

- random table selection
- available spells
- movement
- search rules
- encounter rules
- visibility
- hazards
- UI badges/icons
- state application or expiration

Target terrain record:

```json
{
  "id": "fungal_grottoes",
  "name": "Fungal Grottoes",
  "source": {
    "supplement_id": "expanded-edition-core",
    "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf",
    "page": 0,
    "topic": "Fungal Grottoes"
  },
  "applies_to": ["session", "tile", "location"],
  "table_overrides": [],
  "state_interactions": [],
  "ui": {
    "icon": "mushrooms",
    "hover": "Uses fungal grotto rules, tables, hazards, and terrain-specific interactions."
  },
  "review_status": "needs_pdf_page"
}
```

## State Model

Target state definition:

```json
{
  "id": "dark-plague",
  "name": "Dark Plague",
  "scope": "character",
  "source": {
    "supplement_id": "four-against-the-abyss",
    "source_pdf": "Four-Against-the-Abyss.pdf",
    "page": 0,
    "topic": "Dark Plague"
  },
  "description": "Reviewed rules summary.",
  "visibility": "player_visible",
  "value_type": "flag",
  "stacking": "unique",
  "duration": {
    "kind": "until_removed"
  },
  "removal": [
    {
      "method": "blessing",
      "notes": "Use the PDF-specified cure rule."
    }
  ],
  "effects": [],
  "ui": {
    "label": "Dark Plague",
    "hover": "Source-backed disease state. Check the Rules Reference before resolving cures or spread."
  },
  "review_status": "needs_pdf_page"
}
```

Target state instance:

```json
{
  "state_id": "dark-plague",
  "scope": "character",
  "target_id": "character-id",
  "value": true,
  "source_supplement_id": "four-against-the-abyss",
  "applied_at": {
    "session_id": "session-id",
    "round": 0,
    "tile_id": "tile-id"
  },
  "expires": null,
  "metadata": {}
}
```

## State Scopes

| Scope | Examples |
|---|---|
| `character` | poisoned, cursed, petrified, mad, blessed, hungry, lycanthropy |
| `party_member` | combat-only copy of a character state |
| `foe` | asleep, stunned, subdued, regenerating, armored, immune |
| `equipment` | cursed, broken, enchanted, silvered, poisoned, expended |
| `location` | searched, claimed, sealed, trap_disarmed, haunted |
| `tile` | flooded, blocked, secret_exit, river_processed |
| `map` | region_revealed, pin_discovered, route_opened |
| `adventure` | boss_awakened, objective_complete, alarm_raised |
| `campaign` | abyss_plot_active, guild_debt, bank_account_robbed |
| `global` | user preference or library-level flag; use sparingly |

## State Value Types

| Type | Meaning |
|---|---|
| `flag` | Present or absent. |
| `counter` | Numeric value, such as Madness or progress. |
| `choice` | Pending or selected option. |
| `modifier` | Attack, Defense, Save, table roll, or other modifier. |
| `timer` | Turns, rounds, rooms, sessions, adventures, or campaign days. |
| `resource` | Charges, uses, spell slots, stored gold, or similar. |
| `link` | Relationship to another entity, such as sire, carrier, owner, or target. |

## Rule Hooks

Rules should be implemented through small, named hook points rather than arbitrary imported code.

Initial hook candidates:

| Hook | Purpose |
|---|---|
| `on_session_start` | Apply supplement setup and campaign state. |
| `on_room_entered` | Terrain, location, hazard, and encounter entry effects. |
| `on_search` | Search modifiers, hidden results, and location state changes. |
| `on_combat_start` | Surprise, fear, morale, special encounter starts. |
| `modify_attack_roll` | Attack bonuses/penalties from class, item, terrain, or state. |
| `modify_defense_roll` | Defense modifiers and reroll states. |
| `modify_save_roll` | Save bonuses, penalties, immunities, and rerolls. |
| `on_foe_hit_character` | Poison, paralysis, disease, drain, curse, and similar effects. |
| `on_character_hits_foe` | Silver, poison, fire, holy, weakness, regeneration suppression. |
| `on_round_end` | Timed combat states and per-turn effects. |
| `on_combat_end` | End-of-encounter disease, morale, treasure, and cleanup. |
| `on_adventure_complete` | Campaign state, XP, closeout tasks, persistent consequences. |
| `on_blessing` | Cure/removal choices and blessing-preserve logic. |
| `on_state_added` | Trigger secondary effects or UI prompts. |
| `on_state_removed` | Cleanup linked state and UI prompts. |

Imported PDF modules should not define executable hook code. They may define candidate rules and procedures that the app later maps to trusted hook implementations.

## Candidate State Families

This is a starting taxonomy, not a final implementation list.

| Family | Candidate states |
|---|---|
| Core conditions | cursed, petrified, asleep, poisoned, hungry, pit trapped |
| Combat modifiers | attack penalty, defense penalty, no exploding attacks, regeneration suppressed |
| Disease and infection | Dark Plague, lycanthropy exposure, lycanthropy, plague immunity |
| Madness and fear | madness counter, paranoid, fear penalty, insanity/transformation |
| Blessings and buffs | blessed, holy protection, acolyte blessing pending, alchemist buffs |
| Equipment states | enchanted weapon, silvered weapon, cursed item, broken firearm, poisoned weapon |
| Foe traits/states | undead, demon, dragon, armored, flying, stunned, subdued, asleep |
| Terrain states | flooded, fungal, river, lava, haunted, urban, outdoors |
| Location states | searched, claimed, hidden treasure found, trap disarmed, secret exit opened |
| Adventure states | objective active, boss defeated, finale pending, alarm raised |
| Campaign states | Abyss plot, vampire sire, Guild debt, bank robbery, settlement travel |

## PDF Import And Review

PDF import should produce reviewable supplement data, not executable behavior.

Safe imported records:

- foes
- classes
- items
- tables
- maps
- pins
- locations
- exact local narrative text
- candidate states
- candidate rules
- trackers
- procedures
- artwork references

Unsafe imported records:

- arbitrary Python
- arbitrary JavaScript
- shell commands
- expressions that execute
- rules that silently override core behavior without review

When a PDF has a rule the app does not yet support, the importer should create:

- a source-backed candidate rule
- a candidate state, if applicable
- app notes
- review status
- source page/topic
- a "needs implementation" marker

## Storage Direction

Do not rename current folders immediately.

Short-term compatibility:

```text
data/rules/                     packaged active rules data
data/adventures/                packaged adventure schemas/examples
DATA_DIR/Adventures/            installed user/imported adventures
DATA_DIR/rules/                 user/private rule PDFs and overrides
Rules/                          ignored local private rule PDFs
Adventures/                     ignored local private adventure PDFs
```

Target concept:

```text
data/supplements/
  expanded-edition-core/
  four-against-the-abyss/
  forsaken-depths/
  courtship/
  tag/

DATA_DIR/Supplements/
  user-imported-or-reviewed-supplement/
```

Migration rule:

- Build the loader first.
- Let it read current paths.
- Add supplement metadata around existing data.
- Move files only after the app and tests understand the new model.

## Proposed Supplement Metadata

Target manifest:

```json
{
  "schema_version": 1,
  "id": "expanded-edition-core",
  "title": "Four Against Darkness Expanded Edition",
  "kind": "core_rules",
  "locked": true,
  "enabled_by_default": true,
  "source": {
    "type": "pdf",
    "source_pdf": "Four_Against_Darkness_Expanded_Edition.pdf"
  },
  "capabilities": [
    "foes",
    "classes",
    "items",
    "tables",
    "states",
    "rules",
    "room_tiles",
    "terrain_types",
    "generators"
  ],
  "dependencies": [],
  "conflicts": [],
  "data_files": {
    "foes": ["monsters.json"],
    "classes": ["classes.json"],
    "tables": ["dungeon_tables.json"],
    "room_tiles": ["tiles.json"],
    "rules_reference": ["rulebook_reference.json"]
  },
  "review_status": "active"
}
```

## UI Expectations

Supplement-aware UI should eventually show:

- supplement library with on/off controls
- locked core supplement indicator
- dependencies/conflicts
- source PDF and page references
- active supplement set for each campaign/session
- active states on character/foe/location/equipment cards
- hover text for every state and supplement-specific UI control
- rules reference entries filtered by active supplement
- tables list grouped by active supplement
- terrain badges and hover text
- clear warnings when a module contains unimplemented reviewed rules

Default mode should remain dark unless the user chooses otherwise or system settings are followed.

## Migration Plan

### Phase 0: Audit And Documentation

- Keep `docs/PROJECT_RELEVANCE_AUDIT.md` as the cleanup guide.
- Add this architecture note.
- Add/update a docs index.
- Rehome historical audits only after link checks.

### Phase 1: Read-Only Supplement Registry

- Add supplement metadata records for existing rule/data groups.
- Store packaged supplement metadata at `data/supplements/<supplement_id>/supplement.json`.
- Validate supplement metadata against `data/supplements/schema/supplement_manifest.v1.json` plus the app's runtime manifest validator.
- Create `DATA_DIR/Supplements/` for future local reviewed supplements beside `game.db`.
- Do not change gameplay.
- The app can list known supplements and their capabilities.
- Expanded Edition core is locked on.
- Existing data loaders continue reading current files.
- Mark current `ruleset`, `ruleset_profile_id`, `tile_catalog`, `courtship_enabled`, `fiendish_foes_enabled`, and `tag_banking_enabled` fields as legacy compatibility rather than removing them.
- Show the read-only supplement registry in Settings beside the legacy ruleset controls.

### Phase 2: State Registry

- Add state definitions for a small set of already implemented states.
- Start with states that already exist as constants/status strings.
- Map current string statuses to definitions without changing save format yet.
- Add source references and hover text.
- Mark `Character.statuses`, `PartyMemberState.statuses`, `Character.madness`, `PartyMemberState.madness`, and `SessionState.pending_*` as legacy compatibility storage.
- Show the read-only State Registry in Settings beside the Supplement Library.
- Make the read-only State Registry searchable/filterable by family, scope, source supplement, and review status before adding state-instance mutation.
- Adventure View room details now show active registry-backed state/status matches in the Registry Context block. Party Sheet summaries and expanded State Context rows show whether each hero's visible effects map to State Registry rows, and status-chip hovers append matching State Registry metadata to the existing rules tooltip when a legacy status string maps to a registry row.
- Backend resolver helpers and diagnostic APIs now map legacy status/effect labels to State Registry rows so future loaders and reports do not need to duplicate matching logic.
- Campaign-owned TAG effects and Rumor lifecycle records now use structured `CampaignState.campaign_effects` and `CampaignState.tag_rumor_states`, joined from `SessionState.campaign_id`. The pending Invisible Gremlins procedure uses `SessionState.pending_gremlin_event`; per-adventure item protection uses `SessionState.gremlin_protected_items`; TAG p.65 encounter decisions use `SessionState.temporary_weapon_loss_choices`; explicit Bag contents use `Character.item_containers` and `PartyMemberState.item_containers`. These are active structured save fields, not new legacy status strings.

Good first candidates:

- Dark Plague
- Lycanthropy exposure
- Lycanthropy
- Vampire-rise pending
- Petrified
- Hungry
- Envenomed weapon
- FD Psychic Residue +3 Save
- Bofto star-object campaign effect
- TAG Rumor heard/investigating/resolved lifecycle
- Invisible Gremlins pending theft
- Gremlin-protected item
- Bag of Carrying contents

### Phase 3: Terrain Registry

- Add terrain definitions for current environments.
- Start with `dungeon`, `caverns`, `fungal_grottoes`, Forsaken Depths river/citadel/ruins/dark pits concepts, and Courtship demesne regions.
- Wire UI labels and hover text before deeper rule changes.
- Mark `TileState.environment`, `TileState.terrain`, `SessionState.environment`, `SessionState.alter_weather_active`, and `SessionState.forest_pathway_active` as legacy compatibility storage.
- Show a read-only Terrain Registry in Settings and explain the difference between terrain, maps, and room tiles.
- Make the read-only Terrain Registry searchable/filterable by kind, source supplement, review status, and interaction group before adding terrain-instance mutation.
- Adventure View room details now show the current terrain registry match in the Registry Context block, and Play Context terrain hovers expose matching Terrain Registry metadata while leaving map/session terrain fields as the active save format.
- Backend resolver helpers and diagnostic APIs now map environment, terrain, and tile-catalog values to Terrain Registry rows without changing spell, map, or table-routing logic.

### Phase 4: Session Supplement Lock

- Record active supplements when a session starts. Settings provides the default list; Go Adventure shows those defaults as adjustable per-session checkboxes before the final `active_supplement_ids` snapshot is saved.
- Do not let later enable/disable changes corrupt active sessions.
- Add required dependencies automatically and reject declared supplement conflicts before saving defaults or starting sessions.
- Show active supplement list in session diagnostics, the Adventure View header, session lists, and the new-session log/report context.
- Filter Rules Reference and Tables List by inferred supplement context, including the saved enabled-default supplement set.
- Keep old sessions valid by treating missing `active_supplement_ids` as a legacy session with no snapshot metadata.
- Snapshot supplement, state-registry, and terrain-registry versions on new sessions so future migrations can tell which metadata model was active at creation.

### Phase 5: Package Schema v2

- Extend package capabilities with `locations`, `room_tiles`, `terrain_types`, `generators`, `campaign_state`, and `narrative`.
- Keep v1 package compatibility.
- Add migration/validation diagnostics.
- Cross-reference imported package `states` and `terrain_types` against the State Registry and Terrain Registry as review-only hints before any loader promotes them.
- Keep package records declarative unless a trusted loader explicitly promotes them into a supplement manifest.

### Phase 6: Rule Hooks

- Introduce hook points only as needed by real rule implementation.
- Move one existing rule family at a time.
- Keep PDF page references and tests with every behavior change.

### Phase 7: Folder Rehome

- After registry support is stable, move packaged data into supplement folders.
- Keep compatibility aliases for old paths.
- Decide local private PDF convention.
- De-duplicate private PDFs only after user confirmation.

## Open Questions

- Should user-facing storage become `DATA_DIR/Supplements/` while keeping `DATA_DIR/Adventures/` as a compatibility alias?
- Should `states` replace `statuses` in save data immediately, or should the first version map old string statuses to state definitions?
- Should terrain be applied primarily at session, tile, map-region, or location level when several apply?
- Should imported exact PDF narrative live in `narrative[]`, `locations[].player_text`, or both?
- Should active supplement sets be campaign-scoped first, session-scoped first, or both at once?

## Recommended First Coding Slice

Do not start by moving files.

The first implementation slice should be:

1. Define a read-only supplement registry that describes existing content groups.
2. Add metadata for Expanded Edition core, Abyss, Forsaken Depths, Courtship, TAG, and imported adventures.
3. Expose the registry in developer/debug diagnostics or Rules Reference.
4. Add no gameplay changes.
5. Add tests proving the registry loads and the core supplement is locked on.

After that, add the first state registry pass using existing statuses.
