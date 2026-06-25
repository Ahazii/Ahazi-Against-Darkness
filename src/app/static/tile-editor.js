const editor = {
  catalog: "ee",
  tiles: [],
  selectedKey: null,
  mode: "walkable_toggle",
  paintSurface: "floor",
  previewRotation: 0,
  imageLocked: true,
  suppressNextGridClick: false,
  listFilter: "all",
  roomCodeReference: [],
};

const STATUS_OPTIONS = [
  ["placeholder-needs-rulebook-validation", "Placeholder - needs rulebook validation"],
  ["starter-needs-rulebook-validation", "Starter - needs rulebook validation"],
  ["edited-needs-rulebook-validation", "Edited - needs rulebook validation"],
  ["validated", "Validated against rulebook"],
];

const HELP_TOPICS = {
  "validation-status": {
    title: "Validation Status",
    paragraphs: [
      "This is a manual review flag for the map element metadata. It does not change gameplay by itself.",
      "Use Placeholder when the row is still copied from the starter data, Starter when the first pass exists, Edited when you have changed it but not fully checked it, and Validated only after checking the element against the rulebook art/table.",
      "The Ready tag also requires this field to be Validated."
    ],
  },
  "element-tags": {
    title: "Map Element Tags",
    paragraphs: [
      "Ready means the element has no validation errors or warnings.",
      "Needs work means the element has at least one warning or error. Warnings usually mean the element can still be used, but it has not been fully reviewed.",
      "Errors means a hard problem was found, such as missing room type, no walkable squares, invalid dungeon exit placement, blocked exit anchors, or no exits."
    ],
  },
  "exit-placement": {
    title: "Exit Placement",
    paragraphs: [
      "Door and passage markers store the exact square and side you place in the editor.",
      "If an inset exit has one blocked padding square outside it, gameplay keeps the marker in that authored position and lets the connected tile overlap that blocked padding.",
      "A marker may be placed on that single blocked padding square when the square directly inside, opposite the exit direction, is walkable or water.",
      "Use Delete Exit, or the Remove button in this list, to delete a door or passage placed by mistake.",
    ],
  },
  "room-codes": {
    title: "Forsaken Depths Room Codes",
    paragraphs: [
      "Dungeon tiles (FD p.32): NC = narrow corridor; ETC = entrance to Citadel (separate sheet); ETR = exit to river (separate river map).",
      "River stretch tiles (FD River Hazard p.30 and pp.37–40): ETC = entrance to Citadel; END = river end; Ru = ruin; Ca = cairn (printed as C); B = bridge.",
      "Most rooms and stretches have no letter code — leave all checkboxes unchecked for a normal room or ordinary river stretch.",
      "Mark only the codes printed on the scan or confirmed from the rulebook for that element.",
    ],
  },
  water: {
    title: "Water Shape Mode",
    paragraphs: [
      "On Forsaken Depths river stretches, Water toggles the shape tools between green walkable floor and blue river water.",
      "With Water active, use Walk/Block, Half, Slope, Long Slope, Curve, or Half Curve normally. The selected geometry keeps its blocked red portion and paints its open portion as water.",
      "Click Water again to return the shape tools to walkable floor.",
      "Water is not on-foot walkable; boat navigation rules apply when river play is implemented.",
      "Place passage exits on the water opening where the navigable channel continues, and match the exit span to the channel width. Use bank exits only for separate printed foot routes.",
    ],
  },
};

const CELL_SHAPE_MODES = {
  half_cycle: ["a", "b", "c", "d", "A", "B", "C", "D"],
  slope_cycle: ["E", "G", "H", "I"],
  curve_cycle: ["e", "g", "h", "i", "J", "K", "L", "M"],
};

const EXIT_DIRECTIONS = ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"];
const EXIT_DIRECTION_LABELS = {
  north: "N",
  northeast: "NE",
  east: "E",
  southeast: "SE",
  south: "S",
  southwest: "SW",
  west: "W",
  northwest: "NW",
};
const EXIT_SPAN_STEPS = {
  north: [1, 0],
  south: [1, 0],
  east: [0, 1],
  west: [0, 1],
  northeast: [1, 1],
  southwest: [1, 1],
  southeast: [1, -1],
  northwest: [1, -1],
};
const EXIT_DIRECTION_DELTAS = {
  north: [0, -1],
  northeast: [1, -1],
  east: [1, 0],
  southeast: [1, 1],
  south: [0, 1],
  southwest: [-1, 1],
  west: [-1, 0],
  northwest: [-1, -1],
};

const HALF_CURVE_CYCLE = [
  "f",
  "j",
  "k",
  "l",
  "z",
  "2",
  "3",
  "m",
  "n",
  "o",
  "p",
  "Z",
  "7",
  "8",
  "q",
  "r",
  "s",
  "t",
  "9",
  "0",
  "y",
  "u",
  "v",
  "w",
  "x",
  "4",
  "5",
  "6",
];

const BIDIRECTIONAL_GRID_MODES = new Set([
  "walkable_toggle",
  "half_cycle",
  "slope_cycle",
  "curve_cycle",
  "half_curve_cycle",
  "long_slope_cycle",
]);

const WALKABLE_SURFACE_CYCLE = [
  { walkable: "0", shape: "F" },
  { walkable: "1", shape: "V" },
  { walkable: "1", shape: "W" },
  { walkable: "1", shape: "X" },
  { walkable: "1", shape: "Y" },
  { walkable: "1", shape: "F" },
];

const LONG_SLOPE_CODES = new Set(["N", "O", "P", "Q", "R", "S", "T", "U"]);
const LONG_SLOPE_PATTERNS = [
  { codes: ["N", "O"], cells: [[0, 0], [0, 1]] },
  { codes: ["N", "O"], cells: [[0, -1], [0, 0]] },
  { codes: ["P", "Q"], cells: [[0, 0], [0, 1]] },
  { codes: ["P", "Q"], cells: [[0, -1], [0, 0]] },
  { codes: ["R", "S"], cells: [[0, 0], [1, 0]] },
  { codes: ["R", "S"], cells: [[-1, 0], [0, 0]] },
  { codes: ["T", "U"], cells: [[0, 0], [1, 0]] },
  { codes: ["T", "U"], cells: [[-1, 0], [0, 0]] },
];

