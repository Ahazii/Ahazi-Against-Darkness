const editor = {
  icons: [],
  iconFiles: [],
};

const iconList = document.getElementById("icon-list");
const iconStatus = document.getElementById("icon-status");
const addIconButton = document.getElementById("add-icon");
const addFoundIconsButton = document.getElementById("add-found-icons");
const autoAssignIconsButton = document.getElementById("auto-assign-icons");
const refreshIconFilesButton = document.getElementById("refresh-icon-files");
const saveIconsButton = document.getElementById("save-icons");

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
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function setStatus(message) {
  iconStatus.textContent = message;
}

function assetUrl(path) {
  const clean = String(path || "")
    .replace(/^\/?assets\//, "")
    .replace(/^\/+/, "");
  return `/assets/${clean}`;
}

async function loadIcons() {
  try {
    const [icons, iconFiles] = await Promise.all([api("/api/rules/icons"), api("/api/assets/icon-files")]);
    editor.icons = icons;
    editor.iconFiles = iconFiles;
    renderIcons();
    setStatus(`${editor.icons.length} icons | ${editor.iconFiles.length} files found in assets/icons/user`);
  } catch (error) {
    setStatus(error.message);
  }
}

function renderIcons() {
  iconList.replaceChildren();
  for (const icon of editor.icons) {
    iconList.appendChild(renderIconRow(icon));
  }
}

function renderIconRow(icon) {
  const row = node("div", "icon-editor-row");
  const preview = node("div", "icon-editor-preview");
  preview.title = icon.description || icon.label;
  if (icon.file) {
    const image = document.createElement("img");
    image.src = assetUrl(icon.file);
    image.alt = icon.label;
    preview.appendChild(image);
  } else {
    preview.appendChild(node("span", `map-content-icon ${icon.fallback || icon.id}`));
  }

  const fields = node("div", "icon-editor-fields");
  fields.append(
    textField(icon, "id", "ID", "monster"),
    textField(icon, "label", "Label", "Active Enemy"),
    selectField(icon, "category", "Category", ["map", "character", "monster", "item", "condition", "ui"]),
    fileSelectField(icon),
    textField(icon, "fallback", "Fallback", "monster"),
    textField(icon, "source_url", "Source URL", "https://thenounproject.com/..."),
    textField(icon, "attribution", "Attribution", "Icon by Creator from Noun Project"),
    textField(icon, "license", "License", "Noun Project CC BY 3.0"),
    textAreaField(icon, "description", "Description", "What this icon means in play."),
    textAreaField(icon, "notes", "Notes", "Download/account/licensing notes.")
  );

  const actions = node("div", "icon-editor-actions");
  const remove = node("button", "danger-button", "Remove");
  remove.type = "button";
  remove.addEventListener("click", () => {
    editor.icons = editor.icons.filter((item) => item !== icon);
    renderIcons();
  });
  actions.appendChild(remove);

  row.append(preview, fields, actions);
  return row;
}

function fileSelectField(icon) {
  const field = node("label");
  field.textContent = "File";
  const select = document.createElement("select");
  const options = ["", ...editor.iconFiles];
  if (icon.file && !options.includes(icon.file)) options.push(icon.file);
  for (const value of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value || "Built-in fallback only";
    option.selected = icon.file === value;
    select.appendChild(option);
  }
  select.addEventListener("change", () => {
    icon.file = select.value;
    renderIcons();
  });
  field.appendChild(select);
  return field;
}

function textField(icon, key, label, placeholder) {
  const field = node("label");
  field.textContent = label;
  const input = document.createElement("input");
  input.value = icon[key] || "";
  input.placeholder = placeholder;
  input.addEventListener("input", () => {
    icon[key] = input.value;
  });
  field.appendChild(input);
  return field;
}

function textAreaField(icon, key, label, placeholder) {
  const field = node("label", "wide-field");
  field.textContent = label;
  const input = document.createElement("textarea");
  input.rows = 2;
  input.value = icon[key] || "";
  input.placeholder = placeholder;
  input.addEventListener("input", () => {
    icon[key] = input.value;
  });
  field.appendChild(input);
  return field;
}

function selectField(icon, key, label, options) {
  const field = node("label");
  field.textContent = label;
  const select = document.createElement("select");
  for (const value of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    option.selected = icon[key] === value;
    select.appendChild(option);
  }
  select.addEventListener("change", () => {
    icon[key] = select.value;
  });
  field.appendChild(select);
  return field;
}

function addIcon() {
  editor.icons.push({
    id: `new-icon-${Date.now()}`,
    label: "New Icon",
    category: "map",
    description: "",
    file: "",
    fallback: "treasure",
    source_url: "",
    attribution: "",
    license: "Noun Project CC BY 3.0",
    notes: "",
  });
  renderIcons();
}

function addFoundIconFiles() {
  const usedFiles = new Set(editor.icons.map((icon) => icon.file).filter(Boolean));
  const newFiles = editor.iconFiles.filter((file) => !usedFiles.has(file));
  for (const file of newFiles) {
    const id = uniqueIconId(iconIdFromFile(file));
    editor.icons.push({
      id,
      label: labelFromIconId(id),
      category: "map",
      description: "",
      file,
      fallback: "treasure",
      source_url: nounProjectUrlFromFile(file),
      attribution: "",
      license: "Noun Project CC BY 3.0",
      notes: "Fill the creator attribution from the Noun Project page before public use.",
    });
  }
  renderIcons();
  setStatus(newFiles.length ? `Added ${newFiles.length} icon file${newFiles.length === 1 ? "" : "s"}` : "No unassigned icon files found");
}

function autoAssignFoundFiles() {
  const suggestions = {
    monster: ["monster"],
    defeated: ["skull", "dead"],
    fallen: ["grave"],
    "dungeon-exit": ["dungeon", "exit"],
    passage: ["passage", "corridor"],
    door: ["door"],
    treasure: ["treasure", "chest", "gold", "coin"],
    trap: ["trap"],
  };
  let updated = 0;
  for (const [iconId, tokens] of Object.entries(suggestions)) {
    const icon = editor.icons.find((item) => item.id === iconId);
    if (!icon || icon.file) continue;
    const match = editor.iconFiles.find((file) => tokens.some((token) => file.toLowerCase().includes(token)));
    if (!match) continue;
    icon.file = match;
    if (!icon.source_url) icon.source_url = nounProjectUrlFromFile(match);
    if (!icon.license) icon.license = "Noun Project CC BY 3.0";
    if (!icon.notes) icon.notes = "Fill the creator attribution from the Noun Project page before public use.";
    updated += 1;
  }
  renderIcons();
  setStatus(updated ? `Auto assigned ${updated} icon${updated === 1 ? "" : "s"}. Review attribution, then save.` : "No new matching files found");
}

function iconIdFromFile(file) {
  const stem = file
    .split("/")
    .pop()
    .replace(/\.[^.]+$/, "")
    .replace(/^noun-/, "");
  return stem.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || `icon-${Date.now()}`;
}

function uniqueIconId(baseId) {
  const existing = new Set(editor.icons.map((icon) => icon.id));
  if (!existing.has(baseId)) return baseId;
  let index = 2;
  while (existing.has(`${baseId}-${index}`)) index += 1;
  return `${baseId}-${index}`;
}

function labelFromIconId(iconId) {
  return iconId
    .replace(/-\d+$/, "")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function nounProjectUrlFromFile(file) {
  const match = file.match(/-(\d+)\.[^.]+$/);
  return match ? `https://thenounproject.com/icon/${match[1]}/` : "";
}

async function saveIcons() {
  try {
    const normalized = editor.icons.map((icon) => ({
      id: icon.id.trim().toLowerCase(),
      label: icon.label.trim(),
      category: icon.category,
      description: icon.description.trim(),
      file: icon.file.trim(),
      fallback: icon.fallback.trim(),
      source_url: icon.source_url.trim(),
      attribution: icon.attribution.trim(),
      license: icon.license.trim(),
      notes: icon.notes.trim(),
    }));
    await api("/api/rules/icons", {
      method: "PUT",
      body: JSON.stringify(normalized),
    });
    editor.icons = normalized;
    renderIcons();
    setStatus("Saved");
  } catch (error) {
    setStatus(error.message);
  }
}

addIconButton.addEventListener("click", addIcon);
addFoundIconsButton.addEventListener("click", addFoundIconFiles);
autoAssignIconsButton.addEventListener("click", autoAssignFoundFiles);
refreshIconFilesButton.addEventListener("click", loadIcons);
saveIconsButton.addEventListener("click", saveIcons);

loadIcons();
