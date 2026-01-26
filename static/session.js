const mapGrid = document.getElementById("map-grid");
const roomInfo = document.getElementById("room-info");
const partyInfo = document.getElementById("party-info");
const roomDescription = document.getElementById("room-description");
const tileVisual = document.getElementById("tile-visual");
const tablesInfo = document.getElementById("tables-info");
const logBox = document.getElementById("log");
const exploreBtn = document.getElementById("explore-btn");
const combatBtn = document.getElementById("combat-btn");
const searchBtn = document.getElementById("search-btn");
const treasureBtn = document.getElementById("treasure-btn");
const reactionBtn = document.getElementById("reaction-btn");

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

function tileSvg(tile) {
  const label = tile.tile_type === "room" ? "Room" : "Corridor";
  return `
    <svg width="220" height="120" viewBox="0 0 220 120" xmlns="http://www.w3.org/2000/svg">
      <rect x="20" y="20" width="180" height="80" rx="8" fill="#1b2333" stroke="#4c6fff" stroke-width="2" />
      <rect x="70" y="50" width="80" height="20" fill="#3b4a6b" rx="4" />
      <text x="110" y="75" text-anchor="middle" fill="#f5f5f5" font-size="12">${label}</text>
    </svg>
  `;
}

function renderSession(session) {
  currentSession = session;

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
  tileVisual.innerHTML = tileSvg(currentTile);

  exploreBtn.disabled = session.mode !== "exploration";
  combatBtn.disabled = session.mode !== "combat";
  searchBtn.disabled = session.mode !== "exploration" || currentTile.searched;
  treasureBtn.disabled = session.mode !== "exploration" || !currentTile.objects.includes("Treasure");
  reactionBtn.disabled = session.mode !== "exploration" || currentTile.enemies.length === 0;
}

async function loadTables() {
  const tables = await api("/api/tables");
  tablesInfo.innerHTML = tables.map((table) => `<div>${table}</div>`).join("");
}

async function loadSession(sessionId) {
  const session = await api(`/api/sessions/${sessionId}`);
  renderSession(session);
}

function getSessionId() {
  const params = new URLSearchParams(window.location.search);
  return params.get("sessionId");
}

exploreBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  const session = await api(`/api/sessions/${currentSession.id}/advance`, {
    method: "POST",
    body: JSON.stringify({ action: "explore" }),
  });
  renderSession(session);
});

searchBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  const session = await api(`/api/sessions/${currentSession.id}/advance`, {
    method: "POST",
    body: JSON.stringify({ action: "search" }),
  });
  renderSession(session);
});

treasureBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  const session = await api(`/api/sessions/${currentSession.id}/advance`, {
    method: "POST",
    body: JSON.stringify({ action: "open_treasure" }),
  });
  renderSession(session);
});

reactionBtn.addEventListener("click", async () => {
  if (!currentSession) return;
  const session = await api(`/api/sessions/${currentSession.id}/advance`, {
    method: "POST",
    body: JSON.stringify({ action: "reaction" }),
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

const sessionId = getSessionId();
if (sessionId) {
  loadSession(sessionId);
  loadTables();
} else {
  logBox.innerHTML = "<div>No session id provided.</div>";
}
