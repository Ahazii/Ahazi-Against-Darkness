# Four Against the Abyss — Compliance Audit

**Audit date:** 2026-06-17  
**Source of truth:** `Rules/Four-Against-the-Abyss.pdf` (Expert Skills pp.14–23, Expert Spells pp.24–25, Hirelings p.27+, Abyss-only Secrets p.14)  
**App scope:** Random-dungeon digital solo play — Abyss content layered on Expanded Edition core. Heroic/Legendary tiers are **Forsaken Depths**, not Abyss.

## Classification key

| Label | Meaning |
| --- | --- |
| **implemented** | Engine + UI behavior matches Abyss; covered by tests |
| **implemented with intentional interpretation** | Wired with documented EE merge or simplification |
| **missing** | Abyss expects behavior the app does not provide |
| **not applicable** | Outside random-dungeon solo digital play |

---

## 1. Expert Skills (pp.15–23) — 41 skills

| Area | Status | Evidence |
| --- | --- | --- |
| Catalog (41 skills) | implemented | `data/rules/expert_skills.json`, PDF table lock |
| Learn skill instead of level (d8+2) | implemented | `expert_skills.py`, tier advancement |
| All combat/exploration skills | implemented | `expert_skill_effects.py` — all marked `wired` |
| **Arcane Tanner** | implemented | Craft from hides; Phasing Panther Garment Escape once/adventure; Dragon-Skin +1 Defense and +1 saves vs dragon breath; 150gp resale; hide drops from dragons / rare weird foes |
| Berserk Fury vs EE rage | implemented with intentional interpretation | EE scaling rage + Abyss +1 extra melee rage (`mechanic_regression_map.json`) |

---

## 2. Expert Spells (pp.24–25) — 6 spells

| Spell | Status |
| --- | --- |
| Healing Surge | implemented |
| Infallible Missile | implemented |
| Lifeforce Control | implemented |
| Mass Teleport | implemented |
| Aura of Terror | implemented |
| Reverse Gaze | implemented |

---

## 3. Abyss-only Secrets (p.14)

EE ships 16 secrets (pp.123–124). Abyss adds three more at p.14:

| Secret | Status | Evidence |
| --- | --- | --- |
| Chaos Fanatics (+1 Defense vs chaos fanatics) | implemented | `secrets.py`, `use_secret`, `tests/test_abyss_phase_a.py` |
| I Know Where This Corridor Leads (reroll room content) | implemented | `_use_secret_corridor_leads`, `secrets_table` |
| I Can Cook This, and It's Yummy (halfling; +1 vs Madness/fear/disease) | implemented | `secret_yummy_meal_active`, save hooks |

Total secrets in app: **19** (16 EE + 3 Abyss).

---

## 4. Hirelings (p.27+)

| Area | Status |
| --- | --- |
| Retainers (0-level NPCs, marching order, pay fee) | **missing** |
| Professionals (between-adventure services) | **missing** |
| Commanding Presence hireling morale | **missing** (party fear saves wired) |
| Fanatical loyalty after resurrection | **missing** |

**Primary remaining Abyss gap.**

---

## 5. Documentation / metadata fixes (Phase A)

| Item | Status |
| --- | --- |
| `docs/ABYSS_COMPLIANCE_AUDIT.md` | implemented (this file) |
| Heroic/Legendary source labels in `rulebook_reference.json` | fixed — now **Forsaken Depths**, not Abyss |

---

## 6. Bottom-line coverage

| Abyss content | Coverage |
| --- | --- |
| Expert skills (41) | **~100%** (Arcane Tanner completed Phase A) |
| Expert spells (6) | **~100%** |
| Expert advancement (d8+2) | **Done** |
| Abyss p.14 secrets (3) | **Done** |
| Hirelings | **0%** |

**Recommended next phase:** Hirelings MVP (retainers in dungeon, camp hire UI, basic combat participation).