const CELL_SHAPE_DESCRIPTIONS = {
  F: "Walkable",
  a: "Blocked NE quarter",
  b: "Blocked NW quarter",
  c: "Blocked SE quarter",
  d: "Blocked SW quarter",
  A: "Blocked NE half",
  B: "Blocked NW half",
  C: "Blocked SE half",
  D: "Blocked SW half",
  V: "Blocked north (top) half",
  W: "Blocked south (bottom) half",
  X: "Blocked west (left) half",
  Y: "Blocked east (right) half",
  E: "Blocked NE shallow slope",
  G: "Blocked NW shallow slope",
  H: "Blocked SE shallow slope",
  I: "Blocked SW shallow slope",
  e: "Blocked NE quarter curve",
  g: "Blocked NW quarter curve",
  h: "Blocked SE quarter curve",
  i: "Blocked SW quarter curve",
  f: "Half top blocked (flat), open bottom half",
  j: "Half top blocked + shallow TL→BR diagonal curve in bottom half",
  k: "Half top blocked + medium TL→BR diagonal curve in bottom half",
  l: "Half top blocked + deep TL→BR diagonal curve in bottom half",
  z: "Half top blocked + shallow TR→BL diagonal curve in bottom half",
  2: "Half top blocked + medium TR→BL diagonal curve in bottom half",
  3: "Half top blocked + deep TR→BL diagonal curve in bottom half",
  m: "Half bottom blocked (flat), open top half",
  n: "Half bottom blocked + shallow TL→BR diagonal curve in top half",
  o: "Half bottom blocked + medium TL→BR diagonal curve in top half",
  p: "Half bottom blocked + deep TL→BR diagonal curve in top half",
  Z: "Half bottom blocked + shallow TR→BL diagonal curve in top half",
  7: "Half bottom blocked + medium TR→BL diagonal curve in top half",
  8: "Half bottom blocked + deep TR→BL diagonal curve in top half",
  q: "Half left blocked (flat), open right half",
  r: "Half left blocked + shallow TL→BR diagonal curve in right half",
  s: "Half left blocked + medium TL→BR diagonal curve in right half",
  t: "Half left blocked + deep TL→BR diagonal curve in right half",
  9: "Half left blocked + shallow TR→BL diagonal curve in right half",
  0: "Half left blocked + medium TR→BL diagonal curve in right half",
  y: "Half left blocked + deep TR→BL diagonal curve in right half",
  u: "Half right blocked (flat), open left half",
  v: "Half right blocked + shallow TL→BR diagonal curve in left half",
  w: "Half right blocked + medium TL→BR diagonal curve in left half",
  x: "Half right blocked + deep TL→BR diagonal curve in left half",
  4: "Half right blocked + shallow TR→BL diagonal curve in left half",
  5: "Half right blocked + medium TR→BL diagonal curve in left half",
  6: "Half right blocked + deep TR→BL diagonal curve in left half",
  J: "Blocked NE curved corner",
  K: "Blocked NW curved corner",
  L: "Blocked SE curved corner",
  M: "Blocked SW curved corner",
  N: "Long blocked slope down right upper square",
  O: "Long blocked slope down right lower square",
  P: "Long blocked slope down left upper square",
  Q: "Long blocked slope down left lower square",
  R: "Long blocked slope right lower-left square",
  S: "Long blocked slope right lower-right square",
  T: "Long blocked slope right upper-left square",
  U: "Long blocked slope right upper-right square",
};

const statusEl = document.getElementById("editor-status");
const tileCatalogSelect = document.getElementById("tile-catalog");
const tileList = document.getElementById("tile-list");
const tileFilter = document.getElementById("tile-filter");
const validationSummary = document.getElementById("validation-summary");
const tileTitle = document.getElementById("tile-title");
const tilePreview = document.getElementById("tile-preview");
const tileSourcePreview = document.getElementById("tile-source-preview");
const nameInput = document.getElementById("edit-name");
const typeInput = document.getElementById("edit-type");
const terrainInput = document.getElementById("edit-terrain");
const roomCodeFieldset = document.getElementById("room-code-fieldset");
const roomCodeOptions = document.getElementById("room-code-options");
const widthInput = document.getElementById("edit-width");
const heightInput = document.getElementById("edit-height");
const cellSizeInput = document.getElementById("edit-cell-size");
const imageScaleInput = document.getElementById("edit-image-scale");
const imageOffsetXInput = document.getElementById("edit-image-offset-x");
const imageOffsetYInput = document.getElementById("edit-image-offset-y");
const lockImageInput = document.getElementById("lock-image");
const descriptionInput = document.getElementById("edit-description");
const implementationStatusInput = document.getElementById("edit-status");
const gridOverlay = document.getElementById("grid-overlay");
const exitOverlay = document.getElementById("exit-overlay");
const editorStage = document.getElementById("editor-stage");
const exitList = document.getElementById("exit-list");
const tileValidation = document.getElementById("tile-validation");
const toolButtons = document.getElementById("editor-tools");
const rotationPreview = document.getElementById("rotation-preview");
const saveButton = document.getElementById("save-tiles");
const addExitButton = document.getElementById("add-exit");
const exportTilesButton = document.getElementById("export-tiles");
const importTilesButton = document.getElementById("import-tiles");
const importTilesFile = document.getElementById("import-tiles-file");
const helpDialog = document.getElementById("editor-help-dialog");
const helpTitle = document.getElementById("editor-help-title");
const helpBody = document.getElementById("editor-help-body");

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

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function readJsonFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      try {
        resolve(JSON.parse(String(reader.result || "")));
      } catch {
        reject(new Error("Import file is not valid JSON."));
      }
    });
    reader.addEventListener("error", () => reject(new Error("Could not read import file.")));
    reader.readAsText(file);
  });
}

function setStatus(message) {
  statusEl.textContent = message;
}

function strongLine(text) {
  const element = document.createElement("strong");
  element.textContent = text;
  return element;
}

function showHelp(topicName) {
  const topic = HELP_TOPICS[topicName];
  if (!topic) return;
  helpTitle.textContent = topic.title;
  helpBody.replaceChildren();
  for (const paragraph of topic.paragraphs) {
    const item = document.createElement("p");
    item.textContent = paragraph;
    helpBody.appendChild(item);
  }
  if (typeof helpDialog.showModal === "function") {
    helpDialog.showModal();
  } else {
    window.alert(`${topic.title}\n\n${topic.paragraphs.join("\n\n")}`);
  }
}

function selectedTile() {
  return editor.tiles.find((tile) => tile.key === editor.selectedKey);
}

function tileImageUrl(tile) {
  return tile?.image ? `/assets/tiles/${encodeURI(tile.image).replace(/#/g, "%23")}` : "";
}

function catalogQuery() {
  return `catalog=${encodeURIComponent(editor.catalog)}`;
}

async function loadRoomCodeReference() {
  if (editor.catalog === "ee") {
    editor.roomCodeReference = [];
    return;
  }
  try {
    const payload = await api(`/api/rules/tiles/room-codes?${catalogQuery()}`);
    editor.roomCodeReference = payload.codes || [];
  } catch {
    editor.roomCodeReference = [];
  }
}

async function loadTiles() {
  try {
    editor.catalog = tileCatalogSelect?.value || editor.catalog || "ee";
    await loadRoomCodeReference();
    editor.tiles = await api(`/api/rules/tiles?${catalogQuery()}&t=${Date.now()}`);
    editor.tiles.forEach(normalizeTile);
    editor.selectedKey = editor.tiles[0]?.key || null;
    setStatus(`${editor.tiles.length} elements (${editor.catalog})`);
    renderTileList();
    renderSelectedTile();
    renderTools();
  } catch (error) {
    setStatus(error.message);
  }
}

function exportTileMetadata() {
  persistForm();
  const stamp = new Date().toISOString().slice(0, 10);
  downloadJson(`map-elements-${editor.catalog}-${stamp}.json`, {
    version: 1,
    catalog: editor.catalog,
    exported_at: new Date().toISOString(),
    tiles: editor.tiles,
  });
  setStatus("Metadata exported");
}

async function importTileMetadata(file) {
  if (!file) return;
  try {
    const payload = await readJsonFile(file);
    const tiles = Array.isArray(payload) ? payload : payload.tiles;
    if (!Array.isArray(tiles)) throw new Error("Import file must be a tile array or contain a tiles array.");
    editor.tiles = tiles;
    editor.tiles.forEach(normalizeTile);
    editor.selectedKey = editor.tiles[0]?.key || null;
    editor.previewRotation = 0;
    setStatus(`Imported ${editor.tiles.length} elements. Click Save Metadata to write them to the server.`);
    renderTileList();
    renderSelectedTile();
    renderTools();
  } catch (error) {
    setStatus(error.message);
  } finally {
    importTilesFile.value = "";
  }
}

