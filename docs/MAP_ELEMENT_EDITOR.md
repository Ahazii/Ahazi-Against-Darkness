# Map Element Editor — Grid Paint Tools

The **Map Element Editor** (`/static/tile-editor.html`) maintains walkable masks, cell-shape overlays, exits, and (for Forsaken Depths catalogs) water squares and room letter codes.

**Catalog selector:** left panel **Catalog** dropdown (EE, FD dungeon, FD rivers).  
**Current script version:** `tile-editor.js?v=0.37.6` — hard-refresh after deploy.

Forsaken Depths–specific workflow: [FD_MAP_ELEMENT_EDITOR.md](FD_MAP_ELEMENT_EDITOR.md).

## Mouse controls (mask cycle tools)

For **Walk/Block**, **Half**, **Slope**, **Curve**, and **Half Curve**:

- **Left click** — step forward through the cycle
- **Right click** — step backward through the cycle

Other tools (Water, Long Slope, exits) keep left-click only.

## Surface codes (`walkable` grid)

| Code | Editor colour | Meaning |
|------|---------------|---------|
| `0` | Red | Fully blocked (rock / wall) |
| `1` | Green | Walkable floor (or partial shape on a walkable cell) |
| `2` | Blue | Water — **FD rivers catalog only** |

Partial blocks keep `walkable = 1` and store the mask in `cell_shapes`.

## Walk/Block tool

Each **left click** steps forward; **right click** steps back:

1. **Blocked** — full cell (`0`, shape `F`)
2. **Half blocked — top** (shape `V`)
3. **Half blocked — bottom** (shape `W`)
4. **Half blocked — left** (shape `X`)
5. **Half blocked — right** (shape `Y`)
6. **Walkable** — full floor (`1`, shape `F`)

## Half Curve tool

Half the cell blocked; the **boundary between halves** curves across the full width (not corner bumps). **20 steps**, then walkable.

| Group | Shapes | Steps (forward order) |
|-------|--------|------------------------|
| Top blocked | `f` `j` `k` `l` `z` | Flat → shallow → medium → **deep** semicircle → convex |
| Bottom blocked | `m` `n` `o` `p` `Z` | Same |
| Left blocked | `q` `r` `s` `t` `y` | Same |
| Right blocked | `u` `v` `w` `x` `1` | Same |

For top blocked with a curved walkable floor (like irregular FD tunnels): **Half Curve** → left-click from `f` to **`l`** (deep). Right-click goes back.

Left click forward; right click backward.

## Half tool (diagonal)

Each **left click** steps forward; **right click** steps back through **quarter** then **half** diagonal masks, then walkable:

| Step | Shape | Blocked region |
|------|-------|----------------|
| 1–4 | `a` `b` `c` `d` | NE / NW / SE / SW **quarter** (corner triangle, ~25% of cell) |
| 5–8 | `A` `B` `C` `D` | NE / NW / SE / SW **half** (corner triangle, ~50% of cell) |
| 9 | `F` | Walkable (clear) |

## Curve tool

Each **left click** steps forward; **right click** steps back through **quarter** then **full** curved corner masks, then walkable:

| Step | Shape | Blocked region |
|------|-------|----------------|
| 1–4 | `e` `g` `h` `i` | NE / NW / SE / SW **quarter curve** (tight rounded corner) |
| 5–8 | `J` `K` `L` `M` | NE / NW / SE / SW **full curve** (large rounded corner) |
| 9 | `F` | Walkable (clear) |

## Other shape tools

| Tool | Shapes | Use |
|------|--------|-----|
| **Slope** | `E` `G` `H` `I` | Shallow diagonal slopes (one corner chamfered) |
| **Long Slope** | `N`–`U` pairs | Two-cell vertical/horizontal slope patterns |

Shape letters rotate with tile placement (90° / 180° / 270°) so blocked art stays aligned with the scan.

## Exits

- **Passage / Door** — on **walkable** cells at grid edges.
- **Dungeon Exit** — starting tiles `01`–`06` only.
- **Delete Exit** — click an existing marker to remove it.

Inset exits keep their authored square; gameplay may overlap one blocked padding cell on the connected tile (see §13 in [MANUAL_VALIDATION_CHECKLIST.md](MANUAL_VALIDATION_CHECKLIST.md)).

## Forsaken Depths room codes

Optional checkboxes — **leave all unchecked** for normal rooms / ordinary river stretches. Only mark NC / ETC / ETR (dungeon) or END / Ru / Ca / B (rivers) when printed on the scan. Letter **C** on river art = **Ca** (Cairn).

## Save path

**Save Metadata** → `PUT /api/rules/tiles?catalog=…` → `data/rules/_override/<catalog>.json` on the server. Copy merged JSON into `data/rules/` in the repo when a catalog pass is complete.

Validation: home **Rules tables** (`map_elements_validation_table` and FD variants), `GET /api/rules/tiles/validation`, `python tools/validate_tiles.py`.
