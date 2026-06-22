# Four Against Darkness — Expanded Edition Compliance Audit

**Audit date:** 2026-06-18  
**Source of truth:** `Rules/Four_Against_Darkness_Expanded_Edition.pdf` (214 PDF pages; book page ≈ PDF − 5)  
**App scope:** Random-dungeon digital solo play — **excludes AI Adventure import mode** and non-EE supplements except where EE embeds them (Fiendish Foes pp.184–191).  
**Method:** PDF outline + bookmark crosswalk; every actionable rule classified against structured data (`data/rules/*.json`), engine wiring, and locked regression tests — not stale prose docs alone.

### Explicit audit exclusions (out of scope — not counted as gaps)

| Section | Book pages | PDF pages | Rationale |
| --- | --- | --- | --- |
| **Roleplaying** (“The Roleplaying Game” through “The GM’s Role”) | **188–200** | **193–205** | GM/social/oracle/campaign prose; no digital solo mechanics to implement |
| **Roadmap** (“Creating Your Own Adventures” through “Roadmap: Where do I Go From Here?”) | **200–205** | **205–210** | Published-adventure design guidance and supplement pointers; not random-dungeon engine rules |
| AI Adventure import mode | — | — | Separate pipeline; excluded per audit charter |
| Sample adventures (Witch’s Cave, etc.) | 127–144 | 132–149 | Printed modules; not shipped as official EE book adventures |
| Background / Norindaal lore | 9–17 | 14–22 | Setting flavor only |

Book page ≈ PDF page − 5 (`book_page_offset` in outline JSON). Overlap at book p.200 is intentional: both exclusion bands meet at adventure-authoring prose.

## Classification key

| Label | Meaning |
| --- | --- |
| **implemented** | Engine + UI behavior matches EE; covered by behavior tests and/or reference entries |
| **implemented via hand-validated table** | Row text/order locked to PDF (`tests/test_pdf_table_compliance.py` and/or SHA256 table-family snapshots) |
| **implemented with intentional interpretation** | Wired, but engine chose a documented simplification or cross-book merge |
| **not applicable to current app scope** | GM/social/flavor, sample adventure book content, or features outside random-dungeon solo digital play |
| **missing** | EE expects behavior the app does not provide |
| **unclear — needs human PDF review** | Indexed in data/tests but verbatim PDF procedure not re-verified this pass |

---

## 1. Audit by PDF section

### Front matter (PDF 1–5)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Title, credits, OGL | not applicable | No mechanics |
| Print vs PDF page mapping | not applicable | Authoring aid only |

### Introduction (PDF 6–13, book 1–8)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| What is 4aD / supplements list | not applicable | Orientation |
| Choosing starting characters (4 heroes, levels) | implemented | Party size enforced; `tests/test_parties.py`, creation UI |
| Recommended level 1 start | implemented with intentional interpretation | App supports 2–4 in AI prompts; home creation allows any level band |
| How to use this book / flow overview | not applicable | Player guide prose |

### Background — Norindaal (PDF 14–22)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Setting lore, factions, map | not applicable | Flavor; no hex-campaign mode |

### Classes opener (PDF 23)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Class list overview | implemented via hand-validated table | `classes.json` signature lock — `tests/test_class_profiles_audit.py` |

### Character classes (PDF 24–71, book 19–66)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| All 20 class profiles (Life, wealth dice, gear, spells, abilities) | implemented via hand-validated table | `classes.json` SHA256 lock; 14 fields per class |
| Barbarian rage | implemented | `tests/test_class_abilities.py`, `tests/test_tier1_combat.py` |
| Swashbuckler traits (6) | implemented via hand-validated table | `swashbuckler_traits_table` PDF rows p.62; `tests/test_swashbuckler_traits.py` |
| Halfling Luck | implemented | `tests/test_class_abilities.py` |
| Paladin prayer / healing | implemented | Target UI + combat |
| Druid companion / Call of the Wild | implemented | `tests/test_class_abilities_t3.py`, split-party tests |
| Bard Song of Elidra range | implemented | Same/adjacent tile scope — `tests/test_split_party.py` |
| Tier 1–4 class tricks (EE flags) | implemented | `ee_class_tricks.json`, `class_tricks_implementation_table` (25 rows) — `tests/test_class_tricks.py` |
| Per-class combat modifiers (cleric vs undead, etc.) | implemented | `combat_modifiers_table` family lock; `tests/test_combat_modifiers.py` |
| Expert skill eligibility at L5 | implemented | Level-up fork — `tests/test_level_up.py`, `tests/test_expert_skills.py` |

