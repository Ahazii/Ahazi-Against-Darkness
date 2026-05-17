const state = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  sessions: [],
  session: null,
  selectedCharacterId: null,
  selectedPartyId: null,
  editingPartyId: null,
  characterFilters: { classId: "all", level: "all", sort: "name", direction: "asc" },
  partyFilters: { classId: "all", level: "all", sort: "name", direction: "asc" },
  showRolls: true,
  showMath: false,
  mapZoom: 1,
  lastCenteredTileId: null,
};

const ACTIVE_SESSION_KEY = "ahazi-against-darkness.active-session-id";
const WINDOW_SESSION_PREFIX = "ahazi-active-session:";

const apiStatus = document.getElementById("api-status");
const characterClass = document.getElementById("character-class");
const characterForm = document.getElementById("character-form");
const characterName = document.getElementById("character-name");
const characterCount = document.getElementById("character-count");
const charactersEl = document.getElementById("characters");
const characterFilterClass = document.getElementById("character-filter-class");
const characterFilterLevel = document.getElementById("character-filter-level");
const characterSort = document.getElementById("character-sort");
const characterSortDirection = document.getElementById("character-sort-direction");
const partyForm = document.getElementById("party-form");
const partyName = document.getElementById("party-name");
const partyPicks = document.getElementById("party-picks");
const saveParty = document.getElementById("save-party");
const cancelPartyEdit = document.getElementById("cancel-party-edit");
const partiesEl = document.getElementById("parties");
const partyFilterClass = document.getElementById("party-filter-class");
const partyFilterLevel = document.getElementById("party-filter-level");
const partySort = document.getElementById("party-sort");
const partySortDirection = document.getElementById("party-sort-direction");
const partySelect = document.getElementById("party-select");
const adventureSelect = document.getElementById("adventure-select");
const adventuresEl = document.getElementById("adventures");
const setupPanel = document.getElementById("setup-panel");
const saveCount = document.getElementById("save-count");
const savedGamesEl = document.getElementById("saved-games");
const startSession = document.getElementById("start-session");
const resumeSessionBtn = document.getElementById("resume-session");
const sessionPanel = document.getElementById("session-panel");
const showSetupBtn = document.getElementById("show-setup");
const sessionMode = document.getElementById("session-mode");
const mapEl = document.getElementById("map");
const mapZoomOut = document.getElementById("map-zoom-out");
const mapZoomIn = document.getElementById("map-zoom-in");
const mapZoomReset = document.getElementById("map-zoom-reset");
const mapZoomLabel = document.getElementById("map-zoom-label");
const mapCenterCurrent = document.getElementById("map-center-current");
const mapPanUp = document.getElementById("map-pan-up");
const mapPanDown = document.getElementById("map-pan-down");
const mapPanLeft = document.getElementById("map-pan-left");
const mapPanRight = document.getElementById("map-pan-right");
const tileDetail = document.getElementById("tile-detail");
const exitActions = document.getElementById("exit-actions");
const partyState = document.getElementById("party-state");
const sessionLog = document.getElementById("session-log");
const searchBtn = document.getElementById("search");
const combatBtn = document.getElementById("combat-round");
const restBtn = document.getElementById("rest");
const saveSessionBtn = document.getElementById("save-session");
const showRollsInput = document.getElementById("show-rolls");
const showMathInput = document.getElementById("show-math");
saveSessionBtn.disabled = true;

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

function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function subline(text) {
  const el = node("div", "muted");
  el.textContent = text;
  return el;
}

async function loadAll() {
  try {
    const [classes, characters, parties, adventures, sessions] = await Promise.all([
      api("/api/rules/classes"),
      api("/api/characters"),
      api("/api/parties"),
      api("/api/adventures"),
      api("/api/sessions"),
    ]);
    state.classes = classes;
    state.characters = characters;
    state.parties = parties;
    state.adventures = adventures;
    state.sessions = sessions;
    apiStatus.textContent = "Connected";
    renderSetup();
    await restoreActiveSession();
  } catch (error) {
    apiStatus.textContent = error.message;
  }
}

function renderSetup() {
  showSetupView();
  renderClasses();
  renderCharacters();
  renderParties();
  renderAdventures();
  renderSavedGames();
  resumeSessionBtn.classList.toggle("hidden", !state.session);
}

function setStatus(message) {
  apiStatus.textContent = message;
}

function handleError(error) {
  setStatus(error.message || "Action failed");
}

function renderClasses() {
  characterClass.replaceChildren();
  for (const profile of state.classes) {
    const option = document.createElement("option");
    option.value = profile.id;
    option.textContent = profile.name;
    characterClass.appendChild(option);
  }
}

