# EE Completion Plan

Tracking document for Expanded Edition (EE) random-dungeon compliance work.

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