### Magic / spells (PDF 72–84)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Basic wizard/cleric spell list | implemented via hand-validated table | `basic_spells_table` p.69/28 — `test_ee_p68_p76_spell_and_scroll_tables_match_pdf_rows` |
| Druid spells (12) | implemented via hand-validated table | p.70–72 rows; outdoor gates — `tests/test_outdoor_ee_rules.py`, `tests/test_spells_extended.py` |
| Illusionist spells (12) | implemented via hand-validated table | p.73–75; Glamour Mask / Banquet wired |
| Scroll rules | implemented via hand-validated table | `scrolls_table` p.76; `tests/test_spells.py` |
| Once per adventure per spell | implemented | `tests/test_spell_expended.py` |
| Magic resistance / Sleep immunity | implemented | `tests/test_combat_modifiers.py`, spell cast logs |
| Escape spell | implemented | `tests/test_spells.py` |
| Expert spells (Abyss catalog) | implemented via hand-validated table | `expert_spells.json` p.24–25; all six cast effects — `tests/test_expert_spells.py` |
| Outdoor-only druid/illusionist spells | implemented with intentional interpretation | Minimal `PlayContext` (no hex map); entrance/outdoor tiles — `terrain.py`, `play_context_table` |

### Equipment (PDF 85–93, book 80–88)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Shop catalog (40 items) | implemented via hand-validated table | `equipment_shop.json` p.81–88 — `test_ee_p81_p88_equipment_shop_contains_pdf_rows` |
| Door tools (crowbar, lock-picks) | implemented | `tests/test_doors.py`, `tests/test_equipment_clarifications.py` |
| Firearms (swashbuckler) | implemented | Shop + combat — equipment tests |
| Acid vial (combat, not shop) | implemented with intentional interpretation | Loot/resale only; documented in reference |
| Carry limits / encumbrance on doors | implemented | `tests/test_carry_limits.py` |
| Silvering / gilding services | implemented | `tests/test_equipment_shop.py` |

### Combat (PDF 94–104, book 89–99)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Attack / Defense / damage | implemented | `tests/test_combat.py` |
| Round structure, initiative p.146 | implemented | `tests/test_initiative.py` |
| Surprise / immediate action vs Reactions | implemented | `tests/test_reactions.py` |
| Morale / flee / withdraw | implemented | `tests/test_combat.py`, flee tests |
| Corridor rules / marching order | implemented | `tests/test_weapons.py`, trap targeting |
| Subdual / non-lethal | implemented | Quest bring-alive — `tests/test_quests.py` |
| Multi-attack foes | implemented | Combat UI grouping |
| Turn Undead | implemented | Cleric ability tests |
| Monster template effects (charge, poison, MR, regen, etc.) | implemented | `monster_template_effects.py`; `tests/test_monster_template_generalized_effects.py`, wraith boss tests |

### Reactions (PDF 105–107, book 100–102)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Check Reactions procedure | implemented | `tests/test_reactions.py` (55+ cases) |
| Category + named reaction tables | implemented via hand-validated table | 116 named / 265 rows SHA256 — `tests/test_secrets_reactions_table_family.py`, `tests/test_bestiary_coverage.py` |
| Capture / Trade Information / Magic Challenge / Puzzle | implemented | `tests/test_capture.py`, `tests/test_special_bribe_reactions.py` |
| Bribes (gold, weapons, food, gems, magic items) | implemented | Special-bribe UI + table-driven tests (42 cases) |
| Split party / scout ahead | implemented | EE p.105 — `tests/test_split_party.py`, `tests/test_active_group.py` |
| Simultaneous sub-fights | implemented | Detached combat rounds |