function renderCharacterControls() {
  state.characterFilters.classId = renderClassFilter(characterFilterClass, state.characterFilters.classId);
  state.characterFilters.level = renderLevelFilter(characterFilterLevel, characterLevels(), state.characterFilters.level);
  state.characterFilters.sort = renderSortOptions(
    characterSort,
    [
      ["name", "Name"],
      ["class_name", "Class"],
      ["level", "Level"],
      ["gold", "Gold"],
      ["xp", "XP"],
      ["current_life", "Current HP"],
      ["max_life", "Max HP"],
      ["attack_bonus", "Attack"],
      ["defense_bonus", "Defense"],
      ["save_bonus", "Save"],
    ],
    state.characterFilters.sort
  );
  characterSortDirection.textContent = state.characterFilters.direction === "asc" ? "Asc" : "Desc";
}

function renderPartyControls() {
  state.partyFilters.classId = renderClassFilter(partyFilterClass, state.partyFilters.classId);
  state.partyFilters.level = renderLevelFilter(partyFilterLevel, partyAverageLevels(), state.partyFilters.level);
  state.partyFilters.sort = renderSortOptions(
    partySort,
    [
      ["name", "Name"],
      ["averageLevel", "Avg Level"],
      ["classesLabel", "Class Mix"],
      ["memberCount", "Members"],
      ["updated_at", "Updated"],
    ],
    state.partyFilters.sort
  );
  partySortDirection.textContent = state.partyFilters.direction === "asc" ? "Asc" : "Desc";
}

function renderClassFilter(select, selectedValue) {
  const options = [["all", "All classes"], ...state.classes.map((profile) => [profile.id, profile.name])];
  return renderSelectOptions(select, options, selectedValue);
}

function renderLevelFilter(select, levels, selectedValue) {
  return renderSelectOptions(select, [["all", "All levels"], ...levels.map((level) => [String(level), String(level)])], selectedValue);
}

function renderSortOptions(select, options, selectedValue) {
  return renderSelectOptions(select, options, selectedValue);
}

function renderSelectOptions(select, options, selectedValue) {
  const current = options.some(([value]) => value === selectedValue) ? selectedValue : options[0]?.[0] || "";
  select.replaceChildren();
  for (const [value, label] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === current;
    select.appendChild(option);
  }
  select.value = current;
  return current;
}

function characterLevels() {
  return [...new Set(state.characters.map((character) => character.level))].sort((left, right) => left - right);
}

function partyAverageLevels() {
  return [...new Set(state.parties.map((party) => partyStats(party).averageLevelLabel))].sort((left, right) =>
    Number(left) - Number(right)
  );
}

function filteredCharacters() {
  return state.characters.filter((character) => {
    const filters = state.characterFilters;
    if (filters.classId !== "all" && character.class_id !== filters.classId) return false;
    if (filters.level !== "all" && String(character.level) !== filters.level) return false;
    return true;
  });
}

function sortedCharacters(characters) {
  return sortBy(characters, state.characterFilters.sort, state.characterFilters.direction);
}

function filteredParties() {
  return state.parties.filter((party) => {
    const filters = state.partyFilters;
    const stats = partyStats(party);
    if (filters.classId !== "all" && !stats.members.some((member) => member.class_id === filters.classId)) return false;
    if (filters.level !== "all" && stats.averageLevelLabel !== filters.level) return false;
    return true;
  });
}

function sortedParties(parties) {
  return [...parties].sort((left, right) => {
    const leftStats = partyStats(left);
    const rightStats = partyStats(right);
    const key = state.partyFilters.sort;
    const direction = state.partyFilters.direction;
    const leftValue = key in leftStats ? leftStats[key] : left[key];
    const rightValue = key in rightStats ? rightStats[key] : right[key];
    return compareValues(leftValue, rightValue, direction);
  });
}

function sortBy(items, key, direction) {
  return [...items].sort((left, right) => compareValues(left[key], right[key], direction));
}

function compareValues(left, right, direction) {
  const modifier = direction === "desc" ? -1 : 1;
  if (typeof left === "number" && typeof right === "number") return (left - right) * modifier;
  return String(left ?? "").localeCompare(String(right ?? ""), undefined, { numeric: true }) * modifier;
}

function partyStats(party) {
  const members = party.character_ids.map((id) => state.characters.find((character) => character.id === id)).filter(Boolean);
  const averageLevel = members.length
    ? members.reduce((total, member) => total + member.level, 0) / members.length
    : 0;
  const averageLevelLabel = Number.isInteger(averageLevel) ? String(averageLevel) : averageLevel.toFixed(1);
  const classes = [...new Set(members.map((member) => member.class_name))].sort();
  return {
    members,
    memberCount: members.length,
    averageLevel,
    averageLevelLabel,
    classesLabel: classes.length ? classes.join(", ") : "No classes",
  };
}

