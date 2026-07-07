# Four Against the Abyss — Compliance Audit

**Audit date:** 2026-06-23 (refreshed after shared retainer marching order + full-suite validation)
**Source of truth:** `Rules/Four-Against-the-Abyss.pdf`  
**Audit scope:** Phase A only — expert advancement, expert skills/spells,
Abyss p.14 Secrets, and hirelings layered on the Expanded Edition core.
This is not a whole-book Abyss compliance audit. Heroic/Legendary/Epic tiers
are **Forsaken Depths**, not Abyss.

## Classification key

| Label | Meaning |
| --- | --- |
| **implemented** | Engine + UI behavior matches Abyss; covered by tests |
| **partial** | Core behavior present; fidelity, UI, or edge-case gaps remain |
| **implemented with intentional interpretation** | Wired with documented EE merge or simplification |
| **missing** | Abyss expects behavior the app does not provide |
| **not applicable** | Outside random-dungeon solo digital play |

---

## Executive summary — implemented Phase A subset

| Abyss content block | PDF pages | Coverage | Open gaps |
| --- | --- | --- | --- |
| Expert advancement (d8+2, learn skill instead of level) | 14–15 | **~100%** | None material |
| Expert skills (41) | 15–23 | **~100%** | None material |
| Expert spells (6) | 24–25 | **~100%** | None material |
| Abyss-only secrets (3) | 14 | **~100%** | None material |
| Hirelings (10 retainers + 11 professionals) | 28+ | **~100%** | — |

**Bottom line:** The listed Phase A subset is substantially complete. Whole-book
Abyss coverage remains partial; see
[MASTER_RULE_COVERAGE.md](MASTER_RULE_COVERAGE.md).

**Regression tests (Abyss-focused):** `tests/test_abyss_phase_a.py`, `tests/test_expert_skill_effects.py`, `tests/test_hirelings.py`, `tests/test_hireling_choices.py`, `tests/test_alchemist.py`, `tests/test_poison_expert.py`, `tests/test_negotiator_reaction.py`, and UI copy/tooltip coverage in `tests/test_frontend_map_interactions.py`.

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

### Fully implemented (40)

Acute Hearing, Arcane Tanner, Berserk Fury (EE merge), Brawler, Combat Acrobatics, Commanding Presence, Continual Light, Create Holy Water, Culling of the Weak, Danger Sense, Deadly Accuracy, Dead Shot, Deadly Strike, **Detective**, Double Attack, Dragonslayer's Strike, Dying Action, Gladiator, Impervious, Intuition, Knife Throwing, Lesser Necromancy, **Negotiator**, Orcslayer, Poison Resistance, Protective Incense, Quick Footed, Scroll Maker, Shield Bash, Spore Alchemy, Spot Weakness, Stabbing Attack, **Stone Mastery**, Strong Will, Super Logic, Sworn Enemy, Terrifying Savagery, Turn Undead, Vampire Hunter, Withstand Pain, Whirlwind of Steel.

