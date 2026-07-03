# Rulebook Checking Guide

This is the consolidated player-facing checking/signoff guide. Spreadsheet
outputs live under `docs/Checking/Outputs/`. Internal compliance audits remain
in `docs/` because they are engineering audit records referenced by coverage
docs and tests.

Use this to validate **how the game behaves** — not to change `RULE_COVERAGE.md` status labels.

**PDF:** `Rules/Four_Against_Darkness_Expanded_Edition.pdf` unless noted.

**In-app references while playing:**
- Home → **Rules tables** — row text for each table
- Home → **Rules reference** — searchable mechanic summaries
- Session **log** (Summary vs Full rolls mode)
- **Party sheet** / **Exits panel** / **map markers** — where actions appear

**Columns:** `Pass` | `Fail` | `Skip` | `Notes`

---

## How to validate

| Step | What to do |
|------|------------|
| 1 | Open the PDF to the source page in the table row |
| 2 | Trigger the mechanic in a live session (see “How to trigger”) |
| 3 | Compare PDF → log line → UI state → session outcome |
| 4 | Tick Pass/Fail and write Notes (include hero, tile, roll if visible) |

**Forcing specific rolls:** the live UI has no dice cheat. Options:
- Play until the row appears naturally (log the roll when shown)
- Use pytest as a **behavior reference** (`tests/test_exploration.py`, `tests/test_environment_special_events.py`, `tests/test_reactions.py`)
- Temporarily add a dev-only roll override only if you need exhaustive coverage (not in repo today)

---

## Where to start (recommended order)

```
0. Camp-first start (optional) ← Begin camped outside → hirelings → bank → (Re)enter
1. Exploration harness     ← learn movement, search, doors, log modes
2. Tile Content Table      ← everything else spawns from room entry
3. Dungeon Special Features
4. Dungeon Special Events
5. Caverns + Fungal events ← use Secret Passage / environment switch
6. Reactions               ← fight what tile content spawns
7. Saves                   ← traps, poison, doors, event saves (overlap above)
8. Equipment               ← loot, armory, shop, carry limits
9. Secrets                 ← clues, reveal, use-secret timing
10. Character classes      ← cross-cutting; one pass per class
```

**Start at §1 Exploration harness**, then **§2 Tile Content** on the same session. Tile content only matters when you **enter a newly generated room/corridor** — you need the exploration loop working first.

---

## §0 Camp-first session start (optional)

**PDF:** EE p.44 camp; Abyss pp.27–33 hirelings.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Home → Adventure → check **Begin camped outside** → Start Session | Camp panel opens; log mentions camp before first foray |
| 2 | Camp → Hirelings → hire retainer (Expert tier party) | Retainer appears in the shared marching order; assigned bodyguard/acolyte is adjacent to the chosen hero; gold spent |
| 3 | Camp → Bank → deposit carried gold | Carried → bank; status confirms |
| 4 | Camp → **(Re)enter Dungeon** | `camped_outside` clears; exploration at entrance |
| 5 | Imported adventure: repeat 1–4 | Entrance `on_enter` foes/triggers fire only after step 4 |
| 6 | Home party: select saved party matching camped session | **Feed hungry** / **Bank carried gold** visible when applicable |
| 7 | Roster: click party member name in party builder | Roster scrolls to and expands that hero |

**Pass/Fail notes:**

---

## §TAG Adventure Leads (`Tales_from_the_adventurers_guild.pdf`)

Use Home → Adventure → TAG Settlement → **Maps and Adventure Leads**. The **Adventure lead** dropdown has hover text for valid Detail ranges. After creating a lead, open the normal **Adventure** section/dropdown and start the generated module.

Before testing generated Adventures Guild modules, run Developer → Rules PDF Import against the owned local PDF and confirm the extraction status reports 12 Rumors, 19 Scenes, and 0 suspected cut-off warnings.

