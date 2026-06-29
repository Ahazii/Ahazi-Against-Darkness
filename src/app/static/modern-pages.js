const modernState = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  campaign: null,
  rulesProfiles: [],
  equipmentRows: [],
  rulesReference: [],
  tables: {},
};

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
  const rows = [["random", "Random Dungeon"]];
  for (const adventure of modernState.adventures) {
    if (kind === "ai" && !String(adventure.id || "").startsWith("ai-")) continue;
    if (kind === "imported" && String(adventure.id || "").startsWith("ai-")) continue;
    rows.push([adventure.id, adventure.title || adventure.id]);
  }
  return rows;
}

async function loadCore() {
  const [classes, characters, parties, adventures, campaign, profiles] = await Promise.all([
    api("/api/rules/classes"),
    api("/api/characters"),
    api("/api/parties"),
    api("/api/adventures"),
    api("/api/campaign"),
    api("/api/rules/profiles"),
  ]);
  modernState.classes = classes;
  modernState.characters = characters;
  modernState.parties = parties;
  modernState.adventures = adventures;
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
  const create = card("Create / Add Character", "Choose a class, enter a name, and create a roster hero.");
  const name = input("text", "modern-character-name", "Name for the new character.");
  const classSelect = select("modern-character-class", "Class for the new character.", modernState.classes.map((item) => [item.id, item.name]));
  create.append(field("Name", name), field("Class", classSelect));
  create.appendChild(button("Create", "Create this character in the roster.", async () => {
    await api("/api/characters", { method: "POST", body: JSON.stringify({ name: name.value, class_id: classSelect.value }) });
    setStatus("Character created.");
    await refreshCoreAndRender();
  }, ""));
  layout.appendChild(create);

  const list = card("Roster", "Heal, spend XP, or delete roster characters.");
  for (const character of modernState.characters) {
    const row = el("div", "modern-row");
    row.appendChild(el("strong", "", `${character.name} - ${character.class_name} L${character.level}`));
    row.appendChild(el("span", "muted", `HP ${character.current_life}/${character.max_life} · XP ${character.xp || 0} · ${character.gold || 0}gp · ${character.clues || 0} Clues`));
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
    list.appendChild(row);
  }
  layout.appendChild(list);
  rootEl.appendChild(layout);
}

function troupeMemberIds() {
  return (modernState.campaign?.tag_troupe_member_character_ids || []).filter(Boolean);
}

