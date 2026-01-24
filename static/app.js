const characterList = document.getElementById("character-list");
const partyList = document.getElementById("party-list");
const partyCharacters = document.getElementById("party-characters");
const adventurePartySelect = document.getElementById("adventure-party");
const sessionView = document.getElementById("session-view");
const mapGrid = document.getElementById("map-grid");
const roomInfo = document.getElementById("room-info");
const partyInfo = document.getElementById("party-info");
const logBox = document.getElementById("log");
const exploreBtn = document.getElementById("explore-btn");
const combatBtn = document.getElementById("combat-btn");

let currentSession = null;

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

async function loadCharacters() {
  const characters = await api("/api/characters");
  characterList.innerHTML = "";
  partyCharacters.innerHTML = "";
  adventurePartySelect.innerHTML = "";
  characters.forEach((char) => {
    const li = document.createElement("li");
    li.textContent = `${char.name} (L${char.level} ${char.class_name})`;
    characterList.appendChild(li);

    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = char.id;
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(`${char.name} (${char.class_name})`));
    partyCharacters.appendChild(label);
  });
  const parties = await api("/api/parties");
  parties.forEach((party) => {
    const option = document.createElement("option");
    option.value = party.id;
    option.textContent = party.name;
    adventurePartySelect.appendChild(option);
  });
}

async function loadParties() {
  const parties = await api("/api/parties");
  partyList.innerHTML = "";
  parties.forEach((party) => {
    const li = document.createElement("li");
    li.textContent = `${party.name} (${party.character_ids.length} members)`;
    partyList.appendChild(li);
  });
}

function renderSession(session) {
  currentSession = session;
  sessionView.classList.remove("hidden");

  mapGrid.innerHTML = "";
  for (let y = 0; y < session.map_state.height; y += 1) {
    for (let x = 0; x < session.map_state.width; x += 1) {
      const cell = document.createElement("div");
      cell.classList.add("map-cell");
      const tile = session.map_state.tiles.find((t) => t.x === x && t.y === y);
      if (tile) {
        cell.classList.add(tile.tile_type);
        if (tile.id === session.map_state.current_tile_id) {
          cell.classList.add("current");
        }
      }
      mapGrid.appendChild(cell);
    }
  }

  const currentTile = session.map_state.tiles.find(
    (t) => t.id === session.map_state.current_tile_id
  );

  roomInfo.innerHTML = `
    <div><strong>Type:</strong> ${currentTile.tile_type}</div>
    <div><strong>Content:</strong> ${currentTile.content}</div>
    <div><strong>Objects:</strong> ${currentTile.objects.join(", ") || "None"}</div>
    <div><strong>Enemies:</strong> ${
      currentTile.enemies.length ? currentTile.enemies.map((e) => `${e.name} (L${e.level})`).join(", ") : "None"
    }</div>
  `;

  partyInfo.innerHTML = session.party_status
    .map(
      (pc) =>
        `<div>${pc.name} - ${pc.class_name} (L${pc.level}) ${pc.current_life}/${pc.max_life}</div>`
    )
    .join("");

  logBox.innerHTML = session.log.map((entry) => `<div>${entry}</div>`).join("");

  exploreBtn.disabled = session.mode !== "exploration";
  combatBtn.disabled = session.mode !== "combat";
}

document.getElementById("character-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = document.getElementById("char-name").value;
  const className = document.getElementById("char-class").value;
  const level = parseInt(document.getElementById("char-level").value, 10);
  await api("/api/characters", {
    method: "POST",
    body: JSON.stringify({ name, class_name: className, level }),
  });
  event.target.reset();
  await loadCharacters();
  await loadParties();
});

document.getElementById("party-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = document.getElementById("party-name").value;
  const characterIds = Array.from(
    partyCharacters.querySelectorAll("input[type='checkbox']:checked")
  ).map((input) => input.value);
  await api("/api/parties", {
    method: "POST",
    body: JSON.stringify({ name, character_ids: characterIds }),
  });
  event.target.reset();
  await loadCharacters();
  await loadParties();
});

document.getElementById("start-random").addEventListener("click", async () => {
  const partyId = adventurePartySelect.value;
  if (!partyId) {
    alert("Create a party first.");
    return;
  }
  const session = await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ party_id: partyId, adventure_type: "random" }),
  });
  renderSession(session);
});

exploreBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  const session = await api(`/api/sessions/${currentSession.id}/advance`, {
    method: "POST",
    body: JSON.stringify({ action: "explore" }),
  });
  renderSession(session);
});

combatBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  const session = await api(`/api/sessions/${currentSession.id}/advance`, {
    method: "POST",
    body: JSON.stringify({ action: "combat_round" }),
  });
  renderSession(session);
});

loadCharacters();
loadParties();
