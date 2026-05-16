const editor = {
  tiles: [],
  selectedKey: null,
  mode: "walkable",
};

const statusEl = document.getElementById("editor-status");
const tileList = document.getElementById("tile-list");
const tileTitle = document.getElementById("tile-title");
const tilePreview = document.getElementById("tile-preview");
const nameInput = document.getElementById("edit-name");
const typeInput = document.getElementById("edit-type");
const widthInput = document.getElementById("edit-width");
const heightInput = document.getElementById("edit-height");
const descriptionInput = document.getElementById("edit-description");
const implementationStatusInput = document.getElementById("edit-status");
const gridOverlay = document.getElementById("grid-overlay");
const exitOverlay = document.getElementById("exit-overlay");
const exitList = document.getElementById("exit-list");
const toolButtons = document.getElementById("editor-tools");
const saveButton = document.getElementById("save-tiles");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || "Request failed");
  }
  return response.json();
}

function setStatus(message) {
  statusEl.textContent = message;
}

function selectedTile() {
  return editor.tiles.find((tile) => tile.key === editor.selectedKey);
}

async function loadTiles() {
  try {
    editor.tiles = await api("/api/rules/tiles");
    editor.tiles.forEach(normalizeTile);
    editor.selectedKey = editor.tiles[0]?.key || null;
    setStatus(`${editor.tiles.length} elements`);
    renderTileList();
    renderSelectedTile();
    renderTools();
  } catch (error) {
    setStatus(error.message);
  }
}

function renderTileList() {
  tileList.replaceChildren();
  for (const tile of editor.tiles) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tile-list-item";
    if (tile.key === editor.selectedKey) button.classList.add("selected");
    button.textContent = `${tile.key} ${tile.name}`;
    button.addEventListener("click", () => {
      persistForm();
      editor.selectedKey = tile.key;
      renderTileList();
      renderSelectedTile();
    });
    tileList.appendChild(button);
  }
}

function renderSelectedTile() {
  const tile = selectedTile();
  if (!tile) return;
  normalizeTile(tile);
  tileTitle.textContent = `${tile.key} ${tile.name}`;
  tilePreview.src = tile.image ? `/assets/tiles/${tile.image}` : "";
  tilePreview.alt = tile.name;
  nameInput.value = tile.name || "";
  typeInput.value = tile.tile_type || "unknown";
  widthInput.value = tile.footprint_width || 1;
  heightInput.value = tile.footprint_height || 1;
  descriptionInput.value = tile.description || "";
  implementationStatusInput.value = tile.implementation_status || "";
  renderGrid(tile);
  renderExitList(tile);
}

function renderTools() {
  for (const button of toolButtons.querySelectorAll("button")) {
    button.classList.toggle("selected", button.dataset.mode === editor.mode);
  }
}

function renderGrid(tile) {
  normalizeTile(tile);
  gridOverlay.replaceChildren();
  exitOverlay.replaceChildren();
  gridOverlay.style.gridTemplateColumns = `repeat(${tile.footprint_width}, minmax(0, 1fr))`;
  gridOverlay.style.gridTemplateRows = `repeat(${tile.footprint_height}, minmax(0, 1fr))`;

  for (let y = 0; y < tile.footprint_height; y += 1) {
    for (let x = 0; x < tile.footprint_width; x += 1) {
      const square = document.createElement("button");
      square.type = "button";
      square.className = `grid-square ${isWalkable(tile, x, y) ? "walkable" : "blocked"}`;
      square.dataset.x = x;
      square.dataset.y = y;
      square.addEventListener("click", (event) => handleGridClick(tile, x, y, event));
      gridOverlay.appendChild(square);
    }
  }

  for (const exit of tile.exits) {
    exitOverlay.appendChild(exitMarker(tile, exit));
  }
}

