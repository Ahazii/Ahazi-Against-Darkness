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
  artwork: [],
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
  home: ["Dashboard", "Start from the major play areas: manage rosters and world records, generate or import adventure modules, launch play, review rules/tables, and open developer tools when maintaining assets or metadata."],
  characters: ["Character Management", "Create and maintain the full roster: class, level, Life, gold, clues, equipment slots, inventory, spells, campaign, Guild, troupe, party, and home-settlement context before a hero enters play."],
  troupes: ["Troupe Management", "Manage the troupe as the campaign's travelling roster: assign members, review the selected member sheet, see linked parties, confirm the home settlement, and record travel or membership changes."],
  guild: ["Guild Management", "Run The Adventures Guild layer: membership, coffers, finance, jobs, benefits, closeout obligations, and searchable member records tied back to the campaign world."],
  parties: ["Party Management", "Build and maintain four-hero adventuring parties, keep party members aligned with their troupe, heal or bank for the group, and check assignment warnings before starting a session."],
  equipment: ["Equipment Shop", "Buy and sell gear for roster characters, review prices and resale handling, and keep carried equipment aligned with the character sheet before the next adventure."],
  banking: ["Banking and Finance", "Track The Adventures Guild accounts, hidden treasure troves, robbed accounts, inheritance, loans, storage risks, and recovery tasks that can affect closeout and future play."],
  settlement: ["Settlement Management", "Maintain friendly settlements, size modifiers, services, travel notes, availability checks, and campaign assignment for the places your troupes use between adventures."],
  campaign: ["Campaign Management", "Keep the app-owned world-builder records together: campaign description, assigned Guild, troupes, friendly settlements, troublesome-town placeholders, chronicle, and future map hooks."],
  settings: ["Settings / Options", "Control ruleset profiles, enabled rule families, map limits, campaign options, and Adventures Guild preferences without changing the underlying rule data."],
  "adventure-management": ["Adventure Management", "Manage every playable module in one place: generated Adventures Guild modules, imported modules, AI-authored modules, export packages, delete safe modules, and review in-use/completed status."],
  "go-adventure": ["Go Adventure!", "Choose the party and module, review readiness warnings, start or resume play, and let supported adventure objectives drive the exploration guidance automatically."],
  "rules-reference": ["Rules Reference", "Search curated implementation notes with source references, app-owned boundaries, TAG automation explanations, and links from controls that need rules context."],
  tables: ["Tables List", "Browse structured rule and app tables, filter by family or artwork links, and inspect the data that powers rules lookups, validation, and dashboard references."],
  library: ["Credits / History / Background", "Open owned PDFs, maintain signoff-safe background notes, and keep artwork/PDF boundaries clear for personal-use and publication-safe content."],
  guides: ["Game Guides", "Open player-facing workflow guides, test checklists, and future quick-start material for using the app during setup, play, closeout, and TAG procedures."],
  developer: ["Developer Section", "Password-gated maintenance tools for module import scaffolding, map and icon editors, artwork status, validation helpers, and content pipeline checks."],
};

const PDF_LINKS = [
  ["Expanded Edition", "/Rules/Four_Against_Darkness_Expanded_Edition.pdf", "Open the Expanded Edition PDF."],
  ["Four Against the Abyss", "/Rules/Four-Against-the-Abyss.pdf", "Open Four Against the Abyss PDF."],
  ["Forsaken Depths", "/Rules/Four_Against_the_Forsaken_Depths.pdf", "Open Forsaken Depths PDF."],
  ["Tales from the Adventurers Guild", "/Rules/Tales_from_the_adventurers_guild.pdf", "Open Tales from the Adventurers Guild PDF."],
  ["Four Against the Netherworld", "/Rules/Four Against_the_Netherworld.pdf", "Open Four Against the Netherworld PDF."],
  ["Courtship of Flower Demons", "/Rules/The_Courtship_of_Flower_Demons.pdf", "Open The Courtship of Flower Demons PDF."],
];

const PAGE_HELP_QUERIES = {
  home: "dashboard guidance log",
  characters: "character sheet equipment inventory party troupe guild",
  troupes: "troupe campaign party settlement travel",
  guild: "guild coffers upkeep job benefits",
  parties: "party troupe membership",
  equipment: "equipment shop buy sell guild discount",
  banking: "banking finance trove robbery inheritance",
  settlement: "settlement services availability travel",
  campaign: "campaign world builder",
  settings: "settings ruleset profile",
  "adventure-management": "adventure management import export generated module",
  "go-adventure": "go adventure closeout gates start override",
  "rules-reference": "rules artwork registry",
  tables: "artwork table source page",
  library: "pdf artwork boundary",
  guides: "guide checklist",
  developer: "developer import editor",
};

const PAGE_HELP_REFS = {
  characters: "home_character_sheets",
  troupes: "campaign_membership_boundaries",
  guild: "tag_guild_closeout_guidance",
  parties: "campaign_membership_boundaries",
  equipment: "equipment_shop",
  banking: "tag_settlement_campaign",
  settlement: "tag_settlement_campaign",
  campaign: "campaign_command_center",
  "adventure-management": "go_adventure_closeout_gates",
  "go-adventure": "go_adventure_closeout_gates",
  "rules-reference": "rules_artwork_registry",
  tables: "rules_tables_index",
  library: "pdf_artwork_boundary",
};

const statusEl = document.getElementById("modern-status");
const titleEl = document.getElementById("modern-page-title");
const subtitleEl = document.getElementById("modern-page-subtitle");
const descriptionEl = document.getElementById("modern-page-description");
const helpEl = document.getElementById("modern-page-help");
const pageHeadEl = document.querySelector(".modern-page-head");
const pageCompanionEl = document.getElementById("modern-page-companion");
const pageArtworkEl = document.getElementById("modern-page-artwork");
const navArtworkEl = document.getElementById("modern-nav-artwork");
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

function helpLink(label, href, title) {
  const anchor = link(label, href, title, "help-ref-link");
  anchor.setAttribute("aria-label", title);
  return anchor;
}

function ruleReferenceHref(entryId, fallbackQuery = "") {
  if (entryId) return `/modern/rules-reference?entry=${encodeURIComponent(entryId)}`;
  return `/modern/rules-reference?help=${encodeURIComponent(fallbackQuery || "rules reference")}`;
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

function classProfileById(classId) {
  return modernState.classes.find((item) => item.id === classId) || modernState.classes[0] || null;
}

function classImageSrc(profile) {
  if (!profile?.image) return "";
  if (/^(https?:|\/)/.test(profile.image)) return profile.image;
  return `/assets/${profile.image}`;
}

function renderClassDossier(profile) {
  const wrap = el("div", "modern-class-info");
  wrap.title = "Class dossier from the structured class rules data: artwork, core stats, starting kit, spells, abilities, and implementation status.";
  if (!profile) {
    wrap.appendChild(el("p", "muted", "Choose a class to inspect its rules profile before creating the character."));
    return wrap;
  }
  const hero = el("div", "modern-class-hero");
  const src = classImageSrc(profile);
  if (src) {
    const image = document.createElement("img");
    image.src = src;
    image.alt = `${profile.name} class artwork`;
    image.title = `${profile.name} class artwork from the project assets.`;
    hero.appendChild(image);
  }
  const summary = el("div", "modern-stack");
  summary.appendChild(el("strong", "", `${profile.name} class dossier`));
  summary.appendChild(
    el(
      "span",
      "muted",
      `Life ${profile.base_life ?? "?"} · Attack ${profile.attack_bonus ?? 0} · Defense ${profile.defense_bonus ?? 0} · Save ${profile.save_bonus ?? 0} · Wealth ${profile.starting_wealth_roll || `${profile.starting_gold || 0}gp`}`
    )
  );
  summary.appendChild(el("span", "muted", `Status: ${profile.implementation_status || "review"}`));
  hero.appendChild(summary);
  wrap.appendChild(hero);
  const details = el("div", "modern-class-grid");
  details.appendChild(
    modernStatusRow(
      "Starting equipment",
      (profile.starting_inventory || []).join(", ") || "No starting equipment listed.",
      "Items added or referenced when this class is created."
    )
  );
  details.appendChild(
    modernStatusRow(
      "Starting spells",
      (profile.starting_spells || []).join(", ") || "No starting spells.",
      "Spells or prayers granted at character creation."
    )
  );
  details.appendChild(
    modernStatusRow(
      "Abilities",
      (profile.abilities || []).join(", ") || "No separate ability summary listed.",
      "Rules abilities implemented or tracked for this class."
    )
  );
  wrap.appendChild(details);
  if (profile.description) {
    const desc = el("p", "modern-class-description", profile.description);
    desc.title = "Full class rules text from data/rules/classes.json.";
    wrap.appendChild(desc);
  }
  return wrap;
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

function formatSnapshotDetail(detail) {
  if (detail == null) return "";
  if (Array.isArray(detail)) return detail.filter(Boolean).join("\n");
  return String(detail || "");
}

function showSnapshotDetail(title, detail) {
  const text = formatSnapshotDetail(detail);
  if (!text) return;
  const existing = document.getElementById("modern-snapshot-detail-dialog");
  if (existing) existing.remove();
  const overlay = el("div", "modern-snapshot-detail-overlay");
  overlay.id = "modern-snapshot-detail-dialog";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", title);
  const panel = el("section", "modern-snapshot-detail-panel");
  panel.appendChild(el("h3", "", title));
  const body = el("pre", "modern-snapshot-detail-body", text);
  panel.appendChild(body);
  const row = actions();
  row.appendChild(button("Close", "Close this snapshot detail panel.", async () => overlay.remove(), "secondary"));
  panel.appendChild(row);
  overlay.appendChild(panel);
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) overlay.remove();
  });
  overlay.addEventListener("keydown", (event) => {
    if (event.key === "Escape") overlay.remove();
  });
  document.body.appendChild(overlay);
  row.querySelector("button")?.focus();
}

function snapshotStatusRow(title, body, hint = "", detail = "") {
  const text = formatSnapshotDetail(detail);
  const row = modernStatusRow(title, body, text ? `${hint || "Open details."}\n\n${text}` : hint);
  if (text) {
    row.classList.add("modern-row-action");
    row.tabIndex = 0;
    row.setAttribute("role", "button");
    row.setAttribute("aria-label", `${title}: open details`);
    row.addEventListener("click", () => showSnapshotDetail(title, text));
    row.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      event.preventDefault();
      showSnapshotDetail(title, text);
    });
  }
  return row;
}

function characterSearchText(character) {
  const troupe = worldTroupeForCharacter(character);
  return [
    character.name,
    character.class_name,
    character.level,
    character.gold,
    character.clues,
    worldName(worldCampaigns(), character.campaign_id, ""),
    worldName(worldGuilds(), character.guild_id, ""),
    worldName(worldTroupes(), character.troupe_id, ""),
    troupe?.home_settlement_id ? worldName(worldSettlements(), troupe.home_settlement_id, "") : "",
    ...(character.statuses || []),
    ...(character.inventory || []),
    ...(character.spells || []),
    ...(character.abilities || []),
    ...partyNamesForCharacter(character.id),
    (modernState.campaign?.tag_troupe_member_character_ids || []).includes(character.id) ? "troupe" : "",
    (modernState.campaign?.tag_troupe_active_character_ids || []).includes(character.id) ? "active" : "",
    characterEquipmentWarnings(character).length ? "equipment gap warning" : "",
    characterContextWarnings(character).length ? "context mismatch warning" : "",
    character.current_life <= 0 ? "dead fallen" : "",
    character.current_life < character.max_life ? "injured wounded" : "",
  ].join(" ").toLowerCase();
}

