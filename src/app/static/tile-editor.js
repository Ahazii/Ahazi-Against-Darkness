const editor = {
  catalog: "ee",
  tiles: [],
  selectedKey: null,
  mode: "walkable_toggle",
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
      "Use Delete Exit, or the Remove button in this list, to delete a door or passage placed by mistake.",
    ],
  },
  "room-codes": {
    title: "Forsaken Depths Room Codes",
    paragraphs: [
      "Dungeon tiles (FD p.32): NC = narrow corridor; ETC = entrance to Citadel (separate sheet); ETR = exit to river (separate river map).",
      "River stretch tiles (FD p.37–40): END = river end (no longer navigable); Ru = ruin; Ca = cairn (printed as C on tile art); B = bridge.",
      "Most rooms and stretches have no letter code — leave all checkboxes unchecked for a normal room or ordinary river stretch.",
      "Mark only the codes printed on the scan or confirmed from the rulebook for that element.",
    ],
  },
  water: {
    title: "Water Squares",
    paragraphs: [
      "Blue squares mark river water on Forsaken Depths river stretches (FD p.37).",
      "Water is not on-foot walkable; boat navigation rules apply when river play is implemented.",
      "Place exits on walkable bank squares, not on water.",
    ],
  },
};

const CELL_SHAPE_MODES = {
  half_cycle: ["a", "b", "c", "d", "A", "B", "C", "D"],
  slope_cycle: ["E", "G", "H", "I"],
  curve_cycle: ["e", "g", "h", "i", "J", "K", "L", "M"],
};

const HALF_CURVE_CYCLE = [
  "f",
  "j",
  "k",
  "l",
  "z",
  "2",
  "3",
  "4",
  "5",
  "6",
  "m",
  "n",
  "o",
  "p",
  "Z",
  "7",
  "8",
  "9",
  "0",
  "y",
  "q",
  "r",
  "s",
  "t",
  "u",
  "v",
  "w",
  "x",
];

