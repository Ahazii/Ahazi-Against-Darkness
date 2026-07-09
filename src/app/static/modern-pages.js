const modernState = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  adventurePackages: [],
  sessions: [],
  campaign: null,
  rulesProfiles: [],
  equipmentRows: [],
  rulesReference: [],
  artwork: [],
  tables: {},
  preferences: {},
  supplements: { supplements: [], legacy_fields: [] },
  states: { states: [], legacy_fields: [] },
  terrain: { terrain: [], legacy_fields: [] },
  appVersion: null,
};

const MODERN_PREFS_KEY = "ahazi-modern-dashboard-prefs";
const ADVENTURE_MANAGEMENT_TAB_KEY = "ahazi-modern-adventure-management-tab";

const TAG_ADVENTURE_FIXED_RESULTS = {
  rumor: [
    ["1", "Rumor 1 - Bofuto's trouble"],
    ["2", "Rumor 2 - Medusa in the Hunter's Cabin"],
    ["3", "Rumor 3 - Paladin sword red herring"],
    ["4", "Rumor 4 - Mutant Fish Under the Bridge"],
    ["5", "Rumor 5 - Dragon in Disguise"],
    ["6", "Rumor 6 - Leprechauns at Blackbird Hill"],
    ["7", "Rumor 7 - Tamas Zeya temple handoff"],
    ["8", "Rumor 8 - Shaura and the gargoyles"],
    ["9", "Rumor 9 - Daroc's cat"],
    ["10", "Rumor 10 - White gargoyles"],
    ["11", "Rumor 11 - Deoldyn archery training"],
    ["12", "Rumor 12 - Shinta and Agaratha"],
  ],
  treasure_map: [
    ["1", "Map 1 - Underground caves"],
    ["2", "Map 2 - Underground temple"],
    ["3", "Map 3 - Humanoid camp"],
    ["4", "Map 4 - Underground structure"],
    ["5", "Map 5 - Boss-only structure"],
    ["6", "Map 6 - Lich chamber"],
  ],
  thematic_dungeon: [
    ["1", "Theme 1 - Cavern"],
    ["2", "Theme 2 - Monster lair"],
    ["3", "Theme 3 - Dragon's Lair"],
    ["4", "Theme 4 - Undead crypt"],
    ["5", "Theme 5 - Sewers"],
    ["6", "Theme 6 - Bandit Hideout"],
  ],
  guild_job: [
    ["1", "Guild Job 1 - Minor quest table"],
    ["2", "Guild Job 2 - Minor quest table"],
    ["3", "Guild Job 3 - Minor quest table"],
    ["4", "Guild Job 4 - Rumor table"],
    ["5", "Guild Job 5 - Rumor table"],
    ["6", "Guild Job 6 - Thematic Dungeon table"],
  ],
};

const TAG_ADVENTURE_LEAD_TYPES = [
  ["rumor", "Rumor Scene"],
  ["treasure_map", "Treasure Map destination"],
  ["thematic_dungeon", "Thematic Dungeon"],
  ["guild_job", "Guild Job"],
];

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
  guides: ["Game Guides", "Open player-facing workflow guides, test checklists, and future quick-start material for using the app during setup, play, closeout, and Adventures Guild procedures."],
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
  characters: "",
  troupes: "",
  guild: "tag_guild_closeout_guidance",
  parties: "",
  equipment: "equipment_shop",
  banking: "tag_settlement_campaign",
  settlement: "tag_settlement_campaign",
  campaign: "",
  "adventure-management": "",
  "go-adventure": "",
  "rules-reference": "",
  tables: "",
  library: "",
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

const versionEl = document.createElement("div");
versionEl.className = "status modern-version";
versionEl.textContent = "v...";
document.querySelector(".topbar-actions")?.insertBefore(versionEl, statusEl);

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
  btn.dataset.defaultLabel = label;
  btn.addEventListener("click", () => Promise.resolve().then(() => onClick(btn)).catch(handleError));
  return btn;
}

function setButtonWorking(btn, working, label = "") {
  if (!btn) return;
  btn.disabled = Boolean(working);
  btn.classList.toggle("is-working", Boolean(working));
  btn.setAttribute("aria-busy", working ? "true" : "false");
  if (working && label) btn.textContent = label;
  if (!working) btn.textContent = btn.dataset.defaultLabel || btn.textContent;
}

async function runWithButtonProgress(btn, busyLabel, work) {
  setButtonWorking(btn, true, busyLabel);
  setStatus(busyLabel);
  try {
    return await work();
  } finally {
    setButtonWorking(btn, false);
  }
}

function scrollPanelIntoView(panel) {
  if (!panel || panel.classList.contains("hidden")) return;
  window.requestAnimationFrame(() => {
    panel.scrollIntoView({
      block: "start",
      behavior: window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ? "auto" : "smooth",
    });
  });
}

async function toggleRevealedPanel(mount, buildPanel, openedStatus = "") {
  if (!mount.childElementCount) mount.appendChild(await buildPanel());
  const willOpen = mount.classList.contains("hidden");
  mount.classList.toggle("hidden");
  if (willOpen) {
    if (openedStatus) setStatus(openedStatus);
    scrollPanelIntoView(mount);
  }
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

function collapsibleSettingsPanel(panel, title, body = "") {
  const details = document.createElement("details");
  details.className = panel.className || "modern-card";
  details.classList.add("modern-collapsible", "modern-settings-panel");
  details.title = panel.title || `Open ${title}.`;
  const summary = document.createElement("summary");
  summary.appendChild(el("strong", "", title));
  if (body) summary.appendChild(el("span", "muted", body));
  details.appendChild(summary);
  for (const child of [...panel.childNodes]) {
    if (child.matches?.("h3") || (child.matches?.("p.muted") && child.textContent === body)) continue;
    details.appendChild(child);
  }
  return details;
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

function developerReferenceHref(entryId, fallbackQuery = "") {
  const params = new URLSearchParams({ audience: "developer" });
  if (entryId) params.set("entry", entryId);
  else params.set("help", fallbackQuery || "developer reference");
  return `/modern/rules-reference?${params.toString()}`;
}

function developerTablesHref(tableKey = "") {
  const params = new URLSearchParams({ audience: "developer" });
  if (tableKey) params.set("search", tableKey);
  return `/modern/tables?${params.toString()}`;
}

function modernReferenceAudience() {
  return new URLSearchParams(window.location.search).get("audience") === "developer" ? "developer" : "player";
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

function searchTerms(needle) {
  return String(needle || "")
    .trim()
    .split(/\s+/)
    .filter((term) => term.length >= 2)
    .slice(0, 8);
}

function normalizedSearchNeedle(value) {
  return String(value || "")
    .normalize("NFKC")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .trim()
    .replace(/\s+/g, " ")
    .toLowerCase();
}

function modernTextMatchesNeedle(text, needle) {
  const value = normalizedSearchNeedle(text);
  const query = normalizedSearchNeedle(needle);
  if (!query) return true;
  if (value.includes(query)) return true;
  const terms = searchTerms(query);
  return Boolean(terms.length) && terms.every((term) => value.includes(term));
}

function appendHighlightedText(node, text, needle) {
  const value = String(text ?? "");
  const terms = searchTerms(needle);
  if (!value || !terms.length) {
    node.appendChild(document.createTextNode(value));
    return node;
  }
  const escaped = terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  let lastIndex = 0;
  for (const match of value.matchAll(pattern)) {
    if (match.index > lastIndex) node.appendChild(document.createTextNode(value.slice(lastIndex, match.index)));
    node.appendChild(el("mark", "modern-search-hit", match[0]));
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < value.length) node.appendChild(document.createTextNode(value.slice(lastIndex)));
  return node;
}

function highlightedEl(tag, className, text, needle) {
  return appendHighlightedText(el(tag, className), text, needle);
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
  const bodyNode = Array.isArray(body) ? el("ul", "modern-inline-list") : el("span", "muted", body);
  if (Array.isArray(body)) {
    for (const item of body.filter(Boolean)) bodyNode.appendChild(el("li", "", item));
  }
  row.append(el("strong", "", title), bodyNode);
  return row;
}

function modernStatusRowHighlighted(title, body, hint = "", needle = "") {
  const row = el("div", "modern-row");
  if (hint) row.title = hint;
  row.append(highlightedEl("strong", "", title, needle), highlightedEl("span", "muted", body, needle));
  return row;
}

function modernInfoPanel(title, subtitle, fields, hint = "") {
  const panel = document.createElement("details");
  panel.className = "modern-row modern-info-panel";
  if (hint) panel.title = hint;
  const summary = document.createElement("summary");
  summary.append(el("strong", "", title), el("span", "muted", ` · ${subtitle}`));
  const grid = el("dl", "modern-info-grid");
  for (const fieldDef of fields.filter(Boolean)) {
    const term = el("dt", "", fieldDef.label || "");
    const value = Array.isArray(fieldDef.value) ? fieldDef.value.filter(Boolean).join("\n") : String(fieldDef.value ?? "");
    const desc = el("dd", "", value || "None");
    if (fieldDef.hint) desc.title = fieldDef.hint;
    grid.append(term, desc);
  }
  panel.append(summary, grid);
  return panel;
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
    ["Generated lead", latestLead || "No generated Adventures Guild lead recorded.", latestLead ? "ok" : "warn", "Confirm the latest generated module came from the intended Rumor, Treasure Map, Thematic Dungeon, or Guild Job."],
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
    button("Mark Signoff Reviewed", "Record a generated Adventures Guild adventure signoff review. This logs open closeout and XP counts; it only completes broad review guidance when no open closeout or XP markers remain.", () => recordTagSignoffReview(note.value), ""),
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
        "Finish an adventure, create an Adventures Guild lead, use Guild jobs, travel, or perform settlement/banking actions and the latest guidance will appear here.",
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
  const panel = card(context, "Checklist for generated Adventures Guild adventures: record branch/route choices, rewards, XP, Guild obligations, banking/storage consequences, and closeout resolution.");
  const route = (campaign.tag_adventure_routes || []).slice(-1)[0];
  const log = (campaign.tag_downtime_log || []).slice(-1)[0];
  const openCloseout = (campaign.tag_closeout_tasks || []).filter((task) => !task.resolved).length;
  const pendingXp = (campaign.tag_xp_markers || []).filter((marker) => !marker.applied).length;
  panel.append(
    modernStatusRow("Generated lead", (campaign.tag_generated_adventure_ids || []).slice(-1)[0] || "No generated Adventures Guild lead yet.", "Create Rumor, Treasure Map, Thematic Dungeon, or Guild Job modules from Go Adventure or Guild Management."),
    modernStatusRow("Latest route marker", route ? route.result_text : "No route marker recorded.", "Adventures Guild Actions during exploration records parley, Clue gates, skipped scenes, final route, solo restrictions, and generated-module route rewrites."),
    modernStatusRow("Pending XP", `${pendingXp} marker(s)`, "Resolve pending TAG XP markers from Adventures Guild Actions or closeout before starting the next adventure."),
    modernStatusRow("Closeout prompts", `${openCloseout} open prompt(s)`, "Open closeout prompts must be resolved by the relevant Guild, Banking, storage, XP, or manual signoff workflow."),
    modernStatusRow("Latest TAG log", log ? `${modernTitleFromKey(log.action)} · ${log.result_text}` : "No TAG log entries yet.", "Recent TAG automation/log action. Open the TAG guide when checking generated-adventure signoff against the PDF.")
  );
  const note = input("text", `modern-tag-panel-signoff-note-${context.toLowerCase().replace(/\W+/g, "-")}`, "Optional generated-adventure signoff note. This is saved to the TAG log and Campaign Chronicle.", "");
  const row = actions();
  row.append(
    field("Signoff note", note),
    button("Mark Reviewed", "Record that the latest generated Adventures Guild adventure signoff was reviewed. This does not resolve printed-rule decisions or open closeout tasks by itself.", () => recordTagSignoffReview(note.value), ""),
    link("Go Adventure", "/modern/go-adventure", "Open Go Adventure to create Adventures Guild leads, select generated modules, and review closeout gates.", "link-button secondary"),
    link("Guidance", "/modern/home", "Return to the Dashboard Guidance / Log for active task completion, deferral, or dismissal.", "link-button secondary"),
    link("TAG Guide", "/docs/Checking/TAG_SECTION_GUIDE.html", "Open generated-adventure manual checking and signoff guidance.", "link-button secondary")
  );
  panel.appendChild(row);
  return panel;
}

function renderTagActionLogExplorer() {
  const panel = card("Adventures Guild Action Log", "Search and filter TAG route, XP, finance, Guild, branch, generated-module, and signoff events. Use this when checking what a generated lead changed before closeout.");
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
    const row = document.createElement("details");
    row.className = "modern-row modern-collapsible";
    row.title = `${adventure.notes || "Generated Adventures Guild module."} ${adventure.tag_pdf_pages ? `Source ${adventure.tag_pdf_pages}.` : ""}`;
    const rowSummary = document.createElement("summary");
    rowSummary.title = "Show or hide this generated Adventures Guild lead audit row.";
    rowSummary.append(
      el("strong", "", adventure.name || adventure.id),
      el("span", "muted", `${modernTitleFromKey(adventure.tag_lead_type || "tag lead")} · ${adventure.tag_scene || adventure.tag_lead_detail || "generated module"}${adventure.tag_pdf_pages ? ` · ${adventure.tag_pdf_pages}` : ""}`)
    );
    row.appendChild(rowSummary);
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
    ["Signoff", "Route, reward, XP, Guild/finance, and closeout review", "Use the TAG prompt buttons during exploration, then review Adventures Guild Action Log before starting another lead."],
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
    ["Complication", "Resolve Clue costs, red herrings, ambushes, peaceful/hostile branches, and profile-specific rolls.", "Use Adventures Guild Actions so the Campaign log shows why the route changed."],
    ["Finale", "Confirm final foe/procedure, reward, item, bounty, capture-alive route, and any scene restriction.", "The generated room is a play aid; the printed result remains the authority."],
    ["Closeout", "Review pending XP, Guild obligations, banking/storage, guidance tasks, and the Adventures Guild Action Log.", "Do this before creating the next lead so unresolved state is visible."],
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
    ["Current room treasure", "If exploration says hidden treasure was found, use Claim Treasure for that room. That does not replace the Map Leads To destination procedure.", "Claim Treasure handles the local room hoard; Adventures Guild Actions record map procedure and closeout decisions."],
    ["Play focus", "Follow-map result -> destination procedure -> deferred/reward treasure -> closeout", "Treasure Map leads are about proving the map, choosing risk, and making reward accounting visible."],
    ["Signoff", "Route, procedure rolls, treasure transfer, XP, Guild/finance, and storage review", "Use Adventures Guild Actions during exploration, then review Adventures Guild Action Log and banking/storage before starting another lead."],
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
    ["Destination procedure", "Resolve destination-specific room count, report/stealth choice, deferred treasure, boss-only conversion, or death-magic setup.", "Use Adventures Guild Actions so the procedure is recorded before final reward handling."],
    ["Treasure", "Move deferred treasure, idol value, report reward, lich treasure, magic items, or Boss treasure into the correct party/Guild/bank/storage workflow.", "Treasure Maps often need accounting after the fight, not just a combat victory."],
    ["Closeout", "Review pending XP, Guild share, banking/storage, guidance tasks, and the Adventures Guild Action Log before creating another map lead.", "This avoids losing map bonuses, deferred treasure, or unpaid Guild obligations."],
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
    ["Signoff", "Replacement rolls, Clue spends, route markers, reward, XP, Guild/finance, and storage review", "Use Adventures Guild Actions during exploration, then review Adventures Guild Action Log before starting another lead."],
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
    ["Procedure rolls", "Resolve undead replacement, cave-ins, boulder throw, dragon reveal, prisoner table, maze lost/event checks, stolen goods, or capture-alive choice.", "Use Adventures Guild Actions so the changed dungeon logic stays visible in the campaign log."],
    ["Finale", "Confirm final-room size/route, final foe, special restrictions, reward, treasure conversion, and XP.", "Generated encounters are proxies where needed; the printed theme procedure remains the authority."],
    ["Closeout", "Review pending XP, Guild share, banking/storage, guidance tasks, route markers, and the Adventures Guild Action Log before creating another lead.", "Thematic dungeons tend to leave more state behind than ordinary random dungeons."],
  ];
  for (const [title, body, hint] of checks) {
    panel.appendChild(modernStatusRow(title, body, hint));
  }
  const panelActions = actions();
  panelActions.append(
    link("Theme Rules", ruleReferenceHref("tag_thematic_dungeon_playthrough_audit", "TAG thematic dungeon playthrough audit"), "Open the Rules Reference entry for Thematic Dungeon signoff guidance.", "link-button secondary"),
    link("Adventures Guild Actions", "/modern/go-adventure", "Return to Go Adventure to review generated leads, closeout, signoff, and Adventures Guild Action Log state.", "link-button secondary")
  );
  panel.appendChild(panelActions);
  return panel;
}

function tagGuildJobNumber(adventure) {
  const text = `${adventure.tag_lead_detail || ""} ${adventure.name || ""} ${adventure.id || ""}`;
  const explicit = text.match(/guild job\s+(\d{1,2})/i);
  if (explicit) return Number(explicit[1]);
  const tagId = String(adventure.id || "");
  const suffix = tagId.match(/tag-guild-job-(\d{1,2})/i);
  return suffix ? Number(suffix[1]) : 0;
}

function tagGuildJobGuidance(adventure) {
  const text = `${adventure.tag_lead_detail || ""} ${adventure.tag_scene || ""} ${adventure.name || ""}`.toLowerCase();
  if (text.includes("clean up my castle")) return "Clean Up My Castle: track ten-room completion, no exit/re-entry, foe-count pay, and the 1-Clue portrait cache before Guild payout.";
  if (text.includes("gorungar")) return "Gorungar: confirm archer count/proxy, poison/surprise notes, killed-or-captured outcome, and armband/coin-bag reward.";
  if (text.includes("griffin")) return "Griffin Omelets: track mountain checks, nest search, egg count, carrying limits, egg break checks, and intact/broken egg payment.";
  if (text.includes("portrait")) return "A Portrait in Red: track outbound checks, persuasion/ejected characters, return checks, painting snatch, artist survival, and commission payout.";
  if (text.includes("sewer")) return "Sewers Search: use sewer vermin/minion procedures, spend 3 Clues to reveal the thief, capture-alive bonus, and post-adventure disease checks.";
  if (text.includes("monoceros")) return "Monoceros Hunt: track hunting rolls, 3-Clue shortcut risk, capture-alive condition, forbidden damage types, hide checks, and reward eligibility.";
  if (text.includes("rumor")) return "Guild Job routed to Rumor: review both the Guild Job commission and the nested Rumor route/reward/XP closeout.";
  if (text.includes("thematic dungeon")) return "Guild Job routed to Thematic Dungeon: review both the Guild Job commission and the nested theme procedure/reward closeout.";
  return "Check generated module metadata for the Guild Job commission, nested result, proof condition, payment, XP, Guild coffers/share, and closeout state.";
}

function tagGuildJobAuditRows(adventure) {
  const number = tagGuildJobNumber(adventure);
  return [
    ["Guild Job result", number ? `Guild Job ${number}` : "Generated Guild Job", "Confirm this is the intended Guild Job table result before Start Adventure."],
    ["Job procedure", tagGuildJobGuidance(adventure), "Procedure metadata comes from the generated manifest. Exact values, rolls, reward amounts, and consequences remain with the PDF/player signoff."],
    ["Play focus", "Commission -> proof/procedure -> payment/reward -> Guild closeout", "Guild Jobs are official work: proving the job condition matters as much as clearing the room."],
    ["Signoff", "Job proof, capture-alive route, Clue spends, payment, XP, Guild coffers/share, banking/storage, and closeout review", "Use Adventures Guild Actions during play, then review the Adventures Guild Action Log before creating another job."],
  ];
}

function renderGuildJobLeadAuditPanel(adventureSelect = null) {
  const panel = card("TAG Guild Job Leads", "Audit installed Guild Job modules before play. Each row helps confirm the commission, nested result, proof condition, payment, XP, Guild obligations, and closeout signoff.");
  const jobs = tagGeneratedAdventures().filter((adventure) => String(adventure.tag_lead_type || "").toLowerCase() === "guild_job");
  if (!jobs.length) {
    panel.appendChild(el("p", "muted", "No Guild Job modules are installed yet. Create a Guild Job lead in Go Adventure or Guild Management, then use this panel to review it before Start Adventure."));
    const emptyActions = actions();
    emptyActions.append(
      link("Job Rules", ruleReferenceHref("tag_guild_job_playthrough_audit", "TAG guild job playthrough audit"), "Open the Rules Reference entry for the app-owned Guild Job playthrough audit workflow.", "link-button secondary"),
      link("Job Table", "/modern/tables?help=tag_guild_job_playthrough_audit_table", "Open the modern Tables entry for Guild Job audit surfaces and PDF boundaries.", "link-button secondary")
    );
    panel.appendChild(emptyActions);
    return panel;
  }
  for (const adventure of jobs.slice(0, 12)) {
    const row = document.createElement("details");
    row.className = "modern-row modern-collapsible";
    row.title = "Guild Job audit row: confirms which job commission this is and which proof, payment, XP, Guild, banking, and storage checks should be reviewed.";
    const rowSummary = document.createElement("summary");
    rowSummary.title = "Show or hide this Guild Job audit row.";
    rowSummary.append(
      el("strong", "", adventure.name || adventure.id),
      el("span", "muted", `${adventure.tag_lead_detail || "Guild Job"}${adventure.tag_pdf_pages ? ` · ${adventure.tag_pdf_pages}` : ""}`)
    );
    row.appendChild(rowSummary);
    for (const [title, body, hint] of tagGuildJobAuditRows(adventure)) {
      row.appendChild(modernStatusRow(title, body, hint));
    }
    const rowActions = actions();
    rowActions.append(
      button("Select Job", "Switch Start New Adventure to Imported Adventure Module and select this Guild Job lead.", async () => {
        const type = document.getElementById("modern-adventure-type");
        if (type) type.value = "imported";
        if (adventureSelect) {
          adventureSelect.replaceChildren(...optionRows(adventureOptions("imported")));
          adventureSelect.value = adventure.id;
        }
        writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: adventure.id || "" });
        setStatus(`Selected Guild Job lead ${adventure.name || adventure.id}. Review setup and closeout gates before starting.`);
      }),
      link("Rules", ruleReferenceHref("tag_guild_job_playthrough_audit", "TAG guild job playthrough audit"), "Open the Rules Reference entry for Guild Job playthrough audit guidance.", "link-button secondary"),
      link("Table", "/modern/tables?help=tag_guild_job_playthrough_audit_table", "Open the modern Tables row documenting this Guild Job audit surface.", "link-button secondary")
    );
    row.appendChild(rowActions);
    panel.appendChild(row);
  }
  return panel;
}

