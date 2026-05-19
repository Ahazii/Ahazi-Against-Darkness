const state = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  rulesTables: {},
  icons: [],
  sessions: [],
  session: null,
  selectedCharacterId: null,
  selectedPartyId: null,
  editingPartyId: null,
  partyMarchingIds: [],
  characterFilters: { classId: "all", level: "all", sort: "name", direction: "asc" },
  partyFilters: { classId: "all", level: "all", sort: "name", direction: "asc" },
  showRolls: true,
  showMath: false,
  mapZoom: 1,
  lastCenteredTileId: null,
};

const ACTIVE_SESSION_KEY = "ahazi-against-darkness.active-session-id";
const ACTIVE_VIEW_KEY = "ahazi-against-darkness.active-view";
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
const partyMarchingOrderEl = document.getElementById("party-marching-order");
const partyMarchingListEl = document.getElementById("party-marching-list");
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
const rulesTablesEl = document.getElementById("rules-tables");
const exportPlayerDataBtn = document.getElementById("export-player-data");
const importPlayerDataBtn = document.getElementById("import-player-data");
const importPlayerFile = document.getElementById("import-player-file");
const setupPanel = document.getElementById("setup-panel");
const saveCount = document.getElementById("save-count");
const savedGamesEl = document.getElementById("saved-games");
const startSession = document.getElementById("start-session");
const resumeSessionBtn = document.getElementById("resume-session");
const sessionPanel = document.getElementById("session-panel");
const showSetupBtn = document.getElementById("show-setup");
const sessionMode = document.getElementById("session-mode");
const mapViewportEl = document.getElementById("map-viewport");
const mapEl = document.getElementById("map");
const MAP_BASE_CELL = 116;
const MAP_MIN_ZOOM = 0.08;
const MAP_MAX_ZOOM = 2.5;
const iconKey = document.getElementById("icon-key");
const mapZoomOut = document.getElementById("map-zoom-out");
const mapZoomIn = document.getElementById("map-zoom-in");
const mapZoomReset = document.getElementById("map-zoom-reset");
const mapZoomRoom = document.getElementById("map-zoom-room");
const mapZoomMap = document.getElementById("map-zoom-map");
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
const searchChoicesEl = document.getElementById("search-choices");
const searchTreasureBtn = document.getElementById("search-treasure");
const searchDoorBtn = document.getElementById("search-door");
const searchPassageBtn = document.getElementById("search-passage");
const searchClueBtn = document.getElementById("search-clue");
const reactionChoicesEl = document.getElementById("reaction-choices");
const checkReactionBtn = document.getElementById("check-reaction");
const payBribeBtn = document.getElementById("pay-bribe");
const declineBribeBtn = document.getElementById("decline-bribe");
const spellChoicesEl = document.getElementById("spell-choices");
const combatBtn = document.getElementById("combat-round");
const fleeBtn = document.getElementById("flee");
const withdrawBtn = document.getElementById("withdraw");
const resolveTrapBtn = document.getElementById("resolve-trap");
const claimTreasureBtn = document.getElementById("claim-treasure");
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

async function loadAll(options = {}) {
  const { restoreSession = true } = options;
  try {
    const requestedView = readRequestedView();
    if (requestedView === "setup" || requestedView === "game") {
      writeActiveView(requestedView);
      clearRequestedView();
    }
    const preferredView = requestedView || readActiveView();
    const [classes, characters, parties, adventures, rulesTables, icons, sessions] = await Promise.all([
      api("/api/rules/classes"),
      api("/api/characters"),
      api("/api/parties"),
      api("/api/adventures"),
      api("/api/rules/tables"),
      api("/api/rules/icons"),
      api("/api/sessions"),
    ]);
    state.classes = classes;
    state.characters = characters;
    state.parties = parties;
    state.adventures = adventures;
    state.rulesTables = rulesTables;
    state.icons = icons;
    state.sessions = sessions;
    apiStatus.textContent = "Connected";
    renderSetup({ rememberView: preferredView !== "game" });
    if (restoreSession && preferredView === "game") await restoreActiveSession();
  } catch (error) {
    apiStatus.textContent = error.message;
  }
}

function renderSetup(options = {}) {
  const { rememberView = true } = options;
  showSetupView({ rememberView });
  renderClasses();
  renderCharacters();
  renderParties();
  renderAdventures();
  renderSavedGames();
  renderRulesTables();
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
      const heal = node("button", "secondary", "Heal");
      heal.type = "button";
      heal.disabled = character.current_life >= character.max_life;
      heal.addEventListener("click", async (event) => {
        event.stopPropagation();
        await healCharacter(character.id);
      });
      const remove = node("button", "danger-button", "Delete");
      remove.type = "button";
      remove.addEventListener("click", async (event) => {
        event.stopPropagation();
        await deleteCharacter(character.id);
      });
      actions.append(heal, remove);
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
    checkbox.checked = state.partyMarchingIds.includes(character.id);
    checkbox.addEventListener("change", () => {
      togglePartyMember(character.id, checkbox.checked, checkbox);
      renderPartyMarchingOrder();
    });
    pick.appendChild(checkbox);
    const labelText = node("span");
    labelText.appendChild(node("strong", "", character.name));
    labelText.appendChild(subline(`${character.class_name} | L${character.level} | Gold ${character.gold}`));
    pick.appendChild(labelText);
    partyPicks.appendChild(pick);
  }
  renderPartyMarchingOrder();
}