### Dungeon delving / exploration (PDF 108–129)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Search table d6 (corridor −1) | implemented via hand-validated table | p.107 — exploration family lock |
| Wandering monsters | implemented via hand-validated table | p.107 |
| Hidden treasure formulas | implemented via hand-validated table | p.108 |
| Door table 2d6 | implemented via hand-validated table | p.109 — `tests/test_doors.py` |
| Clues (earn/spend) | implemented via hand-validated table | `clue_spends_table` — secrets family lock |
| Secrets (16) | implemented via hand-validated table | All `implementation: wired` — `tests/test_secrets_text_compliance.py` |
| Madness (gain/heal/insanity) | implemented | `madness.py`; ghost fear; exit heal once |
| Rest once/adventure | implemented | p.114 — `tests/test_rest.py` |
| Level-up procedure | **validated** | EE p.117–118 XP tables locked; FD tier dice merged; `tests/test_level_up_pdf_compliance.py`, `tests/test_tier_dice.py`, `tests/test_level_up.py` |
| Death / carry body / resurrection 1000gp | implemented | `tests/test_death_recovery.py` |
| Retreat / camp outside | implemented | `tests/test_retreat.py`; roster sync on complete **and** camp |
| d66 map placement / truncation | implemented | `tests/test_exploration.py`, tile validation |
| Tile content table | implemented via hand-validated table | p.152 — roll 5/7–10 EE splits |
| Environment variants (dungeon/caverns/fungal) | implemented | Secret passage UI; table routing — `tests/test_environment_special_events.py` |
| Caverns special features + water pools | implemented via hand-validated table | p.112 rows locked in `test_ee_p153_p154_special_feature_and_event_tables_match_pdf_rows`; water pool UI wired |
| Paper map 20×28 bounds | implemented | Session option |

### Sample adventures (PDF 130–149)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Witch's Cave, Purple Crystals, Abandoned Mines, flowcharts | not applicable | Printed modules; not shipped as playable EE book adventures in app |
| Flowchart procedure diagrams | not applicable | Reference for human GMs |

### Reference charts (PDF 151–153)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Quick-reference tables (duplicate of main tables) | implemented via hand-validated table | Same keys as locked dungeon tables |
| Map element diagram | implemented via hand-validated table | 42 tiles `implementation_status: validated` — `tests/test_tiles_validation.py` |

### Random dungeon & event tables (PDF 154–161)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Dungeon special features / events | implemented via hand-validated table | p.153–154 |
| Caverns / fungal special events | implemented via hand-validated table | p.155–156 |
| Treasure d6 | implemented via hand-validated table | p.157 |
| Magic treasure d6 | implemented via hand-validated table | p.158 |
| Caverns special items / fungal rare items / mushrooms | implemented via hand-validated table | p.159–161; fungal items wired in engine |

### Treasure & quest tables (PDF 162–168)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Quest table | implemented via hand-validated table | p.162 — `tests/test_quests.py` |
| Epic rewards | implemented via hand-validated table | p.163; concrete reward wiring |
| Magic weapons/armor rolls | implemented | `tests/test_magic_weapons.py` |
| XP systems (4 modes) | implemented via hand-validated table | Economy family lock — `tests/test_economy.py` |

### Trap tables (PDF 169–171)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Dungeon / caverns / fungal traps | implemented via hand-validated table | p.164–166; target shapes wired — `tests/test_exploration.py` |
| Rolling boulder choices | implemented | Map trap menu — frontend tests |
| Hidden pit → secret passage clue | implemented | `tests/test_exploration.py` |

### Monster tables — standard environments (PDF 172–183)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Vermin / minions / weird / boss (dungeon) | implemented via hand-validated table | p.167–170 names + stats |
| Caverns variants | implemented via hand-validated table | p.171–174 deep text match tests |
| Fungal grottoes variants | implemented via hand-validated table | p.175–178 deep text match tests |
| Named per-monster reaction tables | implemented via hand-validated table | 265 rows locked; every indexed monster resolves own table |
| Final Boss / wandering exclusions | implemented | `never_wandering`, Final Boss reveal |

