const characterList = document.getElementById("character-list");
const partyList = document.getElementById("party-list");
const partyCharacters = document.getElementById("party-characters");
const adventurePartySelect = document.getElementById("adventure-party");
const adventureSelect = document.getElementById("adventure-select");
const sessionView = document.getElementById("session-view");
const mapGrid = document.getElementById("map-grid");
const roomInfo = document.getElementById("room-info");
const partyInfo = document.getElementById("party-info");
const roomDescription = document.getElementById("room-description");
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
}

async function loadParties() {
  const parties = await api("/api/parties");
  partyList.innerHTML = "";
  adventurePartySelect.innerHTML = "";
  parties.forEach((party) => {
    const li = document.createElement("li");
    li.textContent = `${party.name} (${party.character_ids.length} members)`;
    partyList.appendChild(li);
    const option = document.createElement("option");
    option.value = party.id;
    option.textContent = party.name;
    adventurePartySelect.appendChild(option);
  });
}

async function loadAdventures() {
  const adventures = await api("/api/adventures");
  adventureSelect.innerHTML = "";
  adventures.random.forEach((adventure) => {
    const option = document.createElement("option");
    option.value = adventure.id;
    option.textContent = `Random: ${adventure.name}`;
    adventureSelect.appendChild(option);
  });
  adventures.imported.forEach((adventure) => {
    const option = document.createElement("option");
    option.value = adventure.id;
    option.textContent = `Imported: ${adventure.name}`;
    adventureSelect.appendChild(option);
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

  const enemySummary = currentTile.enemies.length
    ? currentTile.enemies.map((e) => `${e.name} (L${e.level})`).join(", ")
    : "None";
  const objectSummary = currentTile.objects.length ? currentTile.objects.join(", ") : "None";
  const encounterText = currentTile.enemies.length ? "Enemies are present." : "No enemies in sight.";

  roomDescription.innerHTML = `
    <div><strong>Location:</strong> ${currentTile.content}</div>
    <div>${currentTile.tile_type === "room" ? "A room opens up around you." : "A narrow corridor stretches ahead."}</div>
    <div><strong>Encounter:</strong> ${encounterText}</div>
  `;

  roomInfo.innerHTML = `
    <div><strong>Tile type:</strong> ${currentTile.tile_type}</div>
    <div><strong>Objects:</strong> ${objectSummary}</div>
    <div><strong>Enemies:</strong> ${enemySummary}</div>
  `;

  partyInfo.innerHTML = session.party_status
    .map(
      (pc) => `<div>
        <strong>${pc.name}</strong> (${pc.class_name} L${pc.level})<br/>
        Life: ${pc.current_life}/${pc.max_life} | Attack: +${pc.attack_bonus} | Defense: +${pc.defense_bonus}
      </div>`
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
  const adventureId = adventureSelect.value;
  const adventureType = adventureId === "random" ? "random" : "imported";
  if (!partyId) {
    alert("Create a party first.");
    return;
  }
  const session = await api("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ party_id: partyId, adventure_type: adventureType, adventure_id: adventureId }),
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
loadAdventures();