| # | Mechanic | PDF | How to trigger | Check |
|---|----------|-----|----------------|-------|
| TAG.1 | Rumor Scene install | TAG pp.22-24, scenes pp.25-31 | Select Rumor Scene; enter 1-12; Create adventure | Installed adventure title names the rumor; `source.parameters.tag_reference` has scene/page/reward notes; finale uses the TAG-specific foe profile where one is defined |
| TAG.2 | Medusa rumor exact foe | TAG pp.22, 25-26 | Rumor Scene Detail `2` | Final room is Xasartha's cabin; Scene 10 approach and Scene 1 stealth/reaction choices appear before combat; Xasartha spawns only when the printed result says combat starts; notes mention Scene 1 pendant and source pages |
| TAG.3 | Thematic Dungeon install | TAG pp.38-48 | Select Thematic Dungeon; enter 1-6 | Title and room text match the theme; tag reference lists target room count, special rules, final foe groups, rewards |
| TAG.4 | Dragon's Lair theme | TAG pp.39-40 | Thematic Dungeon Detail `3` | Notes mention four-room target, 2-Clue dragon-type reveal, and Young Dragon/Young Red Dragon handling |
| TAG.5 | Guild Job install | TAG pp.54-59 | Select Guild Job; enter 1-6 or leave blank | Guild table row is used; minor quests carry named source/reward notes; rumor/theme jobs reuse their profiles |
| TAG.6 | TAG references in Services | TAG pp.54, 61-65 | Refresh TAG services | Adventurers Guild jobs, Trinkets, Guild spells, and TAG special foes rows appear with cost/summary/automation text and hover hints |
| TAG.7 | Mixed TAG finales | TAG pp.31, 48, 55 | Create Shaura, Bandit Hideout, or Gorungar leads | Final encounter includes multiple foe groups where printed: priestess + cultists, chieftain + bandits, Gorungar + archers |
| TAG.8 | Branch action controls | TAG scene pages | TAG Actions → Branch | Social choices log, Clue spends deduct Clues, variable counts roll/log, capture-alive can award a Clue, rewards can add gp. Changing the Branch selector updates the helper row explaining what Reference and Amount should contain for that action |
| TAG.9 | Route controls | TAG scene pages | TAG Actions → Route | Parley success/failure, Clue gates, peaceful/hostile branches, skipped/unlocked scenes, solo restrictions, and final routes persist in `tag_adventure_routes`; Clue unlocks deduct Clues |
| TAG.10 | Scene result controls | TAG scene/theme pages | TAG Actions → Scene result | Printed results apply and log: Medusa pendant, gargoyle bounty, Gorungar bounty, bandit capture, Shaura reward, Daroc's cat, mutant-fish rations, Agaratha, Deoldyn training, Dragon's Lair type reveal. Dragon's Lair reveal also rewrites the latest installed Dragon's Lair finale title/reference while keeping the validated Young Dragon encounter proxy |
| TAG.11 | XP controls | TAG scene/theme pages | TAG Actions → XP | Pending scene XP, minor encounter count, capture XP, and training XP-roll markers persist in `tag_xp_markers`; Award XP adds XP immediately to the selected character |
| TAG.12 | Trinkets and Guild spells | TAG pp.61-66 | TAG Actions → Trinket / Guild spell | Carried trinkets/scrolls are consumed where present; Speedy Recovery marks settlement healing at 2 Life/day; Look Tough is consumed on the next Streetwise roll; Wizard's Luck modifies Gambling House resolution; Temporary Weapon, Troupe Switch, and Silence use optional target fields and target-specific markers |
| TAG.13 | Finance and bank ledgers | TAG pp.9-16, p.53 | TAG Actions → Finance; `/modern/banking` | Bank deposit charges 10% unless active Guild ledger applies; withdrawal restores gp; inheritance note records heir; inheritance transfer applies 20% tax; robbery risk marks the selected TAG bank account robbed; 3-Clue bank robbery recovery clears the robbed flag and creates/selects the Bandit Hideout lead; loan enforcement and Guild finance actions write TAG log entries |
| TAG.14 | Guild management surface | TAG pp.54, 61-68 | `/modern/guild`; TAG Actions → Guild spell | Guild membership/coffers are separate from troupe membership; benefits require membership plus coffers above 0 gp; leaving is blocked below 5000 gp coffers; Guild page exposes upkeep, 50% loot share, resurrection funding, availability reroll/reset, Guild Job lead creation, member ledger summaries, closeout tasks, and recent Guild log entries |
| TAG.15 | Contextual generated-adventure prompts | TAG scene pages | Start a newly generated TAG module, then inspect the current room detail panel, Current Objective banner, Ongoing Quest card, and TAG Actions dialog during exploration | A **TAG scene prompt** appears for generated TAG rooms. Lead entry, side clue, complication, final scene, and unlocked-scene rooms read `source.parameters.tag_reference.room_prompts` and show shortcut buttons with hover hints. The generated TAG **Director** names the current phase, links to Rules Reference/Tables, and explains what kind of decision matters now. The Current Objective banner summarizes the current prompt, offers the first relevant action, and shows Entry/Side lead/Complication/Finale/Route/Reward/XP/Closeout lifecycle chips. TAG Actions shows a **Relevant Now** shortcut panel above collapsible Advanced TAG controls with a recommended action, explanation, and focused current action family first. Generated TAG Ongoing Quest cards show a five-step closeout wizard for objective, route/reward, XP, Guild/banking/guidance, and signoff. Older modules can use Repair guidance to rebuild generic app prompt metadata and normalize legacy log wording. Buttons prefill the matching branch/route/reward/XP reference; known profile Clue gates such as Dragon's Lair, Shaura, Daroc's familiar, and Fiendish Abyss prefill the 2-Clue cost. The player still checks the PDF and confirms the exact amount/result before applying it |
| TAG.15a | Rumor playthrough audit panels | TAG pp.22-31 | Generate one or more Rumor Scene leads, open `/modern/go-adventure`, then start/resume a generated Rumor module | Go Adventure shows **TAG Rumor Leads** and **Rumor Signoff Checklist**. Rumor rows expose scene/page metadata, Select Rumor, Rules, and Table actions. Exploration TAG prompts show a room checklist beside action buttons. The prose is app-authored guidance only; exact scene text/rewards remain with the PDF/player signoff |
| TAG.15b | Treasure Map playthrough audit panels | TAG pp.32-33 | Generate one or more Treasure Map destination leads, open `/modern/go-adventure`, then start/resume a generated Treasure Map module or Lady in White Treasure Map quest | Go Adventure shows **TAG Treasure Map Leads** and **Treasure Map Signoff Checklist**. Map rows expose destination metadata, Select Map, Rules, and Table actions. Exploration TAG prompts show destination checklist reminders for follow-map result, destination procedure, treasure transfer, XP, Guild share, banking/storage, and closeout. Active Lady in White Treasure Map quest cards show a destination procedure tracker with action explanations, completed-state marking, stored room targets, and signoff. The Current Objective banner should point to Claim Treasure for ordinary room hoards, the relevant Map Leads To action for destination work, Sign off destination after PDF/player confirmation, and Claim Quest Reward once ready. The prose is app-authored guidance only; exact map table text/rewards remain with the PDF/player signoff |
| TAG.15c | Thematic Dungeon playthrough audit panels | TAG pp.38-48 | Generate one or more Thematic Dungeon leads, open `/modern/go-adventure`, then start/resume a generated Thematic Dungeon module | Go Adventure shows **TAG Thematic Dungeon Leads** and **Thematic Dungeon Signoff Checklist**. Theme rows expose target/procedure metadata, Select Theme, Rules, and Table actions. Exploration TAG prompts show theme checklist reminders for cave-ins, undead replacement, boulder throw, dragon reveal, prisoner table, maze checks, stolen goods, capture-alive choices, reward, XP, Guild share, banking/storage, and closeout. The prose is app-authored guidance only; exact theme text/rewards remain with the PDF/player signoff |
| TAG.16 | Priority module profile notes | TAG pp.39-40, 48, 55, Scene 16 | Generate Dragon's Lair, Bandit Hideout, Shaura, or Gorungar; inspect the room prompt panel | Prompt panel shows module-profile target/procedure/check lines: Dragon's Lair four rooms and dragon reveal; Bandit Hideout HCL+3 rooms, stolen-goods checks, and chieftain capture; Shaura ten-room cult dungeon and 2-Clue gate; Gorungar single job encounter with 2d6 archers note. Bandit Hideout complication rooms expose **Roll stolen goods** with a hover hint; it rolls the 1-in-6 goods check, 8d6 gp value, and trapdoor chance but does not auto-claim the treasure. Final-room buttons prefill exact supported reward actions where implemented |
| TAG.17 | Remaining generated-profile notes | TAG pp.41-47, 55-59 | Generate Ghastly Mine, Giant's Lair, Fiendish Abyss, Minotaur Maze, Clean Up My Castle, Griffin, Portrait, Sewers, or Monoceros; inspect the prompt panel | Module-profile notes show target room counts and procedure/signoff checks: cave-ins and undead replacement, hill giant final room, abyss prisoner table, maze lost/search rules, castle single-session payment, griffin egg handling, portrait escort/persuasion, sewer clue spend/disease, and monoceros hunt/capture. Ghastly Mine buttons roll minion/major undead replacement, gp treasure conversion, and cave-in severity; Fiendish Abyss final prompt rolls the Prisoner Table; Minotaur Maze buttons roll lost checks, wandering subtype, Special Event Table, and can prefill a shortcut route marker. Clean Up My Castle tallies pay; Griffin buttons roll mountain checks, nest search, eggs, and egg breaks; Portrait buttons roll outbound checks, L6 persuasion, and painting snatch; Sewers buttons roll vermin/minions/disease; Monoceros buttons roll tracking, 3-Clue encounter risk, and thick-hide checks. Supported Clue/capture shortcuts prefill TAG Actions where available |

