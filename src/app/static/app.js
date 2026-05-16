const state = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  session: null,
  selectedCharacterId: null,
  selectedPartyId: null,
  editingPartyId: null,
};

const apiStatus = document.getElementById("api-status");
const characterClass = document.getElementById("character-class");
const characterForm = document.getElementById("character-form");
const characterName = document.getElementById("character-name");
const characterCount = document.getElementById("character-count");
const charactersEl = document.getElementById("characters");
const partyForm = document.getElementById("party-form");
const partyName = document.getElementById("party-name");
const partyPicks = document.getElementById("party-picks");
const saveParty = document.getElementById("save-party");
const cancelPartyEdit = document.getElementById("cancel-party-edit");
const partiesEl = document.getElementById("parties");
const partySelect = document.getElementById("party-select");
const adventureSelect = document.getElementById("adventure-select");
const adventuresEl = document.getElementById("adventures");
const startSession = document.getElementById("start-session");
const sessionPanel = document.getElementById("session-panel");
const sessionMode = document.getElementById("session-mode");
const mapEl = document.getElementById("map");
const tileDetail = document.getElementById("tile-detail");
const exitActions = document.getElementById("exit-actions");
const partyState = document.getElementById("party-state");
const sessionLog = document.getElementById("session-log");
const searchBtn = document.getElementById("search");
const combatBtn = document.getElementById("combat-round");
const restBtn = document.getElementById("rest");

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
    const [classes, characters, parties, adventures] = await Promise.all([
      api("/api/rules/classes"),
      api("/api/characters"),
      api("/api/parties"),
      api("/api/adventures"),
    ]);
    state.classes = classes;
    state.characters = characters;
    state.parties = parties;
    state.adventures = adventures;
    apiStatus.textContent = "Connected";
    renderSetup();
  } catch (error) {
    apiStatus.textContent = error.message;
  }
}

