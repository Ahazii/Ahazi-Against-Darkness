# Map Element Editor — Grid Paint Tools

The **Map Element Editor** (`/static/tile-editor.html`) maintains walkable masks, cell-shape overlays, exits, and (for Forsaken Depths catalogs) water squares and room letter codes.

**Catalog selector:** left panel **Catalog** dropdown (EE, FD dungeon, FD rivers).  
**Current script version:** `tile-editor.js?v=0.40.2` — hard-refresh after deploy.

Forsaken Depths–specific workflow: [FD_MAP_ELEMENT_EDITOR.md](FD_MAP_ELEMENT_EDITOR.md).

## Mouse controls (mask cycle tools)

For **Walk/Block**, **Half**, **Slope**, **Curve**, and **Half Curve**:

- **Left click** — step forward through the cycle
- **Right click** — step backward through the cycle

Long Slope supports left/right click like Walk/Block and Half Curve.

## Water shape mode

On the **Forsaken Depths rivers** catalog, **Water** is a persistent surface
toggle rather than a separate one-shape paint tool.

1. Click **Water** so it remains highlighted.
2. Choose **Walk/Block**, **Half**, **Slope**, **Long Slope**, **Curve**, or
   **Half Curve**.
3. Paint normally. The open part of the selected shape is blue water and the
   blocked part remains red.
4. Click **Water** again to return those tools to green walkable-floor painting.

Left-click and right-click shape cycling work identically in floor and water
mode. Water mode is available only for the FD rivers catalog.

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

One half is a **flat solid block**; the open half gets a **diagonal curved wedge** (corner to opposite corner). **28 steps**, then walkable.

Each direction group uses the **same curve geometry as top-blocked**, rotated 90°/180°/270° for bottom, left, and right.

| Group | Flat | TL→BR | TR→BL |
|-------|------|-------|-------|
| Top blocked | `f` | `j` `k` `l` | `z` `2` `3` |
| Bottom blocked | `m` | `n` `o` `p` | `Z` `7` `8` |
| Left blocked | `q` | `r` `s` `t` | `9` `0` `y` |
| Right blocked | `u` | `v` `w` `x` | `4` `5` `6` |

Example (top blocked, TL→BR deep — like your diagram): **Half Curve** → click to **`l`**.

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
| **Long Slope** | `N`–`U` pairs | Eight two-cell patterns: `N`/`O` and `P`/`Q` vertical (down/up), `R`/`S` and `T`/`U` horizontal (right/left). Left click forward, right click back; ninth step clears. |

Shape letters rotate with tile placement (90° / 180° / 270°) so blocked art stays aligned with the scan.

## Exits

- **Passage / Door** — place on a traversable cell and choose any of the eight
  compass directions: N, NE, E, SE, S, SW, W, or NW. Clicking near a cell
  corner creates a diagonal direction; the exit row provides explicit direction
  buttons.
- Diagonal exits are true map connections. Exploring NE places and connects the
  next tile to the northeast through its reciprocal SW exit.
- Exit spans work for cardinal and diagonal exits. A diagonal span follows the
  45-degree portal line across its cells.
- The marker may sit on one **blocked padding square** immediately beyond the
  opening when the square directly inside, opposite the exit direction, is
  walkable or water. Gameplay treats that blocked anchor as overwriteable
  throat space for the connecting tile. Do not use multiple blocked squares as
  the interior of an exit.
- For the **Forsaken Depths rivers** catalog, place passage exits on water cells
  where the navigable channel continues. Match the exit span to the width of the
  water opening. Use bank/chamber exits only for distinct printed foot routes.
- **Dungeon Exit** — starting tiles `01`–`06` only.
- **Delete Exit** — click an existing marker to remove it.

Inset exits keep their authored square; gameplay may overlap one blocked padding cell on the connected tile (see §13 in [MANUAL_VALIDATION_CHECKLIST.md](MANUAL_VALIDATION_CHECKLIST.md)).

## Forsaken Depths room codes

Optional checkboxes — **leave all unchecked** for normal rooms / ordinary river
stretches. Mark NC / ETC / ETR on dungeon tiles, or ETC / END / Ru / Ca / B on
river tiles, only when printed on the scan. **ETC** is valid in both catalogs.
Letter **C** on river art = **Ca** (Cairn).

## Save path

**Save Metadata** → `PUT /api/rules/tiles?catalog=…` →
`DATA_DIR/rules/<catalog-file>.json` on the server. The local default is
`.data/rules/`; deployments may configure a different `DATA_DIR`. Copy or merge
validated catalogs into the packaged `data/rules/` files when a catalog pass is
complete.

Validation: home **Rules tables** (`map_elements_validation_table` and FD variants), `GET /api/rules/tiles/validation`, `python tools/validate_tiles.py`.
