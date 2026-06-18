# Reactions Audit

**Audited:** 2026-06-17  
**Polish completed:** 2026-06-17 (items 1–5)  
**Scope:** Four Against Darkness Expanded Edition reaction tables in `data/rules/monsters.json`, category fallbacks in `dungeon_tables.json`, engine handlers in `reactions.py` / `random_dungeon.py`, UI in `app.js`, and regression tests.

## Summary

| Metric | Count |
| --- | --- |
| Named monster reaction tables | 116 |
| Total reaction rows (named tables) | 265 |
| Distinct reaction `key` values in named tables | 27 (+ `bribe_magic_item` via `bribe_magic_item: true` normalization) |
| Rows on category fallback tables | 11 |
| Tests in `tests/test_reactions.py` | 55 |
| Tests in `tests/test_special_bribe_reactions.py` | 42 |

**Overall:** All reaction keys are engine-handled with Combat Focus / legacy UI affordances. Scout-ahead reactions share the same special-outcome paths. Dwarf Miser blocks all bribes. Sleep reads `attack_bonus_first_round` from data. Gem bribes log counted resale value (dwarf +20% where applicable). Table-driven tests cover every `bribe_*` special key.

Full table listing: `docs/REACTION_TABLES_LIST.txt` (regenerate with `python tools/list_reaction_tables.py`).

---

## Reaction keys inventory

| Key | Rows | Engine | UI | Tests |
| --- | ---: | --- | --- | --- |
| `fight` | 93+ | Yes | N/A (combat) | Yes |
| `fight_to_death` | 47+ | Yes (no morale) | N/A | Partial |
| `bribe` | 36+ | Yes (`pay_bribe`) | Pay / Fools' Gold | Yes |
| `flee` | 33+ | Yes (strike as they run) | N/A | Partial |
| `ignore` | 11 | Yes (peaceful) | N/A | Partial |
| `quest` | 9 | Yes | Accept / Decline | Yes |
| `blood_offering` | 7 | Yes | Life or chicken blood | Yes |
| `flee_if_outnumbered` | 6 | Yes | N/A | Partial |
| `magic_challenge` | 2 | Yes (save prompt) | Luck / prayer reroll | Yes |
| `sleep` | 2 | Yes (data-driven bonus) | N/A | Yes |
| `bribe_food` | 2 | Yes | Accept (auto food) | Yes |
| `puzzle` | 1 | Yes (save prompt) | Luck reroll | Yes |
| `peaceful` | 1 | Yes | N/A | Partial |
| `trade_information` | 1 | Yes | Sell / Buy / Decline | Yes |
| `bribe_treasure_or_magic_item` | 1 | Yes | Per magic item + all gold | Yes |
| `bribe_gold_or_food` | 1 | Yes | Food / gold mode buttons | Yes |
| `offer_information` | 1 | Yes (caverns morlock flag) | N/A | Partial |
| `buy_weapons` | 1 | Yes (cave orcs) | Per-weapon sell | Yes |
| `bribe_ration_gold_or_mushroom` | 1 | Yes | Food / mushroom / gold | Yes |
| `bribe_food_or_gem` | 1 | Yes | Food / per-gem give | Yes |
| `bribe_gem` | 1 | Yes | Per-gem give | Yes |
| `bribe_scrolls_or_potions` | 1 | Yes | Per scroll/potion give | Yes |
| `challenge_of_champions` | 1 | Yes (trial flow) | Accept champion | Partial |
| `bribe_gem_or_two_handed_weapon` | 1 | Yes | Per gem or heavy weapon | Yes |
| `offer_food` | 1 | Yes (heal 1 Life) | N/A | Partial |
| `trade` | 1 | Yes (mushroom pickers) | Open Trade / buy / Done | Yes |
| `bribe_food_per_foe` | 1 | Yes | Accept (auto food) | Yes |
| `trial_of_champions` | 1 | Yes (trial flow) | Accept champion | Partial |
| `bribe_magic_item` | 0* | Yes (Wraith normalize) | Per magic-item give | Yes |

\*Normalized from `bribe` rows with `bribe_magic_item: true` (Wraith).

**Overlay (not a table key):** `capture` — minion-only roll 1 overlay in `apply_reaction_overlays()`; also minion fallback table roll 1.

---

## Polish completed (2026-06-17)

1. **Per-item pickers** — gems, scrolls/potions, heavy weapons, magic items, cave-orc weapon sales, compound bribe mode buttons.
2. **Scout path parity** — quest, blood offering, buy weapons, magic-item bribe, special bribes, sleep bonus, gold bribe.
3. **`attack_bonus_first_round`** — sleep rows drive `Sleeping foe +N first Attack` and `SessionState.reaction_sleep_attack_bonus`.
4. **Dwarf gem counted value** — `jewelry_bribe_counted_gp()` logged on gem surrender.
5. **Table-driven tests** — `tests/test_special_bribe_reactions.py` (success/failure/Miser/scout/gem-counted matrix).

Earlier P0 fixes (same pass): Wraith `bribe_magic_item` normalization; Dwarf Miser bribe block.

---

## Wired and verified

- Category fallbacks: vermin / minion / major / default (`dungeon_tables.json`)
- Named-table resolution per foe group (`resolve_reaction_source`)
- Capture overlay for homogeneous minion groups (roll 1)
- Standard gold/weapon bribes + Fools' Gold + `no_fools_gold`
- Trade Information (sell clues / buy clue)
- Halfling Mushroom Pickers trade stock + buy UI
- Puzzle & Magic Challenge (save + luck/paladin reroll)
- Blood offering (2 Life or jar of chicken blood)
- Quest accept → `active_quest`
- Trial / Challenge of Champions
- Scout-ahead reactions (`scout_reaction` on detached tile)
- Split-party scoping (`combat_party` for bribes, trade info, challenges)
- Reaction modifiers: Negotiator, Song of Elidra, Beast Leadership
- Brown Cap Delight = 3 rations for food bribes

---

## Commands

```powershell
cd c:\Coding\4AD
$env:PYTHONPATH="src"
python -m pytest tests/test_reactions.py tests/test_special_bribe_reactions.py tests/test_mechanic_regression_map.py tests/test_secrets_reactions_table_family.py -q
python tools/list_reaction_tables.py > docs/REACTION_TABLES_LIST.txt
```
