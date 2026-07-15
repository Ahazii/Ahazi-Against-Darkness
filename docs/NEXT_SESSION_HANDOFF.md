# Next Session Handoff

Last updated: 2026-07-15. Repository branch: `main`. Latest release: `v0.39.17` (`961dae0`).

## Start Here

1. Read `AGENTS.md`, `docs/STATUS.md`, and `docs/PLAYTEST_PLAN.md` before changing code.
2. Treat the owned Rules PDFs as the source of truth for every rule. Quote the PDF page/topic when a rule is ambiguous. Do not silently invent a rule or discard player rewards.
3. The Docker app runs on Unraid at `http://192.168.1.55:8001`; user-visible persistent data is under `\\TOWER\appdata\ahazi-against-darkness`.
4. Do not mutate `game.db` directly unless necessary to repair a live blocker; make a timestamped backup beside it first.

## Current Priority: Deploy Follow-up Patch, Then Resume Game 2

The previous playtest exposed a real camp/re-entry failure after developer-forced encounters. `v0.39.17` fixes it by storing `SessionState.entrance_tile_id`, recovering it for legacy sessions from the marked dungeon exit, and anchoring camp actions to that entrance rather than a stale saved-room location.

Follow-up player testing then exposed two smaller UI blockers: after spending the last pending Classical XP roll, the entrance **Complete / abandon** choice could remain dimmed until a hard refresh; and Forsaken Depths Game 2 showed `Supplements: 3` but no FD developer force controls. That patch made closeout use the latest in-memory session and made both frontend/backend FD recognition supplement-snapshot aware. Later Game 2 evidence confirmed the controls appear and Infallible Missile's Level 8+ second missile works, but exposed FD p.40/p.42 gaps: Deep Trolls did not revive/roll treasure at -1, Horde of Dark Elves lacked its printed FD treasure roll, FD debug context said inactive, and FD minions could tick the Abyss minion XP track in an Abyss+FD session. The next feedback confirmed the Deep Troll chip and Hack button appeared, but a newly slain body could still return after hacking; hacking now blocks the next return for the whole active Deep Troll group. FD p.62 treasure choices also now appear directly in Current Objective.

Before further modularisation, ask the user to deploy the latest `main` build, force-refresh, and complete the updated **No New Game Needed** / **Game 2 Forsaken Depths** checks in `docs/PLAYTEST_PLAN.md`:

- Resume the current EE + Abyss session. It must open at Entrance Map Element 06, not Map Element 32.
- Camp, refresh, then re-enter. The dungeon entrance and exits must remain usable.
- Return to camp and abandon the unfinished dungeon after resolving any pending Classical XP roll. A Final Boss is not required for abandonment; pending XP, pending spell selection, and prisoner reward choices intentionally block closeout so earned rewards are never silently lost. After XP is resolved, the completion choice must enable without a browser hard refresh.
- Confirm the recovery redesign has not left stray body/recovery controls in Party Sheets.
- Resume Forsaken Depths Game 2 if still active. First force **FD foe encounter -> Minions -> Deep Trolls** once to confirm Hack prevents the next slain-troll return for the whole active group, FD treasure at `-1`, and ordinary minor XP wording. Then select **FD foe encounter -> Citadel Weird** in the named foe dropdown for the next forced foe.

The current live session id was `2b51e57ab5cd4623942fbef9b65b30d3` when this note was written. It may be complete by the time this handoff is read.

## Remaining Playtests

After the blocking check passes, continue the minimum-game plan in `docs/PLAYTEST_PLAN.md`:

1. Disposable Forsaken Depths game: Deep Troll regression, one Citadel-Weird from the FD foe selector, one Citadel, save/reload side-sheet state, and one quest path where offered.
2. One TAG generated lead with TAG fixed-result controls enabled only for that game; verify prompt wording, reward policy, signoff, and no active session after closeout.

Completed checks should not be repeated unless a new change reopens them. In particular, Ant People, Dark Plague, Ghoul King Elf `+Level` save/Blessing cure, treasure cap/claiming, Shrieking Fungi, Flying Skulls, Phasing Panther, and Tentacled Brain already have recorded evidence. Ghoul King's automatic hit after a failed paralysis save remains passive future evidence, not a reason to force repeated encounters.

## Modularisation Direction After Playtests

The project has already extracted reusable lifecycle modules for adventure completion, combat lifecycle, treasure claims, Quest transactions, healing potions, and manifest-backed supplement/catalogue ownership. Do not resume broad refactoring until the active exit/camp regression is proven on the deployed container.

Then choose one bounded shared runtime responsibility from `docs/STATUS.md`/`docs/ROADMAP.md`, preserve existing API/UI behaviour, add focused tests, and update `STATUS.md`, `PLAYTEST_PLAN.md`, Rules Reference, and Tables List whenever player-visible rules change. Keep review/import packages declarative until a validated promotion explicitly creates trusted runtime content.

## Recent Releases

- `v0.39.17` / `961dae0`: stable camp entrance identity and closeout repair.
- `v0.39.16` / `c834f935`: recovery controls moved into a compact draggable dialog.
- `v0.39.15` / `94e5b16`: fallen transfer dialog and Ghoul King Elf `+Level` save correction.
- `v0.39.14` / `22d5f3e1`: Abyss encounter-effect fidelity pass.

## Verification and Delivery

Use `apply_patch` for edits. Run focused tests plus `node --check src/app/static/app.js` for frontend work and `git diff --check` before committing. Commit and push substantial Docker changes to `main`; tell the user the exact version and Unraid tests to perform.