function renderExitList(tile) {
  exitList.replaceChildren();
  for (const exit of tile.exits) {
    const row = document.createElement("div");
    row.className = "exit-row visual-exit-row";
    const label = document.createElement("div");
    label.innerHTML = `<strong>${exitLabel(exit)}</strong><span class="muted">square ${exit.x + 1},${exit.y + 1}</span>`;
    const kind = document.createElement("select");
    kind.className = "exit-kind";
    for (const value of ["passage", "door"]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      option.selected = value === exit.kind;
      kind.appendChild(option);
    }
    kind.addEventListener("change", () => {
      exit.kind = kind.value;
      renderGrid(tile);
      renderExitList(tile);
    });
    const dungeonExit = document.createElement("label");
    dungeonExit.className = "inline-check";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(exit.dungeon_exit);
    checkbox.addEventListener("change", () => {
      exit.dungeon_exit = checkbox.checked;
      renderGrid(tile);
      renderExitList(tile);
    });
    dungeonExit.append(checkbox, document.createTextNode("Dungeon exit"));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      tile.exits = tile.exits.filter((item) => item.id !== exit.id);
      renderGrid(tile);
      renderExitList(tile);
    });
    row.append(label, kind, dungeonExit, remove);
    exitList.appendChild(row);
  }
}

function handleGridClick(tile, x, y, event) {
  if (editor.mode === "walkable" || editor.mode === "blocked") {
    setWalkable(tile, x, y, editor.mode === "walkable");
    renderGrid(tile);
    return;
  }

  const direction = nearestEdge(event);
  if (editor.mode === "erase_exit") {
    tile.exits = tile.exits.filter((exit) => !(exit.x === x && exit.y === y && exit.direction === direction));
  } else {
    upsertExit(tile, x, y, direction, editor.mode);
  }
  renderGrid(tile);
  renderExitList(tile);
}

function nearestEdge(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const distances = [
    ["north", y],
    ["east", rect.width - x],
    ["south", rect.height - y],
    ["west", x],
  ];
  distances.sort((a, b) => a[1] - b[1]);
  return distances[0][0];
}

function upsertExit(tile, x, y, direction, mode) {
  const dungeonExit = mode === "dungeon_exit";
  const kind = dungeonExit ? "passage" : mode;
  const existing = tile.exits.find((exit) => exit.x === x && exit.y === y && exit.direction === direction);
  const offset = exitOffset(direction, x, y);
  if (existing) {
    existing.kind = kind;
    existing.dungeon_exit = dungeonExit;
    existing.offset = offset;
    existing.position = exitPosition(direction, offset, tile.footprint_width, tile.footprint_height);
    return;
  }
  tile.exits.push({
    id: newExitId(tile),
    direction,
    kind,
    x,
    y,
    offset,
    position: exitPosition(direction, offset, tile.footprint_width, tile.footprint_height),
    dungeon_exit: dungeonExit,
  });
}

function exitMarker(tile, exit) {
  const marker = document.createElement("button");
  marker.type = "button";
  marker.className = `exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""} ${exit.direction}`;
  marker.title = exitLabel(exit);
  const cellW = 100 / tile.footprint_width;
  const cellH = 100 / tile.footprint_height;
  const left = exit.x * cellW;
  const top = exit.y * cellH;
  if (exit.direction === "north" || exit.direction === "south") {
    marker.style.left = `${left + cellW * 0.2}%`;
    marker.style.top = `${top + (exit.direction === "north" ? 0 : cellH)}%`;
    marker.style.width = `${cellW * 0.6}%`;
  } else {
    marker.style.left = `${left + (exit.direction === "west" ? 0 : cellW)}%`;
    marker.style.top = `${top + cellH * 0.2}%`;
    marker.style.height = `${cellH * 0.6}%`;
  }
  marker.addEventListener("click", (event) => {
    event.stopPropagation();
    tile.exits = tile.exits.filter((item) => item.id !== exit.id);
    renderGrid(tile);
    renderExitList(tile);
  });
  return marker;
}

function persistForm() {
  const tile = selectedTile();
  if (!tile) return;
  tile.name = nameInput.value.trim() || `Map Element ${tile.key}`;
  tile.tile_type = typeInput.value;
  tile.footprint_width = clampNumber(widthInput.value, 1, 20);
  tile.footprint_height = clampNumber(heightInput.value, 1, 20);
  tile.description = descriptionInput.value.trim();
  tile.implementation_status = implementationStatusInput.value.trim() || "edited";
  normalizeTile(tile);
}

