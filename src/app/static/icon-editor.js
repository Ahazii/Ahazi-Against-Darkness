const editor = {
  icons: [],
};

const iconList = document.getElementById("icon-list");
const iconStatus = document.getElementById("icon-status");
const addIconButton = document.getElementById("add-icon");
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
    editor.icons = await api("/api/rules/icons");
    renderIcons();
    setStatus(`${editor.icons.length} icons`);
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
    textField(icon, "file", "File", "icons/user/example.svg"),
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
saveIconsButton.addEventListener("click", saveIcons);

loadIcons();
