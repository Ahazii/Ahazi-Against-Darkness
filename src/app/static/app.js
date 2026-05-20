const state = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  rulesTables: {},
  icons: [],
  sessions: [],
  session: null,
  selectedCharacterId: null,
  selectedPartyId: null,
  editingPartyId: null,
  partyMarchingIds: [],
  characterFilters: { classId: "all", level: "all", sort: "name", direction: "asc" },
  partyFilters: { classId: "all", level: "all", sort: "name", direction: "asc" },
  showRolls: true,
  showMath: false,
  mapZoom: 1,
  mapFocusedTileId: null,
  lastCenteredTileId: null,
  combatTargets: {},
  combatPanelKey: null,
  iconKeyExpanded: null,
};

const ACTIVE_SESSION_KEY = "ahazi-against-darkness.active-session-id";
const ACTIVE_VIEW_KEY = "ahazi-against-darkness.active-view";
const ICON_KEY_EXPANDED_KEY = "ahazi-against-darkness.icon-key-expanded";
const WINDOW_SESSION_PREFIX = "ahazi-active-session:";

const apiStatus = document.getElementById("api-status");
const characterClass = document.getElementById("character-class");
const characterForm = document.getElementById("character-form");
const characterName = document.getElementById("character-name");
const characterCount = document.getElementById("character-count");
const charactersEl = document.getElementById("characters");
const characterFilterClass = document.getElementById("character-filter-class");
const characterFilterLevel = document.getElementById("character-filter-level");
const characterSort = document.getElementById("character-sort");
const characterSortDirection = document.getElementById("character-sort-direction");
const partyForm = document.getElementById("party-form");
const partyName = document.getElementById("party-name");
const partyPicks = document.getElementById("party-picks");
const partyMarchingOrderEl = document.getElementById("party-marching-order");
const partyMarchingListEl = document.getElementById("party-marching-list");
const saveParty = document.getElementById("save-party");
const cancelPartyEdit = document.getElementById("cancel-party-edit");
const partiesEl = document.getElementById("parties");
const partyFilterClass = document.getElementById("party-filter-class");
const partyFilterLevel = document.getElementById("party-filter-level");
const partySort = document.getElementById("party-sort");
const partySortDirection = document.getElementById("party-sort-direction");
const partySelect = document.getElementById("party-select");
const adventureSelect = document.getElementById("adventure-select");
const adventuresEl = document.getElementById("adventures");
const rulesTablesEl = document.getElementById("rules-tables");
const monsterBestiaryEl = document.getElementById("monster-bestiary");
const monsterReactionsEl = document.getElementById("monster-reactions");
const exportPlayerDataBtn = document.getElementById("export-player-data");
const importPlayerDataBtn = document.getElementById("import-player-data");
const importPlayerFile = document.getElementById("import-player-file");
const setupPanel = document.getElementById("setup-panel");
const saveCount = document.getElementById("save-count");
const savedGamesEl = document.getElementById("saved-games");
const startSession = document.getElementById("start-session");
const resumeSessionBtn = document.getElementById("resume-session");
const sessionPanel = document.getElementById("session-panel");
const showSetupBtn = document.getElementById("show-setup");
const sessionMode = document.getElementById("session-mode");
const mapViewportEl = document.getElementById("map-viewport");
const mapEl = document.getElementById("map");
const MAP_BASE_CELL = 116;
const MAP_MIN_ZOOM = 0.08;
const MAP_MAX_ZOOM = 2.5;
const iconKey = document.getElementById("icon-key");
const mapZoomOut = document.getElementById("map-zoom-out");
const mapZoomIn = document.getElementById("map-zoom-in");
const mapZoomReset = document.getElementById("map-zoom-reset");
const mapZoomRoom = document.getElementById("map-zoom-room");
const mapZoomMap = document.getElementById("map-zoom-map");
const mapZoomLabel = document.getElementById("map-zoom-label");
const mapCenterCurrent = document.getElementById("map-center-current");
const mapPanUp = document.getElementById("map-pan-up");
const mapPanDown = document.getElementById("map-pan-down");
const mapPanLeft = document.getElementById("map-pan-left");
const mapPanRight = document.getElementById("map-pan-right");
const tileDetail = document.getElementById("tile-detail");
const exitActions = document.getElementById("exit-actions");
const partyState = document.getElementById("party-state");
const transferItemsSetupBtn = document.getElementById("transfer-items-setup");
const equipmentShopSetupBtn = document.getElementById("equipment-shop-setup");
const equipmentShopDialog = document.getElementById("equipment-shop-dialog");
const equipmentShopDialogForm = document.getElementById("equipment-shop-dialog-form");
const equipmentShopNote = document.getElementById("equipment-shop-note");
const equipmentShopCharacterSelect = document.getElementById("equipment-shop-character");
const equipmentShopBuyTab = document.getElementById("equipment-shop-buy-tab");
const equipmentShopSellTab = document.getElementById("equipment-shop-sell-tab");
const equipmentShopBuyPanel = document.getElementById("equipment-shop-buy-panel");
const equipmentShopSellPanel = document.getElementById("equipment-shop-sell-panel");
const equipmentShopBuyList = document.getElementById("equipment-shop-buy-list");
const equipmentShopSellItem = document.getElementById("equipment-shop-sell-item");
const equipmentShopSellQuote = document.getElementById("equipment-shop-sell-quote");
const equipmentShopConfirmBtn = document.getElementById("equipment-shop-confirm");
const transferItemsSessionBtn = document.getElementById("transfer-items-session");
const transferDialog = document.getElementById("transfer-dialog");
const transferDialogForm = document.getElementById("transfer-dialog-form");
const transferDialogNote = document.getElementById("transfer-dialog-note");
const transferFromSelect = document.getElementById("transfer-from");
const transferPayloadStep = document.getElementById("transfer-payload-step");
const transferItemOptions = document.getElementById("transfer-item-options");
const transferGoldRadio = document.getElementById("transfer-gold-radio");
const transferGoldAmount = document.getElementById("transfer-gold-amount");
const transferToStep = document.getElementById("transfer-to-step");
const transferToSelect = document.getElementById("transfer-to");
const transferConfirmBtn = document.getElementById("transfer-confirm");
const weaponPickerDialog = document.getElementById("weapon-picker-dialog");
const weaponPickerDialogForm = document.getElementById("weapon-picker-dialog-form");
const weaponPickerTitle = document.getElementById("weapon-picker-title");
const weaponPickerNote = document.getElementById("weapon-picker-note");
const weaponPickerDefaultsStep = document.getElementById("weapon-picker-defaults-step");
const weaponPickerDrawStep = document.getElementById("weapon-picker-draw-step");
const weaponPickerMeleeSelect = document.getElementById("weapon-picker-melee");
const weaponPickerMissileSelect = document.getElementById("weapon-picker-missile");
const weaponPickerDrawSelect = document.getElementById("weapon-picker-draw");
const weaponPickerConfirmBtn = document.getElementById("weapon-picker-confirm");
const sessionLog = document.getElementById("session-log");
const searchBtn = document.getElementById("search");
const searchChoicesEl = document.getElementById("search-choices");
const searchTreasureBtn = document.getElementById("search-treasure");
const searchDoorBtn = document.getElementById("search-door");
const searchPassageBtn = document.getElementById("search-passage");
const searchClueBtn = document.getElementById("search-clue");
const searchChoicesHelp = document.getElementById("search-choices-help");
const reactionChoicesEl = document.getElementById("reaction-choices");
const checkReactionBtn = document.getElementById("check-reaction");
const combatStatusEl = document.getElementById("combat-status");
const payBribeBtn = document.getElementById("pay-bribe");
const declineBribeBtn = document.getElementById("decline-bribe");
const spellChoicesEl = document.getElementById("spell-choices");
const levelUpSpellChoicesEl = document.getElementById("level-up-spell-choices");
const economyChoicesEl = document.getElementById("economy-choices");
const questChoicesEl = document.getElementById("quest-choices");
const ongoingQuestsEl = document.getElementById("ongoing-quests");
const potionChoicesEl = document.getElementById("potion-choices");
const combatPanelEl = document.getElementById("combat-panel");
const combatPanelStatusEl = document.getElementById("combat-panel-status");
const combatFoesEl = document.getElementById("combat-foes");
const combatHeroesEl = document.getElementById("combat-heroes");
const combatResolveBtn = document.getElementById("combat-resolve");
const combatFleeBtn = document.getElementById("combat-flee");
const combatWithdrawBtn = document.getElementById("combat-withdraw");
const xpSystemSelect = document.getElementById("xp-system-select");
const combatBtn = document.getElementById("combat-round");
const subdualInput = document.getElementById("subdual-damage");
const subdualLabel = document.getElementById("subdual-label");
const fleeBtn = document.getElementById("flee");
const withdrawBtn = document.getElementById("withdraw");
const resolveTrapBtn = document.getElementById("resolve-trap");
const claimTreasureBtn = document.getElementById("claim-treasure");
const restBtn = document.getElementById("rest");
const saveSessionBtn = document.getElementById("save-session");
const showRollsInput = document.getElementById("show-rolls");
const showMathInput = document.getElementById("show-math");
saveSessionBtn.disabled = true;

const ACTION_TOOLTIPS = {
  search: "Search the current room once (d6; corridors -1). May find treasure, a secret, a clue, or wandering monsters.",
  searchTreasure: "If Search finds something (d6 5–6), take hidden treasure. Pick this first, then click Search Room.",
  searchDoor: "If Search finds something, reveal a secret door on this tile. Pick this first, then click Search Room.",
  searchPassage: "If Search finds something, reveal a secret passage. Pick this first, then click Search Room.",
  searchClue: "If Search finds something, gain 1 new Clue (not spending held Clues). Pick this first, then click Search Room.",
  checkReaction: "Roll d6 on the foe reaction table before fighting. Foes may flee, bribe, fight, or offer peace.",
  payBribe: "Pay the demanded bribe to end the encounter peacefully (uses weapons first, then gold).",
  declineBribe: "Refuse the bribe; the foes attack (usually striking first).",
  combatRound:
    "Resolve one combat round. In rooms, heroes with bows/slings get one opening missile shot each on the first round (automatic). In corridors, rear rank (3-4) may shoot every round. No separate Shoot button — use Combat Round.",
  flee: "Flee: run toward the rear during combat. You stay in this room; living foes may get a parting strike and the fight can continue.",
  withdraw: "Withdraw: step back through a door into the previous room. Foes remain in the room you left and do not follow through the door.",
  resolveTrap: "Attempt to overcome the trap on this tile using the rulebook save/defense listed in the log.",
  claimTreasure: "Split gold and assign items from treasure here among surviving heroes.",
  rest: "Catch your breath: each living hero with missing Life recovers 1 Life (exploration only).",
  saveSession: "Save this session to the server so you can resume it later from the home screen.",
  showRolls: "Include d6 and table roll results in the adventure log.",
  showMath: "Include modifier breakdowns and lookup notes in the adventure log.",
  usePotion:
    "Drink a Potion of Healing: restore all lost Life. Once per hero per adventure; free action even in combat. Barbarians cannot use potions — transfer to an ally.",
  acceptQuest: "Accept the Lady in White's mission and roll on the Quest Table.",
  refuseQuest: "Decline the quest; the Lady in White will not appear again this adventure.",
  claimQuestReward: "Turn in a completed quest and roll on the Epic Rewards Table.",
  buyHealing: "Pay 10gp to restore 1 Life while the wandering healer is on this tile.",
  buyPotion: "Pay 50gp for a Potion of Healing added to this hero (once per hero per adventure).",
  buyPoison: "Pay 30gp for blade poison added to this hero (once per hero per adventure).",
  xpRoll:
    "Spend 1 pending XP roll: d6 > hero Level (6 always succeeds) to gain 1 Level, +1 Life, and class benefits. Casters may need to pick a new spell.",
  pickLevelUpSpell: "Choose a spell from your class list to fill the new spell slot gained at this Level.",
  oldSchoolLevelUp: "Spend (Tier+2)×100 Old School XP to gain 1 Level.",
  slowerXpSpend: "Spend banked XP equal to target Level (plus extra for +1 on the roll) to attempt advancement.",
  transferItems: "Move items or gold between living party members (exploration only).",
  weaponDefaults:
    "Choose default melee and missile weapons for this hero (exploration only). Used at the start of each fight.",
  drawWeapon: "Spend this hero's turn drawing a different melee weapon, then foes attack (rulebook p.94).",
  openDoor: "Attempt to open a closed door (2d6 on the door table). Must open before moving through.",
  reenterDungeon: "Leave camp and explore back into the persisted dungeon map.",
  retreatCamp:
    "Fallen heroes remain inside. Retreat to camp outside—the dungeon map persists so you can regroup and return. Unattended bodies risk 5-in-6 loot theft.",
  leaveDungeon:
    "No fallen remain inside. Leave to end the adventure; surviving heroes fully heal between adventures.",
  leaveDungeonBoss:
    "Final Boss slain and no fallen remain inside. Leave to complete the adventure.",
};

const LEVEL_UP_SPELL_LISTS = {
  wizard: ["Blessing", "Escape", "Lightning", "Fireball", "Protection", "Sleep"],
  elf: ["Escape", "Lightning", "Fireball", "Protection", "Sleep"],
  druid: [
    "Disperse Vermin",
    "Summon Beast",
    "Water Jet",
    "Bear Form",
    "Warp Wood",
    "Barkskin",
    "Lightning Strike",
    "Spiderweb",
    "Entangle",
    "Subdual",
    "Forest Pathway",
    "Alter Weather",
  ],
  illusionist: [
    "Illusionary Armor",
    "Illusionary Mirror Image",
    "Illusionary Servant",
    "Disbelief",
    "Phantasmal Binding",
    "Illusionary Fog",
    "Glamour Mask",
    "Shadow Strike",
    "Specter Swarm",
    "Mirage of Fortune",
    "Illusionary Banquet",
    "Illusionary Sword",
  ],
};

const EXPLORATION_SPELL_KEYS = new Set([
  "escape",
  "blessing",
  "healing_prayer",
  "healing",
  "protection",
  "warp_wood",
  "glamour_mask",
  "forest_pathway",
  "alter_weather",
  "illusionary_servant",
  "illusionary_banquet",
]);

const SPELL_TABLE_KEYS = ["basic_spells_table", "druid_spells_table", "illusionist_spells_table"];

function levelUpSpellOptions(classId) {
  return LEVEL_UP_SPELL_LISTS[(classId || "").toLowerCase()] || [];
}

function casterNeedsSpellPick(classId) {
  return levelUpSpellOptions(classId).length > 0;
}

function normalizeSpellKey(spell) {
  return String(spell || "")
    .trim()
    .toLowerCase()
    .replace(/'/g, "")
    .replace(/\s+/g, "_");
}

function spellExpended(session, member, spell) {
  const key = normalizeSpellKey(spell);
  const expended = ((session?.expended_spells || {})[member.character_id] || []).map(normalizeSpellKey);
  if (expended.includes(key)) {
    return true;
  }
  if (key.includes("healing") || key === "healing_prayer") {
    return ((session?.healing_prayer_uses || {})[member.character_id] || 0) >= 3;
  }
  return false;
}

function spellLabel(session, member, spell) {
  return spellExpended(session, member, spell) ? `${spell} (used)` : spell;
}

function levelUpSpellPickOptions(member) {
  const prepared = new Set((member?.spells || []).map((spell) => spell.toLowerCase()));
  return levelUpSpellOptions(member?.class_id).filter((spell) => !prepared.has(spell.toLowerCase()));
}

function pendingLevelUpMember(session) {
  const pendingId = session?.level_up_spell_pending_character_id;
  if (!pendingId) return null;
  return (session.party || []).find((member) => member.character_id === pendingId) || null;
}

function appendLevelUpSpellPickButtons(container, member) {
  const options = levelUpSpellPickOptions(member);
  for (const spell of options) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = spell;
    setButtonTooltip(button, spellTooltip(spell));
    button.addEventListener("click", () =>
      advance("pick_level_up_spell", { character_id: member.character_id, spell_name: spell })
    );
    container.appendChild(button);
  }
  return options.length;
}

function formatBribeRequirement(session) {
  const gold = session?.reaction_bribe_gold || 0;
  const weapons = session?.reaction_bribe_weapons || 0;
  if (weapons > 0) {
    return `${gold}gp or ${weapons} weapons (mix OK)`;
  }
  return `${gold}gp`;
}

const BRIBE_WEAPON_SKIP = [
  "armor",
  "shield",
  "bandage",
  "rope",
  "lockpick",
  "holy",
  "spellbook",
  "ink",
  "ration",
  "potion",
  "poison",
  "lantern",
  "symbol",
  "crystal",
  "treasure",
  "gold",
  "coin",
  "key",
  "scroll",
];

const BRIBE_WEAPON_KEYWORDS = [
  "weapon",
  "sword",
  "dagger",
  "mace",
  "staff",
  "bow",
  "axe",
  "scimitar",
  "spear",
  "hammer",
  "club",
  "blade",
  "crossbow",
  "sling",
  "whip",
  "flail",
];

function isBribeWeapon(item) {
  const lower = String(item || "").toLowerCase();
  if (lower.includes("blade poison")) return false;
  if (BRIBE_WEAPON_SKIP.some((skip) => lower.includes(skip))) {
    if (lower.includes("hand weapon") || lower.includes("heavy weapon") || lower.includes("light weapon")) {
      return true;
    }
    return false;
  }
  return BRIBE_WEAPON_KEYWORDS.some((keyword) => lower.includes(keyword));
}

const CARRY_LIMITS = { gold: 200, shields: 2, weapons: 3 };

function isCarriedShield(item) {
  return String(item || "").toLowerCase().includes("shield");
}

function isCarriedWeapon(item) {
  return isInventoryWeapon(item);
}

function isInventoryWeapon(item) {
  const lower = String(item || "").toLowerCase();
  if (lower.includes("blade poison")) return false;
  const hasNamedWeapon =
    lower.includes("hand weapon") || lower.includes("heavy weapon") || lower.includes("light weapon");
  if (BRIBE_WEAPON_SKIP.some((skip) => lower.includes(skip)) && !hasNamedWeapon) {
    return false;
  }
  if (lower.includes("bow") || lower.includes("crossbow") || lower.includes("sling")) {
    return true;
  }
  if (hasNamedWeapon) return true;
  return BRIBE_WEAPON_KEYWORDS.some((keyword) => lower.includes(keyword)) || lower.includes("knife");
}

function countCarriedShields(inventory) {
  return (inventory || []).filter(isCarriedShield).length;
}

function countCarriedWeapons(inventory) {
  return (inventory || []).filter(isCarriedWeapon).length;
}

function goldCarryCapacity(member) {
  return Math.max(0, CARRY_LIMITS.gold - (member?.gold || 0));
}

function isMissileWeapon(item) {
  const lower = String(item || "").toLowerCase();
  return lower.includes("bow") || lower.includes("crossbow") || lower.includes("sling");
}

function isTwoHandedWeapon(item) {
  const lower = String(item || "").toLowerCase();
  return lower.includes("heavy weapon") || lower.includes("two-handed") || lower.includes("two handed");
}

function weaponCarrySlots(inventory) {
  let total = 0;
  for (const item of inventory || []) {
    if (!isCarriedWeapon(item)) continue;
    total += isTwoHandedWeapon(item) ? 2 : 1;
  }
  return total;
}

function isOverEncumbered(member) {
  return (
    (member?.gold || 0) > CARRY_LIMITS.gold ||
    countCarriedShields(member?.inventory) > CARRY_LIMITS.shields ||
    weaponCarrySlots(member?.inventory) > CARRY_LIMITS.weapons
  );
}

function memberMeleeWeapons(member) {
  return (member?.inventory || []).filter((item) => isCarriedWeapon(item) && !isMissileWeapon(item));
}

function memberMissileWeapons(member) {
  return (member?.inventory || []).filter((item) => isMissileWeapon(item));
}

function carryLimitsLine(member) {
  const gold = member?.gold || 0;
  return (
    `Carry ${gold}/${CARRY_LIMITS.gold}gp | ` +
    `${weaponCarrySlots(member?.inventory)}/${CARRY_LIMITS.weapons} weapon slots | ` +
    `${countCarriedShields(member?.inventory)}/${CARRY_LIMITS.shields} shields`
  );
}

function canMemberReceiveItem(member, itemName) {
  if (!member || !itemName) return false;
  if (isCarriedShield(itemName) && countCarriedShields(member.inventory) >= CARRY_LIMITS.shields) {
    return false;
  }
  if (isCarriedWeapon(itemName)) {
    const slots = isTwoHandedWeapon(itemName) ? 2 : 1;
    if (weaponCarrySlots(member.inventory) + slots > CARRY_LIMITS.weapons) {
      return false;
    }
  }
  return true;
}

function partyGoldTotal(session) {
  return (session?.party || [])
    .filter((member) => member.current_life > 0)
    .reduce((total, member) => total + (member.gold || 0), 0);
}

function countPartyWeapons(session) {
  let total = 0;
  for (const member of session?.party || []) {
    if (member.current_life <= 0) continue;
    total += (member.inventory || []).filter((item) => isBribeWeapon(item)).length;
  }
  return total;
}

function bribePerFoeRates(session) {
  const foeCount = Math.max(1, session.reaction_bribe_foe_count || 1);
  let goldPerFoe = session.reaction_bribe_gold_per_foe || 0;
  let weaponsPerFoe = session.reaction_bribe_weapons_per_foe || 0;
  if (goldPerFoe <= 0 && session.reaction_bribe_gold > 0) {
    goldPerFoe = Math.floor(session.reaction_bribe_gold / foeCount);
  }
  if (weaponsPerFoe <= 0 && session.reaction_bribe_weapons > 0) {
    weaponsPerFoe = Math.floor(session.reaction_bribe_weapons / foeCount);
  }
  return { foeCount, goldPerFoe, weaponsPerFoe };
}

