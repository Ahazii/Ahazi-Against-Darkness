# Consolidated Playtest Plan

Last updated: 2026-07-13. Target build: v0.39.10.

This plan covers the current manual regression backlog in the fewest practical games. It deliberately does not claim to sign off the 172-row foe audit: every pending foe still needs its PDF row compared, structured mechanics checked, and a focused regression test before it can be marked reviewed in `docs/audits/FOE_RULE_AUDIT.md`.

## Before Games

1. In Developer Playtest Preferences, enable **dungeon playtest controls**. Leave **TAG fixed-result controls** off for now; enable that separate switch only before Game 3, where it exposes a fixed Rumor, Treasure Map, Thematic Dungeon, or Guild Job result instead of a random TAG lead.
2. In Developer > Supplement Workbench, confirm the installed EE, Abyss, and FD runtime branches are read-only and their tables/foes show under the correct book.
3. Keep Copy Narrative Report available. Copy it after each forced special encounter and after each game closeout.

## Game 1: EE + Abyss Regression

Start one Classical random dungeon with EE + Abyss. Use a four-hero party including an elf or wizard, a rogue, and a crushing weapon plus a bow. This single game covers shared exploration, camp, EE, and Abyss behaviour.

1. Explore one ordinary room, open an exit, save, reload, return through the exit, then Search. Leave treasure behind once, trigger a wandering encounter by Searching, and later Claim Treasure. Confirm every item/gp appears only once and the 200gp cap leaves only the excess behind.
2. Return to camp, bank carried gold, and re-enter. The map must show the entrance and its usable exits immediately before and after a normal browser refresh.
3. In the developer selector, confirm both Abyss and EE options appear. Run Abyss Unique Event: Dark Plague. Confirm the save/immunity or infection state appears in Narrative and survives a save/reload.
4. Run these Abyss foe encounters, resolving each before the next: Shrieking Fungi, Flying Skulls, Phasing Panther, Tentacled Brain, and Dragon Man. Check only the printed special behaviour named in `STATUS.md`; do not try to force every die result in this one pass. Record any discrepancy with a Narrative Report.
5. Run one EE foe from each group with a visible mechanic: core, Caverns, Fungal Grottoes, and Fiendish Foes. Confirm the selected name, normal Reaction flow, and its visible combat effect. Use one Weird or Boss as an EE Final Boss, claim its treasure, exit, and complete the adventure.
6. Before closeout, use EE Quest result to inspect one Quest route. Confirm the Quest Details panel identifies the printed result. Do not attempt all six Quest life cycles in this game; they remain separate rule-audit work.
7. In the eligible hero sheet, spend or bank one pending XP roll. Confirm the skill/spell choices are eligible, the resulting choice remains on that hero's sheet, and no duplicate chooser appears in the sidebar.

## Game 2: Forsaken Depths Regression

Start one FD dungeon with a tier-appropriate four-hero party. Enable the same dungeon playtest controls.

1. Confirm the selector has FD foe encounter and Forsaken Depths Citadel. Run Horde of Dark Elves; confirm the normal opening volley and combat handling. Then run one Vermin, Minion, Boss, Weird, and Citadel-Weird row, resolving each normally.
2. Force one Citadel result, preferably Citadel of Traps or Magic Citadel. Confirm the FD side sheet opens and normal room generation works. Complete enough of it to verify the return/exit path.
3. During ordinary exploration, exercise one FD room hazard or trap, one treasure choice, and one current-event choice if offered. Save/reload while an FD state, quest, or side sheet is active; confirm it returns intact.
4. If practical, trigger Lady in Gray or the Cyclopean Idol and accept one Quest. Verify the Ongoing Quests panel, the stated progress condition, and one reward/choice path.

## Game 3: TAG Regression

Start or generate one Adventures Guild lead using the fixed-result selector. Choose the lead family least recently tested; repeat this game only for other lead families when a specific route needs review.

1. Confirm the selected Rumor, Treasure Map, Thematic Dungeon, or Guild Job is visibly labelled as a developer override and its prompt text/branch buttons match the local extracted narrative.
2. Follow one branch through an encounter or handoff, then verify the applicable reward policy: no loot, scene reward, purchase/service, no automatic room loot, or handoff dungeon loot.
3. Run its closeout/signoff workflow, including any route marker, reward, XP, Guild share, and dashboard return. Confirm it does not leave a resumable active session after complete closeout.

## Result Recording

For every failure, record: game number, selected developer scenario, exact foe/result, current map element, action taken, and the Copy Narrative Report. A passing forced encounter proves that selected path only; it is not a blanket signoff for other rows in the same PDF table.