function togglePartyMember(characterId, checked, checkbox) {
  if (checked) {
    if (state.partyMarchingIds.includes(characterId)) return;
    if (state.partyMarchingIds.length >= 4) {
      checkbox.checked = false;
      setStatus("Party is full. Uncheck a hero before adding another.");
      return;
    }
    state.partyMarchingIds.push(characterId);
    return;
  }
  state.partyMarchingIds = state.partyMarchingIds.filter((id) => id !== characterId);
}

function movePartyMarchingId(characterId, direction) {
  const index = state.partyMarchingIds.indexOf(characterId);
  if (index < 0) return;
  const targetIndex = direction === "up" ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= state.partyMarchingIds.length) return;
  const ids = [...state.partyMarchingIds];
  [ids[index], ids[targetIndex]] = [ids[targetIndex], ids[index]];
  state.partyMarchingIds = ids;
  renderPartyMarchingOrder();
}

function renderPartyMarchingOrder() {
  if (!partyMarchingOrderEl || !partyMarchingListEl) return;
  partyMarchingListEl.replaceChildren();
  if (!state.partyMarchingIds.length) {
    partyMarchingOrderEl.classList.add("hidden");
    return;
  }
  partyMarchingOrderEl.classList.remove("hidden");
  state.partyMarchingIds.forEach((characterId, index) => {
    const row = node("div", "marching-order-row");
    row.appendChild(node("span", "position", `#${index + 1}`));
    row.appendChild(node("span", "name", characterNameById(characterId)));
    const actions = node("div", "marching-order-actions");
    const up = node("button", "secondary", "↑");
    up.type = "button";
    up.disabled = index === 0;
    up.addEventListener("click", () => movePartyMarchingId(characterId, "up"));
    const down = node("button", "secondary", "↓");
    down.type = "button";
    down.disabled = index === state.partyMarchingIds.length - 1;
    down.addEventListener("click", () => movePartyMarchingId(characterId, "down"));
    actions.append(up, down);
    row.appendChild(actions);
    partyMarchingListEl.appendChild(row);
  });
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
      party.character_ids.forEach((characterId, index) => {
        item.appendChild(subline(`#${index + 1} ${characterNameById(characterId)}`));
      });
      const actions = node("div", "item-actions");
      const heal = node("button", "secondary", "Heal Party");
      heal.type = "button";
      heal.disabled = !stats.members.some((member) => member.current_life < member.max_life);
      heal.addEventListener("click", async (event) => {
        event.stopPropagation();
        await healParty(party.id);
      });
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
      actions.append(heal, edit, remove);
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

const RULES_TABLE_META_KEYS = new Set(["ruleset_status", "open_items", "validation"]);
const RULES_TABLE_ORDER = [
  "door_table",
  "trap_table",
  "treasure_table",
  "hidden_treasure_table",
  "search_table",
  "room_content_table",
  "wandering_monsters_table",
  "special_event_wandering_table",
  "dungeon_special_events_table",
  "dungeon_special_features_table",
  "dungeon_magic_treasure_table",
  "default_reaction_table",
  "vermin_reaction_table",
  "minion_reaction_table",
  "major_reaction_table",
  "basic_spells_table",
  "combat_notes",
];

function renderRulesTables() {
  rulesTablesEl.replaceChildren();
  const tables = state.rulesTables || {};
  const orderedKeys = [
    ...RULES_TABLE_ORDER.filter((key) => tables[key] != null),
    ...Object.keys(tables).filter((key) => !RULES_TABLE_META_KEYS.has(key) && !RULES_TABLE_ORDER.includes(key)),
  ];
  if (!orderedKeys.length) {
    rulesTablesEl.appendChild(node("div", "item", "No structured tables loaded."));
    return;
  }
  if (tables.ruleset_status) {
    rulesTablesEl.appendChild(node("div", "item muted", tables.ruleset_status));
  }
  for (const key of orderedKeys) {
    const value = tables[key];
    const detail = document.createElement("details");
    detail.className = "rules-table-card";
    detail.open = key === "door_table" || key === "search_table";
    const summary = document.createElement("summary");
    summary.textContent = titleFromKey(key);
    detail.appendChild(summary);
    if (Array.isArray(value) && value.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      detail.appendChild(renderObjectTable(flattenRulesRows(value)));
    } else if (Array.isArray(value)) {
      const list = node("div", "list compact");
      value.forEach((item) => list.appendChild(node("div", "item", String(item))));
      detail.appendChild(list);
    } else {
      detail.appendChild(node("div", "item", String(value)));
    }
    rulesTablesEl.appendChild(detail);
  }
}

function flattenRulesRows(rows) {
  return rows.map((row) => {
    const flat = { ...row };
    for (const key of ["any", "corridor", "room"]) {
      if (!flat[key] || typeof flat[key] !== "object") continue;
      const payload = flat[key];
      flat.result = flat.result || payload.description || payload.key || flat.result;
      flat.content_key = payload.key;
      flat.enemy_category = payload.enemy_category;
      flat.objects = Array.isArray(payload.objects) ? payload.objects.join(", ") : payload.objects;
      delete flat[key];
    }
    return flat;
  });
}

function formatRulesCell(value) {
  if (value == null) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function renderObjectTable(rows) {
  const table = document.createElement("table");
  table.className = "rules-data-table";
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((column) => headRow.appendChild(node("th", "", titleFromKey(column))));
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => tr.appendChild(node("td", "", formatRulesCell(row[column]))));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
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
    writeActiveView("setup");
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
    if (readActiveSessionId() === sessionId) clearActiveSessionId();
    if (state.session?.id === sessionId) {
      state.session = null;
      showSetupView();
      saveSessionBtn.disabled = true;
      saveSessionBtn.classList.add("hidden");
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

function readActiveView() {
  try {
    if (window.localStorage) return window.localStorage.getItem(ACTIVE_VIEW_KEY) || "setup";
  } catch {
    // Default to setup if browser storage is blocked.
  }
  return "setup";
}

function readRequestedView() {
  const value = new URLSearchParams(window.location.search).get("view");
  return value === "game" || value === "setup" ? value : "";
}

function clearRequestedView() {
  const url = new URL(window.location.href);
  if (!url.searchParams.has("view")) return;
  url.searchParams.delete("view");
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

function writeActiveView(view) {
  try {
    if (window.localStorage) window.localStorage.setItem(ACTIVE_VIEW_KEY, view);
  } catch {
    // View persistence is optional.
  }
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
  renderIconKey();
  renderExitActions(session);
  renderPartyState(session);
  renderLog(session);
  const tile = currentTile(session);
  const hasTrap = Boolean(tile.trap_key && !tile.trap_resolved);
  const hasTreasure =
    !tile.treasure_claimed && (Boolean(tile.treasure_gold) || (tile.treasure_items || []).length > 0);
  const canSearch = session.mode === "exploration" && !tile.searched;
  searchBtn.disabled = !canSearch;
  if (searchChoicesEl) searchChoicesEl.classList.toggle("hidden", !canSearch);
  if (searchTreasureBtn) searchTreasureBtn.disabled = !canSearch;
  if (searchDoorBtn) searchDoorBtn.disabled = !canSearch;
  if (searchPassageBtn) searchPassageBtn.disabled = !canSearch;
  if (searchClueBtn) searchClueBtn.disabled = !canSearch;
  restBtn.disabled = session.mode !== "exploration";
  const inCombat = session.mode === "combat";
  const canCheckReaction = inCombat && session.reaction_pending && !session.reaction_checked;
  const bribeOutstanding = inCombat && session.reaction_key === "bribe";
  if (reactionChoicesEl) reactionChoicesEl.classList.toggle("hidden", !inCombat);
  if (checkReactionBtn) checkReactionBtn.disabled = !canCheckReaction;
  if (payBribeBtn) {
    payBribeBtn.classList.toggle("hidden", !bribeOutstanding);
    payBribeBtn.disabled = !bribeOutstanding;
    if (bribeOutstanding) {
      payBribeBtn.textContent = `Pay Bribe (${session.reaction_bribe_gold || 0}gp)`;
    }
  }
  if (declineBribeBtn) {
    declineBribeBtn.classList.toggle("hidden", !bribeOutstanding);
    declineBribeBtn.disabled = !bribeOutstanding;
  }
  renderSpellChoices(session);
  combatBtn.disabled = !inCombat;
  if (fleeBtn) fleeBtn.disabled = !inCombat;
  const withdrawDoors =
    session.mode === "combat"
      ? (tile.exits || []).filter((exit) => exit.kind === "door" && exit.destination_tile_id)
      : [];
  if (withdrawBtn) withdrawBtn.disabled = session.mode !== "combat" || !withdrawDoors.length;
  resolveTrapBtn.disabled = session.mode !== "exploration" || !hasTrap;
  claimTreasureBtn.disabled = session.mode !== "exploration" || !hasTreasure || hasTrap;
  saveSessionBtn.disabled = false;
}

function renderSpellChoices(session) {
  if (!spellChoicesEl) return;
  spellChoicesEl.replaceChildren();
  if (session.mode !== "combat") {
    spellChoicesEl.classList.add("hidden");
    return;
  }
  const living = (session.party || []).filter((member) => member.current_life > 0);
  const entries = [];
  for (const member of living) {
    for (const spell of member.spells || []) {
      entries.push({ member, spell });
    }
  }
  if (!entries.length) {
    spellChoicesEl.classList.add("hidden");
    return;
  }
  spellChoicesEl.classList.remove("hidden");
  spellChoicesEl.appendChild(node("span", "search-label", "Cast spell:"));
  for (const { member, spell } of entries) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = `${member.name}: ${spell}`;
    button.addEventListener("click", () =>
      advance("cast_spell", { character_id: member.character_id, spell_name: spell })
    );
    spellChoicesEl.appendChild(button);
  }
}

function renderMap(session) {
  mapEl.replaceChildren();
  const tiles = session.map_state.tiles;
  const bounds = mapBounds(session);
  const boundsWidth = bounds.maxX - bounds.minX + 3;
  const boundsHeight = bounds.maxY - bounds.minY + 3;
  const cell = Math.round(MAP_BASE_CELL * state.mapZoom);
  const pad = 1;
  let currentTileEl = null;
  mapEl.style.setProperty("--cell", `${cell}px`);
  mapEl.style.minWidth = `${boundsWidth * cell}px`;
  mapEl.style.minHeight = `${boundsHeight * cell}px`;
  mapZoomLabel.textContent = `${Math.round(state.mapZoom * 100)}%`;

  for (const tile of tiles) {
    const el = node("div", `placed-tile ${tile.tile_type}`);
    if (tile.id === session.map_state.current_tile_id) {
      el.classList.add("current");
      currentTileEl = el;
    }
    const width = rotatedWidth(tile);
    const height = rotatedHeight(tile);
    el.style.left = `${(tile.x - bounds.minX + pad) * cell}px`;
    el.style.top = `${(tile.y - bounds.minY + pad) * cell}px`;
    el.style.width = `${width * cell}px`;
    el.style.height = `${height * cell}px`;
    el.title = tile.title;

    if (tile.image) el.appendChild(mapImageLayer(tile, cell, width, height));
    el.appendChild(tileOverlay(tile, session));
    const key = node("span", "tile-key", tile.tile_key);
    el.appendChild(key);
    if (tile.id === session.map_state.current_tile_id) {
      const marker = node("span", "current-party-marker", "Current Party");
      positionInVisibleBounds(marker, tile, width, height);
      el.appendChild(marker);
    }
    mapEl.appendChild(el);
  }
  if (currentTileEl && state.lastCenteredTileId !== session.map_state.current_tile_id) {
    state.lastCenteredTileId = session.map_state.current_tile_id;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => centerMapOn(currentTileEl));
    });
  }
}

