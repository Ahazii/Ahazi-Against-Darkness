const modernState = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  sessions: [],
  campaign: null,
  rulesProfiles: [],
  equipmentRows: [],
  rulesReference: [],
  tables: {},
};

const MODERN_PREFS_KEY = "ahazi-modern-dashboard-prefs";

function readModernPrefs() {
  try {
    return JSON.parse(window.localStorage.getItem(MODERN_PREFS_KEY) || "{}");
  } catch {
    return {};
  }
}

function writeModernPrefs(patch) {
  const next = { ...readModernPrefs(), ...patch };
  window.localStorage.setItem(MODERN_PREFS_KEY, JSON.stringify(next));
  return next;
}

const PAGE_META = {
  home: ["New Home Dashboard", "Separate pages for campaign setup, TAG management, rules, guides, and developer tools."],
  characters: ["Character Management", "Create, maintain, level, heal, delete, and review roster characters."],
  troupes: ["Troupe Management", "Manage the TAG troupe roster, active party selection, travel, and home settlement."],
  guild: ["Guild Management", "Manage Adventurers Guild membership, coffers, upkeep, benefits, and obligations."],
  parties: ["Party Management", "Create, heal, delete, and review four-character parties."],
  equipment: ["Equipment Shop", "Buy and sell equipment for a selected character without returning to the legacy home page."],
  banking: ["Banking and Finance", "TAG bank accounts, hidden treasure troves, robbery recovery, and finance actions."],
  settlement: ["Settlement Management", "Maintain TAG settlement name, size, notes, services, travel, and availability rolls."],
  campaign: ["Campaign Management", "World, hex map, and settlement-map planning surface."],
  settings: ["Settings / Options", "Ruleset profiles, campaign options, map limits, and TAG banking preferences."],
  "ai-adventures": ["AI Adventure Generation", "Generate prompts, validate imports, and install AI-authored modules."],
  "go-adventure": ["Go Adventure!", "Select a party, adventure type, ruleset, and start a session."],
  "rules-reference": ["Rules Reference", "Search and inspect curated implementation references."],
  tables: ["Tables List", "Browse structured rules and data tables."],
  library: ["Credits / History / Background", "Open owned PDFs and maintain signoff-safe background notes."],
  guides: ["Game Guides", "Player guides and workflow documents."],
  developer: ["Developer Section", "Password-gated tooling for module import, editors, and validation."],
};

const PDF_LINKS = [
  ["Expanded Edition", "/Rules/Four_Against_Darkness_Expanded_Edition.pdf", "Open the Expanded Edition PDF."],
  ["Four Against the Abyss", "/Rules/Four-Against-the-Abyss.pdf", "Open Four Against the Abyss PDF."],
  ["Forsaken Depths", "/Rules/Four_Against_the_Forsaken_Depths.pdf", "Open Forsaken Depths PDF."],
  ["Tales from the Adventurers Guild", "/Rules/Tales_from_the_adventurers_guild.pdf", "Open Tales from the Adventurers Guild PDF."],
  ["Four Against the Netherworld", "/Rules/Four Against_the_Netherworld.pdf", "Open Four Against the Netherworld PDF."],
  ["Courtship of Flower Demons", "/Rules/The_Courtship_of_Flower_Demons.pdf", "Open The Courtship of Flower Demons PDF."],
];

const statusEl = document.getElementById("modern-status");
const titleEl = document.getElementById("modern-page-title");
const subtitleEl = document.getElementById("modern-page-subtitle");
const descriptionEl = document.getElementById("modern-page-description");
const rootEl = document.getElementById("modern-page-root");

function currentPage() {
  const raw = window.location.pathname.replace(/^\/modern\/?/, "") || "home";
  return PAGE_META[raw] ? raw : "home";
}

function setStatus(message) {
  statusEl.textContent = message;
}

function handleError(error) {
  setStatus(error?.message || "Action failed");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      /* keep status text */
    }
    throw new Error(detail);
  }
  return response.json();
}

function el(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}

function button(label, title, onClick, className = "secondary") {
  const btn = el("button", className, label);
  btn.type = "button";
  btn.title = title;
  btn.addEventListener("click", () => onClick().catch(handleError));
  return btn;
}

function link(label, href, title, className = "link-button secondary") {
  const anchor = el("a", className, label);
  anchor.href = href;
  anchor.title = title;
  return anchor;
}

function field(labelText, input) {
  const label = el("label", "modern-field");
  label.appendChild(el("span", "", labelText));
  label.appendChild(input);
  return label;
}

function input(type, id, title, value = "") {
  const node = document.createElement("input");
  node.type = type;
  node.id = id;
  node.title = title;
  if (value !== "") node.value = value;
  return node;
}

function select(id, title, options = []) {
  const node = document.createElement("select");
  node.id = id;
  node.title = title;
  for (const [value, label] of options) node.appendChild(new Option(label, value));
  return node;
}

function textarea(id, title, rows = 5) {
  const node = document.createElement("textarea");
  node.id = id;
  node.rows = rows;
  node.title = title;
  return node;
}

function card(title, body = "") {
  const node = el("section", "modern-card");
  node.appendChild(el("h3", "", title));
  if (body) node.appendChild(el("p", "muted", body));
  return node;
}

function actions() {
  return el("div", "modern-actions");
}

function optionRows(options) {
  return options.map(([value, label]) => new Option(label, value));
}

function formatCharacter(character) {
  if (!character) return "Unknown character";
  return `${character.name} (${character.class_name}, L${character.level}, ${character.gold || 0}gp, ${character.clues || 0} Clues)`;
}