const BIDIRECTIONAL_GRID_MODES = new Set([
  "walkable_toggle",
  "half_cycle",
  "slope_cycle",
  "curve_cycle",
  "half_curve_cycle",
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
  { codes: ["N", "O"], dx: 0, dy: 1 },
  { codes: ["P", "Q"], dx: 0, dy: 1 },
  { codes: ["R", "S"], dx: 1, dy: 0 },
  { codes: ["T", "U"], dx: 1, dy: 0 },
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
  j: "Half top blocked + shallow semicircle wall in bottom half",
  k: "Half top blocked + medium semicircle wall in bottom half",
  l: "Half top blocked + deep semicircle wall in bottom half",
  z: "Half top blocked + shallow left-side quarter arc in bottom half",
  2: "Half top blocked + medium left-side quarter arc in bottom half",
  3: "Half top blocked + deep left-side quarter arc in bottom half",
  4: "Half top blocked + shallow right-side quarter arc in bottom half",
  5: "Half top blocked + medium right-side quarter arc in bottom half",
  6: "Half top blocked + deep right-side quarter arc in bottom half",
  m: "Half bottom blocked (flat), open top half",
  n: "Half bottom blocked + shallow semicircle wall in top half",
  o: "Half bottom blocked + medium semicircle wall in top half",
  p: "Half bottom blocked + deep semicircle wall in top half",
  Z: "Half bottom blocked + shallow left-side quarter arc in top half",
  7: "Half bottom blocked + medium left-side quarter arc in top half",
  8: "Half bottom blocked + deep left-side quarter arc in top half",
  9: "Half bottom blocked + shallow right-side quarter arc in top half",
  0: "Half bottom blocked + medium right-side quarter arc in top half",
  y: "Half bottom blocked + deep right-side quarter arc in top half",
  q: "Half left blocked (flat), open right half",
  r: "Half left blocked + shallow semicircle wall in right half",
  s: "Half left blocked + medium semicircle wall in right half",
  t: "Half left blocked + deep semicircle wall in right half",
  u: "Half right blocked (flat), open left half",
  v: "Half right blocked + shallow semicircle wall in left half",
  w: "Half right blocked + medium semicircle wall in left half",
  x: "Half right blocked + deep semicircle wall in left half",
  1: "Half right blocked + shallow left-side quarter arc in open half",
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
  normalizeTile(tile);
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

  const blockedExitLabels = exits.filter((exit) => exitTouchesBlockedSquare(tile, exit)).map(exitLabelForValidation);
  add(
    blockedExitLabels.length ? "fail" : "pass",
    blockedExitLabels.length ? `Exit on blocked square: ${blockedExitLabels.join(", ")}` : "All exits touch walkable squares"
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

function exitTouchesBlockedSquare(tile, exit) {
  return exitCells(tile, exit).some(({ x, y }) => tile.walkable[y]?.[x] === "0");
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
  for (const button of toolButtons.querySelectorAll("button")) {
    button.disabled =
      previewing ||
      (button.dataset.mode === "dungeon_exit" && !startTile) ||
      (button.dataset.mode === "move_image" && editor.imageLocked);
    button.classList.toggle("selected", !previewing && button.dataset.mode === editor.mode);
  }
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
      refreshValidationViews(tile);
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
      refreshValidationViews(tile);
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
      refreshValidationViews(tile);
    });
    dungeonExit.append(checkbox, document.createTextNode("Dungeon exit"));
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "Remove";
    remove.title = "Delete this door or passage from the map element.";
    remove.addEventListener("click", () => {
      removeExit(tile, exit.id);
      renderGrid(tile);
      renderExitList(tile);
      refreshValidationViews(tile);
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
  exit.span = clampExitSpan(tile, exit.direction, exit.span || 1, exit.x, exit.y);
  exit.offset = exitOffset(exit.direction, exit.x, exit.y);
  exit.position = exitPosition(exit.direction, exit.offset, tile.footprint_width, tile.footprint_height);
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
    cycleWalkableSurface(tile, x, y, step);
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (editor.mode === "water_toggle") {
    if (step < 0) return;
    const current = surfaceCode(tile, x, y);
    setSurface(tile, x, y, current === "2" ? "0" : "2");
    setCellShape(tile, x, y, "F");
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (editor.mode === "half_curve_cycle") {
    cycleShapeList(tile, x, y, HALF_CURVE_CYCLE, step);
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (CELL_SHAPE_MODES[editor.mode]) {
    cycleShapeList(tile, x, y, CELL_SHAPE_MODES[editor.mode], step);
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (editor.mode === "long_slope_cycle") {
    if (step < 0) return;
    cycleLongSlope(tile, x, y);
    renderGrid(tile);
    refreshValidationViews(tile);
    return;
  }

  if (step < 0) return;

  const direction = nearestEdge(event);
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

function cycleShapeList(tile, x, y, shapes, step = 1) {
  const current = cellShape(tile, x, y);
  const onWalkable = isWalkable(tile, x, y);
  let index = onWalkable && shapes.includes(current) ? shapes.indexOf(current) : -1;

  if (step > 0) {
    if (index === -1) {
      setWalkable(tile, x, y, true);
      setCellShape(tile, x, y, shapes[0]);
      return;
    }
    if (index === shapes.length - 1) {
      setWalkable(tile, x, y, true);
      setCellShape(tile, x, y, "F");
      return;
    }
    setWalkable(tile, x, y, true);
    setCellShape(tile, x, y, shapes[index + 1]);
    return;
  }

  if (index === -1) {
    setWalkable(tile, x, y, true);
    setCellShape(tile, x, y, shapes[shapes.length - 1]);
    return;
  }
  if (index === 0) {
    setWalkable(tile, x, y, true);
    setCellShape(tile, x, y, "F");
    return;
  }
  setWalkable(tile, x, y, true);
  setCellShape(tile, x, y, shapes[index - 1]);
}

function cycleLongSlope(tile, x, y) {
  const current = cellShape(tile, x, y);
  const currentIndex = LONG_SLOPE_PATTERNS.findIndex((pattern) => pattern.codes.includes(current));
  clearLongSlopeTouching(tile, x, y);
  for (let step = 1; step <= LONG_SLOPE_PATTERNS.length; step += 1) {
    const nextIndex = (currentIndex + step) % (LONG_SLOPE_PATTERNS.length + 1);
    if (nextIndex >= LONG_SLOPE_PATTERNS.length) return;
    const pattern = LONG_SLOPE_PATTERNS[nextIndex];
    if (x + pattern.dx < tile.footprint_width && y + pattern.dy < tile.footprint_height) {
      applyLongSlopePattern(tile, x, y, pattern);
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

function applyLongSlopePattern(tile, x, y, pattern) {
  setWalkable(tile, x, y, true);
  setWalkable(tile, x + pattern.dx, y + pattern.dy, true);
  setCellShape(tile, x, y, pattern.codes[0]);
  setCellShape(tile, x + pattern.dx, y + pattern.dy, pattern.codes[1]);
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

function walkableSurfaceCycleIndex(tile, x, y) {
  const code = surfaceCode(tile, x, y);
  const shape = cellShape(tile, x, y);
  if (code === "2") return -1;
  const index = WALKABLE_SURFACE_CYCLE.findIndex((state) => state.walkable === code && state.shape === shape);
  if (index >= 0) return index;
  if (code === "0") return 0;
  return WALKABLE_SURFACE_CYCLE.length - 1;
}

function cycleWalkableSurface(tile, x, y, step = 1) {
  let currentIndex = walkableSurfaceCycleIndex(tile, x, y);
  if (currentIndex < 0) {
    const fallback = step > 0 ? WALKABLE_SURFACE_CYCLE[0] : WALKABLE_SURFACE_CYCLE[WALKABLE_SURFACE_CYCLE.length - 1];
    setSurface(tile, x, y, fallback.walkable);
    setCellShape(tile, x, y, fallback.shape);
    return;
  }
  const nextIndex =
    step > 0
      ? (currentIndex + 1) % WALKABLE_SURFACE_CYCLE.length
      : (currentIndex - 1 + WALKABLE_SURFACE_CYCLE.length) % WALKABLE_SURFACE_CYCLE.length;
  const next = WALKABLE_SURFACE_CYCLE[nextIndex];
  setSurface(tile, x, y, next.walkable);
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
  if (isWater(tile, x, y)) return "Water";
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
    {
      A: "C", C: "D", D: "B", B: "A", E: "H", H: "I", I: "G", G: "E", J: "L", L: "M", M: "K", K: "J", N: "T", O: "U", P: "R", Q: "S", R: "N", S: "O", T: "P", U: "Q",
      f: "u", j: "v", k: "w", l: "x", z: "1", 2: "v", 3: "w", 4: "x", 5: "l", 6: "k",
      m: "q", n: "r", o: "s", p: "t", Z: "7", 7: "r", 8: "s", 9: "t", 0: "p", y: "o",
      q: "m", r: "n", s: "o", t: "p", u: "f", v: "j", w: "k", x: "l", 1: "z",
    },
    {
      A: "D", D: "A", B: "C", C: "B", E: "I", I: "E", G: "H", H: "G", J: "M", M: "J", K: "L", L: "K", N: "Q", O: "P", P: "O", Q: "N", R: "U", S: "T", T: "S", U: "R",
      f: "m", j: "n", k: "o", l: "p", z: "Z", 2: "7", 3: "8", 4: "9", 5: "0", 6: "y",
      m: "f", n: "j", o: "k", p: "l", Z: "z", 7: "2", 8: "3", 9: "4", 0: "5", y: "6",
      q: "u", r: "v", s: "w", t: "x", u: "q", v: "r", w: "s", x: "t", 1: "8",
    },
    {
      A: "B", B: "D", D: "C", C: "A", E: "G", G: "I", I: "H", H: "E", J: "K", K: "M", M: "L", L: "J", N: "R", O: "S", P: "T", Q: "U", R: "P", S: "Q", T: "N", U: "O",
      f: "q", j: "r", k: "s", l: "t", z: "7", 2: "r", 3: "s", 4: "t", 5: "p", 6: "o",
      m: "u", n: "v", o: "w", p: "x", Z: "1", 7: "v", 8: "w", 9: "x", 0: "l", y: "k",
      q: "f", r: "j", s: "k", t: "l", u: "m", v: "n", w: "o", x: "p", 1: "3",
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
  return Boolean(tile && editor.catalog === "ee" && /^0[1-6]$/.test(tile.key));
}

toolButtons.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-mode]");
  if (!button) return;
  if (button.disabled) return;
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