function normalizeTile(tile) {
  tile.footprint_width = clampNumber(tile.footprint_width || 1, 1, 20);
  tile.footprint_height = clampNumber(tile.footprint_height || 1, 1, 20);
  tile.walkable = normalizeWalkable(tile.walkable, tile.footprint_width, tile.footprint_height);
  tile.exits = (tile.exits || []).map((exit) => normalizeExit(tile, exit));
}

function normalizeWalkable(rows, width, height) {
  const normalized = [];
  const source = Array.isArray(rows) ? rows : [];
  for (let y = 0; y < height; y += 1) {
    const sourceRow = String(source[y] || "");
    let row = "";
    for (let x = 0; x < width; x += 1) {
      row += sourceRow[x] === "0" ? "0" : "1";
    }
    normalized.push(row);
  }
  return normalized;
}

function normalizeExit(tile, exit) {
  const direction = exit.direction || "north";
  const x = clampNumber(exit.x ?? coordinateFromOffset(exit, tile).x, 0, tile.footprint_width - 1);
  const y = clampNumber(exit.y ?? coordinateFromOffset(exit, tile).y, 0, tile.footprint_height - 1);
  const offset = exitOffset(direction, x, y);
  return {
    id: exit.id || newExitId(tile),
    direction,
    kind: exit.kind === "door" ? "door" : "passage",
    x,
    y,
    offset,
    position: exitPosition(direction, offset, tile.footprint_width, tile.footprint_height),
    dungeon_exit: Boolean(exit.dungeon_exit),
  };
}

function coordinateFromOffset(exit, tile) {
  const offset = clampNumber(exit.offset || 0, 0, 99);
  if (exit.direction === "south") return { x: Math.min(offset, tile.footprint_width - 1), y: tile.footprint_height - 1 };
  if (exit.direction === "east") return { x: tile.footprint_width - 1, y: Math.min(offset, tile.footprint_height - 1) };
  if (exit.direction === "west") return { x: 0, y: Math.min(offset, tile.footprint_height - 1) };
  return { x: Math.min(offset, tile.footprint_width - 1), y: 0 };
}

function isWalkable(tile, x, y) {
  return tile.walkable[y]?.[x] !== "0";
}

function setWalkable(tile, x, y, value) {
  const row = tile.walkable[y].split("");
  row[x] = value ? "1" : "0";
  tile.walkable[y] = row.join("");
}

function exitOffset(direction, x, y) {
  return direction === "north" || direction === "south" ? x : y;
}

function exitPosition(direction, offset, width, height) {
  const side = direction === "north" || direction === "south" ? width : height;
  return side <= 1 ? 0.5 : offset / (side - 1);
}

function exitLabel(exit) {
  const direction = exit.direction[0].toUpperCase() + exit.direction.slice(1);
  if (exit.dungeon_exit) return `${direction} Dungeon Exit`;
  const kind = exit.kind[0].toUpperCase() + exit.kind.slice(1);
  return `${direction} ${kind}`;
}

function clampNumber(value, min, max) {
  const number = Number.parseInt(value, 10);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function newExitId(tile) {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return `${tile.key}-exit-${window.crypto.randomUUID()}`;
  }
  return `${tile.key}-exit-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

toolButtons.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-mode]");
  if (!button) return;
  editor.mode = button.dataset.mode;
  renderTools();
});

for (const input of [widthInput, heightInput]) {
  input.addEventListener("change", () => {
    persistForm();
    renderSelectedTile();
  });
}

saveButton.addEventListener("click", async () => {
  try {
    persistForm();
    await api("/api/rules/tiles", {
      method: "PUT",
      body: JSON.stringify(editor.tiles),
    });
    setStatus("Saved");
    renderTileList();
    renderSelectedTile();
  } catch (error) {
    setStatus(error.message);
  }
});

loadTiles();
