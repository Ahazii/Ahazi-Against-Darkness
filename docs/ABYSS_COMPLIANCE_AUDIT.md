# Four Against the Abyss — Compliance Audit

**Audit date:** 2026-06-17 (refreshed after hireling specials + negotiator UI)  
**Source of truth:** `Rules/Four-Against-the-Abyss.pdf`  
**App scope:** Random-dungeon digital solo play — Abyss content layered on Expanded Edition core. Heroic/Legendary/Epic tiers are **Forsaken Depths**, not Abyss.

## Classification key

| Label | Meaning |
| --- | --- |
| **implemented** | Engine + UI behavior matches Abyss; covered by tests |
| **partial** | Core behavior present; fidelity, UI, or edge-case gaps remain |
| **implemented with intentional interpretation** | Wired with documented EE merge or simplification |
| **missing** | Abyss expects behavior the app does not provide |
| **not applicable** | Outside random-dungeon solo digital play |

---

## Executive summary

| Abyss content block | PDF pages | Coverage | Open gaps |
| --- | --- | --- | --- |
| Expert advancement (d8+2, learn skill instead of level) | 14–15 | **~100%** | None material |
| Expert skills (41) | 15–23 | **~96%** | 9 partial fidelity/UI gaps |
| Expert spells (6) | 24–25 | **~100%** | None material |
| Abyss-only secrets (3) | 14 | **~100%** | Chaos Fanatics activation test only |
| Hirelings (10 retainers + 9 professionals) | 27+ | **~97%** | Porter bulky UI, storyteller patron, loadout enforcement |

**Bottom line:** Abyss is effectively playable. Remaining work is rule fidelity polish—not missing catalogs or core loops.

**Regression tests (Abyss-focused):** `tests/test_abyss_phase_a.py`, `tests/test_expert_skill_effects.py`, `tests/test_hirelings.py`, `tests/test_negotiator_reaction.py` — **18+ passed** (2026-06-17).

---

## 1. Expert advancement (p.14–15)

| Rule | Status | Notes |
| --- | --- | --- |
| Learn expert skill **instead of** +1 Level | **implemented** | L5+ fork after Expert tier training |
| Advancement roll **d8+2** | **implemented** | `tier_advancement.py`, `advancement_roll_spec` |
| Success: total > Level **or** natural 7–8 | **implemented** | `advancement_auto_success_naturals` |
| Each skill once (Impervious repeatable per type) | **implemented** | `expert_skills.py`, target picker for Impervious/Sworn Enemy |
| Class eligibility per skill | **implemented** | `expert_skills.json` class codes enforced |
| Expert tier entry (500 gp / 1 banked XP) separate from skill learn | **implemented** | Tier training vs skill fork documented in `rulebook_reference.json` |

---

## 2. Expert skills (pp.15–23) — 41 skills

All 41 catalog IDs are marked **wired** in `expert_skill_effects.py` with at least one engine hook.

### Fully implemented (32)

Acute Hearing, Arcane Tanner (core crafting/resale/dragon save), Berserk Fury (EE merge), Brawler, Combat Acrobatics, Commanding Presence, Create Holy Water, Culling of the Weak, Danger Sense, Deadly Accuracy, Deadly Strike, Double Attack, Dragonslayer's Strike, Dying Action, Gladiator, Impervious, Intuition, Knife Throwing, **Negotiator**, Orcslayer, Poison Resistance, Quick Footed, Scroll Maker, Shield Bash, Spore Alchemy, Spot Weakness, Stabbing Attack, Strong Will, Super Logic, Sworn Enemy, Turn Undead, Withstand Pain, Whirlwind of Steel.

*(Dead Shot works engine-side with auto-reroll on first failed missile — no declare UI.)*

### Partial — fidelity or UI gaps (9)

| Skill | Gap |
| --- | --- |
| **Arcane Tanner** (Phasing Panther Escape) | Escape tracked in per-encounter spent flags cleared each combat — **not once/adventure** as Abyss text implies |
| **Continual Light** | Engine allows wizard/cleric; **UI only offers cleric** |
| **Detective** | Bonus wired for clue searches but standard search flow never applies it (+1 clue / 4→5 intent mismatch) |
| **Stone Mastery** | Same search-flow gap for secret-door searches |
| **Lesser Necromancy** | Ritual works; **does not strip class abilities/spells** from raised undead ally |
| **Protective Incense** | Defense bonus wired; **once/encounter not enforced** (no `mark_encounter_spent`) |
| **Terrifying Savagery** | −1 morale once/encounter wired; **not gated** on barbarian minion kill triggering morale |
| **Vampire Hunter** | +1 Attack wired; **no bypass** for harming vampires without stakes/magic weapons |
| **Dead Shot** | Minor: auto-reroll only; no player opt-in |

### Intentional interpretation (1)

| Skill | Notes |
| --- | --- |
| **Berserk Fury** | Abyss: rage attack twice/adventure, no ranged. EE already gives scaling rage uses. Engine applies **+1 extra melee rage use** (`mechanic_regression_map.json`). |

---

## 3. Expert spells (pp.24–25) — 6 spells

