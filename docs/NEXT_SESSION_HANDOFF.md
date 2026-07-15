# Next Session Handoff

Last updated: 2026-07-15. Repository branch: `main`. Latest release: `v0.39.17` (`961dae0`).

## Start Here

1. Read `AGENTS.md`, `docs/STATUS.md`, and `docs/PLAYTEST_PLAN.md` before changing code.
2. Treat the owned Rules PDFs as the source of truth for every rule. Quote the PDF page/topic when a rule is ambiguous. Do not silently invent a rule or discard player rewards.
3. The Docker app runs on Unraid at `http://192.168.1.55:8001`; user-visible persistent data is under `\\TOWER\appdata\ahazi-against-darkness`.
4. Do not mutate `game.db` directly unless necessary to repair a live blocker; make a timestamped backup beside it first.

## Current Priority: Finish Blocking Fix Validation

The previous playtest exposed a real camp/re-entry failure after developer-forced encounters. `v0.39.17` fixes it by storing `SessionState.entrance_tile_id`, recovering it for legacy sessions from the marked dungeon exit, and anchoring camp actions to that entrance rather than a stale saved-room location.

Before further modularisation, ask the user to deploy `v0.39.17`, force-refresh, and complete the **No New Game Needed** section of `docs/PLAYTEST_PLAN.md`:

- Resume the current EE + Abyss session. It must open at Entrance Map Element 06, not Map Element 32.
- Camp, refresh, then re-enter. The dungeon entrance and exits must remain usable.
- Return to camp and abandon the unfinished dungeon after resolving its one pending Classical XP roll. A Final Boss is not required for abandonment; pending XP, pending spell selection, and prisoner reward choices intentionally block closeout so earned rewards are never silently lost.
- Confirm the recovery redesign has not left stray body/recovery controls in Party Sheets.

The current live session id was `2b51e57ab5cd4623942fbef9b65b30d3` when this note was written. It may be complete by the time this handoff is read.

## Remaining Playtests

After the blocking check passes, continue the minimum-game plan in `docs/PLAYTEST_PLAN.md`:

1. Disposable EE + Abyss game: force Dragon Man. Optional natural fallen-hero recovery check only.
2. Disposable Forsaken Depths game: named foe families, one Citadel, save/reload side-sheet state, and one quest path where offered.
3. One TAG generated lead with TAG fixed-result controls enabled only for that game; verify prompt wording, reward policy, signoff, and no active session after closeout.

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