### Fiendish Foes (PDF 184–191, embedded in EE)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Fiendish vermin/minion/weird/boss tables | implemented via hand-validated table | `test_fiendish_foes_*_match_pdf_*` (5 tests) |
| Fiendish treasure + magic treasure | implemented via hand-validated table | Row locks; roll when fiendish-tagged foes on tile |
| Wand of Power | implemented | Wizard charge spend — reference + tests |
| **L3+ optional Fiendish Foes tables (d6 mixed 50%)** | **implemented** | `fiendish_foes_enabled` per adventure type; EE p.180 eligibility at roll time — `tests/test_fiendish_foes_mode.py` |
| Mixed major+minor XP (2 rolls) + minor treasure suppression | **implemented** | EE p.180 — `tests/test_fiendish_foes_mixed_rules.py` |
| Global `treasure_rolls` (once per foe type; missing = no treasure) | **implemented** | `monster_combat_hooks.treasure_roll_count_from_defeated` |
| Fiendish boss/weird combat hooks (mantlebeast, skeletal demon, etc.) | **implemented** | `monster_combat_hooks.py` — `tests/test_monster_combat_hooks.py` |
| Fiendish Chaos Lord free slaves + wandering | **implemented** | `resolve_free_slaves` action + UI |
| Arrow of Slaying any major table | **implemented** | `major_foe_table_keys()` — `tests/test_quests.py` |
| Enchanted Paint (gear/rations/doors) | **implemented** | `special_items.py` — `tests/test_special_items.py` |
| Fiendish vermin/minion combat_modifiers | **implemented** | Blademaster riposte, gnoll frenzy, spider webs/poison, armored skeleton modifiers, orc looter spell morale — `monster_combat_modifiers.py`, `tests/test_monster_combat_modifiers.py` |

### Roleplaying (book 188–200 / PDF 193–205) — **EXCLUDED**

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Entire section (oracle cards, campaign, GM role, four pillars, etc.) | **not applicable — excluded from audit** | Explicit scope exclusion; no engine deliverables |

### Roadmap & adventure authoring (book 200–205 / PDF 205–210) — **EXCLUDED**

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Creating adventures, roadmap, supplement pointers | **not applicable — excluded from audit** | Explicit scope exclusion; future authored-adventure phase |

### Back matter (PDF 211–214, book 206+)

| Rule / content | Classification | Evidence |
| --- | --- | --- |
| Index, OGL repeat | not applicable | |

---

## 2. Gap list (by rules impact)

### High impact (affects core random-dungeon EE play)

_None remaining in the in-scope random-dungeon loop._

### Medium impact

1. **Fortress-style outdoor / hex wilderness** — EE minimal outdoor context exists (`play_context_table`); Fortress hex-map rules explicitly deferred in `mechanic_regression_map.json`. **Impact:** outdoor spells gated; no wilderness exploration loop.

### Low impact

2. **Imported-adventure-only edge cases** — Paint on imported map tiles; AI Adventure import mode excluded from audit scope.

---

## 3. Intentional interpretations & source conflicts

| ID | Sources | Current behavior | Location |
| --- | --- | --- | --- |
| Berserk Fury vs EE rage | Abyss p.15 vs EE Barbarian p.24 | EE scaling rage uses preserved; Berserk Fury adds +1 melee rage use | `mechanic_regression_map.json` → `berserk_fury_ee_compatibility` |
| Expert skills catalog | Abyss p.15–22 in EE book context | Abyss-only `expert_skills.json`; EE class tricks separated | `expert_skills.json`, `ee_class_tricks.json` |
| Heroic / Legendary skills | Forsaken Depths p.6–21 | FD catalogs used inside EE app | PDF tests cite FD pages |
| Tier training costs / tier dice | FD p.9 + EE level gates | Merged tier dice; **action dice follow training flags** (Expert d8 explodes 7–8, etc.) when PC object passed to roll — `tests/test_level_up_pdf_compliance.py` |
| Acid vial | EE equipment prose | Combat/loot only; not in shop catalog | `equipment_shop.json`, reference |
| Outdoor spells | EE druid/illusionist outdoor gates | Tile `terrain`/`environment` flags, not hex map | `terrain.py`, `play_context_table` |
| Fiendish treasure routing | EE p.184–191 | Rolls fiendish table only if fiendish-tagged foes already on tile | `random_dungeon.py` `_tile_has_fiendish_foes` |
| Capture ranger Clue reduction | Gap note vs p.102 | 3 Clues flat; no ranger discount | `rejected_false_positive` |

---

## 4. Tests & table locks proving compliance

### PDF row-by-row locks (`tests/test_pdf_table_compliance.py`)

