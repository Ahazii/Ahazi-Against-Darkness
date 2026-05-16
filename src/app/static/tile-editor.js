const editor = {
  tiles: [],
  selectedKey: null,
  mode: "walkable",
  suppressNextGridClick: false,
};

const STATUS_OPTIONS = [
  ["placeholder-needs-rulebook-validation", "Placeholder - needs rulebook validation"],
  ["starter-needs-rulebook-validation", "Starter - needs rulebook validation"],
  ["edited-needs-rulebook-validation", "Edited - needs rulebook validation"],
  ["validated", "Validated against rulebook"],
];

const statusEl = document.getElementById("editor-status");
const tileList = document.getElementById("tile-list");
const tileTitle = document.getElementById("tile-title");
const tilePreview = document.getElementById("tile-preview");
const nameInput = document.getElementById("edit-name");
const typeInput = document.getElementById("edit-type");
const widthInput = document.getElementById("edit-width");
const heightInput = document.getElementById("edit-height");
const cellSizeInput = document.getElementById("edit-cell-size");
const imageScaleInput = document.getElementById("edit-image-scale");
const imageOffsetXInput = document.getElementById("edit-image-offset-x");
const imageOffsetYInput = document.getElementById("edit-image-offset-y");
const descriptionInput = document.getElementById("edit-description");
const implementationStatusInput = document.getElementById("edit-status");
const gridOverlay = document.getElementById("grid-overlay");
const exitOverlay = document.getElementById("exit-overlay");
const editorStage = document.getElementById("editor-stage");
const exitList = document.getElementById("exit-list");
const toolButtons = document.getElementById("editor-tools");
const saveButton = document.getElementById("save-tiles");
const addExitButton = document.getElementById("add-exit");

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
  cellSizeInput.value = tile.editor_cell_size || 80;
  imageScaleInput.value = Math.round((tile.image_scale || 1) * 100);
  imageOffsetXInput.value = tile.image_offset_x || 0;
  imageOffsetYInput.value = tile.image_offset_y || 0;
  descriptionInput.value = tile.description || "";
  renderStatusOptions(tile.implementation_status || "placeholder-needs-rulebook-validation");
  renderGrid(tile);
  renderExitList(tile);
  renderTools();
}

function renderStatusOptions(currentStatus) {
  implementationStatusInput.replaceChildren();
  const known = new Set(STATUS_OPTIONS.map(([value]) => value));
  for (const [value, label] of STATUS_OPTIONS) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === currentStatus;
    implementationStatusInput.appendChild(option);
  }
  if (currentStatus && !known.has(currentStatus)) {
    const option = document.createElement("option");
    option.value = currentStatus;
    option.textContent = currentStatus;
    option.selected = true;
    implementationStatusInput.appendChild(option);
  }
}

function renderTools() {
  const startTile = isStartingTile(selectedTile());
  for (const button of toolButtons.querySelectorAll("button")) {
    if (button.dataset.mode === "dungeon_exit") {
      button.disabled = !startTile;
    }
    button.classList.toggle("selected", button.dataset.mode === editor.mode);
  }
  editorStage.classList.toggle("move-mode", editor.mode === "move_image");
}

function renderGrid(tile) {
  normalizeTile(tile);
  if (editor.mode === "dungeon_exit" && !isStartingTile(tile)) {
    editor.mode = "passage";
    renderTools();
  }
  gridOverlay.replaceChildren();
  exitOverlay.replaceChildren();
  applyStageLayout(tile);
  gridOverlay.style.gridTemplateColumns = `repeat(${tile.footprint_width}, minmax(0, 1fr))`;
  gridOverlay.style.gridTemplateRows = `repeat(${tile.footprint_height}, minmax(0, 1fr))`;

  for (let y = 0; y < tile.footprint_height; y += 1) {
    for (let x = 0; x < tile.footprint_width; x += 1) {
      const square = document.createElement("button");
      square.type = "button";
      square.className = `grid-square ${isWalkable(tile, x, y) ? "walkable" : "blocked"} shape-${cellShape(tile, x, y)}`;
      square.dataset.x = x;
      square.dataset.y = y;
      square.title = `${squareDescription(tile, x, y)} square ${x + 1},${y + 1}`;
      square.setAttribute("aria-label", square.title);
      square.addEventListener("click", (event) => handleGridClick(tile, x, y, event));
      gridOverlay.appendChild(square);
    }
  }

  tile.exits.forEach((exit, index) => {
    exitOverlay.appendChild(exitMarker(tile, exit, index));
  });
}