function renderCharacters() {
  const checkedIds = state.editingPartyId
    ? currentPartyEditIds()
    : Array.from(partyPicks.querySelectorAll("input:checked")).map((input) => input.value);
  renderCharacterControls();
  const visibleCharacters = sortedCharacters(filteredCharacters());
  characterCount.textContent =
    visibleCharacters.length === state.characters.length
      ? `${state.characters.length} saved`
      : `${visibleCharacters.length} of ${state.characters.length}`;
  charactersEl.replaceChildren();
  partyPicks.replaceChildren();

  for (const character of visibleCharacters) {
    const item = node("div", "item selectable-item");
    item.tabIndex = 0;
    if (character.id === state.selectedCharacterId) item.classList.add("selected");
    item.appendChild(node("strong", "", `${character.name} - ${character.class_name}`));
    item.appendChild(
      subline(
        `L${character.level} HP ${character.current_life}/${character.max_life} ATK +${character.attack_bonus} DEF +${character.defense_bonus} SAVE +${character.save_bonus}`
      )
    );
    item.appendChild(subline(`Gold ${character.gold} | XP ${character.xp}`));
    if (character.id === state.selectedCharacterId) {
      item.appendChild(subline(`Inventory: ${character.inventory.join(", ") || "none"}`));
      item.appendChild(subline(`Spells: ${character.spells.join(", ") || "none"}`));
      const actions = node("div", "item-actions");
      const remove = node("button", "danger-button", "Delete");
      remove.type = "button";
      remove.addEventListener("click", async (event) => {
        event.stopPropagation();
        await deleteCharacter(character.id);
      });
      actions.appendChild(remove);
      item.appendChild(actions);
    }
    item.addEventListener("click", () => {
      state.selectedCharacterId = state.selectedCharacterId === character.id ? null : character.id;
      renderCharacters();
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        item.click();
      }
    });
    charactersEl.appendChild(item);
  }

  for (const character of sortedCharacters([...state.characters])) {
    const pick = node("label", "pick");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = character.id;
    checkbox.checked = checkedIds.includes(character.id);
    pick.appendChild(checkbox);
    const labelText = node("span");
    labelText.appendChild(node("strong", "", character.name));
    labelText.appendChild(subline(`${character.class_name} | L${character.level} | Gold ${character.gold}`));
    pick.appendChild(labelText);
    partyPicks.appendChild(pick);
  }
}

function renderParties() {
  renderPartyControls();
  partiesEl.replaceChildren();
  partySelect.replaceChildren();
  const visibleParties = sortedParties(filteredParties());
  for (const party of visibleParties) {
    const stats = partyStats(party);
    const item = node("div", "item selectable-item");
    item.tabIndex = 0;
    if (party.id === state.selectedPartyId) item.classList.add("selected");
    item.appendChild(node("strong", "", party.name));
    item.appendChild(subline(`${party.character_ids.length} members | Avg L${stats.averageLevelLabel} | ${stats.classesLabel}`));
    if (party.id === state.selectedPartyId) {
      for (const member of stats.members) {
        item.appendChild(subline(`${member.name} - ${member.class_name} | L${member.level} | Gold ${member.gold}`));
      }
      const actions = node("div", "item-actions");
      const edit = node("button", "secondary", "Edit");
      edit.type = "button";
      edit.addEventListener("click", (event) => {
        event.stopPropagation();
        startPartyEdit(party);
      });
      const remove = node("button", "danger-button", "Delete");
      remove.type = "button";
      remove.addEventListener("click", async (event) => {
        event.stopPropagation();
        await deleteParty(party.id);
      });
      actions.append(edit, remove);
      item.appendChild(actions);
    }
    item.addEventListener("click", () => {
      state.selectedPartyId = state.selectedPartyId === party.id ? null : party.id;
      renderParties();
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        item.click();
      }
    });
    partiesEl.appendChild(item);
  }

  for (const party of state.parties) {
    const option = document.createElement("option");
    option.value = party.id;
    const stats = partyStats(party);
    option.textContent = `${party.name} (Avg L${stats.averageLevelLabel})`;
    partySelect.appendChild(option);
  }
}

function renderAdventures() {
  adventuresEl.replaceChildren();
  adventureSelect.replaceChildren();
  for (const adventure of state.adventures) {
    const option = document.createElement("option");
    option.value = adventure.id;
    option.disabled = !adventure.playable;
    option.textContent = adventure.playable ? adventure.name : `${adventure.name} (manifest needed)`;
    adventureSelect.appendChild(option);

    const item = node("div", "item");
    item.appendChild(node("strong", "", adventure.name));
    item.appendChild(subline(adventure.notes));
    adventuresEl.appendChild(item);
  }
}

