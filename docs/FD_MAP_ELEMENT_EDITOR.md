# Forsaken Depths Map Element Editor

Workflow for marking **Four Against the Forsaken Depths** dungeon and river tiles on the **server** (where scans and the running app live), then syncing metadata back into this repository.

Source of truth: `Rules/Four_Against_the_Forsaken_Depths.pdf` — dungeon letter codes p.32; rivers p.37–41.

## Assets

| Location | Contents |
|----------|----------|
| `assets/tiles/forsaken_depths/Forsaken Depths Tile XX.gif` | Dungeon tiles 11–66 |
| `assets/tiles/forsaken_depths/Forsaken Depths Rivers XX.gif` | River stretches 11–66 (**River 17 scan missing**) |
| `data/rules/forsaken_depths_tiles.json` | Dungeon metadata (placeholder grids until edited) |
| `data/rules/forsaken_depths_rivers_tiles.json` | River metadata |

## Editor URLs (on server)

| Catalog | URL |
|---------|-----|
| FD dungeon | `/static/tile-editor.html?catalog=forsaken_depths` |
| FD rivers | `/static/tile-editor.html?catalog=forsaken_depths_rivers` |

API: `GET/PUT /api/rules/tiles?catalog=forsaken_depths` or `forsaken_depths_rivers`  
Room code reference: `GET /api/rules/tiles/room-codes?catalog=…`

**Grid paint tools** (Walk/Block edge halves, diagonal quarters/halves, curves, water): see [MAP_ELEMENT_EDITOR.md](MAP_ELEMENT_EDITOR.md).

## Paint tools

| Tool | Code | Use |
|------|------|-----|
| Blocked | `0` (red) | Rock, walls, impassable |
| Walkable | `1` (green) | Floor, river **banks**, chambers where heroes walk or disembark |
| Water | `2` (blue) | **River catalog only** — navigable channel (boat travel) |
| Passage / door | exit markers | On **walkable** cells at tile edges — connects to adjacent stretches or rooms |

There is **no** separate “water in” / “water out” cell type. Connectivity between river stretches uses **exits on bank squares** at the channel mouth, same as EE dungeon exits.

## River stretches — what to mark

1. **Water (blue)** — full width/length of the navigable river channel on the scan.
2. **Walkable (green)** — banks and any **open chambers** where the party may disembark and walk (FD p.33).
3. **Blocked (red)** — everything else solid.
4. **Exits** — on walkable **bank** cells at edges where:
   - the river continues to the next stretch (upstream/downstream), or
   - a side chamber connects, or
   - the stretch links back to a dungeon **ETR** room (noted on the paper map; metadata is per tile only).
5. Do **not** place exits on water cells.

### River room codes (checkboxes)

| Code | On tile art | Meaning (FD) |
|------|-------------|--------------|
| **END** | END printed | River end — no longer navigable, goes underground (p.37) |
| **Ru** | Ru | Ruin — optional side dungeon (p.39–40) |
| **Ca** | **C** (not “Ca”) | **Cairn** — Precursor mound; spellcasters may tap cairn energy (p.40–41) |
| **B** | B | Bridge — may disembark; 2-in-6 guard roll (p.40) |

If Ru/Ca/B are not printed, they may still appear from the River Features roll at play time — only mark codes **visible on the scan** (or END where printed).

**NC / ETC / ETR** are for the **dungeon** catalog only, not typical river stretches.

## Dungeon tiles — what to mark

1. Blocked / walkable per the scan (irregular worm-tunnel shapes).
2. Exits on walkable cells at passages and doors.
3. Room codes where printed or clearly applicable:
   - **NC** — narrow corridor (p.32)
   - **ETC** — entrance to citadel (p.32)
   - **ETR** — exit to underground river (p.32)

## Save and sync

1. Edit each tile in the editor; **Save** writes the full catalog to:
   - `data/rules/_override/forsaken_depths_tiles.json`
   - `data/rules/_override/forsaken_depths_rivers_tiles.json`
2. When a catalog is complete, copy or merge into the packaged files under `data/rules/` in the repo.
3. Set `implementation_status` to `validated` on each finished tile when ready.
4. Run `python tools/validate_tiles.py` (or CI) before commit.

Home page **Rules tables** expose:

- `forsaken_depths_map_elements_validation_table`
- `forsaken_depths_rivers_map_elements_validation_table`
- `forsaken_depths_room_codes_table`

Rules reference entries: `map_element_catalog`, `forsaken_depths_map_editor`.

## Open items

- **River 17** — no GIF in assets; tile 17 metadata exists but cannot be visually calibrated until a scan is added.
- **END tile(s)** — note which key(s) show END when editing for play reference.
- **Engine wiring** — FD dungeon/river placement in live sessions is future work; this phase is metadata + editor only.
