# Next Session Handoff

Last updated: 2026-07-18. Repository branch: `main`. Latest release: `v0.39.32`.

## Start Here

1. Read `AGENTS.md`, `docs/STATUS.md`, and `docs/PLAYTEST_PLAN.md` before changing code.
2. Treat the owned Rules PDFs as the source of truth for every rule. Quote the PDF page/topic when a rule is ambiguous. Do not silently invent a rule or discard player rewards.
3. The Docker app runs on Unraid at `http://192.168.1.55:8001`; user-visible persistent data is under `\\TOWER\appdata\ahazi-against-darkness`.
4. Do not mutate `game.db` directly unless necessary to repair a live blocker; make a timestamped backup beside it first.

## Current Priority: Deploy TAG Scene-Chain Patch, Then Resume Game 3

The previous playtest exposed a real camp/re-entry failure after developer-forced encounters. `v0.39.17` fixes it by storing `SessionState.entrance_tile_id`, recovering it for legacy sessions from the marked dungeon exit, and anchoring camp actions to that entrance rather than a stale saved-room location.

Follow-up player testing then exposed two smaller UI blockers: after spending the last pending Classical XP roll, the entrance **Complete / abandon** choice could remain dimmed until a hard refresh; and Forsaken Depths Game 2 showed `Supplements: 3` but no FD developer force controls. That patch made closeout use the latest in-memory session and made both frontend/backend FD recognition supplement-snapshot aware. Later Game 2 evidence confirmed the controls appear and Infallible Missile's Level 8+ second missile works, but exposed FD p.40/p.42 gaps: Deep Trolls did not revive/roll treasure at -1, Horde of Dark Elves lacked its printed FD treasure roll, FD debug context said inactive, and FD minions could tick the Abyss minion XP track in an Abyss+FD session. The next feedback confirmed the Deep Troll chip and Hack button appeared, but a newly slain body could still return after hacking; hacking now blocks the next return for the whole active Deep Troll group. FD p.62 treasure choices also now appear directly in Current Objective. The latest FD Citadel reports confirmed first-room-only side-sheet reveal and save/reload restoration, then exposed FD p.38 vermin gaps, a stale Citadel marker after returning to main-map Tile 41 in session `f0ab5c80eee34a9c9cec7b3e95484823`, and missing Greater Mutated Goblin handling. Named inline FD reactions now resolve, `never_test_morale` suppresses morale on attack-immediate, Spore Spiders have structured 4-in-6 surprise, Deep Cave Spiders reduce remaining spiders by 1 Level per two killed to minimum L3, movement/normalization clear stale side-sheet markers when the party is back on the non-side-sheet origin, and Greater Mutated Goblin now follows the FD p.41 row: Tier damage, fixed loot, corrosive mucus with flee/Defense/damage effects, Blessing/goblin-defeat cleanup, and -1 reactions when the party includes a goblin. Follow-up evidence then showed the backend side sheet was already inactive (`Side sheet: none; active=false; origin=none`) while the frontend still displayed the remembered Citadel label on main-map Tile 41; the Citadel badge/debug line now require an active Citadel side sheet. The next deploy proved the stale badge is gone, but a new EE+Abyss+FD disposable session showed Soulbinding and Citadel routing blockers: the backend correctly added `FD Soulbound:<tile id>` and later UI showed Life/Madness choices, but Blessing did not free the hero; the first Citadel room also had an unclear route with no obvious return/re-entry path. FD p.58 says Soulbinding lasts until Blessing frees the character, so Blessing now removes the Soulbound status, clears pending Soulbinding choices, and logs the cure. Citadel side-sheet routes now repair on resume and are labelled **Enter Citadel sheet** / **Return to main map**; returning to the origin clears only the active marker and preserves the route so the party can re-enter the Citadel. v0.39.20 also fixes the origin **Enter Citadel sheet** action for already-used entries and adds **Explore deeper into Citadel/Ruins/Dark Pits** while the side-sheet room budget remains, creating a side-sheet passage when clipped tile geometry leaves only the return route visible. The Citadel route playtest passed save/dashboard/resume, return-to-main-map, and deeper-room generation, then exposed that Armored Forsaken Depths Troll was missing FD p.44 HCL-1 Magic Resistance and 4-in-6 non-magical blow deflection. v0.39.21 records and applies those rules, and later live evidence confirmed the deflection rolls fire for non-magical weapon hits. The same report showed Dark Elf Warlock still using two generic attacks instead of FD p.44's staff-plus-ice-blast split; v0.39.24 changes the Warlock to one normal staff attack plus a separate ice blast Defense roll where shields count, armor is ignored, failed targets lose 2 Life, and barbarians/Ice-based characters add +1/2 L. v0.39.25 adds character-sheet gender dropdowns and uses them for the printed Warlock priority: female elves/female spellcasters, then other female heroes. Spore coughing and Deep Cave character-death spawn/no-resurrection remain future fidelity hooks.

Before further modularisation, ask the user to deploy the latest `main` build, force-refresh, and complete the updated **Game 3: Adventures Guild** check in `docs/PLAYTEST_PLAN.md`:

- Resume the current EE + Abyss session. It must open at Entrance Map Element 06, not Map Element 32.
- Camp, refresh, then re-enter. The dungeon entrance and exits must remain usable.
- Return to camp and abandon the unfinished dungeon after resolving any pending Classical XP roll. A Final Boss is not required for abandonment; pending XP, pending spell selection, and prisoner reward choices intentionally block closeout so earned rewards are never silently lost. After XP is resolved, the completion choice must enable without a browser hard refresh.
- Confirm the recovery redesign has not left stray body/recovery controls in Party Sheets.
- Start a fresh generated Adventures Guild lead with TAG fixed-result controls and force Rumor 1, **Bofto's Star-Shaped Find**. v0.39.32 fixes the previous Bofto failures: extracted Scene 9 branch choices should be visible without using signoff, clicking Scene 17 should move to a real Scene 17 prompt with PDF-derived text, reaching Scene 9 should not complete the quest by itself, generated scene-chain exits now match the native tile portals/kinds used by tiles 11 and 13, PDF routing text such as `go to Scene 9` is hidden behind player-facing choice buttons, entering Scene 9 logs the cleaned PDF scene prose rather than the old resolution instruction, route clicks no longer add `TAG route:` debug chatter to the player Narrative, and Scene 17 offers **Insist on investigating** / **You choose to leave** instead of generic **Mark scene resolved** / **Apply scene reward** controls. All wider Game 2 FD checks have enough evidence and should not be repeated unless a later regression reopens them. Armored Troll HCL-1 MR remains passive evidence if an offensive spell is naturally cast at one.

The current live session id was `2b51e57ab5cd4623942fbef9b65b30d3` when this note was written. It may be complete by the time this handoff is read.

## Remaining Playtests

After the blocking check passes, continue the minimum-game plan in `docs/PLAYTEST_PLAN.md`:

1. One TAG generated lead with TAG fixed-result controls enabled only for that game; verify Bofto generation succeeds, rumour framing, investigate/ignore entry, cleaned Scene 9 Narrative log with no `TAG route:` line, hidden scene-routing text, Scene 9 branch wording, Scene 17 movement/text/buttons, scene-resolved completion, signoff, and no active session after closeout.
2. Optional only if time allows: one non-Rumor generated lead smoke check for first-prompt clarity.

Completed checks should not be repeated unless a new change reopens them. In particular, Ant People, Dark Plague, Ghoul King Elf `+Level` save/Blessing cure, treasure cap/claiming, Shrieking Fungi, Flying Skulls, Phasing Panther, and Tentacled Brain already have recorded evidence. Ghoul King's automatic hit after a failed paralysis save remains passive future evidence, not a reason to force repeated encounters.

## Modularisation Direction After Playtests

The project has already extracted reusable lifecycle modules for adventure completion, combat lifecycle, treasure claims, Quest transactions, healing potions, and manifest-backed supplement/catalogue ownership. Do not resume broad refactoring until the active exit/camp regression is proven on the deployed container.

Then choose one bounded shared runtime responsibility from `docs/STATUS.md`/`docs/ROADMAP.md`, preserve existing API/UI behaviour, add focused tests, and update `STATUS.md`, `PLAYTEST_PLAN.md`, Rules Reference, and Tables List whenever player-visible rules change. Keep review/import packages declarative until a validated promotion explicitly creates trusted runtime content.

## Recent Releases

- `v0.39.32`: TAG scene-chain route clicks no longer log `TAG route:` debug chatter, and extracted terminal scene prompts use player-facing choices such as **Insist on investigating** / **You choose to leave** instead of generic resolution/reward buttons.
- `v0.39.31`: TAG scene-chain room-entry triggers now log cleaned extracted Scene prose instead of old fallback resolution instructions.
- `v0.39.30`: TAG rumor-generated leads split player-facing rumour/scene prose from hidden `go to Scene` routing and expose investigate/ignore choice buttons.
- `v0.39.29`: TAG scene-chain generated leads now use native-valid scene exits and legacy imported-session repair ignores manifest-only orphan rooms.
- `v0.39.28`: TAG scene-chain generated leads now use extracted Scene rooms/buttons and complete only after explicit scene resolution.
- `v0.39.27`: FD p.62 row 7 bow branch now claims as one Masterwork bow plus 24 silver-tipped arrows bundle.
- `v0.39.26`: FD Event schema fix and FD p.62 treasure-row developer forcing.
- `v0.39.25`: Character gender dropdowns and Dark Elf Warlock female-priority targeting.
- `v0.39.24`: Dark Elf Warlock staff-plus-ice-blast combat split.
- `v0.39.23`: Concrete weapon choices for Greater Mutated Goblin fixed loot, FD silvered melee bundles, and Abyss non-magical weapon treasure.
- `v0.39.22`: FD p.62 concrete masterwork weapon choices and FD Event developer override.
- `v0.39.21`: FD Armored Forsaken Depths Troll HCL-1 Magic Resistance and 4-in-6 armor deflection.
- `v0.39.20`: FD Citadel origin re-entry and deeper side-sheet room action.
- `v0.39.19`: FD Soulbinding Blessing cure and labelled Citadel side-sheet routes.
- `v0.39.17` / `961dae0`: stable camp entrance identity and closeout repair.
- `v0.39.16` / `c834f935`: recovery controls moved into a compact draggable dialog.
- `v0.39.15` / `94e5b16`: fallen transfer dialog and Ghoul King Elf `+Level` save correction.
- `v0.39.14` / `22d5f3e1`: Abyss encounter-effect fidelity pass.

## Verification and Delivery

Use `apply_patch` for edits. Run focused tests plus `node --check src/app/static/app.js` for frontend work and `git diff --check` before committing. Commit and push substantial Docker changes to `main`; tell the user the exact version and Unraid tests to perform.