function filteredCharacters({ search = "", classId = "", sort = "name", campaignId = "", guildId = "", troupeId = "", partyId = "", readiness = "" } = {}) {
  const needle = String(search || "").toLowerCase();
  const rows = modernState.characters.filter((character) => {
    if (classId && character.class_id !== classId) return false;
    if (campaignId && character.campaign_id !== campaignId) return false;
    if (guildId && character.guild_id !== guildId) return false;
    if (troupeId && character.troupe_id !== troupeId) return false;
    if (partyId && character.party_id !== partyId) return false;
    if (readiness === "injured" && !(character.current_life < character.max_life && character.current_life > 0)) return false;
    if (readiness === "fallen" && character.current_life > 0) return false;
    if (readiness === "locked" && !character.active_session_id) return false;
    if (readiness === "equipment_gap" && !characterEquipmentWarnings(character).length) return false;
    if (readiness === "context_warning" && !characterContextWarnings(character).length) return false;
    return !needle || characterSearchText(character).includes(needle);
  });
  rows.sort((left, right) => {
    if (sort === "level") return (right.level || 0) - (left.level || 0) || left.name.localeCompare(right.name);
    if (sort === "class") return String(left.class_name || "").localeCompare(String(right.class_name || "")) || left.name.localeCompare(right.name);
    if (sort === "party") return partyNamesForCharacter(left.id).join(",").localeCompare(partyNamesForCharacter(right.id).join(",")) || left.name.localeCompare(right.name);
    if (sort === "troupe") return worldName(worldTroupes(), left.troupe_id, "").localeCompare(worldName(worldTroupes(), right.troupe_id, "")) || left.name.localeCompare(right.name);
    if (sort === "campaign") return worldName(worldCampaigns(), left.campaign_id, "").localeCompare(worldName(worldCampaigns(), right.campaign_id, "")) || left.name.localeCompare(right.name);
    if (sort === "life") return (left.current_life || 0) - (right.current_life || 0) || left.name.localeCompare(right.name);
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

function characterManagementFilterControls(prefix, onChange) {
  const panel = el("div", "modern-filterbar");
  const search = input("search", `${prefix}-character-search`, "Search by name, class, party, campaign, guild, troupe, home settlement, inventory, spells, status, gold, Clues, or setup warnings.");
  const classFilter = select(`${prefix}-character-class-filter`, "Filter roster characters by class.", [["", "All classes"], ...modernState.classes.map((item) => [item.id, item.name])]);
  const campaignFilter = select(`${prefix}-character-campaign-filter`, "Filter by assigned campaign/world.", [["", "All campaigns"], ...worldCampaigns().map((item) => [item.id, item.name])]);
  const guildFilter = select(`${prefix}-character-guild-filter`, "Filter by assigned guild.", [["", "All guilds"], ...worldGuilds().map((item) => [item.id, item.name])]);
  const troupeFilter = select(`${prefix}-character-troupe-filter`, "Filter by assigned troupe.", [["", "All troupes"], ...worldTroupes().map((item) => [item.id, item.name])]);
  const partyFilter = select(`${prefix}-character-party-filter`, "Filter by saved party assignment.", [["", "All parties"], ...modernState.parties.map((item) => [item.id, item.name])]);
  const readiness = select(`${prefix}-character-readiness-filter`, "Filter by adventure readiness and cleanup warnings.", [["", "All readiness"], ["injured", "Injured"], ["fallen", "Fallen"], ["locked", "Active session lock"], ["equipment_gap", "Equipment gaps"], ["context_warning", "Context warnings"]]);
  const sort = select(`${prefix}-character-sort`, "Sort roster characters.", [["name", "Name"], ["level", "Level"], ["class", "Class"], ["party", "Party"], ["troupe", "Troupe"], ["campaign", "Campaign"], ["life", "Lowest Life"]]);
  panel.append(field("Search", search), field("Class", classFilter), field("Campaign", campaignFilter), field("Guild", guildFilter), field("Troupe", troupeFilter), field("Party", partyFilter), field("Readiness", readiness), field("Sort", sort));
  for (const node of [search, classFilter, campaignFilter, guildFilter, troupeFilter, partyFilter, readiness, sort]) {
    node.addEventListener("input", onChange);
    node.addEventListener("change", onChange);
  }
  return { panel, search, classFilter, campaignFilter, guildFilter, troupeFilter, partyFilter, readiness, sort };
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

function openGuidanceTasks() {
  return (modernState.campaign?.guidance_tasks || []).filter((task) => task.status === "open");
}

async function updateGuidanceTask(task, status) {
  const result = await api("/api/campaign/guidance-task", {
    method: "POST",
    body: JSON.stringify({ task_id: task.id, status, note: `Updated from modern dashboard as ${status}` }),
  });
  modernState.campaign = result.campaign;
  setStatus(result.entry?.result_text || "Guidance task updated.");
  await refreshCoreAndRender();
}

async function recordTagSignoffReview(note = "") {
  const result = await api("/api/campaign/tag/signoff-review", {
    method: "POST",
    body: JSON.stringify({ note }),
  });
  modernState.campaign = result.campaign;
  setStatus(result.entry?.result_text || "TAG signoff review recorded.");
  await refreshCoreAndRender();
}

function closeoutActionTargets(task) {
  const action = task.task_action || "";
  if (action.includes("guild")) {
    return [
      ["Guild", "/modern/guild", "Open Guild Management to resolve loot share, upkeep, reroll reset, resurrection funding, or leaving-restriction closeout."],
      ["Rules", ruleReferenceHref("tag_guild_closeout_guidance", "TAG guild closeout"), "Open the Guild closeout guidance reference."]
    ];
  }
  if (action.includes("bank") || action.includes("trove") || task.category === "finance" || task.category === "storage") {
    return [
      ["Banking", "/modern/banking", "Open Banking and Finance to resolve bank robbery, hidden trove risk, recovery, inheritance, or storage consequences."],
      ["Rules", ruleReferenceHref("tag_settlement_campaign", "TAG banking storage"), "Open the TAG settlement/banking reference."]
    ];
  }
  if (action.includes("xp") || task.category === "xp") {
    return [
      ["Go Adventure", "/modern/go-adventure", "Open Go Adventure and review generated-adventure signoff before manually clearing XP closeout."],
      ["Rules", ruleReferenceHref("tag_generated_adventure_signoff", "TAG XP signoff"), "Open the TAG generated-adventure signoff reference."]
    ];
  }
  return [
    ["Rules", ruleReferenceHref("adventure_closeout_workflow", "adventure closeout workflow"), "Open the app-owned adventure closeout workflow reference."]
  ];
}

function closeoutChecklistRows() {
  const campaign = modernState.campaign || {};
  const tasks = campaign.tag_closeout_tasks || [];
  const openTasks = tasks.filter((task) => !task.resolved);
  const pendingXp = (campaign.tag_xp_markers || []).filter((marker) => !marker.applied);
  const openGuidance = (campaign.guidance_tasks || []).filter((task) => task.status === "open");
  const latestRoute = (campaign.tag_adventure_routes || []).slice(-1)[0];
  const latestLead = (campaign.tag_generated_adventure_ids || []).slice(-1)[0];
  return [
    ["Generated lead", latestLead || "No generated TAG lead recorded.", latestLead ? "ok" : "warn", "Confirm the latest generated module came from the intended Rumor, Treasure Map, Thematic Dungeon, or Guild Job."],
    ["Route / branch marker", latestRoute ? latestRoute.result_text : "No route marker recorded.", latestRoute ? "ok" : "warn", "Record parley, Clue gates, skipped scenes, unlocked scenes, final route, or solo restrictions when the generated adventure uses them."],
    ["XP markers", `${pendingXp.length} pending marker(s).`, pendingXp.length ? "block" : "ok", "Pending XP markers should be awarded, rolled, or intentionally dismissed before the next adventure."],
    ["Guild obligations", `${openTasks.filter((task) => task.category === "guild").length} open task(s).`, openTasks.some((task) => task.category === "guild") ? "block" : "ok", "Resolve Guild loot share, upkeep, availability reroll reset, leaving restrictions, and other Guild obligations."],
    ["Banking / storage", `${openTasks.filter((task) => ["finance", "storage"].includes(task.category)).length} open task(s).`, openTasks.some((task) => ["finance", "storage"].includes(task.category)) ? "block" : "ok", "Resolve bank robbery recovery, hidden trove risk, stolen trove recovery, inheritance, and storage consequences."],
    ["Guidance actions", `${openGuidance.length} open guidance task(s).`, openGuidance.some((task) => task.priority === "required") ? "block" : (openGuidance.length ? "warn" : "ok"), "Complete, defer, or dismiss guidance tasks from the Dashboard Guidance / Log or Campaign Management archive."]
  ];
}

function renderAdventureCloseoutCockpit(context = "Dashboard") {
  const rows = closeoutChecklistRows();
  const openRows = rows.filter(([, , status]) => status === "block");
  const warnRows = rows.filter(([, , status]) => status === "warn");
  const panel = card("Adventure Closeout Checklist", "Actionable TAG closeout review before the next start: generated lead, route marker, XP, Guild, banking/storage, and guidance.");
  panel.classList.add(openRows.length ? "modern-primary-card" : "modern-card-compact");
  const statusText = openRows.length
    ? `${openRows.length} required closeout area(s) need attention before normal play.`
    : (warnRows.length ? `${warnRows.length} review warning(s); signoff may still be valid if not relevant.` : "Closeout looks ready for the next adventure.");
  panel.appendChild(modernStatusRow(`${context} closeout state`, statusText, "This is app workflow guidance. It summarizes open state but does not replace printed PDF decisions for exact rewards or scene text."));
  for (const [title, body, status, hint] of rows) {
    const row = modernStatusRow(title, body, hint);
    row.classList.add(status === "ok" ? "modern-row-ok" : "modern-row-warn");
    panel.appendChild(row);
  }
  const note = input("text", `modern-tag-signoff-note-${context.toLowerCase().replace(/\W+/g, "-")}`, "Optional note saved to the TAG log and Campaign Chronicle with this generated-adventure signoff review.", "");
  const row = actions();
  row.append(
    field("Review note", note),
    button("Mark Signoff Reviewed", "Record a generated TAG adventure signoff review. This logs open closeout and XP counts; it only completes broad review guidance when no open closeout or XP markers remain.", () => recordTagSignoffReview(note.value), ""),
    link("Guild", "/modern/guild", "Resolve Guild closeout obligations.", "link-button secondary"),
    link("Banking", "/modern/banking", "Resolve banking and hidden-trove closeout obligations.", "link-button secondary"),
    link("Rules", ruleReferenceHref("tag_closeout_checklist_automation", "TAG closeout checklist automation"), "Open the Rules Reference entry for this closeout checklist.", "link-button secondary")
  );
  panel.appendChild(row);
  return panel;
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
    const taskActions = actions();
    for (const [label, href, titleText] of closeoutActionTargets(task)) {
      taskActions.appendChild(link(label, href, titleText, "link-button secondary"));
    }
    taskActions.appendChild(button("Mark Done", "Manual signoff: mark this TAG closeout task as resolved only after you used the relevant control, checked the printed rule/PDF, or intentionally handled it outside the app.", async () => {
      const result = await api("/api/campaign/tag/closeout-task", {
        method: "POST",
        body: JSON.stringify({ task_id: task.id, note: "Resolved from modern closeout checklist" }),
      });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Closeout task resolved.");
      await refreshCoreAndRender();
    }));
    row.appendChild(taskActions);
    panel.appendChild(row);
  }
  return panel;
}

function guidanceLogEntries() {
  const tasks = openGuidanceTasks()
    .slice(0, 8)
    .map((task) => ({
      kind: "task",
      task,
      title: `${modernTitleFromKey(task.priority || "recommended")}: ${task.title || "Guidance task"}`,
      body: task.body || task.reference || "Review this campaign task.",
      hint: task.reference || "Structured campaign guidance task.",
    }));
  if (tasks.length) return tasks;
  const closeouts = (modernState.campaign?.tag_closeout_tasks || [])
    .filter((task) => !task.resolved)
    .slice(0, 6)
    .map((task) => ({
      title: task.title || "Closeout task",
      body: task.result_text || task.reference || "Resolve this before the next adventure.",
      hint: task.reference || "TAG closeout task generated by adventure completion.",
    }));
  const logs = (modernState.campaign?.campaign_chronicle || modernState.campaign?.tag_downtime_log || [])
    .slice(-6)
    .reverse()
    .map((entry) => ({
      title: entry.title || modernTitleFromKey(entry.action || entry.event_type || "log"),
      body: entry.body || entry.result_text || entry.note || "Recent campaign log entry.",
      hint: entry.reference || "Recent campaign chronicle entry.",
    }));
  return closeouts.length ? closeouts : logs;
}

function renderGuidanceLog() {
  const panel = document.createElement("details");
  panel.className = "modern-card modern-collapsible";
  const summary = document.createElement("summary");
  summary.title = "Show or hide next-action guidance and recent campaign log entries.";
  summary.append(
    el("strong", "", "Guidance / Log"),
    el("span", "muted", "Next-action prompts from TAG closeout tasks and recent Guild, settlement, travel, banking, and adventure logs.")
  );
  panel.appendChild(summary);
  const links = actions();
  links.append(
    helpLink("?", ruleReferenceHref("tag_guild_closeout_guidance", "TAG closeout guidance"), "Open the exact guidance/closeout rules-reference entry. If an exact entry does not exist, the app links to a targeted search instead of copying PDF text here."),
    link("TAG Guide", "/docs/Checking/TAG_SECTION_GUIDE.html", "Open the TAG workflow guide.", "link-button secondary")
  );
  panel.appendChild(links);
  const entries = guidanceLogEntries();
  if (!entries.length) {
    panel.appendChild(
      modernStatusRow(
        "No current prompts",
        "Finish an adventure, create a TAG lead, use Guild jobs, travel, or perform settlement/banking actions and the latest guidance will appear here.",
        "Dashboard guidance is generated from app state, closeout tasks, and TAG logs."
      )
    );
    return panel;
  }
  for (const entry of entries) {
    const row = modernStatusRow(entry.title, entry.body, entry.hint);
    if (entry.kind === "task" && entry.task) {
      const taskActions = actions();
      taskActions.append(
        button("Complete", "Mark this guidance task complete. This hides the active prompt but keeps the campaign chronicle history.", () => updateGuidanceTask(entry.task, "completed")),
        button("Defer", "Defer this guidance task for later without deleting it.", () => updateGuidanceTask(entry.task, "deferred")),
        button("Dismiss", "Dismiss this guidance task when it does not apply to this campaign. The chronicle remains.", () => updateGuidanceTask(entry.task, "dismissed"))
      );
      row.appendChild(taskActions);
    }
    panel.appendChild(row);
  }
  return panel;
}

function collapseCard(panel, summaryHint = "") {
  const collapsed = document.createElement("details");
  collapsed.className = "modern-card modern-collapsible";
  const title = panel.querySelector("h3")?.textContent || "Details";
  const body = panel.querySelector(":scope > p.muted")?.textContent || summaryHint;
  const summary = document.createElement("summary");
  summary.title = `Show or hide ${title}.`;
  summary.append(el("strong", "", title), el("span", "muted", body));
  collapsed.appendChild(summary);
  for (const child of Array.from(panel.childNodes)) {
    if (child.nodeType === Node.ELEMENT_NODE && ["H3", "P"].includes(child.tagName)) continue;
    collapsed.appendChild(child);
  }
  return collapsed;
}

function renderCampaignChronicle(title = "Campaign Chronicle", limit = 12) {
  const panel = card(title, "Chronological campaign log for completed adventures, TAG actions, closeout signoffs, Guild/banking/settlement actions, and guidance task updates.");
  const entries = [...(modernState.campaign?.campaign_chronicle || [])].reverse().slice(0, limit);
  if (!entries.length) {
    panel.appendChild(el("p", "muted", "No campaign chronicle entries yet. Complete an adventure or use campaign/TAG actions to create history."));
    return panel;
  }
  for (const entry of entries) {
    panel.appendChild(
      modernStatusRow(
        entry.title || modernTitleFromKey(entry.event_type || "campaign event"),
        `${entry.body || ""}${entry.party_name ? ` · Party ${entry.party_name}` : ""}${entry.character_name ? ` · ${entry.character_name}` : ""}`,
        `${entry.created_at || ""}${entry.reference ? ` · ${entry.reference}` : ""}`
      )
    );
  }
  return panel;
}

function tagWorkflowCounts() {
  const campaign = modernState.campaign || {};
  return {
    troupeMembers: (campaign.tag_troupe_member_character_ids || []).length,
    activeMembers: (campaign.tag_troupe_active_character_ids || []).length,
    guildActive: Boolean(campaign.tag_guild_member),
    guildBenefits: tagGuildBenefitsActive(campaign),
    guildCoffers: campaign.tag_guild_coffers_gp || 0,
    bankAccounts: (campaign.tag_bank_accounts || []).length,
    robbedAccounts: (campaign.tag_bank_accounts || []).filter((account) => account.robbed).length,
    hiddenTroveItems: (campaign.tag_stored_items || []).filter((item) => item.storage === "trove").length,
    hiddenTroveGold: campaign.tag_storage_gold_gp || 0,
    hiddenTroveRobbed: Boolean(campaign.tag_hidden_trove_robbed),
    routes: (campaign.tag_adventure_routes || []).length,
    xpPending: (campaign.tag_xp_markers || []).filter((marker) => !marker.applied).length,
    generatedLeads: (campaign.tag_generated_adventure_ids || []).length,
    openCloseout: (campaign.tag_closeout_tasks || []).filter((task) => !task.resolved).length,
    openGuidance: (campaign.guidance_tasks || []).filter((task) => task.status === "open").length,
  };
}

function renderTagWorkflowDashboard(context = "overview") {
  const counts = tagWorkflowCounts();
  const panel = card("The Adventures Guild Workflow Summary", "Live player-facing Adventures Guild status: troupe, Guild, banking, storage, generated leads, route/XP signoff, and closeout prompts. Use this as the first scan before and after Adventures Guild adventures.");
  panel.classList.add("modern-primary-card");
  panel.append(
    modernStatusRow("Troupe readiness", `${counts.troupeMembers} troupe member(s) · ${counts.activeMembers}/4 active`, "Active members are the likely adventuring party. Keep this aligned with Party Management and Go Adventure."),
    modernStatusRow("Guild status", `${counts.guildActive ? "member" : "not a member"} · benefits ${counts.guildBenefits ? "active" : "inactive"} · ${counts.guildCoffers} gp coffers`, "Guild benefits depend on active membership and coffers above 0 gp; coffers affect benefits, upkeep, resurrection funding, and loot-share obligations."),
    modernStatusRow("Finance/storage", `${counts.bankAccounts} bank account(s) · ${counts.robbedAccounts} robbed · trove ${counts.hiddenTroveGold} gp / ${counts.hiddenTroveItems} item stack(s)${counts.hiddenTroveRobbed ? " · stolen" : ""}`, "Bank accounts, robbery recovery, hidden troves, and stolen trove recovery are handled from Banking and Finance."),
    modernStatusRow("Adventure signoff", `${counts.generatedLeads} generated Adventures Guild lead(s) · ${counts.routes} route marker(s) · ${counts.xpPending} pending XP marker(s)`, "Generated Adventures Guild adventures use room prompts and Adventures Guild Actions to record branch, route, reward, and XP signoff."),
    modernStatusRow("Needs attention", `${counts.openCloseout} closeout prompt(s) · ${counts.openGuidance} open guidance task(s)`, "Closeout and guidance tasks should be reviewed before the next adventure; Go Adventure enforces required closeout warnings with explicit override.")
  );
  const row = actions();
  row.append(
    link("Guild", "/modern/guild", "Open Guild Management for membership, coffers, benefits, Guild jobs, and closeout prompts.", "link-button secondary"),
    link("Banking", "/modern/banking", "Open Banking and Finance for TAG bank accounts, hidden troves, robbery recovery, inheritance, and loans.", "link-button secondary"),
    link("Troupe", "/modern/troupes", "Open Troupe Management for members, active adventurers, settlement travel, and party context.", "link-button secondary"),
    link("Settlement", "/modern/settlement", "Open Settlement Management for size, availability checks, tracked settlements, and travel.", "link-button secondary"),
    link("Rules", ruleReferenceHref("modern_tag_workflow_completion", "modern TAG workflow"), "Open the Rules Reference entry for this modern TAG workflow pass.", "link-button secondary")
  );
  if (context === "go") {
    row.appendChild(link("TAG Guide", "/docs/Checking/TAG_SECTION_GUIDE.html", "Open the TAG checking guide for generated adventures and closeout review.", "link-button secondary"));
  }
  panel.appendChild(row);
  return panel;
}

function renderTagSignoffPanel(context = "TAG Signoff") {
  const campaign = modernState.campaign || {};
  const panel = card(context, "Checklist for generated TAG adventures: record branch/route choices, rewards, XP, Guild obligations, banking/storage consequences, and closeout resolution.");
  const route = (campaign.tag_adventure_routes || []).slice(-1)[0];
  const log = (campaign.tag_downtime_log || []).slice(-1)[0];
  const openCloseout = (campaign.tag_closeout_tasks || []).filter((task) => !task.resolved).length;
  const pendingXp = (campaign.tag_xp_markers || []).filter((marker) => !marker.applied).length;
  panel.append(
    modernStatusRow("Generated lead", (campaign.tag_generated_adventure_ids || []).slice(-1)[0] || "No generated TAG lead yet.", "Create Rumor, Treasure Map, Thematic Dungeon, or Guild Job modules from Go Adventure or Guild Management."),
    modernStatusRow("Latest route marker", route ? route.result_text : "No route marker recorded.", "TAG Actions during exploration records parley, Clue gates, skipped scenes, final route, solo restrictions, and generated-module route rewrites."),
    modernStatusRow("Pending XP", `${pendingXp} marker(s)`, "Resolve pending TAG XP markers from TAG Actions or closeout before starting the next adventure."),
    modernStatusRow("Closeout prompts", `${openCloseout} open prompt(s)`, "Open closeout prompts must be resolved by the relevant Guild, Banking, storage, XP, or manual signoff workflow."),
    modernStatusRow("Latest TAG log", log ? `${modernTitleFromKey(log.action)} · ${log.result_text}` : "No TAG log entries yet.", "Recent TAG automation/log action. Open the TAG guide when checking generated-adventure signoff against the PDF.")
  );
  const note = input("text", `modern-tag-panel-signoff-note-${context.toLowerCase().replace(/\W+/g, "-")}`, "Optional generated-adventure signoff note. This is saved to the TAG log and Campaign Chronicle.", "");
  const row = actions();
  row.append(
    field("Signoff note", note),
    button("Mark Reviewed", "Record that the latest generated TAG adventure signoff was reviewed. This does not resolve printed-rule decisions or open closeout tasks by itself.", () => recordTagSignoffReview(note.value), ""),
    link("Go Adventure", "/modern/go-adventure", "Open Go Adventure to create TAG leads, select generated modules, and review closeout gates.", "link-button secondary"),
    link("Guidance", "/modern/home", "Return to the Dashboard Guidance / Log for active task completion, deferral, or dismissal.", "link-button secondary"),
    link("TAG Guide", "/docs/Checking/TAG_SECTION_GUIDE.html", "Open generated-adventure manual checking and signoff guidance.", "link-button secondary")
  );
  panel.appendChild(row);
  return panel;
}

function renderTagActionLogExplorer() {
  const panel = card("TAG Action Log", "Search and filter TAG route, XP, finance, Guild, branch, generated-module, and signoff events. Use this when checking what a generated lead changed before closeout.");
  const search = input("search", "modern-tag-log-search", "Search TAG action, character, result text, reference, cost, or roll.");
  const family = select("modern-tag-log-family", "Filter by TAG log family.", [
    ["", "All TAG logs"],
    ["route", "Route"],
    ["xp", "XP"],
    ["finance", "Finance / banking"],
    ["guild", "Guild"],
    ["branch", "Branch / scene"],
    ["generated", "Generated lead"],
    ["signoff", "Signoff / closeout"],
  ]);
  const results = el("div", "modern-list");
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Family", family));
  const familyMatches = (entry) => {
    const action = String(entry.action || "").toLowerCase();
    if (!family.value) return true;
    if (family.value === "route") return action.includes("route");
    if (family.value === "xp") return action.includes("xp");
    if (family.value === "finance") return /bank|finance|trove|loan|inheritance/.test(action);
    if (family.value === "guild") return action.includes("guild");
    if (family.value === "branch") return /branch|scene|reward|map|rumor|maze|portrait|sewer|monoceros|dragon|bandit|gargoyle/.test(action);
    if (family.value === "generated") return action.includes("create_tag_adventure");
    if (family.value === "signoff") return /signoff|closeout/.test(action);
    return true;
  };
  function draw() {
    results.replaceChildren();
    const needle = search.value.toLowerCase();
    const rows = [...(modernState.campaign?.tag_downtime_log || [])]
      .reverse()
      .filter(familyMatches)
      .filter((entry) => !needle || `${entry.action} ${entry.character_name || ""} ${entry.result_text || ""} ${entry.roll || ""} ${entry.cost_gp || ""}`.toLowerCase().includes(needle))
      .slice(0, 40);
    results.appendChild(el("p", "muted", `${rows.length} TAG log entr${rows.length === 1 ? "y" : "ies"} shown.`));
    for (const entry of rows) {
      results.appendChild(
        modernStatusRow(
          `${modernTitleFromKey(entry.action)}${entry.character_name ? ` · ${entry.character_name}` : ""}`,
          `${entry.result_text || ""}${entry.roll ? ` · roll ${entry.roll}` : ""}${entry.cost_gp ? ` · ${entry.cost_gp} gp` : ""}`,
          "TAG action history for route, XP, finance, Guild, generated-module, and closeout review."
        )
      );
    }
  }
  search.addEventListener("input", draw);
  family.addEventListener("change", draw);
  panel.append(controls, results);
  draw();
  return panel;
}

function renderCommandCenter(command) {
  const panel = card("Campaign Command Center", "Selected campaign overview: assigned Guild, troupes, settlements, troublesome towns, parties, active sessions, open guidance, unresolved closeout prompts, and recent chronicle.");
  panel.classList.add("modern-primary-card");
  const campaignName = command?.campaign_name || selectedWorldCampaign()?.name || "No campaign";
  panel.append(
    modernStatusRow("Campaign", campaignName, "The active world-builder campaign. New records default here unless a creation form overrides the campaign."),
    modernStatusRow("World records", `${(command.guilds || []).length} guild(s) · ${(command.troupes || []).length} troupe(s) · ${(command.settlements || []).length} friendly settlement(s) · ${(command.troublesome_towns || []).length} troublesome town(s)`, "Records assigned to this selected campaign."),
    modernStatusRow("Play records", `${(command.parties || []).length} part${(command.parties || []).length === 1 ? "y" : "ies"} · ${(command.characters || []).length} character(s) · ${(command.active_sessions || []).length} active session(s)`, "Campaign-linked parties, characters, and active sessions."),
    modernStatusRow("Needs attention", `${(command.open_guidance || []).length} open guidance · ${(command.unresolved_closeout || []).length} unresolved closeout`, "Open app guidance and TAG closeout prompts that should be reviewed before the next adventure.")
  );
  const row = actions();
  row.append(
    link("Export Chronicle JSON", `/api/campaign/chronicle/export?campaign_id=${encodeURIComponent(command.campaign_id || "")}`, "Export this campaign chronicle as JSON.", "link-button secondary"),
    link("Export Chronicle MD", `/api/campaign/chronicle/export?format=markdown&campaign_id=${encodeURIComponent(command.campaign_id || "")}`, "Export this campaign chronicle as Markdown.", "link-button secondary"),
    button("Assign Orphans", "Assign orphaned characters, parties, troupes, guilds, settlements, and troublesome-town placeholders to the selected campaign where safe.", async () => {
      await worldAction({ action: "bulk_assign_campaign", campaign_id: command.campaign_id || modernState.campaign?.active_world_campaign_id });
    })
  );
  panel.appendChild(row);
  return panel;
}

function renderGuidanceArchive() {
  const panel = card("Guidance Archive", "Filter open, deferred, completed, and dismissed guidance without deleting campaign chronicle history.");
  const search = input("search", "modern-guidance-search", "Search guidance title, body, reference, status, priority, or category.");
  const status = select("modern-guidance-status", "Filter by guidance status. Open tasks appear in Dashboard guidance; completed/deferred/dismissed tasks remain for review.", [["", "All statuses"], ["open", "Open"], ["deferred", "Deferred"], ["completed", "Completed"], ["dismissed", "Dismissed"]]);
  status.value = "open";
  const priority = select("modern-guidance-priority", "Filter by priority. Required tasks are the strongest closeout/start warnings.", [["", "All priorities"], ["required", "Required"], ["recommended", "Recommended"], ["optional", "Optional"]]);
  const category = select("modern-guidance-category", "Filter by category: closeout, campaign, character, finance, guild, settlement, or adventure.", [["", "All categories"], ["closeout", "Closeout"], ["campaign", "Campaign"], ["character", "Character"], ["finance", "Finance"], ["guild", "Guild"], ["settlement", "Settlement"], ["adventure", "Adventure"]]);
  const results = el("div", "modern-list");
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Status", status), field("Priority", priority), field("Category", category));
  function draw() {
    results.replaceChildren();
    const needle = search.value.toLowerCase();
    const rows = (modernState.campaign?.guidance_tasks || [])
      .filter((task) => !status.value || task.status === status.value)
      .filter((task) => !priority.value || task.priority === priority.value)
      .filter((task) => !category.value || task.category === category.value)
      .filter((task) => !needle || `${task.title} ${task.body} ${task.reference} ${task.status} ${task.priority} ${task.category}`.toLowerCase().includes(needle))
      .slice()
      .reverse();
    results.appendChild(el("p", "muted", `${rows.length} guidance task(s) match the current filters.`));
    for (const task of rows) {
      const row = modernStatusRow(`${modernTitleFromKey(task.priority)} · ${task.title}`, `${modernTitleFromKey(task.status)} · ${modernTitleFromKey(task.category)} · ${task.body || task.reference || "No detail."}`, task.reference || "Structured app guidance task.");
      const rowActions = actions();
      if (task.status === "open") {
        rowActions.append(
          button("Complete", "Mark this open guidance task complete and keep its chronicle history.", () => updateGuidanceTask(task, "completed")),
          button("Defer", "Defer this guidance task for later.", () => updateGuidanceTask(task, "deferred")),
          button("Dismiss", "Dismiss this guidance task as irrelevant to this campaign.", () => updateGuidanceTask(task, "dismissed"))
        );
      } else {
        rowActions.append(button("Reopen", "Return this guidance task to the active Dashboard guidance list.", () => updateGuidanceTask(task, "open")));
      }
      row.appendChild(rowActions);
      results.appendChild(row);
    }
  }
  search.addEventListener("input", draw);
  status.addEventListener("change", draw);
  priority.addEventListener("change", draw);
  category.addEventListener("change", draw);
  panel.append(controls, results);
  draw();
  return panel;
}

function renderGuide(title, items, referenceId = "", fallbackQuery = "") {
  const panel = card(title, "");
  panel.classList.add("modern-guide-card");
  const list = el("ul", "modern-guide-list");
  for (const item of items) {
    const row = el("li", "", item);
    row.title = item;
    list.appendChild(row);
  }
  const guideActions = actions();
  guideActions.appendChild(
    helpLink("?", ruleReferenceHref(referenceId, fallbackQuery || title), `Open the most relevant Rules Reference entry for ${title}.`)
  );
  panel.append(list, guideActions);
  return panel;
}

function inventoryItemsMatching(character, pattern) {
  return (character.inventory || []).filter((item) => pattern.test(String(item)));
}

function equippedArmorSummary(character) {
  const armor = inventoryItemsMatching(character, /armor|mail|chain|attire|garment/i);
  const shields = inventoryItemsMatching(character, /shield/i);
  return {
    armor: armor.join(", ") || "No armor detected",
    shield: shields.join(", ") || "No shield detected",
  };
}

function characterEquipmentWarnings(character) {
  const warnings = [];
  const meleeItems = modernInventoryWeaponCandidates(character, "melee");
  const missileItems = modernInventoryWeaponCandidates(character, "missile");
  if (!meleeItems.length) warnings.push("No melee weapon detected in inventory.");
  if (meleeItems.length && !character.default_melee_weapon) warnings.push("Melee slot is not assigned; the backend will infer a default where possible.");
  if (missileItems.length && !character.default_missile_weapon) warnings.push("Missile weapon carried but missile slot is not assigned.");
  if (character.default_melee_weapon && !(character.inventory || []).includes(character.default_melee_weapon)) warnings.push("Assigned melee weapon is no longer in inventory.");
  if (character.default_melee_weapon_secondary && !(character.inventory || []).includes(character.default_melee_weapon_secondary)) warnings.push("Assigned off-hand weapon is no longer in inventory.");
  if (character.default_missile_weapon && !(character.inventory || []).includes(character.default_missile_weapon)) warnings.push("Assigned missile weapon is no longer in inventory.");
  return warnings;
}

function characterContextWarnings(character) {
  const warnings = [];
  const party = modernState.parties.find((item) => item.id === character.party_id);
  const troupe = worldTroupes().find((item) => item.id === character.troupe_id);
  if (party && party.troupe_id && character.troupe_id && party.troupe_id !== character.troupe_id) warnings.push(`Party ${party.name} belongs to ${worldName(worldTroupes(), party.troupe_id)}, but character points to ${worldName(worldTroupes(), character.troupe_id)}.`);
  if (party && party.campaign_id && character.campaign_id && party.campaign_id !== character.campaign_id) warnings.push(`Party campaign ${worldName(worldCampaigns(), party.campaign_id)} differs from character campaign ${worldName(worldCampaigns(), character.campaign_id)}.`);
  if (troupe && troupe.campaign_id && character.campaign_id && troupe.campaign_id !== character.campaign_id) warnings.push(`Troupe campaign ${worldName(worldCampaigns(), troupe.campaign_id)} differs from character campaign ${worldName(worldCampaigns(), character.campaign_id)}.`);
  if (troupe && troupe.guild_id && character.guild_id && troupe.guild_id !== character.guild_id) warnings.push(`Troupe guild ${worldName(worldGuilds(), troupe.guild_id)} differs from character guild ${worldName(worldGuilds(), character.guild_id)}.`);
  if (!character.party_id) warnings.push("No saved party assigned.");
  if (!character.troupe_id) warnings.push("No troupe assigned.");
  if (!character.guild_id) warnings.push("No guild assigned.");
  if (!character.campaign_id) warnings.push("No campaign assigned.");
  return warnings;
}

function characterReadinessRows(character) {
  const armor = equippedArmorSummary(character);
  const equipmentWarnings = characterEquipmentWarnings(character);
  const contextWarnings = characterContextWarnings(character);
  const rows = [
    ["Life", `${character.current_life}/${character.max_life} Life`, character.current_life <= 0 ? "block" : (character.current_life < character.max_life ? "warn" : "ok"), "Fallen characters cannot start ordinary adventures; injured characters can start but should be reviewed."],
    ["Equipment", equipmentWarnings.length ? equipmentWarnings.join(" ") : characterEquipmentSummary(character), equipmentWarnings.length ? "warn" : "ok", "Weapon slot assignments are saved to the roster. Armor and shield are detected from inventory until explicit armor slots are added."],
    ["Armor / shield", `${armor.armor} · ${armor.shield}`, "ok", "Detected carried armor/shield. Class legality is enforced during adventure play where those rules already exist."],
    ["World context", contextWarnings.length ? contextWarnings.join(" ") : characterWorldSummary(character), contextWarnings.length ? "warn" : "ok", "Campaign, guild, troupe, party, and home settlement context used by management pages and adventure setup checks."],
  ];
  if (character.active_session_id) rows.push(["Active session", `Locked by session ${character.active_session_id}.`, "block", "Delete or resume the active session before sending this character into another new adventure."]);
  return rows;
}

function renderReadinessRows(rows) {
  const wrap = el("div", "modern-list");
  for (const [title, body, status, hint] of rows) {
    const row = modernStatusRow(title, body, hint || (status === "ok" ? "Ready." : "Review this before continuing."));
    row.classList.add(status === "ok" ? "modern-row-ok" : "modern-row-warn");
    wrap.appendChild(row);
  }
  return wrap;
}

function characterEquipmentSummary(character) {
  const slots = [
    ["Melee", character.default_melee_weapon || "unassigned"],
    ["Off-hand", character.default_melee_weapon_secondary || "unassigned"],
    ["Missile", character.default_missile_weapon || "unassigned"],
  ];
  return slots.map(([slot, value]) => `${slot}: ${value}`).join(" | ");
}

function modernInventoryWeaponCandidates(character, kind = "all") {
  const items = character.inventory || [];
  const weaponPattern = /weapon|sword|dagger|axe|mace|spear|scimitar|club|hammer|staff|bow|sling|crossbow|handgun|rifle|javelin|arrows?/i;
  const missilePattern = /bow|sling|crossbow|handgun|rifle|javelin|arrows?|missile/i;
  return items.filter((item) => {
    if (!weaponPattern.test(String(item))) return false;
    if (kind === "missile") return missilePattern.test(String(item));
    if (kind === "melee") return !missilePattern.test(String(item));
    return true;
  });
}

function weaponSlotSelect(id, title, items, current) {
  const rows = [["", "Auto / unassigned"], ...items.map((item) => [item, item])];
  const node = select(id, title, rows);
  if (current && rows.some(([value]) => value === current)) node.value = current;
  return node;
}

function renderCharacterEquipmentEditor(character) {
  const editor = el("div", "modern-equipment-editor");
  const meleeItems = modernInventoryWeaponCandidates(character, "melee");
  const missileItems = modernInventoryWeaponCandidates(character, "missile");
  const melee = weaponSlotSelect(
    `modern-${character.id}-melee`,
    "Default melee weapon used when this character enters combat. Choosing Auto lets the backend infer a carried weapon where possible.",
    meleeItems,
    character.default_melee_weapon
  );
  const offhand = weaponSlotSelect(
    `modern-${character.id}-offhand`,
    "Optional off-hand melee weapon. Backend loadout rules decide whether the combination is legal; incompatible pairings are rejected during play.",
    meleeItems,
    character.default_melee_weapon_secondary
  );
  const missile = weaponSlotSelect(
    `modern-${character.id}-missile`,
    "Default missile weapon used for ranged attacks where allowed. Carrying a bow/sling/crossbow without assigning it creates a setup warning.",
    missileItems,
    character.default_missile_weapon
  );
  editor.append(field("Melee slot", melee), field("Off-hand slot", offhand), field("Missile slot", missile));
  editor.appendChild(
    button("Save equipment slots", "Assign these inventory items to the character's melee, off-hand, and missile slots. Empty slots are treated as Auto and may be inferred from inventory by the backend.", async () => {
      await api(`/api/characters/${character.id}/weapon-defaults`, {
        method: "POST",
        body: JSON.stringify({
          default_melee_weapon: melee.value,
          default_melee_weapon_secondary: offhand.value,
          default_missile_weapon: missile.value,
        }),
      });
      setStatus("Equipment slots saved.");
      await refreshCoreAndRender();
    })
  );
  return editor;
}

function renderCharacterInventoryDetails(character) {
  const details = document.createElement("details");
  details.className = "modern-row modern-character-details";
  const summary = document.createElement("summary");
  summary.title = "Show full roster sheet details: assigned equipment slots, inventory, spells, abilities, traits, statuses, and party links.";
  summary.append(el("strong", "", "Full sheet"), el("span", "muted", `${(character.inventory || []).length} inventory item(s)`));
  details.appendChild(summary);
  const body = el("div", "modern-stack");
  const armor = equippedArmorSummary(character);
  body.appendChild(modernStatusRow("Core stats", `Attack +${character.attack_bonus || 0} · Defense +${character.defense_bonus || 0} · Save +${character.save_bonus || 0} · Madness ${character.madness || 0}`, "Permanent roster modifiers and Madness. Adventure-specific temporary effects are shown during play."));
  body.appendChild(modernStatusRow("World assignment", characterWorldSummary(character), "Campaign, Guild, Troupe, Party, and home settlement context. Use the quick links above to edit assignments."));
  body.appendChild(renderReadinessRows(characterReadinessRows(character)));
  body.appendChild(modernStatusRow("Equipment slots", characterEquipmentSummary(character), "Assigned defaults used by the adventure combat sheet when a fight starts."));
  body.appendChild(renderCharacterEquipmentEditor(character));
  body.appendChild(modernStatusRow("Armor / shield", `${armor.armor} · ${armor.shield}`, "Detected from inventory. Explicit armor/shield slot persistence is not added yet, so combat and save rules still use existing inventory detection."));
  body.appendChild(modernStatusRow("Inventory", (character.inventory || []).join(", ") || "No inventory.", "Everything currently stored on this roster character, including weapons, armor, supplies, special items, scrolls, and treasure items."));
  body.appendChild(modernStatusRow("Spells", (character.spells || []).join(", ") || "No spells.", "Known spells/prayers available to this character where their class supports them."));
  body.appendChild(modernStatusRow("Abilities", (character.abilities || []).join(", ") || "No abilities listed.", "Class and rules abilities tracked for this roster character."));
  body.appendChild(modernStatusRow("Learned skills", [...(character.learned_expert_skills || []), ...(character.learned_heroic_skills || []), ...(character.learned_legendary_skills || [])].join(", ") || "No learned tier skills.", "Expert, Heroic, and Legendary learned skills on this roster character."));
  body.appendChild(modernStatusRow("Traits / statuses", [...(character.class_traits || []), ...(character.statuses || [])].join(", ") || "None.", "Class traits and current roster statuses."));
  const referenceLinks = actions();
  referenceLinks.append(
    link("Class Rules", `/modern/rules-reference?help=${encodeURIComponent(character.class_name || character.class_id || "class")}`, "Open Rules Reference search for this character class.", "link-button secondary"),
    link("Equipment Rules", ruleReferenceHref("equipment_shop", "equipment inventory carry limits"), "Open equipment/inventory rules reference.", "link-button secondary"),
    link("Character Sheet Rules", ruleReferenceHref("character_management_deep_polish", "character sheet equipment slots"), "Open the dashboard character-sheet reference entry.", "link-button secondary")
  );
  body.appendChild(referenceLinks);
  details.appendChild(body);
  return details;
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
    const adventureId = String(adventure.id || "");
    const adventureSource = String(adventure.source || "");
    const adventureName = adventure.name || adventure.title || adventureId;
    const tagLabel = adventure.tag_lead_type
      ? `Adventures Guild ${modernTitleFromKey(adventure.tag_lead_type)} · ${adventureName}${adventure.tag_prompt_count ? ` · ${adventure.tag_prompt_count} prompts` : ""}`
      : adventureName;
    if (kind === "ai" && !adventureId.startsWith("ai-")) continue;
    if (kind === "imported" && (adventureId === "random" || adventureId === "ai-adventure" || adventureId.startsWith("ai-") || adventureSource === "rules")) continue;
    if ((kind === "random" || kind === "ruleset") && adventure.id !== "random") continue;
    rows.push([adventure.id, tagLabel]);
  }
  return rows;
}

function tagGeneratedAdventures() {
  const generatedIds = modernState.campaign?.tag_generated_adventure_ids || [];
  const generatedIdSet = new Set(generatedIds);
  const order = new Map(generatedIds.map((id, index) => [id, index]));
  return (modernState.adventures || [])
    .filter((adventure) => adventure.tag_lead_type || generatedIdSet.has(adventure.id) || String(adventure.id || "").startsWith("tag-"))
    .sort((left, right) => (order.get(right.id) ?? -1) - (order.get(left.id) ?? -1) || String(right.id || "").localeCompare(String(left.id || "")));
}

function tagLeadStatusRows(adventure) {
  const campaign = modernState.campaign || {};
  const openCloseout = (campaign.tag_closeout_tasks || []).filter((task) => !task.resolved).length;
  const pendingXp = (campaign.tag_xp_markers || []).filter((marker) => !marker.applied).length;
  const routeCount = (campaign.tag_adventure_routes || []).length;
  return [
    ["Lead", adventure.tag_lead_detail || adventure.name || adventure.id, "Generated Adventures Guild lead detail/result. Use this to confirm you created the intended Rumor, Treasure Map, Thematic Dungeon, or Guild Job."],
    ["Prompts", `${adventure.tag_prompt_count || 0} room prompt(s)`, "Prompt count from the generated module metadata. More prompts means more room-aware Adventures Guild Action shortcuts during exploration."],
    ["Route signoff", `${routeCount} route marker(s) in campaign`, "Route markers are global campaign signoff state; review latest markers before closing the lead."],
    ["Closeout", `${openCloseout} open closeout · ${pendingXp} pending XP`, "Generated adventures should be reviewed against closeout and XP state before starting another lead."],
  ];
}

function renderTagLeadSelectorPanel(adventureSelect = null) {
  const panel = card("Generated Adventures Guild Leads", "Installed Adventures Guild modules with lead type, source detail, prompt coverage, director guidance, and closeout wizard state. Use this before Start Adventure so you know why the module exists and what still needs review.");
  const leads = tagGeneratedAdventures();
  if (!leads.length) {
    panel.appendChild(el("p", "muted", "No generated Adventures Guild modules are installed yet. Create a Rumor, Treasure Map, Thematic Dungeon, or Guild Job lead first."));
    return panel;
  }
  for (const adventure of leads.slice(0, 8)) {
    const row = el("div", "modern-row");
    row.title = `${adventure.notes || "Generated Adventures Guild module."} ${adventure.tag_pdf_pages ? `Source ${adventure.tag_pdf_pages}.` : ""}`;
    row.append(
      el("strong", "", adventure.name || adventure.id),
      el("span", "muted", `${modernTitleFromKey(adventure.tag_lead_type || "tag lead")} · ${adventure.tag_scene || adventure.tag_lead_detail || "generated module"}${adventure.tag_pdf_pages ? ` · ${adventure.tag_pdf_pages}` : ""}`)
    );
    for (const [title, body, hint] of tagLeadStatusRows(adventure)) {
      row.appendChild(modernStatusRow(title, body, hint));
    }
    const rowActions = actions();
    rowActions.append(
      button("Select Lead", "Switch Go Adventure to Imported Adventure Module and select this generated Adventures Guild lead.", async () => {
        const type = document.getElementById("modern-adventure-type");
        if (type) type.value = "imported";
        if (adventureSelect) {
          adventureSelect.replaceChildren(...optionRows(adventureOptions("imported")));
          adventureSelect.value = adventure.id;
        }
        writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: adventure.id || "" });
        setStatus(`Selected ${adventure.name || adventure.id}. Review setup and closeout gates before starting.`);
      }),
      link("Rules", ruleReferenceHref("tag_generated_prompt_playtest", "Adventures Guild generated prompt playtest"), "Open the Rules Reference entry for generated Adventures Guild prompt playtest and selector workflow.", "link-button secondary"),
      link("Signoff Table", "/modern/tables?help=tag_generated_adventure_signoff_table", "Open the Tables row for generated Adventures Guild lifecycle, route, reward, XP, guidance, and closeout signoff checkpoints.", "link-button secondary")
    );
    row.appendChild(rowActions);
    panel.appendChild(row);
  }
  return panel;
}