function renderTileList() {
  tileFilter.value = editor.listFilter;
  renderValidationSummary();
  tileList.replaceChildren();
  const visibleTiles = editor.tiles.filter((tile) => tileMatchesFilter(tile, editor.listFilter));
  if (!visibleTiles.length) {
    const empty = document.createElement("div");
    empty.className = "empty-state";
    empty.textContent = "No map elements match this filter.";
    tileList.appendChild(empty);
    return;
  }
  for (const tile of visibleTiles) {
    const validation = validateTile(tile);
    const button = document.createElement("button");
    button.type = "button";
    button.className = `tile-list-item ${validationClass(validation)}`;
    if (tile.key === editor.selectedKey) button.classList.add("selected");
    const label = document.createElement("span");
    label.textContent = `${tile.key} ${tile.name}`;
    const badge = document.createElement("span");
    badge.className = "tile-validation-badge";
    badge.textContent = validationBadgeText(validation);
    button.append(label, badge);
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
  tilePreview.src = tileImageUrl(tile);
  tilePreview.alt = tile.name;
  tileSourcePreview.src = tileImageUrl(tile);
  tileSourcePreview.alt = `${tile.name} original scan`;
  nameInput.value = tile.name || "";
  typeInput.value = tile.tile_type || "unknown";
  terrainInput.value = tile.terrain || "indoor";
  widthInput.value = tile.footprint_width || 1;
  heightInput.value = tile.footprint_height || 1;
  cellSizeInput.value = tile.editor_cell_size || 80;
  imageScaleInput.value = Math.round((tile.image_scale || 1) * 100);
  imageOffsetXInput.value = tile.image_offset_x || 0;
  imageOffsetYInput.value = tile.image_offset_y || 0;
  descriptionInput.value = tile.description || "";
  renderStatusOptions(tile.implementation_status || "placeholder-needs-rulebook-validation");
  renderRoomCodeOptions(tile);
  renderGrid(tile);
  renderExitList(tile);
  renderTileValidation(tile);
  renderImageLock();
  renderTools();
  renderRotationPreview();
}

function renderValidationSummary() {
  const results = editor.tiles.map(validateTile);
  const ready = results.filter((result) => result.ready).length;
  const errors = results.filter((result) => result.errors.length).length;
  const needsWork = results.filter((result) => !result.ready).length;
  validationSummary.replaceChildren();
  validationSummary.append(
    validationCount("Ready", ready, "pass"),
    validationCount("Needs work", needsWork, needsWork ? "warn" : "pass"),
    validationCount("Errors", errors, errors ? "fail" : "pass")
  );
}

function validationCount(label, count, status) {
  const item = document.createElement("span");
  item.className = `validation-count ${status}`;
  item.textContent = `${label}: ${count}`;
  return item;
}

function renderTileValidation(tile) {
  const validation = validateTile(tile);
  tileValidation.replaceChildren();
  const heading = document.createElement("div");
  heading.className = "validation-panel-heading";
  heading.appendChild(strongLine(validation.ready ? "Metadata ready" : "Metadata needs work"));
  const status = document.createElement("span");
  status.className = `validation-pill ${validationClass(validation)}`;
  status.textContent = validationBadgeText(validation);
  heading.appendChild(status);
  tileValidation.appendChild(heading);
  const issues = validation.items.filter((item) => item.status !== "pass");
  if (issues.length) {
    const issuePanel = document.createElement("div");
    issuePanel.className = "validation-issue-panel";
    issuePanel.appendChild(strongLine("Warnings and errors"));
    const issueList = document.createElement("ul");
    for (const issue of issues) {
      const item = document.createElement("li");
      item.className = `validation-issue ${issue.status}`;
      item.textContent = issue.text;
      issueList.appendChild(item);
    }
    issuePanel.appendChild(issueList);
    tileValidation.appendChild(issuePanel);
  }
  const list = document.createElement("div");
  list.className = "validation-checklist";
  for (const item of validation.items) {
    const row = document.createElement("div");
    row.className = `validation-check ${item.status}`;
    row.appendChild(document.createElement("span"));
    row.appendChild(document.createTextNode(item.text));
    list.appendChild(row);
  }
  tileValidation.appendChild(list);
}

function refreshValidationViews(tile = selectedTile()) {
  if (tile) renderTileValidation(tile);
  renderValidationSummary();
  renderTileList();
}

function validateTile(tile) {
  const items = [];
  const add = (status, text) => items.push({ status, text });
  const startTile = isStartingTile(tile);
  const exits = tile.exits || [];
  const dungeonExits = exits.filter((exit) => exit.dungeon_exit);
  const normalExits = exits.filter((exit) => !exit.dungeon_exit);
  const walkableCount = tile.walkable.reduce(
    (total, row) => total + [...row].filter((value) => value === "1").length,
    0
  );
  const waterCount = tile.walkable.reduce((total, row) => total + [...row].filter((value) => value === "2").length, 0);

  add(tile.name?.trim() ? "pass" : "fail", tile.name?.trim() ? "Name set" : "Name is missing");
  add(tile.tile_type !== "unknown" ? "pass" : "fail", tile.tile_type !== "unknown" ? `Type is ${tile.tile_type}` : "Room type is unknown");
  if (editor.catalog !== "ee") {
    const codes = tile.room_codes || [];
    add(
      "pass",
      codes.length
        ? `Room codes: ${codes.join(", ")}`
        : "No special letter codes (normal room or river stretch)"
    );
  }
  add(tile.image ? "pass" : "warn", tile.image ? "Image assigned" : "No map element image assigned");
  add(walkableCount > 0 || waterCount > 0 ? "pass" : "fail", walkableCount > 0 || waterCount > 0 ? `${walkableCount} walkable + ${waterCount} water square${walkableCount + waterCount === 1 ? "" : "s"}` : "No walkable or water squares marked");
  add(
    tile.walkable.length === tile.footprint_height && tile.walkable.every((row) => row.length === tile.footprint_width)
      ? "pass"
      : "fail",
    "Walkable grid matches width and height"
  );
  add(
    tile.cell_shapes.length === tile.footprint_height && tile.cell_shapes.every((row) => row.length === tile.footprint_width)
      ? "pass"
      : "fail",
    "Shape grid matches width and height"
  );

  if (startTile) {
    add(dungeonExits.length === 1 ? "pass" : "fail", dungeonExits.length === 1 ? "One dungeon exit marked" : "Starting element needs exactly one dungeon exit");
    add(normalExits.length > 0 ? "pass" : "fail", normalExits.length > 0 ? `${normalExits.length} dungeon passage/door exit${normalExits.length === 1 ? "" : "s"}` : "Starting element needs at least one normal exit");
  } else {
    add(dungeonExits.length === 0 ? "pass" : "fail", dungeonExits.length === 0 ? "No illegal dungeon exit" : "Dungeon exits are only valid on 01-06");
    add(exits.length > 0 ? "pass" : "fail", exits.length > 0 ? `${exits.length} exit${exits.length === 1 ? "" : "s"} marked` : "No exits marked");
  }

  const blockedExitLabels = exits.filter((exit) => exitHasInvalidAnchor(tile, exit)).map(exitLabelForValidation);
  add(
    blockedExitLabels.length ? "fail" : "pass",
    blockedExitLabels.length
      ? `Exit lacks traversable interior: ${blockedExitLabels.join(", ")}`
      : "All exits have traversable interior squares"
  );

  const duplicateLabels = duplicateExitLabels(tile);
  add(
    duplicateLabels.length ? "warn" : "pass",
    duplicateLabels.length ? `Duplicate exit anchor: ${duplicateLabels.join(", ")}` : "No duplicate exit anchors"
  );

  add(
    tile.implementation_status === "validated" ? "pass" : "warn",
    tile.implementation_status === "validated" ? "Marked validated" : "Not marked validated against rulebook"
  );

  const errors = items.filter((item) => item.status === "fail");
  const warnings = items.filter((item) => item.status === "warn");
  return {
    items,
    errors,
    warnings,
    ready: errors.length === 0 && warnings.length === 0,
  };
}

function exitHasInvalidAnchor(tile, exit) {
  const [dx, dy] = EXIT_DIRECTION_DELTAS[exit.direction] || [0, 0];
  return exitCells(tile, exit).some(({ x, y }) => {
    if (surfaceCode(tile, x, y) !== "0") return false;
    const insideX = x - dx;
    const insideY = y - dy;
    if (insideX < 0 || insideY < 0 || insideX >= tile.footprint_width || insideY >= tile.footprint_height) {
      return true;
    }
    return surfaceCode(tile, insideX, insideY) === "0";
  });
}

function duplicateExitLabels(tile) {
  const seen = new Set();
  const duplicates = new Set();
  for (const exit of tile.exits || []) {
    const key = `${exit.direction}:${exit.x}:${exit.y}:${exit.span || 1}`;
    if (seen.has(key)) duplicates.add(exitLabelForValidation(exit));
    seen.add(key);
  }
  return [...duplicates];
}

function exitLabelForValidation(exit) {
  return `${exit.direction} ${exit.x + 1},${exit.y + 1}`;
}

function validationClass(validation) {
  if (validation.errors.length) return "has-errors";
  if (validation.warnings.length) return "has-warnings";
  return "ready";
}

function validationBadgeText(validation) {
  if (validation.errors.length) return `${validation.errors.length} error${validation.errors.length === 1 ? "" : "s"}`;
  if (validation.warnings.length) return `${validation.warnings.length} warning${validation.warnings.length === 1 ? "" : "s"}`;
  return "ready";
}

function tileMatchesFilter(tile, filter) {
  const validation = validateTile(tile);
  if (filter === "ready") return validation.ready;
  if (filter === "errors") return validation.errors.length > 0;
  if (filter === "needs-work") return !validation.ready;
  return true;
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
  const riverCatalog = editor.catalog === "forsaken_depths_rivers";
  for (const button of toolButtons.querySelectorAll("button")) {
    const isWaterToggle = button.dataset.mode === "water_toggle";
    button.disabled =
      previewing ||
      (isWaterToggle && !riverCatalog) ||
      (button.dataset.mode === "dungeon_exit" && !startTile) ||
      (button.dataset.mode === "move_image" && editor.imageLocked);
    button.classList.toggle(
      "selected",
      !previewing && (isWaterToggle ? editor.paintSurface === "water" : button.dataset.mode === editor.mode)
    );
    if (isWaterToggle) {
      button.setAttribute("aria-pressed", String(editor.paintSurface === "water"));
      button.title =
        editor.paintSurface === "water"
          ? "Water shape mode is active. Choose any shape tool to paint blue water; click Water again for walkable floor."
          : "Toggle water shape mode for Forsaken Depths rivers, then use any shape tool.";
    }
  }
  toolButtons.classList.toggle("water-paint-active", riverCatalog && editor.paintSurface === "water");
  editorStage.classList.toggle("move-mode", !previewing && !editor.imageLocked && editor.mode === "move_image");
  editorStage.classList.toggle("rotation-preview", previewing);
}

function renderImageLock() {
  lockImageInput.checked = editor.imageLocked;
  if (editor.imageLocked && editor.mode === "move_image") editor.mode = "walkable_toggle";
  imageScaleInput.disabled = editor.imageLocked;
  imageOffsetXInput.disabled = editor.imageLocked;
  imageOffsetYInput.disabled = editor.imageLocked;
  document.querySelectorAll("[data-offset-action]").forEach((button) => {
    button.disabled = editor.imageLocked;
  });
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
      square.className = `grid-square ${surfaceClass(view.walkable[y]?.[x])} shape-${view.cell_shapes[y]?.[x] || "F"}`;
      square.dataset.x = x;
      square.dataset.y = y;
      square.title =
        editor.previewRotation === 0
          ? `${squareDescription(tile, x, y)} square ${x + 1},${y + 1}`
          : `Read-only ${editor.previewRotation}deg rotation preview`;
      square.setAttribute("aria-label", square.title);
      if (editor.previewRotation === 0) {
        square.addEventListener("mousedown", (event) => {
          if (event.button === 1) return;
          const step = event.button === 2 ? -1 : event.button === 0 ? 1 : 0;
          if (!step) return;
          if (event.button === 2 && BIDIRECTIONAL_GRID_MODES.has(editor.mode)) {
            event.preventDefault();
          }
          handleGridInteraction(tile, x, y, event, step);
        });
        square.addEventListener("contextmenu", (event) => {
          if (BIDIRECTIONAL_GRID_MODES.has(editor.mode)) event.preventDefault();
        });
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
    exitList.appendChild(buildExitRow(tile, exit, index, displayExits.get(exit.id) || exit, view));
  });
}