function mapViewportSize() {
  return {
    width: mapViewportEl.clientWidth,
    height: mapViewportEl.clientHeight,
  };
}

function mapImageLayer(tile, cell, width, height) {
  const visible = normalizedVisible(tile, width, height);
  const clipped = visible.some((row) => row.includes("0"));
  if (!clipped) return mapImageElement(tile, cell, { className: "map-image-full" });

  const layer = node("div", "map-image-clipped");
  const tileWidth = width * cell;
  const tileHeight = height * cell;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (visible[y]?.[x] === "0") continue;
      const clip = node("span", "map-image-clip-cell");
      clip.style.left = `${x * cell}px`;
      clip.style.top = `${y * cell}px`;
      clip.style.width = `${cell}px`;
      clip.style.height = `${cell}px`;
      const image = mapImageElement(tile, cell, { className: "map-image-cell-image", decorative: true });
      image.style.left = `${tileWidth / 2 - x * cell}px`;
      image.style.top = `${tileHeight / 2 - y * cell}px`;
      clip.appendChild(image);
      layer.appendChild(clip);
    }
  }
  return layer;
}

function mapImageElement(tile, cell, { className, decorative = false }) {
  const image = document.createElement("img");
  image.className = className;
  image.src = tile.image;
  image.alt = decorative ? "" : tile.title;
  if (decorative) image.setAttribute("aria-hidden", "true");
  image.style.width = `${(tile.footprint_width || 1) * cell}px`;
  image.style.height = `${(tile.footprint_height || 1) * cell}px`;
  image.style.transform = mapImageTransform(tile, cell);
  return image;
}