**Current boundary:** TAG-specific foe names are now spawnable from `tag_monsters.json`, separate from the locked EE bestiary. Major printed rewards, route decisions, XP markers, bank ledgers, route rewrites, Dragon's Lair type reveal module updates, Bandit Hideout stolen-goods room checks, Ghastly Mine/Fiendish Abyss/Minotaur Maze procedure rolls, Guild Job procedure rolls, Look Tough, Speedy Recovery, Wizard's Luck, target-specific Guild spell markers, and contextual generated-adventure prompts have UI actions. Remaining TAG work is broader playtest signoff.

**Pass/Fail notes:**

---

## §1 Exploration harness

Validate the shell before table-specific rows.

| # | Mechanic | PDF | How to trigger | Check |
|---|----------|-----|----------------|-------|
| 1.1 | Enter new room | p.25+ | Move through open exit | Log names tile; map updates; `current_tile_id` changes |
| 1.2 | Closed door | p.109 | Exit shows closed door | Open / Bash / Lock-pick / Spellcast / Spend clues options |
| 1.3 | Iron / sealed / illusion / lever | p.109–110 | Roll door on closed exit | Correct restrictions (no bash on iron, etc.) |
| 1.4 | Search once per tile | p.107 | Search on current tile | d6 shown; corridor −1; second search blocked |
| 1.5 | Search reward choice | p.107–108 | Search 5–6 | Pick treasure / secret door / passage / clue |
| 1.6 | Wandering on backtrack | p.107 | Leave tile and return | 1-in-6 roll logged when applicable |
| 1.7 | Trap on tile | p.164–166 | Enter trap room or special event trap | Resolve Trap; marching-order targets; caverns swinging log shows full EE text in log |
| 1.7a | Caverns hidden pit | p.165 | Hidden pit fails lead Save | Trapped status; **Find Secret Passage (1 Clue)** only when fallen; destinations **Dungeon** or **Fungal Grottoes** only |
| 1.7b | Caverns toxic mushrooms | p.165 | Roll toxic mushrooms | Mushroom-class heroes immune; ranger/druid/outdoor forester +L on lead save; −1 Saves 6 rooms |
| 1.8 | Claim treasure | p.157 | Treasure room, foes cleared | Gold/items distributed; carry limit excess logged |
| 1.9 | Rest once/adventure | p.114 | Cleared room + adjacent clear | Nail doors, Life/ability recovery, 1-in-6 wander |
| 1.10 | Camp / return | p.25 | Exit dungeon, camp | Roster sync; bank/shop/regroup available |
| 1.11 | Secret passage | p.112–113, p.165 | Search passage, hidden pit (1 Clue when trapped), fungal roll 5, or tile roll 9 (2 Clues) | Player chooses destination environment (not the one they are leaving); hidden-pit clue limited to dungeon/fungal |
| 1.11a | Secret passage placement | p.112–113 | After choosing destination | New map element appears in destination color; labeled secret-passage exit on source tile; party moves onto new tile; source tile keeps its original environment tint |
| 1.11b | Secret passage repair | — | Reload a save broken by the old bug (env switched, one tile, no passage exit) | Session auto-repairs on load: second tile placed, party on destination, entrance stays dungeon-colored |
| 1.12 | Secret passage → fungal | p.112–113 | As above | Fungal grottoes tables used on fungal-tinted tiles |
| 1.13 | Split / scout (optional) | p.105 | Detach, scout ahead, Navigate | Scoped actions use heroes on current tile only |