function refreshExitEditorViews(tile) {
  renderGrid(tile);
  renderExitList(tile);
  refreshValidationViews(tile);
}

function commitExitGeometry(tile, exit, { span, x, y } = {}) {
  if (x !== undefined) {
    exit.x = clampNumber(x, 0, tile.footprint_width - 1);
  }
  if (y !== undefined) {
    exit.y = clampNumber(y, 0, tile.footprint_height - 1);
  }
  if (span !== undefined) {
    applyExitSpan(tile, exit, span);
  } else {
    syncExitAnchor(tile, exit);
    applyExitSpan(tile, exit, exit.span || 1);
  }
  refreshExitEditorViews(tile);
}

function buildExitRow(tile, exit, index, displayExit, view) {
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
  meta.className = "muted exit-row-meta";
  meta.textContent = `canonical ${exit.direction}, square ${exit.x + 1},${exit.y + 1}, span ${exit.span || 1}`;
  label.appendChild(meta);

  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "secondary exit-remove-btn";
  remove.textContent = "Remove";
  remove.title = "Delete this door or passage from the map element.";
  remove.addEventListener("click", () => {
    removeExit(tile, exit.id);
    refreshExitEditorViews(tile);
  });

  const head = document.createElement("div");
  head.className = "exit-row-head";
  head.append(number, label, remove);

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
    refreshExitEditorViews(tile);
  });

  const span = document.createElement("label");
  span.className = "span-field";
  span.appendChild(document.createTextNode("Span"));
  const spanInput = document.createElement("input");
  spanInput.type = "number";
  spanInput.min = "1";
  spanInput.step = "1";
  spanInput.inputMode = "numeric";
  const refreshSpanField = () => {
    const anchorMax = maxExitSpan(tile, exit.direction, exit.x, exit.y);
    const requestMax = maxRequestableExitSpan(tile, exit.direction);
    spanInput.max = String(requestMax);
    spanInput.value = String(exit.span || 1);
    spanInput.title =
      `Span grows along the edge from anchor square ${exit.x + 1},${exit.y + 1}. ` +
      `Up to ${anchorMax} without sliding the anchor; up to ${requestMax} with anchor slide.`;
  };
  refreshSpanField();
  const commitSpan = () => {
    const parsed = Number.parseInt(spanInput.value, 10);
    if (Number.isNaN(parsed)) {
      refreshSpanField();
      return;
    }
    commitExitGeometry(tile, exit, { span: parsed });
  };
  spanInput.addEventListener("change", commitSpan);
  spanInput.addEventListener("blur", commitSpan);
  spanInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      commitSpan();
    }
  });
  span.appendChild(spanInput);

  const xField = document.createElement("label");
  xField.className = "span-field coord-field";
  xField.appendChild(document.createTextNode("X"));
  const xInput = document.createElement("input");
  xInput.type = "number";
  xInput.min = "1";
  xInput.max = String(tile.footprint_width);
  xInput.value = String(exit.x + 1);
  xInput.title = "Anchor column (1-based grid coordinate).";
  const commitX = () => {
    commitExitGeometry(tile, exit, { x: Number.parseInt(xInput.value, 10) - 1 });
  };
  xInput.addEventListener("change", commitX);
  xInput.addEventListener("blur", commitX);
  xInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      commitX();
    }
  });
  xField.appendChild(xInput);

  const yField = document.createElement("label");
  yField.className = "span-field coord-field";
  yField.appendChild(document.createTextNode("Y"));
  const yInput = document.createElement("input");
  yInput.type = "number";
  yInput.min = "1";
  yInput.max = String(tile.footprint_height);
  yInput.value = String(exit.y + 1);
  yInput.title = "Anchor row (1-based grid coordinate).";
  const commitY = () => {
    commitExitGeometry(tile, exit, { y: Number.parseInt(yInput.value, 10) - 1 });
  };
  yInput.addEventListener("change", commitY);
  yInput.addEventListener("blur", commitY);
  yInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      commitY();
    }
  });
  yField.appendChild(yInput);

  const coords = document.createElement("div");
  coords.className = "exit-coord-fields";
  coords.append(span, xField, yField);

  const dungeonExit = document.createElement("label");
  dungeonExit.className = "inline-check exit-dungeon-toggle";
  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = Boolean(exit.dungeon_exit);
  checkbox.disabled = !isStartingTile(tile);
  checkbox.addEventListener("change", () => {
    exit.dungeon_exit = checkbox.checked;
    refreshExitEditorViews(tile);
  });
  dungeonExit.append(checkbox, document.createTextNode("Dungeon exit"));

  const controls = document.createElement("div");
  controls.className = "exit-row-controls";
  controls.append(directionControl, kind, coords, dungeonExit);

  row.append(head, controls);
  return row;
}

