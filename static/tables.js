async function api(path) {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error("Request failed");
  }
  return response.json();
}

function tileSvg(shape) {
  const doors = shape.doors || [];
  const doorLine = (x1, y1, x2, y2) =>
    `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#f5c542" stroke-width="4" />`;
  const doorSegments = [
    doors.includes("north") ? doorLine(70, 10, 130, 10) : "",
    doors.includes("south") ? doorLine(70, 110, 130, 110) : "",
    doors.includes("west") ? doorLine(10, 40, 10, 80) : "",
    doors.includes("east") ? doorLine(210, 40, 210, 80) : "",
  ].join("");
  return `
    <svg width="220" height="120" viewBox="0 0 220 120" xmlns="http://www.w3.org/2000/svg">
      <rect x="20" y="20" width="180" height="80" rx="8" fill="#1b2333" stroke="#4c6fff" stroke-width="2" />
      ${doorSegments}
      <text x="110" y="70" text-anchor="middle" fill="#f5f5f5" font-size="12">${shape.name}</text>
    </svg>
  `;
}

function renderTables(data) {
  const tablesList = document.getElementById("tables-list");
  tablesList.innerHTML = "";
  Object.entries(data.tables).forEach(([name, entries]) => {
    const section = document.createElement("div");
    section.classList.add("card");
    section.innerHTML = `<h3>${entries.name || name}</h3><div>Dice: ${entries.dice || "n/a"}</div>`;

    if (entries.entries && Array.isArray(entries.entries)) {
      const list = document.createElement("ul");
      list.classList.add("list");
      entries.entries.forEach((entry) => {
        const item = document.createElement("li");
        item.innerHTML = `<strong>Roll ${entry.roll}:</strong> ${entry.result || ""}`;
        list.appendChild(item);
      });
      section.appendChild(list);
    } else if (Array.isArray(entries)) {
      const list = document.createElement("ul");
      list.classList.add("list");
      entries.forEach((entry, index) => {
        const item = document.createElement("li");
        item.textContent = typeof entry === "string" ? entry : `#${index + 1} ${JSON.stringify(entry)}`;
        list.appendChild(item);
      });
      section.appendChild(list);
    } else {
      const pre = document.createElement("pre");
      pre.textContent = JSON.stringify(entries, null, 2);
      section.appendChild(pre);
    }
    tablesList.appendChild(section);
  });
}

function renderShapes(shapes) {
  const grid = document.getElementById("tile-shapes");
  grid.innerHTML = "";
  const tileTable = dataCache.tile_table || { entries: [] };
  const tileMap = new Map(tileTable.entries.map((entry) => [entry.tile_id, entry]));
  shapes.forEach((shape) => {
    const card = document.createElement("div");
    card.classList.add("card");
    const tableEntry = tileMap.get(shape.id);
    const image = tableEntry ? tableEntry.image : null;
    const imageMarkup = image
      ? `<img src="/static/${image}" alt="${shape.name}" class="tile-image" />`
      : `<div class="tile-image placeholder">Add image for ${shape.id}</div>`;
    card.innerHTML = `
      <div>${imageMarkup}</div>
      ${tileSvg(shape)}
      <div><strong>${shape.id}</strong> - ${shape.name}</div>
      <div>${tableEntry ? `Roll ${tableEntry.roll}` : "Roll: n/a"}</div>
    `;
    grid.appendChild(card);
  });
}

let dataCache = {};

async function load() {
  dataCache = await api("/api/tables/details");
  renderTables(dataCache);
  renderShapes(dataCache.tile_shapes);
}

load();