**Pass/Fail notes:**

---

## §2 Tile Content Table (`room_content_table`, p.152)

Triggered when a **new** map element is generated and features are seeded (`_seed_tile_features`). Check **room vs corridor** column.

| Roll | Key | Room behavior | Corridor behavior | Check in UI/log |
|------|-----|---------------|-------------------|-----------------|
| 2 | treasure | Treasure present | Same | Treasure marker; claim after clear |
| 3 | trap_treasure | Trap + treasure | Same | Both objects; trap before claim |
| 4 | special_event | Special event | searchable only | Room: event fires on entry; corridor: searchable |
| 5 | special_feature | Special feature (env table) / fungal secret passage | empty | Room: dungeon or caverns feature; fungal: secret passage choice then new caverns/dungeon tile; corridor empty |
| 6 | vermin | Vermin spawn | Same | Environment vermin table |
| 7 | minions | Minions spawn | Same | Environment minions table |
| 8 | minions (room) | Minions | empty | Corridor empty; room minions |
| 9 | searchable + secret passage | Empty/searchable; 2-Clue passage option | Same | Choice panel: searchable or spend 2 Clues |
| 10 | weird (room) | Weird monsters | searchable only | Room: environment weird table |
| 11 | boss | Boss spawn | Same | Major foe; Final Boss check if applicable |
| 12 | lair (dragon) | Boss + dragon tag | empty corridor | Lair object; dragon-tagged boss |

**Pass/Fail notes:**

---

## §3a Caverns Special Features (`caverns_special_features_table`, p.112)

Enter a **caverns** room whose tile content rolled **5** (special feature).

| Roll | Key | PDF effect | Check |
|------|-----|------------|-------|
| 1 | stalactites | 3-in-6 fall after explosive two-handed hit | Combat log; PC Defense or foe damage |
| 2 | stalagmites | PCs cannot explode Attack rolls | Attack rolls do not chain |
| 3 | boulders | +1 Defense vs ranged; −1 ranged Attack; +1 Stealth; foes surprise 2-in-6 | Modifiers in combat/scout logs |
| 4 | echo | −1 Stealth; 2-in-6 wandering/backtrack; spell echo on d6 6 | Rest/backtrack; free repeat cast |
| 5–6 | water_pools | Dip → Water Pool Table | Dip buttons; contaminated / heal once |

**Pass/Fail notes:**

---

## §3 Dungeon Special Features (`dungeon_special_features_table`, p.153)

Enter a room whose content rolled **special_feature** (tile content roll 5).

| Roll | Key | PDF effect | How to trigger | Check |
|------|-----|------------|----------------|-------|
| 1 | fountain | +1 Life once/adventure per PC | Resolve feature | Once only; living PCs |
| 2 | blessed_temple | +1 Attack vs undead/demons until one slain | Resolve feature | Buff persists; clears after kill |
| 3 | armory | Change weapons within class limits | Resolve feature | Weapon swap UI; class restrictions |
| 4 | cursed_altar | Random PC −1 Defense | Resolve feature | Curse on one hero; shown on sheet |
| 5 | statue | Touch or leave; d6 outcome | Map marker → touch/leave | Living statue fight OR gold break |
| 6 | puzzle_box | Save vs L or 1 damage per fail | Map marker → attempt/leave | Failed attempt keeps pending |

**Pass/Fail notes:**

---

## §4 Dungeon Special Events (`dungeon_special_events_table`, p.154)

Enter a room whose content rolled **special_event** (tile content roll 4).

| Roll | Key | PDF effect | Check |
|------|-----|------------|-------|
| 1 | ghost | Pass through; saves/immunity | Per-hero log: immunity, save, fail, Life loss |
| 2 | wandering_monsters | Wandering attack | Foes spawn; event remembered on tile |
| 3 | lady_in_white | Quest offer | Accept/refuse; Ongoing Quests panel |
| 4 | trap | Roll trap table | Trap resolves; Resolve Trap UI |
| 5 | healer | 10gp/Life | Buy healing; once per adventure substitution if repeat |
| 6 | alchemist | Potions/poison shop | Buy; repeat → trap substitution logged |

**Pass/Fail notes:**

---

## §5 Caverns Special Events (`caverns_special_events_table`, p.155)

Reach **caverns** environment (secret passage from search or tile content).

| Roll | Key | PDF effect | Check |
|------|-----|------------|-------|
| 1 | trap | Caverns trap table | Correct trap table routing |
| 2 | cavemen_explorers | Feed 2 rations or fight | Feed/fight choice; HCL+3 minions |
| 3 | morlock_spy | 5gp → no surprise by morlocks | Warning flag; wandering surprise rules |
| 4 | cave_goblin_scout | 10gp → no surprise, +1 Saves | Warning until exit caverns |
| 5 | dwarf_miner | Gem buy/sell; preview next tile | Trade + preview log |
| 6 | dwarf_party_gem | Dwarf only: gem + 1-in-6 wander risk | Ignored without dwarf |

**Pass/Fail notes:**

---

## §6 Fungal Grottoes Special Events (`fungal_grottoes_special_events_table`, p.156)

Reach **fungal_grottoes** environment.

