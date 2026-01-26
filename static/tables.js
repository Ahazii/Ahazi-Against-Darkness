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
    section.innerHTML = `<h3>${name}</h3>`;
    if (Array.isArray(entries)) {
      const list = document.createElement("ul");
      list.classList.add("list");
      entries.forEach((entry) => {
        const item = document.createElement("li");
        item.textContent = typeof entry === "string" ? entry : JSON.stringify(entry);
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
  shapes.forEach((shape) => {
    const card = document.createElement("div");
    card.classList.add("card");
    card.innerHTML = tileSvg(shape);
    grid.appendChild(card);
  });
}

async function load() {
  const data = await api("/api/tables/details");
  renderTables(data);
  renderShapes(data.tile_shapes);
}

load();