function tagRumorNumber(adventure) {
  const text = `${adventure.tag_lead_detail || ""} ${adventure.name || ""} ${adventure.id || ""}`;
  const explicit = text.match(/rumor\s+(\d{1,2})/i);
  if (explicit) return Number(explicit[1]);
  const tagId = String(adventure.id || "");
  const suffix = tagId.match(/tag-rumor-(\d{1,2})/i);
  return suffix ? Number(suffix[1]) : 0;
}

function tagRumorAuditRows(adventure) {
  const number = tagRumorNumber(adventure);
  return [
    ["Rumor result", number ? `Rumor ${number}` : "Generated Rumor lead", "Use this to confirm the intended TAG rumor result before starting or resuming the module."],
    ["Printed scene", adventure.tag_scene || adventure.tag_pdf_pages || "Check generated module metadata", "Scene/page metadata comes from the generated adventure manifest; exact rule text stays in the PDF/player signoff."],
    ["Play focus", "Entry choice -> complication branch -> final reward/XP closeout", "Rumor leads should be played as a short settlement story, not only as a combat room."],
    ["Signoff", "Route, reward, XP, Guild/finance, and closeout review", "Use the TAG prompt buttons during exploration, then review TAG Action Log before starting another lead."],
  ];
}

function renderRumorLeadAuditPanel(adventureSelect = null) {
  const panel = card("TAG Rumor Leads", "Audit installed Rumor Scene modules before play. Each row links to the app-owned Rumor playthrough reference and helps confirm scene, prompt, route, reward, and XP signoff.");
  const rumors = tagGeneratedAdventures().filter((adventure) => String(adventure.tag_lead_type || "").toLowerCase() === "rumor");
  if (!rumors.length) {
    panel.appendChild(el("p", "muted", "No Rumor Scene modules are installed yet. Create a Rumor lead in Go Adventure, then use this panel to review it before Start Adventure."));
    const emptyActions = actions();
    emptyActions.append(
      link("Rumor Rules", ruleReferenceHref("tag_rumor_playthrough_audit", "TAG rumor playthrough audit"), "Open the Rules Reference entry for the app-owned Rumor playthrough audit workflow.", "link-button secondary"),
      link("Rumor Table", "/modern/tables?help=tag_rumor_playthrough_audit_table", "Open the modern Tables entry for Rumor audit surfaces and PDF boundaries.", "link-button secondary")
    );
    panel.appendChild(emptyActions);
    return panel;
  }
  for (const adventure of rumors.slice(0, 12)) {
    const row = el("div", "modern-row");
    row.title = "Rumor audit row: confirms which Rumor module this is, what scene metadata exists, and which closeout checks should be reviewed before another lead.";
    row.append(
      el("strong", "", adventure.name || adventure.id),
      el("span", "muted", `${adventure.tag_lead_detail || "Rumor Scene"}${adventure.tag_pdf_pages ? ` · ${adventure.tag_pdf_pages}` : ""}`)
    );
    for (const [title, body, hint] of tagRumorAuditRows(adventure)) {
      row.appendChild(modernStatusRow(title, body, hint));
    }
    const rowActions = actions();
    rowActions.append(
      button("Select Rumor", "Switch Start New Adventure to Imported Adventure Module and select this Rumor lead.", async () => {
        const type = document.getElementById("modern-adventure-type");
        if (type) type.value = "imported";
        if (adventureSelect) {
          adventureSelect.replaceChildren(...optionRows(adventureOptions("imported")));
          adventureSelect.value = adventure.id;
        }
        writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: adventure.id || "" });
        setStatus(`Selected Rumor lead ${adventure.name || adventure.id}. Review setup and closeout gates before starting.`);
      }),
      link("Rules", ruleReferenceHref("tag_rumor_playthrough_audit", "TAG rumor playthrough audit"), "Open the Rules Reference entry for Rumor playthrough audit guidance.", "link-button secondary"),
      link("Table", "/modern/tables?help=tag_rumor_playthrough_audit_table", "Open the modern Tables row documenting this Rumor audit surface.", "link-button secondary")
    );
    row.appendChild(rowActions);
    panel.appendChild(row);
  }
  return panel;
}

function renderRumorSignoffChecklist() {
  const panel = card("Rumor Signoff Checklist", "Use this app-owned checklist after a TAG Rumor module. It helps you remember what to review without replacing the printed scene rules.");
  const checks = [
    ["Entry choice", "Record the party's approach, refusal, stealth, parley, or direct confrontation.", "Entry state explains why later route markers exist."],
    ["Complication", "Resolve Clue costs, red herrings, ambushes, peaceful/hostile branches, and profile-specific rolls.", "Use TAG Actions so the Campaign log shows why the route changed."],
    ["Finale", "Confirm final foe/procedure, reward, item, bounty, capture-alive route, and any scene restriction.", "The generated room is a play aid; the printed result remains the authority."],
    ["Closeout", "Review pending XP, Guild obligations, banking/storage, guidance tasks, and the TAG Action Log.", "Do this before creating the next lead so unresolved state is visible."],
  ];
  for (const [title, body, hint] of checks) {
    panel.appendChild(modernStatusRow(title, body, hint));
  }
  const panelActions = actions();
  panelActions.append(
    link("Rumor Rules", ruleReferenceHref("tag_rumor_playthrough_audit", "TAG rumor playthrough audit"), "Open the Rules Reference entry for Rumor signoff guidance.", "link-button secondary"),
    link("Closeout Rules", ruleReferenceHref("tag_closeout_checklist_automation", "TAG closeout checklist automation"), "Open the closeout checklist reference entry.", "link-button secondary")
  );
  panel.appendChild(panelActions);
  return panel;
}

function tagTreasureMapDestination(adventure) {
  const text = `${adventure.tag_lead_detail || ""} ${adventure.name || ""} ${adventure.id || ""}`;
  const explicit = text.match(/treasure map\s+(\d{1,2})/i) || text.match(/map leads to\s+(\d{1,2})/i);
  if (explicit) return Number(explicit[1]);
  const tagId = String(adventure.id || "");
  const suffix = tagId.match(/tag-treasure-map-(\d{1,2})/i);
  return suffix ? Number(suffix[1]) : 0;
}

function tagTreasureMapDestinationGuidance(number) {
  const guidance = {
    1: "Underground caves: roll/log the d6+3 room target, skip entrance content, dead-end unopened exits after the target count, then resolve the boosted final Boss and double maximum treasure.",
    2: "Forgotten temple: record idol value, cult leader scroll chance, cultist treasure, XP, and how the heavy idol is carried or stored.",
    3: "Hostile humanoid camp: choose report, stealth theft, or fight before resolving reward, loot, reinforcements, and XP.",
    4: "Underground structure: track generated treasure as deferred state and move it to the final Boss before closeout.",
    5: "Boss-only underground structure: convert monsters to Boss encounters, defer treasure, and enforce final reward minimums.",
    6: "Lich chamber: resolve entry death magic, lich Life, defenders, treasure, and map/scroll follow-up before closeout.",
  };
  return guidance[number] || "Check generated module metadata for the selected Map Leads To destination.";
}

function tagTreasureMapAuditRows(adventure) {
  const number = tagTreasureMapDestination(adventure);
  return [
    ["Destination", number ? `Map Leads To ${number}` : "Generated Treasure Map destination", "Confirm this is the intended destination before Start Adventure; Follow Map and Map Leads To are separate signoff steps."],
    ["Procedure", tagTreasureMapDestinationGuidance(number), "Destination metadata comes from the generated manifest. Exact room count, reward, and procedure values remain with the PDF/player signoff."],
    ["Current room treasure", "If exploration says hidden treasure was found, use Claim Treasure for that room. That does not replace the Map Leads To destination procedure.", "Claim Treasure handles the local room hoard; TAG Actions record map procedure and closeout decisions."],
    ["Play focus", "Follow-map result -> destination procedure -> deferred/reward treasure -> closeout", "Treasure Map leads are about proving the map, choosing risk, and making reward accounting visible."],
    ["Signoff", "Route, procedure rolls, treasure transfer, XP, Guild/finance, and storage review", "Use TAG Actions during exploration, then review TAG Action Log and banking/storage before starting another lead."],
  ];
}

function renderTreasureMapLeadAuditPanel(adventureSelect = null) {
  const panel = card("TAG Treasure Map Leads", "Audit installed Treasure Map destination modules before play. Each row helps confirm destination, procedure, reward, treasure storage, XP, and closeout signoff.");
  const maps = tagGeneratedAdventures().filter((adventure) => String(adventure.tag_lead_type || "").toLowerCase() === "treasure_map");
  if (!maps.length) {
    panel.appendChild(el("p", "muted", "No Treasure Map destination modules are installed yet. Create a Treasure Map lead in Go Adventure, then use this panel to review it before Start Adventure."));
    const emptyActions = actions();
    emptyActions.append(
      link("Map Rules", ruleReferenceHref("tag_treasure_map_playthrough_audit", "TAG treasure map playthrough audit"), "Open the Rules Reference entry for the app-owned Treasure Map playthrough audit workflow.", "link-button secondary"),
      link("Map Table", "/modern/tables?help=tag_treasure_map_playthrough_audit_table", "Open the modern Tables entry for Treasure Map audit surfaces and PDF boundaries.", "link-button secondary")
    );
    panel.appendChild(emptyActions);
    return panel;
  }
  for (const adventure of maps.slice(0, 12)) {
    const row = el("div", "modern-row");
    row.title = "Treasure Map audit row: confirms which map destination this is and which procedure, reward, XP, Guild, banking, and storage checks should be reviewed.";
    row.append(
      el("strong", "", adventure.name || adventure.id),
      el("span", "muted", `${adventure.tag_lead_detail || "Treasure Map destination"}${adventure.tag_pdf_pages ? ` · ${adventure.tag_pdf_pages}` : ""}`)
    );
    for (const [title, body, hint] of tagTreasureMapAuditRows(adventure)) {
      row.appendChild(modernStatusRow(title, body, hint));
    }
    const rowActions = actions();
    rowActions.append(
      button("Select Map", "Switch Start New Adventure to Imported Adventure Module and select this Treasure Map lead.", async () => {
        const type = document.getElementById("modern-adventure-type");
        if (type) type.value = "imported";
        if (adventureSelect) {
          adventureSelect.replaceChildren(...optionRows(adventureOptions("imported")));
          adventureSelect.value = adventure.id;
        }
        writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: adventure.id || "" });
        setStatus(`Selected Treasure Map lead ${adventure.name || adventure.id}. Review setup and closeout gates before starting.`);
      }),
      link("Rules", ruleReferenceHref("tag_treasure_map_playthrough_audit", "TAG treasure map playthrough audit"), "Open the Rules Reference entry for Treasure Map playthrough audit guidance.", "link-button secondary"),
      link("Table", "/modern/tables?help=tag_treasure_map_playthrough_audit_table", "Open the modern Tables row documenting this Treasure Map audit surface.", "link-button secondary")
    );
    row.appendChild(rowActions);
    panel.appendChild(row);
  }
  return panel;
}

function renderTreasureMapSignoffChecklist() {
  const panel = card("Treasure Map Signoff Checklist", "Use this app-owned checklist after a TAG Treasure Map destination. It focuses on map verification, destination procedure, reward accounting, and closeout.");
  const checks = [
    ["Map result", "Confirm the Follow Treasure Map result, stored/Guild cartographer bonus, and Map Leads To destination.", "The purchased map roll and the generated destination are related but should both be visible in the log."],
    ["Destination procedure", "Resolve destination-specific room count, report/stealth choice, deferred treasure, boss-only conversion, or death-magic setup.", "Use TAG Actions so the procedure is recorded before final reward handling."],
    ["Treasure", "Move deferred treasure, idol value, report reward, lich treasure, magic items, or Boss treasure into the correct party/Guild/bank/storage workflow.", "Treasure Maps often need accounting after the fight, not just a combat victory."],
    ["Closeout", "Review pending XP, Guild share, banking/storage, guidance tasks, and the TAG Action Log before creating another map lead.", "This avoids losing map bonuses, deferred treasure, or unpaid Guild obligations."],
  ];
  for (const [title, body, hint] of checks) {
    panel.appendChild(modernStatusRow(title, body, hint));
  }
  const panelActions = actions();
  panelActions.append(
    link("Map Rules", ruleReferenceHref("tag_treasure_map_playthrough_audit", "TAG treasure map playthrough audit"), "Open the Rules Reference entry for Treasure Map signoff guidance.", "link-button secondary"),
    link("Banking", "/modern/banking", "Open Banking and Finance to handle bank deposits, hidden troves, Guild share follow-up, and storage consequences.", "link-button secondary")
  );
  panel.appendChild(panelActions);
  return panel;
}

function tagThematicDungeonNumber(adventure) {
  const text = `${adventure.tag_lead_detail || ""} ${adventure.name || ""} ${adventure.id || ""}`;
  const explicit = text.match(/thematic dungeon\s+(\d{1,2})/i);
  if (explicit) return Number(explicit[1]);
  const themeNames = [
    ["ghastly mine", 1],
    ["giant's lair", 2],
    ["dragon's lair", 3],
    ["fiendish abyss", 4],
    ["minotaur maze", 5],
    ["bandit hideout", 6],
  ];
  const lower = text.toLowerCase();
  for (const [name, number] of themeNames) {
    if (lower.includes(name)) return number;
  }
  const tagId = String(adventure.id || "");
  const suffix = tagId.match(/tag-thematic-dungeon-(\d{1,2})/i);
  return suffix ? Number(suffix[1]) : 0;
}

function tagThematicAuditRows(adventure) {
  const number = tagThematicDungeonNumber(adventure);
  return [
    ["Theme result", number ? `Thematic Dungeon ${number}` : "Generated Thematic Dungeon", "Confirm this is the intended TAG thematic result before Start Adventure; themes change room count, monster logic, treasure, or final-room handling."],
    ["Procedure", adventure.tag_scene || adventure.tag_lead_detail || "Check generated module metadata", "Theme metadata comes from the generated manifest. Exact room count, replacement rolls, and special procedure values remain with the PDF/player signoff."],
    ["Play focus", "Target rooms -> theme procedure -> final-room exception -> reward/XP closeout", "Thematic Dungeons should be treated as altered dungeon engines, not just renamed random dungeons."],
    ["Signoff", "Replacement rolls, Clue spends, route markers, reward, XP, Guild/finance, and storage review", "Use TAG Actions during exploration, then review TAG Action Log before starting another lead."],
  ];
}

function renderThematicDungeonLeadAuditPanel(adventureSelect = null) {
  const panel = card("TAG Thematic Dungeon Leads", "Audit installed Thematic Dungeon modules before play. Each row helps confirm target rooms, special procedure, final-room exception, reward, XP, and closeout signoff.");
  const themes = tagGeneratedAdventures().filter((adventure) => String(adventure.tag_lead_type || "").toLowerCase() === "thematic_dungeon");
  if (!themes.length) {
    panel.appendChild(el("p", "muted", "No Thematic Dungeon modules are installed yet. Create a Thematic Dungeon lead in Go Adventure, then use this panel to review it before Start Adventure."));
    const emptyActions = actions();
    emptyActions.append(
      link("Theme Rules", ruleReferenceHref("tag_thematic_dungeon_playthrough_audit", "TAG thematic dungeon playthrough audit"), "Open the Rules Reference entry for the app-owned Thematic Dungeon playthrough audit workflow.", "link-button secondary"),
      link("Theme Table", "/modern/tables?help=tag_thematic_dungeon_playthrough_audit_table", "Open the modern Tables entry for Thematic Dungeon audit surfaces and PDF boundaries.", "link-button secondary")
    );
    panel.appendChild(emptyActions);
    return panel;
  }
  for (const adventure of themes.slice(0, 12)) {
    const row = el("div", "modern-row");
    row.title = "Thematic Dungeon audit row: confirms which theme this is and which room-count, procedure, reward, XP, Guild, banking, and storage checks should be reviewed.";
    row.append(
      el("strong", "", adventure.name || adventure.id),
      el("span", "muted", `${adventure.tag_lead_detail || "Thematic Dungeon"}${adventure.tag_pdf_pages ? ` · ${adventure.tag_pdf_pages}` : ""}`)
    );
    for (const [title, body, hint] of tagThematicAuditRows(adventure)) {
      row.appendChild(modernStatusRow(title, body, hint));
    }
    const rowActions = actions();
    rowActions.append(
      button("Select Theme", "Switch Start New Adventure to Imported Adventure Module and select this Thematic Dungeon lead.", async () => {
        const type = document.getElementById("modern-adventure-type");
        if (type) type.value = "imported";
        if (adventureSelect) {
          adventureSelect.replaceChildren(...optionRows(adventureOptions("imported")));
          adventureSelect.value = adventure.id;
        }
        writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: adventure.id || "" });
        setStatus(`Selected Thematic Dungeon lead ${adventure.name || adventure.id}. Review setup and closeout gates before starting.`);
      }),
      link("Rules", ruleReferenceHref("tag_thematic_dungeon_playthrough_audit", "TAG thematic dungeon playthrough audit"), "Open the Rules Reference entry for Thematic Dungeon playthrough audit guidance.", "link-button secondary"),
      link("Table", "/modern/tables?help=tag_thematic_dungeon_playthrough_audit_table", "Open the modern Tables row documenting this Thematic Dungeon audit surface.", "link-button secondary")
    );
    row.appendChild(rowActions);
    panel.appendChild(row);
  }
  return panel;
}

function renderThematicDungeonSignoffChecklist() {
  const panel = card("Thematic Dungeon Signoff Checklist", "Use this app-owned checklist after a TAG Thematic Dungeon. It focuses on target-room procedure, theme exceptions, reward handling, and closeout.");
  const checks = [
    ["Target and theme", "Confirm room target and core procedure: nine-room mine, HCL+5 giant/abyss, four-room dragon, d6+5 maze, or HCL+3 hideout.", "Theme target changes when the dungeon should end and what happens to unvisited exits."],
    ["Procedure rolls", "Resolve undead replacement, cave-ins, boulder throw, dragon reveal, prisoner table, maze lost/event checks, stolen goods, or capture-alive choice.", "Use TAG Actions so the changed dungeon logic stays visible in the campaign log."],
    ["Finale", "Confirm final-room size/route, final foe, special restrictions, reward, treasure conversion, and XP.", "Generated encounters are proxies where needed; the printed theme procedure remains the authority."],
    ["Closeout", "Review pending XP, Guild share, banking/storage, guidance tasks, route markers, and the TAG Action Log before creating another lead.", "Thematic dungeons tend to leave more state behind than ordinary random dungeons."],
  ];
  for (const [title, body, hint] of checks) {
    panel.appendChild(modernStatusRow(title, body, hint));
  }
  const panelActions = actions();
  panelActions.append(
    link("Theme Rules", ruleReferenceHref("tag_thematic_dungeon_playthrough_audit", "TAG thematic dungeon playthrough audit"), "Open the Rules Reference entry for Thematic Dungeon signoff guidance.", "link-button secondary"),
    link("TAG Actions", "/modern/go-adventure", "Return to Go Adventure to review generated leads, closeout, signoff, and TAG Action Log state.", "link-button secondary")
  );
  panel.appendChild(panelActions);
  return panel;
}

function sessionRecencyKey(session) {
  return String(session?.updated_at || session?.saved_at || session?.created_at || session?.id || "");
}

function latestSessionPerParty(sessions) {
  const latest = new Map();
  for (const session of sessions || []) {
    const partyId = session?.party_id || session?.id || "";
    const current = latest.get(partyId);
    if (!current || sessionRecencyKey(session).localeCompare(sessionRecencyKey(current)) > 0) {
      latest.set(partyId, session);
    }
  }
  return Array.from(latest.values()).sort((a, b) => sessionRecencyKey(b).localeCompare(sessionRecencyKey(a)));
}

