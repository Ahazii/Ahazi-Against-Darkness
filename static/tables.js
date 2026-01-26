async function api(path, options = {}) {
  const response = await fetch(path, options);
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

function renderShapes() {
  const grid = document.getElementById("tile-shapes");
  grid.innerHTML = "";
  const tileTable = dataCache.tile_table || { entries: [] };
  tileTable.entries.forEach((entry) => {
    const card = document.createElement("div");
    card.classList.add("card");
    const imageName = entry.image ? entry.image.split("/").pop() : `${entry.roll}.gif`;
    const imageMarkup = entry.image
      ? `<img src="/api/tiles/${imageName}" alt="Tile ${entry.roll}" class="tile-image" />`
      : `<div class="tile-image placeholder">Add image for ${entry.roll}</div>`;
    const passageways = entry.passageways || "0,0,0,0";
    const doors = entry.doors || "0,0,0,0";
    card.innerHTML = `
      <div>${imageMarkup}</div>
      <div><strong>Roll ${entry.roll}</strong></div>
      <div>Image: ${entry.image || "n/a"}</div>
      <div>Description: ${entry.description || ""}</div>
      <div>Passageways: ${passageways}</div>
      <div>Doors: ${doors}</div>
      <div class="tile-upload">
        <input type="file" data-filename="${imageName}" />
        <button class="upload-btn">Replace Image</button>
      </div>
    `;
    grid.appendChild(card);
  });
}

document.addEventListener("click", async (event) => {
  if (!event.target.classList.contains("upload-btn")) return;
  const container = event.target.closest(".card");
  const input = container.querySelector("input[type='file']");
  const file = input.files[0];
  if (!file) {
    saveStatus.textContent = "Select a file before uploading.";
    return;
  }
  const filename = input.dataset.filename;
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`/api/tiles/${filename}`, {
    method: "POST",
    body: form,
  });
  if (!response.ok) {
    saveStatus.textContent = "Upload failed.";
    return;
  }
  saveStatus.textContent = "Image uploaded.";
  load();
});

let dataCache = {};
const tablesJson = document.getElementById("tables-json");
const tileShapesJson = document.getElementById("tile-shapes-json");
const tileTableJson = document.getElementById("tile-table-json");
const saveButton = document.getElementById("save-tables");
const saveStatus = document.getElementById("save-status");

async function load() {
  dataCache = await api("/api/tables/details");
  renderTables(dataCache);
  renderShapes();
  tablesJson.value = JSON.stringify(dataCache.tables, null, 2);
  tileShapesJson.value = JSON.stringify(dataCache.tile_shapes, null, 2);
  tileTableJson.value = JSON.stringify(dataCache.tile_table, null, 2);
}

saveButton.addEventListener("click", async () => {
  try {
    const payload = {
      tables: JSON.parse(tablesJson.value),
      tile_shapes: JSON.parse(tileShapesJson.value),
      tile_table: JSON.parse(tileTableJson.value),
    };
    await api("/api/tables/details", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    saveStatus.textContent = "Saved.";
    dataCache = payload;
    renderTables(dataCache);
    renderShapes();
  } catch (error) {
    saveStatus.textContent = "Invalid JSON or save failed.";
  }
});

load();