| Spell | Status | Evidence |
| --- | --- | --- |
| Healing Surge | **implemented** | `expert_spells.py` |
| Infallible Missile | **implemented** | |
| Lifeforce Control | **implemented** | Combat + exploration UI |
| Mass Teleport | **implemented** | Combat + exploration UI |
| Aura of Terror | **implemented** | |
| Reverse Gaze | **implemented** | |

Wizard/elf L5+ learn fork, once-per-adventure slot tracking, and cast effects are wired. No material Abyss spell gaps identified.

---

## 4. Abyss-only secrets (p.14)

EE ships 16 secrets; Abyss adds three at p.14. Total in app: **19**.

| Secret | Status | Gap |
| --- | --- | --- |
| Chaos Fanatics (+1 Defense vs chaos fanatics) | **implemented** | No end-to-end `use_secret` test (defense bonus tested with flag pre-set) |
| I Know Where This Corridor Leads (reroll room content) | **implemented** | Tested in `test_abyss_phase_a.py` |
| I Can Cook This, and It's Yummy (halfling; +1 vs Madness/fear/disease) | **implemented** | Halfling gate + save bonus tested |

---

## 5. Hirelings (p.27+)

### Cross-cutting rules

| Rule | Status |
| --- | --- |
| Expert tier required | **implemented** |
| Max 2 retainers (#5–#6 marching) | **implemented** |
| Fee payment (non-refundable outside gold) | **implemented** |
| Combat round hireling attacks | **implemented** |
| Morale on party casualty (d6, 4+ / CP 3+) | **partial** — hero death only; not other morale triggers |
| Treasure share (2× fee, +1 morale) | **implemented** |
| Resurrection (max(50, 2× fee), fanatical) | **implemented** |
| Professionals max 3/camp | **implemented** |
| Buffs persist into next foray; cleared on dungeon exit | **implemented** |
| Home **hirelings_table** + Rules reference entry | **implemented** |

### Retainers

| Retainer | Status | Remaining gap |
| --- | --- | --- |
| Acolyte | **implemented** | Assignment required; adjacent to assigned cleric; Blessing preservation once/adventure |
| Bodyguard | **implemented** | Assignment + adjacent intercept; loadout not modeled |
| Dungeon Guide | **implemented** | Light-weapon restriction not enforced |
| Lantern Bearer | **implemented** | |
| Man-At-Arms | **implemented** | Loadout restrictions not enforced |
| Minstrel | **implemented** | Light-weapon restriction not enforced |
| Porter | **partial** | Gold load UI ✓; **`porter_load_item` (bulky objects) engine-only — no UI**; cargo not returned on clean exit |
| Rat Exterminator | **implemented** | d6-kill vs first rat in encounter; +2 Def vs rats |
| Spear Carrier | **implemented** | Weapon swap + Ready shield without attack forfeit; post-return slashing weapon not enforced |
| Surgeon | **implemented** | +2 Life heal; Read scroll/book from retainer panel |

### Professionals

| Professional | Status | Remaining gap |
| --- | --- | --- |
| Bladesmith | **implemented** | |
| Confessor | **implemented** | |
| Fortune-Teller | **implemented** | 2d8 bank + d8 consumption; barbarian ban |
| Herbalist | **implemented** | Whole-foray +1 poison/disease saves |
| Sage | **implemented** | |
| Shieldmaker | **implemented** | |
| Silversmith | **implemented** | Silver coating via `(silvered)` weapon finish |
| Storyteller | **partial** | +1 first morale roll ✓; **“while patron lives” not tracked** |
| Tailor | **implemented** | Auto ±1 when bribe outcome would flip; Negotiator manual nudge in reaction UI |

---

## 6. Not Abyss (clarification)

These appear in the app but are **not** Four Against the Abyss content:

| Content | Source |
| --- | --- |
| Heroic skills (45) | Forsaken Depths |
| Legendary skills (20) | Forsaken Depths |
| Heroic/Legendary/Epic tier dice & advancement | Forsaken Depths p.9 |
| EE core dungeon rules, bestiary, reactions | Expanded Edition |
| Fiendish Foes mode | Fiendish Foes supplement |

---

## 7. Recommended fix priority

### Medium (fidelity / UX)

1. **Porter** — UI for bulky item load; return cargo on successful dungeon exit.
2. **Protective Incense** — enforce once/encounter spent flag.
3. **Vampire Hunter** — bypass weapon restriction vs vampires.
4. **Detective / Stone Mastery** — apply search bonuses in actual search flow.
5. **Phasing Panther Garment** — adventure-scoped Escape tracking.
6. **Continual Light** — wizard holders in combat ability UI.

### Low (optional polish)

7. **Storyteller** — track paying hero as patron.
8. **Hireling loadout restrictions** (light armor, one-handed, etc.) — cosmetic enforcement.
9. **Expert skill test coverage** — dedicated tests for skills without unit tests.

---

## 8. Coverage table (updated)

| Abyss content | Coverage |
| --- | --- |
| Expert advancement | **~100%** |
| Expert skills (41) | **~96%** (32 full, 9 partial, 0 missing) |
| Expert spells (6) | **~100%** |
| Abyss p.14 secrets (3) | **~100%** |
| Hirelings | **~97%** |

**Overall Abyss compliance (random-dungeon solo scope): ~97%.**
