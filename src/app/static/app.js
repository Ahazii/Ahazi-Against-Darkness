const state = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  session: null,
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
  characterCount.textContent = `${state.characters.length} saved`;
  charactersEl.replaceChildren();
  partyPicks.replaceChildren();

  for (const character of state.characters) {
    const item = node("div", "item");
    item.appendChild(node("strong", "", `${character.name} - ${character.class_name}`));
    item.appendChild(
      subline(
        `L${character.level} HP ${character.current_life}/${character.max_life} ATK +${character.attack_bonus} DEF +${character.defense_bonus} SAVE +${character.save_bonus}`
      )
    );
    item.appendChild(subline(`Gold ${character.gold} | XP ${character.xp}`));
    charactersEl.appendChild(item);

    const pick = node("label", "pick");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = character.id;
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
    const item = node("div", "item");
    item.appendChild(node("strong", "", party.name));
    item.appendChild(subline(`${party.character_ids.length} members`));
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
  const maxX = Math.max(...tiles.map((tile) => tile.x));
  const minY = Math.min(...tiles.map((tile) => tile.y));
  const maxY = Math.max(...tiles.map((tile) => tile.y));
  const cell = 28;
  const pad = 3;
  mapEl.style.minWidth = `${(maxX - minX + pad * 2 + 1) * cell}px`;
  mapEl.style.minHeight = `${(maxY - minY + pad * 2 + 1) * cell}px`;

  for (const tile of tiles) {
    const el = node("button", `tile ${tile.tile_type}`);
    if (tile.id === session.map_state.current_tile_id) el.classList.add("current");
    el.style.left = `${(tile.x - minX + pad) * cell}px`;
    el.style.top = `${(tile.y - minY + pad) * cell}px`;
    el.title = tile.title;
    el.textContent = tile.tile_key;
    mapEl.appendChild(el);
  }
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
    tileDetail.appendChild(image);
  } else {
    tileDetail.appendChild(node("div", "item", "No tile image available"));
  }

  const info = node("div");
  info.appendChild(node("h2", "", tile.title));
  info.appendChild(subline(`${tile.tile_type} | ${tile.content_key}`));
  info.appendChild(node("p", "", tile.description));
  info.appendChild(subline(`Objects: ${tile.objects.length ? tile.objects.join(", ") : "none"}`));
  info.appendChild(subline(`Enemies: ${tile.enemies.length ? tile.enemies.map((enemy) => `${enemy.name} ${enemy.life}/${enemy.max_life}`).join(", ") : "none"}`));
  info.appendChild(subline(`Exits: ${tile.exits.map((exit) => `${exit.direction} ${exit.kind} ${exit.status}`).join(", ")}`));
  tileDetail.appendChild(info);
}

function renderExitActions(session) {
  const tile = currentTile(session);
  exitActions.replaceChildren();

  const heading = node("h2", "", "Exits");
  exitActions.appendChild(heading);

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
    button.addEventListener("click", () => advance("explore", { direction: exit.direction }));
    buttons.appendChild(button);
  }
  exitActions.appendChild(buttons);
}

function exitButtonLabel(exit) {
  const direction = exit.direction[0].toUpperCase() + exit.direction.slice(1);
  const kind = exit.kind[0].toUpperCase() + exit.kind.slice(1);
  if (exit.status === "open" && exit.destination_tile_id) {
    return `Go ${direction}`;
  }
  if (exit.status === "open") {
    return `Follow ${direction} ${kind}`;
  }
  return `Explore ${direction} ${kind}`;
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
    await api("/api/parties", {
      method: "POST",
      body: JSON.stringify({
        name: partyName.value,
        character_ids,
      }),
    });
    partyName.value = "";
    partyPicks.querySelectorAll("input:checked").forEach((input) => {
      input.checked = false;
    });
    setStatus("Party saved");
    await loadAll();
  } catch (error) {
    handleError(error);
  }
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