| Roll | Key | PDF effect | Check |
|------|-----|------------|-------|
| 1 | trap_rare_item | Trap then rare item table | Both resolve in order |
| 2 | fungal_cavemen | Feed rations/mushroom or fight | Fed: secret-passage exit + new caverns tile; party moves there; fungal event tile stays green |
| 3 | spore_cloud | Save vs poison or −2 Life | Monk immune; halfling/barbarian +L |
| 4 | halfling_scout | 10gp → no surprise, +1 Saves | Until exit fungal grottoes |
| 5 | fungal_merchant | Shop +20% buy; sell gems/mushrooms | Repeat roll → treat as 4 (scout) |
| 6 | mycelial_warning | Mushroom monk: ignore next trap/wander | Requires monk in party |

**Known gap to verify:** Halfling Mushroom Pickers **trade** reaction — stock, buy, and Done Trading are wired; spot-check prices and halfling discount.

**Pass/Fail notes:**

---

## §7 Reactions

PDF: category tables p.95–96; named tables in bestiary; Capture p.102.

### 7a Category fallback (any mixed/unknown group)

| Table | Roll | Expected | Check |
|-------|------|----------|-------|
| vermin_reaction_table | 1–6 each | fight/flee/parley/bribe per row | Check Reactions before round 1 |
| minion_reaction_table | 1 = capture | Non-lethal; foes strike first | Capture flow if hero to 0 Life |
| major_reaction_table | 1–6 each | Per row | Morale interaction after |

### 7b Special reaction keys (when rolled)

| Key | Trigger | Success | Failure |
|-----|---------|---------|---------|
| puzzle | Named foe table | Peaceful | Fight, foes first |
| magic_challenge | Named foe table | Peaceful | Fight + magical save reroll |
| trade_information | Named foe table | Sell clues / buy clue | Gold/clue counts |
| capture | Minion roll 1 | Capture not kill | Hideout/ransom if applicable |
| bribe | Per table | Pay gold/weapons | Decline → fight |
| bribe_magic_item | Wraith (normalize) | Give magic item | Miser / no item |
| bribe_food / bribe_food_per_foe | Named table | Accept (food) | Insufficient rations |
| bribe_gold_or_food | Morlocks | 5 food or 15gp buttons | Decline → fight |
| bribe_ration_gold_or_mushroom | Rat Men | Food / mushroom / gold | Decline → fight |
| bribe_food_or_gem / bribe_gem | Cavemen / Cave Dragon | Food or per-gem give | Decline → fight |
| bribe_scrolls_or_potions | Manataur | Give 2 scrolls/potions | Decline → fight |
| bribe_gem_or_two_handed_weapon | Caveman Champion | Gem or heavy weapon | Decline → fight |
| bribe_treasure_or_magic_item | Young Dragon | Magic item or all gold (100gp min) | Decline → fight |
| buy_weapons | Cave Orcs | Sell eligible weapon | Dwarves/elves block |
| trade | Halfling Pickers | Buy stock, Done Trading | Refuse → fight |
| sleep | Young Dragon | +N first attack (data field) | N/A (combat follows) |
| blood_offering / quest / trial* | Per table | Per key | Decline → fight |

\*Trial / Challenge of Champions use the champion duel flow.

### 7c Named tables worth spot-checking

| Foe / table | Why |
|-------------|-----|
| Kobolds | Puzzle / trade / magic challenge rows |
| Cultists | Same |
| Necromancers | Same |
| Halfling Mushroom Pickers | Trade stock + buy UI |
| Any fiendish foe | New 2026-06-16 specials (web, blood drain, etc.) |

### 7d Reaction procedure

| # | Check |
|---|-------|
| 7d.1 | Surprise skips or favors party per rules |
| 7d.2 | Attack immediately forfeits Check Reactions |
| 7d.3 | Pay Bribe spends correct gold/weapons from present heroes |
| 7d.4 | Split party: only present heroes count for trade/bribe |
| 7d.5 | Scout failed-stealth uses scout-local reaction path (incl. special bribes) |
| 7d.6 | Fight-to-the-death: foes first strike; no morale flee |
| 7d.7 | 2+ dwarves: Miser blocks Pay Bribe and special bribes |

**Pass/Fail notes:**

---

## §8 Saves

Cross-cutting — validate during traps, events, doors, combat.

| Situation | PDF | How to trigger | Check |
|-----------|-----|----------------|-------|
| Trap save | p.164–166 | Resolve trap | Target (marching order / random / all) |
| Poison (foe) | p.97 | Poisonous foe hit | Lingering poison; class resistance |
| Poison (spore cloud) | p.156 | Fungal event | Monk immune; halfling/barbarian +L |
| Ghost | p.154 | Dungeon ghost event | Per-hero immunity/save |
| Door (locked) | p.109 | Rogue/warrior/barbarian | Class gate on lock-pick/bash |
| Encumbrance | p.16 | Over carry limit | −1 Defense/Saves on doors |
| Puzzle box | p.153 | Special feature | Save vs L; damage on fail |
| Magic challenge | p.102 | Reaction | Save vs highest foe L |
| Puzzle reaction | p.102 | Reaction | Save vs L |
| Stable Mind | mushroom | Fungal madness | Expert skill blocks madness |
| Class climbing/tracking/swimming | class text | Ranger +L on listed saves | When those saves occur |

**Pass/Fail notes:**

---

## §9 Equipment