function modernTitleFromKey(key) {
  return String(key || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function modernStatusLabel(status) {
  const labels = {
    full: "Full",
    implemented: "Implemented",
    partial: "Partial",
    planned: "Planned",
    validated: "Validated",
    not_in_app: "Not in app",
  };
  return labels[status] || modernTitleFromKey(status || "reference");
}

function modernSearchText(value) {
  if (value == null) return "";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return value.map((item) => modernSearchText(item)).join(" ");
  if (typeof value === "object") return Object.values(value).map((item) => modernSearchText(item)).join(" ");
  return "";
}

function partyNamesForCharacter(characterId) {
  return modernState.parties.filter((party) => (party.character_ids || []).includes(characterId)).map((party) => party.name);
}

function tagBankForCharacter(characterId) {
  const account = (modernState.campaign?.tag_bank_accounts || []).find((item) => item.owner_character_id === characterId);
  return account?.gold_gp || 0;
}

function tagBankAccountForCharacter(characterId) {
  return (modernState.campaign?.tag_bank_accounts || []).find((item) => item.owner_character_id === characterId) || null;
}

function tagGuildBenefitsActive(campaign = modernState.campaign || {}) {
  return Boolean(campaign.tag_guild_member) && Number(campaign.tag_guild_coffers_gp || 0) > 0;
}

function unresolvedCloseoutTasks(categories = []) {
  const wanted = new Set(categories);
  return (modernState.campaign?.tag_closeout_tasks || []).filter((task) => !task.resolved && (!wanted.size || wanted.has(task.category)));
}

function latestTagLogs(actions = []) {
  const wanted = new Set(actions);
  return (modernState.campaign?.tag_downtime_log || [])
    .filter((entry) => !wanted.size || wanted.has(entry.action))
    .slice(-6)
    .reverse();
}

function modernStatusRow(title, body, hint = "") {
  const row = el("div", "modern-row");
  if (hint) row.title = hint;
  row.append(el("strong", "", title), el("span", "muted", body));
  return row;
}

function characterSearchText(character) {
  return [
    character.name,
    character.class_name,
    character.level,
    character.gold,
    character.clues,
    ...(character.statuses || []),
    ...partyNamesForCharacter(character.id),
    (modernState.campaign?.tag_troupe_member_character_ids || []).includes(character.id) ? "troupe" : "",
    (modernState.campaign?.tag_troupe_active_character_ids || []).includes(character.id) ? "active" : "",
  ].join(" ").toLowerCase();
}

function filteredCharacters({ search = "", classId = "", sort = "name" } = {}) {
  const needle = String(search || "").toLowerCase();
  const rows = modernState.characters.filter((character) => {
    if (classId && character.class_id !== classId) return false;
    return !needle || characterSearchText(character).includes(needle);
  });
  rows.sort((left, right) => {
    if (sort === "level") return (right.level || 0) - (left.level || 0) || left.name.localeCompare(right.name);
    if (sort === "class") return String(left.class_name || "").localeCompare(String(right.class_name || "")) || left.name.localeCompare(right.name);
    if (sort === "party") return partyNamesForCharacter(left.id).join(",").localeCompare(partyNamesForCharacter(right.id).join(",")) || left.name.localeCompare(right.name);
    return left.name.localeCompare(right.name);
  });
  return rows;
}

function characterFilterControls(prefix, onChange) {
  const panel = el("div", "modern-filterbar");
  const search = input("search", `${prefix}-character-search`, "Search by name, class, level, party, troupe, status, gold, or Clues.");
  const classFilter = select(`${prefix}-character-class-filter`, "Filter characters by class.", [["", "All classes"], ...modernState.classes.map((item) => [item.id, item.name])]);
  const sort = select(`${prefix}-character-sort`, "Sort characters.", [["name", "Name"], ["level", "Level"], ["class", "Class"], ["party", "Party"]]);
  panel.append(field("Search", search), field("Class", classFilter), field("Sort", sort));
  for (const node of [search, classFilter, sort]) node.addEventListener("input", onChange);
  classFilter.addEventListener("change", onChange);
  sort.addEventListener("change", onChange);
  return { panel, search, classFilter, sort };
}

function characterSelect(id, title, blank = "Choose character") {
  return select(id, title, [["", blank], ...filteredCharacters().map((character) => [character.id, formatCharacter(character)])]);
}

function updateCharacterSelect(selectNode, blank, filters = {}) {
  const current = selectNode.value;
  selectNode.replaceChildren(...optionRows([["", blank], ...filteredCharacters(filters).map((character) => [character.id, formatCharacter(character)])]));
  if ([...selectNode.options].some((option) => option.value === current)) selectNode.value = current;
}

function searchablePicker(prefix, label, title, rows, getLabel, getText, onPick, { sortOptions = [["name", "Name"]], blank = "Choose" } = {}) {
  const wrap = el("div", "modern-picker");
  const search = input("search", `${prefix}-search`, `Search ${label}.`);
  const sort = select(`${prefix}-sort`, `Sort ${label}.`, sortOptions);
  const picker = select(`${prefix}-select`, title, [["", blank]]);
  const draw = () => {
    const needle = search.value.trim().toLowerCase();
    const sorted = [...rows].filter((row) => !needle || getText(row).toLowerCase().includes(needle));
    sorted.sort((a, b) => {
      const key = sort.value || "name";
      if (key === "price") return (a.price_gp || a.cost_gp || 0) - (b.price_gp || b.cost_gp || 0) || getLabel(a).localeCompare(getLabel(b));
      if (key === "class") return String(a.class_name || a.category || "").localeCompare(String(b.class_name || b.category || "")) || getLabel(a).localeCompare(getLabel(b));
      return getLabel(a).localeCompare(getLabel(b));
    });
    const current = picker.value;
    picker.replaceChildren(...optionRows([["", blank], ...sorted.map((row) => [row.key || row.id || row.name, getLabel(row)])]));
    if ([...picker.options].some((option) => option.value === current)) picker.value = current;
    if (onPick) onPick(picker.value);
  };
  search.addEventListener("input", draw);
  sort.addEventListener("change", draw);
  picker.addEventListener("change", () => onPick?.(picker.value));
  wrap.append(field(`${label} search`, search), field(`${label} sort`, sort), field(label, picker));
  draw();
  return { wrap, search, sort, picker, draw };
}

function closeoutTasksFor(categories = []) {
  const allowed = new Set(categories);
  return (modernState.campaign?.tag_closeout_tasks || []).filter((task) => {
    if (task.resolved) return false;
    return !allowed.size || allowed.has(task.category);
  });
}

function renderCloseoutTasks(title, categories) {
  const tasks = closeoutTasksFor(categories);
  const panel = card(title, "Outstanding TAG closeout prompts created when an adventure completes.");
  if (!tasks.length) {
    panel.appendChild(el("p", "muted", "No open TAG closeout tasks for this section."));
    return panel;
  }
  for (const task of tasks) {
    const row = el("div", "modern-row");
    row.title = task.reference || task.result_text || task.title;
    const copy = el("div", "modern-stack");
    copy.append(el("strong", "", task.title), el("span", "muted", task.result_text || ""));
    if (task.reference) copy.appendChild(el("span", "muted", task.reference));
    row.appendChild(copy);
    row.appendChild(button("Mark Done", "Mark this TAG closeout task as resolved if you handled it manually or with another control.", async () => {
      const result = await api("/api/campaign/tag/closeout-task", {
        method: "POST",
        body: JSON.stringify({ task_id: task.id, note: "Resolved from modern closeout checklist" }),
      });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Closeout task resolved.");
      await refreshCoreAndRender();
    }));
    panel.appendChild(row);
  }
  return panel;
}

function characterOptions(blank = "Choose character") {
  return [["", blank], ...modernState.characters.map((character) => [character.id, `${character.name} (${character.class_name}, L${character.level}, ${character.gold || 0}gp, ${character.clues || 0} Clues)`])];
}

function partyOptions(blank = "Choose party") {
  return [["", blank], ...modernState.parties.map((party) => [party.id, party.name])];
}

function adventureOptions(kind = "all") {
  const rows = kind === "random" || kind === "ruleset" || kind === "all" ? [["random", "Random Dungeon"]] : [];
  for (const adventure of modernState.adventures) {
    if (kind === "ai" && !String(adventure.id || "").startsWith("ai-")) continue;
    if (kind === "imported" && String(adventure.id || "").startsWith("ai-")) continue;
    if ((kind === "random" || kind === "ruleset") && adventure.id !== "random") continue;
    rows.push([adventure.id, adventure.title || adventure.id]);
  }
  return rows;
}

async function loadCore() {
  const [classes, characters, parties, adventures, sessions, campaign, profiles] = await Promise.all([
    api("/api/rules/classes"),
    api("/api/characters"),
    api("/api/parties"),
    api("/api/adventures"),
    api("/api/sessions/summaries"),
    api("/api/campaign"),
    api("/api/rules/profiles"),
  ]);
  modernState.classes = classes;
  modernState.characters = characters;
  modernState.parties = parties;
  modernState.adventures = adventures;
  modernState.sessions = sessions;
  modernState.campaign = campaign;
  modernState.rulesProfiles = profiles;
}

async function refreshCoreAndRender() {
  await loadCore();
  renderPage();
}

function renderHome() {
  const grid = el("div", "modern-home-grid");
  for (const [page, meta] of Object.entries(PAGE_META)) {
    if (page === "home") continue;
    const section = card(meta[0], meta[1]);
    const row = actions();
    row.appendChild(link("Open", `/modern/${page}`, `Open ${meta[0]}.`, "link-button"));
    section.appendChild(row);
    grid.appendChild(section);
  }
  rootEl.appendChild(grid);
}

function renderCharacters() {
  const layout = el("div", "modern-two-col");
  const list = card("Roster", "Search, sort, heal, spend XP, or delete roster characters.");
  const filters = characterFilterControls("modern-roster", drawRoster);
  const rows = el("div", "modern-list modern-list-tall");
  list.append(filters.panel, rows);
  function drawRoster() {
    rows.replaceChildren();
    for (const character of filteredCharacters({ search: filters.search.value, classId: filters.classFilter.value, sort: filters.sort.value })) {
      const row = el("div", "modern-row");
      const parties = partyNamesForCharacter(character.id);
      const troupe = (modernState.campaign?.tag_troupe_member_character_ids || []).includes(character.id) ? "TAG troupe" : "not in TAG troupe";
      row.appendChild(el("strong", "", `${character.name} - ${character.class_name} L${character.level}`));
      row.appendChild(el("span", "muted", `HP ${character.current_life}/${character.max_life} · XP ${character.xp || 0} · carried ${character.gold || 0}gp · TAG bank ${tagBankForCharacter(character.id)}gp · ${character.clues || 0} Clues`));
      row.appendChild(el("span", "muted", `Party: ${parties.join(", ") || "none"} · ${troupe}`));
      const rowActions = actions();
      rowActions.append(
        button("Heal", "Restore this character to full Life.", async () => {
          await api(`/api/characters/${character.id}/heal`, { method: "POST" });
          setStatus("Character healed.");
          await refreshCoreAndRender();
        }),
        button("Spend XP", "Spend one pending XP roll using this character's configured campaign mode.", async () => {
          await api(`/api/characters/${character.id}/spend-xp`, { method: "POST", body: JSON.stringify({}) });
          setStatus("XP spend attempted.");
          await refreshCoreAndRender();
        }),
        button("Delete", "Delete this character if they are not in a saved party.", async () => {
          if (!window.confirm(`Delete ${character.name}?`)) return;
          await api(`/api/characters/${character.id}`, { method: "DELETE" });
          setStatus("Character deleted.");
          await refreshCoreAndRender();
        })
      );
      row.appendChild(rowActions);
      rows.appendChild(row);
    }
  }
  drawRoster();
  layout.appendChild(list);

  const create = card("Create / Add Character", "Choose a class, enter a name, and create a roster hero.");
  create.classList.add("modern-card-compact");
  const name = input("text", "modern-character-name", "Name for the new character.");
  const classSelect = select("modern-character-class", "Class for the new character.", modernState.classes.map((item) => [item.id, item.name]));
  create.append(field("Name", name), field("Class", classSelect));
  create.appendChild(button("Create", "Create this character in the roster.", async () => {
    await api("/api/characters", { method: "POST", body: JSON.stringify({ name: name.value, class_id: classSelect.value }) });
    setStatus("Character created.");
    await refreshCoreAndRender();
  }, ""));
  layout.appendChild(create);
  rootEl.appendChild(layout);
}

function troupeMemberIds() {
  return (modernState.campaign?.tag_troupe_member_character_ids || []).filter(Boolean);
}

function knownSettlements() {
  const names = new Set([modernState.campaign?.settlement_name || "Home Settlement"]);
  for (const settlement of modernState.campaign?.tag_settlements || []) {
    if (settlement.name) names.add(settlement.name);
  }
  for (const entry of modernState.campaign?.tag_travel_log || []) {
    if (entry.from_settlement) names.add(entry.from_settlement);
    if (entry.to_settlement) names.add(entry.to_settlement);
  }
  return [...names].filter(Boolean).sort();
}

function renderTroupes() {
  const campaign = modernState.campaign || {};
  const panel = card("Troupe Roster", "The troupe is the wider TAG character company; the active party is selected from these members.");
  const name = input("text", "modern-troupe-name", "Name of the TAG troupe.", campaign.tag_troupe_name || "Adventuring Troupe");
  const addFilters = characterFilterControls("modern-troupe-add", () => updateCharacterSelect(add, "Choose member to add", { search: addFilters.search.value, classId: addFilters.classFilter.value, sort: addFilters.sort.value }));
  const add = characterSelect("modern-troupe-add-select", "Roster character to add to the troupe.", "Choose member to add");
  const remove = select("modern-troupe-remove", "Troupe character to remove.", [["", "Choose member to remove"], ...troupeMemberIds().map((id) => {
    const c = modernState.characters.find((item) => item.id === id);
    return [id, c ? formatCharacter(c) : id];
  })]);
  const active = select("modern-troupe-active", "Select up to four active troupe members.", troupeMemberIds().map((id) => {
    const c = modernState.characters.find((item) => item.id === id);
    return [id, c ? formatCharacter(c) : id];
  }));
  active.multiple = true;
  active.size = Math.max(4, Math.min(8, troupeMemberIds().length || 4));
  for (const option of active.options) option.selected = (campaign.tag_troupe_active_character_ids || []).includes(option.value);
  panel.append(field("Troupe name", name), addFilters.panel, field("Add member", add), field("Remove member", remove), field("Active members", active));
  const save = async (memberIds = troupeMemberIds()) => {
    const activeIds = Array.from(active.selectedOptions).map((option) => option.value).filter((id) => memberIds.includes(id)).slice(0, 4);
    modernState.campaign = (await api("/api/campaign/tag/troupe", {
      method: "POST",
      body: JSON.stringify({
        troupe_name: name.value || "Adventuring Troupe",
        member_character_ids: memberIds,
        active_character_ids: activeIds,
        guild_member: Boolean(campaign.tag_guild_member),
        guild_coffers_gp: Number(campaign.tag_guild_coffers_gp || 0),
      }),
    })).campaign;
    setStatus("Troupe saved.");
    await refreshCoreAndRender();
  };
  const row = actions();
  row.append(
    button("Save Troupe", "Save the troupe name and active member selection.", () => save(), ""),
    button("Add Member", "Add selected roster character to this troupe.", () => {
      const ids = Array.from(new Set([...troupeMemberIds(), add.value].filter(Boolean)));
      return save(ids);
    }),
    button("Remove Member", "Remove selected member from this troupe.", () => {
      const ids = troupeMemberIds().filter((id) => id !== remove.value);
      return save(ids);
    }),
    button("Delete Troupe", "Clear troupe members, active party selection, and reset the troupe name.", () => save([]))
  );
  panel.appendChild(row);
  const memberList = card("Troupe Members", "Current troupe members with party, bank, and activity status.");
  for (const id of troupeMemberIds()) {
    const character = modernState.characters.find((item) => item.id === id);
    if (!character) continue;
    const activeText = (campaign.tag_troupe_active_character_ids || []).includes(id) ? "active party" : "home/available";
    const memberRow = el("div", "modern-row");
    memberRow.append(el("strong", "", character.name), el("span", "muted", `${character.class_name} L${character.level} · ${activeText} · carried ${character.gold || 0}gp · TAG bank ${tagBankForCharacter(id)}gp · parties: ${partyNamesForCharacter(id).join(", ") || "none"}`));
    memberList.appendChild(memberRow);
  }

  const travel = card("Travel / Home Settlement", "The size modifier belongs to the selected TAG settlement and affects availability rolls. Travel changes the troupe home settlement focus.");
  const settlement = input("text", "modern-settlement-name", "Current home settlement name.", campaign.settlement_name || "Home Settlement");
  const size = select("modern-settlement-size", "Current settlement size modifier.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
  size.value = String(campaign.settlement_size ?? 0);
  const settlementList = select("modern-travel-known-destination", "Known settlement destination.", [["", "Choose known settlement"], ...knownSettlements().map((item) => [item, item])]);
  const dest = input("text", "modern-travel-destination", "Destination settlement name. Use this for a new settlement or to override the known-settlement list.");
  settlementList.addEventListener("change", () => {
    if (settlementList.value) dest.value = settlementList.value;
  });
  travel.append(field("Home settlement", settlement), field("Size modifier", size), field("Known settlements", settlementList), field("Travel destination", dest));
  const travelActions = actions();
  travelActions.append(
    button("Save Home", "Save settlement name and size.", async () => {
      modernState.campaign = await api("/api/campaign", { method: "PUT", body: JSON.stringify({ settlement_name: settlement.value, settlement_size: Number(size.value) }) });
      setStatus("Home settlement saved.");
      await refreshCoreAndRender();
    }, ""),
    button("Travel", "Travel to this settlement and roll TAG travel details.", async () => {
      const result = await api("/api/campaign/tag/travel-settlement", { method: "POST", body: JSON.stringify({ destination_name: dest.value, use_hex_map: false, pay_road_tithe: false }) });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Travel logged.");
      await refreshCoreAndRender();
    })
  );
  travel.appendChild(travelActions);
  rootEl.append(panel, memberList, travel);
}

function renderGuild() {
  const campaign = modernState.campaign || {};
  const panel = card("Guild Membership", "TAG currently models the printed Adventurers Guild. This is separate from the troupe roster: the troupe is who exists; Guild membership is the rules organisation with coffers, obligations, and benefits.");
  const active = input("checkbox", "modern-guild-active", "Enable Adventurers Guild membership for the troupe.");
  active.checked = Boolean(campaign.tag_guild_member);
  const coffers = input("number", "modern-guild-coffers-page", "Shared Guild coffers in gp.", String(campaign.tag_guild_coffers_gp || 0));
  const actionCharacter = select("modern-guild-character", "Guild member receiving resurrection funding or other character-specific Guild handling.", characterOptions("Choose character"));
  const amount = input("number", "modern-guild-amount", "Gold amount for Guild loot share, resurrection funding, or notes.", "0");
  const itemName = input("text", "modern-guild-availability-item", "Item name for the once-per-adventure Guild availability reroll.");
  panel.append(field("Guild active", active), field("Guild coffers gp", coffers));
  panel.appendChild(
    modernStatusRow(
      tagGuildBenefitsActive(campaign) ? "Benefits active" : "Benefits suspended/inactive",
      `Coffers ${campaign.tag_guild_coffers_gp || 0} gp · availability reroll ${campaign.tag_guild_availability_reroll_used ? "used" : "available"} · ${unresolvedCloseoutTasks(["guild"]).length} unresolved Guild closeout task(s).`,
      "Guild benefits require Adventurers Guild membership and coffers above 0 gp."
    )
  );
  const saveRow = actions();
  saveRow.append(
    button("Save Guild", "Save Guild active state and coffer total. New Guild membership defaults to 5000 gp if no coffers are entered.", async () => {
      modernState.campaign = (await api("/api/campaign/tag/troupe", {
        method: "POST",
        body: JSON.stringify({
          troupe_name: campaign.tag_troupe_name || "Adventuring Troupe",
          member_character_ids: troupeMemberIds(),
          active_character_ids: campaign.tag_troupe_active_character_ids || [],
          guild_member: active.checked,
          guild_coffers_gp: Number(coffers.value || 0),
        }),
      })).campaign;
      setStatus("Guild saved.");
      await refreshCoreAndRender();
    }, "")
  );
  panel.appendChild(saveRow);

  const finance = card("Guild Finance", "Run the TAG Guild money obligations at closeout or when playtesting a Guild rule.");
  finance.append(field("Amount gp", amount), field("Availability item", itemName));
  const financeRow = actions();
  financeRow.append(
    button("Run Upkeep", "Manual override for the closeout prompt: charge 10% upkeep from Guild coffers, reset the availability reroll, and suspend benefits at 0 gp.", async () => {
      const result = await api("/api/campaign/tag/finance-action", { method: "POST", body: JSON.stringify({ finance_action: "guild_upkeep" }) });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Guild upkeep charged.");
      await refreshCoreAndRender();
    }),
    button("Apply 50% Loot Share", "Enter total monetary loot; the Guild share is added to coffers and the party remainder is logged.", async () => {
      const result = await api("/api/campaign/tag/finance-action", {
        method: "POST",
        body: JSON.stringify({ finance_action: "guild_loot_share", amount_gp: Number(amount.value || 0) }),
      });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Guild loot share recorded.");
      await refreshCoreAndRender();
    }),
    button("Availability Reroll", "Use the Guild's once-per-adventure failed availability reroll for this item.", async () => {
      const result = await api("/api/campaign/tag/guild-availability-reroll", {
        method: "POST",
        body: JSON.stringify({ item_name: itemName.value, difficulty: 6, base_price_gp: Number(amount.value || 0) || null }),
      });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Guild availability reroll used.");
      await refreshCoreAndRender();
    }),
    button("Reset Reroll", "Reset the Guild availability reroll for the next adventure or monthly upkeep window.", async () => {
      const result = await api("/api/campaign/tag/finance-action", { method: "POST", body: JSON.stringify({ finance_action: "guild_availability_reroll_reset" }) });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Guild availability reroll reset.");
      await refreshCoreAndRender();
    })
  );
  finance.appendChild(financeRow);

  const members = card("Guild Jobs and Members", "Use this for Guild-specific character funding and for generating TAG Adventurers Guild job leads.");
  members.append(field("Character", actionCharacter));
  const memberRow = actions();
  memberRow.append(
    button("Pay Resurrection", "Pay a Level 2+ member's resurrection attempt from active Guild coffers. Enter the cost in Amount gp.", async () => {
      const result = await api("/api/campaign/tag/finance-action", {
        method: "POST",
        body: JSON.stringify({ character_id: actionCharacter.value, finance_action: "guild_resurrection_fund", amount_gp: Number(amount.value || 0) }),
      });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Guild resurrection funding logged.");
      await refreshCoreAndRender();
    }),
    button("Guild Job Lead", "Roll/create a playable TAG Guild Job module and install it into the Adventure list. Use this when the party accepts work from the Adventurers Guild.", async () => {
      const result = await api("/api/campaign/tag/create-adventure", { method: "POST", body: JSON.stringify({ lead_type: "guild_job", detail: "" }) });
      modernState.campaign = result.campaign;
      modernState.adventures = await api("/api/adventures");
      setStatus(`Created ${result.title}.`);
      await refreshCoreAndRender();
    })
  );
  members.appendChild(memberRow);
  const memberList = el("div", "modern-list");
  const memberIds = new Set(campaign.tag_troupe_member_character_ids || []);
  const activeIds = new Set(campaign.tag_troupe_active_character_ids || []);
  for (const character of modernState.characters.filter((item) => memberIds.has(item.id))) {
    const account = tagBankAccountForCharacter(character.id);
    memberList.appendChild(
      modernStatusRow(
        character.name,
        `${character.class_name} L${character.level} · ${activeIds.has(character.id) ? "active party" : "home"} · ${character.gold || 0} gp carried · TAG bank ${account?.gold_gp || 0} gp${account?.robbed ? " · bank robbed" : ""}`,
        "Guild member summary from the TAG troupe roster and TAG bank ledger."
      )
    );
  }
  if (!memberList.childElementCount) memberList.appendChild(el("p", "muted", "No troupe members are listed yet. Add members from Troupe Management before treating them as Guild members."));
  members.appendChild(memberList);

  const benefits = card("Guild Benefits / Obligations", "Printed Guild features currently exposed in the app.");
  const list = el("ul", "modern-check-list");
  [
    "5000 gp starting coffers when Guild membership starts.",
    "Adventure completion creates closeout prompts for 50% monetary loot share, upkeep, availability-reroll reset, and leaving-restriction signoff.",
    "Run Upkeep and Apply 50% Loot Share clear their matching closeout prompts automatically.",
    "Free Guild ledger deposits, equipment discount, martial arts training, cartographer bonus, resurrection funding, and availability reroll require active benefits and coffers above 0 gp.",
    "Guild Job Lead installs a playable Guild Job adventure module; Guild spell handling remains in TAG Actions during exploration.",
    "Leaving Guild membership is blocked while coffers are below 5000 gp; restore coffers first, then turn Guild active off.",
  ].forEach((text) => list.appendChild(el("li", "", text)));
  benefits.appendChild(list);
  const recent = card("Recent Guild Log", "Latest Guild finance, job, spell, and marker actions.");
  for (const entry of latestTagLogs(["guild_upkeep", "guild_loot_share", "guild_resurrection_fund", "guild_availability_reroll_reset", "guild_leaving_restriction", "guild_spell", "guild_marker_clear"])) {
    recent.appendChild(modernStatusRow(entry.action.replaceAll("_", " "), entry.result_text || "", "Recent TAG Guild log entry."));
  }
  if (recent.childElementCount <= 2) recent.appendChild(el("p", "muted", "No recent Guild log entries."));
  rootEl.append(panel, finance, members, renderCloseoutTasks("Guild Closeout", ["guild", "xp"]), benefits, recent);
}

function renderParties() {
  const create = card("Create Party", "Choose exactly four different roster heroes.");
  const name = input("text", "modern-party-name", "Name of this saved party.");
  create.appendChild(field("Party name", name));
  const picks = [];
  for (let i = 0; i < 4; i += 1) {
    const pick = characterSelect(`modern-party-member-${i}`, `Party slot ${i + 1}.`, `Slot ${i + 1}`);
    picks.push(pick);
    create.appendChild(field(`Slot ${i + 1}`, pick));
  }
  create.appendChild(button("Save Party", "Create a four-character party.", async () => {
    await api("/api/parties", { method: "POST", body: JSON.stringify({ name: name.value, character_ids: picks.map((item) => item.value) }) });
    setStatus("Party saved.");
    await refreshCoreAndRender();
  }, ""));
  const list = card("Saved Parties", "Review, heal, bank, or delete saved parties.");
  const listActions = actions();
  listActions.append(
    button("Expand All", "Expand all saved party details.", async () => {
      list.querySelectorAll("details").forEach((item) => { item.open = true; });
    }),
    button("Collapse All", "Collapse all saved party details.", async () => {
      list.querySelectorAll("details").forEach((item) => { item.open = false; });
    })
  );
  list.appendChild(listActions);
  for (const party of modernState.parties) {
    const row = document.createElement("details");
    row.className = "modern-row";
    const summary = document.createElement("summary");
    const members = (party.character_ids || []).map((id) => modernState.characters.find((c) => c.id === id)).filter(Boolean);
    summary.textContent = `${party.name} - ${members.map((member) => member.name).join(", ") || "empty"}`;
    row.appendChild(summary);
    const detail = el("div", "modern-stack");
    for (const member of members) {
      detail.appendChild(el("span", "muted", `${member.name}: ${member.class_name} L${member.level}, HP ${member.current_life}/${member.max_life}, XP ${member.xp || 0}, carried ${member.gold || 0}gp, TAG bank ${tagBankForCharacter(member.id)}gp, ${member.clues || 0} Clues`));
    }
    row.appendChild(detail);
    const rowActions = actions();
    rowActions.append(
      button("Heal Party", "Restore every party member to full Life.", async () => {
        await api(`/api/parties/${party.id}/heal`, { method: "POST" });
        setStatus("Party healed.");
        await refreshCoreAndRender();
      }),
      button("Bank Party Gold", "Move each party member's roster gold into TAG bank accounts without a deposit fee. Use only when TAG banking is enabled for your campaign.", async () => {
        for (const memberId of party.character_ids || []) {
          await api("/api/campaign/tag/bank-migration", { method: "POST", body: JSON.stringify({ character_id: memberId, include_legacy_bank: false, apply_deposit_fee: false, note: `Modern party banking: ${party.name}` }) });
        }
        setStatus("Party roster gold moved to TAG bank accounts.");
        await refreshCoreAndRender();
      }),
      button("Delete", "Delete this saved party.", async () => {
        if (!window.confirm(`Delete ${party.name}?`)) return;
        await api(`/api/parties/${party.id}`, { method: "DELETE" });
        setStatus("Party deleted.");
        await refreshCoreAndRender();
      })
    );
    row.appendChild(rowActions);
    list.appendChild(row);
  }
  rootEl.append(create, list);
}

async function renderEquipment() {
  if (!modernState.equipmentRows.length) {
    const payload = await api("/api/rules/equipment-shop");
    modernState.equipmentRows = payload.items || Object.values(payload).flat().filter((item) => item && item.key && item.name);
  }
  const panel = card("Equipment Shop", "Select a character, choose an item, then buy or sell using existing backend shop rules.");
  const buyerFilters = characterFilterControls("modern-shop-buyer", () => updateCharacterSelect(buyer, "Choose buyer", { search: buyerFilters.search.value, classId: buyerFilters.classFilter.value, sort: buyerFilters.sort.value }));
  const buyer = characterSelect("modern-shop-buyer", "Character buying or selling equipment.", "Choose buyer");
  const buyerSummary = el("p", "modern-home-status", "Choose a buyer to show carried gold and TAG bank balance.");
  buyer.addEventListener("change", () => {
    const character = modernState.characters.find((item) => item.id === buyer.value);
    buyerSummary.textContent = character ? `${character.name}: carried ${character.gold || 0}gp · TAG bank ${tagBankForCharacter(character.id)}gp · inventory ${(character.inventory || []).length} item(s).` : "Choose a buyer to show carried gold and TAG bank balance.";
  });
  const itemPicker = searchablePicker(
    "modern-shop-item",
    "Equipment",
    "Equipment item to buy.",
    modernState.equipmentRows,
    (row) => `${row.name} - ${row.price_gp ?? row.cost_gp ?? 0}gp`,
    (row) => `${row.name} ${row.key} ${row.category || ""} ${row.price_gp ?? row.cost_gp ?? ""}`,
    null,
    { sortOptions: [["name", "Name"], ["price", "Price"], ["class", "Category"]], blank: "Choose equipment" }
  );
  const qty = input("number", "modern-shop-qty", "Quantity to buy.", "1");
  const sellItem = input("text", "modern-shop-sell", "Exact inventory item name to sell.");
  panel.append(buyerFilters.panel, field("Buyer", buyer), buyerSummary, itemPicker.wrap, field("Quantity", qty), field("Sell item", sellItem));
  const row = actions();
  row.append(
    button("Buy", "Buy selected equipment for the selected character.", async () => {
      if (!buyer.value) throw new Error("Choose a buyer.");
      if (!itemPicker.picker.value) throw new Error("Choose equipment.");
      await api(`/api/characters/${buyer.value}/buy-equipment`, { method: "POST", body: JSON.stringify({ item_key: itemPicker.picker.value, quantity: Number(qty.value || 1) }) });
      setStatus("Equipment bought.");
      await refreshCoreAndRender();
    }, ""),
    button("Sell", "Sell the named item from the selected character's inventory.", async () => {
      if (!buyer.value) throw new Error("Choose a seller.");
      await api(`/api/characters/${buyer.value}/sell-item`, { method: "POST", body: JSON.stringify({ item_name: sellItem.value }) });
      setStatus("Item sold.");
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  rootEl.appendChild(panel);
}

function renderBanking() {
  const panel = card("TAG Banking and Finance", "Bank accounts, hidden treasure troves, robbery recovery, and Guild finance.");
  const filters = characterFilterControls("modern-finance", () => updateCharacterSelect(character, "Choose character", { search: filters.search.value, classId: filters.classFilter.value, sort: filters.sort.value }));
  const character = characterSelect("modern-finance-character", "Character used for TAG finance actions.", "Choose character");
  const amount = input("number", "modern-finance-amount", "Gold amount for banking or storage.", "0");
  const item = input("text", "modern-finance-item", "Optional hidden trove item, inheritance heir, or finance note.");
  const party = select("modern-finance-party", "Party for party-level banking.", partyOptions("Choose party"));
  const balance = el("p", "modern-home-status", "Choose a character to show carried gold, TAG bank, party, and troupe status.");
  character.addEventListener("change", () => {
    const selected = modernState.characters.find((row) => row.id === character.value);
    const account = selected ? tagBankAccountForCharacter(selected.id) : null;
    balance.textContent = selected
      ? `${selected.name}: carried ${selected.gold || 0}gp · TAG bank ${account?.gold_gp || 0}gp${account?.robbed ? " · robbed" : ""} · parties ${partyNamesForCharacter(selected.id).join(", ") || "none"} · ${(modernState.campaign?.tag_troupe_member_character_ids || []).includes(selected.id) ? "in TAG troupe" : "not in TAG troupe"}`
      : "Choose a character to show carried gold, TAG bank, party, and troupe status.";
  });
  panel.append(filters.panel, field("Character", character), balance, field("Amount gp", amount), field("Item / heir / note", item), field("Party", party));
  const row = actions();
  row.append(
    button("Deposit TAG Bank", "Deposit gp into selected character's TAG bank account; active Guild ledger deposits are free, otherwise the TAG bank fee applies.", async () => tagFinance(character.value, "bank_deposit", amount.value, item.value), ""),
    button("Withdraw TAG Bank", "Withdraw gp from selected character's TAG bank account to carried roster gold.", async () => tagFinance(character.value, "bank_withdraw", amount.value, item.value)),
    button("Bank Robbery Risk", "Roll bank robbery risk for the selected character and mark their TAG bank account robbed if the roll fails.", async () => tagFinance(character.value, "robbery_risk", amount.value, item.value)),
    button("Inheritance Note", "Record the selected character's TAG bank heir name in the note field. Inheritance transfers apply the printed 20% tax.", async () => tagFinance(character.value, "inheritance", amount.value, item.value)),
    button("Inheritance Transfer", "Transfer a matching inherited TAG bank account to this character after the 20% inheritance tax.", async () => tagFinance(character.value, "inheritance_transfer", amount.value, item.value)),
    button("Loan Enforcement", "Roll/log moneylender pursuit or enforcement for the amount entered.", async () => tagFinance(character.value, "loan_enforcement", amount.value, item.value)),
    button("Hide Treasure", "Hide gold or item in the TAG hidden treasure trove.", async () => {
      await api("/api/campaign/tag/store-treasure", { method: "POST", body: JSON.stringify({ character_id: character.value, storage: "trove", gold_gp: Number(amount.value || 0), item_name: item.value, quantity: 1 }) });
      setStatus("Hidden trove updated.");
      await refreshCoreAndRender();
    }),
    button("Roll Trove Risk", "Roll 3d6 hidden treasure trove theft risk.", async () => {
      const result = await api("/api/campaign/tag/hidden-trove-risk", { method: "POST" });
      setStatus(result.entry?.result_text || "Trove risk rolled.");
      await refreshCoreAndRender();
    }),
    button("Recover Trove", "Spend 4 Clues and roll Interrogation vs L6 to recover stolen hidden treasure.", async () => {
      const result = await api("/api/campaign/tag/hidden-trove-recovery", { method: "POST", body: JSON.stringify({ character_id: character.value }) });
      setStatus(result.entry?.result_text || "Trove recovery resolved.");
      await refreshCoreAndRender();
    }),
    button("Recover Bank Robbery", "Spend 3 Clues and create the Bandit Hideout adventure lead.", async () => {
      const result = await api("/api/campaign/tag/bank-robbery-recovery", { method: "POST", body: JSON.stringify({ character_id: character.value }) });
      setStatus(result.adventure ? `Created ${result.adventure.title}.` : result.entry?.result_text || "Bank robbery recovery resolved.");
      await refreshCoreAndRender();
    }),
    button("Bank All Roster Gold", "Move all roster gold into TAG bank accounts without applying the deposit fee by default.", async () => {
      await api("/api/campaign/tag/bank-migration", { method: "POST", body: JSON.stringify({ character_id: "", include_legacy_bank: false, apply_deposit_fee: false, note: "Modern banking page bulk conversion" }) });
      setStatus("Roster gold moved to TAG bank accounts.");
      await refreshCoreAndRender();
    }),
    button("Bank Troupe Gold", "Move current TAG troupe members' roster gold into TAG bank accounts without applying the deposit fee.", async () => {
      for (const id of troupeMemberIds()) {
        await api("/api/campaign/tag/bank-migration", { method: "POST", body: JSON.stringify({ character_id: id, include_legacy_bank: false, apply_deposit_fee: false, note: "Modern troupe banking" }) });
      }
      setStatus("Troupe roster gold moved to TAG bank accounts.");
      await refreshCoreAndRender();
    }),
    button("Bank Party Gold", "Move selected party members' roster gold into TAG bank accounts without applying the deposit fee.", async () => {
      const selectedParty = modernState.parties.find((row) => row.id === party.value);
      if (!selectedParty) throw new Error("Choose a party.");
      for (const id of selectedParty.character_ids || []) {
        await api("/api/campaign/tag/bank-migration", { method: "POST", body: JSON.stringify({ character_id: id, include_legacy_bank: false, apply_deposit_fee: false, note: `Modern finance party banking: ${selectedParty.name}` }) });
      }
      setStatus("Party roster gold moved to TAG bank accounts.");
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  const ledger = card("TAG Bank Ledger", "Per-character TAG bank accounts. Robbed accounts can be recovered with 3 Clues, then the app creates the Bandit Hideout lead.");
  const accounts = modernState.campaign?.tag_bank_accounts || [];
  for (const account of accounts) {
    ledger.appendChild(
      modernStatusRow(
        account.owner_name || "Account",
        `${account.gold_gp || 0} gp${account.robbed ? " · robbed" : ""}${account.heir_name ? ` · heir ${account.heir_name}` : ""}${account.notes ? ` · ${account.notes}` : ""}`,
        "TAG bank ledger entry. Use Recover Bank Robbery if this account is marked robbed."
      )
    );
  }
  if (!accounts.length) ledger.appendChild(el("p", "muted", "No TAG bank accounts yet. Deposit or bank roster gold to create accounts."));

  const trove = card("Hidden Treasure Trove", "Hidden trove storage and theft recovery state.");
  const stolenItems = modernState.campaign?.tag_hidden_trove_stolen_items || [];
  trove.appendChild(
    modernStatusRow(
      modernState.campaign?.tag_hidden_trove_robbed ? "Stolen trove pending recovery" : "Trove currently safe",
      `Stored ${modernState.campaign?.tag_storage_gold_gp || 0} gp · stolen ${modernState.campaign?.tag_hidden_trove_stolen_gold_gp || 0} gp · stolen item stack(s) ${stolenItems.length}`,
      "Roll Trove Risk between adventures when prompted. Recover Trove spends 4 Clues and rolls Interrogation vs L6."
    )
  );
  for (const stored of modernState.campaign?.tag_stored_items || []) {
    trove.appendChild(modernStatusRow(stored.item_name || "Stored item", `${stored.quantity || 1} stored for ${stored.owner_name || "party"}`, "Hidden trove stored item."));
  }

  const recent = card("Recent Finance Log", "Latest TAG banking, robbery, storage, inheritance, loan, and Guild finance entries.");
  for (const entry of latestTagLogs(["bank_deposit", "bank_withdraw", "bank_inheritance", "bank_inheritance_transfer", "bank_robbery_risk", "bank_robbery_recovery", "tag_bank_migration", "hidden_trove_risk", "hidden_trove_recovery", "loan_enforcement", "guild_loot_share", "guild_upkeep"])) {
    recent.appendChild(modernStatusRow(entry.action.replaceAll("_", " "), entry.result_text || "", "Recent TAG finance log entry."));
  }
  if (recent.childElementCount <= 2) recent.appendChild(el("p", "muted", "No recent finance log entries."));
  rootEl.append(panel, ledger, trove, renderCloseoutTasks("Finance Closeout", ["finance", "storage"]), recent);
}

async function tagFinance(characterId, action, amount, note = "") {
  if (!characterId) throw new Error("Choose a character.");
  const result = await api("/api/campaign/tag/finance-action", { method: "POST", body: JSON.stringify({ character_id: characterId, finance_action: action, amount_gp: Number(amount || 0), note }) });
  setStatus(result.entry?.result_text || "Finance action logged.");
  await refreshCoreAndRender();
}

async function renderSettlement() {
  if (!modernState.equipmentRows.length) {
    const payload = await api("/api/rules/equipment-shop");
    modernState.equipmentRows = payload.items || Object.values(payload).flat().filter((item) => item && item.key && item.name);
  }
  const campaign = modernState.campaign || {};
  const panel = card("Settlement", "A TAG settlement is a town/village downtime hub, separate from the Camp outside the dungeon. Settlement size modifies availability checks.");
  const name = input("text", "modern-settlement-name-page", "TAG home settlement name.", campaign.settlement_name || "Home Settlement");
  const size = select("modern-settlement-size-page", "Settlement size modifier.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
  size.value = String(campaign.settlement_size ?? 0);
  const notes = textarea("modern-settlement-notes", "Settlement notes.", 4);
  notes.value = campaign.settlement_notes || "";
  const servicePayload = await api("/api/campaign/tag/services");
  const availabilityRows = [...modernState.equipmentRows, ...(servicePayload.services || [])];
  const availabilityPicker = searchablePicker(
    "modern-availability-item",
    "Availability item",
    "Equipment or service to check in this settlement.",
    availabilityRows,
    (row) => `${row.name || row.key}${row.price_gp != null ? ` - ${row.price_gp}gp` : ""}`,
    (row) => `${row.name || ""} ${row.key || ""} ${row.category || ""} ${row.summary || ""}`,
    null,
    { sortOptions: [["name", "Name"], ["price", "Price"], ["class", "Category"]], blank: "Choose item/service" }
  );
  panel.append(field("Settlement", name), field("Size", size), field("Notes", notes), availabilityPicker.wrap);
  const row = actions();
  row.append(
    button("Save Settlement", "Save settlement name, size, and notes.", async () => {
      modernState.campaign = await api("/api/campaign", { method: "PUT", body: JSON.stringify({ settlement_name: name.value, settlement_size: Number(size.value), settlement_notes: notes.value }) });
      setStatus("Settlement saved.");
      await refreshCoreAndRender();
    }, ""),
    button("Create Settlement", "Create or update this named settlement and select it as current.", async () => {
      const result = await api("/api/campaign/tag/settlement", { method: "POST", body: JSON.stringify({ action: "create", name: name.value, size: Number(size.value), notes: notes.value }) });
      modernState.campaign = result.campaign;
      setStatus(`Settlement ${result.settlement?.name || name.value} saved.`);
      await refreshCoreAndRender();
    }),
    button("Roll Size", "Roll a random TAG settlement size.", async () => {
      const result = await api("/api/campaign/settlement/roll-size", { method: "POST" });
      setStatus(`Settlement size rolled ${result.roll}.`);
      await refreshCoreAndRender();
    }),
    button("Check Availability", "Roll d6 plus settlement size against difficulty 6.", async () => {
      const itemName = availabilityPicker.picker.selectedOptions[0]?.textContent || availabilityPicker.picker.value || "";
      const result = await api("/api/campaign/tag/availability", { method: "POST", body: JSON.stringify({ item_name: itemName, difficulty: 6 }) });
      setStatus(result.check?.result_text || "Availability checked.");
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  const list = card("Known Settlements", "Create, select, travel to, or delete TAG settlements tracked in this campaign.");
  for (const settlement of campaign.tag_settlements || []) {
    const item = el("div", "modern-row");
    const troupeHere = settlement.name === campaign.settlement_name ? campaign.tag_troupe_name || "Current troupe" : "No troupe currently focused here";
    item.append(el("strong", "", `${settlement.name} (${settlement.size >= 0 ? "+" : ""}${settlement.size})`), el("span", "muted", `${troupeHere} · ${settlement.notes || "No notes"}`));
    const itemActions = actions();
    itemActions.append(
      button("Select", "Make this the current TAG settlement.", async () => {
        const result = await api("/api/campaign/tag/settlement", { method: "POST", body: JSON.stringify({ action: "select", settlement_id: settlement.id }) });
        modernState.campaign = result.campaign;
        setStatus(`${settlement.name} selected.`);
        await refreshCoreAndRender();
      }),
      button("Travel To", "Travel to this settlement and roll TAG travel days/size.", async () => {
        const result = await api("/api/campaign/tag/travel-settlement", { method: "POST", body: JSON.stringify({ destination_name: settlement.name, use_hex_map: false, pay_road_tithe: false }) });
        modernState.campaign = result.campaign;
        setStatus(result.entry?.result_text || "Travel logged.");
        await refreshCoreAndRender();
      }),
      button("Delete", "Delete this settlement from the tracked settlement list. Current settlement state is preserved if this is the last settlement.", async () => {
        if (!window.confirm(`Delete settlement ${settlement.name}?`)) return;
        const result = await api("/api/campaign/tag/settlement", { method: "POST", body: JSON.stringify({ action: "delete", settlement_id: settlement.id }) });
        modernState.campaign = result.campaign;
        setStatus(result.deleted ? "Settlement deleted." : "Settlement not found.");
        await refreshCoreAndRender();
      })
    );
    item.appendChild(itemActions);
    list.appendChild(item);
  }
  rootEl.append(panel, list);
}

function renderCampaign() {
  const panel = card("Campaign Management", "Placeholder page for world, hex map, and settlement-map campaign tools.");
  panel.appendChild(el("p", "modern-home-status in-progress", "In progress: create world, hex map editor, settlement list, and settlement placement."));
  rootEl.appendChild(panel);
}

function renderSettings() {
  const prefs = readModernPrefs();
  const panel = card("Settings / Options", "Save dashboard preferences for starting adventures. These preferences are used by Go Adventure.");
  const tag = input("checkbox", "modern-tag-banking", "Use TAG banking instead of legacy-only home bank.");
  tag.checked = Boolean(modernState.campaign?.tag_banking_enabled);
  const defaultProfile = select("modern-rules-profile", "Default ruleset profile for random adventures.", modernState.rulesProfiles.map((p) => [p.id, p.label]));
  defaultProfile.value = prefs.defaultRulesetProfile || "ee_random";
  const mapMode = select("modern-default-map-mode", "Default map mode.", [["unlimited", "Unlimited"], ["paper", "Paper 20x28"]]);
  mapMode.value = prefs.defaultMapMode || "unlimited";
  const mapLimit = input("number", "modern-default-map-limit", "Default unlimited-map element cap before end-boss pressure.", String(prefs.defaultMapLimit || 60));
  const xp = select("modern-default-xp-system", "Default XP system.", [["classical", "Classical"], ["slow_and_sure", "Slow and Sure"], ["old_school", "Old School"], ["slower_advancement", "Slower Advancement"]]);
  xp.value = prefs.defaultXpSystem || "classical";
  panel.append(field("TAG banking", tag), field("Default random ruleset", defaultProfile), field("Default map mode", mapMode), field("Default map limit", mapLimit), field("XP system", xp));
  const rulesCard = card("Enabled Rulesets", "Choose which ruleset profiles appear as preferred options on Go Adventure. This does not delete content or rules data.");
  for (const profile of modernState.rulesProfiles) {
    const checkbox = input("checkbox", `modern-enabled-ruleset-${profile.id}`, `Enable ${profile.label} in the modern dashboard.`);
    const enabled = prefs.enabledRulesets ? prefs.enabledRulesets.includes(profile.id) : true;
    checkbox.checked = enabled;
    rulesCard.appendChild(field(profile.label, checkbox));
  }
  panel.appendChild(button("Save Preferences", "Save TAG banking and dashboard defaults.", async () => {
    modernState.campaign = await api("/api/campaign", { method: "PUT", body: JSON.stringify({ tag_banking_enabled: tag.checked }) });
    const enabledRulesets = modernState.rulesProfiles
      .filter((profile) => document.getElementById(`modern-enabled-ruleset-${profile.id}`)?.checked)
      .map((profile) => profile.id);
    writeModernPrefs({
      defaultRulesetProfile: defaultProfile.value,
      defaultMapMode: mapMode.value,
      defaultMapLimit: Number(mapLimit.value || 60),
      defaultXpSystem: xp.value,
      enabledRulesets,
    });
    setStatus("Settings saved.");
    await refreshCoreAndRender();
  }, ""));
  rootEl.append(panel, rulesCard);
}

function renderAiAdventures() {
  const panel = card("AI Adventure Generation", "Workflow: generate an external-AI prompt, paste or load the returned adventure JSON, validate it, then import it as a playable module.");
  const theme = input("text", "modern-ai-theme", "Theme for the AI adventure prompt.");
  const promptBox = textarea("modern-ai-prompt", "Generated prompt/export token text. Send this to your AI tool.", 8);
  const json = textarea("modern-ai-json", "Paste AI adventure JSON to validate or import.", 10);
  const file = input("file", "modern-ai-file", "Import adventure JSON from a .json file. Zip import remains a planned developer feature.");
  file.accept = ".json,application/json";
  file.addEventListener("change", async () => {
    const selected = file.files?.[0];
    if (!selected) return;
    json.value = await selected.text();
    setStatus(`Loaded ${selected.name} into Adventure JSON.`);
  });
  panel.append(field("Theme", theme), field("Prompt / export token", promptBox), field("Adventure JSON", json), field("Import file", file));
  const row = actions();
  row.append(
    button("Generate Prompt", "Generate an external-LLM prompt for this theme.", async () => {
      const result = await api("/api/adventures/ai/prompt", {
        method: "POST",
        body: JSON.stringify({
          theme: theme.value || "dungeon",
          difficulty: "standard",
          length: "short",
          style: "grim",
          environment: "dungeon",
          boss_type: "random",
          party_level_min: 1,
          party_level_max: 3,
        }),
      });
      promptBox.value = result.prompt || "";
      setStatus("Prompt generated into the text area.");
    }, ""),
    button("Validate JSON", "Validate pasted AI adventure JSON.", async () => {
      const result = await api("/api/adventures/validate", { method: "POST", body: JSON.stringify({ manifest: JSON.parse(json.value) }) });
      setStatus(result.valid ? "Adventure JSON valid." : `Invalid: ${(result.errors || []).join("; ")}`);
    }),
    button("Import JSON", "Import pasted AI adventure JSON as an installed module.", async () => {
      const result = await api("/api/adventures/import", { method: "POST", body: JSON.stringify({ manifest: JSON.parse(json.value), overwrite: false }) });
      setStatus(result.message || "Adventure imported.");
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  const list = card("Installed AI Adventures", "Manage installed AI-authored modules.");
  for (const adventure of modernState.adventures.filter((item) => String(item.id || "").startsWith("ai-"))) {
    const item = el("div", "modern-row");
    item.append(el("strong", "", adventure.title || adventure.id), el("span", "muted", `${adventure.id} · ${adventure.room_count || 0} room(s)`));
    const itemActions = actions();
    itemActions.append(
      link("Export JSON", `/api/adventures/${encodeURIComponent(adventure.id)}/export`, "Export this adventure manifest as JSON."),
      link("Export ZIP", `/api/adventures/${encodeURIComponent(adventure.id)}/export.zip`, "Export this adventure as a zip package."),
      button("Delete", "Delete this installed AI adventure module.", async () => {
        if (!window.confirm(`Delete ${adventure.title || adventure.id}?`)) return;
        await api(`/api/adventures/${encodeURIComponent(adventure.id)}`, { method: "DELETE" });
        setStatus("AI adventure deleted.");
        await refreshCoreAndRender();
      })
    );
    item.appendChild(itemActions);
    list.appendChild(item);
  }
  if (!list.querySelector(".modern-row")) list.appendChild(el("p", "muted", "No installed AI adventure modules."));
  rootEl.append(panel, list);
}

function renderGoAdventure() {
  const prefs = readModernPrefs();
  const panel = card("Start Adventure", "Choose party, adventure type, module, ruleset, and start play.");
  const party = select("modern-start-party", "Party to send on the adventure.", partyOptions());
  party.value = prefs.lastPartyId || "";
  const type = select("modern-adventure-type", "Adventure type filter.", [["random", "Random"], ["imported", "Imported Adventure Module"], ["ai", "AI Adventure Module"]]);
  const adventure = select("modern-start-adventure", "Specific adventure module, or Random Dungeon.", adventureOptions("random"));
  const enabledRulesets = prefs.enabledRulesets || modernState.rulesProfiles.map((profile) => profile.id);
  const profileRows = modernState.rulesProfiles.filter((profile) => enabledRulesets.includes(profile.id));
  const profile = select("modern-start-profile", "Ruleset profile used only for Random adventures.", profileRows.map((p) => [p.id, p.label]));
  profile.value = prefs.defaultRulesetProfile || "ee_random";
  const xp = select("modern-start-xp", "XP system for this adventure.", [["classical", "Classical"], ["slow_and_sure", "Slow and Sure"], ["old_school", "Old School"], ["slower_advancement", "Slower Advancement"]]);
  xp.value = prefs.defaultXpSystem || "classical";
  const mapMode = select("modern-start-map-mode", "Map mode for this adventure.", [["unlimited", "Unlimited"], ["paper", "Paper 20x28"]]);
  mapMode.value = prefs.defaultMapMode || "unlimited";
  const mapLimit = input("number", "modern-start-map-limit", "Unlimited-map element cap before end-boss pressure.", String(prefs.defaultMapLimit || 60));
  panel.append(field("Party", party), field("Adventure type", type), field("Adventure/module", adventure), field("Random ruleset", profile), field("XP system", xp), field("Map mode", mapMode), field("Map limit", mapLimit));
  type.addEventListener("change", () => {
    adventure.replaceChildren(...optionRows(adventureOptions(type.value)));
    profile.closest("label")?.classList.toggle("hidden", type.value !== "random");
  });
  profile.closest("label")?.classList.toggle("hidden", type.value !== "random");
  panel.appendChild(button("Start Adventure", "Create a new session with the selected party and adventure settings.", async () => {
    if (!party.value) throw new Error("Choose a party.");
    writeModernPrefs({ lastPartyId: party.value, defaultRulesetProfile: profile.value, defaultXpSystem: xp.value, defaultMapMode: mapMode.value, defaultMapLimit: Number(mapLimit.value || 60) });
    const adventureId = type.value === "random" ? "random" : adventure.value;
    const session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({
        party_id: party.value,
        adventure_id: adventureId,
        ruleset_profile_id: type.value === "random" ? profile.value : "ee_random",
        xp_system: xp.value,
        map_bounds_mode: mapMode.value,
        unlimited_map_element_cap: Number(mapLimit.value || 60),
      }),
    });
    window.location.href = `/?session=${encodeURIComponent(session.id || "")}`;
  }, ""));
  const sessions = card("Resume / Saved Games", "Resume active games, load saved games, or delete old sessions.");
  for (const session of [...modernState.sessions].sort((a, b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")))) {
    const partyName = modernState.parties.find((item) => item.id === session.party_id)?.name || session.party_id;
    const row = el("div", "modern-row");
    row.append(el("strong", "", session.save_label || `${partyName} - ${session.mode}`));
    row.append(el("span", "muted", `${partyName} · ${session.adventure_type || session.adventure_id} · ${session.saved_at ? `saved ${session.saved_at}` : "active/unsaved"} · ${session.tile_count || 0} map element(s)`));
    const rowActions = actions();
    rowActions.append(
      button(session.saved_at ? "Load Saved Game" : "Resume Adventure", "Open this session in the main play interface.", async () => {
        window.location.href = `/?session=${encodeURIComponent(session.id)}`;
      }, ""),
      button("Delete", "Delete this saved/active session and unlock its characters.", async () => {
        if (!window.confirm("Delete this session?")) return;
        await api(`/api/sessions/${encodeURIComponent(session.id)}`, { method: "DELETE" });
        setStatus("Session deleted.");
        await refreshCoreAndRender();
      })
    );
    row.appendChild(rowActions);
    sessions.appendChild(row);
  }
  if (!modernState.sessions.length) sessions.appendChild(el("p", "muted", "No active or saved sessions."));
  rootEl.append(panel, sessions);
}

async function renderRulesReference() {
  if (!modernState.rulesReference.length) {
    const payload = await api("/api/rules/reference");
    modernState.rulesReference = Array.isArray(payload) ? payload : (payload.entries || []);
  }
  const panel = card("Rules Reference", "Search every curated implementation reference entry from the app reference index.");
  const search = input("search", "modern-rules-search", "Filter rules reference entries.");
  const categories = [...new Set(modernState.rulesReference.map((entry) => entry.category || "rules"))].sort();
  const category = select("modern-rules-category", "Filter by rules category.", [["", "All categories"], ...categories.map((item) => [item, item])]);
  const statuses = [...new Set(modernState.rulesReference.map((entry) => entry.implementation_status || "reference"))].sort();
  const status = select("modern-rules-status", "Filter by implementation status.", [["", "All statuses"], ...statuses.map((item) => [item, modernStatusLabel(item)])]);
  const source = select("modern-rules-source", "Filter entries by whether they cite a printed source page.", [["", "All source refs"], ["with", "With source page"], ["app", "App-only / no source page"]]);
  const sort = select("modern-rules-sort", "Sort rules reference entries.", [["category", "Category"], ["title", "Title"], ["implementation_status", "Status"], ["source_page", "Source page"]]);
  const results = el("div", "modern-list");
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Category", category), field("Status", status), field("Source", source), field("Sort", sort));
  const rowActions = actions();
  rowActions.append(
    button("Expand All", "Open every visible rules reference card.", async () => {
      results.querySelectorAll("details").forEach((item) => { item.open = true; });
    }),
    button("Collapse All", "Close every visible rules reference card.", async () => {
      results.querySelectorAll("details").forEach((item) => { item.open = false; });
    })
  );
  panel.append(controls, rowActions, results);
  const draw = () => {
    results.replaceChildren();
    const needle = search.value.toLowerCase();
    const rows = modernState.rulesReference
      .filter((entry) => !category.value || (entry.category || "rules") === category.value)
      .filter((entry) => !status.value || (entry.implementation_status || "reference") === status.value)
      .filter((entry) => source.value !== "with" || Boolean(entry.source_page))
      .filter((entry) => source.value !== "app" || !entry.source_page)
      .filter((entry) => `${entry.title} ${entry.summary || ""} ${entry.body} ${entry.category || ""} ${entry.implementation_status || ""} ${entry.source_page || ""} ${(entry.keywords || []).join(" ")}`.toLowerCase().includes(needle))
      .sort((a, b) => String(a[sort.value] || "").localeCompare(String(b[sort.value] || ""), undefined, { numeric: true }) || String(a.title || "").localeCompare(String(b.title || "")));
    const byCategory = rows.reduce((groups, entry) => {
      const key = entry.category || "rules";
      if (!groups[key]) groups[key] = [];
      groups[key].push(entry);
      return groups;
    }, {});
    const summary = el("p", "muted", `${rows.length} matching rule reference entr${rows.length === 1 ? "y" : "ies"} across ${Object.keys(byCategory).length} categor${Object.keys(byCategory).length === 1 ? "y" : "ies"}.`);
    results.appendChild(summary);
    for (const [groupName, items] of Object.entries(byCategory).sort(([a], [b]) => a.localeCompare(b))) {
      const group = document.createElement("details");
      group.className = "modern-row modern-reference-group";
      group.open = rows.length <= 25 || Boolean(search.value);
      const groupSummary = document.createElement("summary");
      groupSummary.title = `Show or hide ${items.length} ${groupName} reference entries.`;
      groupSummary.append(el("strong", "", modernTitleFromKey(groupName)), el("span", "muted", `${items.length} entr${items.length === 1 ? "y" : "ies"}`));
      group.appendChild(groupSummary);
      const groupBody = el("div", "modern-reference-group-body");
      for (const item of items) {
        const row = document.createElement("details");
        row.className = "modern-row modern-reference-card";
        row.open = rows.length <= 8;
        const rowSummary = document.createElement("summary");
        rowSummary.title = "Show or hide the full implementation note for this rule reference.";
        rowSummary.append(
          el("strong", "", item.title || item.id),
          el("span", "muted", `${modernStatusLabel(item.implementation_status)}${item.source_page ? ` · p.${item.source_page}` : ""}`)
        );
        row.appendChild(rowSummary);
        if (item.summary) row.appendChild(el("p", "modern-home-status", item.summary));
        if (item.keywords?.length) row.appendChild(el("span", "muted", item.keywords.join(" · ")));
        if (item.body) {
          const body = el("div", "modern-reference-body");
          item.body.split("\n").filter((line) => line.trim()).forEach((line) => body.appendChild(el("p", "", line)));
          row.appendChild(body);
        }
        groupBody.appendChild(row);
      }
      group.appendChild(groupBody);
      results.appendChild(group);
    }
    if (!rows.length) {
      results.appendChild(
        el(
          "p",
          "modern-home-status in-progress",
          "No matching rules reference entries. Clear filters or search by rule name, implementation status, keyword, source page, or body text."
        )
      );
    }
  };
  search.addEventListener("input", draw);
  category.addEventListener("change", draw);
  status.addEventListener("change", draw);
  source.addEventListener("change", draw);
  sort.addEventListener("change", draw);
  draw();
  rootEl.appendChild(panel);
}

function modernTableRowCount(value) {
  if (Array.isArray(value)) return value.length;
  if (value && typeof value === "object") return Object.keys(value).length;
  return 0;
}

function modernTableRows(value) {
  return Array.isArray(value)
    ? value
    : Object.entries(value || {}).map(([key, row]) => (row && typeof row === "object" && !Array.isArray(row) ? { key, ...row } : { key, value: row }));
}

function modernTableFamily(key) {
  if (key.startsWith("abyss_")) return "Four Against the Abyss";
  if (key.startsWith("fd_") || key.startsWith("forsaken_depths_")) return "Forsaken Depths";
  if (key.startsWith("courtship_")) return "Courtship of Flower Demons";
  if (key.startsWith("fungal_")) return "Fungal Grottoes";
  if (key.startsWith("caverns_")) return "Caverns";
  if (key.startsWith("fiendish_")) return "Fiendish Foes";
  if (key.includes("spell")) return "Spells";
  if (key.includes("skill") || key.includes("class")) return "Classes and advancement";
  if (key.includes("monster") || key.includes("reaction") || key.includes("vermin") || key.includes("minion") || key.includes("boss") || key.includes("weird") || key.includes("horde")) return "Monsters and reactions";
  if (key.includes("map") || key.includes("room") || key.includes("door") || key.includes("trap") || key.includes("treasure") || key.includes("search") || key.includes("quest")) return "Dungeon and exploration";
  if (key.includes("equipment") || key.includes("hireling") || key.includes("economy") || key.includes("hidden") || key.includes("icon")) return "Equipment, economy, and app registries";
  return "Expanded Edition and app tables";
}

function modernTablePreview(value, needle = "") {
  const rows = Array.isArray(value)
    ? value
    : modernTableRows(value);
  const visibleRows = needle
    ? rows.filter((row) => modernSearchText(row).toLowerCase().includes(needle))
    : rows;
  const box = el("div", "modern-list-tall");
  if (!visibleRows.length) {
    box.appendChild(el("p", "muted", "No rows in this table match the current search."));
    return box;
  }
  for (const row of visibleRows.slice(0, 250)) {
    const line = el("div", "modern-row");
    if (row && typeof row === "object") {
      const title = row.name || row.title || row.roll || row.key || row.id || row.table || "row";
      const detail = Object.entries(row)
        .map(([key, val]) => `${key}: ${Array.isArray(val) ? val.join(", ") : String(val)}`)
        .join(" | ");
      line.append(el("strong", "", String(title)), el("span", "muted", detail));
    } else {
      line.append(el("span", "", String(row)));
    }
    box.appendChild(line);
  }
  if (visibleRows.length > 250) box.appendChild(el("p", "muted", `Showing first 250 of ${visibleRows.length} matching rows. Use search to narrow this table.`));
  return box;
}

async function renderTables() {
  if (!Object.keys(modernState.tables).length) modernState.tables = await api("/api/rules/tables");
  const panel = card("Tables List", "Search every structured rules and app table exposed by the game.");
  const search = input("search", "modern-table-search", "Search by table name or entry text.");
  const families = [...new Set(Object.keys(modernState.tables).map(modernTableFamily))].sort();
  const family = select("modern-table-family", "Filter by table family.", [["", "All table families"], ...families.map((item) => [item, item])]);
  const sort = select("modern-table-sort", "Sort table groups.", [["name", "Name"], ["rows", "Row count"]]);
  const results = el("div", "modern-list");
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Family", family), field("Sort", sort));
  const rowActions = actions();
  rowActions.append(
    button("Expand All", "Open every visible table group and table.", async () => {
      results.querySelectorAll("details").forEach((item) => { item.open = true; });
    }),
    button("Collapse All", "Close every visible table group and table.", async () => {
      results.querySelectorAll("details").forEach((item) => { item.open = false; });
    })
  );
  panel.append(controls, rowActions, results);
  const draw = () => {
    results.replaceChildren();
    const needle = search.value.toLowerCase();
    const keys = Object.keys(modernState.tables).filter((key) => {
      if (family.value && modernTableFamily(key) !== family.value) return false;
      if (!needle) return true;
      return key.toLowerCase().includes(needle) || modernSearchText(modernState.tables[key]).toLowerCase().includes(needle);
    });
    keys.sort((a, b) => {
      if (sort.value === "rows") {
        const rowsA = modernTableRowCount(modernState.tables[a]);
        const rowsB = modernTableRowCount(modernState.tables[b]);
        return rowsB - rowsA || a.localeCompare(b);
      }
      return a.localeCompare(b);
    });
    const byFamily = keys.reduce((groups, key) => {
      const groupName = modernTableFamily(key);
      if (!groups[groupName]) groups[groupName] = [];
      groups[groupName].push(key);
      return groups;
    }, {});
    results.appendChild(el("p", "muted", `${keys.length} matching table${keys.length === 1 ? "" : "s"} across ${Object.keys(byFamily).length} famil${Object.keys(byFamily).length === 1 ? "y" : "ies"}.`));
    for (const [groupName, groupKeys] of Object.entries(byFamily).sort(([a], [b]) => a.localeCompare(b))) {
      const group = document.createElement("details");
      group.className = "modern-row modern-table-group";
      group.open = keys.length <= 30 || Boolean(search.value);
      const groupSummary = document.createElement("summary");
      groupSummary.title = `Show or hide ${groupKeys.length} ${groupName} tables.`;
      const rowsInGroup = groupKeys.reduce((total, key) => total + modernTableRowCount(modernState.tables[key]), 0);
      groupSummary.append(el("strong", "", groupName), el("span", "muted", `${groupKeys.length} table${groupKeys.length === 1 ? "" : "s"} · ${rowsInGroup} row(s)`));
      group.appendChild(groupSummary);
      const groupBody = el("div", "modern-reference-group-body");
      for (const key of groupKeys) {
        const value = modernState.tables[key];
        const details = document.createElement("details");
        details.className = "modern-row modern-table-card";
        details.open = groupKeys.length <= 4 && keys.length <= 12;
        const summary = document.createElement("summary");
        summary.title = "Show or hide this table's rows.";
        summary.append(el("strong", "", modernTitleFromKey(key)), el("span", "muted", `${key} · ${modernTableRowCount(value)} row(s)`));
        details.appendChild(summary);
        const previewMount = el("div", "modern-table-preview-mount");
        const renderPreview = () => {
          if (previewMount.dataset.loaded === "1" && previewMount.dataset.needle === needle) return;
          previewMount.replaceChildren(modernTablePreview(value, needle));
          previewMount.dataset.loaded = "1";
          previewMount.dataset.needle = needle;
        };
        details.addEventListener("toggle", () => {
          if (details.open) renderPreview();
        });
        if (details.open) renderPreview();
        details.appendChild(previewMount);
        groupBody.appendChild(details);
      }
      group.appendChild(groupBody);
      results.appendChild(group);
    }
    if (!keys.length) {
      results.appendChild(el("p", "modern-home-status in-progress", "No matching tables. Clear filters or search by table name, row text, roll result, monster, item, tile, icon, or source term."));
    }
  };
  search.addEventListener("input", draw);
  family.addEventListener("change", draw);
  sort.addEventListener("change", draw);
  draw();
  rootEl.appendChild(panel);
}

function renderLibrary() {
  const panel = card("PDF Library and Background", "Open owned PDFs and maintain signoff-safe background summaries.");
  const pdfRow = actions();
  for (const [label, href, title] of PDF_LINKS) pdfRow.appendChild(link(label, href, title));
  panel.appendChild(pdfRow);
  const notes = card("Background Import Plan", "I should not bulk-copy full PDF background text. Work book-by-book and section-by-section: you identify pages, I summarise into app-safe background notes and cite the PDF page.");
  notes.appendChild(el("p", "modern-home-status in-progress", "In progress: curated background summaries and approved artwork/map extraction."));
  rootEl.append(panel, notes);
}

function renderGuides() {
  const panel = card("Game Guides", "Standalone guide links and future player-facing guide list.");
  const row = actions();
  row.append(
    link("TAG Section Guide", "/docs/Checking/TAG_SECTION_GUIDE.html", "Open the TAG workflow guide."),
    link("Checking Docs", "/docs/Checking/", "Open the Checking docs folder where the server can list files if enabled.")
  );
  panel.appendChild(row);
  const planned = el("ul", "modern-check-list");
  ["Starter guide", "Choosing starting characters guide", "Before adventure checklist", "During adventure checklist", "After adventure closeout guide", "TAG settlement workflow"].forEach((item) => planned.appendChild(el("li", "", item)));
  panel.appendChild(planned);
  rootEl.appendChild(panel);
}

function renderDeveloper() {
  const gate = card("Developer Unlock", "Enter password 7979 to show developer tools.");
  const pw = input("password", "modern-dev-pw", "Developer password. Default is 7979.");
  const tools = el("div", "modern-dev-tools hidden");
  const row = actions();
  row.append(
    link("Adventure PDF Import", "/modern/developer", "Placeholder for future PDF adventure module import."),
    link("Adventure Module Editor", "/modern/developer", "Placeholder for future adventure module editor."),
    link("Adventure Module Creator", "/modern/developer", "Placeholder for future adventure-from-scratch creator."),
    link("Map Elements Editor", "/static/tile-editor.html", "Open the existing map element editor as its own page."),
    link("Icon Editor", "/static/icon-editor.html", "Open the existing icon editor as its own page.")
  );
  tools.appendChild(row);
  if (window.sessionStorage.getItem("ahazi-modern-dev-unlocked") === "1") tools.classList.remove("hidden");
  const unlock = button("Unlock", "Show developer tools when password is 7979.", async () => {
    if (pw.value !== "7979") throw new Error("Incorrect developer password.");
    window.sessionStorage.setItem("ahazi-modern-dev-unlocked", "1");
    tools.classList.remove("hidden");
    setStatus("Developer tools unlocked.");
  }, "");
  gate.append(field("Password", pw), unlock, tools);
  rootEl.appendChild(gate);
}

function renderPage() {
  const page = currentPage();
  const meta = PAGE_META[page];
  document.querySelectorAll(".modern-nav a").forEach((anchor) => anchor.classList.toggle("active", anchor.dataset.page === page));
  titleEl.textContent = meta[0];
  subtitleEl.textContent = meta[0];
  descriptionEl.textContent = meta[1];
  rootEl.replaceChildren();
  const result = {
    home: renderHome,
    characters: renderCharacters,
    troupes: renderTroupes,
    guild: renderGuild,
    parties: renderParties,
    equipment: renderEquipment,
    banking: renderBanking,
    settlement: renderSettlement,
    campaign: renderCampaign,
    settings: renderSettings,
    "ai-adventures": renderAiAdventures,
    "go-adventure": renderGoAdventure,
    "rules-reference": renderRulesReference,
    tables: renderTables,
    library: renderLibrary,
    guides: renderGuides,
    developer: renderDeveloper,
  }[page]();
  if (result?.catch) result.catch(handleError);
}

loadCore()
  .then(() => {
    renderPage();
    setStatus("Ready");
  })
  .catch(handleError);