function adventureReadinessRows(selectedPartyId, { adventureType = "random", adventureId = "", profileId = "", mapLimitValue = 60 } = {}) {
  const party = modernState.parties.find((item) => item.id === selectedPartyId);
  const baseRows = [
    ["Adventure module", adventureType === "random" ? `Random dungeon · ${profileId || "profile"}` : (adventureId ? `${adventureType} · ${adventureId}` : "Choose an installed module"), adventureType === "random" || adventureId ? "ok" : "block", "Imported and AI adventure types require a selected installed module."],
    ["Map limit", `${Number(mapLimitValue || 0)} map element cap`, Number(mapLimitValue || 0) > 0 ? "ok" : "block", "Unlimited map mode needs a positive cap before end-boss pressure."],
  ];
  if (!party) return [["Choose party", "Pick a saved party before starting a new adventure.", "block", "A saved party is required before a new session can be created."], ...baseRows];
  const memberCount = (party.character_ids || []).length;
  const members = (party.character_ids || []).map((id) => modernState.characters.find((character) => character.id === id)).filter(Boolean);
  const mismatched = members.filter((member) => characterContextWarnings(member).some((warning) => !warning.startsWith("No saved party")));
  const equipmentWarnings = members.filter((member) => characterEquipmentWarnings(member).length);
  const fallen = members.filter((member) => member.current_life <= 0);
  const injured = members.filter((member) => member.current_life > 0 && member.current_life < member.max_life);
  const locked = members.filter((member) => member.active_session_id);
  const activeTroupe = worldTroupes().find((item) => item.id === party.troupe_id);
  const rows = [
    ["Party", `${party.name} · ${memberCount}/4 members`, memberCount === 4 ? "ok" : "block", "A normal 4AD party needs exactly four members."],
    ["Troupe", `${worldName(worldTroupes(), party.troupe_id, "No troupe assigned")} · home ${activeTroupe?.home_settlement_id ? worldName(worldSettlements(), activeTroupe.home_settlement_id) : "Unassigned"}`, party.troupe_id ? "ok" : "warn", "Party troupe sets campaign/guild/home context for characters when assigned."],
    ["Campaign", worldName(worldCampaigns(), party.campaign_id, "No campaign assigned"), party.campaign_id ? "ok" : "warn", "Campaign context is app world-builder bookkeeping and should be set before play."],
    ...baseRows,
  ];
  if (fallen.length) rows.push(["Fallen members", fallen.map((member) => member.name).join(", "), "block", "Fallen characters cannot start normal adventures. Heal/resurrect or change party."]);
  if (locked.length) rows.push(["Active locks", `${locked.length} member(s) already have an active session: ${locked.map((member) => member.name).join(", ")}.`, "block", "Delete or resume the active session before starting another new adventure with these characters."]);
  if (injured.length) rows.push(["Injured members", injured.map((member) => `${member.name} ${member.current_life}/${member.max_life}`).join(", "), "warn", "Injured characters can start, but this should be a deliberate choice."]);
  if (equipmentWarnings.length) rows.push(["Equipment warnings", equipmentWarnings.map((member) => `${member.name}: ${characterEquipmentWarnings(member).join(" ")}`).join(" "), "warn", "Open Character Management to assign weapon slots or review inventory."]);
  if (mismatched.length) rows.push(["Context warnings", mismatched.map((member) => `${member.name}: ${characterContextWarnings(member).join(" ")}`).join(" "), "warn", "Use Party or Troupe Management to resync campaign/guild/troupe context before play."]);
  return rows;
}

