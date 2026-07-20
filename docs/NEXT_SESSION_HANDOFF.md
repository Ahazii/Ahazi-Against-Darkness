# Next Session Handoff

Last updated: 2026-07-20. Repository branch: `main`. Latest release: `v0.39.35`.

## Start Here

1. Read `AGENTS.md`, `docs/STATUS.md`, `docs/PLAYTEST_PLAN.md`, and `docs/ROADMAP.md` before changing code.
2. Treat the owned Rules PDFs as the source of truth. Quote the PDF page/topic when a rule is ambiguous; do not invent a rule or discard a reward.
3. The Docker app runs on Unraid at `http://192.168.1.55:8001`. User-visible persistent data belongs under `\\TOWER\appdata\ahazi-against-darkness`.
4. Do not alter `game.db` directly without first making a timestamped backup beside it.

## Current Priority

Ask the user to deploy `v0.39.35`, force-refresh, and run only the remaining checks at the top of `docs/PLAYTEST_PLAN.md`.

The blocking path is a fresh TAG Rumor 1, **Bofto's Star-Shaped Find**, successful Scene 14 theft followed by automatic Scene 19 resolution. Confirm the Narrative ends with the Scene 19 curse material rather than absorbing **Following the Treasure Map Table** and later book sections. The selected thief must make the printed L8 Will Save automatically, receive the persistent cursed item after either outcome, and reach the normal adventure-complete summary without stale manual Will/Star-Slayer controls.

Then run the three focused curse checks: voluntary transfer/sale/storage is blocked; Developer **TAG Star-Slayer curse encounter** follows the TAG pp.30-31 profile and awards exactly two XP rolls; Developer **TAG Invisible Gremlins curse encounter** asks whether to keep or release the object, with explicit release bypassing protection and ending the curse.

If old session `b47cac2be0eb4977b52e5eb19172d4d5` still exists, resume it once as a compatibility check. Its oversized Scene 19 prompt/Narrative should trim before **Following the Treasure Map Table** and stale Bofto controls should be removed. Skip it if already completed or deleted.

## Implemented In v0.39.35

Rules source: `Tales_from_the_adventurers_guild.pdf`, Scene 19 and Star-Slayer, printed pp.30-31.

- Scene 19 PDF extraction has a structural end boundary and strips the trailing illustration caption. Resume-time compatibility repair trims affected manifests, room triggers, prompts, and saved Narrative lines.
- A successful Scene 14 theft assigns the object to the selected thief, resolves the L8 Will Save with Spellcaster/Cleric +Level and one Halfling failure reroll, applies Madness on failure, and closes the generated module.
- The curse persists after either Will result. Blessing and magic do not remove it, and voluntary transfer/drop/store/sale plus generic equipment-loss paths cannot discard it.
- Carrier death transfers the object automatically. A total party kill stores campaign recovery state; each later claimed treasure receives the printed 1-in-6 check until a living character is assigned the recovered object.
- Each encountered Boss/Weird receives one 2-in-6 replacement check while the curse operates. Star-Slayer is HCL+6 with HCL+5 Life, four Tier-damage attacks, no ordinary treasure, and always fights to the death.
- On sight, every living hero Saves vs HCL+1 or gains 1 Madness and loses 2 Life. Heroes who gained Madness cannot flee; successful savers may flee as a split group.
- A Star-Slayer replacing a Final Boss retains that Boss's treasure. Any defeated Star-Slayer awards exactly two XP rolls, including when it replaced a Final Boss, and never breaks the curse.
- Invisible Gremlins present a player choice. **Let them take the cursed object** bypasses Gremlin protection and clears the curse; **Keep the cursed object** follows ordinary protection/theft handling.
- State Registry, supplement capabilities, Tables List, Rules Reference, item hover text, developer controls, and focused tests cover the new state and procedure.

## Testing Boundary

Do not reopen broad EE, Abyss, Forsaken Depths, Citadel, or earlier Bofto Scene 9/14/17 testing. Those passes are retained in `docs/STATUS.md`. Full death/TPK recovery, Final Boss treasure retention, mixed-result split fleeing, and generic loss protection have automated coverage and do not justify risking a valuable live party.

After the remaining v0.39.35 checks pass, stop adventure regression testing and resume modularisation in one small tested runtime slice at a time. Preserve current API/UI behavior, update Rules Reference and Tables whenever a player-visible rule changes, and keep imported/review packages declarative until explicitly promoted.

## Recent Releases

- `v0.39.35`: Bofto Scene 19 extraction/automation and complete persistent star-object curse lifecycle.
- `v0.39.34`: Scene 14 requires a selected thief on every UI/API path; stale terminal-scene shortcuts removed.
- `v0.39.33`: Scene 14 rolls the printed L6 theft Save and routes automatically.
- `v0.39.32`: scene-route debug chatter removed; Scene 17 receives player-facing choices.
- `v0.39.31`: scene entry logs cleaned extracted prose.
- `v0.39.30`: rumour/scene prose separated from hidden route instructions.
- `v0.39.29`: generated scene exits use native-valid tile portals.
- `v0.39.28`: extracted Scene rooms/buttons and explicit scene completion.
- `v0.39.17` / `961dae0`: stable camp entrance identity and closeout repair.

## Verification And Delivery

Run focused Python tests, `node --check src/app/static/app.js`, JSON parsing, Python compilation, and `git diff --check`. Commit and push substantial Docker changes to `main`; report the exact release and only the remaining Unraid checks.
