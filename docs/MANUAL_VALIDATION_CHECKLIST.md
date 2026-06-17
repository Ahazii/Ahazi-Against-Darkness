# Manual Validation Checklist

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
| 1.7 | Trap on tile | p.164 | Enter trap room or special event trap | Resolve Trap; marching-order targets |
| 1.8 | Claim treasure | p.157 | Treasure room, foes cleared | Gold/items distributed; carry limit excess logged |
| 1.9 | Rest once/adventure | p.114 | Cleared room + adjacent clear | Nail doors, Life/ability recovery, 1-in-6 wander |
| 1.10 | Camp / return | p.25 | Exit dungeon, camp | Roster sync; bank/shop/regroup available |
| 1.11 | Secret passage | p.112–113 | Search passage, hidden pit, fungal roll 5, or tile roll 9 (2 Clues) | Player chooses destination environment; map tiles tint by environment |
| 1.12 | Secret passage → fungal | p.112–113 | As above | Fungal grottoes tables used |
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
| 5 | special_feature | Special feature (env table) / fungal secret passage | empty | Room: dungeon or caverns feature; fungal: secret passage; corridor empty |
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
| 2 | fungal_cavemen | Feed rations/mushroom or fight | Secret passage to caves if fed |
| 3 | spore_cloud | Save vs poison or −2 Life | Monk immune; halfling/barbarian +L |
| 4 | halfling_scout | 10gp → no surprise, +1 Saves | Until exit fungal grottoes |
| 5 | fungal_merchant | Shop +20% buy; sell gems/mushrooms | Repeat roll → treat as 4 (scout) |
| 6 | mycelial_warning | Mushroom monk: ignore next trap/wander | Requires monk in party |

**Known gap to verify:** Halfling Mushroom Pickers **trade** reaction (not this table, but fungal) — accepting may still start combat without full trade stock.

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

### 7c Named tables worth spot-checking

| Foe / table | Why |
|-------------|-----|
| Kobolds | Puzzle / trade / magic challenge rows |
| Cultists | Same |
| Necromancers | Same |
| Halfling Mushroom Pickers | **Trade row — known partial** |
| Any fiendish foe | New 2026-06-16 specials (web, blood drain, etc.) |

### 7d Reaction procedure

| # | Check |
|---|-------|
| 7d.1 | Surprise skips or favors party per rules |
| 7d.2 | Attack immediately forfeits Check Reactions |
| 7d.3 | Pay Bribe spends correct gold/weapons from present heroes |
| 7d.4 | Split party: only present heroes count for trade/bribe |
| 7d.5 | Scout failed-stealth uses scout-local reaction path |
| 7d.6 | Fight-to-the-death: foes first strike; no morale flee |

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
| someone_imprisoned | Hero captive | 3 clues / Find Hideout | Hideout tile; ransom/rescue |

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
| swashbuckler | Life 5 | Panache; **trait buttons still partial** |

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

## Quick pytest references (expected behavior)

| Area | Test file |
|------|-----------|
| Tile content / search | `tests/test_exploration.py` |
| Special events | `tests/test_environment_special_events.py` |
| Reactions / capture | `tests/test_reactions.py`, `tests/test_capture.py` |
| Doors / traps | `tests/test_doors.py`, `tests/test_exploration.py` |
| Secrets | `tests/test_economy.py`, `tests/test_capture.py` |
| Classes catalog | `tests/test_class_profiles_audit.py` |
| Equipment | `tests/test_equipment_shop.py`, `tests/test_carry_limits.py`, `tests/test_special_items.py`, `tests/test_special_items_wiring.py`, `tests/test_equipment_batch.py` |
| PDF row text | `tests/test_pdf_table_compliance.py` |
