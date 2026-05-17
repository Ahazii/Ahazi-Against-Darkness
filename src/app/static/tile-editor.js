const editor = {
  tiles: [],
  selectedKey: null,
  mode: "walkable",
  previewRotation: 0,
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
const rotationPreview = document.getElementById("rotation-preview");
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
      editor.previewRotation = 0;
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
  renderRotationPreview();
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
  const previewing = editor.previewRotation !== 0;
  for (const button of toolButtons.querySelectorAll("button")) {
    button.disabled = previewing || (button.dataset.mode === "dungeon_exit" && !startTile);
    button.classList.toggle("selected", !previewing && button.dataset.mode === editor.mode);
  }
  editorStage.classList.toggle("move-mode", !previewing && editor.mode === "move_image");
  editorStage.classList.toggle("rotation-preview", previewing);
}

function renderRotationPreview() {
  for (const button of rotationPreview.querySelectorAll("button[data-preview-rotation]")) {
    button.classList.toggle("selected", Number(button.dataset.previewRotation) === editor.previewRotation);
  }
}

function renderGrid(tile) {
  normalizeTile(tile);
  if (editor.mode === "dungeon_exit" && !isStartingTile(tile)) {
    editor.mode = "passage";
    renderTools();
  }
  gridOverlay.replaceChildren();
  exitOverlay.replaceChildren();
  const view = tileView(tile);
  applyStageLayout(tile, view);
  gridOverlay.style.gridTemplateColumns = `repeat(${view.footprint_width}, minmax(0, 1fr))`;
  gridOverlay.style.gridTemplateRows = `repeat(${view.footprint_height}, minmax(0, 1fr))`;

  for (let y = 0; y < view.footprint_height; y += 1) {
    for (let x = 0; x < view.footprint_width; x += 1) {
      const square = document.createElement("button");
      square.type = "button";
      square.className = `grid-square ${view.walkable[y]?.[x] !== "0" ? "walkable" : "blocked"} shape-${view.cell_shapes[y]?.[x] || "F"}`;
      square.dataset.x = x;
      square.dataset.y = y;
      square.title =
        editor.previewRotation === 0
          ? `${squareDescription(tile, x, y)} square ${x + 1},${y + 1}`
          : `Read-only ${editor.previewRotation}deg rotation preview`;
      square.setAttribute("aria-label", square.title);
      if (editor.previewRotation === 0) {
        square.addEventListener("click", (event) => handleGridClick(tile, x, y, event));
      }
      gridOverlay.appendChild(square);
    }
  }

  view.exits.forEach((displayExit, index) => {
    exitOverlay.appendChild(exitMarker(tile, displayExit.source, index, displayExit, view));
  });
}

function applyStageLayout(tile, view = tileView(tile)) {
  const width = view.footprint_width * tile.editor_cell_size;
  const height = view.footprint_height * tile.editor_cell_size;
  editorStage.style.width = `${width}px`;
  editorStage.style.height = `${height}px`;
  tilePreview.style.width = `${tile.footprint_width * tile.editor_cell_size}px`;
  tilePreview.style.height = `${tile.footprint_height * tile.editor_cell_size}px`;
  tilePreview.style.transform = imageTransform(tile);
}