function renderSetup() {
  renderClasses();
  renderCharacters();
  renderParties();
  renderAdventures();
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

function renderCharacters() {
  const checkedIds = state.editingPartyId
    ? currentPartyEditIds()
    : Array.from(partyPicks.querySelectorAll("input:checked")).map((input) => input.value);
  characterCount.textContent = `${state.characters.length} saved`;
  charactersEl.replaceChildren();
  partyPicks.replaceChildren();

  for (const character of state.characters) {
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

    const pick = node("label", "pick");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = character.id;
    checkbox.checked = checkedIds.includes(character.id);
    pick.appendChild(checkbox);
    const labelText = node("span");
    labelText.appendChild(node("strong", "", character.name));
    labelText.appendChild(subline(character.class_name));
    pick.appendChild(labelText);
    partyPicks.appendChild(pick);
  }
}

function renderParties() {
  partiesEl.replaceChildren();
  partySelect.replaceChildren();
  for (const party of state.parties) {
    const item = node("div", "item selectable-item");
    item.tabIndex = 0;
    if (party.id === state.selectedPartyId) item.classList.add("selected");
    item.appendChild(node("strong", "", party.name));
    item.appendChild(subline(`${party.character_ids.length} members`));
    if (party.id === state.selectedPartyId) {
      const names = party.character_ids.map((id) => characterNameById(id)).join(", ");
      item.appendChild(subline(names || "No members"));
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

    const option = document.createElement("option");
    option.value = party.id;
    option.textContent = party.name;
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

function renderSession() {
  const session = state.session;
  if (!session) return;
  sessionPanel.classList.remove("hidden");
  sessionMode.textContent = session.mode;
  renderMap(session);
  renderTileDetail(session);
  renderExitActions(session);
  renderPartyState(session);
  renderLog(session);
  searchBtn.disabled = session.mode !== "exploration";
  restBtn.disabled = session.mode !== "exploration";
  combatBtn.disabled = session.mode !== "combat";
}

function renderMap(session) {
  mapEl.replaceChildren();
  const tiles = session.map_state.tiles;
  const minX = Math.min(...tiles.map((tile) => tile.x));
  const maxX = Math.max(...tiles.map((tile) => tile.x + rotatedWidth(tile) - 1));
  const minY = Math.min(...tiles.map((tile) => tile.y));
  const maxY = Math.max(...tiles.map((tile) => tile.y + rotatedHeight(tile) - 1));
  const cell = 116;
  const pad = 1;
  mapEl.style.minWidth = `${(maxX - minX + pad * 2 + 1) * cell}px`;
  mapEl.style.minHeight = `${(maxY - minY + pad * 2 + 1) * cell}px`;

  for (const tile of tiles) {
    const el = node("button", `placed-tile ${tile.tile_type}`);
    if (tile.id === session.map_state.current_tile_id) el.classList.add("current");
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
    mapEl.appendChild(el);
  }
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
  overlay.style.gridTemplateColumns = `repeat(${width}, minmax(0, 1fr))`;
  overlay.style.gridTemplateRows = `repeat(${height}, minmax(0, 1fr))`;
  const walkable = normalizedWalkable(tile, width, height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      overlay.appendChild(node("span", `map-square ${walkable[y]?.[x] === "0" ? "blocked" : "walkable"} shape-${cellShape(tile, x, y)}`));
    }
  }
  for (const exit of tile.exits || []) {
    overlay.appendChild(mapExitMarker(tile, exit, width, height));
  }
  return overlay;
}

function mapExitMarker(tile, exit, width, height) {
  const marker = node("span", `map-exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""} ${exit.direction}`);
  marker.title = exitDisplayLabel(exit);
  const cellW = 100 / width;
  const cellH = 100 / height;
  const x = Math.max(0, Math.min(exit.x || 0, width - 1));
  const y = Math.max(0, Math.min(exit.y || 0, height - 1));
  if (exit.direction === "north" || exit.direction === "south") {
    marker.style.left = `${x * cellW + cellW * 0.5}%`;
    marker.style.top = `${y * cellH + (exit.direction === "north" ? 0 : cellH)}%`;
    marker.style.width = `${cellW * 0.6}%`;
  } else {
    marker.style.left = `${x * cellW + (exit.direction === "west" ? 0 : cellW)}%`;
    marker.style.top = `${y * cellH + cellH * 0.5}%`;
    marker.style.height = `${cellH * 0.6}%`;
  }
  return marker;
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
  const offsetX = (tile.image_offset_x || 0) * offsetScale;
  const offsetY = (tile.image_offset_y || 0) * offsetScale;
  const scale = tile.image_scale || 1;
  return `translate(calc(-50% + ${offsetX}px), calc(-50% + ${offsetY}px)) rotate(${tile.rotation || 0}deg) scale(${scale})`;
}

function rotatedWidth(tile) {
  return (tile.rotation || 0) % 180 === 0 ? tile.footprint_width || 1 : tile.footprint_height || 1;
}

function rotatedHeight(tile) {
  return (tile.rotation || 0) % 180 === 0 ? tile.footprint_height || 1 : tile.footprint_width || 1;
}

function currentTile(session) {
  return session.map_state.tiles.find((tile) => tile.id === session.map_state.current_tile_id);
}

function renderTileDetail(session) {
  const tile = currentTile(session);
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
        .map((exit) => `${exitDisplayLabel(exit)} ${exit.status}`)
        .join(", ")}`
    )
  );
  tileDetail.appendChild(info);
}

function renderExitActions(session) {
  const tile = currentTile(session);
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
    button.disabled = session.mode !== "exploration";
    button.textContent = exitButtonLabel(exit);
    button.addEventListener("click", () => advance("explore", { exit_id: exit.id, direction: exit.direction }));
    buttons.appendChild(button);
  }
  exitActions.appendChild(buttons);
}

function exitButtonLabel(exit) {
  const direction = exit.direction[0].toUpperCase() + exit.direction.slice(1);
  const kind = exit.kind[0].toUpperCase() + exit.kind.slice(1);
  const label = exit.label ? `${exit.label} (${direction})` : direction;
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

function exitDisplayLabel(exit) {
  if (exit.label) return exit.label;
  const direction = exit.direction[0].toUpperCase() + exit.direction.slice(1);
  if (exit.dungeon_exit) return `${direction} dungeon exit`;
  return `${direction} ${exit.kind}`;
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
    setStatus("Session started");
    renderSession();
  } catch (error) {
    handleError(error);
  }
});

async function advance(action, extra = {}) {
  if (!state.session) return;
  try {
    state.session = await api(`/api/sessions/${state.session.id}/advance`, {
      method: "POST",
      body: JSON.stringify({ action, ...extra }),
    });
    setStatus("Session updated");
    renderSession();
  } catch (error) {
    handleError(error);
  }
}

searchBtn.addEventListener("click", () => advance("search"));
combatBtn.addEventListener("click", () => advance("combat_round"));
restBtn.addEventListener("click", () => advance("rest"));

loadAll();