| # | Area | How to trigger | Check |
|---|------|----------------|-------|
| 9.1 | Home shop buy | Camp or home | Class restrictions; quantity buys |
| 9.2 | Home shop sell | Sell loot | Half list; magic fixed resale |
| 9.3 | Camp shop | Camped outside | Carried + banked gold |
| 9.4 | Carry limit 200gp | Claim treasure | Excess logged; redistribution |
| 9.5 | Encumbrance | Extra gear beyond starting | −1 Defense/Saves |
| 9.6 | Default weapons | Set on roster/sheet | Used in combat |
| 9.7 | Combat weapon swap | Combat round | 1 turn cost |
| 9.8 | Transfer items | Party sheet / camp | Roster sync; blocked in combat |
| 9.9 | Armory feature | Special feature roll 3 | In-class weapon change |
| 9.10 | Fungal merchant +20% | Fungal event roll 5 | Prices rounded up |
| 9.11 | Blade poison / acid / oil / holy water | Party sheet consumables | Correct combat effect |
| 9.12 | Wolfsbane / berserker mushroom | Shop buy + party sheet | Throw vs lycanthrope; eat mushroom → rage next combat |
| 9.13 | Torch / rope / pit | Hidden pit trap + party sheet | Spend torch unblocks flee; rope or ally climbs out |
| 9.14 | Map fragment / wand / paint | Caverns / Fiendish treasure | Preview next tile once; wand charges on wizard cast; paint choices |
| 9.12 | Big Money Buyer secret | After adventure sell | Triple one gem/jewel |

**Pass/Fail notes:**

---

## §10 Secrets (`secrets_table`, p.123–124 + p.102 captive)

Earn clues via Search 5–6 → Clue choice, or Trade Information buy.

| Key | Timing (PDF) | How to test | Check |
|-----|--------------|-------------|-------|
| weakness_of_a_foe | Meet major foe | Use Secret on foe | +2 Attack this combat |
| deal_with_a_foe | Meet foe | Use Secret | Peaceful pass; no XP/treasure |
| hidden_treasure_location | Empty non-entrance room | Reveal (3 clues) | 3d6×10gp |
| magic_item_location | Enter non-entrance room | Reveal | Magic treasure on tile |
| scroll_location | Non-entrance room | Reveal | Scroll in inventory or treasure |
| true_name_spiritual_entity | When used | Use Secret | Angel heal/rescue or demon kill |
| new_spell | Spellcaster | Reveal | Temp spell + slot |
| magical_power_increase | Cleric/caster | Reveal | Permanent extra use |
| potion_recipe | 2 major foes + 50gp | Reveal | Shop 50gp potion unlock |
| terrifying_secret | Morale test | Use Secret | Next vermin/minion morale fails |
| big_money_buyer | Sell valuable item | Use Secret | Triple one sale |
| enemy_in_dungeon | Meet major foe | Use Secret | Swap to chaos lord |
| prisoner | Minions/boss room | Use Secret | NPC rescue reward |
| dragonslayer_bloodline | Barb/dwarf | Reveal | +1 vs dragons persistent |
| secret_diet | Camp outside | Use Secret | +1 Life for adventure |
| someone_imprisoned | Hero captive | 3 clues / Find Hideout | Hideout tile; Reaction roll at arrival; bribe → Level×10 gp ransom; else combat rescue |

Also check: **Reveal Secret** picker vs **Find Hideout** for captive; clue spend from correct holder; secret shown on home + party sheet.

**Pass/Fail notes:**

---

## §11 Character classes (all 20)

Catalog data is signature-locked — validate **play behavior** and **unique mechanics**.

| Class | Starting check | Unique mechanic to validate |
|-------|----------------|----------------------------|
| warrior | Life 7, 3d6×10gp | Bash doors; weapon restrictions |
| cleric | Life 5 | Healing prayer d6+L; Turn Undead |
| rogue | Life 4 | Lock-pick; stealth (if used) |
| wizard | Life 3 | Spells once/adventure; scroll copy |
| barbarian | Life 8 | Rage; no scrolls; poison resist |
| ranger | Life 7 | +L attack; outdoor bow (if outdoor added) |
| dwarf | Life 6 | Miser/no bribe; climbing save +L |
| elf | Life 5 | Spells; missile |
| halfling | Life 4 | Luck rerolls; Nourishing Meal |
| druid | Life 4 | Companion; Call of the Wild L10+ |
| illusionist | Life 3 | Illusion spells; mirror image |
| acrobat | Life 4 | Combat acrobatics (expert) if L5+ |
| assassin | Life 4 | Stealth; backstab if wired |
| bulwark | Life 8 | Shield/defense tricks |
| gnome | Life 5 | Lever doors / gadgets |
| kukla | Life 6 | Rings/compartment |
| light_gladiator | Life 6 | Arena-style combat |
| mushroom_monk | Life 5 | Spore immunity; fungal interactions |
| paladin | Life 7 | Prayer heal/reroll save |
| swashbuckler | Life 5 | Panache; six optional traits wired (combat abilities + sheet buttons) |

For each class: create hero → run one combat → one exploration action → check sheet shows correct Life/gear/spells.

**Pass/Fail notes:**

---

## Session log template

Copy per session:

```
Date:
Adventure id:
Environment: dungeon / caverns / fungal_grottoes
XP mode:

Tile entered:
Content roll (if seen):
Event/Feature key:
PDF page:
Log lines:
UI actions available:
Expected (PDF):
Actual:
Pass/Fail:
Notes:
```

---

## §12 AI Adventure (imported modules)

Use after hard-refresh (`app.js` v0.68.43+). Hover any AI Adventure control for hints.

