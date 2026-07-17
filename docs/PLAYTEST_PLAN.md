# Current Playtest Plan

Last updated: 2026-07-18. Target build: v0.39.32 TAG scene-choice cleanup.

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

## Must Do Next

1. Deploy v0.39.32 or later and force-refresh until the app header shows that build.
2. Start a fresh **Game 3: Adventures Guild** generated lead with TAG fixed-result controls enabled. Choose Rumor 1, **Bofto's Star-Shaped Find**.
3. Confirm the generated lead uses the local PDF scene text, not generic filler: the opening should frame Bofto as a rumour, ask **Do you investigate?**, and show **Choose to investigate** / **Don't investigate** buttons. After choosing investigate, the Narrative should log the cleaned Scene 9 star-object prose, not the old `Choose the Scene 9 resolution...` instruction and not a `TAG route:` debug line.
4. Click the Scene 17 branch. Confirm the party moves to a real **Scene 17** room/prompt with the PDF-derived family text, no visible `playing Scene 9` routing instruction, and only **Insist on investigating** / **You choose to leave** action buttons. **Insist on investigating** must return to Scene 9; **You choose to leave** ends the module.
5. Complete generated-lead closeout and confirm the signoff panel records route/reward/XP/Guild/banking review without leaving a resumable active session.
6. If Bofto passes, run one small non-Rumor generated lead smoke check only if time allows: generate either one Treasure Map or one Guild Job and confirm its first prompt/action wording is understandable. Do not restart broad FD/adventure testing unless this v0.39.32 TAG repair fails.
7. After the TAG scene-chain check passes, stop adventure regression testing for now and resume modularisation only in small tested slices.

## Passed: Game 2 Forsaken Depths

Latest evidence copied 2026-07-17 for disposable session `003f51881ebc417a8a70891da9e0de00`: the FD p.62 row 3 developer-forced treasure path offered the printed gold/masterwork choice, accepted a concrete Masterwork sword choice, and awarded the exact weapon. FD p.62 row 7 offered the printed branches and the silvered melee weapon path accepted a concrete sword choice. The bow branch was patched in v0.39.27 to award one bundled `Masterwork bow with 24 silver-tipped arrows` item rather than split bow/arrows across different heroes. Do not repeat Game 2 unless this exact bow bundle appears broken in later incidental play.

The same report forced FD Event `d10 = 6 - Earthquake`: the Narrative logged FD p.63, each hero rolled `d3` falling stones, each stone made a Save vs HCL 10, and each failed Save cost exactly 1 Life. Dark Elf Warlock then showed the v0.39.24/25 combat correction live: one ordinary staff attack plus one separate ice blast per round, ice blast logs FD p.44, armor is ignored, and failed ice saves cost 2 Life. The Warlock targeted Faelar Sunshadow in the supplied run, matching the intended female-priority check if Faelar's character-sheet gender was set to Female.

Do not repeat these passed Game 2 checks unless a later deploy visibly reopens one:

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
- FD p.62 row 3 concrete masterwork choice, row 7 concrete silvered melee choice, FD Event override, Earthquake, and Dark Elf Warlock staff/ice-blast split have live evidence.

### Passive Future Evidence

- If a fresh Soulbinding trap naturally appears later, move away once and confirm the **Lose 1 Life** / **Gain 1 Madness** buttons appear before continuing.
- If Spore Spiders naturally produce melee kills, confirm coughing checks accumulate correctly and magical healing before encounter end prevents the loss.
- If Deep Cave Spiders naturally kill a character, confirm they immediately spawn another 2d6 Deep Cave Spiders and the slain character cannot be resurrected.
- If a hero naturally falls while carrying Clues, a Secret, or valuable items, reuse the Game 1 passive recovery checklist instead of manufacturing a death.
- If Ghoul King naturally appears again, the remaining passive Abyss check is the automatic-hit-after-failed-save outcome.
- Record as lower-priority visual debt, not a blocker for rules testing: the first forced Citadel side-sheet tile in session `003f51881ebc417a8a70891da9e0de00` was clipped badly. Investigate side-sheet placement/truncation after the current rule-flow blockers are clear.

## Game 3: Adventures Guild

Enable **TAG fixed-result controls** immediately before this game. v0.39.32 focuses on Rumor 1 because the previous runs proved the app had the extracted Scene text but first hid the branch buttons/completed too early, then generated scene exits that did not match native tile portals, then exposed PDF routing text directly to the player, then logged old resolution/debug instructions instead of clean player-facing scene prose.

1. Force Rumor 1, Bofto's Star-Shaped Find. Confirm the opening is framed as a rumour and Scene 9 is a choice scene, not quest completion.
2. Follow Scene 17 from the visible branch button. Confirm the target scene room/prompt uses the local PDF-derived text and offers only **Insist on investigating** and **You choose to leave**.
3. Resolve/close out from the scene prompt. Confirm route marker, reward/XP/Guild/banking signoff, and dashboard return work, and no resumable active session remains after closeout.

## Record Failures

For a failure, provide the game number, selected developer scenario, exact foe/result, current map element, action taken, and a Copy Narrative Report. A passing forced encounter proves that selected row only; it does not sign off an entire PDF table.