function renderExitList(tile) {
  exitList.replaceChildren();
  const view = tileView(tile);
  const displayExits = new Map(view.exits.map((exit) => [exit.id, exit]));
  tile.exits.forEach((exit, index) => {
    const displayExit = displayExits.get(exit.id) || exit;
    const row = document.createElement("div");
    row.className = "exit-row visual-exit-row";
    const number = document.createElement("span");
    number.className = "exit-number";
    number.textContent = String(index + 1);
    number.title = exitLabel(view, displayExit);
    const label = document.createElement("div");
    label.className = "exit-label-cell";
    label.appendChild(nodeStrong(exitLabel(view, displayExit)));
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent = `canonical ${exit.direction}, square ${exit.x + 1},${exit.y + 1}, span ${exit.span || 1}`;
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
    const span = document.createElement("label");
    span.className = "span-field";
    span.appendChild(document.createTextNode("Span"));
    const spanInput = document.createElement("input");
    spanInput.type = "number";
    spanInput.min = "1";
    spanInput.max = String(maxExitSpan(tile, exit.direction, exit.x, exit.y));
    spanInput.value = exit.span || 1;
    spanInput.addEventListener("change", () => {
      exit.span = clampExitSpan(tile, exit.direction, spanInput.value, exit.x, exit.y);
      renderGrid(tile);
      renderExitList(tile);
    });
    span.appendChild(spanInput);
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
    row.append(number, label, directionControl, kind, span, dungeonExit, remove);
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
  exit.direction = direction;
  exit.x = clampNumber(exit.x, 0, tile.footprint_width - 1);
  exit.y = clampNumber(exit.y, 0, tile.footprint_height - 1);
  exit.span = clampExitSpan(tile, exit.direction, exit.span || 1, exit.x, exit.y);
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
  const span = clampExitSpan(tile, direction, values.span || 1, x, y);
  const offset = exitOffset(direction, x, y);
  return {
    id: newExitId(tile),
    label: "",
    direction,
    kind: values.kind === "door" ? "door" : "passage",
    x,
    y,
    span,
    offset,
    position: exitPosition(direction, offset, tile.footprint_width, tile.footprint_height),
    dungeon_exit: Boolean(values.dungeon_exit),
  };
}

function exitMarker(tile, exit, index, displayExit = exit, view = tileView(tile)) {
  const marker = document.createElement("button");
  marker.type = "button";
  marker.className = `exit-marker ${displayExit.kind}${displayExit.dungeon_exit ? " dungeon-exit" : ""} ${displayExit.direction}`;
  marker.title = exitLabel(view, displayExit);
  const badge = document.createElement("span");
  badge.className = "exit-marker-badge";
  badge.textContent = String(index + 1);
  marker.appendChild(badge);
  positionExitMarker(marker, view, displayExit);
  if (editor.previewRotation === 0) {
    marker.addEventListener("pointerdown", (event) => startExitDrag(event, tile, exit));
  } else {
    marker.classList.add("preview-only");
  }
  return marker;
}

function positionExitMarker(marker, tile, exit) {
  const cellW = 100 / tile.footprint_width;
  const cellH = 100 / tile.footprint_height;
  const span = clampExitSpan(tile, exit.direction, exit.span || 1, exit.x, exit.y);
  const left = exit.x * cellW;
  const top = exit.y * cellH;
  marker.className = `exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""} ${exit.direction}`;
  if (exit.direction === "north" || exit.direction === "south") {
    marker.style.left = `${left + cellW * (span / 2)}%`;
    marker.style.top = `${top + (exit.direction === "north" ? 0 : cellH)}%`;
    marker.style.width = `${cellW * Math.max(0.72, span - 0.16)}%`;
    marker.style.height = "";
  } else {
    marker.style.left = `${left + (exit.direction === "west" ? 0 : cellW)}%`;
    marker.style.top = `${top + cellH * (span / 2)}%`;
    marker.style.height = `${cellH * Math.max(0.72, span - 0.16)}%`;
    marker.style.width = "";
  }
}

function startExitDrag(event, tile, exit) {
  event.preventDefault();
  event.stopPropagation();
  const marker = event.currentTarget;
  marker.setPointerCapture(event.pointerId);

  const move = (moveEvent) => {
    const placement = placementFromPoint(tile, moveEvent.clientX, moveEvent.clientY, exit.direction);
    exit.x = placement.x;
    exit.y = placement.y;
    exit.direction = placement.direction;
    exit.span = clampExitSpan(tile, exit.direction, exit.span || 1, exit.x, exit.y);
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

function placementFromPoint(tile, clientX, clientY, direction) {
  const rect = editorStage.getBoundingClientRect();
  const localX = Math.max(0, Math.min(rect.width - 1, clientX - rect.left));
  const localY = Math.max(0, Math.min(rect.height - 1, clientY - rect.top));
  const cellSize = tile.editor_cell_size || 80;
  const probeX = direction === "east" ? Math.max(0, localX - 1) : localX;
  const probeY = direction === "south" ? Math.max(0, localY - 1) : localY;
  const x = Math.max(0, Math.min(tile.footprint_width - 1, Math.floor(probeX / cellSize)));
  const y = Math.max(0, Math.min(tile.footprint_height - 1, Math.floor(probeY / cellSize)));
  return { x, y, direction };
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
  const span = clampExitSpan(tile, direction, exit.span || 1, x, y);
  const offset = exitOffset(direction, x, y);
  return {
    id: exit.id || newExitId(tile),
    label: "",
    direction,
    kind: exit.kind === "door" ? "door" : "passage",
    x,
    y,
    span,
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
  const offset = rotatedOffset(tile.image_offset_x || 0, tile.image_offset_y || 0, editor.previewRotation);
  return `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px) rotate(${editor.previewRotation}deg) scale(${tile.image_scale})`;
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
  applyStageLayout(tile, tileView(tile));
}

function startImageDrag(event) {
  if (editor.previewRotation !== 0) return;
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
    applyStageLayout(tile, tileView(tile));
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
  if (editor.previewRotation !== 0) return;
  event.preventDefault();
  const step = event.deltaY < 0 ? 0.05 : -0.05;
  tile.image_scale = clampFloat((tile.image_scale || 1) + step, 0.1, 5);
  updateCalibrationInputs(tile);
  applyStageLayout(tile, tileView(tile));
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

function tileView(tile) {
  const rotation = editor.previewRotation || 0;
  const [width, height] = rotatedSize(tile.footprint_width, tile.footprint_height, rotation);
  return {
    ...tile,
    footprint_width: width,
    footprint_height: height,
    walkable: rotateRows(tile.walkable, tile.footprint_width, tile.footprint_height, rotation),
    cell_shapes: rotateRows(tile.cell_shapes, tile.footprint_width, tile.footprint_height, rotation, rotateCellShape),
    exits: (tile.exits || []).map((exit) => rotatedExit(tile, exit, rotation)),
  };
}

function rotatedExit(tile, exit, rotation) {
  if (rotation === 0) return { ...exit, source: exit };
  const direction = rotateDirection(exit.direction, rotation);
  const cells = exitCells(tile, exit).map((cell) => rotateCell(cell.x, cell.y, tile.footprint_width, tile.footprint_height, rotation));
  const xs = cells.map((cell) => cell.x);
  const ys = cells.map((cell) => cell.y);
  const x = direction === "north" || direction === "south" ? Math.min(...xs) : xs[0];
  const y = direction === "east" || direction === "west" ? Math.min(...ys) : ys[0];
  const span =
    direction === "north" || direction === "south"
      ? Math.max(...xs) - Math.min(...xs) + 1
      : Math.max(...ys) - Math.min(...ys) + 1;
  return {
    ...exit,
    direction,
    x,
    y,
    span,
    offset: exitOffset(direction, x, y),
    source: exit,
  };
}

function exitCells(tile, exit) {
  const span = clampExitSpan(tile, exit.direction, exit.span || 1, exit.x, exit.y);
  return Array.from({ length: span }, (_, index) => ({
    x: exit.direction === "north" || exit.direction === "south" ? exit.x + index : exit.x,
    y: exit.direction === "east" || exit.direction === "west" ? exit.y + index : exit.y,
  }));
}

function rotateRows(rows, width, height, rotation, transformValue = (value) => value) {
  if (rotation === 0) return rows;
  const [rotatedWidth, rotatedHeight] = rotatedSize(width, height, rotation);
  const rotated = Array.from({ length: rotatedHeight }, () => Array.from({ length: rotatedWidth }, () => "0"));
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const cell = rotateCell(x, y, width, height, rotation);
      rotated[cell.y][cell.x] = transformValue(rows[y]?.[x] || "0", rotation);
    }
  }
  return rotated.map((row) => row.join(""));
}

function rotateCell(x, y, width, height, rotation) {
  const turns = (rotation / 90) % 4;
  if (turns === 1) return { x: height - 1 - y, y: x };
  if (turns === 2) return { x: width - 1 - x, y: height - 1 - y };
  if (turns === 3) return { x: y, y: width - 1 - x };
  return { x, y };
}

function rotatedSize(width, height, rotation) {
  return rotation === 90 || rotation === 270 ? [height, width] : [width, height];
}

function rotateDirection(direction, rotation) {
  const directions = ["north", "east", "south", "west"];
  const turns = (rotation / 90) % 4;
  return directions[(directions.indexOf(direction) + turns) % 4];
}

function rotateCellShape(value, rotation) {
  const turns = (rotation / 90) % 4;
  const maps = [
    {},
    { A: "C", C: "D", D: "B", B: "A" },
    { A: "D", D: "A", B: "C", C: "B" },
    { A: "B", B: "D", D: "C", C: "A" },
  ];
  return maps[turns]?.[value] || value;
}

function rotatedOffset(x, y, rotation) {
  const turns = (rotation / 90) % 4;
  if (turns === 1) return { x: -y, y: x };
  if (turns === 2) return { x: -x, y: -y };
  if (turns === 3) return { x: y, y: -x };
  return { x, y };
}

function exitLabel(tile, exit) {
  const side = exitSideLabels(tile).get(exit.id) || titleCase(exit.direction);
  return `${side} ${exit.dungeon_exit ? "Dungeon Exit" : titleCase(exit.kind)}`;
}

function exitSideLabels(tile) {
  const labels = new Map();
  const counts = new Map();
  for (const exit of tile.exits || []) {
    const direction = exit.direction || "north";
    const nextCount = (counts.get(direction) || 0) + 1;
    counts.set(direction, nextCount);
    labels.set(exit.id, `${titleCase(direction)} ${nextCount}`);
  }
  return labels;
}

function titleCase(value) {
  return value[0].toUpperCase() + value.slice(1);
}

function clampExitSpan(tile, direction, value, x, y) {
  return clampNumber(value, 1, maxExitSpan(tile, direction, x, y));
}

function maxExitSpan(tile, direction, x, y) {
  if (direction === "north" || direction === "south") {
    return Math.max(1, tile.footprint_width - clampNumber(x, 0, tile.footprint_width - 1));
  }
  return Math.max(1, tile.footprint_height - clampNumber(y, 0, tile.footprint_height - 1));
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

rotationPreview.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-preview-rotation]");
  if (!button) return;
  persistForm();
  editor.previewRotation = Number(button.dataset.previewRotation);
  const tile = selectedTile();
  if (!tile) return;
  renderGrid(tile);
  renderExitList(tile);
  renderTools();
  renderRotationPreview();
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