function canAffordBribe(session) {
  if (session?.reaction_key !== "bribe") return false;
  const { foeCount, goldPerFoe, weaponsPerFoe } = bribePerFoeRates(session);
  const totalGold = partyGoldTotal(session);
  const totalWeapons = countPartyWeapons(session);
  if (weaponsPerFoe <= 0) {
    return totalGold >= foeCount * goldPerFoe;
  }
  if (goldPerFoe <= 0) {
    return totalWeapons >= foeCount * weaponsPerFoe;
  }
  const maxWeaponSlots = Math.floor(totalWeapons / weaponsPerFoe);
  const remainingFoes = foeCount - maxWeaponSlots;
  if (remainingFoes <= 0) return true;
  return totalGold >= remainingFoes * goldPerFoe;
}

function bribeAffordabilitySummary(session) {
  const gold = partyGoldTotal(session);
  const weapons = countPartyWeapons(session);
  const canPay = canAffordBribe(session);
  return { gold, weapons, canPay };
}

function defeatedEnemyLabel(enemy) {
  return enemy.subdued ? `${enemy.name} (subdued)` : enemy.name;
}

function canClaimQuestReward(session, quest) {
  if (!quest || quest.reward_claimed) return false;
  const tile = currentTile(session);
  const onQuestTile = tile?.id === quest.tile_id;
  const partyGold = partyGoldTotal(session);
  switch (quest.key) {
    case "peaceful_way":
      return (quest.peaceful_count || 0) >= (quest.peaceful_required || 3);
    case "slay_all":
      return Boolean(quest.completed);
    case "bring_gold":
      return onQuestTile && partyGold >= (quest.gold_required || 0);
    case "bring_item":
      return onQuestTile && Boolean(quest.item_collected);
    case "bring_head":
    case "bring_alive":
      return onQuestTile && Boolean(quest.completed);
    default:
      return Boolean(quest.completed);
  }
}

function hasMissileWeapon(member) {
  return (member?.inventory || []).some((item) => {
    const lower = String(item).toLowerCase();
    return lower.includes("bow") || lower.includes("crossbow") || lower.includes("sling");
  });
}

function missileStatusSummary(session) {
  const used = new Set(session?.missile_used_character_ids || []);
  const tile = currentTile(session);
  const tileType = tile?.tile_type || "room";
  const round = session?.combat_round || 0;
  const archers = (session?.party || []).filter(
    (member) => member.current_life > 0 && hasMissileWeapon(member) && !used.has(member.character_id)
  );
  if (!archers.length) {
    const living = (session?.party || []).filter((member) => member.current_life > 0);
    const withoutBow = living.filter((member) => !hasMissileWeapon(member));
    if (living.length && withoutBow.length === living.length && session?.mode === "combat") {
      return "No bow/sling in party inventory — missiles fire automatically when equipped.";
    }
    return null;
  }
  if (tileType === "corridor") {
    const rear = archers.filter((member) => member.marching_order >= 3);
    if (!rear.length) {
      return "Corridor: move archers to rear rank (3–4) to shoot; then click Combat Round.";
    }
    return `Corridor: ${rear.map((member) => member.name).join(", ")} shoot on Combat Round.`;
  }
  if (round === 0) {
    return `Opening volley: ${archers.map((member) => member.name).join(", ")} shoot first on Combat Round.`;
  }
  return null;
}

function combatRoundButtonLabel(session) {
  if (session?.mode !== "combat") return "Combat Round";
  if (session.reaction_pending && !session.reaction_checked) return "Resolve Round";
  const missileNote = missileStatusSummary(session);
  if (missileNote && missileNote.includes("Opening volley")) return "Resolve Round (opening volley)";
  if (missileNote && missileNote.startsWith("Corridor:")) return "Resolve Round (rear rank shoots)";
  return "Resolve Round";
}

function combatEncounterKey(session) {
  const tile = currentTile(session);
  if (!tile) return "";
  const livingIds = (tile.enemies || [])
    .filter((enemy) => enemy.life > 0)
    .map((enemy) => enemy.id)
    .sort()
    .join(",");
  return `${tile.id}:${livingIds}:${session.combat_round || 0}`;
}

function syncCombatTargets(session) {
  if (session.mode !== "combat") {
    state.combatPanelKey = null;
    state.combatTargets = {};
    return;
  }
  const tile = currentTile(session);
  const living = (tile?.enemies || []).filter((enemy) => enemy.life > 0);
  if (!living.length) {
    state.combatTargets = {};
    return;
  }
  const defaultTarget = living[0].id;
  const key = combatEncounterKey(session);
  if (state.combatPanelKey !== key) {
    state.combatPanelKey = key;
    state.combatTargets = {};
  }
  for (const member of session.party || []) {
    if (member.current_life <= 0) continue;
    const current = state.combatTargets[member.character_id];
    if (!current || !living.some((enemy) => enemy.id === current)) {
      state.combatTargets[member.character_id] = defaultTarget;
    }
  }
  for (const characterId of Object.keys(state.combatTargets)) {
    const member = (session.party || []).find((item) => item.character_id === characterId);
    if (!member || member.current_life <= 0) {
      delete state.combatTargets[characterId];
    }
  }
}

function buildAttackTargetsPayload() {
  const targets = {};
  for (const [characterId, enemyId] of Object.entries(state.combatTargets || {})) {
    if (enemyId) targets[characterId] = enemyId;
  }
  return Object.keys(targets).length ? targets : undefined;
}

function heroWillUseMissile(session, member, tile) {
  if (!hasMissileWeapon(member) || member.current_life <= 0) return false;
  const used = new Set(session.missile_used_character_ids || []);
  if (used.has(member.character_id)) return false;
  const tileType = tile?.tile_type || "room";
  const round = session.combat_round || 0;
  if (tileType === "corridor") return member.marching_order >= 3;
  if (round !== 0) return false;
  return true;
}

function heroCanMeleeInCombat(session, member, tile) {
  if (member.current_life <= 0) return false;
  const tileType = tile?.tile_type || "room";
  if (tileType !== "corridor") return true;
  if (tile?.wandering_ambush && session.combat_round === 0) {
    return member.marching_order >= 3;
  }
  return member.marching_order <= 2;
}

function heroCombatPlanLabel(session, member, tile) {
  if (member.current_life <= 0) return "Fallen";
  if (heroWillUseMissile(session, member, tile)) return "Missile this round";
  if (heroCanMeleeInCombat(session, member, tile)) return "Melee this round";
  const tileType = tile?.tile_type || "room";
  if (tileType === "corridor") {
    return tile?.wandering_ambush && session.combat_round === 0
      ? "Rear rank only (ambush)"
      : "Front rank only (corridor)";
  }
  return "No attack";
}

function heroCombatSpells(session, member) {
  return (member.spells || []).filter((spell) => {
    const key = normalizeSpellKey(spell);
    if (EXPLORATION_SPELL_KEYS.has(key)) return false;
    return !spellExpended(session, member, spell);
  });
}

function heroCanUsePotion(session, member) {
  return (
    canDrinkPotion(member) &&
    !(session.potion_used_character_ids || []).includes(member.character_id) &&
    (member.inventory || []).some((item) => item.toLowerCase().includes("potion of healing"))
  );
}

function renderCombatPanel(session) {
  if (!combatPanelEl) return;
  const inCombat = session.mode === "combat";
  combatPanelEl.classList.toggle("hidden", !inCombat);
  if (!inCombat) return;

  syncCombatTargets(session);
  const tile = currentTile(session);
  const livingFoes = (tile?.enemies || []).filter((enemy) => enemy.life > 0);
  const canResolve = livingFoes.length > 0 && !(session.reaction_pending && !session.reaction_checked);

  if (combatPanelStatusEl) {
    combatPanelStatusEl.replaceChildren();
    if (session.reaction_pending && !session.reaction_checked) {
      combatPanelStatusEl.textContent =
        "Check Reactions before resolving a round. Missiles fire automatically on the first round.";
    } else if (session.reaction_key === "bribe") {
      const { gold, weapons, canPay } = bribeAffordabilitySummary(session);
      const requirement = formatBribeRequirement(session);
      combatPanelStatusEl.textContent = canPay
        ? `Bribe owed: ${requirement}. Party has ${gold}gp and ${weapons} weapon(s).`
        : `Bribe owed: ${requirement}. Party has ${gold}gp and ${weapons} weapon(s) — cannot afford full payment.`;
    } else if (session.reaction_checked && session.reaction_key === "fight") {
      combatPanelStatusEl.textContent = "Foes attack! They may strike first this round.";
    } else {
      const missileNote = missileStatusSummary(session);
      combatPanelStatusEl.textContent = missileNote || `Round ${(session.combat_round || 0) + 1} — pick targets, then Resolve Round.`;
    }
  }

  if (combatFoesEl) {
    combatFoesEl.replaceChildren();
    combatFoesEl.appendChild(node("div", "combat-section-label", "Foes"));
    const foes = tile?.enemies || [];
    if (!foes.length) {
      combatFoesEl.appendChild(node("div", "muted", "No foes on this tile."));
    }
    for (const foe of foes) {
      const card = node("div", foe.life > 0 ? "combat-foe-card" : "combat-foe-card dead");
      const header = node("div", "combat-foe-header");
      header.appendChild(node("span", "combat-foe-name", foe.name));
      header.appendChild(node("span", "combat-foe-stats", `Life ${foe.life}/${foe.max_life} · L${foe.level}`));
      card.appendChild(header);
      if (foe.tags?.length) {
        card.appendChild(node("div", "combat-foe-tags", foe.tags.join(", ")));
      }
      combatFoesEl.appendChild(card);
    }
  }

  if (combatHeroesEl) {
    combatHeroesEl.replaceChildren();
    combatHeroesEl.appendChild(node("div", "combat-section-label", "Party"));
    const members = [...(session.party || [])].sort((left, right) => left.marching_order - right.marching_order);
    for (const member of members) {
      const row = node("div", "combat-hero-row");
      if (member.current_life <= 0) row.classList.add("inactive");
      const header = node("div", "combat-hero-header");
      header.appendChild(node("span", "combat-hero-name", `#${member.marching_order} ${member.name}`));
      header.appendChild(
        node("span", "combat-hero-stats", `${member.class_name} · Life ${member.current_life}/${member.max_life}`)
      );
      row.appendChild(header);

      const wielded = session.wielded_melee_weapons?.[member.character_id] || member.default_melee_weapon || "unarmed";
      const plan = heroCombatPlanLabel(session, member, tile);
      row.appendChild(node("div", "combat-hero-meta", `Wielding ${wielded} · ${plan}`));

      const actions = node("div", "combat-hero-actions");
      if (member.current_life > 0 && livingFoes.length) {
        const targetRow = node("div", "combat-target-row");
        targetRow.appendChild(document.createTextNode("Target:"));
        const select = document.createElement("select");
        select.dataset.characterId = member.character_id;
        for (const foe of livingFoes) {
          const option = document.createElement("option");
          option.value = foe.id;
          option.textContent = `${foe.name} (L${foe.level})`;
          select.appendChild(option);
        }
        select.value = state.combatTargets[member.character_id] || livingFoes[0].id;
        select.addEventListener("change", () => {
          state.combatTargets[member.character_id] = select.value;
        });
        targetRow.appendChild(select);
        actions.appendChild(targetRow);
      }

      if (session.mode === "combat" && member.current_life > 0) {
        const wieldedMelee = session.wielded_melee_weapons?.[member.character_id];
        const drawOptions = memberMeleeWeapons(member).filter((weapon) => weapon !== wieldedMelee);
        if (drawOptions.length) {
          const drawBtn = node("button", "secondary", "Draw weapon");
          drawBtn.type = "button";
          setButtonTooltip(drawBtn, ACTION_TOOLTIPS.drawWeapon);
          drawBtn.addEventListener("click", () =>
            openWeaponPickerDialog({ mode: "draw", source: "session", member, session })
          );
          actions.appendChild(drawBtn);
        }
      }

      if (heroCanUsePotion(session, member)) {
        const potionBtn = node("button", "secondary", "Potion");
        potionBtn.type = "button";
        setButtonTooltip(potionBtn, ACTION_TOOLTIPS.usePotion);
        potionBtn.addEventListener("click", () => advance("use_potion", { character_id: member.character_id }));
        actions.appendChild(potionBtn);
      }

      const spells = heroCombatSpells(session, member);
      for (const spell of spells) {
        const spellBtn = node("button", "secondary", spell);
        spellBtn.type = "button";
        setButtonTooltip(spellBtn, spellTooltip(spell));
        spellBtn.addEventListener("click", () =>
          advance("cast_spell", { character_id: member.character_id, spell_name: spell })
        );
        actions.appendChild(spellBtn);
      }

      row.appendChild(actions);
      combatHeroesEl.appendChild(row);
    }
  }

  const resolveLabel = combatRoundButtonLabel(session);
  if (combatResolveBtn) {
    combatResolveBtn.disabled = !canResolve;
    combatResolveBtn.textContent = resolveLabel;
    setButtonTooltip(combatResolveBtn, ACTION_TOOLTIPS.combatRound);
  }
  if (combatFleeBtn) combatFleeBtn.disabled = !inCombat;
  const withdrawDoors =
    tile ? (tile.exits || []).filter((exit) => exit.kind === "door" && exit.destination_tile_id) : [];
  if (combatWithdrawBtn) combatWithdrawBtn.disabled = !inCombat || !withdrawDoors.length;

  if (subdualLabel) {
    const wantsCapture = session.active_quest?.key === "bring_alive" && !session.active_quest?.completed;
    subdualLabel.classList.toggle("hidden", !inCombat);
    if (subdualInput && wantsCapture && inCombat) {
      subdualInput.checked = true;
    }
  }
}

function renderCombatStatus(session) {
  if (!combatStatusEl) return;
  combatStatusEl.replaceChildren();
  combatStatusEl.classList.add("hidden");
  if (session.mode !== "combat") return;

  if (session.reaction_pending && !session.reaction_checked) {
    combatStatusEl.textContent =
      "Reactions unchecked — roll d6 before fighting (Check Reactions). Missiles fire automatically on the first Combat Round.";
    combatStatusEl.classList.remove("hidden");
    return;
  }

  if (session.reaction_key === "bribe") {
    const { gold, weapons, canPay } = bribeAffordabilitySummary(session);
    const requirement = formatBribeRequirement(session);
    combatStatusEl.textContent = canPay
      ? `Bribe owed: ${requirement}. Party has ${gold}gp and ${weapons} weapon(s).`
      : `Bribe owed: ${requirement}. Party has ${gold}gp and ${weapons} weapon(s) — cannot afford full payment.`;
    combatStatusEl.classList.toggle("combat-status-unaffordable", !canPay);
    combatStatusEl.classList.remove("hidden");
    return;
  }

  if (session.reaction_checked && session.reaction_key === "fight") {
    combatStatusEl.textContent = "Foes attack! Resolve a combat round (they may strike first this round).";
    combatStatusEl.classList.remove("hidden");
    return;
  }

  const missileNote = missileStatusSummary(session);
  if (missileNote) {
    combatStatusEl.textContent = missileNote;
    combatStatusEl.classList.remove("hidden");
  }
}

const SETUP_TOOLTIPS = {
  createCharacter: "Roll a new hero with the selected class and add them to your roster.",
  healCharacter: "Restore this hero to full Life (home screen only).",
  transferItems: "Move items or gold between heroes on your roster.",
  equipmentShop:
    "Buy gear before an adventure or sell loot for gold. Roster gold is uncapped; the 200gp limit applies only in the dungeon. There is no bank in the rulebook.",
  weaponDefaults: "Choose default melee and missile weapons for this hero. Used when a fight starts.",
  deleteCharacter: "Permanently remove this hero from your roster.",
  sortDirection: "Toggle ascending or descending sort for the list below.",
  saveParty: "Save the party name, members, and marching order.",
  cancelPartyEdit: "Discard party edits and exit edit mode.",
  healParty: "Restore all party members to full Life.",
  editParty: "Edit party name, members, or marching order.",
  deleteParty: "Permanently delete this party.",
  marchingUp: "Move this member one step forward in marching order (position 1 leads).",
  marchingDown: "Move this member one step back in marching order (position 4 is rear).",
  startSession: "Begin a new adventure with the selected party, dungeon, and XP system.",
  resumeSession: "Return to your in-progress game without starting over.",
  exportPlayerData: "Download all heroes and parties as a JSON backup file.",
  importPlayerData: "Import heroes and parties from a previously exported JSON file.",
  showSetup: "Return to the home screen. Your current session stays in memory until you save or start fresh.",
  loadSave: "Load this saved game and resume the adventure.",
  deleteSave: "Permanently delete this saved game from the server.",
  xpSystem:
    "Classical: d6 XP rolls. Old School: tiered XP purchases. Slower Advancement: bank XP and spend to level.",
};

const MAP_TOOLTIPS = {
  panUp: "Pan the map view up.",
  panDown: "Pan the map view down.",
  panLeft: "Pan the map view left.",
  panRight: "Pan the map view right.",
  centerCurrent: "Center the map on the party's current tile.",
  zoomOut: "Zoom out on the dungeon map.",
  zoomIn: "Zoom in on the dungeon map.",
  zoomReset: "Reset map zoom to 100%.",
  zoomRoom: "Zoom to fit the current room on screen.",
  zoomFull: "Zoom to fit the entire explored map on screen.",
};

const TOOLTIP_WRAP_CLASS = "action-tooltip-wrap";

function ensureTooltipWrap(button) {
  if (!button || button.tagName !== "BUTTON" || !button.parentElement) return button;
  const parent = button.parentElement;
  if (parent.classList.contains(TOOLTIP_WRAP_CLASS)) return parent;
  const wrap = document.createElement("span");
  wrap.className = TOOLTIP_WRAP_CLASS;
  parent.insertBefore(wrap, button);
  wrap.appendChild(button);
  return wrap;
}

function removeTooltipWrap(button) {
  const parent = button?.parentElement;
  if (!parent?.classList?.contains(TOOLTIP_WRAP_CLASS)) return;
  parent.parentNode?.insertBefore(button, parent);
  parent.remove();
}

function setTooltip(element, text) {
  if (!element || !text) return;
  element.title = text;
}

function setButtonTooltip(button, text) {
  if (!button) return;
  if (text) button.dataset.tooltip = text;
  else delete button.dataset.tooltip;
  syncButtonTooltip(button);
}

function syncButtonTooltip(button) {
  if (!button || button.tagName !== "BUTTON") return;
  const text = button.dataset.tooltip || "";
  if (!text) {
    removeTooltipWrap(button);
    button.title = "";
    return;
  }
  if (!button.isConnected) {
    button.title = button.disabled ? "" : text;
    return;
  }
  if (button.disabled) {
    const wrap = ensureTooltipWrap(button);
    if (wrap !== button) {
      wrap.title = text;
      button.title = "";
    } else {
      button.title = text;
    }
    return;
  }
  removeTooltipWrap(button);
  button.title = text;
}

function refreshButtonTooltips(root = document) {
  for (const button of root.querySelectorAll("button[data-tooltip]")) {
    syncButtonTooltip(button);
  }
}

function unwrapMapControlButtons() {
  for (const id of [
    "map-pan-up",
    "map-pan-down",
    "map-pan-left",
    "map-pan-right",
    "map-center-current",
    "map-zoom-out",
    "map-zoom-in",
    "map-zoom-reset",
    "map-zoom-room",
    "map-zoom-map",
  ]) {
    const button = document.getElementById(id);
    if (button) removeTooltipWrap(button);
  }
}

function spellRow(spellName) {
  for (const tableKey of SPELL_TABLE_KEYS) {
    const table = state.rulesTables?.[tableKey] || [];
    const normalized = normalizeSpellKey(spellName).replace(/_/g, " ");
    const row = table.find((item) => {
      const spell = normalizeSpellKey(item.spell || "").replace(/_/g, " ");
      return spell === normalized || normalized.includes(spell) || spell.includes(normalized);
    });
    if (row) return row;
  }
  return null;
}

function spellTooltip(spellName) {
  const row = spellRow(spellName);
  if (!row) {
    return `Cast ${spellName}. Once per adventure unless noted; expended spells stay on your sheet until the dungeon ends.`;
  }
  const parts = [`${row.spell}: ${row.result}`];
  if (row.implementation === "partial") {
    parts.push("Partially implemented — spell is consumed but you may need to move manually.");
  } else if (row.implementation === "yes") {
    parts.push("Fully implemented.");
  } else if (row.implementation === "no") {
    parts.push("Not yet implemented in the app.");
  }
  if (row.source_page) {
    parts.push(`Rulebook p.${row.source_page}.`);
  }
  return parts.join(" ");
}

function appendSpellSubline(container, spells, session = null, member = null) {
  const line = node("div", "subline spell-line");
  const list = spells || [];
  if (!list.length) {
    line.textContent = "Spells: none";
    container.appendChild(line);
    return;
  }
  line.appendChild(document.createTextNode("Spells: "));
  list.forEach((spell, index) => {
    if (index > 0) line.appendChild(document.createTextNode(", "));
    const label = session && member ? spellLabel(session, member, spell) : spell;
    const tag = node("span", "spell-tag", label);
    setTooltip(tag, spellTooltip(spell));
    line.appendChild(tag);
  });
  container.appendChild(line);
}

function fallenInDungeon(session) {
  const ids = new Set();
  for (const tile of session?.map_state?.tiles || []) {
    for (const characterId of tile.fallen_character_ids || []) ids.add(characterId);
  }
  return [...ids];
}