function renderTroupes() {
  const campaign = modernState.campaign || {};
  const panel = card("Troupe Roster", "The troupe is the wider TAG character company; the active party is selected from these members.");
  const name = input("text", "modern-troupe-name", "Name of the TAG troupe.", campaign.tag_troupe_name || "Adventuring Troupe");
  const add = select("modern-troupe-add", "Roster character to add to the troupe.", characterOptions("Choose member to add"));
  const remove = select("modern-troupe-remove", "Troupe character to remove.", [["", "Choose member to remove"], ...troupeMemberIds().map((id) => {
    const c = modernState.characters.find((item) => item.id === id);
    return [id, c ? c.name : id];
  })]);
  const active = select("modern-troupe-active", "Select up to four active troupe members.", troupeMemberIds().map((id) => {
    const c = modernState.characters.find((item) => item.id === id);
    return [id, c ? c.name : id];
  }));
  active.multiple = true;
  active.size = Math.max(4, Math.min(8, troupeMemberIds().length || 4));
  for (const option of active.options) option.selected = (campaign.tag_troupe_active_character_ids || []).includes(option.value);
  panel.append(field("Troupe name", name), field("Add member", add), field("Remove member", remove), field("Active members", active));
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

  const travel = card("Travel / Home Settlement", "Move the troupe's settlement focus and record TAG travel.");
  const settlement = input("text", "modern-settlement-name", "Current home settlement name.", campaign.settlement_name || "Home Settlement");
  const size = select("modern-settlement-size", "Current settlement size modifier.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
  size.value = String(campaign.settlement_size ?? 0);
  const dest = input("text", "modern-travel-destination", "Destination settlement name.");
  travel.append(field("Home settlement", settlement), field("Size", size), field("Travel destination", dest));
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
  rootEl.append(panel, travel);
}

function renderGuild() {
  const campaign = modernState.campaign || {};
  const panel = card("Adventurers Guild", "Guild rules are separate from troupe membership: coffers, obligations, benefits, and suspension live here.");
  const active = input("checkbox", "modern-guild-active", "Enable Adventurers Guild membership for the troupe.");
  active.checked = Boolean(campaign.tag_guild_member);
  const coffers = input("number", "modern-guild-coffers-page", "Shared Guild coffers in gp.", String(campaign.tag_guild_coffers_gp || 0));
  const actionCharacter = select("modern-guild-character", "Character receiving Guild resurrection funding or Guild spell handling.", characterOptions("Choose character"));
  const amount = input("number", "modern-guild-amount", "Gold amount for Guild loot share, resurrection funding, or notes.", "0");
  const itemName = input("text", "modern-guild-availability-item", "Item name for the once-per-adventure Guild availability reroll.");
  panel.append(field("Guild active", active), field("Guild coffers gp", coffers), field("Character", actionCharacter), field("Amount gp", amount), field("Availability item", itemName));
  const row = actions();
  row.append(
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
    button("Run Upkeep", "Charge 10% upkeep from Guild coffers and suspend benefits at 0 gp.", async () => {
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
    button("Pay Resurrection", "Pay a Level 2+ member's resurrection attempt from active Guild coffers.", async () => {
      const result = await api("/api/campaign/tag/finance-action", {
        method: "POST",
        body: JSON.stringify({ character_id: actionCharacter.value, finance_action: "guild_resurrection_fund", amount_gp: Number(amount.value || 0) }),
      });
      modernState.campaign = result.campaign;
      setStatus(result.entry?.result_text || "Guild resurrection funding logged.");
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
    }),
    button("Guild Job Lead", "Create a TAG Guild Job adventure lead.", async () => {
      const result = await api("/api/campaign/tag/create-adventure", { method: "POST", body: JSON.stringify({ lead_type: "guild_job", detail: "" }) });
      modernState.campaign = result.campaign;
      modernState.adventures = await api("/api/adventures");
      setStatus(`Created ${result.title}.`);
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  const benefits = card("Guild Benefits / Obligations", "Rules-complete UI surface for TAG p.68 Guild management.");
  const list = el("ul", "modern-check-list");
  [
    "5000 gp starting coffers when Guild membership starts.",
    "10% upkeep after each month/adventure; benefits suspend at 0 gp.",
    "Free Guild ledger deposits; individual TAG bank accounts remain separate.",
    "10% discount on mundane equipment, free martial arts training, free ledger deposits, and cartographer bonus require active benefits and coffers above 0 gp.",
    "Guild jobs, resurrection funding, 50% monetary loot share, and the once-per-adventure availability reroll are exposed here for playtest tracking.",
    "Adventure completion creates Guild closeout prompts here; leaving restriction enforcement remains a manual signoff task.",
  ].forEach((text) => list.appendChild(el("li", "", text)));
  benefits.appendChild(el("p", "modern-home-status", `Benefits ${campaign.tag_guild_member && campaign.tag_guild_coffers_gp > 0 ? "active" : "suspended/inactive"} · availability reroll ${campaign.tag_guild_availability_reroll_used ? "used" : "available"}.`));
  benefits.appendChild(list);
  rootEl.append(panel, renderCloseoutTasks("Guild Closeout", ["guild", "xp"]), benefits);
}

function renderParties() {
  const create = card("Create Party", "Choose exactly four different roster heroes.");
  const name = input("text", "modern-party-name", "Name of this saved party.");
  create.appendChild(field("Party name", name));
  const picks = [];
  for (let i = 0; i < 4; i += 1) {
    const pick = select(`modern-party-member-${i}`, `Party slot ${i + 1}.`, characterOptions(`Slot ${i + 1}`));
    picks.push(pick);
    create.appendChild(field(`Slot ${i + 1}`, pick));
  }
  create.appendChild(button("Save Party", "Create a four-character party.", async () => {
    await api("/api/parties", { method: "POST", body: JSON.stringify({ name: name.value, character_ids: picks.map((item) => item.value) }) });
    setStatus("Party saved.");
    await refreshCoreAndRender();
  }, ""));
  const list = card("Saved Parties", "Heal or delete saved parties.");
  for (const party of modernState.parties) {
    const row = el("div", "modern-row");
    const names = party.character_ids.map((id) => modernState.characters.find((c) => c.id === id)?.name || id).join(", ");
    row.append(el("strong", "", party.name), el("span", "muted", names));
    const rowActions = actions();
    rowActions.append(
      button("Heal Party", "Restore every party member to full Life.", async () => {
        await api(`/api/parties/${party.id}/heal`, { method: "POST" });
        setStatus("Party healed.");
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
  const buyer = select("modern-shop-buyer", "Character buying or selling equipment.", characterOptions("Choose buyer"));
  const item = select("modern-shop-item", "Equipment item to buy.", modernState.equipmentRows.map((row) => [row.key, `${row.name} - ${row.price_gp}gp`]));
  const qty = input("number", "modern-shop-qty", "Quantity to buy.", "1");
  const sellItem = input("text", "modern-shop-sell", "Exact inventory item name to sell.");
  panel.append(field("Buyer", buyer), field("Buy item", item), field("Quantity", qty), field("Sell item", sellItem));
  const row = actions();
  row.append(
    button("Buy", "Buy selected equipment for the selected character.", async () => {
      if (!buyer.value) throw new Error("Choose a buyer.");
      await api(`/api/characters/${buyer.value}/buy-equipment`, { method: "POST", body: JSON.stringify({ item_key: item.value, quantity: Number(qty.value || 1) }) });
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
  const character = select("modern-finance-character", "Character used for TAG finance actions.", characterOptions("Choose character"));
  const amount = input("number", "modern-finance-amount", "Gold amount for banking or storage.", "0");
  const item = input("text", "modern-finance-item", "Optional hidden trove item name.");
  panel.append(field("Character", character), field("Amount gp", amount), field("Hidden trove item", item));
  const row = actions();
  row.append(
    button("Deposit TAG Bank", "Deposit gp into selected character's TAG bank account; Guild ledger deposits are free.", async () => tagFinance(character.value, "bank_deposit", amount.value), ""),
    button("Withdraw TAG Bank", "Withdraw gp from selected character's TAG bank account.", async () => tagFinance(character.value, "bank_withdraw", amount.value)),
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
    })
  );
  panel.appendChild(row);
  const summary = card("Finance Summary", `TAG storage ${modernState.campaign?.tag_storage_gold_gp || 0} gp. Hidden trove robbed: ${modernState.campaign?.tag_hidden_trove_robbed ? "yes" : "no"}.`);
  rootEl.append(panel, renderCloseoutTasks("Finance Closeout", ["finance", "storage"]), summary);
}

async function tagFinance(characterId, action, amount) {
  if (!characterId) throw new Error("Choose a character.");
  const result = await api("/api/campaign/tag/finance-action", { method: "POST", body: JSON.stringify({ character_id: characterId, finance_action: action, amount_gp: Number(amount || 0) }) });
  setStatus(result.entry?.result_text || "Finance action logged.");
  await refreshCoreAndRender();
}

function renderSettlement() {
  const campaign = modernState.campaign || {};
  const panel = card("Settlement", "Maintain the TAG home settlement and service checks.");
  const name = input("text", "modern-settlement-name-page", "TAG home settlement name.", campaign.settlement_name || "Home Settlement");
  const size = select("modern-settlement-size-page", "Settlement size modifier.", [["-3", "-3"], ["-2", "-2"], ["-1", "-1"], ["0", "0"], ["1", "+1"], ["2", "+2"], ["3", "+3"]]);
  size.value = String(campaign.settlement_size ?? 0);
  const notes = textarea("modern-settlement-notes", "Settlement notes.", 4);
  notes.value = campaign.settlement_notes || "";
  const availability = input("text", "modern-availability-item", "Item or service to check availability for.");
  panel.append(field("Settlement", name), field("Size", size), field("Notes", notes), field("Availability item", availability));
  const row = actions();
  row.append(
    button("Save Settlement", "Save settlement name, size, and notes.", async () => {
      modernState.campaign = await api("/api/campaign", { method: "PUT", body: JSON.stringify({ settlement_name: name.value, settlement_size: Number(size.value), settlement_notes: notes.value }) });
      setStatus("Settlement saved.");
      await refreshCoreAndRender();
    }, ""),
    button("Roll Size", "Roll a random TAG settlement size.", async () => {
      const result = await api("/api/campaign/settlement/roll-size", { method: "POST" });
      setStatus(`Settlement size rolled ${result.roll}.`);
      await refreshCoreAndRender();
    }),
    button("Check Availability", "Roll d6 plus settlement size against difficulty 6.", async () => {
      const result = await api("/api/campaign/tag/availability", { method: "POST", body: JSON.stringify({ item_name: availability.value, difficulty: 6 }) });
      setStatus(result.check?.result_text || "Availability checked.");
      await refreshCoreAndRender();
    })
  );
  panel.appendChild(row);
  rootEl.appendChild(panel);
}

function renderCampaign() {
  const panel = card("Campaign Management", "Placeholder page for world, hex map, and settlement-map campaign tools.");
  panel.appendChild(el("p", "modern-home-status in-progress", "In progress: create world, hex map editor, settlement list, and settlement placement."));
  rootEl.appendChild(panel);
}

function renderSettings() {
  const panel = card("Settings / Options", "Save rules selections and campaign preferences.");
  const tag = input("checkbox", "modern-tag-banking", "Use TAG banking instead of legacy-only home bank.");
  tag.checked = Boolean(modernState.campaign?.tag_banking_enabled);
  const rules = select("modern-rules-profile", "Ruleset profile to use when starting random adventures.", modernState.rulesProfiles.map((p) => [p.id, p.label]));
  panel.append(field("TAG banking", tag), field("Default ruleset", rules));
  panel.appendChild(button("Save TAG Banking", "Save TAG banking preference to campaign state.", async () => {
    modernState.campaign = await api("/api/campaign", { method: "PUT", body: JSON.stringify({ tag_banking_enabled: tag.checked }) });
    setStatus("Settings saved.");
    await refreshCoreAndRender();
  }, ""));
  rootEl.appendChild(panel);
}

function renderAiAdventures() {
  const panel = card("AI Adventure Generation", "Generate a prompt, validate JSON, and import an AI-authored module.");
  const theme = input("text", "modern-ai-theme", "Theme for the AI adventure prompt.");
  const json = textarea("modern-ai-json", "Paste AI adventure JSON to validate or import.", 10);
  panel.append(field("Theme", theme), field("Adventure JSON", json));
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
      json.value = result.prompt || "";
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
  rootEl.appendChild(panel);
}

function renderGoAdventure() {
  const panel = card("Start Adventure", "Choose party, adventure type, module, ruleset, and start play.");
  const party = select("modern-start-party", "Party to send on the adventure.", partyOptions());
  const type = select("modern-adventure-type", "Adventure type filter.", [["random", "Random"], ["imported", "Imported module"], ["ai", "AI module"], ["ruleset", "Random by ruleset"]]);
  const adventure = select("modern-start-adventure", "Specific adventure module, or Random Dungeon.", adventureOptions());
  const profile = select("modern-start-profile", "Ruleset profile for random adventures.", modernState.rulesProfiles.map((p) => [p.id, p.label]));
  panel.append(field("Party", party), field("Adventure type", type), field("Adventure/module", adventure), field("Ruleset", profile));
  type.addEventListener("change", () => {
    adventure.replaceChildren(...adventureOptions(type.value === "ruleset" ? "all" : type.value).map(([value, label]) => new Option(label, value)));
  });
  panel.appendChild(button("Start Adventure", "Create a new session with the selected party and adventure settings.", async () => {
    if (!party.value) throw new Error("Choose a party.");
    const adventureId = type.value === "random" || type.value === "ruleset" ? "random" : adventure.value;
    const session = await api("/api/sessions", { method: "POST", body: JSON.stringify({ party_id: party.value, adventure_id: adventureId, ruleset_profile_id: profile.value, xp_system: "classical", map_bounds_mode: "unlimited" }) });
    window.location.href = `/?session=${encodeURIComponent(session.id || "")}`;
  }, ""));
  rootEl.appendChild(panel);
}

async function renderRulesReference() {
  if (!modernState.rulesReference.length) modernState.rulesReference = await api("/api/rules/reference");
  const panel = card("Rules Reference", "Search curated implementation reference entries.");
  const search = input("search", "modern-rules-search", "Filter rules reference entries.");
  const results = el("div", "modern-list");
  panel.append(field("Search", search), results);
  const draw = () => {
    results.replaceChildren();
    const needle = search.value.toLowerCase();
    for (const item of modernState.rulesReference.filter((entry) => `${entry.title} ${entry.body}`.toLowerCase().includes(needle)).slice(0, 40)) {
      const row = el("div", "modern-row");
      row.append(el("strong", "", item.title), el("span", "muted", `${item.category || "rules"} · ${item.status || "reference"}`), el("p", "", item.body || ""));
      results.appendChild(row);
    }
  };
  search.addEventListener("input", draw);
  draw();
  rootEl.appendChild(panel);
}

async function renderTables() {
  if (!Object.keys(modernState.tables).length) modernState.tables = await api("/api/rules/tables");
  const panel = card("Tables List", "Browse the top-level structured rules table groups.");
  for (const key of Object.keys(modernState.tables).sort()) {
    const row = el("div", "modern-row");
    const value = modernState.tables[key];
    row.append(el("strong", "", key), el("span", "muted", Array.isArray(value) ? `${value.length} row(s)` : typeof value));
    panel.appendChild(row);
  }
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
  const unlock = button("Unlock", "Show developer tools when password is 7979.", async () => {
    if (pw.value !== "7979") throw new Error("Incorrect developer password.");
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
