# Current Playtest Plan

Last updated: 2026-07-16. Target build: v0.39.24 Dark Elf Warlock combat follow-up.

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

## Next Required: Game 2 Forsaken Depths Resume Checklist

The latest disposable Game 2 report was session `003f51881ebc417a8a70891da9e0de00`: an EE+Abyss+FD session where Soulbinding Blessing cure works, the Citadel side sheet now re-enters, returns to the main map, saves/reloads, generates deeper Citadel rooms, and clears its active marker after return. v0.39.23 included the follow-up concrete weapon-choice fixes for FD p.62 row 3, FD p.62 row 7, Greater Mutated Goblin fixed loot, and Abyss weapon-choice treasure. v0.39.24 changes Dark Elf Warlock from two generic attacks to the printed FD p.44 split: one staff attack plus one separate ice blast. Older sessions `f0ab5c80eee34a9c9cec7b3e95484823` and `fed118f1c70a4835b84f245bf8ddefeb` may now be complete or abandoned. Use the active disposable session if it is still available; otherwise start a fresh disposable EE+Abyss+FD Game 2 after deployment.

Active goal: prove only the latest fixes and still-open FD fidelity gaps. Do not rerun passed Citadel, Soulbinding, spider, Deep Troll, or Greater Mutated Goblin checks unless a later deploy visibly reopens one of them.

### Must Do Next

1. Deploy v0.39.24 or later and force-refresh until the app header shows that build.
2. Force or naturally produce FD p.62 treasure roll row 3. Choose the masterwork alternative and confirm the UI asks for the concrete weapon type, then awards that exact weapon. FD p.62 row 3 is player choice: `10d6+10 gp OR a Masterwork weapon of your choice`.
3. Force or naturally produce FD p.62 treasure roll row 7. Choose **10 silvered melee weapons** and confirm the app asks which melee weapon type, then awards ten concrete silvered weapons.
4. Force **Forsaken Depths Event** from Developer Playtest controls. Pick any d10 row that is easy to inspect; `d10 = 3 - Something Stirs in the Darkness` should set the six-area state and log the FD p.63 event. Event generation now exists for Abyss unique events, EE quests/foes/final bosses, and Forsaken Depths Events/Citadels/foes; Courtship Demesne event overrides are not yet added because that supplement's route is not a single d6/d10 dungeon-event table.
5. Force **Dark Elf Warlock** once after deploying v0.39.24. Treasure at `+2` is passed; the open live check is FD p.44's printed split: one staff attack and one ice blast each turn. The ice-blast target should make a Defense roll or lose 2 Life, shields should count, armor should be ignored except Cold defense, and barbarians/Ice-based characters should add +1/2 L. Current limitation: the app does not yet store PC sex/gender, so the printed female elf/female spellcaster targeting priority cannot be faithfully automated yet.
6. During ordinary exploration, resolve one FD hazard/event choice and, if offered, accept Lady in Gray or Cyclopean Idol. Confirm Ongoing Quests shows the progress condition and one reward or choice path.
7. If an Armored Forsaken Depths Troll appears naturally and a caster uses an offensive spell, confirm the second MR penetration roll is against HCL-1 unless a Magic Citadel is active. HCL means Highest Character Level; for a highest-level-10 party, HCL-1 is MR penetration level 9.
8. After any failed path or newly fixed path, save, return to Dashboard, resume, and confirm the same room restores with the expected route labels and no stale side-sheet marker. Skip this save/reload step if nothing new or suspicious happened.

### Do Not Repeat Unless Reopened

