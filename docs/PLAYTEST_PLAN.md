# Current Playtest Plan

Last updated: 2026-07-15. Target build: post-v0.39.17 Deep Troll / FD treasure-choice patch.

This is the active player checklist only. Completed and superseded checks are retained as release history in `docs/STATUS.md`; do not repeat them unless a later change specifically reopens them.

## Before Testing

1. Deploy the latest image and force-refresh until the header shows the current build.
2. In Developer Playtest Preferences, enable **dungeon playtest controls**. Leave TAG fixed-result controls off until Game 3.
3. Keep **Copy Narrative Report** available. Copy one after any failure and after each closeout.

## Passed: No New Game Needed

Evidence copied 2026-07-15 for live session `2b51e57ab5cd4623942fbef9b65b30d3`: after camping and re-entry, the current room was **Entrance Map Element 06**, mode/camp was `exploration / inside`, no enemies remained, and exits were south passage open plus west/east doors open. Resuming into the Camp screen is valid if the session was saved while `camped_outside`; the invariant is that **(Re)enter Dungeon** returns to Entrance 06 with dungeon exits usable, not to stale Map Element 32.

The session also showed no active recovery/body state in Debug Context after the playtest reset repair removed stale fallen-body markers. Follow-up player evidence found one UI freshness issue: **Complete / abandon** stayed dimmed after the pending Classical XP roll was spent until a hard refresh. The next build now rechecks exit completion against the latest in-memory session and gives the camp **Abandon Dungeon** button an explicit pending-XP disabled state/tooltip. Reconfirm once after deployment: spend or bank pending XP, return to the entrance, and the completion choice should enable without a browser hard refresh. A Final Boss is not required to abandon; pending Classical XP still intentionally blocks closeout until banked or spent.

## Passed: Game 1 EE + Abyss Targeted Check

Evidence copied 2026-07-15: Dragon Man was forced from camp re-entry at Entrance 06. Before claw attacks, all living heroes rolled Level 8 dragon-fire saves. The Elf and Rogue received the printed `+1`; the Warrior and Cleric did not. Failed saves lost exactly 1 Life, then ordinary claw attacks and treasure proceeded.

Optional recovery remains passive future evidence only: if a hero naturally falls while carrying Clues or a Secret in a disposable session, confirm Party Sheets stay visible, a single compact **Recovery** opener appears, and its draggable window offers only valid actions. The fallen-transfer modal must then show every living recipient and resolve once. Do not manufacture a death in a valuable party just for this check.

Already passed and deliberately removed from this game: Ant People marker spray, Dark Plague Level 10 workflow, Ghoul King Elf `+Level` save and Blessing cure, save/reload entrance restoration, 200gp carrying cap, left-behind treasure claim, Shrieking Fungi, Flying Skulls, Phasing Panther, Tentacled Brain, and ordinary EE table/sample checks. The Ghoul King automatic-hit-after-failed-save outcome was not rolled before the foe died; leave it as passive future evidence rather than repeating the encounter.

## Next Required: Game 2 Forsaken Depths

Resume the disposable Forsaken Depths Game 2 already started if it is still active. If it was abandoned, start one disposable Forsaken Depths dungeon with a tier-appropriate four-hero party.

1. Deploy the latest build and force-refresh. In the current Game 2 session, force **FD foe encounter -> Minions -> Deep Trolls** once. Confirm **Hack slain trolls** still appears after a troll body is down and, after using it, no slain Deep Troll returns on the next troll turn. The log should say the hacked bodies prevent the return. Confirm the defeated Deep Troll encounter still gives an FD treasure roll at `-1` and ordinary `minor encounter` XP wording.
2. If an FD treasure choice appears, confirm the choice buttons are visible in **Current Objective** before using **Claim Treasure**. The marker-menu path may also work, but it should no longer be the only visible route.
3. The following Game 2 checks are complete unless later regression reopens them: FD developer controls appeared with `Supplements: 3`; Shadowbats of the Deep combat looked correct; Infallible Missile created the Level 8+ second missile correctly; Deep Troll chip/hover and Hack button appeared; Deep Troll slain-body return fired before hacking; Horde of Dark Elves opening volley was visible; one Boss and one Weird entered ordinary combat; Undead Leviathan generated FD treasure; Citadel of Traps opened a side sheet.
4. To force a **Citadel-Weird**, choose **FD foe encounter**, then in the named foe dropdown select any foe under the **Citadel Weird** group (for example Chaos Mothbeast Queen). Resolve one such encounter. This remains open because the previous evidence showed Citadel-Weird rows mixed with ordinary FD Weird rows.
5. In the existing Citadel of Traps side sheet, generate and resolve one normal room, then confirm the return/exit route works. Save and reload while the side sheet is active; confirm it restores intact.
6. During exploration, resolve one FD hazard or trap and one treasure or current-event choice. If offered, accept Lady in Gray or Cyclopean Idol and confirm Ongoing Quests shows the progress condition and one reward or choice path.

## Game 3: Adventures Guild

Enable **TAG fixed-result controls** immediately before this game. Start one generated lead from the family least recently checked.

1. Confirm the selected Rumor, Treasure Map, Thematic Dungeon, or Guild Job is visibly marked as a developer override and the prompt/branch wording matches the extracted local narrative.
2. Follow one branch through an encounter or handoff. Confirm its reward policy: no loot, scene reward, purchase/service, no automatic room loot, or handoff-dungeon loot.
3. Complete its signoff workflow. Confirm route marker, reward, XP, Guild share, and dashboard return work, and no resumable active session remains after closeout.

## Record Failures

For a failure, provide the game number, selected developer scenario, exact foe/result, current map element, action taken, and a Copy Narrative Report. A passing forced encounter proves that selected row only; it does not sign off an entire PDF table.
