# Project Plan

## Goals
- Deliver a faithful implementation of the Four Against Darkness rules.
- Support both random (procedural) adventures and imported adventures.
- Keep content (tables, tiles, adventures) data-driven and editable.
- Run reliably in Docker/Unraid with persistent storage.

## Non-Goals (for now)
- Multiplayer networking
- Automated PDF import
- Advanced editor UI (beyond JSON tables)

## Current State (Implemented)
- Character creation and storage
- Party selection
- Random adventure sessions
- Tile map rendering and basic exploration flow
- Basic combat loop
- Table viewer + in-app JSON editor (tables/tiles)
- Docker/Unraid deployment pipeline

## Roadmap

### Phase 1 — Core Rules Fidelity
- Tile generation (full d66 set with per-tile graphics)
- Door handling (Door Table, door memory per tile)
- Search table and secret doors/passages per rules
- Wandering monsters table and retracing logic
- Environment rules (dungeon/cavern/fungal)
- Loot and trap resolution

### Phase 2 — Character System
- Full class profiles (attack/defense modifiers)
- Equipment, inventory, and light source rules
- Spell usage, scrolls, and consumables
- XP and level-up flow

### Phase 3 — Imported Adventures
- JSON schema for authored adventures
- Node-based map/paragraph system
- Adventure-specific tables and overrides

### Phase 4 — UX and Tools
- In-app table editor with validation
- Tile image manager (upload + mapping to d66)
- Session history and export
- Configurable logs and play sheet export

## Milestones
- M1: Full d66 tile table + images
- M2: Doors + search + wandering monsters
- M3: Equipment/loot + traps
- M4: Imported adventure support

## Risks & Mitigations
- Rule fidelity drift → maintain table-driven rules and cross-check
- Content scale → keep tables external and editable
- Persistence permissions → enforce PUID/PGID + writable data directory
