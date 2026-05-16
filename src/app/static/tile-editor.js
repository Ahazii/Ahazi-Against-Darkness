const editor = {
  tiles: [],
  selectedKey: null,
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
const exitList = document.getElementById("exit-list");
const addExitButton = document.getElementById("add-exit");
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
    editor.selectedKey = editor.tiles[0]?.key || null;
    setStatus(`${editor.tiles.length} tiles`);
    renderTileList();
    renderSelectedTile();
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
  tileTitle.textContent = `${tile.key} ${tile.name}`;
  tilePreview.src = tile.image ? `/assets/tiles/${tile.image}` : "";
  tilePreview.alt = tile.name;
  nameInput.value = tile.name || "";
  typeInput.value = tile.tile_type || "unknown";
  widthInput.value = tile.footprint_width || 1;
  heightInput.value = tile.footprint_height || 1;
  descriptionInput.value = tile.description || "";
  implementationStatusInput.value = tile.implementation_status || "";
  renderExits(tile);
}

function renderExits(tile) {
  exitList.replaceChildren();
  for (const exit of tile.exits || []) {
    const row = document.createElement("div");
    row.className = "exit-row";
    row.dataset.exitId = exit.id;

    const direction = select(["north", "east", "south", "west"], exit.direction);
    direction.className = "exit-direction";
    const kind = select(["passage", "door"], exit.kind);
    kind.className = "exit-kind";
    const position = document.createElement("input");
    position.type = "number";
    position.min = "0";
    position.max = "1";
    position.step = "0.05";
    position.value = exit.position ?? 0.5;
    position.className = "exit-position";
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.addEventListener("click", () => {
      tile.exits = tile.exits.filter((item) => item.id !== exit.id);
      renderExits(tile);
    });

    row.append(direction, kind, position, remove);
    exitList.appendChild(row);
  }
}

function select(values, current) {
  const el = document.createElement("select");
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    option.selected = value === current;
    el.appendChild(option);
  }
  return el;
}

function persistForm() {
  const tile = selectedTile();
  if (!tile) return;
  tile.name = nameInput.value.trim() || `Dungeon Tile ${tile.key}`;
  tile.tile_type = typeInput.value;
  tile.footprint_width = Number.parseInt(widthInput.value || "1", 10);
  tile.footprint_height = Number.parseInt(heightInput.value || "1", 10);
  tile.description = descriptionInput.value.trim();
  tile.implementation_status = implementationStatusInput.value.trim() || "edited";
  tile.exits = Array.from(exitList.querySelectorAll(".exit-row")).map((row, index) => ({
    id: row.dataset.exitId || `${tile.key}-exit-${index + 1}`,
    direction: row.querySelector(".exit-direction").value,
    kind: row.querySelector(".exit-kind").value,
    position: Number.parseFloat(row.querySelector(".exit-position").value || "0.5"),
  }));
}

function newExitId(tile) {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return `${tile.key}-exit-${window.crypto.randomUUID()}`;
  }
  return `${tile.key}-exit-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

addExitButton.addEventListener("click", () => {
  const tile = selectedTile();
  if (!tile) return;
  persistForm();
  tile.exits.push({
    id: newExitId(tile),
    direction: "north",
    kind: "passage",
    position: 0.5,
  });
  renderExits(tile);
});

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
