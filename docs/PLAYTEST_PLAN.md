# Current Playtest Plan

Last updated: 2026-07-15. Target build: v0.39.17.

This is the active player checklist only. Completed and superseded checks are retained as release history in `docs/STATUS.md`; do not repeat them unless a later change specifically reopens them.

## Before Testing

1. Deploy the latest image and force-refresh until the header shows `v0.39.17`.
2. In Developer Playtest Preferences, enable **dungeon playtest controls**. Leave TAG fixed-result controls off until Game 3.
3. Keep **Copy Narrative Report** available. Copy one after any failure and after each closeout.

## No New Game Needed

1. Resume the current EE + Abyss session. It must open at **Entrance Map Element 06**, not the room where the manual save was made, and its dungeon exit must be usable immediately after a normal refresh.
2. Choose **Camp outside**, refresh once, then use **(Re)enter Dungeon**. The party must return to that same entrance with its existing exits usable; the saved checkpoint must not move the party back to Map Element 32.
3. Return to camp again. **Abandon Dungeon** must be present even though the Final Boss is not defeated. This current session has one pending Classical XP roll: bank it to an eligible hero or spend it from the camp XP panel, then confirm **Abandon Dungeon** completes the session. Do not discard or silently lose earned XP.
4. Party Sheets must remain fully visible and there must be no Recovery control, body carrier, fallen-body marker, or pending transfer. Do not deliberately create another recovery situation in this valuable session.

## Game 1: EE + Abyss Targeted Check

Start one disposable Classical EE + Abyss dungeon with an Elf, a Rogue, and ordinary combat equipment. Use the developer selector only while no encounter is active.

1. Force **Dragon Man**. Before claw attacks, every living hero must make the displayed Level 8 dragon-fire save. Only Elves, Rogues, and Swashbucklers receive `+1`; Wizards receive no extra printed bonus. A failed save loses exactly 1 Life.
2. Optional only if a hero naturally falls while carrying Clues or a Secret: confirm Party Sheets stay visible, a single compact **Recovery** opener appears, and its draggable window offers only valid actions. The fallen-transfer modal must then show every living recipient and resolve once. Do not manufacture a death in a non-disposable party just for this check.

Already passed and deliberately removed from this game: Ant People marker spray, Dark Plague Level 10 workflow, Ghoul King Elf `+Level` save and Blessing cure, save/reload entrance restoration, 200gp carrying cap, left-behind treasure claim, Shrieking Fungi, Flying Skulls, Phasing Panther, Tentacled Brain, and ordinary EE table/sample checks. The Ghoul King automatic-hit-after-failed-save outcome was not rolled before the foe died; leave it as passive future evidence rather than repeating the encounter.

## Game 2: Forsaken Depths

Start one disposable Forsaken Depths dungeon with a tier-appropriate four-hero party.

1. Force one FD Vermin, Minion, Horde of Dark Elves, Boss, Weird, and Citadel-Weird. Confirm the named foe enters ordinary combat and the Horde's opening volley is visible.
2. Force one Citadel, preferably **Citadel of Traps** or **Magic Citadel**. Confirm the side sheet opens, one normal room is generated, and the return/exit route works.
3. During exploration, resolve one FD hazard or trap and one treasure or current-event choice. Save and reload while the FD side sheet, state, or quest is active; confirm it restores intact.
4. If offered, accept Lady in Gray or Cyclopean Idol. Confirm Ongoing Quests shows the progress condition and one reward or choice path.

## Game 3: Adventures Guild

Enable **TAG fixed-result controls** immediately before this game. Start one generated lead from the family least recently checked.

1. Confirm the selected Rumor, Treasure Map, Thematic Dungeon, or Guild Job is visibly marked as a developer override and the prompt/branch wording matches the extracted local narrative.
2. Follow one branch through an encounter or handoff. Confirm its reward policy: no loot, scene reward, purchase/service, no automatic room loot, or handoff-dungeon loot.
3. Complete its signoff workflow. Confirm route marker, reward, XP, Guild share, and dashboard return work, and no resumable active session remains after closeout.

## Record Failures

For a failure, provide the game number, selected developer scenario, exact foe/result, current map element, action taken, and a Copy Narrative Report. A passing forced encounter proves that selected row only; it does not sign off an entire PDF table.