function renderSavedGames() {
  savedGamesEl.replaceChildren();
  const savedSessions = [...state.sessions]
    .filter((session) => session.saved_at)
    .sort((left, right) => right.saved_at.localeCompare(left.saved_at));
  saveCount.textContent = `${savedSessions.length} saved`;
  if (!savedSessions.length) {
    savedGamesEl.appendChild(node("div", "item", "No manual saves yet."));
    return;
  }
  for (const session of savedSessions.slice(0, 5)) {
    const item = node("div", "item selectable-item");
    if (state.session?.id === session.id) item.classList.add("selected");
    item.appendChild(node("strong", "", `${partyNameById(session.party_id)} - ${session.adventure_id}`));
    item.appendChild(
      subline(`${session.mode} | saved ${formatDateTime(session.saved_at)} | ${session.map_state.tiles.length} map elements`)
    );
    const actions = node("div", "item-actions");
    const load = node("button", "secondary", state.session?.id === session.id ? "Current" : "Load");
    load.type = "button";
    load.disabled = state.session?.id === session.id;
    load.addEventListener("click", async () => loadSession(session.id));
    const remove = node("button", "danger-button", "Delete");
    remove.type = "button";
    remove.addEventListener("click", async () => deleteSession(session.id));
    actions.append(load, remove);
    item.appendChild(actions);
    savedGamesEl.appendChild(item);
  }
}

async function refreshSessions() {
  state.sessions = await api("/api/sessions");
  renderSavedGames();
}

async function restoreActiveSession() {
  if (state.session) {
    renderSession();
    return;
  }
  const sessionId = readActiveSessionId();
  if (!sessionId) return;
  try {
    await loadSession(sessionId, { quiet: true });
  } catch {
    clearActiveSessionId();
  }
}

async function loadSession(sessionId, options = {}) {
  state.session = await api(`/api/sessions/${sessionId}`);
  writeActiveSessionId(state.session.id);
  renderSession();
  renderSavedGames();
  if (!options.quiet) setStatus("Saved game loaded");
}

async function deleteSession(sessionId) {
  try {
    await api(`/api/sessions/${sessionId}`, { method: "DELETE" });
    if (state.session?.id === sessionId) {
      state.session = null;
      clearActiveSessionId();
      showSetupView();
      saveSessionBtn.disabled = true;
    }
    await refreshSessions();
    setStatus("Saved game deleted");
  } catch (error) {
    handleError(error);
  }
}

function readActiveSessionId() {
  try {
    if (window.localStorage) {
      const value = window.localStorage.getItem(ACTIVE_SESSION_KEY);
      if (value) return value;
    }
  } catch {
    // Fall back to window.name below.
  }
  return window.name?.startsWith(WINDOW_SESSION_PREFIX) ? window.name.slice(WINDOW_SESSION_PREFIX.length) : "";
}

function writeActiveSessionId(sessionId) {
  try {
    if (window.localStorage) window.localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
  } catch {
    // Fall back to window.name below.
  }
  window.name = `${WINDOW_SESSION_PREFIX}${sessionId}`;
}

function clearActiveSessionId() {
  try {
    if (window.localStorage) window.localStorage.removeItem(ACTIVE_SESSION_KEY);
  } catch {
    // Fall back to window.name below.
  }
  if (window.name?.startsWith(WINDOW_SESSION_PREFIX)) window.name = "";
}