*(Dead Shot is declared in the combat ability selector and rerolls the hero's next failed missile attack.)*

### Partial — fidelity or UI gaps (0)

| Skill | Gap |
| --- | --- |
| — | — |

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
| Chaos Fanatics (+1 Defense vs chaos fanatics) | **implemented** | `use_secret` activation, consumption, defense bonus, and combat UI tooltip covered |
| I Know Where This Corridor Leads (reroll room content) | **implemented** | Tested in `test_abyss_phase_a.py` |
| I Can Cook This, and It's Yummy (halfling; +1 vs Madness/fear/disease) | **implemented** | Halfling gate + save bonus tested |

---

## 5. Hirelings (p.27+)

### Cross-cutting rules

| Rule | Status |
| --- | --- |
| Expert tier required | **implemented** |
| Max 2 retainers in the party marching order | **implemented** — camp hire form inserts into the shared #1–#6 marching line; roster ↑/↓ works at camp and in dungeon |
| Fee payment (non-refundable outside gold) | **implemented** — assignment validated before gold is spent |
| Combat round hireling attacks | **implemented** |
| Morale on casualty (d6, 4+ / CP 3+) | **implemented** — hero death, retainer death, petrification, insanity flee |
| Treasure share (2× fee, +1 morale) | **implemented** |
| Resurrection (max(50, 2× fee), fanatical) | **implemented** |
| Professionals max 3/camp | **implemented** |
| Buffs persist into next foray; cleared on dungeon exit | **implemented** |
| Home **hirelings_table** + Rules reference entry | **implemented** |

### Retainers

| Retainer | Status | Remaining gap |
| --- | --- | --- |
| Acolyte | **implemented** | Optional Blessing preserve UI |
| Bodyguard | **implemented** | Optional intercept; camp insertion picker; assign filtered to adjacent heroes |
| Dungeon Guide | **implemented** | Loadout enforced on equip |
| Lantern Bearer | **implemented** | |
| Man-At-Arms | **implemented** | |
| Minstrel | **implemented** | Loadout enforced on equip |
| Porter | **implemented** | Bulky load UI; cargo returned on clean dungeon exit |
| Rat Exterminator | **implemented** | d6-kill vs rats; +2 Def vs rats |
| Spear Carrier | **implemented** | Sidearm slashing weapon required after gear return |
| Surgeon | **implemented** | +2 Life heal; Read scroll/book; no-armor loadout |

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
| Storyteller | **implemented** | +1 first morale roll while patron lives |
| Tailor | **implemented** | Auto ±1 when bribe outcome would flip; Negotiator manual nudge in reaction UI |
| Alchemist | **implemented** | 8 potions; 50gp + materials; d6 completion on adventure exit; single order at a time |
| Poison Expert | **implemented** | Rogue L5+; 25gp; coat weapon/arrow `(poisoned)`; +1 vs minion or boss level drop |

---

## 6. Whole-book Abyss areas beyond Phase A

The following book areas are outside the original Phase A percentage. The
2026-06-28 runtime and phase-1 exact-effect passes make the random-dungeon
subset playable, indexed, and automated for the first trap/feature/event layer:

- deeper/Abyss dungeon generation and content tables — playable profile, p.46
  room content routing, monsters, treasure payloads, and wandering spawns are
  wired;
- minion leaders, multiple bosses, hordes and Trial of Champions rules;
- traps, treasure, hidden treasure, scrolls and magical defenses — Abyss traps,
  treasure choices, scroll/magic/defense rows, Useful Stuff, magical defense
  item names, and core inventory use-actions are wired;
- Abyss vermin, minions, bosses, weird monsters and dragons — vermin, minions,
  bosses, weird monsters, and large-room Dragon Lairs are routed;
- unique events, enchanted banquet and useful-stuff tables — event choices and
  direct effects are wired through the existing feature/treasure UI;
- Dark Plague and lycanthropy lifecycles are wired; vampire level-drain death
  blocks ordinary resurrection. Vampire sire hunt/re-encounter and the six
  Abyss campaign plots have playable persistent state/UI; Entity enforces one
  artefact piece per dungeon adventure. Optional extended-campaign chaining
  still needs manual playtest sign-off.

## 7. Not Abyss (clarification)

These appear in the app but are **not** Four Against the Abyss content:

| Content | Source |
| --- | --- |
| Heroic skills (45) | Forsaken Depths |
| Legendary skills (20) | Forsaken Depths |
| Heroic/Legendary/Epic tier dice & advancement | Forsaken Depths p.9 |
| EE core dungeon rules, bestiary, reactions | Expanded Edition |
| Fiendish Foes mode | Fiendish Foes supplement |

---

## 8. Recommended fix priority

### Medium (fidelity / UX)

1. ~~**Dead Shot**~~ — optional player-declare UI (2026-06-22).
2. ~~**Continual Light**~~ — wizard/cleric combat drawer eligibility and wording polish (2026-06-22).
3. ~~**Protective Incense**~~ — once/encounter spent flag enforced (2026-06-22).
4. ~~**Vampire Hunter**~~ — bypasses vampire weapon restriction (2026-06-22).
5. ~~**Phasing Panther Garment**~~ — adventure-scoped Escape tracking (2026-06-22).
6. ~~**Lesser Necromancy**~~ — raised undead lose class abilities/spells/learned skills (2026-06-22).
7. ~~**Terrifying Savagery**~~ — morale penalty gated on barbarian minion kill (2026-06-22).
8. ~~**Detective / Stone Mastery**~~ — initial Search roll treats 4 as 5 (2026-06-17).
9. ~~**Poison Expert professional**~~ — implemented (Abyss p.32).

---

## 9. Phase A coverage table

| Abyss content | Coverage |
| --- | --- |
| Expert advancement | **~100%** |
| Expert skills (41) | **~100%** (40 full, 0 partial, 1 intentional, 0 missing) |
| Expert spells (6) | **~100%** |
| Abyss p.14 secrets (3) | **~100%** |
| Hirelings | **~100%** |
| Abyss random-dungeon runtime | **partial/playable** |

**Implemented Phase A subset: ~99%. Whole-book Abyss coverage: partial.**