| Step | Where | Pass criteria |
|------|-------|---------------|
| 12.1 | Adventure → **Crypt of Whispers (imported)** | Starts session; fog of war on unvisited tiles |
| 12.2 | Explore + fights | `on_enter` triggers spawn foes from manifest |
| 12.2b | After combat | Log repeats room title/description + treasure hint at end of fight |
| 12.2c | Slim Text Commands palette | Toggle **Text Commands**, press `?` for examples, run `look`, `go north 1`, `open west 1`, `search`, `claim`, then press `Escape` to close |
| 12.3 | Quest + exit | Boss objective completes; dungeon exit on exit room finishes adventure |
| 12.4 | AI Adventure panel | Generate + Copy prompt; Validate pasted JSON; Import installs module |
| 12.5 | Party sheets | All four heroes render during exploration; no "Could not render party sheets" after search/move |

**Pass/Fail notes:**

---

## §12b Forsaken Depths Heroic Spells

Use a Forsaken Depths session with a Heroic-trained caster or a Heroic spell scroll. Hover spell buttons/tags to confirm the rule hint before casting.

| Step | Where | Pass criteria |
|------|-------|---------------|
| 12b.1 | Party sheet / combat spell button → **Fire of Truth** | Hover text says living foes only, +1 on the spell roll vs chaos creatures, Clue insight on a kill, and natural 1 wandering-monster risk |
| 12b.2 | Cast **Fire of Truth** at a chaos living foe | Verbose spell roll includes the +1 chaos bonus; miss/hit log names Fire of Truth, not generic Fireball |
| 12b.3 | Kill the target with **Fire of Truth** | Insight roll can grant 1 Clue; natural 1 schedules a wandering-monster check |
| 12b.4 | Cast **Teleport Enemy** in a mapped/visited area | Target leaves the fight, a returning-foe log is created, and later movement/combat turns tick it back one room/hex/area at a time |
| 12b.5 | Block Teleport Enemy's return route | Log says the foe cannot return because an obstacle blocks the route |
| 12b.6 | Teleport Enemy return crosses a room with living occupants | Log includes the occupied-room d6 reaction roll, table source, outcome, and whether the occupants engage or do not block the return |
| 12b.7 | Party sheet → **Mass Blessing** | UI shows living heroes/hirelings plus Blessing-removable condition checkboxes with hover hints |
| 12b.8 | Cast **Mass Blessing** with one hireling condition selected | Caster Life cost equals selected targets beyond the first + selected conditions; selected hireling status is removed and non-selected statuses remain |

---

## §12c TAG Settlement Apothecary

Use a TAG banking/settlement-mode session with a living Wandering Alchemist carrying mortar and pestle. This is a settlement/town downtime surface, not the Camp Outside Dungeon panel.

| Step | Where | Pass criteria |
|------|-------|---------------|
| 12c.1 | Side panel → **TAG Settlement Apothecary** | Panel appears separately from **Camp Outside Dungeon** when TAG banking is enabled and an eligible brewer is present |
| 12c.2 | Hover recipe buttons | Tooltip describes TAG settlement downtime brew, difficulty, materials, and TCOTFD ingredient requirement |

## §12d TAG Troupe, Storage, Maps, and Streetwise

Use the home Adventure setup TAG settlement panel.

| Check | Action | Expected |
| --- | --- | --- |
| 12d.1 | Save troupe name, active party, guild membership, and guild gp | Campaign reload preserves the troupe state |
| 12d.2 | Store gp in Bank | Character pays stored gp plus 10% rounded-up fee; campaign storage gp increases |
| 12d.3 | Withdraw stored gp | Character receives gp; campaign storage gp decreases |
| 12d.4 | Buy a fixed TAG item/service | Character gold decreases and inventory/status/campaign PP updates as appropriate |
| 12d.5 | Create and summon magic locker | Size 0+ settlement allows setup; summon rolls 3d6 and logs success/mishap |
| 12d.6 | Roll Gambling House | Stake is spent and gp outcome is applied/logged |
| 12d.7 | Roll Streetwise actions | Look for Clue, Listen to Rumors, Interrogate, and Look Tough log the correct TAG result class |
| 12d.8 | Follow treasure map | Following the Treasure Map result logs; Real Deal also logs Map Leads To summary |
| 12d.9 | Create adventure from Rumor Scene, Treasure Map, Thematic Dungeon, and Guild Job | Each creates a removable installed module in the normal Adventure section/dropdown and selects it |
| 12d.10 | Start a generated TAG adventure | Normal imported-adventure flow starts, quest objective is visible, and completion returns through normal adventure closeout |
| 12c.3 | Brew with missing ingredients | Log blocks the brew with missing ingredient/material message |
| 12c.4 | Brew with valid ingredients/materials | Ingredients/gp are consumed, d6+L rolls when required, and the brewed `(Apothecary` item is added to the brewer inventory |

**Pass/Fail notes:**

---

## §13 Map Element Editor / Inset Exits

Use after hard-refreshing the editor (`tile-editor.js` v0.40.2+).