function partyNameById(partyId) {
  return state.parties.find((party) => party.id === partyId)?.name || `Party ${partyId.slice(0, 6)}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { dateStyle: "short", timeStyle: "short" });
}

function renderSession() {
  const session = state.session;
  if (!session) return;
  showGameView();
  sessionMode.textContent = session.mode;
  showRollsInput.checked = state.showRolls;
  showMathInput.checked = state.showMath;
  renderMap(session);
  renderTileDetail(session);
  renderExitActions(session);
  renderPartyState(session);
  renderLog(session);
  searchBtn.disabled = session.mode !== "exploration";
  restBtn.disabled = session.mode !== "exploration";
  combatBtn.disabled = session.mode !== "combat";
  saveSessionBtn.disabled = false;
}

function renderMap(session) {
  mapEl.replaceChildren();
  const tiles = session.map_state.tiles;
  const minX = Math.min(...tiles.map((tile) => tile.x));
  const maxX = Math.max(...tiles.map((tile) => tile.x + rotatedWidth(tile) - 1));
  const minY = Math.min(...tiles.map((tile) => tile.y));
  const maxY = Math.max(...tiles.map((tile) => tile.y + rotatedHeight(tile) - 1));
  const cell = Math.round(116 * state.mapZoom);
  const pad = 1;
  let currentTileEl = null;
  mapEl.style.setProperty("--cell", `${cell}px`);
  mapEl.style.minWidth = `${(maxX - minX + pad * 2 + 1) * cell}px`;
  mapEl.style.minHeight = `${(maxY - minY + pad * 2 + 1) * cell}px`;
  mapZoomLabel.textContent = `${Math.round(state.mapZoom * 100)}%`;

  for (const tile of tiles) {
    const el = node("button", `placed-tile ${tile.tile_type}`);
    if (tile.id === session.map_state.current_tile_id) {
      el.classList.add("current");
      currentTileEl = el;
    }
    const width = rotatedWidth(tile);
    const height = rotatedHeight(tile);
    el.style.left = `${(tile.x - minX + pad) * cell}px`;
    el.style.top = `${(tile.y - minY + pad) * cell}px`;
    el.style.width = `${width * cell}px`;
    el.style.height = `${height * cell}px`;
    el.title = tile.title;

    if (tile.image) {
      const image = document.createElement("img");
      image.src = tile.image;
      image.alt = tile.title;
      image.style.width = `${(tile.footprint_width || 1) * cell}px`;
      image.style.height = `${(tile.footprint_height || 1) * cell}px`;
      image.style.transform = mapImageTransform(tile, cell);
      el.appendChild(image);
    }
    el.appendChild(tileOverlay(tile));
    const key = node("span", "tile-key", tile.tile_key);
    el.appendChild(key);
    if (tile.id === session.map_state.current_tile_id) {
      el.appendChild(node("span", "current-party-marker", "Current Party"));
    }
    mapEl.appendChild(el);
  }
  if (currentTileEl && state.lastCenteredTileId !== session.map_state.current_tile_id) {
    state.lastCenteredTileId = session.map_state.current_tile_id;
    requestAnimationFrame(() => centerMapOn(currentTileEl));
  }
}

function setMapZoom(nextZoom, { recenter = false } = {}) {
  state.mapZoom = clampFloat(nextZoom, 0.35, 2.5);
  if (recenter) state.lastCenteredTileId = null;
  if (state.session) renderMap(state.session);
}

function panMap(deltaX, deltaY) {
  mapEl.scrollBy({ left: deltaX, top: deltaY, behavior: "smooth" });
}

function centerCurrentTile() {
  const current = mapEl.querySelector(".placed-tile.current");
  if (current) centerMapOn(current);
}

function centerMapOn(element) {
  mapEl.scrollLeft = element.offsetLeft + element.offsetWidth / 2 - mapEl.clientWidth / 2;
  mapEl.scrollTop = element.offsetTop + element.offsetHeight / 2 - mapEl.clientHeight / 2;
}

function handleMapWheel(event) {
  if (!event.ctrlKey) return;
  event.preventDefault();
  setMapZoom(state.mapZoom + (event.deltaY < 0 ? 0.1 : -0.1), { recenter: true });
}

function startMapPan(event) {
  if (!(event.button === 1 || event.shiftKey)) return;
  event.preventDefault();
  mapEl.classList.add("panning");
  mapEl.setPointerCapture(event.pointerId);
  const startX = event.clientX;
  const startY = event.clientY;
  const startScrollLeft = mapEl.scrollLeft;
  const startScrollTop = mapEl.scrollTop;

  const move = (moveEvent) => {
    mapEl.scrollLeft = startScrollLeft - (moveEvent.clientX - startX);
    mapEl.scrollTop = startScrollTop - (moveEvent.clientY - startY);
  };

  const stop = () => {
    mapEl.classList.remove("panning");
    mapEl.removeEventListener("pointermove", move);
    mapEl.removeEventListener("pointerup", stop);
    mapEl.removeEventListener("pointercancel", stop);
  };

  mapEl.addEventListener("pointermove", move);
  mapEl.addEventListener("pointerup", stop);
  mapEl.addEventListener("pointercancel", stop);
}

function currentPartyEditIds() {
  if (!state.editingPartyId) return [];
  const party = state.parties.find((item) => item.id === state.editingPartyId);
  return party ? party.character_ids : [];
}

function characterNameById(id) {
  const character = state.characters.find((item) => item.id === id);
  return character ? character.name : `Missing ${id.slice(0, 6)}`;
}

function startPartyEdit(party) {
  state.editingPartyId = party.id;
  state.selectedPartyId = party.id;
  partyName.value = party.name;
  saveParty.textContent = "Update Party";
  cancelPartyEdit.classList.remove("hidden");
  renderCharacters();
  renderParties();
}

function cancelPartyEditMode() {
  state.editingPartyId = null;
  partyName.value = "";
  saveParty.textContent = "Save Party";
  cancelPartyEdit.classList.add("hidden");
  partyPicks.querySelectorAll("input:checked").forEach((input) => {
    input.checked = false;
  });
  renderCharacters();
}

async function deleteCharacter(characterId) {
  try {
    await api(`/api/characters/${characterId}`, { method: "DELETE" });
    if (state.selectedCharacterId === characterId) state.selectedCharacterId = null;
    setStatus("Character deleted");
    await loadAll();
  } catch (error) {
    handleError(error);
  }
}

async function deleteParty(partyId) {
  try {
    await api(`/api/parties/${partyId}`, { method: "DELETE" });
    if (state.selectedPartyId === partyId) state.selectedPartyId = null;
    if (state.editingPartyId === partyId) cancelPartyEditMode();
    setStatus("Party deleted");
    await loadAll();
  } catch (error) {
    handleError(error);
  }
}

function tileOverlay(tile) {
  const overlay = node("div", "map-tile-overlay");
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const sideLabels = exitSideLabels(tile);
  overlay.style.gridTemplateColumns = `repeat(${width}, minmax(0, 1fr))`;
  overlay.style.gridTemplateRows = `repeat(${height}, minmax(0, 1fr))`;
  const walkable = normalizedWalkable(tile, width, height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      overlay.appendChild(node("span", `map-square ${walkable[y]?.[x] === "0" ? "blocked" : "walkable"} shape-${cellShape(tile, x, y)}`));
    }
  }
  for (const exit of tile.exits || []) {
    overlay.appendChild(mapExitMarker(tile, exit, width, height, sideLabels.get(exit.id)));
  }
  return overlay;
}

function mapExitMarker(tile, exit, width, height, sideLabel) {
  const marker = node("span", `map-exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""} ${exit.direction}`);
  const label = exitDisplayLabel(exit, sideLabel);
  marker.title = label;
  const cellW = 100 / width;
  const cellH = 100 / height;
  const x = Math.max(0, Math.min(exit.x || 0, width - 1));
  const y = Math.max(0, Math.min(exit.y || 0, height - 1));
  const span = clampExitSpan(exit, width, height);
  if (exit.direction === "north" || exit.direction === "south") {
    marker.style.left = `${x * cellW + cellW * (span / 2)}%`;
    marker.style.top = `${y * cellH + (exit.direction === "north" ? 0 : cellH)}%`;
    marker.style.width = `${cellW * Math.max(0.72, span - 0.16)}%`;
  } else {
    marker.style.left = `${x * cellW + (exit.direction === "west" ? 0 : cellW)}%`;
    marker.style.top = `${y * cellH + cellH * (span / 2)}%`;
    marker.style.height = `${cellH * Math.max(0.72, span - 0.16)}%`;
  }
  marker.appendChild(node("span", "map-exit-marker-label", compactExitLabel(exit, sideLabel)));
  return marker;
}

function clampExitSpan(exit, width, height) {
  const span = Math.max(1, Number.parseInt(exit.span || 1, 10));
  if (exit.direction === "north" || exit.direction === "south") {
    return Math.min(span, Math.max(1, width - Math.max(0, Math.min(exit.x || 0, width - 1))));
  }
  return Math.min(span, Math.max(1, height - Math.max(0, Math.min(exit.y || 0, height - 1))));
}

function clampFloat(value, min, max) {
  const number = Number.parseFloat(value);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function normalizedWalkable(tile, width, height) {
  const rows = Array.isArray(tile.walkable) ? tile.walkable : [];
  return Array.from({ length: height }, (_, y) => {
    const source = String(rows[y] || "");
    return Array.from({ length: width }, (__, x) => (source[x] === "0" ? "0" : "1")).join("");
  });
}

function cellShape(tile, x, y) {
  const rows = Array.isArray(tile.cell_shapes) ? tile.cell_shapes : [];
  return rows[y]?.[x] || "F";
}

function mapImageTransform(tile, cellSize) {
  const calibrationSize = tile.editor_cell_size || 80;
  const offsetScale = cellSize / calibrationSize;
  const offset = rotatedOffset((tile.image_offset_x || 0) * offsetScale, (tile.image_offset_y || 0) * offsetScale, tile.rotation || 0);
  const scale = tile.image_scale || 1;
  return `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px) rotate(${tile.rotation || 0}deg) scale(${scale})`;
}

function rotatedWidth(tile) {
  return (tile.rotation || 0) % 180 === 0 ? tile.footprint_width || 1 : tile.footprint_height || 1;
}

function rotatedHeight(tile) {
  return (tile.rotation || 0) % 180 === 0 ? tile.footprint_height || 1 : tile.footprint_width || 1;
}

function rotatedOffset(x, y, rotation) {
  const turns = ((rotation || 0) / 90) % 4;
  if (turns === 1) return { x: -y, y: x };
  if (turns === 2) return { x: -x, y: -y };
  if (turns === 3) return { x: y, y: -x };
  return { x, y };
}

function currentTile(session) {
  return session.map_state.tiles.find((tile) => tile.id === session.map_state.current_tile_id);
}

function renderTileDetail(session) {
  const tile = currentTile(session);
  const sideLabels = exitSideLabels(tile);
  tileDetail.replaceChildren();
  if (tile.image) {
    const image = document.createElement("img");
    image.src = tile.image;
    image.alt = tile.title;
    image.style.transform = `rotate(${tile.rotation || 0}deg)`;
    tileDetail.appendChild(image);
  } else {
    tileDetail.appendChild(node("div", "item", "No map element image available"));
  }

  const info = node("div");
  info.appendChild(node("h2", "", tile.title));
  info.appendChild(
    subline(
      `${tile.tile_type} | ${tile.content_key} | ${tile.footprint_width || 1}x${tile.footprint_height || 1} squares | rotation ${tile.rotation || 0}deg`
    )
  );
  info.appendChild(node("p", "", tile.description));
  info.appendChild(subline(`Objects: ${tile.objects.length ? tile.objects.join(", ") : "none"}`));
  info.appendChild(subline(`Enemies: ${tile.enemies.length ? tile.enemies.map((enemy) => `${enemy.name} ${enemy.life}/${enemy.max_life}`).join(", ") : "none"}`));
  info.appendChild(
    subline(
      `Exits: ${tile.exits
        .map((exit) => `${exitDisplayLabel(exit, sideLabels.get(exit.id))} ${exit.status}`)
        .join(", ")}`
    )
  );
  tileDetail.appendChild(info);
}

function renderExitActions(session) {
  const tile = currentTile(session);
  const sideLabels = exitSideLabels(tile);
  exitActions.replaceChildren();

  const heading = node("h2", "", "Exits");
  exitActions.appendChild(heading);
  if (session.mode === "complete") {
    const summary = node("div", "list compact");
    for (const line of session.summary || ["Adventure complete."]) {
      summary.appendChild(node("div", "item", line));
    }
    exitActions.appendChild(summary);
    return;
  }

  const buttons = node("div", "actions");
  const available = tile.exits.filter((exit) => exit.status !== "blocked");
  if (!available.length) {
    buttons.appendChild(subline("No available exits."));
  }

  for (const exit of available) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `exit-button ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""}`;
    button.disabled = session.mode !== "exploration";
    button.textContent = exitButtonLabel(exit, sideLabels.get(exit.id));
    button.title = exitDisplayLabel(exit, sideLabels.get(exit.id));
    button.addEventListener("click", () => advance("explore", { exit_id: exit.id, direction: exit.direction }));
    buttons.appendChild(button);
  }
  exitActions.appendChild(buttons);
}

function exitButtonLabel(exit, sideLabel) {
  const kind = exit.kind[0].toUpperCase() + exit.kind.slice(1);
  const label = sideLabel || titleCase(exit.direction);
  if (exit.dungeon_exit) {
    return `Leave Dungeon (${label})`;
  }
  if (exit.status === "open" && exit.destination_tile_id) {
    return `Go ${label}`;
  }
  if (exit.status === "open") {
    return `Follow ${label} ${kind}`;
  }
  const offset = exit.offset ? ` sq ${exit.offset + 1}` : "";
  return `Explore ${label}${offset} ${kind}`;
}

function exitDisplayLabel(exit, sideLabel) {
  const label = sideLabel || titleCase(exit.direction);
  if (exit.dungeon_exit) return `${label} dungeon exit`;
  return `${label} ${exit.kind}`;
}

function compactExitLabel(exit, sideLabel) {
  const label = sideLabel || titleCase(exit.direction);
  const compact = label
    .replace("North", "N")
    .replace("East", "E")
    .replace("South", "S")
    .replace("West", "W");
  if (exit.dungeon_exit) return `${compact}X`;
  return compact;
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

function renderPartyState(session) {
  partyState.replaceChildren();
  for (const member of session.party) {
    const item = node("div", "item");
    item.appendChild(node("strong", "", `${member.name} - ${member.class_name}`));
    item.appendChild(subline(`HP ${member.current_life}/${member.max_life} | Gold ${member.gold} | XP ${member.xp}`));
    item.appendChild(subline(`Inventory: ${member.inventory.join(", ") || "none"}`));
    partyState.appendChild(item);
  }
}

function renderLog(session) {
  sessionLog.replaceChildren();
  for (const entry of session.log.slice(-80)) {
    sessionLog.appendChild(node("div", "", entry));
  }
  sessionLog.scrollTop = sessionLog.scrollHeight;
}

function showGameView() {
  setupPanel.classList.add("hidden");
  sessionPanel.classList.remove("hidden");
  resumeSessionBtn.classList.toggle("hidden", !state.session);
}

function showSetupView() {
  setupPanel.classList.remove("hidden");
  sessionPanel.classList.add("hidden");
  resumeSessionBtn.classList.toggle("hidden", !state.session);
}

characterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/characters", {
      method: "POST",
      body: JSON.stringify({
        name: characterName.value,
        class_id: characterClass.value,
      }),
    });
    characterName.value = "";
    setStatus("Character saved");
    await loadAll();
  } catch (error) {
    handleError(error);
  }
});

partyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const character_ids = Array.from(partyPicks.querySelectorAll("input:checked")).map((input) => input.value);
    const path = state.editingPartyId ? `/api/parties/${state.editingPartyId}` : "/api/parties";
    await api(path, {
      method: state.editingPartyId ? "PUT" : "POST",
      body: JSON.stringify({
        name: partyName.value,
        character_ids,
      }),
    });
    setStatus(state.editingPartyId ? "Party updated" : "Party saved");
    cancelPartyEditMode();
    await loadAll();
  } catch (error) {
    handleError(error);
  }
});

cancelPartyEdit.addEventListener("click", cancelPartyEditMode);

characterFilterClass.addEventListener("change", () => {
  state.characterFilters.classId = characterFilterClass.value;
  renderCharacters();
});

characterFilterLevel.addEventListener("change", () => {
  state.characterFilters.level = characterFilterLevel.value;
  renderCharacters();
});

characterSort.addEventListener("change", () => {
  state.characterFilters.sort = characterSort.value;
  renderCharacters();
});

characterSortDirection.addEventListener("click", () => {
  state.characterFilters.direction = state.characterFilters.direction === "asc" ? "desc" : "asc";
  renderCharacters();
});

partyFilterClass.addEventListener("change", () => {
  state.partyFilters.classId = partyFilterClass.value;
  renderParties();
});

partyFilterLevel.addEventListener("change", () => {
  state.partyFilters.level = partyFilterLevel.value;
  renderParties();
});

partySort.addEventListener("change", () => {
  state.partyFilters.sort = partySort.value;
  renderParties();
});

partySortDirection.addEventListener("click", () => {
  state.partyFilters.direction = state.partyFilters.direction === "asc" ? "desc" : "asc";
  renderParties();
});

startSession.addEventListener("click", async () => {
  try {
    const party_id = partySelect.value;
    const adventure_id = adventureSelect.value || "random";
    if (!party_id) {
      setStatus("Create a party first");
      return;
    }
    state.session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ party_id, adventure_id }),
    });
    writeActiveSessionId(state.session.id);
    await refreshSessions();
    setStatus("Session started");
    renderSession();
  } catch (error) {
    handleError(error);
  }
});

resumeSessionBtn.addEventListener("click", () => {
  if (state.session) renderSession();
});

showSetupBtn.addEventListener("click", () => {
  showSetupView();
});

showRollsInput.addEventListener("change", () => {
  state.showRolls = showRollsInput.checked;
});

showMathInput.addEventListener("change", () => {
  state.showMath = showMathInput.checked;
});

mapZoomOut.addEventListener("click", () => setMapZoom(state.mapZoom - 0.1, { recenter: true }));
mapZoomIn.addEventListener("click", () => setMapZoom(state.mapZoom + 0.1, { recenter: true }));
mapZoomReset.addEventListener("click", () => setMapZoom(1, { recenter: true }));
mapCenterCurrent.addEventListener("click", centerCurrentTile);
mapPanUp.addEventListener("click", () => panMap(0, -160));
mapPanDown.addEventListener("click", () => panMap(0, 160));
mapPanLeft.addEventListener("click", () => panMap(-160, 0));
mapPanRight.addEventListener("click", () => panMap(160, 0));
mapEl.addEventListener("wheel", handleMapWheel, { passive: false });
mapEl.addEventListener("pointerdown", startMapPan);

async function advance(action, extra = {}) {
  if (!state.session) return;
  try {
    state.session = await api(`/api/sessions/${state.session.id}/advance`, {
      method: "POST",
      body: JSON.stringify({
        action,
        show_rolls: state.showRolls,
        explain_math: state.showMath,
        ...extra,
      }),
    });
    writeActiveSessionId(state.session.id);
    await refreshSessions();
    setStatus("Session updated");
    renderSession();
  } catch (error) {
    handleError(error);
  }
}

searchBtn.addEventListener("click", () => advance("search"));
combatBtn.addEventListener("click", () => advance("combat_round"));
restBtn.addEventListener("click", () => advance("rest"));
saveSessionBtn.addEventListener("click", async () => {
  if (!state.session) return;
  try {
    state.session = await api(`/api/sessions/${state.session.id}/save`, { method: "POST" });
    writeActiveSessionId(state.session.id);
    await refreshSessions();
    renderSession();
    setStatus("Game saved to server");
  } catch (error) {
    handleError(error);
  }
});

loadAll();