function applySessionActionTooltips(session, sessionUi = {}) {
  const { tile, hasTreasure, hasTrap } = sessionUi;
  setButtonTooltip(searchBtn, ACTION_TOOLTIPS.search);
  setButtonTooltip(searchTreasureBtn, ACTION_TOOLTIPS.searchTreasure);
  setButtonTooltip(searchDoorBtn, ACTION_TOOLTIPS.searchDoor);
  setButtonTooltip(searchPassageBtn, ACTION_TOOLTIPS.searchPassage);
  setButtonTooltip(searchClueBtn, ACTION_TOOLTIPS.searchClue);
  const searchLabel = searchChoicesEl?.querySelector(".search-label");
  setTooltip(
    searchLabel,
    "Pick the outcome you want when Search finds something (d6 5–6), then click Search Room."
  );
  setButtonTooltip(checkReactionBtn, ACTION_TOOLTIPS.checkReaction);
  if (session?.reaction_key === "bribe" && (session.reaction_bribe_gold || session.reaction_bribe_weapons)) {
    const { gold, weapons, canPay } = bribeAffordabilitySummary(session);
    const affordNote = canPay
      ? `Party has ${gold}gp and ${weapons} weapon(s).`
      : `Party has ${gold}gp and ${weapons} weapon(s) — not enough to pay.`;
    setButtonTooltip(
      payBribeBtn,
      `${ACTION_TOOLTIPS.payBribe} Required: ${formatBribeRequirement(session)}. ${affordNote}`
    );
  } else {
    setButtonTooltip(payBribeBtn, ACTION_TOOLTIPS.payBribe);
  }
  setButtonTooltip(declineBribeBtn, ACTION_TOOLTIPS.declineBribe);
  setButtonTooltip(combatBtn, ACTION_TOOLTIPS.combatRound);
  setTooltip(
    subdualLabel,
    "Subdual attacks deal normal damage but knock foes out at 0 Life instead of slaying them. Required to complete bring-alive Boss quests."
  );
  setButtonTooltip(fleeBtn, ACTION_TOOLTIPS.flee);
  setButtonTooltip(withdrawBtn, ACTION_TOOLTIPS.withdraw);
  setButtonTooltip(resolveTrapBtn, ACTION_TOOLTIPS.resolveTrap);
  let claimTooltip = ACTION_TOOLTIPS.claimTreasure;
  if (session?.mode === "exploration" && hasTrap) {
    claimTooltip = "Resolve the trap before claiming treasure.";
  } else if (session?.mode === "exploration" && !hasTreasure && tile?.treasure_summary) {
    claimTooltip = tile.treasure_summary;
  }
  setButtonTooltip(claimTreasureBtn, claimTooltip);
  setButtonTooltip(restBtn, ACTION_TOOLTIPS.rest);
  setButtonTooltip(saveSessionBtn, ACTION_TOOLTIPS.saveSession);
  setButtonTooltip(showSetupBtn, SETUP_TOOLTIPS.showSetup);
  setTooltip(showRollsInput?.closest("label"), ACTION_TOOLTIPS.showRolls);
  setTooltip(showMathInput?.closest("label"), ACTION_TOOLTIPS.showMath);
  if (session?.camped_outside) {
    setButtonTooltip(restBtn, `${ACTION_TOOLTIPS.rest} You are camped outside the dungeon.`);
  }
  refreshButtonTooltips(sessionPanel);
}

function applySetupTooltips() {
  setButtonTooltip(characterForm?.querySelector('button[type="submit"]'), SETUP_TOOLTIPS.createCharacter);
  setButtonTooltip(characterSortDirection, SETUP_TOOLTIPS.sortDirection);
  setButtonTooltip(partySortDirection, SETUP_TOOLTIPS.sortDirection);
  setButtonTooltip(saveParty, SETUP_TOOLTIPS.saveParty);
  setButtonTooltip(cancelPartyEdit, SETUP_TOOLTIPS.cancelPartyEdit);
  setButtonTooltip(startSession, SETUP_TOOLTIPS.startSession);
  setButtonTooltip(resumeSessionBtn, SETUP_TOOLTIPS.resumeSession);
  setButtonTooltip(exportPlayerDataBtn, SETUP_TOOLTIPS.exportPlayerData);
  setButtonTooltip(importPlayerDataBtn, SETUP_TOOLTIPS.importPlayerData);
  setButtonTooltip(transferItemsSetupBtn, SETUP_TOOLTIPS.transferItems);
  setButtonTooltip(equipmentShopSetupBtn, SETUP_TOOLTIPS.equipmentShop);
  setTooltip(xpSystemSelect, SETUP_TOOLTIPS.xpSystem);
  refreshButtonTooltips(setupPanel);
}

function applyMapControlTooltips() {
  unwrapMapControlButtons();
  setTooltip(mapPanUp, MAP_TOOLTIPS.panUp);
  setTooltip(mapPanDown, MAP_TOOLTIPS.panDown);
  setTooltip(mapPanLeft, MAP_TOOLTIPS.panLeft);
  setTooltip(mapPanRight, MAP_TOOLTIPS.panRight);
  setTooltip(mapCenterCurrent, MAP_TOOLTIPS.centerCurrent);
  setTooltip(mapZoomOut, MAP_TOOLTIPS.zoomOut);
  setTooltip(mapZoomIn, MAP_TOOLTIPS.zoomIn);
  setTooltip(mapZoomReset, MAP_TOOLTIPS.zoomReset);
  setTooltip(mapZoomRoom, MAP_TOOLTIPS.zoomRoom);
  setTooltip(mapZoomMap, MAP_TOOLTIPS.zoomFull);
}

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

function downloadJson(filename, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}

function readJsonFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      try {
        resolve(JSON.parse(String(reader.result || "")));
      } catch {
        reject(new Error("Import file is not valid JSON."));
      }
    });
    reader.addEventListener("error", () => reject(new Error("Could not read import file.")));
    reader.readAsText(file);
  });
}

function node(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text;
  return el;
}

function subline(text) {
  const el = node("div", "muted");
  el.textContent = text;
  return el;
}

async function loadAll(options = {}) {
  const { restoreSession = true } = options;
  try {
    const requestedView = readRequestedView();
    if (requestedView === "setup" || requestedView === "game") {
      writeActiveView(requestedView);
      clearRequestedView();
    }
    const preferredView = requestedView || readActiveView();
    const [classes, characters, parties, adventures, rulesTables, monsterBestiary, monsterReactions, icons, sessions] = await Promise.all([
      api("/api/rules/classes"),
      api("/api/characters"),
      api("/api/parties"),
      api("/api/adventures"),
      api("/api/rules/tables"),
      api("/api/rules/monsters"),
      api("/api/rules/monster-reactions"),
      api("/api/rules/icons"),
      api("/api/sessions"),
    ]);
    state.classes = classes;
    state.characters = characters;
    state.parties = parties;
    state.adventures = adventures;
    state.rulesTables = rulesTables;
    state.monsterBestiary = monsterBestiary;
    state.monsterReactions = monsterReactions;
    state.icons = icons;
    state.sessions = sessions;
    apiStatus.textContent = "Connected";
    applyMapControlTooltips();
    renderSetup({ rememberView: preferredView !== "game" });
    if (restoreSession && preferredView === "game") await restoreActiveSession();
  } catch (error) {
    apiStatus.textContent = error.message;
  }
}

function renderSetup(options = {}) {
  const { rememberView = true } = options;
  showSetupView({ rememberView });
  renderClasses();
  renderCharacters();
  renderParties();
  renderAdventures();
  renderSavedGames();
  renderRulesTables();
  renderMonsterBestiary();
  renderMonsterReactionTables();
  resumeSessionBtn.classList.toggle("hidden", !state.session);
  applySetupTooltips();
}

function setStatus(message) {
  apiStatus.textContent = message;
}

function handleError(error) {
  setStatus(error.message || "Action failed");
}

function renderClasses() {
  characterClass.replaceChildren();
  for (const profile of state.classes) {
    const option = document.createElement("option");
    option.value = profile.id;
    option.textContent = profile.name;
    characterClass.appendChild(option);
  }
}

function renderCharacterControls() {
  state.characterFilters.classId = renderClassFilter(characterFilterClass, state.characterFilters.classId);
  state.characterFilters.level = renderLevelFilter(characterFilterLevel, characterLevels(), state.characterFilters.level);
  state.characterFilters.sort = renderSortOptions(
    characterSort,
    [
      ["name", "Name"],
      ["class_name", "Class"],
      ["level", "Level"],
      ["gold", "Gold"],
      ["xp", "XP"],
      ["current_life", "Current HP"],
      ["max_life", "Max HP"],
      ["attack_bonus", "Attack"],
      ["defense_bonus", "Defense"],
      ["save_bonus", "Save"],
    ],
    state.characterFilters.sort
  );
  characterSortDirection.textContent = state.characterFilters.direction === "asc" ? "Asc" : "Desc";
}

function renderPartyControls() {
  state.partyFilters.classId = renderClassFilter(partyFilterClass, state.partyFilters.classId);
  state.partyFilters.level = renderLevelFilter(partyFilterLevel, partyAverageLevels(), state.partyFilters.level);
  state.partyFilters.sort = renderSortOptions(
    partySort,
    [
      ["name", "Name"],
      ["averageLevel", "Avg Level"],
      ["classesLabel", "Class Mix"],
      ["memberCount", "Members"],
      ["updated_at", "Updated"],
    ],
    state.partyFilters.sort
  );
  partySortDirection.textContent = state.partyFilters.direction === "asc" ? "Asc" : "Desc";
}

function renderClassFilter(select, selectedValue) {
  const options = [["all", "All classes"], ...state.classes.map((profile) => [profile.id, profile.name])];
  return renderSelectOptions(select, options, selectedValue);
}

function renderLevelFilter(select, levels, selectedValue) {
  return renderSelectOptions(select, [["all", "All levels"], ...levels.map((level) => [String(level), String(level)])], selectedValue);
}

function renderSortOptions(select, options, selectedValue) {
  return renderSelectOptions(select, options, selectedValue);
}

function renderSelectOptions(select, options, selectedValue) {
  const current = options.some(([value]) => value === selectedValue) ? selectedValue : options[0]?.[0] || "";
  select.replaceChildren();
  for (const [value, label] of options) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === current;
    select.appendChild(option);
  }
  select.value = current;
  return current;
}

function characterLevels() {
  return [...new Set(state.characters.map((character) => character.level))].sort((left, right) => left - right);
}

function partyAverageLevels() {
  return [...new Set(state.parties.map((party) => partyStats(party).averageLevelLabel))].sort((left, right) =>
    Number(left) - Number(right)
  );
}

function filteredCharacters() {
  return state.characters.filter((character) => {
    const filters = state.characterFilters;
    if (filters.classId !== "all" && character.class_id !== filters.classId) return false;
    if (filters.level !== "all" && String(character.level) !== filters.level) return false;
    return true;
  });
}

function sortedCharacters(characters) {
  return sortBy(characters, state.characterFilters.sort, state.characterFilters.direction);
}

function filteredParties() {
  return state.parties.filter((party) => {
    const filters = state.partyFilters;
    const stats = partyStats(party);
    if (filters.classId !== "all" && !stats.members.some((member) => member.class_id === filters.classId)) return false;
    if (filters.level !== "all" && stats.averageLevelLabel !== filters.level) return false;
    return true;
  });
}

function sortedParties(parties) {
  return [...parties].sort((left, right) => {
    const leftStats = partyStats(left);
    const rightStats = partyStats(right);
    const key = state.partyFilters.sort;
    const direction = state.partyFilters.direction;
    const leftValue = key in leftStats ? leftStats[key] : left[key];
    const rightValue = key in rightStats ? rightStats[key] : right[key];
    return compareValues(leftValue, rightValue, direction);
  });
}

function sortBy(items, key, direction) {
  return [...items].sort((left, right) => compareValues(left[key], right[key], direction));
}

function compareValues(left, right, direction) {
  const modifier = direction === "desc" ? -1 : 1;
  if (typeof left === "number" && typeof right === "number") return (left - right) * modifier;
  return String(left ?? "").localeCompare(String(right ?? ""), undefined, { numeric: true }) * modifier;
}

function partyStats(party) {
  const members = party.character_ids.map((id) => state.characters.find((character) => character.id === id)).filter(Boolean);
  const averageLevel = members.length
    ? members.reduce((total, member) => total + member.level, 0) / members.length
    : 0;
  const averageLevelLabel = Number.isInteger(averageLevel) ? String(averageLevel) : averageLevel.toFixed(1);
  const classes = [...new Set(members.map((member) => member.class_name))].sort();
  return {
    members,
    memberCount: members.length,
    averageLevel,
    averageLevelLabel,
    classesLabel: classes.length ? classes.join(", ") : "No classes",
  };
}

function renderCharacters() {
  renderCharacterControls();
  const visibleCharacters = sortedCharacters(filteredCharacters());
  characterCount.textContent =
    visibleCharacters.length === state.characters.length
      ? `${state.characters.length} saved`
      : `${visibleCharacters.length} of ${state.characters.length}`;
  charactersEl.replaceChildren();
  partyPicks.replaceChildren();

  for (const character of visibleCharacters) {
    const item = node("div", "item selectable-item");
    item.tabIndex = 0;
    if (character.id === state.selectedCharacterId) item.classList.add("selected");
    item.appendChild(node("strong", "", `${character.name} - ${character.class_name}`));
    item.appendChild(
      subline(
        `L${character.level} HP ${character.current_life}/${character.max_life} ATK +${character.attack_bonus} DEF +${character.defense_bonus} SAVE +${character.save_bonus}`
      )
    );
    item.appendChild(subline(`Gold ${character.gold} | XP ${character.xp}`));
    item.appendChild(subline(carryLimitsLine(character)));
    const meleeDefault = character.default_melee_weapon || "none";
    const missileDefault = character.default_missile_weapon || "none";
    item.appendChild(subline(`Sheet defaults: melee ${meleeDefault}, missile ${missileDefault}`));
    if (character.id === state.selectedCharacterId) {
      item.appendChild(subline(`Inventory: ${character.inventory.join(", ") || "none"}`));
      appendSpellSubline(item, character.spells);
      const actions = node("div", "item-actions");
      const heal = node("button", "secondary", "Heal");
      heal.type = "button";
      heal.disabled = character.current_life >= character.max_life;
      heal.addEventListener("click", async (event) => {
        event.stopPropagation();
        await healCharacter(character.id);
      });
      setButtonTooltip(heal, SETUP_TOOLTIPS.healCharacter);
      if (canEditWeaponDefaults(character)) {
        const weaponDefaultsBtn = node("button", "secondary", "Weapon defaults");
        weaponDefaultsBtn.type = "button";
        setButtonTooltip(weaponDefaultsBtn, SETUP_TOOLTIPS.weaponDefaults);
        weaponDefaultsBtn.addEventListener("click", (event) => {
          event.stopPropagation();
          openWeaponPickerDialog({ mode: "defaults", source: "roster", member: character });
        });
        actions.appendChild(weaponDefaultsBtn);
      }
      const shopBtn = node("button", "secondary", "Buy / Sell");
      shopBtn.type = "button";
      setButtonTooltip(shopBtn, SETUP_TOOLTIPS.equipmentShop);
      shopBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        openEquipmentShopDialog(character.id);
      });
      actions.appendChild(shopBtn);
      const remove = node("button", "danger-button", "Delete");
      remove.type = "button";
      remove.addEventListener("click", async (event) => {
        event.stopPropagation();
        await deleteCharacter(character.id);
      });
      setButtonTooltip(remove, SETUP_TOOLTIPS.deleteCharacter);
      actions.append(heal, remove);
      item.appendChild(actions);
    }
    item.addEventListener("click", () => {
      state.selectedCharacterId = state.selectedCharacterId === character.id ? null : character.id;
      renderCharacters();
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        item.click();
      }
    });
    charactersEl.appendChild(item);
  }

  for (const character of sortedCharacters([...state.characters])) {
    const pick = node("label", "pick");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.value = character.id;
    checkbox.checked = state.partyMarchingIds.includes(character.id);
    checkbox.addEventListener("change", () => {
      togglePartyMember(character.id, checkbox.checked, checkbox);
      renderPartyMarchingOrder();
    });
    pick.appendChild(checkbox);
    const labelText = node("span");
    labelText.appendChild(node("strong", "", character.name));
    labelText.appendChild(subline(`${character.class_name} | L${character.level} | Gold ${character.gold}`));
    pick.appendChild(labelText);
    partyPicks.appendChild(pick);
  }
  renderPartyMarchingOrder();
  if (transferItemsSetupBtn) {
    transferItemsSetupBtn.disabled = state.characters.length < 2;
  }
  if (equipmentShopSetupBtn) {
    equipmentShopSetupBtn.disabled = !state.characters.length;
  }
  refreshButtonTooltips(setupPanel);
}

function togglePartyMember(characterId, checked, checkbox) {
  if (checked) {
    if (state.partyMarchingIds.includes(characterId)) return;
    if (state.partyMarchingIds.length >= 4) {
      checkbox.checked = false;
      setStatus("Party is full. Uncheck a hero before adding another.");
      return;
    }
    state.partyMarchingIds.push(characterId);
    return;
  }
  state.partyMarchingIds = state.partyMarchingIds.filter((id) => id !== characterId);
}

function movePartyMarchingId(characterId, direction) {
  const index = state.partyMarchingIds.indexOf(characterId);
  if (index < 0) return;
  const targetIndex = direction === "up" ? index - 1 : index + 1;
  if (targetIndex < 0 || targetIndex >= state.partyMarchingIds.length) return;
  const ids = [...state.partyMarchingIds];
  [ids[index], ids[targetIndex]] = [ids[targetIndex], ids[index]];
  state.partyMarchingIds = ids;
  renderPartyMarchingOrder();
}

function renderPartyMarchingOrder() {
  if (!partyMarchingOrderEl || !partyMarchingListEl) return;
  partyMarchingListEl.replaceChildren();
  if (!state.partyMarchingIds.length) {
    partyMarchingOrderEl.classList.add("hidden");
    return;
  }
  partyMarchingOrderEl.classList.remove("hidden");
  state.partyMarchingIds.forEach((characterId, index) => {
    const row = node("div", "marching-order-row");
    row.appendChild(node("span", "position", `#${index + 1}`));
    row.appendChild(node("span", "name", characterNameById(characterId)));
    const actions = node("div", "marching-order-actions");
    const up = node("button", "secondary", "↑");
    up.type = "button";
    up.disabled = index === 0;
    up.addEventListener("click", () => movePartyMarchingId(characterId, "up"));
    setButtonTooltip(up, SETUP_TOOLTIPS.marchingUp);
    const down = node("button", "secondary", "↓");
    down.type = "button";
    down.disabled = index === state.partyMarchingIds.length - 1;
    down.addEventListener("click", () => movePartyMarchingId(characterId, "down"));
    setButtonTooltip(down, SETUP_TOOLTIPS.marchingDown);
    actions.append(up, down);
    row.appendChild(actions);
    partyMarchingListEl.appendChild(row);
  });
  refreshButtonTooltips(setupPanel);
}

function renderParties() {
  renderPartyControls();
  partiesEl.replaceChildren();
  partySelect.replaceChildren();
  const visibleParties = sortedParties(filteredParties());
  for (const party of visibleParties) {
    const stats = partyStats(party);
    const item = node("div", "item selectable-item");
    item.tabIndex = 0;
    if (party.id === state.selectedPartyId) item.classList.add("selected");
    item.appendChild(node("strong", "", party.name));
    item.appendChild(subline(`${party.character_ids.length} members | Avg L${stats.averageLevelLabel} | ${stats.classesLabel}`));
    if (party.id === state.selectedPartyId) {
      party.character_ids.forEach((characterId, index) => {
        item.appendChild(subline(`#${index + 1} ${characterNameById(characterId)}`));
      });
      const actions = node("div", "item-actions");
      const heal = node("button", "secondary", "Heal Party");
      heal.type = "button";
      heal.disabled = !stats.members.some((member) => member.current_life < member.max_life);
      heal.addEventListener("click", async (event) => {
        event.stopPropagation();
        await healParty(party.id);
      });
      setButtonTooltip(heal, SETUP_TOOLTIPS.healParty);
      const edit = node("button", "secondary", "Edit");
      edit.type = "button";
      edit.addEventListener("click", (event) => {
        event.stopPropagation();
        startPartyEdit(party);
      });
      setButtonTooltip(edit, SETUP_TOOLTIPS.editParty);
      const remove = node("button", "danger-button", "Delete");
      remove.type = "button";
      remove.addEventListener("click", async (event) => {
        event.stopPropagation();
        await deleteParty(party.id);
      });
      setButtonTooltip(remove, SETUP_TOOLTIPS.deleteParty);
      actions.append(heal, edit, remove);
      item.appendChild(actions);
    }
    item.addEventListener("click", () => {
      state.selectedPartyId = state.selectedPartyId === party.id ? null : party.id;
      renderParties();
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        item.click();
      }
    });
    partiesEl.appendChild(item);
  }

  for (const party of state.parties) {
    const option = document.createElement("option");
    option.value = party.id;
    const stats = partyStats(party);
    option.textContent = `${party.name} (Avg L${stats.averageLevelLabel})`;
    partySelect.appendChild(option);
  }
  refreshButtonTooltips(setupPanel);
}

function renderAdventures() {
  adventuresEl.replaceChildren();
  adventureSelect.replaceChildren();
  for (const adventure of state.adventures) {
    const option = document.createElement("option");
    option.value = adventure.id;
    option.disabled = !adventure.playable;
    option.textContent = adventure.playable ? adventure.name : `${adventure.name} (manifest needed)`;
    adventureSelect.appendChild(option);

    const item = node("div", "item");
    item.appendChild(node("strong", "", adventure.name));
    item.appendChild(subline(adventure.notes));
    adventuresEl.appendChild(item);
  }
}