function mapBounds(session) {
  const tiles = session.map_state.tiles;
  return {
    minX: Math.min(...tiles.map((tile) => tile.x)),
    maxX: Math.max(...tiles.map((tile) => tile.x + rotatedWidth(tile) - 1)),
    minY: Math.min(...tiles.map((tile) => tile.y)),
    maxY: Math.max(...tiles.map((tile) => tile.y + rotatedHeight(tile) - 1)),
  };
}

function setMapZoom(nextZoom, { recenter = false } = {}) {
  state.mapZoom = clampFloat(nextZoom, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  if (recenter) state.lastCenteredTileId = null;
  if (state.session) renderMap(state.session);
}

function zoomToCurrentRoom() {
  const tile = currentTile(state.session);
  const viewport = mapViewportSize();
  if (!tile || !viewport.width || !viewport.height) return;
  const target = Math.min(
    (viewport.width * 0.62) / (rotatedWidth(tile) * MAP_BASE_CELL),
    (viewport.height * 0.62) / (rotatedHeight(tile) * MAP_BASE_CELL),
    MAP_MAX_ZOOM
  );
  setMapZoom(target, { recenter: true });
}

function zoomToFullMap() {
  const viewport = mapViewportSize();
  if (!state.session || !viewport.width || !viewport.height) return;
  const bounds = mapBounds(state.session);
  const boundsWidth = bounds.maxX - bounds.minX + 3;
  const boundsHeight = bounds.maxY - bounds.minY + 3;
  const target = Math.min(
    (viewport.width - 24) / (boundsWidth * MAP_BASE_CELL),
    (viewport.height - 24) / (boundsHeight * MAP_BASE_CELL),
    1.2
  );
  state.mapZoom = clampFloat(target, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  if (state.session) renderMap(state.session);
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      mapViewportEl.scrollLeft = Math.max(0, (mapViewportEl.scrollWidth - mapViewportEl.clientWidth) / 2);
      mapViewportEl.scrollTop = Math.max(0, (mapViewportEl.scrollHeight - mapViewportEl.clientHeight) / 2);
    });
  });
}

function panMap(deltaX, deltaY) {
  mapViewportEl.scrollBy({ left: deltaX, top: deltaY, behavior: "smooth" });
}

function centerCurrentTile() {
  const current = mapEl.querySelector(".placed-tile.current");
  if (current) centerMapOn(current);
}

function centerMapOn(element) {
  const maxScrollLeft = Math.max(0, mapViewportEl.scrollWidth - mapViewportEl.clientWidth);
  const maxScrollTop = Math.max(0, mapViewportEl.scrollHeight - mapViewportEl.clientHeight);
  mapViewportEl.scrollLeft = clampFloat(
    element.offsetLeft + element.offsetWidth / 2 - mapViewportEl.clientWidth / 2,
    0,
    maxScrollLeft
  );
  mapViewportEl.scrollTop = clampFloat(
    element.offsetTop + element.offsetHeight / 2 - mapViewportEl.clientHeight / 2,
    0,
    maxScrollTop
  );
}