38 test functions covering: spells, scrolls, expert/heroic/legendary catalogs, swashbuckler traits, search/wandering/hidden treasure/doors/tile content, special features/events (dungeon + caverns + fungal), treasure/quest/epic rewards, traps (3 environments), equipment shop, environment items/mushrooms, monsters (dungeon + caverns + fungal + **fiendish**), fiendish treasure tables.

### SHA256 API snapshot families

| Test file | Tables locked |
| --- | --- |
| `tests/test_exploration_generation_table_family.py` | doors, traps×3, search, wandering, room content, special features/events×3, map elements |
| `tests/test_economy_rewards_table_family.py` | XP×4, economy services, shop, treasure×5, quests, epic rewards, tier training |
| `tests/test_secrets_reactions_table_family.py` | clues, secrets, category reactions, 116 named reaction tables |
| `tests/test_spells_skills_combat_table_family.py` | spells×4, expert/heroic/legendary skills, class tricks, swashbuckler, combat modifiers |
| `tests/test_class_profiles_audit.py` | 20 classes × 14 fields |
| `tests/test_bestiary_coverage.py` | 100 monster stat rows; 265 reaction rows |

### Behavior regression suites (representative)

| Area | Primary tests |
| --- | --- |
| Combat core | `test_combat.py`, `test_initiative.py`, `test_combat_modifiers.py` |
| Reactions | `test_reactions.py`, `test_special_bribe_reactions.py`, `test_capture.py` |
| Exploration | `test_exploration.py`, `test_doors.py`, `test_tier3_map.py` |
| Split party | `test_split_party.py`, `test_active_group.py` |
| Outdoor EE | `test_outdoor_ee_rules.py`, `test_terrain.py` |
| Economy / treasure | `test_economy.py`, `test_magic_weapons.py`, `test_fungal_rare_items.py` |
| Class / skills | `test_class_tricks.py`, `test_expert_skills.py`, `test_heroic_skill_effects.py`, `test_swashbuckler_traits.py`, `test_level_up_pdf_compliance.py` |
| Fiendish Foes | `test_fiendish_foes_mode.py`, `test_fiendish_foes_mixed_rules.py`, `test_monster_combat_hooks.py`, `test_monster_combat_modifiers.py` |
| Mechanic map integrity | `tests/test_mechanic_regression_map.py` |
| Rule reference | `tests/test_rulebook_reference.py` (140+ entries; API index sync) |
| **Total suite** | **1169 tests** collected (2026-06-20) |

### Structural validators

- `tools/validate_tiles.py` — 42 map elements  
- `tools/validate_monsters.py` — bestiary + reaction index  
- `tests/test_rulebook_validation.py` — 52 home Rules table keys classified  

---

## 5. Compliance estimates

| Scope | Estimate | Basis |
| --- | --- | --- |
| **EE random-dungeon procedural loop** | **~99%** | Fiendish Foes, combat modifiers, Enchanted Paint, treasure rules wired |
| **Whole in-scope EE book** (excludes RP pp.188–200, Roadmap pp.200–205, sample modules, lore) | **~92–95%** | Fortress hex outdoor deferred; imported-adventure edge cases only |

**Definition of done status:** Every indexed EE mechanic in `mechanic_regression_map.json` is implemented, rejected with evidence, or listed above as **missing/deferred**. No stale `partial` entries for in-scope random-dungeon mechanics.

---

## 6. Concrete next implementation tasks

1. **Fortress / hex outdoor** — Remains deferred until authored-adventure phase; do not count as EE compliance blocker for random dungeon.

2. **Refresh home Rules table row counts** after future table additions (economy family SHA256 updates as needed).

---

## Appendix: Files used (not prose docs)

- `Rules/Four_Against_Darkness_Expanded_Edition.pdf` + `Rules/Four_Against_Darkness_Expanded_Edition_outline.json`
- `data/rules/dungeon_tables.json`, `classes.json`, `monsters.json`, `tiles.json`, `equipment_shop.json`, `expert_skills.json`, `mechanic_regression_map.json`, `rulebook_reference.json`
- `tests/test_pdf_table_compliance.py` and four `*_table_family.py` suites
- `tests/test_bestiary_coverage.py`, `tests/test_mechanic_regression_map.py`