function renderSavedGames() {
  savedGamesEl.replaceChildren();
  const savedSessions = [...state.sessions]
    .filter((session) => session.saved_at)
    .sort((left, right) => right.saved_at.localeCompare(left.saved_at));
  saveCount.textContent = `${savedSessions.length} saved`;
  if (!savedSessions.length) {
    savedGamesEl.appendChild(node("div", "item", "No manual saves yet."));
    return;
  }
  for (const session of savedSessions.slice(0, 5)) {
    const item = node("div", "item selectable-item");
    if (state.session?.id === session.id) item.classList.add("selected");
    item.appendChild(node("strong", "", `${partyNameById(session.party_id)} - ${session.adventure_id}`));
    item.appendChild(
      subline(`${session.mode} | saved ${formatDateTime(session.saved_at)} | ${session.map_state.tiles.length} map elements`)
    );
    const actions = node("div", "item-actions");
    const load = node("button", "secondary", state.session?.id === session.id ? "Current" : "Load");
    load.type = "button";
    load.disabled = state.session?.id === session.id;
    load.addEventListener("click", async () => loadSession(session.id));
    setButtonTooltip(load, SETUP_TOOLTIPS.loadSave);
    const remove = node("button", "danger-button", "Delete");
    remove.type = "button";
    remove.addEventListener("click", async () => deleteSession(session.id));
    setButtonTooltip(remove, SETUP_TOOLTIPS.deleteSave);
    actions.append(load, remove);
    item.appendChild(actions);
    savedGamesEl.appendChild(item);
  }
  refreshButtonTooltips(setupPanel);
}

const RULES_TABLE_META_KEYS = new Set(["ruleset_status", "open_items", "validation"]);
const RULES_TABLE_ORDER = [
  "basic_spells_table",
  "druid_spells_table",
  "illusionist_spells_table",
  "scrolls_table",
  "door_table",
  "trap_table",
  "treasure_table",
  "hidden_treasure_table",
  "search_table",
  "room_content_table",
  "wandering_monsters_table",
  "special_event_wandering_table",
  "dungeon_special_events_table",
  "dungeon_special_features_table",
  "dungeon_magic_treasure_table",
  "default_reaction_table",
  "vermin_reaction_table",
  "minion_reaction_table",
  "major_reaction_table",
  "experience_classical_table",
  "experience_slow_sure_table",
  "experience_old_school_table",
  "experience_slower_table",
  "economy_services_table",
  "equipment_shop_table",
  "quest_table",
  "epic_rewards_table",
  "combat_modifiers_table",
  "combat_notes",
];

function renderRulesTables() {
  rulesTablesEl.replaceChildren();
  const tables = state.rulesTables || {};
  const orderedKeys = [
    ...RULES_TABLE_ORDER.filter((key) => tables[key] != null),
    ...Object.keys(tables).filter((key) => !RULES_TABLE_META_KEYS.has(key) && !RULES_TABLE_ORDER.includes(key)),
  ];
  if (!orderedKeys.length) {
    rulesTablesEl.appendChild(node("div", "item", "No structured tables loaded."));
    return;
  }
  if (tables.ruleset_status) {
    rulesTablesEl.appendChild(node("div", "item muted", tables.ruleset_status));
  }
  for (const key of orderedKeys) {
    const value = tables[key];
    const detail = document.createElement("details");
    detail.className = "rules-table-card";
    detail.open = key === "basic_spells_table" || key === "door_table" || key === "search_table";
    const summary = document.createElement("summary");
    summary.textContent = titleFromKey(key);
    detail.appendChild(summary);
    if (key === "basic_spells_table") {
      detail.appendChild(
        node(
          "div",
          "item muted",
          "Basic wizard and cleric prayers. Druid and illusionist lists are separate tables below. Hover spells in party sheets for summaries."
        )
      );
    }
    if (key === "druid_spells_table" || key === "illusionist_spells_table") {
      detail.appendChild(
        node("div", "item muted", "Class-exclusive spells from the Expanded Edition rulebook (p.70–75).")
      );
    }
    if (key === "scrolls_table") {
      detail.appendChild(
        node(
          "div",
          "item muted",
          "Burn scrolls from inventory during play. Wizards can copy unknown spells into their spellbook instead of casting."
        )
      );
    }
    if (key === "equipment_shop_table") {
      detail.appendChild(
        node(
          "div",
          "item muted",
          "Buy before or between adventures via the home Equipment Shop (p.16). Sell loot there; magic resale on the last row (p.19). No bank — gold stays on hero sheets."
        )
      );
    }
    if (Array.isArray(value) && value.every((item) => item && typeof item === "object" && !Array.isArray(item))) {
      detail.appendChild(renderObjectTable(flattenRulesRows(value)));
    } else if (Array.isArray(value)) {
      const list = node("div", "list compact");
      value.forEach((item) => list.appendChild(node("div", "item", String(item))));
      detail.appendChild(list);
    } else {
      detail.appendChild(node("div", "item", String(value)));
    }
    rulesTablesEl.appendChild(detail);
  }
}

function renderMonsterBestiary() {
  if (!monsterBestiaryEl) return;
  monsterBestiaryEl.replaceChildren();
  const bestiary = state.monsterBestiary || {};
  const categories = Object.keys(bestiary);
  if (!categories.length) {
    monsterBestiaryEl.appendChild(node("div", "item", "No monster bestiary loaded."));
    return;
  }
  const heading = node("h2", "", "Monster Bestiary");
  monsterBestiaryEl.appendChild(heading);
  monsterBestiaryEl.appendChild(node("div", "item muted", "Spawn templates used by room content and wandering tables."));
  for (const category of categories) {
    const rows = bestiary[category] || [];
    const detail = document.createElement("details");
    detail.className = "rules-table-card";
    const summary = document.createElement("summary");
    summary.textContent = titleFromKey(category);
    detail.appendChild(summary);
    detail.appendChild(renderObjectTable(rows));
    monsterBestiaryEl.appendChild(detail);
  }
}

function renderMonsterReactionTables() {
  if (!monsterReactionsEl) return;
  monsterReactionsEl.replaceChildren();
  const reactions = state.monsterReactions || {};
  const names = Object.keys(reactions);
  if (!names.length) {
    monsterReactionsEl.appendChild(node("div", "item", "No per-foe reaction tables loaded."));
    return;
  }
  const heading = node("h2", "", "Monster Reaction Tables");
  monsterReactionsEl.appendChild(heading);
  monsterReactionsEl.appendChild(
    node(
      "div",
      "item muted",
      "Per-foe d6 reaction tables from the bestiary. Homogeneous encounters use these; mixed groups fall back to category tables above."
    )
  );
  for (const name of names.sort()) {
    const rows = reactions[name] || [];
    const detail = document.createElement("details");
    detail.className = "rules-table-card";
    detail.open = name === "Goblins";
    const summary = document.createElement("summary");
    summary.textContent = name;
    detail.appendChild(summary);
    detail.appendChild(renderObjectTable(rows));
    monsterReactionsEl.appendChild(detail);
  }
}

function flattenRulesRows(rows) {
  return rows.map((row) => {
    const flat = { ...row };
    for (const key of ["any", "corridor", "room"]) {
      if (!flat[key] || typeof flat[key] !== "object") continue;
      const payload = flat[key];
      flat.result = flat.result || payload.description || payload.key || flat.result;
      flat.content_key = payload.key;
      flat.enemy_category = payload.enemy_category;
      flat.objects = Array.isArray(payload.objects) ? payload.objects.join(", ") : payload.objects;
      delete flat[key];
    }
    return flat;
  });
}

