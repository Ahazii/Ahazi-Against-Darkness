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
- Class profile audit (EE p.24–69): Life, wealth, starting gear; `tools/audit_class_profiles.py`.
- Inventory carry limits, default weapons, session-to-roster persistence on clean exit.
- Home equipment shop (buy p.16 / sell p.19) and weapon-default dialogs.
- Dice trace on exploration and many combat actions.
- Tests for tables, combat modifiers, weapons, exploration, economy, reactions, spells,
  carry limits, equipment, equipment shop, session persist, door sync.

Still open:

- Class abilities Tiers 2–4 (tricks, gadgets, advanced skills); expand Luck reroll hooks (defense, saves, treasure).
- **Named save labels** for Saved Games (party + timestamp today; user labels planned).
- Replace placeholder `tiles.json` rows with exact starting (`01-06`) and
  generated (`11-66`) map element metadata.
- Validate map element footprints and multiple exits on the same edge through
  the visual metadata editor. Exits are anchored to exact grid-square edges.
- Continue validating walkable-space placement and truncation against more
  rulebook examples, especially cases where other exits would be covered.
- ~~Add optional fixed paper size~~ — done: unlimited (default) or 20×28 at session start.
- ~~Caverns/fungal grottoes table variants~~ — starter tables wired; validate row text against PDF.
- Refine visual truncation beyond cell clipping if later rules require more
  precise pixel/vector masks.
- Add paint-mask or arbitrary polygon mask authoring if the per-square
  shallow-slope, two-square long-slope, and curved-corner masks are not precise
  enough for circular rooms or later line-of-sight needs.
- Per-foe reaction tables for remaining bestiary entries, expanded MR tiers.
- **Split party (EE p.105, p.79–80, Fiendish Foes p.180):** not implemented.
  Rulebook allows leaving PCs behind (guard bodies, solo quest steps) with a
  separate 1-in-6 wandering-monster check for the detached group each time the
  main party rolls wanderers; stealth/scout rules can leave a lone PC one turn
  from backup; simultaneous fights when a Major Foe and Minions share a tile
  require splitting attacks across sub-groups. Needs session model for multiple
  map positions / sub-parties and UI to assign heroes to each group.
- Dedicated combat panel with per-hero targeting (defaults/swap and shop exist today).
- **Session UI polish** (in progress):
  - Done: map pan/zoom overlay pinned to viewport; hero actions on party sheets;
    equipment/inventory header icons; ally bandage targeting; room panel and **exits dock
    beside the log**; icon key as map overlay; resizable log/map, side-panel, and map-height
    splits (double-click reset, fill-remaining-space default); compact expandable session log;
    unified per-exit list with door shortcuts; party sheet accordion; **2×2 party grid**
    (container-query responsive); sticky session action bar; **Fight Round** label; exits
    default open with persisted layout prefs.
  - Planned:
    - Expand `rulebook_reference.json` with more scanned snippets beside table data.
- **Remaining expert skill effects** — all Abyss catalog skills wired (2026-05-19).
- Extend the local icon registry beyond room-state markers to support character
  class icons, monster-type icons, item icons, and room-feature icons in the
  relevant sheets and combat views.
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