function nodeStrong(text) {
  const strong = document.createElement("strong");
  strong.textContent = text;
  return strong;
}

function directionButtons(tile, exit) {
  const wrap = document.createElement("div");
  wrap.className = "direction-buttons";
  for (const direction of EXIT_DIRECTIONS) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "direction-button";
    if (exit.direction === direction) button.classList.add("selected");
    button.textContent = EXIT_DIRECTION_LABELS[direction];
    button.title = `Place on ${direction} side in canonical orientation`;
    button.addEventListener("click", () => {
      setExitDirection(tile, exit, direction);
      renderGrid(tile);
      renderExitList(tile);
      refreshValidationViews(tile);
    });
    wrap.appendChild(button);
  }
  return wrap;
}

function setExitDirection(tile, exit, direction) {
  exit.direction = direction;
  exit.x = clampNumber(exit.x, 0, tile.footprint_width - 1);
  exit.y = clampNumber(exit.y, 0, tile.footprint_height - 1);
  syncExitAnchor(tile, exit);
  applyExitSpan(tile, exit, exit.span || 1);
}

function handleGridInteraction(tile, x, y, event, step = 1) {
  if (editor.suppressNextGridClick || event.ctrlKey) {
    editor.suppressNextGridClick = false;
    return;
  }

  if (editor.mode === "move_image") {
    return;
  }

  if (editor.mode === "walkable_toggle") {
    cycleWalkableSurface(tile, x, y, step, activePaintSurfaceCode());
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (editor.mode === "half_curve_cycle") {
    cycleShapeList(tile, x, y, HALF_CURVE_CYCLE, step, activePaintSurfaceCode());
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (CELL_SHAPE_MODES[editor.mode]) {
    cycleShapeList(tile, x, y, CELL_SHAPE_MODES[editor.mode], step, activePaintSurfaceCode());
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (editor.mode === "long_slope_cycle") {
    cycleLongSlope(tile, x, y, step, activePaintSurfaceCode());
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (step < 0) return;

  const direction = nearestDirection(event);
  if (editor.mode === "dungeon_exit" && !isStartingTile(tile)) return;
  if (editor.mode === "delete_exit") {
    removeExitAt(tile, x, y, direction);
    renderGrid(tile);
    renderExitList(tile);
    refreshValidationViews(tile);
    return;
  }
  upsertExit(tile, x, y, direction, editor.mode);
  renderGrid(tile);
  renderExitList(tile);
  refreshValidationViews(tile);
}

function cycleShapeList(tile, x, y, shapes, step = 1, surface = "1") {
  const current = cellShape(tile, x, y);
  const onSurface = surfaceCode(tile, x, y) === surface;
  let index = onSurface && shapes.includes(current) ? shapes.indexOf(current) : -1;

  if (step > 0) {
    if (index === -1) {
      setSurface(tile, x, y, surface);
      setCellShape(tile, x, y, shapes[0]);
      return;
    }
    if (index === shapes.length - 1) {
      setSurface(tile, x, y, surface);
      setCellShape(tile, x, y, "F");
      return;
    }
    setSurface(tile, x, y, surface);
    setCellShape(tile, x, y, shapes[index + 1]);
    return;
  }

  if (index === -1) {
    setSurface(tile, x, y, surface);
    setCellShape(tile, x, y, shapes[shapes.length - 1]);
    return;
  }
  if (index === 0) {
    setSurface(tile, x, y, surface);
    setCellShape(tile, x, y, "F");
    return;
  }
  setSurface(tile, x, y, surface);
  setCellShape(tile, x, y, shapes[index - 1]);
}

function longSlopePatternIndex(tile, x, y) {
  for (let index = 0; index < LONG_SLOPE_PATTERNS.length; index += 1) {
    const pattern = LONG_SLOPE_PATTERNS[index];
    for (let anchor = 0; anchor < pattern.cells.length; anchor += 1) {
      const originX = x - pattern.cells[anchor][0];
      const originY = y - pattern.cells[anchor][1];
      if (longSlopePatternMatches(tile, pattern, originX, originY)) return index;
    }
  }
  return -1;
}

function longSlopePatternMatches(tile, pattern, originX, originY) {
  for (let index = 0; index < pattern.codes.length; index += 1) {
    const cellX = originX + pattern.cells[index][0];
    const cellY = originY + pattern.cells[index][1];
    if (cellX < 0 || cellY < 0 || cellX >= tile.footprint_width || cellY >= tile.footprint_height) return false;
    if (cellShape(tile, cellX, cellY) !== pattern.codes[index]) return false;
  }
  return true;
}

function longSlopePatternFits(tile, pattern, originX, originY) {
  for (const [offsetX, offsetY] of pattern.cells) {
    const cellX = originX + offsetX;
    const cellY = originY + offsetY;
    if (cellX < 0 || cellY < 0 || cellX >= tile.footprint_width || cellY >= tile.footprint_height) return false;
  }
  return true;
}

function cycleLongSlope(tile, x, y, step = 1, surface = "1") {
  const currentIndex = longSlopePatternIndex(tile, x, y);
  clearLongSlopeTouching(tile, x, y);
  const total = LONG_SLOPE_PATTERNS.length;
  for (let attempt = 0; attempt <= total; attempt += 1) {
    const nextIndex =
      step > 0
        ? (currentIndex + attempt + 1) % (total + 1)
        : (currentIndex - attempt - 1 + (total + 1)) % (total + 1);
    if (nextIndex >= total) return;
    const pattern = LONG_SLOPE_PATTERNS[nextIndex];
    if (longSlopePatternFits(tile, pattern, x, y)) {
      applyLongSlopePattern(tile, x, y, pattern, surface);
      return;
    }
  }
}

function clearLongSlopeTouching(tile, x, y) {
  for (const [cellX, cellY] of [
    [x, y],
    [x, y - 1],
    [x, y + 1],
    [x - 1, y],
    [x + 1, y],
  ]) {
    if (cellX < 0 || cellY < 0 || cellX >= tile.footprint_width || cellY >= tile.footprint_height) continue;
    if (LONG_SLOPE_CODES.has(cellShape(tile, cellX, cellY))) setCellShape(tile, cellX, cellY, "F");
  }
}

function applyLongSlopePattern(tile, originX, originY, pattern, surface = "1") {
  for (let index = 0; index < pattern.codes.length; index += 1) {
    const cellX = originX + pattern.cells[index][0];
    const cellY = originY + pattern.cells[index][1];
    setSurface(tile, cellX, cellY, surface);
    setCellShape(tile, cellX, cellY, pattern.codes[index]);
  }
}

function nearestDirection(event) {
  const rect = event.currentTarget.getBoundingClientRect();
  const dx = event.clientX - rect.left - rect.width / 2;
  const dy = event.clientY - rect.top - rect.height / 2;
  const octant = Math.round(Math.atan2(dy, dx) / (Math.PI / 4));
  return ["east", "southeast", "south", "southwest", "west", "northwest", "north", "northeast"][
    (octant + 8) % 8
  ];
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

function removeExit(tile, exitId) {
  const before = tile.exits.length;
  tile.exits = tile.exits.filter((item) => item.id !== exitId);
  if (tile.exits.length < before) {
    setStatus("Exit removed. Click Save Metadata to write the change.");
  }
}

function removeExitAt(tile, x, y, direction) {
  const match = tile.exits.find((exit) => exit.direction === direction && exitCells(tile, exit).some((cell) => cell.x === x && cell.y === y));
  if (match) {
    removeExit(tile, match.id);
    return;
  }
  setStatus("No exit marker on that edge square.");
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
  marker.title =
    editor.previewRotation === 0
      ? `${exitLabel(view, displayExit)}. Drag to move; choose Delete Exit and click this marker to remove it.`
      : `${exitLabel(view, displayExit)} preview`;
  const badge = document.createElement("span");
  badge.className = "exit-marker-badge";
  badge.textContent = String(index + 1);
  marker.appendChild(badge);
  positionExitMarker(marker, view, displayExit);
  if (editor.previewRotation === 0) {
    marker.addEventListener("click", (event) => {
      if (editor.mode !== "delete_exit") return;
      event.preventDefault();
      event.stopPropagation();
      removeExit(tile, exit.id);
      renderGrid(tile);
      renderExitList(tile);
      refreshValidationViews(tile);
    });
    marker.addEventListener("pointerdown", (event) => {
      if (editor.mode === "delete_exit") return;
      startExitDrag(event, tile, exit);
    });
  } else {
    marker.classList.add("preview-only");
  }
  return marker;
}

function positionExitMarker(marker, tile, exit) {
  const cellW = 100 / tile.footprint_width;
  const cellH = 100 / tile.footprint_height;
  const span = clampExitSpan(tile, exit.direction, exit.span || 1, exit.x, exit.y);
  const cells = exitCells(tile, exit);
  const centers = cells.map(({ x, y }) => ({ x: (x + 0.5) * cellW, y: (y + 0.5) * cellH }));
  const first = centers[0];
  const last = centers[centers.length - 1];
  const centerX = (first.x + last.x) / 2;
  const centerY = (first.y + last.y) / 2;
  const blockedAnchor = surfaceCode(tile, exit.x, exit.y) === "0";
  marker.className = `exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""} ${exit.direction}`;
  marker.style.transform = "";
  if (exit.direction === "north" || exit.direction === "south") {
    marker.style.left = `${centerX}%`;
    marker.style.top = `${
      exit.y * cellH +
      (exit.direction === "north"
        ? blockedAnchor
          ? cellH
          : 0
        : blockedAnchor
          ? 0
          : cellH)
    }%`;
    marker.style.width = `${cellW * Math.max(0.72, span - 0.16)}%`;
    marker.style.height = "";
  } else if (exit.direction === "east" || exit.direction === "west") {
    marker.style.left = `${
      exit.x * cellW +
      (exit.direction === "west"
        ? blockedAnchor
          ? cellW
          : 0
        : blockedAnchor
          ? 0
          : cellW)
    }%`;
    marker.style.top = `${centerY}%`;
    marker.style.height = `${cellH * Math.max(0.72, span - 0.16)}%`;
    marker.style.width = "";
  } else {
    const [moveX, moveY] = {
      northeast: [0.5, -0.5],
      southeast: [0.5, 0.5],
      southwest: [-0.5, 0.5],
      northwest: [-0.5, -0.5],
    }[exit.direction];
    const anchorFactor = blockedAnchor ? -1 : 1;
    marker.style.left = `${centerX + moveX * cellW * anchorFactor}%`;
    marker.style.top = `${centerY + moveY * cellH * anchorFactor}%`;
    marker.style.width = `${Math.hypot(cellW, cellH) * Math.max(0.72, span - 0.16)}%`;
    marker.style.height = "14px";
    marker.style.transform = `translate(-50%, -50%) rotate(${exit.direction === "northeast" || exit.direction === "southwest" ? 45 : -45}deg)`;
  }
}

function startExitDrag(event, tile, exit) {
  if (editor.mode === "delete_exit") return;
  event.preventDefault();
  event.stopPropagation();
  editor.suppressNextGridClick = true;
  const marker = event.currentTarget;
  editorStage.setPointerCapture(event.pointerId);

  const move = (moveEvent) => {
    moveExitAnchorFromPointer(tile, exit, moveEvent.clientX, moveEvent.clientY);
    positionExitMarker(marker, tile, exit);
  };

  const stop = () => {
    editorStage.removeEventListener("pointermove", move);
    editorStage.removeEventListener("pointerup", stop);
    editorStage.removeEventListener("pointercancel", stop);
    applyExitSpan(tile, exit, exit.span || 1);
    renderGrid(tile);
    renderExitList(tile);
    refreshValidationViews(tile);
  };

  editorStage.addEventListener("pointermove", move);
  editorStage.addEventListener("pointerup", stop);
  editorStage.addEventListener("pointercancel", stop);
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
  tile.terrain = terrainInput.value || "indoor";
  tile.footprint_width = clampNumber(widthInput.value, 1, 20);
  tile.footprint_height = clampNumber(heightInput.value, 1, 20);
  tile.editor_cell_size = clampNumber(cellSizeInput.value, 24, 180);
  tile.image_scale = clampNumber(imageScaleInput.value, 10, 2000) / 100;
  tile.image_offset_x = clampNumber(imageOffsetXInput.value, -1000, 1000);
  tile.image_offset_y = clampNumber(imageOffsetYInput.value, -1000, 1000);
  tile.description = descriptionInput.value.trim();
  tile.implementation_status = implementationStatusInput.value || "edited-needs-rulebook-validation";
  tile.room_codes = readRoomCodeSelection();
  normalizeTile(tile);
}

function normalizeTile(tile) {
  tile.catalog = tile.catalog || editor.catalog || "ee";
  tile.footprint_width = clampNumber(tile.footprint_width || 1, 1, 20);
  tile.footprint_height = clampNumber(tile.footprint_height || 1, 1, 20);
  tile.editor_cell_size = clampNumber(tile.editor_cell_size || 80, 24, 180);
  tile.image_scale = clampFloat(tile.image_scale || 1, 0.1, 20);
  tile.image_offset_x = clampNumber(tile.image_offset_x || 0, -1000, 1000);
  tile.image_offset_y = clampNumber(tile.image_offset_y || 0, -1000, 1000);
  tile.terrain = tile.terrain || (tile.catalog === "forsaken_depths_rivers" ? "river" : "indoor");
  tile.room_codes = Array.isArray(tile.room_codes) ? [...new Set(tile.room_codes)] : [];
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
      const value = sourceRow[x];
      row += value === "0" || value === "2" ? value : "1";
    }
    normalized.push(row);
  }
  return normalized;
}

function normalizeCellShapes(rows, width, height) {
  const normalized = [];
  const source = Array.isArray(rows) ? rows : [];
  const allowed = new Set(Object.keys(CELL_SHAPE_DESCRIPTIONS));
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
  const normalized = {
    id: exit.id || newExitId(tile),
    label: "",
    direction,
    kind: exit.kind === "door" ? "door" : "passage",
    x: clampNumber(exit.x ?? coordinateFromOffset(exit, tile).x, 0, tile.footprint_width - 1),
    y: clampNumber(exit.y ?? coordinateFromOffset(exit, tile).y, 0, tile.footprint_height - 1),
    span: exit.span || 1,
    offset: 0,
    position: 0.5,
    dungeon_exit: Boolean(exit.dungeon_exit),
  };
  applyExitSpan(tile, normalized, normalized.span);
  return normalized;
}

function syncExitAnchor(tile, exit) {
  exit.x = clampNumber(exit.x, 0, tile.footprint_width - 1);
  exit.y = clampNumber(exit.y, 0, tile.footprint_height - 1);
  exit.offset = exitOffset(exit.direction, exit.x, exit.y);
  exit.position = exitPosition(exit.direction, exit.offset, tile.footprint_width, tile.footprint_height);
}

function moveExitAnchorFromPointer(tile, exit, clientX, clientY) {
  const placement = placementFromPoint(tile, clientX, clientY, exit.direction);
  exit.x = placement.x;
  exit.y = placement.y;
  syncExitAnchor(tile, exit);
}

function coordinateFromOffset(exit, tile) {
  const offset = clampNumber(exit.offset || 0, 0, 99);
  if (exit.direction === "south") return { x: Math.min(offset, tile.footprint_width - 1), y: tile.footprint_height - 1 };
  if (exit.direction === "east") return { x: tile.footprint_width - 1, y: Math.min(offset, tile.footprint_height - 1) };
  if (exit.direction === "west") return { x: 0, y: Math.min(offset, tile.footprint_height - 1) };
  if (exit.direction === "northeast") return { x: tile.footprint_width - 1, y: 0 };
  if (exit.direction === "southeast") return { x: tile.footprint_width - 1, y: tile.footprint_height - 1 };
  if (exit.direction === "southwest") return { x: 0, y: tile.footprint_height - 1 };
  if (exit.direction === "northwest") return { x: 0, y: 0 };
  return { x: Math.min(offset, tile.footprint_width - 1), y: 0 };
}

function surfaceCode(tile, x, y) {
  const value = tile.walkable[y]?.[x];
  return value === "0" || value === "2" ? value : "1";
}

function surfaceClass(code) {
  if (code === "2") return "water";
  if (code === "1") return "walkable";
  return "blocked";
}

function isWalkable(tile, x, y) {
  return surfaceCode(tile, x, y) === "1";
}

function isWater(tile, x, y) {
  return surfaceCode(tile, x, y) === "2";
}

function setSurface(tile, x, y, code) {
  const row = tile.walkable[y].split("");
  row[x] = code;
  tile.walkable[y] = row.join("");
}

function setWalkable(tile, x, y, value) {
  setSurface(tile, x, y, value ? "1" : "0");
}

function activePaintSurfaceCode() {
  return editor.catalog === "forsaken_depths_rivers" && editor.paintSurface === "water" ? "2" : "1";
}

function walkableSurfaceCycleIndex(tile, x, y, surface = "1") {
  const code = surfaceCode(tile, x, y);
  const shape = cellShape(tile, x, y);
  const index = WALKABLE_SURFACE_CYCLE.findIndex(
    (state) => (state.walkable === "1" ? surface : state.walkable) === code && state.shape === shape
  );
  if (index >= 0) return index;
  if (code === "0") return 0;
  return WALKABLE_SURFACE_CYCLE.length - 1;
}

function cycleWalkableSurface(tile, x, y, step = 1, surface = "1") {
  const currentSurface = surfaceCode(tile, x, y);
  if (currentSurface !== "0" && currentSurface !== surface) {
    setSurface(tile, x, y, surface);
    return;
  }
  let currentIndex = walkableSurfaceCycleIndex(tile, x, y, surface);
  if (currentIndex < 0) {
    const fallback = step > 0 ? WALKABLE_SURFACE_CYCLE[0] : WALKABLE_SURFACE_CYCLE[WALKABLE_SURFACE_CYCLE.length - 1];
    setSurface(tile, x, y, fallback.walkable === "1" ? surface : fallback.walkable);
    setCellShape(tile, x, y, fallback.shape);
    return;
  }
  const nextIndex =
    step > 0
      ? (currentIndex + 1) % WALKABLE_SURFACE_CYCLE.length
      : (currentIndex - 1 + WALKABLE_SURFACE_CYCLE.length) % WALKABLE_SURFACE_CYCLE.length;
  const next = WALKABLE_SURFACE_CYCLE[nextIndex];
  setSurface(tile, x, y, next.walkable === "1" ? surface : next.walkable);
  setCellShape(tile, x, y, next.shape);
}

function setCellShape(tile, x, y, value) {
  const row = tile.cell_shapes[y].split("");
  row[x] = value;
  tile.cell_shapes[y] = row.join("");
}

function cellShape(tile, x, y) {
  return tile.cell_shapes[y]?.[x] || "F";
}

function squareDescription(tile, x, y) {
  if (isWater(tile, x, y)) {
    const shape = cellShape(tile, x, y);
    return shape === "F" ? "Water" : `Water with ${CELL_SHAPE_DESCRIPTIONS[shape] || "partial blocked shape"}`;
  }
  if (!isWalkable(tile, x, y)) return "Blocked";
  return CELL_SHAPE_DESCRIPTIONS[cellShape(tile, x, y)] || "Walkable";
}

function renderRoomCodeOptions(tile) {
  if (!roomCodeFieldset || !roomCodeOptions) return;
  const show = editor.catalog !== "ee";
  roomCodeFieldset.classList.toggle("hidden", !show);
  if (!show) {
    roomCodeOptions.replaceChildren();
    return;
  }
  roomCodeOptions.replaceChildren();
  const hint = document.createElement("p");
  hint.className = "muted room-code-hint";
  hint.textContent =
    "Optional. Leave all unchecked for a normal room or ordinary river stretch — only mark codes printed on the scan.";
  roomCodeOptions.appendChild(hint);
  const selected = new Set(tile.room_codes || []);
  for (const entry of editor.roomCodeReference) {
    const label = document.createElement("label");
    label.className = "room-code-option";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = entry.code;
    input.checked = selected.has(entry.code);
    input.addEventListener("change", () => {
      persistForm();
      refreshValidationViews(tile);
    });
    const text = document.createElement("span");
    text.textContent = `${entry.code} — ${entry.description}`;
    label.append(input, text);
    roomCodeOptions.appendChild(label);
  }
}

function readRoomCodeSelection() {
  if (!roomCodeOptions) return [];
  return [...roomCodeOptions.querySelectorAll('input[type="checkbox"]:checked')].map((input) => input.value);
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
  if (!tile || editor.imageLocked) return;
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
  if (editor.imageLocked) return;
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
  if (editor.imageLocked) return;
  event.preventDefault();
  const step = event.deltaY < 0 ? 0.05 : -0.05;
  tile.image_scale = clampFloat((tile.image_scale || 1) + step, 0.1, 20);
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
  if (!["north", "south", "east", "west"].includes(direction)) return Math.min(x, y);
  return direction === "north" || direction === "south" ? x : y;
}

function exitPosition(direction, offset, width, height) {
  const side = !["north", "south", "east", "west"].includes(direction)
    ? Math.min(width, height)
    : direction === "north" || direction === "south"
      ? width
      : height;
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
  const geometry = exitGeometryFromCells(cells, direction);
  return {
    ...exit,
    direction,
    x: geometry.x,
    y: geometry.y,
    span: geometry.span,
    offset: exitOffset(direction, geometry.x, geometry.y),
    source: exit,
  };
}

function exitCells(tile, exit) {
  const span = clampExitSpan(tile, exit.direction, exit.span || 1, exit.x, exit.y);
  const [stepX, stepY] = EXIT_SPAN_STEPS[exit.direction] || [0, 0];
  return Array.from({ length: span }, (_, index) => ({
    x: exit.x + index * stepX,
    y: exit.y + index * stepY,
  }));
}

function exitGeometryFromCells(cells, direction) {
  const [stepX, stepY] = EXIT_SPAN_STEPS[direction] || [0, 0];
  const keys = new Set(cells.map(({ x, y }) => `${x},${y}`));
  for (const start of cells) {
    const generated = Array.from({ length: cells.length }, (_, index) => `${start.x + index * stepX},${start.y + index * stepY}`);
    if (generated.every((key) => keys.has(key))) return { x: start.x, y: start.y, span: cells.length };
  }
  return { x: cells[0]?.x || 0, y: cells[0]?.y || 0, span: 1 };
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
  const turns = (rotation / 90) % 4;
  return EXIT_DIRECTIONS[(EXIT_DIRECTIONS.indexOf(direction) + turns * 2) % EXIT_DIRECTIONS.length];
}

function rotateCellShape(value, rotation) {
  const turns = (rotation / 90) % 4;
  const maps = [
    {},
    {
      A: "C", C: "D", D: "B", B: "A", E: "H", H: "I", I: "G", G: "E", J: "L", L: "M", M: "K", K: "J", N: "T", O: "U", P: "R", Q: "S", R: "N", S: "O", T: "P", U: "Q",
      f: "u", j: "v", k: "w", l: "x", z: "4", 2: "5", 3: "6",
      m: "q", n: "r", o: "s", p: "t", Z: "9", 7: "0", 8: "y",
      q: "m", r: "n", s: "o", t: "p", 9: "Z", 0: "7", y: "8",
      u: "f", v: "j", w: "k", x: "l", 4: "z", 5: "2", 6: "3",
    },
    {
      A: "D", D: "A", B: "C", C: "B", E: "I", I: "E", G: "H", H: "G", J: "M", M: "J", K: "L", L: "K", N: "Q", O: "P", P: "O", Q: "N", R: "U", S: "T", T: "S", U: "R",
      f: "m", j: "p", k: "o", l: "n", z: "Z", 2: "7", 3: "8",
      m: "f", n: "l", o: "k", p: "j", Z: "z", 7: "2", 8: "3",
      q: "u", r: "x", s: "w", t: "v", 9: "6", 0: "5", y: "4",
      u: "q", v: "t", w: "s", x: "r", 4: "y", 5: "0", 6: "9",
    },
    {
      A: "B", B: "D", D: "C", C: "A", E: "G", G: "I", I: "H", H: "E", J: "K", K: "M", M: "L", L: "J", N: "R", O: "S", P: "T", Q: "U", R: "P", S: "Q", T: "N", U: "O",
      f: "q", j: "9", k: "0", l: "y", z: "r", 2: "s", 3: "t",
      m: "u", n: "4", o: "5", p: "6", Z: "v", 7: "w", 8: "x",
      q: "f", r: "j", s: "k", t: "l", 9: "z", 0: "2", y: "3",
      u: "m", v: "n", w: "o", x: "p", 4: "Z", 5: "7", 6: "8",
    },
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

function applyExitSpan(tile, exit, requestedSpan) {
  const direction = exit.direction;
  let x = clampNumber(exit.x, 0, tile.footprint_width - 1);
  let y = clampNumber(exit.y, 0, tile.footprint_height - 1);
  let span = clampNumber(requestedSpan, 1, 20);
  const [stepX, stepY] = EXIT_SPAN_STEPS[direction] || [0, 0];
  const room = maxExitSpan(tile, direction, x, y);
  if (span > room) {
    const shift = span - room;
    x = clampNumber(x - stepX * shift, 0, tile.footprint_width - 1);
    y = clampNumber(y - stepY * shift, 0, tile.footprint_height - 1);
  }
  span = clampNumber(span, 1, maxExitSpan(tile, direction, x, y));
  exit.x = x;
  exit.y = y;
  exit.span = span;
  syncExitAnchor(tile, exit);
  return span;
}

function clampExitSpan(tile, direction, value, x, y) {
  return clampNumber(value, 1, maxExitSpan(tile, direction, x, y));
}

function maxExitSpan(tile, direction, x, y) {
  x = clampNumber(x, 0, tile.footprint_width - 1);
  y = clampNumber(y, 0, tile.footprint_height - 1);
  const [stepX, stepY] = EXIT_SPAN_STEPS[direction] || [0, 0];
  const unlimited = tile.footprint_width + tile.footprint_height;
  const xRoom = stepX > 0 ? tile.footprint_width - x : stepX < 0 ? x + 1 : unlimited;
  const yRoom = stepY > 0 ? tile.footprint_height - y : stepY < 0 ? y + 1 : unlimited;
  return Math.max(1, Math.min(xRoom, yRoom));
}

function maxRequestableExitSpan(tile, direction) {
  if (!["north", "south", "east", "west"].includes(direction)) return Math.min(tile.footprint_width, tile.footprint_height);
  return direction === "north" || direction === "south" ? tile.footprint_width : tile.footprint_height;
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
  return Boolean(tile && editor.catalog === "ee" && /^0[1-6]$/.test(tile.key));
}

toolButtons.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-mode]");
  if (!button) return;
  if (button.disabled) return;
  if (button.dataset.mode === "water_toggle") {
    editor.paintSurface = editor.paintSurface === "water" ? "floor" : "water";
    renderTools();
    return;
  }
  editor.mode = button.dataset.mode;
  renderTools();
});

document.addEventListener("click", (event) => {
  const button = event.target.closest(".help-button[data-help-topic]");
  if (!button) return;
  event.preventDefault();
  event.stopPropagation();
  showHelp(button.dataset.helpTopic);
});

tileFilter.addEventListener("change", () => {
  persistForm();
  editor.listFilter = tileFilter.value;
  renderTileList();
});

tileCatalogSelect?.addEventListener("change", async () => {
  persistForm();
  editor.catalog = tileCatalogSelect.value;
  if (editor.catalog !== "forsaken_depths_rivers") editor.paintSurface = "floor";
  await loadTiles();
});

const initialCatalog = new URLSearchParams(window.location.search).get("catalog");
if (initialCatalog && tileCatalogSelect) {
  tileCatalogSelect.value = initialCatalog;
  editor.catalog = initialCatalog;
}

for (const input of [nameInput, descriptionInput]) {
  input.addEventListener("input", () => {
    persistForm();
    const tile = selectedTile();
    if (!tile) return;
    tileTitle.textContent = `${tile.key} ${tile.name}`;
    refreshValidationViews(tile);
  });
}

for (const input of [typeInput, implementationStatusInput]) {
  input.addEventListener("change", () => {
    persistForm();
    const tile = selectedTile();
    if (tile) refreshValidationViews(tile);
  });
}

for (const input of [widthInput, heightInput, cellSizeInput, imageScaleInput, imageOffsetXInput, imageOffsetYInput]) {
  input.addEventListener("change", () => {
    persistForm();
    renderSelectedTile();
    renderTileList();
  });
}

document.querySelectorAll("[data-offset-action]").forEach((button) => {
  button.addEventListener("click", () => adjustImageOffset(button.dataset.offsetAction));
});

lockImageInput.addEventListener("change", () => {
  editor.imageLocked = lockImageInput.checked;
  renderImageLock();
  renderTools();
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
  refreshValidationViews(tile);
});

exportTilesButton.addEventListener("click", exportTileMetadata);
importTilesButton.addEventListener("click", () => importTilesFile.click());
importTilesFile.addEventListener("change", () => importTileMetadata(importTilesFile.files?.[0]));

saveButton.addEventListener("click", async () => {
  try {
    persistForm();
    const selectedKey = editor.selectedKey;
    await api(`/api/rules/tiles?${catalogQuery()}`, {
      method: "PUT",
      body: JSON.stringify(editor.tiles),
    });
    await loadTiles();
    editor.selectedKey = selectedKey;
    renderTileList();
    renderSelectedTile();
    setStatus("Saved");
  } catch (error) {
    setStatus(error.message);
  }
});

loadTiles();