function handleMapWheel(event) {
  if (!event.ctrlKey) return;
  event.preventDefault();
  setMapZoom(state.mapZoom + (event.deltaY < 0 ? 0.1 : -0.1), { recenter: true });
}

function startMapPan(event) {
  if (event.button !== 0 && event.button !== 1) return;
  if (event.button === 0 && event.target.closest("button, a, input, label, select, textarea")) return;
  event.preventDefault();
  mapViewportEl.classList.add("panning");
  mapViewportEl.setPointerCapture(event.pointerId);
  const startX = event.clientX;
  const startY = event.clientY;
  const startScrollLeft = mapViewportEl.scrollLeft;
  const startScrollTop = mapViewportEl.scrollTop;

  const move = (moveEvent) => {
    mapViewportEl.scrollLeft = startScrollLeft - (moveEvent.clientX - startX);
    mapViewportEl.scrollTop = startScrollTop - (moveEvent.clientY - startY);
  };

  const stop = () => {
    mapViewportEl.classList.remove("panning");
    mapViewportEl.removeEventListener("pointermove", move);
    mapViewportEl.removeEventListener("pointerup", stop);
    mapViewportEl.removeEventListener("pointercancel", stop);
    if (mapViewportEl.hasPointerCapture(event.pointerId)) {
      mapViewportEl.releasePointerCapture(event.pointerId);
    }
  };

  mapViewportEl.addEventListener("pointermove", move);
  mapViewportEl.addEventListener("pointerup", stop);
  mapViewportEl.addEventListener("pointercancel", stop);
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
  state.partyMarchingIds = [...party.character_ids];
  partyName.value = party.name;
  saveParty.textContent = "Update Party";
  cancelPartyEdit.classList.remove("hidden");
  renderCharacters();
  renderParties();
}

function cancelPartyEditMode() {
  state.editingPartyId = null;
  state.partyMarchingIds = [];
  partyName.value = "";
  saveParty.textContent = "Save Party";
  cancelPartyEdit.classList.add("hidden");
  renderCharacters();
}