function applyStageLayout(tile) {
  const width = tile.footprint_width * tile.editor_cell_size;
  const height = tile.footprint_height * tile.editor_cell_size;
  editorStage.style.width = `${width}px`;
  editorStage.style.height = `${height}px`;
  tilePreview.style.transform = imageTransform(tile);
}

function renderExitList(tile) {
  exitList.replaceChildren();
  tile.exits.forEach((exit, index) => {
    const row = document.createElement("div");
    row.className = "exit-row visual-exit-row";
    const number = document.createElement("span");
    number.className = "exit-number";
    number.textContent = String(index + 1);
    number.title = exitLabel(tile, exit);
    const label = document.createElement("div");
    label.className = "exit-label-cell";
    label.appendChild(nodeStrong(exitLabel(tile, exit)));
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent = `canonical ${exit.direction}, square ${exit.x + 1},${exit.y + 1}`;
    label.appendChild(meta);
    const directionControl = directionButtons(tile, exit);
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
    checkbox.disabled = !isStartingTile(tile);
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
    row.append(number, label, directionControl, kind, dungeonExit, remove);
    exitList.appendChild(row);
  });
}

function nodeStrong(text) {
  const strong = document.createElement("strong");
  strong.textContent = text;
  return strong;
}

function directionButtons(tile, exit) {
  const wrap = document.createElement("div");
  wrap.className = "direction-buttons";
  for (const direction of ["north", "east", "south", "west"]) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "direction-button";
    if (exit.direction === direction) button.classList.add("selected");
    button.textContent = direction[0].toUpperCase();
    button.title = `Place on ${direction} side in canonical orientation`;
    button.addEventListener("click", () => {
      setExitDirection(tile, exit, direction);
      renderGrid(tile);
      renderExitList(tile);
    });
    wrap.appendChild(button);
  }
  return wrap;
}

function setExitDirection(tile, exit, direction) {
  const offset = exitOffset(exit.direction, exit.x, exit.y);
  exit.direction = direction;
  if (direction === "north" || direction === "south") {
    exit.x = clampNumber(offset, 0, tile.footprint_width - 1);
    exit.y = direction === "north" ? 0 : tile.footprint_height - 1;
  } else {
    exit.x = direction === "west" ? 0 : tile.footprint_width - 1;
    exit.y = clampNumber(offset, 0, tile.footprint_height - 1);
  }
  exit.offset = exitOffset(exit.direction, exit.x, exit.y);
  exit.position = exitPosition(exit.direction, exit.offset, tile.footprint_width, tile.footprint_height);
}