function renderGuildJobSignoffChecklist() {
  const panel = card("Guild Job Signoff Checklist", "Use this app-owned checklist after a TAG Guild Job. It focuses on proof, job-specific payment, Guild obligations, and closeout.");
  const checks = [
    ["Commission", "Confirm the Guild Job table result and any nested minor quest, Rumor, or Thematic Dungeon result.", "Guild Jobs can hand off to another generated family; keep the official job wrapper visible."],
    ["Proof and procedure", "Resolve foe-count pay, capture-alive outcome, egg/portrait/sewer/monoceros procedures, Clue spends, or nested route choices.", "Use Adventures Guild Actions so the campaign log explains why payment or reward changed."],
    ["Payment and rewards", "Check party pay, bonus/forfeit conditions, item rewards, XP markers, Guild share, bank deposits, and storage consequences.", "Jobs often fail or change payout based on proof, survival, capture, or carried goods."],
    ["Closeout", "Review Guild upkeep, availability reroll reset, unresolved guidance, and the Adventures Guild Action Log before creating another job.", "Guild Jobs are closeout-sensitive because Guild benefits and coffers can drift between sessions."],
  ];
  for (const [title, body, hint] of checks) {
    panel.appendChild(modernStatusRow(title, body, hint));
  }
  const panelActions = actions();
  panelActions.append(
    link("Job Rules", ruleReferenceHref("tag_guild_job_playthrough_audit", "TAG guild job playthrough audit"), "Open the Rules Reference entry for Guild Job signoff guidance.", "link-button secondary"),
    link("Guild", "/modern/guild", "Open Guild Management to review coffers, benefits, Guild jobs, and closeout prompts.", "link-button secondary")
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

function sessionSupplementSummary(session) {
  const ids = Array.isArray(session?.active_supplement_ids) ? session.active_supplement_ids : [];
  if (!ids.length) return "legacy session: no supplement snapshot";
  const known = new Map((modernState.supplements?.supplements || []).map((supplement) => [supplement.id, supplement.title || supplement.id]));
  return ids.map((id) => known.get(id) || id).join(", ");
}

function supplementTitlesForIds(ids) {
  const known = new Map((modernState.supplements?.supplements || []).map((supplement) => [supplement.id, supplement.title || supplement.id]));
  return (ids || []).map((id) => known.get(id) || id).join(", ");
}

function supplementConflictIds(ids) {
  const selected = new Set(ids || []);
  const conflicts = new Set();
  for (const supplement of modernState.supplements?.supplements || []) {
    if (!selected.has(supplement.id)) continue;
    for (const conflictId of supplement.conflicts || []) conflicts.add(conflictId);
  }
  return conflicts;
}

function supplementRegistryMap() {
  return new Map((modernState.supplements?.supplements || []).map((supplement) => [supplement.id, supplement]));
}

function activeDefaultSupplementIds() {
  const selected = new Set(modernState.preferences?.enabled_supplement_ids || []);
  for (const supplement of modernState.supplements?.supplements || []) {
    if (supplement.locked) selected.add(supplement.id);
  }
  return selected;
}

function supplementFilterOptions() {
  return [
    ["", "All supplement contexts"],
    ["__active_defaults", "Enabled defaults only"],
    ...(modernState.supplements?.supplements || []).map((supplement) => [supplement.id, supplement.title || supplement.id]),
  ];
}

function inferredSupplementIdsForText(text, { fallbackCore = true } = {}) {
  const haystack = String(text || "").toLowerCase();
  const known = supplementRegistryMap();
  const ids = [];
  const add = (id) => {
    if (known.has(id) && !ids.includes(id)) ids.push(id);
  };
  if (/\btag\b|adventurers'? guild|tales from the adventurers/.test(haystack)) add("tag");
  if (/abyss|four against the abyss/.test(haystack)) add("four-against-the-abyss");
  if (/forsaken depths|\bfd_|fd |fd_|four against the forsaken/.test(haystack)) add("forsaken-depths");
  if (/courtship|tcotfd|flower demons|blossoms|demesne|norindaal|soul cube/.test(haystack)) add("courtship");
  if (/imported adventure|adventure package|package\.json|pdf import|source pdf|module-local/.test(haystack)) add("imported-adventures");
  if (!ids.length && fallbackCore) add("expanded-edition-core");
  return ids;
}

function supplementTitlesForBadges(ids) {
  const known = supplementRegistryMap();
  return (ids || []).map((id) => known.get(id)?.title || id);
}

function renderSupplementBadges(ids, title = "Inferred supplement context for filtering. This is navigation metadata, not a rules outcome.") {
  const badges = el("div", "modern-supplement-badges");
  badges.title = title;
  for (const label of supplementTitlesForBadges(ids)) {
    badges.appendChild(el("span", "modern-supplement-badge", label));
  }
  return badges;
}

function supplementFilterMatches(ids, selectedValue) {
  if (!selectedValue) return true;
  const itemIds = new Set(ids || []);
  if (selectedValue === "__active_defaults") {
    const active = activeDefaultSupplementIds();
    return !itemIds.size || [...itemIds].some((id) => active.has(id));
  }
  return itemIds.has(selectedValue);
}

function suggestedLegacyProfileForSupplements(ids) {
  const enabled = new Set(ids || []);
  if (enabled.has("four-against-the-abyss")) return "abyss";
  if (enabled.has("forsaken-depths") && enabled.has("courtship")) return "forsaken_depths";
  if (enabled.has("forsaken-depths")) return "forsaken_depths_no_courtship";
  return "ee_random";
}

function legacyProfileLabel(profileId) {
  return modernState.rulesProfiles.find((profile) => profile.id === profileId)?.label || profileId;
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
  const [classes, characters, parties, adventures, adventurePackages, sessions, campaign, profiles, preferences, supplements, states, terrain, appVersion] = await Promise.all([
    api("/api/rules/classes"),
    api("/api/characters"),
    api("/api/parties"),
    api("/api/adventures"),
    api("/api/adventures/packages"),
    api("/api/sessions/summaries"),
    api("/api/campaign"),
    api("/api/rules/profiles"),
    api("/api/preferences"),
    api("/api/supplements"),
    api("/api/states"),
    api("/api/terrain"),
    api("/api/app/version"),
  ]);
  modernState.classes = classes;
  modernState.characters = characters;
  modernState.parties = parties;
  modernState.adventures = adventures;
  modernState.adventurePackages = adventurePackages.packages || [];
  modernState.sessions = sessions;
  modernState.campaign = campaign;
  modernState.rulesProfiles = profiles;
  modernState.preferences = preferences || {};
  modernState.supplements = supplements || { supplements: [], legacy_fields: [] };
  modernState.states = states || { states: [], legacy_fields: [] };
  modernState.terrain = terrain || { terrain: [], legacy_fields: [] };
  modernState.appVersion = appVersion || null;
  if (modernState.appVersion?.version) {
    versionEl.textContent = `v${modernState.appVersion.version}`;
    versionEl.title = modernState.appVersion.build
      ? `Ahazi Against Darkness ${modernState.appVersion.version}; build ${modernState.appVersion.build}.`
      : `Ahazi Against Darkness ${modernState.appVersion.version}.`;
  }
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
      ["Use case", "before, during, after play", "Good guides reduce log/action confusion during Adventures Guild procedures."],
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
    "Guild Job Lead installs a playable Guild Job adventure module; Guild spell handling remains in Adventures Guild Actions during exploration.",
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

function renderSupplementRegistryPanel() {
  const payload = modernState.supplements || {};
  const supplements = Array.isArray(payload.supplements) ? payload.supplements : [];
  const legacyFields = Array.isArray(payload.legacy_fields) ? payload.legacy_fields : [];
  const diagnostics = Array.isArray(payload.diagnostics) ? payload.diagnostics : [];
  const panel = card(
    "Supplement Library (read-only)",
    "A supplement is a book, adventure, rules expansion, tile pack, terrain pack, or imported PDF package. These records explain what each package can add before the app lets campaigns turn them on or off."
  );
  panel.classList.add("modern-registry-panel");
  panel.title = "Read-only supplement registry. Expanded Edition is locked on; existing ruleset controls below are legacy compatibility until activation is session-safe.";
  panel.appendChild(registryExplanation("Why this exists", [
    "Today the app still uses legacy ruleset profile fields for Go Adventure.",
    "The target model is a list of active supplements per campaign/session, such as Expanded Edition + Forsaken Depths + a reviewed imported adventure.",
    "Capabilities explain what a supplement can provide: foes, classes, states, maps, locations, terrain types, room tiles, rules, procedures, or exact local narrative text."
  ]));
  const summary = el("div", "modern-grid two");
  summary.append(
    modernStatusRow("Registry", `${supplements.length} supplement records`, "Read-only registry loaded from the backend supplement metadata."),
    modernStatusRow("Locked core", payload.locked_core_id || "expanded-edition-core", "The base Expanded Edition supplement is always active."),
    modernStatusRow("Manifest schema", payload.manifest_schema || "ROOT/data/supplements/schema/supplement_manifest.v1.json", "Schema and app validator used for packaged and local supplement manifests."),
    modernStatusRow("Packaged manifests", payload.packaged_manifest_root || "ROOT/data/supplements", "Built-in supplement manifests shipped with the app."),
    modernStatusRow("Local manifests", payload.local_manifest_root || "DATA_DIR/Supplements", "User-facing folder for future local supplement manifests beside game.db."),
    modernStatusRow("Mode", payload.read_only ? "Read-only" : "Editable", "This screen is intentionally not changing gameplay yet."),
    modernStatusRow("Legacy bridge", `${legacyFields.length} compatibility fields`, "Existing save/session fields remain valid during migration.")
  );
  panel.appendChild(summary);
  for (const supplement of supplements) {
    const row = el("details", "modern-row modern-registry-row");
    row.title = supplement.notes || "Supplement metadata record.";
    const state = supplement.locked ? "locked" : (supplement.enabled_by_default ? "default on" : "optional");
    row.appendChild(registrySummary(supplement.title || supplement.id, `${modernTitleFromKey(supplement.kind)} · ${modernTitleFromKey(supplement.status)} · ${state}`));
    const chips = el("div", "modern-chip-row");
    for (const capability of supplement.capabilities || []) {
      const chip = el("span", "modern-tag", modernTitleFromKey(capability));
      chip.title = `Capability supplied by ${supplement.title || supplement.id}: ${modernTitleFromKey(capability)}.`;
      chips.appendChild(chip);
    }
    row.appendChild(chips);
    row.append(
      modernStatusRow("Source", supplement.source?.source_pdf || supplement.source?.source_path || supplement.source?.type || "Current project data", "Source file or storage area represented by this supplement."),
      modernStatusRow("Manifest", supplement.manifest_path || supplement.registry_origin || "Built-in fallback", `Registry origin: ${modernTitleFromKey(supplement.registry_origin || "builtin_fallback")}.`),
      modernStatusRow("Dependencies", (supplement.dependencies || []).join(", ") || "None", "Supplement dependencies that must be active before this supplement can be enabled."),
      modernStatusRow("Legacy mappings", Object.keys(supplement.legacy_mappings || {}).join(", ") || "None", "Current fields that still stand in for future supplement activation."),
      modernStatusRow("Example", supplementExample(supplement), "Plain-language example of what this supplement record means."),
      el("p", "muted", supplement.notes || "")
    );
    panel.appendChild(row);
  }
  if (diagnostics.length) {
    const diagnosticsBox = el("details", "modern-row modern-registry-row");
    diagnosticsBox.open = true;
    diagnosticsBox.title = "Supplement manifest load warnings. Fix the local manifest file, then refresh Settings.";
    diagnosticsBox.appendChild(registrySummary("Manifest diagnostics", `${diagnostics.length} warning(s)`));
    for (const diagnostic of diagnostics) {
      diagnosticsBox.appendChild(modernStatusRow(diagnostic.severity || "warning", diagnostic.path || "unknown path", diagnostic.message || "No detail."));
    }
    panel.appendChild(diagnosticsBox);
  }
  if (legacyFields.length) {
    const legacy = el("details", "modern-row modern-registry-row");
    legacy.title = "Current compatibility fields that will eventually be replaced by campaign/session supplement ids.";
    legacy.appendChild(registrySummary("Legacy compatibility fields", "Current fields kept while supplement activation is introduced"));
    for (const fieldInfo of legacyFields) {
      legacy.appendChild(modernStatusRow(fieldInfo.field, `${fieldInfo.status} -> ${fieldInfo.replacement}`, fieldInfo.notes || ""));
    }
    panel.appendChild(legacy);
  }
  return panel;
}

function registryExplanation(title, lines) {
  const box = el("div", "modern-registry-explainer");
  box.appendChild(el("strong", "", title));
  const list = el("ul", "modern-warning-list");
  for (const line of lines) list.appendChild(el("li", "", line));
  box.appendChild(list);
  return box;
}

function registrySummary(title, meta) {
  const summary = document.createElement("summary");
  summary.append(el("strong", "", title), el("span", "muted", meta));
  return summary;
}

function registrySummaryWithHighlight(title, meta, needle = "") {
  const summary = document.createElement("summary");
  summary.append(highlightedEl("strong", "", title, needle), highlightedEl("span", "muted", meta, needle));
  return summary;
}

function renderRegistryDiagnostics(title, diagnostics, hint) {
  if (!Array.isArray(diagnostics) || !diagnostics.length) return null;
  const box = el("details", "modern-row modern-registry-row");
  box.open = true;
  box.title = hint || "Registry metadata diagnostics.";
  box.appendChild(registrySummary(title, `${diagnostics.length} warning(s)`));
  for (const diagnostic of diagnostics) {
    box.appendChild(modernStatusRow(diagnostic.severity || "warning", diagnostic.path || "unknown path", diagnostic.message || "No detail."));
  }
  return box;
}

function supplementExample(supplement) {
  const id = supplement?.id || "";
  if (id === "expanded-edition-core") return "Expanded Edition is always active and provides the baseline rules, classes, monsters, tables, states, room tiles, and rules reference.";
  if (id === "forsaken-depths") return "Forsaken Depths can add its own room tiles, river/citadel/ruins terrain concepts, foes, classes, tables, states, and generation profiles.";
  if (id === "imported-adventures") return "An imported PDF package can hold exact local narrative text, map pins, locations, foes, items, candidate rules, and candidate states for review.";
  return "When activation is added, this record will help decide what content and rules can be used by a campaign or new session.";
}

function renderStateRegistryPanel() {
  const payload = modernState.states || {};
  const states = Array.isArray(payload.states) ? payload.states : [];
  const legacyFields = Array.isArray(payload.legacy_fields) ? payload.legacy_fields : [];
  const panel = card(
    "State Registry (read-only)",
    "A state is anything the game can remember or test: poisoned, hungry, cursed, a Madness counter, an envenomed weapon, a pending choice, or a terrain/location marker."
  );
  panel.classList.add("modern-registry-panel");
  panel.title = "Read-only state registry. These records describe existing status strings, counters, and pending choices without changing gameplay.";
  panel.appendChild(registryExplanation("How to read states", [
    "Scope says what the state applies to, for example a character, an item, a location, a tile, or a whole campaign.",
    "Value type says how it behaves: a flag is on/off, a counter stores a number, a timer expires later, and a modifier changes a roll.",
    "Legacy mappings show today's save fields or status strings, such as PartyMemberState.statuses, Character.madness, or a poisoned item suffix."
  ]));
  const families = Array.isArray(payload.families) ? payload.families : [];
  const scopes = Array.isArray(payload.scopes) ? payload.scopes : [];
  const reviewStatuses = [...new Set(states.map((state) => state.review_status || "review").filter(Boolean))].sort();
  const sourceBacked = states.filter((state) => state.review_status === "source_backed").length;
  const summary = el("div", "modern-grid two");
  summary.append(
    modernStatusRow("Registry", `${states.length} state definitions`, "State definitions are metadata only in this slice."),
    modernStatusRow("Source-backed", `${sourceBacked}/${states.length}`, "Records with confirmed PDF page or source references."),
    modernStatusRow("Families", families.map(modernTitleFromKey).join(", ") || "None", "State family taxonomy for future filters."),
    modernStatusRow("Scopes", scopes.map(modernTitleFromKey).join(", ") || "None", "Where these states can apply.")
  );
  panel.appendChild(summary);
  const diagnosticsPanel = renderRegistryDiagnostics("State diagnostics", payload.diagnostics, "State registry metadata warnings. Fix the source record before using it for future state-instance migration.");
  if (diagnosticsPanel) panel.appendChild(diagnosticsPanel);
  const search = input("search", "modern-state-registry-search", "Search state name, id, family, scope, source, topic, legacy mapping, or hover text.");
  search.placeholder = "Search states...";
  const familyFilter = select("modern-state-registry-family", "Filter state definitions by family.", [["", "All families"], ...families.map((item) => [item, modernTitleFromKey(item)])]);
  const scopeFilter = select("modern-state-registry-scope", "Filter state definitions by scope.", [["", "All scopes"], ...scopes.map((item) => [item, modernTitleFromKey(item)])]);
  const supplementFilter = select("modern-state-registry-supplement", "Filter state definitions by source supplement.", supplementFilterOptions());
  const reviewFilter = select("modern-state-registry-review", "Filter state definitions by PDF/source review status.", [["", "All review states"], ...reviewStatuses.map((item) => [item, modernTitleFromKey(item)])]);
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Family", familyFilter), field("Scope", scopeFilter), field("Supplement", supplementFilter), field("Review", reviewFilter));
  const results = el("div", "modern-list");
  panel.append(controls, results);

  const stateSearchText = (state) => [
    state.id,
    state.name,
    state.family,
    state.scope,
    state.value_type,
    state.review_status,
    state.source?.supplement_id,
    state.source?.source_pdf,
    state.source?.topic,
    state.ui?.label,
    state.ui?.hover,
    stateExample(state),
    stateLegacyMappingText(state),
  ].join(" ").toLowerCase();

  const renderStateRow = (state, needle) => {
    const row = el("details", "modern-row modern-registry-row");
    row.title = state.ui?.hover || "State metadata record.";
    const page = Number(state.source?.page || 0) > 0 ? `p.${state.source.page}` : state.review_status;
    row.appendChild(registrySummaryWithHighlight(state.name || state.id, `${modernTitleFromKey(state.family)} · ${modernTitleFromKey(state.scope)} · ${page}`, needle));
    row.appendChild(renderSupplementBadges([state.source?.supplement_id].filter(Boolean), "Source supplement for this state definition."));
    const chips = el("div", "modern-chip-row");
    for (const value of [state.value_type, state.source?.supplement_id, state.review_status].filter(Boolean)) {
      const chip = highlightedEl("span", "modern-tag", modernTitleFromKey(value), needle);
      chip.title = `State metadata: ${modernTitleFromKey(value)}.`;
      chips.appendChild(chip);
    }
    row.appendChild(chips);
    row.append(
      modernStatusRowHighlighted("Source", `${state.source?.source_pdf || "Current project data"} · ${state.source?.topic || "State"}`, "PDF/source reference for this state definition.", needle),
      modernStatusRowHighlighted("Legacy mappings", stateLegacyMappingText(state), "Current save fields, status strings, or item suffixes represented by this state.", needle),
      modernStatusRowHighlighted("Implementation", state.implemented ? "Implemented in current helpers" : "Metadata only", "Whether existing app logic already uses this condition.", needle),
      modernStatusRowHighlighted("Example", stateExample(state), "Plain-language example of what this state means during play.", needle),
      highlightedEl("p", "muted", state.ui?.hover || "", needle)
    );
    return row;
  };

  const draw = () => {
    results.replaceChildren();
    const needle = search.value.trim().toLowerCase();
    const rows = states
      .filter((state) => !familyFilter.value || state.family === familyFilter.value)
      .filter((state) => !scopeFilter.value || state.scope === scopeFilter.value)
      .filter((state) => !reviewFilter.value || state.review_status === reviewFilter.value)
      .filter((state) => supplementFilterMatches([state.source?.supplement_id].filter(Boolean), supplementFilter.value))
      .filter((state) => !needle || stateSearchText(state).includes(needle));
    results.appendChild(el("p", "muted", `${rows.length} matching state definition${rows.length === 1 ? "" : "s"} across ${new Set(rows.map((state) => state.family)).size} famil${new Set(rows.map((state) => state.family)).size === 1 ? "y" : "ies"}.`));
    for (const state of rows) results.appendChild(renderStateRow(state, needle));
    if (!rows.length) results.appendChild(el("p", "modern-home-status in-progress", "No matching state definitions. Clear filters or search by state name, source book, legacy status string, save field, or rules topic."));
  };
  search.addEventListener("input", draw);
  familyFilter.addEventListener("change", draw);
  scopeFilter.addEventListener("change", draw);
  supplementFilter.addEventListener("change", draw);
  reviewFilter.addEventListener("change", draw);
  draw();
  if (legacyFields.length) {
    const legacy = el("details", "modern-row modern-registry-row");
    legacy.title = "Current fields that will eventually become state instances or procedures.";
    legacy.appendChild(registrySummary("Legacy state storage", "Current save fields kept until migration"));
    for (const fieldInfo of legacyFields) {
      legacy.appendChild(modernStatusRow(fieldInfo.field, `${fieldInfo.status} -> ${fieldInfo.replacement}`, fieldInfo.notes || ""));
    }
    panel.appendChild(legacy);
  }
  return panel;
}

function stateExample(state) {
  const id = state?.id || "";
  if (id === "madness") return "A hero with Madness 2 is not just carrying text; the counter can be tested by rules that check thresholds, recovery, or insanity.";
  if (id === "dark-plague") return "Dark Plague is a character state that room-entry rules can read, damage from, spread, or remove through specific cure rules.";
  if (id === "envenomed-weapon") return "An envenomed weapon is an equipment state: the app can read it during an attack, then clear or consume it after the poison matters.";
  if (id === "fd-psychic-residue-save") return "Psychic Residue +3 Save is a temporary adventure marker that modifies later Psychic Residue saves.";
  return "Later rules can read, apply, remove, or expire this state instead of adding another one-off field.";
}

function stateLegacyMappingText(state) {
  const mappings = state?.legacy_mappings || {};
  const parts = [];
  for (const [key, value] of Object.entries(mappings)) {
    if (Array.isArray(value)) {
      parts.push(`${modernTitleFromKey(key)}: ${value.join(", ")}`);
    } else if (value && typeof value === "object") {
      parts.push(`${modernTitleFromKey(key)}: ${modernSearchText(value)}`);
    } else {
      parts.push(`${modernTitleFromKey(key)}: ${String(value)}`);
    }
  }
  return parts.join(" | ") || "None";
}

function terrainLegacyMappingText(record) {
  const mappings = record?.legacy_mappings || {};
  const parts = [];
  for (const [key, value] of Object.entries(mappings)) {
    if (Array.isArray(value)) {
      parts.push(`${modernTitleFromKey(key)}: ${value.join(", ")}`);
    } else if (value && typeof value === "object") {
      parts.push(`${modernTitleFromKey(key)}: ${modernSearchText(value)}`);
    } else {
      parts.push(`${modernTitleFromKey(key)}: ${String(value)}`);
    }
  }
  return parts.join(" | ") || "None";
}

function renderTerrainRegistryPanel() {
  const payload = modernState.terrain || {};
  const terrain = Array.isArray(payload.terrain) ? payload.terrain : [];
  const legacyFields = Array.isArray(payload.legacy_fields) ? payload.legacy_fields : [];
  const panel = card(
    "Terrain Registry (read-only)",
    "Terrain records describe where play is happening and which environment rules can apply. This is separate from fixed maps and separate from random room tiles."
  );
  panel.classList.add("modern-registry-panel");
  panel.title = "Read-only terrain registry. These records describe existing environment and terrain values without changing map generation.";
  panel.appendChild(registryExplanation("Terrain vs maps vs room tiles", [
    "Maps are authored places with pins, regions, and linked locations.",
    "Room tiles are reusable random-generation pieces with exits, walkable cells, and catalog rules.",
    "Terrain is the rules context on top: indoor, forest, swamp, water, caverns, fungal grottoes, FD river bank, or Courtship Demesne water."
  ]));
  const kinds = Array.isArray(payload.kinds) ? payload.kinds : [];
  const reviewStatuses = [...new Set(terrain.map((record) => record.review_status || "review").filter(Boolean))].sort();
  const summary = el("div", "modern-grid two");
  summary.append(
    modernStatusRow("Registry", `${terrain.length} terrain records`, "Terrain definitions are metadata only in this slice."),
    modernStatusRow("Environment values", (payload.environment_values || []).map(modernTitleFromKey).join(", "), "Current table-routing environments."),
    modernStatusRow("Terrain values", (payload.terrain_values || []).map(modernTitleFromKey).join(", "), "Current tile terrain values."),
    modernStatusRow("Water group", (payload.water_values || []).map(modernTitleFromKey).join(", "), "Values treated as water by current terrain helpers.")
  );
  panel.appendChild(summary);
  const diagnosticsPanel = renderRegistryDiagnostics("Terrain diagnostics", payload.diagnostics, "Terrain registry metadata warnings. Fix the source record before using it for future terrain-instance migration.");
  if (diagnosticsPanel) panel.appendChild(diagnosticsPanel);
  const search = input("search", "modern-terrain-registry-search", "Search terrain name, id, kind, source, topic, interactions, examples, legacy mapping, or hover text.");
  search.placeholder = "Search terrain...";
  const kindFilter = select("modern-terrain-registry-kind", "Filter terrain definitions by kind.", [["", "All kinds"], ...kinds.map((item) => [item, modernTitleFromKey(item)])]);
  const supplementFilter = select("modern-terrain-registry-supplement", "Filter terrain definitions by source supplement.", supplementFilterOptions());
  const reviewFilter = select("modern-terrain-registry-review", "Filter terrain definitions by PDF/source review status.", [["", "All review states"], ...reviewStatuses.map((item) => [item, modernTitleFromKey(item)])]);
  const interactionFilter = select("modern-terrain-registry-interaction", "Filter terrain by common interaction groups.", [
    ["", "All interactions"],
    ["water", "Water / Flower Portal"],
    ["outdoor", "Outdoor"],
    ["entangle", "Entangle"],
    ["forest_pathway", "Forest Pathway"],
    ["routing", "Table routing"],
  ]);
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Kind", kindFilter), field("Supplement", supplementFilter), field("Review", reviewFilter), field("Interaction", interactionFilter));
  const results = el("div", "modern-list");
  panel.append(controls, results);

  const terrainSearchText = (record) => [
    record.id,
    record.name,
    record.kind,
    record.review_status,
    record.source?.supplement_id,
    record.source?.source_pdf,
    record.source?.topic,
    record.ui?.hover,
    terrainLegacyMappingText(record),
    ...(record.interactions || []),
    ...(record.examples || []),
  ].join(" ").toLowerCase();

  const matchesInteraction = (record) => {
    const text = terrainSearchText(record);
    if (!interactionFilter.value) return true;
    if (interactionFilter.value === "water") return /water|river|seaside|riverside|flower portal/.test(text);
    if (interactionFilter.value === "outdoor") return /outdoor/.test(text);
    if (interactionFilter.value === "entangle") return /entangle/.test(text);
    if (interactionFilter.value === "forest_pathway") return /forest pathway/.test(text);
    if (interactionFilter.value === "routing") return /routing|routes|table/.test(text);
    return true;
  };

  const renderTerrainRow = (record, needle) => {
    const row = el("details", "modern-row modern-registry-row");
    row.title = record.ui?.hover || "Terrain metadata record.";
    const page = Number(record.source?.page || 0) > 0 ? `p.${record.source.page}` : record.review_status;
    row.appendChild(registrySummaryWithHighlight(record.name || record.id, `${modernTitleFromKey(record.kind)} · ${page}`, needle));
    row.appendChild(renderSupplementBadges([record.source?.supplement_id].filter(Boolean), "Source supplement for this terrain definition."));
    const chips = el("div", "modern-chip-row");
    for (const value of [record.kind, record.source?.supplement_id, record.review_status].filter(Boolean)) {
      const chip = highlightedEl("span", "modern-tag", modernTitleFromKey(value), needle);
      chip.title = `Terrain metadata: ${modernTitleFromKey(value)}.`;
      chips.appendChild(chip);
    }
    row.appendChild(chips);
    row.append(
      modernStatusRowHighlighted("Source", `${record.source?.source_pdf || "Current project data"} · ${record.source?.topic || "Terrain"}`, "PDF/source reference for this terrain definition.", needle),
      modernStatusRowHighlighted("Legacy mappings", terrainLegacyMappingText(record), "Current fields or tile-grid concepts represented by this terrain record.", needle),
      modernStatusRowHighlighted("Interactions", (record.interactions || []).join("; ") || "None recorded", "Current rules that read or care about this terrain.", needle),
      modernStatusRowHighlighted("Example", (record.examples || [])[0] || "Terrain helps decide which rules can apply in a place.", "Plain-language example of what this terrain means during play.", needle),
      highlightedEl("p", "muted", record.ui?.hover || "", needle)
    );
    return row;
  };

  const draw = () => {
    results.replaceChildren();
    const needle = search.value.trim().toLowerCase();
    const rows = terrain
      .filter((record) => !kindFilter.value || record.kind === kindFilter.value)
      .filter((record) => !reviewFilter.value || record.review_status === reviewFilter.value)
      .filter((record) => supplementFilterMatches([record.source?.supplement_id].filter(Boolean), supplementFilter.value))
      .filter(matchesInteraction)
      .filter((record) => !needle || terrainSearchText(record).includes(needle));
    results.appendChild(el("p", "muted", `${rows.length} matching terrain record${rows.length === 1 ? "" : "s"} across ${new Set(rows.map((record) => record.kind)).size} kind${new Set(rows.map((record) => record.kind)).size === 1 ? "" : "s"}.`));
    for (const record of rows) results.appendChild(renderTerrainRow(record, needle));
    if (!rows.length) results.appendChild(el("p", "modern-home-status in-progress", "No matching terrain records. Clear filters or search by terrain name, source book, legacy field, interaction, map concept, or rules topic."));
  };
  search.addEventListener("input", draw);
  kindFilter.addEventListener("change", draw);
  supplementFilter.addEventListener("change", draw);
  reviewFilter.addEventListener("change", draw);
  interactionFilter.addEventListener("change", draw);
  draw();
  if (legacyFields.length) {
    const legacy = el("details", "modern-row modern-registry-row");
    legacy.title = "Current fields that will eventually become terrain instances or terrain modifiers.";
    legacy.appendChild(registrySummary("Legacy terrain storage", "Current map/session fields kept until migration"));
    for (const fieldInfo of legacyFields) {
      legacy.appendChild(modernStatusRow(fieldInfo.field, `${fieldInfo.status} -> ${fieldInfo.replacement}`, fieldInfo.notes || ""));
    }
    panel.appendChild(legacy);
  }
  return panel;
}

function registryResolverMatchRow(title, match, type) {
  const definition = type === "state" ? match?.state : match;
  if (!definition) {
    return modernStatusRow(title, "No registry match", "The resolver did not find a metadata row for this value.");
  }
  const source = definition.source || {};
  const page = Number(source.page || 0) > 0 ? ` p.${source.page}` : "";
  const sourceText = `${source.source_pdf || "Current project data"}${page} · ${source.topic || (type === "state" ? "State" : "Terrain")}`;
  const row = el("details", "modern-row modern-registry-row");
  row.appendChild(registrySummary(definition.name || definition.id, `${definition.id} · ${sourceText}`));
  if (type === "state") {
    row.append(
      modernStatusRow("Family / scope", `${modernTitleFromKey(definition.family)} · ${modernTitleFromKey(definition.scope)} · ${modernTitleFromKey(definition.value_type)}`, "State taxonomy for future state-instance migration."),
      modernStatusRow("Legacy mappings", stateLegacyMappingText(definition), "Legacy labels, fields, or item suffixes that matched this state."),
      modernStatusRow("Hover", definition.ui?.hover || "No hover text recorded.", "Player-facing explanation from the State Registry.")
    );
  } else {
    row.append(
      modernStatusRow("Kind", modernTitleFromKey(definition.kind), "Terrain taxonomy for future terrain-instance migration."),
      modernStatusRow("Legacy mappings", terrainLegacyMappingText(definition), "Legacy environment, terrain, or tile-catalog values that matched this record."),
      modernStatusRow("Interactions", (definition.interactions || []).join("; ") || "None recorded", "Current rules that read or care about this terrain.")
    );
  }
  return row;
}

function renderRegistryResolverPanel() {
  const panel = card(
    "Registry Resolver (read-only)",
    "Diagnostic lookup for checking which State or Terrain Registry rows match today's legacy labels and terrain fields."
  );
  panel.classList.add("modern-registry-panel");
  panel.title = "Read-only resolver. This does not write character/session state, change terrain, or apply rules.";

  const stateLabels = input("text", "modern-registry-resolve-state-labels", "Enter one or more visible effect/status labels, separated by commas.");
  stateLabels.placeholder = "Cursed (-1 Def), Poisoned L5, Longsword (poisoned)";
  const stateResults = el("div", "modern-list");
  const stateRun = button("Resolve State Labels", "Match visible status/effect labels against the State Registry without changing saves.", async () => {
    stateResults.replaceChildren();
    const params = new URLSearchParams();
    params.set("labels", stateLabels.value || "");
    const payload = await api(`/api/registry/resolve/states?${params.toString()}`);
    stateResults.appendChild(modernStatusRow("Lookup", `${payload.matches?.length || 0} label result(s)`, "Read-only State Registry resolver result."));
    for (const match of payload.matches || []) {
      stateResults.appendChild(registryResolverMatchRow(match.label || "Label", match, "state"));
    }
    if (!(payload.matches || []).length) stateResults.appendChild(modernStatusRow("Result", "No labels entered", "Enter visible effect/status labels first."));
  });

  const stateSection = el("div", "modern-resolver-section");
  stateSection.append(field("State/effect labels", stateLabels), stateRun, stateResults);

  const environment = input("text", "modern-registry-resolve-environment", "Legacy environment value such as dungeon, caverns, or fungal_grottoes.");
  environment.placeholder = "dungeon";
  const terrain = input("text", "modern-registry-resolve-terrain", "Legacy terrain value such as indoor, forest, river, or outdoor.");
  terrain.placeholder = "indoor";
  const tileCatalog = input("text", "modern-registry-resolve-tile-catalog", "Optional tile catalog such as forsaken_depths_rivers.");
  tileCatalog.placeholder = "forsaken_depths_rivers";
  const terrainResults = el("div", "modern-list");
  const terrainRun = button("Resolve Terrain Context", "Match environment, terrain, and tile catalog values against the Terrain Registry without changing the map.", async () => {
    terrainResults.replaceChildren();
    const params = new URLSearchParams();
    if (environment.value) params.set("environment", environment.value);
    if (terrain.value) params.set("terrain", terrain.value);
    if (tileCatalog.value) params.set("tile_catalog", tileCatalog.value);
    const payload = await api(`/api/registry/resolve/terrain?${params.toString()}`);
    terrainResults.appendChild(modernStatusRow("Lookup", `${payload.matches?.length || 0} terrain match(es)`, "Read-only Terrain Registry resolver result."));
    for (const match of payload.matches || []) terrainResults.appendChild(registryResolverMatchRow(match.name || match.id, match, "terrain"));
    if (!(payload.matches || []).length) terrainResults.appendChild(modernStatusRow("Result", "No terrain records matched", "Try environment=dungeon and terrain=indoor, or tile_catalog=forsaken_depths_rivers."));
  });

  const terrainSection = el("div", "modern-resolver-section");
  const terrainFields = el("div", "modern-grid three");
  terrainFields.append(field("Environment", environment), field("Terrain", terrain), field("Tile catalog", tileCatalog));
  terrainSection.append(terrainFields, terrainRun, terrainResults);

  panel.append(stateSection, terrainSection);
  return panel;
}

function renderSettings() {
  const prefs = readModernPrefs();
  const selectedSupplements = new Set(modernState.preferences?.enabled_supplement_ids || ["expanded-edition-core"]);
  const guidePanel = renderGuide("Settings Workflow", [
    "Settings affect dashboard defaults and Go Adventure choices; they do not delete rules data.",
    "Supplement switches are saved defaults for new sessions. Go Adventure preselects them, lets you adjust the list for that session, and locks the final supplement snapshot when play starts.",
    "The State Registry is read-only for now; existing status strings and counters remain the save format.",
    "The Terrain Registry is read-only for now; current map/session terrain fields remain the save format.",
    "Legacy ruleset/profile controls still decide which profiles appear as preferred random-adventure choices.",
    "TAG banking toggles which finance workflow the dashboard emphasizes."
  ], "", "settings ruleset profile");
  const settingsBody = "Save dashboard preferences for starting adventures. These preferences are used by Go Adventure.";
  const panel = card("Settings / Options", settingsBody);
  const tag = input("checkbox", "modern-tag-banking", "Use TAG banking for campaign finance actions instead of only the legacy home-bank flow.");
  tag.checked = Boolean(modernState.campaign?.tag_banking_enabled);
  const defaultProfile = select("modern-rules-profile", "Legacy default ruleset profile for random adventures. New sessions now also snapshot active supplement ids.", modernState.rulesProfiles.map((p) => [p.id, p.label]));
  defaultProfile.value = prefs.defaultRulesetProfile || "ee_random";
  const mapMode = select("modern-default-map-mode", "Default map mode.", [["unlimited", "Unlimited"], ["paper", "Paper 20x28"]]);
  mapMode.value = prefs.defaultMapMode || "unlimited";
  const mapLimit = input("number", "modern-default-map-limit", "Default unlimited-map element cap before end-boss pressure.", String(prefs.defaultMapLimit || 60));
  const xp = select("modern-default-xp-system", "Default XP system.", [["classical", "Classical"], ["slow_and_sure", "Slow and Sure"], ["old_school", "Old School"], ["slower_advancement", "Slower Advancement"]]);
  xp.value = prefs.defaultXpSystem || "classical";
  panel.append(field("TAG banking", tag), field("Default random ruleset (legacy)", defaultProfile), field("Default map mode", mapMode), field("Default map limit", mapLimit), field("XP system", xp));
  const supplementPrefsBody = "Saved default list for new sessions. Expanded Edition is locked on; Go Adventure can adjust optional supplements per session before locking the snapshot.";
  const supplementPrefsCard = card("Enabled Supplements (default)", supplementPrefsBody);
  const supplements = Array.isArray(modernState.supplements?.supplements) ? modernState.supplements.supplements : [];
  const supplementPrefChecks = new Map();
  function selectedDefaultSupplementIds() {
    return supplements
      .filter((supplement) => supplement.locked || supplementPrefChecks.get(supplement.id)?.checked)
      .map((supplement) => supplement.id);
  }
  function syncDefaultSupplementRows() {
    const selected = selectedDefaultSupplementIds();
    const conflicts = supplementConflictIds(selected);
    for (const supplement of supplements) {
      const checkbox = supplementPrefChecks.get(supplement.id);
      if (!checkbox) continue;
      const blockedByConflict = conflicts.has(supplement.id) && !checkbox.checked && !supplement.locked;
      checkbox.disabled = Boolean(supplement.locked || blockedByConflict);
      checkbox.title = blockedByConflict
        ? `${supplement.title || supplement.id} conflicts with another selected default supplement.`
        : `Save ${supplement.title || supplement.id} as a default enabled supplement for new sessions. This does not alter existing saved sessions.`;
      const label = checkbox.closest("label")?.querySelector("[data-supplement-pref-label]");
      if (label) {
        const state = supplement.locked ? "locked on" : blockedByConflict ? "conflicts with selected default" : checkbox.checked ? "enabled preference" : "off preference";
        label.textContent = `${supplement.title || supplement.id} - ${state}`;
      }
    }
  }
  for (const supplement of supplements) {
    const checkbox = input("checkbox", `modern-supplement-${supplement.id}`, `Save ${supplement.title || supplement.id} as a default enabled supplement for new sessions. This does not alter existing saved sessions.`);
    checkbox.checked = supplement.locked || selectedSupplements.has(supplement.id);
    checkbox.disabled = Boolean(supplement.locked);
    supplementPrefChecks.set(supplement.id, checkbox);
    const state = supplement.locked ? "locked on" : (checkbox.checked ? "enabled preference" : "off preference");
    const row = el("label", "modern-check-row");
    const label = el("span", "", `${supplement.title || supplement.id} - ${state}`);
    label.dataset.supplementPrefLabel = "true";
    row.append(checkbox, label);
    row.title = `${supplement.notes || "Supplement registry record."} Capabilities: ${(supplement.capabilities || []).join(", ") || "none listed"}.`;
    checkbox.addEventListener("change", syncDefaultSupplementRows);
    supplementPrefsCard.appendChild(row);
  }
  syncDefaultSupplementRows();
  const rulesBody = "Legacy compatibility controls for which ruleset profiles appear as preferred options on Go Adventure. This does not enable, disable, or delete supplement content.";
  const rulesCard = card("Legacy Ruleset Profiles", rulesBody);
  for (const profile of modernState.rulesProfiles) {
    const checkbox = input("checkbox", `modern-enabled-ruleset-${profile.id}`, `Show ${profile.label} as an available legacy ruleset profile in Go Adventure. This only changes dashboard filtering; it does not remove rules data or change supplement activation.`);
    const enabled = prefs.enabledRulesets ? prefs.enabledRulesets.includes(profile.id) : true;
    checkbox.checked = enabled;
    const row = el("label", "modern-check-row");
    row.append(checkbox, el("span", "", profile.label));
    row.title = checkbox.title;
    rulesCard.appendChild(row);
  }
  panel.appendChild(button("Save Preferences", "Save TAG banking and dashboard defaults.", async () => {
    modernState.campaign = await api("/api/campaign", { method: "PUT", body: JSON.stringify({ tag_banking_enabled: tag.checked }) });
    const enabledSupplementIds = supplements
      .filter((supplement) => supplement.locked || document.getElementById(`modern-supplement-${supplement.id}`)?.checked)
      .map((supplement) => supplement.id);
    modernState.preferences = await api("/api/preferences", {
      method: "PUT",
      body: JSON.stringify({ enabled_supplement_ids: enabledSupplementIds }),
    });
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
  rootEl.append(
    collapsibleSettingsPanel(guidePanel, "Settings Workflow", "What these settings do and do not change."),
    collapsibleSettingsPanel(panel, "Settings / Options", settingsBody),
    collapsibleSettingsPanel(supplementPrefsCard, "Enabled Supplements (default)", supplementPrefsBody),
    collapsibleSettingsPanel(renderSupplementRegistryPanel(), "Supplement Library (read-only)", "Known packaged and local supplement records."),
    collapsibleSettingsPanel(renderStateRegistryPanel(), "State Registry (read-only)", "Search and inspect metadata for current and future state records."),
    collapsibleSettingsPanel(renderRegistryResolverPanel(), "Registry Resolver (read-only)", "Resolve visible labels and terrain fields against registry metadata."),
    collapsibleSettingsPanel(renderTerrainRegistryPanel(), "Terrain Registry (read-only)", "Search and inspect metadata for terrain, environments, and tile contexts."),
    collapsibleSettingsPanel(rulesCard, "Legacy Ruleset Profiles", rulesBody)
  );
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
  if (adventure.pdf_source) return "PDF";
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

function adventureModuleStatus(adventure) {
  if (adventure.pdf_source) return "N/A";
  const inUse = adventureModuleInUse(adventure.id).length;
  if (inUse) return "In progress";
  if (adventureModuleCompleted(adventure.id)) return "Completed";
  if (adventure.playable === false) return "Not playable";
  if (["random", "ai-adventure", "courtship-demesne"].includes(String(adventure.id || "")) || adventure.source === "rules") return "Protected";
  return "Ready";
}

function adventureModuleTags(adventure) {
  const tags = [adventureModuleKind(adventure)];
  if (adventure.playable === false) tags.push("Not playable");
  if (adventure.pdf_source && adventure.pdf_detected_type) tags.push(String(adventure.pdf_detected_type).replaceAll("_", " "));
  if (adventure.pdf_source && adventure.pdf_map_signals) tags.push("Maps");
  if (adventure.pdf_source && adventure.pdf_table_signals) tags.push("Tables");
  if (adventure.pdf_source && adventure.pdf_foe_signals) tags.push("Foes");
  if (adventure.pdf_source && adventure.pdf_class_signals) tags.push("Classes");
  if (adventure.pdf_source && adventure.pdf_conversion_status === "source_pdf_unscanned") tags.push("Unscanned");
  if (adventureModuleCompleted(adventure.id)) tags.push("Completed");
  if (adventureModuleInUse(adventure.id).length) tags.push("In use");
  return tags;
}

function renderAdventurePdfSourceScanner() {
  const pdfSources = (modernState.adventures || []).filter((adventure) => adventure.pdf_source);
  const unscanned = pdfSources.filter((adventure) => adventure.pdf_conversion_status === "source_pdf_unscanned").length;
  const panel = card(
    "PDF Adventure Sources",
    "Scan source PDFs before conversion. The scanner records title, pages, extractability, likely module type, package/map signals, and recommended conversion path; it does not turn a PDF into a playable module without a reviewed manifest."
  );
  panel.append(
    modernStatusRow("Source folder", "DATA_DIR/Adventure PDFs", "Place new owned adventure PDFs here in the user-facing appdata folder. The legacy repo Adventures folder is also scanned for existing local PDFs."),
    modernStatusRow("Assessed PDFs", `${pdfSources.length} source PDF(s) · ${unscanned} unscanned`, "PDF sources stay non-playable until a validated adventure.json manifest is created and imported."),
    modernStatusRow("Package signals", "Maps, pins, tables, foes, classes", "The scanner flags source PDFs that may need local package data before conversion."),
    modernStatusRow("Map/pin signals", "Review before conversion", "Use package review to place extracted or manually supplied map art and pin rooms, scenes, hexes, or locations."),
    modernStatusRow("Package layer", "Maps, pins, tables, foes, classes", "Odd modules should become declarative adventure packages: local data and map pins, not executable scripts.")
  );
  const row = actions();
  row.appendChild(
    button("Scan new PDFs", "Scan new or changed PDFs in DATA_DIR/Adventure PDFs and the legacy Adventures folder. This creates assessment metadata only.", async () => {
      const result = await api("/api/adventures/pdf-sources/scan", { method: "POST", body: JSON.stringify({}) });
      setStatus(`Scanned ${result.scanned?.length || 0} new PDF source(s); ${result.skipped?.length || 0} already assessed.`);
      window.sessionStorage.setItem(ADVENTURE_MANAGEMENT_TAB_KEY, "pdf");
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  return panel;
}

function adventurePackageForPdf(adventure) {
  const id = String(adventure?.id || "");
  return (modernState.adventurePackages || []).find((item) => item.package_id === id) || null;
}

async function refreshAdventurePackageSummaries() {
  const result = await api("/api/adventures/packages");
  modernState.adventurePackages = result.packages || [];
  return modernState.adventurePackages;
}

function renderAdventurePackageManager() {
  const pdfSources = (modernState.adventures || []).filter((adventure) => adventure.pdf_source);
  const panel = card(
    "PDF Importer Module List",
    "Every scanned source PDF appears here with status and actions. Scan/rescan updates assessment metadata; Create / Refresh builds the local DATA_DIR package; Validate checks the package; Edit / Check opens the structured review workspace."
  );
  if (!pdfSources.length) {
    panel.appendChild(el("p", "muted", "No PDF sources found. Place PDFs in DATA_DIR/Adventure PDFs, then use Scan new PDFs."));
    return panel;
  }
  const packageContainer = el("div", "modern-package-review");
  const drawWorkspace = (pkg = null) => {
    packageContainer.replaceChildren();
    if (!pkg) {
      packageContainer.appendChild(el("p", "muted", "Choose Edit / Check on a scanned module to open its structured review workspace."));
      return;
    }
    packageContainer.append(
      modernStatusRow("Editing module", pkg.title || pkg.package_id, "This is the local package review record; it is not playable until a validated adventure.json manifest exists."),
      modernStatusRow("Package status", `${pkg.node_count || 0} location(s) · ${pkg.map_count || 0} map(s) · ${pkg.foe_count || 0} foe(s) · ${pkg.item_count || 0} item(s) · ${pkg.state_count || 0} state(s) · ${pkg.rule_count || 0} rule(s)`, "Use the browser and editors below to check every imported element against the source PDF."),
      modernStatusRow("Storage", pkg.adventure_folder || "DATA_DIR/Adventures/<adventure_id>/", "Everything for this adventure lives together beside game.db: package.json, maps/, artwork/, tables/, notes/, and the future adventure.json.")
    );
    packageContainer.appendChild(renderAdventurePackageMaps(pkg));
    packageContainer.appendChild(renderAdventurePackageArtworkLibrary(pkg));
    packageContainer.appendChild(renderAdventurePackageReviewWorkspace(pkg, () => renderPage()));
    packageContainer.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const topActions = actions();
  topActions.append(
    button("Scan New PDFs", "Scan new PDFs in DATA_DIR/Adventure PDFs and the legacy Adventures folder. Existing unchanged assessments are skipped.", async () => {
      const result = await api("/api/adventures/pdf-sources/scan", { method: "POST", body: JSON.stringify({}) });
      setStatus(`Scanned ${result.scanned?.length || 0} new PDF source(s); ${result.skipped?.length || 0} already assessed.`);
      window.sessionStorage.setItem(ADVENTURE_MANAGEMENT_TAB_KEY, "pdf");
      await refreshCoreAndRender();
    }),
    button("Rescan All PDFs", "Force a metadata rescan for all source PDFs. This updates assessment metadata but does not overwrite reviewed package records.", async () => {
      const result = await api("/api/adventures/pdf-sources/scan", { method: "POST", body: JSON.stringify({ force: true }) });
      setStatus(`Rescanned ${result.scanned?.length || 0} PDF source(s); ${result.errors?.length || 0} scanner issue(s).`);
      window.sessionStorage.setItem(ADVENTURE_MANAGEMENT_TAB_KEY, "pdf");
      await refreshCoreAndRender();
    }, "secondary"),
    button("Refresh List", "Reload package summaries already stored in DATA_DIR. This does not rescan PDFs.", async () => {
      const packages = await refreshAdventurePackageSummaries();
      setStatus(`Loaded ${packages.length} adventure package(s).`);
      renderPage();
    }, "secondary")
  );
  const list = el("div", "modern-module-table modern-pdf-module-list");
  list.append(el("strong", "", "Module"), el("strong", "", "Status"), el("strong", "", "Detected Content"), el("strong", "", "Actions"));
  for (const adventure of [...pdfSources].sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id))) {
    let currentPkg = adventurePackageForPdf(adventure);
    const nameCell = el("div", "modern-row-copy");
    nameCell.append(
      el("strong", "", adventure.name || adventure.id),
      el("span", "muted", `${adventure.id} · ${adventure.pdf_page_count || 0} page(s) · ${adventure.pdf_source_kind || "source"}`)
    );
    if (adventure.source) nameCell.appendChild(el("span", "muted", adventure.source));
    const statusCell = el("div", "modern-row-copy");
    statusCell.append(
      el("span", "modern-tag", currentPkg ? (currentPkg.review?.status || "draft review") : (adventure.pdf_conversion_status || "source PDF assessed")),
      el("span", "muted", currentPkg ? `${currentPkg.node_count || 0} location(s), ${currentPkg.map_count || 0} map(s), ${currentPkg.pin_count || 0} pin(s)` : "No local package yet")
    );
    const detected = el("div", "modern-chip-row");
    const signals = [
      [adventure.pdf_detected_type ? String(adventure.pdf_detected_type).replaceAll("_", " ") : "unknown", "Detected PDF workflow type."],
      [`maps ${adventure.pdf_map_signals || 0}`, "Potential map/image signals found by the scanner."],
      [`locations ${adventure.pdf_numbered_location_signals || 0}`, "Potential room, scene, hex, or numbered-location signals."],
      [`tables ${adventure.pdf_table_signals || 0}`, "Potential roll table signals."],
      [`foes ${adventure.pdf_foe_signals || 0}`, "Potential foe or monster signals."],
      [`classes ${adventure.pdf_class_signals || 0}`, "Potential new character class signals."],
    ];
    for (const [label, hint] of signals) {
      const chip = el("span", "modern-tag", label);
      chip.title = hint;
      detected.appendChild(chip);
    }
    const rowActions = actions();
    rowActions.append(
      button("Create / Refresh", "Create or refresh the local package from this PDF. Existing reviewed records and matching pins are preserved where possible.", async () => {
        setStatus(`Creating or refreshing package for ${adventure.name || adventure.id}...`);
        const result = await api(`/api/adventures/pdf-sources/${encodeURIComponent(adventure.id)}/package`, {
          method: "POST",
          body: JSON.stringify({ extract_maps: true }),
        });
        const detail = await api(`/api/adventures/packages/${encodeURIComponent(result.package.package_id)}`);
        replaceAdventurePackageInState(detail.package);
        currentPkg = detail.package;
        setStatus(`Package ready: ${detail.package.title}.`);
        drawWorkspace(detail.package);
      }),
      button("Validate", "Load this package and show structural diagnostics. This checks local package coherence; it does not certify PDF accuracy.", async () => {
        if (!currentPkg) {
          setStatus(`No package exists yet for ${adventure.name || adventure.id}. Use Create / Refresh first.`);
          return;
        }
        setStatus(`Validating package for ${currentPkg.title || currentPkg.package_id}...`);
        const result = await api(`/api/adventures/packages/${encodeURIComponent(currentPkg.package_id)}`);
        replaceAdventurePackageInState(result.package);
        currentPkg = result.package;
        const diagnostics = result.package.diagnostics || {};
        const messages = [...(diagnostics.errors || []), ...(diagnostics.warnings || [])];
        setStatus(diagnostics.valid ? `${result.package.title} package is structurally valid.` : `${result.package.title} needs attention: ${messages.slice(0, 2).join("; ")}`);
        drawWorkspace(result.package);
      }, "secondary"),
      button("Edit / Check", "Open the structured review workspace for locations, maps, foes, items, classes, states, rules, tables, trackers, and procedures.", async () => {
        let editable = currentPkg;
        setStatus(`Opening review workspace for ${adventure.name || adventure.id}...`);
        if (!editable) {
          const created = await api(`/api/adventures/pdf-sources/${encodeURIComponent(adventure.id)}/package`, {
            method: "POST",
            body: JSON.stringify({ extract_maps: true }),
          });
          editable = created.package;
          replaceAdventurePackageInState(editable);
        }
        const result = await api(`/api/adventures/packages/${encodeURIComponent(editable.package_id)}`);
        replaceAdventurePackageInState(result.package);
        currentPkg = result.package;
        setStatus(`Opened review workspace for ${result.package.title}.`);
        drawWorkspace(result.package);
      }),
      button("Delete Package", "Delete the local review package from DATA_DIR/Adventures. This does not delete the original PDF source.", async () => {
        if (!currentPkg) {
          setStatus(`No local package exists yet for ${adventure.name || adventure.id}.`);
          return;
        }
        if (!window.confirm(`Delete the local review package for ${currentPkg.title || currentPkg.package_id}? The source PDF is not deleted.`)) return;
        setStatus(`Deleting local package ${currentPkg.title || currentPkg.package_id}...`);
        const result = await api(`/api/adventures/packages/${encodeURIComponent(currentPkg.package_id)}`, { method: "DELETE" });
        currentPkg = null;
        await refreshAdventurePackageSummaries();
        setStatus(result.message || "Deleted local package.");
        renderPage();
      }, "danger-button")
    );
    list.append(nameCell, statusCell, detected, rowActions);
  }
  panel.append(topActions, packageContainer, list);
  drawWorkspace();
  return panel;
}

function parseJsonArrayField(control, label) {
  try {
    const value = JSON.parse(control.value || "[]");
    if (!Array.isArray(value)) throw new Error(`${label} must be a JSON array.`);
    return value;
  } catch (error) {
    throw new Error(`${label}: ${error.message}`);
  }
}

function commaList(value) {
  return String(value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function replaceAdventurePackageInState(pkg) {
  modernState.adventurePackages = (modernState.adventurePackages || []).filter((item) => item.package_id !== pkg.package_id);
  modernState.adventurePackages.push(pkg);
}

function renderAdventurePackageDiagnostics(pkg) {
  const diagnostics = pkg.diagnostics || {};
  const panel = el("div", diagnostics.valid ? "modern-package-diagnostics ok" : "modern-package-diagnostics warn");
  panel.appendChild(el("strong", "", diagnostics.valid ? "Package review data is structurally valid" : "Package review data needs attention"));
  const messages = [...(diagnostics.errors || []), ...(diagnostics.warnings || [])];
  if (!messages.length) {
    panel.appendChild(el("span", "muted", "No package diagnostics reported. This does not mean the PDF content has been fully checked yet."));
    return panel;
  }
  const list = el("ul", "modern-warning-list");
  for (const message of messages) list.appendChild(el("li", "", message));
  panel.appendChild(list);
  return panel;
}

function renderAdventurePackageReviewWorkspace(pkg, redraw) {
  const panel = card(
    "PDF Import Review Workspace",
    "Review the import as structured facts before it becomes playable: source pages, room/scene/location nodes, branch targets, maps, pins, local tables, foes, items, classes, states, rules, trackers, and procedures."
  );
  panel.appendChild(renderAdventurePackageDiagnostics(pkg));
  const hasDetail = Array.isArray(pkg.nodes);
  if (!hasDetail) {
    const loadRow = actions();
    loadRow.appendChild(button("Load Editable Package", "Load the full local package.json from DATA_DIR so you can review and edit structured sections.", async () => {
      const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}`);
      replaceAdventurePackageInState(result.package);
      setStatus(`Loaded editable package: ${result.package.title}.`);
      redraw();
    }));
    panel.appendChild(loadRow);
    return panel;
  }
  const title = input("text", `package-title-${pkg.package_id}`, "Package title shown in Adventure Management and future module conversion.");
  title.value = pkg.title || "";
  const pages = input("text", `package-pages-${pkg.package_id}`, "Comma-separated PDF pages reviewed for this package.");
  pages.value = (pkg.source?.source_pages || []).join(", ");
  const status = select(`package-review-status-${pkg.package_id}`, "Review status. Use ready only after the source PDF has been checked.", [
    ["draft_review_needed", "Draft - needs PDF review"],
    ["review_in_progress", "Review in progress"],
    ["ready_for_manifest", "Ready for manifest conversion"],
    ["blocked", "Blocked"],
  ]);
  status.value = pkg.review?.status || "draft_review_needed";
  const license = textarea(`package-license-${pkg.package_id}`, "Private-use or publishing-rights note for PDF-derived text and artwork.", 3);
  license.value = pkg.source?.license_note || "";
  const notes = textarea(`package-review-notes-${pkg.package_id}`, "Reviewer notes: what was checked, what is uncertain, and what still needs PDF/source confirmation.", 4);
  notes.value = pkg.review?.notes || "";
  const detailGrid = el("div", "modern-package-review-grid");
  detailGrid.append(
    field("Package Title", title),
    field("Reviewed PDF Pages", pages),
    field("Review Status", status),
    field("License / Rights Note", license),
    field("Reviewer Notes", notes)
  );
  const saveDetails = actions();
  saveDetails.appendChild(button("Save Review Details", "Save package title, reviewed pages, rights note, and review status to DATA_DIR/Adventures/<module_id>/package.json.", async () => {
    const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/review`, {
      method: "POST",
      body: JSON.stringify({
        title: title.value,
        source_pages: pages.value,
        license_note: license.value,
        review_status: status.value,
        review_notes: notes.value,
      }),
    });
    replaceAdventurePackageInState(result.package);
    setStatus(`Saved review details for ${result.package.title}.`);
    redraw();
  }));
  const extractRow = actions();
  extractRow.appendChild(button("Extract Candidate Lists", "Re-scan the source PDF text and add candidate locations, tables, foes, classes, items, states, rules, and procedures without overwriting reviewed records. Treat results as guesses until checked against the PDF.", async () => {
    const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/extract-candidates`, { method: "POST" });
    replaceAdventurePackageInState(result.package);
    const changes = result.package.candidate_changes || {};
    setStatus(`Candidate extraction complete: locations ${changes.nodes || 0}, tables ${changes.tables || 0}, foes ${changes.foes || 0}, classes ${changes.classes || 0}, items ${changes.items || 0}, states ${changes.states || 0}, rules ${changes.rules || 0}, procedures ${changes.procedures || 0}.`);
    redraw();
  }));
  panel.append(detailGrid, saveDetails, extractRow, renderAdventurePackageReviewBrowser(pkg), renderAdventurePackageNodeEditor(pkg, redraw), renderAdventurePackageRecordEditor(pkg, redraw), renderAdventurePackageSectionEditor(pkg, redraw));
  return panel;
}

function packageRecordTitle(kind, record) {
  if (kind === "nodes") return record.title || record.id || "Untitled location";
  if (kind === "tables") return record.title || record.id || "Untitled table";
  if (kind === "procedures") return record.title || record.id || "Untitled procedure";
  if (kind === "states") return record.name || record.title || record.id || "Untitled state";
  if (kind === "rules") return record.name || record.title || record.id || "Untitled rule";
  return record.name || record.title || record.id || "Untitled record";
}

function packageRecordSingular(kind) {
  return {
    foes: "foe",
    items: "item",
    classes: "class",
    states: "state",
    rules: "rule",
    tables: "table",
    trackers: "tracker",
    procedures: "procedure",
  }[kind] || "record";
}

const PACKAGE_REVIEW_GROUPS = [
  ["nodes", "Locations"],
  ["tables", "Tables"],
  ["foes", "Foes"],
  ["items", "Items"],
  ["classes", "Classes"],
  ["states", "States"],
  ["rules", "Rules"],
  ["procedures", "Procedures"],
  ["ignored_records", "Ignored"],
];

function packageRecordId(record) {
  return String(record?.id || "");
}

function normalizePackageRecordForKind(record, targetKind, sourceKind = "") {
  const copy = { ...(record || {}) };
  copy.original_extraction = copy.original_extraction || {
    detected_as: sourceKind || targetKind,
    source_text: copy.source_text || copy.player_text || copy.notes || "",
  };
  copy.corrected_type = targetKind;
  copy.review_status = copy.review_status || "needs_pdf_check";
  if (targetKind === "nodes") {
    copy.type = copy.type || "location";
    copy.title = copy.title || copy.name || copy.id || "Untitled location";
    copy.player_text = copy.player_text || copy.source_text || copy.notes || "";
    copy.branches = Array.isArray(copy.branches) ? copy.branches : [];
  } else if (targetKind === "tables") {
    copy.title = copy.title || copy.name || copy.id || "Untitled table";
    copy.rows = Array.isArray(copy.rows) && copy.rows.length ? copy.rows : [{ result: "candidate", text: copy.source_text || copy.notes || "" }];
  } else if (targetKind === "procedures") {
    copy.title = copy.title || copy.name || copy.id || "Untitled procedure";
    copy.steps = Array.isArray(copy.steps) && copy.steps.length ? copy.steps : [{ op: "show_choice" }];
  } else if (targetKind === "states") {
    copy.name = copy.name || copy.title || copy.id || "Untitled state";
    copy.applies_to = copy.applies_to || "character";
    copy.modifiers = Array.isArray(copy.modifiers) ? copy.modifiers : [];
  } else if (targetKind === "rules") {
    copy.name = copy.name || copy.title || copy.id || "Untitled rule";
    copy.scope = copy.scope || "module";
  } else {
    copy.name = copy.name || copy.title || copy.id || "Untitled record";
  }
  copy.source_page = Number(copy.source_page || 0);
  return copy;
}

function packageRecordSubtitle(kind, record) {
  const bits = [];
  if (record.type) bits.push(record.type);
  if (record.source_page !== undefined) bits.push(`page ${record.source_page}`);
  if (record.review_status) bits.push(String(record.review_status).replaceAll("_", " "));
  if (kind === "tables" && record.dice) bits.push(record.dice);
  if (kind === "nodes" && Array.isArray(record.branches) && record.branches.length) bits.push(`${record.branches.length} branch(es)`);
  if (kind === "tables" && Array.isArray(record.rows)) bits.push(`${record.rows.length} row(s)`);
  return bits.join(" · ") || "candidate";
}

function packageNodeLinkedRecords(pkg, node) {
  const nodeId = packageRecordId(node);
  const text = `${node?.player_text || ""} ${node?.app_notes || ""} ${node?.source_text || ""}`.toLowerCase();
  const linkedById = (records, ids = []) => (records || []).filter((record) => ids.includes(record.id) || ids.includes(record.name));
  const linkedByText = (records) => (records || []).filter((record) => {
    const name = String(record.name || record.title || record.id || "").toLowerCase();
    return name && name.length > 2 && text.includes(name);
  });
  const mapPins = [];
  for (const map of pkg.maps || []) {
    for (const pin of map.pins || []) {
      if (pin.node_id === nodeId || pin.id === node?.map_pin_id) mapPins.push({ ...pin, map_title: map.title, asset_url: map.asset_url, asset_exists: map.asset_exists });
    }
  }
  return {
    foes: [...new Map([...linkedById(pkg.foes, node.foe_ids || []), ...linkedByText(pkg.foes)].map((item) => [item.id || item.name, item])).values()],
    items: [...new Map([...linkedById(pkg.items, node.item_ids || []), ...linkedByText(pkg.items)].map((item) => [item.id || item.name, item])).values()],
    procedures: [...new Map([...linkedById(pkg.procedures, node.procedure_ids || []), ...linkedByText(pkg.procedures)].map((item) => [item.id || item.title, item])).values()],
    mapPins,
  };
}

function renderMiniRecordList(title, records, emptyText, titleHint) {
  const box = el("div", "modern-location-preview-box");
  box.appendChild(el("strong", "", title));
  box.title = titleHint || "";
  if (!records.length) {
    box.appendChild(el("p", "muted", emptyText));
    return box;
  }
  const list = el("ul", "modern-warning-list");
  for (const record of records) {
    list.appendChild(el("li", "", `${record.name || record.title || record.label || record.id}${record.source_page !== undefined ? ` · page ${record.source_page}` : ""}`));
  }
  box.appendChild(list);
  return box;
}

function renderLocationPreview(pkg, node) {
  const linked = packageNodeLinkedRecords(pkg, node);
  const preview = el("div", "modern-location-preview");
  preview.appendChild(el("h4", "", `Location Preview: ${node.title || node.id || "Untitled"}`));
  const meta = el("div", "modern-chip-row");
  for (const [label, value] of [
    ["id", node.id],
    ["type", node.type || "location"],
    ["page", node.source_page],
    ["review", node.review_status || "needs_pdf_check"],
  ]) {
    if (value !== undefined && value !== "") meta.appendChild(el("span", "modern-tag", `${label}: ${value}`));
  }
  preview.appendChild(meta);
  const stage = el("div", "modern-location-preview-stage");
  const art = el("div", "modern-location-preview-art");
  const pinWithImage = linked.mapPins.find((pin) => pin.asset_exists && pin.asset_url);
  if (pinWithImage) {
    const img = document.createElement("img");
    img.src = pinWithImage.asset_url;
    img.alt = `${pinWithImage.map_title || "Map"} linked to ${node.title || node.id}`;
    img.title = "Map image linked by a package pin. This is the full map asset for now; future work can crop to the pin rectangle.";
    art.appendChild(img);
  } else {
    art.appendChild(el("span", "muted", "No linked room graphic or map pin image yet."));
  }
  const prose = el("div", "modern-location-preview-prose");
  prose.append(el("strong", "", "Player description"), el("p", "muted", node.player_text || "No reviewed player-facing description yet."));
  prose.append(el("strong", "", "App / rules notes"), el("p", "muted", node.app_notes || "No app notes yet. Add saves, rolls, rewards, branch rules, or automation notes here."));
  stage.append(art, prose);
  preview.appendChild(stage);
  const grid = el("div", "modern-location-preview-grid");
  grid.append(
    renderMiniRecordList("Foes", linked.foes, "No linked foes. If a foe appears in the text, link or move it into Foes before conversion.", "Foes linked by node foe_ids or detected by name in the location text."),
    renderMiniRecordList("Items / Rewards", linked.items, "No linked items or rewards. Add item_ids or move detected records into Items.", "Items linked by node item_ids or detected by name in the location text."),
    renderMiniRecordList("Exits / Choices", node.branches || [], "No exits or choices recorded yet.", "Branches are printed choices, scene jumps, doors, save outcomes, routes, or endings."),
    renderMiniRecordList("Procedures", linked.procedures, "No linked procedures. Add procedure_ids for saves, rolls, table lookups, or special handling.", "Procedures linked by node procedure_ids or detected by title in the location text."),
    renderMiniRecordList("Map Pins", linked.mapPins, "No map pin linked to this location yet.", "Pins connect this node id to a package map image.")
  );
  preview.appendChild(grid);
  return preview;
}

function packageRecordUsage(pkg, kind, record) {
  const recordId = String(record?.id || record?.name || "").toLowerCase();
  const recordName = String(record?.name || record?.title || record?.label || "").toLowerCase();
  if (!recordId && !recordName) return [];
  const idField = kind === "foes" ? "foe_ids" : kind === "items" ? "item_ids" : kind === "procedures" ? "procedure_ids" : "";
  return (pkg.nodes || []).filter((node) => {
    const ids = Array.isArray(node[idField]) ? node[idField].map((item) => String(item).toLowerCase()) : [];
    const text = `${node.player_text || ""} ${node.app_notes || ""} ${node.source_text || ""}`.toLowerCase();
    return ids.includes(recordId) || ids.includes(recordName) || (recordName && recordName.length > 2 && text.includes(recordName));
  });
}

function renderPackageRecordPreview(pkg, kind, record) {
  const preview = el("div", "modern-package-record-preview");
  const title = packageRecordTitle("", record);
  preview.appendChild(el("h4", "", `${PACKAGE_REVIEW_GROUPS.find(([key]) => key === kind)?.[1] || "Record"} Preview: ${title}`));
  const meta = el("div", "modern-chip-row");
  for (const [label, value] of [
    ["id", record.id],
    ["page", record.source_page],
    ["review", record.review_status],
    ["dice", record.dice],
  ]) {
    if (value !== undefined && value !== "") meta.appendChild(el("span", "modern-tag", `${label}: ${value}`));
  }
  preview.appendChild(meta);
  const grid = el("div", "modern-location-preview-grid");
  const notes = el("div", "modern-location-preview-box");
  notes.append(el("strong", "", "Notes / source text"), el("p", "muted", record.notes || record.source_text || "No notes recorded yet."));
  grid.appendChild(notes);
  if (kind === "tables") {
    grid.appendChild(renderMiniRecordList("Rows", record.rows || [], "No rows recorded yet.", "Rows should preserve the printed dice result and reviewed outcome text."));
  } else if (kind === "procedures") {
    grid.appendChild(renderMiniRecordList("Steps", record.steps || [], "No procedure steps recorded yet.", "Procedure steps use allowlisted app operations only; no script code is executed."));
  } else if (kind === "trackers") {
    const tracker = el("div", "modern-location-preview-box");
    tracker.append(
      el("strong", "", "Tracker range"),
      el("p", "muted", `Initial ${record.initial ?? 0} · min ${record.minimum ?? "none"} · max ${record.maximum ?? "none"}`)
    );
    grid.appendChild(tracker);
  }
  const usageKinds = ["foes", "items", "procedures"];
  if (usageKinds.includes(kind)) {
    const usedBy = packageRecordUsage(pkg, kind, record);
    grid.appendChild(renderMiniRecordList("Used By Locations", usedBy, "No reviewed location links this record yet.", "Locations can link this record by id or can be detected by name in location text."));
  }
  const raw = el("details", "modern-raw-details");
  raw.append(el("summary", "", "Raw JSON"), el("pre", "modern-json-preview", JSON.stringify(record, null, 2)));
  preview.append(grid, raw);
  return preview;
}

function packageRecordDetail(pkg, kind, record, redraw) {
  const wrap = el("div", "modern-package-detail");
  if (kind === "nodes") wrap.appendChild(renderLocationPreview(pkg, record));
  else wrap.appendChild(renderPackageRecordPreview(pkg, kind, record));
  wrap.appendChild(el("h4", "", packageRecordTitle("", record)));
  const meta = el("div", "modern-chip-row");
  for (const key of ["id", "type", "source_page", "review_status", "dice"]) {
    if (record[key] !== undefined && record[key] !== "") meta.appendChild(el("span", "modern-tag", `${key}: ${record[key]}`));
  }
  wrap.appendChild(meta);
  const textKeys = ["player_text", "description", "notes", "app_notes", "source_text"];
  for (const key of textKeys) {
    if (record[key]) {
      wrap.appendChild(el("strong", "", key.replaceAll("_", " ")));
      wrap.appendChild(el("p", "muted", String(record[key])));
    }
  }
  if (Array.isArray(record.branches) && record.branches.length) {
    wrap.appendChild(el("strong", "", "branches"));
    const list = el("ul", "modern-warning-list");
    for (const branch of record.branches) list.appendChild(el("li", "", `${branch.label || "Branch"} -> ${branch.to || "?"}${branch.condition ? ` (${branch.condition})` : ""}`));
    wrap.appendChild(list);
  }
  if (Array.isArray(record.rows) && record.rows.length) {
    wrap.appendChild(el("strong", "", "rows"));
    const list = el("ul", "modern-warning-list");
    for (const row of record.rows.slice(0, 20)) list.appendChild(el("li", "", `${row.result || "?"}: ${row.text || row.description || JSON.stringify(row)}`));
    wrap.appendChild(list);
  }
  if (Array.isArray(record.steps) && record.steps.length) {
    wrap.appendChild(el("strong", "", "procedure steps"));
    const list = el("ul", "modern-warning-list");
    for (const step of record.steps) list.appendChild(el("li", "", step.op || JSON.stringify(step)));
    wrap.appendChild(list);
  }
  const json = document.createElement("pre");
  json.className = "modern-json-preview";
  json.textContent = JSON.stringify(record, null, 2);
  wrap.append(renderPackageRecordCorrectionControls(pkg, kind, record, redraw), json);
  return wrap;
}

function renderPackageRecordCorrectionControls(pkg, kind, record, redraw) {
  const panel = el("div", "modern-package-correction-panel");
  panel.appendChild(el("strong", "", "Review correction"));
  const title = input("text", `record-title-${pkg.package_id}-${kind}-${packageRecordId(record)}`, "Correct the displayed title/name for this record.");
  title.value = packageRecordTitle(kind, record);
  const page = input("number", `record-page-${pkg.package_id}-${kind}-${packageRecordId(record)}`, "Correct the source PDF page for this record.");
  page.min = "0";
  page.step = "1";
  page.value = String(record.source_page || 0);
  const status = select(`record-status-${pkg.package_id}-${kind}-${packageRecordId(record)}`, "Review status for this candidate record.", [
    ["needs_pdf_check", "Needs PDF check"],
    ["draft", "Draft"],
    ["checked", "Checked"],
    ["ready_for_manifest", "Ready for manifest"],
    ["wrong_type", "Wrong type"],
    ["ignored", "Ignored"],
  ]);
  status.value = record.review_status || "needs_pdf_check";
  const target = select(`record-target-${pkg.package_id}-${kind}-${packageRecordId(record)}`, "Move this record to another imported-content list if it was misclassified.", PACKAGE_REVIEW_GROUPS.map(([key, label]) => [key, label]));
  target.value = kind;
  const reason = input("text", `record-reason-${pkg.package_id}-${kind}-${packageRecordId(record)}`, "Optional correction note explaining why this record was moved or ignored.");
  reason.value = "";
  panel.append(field("Title / Name", title), field("Source Page", page), field("Review Status", status), field("Move To", target), field("Correction Note", reason));
  const row = actions();
  const savePayload = async (payload, message) => {
    const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    replaceAdventurePackageInState(result.package);
    setStatus(message);
    redraw();
  };
  row.append(
    button("Save Correction", "Save title/name, source page, review status, and optional correction note in this list.", async () => {
      const records = [...(pkg[kind] || [])];
      const next = records.map((item) => {
        if (packageRecordId(item) !== packageRecordId(record)) return item;
        const copy = { ...item, source_page: Number(page.value || 0), review_status: status.value };
        if (kind === "nodes" || kind === "tables" || kind === "procedures") copy.title = title.value;
        else copy.name = title.value;
        if (reason.value.trim()) copy.correction_note = reason.value.trim();
        return copy;
      });
      await savePayload({ [kind]: next }, `Saved correction for ${title.value}.`);
    }),
    button("Move Record", "Move this record into the selected list while preserving original extraction metadata.", async () => {
      if (target.value === kind) throw new Error("Choose a different target list before moving.");
      const sourceRecords = (pkg[kind] || []).filter((item) => packageRecordId(item) !== packageRecordId(record));
      const moved = normalizePackageRecordForKind(
        {
          ...record,
          source_page: Number(page.value || 0),
          correction_note: reason.value.trim() || `Moved from ${kind} to ${target.value}.`,
        },
        target.value,
        kind
      );
      if (target.value === "nodes" || target.value === "tables" || target.value === "procedures") moved.title = title.value;
      else moved.name = title.value;
      const targetRecords = [...(pkg[target.value] || []).filter((item) => packageRecordId(item) !== packageRecordId(moved)), moved];
      await savePayload({ [kind]: sourceRecords, [target.value]: targetRecords }, `Moved ${title.value} to ${PACKAGE_REVIEW_GROUPS.find(([key]) => key === target.value)?.[1] || target.value}.`);
    }),
    button("Mark Wrong / Ignore", "Remove this candidate from the active list and preserve it under ignored_records for later importer improvement.", async () => {
      const sourceRecords = (pkg[kind] || []).filter((item) => packageRecordId(item) !== packageRecordId(record));
      const ignored = {
        ...record,
        name: title.value,
        title: title.value,
        source_page: Number(page.value || 0),
        review_status: "ignored",
        corrected_type: "ignored_records",
        ignored_reason: reason.value.trim() || "Marked wrong or not useful during PDF review.",
        original_list: kind,
        original_extraction: record.original_extraction || {
          detected_as: kind,
          source_text: record.source_text || record.player_text || record.notes || "",
        },
      };
      const ignoredRecords = [...(pkg.ignored_records || []).filter((item) => packageRecordId(item) !== packageRecordId(ignored)), ignored];
      await savePayload({ [kind]: sourceRecords, ignored_records: ignoredRecords }, `Ignored ${title.value}.`);
    }, "danger-button")
  );
  panel.appendChild(row);
  return panel;
}

function renderAdventurePackageReviewBrowser(pkg) {
  const panel = el("div", "modern-package-browser");
  panel.appendChild(el("h4", "", "Imported Content Browser"));
  panel.appendChild(el("p", "muted", "These are candidate or reviewed records from the package. Click a row to inspect details; check the PDF before marking anything ready for manifest conversion."));
  const groups = PACKAGE_REVIEW_GROUPS.map(([key, label]) => [key, label, pkg[key] || []]);
  let active = groups.find(([, , records]) => records.length)?.[0] || "nodes";
  let selected = null;
  const tabs = el("div", "modern-package-browser-tabs");
  const body = el("div", "modern-package-browser-body");
  const draw = () => {
    tabs.replaceChildren();
    body.replaceChildren();
    for (const [key, label, records] of groups) {
      const tab = button(`${label} (${records.length})`, `Show imported ${label.toLowerCase()} detected or edited in this package.`, () => {
        active = key;
        selected = null;
        draw();
      }, key === active ? "" : "secondary");
      tabs.appendChild(tab);
    }
    const [, label, records] = groups.find(([key]) => key === active) || groups[0];
    const activeSummary = el("div", "modern-package-browser-active", `${label} (${records.length})`);
    activeSummary.title = `Currently reviewing ${label.toLowerCase()} extracted or edited for this package.`;
    const list = el("div", "modern-package-record-list");
    const detail = el("div", "modern-package-record-detail");
    body.appendChild(activeSummary);
    list.appendChild(el("strong", "", `${label} (${records.length})`));
    if (!records.length) {
      list.appendChild(el("p", "muted", `No ${label.toLowerCase()} recorded yet. Use Extract Candidate Lists or add records manually in the editor below.`));
      detail.append(
        el("strong", "", `${label} detail`),
        el("p", "muted", `No ${label.toLowerCase()} are currently recorded in this package. If the extractor put one in the wrong list, open that source list, select the record, choose Move To ${label}, then press Move Record.`)
      );
    } else {
      const selectedRecord = selected || records[0];
      selected = selectedRecord;
      for (const record of records) {
        const item = document.createElement("button");
        item.type = "button";
        item.className = `modern-package-record-item${record === selectedRecord ? " selected" : ""}`;
        item.title = "Inspect this imported candidate. Confirm details against the PDF before using it in play.";
        item.append(el("strong", "", packageRecordTitle(active, record)), el("span", "muted", packageRecordSubtitle(active, record)));
        item.addEventListener("click", () => {
          selected = record;
          draw();
        });
        list.appendChild(item);
      }
      try {
        detail.appendChild(packageRecordDetail(pkg, active, selectedRecord, () => renderPage()));
      } catch (error) {
        detail.append(
          el("strong", "", `${label} detail`),
          el("p", "warning-text", `Could not preview this record: ${error?.message || "unknown render error"}`),
          el("pre", "modern-json-preview", JSON.stringify(selectedRecord, null, 2))
        );
      }
    }
    body.append(list, detail);
  };
  panel.append(tabs, body);
  draw();
  return panel;
}

function renderAdventurePackageNodeEditor(pkg, redraw) {
  const panel = el("div", "modern-package-node-editor");
  panel.appendChild(el("h4", "", "Location Editor"));
  panel.appendChild(el("p", "muted", "Create or edit a reviewed location/node. This editor is intentionally reusable for the future Create Module screen: title, description, app notes, linked foes/items/procedures, choices, and map-pin references all live in the package node."));
  const nodes = Array.isArray(pkg.nodes) ? pkg.nodes : [];
  const selectedNodeId = select(`node-select-${pkg.package_id}`, "Choose an existing reviewed location to edit, or choose New Location to create one.", [["", "New Location"], ...nodes.map((node) => [node.id, `${node.title || node.id} (${node.type || "location"})`])]);
  const editMount = el("div", "modern-location-editor-mount");
  const drawEditor = () => {
    editMount.replaceChildren();
    const existing = nodes.find((node) => node.id === selectedNodeId.value) || {};
    const id = input("text", `node-id-${pkg.package_id}`, "Lowercase id for this room, scene, hex, or location. Existing ids are used by map pins and future adventure conversion.");
    id.value = existing.id || "";
    const type = select(`node-type-${pkg.package_id}`, "What kind of reviewed content this node represents.", [
      ["room", "Room"],
      ["scene", "Scene"],
      ["location", "Location"],
      ["hex", "Hex"],
      ["camp", "Camp"],
      ["settlement", "Settlement"],
      ["ending", "Ending"],
    ]);
    type.value = existing.type || "location";
    const title = input("text", `node-title-${pkg.package_id}`, "Player-facing location title.");
    title.value = existing.title || "";
    const page = input("number", `node-page-${pkg.package_id}`, "PDF page number used as source reference.");
    page.min = "0";
    page.step = "1";
    page.value = String(existing.source_page || 0);
    const reviewStatus = select(`node-review-${pkg.package_id}`, "Node review status. Use Ready only after PDF text, choices, foes, rewards, and map link have been checked.", [
      ["needs_pdf_check", "Needs PDF check"],
      ["draft", "Draft"],
      ["checked", "Checked"],
      ["ready_for_manifest", "Ready for manifest"],
      ["wrong_type", "Wrong type"],
      ["ignored", "Ignored"],
    ]);
    reviewStatus.value = existing.review_status || "needs_pdf_check";
    const text = textarea(`node-text-${pkg.package_id}`, "Reviewed player-facing narrative/location text for this node.", 5);
    text.value = existing.player_text || "";
    const appNotes = textarea(`node-notes-${pkg.package_id}`, "App notes: saves, rolls, foes, rewards, choices, rules handling, or branch requirements.", 4);
    appNotes.value = existing.app_notes || "";
    const foeIds = input("text", `node-foes-${pkg.package_id}`, "Comma-separated foe ids or names linked to this location. Use ids from the Foes list.");
    foeIds.value = (existing.foe_ids || []).join(", ");
    const itemIds = input("text", `node-items-${pkg.package_id}`, "Comma-separated item/reward ids or names linked to this location. Use ids from the Items list.");
    itemIds.value = (existing.item_ids || []).join(", ");
    const procedureIds = input("text", `node-procedures-${pkg.package_id}`, "Comma-separated procedure ids linked to this location. Use ids from the Procedures list.");
    procedureIds.value = (existing.procedure_ids || []).join(", ");
    const mapPinId = input("text", `node-map-pin-${pkg.package_id}`, "Optional map pin id linked to this location. Map pins can also link by node id.");
    mapPinId.value = existing.map_pin_id || "";
    const branches = textarea(`node-branches-${pkg.package_id}`, "JSON array of exits/choices, e.g. [{\"label\":\"Open the north door\",\"to\":\"room-2\",\"condition\":\"door choice\"}].", 4);
    branches.value = JSON.stringify(existing.branches || [], null, 2);
    const form = el("div", "modern-package-node-form");
    form.append(
      field("Node Id", id),
      field("Type", type),
      field("Title", title),
      field("Source Page", page),
      field("Review Status", reviewStatus),
      field("Linked Foes", foeIds),
      field("Linked Items", itemIds),
      field("Linked Procedures", procedureIds),
      field("Map Pin Id", mapPinId),
      field("Player Description", text),
      field("App / Rules Notes", appNotes),
      field("Exits / Choices JSON", branches)
    );
    const row = actions();
    row.append(
      button("Save Location", "Save this reviewed location into package.json. This does not make it playable until conversion creates adventure.json.", async () => {
        const nodeId = id.value.trim();
        if (!nodeId) throw new Error("Node Id is required.");
        const nextNode = {
          ...existing,
          id: nodeId,
          type: type.value,
          title: title.value.trim() || nodeId,
          source_page: Number(page.value || 0),
          player_text: text.value,
          app_notes: appNotes.value,
          foe_ids: commaList(foeIds.value),
          item_ids: commaList(itemIds.value),
          procedure_ids: commaList(procedureIds.value),
          map_pin_id: mapPinId.value.trim(),
          branches: parseJsonArrayField(branches, "Exits / Choices JSON"),
          review_status: reviewStatus.value,
        };
        const nextNodes = nodes.filter((item) => item.id !== (existing.id || nodeId));
        nextNodes.push(nextNode);
        const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/review`, {
          method: "POST",
          body: JSON.stringify({ nodes: nextNodes }),
        });
        replaceAdventurePackageInState(result.package);
        setStatus(`Saved location ${nodeId}.`);
        redraw();
      }),
      button("Clear Editor", "Clear the editor so you can create a new location.", async () => {
        selectedNodeId.value = "";
        drawEditor();
      }, "secondary")
    );
    editMount.append(form, row);
    if (existing.id) editMount.appendChild(renderLocationPreview(pkg, existing));
  };
  selectedNodeId.addEventListener("change", drawEditor);
  panel.appendChild(field("Edit Location", selectedNodeId));
  panel.appendChild(editMount);
  drawEditor();
  const nodeList = el("div", "modern-package-node-list");
  if (!nodes.length) nodeList.appendChild(el("p", "muted", "No reviewed nodes yet. Add one from the source PDF before converting this package to a playable module."));
  for (const node of nodes) {
    const row = el("details", "modern-package-node-card");
    row.appendChild(el("summary", "", `${node.id || "node"} · ${node.title || "Untitled"} · ${node.type || "room"} · page ${node.source_page ?? "?"}`));
    row.append(
      modernStatusRow("Review", node.review_status || "draft", "Node-level review status. ready_for_manifest means the source page and branch logic have been checked."),
      modernStatusRow("Branches", `${(node.branches || []).length}`, "Branches represent printed choices, save results, doors, routes, or endings."),
      el("p", "muted", node.player_text || "No player text recorded."),
      el("p", "muted", node.app_notes || "No app notes recorded.")
    );
    nodeList.appendChild(row);
  }
  panel.appendChild(nodeList);
  return panel;
}

function packageRecordKnownKeys(kind) {
  if (kind === "tables") return ["id", "title", "source_page", "dice", "rows", "review_status", "source_text"];
  if (kind === "trackers") return ["id", "label", "initial", "minimum", "maximum", "source_page"];
  if (kind === "procedures") return ["id", "title", "source_page", "steps", "review_status", "source_text"];
  if (kind === "items") return ["id", "name", "source_page", "description", "modifiers", "states_applied", "sale_price_gp", "sellable", "buyable", "notes", "source_text", "review_status"];
  if (kind === "states") return ["id", "name", "source_page", "description", "applies_to", "duration", "modifiers", "removal", "notes", "source_text", "review_status"];
  if (kind === "rules") return ["id", "name", "source_page", "description", "scope", "trigger", "effect", "notes", "source_text", "review_status"];
  return ["id", "name", "source_page", "notes", "source_text", "review_status"];
}

function packageRecordExtraJson(kind, record) {
  const known = new Set(packageRecordKnownKeys(kind));
  const extra = {};
  for (const [key, value] of Object.entries(record || {})) {
    if (!known.has(key)) extra[key] = value;
  }
  return JSON.stringify(extra, null, 2);
}

function parseJsonObjectField(control, label) {
  try {
    const parsed = control.value.trim() ? JSON.parse(control.value) : {};
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("Expected object");
    return parsed;
  } catch (error) {
    throw new Error(`${label} must be a JSON object: ${error.message}`);
  }
}

function renderAdventurePackageRecordEditor(pkg, redraw) {
  const panel = el("div", "modern-package-record-editor");
  panel.appendChild(el("h4", "", "Imported Record Editor"));
  panel.appendChild(el("p", "muted", "Review and edit module-local records extracted from a PDF. Foes, items, classes, tables, trackers, and procedures remain package data until a playable manifest explicitly uses them."));
  const editableKinds = [
    ["foes", "Foes"],
    ["items", "Items"],
    ["classes", "Classes"],
    ["states", "States"],
    ["rules", "Rules"],
    ["tables", "Tables"],
    ["trackers", "Trackers"],
    ["procedures", "Procedures"],
  ];
  const kindSelect = select(`record-kind-${pkg.package_id}`, "Choose which imported record type to edit. Use Move Record in the candidate browser when the importer put something in the wrong list.", editableKinds);
  const recordSelectMount = el("div", "modern-package-record-editor-mount");
  const editorMount = el("div", "modern-package-record-editor-mount");
  const drawRecordEditor = () => {
    recordSelectMount.replaceChildren();
    editorMount.replaceChildren();
    const kind = kindSelect.value;
    const records = Array.isArray(pkg[kind]) ? pkg[kind] : [];
    const recordSelect = select(`record-select-${pkg.package_id}-${kind}`, "Choose an existing record to edit, or choose New Record to create one.", [["", "New Record"], ...records.map((record) => [record.id || record.name || record.title || record.label, packageRecordTitle("", record)])]);
    recordSelectMount.appendChild(field("Edit Record", recordSelect));
    const drawForm = () => {
      editorMount.replaceChildren();
      const recordKey = recordSelect.value;
      const existing = records.find((record) => (record.id || record.name || record.title || record.label) === recordKey) || {};
      const id = input("text", `record-id-${pkg.package_id}-${kind}`, "Stable lowercase id for links from locations, procedures, tables, and future adventure conversion.");
      id.value = existing.id || "";
      const nameLabel = kind === "tables" || kind === "procedures" ? "Title" : kind === "trackers" ? "Label" : "Name";
      const name = input("text", `record-name-${pkg.package_id}-${kind}`, `${nameLabel} shown in the review workspace.`);
      name.value = existing.title || existing.label || existing.name || "";
      const page = input("number", `record-page-${pkg.package_id}-${kind}`, "PDF page number used as source reference.");
      page.min = "0";
      page.step = "1";
      page.value = String(existing.source_page || 0);
      const reviewStatus = select(`record-review-${pkg.package_id}-${kind}`, "Review status. Use Ready only after checking the source PDF and required app behavior.", [
        ["candidate", "Candidate"],
        ["needs_pdf_check", "Needs PDF check"],
        ["draft", "Draft"],
        ["checked", "Checked"],
        ["ready_for_manifest", "Ready for manifest"],
        ["wrong_type", "Wrong type"],
        ["ignored", "Ignored"],
      ]);
      reviewStatus.value = existing.review_status || "needs_pdf_check";
      const notes = textarea(`record-notes-${pkg.package_id}-${kind}`, "Reviewer notes, source text, rules handling, or explanation for this record.", 4);
      notes.value = existing.notes || existing.source_text || "";
      const extra = textarea(`record-extra-${pkg.package_id}-${kind}`, "Optional extra JSON object for module-specific fields. Use this for stats, prices, tags, equipment traits, class notes, or other data not covered above.", 5);
      extra.value = packageRecordExtraJson(kind, existing);
      const form = el("div", "modern-package-node-form");
      form.append(field("Id", id), field(nameLabel, name), field("Source Page", page));
      if (kind !== "trackers") form.appendChild(field("Review Status", reviewStatus));
      if (kind === "tables") {
        const dice = input("text", `record-dice-${pkg.package_id}`, "Dice expression printed for this table, for example d6 or 2d6.");
        dice.value = existing.dice || "";
        const rows = textarea(`record-rows-${pkg.package_id}`, "Rows JSON array. Each row should include at least result and the reviewed outcome text.", 7);
        rows.value = JSON.stringify(existing.rows || [], null, 2);
        form.append(field("Dice", dice), field("Rows JSON", rows), field("Source / Notes", notes), field("Extra JSON", extra));
        editorMount.append(form, renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, () => ({
          ...parseJsonObjectField(extra, "Extra JSON"),
          id: id.value.trim(),
          title: name.value.trim() || id.value.trim(),
          source_page: Number(page.value || 0),
          dice: dice.value.trim(),
          rows: parseJsonArrayField(rows, "Rows JSON"),
          review_status: reviewStatus.value,
          source_text: notes.value,
        })));
      } else if (kind === "procedures") {
        const steps = textarea(`record-steps-${pkg.package_id}`, "Procedure steps JSON array using allowlisted operations such as roll_table, test_save, spawn_foes, grant_item, branch_if, or transition_to_node.", 7);
        steps.value = JSON.stringify(existing.steps || [], null, 2);
        form.append(field("Steps JSON", steps), field("Source / Notes", notes), field("Extra JSON", extra));
        editorMount.append(form, renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, () => ({
          ...parseJsonObjectField(extra, "Extra JSON"),
          id: id.value.trim(),
          title: name.value.trim() || id.value.trim(),
          source_page: Number(page.value || 0),
          steps: parseJsonArrayField(steps, "Steps JSON"),
          review_status: reviewStatus.value,
          source_text: notes.value,
        })));
      } else if (kind === "trackers") {
        const initial = input("number", `record-initial-${pkg.package_id}`, "Starting tracker value.");
        const minimum = input("number", `record-min-${pkg.package_id}`, "Optional minimum tracker value.");
        const maximum = input("number", `record-max-${pkg.package_id}`, "Optional maximum tracker value.");
        initial.value = String(existing.initial ?? 0);
        minimum.value = existing.minimum ?? "";
        maximum.value = existing.maximum ?? "";
        form.append(field("Initial", initial), field("Minimum", minimum), field("Maximum", maximum), field("Notes", notes), field("Extra JSON", extra));
        editorMount.append(form, renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, () => ({
          ...parseJsonObjectField(extra, "Extra JSON"),
          id: id.value.trim(),
          label: name.value.trim() || id.value.trim(),
          source_page: Number(page.value || 0),
          initial: Number(initial.value || 0),
          ...(minimum.value !== "" ? { minimum: Number(minimum.value) } : {}),
          ...(maximum.value !== "" ? { maximum: Number(maximum.value) } : {}),
        })));
      } else if (kind === "items") {
        const description = textarea(`record-description-${pkg.package_id}-${kind}`, "Player-facing item description: what it is and what it does in this module.", 3);
        description.value = existing.description || "";
        const modifiers = textarea(`record-modifiers-${pkg.package_id}-${kind}`, "JSON array of modifiers this item applies, for example attack, defense, saves, spell effects, or inventory traits.", 4);
        modifiers.value = JSON.stringify(existing.modifiers || [], null, 2);
        const statesApplied = input("text", `record-states-${pkg.package_id}-${kind}`, "Comma-separated state ids applied by this item, if any.");
        statesApplied.value = (existing.states_applied || []).join(", ");
        const salePrice = input("number", `record-sale-price-${pkg.package_id}-${kind}`, "Sale price in gp if the PDF gives one. Leave blank if not sellable or unknown.");
        salePrice.min = "0";
        salePrice.step = "1";
        salePrice.value = existing.sale_price_gp ?? "";
        const sellable = input("checkbox", `record-sellable-${pkg.package_id}-${kind}`, "Whether this item can be sold under the module/PDF rules.");
        sellable.checked = Boolean(existing.sellable);
        const buyable = input("checkbox", `record-buyable-${pkg.package_id}-${kind}`, "Whether this item can be bought under the module/PDF rules.");
        buyable.checked = Boolean(existing.buyable);
        const sellableRow = el("label", "modern-check-row");
        sellableRow.title = sellable.title;
        sellableRow.append(sellable, el("span", "", "Sellable"));
        const buyableRow = el("label", "modern-check-row");
        buyableRow.title = buyable.title;
        buyableRow.append(buyable, el("span", "", "Buyable"));
        form.append(field("Description", description), field("Modifiers JSON", modifiers), field("States Applied", statesApplied), field("Sale Price gp", salePrice), sellableRow, buyableRow, field("Notes / Source Text", notes), field("Extra JSON", extra));
        editorMount.append(form, renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, () => ({
          ...parseJsonObjectField(extra, "Extra JSON"),
          id: id.value.trim(),
          name: name.value.trim() || id.value.trim(),
          source_page: Number(page.value || 0),
          description: description.value,
          modifiers: parseJsonArrayField(modifiers, "Modifiers JSON"),
          states_applied: commaList(statesApplied.value),
          ...(salePrice.value !== "" ? { sale_price_gp: Number(salePrice.value || 0) } : {}),
          sellable: sellable.checked,
          buyable: buyable.checked,
          notes: notes.value,
          source_text: notes.value,
          review_status: reviewStatus.value,
        })));
      } else if (kind === "states") {
        const description = textarea(`record-description-${pkg.package_id}-${kind}`, "Player-facing state or condition description.", 3);
        description.value = existing.description || "";
        const appliesTo = input("text", `record-applies-${pkg.package_id}-${kind}`, "Who or what this state can apply to, for example character, party, foe, or item.");
        appliesTo.value = existing.applies_to || "";
        const duration = input("text", `record-duration-${pkg.package_id}-${kind}`, "How long this state lasts, using the PDF wording or reviewer summary.");
        duration.value = existing.duration || "";
        const modifiers = textarea(`record-modifiers-${pkg.package_id}-${kind}`, "JSON array of modifiers this state applies. Keep empty until checked against the PDF.", 4);
        modifiers.value = JSON.stringify(existing.modifiers || [], null, 2);
        const removal = textarea(`record-removal-${pkg.package_id}-${kind}`, "How this state is cured, removed, expires, or is replaced.", 3);
        removal.value = existing.removal || "";
        form.append(field("Description", description), field("Applies To", appliesTo), field("Duration", duration), field("Modifiers JSON", modifiers), field("Removal / Cure", removal), field("Notes / Source Text", notes), field("Extra JSON", extra));
        editorMount.append(form, renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, () => ({
          ...parseJsonObjectField(extra, "Extra JSON"),
          id: id.value.trim(),
          name: name.value.trim() || id.value.trim(),
          source_page: Number(page.value || 0),
          description: description.value,
          applies_to: appliesTo.value,
          duration: duration.value,
          modifiers: parseJsonArrayField(modifiers, "Modifiers JSON"),
          removal: removal.value,
          notes: notes.value,
          source_text: notes.value,
          review_status: reviewStatus.value,
        })));
      } else if (kind === "rules") {
        const description = textarea(`record-description-${pkg.package_id}-${kind}`, "Readable summary of the module-local rule.", 3);
        description.value = existing.description || "";
        const scope = input("text", `record-scope-${pkg.package_id}-${kind}`, "Rule scope, for example module, location, combat, travel, campaign, or class.");
        scope.value = existing.scope || "";
        const trigger = textarea(`record-trigger-${pkg.package_id}-${kind}`, "When this rule applies.", 3);
        trigger.value = existing.trigger || "";
        const effect = textarea(`record-effect-${pkg.package_id}-${kind}`, "What the rule changes or requires.", 4);
        effect.value = existing.effect || "";
        form.append(field("Description", description), field("Scope", scope), field("Trigger", trigger), field("Effect", effect), field("Notes / Source Text", notes), field("Extra JSON", extra));
        editorMount.append(form, renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, () => ({
          ...parseJsonObjectField(extra, "Extra JSON"),
          id: id.value.trim(),
          name: name.value.trim() || id.value.trim(),
          source_page: Number(page.value || 0),
          description: description.value,
          scope: scope.value,
          trigger: trigger.value,
          effect: effect.value,
          notes: notes.value,
          source_text: notes.value,
          review_status: reviewStatus.value,
        })));
      } else {
        form.append(field("Notes / Source Text", notes), field("Extra JSON", extra));
        editorMount.append(form, renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, () => ({
          ...parseJsonObjectField(extra, "Extra JSON"),
          id: id.value.trim(),
          name: name.value.trim() || id.value.trim(),
          source_page: Number(page.value || 0),
          notes: notes.value,
          source_text: notes.value,
          review_status: reviewStatus.value,
        })));
      }
      if (existing.id || existing.name || existing.title || existing.label) editorMount.appendChild(renderPackageRecordPreview(pkg, kind, existing));
    };
    recordSelect.addEventListener("change", drawForm);
    drawForm();
  };
  kindSelect.addEventListener("change", drawRecordEditor);
  panel.append(field("Record Type", kindSelect), recordSelectMount, editorMount);
  drawRecordEditor();
  return panel;
}

function renderPackageRecordSaveRow(pkg, kind, records, existing, redraw, buildRecord) {
  const row = actions();
  row.append(
    button("Save Record", "Save this structured package record. This updates package.json only; rules/mechanics still need PDF review before conversion to playable data.", async () => {
      const nextRecord = buildRecord();
      const nextId = String(nextRecord.id || "").trim();
      if (!nextId) throw new Error("Id is required.");
      const existingId = String(existing.id || existing.name || existing.title || existing.label || nextId);
      const nextRecords = records.filter((item) => String(item.id || item.name || item.title || item.label || "") !== existingId && String(item.id || "") !== nextId);
      nextRecords.push(nextRecord);
      const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/review`, {
        method: "POST",
        body: JSON.stringify({ [kind]: nextRecords }),
      });
      replaceAdventurePackageInState(result.package);
      setStatus(`Saved ${packageRecordSingular(kind)} ${nextId}.`);
      redraw();
    }),
    button("Clear Editor", "Clear this editor so you can create a new record.", async () => {
      redraw();
    }, "secondary")
  );
  return row;
}

function renderAdventurePackageSectionEditor(pkg, redraw) {
  const details = document.createElement("details");
  details.className = "modern-package-section-editor";
  const summary = document.createElement("summary");
  summary.textContent = "Advanced structured sections";
  summary.title = "Edit package arrays directly when the importer guessed tables, foes, items, trackers, or procedures. This still saves structured package data, not arbitrary executable code.";
  details.appendChild(summary);
  const fields = [
    ["nodes", "Nodes"],
    ["foes", "Foes"],
    ["classes", "Classes"],
    ["items", "Items"],
    ["states", "States"],
    ["rules", "Rules"],
    ["tables", "Tables"],
    ["trackers", "Trackers"],
    ["procedures", "Procedures"],
    ["ignored_records", "Ignored Records"],
  ];
  const controls = {};
  const grid = el("div", "modern-package-section-grid");
  for (const [key, label] of fields) {
    const control = textarea(`package-${key}-${pkg.package_id}`, `${label} JSON array. Keep source_page/source text references so the PDF can be audited later.`, key === "nodes" ? 12 : 7);
    control.value = JSON.stringify(pkg[key] || [], null, 2);
    controls[key] = control;
    grid.appendChild(field(label, control));
  }
  const row = actions();
  row.appendChild(button("Save Structured Sections", "Save these reviewed arrays to package.json. Procedure steps are sanitized to the allowlisted operation names only.", async () => {
    const payload = {};
    for (const [key, label] of fields) payload[key] = parseJsonArrayField(controls[key], label);
    const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    replaceAdventurePackageInState(result.package);
    setStatus(`Saved structured sections for ${result.package.title}.`);
    redraw();
  }));
  details.append(grid, row);
  return details;
}

function renderAdventurePackageMaps(pkg) {
  const panel = card(
    "Map Review / Pin Locations",
    "Review extracted PDF images or rendered map pages, then click the map to place percent-based markers. Use pin roles to mark rooms, the dungeon entrance, exits, stairs, secrets, objectives, camps, or settlements before converting the package into a playable graph."
  );
  const sourceId = pkg.source?.pdf_assessment_id || pkg.package_id;
  const mapActions = actions();
  mapActions.appendChild(button("Re-extract Maps", "Run the PDF map extractor again for this package. Existing pins are preserved when map ids match. Use this when the package still shows only a manual map slot after a PDF scan/import update.", async () => {
    const result = await api(`/api/adventures/pdf-sources/${encodeURIComponent(sourceId)}/package`, {
      method: "POST",
      body: JSON.stringify({ extract_maps: true }),
    });
    const detail = await api(`/api/adventures/packages/${encodeURIComponent(result.package.package_id)}`);
    replaceAdventurePackageInState(detail.package);
    setStatus(`Re-extracted maps for ${detail.package.title}.`);
    renderPage();
  }, "secondary"));
  panel.appendChild(mapActions);
  const wrap = el("div", "modern-package-map-list");
  if (!(pkg.maps || []).length) {
    wrap.appendChild(el("p", "muted", "No map records yet. Create / Refresh will add a manual map slot when the PDF importer cannot extract a map image."));
    panel.appendChild(wrap);
    return panel;
  }
  for (const map of pkg.maps || []) {
    const cardEl = el("div", "modern-package-map-card");
    cardEl.append(
      el("h4", "", map.title || map.id),
      el("p", "muted", `${map.asset_path || "No asset path"} · page ${map.source_page || "?"} · ${map.asset_exists ? "asset present" : "asset missing"}`)
    );
    if (map.extraction_note) cardEl.appendChild(el("p", "muted", map.extraction_note));
    const preview = el("div", "modern-package-map-preview");
    if (map.asset_exists && map.asset_path) {
      const img = document.createElement("img");
      img.src = map.asset_url || `/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/maps/${encodeURIComponent(String(map.asset_path || "").split("/").pop() || "")}`;
      img.alt = map.title || map.id;
      img.title = "Click the map to fill the pin X/Y percentage fields. Review placement against the source PDF before trusting it in play.";
      preview.appendChild(img);
    } else {
      preview.appendChild(el("span", "muted", `Put a map image at DATA_DIR/Adventures/${pkg.package_id}/${map.asset_path || "maps/manual-map-review-slot_1600x900.png"}`));
    }
    const form = renderAdventurePackagePinForm(pkg, map, preview);
    cardEl.append(preview, form, renderAdventurePackagePins(pkg, map));
    wrap.appendChild(cardEl);
  }
  panel.appendChild(wrap);
  return panel;
}

function renderAdventurePackageArtworkLibrary(pkg) {
  const panel = card(
    "Extracted Artwork Library",
    "Extract all images exposed by the source PDF into this adventure folder for private/local review. The library may include useful art, maps, covers, logos, masks, and tiny page furniture; review before assigning anything in the app."
  );
  const row = actions();
  row.appendChild(button("Extract Artwork Library", "Extract every image exposed by the source PDF into DATA_DIR/Adventures/<module_id>/artwork/extracted. Existing review labels are preserved on re-run.", async () => {
    const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/extract-artwork`, { method: "POST" });
    replaceAdventurePackageInState(result.package);
    const changes = result.package.artwork_changes || {};
    setStatus(`Extracted artwork for ${result.package.title}: ${changes.found ?? result.package.artwork_count ?? 0} found, ${changes.added ?? 0} new.`);
    renderPage();
  }, "secondary"));
  panel.appendChild(row);
  const artwork = pkg.artwork || [];
  if (!artwork.length) {
    panel.appendChild(el("p", "muted", "No extracted artwork yet. Use Extract Artwork Library after creating the package from a PDF."));
    return panel;
  }
  const grid = el("div", "modern-package-artwork-grid");
  for (const item of artwork) {
    const cardEl = el("div", "modern-package-artwork-card");
    const frame = el("figure", "modern-package-artwork-frame");
    if (item.asset_exists && item.asset_url) {
      const img = document.createElement("img");
      img.src = item.asset_url;
      img.alt = item.title || item.id;
      img.loading = "lazy";
      img.title = `${item.title || item.id} from page ${item.source_page || "?"}. ${item.notes || "Review before use."}`;
      frame.appendChild(img);
    } else {
      frame.appendChild(el("span", "muted", "Asset missing"));
    }
    const meta = el("div", "modern-row-copy");
    meta.append(
      el("strong", "", item.title || item.id),
      el("span", "muted", `page ${item.source_page || "?"} · ${item.asset_path || "no path"}`),
      el("span", "muted", `${item.review_status || "needs_review"} · ${item.use || "unassigned"}`)
    );
    cardEl.append(frame, meta);
    grid.appendChild(cardEl);
  }
  panel.appendChild(grid);
  return panel;
}

function renderAdventurePackagePinForm(pkg, map, preview) {
  const label = input("text", `pin-label-${pkg.package_id}-${map.id}`, "Short map label, for example 1 or A.");
  const role = select(`pin-role-${pkg.package_id}-${map.id}`, "What this marker represents on the map. Use Dungeon Entrance and Dungeon Exit for route endpoints; use Location or Room for ordinary keyed areas.", [
    ["location", "Location"],
    ["room", "Room"],
    ["entrance", "Dungeon Entrance"],
    ["exit", "Dungeon Exit"],
    ["stairs", "Stairs / Level Change"],
    ["secret", "Secret / Hidden"],
    ["objective", "Objective / Key Site"],
    ["camp", "Camp"],
    ["settlement", "Settlement"],
    ["other", "Other"],
  ]);
  const node = input("text", `pin-node-${pkg.package_id}-${map.id}`, "Room, scene, hex, or location id this pin links to. Pick an existing reviewed node when possible; use a temporary id for visual markers not reviewed yet.");
  const x = input("number", `pin-x-${pkg.package_id}-${map.id}`, "X coordinate as percentage across the map.");
  const y = input("number", `pin-y-${pkg.package_id}-${map.id}`, "Y coordinate as percentage down the map.");
  const width = input("number", `pin-width-${pkg.package_id}-${map.id}`, "Optional width percentage for a rectangular area.");
  const height = input("number", `pin-height-${pkg.package_id}-${map.id}`, "Optional height percentage for a rectangular area.");
  const shape = select(`pin-shape-${pkg.package_id}-${map.id}`, "Pin shape. Use point for a numbered room marker or rect for an area.", [["point", "Point"], ["rect", "Rectangle"], ["circle", "Circle"]]);
  const notes = textarea(`pin-notes-${pkg.package_id}-${map.id}`, "Optional review notes, for example which PDF label, door, staircase, exit arrow, or entrance text this marker came from.", 2);
  const datalistId = `pin-node-options-${pkg.package_id}-${map.id}`;
  node.setAttribute("list", datalistId);
  const datalist = document.createElement("datalist");
  datalist.id = datalistId;
  for (const item of pkg.nodes || []) {
    if (!item?.id) continue;
    const option = document.createElement("option");
    option.value = item.id;
    option.label = `${item.title || item.id}${item.type ? ` (${item.type})` : ""}`;
    datalist.appendChild(option);
  }
  for (const numeric of [x, y, width, height]) {
    numeric.min = "0";
    numeric.max = "100";
    numeric.step = "0.1";
  }
  preview.addEventListener("click", (event) => {
    const img = preview.querySelector("img");
    if (!img) return;
    const rect = img.getBoundingClientRect();
    x.value = Math.max(0, Math.min(100, ((event.clientX - rect.left) / rect.width) * 100)).toFixed(2);
    y.value = Math.max(0, Math.min(100, ((event.clientY - rect.top) / rect.height) * 100)).toFixed(2);
    setStatus(`Pin coordinate filled: ${x.value}%, ${y.value}%. Add a label and node id, then save.`);
  });
  const fillFromPin = (pin) => {
    label.value = pin.label || "";
    role.value = pin.role || "location";
    node.value = pin.node_id || "";
    x.value = pin.x ?? "";
    y.value = pin.y ?? "";
    width.value = pin.width || "";
    height.value = pin.height || "";
    shape.value = pin.shape || "point";
    notes.value = pin.notes || "";
    setStatus(`Loaded map pin ${pin.label || pin.id} for editing.`);
  };
  for (const pin of map.pins || []) {
    const marker = renderAdventurePackageMapPinMarker(pin);
    marker.addEventListener("click", (event) => {
      event.stopPropagation();
      fillFromPin(pin);
    });
    preview.appendChild(marker);
  }
  const form = el("div", "modern-package-pin-form");
  form.append(
    field("Label", label),
    field("Pin Role", role),
    field("Node / Room Id", node),
    field("X %", x),
    field("Y %", y),
    field("Width %", width),
    field("Height %", height),
    field("Shape", shape),
    field("Notes", notes),
    datalist
  );
  const row = actions();
  row.appendChild(button("Save Map Pin", "Save or update this role-marked pin in the local package JSON. This does not create playable exits until a reviewed manifest uses the package.", async () => {
    const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/pins`, {
      method: "POST",
      body: JSON.stringify({
        map_id: map.id,
        label: label.value,
        role: role.value,
        node_id: node.value,
        x: Number(x.value || 0),
        y: Number(y.value || 0),
        width: Number(width.value || 0),
        height: Number(height.value || 0),
        shape: shape.value,
        notes: notes.value,
      }),
    });
    modernState.adventurePackages = (modernState.adventurePackages || []).filter((item) => item.package_id !== result.package.package_id);
    modernState.adventurePackages.push(result.package);
    setStatus(`Saved pin for ${result.package.title}.`);
    renderPage();
  }));
  form.appendChild(row);
  return form;
}

function renderAdventurePackageMapPinMarker(pin) {
  const marker = el("button", `modern-package-map-pin-marker role-${pin.role || "location"}`, pin.label || pin.id || "?");
  marker.type = "button";
  marker.style.left = `${Math.max(0, Math.min(100, Number(pin.x || 0)))}%`;
  marker.style.top = `${Math.max(0, Math.min(100, Number(pin.y || 0)))}%`;
  marker.title = `${modernTitleFromKey(pin.role || "location")}: ${pin.label || pin.id || "pin"}${pin.node_id ? ` -> ${pin.node_id}` : ""}. Click to load this marker into the editor.`;
  return marker;
}

function renderAdventurePackagePins(pkg, map) {
  const pins = map.pins || [];
  const list = el("div", "modern-package-pin-list");
  if (!pins.length) {
    list.appendChild(el("p", "muted", "No pins yet. Click the map preview to fill X/Y, choose a pin role, then save a room, entrance, exit, objective, or location marker."));
    return list;
  }
  for (const pin of pins) {
    const row = el("div", "modern-row");
    const summary = el("span", "", `${modernTitleFromKey(pin.role || "location")}: ${pin.label} -> ${pin.node_id} (${pin.x}%, ${pin.y}%)`);
    summary.title = pin.notes || "Click the marker on the map to load this pin into the editor.";
    row.appendChild(summary);
    const rowActions = actions();
    rowActions.appendChild(button("Delete Pin", "Remove this pin from the local package JSON.", async () => {
      const result = await api(`/api/adventures/packages/${encodeURIComponent(pkg.package_id)}/maps/${encodeURIComponent(map.id)}/pins/${encodeURIComponent(pin.id)}`, { method: "DELETE" });
      modernState.adventurePackages = (modernState.adventurePackages || []).filter((item) => item.package_id !== result.package.package_id);
      modernState.adventurePackages.push(result.package);
      setStatus(`Deleted pin ${pin.label}.`);
      renderPage();
    }, "danger-button"));
    row.appendChild(rowActions);
    list.appendChild(row);
  }
  return list;
}

function renderAdventureModuleImportActions() {
  const panel = card("Module Import", "Import creates a new module in DATA_DIR/Adventures/<module_id>. JSON import is available now; ZIP import is shown here because package/module bundles will use it next.");
  const json = textarea("modern-module-import-json", "Paste an adventure module JSON manifest to validate or import.", 8);
  const file = input("file", "modern-module-import-file", "Load an adventure module JSON file.");
  file.accept = ".json,application/json";
  const zipFile = input("file", "modern-module-import-zip-file", "Load a future module .zip package. ZIP import is not implemented yet.");
  zipFile.accept = ".zip,application/zip";
  zipFile.disabled = true;
  file.addEventListener("change", async () => {
    const selected = file.files?.[0];
    if (!selected) return;
    json.value = await selected.text();
    setStatus(`Loaded ${selected.name} into Module JSON.`);
  });
  panel.append(field("Module JSON", json), field("Import .json file", file), field("Import .zip file", zipFile));
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
    }),
    button("Import ZIP", "ZIP import is planned for full adventure folders containing adventure.json, package.json, maps, artwork, tables, and notes.", async () => {
      setStatus("ZIP import is planned; use Import JSON for now.");
    }, "secondary")
  );
  row.lastChild.disabled = true;
  panel.appendChild(row);
  return panel;
}

function renderAdventureModuleList() {
  const panel = card(
    "All Modules",
    "Every module source appears here: rules, The Adventures Guild, AI/imported, PDF sources, and future custom modules. Source-specific preparation lives in the generator and PDF importer tabs."
  );
  const rows = [...(modernState.adventures || [])].sort((a, b) => (a.name || a.title || a.id).localeCompare(b.name || b.title || b.id));
  if (!rows.length) {
    panel.appendChild(el("p", "muted", "No adventure modules found."));
    return panel;
  }
  const list = el("div", "modern-module-table");
  list.append(
    el("strong", "", "Module Name"),
    el("strong", "", "Source"),
    el("strong", "", "Status"),
    el("strong", "", "Actions")
  );
  for (const adventure of rows) {
    const id = String(adventure.id || "");
    const title = adventure.name || adventure.title || id;
    const inUse = adventureModuleInUse(id);
    const protectedModule = ["random", "ai-adventure", "courtship-demesne"].includes(id) || adventure.source === "rules" || adventure.playable === false;
    const source = adventureModuleKind(adventure);
    const status = adventureModuleStatus(adventure);
    const nameCell = el("div", "modern-row-copy");
    nameCell.append(el("strong", "", title), el("span", "muted", `${id}${adventure.room_count ? ` · ${adventure.room_count} room(s)` : ""}`));
    if (adventure.pdf_source) {
      nameCell.appendChild(el("span", "muted", `${adventure.pdf_detected_type ? String(adventure.pdf_detected_type).replaceAll("_", " ") : "unscanned"} · ${adventure.pdf_package_recommendation || adventure.pdf_recommended_action || "Review in PDF Module Importer"}`));
    } else if (adventure.notes) {
      nameCell.appendChild(el("span", "muted", adventure.notes));
    }
    const sourceCell = el("span", "modern-tag", source);
    sourceCell.title = "Module source. PDF source rows are assessment/preparation records until converted to a playable module.";
    const statusCell = el("span", "modern-tag", status);
    statusCell.title = "Module status: N/A for source PDFs, Ready for playable modules, In progress for active sessions, Completed if a session has finished.";
    const rowActions = actions();
    if (adventure.playable) {
      rowActions.append(link("Export .json", `/api/adventures/${encodeURIComponent(id)}/export`, "Export this module manifest as JSON."));
      rowActions.append(link("Export .zip", `/api/adventures/${encodeURIComponent(id)}/export.zip`, "Export the full adventure folder as a ZIP package."));
    } else {
      rowActions.appendChild(el("span", "muted", adventure.pdf_source ? "Review in PDF Importer" : "No export"));
    }
    if (!protectedModule && adventure.playable) {
      const remove = button("Delete", inUse.length ? "Cannot delete while this module has an in-progress game." : "Delete this installed module. Completed session history is kept.", async () => {
        if (inUse.length) throw new Error(`Cannot delete ${title}: ${inUse.length} game(s) still use it.`);
        if (!window.confirm(`Delete ${title}?`)) return;
        const result = await api(`/api/adventures/${encodeURIComponent(id)}`, { method: "DELETE" });
        setStatus(result.message || "Adventure module deleted.");
        await refreshCoreAndRender();
      });
      remove.disabled = Boolean(inUse.length);
      rowActions.appendChild(remove);
    } else if (protectedModule) {
      rowActions.appendChild(el("span", "muted", "Protected"));
    }
    list.append(nameCell, sourceCell, statusCell, rowActions);
  }
  panel.appendChild(list);
  return panel;
}

function renderCreateModulePlaceholder() {
  const panel = card(
    "Create Module",
    "Placeholder for a hand-authored module builder. This will create a complete DATA_DIR/Adventures/<module_id>/ folder with adventure.json, package.json, maps, artwork, tables, notes, and validation."
  );
  panel.append(
    modernStatusRow("Status", "Planned", "Manual module creation is deliberately separate from TAG generation, AI prompts, and PDF source conversion."),
    modernStatusRow("Folder model", "DATA_DIR/Adventures/<module_id>/", "Everything for a module should live in one adventure folder for backup, export, and deletion."),
    modernStatusRow("Next design step", "Room graph + map/pin + validation workflow", "The builder should use the same reviewed manifest/package schemas as imported modules.")
  );
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
  const tagLeadType = select("modern-tag-lead-type", "Choose which Adventures Guild lead table to generate from when Random is off.", TAG_ADVENTURE_LEAD_TYPES);
  const tagLeadRandom = input("checkbox", "modern-tag-lead-random", "Random Adventures Guild lead: choose the lead family and table result randomly when the module is generated.");
  tagLeadRandom.checked = true;
  const randomRow = el("label", "modern-check-row");
  randomRow.title = tagLeadRandom.title;
  randomRow.append(tagLeadRandom, el("span", "", "Random lead family"));
  const fixedResult = select("modern-tag-lead-detail", "Developer playtest override: choose the exact printed table result instead of rolling. Hidden unless enabled in Developer.", []);
  const fixedResultField = field("Fixed result", fixedResult);
  fixedResultField.classList.add("modern-dev-only-control");
  function syncFixedResults() {
    const leadType = tagLeadType.value || "rumor";
    const current = fixedResult.value || "";
    fixedResult.replaceChildren(new Option(leadType === "rumor" ? "Random - roll d12" : "Random - roll table", ""));
    for (const [value, label] of TAG_ADVENTURE_FIXED_RESULTS[leadType] || TAG_ADVENTURE_FIXED_RESULTS.rumor) {
      const option = new Option(label, value);
      option.title = `Developer playtest override: force ${label} instead of rolling from the printed table.`;
      fixedResult.appendChild(option);
    }
    fixedResult.value = [...fixedResult.options].some((option) => option.value === current) ? current : "";
  }
  const syncTagLeadRandom = () => {
    tagLeadType.disabled = tagLeadRandom.checked;
    tagLeadType.closest("label")?.classList.toggle("muted", tagLeadRandom.checked);
    fixedResult.disabled = tagLeadRandom.checked;
    fixedResultField.classList.toggle("muted", tagLeadRandom.checked);
  };
  tagLeadType.addEventListener("change", syncFixedResults);
  tagLeadRandom.addEventListener("change", syncTagLeadRandom);
  syncFixedResults();
  syncTagLeadRandom();
  tagLead.append(randomRow, field("Lead type", tagLeadType));
  if (modernState.preferences?.show_tag_fixed_result_selector) tagLead.appendChild(fixedResultField);
  tagLead.appendChild(button("Create Adventures Guild Module", "Create and install an Adventures Guild lead as a playable imported adventure. With Random checked, the app chooses the lead family and table result.", async () => {
    const leadTypes = TAG_ADVENTURE_LEAD_TYPES.map(([value]) => value);
    const selectedLeadType = tagLeadRandom.checked
      ? leadTypes[Math.floor(Math.random() * leadTypes.length)]
      : tagLeadType.value;
    const selectedDetail = !tagLeadRandom.checked && modernState.preferences?.show_tag_fixed_result_selector
      ? fixedResult.value
      : "";
    const result = await api("/api/campaign/tag/create-adventure", {
      method: "POST",
      body: JSON.stringify({ lead_type: selectedLeadType, detail: selectedDetail }),
    });
    modernState.campaign = result.campaign;
    modernState.adventures = await api("/api/adventures");
    writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: result.adventure_id || "" });
    if (selectedAdventureControl) {
      selectedAdventureControl.replaceChildren(...optionRows(adventureOptions("imported")));
      selectedAdventureControl.value = result.adventure_id || "";
    }
    setStatus(`Created ${result.title || result.adventure_id}. It is selected in Go Adventure > Start.`);
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
      writeModernPrefs({ lastAdventureType: "imported", lastAdventureId: result.adventure_id || "" });
      setStatus(result.message || `Imported ${result.title || result.adventure_id}. It is selected in Go Adventure > Start.`);
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  return panel;
}

function renderAdventureManagement() {
  rootEl.appendChild(renderGuide("Adventure Management", [
    "Use Modules for the single list of all modules from every source, with import, export, delete, source, and status in one place.",
    "Use Generate Modules for The Adventures Guild and AI generators.",
    "Use PDF Module Importer to scan source PDFs, create package folders, review maps, and pin rooms before conversion.",
    "Use Create Module for the future hand-authored module builder.",
    "Start and resume actual play from Go Adventure."
  ], "go_adventure_closeout_gates", "adventure management generated modules import export delete"));
  const tabs = el("div", "modern-tabs");
  const panels = {};
  function activateAdventureTab(key) {
    window.sessionStorage.setItem(ADVENTURE_MANAGEMENT_TAB_KEY, key);
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
  addAdventureTab("modules", "Modules", "Single list of all modules plus global JSON/ZIP import actions.", [renderAdventureModuleImportActions(), renderAdventureModuleList()]);
  addAdventureTab("generate", "Generate Modules", "Generate Adventures Guild modules and AI-authored module prompts/imports.", [
    renderTagModuleGeneration(),
    renderAiModuleGeneration(),
    collapseCard(renderTagWorkflowDashboard("go")),
  ]);
  addAdventureTab("pdf", "PDF Module Importer", "Scan PDF sources, create package folders, review map assets, and pin rooms or locations.", [
    renderAdventurePdfSourceScanner(),
    renderAdventurePackageManager(),
  ]);
  addAdventureTab("create", "Create Module", "Placeholder for a hand-authored module builder.", [renderCreateModulePlaceholder()]);
  addAdventureTab("reference", "Reference", "Review closeout, signoff, action history, and rules/table links for generated modules.", [
    renderPlaytestTriagePanel("adventure-management"),
    renderAdventureCloseoutCockpit("Adventure Management"),
    renderTagSignoffPanel("Adventures Guild Lead / Start Signoff"),
    renderTagActionLogExplorer(),
    renderTagLeadSelectorPanel(),
    renderRumorLeadAuditPanel(),
    renderRumorSignoffChecklist(),
    renderTreasureMapLeadAuditPanel(),
    renderTreasureMapSignoffChecklist(),
    renderThematicDungeonLeadAuditPanel(),
    renderThematicDungeonSignoffChecklist(),
    renderGuildJobLeadAuditPanel(),
    renderGuildJobSignoffChecklist(),
  ]);
  rootEl.append(tabs, ...Object.values(panels));
  const storedTab = window.sessionStorage.getItem(ADVENTURE_MANAGEMENT_TAB_KEY);
  activateAdventureTab(panels[storedTab] ? storedTab : "modules");
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
  const enabledSupplementIds = modernState.preferences?.enabled_supplement_ids || ["expanded-edition-core"];
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
  const initialSuggestedProfile = suggestedLegacyProfileForSupplements(enabledSupplementIds);
  let profileManuallyChanged = false;
  if ([...profile.options].some((option) => option.value === initialSuggestedProfile)) {
    profile.value = initialSuggestedProfile;
  }
  profile.addEventListener("change", () => {
    profileManuallyChanged = true;
  });
  const xp = select("modern-start-xp", "XP system for this adventure.", [["classical", "Classical"], ["slow_and_sure", "Slow and Sure"], ["old_school", "Old School"], ["slower_advancement", "Slower Advancement"]]);
  xp.value = prefs.defaultXpSystem || "classical";
  const mapMode = select("modern-start-map-mode", "Map mode for this adventure.", [["unlimited", "Unlimited"], ["paper", "Paper 20x28"]]);
  mapMode.value = prefs.defaultMapMode || "unlimited";
  const mapLimit = input("number", "modern-start-map-limit", "Unlimited-map element cap before end-boss pressure.", String(prefs.defaultMapLimit || 60));
  const startSupplements = Array.isArray(modernState.supplements?.supplements) ? modernState.supplements.supplements : [];
  const startSupplementChecks = new Map();
  const supplementPreferenceCard = card("Session Supplements", "Settings provides the starting checklist. Adjust it here before Start Adventure; the final list is locked onto the new session and shown on Resume/Saved Games.");
  supplementPreferenceCard.classList.add("modern-card-compact");
  const supplementStatusRows = el("div", "modern-list");
  function selectedStartSupplementIds() {
    return startSupplements
      .filter((supplement) => {
        const checkbox = startSupplementChecks.get(supplement.id);
        return supplement.locked || checkbox?.checked || (type.value !== "random" && supplement.id === "imported-adventures");
      })
      .map((supplement) => supplement.id);
  }
  function syncStartSupplementProfile({ userChanged = false } = {}) {
    const chosen = selectedStartSupplementIds();
    const suggested = suggestedLegacyProfileForSupplements(chosen);
    const conflicts = supplementConflictIds(chosen);
    if (type.value === "random" && !profileManuallyChanged && [...profile.options].some((option) => option.value === suggested)) {
      profile.value = suggested;
      drawReadiness();
    }
    supplementStatusRows.replaceChildren(
      modernStatusRow(
        "Session selection",
        supplementTitlesForIds(chosen).split(", ").filter(Boolean),
        "This is the supplement snapshot that will be saved on the new session. Existing saved sessions are unchanged."
      ),
      modernStatusRow(
        "Suggested legacy random profile",
        legacyProfileLabel(suggested),
        "Based on the selected session supplements: Abyss suggests Abyss; Forsaken Depths + Courtship suggests the combined Forsaken Depths profile; Forsaken Depths alone suggests the no-Courtship profile; otherwise Expanded Edition random. The legacy profile still drives random generation until supplement activation fully replaces it."
      )
    );
    for (const supplement of startSupplements) {
      const checkbox = startSupplementChecks.get(supplement.id);
      if (!checkbox) continue;
      const forcedImported = type.value !== "random" && supplement.id === "imported-adventures";
      const blockedByConflict = conflicts.has(supplement.id) && !checkbox.checked && !supplement.locked && !forcedImported;
      checkbox.checked = Boolean(supplement.locked || forcedImported || checkbox.checked);
      checkbox.disabled = Boolean(supplement.locked || forcedImported || blockedByConflict);
      checkbox.title = blockedByConflict
        ? `${supplement.title || supplement.id} conflicts with another selected session supplement.`
        : forcedImported
        ? "Imported adventure sessions always record the Imported Adventure Packages supplement because the selected module supplies maps, locations, narrative, or package data."
        : `Include ${supplement.title || supplement.id} in the supplement snapshot for this new session.`;
      const label = checkbox.closest("label")?.querySelector("[data-supplement-start-label]");
      if (label) {
        const state = supplement.locked ? "locked on" : forcedImported ? "required for imported module" : blockedByConflict ? "conflicts with selected session supplement" : checkbox.checked ? "on for this session" : "off for this session";
        label.textContent = `${supplement.title || supplement.id} - ${state}`;
      }
    }
  }
  for (const supplement of startSupplements) {
    const checkbox = input("checkbox", `modern-start-supplement-${supplement.id}`, `Include ${supplement.title || supplement.id} in the supplement snapshot for this new session.`);
    checkbox.checked = Boolean(supplement.locked || enabledSupplementIds.includes(supplement.id));
    checkbox.disabled = Boolean(supplement.locked);
    startSupplementChecks.set(supplement.id, checkbox);
    const row = el("label", "modern-check-row");
    row.title = `${supplement.notes || "Supplement registry record."} Capabilities: ${(supplement.capabilities || []).join(", ") || "none listed"}.`;
    const label = el("span");
    label.dataset.supplementStartLabel = "true";
    row.append(checkbox, label);
    checkbox.addEventListener("change", () => syncStartSupplementProfile({ userChanged: true }));
    supplementPreferenceCard.appendChild(row);
  }
  supplementPreferenceCard.appendChild(supplementStatusRows);
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
  syncStartSupplementProfile();
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
    syncStartSupplementProfile();
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
        active_supplement_ids: selectedStartSupplementIds(),
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
    row.appendChild(modernStatusRow("Locked supplements", sessionSupplementSummary(session), "Supplements snapshot locked when this session was created. Legacy sessions may not have this metadata yet."));
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
    row.appendChild(modernStatusRow("Locked supplements", sessionSupplementSummary(session), "Supplements snapshot locked when this session was created. Legacy sessions may not have this metadata yet."));
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
  addGoAdventureTab("start", "Start", "Start a fresh adventure after setup and closeout checks.", [
    collapseCard(panel),
    collapseCard(supplementPreferenceCard),
    collapseCard(workflowGuide),
  ]);
  addGoAdventureTab("resume", "Resume", "Resume active adventures or load saved games.", [
    collapseCard(sessions),
    collapseCard(saved),
    collapseCard(management),
  ]);
  addGoAdventureTab("reference", "Reference / Playtest", "Capture playtest issues and review closeout/reference context.", [
    collapseCard(renderPlaytestTriagePanel("go-adventure")),
    collapseCard(renderAdventureCloseoutCockpit("Go Adventure")),
    collapseCard(renderTagLeadSelectorPanel()),
    collapseCard(renderGuildJobLeadAuditPanel(adventure)),
    collapseCard(renderGuildJobSignoffChecklist()),
    collapseCard(renderTagActionLogExplorer()),
  ]);
  rootEl.append(tabs, ...Object.values(panels));
  activateGoAdventureTab("start");
}

async function renderRulesReference() {
  const audience = modernReferenceAudience();
  const payload = await api(`/api/rules/reference?audience=${encodeURIComponent(audience)}`);
  modernState.rulesReference = Array.isArray(payload) ? payload : (payload.entries || []);
  await loadArtwork();
  const isDeveloper = audience === "developer";
  const panel = card(
    isDeveloper ? "Developer Reference" : "Rules Reference",
    isDeveloper
      ? "Search app-owned implementation notes, workflow references, diagnostics, and maintenance boundaries."
      : "Search implemented player-facing rule references. Exact PDF wording belongs in local DATA_DIR/rules indexes created from PDFs you manually provide, not in git."
  );
  const search = input("search", "modern-rules-search", "Filter rules reference entries.");
  const params = new URLSearchParams(window.location.search);
  const helpQuery = params.get("help");
  const searchQuery = params.get("search");
  const exactEntryId = params.get("entry");
  if (searchQuery || helpQuery) search.value = searchQuery || helpQuery;
  const categories = [...new Set(modernState.rulesReference.map((entry) => entry.category || "rules"))].sort();
  const category = select("modern-rules-category", "Filter by rules category.", [["", "All categories"], ...categories.map((item) => [item, item])]);
  const statuses = [...new Set(modernState.rulesReference.map((entry) => entry.implementation_status || "reference"))].sort();
  const status = select("modern-rules-status", "Filter by implementation status.", [["", "All statuses"], ...statuses.map((item) => [item, modernStatusLabel(item)])]);
  const source = select("modern-rules-source", "Filter entries by whether they cite a printed source page or have artwork slots.", [["", "All source refs"], ["with", "With source page"], ...(isDeveloper ? [["app", "App-only / no source page"]] : []), ["art", "With artwork slot"]]);
  const supplementFilter = select("modern-rules-supplement", "Filter by inferred supplement context. Enabled defaults uses the saved Settings supplement list and always includes locked core.", supplementFilterOptions());
  const sort = select("modern-rules-sort", "Sort rules reference entries.", [["category", "Category"], ["title", "Title"], ["implementation_status", "Status"], ["source_page", "Source page"]]);
  const results = el("div", "modern-list");
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Category", category), field("Status", status), field("Source", source), field("Supplement", supplementFilter), field("Sort", sort));
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
    const needle = normalizedSearchNeedle(search.value);
    const rows = modernState.rulesReference
      .filter((entry) => !exactEntryId || entry.id === exactEntryId)
      .filter((entry) => !category.value || (entry.category || "rules") === category.value)
      .filter((entry) => !status.value || (entry.implementation_status || "reference") === status.value)
      .filter((entry) => source.value !== "with" || Boolean(entry.source_page))
      .filter((entry) => source.value !== "app" || !entry.source_page)
      .filter((entry) => source.value !== "art" || artworkForReference(entry).length)
      .filter((entry) => supplementFilterMatches(inferredSupplementIdsForText(`${entry.id || ""} ${entry.title || ""} ${entry.summary || ""} ${entry.body || ""} ${entry.source || ""} ${(entry.keywords || []).join(" ")}`), supplementFilter.value))
      .filter((entry) => modernTextMatchesNeedle(`${entry.title} ${entry.summary || ""} ${entry.body} ${entry.category || ""} ${entry.implementation_status || ""} ${entry.source_page || ""} ${(entry.keywords || []).join(" ")} ${artworkForReference(entry).map((art) => `${art.title} ${art.summary} ${art.source_pdf}`).join(" ")}`, needle))
      .sort((a, b) => String(a[sort.value] || "").localeCompare(String(b[sort.value] || ""), undefined, { numeric: true }) || String(a.title || "").localeCompare(String(b.title || "")));
    const byCategory = rows.reduce((groups, entry) => {
      const key = entry.category || "rules";
      if (!groups[key]) groups[key] = [];
      groups[key].push(entry);
      return groups;
    }, {});
    const summary = el("p", "muted", exactEntryId
      ? `${rows.length ? "Exact" : "No"} rule reference match for ${exactEntryId}.`
      : `${rows.length} matching ${isDeveloper ? "developer" : "player"} reference entr${rows.length === 1 ? "y" : "ies"} across ${Object.keys(byCategory).length} categor${Object.keys(byCategory).length === 1 ? "y" : "ies"}.`);
    results.appendChild(summary);
    for (const [groupName, items] of Object.entries(byCategory).sort(([a], [b]) => a.localeCompare(b))) {
      const group = document.createElement("details");
      group.className = "modern-row modern-reference-group";
      group.open = Boolean(exactEntryId);
      const groupSummary = document.createElement("summary");
      groupSummary.title = `Show or hide ${items.length} ${groupName} reference entries.`;
      groupSummary.append(el("strong", "", modernTitleFromKey(groupName)), el("span", "muted", `${items.length} entr${items.length === 1 ? "y" : "ies"}`));
      group.appendChild(groupSummary);
      const groupBody = el("div", "modern-reference-group-body");
      for (const item of items) {
        const row = document.createElement("details");
        row.className = "modern-row modern-reference-card";
        row.open = Boolean(exactEntryId);
        const rowSummary = document.createElement("summary");
        rowSummary.title = isDeveloper
          ? "Show or hide the full developer implementation note for this reference."
          : "Show or hide the player-facing rule reference text for this entry.";
        rowSummary.append(
          highlightedEl("strong", "", item.title || item.id, needle),
          el("span", "muted", `${modernStatusLabel(item.implementation_status)}${item.page_label ? ` · ${item.page_label}` : item.source_page ? ` · p.${item.source_page}` : ""}`)
        );
        row.appendChild(rowSummary);
        if (item.summary) row.appendChild(highlightedEl("p", "modern-home-status", item.summary, needle));
        row.appendChild(renderSupplementBadges(inferredSupplementIdsForText(`${item.id || ""} ${item.title || ""} ${item.summary || ""} ${item.body || ""} ${item.source || ""} ${(item.keywords || []).join(" ")}`), "Inferred from this reference title, source, keywords, and body. Use the Supplement filter to narrow the reference index."));
        if (item.keywords?.length) row.appendChild(highlightedEl("span", "muted", item.keywords.join(" · "), needle));
        const relatedArt = artworkForReference(item);
        if (relatedArt.length) row.appendChild(renderArtworkRows(relatedArt.slice(0, 3), { compact: true }));
        if (item.body) {
          const body = el("div", "modern-reference-body");
          item.body.split("\n").filter((line) => line.trim()).forEach((line) => body.appendChild(highlightedEl("p", "", line, needle)));
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
          isDeveloper
            ? "No matching developer reference entries. Clear filters or search by workflow, table, implementation status, keyword, source page, or body text."
            : "No matching player rules reference entries. Clear filters or search by rule name, source page, keyword, or local exact-PDF wording once indexed."
        )
      );
    }
  };
  search.addEventListener("input", draw);
  category.addEventListener("change", draw);
  status.addEventListener("change", draw);
  source.addEventListener("change", draw);
  supplementFilter.addEventListener("change", draw);
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

function supplementIdsForTable(key, value) {
  return inferredSupplementIdsForText(`${key} ${modernTableFamily(key)} ${modernSearchText(value)}`);
}

function modernTablePreview(value, needle = "") {
  const rowNeedle = normalizedSearchNeedle(needle);
  const rows = Array.isArray(value)
    ? value
    : modernTableRows(value);
  const visibleRows = rowNeedle
    ? rows.filter((row) => modernTextMatchesNeedle(modernSearchText(row), rowNeedle))
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
      line.append(highlightedEl("strong", "", String(title), rowNeedle), highlightedEl("span", "muted", detail, rowNeedle));
    } else {
      line.append(highlightedEl("span", "", String(row), rowNeedle));
    }
    box.appendChild(line);
  }
  if (visibleRows.length > 250) box.appendChild(el("p", "muted", `Showing first 250 of ${visibleRows.length} matching rows. Use search to narrow this table.`));
  return box;
}

async function renderTables() {
  const audience = modernReferenceAudience();
  modernState.tables = await api(`/api/rules/tables?audience=${encodeURIComponent(audience)}`);
  await loadArtwork();
  const isDeveloper = audience === "developer";
  const panel = card(
    isDeveloper ? "Developer Tables" : "Tables List",
    isDeveloper
      ? "Search internal app tables for workflows, registries, validation, imported package review, and diagnostics."
      : "Search implemented player-facing tables from rules PDFs and generated PDF-backed catalogs."
  );
  const search = input("search", "modern-table-search", "Search by table name or entry text.");
  const params = new URLSearchParams(window.location.search);
  const helpQuery = params.get("help");
  const searchQuery = params.get("search");
  if (searchQuery || helpQuery) search.value = searchQuery || helpQuery;
  const families = [...new Set(Object.keys(modernState.tables).map(modernTableFamily))].sort();
  const family = select("modern-table-family", "Filter by table family.", [["", "All table families"], ...families.map((item) => [item, item])]);
  const artworkFilter = select("modern-table-artwork", "Filter tables by whether they have local artwork slots.", [["", "All artwork states"], ["with", "With artwork slot"], ["without", "Without artwork slot"]]);
  const supplementFilter = select("modern-table-supplement", "Filter tables by inferred supplement context. Enabled defaults uses the saved Settings supplement list and always includes locked core.", supplementFilterOptions());
  const sort = select("modern-table-sort", "Sort table groups.", [["name", "Name"], ["rows", "Row count"]]);
  const results = el("div", "modern-list");
  const controls = el("div", "modern-filterbar");
  controls.append(field("Search", search), field("Family", family), field("Artwork", artworkFilter), field("Supplement", supplementFilter), field("Sort", sort));
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
    const needle = normalizedSearchNeedle(search.value);
    const keys = Object.keys(modernState.tables).filter((key) => {
      if (family.value && modernTableFamily(key) !== family.value) return false;
      if (artworkFilter.value === "with" && !artworkForTable(key).length) return false;
      if (artworkFilter.value === "without" && artworkForTable(key).length) return false;
      if (!supplementFilterMatches(supplementIdsForTable(key, modernState.tables[key]), supplementFilter.value)) return false;
      if (!needle) return true;
      return modernTextMatchesNeedle(key, needle)
        || modernTextMatchesNeedle(modernSearchText(modernState.tables[key]), needle)
        || modernTextMatchesNeedle(artworkForTable(key).map((art) => `${art.title} ${art.summary} ${art.source_pdf}`).join(" "), needle);
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
    results.appendChild(el("p", "muted", `${keys.length} matching ${isDeveloper ? "developer" : "player"} table${keys.length === 1 ? "" : "s"} across ${Object.keys(byFamily).length} famil${Object.keys(byFamily).length === 1 ? "y" : "ies"} · ${artworkCount} with artwork slots.`));
    for (const [groupName, groupKeys] of Object.entries(byFamily).sort(([a], [b]) => a.localeCompare(b))) {
      const group = document.createElement("details");
      group.className = "modern-row modern-table-group";
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
        const summary = document.createElement("summary");
        summary.title = "Show or hide this table's rows.";
        const tableArt = artworkForTable(key);
        summary.append(highlightedEl("strong", "", modernTitleFromKey(key), needle), highlightedEl("span", "muted", `${key} · ${modernTableRowCount(value)} row(s)${tableArt.length ? ` · ${tableArt.length} art slot(s)` : ""}`, needle));
        details.appendChild(summary);
        details.appendChild(renderSupplementBadges(supplementIdsForTable(key, value), "Inferred from this table key, family, and row text. Use the Supplement filter to narrow table navigation."));
        if (tableArt.length) details.appendChild(renderArtworkRows(tableArt.slice(0, 4), { compact: true }));
        const previewMount = el("div", "modern-table-preview-mount");
        const renderPreview = () => {
          const rowNeedle = modernTextMatchesNeedle(key, needle) ? "" : needle;
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
      results.appendChild(el("p", "modern-home-status in-progress", isDeveloper
        ? "No matching developer tables. Clear filters or search by workflow, registry, validation, package, artwork, or diagnostic term."
        : "No matching player tables. Clear filters or search by table name, row text, roll result, monster, item, tile, or source term."));
    }
  };
  search.addEventListener("input", draw);
  family.addEventListener("change", draw);
  artworkFilter.addEventListener("change", draw);
  supplementFilter.addEventListener("change", draw);
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

async function renderRulePdfManager() {
  const panel = card("PDF / Supplement Workbench", "Upload owned PDFs into DATA_DIR/rules, index exact page text for the player Rules Reference, or run specialist extractors while the broader supplement review workbench is built.");
  const file = input("file", "modern-rule-pdf-upload", "Choose an owned rules PDF from your computer to upload to the server.");
  file.accept = "application/pdf,.pdf";
  const sourceAssetFile = input("file", "modern-supplement-source-asset-upload", "Choose a map, handout, or image source file to attach to the selected supplement package.");
  sourceAssetFile.accept = "image/png,image/jpeg,image/webp,image/gif,image/bmp,image/svg+xml,.png,.jpg,.jpeg,.webp,.gif,.bmp,.tif,.tiff,.svg";
  const uploadedSelect = select("modern-rule-pdf-select", "Uploaded DATA_DIR/rules PDF to extract from.", [["", "Choose uploaded PDF"]]);
  const pageOffset = input("number", "modern-rule-pdf-page-offset", "Optional printed-page offset. The app calculates printed page = PDF page + offset. Example: if PDF page 7 is printed page 1, enter -6.", "0");
  const supplementId = input("text", "modern-rule-pdf-supplement-id", "Supplement package id. Use the same id for multiple PDFs that belong to one supplement package.", "");
  const supplementTitle = input("text", "modern-rule-pdf-supplement-title", "Human-readable supplement package title. This groups multiple source documents into one future playable supplement.", "");
  const overwrite = input("checkbox", "modern-rule-pdf-overwrite", "Overwrite existing fields in DATA_DIR/tag_scene_narrative_overrides.json. Leave off to preserve local edits.");
  const status = el("div", "modern-list");
  const resultBox = el("div", "modern-list");
  const uploadedPdfSettings = new Map();
  function showRulePdfResult(kind, message, title = "Rules PDF Import") {
    resultBox.replaceChildren(modernStatusRow(title, message, kind === "error" ? "Fix the issue shown here, then run Extract Adventures Guild Narrative again." : "This is the latest upload/extraction result."));
  }
  function extractionWarningSummary(warnings) {
    if (!Array.isArray(warnings) || !warnings.length) return "No suspected cut-off entries.";
    return warnings.slice(0, 8).join(" ");
  }
  const sourceScanStatus = el("div", "modern-list modern-source-scan-status");
  function suggestedSupplementId(filename) {
    return String(filename || "")
      .replace(/\.pdf$/i, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "supplement-package";
  }
  function suggestedSupplementTitle(filename) {
    return String(filename || "")
      .replace(/\.pdf$/i, "")
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim() || "Supplement Package";
  }
  function sourceMetadataPayload() {
    return {
      filename: uploadedSelect.value,
      page_offset: Number(pageOffset.value || 0),
      supplement_id: supplementId.value || suggestedSupplementId(uploadedSelect.value),
      supplement_title: supplementTitle.value || suggestedSupplementTitle(uploadedSelect.value),
    };
  }
  function d66Labels() {
    const labels = [];
    for (let tens = 0; tens <= 5; tens += 1) {
      for (let ones = 1; ones <= 6; ones += 1) labels.push(`${tens}${ones}`);
    }
    return labels;
  }
  function imageToCanvasBlob(image, rect) {
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(rect.w));
    canvas.height = Math.max(1, Math.round(rect.h));
    const ctx = canvas.getContext("2d");
    ctx.drawImage(image, Math.round(rect.x), Math.round(rect.y), Math.round(rect.w), Math.round(rect.h), 0, 0, canvas.width, canvas.height);
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("Could not create cropped tile image.")), "image/png");
    });
  }
  function maskToCanvasBlob(image, shapes) {
    if (!image.complete || !image.naturalWidth || !image.naturalHeight) throw new Error("Image preview is not loaded yet.");
    if (!shapes.length) throw new Error("Draw at least one mask shape first.");
    const minX = Math.max(0, Math.floor(Math.min(...shapes.map((shape) => shape.x))));
    const minY = Math.max(0, Math.floor(Math.min(...shapes.map((shape) => shape.y))));
    const maxX = Math.min(image.naturalWidth, Math.ceil(Math.max(...shapes.map((shape) => shape.x + shape.w))));
    const maxY = Math.min(image.naturalHeight, Math.ceil(Math.max(...shapes.map((shape) => shape.y + shape.h))));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, maxX - minX);
    canvas.height = Math.max(1, maxY - minY);
    const ctx = canvas.getContext("2d");
    ctx.save();
    ctx.beginPath();
    for (const shape of shapes) {
      const x = shape.x - minX;
      const y = shape.y - minY;
      if (shape.type === "ellipse") {
        ctx.ellipse(x + shape.w / 2, y + shape.h / 2, Math.abs(shape.w / 2), Math.abs(shape.h / 2), 0, 0, Math.PI * 2);
      } else {
        ctx.rect(x, y, shape.w, shape.h);
      }
    }
    ctx.clip();
    ctx.drawImage(image, -minX, -minY);
    ctx.restore();
    return new Promise((resolve, reject) => {
      canvas.toBlob((blob) => blob ? resolve(blob) : reject(new Error("Could not create masked image.")), "image/png");
    });
  }
  async function uploadPackageAssetBlob(pkg, blob, filename, params = {}) {
    const query = new URLSearchParams({
      filename,
      supplement_id: pkg.supplement_id || supplementId.value || "supplement-package",
      supplement_title: pkg.supplement_title || supplementTitle.value || "Supplement Package",
      asset_kind: params.asset_kind || "map_or_image",
      category: params.category || "unknown",
      title: params.title || filename.replace(/\.[^.]+$/, ""),
      notes: params.notes || "",
      parent_asset_id: params.parent_asset_id || "",
    });
    const response = await fetch(`/api/supplements/source-asset?${query.toString()}`, {
      method: "POST",
      headers: { "Content-Type": blob.type || "image/png" },
      body: await blob.arrayBuffer(),
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
  function workbenchSection(title, subtitle, body) {
    const details = document.createElement("details");
    details.className = "modern-row modern-source-review-section";
    const summary = document.createElement("summary");
    summary.append(el("strong", "", title), el("span", "muted", ` · ${subtitle}`));
    details.append(summary, body);
    return details;
  }
  function compactInfoStrip(title, items, hint = "") {
    const strip = el("div", "modern-source-compact-strip");
    if (hint) strip.title = hint;
    strip.appendChild(el("strong", "", title));
    for (const item of items.filter(Boolean)) {
      const label = typeof item === "string" ? item : item.label;
      const value = typeof item === "string" ? "" : item.value;
      const chip = el("span", "modern-source-compact-chip");
      if (item.hint) chip.title = item.hint;
      chip.append(el("span", "muted", label), value ? el("span", "", value) : document.createTextNode(""));
      strip.appendChild(chip);
    }
    return strip;
  }
  function actionGroup(title, buttons) {
    const group = el("div", "modern-source-action-group");
    group.appendChild(el("span", "muted", title));
    const row = el("div", "modern-source-action-row");
    row.append(...buttons);
    group.appendChild(row);
    return group;
  }
  function treeBranch(title, count, body, options = {}) {
    const details = document.createElement("details");
    details.className = `modern-source-tree-branch ${options.className || ""}`.trim();
    details.open = Boolean(options.open);
    const summary = document.createElement("summary");
    summary.append(el("strong", "", title), el("span", "modern-source-tree-count", String(count)));
    if (options.hint) summary.title = options.hint;
    details.append(summary, body);
    return details;
  }
  const sourceWorkbenchState = {
    packageId: window.sessionStorage.getItem("ahazi-source-workbench-package") || "",
    sourceId: window.sessionStorage.getItem("ahazi-source-workbench-source") || "",
    search: window.sessionStorage.getItem("ahazi-source-workbench-search") || "",
    assignment: window.sessionStorage.getItem("ahazi-source-workbench-assignment") || "",
    scope: window.sessionStorage.getItem("ahazi-source-workbench-scope") || "document",
    page: Number(window.sessionStorage.getItem("ahazi-source-workbench-page") || 0) || 0,
    selectedBlockIds: new Set(),
    scrollY: 0,
  };
  function persistSourceWorkbenchState() {
    window.sessionStorage.setItem("ahazi-source-workbench-package", sourceWorkbenchState.packageId || "");
    window.sessionStorage.setItem("ahazi-source-workbench-source", sourceWorkbenchState.sourceId || "");
    window.sessionStorage.setItem("ahazi-source-workbench-search", sourceWorkbenchState.search || "");
    window.sessionStorage.setItem("ahazi-source-workbench-assignment", sourceWorkbenchState.assignment || "");
    window.sessionStorage.setItem("ahazi-source-workbench-scope", sourceWorkbenchState.scope || "document");
    window.sessionStorage.setItem("ahazi-source-workbench-page", String(sourceWorkbenchState.page || ""));
  }
  function renderSourceScanDetail(payload, mount) {
    const blocks = Array.isArray(payload.blocks) ? payload.blocks.map((block) => ({ ...block, source_item_type: "block" })) : [];
    const candidates = Array.isArray(payload.continuation_candidates) ? payload.continuation_candidates.map((block) => ({ ...block, source_item_type: "page-boundary candidate" })) : [];
    const artworkItems = Array.isArray(payload.artwork) ? payload.artwork : [];
    const reviewedTables = Array.isArray(payload.tables) ? payload.tables : [];
    const sourceItems = blocks.concat(candidates);
    const search = input("search", "modern-source-block-search", "Search extracted source blocks from this PDF.", "");
    const assignment = select("modern-source-block-assignment", "Filter by current manual assignment.", [["", "All assignments"]]);
    const reviewScope = select("modern-source-review-scope", "Choose whether the block and artwork lists follow the current PDF page or show the whole source document.", [
      ["page", "Current PDF page"],
      ["document", "Whole document"],
    ]);
    for (const option of payload.assignment_options || []) assignment.appendChild(new Option(option, option));
    if (candidates.length) assignment.appendChild(new Option("Page-boundary candidates", "page_boundary_candidate"));
    search.value = sourceWorkbenchState.search || "";
    assignment.value = sourceWorkbenchState.assignment || "";
    reviewScope.value = sourceWorkbenchState.scope || "document";
    const results = el("div", "modern-source-tree");
    const selectedBlockIds = new Set([...sourceWorkbenchState.selectedBlockIds].filter((blockId) => sourceItems.some((item) => item.id === blockId)));
    let visibleSelectableBlockIds = [];
    const selectionStatus = el("p", "muted", "No source blocks selected.");
    const firstPdfPage = Number(sourceItems.find((item) => item.pdf_page)?.pdf_page || 1);
    const leftRail = el("div", "modern-source-left-rail");
    const pdfViewer = el("div", "modern-source-pdf-viewer");
    const pdfToolbar = actions();
    pdfToolbar.classList.add("modern-source-pdf-actions");
    const pdfControlBar = el("div", "modern-source-pdf-toolbar");
    const pageInput = input("number", "modern-source-pdf-page", "PDF page to preview beside the extracted text.", String(sourceWorkbenchState.page || firstPdfPage));
    pageInput.min = "1";
    const pdfCanvas = el("div", "modern-source-pdf-canvas");
    const pdfImage = el("img", "modern-source-pdf-image");
    pdfImage.alt = `Rendered source PDF page for ${payload.source_id || "supplement source"}`;
    const pdfStatus = el("p", "muted", "");
    let pdfZoom = 1;
    let pdfPanX = 0;
    let pdfPanY = 0;
    let pdfDragging = false;
    let pdfDragStartX = 0;
    let pdfDragStartY = 0;
    let pdfStartPanX = 0;
    let pdfStartPanY = 0;
    let redrawArtwork = () => {};
    function applyPdfTransform() {
      pdfImage.style.transform = `translate(${pdfPanX}px, ${pdfPanY}px) scale(${pdfZoom})`;
      pdfStatus.textContent = `PDF page ${pageInput.value || firstPdfPage} · zoom ${Math.round(pdfZoom * 100)}%`;
    }
    function setPdfPage(page) {
      const pageNo = Math.max(1, Number(page) || 1);
      pageInput.value = String(pageNo);
      pdfPanX = 0;
      pdfPanY = 0;
      pdfImage.src = payload.source_pdf_page_url ? `${payload.source_pdf_page_url}?page=${encodeURIComponent(pageNo)}` : "";
      applyPdfTransform();
    }
    function goPdfPage(page) {
      setPdfPage(page);
      sourceWorkbenchState.page = Number(pageInput.value || firstPdfPage) || firstPdfPage;
      persistSourceWorkbenchState();
      draw();
      redrawArtwork();
    }
    function previewPdfPage(page) {
      setPdfPage(page);
      sourceWorkbenchState.page = Number(pageInput.value || firstPdfPage) || firstPdfPage;
      persistSourceWorkbenchState();
    }
    function setPdfZoom(nextZoom) {
      pdfZoom = Math.min(4, Math.max(0.35, nextZoom));
      applyPdfTransform();
    }
    pdfToolbar.append(
      button("‹ Prev", "Show the previous PDF page and review items on that page.", () => goPdfPage(Number(pageInput.value || 1) - 1)),
      button("Next ›", "Show the next PDF page and review items on that page.", () => goPdfPage(Number(pageInput.value || 1) + 1)),
      button("+ Zoom", "Increase PDF preview zoom.", () => setPdfZoom(pdfZoom + 0.15)),
      button("- Zoom", "Decrease PDF preview zoom.", () => setPdfZoom(pdfZoom - 0.15)),
      button("⟲ Reset", "Reset PDF zoom and pan.", () => {
        pdfZoom = 1;
        pdfPanX = 0;
        pdfPanY = 0;
        applyPdfTransform();
      })
    );
    pageInput.addEventListener("change", () => goPdfPage(pageInput.value));
    pdfCanvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      setPdfZoom(pdfZoom + (event.deltaY < 0 ? 0.12 : -0.12));
    }, { passive: false });
    pdfCanvas.addEventListener("pointerdown", (event) => {
      pdfDragging = true;
      pdfCanvas.setPointerCapture(event.pointerId);
      pdfDragStartX = event.clientX;
      pdfDragStartY = event.clientY;
      pdfStartPanX = pdfPanX;
      pdfStartPanY = pdfPanY;
    });
    pdfCanvas.addEventListener("pointermove", (event) => {
      if (!pdfDragging) return;
      pdfPanX = pdfStartPanX + event.clientX - pdfDragStartX;
      pdfPanY = pdfStartPanY + event.clientY - pdfDragStartY;
      applyPdfTransform();
    });
    pdfCanvas.addEventListener("pointerup", (event) => {
      pdfDragging = false;
      try {
        pdfCanvas.releasePointerCapture(event.pointerId);
      } catch {
        /* pointer may already be released */
      }
    });
    pdfCanvas.appendChild(pdfImage);
    pdfControlBar.append(
      field("PDF page", pageInput),
      pdfToolbar
    );
    pdfViewer.append(
      pdfControlBar,
      pdfCanvas,
      pdfStatus
    );
    setPdfPage(sourceWorkbenchState.page || firstPdfPage);
    function saveCurrentWorkbenchState() {
      sourceWorkbenchState.sourceId = payload.source_id || sourceWorkbenchState.sourceId;
      sourceWorkbenchState.search = search.value || "";
      sourceWorkbenchState.assignment = assignment.value || "";
      sourceWorkbenchState.scope = reviewScope.value || "document";
      sourceWorkbenchState.page = Number(pageInput.value || firstPdfPage) || firstPdfPage;
      sourceWorkbenchState.selectedBlockIds = new Set(selectedBlockIds);
      sourceWorkbenchState.scrollY = window.scrollY || 0;
      persistSourceWorkbenchState();
    }
    async function reloadCurrentScan(message = "Source scan refreshed.") {
      saveCurrentWorkbenchState();
      const detail = await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}`);
      renderSourceScanDetail(detail, mount);
      setStatus(message);
      window.requestAnimationFrame(() => window.scrollTo({ top: sourceWorkbenchState.scrollY || window.scrollY, behavior: "auto" }));
    }
    function updateSelectionStatus() {
      selectionStatus.textContent = selectedBlockIds.size
        ? `${selectedBlockIds.size} source block(s) selected. Use the controls here to assign, merge, edit, move, or draft.`
        : "No source blocks selected.";
      sourceWorkbenchState.selectedBlockIds = new Set(selectedBlockIds);
      persistSourceWorkbenchState();
    }
    const mergeSelectedButton = button("⇄ Merge", "Merge the selected adjacent source blocks into one reviewed block. Select blocks in document order on the right, then use this button.", async (btn) => runWithButtonProgress(btn, "Merging selected...", async () => {
      await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/merge-selected`, {
        method: "POST",
        body: JSON.stringify({ block_ids: Array.from(selectedBlockIds) }),
      });
      await reloadCurrentScan("Selected source blocks merged.");
    }));
    const bulkAssignment = select("modern-source-bulk-assignment", "Assignment to apply to selected text blocks.", [["", "Choose assignment"]]);
    for (const option of payload.assignment_options || []) bulkAssignment.appendChild(new Option(option, option));
    const applyAssignmentButton = button("✓ Apply", "Apply the chosen assignment to every selected source block. This moves reviewed blocks into that category group.", async (btn) => runWithButtonProgress(btn, "Assigning blocks...", async () => {
      const nextAssignment = bulkAssignment.value;
      if (!nextAssignment) throw new Error("Choose an assignment first.");
      if (!selectedBlockIds.size) throw new Error("Select one or more source blocks first.");
      for (const blockId of Array.from(selectedBlockIds)) {
        await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(blockId)}`, {
          method: "PATCH",
          body: JSON.stringify({ assignment: nextAssignment, review_status: "edited" }),
        });
      }
      await reloadCurrentScan("Selected source blocks assigned.");
    }));
    const ignorePhraseButton = button("⊘ Ignore", "Use the current Search text as a literal phrase. Every occurrence in this source document is split into its own reviewed block and assigned to ignore.", async (btn) => runWithButtonProgress(btn, "Splitting ignored phrase...", async () => {
      const phrase = String(search.value || "").trim();
      if (!phrase) throw new Error("Enter the repeated phrase in Search before using Ignore Phrase.");
      const confirmed = window.confirm(`Split every occurrence of "${phrase}" into separate ignored snippets and remove it from the surrounding reviewed text blocks? Ignored snippets are hidden from normal search unless you filter to Ignore.`);
      if (!confirmed) {
        setStatus("Ignore phrase cancelled.");
        return;
      }
      const result = await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/split-ignore-phrase`, {
        method: "POST",
        body: JSON.stringify({ phrase }),
      });
      selectedBlockIds.clear();
      sourceWorkbenchState.selectedBlockIds = new Set();
      await reloadCurrentScan(result.message || "Matching phrase split into ignored blocks.");
    }));
    const selectVisibleButton = button("☑ Shown", "Select all visible reviewed text blocks in the current search/filter/page scope. Page-boundary candidates are not selected.", () => {
      for (const blockId of visibleSelectableBlockIds) selectedBlockIds.add(blockId);
      updateSelectionStatus();
      draw();
    });
    const clearSelectionButton = button("☐ Clear", "Clear the current source block selection.", () => {
      selectedBlockIds.clear();
      updateSelectionStatus();
      draw();
    });
    function selectedReviewedBlock() {
      if (selectedBlockIds.size !== 1) return null;
      const blockId = Array.from(selectedBlockIds)[0];
      return blocks.find((block) => block.id === blockId) || null;
    }
    function selectedAnyBlock() {
      if (selectedBlockIds.size !== 1) return null;
      const blockId = Array.from(selectedBlockIds)[0];
      return sourceItems.find((block) => block.id === blockId) || null;
    }
    function requireSelectedReviewedBlock(actionLabel) {
      const block = selectedReviewedBlock();
      if (!block) throw new Error(`${actionLabel} needs exactly one reviewed source block selected.`);
      return block;
    }
    let activeBlockEditor = null;
    async function splitBlockAtCursor(block, textValue, cursorPosition) {
      if (!block || block.source_item_type === "page-boundary candidate") throw new Error("Split needs exactly one reviewed source block selected.");
      const sourceText = String(textValue || "");
      const cursor = Math.max(0, Math.min(Number(cursorPosition || 0), sourceText.length));
      const parts = [sourceText.slice(0, cursor), sourceText.slice(cursor)]
        .map((part) => part.trim())
        .filter(Boolean);
      if (parts.length < 2) throw new Error("Place the cursor inside the block text before splitting. The cursor cannot be at the start or end.");
      await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(block.id)}/split`, {
        method: "POST",
        body: JSON.stringify({ parts }),
      });
      await reloadCurrentScan("Source block split at cursor.");
    }
    const editSelectedButton = button("✎ Edit", "Open the selected source block in the active review tool. Select exactly one text block on the right.", () => {
      const block = selectedAnyBlock();
      if (!block) throw new Error("Select exactly one source block to edit.");
      if (block.pdf_page) previewPdfPage(block.pdf_page);
      openSourceTool(`${block.page_label || `p.${block.source_page || "?"}`} · ${block.assignment || "unassigned"}`, blockEditor(block, search.value));
    });
    const splitSelectedButton = button("⟂ Split", "Split one selected reviewed text block. First click Split to open the editor, place the cursor in Reviewed text, then click Split again or use Split At Cursor in the editor.", async (btn) => runWithButtonProgress(btn, "Preparing split...", async () => {
      const block = requireSelectedReviewedBlock("Split");
      if (activeBlockEditor?.blockId === block.id && activeBlockEditor.textArea && document.body.contains(activeBlockEditor.textArea)) {
        await splitBlockAtCursor(block, activeBlockEditor.textArea.value, activeBlockEditor.textArea.selectionStart);
        return;
      }
      if (block.pdf_page) previewPdfPage(block.pdf_page);
      openSourceTool(`${block.page_label || `p.${block.source_page || "?"}`} · ${block.assignment || "unassigned"}`, blockEditor(block, search.value));
      activeBlockEditor?.textArea?.focus();
      setStatus("Place the cursor in Reviewed text, then click Split again or use Split At Cursor in the editor.");
    }));
    const draftTableButton = button("▦ Table", "Parse the selected table-assigned source block into editable machine rows. Select exactly one reviewed block assigned as table.", async (btn) => runWithButtonProgress(btn, "Drafting table...", async () => {
      const block = requireSelectedReviewedBlock("Draft Table");
      if (block.assignment !== "table") throw new Error("Assign the selected block as table before drafting machine rows.");
      await openTableDraftFromBlock(block, search.value);
    }));
    const moveUpButton = button("↑ Up", "Move the selected reviewed block earlier in the underlying document order. Filters may hide neighbouring blocks.", async (btn) => runWithButtonProgress(btn, "Moving block...", async () => {
      const block = requireSelectedReviewedBlock("Move Up");
      await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(block.id)}/move`, {
        method: "POST",
        body: JSON.stringify({ direction: "up" }),
      });
      await reloadCurrentScan("Source block moved up.");
    }));
    const moveDownButton = button("↓ Down", "Move the selected reviewed block later in the underlying document order. Filters may hide neighbouring blocks.", async (btn) => runWithButtonProgress(btn, "Moving block...", async () => {
      const block = requireSelectedReviewedBlock("Move Down");
      await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(block.id)}/move`, {
        method: "POST",
        body: JSON.stringify({ direction: "down" }),
      });
      await reloadCurrentScan("Source block moved down.");
    }));
    const sourceToolMount = el("div", "modern-source-tool-panel hidden");
    function openSourceTool(title, toolBody) {
      sourceToolMount.classList.remove("hidden");
      sourceToolMount.replaceChildren(
        modernStatusRow("Active review tool", title, "The source PDF, page text block list, and artwork list remain visible while this selected item is edited here."),
        toolBody
      );
      scrollPanelIntoView(sourceToolMount);
    }
    function blockEditor(block, needle) {
      const textArea = document.createElement("textarea");
      textArea.className = "modern-source-block-text";
      textArea.title = "Edit the reviewed source block text. This changes only the local DATA_DIR source block file, not the PDF.";
      textArea.value = block.text || "";
      const assignmentEdit = select(`modern-source-block-assignment-${block.id}`, "Assign this reviewed block to the kind of supplement data it represents.", [["", "Choose assignment"]]);
      for (const option of payload.assignment_options || []) assignmentEdit.appendChild(new Option(option, option));
      assignmentEdit.value = block.assignment || "unassigned";
      const actionsRow = actions();
      if (block.source_item_type !== "page-boundary candidate") {
        actionsRow.append(
          button("Save Block", "Save edited text, assignment, and review status for this source block.", async (btn) => runWithButtonProgress(btn, "Saving block...", async () => {
            await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(block.id)}`, {
              method: "PATCH",
              body: JSON.stringify({ text: textArea.value, assignment: assignmentEdit.value || "unassigned", review_status: "edited" }),
            });
            await reloadCurrentScan("Source block saved.");
          })),
          button("Split At Cursor", "Split this source block at the cursor position in the reviewed text field.", async (btn) => runWithButtonProgress(btn, "Splitting block...", async () => {
            await splitBlockAtCursor(block, textArea.value, textArea.selectionStart);
          })),
          button("Move Up", "Move this reviewed block above the previous reviewed block.", async (btn) => runWithButtonProgress(btn, "Moving block...", async () => {
            await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(block.id)}/move`, {
              method: "POST",
              body: JSON.stringify({ direction: "up" }),
            });
            await reloadCurrentScan("Source block moved up.");
          })),
          button("Move Down", "Move this reviewed block below the next reviewed block.", async (btn) => runWithButtonProgress(btn, "Moving block...", async () => {
            await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(block.id)}/move`, {
              method: "POST",
              body: JSON.stringify({ direction: "down" }),
            });
            await reloadCurrentScan("Source block moved down.");
          }))
        );
      }
      const editor = el("div", "modern-source-block-editor");
      const searchPreview = el("div", "modern-source-block-search-preview");
      if (searchTerms(needle).length) {
        searchPreview.append(el("strong", "", "Search hit preview"), highlightedEl("p", "modern-pre-wrap", block.text || "", needle));
      }
      editor.append(
        searchPreview,
        field("Reviewed text", textArea),
        field("Assignment", assignmentEdit),
        actionsRow
      );
      activeBlockEditor = { blockId: block.id, textArea };
      return editor;
    }
    function artworkEditor(item, categories) {
      activeBlockEditor = null;
      const editor = el("div", "modern-source-block-editor");
      const img = el("img", "modern-source-artwork-image");
      img.alt = item.title || item.id || "Artwork candidate";
      if (item.asset_url) img.src = item.asset_url;
      const titleInput = input("text", `modern-source-artwork-title-${item.id}`, "Name this artwork for later reuse.", item.title || "");
      const categorySelect = select(`modern-source-artwork-category-${item.id}`, "Categorise this artwork for future game use.", categories.map((category) => [category, category.replace(/_/g, " ")]));
      categorySelect.value = item.category || "unknown";
      const notesInput = document.createElement("textarea");
      notesInput.className = "modern-source-block-text compact";
      notesInput.title = "Review notes for this artwork candidate.";
      notesInput.value = item.notes || "";
      const artActions = actions();
      artActions.append(
        button("Save Artwork", "Save artwork name, category, and notes.", async (btn) => runWithButtonProgress(btn, "Saving artwork...", async () => {
          await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/artwork/${encodeURIComponent(item.id)}`, {
            method: "PATCH",
            body: JSON.stringify({ title: titleInput.value, category: categorySelect.value, notes: notesInput.value, review_status: "checked" }),
          });
          await reloadCurrentScan("Artwork review saved.");
        }))
      );
      editor.append(
        img,
        field("Artwork name", titleInput),
        field("Artwork category", categorySelect),
        field("Artwork notes", notesInput),
        artActions
      );
      return editor;
    }
    function tableDraftEditor(table, sourceText = "", needle = "") {
      activeBlockEditor = null;
      const editor = el("div", "modern-source-table-review-grid");
      const sourcePanel = el("div", "modern-source-block-editor");
      sourcePanel.append(
        modernInfoPanel("Source block", table.page_label || "PDF source", [
          { label: "Block id", value: table.source_block_id || "Manual table" },
          { label: "Source PDF", value: table.source_pdf || payload.source_pdf || "Source PDF" },
          { label: "Parser status", value: table.parser_status || "draft" },
        ], "Exact extracted text remains beside the machine table draft for review."),
        highlightedEl("p", "modern-pre-wrap modern-source-preview-text tall", sourceText || "No source text available.", needle)
      );
      const draftPanel = el("div", "modern-source-block-editor");
      const tableIdInput = input("text", `modern-source-table-id-${table.id || "new"}`, "Stable machine id for this reviewed table. Use lowercase words separated by underscores.", table.id || "");
      const titleInput = input("text", `modern-source-table-title-${table.id || "new"}`, "Human-readable table title from the PDF.", table.title || "");
      const notesInput = document.createElement("textarea");
      notesInput.className = "modern-source-block-text compact";
      notesInput.title = "Reviewer notes about parsing, uncertain rows, or future loader work.";
      notesInput.value = table.notes || "";
      const rowsMount = el("div", "modern-table-draft-rows");
      function addDraftRow(row = {}) {
        const rowNode = el("div", "modern-table-draft-row");
        const keyInput = input("text", "", "Dice result, key, range, or lookup value.", row.key || "");
        const resultInput = input("text", "", "Machine-readable row text. Keep wording reviewed against the PDF before promoting.", row.result || "");
        const noteInput = input("text", "", "Optional row note or uncertainty marker.", row.notes || "");
        const deleteButton = button("Delete Row", "Remove this draft row from the reviewed table.", () => rowNode.remove());
        rowNode.append(field("Key", keyInput), field("Result", resultInput), field("Notes", noteInput), deleteButton);
        rowsMount.appendChild(rowNode);
      }
      for (const row of table.rows || []) addDraftRow(row);
      if (!rowsMount.children.length) addDraftRow();
      const tableActions = actions();
      tableActions.append(
        button("Add Row", "Add one editable row to this machine table draft.", () => addDraftRow()),
        button("Save Reviewed Table", "Save this table draft into DATA_DIR/Supplements/_sources beside the source block scan.", async (btn) => runWithButtonProgress(btn, "Saving reviewed table...", async () => {
          const tableId = String(tableIdInput.value || "").trim();
          if (!tableId) throw new Error("Enter a table id before saving.");
          const rows = [...rowsMount.querySelectorAll(".modern-table-draft-row")].map((rowNode) => {
            const inputs = rowNode.querySelectorAll("input");
            return {
              key: inputs[0]?.value || "",
              result: inputs[1]?.value || "",
              notes: inputs[2]?.value || "",
            };
          });
          await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/tables/${encodeURIComponent(tableId)}`, {
            method: "PUT",
            body: JSON.stringify({
              ...table,
              id: tableId,
              title: titleInput.value,
              notes: notesInput.value,
              rows,
              review_status: "reviewed",
            }),
          });
          await reloadCurrentScan("Reviewed table saved.");
        }))
      );
      draftPanel.append(
        field("Table id", tableIdInput),
        field("Table title", titleInput),
        field("Table notes", notesInput),
        rowsMount,
        tableActions
      );
      editor.append(sourcePanel, draftPanel);
      return editor;
    }
    async function openTableDraftFromBlock(block, needle = "") {
      if (block.pdf_page) previewPdfPage(block.pdf_page);
      const draft = await api(`/api/supplements/source-scans/${encodeURIComponent(payload.source_id)}/blocks/${encodeURIComponent(block.id)}/table-draft`, {
        method: "POST",
        body: JSON.stringify({ title: block.page_label || "" }),
      });
      openSourceTool(`Table Draft - ${draft.table?.title || block.page_label || block.id}`, tableDraftEditor(draft.table || {}, block.text || "", needle));
    }
    function renderReviewedTablesPanel() {
      const panel = el("div", "modern-list");
      panel.appendChild(modernInfoPanel("Reviewed table drafts", `${reviewedTables.length} table draft(s)`, [
        { label: "Storage", value: "DATA_DIR/Supplements/_sources/<source>/source_blocks.json" },
        { label: "Status", value: reviewedTables.length ? "Local reviewed tables available" : "No reviewed table drafts yet" },
        { label: "Next step", value: "Assign a block as table, then use Draft Table." },
      ], "These are reviewed machine table drafts, not active game rules yet."));
      for (const table of reviewedTables) {
        const row = document.createElement("details");
        row.className = "modern-row";
        const summary = document.createElement("summary");
        summary.append(
          el("strong", "", table.title || table.id || "Reviewed table"),
          el("span", "muted", ` · ${(table.rows || []).length} row(s) · ${table.page_label || "source block"}`)
        );
        const sourceBlock = blocks.find((block) => block.id === table.source_block_id) || {};
        const tableActions = actions();
        tableActions.append(
          button("Edit Table Draft", "Open this reviewed table in the active review tool.", () => {
            if (table.pdf_page) previewPdfPage(table.pdf_page);
            openSourceTool(`Reviewed Table - ${table.title || table.id}`, tableDraftEditor(table, sourceBlock.text || "", search.value));
          })
        );
        row.append(
          summary,
          modernInfoPanel("Table summary", table.id || "reviewed table", [
            { label: "Title", value: table.title || "" },
            { label: "Rows", value: `${(table.rows || []).length}` },
            { label: "Source", value: table.page_label || table.source_block_id || "" },
            { label: "Review status", value: table.review_status || "draft" },
            { label: "Notes", value: table.notes || "None" },
          ], "Use Edit Table Draft to inspect source text beside machine rows."),
          tableActions
        );
        panel.appendChild(row);
      }
      return panel;
    }
    function renderSourceBlockTreeItem(block, needle) {
      const item = document.createElement("details");
      item.className = "modern-source-tree-item";
      item.addEventListener("toggle", () => {
        if (item.open && block.pdf_page) previewPdfPage(block.pdf_page);
      });
      const summary = document.createElement("summary");
      const selectBox = input("checkbox", `modern-source-block-select-${block.id}`, "Select this block for the left-side workbench controls.");
      selectBox.checked = selectedBlockIds.has(block.id);
      selectBox.addEventListener("click", (event) => event.stopPropagation());
      selectBox.addEventListener("change", () => {
        if (selectBox.checked) selectedBlockIds.add(block.id);
        else selectedBlockIds.delete(block.id);
        item.classList.toggle("modern-row-selected", selectedBlockIds.has(block.id));
        updateSelectionStatus();
      });
      summary.append(
        selectBox,
        el("strong", "", block.page_label || `p.${block.source_page || "?"}`),
        el("span", "muted", ` · ${block.source_item_type === "page-boundary candidate" ? "boundary" : `block ${block.block_index || "?"}`}`)
      );
      item.classList.toggle("modern-row-selected", selectedBlockIds.has(block.id));
      item.appendChild(summary);
      item.append(
        el("p", "muted", `${block.id || ""}${(block.extraction_methods || []).length ? ` · ${(block.extraction_methods || []).join(", ")}` : ""}`),
        highlightedEl("p", "modern-pre-wrap modern-source-preview-text", block.text || "", needle)
      );
      return item;
    }
    function renderArtworkTreePanel(items, needle) {
      const panel = el("div", "modern-source-tree-children");
      const categories = payload.artwork_categories || ["unknown"];
      if (!items.length) {
        panel.appendChild(el("p", "muted", "No artwork candidates match the current page/search filter."));
        return panel;
      }
      for (const item of items.slice(0, 80)) {
        const row = document.createElement("details");
        row.className = "modern-source-tree-item";
        row.addEventListener("toggle", () => {
          if (row.open && item.pdf_page) previewPdfPage(item.pdf_page);
        });
        const summary = document.createElement("summary");
        summary.append(
          el("strong", "", item.title || item.id || "Artwork candidate"),
          el("span", "muted", ` · ${item.page_label || `p.${item.source_page || "?"}`} · ${item.category || "unknown"}`)
        );
        const artActions = actions();
        artActions.append(
          button("✎ Edit", "Open this artwork candidate in the active review tool.", () => {
            if (item.pdf_page) previewPdfPage(item.pdf_page);
            openSourceTool(`${item.title || item.id || "Artwork candidate"} · ${item.category || "unknown"}`, artworkEditor(item, categories));
          })
        );
        row.append(
          summary,
          item.asset_url ? Object.assign(el("img", "modern-source-artwork-image compact"), { src: item.asset_url, alt: item.title || item.id || "Artwork candidate" }) : el("p", "muted", "No preview available."),
          highlightedEl("p", "muted", `${String(item.candidate_type || "embedded_image").replace(/_/g, " ")} · ${item.notes || "No notes"}`, needle),
          artActions
        );
        panel.appendChild(row);
      }
      if (items.length > 80) panel.appendChild(el("p", "muted", `Showing first 80 matching artwork candidates. ${items.length - 80} more match the current page/search filter.`));
      return panel;
    }
    function draw() {
      const needle = search.value;
      const assignmentNeedle = assignment.value;
      const activePage = Math.max(1, Number(pageInput.value || firstPdfPage) || 1);
      const hasSearch = Boolean(searchTerms(needle).length);
      const documentScope = reviewScope.value === "document" || hasSearch;
      const matches = sourceItems.filter((block) => {
        if (assignmentNeedle && block.assignment !== assignmentNeedle) return false;
        if (hasSearch && !assignmentNeedle && block.assignment === "ignore") return false;
        if (!documentScope) {
          const startPage = Number(block.pdf_page || 0);
          const endPage = Number(block.pdf_page_end || startPage);
          if (activePage < startPage || activePage > endPage) return false;
        }
        return modernTextMatchesNeedle(`${block.id || ""} ${block.page_label || ""} ${block.assignment || ""} ${block.text || ""}`, needle);
      });
      visibleSelectableBlockIds = matches
        .filter((block) => block.source_item_type !== "page-boundary candidate" && block.assignment !== "ignore")
        .map((block) => block.id)
        .filter(Boolean);
      const artworkMatches = artworkItems.filter((item) => {
        if (!documentScope && Number(item.pdf_page || 0) !== activePage) return false;
        return modernTextMatchesNeedle(`${item.id || ""} ${item.page_label || ""} ${item.category || ""} ${item.title || ""} ${item.notes || ""}`, needle);
      });
      const unassignedCount = blocks.filter((block) => (block.assignment || "unassigned") === "unassigned").length;
      const boundaryCount = candidates.length;
      const scopeText = hasSearch ? "search" : documentScope ? "document" : `PDF p.${activePage}`;
      results.replaceChildren(
        compactInfoStrip("Module contents", [
          { label: "Scope", value: scopeText },
          { label: "Text", value: `${matches.length}/${sourceItems.length}` },
          { label: "Unassigned", value: `${unassignedCount}` },
          { label: "Boundary", value: `${boundaryCount}` },
          { label: "Tables", value: `${reviewedTables.length}` },
          { label: "Artwork", value: `${artworkMatches.length}/${artworkItems.length}` },
        ], "Counts update as the current page, search, assignment filter, and manual review categories change.")
      );
      const groupRank = (key) => {
        if (key === "unassigned") return "00";
        if (key === "page_boundary_candidate") return "01";
        if (key === "ignore") return "99";
        return `10-${key}`;
      };
      const grouped = new Map();
      for (const block of matches) {
        const key = block.source_item_type === "page-boundary candidate" ? "page_boundary_candidate" : (block.assignment || "unassigned");
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(block);
      }
      const textTree = el("div", "modern-source-tree-children");
      const orderedGroups = Array.from(grouped.entries()).sort(([left], [right]) => groupRank(left).localeCompare(groupRank(right)));
      let rendered = 0;
      const renderLimit = 160;
      for (const [groupKey, groupBlocks] of orderedGroups) {
        if (rendered >= renderLimit) break;
        const branchBody = el("div", "modern-source-tree-children");
        for (const block of groupBlocks) {
          if (rendered >= renderLimit) break;
          rendered += 1;
          branchBody.appendChild(renderSourceBlockTreeItem(block, needle));
        }
        const groupTitle = groupKey === "page_boundary_candidate" ? "Page boundary candidates" : modernTitleFromKey(groupKey || "unassigned");
        textTree.appendChild(treeBranch(groupTitle, `${groupBlocks.length}`, branchBody, {
          open: groupKey === "unassigned" || hasSearch,
          hint: groupKey === "unassigned" ? "Primary review queue. Select blocks here, then use the left controls to assign, merge, move, edit, split, or draft tables." : "Assigned content remains in document order within this category.",
        }));
      }
      if (matches.length > renderLimit) textTree.appendChild(el("p", "muted", `Showing first ${renderLimit} matches. Narrow the search or filter to inspect the remaining ${matches.length - renderLimit}.`));
      const sourceTree = el("div", "modern-source-tree-children");
      sourceTree.append(
        treeBranch("Text blocks", `${matches.length}`, textTree, { open: true }),
        treeBranch("Reviewed tables", `${reviewedTables.length}`, renderReviewedTablesPanel(), { open: false }),
        treeBranch("Artwork", `${artworkMatches.length}`, renderArtworkTreePanel(artworkMatches, needle), { open: false })
      );
      results.appendChild(treeBranch(payload.source_id || "Source document", `${sourceItems.length + artworkItems.length + reviewedTables.length}`, sourceTree, {
        open: true,
        className: "modern-source-tree-root",
        hint: "Imported source document tree. Text, tables, artwork, and future data types sit under this document so review follows the PDF/source order.",
      }));
    }
    function renderArtworkPanel() {
      const panel = el("div", "modern-source-artwork-panel");
      const artworkResults = el("div", "modern-list");
      panel.appendChild(modernStatusRow("Artwork candidates", `${artworkItems.length} reviewed candidate(s)`, "Embedded image extraction is best-effort. If the PDF exposes no images, the app renders full PDF pages as review/crop candidates; reviewed metadata is preserved across re-extraction."));
      if (!artworkItems.length) {
        panel.appendChild(el("p", "muted", "No artwork candidates extracted yet. Use Extract Artwork Candidates from the source scan list after selecting the PDF."));
        return panel;
      }
      const categories = payload.artwork_categories || ["unknown"];
      function drawArtwork() {
        const activePage = Math.max(1, Number(pageInput.value || firstPdfPage) || 1);
        const needle = search.value;
        const hasSearch = Boolean(searchTerms(needle).length);
        const documentScope = reviewScope.value === "document" || hasSearch;
        const matches = artworkItems.filter((item) => {
          if (!documentScope && Number(item.pdf_page || 0) !== activePage) return false;
          return modernTextMatchesNeedle(`${item.id || ""} ${item.page_label || ""} ${item.category || ""} ${item.title || ""} ${item.notes || ""}`, needle);
        });
        const scopeTitle = hasSearch ? "Matching artwork" : documentScope ? "All artwork" : "Page artwork";
        const scopeHint = hasSearch
          ? "Search is showing matching artwork across this whole source document."
          : documentScope
            ? "Showing every artwork candidate in this document. Use Current PDF page when reviewing page-by-page beside the PDF preview."
            : `Showing artwork candidates for PDF page ${activePage}. Switch Review scope to Whole document to see all ${artworkItems.length}.`;
        artworkResults.replaceChildren(modernStatusRow(scopeTitle, `${matches.length} of ${artworkItems.length}`, scopeHint));
        for (const item of matches.slice(0, 80)) {
          const row = document.createElement("details");
          row.className = "modern-row";
          row.addEventListener("toggle", () => {
            if (row.open && item.pdf_page) previewPdfPage(item.pdf_page);
          });
          const summary = document.createElement("summary");
          summary.append(
            el("strong", "", item.title || item.id || "Artwork candidate"),
            el("span", "muted", ` · ${item.page_label || `p.${item.source_page || "?"}`} · ${item.category || "unknown"} · ${String(item.candidate_type || "embedded_image").replace(/_/g, " ")}`)
          );
          const img = el("img", "modern-source-artwork-image");
          img.alt = item.title || item.id || "Artwork candidate";
          if (item.asset_url) img.src = item.asset_url;
          const artActions = actions();
          artActions.append(
            button("Edit Artwork", "Open this artwork candidate in the active review tool without filling every row with edit fields.", () => {
              if (item.pdf_page) previewPdfPage(item.pdf_page);
              openSourceTool(`${item.title || item.id || "Artwork candidate"} · ${item.category || "unknown"}`, artworkEditor(item, categories));
            })
          );
          row.append(
            summary,
            img,
            modernInfoPanel("Artwork summary", item.title || item.id || "Artwork candidate", [
              { label: "Page", value: item.page_label || `p.${item.source_page || "?"}` },
              { label: "Category", value: item.category || "unknown" },
              { label: "Type", value: String(item.candidate_type || "embedded_image").replace(/_/g, " ") },
              { label: "Notes", value: item.notes || "None" },
            ], "Use Edit Artwork to change title, category, notes, and review status."),
            artActions
          );
          artworkResults.appendChild(row);
        }
        if (matches.length > 80) artworkResults.appendChild(el("p", "muted", `Showing first 80 matching artwork candidates. ${matches.length - 80} more match the current page/search filter.`));
      }
      redrawArtwork = drawArtwork;
      panel.appendChild(artworkResults);
      drawArtwork();
      return panel;
    }
    search.addEventListener("input", () => {
      sourceWorkbenchState.search = search.value || "";
      persistSourceWorkbenchState();
      draw();
      redrawArtwork();
    });
    assignment.addEventListener("change", () => {
      sourceWorkbenchState.assignment = assignment.value || "";
      persistSourceWorkbenchState();
      draw();
    });
    reviewScope.addEventListener("change", () => {
      sourceWorkbenchState.scope = reviewScope.value || "document";
      persistSourceWorkbenchState();
      draw();
      redrawArtwork();
    });
    mount.classList.remove("hidden");
    const reviewPanel = el("div", "modern-source-review-panel");
    const selectionActions = el("div", "modern-source-action-groups");
    selectionActions.append(
      actionGroup("Select", [selectVisibleButton, clearSelectionButton]),
      actionGroup("Assign", [applyAssignmentButton, ignorePhraseButton]),
      actionGroup("Blocks", [mergeSelectedButton, editSelectedButton, splitSelectedButton]),
      actionGroup("Extract", [draftTableButton]),
      actionGroup("Order", [moveUpButton, moveDownButton])
    );
    const controlFields = el("div", "modern-source-controls-grid");
    controlFields.append(
      field("Search", search),
      field("Scope", reviewScope),
      field("Filter", assignment),
      field("Assign to", bulkAssignment)
    );
    const blockTools = el("div", "modern-source-controls-panel");
    blockTools.append(
      compactInfoStrip("Source controls", [
        { label: "Selected", value: "blocks" },
        { label: "Target", value: "content tree" },
      ], "These controls affect selected text blocks in the module contents tree."),
      controlFields,
      selectionStatus,
      selectionActions
    );
    leftRail.append(blockTools, pdfViewer);
    reviewPanel.append(
      sourceToolMount,
      results
    );
    const reviewGrid = el("div", "modern-source-review-grid");
    reviewGrid.append(leftRail, reviewPanel);
    mount.replaceChildren(
      compactInfoStrip("Selected source scan", [
        { label: "Source", value: payload.source_id || "source" },
        { label: "Text", value: `${blocks.length}` },
        { label: "Boundary", value: `${candidates.length}` },
        { label: "Artwork", value: `${artworkItems.length}` },
        { label: "Tables", value: `${reviewedTables.length}` },
        { label: "Offset", value: `${payload.page_offset || 0}`, hint: "Used when PDF viewer pages differ from printed book pages." },
      ], `${payload.source_pdf || "Source PDF"} · local DATA_DIR/Supplements/_sources review data.`),
      reviewGrid
    );
    draw();
  }
  async function refreshSourceScans() {
    const payload = await api("/api/supplements/source-scans");
    const scans = payload.scans || [];
    const packages = payload.packages || [];
    sourceScanStatus.replaceChildren();
    if (!scans.length && !packages.length) {
      sourceScanStatus.appendChild(modernStatusRow("Source block scans", "No scans yet", "Use Scan Source Blocks after uploading or selecting a PDF."));
      return;
    }
    const moduleWorkbenchMount = el("div", "modern-source-module-workbench");
    const sourcePickerBar = el("div", "modern-source-picker-bar");
    const moduleSelect = select("modern-source-module-select", "Choose the imported supplement module to review. A module may contain source PDFs plus attached map/image assets.", [["", "Choose module"]]);
    const packageRows = packages.length
      ? packages
      : scans.map((scan) => ({
        supplement_id: scan.supplement_id || scan.source_id,
        supplement_title: scan.supplement_title || scan.source_id,
        source_count: 1,
        asset_count: 0,
        blocks: scan.blocks || 0,
        artwork: scan.artwork || 0,
        tables: scan.tables || 0,
        sources: [scan],
        assets: [],
      }));
    for (const pkg of packageRows) {
      const label = `${pkg.supplement_title || pkg.supplement_id || "Supplement Package"} (${pkg.source_count || 0} PDF${Number(pkg.source_count || 0) === 1 ? "" : "s"}, ${pkg.asset_count || 0} asset${Number(pkg.asset_count || 0) === 1 ? "" : "s"})`;
      moduleSelect.appendChild(new Option(label, pkg.supplement_id || ""));
    }
    if (sourceWorkbenchState.packageId && packageRows.some((pkg) => pkg.supplement_id === sourceWorkbenchState.packageId)) {
      moduleSelect.value = sourceWorkbenchState.packageId;
    } else if (packageRows[0]?.supplement_id) {
      moduleSelect.value = packageRows[0].supplement_id;
      sourceWorkbenchState.packageId = moduleSelect.value;
      persistSourceWorkbenchState();
    }
    async function openSelectedModule() {
      const pkg = packageRows.find((item) => item.supplement_id === moduleSelect.value) || packageRows[0];
      moduleWorkbenchMount.replaceChildren();
      sourcePickerBar.replaceChildren(field("Imported module", moduleSelect));
      if (!pkg) return;
      sourceWorkbenchState.packageId = pkg.supplement_id || "";
      persistSourceWorkbenchState();
      const sourceMount = el("div", "modern-source-scan-detail");
      const sources = pkg.sources || [];
      sourcePickerBar.appendChild(compactInfoStrip("Package", [
        { label: "PDFs", value: `${pkg.source_count || sources.length || 0}` },
        { label: "Assets", value: `${pkg.asset_count || 0}` },
        { label: "Blocks", value: `${pkg.blocks || 0}` },
        { label: "Artwork", value: `${pkg.artwork || 0}` },
        { label: "Tables", value: `${pkg.tables || 0}` },
      ], "Current supplement package counts. Source documents and package assets remain local review data until promoted into a playable supplement."));
      if (sources.length > 1) {
        const sourceSelect = select("modern-source-document-select", "Choose which source document inside this module to review.", []);
        for (const scan of sources) {
          sourceSelect.appendChild(new Option(`${scan.supplement_title || scan.source_id} (${scan.blocks || 0} blocks, ${scan.artwork || 0} artwork)`, scan.source_id));
        }
        sourceSelect.value = sources.some((scan) => scan.source_id === sourceWorkbenchState.sourceId)
          ? sourceWorkbenchState.sourceId
          : sources[0].source_id;
        sourceSelect.addEventListener("change", async () => {
          sourceWorkbenchState.sourceId = sourceSelect.value;
          sourceWorkbenchState.selectedBlockIds = new Set();
          persistSourceWorkbenchState();
          const detail = await api(`/api/supplements/source-scans/${encodeURIComponent(sourceSelect.value)}`);
          renderSourceScanDetail(detail, sourceMount);
        });
        sourcePickerBar.appendChild(field("Source document", sourceSelect));
      }
      moduleWorkbenchMount.appendChild(sourceMount);
      if (sources.length) {
        const activeSource = sources.find((scan) => scan.source_id === sourceWorkbenchState.sourceId) || sources[0];
        sourceWorkbenchState.sourceId = activeSource.source_id;
        persistSourceWorkbenchState();
        const detail = await api(`/api/supplements/source-scans/${encodeURIComponent(activeSource.source_id)}`);
        renderSourceScanDetail(detail, sourceMount);
      } else {
        sourceMount.appendChild(modernStatusRow("No source PDF scan", `${pkg.asset_count || 0} package asset(s)`, "This module currently has attached assets but no scanned PDF source blocks."));
      }
      if ((pkg.assets || []).length) {
        const assetList = el("div", "modern-list");
        appendAssetRows(pkg, assetList);
        moduleWorkbenchMount.appendChild(workbenchSection("Package assets", `${pkg.asset_count || 0} map/image/tile asset(s)`, assetList));
      }
    }
    moduleSelect.addEventListener("change", async () => {
      sourceWorkbenchState.packageId = moduleSelect.value;
      sourceWorkbenchState.sourceId = "";
      sourceWorkbenchState.selectedBlockIds = new Set();
      persistSourceWorkbenchState();
      await openSelectedModule();
    });
    sourceScanStatus.append(
      compactInfoStrip("Supplement source packages", [
        { label: "Packages", value: `${packages.length || scans.length}` },
        { label: "Source scans", value: `${scans.length}` },
        { label: "Rule", value: "same package id groups related files", hint: "Examples: main rules, adventure text, maps, extra sheets, errata, or bonus documents." },
      ], "A supplement package can contain multiple PDFs, maps, extra sheets, or bonus documents."),
      sourcePickerBar,
      moduleWorkbenchMount
    );
    function appendAssetRows(pkg, parent) {
      const categories = pkg.asset_categories || ["unknown", "world_map", "dungeon_map", "room_tile_sheet", "room_tile"];
      const selectedAssets = new Set();
      let lastAssetIndex = -1;
      const assets = pkg.assets || [];
      const assetIds = new Set(assets.map((asset) => String(asset.id || "")).filter(Boolean));
      const childAssetsByParent = new Map();
      for (const asset of assets) {
        const parentId = String(asset.parent_asset_id || "");
        if (!parentId) continue;
        if (!childAssetsByParent.has(parentId)) childAssetsByParent.set(parentId, []);
        childAssetsByParent.get(parentId).push(asset);
      }
      const topLevelAssets = assets.filter((asset) => !asset.parent_asset_id || !assetIds.has(String(asset.parent_asset_id || "")));
      function deleteAsset(assetId) {
        return api(`/api/supplements/source-packages/${encodeURIComponent(pkg.supplement_id)}/assets/${encodeURIComponent(assetId)}`, { method: "DELETE" });
      }
      async function deleteAssetAndChildren(asset) {
        for (const child of childAssetsByParent.get(String(asset.id || "")) || []) {
          if (child.id) await deleteAsset(child.id);
        }
        if (asset.id) await deleteAsset(asset.id);
      }
      function renderChildAssetList(childAssets) {
        const childPanel = el("div", "modern-list");
        const selectedChildren = new Set();
        let lastChildIndex = -1;
        const childStatus = el("p", "muted", "No extracted tiles selected.");
        function updateChildStatus() {
          childStatus.textContent = selectedChildren.size ? `${selectedChildren.size} extracted tile asset(s) selected.` : "No extracted tiles selected.";
        }
        const childActions = actions("modern-row-actions");
        childActions.append(
          button("Delete Selected Tiles", "Delete selected child tile assets under this source sheet. Shift-click tile checkboxes to select a range.", async (btn) => runWithButtonProgress(btn, "Deleting selected tiles...", async () => {
            if (!selectedChildren.size) throw new Error("Select one or more extracted tiles first.");
            if (!window.confirm(`Delete ${selectedChildren.size} selected extracted tile asset(s)? This removes the imported image files.`)) return;
            for (const assetId of Array.from(selectedChildren)) await deleteAsset(assetId);
            selectedChildren.clear();
            await refreshSourceScans();
            setStatus("Selected extracted tile assets deleted.");
          }))
        );
        childPanel.append(modernStatusRow("Extracted tiles", `${childAssets.length} child tile/art asset(s)`, "Tiles produced from this source sheet are kept here so the workbench follows the supplement document instead of becoming one long flat asset list."), childStatus, childActions);
        for (const [childIndex, child] of childAssets.entries()) {
          const childRow = document.createElement("details");
          childRow.className = "modern-row compact";
          const childSummary = document.createElement("summary");
          const childSelect = input("checkbox", `modern-package-child-asset-select-${pkg.supplement_id}-${child.id}`, "Select this extracted tile for bulk delete.");
          childSelect.addEventListener("click", (event) => {
            event.stopPropagation();
            childSelect.dataset.shiftClick = event.shiftKey ? "1" : "0";
          });
          childSelect.addEventListener("change", () => {
            if (childSelect.dataset.shiftClick === "1" && lastChildIndex >= 0) {
              const [start, end] = [lastChildIndex, childIndex].sort((left, right) => left - right);
              for (let index = start; index <= end; index += 1) {
                const rangeAsset = childAssets[index];
                if (rangeAsset?.id) selectedChildren.add(rangeAsset.id);
                const box = document.getElementById(`modern-package-child-asset-select-${pkg.supplement_id}-${rangeAsset?.id}`);
                if (box) box.checked = true;
              }
            } else if (childSelect.checked) {
              selectedChildren.add(child.id);
            } else {
              selectedChildren.delete(child.id);
            }
            childSelect.dataset.shiftClick = "0";
            lastChildIndex = childIndex;
            updateChildStatus();
          });
          childSummary.append(
            childSelect,
            el("strong", "", child.title || child.filename || child.id || "Extracted tile"),
            el("span", "muted", ` · ${child.category || "room_tile"} · ${Math.round((child.size_bytes || 0) / 1024)} KB`)
          );
          childRow.appendChild(childSummary);
          if (child.asset_url) {
            const childPreview = el("img", "modern-source-artwork-image compact");
            childPreview.alt = child.filename || "Extracted tile";
            childPreview.src = child.asset_url;
            childRow.appendChild(childPreview);
          }
          const childRowActions = actions("modern-row-actions");
          if (child.asset_url) childRowActions.append(link("Open Tile", child.asset_url, "Open this extracted tile asset in a new tab.", "link-button secondary"));
          childRowActions.append(
            button("Delete Tile", "Delete this extracted child tile asset.", async (btn) => runWithButtonProgress(btn, "Deleting tile...", async () => {
              if (!window.confirm(`Delete ${child.title || child.filename || child.id}? This removes the imported tile image file.`)) return;
              await deleteAsset(child.id);
              await refreshSourceScans();
              setStatus("Extracted tile asset deleted.");
            }))
          );
          childRow.append(
            modernStatusRow("Source", child.filename || child.id || "Extracted tile", child.notes || "Child asset generated from this source sheet."),
            childRowActions
          );
          childPanel.appendChild(childRow);
        }
        return childPanel;
      }
      const bulkActions = actions("modern-row-actions");
      const bulkStatus = el("p", "muted", "No package assets selected.");
      function setAssetSelection(assetId, checked) {
        if (checked) selectedAssets.add(assetId);
        else selectedAssets.delete(assetId);
        bulkStatus.textContent = selectedAssets.size ? `${selectedAssets.size} package asset(s) selected.` : "No package assets selected.";
      }
      bulkActions.append(
        button("Delete Selected Assets", "Delete all selected package source assets. Shift-click asset checkboxes to select a range.", async (btn) => runWithButtonProgress(btn, "Deleting selected assets...", async () => {
          if (!selectedAssets.size) throw new Error("Select one or more package assets first.");
          if (!window.confirm(`Delete ${selectedAssets.size} selected package asset(s)? This removes the imported image files.`)) return;
          for (const asset of topLevelAssets) {
            if (selectedAssets.has(asset.id)) await deleteAssetAndChildren(asset);
          }
          selectedAssets.clear();
          await refreshSourceScans();
          setStatus("Selected package source assets deleted.");
        }))
      );
      parent.append(
        modernInfoPanel("Package Assets", `${topLevelAssets.length} source asset(s), ${assets.length - topLevelAssets.length} extracted child asset(s)`, [
          { label: "Source assets", value: `${topLevelAssets.length}`, hint: "Original package-level maps, handouts, tile sheets, and imported images." },
          { label: "Extracted children", value: `${assets.length - topLevelAssets.length}`, hint: "Tiles or artwork extracted from a parent source asset." },
          { label: "Layout", value: "Source assets first; extracted children nested under their parent.", hint: "This keeps tools and generated assets from overwhelming the package list." },
        ], "Asset rows remain collapsed by default. Select several with checkboxes, including shift-click ranges, then delete them together."),
        bulkStatus,
        bulkActions
      );
      for (const [assetIndex, asset] of topLevelAssets.entries()) {
        const row = document.createElement("details");
        row.className = "modern-row";
        const summary = document.createElement("summary");
        const assetSelect = input("checkbox", `modern-package-asset-select-${pkg.supplement_id}-${asset.id}`, "Select this package asset for bulk delete.");
        assetSelect.addEventListener("click", (event) => {
          event.stopPropagation();
          assetSelect.dataset.shiftClick = event.shiftKey ? "1" : "0";
        });
        assetSelect.addEventListener("change", (event) => {
          if (assetSelect.dataset.shiftClick === "1" && lastAssetIndex >= 0) {
            const [start, end] = [lastAssetIndex, assetIndex].sort((left, right) => left - right);
            for (let index = start; index <= end; index += 1) {
              const rangeAsset = topLevelAssets[index];
              if (rangeAsset?.id) selectedAssets.add(rangeAsset.id);
              const box = document.getElementById(`modern-package-asset-select-${pkg.supplement_id}-${rangeAsset?.id}`);
              if (box) box.checked = true;
            }
          } else {
            setAssetSelection(asset.id, assetSelect.checked);
          }
          assetSelect.dataset.shiftClick = "0";
          lastAssetIndex = assetIndex;
          bulkStatus.textContent = selectedAssets.size ? `${selectedAssets.size} package asset(s) selected.` : "No package assets selected.";
        });
        summary.append(
          assetSelect,
          el("strong", "", asset.title || asset.filename || asset.id || "Package asset"),
          el("span", "muted", ` · ${asset.category || "unknown"} · ${Math.round((asset.size_bytes || 0) / 1024)} KB`)
        );
        row.appendChild(summary);
        const titleInput = input("text", `modern-package-asset-title-${pkg.supplement_id}-${asset.id}`, "Name this artwork/map resource for the future supplement module.", asset.title || asset.filename || "");
        const categorySelect = select(`modern-package-asset-category-${pkg.supplement_id}-${asset.id}`, "Assign this source image to the supplement artwork/map/tile bucket it represents.", categories.map((category) => [category, category.replace(/_/g, " ")]));
        categorySelect.value = asset.category || "unknown";
        const notesInput = document.createElement("textarea");
        notesInput.className = "modern-source-block-text compact";
        notesInput.title = "Review notes for this package image source asset.";
        notesInput.value = asset.notes || "";
        const rowActions = actions("modern-row-actions");
        const assetToolMount = el("div", "modern-asset-tool-panel hidden");
        function openAssetTool(title, toolBody, afterOpen = () => {}) {
          assetToolMount.classList.remove("hidden");
          assetToolMount.replaceChildren(
            modernStatusRow("Active asset tool", title, "Asset tools open here only when selected. The source asset and extracted child assets remain below as review data."),
            toolBody
          );
          afterOpen();
          scrollPanelIntoView(assetToolMount);
        }
        rowActions.append(
          button("Save Asset", "Save title, assignment category, and notes for this package source image.", async (btn) => runWithButtonProgress(btn, "Saving asset...", async () => {
            await api(`/api/supplements/source-packages/${encodeURIComponent(pkg.supplement_id)}/assets/${encodeURIComponent(asset.id)}`, {
              method: "PATCH",
              body: JSON.stringify({ title: titleInput.value, category: categorySelect.value, notes: notesInput.value, review_status: "checked" }),
            });
            await refreshSourceScans();
            setStatus("Package source asset saved.");
          }))
        );
        rowActions.append(
          button("Delete Asset", "Delete this package source asset and remove its image file from DATA_DIR. Use this to remove unwanted auto-split tiles.", async (btn) => runWithButtonProgress(btn, "Deleting asset...", async () => {
            if (!window.confirm(`Delete ${asset.title || asset.filename || asset.id}? This removes the imported package image file.`)) return;
            await deleteAssetAndChildren(asset);
            await refreshSourceScans();
            setStatus("Package source asset deleted.");
          }))
        );
        if (asset.asset_url) rowActions.append(link("Open Asset", asset.asset_url, "Open this imported package source asset in a new tab.", "link-button secondary"));
        row.append(field("Asset title", titleInput), field("Artwork/module assignment", categorySelect), field("Asset notes", notesInput), rowActions, assetToolMount);
        if (asset.asset_url) {
          const preview = el("img", "modern-source-artwork-image");
          preview.alt = asset.filename || "Package source asset";
          preview.src = asset.asset_url;
          const sourceAssetPanel = el("div", "modern-source-asset-data");
          sourceAssetPanel.append(
            modernStatusRow("Whole source asset", asset.filename || asset.id || "Imported image", "This is the original imported package asset. Use the row buttons above to extract masked artwork or auto-split a regular grid."),
            preview
          );
          row.appendChild(sourceAssetPanel);
          const maskCrop = el("div", "modern-list");
          const maskName = input("text", `modern-package-asset-mask-name-${pkg.supplement_id}-${asset.id}`, "Name or die-roll id for this masked tile/art resource, such as 01, 12, chapel, or north_bridge.", "");
          const shapeMode = select(`modern-package-asset-mask-shape-${pkg.supplement_id}-${asset.id}`, "Shape to draw into the additive mask.", [["rect", "Rectangle / square"], ["ellipse", "Circle / oval"]]);
          const maskMode = select(`modern-package-asset-mask-mode-${pkg.supplement_id}-${asset.id}`, "Choose Draw mode to create mask shapes, or Pan mode to move around a zoomed image.", [["draw", "Draw Mode"], ["pan", "Pan Mode"]]);
          const maskViewport = el("div", "modern-mask-canvas-viewport");
          const maskCanvas = document.createElement("canvas");
          maskCanvas.className = "modern-mask-canvas";
          maskViewport.appendChild(maskCanvas);
          const maskStatus = el("p", "muted", "Open this section, then drag on the image to add mask shapes.");
          const maskShapes = [];
          let maskDragging = false;
          let panDragging = false;
          let maskStart = null;
          let panStart = null;
          let draftShape = null;
          let maskZoom = 1;
          let maskPanX = 0;
          let maskPanY = 0;
          let maskViewInitialized = false;
          function clamp(value, min, max) {
            return Math.max(min, Math.min(max, value));
          }
          function updateMaskStatus() {
            const modeText = maskMode.value === "pan" ? "Pan mode: drag to move the zoomed image." : `Draw mode: drag to add ${shapeMode.value === "ellipse" ? "a circle/oval" : "a square/rectangle"}.`;
            maskStatus.textContent = `${maskShapes.length} saved mask shape(s). Zoom ${Math.round(maskZoom * 100)}%. ${modeText}`;
          }
          function applyMaskTransform() {
            maskCanvas.style.transform = `translate(${maskPanX}px, ${maskPanY}px) scale(${maskZoom})`;
            maskCanvas.classList.toggle("is-panning", maskMode.value === "pan");
            updateMaskStatus();
          }
          function resetMaskView() {
            if (!preview.complete || !preview.naturalWidth || !preview.naturalHeight) return;
            const viewportWidth = Math.max(320, maskViewport.clientWidth || 980);
            const viewportHeight = Math.max(240, Math.min(window.innerHeight * 0.72, 760));
            maskZoom = clamp(Math.min(viewportWidth / preview.naturalWidth, viewportHeight / preview.naturalHeight, 1), 0.08, 8);
            maskPanX = 0;
            maskPanY = 0;
            maskViewInitialized = true;
            applyMaskTransform();
          }
          function zoomMask(delta, focusEvent = null) {
            const previousZoom = maskZoom;
            const nextZoom = clamp(maskZoom * delta, 0.08, 8);
            if (Math.abs(nextZoom - previousZoom) < 0.001) return;
            if (focusEvent) {
              const rect = maskCanvas.getBoundingClientRect();
              const focusX = focusEvent.clientX - rect.left;
              const focusY = focusEvent.clientY - rect.top;
              maskPanX -= focusX * (nextZoom / previousZoom - 1);
              maskPanY -= focusY * (nextZoom / previousZoom - 1);
            }
            maskZoom = nextZoom;
            applyMaskTransform();
          }
          function canvasPoint(event) {
            const rect = maskCanvas.getBoundingClientRect();
            const scaleX = maskCanvas.width / rect.width;
            const scaleY = maskCanvas.height / rect.height;
            return { x: (event.clientX - rect.left) * scaleX, y: (event.clientY - rect.top) * scaleY };
          }
          function normalizeShape(left, right, type) {
            const x = Math.min(left.x, right.x);
            const y = Math.min(left.y, right.y);
            return { type, x, y, w: Math.abs(right.x - left.x), h: Math.abs(right.y - left.y) };
          }
          function drawMaskCanvas() {
            if (!preview.complete || !preview.naturalWidth || !preview.naturalHeight) return;
            maskCanvas.width = Math.max(1, Math.round(preview.naturalWidth));
            maskCanvas.height = Math.max(1, Math.round(preview.naturalHeight));
            const ctx = maskCanvas.getContext("2d");
            ctx.clearRect(0, 0, maskCanvas.width, maskCanvas.height);
            ctx.drawImage(preview, 0, 0, maskCanvas.width, maskCanvas.height);
            ctx.lineWidth = 3;
            for (const shape of maskShapes.concat(draftShape ? [draftShape] : [])) {
              ctx.save();
              ctx.fillStyle = "rgba(201, 162, 39, 0.24)";
              ctx.strokeStyle = "#f5d66b";
              ctx.beginPath();
              if (shape.type === "ellipse") ctx.ellipse(shape.x + shape.w / 2, shape.y + shape.h / 2, Math.abs(shape.w / 2), Math.abs(shape.h / 2), 0, 0, Math.PI * 2);
              else ctx.rect(shape.x, shape.y, shape.w, shape.h);
              ctx.fill();
              ctx.stroke();
              ctx.restore();
            }
            if (!maskViewInitialized) resetMaskView();
            else applyMaskTransform();
          }
          preview.addEventListener("load", drawMaskCanvas);
          maskCanvas.addEventListener("pointerdown", (event) => {
            if (!preview.complete || !preview.naturalWidth || !preview.naturalHeight) return;
            if (maskMode.value === "pan") {
              panDragging = true;
              panStart = { x: event.clientX, y: event.clientY, panX: maskPanX, panY: maskPanY };
              maskCanvas.setPointerCapture(event.pointerId);
              return;
            }
            maskDragging = true;
            maskCanvas.setPointerCapture(event.pointerId);
            maskStart = canvasPoint(event);
            draftShape = null;
          });
          maskCanvas.addEventListener("pointermove", (event) => {
            if (panDragging && panStart) {
              maskPanX = panStart.panX + event.clientX - panStart.x;
              maskPanY = panStart.panY + event.clientY - panStart.y;
              applyMaskTransform();
              return;
            }
            if (!maskDragging || !maskStart) return;
            draftShape = normalizeShape(maskStart, canvasPoint(event), shapeMode.value);
            drawMaskCanvas();
          });
          maskCanvas.addEventListener("pointerup", (event) => {
            if (panDragging) {
              panDragging = false;
              panStart = null;
              try { maskCanvas.releasePointerCapture(event.pointerId); } catch { /* pointer already released */ }
              return;
            }
            if (!maskDragging || !maskStart) return;
            maskDragging = false;
            try { maskCanvas.releasePointerCapture(event.pointerId); } catch { /* pointer already released */ }
            const shape = normalizeShape(maskStart, canvasPoint(event), shapeMode.value);
            if (shape.w >= 4 && shape.h >= 4) maskShapes.push(shape);
            draftShape = null;
            maskStart = null;
            drawMaskCanvas();
          });
          maskViewport.addEventListener("wheel", (event) => {
            event.preventDefault();
            zoomMask(event.deltaY < 0 ? 1.12 : 0.88, event);
          }, { passive: false });
          shapeMode.addEventListener("change", updateMaskStatus);
          maskMode.addEventListener("change", applyMaskTransform);
          const maskActions = actions("modern-row-actions");
          maskActions.append(
            button("Zoom In", "Zoom into the mask crop image without changing its shape or saved crop coordinates.", () => zoomMask(1.2)),
            button("Zoom Out", "Zoom out of the mask crop image without changing its shape or saved crop coordinates.", () => zoomMask(0.84)),
            button("Reset View", "Fit the image back into the crop viewport and reset pan.", () => {
              resetMaskView();
              drawMaskCanvas();
            }),
            button("Undo Shape", "Remove the last mask shape.", () => {
              maskShapes.pop();
              drawMaskCanvas();
            }),
            button("Clear Mask", "Remove all mask shapes for this asset.", () => {
              maskShapes.length = 0;
              drawMaskCanvas();
            }),
            button("Save Mask Asset", "Save the combined mask as a transparent PNG package asset.", async (btn) => runWithButtonProgress(btn, "Saving masked asset...", async () => {
              const name = String(maskName.value || "").trim();
              if (!name) throw new Error("Enter a tile/art name or die roll first.");
              const blob = await maskToCanvasBlob(preview, maskShapes);
              const baseName = String(asset.filename || asset.id || "source-art").replace(/\.[^.]+$/, "");
              await uploadPackageAssetBlob(pkg, blob, `${baseName}-mask-${name}.png`, {
                asset_kind: categorySelect.value === "room_tile_sheet" ? "room_tile" : "map_or_image",
                category: categorySelect.value === "room_tile_sheet" ? "room_tile" : (categorySelect.value || "unknown"),
                title: name.match(/^\d+$/) ? `Tile ${name}` : name,
                parent_asset_id: asset.id || "",
                notes: `Masked asset from ${asset.filename || asset.id || "source image"} using ${maskShapes.length} additive shape(s).`,
              });
              await refreshSourceScans();
              setStatus(`Imported masked asset ${name}.`);
            }))
          );
          maskCrop.append(
            modernStatusRow("Mask Crop", "Draw rectangles, squares, circles, and ovals", "Use several additive shapes to cover an irregular hand-drawn tile or artwork. The saved asset becomes a transparent PNG cropped to the mask bounds."),
            field("Tile/art name or die roll", maskName),
            field("Mask shape", shapeMode),
            field("Canvas mode", maskMode),
            maskViewport,
            maskStatus,
            maskActions
          );
          rowActions.append(
            button("Manual Mask", "Open the manual mask cropper for this source asset. Use it for hand-drawn tiles or artwork that does not align to a regular grid.", () => {
              openAssetTool("Manual Mask - draw rectangles/squares/circles/ovals over this source asset", maskCrop, drawMaskCanvas);
            })
          );
          const splitter = el("div", "modern-list");
          const rowsInput = input("number", `modern-package-asset-rows-${pkg.supplement_id}-${asset.id}`, "Number of tile rows in this sheet.", "6");
          const colsInput = input("number", `modern-package-asset-cols-${pkg.supplement_id}-${asset.id}`, "Number of tile columns in this sheet.", "6");
          const labelsInput = document.createElement("textarea");
          labelsInput.className = "modern-source-block-text compact";
          labelsInput.title = "Tile names to apply in row order. Use D66 labels for Expanded Edition-style tile sheets.";
          labelsInput.value = d66Labels().join(", ");
          const splitActions = actions("modern-row-actions");
          splitActions.append(
            button("Fill D66 Labels", "Fill labels as 01-06, 11-16, 21-26, 31-36, 41-46, 51-56.", () => {
              labelsInput.value = d66Labels().join(", ");
            }),
            button("Split Grid To Tiles", "Crop this image into equal grid cells and import each crop as a room_tile package asset using the labels in row order.", async (btn) => runWithButtonProgress(btn, "Splitting tile sheet...", async () => {
              const image = preview;
              if (!image.complete || !image.naturalWidth || !image.naturalHeight) throw new Error("Image preview is not loaded yet.");
              const rows = Math.max(1, Number(rowsInput.value || 1));
              const cols = Math.max(1, Number(colsInput.value || 1));
              const labels = labelsInput.value.split(/[\s,;]+/).map((value) => value.trim()).filter(Boolean);
              const cellW = image.naturalWidth / cols;
              const cellH = image.naturalHeight / rows;
              let count = 0;
              for (let rowIndex = 0; rowIndex < rows; rowIndex += 1) {
                for (let colIndex = 0; colIndex < cols; colIndex += 1) {
                  const label = labels[count] || `${rowIndex + 1}-${colIndex + 1}`;
                  const blob = await imageToCanvasBlob(image, { x: colIndex * cellW, y: rowIndex * cellH, w: cellW, h: cellH });
                  const baseName = String(asset.filename || asset.id || "tile-sheet").replace(/\.[^.]+$/, "");
                  await uploadPackageAssetBlob(pkg, blob, `${baseName}-tile-${label}.png`, {
                    asset_kind: "room_tile",
                    category: "room_tile",
                    title: `Tile ${label}`,
                    parent_asset_id: asset.id || "",
                    notes: `Cropped from ${asset.filename || asset.id || "tile sheet"} at row ${rowIndex + 1}, column ${colIndex + 1}.`,
                  });
                  count += 1;
                }
              }
              await refreshSourceScans();
              setStatus(`Imported ${count} room tile asset(s) from ${asset.filename || "tile sheet"}.`);
            }))
          );
          splitter.append(
            modernStatusRow("Tile Sheet Splitter", "Manual equal-grid crop", "Assign the source image as Room Tile Sheet, set rows/columns, then split into room_tile assets. For EE D66 sheets, use labels 01-06, 11-16, etc."),
            field("Rows", rowsInput),
            field("Columns", colsInput),
            field("Tile labels", labelsInput),
            splitActions
          );
          rowActions.append(
            button("Auto Split", "Open the equal-grid tile splitter for this source asset. Use Manual Mask instead for hand-drawn or irregular sheets.", () => {
              openAssetTool("Auto Split - create named tiles from an equal grid", splitter);
            })
          );
        }
        const childAssets = childAssetsByParent.get(String(asset.id || "")) || [];
        if (childAssets.length) row.appendChild(workbenchSection("Extracted tiles", `${childAssets.length} child tile/art asset(s) under this source sheet`, renderChildAssetList(childAssets)));
        parent.appendChild(row);
      }
    }
    await openSelectedModule();
  }
  async function refreshList() {
    const payload = await api("/api/rules/pdfs");
    const override = payload.override_status || {};
    const textIndex = payload.local_text_index || {};
    const previousPdf = uploadedSelect.value;
    uploadedPdfSettings.clear();
    uploadedSelect.replaceChildren(new Option("Choose uploaded PDF", ""));
    for (const item of payload.uploaded || []) {
      uploadedPdfSettings.set(item.filename, item.source_settings || {});
      uploadedSelect.appendChild(new Option(`${item.filename} (${Math.round((item.size_bytes || 0) / 1024)} KB)`, item.filename));
    }
    if (previousPdf && uploadedPdfSettings.has(previousPdf)) uploadedSelect.value = previousPdf;
    const selectedSettings = uploadedPdfSettings.get(uploadedSelect.value);
    if (selectedSettings) {
      pageOffset.value = String(selectedSettings.page_offset || 0);
      supplementId.value = selectedSettings.supplement_id || suggestedSupplementId(uploadedSelect.value);
      supplementTitle.value = selectedSettings.supplement_title || suggestedSupplementTitle(uploadedSelect.value);
    }
    const indexedDocs = (textIndex.documents || []).map((item) => `${item.filename}: ${item.pages_indexed || 0} page(s)${item.page_offset ? `, offset ${item.page_offset}` : ""}`).join("; ");
    status.replaceChildren(
      compactInfoStrip("PDF import status", [
        { label: "Uploaded", value: `${(payload.uploaded || []).length}` },
        { label: "Index", value: textIndex.exists ? `${textIndex.entry_count || 0} entries / ${textIndex.document_count || 0} PDF(s)` : "none", hint: indexedDocs || "Build this from uploaded PDFs when you want exact PDF wording searchable in the player Rules Reference." },
        { label: "Narrative", value: override.exists ? `${override.rumors || 0} rumor(s), ${override.scenes || 0} scene(s), ${override.scene_branches || 0} branch(es)` : "none", hint: override.error || "Counts are read from DATA_DIR/tag_scene_narrative_overrides.json and show what generated Adventures Guild modules can use." },
        { label: "Warn", value: `${(override.extraction_warnings || []).length}`, hint: extractionWarningSummary(override.extraction_warnings) },
        { label: "Packaged", value: `${(payload.packaged || []).length}` },
        { label: "Boundary", value: "local DATA_DIR only", hint: "Exact PDF prose is written only to DATA_DIR files such as rules/rule_text_index.json and tag_scene_narrative_overrides.json. It is not committed or redistributed by the app repository." },
      ], "Compact status for uploaded PDFs, local exact text index, narrative extraction, and local-only copied prose.")
    );
  }
  uploadedSelect.addEventListener("change", () => {
    const selectedSettings = uploadedPdfSettings.get(uploadedSelect.value);
    pageOffset.value = String(selectedSettings?.page_offset || 0);
    supplementId.value = selectedSettings?.supplement_id || suggestedSupplementId(uploadedSelect.value);
    supplementTitle.value = selectedSettings?.supplement_title || suggestedSupplementTitle(uploadedSelect.value);
  });
  await refreshList();
  await refreshSourceScans();
  const row = actions();
  row.append(
    button("↑ PDF", "Upload PDF: upload the selected PDF into DATA_DIR/rules on the server.", async (btn) => runWithButtonProgress(btn, "Uploading PDF...", async () => {
      const chosen = file.files?.[0];
      if (!chosen) throw new Error("Choose a PDF file first.");
      const response = await fetch(`/api/rules/upload-pdf?filename=${encodeURIComponent(chosen.name)}`, {
        method: "POST",
        headers: { "Content-Type": "application/pdf" },
        body: await chosen.arrayBuffer(),
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
      const result = await response.json();
      setStatus(result.message || "PDF uploaded.");
      showRulePdfResult("ok", result.message || "PDF uploaded.", "Upload complete");
      await refreshList();
    })),
    button("↑ Asset", "Upload Package Map/Image: attach the selected map, handout, or image file to the current supplement package. Use this for separate PNG/JPG map files that belong with the same module.", async (btn) => runWithButtonProgress(btn, "Uploading package asset...", async () => {
      const chosen = sourceAssetFile.files?.[0];
      if (!chosen) throw new Error("Choose a map or image file first.");
      const metadata = sourceMetadataPayload();
      const response = await fetch(`/api/supplements/source-asset?filename=${encodeURIComponent(chosen.name)}&supplement_id=${encodeURIComponent(metadata.supplement_id)}&supplement_title=${encodeURIComponent(metadata.supplement_title)}&asset_kind=map_or_image`, {
        method: "POST",
        headers: { "Content-Type": chosen.type || "application/octet-stream" },
        body: await chosen.arrayBuffer(),
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
      const result = await response.json();
      setStatus(result.message || "Package source asset uploaded.");
      showRulePdfResult("ok", result.message || "Package source asset uploaded.", "Package asset uploaded");
      await refreshSourceScans();
    })),
    button("⌕ Index", "Index Exact Rules Text: extract exact searchable page text from the selected uploaded PDF into DATA_DIR/rules/rule_text_index.json. This is local/private user data and is not committed.", async (btn) => runWithButtonProgress(btn, "Indexing exact rules text...", async () => {
      try {
        showRulePdfResult("ok", "Indexing exact rules text. Large PDFs can take a little while; this panel will update when the server finishes.", "Indexing in progress");
        const result = await api("/api/rules/index-pdf-text", {
          method: "POST",
          body: JSON.stringify(sourceMetadataPayload()),
        });
        const message = result.message || `Indexed ${result.entries_indexed || 0} page(s).`;
        setStatus(message);
        showRulePdfResult("ok", `${message} Open Rules Reference and search for exact wording from this PDF.`, "Rules text indexed");
        await refreshList();
      } catch (error) {
        const message = error?.message || "Rules text indexing failed.";
        showRulePdfResult("error", message, "Indexing failed");
        throw error;
      }
    })),
    button("▤ Blocks", "Scan Source Blocks: extract unassigned review blocks from the selected PDF into DATA_DIR/Supplements/_sources for later manual classification as rules, foes, locations, tables, equipment, classes, states, terrain, or narrative.", async (btn) => runWithButtonProgress(btn, "Scanning PDF source blocks...", async () => {
      try {
        showRulePdfResult("ok", "Scanning PDF source blocks into the local supplement review workspace.", "Source scan in progress");
        const result = await api("/api/supplements/source-scan", {
          method: "POST",
          body: JSON.stringify(sourceMetadataPayload()),
        });
        const message = result.message || `Scanned ${result.blocks || 0} source block(s).`;
        setStatus(message);
        showRulePdfResult("ok", `${message} Manual assignment UI is the next workbench step.`, "Source scan complete");
        await refreshSourceScans();
      } catch (error) {
        const message = error?.message || "Source scan failed.";
        showRulePdfResult("error", message, "Source scan failed");
        throw error;
      }
    })),
    button("◇ Art", "Extract Artwork Candidates: extract embedded artwork candidates from the selected PDF into DATA_DIR/Supplements/_sources for naming and categorisation.", async (btn) => runWithButtonProgress(btn, "Extracting artwork...", async () => {
      try {
        showRulePdfResult("ok", "Extracting embedded artwork candidates into the local supplement review workspace.", "Artwork extraction in progress");
        const result = await api("/api/supplements/source-artwork", {
          method: "POST",
          body: JSON.stringify(sourceMetadataPayload()),
        });
        const message = result.message || `Extracted ${result.raw_artwork || 0} artwork candidate(s).`;
        setStatus(message);
        showRulePdfResult("ok", message, "Artwork extraction complete");
        await refreshSourceScans();
      } catch (error) {
        const message = error?.message || "Artwork extraction failed.";
        showRulePdfResult("error", message, "Artwork extraction failed");
        throw error;
      }
    })),
    button("TAG", "Extract Adventures Guild Narrative: extract supported Tales from The Adventures Guild Rumor/Scene prose from the selected uploaded PDF into DATA_DIR/tag_scene_narrative_overrides.json.", async (btn) => runWithButtonProgress(btn, "Extracting Adventures Guild narrative...", async () => {
      try {
        showRulePdfResult("ok", "Extracting Adventures Guild narrative into the local override file.", "Extraction in progress");
        const result = await api("/api/rules/extract-tag-narrative", {
          method: "POST",
          body: JSON.stringify({ filename: uploadedSelect.value, overwrite: overwrite.checked }),
        });
        const warningCount = (result.extraction_warnings || []).length;
        const message = `${result.message} ${result.changed_fields || 0} field(s) changed; ${result.skipped_existing_fields || 0} preserved. Rumors found: ${result.rumors_found || 0}; scenes found: ${result.scenes_found || 0}; scene branches found: ${result.scene_branches_found || 0}; extraction warnings: ${warningCount}.`;
        setStatus(message);
        showRulePdfResult("ok", message, "Extraction complete");
        await refreshList();
      } catch (error) {
        const message = error?.message || "Extraction failed.";
        showRulePdfResult("error", message, "Extraction failed");
        throw error;
      }
    })),
    link("Rules Ref", "/modern/rules-reference?search=local_exact", "Player Rules Reference: open the player Rules Reference and search exact wording from locally indexed PDFs.", "link-button secondary"),
    link("Narrative Ref", ruleReferenceHref("tag_local_narrative_overrides", "tag narrative overrides"), "Narrative Override Reference: open the Rules Reference entry for local narrative overrides.", "link-button secondary")
  );
  row.classList.add("modern-source-import-actions");
  const overwriteLine = el("label", "modern-check-row modern-source-overwrite");
  overwriteLine.title = overwrite.title;
  overwriteLine.append(overwrite, el("span", "", "Overwrite local edits"));
  const importGrid = el("div", "modern-source-import-grid");
  importGrid.append(
    field("Rules PDF", file),
    field("Package map/image", sourceAssetFile),
    field("Uploaded PDF", uploadedSelect),
    field("Package id", supplementId),
    field("Package title", supplementTitle),
    field("Printed page offset", pageOffset),
    overwriteLine
  );
  const importPanel = el("div", "modern-source-import-panel");
  importPanel.append(
    importGrid,
    row,
    el("p", "muted", "Use one package id for every PDF, map sheet, image, or bonus document in the same future supplement. Page offset example: PDF page 7 printed as page 1 uses -6.")
  );
  panel.append(
    importPanel,
    resultBox,
    status,
    sourceScanStatus,
    el("p", "muted", "Rules text indexing stores exact PDF page text only in DATA_DIR/rules/rule_text_index.json for private local search. Use Printed page offset when the PDF viewer page differs from the printed book page: if PDF page 7 is printed page 1, enter -6. Source block scans create local review files under DATA_DIR/Supplements/_sources for future manual assignment. Package map/image uploads create local source assets under DATA_DIR/Supplements/_sources/_package_assets. TAG narrative extraction currently supports Tales from The Adventures Guild Rumor/Scene prose. AES/protected PDFs require the server image to include the cryptography Python package. Exact copied prose is written only to DATA_DIR and is not committed to the app repository.")
  );
  return panel;
}

function renderDeveloperPreferences() {
  const panel = card("Developer Playtest Preferences", "Developer-only switches for diagnostics and repeatable playtesting. Normal Adventures Guild play should leave fixed result selection off so the app rolls from the printed tables.");
  const fixed = input("checkbox", "modern-dev-tag-fixed-result-selector", "Show fixed Adventures Guild result selectors in module generators. Use only for repeatable playtests; normal play should roll from the printed tables.");
  fixed.checked = Boolean(modernState.preferences?.show_tag_fixed_result_selector);
  const row = el("label", "modern-check-row");
  row.title = fixed.title;
  row.append(fixed, el("span", "", "Show Adventures Guild fixed-result selector"));
  const status = el("p", "muted", fixed.checked ? "Fixed result selectors are visible in Adventure Management." : "Fixed result selectors are hidden; generators roll normally.");
  fixed.addEventListener("change", async () => {
    modernState.preferences = await api("/api/preferences", {
      method: "PUT",
      body: JSON.stringify({ show_tag_fixed_result_selector: fixed.checked }),
    });
    status.textContent = fixed.checked
      ? "Fixed result selectors are visible in Adventure Management."
      : "Fixed result selectors are hidden; generators roll normally.";
    setStatus("Developer preference saved.");
  });
  panel.append(row, status);
  return panel;
}

function renderGuides() {
  const panel = card("Game Guides", "Standalone guide links and future player-facing guide list.");
  const row = actions();
  row.append(
    link("TAG Section Guide", "/docs/Checking/TAG_SECTION_GUIDE.html", "Open the TAG workflow guide."),
    link("Adventures Guild Test Checklist", "/docs/Checking/TAG_SECTION_GUIDE.html#manual-test-generated-tag-adventures", "Open the manual test checklist for generated Adventures Guild adventures."),
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
  const gate = card("Developer Unlock", "Enter the developer password to show maintenance tools.");
  const pw = input("password", "modern-dev-pw", "Developer password.");
  const tools = el("div", "modern-dev-tools hidden");
  const artworkMount = el("div", "modern-dev-artwork-manager hidden");
  const rulePdfMount = el("div", "modern-dev-rule-pdf-manager hidden");
  const row = actions();
  row.append(
    link("Adventure PDF Import", "/modern/developer", "Placeholder for future PDF adventure module import."),
    link("Adventure Module Editor", "/modern/developer", "Placeholder for future adventure module editor."),
    link("Adventure Module Creator", "/modern/developer", "Placeholder for future adventure-from-scratch creator."),
    link("Map Elements Editor", "/static/tile-editor.html", "Open the existing map element editor as its own page."),
    link("Icon Editor", "/static/icon-editor.html", "Open the existing icon editor as its own page."),
    link("Developer Reference", developerReferenceHref("", "developer reference"), "Open app-only implementation notes, workflow references, diagnostics, and maintenance boundaries.", "link-button secondary"),
    link("Developer Tables", developerTablesHref(), "Open internal app tables for workflows, registries, validation, package review, artwork, and diagnostics.", "link-button secondary"),
    button("PDF / Supplement Workbench", "Show or hide local PDF upload, exact text indexing, and specialist supplement extraction tools.", async () => {
      await toggleRevealedPanel(rulePdfMount, renderRulePdfManager, "PDF / Supplement Workbench opened.");
    }),
    button("Artwork Manager", "Show or hide the artwork slot manager for DATA_DIR/assets paths, missing files, and linked Rules Reference entries.", async () => {
      await toggleRevealedPanel(artworkMount, () => renderArtworkManager(), "Artwork Manager opened.");
    })
  );
  tools.appendChild(row);
  tools.appendChild(renderDeveloperPreferences());
  tools.appendChild(renderSupplementRegistryPanel());
  tools.appendChild(rulePdfMount);
  tools.appendChild(artworkMount);
  if (window.sessionStorage.getItem("ahazi-modern-dev-unlocked") === "1") tools.classList.remove("hidden");
  const unlock = button("Unlock", "Show developer tools when the password is correct.", async () => {
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
