const state = {
  classes: [],
  characters: [],
  parties: [],
  adventures: [],
  rulesTables: {},
  expertSkillsCatalog: null,
  icons: [],
  sessions: [],
  session: null,
  selectedCharacterId: null,
  selectedPartyId: null,
  editingPartyId: null,
  partySlotIds: [null, null, null, null],
  partyDragCharacterId: null,
  characterFilters: { classId: "all", level: "all", availability: "all", sort: "name", direction: "asc" },
  partyFilters: { classId: "all", level: "all", sort: "name", direction: "asc" },
  logMode: "summary",
  showRolls: false,
  showMath: false,
  mapZoom: 1,
  mapFocusedTileId: null,
  lastCenteredTileId: null,
  combatTargets: {},
  spellAimModes: {},
  spellFoeTargets: {},
  abilityFoeTargets: {},
  abilityAllyTargets: {},
  combatSecondaryTargets: {},
  doubleKickTargets: {},
  protectiveIncenseTargets: {},
  spellSecondaryFoeTargets: {},
  combatAbilities: {},
  rulesReference: [],
  mapElementDefinitions: [],
  allySpellTargets: {},
  spellLifeTransfer: {},
  teleportTileId: {},
  teleportAllies: {},
  combatPanelKey: null,
  combatWithdrawExitId: null,
  mapRoomOpen: false,
  mapIconKeyOpen: false,
  mapExitsOpen: false,
  partyRegroupOpen: false,
  partySheetOpen: {},
  logPanelHeight: 240,
  mapStageHeight: null,
  sidePanelWidth: 420,
  exitsPanelWidth: 280,
  mapPanX: 0,
  mapPanY: 0,
  mapViewRevision: 0,
  mapSuppressClick: false,
  combatCinema: false,
  combatCommandTab: "exits",
  combatRailHeight: 108,
  combatSideRailWidth: 340,
  combatHeroDrawerHeight: 240,
  combatHeroDrawerId: null,
  mapStageHeightBeforeCinema: null,
  mapStageHeightBeforeCombat: null,
  lastCombatRoundSeen: 0,
  selectedCreateClassId: null,
};

let combatRoundToastTimer = null;

const ACTIVE_SESSION_KEY = "ahazi-against-darkness.active-session-id";
const ACTIVE_VIEW_KEY = "ahazi-against-darkness.active-view";
const LAYOUT_STORAGE_KEY = "ahazi-against-darkness.layout";
const SVG_NS = "http://www.w3.org/2000/svg";
const LAYOUT_DEFAULTS = {
  logPanelHeight: 240,
  mapStageHeight: null,
  sidePanelWidth: 420,
  exitsPanelWidth: 280,
  logMode: "summary",
  mapExitsOpen: false,
  partyRegroupOpen: false,
  combatRailHeight: 108,
  combatSideRailWidth: 340,
  combatHeroDrawerHeight: 240,
};
const WINDOW_SESSION_PREFIX = "ahazi-active-session:";
let mapClipSequence = 0;

const apiStatus = document.getElementById("api-status");
const characterClass = document.getElementById("character-class");
const classPickerEl = document.getElementById("class-picker");
const classDetailEl = document.getElementById("class-detail");
const characterForm = document.getElementById("character-form");
const characterName = document.getElementById("character-name");
const characterCount = document.getElementById("character-count");
const charactersEl = document.getElementById("characters");
const characterFilterClass = document.getElementById("character-filter-class");
const characterFilterLevel = document.getElementById("character-filter-level");
const characterFilterAvailability = document.getElementById("character-filter-availability");
const characterSort = document.getElementById("character-sort");
const characterSortDirection = document.getElementById("character-sort-direction");
const partyForm = document.getElementById("party-form");
const partySlotsEl = document.getElementById("party-slots");
const partyName = document.getElementById("party-name");
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
const rulesReferenceSearchEl = document.getElementById("rules-reference-search");
const rulesReferenceCategoryEl = document.getElementById("rules-reference-category");
const rulesReferenceStatusEl = document.getElementById("rules-reference-status");
const rulesReferenceResultsEl = document.getElementById("rules-reference-results");

const REFERENCE_STATUS_LABELS = {
  implemented: "Implemented",
  partial: "Partial",
  planned: "Planned",
  not_in_app: "Not in app",
};
const exportPlayerDataBtn = document.getElementById("export-player-data");
const importPlayerDataBtn = document.getElementById("import-player-data");
const importPlayerFile = document.getElementById("import-player-file");
const setupPanel = document.getElementById("setup-panel");
const saveCount = document.getElementById("save-count");
const savedGamesEl = document.getElementById("saved-games");
const activeGamesEl = document.getElementById("active-games");
const activeGameCount = document.getElementById("active-game-count");
const startSession = document.getElementById("start-session");
const resumeSessionBtn = document.getElementById("resume-session");
const sessionPanel = document.getElementById("session-panel");
const sessionMain = document.getElementById("session-main");
const showSetupBtn = document.getElementById("show-setup");
const sessionMode = document.getElementById("session-mode");
const mapViewportEl = document.getElementById("map-viewport");
const mapEl = document.getElementById("map");
const MAP_BASE_CELL = 116;
const MAP_MIN_ZOOM = 0.08;
const MAP_MAX_ZOOM = 2.5;
const MAP_RENDER_PAD = 3;
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
const mapExitsPanel = document.getElementById("map-exits-panel");
const combatMinimapEl = document.getElementById("combat-minimap");
const combatPartyStripEl = document.getElementById("combat-party-strip");
const combatCommandRailEl = document.getElementById("combat-command-rail");
const combatCommandRailResizerEl = document.getElementById("combat-command-rail-resizer");
const combatSideRailEl = document.getElementById("combat-side-rail");
const combatSideRailResizerEl = document.getElementById("combat-side-rail-resizer");
const combatStageColumnEl = document.getElementById("combat-stage-column");
const combatRailExitsEl = document.getElementById("combat-rail-exits");
const combatRailEncounterEl = document.getElementById("combat-rail-encounter");
const combatRailLogEl = document.getElementById("combat-rail-log");
const combatTabExitsBadgeEl = document.getElementById("combat-tab-exits-badge");
const combatCinemaToggleRailBtn = document.getElementById("combat-cinema-toggle-rail");
const combatCinemaToggleTacticalBtn = document.getElementById("combat-cinema-toggle-tactical");
const tacticalRoomViewportEl = document.getElementById("tactical-room-viewport");
const tacticalRoomEl = document.getElementById("tactical-room");
const combatHeroChipsEl = document.getElementById("combat-hero-chips");
const combatHeroDrawerEl = document.getElementById("combat-hero-drawer");
const combatHeroDrawerResizerEl = document.getElementById("combat-hero-drawer-resizer");
const combatDeckSlimEl = document.getElementById("combat-deck-slim");
const combatFloatDeckEl = document.getElementById("combat-float-deck");
const combatCinemaToggleBtn = document.getElementById("combat-cinema-toggle");
const combatRoundToastEl = document.getElementById("combat-round-toast");
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
const weaponPickerMeleeSecondarySelect = document.getElementById("weapon-picker-melee-secondary");
const weaponPickerMissileSelect = document.getElementById("weapon-picker-missile");
const weaponPickerDrawSelect = document.getElementById("weapon-picker-draw");
const weaponPickerConfirmBtn = document.getElementById("weapon-picker-confirm");
const sessionLog = document.getElementById("session-log");
const mapLogPanel = document.getElementById("map-log-panel");
const mapLogRow = document.getElementById("map-log-row");
const mapStageWrap = document.getElementById("map-stage-wrap");
const mapEncounterBannerEl = document.getElementById("map-encounter-banner");
const logMapResizer = document.getElementById("log-map-resizer");
const logExitsResizer = document.getElementById("log-exits-resizer");
const mapBottomResizer = document.getElementById("map-bottom-resizer");
const sessionColumnResizer = document.getElementById("session-column-resizer");
const pendingXpBanner = document.getElementById("pending-xp-banner");
const armoryChoicesEl = document.getElementById("armory-choices");
const searchBtn = document.getElementById("search");
const searchChoicesEl = document.getElementById("search-choices");
const searchTreasureBtn = document.getElementById("search-treasure");
const searchDoorBtn = document.getElementById("search-door");
const searchPassageBtn = document.getElementById("search-passage");
const searchClueBtn = document.getElementById("search-clue");
const searchClueHolderSelect = document.getElementById("search-clue-holder");
const searchChoicesHelp = document.getElementById("search-choices-help");
const clueChoicesEl = document.getElementById("clue-choices");
const reactionChoicesEl = document.getElementById("reaction-choices");
const checkReactionBtn = document.getElementById("check-reaction");
const combatStatusEl = document.getElementById("combat-status");
const payBribeBtn = document.getElementById("pay-bribe");
const declineBribeBtn = document.getElementById("decline-bribe");
const tradeInfoSellBtn = document.getElementById("trade-info-sell");
const tradeInfoBuyBtn = document.getElementById("trade-info-buy");
const tradeInfoDeclineBtn = document.getElementById("trade-info-decline");
const spellChoicesEl = document.getElementById("spell-choices");
const levelUpSpellChoicesEl = document.getElementById("level-up-spell-choices");
const economyChoicesEl = document.getElementById("economy-choices");
const questChoicesEl = document.getElementById("quest-choices");
const ongoingQuestsEl = document.getElementById("ongoing-quests");
const potionChoicesEl = document.getElementById("potion-choices");
const recoveryChoicesEl = document.getElementById("recovery-choices");
const combatPanelEl = document.getElementById("combat-panel");
const combatPanelTitleEl = document.getElementById("combat-panel-title");
const combatPanelStatusEl = document.getElementById("combat-panel-status");
const combatPreviewEl = document.getElementById("combat-preview");
const combatFoesEl = document.getElementById("combat-foes");
const combatHeroesEl = document.getElementById("combat-heroes");
const combatStartBtn = document.getElementById("combat-start");
const combatResolveBtn = document.getElementById("combat-resolve");
const combatFleeBtn = document.getElementById("combat-flee");
const combatFleeLuckBtn = document.getElementById("combat-flee-luck");
const combatWithdrawBtn = document.getElementById("combat-withdraw");
const xpSystemSelect = document.getElementById("xp-system-select");
const mapBoundsSelect = document.getElementById("map-bounds-select");
const combatBtn = document.getElementById("combat-round");
const startCombatBtn = document.getElementById("start-combat");
const encounterHintEl = document.getElementById("encounter-hint");
const subdualInput = document.getElementById("subdual-damage");
const subdualLabel = document.getElementById("subdual-label");
const fleeBtn = document.getElementById("flee");
const withdrawBtn = document.getElementById("withdraw");
const resolveTrapBtn = document.getElementById("resolve-trap");
const claimTreasureBtn = document.getElementById("claim-treasure");
const restBtn = document.getElementById("rest");
const restChoicesEl = document.getElementById("rest-choices");
const saveSessionBtn = document.getElementById("save-session");
const logModeSummaryBtn = document.getElementById("log-mode-summary");
const logModeVerboseBtn = document.getElementById("log-mode-verbose");
saveSessionBtn.disabled = true;

const ACTION_TOOLTIPS = {
  search: "Search the current room once (d6; corridors -1). May find treasure, a secret, a clue, or wandering monsters.",
  searchTreasure: "After Search finds something (d6 5–6), choose hidden treasure.",
  searchDoor: "After Search finds something, choose a secret door on this tile.",
  searchPassage: "After Search finds something, choose a secret passage.",
  searchClue: "After Search finds something, choose 1 new Clue. Clues are not spent unless you deliberately spend them.",
  revealSecretWithClues: "Spend 3 held Clues to reveal a Secret and gain the appropriate XP reward for the campaign mode.",
  learnSpellWithClues:
    "Spend 3 held Clues to learn an eligible expert spell. Currently wired for the expert spell catalog; druid expert spells need their own catalog.",
  checkReaction:
    "Roll d6 on the foe Reaction table before party actions (p.146). If the result is hostile, foes may strike first and the party loses the opening volley.",
  payBribe: "Pay the demanded bribe to end the encounter peacefully (uses weapons first, then gold).",
  declineBribe: "Refuse the bribe; the foes attack (usually striking first).",
  tradeInfoSell: "Trade shared information for 25gp per held Clue. The Clues are not spent.",
  tradeInfoBuy: "Pay 100gp to buy 1 Clue from the encountered creatures.",
  tradeInfoDecline: "Refuse the information trade; the foes attack.",
  startCombat:
    "Enter the encounter state for older saved games. Strict p.146 play starts this automatically when living foes are present.",
  combatRound:
    "Fight Round: choose immediate attack if Reactions are unresolved (p.146), then resolve melee/missiles and surviving foe attacks. Pick targets first.",
  flee: "Flee during combat (p.97): the party runs from melee and living foes may get parting strikes.",
  withdraw: "Withdraw through a door to a visited tile (p.97): foes strike as you pull back, then remain behind if you survive.",
  resolveTrap:
    "Disarm the trap on this tile (rogue first, then gnome gadget or trap table). Room trap-treasure may roll empty on the treasure table — the log states what was found when you entered.",
  claimTreasure: "Split gold and assign items from treasure here among surviving heroes.",
  rest:
    "Rulebook Rest (p.114, once/adventure): cleared room + cleared adjacent tiles, optional nail doors (1 bag of nails per door, 4gp). Each hero recovers 1 Life or 1 spent ability, then roll 1-in-6 for Wandering Monsters.",
  saveSession: "Save this session to the server so you can resume it later from the home screen.",
  logSummary: "Summary log: show outcomes without roll, lookup, or math detail.",
  logVerbose: "Verbose log: include rolls, table lookups, and modifier math.",
  usePotion:
    "Drink a Potion of Healing: restore all lost Life. Once per hero per adventure; free action even in combat. Barbarians cannot use potions — transfer to an ally.",
  useHolyWater:
    "Throw holy water at an undead foe (p.110). Uses your combat target; consumes the vial. Counts as attacking (skips Reactions). Barbarians cannot use holy water.",
  useLanternOil:
    "Splash lantern oil on a regenerating foe and ignite it (p.99). 1 Life on hit; blocks regeneration that round. Uses combat target; consumes the flask. Counts as attacking.",
  useBandage:
    "Apply a bandage to yourself or a wounded ally: restore 1 Life. Once per hero per adventure; exploration only (p.89). Kuklas cannot use or receive bandages.",
  acceptQuest: "Accept the Lady in White's mission and roll on the Quest Table.",
  refuseQuest: "Decline the quest; the Lady in White will not appear again this adventure.",
  claimQuestReward: "Turn in a completed quest and roll on the Epic Rewards Table.",
  buyHealing: "Pay 10gp to restore 1 Life while the wandering healer is on this tile.",
  buyPotion: "Pay 50gp for a Potion of Healing added to this hero (once per hero per adventure).",
  buyPoison: "Pay 30gp for blade poison added to this hero (once per hero per adventure).",
  xpRoll:
    "Spend 1 pending XP roll. Basic heroes roll d6 to level up. Expert-trained heroes may choose Level up or Learn expert skill/spell; tier dice apply (d8+2 … d20+10).",
  learnExpertSkill:
    "Spend 1 pending XP roll to attempt learning an expert skill or spell instead of gaining a Level. Requires Expert tier training first.",
  enterExpertTier:
    "Enter Expert tier between adventures: 500 gp from the party, or 1 banked XP roll instead of gold. Required before Level 6, Expert dice, or Expert skill/spell learning; learning a skill later uses a separate advancement roll.",
  enterHeroicTier:
    "Heroic training (L9+): 1000 gp + 2 banked XP rolls per hero. Required before Level 10.",
  enterLegendaryTier:
    "Legendary training (L14+): 2000 gp + 3 banked XP rolls per hero. Required before Level 15.",
  pickLevelUpSpell: "Choose a spell from your class list to fill the new spell slot gained at this Level.",
  oldSchoolLevelUp: "Spend (Tier+2)×100 Old School XP to gain 1 Level.",
  slowerXpSpend: "Spend banked XP equal to target Level (plus extra for +1 on the roll) to attempt advancement.",
  transferItems: "Move items or gold between living party members (exploration only).",
  weaponDefaults:
    "Equipment slots — set default melee and missile weapons for this hero (exploration only). Used when a fight starts.",
  drawWeapon:
    "Change wielded melee weapon (costs your turn in combat; foes attack after you draw, p.94).",
  openDoor: "Attempt to open a closed door (2d6 on the door table). Must open before moving through.",
  reenterDungeon: "Leave camp and explore back into the persisted dungeon map.",
  retreatCamp:
    "Fallen heroes remain inside. Retreat to camp outside—the dungeon map persists so you can regroup and return. Unattended bodies risk 5-in-6 loot theft.",
  leaveDungeon:
    "No fallen remain inside. Leave to end the adventure; surviving heroes fully heal between adventures.",
  leaveDungeonBoss:
    "Final Boss slain and no fallen remain inside. Leave to complete the adventure.",
};

const CAMPAIGN_MODE_LABELS = {
  classical: "Classical",
  slow_and_sure: "Slow and Sure",
  old_school: "Old School",
  slower_advancement: "Slower Advancement",
};

function campaignModeLabel(mode) {
  return CAMPAIGN_MODE_LABELS[mode] || (mode || "classical").replace(/_/g, " ");
}

const CLASS_SKILL_CODES = {
  warrior: ["W"],
  barbarian: ["B"],
  cleric: ["C"],
  rogue: ["R"],
  wizard: ["Wi"],
  elf: ["E"],
  dwarf: ["D"],
  halfling: ["H"],
  swashbuckler: ["S"],
  paladin: ["C", "W"],
  druid: ["Wi", "C"],
  illusionist: ["Wi"],
  assassin: ["R"],
  acrobat: ["H", "E"],
  bulwark: ["W", "D"],
  gnome: ["H", "Wi"],
  kukla: ["H"],
  mushroom_monk: ["H", "B"],
  ranger: ["E", "H", "R"],
  light_gladiator: ["W", "B"],
};

function learnedHeroicSkillIds(member) {
  return new Set((member.learned_heroic_skills || []).map((item) => String(item).toLowerCase().split(":")[0]));
}

function learnedLegendarySkillIds(member) {
  return new Set((member.learned_legendary_skills || []).map((item) => String(item).toLowerCase().split(":")[0]));
}

function detachedElsewhereIds(session, tileId) {
  const active = tileId || session.map_state?.current_tile_id;
  const ids = new Set();
  for (const group of session.detached_groups || []) {
    if (group.tile_id !== active) {
      for (const id of group.character_ids || []) ids.add(id);
    }
  }
  return ids;
}

function detachedGroupsOnTile(session, tileId) {
  return (session.detached_groups || []).filter((group) => group.tile_id === tileId);
}

function detachedHeroNames(session, characterIds) {
  return (characterIds || [])
    .map((id) => (session.party || []).find((member) => member.character_id === id)?.name)
    .filter(Boolean);
}

function isDetachedElsewhere(session, member) {
  return detachedElsewhereIds(session).has(member.character_id);
}

function isDetachedHere(session, member) {
  const tileId = session.map_state?.current_tile_id;
  return (session.detached_groups || []).some(
    (group) => group.tile_id === tileId && (group.character_ids || []).includes(member.character_id)
  );
}

function eligibleHeroicSkillOptions(member) {
  const catalog = state.heroicSkillsCatalog;
  if (!catalog || (member.level || 1) < (catalog.min_level_default || 10)) return [];
  if (!member.heroic_trained) return [];
  const codes = CLASS_SKILL_CODES[member.class_id] || [];
  const learned = learnedHeroicSkillIds(member);
  const options = [];
  for (const skill of catalog.skills || []) {
    const id = String(skill.id || "").toLowerCase();
    if (!id) continue;
    const allowed = (skill.classes || []).some((code) => codes.includes(code));
    if (!allowed || (learned.has(id) && !skill.repeatable)) continue;
    options.push({
      id,
      label: skill.name,
      kind: "skill",
      category: skill.category || "",
      classes: skill.classes || [],
      repeatable: Boolean(skill.repeatable),
    });
  }
  return options.sort((left, right) => left.label.localeCompare(right.label));
}

function eligibleLegendarySkillOptions(member) {
  const catalog = state.legendarySkillsCatalog;
  if (!catalog || (member.level || 1) < (catalog.min_level_default || 15)) return [];
  if (!member.legendary_trained) return [];
  const codes = CLASS_SKILL_CODES[member.class_id] || [];
  const learned = learnedLegendarySkillIds(member);
  const heroicLearned = learnedHeroicSkillIds(member);
  const options = [];
  for (const skill of catalog.skills || []) {
    const id = String(skill.id || "").toLowerCase();
    if (!id) continue;
    const allowed = (skill.classes || []).some((code) => codes.includes(code));
    if (!allowed || (learned.has(id) && !skill.repeatable)) continue;
    const baseId = String(skill.upgrades || "").toLowerCase();
    if (baseId && !heroicLearned.has(baseId)) continue;
    options.push({
      id,
      label: skill.name,
      kind: "skill",
      category: skill.category || "",
      classes: skill.classes || [],
      repeatable: Boolean(skill.repeatable),
      upgrades: skill.upgrades || "",
    });
  }
  return options.sort((left, right) => left.label.localeCompare(right.label));
}

function appendSkillLearnDetails(parent, label, options, fork, member, advanceAction = "xp_roll", xpSpent = null) {
  if (!options.length) return;
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = label;
  details.appendChild(summary);
  const skillRow = node("div", "level-up-spell-pick-actions");
  for (const option of options) {
    const skillBtn = node("button", "secondary", option.label);
    skillBtn.type = "button";
    setButtonTooltip(skillBtn, skillOptionTooltip(option, fork));
    skillBtn.addEventListener("click", () => {
      const payload = { character_id: member.character_id, advancement_fork: fork };
      if (xpSpent != null) payload.xp_spent = xpSpent;
      if (fork === "learn_expert_skill") {
        payload.expert_skill_id = option.id;
        if (EXPERT_TARGET_SKILLS.has(option.id)) {
          const target = window.prompt(`Monster type for ${option.label} (e.g. goblin, undead):`, "");
          if (!target || !target.trim()) return;
          payload.expert_skill_target = target.trim();
        }
      } else if (fork === "learn_heroic_skill") {
        payload.heroic_skill_id = option.id;
        if (HEROIC_TARGET_SKILLS.has(option.id)) {
          const target = window.prompt(`Weapon type for ${option.label} (e.g. bow, sword, dagger):`, "");
          if (!target || !target.trim()) return;
          payload.heroic_skill_target = target.trim();
        }
      } else if (fork === "learn_legendary_skill") {
        payload.legendary_skill_id = option.id;
      }
      advance(advanceAction, payload);
    });
    skillRow.appendChild(skillBtn);
  }
  details.appendChild(skillRow);
  parent.appendChild(details);
}

function skillOptionTooltip(option, fork) {
  const catalog =
    fork === "learn_expert_skill"
      ? state.expertSkillsCatalog
      : fork === "learn_heroic_skill"
        ? state.heroicSkillsCatalog
        : state.legendarySkillsCatalog;
  const tier =
    fork === "learn_expert_skill"
      ? "expert"
      : fork === "learn_heroic_skill"
        ? "heroic"
        : "legendary";
  const parts = [
    `Spend this advancement roll to attempt learning ${option.label}.`,
    `${titleCase(tier)} ${option.kind === "spell" ? "spell" : "skill"}.`,
  ];
  if (option.category) parts.push(`Category: ${titleCase(option.category)}.`);
  const classNames = skillClassNames(option, catalog);
  if (classNames.length) parts.push(`Eligible classes: ${classNames.join(", ")}.`);
  if (option.minLevel) parts.push(`Minimum level: ${option.minLevel}.`);
  if (option.repeatable) parts.push("Repeatable: may be learned more than once where the rules allow.");
  if (EXPERT_TARGET_SKILLS.has(option.id)) parts.push("Requires a monster type target when chosen.");
  if (HEROIC_TARGET_SKILLS.has(option.id)) parts.push("Requires a weapon type target when chosen.");
  if (option.upgrades) parts.push(`Requires ${titleCase(String(option.upgrades).replace(/_/g, " "))}.`);
  return parts.join(" ");
}

function skillClassNames(option, catalog) {
  const codeMap = catalog?.class_codes || {};
  const codes = option.classes || [];
  const classIds = option.classIds || [];
  return [
    ...codes.map((code) => titleCase(codeMap[code] || code)),
    ...classIds.map((classId) => titleCase(String(classId).replace(/_/g, " "))),
  ];
}

function learnedExpertSkillIds(member) {
  return new Set(
    (member.learned_expert_skills || []).map((item) => String(item).toLowerCase().split(":")[0])
  );
}

function hasExpertSkill(member, skillId) {
  return learnedExpertSkillIds(member).has(String(skillId || "").toLowerCase());
}

function hasHeroicSkill(member, skillId) {
  return learnedHeroicSkillIds(member).has(String(skillId || "").toLowerCase());
}

function hasLegendarySkill(member, skillId) {
  return learnedLegendarySkillIds(member).has(String(skillId || "").toLowerCase());
}

const EXPERT_TARGET_SKILLS = new Set(["impervious", "sworn_enemy"]);
const HEROIC_TARGET_SKILLS = new Set(["heroic_accuracy"]);

function eligibleExpertSkillOptions(member) {
  const catalog = state.expertSkillsCatalog;
  if (!catalog || (member.level || 1) < (catalog.min_level_default || 5)) return [];
  if (!member.expert_trained) return [];
  const codes = CLASS_SKILL_CODES[member.class_id] || [];
  const learned = learnedExpertSkillIds(member);
  const options = [];
  for (const skill of catalog.skills || []) {
    const id = String(skill.id || "").toLowerCase();
    if (!id) continue;
    const allowed = (skill.classes || []).some((code) => codes.includes(code));
    if (!allowed) continue;
    if (learned.has(id) && !skill.repeatable) continue;
    options.push({
      id,
      label: skill.name,
      kind: "skill",
      category: skill.category || "",
      classes: skill.classes || [],
      classIds: skill.class_ids || [],
      repeatable: Boolean(skill.repeatable),
    });
  }
  for (const spell of catalog.expert_spells || []) {
    const id = String(spell.id || "").toLowerCase();
    if (!id || learned.has(id)) continue;
    const minLevel = spell.min_level || catalog.min_level_default || 5;
    if ((member.level || 1) < minLevel) continue;
    const allowed = (spell.classes || []).some((code) => codes.includes(code));
    if (!allowed) continue;
    options.push({
      id,
      label: `${spell.name} (expert spell)`,
      kind: "spell",
      classes: spell.classes || [],
      minLevel,
    });
  }
  return options.sort((left, right) => left.label.localeCompare(right.label));
}

function eligibleClueSpellOptions(member) {
  const classId = String(member?.class_id || "").toLowerCase();
  if (!["wizard", "elf"].includes(classId)) return [];
  return eligibleExpertSkillOptions(member)
    .filter((option) => option.kind === "spell")
    .map((option) => ({ ...option, label: option.label.replace(/\s+\(expert spell\)$/i, "") }));
}

function learnedExpertSkillsLine(member) {
  const catalog = state.expertSkillsCatalog;
  const learned = member.learned_expert_skills || [];
  if (!learned.length) return "";
  const names = learned.map((skillId) => {
    const skill = (catalog?.skills || []).find((item) => item.id === skillId);
    if (skill) return skill.name;
    const spell = (catalog?.expert_spells || []).find((item) => item.id === skillId);
    if (spell) return spell.name;
    return skillId;
  });
  return `Expert skills: ${names.join(", ")}`;
}

function tierTrainingButtons(session, member, item) {
  if (session.mode !== "exploration" || member.current_life <= 0) return;
  const row = node("div", "level-up-spell-pick-actions");
  let added = false;
  if (member.level >= 5 && !member.expert_trained) {
    const expertBtn = node("button", "secondary", "Expert training (500gp)");
    expertBtn.type = "button";
    setButtonTooltip(expertBtn, ACTION_TOOLTIPS.enterExpertTier);
    expertBtn.addEventListener("click", () =>
      advance("enter_tier_training", { character_id: member.character_id, tier_training: "expert" })
    );
    const expertXpBtn = node("button", "secondary", "Expert training (1 XP roll)");
    expertXpBtn.type = "button";
    setButtonTooltip(expertXpBtn, ACTION_TOOLTIPS.enterExpertTier);
    expertXpBtn.addEventListener("click", () =>
      advance("enter_tier_training", {
        character_id: member.character_id,
        tier_training: "expert",
        use_xp_for_tier: true,
      })
    );
    row.append(expertBtn, expertXpBtn);
    added = true;
  }
  if (member.level >= 9 && member.expert_trained && !member.heroic_trained) {
    const heroicBtn = node("button", "secondary", "Heroic training (1000gp + 2 XP)");
    heroicBtn.type = "button";
    setButtonTooltip(heroicBtn, ACTION_TOOLTIPS.enterHeroicTier);
    heroicBtn.addEventListener("click", () =>
      advance("enter_tier_training", { character_id: member.character_id, tier_training: "heroic" })
    );
    row.appendChild(heroicBtn);
    added = true;
  }
  if (member.level >= 14 && member.heroic_trained && !member.legendary_trained) {
    const legendaryBtn = node("button", "secondary", "Legendary training (2000gp + 3 XP)");
    legendaryBtn.type = "button";
    setButtonTooltip(legendaryBtn, ACTION_TOOLTIPS.enterLegendaryTier);
    legendaryBtn.addEventListener("click", () =>
      advance("enter_tier_training", { character_id: member.character_id, tier_training: "legendary" })
    );
    row.appendChild(legendaryBtn);
    added = true;
  }
  if (added) {
    const wrap = node("div", "level-up-spell-pick");
    wrap.appendChild(node("strong", "", "Tier training (between adventures):"));
    if (member.level >= 5 && !member.expert_trained) {
      wrap.appendChild(
        node(
          "div",
          "muted",
          "Expert training is required before Level 6, Expert dice, or Expert skill/spell learning. Spending 1 XP here enters the tier; it is not the later skill-learning roll."
        )
      );
    }
    wrap.appendChild(row);
    item.appendChild(wrap);
  }
}

function appendXpAdvancementChoices(item, session, member) {
  const xpSystem = session.xp_system || "classical";
  const spellPickPending = Boolean(session.level_up_spell_pending_character_id);
  if (
    session.mode !== "exploration" ||
    member.current_life <= 0 ||
    spellPickPending ||
    xpSystem !== "classical" ||
    (session.xp_rolls_pending || 0) <= 0
  ) {
    return;
  }
  if ((member.level || 1) < 5) {
    const xpBtn = node("button", "secondary", "Spend XP Roll (Level up)");
    xpBtn.type = "button";
    setButtonTooltip(xpBtn, ACTION_TOOLTIPS.xpRoll);
    xpBtn.addEventListener("click", () =>
      advance("xp_roll", { character_id: member.character_id, advancement_fork: "level_up" })
    );
    item.appendChild(xpBtn);
    return;
  }
  if (!member.expert_trained) return;
  const wrap = node("div", "level-up-spell-pick");
  wrap.appendChild(node("strong", "", "Spend 1 XP roll — choose advancement:"));
  const row = node("div", "level-up-spell-pick-actions");
  const levelBtn = node("button", "secondary", "Level up");
  levelBtn.type = "button";
  setButtonTooltip(levelBtn, ACTION_TOOLTIPS.xpRoll);
  levelBtn.addEventListener("click", () =>
    advance("xp_roll", { character_id: member.character_id, advancement_fork: "level_up" })
  );
  row.appendChild(levelBtn);
  appendSkillLearnDetails(row, "Learn expert skill or spell", eligibleExpertSkillOptions(member), "learn_expert_skill", member);
  if ((member.level || 1) >= 10) {
    appendSkillLearnDetails(row, "Learn heroic skill", eligibleHeroicSkillOptions(member), "learn_heroic_skill", member);
  }
  if ((member.level || 1) >= 15) {
    appendSkillLearnDetails(row, "Learn legendary skill", eligibleLegendarySkillOptions(member), "learn_legendary_skill", member);
  }
  wrap.appendChild(row);
  item.appendChild(wrap);
}

function appendSlowerAdvancementChoices(item, session, member) {
  const xpSystem = session.xp_system || "classical";
  const spellPickPending = Boolean(session.level_up_spell_pending_character_id);
  const minimum = (member.level || 1) + 1;
  if (
    session.mode !== "exploration" ||
    member.current_life <= 0 ||
    spellPickPending ||
    xpSystem !== "slower_advancement" ||
    (session.slower_xp_bank || 0) < minimum
  ) {
    return;
  }
  if ((member.level || 1) < 5) {
    const xpBtn = node("button", "secondary", `Spend ${minimum}+ Banked XP (Level up)`);
    xpBtn.type = "button";
    setButtonTooltip(xpBtn, ACTION_TOOLTIPS.slowerXpSpend);
    xpBtn.addEventListener("click", () =>
      advance("slower_xp_spend", {
        character_id: member.character_id,
        xp_spent: minimum,
        advancement_fork: "level_up",
      })
    );
    item.appendChild(xpBtn);
    return;
  }
  if (!member.expert_trained) return;
  const wrap = node("div", "level-up-spell-pick");
  wrap.appendChild(node("strong", "", `Spend ${minimum}+ banked XP — choose advancement:`));
  const row = node("div", "level-up-spell-pick-actions");
  const levelBtn = node("button", "secondary", "Level up");
  levelBtn.type = "button";
  setButtonTooltip(levelBtn, ACTION_TOOLTIPS.slowerXpSpend);
  levelBtn.addEventListener("click", () =>
    advance("slower_xp_spend", {
      character_id: member.character_id,
      xp_spent: minimum,
      advancement_fork: "level_up",
    })
  );
  row.appendChild(levelBtn);
  appendSkillLearnDetails(
    row,
    "Learn expert skill or spell",
    eligibleExpertSkillOptions(member),
    "learn_expert_skill",
    member,
    "slower_xp_spend",
    minimum
  );
  if ((member.level || 1) >= 10) {
    appendSkillLearnDetails(
      row,
      "Learn heroic skill",
      eligibleHeroicSkillOptions(member),
      "learn_heroic_skill",
      member,
      "slower_xp_spend",
      minimum
    );
  }
  if ((member.level || 1) >= 15) {
    appendSkillLearnDetails(
      row,
      "Learn legendary skill",
      eligibleLegendarySkillOptions(member),
      "learn_legendary_skill",
      member,
      "slower_xp_spend",
      minimum
    );
  }
  wrap.appendChild(row);
  item.appendChild(wrap);
}

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
  "warp_wood",
  "glamour_mask",
  "forest_pathway",
  "alter_weather",
  "illusionary_servant",
  "illusionary_banquet",
  "healing_surge",
  "mass_teleport",
  "lifeforce_control",
]);

const COMBAT_BLOCKED_SPELL_KEYS = new Set([
  ...EXPLORATION_SPELL_KEYS,
]);

const EXPLORATION_MODE_SPELL_KEYS = new Set([
  ...EXPLORATION_SPELL_KEYS,
  "blessing",
  "healing_prayer",
  "healing",
  "protection",
]);

const COMBAT_UTILITY_SPELL_KEYS = new Set([
  "blessing",
  "healing_prayer",
  "healing",
  "protection",
  "illusionary_armor",
  "illusionary_mirror_image",
  "illusionary_fog",
  "barkskin",
  "bear_form",
  "healing_surge",
  "lifeforce_control",
  "mass_teleport",
  "reverse_gaze",
]);

const ALLY_TARGET_SPELL_KEYS = new Set([
  "blessing",
  "healing_prayer",
  "healing",
  "protection",
  "barkskin",
  "lifeforce_control",
]);

function spellNeedsAllyTarget(spellName) {
  return ALLY_TARGET_SPELL_KEYS.has(normalizeSpellKey(spellName));
}

function livingPartyMembers(session) {
  return (session.party || []).filter((member) => member.current_life > 0);
}

function syncAllySpellTargets(session) {
  const living = livingPartyMembers(session);
  if (!living.length) {
    state.allySpellTargets = {};
    return;
  }
  const next = { ...state.allySpellTargets };
  for (const member of living) {
    const current = next[member.character_id];
    if (!current || !living.some((ally) => ally.character_id === current)) {
      next[member.character_id] = member.character_id;
    }
  }
  for (const characterId of Object.keys(next)) {
    if (!living.some((member) => member.character_id === characterId)) {
      delete next[characterId];
    }
  }
  state.allySpellTargets = next;
}

function allyTargetSelect(session, casterId) {
  syncAllySpellTargets(session);
  const living = livingPartyMembers(session);
  const select = document.createElement("select");
  select.className = "ally-target-select";
  for (const ally of living) {
    const option = document.createElement("option");
    option.value = ally.character_id;
    option.textContent = ally.name;
    select.appendChild(option);
  }
  select.value = state.allySpellTargets[casterId] || casterId;
  select.addEventListener("change", () => {
    state.allySpellTargets[casterId] = select.value;
  });
  return select;
}

function sessionDisplayTitle(session) {
  const label = session?.save_label?.trim();
  if (label) return label;
  return `${partyNameById(session.party_id)} — ${session.adventure_id}`;
}

function spellCastPayload(casterId, spellName, extra = {}) {
  const payload = { character_id: casterId, spell_name: spellName, ...extra };
  const key = normalizeSpellKey(spellName);
  if (state.session) syncAllySpellTargets(state.session);
  if (spellNeedsAllyTarget(spellName)) {
    payload.target_character_id = state.allySpellTargets[casterId] || casterId;
  }
  const session = state.session;
  if (session?.mode === "combat") {
    const tile = currentTile(session);
    const livingFoes = (tile?.enemies || []).filter((foe) => foe.life > 0);
    const member = (session.party || []).find((hero) => hero.character_id === casterId);
    if (key === "fireball" && member) {
      const aim = fireballAimModeFor(session, member, livingFoes);
      if (aim) payload.spell_target_mode = aim;
      if (aim === "minions") {
        const minors = livingFoeMinors(livingFoes);
        payload.foe_id = minors[0]?.id;
      } else if (aim === "single") {
        const pool = spellFoeTargetPool(session, member, livingFoes);
        const chosen = state.spellFoeTargets?.[casterId];
        payload.foe_id =
          chosen && pool.some((foe) => foe.id === chosen) ? chosen : pool[0]?.id;
      }
    } else if ((key === "lightning" || key === "sleep") && livingFoes.length) {
      const chosen = state.spellFoeTargets?.[casterId];
      payload.foe_id =
        chosen && livingFoes.some((foe) => foe.id === chosen) ? chosen : livingFoes[0].id;
    } else if (
      (key === "infallible_missile" ||
        key === "aura_of_terror" ||
        key === "reverse_gaze" ||
        key === "lifeforce_control" ||
        key === "phantasmal_binding" ||
        key === "water_jet") &&
      livingFoes.length
    ) {
      const chosen = state.spellFoeTargets?.[casterId];
      payload.foe_id =
        chosen && livingFoes.some((foe) => foe.id === chosen) ? chosen : livingFoes[0].id;
      if (key === "infallible_missile" && member && member.level >= 8) {
        const secondary = state.spellSecondaryFoeTargets?.[casterId];
        if (secondary && livingFoes.some((foe) => foe.id === secondary)) {
          payload.secondary_foe_id = secondary;
        }
      }
    }
  }
  if (key === "lifeforce_control" && !payload.life_transfer_amount) {
    payload.life_transfer_amount = Math.max(
      1,
      Number.parseInt(state.spellLifeTransfer?.[casterId], 10) || 1
    );
  }
  if (key === "mass_teleport") {
    if (session && !payload.teleport_tile_id) {
      payload.teleport_tile_id =
        state.teleportTileId?.[casterId] || session.map_state?.current_tile_id;
    }
    const selected = state.teleportAllies?.[casterId];
    if (Array.isArray(selected) && selected.length) {
      payload.teleport_character_ids = selected;
    }
  }
  return payload;
}

function spellCommitsToAttack(spellName) {
  return true;
}

const SPELL_TABLE_KEYS = [
  "basic_spells_table",
  "druid_spells_table",
  "illusionist_spells_table",
  "expert_spells_table",
];

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

function goldCarryCapacity(member, session = null) {
  const cap = session ? effectiveGoldCap(session, member) : CARRY_LIMITS.gold;
  return Math.max(0, cap - (member?.gold || 0));
}

function isMissileWeapon(item) {
  const lower = String(item || "").toLowerCase();
  return lower.includes("bow") || lower.includes("crossbow") || lower.includes("sling");
}

function isTwoHandedWeapon(item) {
  const lower = String(item || "").toLowerCase();
  return (
    lower.includes("heavy weapon") ||
    lower.includes("two-handed") ||
    lower.includes("two handed") ||
    lower.includes("bow") ||
    lower.includes("crossbow")
  );
}

function effectiveGoldCap(session, member) {
  const servant =
    session?.illusionary_servant_active && session?.illusionary_servant_owner_id === member?.character_id;
  return CARRY_LIMITS.gold + (servant ? CARRY_LIMITS.gold : 0);
}

function effectiveWeaponCap(session, member) {
  const servant =
    session?.illusionary_servant_active && session?.illusionary_servant_owner_id === member?.character_id;
  const baseline = carryBaseline(member, session);
  return baseline.weapons + CARRY_LIMITS.weapons + (servant ? CARRY_LIMITS.weapons : 0);
}

function carryBaseline(member, session = null) {
  if (session && member?.starting_weapon_slots != null && member?.starting_shields != null) {
    return { weapons: member.starting_weapon_slots, shields: member.starting_shields };
  }
  if (!session) {
    return { weapons: CARRY_LIMITS.weapons, shields: CARRY_LIMITS.shields };
  }
  return { weapons: 0, shields: 0 };
}

function encumbranceReasons(member, session = null) {
  const reasons = [];
  const goldCap = session ? effectiveGoldCap(session, member) : CARRY_LIMITS.gold;
  const baseline = carryBaseline(member, session);
  const gold = member?.gold || 0;
  const weaponSlots = weaponCarrySlots(member?.inventory);
  const shields = countCarriedShields(member?.inventory);
  if (gold > goldCap) reasons.push(`gold (${gold}/${goldCap}gp)`);
  if (session && weaponSlots > baseline.weapons) {
    reasons.push(`extra weapons (${weaponSlots - baseline.weapons} over start)`);
  } else if (!session && weaponSlots > CARRY_LIMITS.weapons) {
    reasons.push(`weapons (${weaponSlots}/${CARRY_LIMITS.weapons} slots)`);
  }
  if (session && shields > baseline.shields) {
    reasons.push(`extra shields (${shields - baseline.shields} over start)`);
  } else if (!session && shields > CARRY_LIMITS.shields) {
    reasons.push(`shields (${shields}/${CARRY_LIMITS.shields})`);
  }
  return reasons;
}

function isOverEncumbered(member, session = null) {
  return encumbranceReasons(member, session).length > 0;
}

function memberMeleeWeapons(member) {
  return (member?.inventory || []).filter((item) => isCarriedWeapon(item) && !isMissileWeapon(item));
}

function memberMissileWeapons(member) {
  return (member?.inventory || []).filter((item) => isMissileWeapon(item));
}

function weaponCarrySlots(inventory) {
  let total = 0;
  for (const item of inventory || []) {
    if (!isCarriedWeapon(item)) continue;
    total += isTwoHandedWeapon(item) ? 2 : 1;
  }
  return total;
}

function carryLimitsLine(member, session = null) {
  const gold = member?.gold || 0;
  const bankGold = member?.bank_gold || 0;
  const goldCap = session ? effectiveGoldCap(session, member) : CARRY_LIMITS.gold;
  const weaponSlots = weaponCarrySlots(member?.inventory);
  const shields = countCarriedShields(member?.inventory);
  if (session) {
    const baseline = carryBaseline(member, session);
    const weaponCap = effectiveWeaponCap(session, member);
    const bankLine = bankGold > 0 ? ` | Bank ${bankGold}gp` : "";
    return (
      `Carry ${gold}/${goldCap}gp | ` +
      `${weaponSlots}/${weaponCap} weapon slots (started ${baseline.weapons}) | ` +
      `${shields} shields (started ${baseline.shields})` +
      bankLine
    );
  }
  return (
    `Home gold ${gold}gp | ` +
    `${weaponSlots}/${CARRY_LIMITS.weapons} weapon slots | ` +
    `${shields}/${CARRY_LIMITS.shields} shields`
  );
}

function canMemberReceiveItem(member, itemName, session = null) {
  if (!member || !itemName) return false;
  if (isCarriedShield(itemName) && countCarriedShields(member.inventory) >= CARRY_LIMITS.shields) {
    return false;
  }
  if (isCarriedWeapon(itemName)) {
    const slots = isTwoHandedWeapon(itemName) ? 2 : 1;
    const weaponCap = session ? effectiveWeaponCap(session, member) : CARRY_LIMITS.weapons;
    if (weaponCarrySlots(member.inventory) + slots > weaponCap) {
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

function foeLevelLabel(foe) {
  const level = foe?.level ?? "?";
  return foe?.level_drop_applied ? `Eff L${level}` : `L${level}`;
}

function buildFoeDisplayLabels(enemies) {
  const living = (enemies || []).filter((enemy) => enemy.life > 0);
  const totals = {};
  for (const enemy of living) {
    totals[enemy.name] = (totals[enemy.name] || 0) + 1;
  }
  const seen = {};
  const labels = new Map();
  for (const enemy of living) {
    if (totals[enemy.name] > 1) {
      seen[enemy.name] = (seen[enemy.name] || 0) + 1;
      labels.set(enemy.id, `${enemy.name} (${seen[enemy.name]})`);
    } else if (enemy.subdued) {
      labels.set(enemy.id, `${enemy.name} (subdued)`);
    } else {
      labels.set(enemy.id, enemy.name);
    }
  }
  return labels;
}

function foeDisplayName(enemies, enemy) {
  return buildFoeDisplayLabels(enemies).get(enemy.id) || enemy.name;
}

function foeIsMassKillMinor(foe) {
  return foe.life > 0 && (foe.category === "minions" || foe.category === "vermin");
}

function livingFoeMinors(foes) {
  return (foes || []).filter((foe) => foe.life > 0 && foeIsMassKillMinor(foe));
}

function livingFoeSingles(foes) {
  return (foes || []).filter((foe) => foe.life > 0 && !foeIsMassKillMinor(foe));
}

function fireballNeedsAimChoice(foes) {
  return livingFoeMinors(foes).length > 0 && livingFoeSingles(foes).length > 0;
}

function defaultFireballAimMode(foes) {
  const minors = livingFoeMinors(foes);
  const singles = livingFoeSingles(foes);
  if (minors.length && !singles.length) return "minions";
  if (singles.length && !minors.length) return "single";
  return "";
}

function fireballAimModeFor(session, member, livingFoes) {
  return state.spellAimModes?.[member.character_id] || defaultFireballAimMode(livingFoes);
}

function fireballAimHint(member, livingFoes) {
  const level = member?.level || 1;
  const sample = livingFoeMinors(livingFoes)[0];
  const foeLevel = sample ? foeLevelLabel(sample) : "L?";
  return (
    `Minion aim: on success vs vermin/minions, slays max(1, spell total − foe level) creatures. ` +
    `At caster L${level}, slays 1× ${foeLevel} minion on a minimal roll; higher totals kill more. ` +
    `Single aim: 1 damage to one boss/weird foe — cannot also wipe minions. Mummies: +2 on the Fireball roll.`
  );
}

function spellNeedsFoeTargetRow(spellName, session, member, livingFoes) {
  const key = normalizeSpellKey(spellName);
  if (key === "lightning" || key === "sleep") return livingFoes.length > 1;
  if (
    key === "infallible_missile" ||
    key === "aura_of_terror" ||
    key === "reverse_gaze" ||
    key === "lifeforce_control" ||
    key === "phantasmal_binding" ||
    key === "water_jet"
  ) {
    return livingFoes.length > 1;
  }
  if (key === "fireball") {
    const aim = fireballAimModeFor(session, member, livingFoes);
    if (aim === "single") {
      const singles = livingFoeSingles(livingFoes);
      return singles.length > 1;
    }
  }
  return false;
}

function spellFoeTargetPool(session, member, livingFoes) {
  const spells = heroCombatSpells(session, member);
  const hasFireball = spells.some((spell) => normalizeSpellKey(spell) === "fireball");
  if (hasFireball && fireballAimModeFor(session, member, livingFoes) === "single") {
    const singles = livingFoeSingles(livingFoes);
    if (singles.length) return singles;
  }
  return livingFoes;
}

function createFoeTargetSelect(livingFoes, { value, onChange, filter = null }) {
  const select = document.createElement("select");
  const pool = filter ? livingFoes.filter(filter) : livingFoes;
  const labels = buildFoeDisplayLabels(livingFoes);
  if (!pool.length) {
    select.disabled = true;
    const option = document.createElement("option");
    option.textContent = "No valid targets";
    select.appendChild(option);
    return select;
  }
  for (const foe of pool) {
    const option = document.createElement("option");
    option.value = foe.id;
    option.textContent = `${labels.get(foe.id) || foe.name} (${foeLevelLabel(foe)})`;
    select.appendChild(option);
  }
  const resolved = value && pool.some((foe) => foe.id === value) ? value : pool[0].id;
  select.value = resolved;
  onChange(resolved);
  select.addEventListener("change", () => onChange(select.value));
  return select;
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
      return "Move archers to rear rank (#3–4) to shoot. Resolve Round still runs front melee and foe attacks.";
    }
    return null;
  }
  if (round === 0) {
    if (session.party_attacked_immediately) {
      return `Opening volley: ${archers.map((member) => member.name).join(", ")} shoot on Resolve Round.`;
    }
    if (session.party_surprised) {
      return `Surprised opening round: ${archers.map((member) => member.name).join(", ")} may shoot after foes act.`;
    }
    return `Bows ready, but no opening volley — you checked Reactions first (p.146). Attack immediately next fight, or use corridor rear rank (#3–4).`;
  }
  return null;
}

function combatRoundStatusText(session) {
  const tile = currentTile(session);
  const tileType = tile?.tile_type || "room";
  const round = (session.combat_round || 0) + 1;
  const living = (session?.party || []).filter((member) => member.current_life > 0);

  if (tileType === "corridor") {
    const rearMissile = living.filter((member) => heroWillUseMissile(session, member, tile));
    const frontMelee = living.filter((member) => heroCanMeleeInCombat(session, member, tile));
    const parts = [];
    if (rearMissile.length) {
      parts.push(`rear shoots (${rearMissile.map((member) => member.name).join(", ")})`);
    }
    if (frontMelee.length) {
      parts.push(`front melees (${frontMelee.map((member) => member.name).join(", ")})`);
    }
    const plan = parts.length ? `${parts.join("; ")}; then foes attack` : "foes attack";
    return `Round ${round}: one Resolve Round — ${plan}.`;
  }

  const missileNote = missileStatusSummary(session);
  if (missileNote?.includes("Opening volley")) {
    const shooters = living.filter((member) => heroWillUseMissile(session, member, tile));
    const melee = living.filter((member) => member.marching_order <= 2 || tileType !== "corridor");
    const opener = shooters.length
      ? `opening volley (${shooters.map((member) => member.name).join(", ")})`
      : "opening volley";
    const front = melee.length ? `; front melees (${melee.map((member) => member.name).join(", ")})` : "";
    return `Round ${round}: one Resolve Round — ${opener}${front}; then foes attack.`;
  }
  if (missileNote) return missileNote;
  return `Round ${round}: one Resolve Round — party attacks, then foes attack.`;
}

function encounterPending(session) {
  return session?.mode === "exploration" && livingFoesOnTile(session).length > 0;
}

function shouldUseCombatFocus(session) {
  if (!session || session.mode === "complete" || session.camped_outside) return false;
  return session.mode === "combat" || encounterPending(session);
}

function toggleCombatCinema() {
  const entering = !state.combatCinema;
  if (entering) {
    state.mapStageHeightBeforeCinema = state.mapStageHeight;
    state.mapStageHeight = null;
  } else if (state.mapStageHeightBeforeCinema !== undefined) {
    state.mapStageHeight = state.mapStageHeightBeforeCinema;
    state.mapStageHeightBeforeCinema = null;
  }
  state.combatCinema = entering;
  updateCombatCinemaToggleButtons();
  applyLayoutCss();
  if (state.session) applyCombatFocusLayout(state.session);
}

function updateCombatCinemaToggleButtons() {
  const label = state.combatCinema ? "Exit cinema view" : "Cinema view";
  const pressed = state.combatCinema ? "true" : "false";
  for (const btn of [combatCinemaToggleBtn, combatCinemaToggleRailBtn, combatCinemaToggleTacticalBtn]) {
    if (!btn) continue;
    btn.textContent = label;
    btn.setAttribute("aria-pressed", pressed);
    btn.classList.toggle("cinema-active", state.combatCinema);
  }
}

function setCombatCommandTab(tab) {
  state.combatCommandTab = tab;
  if (!combatCommandRailEl) return;
  for (const button of combatCommandRailEl.querySelectorAll(".combat-command-tab")) {
    const active = button.dataset.tab === tab;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  }
  combatRailExitsEl?.classList.toggle("hidden", tab !== "exits");
  combatRailEncounterEl?.classList.toggle("hidden", tab !== "encounter");
  combatRailLogEl?.classList.toggle("hidden", tab !== "log");
}

function applyCombatFocusLayout(session) {
  const active = shouldUseCombatFocus(session);
  const wasActive = sessionMain?.classList.contains("combat-focus");
  if (active && !wasActive && livingFoesOnTile(session).length) {
    state.combatCommandTab = "encounter";
  }
  if (active && !wasActive) {
    state.mapStageHeightBeforeCombat = state.mapStageHeight;
    state.mapStageHeight = null;
  }
  if (!active && wasActive) {
    state.mapStageHeight = state.mapStageHeightBeforeCombat ?? null;
    state.mapStageHeightBeforeCombat = null;
    if (typeof state.mapStageHeight === "number" && state.mapStageHeight < 280) {
      state.mapStageHeight = null;
    }
  }
  if (!active) {
    state.combatCinema = false;
    state.combatHeroDrawerId = null;
  }
  if (active && session.mode === "combat") {
    const round = session.combat_round || 0;
    if (round > state.lastCombatRoundSeen && round > 0) {
      state.combatCommandTab = "log";
      const summary = extractRoundSummaryFromSession(session);
      if (summary) showCombatRoundToast(summary, round);
    }
    state.lastCombatRoundSeen = round;
  } else if (!active) {
    state.lastCombatRoundSeen = 0;
  }
  sessionMain?.classList.toggle("combat-focus", active);
  sessionMain?.classList.toggle("combat-cinema", active && state.combatCinema);
  sessionPanel?.classList.toggle("combat-focus", active);
  combatPartyStripEl?.classList.add("hidden");
  combatCommandRailEl?.classList.toggle("hidden", !active);
  combatCommandRailResizerEl?.classList.toggle("hidden", !active);
  combatSideRailEl?.classList.toggle("hidden", !active);
  combatSideRailResizerEl?.classList.toggle("hidden", !active);
  combatHeroChipsEl?.classList.toggle("hidden", !active);
  combatHeroDrawerEl?.classList.toggle("hidden", !active || !state.combatHeroDrawerId);
  combatHeroDrawerResizerEl?.classList.toggle("hidden", !active || !state.combatHeroDrawerId);
  combatDeckSlimEl?.classList.toggle("hidden", !active);
  tacticalRoomViewportEl?.classList.toggle("hidden", !active);
  mapViewportEl?.classList.toggle("hidden", active);
  combatCinemaToggleTacticalBtn?.classList.toggle("hidden", !active || !state.combatCinema);
  combatCinemaToggleRailBtn?.classList.toggle("hidden", !active || state.combatCinema);
  combatCinemaToggleBtn?.classList.add("hidden");
  mapLogRow?.classList.toggle("hidden", active);
  if (!active && wasActive) {
    renderLog(session);
    requestAnimationFrame(() => {
      if (!state.session) return;
      renderMap(state.session, { skipFocus: true });
      zoomToCurrentRoom();
    });
  }
  updateCombatCinemaToggleButtons();
  if (active) setCombatCommandTab(state.combatCommandTab);
  applyLayoutCss();
  syncCombatViewportLayout();
  renderMapEncounterBanner(session);
  renderCombatCommandRail(session);
  renderCombatFloatDeck(session);
  if (active) scheduleTacticalRoomRender(session);
}

function syncCombatViewportLayout() {
  const active = sessionMain?.classList.contains("combat-focus");
  document.body.classList.toggle("combat-focus-active", Boolean(active));
  if (!sessionPanel) return;
  if (!active) {
    sessionPanel.style.height = "";
    sessionPanel.style.maxHeight = "";
    sessionPanel.style.overflow = "";
    return;
  }
  const top = sessionPanel.getBoundingClientRect().top;
  const height = Math.max(360, window.innerHeight - top - 6);
  sessionPanel.style.height = `${height}px`;
  sessionPanel.style.maxHeight = `${height}px`;
  sessionPanel.style.overflow = "hidden";
  tacticalRoomLastSize = "";
}

function shouldShowLogEntry(entry, { showRolls = true, showMath = false } = {}) {
  const line = String(entry || "");
  if (!showRolls && /\b\d*d\d+\b|\b[A-Z][A-Za-z ]+ rolls?[:(]|\brolls?\s+\d|Roll:|Exploding|table roll|Door attempt| vs L\d/i.test(line)) {
    return false;
  }
  if (!showMath && /math|modifier breakdown|lookup notes|lookup uses|Spellcasting: exploding|explain_math/i.test(line)) {
    return false;
  }
  return true;
}

function filteredLogEntries(session, { limit = 120, tail = null } = {}) {
  const entries = (session.log || []).filter((entry) =>
    shouldShowLogEntry(entry, { showRolls: state.showRolls, showMath: state.showMath })
  );
  const slice = tail ? entries.slice(-tail) : entries.slice(-limit);
  return slice;
}

function updateLogModeControls() {
  const verbose = state.logMode === "verbose";
  state.showRolls = verbose;
  state.showMath = verbose;
  setButtonTooltip(logModeSummaryBtn, ACTION_TOOLTIPS.logSummary);
  setButtonTooltip(logModeVerboseBtn, ACTION_TOOLTIPS.logVerbose);
  logModeSummaryBtn?.classList.toggle("selected", !verbose);
  logModeSummaryBtn?.setAttribute("aria-pressed", verbose ? "false" : "true");
  logModeVerboseBtn?.classList.toggle("selected", verbose);
  logModeVerboseBtn?.setAttribute("aria-pressed", verbose ? "true" : "false");
}

function setLogMode(mode) {
  state.logMode = mode === "verbose" ? "verbose" : "summary";
  updateLogModeControls();
  saveLayoutPrefs();
  if (state.session) {
    renderLog(state.session);
    renderCombatRailLog(state.session);
  }
}

function buildLogModeToggle() {
  const wrap = node("div", "log-mode-toggle", "");
  wrap.setAttribute("role", "group");
  wrap.setAttribute("aria-label", "Log detail");
  const summary = node("button", `secondary log-mode-btn${state.logMode === "summary" ? " selected" : ""}`, "Summary");
  summary.type = "button";
  summary.setAttribute("aria-pressed", state.logMode === "summary" ? "true" : "false");
  setButtonTooltip(summary, ACTION_TOOLTIPS.logSummary);
  summary.addEventListener("click", () => setLogMode("summary"));
  const verbose = node("button", `secondary log-mode-btn${state.logMode === "verbose" ? " selected" : ""}`, "Verbose");
  verbose.type = "button";
  verbose.setAttribute("aria-pressed", state.logMode === "verbose" ? "true" : "false");
  setButtonTooltip(verbose, ACTION_TOOLTIPS.logVerbose);
  verbose.addEventListener("click", () => setLogMode("verbose"));
  wrap.appendChild(summary);
  wrap.appendChild(verbose);
  return wrap;
}

function toggleCombatHeroDrawer(characterId, session) {
  state.combatHeroDrawerId = state.combatHeroDrawerId === characterId ? null : characterId;
  applyCombatFocusLayout(session);
  renderCombatHeroChips(session);
  renderCombatHeroDrawer(session);
  scheduleTacticalRoomRender(session);
}

function appendHeroCombatPlanningRows(parent, session, member, tile, livingFoes) {
  if (!livingFoes.length || member.current_life <= 0) return;
  const targetSelect = document.createElement("select");
  for (const foe of livingFoes) {
    const option = document.createElement("option");
    option.value = foe.id;
    option.textContent = `${foeDisplayName(livingFoes, foe)} (${foeLevelLabel(foe)})`;
    targetSelect.appendChild(option);
  }
  targetSelect.value = state.combatTargets[member.character_id] || livingFoes[0].id;
  targetSelect.addEventListener("change", () => {
    state.combatTargets[member.character_id] = targetSelect.value;
    renderCombatHeroDrawer(session);
    renderCombatHeroChips(session);
  });
  appendCombatSelectRow(parent, "Target", targetSelect);

  const abilityChoices = buildCombatAbilityChoices(session, member);
  if (abilityChoices.length) {
    const abilitySelect = document.createElement("select");
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "None";
    abilitySelect.appendChild(none);
    for (const [value, label] of abilityChoices) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      abilitySelect.appendChild(option);
    }
    abilitySelect.value = state.combatAbilities[member.character_id] || "";
    abilitySelect.addEventListener("change", () => {
      if (abilitySelect.value) state.combatAbilities[member.character_id] = abilitySelect.value;
      else delete state.combatAbilities[member.character_id];
      renderCombatHeroDrawer(session);
    });
    appendCombatSelectRow(parent, "Ability", abilitySelect);
  }

  const ability = state.combatAbilities?.[member.character_id];
  if (ability === "bulwark_sacrifice") {
    const guardSelect = document.createElement("select");
    const allies = (session.party || []).filter(
      (entry) => entry.character_id !== member.character_id && entry.current_life > 0
    );
    for (const ally of allies) {
      const option = document.createElement("option");
      option.value = ally.character_id;
      option.textContent = ally.name;
      guardSelect.appendChild(option);
    }
    guardSelect.value =
      state.combatGuardTargets?.[member.character_id] || allies[0]?.character_id || "";
    guardSelect.addEventListener("change", () => {
      state.combatGuardTargets[member.character_id] = guardSelect.value;
    });
    appendCombatSelectRow(parent, "Guard ally", guardSelect);
  }
  if (ability === "double_attack" && livingFoes.length > 1) {
    const secondarySelect = document.createElement("select");
    for (const foe of livingFoes) {
      const option = document.createElement("option");
      option.value = foe.id;
      option.textContent = `${foeDisplayName(livingFoes, foe)} (${foeLevelLabel(foe)})`;
      secondarySelect.appendChild(option);
    }
    secondarySelect.value =
      state.combatSecondaryTargets?.[member.character_id] || livingFoes[1]?.id || livingFoes[0].id;
    secondarySelect.addEventListener("change", () => {
      state.combatSecondaryTargets[member.character_id] = secondarySelect.value;
    });
    appendCombatSelectRow(parent, "2nd attack target", secondarySelect);
  }
  if (ability === "double_kick") {
    const minors = livingFoeMinors(livingFoes);
    if (minors.length >= 2) {
      for (let index = 0; index < 2; index += 1) {
        const kickSelect = document.createElement("select");
        for (const foe of minors) {
          const option = document.createElement("option");
          option.value = foe.id;
          option.textContent = `${foeDisplayName(livingFoes, foe)} (${foeLevelLabel(foe)})`;
          kickSelect.appendChild(option);
        }
        const stored = state.doubleKickTargets?.[member.character_id] || [];
        kickSelect.value = stored[index] || minors[index]?.id || minors[0].id;
        kickSelect.addEventListener("change", () => {
          const next = [...(state.doubleKickTargets[member.character_id] || minors.slice(0, 2).map((foe) => foe.id))];
          next[index] = kickSelect.value;
          state.doubleKickTargets[member.character_id] = next;
        });
        appendCombatSelectRow(parent, `Kick target ${index + 1}`, kickSelect);
      }
    }
  }
  if (ability === "protective_incense") {
    const allySelect = document.createElement("select");
    const allies = (session.party || []).filter((entry) => entry.current_life > 0);
    for (const ally of allies) {
      const option = document.createElement("option");
      option.value = ally.character_id;
      option.textContent = ally.name;
      allySelect.appendChild(option);
    }
    allySelect.value =
      state.protectiveIncenseTargets?.[member.character_id] || member.character_id;
    allySelect.addEventListener("change", () => {
      state.protectiveIncenseTargets[member.character_id] = allySelect.value;
    });
    appendCombatSelectRow(parent, "Incense protects", allySelect);
  }
  if (ability === "ward_of_protection" || ability === "restore") {
    const allySelect = document.createElement("select");
    const allies = (session.party || []).filter((entry) => entry.current_life > 0);
    for (const ally of allies) {
      const option = document.createElement("option");
      option.value = ally.character_id;
      option.textContent = ally.name;
      allySelect.appendChild(option);
    }
    const defaultAlly =
      allies.find((ally) => ally.character_id !== member.character_id && ally.current_life < ally.max_life) ||
      allies.find((ally) => ally.character_id !== member.character_id) ||
      allies[0];
    allySelect.value = state.combatGuardTargets?.[member.character_id] || defaultAlly?.character_id || member.character_id;
    allySelect.addEventListener("change", () => {
      state.combatGuardTargets[member.character_id] = allySelect.value;
    });
    appendCombatSelectRow(parent, ability === "restore" ? "Heal ally" : "Ward ally", allySelect);
  }
  if (ability === "double_shot" && livingFoes.length > 1) {
    const secondarySelect = document.createElement("select");
    for (const foe of livingFoes) {
      const option = document.createElement("option");
      option.value = foe.id;
      option.textContent = `${foeDisplayName(livingFoes, foe)} (${foeLevelLabel(foe)})`;
      secondarySelect.appendChild(option);
    }
    secondarySelect.value =
      state.combatSecondaryTargets?.[member.character_id] || livingFoes[1]?.id || livingFoes[0].id;
    secondarySelect.addEventListener("change", () => {
      state.combatSecondaryTargets[member.character_id] = secondarySelect.value;
    });
    appendCombatSelectRow(parent, "2nd shot target", secondarySelect);
  }
}

function buildCombatSecondaryTargetsPayload() {
  const targets = {};
  for (const [characterId, enemyId] of Object.entries(state.combatSecondaryTargets || {})) {
    if (enemyId) targets[characterId] = enemyId;
  }
  return Object.keys(targets).length ? targets : undefined;
}

function buildDoubleKickTargetsPayload() {
  const targets = {};
  for (const [characterId, foeIds] of Object.entries(state.doubleKickTargets || {})) {
    if (Array.isArray(foeIds) && foeIds.length >= 2) targets[characterId] = foeIds.slice(0, 2);
  }
  return Object.keys(targets).length ? targets : undefined;
}

function buildProtectiveIncenseTargetsPayload() {
  const targets = {};
  for (const [characterId, allyId] of Object.entries(state.protectiveIncenseTargets || {})) {
    if (allyId) targets[characterId] = allyId;
  }
  return Object.keys(targets).length ? targets : undefined;
}

let tacticalRoomRenderFrame = null;
let tacticalRoomLastSize = "";

function scheduleTacticalRoomRender(session) {
  if (!session || !shouldUseCombatFocus(session)) return;
  window.cancelAnimationFrame(tacticalRoomRenderFrame);
  tacticalRoomRenderFrame = window.requestAnimationFrame(() => {
    tacticalRoomRenderFrame = window.requestAnimationFrame(() => {
      renderTacticalRoom(session);
    });
  });
}

function extractRoundSummaryFromSession(session) {
  const lines = session?.log || [];
  for (let index = lines.length - 1; index >= 0; index -= 1) {
    if (lines[index].startsWith("Round summary:")) {
      return lines[index].replace(/^Round summary:\s*/, "");
    }
  }
  return "";
}

function showCombatRoundToast(summary, round) {
  if (!combatRoundToastEl || !summary) return;
  combatRoundToastEl.replaceChildren();
  combatRoundToastEl.appendChild(node("strong", "", `Round ${round}`));
  combatRoundToastEl.appendChild(document.createTextNode(` — ${summary}`));
  combatRoundToastEl.classList.remove("hidden");
  window.clearTimeout(combatRoundToastTimer);
  combatRoundToastTimer = window.setTimeout(() => {
    combatRoundToastEl.classList.add("hidden");
  }, 6500);
}

function renderCombatCommandRail(session) {
  if (!combatCommandRailEl || !shouldUseCombatFocus(session)) return;
  const tile = currentTile(session);
  const exits = tile ? playerFacingExits(session, tile) : [];
  if (combatTabExitsBadgeEl) {
    combatTabExitsBadgeEl.textContent = exits.length ? String(exits.length) : "";
    combatTabExitsBadgeEl.classList.toggle("hidden", !exits.length);
  }
  renderCombatRailExits(session, tile, exits);
  renderCombatRailEncounter(session, tile);
  renderCombatRailLog(session);
}

function renderCombatRailExits(session, tile, exits) {
  if (!combatRailExitsEl) return;
  combatRailExitsEl.replaceChildren();
  if (!tile) {
    combatRailExitsEl.appendChild(node("div", "combat-rail-empty muted", "No current room."));
    return;
  }
  if (!exits.length) {
    const rawCount = (tile.exits || []).length;
    combatRailExitsEl.appendChild(
      node(
        "div",
        "combat-rail-empty muted",
        rawCount
          ? "No exits are reachable from where you stand."
          : "No exits on this map element."
      )
    );
    return;
  }
  const mode = effectiveSessionMode(session);
  const sideLabels = exitSideLabelsForExits(exits);
  const list = node("div", "combat-exit-chip-list");
  for (const exit of exits) {
    list.appendChild(buildCompactExitChip(session, tile, exit, sideLabels, mode));
  }
  combatRailExitsEl.appendChild(list);
}

function buildCompactExitChip(session, tile, exit, sideLabels, mode) {
  const chip = node("div", `combat-exit-chip${exit.status === "blocked" ? " combat-exit-chip-blocked" : ""}`);
  const head = node("div", "combat-exit-chip-head");
  head.appendChild(node("strong", "combat-exit-label", exitDisplayLabel(exit, sideLabels.get(exit.id))));
  head.appendChild(node("span", "combat-exit-status", exitStatusLabel(exit)));
  chip.appendChild(head);
  const actions = node("div", "combat-exit-actions");
  appendExitRowActions(session, tile, exit, sideLabels.get(exit.id), actions, mode, { dock: false });
  chip.appendChild(actions);
  return chip;
}

function renderCombatRailEncounter(session, tile) {
  if (!combatRailEncounterEl) return;
  combatRailEncounterEl.replaceChildren();
  const foes = livingFoesOnTile(session);
  if (!foes.length) {
    combatRailEncounterEl.appendChild(node("div", "combat-rail-empty muted", "No foes on this tile."));
    return;
  }
  const foeLabels = buildFoeDisplayLabels(tile?.enemies || foes);
  const summary = node("div", "combat-rail-encounter-summary");
  summary.appendChild(
    node(
      "div",
      "combat-rail-encounter-title",
      `${foes.length} foe${foes.length === 1 ? "" : "s"} — click tokens on the tactical map for actions`
    )
  );
  const list = node("div", "combat-rail-foe-list");
  for (const foe of foes.slice(0, 8)) {
    const row = node("div", "combat-rail-foe-row");
    row.appendChild(node("span", "", foeLabels.get(foe.id) || foe.name));
    row.appendChild(node("span", "muted", `${foeLevelLabel(foe)} · ${foe.life}/${foe.max_life}`));
    list.appendChild(row);
  }
  if (foes.length > 8) {
    list.appendChild(node("div", "muted", `+${foes.length - 8} more on the map`));
  }
  summary.appendChild(list);
  combatRailEncounterEl.appendChild(summary);
  const notes = tile ? combatContextNotes(session, tile) : [];
  if (notes.length) {
    const notesBlock = node("div", "combat-rail-notes");
    for (const note of notes) {
      notesBlock.appendChild(node("div", "combat-context-note", note));
    }
    combatRailEncounterEl.appendChild(notesBlock);
  }
  combatRailEncounterEl.appendChild(
    node("div", "combat-rail-encounter-hint muted", "Use the combat deck below for actions, or click a hero chip for spells and abilities.")
  );
}

function renderCombatRailLog(session) {
  if (!combatRailLogEl) return;
  combatRailLogEl.replaceChildren();
  const head = node("div", "combat-rail-log-head");
  head.appendChild(node("strong", "", "Adventure log"));
  head.appendChild(buildLogModeToggle());
  combatRailLogEl.appendChild(head);
  const body = node("div", "combat-rail-log-body");
  const entries = filteredLogEntries(session, { limit: 120 });
  const shown = entries.slice(-24);
  if (!shown.length) {
    body.appendChild(node("div", "combat-log-line muted", "No log entries yet."));
  } else {
    for (const entry of shown) {
      const line = node(
        "div",
        entry.startsWith("Round summary:") ? "combat-log-line combat-log-round-summary" : "combat-log-line",
        entry
      );
      body.appendChild(line);
    }
  }
  combatRailLogEl.appendChild(body);
  body.scrollTop = body.scrollHeight;
}

function visibleWalkableCells(tile, width, height) {
  const walkable = normalizedWalkable(tile, width, height);
  const visible = normalizedVisible(tile, width, height);
  const cells = [];
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (walkable[y]?.[x] !== "0" && visible[y]?.[x] !== "0") cells.push({ x, y });
    }
  }
  return cells;
}

function spreadCellsAcross(cells, count) {
  if (!cells.length || count <= 0) return [];
  const sorted = [...cells].sort((left, right) => left.x - right.x || left.y - right.y);
  if (count === 1) return [sorted[Math.floor(sorted.length / 2)]];
  const picks = [];
  for (let index = 0; index < count; index += 1) {
    const slot = Math.round((index * (sorted.length - 1)) / Math.max(1, count - 1));
    picks.push(sorted[slot]);
  }
  return picks;
}

function computeTacticalTokenLayout(session, tile, width, height) {
  const cells = visibleWalkableCells(tile, width, height);
  const heroes = [...(session.party || [])].sort((left, right) => left.marching_order - right.marching_order);
  const livingFoes = (tile.enemies || []).filter((foe) => foe.life > 0);
  const heroSlots = new Map();
  const foeSlots = new Map();
  const foeStacks = new Map();
  if (!cells.length) return { heroSlots, foeSlots, foeStacks };

  const tileType = tile.tile_type || "room";
  const longAxis = width >= height ? "x" : "y";
  const sorted = [...cells].sort((left, right) => {
    if (longAxis === "x") return left.x - right.x || left.y - right.y;
    return left.y - right.y || left.x - right.x;
  });

  if (tileType === "corridor") {
    const mid = Math.max(1, Math.floor(sorted.length / 2));
    const partyCells = sorted.slice(0, mid);
    const foeCells = sorted.slice(mid);
    const ambush = Boolean(tile.wandering_ambush && (session.combat_round || 0) === 0);
    const frontOrders = ambush ? [3, 4] : [1, 2];
    const rearOrders = ambush ? [1, 2] : [3, 4];
    const frontCells = partyCells.slice(-Math.min(2, partyCells.length));
    const rearCells = partyCells.slice(0, Math.max(0, partyCells.length - frontCells.length));
    frontOrders.forEach((order, index) => {
      const member = heroes.find((entry) => entry.marching_order === order);
      const cell = frontCells[index] || frontCells[frontCells.length - 1];
      if (member && cell) heroSlots.set(member.character_id, cell);
    });
    rearOrders.forEach((order, index) => {
      const member = heroes.find((entry) => entry.marching_order === order);
      const cell = rearCells[index] || rearCells[rearCells.length - 1] || partyCells[index];
      if (member && cell) heroSlots.set(member.character_id, cell);
    });
    livingFoes.forEach((foe, index) => {
      const cell = foeCells[index % Math.max(1, foeCells.length)] || sorted[sorted.length - 1 - index];
      foeSlots.set(foe.id, cell);
    });
  } else {
    const sortedByY = [...cells].sort((left, right) => left.y - right.y || left.x - right.x);
    const minY = sortedByY[0].y;
    const maxY = sortedByY[sortedByY.length - 1].y;
    const range = maxY - minY + 1;
    const partyBand = sortedByY.filter((cell) => cell.y >= maxY - Math.max(0, Math.floor(range * 0.35)));
    const foeBand = sortedByY.filter((cell) => cell.y <= minY + Math.max(0, Math.floor(range * 0.35)));
    const partySpread = spreadCellsAcross(partyBand.length ? partyBand : sortedByY, heroes.length);
    heroes.forEach((member, index) => {
      const cell = partySpread[index] || sortedByY[index % sortedByY.length];
      if (cell) heroSlots.set(member.character_id, cell);
    });
    if (livingFoes.length > 4) {
      const groups = new Map();
      for (const foe of livingFoes) {
        const key = foe.name;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(foe);
      }
      const foeSpread = spreadCellsAcross(foeBand.length ? foeBand : sortedByY.slice(0, 3), groups.size);
      let groupIndex = 0;
      for (const group of groups.values()) {
        const cell = foeSpread[groupIndex] || sortedByY[groupIndex % sortedByY.length];
        const stackKey = `${cell.x},${cell.y}`;
        foeStacks.set(stackKey, group);
        for (const foe of group) foeSlots.set(foe.id, cell);
        groupIndex += 1;
      }
    } else {
      const foeSpread = spreadCellsAcross(foeBand.length ? foeBand : sortedByY.slice(0, livingFoes.length), livingFoes.length);
      livingFoes.forEach((foe, index) => {
        const cell = foeSpread[index] || sortedByY[index % sortedByY.length];
        foeSlots.set(foe.id, cell);
      });
    }
  }
  return { heroSlots, foeSlots, foeStacks };
}

function tacticalFormationHint(session, tile) {
  const tileType = tile?.tile_type || "room";
  if (tileType === "corridor") {
    const ambush = Boolean(tile?.wandering_ambush && (session.combat_round || 0) === 0);
    return ambush
      ? "Corridor ambush: #3–#4 front, #1–#2 rear (round 0)"
      : "Corridor: #1–#2 front melee, #3–#4 rear missiles";
  }
  return "Room: all heroes may melee; rear ranks may volley on round 0";
}

function positionTacticalToken(token, cell, width, height, slotIndex = 0, slotTotal = 1) {
  let offsetX = 0;
  let offsetY = 0;
  if (slotTotal > 1) {
    const angle = (slotIndex / slotTotal) * Math.PI * 2;
    offsetX = Math.cos(angle) * 0.18;
    offsetY = Math.sin(angle) * 0.18;
  }
  token.style.left = `${((cell.x + 0.5 + offsetX) / width) * 100}%`;
  token.style.top = `${((cell.y + 0.5 + offsetY) / height) * 100}%`;
}

function buildTacticalHeroToken(session, tile, member, cell, width, height, livingFoes, slotIndex = 0, slotTotal = 1) {
  const token = node("button", `tactical-token tactical-hero-token${member.current_life <= 0 ? " fallen" : ""}`);
  token.type = "button";
  token.title =
    state.combatCinema || !shouldUseCombatFocus(session)
      ? `#${member.marching_order} ${member.name} — click for spells and combat actions`
      : `#${member.marching_order} ${member.name} — click for sheet; right-click for combat actions`;
  positionTacticalToken(token, cell, width, height, slotIndex, slotTotal);
  token.appendChild(node("span", "tactical-token-order", `#${member.marching_order}`));
  token.appendChild(node("span", "tactical-token-name", member.name.split(" ")[0]));
  token.appendChild(
    node("span", "tactical-token-hp", `${member.current_life}/${member.max_life}`)
  );
  if (state.combatHeroDrawerId === member.character_id) token.classList.add("selected");
  token.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (state.combatCinema) {
      openCombatHeroMenu(session, tile, member, token, livingFoes);
      return;
    }
    toggleCombatHeroDrawer(member.character_id, session);
  });
  token.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    openCombatHeroMenu(session, tile, member, token, livingFoes);
  });
  return token;
}

function buildTacticalFoeToken(session, tile, foe, cell, width, height, foeLabels, stackCount = 1, slotIndex = 0, slotTotal = 1) {
  const token = node("button", `tactical-token tactical-foe-token${foe.life <= 0 ? " dead" : ""}`);
  token.type = "button";
  token.title = `${foeLabels.get(foe.id) || foe.name} — click for targets and spells`;
  positionTacticalToken(token, cell, width, height, slotIndex, slotTotal);
  const icon = contentMarker("monster", foe.name, stackCount);
  icon.classList.add("tactical-foe-icon");
  token.appendChild(icon);
  token.appendChild(node("span", "tactical-token-name", foe.name.split(" ")[0]));
  token.appendChild(node("span", "tactical-token-hp", `${foe.life}/${foe.max_life}`));
  if (stackCount > 1) token.appendChild(node("span", "tactical-token-stack", `×${stackCount}`));
  const openMenu = (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (encounterPending(session)) openMapMonsterMenu(session, tile, token);
    else openCombatFoeMenu(session, tile, foe, token, foeLabels);
  };
  token.addEventListener("click", openMenu);
  token.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") openMenu(event);
  });
  return token;
}

function tacticalRoomCellSize(viewport, tileWidth, tileHeight) {
  const pad = 20;
  const availableW = Math.max(80, viewport.width - pad * 2);
  const availableH = Math.max(80, viewport.height - pad * 2);
  const compact =
    typeof state.mapStageHeight === "number" ||
    (shouldUseCombatFocus(state.session) && availableH < 260);
  const cellFromWidth = availableW / tileWidth;
  const cellFromHeight = availableH / tileHeight;
  const maxCell = compact ? 108 : 168;
  const minCell = compact ? 44 : 52;
  return Math.max(minCell, Math.min(cellFromWidth, cellFromHeight, maxCell));
}

function renderTacticalRoom(session) {
  if (!tacticalRoomEl || !tacticalRoomViewportEl) return;
  const active = shouldUseCombatFocus(session);
  if (!active) {
    tacticalRoomEl.replaceChildren();
    return;
  }
  const tile = currentTile(session);
  if (!tile) {
    tacticalRoomEl.replaceChildren();
    tacticalRoomEl.appendChild(node("div", "tactical-room-empty muted", "No current room."));
    return;
  }
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const viewport = tacticalRoomViewportEl.getBoundingClientRect();
  if (viewport.width < 24 || viewport.height < 24) {
    scheduleTacticalRoomRender(session);
    return;
  }
  const sizeKey = [
    Math.round(viewport.width),
    Math.round(viewport.height),
    tile.id,
    tile.rotation || 0,
    (tile.visible || []).join("/"),
    (tile.walkable || []).join("/"),
    session.mode,
    session.combat_round || 0,
    state.combatHeroDrawerId || "",
  ].join("|");
  if (sizeKey === tacticalRoomLastSize && tacticalRoomEl.childElementCount > 0) {
    return;
  }
  dismissMapContextMenu();
  tacticalRoomEl.replaceChildren();
  tacticalRoomLastSize = sizeKey;
  const compact =
    typeof state.mapStageHeight === "number" ||
    (shouldUseCombatFocus(session) && viewport.height < 260);
  tacticalRoomViewportEl.classList.toggle("tactical-room-compact", compact);
  const cell = tacticalRoomCellSize(viewport, width, height);
  const cellOwnership = buildMapCellOwnership(session);
  const stage = node("div", "tactical-room-stage");
  stage.style.width = `${width * cell}px`;
  stage.style.height = `${height * cell}px`;
  stage.style.setProperty("--cell", `${cell}px`);
  const tileEl = node("div", `tactical-tile ${tile.tile_type || "room"}`);
  tileEl.style.width = "100%";
  tileEl.style.height = "100%";
  if (tile.image) tileEl.appendChild(mapImageLayer(tile, cell, width, height, cellOwnership, session));
  tileEl.appendChild(tileOverlay(tile, session, cellOwnership, { skipContentMarkers: true }));
  const tokenLayer = node("div", "tactical-token-layer");
  const livingFoes = (tile.enemies || []).filter((foe) => foe.life > 0);
  const foeLabels = buildFoeDisplayLabels(tile.enemies || []);
  const layout = computeTacticalTokenLayout(session, tile, width, height);
  const renderedStacks = new Set();
  const slotUsed = new Map();
  const cellTotals = new Map();
  const cellKey = (cell) => `${cell.x},${cell.y}`;
  const countPlacements = () => {
    for (const cell of layout.heroSlots.values()) {
      const key = cellKey(cell);
      cellTotals.set(key, (cellTotals.get(key) || 0) + 1);
    }
    for (const foe of livingFoes) {
      const cell = layout.foeSlots.get(foe.id);
      if (!cell) continue;
      const key = cellKey(cell);
      const stack = layout.foeStacks.get(key);
      if (stack?.length > 1) {
        if (!cellTotals.has(`${key}-foe-stack`)) {
          cellTotals.set(key, (cellTotals.get(key) || 0) + 1);
          cellTotals.set(`${key}-foe-stack`, 1);
        }
      } else {
        cellTotals.set(key, (cellTotals.get(key) || 0) + 1);
      }
    }
  };
  countPlacements();
  const nextSlot = (cell) => {
    const key = cellKey(cell);
    const index = slotUsed.get(key) || 0;
    slotUsed.set(key, index + 1);
    return { index, total: cellTotals.get(key) || 1 };
  };
  for (const member of session.party || []) {
    const cell = layout.heroSlots.get(member.character_id);
    if (!cell) continue;
    const { index, total } = nextSlot(cell);
    tokenLayer.appendChild(
      buildTacticalHeroToken(session, tile, member, cell, width, height, livingFoes, index, total)
    );
  }
  for (const foe of livingFoes) {
    const cell = layout.foeSlots.get(foe.id);
    if (!cell) continue;
    const stackKey = `${cell.x},${cell.y}`;
    const stack = layout.foeStacks.get(stackKey);
    if (stack?.length > 1) {
      if (renderedStacks.has(stackKey)) continue;
      renderedStacks.add(stackKey);
      const { index, total } = nextSlot(cell);
      tokenLayer.appendChild(
        buildTacticalFoeToken(session, tile, stack[0], cell, width, height, foeLabels, stack.length, index, total)
      );
      continue;
    }
    const { index, total } = nextSlot(cell);
    tokenLayer.appendChild(
      buildTacticalFoeToken(session, tile, foe, cell, width, height, foeLabels, 1, index, total)
    );
  }
  tileEl.appendChild(tokenLayer);
  stage.appendChild(tileEl);
  stage.appendChild(node("div", "tactical-formation-hint", tacticalFormationHint(session, tile)));
  tacticalRoomEl.appendChild(stage);
}

function renderCombatHeroChips(session) {
  if (!combatHeroChipsEl || !shouldUseCombatFocus(session)) return;
  combatHeroChipsEl.replaceChildren();
  const tile = currentTile(session);
  const members = [...(session.party || [])].sort((left, right) => left.marching_order - right.marching_order);
  for (const member of members) {
    const chip = node(
      "button",
      `combat-hero-chip${member.current_life <= 0 ? " fallen" : ""}${state.combatHeroDrawerId === member.character_id ? " selected" : ""}`
    );
    chip.type = "button";
    chip.title = partySheetSummaryLine(member, session, tile);
    chip.appendChild(node("span", "combat-hero-chip-order", `#${member.marching_order}`));
    chip.appendChild(node("span", "combat-hero-chip-name", member.name));
    chip.appendChild(
      node("span", "combat-hero-chip-hp", `${member.current_life}/${member.max_life}`)
    );
    chip.appendChild(node("span", "combat-hero-chip-plan muted", heroCombatPlanLabel(session, member, tile)));
    chip.addEventListener("click", () => {
      if (state.combatCinema) {
        openCombatHeroMenu(session, tile, member, chip, livingFoesOnTile(session));
        return;
      }
      toggleCombatHeroDrawer(member.character_id, session);
    });
    combatHeroChipsEl.appendChild(chip);
  }
}

function renderCombatHeroDrawer(session) {
  if (!combatHeroDrawerEl || !shouldUseCombatFocus(session)) return;
  combatHeroDrawerEl.replaceChildren();
  if (!state.combatHeroDrawerId) {
    combatHeroDrawerEl.classList.add("hidden");
    combatHeroDrawerResizerEl?.classList.add("hidden");
    return;
  }
  combatHeroDrawerEl.classList.remove("hidden");
  combatHeroDrawerResizerEl?.classList.remove("hidden");
  const member = (session.party || []).find((entry) => entry.character_id === state.combatHeroDrawerId);
  if (!member) {
    state.combatHeroDrawerId = null;
    combatHeroDrawerEl.classList.add("hidden");
    return;
  }
  const tile = currentTile(session);
  const head = node("div", "combat-hero-drawer-head");
  head.appendChild(node("strong", "", `#${member.marching_order} ${member.name}`));
  const closeBtn = node("button", "secondary", "Close");
  closeBtn.type = "button";
  closeBtn.addEventListener("click", () => toggleCombatHeroDrawer(member.character_id, session));
  head.appendChild(closeBtn);
  combatHeroDrawerEl.appendChild(head);
  const body = node("div", "combat-hero-drawer-body party-sheet-body");
  const inventoryPanel = buildMemberInventoryPanel(member);
  body.appendChild(inventoryPanel);
  body.appendChild(
    subline(
      `HP ${member.current_life}/${member.max_life} | Gold ${member.gold} | XP ${member.xp} | L${member.level} | Clues ${member.clues || 0}`
    )
  );
  appendStatusChips(body, heroStatusChips(session, member, tile));
  body.appendChild(subline(heroCombatPlanLabel(session, member, tile)));
  const livingFoes = livingFoesOnTile(session);
  if (session.mode === "combat" && member.current_life > 0 && livingFoes.length) {
    appendHeroCombatPlanningRows(body, session, member, tile, livingFoes);
  }
  const actions = node("div", "combat-hero-drawer-actions member-sheet-actions");
  appendMemberSheetHeaderActions(actions, session, member, inventoryPanel);
  if (session.mode === "combat" && member.current_life > 0) {
    appendMemberCombatActions(actions, session, member, tile, livingFoes, reactionsOpen(session));
  } else {
    appendMemberExplorationActions(body, session, member, tile);
  }
  body.appendChild(actions);
  combatHeroDrawerEl.appendChild(body);
}

function renderCombatDeckSlim(session) {
  if (!combatDeckSlimEl || !shouldUseCombatFocus(session)) return;
  const pendingEncounter = encounterPending(session);
  const inCombat = session.mode === "combat";
  combatDeckSlimEl.replaceChildren();
  const tile = currentTile(session);
  const livingFoes = livingFoesOnTile(session);
  const reactionsPending = reactionsOpen(session);
  const immediateLocked = surpriseReactionLocked(session);
  const withdrawDoors = combatWithdrawDoorOptions(session, tile);
  if (withdrawDoors.length) {
    const valid = withdrawDoors.some((exit) => exit.id === state.combatWithdrawExitId);
    if (!valid) state.combatWithdrawExitId = withdrawDoors[0].id;
  } else {
    state.combatWithdrawExitId = null;
  }

  const title = node("div", "combat-deck-title", inCombat ? "Combat" : "Encounter");
  const scroll = node("div", "combat-deck-scroll");
  scroll.appendChild(title);

  const status = node("div", "combat-deck-status");
  renderCombatPhaseSteps(session, status);
  const statusLine = node("div", "combat-panel-status-line");
  if (session.reaction_checked && session.reaction_key === "fight") {
    statusLine.textContent = "Foes attack! They may strike first this round.";
  } else if (session.foe_flee_strike_pending) {
    statusLine.textContent = "Foes are fleeing! Resolve Round to strike them once (+1 Attack).";
  } else if (!reactionsPending && !["bribe", "trade_information"].includes(session.reaction_key || "")) {
    statusLine.textContent = combatRoundStatusText(session);
  } else if (reactionsPending) {
    statusLine.textContent = surpriseReactionLocked(session)
      ? "Surprised: Check Reactions before any party action (p.146)."
      : "Choose: Check Reactions, or immediate action with Fight Round / a combat spell (p.146).";
  } else if (pendingEncounter && !inCombat) {
    statusLine.textContent = "Legacy encounter pause: enter the encounter to resolve foes under p.146.";
  }
  if (statusLine.textContent) status.appendChild(statusLine);
  scroll.appendChild(status);

  if (inCombat && livingFoes.length) {
    const preview = node("div", "combat-deck-preview");
    const foeLabels = buildFoeDisplayLabels(tile?.enemies || []);
    const roundPlan = renderCombatRoundPlan(session, tile, livingFoes, foeLabels, reactionsPending);
    if (roundPlan) preview.appendChild(roundPlan);
    if (preview.childElementCount) scroll.appendChild(preview);
  }

  combatDeckSlimEl.appendChild(scroll);

  const bribeOutstanding = inCombat && session.reaction_key === "bribe";
  const tradeInfoOutstanding = inCombat && session.reaction_key === "trade_information";
  const actionRow = node("div", "combat-deck-actions combat-deck-actions-sticky");
  if (pendingEncounter && !inCombat) {
    const start = node("button", "", "Start Combat");
    start.type = "button";
    setButtonTooltip(start, ACTION_TOOLTIPS.startCombat);
    start.addEventListener("click", () => advance("start_combat"));
    actionRow.appendChild(start);
  }
  if (reactionsPending) {
    const react = node("button", "secondary", "Check Reactions");
    react.type = "button";
    setButtonTooltip(react, ACTION_TOOLTIPS.checkReaction);
    react.addEventListener("click", () => advance("check_reaction"));
    actionRow.appendChild(react);
  }
  if (bribeOutstanding) {
    const pay = node("button", "secondary", `Pay Bribe (${formatBribeRequirement(session)})`);
    pay.type = "button";
    pay.disabled = !canAffordBribe(session);
    setButtonTooltip(pay, ACTION_TOOLTIPS.payBribe);
    pay.addEventListener("click", () => advance("pay_bribe", { pay_bribe: true }));
    actionRow.appendChild(pay);
    const decline = node("button", "secondary", "Refuse Bribe");
    decline.type = "button";
    setButtonTooltip(decline, ACTION_TOOLTIPS.declineBribe);
    decline.addEventListener("click", () => advance("pay_bribe", { pay_bribe: false }));
    actionRow.appendChild(decline);
  }
  if (tradeInfoOutstanding) {
    const clueCount = session.clues_found || 0;
    const sell = node("button", "secondary", `Sell Info (${clueCount * 25}gp)`);
    sell.type = "button";
    sell.disabled = clueCount <= 0;
    setButtonTooltip(sell, ACTION_TOOLTIPS.tradeInfoSell);
    sell.addEventListener("click", () => advance("trade_information", { trade_information_choice: "sell" }));
    actionRow.appendChild(sell);
    const buy = node("button", "secondary", "Buy Clue (100gp)");
    buy.type = "button";
    buy.disabled = partyGoldTotal(session) < 100;
    setButtonTooltip(buy, ACTION_TOOLTIPS.tradeInfoBuy);
    buy.addEventListener("click", () => advance("trade_information", { trade_information_choice: "buy" }));
    actionRow.appendChild(buy);
    const decline = node("button", "secondary", "Refuse Trade");
    decline.type = "button";
    setButtonTooltip(decline, ACTION_TOOLTIPS.tradeInfoDecline);
    decline.addEventListener("click", () => advance("trade_information", { trade_information_choice: "decline" }));
    actionRow.appendChild(decline);
  }
  if (inCombat) {
    const resolve = node("button", "", combatRoundButtonLabel(session));
    resolve.type = "button";
    setButtonTooltip(
      resolve,
      immediateActionTooltip(session, "Resolve melee and missile attacks for this round. Spells are cast separately.")
    );
    resolve.disabled = !livingFoes.length || immediateLocked;
    resolve.addEventListener("click", () => resolveCombatRound());
    actionRow.appendChild(resolve);
    const flee = node("button", "secondary", "Flee");
    flee.type = "button";
    flee.disabled = immediateLocked;
    setButtonTooltip(flee, immediateLocked ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee) : ACTION_TOOLTIPS.flee);
    flee.addEventListener("click", () => advance("flee"));
    actionRow.appendChild(flee);
    const luckHalfling = halflingForLuckFlee(session);
    if (luckHalfling) {
      const fleeLuck = node("button", "secondary", "Flee (Luck)");
      fleeLuck.type = "button";
      fleeLuck.disabled = immediateLocked;
      setButtonTooltip(
        fleeLuck,
        immediateLocked
          ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee)
          : `${luckHalfling.name} spends 1 Luck so the party flees without parting blows.`
      );
      fleeLuck.addEventListener("click", () =>
        advance("flee", { use_luck_flee: true, character_id: luckHalfling.character_id })
      );
      actionRow.appendChild(fleeLuck);
    }
    const withdraw = node("button", "secondary", "Withdraw");
    withdraw.type = "button";
    withdraw.disabled = !withdrawDoors.length || immediateLocked;
    setButtonTooltip(
      withdraw,
      immediateLocked
        ? immediateActionTooltip(session, ACTION_TOOLTIPS.withdraw)
        : withdrawDoors.length
          ? ACTION_TOOLTIPS.withdraw
          : "Withdraw requires an open door to a visited tile."
    );
    withdraw.addEventListener("click", () => combatWithdrawBtn?.click());
    actionRow.appendChild(withdraw);
    if (withdrawDoors.length > 1) {
      const doorSelect = document.createElement("select");
      for (const exit of withdrawDoors) {
        const option = document.createElement("option");
        option.value = exit.id;
        option.textContent = exit.label || `${exit.direction} door`;
        doorSelect.appendChild(option);
      }
      doorSelect.value = state.combatWithdrawExitId || withdrawDoors[0].id;
      doorSelect.addEventListener("change", () => {
        state.combatWithdrawExitId = doorSelect.value;
      });
      actionRow.appendChild(doorSelect);
    }
    const wantsCapture = session.active_quest?.key === "bring_alive" && !session.active_quest?.completed;
    if (wantsCapture) {
      const subdual = node("label", "combat-deck-subdual inline-check");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = Boolean(subdualInput?.checked ?? true);
      input.addEventListener("change", () => {
        if (subdualInput) subdualInput.checked = input.checked;
      });
      subdual.appendChild(input);
      subdual.appendChild(document.createTextNode(" Subdual damage"));
      actionRow.appendChild(subdual);
    }
    for (const member of livingParty(session)) {
      const spells = heroCombatSpells(session, member);
      if (!spells.length) continue;
      const spellBtn = node("button", "secondary", `${member.name.split(" ")[0]}: Spells`);
      spellBtn.type = "button";
      spellBtn.disabled = immediateLocked;
      setButtonTooltip(
        spellBtn,
        immediateActionTooltip(
          session,
          `${spells.length} combat spell${spells.length === 1 ? "" : "s"} available.`
        )
      );
      spellBtn.addEventListener("click", () => openCombatHeroMenu(session, tile, member, spellBtn, livingFoes));
      actionRow.appendChild(spellBtn);
    }
  }
  combatDeckSlimEl.appendChild(actionRow);
  refreshButtonTooltips(actionRow);
}

function menuSectionHeading(label) {
  return { label, disabled: true, heading: true };
}

function appendMenuSection(items, title, sectionItems) {
  if (!sectionItems?.length) return;
  items.push(menuSectionHeading(title));
  items.push(...sectionItems);
}

function renderCombatFloatDeck(session) {
  if (!combatFloatDeckEl) return;
  // Side rail replaces the floating pill in combat focus (including cinema).
  const active = false;
  combatFloatDeckEl.classList.toggle("hidden", !active);
  if (!active) {
    combatFloatDeckEl.replaceChildren();
    return;
  }
  combatFloatDeckEl.replaceChildren();
  const inCombat = session.mode === "combat";
  const pending = encounterPending(session);
  if (inCombat) {
    const phase = node("div", "combat-float-phase", combatRoundStatusText(session));
    combatFloatDeckEl.appendChild(phase);
  }
  if (inCombat || pending) {
    combatFloatDeckEl.appendChild(
      node(
        "div",
        "combat-float-hint",
        "Fight Round is melee/missiles only. Spells cast immediately from token menus or party sheet — not from Fight Round."
      )
    );
  }
  const actions = node("div", "combat-float-actions");
  if (pending && !inCombat) {
    const start = node("button", "", "Start Combat");
    start.type = "button";
    setButtonTooltip(start, ACTION_TOOLTIPS.startCombat);
    start.addEventListener("click", () => advance("start_combat"));
    actions.appendChild(start);
  }
  if (inCombat && reactionsOpen(session)) {
    const react = node("button", "secondary", "Check Reactions");
    react.type = "button";
    setButtonTooltip(react, ACTION_TOOLTIPS.checkReaction);
    react.addEventListener("click", () => advance("check_reaction"));
    actions.appendChild(react);
  }
  if (inCombat) {
    const resolve = node("button", "", combatRoundButtonLabel(session));
    resolve.type = "button";
    setButtonTooltip(
      resolve,
      immediateActionTooltip(session, "Resolve melee and missile attacks for this round. Spells are cast separately.")
    );
    resolve.disabled = !livingFoesOnTile(session).length || immediateLocked;
    resolve.addEventListener("click", () => resolveCombatRound());
    actions.appendChild(resolve);
    const tile = currentTile(session);
    const livingFoes = livingFoesOnTile(session);
    for (const member of livingParty(session)) {
      const spells = heroCombatSpells(session, member);
      if (!spells.length) continue;
      const spellBtn = node("button", "secondary", `${member.name.split(" ")[0]}: Spells`);
      spellBtn.type = "button";
      spellBtn.disabled = immediateLocked;
      setButtonTooltip(
        spellBtn,
        immediateActionTooltip(
          session,
          `${spells.length} combat spell${spells.length === 1 ? "" : "s"} available.`
        )
      );
      spellBtn.addEventListener("click", () => openCombatHeroMenu(session, tile, member, spellBtn, livingFoes));
      actions.appendChild(spellBtn);
    }
    const flee = node("button", "secondary", "Flee");
    flee.type = "button";
    flee.disabled = immediateLocked;
    setButtonTooltip(flee, immediateLocked ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee) : ACTION_TOOLTIPS.flee);
    flee.addEventListener("click", () => advance("flee"));
    actions.appendChild(flee);
    const withdraw = node("button", "secondary", "Withdraw");
    withdraw.type = "button";
    const withdrawDoors = combatWithdrawDoorOptions(session, currentTile(session));
    withdraw.disabled = !withdrawDoors.length || immediateLocked;
    setButtonTooltip(
      withdraw,
      immediateLocked
        ? immediateActionTooltip(session, ACTION_TOOLTIPS.withdraw)
        : withdrawDoors.length
          ? ACTION_TOOLTIPS.withdraw
          : "Withdraw requires an open door to a visited tile."
    );
    withdraw.addEventListener("click", () => combatWithdrawBtn?.click());
    actions.appendChild(withdraw);
  }
  combatFloatDeckEl.appendChild(actions);
  refreshButtonTooltips(actions);
}

function renderMapEncounterBanner(session) {
  if (!mapEncounterBannerEl) return;
  const tile = currentTile(session);
  const foes = livingFoesOnTile(session);
  const detachedPending =
    tile && (session.detached_wandering_pending || []).includes(tile.id) && foes.length > 0;
  const pending = (encounterPending(session) || detachedPending) && shouldUseCombatFocus(session);
  mapEncounterBannerEl.classList.toggle("hidden", !pending);
  if (!pending) {
    mapEncounterBannerEl.textContent = "";
    return;
  }
  const summary = foes
    .slice(0, 3)
    .map((foe) => `${foe.name} (${foeLevelLabel(foe)})`)
    .join(", ");
  const extra = foes.length > 3 ? ` +${foes.length - 3} more` : "";
  if (detachedPending) {
    mapEncounterBannerEl.textContent = `Wandering Monsters threaten heroes left behind here (${summary}${extra}). Regroup to enter the encounter with them.`;
    return;
  }
  mapEncounterBannerEl.textContent = `Foes present: ${summary}${extra}. Click foe tokens on the map, or use the Encounter tab.`;
}

function partyStateTarget(session) {
  return partyState;
}

function combatRoundButtonLabel(session) {
  if (encounterPending(session)) return "Start Combat";
  if (session?.mode !== "combat") return "Start Combat";
  if (session?.foe_flee_strike_pending) return "Fight Round (+1 vs fleeing)";
  return "Fight Round";
}

function reactionsOpen(session) {
  return (
    session?.mode === "combat" &&
    (session.combat_round || 0) === 0 &&
    session.reaction_pending &&
    !session.reaction_checked
  );
}

function surpriseReactionLocked(session) {
  return reactionsOpen(session) && Boolean(session?.party_surprised);
}

function immediateActionTooltip(session, baseText) {
  if (surpriseReactionLocked(session)) {
    return "The party is surprised; Check Reactions is mandatory before any party action (p.146).";
  }
  if (reactionsOpen(session)) {
    return `${baseText} This chooses immediate action and skips the Reaction roll (p.146).`;
  }
  return baseText;
}

function livingFoesOnTile(session) {
  const tile = currentTile(session);
  return (tile?.enemies || []).filter((enemy) => enemy.life > 0);
}

function characterAdventureSession(character) {
  const sessionId = character?.active_session_id;
  if (!sessionId) return null;
  const session = state.sessions.find((item) => item.id === sessionId);
  if (!session || session.mode === "complete") return null;
  return session;
}

function characterInActiveAdventure(character) {
  return Boolean(characterAdventureSession(character));
}

function characterAdventureLabel(character) {
  const session = characterAdventureSession(character);
  if (!session) return "";
  const partyName = partyNameById(session.party_id);
  return partyName ? `Gone adventuring with ${partyName}` : "Gone adventuring";
}

function partyHasBusyMembers(party) {
  return (party?.character_ids || []).some((characterId) => {
    const character = state.characters.find((item) => item.id === characterId);
    return character && characterInActiveAdventure(character);
  });
}

function effectiveSessionMode(session) {
  if (session?.mode === "combat" && !livingFoesOnTile(session).length) {
    return "exploration";
  }
  return session?.mode;
}

const SPELLCASTER_CLASS_IDS = new Set(["wizard", "elf", "illusionist", "druid", "cleric"]);

function isSpellcaster(member) {
  return SPELLCASTER_CLASS_IDS.has(String(member?.class_id || "").toLowerCase());
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
    state.spellAimModes = {};
    state.spellFoeTargets = {};
    state.abilityFoeTargets = {};
    return;
  }
  const tile = currentTile(session);
  const living = (tile?.enemies || []).filter((enemy) => enemy.life > 0);
  if (!living.length) {
    state.combatTargets = {};
    state.spellFoeTargets = {};
    state.abilityFoeTargets = {};
    return;
  }
  const defaultTarget = living[0].id;
  const key = combatEncounterKey(session);
  if (state.combatPanelKey !== key) {
    state.combatPanelKey = key;
    state.combatTargets = {};
    state.spellAimModes = {};
    state.spellFoeTargets = {};
    state.abilityFoeTargets = {};
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
      delete state.spellFoeTargets[characterId];
      delete state.spellAimModes[characterId];
    }
  }
  for (const member of session.party || []) {
    if (member.current_life <= 0) continue;
    const pool = spellFoeTargetPool(session, member, living);
    const currentSpellTarget = state.spellFoeTargets[member.character_id];
    if (!currentSpellTarget || !pool.some((foe) => foe.id === currentSpellTarget)) {
      state.spellFoeTargets[member.character_id] = pool[0]?.id || defaultTarget;
    }
    const currentAbilityTarget = state.abilityFoeTargets[member.character_id];
    if (!currentAbilityTarget || !living.some((foe) => foe.id === currentAbilityTarget)) {
      state.abilityFoeTargets[member.character_id] = defaultTarget;
    }
  }
}

function buildCombatAbilitiesPayload() {
  const abilities = {};
  for (const [characterId, choice] of Object.entries(state.combatAbilities || {})) {
    if (choice) abilities[characterId] = choice;
  }
  return Object.keys(abilities).length ? abilities : undefined;
}

function buildCombatGuardTargetsPayload() {
  const guards = {};
  for (const [characterId, allyId] of Object.entries(state.combatGuardTargets || {})) {
    if (allyId) guards[characterId] = allyId;
  }
  return Object.keys(guards).length ? guards : undefined;
}

function rageUsesRemaining(session, member) {
  if (member.class_id !== "barbarian") return 0;
  let maximum = 1 + Math.floor(member.level / 2);
  if (hasExpertSkill(member, "berserk_fury")) maximum += 1;
  return Math.max(0, maximum - (session.rage_uses_spent?.[member.character_id] || 0));
}

function luckPointsRemaining(session, member) {
  if (member.class_id !== "halfling") return 0;
  const maximum = member.level + 1;
  return Math.max(0, maximum - (session.luck_points_spent?.[member.character_id] || 0));
}

function acrobatTricksRemaining(session, member) {
  if (member.class_id !== "acrobat") return 0;
  const maximum = member.level + 3;
  return Math.max(0, maximum - (session.acrobat_tricks_spent?.[member.character_id] || 0));
}

function illusionistSpellSlotsRemaining(session, member) {
  if (member.class_id !== "illusionist") return 0;
  const maximum = member.level + 3;
  const used = (session.expended_spells?.[member.character_id] || []).length;
  return Math.max(0, maximum - used);
}

function acrobatHasThrowableBlade(member) {
  return (member.inventory || []).some((item) => /dagger|knife|blade/i.test(item));
}

function gnomeGadgetsRemaining(session, member) {
  if (member.class_id !== "gnome") return 0;
  const maximum = member.level + 6;
  return Math.max(0, maximum - (session.gnome_gadgets_spent?.[member.character_id] || 0));
}

function inventoryMeleeWeapons(member) {
  return (member.inventory || []).filter((item) => {
    const lower = item.toLowerCase();
    return (
      lower.includes("hand weapon") ||
      lower.includes("light weapon") ||
      lower.includes("heavy weapon") ||
      ["sword", "dagger", "axe", "mace", "staff", "spear", "hammer", "club", "scimitar"].some((word) => lower.includes(word))
    );
  });
}

function weaponStyleCategory(item) {
  const lower = item.toLowerCase();
  if (lower.includes("heavy weapon") || lower.includes("two-handed")) return "two_handed";
  if (lower.includes("light weapon") || lower.includes("dagger") || lower.includes("scimitar")) {
    return lower.includes("mace") || lower.includes("club") ? "light_blunt" : "light_slashing";
  }
  if (lower.includes("mace") || lower.includes("hammer") || lower.includes("club") || lower.includes("staff")) {
    return "hand_blunt";
  }
  return "hand_slashing";
}

function rangerWeaponsCompatible(leftItem, rightItem) {
  const left = weaponStyleCategory(leftItem);
  const right = weaponStyleCategory(rightItem);
  if (left === right && (left === "hand_slashing" || left === "hand_blunt")) return true;
  return (
    (left === "hand_slashing" && right === "light_slashing") ||
    (left === "light_slashing" && right === "hand_slashing")
  );
}

function rangerDualWieldReady(member) {
  if (member.class_id !== "ranger") return false;
  const melee = inventoryMeleeWeapons(member).filter((item) => weaponStyleCategory(item) !== "two_handed");
  for (let i = 0; i < melee.length; i += 1) {
    for (let j = i + 1; j < melee.length; j += 1) {
      const left = weaponStyleCategory(melee[i]);
      const right = weaponStyleCategory(melee[j]);
      if (left === right && (left === "hand_slashing" || left === "hand_blunt")) return true;
      if (
        (left === "hand_slashing" && right === "light_slashing") ||
        (left === "light_slashing" && right === "hand_slashing")
      ) {
        return true;
      }
    }
  }
  return false;
}

function lightGladiatorDualReady(member) {
  if (member.class_id !== "light_gladiator") return false;
  const lights = inventoryMeleeWeapons(member).filter((item) => {
    const lower = item.toLowerCase();
    return lower.includes("light weapon") || lower.includes("dagger") || lower.includes("scimitar");
  });
  return lights.length >= 2;
}

function swashbucklerDualReady(member) {
  if (member.class_id !== "swashbuckler") return false;
  const melee = inventoryMeleeWeapons(member);
  const hands = melee.filter((item) => weaponStyleCategory(item) !== "light_slashing" && weaponStyleCategory(item) !== "light_blunt" && weaponStyleCategory(item) !== "two_handed");
  const lights = melee.filter((item) => {
    const style = weaponStyleCategory(item);
    return style === "light_slashing" || style === "light_blunt";
  });
  return hands.length >= 1 && lights.length >= 1;
}

function tierForLevel(level) {
  return Math.max(1, Math.floor(((level || 1) - 1) / 4) + 1);
}

function mushroomMonkFlurryItemName(name) {
  const lower = String(name || "").toLowerCase();
  if (!lower) return true;
  if (lower.includes("nunchaku")) return true;
  if (lower.includes("throwing star") || lower.includes("shuriken")) return true;
  return false;
}

function mushroomMonkFlurryReady(session, member) {
  if (member.class_id !== "mushroom_monk") return false;
  const wielded =
    session?.wielded_melee_weapons?.[member.character_id] || member.default_melee_weapon || "";
  return mushroomMonkFlurryItemName(wielded);
}

const DUAL_MELEE_CLASS_IDS = new Set(["ranger", "light_gladiator", "swashbuckler"]);

function memberUsesDualMeleeDefaults(member) {
  return DUAL_MELEE_CLASS_IDS.has(member.class_id);
}

function secondaryMeleeOptions(member, primaryMelee) {
  const options = inventoryMeleeWeapons(member).filter((item) => item !== primaryMelee);
  if (member.class_id === "light_gladiator") {
    return options.filter((item) => {
      const lower = item.toLowerCase();
      return lower.includes("light weapon") || lower.includes("dagger") || lower.includes("scimitar");
    });
  }
  if (member.class_id === "swashbuckler") {
    return options.filter((item) => {
      const style = weaponStyleCategory(item);
      return style === "light_slashing" || style === "light_blunt";
    });
  }
  if (member.class_id === "ranger") {
    if (!primaryMelee) return options;
    return options.filter((item) => rangerWeaponsCompatible(primaryMelee, item));
  }
  return [];
}

function tileOutdoors(tile) {
  const terrain = tile?.terrain || "indoor";
  return terrain !== "indoor";
}

function rangerOutdoorBowReady(member, tile) {
  if (member.class_id !== "ranger" || !tileOutdoors(tile)) return false;
  return (member.inventory || []).some((item) => item.toLowerCase().includes("bow"));
}

function mushroomSporesRemaining(session, member) {
  if (member.class_id !== "mushroom_monk") return 0;
  const tier = Math.max(1, Math.floor((member.level - 1) / 4) + 1);
  const used = session.mushroom_spore_uses?.[member.character_id] || 0;
  return Math.max(0, tier - used);
}

function panachePoints(session, member) {
  if (member.class_id !== "swashbuckler") return 0;
  return Math.min(member.level, session.panache_points?.[member.character_id] || 0);
}

function paladinPrayerRemaining(session, member) {
  if (member.class_id !== "paladin") return 0;
  const maximum = member.level + 1;
  return Math.max(0, maximum - (session.paladin_prayer_spent?.[member.character_id] || 0));
}

function abilityStatusLine(session, member) {
  if (member.class_id === "barbarian") {
    const remaining = rageUsesRemaining(session, member);
    if (remaining) return `Rage: ${remaining}/${1 + Math.floor(member.level / 2)}`;
  }
  if (member.class_id === "halfling") {
    const remaining = luckPointsRemaining(session, member);
    if (remaining) return `Luck: ${remaining}/${member.level + 1}`;
  }
  if (member.class_id === "swashbuckler") {
    return `Panache: ${panachePoints(session, member)}/${member.level}`;
  }
  if (member.class_id === "paladin") {
    const remaining = paladinPrayerRemaining(session, member);
    if (remaining) return `Prayer: ${remaining}/${member.level + 1}`;
  }
  if (member.class_id === "light_gladiator") {
    const pending = session.gladiator_counter_pending?.[member.character_id];
    if (pending?.bonus) return `Counter-strike +${pending.bonus} vs marked foe`;
    if (!(session.gladiator_counter_used || []).includes(member.character_id)) {
      return "Counter-strike available";
    }
  }
  if (member.class_id === "mushroom_monk") {
    const parts = [];
    if (mushroomMonkFlurryReady(session, member)) {
      parts.push(`Flurry: ${tierForLevel(member.level)} attack(s)`);
    }
    const spores = mushroomSporesRemaining(session, member);
    if (spores) parts.push(`Spore uses: ${spores}/${tierForLevel(member.level)}`);
    if (parts.length) return parts.join(" · ");
  }
  return null;
}

function buildCombatAbilityChoices(session, member) {
  const choices = [];
  if (rageUsesRemaining(session, member) > 0) choices.push(["rage", "Rage attack"]);
  if (panachePoints(session, member) > 0) {
    choices.push(["panache_attack", "Panache +1 attack"]);
    choices.push(["panache_defense", "Panache +1 defense"]);
  }
  if (luckPointsRemaining(session, member) > 0) choices.push(["luck_attack", "Luck reroll attack"]);
  if (luckPointsRemaining(session, member) > 0) choices.push(["luck_defense", "Luck reroll defense"]);
  if (member.class_id === "gnome" && gnomeGadgetsRemaining(session, member) > 0) {
    choices.push(["gnome_gadget", "Gadget attack (+L)"]);
  }
  if (member.class_id === "acrobat" && acrobatTricksRemaining(session, member) > 0) {
    choices.push(["flip_kick", "Flip Kick"]);
  }
  if (
    member.class_id === "acrobat" &&
    acrobatTricksRemaining(session, member) > 0 &&
    acrobatHasThrowableBlade(member)
  ) {
    choices.push(["acrobat_knife_throw", "Trick: Knife Throw (+Tier)"]);
  }
  if (
    member.class_id === "illusionist" &&
    illusionistSpellSlotsRemaining(session, member) > 0
  ) {
    choices.push(["illusionist_knife_throw", "Illusionary Knife (+Tier+L)"]);
  }
  if (member.class_id === "illusionist") {
    choices.push(["illusionist_continual_light", "Continual Light (forfeit attacks)"]);
  }
  if (member.class_id === "light_gladiator" && lightGladiatorDualReady(member)) {
    choices.push(["gladiator_parry", "Parry (+1 Defense, forgo attacks)"]);
  }
  if (member.class_id === "bulwark" && hasExpertSkill(member, "sacrifice_defense")) {
    choices.push(["bulwark_sacrifice", "Sacrifice Defense (guard ally)"]);
  }
  if (
    member.class_id === "bulwark" &&
    hasExpertSkill(member, "sacrifice_shield") &&
    (member.inventory || []).some((item) => String(item).toLowerCase().includes("shield"))
  ) {
    choices.push(["sacrifice_shield", "Sacrifice Shield (negate one hit)"]);
  }
  if (member.class_id === "paladin" && hasExpertSkill(member, "divine_smite") && !(session?.divine_smite_used || []).includes(member.character_id)) {
    choices.push(["divine_smite", "Divine Smite (3 dmg vs major)"]);
  }
  if (member.class_id === "acrobat" && acrobatTricksRemaining(session, member) > 0) {
    choices.push(["double_kick", "Double Kick (2 minors)"]);
  }
  if (hasExpertSkill(member, "deadly_strike")) {
    choices.push(["deadly_strike", "Deadly Strike (2H double wounds)"]);
  }
  if (hasExpertSkill(member, "double_attack")) {
    choices.push(["double_attack", "Double Attack (2 melee)"]);
  }
  if (hasExpertSkill(member, "protective_incense")) {
    choices.push(["protective_incense", "Protective Incense (+1 vs undead/demons)"]);
  }
  if (hasExpertSkill(member, "whirlwind_of_steel")) {
    choices.push(["whirlwind_of_steel", "Whirlwind of Steel (minion chain)"]);
  }
  if (
    hasExpertSkill(member, "knife_throwing") &&
    (member.inventory || []).some((item) => /dagger|knife|blade/i.test(item))
  ) {
    choices.push(["knife_throwing", "Knife Throw (−1 ranged)"]);
  }
  if (hasExpertSkill(member, "continual_light") && member.class_id === "cleric") {
    choices.push(["continual_light", "Continual Light (forfeit attacks)"]);
  }
  if (hasHeroicSkill(member, "aggressive_stance")) {
    choices.push(["aggressive_stance", "Aggressive Stance (+1 atk, −1 def next round)"]);
  }
  if (hasHeroicSkill(member, "defensive_stance")) {
    choices.push(["defensive_stance", "Defensive Stance (+1 Defense)"]);
  }
  if (hasHeroicSkill(member, "master_strike")) {
    choices.push(["master_strike", "Master Strike (+1 wound, once/encounter)"]);
  }
  if (hasHeroicSkill(member, "double_shot") && !(session?.expert_encounter_spent?.[member.character_id] || []).includes("double_shot")) {
    choices.push(["double_shot", "Double Shot (2 missiles, once/encounter)"]);
  }
  if (
    hasHeroicSkill(member, "mass_blessing") &&
    !session?.mass_blessing_used &&
    member.class_id === "cleric"
  ) {
    choices.push(["mass_blessing", "Mass Blessing (+1 atk all allies, once/adventure)"]);
  }
  if (
    (hasHeroicSkill(member, "ward_of_protection") || hasLegendarySkill(member, "legendary_ward_of_protection")) &&
    !(session?.expert_encounter_spent?.[member.character_id] || []).includes("ward_of_protection")
  ) {
    choices.push(["ward_of_protection", "Ward of Protection (ally +Defense, once/encounter)"]);
  }
  if (
    hasHeroicSkill(member, "restore") &&
    member.class_id === "cleric" &&
    !(session?.expert_encounter_spent?.[member.character_id] || []).includes("restore")
  ) {
    choices.push(["restore", "Restore (heal ally 1 Life, once/encounter)"]);
  }
  return choices;
}

function combatAbilityDisplayLabel(session, member) {
  const choice = state.combatAbilities?.[member.character_id];
  if (!choice) return null;
  const match = buildCombatAbilityChoices(session, member).find(([value]) => value === choice);
  return match ? match[1] : choice.replace(/_/g, " ");
}

function combatWithdrawDoorOptions(session, tile) {
  return playerFacingExits(session, tile).filter(
    (exit) => exit.kind === "door" && exit.destination_tile_id && exit.door_open
  );
}

function combatPhaseSteps(session) {
  const reactionsPending = reactionsOpen(session);
  if (reactionsPending) {
    return { current: "reactions", steps: ["Reactions", "Plan round", "Resolve"] };
  }
  if (session.reaction_key === "bribe") {
    return { current: "bribe", steps: ["Reactions", "Bribe", "Resolve"] };
  }
  if (session.reaction_key === "trade_information") {
    return { current: "trade", steps: ["Reactions", "Trade", "Resolve"] };
  }
  return { current: "resolve", steps: ["Reactions", "Plan round", "Resolve"] };
}

function renderCombatPhaseSteps(session, container) {
  const { current, steps } = combatPhaseSteps(session);
  const stepIds =
    session.reaction_key === "bribe" && !reactionsOpen(session)
      ? ["reactions", "bribe", "resolve"]
      : session.reaction_key === "trade_information" && !reactionsOpen(session)
        ? ["reactions", "trade", "resolve"]
      : ["reactions", "plan", "resolve"];
  const row = node("div", "combat-phase-steps");
  steps.forEach((label, index) => {
    row.appendChild(node("span", `combat-phase-step${stepIds[index] === current ? " active" : ""}`, label));
    if (index < steps.length - 1) row.appendChild(node("span", "combat-phase-arrow", "→"));
  });
  container.appendChild(row);
}

function renderCombatRoundPlan(session, tile, livingFoes, foeLabels, reactionsPending) {
  const livingHeroes = (session.party || []).filter((member) => member.current_life > 0);
  if (!livingHeroes.length || !livingFoes.length) return null;
  const block = node("div", "combat-round-plan");
  block.appendChild(
    node(
      "div",
      "combat-section-label",
      reactionsPending ? "Planned targets (if you fight this round)" : "This round's plan"
    )
  );
  const list = node("div", "combat-attack-preview");
  for (const member of livingHeroes.sort((left, right) => left.marching_order - right.marching_order)) {
    const targetId = state.combatTargets[member.character_id] || livingFoes[0]?.id;
    const foe = livingFoes.find((entry) => entry.id === targetId);
    const foeLabel = foe ? foeLabels.get(foe.id) || foe.name : "—";
    const plan = heroCombatPlanLabel(session, member, tile);
    const ability = combatAbilityDisplayLabel(session, member);
    const parts = [`#${member.marching_order} ${member.name} → ${foeLabel}`, plan];
    if (ability) parts.push(ability);
    list.appendChild(node("div", "combat-attack-preview-row", parts.join(" · ")));
  }
  block.appendChild(list);
  if (!shouldUseCombatFocus(session)) {
    block.appendChild(
      node(
        "div",
        "combat-preview-hint muted",
        "Spells, potions, and class abilities are on each party sheet below."
      )
    );
  }
  return block;
}

function appendCombatSelectRow(parent, labelText, select) {
  const row = node("div", "combat-target-row");
  row.appendChild(document.createTextNode(`${labelText}:`));
  row.appendChild(select);
  parent.appendChild(row);
}

function renderCombatHeroRows(session, tile, livingFoes) {
  if (!combatHeroesEl) return;
  combatHeroesEl.replaceChildren();
  const livingHeroes = (session.party || [])
    .filter((member) => member.current_life > 0)
    .sort((left, right) => left.marching_order - right.marching_order);
  if (!livingHeroes.length) {
    combatHeroesEl.appendChild(node("div", "muted", "No living heroes."));
    return;
  }
  combatHeroesEl.appendChild(node("div", "combat-section-label", "Heroes"));
  for (const member of livingHeroes) {
    const row = node("div", "combat-hero-row clickable");
    row.setAttribute("role", "button");
    row.tabIndex = 0;
    row.title = `${member.name} — click for combat actions`;
    const openHeroMenu = (event) => {
      event.preventDefault();
      event.stopPropagation();
      openCombatHeroMenu(session, tile, member, row, livingFoes);
    };
    row.addEventListener("click", openHeroMenu);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") openHeroMenu(event);
    });
    const header = node("div", "combat-hero-header");
    header.appendChild(node("span", "combat-hero-name", `#${member.marching_order} ${member.name}`));
    header.appendChild(
      node("span", "combat-hero-stats", `Life ${member.current_life}/${member.max_life} · L${member.level}`)
    );
    row.appendChild(header);
    row.appendChild(node("div", "combat-hero-meta muted", heroCombatPlanLabel(session, member, tile)));
    const actions = node("div", "combat-hero-actions");
    if (livingFoes.length) {
      const targetSelect = document.createElement("select");
      targetSelect.dataset.characterId = member.character_id;
      for (const foe of livingFoes) {
        const option = document.createElement("option");
        option.value = foe.id;
        option.textContent = `${foeDisplayName(livingFoes, foe)} (${foeLevelLabel(foe)})`;
        targetSelect.appendChild(option);
      }
      targetSelect.value = state.combatTargets[member.character_id] || livingFoes[0].id;
      targetSelect.addEventListener("change", () => {
        state.combatTargets[member.character_id] = targetSelect.value;
        renderSession();
      });
      appendCombatSelectRow(actions, "Target", targetSelect);
      const abilityChoices = buildCombatAbilityChoices(session, member);
      if (abilityChoices.length) {
        const abilitySelect = document.createElement("select");
        abilitySelect.dataset.characterId = member.character_id;
        const none = document.createElement("option");
        none.value = "";
        none.textContent = "None";
        abilitySelect.appendChild(none);
        for (const [value, label] of abilityChoices) {
          const option = document.createElement("option");
          option.value = value;
          option.textContent = label;
          abilitySelect.appendChild(option);
        }
        abilitySelect.value = state.combatAbilities[member.character_id] || "";
        abilitySelect.addEventListener("change", () => {
          if (abilitySelect.value) state.combatAbilities[member.character_id] = abilitySelect.value;
          else delete state.combatAbilities[member.character_id];
          renderSession();
        });
        appendCombatSelectRow(actions, "Ability", abilitySelect);
      }
      if (
        member.class_id === "bulwark" &&
        state.combatAbilities?.[member.character_id] === "bulwark_sacrifice"
      ) {
        const guardSelect = document.createElement("select");
        guardSelect.dataset.characterId = member.character_id;
        const allies = (session.party || []).filter(
          (entry) => entry.character_id !== member.character_id && entry.current_life > 0
        );
        for (const ally of allies) {
          const option = document.createElement("option");
          option.value = ally.character_id;
          option.textContent = ally.name;
          guardSelect.appendChild(option);
        }
        guardSelect.value =
          state.combatGuardTargets?.[member.character_id] || guardSelect.options[0]?.value || "";
        guardSelect.addEventListener("change", () => {
          state.combatGuardTargets = state.combatGuardTargets || {};
          state.combatGuardTargets[member.character_id] = guardSelect.value;
        });
        appendCombatSelectRow(actions, "Guard", guardSelect);
      }
    }
    row.appendChild(actions);
    combatHeroesEl.appendChild(row);
  }
}

function halflingForLuckFlee(session) {
  return (session.party || []).find(
    (member) => member.class_id === "halfling" && member.current_life > 0 && luckPointsRemaining(session, member) > 0
  );
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
  if (state.combatAbilities?.[member.character_id] === "gladiator_parry") {
    return "Parry (+1 Defense vs melee)";
  }
  if (heroWillUseMissile(session, member, tile)) {
    if (rangerOutdoorBowReady(member, tile)) return "Double bow shot (outdoors)";
    return "Missile this round";
  }
  if (heroCanMeleeInCombat(session, member, tile)) {
    if (rangerDualWieldReady(member)) return "Dual wield melee";
    if (lightGladiatorDualReady(member)) return "Dual light weapons";
    if (swashbucklerDualReady(member)) return "Main hand + off-hand";
    if (mushroomMonkFlurryReady(session, member)) {
      return `Flurry (${tierForLevel(member.level)} melee attacks)`;
    }
    return "Melee this round";
  }
  const tileType = tile?.tile_type || "room";
  if (tileType === "corridor") {
    return tile?.wandering_ambush && session.combat_round === 0
      ? "Rear rank only (ambush)"
      : member.marching_order <= 2
        ? "Front melee this round"
        : hasMissileWeapon(member)
          ? "Rear missile this round"
          : "Rear rank (no missile weapon)";
  }
  return "No attack";
}

function foeMatchesKeyword(enemy, keywords) {
  const tags = new Set((enemy.tags || []).map((tag) => tag.toLowerCase()));
  const name = (enemy.name || "").toLowerCase();
  return keywords.some((keyword) => tags.has(keyword) || name.includes(keyword));
}

function isHatedByFoes(member, enemies) {
  const classId = (member.class_id || "").toLowerCase();
  if (classId === "dwarf" && enemies.some((enemy) => foeMatchesKeyword(enemy, ["goblin", "kobold", "troll"]))) {
    return true;
  }
  if (classId === "elf" && enemies.some((enemy) => foeMatchesKeyword(enemy, ["orc"]))) {
    return true;
  }
  if (classId === "cleric" && enemies.some((enemy) => (enemy.tags || []).map((tag) => tag.toLowerCase()).includes("undead"))) {
    return true;
  }
  return false;
}

function livingPartySorted(party) {
  return [...(party || [])]
    .filter((member) => member.current_life > 0)
    .sort((left, right) => left.marching_order - right.marching_order);
}

function previewEnemyAttacks(session, tile) {
  const enemies = (tile?.enemies || []).filter((enemy) => enemy.life > 0);
  const living = livingPartySorted(session.party);
  if (!living.length || !enemies.length) return [];

  const tileType = tile?.tile_type || "room";
  const wanderingAmbush = Boolean(tile?.wandering_ambush && (session.combat_round || 0) === 0);

  if (tileType === "corridor") {
    const positions = wanderingAmbush ? new Set([3, 4]) : new Set([1, 2]);
    const eligible = living.filter((member) => positions.has(member.marching_order));
    const pool = eligible.length ? eligible : living.slice(0, 2);
    const attackers = enemies.slice(0, 2);
    const pairs = [];
    for (const enemy of attackers) {
      const repeat = Math.max(1, enemy.attacks || 1);
      for (let index = 0; index < repeat; index += 1) {
        pairs.push({ enemy, target: pool[index % pool.length] });
      }
    }
    return pairs;
  }

  const strikes = [];
  for (const enemy of enemies) {
    const repeat = Math.max(1, enemy.attacks || 1);
    for (let index = 0; index < repeat; index += 1) {
      strikes.push(enemy);
    }
  }

  if (strikes.length <= living.length) {
    return strikes.map((enemy, index) => ({ enemy, target: living[index % living.length] }));
  }

  const targets = [];
  for (const member of living) {
    for (let index = 0; index < Math.floor(strikes.length / living.length); index += 1) {
      targets.push(member);
    }
  }
  const hated = living.filter((member) => isHatedByFoes(member, enemies));
  const pool = hated.length ? hated : living;
  while (targets.length < strikes.length) {
    targets.push(pool[targets.length % pool.length]);
  }
  return strikes.map((enemy, index) => ({ enemy, target: targets[index] }));
}

function combatContextNotes(session, tile) {
  const notes = [];
  const tileType = tile?.tile_type || "room";
  if (tileType === "corridor" && tile?.wandering_ambush && (session.combat_round || 0) === 0) {
    notes.push("Wandering ambush: rear rank (#3–#4) is attacked this round; shields do not apply (p.54).");
  } else if (tileType === "corridor") {
    notes.push(
      "Corridor: rear (#3–#4) may shoot; front (#1–#2) melees; foes attack front rank (#1–#2) unless this is a wandering ambush."
    );
  }
  if (session.foes_strike_first) {
    notes.push("Foes strike first this round.");
  }
  if (session.party_surprised && (session.combat_round || 0) === 0) {
    notes.push("Party is surprised — Check Reactions first; hostile foes act before party actions (p.146).");
  }
  if ((session.summoned_beast_life || 0) > 0) {
    notes.push(
      `Summoned beast: ${session.summoned_beast_life} Life remaining (1 claw/round, foes hit it on L3+).`
    );
  }
  if ((session.druid_companion_life || 0) > 0) {
    const kind = (session.druid_companion_kind || "wolf").replace(/^./, (c) => c.toUpperCase());
    notes.push(
      `Druid companion (${kind}): ${session.druid_companion_life}/${session.druid_companion_max_life || session.druid_companion_life} Life, L${session.druid_companion_level || 3}.`
    );
  }
  return notes;
}

function heroStatusChips(session, member, tile) {
  const chips = [];
  for (const status of member.statuses || []) {
    const lower = status.toLowerCase();
    if (lower.startsWith("poisoned")) {
      chips.push({ label: status, kind: "danger" });
    } else if (
      lower === "protection" ||
      lower === "barkskin" ||
      lower.startsWith("mirror image") ||
      lower.includes("illusionary armor") ||
      lower === "bear form" ||
      lower.includes("specter")
    ) {
      chips.push({ label: status, kind: "buff" });
    }
  }
  if (member.character_id === session.cursed_character_id) {
    chips.push({ label: "Cursed (−1 Def)", kind: "danger" });
  }
  if (member.character_id === session.blessed_undead_bonus_character_id) {
    chips.push({ label: "+1 vs undead/demons", kind: "buff" });
  }
  if (member.character_id === session.body_carrier_id) {
    chips.push({ label: "Carrying body (auto-hit)", kind: "danger" });
  }
  const inventory = (member.inventory || []).join(" ").toLowerCase();
  if (inventory.includes("shield") && tileShieldApplies(session, tile)) {
    chips.push({ label: "Shield", kind: "neutral" });
  }
  return chips;
}

function tileShieldApplies(session, tile) {
  if (!tile) return true;
  return !(tile.tile_type === "corridor" && tile.wandering_ambush && (session.combat_round || 0) === 0);
}

function foeStatusLabels(foe) {
  const tags = new Set((foe.tags || []).map((tag) => tag.toLowerCase()));
  const labels = [];
  if (foe.category) {
    labels.push(foe.category.replace(/_/g, " "));
  }
  if (foe.subdued) labels.push("Subdued");
  if (tags.has("poison")) labels.push("Poison");
  if (tags.has("magic_resist") || tags.has("caster")) labels.push("MR +1");
  if (tags.has("undead")) labels.push("Undead");
  if (tags.has("regeneration")) labels.push("Regenerates");
  if (foe.regen_suppressed) labels.push("Regen blocked");
  if (foe.level_drop_applied) labels.push("Bloodied L drop");
  if ((foe.attacks || 1) > 1) labels.push(`${foe.attacks} attacks`);
  return labels;
}

function appendStatusChips(container, chips) {
  if (!chips.length) return;
  const row = node("div", "combat-status-chips");
  for (const chip of chips) {
    row.appendChild(node("span", `combat-chip combat-chip-${chip.kind}`, chip.label));
  }
  container.appendChild(row);
}

function heroCombatSpells(session, member) {
  const usedThisRound = new Set(session?.spell_used_character_ids || []);
  if (usedThisRound.has(member.character_id)) return [];
  return (member.spells || []).filter((spell) => {
    const key = normalizeSpellKey(spell);
    if (COMBAT_BLOCKED_SPELL_KEYS.has(key) && !COMBAT_UTILITY_SPELL_KEYS.has(key)) return false;
    return !spellExpended(session, member, spell);
  });
}

function heroUsableBandages(session, member) {
  if (session.mode === "combat") return [];
  if ((session.bandage_used_character_ids || []).includes(member.character_id)) return [];
  if (member.class_id === "kukla") return [];
  if (member.current_life <= 0) return [];
  return (member.inventory || []).filter((item) => item.toLowerCase().includes("bandage"));
}

function bandageReceivers(session) {
  return (session.party || []).filter(
    (member) =>
      member.current_life > 0 &&
      member.current_life < member.max_life &&
      member.class_id !== "kukla"
  );
}

function heroUsablePotions(session, member) {
  if (!canDrinkPotion(member)) return [];
  const healingUsed = (session.potion_used_character_ids || []).includes(member.character_id);
  return (member.inventory || []).filter((item) => {
    const lower = item.toLowerCase();
    if (!lower.includes("potion")) return false;
    if (lower.includes("healing") && healingUsed) return false;
    return true;
  });
}

function isLanternOilItem(item) {
  return item.toLowerCase().includes("lantern oil");
}

function foeHasRegeneration(foe) {
  return (foe.tags || []).some((tag) => tag.toLowerCase() === "regeneration");
}

function heroUsableLanternOil(session, member, livingFoes) {
  if (session.mode !== "combat") return [];
  if (member.current_life <= 0) return [];
  if (!(livingFoes || []).some(foeHasRegeneration)) return [];
  return (member.inventory || []).filter(isLanternOilItem);
}

function isHolyWaterItem(item) {
  return item.toLowerCase().includes("holy water");
}

function foeIsUndead(foe) {
  const tags = foe.tags || [];
  const name = (foe.name || "").toLowerCase();
  return (
    tags.includes("undead") ||
    name.includes("skeleton") ||
    name.includes("wight") ||
    name.includes("wraith")
  );
}

function heroUsableHolyWater(session, member, livingFoes) {
  if (session.mode !== "combat") return [];
  if (member.class_id === "barbarian" || member.current_life <= 0) return [];
  if (!(livingFoes || []).some(foeIsUndead)) return [];
  return (member.inventory || []).filter(isHolyWaterItem);
}

function isMushroomItem(item) {
  return item.toLowerCase().includes("mushroom");
}

function heroUsableMushrooms(session, member) {
  if (session.mode !== "exploration") return [];
  if (member.current_life <= 0) return [];
  return (member.inventory || []).filter(isMushroomItem);
}

function isAcidVialItem(item) {
  return item.toLowerCase().includes("acid vial");
}

function heroUsableAcidVial(session, member, livingFoes) {
  if (session.mode !== "combat") return [];
  if (member.current_life <= 0) return [];
  if (!(livingFoes || []).length) return [];
  return (member.inventory || []).filter(isAcidVialItem);
}

function heroCanUsePotion(session, member) {
  return heroUsablePotions(session, member).length > 0;
}

function renderCombatPanel(session) {
  if (!combatPanelEl) return;
  const pendingEncounter = encounterPending(session);
  const inCombat = session.mode === "combat";
  const inFocus = shouldUseCombatFocus(session);
  const showDeck = inCombat || (pendingEncounter && inFocus);
  combatPanelEl.classList.toggle("hidden", !showDeck || inFocus);
  combatPanelEl.classList.toggle("encounter-deck", pendingEncounter && !inCombat);
  if (inFocus) {
    renderCombatDeckSlim(session);
    if (!showDeck) state.combatWithdrawExitId = null;
    return;
  }
  if (!showDeck) {
    state.combatWithdrawExitId = null;
    return;
  }

  if (combatPanelTitleEl) {
    combatPanelTitleEl.textContent = inCombat ? "Combat" : "Encounter";
  }
  if (combatStartBtn) {
    combatStartBtn.classList.toggle("hidden", !pendingEncounter || inCombat);
    combatStartBtn.disabled = !pendingEncounter || inCombat;
    setButtonTooltip(combatStartBtn, ACTION_TOOLTIPS.startCombat);
  }
  if (combatResolveBtn) combatResolveBtn.classList.toggle("hidden", !inCombat);
  if (combatFleeBtn) combatFleeBtn?.classList.toggle("hidden", !inCombat);
  if (combatFleeLuckBtn) combatFleeLuckBtn?.classList.toggle("hidden", !inCombat);
  if (combatWithdrawBtn) combatWithdrawBtn?.classList.toggle("hidden", !inCombat);
  if (combatPreviewEl) combatPreviewEl.classList.toggle("hidden", pendingEncounter && !inCombat);
  if (combatHeroesEl) combatHeroesEl.classList.toggle("hidden", pendingEncounter && !inCombat);

  if (pendingEncounter && !inCombat) {
    if (combatPanelStatusEl) {
      combatPanelStatusEl.replaceChildren();
      combatPanelStatusEl.appendChild(
        node(
          "div",
          "combat-panel-status-line",
          "Legacy encounter pause. Enter the encounter, then choose Reactions or immediate action (p.146)."
        )
      );
    }
    if (combatFoesEl) {
      combatFoesEl.replaceChildren();
      combatFoesEl.appendChild(node("div", "combat-section-label", "Foes"));
      const foes = livingFoesOnTile(session);
      const foeLabels = buildFoeDisplayLabels(foes);
      for (const foe of foes) {
        combatFoesEl.appendChild(buildCombatFoeCard(session, currentTile(session), foe, foeLabels, { interactive: true }));
      }
    }
    return;
  }

  if (!inCombat) {
    state.combatWithdrawExitId = null;
    return;
  }

  syncCombatTargets(session);
  syncAllySpellTargets(session);
  const tile = currentTile(session);
  const foes = tile?.enemies || [];
  const livingFoes = foes.filter((enemy) => enemy.life > 0);
  const canResolve = livingFoes.length > 0;
  const reactionsPending = reactionsOpen(session);
  const immediateLocked = surpriseReactionLocked(session);
  const withdrawDoors = combatWithdrawDoorOptions(session, tile);
  if (withdrawDoors.length) {
    const valid = withdrawDoors.some((exit) => exit.id === state.combatWithdrawExitId);
    if (!valid) state.combatWithdrawExitId = withdrawDoors[0].id;
  } else {
    state.combatWithdrawExitId = null;
  }

  if (combatPanelStatusEl) {
    combatPanelStatusEl.replaceChildren();
    renderCombatPhaseSteps(session, combatPanelStatusEl);
    const statusLine = node("div", "combat-panel-status-line");
    if (session.reaction_checked && session.reaction_key === "fight") {
      statusLine.textContent = "Foes attack! They may strike first this round.";
    } else if (session.foe_flee_strike_pending) {
      statusLine.textContent = "Foes are fleeing! Resolve Round to strike them once (+1 Attack).";
    } else if (!reactionsPending && !["bribe", "trade_information"].includes(session.reaction_key || "")) {
      statusLine.textContent = combatRoundStatusText(session);
    } else if (reactionsPending) {
      statusLine.textContent = surpriseReactionLocked(session)
        ? "Surprised: Check Reactions before any party action (p.146)."
        : "Choose: Check Reactions, or immediate action with Fight Round / a combat spell (p.146).";
    }
    if (statusLine.textContent) combatPanelStatusEl.appendChild(statusLine);
  }

  if (combatPreviewEl) {
    combatPreviewEl.replaceChildren();
    const notes = combatContextNotes(session, tile);
    if (notes.length) {
      const notesBlock = node("div", "combat-context-notes");
      for (const note of notes) {
        notesBlock.appendChild(node("div", "combat-context-note", note));
      }
      combatPreviewEl.appendChild(notesBlock);
    }
    if (livingFoes.length) {
      const foeLabels = buildFoeDisplayLabels(foes);
      const roundPlan = renderCombatRoundPlan(session, tile, livingFoes, foeLabels, reactionsPending);
      if (roundPlan) combatPreviewEl.appendChild(roundPlan);
      if (!reactionsPending) {
        const previewPairs = previewEnemyAttacks(session, tile);
        if (previewPairs.length) {
          combatPreviewEl.appendChild(node("div", "combat-section-label", "Expected foe attacks"));
          const list = node("div", "combat-attack-preview");
          for (const pair of previewPairs) {
            const foeLabel = foeLabels.get(pair.enemy.id) || pair.enemy.name;
            list.appendChild(
              node(
                "div",
                "combat-attack-preview-row",
                `${foeLabel} → #${pair.target.marching_order} ${pair.target.name}`
              )
            );
          }
          combatPreviewEl.appendChild(list);
          combatPreviewEl.appendChild(
            node(
              "div",
              "combat-preview-hint muted",
              "Assignment follows rulebook targeting; actual hits depend on defense rolls."
            )
          );
        }
      }
    }
  }

  if (combatFoesEl) {
    combatFoesEl.replaceChildren();
    combatFoesEl.appendChild(node("div", "combat-section-label", "Foes"));
    if (!foes.length) {
      combatFoesEl.appendChild(node("div", "muted", "No foes on this tile."));
    }
    const foeLabels = buildFoeDisplayLabels(foes);
    for (const foe of foes) {
      combatFoesEl.appendChild(buildCombatFoeCard(session, tile, foe, foeLabels, { interactive: inCombat && foe.life > 0 }));
    }
  }

  renderCombatHeroRows(session, tile, livingFoes);

  const resolveLabel = combatRoundButtonLabel(session);
  if (combatResolveBtn) {
    combatResolveBtn.disabled = !canResolve || immediateLocked;
    combatResolveBtn.textContent = resolveLabel;
    setButtonTooltip(
      combatResolveBtn,
      !canResolve
        ? "No living foes remain."
        : inCombat
          ? immediateActionTooltip(session, ACTION_TOOLTIPS.combatRound)
          : ACTION_TOOLTIPS.startCombat
    );
  }
  if (combatFleeBtn) {
    combatFleeBtn.disabled = !inCombat || immediateLocked;
    setButtonTooltip(
      combatFleeBtn,
      immediateLocked ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee) : ACTION_TOOLTIPS.flee
    );
  }
  const luckHalfling = halflingForLuckFlee(session);
  if (combatFleeLuckBtn) {
    combatFleeLuckBtn.disabled = !inCombat || !luckHalfling;
    if (immediateLocked) combatFleeLuckBtn.disabled = true;
    combatFleeLuckBtn.classList.toggle("hidden", !luckHalfling);
    setButtonTooltip(
      combatFleeLuckBtn,
      immediateLocked
        ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee)
        : luckHalfling
          ? `${luckHalfling.name} spends 1 Luck so the party flees without parting blows.`
          : "No halfling Luck available."
    );
  }
  if (combatWithdrawBtn) {
    combatWithdrawBtn.disabled = !inCombat || !withdrawDoors.length || immediateLocked;
    setButtonTooltip(
      combatWithdrawBtn,
      immediateLocked
        ? immediateActionTooltip(session, ACTION_TOOLTIPS.withdraw)
        : withdrawDoors.length
          ? ACTION_TOOLTIPS.withdraw
          : "Withdraw requires an open door to a visited tile."
    );
  }
  let withdrawRow = combatPanelEl.querySelector(".combat-withdraw-row");
  if (withdrawDoors.length > 1) {
    if (!withdrawRow) {
      withdrawRow = node("div", "combat-withdraw-row");
      const actionsEl = combatPanelEl.querySelector(".combat-panel-actions");
      if (actionsEl) actionsEl.parentNode.insertBefore(withdrawRow, actionsEl);
    }
    withdrawRow.replaceChildren();
    withdrawRow.classList.remove("hidden");
    withdrawRow.appendChild(document.createTextNode("Withdraw via: "));
    const doorSelect = document.createElement("select");
    doorSelect.id = "combat-withdraw-door";
    for (const exit of withdrawDoors) {
      const option = document.createElement("option");
      option.value = exit.id;
      option.textContent = exit.label || `${exit.direction} door`;
      doorSelect.appendChild(option);
    }
    doorSelect.value = state.combatWithdrawExitId || withdrawDoors[0].id;
    doorSelect.addEventListener("change", () => {
      state.combatWithdrawExitId = doorSelect.value;
    });
    withdrawRow.appendChild(doorSelect);
  } else if (withdrawRow) {
    withdrawRow.classList.add("hidden");
    withdrawRow.replaceChildren();
  }

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
  combatStatusEl.classList.remove("combat-status-unaffordable");
  if (session.mode !== "combat") return;

  const reactionsPending = reactionsOpen(session);
  if (reactionsPending) {
    combatStatusEl.textContent = surpriseReactionLocked(session)
      ? "Round 0 — surprised; Check Reactions is mandatory before party actions (p.146)."
      : "Round 0 — choose Check Reactions, or immediate action with Fight Round / a combat spell (p.146).";
    combatStatusEl.classList.remove("hidden");
    return;
  }

  if (session.reaction_key === "bribe") {
    const { gold, weapons, canPay } = bribeAffordabilitySummary(session);
    const requirement = formatBribeRequirement(session);
    combatStatusEl.textContent = canPay
      ? `Bribe: ${requirement} (${gold}gp, ${weapons} weapon(s) available).`
      : `Bribe: ${requirement} — cannot afford (${gold}gp, ${weapons} weapon(s)).`;
    combatStatusEl.classList.toggle("combat-status-unaffordable", !canPay);
    combatStatusEl.classList.remove("hidden");
    return;
  }

  if (session.reaction_key === "trade_information") {
    const clues = session.clues_found || 0;
    const gold = partyGoldTotal(session);
    combatStatusEl.textContent = `Trade Information: sell info for ${clues * 25}gp, buy 1 Clue for 100gp (${gold}gp available), or refuse.`;
    combatStatusEl.classList.toggle("combat-status-unaffordable", clues <= 0 && gold < 100);
    combatStatusEl.classList.remove("hidden");
  }
}

const SETUP_TOOLTIPS = {
  createCharacter: "Roll a new hero with the selected class and add them to your roster.",
  addToParty: "Add this hero to the next open party slot.",
  rosterDragHandle: "Drag onto a party slot, or double-click the hero to add quickly.",
  partySlot: "Drop a hero here. Slot number is marching order (#1 leads).",
  removeFromParty: "Remove this hero from the party.",
  healCharacter: "Restore this hero to full Life (home screen only).",
  transferItems: "Move items or gold between heroes on your roster.",
  equipmentShop:
    "Buy gear before an adventure or sell loot using rulebook resale values on the home screen. Roster gold is home bank gold; only dungeon-carried gold is limited to 200gp per hero.",
  weaponDefaults: "Equipment slots — set default melee and missile weapons. Used when a fight starts.",
  deleteCharacter: "Permanently remove this hero from your roster.",
  sortDirection: "Toggle ascending or descending sort for the list below.",
  saveParty: "Save the party name, members, and marching order.",
  cancelPartyEdit: "Discard party edits and exit edit mode.",
  healParty: "Restore all party members to full Life.",
  editParty: "Edit party name, members, or marching order.",
  deleteParty: "Permanently delete this party.",
  marchingUp: "Move this member one step forward in marching order (position 1 leads).",
  marchingDown: "Move this member one step back in marching order (position 4 is rear).",
  startSession: "Begin a new adventure with the selected party, dungeon, and campaign mode.",
  resumeSession: "Return to your in-progress game without starting over.",
  exportPlayerData: "Download all heroes and parties as a JSON backup file.",
  importPlayerData: "Import heroes and parties from a previously exported JSON file.",
  showSetup: "Return to the home screen. Your current session stays in memory until you save or start fresh.",
  loadSave: "Load this saved game and resume the adventure.",
  deleteSave: "Permanently delete this saved game from the server.",
  campaignMode:
    "Classical: XP rolls. Slow and Sure: +1 level after a clean adventure. Old School: XP tally purchases. Slower Advancement: bank XP then roll to advance.",
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

function spellTooltip(spellName, session = null, member = null) {
  const row = spellRow(spellName);
  const parts = [];
  if (row) {
    parts.push(`${row.spell}: ${row.result}`);
  } else {
    parts.push(`Cast ${spellName}. Once per adventure unless noted.`);
  }
  const key = normalizeSpellKey(spellName);
  if (key === "fireball" && session && member) {
    const tile = currentTile(session);
    const livingFoes = (tile?.enemies || []).filter((foe) => foe.life > 0);
    if (livingFoes.length) parts.push(fireballAimHint(member, livingFoes));
  }
  if (key === "lightning") {
    parts.push(
      "Single target: must meet foe Level on spell roll; slays one vermin/minion or 2 Life damage to a boss/weird foe."
    );
  }
  if (key === "sleep") {
    parts.push("No effect on undead, dragons, or foes Level 11+.");
  }
  if (key === "healing_surge") {
    parts.push("All allies except caster heal 2 Life; vampires in play lose 2 Life.");
  }
  if (key === "infallible_missile") {
    parts.push("Auto 1 Life wound; exploding d6 chains to same or another foe. L8+ casts two missiles.");
  }
  if (key === "lifeforce_control") {
    parts.push("Transfer Life from caster to a living ally, or equal damage to a vampire foe.");
  }
  if (key === "mass_teleport") {
    parts.push("Teleport chosen allies to any visited room; caster pays 1 Life per ally moved.");
  }
  if (key === "aura_of_terror") {
    parts.push("Morale d6 ≤3 flees; undead, final bosses, and fear attackers are immune.");
  }
  if (key === "reverse_gaze") {
    parts.push("Blocks gaze on caster; d8 + level vs foe level may turn the gaze back.");
  }
  if (row?.implementation === "partial") {
    parts.push("Partially implemented — spell is consumed but you may need to move manually.");
  } else if (row?.implementation === "yes") {
    parts.push("Fully implemented.");
  } else if (row?.implementation === "no") {
    parts.push("Not yet implemented in the app.");
  }
  if (row?.source_page) {
    parts.push(`Rulebook p.${row.source_page}.`);
  }
  return parts.join(" ");
}

function appendMassTeleportTargeting(container, session, member) {
  const roomRow = node("div", "combat-target-row");
  roomRow.appendChild(document.createTextNode("Teleport to:"));
  const teleportSelect = document.createElement("select");
  for (const tile of session.map_state?.tiles || []) {
    const option = document.createElement("option");
    option.value = tile.id;
    option.textContent = tile.title || tile.id;
    teleportSelect.appendChild(option);
  }
  teleportSelect.value =
    state.teleportTileId?.[member.character_id] ||
    session.map_state?.current_tile_id ||
    teleportSelect.options[0]?.value ||
    "";
  state.teleportTileId[member.character_id] = teleportSelect.value;
  teleportSelect.addEventListener("change", () => {
    state.teleportTileId[member.character_id] = teleportSelect.value;
  });
  roomRow.appendChild(teleportSelect);
  container.appendChild(roomRow);

  const alliesRow = node("div", "combat-target-row spell-teleport-allies");
  alliesRow.appendChild(document.createTextNode("Allies to move:"));
  const living = livingPartyMembers(session);
  if (!state.teleportAllies[member.character_id]) {
    state.teleportAllies[member.character_id] = living.map((ally) => ally.character_id);
  }
  for (const ally of living) {
    const label = node("label", "spell-teleport-ally");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.teleportAllies[member.character_id].includes(ally.character_id);
    checkbox.addEventListener("change", () => {
      const selected = new Set(state.teleportAllies[member.character_id] || []);
      if (checkbox.checked) selected.add(ally.character_id);
      else selected.delete(ally.character_id);
      state.teleportAllies[member.character_id] = [...selected];
    });
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(` ${ally.name}`));
    alliesRow.appendChild(label);
  }
  container.appendChild(alliesRow);
}

function appendSpellTargetingRows(container, session, member, livingFoes, extraSpells = []) {
  const spells = [...heroCombatSpells(session, member), ...extraSpells];
  if (!spells.length) return;
  const foelessOk = new Set(["mass_teleport", "healing_surge", "lifeforce_control"]);
  const allNeedFoes = spells.every((spell) => !foelessOk.has(normalizeSpellKey(spell)));
  if (allNeedFoes && !livingFoes.length) return;

  const hasFireball = spells.some((spell) => normalizeSpellKey(spell) === "fireball");
  if (hasFireball && fireballNeedsAimChoice(livingFoes)) {
    const aimRow = node("div", "combat-target-row");
    aimRow.appendChild(document.createTextNode("Fireball aim:"));
    const aimSelect = document.createElement("select");
    for (const [value, label] of [
      ["minions", "Minions (area slay)"],
      ["single", "Single boss/weird"],
    ]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      aimSelect.appendChild(option);
    }
    aimSelect.value = fireballAimModeFor(session, member, livingFoes) || "minions";
    state.spellAimModes[member.character_id] = aimSelect.value;
    aimSelect.addEventListener("change", () => {
      state.spellAimModes[member.character_id] = aimSelect.value;
      renderSession();
    });
    aimRow.appendChild(aimSelect);
    container.appendChild(aimRow);
  }

  const needsSpellTarget = spells.some((spell) =>
    spellNeedsFoeTargetRow(spell, session, member, livingFoes)
  );
  if (needsSpellTarget) {
    const foeRow = node("div", "combat-target-row");
    foeRow.appendChild(document.createTextNode("Spell target:"));
    const pool = spellFoeTargetPool(session, member, livingFoes);
    foeRow.appendChild(
      createFoeTargetSelect(livingFoes, {
        value: state.spellFoeTargets?.[member.character_id],
        filter: (foe) => pool.some((item) => item.id === foe.id),
        onChange: (foeId) => {
          state.spellFoeTargets[member.character_id] = foeId;
        },
      })
    );
    container.appendChild(foeRow);
  }

  const hasInfallible = spells.some((spell) => normalizeSpellKey(spell) === "infallible_missile");
  if (hasInfallible && member.level >= 8 && livingFoes.length > 1) {
    const secondRow = node("div", "combat-target-row");
    secondRow.appendChild(document.createTextNode("2nd missile:"));
    secondRow.appendChild(
      createFoeTargetSelect(livingFoes, {
        value: state.spellSecondaryFoeTargets?.[member.character_id],
        onChange: (foeId) => {
          state.spellSecondaryFoeTargets[member.character_id] = foeId;
        },
      })
    );
    container.appendChild(secondRow);
  }

  if (spells.some((spell) => normalizeSpellKey(spell) === "lifeforce_control")) {
    const amountRow = node("div", "combat-target-row");
    amountRow.appendChild(document.createTextNode("Life to transfer:"));
    const lifeInput = document.createElement("input");
    lifeInput.type = "number";
    lifeInput.min = "1";
    lifeInput.max = String(Math.max(1, member.current_life));
    lifeInput.value = String(state.spellLifeTransfer?.[member.character_id] || 1);
    lifeInput.className = "spell-life-input";
    lifeInput.addEventListener("change", () => {
      state.spellLifeTransfer[member.character_id] = Math.max(
        1,
        Number.parseInt(lifeInput.value, 10) || 1
      );
    });
    amountRow.appendChild(lifeInput);
    container.appendChild(amountRow);
  }

  if (spells.some((spell) => normalizeSpellKey(spell) === "mass_teleport")) {
    appendMassTeleportTargeting(container, session, member);
  }
}

function appendSpellSubline(container, spells, session = null, member = null) {
  const line = node("div", "subline spell-line");
  const list = spells || [];
  if (!list.length) {
    line.textContent = "Spells: none";
    container.appendChild(line);
    return;
  }
  const inCombat = session?.mode === "combat" && member?.current_life > 0;
  line.appendChild(document.createTextNode(inCombat ? "Spells (reference): " : "Spells: "));
  list.forEach((spell, index) => {
    if (index > 0) line.appendChild(document.createTextNode(", "));
    const label = session && member ? spellLabel(session, member, spell) : spell;
    const tag = node("span", inCombat ? "spell-tag spell-tag-readonly" : "spell-tag", label);
    setTooltip(tag, spellTooltip(spell, session, member));
    line.appendChild(tag);
  });
  container.appendChild(line);
}

function appendMemberExplorationActions(item, session, member) {
  if (session.mode !== "exploration" || member.current_life <= 0) return;
  syncAllySpellTargets(session);
  const actions = node("div", "item-actions member-sheet-actions");
  let hasActions = false;

  for (const spell of member.spells || []) {
    const key = normalizeSpellKey(spell);
    if (!EXPLORATION_MODE_SPELL_KEYS.has(key) || spellExpended(session, member, spell)) continue;
    const row = node("div", "spell-cast-row");
    if (spellNeedsAllyTarget(spell)) {
      const allyRow = node("label", "spell-ally-label");
      allyRow.appendChild(document.createTextNode("Target: "));
      allyRow.appendChild(allyTargetSelect(session, member.character_id));
      row.appendChild(allyRow);
    }
    let lifeAmountInput = null;
    if (key === "lifeforce_control") {
      const amountRow = node("label", "spell-ally-label");
      amountRow.appendChild(document.createTextNode("Life to transfer: "));
      lifeAmountInput = document.createElement("input");
      lifeAmountInput.type = "number";
      lifeAmountInput.min = "1";
      lifeAmountInput.max = String(Math.max(1, member.current_life));
      lifeAmountInput.value = String(state.spellLifeTransfer?.[member.character_id] || 1);
      lifeAmountInput.className = "spell-life-input";
      amountRow.appendChild(lifeAmountInput);
      row.appendChild(amountRow);
    }
    if (key === "mass_teleport") {
      appendMassTeleportTargeting(row, session, member);
    }
    const button = node("button", "secondary", spell);
    button.type = "button";
    setButtonTooltip(button, spellTooltip(spell));
    button.addEventListener("click", () => {
      const extra = {};
      if (lifeAmountInput) {
        extra.life_transfer_amount = Math.max(1, Number.parseInt(lifeAmountInput.value, 10) || 1);
        state.spellLifeTransfer[member.character_id] = extra.life_transfer_amount;
      }
      advance("cast_spell", spellCastPayload(member.character_id, spell, extra));
    });
    row.appendChild(button);
    actions.appendChild(row);
    hasActions = true;
  }

  if (member.class_id !== "barbarian") {
    for (const inventoryItem of member.inventory || []) {
      const spell = scrollSpellName(inventoryItem);
      if (!spell) continue;
      const row = node("div", "spell-cast-row");
      if (spellNeedsAllyTarget(spell)) {
        const allyRow = node("label", "spell-ally-label");
        allyRow.appendChild(document.createTextNode("Target: "));
        allyRow.appendChild(allyTargetSelect(session, member.character_id));
        row.appendChild(allyRow);
      }
      const button = node("button", "secondary", `Burn scroll: ${spell}`);
      button.type = "button";
      setButtonTooltip(button, `${spellTooltip(spell)} Burns the scroll; does not use a memorized slot.`);
      button.addEventListener("click", () => advance("burn_scroll", spellCastPayload(member.character_id, spell)));
      row.appendChild(button);
      actions.appendChild(row);
      hasActions = true;
      if (
        member.class_id === "wizard" &&
        !(member.spells || []).some((known) => normalizeSpellKey(known) === normalizeSpellKey(spell))
      ) {
        const copyBtn = node("button", "secondary", `Copy ${spell} to spellbook`);
        copyBtn.type = "button";
        setButtonTooltip(copyBtn, "Copy this scroll into the wizard's spellbook instead of casting (destroys scroll).");
        copyBtn.addEventListener("click", () =>
          advance("copy_scroll", { character_id: member.character_id, spell_name: spell })
        );
        actions.appendChild(copyBtn);
      }
    }
    for (const magic of heroChargedMagicItems(member)) {
      const row = node("div", "spell-cast-row");
      if (spellNeedsAllyTarget(magic.spell)) {
        const allyRow = node("label", "spell-ally-label");
        allyRow.appendChild(document.createTextNode("Target: "));
        allyRow.appendChild(allyTargetSelect(session, member.character_id));
        row.appendChild(allyRow);
      }
      const button = node("button", "secondary", `Use ${magic.label} (${magic.charges})`);
      button.type = "button";
      setButtonTooltip(
        button,
        `${spellTooltip(magic.spell)} Uses 1 charge from ${magic.item}; does not use a memorized slot.`
      );
      button.addEventListener("click", () =>
        advance(
          "use_magic_item",
          spellCastPayload(member.character_id, magic.spell, { item_name: magic.item })
        )
      );
      row.appendChild(button);
      actions.appendChild(row);
      hasActions = true;
    }
  }

  for (const mushroomName of heroUsableMushrooms(session, member)) {
    const mushroomBtn = node("button", "secondary", `Eat: ${mushroomName}`);
    mushroomBtn.type = "button";
    setButtonTooltip(mushroomBtn, "Eat a rare mushroom from inventory (EE p.159 effects).");
    mushroomBtn.addEventListener("click", () =>
      advance("use_mushroom", { character_id: member.character_id, item_name: mushroomName })
    );
    actions.appendChild(mushroomBtn);
    hasActions = true;
  }

  for (const potionName of heroUsablePotions(session, member)) {
    const potionBtn = node("button", "secondary", potionName);
    potionBtn.type = "button";
    const sleepPotion = potionName.toLowerCase().includes("sleep");
    potionBtn.disabled = sleepPotion && immediateLocked;
    const tooltip = potionName.toLowerCase().includes("healing")
      ? ACTION_TOOLTIPS.usePotion
      : sleepPotion
        ? immediateActionTooltip(session, `Use ${potionName} against foes (consumes the potion).`)
        : `Use ${potionName} from inventory (consumes the potion).`;
    setButtonTooltip(potionBtn, tooltip);
    potionBtn.addEventListener("click", () =>
      advance("use_potion", { character_id: member.character_id, item_name: potionName })
    );
    actions.appendChild(potionBtn);
    hasActions = true;
  }

  for (const bandageName of heroUsableBandages(session, member)) {
    const receivers = bandageReceivers(session);
    if (!receivers.length) continue;
    const row = node("div", "combat-target-row");
    row.appendChild(document.createTextNode("Bandage target:"));
    const select = document.createElement("select");
    for (const ally of receivers) {
      const option = document.createElement("option");
      option.value = ally.character_id;
      option.textContent = ally.name;
      select.appendChild(option);
    }
    const preferred =
      state.bandageTargets?.[member.character_id] ||
      (receivers.some((ally) => ally.character_id === member.character_id) ? member.character_id : receivers[0].character_id);
    select.value = receivers.some((ally) => ally.character_id === preferred) ? preferred : receivers[0].id;
    select.addEventListener("change", () => {
      state.bandageTargets = state.bandageTargets || {};
      state.bandageTargets[member.character_id] = select.value;
    });
    row.appendChild(select);
    const bandageBtn = node("button", "secondary", bandageName);
    bandageBtn.type = "button";
    setButtonTooltip(bandageBtn, ACTION_TOOLTIPS.useBandage);
    bandageBtn.addEventListener("click", () =>
      advance("use_bandage", {
        character_id: member.character_id,
        target_character_id: select.value,
      })
    );
    row.appendChild(bandageBtn);
    actions.appendChild(row);
    hasActions = true;
  }

  if (hasActions) {
    item.appendChild(node("div", "combat-section-label", "Actions"));
    item.appendChild(actions);
  }
}

function appendMemberCombatActions(item, session, member, tile, livingFoes, reactionsPending) {
  if (session.mode !== "combat" || member.current_life <= 0) return;
  const actions = node("div", "item-actions member-sheet-actions");
  const immediateLocked = surpriseReactionLocked(session);

  const abilityLine = abilityStatusLine(session, member);
  if (abilityLine) {
    item.appendChild(node("div", "combat-hero-meta muted", abilityLine));
  }

  const wieldedMelee = session.wielded_melee_weapons?.[member.character_id];
  const drawOptions = memberMeleeWeapons(member).filter((weapon) => weapon !== wieldedMelee);
  if (drawOptions.length) {
    actions.appendChild(
      createSheetIconButton({
        kind: "changeWeapon",
        ariaLabel: "Change weapon",
        tooltip: immediateActionTooltip(session, ACTION_TOOLTIPS.drawWeapon),
        disabled: immediateLocked,
        onClick: () => openWeaponPickerDialog({ mode: "draw", source: "session", member, session }),
      })
    );
  }

  for (const potionName of heroUsablePotions(session, member)) {
    const potionBtn = node("button", "secondary", potionName);
    potionBtn.type = "button";
    const tooltip = potionName.toLowerCase().includes("healing")
      ? ACTION_TOOLTIPS.usePotion
      : `Use ${potionName} from inventory (consumes the potion).`;
    setButtonTooltip(potionBtn, tooltip);
    potionBtn.addEventListener("click", () =>
      advance("use_potion", { character_id: member.character_id, item_name: potionName })
    );
    actions.appendChild(potionBtn);
  }

  for (const vialName of heroUsableHolyWater(session, member, livingFoes)) {
    const holyBtn = node("button", "secondary", "Throw holy water");
    holyBtn.type = "button";
    holyBtn.disabled = immediateLocked;
    setButtonTooltip(holyBtn, immediateActionTooltip(session, ACTION_TOOLTIPS.useHolyWater));
    holyBtn.addEventListener("click", () => {
      const targetId = state.combatTargets[member.character_id] || livingFoes.find(foeIsUndead)?.id;
      const attack_targets = targetId ? { [member.character_id]: targetId } : undefined;
      advance("use_holy_water", {
        character_id: member.character_id,
        item_name: vialName,
        attack_targets,
      });
    });
    actions.appendChild(holyBtn);
  }

  for (const oilName of heroUsableLanternOil(session, member, livingFoes)) {
    const oilBtn = node("button", "secondary", "Splash lantern oil");
    oilBtn.type = "button";
    oilBtn.disabled = immediateLocked;
    setButtonTooltip(oilBtn, immediateActionTooltip(session, ACTION_TOOLTIPS.useLanternOil));
    oilBtn.addEventListener("click", () => {
      const targetId =
        state.combatTargets[member.character_id] || livingFoes.find(foeHasRegeneration)?.id;
      const attack_targets = targetId ? { [member.character_id]: targetId } : undefined;
      advance("use_lantern_oil", {
        character_id: member.character_id,
        item_name: oilName,
        attack_targets,
      });
    });
    actions.appendChild(oilBtn);
  }

  for (const acidName of heroUsableAcidVial(session, member, livingFoes)) {
    const acidBtn = node("button", "secondary", "Throw acid vial");
    acidBtn.type = "button";
    acidBtn.disabled = immediateLocked;
    setButtonTooltip(
      acidBtn,
      immediateActionTooltip(
        session,
        "Throw acid at a foe (p.99). Acid damage blocks troll regeneration. Uses combat target; consumes the vial."
      )
    );
    acidBtn.addEventListener("click", () => {
      const targetId = state.combatTargets[member.character_id] || livingFoes[0]?.id;
      const attack_targets = targetId ? { [member.character_id]: targetId } : undefined;
      advance("use_acid_vial", {
        character_id: member.character_id,
        item_name: acidName,
        attack_targets,
      });
    });
    actions.appendChild(acidBtn);
  }

  const magicItems = heroChargedMagicItems(member);
  const magicSpells = magicItems.map((entry) => entry.spell);
  const spells = heroCombatSpells(session, member);
  const allySpells = [...spells, ...magicSpells].filter(spellNeedsAllyTarget);
  if (allySpells.length) {
    const allyRow = node("div", "combat-target-row");
    allyRow.appendChild(document.createTextNode("Ally spell target:"));
    allyRow.appendChild(allyTargetSelect(session, member.character_id));
    actions.appendChild(allyRow);
  }
  if (spells.length || magicSpells.length) {
    appendSpellTargetingRows(actions, session, member, livingFoes, magicSpells);
  }
  for (const magic of magicItems) {
    const magicBtn = node("button", "secondary", `${magic.label} (${magic.charges})`);
    magicBtn.type = "button";
    magicBtn.disabled = immediateLocked;
    const skipsReactions = reactionsPending && spellCommitsToAttack(magic.spell);
    setButtonTooltip(
      magicBtn,
      immediateLocked
        ? immediateActionTooltip(session, `${spellTooltip(magic.spell, session, member)} Uses 1 charge from ${magic.item}.`)
        : skipsReactions
        ? `${spellTooltip(magic.spell, session, member)} Uses 1 charge; casting now skips the Reaction roll.`
        : `${spellTooltip(magic.spell, session, member)} Uses 1 charge from ${magic.item}; does not use a memorized slot.`
    );
    magicBtn.addEventListener("click", () =>
      advance(
        "use_magic_item",
        spellCastPayload(member.character_id, magic.spell, { item_name: magic.item })
      )
    );
    actions.appendChild(magicBtn);
  }
  for (const spell of spells) {
    const spellBtn = node("button", "secondary", spell);
    spellBtn.type = "button";
    spellBtn.disabled = immediateLocked;
    const skipsReactions = reactionsPending && spellCommitsToAttack(spell);
    setButtonTooltip(
      spellBtn,
      immediateLocked
        ? immediateActionTooltip(session, spellTooltip(spell, session, member))
        : skipsReactions
        ? `${spellTooltip(spell, session, member)} Casting now skips the Reaction roll.`
        : spellTooltip(spell, session, member)
    );
    spellBtn.addEventListener("click", () => advance("cast_spell", spellCastPayload(member.character_id, spell)));
    actions.appendChild(spellBtn);
  }

  if (actions.childElementCount) {
    item.appendChild(node("div", "combat-section-label", "Spells & items"));
    item.appendChild(actions);
  }
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
    "Search has already found something; choose one reward from the page 107 list."
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
  setButtonTooltip(tradeInfoSellBtn, ACTION_TOOLTIPS.tradeInfoSell);
  setButtonTooltip(tradeInfoBuyBtn, ACTION_TOOLTIPS.tradeInfoBuy);
  setButtonTooltip(tradeInfoDeclineBtn, ACTION_TOOLTIPS.tradeInfoDecline);
  const combatLivingFoes = session ? livingFoesOnTile(session) : [];
  const combatWithdrawDoors =
    session?.mode === "combat" ? combatWithdrawDoorOptions(session, tile || currentTile(session)) : [];
  setButtonTooltip(
    combatBtn,
    combatLivingFoes.length
      ? immediateActionTooltip(session, ACTION_TOOLTIPS.combatRound)
      : "No living foes remain."
  );
  setButtonTooltip(combatStartBtn, ACTION_TOOLTIPS.startCombat);
  setButtonTooltip(combatResolveBtn, immediateActionTooltip(session, ACTION_TOOLTIPS.combatRound));
  setTooltip(
    subdualLabel,
    "Subdual attacks deal normal damage but knock foes out at 0 Life instead of slaying them. Required to complete bring-alive Boss quests."
  );
  setButtonTooltip(
    fleeBtn,
    surpriseReactionLocked(session) ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee) : ACTION_TOOLTIPS.flee
  );
  setButtonTooltip(
    withdrawBtn,
    surpriseReactionLocked(session)
      ? immediateActionTooltip(session, ACTION_TOOLTIPS.withdraw)
      : combatWithdrawDoors.length
        ? ACTION_TOOLTIPS.withdraw
        : "Withdraw requires an open door to a visited tile."
  );
  setButtonTooltip(
    combatFleeBtn,
    surpriseReactionLocked(session) ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee) : ACTION_TOOLTIPS.flee
  );
  setButtonTooltip(
    combatWithdrawBtn,
    surpriseReactionLocked(session) ? immediateActionTooltip(session, ACTION_TOOLTIPS.withdraw) : ACTION_TOOLTIPS.withdraw
  );
  setButtonTooltip(resolveTrapBtn, ACTION_TOOLTIPS.resolveTrap);
  let claimTooltip = ACTION_TOOLTIPS.claimTreasure;
  if (session?.mode === "exploration" && hasTrap) {
    claimTooltip = "Resolve the trap before claiming treasure.";
  } else if (session?.mode === "exploration" && !hasTreasure && tile?.treasure_summary) {
    claimTooltip = tile.treasure_summary;
  }
  setButtonTooltip(claimTreasureBtn, claimTooltip);
  const restStatus = session ? restEligibility(session) : { ok: false, reason: "" };
  setButtonTooltip(
    restBtn,
    restStatus.ok ? ACTION_TOOLTIPS.rest : `${ACTION_TOOLTIPS.rest} ${restStatus.reason}`.trim()
  );
  setButtonTooltip(saveSessionBtn, ACTION_TOOLTIPS.saveSession);
  setButtonTooltip(showSetupBtn, SETUP_TOOLTIPS.showSetup);
  setButtonTooltip(logModeSummaryBtn, ACTION_TOOLTIPS.logSummary);
  setButtonTooltip(logModeVerboseBtn, ACTION_TOOLTIPS.logVerbose);
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
  setTooltip(xpSystemSelect, SETUP_TOOLTIPS.campaignMode);
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
    const [classes, characters, parties, adventures, rulesTables, expertSkillsCatalog, heroicSkillsCatalog, legendarySkillsCatalog, monsterBestiary, monsterReactions, mapElementDefinitions, icons, sessions] = await Promise.all([
      api("/api/rules/classes"),
      api("/api/characters"),
      api("/api/parties"),
      api("/api/adventures"),
      api("/api/rules/tables"),
      api("/api/rules/expert-skills"),
      api("/api/rules/heroic-skills"),
      api("/api/rules/legendary-skills"),
      api("/api/rules/monsters"),
      api("/api/rules/monster-reactions"),
      api("/api/rules/tiles"),
      api("/api/rules/icons"),
      api("/api/sessions"),
    ]);
    state.classes = classes;
    state.characters = characters;
    state.parties = parties;
    state.adventures = adventures;
    state.rulesTables = rulesTables;
    state.expertSkillsCatalog = expertSkillsCatalog;
    state.heroicSkillsCatalog = heroicSkillsCatalog;
    state.legendarySkillsCatalog = legendarySkillsCatalog;
    state.monsterBestiary = monsterBestiary;
    state.monsterReactions = monsterReactions;
    state.mapElementDefinitions = mapElementDefinitions;
    state.icons = icons;
    state.sessions = sessions;
    apiStatus.textContent = "Connected";
    applyMapControlTooltips();
    renderSetup({ rememberView: preferredView !== "game" });
    refreshRulesReference().catch(() => {
      state.rulesReference = [];
      renderRulesReference([]);
    });
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
  renderActiveGames();
  renderSavedGames();
  renderRulesTables();
  resumeSessionBtn.classList.toggle("hidden", !state.session);
  applySetupTooltips();
}

function setStatus(message) {
  apiStatus.textContent = message;
}

function handleError(error) {
  setStatus(error.message || "Action failed");
}

function classImageUrl(profile) {
  if (!profile?.image) return "";
  return `/assets/${profile.image}`;
}

function formatClassDescription(description) {
  if (!description) return "No rulebook summary loaded for this class yet.";
  return description.replace(
    / (?=(?:Combat|Traits|Tricks|Life|Armor(?: Allowed)?|Weapons(?: Allowed)?|Starting(?: Equipment| wealth| Wealth)|Magic(?: items| Use| Item Use)?|Scroll use|Saves|Stealth|Advanced Skills|Rage|No Magic|Illiterate|Prayer|Healing|Blessing|Panache|Two Weapon Fighting|Combat Experience|Parry and Counter-strike|Expert Skill|Spell Burning|Gadgets|Optional|Assassin|Druid|Illusion|Magic Resistance)[^:]{0,48}:)/g,
    "\n\n$1",
  );
}

function classCardRoleLabel(profile) {
  if (profile.abilities?.length) return profile.abilities.slice(0, 2).join(" · ");
  return "Adventurer";
}

function classCardTooltip(profile) {
  const lines = [profile.name];
  if (profile.abilities?.length) lines.push(profile.abilities.join(" · "));
  if (profile.starting_spells?.length) lines.push(`Starts with: ${profile.starting_spells.join(", ")}`);
  if (profile.description) {
    const snippet = profile.description.length > 260 ? `${profile.description.slice(0, 260)}…` : profile.description;
    lines.push(snippet);
  }
  return lines.join("\n\n");
}

function selectedCreateClassProfile() {
  const classId = state.selectedCreateClassId || state.classes[0]?.id || "";
  return state.classes.find((profile) => profile.id === classId) || state.classes[0] || null;
}

function selectCreateClass(classId) {
  if (!state.classes.some((profile) => profile.id === classId)) return;
  state.selectedCreateClassId = classId;
  characterClass.value = classId;
  renderClassPicker();
  renderClassDetail();
}

function renderClassPicker() {
  if (!classPickerEl) return;
  classPickerEl.replaceChildren();
  const selectedId = selectedCreateClassProfile()?.id || "";
  for (const profile of state.classes) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "class-card";
    button.dataset.classId = profile.id;
    if (profile.id === selectedId) button.classList.add("selected");
    button.setAttribute("aria-pressed", profile.id === selectedId ? "true" : "false");
    button.dataset.tooltip = classCardTooltip(profile);
    button.title = profile.name;
    const overlay = node("div", "class-card-overlay");
    overlay.appendChild(node("span", "class-card-type", profile.name));
    overlay.appendChild(node("span", "class-card-role", classCardRoleLabel(profile)));
    const media = node("div", "class-card-media");
    const imageUrl = classImageUrl(profile);
    if (imageUrl) {
      const image = document.createElement("img");
      image.src = imageUrl;
      image.alt = `${profile.name} portrait`;
      image.loading = "lazy";
      media.appendChild(image);
    } else {
      const fallback = document.createElement("div");
      fallback.className = "class-card-fallback";
      fallback.textContent = profile.name.slice(0, 1);
      media.appendChild(fallback);
    }
    button.appendChild(media);
    button.appendChild(overlay);
    button.addEventListener("click", () => selectCreateClass(profile.id));
    classPickerEl.appendChild(button);
  }
}

function renderClassDetail() {
  if (!classDetailEl) return;
  classDetailEl.replaceChildren();
  const profile = selectedCreateClassProfile();
  if (!profile) {
    classDetailEl.appendChild(node("p", "muted", "No classes loaded."));
    return;
  }

  const portraitWrap = node("div", "class-detail-portrait");
  const imageUrl = classImageUrl(profile);
  if (imageUrl) {
    const image = document.createElement("img");
    image.src = imageUrl;
    image.alt = `${profile.name} rulebook art`;
    image.loading = "lazy";
    portraitWrap.appendChild(image);
  } else {
    const fallback = node("div", "class-detail-fallback", profile.name.slice(0, 1));
    portraitWrap.appendChild(fallback);
  }

  const body = node("div", "class-detail-body");
  body.appendChild(node("h3", "", profile.name));
  const stats = node("div", "class-detail-stats");
  stats.appendChild(node("span", "", `Attack ${formatSigned(profile.attack_bonus)}`));
  stats.appendChild(node("span", "", `Defense ${formatSigned(profile.defense_bonus)}`));
  stats.appendChild(node("span", "", `Save ${formatSigned(profile.save_bonus)}`));
  const wealthLabel = profile.starting_wealth_roll || (profile.starting_gold ? `${profile.starting_gold}gp` : "");
  if (wealthLabel) stats.appendChild(node("span", "", `${wealthLabel}${profile.starting_wealth_roll ? "gp" : ""}`));
  body.appendChild(stats);
  body.appendChild(node("p", "class-detail-text", formatClassDescription(profile.description)));
  if (profile.starting_inventory?.length) {
    body.appendChild(node("p", "class-detail-spells", `Starting gear: ${profile.starting_inventory.join(", ")}`));
  }
  if (profile.starting_spells?.length) {
    body.appendChild(node("p", "class-detail-spells", `Starting spells/prayers: ${profile.starting_spells.join(", ")}`));
  }
  if (profile.abilities?.length) {
    body.appendChild(node("p", "class-detail-spells", `Highlights: ${profile.abilities.join(", ")}`));
  }

  classDetailEl.appendChild(portraitWrap);
  classDetailEl.appendChild(body);
}

function formatSigned(value) {
  if (value > 0) return `+${value}`;
  return String(value);
}

function renderClasses() {
  if (!state.selectedCreateClassId && state.classes[0]) {
    state.selectedCreateClassId = state.classes[0].id;
  }
  if (state.selectedCreateClassId && !state.classes.some((profile) => profile.id === state.selectedCreateClassId)) {
    state.selectedCreateClassId = state.classes[0]?.id || null;
  }
  characterClass.value = selectedCreateClassProfile()?.id || "";
  renderClassPicker();
  renderClassDetail();
}

function renderCharacterControls() {
  state.characterFilters.classId = renderClassFilter(characterFilterClass, state.characterFilters.classId);
  state.characterFilters.level = renderLevelFilter(characterFilterLevel, characterLevels(), state.characterFilters.level);
  if (characterFilterAvailability) {
    state.characterFilters.availability = renderSelectOptions(
      characterFilterAvailability,
      [
        ["all", "All heroes"],
        ["available", "Available"],
        ["adventuring", "Gone adventuring"],
      ],
      state.characterFilters.availability
    );
  }
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
    const adventuring = characterInActiveAdventure(character);
    if (filters.availability === "available" && adventuring) return false;
    if (filters.availability === "adventuring" && !adventuring) return false;
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

function characterById(characterId) {
  return state.characters.find((character) => character.id === characterId) || null;
}

function emptyPartySlots() {
  return [null, null, null, null];
}

function partySlotsFromIds(characterIds) {
  const slots = emptyPartySlots();
  characterIds.slice(0, 4).forEach((characterId, index) => {
    slots[index] = characterId;
  });
  return slots;
}

function filledPartyCharacterIds() {
  return state.partySlotIds.filter(Boolean);
}

function heroIsInParty(characterId) {
  return state.partySlotIds.includes(characterId);
}

function firstEmptyPartySlotIndex() {
  return state.partySlotIds.findIndex((characterId) => !characterId);
}

function assignPartySlot(slotIndex, characterId, options = {}) {
  if (!characterId || slotIndex < 0 || slotIndex > 3) return false;
  const character = characterById(characterId);
  if (!character) return false;
  if (characterInActiveAdventure(character)) {
    setStatus(`${character.name} is already in an active adventure.`);
    return false;
  }
  state.partySlotIds = state.partySlotIds.map((id) => (id === characterId ? null : id));
  const displaced = state.partySlotIds[slotIndex];
  state.partySlotIds[slotIndex] = characterId;
  if (displaced && displaced !== characterId && options.swapDisplaced !== false) {
    const emptyIndex = state.partySlotIds.findIndex((id) => !id);
    if (emptyIndex >= 0) state.partySlotIds[emptyIndex] = displaced;
  }
  renderPartySlots();
  renderCharacterPartyMarkers();
  return true;
}

function addCharacterToParty(characterId) {
  const character = state.characters.find((item) => item.id === characterId);
  if (character && characterInActiveAdventure(character)) {
    setStatus(`${character.name} is already in an active adventure.`);
    return false;
  }
  const emptyIndex = firstEmptyPartySlotIndex();
  if (emptyIndex < 0) {
    setStatus("Party is full. Remove a hero from a slot first.");
    return false;
  }
  assignPartySlot(emptyIndex, characterId);
  setStatus("Hero added to party.");
  return true;
}

function removePartySlot(slotIndex) {
  if (slotIndex < 0 || slotIndex > 3) return;
  state.partySlotIds[slotIndex] = null;
  renderPartySlots();
  renderCharacterPartyMarkers();
}

function movePartySlot(fromIndex, toIndex) {
  if (fromIndex === toIndex || fromIndex < 0 || fromIndex > 3 || toIndex < 0 || toIndex > 3) return;
  const movingId = state.partySlotIds[fromIndex];
  if (!movingId) return;
  const targetId = state.partySlotIds[toIndex];
  state.partySlotIds[fromIndex] = targetId || null;
  state.partySlotIds[toIndex] = movingId;
  renderPartySlots();
  renderCharacterPartyMarkers();
}

function rosterDragPayload(event, characterId) {
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", characterId);
  state.partyDragCharacterId = characterId;
}

function renderPartySlots() {
  if (!partySlotsEl) return;
  partySlotsEl.replaceChildren();
  state.partySlotIds.forEach((characterId, index) => {
    const slot = node("div", "party-slot");
    if (characterId) slot.classList.add("filled");
    slot.dataset.slotIndex = String(index);
    setTooltip(slot, SETUP_TOOLTIPS.partySlot);
    slot.appendChild(node("span", "party-slot-position", `#${index + 1}`));

    const body = node("div", "party-slot-body");
    if (characterId) {
      const character = characterById(characterId);
      if (character) {
        body.appendChild(node("strong", "", character.name));
        body.appendChild(
          node(
            "span",
            "muted",
            `${character.class_name} · L${character.level} · ${character.gold}gp · ${character.clues || 0} Clue(s)`
          )
        );
        slot.draggable = true;
        slot.addEventListener("dragstart", (event) => {
          rosterDragPayload(event, characterId);
          event.dataTransfer.setData("application/party-slot", String(index));
        });
      } else {
        body.appendChild(node("span", "party-slot-empty", "Missing hero"));
      }
    } else {
      body.appendChild(node("span", "party-slot-empty", "Drop hero here"));
    }
    slot.appendChild(body);

    const remove = node("button", "secondary party-slot-remove", "×");
    remove.type = "button";
    remove.disabled = !characterId;
    setButtonTooltip(remove, SETUP_TOOLTIPS.removeFromParty);
    remove.addEventListener("click", () => removePartySlot(index));
    slot.appendChild(remove);

    slot.addEventListener("dragover", (event) => {
      event.preventDefault();
      slot.classList.add("drag-over");
    });
    slot.addEventListener("dragleave", () => slot.classList.remove("drag-over"));
    slot.addEventListener("drop", (event) => {
      event.preventDefault();
      slot.classList.remove("drag-over");
      const characterIdFromDrag = event.dataTransfer.getData("text/plain");
      const fromSlot = event.dataTransfer.getData("application/party-slot");
      if (!characterIdFromDrag) return;
      if (fromSlot !== "") {
        movePartySlot(Number(fromSlot), index);
        return;
      }
      assignPartySlot(index, characterIdFromDrag);
    });

    partySlotsEl.appendChild(slot);
  });
  refreshButtonTooltips(partySlotsEl);
}

function renderCharacterPartyMarkers() {
  for (const item of charactersEl.querySelectorAll(".roster-item")) {
    const characterId = item.dataset.characterId;
    item.classList.toggle("in-party", heroIsInParty(characterId));
  }
}

function renderCharacters() {
  renderCharacterControls();
  const visibleCharacters = sortedCharacters(filteredCharacters());
  characterCount.textContent =
    visibleCharacters.length === state.characters.length
      ? `${state.characters.length} saved`
      : `${visibleCharacters.length} of ${state.characters.length}`;
  charactersEl.replaceChildren();

  for (const character of visibleCharacters) {
    const item = node("div", "item selectable-item roster-item");
    item.tabIndex = 0;
    item.dataset.characterId = character.id;
    if (character.id === state.selectedCharacterId) item.classList.add("selected");
    if (heroIsInParty(character.id)) item.classList.add("in-party");
    if (characterInActiveAdventure(character)) item.classList.add("gone-adventuring");

    const dragHandle = node("span", "roster-drag-handle", "⋮⋮");
    dragHandle.draggable = !characterInActiveAdventure(character);
    setTooltip(dragHandle, SETUP_TOOLTIPS.rosterDragHandle);
    dragHandle.addEventListener("dragstart", (event) => {
      rosterDragPayload(event, character.id);
    });
    item.appendChild(dragHandle);

    const body = node("div", "roster-item-body");
    const titleRow = node("div", "roster-title-row");
    titleRow.appendChild(node("strong", "", `${character.name} - ${character.class_name}`));
    if (characterInActiveAdventure(character)) {
      titleRow.appendChild(node("span", "roster-status-badge gone-adventuring-badge", "Gone adventuring"));
    }
    body.appendChild(titleRow);
    body.appendChild(
      subline(
        `L${character.level} HP ${character.current_life}/${character.max_life} ATK +${character.attack_bonus} DEF +${character.defense_bonus} SAVE +${character.save_bonus}`
      )
    );
    body.appendChild(subline(`Gold ${character.gold} | XP ${character.xp} | Clues ${character.clues || 0}`));
    body.appendChild(subline(carryLimitsLine(character)));
    const meleeDefault = character.default_melee_weapon || "none";
    const meleeSecondaryDefault = character.default_melee_weapon_secondary || "none";
    const missileDefault = character.default_missile_weapon || "none";
    const defaultLine = memberUsesDualMeleeDefaults(character)
      ? `Equipment: melee ${meleeDefault}, off-hand ${meleeSecondaryDefault}, missile ${missileDefault}`
      : `Equipment: melee ${meleeDefault}, missile ${missileDefault}`;
    body.appendChild(subline(defaultLine));
    if (character.class_id === "ranger" && hasMissileWeapon(character)) {
      body.appendChild(subline("Outdoor bow: one default bow fires twice per round (+½L each)."));
    }
    if (heroIsInParty(character.id)) {
      const slotIndex = state.partySlotIds.indexOf(character.id);
      body.appendChild(subline(`In party slot #${slotIndex + 1}`));
    }
    if (characterInActiveAdventure(character)) {
      body.appendChild(subline(characterAdventureLabel(character)));
    }
    if (character.id === state.selectedCharacterId) {
      body.appendChild(subline(`Inventory: ${character.inventory.join(", ") || "none"}`));
      appendSpellSubline(body, character.spells);
      const actions = node("div", "item-actions");
      const addParty = node("button", "secondary", heroIsInParty(character.id) ? "In party" : "Add to party");
      addParty.type = "button";
      addParty.disabled = heroIsInParty(character.id) || characterInActiveAdventure(character);
      setButtonTooltip(addParty, SETUP_TOOLTIPS.addToParty);
      addParty.addEventListener("click", async (event) => {
        event.stopPropagation();
        addCharacterToParty(character.id);
      });
      actions.appendChild(addParty);
      const heal = node("button", "secondary", "Heal");
      heal.type = "button";
      heal.disabled = character.current_life >= character.max_life;
      heal.addEventListener("click", async (event) => {
        event.stopPropagation();
        await healCharacter(character.id);
      });
      setButtonTooltip(heal, SETUP_TOOLTIPS.healCharacter);
      if (canEditWeaponDefaults(character)) {
        const equipmentBtn = createSheetIconButton({
          kind: "equipment",
          ariaLabel: "Equipment slots",
          tooltip: SETUP_TOOLTIPS.weaponDefaults,
          onClick: (event) => {
            event.stopPropagation();
            openWeaponPickerDialog({ mode: "defaults", source: "roster", member: character });
          },
        });
        actions.appendChild(equipmentBtn);
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
      body.appendChild(actions);
    }
    item.appendChild(body);
    item.addEventListener("click", () => {
      state.selectedCharacterId = state.selectedCharacterId === character.id ? null : character.id;
      renderCharacters();
    });
    item.addEventListener("dblclick", (event) => {
      event.preventDefault();
      addCharacterToParty(character.id);
    });
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        item.click();
      }
    });
    charactersEl.appendChild(item);
  }

  renderPartySlots();
  if (transferItemsSetupBtn) {
    transferItemsSetupBtn.disabled = state.characters.length < 2;
  }
  if (equipmentShopSetupBtn) {
    equipmentShopSetupBtn.disabled = !state.characters.length;
  }
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
    const busyLabel = partyHasBusyMembers(party) ? " — in adventure" : "";
    option.textContent = `${party.name} (Avg L${stats.averageLevelLabel})${busyLabel}`;
    partySelect.appendChild(option);
  }
  const selectedParty = state.parties.find((party) => party.id === partySelect.value);
  startSession.disabled = !partySelect.value || (selectedParty && partyHasBusyMembers(selectedParty));
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

function renderActiveGames() {
  if (!activeGamesEl) return;
  activeGamesEl.replaceChildren();
  const activeSessions = [...state.sessions]
    .filter((session) => session.mode !== "complete")
    .sort((left, right) => (right.updated_at || "").localeCompare(left.updated_at || ""));
  if (activeGameCount) {
    activeGameCount.textContent =
      activeSessions.length === 1 ? "1 in progress" : `${activeSessions.length} in progress`;
  }
  if (!activeSessions.length) {
    activeGamesEl.appendChild(node("div", "item", "No adventures in progress."));
    return;
  }
  for (const session of activeSessions) {
    const item = node("div", "item selectable-item");
    if (state.session?.id === session.id) item.classList.add("selected");
    item.appendChild(node("strong", "", sessionDisplayTitle(session)));
    item.appendChild(
      subline(
        `${session.mode}${session.saved_at ? " | saved" : " | unsaved"} | ${session.map_state?.tiles?.length || 0} map elements`
      )
    );
    const actions = node("div", "item-actions");
    const resume = node("button", "secondary", state.session?.id === session.id ? "Current" : "Resume");
    resume.type = "button";
    resume.disabled = state.session?.id === session.id;
    resume.addEventListener("click", async () => loadSession(session.id));
    const remove = node("button", "danger-button", "End adventure");
    remove.type = "button";
    remove.addEventListener("click", async () => deleteSession(session.id));
    actions.append(resume, remove);
    item.appendChild(actions);
    activeGamesEl.appendChild(item);
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
    item.appendChild(node("strong", "", sessionDisplayTitle(session)));
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

const ENVIRONMENT_TABLE_HINTS = {
  caverns_special_events_table: "Caverns Special Events (d6), EE p.155. Used after a secret passage into caverns.",
  fungal_grottoes_special_events_table: "Fungal Grottoes Special Events (d6), EE p.156.",
  caverns_special_item_table: "Caverns Special Item / treasure roll 6, EE p.160.",
  fungal_grottoes_rare_item_table: "Fungal Grottoes rare items / treasure roll 6, EE p.161.",
  fungal_grottoes_rare_mushroom_table: "Rare Mushroom sub-table (d6), EE p.159.",
  caverns_trap_table: "Caverns Traps (d6), EE p.165.",
  fungal_grottoes_trap_table: "Fungal Grottoes Traps (d6), EE p.166.",
};

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
  "clue_spends_table",
  "room_content_table",
  "wandering_monsters_table",
  "special_event_wandering_table",
  "dungeon_special_events_table",
  "caverns_special_events_table",
  "fungal_grottoes_special_events_table",
  "dungeon_special_features_table",
  "dungeon_magic_treasure_table",
  "caverns_special_item_table",
  "fungal_grottoes_rare_item_table",
  "fungal_grottoes_rare_mushroom_table",
  "caverns_trap_table",
  "fungal_grottoes_trap_table",
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
  "expert_skills_table",
  "expert_skill_implementation_table",
  "expert_spells_table",
  "heroic_skills_table",
  "legendary_skills_table",
  "class_tricks_implementation_table",
  "map_elements_validation_table",
  "tier_training_costs_table",
  "quest_table",
  "epic_rewards_table",
  "combat_modifiers_table",
  "combat_notes",
];

function createRulesSectionGroup(title, hint) {
  const group = document.createElement("details");
  group.className = "rules-section-group";
  const summary = document.createElement("summary");
  const titleEl = node("span", "rules-section-title", title);
  summary.appendChild(titleEl);
  if (hint) {
    summary.appendChild(node("span", "rules-section-hint", hint));
  }
  group.appendChild(summary);
  const body = node("div", "rules-section-body");
  group.appendChild(body);
  return { group, body };
}

function appendRulesTableCard(parent, key, value, displayTitle = "") {
  const detail = document.createElement("details");
  detail.className = "rules-table-card";
  const summary = document.createElement("summary");
  summary.textContent = displayTitle || titleFromKey(key);
  detail.appendChild(summary);
  if (key === "basic_spells_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Spellcasting roll: exploding tier die + caster Level vs foe Level (MR foes need a second roll). " +
          "Damage/effect is in the Result column. Fireball: +2 vs mummies. Hover spells on party sheets for the same summary."
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
  if (key === "dungeon_magic_treasure_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Roll 1: Wand of Sleep (3 charges). Roll 6: Fireball Staff (2 charges) — use from party sheets in combat; each cast spends 1 charge without using a memorized slot. Roll 4: Magic Weapon — d6 determines type (club, dagger, mace, sword, greatsword, or bow); +1 Attack when wielded (p.163)."
      )
    );
  }
  if (key === "equipment_shop_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Buy before or between adventures via the home Equipment Shop (p.16). Sell loot there; magic resale on the last row (p.19). Roster gold is home bank gold; only dungeon-carried gold is limited."
      )
    );
  }
  if (key === "expert_skills_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Four Against the Abyss expert skills (pp.14–23). Expert-trained L5+ heroes may spend an advancement XP roll to learn one instead of leveling up. Expert tier entry itself is a separate 500gp or 1 banked-XP training cost."
      )
    );
  }
  if (key === "expert_skill_implementation_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Expert skill effect coverage in the engine: wired skills apply in combat/exploration; planned skills are catalog-only until implemented."
      )
    );
  }
  if (key === "expert_spells_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Expert spells for wizard and elf (Abyss pp.24–25). Expert-trained casters learn these through the same XP fork as expert skills; all six cast effects are wired in play."
      )
    );
  }
  if (key === "tier_training_costs_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Forsaken Depths tier entry costs (summary p.9). Use Tier training on the party sheet between adventures. Expert entry costs 500gp or 1 banked XP roll and unlocks, but does not itself buy, an Expert skill."
      )
    );
  }
  if (key === "heroic_skills_table" || key === "legendary_skills_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Heroic (L10+) and Legendary (L15+) skills from Four Against the Abyss. Learn via the classical/slower XP fork on the party sheet. All 45 heroic and 20 legendary skills are wired — status column shows mechanic text."
      )
    );
  }
  if (key === "class_tricks_implementation_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Class tricks and Tier 1–4 abilities (EE p.40+). See class_tricks_tiers in Rules reference."
      )
    );
  }
  if (key === "map_elements_validation_table") {
    detail.appendChild(
      node(
        "div",
        "item muted",
        "Structural validation for all 01–06 entrance and 11–66 generated map elements. Also available via GET /api/rules/tiles/validation and tools/validate_tiles.py."
      )
    );
  }
  if (ENVIRONMENT_TABLE_HINTS[key]) {
    detail.appendChild(node("div", "item muted", ENVIRONMENT_TABLE_HINTS[key]));
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
  parent.appendChild(detail);
}

function renderDungeonRulesTables(parent, tables) {
  const orderedKeys = [
    ...RULES_TABLE_ORDER.filter((key) => tables[key] != null),
    ...Object.keys(tables).filter((key) => !RULES_TABLE_META_KEYS.has(key) && !RULES_TABLE_ORDER.includes(key)),
  ];
  if (!orderedKeys.length) {
    parent.appendChild(node("div", "item", "No structured tables loaded."));
    return;
  }
  for (const key of orderedKeys) {
    appendRulesTableCard(parent, key, tables[key]);
  }
}

function renderMonsterBestiaryTables(parent) {
  const bestiary = state.monsterBestiary || {};
  const categories = Object.keys(bestiary).sort();
  if (!categories.length) {
    parent.appendChild(node("div", "item", "No monster bestiary loaded."));
    return;
  }
  for (const category of categories) {
    appendRulesTableCard(parent, category, bestiary[category] || []);
  }
}

function renderMonsterReactionRulesTables(parent) {
  const reactions = state.monsterReactions || {};
  const names = Object.keys(reactions).sort();
  if (!names.length) {
    parent.appendChild(node("div", "item", "No per-foe reaction tables loaded."));
    return;
  }
  for (const name of names) {
    appendRulesTableCard(parent, name, reactions[name] || [], name);
  }
}

function renderMapElementTables(parent) {
  const tiles = state.mapElementDefinitions || [];
  if (!tiles.length) {
    parent.appendChild(node("div", "item", "No map element definitions loaded."));
    return;
  }
  const sorted = [...tiles].sort((left, right) => String(left.key).localeCompare(String(right.key)));
  for (const tile of sorted) {
    const exitCount = Array.isArray(tile.exits) ? tile.exits.length : 0;
    const detailLines = [
      `Type: ${tile.tile_type || "unknown"} · Terrain: ${tile.terrain || "indoor"}`,
      `Footprint: ${tile.footprint_width || 1}×${tile.footprint_height || 1} · Exits: ${exitCount}`,
      tile.description || "",
      tile.implementation_status ? `Status: ${tile.implementation_status}` : "",
    ].filter(Boolean);
    appendRulesTableCard(parent, tile.key, detailLines, `${tile.key} — ${tile.name || "Map element"}`);
  }
}

function renderIconRegistryTables(parent) {
  const icons = state.icons || [];
  if (!icons.length) {
    parent.appendChild(node("div", "item", "No icon registry entries loaded."));
    return;
  }
  const sorted = [...icons].sort((left, right) => String(left.id).localeCompare(String(right.id)));
  for (const icon of sorted) {
    const detailLines = [
      `Category: ${icon.category || "map"}`,
      icon.description || "",
      icon.file ? `File: ${icon.file}` : "",
      icon.fallback ? `Fallback: ${icon.fallback}` : "",
      icon.license ? `License: ${icon.license}` : "",
      icon.attribution ? `Attribution: ${icon.attribution}` : "",
    ].filter(Boolean);
    appendRulesTableCard(parent, icon.id, detailLines, icon.label || icon.id);
  }
}

function renderRulesReference(entries = state.rulesReference) {
  if (!rulesReferenceResultsEl) return;
  rulesReferenceResultsEl.replaceChildren();
  if (!entries.length) {
    rulesReferenceResultsEl.appendChild(node("div", "item muted", "No matching rules entries."));
    return;
  }
  for (const entry of entries) {
    const card = document.createElement("details");
    card.className = "rules-reference-card";
    card.open = entries.length <= 3;
    const summary = document.createElement("summary");
    const titleRow = node("span", "rules-reference-title-row", "");
    titleRow.appendChild(node("span", "rules-reference-title", entry.title || entry.id));
    const status = entry.implementation_status;
    if (status && REFERENCE_STATUS_LABELS[status]) {
      titleRow.appendChild(
        node("span", `rules-reference-status rules-reference-status-${status}`, REFERENCE_STATUS_LABELS[status])
      );
    }
    summary.appendChild(titleRow);
    const metaBits = [];
    if (entry.source_page) metaBits.push(`p.${entry.source_page}`);
    if (entry.category) metaBits.push(entry.category);
    if (metaBits.length) {
      summary.appendChild(node("span", "rules-reference-meta muted", metaBits.join(" · ")));
    }
    card.appendChild(summary);
    if (entry.summary) {
      card.appendChild(node("div", "rules-reference-summary", entry.summary));
    }
    if (entry.keywords?.length) {
      card.appendChild(node("div", "rules-reference-keywords muted", entry.keywords.join(" · ")));
    }
    if (entry.body) {
      const body = node("div", "rules-reference-body");
      entry.body.split("\n").forEach((line) => {
        if (line.trim()) body.appendChild(node("p", "", line));
      });
      card.appendChild(body);
    }
    rulesReferenceResultsEl.appendChild(card);
  }
}

async function refreshRulesReference() {
  const query = rulesReferenceSearchEl?.value?.trim() || "";
  const category = rulesReferenceCategoryEl?.value || "";
  const implementationStatus = rulesReferenceStatusEl?.value || "";
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (category) params.set("category", category);
  if (implementationStatus) params.set("implementation_status", implementationStatus);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const payload = await api(`/api/rules/reference${suffix}`);
  state.rulesReference = payload.entries || [];
  renderRulesReference(state.rulesReference);
}

function renderRulesTables() {
  if (!rulesTablesEl) return;
  rulesTablesEl.replaceChildren();
  const tables = state.rulesTables || {};
  if (tables.ruleset_status) {
    rulesTablesEl.appendChild(node("div", "item muted", tables.ruleset_status));
  }

  const tableCount = [
    ...RULES_TABLE_ORDER.filter((key) => tables[key] != null),
    ...Object.keys(tables).filter((key) => !RULES_TABLE_META_KEYS.has(key) && !RULES_TABLE_ORDER.includes(key)),
  ].length;
  const dungeonGroup = createRulesSectionGroup(
    "Dungeon and adventure tables",
    `${tableCount} tables from dungeon_tables.json plus equipment shop, expert skills, implementation status, and tier training (engine-used keys)`
  );
  renderDungeonRulesTables(dungeonGroup.body, tables);
  rulesTablesEl.appendChild(dungeonGroup.group);

  const bestiaryGroup = createRulesSectionGroup(
    "Monster bestiary",
    "Spawn templates for dungeon, caverns, and fungal grottoes"
  );
  renderMonsterBestiaryTables(bestiaryGroup.body);
  rulesTablesEl.appendChild(bestiaryGroup.group);

  const reactionsGroup = createRulesSectionGroup(
    "Monster reaction tables",
    "Per-foe d6 reactions; mixed groups fall back to category tables above"
  );
  renderMonsterReactionRulesTables(reactionsGroup.body);
  rulesTablesEl.appendChild(reactionsGroup.group);

  const mapElementsGroup = createRulesSectionGroup(
    "Map elements (tiles.json)",
    `${(state.mapElementDefinitions || []).length} starting (01–06) and generated (11–66) map element definitions used for placement, walkable masks, and exits`
  );
  renderMapElementTables(mapElementsGroup.body);
  rulesTablesEl.appendChild(mapElementsGroup.group);

  const classesGroup = createRulesSectionGroup(
    "Class profiles",
    `${(state.classes || []).length} playable classes from classes.json (Life, gear, abilities)`
  );
  renderClassProfileTables(classesGroup.body);
  rulesTablesEl.appendChild(classesGroup.group);

  const iconsGroup = createRulesSectionGroup(
    "Icon registry (icons.json)",
    `${(state.icons || []).length} map and UI icon definitions used on the play map and in the icon editor`
  );
  renderIconRegistryTables(iconsGroup.body);
  rulesTablesEl.appendChild(iconsGroup.group);
}

function renderClassProfileTables(parent) {
  const classes = state.classes || [];
  if (!classes.length) {
    parent.appendChild(node("div", "item", "No class profiles loaded."));
    return;
  }
  for (const profile of classes) {
    const rows = [
      { field: "Life", value: `${profile.base_life}+L${profile.life_offset != null ? ` (offset ${profile.life_offset})` : ""}` },
      { field: "Starting wealth", value: profile.starting_wealth_roll || `${profile.starting_gold}gp` },
      { field: "Starting gear", value: (profile.starting_inventory || []).join(", ") },
      { field: "Abilities", value: (profile.abilities || []).join(", ") },
      { field: "Status", value: profile.implementation_status || "" },
    ];
    appendRulesTableCard(parent, profile.id, rows, profile.name);
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
  renderActiveGames();
  renderSavedGames();
  renderCharacters();
  renderParties();
}

async function refreshCharacters() {
  state.characters = await api("/api/characters");
  renderCharacters();
  renderParties();
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
    await refreshCharacters();
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
  applyCombatFocusLayout(session);
  sessionMode.textContent = session.camped_outside ? "camp" : session.mode;
  updateLogModeControls();

  safeSessionRender("map", () => renderMap(session));
  safeSessionRender("tacticalRoom", () => scheduleTacticalRoomRender(session));
  safeSessionRender("combatHeroChips", () => renderCombatHeroChips(session));
  safeSessionRender("combatHeroDrawer", () => renderCombatHeroDrawer(session));
  safeSessionRender("tileDetail", () => renderTileDetail(session));
  safeSessionRender("iconKey", () => renderIconKey());
  safeSessionRender("mapExits", () => renderMapExitsOverlay(session));
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
  const pendingSearchReward =
    session.mode === "exploration" &&
    Boolean(tile) &&
    session.pending_search_reward_tile_id === tile.id;
  const canSearch = session.mode === "exploration" && Boolean(tile) && !tile.searched && !pendingSearchReward;
  searchBtn.disabled = !canSearch;
  if (searchChoicesEl) searchChoicesEl.classList.toggle("hidden", !pendingSearchReward);
  if (searchChoicesHelp) {
    searchChoicesHelp.classList.toggle("hidden", !pendingSearchReward);
    if (pendingSearchReward) {
      searchChoicesHelp.textContent = `Search found something. Choose Hidden Treasure, Secret Door, Secret Passage, or 1 Clue. Held Clues: ${session.clues_found || 0}.`;
    }
  }
  if (searchTreasureBtn) searchTreasureBtn.disabled = !pendingSearchReward;
  if (searchDoorBtn) searchDoorBtn.disabled = !pendingSearchReward;
  if (searchPassageBtn) searchPassageBtn.disabled = !pendingSearchReward;
  const searchClueHolders = livingPartyMembers(session);
  if (searchClueBtn) searchClueBtn.disabled = !pendingSearchReward || !searchClueHolders.length;
  if (searchClueHolderSelect) {
    searchClueHolderSelect.replaceChildren();
    for (const member of searchClueHolders) {
      const option = document.createElement("option");
      option.value = member.character_id;
      option.textContent = `${member.name} (${member.clues || 0})`;
      searchClueHolderSelect.appendChild(option);
    }
    searchClueHolderSelect.classList.toggle("hidden", !pendingSearchReward);
    searchClueHolderSelect.disabled = !pendingSearchReward || !searchClueHolders.length;
  }
  const restStatus = restEligibility(session);
  restBtn.disabled = !restStatus.ok;
  safeSessionRender("restChoices", () => renderRestChoices(session));
  const inCombat = session.mode === "combat";
  const pendingEncounter = encounterPending(session);
  const canCheckReaction = reactionsOpen(session);
  const immediateLocked = surpriseReactionLocked(session);
  const livingCombatFoes = livingFoesOnTile(session);
  const combatWithdrawDoors = inCombat ? combatWithdrawDoorOptions(session, tile) : [];
  const bribeOutstanding = inCombat && session.reaction_key === "bribe";
  const tradeInfoOutstanding = inCombat && session.reaction_key === "trade_information";
  if (reactionChoicesEl) reactionChoicesEl.classList.toggle("hidden", !inCombat);
  if (checkReactionBtn) checkReactionBtn.disabled = !canCheckReaction;
  if (startCombatBtn) {
    const showStickyStart = pendingEncounter && !shouldUseCombatFocus(session);
    startCombatBtn.classList.toggle("hidden", !showStickyStart);
    startCombatBtn.disabled = !pendingEncounter;
    setButtonTooltip(startCombatBtn, ACTION_TOOLTIPS.startCombat);
  }
  if (encounterHintEl) {
    if (pendingEncounter && !shouldUseCombatFocus(session)) {
      const foes = livingFoesOnTile(session);
      const summary = foes
        .slice(0, 2)
        .map((foe) => `${foe.name} (${foeLevelLabel(foe)})`)
        .join(", ");
      const extra = foes.length > 2 ? ` +${foes.length - 2} more` : "";
      encounterHintEl.textContent = `Foes here: ${summary}${extra}. Enter the encounter, then choose Reactions or immediate action (p.146).`;
      encounterHintEl.classList.remove("hidden");
    } else {
      encounterHintEl.textContent = "";
      encounterHintEl.classList.add("hidden");
    }
  }
  if (combatBtn) {
    combatBtn.textContent = combatRoundButtonLabel(session);
    combatBtn.disabled = !inCombat || !livingCombatFoes.length || immediateLocked;
  }
  if (fleeBtn) fleeBtn.disabled = !inCombat || immediateLocked;
  if (withdrawBtn) withdrawBtn.disabled = !inCombat || !combatWithdrawDoors.length || immediateLocked;
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
  if (tradeInfoSellBtn) {
    tradeInfoSellBtn.classList.toggle("hidden", !tradeInfoOutstanding);
    tradeInfoSellBtn.disabled = !tradeInfoOutstanding || !(session.clues_found > 0);
    if (tradeInfoOutstanding) {
      tradeInfoSellBtn.textContent = `Sell Info (${(session.clues_found || 0) * 25}gp)`;
    }
  }
  if (tradeInfoBuyBtn) {
    tradeInfoBuyBtn.classList.toggle("hidden", !tradeInfoOutstanding);
    tradeInfoBuyBtn.disabled = !tradeInfoOutstanding || partyGoldTotal(session) < 100;
    if (tradeInfoOutstanding) tradeInfoBuyBtn.textContent = "Buy Clue (100gp)";
  }
  if (tradeInfoDeclineBtn) {
    tradeInfoDeclineBtn.classList.toggle("hidden", !tradeInfoOutstanding);
    tradeInfoDeclineBtn.disabled = !tradeInfoOutstanding;
  }
  renderCombatStatus(session);
  safeSessionRender("spellChoices", () => renderSpellChoices(session));
  safeSessionRender("levelUpSpellChoices", () => renderLevelUpSpellChoices(session));
  safeSessionRender("potionChoices", () => renderPotionChoices(session));
  safeSessionRender("recoveryChoices", () => renderRecoveryChoices(session));
  safeSessionRender("economyChoices", () => renderEconomyChoices(session));
  safeSessionRender("clueChoices", () => renderClueChoices(session));
  safeSessionRender("armoryChoices", () => renderArmoryChoices(session));
  renderPendingXpBanner(session);
  safeSessionRender("ongoingQuests", () => renderOngoingQuests(session));
  searchBtn.classList.toggle("hidden", inCombat || !canSearch);
  restBtn.classList.toggle("hidden", inCombat || !restStatus.ok);
  resolveTrapBtn.classList.toggle("hidden", inCombat || !hasTrap);
  claimTreasureBtn.classList.toggle("hidden", inCombat || !hasTreasure || hasTrap);
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

function parseChargedMagicItem(item) {
  const text = String(item || "").trim();
  const match = text.match(/\(\s*(\d+)\s*charges?\s*\)\s*$/i);
  if (!match) return null;
  const charges = Number(match[1]);
  if (!Number.isFinite(charges) || charges < 1) return null;
  const base = text.slice(0, match.index).trim();
  let spell = null;
  const wand = base.match(/^wand\s+of\s+(.+)$/i);
  if (wand) spell = wand[1].trim();
  else {
    const staffOf = base.match(/^staff\s+of\s+(.+)$/i);
    if (staffOf) spell = staffOf[1].trim();
    else {
      const namedStaff = base.match(/^(.+?)\s+staff$/i);
      if (namedStaff) spell = namedStaff[1].trim();
    }
  }
  if (!spell) return null;
  return { item: text, spell, charges, label: base };
}

function heroChargedMagicItems(member) {
  if (member.class_id === "barbarian") return [];
  return (member.inventory || []).map((item) => parseChargedMagicItem(item)).filter(Boolean);
}

function renderSpellChoices(session) {
  if (!spellChoicesEl) return;
  spellChoicesEl.replaceChildren();
  spellChoicesEl.classList.add("hidden");
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

function renderRecoveryChoices(session) {
  if (!recoveryChoicesEl) return;
  recoveryChoicesEl.replaceChildren();
  if (session.mode !== "exploration") {
    recoveryChoicesEl.classList.add("hidden");
    return;
  }
  const tile = currentTile(session);
  const onCurrentTile = Boolean(tile && tile.id === session.map_state.current_tile_id);
  const living = (session.party || []).filter((member) => member.current_life > 0);
  const partyGold = living.reduce((total, member) => total + (member.gold || 0) + (member.bank_gold || 0), 0);
  const fallenHere = onCurrentTile ? fallenMembersForTile(tile, session) : [];
  const outside = (session.fallen_outside_character_ids || [])
    .map((id) => (session.party || []).find((member) => member.character_id === id))
    .filter(Boolean);
  const hasCarry = !session.carried_body_id && fallenHere.length && living.length;
  const hasDrop = Boolean(session.carried_body_id);
  const hasResurrect = outside.length > 0;
  if (!hasCarry && !hasDrop && !hasResurrect) {
    recoveryChoicesEl.classList.add("hidden");
    return;
  }
  recoveryChoicesEl.classList.remove("hidden");
  if (hasCarry) {
    recoveryChoicesEl.appendChild(node("span", "search-label", "Fallen heroes (p.44):"));
    for (const fallen of fallenHere) {
      for (const carrier of living) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "secondary";
        button.textContent = `${carrier.name} carries ${fallen.name}`;
        setButtonTooltip(
          button,
          "Carrier moves to rearguard and cannot make Defense rolls until the body is dropped or delivered outside."
        );
        button.addEventListener("click", () =>
          advance("carry_body", { character_id: carrier.character_id, target_character_id: fallen.character_id })
        );
        recoveryChoicesEl.appendChild(button);
      }
    }
  }
  if (hasDrop) {
    const carrier = (session.party || []).find((member) => member.character_id === session.body_carrier_id);
    const body = (session.party || []).find((member) => member.character_id === session.carried_body_id);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    button.textContent = `Set down ${body?.name || "body"}`;
    setButtonTooltip(button, "Leave the body on this map element.");
    button.addEventListener("click", () => advance("drop_body"));
    recoveryChoicesEl.appendChild(button);
    if (carrier && body) {
      recoveryChoicesEl.appendChild(
        subline(`${carrier.name} is carrying ${body.name}. Exit the dungeon at the entrance to deliver the body outside.`)
      );
    }
  }
  if (hasResurrect) {
    recoveryChoicesEl.appendChild(node("span", "search-label", "Resurrection Ritual (1000gp; L6+ automatic):"));
    recoveryChoicesEl.appendChild(
      subline(`Outside funds: ${partyGold}/1000gp. Home bank funds are available outside the dungeon.`)
    );
    for (const fallen of outside) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.textContent = `Resurrect ${fallen.name}`;
      button.disabled = partyGold < 1000;
      setButtonTooltip(
        button,
        partyGold >= 1000
          ? "Pay 1000gp from survivors. On success the hero returns at full Life."
          : "The party needs 1000gp from living survivors and home bank funds before this ritual can be attempted."
      );
      button.addEventListener("click", () =>
        advance("attempt_resurrection", { target_character_id: fallen.character_id })
      );
      recoveryChoicesEl.appendChild(button);
      const lossButton = document.createElement("button");
      lossButton.type = "button";
      lossButton.className = "danger-button";
      lossButton.textContent = `Lay ${fallen.name} to rest`;
      setButtonTooltip(lossButton, "Accept permanent loss for this fallen hero and choose a new 1st-level hero later.");
      lossButton.addEventListener("click", () =>
        advance("accept_fallen_loss", { target_character_id: fallen.character_id })
      );
      recoveryChoicesEl.appendChild(lossButton);
    }
  }
}

function renderPotionChoices(session) {
  if (!potionChoicesEl) return;
  potionChoicesEl.replaceChildren();
  potionChoicesEl.classList.add("hidden");
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

let restPanelOpen = false;

function countPartyNailBags(party) {
  return (party || []).reduce((total, member) => {
    return (
      total +
      (member.inventory || []).filter((item) => /bag(s)? of nails/i.test(item)).length
    );
  }, 0);
}

function restDoorCount(session) {
  const tile = currentTile(session);
  if (!tile) return 0;
  return (tile.exits || []).filter((exit) => exit.kind === "door" && !exit.door_destroyed).length;
}

function neighborTiles(session, tile) {
  const byId = new Map((session.map_state?.tiles || []).map((entry) => [entry.id, entry]));
  return (tile.exits || [])
    .map((exit) => (exit.destination_tile_id ? byId.get(exit.destination_tile_id) : null))
    .filter(Boolean);
}

function restEligibility(session) {
  if (typeof session.rest_available === "boolean" && session.rest_block_reason !== undefined) {
    return { ok: session.rest_available, reason: session.rest_block_reason || "" };
  }
  if (session.camped_outside) {
    return { ok: false, reason: "You are camped outside the dungeon." };
  }
  if (session.mode !== "exploration") {
    return { ok: false, reason: "The party cannot rest during combat." };
  }
  if (session.rest_used) {
    return { ok: false, reason: "The party has already rested once this adventure (rulebook p.114)." };
  }
  const tile = currentTile(session);
  if (!tile) {
    return { ok: false, reason: "No map location." };
  }
  if (tile.tile_type !== "room") {
    return { ok: false, reason: "Rest requires a cleared room, not a corridor." };
  }
  if ((tile.enemies || []).some((foe) => foe.life > 0)) {
    return { ok: false, reason: "Rest requires a room cleared of foes." };
  }
  const neighbors = neighborTiles(session, tile);
  if (!neighbors.length) {
    return { ok: false, reason: "Rest requires adjacent explored map elements; none are connected yet." };
  }
  if (neighbors.some((neighbor) => (neighbor.enemies || []).some((foe) => foe.life > 0))) {
    return { ok: false, reason: "Adjacent rooms or corridors must also be cleared before resting." };
  }
  if (!restDoorCount(session)) {
    return {
      ok: false,
      reason: "Rest requires doors that can be nailed shut (cavern openings do not qualify).",
    };
  }
  return { ok: true, reason: "" };
}

function memberHasRecoverableAbility(session, member) {
  const expended = session.expended_spells?.[member.character_id] || [];
  if (expended.length) return true;
  const prayerUses = session.healing_prayer_uses?.[member.character_id] || 0;
  if (prayerUses > 0 && (member.spells || []).some((spell) => /healing/i.test(spell))) return true;
  if (member.class_id === "barbarian" && (session.rage_uses_spent?.[member.character_id] || 0) > 0) return true;
  if (member.class_id === "halfling" && (session.luck_points_spent?.[member.character_id] || 0) > 0) return true;
  if (member.class_id === "paladin" && (session.paladin_prayer_spent?.[member.character_id] || 0) > 0) return true;
  return false;
}

function countFoodRations(party) {
  return (party || []).reduce((total, member) => {
    return total + (member.inventory || []).filter((item) => /food ration/i.test(item)).length;
  }, 0);
}

function defaultRestChoice(session, member) {
  if (member.current_life < member.max_life) return "life";
  if (memberHasRecoverableAbility(session, member)) return "ability";
  return "life";
}

function renderRestChoices(session) {
  if (!restChoicesEl) return;
  restChoicesEl.replaceChildren();
  const tile = currentTile(session);
  const restStatus = restEligibility(session);
  const canShow = restPanelOpen && !session.rest_used;
  if (!canShow) {
    restChoicesEl.classList.add("hidden");
    return;
  }
  restChoicesEl.classList.remove("hidden");
  restChoicesEl.appendChild(node("span", "search-label", "Rest (once per adventure)"));

  const guidance = node("div", "ongoing-quest-guidance");
  if (!restStatus.ok) {
    guidance.textContent = restStatus.reason;
  } else {
    const doors = restDoorCount(session);
    const nails = countPartyNailBags(session.party);
    guidance.textContent = `Requires cleared adjacent tiles. ${doors} door(s) can be nailed (${nails} bag(s) of nails in party).`;
  }
  restChoicesEl.appendChild(guidance);

  if (!restStatus.ok) {
    return;
  }

  const nailWrap = node("label", "search-label");
  const nailInput = document.createElement("input");
  nailInput.type = "checkbox";
  nailInput.id = "rest-nail-doors";
  const doors = restDoorCount(session);
  const nails = countPartyNailBags(session.party);
  nailInput.checked = doors > 0 && nails >= doors;
  nailInput.disabled = doors === 0 || nails < doors;
  nailWrap.appendChild(nailInput);
  nailWrap.appendChild(document.createTextNode(` Nail doors shut (${doors} bag(s) needed)`));
  restChoicesEl.appendChild(nailWrap);

  const living = (session.party || []).filter((member) => member.current_life > 0);
  const halflingCook = living.some((member) => member.class_id === "halfling");
  let mealEaterIds = living.map((member) => member.character_id);
  if (halflingCook && !session.nourishing_meal_used) {
    const mealWrap = node("div", "rest-meal-options");
    const mealCheck = document.createElement("input");
    mealCheck.type = "checkbox";
    mealCheck.id = "rest-nourishing-meal";
    const mealLabel = node("label", "search-label");
    mealLabel.appendChild(mealCheck);
    mealLabel.appendChild(
      document.createTextNode(` Nourishing Meal (${countFoodRations(session.party)} ration(s) available)`)
    );
    mealWrap.appendChild(mealLabel);
    const eaterFields = {};
    living.forEach((member) => {
      const eaterRow = node("label", "search-label rest-meal-eater");
      const eaterCheck = document.createElement("input");
      eaterCheck.type = "checkbox";
      eaterCheck.checked = true;
      eaterCheck.dataset.characterId = member.character_id;
      eaterCheck.disabled = true;
      eaterFields[member.character_id] = eaterCheck;
      eaterRow.appendChild(eaterCheck);
      eaterRow.appendChild(document.createTextNode(` ${member.name} eats`));
      mealWrap.appendChild(eaterRow);
    });
    mealCheck.addEventListener("change", () => {
      Object.values(eaterFields).forEach((input) => {
        input.disabled = !mealCheck.checked;
      });
    });
    restChoicesEl.appendChild(mealWrap);
    mealEaterIds = () =>
      mealCheck.checked
        ? Object.entries(eaterFields)
            .filter(([, input]) => input.checked)
            .map(([characterId]) => characterId)
        : [];
  }

  const choiceFields = {};
  living.forEach((member) => {
      const row = node("label", "search-label");
      const select = document.createElement("select");
      select.dataset.characterId = member.character_id;
      ["life", "ability"].forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value === "life" ? "+1 Life" : "Recover ability";
        select.appendChild(option);
      });
      select.value = defaultRestChoice(session, member);
      if (select.value === "ability" && !memberHasRecoverableAbility(session, member)) {
        select.value = "life";
      }
      choiceFields[member.character_id] = select;
      row.appendChild(document.createTextNode(`${member.name}: `));
      row.appendChild(select);
      restChoicesEl.appendChild(row);
    });

  const confirm = document.createElement("button");
  confirm.type = "button";
  confirm.className = "secondary";
  confirm.textContent = "Confirm Rest";
  confirm.addEventListener("click", async () => {
    const rest_choices = {};
    Object.entries(choiceFields).forEach(([characterId, select]) => {
      rest_choices[characterId] = select.value;
    });
    restPanelOpen = false;
    const payload = {
      nail_doors: nailInput.checked,
      rest_choices,
    };
    if (halflingCook && !session.nourishing_meal_used) {
      const mealCheck = document.getElementById("rest-nourishing-meal");
      if (mealCheck?.checked) {
        payload.nourishing_meal = true;
        payload.nourishing_meal_eaters = typeof mealEaterIds === "function" ? mealEaterIds() : mealEaterIds;
      }
    }
    await advance("rest", payload);
  });
  restChoicesEl.appendChild(confirm);
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

function renderClueChoices(session) {
  if (!clueChoicesEl) return;
  clueChoicesEl.replaceChildren();
  if (session.mode !== "exploration") {
    clueChoicesEl.classList.add("hidden");
    return;
  }
  const clues = session.clues_found || 0;
  const living = livingPartyMembers(session);
  const holderSummary = (session.party || [])
    .filter((member) => (member.clues || 0) > 0)
    .map((member) => `${member.name} ${member.clues}`)
    .join(", ");
  clueChoicesEl.classList.remove("hidden");
  clueChoicesEl.appendChild(node("span", "search-label", `Held Clues: ${clues}`));
  clueChoicesEl.appendChild(
    subline(
      clues >= 3
        ? "Your held Clues are spent deliberately on a Secret, eligible spell learning, or a special clue use."
        : "Find Clues with Search. They are held until you choose how to spend them."
    )
  );
  if (holderSummary) clueChoicesEl.appendChild(subline(`Holders: ${holderSummary}`));
  const secretSelect = document.createElement("select");
  secretSelect.className = "search-choice-select";
  secretSelect.disabled = clues < 3 || !living.length;
  for (const member of living) {
    const option = document.createElement("option");
    option.value = member.character_id;
    option.textContent = `${member.name} (${member.clues || 0})`;
    secretSelect.appendChild(option);
  }
  const secretBtn = node("button", "secondary", "Reveal Secret (3 Clues)");
  secretBtn.type = "button";
  secretBtn.disabled = clues < 3 || !living.length;
  setButtonTooltip(secretBtn, ACTION_TOOLTIPS.revealSecretWithClues);
  secretBtn.addEventListener("click", () =>
    advance("reveal_secret_with_clues", { character_id: secretSelect.value || undefined })
  );
  clueChoicesEl.appendChild(secretSelect);
  clueChoicesEl.appendChild(secretBtn);

  const spellRows = living
    .map((member) => ({ member, options: eligibleClueSpellOptions(member) }))
    .filter((row) => row.options.length);
  if (spellRows.length) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "Learn spell (3 Clues)";
    details.appendChild(summary);
    const row = node("div", "level-up-spell-pick-actions");
    for (const { member, options } of spellRows) {
      for (const option of options) {
        const button = node("button", "secondary", `${member.name}: ${option.label}`);
        button.type = "button";
        button.disabled = clues < 3;
        setButtonTooltip(button, ACTION_TOOLTIPS.learnSpellWithClues);
        button.addEventListener("click", () =>
          advance("learn_spell_with_clues", {
            character_id: member.character_id,
            expert_skill_id: option.id,
          })
        );
        row.appendChild(button);
      }
    }
    details.appendChild(row);
    clueChoicesEl.appendChild(details);
  } else if (clues >= 3 && living.some((member) => member.class_id === "druid")) {
    clueChoicesEl.appendChild(
      subline("Druid spell learning from Clues needs the druid expert-spell catalog before it can be offered here.")
    );
  }
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
  const hasBank = Boolean(session.camped_outside);
  if (!hasHealer && !hasAlchemist && !hasBank) {
    economyChoicesEl.classList.add("hidden");
    return;
  }
  economyChoicesEl.classList.remove("hidden");
  if (hasBank) {
    economyChoicesEl.appendChild(node("span", "search-label", "Home bank:"));
    economyChoicesEl.appendChild(
      subline("Deposit carried dungeon gold before re-entering, or withdraw banked gold up to the 200gp carry limit.")
    );
    const depositAll = document.createElement("button");
    depositAll.type = "button";
    depositAll.className = "secondary";
    depositAll.textContent = "Deposit all carried gold";
    depositAll.disabled = !living.some((member) => (member.gold || 0) > 0);
    setButtonTooltip(depositAll, "Each living party member deposits all carried gold into their home bank.");
    depositAll.addEventListener("click", () => advance("deposit_party_bank_gold"));
    economyChoicesEl.appendChild(depositAll);
    for (const member of living) {
      const bankGold = member.bank_gold || 0;
      const carriedGold = member.gold || 0;
      const freeCarry = Math.max(0, effectiveGoldCap(session, member) - carriedGold);
      const depositBtn = document.createElement("button");
      depositBtn.type = "button";
      depositBtn.className = "secondary";
      depositBtn.textContent = `Deposit ${member.name} ${carriedGold}gp`;
      depositBtn.disabled = carriedGold <= 0;
      setButtonTooltip(depositBtn, "Move this hero's carried gold to home bank storage.");
      depositBtn.addEventListener("click", () =>
        advance("deposit_bank_gold", { character_id: member.character_id, gold_amount: carriedGold })
      );
      economyChoicesEl.appendChild(depositBtn);
      const withdraw = Math.min(bankGold, freeCarry);
      const withdrawBtn = document.createElement("button");
      withdrawBtn.type = "button";
      withdrawBtn.className = "secondary";
      withdrawBtn.textContent = `Withdraw ${member.name} ${withdraw}gp`;
      withdrawBtn.disabled = withdraw <= 0;
      setButtonTooltip(withdrawBtn, "Withdraw banked gold up to this hero's carried gold limit.");
      withdrawBtn.addEventListener("click", () =>
        advance("withdraw_bank_gold", { character_id: member.character_id, gold_amount: withdraw })
      );
      economyChoicesEl.appendChild(withdrawBtn);
    }
  }
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

function loadLayoutPrefs() {
  try {
    const saved = JSON.parse(localStorage.getItem(LAYOUT_STORAGE_KEY));
    if (!saved || typeof saved !== "object") return;
    if (typeof saved.logPanelHeight === "number") state.logPanelHeight = saved.logPanelHeight;
    if ("mapStageHeight" in saved) {
      state.mapStageHeight = typeof saved.mapStageHeight === "number" ? saved.mapStageHeight : null;
    }
    if (typeof saved.sidePanelWidth === "number") state.sidePanelWidth = saved.sidePanelWidth;
    if (typeof saved.exitsPanelWidth === "number") state.exitsPanelWidth = saved.exitsPanelWidth;
    if (saved.logMode === "verbose" || saved.logMode === "summary") state.logMode = saved.logMode;
    updateLogModeControls();
    if (typeof saved.mapExitsOpen === "boolean") state.mapExitsOpen = saved.mapExitsOpen;
    if (typeof saved.partyRegroupOpen === "boolean") state.partyRegroupOpen = saved.partyRegroupOpen;
    if (typeof saved.combatRailHeight === "number") state.combatRailHeight = saved.combatRailHeight;
    if (typeof saved.combatSideRailWidth === "number") state.combatSideRailWidth = saved.combatSideRailWidth;
    if (typeof saved.combatHeroDrawerHeight === "number") state.combatHeroDrawerHeight = saved.combatHeroDrawerHeight;
  } catch {
    /* ignore corrupt layout prefs */
  }
}

function saveLayoutPrefs() {
  try {
    localStorage.setItem(
      LAYOUT_STORAGE_KEY,
      JSON.stringify({
        logPanelHeight: state.logPanelHeight,
        mapStageHeight: state.mapStageHeight,
        sidePanelWidth: state.sidePanelWidth,
        exitsPanelWidth: state.exitsPanelWidth,
        logMode: state.logMode,
        mapExitsOpen: state.mapExitsOpen,
        partyRegroupOpen: state.partyRegroupOpen,
        combatRailHeight: state.combatRailHeight,
        combatSideRailWidth: state.combatSideRailWidth,
        combatHeroDrawerHeight: state.combatHeroDrawerHeight,
      })
    );
  } catch {
    /* ignore storage failures */
  }
}

function resetLayoutPref(key) {
  if (!(key in LAYOUT_DEFAULTS)) return;
  state[key] = LAYOUT_DEFAULTS[key];
  applyLayoutCss();
  saveLayoutPrefs();
}

function applyLayoutCss() {
  if (sessionMain) {
    sessionMain.style.setProperty("--side-panel-width", `${Math.round(state.sidePanelWidth)}px`);
    sessionMain.style.setProperty("--combat-side-rail-width", `${Math.round(state.combatSideRailWidth)}px`);
  }
  if (mapLogRow) {
    mapLogRow.style.setProperty("--exits-panel-width", `${Math.round(state.exitsPanelWidth)}px`);
    mapLogRow.style.setProperty("--log-panel-height", `${Math.round(state.logPanelHeight)}px`);
  }
  if (mapLogRow) {
    mapLogRow.style.height = "";
  }
  if (mapLogPanel) {
    mapLogPanel.style.height = "";
  }
  if (logMapResizer) logMapResizer.classList.remove("hidden");
  if (mapStageWrap) {
    if (typeof state.mapStageHeight === "number") {
      mapStageWrap.style.height = `${Math.round(state.mapStageHeight)}px`;
      mapStageWrap.style.flex = "0 0 auto";
    } else {
      mapStageWrap.style.height = "";
      mapStageWrap.style.flex = "1 1 auto";
    }
  }
  if (combatCommandRailEl && sessionMain?.classList.contains("combat-focus")) {
    combatCommandRailEl.style.height = `${Math.round(state.combatRailHeight)}px`;
  } else if (combatCommandRailEl) {
    combatCommandRailEl.style.height = "";
  }
  if (combatHeroDrawerEl && state.combatHeroDrawerId) {
    combatHeroDrawerEl.style.maxHeight = `${Math.round(state.combatHeroDrawerHeight)}px`;
  } else if (combatHeroDrawerEl) {
    combatHeroDrawerEl.style.maxHeight = "";
  }
}

function setupDragResizer(handle, { onDelta, onComplete, onReset }) {
  if (!handle) return;
  let dragDistance = 0;
  handle.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    event.preventDefault();
    dragDistance = 0;
    handle.classList.add("dragging");
    handle.setPointerCapture(event.pointerId);
    let lastX = event.clientX;
    let lastY = event.clientY;
    const move = (moveEvent) => {
      moveEvent.preventDefault();
      const dx = moveEvent.clientX - lastX;
      const dy = moveEvent.clientY - lastY;
      lastX = moveEvent.clientX;
      lastY = moveEvent.clientY;
      dragDistance += Math.abs(dx) + Math.abs(dy);
      onDelta(dx, dy);
    };
    const stop = () => {
      handle.classList.remove("dragging");
      handle.removeEventListener("pointermove", move);
      handle.removeEventListener("pointerup", stop);
      handle.removeEventListener("pointercancel", stop);
      if (handle.hasPointerCapture(event.pointerId)) {
        handle.releasePointerCapture(event.pointerId);
      }
      onComplete?.();
    };
    handle.addEventListener("pointermove", move);
    handle.addEventListener("pointerup", stop);
    handle.addEventListener("pointercancel", stop);
  });
  handle.addEventListener("dblclick", (event) => {
    event.preventDefault();
    if (dragDistance > 4) return;
    onReset?.();
    onComplete?.();
  });
}

function initLayoutResizers() {
  loadLayoutPrefs();
  applyLayoutCss();
  setupDragResizer(logMapResizer, {
    onDelta: (_dx, dy) => {
      state.logPanelHeight = clampFloat(state.logPanelHeight + dy, 120, window.innerHeight * 0.68);
      applyLayoutCss();
    },
    onComplete: saveLayoutPrefs,
    onReset: () => resetLayoutPref("logPanelHeight"),
  });
  setupDragResizer(sessionColumnResizer, {
    onDelta: (dx) => {
      state.sidePanelWidth = clampFloat(state.sidePanelWidth - dx, 280, 720);
      applyLayoutCss();
    },
    onComplete: saveLayoutPrefs,
    onReset: () => resetLayoutPref("sidePanelWidth"),
  });
  setupDragResizer(logExitsResizer, {
    onDelta: (dx) => {
      state.exitsPanelWidth = clampFloat(state.exitsPanelWidth - dx, 160, 520);
      applyLayoutCss();
    },
    onComplete: saveLayoutPrefs,
    onReset: () => resetLayoutPref("exitsPanelWidth"),
  });
  setupDragResizer(mapBottomResizer, {
    onDelta: (_dx, dy) => {
      const current =
        typeof state.mapStageHeight === "number"
          ? state.mapStageHeight
          : mapStageWrap?.getBoundingClientRect().height || 360;
      state.mapStageHeight = clampFloat(current + dy, 180, window.innerHeight * 0.82);
      applyLayoutCss();
      if (state.session && shouldUseCombatFocus(state.session)) {
        scheduleTacticalRoomRender(state.session);
      }
    },
    onComplete: () => {
      saveLayoutPrefs();
      if (state.session && shouldUseCombatFocus(state.session)) {
        scheduleTacticalRoomRender(state.session);
      }
    },
    onReset: () => resetLayoutPref("mapStageHeight"),
  });
  setupDragResizer(combatSideRailResizerEl, {
    onDelta: (dx) => {
      state.combatSideRailWidth = clampFloat(state.combatSideRailWidth + dx, 280, Math.min(520, window.innerWidth * 0.42));
      applyLayoutCss();
    },
    onComplete: () => {
      saveLayoutPrefs();
      if (state.session && shouldUseCombatFocus(state.session)) {
        scheduleTacticalRoomRender(state.session);
      }
    },
    onReset: () => resetLayoutPref("combatSideRailWidth"),
  });
  setupDragResizer(combatCommandRailResizerEl, {
    onDelta: (_dx, dy) => {
      state.combatRailHeight = clampFloat(state.combatRailHeight + dy, 72, Math.min(window.innerHeight * 0.22, 168));
      applyLayoutCss();
    },
    onComplete: saveLayoutPrefs,
    onReset: () => resetLayoutPref("combatRailHeight"),
  });
  setupDragResizer(combatHeroDrawerResizerEl, {
    onDelta: (_dx, dy) => {
      state.combatHeroDrawerHeight = clampFloat(state.combatHeroDrawerHeight + dy, 120, window.innerHeight * 0.5);
      applyLayoutCss();
    },
    onComplete: saveLayoutPrefs,
    onReset: () => resetLayoutPref("combatHeroDrawerHeight"),
  });
}

function isArmoryTile(tile) {
  if (!tile) return false;
  if (tile.content_key === "armory") return true;
  return (tile.objects || []).some((obj) => /armou?ry/i.test(String(obj)));
}

function renderArmoryChoices(session) {
  if (!armoryChoicesEl) return;
  armoryChoicesEl.replaceChildren();
  if (session.mode !== "exploration") {
    armoryChoicesEl.classList.add("hidden");
    return;
  }
  const tile = currentTile(session);
  if (!isArmoryTile(tile)) {
    armoryChoicesEl.classList.add("hidden");
    return;
  }
  const living = (session.party || []).filter((member) => member.current_life > 0);
  armoryChoicesEl.classList.remove("hidden");
  armoryChoicesEl.appendChild(
    node(
      "span",
      "search-label",
      "Armory — swap default weapons from carried gear (class limits apply):"
    )
  );
  for (const member of living) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary";
    if (canEditWeaponDefaults(member)) {
      button.textContent = `${member.name}: change weapons`;
      setButtonTooltip(button, "Set melee/missile defaults from this hero's inventory.");
      button.addEventListener("click", () =>
        openWeaponPickerDialog({ mode: "defaults", source: "session", member, session })
      );
    } else {
      button.textContent = `${member.name}: no weapons carried`;
      button.disabled = true;
      setButtonTooltip(button, "This hero carries no weapons to equip.");
    }
    armoryChoicesEl.appendChild(button);
  }
}

function renderPendingXpBanner(session) {
  if (!pendingXpBanner) return;
  pendingXpBanner.replaceChildren();
  const pending = session.xp_rolls_pending || 0;
  const show =
    pending > 0 &&
    session.mode === "exploration" &&
    (session.xp_system || "classical") === "classical";
  pendingXpBanner.classList.toggle("hidden", !show);
  if (!show) return;
  const note = session.camped_outside
    ? "Spend them on party sheets before re-entering or completing the adventure."
    : "Spend them on party sheets before leaving the dungeon.";
  pendingXpBanner.textContent = `${pending} banked XP roll${pending === 1 ? "" : "s"} pending — ${note}`;
}

function applyMapTransform() {
  if (!mapEl) return;
  mapEl.style.transform = `translate(${state.mapPanX}px, ${state.mapPanY}px)`;
}

function nextMapViewRevision() {
  state.mapViewRevision = (state.mapViewRevision || 0) + 1;
  return state.mapViewRevision;
}

function isCurrentMapViewRevision(viewRevision) {
  return viewRevision == null || viewRevision === state.mapViewRevision;
}

function setMapViewportScroll({ left = null, top = null, instant = false } = {}) {
  if (!mapViewportEl) return;
  const previousBehavior = mapViewportEl.style.scrollBehavior;
  if (instant) mapViewportEl.style.scrollBehavior = "auto";
  if (left !== null) mapViewportEl.scrollLeft = left;
  if (top !== null) mapViewportEl.scrollTop = top;
  if (instant) mapViewportEl.style.scrollBehavior = previousBehavior;
}

function resolveMapTileImageUrl(tile) {
  if (tile?.image) return tile.image;
  const key = tile?.tile_key;
  if (!key) return null;
  return `/assets/tiles/${key}.gif`;
}

function mapViewportSize() {
  return {
    width: mapViewportEl?.clientWidth || 0,
    height: mapViewportEl?.clientHeight || 0,
  };
}

function queueMapFocusRetry(session) {
  if (state.mapFocusRetryTimer) window.clearTimeout(state.mapFocusRetryTimer);
  state.mapFocusRetryTimer = window.setTimeout(() => {
    state.mapFocusRetryTimer = null;
    if (state.session === session) scheduleMapFocus(session);
  }, 80);
}

function setupMapViewportResize() {
  if (!mapViewportEl || typeof ResizeObserver === "undefined" || state.mapViewportResizeObserver) return;
  state.mapViewportResizeObserver = new ResizeObserver(() => {
    const session = state.session;
    if (!session?.map_state?.tiles?.length) return;
    const { width, height } = mapViewportSize();
    if (width <= 0 || height <= 0) return;
    syncMapViewportMode();
    if (state.mapFocusRetryTimer) {
      window.clearTimeout(state.mapFocusRetryTimer);
      state.mapFocusRetryTimer = null;
      scheduleMapFocus(session);
    }
  });
  state.mapViewportResizeObserver.observe(mapViewportEl);
}


function clampMapPan() {
  if (!mapEl || !mapViewportEl) return;
  const mapWidth = mapEl.offsetWidth || mapEl.scrollWidth;
  const mapHeight = mapEl.offsetHeight || mapEl.scrollHeight;
  const viewportWidth = mapViewportEl.clientWidth;
  const viewportHeight = mapViewportEl.clientHeight;
  if (mapWidth <= viewportWidth) {
    state.mapPanX = clampFloat(state.mapPanX, 0, viewportWidth - mapWidth);
  } else {
    state.mapPanX = clampFloat(state.mapPanX, viewportWidth - mapWidth, 0);
  }
  if (mapHeight <= viewportHeight) {
    state.mapPanY = clampFloat(state.mapPanY, 0, viewportHeight - mapHeight);
  } else {
    state.mapPanY = clampFloat(state.mapPanY, viewportHeight - mapHeight, 0);
  }
}

/** Each axis independently chooses scroll-mode (map overflows) or transform-mode (map fits). */
function syncMapViewportMode() {
  if (!mapViewportEl) return;
  const { maxScrollLeft, maxScrollTop } = mapScrollRange();
  if (maxScrollLeft > 0) {
    state.mapPanX = 0;
  } else {
    mapViewportEl.scrollLeft = 0;
  }
  if (maxScrollTop > 0) {
    state.mapPanY = 0;
  } else {
    mapViewportEl.scrollTop = 0;
  }
  clampMapPan();
  applyMapTransform();
}

function resetMapPan() {
  state.mapPanX = 0;
  state.mapPanY = 0;
  if (mapViewportEl) {
    mapViewportEl.scrollLeft = 0;
    mapViewportEl.scrollTop = 0;
  }
  applyMapTransform();
}

function mapScrollRange() {
  return {
    maxScrollLeft: Math.max(0, mapViewportEl.scrollWidth - mapViewportEl.clientWidth),
    maxScrollTop: Math.max(0, mapViewportEl.scrollHeight - mapViewportEl.clientHeight),
  };
}

function applyMapPanDelta(deltaX, deltaY, { smooth = false } = {}) {
  const { maxScrollLeft, maxScrollTop } = mapScrollRange();
  if (maxScrollLeft > 0) {
    state.mapPanX = 0;
  } else {
    mapViewportEl.scrollLeft = 0;
  }
  if (maxScrollTop > 0) {
    state.mapPanY = 0;
  } else {
    mapViewportEl.scrollTop = 0;
  }
  // Flush any pan resets to the DOM before applying scroll offsets, so the
  // CSS transform and scrollLeft/scrollTop never double-count a pan offset.
  applyMapTransform();

  // Compute both scroll targets first so we can issue a SINGLE scrollTo call.
  // Two separate smooth scrollTo calls cancel each other in most browsers —
  // the second call aborts the first animation before it starts.
  const nextLeft = maxScrollLeft > 0 ? clampFloat(mapViewportEl.scrollLeft + deltaX, 0, maxScrollLeft) : null;
  const nextTop  = maxScrollTop  > 0 ? clampFloat(mapViewportEl.scrollTop  + deltaY, 0, maxScrollTop)  : null;

  if (nextLeft !== null || nextTop !== null) {
    if (smooth) {
      const opts = { behavior: "smooth" };
      if (nextLeft !== null) opts.left = nextLeft;
      if (nextTop  !== null) opts.top  = nextTop;
      mapViewportEl.scrollTo(opts);
    } else {
      if (nextLeft !== null) mapViewportEl.scrollLeft = nextLeft;
      if (nextTop  !== null) mapViewportEl.scrollTop  = nextTop;
    }
  }

  if (maxScrollLeft === 0) state.mapPanX -= deltaX;
  if (maxScrollTop  === 0) state.mapPanY -= deltaY;
  if (maxScrollLeft === 0 || maxScrollTop === 0) {
    clampMapPan();
    applyMapTransform();
  }
}

function renderMap(session, { skipFocus = false, viewRevision = null } = {}) {
  dismissMapContextMenu();
  mapEl.replaceChildren();
  const syncRevision = viewRevision ?? state.mapViewRevision;
  const tiles = session.map_state.tiles;
  const bounds = mapBounds(session);
  const boundsWidth = bounds.maxX - bounds.minX + 2 * MAP_RENDER_PAD + 1;
  const boundsHeight = bounds.maxY - bounds.minY + 2 * MAP_RENDER_PAD + 1;
  const cell = currentMapCellSize();
  const pad = MAP_RENDER_PAD;
  let currentTileEl = null;
  mapEl.style.setProperty("--cell", `${cell}px`);
  mapEl.style.width = `${boundsWidth * cell}px`;
  mapEl.style.height = `${boundsHeight * cell}px`;
  mapEl.style.minWidth = `${boundsWidth * cell}px`;
  mapEl.style.minHeight = `${boundsHeight * cell}px`;
  mapZoomLabel.textContent = `${Math.round(state.mapZoom * 100)}%`;

  const cellOwnership = buildMapCellOwnership(session);
  for (const tile of tiles) {
    const el = node("div", `placed-tile ${tile.tile_type}`);
    el.dataset.tileId = tile.id;
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

    const imageUrl = resolveMapTileImageUrl(tile);
    if (imageUrl) {
      el.appendChild(
        mapImageLayer(tile, cell, width, height, cellOwnership, session, imageUrl, () => {
          el.classList.add("no-map-art");
        })
      );
    } else {
      el.classList.add("no-map-art");
    }
    el.appendChild(tileOverlay(tile, session, cellOwnership));
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
  applyMapTransform();
  if (!skipFocus) scheduleMapFocus(session);
  requestAnimationFrame(() => {
    if (isCurrentMapViewRevision(syncRevision)) syncMapViewportMode();
  });
  renderCombatMinimap(session);
}

function renderCombatMinimap(session) {
  if (!combatMinimapEl) return;
  const active = shouldUseCombatFocus(session);
  combatMinimapEl.classList.toggle("hidden", !active);
  combatMinimapEl.setAttribute("aria-hidden", active ? "false" : "true");
  if (!active) {
    combatMinimapEl.replaceChildren();
    return;
  }
  const tiles = session.map_state.tiles || [];
  if (!tiles.length) {
    combatMinimapEl.replaceChildren();
    return;
  }
  const bounds = visibleMapBounds(session);
  const boundsWidth = bounds.maxX - bounds.minX + 3;
  const boundsHeight = bounds.maxY - bounds.minY + 3;
  const pad = 1;
  const maxSize = 180;
  const cell = Math.max(
    3,
    Math.min(Math.floor((maxSize - 10) / boundsWidth), Math.floor((maxSize - 10) / boundsHeight))
  );
  const innerWidth = boundsWidth * cell;
  const innerHeight = boundsHeight * cell;
  const stage = node("div", "combat-minimap-stage");
  stage.style.width = `${innerWidth + 10}px`;
  stage.style.height = `${innerHeight + 10}px`;
  const inner = node("div", "combat-minimap-inner");
  inner.style.width = `${innerWidth}px`;
  inner.style.height = `${innerHeight}px`;
  const currentId = session.map_state.current_tile_id;
  const current = currentTile(session);
  const cellOwnership = buildMapCellOwnership(session);
  for (const tile of tiles) {
    const width = rotatedWidth(tile);
    const height = rotatedHeight(tile);
    const cells = displayedMinimapCells(tile, cellOwnership);
    if (!cells.length) continue;
    const tileBounds = boundsForCells(cells, width, height);
    const el = node("div", `combat-minimap-tile ${tile.tile_type || "room"} clickable`);
    el.dataset.tileId = tile.id;
    if (tile.id === currentId) el.classList.add("current");
    el.style.left = `${(tile.x + tileBounds.minX - bounds.minX + pad) * cell}px`;
    el.style.top = `${(tile.y + tileBounds.minY - bounds.minY + pad) * cell}px`;
    el.style.width = `${(tileBounds.maxX - tileBounds.minX + 1) * cell}px`;
    el.style.height = `${(tileBounds.maxY - tileBounds.minY + 1) * cell}px`;
    el.title = `${tile.title || tile.tile_key}${tile.id === currentId ? " (current room)" : " — click to pan map here"}`;
    el.setAttribute("role", "button");
    el.tabIndex = 0;
    for (const minimapCell of cells) {
      const cellEl = node("span", "combat-minimap-cell");
      cellEl.style.left = `${(minimapCell.x - tileBounds.minX) * cell}px`;
      cellEl.style.top = `${(minimapCell.y - tileBounds.minY) * cell}px`;
      cellEl.style.width = `${cell}px`;
      cellEl.style.height = `${cell}px`;
      el.appendChild(cellEl);
    }
    const focusTile = (event) => {
      event.preventDefault();
      event.stopPropagation();
      focusMapOnTile(session, tile.id);
    };
    el.addEventListener("click", focusTile);
    el.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") focusTile(event);
    });
    inner.appendChild(el);
  }
  if (current) {
    const width = rotatedWidth(current);
    const height = rotatedHeight(current);
    const cells = displayedMinimapCells(current, cellOwnership);
    const tileBounds = boundsForCells(cells, width, height);
    const baseLeft = (current.x + tileBounds.minX - bounds.minX + pad) * cell;
    const baseTop = (current.y + tileBounds.minY - bounds.minY + pad) * cell;
    const currentWidth = (tileBounds.maxX - tileBounds.minX + 1) * cell;
    const currentHeight = (tileBounds.maxY - tileBounds.minY + 1) * cell;
    const livingFoes = (current.enemies || []).filter((foe) => foe.life > 0);
    livingFoes.forEach((foe, index) => {
      const marker = node("span", "combat-minimap-foe");
      marker.title = foe.name;
      marker.style.left = `${baseLeft + (currentWidth * (index + 1)) / (livingFoes.length + 1)}px`;
      marker.style.top = `${baseTop + currentHeight * 0.32}px`;
      inner.appendChild(marker);
    });
    const partyMarker = node("span", "combat-minimap-party");
    partyMarker.title = "Party";
    partyMarker.style.left = `${baseLeft + currentWidth / 2}px`;
    partyMarker.style.top = `${baseTop + currentHeight * 0.68}px`;
    inner.appendChild(partyMarker);
  }
  stage.appendChild(inner);
  combatMinimapEl.replaceChildren(stage);
  combatMinimapEl.title = "Dungeon overview — current room highlighted";
}

function displayedMinimapCells(tile, cellOwnership) {
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const visible = normalizedVisible(tile, width, height);
  const walkable = normalizedWalkable(tile, width, height);
  const cells = [];
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (walkable[y]?.[x] === "0") continue;
      if (isMapCellDisplayed(tile, x, y, visible, cellOwnership)) cells.push({ x, y });
    }
  }
  return cells;
}

function boundsForCells(cells, width, height) {
  if (!cells.length) return { minX: 0, minY: 0, maxX: width - 1, maxY: height - 1 };
  return {
    minX: Math.min(...cells.map((cell) => cell.x)),
    minY: Math.min(...cells.map((cell) => cell.y)),
    maxX: Math.max(...cells.map((cell) => cell.x)),
    maxY: Math.max(...cells.map((cell) => cell.y)),
  };
}

function focusMapOnTile(session, tileId) {
  if (!session || !tileId) return;
  if (tileId === session.map_state.current_tile_id) {
    zoomToCurrentRoom();
    return;
  }
  const tile = (session.map_state?.tiles || []).find((item) => item.id === tileId);
  if (!tile) return;
  const viewRevision = nextMapViewRevision();
  zoomToFullMap({ viewRevision, centerBounds: tileVisibleWorldBounds(tile) });
}

function scheduleMapFocus(session) {
  const currentId = session?.map_state?.current_tile_id;
  if (!currentId) return;
  const previousId = state.mapFocusedTileId;
  const tileChanged = previousId !== currentId;
  if (tileChanged) state.mapFocusedTileId = currentId;
  if (!tileChanged) {
    syncMapViewportMode();
    return;
  }
  const viewRevision = nextMapViewRevision();
  requestAnimationFrame(() => {
    if (!isCurrentMapViewRevision(viewRevision)) return;
    requestAnimationFrame(() => {
      if (!isCurrentMapViewRevision(viewRevision)) return;
      const viewport = mapViewportSize();
      if (!viewport.width || !viewport.height) {
        queueMapFocusRetry(session);
        return;
      }
      const tile = currentTile(session);
      if (!tile) return;
      const bounds = tileVisibleWorldBounds(tile);
      const visibleWidth = Math.max(1, bounds.maxX - bounds.minX + 1);
      const visibleHeight = Math.max(1, bounds.maxY - bounds.minY + 1);
      const nextZoom = clampFloat(
        Math.min(
          (viewport.width * 0.72) / (visibleWidth * MAP_BASE_CELL),
          (viewport.height * 0.72) / (visibleHeight * MAP_BASE_CELL),
          MAP_MAX_ZOOM
        ),
        MAP_MIN_ZOOM,
        MAP_MAX_ZOOM
      );
      if (Math.abs(state.mapZoom - nextZoom) > 0.02) {
        state.mapZoom = nextZoom;
        resetMapPan();
        renderMap(session, { skipFocus: true, viewRevision });
        afterMapRender(() => centerMapOnTile(session, tile, { instant: true }), viewRevision);
        return;
      }
      centerMapOnTile(session, tile, { instant: true });
    });
  });
}

function buildMapCellOwnership(session) {
  const ownership = new Map();
  const tiles = session.map_state.tiles || [];
  const hardTiles = [
    ...tiles.filter((tile) => isEntranceMapElement(tile)),
    ...tiles.filter((tile) => !isEntranceMapElement(tile)),
  ];
  for (const tile of hardTiles) {
    const width = rotatedWidth(tile);
    const height = rotatedHeight(tile);
    const visible = normalizedVisible(tile, width, height);
    const walkable = normalizedWalkable(tile, width, height);
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        if (visible[y]?.[x] === "0") continue;
        if (walkable[y]?.[x] === "0") continue;
        const key = `${tile.x + x},${tile.y + y}`;
        if (ownership.has(key)) continue;
        ownership.set(key, tile.id);
      }
    }
  }
  const softTiles = [...tiles].reverse();
  for (const tile of softTiles) {
    const width = rotatedWidth(tile);
    const height = rotatedHeight(tile);
    const visible = normalizedVisible(tile, width, height);
    const walkable = normalizedWalkable(tile, width, height);
    for (let y = 0; y < height; y += 1) {
      for (let x = 0; x < width; x += 1) {
        if (visible[y]?.[x] === "0") continue;
        if (walkable[y]?.[x] !== "0") continue;
        const key = `${tile.x + x},${tile.y + y}`;
        if (ownership.has(key)) continue;
        ownership.set(key, tile.id);
      }
    }
  }
  return ownership;
}

function isMapCellDisplayed(tile, x, y, visible, cellOwnership) {
  if (visible[y]?.[x] === "0") return false;
  return cellOwnership.get(`${tile.x + x},${tile.y + y}`) === tile.id;
}

function buildVisibleClipSvg(width, height, visible, tile, cellOwnership) {
  const rects = [];
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (!isMapCellDisplayed(tile, x, y, visible, cellOwnership)) continue;
      rects.push({
        x: x / width,
        y: y / height,
        width: 1 / width,
        height: 1 / height,
      });
    }
  }
  if (!rects.length) return null;

  const clipId = `map-image-clip-${mapClipSequence += 1}`;
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.classList.add("map-clip-def");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");

  const defs = document.createElementNS(SVG_NS, "defs");
  const clipPath = document.createElementNS(SVG_NS, "clipPath");
  clipPath.setAttribute("id", clipId);
  clipPath.setAttribute("clipPathUnits", "objectBoundingBox");
  for (const rectData of rects) {
    const rect = document.createElementNS(SVG_NS, "rect");
    rect.setAttribute("x", rectData.x.toFixed(6));
    rect.setAttribute("y", rectData.y.toFixed(6));
    rect.setAttribute("width", rectData.width.toFixed(6));
    rect.setAttribute("height", rectData.height.toFixed(6));
    clipPath.appendChild(rect);
  }
  defs.appendChild(clipPath);
  svg.appendChild(defs);
  return { id: clipId, svg };
}

function tileNeedsOwnershipClip(tile, width, height, visible, cellOwnership) {
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (visible[y]?.[x] === "0") continue;
      const owner = cellOwnership.get(`${tile.x + x},${tile.y + y}`);
      if (owner && owner !== tile.id) return true;
    }
  }
  return false;
}

function mapImageLayer(tile, cell, width, height, cellOwnership, session = null, imageUrl = null, onImageMissing = null) {
  const calibrationSize = tile.editor_cell_size || 80;
  const layoutScale = cell / calibrationSize;
  const visible = normalizedVisible(tile, width, height);
  const maskClipped = visible.some((row) => row.includes("0"));
  const ownershipClipped = tileNeedsOwnershipClip(tile, width, height, visible, cellOwnership);
  let useFull = !maskClipped && !ownershipClipped;

  const stage = node("div", "map-image-stage");
  if (!useFull) {
    const clip = buildVisibleClipSvg(width, height, visible, tile, cellOwnership);
    if (clip) {
      stage.appendChild(clip.svg);
      stage.style.clipPath = `url(#${clip.id})`;
    } else {
      useFull = true;
    }
  }

  const wrap = node("div", "map-image-calibrated");
  wrap.style.width = `${(tile.footprint_width || 1) * calibrationSize}px`;
  wrap.style.height = `${(tile.footprint_height || 1) * calibrationSize}px`;
  wrap.style.transform = `translate(-50%, -50%) scale(${layoutScale})`;
  wrap.appendChild(
    mapImageElement(tile, { className: "map-image-full", imageUrl, onMissing: onImageMissing })
  );
  stage.appendChild(wrap);
  return stage;
}

function mapImageElement(tile, { className, decorative = false, imageUrl = null, onMissing = null } = {}) {
  const calibrationSize = tile.editor_cell_size || 80;
  const image = document.createElement("img");
  image.className = className;
  image.src = imageUrl || resolveMapTileImageUrl(tile) || "";
  image.alt = decorative ? "" : tile.title;
  if (decorative) image.setAttribute("aria-hidden", "true");
  image.style.width = `${(tile.footprint_width || 1) * calibrationSize}px`;
  image.style.height = `${(tile.footprint_height || 1) * calibrationSize}px`;
  image.style.transform = mapImageTransformCalibrated(tile);
  image.addEventListener("error", () => {
    image.classList.add("map-image-missing");
    image.removeAttribute("src");
    if (typeof onMissing === "function") onMissing();
  });
  return image;
}

function mapImageTransformCalibrated(tile) {
  const offset = rotatedOffset(tile.image_offset_x || 0, tile.image_offset_y || 0, tile.rotation || 0);
  const scale = tile.image_scale || 1;
  return `translate(-50%, -50%) translate(${offset.x}px, ${offset.y}px) rotate(${tile.rotation || 0}deg) scale(${scale})`;
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

function tileVisibleWorldBounds(tile) {
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const bounds = visibleCellBounds(tile, width, height);
  return {
    minX: tile.x + bounds.minX,
    maxX: tile.x + bounds.maxX,
    minY: tile.y + bounds.minY,
    maxY: tile.y + bounds.maxY,
  };
}

function visibleMapBounds(session) {
  const tiles = session?.map_state?.tiles || [];
  if (!tiles.length) return { minX: 0, maxX: 0, minY: 0, maxY: 0 };
  const bounds = tiles.map(tileVisibleWorldBounds);
  return {
    minX: Math.min(...bounds.map((item) => item.minX)),
    maxX: Math.max(...bounds.map((item) => item.maxX)),
    minY: Math.min(...bounds.map((item) => item.minY)),
    maxY: Math.max(...bounds.map((item) => item.maxY)),
  };
}

function currentMapCellSize() {
  return Math.max(4, Math.round(MAP_BASE_CELL * state.mapZoom));
}

function mapPixelForWorldPoint(session, worldX, worldY) {
  const bounds = mapBounds(session);
  const cell = currentMapCellSize();
  return {
    x: (worldX - bounds.minX + MAP_RENDER_PAD) * cell,
    y: (worldY - bounds.minY + MAP_RENDER_PAD) * cell,
  };
}

function centerMapOnPoint(pixelX, pixelY, { instant = false } = {}) {
  if (!mapViewportEl) return;
  const { maxScrollLeft, maxScrollTop } = mapScrollRange();
  let nextLeft = null;
  let nextTop = null;
  if (maxScrollLeft > 0) {
    state.mapPanX = 0;
    nextLeft = clampFloat(pixelX - mapViewportEl.clientWidth / 2, 0, maxScrollLeft);
  } else {
    state.mapPanX = mapViewportEl.clientWidth / 2 - pixelX;
  }
  if (maxScrollTop > 0) {
    state.mapPanY = 0;
    nextTop = clampFloat(pixelY - mapViewportEl.clientHeight / 2, 0, maxScrollTop);
  } else {
    state.mapPanY = mapViewportEl.clientHeight / 2 - pixelY;
  }
  setMapViewportScroll({ left: nextLeft, top: nextTop, instant });
  clampMapPan();
  applyMapTransform();
}

function centerMapOnWorldPoint(session, worldX, worldY, options = {}) {
  if (!session) return;
  const point = mapPixelForWorldPoint(session, worldX, worldY);
  centerMapOnPoint(point.x, point.y, options);
}

function centerMapOnWorldBounds(session, bounds, options = {}) {
  centerMapOnWorldPoint(
    session,
    (bounds.minX + bounds.maxX + 1) / 2,
    (bounds.minY + bounds.maxY + 1) / 2,
    options
  );
}

function centerMapOnTile(session, tile, options = {}) {
  if (!session || !tile) return;
  centerMapOnWorldBounds(session, tileVisibleWorldBounds(tile), options);
}

function afterMapRender(callback, viewRevision = null) {
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      if (isCurrentMapViewRevision(viewRevision)) callback();
    });
  });
}

function setMapZoom(nextZoom, { recenter = false } = {}) {
  const viewRevision = nextMapViewRevision();
  state.mapZoom = clampFloat(nextZoom, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  if (recenter) {
    state.lastCenteredTileId = null;
    resetMapPan();
  }
  if (state.session) renderMap(state.session, { skipFocus: true, viewRevision });
  if (recenter) {
    afterMapRender(() => centerCurrentTile({ instant: true }), viewRevision);
  }
}

function zoomToCurrentRoom() {
  const viewRevision = nextMapViewRevision();
  const currentId = state.session?.map_state?.current_tile_id;
  const tile = currentTile(state.session);
  const viewport = mapViewportSize();
  if (!tile || !viewport.width || !viewport.height) {
    return;
  }
  const bounds = tileVisibleWorldBounds(tile);
  const visibleWidth = Math.max(1, bounds.maxX - bounds.minX + 1);
  const visibleHeight = Math.max(1, bounds.maxY - bounds.minY + 1);
  const target = Math.min(
    (viewport.width * 0.72) / (visibleWidth * MAP_BASE_CELL),
    (viewport.height * 0.72) / (visibleHeight * MAP_BASE_CELL),
    MAP_MAX_ZOOM
  );
  state.mapZoom = clampFloat(target, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  resetMapPan();
  if (state.session) renderMap(state.session, { skipFocus: true, viewRevision });
  afterMapRender(() => {
    const targetTile = (state.session?.map_state?.tiles || []).find((item) => item.id === currentId);
    if (targetTile) centerMapOnTile(state.session, targetTile, { instant: true });
  }, viewRevision);
}

function zoomToFullMap({ viewRevision = null, centerBounds = null } = {}) {
  const revision = viewRevision ?? nextMapViewRevision();
  const viewport = mapViewportSize();
  if (!state.session || !viewport.width || !viewport.height) return;
  const bounds = visibleMapBounds(state.session);
  const targetBounds = centerBounds || bounds;
  const boundsWidth = bounds.maxX - bounds.minX + 2 * MAP_RENDER_PAD + 1;
  const boundsHeight = bounds.maxY - bounds.minY + 2 * MAP_RENDER_PAD + 1;
  const availableWidth = Math.max(80, viewport.width - 48);
  const availableHeight = Math.max(80, viewport.height - 48);
  const target = Math.min(
    availableWidth / (boundsWidth * MAP_BASE_CELL),
    availableHeight / (boundsHeight * MAP_BASE_CELL),
    1.2
  );
  state.mapZoom = clampFloat(target * 0.92, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  resetMapPan();
  if (state.session) renderMap(state.session, { skipFocus: true, viewRevision: revision });
  afterMapRender(() => centerMapOnWorldBounds(state.session, targetBounds, { instant: true }), revision);
}

function panMap(deltaX, deltaY) {
  applyMapPanDelta(deltaX, deltaY, { smooth: true });
}

function centerCurrentTile(options = {}) {
  const tile = currentTile(state.session);
  if (tile) centerMapOnTile(state.session, tile, options);
}

function centerMapOn(element) {
  const { maxScrollLeft, maxScrollTop } = mapScrollRange();
  const elCenterX = element.offsetLeft + element.offsetWidth / 2;
  const elCenterY = element.offsetTop + element.offsetHeight / 2;
  if (maxScrollLeft > 0) {
    state.mapPanX = 0;
    mapViewportEl.scrollLeft = clampFloat(elCenterX - mapViewportEl.clientWidth / 2, 0, maxScrollLeft);
  } else {
    state.mapPanX = mapViewportEl.clientWidth / 2 - elCenterX;
  }
  if (maxScrollTop > 0) {
    state.mapPanY = 0;
    mapViewportEl.scrollTop = clampFloat(elCenterY - mapViewportEl.clientHeight / 2, 0, maxScrollTop);
  } else {
    state.mapPanY = mapViewportEl.clientHeight / 2 - elCenterY;
  }
  clampMapPan();
  applyMapTransform();
}

function mapContentPointForClient(clientX, clientY) {
  const rect = mapViewportEl.getBoundingClientRect();
  const pointerX = clampFloat(clientX - rect.left, 0, rect.width || mapViewportEl.clientWidth || 1);
  const pointerY = clampFloat(clientY - rect.top, 0, rect.height || mapViewportEl.clientHeight || 1);
  const { maxScrollLeft, maxScrollTop } = mapScrollRange();
  const contentX = maxScrollLeft > 0 ? mapViewportEl.scrollLeft + pointerX : pointerX - state.mapPanX;
  const contentY = maxScrollTop > 0 ? mapViewportEl.scrollTop + pointerY : pointerY - state.mapPanY;
  const mapWidth = mapEl.offsetWidth || mapEl.scrollWidth || 1;
  const mapHeight = mapEl.offsetHeight || mapEl.scrollHeight || 1;
  return {
    ratioX: clampFloat(contentX / mapWidth, 0, 1),
    ratioY: clampFloat(contentY / mapHeight, 0, 1),
    pointerX,
    pointerY,
  };
}

function positionMapContentAtPointer(ratioX, ratioY, pointerX, pointerY, { instant = false } = {}) {
  const targetX = ratioX * (mapEl.offsetWidth || mapEl.scrollWidth || 1);
  const targetY = ratioY * (mapEl.offsetHeight || mapEl.scrollHeight || 1);
  const { maxScrollLeft, maxScrollTop } = mapScrollRange();
  let nextLeft = null;
  let nextTop = null;
  if (maxScrollLeft > 0) {
    state.mapPanX = 0;
    nextLeft = clampFloat(targetX - pointerX, 0, maxScrollLeft);
  } else {
    state.mapPanX = pointerX - targetX;
  }
  if (maxScrollTop > 0) {
    state.mapPanY = 0;
    nextTop = clampFloat(targetY - pointerY, 0, maxScrollTop);
  } else {
    state.mapPanY = pointerY - targetY;
  }
  setMapViewportScroll({ left: nextLeft, top: nextTop, instant });
  clampMapPan();
  applyMapTransform();
}

function zoomMapAtClientPoint(nextZoom, clientX, clientY) {
  if (!state.session || !mapEl || !mapViewportEl) return;
  const viewRevision = nextMapViewRevision();
  const focus = mapContentPointForClient(clientX, clientY);
  state.mapZoom = clampFloat(nextZoom, MAP_MIN_ZOOM, MAP_MAX_ZOOM);
  renderMap(state.session, { skipFocus: true, viewRevision });
  positionMapContentAtPointer(focus.ratioX, focus.ratioY, focus.pointerX, focus.pointerY, { instant: true });
}

function handleMapWheel(event) {
  event.preventDefault();
  const factor = event.deltaY < 0 ? 1.01 : 1 / 1.01;
  zoomMapAtClientPoint(state.mapZoom * factor, event.clientX, event.clientY);
}

function startMapPan(event) {
  if (event.button !== 0 && event.button !== 1) return;
  if (
    event.button === 0 &&
    event.target.closest(
      ".map-controls-overlay, .map-exit-menu, .map-context-menu, button, [role=\"button\"], a, input, label, select, textarea"
    )
  ) {
    return;
  }
  mapViewportEl.setPointerCapture(event.pointerId);
  const startX = event.clientX;
  const startY = event.clientY;
  let lastX = event.clientX;
  let lastY = event.clientY;
  let dragging = false;

  const move = (moveEvent) => {
    const totalMove = Math.hypot(moveEvent.clientX - startX, moveEvent.clientY - startY);
    const dx = lastX - moveEvent.clientX;
    const dy = lastY - moveEvent.clientY;
    lastX = moveEvent.clientX;
    lastY = moveEvent.clientY;
    if (!dragging && totalMove < 4) return;
    dragging = true;
    moveEvent.preventDefault();
    mapViewportEl.classList.add("panning");
    applyMapPanDelta(dx, dy);
  };

  const stop = (stopEvent) => {
    if (dragging) {
      state.mapSuppressClick = true;
      if (stopEvent) stopEvent.preventDefault();
    }
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
  state.partySlotIds = partySlotsFromIds(party.character_ids);
  partyName.value = party.name;
  saveParty.textContent = "Update Party";
  cancelPartyEdit.classList.remove("hidden");
  renderCharacters();
  renderParties();
}

function cancelPartyEditMode() {
  state.editingPartyId = null;
  state.partySlotIds = emptyPartySlots();
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
    setStatus("Equipment slots saved");
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
      "Buy before or between adventures. Roster gold is home bank gold; dungeon-carried gold is limited to 200gp.";
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

function tileOverlay(tile, session, cellOwnership, { skipContentMarkers = false } = {}) {
  const overlay = node("div", "map-tile-overlay");
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const facingExits = playerFacingExits(session, tile);
  const sideLabels = exitSideLabelsForExits(facingExits);
  const isCurrent = tile.id === session.map_state.current_tile_id;
  overlay.style.gridTemplateColumns = `repeat(${width}, minmax(0, 1fr))`;
  overlay.style.gridTemplateRows = `repeat(${height}, minmax(0, 1fr))`;
  const walkable = normalizedWalkable(tile, width, height);
  const visible = normalizedVisible(tile, width, height);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const isHidden = !isMapCellDisplayed(tile, x, y, visible, cellOwnership);
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
  for (const exit of facingExits) {
    overlay.appendChild(mapExitMarker(tile, exit, width, height, sideLabels.get(exit.id), session));
  }
  const contentMarkers = skipContentMarkers ? null : tileContentMarkers(tile, session, width, height);
  if (contentMarkers) overlay.appendChild(contentMarkers);
  return overlay;
}

function mapExitMarker(tile, exit, width, height, sideLabel, session) {
  const onCurrentTile = tile.id === session.map_state.current_tile_id;
  const canUse =
    onCurrentTile &&
    exit.status !== "blocked" &&
    (session.mode === "exploration" || session.mode === "combat");
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
      openMapExitMenu(session, tile, exit, marker, sideLabel);
    });
  }
  const label = exitDisplayLabel(exit, sideLabel);
  const doorHint = exit.kind === "door" ? (exit.door_open ? " - open" : " - closed") : "";
  marker.title = exit.status === "blocked"
    ? `${label} - dead end`
    : `${label}${doorHint}${exit.door_result ? ` (${exit.door_result})` : ""} — click for actions`;
  const cellW = 100 / width;
  const cellH = 100 / height;
  const portal = exitPortalDisplayLocal(tile, exit, width, height);
  const x = portal.edge.x;
  const y = portal.edge.y;
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

function tileHasActiveTrap(tile) {
  return Boolean(tile?.trap_key && !tile.trap_resolved);
}

function tileHasClaimableTreasure(tile) {
  return Boolean(
    tile &&
      !tile.treasure_claimed &&
      (tile.treasure_gold || (tile.treasure_items || []).length > 0)
  );
}

function tileContentMarkers(tile, session, width, height) {
  const markers = [];
  const liveEnemies = (tile.enemies || []).filter((enemy) => enemy.life > 0);
  const defeatedEnemies = tile.defeated_enemies || [];
  const objects = tile.objects || [];
  const fallen = fallenMembersForTile(tile, session);
  const isCurrent = tile.id === session.map_state.current_tile_id;
  const canInteract = session.mode === "exploration" && isCurrent;
  const canMonsterMenu =
    isCurrent && liveEnemies.length && (encounterPending(session) || session.mode === "combat");
  if (liveEnemies.length) {
    if (canMonsterMenu) {
      markers.push(
        interactiveContentMarker(
          "monster",
          `${liveEnemies.length} active foe${liveEnemies.length === 1 ? "" : "s"}`,
          true,
          (marker) => openMapMonsterMenu(session, tile, marker),
          liveEnemies.length
        )
      );
    } else {
      markers.push(
        contentMarker("monster", `${liveEnemies.length} active foe${liveEnemies.length === 1 ? "" : "s"}`, liveEnemies.length)
      );
    }
  }
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
  if (tileHasClaimableTreasure(tile) || objects.some((item) => /treasure/i.test(item)) || (tile.treasure_summary && !tile.treasure_claimed)) {
    const treasureTitle = tile.treasure_summary || "Treasure present";
    markers.push(
      interactiveContentMarker("treasure", treasureTitle, canInteract, (marker) =>
        openMapTreasureMenu(session, tile, marker)
      )
    );
  }
  if (tileHasActiveTrap(tile) || objects.some((item) => /trap/i.test(item))) {
    const trapTitle = tile.trap_key ? `Trap: ${tile.trap_key} (L${tile.trap_level || "?"})` : "Trap present";
    markers.push(
      interactiveContentMarker("trap", trapTitle, canInteract, (marker) => openMapTrapMenu(session, tile, marker))
    );
  }
  if (fallen.length) markers.push(contentMarker("fallen", `${fallen.map((member) => member.name).join(", ")} fallen here`, fallen.length));
  for (const group of detachedGroupsOnTile(session, tile.id)) {
    const names = detachedHeroNames(session, group.character_ids);
    if (!names.length) continue;
    const reason = group.reason ? ` (${group.reason})` : "";
    markers.push(
      contentMarker("detached", `${names.join(", ")} left behind${reason}`, names.length)
    );
  }
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

function interactiveContentMarker(kind, title, canInteract, onOpen, count = 0) {
  const marker = contentMarker(kind, title, count);
  if (!canInteract || typeof onOpen !== "function") return marker;
  marker.classList.add("clickable");
  marker.setAttribute("role", "button");
  marker.tabIndex = 0;
  marker.title = `${title} — click for actions`;
  const open = (event) => {
    event.preventDefault();
    event.stopPropagation();
    onOpen(marker);
  };
  marker.addEventListener("click", open);
  marker.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") open(event);
  });
  return marker;
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

const CLASS_ICON_IDS = {
  warrior: "class-warrior",
  barbarian: "class-barbarian",
  cleric: "class-cleric",
  rogue: "class-rogue",
  wizard: "class-wizard",
  elf: "class-elf",
  dwarf: "class-dwarf",
  halfling: "class-halfling",
  ranger: "class-ranger",
  swashbuckler: "class-swashbuckler",
  paladin: "class-paladin",
  druid: "class-druid",
  acrobat: "class-acrobat",
  gnome: "class-gnome",
  mushroom_monk: "class-monk",
  kukla: "class-kukla",
  light_gladiator: "class-gladiator",
  illusionist: "class-illusionist",
};

function classIconGraphic(classId, className = "") {
  const iconId = CLASS_ICON_IDS[(classId || "").toLowerCase()] || "class-hero";
  const definition = iconDefinition(iconId);
  if (className && !definition.label) definition.label = className;
  const wrap = node("span", "party-class-icon");
  wrap.appendChild(iconGraphic(definition, "party-class-icon-graphic", className || definition.label));
  return wrap;
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

const EXIT_DIRECTION_DELTA = {
  north: [0, -1],
  south: [0, 1],
  east: [1, 0],
  west: [-1, 0],
};

function isEntranceMapElement(tile) {
  const key = String(tile?.tile_key || "");
  return (
    tile?.content_key === "entrance" ||
    (/^0[1-6]$/.test(key) && (tile?.exits || []).some((exit) => exit.dungeon_exit))
  );
}

function exitCellsLocal(exit, width, height) {
  const span = clampExitSpan(exit, width, height);
  const x = Math.max(0, Math.min(exit.x || 0, width - 1));
  const y = Math.max(0, Math.min(exit.y || 0, height - 1));
  if (exit.direction === "north" || exit.direction === "south") {
    return Array.from({ length: span }, (_, index) => [x + index, y]);
  }
  return Array.from({ length: span }, (_, index) => [x, y + index]);
}

function authoredExitPortalLocal(exit, width, height) {
  const [edgeX, edgeY] = exitCellsLocal(exit, width, height)[0] || [0, 0];
  const [dx, dy] = EXIT_DIRECTION_DELTA[exit.direction] || [0, 0];
  return {
    edge: { x: edgeX, y: edgeY },
    outside: { x: edgeX + dx, y: edgeY + dy },
  };
}

function exitPortalEdgeLocal(tile, exit, width, height) {
  const walkable = normalizedWalkable(tile, width, height);
  const visible = normalizedVisible(tile, width, height);
  const [dx, dy] = EXIT_DIRECTION_DELTA[exit.direction] || [0, 0];
  const [startX, startY] = exitCellsLocal(exit, width, height)[0] || [0, 0];
  let edgeX = startX;
  let edgeY = startY;
  let probeX = edgeX + dx;
  let probeY = edgeY + dy;
  while (probeX >= 0 && probeY >= 0 && probeX < width && probeY < height) {
    if (visible[probeY]?.[probeX] === "0") break;
    if (walkable[probeY]?.[probeX] !== "0") {
      edgeX = probeX;
      edgeY = probeY;
    }
    probeX += dx;
    probeY += dy;
  }
  return {
    edge: { x: edgeX, y: edgeY },
    outside: { x: probeX, y: probeY },
  };
}

function exitPortalDisplayLocal(tile, exit, width, height) {
  if (isEntranceMapElement(tile)) return authoredExitPortalLocal(exit, width, height);
  return exitPortalEdgeLocal(tile, exit, width, height);
}

function tileOccupiedCellKeys(tile) {
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const walkable = normalizedWalkable(tile, width, height);
  const keys = new Set();
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      if (walkable[y]?.[x] !== "0") keys.add(`${tile.x + x},${tile.y + y}`);
    }
  }
  return keys;
}

function exitOutsideCellKey(tile, exit) {
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const { x, y } = exitPortalEdgeLocal(tile, exit, width, height).outside;
  return `${tile.x + x},${tile.y + y}`;
}

function isExitOnDisplayedCell(tile, exit, cellOwnership) {
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const visible = normalizedVisible(tile, width, height);
  return exitCellsLocal(exit, width, height).some(([x, y]) =>
    isMapCellDisplayed(tile, x, y, visible, cellOwnership)
  );
}

function isExitOnWalkableCell(tile, exit) {
  const width = rotatedWidth(tile);
  const height = rotatedHeight(tile);
  const walkable = normalizedWalkable(tile, width, height);
  return exitCellsLocal(exit, width, height).some(([x, y]) => walkable[y]?.[x] !== "0");
}

/** Exits the player can see on the map and act on (excludes hidden/truncated/invalid markers). */
function playerFacingExits(session, tile) {
  if (!tile) return [];
  const cellOwnership = buildMapCellOwnership(session);
  return (tile.exits || []).filter((exit) => {
    if (!isExitOnDisplayedCell(tile, exit, cellOwnership)) return false;
    if (!isExitOnWalkableCell(tile, exit)) return false;
    return true;
  });
}

function exitSideLabelsForExits(exits) {
  const labels = new Map();
  const counts = new Map();
  for (const exit of exits || []) {
    const direction = exit.direction || "north";
    const nextCount = (counts.get(direction) || 0) + 1;
    counts.set(direction, nextCount);
    labels.set(exit.id, `${titleCase(direction)} ${nextCount}`);
  }
  return labels;
}

function clampFloat(value, min, max) {
  const number = Number.parseFloat(value);
  if (Number.isNaN(number)) return min;
  return Math.max(min, Math.min(max, number));
}

function rotateMapCell(x, y, width, height, rotation) {
  const turns = ((rotation || 0) / 90) % 4;
  if (turns === 1) return { x: height - 1 - y, y: x };
  if (turns === 2) return { x: width - 1 - x, y: height - 1 - y };
  if (turns === 3) return { x: y, y: width - 1 - x };
  return { x, y };
}

function rotateMapGrid(rows, width, height, rotation, emptyValue = "0") {
  if (!rotation) return rows;
  const rotatedWidth = rotation === 90 || rotation === 270 ? height : width;
  const rotatedHeight = rotation === 90 || rotation === 270 ? width : height;
  const rotated = Array.from({ length: rotatedHeight }, () => Array.from({ length: rotatedWidth }, () => emptyValue));
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const cell = rotateMapCell(x, y, width, height, rotation);
      rotated[cell.y][cell.x] = String(rows[y] || "")[x] || emptyValue;
    }
  }
  return rotated.map((row) => row.join(""));
}

function rotateMapRows(rows, width, height, rotation) {
  return rotateMapGrid(rows, width, height, rotation, "0").map((row) =>
    Array.from(row, (char) => (char === "0" ? "0" : "1")).join("")
  );
}

function walkableSourceRows(tile) {
  return Array.isArray(tile.walkable) ? tile.walkable : [];
}

function normalizedWalkable(tile, width, height) {
  const rows = walkableSourceRows(tile);
  return Array.from({ length: height }, (_, y) => {
    const source = String(rows[y] || "");
    return Array.from({ length: width }, (__, x) => (source[x] === "0" ? "0" : "1")).join("");
  });
}

function cellShape(tile, x, y) {
  const rows = Array.isArray(tile.cell_shapes) ? tile.cell_shapes : [];
  return rows[y]?.[x] || "F";
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

function tileRoomSummary(tile, session) {
  const parts = [tile.title];
  const livingFoes = (tile.enemies || []).filter((foe) => foe.life > 0);
  if (livingFoes.length) parts.push(`${livingFoes.length} foe${livingFoes.length === 1 ? "" : "s"}`);
  if (tile.treasure_summary && !tile.treasure_claimed) parts.push("treasure");
  if (tile.trap_key && !tile.trap_resolved) parts.push("trap");
  if (tile.healer_available) parts.push("healer");
  if (tile.alchemist_available) parts.push("alchemist");
  if (session?.camped_outside) parts.push("camped outside");
  return parts.join(" · ");
}

function renderTileDetail(session) {
  const tile = currentTile(session);
  tileDetail.replaceChildren();
  if (!tile) {
    tileDetail.appendChild(node("div", "map-overlay-empty", "No current room."));
    return;
  }

  const details = document.createElement("details");
  details.className = "map-overlay-details map-room-details";
  details.open = Boolean(state.mapRoomOpen);
  const summary = document.createElement("summary");
  summary.textContent = tileRoomSummary(tile, session);
  details.appendChild(summary);

  const body = node("div", "map-room-body");
  if (tile.image) {
    const image = document.createElement("img");
    image.src = tile.image;
    image.alt = tile.title;
    image.style.transform = `rotate(${tile.rotation || 0}deg)`;
    body.appendChild(image);
  }

  const info = node("div", "map-room-info");
  info.appendChild(node("h3", "map-room-title", tile.title));
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
  info.appendChild(node("p", "map-room-description", tile.description));
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
      `${campaignModeLabel(session.xp_system)}: ${session.clues_found || 0} Clues · ` +
        `${session.minor_encounters_defeated || 0}/10 minors · ` +
        `${session.xp_rolls_pending || 0} roll(s) · ` +
        `${session.slower_xp_bank || 0} banked · ` +
        `${session.old_school_xp_tally || 0} Old School tally`
    )
  );
  const envLabel =
    session.environment === "caverns"
      ? "Caverns"
      : session.environment === "fungal_grottoes"
        ? "Fungal grottoes"
        : "Dungeon";
  const boundsLabel =
    session.map_bounds_mode === "paper"
      ? `Paper ${session.map_state?.width || 20}×${session.map_state?.height || 28}`
      : "Unlimited map";
  info.appendChild(subline(`Environment: ${envLabel} · Map: ${boundsLabel}`));
  if (tile.environment && tile.environment !== "dungeon") {
    info.appendChild(subline(`This map element: ${tile.environment.replace("_", " ")}`));
  }
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
  const facingExits = playerFacingExits(session, tile);
  const sideLabels = exitSideLabelsForExits(facingExits);
  info.appendChild(
    subline(
      `Exits: ${facingExits
        .map((exit) => {
          const label = exitDisplayLabel(exit, sideLabels.get(exit.id));
          const doorState = exit.kind === "door" ? (exit.door_open ? " open" : " closed") : "";
          return `${label} ${exit.status}${doorState}`;
        })
        .join(", ") || "none visible"}`
    )
  );
  body.appendChild(info);
  details.appendChild(body);
  details.addEventListener("toggle", () => {
    state.mapRoomOpen = details.open;
  });
  tileDetail.appendChild(details);
}

function renderIconKey() {
  if (!iconKey) return;
  iconKey.replaceChildren();
  const details = document.createElement("details");
  details.className = "map-overlay-details map-icon-key-details";
  details.open = Boolean(state.mapIconKeyOpen);
  const summary = document.createElement("summary");
  summary.textContent = "Icon key";
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
    state.mapIconKeyOpen = details.open;
  });
  iconKey.appendChild(details);
}

function mapExitsSummary(session) {
  const tile = currentTile(session);
  if (!tile) return "Exits";
  const exits = playerFacingExits(session, tile);
  if (!exits.length) {
    const hidden = (tile.exits || []).length;
    return hidden ? "Exits · none reachable" : "Exits · none";
  }
  const sideLabels = exitSideLabelsForExits(exits);
  const labels = exits.slice(0, 3).map((exit) => compactExitLabel(exit, sideLabels.get(exit.id), true));
  const extra = exits.length > 3 ? ` +${exits.length - 3}` : "";
  return `Exits (${exits.length}) · ${labels.join(" · ")}${extra}`;
}

function estimateExitRowWeight(session, exit, mode) {
  if (exit.status === "blocked") return 1;
  if (mode === "combat") return 1;
  if (exit.kind === "door" && !exit.door_open) {
    const doorOptions = collectDoorActionOptions(session, exit);
    const groups = groupDoorActionOptions(doorOptions);
    let actionRows = 0;
    for (const [, options] of groups) {
      if (options.some((option) => !option.disabled)) actionRows += 1;
    }
    let weight = 2 + actionRows;
    if (!exit.door_type) weight += 1;
    if (exit.door_type === "iron") weight += 1;
    return Math.min(5, Math.max(2, weight));
  }
  return 1;
}

function sumExitRowWeights(session, tile) {
  const exits = playerFacingExits(session, tile);
  const mode = effectiveSessionMode(session);
  let total = 0;
  for (const exit of exits) {
    total += estimateExitRowWeight(session, exit, mode);
  }
  return Math.max(1, total);
}

function bindMapExitsScrollHint(shell) {
  if (!shell || shell.dataset.scrollBound === "1") return;
  const scroll = shell.querySelector(".map-exits-scroll");
  const hint = shell.querySelector(".map-exits-scroll-hint");
  if (!scroll) return;
  shell.dataset.scrollBound = "1";
  const update = () => {
    const scrollable = scroll.scrollHeight > scroll.clientHeight + 2;
    const atTop = scroll.scrollTop <= 2;
    const atBottom = scroll.scrollTop + scroll.clientHeight >= scroll.scrollHeight - 2;
    const exitRows = scroll.querySelectorAll(".exit-row").length;
    const rowHeight = scroll.querySelector(".exit-row")?.offsetHeight || 76;
    const visibleEstimate = scroll.clientHeight > 0 ? Math.max(1, Math.floor(scroll.clientHeight / rowHeight)) : 1;
    const hiddenCount = Math.max(0, exitRows - visibleEstimate);
    scroll.classList.toggle("has-scroll", scrollable);
    scroll.classList.toggle("at-scroll-top", atTop);
    scroll.classList.toggle("at-scroll-bottom", atBottom);
    if (hint) {
      if (!scrollable) {
        hint.classList.add("hidden");
      } else {
        hint.classList.remove("hidden");
        const more = hiddenCount > 0 ? `${hiddenCount} more exit${hiddenCount === 1 ? "" : "s"} — ` : "";
        hint.textContent = atBottom ? `${more}End of list`.trim() : `${more}Scroll for more exits ↓`.trim();
      }
    }
  };
  update();
  scroll.addEventListener("scroll", update, { passive: true });
  if (typeof ResizeObserver !== "undefined") {
    const observer = new ResizeObserver(update);
    observer.observe(shell);
    observer.observe(scroll);
    for (const child of scroll.children) observer.observe(child);
  }
  window.setTimeout(update, 0);
  window.setTimeout(update, 120);
}

function createExitRowElement(session, tile, exit, sideLabels, mode, { dock = false } = {}) {
  const row = node("div", `exit-row${exit.status === "blocked" ? " exit-row-blocked" : ""}${dock ? " exit-row-dock" : ""}`);
  const head = node("div", "exit-row-head");
  head.appendChild(node("strong", "exit-row-label", exitDisplayLabel(exit, sideLabels.get(exit.id))));
  const status = node("span", "exit-row-status", exitStatusLabel(exit));
  if (exit.kind === "door" && !exit.door_open && exit.status !== "blocked") {
    status.title = doorTypeHint(exit, session);
  }
  head.appendChild(status);
  row.appendChild(head);

  const rowActions = node("div", "exit-row-actions");
  appendExitRowActions(session, tile, exit, sideLabels.get(exit.id), rowActions, mode, { dock });
  row.appendChild(rowActions);
  return row;
}

function buildExitListElement(session) {
  const tile = currentTile(session);
  if (!tile) return null;
  const exits = playerFacingExits(session, tile);
  if (!exits.length) return null;
  const mode = effectiveSessionMode(session);
  const sideLabels = exitSideLabelsForExits(exits);
  const list = node("div", "exit-list");
  for (const exit of exits) {
    list.appendChild(createExitRowElement(session, tile, exit, sideLabels, mode, { dock: true }));
  }
  return list;
}

function renderMapExitsOverlay(session) {
  if (!mapExitsPanel) return;
  mapExitsPanel.replaceChildren();
  if (session.mode === "complete") {
    mapExitsPanel.classList.add("hidden");
    return;
  }
  mapExitsPanel.classList.remove("hidden");
  const tile = currentTile(session);
  if (!tile) {
    mapExitsPanel.appendChild(node("div", "map-overlay-empty", "No current room."));
    return;
  }

  const details = document.createElement("details");
  details.className = "map-overlay-details map-exits-details";
  details.open = Boolean(state.mapExitsOpen);
  const mode = effectiveSessionMode(session);
  const summary = document.createElement("summary");
  summary.textContent = mapExitsSummary(session);
  summary.title =
    mode === "combat"
      ? "Withdraw through a door or use the dungeon exit when allowed."
      : "Travel, open doors, and leave the dungeon from here.";
  details.appendChild(summary);

  const shell = node("div", "map-exits-body");
  const scroll = node("div", "map-exits-scroll");
  scroll.setAttribute("aria-label", "Room exits");
  const list = buildExitListElement(session);
  if (list) {
    scroll.appendChild(list);
  } else {
    const rawCount = (tile.exits || []).length;
    scroll.appendChild(
      node(
        "div",
        "map-overlay-empty",
        rawCount
          ? "No exits are reachable from where you stand. Hidden, blocked, or invalid passages are omitted."
          : "No exits on this map element."
      )
    );
  }
  shell.appendChild(scroll);
  shell.appendChild(node("div", "map-exits-scroll-hint hidden", "Scroll for more exits ↓"));
  const exitCount = list ? list.querySelectorAll(".exit-row").length : 0;
  const exitWeight = tile ? sumExitRowWeights(session, tile) : exitCount;
  for (const host of [shell, mapExitsPanel, mapLogRow].filter(Boolean)) {
    host.style.setProperty("--exit-row-count", String(exitCount));
    host.style.setProperty("--exit-row-weight", String(exitWeight));
  }
  if (mapLogRow) {
    mapLogRow.classList.toggle("log-row-exits-heavy", exitWeight >= 4 && details.open);
  }
  details.appendChild(shell);
  details.addEventListener("toggle", () => {
    state.mapExitsOpen = details.open;
    saveLayoutPrefs();
    if (details.open) requestAnimationFrame(() => bindMapExitsScrollHint(shell));
  });
  mapExitsPanel.appendChild(details);
  if (details.open) requestAnimationFrame(() => bindMapExitsScrollHint(shell));
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

function collectDoorActionOptions(session, exit) {
  const options = [];
  const members = livingParty(session);
  const doorType = exit.door_type || null;
  const clues = session.clues_found || 0;

  const pushCharacterAction = (member, label, action, extra = {}, shortLabel = null) => {
    options.push({
      label,
      shortLabel: shortLabel || member.name,
      characterId: member.character_id,
      action,
      extra,
      disabled: false,
    });
  };

  const pushPartyAction = (label, action, extra = {}, disabled = false, shortLabel = null) => {
    options.push({
      label,
      shortLabel: shortLabel || label,
      characterId: null,
      action,
      extra,
      disabled,
    });
  };

  if (!members.length) return options;

  if (!doorType) {
    for (const member of members) {
      const actionLabel =
        member.class_id === "warrior" || member.class_id === "barbarian"
          ? `${member.name}: roll door (bash if locked)`
          : `${member.name}: open door (2d6)`;
      pushCharacterAction(member, actionLabel, "open_door");
    }
    return options;
  }

  if (doorType === "sealed") {
    if (!exit.door_sealed_attempted) {
      for (const member of members.filter(isSpellcaster)) {
        pushCharacterAction(member, `${member.name}: spellcast sealed door`, "spellcast_door");
      }
    }
    return options;
  }

  if (doorType === "illusion") {
    pushPartyAction(`Spend 3 Clues (${clues} held)`, "spend_clues_on_door", {}, clues < 3, "Clues (need 3)");
    for (const member of members.filter((m) => m.class_id === "illusionist")) {
      if ((exit.door_illusion_attempted_ids || []).includes(member.character_id)) continue;
      pushCharacterAction(member, `${member.name}: dispel illusion`, "spellcast_door");
    }
    return options;
  }

  if (doorType === "lever") {
    pushPartyAction(`Spend 1 Clue (${clues} held)`, "spend_clues_on_door", {}, clues < 1, `Clues (${clues} held)`);
    return options;
  }

  if (doorType === "iron") {
    const hasRogue = members.some((m) => m.class_id === "rogue");
    for (const member of members.filter((m) => m.class_id === "rogue")) {
      pushCharacterAction(member, `${member.name}: lock-pick iron door`, "open_door");
    }
    for (const member of members) {
      for (const spell of ["Fireball", "Lightning"]) {
        if (!(member.spells || []).some((s) => normalizeSpellKey(s) === normalizeSpellKey(spell))) continue;
        if (spellExpended(session, member, spell)) continue;
        pushCharacterAction(
          member,
          `${member.name}: ${spell} (destroy door)`,
          "cast_spell",
          { spell_name: spell, highlight: !hasRogue },
          `${spell}`
        );
      }
    }
    return options;
  }

  if (doorType === "locked" || doorType === "trap_door" || doorType === "unlocked") {
    for (const member of members) {
      if (doorType === "locked") {
        if (member.class_id === "rogue") {
          pushCharacterAction(member, `${member.name}: lock-pick`, "open_door");
        } else if (member.class_id === "warrior" || member.class_id === "barbarian") {
          pushCharacterAction(member, `${member.name}: bash door`, "open_door");
        }
      } else {
        pushCharacterAction(member, `${member.name}: open door`, "open_door");
      }
      if (hasExpertSkill(member, "acute_hearing") && !exit.door_listened) {
        pushCharacterAction(member, `${member.name}: listen (Acute Hearing)`, "listen_at_door");
      }
    }
  }

  if (["locked", "lever", "unlocked", "trap_door"].includes(doorType)) {
    for (const member of members.filter((m) => m.class_id === "druid")) {
      if (spellExpended(session, member, "Warp Wood")) continue;
      if (!(member.spells || []).some((s) => normalizeSpellKey(s) === "warp_wood")) continue;
      pushCharacterAction(member, `${member.name}: Warp Wood`, "cast_spell", { spell_name: "Warp Wood" });
    }
  }

  return options;
}

function runDoorActionOption(option, exit) {
  if (option.disabled) return;
  if (option.action === "open_door") {
    advance("open_door", { exit_id: exit.id, character_id: option.characterId });
    return;
  }
  if (option.action === "listen_at_door") {
    advance("listen_at_door", { exit_id: exit.id, character_id: option.characterId });
    return;
  }
  if (option.action === "spellcast_door") {
    advance("spellcast_door", { exit_id: exit.id, character_id: option.characterId });
    return;
  }
  if (option.action === "spend_clues_on_door") {
    advance("spend_clues_on_door", { exit_id: exit.id });
    return;
  }
  if (option.action === "cast_spell") {
    advance("cast_spell", {
      exit_id: exit.id,
      character_id: option.characterId,
      spell_name: option.extra.spell_name,
    });
  }
}

function doorActionCategory(option) {
  if (option.action === "spend_clues_on_door") return "clues";
  if (option.action === "spellcast_door") return "spellcast";
  if (option.extra?.spell_name) {
    const spell = option.extra.spell_name;
    if (normalizeSpellKey(spell) === "warp_wood") return "warp_wood";
    return `spell:${spell}`;
  }
  const label = option.label.toLowerCase();
  if (label.includes("lock-pick") || label.includes("lockpick")) return "lockpick";
  if (label.includes("bash")) return "bash";
  if (label.includes("roll door")) return "bash";
  if (label.includes("open door")) return "open";
  return "action";
}

const DOOR_ACTION_LABELS = {
  clues: "Spend clues",
  spellcast: "Spellcast",
  lockpick: "Lock-pick",
  bash: "Bash",
  open: "Open",
  warp_wood: "Warp Wood",
  action: "Try",
};

function doorActionButtonLabel(category) {
  if (category.startsWith("spell:")) return category.slice(6);
  return DOOR_ACTION_LABELS[category] || DOOR_ACTION_LABELS.action;
}

function groupDoorActionOptions(options) {
  const groups = new Map();
  for (const option of options) {
    const category = doorActionCategory(option);
    if (!groups.has(category)) groups.set(category, []);
    groups.get(category).push(option);
  }
  const entries = [...groups.entries()];
  entries.sort((left, right) => {
    const leftSpell = left[0].startsWith("spell:") ? 0 : 1;
    const rightSpell = right[0].startsWith("spell:") ? 0 : 1;
    if (leftSpell !== rightSpell) return leftSpell - rightSpell;
    return left[0].localeCompare(right[0]);
  });
  return new Map(entries);
}

function doorActionSelectLabel(option) {
  return option.shortLabel || option.label;
}

let mapContextMenuEl = null;
let mapContextMenuCleanup = null;

function dismissMapContextMenu() {
  if (mapContextMenuCleanup) {
    mapContextMenuCleanup();
    mapContextMenuCleanup = null;
  }
  if (mapContextMenuEl) {
    mapContextMenuEl.remove();
    mapContextMenuEl = null;
  }
}

function positionMapContextMenu(menu, anchorEl) {
  const anchor = anchorEl.getBoundingClientRect();
  menu.style.position = "fixed";
  menu.style.left = `${Math.round(anchor.left + anchor.width / 2)}px`;
  menu.style.top = `${Math.round(anchor.bottom + 6)}px`;
  menu.style.transform = "translateX(-50%)";
  requestAnimationFrame(() => {
    const menuRect = menu.getBoundingClientRect();
    let left = anchor.left + anchor.width / 2 - menuRect.width / 2;
    left = Math.max(8, Math.min(left, window.innerWidth - menuRect.width - 8));
    let top = anchor.bottom + 6;
    if (top + menuRect.height > window.innerHeight - 8) {
      top = Math.max(8, anchor.top - menuRect.height - 6);
    }
    menu.style.left = `${Math.round(left)}px`;
    menu.style.top = `${Math.round(top)}px`;
    menu.style.transform = "none";
  });
}

function prepareSpellCastAtFoe(session, member, spell, foe, livingFoes) {
  state.spellFoeTargets = state.spellFoeTargets || {};
  state.spellAimModes = state.spellAimModes || {};
  state.spellFoeTargets[member.character_id] = foe.id;
  state.combatTargets[member.character_id] = foe.id;
  const key = normalizeSpellKey(spell);
  if (key === "fireball") {
    if (fireballNeedsAimChoice(livingFoes)) {
      state.spellAimModes[member.character_id] = foeIsMassKillMinor(foe) ? "minions" : "single";
    } else if (livingFoeMinors(livingFoes).length) {
      state.spellAimModes[member.character_id] = "minions";
    } else {
      state.spellAimModes[member.character_id] = "single";
    }
  }
  return spellCastPayload(member.character_id, spell);
}

function spellCanTargetFoe(session, member, spell, foe, livingFoes) {
  if (!foe || foe.life <= 0) return false;
  const key = normalizeSpellKey(spell);
  if (EXPLORATION_SPELL_KEYS.has(key) || spellNeedsAllyTarget(spell)) return false;
  if (key === "mass_teleport" || key === "healing_surge") return false;
  if (key === "fireball") {
    if (fireballNeedsAimChoice(livingFoes)) {
      const aim = fireballAimModeFor(session, member, livingFoes);
      if (aim === "minions") return foeIsMassKillMinor(foe);
      if (aim === "single") return !foeIsMassKillMinor(foe);
      return true;
    }
    return livingFoes.some((entry) => entry.id === foe.id);
  }
  return livingFoes.some((entry) => entry.id === foe.id);
}

function buildCombatFoeCard(session, tile, foe, foeLabels, { interactive = false } = {}) {
  const card = node(
    "div",
    `${foe.life > 0 ? "combat-foe-card" : "combat-foe-card dead"}${interactive ? " clickable" : ""}`
  );
  if (interactive) {
    card.setAttribute("role", "button");
    card.tabIndex = 0;
    card.title = `${foeLabels.get(foe.id) || foe.name} — click to assign hero targets`;
    const openMenu = (event) => {
      event.preventDefault();
      event.stopPropagation();
      openCombatFoeMenu(session, tile, foe, card, foeLabels);
    };
    card.addEventListener("click", openMenu);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") openMenu(event);
    });
  }
  const header = node("div", "combat-foe-header");
  header.appendChild(node("span", "combat-foe-name", foeLabels.get(foe.id) || foe.name));
  header.appendChild(node("span", "combat-foe-stats", `Life ${foe.life}/${foe.max_life} · ${foeLevelLabel(foe)}`));
  card.appendChild(header);
  const foeChips = foeStatusLabels(foe).map((label) => ({ label, kind: "neutral" }));
  appendStatusChips(card, foeChips);
  if (foe.tags?.length) {
    card.appendChild(node("div", "combat-foe-tags", foe.tags.join(", ")));
  }
  return card;
}

function collectFoeMenuItems(session, tile, foe, foeLabels) {
  const items = [];
  const label = foeLabels.get(foe.id) || foe.name;
  items.push({
    label: `${label} · Life ${foe.life}/${foe.max_life} · ${foeLevelLabel(foe)}`,
    disabled: true,
  });
  if (encounterPending(session)) {
    items.push({
      label: "Start Combat",
      title: ACTION_TOOLTIPS.startCombat,
      onClick: () => advance("start_combat"),
    });
    return items;
  }
  if (foe.life <= 0 || session.mode !== "combat") return items;

  const livingFoes = (tile?.enemies || []).filter((entry) => entry.life > 0);
  const spellItems = [];
  for (const member of livingParty(session)) {
    for (const spell of heroCombatSpells(session, member)) {
      if (!spellCanTargetFoe(session, member, spell, foe, livingFoes)) continue;
      const reactionsPending = reactionsOpen(session);
      const skipsReactions = reactionsPending && spellCommitsToAttack(spell);
      const castNow = spellCommitsToAttack(spell) ? " (casts now)" : "";
      spellItems.push({
        label: `${member.name}: ${spell}${castNow}`,
        disabled: surpriseReactionLocked(session),
        title: surpriseReactionLocked(session)
          ? immediateActionTooltip(session, spellTooltip(spell, session, member))
          : skipsReactions
            ? `${spellTooltip(spell, session, member)} Casts immediately — not via Fight Round. Casting now skips the Reaction roll.`
            : `${spellTooltip(spell, session, member)} Casts immediately — not via Fight Round.`,
        onClick: () =>
          advance(
            "cast_spell",
            prepareSpellCastAtFoe(session, member, spell, foe, livingFoes)
          ),
      });
    }
  }
  appendMenuSection(items, "Spells", spellItems);

  const targetItems = [];
  const livingHeroes = (session.party || [])
    .filter((member) => member.current_life > 0)
    .sort((left, right) => left.marching_order - right.marching_order);
  for (const member of livingHeroes) {
    const selected = state.combatTargets[member.character_id] === foe.id;
    targetItems.push({
      label: `${selected ? "✓ " : ""}#${member.marching_order} ${member.name}`,
      onClick: () => {
        state.combatTargets[member.character_id] = foe.id;
        renderSession();
      },
    });
  }
  appendMenuSection(items, "Melee targets", targetItems);
  return items;
}

function openCombatFoeMenu(session, tile, foe, anchorEl, foeLabels) {
  openMapContextMenu(anchorEl, {
    title: foeLabels.get(foe.id) || foe.name,
    status: foe.life > 0 ? "Assign hero targets" : "Defeated",
    items: collectFoeMenuItems(session, tile, foe, foeLabels),
    ariaLabel: "Foe actions",
  });
}

function collectHeroCombatMenuItems(session, tile, member, livingFoes) {
  const items = [];
  items.push({
    label: `#${member.marching_order} ${member.name} · HP ${member.current_life}/${member.max_life}`,
    disabled: true,
  });
  if (session.mode !== "combat" || member.current_life <= 0) return items;

  const targetItems = [];
  if (livingFoes.length) {
    for (const foe of livingFoes) {
      const selected = state.combatTargets[member.character_id] === foe.id;
      targetItems.push({
        label: `${selected ? "✓ " : ""}${foeDisplayName(livingFoes, foe)} (${foeLevelLabel(foe)})`,
        onClick: () => {
          state.combatTargets[member.character_id] = foe.id;
          renderSession();
        },
      });
    }
  }
  appendMenuSection(items, "Melee targets", targetItems);

  const potionItems = [];
  const immediateLocked = surpriseReactionLocked(session);
  for (const potionName of heroUsablePotions(session, member)) {
    const sleepPotion = potionName.toLowerCase().includes("sleep");
    potionItems.push({
      label: potionName,
      disabled: sleepPotion && immediateLocked,
      title: potionName.toLowerCase().includes("healing")
        ? ACTION_TOOLTIPS.usePotion
        : sleepPotion
          ? immediateActionTooltip(session, `Use ${potionName} against foes (consumes the potion).`)
          : `Use ${potionName} from inventory (consumes the potion).`,
      onClick: () => advance("use_potion", { character_id: member.character_id, item_name: potionName }),
    });
  }
  appendMenuSection(items, "Potions", potionItems);

  const abilityItems = [];
  for (const [value, label] of buildCombatAbilityChoices(session, member)) {
    abilityItems.push({
      label,
      onClick: () => {
        state.combatAbilities[member.character_id] = value;
        renderSession();
      },
    });
  }
  appendMenuSection(items, "Abilities", abilityItems);

  const spellItems = [];
  const targetId = state.combatTargets[member.character_id] || livingFoes[0]?.id;
  const target = livingFoes.find((foe) => foe.id === targetId) || livingFoes[0];
  for (const spell of heroCombatSpells(session, member)) {
    if (!target || !spellCanTargetFoe(session, member, spell, target, livingFoes)) continue;
    const reactionsPending = reactionsOpen(session);
    const skipsReactions = reactionsPending && spellCommitsToAttack(spell);
    spellItems.push({
      label: `${spell} → ${foeDisplayName(livingFoes, target)}`,
      disabled: surpriseReactionLocked(session),
      title: surpriseReactionLocked(session)
        ? immediateActionTooltip(session, spellTooltip(spell, session, member))
        : skipsReactions
          ? `${spellTooltip(spell, session, member)} Casting now skips the Reaction roll.`
          : spellTooltip(spell, session, member),
      onClick: () =>
        advance(
          "cast_spell",
          prepareSpellCastAtFoe(session, member, spell, target, livingFoes)
        ),
    });
  }
  appendMenuSection(items, "Spells", spellItems);

  if (!items.some((item) => !item.disabled && !item.heading && item.onClick)) {
    items.push({ label: "No quick actions", disabled: true });
  }
  return items;
}

function openCombatHeroMenu(session, tile, member, anchorEl, livingFoes) {
  openMapContextMenu(anchorEl, {
    title: `#${member.marching_order} ${member.name}`,
    status: heroCombatPlanLabel(session, member, tile),
    items: collectHeroCombatMenuItems(session, tile, member, livingFoes),
    ariaLabel: "Hero combat actions",
  });
}

function collectMonsterMenuItems(session, tile) {
  const items = [];
  const living = livingFoesOnTile(session);
  const status = living.map((foe) => `${foe.name} (${foeLevelLabel(foe)})`).join(", ");

  if (encounterPending(session)) {
    items.push({
      label: "Start Combat",
      title: ACTION_TOOLTIPS.startCombat,
      onClick: () => advance("start_combat"),
    });
    const exits = playerFacingExits(session, tile).filter((exit) => exit.status !== "blocked");
    if (exits.length) {
      const sideLabels = exitSideLabelsForExits(exits);
      for (const exit of exits) {
        items.push({
          label: `Leave via ${exitDisplayLabel(exit, sideLabels.get(exit.id))}`,
          onClick: () => runTravelExit(session, exit),
        });
      }
    } else {
      items.push({ label: "No exits to leave through", disabled: true });
    }
    return { status, items };
  }

  if (session.mode === "combat") {
    const immediateLocked = surpriseReactionLocked(session);
    if (reactionsOpen(session)) {
      items.push({
        label: "Check Reactions",
        title: ACTION_TOOLTIPS.checkReaction,
        onClick: () => advance("check_reaction"),
      });
    }
    items.push({
      label: combatRoundButtonLabel(session),
      disabled: immediateLocked,
      title: immediateActionTooltip(session, ACTION_TOOLTIPS.combatRound),
      onClick: () => resolveCombatRound(),
    });
    items.push({
      label: "Flee",
      disabled: immediateLocked,
      title: immediateLocked ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee) : ACTION_TOOLTIPS.flee,
      onClick: () => advance("flee"),
    });
    const luckHalfling = halflingForLuckFlee(session);
    if (luckHalfling) {
      items.push({
        label: `Flee (${luckHalfling.name}'s Luck)`,
        disabled: immediateLocked,
        title: immediateLocked
          ? immediateActionTooltip(session, ACTION_TOOLTIPS.flee)
          : `${luckHalfling.name} spends 1 Luck so the party flees without parting blows.`,
        onClick: () =>
          advance("flee", { use_luck_flee: true, character_id: luckHalfling.character_id }),
      });
    }
  }

  if (!items.length) {
    items.push({ label: "No actions", disabled: true });
  }
  return { status, items };
}

function openMapMonsterMenu(session, tile, anchorEl) {
  const { status, items } = collectMonsterMenuItems(session, tile);
  openMapContextMenu(anchorEl, {
    title: "Foes",
    status,
    items,
    ariaLabel: "Encounter actions",
  });
}

function openMapContextMenu(anchorEl, { title, status = "", items = [], ariaLabel = "Actions" }) {
  dismissMapContextMenu();
  const menu = node("div", "map-context-menu");
  menu.setAttribute("role", "menu");
  menu.setAttribute("aria-label", ariaLabel);

  const head = node("div", "map-context-menu-head");
  head.appendChild(node("strong", "", title));
  if (status) head.appendChild(node("span", "map-context-menu-status muted", status));
  menu.appendChild(head);

  const body = node("div", "map-context-menu-body");
  if (!items.length) {
    body.appendChild(node("div", "map-context-menu-empty muted", "No actions available."));
  } else {
    for (const item of items) {
      if (item.heading) {
        body.appendChild(node("div", "map-context-menu-heading", item.label));
        continue;
      }
      const button = document.createElement("button");
      button.type = "button";
      button.className = "map-context-menu-item secondary";
      button.setAttribute("role", "menuitem");
      button.textContent = item.label;
      button.disabled = Boolean(item.disabled);
      if (!item.disabled && typeof item.onClick === "function") {
        button.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          dismissMapContextMenu();
          item.onClick();
        });
      }
      body.appendChild(button);
      if (item.title) setButtonTooltip(button, item.title);
    }
  }
  menu.appendChild(body);
  document.body.appendChild(menu);
  positionMapContextMenu(menu, anchorEl);
  mapContextMenuEl = menu;

  const onDocumentClick = (event) => {
    if (menu.contains(event.target) || anchorEl.contains(event.target)) return;
    dismissMapContextMenu();
  };
  const onKeyDown = (event) => {
    if (event.key === "Escape") dismissMapContextMenu();
  };
  window.setTimeout(() => {
    document.addEventListener("click", onDocumentClick, true);
    document.addEventListener("keydown", onKeyDown);
  }, 0);
  mapContextMenuCleanup = () => {
    document.removeEventListener("click", onDocumentClick, true);
    document.removeEventListener("keydown", onKeyDown);
  };
}

function runTravelExit(session, exit) {
  const pendingXp = session.xp_rolls_pending || 0;
  const completing = exit.dungeon_exit && !fallenInDungeon(session).length && session.final_boss_defeated;
  if (
    completing &&
    pendingXp > 0 &&
    (session.xp_system || "classical") === "classical" &&
    !window.confirm(
      `${pendingXp} banked XP roll${pendingXp === 1 ? "" : "s"} remain. Completing the adventure ends the session — spend them on party sheets first. Leave anyway?`
    )
  ) {
    return;
  }
  advance("explore", { exit_id: exit.id, direction: exit.direction });
}

function collectTravelExitMenuItems(session, exit, sideLabel) {
  return [
    {
      label: exitButtonLabel(exit, sideLabel, session),
      title: exitTooltip(exit, session, sideLabel),
      onClick: () => runTravelExit(session, exit),
    },
  ];
}

function collectExitMenuItems(session, tile, exit, sideLabel) {
  const items = [];
  const mode = effectiveSessionMode(session);

  if (exit.status === "blocked") {
    return [{ label: "Blocked dead end", disabled: true, title: "This passage was truncated and cannot be used." }];
  }

  if (mode === "combat") {
    if (exit.kind === "door" && exit.destination_tile_id) {
      items.push({
        label: "Withdraw through door",
        title: ACTION_TOOLTIPS.withdraw,
        onClick: () => advance("withdraw", { exit_id: exit.id }),
      });
    }
    if (exit.dungeon_exit) {
      items.push(...collectTravelExitMenuItems(session, exit, sideLabel));
    }
    if (!items.length) {
      items.push({ label: "Resolve combat first", disabled: true });
    }
    return items;
  }

  if (exit.kind === "door" && !exit.door_open) {
    const doorOptions = collectDoorActionOptions(session, exit);
    if (!doorOptions.length) {
      items.push({ label: "No living heroes can work this door", disabled: true });
      return items;
    }
    for (const option of doorOptions) {
      items.push({
        label: option.label,
        title: option.label,
        disabled: option.disabled,
        onClick: () => runDoorActionOption(option, exit),
      });
    }
    return items;
  }

  return collectTravelExitMenuItems(session, exit, sideLabel);
}

function collectTreasureMenuItems(session, tile) {
  const items = [];
  const hasTrap = tileHasActiveTrap(tile);
  const hasTreasure = tileHasClaimableTreasure(tile);
  const status = tile.treasure_summary || (hasTreasure ? "Treasure available" : "No treasure");

  if (hasTrap) {
    items.push({
      label: "Resolve the trap before claiming treasure",
      disabled: true,
      title: ACTION_TOOLTIPS.resolveTrap,
    });
  } else if (hasTreasure) {
    items.push({
      label: "Claim treasure",
      title: ACTION_TOOLTIPS.claimTreasure,
      onClick: () => advance("claim_treasure"),
    });
  } else if (tile.treasure_claimed) {
    items.push({ label: "Treasure already claimed", disabled: true });
  } else {
    items.push({ label: status, disabled: true });
  }

  for (const member of livingParty(session)) {
    if (
      member.class_id === "halfling" &&
      luckPointsRemaining(session, member) > 0 &&
      session.pending_treasure_reroll_tile_id === tile.id
    ) {
      items.push({
        label: `${member.name}: Luck reroll treasure`,
        onClick: () =>
          advance("use_class_ability", {
            character_id: member.character_id,
            class_ability: "halfling_luck_treasure",
          }),
      });
    }
  }
  return { status, items };
}

function collectTrapMenuItems(session, tile) {
  const items = [];
  if (!tileHasActiveTrap(tile)) {
    return { status: "Resolved or none", items: [{ label: "No active trap here", disabled: true }] };
  }
  const status = `${tile.trap_key || "Trap"} · L${tile.trap_level || "?"}`;

  items.push({
    label: "Disarm trap (Rogue → Gnome → trap table)",
    title: ACTION_TOOLTIPS.resolveTrap,
    onClick: () => advance("resolve_trap"),
  });

  for (const member of livingParty(session)) {
    if (member.class_id === "gnome" && gnomeGadgetsRemaining(session, member) > 0) {
      items.push({
        label: `${member.name}: Gadget disarm trap`,
        title: "Spend 1 gadget point for +Level on the disarm roll.",
        onClick: () =>
          advance("use_class_ability", {
            character_id: member.character_id,
            class_ability: "gnome_gadget_trap",
            gadget_points: 1,
          }),
      });
    }
  }
  return { status, items };
}

function openMapExitMenu(session, tile, exit, anchorEl, sideLabel) {
  openMapContextMenu(anchorEl, {
    title: exitDisplayLabel(exit, sideLabel),
    status: exitStatusLabel(exit),
    items: collectExitMenuItems(session, tile, exit, sideLabel),
    ariaLabel: `${exitDisplayLabel(exit, sideLabel)} actions`,
  });
}

function openMapTreasureMenu(session, tile, anchorEl) {
  const { status, items } = collectTreasureMenuItems(session, tile);
  openMapContextMenu(anchorEl, {
    title: "Treasure",
    status,
    items,
    ariaLabel: "Treasure actions",
  });
}

function openMapTrapMenu(session, tile, anchorEl) {
  const { status, items } = collectTrapMenuItems(session, tile);
  openMapContextMenu(anchorEl, {
    title: "Trap",
    status,
    items,
    ariaLabel: "Trap actions",
  });
}

function appendOpenDoorShortcuts(session, exit, actions, { dock = false } = {}) {
  const doorOptions = collectDoorActionOptions(session, exit);
  if (!doorOptions.length) return false;

  const groups = groupDoorActionOptions(doorOptions);
  const wrap = node("div", "door-shortcut-list");
  for (const [category, options] of groups) {
    const row = node("div", "door-shortcut-row");
    const label = doorActionButtonLabel(category);
    const enabled = options.filter((option) => !option.disabled);

    if (!enabled.length) {
      const note = node("div", "exit-row-note muted", options[0]?.label || "No action available.");
      row.appendChild(note);
      wrap.appendChild(row);
      continue;
    }

    if (enabled.length === 1) {
      const option = enabled[0];
      const buttonLabel =
        dock && option.characterId ? `${option.shortLabel} · ${label}` : dock ? doorActionSelectLabel(option) : label;
      const spellClass =
        category.startsWith("spell:") && option.extra?.highlight ? " door-destroy-spell" : "";
      const button = node("button", `secondary${spellClass}`, buttonLabel);
      button.type = "button";
      setButtonTooltip(button, option.label);
      button.addEventListener("click", () => runDoorActionOption(option, exit));
      row.appendChild(button);
      if (option.characterId && !dock) {
        row.appendChild(node("div", "door-shortcut-note muted", option.label));
      }
    } else {
      const select = document.createElement("select");
      select.className = dock ? "door-shortcut-select" : "door-shortcut-select";
      for (const [index, option] of enabled.entries()) {
        const opt = document.createElement("option");
        opt.value = String(index);
        opt.textContent = doorActionSelectLabel(option);
        opt.title = option.label;
        select.appendChild(opt);
      }
      const button = node("button", "secondary", label);
      button.type = "button";
      setButtonTooltip(button, ACTION_TOOLTIPS.openDoor);
      button.addEventListener("click", () => {
        const option = enabled[Number(select.value)];
        if (option) runDoorActionOption(option, exit);
      });
      if (dock) {
        row.classList.add("door-shortcut-row-stacked");
      }
      row.appendChild(select);
      row.appendChild(button);
    }
    wrap.appendChild(row);
  }
  actions.appendChild(wrap);
  return true;
}

function appendOpenDoorActions(session, exit, sideLabel, actions, { inline = false, dock = false } = {}) {
  const label = exitDisplayLabel(exit, sideLabel);
  const host = inline ? actions : node("div", "exit-door-card item");
  if (!inline) {
    host.appendChild(node("strong", "", label));
    const doorType = exit.door_type || null;
    host.appendChild(subline(exit.door_result || (doorType ? titleCase(doorType) : "Closed — type not yet rolled (2d6)")));
    host.appendChild(subline(doorType ? doorTypeHint(exit, session) : "Choose an action; the door table roll happens on first try."));
  }

  const doorOptions = collectDoorActionOptions(session, exit);
  if (!doorOptions.length) {
    let emptyNote = "No living heroes can work this door.";
    const doorType = exit.door_type || null;
    if (doorType === "iron") emptyNote = "Iron doors need a Rogue lock-pick or Fireball/Lightning.";
    if (doorType === "sealed" && exit.door_sealed_attempted) emptyNote = "Sealed door already resisted spellcasting.";
    if (doorType === "sealed" && !exit.door_sealed_attempted) {
      emptyNote = livingParty(session).some(isSpellcaster)
        ? "No spellcaster available."
        : "A spellcaster must open a magically sealed door.";
    }
    host.appendChild(subline(emptyNote));
    if (!inline) actions.appendChild(host);
    return;
  }

  if (appendOpenDoorShortcuts(session, exit, inline ? actions : host, { dock })) {
    if (!inline) actions.appendChild(host);
    return;
  }

  const row = node("div", `exit-door-controls${dock ? " exit-door-controls-dock" : ""}`);
  const select = document.createElement("select");
  select.className = "door-action-select";
  select.appendChild(new Option("Choose hero & action…", "", true, true));
  for (const [index, option] of doorOptions.entries()) {
    const opt = new Option(dock ? doorActionSelectLabel(option) : option.label, String(index), false, option.disabled);
    opt.disabled = option.disabled;
    opt.title = option.label;
    select.appendChild(opt);
  }
  const go = node("button", "secondary", inline ? "Open" : "Go");
  go.type = "button";
  go.disabled = true;
  setButtonTooltip(go, ACTION_TOOLTIPS.openDoor);
  select.addEventListener("change", () => {
    go.disabled = !select.value;
  });
  go.addEventListener("click", () => {
    const option = doorOptions[Number(select.value)];
    if (!option) return;
    runDoorActionOption(option, exit);
  });
  row.appendChild(select);
  row.appendChild(go);
  host.appendChild(row);
  if (!inline) actions.appendChild(host);
}

function appendTravelExitButton(actions, session, exit, sideLabel, { compact = false } = {}) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `exit-button ${exit.kind}${exit.dungeon_exit ? " dungeon-exit" : ""}`;
  button.textContent = compact ? "Go through" : exitButtonLabel(exit, sideLabel, session);
  setButtonTooltip(button, exitTooltip(exit, session, sideLabel));
  button.addEventListener("click", () => runTravelExit(session, exit));
  actions.appendChild(button);
}

function exitStatusLabel(exit) {
  if (exit.status === "blocked") return "dead end";
  if (exit.dungeon_exit) return "dungeon exit";
  if (exit.kind === "door") {
    const type = exit.door_type ? titleCase(exit.door_type) : "door";
    if (!exit.door_open && exit.door_type === "iron") return `${type} · closed · no bash`;
    return exit.door_open ? `${type} · open` : `${type} · closed`;
  }
  return exit.status || "open";
}

function appendExitRowActions(session, tile, exit, sideLabel, rowActions, mode, { dock = false } = {}) {
  if (exit.status === "blocked") {
    rowActions.appendChild(node("span", "exit-row-note muted", "Blocked dead end"));
    return;
  }

  if (mode === "combat") {
    if (exit.kind === "door" && exit.destination_tile_id) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "exit-button door withdraw-door secondary";
      button.textContent = "Withdraw";
      setButtonTooltip(button, ACTION_TOOLTIPS.withdraw);
      button.addEventListener("click", () => advance("withdraw", { exit_id: exit.id }));
      rowActions.appendChild(button);
    } else if (exit.dungeon_exit) {
      appendTravelExitButton(rowActions, session, exit, sideLabel);
    } else {
      rowActions.appendChild(node("span", "exit-row-note muted", "Resolve combat first"));
    }
    return;
  }

  if (exit.kind === "door" && !exit.door_open) {
    if (exit.door_type === "iron") {
      const hasRogue = livingParty(session).some((m) => m.class_id === "rogue");
      const ironNote = hasRogue
        ? "Iron — Rogue pick, Fireball, or Lightning only."
        : "Iron — no Rogue: Fireball or Lightning (highlighted).";
      rowActions.appendChild(
        node("div", "exit-row-note muted", dock ? ironNote : hasRogue
          ? "Iron doors cannot be bashed — Rogue lock-pick, Fireball, or Lightning only."
          : "Iron door — no Rogue: Fireball or Lightning only (highlighted below).")
      );
    } else if (!exit.door_type) {
      rowActions.appendChild(
        node(
          "div",
          "exit-row-note muted",
          dock
            ? "First try rolls 2d6 door type; bash if locked."
            : "First attempt rolls 2d6 for door type; Warrior/Barbarian can bash if locked."
        )
      );
    }
    appendOpenDoorActions(session, exit, sideLabel, rowActions, { inline: true, dock });
    return;
  }

  appendTravelExitButton(rowActions, session, exit, sideLabel, { compact: true });
}

function renderExitActions(session) {
  exitActions.replaceChildren();
  exitActions.classList.toggle("hidden", session.mode !== "complete");

  if (session.mode !== "complete") {
    return;
  }

  const heading = node("h2", "exit-actions-title", "Adventure Complete");
  exitActions.appendChild(heading);
  const summary = node("div", "list compact");
  for (const line of session.summary || ["Adventure complete."]) {
    summary.appendChild(node("div", "item", line));
  }
  exitActions.appendChild(summary);
  exitActions.appendChild(
    subline("Home roster sheets now show gold, loot, levels, and healed Life from this run.")
  );
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
  payloadKind: null,
  toCharacterId: null,
};

function resetTransferDialogState() {
  transferDialogState.context = null;
  transferDialogState.members = [];
  transferDialogState.payloadKind = null;
  transferDialogState.toCharacterId = null;
}

function resetTransferDialogForm() {
  if (transferGoldRadio) transferGoldRadio.checked = false;
  if (transferGoldAmount) {
    transferGoldAmount.value = "1";
    transferGoldAmount.disabled = true;
  }
  if (transferItemOptions) transferItemOptions.replaceChildren();
  if (transferToSelect) transferToSelect.replaceChildren();
  if (transferConfirmBtn) transferConfirmBtn.disabled = true;
}

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

function transferSessionContext() {
  return transferDialogState.context?.mode === "session" ? state.session : null;
}

function maxTransferGoldAmount(fromMember, toMember) {
  if (!fromMember) return 0;
  if (isRosterTransferContext()) return fromMember.gold;
  if (!toMember) return fromMember.gold;
  const session = transferDialogState.context?.mode === "session" ? state.session : null;
  return Math.min(fromMember.gold, goldCarryCapacity(toMember, session));
}

function selectDefaultTransferPayload(fromMember, toMember) {
  if (!fromMember || !transferDialogForm) return;

  if (transferDialogState.payloadKind === "gold" && fromMember.gold > 0 && transferGoldRadio) {
    for (const input of transferDialogForm.querySelectorAll('input[name="transfer-payload"]')) {
      input.checked = false;
    }
    transferGoldRadio.checked = true;
    if (transferGoldAmount) {
      const maxGold = maxTransferGoldAmount(fromMember, toMember);
      transferGoldAmount.value = maxGold > 0 ? "1" : "0";
    }
    return;
  }

  if (transferDialogState.payloadKind?.startsWith("item:")) {
    const saved = transferItemOptions?.querySelector(
      `input[name="transfer-payload"][value="${transferDialogState.payloadKind}"]:not([disabled])`
    );
    if (saved) {
      for (const input of transferDialogForm.querySelectorAll('input[name="transfer-payload"]')) {
        input.checked = false;
      }
      saved.checked = true;
      return;
    }
  }

  for (const input of transferDialogForm.querySelectorAll('input[name="transfer-payload"]')) {
    input.checked = false;
  }

  const firstItem = transferItemOptions?.querySelector('input[name="transfer-payload"]:not([disabled])');
  if (firstItem) {
    firstItem.checked = true;
    transferDialogState.payloadKind = firstItem.value;
    return;
  }

  if (fromMember.gold > 0 && transferGoldRadio && !transferGoldRadio.disabled) {
    transferGoldRadio.checked = true;
    transferDialogState.payloadKind = "gold";
    if (transferGoldAmount) {
      const maxGold = maxTransferGoldAmount(fromMember, toMember);
      transferGoldAmount.value = maxGold > 0 ? "1" : "0";
    }
  }
}

function rememberTransferPayloadSelection() {
  const checked = transferDialogForm?.querySelector('input[name="transfer-payload"]:checked');
  if (transferGoldRadio?.checked) {
    transferDialogState.payloadKind = "gold";
    return;
  }
  if (checked?.value?.startsWith("item:")) {
    transferDialogState.payloadKind = checked.value;
  }
}

function populateTransferTargets(fromMember) {
  if (!transferToSelect || !fromMember) return null;
  const members = transferDialogState.members;
  const targets = members.filter((member) => member.id !== fromMember.id);
  transferToSelect.replaceChildren();
  for (const target of targets) {
    const option = document.createElement("option");
    option.value = target.id;
    option.textContent = target.name;
    transferToSelect.appendChild(option);
  }
  if (!targets.length) {
    transferDialogState.toCharacterId = null;
    return null;
  }
  const preferred = transferDialogState.toCharacterId;
  if (preferred && targets.some((target) => target.id === preferred)) {
    transferToSelect.value = preferred;
  } else {
    transferToSelect.value = targets[0].id;
    transferDialogState.toCharacterId = targets[0].id;
  }
  return members.find((member) => member.id === transferToSelect.value) || null;
}

function updateTransferItemAvailability(fromMember, toMember) {
  if (!fromMember || !transferItemOptions) return;
  for (const radio of transferItemOptions.querySelectorAll('input[name="transfer-payload"][value^="item:"]')) {
    const index = Number.parseInt(radio.value.slice(5), 10);
    const itemName = fromMember.inventory[index];
    const blocked = Boolean(toMember && itemName && !canMemberReceiveItem(toMember, itemName, transferSessionContext()));
    radio.disabled = blocked;
    const label = radio.closest("label");
    if (label && itemName) {
      const textNode = radio.nextSibling;
      if (textNode) {
        textNode.textContent = blocked ? `${itemName} (recipient full)` : itemName;
      }
    }
  }
  const checked = transferDialogForm?.querySelector('input[name="transfer-payload"]:checked');
  if (checked?.disabled) {
    transferDialogState.payloadKind = null;
    selectDefaultTransferPayload(fromMember, toMember);
  }
}

function syncTransferGoldControls(fromMember, toMember) {
  if (!fromMember) return;
  if (transferGoldRadio) {
    transferGoldRadio.disabled = fromMember.gold <= 0;
  }
  const maxGold = maxTransferGoldAmount(fromMember, toMember);
  if (transferGoldAmount) {
    transferGoldAmount.max = String(Math.max(maxGold, 1));
    if (Number.parseInt(transferGoldAmount.value || "0", 10) > maxGold) {
      transferGoldAmount.value = maxGold > 0 ? String(maxGold) : "0";
    }
    transferGoldAmount.disabled = !transferGoldRadio?.checked || maxGold <= 0;
  }
}

function refreshTransferRecipientState() {
  if (!transferFromSelect || !transferDialogState.context) return;
  const fromId = transferFromSelect.value;
  const fromMember = transferDialogState.members.find((member) => member.id === fromId) || null;
  const toMember = fromMember
    ? transferDialogState.members.find((member) => member.id === transferToSelect?.value) || null
    : null;
  updateTransferItemAvailability(fromMember, toMember);
  syncTransferGoldControls(fromMember, toMember);
  updateTransferConfirmState();
}

function refreshTransferDialog(fromChanged = false) {
  if (!transferFromSelect || !transferDialogState.context) return;
  const fromId = transferFromSelect.value;
  const fromMember = transferDialogState.members.find((member) => member.id === fromId) || null;

  transferPayloadStep?.classList.toggle("hidden", !fromMember);
  transferToStep?.classList.toggle("hidden", !fromMember);

  if (!fromMember) {
    resetTransferDialogForm();
    return;
  }

  if (fromChanged) {
    transferDialogState.payloadKind = null;
    transferDialogState.toCharacterId = null;
  }

  const toMember = populateTransferTargets(fromMember);
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
        const blocked = toMember && !canMemberReceiveItem(toMember, itemName, transferSessionContext());
        radio.disabled = blocked;
        radio.addEventListener("change", () => {
          rememberTransferPayloadSelection();
          syncTransferGoldControls(fromMember, toMember);
          updateTransferConfirmState();
        });
        label.append(radio, document.createTextNode(blocked ? `${itemName} (recipient full)` : itemName));
        transferItemOptions.appendChild(label);
      });
    }
  }

  syncTransferGoldControls(fromMember, toMember);
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
    if (!itemName || !toMember || !canMemberReceiveItem(toMember, itemName, transferSessionContext())) return null;
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

  resetTransferDialogForm();
  transferDialogState.context = context;
  transferDialogState.members = members;
  transferDialogState.payloadKind = null;
  transferDialogState.toCharacterId = null;
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
  transferFromSelect.value = givers[0].id;

  refreshTransferDialog(true);
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
      resetTransferDialogState();
    }
  } catch (error) {
    handleError(error);
  } finally {
    if (transferDialogState.context) {
      updateTransferConfirmState();
    }
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

const SHEET_ICON_SVGS = {
  equipment:
    '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2 16 3.5 7 18l-1.5-1.5z"/><path d="M20 4 9 17"/><path d="m4 20 4-1 9-9-3-3-9 9z"/></svg>',
  inventory:
    '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 6h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z"/><path d="M9 6V5a3 3 0 0 1 6 0v1"/><path d="M8 11h8"/></svg>',
  changeWeapon:
    '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 3 5 14l-2 7 7-2 11-11z"/><path d="m15 5 4 4"/></svg>',
};

function createSheetIconButton({ kind, ariaLabel, tooltip, disabled = false, pressed = false, onClick }) {
  const button = node("button", `secondary sheet-icon-btn sheet-icon-${kind}`);
  button.type = "button";
  button.setAttribute("aria-label", ariaLabel);
  button.innerHTML = SHEET_ICON_SVGS[kind] || "";
  button.disabled = disabled;
  button.setAttribute("aria-pressed", pressed ? "true" : "false");
  setButtonTooltip(button, tooltip);
  if (onClick) {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      onClick(event);
    });
  }
  return button;
}

function memberInventoryCount(member) {
  return (member.inventory || []).length;
}

function updateInventoryIconBadge(inventoryBtn, member, isOpen) {
  let badge = inventoryBtn.querySelector(".sheet-icon-badge");
  const count = memberInventoryCount(member);
  if (isOpen || count <= 0) {
    badge?.remove();
    return;
  }
  if (!badge) {
    badge = node("span", "sheet-icon-badge");
    inventoryBtn.appendChild(badge);
  }
  badge.textContent = count > 9 ? "9+" : String(count);
}

function buildMemberInventoryPanel(member) {
  const panel = node("div", "member-inventory-panel");
  const items = member.inventory || [];
  if (!items.length) {
    panel.appendChild(node("div", "muted", "Inventory empty"));
    return panel;
  }
  const list = document.createElement("ul");
  list.className = "member-inventory-list";
  for (const itemName of items) {
    const entry = document.createElement("li");
    if (member.class_id === "barbarian" && itemName.toLowerCase().includes("potion of healing")) {
      entry.textContent = `${itemName} (transfer to ally)`;
    } else {
      entry.textContent = itemName;
    }
    list.appendChild(entry);
  }
  panel.appendChild(list);
  return panel;
}

function inventoryIconTooltip(member) {
  const count = (member.inventory || []).length;
  const summary = count ? `${count} item${count === 1 ? "" : "s"}` : "empty";
  return `Inventory (${summary}) — click to show or hide carried items.`;
}

function appendMemberSheetHeaderActions(actions, session, member, inventoryPanel) {
  if (!state.sheetInventoryOpen) state.sheetInventoryOpen = {};
  const inventoryOpen = Boolean(state.sheetInventoryOpen[member.character_id]);
  inventoryPanel.classList.toggle("hidden", !inventoryOpen);

  const inventoryBtn = createSheetIconButton({
    kind: "inventory",
    ariaLabel: "Toggle inventory",
    tooltip: inventoryIconTooltip(member),
    pressed: inventoryOpen,
    onClick: () => {
      const nextOpen = !state.sheetInventoryOpen[member.character_id];
      state.sheetInventoryOpen[member.character_id] = nextOpen;
      if (nextOpen) {
        const details = inventoryPanel.closest("details.party-sheet-details");
        if (details && !details.open) {
          details.open = true;
          state.partySheetOpen[member.character_id] = true;
        }
      }
      inventoryPanel.classList.toggle("hidden", !nextOpen);
      inventoryBtn.setAttribute("aria-pressed", nextOpen ? "true" : "false");
      updateInventoryIconBadge(inventoryBtn, member, nextOpen);
    },
  });
  updateInventoryIconBadge(inventoryBtn, member, inventoryOpen);
  actions.appendChild(inventoryBtn);

  const inExploration = session.mode === "exploration" && member.current_life > 0;
  if (inExploration && canEditWeaponDefaults(member)) {
    actions.appendChild(
      createSheetIconButton({
        kind: "equipment",
        ariaLabel: "Equipment slots",
        tooltip: ACTION_TOOLTIPS.weaponDefaults,
        onClick: () => openWeaponPickerDialog({ mode: "defaults", source: "session", member, session }),
      })
    );
  } else if (canEditWeaponDefaults(member)) {
    actions.appendChild(
      createSheetIconButton({
        kind: "equipment",
        ariaLabel: "Equipment slots",
        tooltip: "Equipment slots can only be changed during exploration.",
        disabled: true,
      })
    );
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
    if (weaponPickerTitle) weaponPickerTitle.textContent = `Equipment slots — ${member.name}`;
    const dualMelee = memberUsesDualMeleeDefaults(member);
    if (weaponPickerNote) {
      const base =
        source === "roster"
          ? "Saved on this hero's roster. New adventures use these defaults when a fight starts."
          : "Defaults are noted on the hero sheet and used when a fight starts. Change them during exploration only.";
      const dualNote = dualMelee
        ? member.class_id === "swashbuckler"
          ? " Set main-hand and off-hand melee weapons for two attacks per round."
          : member.class_id === "ranger"
            ? " Set two compatible melee weapons for dual wield. Outdoors, one bow default fires twice (+½L each)."
            : " Set two light weapons for dual-wield attacks."
        : member.class_id === "ranger"
          ? " Outdoors, one bow default fires twice per round (+½L each)."
          : "";
      weaponPickerNote.textContent = `${base}${dualNote}`;
    }
    weaponPickerDefaultsStep?.classList.remove("hidden");
    weaponPickerDrawStep?.classList.add("hidden");
    const meleeOptions = memberMeleeWeapons(member);
    const missileOptions = memberMissileWeapons(member);
    fillWeaponSelect(weaponPickerMeleeSelect, meleeOptions, member.default_melee_weapon);
    const secondaryStep = document.getElementById("weapon-picker-melee-secondary-step");
    const secondaryOptions = dualMelee ? secondaryMeleeOptions(member, weaponPickerMeleeSelect?.value) : [];
    if (secondaryStep) secondaryStep.classList.toggle("hidden", !dualMelee || !secondaryOptions.length);
    if (weaponPickerMeleeSecondarySelect) {
      fillWeaponSelect(weaponPickerMeleeSecondarySelect, secondaryOptions, member.default_melee_weapon_secondary);
      if (weaponPickerMeleeSelect) {
        weaponPickerMeleeSelect.onchange = () => {
          const nextSecondary = secondaryMeleeOptions(member, weaponPickerMeleeSelect.value);
          fillWeaponSelect(weaponPickerMeleeSecondarySelect, nextSecondary, member.default_melee_weapon_secondary);
          secondaryStep?.classList.toggle("hidden", !nextSecondary.length);
        };
      }
    }
    fillWeaponSelect(weaponPickerMissileSelect, missileOptions, member.default_missile_weapon);
    document.getElementById("weapon-picker-melee-step")?.classList.toggle("hidden", !meleeOptions.length);
    document.getElementById("weapon-picker-missile-step")?.classList.toggle("hidden", !missileOptions.length);
    if (weaponPickerConfirmBtn) weaponPickerConfirmBtn.textContent = "Save equipment";
  } else {
    const wielded = session.wielded_melee_weapons?.[member.character_id];
    const drawOptions = memberMeleeWeapons(member).filter((weapon) => weapon !== wielded);
    if (!drawOptions.length) return;
    if (weaponPickerTitle) weaponPickerTitle.textContent = `Change weapon — ${member.name}`;
    if (weaponPickerNote) {
      weaponPickerNote.textContent = wielded
        ? `Currently wielding ${wielded}. Drawing another weapon costs this hero's turn.`
        : "Choose a melee weapon to wield for the rest of this fight.";
    }
    weaponPickerDefaultsStep?.classList.add("hidden");
    weaponPickerDrawStep?.classList.remove("hidden");
    fillWeaponSelect(weaponPickerDrawSelect, drawOptions, drawOptions[0]);
    if (weaponPickerConfirmBtn) weaponPickerConfirmBtn.textContent = "Change weapon";
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
      const meleeSecondary = weaponPickerMeleeSecondarySelect?.value;
      const missile = weaponPickerMissileSelect?.value;
      if (melee && melee !== member.default_melee_weapon) {
        updates.push({ weapon_kind: "melee", item_name: melee });
        payload.default_melee_weapon = melee;
      }
      if (meleeSecondary && meleeSecondary !== member.default_melee_weapon_secondary) {
        payload.default_melee_weapon_secondary = meleeSecondary;
      }
      if (missile && missile !== member.default_missile_weapon) {
        updates.push({ weapon_kind: "missile", item_name: missile });
        payload.default_missile_weapon = missile;
      }
      if (!Object.keys(payload).length) {
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

function characterAvailableForSession(character, sessionId) {
  if (!character) return false;
  if (!character.active_session_id) return true;
  return character.active_session_id === sessionId;
}

function renderPartyRegroup(session) {
  if (!session.party_editable) return null;
  const details = document.createElement("details");
  details.className = "party-regroup-details";
  details.open = Boolean(state.partyRegroupOpen);
  const summary = document.createElement("summary");
  summary.appendChild(document.createTextNode("Regroup Party"));
  const summaryHint = node(
    "span",
    "party-regroup-summary-hint",
    session.camped_outside
      ? "Camped outside — swap heroes or marching order before re-entering."
      : "Saved game — swap heroes or marching order before continuing."
  );
  summary.appendChild(summaryHint);
  details.appendChild(summary);

  const instruction = node(
    "p",
    "party-regroup-instruction",
    "Pick four different heroes for marching order #1 (lead) through #4 (rear), then Apply. " +
      "Heroes you remove return to the home roster; the explored map and any fallen bodies stay as they are."
  );
  details.appendChild(instruction);

  const ordered = [...(session.party || [])].sort((left, right) => left.marching_order - right.marching_order);
  const slotIds = ordered.map((member) => member.character_id);
  while (slotIds.length < 4) slotIds.push("");
  const selects = [];
  const rosterChoices = state.characters.filter((character) =>
    characterAvailableForSession(character, session.id)
  );
  const slots = node("div", "party-regroup-slots");
  for (let index = 0; index < 4; index += 1) {
    const row = node("div", "combat-target-row");
    row.appendChild(document.createTextNode(`#${index + 1}`));
    const select = document.createElement("select");
    select.dataset.slotIndex = String(index);
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Choose hero";
    select.appendChild(empty);
    for (const character of rosterChoices) {
      const option = document.createElement("option");
      option.value = character.id;
      option.textContent = `${character.name} (${character.class_name} L${character.level})`;
      select.appendChild(option);
    }
    select.value = slotIds[index] || "";
    selects.push(select);
    row.appendChild(select);
    slots.appendChild(row);
  }
  details.appendChild(slots);

  const applyBtn = node("button", "secondary party-regroup-apply", "Apply regroup");
  applyBtn.type = "button";
  applyBtn.addEventListener("click", async () => {
    const character_ids = selects.map((select) => select.value).filter(Boolean);
    if (character_ids.length !== 4 || new Set(character_ids).size !== 4) {
      setStatus("Choose four different heroes for marching order #1–#4.");
      return;
    }
    try {
      state.session = await api(`/api/sessions/${session.id}/party`, {
        method: "PUT",
        body: JSON.stringify({ character_ids }),
      });
      await reloadCharacters();
      await refreshSessions();
      renderSession();
      setStatus("Party regrouped.");
    } catch (error) {
      handleError(error);
    }
  });
  details.appendChild(applyBtn);
  details.addEventListener("toggle", () => {
    state.partyRegroupOpen = details.open;
    saveLayoutPrefs();
  });
  return details;
}

function appendExplorationClassAbilities(item, session, member, tile) {
  if (member.current_life <= 0) return;
  const livingFoes = (tile?.enemies || []).filter((foe) => foe.life > 0);
  const inCombat = session.mode === "combat";
  const actions = node("div", "item-actions");

  if (member.class_id === "acrobat" && session.mode === "exploration" && acrobatTricksRemaining(session, member) > 0) {
    const allies = (session.party || []).filter(
      (ally) => ally.character_id !== member.character_id && ally.current_life > 0
    );
    if (allies.length) {
      const allyRow = node("div", "combat-target-row");
      allyRow.appendChild(document.createTextNode("Swap with:"));
      const allySelect = document.createElement("select");
      for (const ally of allies) {
        const option = document.createElement("option");
        option.value = ally.character_id;
        option.textContent = ally.name;
        allySelect.appendChild(option);
      }
      allySelect.value =
        state.abilityAllyTargets?.[member.character_id] || allies[0].character_id;
      allySelect.addEventListener("change", () => {
        state.abilityAllyTargets[member.character_id] = allySelect.value;
      });
      allyRow.appendChild(allySelect);
      actions.appendChild(allyRow);
      const shiftBtn = node("button", "secondary", "Trick: Shift Position");
      shiftBtn.type = "button";
      shiftBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          target_character_id:
            state.abilityAllyTargets?.[member.character_id] || allies[0].character_id,
          class_ability: "acrobat_shift_position",
        })
      );
      actions.appendChild(shiftBtn);
    }
  }
  if (member.class_id === "acrobat" && livingFoes.length && acrobatTricksRemaining(session, member) > 0) {
    if (livingFoes.length > 1) {
      const foeRow = node("div", "combat-target-row");
      foeRow.appendChild(document.createTextNode("Distract target:"));
      foeRow.appendChild(
        createFoeTargetSelect(livingFoes, {
          value: state.abilityFoeTargets?.[member.character_id],
          onChange: (foeId) => {
            state.abilityFoeTargets[member.character_id] = foeId;
          },
        })
      );
      actions.appendChild(foeRow);
    }
    const distractBtn = node("button", "secondary", "Trick: Distract");
    distractBtn.type = "button";
    distractBtn.addEventListener("click", () =>
      advance("use_class_ability", {
        character_id: member.character_id,
        foe_id: state.abilityFoeTargets?.[member.character_id] || livingFoes[0].id,
        class_ability: "acrobat_distract",
      })
    );
    actions.appendChild(distractBtn);
  }
  if (member.class_id === "acrobat" && session.pending_save_reroll?.character_id === member.character_id) {
    const leapBtn = node("button", "secondary", "Trick: Leap out of Harm");
    leapBtn.type = "button";
    leapBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "acrobat_leap_harm" })
    );
    actions.appendChild(leapBtn);
  }
  if (member.class_id === "acrobat" && !inCombat && acrobatTricksRemaining(session, member) > 0) {
    const gracefulBtn = node("button", "secondary", "Trick: Graceful Move");
    gracefulBtn.type = "button";
    gracefulBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "acrobat_graceful_move" })
    );
    actions.appendChild(gracefulBtn);
  }
  if (
    member.class_id === "mushroom_monk" &&
    !inCombat &&
    !(session.hyphae_used || []).includes(member.character_id)
  ) {
    const hyphaeRow = node("div", "combat-target-row");
    hyphaeRow.appendChild(document.createTextNode("Hyphae effect:"));
    const hyphaeSelect = document.createElement("select");
    for (const [value, label] of [
      ["search", "+1 next Search"],
      ["clue", "Gain 1 Clue"],
      ["secret_door", "Reveal secret door"],
      ["secret_passage", "Reveal secret passage"],
    ]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      hyphaeSelect.appendChild(option);
    }
    hyphaeRow.appendChild(hyphaeSelect);
    actions.appendChild(hyphaeRow);
    const hyphaeBtn = node("button", "secondary", "Hyphae communion");
    hyphaeBtn.type = "button";
    hyphaeBtn.addEventListener("click", () =>
      advance("use_class_ability", {
        character_id: member.character_id,
        class_ability: "mushroom_hyphae",
        search_choice: hyphaeSelect.value,
      })
    );
    actions.appendChild(hyphaeBtn);
  }
  if (member.class_id === "illusionist" && !inCombat) {
    const lightBtn = node("button", "secondary", "Continual Light");
    lightBtn.type = "button";
    lightBtn.addEventListener("click", () =>
      advance("use_class_ability", {
        character_id: member.character_id,
        class_ability: "illusionist_continual_light",
      })
    );
    actions.appendChild(lightBtn);
  }
  if (
    member.class_id === "gnome" &&
    gnomeGadgetsRemaining(session, member) > 0 &&
    session.mode === "exploration"
  ) {
    const allies = (session.party || []).filter(
      (ally) => ally.character_id !== member.character_id && ally.current_life > 0
    );
    if (allies.length) {
      const allyRow = node("div", "combat-target-row");
      allyRow.appendChild(document.createTextNode("Free ally:"));
      const allySelect = document.createElement("select");
      for (const ally of allies) {
        const option = document.createElement("option");
        option.value = ally.character_id;
        option.textContent = ally.name;
        allySelect.appendChild(option);
      }
      allyRow.appendChild(allySelect);
      actions.appendChild(allyRow);
      const freeBtn = node("button", "secondary", "Gadget: free restraints");
      freeBtn.type = "button";
      freeBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          target_character_id: allySelect.value,
          class_ability: "gnome_gadget_free",
        })
      );
      actions.appendChild(freeBtn);
    }
  }
  if (
    member.class_id === "kukla" &&
    hasExpertSkill(member, "army_of_dolls") &&
    !(session.army_of_dolls_deployed || []).includes(member.character_id)
  ) {
    const dollBtn = node("button", "secondary", "Deploy Army of Dolls");
    dollBtn.type = "button";
    dollBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "kukla_army_of_dolls" })
    );
    actions.appendChild(dollBtn);
  }
  if (member.class_id === "kukla" && !inCombat && member.current_life > 0) {
    const compartment = member.kukla_compartment_items || [];
    const compartmentGold = member.kukla_compartment_gold || 0;
    if (compartment.length || compartmentGold) {
      actions.appendChild(
        subline(
          `Secret compartment: ${compartment.join(", ") || "empty"}${compartmentGold ? `; ${compartmentGold}gp hidden` : ""}.`
        )
      );
    }
    const stashable = (member.inventory || []).filter(
      (item) => !/green ring|red ring/i.test(item)
    );
    if (stashable.length) {
      const stashRow = node("div", "combat-target-row");
      stashRow.appendChild(document.createTextNode("Stash in compartment:"));
      const stashSelect = document.createElement("select");
      for (const item of stashable) {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        stashSelect.appendChild(option);
      }
      stashRow.appendChild(stashSelect);
      actions.appendChild(stashRow);
      const stashBtn = node("button", "secondary", "Hide item");
      stashBtn.type = "button";
      stashBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          class_ability: "kukla_compartment_stash",
          item_name: stashSelect.value,
        })
      );
      actions.appendChild(stashBtn);
    }
    if (compartment.length) {
      const retrieveRow = node("div", "combat-target-row");
      retrieveRow.appendChild(document.createTextNode("Retrieve from compartment:"));
      const retrieveSelect = document.createElement("select");
      for (const item of compartment) {
        const option = document.createElement("option");
        option.value = item;
        option.textContent = item;
        retrieveSelect.appendChild(option);
      }
      retrieveRow.appendChild(retrieveSelect);
      actions.appendChild(retrieveRow);
      const retrieveBtn = node("button", "secondary", "Retrieve item");
      retrieveBtn.type = "button";
      retrieveBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          class_ability: "kukla_compartment_retrieve",
          item_name: retrieveSelect.value,
        })
      );
      actions.appendChild(retrieveBtn);
    }
    if (compartmentGold > 0) {
      const goldBtn = node("button", "secondary", `Retrieve ${compartmentGold}gp`);
      goldBtn.type = "button";
      goldBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          class_ability: "kukla_compartment_retrieve",
          gold_amount: compartmentGold,
        })
      );
      actions.appendChild(goldBtn);
    }
    if ((member.inventory || []).some((item) => /green ring/i.test(item))) {
      const fallenKuklas = (session.party || []).filter(
        (ally) =>
          ally.class_id === "kukla" &&
          ally.current_life <= 0 &&
          (currentTile(session)?.fallen_character_ids || []).includes(ally.character_id)
      );
      if (fallenKuklas.length) {
        const reviveRow = node("div", "combat-target-row");
        reviveRow.appendChild(document.createTextNode("Green ring — revive:"));
        const reviveSelect = document.createElement("select");
        for (const ally of fallenKuklas) {
          const option = document.createElement("option");
          option.value = ally.character_id;
          option.textContent = ally.name;
          reviveSelect.appendChild(option);
        }
        reviveRow.appendChild(reviveSelect);
        actions.appendChild(reviveRow);
        const reviveBtn = node("button", "secondary", "Use green ring");
        reviveBtn.type = "button";
        reviveBtn.addEventListener("click", () =>
          advance("use_class_ability", {
            character_id: member.character_id,
            target_character_id: reviveSelect.value,
            class_ability: "kukla_green_ring_revive",
          })
        );
        actions.appendChild(reviveBtn);
      }
    }
  }
  if (
    member.class_id === "kukla" &&
    (member.inventory || []).some((item) => /red ring/i.test(item)) &&
    livingFoes.length
  ) {
    const poisonRow = node("div", "combat-target-row");
    poisonRow.appendChild(document.createTextNode("Red ring poison:"));
    const foeSelect = document.createElement("select");
    for (const foe of livingFoes) {
      const option = document.createElement("option");
      option.value = foe.id;
      option.textContent = foe.name;
      foeSelect.appendChild(option);
    }
    poisonRow.appendChild(foeSelect);
    actions.appendChild(poisonRow);
    const poisonBtn = node("button", "secondary", "Use red ring poison");
    poisonBtn.type = "button";
    poisonBtn.addEventListener("click", () =>
      advance("use_class_ability", {
        character_id: member.character_id,
        foe_id: foeSelect.value,
        class_ability: "kukla_red_ring_poison",
      })
    );
    actions.appendChild(poisonBtn);
  }
  if (
    !inCombat &&
    (hasHeroicSkill(member, "training_focus") || hasLegendarySkill(member, "legendary_training_focus")) &&
    !(session.training_focus_bonus || {})[member.character_id]
  ) {
    const focusBtn = node("button", "secondary", "Bank Training Focus");
    focusBtn.type = "button";
    focusBtn.addEventListener("click", () =>
      advance("bank_training_focus", { character_id: member.character_id })
    );
    actions.appendChild(focusBtn);
  }
  if (
    !inCombat &&
    hasHeroicSkill(member, "restore_mental_capacity") &&
    !session.restore_mental_capacity_used
  ) {
    const allies = (session.party || []).filter((ally) => ally.current_life > 0);
    if (allies.length) {
      const allyRow = node("div", "combat-target-row");
      allyRow.appendChild(document.createTextNode("Restore mind:"));
      const allySelect = document.createElement("select");
      for (const ally of allies) {
        const option = document.createElement("option");
        option.value = ally.character_id;
        option.textContent = ally.name;
        allySelect.appendChild(option);
      }
      allySelect.value = state.abilityAllyTargets?.[member.character_id] || allies[0].character_id;
      allySelect.addEventListener("change", () => {
        state.abilityAllyTargets[member.character_id] = allySelect.value;
      });
      allyRow.appendChild(allySelect);
      actions.appendChild(allyRow);
      const restoreMindBtn = node("button", "secondary", "Restore Mental Capacity");
      restoreMindBtn.type = "button";
      restoreMindBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          target_character_id:
            state.abilityAllyTargets?.[member.character_id] || allies[0].character_id,
          class_ability: "restore_mental_capacity",
        })
      );
      actions.appendChild(restoreMindBtn);
    }
  }
  if (member.class_id === "illusionist" && livingFoes.length && inCombat) {
    if (livingFoes.length > 1) {
      const foeRow = node("div", "combat-target-row");
      foeRow.appendChild(document.createTextNode("Distract target:"));
      foeRow.appendChild(
        createFoeTargetSelect(livingFoes, {
          value: state.abilityFoeTargets?.[member.character_id],
          onChange: (foeId) => {
            state.abilityFoeTargets[member.character_id] = foeId;
          },
        })
      );
      actions.appendChild(foeRow);
    }
    const lightBtn = node("button", "secondary", "Distracting Lights");
    lightBtn.type = "button";
    lightBtn.addEventListener("click", () =>
      advance("use_class_ability", {
        character_id: member.character_id,
        foe_id: state.abilityFoeTargets?.[member.character_id] || livingFoes[0].id,
        class_ability: "illusionist_distract",
      })
    );
    actions.appendChild(lightBtn);
  }
  if (member.class_id === "gnome" && gnomeGadgetsRemaining(session, member) > 0 && (inCombat || livingFoes.length)) {
    const smokeBtn = node("button", "secondary", "Gadget: Smokescreen");
    smokeBtn.type = "button";
    smokeBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "gnome_smokescreen" })
    );
    actions.appendChild(smokeBtn);
  }
  if (member.class_id === "mushroom_monk" && livingFoes.length && mushroomSporesRemaining(session, member) > 0) {
    const sporeBtn = node("button", "secondary", "Spore cloud");
    sporeBtn.type = "button";
    sporeBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "mushroom_spore_cloud" })
    );
    actions.appendChild(sporeBtn);
  }
  if (member.class_id === "assassin" && inCombat && livingFoes.length && !session.assassin_hidden_id) {
    if (livingFoes.length > 1) {
      const foeRow = node("div", "combat-target-row");
      foeRow.appendChild(document.createTextNode("Mark target:"));
      foeRow.appendChild(
        createFoeTargetSelect(livingFoes, {
          value: state.abilityFoeTargets?.[member.character_id],
          onChange: (foeId) => {
            state.abilityFoeTargets[member.character_id] = foeId;
          },
        })
      );
      actions.appendChild(foeRow);
    }
    const hideBtn = node("button", "secondary", "Hide in Shadows");
    hideBtn.type = "button";
    hideBtn.addEventListener("click", () =>
      advance("use_class_ability", {
        character_id: member.character_id,
        foe_id: state.abilityFoeTargets?.[member.character_id] || livingFoes[0].id,
        class_ability: "assassin_hide",
      })
    );
    actions.appendChild(hideBtn);
  }
  if (member.class_id === "acrobat" && inCombat && acrobatTricksRemaining(session, member) > 0) {
    const twistBtn = node("button", "secondary", "Trick: Serpent Twist");
    twistBtn.type = "button";
    twistBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "acrobat_serpent_twist" })
    );
    actions.appendChild(twistBtn);
    const evadeBtn = node("button", "secondary", "Trick: Evade");
    evadeBtn.type = "button";
    evadeBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "acrobat_evade" })
    );
    actions.appendChild(evadeBtn);
  }
  if (
    member.class_id === "halfling" &&
    luckPointsRemaining(session, member) > 0 &&
    session.pending_treasure_reroll_tile_id === tile?.id
  ) {
    const luckTreasureBtn = node("button", "secondary", "Luck: reroll treasure");
    luckTreasureBtn.type = "button";
    luckTreasureBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "halfling_luck_treasure" })
    );
    actions.appendChild(luckTreasureBtn);
  }
  if (
    member.class_id === "halfling" &&
    luckPointsRemaining(session, member) > 0 &&
    session.pending_search_reroll_tile_id === tile?.id
  ) {
    const luckSearchBtn = node("button", "secondary", "Luck: reroll search");
    luckSearchBtn.type = "button";
    luckSearchBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "halfling_luck_search" })
    );
    actions.appendChild(luckSearchBtn);
  }
  if (
    member.class_id === "halfling" &&
    luckPointsRemaining(session, member) > 0 &&
    session.pending_save_reroll?.character_id === member.character_id
  ) {
    const luckSaveBtn = node("button", "secondary", "Luck: reroll save");
    luckSaveBtn.type = "button";
    luckSaveBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "halfling_reroll_save" })
    );
    actions.appendChild(luckSaveBtn);
  }
  if (member.class_id === "paladin" && session.mode === "exploration" && paladinPrayerRemaining(session, member) > 0) {
    const steedBtn = node("button", "secondary", "Prayer: Summon steed");
    steedBtn.type = "button";
    steedBtn.addEventListener("click", () =>
      advance("use_class_ability", { character_id: member.character_id, class_ability: "paladin_summon_steed" })
    );
    actions.appendChild(steedBtn);
  }
  if (member.class_id === "gnome" && gnomeGadgetsRemaining(session, member) > 0 && session.mode === "exploration") {
    const closedDoors = (tile?.exits || []).filter((exit) => exit.kind === "door" && !exit.door_open);
    if (closedDoors.length) {
      const doorRow = node("div", "combat-target-row");
      doorRow.appendChild(document.createTextNode("Gadget door:"));
      const doorSelect = document.createElement("select");
      for (const exit of closedDoors) {
        const option = document.createElement("option");
        option.value = exit.id;
        option.textContent = `${exit.direction} door`;
        doorSelect.appendChild(option);
      }
      doorRow.appendChild(doorSelect);
      actions.appendChild(doorRow);
      const doorBtn = node("button", "secondary", "Gadget: open door");
      doorBtn.type = "button";
      doorBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          class_ability: "gnome_gadget_door",
          exit_id: doorSelect.value,
          gadget_points: 1,
        })
      );
      actions.appendChild(doorBtn);
    }
    if (tile?.trap_key && !tile.trap_resolved) {
      const trapBtn = node("button", "secondary", "Gadget: disarm trap");
      trapBtn.type = "button";
      trapBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          class_ability: "gnome_gadget_trap",
          gadget_points: 1,
        })
      );
      actions.appendChild(trapBtn);
    }
  }
  if (actions.childElementCount) item.appendChild(actions);
}

function partySheetSummaryLine(member, session, tile) {
  const chips = heroStatusChips(session, member, tile);
  const chipNote = chips.length ? ` · ${chips.length} effect${chips.length === 1 ? "" : "s"}` : "";
  if (member.current_life <= 0) {
    return `${member.name} · ${member.class_name} · fallen${chipNote}`;
  }
  return `${member.name} · ${member.class_name} · HP ${member.current_life}/${member.max_life} · L${member.level}${chipNote}`;
}

function renderPartyState(session) {
  const target = partyStateTarget(session);
  if (partyState && partyState !== target) partyState.replaceChildren();
  target.replaceChildren();
  target.classList.remove("party-sheet-strip");
  const regroup = renderPartyRegroup(session);
  if (regroup) target.appendChild(regroup);
  const tile = currentTile(session);
  const members = session.party || [];
  if (!members.length) {
    target.appendChild(node("div", "item", "No party members in this session."));
    return;
  }
  if (!state.partySheetOpen) state.partySheetOpen = {};
  const ordered = [...members].sort((left, right) => left.marching_order - right.marching_order);
  const canReorder = session.mode === "exploration";
  for (const member of ordered) {
    const details = document.createElement("details");
    details.className = "party-sheet-details item";
    if (member.current_life <= 0) details.classList.add("party-sheet-fallen");
    const spellPickPending = session.level_up_spell_pending_character_id === member.character_id;
    if (spellPickPending) details.classList.add("spell-pick-pending");
    const inCombat = session.mode === "combat";
    const defaultOpen = spellPickPending || (inCombat && member.current_life > 0);
    details.open = state.partySheetOpen[member.character_id] ?? defaultOpen;

    const summary = document.createElement("summary");
    summary.className = "party-sheet-summary marching-order-row";
    summary.appendChild(classIconGraphic(member.class_id, member.class_name));
    summary.appendChild(node("span", "position", `#${member.marching_order}`));
    summary.appendChild(node("span", "party-sheet-meta", partySheetSummaryLine(member, session, tile)));

    const inventoryPanel = buildMemberInventoryPanel(member);
    const headerActions = node("div", "marching-order-actions");
    if (canReorder && member.current_life > 0) {
      const up = node("button", "secondary", "↑");
      up.type = "button";
      up.disabled = member.marching_order <= 1;
      setButtonTooltip(up, "Move this hero one step forward in marching order (position 1 leads).");
      up.addEventListener("click", (event) => {
        event.stopPropagation();
        advance("set_marching_order", {
          character_id: member.character_id,
          marching_order: member.marching_order - 1,
        });
      });
      const down = node("button", "secondary", "↓");
      down.type = "button";
      down.disabled = member.marching_order >= 4;
      setButtonTooltip(down, "Move this hero one step back in marching order (position 4 is rear).");
      down.addEventListener("click", (event) => {
        event.stopPropagation();
        advance("set_marching_order", {
          character_id: member.character_id,
          marching_order: member.marching_order + 1,
        });
      });
      headerActions.append(up, down);
    }
    appendMemberSheetHeaderActions(headerActions, session, member, inventoryPanel);
    summary.appendChild(headerActions);
    details.appendChild(summary);

    const body = node("div", "party-sheet-body");
    body.appendChild(inventoryPanel);
    body.appendChild(
      subline(
        `HP ${member.current_life}/${member.max_life} | Gold ${member.gold} | XP ${member.xp} | L${member.level} | Clues ${member.clues || 0}`
      )
    );
    const tierParts = [];
    if (member.expert_trained) tierParts.push("Expert");
    if (member.heroic_trained) tierParts.push("Heroic");
    if (member.legendary_trained) tierParts.push("Legendary");
    if (member.epic_trained) tierParts.push("Epic");
    if (tierParts.length) body.appendChild(subline(`Tier: ${tierParts.join(", ")}`));
    const expertLine = learnedExpertSkillsLine(member);
    if (expertLine) body.appendChild(subline(expertLine));
    appendStatusChips(body, heroStatusChips(session, member, tile));
    const abilityLine = abilityStatusLine(session, member);
    if (abilityLine) body.appendChild(subline(abilityLine));
    body.appendChild(subline(carryLimitsLine(member, session)));
    const encumbered = encumbranceReasons(member, session);
    if (encumbered.length) {
      body.appendChild(
        subline(`Over encumbered (−1 Defense and physical Saves): ${encumbered.join("; ")}.`)
      );
    }
    const wielded = session.wielded_melee_weapons?.[member.character_id];
    const meleeDefault = member.default_melee_weapon || "none";
    const missileDefault = member.default_missile_weapon || "none";
    body.appendChild(
      subline(
        session.mode === "combat" && wielded
          ? `Wielding ${wielded} · ${heroCombatPlanLabel(session, member, tile)} | Equipment: melee ${meleeDefault}, missile ${missileDefault}`
          : `Equipment: melee ${meleeDefault}, missile ${missileDefault}`
      )
    );
    if (isDetachedElsewhere(session, member)) {
      const elsewhere = (session.detached_groups || []).find((group) =>
        (group.character_ids || []).includes(member.character_id)
      );
      const detachedTile = (session.map_state?.tiles || []).find((item) => item.id === elsewhere?.tile_id);
      body.appendChild(
        subline(`Left behind at ${detachedTile?.title || "another room"} (${elsewhere?.reason || "guard"}).`)
      );
    }
    const xpSystem = session.xp_system || "classical";
    const levelUpSpellPickPending = Boolean(session.level_up_spell_pending_character_id);
    if (canReorder) {
      appendXpAdvancementChoices(body, session, member);
      tierTrainingButtons(session, member, body);
    }
    if (canReorder && member.current_life > 0 && xpSystem === "old_school" && !levelUpSpellPickPending) {
      const xpBtn = node("button", "secondary", "Old School Level Up");
      xpBtn.type = "button";
      setButtonTooltip(xpBtn, ACTION_TOOLTIPS.oldSchoolLevelUp);
      xpBtn.addEventListener("click", () => advance("old_school_level_up", { character_id: member.character_id }));
      body.appendChild(xpBtn);
    }
    if (
      canReorder &&
      member.current_life > 0 &&
      xpSystem === "slower_advancement" &&
      !levelUpSpellPickPending
    ) {
      appendSlowerAdvancementChoices(body, session, member);
    }
    if (
      canReorder &&
      session.mode === "exploration" &&
      member.current_life > 0 &&
      !isDetachedElsewhere(session, member)
    ) {
      if (!isDetachedHere(session, member)) {
        const leaveBtn = node("button", "secondary", "Leave behind on this tile");
        leaveBtn.type = "button";
        leaveBtn.addEventListener("click", () =>
          advance("detach_heroes", { detached_character_ids: [member.character_id] })
        );
        body.appendChild(leaveBtn);
        const scoutBtn = node("button", "secondary", "Scout ahead (1 turn behind)");
        scoutBtn.type = "button";
        scoutBtn.addEventListener("click", () =>
          advance("scout_ahead", { character_id: member.character_id })
        );
        body.appendChild(scoutBtn);
      } else {
        const rejoinBtn = node("button", "secondary", "Rejoin main group");
        rejoinBtn.type = "button";
        rejoinBtn.addEventListener("click", () =>
          advance("reattach_heroes", { detached_character_ids: [member.character_id] })
        );
        body.appendChild(rejoinBtn);
      }
    }
    if ((member.spells || []).length) {
      appendSpellSubline(body, member.spells, session, member);
    }
    if (member.class_id === "paladin" && member.current_life > 0 && paladinPrayerRemaining(session, member) > 0) {
      const healBtn = node("button", "secondary", "Prayer: heal ally");
      healBtn.type = "button";
      healBtn.addEventListener("click", () => {
        const allies = (session.party || []).filter(
          (ally) => ally.current_life > 0 && ally.current_life < ally.max_life
        );
        const targetId = allies[0]?.character_id || member.character_id;
        advance("use_class_ability", {
          character_id: member.character_id,
          target_character_id: targetId,
          class_ability: "paladin_heal",
        });
      });
      body.appendChild(healBtn);
    }
    if (
      member.class_id === "paladin" &&
      session.pending_save_reroll?.character_id === member.character_id &&
      paladinPrayerRemaining(session, member) > 0
    ) {
      const rerollBtn = node("button", "secondary", "Prayer: reroll Save");
      rerollBtn.type = "button";
      rerollBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          class_ability: "paladin_reroll_save",
        })
      );
      body.appendChild(rerollBtn);
    }
    if (
      session.mode === "combat" &&
      member.current_life > 0 &&
      hasExpertSkill(member, "turn_undead")
    ) {
      const turnBtn = node("button", "secondary", "Turn Undead");
      turnBtn.type = "button";
      turnBtn.addEventListener("click", () =>
        advance("use_class_ability", { character_id: member.character_id, class_ability: "turn_undead" })
      );
      body.appendChild(turnBtn);
    }
    if (
      session.mode === "combat" &&
      member.current_life > 0 &&
      hasExpertSkill(member, "combat_acrobatics")
    ) {
      const allies = (session.party || []).filter(
        (ally) => ally.character_id !== member.character_id && ally.current_life > 0
      );
      if (allies.length) {
        const swapBtn = node("button", "secondary", "Combat Acrobatics (swap)");
        swapBtn.type = "button";
        swapBtn.addEventListener("click", () => {
          const ally = allies[0];
          advance("use_class_ability", {
            character_id: member.character_id,
            class_ability: "combat_acrobatics",
            target_character_id: ally.character_id,
          });
        });
        body.appendChild(swapBtn);
      }
    }
    if (
      session.mode === "combat" &&
      member.current_life > 0 &&
      hasExpertSkill(member, "spore_alchemy") &&
      (session.expert_spore_doses?.[member.character_id] || 0) > 0
    ) {
      const sporeBtn = node("button", "secondary", `Throw sleep spore (${session.expert_spore_doses[member.character_id]})`);
      sporeBtn.type = "button";
      sporeBtn.addEventListener("click", () =>
        advance("use_class_ability", { character_id: member.character_id, class_ability: "throw_spore" })
      );
      body.appendChild(sporeBtn);
    }
    if (
      session.mode === "exploration" &&
      hasExpertSkill(member, "lesser_necromancy") &&
      (tile?.fallen_character_ids || []).length
    ) {
      const fallenId = tile.fallen_character_ids[0];
      const fallen = (session.party || []).find((entry) => entry.character_id === fallenId);
      if (fallen) {
        const necBtn = node("button", "secondary", `Lesser Necromancy (${fallen.name})`);
        necBtn.type = "button";
        necBtn.addEventListener("click", () =>
          advance("use_class_ability", {
            character_id: member.character_id,
            class_ability: "lesser_necromancy",
            target_character_id: fallenId,
          })
        );
        body.appendChild(necBtn);
      }
    }
    if (
      member.class_id === "halfling" &&
      session.pending_save_reroll?.character_id === member.character_id &&
      luckPointsRemaining(session, member) > 0
    ) {
      const luckSaveBtn = node("button", "secondary", "Luck: reroll Save");
      luckSaveBtn.type = "button";
      luckSaveBtn.addEventListener("click", () =>
        advance("use_class_ability", {
          character_id: member.character_id,
          class_ability: "halfling_reroll_save",
        })
      );
      body.appendChild(luckSaveBtn);
    }
    appendExplorationClassAbilities(body, session, member, tile);
    if (session.mode === "exploration") {
      appendMemberExplorationActions(body, session, member);
    } else if (session.mode === "combat") {
      const livingFoes = (tile?.enemies || []).filter((foe) => foe.life > 0);
      appendMemberCombatActions(body, session, member, tile, livingFoes, reactionsOpen(session));
    }
    if (spellPickPending) {
      const pick = node("div", "level-up-spell-pick");
      pick.appendChild(node("strong", "", "Choose spell for new slot:"));
      const pickRow = node("div", "level-up-spell-pick-actions");
      appendLevelUpSpellPickButtons(pickRow, member);
      pick.appendChild(pickRow);
      body.appendChild(pick);
    }
    details.appendChild(body);
    details.addEventListener("toggle", () => {
      state.partySheetOpen[member.character_id] = details.open;
    });
    target.appendChild(details);
  }
}

function renderLog(session) {
  sessionLog.replaceChildren();
  for (const entry of filteredLogEntries(session, { limit: 80 })) {
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
    const character_ids = filledPartyCharacterIds();
    if (character_ids.length !== 4) {
      setStatus("Fill all 4 party slots before saving.");
      return;
    }
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

if (characterFilterAvailability) {
  characterFilterAvailability.addEventListener("change", () => {
    state.characterFilters.availability = characterFilterAvailability.value;
    renderCharacters();
  });
}

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
    const party = state.parties.find((item) => item.id === party_id);
    if (party && partyHasBusyMembers(party)) {
      setStatus("One or more party members are already in an active adventure.");
      return;
    }
    state.session = await api("/api/sessions", {
      method: "POST",
      body: JSON.stringify({
        party_id,
        adventure_id,
        xp_system: xpSystemSelect?.value || "classical",
        map_bounds_mode: mapBoundsSelect?.value || "unlimited",
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

logModeSummaryBtn?.addEventListener("click", () => setLogMode("summary"));
logModeVerboseBtn?.addEventListener("click", () => setLogMode("verbose"));

for (const btn of [combatCinemaToggleBtn, combatCinemaToggleRailBtn, combatCinemaToggleTacticalBtn]) {
  btn?.addEventListener("click", () => toggleCombatCinema());
}

combatCommandRailEl?.addEventListener("click", (event) => {
  const tabBtn = event.target.closest(".combat-command-tab");
  if (!tabBtn?.dataset.tab) return;
  setCombatCommandTab(tabBtn.dataset.tab);
  if (state.session) {
    renderCombatCommandRail(state.session);
  }
});

function setupTacticalRoomResizeObserver() {
  if (!tacticalRoomViewportEl || tacticalRoomViewportEl.dataset.resizeBound === "1") return;
  tacticalRoomViewportEl.dataset.resizeBound = "1";
  if (typeof ResizeObserver === "undefined") return;
  let resizeTimer = null;
  const observer = new ResizeObserver(() => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(() => {
      if (state.session && shouldUseCombatFocus(state.session)) {
        tacticalRoomLastSize = "";
        scheduleTacticalRoomRender(state.session);
      }
    }, 80);
  });
  observer.observe(tacticalRoomViewportEl);
}

initLayoutResizers();
setupTacticalRoomResizeObserver();
window.addEventListener("resize", () => {
  if (sessionMain?.classList.contains("combat-focus")) {
    syncCombatViewportLayout();
    if (state.session) scheduleTacticalRoomRender(state.session);
  }
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
mapViewportEl.addEventListener(
  "click",
  (event) => {
    if (!state.mapSuppressClick) return;
    state.mapSuppressClick = false;
    event.preventDefault();
    event.stopPropagation();
  },
  true
);
setupMapViewportResize();

async function reloadCharacters() {
  state.characters = await api("/api/characters");
  renderCharacters();
}

const ADVENTURE_SPELL_CONFIRM_KEYS = new Set(["fireball", "lightning"]);

function shouldConfirmAdventureSpell(action, extra) {
  if (action !== "cast_spell" || !state.session) return false;
  const key = normalizeSpellKey(extra.spell_name || "");
  if (!ADVENTURE_SPELL_CONFIRM_KEYS.has(key)) return false;
  const casterId = extra.character_id;
  const expended = ((state.session.expended_spells || {})[casterId] || []).map(normalizeSpellKey);
  return !expended.includes(key);
}

async function advance(action, extra = {}) {
  if (!state.session) return false;
  if (shouldConfirmAdventureSpell(action, extra)) {
    const spell = extra.spell_name || "This spell";
    const ok = window.confirm(
      `${spell} is expended until this adventure ends (still on your spell list). Cast now?`
    );
    if (!ok) return false;
  }
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
      clearActiveSessionId();
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
searchClueBtn?.addEventListener("click", () =>
  advance("search", {
    search_choice: "clue",
    character_id: searchClueHolderSelect?.value || undefined,
  })
);
checkReactionBtn?.addEventListener("click", () => advance("check_reaction"));
startCombatBtn?.addEventListener("click", () => advance("start_combat"));
combatStartBtn?.addEventListener("click", () => advance("start_combat"));
payBribeBtn?.addEventListener("click", () => advance("pay_bribe", { pay_bribe: true }));
declineBribeBtn?.addEventListener("click", () => advance("pay_bribe", { pay_bribe: false }));
tradeInfoSellBtn?.addEventListener("click", () =>
  advance("trade_information", { trade_information_choice: "sell" })
);
tradeInfoBuyBtn?.addEventListener("click", () =>
  advance("trade_information", { trade_information_choice: "buy" })
);
tradeInfoDeclineBtn?.addEventListener("click", () =>
  advance("trade_information", { trade_information_choice: "decline" })
);
function resolveCombatRound() {
  const payload = { subdual: Boolean(subdualInput?.checked) };
  const targets = buildAttackTargetsPayload();
  if (targets) payload.attack_targets = targets;
  const secondaryTargets = buildCombatSecondaryTargetsPayload();
  if (secondaryTargets) payload.attack_secondary_targets = secondaryTargets;
  const kickTargets = buildDoubleKickTargetsPayload();
  if (kickTargets) payload.double_kick_targets = kickTargets;
  const incenseTargets = buildProtectiveIncenseTargetsPayload();
  if (incenseTargets) payload.protective_incense_targets = incenseTargets;
  const abilities = buildCombatAbilitiesPayload();
  if (abilities) payload.combat_abilities = abilities;
  const guards = buildCombatGuardTargetsPayload();
  if (guards) payload.guard_targets = guards;
  advance("combat_round", payload).then(() => {
    state.combatAbilities = {};
    state.combatGuardTargets = {};
  });
}

combatBtn.addEventListener("click", () => resolveCombatRound());
combatResolveBtn?.addEventListener("click", () => resolveCombatRound());
combatFleeBtn?.addEventListener("click", () => advance("flee"));
combatFleeLuckBtn?.addEventListener("click", () => {
  const luckHalfling = state.session ? halflingForLuckFlee(state.session) : null;
  if (!luckHalfling) return;
  advance("flee", { use_luck_flee: true, character_id: luckHalfling.character_id });
});
rulesReferenceSearchEl?.addEventListener("input", () => {
  refreshRulesReference().catch(handleError);
});
rulesReferenceCategoryEl?.addEventListener("change", () => {
  refreshRulesReference().catch(handleError);
});
rulesReferenceStatusEl?.addEventListener("change", () => {
  refreshRulesReference().catch(handleError);
});
fleeBtn?.addEventListener("click", () => advance("flee"));
combatWithdrawBtn?.addEventListener("click", () => {
  const session = state.session;
  if (!session) return;
  const tile = currentTile(session);
  const doors = combatWithdrawDoorOptions(session, tile);
  const chosen =
    doors.find((exit) => exit.id === state.combatWithdrawExitId) ||
    doors.find((exit) => exit.kind === "door" && exit.destination_tile_id);
  if (chosen) advance("withdraw", { exit_id: chosen.id });
});
withdrawBtn?.addEventListener("click", () => {
  const session = state.session;
  if (!session) return;
  const tile = currentTile(session);
  const doors = combatWithdrawDoorOptions(session, tile);
  const chosen =
    doors.find((exit) => exit.id === state.combatWithdrawExitId) ||
    doors.find((exit) => exit.kind === "door" && exit.destination_tile_id);
  if (chosen) advance("withdraw", { exit_id: chosen.id });
});
resolveTrapBtn.addEventListener("click", () => advance("resolve_trap"));
claimTreasureBtn.addEventListener("click", () => advance("claim_treasure"));
restBtn.addEventListener("click", () => {
  if (!state.session || state.session.rest_used) return;
  const restStatus = restEligibility(state.session);
  if (!restStatus.ok) {
    setStatus(restStatus.reason);
    restPanelOpen = false;
    renderRestChoices(state.session);
    return;
  }
  restPanelOpen = !restPanelOpen;
  renderRestChoices(state.session);
});
saveSessionBtn.addEventListener("click", async () => {
  if (!state.session) return;
  const defaultLabel = sessionDisplayTitle(state.session);
  const label = window.prompt("Save label (optional):", state.session.save_label || defaultLabel);
  if (label === null) return;
  try {
    state.session = await api(`/api/sessions/${state.session.id}/save`, {
      method: "POST",
      body: JSON.stringify({ label: label.trim() || null }),
    });
    writeActiveSessionId(state.session.id);
    await refreshSessions();
    renderSession();
    setStatus("Game saved to server");
  } catch (error) {
    handleError(error);
  }
});

transferFromSelect?.addEventListener("change", () => refreshTransferDialog(true));
transferToSelect?.addEventListener("change", () => {
  transferDialogState.toCharacterId = transferToSelect.value;
  refreshTransferRecipientState();
});
transferGoldRadio?.addEventListener("change", () => {
  rememberTransferPayloadSelection();
  refreshTransferRecipientState();
});
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
  resetTransferDialogState();
  resetTransferDialogForm();
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