function handleGridClick(tile, x, y, event) {
  if (editor.suppressNextGridClick || event.ctrlKey) {
    editor.suppressNextGridClick = false;
    return;
  }

  if (editor.mode === "move_image") {
    return;
  }

  if (editor.mode === "walkable" || editor.mode === "blocked") {
    setWalkable(tile, x, y, editor.mode === "walkable");
    setCellShape(tile, x, y, "F");
    renderGrid(tile);
    return;
  }

  if (editor.mode.startsWith("half_")) {
    setWalkable(tile, x, y, true);
    setCellShape(tile, x, y, halfShape(editor.mode));
    renderGrid(tile);
    return;
  }

  const direction = nearestEdge(event);
  if (editor.mode === "erase_exit") {
    tile.exits = tile.exits.filter((exit) => !(exit.x === x && exit.y === y && exit.direction === direction));
  } else {
    if (editor.mode === "dungeon_exit" && !isStartingTile(tile)) return;
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
  tile.exits.push(newExit(tile, {
    direction,
    kind,
    x,
    y,
    dungeon_exit: dungeonExit,
  }));
}

function newExit(tile, values) {
  const direction = values.direction || "north";
  const x = clampNumber(values.x || 0, 0, tile.footprint_width - 1);
  const y = clampNumber(values.y || 0, 0, tile.footprint_height - 1);
  const offset = exitOffset(direction, x, y);
  return {
    id: newExitId(tile),
    label: "",
    direction,
    kind: values.kind === "door" ? "door" : "passage",
    x,
    y,
    offset,
    position: exitPosition(direction, offset, tile.footprint_width, tile.footprint_height),
    dungeon_exit: Boolean(values.dungeon_exit),
  };
}

function exitMarker(tile, exit, index) {
  const marker = document.createElement("button");
  marker.type = "button";
  marker.className = `exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""} ${exit.direction}`;
  marker.title = exitLabel(tile, exit);
  const badge = document.createElement("span");
  badge.className = "exit-marker-badge";
  badge.textContent = String(index + 1);
  marker.appendChild(badge);
  positionExitMarker(marker, tile, exit);
  marker.addEventListener("pointerdown", (event) => startExitDrag(event, tile, exit));
  return marker;
}

function positionExitMarker(marker, tile, exit) {
  const cellW = 100 / tile.footprint_width;
  const cellH = 100 / tile.footprint_height;
  const left = exit.x * cellW;
  const top = exit.y * cellH;
  marker.className = `exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""} ${exit.direction}`;
  if (exit.direction === "north" || exit.direction === "south") {
    marker.style.left = `${left + cellW * 0.5}%`;
    marker.style.top = `${top + (exit.direction === "north" ? 0 : cellH)}%`;
    marker.style.width = `${cellW * 0.6}%`;
    marker.style.height = "";
  } else {
    marker.style.left = `${left + (exit.direction === "west" ? 0 : cellW)}%`;
    marker.style.top = `${top + cellH * 0.5}%`;
    marker.style.height = `${cellH * 0.6}%`;
    marker.style.width = "";
  }
}

function startExitDrag(event, tile, exit) {
  event.preventDefault();
  event.stopPropagation();
  const marker = event.currentTarget;
  marker.setPointerCapture(event.pointerId);

  const move = (moveEvent) => {
    const placement = placementFromPoint(tile, moveEvent.clientX, moveEvent.clientY);
    exit.x = placement.x;
    exit.y = placement.y;
    exit.direction = placement.direction;
    exit.offset = exitOffset(exit.direction, exit.x, exit.y);
    exit.position = exitPosition(exit.direction, exit.offset, tile.footprint_width, tile.footprint_height);
    positionExitMarker(marker, tile, exit);
    renderExitList(tile);
  };

  const stop = () => {
    marker.removeEventListener("pointermove", move);
    marker.removeEventListener("pointerup", stop);
    marker.removeEventListener("pointercancel", stop);
    renderGrid(tile);
    renderExitList(tile);
  };

  marker.addEventListener("pointermove", move);
  marker.addEventListener("pointerup", stop);
  marker.addEventListener("pointercancel", stop);
}

function placementFromPoint(tile, clientX, clientY) {
  const rect = editorStage.getBoundingClientRect();
  const localX = Math.max(0, Math.min(rect.width - 1, clientX - rect.left));
  const localY = Math.max(0, Math.min(rect.height - 1, clientY - rect.top));
  const cellSize = tile.editor_cell_size || 80;
  const x = Math.max(0, Math.min(tile.footprint_width - 1, Math.floor(localX / cellSize)));
  const y = Math.max(0, Math.min(tile.footprint_height - 1, Math.floor(localY / cellSize)));
  const cellLeft = x * cellSize;
  const cellTop = y * cellSize;
  const distances = [
    ["north", localY - cellTop],
    ["east", cellLeft + cellSize - localX],
    ["south", cellTop + cellSize - localY],
    ["west", localX - cellLeft],
  ];
  distances.sort((a, b) => a[1] - b[1]);
  return { x, y, direction: distances[0][0] };
}

function persistForm() {
  const tile = selectedTile();
  if (!tile) return;
  tile.name = nameInput.value.trim() || `Map Element ${tile.key}`;
  tile.tile_type = typeInput.value;
  tile.footprint_width = clampNumber(widthInput.value, 1, 20);
  tile.footprint_height = clampNumber(heightInput.value, 1, 20);
  tile.editor_cell_size = clampNumber(cellSizeInput.value, 24, 180);
  tile.image_scale = clampNumber(imageScaleInput.value, 10, 500) / 100;
  tile.image_offset_x = clampNumber(imageOffsetXInput.value, -1000, 1000);
  tile.image_offset_y = clampNumber(imageOffsetYInput.value, -1000, 1000);
  tile.description = descriptionInput.value.trim();
  tile.implementation_status = implementationStatusInput.value || "edited-needs-rulebook-validation";
  normalizeTile(tile);
}

function normalizeTile(tile) {
  tile.footprint_width = clampNumber(tile.footprint_width || 1, 1, 20);
  tile.footprint_height = clampNumber(tile.footprint_height || 1, 1, 20);
  tile.editor_cell_size = clampNumber(tile.editor_cell_size || 80, 24, 180);
  tile.image_scale = clampFloat(tile.image_scale || 1, 0.1, 5);
  tile.image_offset_x = clampNumber(tile.image_offset_x || 0, -1000, 1000);
  tile.image_offset_y = clampNumber(tile.image_offset_y || 0, -1000, 1000);
  tile.walkable = normalizeWalkable(tile.walkable, tile.footprint_width, tile.footprint_height);
  tile.cell_shapes = normalizeCellShapes(tile.cell_shapes, tile.footprint_width, tile.footprint_height);
  tile.exits = (tile.exits || []).map((exit) => normalizeExit(tile, exit));
  if (!isStartingTile(tile)) {
    tile.exits.forEach((exit) => {
      exit.dungeon_exit = false;
    });
  }
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

function normalizeCellShapes(rows, width, height) {
  const normalized = [];
  const source = Array.isArray(rows) ? rows : [];
  const allowed = new Set(["F", "A", "B", "C", "D"]);
  for (let y = 0; y < height; y += 1) {
    const sourceRow = String(source[y] || "");
    let row = "";
    for (let x = 0; x < width; x += 1) {
      row += allowed.has(sourceRow[x]) ? sourceRow[x] : "F";
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
    label: "",
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

function cellShape(tile, x, y) {
  return tile.cell_shapes[y]?.[x] || "F";
}

function setWalkable(tile, x, y, value) {
  const row = tile.walkable[y].split("");
  row[x] = value ? "1" : "0";
  tile.walkable[y] = row.join("");
}

function setCellShape(tile, x, y, value) {
  const row = tile.cell_shapes[y].split("");
  row[x] = value;
  tile.cell_shapes[y] = row.join("");
}

function halfShape(mode) {
  return { half_a: "A", half_b: "B", half_c: "C", half_d: "D" }[mode] || "F";
}

function squareDescription(tile, x, y) {
  if (!isWalkable(tile, x, y)) return "Blocked";
  const descriptions = {
    F: "Walkable",
    A: "Blocked NE half",
    B: "Blocked NW half",
    C: "Blocked SE half",
    D: "Blocked SW half",
  };
  return descriptions[cellShape(tile, x, y)] || "Walkable";
}

function imageTransform(tile) {
  return `translate(calc(-50% + ${tile.image_offset_x}px), calc(-50% + ${tile.image_offset_y}px)) scale(${tile.image_scale})`;
}

function updateCalibrationInputs(tile) {
  imageScaleInput.value = Math.round((tile.image_scale || 1) * 100);
  imageOffsetXInput.value = tile.image_offset_x || 0;
  imageOffsetYInput.value = tile.image_offset_y || 0;
}

function adjustImageOffset(action) {
  const tile = selectedTile();
  if (!tile) return;
  const step = 5;
  if (action === "x-decrease") tile.image_offset_x = clampNumber((tile.image_offset_x || 0) - step, -1000, 1000);
  if (action === "x-increase") tile.image_offset_x = clampNumber((tile.image_offset_x || 0) + step, -1000, 1000);
  if (action === "y-decrease") tile.image_offset_y = clampNumber((tile.image_offset_y || 0) - step, -1000, 1000);
  if (action === "y-increase") tile.image_offset_y = clampNumber((tile.image_offset_y || 0) + step, -1000, 1000);
  updateCalibrationInputs(tile);
  applyStageLayout(tile);
}

function startImageDrag(event) {
  if ((editor.mode !== "move_image" && !event.ctrlKey) || event.button !== 0) return;
  const tile = selectedTile();
  if (!tile) return;
  event.preventDefault();
  event.stopPropagation();
  editor.suppressNextGridClick = true;
  editorStage.setPointerCapture(event.pointerId);
  const startX = event.clientX;
  const startY = event.clientY;
  const startOffsetX = tile.image_offset_x || 0;
  const startOffsetY = tile.image_offset_y || 0;

  const move = (moveEvent) => {
    tile.image_offset_x = clampNumber(startOffsetX + Math.round(moveEvent.clientX - startX), -1000, 1000);
    tile.image_offset_y = clampNumber(startOffsetY + Math.round(moveEvent.clientY - startY), -1000, 1000);
    updateCalibrationInputs(tile);
    applyStageLayout(tile);
  };

  const stop = () => {
    editorStage.removeEventListener("pointermove", move);
    editorStage.removeEventListener("pointerup", stop);
    editorStage.removeEventListener("pointercancel", stop);
  };

  editorStage.addEventListener("pointermove", move);
  editorStage.addEventListener("pointerup", stop);
  editorStage.addEventListener("pointercancel", stop);
}

function zoomImage(event) {
  const tile = selectedTile();
  if (!tile) return;
  event.preventDefault();
  const step = event.deltaY < 0 ? 0.05 : -0.05;
  tile.image_scale = clampFloat((tile.image_scale || 1) + step, 0.1, 5);
  updateCalibrationInputs(tile);
  applyStageLayout(tile);
}

function addDefaultExit(tile) {
  normalizeTile(tile);
  const placement = firstAvailableExitPlacement(tile);
  const mode = editor.mode === "door" || (editor.mode === "dungeon_exit" && isStartingTile(tile)) ? editor.mode : "passage";
  const dungeonExit = mode === "dungeon_exit" && isStartingTile(tile);
  const kind = dungeonExit ? "passage" : mode;
  tile.exits.push(
    newExit(tile, {
      direction: placement.direction,
      kind,
      x: placement.x,
      y: placement.y,
      dungeon_exit: dungeonExit,
    })
  );
}

function firstAvailableExitPlacement(tile) {
  const candidates = [];
  for (let x = 0; x < tile.footprint_width; x += 1) candidates.push({ direction: "north", x, y: 0 });
  for (let y = 0; y < tile.footprint_height; y += 1) candidates.push({ direction: "east", x: tile.footprint_width - 1, y });
  for (let x = tile.footprint_width - 1; x >= 0; x -= 1) candidates.push({ direction: "south", x, y: tile.footprint_height - 1 });
  for (let y = tile.footprint_height - 1; y >= 0; y -= 1) candidates.push({ direction: "west", x: 0, y });
  return (
    candidates.find(
      (candidate) =>
        !tile.exits.some(
          (exit) => exit.direction === candidate.direction && exit.x === candidate.x && exit.y === candidate.y
        )
    ) || { direction: "north", x: 0, y: 0 }
  );
}

function exitOffset(direction, x, y) {
  return direction === "north" || direction === "south" ? x : y;
}

function exitPosition(direction, offset, width, height) {
  const side = direction === "north" || direction === "south" ? width : height;
  return side <= 1 ? 0.5 : offset / (side - 1);
}

function exitLabel(tile, exit) {
  const side = exitSideLabels(tile).get(exit.id) || titleCase(exit.direction);
  return `${side} ${exit.dungeon_exit ? "Dungeon Exit" : titleCase(exit.kind)}`;
}

function exitSideLabels(tile) {
  const labels = new Map();
  const groups = new Map();
  for (const exit of tile.exits || []) {
    if (!groups.has(exit.direction)) groups.set(exit.direction, []);
    groups.get(exit.direction).push(exit);
  }
  for (const [direction, exits] of groups.entries()) {
    exits.sort((left, right) => exitSortValue(left) - exitSortValue(right));
    exits.forEach((exit, index) => {
      labels.set(exit.id, `${titleCase(direction)}${exits.length > 1 ? ` ${index + 1}` : ""}`);
    });
  }
  return labels;
}

function exitSortValue(exit) {
  return exit.direction === "north" || exit.direction === "south" ? exit.x : exit.y;
}

function titleCase(value) {
  return value[0].toUpperCase() + value.slice(1);
}

function clampNumber(value, min, max) {
  const number = Number.parseInt(value, 10);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function clampFloat(value, min, max) {
  const number = Number.parseFloat(value);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function newExitId(tile) {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return `${tile.key}-exit-${window.crypto.randomUUID()}`;
  }
  return `${tile.key}-exit-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
}

function isStartingTile(tile) {
  return Boolean(tile && /^0[1-6]$/.test(tile.key));
}

toolButtons.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-mode]");
  if (!button) return;
  if (button.disabled) return;
  editor.mode = button.dataset.mode;
  renderTools();
});

for (const input of [widthInput, heightInput, cellSizeInput, imageScaleInput, imageOffsetXInput, imageOffsetYInput]) {
  input.addEventListener("change", () => {
    persistForm();
    renderSelectedTile();
  });
}

document.querySelectorAll("[data-offset-action]").forEach((button) => {
  button.addEventListener("click", () => adjustImageOffset(button.dataset.offsetAction));
});

editorStage.addEventListener("pointerdown", startImageDrag);
editorStage.addEventListener("wheel", zoomImage, { passive: false });

addExitButton.addEventListener("click", () => {
  const tile = selectedTile();
  if (!tile) return;
  addDefaultExit(tile);
  renderGrid(tile);
  renderExitList(tile);
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