function formatRulesCell(value) {
  if (value == null) return "";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function renderObjectTable(rows) {
  const table = document.createElement("table");
  table.className = "rules-data-table";
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const thead = document.createElement("thead");
  const headRow = document.createElement("tr");
  columns.forEach((column) => headRow.appendChild(node("th", "", titleFromKey(column))));
  thead.appendChild(headRow);
  table.appendChild(thead);
  const tbody = document.createElement("tbody");
  rows.forEach((row) => {
    const tr = document.createElement("tr");
    columns.forEach((column) => tr.appendChild(node("td", "", formatRulesCell(row[column]))));
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);
  return table;
}

async function refreshSessions() {
  state.sessions = await api("/api/sessions");
  renderSavedGames();
}

async function restoreActiveSession() {
  if (state.session) {
    renderSession();
    return;
  }
  const sessionId = readActiveSessionId();
  if (!sessionId) return;
  try {
    await loadSession(sessionId, { quiet: true });
  } catch {
    clearActiveSessionId();
    writeActiveView("setup");
  }
}

async function loadSession(sessionId, options = {}) {
  state.session = await api(`/api/sessions/${sessionId}`);
  writeActiveSessionId(state.session.id);
  renderSession();
  renderSavedGames();
  if (!options.quiet) setStatus("Saved game loaded");
}

async function deleteSession(sessionId) {
  try {
    await api(`/api/sessions/${sessionId}`, { method: "DELETE" });
    if (readActiveSessionId() === sessionId) clearActiveSessionId();
    if (state.session?.id === sessionId) {
      state.session = null;
      showSetupView();
      saveSessionBtn.disabled = true;
      saveSessionBtn.classList.add("hidden");
    }
    await refreshSessions();
    setStatus("Saved game deleted");
  } catch (error) {
    handleError(error);
  }
}

function readActiveSessionId() {
  try {
    if (window.localStorage) {
      const value = window.localStorage.getItem(ACTIVE_SESSION_KEY);
      if (value) return value;
    }
  } catch {
    // Fall back to window.name below.
  }
  return window.name?.startsWith(WINDOW_SESSION_PREFIX) ? window.name.slice(WINDOW_SESSION_PREFIX.length) : "";
}

function writeActiveSessionId(sessionId) {
  try {
    if (window.localStorage) window.localStorage.setItem(ACTIVE_SESSION_KEY, sessionId);
  } catch {
    // Fall back to window.name below.
  }
  window.name = `${WINDOW_SESSION_PREFIX}${sessionId}`;
}

function readActiveView() {
  try {
    if (window.localStorage) return window.localStorage.getItem(ACTIVE_VIEW_KEY) || "setup";
  } catch {
    // Default to setup if browser storage is blocked.
  }
  return "setup";
}

function readRequestedView() {
  const value = new URLSearchParams(window.location.search).get("view");
  return value === "game" || value === "setup" ? value : "";
}

function clearRequestedView() {
  const url = new URL(window.location.href);
  if (!url.searchParams.has("view")) return;
  url.searchParams.delete("view");
  window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
}

function writeActiveView(view) {
  try {
    if (window.localStorage) window.localStorage.setItem(ACTIVE_VIEW_KEY, view);
  } catch {
    // View persistence is optional.
  }
}

function clearActiveSessionId() {
  try {
    if (window.localStorage) window.localStorage.removeItem(ACTIVE_SESSION_KEY);
  } catch {
    // Fall back to window.name below.
  }
  if (window.name?.startsWith(WINDOW_SESSION_PREFIX)) window.name = "";
}

function partyNameById(partyId) {
  return state.parties.find((party) => party.id === partyId)?.name || `Party ${partyId.slice(0, 6)}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { dateStyle: "short", timeStyle: "short" });
}

function renderSession() {
  const session = state.session;
  if (!session) return;
  showGameView();
  sessionMode.textContent = session.camped_outside ? "camp" : session.mode;
  showRollsInput.checked = state.showRolls;
  showMathInput.checked = state.showMath;

  safeSessionRender("map", () => renderMap(session));
  safeSessionRender("tileDetail", () => renderTileDetail(session));
  safeSessionRender("iconKey", () => renderIconKey());
  safeSessionRender("exitActions", () => renderExitActions(session));
  safeSessionRender("combatPanel", () => renderCombatPanel(session));
  safeSessionRender("partyState", () => renderPartyState(session));
  safeSessionRender("log", () => renderLog(session));

  const tile = currentTile(session);
  const hasTrap = Boolean(tile?.trap_key && !tile.trap_resolved);
  const hasTreasure =
    Boolean(tile) &&
    !tile.treasure_claimed &&
    (Boolean(tile.treasure_gold) || (tile.treasure_items || []).length > 0);
  const canSearch = session.mode === "exploration" && Boolean(tile) && !tile.searched;
  searchBtn.disabled = !canSearch;
  if (searchChoicesEl) searchChoicesEl.classList.toggle("hidden", !canSearch);
  if (searchChoicesHelp) {
    searchChoicesHelp.classList.toggle("hidden", !canSearch);
    if (canSearch) {
      searchChoicesHelp.textContent = `Search Room rolls once per location (d6; corridors −1). These buttons do not search — they pick what you want IF the roll finds something (table result 5–6). Default is Hidden Treasure. Held Clues: ${session.clues_found || 0}. The Clue button gains a new Clue; it does not spend held Clues (those are for illusion/lever doors).`;
    }
  }
  if (searchTreasureBtn) searchTreasureBtn.disabled = !canSearch;
  if (searchDoorBtn) searchDoorBtn.disabled = !canSearch;
  if (searchPassageBtn) searchPassageBtn.disabled = !canSearch;
  if (searchClueBtn) searchClueBtn.disabled = !canSearch;
  restBtn.disabled = session.mode !== "exploration";
  const inCombat = session.mode === "combat";
  const canCheckReaction = inCombat && session.reaction_pending && !session.reaction_checked;
  const bribeOutstanding = inCombat && session.reaction_key === "bribe";
  if (reactionChoicesEl) reactionChoicesEl.classList.toggle("hidden", !inCombat);
  if (checkReactionBtn) checkReactionBtn.disabled = !canCheckReaction;
  if (payBribeBtn) {
    payBribeBtn.classList.toggle("hidden", !bribeOutstanding);
    const canPay = bribeOutstanding && canAffordBribe(session);
    payBribeBtn.disabled = !bribeOutstanding || !canPay;
    if (bribeOutstanding) {
      payBribeBtn.textContent = `Pay Bribe (${formatBribeRequirement(session)})`;
    }
  }
  if (declineBribeBtn) {
    declineBribeBtn.classList.toggle("hidden", !bribeOutstanding);
    declineBribeBtn.disabled = !bribeOutstanding;
  }
  renderCombatStatus(session);
  safeSessionRender("spellChoices", () => renderSpellChoices(session));
  safeSessionRender("levelUpSpellChoices", () => renderLevelUpSpellChoices(session));
  safeSessionRender("potionChoices", () => renderPotionChoices(session));
  safeSessionRender("economyChoices", () => renderEconomyChoices(session));
  safeSessionRender("ongoingQuests", () => renderOngoingQuests(session));
  const hideLegacyCombat = inCombat;
  if (combatBtn) combatBtn.classList.toggle("hidden", hideLegacyCombat);
  if (fleeBtn) fleeBtn.classList.toggle("hidden", hideLegacyCombat);
  if (withdrawBtn) withdrawBtn.classList.toggle("hidden", hideLegacyCombat);
  searchBtn.classList.toggle("hidden", inCombat);
  restBtn.classList.toggle("hidden", inCombat);
  resolveTrapBtn.classList.toggle("hidden", inCombat);
  claimTreasureBtn.classList.toggle("hidden", inCombat);
  combatBtn.disabled = !inCombat;
  combatBtn.textContent = combatRoundButtonLabel(session);
  if (subdualLabel && !inCombat) {
    subdualLabel.classList.add("hidden");
  }
  if (fleeBtn) fleeBtn.disabled = !inCombat;
  const withdrawDoors =
    session.mode === "combat" && tile
      ? (tile.exits || []).filter((exit) => exit.kind === "door" && exit.destination_tile_id)
      : [];
  if (withdrawBtn) withdrawBtn.disabled = session.mode !== "combat" || !withdrawDoors.length;
  resolveTrapBtn.disabled = session.mode !== "exploration" || !hasTrap;
  claimTreasureBtn.disabled = session.mode !== "exploration" || !hasTreasure || hasTrap;
  saveSessionBtn.disabled = false;
  if (transferItemsSessionBtn) {
    transferItemsSessionBtn.classList.toggle("hidden", session.mode !== "exploration");
    transferItemsSessionBtn.disabled = (session.party || []).filter((member) => member.current_life > 0).length < 2;
  }
  applySessionActionTooltips(session, { tile, hasTreasure, hasTrap });
}

function safeSessionRender(label, renderFn) {
  try {
    renderFn();
  } catch (error) {
    console.error(`Session render failed: ${label}`, error);
    if (label === "tileDetail" && tileDetail) {
      tileDetail.replaceChildren(node("div", "item", "Could not render map element details."));
    }
    if (label === "exitActions" && exitActions) {
      exitActions.replaceChildren(node("div", "item", "Could not render exits."));
    }
    if (label === "partyState" && partyState) {
      partyState.replaceChildren(node("div", "item", "Could not render party sheets."));
    }
    if (label === "log" && sessionLog) {
      sessionLog.replaceChildren(node("div", "item", "Could not render adventure log."));
    }
  }
}

function isScrollItem(item) {
  const lowered = String(item || "").trim().toLowerCase();
  return (
    lowered.startsWith("scroll") ||
    lowered.startsWith("bark:") ||
    lowered.startsWith("bark of") ||
    lowered.startsWith("prism:") ||
    lowered.startsWith("prism of") ||
    lowered.startsWith("druid bark") ||
    lowered.startsWith("illusionist prism")
  );
}

function scrollSpellName(item) {
  if (!isScrollItem(item)) return null;
  return item
    .replace(/^(scroll|bark|prism)\s*(?:of|:)\s*/i, "")
    .replace(/^(druid\s+bark|illusionist\s+prism)\s*(?:of|:)\s*/i, "")
    .trim();
}

function renderSpellChoices(session) {
  if (!spellChoicesEl) return;
  spellChoicesEl.replaceChildren();
  const inCombat = session.mode === "combat";
  const inExploration = session.mode === "exploration";
  if (inCombat) {
    spellChoicesEl.classList.add("hidden");
    return;
  }
  if (!inCombat && !inExploration) {
    spellChoicesEl.classList.add("hidden");
    return;
  }
  const living = (session.party || []).filter((member) => member.current_life > 0);
  const entries = [];
  const scrollEntries = [];
  for (const member of living) {
    for (const spell of member.spells || []) {
      const key = normalizeSpellKey(spell);
      const explorationOnly = EXPLORATION_SPELL_KEYS.has(key);
      if (inExploration && !explorationOnly) continue;
      if (!spellExpended(session, member, spell)) {
        entries.push({ member, spell, action: "cast_spell" });
      }
    }
    if (member.class_id !== "barbarian") {
      for (const item of member.inventory || []) {
        const spell = scrollSpellName(item);
        if (spell) {
          scrollEntries.push({ member, spell, item, action: "burn_scroll" });
        }
      }
    }
  }
  if (!entries.length && !scrollEntries.length) {
    spellChoicesEl.classList.add("hidden");
    return;
  }
  spellChoicesEl.classList.remove("hidden");
  if (entries.length) {
    spellChoicesEl.appendChild(node("span", "search-label", inExploration ? "Cast (exploration):" : "Cast spell:"));
    for (const { member, spell, action } of entries) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = `${member.name}: ${spell}`;
      setButtonTooltip(button, spellTooltip(spell));
      button.addEventListener("click", () =>
        advance(action, { character_id: member.character_id, spell_name: spell })
      );
      spellChoicesEl.appendChild(button);
    }
  }
  if (scrollEntries.length) {
    spellChoicesEl.appendChild(node("span", "search-label", "Burn scroll:"));
    for (const { member, spell, action } of scrollEntries) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = `${member.name}: ${spell} (scroll)`;
      setButtonTooltip(button, `${spellTooltip(spell)} Burns the scroll; does not use a memorized slot.`);
      button.addEventListener("click", () =>
        advance(action, { character_id: member.character_id, spell_name: spell })
      );
      spellChoicesEl.appendChild(button);
      if (member.class_id === "wizard" && !(member.spells || []).some((s) => normalizeSpellKey(s) === normalizeSpellKey(spell))) {
        const copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.className = "secondary";
        copyBtn.textContent = `${member.name}: copy ${spell} to spellbook`;
        setButtonTooltip(copyBtn, "Copy this scroll into the wizard's spellbook instead of casting (destroys scroll).");
        copyBtn.addEventListener("click", () =>
          advance("copy_scroll", { character_id: member.character_id, spell_name: spell })
        );
        spellChoicesEl.appendChild(copyBtn);
      }
    }
  }
}

function renderLevelUpSpellChoices(session) {
  if (!levelUpSpellChoicesEl) return;
  levelUpSpellChoicesEl.replaceChildren();
  const member = pendingLevelUpMember(session);
  if (!member) {
    levelUpSpellChoicesEl.classList.add("hidden");
    levelUpSpellChoicesEl.classList.remove("level-up-spell-banner");
    return;
  }
  const options = levelUpSpellPickOptions(member);
  if (!options.length) {
    levelUpSpellChoicesEl.classList.add("hidden");
    levelUpSpellChoicesEl.classList.remove("level-up-spell-banner");
    return;
  }
  levelUpSpellChoicesEl.classList.remove("hidden");
  levelUpSpellChoicesEl.classList.add("level-up-spell-banner");
  levelUpSpellChoicesEl.appendChild(
    node("span", "search-label", `${member.name} — pick spell for new slot (required before more XP):`)
  );
  appendLevelUpSpellPickButtons(levelUpSpellChoicesEl, member);
  levelUpSpellChoicesEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function canDrinkPotion(member) {
  return member.class_id !== "barbarian";
}

function formatMemberInventory(member) {
  const items = member.inventory || [];
  if (!items.length) return "none";
  if (member.class_id !== "barbarian") return items.join(", ");
  return items
    .map((item) =>
      item.toLowerCase().includes("potion of healing") ? `${item} (cannot drink — transfer to ally)` : item
    )
    .join(", ");
}

function renderPotionChoices(session) {
  if (!potionChoicesEl) return;
  potionChoicesEl.replaceChildren();
  if (session.mode === "combat") {
    potionChoicesEl.classList.add("hidden");
    return;
  }
  const living = (session.party || []).filter((member) => member.current_life > 0);
  const entries = living.filter(
    (member) =>
      canDrinkPotion(member) &&
      !(session.potion_used_character_ids || []).includes(member.character_id) &&
      (member.inventory || []).some(
        (item) => item.toLowerCase().includes("potion of healing")
      )
  );
  if (!entries.length) {
    potionChoicesEl.classList.add("hidden");
    return;
  }
  potionChoicesEl.classList.remove("hidden");
  potionChoicesEl.appendChild(node("span", "search-label", "Potion of Healing (once/adventure, free action):"));
  for (const member of entries) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = `${member.name}: Drink Potion`;
    setButtonTooltip(button, ACTION_TOOLTIPS.usePotion);
    button.addEventListener("click", () => advance("use_potion", { character_id: member.character_id }));
    potionChoicesEl.appendChild(button);
  }
}

function questTile(session) {
  const quest = session?.active_quest;
  if (!quest?.tile_id) return null;
  return session.map_state.tiles.find((tile) => tile.id === quest.tile_id) || null;
}

function questGuidance(session, quest) {
  if (!quest) return "";
  const giver = questTile(session);
  const giverName = giver?.title || "the Lady in White's tile";
  const partyGold = (session.party || [])
    .filter((member) => member.current_life > 0)
    .reduce((total, member) => total + (member.gold || 0), 0);
  switch (quest.key) {
    case "bring_gold":
      return `Collect ${quest.gold_required}gp across the party (currently ${partyGold}gp), then return to ${giverName} and use Claim Quest Reward.`;
    case "bring_item":
      return quest.item_collected
        ? `Return to ${giverName} with ${quest.item_name || "the quest item"} and claim your Epic reward.`
        : `Find ${quest.item_name || "the quest item"} from a Weird or Boss foe, then return to ${giverName}.`;
    case "bring_head":
      return quest.completed
        ? `Return to ${giverName} and claim your Epic reward.`
        : `Slay a Boss, then return to ${giverName} to turn in the quest.`;
    case "bring_alive":
      return quest.completed
        ? `Return to ${giverName} and claim your Epic reward.`
        : `Subdue a Boss without killing it (enable Subdual damage during combat), then return to ${giverName}.`;
    case "peaceful_way":
      return `Complete ${quest.peaceful_required || 3} peaceful encounters (bribe, peaceful reaction, or Sleep). Progress: ${
        quest.peaceful_count || 0
      }/${quest.peaceful_required || 3}. Claim from any tile once complete.`;
    case "slay_all":
      return quest.completed
        ? "Claim your Epic reward from the Ongoing Quests panel."
        : "Defeat the Final Boss and clear every remaining foe from the dungeon, then claim your reward.";
    default:
      return quest.description;
  }
}

function renderOngoingQuests(session) {
  if (!ongoingQuestsEl) return;
  ongoingQuestsEl.replaceChildren();
  const tile = currentTile(session);
  const quest = session.active_quest;
  const showLady = session.mode === "exploration" && tile?.lady_in_white_available;
  const hasQuest = Boolean(quest && !quest.reward_claimed);
  if (!showLady && !hasQuest) {
    ongoingQuestsEl.classList.add("hidden");
    return;
  }
  ongoingQuestsEl.classList.remove("hidden");
  ongoingQuestsEl.appendChild(node("h2", "", "Ongoing Quests"));

  if (showLady) {
    const offer = node("div", "ongoing-quest-card");
    offer.appendChild(node("strong", "", "Lady in White"));
    offer.appendChild(
      node(
        "div",
        "ongoing-quest-guidance",
        "A quest is offered here. Accept to roll on the Quest Table, or refuse to send her away for the rest of this adventure."
      )
    );
    const actions = node("div", "ongoing-quest-actions");
    const accept = document.createElement("button");
    accept.type = "button";
    accept.className = "secondary";
    accept.textContent = "Accept Quest";
    setButtonTooltip(accept, ACTION_TOOLTIPS.acceptQuest);
    accept.addEventListener("click", () => advance("accept_quest"));
    actions.appendChild(accept);
    const refuse = document.createElement("button");
    refuse.type = "button";
    refuse.className = "secondary";
    refuse.textContent = "Refuse Quest";
    setButtonTooltip(refuse, ACTION_TOOLTIPS.refuseQuest);
    refuse.addEventListener("click", () => advance("refuse_quest"));
    actions.appendChild(refuse);
    offer.appendChild(actions);
    ongoingQuestsEl.appendChild(offer);
  }

  if (hasQuest) {
    const card = node("div", "ongoing-quest-card");
    card.appendChild(node("strong", "", "From Lady in White"));
    card.appendChild(node("div", "ongoing-quest-guidance", quest.description));
    card.appendChild(node("div", "ongoing-quest-guidance", questGuidance(session, quest)));
    const giver = questTile(session);
    if (giver) {
      card.appendChild(node("div", "ongoing-quest-guidance", `Quest-giver tile: ${giver.title}`));
    }
    if (quest.completed) {
      const completeText =
        quest.key === "bring_alive" && quest.captured_boss_name
          ? `Objective complete — ${quest.captured_boss_name} was subdued. Claim your Epic reward.`
          : "Objective complete — claim your Epic reward.";
      card.appendChild(node("div", "ongoing-quest-guidance", completeText));
    }
    const canClaim = canClaimQuestReward(session, quest);
    if (canClaim) {
      const actions = node("div", "ongoing-quest-actions");
      const claim = document.createElement("button");
      claim.type = "button";
      claim.className = "secondary";
      claim.textContent = "Claim Quest Reward";
      setButtonTooltip(claim, ACTION_TOOLTIPS.claimQuestReward);
      claim.addEventListener("click", () => advance("claim_quest_reward"));
      actions.appendChild(claim);
      card.appendChild(actions);
    }
    ongoingQuestsEl.appendChild(card);
  }
}

function renderQuestChoices(session) {
  if (!questChoicesEl) return;
  questChoicesEl.replaceChildren();
  questChoicesEl.classList.add("hidden");
}

function renderEconomyChoices(session) {
  if (!economyChoicesEl) return;
  economyChoicesEl.replaceChildren();
  if (session.mode !== "exploration") {
    economyChoicesEl.classList.add("hidden");
    return;
  }
  const tile = currentTile(session);
  const living = (session.party || []).filter((member) => member.current_life > 0);
  const hasHealer = Boolean(tile.healer_available);
  const hasAlchemist = Boolean(tile.alchemist_available);
  if (!hasHealer && !hasAlchemist) {
    economyChoicesEl.classList.add("hidden");
    return;
  }
  economyChoicesEl.classList.remove("hidden");
  if (hasHealer) {
    economyChoicesEl.appendChild(node("span", "search-label", "Wandering healer (10gp / Life):"));
    for (const member of living) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = `Heal ${member.name}`;
      button.disabled = member.current_life >= member.max_life;
      setButtonTooltip(button, ACTION_TOOLTIPS.buyHealing);
      button.addEventListener("click", () => advance("buy_healing", { character_id: member.character_id }));
      economyChoicesEl.appendChild(button);
    }
  }
  if (hasAlchemist) {
    economyChoicesEl.appendChild(node("span", "search-label", "Wandering alchemist (friendly — not a foe):"));
    economyChoicesEl.appendChild(
      subline("Buy between fights. Potions stay in the buyer's inventory; barbarians cannot drink them — transfer to an ally.")
    );
    for (const member of living) {
      const potionBtn = document.createElement("button");
      potionBtn.type = "button";
      potionBtn.className = "secondary";
      potionBtn.textContent = `${member.name}: Potion (50gp)`;
      potionBtn.disabled = (session.alchemist_potion_bought || []).includes(member.character_id);
      setButtonTooltip(potionBtn, ACTION_TOOLTIPS.buyPotion);
      potionBtn.addEventListener("click", () =>
        advance("buy_alchemist", { character_id: member.character_id, alchemist_item: "potion" })
      );
      economyChoicesEl.appendChild(potionBtn);
      const poisonBtn = document.createElement("button");
      poisonBtn.type = "button";
      poisonBtn.className = "secondary";
      poisonBtn.textContent = `${member.name}: Poison (30gp)`;
      poisonBtn.disabled = (session.alchemist_poison_bought || []).includes(member.character_id);
      setButtonTooltip(poisonBtn, ACTION_TOOLTIPS.buyPoison);
      poisonBtn.addEventListener("click", () =>
        advance("buy_alchemist", { character_id: member.character_id, alchemist_item: "poison" })
      );
      economyChoicesEl.appendChild(poisonBtn);
    }
  }
}

function renderMap(session) {
  mapEl.replaceChildren();
  const tiles = session.map_state.tiles;
  const bounds = mapBounds(session);
  const boundsWidth = bounds.maxX - bounds.minX + 3;
  const boundsHeight = bounds.maxY - bounds.minY + 3;
  const cell = Math.round(MAP_BASE_CELL * state.mapZoom);
  const pad = 1;
  let currentTileEl = null;
  mapEl.style.setProperty("--cell", `${cell}px`);
  mapEl.style.minWidth = `${boundsWidth * cell}px`;
  mapEl.style.minHeight = `${boundsHeight * cell}px`;
  mapZoomLabel.textContent = `${Math.round(state.mapZoom * 100)}%`;

  for (const tile of tiles) {
    const el = node("div", `placed-tile ${tile.tile_type}`);
    if (tile.id === session.map_state.current_tile_id) {
      el.classList.add("current");
      currentTileEl = el;
    }
    const width = rotatedWidth(tile);
    const height = rotatedHeight(tile);
    el.style.left = `${(tile.x - bounds.minX + pad) * cell}px`;
    el.style.top = `${(tile.y - bounds.minY + pad) * cell}px`;
    el.style.width = `${width * cell}px`;
    el.style.height = `${height * cell}px`;
    el.style.setProperty("--cell", `${cell}px`);
    el.title = tile.title;

    if (tile.image) el.appendChild(mapImageLayer(tile, cell, width, height));
    el.appendChild(tileOverlay(tile, session));
    const key = node("span", "tile-key", tile.tile_key);
    el.appendChild(key);
    if (tile.id === session.map_state.current_tile_id) {
      const marker = node("span", "current-party-marker", "Current Party");
      positionInVisibleBounds(marker, tile, width, height);
      el.appendChild(marker);
    }
    mapEl.appendChild(el);
  }
  if (currentTileEl && state.lastCenteredTileId !== session.map_state.current_tile_id) {
    state.lastCenteredTileId = session.map_state.current_tile_id;
  }
  scheduleMapFocus(session);
}

function scheduleMapFocus(session) {
  const currentId = session.map_state.current_tile_id;
  const previousId = state.mapFocusedTileId;
  const tileChanged = previousId !== currentId;
  const shouldZoom = tileChanged && previousId !== null;
  if (tileChanged) state.mapFocusedTileId = currentId;
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (shouldZoom) {
        const tile = currentTile(session);
        const viewport = mapViewportSize();
        if (tile && viewport.width && viewport.height) {
          const target = Math.min(
            (viewport.width * 0.72) / (rotatedWidth(tile) * MAP_BASE_CELL),
            (viewport.height * 0.72) / (rotatedHeight(tile) * MAP_BASE_CELL),
            MAP_MAX_ZOOM
          );
          const nextZoom = clampFloat(target, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
          if (Math.abs(state.mapZoom - nextZoom) > 0.02) {
            state.mapZoom = nextZoom;
            renderMap(session);
            return;
          }
        }
      }
      const current = mapEl.querySelector(".placed-tile.current");
      if (current) centerMapOn(current);
    });
  });
}

function mapViewportSize() {
  return {
    width: mapViewportEl.clientWidth,
    height: mapViewportEl.clientHeight,
  };
}

function mapImageLayer(tile, cell, width, height) {
  const visible = normalizedVisible(tile, width, height);
  const clipped = visible.some((row) => row.includes("0"));
  if (!clipped) return mapImageElement(tile, cell, { className: "map-image-full" });

  const layer = node("div", "map-image-clipped");
  const tileWidth = width * cell;
  const tileHeight = height * cell;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (visible[y]?.[x] === "0") continue;
      const clip = node("span", "map-image-clip-cell");
      clip.style.left = `${x * cell}px`;
      clip.style.top = `${y * cell}px`;
      clip.style.width = `${cell}px`;
      clip.style.height = `${cell}px`;
      const image = mapImageElement(tile, cell, { className: "map-image-cell-image", decorative: true });
      image.style.left = `${tileWidth / 2 - x * cell}px`;
      image.style.top = `${tileHeight / 2 - y * cell}px`;
      clip.appendChild(image);
      layer.appendChild(clip);
    }
  }
  return layer;
}

function mapImageElement(tile, cell, { className, decorative = false }) {
  const image = document.createElement("img");
  image.className = className;
  image.src = tile.image;
  image.alt = decorative ? "" : tile.title;
  if (decorative) image.setAttribute("aria-hidden", "true");
  image.style.width = `${(tile.footprint_width || 1) * cell}px`;
  image.style.height = `${(tile.footprint_height || 1) * cell}px`;
  image.style.transform = mapImageTransform(tile, cell);
  return image;
}

function mapBounds(session) {
  const tiles = session.map_state.tiles;
  return {
    minX: Math.min(...tiles.map((tile) => tile.x)),
    maxX: Math.max(...tiles.map((tile) => tile.x + rotatedWidth(tile) - 1)),
    minY: Math.min(...tiles.map((tile) => tile.y)),
    maxY: Math.max(...tiles.map((tile) => tile.y + rotatedHeight(tile) - 1)),
  };
}

function setMapZoom(nextZoom, { recenter = false } = {}) {
  state.mapZoom = clampFloat(nextZoom, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  if (recenter) state.lastCenteredTileId = null;
  if (state.session) renderMap(state.session);
}

function zoomToCurrentRoom() {
  const tile = currentTile(state.session);
  const viewport = mapViewportSize();
  if (!tile || !viewport.width || !viewport.height) return;
  const target = Math.min(
    (viewport.width * 0.62) / (rotatedWidth(tile) * MAP_BASE_CELL),
    (viewport.height * 0.62) / (rotatedHeight(tile) * MAP_BASE_CELL),
    MAP_MAX_ZOOM
  );
  setMapZoom(target, { recenter: true });
}

function zoomToFullMap() {
  const viewport = mapViewportSize();
  if (!state.session || !viewport.width || !viewport.height) return;
  const bounds = mapBounds(state.session);
  const boundsWidth = bounds.maxX - bounds.minX + 3;
  const boundsHeight = bounds.maxY - bounds.minY + 3;
  const target = Math.min(
    (viewport.width - 24) / (boundsWidth * MAP_BASE_CELL),
    (viewport.height - 24) / (boundsHeight * MAP_BASE_CELL),
    1.2
  );
  state.mapZoom = clampFloat(target, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  if (state.session) renderMap(state.session);
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      mapViewportEl.scrollLeft = Math.max(0, (mapViewportEl.scrollWidth - mapViewportEl.clientWidth) / 2);
      mapViewportEl.scrollTop = Math.max(0, (mapViewportEl.scrollHeight - mapViewportEl.clientHeight) / 2);
    });
  });
}

function panMap(deltaX, deltaY) {
  mapViewportEl.scrollBy({ left: deltaX, top: deltaY, behavior: "smooth" });
}

function centerCurrentTile() {
  const current = mapEl.querySelector(".placed-tile.current");
  if (current) centerMapOn(current);
}

function centerMapOn(element) {
  const maxScrollLeft = Math.max(0, mapViewportEl.scrollWidth - mapViewportEl.clientWidth);
  const maxScrollTop = Math.max(0, mapViewportEl.scrollHeight - mapViewportEl.clientHeight);
  mapViewportEl.scrollLeft = clampFloat(
    element.offsetLeft + element.offsetWidth / 2 - mapViewportEl.clientWidth / 2,
    0,
    maxScrollLeft
  );
  mapViewportEl.scrollTop = clampFloat(
    element.offsetTop + element.offsetHeight / 2 - mapViewportEl.clientHeight / 2,
    0,
    maxScrollTop
  );
}

function handleMapWheel(event) {
  if (!event.ctrlKey) return;
  event.preventDefault();
  setMapZoom(state.mapZoom + (event.deltaY < 0 ? 0.1 : -0.1), { recenter: true });
}

function startMapPan(event) {
  if (event.button !== 0 && event.button !== 1) return;
  if (event.button === 0 && event.target.closest("button, a, input, label, select, textarea")) return;
  event.preventDefault();
  mapViewportEl.classList.add("panning");
  mapViewportEl.setPointerCapture(event.pointerId);
  const startX = event.clientX;
  const startY = event.clientY;
  const startScrollLeft = mapViewportEl.scrollLeft;
  const startScrollTop = mapViewportEl.scrollTop;

  const move = (moveEvent) => {
    moveEvent.preventDefault();
    mapViewportEl.scrollLeft = startScrollLeft - (moveEvent.clientX - startX);
    mapViewportEl.scrollTop = startScrollTop - (moveEvent.clientY - startY);
  };

  const stop = (stopEvent) => {
    if (stopEvent) stopEvent.preventDefault();
    mapViewportEl.classList.remove("panning");
    mapViewportEl.removeEventListener("pointermove", move);
    mapViewportEl.removeEventListener("pointerup", stop);
    mapViewportEl.removeEventListener("pointercancel", stop);
    if (mapViewportEl.hasPointerCapture(event.pointerId)) {
      mapViewportEl.releasePointerCapture(event.pointerId);
    }
  };

  mapViewportEl.addEventListener("pointermove", move);
  mapViewportEl.addEventListener("pointerup", stop);
  mapViewportEl.addEventListener("pointercancel", stop);
}

function currentPartyEditIds() {
  if (!state.editingPartyId) return [];
  const party = state.parties.find((item) => item.id === state.editingPartyId);
  return party ? party.character_ids : [];
}

function characterNameById(id) {
  const character = state.characters.find((item) => item.id === id);
  return character ? character.name : `Missing ${id.slice(0, 6)}`;
}

function startPartyEdit(party) {
  state.editingPartyId = party.id;
  state.selectedPartyId = party.id;
  state.partyMarchingIds = [...party.character_ids];
  partyName.value = party.name;
  saveParty.textContent = "Update Party";
  cancelPartyEdit.classList.remove("hidden");
  renderCharacters();
  renderParties();
}

function cancelPartyEditMode() {
  state.editingPartyId = null;
  state.partyMarchingIds = [];
  partyName.value = "";
  saveParty.textContent = "Save Party";
  cancelPartyEdit.classList.add("hidden");
  renderCharacters();
}

async function deleteCharacter(characterId) {
  try {
    await api(`/api/characters/${characterId}`, { method: "DELETE" });
    if (state.selectedCharacterId === characterId) state.selectedCharacterId = null;
    setStatus("Character deleted");
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
}

async function healCharacter(characterId) {
  try {
    await api(`/api/characters/${characterId}/heal`, { method: "POST" });
    setStatus("Character healed");
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
}

async function saveCharacterWeaponDefaults(characterId, payload) {
  try {
    const character = await api(`/api/characters/${characterId}/weapon-defaults`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const index = state.characters.findIndex((item) => item.id === character.id);
    if (index >= 0) state.characters[index] = character;
    setStatus("Weapon defaults saved");
    renderCharacters();
    return character;
  } catch (error) {
    handleError(error);
    throw error;
  }
}

const equipmentShopDialogState = {
  tab: "buy",
  selectedBuyKey: null,
  catalog: null,
};

function selectedShopCharacter() {
  const id = equipmentShopCharacterSelect?.value;
  if (!id) return null;
  return state.characters.find((character) => character.id === id) || null;
}

function setEquipmentShopTab(tab) {
  equipmentShopDialogState.tab = tab;
  const buyActive = tab === "buy";
  equipmentShopBuyTab?.classList.toggle("active", buyActive);
  equipmentShopSellTab?.classList.toggle("active", !buyActive);
  equipmentShopBuyPanel?.classList.toggle("hidden", !buyActive);
  equipmentShopSellPanel?.classList.toggle("hidden", buyActive);
  if (equipmentShopConfirmBtn) {
    equipmentShopConfirmBtn.textContent = buyActive ? "Buy selected" : "Sell item";
  }
  updateEquipmentShopConfirmState();
}

async function refreshEquipmentShopSellQuote() {
  const character = selectedShopCharacter();
  const itemName = equipmentShopSellItem?.value;
  if (!equipmentShopSellQuote || !character || !itemName) {
    if (equipmentShopSellQuote) equipmentShopSellQuote.textContent = "";
    return;
  }
  try {
    const quote = await api(
      `/api/characters/${character.id}/sell-quote?item_name=${encodeURIComponent(itemName)}`
    );
    if (quote.quote_gp != null) {
      equipmentShopSellQuote.textContent = `Payout: ${quote.quote_gp}gp — ${quote.note}`;
    } else {
      equipmentShopSellQuote.textContent = quote.note || "Roll when you sell.";
    }
  } catch (error) {
    equipmentShopSellQuote.textContent = "";
    handleError(error);
  }
}

async function refreshEquipmentShopDialog() {
  const character = selectedShopCharacter();
  if (!character || !equipmentShopBuyList) return;
  if (equipmentShopNote) {
    equipmentShopNote.textContent =
      `${character.name} (${character.class_name}) — ${character.gold}gp on hand. ` +
      "Buy before or between adventures. No bank: gold stays on hero sheets; 200gp carry limit applies only in the dungeon.";
  }
  try {
    const payload = await api(`/api/rules/equipment-shop?class_id=${encodeURIComponent(character.class_id)}`);
    equipmentShopDialogState.catalog = payload;
    equipmentShopBuyList.replaceChildren();
    equipmentShopDialogState.selectedBuyKey = null;
    for (const item of payload.items || []) {
      const row = node("label", `equipment-shop-row${item.allowed ? "" : " disabled"}`);
      const radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "equipment-shop-buy";
      radio.value = item.key;
      radio.disabled = !item.allowed || character.gold < item.price_gp;
      radio.addEventListener("change", () => {
        equipmentShopDialogState.selectedBuyKey = item.key;
        updateEquipmentShopConfirmState();
      });
      const text = node("span");
      text.textContent = `${item.name} — ${item.price_gp}gp`;
      if (!item.allowed) {
        text.appendChild(subline("Not allowed for this class"));
      } else if (character.gold < item.price_gp) {
        text.appendChild(subline("Not enough gold"));
      } else if (item.magic) {
        text.appendChild(subline("Magic (sell only if found as loot)"));
      }
      row.append(radio, text);
      equipmentShopBuyList.appendChild(row);
    }
    if (equipmentShopSellItem) {
      equipmentShopSellItem.replaceChildren();
      for (const item of character.inventory || []) {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        equipmentShopSellItem.appendChild(option);
      }
    }
    await refreshEquipmentShopSellQuote();
    updateEquipmentShopConfirmState();
  } catch (error) {
    handleError(error);
  }
}

function updateEquipmentShopConfirmState() {
  if (!equipmentShopConfirmBtn) return;
  if (equipmentShopDialogState.tab === "buy") {
    equipmentShopConfirmBtn.disabled = !equipmentShopDialogState.selectedBuyKey;
  } else {
    equipmentShopConfirmBtn.disabled = !(equipmentShopSellItem?.value && selectedShopCharacter());
  }
}

function openEquipmentShopDialog(preferredCharacterId = null) {
  if (!equipmentShopDialog || !state.characters.length) {
    setStatus("Create a hero before visiting the equipment shop.");
    return;
  }
  if (equipmentShopCharacterSelect) {
    equipmentShopCharacterSelect.replaceChildren();
    for (const character of sortedCharacters([...state.characters])) {
      const option = document.createElement("option");
      option.value = character.id;
      option.textContent = `${character.name} (${character.class_name}, ${character.gold}gp)`;
      equipmentShopCharacterSelect.appendChild(option);
    }
    const targetId =
      preferredCharacterId ||
      state.selectedCharacterId ||
      state.characters[0]?.id;
    if (targetId) equipmentShopCharacterSelect.value = targetId;
  }
  setEquipmentShopTab("buy");
  refreshEquipmentShopDialog();
  equipmentShopDialog.showModal();
}

async function confirmEquipmentShopDialog() {
  const character = selectedShopCharacter();
  if (!character) return;
  equipmentShopConfirmBtn.disabled = true;
  try {
    if (equipmentShopDialogState.tab === "buy") {
      const itemKey = equipmentShopDialogState.selectedBuyKey;
      if (!itemKey) return;
      const result = await api(`/api/characters/${character.id}/buy-equipment`, {
        method: "POST",
        body: JSON.stringify({ item_key: itemKey }),
      });
      const index = state.characters.findIndex((item) => item.id === result.character.id);
      if (index >= 0) state.characters[index] = result.character;
      setStatus(result.message);
    } else {
      const itemName = equipmentShopSellItem?.value;
      if (!itemName) return;
      const result = await api(`/api/characters/${character.id}/sell-item`, {
        method: "POST",
        body: JSON.stringify({ item_name: itemName }),
      });
      const index = state.characters.findIndex((item) => item.id === result.character.id);
      if (index >= 0) state.characters[index] = result.character;
      setStatus(result.message);
    }
    renderCharacters();
    await refreshEquipmentShopDialog();
  } catch (error) {
    handleError(error);
  } finally {
    updateEquipmentShopConfirmState();
  }
}

async function transferCharacter(fromCharacterId, payload, options = {}) {
  const { skipRender = false } = options;
  try {
    const result = await api(`/api/characters/${fromCharacterId}/transfer`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    for (const updated of [result.source, result.target]) {
      const index = state.characters.findIndex((character) => character.id === updated.id);
      if (index >= 0) state.characters[index] = updated;
    }
    setStatus(result.message);
    if (!skipRender) {
      renderCharacters();
      renderParties();
    }
    return result;
  } catch (error) {
    handleError(error);
    throw error;
  }
}

async function deleteParty(partyId) {
  try {
    await api(`/api/parties/${partyId}`, { method: "DELETE" });
    if (state.selectedPartyId === partyId) state.selectedPartyId = null;
    if (state.editingPartyId === partyId) cancelPartyEditMode();
    setStatus("Party deleted");
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
}

async function healParty(partyId) {
  try {
    await api(`/api/parties/${partyId}/heal`, { method: "POST" });
    setStatus("Party healed");
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
}

async function exportPlayerData() {
  try {
    const payload = await api("/api/export/player-data");
    const stamp = new Date().toISOString().slice(0, 10);
    downloadJson(`ahazi-player-data-${stamp}.json`, payload);
    setStatus("Player data exported");
  } catch (error) {
    handleError(error);
  }
}

async function importPlayerData(file) {
  if (!file) return;
  try {
    const payload = await readJsonFile(file);
    const result = await api("/api/import/player-data", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setStatus(`Imported ${result.characters} characters and ${result.parties} parties`);
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  } finally {
    importPlayerFile.value = "";
  }
}

function tileOverlay(tile, session) {
  const overlay = node("div", "map-tile-overlay");
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const sideLabels = exitSideLabels(tile);
  const isCurrent = tile.id === session.map_state.current_tile_id;
  overlay.style.gridTemplateColumns = `repeat(${width}, minmax(0, 1fr))`;
  overlay.style.gridTemplateRows = `repeat(${height}, minmax(0, 1fr))`;
  const walkable = normalizedWalkable(tile, width, height);
  const visible = normalizedVisible(tile, width, height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const isHidden = visible[y]?.[x] === "0";
      let currentClass = "";
      if (isCurrent && !isHidden) {
        currentClass = isCurrentVisibleEdge(visible, x, y, width, height) ? "current-edge" : "current-interior";
      }
      overlay.appendChild(
        node(
          "span",
          `map-square ${walkable[y]?.[x] === "0" ? "blocked" : "walkable"} ${isHidden ? "hidden" : ""} ${currentClass} shape-${
            isHidden ? "F" : cellShape(tile, x, y)
          }`
        )
      );
    }
  }
  for (const exit of tile.exits || []) {
    overlay.appendChild(mapExitMarker(tile, exit, width, height, sideLabels.get(exit.id), session));
  }
  const contentMarkers = tileContentMarkers(tile, session, width, height);
  if (contentMarkers) overlay.appendChild(contentMarkers);
  return overlay;
}

function mapExitMarker(tile, exit, width, height, sideLabel, session) {
  const canUse = session.mode === "exploration" && tile.id === session.map_state.current_tile_id && exit.status !== "blocked";
  const onCurrentTile = tile.id === session.map_state.current_tile_id;
  const isClosedDoor = exit.kind === "door" && !exit.door_open;
  const doorStateClass = exit.kind === "door" ? (exit.door_open ? " open" : " closed") : "";
  const marker = node(
    canUse ? "button" : "span",
    `map-exit-marker ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""}${exit.status === "blocked" ? " blocked" : ""}${doorStateClass} ${exit.direction}`
  );
  if (canUse) {
    marker.type = "button";
    marker.classList.add("clickable");
    marker.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (isClosedDoor) {
        advance("open_door", { exit_id: exit.id, character_id: leadMemberId(session) });
        return;
      }
      advance("explore", { exit_id: exit.id, direction: exit.direction });
    });
  }
  const label = exitDisplayLabel(exit, sideLabel);
  const doorHint = exit.kind === "door" ? (exit.door_open ? " - open" : " - closed") : "";
  marker.title = exit.status === "blocked" ? `${label} - dead end` : `${label}${doorHint}${exit.door_result ? ` (${exit.door_result})` : ""}`;
  const cellW = 100 / width;
  const cellH = 100 / height;
  const x = Math.max(0, Math.min(exit.x || 0, width - 1));
  const y = Math.max(0, Math.min(exit.y || 0, height - 1));
  const span = clampExitSpan(exit, width, height);
  if (exit.direction === "north" || exit.direction === "south") {
    marker.style.left = `${x * cellW + cellW * (span / 2)}%`;
    marker.style.top = `${y * cellH + (exit.direction === "north" ? 0 : cellH)}%`;
    marker.style.width = `${cellW * Math.max(0.72, span - 0.16)}%`;
  } else {
    marker.style.left = `${x * cellW + (exit.direction === "west" ? 0 : cellW)}%`;
    marker.style.top = `${y * cellH + cellH * (span / 2)}%`;
    marker.style.height = `${cellH * Math.max(0.72, span - 0.16)}%`;
  }
  marker.appendChild(node("span", "map-exit-marker-label", compactExitLabel(exit, sideLabel, onCurrentTile)));
  return marker;
}

function tileContentMarkers(tile, session, width, height) {
  const markers = [];
  const liveEnemies = (tile.enemies || []).filter((enemy) => enemy.life > 0);
  const defeatedEnemies = tile.defeated_enemies || [];
  const objects = tile.objects || [];
  const fallen = fallenMembersForTile(tile, session);
  if (liveEnemies.length) markers.push(contentMarker("monster", `${liveEnemies.length} active foe${liveEnemies.length === 1 ? "" : "s"}`, liveEnemies.length));
  if (defeatedEnemies.length) {
    const subdued = defeatedEnemies.filter((enemy) => enemy.subdued);
    const slain = defeatedEnemies.filter((enemy) => !enemy.subdued);
    const parts = [];
    if (subdued.length) parts.push(`${subdued.map(defeatedEnemyLabel).join(", ")} subdued`);
    if (slain.length) parts.push(`${slain.map((enemy) => enemy.name).join(", ")} slain`);
    markers.push(
      contentMarker(
        "defeated",
        parts.join("; ") + " here",
        defeatedEnemies.length
      )
    );
  }
  if (objects.some((item) => /treasure/i.test(item))) markers.push(contentMarker("treasure", "Treasure present"));
  if (objects.some((item) => /trap/i.test(item))) markers.push(contentMarker("trap", "Trap present"));
  if (fallen.length) markers.push(contentMarker("fallen", `${fallen.map((member) => member.name).join(", ")} fallen here`, fallen.length));
  if (tile.lady_in_white_available) {
    markers.push(contentMarker("quest", "Lady in White — quest available"));
  } else if (session.active_quest && !session.active_quest.reward_claimed && session.active_quest.tile_id === tile.id) {
    markers.push(contentMarker("quest", "Quest from Lady in White"));
  }
  if (!markers.length) return null;
  const wrap = node("div", "map-content-markers");
  positionContentMarkersInVisibleBounds(wrap, tile, width, height);
  wrap.append(...markers);
  return wrap;
}

function contentMarker(kind, title, count = 0) {
  const definition = iconDefinition(kind);
  const marker = node("span", `map-content-marker ${kind}`);
  marker.title = title;
  marker.setAttribute("aria-label", title);
  marker.appendChild(iconGraphic(definition, "map-content-icon", title));
  if (count > 1) marker.appendChild(node("span", "marker-count", String(count)));
  return marker;
}

function iconDefinition(iconId) {
  return (
    state.icons.find((icon) => icon.id === iconId) || {
      id: iconId,
      label: titleFromKey(iconId),
      description: "",
      file: "",
      fallback: iconId,
      attribution: "",
      license: "",
      source_url: "",
    }
  );
}

function iconGraphic(definition, className, title = "") {
  if (definition.file) {
    const image = document.createElement("img");
    image.className = `${className} icon-image`;
    image.src = assetUrl(definition.file);
    image.alt = definition.label;
    image.title = title || iconTitle(definition);
    return image;
  }
  const fallback = definition.fallback || definition.id;
  const icon =
    className === "map-content-icon"
      ? node("span", `${className} ${fallback}`)
      : node("span", className);
  if (className !== "map-content-icon") {
    icon.appendChild(node("span", `map-content-icon ${fallback}`));
  }
  icon.title = title || iconTitle(definition);
  icon.setAttribute("aria-label", icon.title);
  return icon;
}

function iconTitle(definition) {
  const parts = [definition.label, definition.description, definition.attribution].filter(Boolean);
  return parts.join(" - ");
}

function assetUrl(path) {
  const clean = String(path || "")
    .replace(/^\/?assets\//, "")
    .replace(/^\/+/, "");
  return `/assets/${clean}`;
}

function fallenMembersForTile(tile, session) {
  const ids = new Set(tile.fallen_character_ids || []);
  return (session.party || []).filter((member) => ids.has(member.character_id));
}

function clampExitSpan(exit, width, height) {
  const span = Math.max(1, Number.parseInt(exit.span || 1, 10));
  if (exit.direction === "north" || exit.direction === "south") {
    return Math.min(span, Math.max(1, width - Math.max(0, Math.min(exit.x || 0, width - 1))));
  }
  return Math.min(span, Math.max(1, height - Math.max(0, Math.min(exit.y || 0, height - 1))));
}

function clampFloat(value, min, max) {
  const number = Number.parseFloat(value);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function normalizedWalkable(tile, width, height) {
  const rows = Array.isArray(tile.walkable) ? tile.walkable : [];
  return Array.from({ length: height }, (_, y) => {
    const source = String(rows[y] || "");
    return Array.from({ length: width }, (__, x) => (source[x] === "0" ? "0" : "1")).join("");
  });
}

function normalizedVisible(tile, width, height) {
  const rows = Array.isArray(tile.visible) ? tile.visible : [];
  return Array.from({ length: height }, (_, y) => {
    const source = String(rows[y] || "");
    return Array.from({ length: width }, (__, x) => (source[x] === "0" ? "0" : "1")).join("");
  });
}

function isCurrentVisibleEdge(visible, x, y, width, height) {
  if (visible[y]?.[x] === "0") return false;
  for (const [nx, ny] of [
    [x - 1, y],
    [x + 1, y],
    [x, y - 1],
    [x, y + 1],
  ]) {
    if (nx < 0 || ny < 0 || nx >= width || ny >= height) return true;
    if (visible[ny]?.[nx] === "0") return true;
  }
  return false;
}

function visibleCellBounds(tile, width, height) {
  const visible = normalizedVisible(tile, width, height);
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (visible[y]?.[x] !== "0") {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }
  if (maxX < 0) return { minX: 0, minY: 0, maxX: width - 1, maxY: height - 1 };
  return { minX, minY, maxX, maxY };
}

function walkableCellBounds(tile, width, height) {
  const walkable = normalizedWalkable(tile, width, height);
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (walkable[y]?.[x] !== "0") {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }
  if (maxX < 0) return { minX: 0, minY: 0, maxX: width - 1, maxY: height - 1 };
  return { minX, minY, maxX, maxY };
}

function markerAnchorPercent(tile, width, height) {
  const bounds = walkableCellBounds(tile, width, height);
  return {
    left: `${((bounds.minX + bounds.maxX + 1) / 2 / width) * 100}%`,
    top: `${((bounds.minY + bounds.maxY + 1) / 2 / height) * 100}%`,
  };
}

function positionInVisibleBounds(element, tile, width, height) {
  const anchor = markerAnchorPercent(tile, width, height);
  element.style.left = anchor.left;
  element.style.top = anchor.top;
  element.style.transform = "translate(-50%, -50%)";
}

function positionContentMarkersInVisibleBounds(element, tile, width, height) {
  const anchor = markerAnchorPercent(tile, width, height);
  element.style.left = anchor.left;
  element.style.top = anchor.top;
  element.style.right = "";
  element.style.bottom = "";
  element.style.maxWidth = "";
  element.style.transform = "translate(-50%, -50%)";
}

function cellShape(tile, x, y) {
  const rows = Array.isArray(tile.cell_shapes) ? tile.cell_shapes : [];
  return rows[y]?.[x] || "F";
}

function mapImageTransform(tile, cellSize) {
  const calibrationSize = tile.editor_cell_size || 80;
  const offsetScale = cellSize / calibrationSize;
  const offset = rotatedOffset((tile.image_offset_x || 0) * offsetScale, (tile.image_offset_y || 0) * offsetScale, tile.rotation || 0);
  const scale = tile.image_scale || 1;
  return `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px) rotate(${tile.rotation || 0}deg) scale(${scale})`;
}

function rotatedWidth(tile) {
  return (tile.rotation || 0) % 180 === 0 ? tile.footprint_width || 1 : tile.footprint_height || 1;
}

function rotatedHeight(tile) {
  return (tile.rotation || 0) % 180 === 0 ? tile.footprint_height || 1 : tile.footprint_width || 1;
}

function rotatedOffset(x, y, rotation) {
  const turns = ((rotation || 0) / 90) % 4;
  if (turns === 1) return { x: -y, y: x };
  if (turns === 2) return { x: -x, y: -y };
  if (turns === 3) return { x: y, y: -x };
  return { x, y };
}

function currentTile(session) {
  return session.map_state.tiles.find((tile) => tile.id === session.map_state.current_tile_id);
}

function renderTileDetail(session) {
  const tile = currentTile(session);
  tileDetail.replaceChildren();
  if (!tile) {
    tileDetail.appendChild(node("div", "item", "Current map element is missing from session state."));
    return;
  }
  const sideLabels = exitSideLabels(tile);
  if (tile.image) {
    const image = document.createElement("img");
    image.src = tile.image;
    image.alt = tile.title;
    image.style.transform = `rotate(${tile.rotation || 0}deg)`;
    tileDetail.appendChild(image);
  } else {
    tileDetail.appendChild(node("div", "item", "No map element image available"));
  }

  const info = node("div");
  info.appendChild(node("h2", "", tile.title));
  const pendingCaster = pendingLevelUpMember(session);
  if (pendingCaster) {
    const banner = node("div", "level-up-spell-pick");
    banner.appendChild(
      node("strong", "", `${pendingCaster.name} must choose a spell for the new Level ${pendingCaster.level} slot.`)
    );
    const pickRow = node("div", "level-up-spell-pick-actions");
    if (appendLevelUpSpellPickButtons(pickRow, pendingCaster)) {
      banner.appendChild(pickRow);
      info.appendChild(banner);
    }
  }
  info.appendChild(
    subline(
      `${tile.tile_type} | ${tile.content_key} | ${tile.footprint_width || 1}x${tile.footprint_height || 1} squares | rotation ${tile.rotation || 0}deg`
    )
  );
  info.appendChild(node("p", "", tile.description));
  if (session.camped_outside) {
    info.appendChild(subline("Camped outside the dungeon. Re-enter through any open passage to continue the adventure."));
  }
  const fallenIds = fallenInDungeon(session);
  if (fallenIds.length) {
    const fallenNames = session.party
      .filter((member) => fallenIds.includes(member.character_id))
      .map((member) => member.name)
      .join(", ");
    info.appendChild(
      subline(`Fallen inside dungeon: ${fallenNames || fallenIds.length}. Leave via dungeon exit to camp and return later.`)
    );
  }
  info.appendChild(
    subline(
      `XP (${session.xp_system || "classical"}): ${session.clues_found || 0} Clues · ` +
        `${session.minor_encounters_defeated || 0}/10 minors · ` +
        `${session.xp_rolls_pending || 0} roll(s) · ` +
        `${session.slower_xp_bank || 0} banked · ` +
        `${session.old_school_xp_tally || 0} Old School tally`
    )
  );
  if (tile.lady_in_white_available) info.appendChild(subline("The Lady in White offers a Quest."));
  if (session.final_boss_defeated) info.appendChild(subline("Final Boss slain."));
  if (tile.healer_available) info.appendChild(subline("Wandering healer is here."));
  if (tile.alchemist_available) {
    info.appendChild(
      subline("Wandering alchemist is here (friendly trader — not a monster). Use Buy buttons when not in combat.")
    );
  }
  info.appendChild(subline(`Objects: ${(tile.objects || []).length ? tile.objects.join(", ") : "none"}`));
  info.appendChild(
    subline(
      `Enemies: ${(tile.enemies || []).length ? tile.enemies.map((enemy) => `${enemy.name} ${enemy.life}/${enemy.max_life}`).join(", ") : "none"}`
    )
  );
  if ((tile.defeated_enemies || []).length) {
    const labels = tile.defeated_enemies.map(defeatedEnemyLabel);
    info.appendChild(subline(`Defeated: ${labels.join(", ")}`));
  }
  const fallen = fallenMembersForTile(tile, session);
  if (fallen.length) {
    info.appendChild(subline(`Fallen: ${fallen.map((member) => member.name).join(", ")}`));
  }
  if (tile.trap_key && !tile.trap_resolved) {
    info.appendChild(subline(`Trap: ${tile.trap_key} (L${tile.trap_level || "?"})`));
  }
  if (tile.treasure_summary && !tile.treasure_claimed) {
    info.appendChild(subline(`Treasure: ${tile.treasure_summary}`));
  }
  info.appendChild(
    subline(
      `Exits: ${(tile.exits || [])
        .map((exit) => {
          const label = exitDisplayLabel(exit, sideLabels.get(exit.id));
          const doorState = exit.kind === "door" ? (exit.door_open ? " open" : " closed") : "";
          return `${label} ${exit.status}${doorState}`;
        })
        .join(", ")}`
    )
  );
  tileDetail.appendChild(info);
}

function renderIconKey() {
  if (!iconKey) return;
  if (state.iconKeyExpanded === null) {
    state.iconKeyExpanded = readIconKeyExpanded();
  }
  iconKey.replaceChildren();
  const details = document.createElement("details");
  details.className = "icon-key-details";
  details.open = state.iconKeyExpanded;
  const summary = document.createElement("summary");
  summary.textContent = "Map Icon Key";
  details.appendChild(summary);
  const list = node("div", "icon-key-list");
  for (const iconId of ["monster", "defeated", "treasure", "trap", "fallen", "quest", "door", "passage", "dungeon-exit"]) {
    const definition = iconDefinition(iconId);
    const row = node("div", "icon-key-row");
    row.title = iconTitle(definition);
    const sample = contentMarker(iconId, definition.label);
    sample.classList.add("icon-key-sample");
    row.appendChild(sample);
    const text = node("div", "icon-key-text");
    text.appendChild(node("strong", "", definition.label));
    text.appendChild(subline(definition.description || "No description yet."));
    if (definition.attribution || definition.license) {
      text.appendChild(subline([definition.attribution, definition.license].filter(Boolean).join(" | ")));
    }
    if (definition.source_url) {
      const link = document.createElement("a");
      link.href = definition.source_url;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = "Icon source";
      text.appendChild(link);
    }
    row.appendChild(text);
    list.appendChild(row);
  }
  details.appendChild(list);
  details.addEventListener("toggle", () => {
    state.iconKeyExpanded = details.open;
    writeIconKeyExpanded(details.open);
  });
  iconKey.appendChild(details);
}

function readIconKeyExpanded() {
  try {
    return window.localStorage?.getItem(ICON_KEY_EXPANDED_KEY) === "1";
  } catch {
    return false;
  }
}

function writeIconKeyExpanded(expanded) {
  try {
    window.localStorage?.setItem(ICON_KEY_EXPANDED_KEY, expanded ? "1" : "0");
  } catch {
    // ignore storage failures
  }
}

function doorTypeHint(exit, session) {
  const level = exit.door_level;
  const hcl = Math.max(...(session.party || []).map((member) => member.level || 1), 1);
  const levelText = level != null ? `L${level}` : "door level";
  const hints = {
    locked: `Locked (${levelText}). Rogue lock-picks (+Level) or Warrior/Barbarian bashes (+Level). Exploding d6 + modifier vs door level.`,
    iron: `Iron (${levelText}). Rogue lock-pick, or destroy with Fireball/Lightning. Cannot bash.`,
    sealed: `Magically sealed (${levelText}). Spellcasting roll vs door level; one attempt; natural 1 deals 2 damage.`,
    illusion: `Illusion (HCL ${hcl}). Spend 3 held Clues or an Illusionist spellcasting roll.`,
    lever: `Lever door. Spend 1 held Clue (${session.clues_found || 0} held) or 1 gnome Gadget point.`,
    trap_door: `Trap door (${levelText}). Opens easily; trap triggers unless a Rogue disarms first.`,
    unlocked: "Unlocked. Opens easily.",
  };
  return hints[exit.door_type] || exit.door_result || ACTION_TOOLTIPS.openDoor;
}

function livingParty(session) {
  return (session.party || []).filter((member) => member.current_life > 0);
}

function appendExitSection(parent, title, note) {
  const section = node("div", "exit-section");
  section.appendChild(node("div", "exit-section-title", title));
  if (note) section.appendChild(node("div", "exit-section-note muted", note));
  const actions = node("div", "actions exit-section-actions");
  section.appendChild(actions);
  parent.appendChild(section);
  return actions;
}

function appendOpenDoorAttemptButtons(row, exit, members, labelForMember) {
  for (const member of members) {
    const label = labelForMember(member);
    const btn = node("button", "secondary", label);
    btn.type = "button";
    setButtonTooltip(btn, ACTION_TOOLTIPS.openDoor);
    btn.addEventListener("click", () =>
      advance("open_door", { exit_id: exit.id, character_id: member.character_id })
    );
    row.appendChild(btn);
  }
}

function appendOpenDoorActions(session, exit, sideLabel, actions) {
  const label = exitDisplayLabel(exit, sideLabel);
  const card = node("div", "exit-door-card item");
  card.appendChild(node("strong", "", label));
  const doorType = exit.door_type || null;
  card.appendChild(subline(exit.door_result || (doorType ? titleCase(doorType) : "Closed — type not yet rolled (2d6)")));
  card.appendChild(subline(doorType ? doorTypeHint(exit, session) : "Pick a hero to attempt the door; the door table roll happens on first try."));
  const row = node("div", "actions tight-actions");
  card.appendChild(row);
  actions.appendChild(card);

  const members = livingParty(session);
  if (!members.length) {
    row.appendChild(subline("No living heroes can work this door."));
    return;
  }

  if (!doorType) {
    appendOpenDoorAttemptButtons(row, exit, members, (member) => `${member.name}: open door (2d6)`);
    return;
  }

  let addedButton = false;
  const trackButton = (btn) => {
    row.appendChild(btn);
    addedButton = true;
  };

  if (doorType === "sealed") {
    if (!exit.door_sealed_attempted) {
      for (const member of members) {
        const btn = node("button", "secondary", `${member.name}: spellcast sealed door`);
        btn.type = "button";
        btn.addEventListener("click", () =>
          advance("spellcast_door", { exit_id: exit.id, character_id: member.character_id })
        );
        trackButton(btn);
      }
    } else {
      row.appendChild(subline("Sealed door already resisted spellcasting."));
    }
    return;
  }

  if (doorType === "illusion") {
    const clueBtn = node("button", "secondary", `Spend 3 Clues (${session.clues_found || 0} held)`);
    clueBtn.type = "button";
    clueBtn.disabled = (session.clues_found || 0) < 3;
    clueBtn.addEventListener("click", () => advance("spend_clues_on_door", { exit_id: exit.id }));
    trackButton(clueBtn);
    for (const member of members.filter((m) => m.class_id === "illusionist")) {
      if ((exit.door_illusion_attempted_ids || []).includes(member.character_id)) continue;
      const btn = node("button", "secondary", `${member.name}: dispel illusion`);
      btn.type = "button";
      btn.addEventListener("click", () =>
        advance("spellcast_door", { exit_id: exit.id, character_id: member.character_id })
      );
      trackButton(btn);
    }
    return;
  }

  if (doorType === "lever") {
    const leverBtn = node("button", "secondary", `Spend 1 Clue (${session.clues_found || 0} held)`);
    leverBtn.type = "button";
    leverBtn.disabled = (session.clues_found || 0) < 1;
    leverBtn.addEventListener("click", () => advance("spend_clues_on_door", { exit_id: exit.id }));
    trackButton(leverBtn);
    return;
  }

  if (doorType === "iron") {
    for (const member of members.filter((m) => m.class_id === "rogue")) {
      const btn = node("button", "secondary", `${member.name}: lock-pick iron door`);
      btn.type = "button";
      btn.addEventListener("click", () => advance("open_door", { exit_id: exit.id, character_id: member.character_id }));
      trackButton(btn);
    }
    for (const member of members) {
      for (const spell of ["Fireball", "Lightning"]) {
        if (!(member.spells || []).some((s) => normalizeSpellKey(s) === normalizeSpellKey(spell))) continue;
        if (spellExpended(session, member, spell)) continue;
        const btn = node("button", "secondary", `${member.name}: ${spell}`);
        btn.type = "button";
        btn.addEventListener("click", () =>
          advance("cast_spell", { exit_id: exit.id, character_id: member.character_id, spell_name: spell })
        );
        trackButton(btn);
      }
    }
    if (!addedButton) {
      row.appendChild(subline("Iron doors need a Rogue lock-pick or Fireball/Lightning."));
    }
    return;
  }

  const canForce = doorType === "locked" || doorType === "trap_door" || doorType === "unlocked";
  if (canForce) {
    for (const member of members) {
      let actionLabel = `${member.name}: open door`;
      if (doorType === "locked") {
        if (member.class_id === "rogue") actionLabel = `${member.name}: lock-pick`;
        else if (member.class_id === "warrior" || member.class_id === "barbarian") actionLabel = `${member.name}: bash door`;
      }
      const btn = node("button", "secondary", actionLabel);
      btn.type = "button";
      btn.addEventListener("click", () => advance("open_door", { exit_id: exit.id, character_id: member.character_id }));
      trackButton(btn);
    }
  }

  if (doorType === "locked" || doorType === "lever" || doorType === "unlocked" || doorType === "trap_door") {
    for (const member of members.filter((m) => m.class_id === "druid")) {
      if (spellExpended(session, member, "Warp Wood")) continue;
      if (!(member.spells || []).some((s) => normalizeSpellKey(s) === "warp_wood")) continue;
      const btn = node("button", "secondary", `${member.name}: Warp Wood`);
      btn.type = "button";
      btn.addEventListener("click", () =>
        advance("cast_spell", { exit_id: exit.id, character_id: member.character_id, spell_name: "Warp Wood" })
      );
      trackButton(btn);
    }
  }

  if (!addedButton) {
    appendOpenDoorAttemptButtons(row, exit, members, (member) => `${member.name}: open door`);
  }
}

function appendTravelExitButton(actions, session, exit, sideLabel) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `exit-button ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""}`;
  button.textContent = exitButtonLabel(exit, sideLabel, session);
  setButtonTooltip(button, exitTooltip(exit, session, sideLabel));
  button.addEventListener("click", () => advance("explore", { exit_id: exit.id, direction: exit.direction }));
  actions.appendChild(button);
}

function renderExitActions(session) {
  const tile = currentTile(session);
  exitActions.replaceChildren();

  const heading = node("h2", "", "Exits");
  exitActions.appendChild(heading);
  if (!tile) {
    exitActions.appendChild(node("div", "item", "Current map element is missing from session state."));
    return;
  }
  const sideLabels = exitSideLabels(tile);
  if (session.mode === "complete") {
    const summary = node("div", "list compact");
    for (const line of session.summary || ["Adventure complete."]) {
      summary.appendChild(node("div", "item", line));
    }
    exitActions.appendChild(summary);
    exitActions.appendChild(
      subline("Home roster sheets now show gold, loot, levels, and healed Life from this run.")
    );
    return;
  }

  const available = (tile.exits || []).filter((exit) => exit.status !== "blocked");
  const blocked = (tile.exits || []).filter((exit) => exit.status === "blocked");

  if (session.mode === "combat") {
    const actions = appendExitSection(exitActions, "Withdraw", "Leave combat through a door into the previous room.");
    const withdrawDoors = available.filter((exit) => exit.kind === "door" && exit.destination_tile_id);
    if (withdrawDoors.length) {
      for (const exit of withdrawDoors) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "exit-button door withdraw-door secondary";
        button.textContent = `Withdraw ${exitDisplayLabel(exit, sideLabels.get(exit.id))}`;
        setButtonTooltip(button, ACTION_TOOLTIPS.withdraw);
        button.addEventListener("click", () => advance("withdraw", { exit_id: exit.id }));
        actions.appendChild(button);
      }
    } else {
      actions.appendChild(subline("No door leads back for a withdrawal."));
    }
    const dungeonExits = available.filter((exit) => exit.dungeon_exit);
    if (dungeonExits.length) {
      const leaveActions = appendExitSection(
        exitActions,
        "Leave dungeon",
        "Flee contact first if foes are present, then exit the adventure."
      );
      for (const exit of dungeonExits) {
        appendTravelExitButton(leaveActions, session, exit, sideLabels.get(exit.id));
      }
    }
    return;
  }

  const closedDoors = available.filter((exit) => exit.kind === "door" && !exit.door_open);
  const travelExits = available.filter((exit) => !(exit.kind === "door" && !exit.door_open));
  const passages = travelExits.filter((exit) => exit.kind === "passage");
  const openDoors = travelExits.filter((exit) => exit.kind === "door");

  if (closedDoors.length) {
    const actions = appendExitSection(
      exitActions,
      "Doors to open",
      "Work closed doors here. Travel buttons appear below once a door is open."
    );
    for (const exit of closedDoors) {
      appendOpenDoorActions(session, exit, sideLabels.get(exit.id), actions);
    }
  }

  if (passages.length) {
    const actions = appendExitSection(exitActions, "Passages", "Move into a new or visited map element.");
    for (const exit of passages) {
      appendTravelExitButton(actions, session, exit, sideLabels.get(exit.id));
    }
  }

  if (openDoors.length) {
    const actions = appendExitSection(exitActions, "Open doors", "Go through doors that are already open.");
    for (const exit of openDoors) {
      appendTravelExitButton(actions, session, exit, sideLabels.get(exit.id));
    }
  }

  if (!closedDoors.length && !passages.length && !openDoors.length) {
    exitActions.appendChild(node("div", "item", "No available exits."));
  }

  if (blocked.length) {
    exitActions.appendChild(
      subline(`Dead ends: ${blocked.map((exit) => exitDisplayLabel(exit, sideLabels.get(exit.id))).join(", ")}`)
    );
  }
}

function exitButtonLabel(exit, sideLabel, session) {
  const kind = exit.kind[0].toUpperCase() + exit.kind.slice(1);
  const label = sideLabel || titleCase(exit.direction);
  const doorTag = exit.kind === "door" ? (exit.door_open ? " (open)" : " (closed)") : "";
  if (exit.dungeon_exit) {
    const fallen = fallenInDungeon(session).length;
    if (fallen) return `Retreat to Camp (${fallen} fallen)`;
    if (session.final_boss_defeated) return `Complete Adventure (${label})`;
    return `Leave Dungeon (${label})`;
  }
  if (session.camped_outside && exit.destination_tile_id) {
    return `Re-enter ${label}${doorTag}`;
  }
  if (exit.status === "open" && exit.destination_tile_id) {
    return `Go ${label}${doorTag}`;
  }
  if (exit.status === "open") {
    return `Follow ${label} ${kind}${doorTag}`;
  }
  return `Explore ${label} ${kind}${doorTag}`;
}

function exitTooltip(exit, session, sideLabel) {
  const label = sideLabel || titleCase(exit.direction);
  if (exit.dungeon_exit) {
    const fallen = fallenInDungeon(session).length;
    if (fallen) return ACTION_TOOLTIPS.retreatCamp;
    if (session.final_boss_defeated) return ACTION_TOOLTIPS.leaveDungeonBoss;
    return ACTION_TOOLTIPS.leaveDungeon;
  }
  if (session.camped_outside && exit.destination_tile_id) {
    return ACTION_TOOLTIPS.reenterDungeon;
  }
  if (exit.kind === "door" && !exit.door_open) return ACTION_TOOLTIPS.openDoor;
  return `Move ${label} into ${exit.destination_tile_id ? "a visited" : "a new"} map element.`;
}

function exitDisplayLabel(exit, sideLabel) {
  const label = sideLabel || titleCase(exit.direction);
  if (exit.dungeon_exit) return `${label} dungeon exit`;
  return `${label} ${exit.kind}`;
}

function compactExitLabel(exit, sideLabel, onCurrentTile = false) {
  const label = sideLabel || titleCase(exit.direction);
  const compact = label
    .replace("North", "N")
    .replace("East", "E")
    .replace("South", "S")
    .replace("West", "W");
  if (exit.dungeon_exit) return `${compact}X`;
  if (exit.kind === "door" && onCurrentTile) {
    return `${compact}${exit.door_open ? "O" : "D"}`;
  }
  return compact;
}

function exitSideLabels(tile) {
  const labels = new Map();
  const counts = new Map();
  for (const exit of tile.exits || []) {
    const direction = exit.direction || "north";
    const nextCount = (counts.get(direction) || 0) + 1;
    counts.set(direction, nextCount);
    labels.set(exit.id, `${titleCase(direction)} ${nextCount}`);
  }
  return labels;
}

function titleCase(value) {
  const text = String(value || "").trim();
  if (!text) return "Unknown";
  return text[0].toUpperCase() + text.slice(1);
}

function titleFromKey(value) {
  return String(value)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function memberId(member) {
  return member.character_id || member.id;
}

const transferDialogState = {
  context: null,
  members: [],
};

function normalizeTransferMember(member) {
  return {
    id: memberId(member),
    name: member.name,
    class_name: member.class_name || "",
    inventory: [...(member.inventory || [])],
    gold: member.gold || 0,
    current_life: member.current_life ?? 1,
  };
}

function eligibleTransferMembers(members, { requireLiving = false } = {}) {
  return (members || [])
    .map(normalizeTransferMember)
    .filter((member) => !requireLiving || member.current_life > 0);
}

function memberCanGive(member) {
  return member.inventory.length > 0 || member.gold > 0;
}

function isRosterTransferContext() {
  return transferDialogState.context?.mode === "roster";
}

function maxTransferGoldAmount(fromMember, toMember) {
  if (!fromMember) return 0;
  if (isRosterTransferContext()) return fromMember.gold;
  if (!toMember) return fromMember.gold;
  return Math.min(fromMember.gold, goldCarryCapacity(toMember));
}

function selectDefaultTransferPayload(fromMember, toMember) {
  if (!fromMember || !transferDialogForm) return;
  for (const input of transferDialogForm.querySelectorAll('input[name="transfer-payload"]')) {
    input.checked = false;
  }

  const firstItem = transferItemOptions?.querySelector('input[name="transfer-payload"]:not([disabled])');
  if (firstItem) {
    firstItem.checked = true;
    return;
  }

  if (fromMember.gold > 0 && transferGoldRadio && !transferGoldRadio.disabled) {
    transferGoldRadio.checked = true;
    if (transferGoldAmount) {
      const maxGold = maxTransferGoldAmount(fromMember, toMember);
      transferGoldAmount.value = maxGold > 0 ? "1" : "0";
    }
  }
}

function refreshTransferDialog() {
  if (!transferFromSelect || !transferDialogState.context) return;
  const { requireLiving } = transferDialogState.context;
  const members = transferDialogState.members;
  const fromId = transferFromSelect.value;
  const fromMember = members.find((member) => member.id === fromId) || null;

  transferPayloadStep?.classList.toggle("hidden", !fromMember);
  transferToStep?.classList.toggle("hidden", !fromMember);
  transferItemOptions?.replaceChildren();

  if (!fromMember) {
    if (transferToSelect) transferToSelect.replaceChildren();
    if (transferGoldRadio) transferGoldRadio.checked = false;
    if (transferGoldAmount) {
      transferGoldAmount.value = "1";
      transferGoldAmount.disabled = true;
    }
    updateTransferConfirmState();
    return;
  }

  if (transferToSelect) {
    transferToSelect.replaceChildren();
    const targets = members.filter((member) => member.id !== fromId);
    for (const target of targets) {
      const option = document.createElement("option");
      option.value = target.id;
      option.textContent = target.name;
      transferToSelect.appendChild(option);
    }
    if (targets.length && !targets.some((target) => target.id === transferToSelect.value)) {
      transferToSelect.value = targets[0].id;
    }
  }

  const toMember = members.find((member) => member.id === transferToSelect?.value) || null;
  const hasItems = fromMember.inventory.length > 0;
  if (transferItemOptions) {
    transferItemOptions.replaceChildren();
    if (!hasItems) {
      transferItemOptions.appendChild(node("div", "item muted", "No inventory items."));
    } else {
      fromMember.inventory.forEach((itemName, index) => {
        const label = document.createElement("label");
        label.className = "transfer-item-option";
        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = "transfer-payload";
        radio.value = `item:${index}`;
        const blocked = toMember && !canMemberReceiveItem(toMember, itemName);
        radio.disabled = blocked;
        radio.addEventListener("change", updateTransferConfirmState);
        label.append(radio, document.createTextNode(blocked ? `${itemName} (recipient full)` : itemName));
        transferItemOptions.appendChild(label);
      });
    }
  }

  if (transferGoldRadio) {
    transferGoldRadio.disabled = fromMember.gold <= 0;
  }
  const maxGold = maxTransferGoldAmount(fromMember, toMember);
  if (transferGoldAmount) {
    transferGoldAmount.max = String(Math.max(maxGold, 1));
    transferGoldAmount.value = maxGold > 0 ? "1" : "0";
    transferGoldAmount.disabled = maxGold <= 0 || !transferGoldRadio?.checked;
  }

  selectDefaultTransferPayload(fromMember, toMember);
  updateTransferConfirmState();
}

function selectedTransferPayload(fromMember) {
  if (!fromMember) return null;
  const toMember = transferDialogState.members.find((member) => member.id === transferToSelect?.value) || null;
  const checked = transferDialogForm?.querySelector('input[name="transfer-payload"]:checked');
  if (checked?.value?.startsWith("item:")) {
    const index = Number.parseInt(checked.value.slice(5), 10);
    const itemName = fromMember.inventory[index];
    if (!itemName || !toMember || !canMemberReceiveItem(toMember, itemName)) return null;
    return { item_name: itemName };
  }
  if (transferGoldRadio?.checked) {
    const amount = Number.parseInt(transferGoldAmount?.value || "0", 10);
    if (!Number.isFinite(amount) || amount <= 0) return null;
    const maxAmount = maxTransferGoldAmount(fromMember, toMember);
    if (maxAmount <= 0) return null;
    return { gold_amount: Math.min(amount, maxAmount) };
  }
  return null;
}

function updateTransferConfirmState() {
  if (!transferConfirmBtn || !transferFromSelect) return;
  const fromMember = transferDialogState.members.find((member) => member.id === transferFromSelect.value) || null;
  const toMember = transferDialogState.members.find((member) => member.id === transferToSelect?.value) || null;
  const payload = selectedTransferPayload(fromMember);
  const hasTarget = Boolean(transferToSelect?.value);
  transferConfirmBtn.disabled = !(fromMember && payload && hasTarget);
  if (transferGoldAmount && transferGoldRadio) {
    transferGoldAmount.disabled =
      !transferGoldRadio.checked || maxTransferGoldAmount(fromMember, toMember) <= 0;
  }
}

function openTransferDialog(context) {
  if (!transferDialog || !transferFromSelect) return;
  const members = eligibleTransferMembers(context.members, { requireLiving: context.requireLiving });
  if (members.length < 2) {
    setStatus(context.requireLiving ? "Need at least two living heroes to transfer gear." : "Need at least two heroes to transfer gear.");
    return;
  }
  const givers = members.filter(memberCanGive);
  if (!givers.length) {
    setStatus("No hero has items or gold to transfer.");
    return;
  }

  transferDialogState.context = context;
  transferDialogState.members = members;
  if (transferDialogNote) {
    transferDialogNote.textContent = context.note || "";
  }

  transferFromSelect.replaceChildren();
  for (const member of members) {
    const option = document.createElement("option");
    option.value = member.id;
    const suffix = memberCanGive(member) ? "" : " (nothing to give)";
    option.textContent = `${member.name}${suffix}`;
    option.disabled = !memberCanGive(member);
    transferFromSelect.appendChild(option);
  }
  const firstGiver = givers[0];
  transferFromSelect.value = firstGiver.id;

  refreshTransferDialog();
  transferDialog.showModal();
}

async function confirmTransferDialog() {
  const context = transferDialogState.context;
  if (!context || !transferFromSelect || !transferToSelect) return;
  const fromId = transferFromSelect.value;
  const toId = transferToSelect.value;
  const fromMember = transferDialogState.members.find((member) => member.id === fromId);
  const payload = selectedTransferPayload(fromMember);
  if (!fromId || !toId || !payload) return;

  transferConfirmBtn.disabled = true;
  try {
    let ok = false;
    if (context.mode === "session") {
      const action = payload.item_name ? "transfer_item" : "transfer_gold";
      ok = await advance(action, {
        character_id: fromId,
        target_character_id: toId,
        ...payload,
      });
    } else {
      await transferCharacter(fromId, { target_character_id: toId, ...payload }, { skipRender: false });
      ok = true;
    }
    if (ok) {
      transferDialog.close();
      transferDialogState.context = null;
      transferDialogState.members = [];
    }
  } catch (error) {
    handleError(error);
  } finally {
    updateTransferConfirmState();
  }
}

function openSetupTransferDialog() {
  openTransferDialog({
    mode: "roster",
    members: state.characters,
    requireLiving: false,
    note: "Transfer between any heroes on your roster.",
  });
}

function openSessionTransferDialog() {
  if (!state.session || state.session.mode !== "exploration") return;
  openTransferDialog({
    mode: "session",
    members: state.session.party,
    requireLiving: true,
    note: "Transfer between living party members (exploration only).",
  });
}

function leadMemberId(session) {
  const living = session.party.filter((member) => member.current_life > 0);
  if (!living.length) return null;
  return [...living].sort((left, right) => left.marching_order - right.marching_order)[0].character_id;
}

function canEditWeaponDefaults(member) {
  return memberMeleeWeapons(member).length > 0 || memberMissileWeapons(member).length > 0;
}

function appendWeaponPickerButton(item, session, member) {
  const inExploration = session.mode === "exploration" && member.current_life > 0;
  const wielded = session.wielded_melee_weapons?.[member.character_id];
  const drawOptions =
    session.mode === "combat" && member.current_life > 0
      ? memberMeleeWeapons(member).filter((weapon) => weapon !== wielded)
      : [];

  if (inExploration && canEditWeaponDefaults(member)) {
    const button = node("button", "secondary", "Weapon defaults");
    button.type = "button";
    setButtonTooltip(button, ACTION_TOOLTIPS.weaponDefaults);
    button.addEventListener("click", () =>
      openWeaponPickerDialog({ mode: "defaults", source: "session", member, session })
    );
    item.appendChild(button);
  } else if (drawOptions.length) {
    const button = node("button", "secondary", "Draw weapon");
    button.type = "button";
    setButtonTooltip(button, ACTION_TOOLTIPS.drawWeapon);
    button.addEventListener("click", () =>
      openWeaponPickerDialog({ mode: "draw", source: "session", member, session })
    );
    item.appendChild(button);
  }
}

const weaponPickerDialogState = {
  mode: null,
  source: null,
  member: null,
  session: null,
};

function fillWeaponSelect(select, options, selectedValue) {
  if (!select) return;
  select.replaceChildren();
  for (const weapon of options) {
    const option = document.createElement("option");
    option.value = weapon;
    option.textContent = weapon;
    select.appendChild(option);
  }
  if (selectedValue && options.includes(selectedValue)) {
    select.value = selectedValue;
  } else if (options.length) {
    select.value = options[0];
  }
}

function openWeaponPickerDialog({ mode, source = "session", member, session = null }) {
  if (!weaponPickerDialog || !member) return;
  weaponPickerDialogState.mode = mode;
  weaponPickerDialogState.source = source;
  weaponPickerDialogState.member = member;
  weaponPickerDialogState.session = session;

  if (mode === "defaults") {
    if (weaponPickerTitle) weaponPickerTitle.textContent = `Weapon defaults — ${member.name}`;
    if (weaponPickerNote) {
      weaponPickerNote.textContent =
        source === "roster"
          ? "Saved on this hero's roster. New adventures use these defaults when a fight starts."
          : "Defaults are noted on the hero sheet and used when a fight starts. Change them during exploration only.";
    }
    weaponPickerDefaultsStep?.classList.remove("hidden");
    weaponPickerDrawStep?.classList.add("hidden");
    const meleeOptions = memberMeleeWeapons(member);
    const missileOptions = memberMissileWeapons(member);
    fillWeaponSelect(weaponPickerMeleeSelect, meleeOptions, member.default_melee_weapon);
    fillWeaponSelect(weaponPickerMissileSelect, missileOptions, member.default_missile_weapon);
    document.getElementById("weapon-picker-melee-step")?.classList.toggle("hidden", !meleeOptions.length);
    document.getElementById("weapon-picker-missile-step")?.classList.toggle("hidden", !missileOptions.length);
    if (weaponPickerConfirmBtn) weaponPickerConfirmBtn.textContent = "Save defaults";
  } else {
    const wielded = session.wielded_melee_weapons?.[member.character_id];
    const drawOptions = memberMeleeWeapons(member).filter((weapon) => weapon !== wielded);
    if (!drawOptions.length) return;
    if (weaponPickerTitle) weaponPickerTitle.textContent = `Draw weapon — ${member.name}`;
    if (weaponPickerNote) {
      weaponPickerNote.textContent = wielded
        ? `Currently wielding ${wielded}. Drawing another weapon costs this hero's turn.`
        : "Choose a melee weapon to wield for the rest of this fight.";
    }
    weaponPickerDefaultsStep?.classList.add("hidden");
    weaponPickerDrawStep?.classList.remove("hidden");
    fillWeaponSelect(weaponPickerDrawSelect, drawOptions, drawOptions[0]);
    if (weaponPickerConfirmBtn) weaponPickerConfirmBtn.textContent = "Draw weapon";
  }

  weaponPickerDialog.showModal();
}