- Citadel route evidence from 2026-07-16 passed: **Enter Citadel sheet** re-entered the existing sheet, **Return to main map** remained available and working, **Explore deeper into Citadel** generated room 2/21, save/dashboard/resume restored the correct Citadel room, and returning to the entrance then main map cleared the active side-sheet marker.
- Soulbinding Blessing cure passed: Sister Joyce cast Blessing on Sly Silas, the Narrative logged `Blessing frees Sly Silas from Soulbinding (FD p.58)`, the `FD Soulbound` chip disappeared, and pending Soulbinding choices cleared.
- The stale main-map Citadel marker is gone after resume.
- FD developer controls appeared with `Supplements: 3`.
- Shadowbats of the Deep combat looked correct.
- Infallible Missile created the Level 8+ second missile correctly.
- Deep Troll chip/hover and **Hack slain trolls** appeared; slain-body return fired before hacking; the hack blocked the next group return after the follow-up patch; Deep Troll treasure at `-1` and ordinary minor XP wording were visible.
- Horde of Dark Elves opening volley and treasure roll were visible.
- One Boss and one ordinary Weird entered ordinary combat.
- Undead Leviathan generated FD treasure.
- Dark Elf Warlock FD treasure roll at `+2` was visible.
- FD p.62 treasure choice buttons appeared in the main action strip/Current Objective and accepted schema payloads.
- Forcing Citadel no longer completes the adventure via the dungeon exit.
- Citadel of Traps creates/reveals only the first side-sheet room on entry.
- Citadel of Traps Minions/Hordes replacement can create a concrete trap with **Resolve Trap**.
- Spore/Deep Cave/Shadowbat vermin no-treasure outcomes are correct.
- Spore Spiders use their named reaction table and do not flee.
- Deep Cave Spiders reduce remaining spiders by 1 Level per two killed to minimum L3.
- Greater Mutated Goblin corrosive mucus, Tier damage, Blessing/defeat cleanup, XP, and printed fixed treasure have live evidence. Its previous generic masterwork-edged-weapon placeholder is covered by automated tests and does not require replay unless it appears naturally.
- Sir Benedict's repaired placeholder item is now **Masterwork sword** in the live report.
- Armored Forsaken Depths Troll armor deflection now has live evidence: non-magical Masterwork sword, Sword, Mace, and Dagger hits roll the printed 4-in-6 deflection before damage. Its treasure at `+2` and Final Boss handling also have live evidence.

### Passive Future Evidence

- If a fresh Soulbinding trap naturally appears later, move away once and confirm the **Lose 1 Life** / **Gain 1 Madness** buttons appear before continuing.
- If Spore Spiders naturally produce melee kills, confirm coughing checks accumulate correctly and magical healing before encounter end prevents the loss.
- If Deep Cave Spiders naturally kill a character, confirm they immediately spawn another 2d6 Deep Cave Spiders and the slain character cannot be resurrected.
- If a hero naturally falls while carrying Clues, a Secret, or valuable items, reuse the Game 1 passive recovery checklist instead of manufacturing a death.
- If Ghoul King naturally appears again, the remaining passive Abyss check is the automatic-hit-after-failed-save outcome.
- Record as lower-priority visual debt, not a blocker for rules testing: the first forced Citadel side-sheet tile in session `003f51881ebc417a8a70891da9e0de00` was clipped badly. Investigate side-sheet placement/truncation after the current rule-flow blockers are clear.

## Game 3: Adventures Guild

Enable **TAG fixed-result controls** immediately before this game. Start one generated lead from the family least recently checked.

1. Confirm the selected Rumor, Treasure Map, Thematic Dungeon, or Guild Job is visibly marked as a developer override and the prompt/branch wording matches the extracted local narrative.
2. Follow one branch through an encounter or handoff. Confirm its reward policy: no loot, scene reward, purchase/service, no automatic room loot, or handoff-dungeon loot.
3. Complete its signoff workflow. Confirm route marker, reward, XP, Guild share, and dashboard return work, and no resumable active session remains after closeout.

## Record Failures

For a failure, provide the game number, selected developer scenario, exact foe/result, current map element, action taken, and a Copy Narrative Report. A passing forced encounter proves that selected row only; it does not sign off an entire PDF table.