async function deleteCharacter(characterId) {
  try {
    await api(`/api/characters/${characterId}`, { method: "DELETE" });
    if (state.selectedCharacterId === characterId) state.selectedCharacterId = null;
    setStatus("Character deleted");
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
}

async function healCharacter(characterId) {
  try {
    await api(`/api/characters/${characterId}/heal`, { method: "POST" });
    setStatus("Character healed");
    await loadAll({ restoreSession: false });
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
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
}

async function healParty(partyId) {
  try {
    await api(`/api/parties/${partyId}/heal`, { method: "POST" });
    setStatus("Party healed");
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
}

async function exportPlayerData() {
  try {
    const payload = await api("/api/export/player-data");
    const stamp = new Date().toISOString().slice(0, 10);
    downloadJson(`ahazi-player-data-${stamp}.json`, payload);
    setStatus("Player data exported");
  } catch (error) {
    handleError(error);
  }
}

async function importPlayerData(file) {
  if (!file) return;
  try {
    const payload = await readJsonFile(file);
    const result = await api("/api/import/player-data", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setStatus(`Imported ${result.characters} characters and ${result.parties} parties`);
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  } finally {
    importPlayerFile.value = "";
  }
}

function tileOverlay(tile, session) {
  const overlay = node("div", "map-tile-overlay");
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const sideLabels = exitSideLabels(tile);
  const isCurrent = tile.id === session.map_state.current_tile_id;
  overlay.style.gridTemplateColumns = `repeat(${width}, minmax(0, 1fr))`;
  overlay.style.gridTemplateRows = `repeat(${height}, minmax(0, 1fr))`;
  const walkable = normalizedWalkable(tile, width, height);
  const visible = normalizedVisible(tile, width, height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const isHidden = visible[y]?.[x] === "0";
      let currentClass = "";
      if (isCurrent && !isHidden) {
        currentClass = isCurrentVisibleEdge(visible, x, y, width, height) ? "current-edge" : "current-interior";
      }
      overlay.appendChild(
        node(
          "span",
          `map-square ${walkable[y]?.[x] === "0" ? "blocked" : "walkable"} ${isHidden ? "hidden" : ""} ${currentClass} shape-${
            isHidden ? "F" : cellShape(tile, x, y)
          }`
        )
      );
    }
  }
  for (const exit of tile.exits || []) {
    overlay.appendChild(mapExitMarker(tile, exit, width, height, sideLabels.get(exit.id), session));
  }
  const contentMarkers = tileContentMarkers(tile, session, width, height);
  if (contentMarkers) overlay.appendChild(contentMarkers);
  return overlay;
}

function mapExitMarker(tile, exit, width, height, sideLabel, session) {
  const canUse = session.mode === "exploration" && tile.id === session.map_state.current_tile_id && exit.status !== "blocked";
  const onCurrentTile = tile.id === session.map_state.current_tile_id;
  const isClosedDoor = exit.kind === "door" && !exit.door_open;
  const doorStateClass = exit.kind === "door" ? (exit.door_open ? " open" : " closed") : "";
  const marker = node(
    canUse ? "button" : "span",
    `map-exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""}${exit.status === "blocked" ? " blocked" : ""}${doorStateClass} ${exit.direction}`
  );
  if (canUse) {
    marker.type = "button";
    marker.classList.add("clickable");
    marker.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (isClosedDoor) {
        advance("open_door", { exit_id: exit.id, character_id: leadMemberId(session) });
        return;
      }
      advance("explore", { exit_id: exit.id, direction: exit.direction });
    });
  }
  const label = exitDisplayLabel(exit, sideLabel);
  const doorHint = exit.kind === "door" ? (exit.door_open ? " - open" : " - closed") : "";
  marker.title = exit.status === "blocked" ? `${label} - dead end` : `${label}${doorHint}${exit.door_result ? ` (${exit.door_result})` : ""}`;
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
  marker.appendChild(node("span", "map-exit-marker-label", compactExitLabel(exit, sideLabel, onCurrentTile)));
  return marker;
}

function tileContentMarkers(tile, session, width, height) {
  const markers = [];
  const liveEnemies = (tile.enemies || []).filter((enemy) => enemy.life > 0);
  const defeatedEnemies = tile.defeated_enemies || [];
  const objects = tile.objects || [];
  const fallen = fallenMembersForTile(tile, session);
  if (liveEnemies.length) markers.push(contentMarker("monster", `${liveEnemies.length} active foe${liveEnemies.length === 1 ? "" : "s"}`, liveEnemies.length));
  if (defeatedEnemies.length) {
    markers.push(
      contentMarker(
        "defeated",
        `${defeatedEnemies.map((enemy) => enemy.name).join(", ")} defeated here`,
        defeatedEnemies.length
      )
    );
  }
  if (objects.some((item) => /treasure/i.test(item))) markers.push(contentMarker("treasure", "Treasure present"));
  if (objects.some((item) => /trap/i.test(item))) markers.push(contentMarker("trap", "Trap present"));
  if (fallen.length) markers.push(contentMarker("fallen", `${fallen.map((member) => member.name).join(", ")} fallen here`, fallen.length));
  if (!markers.length) return null;
  const wrap = node("div", "map-content-markers");
  positionContentMarkersInVisibleBounds(wrap, tile, width, height);
  wrap.append(...markers);
  return wrap;
}

function contentMarker(kind, title, count = 0) {
  const definition = iconDefinition(kind);
  const marker = node("span", `map-content-marker ${kind}`);
  marker.title = title;
  marker.setAttribute("aria-label", title);
  marker.appendChild(iconGraphic(definition, "map-content-icon", title));
  if (count > 1) marker.appendChild(node("span", "marker-count", String(count)));
  return marker;
}

function iconDefinition(iconId) {
  return (
    state.icons.find((icon) => icon.id === iconId) || {
      id: iconId,
      label: titleFromKey(iconId),
      description: "",
      file: "",
      fallback: iconId,
      attribution: "",
      license: "",
      source_url: "",
    }
  );
}

function iconGraphic(definition, className, title = "") {
  if (definition.file) {
    const image = document.createElement("img");
    image.className = `${className} icon-image`;
    image.src = assetUrl(definition.file);
    image.alt = definition.label;
    image.title = title || iconTitle(definition);
    return image;
  }
  const fallback = definition.fallback || definition.id;
  const icon =
    className === "map-content-icon"
      ? node("span", `${className} ${fallback}`)
      : node("span", className);
  if (className !== "map-content-icon") {
    icon.appendChild(node("span", `map-content-icon ${fallback}`));
  }
  icon.title = title || iconTitle(definition);
  icon.setAttribute("aria-label", icon.title);
  return icon;
}

function iconTitle(definition) {
  const parts = [definition.label, definition.description, definition.attribution].filter(Boolean);
  return parts.join(" - ");
}

function assetUrl(path) {
  const clean = String(path || "")
    .replace(/^\/?assets\//, "")
    .replace(/^\/+/, "");
  return `/assets/${clean}`;
}

function fallenMembersForTile(tile, session) {
  const ids = new Set(tile.fallen_character_ids || []);
  return (session.party || []).filter((member) => ids.has(member.character_id));
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

function normalizedVisible(tile, width, height) {
  const rows = Array.isArray(tile.visible) ? tile.visible : [];
  return Array.from({ length: height }, (_, y) => {
    const source = String(rows[y] || "");
    return Array.from({ length: width }, (__, x) => (source[x] === "0" ? "0" : "1")).join("");
  });
}

function isCurrentVisibleEdge(visible, x, y, width, height) {
  if (visible[y]?.[x] === "0") return false;
  for (const [nx, ny] of [
    [x - 1, y],
    [x + 1, y],
    [x, y - 1],
    [x, y + 1],
  ]) {
    if (nx < 0 || ny < 0 || nx >= width || ny >= height) return true;
    if (visible[ny]?.[nx] === "0") return true;
  }
  return false;
}

function visibleCellBounds(tile, width, height) {
  const visible = normalizedVisible(tile, width, height);
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (visible[y]?.[x] !== "0") {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }
  if (maxX < 0) return { minX: 0, minY: 0, maxX: width - 1, maxY: height - 1 };
  return { minX, minY, maxX, maxY };
}

function positionInVisibleBounds(element, tile, width, height) {
  const bounds = visibleCellBounds(tile, width, height);
  element.style.left = `${((bounds.minX + bounds.maxX + 1) / 2 / width) * 100}%`;
  element.style.top = `${((bounds.minY + bounds.maxY + 1) / 2 / height) * 100}%`;
}

function positionContentMarkersInVisibleBounds(element, tile, width, height) {
  const bounds = visibleCellBounds(tile, width, height);
  element.style.left = `${((bounds.minX + bounds.maxX + 1) / 2 / width) * 100}%`;
  element.style.top = `${((bounds.minY + bounds.maxY + 1) / 2 / height) * 100}%`;
  element.style.right = "";
  element.style.bottom = "";
  element.style.maxWidth = "";
  element.style.transform = "translate(-50%, -50%)";
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
  if ((tile.defeated_enemies || []).length) {
    info.appendChild(subline(`Defeated: ${tile.defeated_enemies.map((enemy) => enemy.name).join(", ")}`));
  }
  const fallen = fallenMembersForTile(tile, session);
  if (fallen.length) {
    info.appendChild(subline(`Fallen: ${fallen.map((member) => member.name).join(", ")}`));
  }
  if (tile.trap_key && !tile.trap_resolved) {
    info.appendChild(subline(`Trap: ${tile.trap_key} (L${tile.trap_level || "?"})`));
  }
  if ((tile.treasure_gold || (tile.treasure_items || []).length) && !tile.treasure_claimed) {
    info.appendChild(subline(`Treasure: ${tile.treasure_summary || "Unclaimed loot"}`));
  }
  info.appendChild(
    subline(
      `Exits: ${tile.exits
        .map((exit) => {
          const label = exitDisplayLabel(exit, sideLabels.get(exit.id));
          const doorState = exit.kind === "door" ? (exit.door_open ? " open" : " closed") : "";
          return `${label} ${exit.status}${doorState}`;
        })
        .join(", ")}`
    )
  );
  tileDetail.appendChild(info);
}

function renderIconKey() {
  iconKey.replaceChildren();
  const heading = node("h2", "", "Map Icon Key");
  iconKey.appendChild(heading);
  const list = node("div", "icon-key-list");
  for (const iconId of ["monster", "defeated", "treasure", "trap", "fallen", "door", "passage", "dungeon-exit"]) {
    const definition = iconDefinition(iconId);
    const row = node("div", "icon-key-row");
    row.title = iconTitle(definition);
    row.appendChild(iconGraphic(definition, "icon-key-symbol"));
    const text = node("div", "icon-key-text");
    text.appendChild(node("strong", "", definition.label));
    text.appendChild(subline(definition.description || "No description yet."));
    if (definition.attribution || definition.license) {
      text.appendChild(subline([definition.attribution, definition.license].filter(Boolean).join(" | ")));
    }
    if (definition.source_url) {
      const link = document.createElement("a");
      link.href = definition.source_url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = "Icon source";
      text.appendChild(link);
    }
    row.appendChild(text);
    list.appendChild(row);
  }
  iconKey.appendChild(list);
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
  const blocked = tile.exits.filter((exit) => exit.status === "blocked");

  if (session.mode === "combat") {
    const withdrawDoors = available.filter((exit) => exit.kind === "door" && exit.destination_tile_id);
    if (withdrawDoors.length) {
      buttons.appendChild(subline("Withdraw through a door:"));
      for (const exit of withdrawDoors) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "exit-button door withdraw-door secondary";
        button.textContent = `Withdraw ${exitDisplayLabel(exit, sideLabels.get(exit.id))}`;
        button.addEventListener("click", () => advance("withdraw", { exit_id: exit.id }));
        buttons.appendChild(button);
      }
    } else {
      buttons.appendChild(subline("No door leads back for a withdrawal."));
    }
    exitActions.appendChild(buttons);
    return;
  }

  if (!available.length) {
    buttons.appendChild(subline("No available exits."));
  }

  for (const exit of available) {
    const isClosedDoor = exit.kind === "door" && !exit.door_open;
    if (isClosedDoor) {
      const doorButton = document.createElement("button");
      doorButton.type = "button";
      doorButton.className = "exit-button door open-door";
      doorButton.disabled = session.mode !== "exploration";
      doorButton.textContent = `Open ${exitDisplayLabel(exit, sideLabels.get(exit.id))} (closed)`;
      doorButton.title = exit.door_result || "Attempt to open this door.";
      doorButton.addEventListener("click", () =>
        advance("open_door", { exit_id: exit.id, character_id: leadMemberId(session) })
      );
      buttons.appendChild(doorButton);
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = `exit-button ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""}`;
    button.disabled = session.mode !== "exploration" || isClosedDoor;
    button.textContent = exitButtonLabel(exit, sideLabels.get(exit.id));
    button.title = exitDisplayLabel(exit, sideLabels.get(exit.id));
    button.addEventListener("click", () => advance("explore", { exit_id: exit.id, direction: exit.direction }));
    buttons.appendChild(button);
  }
  exitActions.appendChild(buttons);
  if (blocked.length) {
    exitActions.appendChild(
      subline(`Dead ends: ${blocked.map((exit) => exitDisplayLabel(exit, sideLabels.get(exit.id))).join(", ")}`)
    );
  }
}

function exitButtonLabel(exit, sideLabel) {
  const kind = exit.kind[0].toUpperCase() + exit.kind.slice(1);
  const label = sideLabel || titleCase(exit.direction);
  const doorTag = exit.kind === "door" ? (exit.door_open ? " (open)" : " (closed)") : "";
  if (exit.dungeon_exit) {
    return `Leave Dungeon (${label})`;
  }
  if (exit.status === "open" && exit.destination_tile_id) {
    return `Go ${label}${doorTag}`;
  }
  if (exit.status === "open") {
    return `Follow ${label} ${kind}${doorTag}`;
  }
  return `Explore ${label} ${kind}${doorTag}`;
}

function exitDisplayLabel(exit, sideLabel) {
  const label = sideLabel || titleCase(exit.direction);
  if (exit.dungeon_exit) return `${label} dungeon exit`;
  return `${label} ${exit.kind}`;
}

function compactExitLabel(exit, sideLabel, onCurrentTile = false) {
  const label = sideLabel || titleCase(exit.direction);
  const compact = label
    .replace("North", "N")
    .replace("East", "E")
    .replace("South", "S")
    .replace("West", "W");
  if (exit.dungeon_exit) return `${compact}X`;
  if (exit.kind === "door" && onCurrentTile) {
    return `${compact}${exit.door_open ? "O" : "D"}`;
  }
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

function titleFromKey(value) {
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function leadMemberId(session) {
  const living = session.party.filter((member) => member.current_life > 0);
  if (!living.length) return null;
  return [...living].sort((left, right) => left.marching_order - right.marching_order)[0].character_id;
}

function renderPartyState(session) {
  partyState.replaceChildren();
  const ordered = [...session.party].sort((left, right) => left.marching_order - right.marching_order);
  const canReorder = session.mode === "exploration";
  for (const member of ordered) {
    const item = node("div", "item");
    const header = node("div", "marching-order-row");
    header.appendChild(node("span", "position", `#${member.marching_order}`));
    header.appendChild(node("span", "name", `${member.name} - ${member.class_name}`));
    if (canReorder && member.current_life > 0) {
      const actions = node("div", "marching-order-actions");
      const up = node("button", "secondary", "↑");
      up.type = "button";
      up.disabled = member.marching_order <= 1;
      up.addEventListener("click", () =>
        advance("set_marching_order", {
          character_id: member.character_id,
          marching_order: member.marching_order - 1,
        })
      );
      const down = node("button", "secondary", "↓");
      down.type = "button";
      down.disabled = member.marching_order >= 4;
      down.addEventListener("click", () =>
        advance("set_marching_order", {
          character_id: member.character_id,
          marching_order: member.marching_order + 1,
        })
      );
      actions.append(up, down);
      header.appendChild(actions);
    }
    item.appendChild(header);
    item.appendChild(subline(`HP ${member.current_life}/${member.max_life} | Gold ${member.gold} | XP ${member.xp}`));
    item.appendChild(subline(`Inventory: ${member.inventory.join(", ") || "none"}`));
    if ((member.spells || []).length) {
      item.appendChild(subline(`Spells: ${member.spells.join(", ")}`));
    }
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

function showGameView(options = {}) {
  const { rememberView = true } = options;
  setupPanel.classList.add("hidden");
  sessionPanel.classList.remove("hidden");
  showSetupBtn.classList.remove("hidden");
  saveSessionBtn.classList.remove("hidden");
  resumeSessionBtn.classList.toggle("hidden", !state.session);
  if (rememberView) writeActiveView("game");
}

function showSetupView(options = {}) {
  const { rememberView = true } = options;
  setupPanel.classList.remove("hidden");
  sessionPanel.classList.add("hidden");
  showSetupBtn.classList.add("hidden");
  saveSessionBtn.classList.add("hidden");
  resumeSessionBtn.classList.toggle("hidden", !state.session);
  if (rememberView) writeActiveView("setup");
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
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
});

partyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    if (state.partyMarchingIds.length !== 4) {
      setStatus("Choose exactly 4 heroes for the party.");
      return;
    }
    const character_ids = [...state.partyMarchingIds];
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
    await loadAll({ restoreSession: false });
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

exportPlayerDataBtn.addEventListener("click", exportPlayerData);
importPlayerDataBtn.addEventListener("click", () => importPlayerFile.click());
importPlayerFile.addEventListener("change", () => importPlayerData(importPlayerFile.files?.[0]));

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
mapZoomRoom.addEventListener("click", zoomToCurrentRoom);
mapZoomMap.addEventListener("click", zoomToFullMap);
mapCenterCurrent.addEventListener("click", centerCurrentTile);
mapPanUp.addEventListener("click", () => panMap(0, -160));
mapPanDown.addEventListener("click", () => panMap(0, 160));
mapPanLeft.addEventListener("click", () => panMap(-160, 0));
mapPanRight.addEventListener("click", () => panMap(160, 0));
mapViewportEl.addEventListener("wheel", handleMapWheel, { passive: false });
mapViewportEl.addEventListener("pointerdown", startMapPan);

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
searchTreasureBtn?.addEventListener("click", () => advance("search", { search_choice: "hidden_treasure" }));
searchDoorBtn?.addEventListener("click", () => advance("search", { search_choice: "secret_door" }));
searchPassageBtn?.addEventListener("click", () => advance("search", { search_choice: "secret_passage" }));
searchClueBtn?.addEventListener("click", () => advance("search", { search_choice: "clue" }));
checkReactionBtn?.addEventListener("click", () => advance("check_reaction"));
payBribeBtn?.addEventListener("click", () => advance("pay_bribe", { pay_bribe: true }));
declineBribeBtn?.addEventListener("click", () => advance("pay_bribe", { pay_bribe: false }));
combatBtn.addEventListener("click", () => advance("combat_round"));
fleeBtn?.addEventListener("click", () => advance("flee"));
withdrawBtn?.addEventListener("click", () => {
  const session = state.session;
  if (!session) return;
  const tile = currentTile(session);
  const door = (tile.exits || []).find((exit) => exit.kind === "door" && exit.destination_tile_id);
  if (door) advance("withdraw", { exit_id: door.id });
});
resolveTrapBtn.addEventListener("click", () => advance("resolve_trap"));
claimTreasureBtn.addEventListener("click", () => advance("claim_treasure"));
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