async function confirmWeaponPickerDialog() {
  const { mode, source, member } = weaponPickerDialogState;
  if (!member || !mode) return;
  weaponPickerConfirmBtn.disabled = true;
  try {
    if (mode === "defaults") {
      const updates = [];
      const payload = {};
      const melee = weaponPickerMeleeSelect?.value;
      const missile = weaponPickerMissileSelect?.value;
      if (melee && melee !== member.default_melee_weapon) {
        updates.push({ weapon_kind: "melee", item_name: melee });
        payload.default_melee_weapon = melee;
      }
      if (missile && missile !== member.default_missile_weapon) {
        updates.push({ weapon_kind: "missile", item_name: missile });
        payload.default_missile_weapon = missile;
      }
      if (!updates.length) {
        weaponPickerDialog.close();
        return;
      }
      if (source === "roster") {
        await saveCharacterWeaponDefaults(member.id, payload);
      } else {
        for (const item of updates) {
          const ok = await advance("set_default_weapon", {
            character_id: member.character_id,
            ...item,
          });
          if (!ok) return;
        }
      }
    } else {
      const weapon = weaponPickerDrawSelect?.value;
      if (!weapon) return;
      const ok = await advance("swap_weapon", {
        character_id: member.character_id,
        item_name: weapon,
      });
      if (!ok) return;
    }
    weaponPickerDialog.close();
  } catch (error) {
    handleError(error);
  } finally {
    weaponPickerConfirmBtn.disabled = false;
  }
}