function adventureReadinessBlocks(rows) {
  return rows.filter(([, , status]) => status === "block");
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

async function loadArtwork() {
  if (!modernState.artwork.length) {
    const payload = await api("/api/rules/artwork");
    modernState.artwork = Array.isArray(payload) ? payload : (payload.entries || []);
  }
  return modernState.artwork;
}

function assetUrl(assetPath) {
  if (!assetPath) return "";
  return `/assets/${String(assetPath).split("/").map(encodeURIComponent).join("/")}`;
}

function artAssetUrl(entry) {
  return assetUrl(entry?.asset_path);
}

function artworkForPage(page) {
  return modernState.artwork.filter((entry) => (entry.dashboard_pages || []).includes(page));
}

function artworkForReference(entry) {
  const id = entry?.id || "";
  const category = entry?.category || "";
  return modernState.artwork.filter((art) => (art.reference_ids || []).includes(id) || (art.category && art.category === category));
}

function artworkForTable(key) {
  return modernState.artwork.filter((art) => (art.table_keys || []).includes(key));
}

function primaryApplicationArtworkForPage(page, { requirePresent = true } = {}) {
  const entries = artworkForPage(page).filter((entry) => entry.category === "app_assets");
  if (!requirePresent) return entries[0] || null;
  return entries.find((entry) => entry.asset_exists !== false) || null;
}

function renderArtworkFigure(entry, className, caption = "") {
  const figure = el("figure", className);
  figure.title = entry.hover || entry.summary || "Application artwork.";
  const image = document.createElement("img");
  image.src = artAssetUrl(entry);
  image.alt = caption || entry.title || "Application artwork";
  image.loading = "lazy";
  image.addEventListener("error", () => {
    figure.remove();
  }, { once: true });
  figure.appendChild(image);
  if (caption) figure.appendChild(el("figcaption", "", caption));
  return figure;
}

function adventureTypeCount(type) {
  return modernState.adventures.filter((adventure) => adventure.type === type || adventure.source === type || adventure.module_type === type).length;
}

function completedAdventureCount() {
  return modernState.adventures.filter((adventure) => adventure.completed || adventure.status === "completed" || adventure.is_completed).length;
}

function moduleInUseCount() {
  const activeIds = new Set((modernState.sessions || []).filter((session) => session.mode !== "complete").map((session) => session.adventure_id).filter(Boolean));
  return modernState.adventures.filter((adventure) => activeIds.has(adventure.id || adventure.adventure_id)).length;
}

function namesList(rows, getName = (row) => row.name || row.id || "Unnamed", empty = "No matching records.") {
  const values = rows.map(getName).filter(Boolean);
  return values.length ? values : [empty];
}

function snapshotTaskDetails(rows, getLine) {
  return rows.length ? rows.map(getLine) : ["No matching issues."];
}

function compactSnapshotDetails(...groups) {
  const rows = groups.flat().filter((line) => line && line !== "No matching issues.");
  return rows.length ? rows : ["No matching issues."];
}

function renderPageCompanion(page) {
  const campaign = modernState.campaign || {};
  const counts = tagWorkflowCounts();
  const activeSessions = (modernState.sessions || []).filter((session) => session.mode !== "complete");
  const injured = modernState.characters.filter((character) => character.current_life > 0 && character.current_life < character.max_life);
  const fallen = modernState.characters.filter((character) => character.current_life <= 0);
  const equipmentWarnings = modernState.characters.filter((character) => characterEquipmentWarnings(character).length);
  const openGuidance = openGuidanceTasks();
  const openCloseout = closeoutTasksFor([]);
  const missingArt = modernState.artwork.filter((entry) => entry.asset_exists === false);
  const companion = el("section", "modern-page-companion");
  const addRows = (title, rows, href = "") => {
    companion.appendChild(el("h3", "", title));
    for (const [rowTitle, body, hint, detail] of rows) companion.appendChild(snapshotStatusRow(rowTitle, body, hint, detail));
    if (href) {
      const row = actions();
      row.appendChild(link("Open Details", href, `Open the main controls for ${title}.`, "link-button secondary"));
      companion.appendChild(row);
    }
  };
  const worldCounts = [
    worldCampaigns().length,
    worldGuilds().length,
    worldTroupes().length,
    worldSettlements().length,
    worldSettlements("troublesome").length,
  ];
  const definitions = {
    home: ["Dashboard", [
      ["Active sessions", `${activeSessions.length} in progress`, "Resume or close sessions before reusing locked characters.", namesList(activeSessions, (session) => `${session.save_label || session.id}: ${session.adventure_type || session.adventure_id || "adventure"} (${session.mode || "active"})`)],
      ["Open guidance", `${openGuidance.length} task(s)`, "Collapsed dashboard checks are at the bottom of the page.", snapshotTaskDetails(openGuidance, (task) => `${modernTitleFromKey(task.priority || "recommended")}: ${task.title || "Guidance task"} - ${task.body || task.reference || "No detail."}`)],
      ["Modules", `${modernState.adventures.length} installed`, "Adventure Management now owns generated, imported, and AI-authored modules."],
    ]],
    characters: ["Roster Snapshot", [
      ["Roster", `${modernState.characters.length} character(s)`, "Full character sheets remain in Character Management below."],
      ["Health", `${injured.length} injured · ${fallen.length} fallen`, "Fallen heroes block normal adventure starts.", compactSnapshotDetails(snapshotTaskDetails(injured, (character) => `${character.name}: injured at ${character.current_life}/${character.max_life} Life`), snapshotTaskDetails(fallen, (character) => `${character.name}: fallen at ${character.current_life}/${character.max_life} Life`))],
      ["Equipment", `${equipmentWarnings.length} warning(s)`, "Open individual sheets to assign weapon slots or review carried gear.", snapshotTaskDetails(equipmentWarnings, (character) => `${character.name}: ${characterEquipmentWarnings(character).join("; ")}`)],
    ]],
    troupes: ["Troupe Snapshot", [
      ["Members", `${counts.troupeMembers} member(s) · ${counts.activeMembers}/4 active`, "Active troupe members should match the intended party."],
      ["Parties", `${modernState.parties.filter((party) => party.troupe_id === "troupe1").length} assigned to Troupe1`, "Party Management owns party-to-troupe assignment."],
      ["Home", campaign.settlement_name || "Home Settlement", "Home settlement drives travel and downtime context."],
    ]],
    guild: ["Guild Snapshot", [
      ["Membership", counts.guildActive ? "active member" : "not active", "Guild benefits require active membership."],
      ["Coffers", `${counts.guildCoffers} gp · benefits ${counts.guildBenefits ? "active" : "inactive"}`, "Coffers affect benefits, upkeep, resurrection funding, and loot-share obligations."],
      ["Closeout", `${unresolvedCloseoutTasks(["guild"]).length} Guild task(s)`, "Resolve Guild prompts after Guild-linked adventures."],
    ]],
    parties: ["Party Snapshot", [
      ["Saved parties", `${modernState.parties.length} party record(s)`, "A normal party should have exactly four characters."],
      ["Active locks", `${activeSessions.length} active session(s)`, "Characters in active sessions cannot start another adventure.", namesList(activeSessions, (session) => `${session.save_label || session.id}: party ${session.party_id || "unknown"}`)],
      ["Roster warnings", `${fallen.length} fallen · ${equipmentWarnings.length} equipment`, "Resolve hard blocks before Go Adventure.", compactSnapshotDetails(snapshotTaskDetails(fallen, (character) => `${character.name}: fallen`), snapshotTaskDetails(equipmentWarnings, (character) => `${character.name}: ${characterEquipmentWarnings(character).join("; ")}`))],
    ]],
    equipment: ["Shop Snapshot", [
      ["Roster shoppers", `${modernState.characters.length} character(s)`, "Choose a character before buying or selling."],
      ["Equipment warnings", `${equipmentWarnings.length} character(s)`, "Warnings usually mean missing weapon-slot assignment or inventory review.", snapshotTaskDetails(equipmentWarnings, (character) => `${character.name}: ${characterEquipmentWarnings(character).join("; ")}`)],
      ["Rules context", "Buy full price · sell half price", "Specific exceptions remain in the equipment rules tables."],
    ]],
    banking: ["Finance / Storage Snapshot", [
      ["Bank accounts", `${counts.bankAccounts} account(s) · ${counts.robbedAccounts} robbed`, "Robbed accounts create recovery prompts and adventure leads."],
      ["Hidden trove", `${counts.hiddenTroveGold} gp · ${counts.hiddenTroveItems} item stack(s)${counts.hiddenTroveRobbed ? " · stolen" : ""}`, "Trove risk and recovery are handled in Banking and Finance."],
      ["Closeout", `${unresolvedCloseoutTasks(["finance", "storage"]).length} finance/storage task(s)`, "Review banking and storage consequences after adventures."],
    ]],
    settlement: ["Settlement Snapshot", [
      ["Current settlement", `${campaign.settlement_name || "Home Settlement"} · size ${campaign.settlement_size ?? 0}`, "Size modifies availability checks."],
      ["Friendly records", `${worldSettlements().length} settlement(s)`, "Friendly settlements are campaign records and can become troupe homes."],
      ["Travel log", `${(campaign.tag_travel_log || []).length} trip(s)`, "Travel logs keep downtime location history."],
    ]],
    campaign: ["World Snapshot", [
      ["Campaign records", `${worldCounts[0]} campaign(s)`, "Campaigns group guilds, troupes, settlements, parties, and characters."],
      ["World entities", `${worldCounts[1]} guild(s) · ${worldCounts[2]} troupe(s) · ${worldCounts[3]} settlement(s)`, "Current campaign support is app-owned world-builder bookkeeping."],
      ["Troublesome towns", `${worldCounts[4]} placeholder(s)`, "Future supplement hooks only; no unsupported mechanics are claimed."],
    ]],
    settings: ["Options Snapshot", [
      ["Ruleset profiles", `${modernState.rulesProfiles.length} available`, "Profiles affect selectable Go Adventure defaults."],
      ["Map defaults", `${readModernPrefs().defaultMapMode || "unlimited"} mode`, "Map limits are start-session preferences."],
      ["Persistence", "Saved in browser preferences", "Rules data itself is not deleted by changing dashboard options."],
    ]],
    "adventure-management": ["Module Snapshot", [
      ["Installed modules", `${modernState.adventures.length} total`, "Adventure Management owns generated, imported, and AI-authored modules."],
      ["In use", `${moduleInUseCount()} module(s) locked by active sessions`, "Server-side delete blocking protects modules used by active sessions."],
      ["Completed", `${completedAdventureCount()} completed · ${adventureTypeCount("ai")} AI`, "Module badges distinguish AI, Adventures Guild, completed, protected, and in-use states."],
    ]],
    "go-adventure": ["Start Snapshot", [
      ["Active sessions", `${activeSessions.length} in progress`, "Resume active sessions instead of starting duplicates.", namesList(activeSessions, (session) => `${session.save_label || session.id}: ${session.adventure_type || session.adventure_id || "adventure"}`)],
      ["Parties", `${modernState.parties.length} saved`, "Choose a four-character party before starting."],
      ["Closeout warnings", `${openCloseout.length} unresolved task(s)`, "Required guidance can trigger a start override warning.", snapshotTaskDetails(openCloseout, (task) => `${task.title || task.task_action}: ${task.result_text || task.reference || "No detail."}`)],
    ]],
    "rules-reference": ["Reference Snapshot", [
      ["Loaded entries", `${modernState.rulesReference.length || "on demand"}`, "Search exact implementation notes, source refs, and app-owned boundaries."],
      ["Artwork links", `${modernState.artwork.length} registry slot(s)`, "Artwork entries can point back to Rules Reference items."],
      ["Boundary", "Summaries, not full PDF copies", "PDF text remains referenced unless publication rights allow more."],
    ]],
    tables: ["Tables Snapshot", [
      ["Table groups", `${Object.keys(modernState.tables).length || "load on open"}`, "Tables load on demand and are guarded by regression tests."],
      ["Artwork-linked tables", `${modernState.artwork.filter((entry) => (entry.table_keys || []).length).length} art-linked slot(s)`, "Table artwork links are registry-driven."],
      ["Validation", "verified allowlist", "New table keys must be documented and classified."],
    ]],
    library: ["Library Snapshot", [
      ["PDF links", `${PDF_LINKS.length} configured`, "Open owned PDFs from the library."],
      ["Artwork boundary", "local or licensed", "Personal-use crops should stay in DATA_DIR/assets unless publication rights are secured."],
      ["Background notes", "curated summaries", "The app should not bulk-copy full PDF background text."],
    ]],
    guides: ["Guide Snapshot", [
      ["Available now", "TAG guide and checking docs", "Guides collect player workflow and manual test material."],
      ["Planned", "starter and closeout guides", "Guide content can grow without changing rule automation."],
      ["Use case", "before, during, after play", "Good guides reduce log/action confusion during TAG procedures."],
    ]],
    developer: ["Developer Snapshot", [
      ["Artwork slots", `${modernState.artwork.length} registered`, "Artwork Manager shows missing/present DATA_DIR/assets paths."],
      ["Missing art", `${missingArt.length} missing`, "Missing application art means the placeholder has not been replaced yet.", snapshotTaskDetails(missingArt, (entry) => `${entry.title || entry.id}: ${entry.asset_path || entry.path || "No asset path"}${entry.dashboard_pages?.length ? ` (${entry.dashboard_pages.join(", ")})` : ""}`)],
      ["Editors", "map, icon, module scaffolds", "Developer tools are maintenance surfaces, not normal play flow."],
    ]],
  };
  const definition = definitions[page] || definitions.home;
  addRows(definition[0], definition[1]);
  return companion;
}

function renderArtworkImage(entry) {
  const frame = el("div", "modern-art-frame");
  const src = artAssetUrl(entry);
  if (!src) {
    frame.appendChild(el("span", "", "No asset path configured"));
    return frame;
  }
  if (entry.asset_exists === false) {
    frame.classList.add("missing");
    frame.appendChild(el("span", "", "Local artwork file not found"));
    return frame;
  }
  const image = document.createElement("img");
  image.src = src;
  image.alt = entry.title || "Rules artwork";
  image.title = entry.hover || entry.summary || "Rules artwork.";
  image.loading = "lazy";
  image.addEventListener("error", () => {
    frame.classList.add("missing");
    frame.replaceChildren(el("span", "", "Local artwork file not found"));
  }, { once: true });
  frame.appendChild(image);
  return frame;
}

function renderArtworkRows(entries, { compact = false, featureApplication = false } = {}) {
  const wrap = el("div", compact ? "modern-art-grid compact" : "modern-art-grid");
  for (const entry of entries) {
    const row = el("div", "modern-art-card");
    if (featureApplication && !compact && entry.category === "app_assets") row.classList.add("modern-art-card-feature");
    row.title = entry.hover || entry.summary || "Artwork registry entry.";
    row.appendChild(renderArtworkImage(entry));
    const body = el("div", "modern-stack");
    body.appendChild(el("strong", "", entry.title || entry.id));
    body.appendChild(el("span", "muted", `${entry.source_pdf || "App"}${entry.source_page ? ` p.${entry.source_page}` : ""} · ${entry.status || "slot"}`));
    if (!compact && entry.summary) body.appendChild(el("span", "muted", entry.summary));
    row.appendChild(body);
    wrap.appendChild(row);
  }
  return wrap;
}

async function renderPageArtwork(page, title = "Relevant Artwork") {
  await loadArtwork();
  const entries = artworkForPage(page).filter((entry) => entry.category !== "app_assets");
  if (!entries.length) return null;
  const panel = card(title, "Local artwork slots and licensed/private-use PDF crops relevant to this section. Missing files are expected until you populate DATA_DIR/assets, including DATA_DIR/assets/Application Artwork.");
  panel.appendChild(renderArtworkRows(entries, { featureApplication: true }));
  return panel;
}

async function renderShellArtwork(page) {
  await loadArtwork();
  if (pageCompanionEl) {
    pageCompanionEl.replaceChildren(renderPageCompanion(page));
  }
  if (pageArtworkEl) {
    pageArtworkEl.replaceChildren();
    const pageArt = primaryApplicationArtworkForPage(page);
    if (pageArt) pageArtworkEl.appendChild(renderArtworkFigure(pageArt, "modern-page-artwork-figure"));
    if (pageHeadEl) pageHeadEl.classList.toggle("has-artwork", Boolean(pageArt));
  }
  if (navArtworkEl) {
    navArtworkEl.replaceChildren();
    const dashboardArt = primaryApplicationArtworkForPage("home");
    if (dashboardArt) navArtworkEl.appendChild(renderArtworkFigure(dashboardArt, "modern-nav-artwork-figure", "Dashboard"));
  }
}

function renderNeedsAttention() {
  const panel = card("Needs Attention", "Open campaign tasks, unresolved closeout prompts, active sessions, injured/fallen characters, and assignment warnings that should be reviewed before the next adventure.");
  panel.classList.add("modern-card-compact");
  const tasks = openGuidanceTasks();
  const closeouts = closeoutTasksFor([]);
  const activeSessions = (modernState.sessions || []).filter((session) => session.mode !== "complete");
  const injured = (modernState.characters || []).filter((character) => character.current_life > 0 && character.current_life < character.max_life);
  const fallen = (modernState.characters || []).filter((character) => character.current_life <= 0);
  const contextWarnings = (modernState.characters || []).filter((character) => characterContextWarnings(character).length);
  panel.append(
    modernStatusRow("Open guidance", `${tasks.length} task(s)`, "Structured required/recommended/optional guidance tasks. Use the bottom Guidance / Log panel to complete, defer, or dismiss them."),
    modernStatusRow("Closeout", `${closeouts.length} unresolved prompt(s)`, "Adventure closeout prompts from supported TAG/Guild/storage/finance/XP workflows."),
    modernStatusRow("Active sessions", `${activeSessions.length} session(s)`, "Resume, save, complete, or delete active sessions before reusing locked characters."),
    modernStatusRow("Roster health", `${injured.length} injured · ${fallen.length} fallen`, "Heal or resolve fallen characters before starting a normal adventure."),
    modernStatusRow("Context warnings", `${contextWarnings.length} character(s)`, "Campaign/Guild/Troupe/Party mismatches to clean up in Character, Party, or Troupe Management.")
  );
  const row = actions();
  row.append(
    link("Go Adventure", "/modern/go-adventure", "Open Go Adventure setup readiness.", "link-button secondary"),
    link("Guild", "/modern/guild", "Open Guild closeout and finance tasks.", "link-button secondary"),
    link("Banking", "/modern/banking", "Open banking, storage, and recovery tasks.", "link-button secondary"),
    link("Rules", ruleReferenceHref("adventure_closeout_workflow", "adventure closeout workflow"), "Open the Adventure Closeout workflow reference.", "link-button secondary")
  );
  panel.appendChild(row);
  return panel;
}

function renderDashboardStatusIcons() {
  const activeSessions = (modernState.sessions || []).filter((session) => session.mode !== "complete");
  const injured = modernState.characters.filter((character) => character.current_life > 0 && character.current_life < character.max_life);
  const fallen = modernState.characters.filter((character) => character.current_life <= 0);
  const closeouts = closeoutTasksFor([]);
  const guidance = openGuidanceTasks();
  const modulesInUse = moduleInUseCount();
  const items = [
    ["▶", "Active", `${activeSessions.length} session(s)`, "/modern/go-adventure", "Resume active games or finish closeout before reusing locked characters."],
    ["!", "Attention", `${guidance.length + closeouts.length} task(s)`, "#dashboard-needs-attention", "Open guidance and closeout tasks that should be reviewed before the next adventure."],
    ["♥", "Roster", `${injured.length} injured · ${fallen.length} fallen`, "/modern/characters", "Review character health, equipment, and assignment warnings."],
    ["◆", "Modules", `${modernState.adventures.length} installed · ${modulesInUse} in use`, "/modern/adventure-management", "Manage generated, imported, and AI adventure modules."],
  ];
  const panel = el("section", "modern-dashboard-status-icons");
  panel.setAttribute("aria-label", "Dashboard status");
  for (const [icon, label, value, href, tooltip] of items) {
    const item = document.createElement("a");
    item.href = href;
    item.className = "modern-dashboard-status-icon";
    item.title = tooltip;
    item.append(el("span", "modern-dashboard-status-symbol", icon), el("strong", "", label), el("span", "muted", value));
    panel.appendChild(item);
  }
  return panel;
}

async function renderHome() {
  await loadArtwork();
  rootEl.appendChild(renderDashboardStatusIcons());
  const grid = el("div", "modern-home-grid");
  for (const [page, meta] of Object.entries(PAGE_META)) {
    if (page === "home") continue;
    const section = card(meta[0], meta[1]);
    const art = primaryApplicationArtworkForPage(page);
    if (art) {
      const artLink = document.createElement("a");
      artLink.href = `/modern/${page}`;
      artLink.className = "modern-home-tile-artwork-link";
      artLink.title = `Open ${meta[0]}.`;
      artLink.appendChild(renderArtworkFigure(art, "modern-home-tile-artwork"));
      section.prepend(artLink);
    }
    const row = actions();
    row.appendChild(link("Open", `/modern/${page}`, `Open ${meta[0]}.`, "link-button"));
    section.appendChild(row);
    grid.appendChild(section);
  }
  rootEl.appendChild(grid);
  const needs = collapseCard(renderNeedsAttention(), "Dashboard safety checks, open guidance, active sessions, closeout prompts, and roster warnings.");
  needs.id = "dashboard-needs-attention";
  rootEl.appendChild(needs);
  rootEl.appendChild(collapseCard(renderAdventureCloseoutCockpit("Dashboard"), "Generated lead, route marker, XP, Guild, banking/storage, and guidance review before the next adventure."));
}

function renderCharacters() {
  rootEl.appendChild(renderWorldContextPanel("Character World Context"));
  rootEl.appendChild(renderGuide("Character Sheet Workflow", [
    "Use readiness filters to find injured, locked, under-equipped, or context-mismatched characters before starting play.",
    "Weapon slots are saved on the roster; armor and shield are currently detected from inventory and shown for review.",
    "Campaign, Guild, Troupe, Party, and Home settlement should line up before Go Adventure setup."
  ], "character_management_deep_polish", "character sheet equipment slots campaign context"));
  const layout = el("div", "modern-two-col");
  const list = card("Roster", "Search, sort, filter, heal, spend XP, review full sheets, or delete roster characters.");
  const filters = characterManagementFilterControls("modern-roster", drawRoster);
  const summary = el("div", "modern-list");
  const rows = el("div", "modern-list modern-list-tall");
  list.append(filters.panel, summary, rows);
  function drawRoster() {
    summary.replaceChildren();
    rows.replaceChildren();
    const filtered = filteredCharacters({
      search: filters.search.value,
      classId: filters.classFilter.value,
      campaignId: filters.campaignFilter.value,
      guildId: filters.guildFilter.value,
      troupeId: filters.troupeFilter.value,
      partyId: filters.partyFilter.value,
      readiness: filters.readiness.value,
      sort: filters.sort.value,
    });
    const injured = filtered.filter((character) => character.current_life < character.max_life && character.current_life > 0).length;
    const fallen = filtered.filter((character) => character.current_life <= 0).length;
    const equipmentGaps = filtered.filter((character) => characterEquipmentWarnings(character).length).length;
    const contextWarnings = filtered.filter((character) => characterContextWarnings(character).length).length;
    summary.appendChild(modernStatusRow("Visible roster", `${filtered.length} character(s) · ${injured} injured · ${fallen} fallen · ${equipmentGaps} equipment warning(s) · ${contextWarnings} context warning(s)`, "Summary of the currently filtered roster. Use Readiness to narrow specific cleanup work."));
    for (const character of filtered) {
      const row = el("div", "modern-row");
      const parties = partyNamesForCharacter(character.id);
      const troupe = (modernState.campaign?.tag_troupe_member_character_ids || []).includes(character.id) ? "TAG troupe" : "not in TAG troupe";
      const readiness = characterReadinessRows(character);
      const blocking = readiness.filter(([, , status]) => status === "block").length;
      const warnings = readiness.filter(([, , status]) => status === "warn").length;
      row.appendChild(el("strong", "", `${character.name} - ${character.class_name} L${character.level}`));
      row.appendChild(el("span", "muted", `HP ${character.current_life}/${character.max_life} · XP ${character.xp || 0} · carried ${character.gold || 0}gp · TAG bank ${tagBankForCharacter(character.id)}gp · ${character.clues || 0} Clues`));
      row.appendChild(el("span", "muted", `Party: ${parties.join(", ") || "none"} · ${troupe}`));
      row.appendChild(el("span", "muted", characterWorldSummary(character)));
      row.appendChild(el("span", "muted", characterEquipmentSummary(character)));
      if (blocking || warnings) {
        const warning = el("span", "muted", `${blocking} blocking issue(s) · ${warnings} warning(s). Open Full sheet for details.`);
        warning.title = "Blocking issues stop normal adventure start; warnings are cleanup items to review before play.";
        row.appendChild(warning);
      }
      const worldLinks = actions();
      worldLinks.append(
        link("Campaign", "/modern/campaign", "Open Campaign Management for this character's campaign, guild, troupe, party, and home-settlement context.", "link-button secondary"),
        link("Guild", "/modern/guild", "Open Guild Management for membership, coffers, jobs, and Guild closeout prompts.", "link-button secondary"),
        link("Troupe", "/modern/troupes", "Open Troupe Management for membership, active adventurers, assigned parties, and travel base.", "link-button secondary"),
        link("Party", "/modern/parties", "Open Party Membership to change this character's saved party assignment.", "link-button secondary")
      );
      row.appendChild(worldLinks);
      row.appendChild(renderCharacterInventoryDetails(character));
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
    if (!rows.childElementCount) rows.appendChild(el("p", "muted", "No roster characters match the current filters."));
  }
  drawRoster();
  layout.appendChild(list);

  const create = card("Create / Add Character", "Choose a class, enter a name, and create a roster hero.");
  const name = input("text", "modern-character-name", "Name for the new character.");
  const classSelect = select("modern-character-class", "Class for the new character.", modernState.classes.map((item) => [item.id, item.name]));
  const classDossierMount = el("div", "modern-class-dossier-mount");
  function drawClassDossier() {
    classDossierMount.replaceChildren(renderClassDossier(classProfileById(classSelect.value)));
  }
  classSelect.addEventListener("change", drawClassDossier);
  create.append(field("Name", name), field("Class", classSelect), classDossierMount);
  drawClassDossier();
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

function worldCampaigns() {
  return modernState.campaign?.world_campaigns || [];
}

function worldGuilds() {
  return modernState.campaign?.world_guilds || [];
}

function worldTroupes() {
  return modernState.campaign?.world_troupes || [];
}

function worldSettlements(kind = "friendly") {
  return kind === "troublesome" ? modernState.campaign?.world_troublesome_towns || [] : modernState.campaign?.world_settlements || [];
}

function worldName(rows, id, fallback = "Unassigned") {
  return rows.find((item) => item.id === id)?.name || fallback;
}

function worldCampaignOptions(blank = "Choose campaign") {
  return [["", blank], ...worldCampaigns().map((item) => [item.id, item.name])];
}

function worldTroupeOptions(blank = "Choose troupe") {
  return [["", blank], ...worldTroupes().map((item) => [item.id, item.name])];
}

function worldGuildOptions(blank = "Choose guild") {
  return [["", blank], ...worldGuilds().map((item) => [item.id, item.name])];
}

function worldSettlementOptions(blank = "Choose settlement") {
  return [["", blank], ...worldSettlements().map((item) => [item.id, item.name])];
}

function characterWorldSummary(character) {
  const troupe = worldTroupes().find((item) => item.id === character.troupe_id);
  const homeSettlement = troupe?.home_settlement_id ? worldName(worldSettlements(), troupe.home_settlement_id) : "Unassigned";
  return `Campaign ${worldName(worldCampaigns(), character.campaign_id)} · Guild ${worldName(worldGuilds(), character.guild_id)} · Troupe ${worldName(worldTroupes(), character.troupe_id)} · Party ${worldName(modernState.parties, character.party_id, "none")} · Home ${homeSettlement}`;
}

function selectedWorldCampaign() {
  return worldCampaigns().find((item) => item.id === modernState.campaign?.active_world_campaign_id) || worldCampaigns()[0] || null;
}

function worldRecordSearchText(row, extra = "") {
  return `${row.name || ""} ${row.description || ""} ${row.notes || ""} ${worldName(worldCampaigns(), row.campaign_id, "")} ${extra}`.toLowerCase();
}

function filteredWorldRows(rows, filters, extraText = () => "") {
  const search = (filters.search.value || "").trim().toLowerCase();
  const campaignId = filters.campaign.value || "";
  const sorted = rows
    .filter((row) => (!campaignId || row.id === campaignId || row.campaign_id === campaignId))
    .filter((row) => !search || worldRecordSearchText(row, extraText(row)).includes(search));
  sorted.sort((a, b) => {
    if (filters.sort.value === "campaign") return worldName(worldCampaigns(), a.campaign_id, "").localeCompare(worldName(worldCampaigns(), b.campaign_id, ""));
    if (filters.sort.value === "created") return String(b.created_at || "").localeCompare(String(a.created_at || ""));
    return String(a.name || "").localeCompare(String(b.name || ""));
  });
  return sorted;
}

function worldFilterControls(prefix, onChange) {
  const panel = card("World List Filters", "Search, sort, and narrow campaign-management lists. These filters only affect what is shown on this page.");
  panel.classList.add("modern-card-compact");
  const search = input("search", `${prefix}-search`, "Search campaign, guild, troupe, settlement, troublesome town, description, notes, and assigned campaign names.");
  const campaign = select(`${prefix}-campaign-filter`, "Show records assigned to this campaign, or show all world-builder records.", [["", "All campaigns"], ...worldCampaigns().map((item) => [item.id, item.name])]);
  const sort = select(`${prefix}-sort`, "Sort campaign-management lists by name, assigned campaign, or newest created record.", [["name", "Name"], ["campaign", "Campaign"], ["created", "Newest"]]);
  search.addEventListener("input", onChange);
  campaign.addEventListener("change", onChange);
  sort.addEventListener("change", onChange);
  panel.append(field("Search", search), field("Campaign filter", campaign), field("Sort", sort));
  return { panel, search, campaign, sort };
}

function worldCampaignCounts(campaignId) {
  return {
    guilds: worldGuilds().filter((item) => item.campaign_id === campaignId).length,
    troupes: worldTroupes().filter((item) => item.campaign_id === campaignId).length,
    settlements: worldSettlements().filter((item) => item.campaign_id === campaignId).length,
    troublesome: worldSettlements("troublesome").filter((item) => item.campaign_id === campaignId).length,
  };
}

function worldTroupeForCharacter(character) {
  return worldTroupes().find((item) => item.id === character?.troupe_id);
}

function renderWorldContextPanel(title = "World Context") {
  const selected = selectedWorldCampaign();
  const counts = selected ? worldCampaignCounts(selected.id) : { guilds: 0, troupes: 0, settlements: 0, troublesome: 0 };
  const defaultGuild = worldGuilds().find((item) => item.id === "adventurers-guild") || worldGuilds()[0];
  const defaultTroupe = worldTroupes().find((item) => item.id === "troupe1") || worldTroupes()[0];
  const defaultSettlement = worldSettlements().find((item) => item.id === "brightwater-gate") || worldSettlements()[0];
  const panel = card(title, "Current campaign/world assignments used by this management page. Open Campaign Management for full editing.");
  panel.classList.add("modern-card-compact");
  panel.append(
    modernStatusRow(
      selected?.name || "No campaign selected",
      selected ? `${counts.guilds} guild(s) · ${counts.troupes} troupe(s) · ${counts.settlements} friendly settlement(s) · ${counts.troublesome} troublesome town(s)` : "Create a campaign from Campaign Management.",
      "Selected campaign defaults new world-builder records and shows where this page writes campaign context."
    ),
    modernStatusRow(
      "Default links",
      `Guild ${defaultGuild?.name || "none"} · Troupe ${defaultTroupe?.name || "none"} · Home ${defaultSettlement?.name || "none"}`,
      "Protected default records seeded by the app. Norindaal, Adventurers Guild, Troupe1, and Hearthmere keep stable default names while their notes and assignments can be edited."
    )
  );
  const row = actions();
  row.append(
    link("Campaign", "/modern/campaign", "Open Campaign Management to edit campaigns, guilds, troupes, settlements, and troublesome-town placeholders.", "link-button secondary"),
    link("Rules", ruleReferenceHref("modern_dashboard_management_polish", "dashboard management polish"), "Open the Rules Reference entry for this dashboard management polish pass.", "link-button secondary"),
    link("Tables", "/modern/tables?help=modern_dashboard_management_table", "Open Tables filtered toward the dashboard management workflow table.", "link-button secondary")
  );
  panel.appendChild(row);
  return panel;
}

function partySearchText(party) {
  const members = (party.character_ids || []).map((id) => modernState.characters.find((character) => character.id === id)).filter(Boolean);
  return [
    party.name,
    worldName(worldCampaigns(), party.campaign_id, ""),
    worldName(worldTroupes(), party.troupe_id, ""),
    ...members.map((member) => `${member.name} ${member.class_name} ${member.level}`),
  ].join(" ").toLowerCase();
}

function filteredParties({ search = "", troupeId = "", sort = "name" } = {}) {
  const needle = String(search || "").toLowerCase();
  const rows = modernState.parties.filter((party) => {
    if (troupeId && party.troupe_id !== troupeId) return false;
    return !needle || partySearchText(party).includes(needle);
  });
  rows.sort((left, right) => {
    if (sort === "troupe") return worldName(worldTroupes(), left.troupe_id, "").localeCompare(worldName(worldTroupes(), right.troupe_id, "")) || left.name.localeCompare(right.name);
    if (sort === "members") return (right.character_ids || []).length - (left.character_ids || []).length || left.name.localeCompare(right.name);
    return left.name.localeCompare(right.name);
  });
  return rows;
}

function partyFilterControls(prefix, onChange) {
  const panel = el("div", "modern-filterbar");
  const search = input("search", `${prefix}-party-search`, "Search saved parties by party name, member name, member class, campaign, or troupe.");
  const troupeFilter = select(`${prefix}-party-troupe-filter`, "Filter saved parties by assigned troupe.", [["", "All troupes"], ...worldTroupes().map((item) => [item.id, item.name])]);
  const sort = select(`${prefix}-party-sort`, "Sort saved parties by name, troupe, or member count.", [["name", "Name"], ["troupe", "Troupe"], ["members", "Members"]]);
  search.addEventListener("input", onChange);
  troupeFilter.addEventListener("change", onChange);
  sort.addEventListener("change", onChange);
  panel.append(field("Search", search), field("Troupe", troupeFilter), field("Sort", sort));
  return { panel, search, troupeFilter, sort };
}

async function worldAction(payload) {
  const result = await api("/api/campaign/world", { method: "POST", body: JSON.stringify(payload) });
  modernState.campaign = result.campaign;
  setStatus(result.messages?.length ? result.messages.join(" ") : "Campaign world updated.");
  await refreshCoreAndRender();
  return result;
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
  rootEl.appendChild(renderWorldContextPanel("Troupe World Context"));
  rootEl.appendChild(renderGuide("Troupe Workflow", [
    "Pick the campaign first, then keep roster membership and active adventurers in sync.",
    "A character can belong to one troupe; assigning across troupes may remove incompatible party membership.",
    "Use the settlement/travel section after membership is saved so logs and home settlement match the troupe.",
    "Before a TAG adventure, check that the active troupe has four intended adventurers and that their saved party context matches."
  ], "campaign_membership_boundaries", "troupe membership party campaign"));
  const panel = card("Create / Select Troupe", "Select the current troupe, add or remove roster members, choose up to four active adventurers, and manage the home settlement and travel below.");
  const name = input("text", "modern-troupe-name", "Name shown for this TAG troupe in dashboard summaries, closeout prompts, and travel logs.", campaign.tag_troupe_name || "Adventuring Troupe");
  const campaignAssign = select("modern-troupe-campaign", "Campaign/world this troupe belongs to. Each troupe may belong to only one campaign.", worldCampaignOptions());
  campaignAssign.value = worldTroupes().find((item) => item.id === "troupe1")?.campaign_id || campaign.active_world_campaign_id || "norindaal";
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
  panel.appendChild(
    modernStatusRow(
      campaign.tag_troupe_name || "Adventuring Troupe",
      `${troupeMemberIds().length} member(s) · ${(campaign.tag_troupe_active_character_ids || []).length} active · home ${campaign.settlement_name || "Home Settlement"}`,
      "Current TAG troupe summary. Save changes here before using the troupe for travel or adventure setup."
    )
  );
  panel.append(field("Troupe name", name), field("Campaign", campaignAssign), addFilters.panel, field("Add member", add), field("Remove member", remove), field("Active members", active));
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
    button("Create / Save Troupe", "Create or update the current TAG troupe name and active member selection.", () => save(), ""),
    button("Add Member", "Add selected roster character to this troupe.", () => {
      const selected = modernState.characters.find((item) => item.id === add.value);
      const existingParty = selected?.party_id ? modernState.parties.find((item) => item.id === selected.party_id) : null;
      if (existingParty && existingParty.troupe_id && existingParty.troupe_id !== "troupe1" && !window.confirm(`${selected.name} belongs to ${existingParty.name}. Assigning them to Troupe1 will remove them from that party. Continue?`)) return Promise.resolve();
      return worldAction({ action: "assign_character_troupe", character_id: add.value, troupe_id: "troupe1" }).then(() => {
        const ids = Array.from(new Set([...troupeMemberIds(), add.value].filter(Boolean)));
        return save(ids);
      });
    }),
    button("Assign Campaign", "Assign Troupe1 to the selected campaign. A troupe can be assigned to only one campaign at a time.", () => worldAction({ action: "assign", entity: "troupe", troupe_id: "troupe1", campaign_id: campaignAssign.value })),
    button("Remove Member", "Remove selected member from this troupe.", () => {
      const ids = troupeMemberIds().filter((id) => id !== remove.value);
      return save(ids);
    }),
    button("Delete Troupe", "Clear troupe members, active party selection, and reset the troupe name.", () => save([]))
  );
  panel.appendChild(row);
  let selectedTroupeMemberId = troupeMemberIds()[0] || "";
  const memberFilters = characterFilterControls("modern-troupe-members", drawTroupeMembers);
  const memberRows = el("div", "modern-list");
  const memberSheet = el("div", "modern-row troupe-member-sheet");
  const memberBrowser = el("div", "modern-two-col troupe-member-browser");
  const memberListPane = el("div", "modern-stack");
  memberListPane.append(el("strong", "", "Members"), memberFilters.panel, memberRows);
  memberBrowser.append(memberListPane, memberSheet);
  panel.appendChild(memberBrowser);
  function drawTroupeMembers() {
    memberRows.replaceChildren();
    memberSheet.replaceChildren();
    const ids = new Set(troupeMemberIds());
    const rows = filteredCharacters({ search: memberFilters.search.value, classId: memberFilters.classFilter.value, sort: memberFilters.sort.value }).filter((item) => ids.has(item.id));
    if (!rows.some((character) => character.id === selectedTroupeMemberId)) selectedTroupeMemberId = rows[0]?.id || "";
    for (const character of rows) {
      const activeText = (campaign.tag_troupe_active_character_ids || []).includes(character.id) ? "active party" : "home/available";
      const worldTroupe = worldTroupeForCharacter(character);
      const memberRow = document.createElement("button");
      memberRow.type = "button";
      memberRow.className = `modern-row troupe-member-select${character.id === selectedTroupeMemberId ? " selected" : ""}`;
      memberRow.append(
        el("strong", "", character.name),
        el("span", "muted", `${character.class_name} L${character.level} · ${activeText} · carried ${character.gold || 0}gp · TAG bank ${tagBankForCharacter(character.id)}gp · parties: ${partyNamesForCharacter(character.id).join(", ") || "none"}`),
        el("span", "muted", `Campaign ${worldName(worldCampaigns(), character.campaign_id)} · Guild ${worldName(worldGuilds(), character.guild_id)} · Troupe ${worldName(worldTroupes(), character.troupe_id)} · Home ${worldTroupe?.home_settlement_id ? worldName(worldSettlements(), worldTroupe.home_settlement_id) : "Unassigned"}`)
      );
      memberRow.title = "Troupe member status. Assigning a character to another troupe can remove incompatible party membership; the backend enforces one troupe per character.";
      memberRow.addEventListener("click", () => {
        selectedTroupeMemberId = character.id;
        drawTroupeMembers();
      });
      memberRows.appendChild(memberRow);
    }
    const selected = modernState.characters.find((character) => character.id === selectedTroupeMemberId);
    if (selected) {
      memberSheet.append(
        el("strong", "", `${selected.name} sheet`),
        el("span", "muted", "Selected troupe member. Review equipment, inventory, spells, statuses, and world context before choosing active adventurers.")
      );
      const sheet = renderCharacterInventoryDetails(selected);
      sheet.open = true;
      memberSheet.appendChild(sheet);
    } else {
      memberSheet.appendChild(el("p", "muted", "Select a troupe member to show their character sheet here."));
    }
    if (!memberRows.childElementCount) {
      memberRows.appendChild(el("p", "muted", "No troupe members match the current filters. Add roster characters above, then choose up to four active members."));
    }
  }
  drawTroupeMembers();

  const troupeParties = card("Assigned Parties", "Saved parties assigned to Troupe1. A party belongs to one troupe, and its characters must belong to the same troupe.");
  const partyFilters = partyFilterControls("modern-troupe-parties", drawTroupeParties);
  const partyRows = el("div", "modern-list");
  troupeParties.append(partyFilters.panel, partyRows);
  function drawTroupeParties() {
    partyRows.replaceChildren();
    const rows = filteredParties({ search: partyFilters.search.value, troupeId: partyFilters.troupeFilter.value || "troupe1", sort: partyFilters.sort.value });
    for (const party of rows) {
      const memberNames = (party.character_ids || []).map((id) => modernState.characters.find((item) => item.id === id)?.name || id).join(", ") || "empty";
      partyRows.appendChild(modernStatusRow(party.name, `${(party.character_ids || []).length} member(s) · campaign ${worldName(worldCampaigns(), party.campaign_id)} · ${memberNames}`, "Party assigned to this troupe. Use Party Management to move a party to another troupe."));
    }
    if (!partyRows.childElementCount) partyRows.appendChild(el("p", "muted", "No saved parties assigned to Troupe1 match the current filters."));
  }
  drawTroupeParties();

  const travel = card("Settlement Details and Travel", "The settlement is the troupe's downtime base. Size modifies availability checks; travel changes which settlement the troupe is focused on.");
  const settlement = input("text", "modern-settlement-name", "Current home settlement name used by TAG travel, services, availability checks, and downtime logs.", campaign.settlement_name || "Home Settlement");
  const size = select("modern-settlement-size", "Settlement size modifier: added to TAG availability checks and used to describe how easy services/items are to find.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
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
  rootEl.append(panel, troupeParties, travel, renderTagSignoffPanel("Troupe Adventure Signoff"));
}

function renderGuild() {
  const campaign = modernState.campaign || {};
  rootEl.appendChild(renderWorldContextPanel("Guild World Context"));
  rootEl.appendChild(renderGuide("Guild Workflow", [
    "Guild benefits need active membership and coffers above 0 gp.",
    "Adventure closeout creates Guild prompts for loot share, upkeep, reroll reset, and leaving-restriction signoff.",
    "Create Guild Job leads here, then start the installed module from Go Adventure.",
    "Use the closeout card after every Guild-linked adventure so coffers, rerolls, and leaving restrictions do not drift."
  ], "tag_guild_closeout_guidance", "guild closeout upkeep job"));
  const panel = card("Create / Select Guild", "Select the current Adventurers Guild state for the troupe, then manage members, coffers, Guild jobs, benefits, and closeout obligations below.");
  const active = input("checkbox", "modern-guild-active", "Enables Adventurers Guild rules for the current TAG troupe. Benefits need membership plus coffers above 0 gp.");
  active.checked = Boolean(campaign.tag_guild_member);
  const guildCampaign = select("modern-guild-campaign", "Campaign/world this guild belongs to. Each campaign may have one assigned guild.", worldCampaignOptions());
  guildCampaign.value = worldGuilds().find((item) => item.id === "adventurers-guild")?.campaign_id || campaign.active_world_campaign_id || "norindaal";
  const coffers = input("number", "modern-guild-coffers-page", "Shared Guild coffers in gp. These fund Guild benefits, upkeep, resurrection funding, and loot-share obligations.", String(campaign.tag_guild_coffers_gp || 0));
  const actionCharacter = select("modern-guild-character", "Guild member receiving resurrection funding or other character-specific Guild handling.", characterOptions("Choose character"));
  const amount = input("number", "modern-guild-amount", "Gold amount for Guild loot share, resurrection funding, or notes.", "0");
  const itemName = input("text", "modern-guild-availability-item", "Item name for the once-per-adventure Guild availability reroll.");
  panel.append(field("Guild active", active), field("Campaign", guildCampaign), field("Guild coffers gp", coffers));
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
    }, ""),
    button("Assign Campaign", "Assign the Adventurers Guild to the selected campaign. Each campaign may have only one guild.", () => worldAction({ action: "assign", entity: "guild", guild_id: "adventurers-guild", campaign_id: guildCampaign.value }))
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

  const members = card("Guild Jobs and Members", "Troupe members are treated as Guild members while Guild membership is active. Search and sort this list to check member state before using Guild finance or jobs.");
  const guildMemberFilters = characterFilterControls("modern-guild-members", drawGuildMembers);
  members.append(guildMemberFilters.panel, field("Character", actionCharacter));
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
  function drawGuildMembers() {
    memberList.replaceChildren();
    const rows = filteredCharacters({ search: guildMemberFilters.search.value, classId: guildMemberFilters.classFilter.value, sort: guildMemberFilters.sort.value }).filter((item) => memberIds.has(item.id));
    for (const character of rows) {
      const account = tagBankAccountForCharacter(character.id);
      const worldTroupe = worldTroupeForCharacter(character);
      memberList.appendChild(
        modernStatusRow(
          character.name,
          `${character.class_name} L${character.level} · ${activeIds.has(character.id) ? "active party" : "home"} · ${character.gold || 0} gp carried · TAG bank ${account?.gold_gp || 0} gp${account?.robbed ? " · bank robbed" : ""} · ${worldTroupe?.name || "no world troupe"}`,
          "Guild member summary from the TAG troupe roster and TAG bank ledger. Use this before resurrection funding, Guild jobs, or availability rerolls."
        )
      );
    }
    if (!memberList.childElementCount) memberList.appendChild(el("p", "muted", "No Guild members match the current filters. Add members from Troupe Management before treating them as Guild members."));
  }
  drawGuildMembers();
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
  rootEl.append(panel, finance, members, renderCloseoutTasks("Guild Closeout", ["guild", "xp"]), renderTagSignoffPanel("Guild Adventure Signoff"), benefits, recent);
}

function renderParties() {
  rootEl.appendChild(renderWorldContextPanel("Party World Context"));
  rootEl.appendChild(renderGuide("Party Workflow", [
    "Create parties from four different roster characters.",
    "A party belongs to one troupe; all party characters should belong to that same troupe.",
    "Use Assign Troupe when moving an existing party into a campaign troupe."
  ], "campaign_membership_boundaries", "party troupe membership"));
  const create = card("Create Party", "Choose exactly four different roster heroes and assign the saved party to one troupe.");
  const name = input("text", "modern-party-name", "Name of this saved party.");
  const partyTroupe = select("modern-party-troupe", "Troupe this party belongs to. Characters can belong to only one party and one troupe.", worldTroupeOptions());
  partyTroupe.value = "troupe1";
  create.append(field("Party name", name), field("Troupe", partyTroupe));
  const picks = [];
  for (let i = 0; i < 4; i += 1) {
    const pick = characterSelect(`modern-party-member-${i}`, `Party slot ${i + 1}.`, `Slot ${i + 1}`);
    picks.push(pick);
    create.appendChild(field(`Slot ${i + 1}`, pick));
  }
  create.appendChild(button("Save Party", "Create a four-character party.", async () => {
    await api("/api/parties", { method: "POST", body: JSON.stringify({ name: name.value, character_ids: picks.map((item) => item.value), troupe_id: partyTroupe.value }) });
    setStatus("Party saved.");
    await refreshCoreAndRender();
  }, ""));
  const list = card("Saved Parties", "Review, filter, assign, heal, bank, or delete saved parties. Text is left aligned so party composition is easy to scan.");
  const partyFilters = partyFilterControls("modern-saved-parties", drawPartyRows);
  const listActions = actions();
  listActions.append(
    button("Expand All", "Expand all saved party details.", async () => {
      list.querySelectorAll("details").forEach((item) => { item.open = true; });
    }),
    button("Collapse All", "Collapse all saved party details.", async () => {
      list.querySelectorAll("details").forEach((item) => { item.open = false; });
    })
  );
  const partyRows = el("div", "modern-list");
  list.append(partyFilters.panel, listActions, partyRows);
  function drawPartyRows() {
    partyRows.replaceChildren();
    const rows = filteredParties({ search: partyFilters.search.value, troupeId: partyFilters.troupeFilter.value, sort: partyFilters.sort.value });
    for (const party of rows) {
      const row = document.createElement("details");
      row.className = "modern-row";
      row.classList.add("party-list-row");
      const summary = document.createElement("summary");
      const members = (party.character_ids || []).map((id) => modernState.characters.find((c) => c.id === id)).filter(Boolean);
      const assignedTroupe = worldTroupes().find((item) => item.id === party.troupe_id);
      const mismatched = members.filter((member) => member.troupe_id && party.troupe_id && member.troupe_id !== party.troupe_id);
      summary.textContent = `${party.name} - ${members.map((member) => member.name).join(", ") || "empty"}`;
      summary.title = "Expand this saved party to review campaign, troupe, member, bank, and assignment details.";
      row.appendChild(summary);
      const detail = el("div", "modern-stack");
      detail.appendChild(el("span", "muted", `Campaign ${worldName(worldCampaigns(), party.campaign_id)} · Troupe ${assignedTroupe?.name || "Unassigned"} · Home ${assignedTroupe?.home_settlement_id ? worldName(worldSettlements(), assignedTroupe.home_settlement_id) : "Unassigned"}`));
      if (mismatched.length) {
        detail.appendChild(el("span", "muted", `Assignment warning: ${mismatched.map((member) => member.name).join(", ")} currently point to a different troupe. Assign Troupe will resync party characters to the selected troupe.`));
      }
      for (const member of members) {
        detail.appendChild(el("span", "muted", `${member.name}: ${member.class_name} L${member.level}, HP ${member.current_life}/${member.max_life}, XP ${member.xp || 0}, carried ${member.gold || 0}gp, TAG bank ${tagBankForCharacter(member.id)}gp, ${member.clues || 0} Clues · ${characterWorldSummary(member)}`));
      }
      const moveTroupe = select(`modern-party-${party.id}-troupe`, "Move this saved party to another troupe. The party can belong to only one troupe; assigned characters are synced to that troupe.", worldTroupeOptions());
      moveTroupe.value = party.troupe_id || "troupe1";
      detail.appendChild(field("Assigned troupe", moveTroupe));
      row.appendChild(detail);
      const rowActions = actions();
      rowActions.append(
        button("Assign Troupe", "Assign this party to the selected troupe and update party characters to the troupe's campaign/guild context.", () => worldAction({ action: "assign_party_troupe", party_id: party.id, troupe_id: moveTroupe.value })),
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
        button("Delete", "Delete this saved party. Characters remain in the roster and keep their campaign/troupe fields until reassigned.", async () => {
          if (!window.confirm(`Delete ${party.name}? Characters stay in the roster.`)) return;
          await api(`/api/parties/${party.id}`, { method: "DELETE" });
          setStatus("Party deleted.");
          await refreshCoreAndRender();
        })
      );
      row.appendChild(rowActions);
      partyRows.appendChild(row);
    }
    if (!partyRows.childElementCount) partyRows.appendChild(el("p", "muted", "No saved parties match the current filters."));
  }
  drawPartyRows();
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
  rootEl.appendChild(renderGuide("Finance Workflow", [
    "Choose a character first so carried gold, TAG bank, party, and troupe context are visible.",
    "Use party/troupe bulk banking for setup migration; use character actions for normal play logs.",
    "Robbed bank accounts and stolen troves create recovery prompts in Guidance and closeout panels.",
    "After every adventure, review hidden trove risk, robbed bank accounts, inheritance notes, and Guild ledger consequences before starting again."
  ], "tag_settlement_campaign", "banking finance trove robbery"));
  const panel = card("TAG Banking and Finance", "Banking moves gold between carried roster gold and TAG bank accounts. Troves store hidden gold/items; robbery and inheritance actions create explicit log entries.");
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
  rootEl.append(panel, ledger, trove, renderCloseoutTasks("Finance Closeout", ["finance", "storage"]), renderTagSignoffPanel("Finance / Storage Signoff"), recent);
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
  rootEl.appendChild(renderWorldContextPanel("Settlement World Context"));
  rootEl.appendChild(renderGuide("Settlement Workflow", [
    "Friendly settlements are campaign world records; TAG settlement fields drive services, availability, travel, and logs.",
    "Size modifies availability checks and should be saved before rolling item or service availability.",
    "Troublesome towns are campaign placeholders for later supplement support, not active TAG settlement mechanics yet.",
    "Availability hover text explains whether a value changes service/item discovery, travel context, or tracked settlement history."
  ], "friendly_settlements", "settlement services availability"));
  const campaign = modernState.campaign || {};
  const panel = card("Create / Select Settlement", "TAG settlements are downtime hubs. Select or create one, maintain notes, check services/items, and travel between known settlements.");
  const name = input("text", "modern-settlement-name-page", "TAG settlement name used in travel logs, troupe home summaries, and service/availability checks.", campaign.settlement_name || "Home Settlement");
  const settlementCampaign = select("modern-settlement-campaign", "Campaign/world this friendly settlement belongs to. Each settlement may belong to only one campaign.", worldCampaignOptions());
  settlementCampaign.value = worldSettlements().find((item) => item.id === "brightwater-gate")?.campaign_id || campaign.active_world_campaign_id || "norindaal";
  const size = select("modern-settlement-size-page", "Settlement size modifier: added to TAG availability checks against the selected difficulty. Larger settlements make items and services easier to find.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
  size.value = String(campaign.settlement_size ?? 0);
  const notes = textarea("modern-settlement-notes", "Settlement notes for services, story hooks, local restrictions, and travel context.", 4);
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
  panel.append(field("Settlement", name), field("Campaign", settlementCampaign), field("Size", size), field("Notes", notes), availabilityPicker.wrap);
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
    button("Assign Campaign", "Assign Hearthmere, the protected default friendly settlement, to the selected campaign.", () => worldAction({ action: "assign", entity: "settlement", settlement_id: "brightwater-gate", campaign_id: settlementCampaign.value })),
    button("Roll Size", "Roll a random TAG settlement size and apply its modifier to availability checks.", async () => {
      const result = await api("/api/campaign/settlement/roll-size", { method: "POST" });
      setStatus(`Settlement size rolled ${result.roll}.`);
      await refreshCoreAndRender();
    }),
    button("Check Availability", "Roll d6 plus settlement size against difficulty 6 to see whether the chosen item or service is available here.", async () => {
      const itemName = availabilityPicker.picker.selectedOptions[0]?.textContent || availabilityPicker.picker.value || "";
      const result = await api("/api/campaign/tag/availability", { method: "POST", body: JSON.stringify({ item_name: itemName, difficulty: 6 }) });
      setStatus(result.check?.result_text || "Availability checked.");
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  const worldList = card("Known Settlements / Campaign Records", "Friendly settlements are active campaign world records; troublesome towns are placeholders for later supplement support. Use Campaign Management for inline editing.");
  const worldFilters = worldFilterControls("modern-settlement-world", drawWorldSettlements);
  const worldRows = el("div", "modern-list");
  worldList.append(worldFilters.panel, worldRows);
  function drawWorldSettlements() {
    worldRows.replaceChildren();
    const friendly = filteredWorldRows(worldSettlements(), worldFilters);
    const troublesome = filteredWorldRows(worldSettlements("troublesome"), worldFilters);
    for (const worldSettlement of friendly) {
      const homeTroupes = worldTroupes().filter((item) => item.home_settlement_id === worldSettlement.id).map((item) => item.name).join(", ") || "no troupe home";
      worldRows.appendChild(modernStatusRow(worldSettlement.name, `Friendly · Campaign ${worldName(worldCampaigns(), worldSettlement.campaign_id)} · size ${worldSettlement.size >= 0 ? "+" : ""}${worldSettlement.size} · ${homeTroupes} · ${worldSettlement.notes || "No notes"}`, "Friendly world settlement assignment. Size can affect TAG availability checks when this settlement is active."));
    }
    for (const worldSettlement of troublesome) {
      worldRows.appendChild(modernStatusRow(worldSettlement.name, `Troublesome placeholder · Campaign ${worldName(worldCampaigns(), worldSettlement.campaign_id)} · size ${worldSettlement.size >= 0 ? "+" : ""}${worldSettlement.size} · ${worldSettlement.notes || "No notes"}`, "Troublesome-town placeholder only. No supplement-specific mechanics are implemented yet."));
    }
    if (!worldRows.childElementCount) worldRows.appendChild(el("p", "muted", "No campaign settlement records match the current filters."));
  }
  drawWorldSettlements();

  const list = card("Tracked TAG Settlements", "Create, select, travel to, or delete TAG settlements tracked in this campaign. These are the settlement-state records used by TAG service and travel tools.");
  const trackedPicker = searchablePicker(
    "modern-tag-settlements",
    "Tracked settlement",
    "Tracked TAG settlement to review.",
    campaign.tag_settlements || [],
    (row) => `${row.name} (${row.size >= 0 ? "+" : ""}${row.size})`,
    (row) => `${row.name} ${row.notes || ""} ${row.size}`,
    null,
    { sortOptions: [["name", "Name"], ["class", "Size"]], blank: "Choose tracked settlement" }
  );
  const trackedRows = el("div", "modern-list");
  list.append(trackedPicker.wrap, trackedRows);
  function drawTrackedSettlements() {
    trackedRows.replaceChildren();
    const needle = trackedPicker.search.value.trim().toLowerCase();
    const rows = (campaign.tag_settlements || []).filter((settlement) => !needle || `${settlement.name} ${settlement.notes || ""} ${settlement.size}`.toLowerCase().includes(needle));
    rows.sort((left, right) => trackedPicker.sort.value === "class" ? (left.size || 0) - (right.size || 0) || left.name.localeCompare(right.name) : left.name.localeCompare(right.name));
    for (const settlement of rows) {
      const item = el("div", "modern-row");
      const troupeHere = settlement.name === campaign.settlement_name ? campaign.tag_troupe_name || "Current troupe" : "No troupe currently focused here";
      item.append(el("strong", "", `${settlement.name} (${settlement.size >= 0 ? "+" : ""}${settlement.size})`), el("span", "muted", `${troupeHere} · ${settlement.notes || "No notes"}`));
      item.title = "Tracked TAG settlement state. Select makes it the active downtime settlement; Travel To logs travel and changes the current settlement.";
      const itemActions = actions();
      itemActions.append(
        button("Select", "Make this the current TAG settlement without rolling travel.", async () => {
          const result = await api("/api/campaign/tag/settlement", { method: "POST", body: JSON.stringify({ action: "select", settlement_id: settlement.id }) });
          modernState.campaign = result.campaign;
          setStatus(`${settlement.name} selected.`);
          await refreshCoreAndRender();
        }),
        button("Travel To", "Travel to this settlement and roll TAG travel days/size. Use when the troupe physically moves between settlements.", async () => {
          const result = await api("/api/campaign/tag/travel-settlement", { method: "POST", body: JSON.stringify({ destination_name: settlement.name, use_hex_map: false, pay_road_tithe: false }) });
          modernState.campaign = result.campaign;
          setStatus(result.entry?.result_text || "Travel logged.");
          await refreshCoreAndRender();
        }),
        button("Delete", "Delete this tracked settlement from the TAG settlement list. Current settlement state is preserved if this is the last settlement.", async () => {
          if (!window.confirm(`Delete settlement ${settlement.name}?`)) return;
          const result = await api("/api/campaign/tag/settlement", { method: "POST", body: JSON.stringify({ action: "delete", settlement_id: settlement.id }) });
          modernState.campaign = result.campaign;
          setStatus(result.deleted ? "Settlement deleted." : "Settlement not found.");
          await refreshCoreAndRender();
        })
      );
      item.appendChild(itemActions);
      trackedRows.appendChild(item);
    }
    if (!trackedRows.childElementCount) trackedRows.appendChild(el("p", "muted", "No tracked TAG settlements match the current search."));
  }
  trackedPicker.search.addEventListener("input", drawTrackedSettlements);
  trackedPicker.sort.addEventListener("change", drawTrackedSettlements);
  drawTrackedSettlements();
  rootEl.append(panel, worldList, list, renderTagSignoffPanel("Settlement / Travel Signoff"));
}

async function renderCampaign() {
  const command = await api(`/api/campaign/command-center?campaign_id=${encodeURIComponent(modernState.campaign?.active_world_campaign_id || "")}`);
  const campaign = modernState.campaign || {};
  rootEl.appendChild(renderGuide("Campaign Workflow", [
    "Campaign is the world-builder layer; it is app-owned rather than a TAG PDF rule.",
    "Assign one guild per campaign, multiple troupes, and multiple friendly/troublesome settlements.",
    "Use map notes for hex-map planning until the dedicated campaign map editor is built."
  ], "campaign_command_center", "campaign world builder"));
  const layout = el("div", "modern-world-grid");
  const filters = worldFilterControls("modern-world", drawLists);

  const selected = selectedWorldCampaign();
  const selectedCounts = selected ? worldCampaignCounts(selected.id) : { guilds: 0, troupes: 0, settlements: 0, troublesome: 0 };
  const selectedCard = card("Selected Campaign", "The selected campaign is the default assignment for new guilds, troupes, settlements, parties, and character world context.");
  selectedCard.appendChild(modernStatusRow(
    selected?.name || "No campaign selected",
    selected ? `${selected.description || "No description"} · ${selectedCounts.guilds} guild(s) · ${selectedCounts.troupes} troupe(s) · ${selectedCounts.settlements} friendly settlement(s) · ${selectedCounts.troublesome} troublesome town(s)` : "Create a campaign below.",
    "Selected campaign summary. Use Select on a campaign row to change where new world-builder records default."
  ));

  const campaignsCard = card("Campaign Details", "Campaigns are the world-builder layer. A guild, troupes, settlements, parties, and characters point into this layer without changing printed TAG rules.");
  const campaignName = input("text", "modern-campaign-name", "Name for a new campaign/world.", "New Campaign");
  const campaignDescription = textarea("modern-campaign-description", "Campaign description, premise, geography, or house notes.", 4);
  const campaignRows = el("div", "modern-list");
  campaignsCard.append(field("Name", campaignName), field("Description", campaignDescription));
  campaignsCard.appendChild(button("Create Campaign", "Create a new campaign/world record.", () => worldAction({ action: "create", entity: "campaign", name: campaignName.value, description: campaignDescription.value }), ""));
  campaignsCard.appendChild(campaignRows);

  const guildsCard = card("Guilds", "Create guild records and assign one guild to each campaign. The default Adventurers Guild stays available for Norindaal.");
  const guildName = input("text", "modern-world-guild-name", "Name for a new guild record.", "New Guild");
  const guildCampaign = select("modern-world-guild-campaign", "Campaign that receives this guild. A campaign may have only one assigned guild.", worldCampaignOptions());
  guildCampaign.value = campaign.active_world_campaign_id || "norindaal";
  const guildDescription = textarea("modern-world-guild-description", "Purpose, membership notes, benefits, local politics, or finance reminders for the new guild.", 3);
  const guildRows = el("div", "modern-list");
  guildsCard.append(field("Guild name", guildName), field("Campaign", guildCampaign), field("Description", guildDescription));
  guildsCard.appendChild(button("Create Guild", "Create a guild and assign it to the selected campaign. The app blocks assigning two guilds to one campaign.", () => worldAction({ action: "create", entity: "guild", name: guildName.value, campaign_id: guildCampaign.value, description: guildDescription.value }), ""));
  guildsCard.appendChild(guildRows);

  const troupesCard = card("Troupes", "Create troupes, assign them to one campaign, and connect them to a guild and home settlement. Parties are then assigned to a troupe.");
  const troupeName = input("text", "modern-world-troupe-name", "Name for a new troupe.", "New Troupe");
  const troupeCampaign = select("modern-world-troupe-campaign", "Campaign this troupe belongs to.", worldCampaignOptions());
  troupeCampaign.value = campaign.active_world_campaign_id || "norindaal";
  const troupeGuild = select("modern-world-troupe-guild", "Guild connected to this troupe.", worldGuildOptions());
  troupeGuild.value = "adventurers-guild";
  const troupeSettlement = select("modern-world-troupe-settlement", "Friendly home settlement for this troupe.", worldSettlementOptions());
  troupeSettlement.value = "brightwater-gate";
  const troupeDescription = textarea("modern-world-troupe-description", "Travel style, party notes, roster theme, obligations, or campaign role for the new troupe.", 3);
  const troupeRows = el("div", "modern-list");
  troupesCard.append(field("Troupe name", troupeName), field("Campaign", troupeCampaign), field("Guild", troupeGuild), field("Home settlement", troupeSettlement), field("Description", troupeDescription));
  troupesCard.appendChild(button("Create Troupe", "Create a troupe assigned to the selected campaign, guild, and home settlement. Parties and characters can then point to this troupe.", () => worldAction({ action: "create", entity: "troupe", name: troupeName.value, campaign_id: troupeCampaign.value, guild_id: troupeGuild.value, home_settlement_id: troupeSettlement.value, description: troupeDescription.value }), ""));
  troupesCard.appendChild(troupeRows);

  function settlementCard(kind) {
    const isTroublesome = kind === "troublesome";
    const section = card(isTroublesome ? "Troublesome Towns" : "Friendly Settlements", isTroublesome ? "Placeholder records for the future Troublesome Towns supplements. These are campaign world records only until that add-on is implemented." : "Friendly towns, villages, and cities used for home bases, services, availability checks, and travel.");
    const name = input("text", `modern-world-${kind}-name`, isTroublesome ? "Name for a troublesome town placeholder." : "Name for a friendly settlement.", isTroublesome ? "Troublesome Town" : "New Settlement");
    const assignCampaign = select(`modern-world-${kind}-campaign`, "Campaign this settlement belongs to.", worldCampaignOptions());
    assignCampaign.value = campaign.active_world_campaign_id || "norindaal";
    const size = select(`modern-world-${kind}-size`, "Settlement size modifier. It affects service and item availability checks where those rules are used.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
    const notes = textarea(`modern-world-${kind}-notes`, "Notes, services, hazards, hooks, or supplement-specific reminders.", 3);
    const rows = el("div", "modern-list");
    section.append(field("Name", name), field("Campaign", assignCampaign), field("Size", size), field("Notes", notes));
    section.appendChild(button(isTroublesome ? "Create Troublesome Town" : "Create Settlement", isTroublesome ? "Create a future troublesome-town placeholder. This does not implement supplement mechanics yet." : "Create this friendly settlement record and assign it to one campaign for services, travel, and home-base context.", () => worldAction({ action: "create", entity: isTroublesome ? "troublesome_town" : "settlement", name: name.value, campaign_id: assignCampaign.value, size: Number(size.value), notes: notes.value }), ""));
    section.appendChild(rows);
    section._worldRows = rows;
    return section;
  }

  const friendlyCard = settlementCard("friendly");
  const troublesomeCard = settlementCard("troublesome");

  const mapCard = card("Campaign / World Hex Map", "Placeholder for the future hex-map editor. Save map planning notes here until the map tool is implemented.");
  const mapNotes = textarea("modern-world-map-notes", "Hex-map planning notes, region list, settlement placement ideas, or travel assumptions.", 5);
  mapNotes.value = campaign.world_map_notes || "";
  mapCard.append(field("Map notes", mapNotes));
  mapCard.appendChild(button("Save Map Notes", "Save campaign hex-map planning notes.", async () => {
    modernState.campaign = await api("/api/campaign", { method: "PUT", body: JSON.stringify({ world_map_notes: mapNotes.value }) });
    setStatus("World map notes saved.");
    await refreshCoreAndRender();
  }, ""));

  function renderCampaignRows() {
    campaignRows.replaceChildren();
    const rows = filteredWorldRows(worldCampaigns(), filters, (row) => worldName(worldGuilds(), row.guild_id, ""));
    if (!rows.length) campaignRows.appendChild(el("p", "muted", "No campaigns match the current filters."));
    for (const item of rows) {
      const counts = worldCampaignCounts(item.id);
      const row = el("div", "modern-row");
      const nameEdit = input("text", `modern-campaign-edit-${item.id}`, item.id === "norindaal" ? "Default campaign name is kept as Norindaal by the migration/defaulting layer." : "Campaign name shown in world-builder lists and assignment selectors.", item.name);
      const descriptionEdit = textarea(`modern-campaign-description-${item.id}`, "Campaign description shown in dashboard summaries and search results.", 3);
      descriptionEdit.value = item.description || "";
      row.append(
        el("strong", "", `${item.name}${item.id === campaign.active_world_campaign_id ? " (selected)" : ""}`),
        el("span", "muted", `Guild ${worldName(worldGuilds(), item.guild_id)} · ${counts.troupes} troupe(s) · ${counts.settlements} settlement(s) · ${counts.troublesome} troublesome town(s)`),
        field("Name", nameEdit),
        field("Description", descriptionEdit)
      );
      const rowActions = actions();
      rowActions.append(
        button("Select", "Make this the selected campaign for new world-builder records and dashboard defaults.", () => worldAction({ action: "select", entity: "campaign", id: item.id })),
        button("Save", "Save this campaign description and, for non-default campaigns, its display name.", () => worldAction({ action: "update", entity: "campaign", id: item.id, name: nameEdit.value, description: descriptionEdit.value })),
        button("Delete", "Remove this campaign and unassign its world records. Norindaal cannot be deleted.", async () => {
          const warning = `Delete campaign ${item.name}? This will unassign ${counts.guilds} guild(s), ${counts.troupes} troupe(s), ${counts.settlements} friendly settlement(s), and ${counts.troublesome} troublesome town(s).`;
          if (!window.confirm(warning)) return;
          await worldAction({ action: "delete", entity: "campaign", id: item.id });
        })
      );
      row.appendChild(rowActions);
      campaignRows.appendChild(row);
    }
  }

  function renderGuildRows() {
    guildRows.replaceChildren();
    const rows = filteredWorldRows(worldGuilds(), filters);
    if (!rows.length) guildRows.appendChild(el("p", "muted", "No guilds match the current filters."));
    for (const guild of rows) {
      const nameEdit = input("text", `modern-world-guild-name-${guild.id}`, guild.id === "adventurers-guild" ? "Default guild name is kept as Adventurers Guild. Use the description for campaign-specific notes." : "Guild name shown in campaign assignment and character context.", guild.name);
      const descriptionEdit = textarea(`modern-world-guild-description-${guild.id}`, "Guild notes, scope, obligations, finance context, or membership policy.", 3);
      descriptionEdit.value = guild.description || "";
      const assign = select(`modern-world-guild-${guild.id}-campaign`, "Move this guild to another campaign. The app blocks two guilds on one campaign.", worldCampaignOptions());
      assign.value = guild.campaign_id || "";
      const conflict = worldGuilds().find((item) => item.id !== guild.id && item.campaign_id === assign.value);
      const row = el("div", "modern-row");
      row.append(
        el("strong", "", guild.name),
        el("span", "muted", `Campaign ${worldName(worldCampaigns(), guild.campaign_id)}${conflict ? ` · conflict if moved: ${conflict.name}` : ""}`),
        field("Name", nameEdit),
        field("Campaign", assign),
        field("Description", descriptionEdit)
      );
      const rowActions = actions();
      rowActions.append(
        button("Save", "Save this guild name/description and campaign assignment. Each campaign may have only one guild.", () => worldAction({ action: "update", entity: "guild", id: guild.id, name: nameEdit.value, description: descriptionEdit.value, campaign_id: assign.value })),
        button("Delete", "Delete this guild and clear troupe links to it. The default Adventurers Guild cannot be deleted.", async () => {
          if (!window.confirm(`Delete guild ${guild.name}? Linked troupes keep their campaign but lose this guild link.`)) return;
          await worldAction({ action: "delete", entity: "guild", id: guild.id });
        })
      );
      row.appendChild(rowActions);
      guildRows.appendChild(row);
    }
  }

  function renderTroupeRows() {
    troupeRows.replaceChildren();
    const rows = filteredWorldRows(worldTroupes(), filters, (row) => `${worldName(worldGuilds(), row.guild_id, "")} ${worldName(worldSettlements(), row.home_settlement_id, "")}`);
    if (!rows.length) troupeRows.appendChild(el("p", "muted", "No troupes match the current filters."));
    for (const troupe of rows) {
      const nameEdit = input("text", `modern-world-troupe-name-${troupe.id}`, troupe.id === "troupe1" ? "Default troupe name is kept as Troupe1. Use the description for campaign-specific notes." : "Troupe name shown in party, character, and campaign context.", troupe.name);
      const descriptionEdit = textarea(`modern-world-troupe-description-${troupe.id}`, "Troupe travel notes, roster theme, obligations, or current campaign purpose.", 3);
      descriptionEdit.value = troupe.description || "";
      const assign = select(`modern-world-troupe-${troupe.id}-campaign`, "Move this troupe to another campaign. A troupe can only belong to one campaign.", worldCampaignOptions());
      assign.value = troupe.campaign_id || "";
      const guildEdit = select(`modern-world-troupe-${troupe.id}-guild`, "Guild linked to this troupe. Characters assigned through this troupe inherit this guild context.", worldGuildOptions());
      guildEdit.value = troupe.guild_id || "";
      const settlementEdit = select(`modern-world-troupe-${troupe.id}-home`, "Friendly home settlement for this troupe. Character sheets show this as home settlement context.", worldSettlementOptions());
      settlementEdit.value = troupe.home_settlement_id || "";
      const row = el("div", "modern-row");
      row.append(
        el("strong", "", troupe.name),
        el("span", "muted", `Campaign ${worldName(worldCampaigns(), troupe.campaign_id)} · guild ${worldName(worldGuilds(), troupe.guild_id)} · home ${worldName(worldSettlements(), troupe.home_settlement_id)} · ${(troupe.party_ids || []).length} party(s)`),
        field("Name", nameEdit),
        field("Campaign", assign),
        field("Guild", guildEdit),
        field("Home settlement", settlementEdit),
        field("Description", descriptionEdit)
      );
      const rowActions = actions();
      rowActions.append(
        button("Save", "Save this troupe's campaign, guild, home settlement, and notes. Existing assigned characters keep their current context until reassigned or party/troupe sync runs.", () => worldAction({ action: "update", entity: "troupe", id: troupe.id, name: nameEdit.value, description: descriptionEdit.value, campaign_id: assign.value, guild_id: guildEdit.value, home_settlement_id: settlementEdit.value })),
        button("Delete", "Delete this troupe, clear party/character troupe links, and move home-settlement links back to Hearthmere. Troupe1 cannot be deleted.", async () => {
          if (!window.confirm(`Delete troupe ${troupe.name}? Assigned parties and characters will lose this troupe assignment.`)) return;
          await worldAction({ action: "delete", entity: "troupe", id: troupe.id });
        })
      );
      row.appendChild(rowActions);
      troupeRows.appendChild(row);
    }
  }

  function renderSettlementRows(kind, mount) {
    mount.replaceChildren();
    const isTroublesome = kind === "troublesome";
    const rows = filteredWorldRows(worldSettlements(kind), filters);
    if (!rows.length) mount.appendChild(el("p", "muted", isTroublesome ? "No troublesome town placeholders match the current filters." : "No friendly settlements match the current filters."));
    for (const settlement of rows) {
      const nameEdit = input("text", `modern-world-${kind}-name-${settlement.id}`, settlement.id === "brightwater-gate" ? "Default friendly settlement name is kept as Hearthmere. Edit size and notes here." : "Settlement name shown in campaign, troupe, travel, and character home context.", settlement.name);
      const assign = select(`modern-world-${kind}-${settlement.id}-campaign`, "Move this settlement to another campaign. A settlement can only belong to one campaign.", worldCampaignOptions());
      assign.value = settlement.campaign_id || "";
      const sizeEdit = select(`modern-world-${kind}-${settlement.id}-size`, "Settlement size modifier. This affects TAG item/service availability checks where those rules are used.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
      sizeEdit.value = String(settlement.size ?? 0);
      const notesEdit = textarea(`modern-world-${kind}-${settlement.id}-notes`, "Notes, services, hazards, hooks, or supplement-specific reminders shown in search and summaries.", 3);
      notesEdit.value = settlement.notes || "";
      const row = el("div", "modern-row");
      row.append(
        el("strong", "", settlement.name),
        el("span", "muted", `Campaign ${worldName(worldCampaigns(), settlement.campaign_id)} · size ${settlement.size >= 0 ? "+" : ""}${settlement.size} · ${settlement.notes || "No notes"}`),
        field("Name", nameEdit),
        field("Campaign", assign),
        field("Size", sizeEdit),
        field("Notes", notesEdit)
      );
      const rowActions = actions();
      rowActions.append(
        button("Save", isTroublesome ? "Save this troublesome-town placeholder. Supplement-specific rules are still planned." : "Save this friendly settlement's assignment, size modifier, and notes.", () => worldAction({ action: "update", entity: isTroublesome ? "troublesome_town" : "settlement", id: settlement.id, name: nameEdit.value, campaign_id: assign.value, size: Number(sizeEdit.value), notes: notesEdit.value })),
        button("Delete", "Delete this settlement record. Hearthmere cannot be deleted; troupe home links move back to Hearthmere when another settlement is deleted.", async () => {
          if (!window.confirm(`Delete settlement ${settlement.name}? Linked troupe home settlements will fall back to Hearthmere.`)) return;
          await worldAction({ action: "delete", entity: isTroublesome ? "troublesome_town" : "settlement", id: settlement.id });
        })
      );
      row.appendChild(rowActions);
      mount.appendChild(row);
    }
  }

  function drawLists() {
    renderCampaignRows();
    renderGuildRows();
    renderTroupeRows();
    renderSettlementRows("friendly", friendlyCard._worldRows);
    renderSettlementRows("troublesome", troublesomeCard._worldRows);
  }

  layout.append(renderCommandCenter(command), renderGuidanceArchive(), selectedCard, filters.panel, campaignsCard, guildsCard, troupesCard, friendlyCard, troublesomeCard, mapCard, renderCampaignChronicle("Campaign Chronicle", 16));
  drawLists();
  rootEl.appendChild(layout);
}

function renderSettings() {
  const prefs = readModernPrefs();
  rootEl.appendChild(renderGuide("Settings Workflow", [
    "Settings affect dashboard defaults and Go Adventure choices; they do not delete rules data.",
    "Enabled rulesets control which profiles appear as preferred random-adventure choices.",
    "TAG banking toggles which finance workflow the dashboard emphasizes."
  ], "", "settings ruleset profile"));
  const panel = card("Settings / Options", "Save dashboard preferences for starting adventures. These preferences are used by Go Adventure.");
  const tag = input("checkbox", "modern-tag-banking", "Use TAG banking for campaign finance actions instead of only the legacy home-bank flow.");
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
    const checkbox = input("checkbox", `modern-enabled-ruleset-${profile.id}`, `Show ${profile.label} as an available ruleset profile in Go Adventure. This only changes dashboard filtering; it does not remove rules data.`);
    const enabled = prefs.enabledRulesets ? prefs.enabledRulesets.includes(profile.id) : true;
    checkbox.checked = enabled;
    const row = el("label", "modern-check-row");
    row.append(checkbox, el("span", "", profile.label));
    row.title = checkbox.title;
    rulesCard.appendChild(row);
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

function adventureModuleKind(adventure) {
  const id = String(adventure.id || "");
  const source = String(adventure.source || "").toLowerCase();
  if (id === "random" || source === "rules") return "Rules";
  if (id.startsWith("ai-") || source === "ai") return "AI";
  if (adventure.tag_lead_type || (modernState.campaign?.tag_generated_adventure_ids || []).includes(id)) return "The Adventures Guild";
  return "Imported";
}

function adventureModuleInUse(adventureId) {
  return (modernState.sessions || []).filter((session) => session.adventure_id === adventureId && session.mode !== "complete");
}

function adventureModuleCompleted(adventureId) {
  return (modernState.sessions || []).some((session) => session.adventure_id === adventureId && session.mode === "complete");
}

function adventureModuleTags(adventure) {
  const tags = [adventureModuleKind(adventure)];
  if (adventure.playable === false) tags.push("Not playable");
  if (adventureModuleCompleted(adventure.id)) tags.push("Completed");
  if (adventureModuleInUse(adventure.id).length) tags.push("In use");
  return tags;
}

function renderAdventureModuleManager() {
  const panel = card(
    "Generated Adventure Modules",
    "One list is cleaner than separate AI and Adventures Guild lists: the tag on each module shows its source, completion state, and whether an active session is using it. The server also blocks deletion while a module is in use."
  );
  const rows = [...(modernState.adventures || [])].sort((a, b) => (a.name || a.title || a.id).localeCompare(b.name || b.title || b.id));
  for (const adventure of rows) {
    const id = String(adventure.id || "");
    const title = adventure.name || adventure.title || id;
    const inUse = adventureModuleInUse(id);
    const protectedModule = ["random", "ai-adventure", "courtship-demesne"].includes(id) || adventure.source === "rules" || adventure.playable === false;
    const row = el("div", "modern-row modern-module-row");
    const copy = el("div", "modern-row-copy");
    copy.append(el("strong", "", title));
    copy.append(el("span", "muted", `${id} · ${adventure.room_count || 0} room(s) · ${adventure.notes || "Playable imported module."}`));
    const tags = el("div", "modern-chip-row");
    for (const tag of adventureModuleTags(adventure)) tags.appendChild(el("span", "modern-tag", tag));
    copy.appendChild(tags);
    row.appendChild(copy);
    const rowActions = actions();
    if (!protectedModule) {
      rowActions.append(
        link("Export JSON", `/api/adventures/${encodeURIComponent(id)}/export`, "Export this module manifest as JSON."),
        link("Export ZIP", `/api/adventures/${encodeURIComponent(id)}/export.zip`, "Export this module as a zip package.")
      );
      const remove = button("Delete", inUse.length ? "Cannot delete while this module has an in-progress game." : "Delete this installed module. Completed session history is kept.", async () => {
        if (inUse.length) throw new Error(`Cannot delete ${title}: ${inUse.length} game(s) still use it.`);
        if (!window.confirm(`Delete ${title}?`)) return;
        const result = await api(`/api/adventures/${encodeURIComponent(id)}`, { method: "DELETE" });
        setStatus(result.message || "Adventure module deleted.");
        await refreshCoreAndRender();
      });
      remove.disabled = Boolean(inUse.length);
      rowActions.appendChild(remove);
    } else {
      rowActions.appendChild(el("span", "muted", protectedModule ? "Protected module" : ""));
    }
    row.appendChild(rowActions);
    panel.appendChild(row);
  }
  if (!rows.length) panel.appendChild(el("p", "muted", "No adventure modules found."));
  return panel;
}

function renderAdventureModuleImport() {
  const panel = card("Import Module", "Import any reviewed adventure manifest JSON. The module will appear in the unified module list with source/status tags after validation.");
  const json = textarea("modern-module-import-json", "Paste an adventure module JSON manifest to validate or import.", 8);
  const file = input("file", "modern-module-import-file", "Load an adventure module JSON file.");
  file.accept = ".json,application/json";
  file.addEventListener("change", async () => {
    const selected = file.files?.[0];
    if (!selected) return;
    json.value = await selected.text();
    setStatus(`Loaded ${selected.name} into Module JSON.`);
  });
  panel.append(field("Module JSON", json), field("Import file", file));
  const row = actions();
  row.append(
    button("Validate Module", "Validate the pasted adventure module before importing it.", async () => {
      const result = await api("/api/adventures/validate", { method: "POST", body: JSON.stringify({ manifest: JSON.parse(json.value) }) });
      setStatus(result.valid ? "Adventure module JSON valid." : `Invalid: ${(result.errors || []).join("; ")}`);
    }),
    button("Import Module", "Import the pasted module as an installed adventure. The app rejects invalid manifests.", async () => {
      const result = await api("/api/adventures/import", { method: "POST", body: JSON.stringify({ manifest: JSON.parse(json.value), overwrite: false }) });
      setStatus(result.message || `Imported ${result.title || result.adventure_id}.`);
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  return panel;
}

function renderAdventureModuleBrowser() {
  const panel = card(
    "Adventure Module Browser",
    "Select a module to inspect source, status, cover-art guidance, export actions, and delete safety. The server blocks deletion while a module is used by an active session."
  );
  const rows = [...(modernState.adventures || [])].sort((a, b) => (a.name || a.title || a.id).localeCompare(b.name || b.title || b.id));
  if (!rows.length) {
    panel.appendChild(el("p", "muted", "No adventure modules found."));
    return panel;
  }
  const browser = el("div", "modern-adventure-browser");
  const list = el("div", "modern-adventure-list");
  const detail = el("div", "modern-adventure-detail");
  let selectedId = rows[0]?.id || "";
  const summary = (adventure) => {
    const id = String(adventure.id || "");
    const title = adventure.name || adventure.title || id;
    const inUse = adventureModuleInUse(id);
    const protectedModule = ["random", "ai-adventure", "courtship-demesne"].includes(id) || adventure.source === "rules" || adventure.playable === false;
    return { id, title, inUse, protectedModule };
  };
  const drawDetail = (adventure) => {
    detail.replaceChildren();
    if (!adventure) {
      detail.appendChild(el("p", "muted", "No module selected."));
      return;
    }
    const { id, title, inUse, protectedModule } = summary(adventure);
    detail.appendChild(el("h3", "", title));
    detail.appendChild(el("p", "muted", adventure.notes || "Playable imported module."));
    const tags = el("div", "modern-chip-row");
    for (const tag of adventureModuleTags(adventure)) tags.appendChild(el("span", "modern-tag", tag));
    detail.appendChild(tags);
    detail.append(
      modernStatusRow("Module id", id, "Stable module id used by saved sessions and export/delete endpoints."),
      modernStatusRow("Rooms", `${adventure.room_count || 0} room(s)`, "Imported and generated modules use authored room counts; Random Dungeon is procedural."),
      modernStatusRow("Source", adventureModuleKind(adventure), "Source tag used to distinguish rules, imported, AI-authored, and Adventures Guild generated modules."),
      modernStatusRow("Usage", inUse.length ? `${inUse.length} active session(s)` : "Not currently in use", "Modules in active sessions cannot be deleted."),
      modernStatusRow("Cover art", `Planned: DATA_DIR/assets/artwork/user/adventures/${id}_cover_1600x900.*`, "Future module cover art slot. Keep copyrighted or AI-generated artwork local unless licensed for distribution.")
    );
    const rowActions = actions();
    if (!protectedModule) {
      rowActions.append(
        link("Export JSON", `/api/adventures/${encodeURIComponent(id)}/export`, "Export this module manifest as JSON."),
        link("Export ZIP", `/api/adventures/${encodeURIComponent(id)}/export.zip`, "Export this module as a zip package.")
      );
      const remove = button("Delete", inUse.length ? "Cannot delete while this module has an in-progress game." : "Delete this installed module. Completed session history is kept.", async () => {
        if (inUse.length) throw new Error(`Cannot delete ${title}: ${inUse.length} game(s) still use it.`);
        if (!window.confirm(`Delete ${title}?`)) return;
        const result = await api(`/api/adventures/${encodeURIComponent(id)}`, { method: "DELETE" });
        setStatus(result.message || "Adventure module deleted.");
        await refreshCoreAndRender();
      });
      remove.disabled = Boolean(inUse.length);
      rowActions.appendChild(remove);
    } else {
      rowActions.appendChild(el("span", "muted", "Protected module"));
    }
    detail.appendChild(rowActions);
  };
  const drawList = () => {
    list.replaceChildren();
    for (const adventure of rows) {
      const { id, title, inUse } = summary(adventure);
      const item = document.createElement("button");
      item.type = "button";
      item.className = `modern-adventure-list-item${id === selectedId ? " selected" : ""}`;
      item.title = "Select this module to inspect status, export options, delete safety, and planned cover art.";
      item.append(
        el("strong", "", title),
        el("span", "muted", `${adventureModuleKind(adventure)} · ${adventure.room_count || 0} room(s)${inUse.length ? " · in use" : ""}`)
      );
      item.addEventListener("click", () => {
        selectedId = id;
        drawList();
        drawDetail(rows.find((row) => row.id === selectedId));
      });
      list.appendChild(item);
    }
  };
  browser.append(list, detail);
  panel.appendChild(browser);
  drawList();
  drawDetail(rows.find((row) => row.id === selectedId));
  return panel;
}

function renderPlaytestTriagePanel(context = "Playtest") {
  const panel = card("Playtest Triage", "Capture confusing or blocked play flow while the exact context is fresh. Use this for app workflow issues; verify rule changes against the PDF before changing mechanics.");
  const area = select(`modern-playtest-area-${context}`, "Where did the issue happen?", [
    ["exploration", "Exploration / Narrative"],
    ["objective", "Current Objective / Quest Details"],
    ["tag", "Adventures Guild generated module"],
    ["adventure-management", "Adventure Management"],
    ["go-adventure", "Go Adventure setup"],
    ["rules", "Rules Reference / Tables"],
    ["other", "Other"],
  ]);
  const severity = select(`modern-playtest-severity-${context}`, "How badly did this affect play?", [
    ["blocked", "Blocked play"],
    ["confusing", "Confusing but playable"],
    ["polish", "Polish / wording"],
  ]);
  const happened = textarea(`modern-playtest-happened-${context}`, "What happened? Include exact button/log wording if possible.", 4);
  const expected = textarea(`modern-playtest-expected-${context}`, "What did you expect the app to do?", 3);
  const steps = textarea(`modern-playtest-steps-${context}`, "Steps to reproduce from the current save/module.", 4);
  const report = textarea(`modern-playtest-report-${context}`, "Copyable Markdown playtest report.", 8);
  const buildReport = () => {
    const active = (modernState.sessions || []).find((session) => session.mode !== "complete");
    const lines = [
      `## Playtest report - ${modernTitleFromKey(area.value)}`,
      "",
      `- Severity: ${modernTitleFromKey(severity.value)}`,
      `- Active session: ${active?.id || "unknown / not loaded in dashboard"}`,
      `- Adventure: ${active?.adventure_id || "unknown"}`,
      "",
      "### What happened",
      happened.value || "-",
      "",
      "### Expected",
      expected.value || "-",
      "",
      "### Steps",
      steps.value || "-",
      "",
      "### Rule boundary",
      "Do not change mechanics until the relevant PDF/table/reference has been checked.",
    ];
    report.value = lines.join("\n");
  };
  const row = actions();
  row.append(
    button("Build Report", "Create a Markdown report from the fields above.", async () => buildReport(), ""),
    button("Copy Report", "Copy the generated Markdown report to the clipboard.", async () => {
      buildReport();
      try {
        await navigator.clipboard.writeText(report.value);
      } catch (error) {
        report.focus();
        report.select();
        document.execCommand("copy");
      }
      setStatus("Playtest report copied.");
    }),
    link("Rules Reference", ruleReferenceHref("playtest_triage_workflow", "playtest triage workflow"), "Open the Rules Reference note for playtest triage and PDF boundaries.", "link-button secondary")
  );
  panel.append(field("Area", area), field("Severity", severity), field("What happened", happened), field("Expected behavior", expected), field("Steps", steps), row, field("Report", report));
  return panel;
}

function renderTagModuleGeneration(selectedAdventureControl = null) {
  const tagLead = card(
    "Generate The Adventures Guild Module",
    "Creates a normal playable adventure module from an Adventures Guild rumor, treasure map, thematic dungeon, or Guild job. Printed choices still belong to the player; fixed rolls are automated and reported in the Narrative."
  );
  const tagLeadType = select("modern-tag-lead-type", "Choose which Adventures Guild lead table to generate from when Random is off.", [
    ["rumor", "Rumor Scene"],
    ["treasure_map", "Treasure Map destination"],
    ["thematic_dungeon", "Thematic Dungeon"],
    ["guild_job", "Guild Job"],
  ]);
  const tagLeadRandom = input("checkbox", "modern-tag-lead-random", "Random Adventures Guild lead: choose the lead family and table result randomly when the module is generated.");
  tagLeadRandom.checked = true;
  const randomRow = el("label", "modern-check-row");
  randomRow.title = tagLeadRandom.title;
  randomRow.append(tagLeadRandom, el("span", "", "Random lead family"));
  const syncTagLeadRandom = () => {
    tagLeadType.disabled = tagLeadRandom.checked;
    tagLeadType.closest("label")?.classList.toggle("muted", tagLeadRandom.checked);
  };
  tagLeadRandom.addEventListener("change", syncTagLeadRandom);
  syncTagLeadRandom();
  tagLead.append(randomRow, field("Lead type", tagLeadType));
  tagLead.appendChild(button("Create Adventures Guild Module", "Create and install an Adventures Guild lead as a playable imported adventure. With Random checked, the app chooses the lead family and table result.", async () => {
    const leadTypes = ["rumor", "treasure_map", "thematic_dungeon", "guild_job"];
    const selectedLeadType = tagLeadRandom.checked
      ? leadTypes[Math.floor(Math.random() * leadTypes.length)]
      : tagLeadType.value;
    const result = await api("/api/campaign/tag/create-adventure", {
      method: "POST",
      body: JSON.stringify({ lead_type: selectedLeadType, detail: "" }),
    });
    modernState.campaign = result.campaign;
    modernState.adventures = await api("/api/adventures");
    if (selectedAdventureControl) {
      selectedAdventureControl.replaceChildren(...optionRows(adventureOptions("imported")));
      selectedAdventureControl.value = result.adventure_id || "";
      writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: result.adventure_id || "" });
    }
    setStatus(`Created ${result.title || result.adventure_id}. Start it from Go Adventure > Start.`);
    await refreshCoreAndRender();
  }));
  return tagLead;
}

function renderAiModuleGeneration() {
  const panel = card("Generate AI Module", "Generate an external-AI prompt, paste or load the returned adventure JSON, validate it, then import it as a playable module.");
  const theme = input("text", "modern-adventure-ai-theme", "Theme for the AI adventure prompt.");
  const promptBox = textarea("modern-adventure-ai-prompt", "Generated prompt/export token text. Send this to your AI tool.", 8);
  const json = textarea("modern-adventure-ai-json", "Paste AI adventure JSON to validate or import.", 10);
  const file = input("file", "modern-adventure-ai-file", "Import adventure JSON from a .json file.");
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
    button("Validate JSON", "Validate pasted AI adventure JSON before import.", async () => {
      const result = await api("/api/adventures/validate", { method: "POST", body: JSON.stringify({ manifest: JSON.parse(json.value) }) });
      setStatus(result.valid ? "Adventure JSON valid." : `Invalid: ${(result.errors || []).join("; ")}`);
    }),
    button("Import JSON", "Import pasted AI adventure JSON as an installed module.", async () => {
      const result = await api("/api/adventures/import", { method: "POST", body: JSON.stringify({ manifest: JSON.parse(json.value), overwrite: false }) });
      setStatus(result.message || `Imported ${result.title || result.adventure_id}.`);
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  return panel;
}

function renderAdventureManagement() {
  rootEl.appendChild(renderGuide("Adventure Management", [
    "Use Modules to import, export, delete, and check whether a module is AI-authored, Adventures Guild generated, completed, or in use.",
    "Use The Adventures Guild generation for rumors, treasure maps, thematic dungeons, and Guild jobs.",
    "Use AI generation when you want a prompt and JSON validation workflow for an external AI-authored adventure.",
    "Start and resume actual play from Go Adventure."
  ], "go_adventure_closeout_gates", "adventure management generated modules import export delete"));
  const tabs = el("div", "modern-tabs");
  const panels = {};
  function activateAdventureTab(key) {
    for (const buttonEl of tabs.querySelectorAll(".modern-tab-button")) {
      const selected = buttonEl.dataset.tab === key;
      buttonEl.classList.toggle("selected", selected);
      buttonEl.setAttribute("aria-selected", selected ? "true" : "false");
    }
    Object.entries(panels).forEach(([panelKey, panelEl]) => {
      panelEl.classList.toggle("hidden", panelKey !== key);
    });
  }
  function addAdventureTab(key, label, title, nodes) {
    const tab = button(label, title, async () => activateAdventureTab(key), "secondary modern-tab-button");
    tab.dataset.tab = key;
    tab.setAttribute("role", "tab");
    tabs.appendChild(tab);
    const panelEl = el("section", "modern-tab-panel hidden");
    panelEl.dataset.tabPanel = key;
    panelEl.setAttribute("role", "tabpanel");
    panelEl.append(...nodes.filter(Boolean));
    panels[key] = panelEl;
  }
  addAdventureTab("modules", "Modules", "Import, export, delete, and review all adventure module types.", [renderAdventureModuleImport(), renderAdventureModuleBrowser()]);
  addAdventureTab("guild", "The Adventures Guild", "Generate Adventures Guild modules and review lead signoff support.", [
    renderTagModuleGeneration(),
    renderTagWorkflowDashboard("go"),
    renderTagLeadSelectorPanel(),
    renderRumorLeadAuditPanel(),
    renderRumorSignoffChecklist(),
    renderTreasureMapLeadAuditPanel(),
    renderTreasureMapSignoffChecklist(),
    renderThematicDungeonLeadAuditPanel(),
    renderThematicDungeonSignoffChecklist(),
  ]);
  addAdventureTab("ai", "AI Modules", "Generate prompts, validate imports, and install AI-authored modules.", [renderAiModuleGeneration()]);
  addAdventureTab("reference", "Reference", "Review closeout, signoff, action history, and rules/table links for generated modules.", [
    renderPlaytestTriagePanel("adventure-management"),
    renderAdventureCloseoutCockpit("Adventure Management"),
    renderTagSignoffPanel("Adventures Guild Lead / Start Signoff"),
    renderTagActionLogExplorer(),
  ]);
  rootEl.append(tabs, ...Object.values(panels));
  activateAdventureTab("modules");
}

async function renderGoAdventure() {
  const prefs = readModernPrefs();
  const workflowGuide = renderGuide("Adventure Workflow", [
    "Start New creates a fresh session from the selected party and module.",
    "Resume Adventure reopens active in-progress sessions; Saved Games are listed separately.",
    "Generate, import, export, or delete modules from Adventure Management.",
    "The Closeout Gate uses campaign guidance and Adventures Guild closeout prompts to warn before starting again."
  ], "tag_guild_closeout_guidance", "go adventure tag lead resume saved");
  const panel = card("Start New Adventure", "Choose party, adventure type, module, ruleset, and start play. This creates a new session.");
  panel.classList.add("modern-primary-card");
  const party = select("modern-start-party", "Party to send on the adventure.", partyOptions());
  party.value = prefs.lastPartyId || "";
  const type = select("modern-adventure-type", "Adventure type filter: Random creates a generated dungeon; Imported/AI uses an installed adventure module.", [["random", "Random"], ["imported", "Imported Adventure Module"], ["ai", "AI Adventure Module"]]);
  type.value = ["random", "imported", "ai"].includes(prefs.lastAdventureType) ? prefs.lastAdventureType : "random";
  const adventure = select("modern-start-adventure", "Specific adventure module to play. For Random, this remains Random Dungeon.", adventureOptions(type.value));
  if (prefs.lastAdventureId && [...adventure.options].some((option) => option.value === prefs.lastAdventureId)) adventure.value = prefs.lastAdventureId;
  const enabledRulesets = prefs.enabledRulesets || modernState.rulesProfiles.map((profile) => profile.id);
  const profileRows = modernState.rulesProfiles.filter((profile) => enabledRulesets.includes(profile.id));
  const profile = select("modern-start-profile", "Ruleset profile used only for Random adventures.", profileRows.map((p) => [p.id, p.label]));
  profile.value = prefs.defaultRulesetProfile || "ee_random";
  const xp = select("modern-start-xp", "XP system for this adventure.", [["classical", "Classical"], ["slow_and_sure", "Slow and Sure"], ["old_school", "Old School"], ["slower_advancement", "Slower Advancement"]]);
  xp.value = prefs.defaultXpSystem || "classical";
  const mapMode = select("modern-start-map-mode", "Map mode for this adventure.", [["unlimited", "Unlimited"], ["paper", "Paper 20x28"]]);
  mapMode.value = prefs.defaultMapMode || "unlimited";
  const mapLimit = input("number", "modern-start-map-limit", "Unlimited-map element cap before end-boss pressure.", String(prefs.defaultMapLimit || 60));
  const readiness = card("Setup Check", "Warnings here should be handled before starting unless you are deliberately testing an edge case.");
  readiness.classList.add("modern-card-compact");
  const gate = card("Closeout Gate", "Server-checked campaign closeout, guidance, roster health, context, equipment, and active-session warnings for the selected party.");
  gate.classList.add("modern-card-compact");
  const gateRows = el("div", "modern-list");
  gate.appendChild(gateRows);
  const overrideStart = input("checkbox", "modern-start-override", "Allow Start Adventure to proceed through overridable closeout/guidance warnings. Hard blocks such as fallen members and active locks cannot be overridden.");
  const overrideRow = el("label", "modern-check-row");
  overrideRow.title = overrideStart.title;
  overrideRow.append(overrideStart, el("span", "", "Start anyway after reviewing overridable closeout warnings"));
  const startSummary = el("div", "modern-list modern-start-summary");
  const startStatusIcons = el("section", "modern-dashboard-status-icons modern-start-status-icons");
  startStatusIcons.setAttribute("aria-label", "Start status checks");
  let latestReadinessRows = [];
  let latestGate = null;
  function addStartStatusIcon(symbol, label, value, tooltip, detail, status = "ok") {
    const item = el("button", `modern-dashboard-status-icon modern-start-status-icon ${status === "block" ? "is-block" : status === "warn" ? "is-warn" : "is-ok"}`);
    item.type = "button";
    item.title = `${tooltip}\n\n${formatSnapshotDetail(detail)}`;
    item.append(el("span", "modern-dashboard-status-symbol", symbol), el("strong", "", label), el("span", "muted", value));
    item.addEventListener("click", () => showSnapshotDetail(label, detail));
    startStatusIcons.appendChild(item);
  }
  function drawStartSummary() {
    startSummary.replaceChildren();
    startStatusIcons.replaceChildren();
    const setupIssues = latestReadinessRows.filter(([, , status]) => status !== "ok");
    const gateIssues = latestGate?.issues || [];
    const setupBlocks = latestReadinessRows.filter(([, , status]) => status === "block").length;
    const gateBlocks = gateIssues.filter((issue) => issue.severity === "block").length;
    const setupStatus = setupBlocks ? "block" : (setupIssues.length ? "warn" : "ok");
    const gateStatus = gateBlocks ? "block" : (latestGate?.requires_override || gateIssues.length ? "warn" : "ok");
    addStartStatusIcon(
      setupBlocks ? "!" : (setupIssues.length ? "?" : "✓"),
      "Setup",
      setupIssues.length ? `${setupBlocks} block · ${setupIssues.length - setupBlocks} warn` : "Ready",
      setupIssues.length ? "Open setup issue details." : "No setup issues detected for the selected party/module.",
      setupIssues.length ? setupIssues.map(([title, body, status, hint]) => `${modernTitleFromKey(status)}: ${title} - ${body}${hint ? ` (${hint})` : ""}`) : ["No setup issues detected."],
      setupStatus
    );
    addStartStatusIcon(
      gateBlocks ? "!" : (latestGate?.requires_override || gateIssues.length ? "?" : "✓"),
      "Closeout",
      gateIssues.length ? `${gateBlocks} block · ${gateIssues.length - gateBlocks} warn` : "Clear",
      gateIssues.length ? "Open closeout/guidance gate details." : "No campaign closeout or guidance warnings for this party.",
      gateIssues.length ? gateIssues.map((issue) => `${modernTitleFromKey(issue.severity)}: ${issue.title} - ${issue.body || "No detail."}`) : ["No campaign closeout or guidance warnings for this party."],
      gateStatus
    );
    if (latestGate?.requires_override) startStatusIcons.appendChild(overrideRow);
    startSummary.appendChild(
      modernStatusRow(
        "Ready status",
        setupIssues.length || gateIssues.length
          ? `${setupIssues.length} setup issue(s) · ${gateIssues.length} closeout/guidance issue(s)`
          : "Ready to start.",
        setupIssues.length || gateIssues.length
          ? "Click the setup or closeout status icon for exact issues. Hard blocks still stop Start Adventure."
          : "Setup Check and Closeout Gate are still enforced in the background when Start Adventure is pressed."
      )
    );
  }
  function drawReadiness() {
    readiness.querySelectorAll(".modern-row").forEach((node) => node.remove());
    const rows = adventureReadinessRows(party.value, { adventureType: type.value, adventureId: adventure.value, profileId: profile.value, mapLimitValue: mapLimit.value });
    latestReadinessRows = rows;
    const blocks = adventureReadinessBlocks(rows).length;
    const visibleIssues = rows.filter(([, , status]) => status !== "ok");
    readiness.classList.toggle("hidden", !visibleIssues.length);
    readiness.appendChild(modernStatusRow("Start readiness", blocks ? `${blocks} blocking issue(s) must be resolved before Start Adventure.` : "No blocking setup issues detected.", blocks ? "Start Adventure is blocked until critical setup issues are fixed." : "Warnings may remain if you deliberately start with injured or under-equipped characters."));
    for (const [title, body, status, hint] of rows) {
      const item = modernStatusRow(title, body, hint || (status === "warn" || status === "block" ? "Resolve this warning before starting a normal adventure." : "This setup item is ready."));
      item.classList.add(status === "ok" ? "modern-row-ok" : "modern-row-warn");
      readiness.appendChild(item);
    }
    drawStartSummary();
  }
  async function drawCloseoutGate() {
    gateRows.replaceChildren();
    latestGate = await api(`/api/campaign/closeout-gate?party_id=${encodeURIComponent(party.value || "")}`);
    const issues = latestGate.issues || [];
    const blocks = issues.filter((issue) => issue.severity === "block").length;
    const overrides = issues.filter((issue) => issue.severity === "override").length;
    const warnings = issues.filter((issue) => issue.severity === "warn").length;
    gate.classList.toggle("hidden", !issues.length);
    gateRows.appendChild(modernStatusRow("Gate summary", latestGate.can_start ? `${blocks} block(s) · ${overrides} override warning(s) · ${warnings} warning(s)` : `${blocks} blocking issue(s) must be resolved.`, latestGate.requires_override ? "Explicit override is required for closeout/guidance warnings." : "Hard blocks cannot be overridden."));
    if (!issues.length) {
      gateRows.appendChild(el("p", "muted", "No campaign closeout, roster, context, or active-session warnings for this party."));
    }
    for (const issue of issues) {
      const row = modernStatusRow(issue.title, issue.body, issue.severity === "override" ? "Overridable only after explicit player confirmation." : "Review this start gate issue.");
      row.classList.add(issue.severity === "block" ? "modern-row-warn" : "modern-row-ok");
      gateRows.appendChild(row);
    }
    drawStartSummary();
  }
  panel.append(field("Party", party), field("Adventure type", type), field("Adventure/module", adventure), field("Random ruleset", profile), field("XP system", xp), field("Map mode", mapMode), field("Map limit", mapLimit), startStatusIcons, startSummary);
  drawReadiness();
  await drawCloseoutGate();
  party.addEventListener("change", () => {
    drawReadiness();
    drawCloseoutGate().catch(handleError);
  });
  type.addEventListener("change", () => {
    adventure.replaceChildren(...optionRows(adventureOptions(type.value)));
    writeModernPrefs({ lastAdventureType: type.value, lastAdventureId: adventure.value || "" });
    profile.closest("label")?.classList.toggle("hidden", type.value !== "random");
    drawReadiness();
  });
  adventure.addEventListener("change", () => {
    writeModernPrefs({ lastAdventureType: type.value, lastAdventureId: adventure.value || "" });
    drawReadiness();
  });
  profile.addEventListener("change", drawReadiness);
  mapLimit.addEventListener("input", drawReadiness);
  profile.closest("label")?.classList.toggle("hidden", type.value !== "random");
  const startRow = actions();
  startRow.appendChild(button("Start Adventure", "Create a new session with the selected party and adventure settings.", async () => {
    if (!party.value) throw new Error("Choose a party.");
    const readinessRows = adventureReadinessRows(party.value, { adventureType: type.value, adventureId: adventure.value, profileId: profile.value, mapLimitValue: mapLimit.value });
    const blocking = adventureReadinessBlocks(readinessRows);
    if (blocking.length) throw new Error(`Resolve setup first: ${blocking.map(([title]) => title).join(", ")}.`);
    latestGate = await api(`/api/campaign/closeout-gate?party_id=${encodeURIComponent(party.value || "")}`);
    const gateBlocks = (latestGate.issues || []).filter((issue) => issue.severity === "block");
    if (gateBlocks.length) throw new Error(`Resolve start gate first: ${gateBlocks.map((issue) => issue.title).join(", ")}.`);
    if (latestGate.requires_override && !overrideStart.checked) throw new Error("Review the Closeout Gate and tick Start anyway before overriding required closeout/guidance warnings.");
    writeModernPrefs({ lastPartyId: party.value, defaultRulesetProfile: profile.value, defaultXpSystem: xp.value, defaultMapMode: mapMode.value, defaultMapLimit: Number(mapLimit.value || 60) });
    const adventureId = type.value === "random" ? "random" : adventure.value;
    const session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({
        party_id: party.value,
        adventure_id: adventureId,
        ruleset_profile_id: type.value === "random" ? profile.value : undefined,
        xp_system: xp.value,
        map_bounds_mode: mapMode.value,
        unlimited_map_element_cap: Number(mapLimit.value || 60),
        allow_start_anyway: Boolean(overrideStart.checked),
      }),
    });
    window.location.href = `/?session=${encodeURIComponent(session.id || "")}`;
  }, "modern-start-button"));
  panel.appendChild(startRow);
  const sessions = card("Resume Adventure", "Shows the latest resumable or saved session for each party. Resume the latest active in-progress session for each party; saved games are listed separately below.");
  const visibleSessions = latestSessionPerParty(modernState.sessions);
  const hiddenSessionCount = Math.max(0, (modernState.sessions || []).length - visibleSessions.length);
  if (hiddenSessionCount) {
    sessions.appendChild(el("p", "muted", `${hiddenSessionCount} older session(s) hidden. Delete or load older sessions from the legacy home list if needed.`));
  }
  const activeSessions = visibleSessions.filter((session) => !session.saved_at);
  const savedSessions = visibleSessions.filter((session) => session.saved_at);
  for (const session of activeSessions) {
    const partyName = modernState.parties.find((item) => item.id === session.party_id)?.name || session.party_id;
    const row = el("div", "modern-row");
    row.append(el("strong", "", session.save_label || `${partyName} - ${session.mode}`));
    row.append(el("span", "muted", `${partyName} · ${session.adventure_type || session.adventure_id} · ${session.saved_at ? `saved ${session.saved_at}` : "active/unsaved"} · ${session.tile_count || 0} map element(s)`));
    const rowActions = actions();
    rowActions.append(
      button("Resume Adventure", "Open this active session in the main play interface.", async () => {
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
  if (!activeSessions.length) sessions.appendChild(el("p", "muted", "No active sessions."));
  const saved = card("Saved Games", "Load or delete saved sessions. These are separated from active resumes so continuing an old game is not confused with starting a new one.");
  for (const session of savedSessions) {
    const partyName = modernState.parties.find((item) => item.id === session.party_id)?.name || session.party_id;
    const row = el("div", "modern-row");
    row.append(el("strong", "", session.save_label || `${partyName} - ${session.mode}`));
    row.append(el("span", "muted", `${partyName} · ${session.adventure_type || session.adventure_id} · saved ${session.saved_at} · ${session.tile_count || 0} map element(s)`));
    const rowActions = actions();
    rowActions.append(
      button("Load Saved Game", "Open this saved session in the main play interface.", async () => {
        window.location.href = `/?session=${encodeURIComponent(session.id)}`;
      }, ""),
      button("Delete", "Delete this saved session and unlock its characters.", async () => {
        if (!window.confirm("Delete this saved game?")) return;
        await api(`/api/sessions/${encodeURIComponent(session.id)}`, { method: "DELETE" });
        setStatus("Saved game deleted.");
        await refreshCoreAndRender();
      })
    );
    row.appendChild(rowActions);
    saved.appendChild(row);
  }
  if (!savedSessions.length) saved.appendChild(el("p", "muted", "No saved games."));
  const management = card("Need a module?", "Create Adventures Guild modules, generate AI prompts, import JSON, export backups, and delete unused modules from Adventure Management.");
  const managementActions = actions();
  managementActions.appendChild(button("Open Adventure Management", "Open module management, Adventures Guild generation, AI generation, and reference tools.", async () => {
    window.location.href = "/modern/adventure-management";
  }));
  management.appendChild(managementActions);
  const tabs = el("div", "modern-tabs");
  const panels = {};
  function activateGoAdventureTab(key) {
    for (const buttonEl of tabs.querySelectorAll(".modern-tab-button")) {
      const selected = buttonEl.dataset.tab === key;
      buttonEl.classList.toggle("selected", selected);
      buttonEl.setAttribute("aria-selected", selected ? "true" : "false");
    }
    Object.entries(panels).forEach(([panelKey, panelEl]) => {
      panelEl.classList.toggle("hidden", panelKey !== key);
    });
  }
  function addGoAdventureTab(key, label, title, nodes) {
    const tab = button(label, title, async () => activateGoAdventureTab(key), "secondary modern-tab-button");
    tab.dataset.tab = key;
    tab.setAttribute("role", "tab");
    tabs.appendChild(tab);
    const panelEl = el("section", "modern-tab-panel hidden");
    panelEl.dataset.tabPanel = key;
    panelEl.setAttribute("role", "tabpanel");
    panelEl.append(...nodes.filter(Boolean));
    panels[key] = panelEl;
  }
  addGoAdventureTab("start", "Start", "Start a fresh adventure after setup and closeout checks.", [panel, workflowGuide]);
  addGoAdventureTab("resume", "Resume", "Resume active adventures or load saved games.", [sessions, saved, management]);
  addGoAdventureTab("reference", "Reference / Playtest", "Capture playtest issues and review closeout/reference context.", [
    renderPlaytestTriagePanel("go-adventure"),
    renderAdventureCloseoutCockpit("Go Adventure"),
    renderTagActionLogExplorer(),
  ]);
  rootEl.append(tabs, ...Object.values(panels));
  activateGoAdventureTab("start");
}

async function renderRulesReference() {
  if (!modernState.rulesReference.length) {
    const payload = await api("/api/rules/reference");
    modernState.rulesReference = Array.isArray(payload) ? payload : (payload.entries || []);
  }
  await loadArtwork();
  const panel = card("Rules Reference", "Search every curated implementation reference entry from the app reference index.");
  const search = input("search", "modern-rules-search", "Filter rules reference entries.");
  const params = new URLSearchParams(window.location.search);
  const helpQuery = params.get("help");
  const exactEntryId = params.get("entry");
  if (helpQuery) search.value = helpQuery;
  const categories = [...new Set(modernState.rulesReference.map((entry) => entry.category || "rules"))].sort();
  const category = select("modern-rules-category", "Filter by rules category.", [["", "All categories"], ...categories.map((item) => [item, item])]);
  const statuses = [...new Set(modernState.rulesReference.map((entry) => entry.implementation_status || "reference"))].sort();
  const status = select("modern-rules-status", "Filter by implementation status.", [["", "All statuses"], ...statuses.map((item) => [item, modernStatusLabel(item)])]);
  const source = select("modern-rules-source", "Filter entries by whether they cite a printed source page or have artwork slots.", [["", "All source refs"], ["with", "With source page"], ["app", "App-only / no source page"], ["art", "With artwork slot"]]);
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
      .filter((entry) => !exactEntryId || entry.id === exactEntryId)
      .filter((entry) => !category.value || (entry.category || "rules") === category.value)
      .filter((entry) => !status.value || (entry.implementation_status || "reference") === status.value)
      .filter((entry) => source.value !== "with" || Boolean(entry.source_page))
      .filter((entry) => source.value !== "app" || !entry.source_page)
      .filter((entry) => source.value !== "art" || artworkForReference(entry).length)
      .filter((entry) => `${entry.title} ${entry.summary || ""} ${entry.body} ${entry.category || ""} ${entry.implementation_status || ""} ${entry.source_page || ""} ${(entry.keywords || []).join(" ")} ${artworkForReference(entry).map((art) => `${art.title} ${art.summary} ${art.source_pdf}`).join(" ")}`.toLowerCase().includes(needle))
      .sort((a, b) => String(a[sort.value] || "").localeCompare(String(b[sort.value] || ""), undefined, { numeric: true }) || String(a.title || "").localeCompare(String(b.title || "")));
    const byCategory = rows.reduce((groups, entry) => {
      const key = entry.category || "rules";
      if (!groups[key]) groups[key] = [];
      groups[key].push(entry);
      return groups;
    }, {});
    const summary = el("p", "muted", exactEntryId
      ? `${rows.length ? "Exact" : "No"} rule reference match for ${exactEntryId}.`
      : `${rows.length} matching rule reference entr${rows.length === 1 ? "y" : "ies"} across ${Object.keys(byCategory).length} categor${Object.keys(byCategory).length === 1 ? "y" : "ies"}.`);
    results.appendChild(summary);
    for (const [groupName, items] of Object.entries(byCategory).sort(([a], [b]) => a.localeCompare(b))) {
      const group = document.createElement("details");
      group.className = "modern-row modern-reference-group";
      group.open = Boolean(exactEntryId) || rows.length <= 25 || Boolean(search.value);
      const groupSummary = document.createElement("summary");
      groupSummary.title = `Show or hide ${items.length} ${groupName} reference entries.`;
      groupSummary.append(el("strong", "", modernTitleFromKey(groupName)), el("span", "muted", `${items.length} entr${items.length === 1 ? "y" : "ies"}`));
      group.appendChild(groupSummary);
      const groupBody = el("div", "modern-reference-group-body");
      for (const item of items) {
        const row = document.createElement("details");
        row.className = "modern-row modern-reference-card";
        row.open = Boolean(exactEntryId) || rows.length <= 8;
        const rowSummary = document.createElement("summary");
        rowSummary.title = "Show or hide the full implementation note for this rule reference.";
        rowSummary.append(
          el("strong", "", item.title || item.id),
          el("span", "muted", `${modernStatusLabel(item.implementation_status)}${item.source_page ? ` · p.${item.source_page}` : ""}`)
        );
        row.appendChild(rowSummary);
        if (item.summary) row.appendChild(el("p", "modern-home-status", item.summary));
        if (item.keywords?.length) row.appendChild(el("span", "muted", item.keywords.join(" · ")));
        const relatedArt = artworkForReference(item);
        if (relatedArt.length) row.appendChild(renderArtworkRows(relatedArt.slice(0, 3), { compact: true }));
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
  if (key.includes("artwork")) return "Artwork and local assets";
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
  await loadArtwork();
  const panel = card("Tables List", "Search every structured rules and app table exposed by the game.");
  const search = input("search", "modern-table-search", "Search by table name or entry text.");
  const params = new URLSearchParams(window.location.search);
  const helpQuery = params.get("help");
  const searchQuery = params.get("search");
  if (searchQuery || helpQuery) search.value = searchQuery || helpQuery;
  const families = [...new Set(Object.keys(modernState.tables).map(modernTableFamily))].sort();
  const family = select("modern-table-family", "Filter by table family.", [["", "All table families"], ...families.map((item) => [item, item])]);
  const artworkFilter = select("modern-table-artwork", "Filter tables by whether they have local artwork slots.", [["", "All artwork states"], ["with", "With artwork slot"], ["without", "Without artwork slot"]]);
  const sort = select("modern-table-sort", "Sort table groups.", [["name", "Name"], ["rows", "Row count"]]);
  const results = el("div", "modern-list");
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Family", family), field("Artwork", artworkFilter), field("Sort", sort));
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
      if (artworkFilter.value === "with" && !artworkForTable(key).length) return false;
      if (artworkFilter.value === "without" && artworkForTable(key).length) return false;
      if (!needle) return true;
      return key.toLowerCase().includes(needle)
        || modernSearchText(modernState.tables[key]).toLowerCase().includes(needle)
        || artworkForTable(key).map((art) => `${art.title} ${art.summary} ${art.source_pdf}`).join(" ").toLowerCase().includes(needle);
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
    const artworkCount = keys.filter((key) => artworkForTable(key).length).length;
    results.appendChild(el("p", "muted", `${keys.length} matching table${keys.length === 1 ? "" : "s"} across ${Object.keys(byFamily).length} famil${Object.keys(byFamily).length === 1 ? "y" : "ies"} · ${artworkCount} with artwork slots.`));
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
        const tableArt = artworkForTable(key);
        summary.append(el("strong", "", modernTitleFromKey(key)), el("span", "muted", `${key} · ${modernTableRowCount(value)} row(s)${tableArt.length ? ` · ${tableArt.length} art slot(s)` : ""}`));
        details.appendChild(summary);
        if (tableArt.length) details.appendChild(renderArtworkRows(tableArt.slice(0, 4), { compact: true }));
        const previewMount = el("div", "modern-table-preview-mount");
        const renderPreview = () => {
          const rowNeedle = key.toLowerCase().includes(needle) ? "" : needle;
          if (previewMount.dataset.loaded === "1" && previewMount.dataset.needle === rowNeedle) return;
          previewMount.replaceChildren(modernTablePreview(value, rowNeedle));
          previewMount.dataset.loaded = "1";
          previewMount.dataset.needle = rowNeedle;
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
  artworkFilter.addEventListener("change", draw);
  sort.addEventListener("change", draw);
  draw();
  rootEl.appendChild(panel);
}

async function renderLibrary() {
  await loadArtwork();
  const panel = card("PDF Library and Background", "Open owned PDFs and maintain signoff-safe background summaries.");
  const pdfRow = actions();
  for (const [label, href, title] of PDF_LINKS) pdfRow.appendChild(link(label, href, title));
  panel.appendChild(pdfRow);
  const notes = card("Background Import Plan", "I should not bulk-copy full PDF background text. Work book-by-book and section-by-section: you identify pages, I summarise into app-safe background notes and cite the PDF page.");
  notes.appendChild(el("p", "modern-home-status in-progress", "In progress: curated background summaries and approved artwork/map extraction."));
  const artwork = card("Local Rules Artwork", "Artwork slots for relevant PDF sections. User-facing files live beside game.db under DATA_DIR/assets; /assets URLs prefer that folder and then fall back to bundled defaults.");
  artwork.appendChild(renderArtworkRows(modernState.artwork));
  artwork.appendChild(el("p", "muted", "On Docker this is the shared appdata folder: DATA_DIR/assets, for example /data/assets/rules_art/local or /data/assets/artwork/user. The dashboard will show matching asset_path files automatically after refresh."));
  rootEl.append(panel, notes, artwork);
}

function renderArtworkManager() {
  const panel = card("Artwork Manager", "Developer status for local artwork slots. User-facing files live beside game.db under DATA_DIR/assets; application-page artwork uses DATA_DIR/assets/Application Artwork.");
  const search = input("search", "modern-artwork-manager-search", "Filter artwork slots by title, page, category, path, source PDF, or summary.");
  search.placeholder = "Search artwork slots...";
  const status = select("modern-artwork-manager-status", "Filter by whether the configured asset file exists in DATA_DIR/assets or bundled fallback assets.", [
    ["", "All slots"],
    ["missing", "Missing files"],
    ["present", "Present files"],
    ["app_assets", "Application artwork"],
  ]);
  const summary = el("div", "modern-status-grid");
  const results = el("div", "modern-list");
  const draw = () => {
    const needle = search.value.trim().toLowerCase();
    const chosen = status.value;
    const entries = modernState.artwork.filter((entry) => {
      const text = [
        entry.id,
        entry.title,
        entry.category,
        entry.asset_path,
        entry.source_pdf,
        entry.summary,
        ...(entry.dashboard_pages || []),
        ...(entry.reference_ids || []),
        ...(entry.table_keys || []),
      ].join(" ").toLowerCase();
      const matchesNeedle = !needle || text.includes(needle);
      const exists = entry.asset_exists !== false;
      const matchesStatus =
        !chosen ||
        (chosen === "missing" && !exists) ||
        (chosen === "present" && exists) ||
        (chosen === "app_assets" && entry.category === "app_assets");
      return matchesNeedle && matchesStatus;
    });
    const appSlots = modernState.artwork.filter((entry) => entry.category === "app_assets");
    const missing = modernState.artwork.filter((entry) => entry.asset_exists === false);
    summary.replaceChildren(
      modernStatusRow("Application Artwork", `${appSlots.length} slot(s)`, "Dashboard and management-screen artwork slots under DATA_DIR/assets/Application Artwork."),
      modernStatusRow("Missing files", `${missing.length} slot(s)`, "Missing means the configured asset path is not present in DATA_DIR/assets or bundled fallback assets."),
      modernStatusRow("Visible now", `${modernState.artwork.length - missing.length} slot(s)`, "Present files are available through the /assets route, preferring DATA_DIR/assets first."),
    );
    results.replaceChildren();
    for (const entry of entries) {
      const exists = entry.asset_exists !== false;
      const row = el("div", "modern-list-row");
      row.title = entry.hover || entry.summary || "Artwork slot.";
      const body = el("div", "modern-stack");
      const pages = (entry.dashboard_pages || []).join(", ") || "No dashboard page";
      body.appendChild(el("strong", "", entry.title || entry.id));
      body.appendChild(el("span", "muted", `${entry.category || "uncategorized"} · ${pages} · ${exists ? `present (${entry.asset_source || "asset"})` : "missing"}`));
      body.appendChild(el("span", "muted", `DATA_DIR/assets/${entry.asset_path || ""}`));
      if (entry.summary) body.appendChild(el("span", "muted", entry.summary));
      const rowActions = actions();
      if (exists) rowActions.appendChild(link("View", artAssetUrl(entry), `Open ${entry.title || entry.id} through the /assets route.`, "link-button secondary"));
      rowActions.appendChild(link("Rules Ref", ruleReferenceHref((entry.reference_ids || [])[0], entry.title || entry.id), "Open the first linked Rules Reference entry for this artwork slot.", "link-button secondary"));
      row.append(body, rowActions);
      results.appendChild(row);
    }
    if (!entries.length) results.appendChild(el("p", "modern-home-status in-progress", "No artwork slots match the current filter."));
  };
  search.addEventListener("input", draw);
  status.addEventListener("change", draw);
  const row = actions();
  row.append(
    link("Artwork Rules Reference", ruleReferenceHref("artwork_manager", "artwork manager"), "Open the Artwork Manager reference entry.", "link-button secondary"),
    link("Application Artwork Table", "/modern/tables?search=application_artwork_slots_table", "Open the table that lists application artwork slots.", "link-button secondary"),
    link("Artwork Registry Table", "/modern/tables?search=artwork_registry_table", "Open the full artwork registry table.", "link-button secondary")
  );
  panel.append(field("Search", search), field("Status", status), row, summary, results);
  draw();
  return panel;
}

function renderGuides() {
  const panel = card("Game Guides", "Standalone guide links and future player-facing guide list.");
  const row = actions();
  row.append(
    link("TAG Section Guide", "/docs/Checking/TAG_SECTION_GUIDE.html", "Open the TAG workflow guide."),
    link("TAG Generated Test Checklist", "/docs/Checking/TAG_SECTION_GUIDE.html#manual-test-generated-tag-adventures", "Open the manual test checklist for generated TAG adventures."),
    link("Checking Docs", "/docs/Checking/", "Open the Checking docs folder where the server can list files if enabled.")
  );
  panel.appendChild(row);
  const planned = el("ul", "modern-check-list");
  ["Starter guide", "Choosing starting characters guide", "Before adventure checklist", "During adventure checklist", "After adventure closeout guide", "TAG settlement workflow"].forEach((item) => planned.appendChild(el("li", "", item)));
  panel.appendChild(planned);
  rootEl.appendChild(panel);
}

async function renderDeveloper() {
  await loadArtwork();
  const gate = card("Developer Unlock", "Enter password 7979 to show developer tools.");
  const pw = input("password", "modern-dev-pw", "Developer password. Default is 7979.");
  const tools = el("div", "modern-dev-tools hidden");
  const artworkMount = el("div", "modern-dev-artwork-manager hidden");
  const row = actions();
  row.append(
    link("Adventure PDF Import", "/modern/developer", "Placeholder for future PDF adventure module import."),
    link("Adventure Module Editor", "/modern/developer", "Placeholder for future adventure module editor."),
    link("Adventure Module Creator", "/modern/developer", "Placeholder for future adventure-from-scratch creator."),
    link("Map Elements Editor", "/static/tile-editor.html", "Open the existing map element editor as its own page."),
    link("Icon Editor", "/static/icon-editor.html", "Open the existing icon editor as its own page."),
    button("Artwork Manager", "Show or hide the artwork slot manager for DATA_DIR/assets paths, missing files, and linked Rules Reference entries.", async () => {
      if (!artworkMount.childElementCount) artworkMount.appendChild(renderArtworkManager());
      artworkMount.classList.toggle("hidden");
    })
  );
  tools.appendChild(row);
  tools.appendChild(artworkMount);
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
  if (helpEl) {
    helpEl.replaceChildren(
      helpLink(
        "?",
        ruleReferenceHref(PAGE_HELP_REFS[page], PAGE_HELP_QUERIES[page] || page),
        PAGE_HELP_REFS[page]
          ? `Open the exact Rules Reference entry for ${meta[0]}.`
          : `Open Rules Reference context for ${meta[0]}. This explains related rules, app-only boundaries, artwork slots, and implementation notes.`
      )
    );
  }
  rootEl.replaceChildren();
  if (pageCompanionEl) pageCompanionEl.replaceChildren();
  if (pageArtworkEl) pageArtworkEl.replaceChildren();
  if (pageHeadEl) pageHeadEl.classList.remove("has-artwork");
  if (navArtworkEl) navArtworkEl.replaceChildren();
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
    "adventure-management": renderAdventureManagement,
    "go-adventure": renderGoAdventure,
    "rules-reference": renderRulesReference,
    tables: renderTables,
    library: renderLibrary,
    guides: renderGuides,
    developer: renderDeveloper,
  }[page]();
  Promise.resolve(result)
    .then(() => renderShellArtwork(page))
    .then(() => renderPageArtwork(page))
    .then((panel) => {
      if (panel && currentPage() === page) rootEl.appendChild(panel);
      if (page === "home" && currentPage() === page) rootEl.appendChild(renderGuidanceLog());
    })
    .catch(handleError);
}

loadCore()
  .then(() => {
    renderPage();
    setStatus("Ready");
  })
  .catch(handleError);