| Step | Where | Pass criteria |
|------|-------|---------------|
| 13.0 | Map Element Editor → **Walk/Block** | Left click cycles blocked → edge halves → walkable; right click reverses |
| 13.0b | Map Element Editor → **Half** / **Curve** / **Half Curve** | Left/right click steps forward/back through mask cycles (see `docs/MAP_ELEMENT_EDITOR.md`) |
| 13.0c | Forsaken Depths Rivers → **Water**, then any shape tool | Water remains selected as a surface mode; Walk/Block, Half, Slope, Long Slope, Curve, and Half Curve paint blue water geometry; clicking Water again restores floor painting |
| 13.0d | Save and reload a river tile containing partial water shapes | Full and partial water cells retain their shape and water surface after reload |
| 13.1 | Map Element Editor → **Exits** help | Help explains that inset exits keep their authored square and one blocked padding square may be overlapped by the connected tile |
| 13.2 | Map Element Editor → Door/Passage tool | Placing a door/passage creates a numbered marker and row with hover text |
| 13.3 | Map Element Editor → **Delete Exit** tool | Selecting Delete Exit and clicking the marker removes the marker and row |
| 13.4 | Map Element Editor → Exits row | Row **Remove** deletes a mistaken door/passage marker |
| 13.5 | Gameplay map placement | An inset west/east/north/south exit remains at its authored square; the adjacent tile overlaps/truncates blocked padding instead of shifting the door |
| 13.6 | Any catalog → Door/Passage → click near a cell corner | Marker is authored as NE, SE, SW, or NW and the exit row shows the matching selected direction |
| 13.7 | Save/reload a diagonal exit, then explore through it in gameplay | Direction, span, and marker angle persist; the connected tile is placed diagonally with the reciprocal compass exit |
| 13.8 | River 23 or another inset opening → place exit on one blocked padding square | Validation passes when the immediately opposite interior square is water/walkable; gameplay places the connected tile over the blocked padding |
| 13.9 | Forsaken Depths Rivers → room codes | ETC is available and saves as Entrance to Citadel; NC and ETR remain dungeon-only |

**Pass/Fail notes:**

---

## Quick pytest references (expected behavior)

| Area | Test file |
|------|-----------|
| Tile content / search | `tests/test_exploration.py` |
| Special events | `tests/test_environment_special_events.py` |
| Reactions / capture | `tests/test_reactions.py`, `tests/test_special_bribe_reactions.py`, `tests/test_capture.py` |
| Doors / traps | `tests/test_doors.py`, `tests/test_exploration.py` |
| Secrets | `tests/test_economy.py`, `tests/test_capture.py` |
| Classes catalog | `tests/test_class_profiles_audit.py` |
| AI Adventure | `tests/test_adventure_import_play.py`, `tests/test_frontend_map_interactions.py` |
| Map editor / placement | `tests/test_tile_editor_ui.py`, `tests/test_truncation.py` |
| Equipment | `tests/test_equipment_shop.py`, `tests/test_carry_limits.py`, `tests/test_special_items.py`, `tests/test_special_items_wiring.py`, `tests/test_equipment_batch.py` |
| PDF row text | `tests/test_pdf_table_compliance.py` |

---

## Archived EE Secrets Signoff (validated 2026-06-17)

---

## Item 1 worksheet — Secrets sign-off (validated 2026-06-17)

Audit against EE PDF pp.123–124 (PDF pages 128–129) and p.102 (Someone Has Been Imprisoned). Engine: `secrets.py`, `random_dungeon.py`. Tests: `test_secrets_text_compliance.py`, `test_secrets_flow.py`, `test_capture.py`, `test_economy.py`.

| # | Secret | PDF p. | Status | Notes |
| --- | --- | --- | --- | --- |
| 1 | Weakness of a Foe | 123 | **validated** | +2 party Attack vs chosen Major Foe for whole combat |
| 2 | Deal with a Foe | 123 | **validated** | Peaceful pass; persists on tile; no vermin/Final Boss |
| 3 | Location of a Hidden Treasure | 123 | **validated** | Empty non-entrance room; 3d6×10gp |
| 4 | Location of a Magic Item | 123 | **validated** | Non-entrance room; environment magic table |
| 5 | True Name of a Spiritual Entity | 123 | **validated** | Angel/demon locked on first use; heal one PC or trap rescue; demon 4 Life to Major or slay up to 6 minions |
| 6 | New Spell | 123 | **validated** | Spellcaster; temp slot + chosen spell |
| 7 | Increase of Magical/Spiritual Power | 123 | **validated** | +1 permanent use of specific spell/prayer (stack on different spells) |
| 8 | Location of a Scroll | 123 | **validated** | Basic scroll to inventory or room treasure |
| 9 | Recipe for a Potion | 123 | **validated** | ≥2 Major Foes this adventure + 50gp; counter resets per session |
| 10 | Terrifying Secret | 124 | **validated** | Next eligible morale fails; not Final Boss |
| 11 | Someone Will Pay Big Money for That | 124 | **validated** | Triple resale on jewelry/gem out of dungeon |
| 12 | Your Enemy Is in the Dungeon | 124 | **validated** | Swap Major Foe → Chaos Lord; +1 Attack |
| 13 | The Prisoner | 124 | **validated** | Auto-discover in minion/boss rooms; Attack vs L4 chain break (retries during combat or after guards dead); escort to exit; magic+treasure OR double held gp |
| 14 | Bloodline of Dragon-Slayers | 124 | **validated** | Barbarian/dwarf only; +1 Attack/Defense vs dragons |
| 15 | Secret Diet | 124 | **validated** | 100gp at camp (50gp halfling); +1 Life this adventure |
| 16 | Someone Has Been Imprisoned | 102 | **validated** | 3 Clues → hideout; fresh Reaction roll at hideout; bribe reaction → Level×10 gp ransom; otherwise combat rescue |

**Cross-cutting checks (item 1):**

- [x] Discoverer gains 1 XP on reveal (all XP systems except Slow and Sure)
- [x] Clues held per character; spend drains holder first
- [x] Fallen hero clue/secret reassignment before play continues
- [x] Row text in `secrets_table` matches PDF (`test_secrets_text_compliance.py`)
- [x] Regression-map `secrets` family → `implemented`

---

## Progress log

| Date | Item | Notes |
| --- | --- | --- |
| 2026-06-17 | Plan created | Checklist built; start at **item 1** (Secrets sign-off). |
| 2026-06-17 | Item 1 started | Worksheet added; partial implementations identified. |
| 2026-06-17 | Item 1 validated | All 16 secrets signed off; hideout Reaction roll + ransom/combat rescue wired; True Name and Prisoner finalized. |