function renderPartyState(session) {
  partyState.replaceChildren();
  const members = session.party || [];
  if (!members.length) {
    partyState.appendChild(node("div", "item", "No party members in this session."));
    return;
  }
  const ordered = [...members].sort((left, right) => left.marching_order - right.marching_order);
  const canReorder = session.mode === "exploration";
  for (const member of ordered) {
    const item = node("div", "item");
    const header = node("div", "marching-order-row");
    header.appendChild(node("span", "position", `#${member.marching_order}`));
    header.appendChild(node("span", "name", `${member.name} - ${member.class_name}`));
    if (canReorder && member.current_life > 0) {
      const actions = node("div", "marching-order-actions");
      const up = node("button", "secondary", "↑");
      up.type = "button";
      up.disabled = member.marching_order <= 1;
      setButtonTooltip(up, "Move this hero one step forward in marching order (position 1 leads).");
      up.addEventListener("click", () =>
        advance("set_marching_order", {
          character_id: member.character_id,
          marching_order: member.marching_order - 1,
        })
      );
      const down = node("button", "secondary", "↓");
      down.type = "button";
      down.disabled = member.marching_order >= 4;
      setButtonTooltip(down, "Move this hero one step back in marching order (position 4 is rear).");
      down.addEventListener("click", () =>
        advance("set_marching_order", {
          character_id: member.character_id,
          marching_order: member.marching_order + 1,
        })
      );
      actions.append(up, down);
      header.appendChild(actions);
    }
    item.appendChild(header);
    item.appendChild(subline(`HP ${member.current_life}/${member.max_life} | Gold ${member.gold} | XP ${member.xp} | L${member.level}`));
    item.appendChild(subline(carryLimitsLine(member)));
    if (isOverEncumbered(member)) {
      item.appendChild(subline("Over encumbered (−1 Defense and physical Saves)."));
    }
    const wielded = session.wielded_melee_weapons?.[member.character_id];
    const meleeDefault = member.default_melee_weapon || "none";
    const missileDefault = member.default_missile_weapon || "none";
    item.appendChild(
      subline(
        session.mode === "combat" && wielded
          ? `Wielding ${wielded} | Sheet defaults: melee ${meleeDefault}, missile ${missileDefault}`
          : `Sheet defaults: melee ${meleeDefault}, missile ${missileDefault}`
      )
    );
    appendWeaponPickerButton(item, session, member);
    const xpSystem = session.xp_system || "classical";
    const spellPickPending = Boolean(session.level_up_spell_pending_character_id);
    if (
      canReorder &&
      member.current_life > 0 &&
      xpSystem === "classical" &&
      (session.xp_rolls_pending || 0) > 0 &&
      !spellPickPending
    ) {
      const xpBtn = node("button", "secondary", "Spend XP Roll");
      xpBtn.type = "button";
      setButtonTooltip(xpBtn, ACTION_TOOLTIPS.xpRoll);
      xpBtn.addEventListener("click", () => advance("xp_roll", { character_id: member.character_id }));
      item.appendChild(xpBtn);
    }
    if (canReorder && member.current_life > 0 && xpSystem === "old_school" && !spellPickPending) {
      const xpBtn = node("button", "secondary", "Old School Level Up");
      xpBtn.type = "button";
      setButtonTooltip(xpBtn, ACTION_TOOLTIPS.oldSchoolLevelUp);
      xpBtn.addEventListener("click", () => advance("old_school_level_up", { character_id: member.character_id }));
      item.appendChild(xpBtn);
    }
    if (
      canReorder &&
      member.current_life > 0 &&
      xpSystem === "slower_advancement" &&
      (session.slower_xp_bank || 0) >= member.level + 1 &&
      !spellPickPending
    ) {
      const xpBtn = node("button", "secondary", `Spend ${member.level + 1}+ Banked XP`);
      xpBtn.type = "button";
      setButtonTooltip(xpBtn, ACTION_TOOLTIPS.slowerXpSpend);
      xpBtn.addEventListener("click", () =>
        advance("slower_xp_spend", { character_id: member.character_id, xp_spent: member.level + 1 })
      );
      item.appendChild(xpBtn);
    }
    item.appendChild(subline(`Inventory: ${formatMemberInventory(member)}`));
    if ((member.spells || []).length) {
      appendSpellSubline(item, member.spells, session, member);
    }
    if (session.level_up_spell_pending_character_id === member.character_id) {
      item.classList.add("spell-pick-pending");
      const pick = node("div", "level-up-spell-pick");
      pick.appendChild(node("strong", "", "Choose spell for new slot:"));
      const pickRow = node("div", "level-up-spell-pick-actions");
      appendLevelUpSpellPickButtons(pickRow, member);
      pick.appendChild(pickRow);
      item.appendChild(pick);
    }
    partyState.appendChild(item);
  }
}

function renderLog(session) {
  sessionLog.replaceChildren();
  for (const entry of (session.log || []).slice(-80)) {
    sessionLog.appendChild(node("div", "", entry));
  }
  sessionLog.scrollTop = sessionLog.scrollHeight;
}

function showGameView(options = {}) {
  const { rememberView = true } = options;
  setupPanel.classList.add("hidden");
  sessionPanel.classList.remove("hidden");
  showSetupBtn.classList.remove("hidden");
  saveSessionBtn.classList.remove("hidden");
  resumeSessionBtn.classList.toggle("hidden", !state.session);
  if (rememberView) writeActiveView("game");
}

function showSetupView(options = {}) {
  const { rememberView = true } = options;
  setupPanel.classList.remove("hidden");
  sessionPanel.classList.add("hidden");
  showSetupBtn.classList.add("hidden");
  saveSessionBtn.classList.add("hidden");
  resumeSessionBtn.classList.toggle("hidden", !state.session);
  if (rememberView) writeActiveView("setup");
}

characterForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("/api/characters", {
      method: "POST",
      body: JSON.stringify({
        name: characterName.value,
        class_id: characterClass.value,
      }),
    });
    characterName.value = "";
    setStatus("Character saved");
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
});

partyForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    if (state.partyMarchingIds.length !== 4) {
      setStatus("Choose exactly 4 heroes for the party.");
      return;
    }
    const character_ids = [...state.partyMarchingIds];
    const path = state.editingPartyId ? `/api/parties/${state.editingPartyId}` : "/api/parties";
    await api(path, {
      method: state.editingPartyId ? "PUT" : "POST",
      body: JSON.stringify({
        name: partyName.value,
        character_ids,
      }),
    });
    setStatus(state.editingPartyId ? "Party updated" : "Party saved");
    cancelPartyEditMode();
    await loadAll({ restoreSession: false });
  } catch (error) {
    handleError(error);
  }
});

cancelPartyEdit.addEventListener("click", cancelPartyEditMode);

characterFilterClass.addEventListener("change", () => {
  state.characterFilters.classId = characterFilterClass.value;
  renderCharacters();
});

characterFilterLevel.addEventListener("change", () => {
  state.characterFilters.level = characterFilterLevel.value;
  renderCharacters();
});

characterSort.addEventListener("change", () => {
  state.characterFilters.sort = characterSort.value;
  renderCharacters();
});

characterSortDirection.addEventListener("click", () => {
  state.characterFilters.direction = state.characterFilters.direction === "asc" ? "desc" : "asc";
  renderCharacters();
});

partyFilterClass.addEventListener("change", () => {
  state.partyFilters.classId = partyFilterClass.value;
  renderParties();
});

partyFilterLevel.addEventListener("change", () => {
  state.partyFilters.level = partyFilterLevel.value;
  renderParties();
});

partySort.addEventListener("change", () => {
  state.partyFilters.sort = partySort.value;
  renderParties();
});

partySortDirection.addEventListener("click", () => {
  state.partyFilters.direction = state.partyFilters.direction === "asc" ? "desc" : "asc";
  renderParties();
});

exportPlayerDataBtn.addEventListener("click", exportPlayerData);
importPlayerDataBtn.addEventListener("click", () => importPlayerFile.click());
importPlayerFile.addEventListener("change", () => importPlayerData(importPlayerFile.files?.[0]));

startSession.addEventListener("click", async () => {
  try {
    const party_id = partySelect.value;
    const adventure_id = adventureSelect.value || "random";
    if (!party_id) {
      setStatus("Create a party first");
      return;
    }
    state.session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({
        party_id,
        adventure_id,
        xp_system: xpSystemSelect?.value || "classical",
      }),
    });
    writeActiveSessionId(state.session.id);
    await refreshSessions();
    setStatus("Session started");
    renderSession();
  } catch (error) {
    handleError(error);
  }
});

resumeSessionBtn.addEventListener("click", () => {
  if (state.session) renderSession();
});

showSetupBtn.addEventListener("click", () => {
  showSetupView();
});

showRollsInput.addEventListener("change", () => {
  state.showRolls = showRollsInput.checked;
});

showMathInput.addEventListener("change", () => {
  state.showMath = showMathInput.checked;
});

mapZoomOut.addEventListener("click", () => setMapZoom(state.mapZoom - 0.1, { recenter: true }));
mapZoomIn.addEventListener("click", () => setMapZoom(state.mapZoom + 0.1, { recenter: true }));
mapZoomReset.addEventListener("click", () => setMapZoom(1, { recenter: true }));
mapZoomRoom.addEventListener("click", zoomToCurrentRoom);
mapZoomMap.addEventListener("click", zoomToFullMap);
mapCenterCurrent.addEventListener("click", centerCurrentTile);
mapPanUp.addEventListener("click", () => panMap(0, -160));
mapPanDown.addEventListener("click", () => panMap(0, 160));
mapPanLeft.addEventListener("click", () => panMap(-160, 0));
mapPanRight.addEventListener("click", () => panMap(160, 0));
mapViewportEl.addEventListener("wheel", handleMapWheel, { passive: false });
mapViewportEl.addEventListener("pointerdown", startMapPan);

async function reloadCharacters() {
  state.characters = await api("/api/characters");
  renderCharacters();
}

async function advance(action, extra = {}) {
  if (!state.session) return false;
  try {
    state.session = await api(`/api/sessions/${state.session.id}/advance`, {
      method: "POST",
      body: JSON.stringify({
        action,
        show_rolls: state.showRolls,
        explain_math: state.showMath,
        ...extra,
      }),
    });
    writeActiveSessionId(state.session.id);
    await refreshSessions();
    if (state.session.mode === "complete") {
      await reloadCharacters();
      setStatus("Adventure complete — character roster updated");
    } else {
      setStatus("Session updated");
    }
    renderSession();
    return true;
  } catch (error) {
    handleError(error);
    return false;
  }
}

searchBtn.addEventListener("click", () => advance("search"));
searchTreasureBtn?.addEventListener("click", () => advance("search", { search_choice: "hidden_treasure" }));
searchDoorBtn?.addEventListener("click", () => advance("search", { search_choice: "secret_door" }));
searchPassageBtn?.addEventListener("click", () => advance("search", { search_choice: "secret_passage" }));
searchClueBtn?.addEventListener("click", () => advance("search", { search_choice: "clue" }));
checkReactionBtn?.addEventListener("click", () => advance("check_reaction"));
payBribeBtn?.addEventListener("click", () => advance("pay_bribe", { pay_bribe: true }));
declineBribeBtn?.addEventListener("click", () => advance("pay_bribe", { pay_bribe: false }));
function resolveCombatRound() {
  const payload = { subdual: Boolean(subdualInput?.checked) };
  const targets = buildAttackTargetsPayload();
  if (targets) payload.attack_targets = targets;
  advance("combat_round", payload);
}

combatBtn.addEventListener("click", () => resolveCombatRound());
combatResolveBtn?.addEventListener("click", () => resolveCombatRound());
combatFleeBtn?.addEventListener("click", () => advance("flee"));
fleeBtn?.addEventListener("click", () => advance("flee"));
combatWithdrawBtn?.addEventListener("click", () => {
  const session = state.session;
  if (!session) return;
  const tile = currentTile(session);
  const door = (tile.exits || []).find((exit) => exit.kind === "door" && exit.destination_tile_id);
  if (door) advance("withdraw", { exit_id: door.id });
});
withdrawBtn?.addEventListener("click", () => {
  const session = state.session;
  if (!session) return;
  const tile = currentTile(session);
  const door = (tile.exits || []).find((exit) => exit.kind === "door" && exit.destination_tile_id);
  if (door) advance("withdraw", { exit_id: door.id });
});
resolveTrapBtn.addEventListener("click", () => advance("resolve_trap"));
claimTreasureBtn.addEventListener("click", () => advance("claim_treasure"));
restBtn.addEventListener("click", () => advance("rest"));
saveSessionBtn.addEventListener("click", async () => {
  if (!state.session) return;
  try {
    state.session = await api(`/api/sessions/${state.session.id}/save`, { method: "POST" });
    writeActiveSessionId(state.session.id);
    await refreshSessions();
    renderSession();
    setStatus("Game saved to server");
  } catch (error) {
    handleError(error);
  }
});

transferFromSelect?.addEventListener("change", refreshTransferDialog);
transferToSelect?.addEventListener("change", () => {
  refreshTransferDialog();
});
transferGoldRadio?.addEventListener("change", updateTransferConfirmState);
transferGoldAmount?.addEventListener("input", updateTransferConfirmState);
transferConfirmBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  confirmTransferDialog();
});
transferItemsSetupBtn?.addEventListener("click", openSetupTransferDialog);
equipmentShopSetupBtn?.addEventListener("click", () => openEquipmentShopDialog());
equipmentShopCharacterSelect?.addEventListener("change", () => refreshEquipmentShopDialog());
equipmentShopBuyTab?.addEventListener("click", () => setEquipmentShopTab("buy"));
equipmentShopSellTab?.addEventListener("click", () => setEquipmentShopTab("sell"));
equipmentShopSellItem?.addEventListener("change", () => {
  refreshEquipmentShopSellQuote();
  updateEquipmentShopConfirmState();
});
equipmentShopConfirmBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  confirmEquipmentShopDialog();
});
equipmentShopDialogForm?.addEventListener("close", () => {
  equipmentShopDialogState.selectedBuyKey = null;
  equipmentShopDialogState.catalog = null;
});
transferItemsSessionBtn?.addEventListener("click", openSessionTransferDialog);
transferDialogForm?.addEventListener("close", () => {
  transferDialogState.context = null;
  transferDialogState.members = [];
});
weaponPickerConfirmBtn?.addEventListener("click", (event) => {
  event.preventDefault();
  confirmWeaponPickerDialog();
});
weaponPickerDialogForm?.addEventListener("close", () => {
  weaponPickerDialogState.mode = null;
  weaponPickerDialogState.source = null;
  weaponPickerDialogState.member = null;
  weaponPickerDialogState.session = null;
});
setButtonTooltip(transferItemsSetupBtn, SETUP_TOOLTIPS.transferItems);
setButtonTooltip(transferItemsSessionBtn, ACTION_TOOLTIPS.transferItems);

loadAll();
