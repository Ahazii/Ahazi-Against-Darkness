# Next Session Handoff

Last updated: 2026-07-23. Repository branch: `main`. Latest release: `v0.39.42`.

## Start Here

1. Read `AGENTS.md`, `docs/STATUS.md`, `docs/PLAYTEST_PLAN.md`, and `docs/ROADMAP.md` before changing code.
2. Treat the owned Rules PDFs as the source of truth. Quote the PDF page/topic when a rule is ambiguous; do not infer dice procedures or branch results from generic prose.
3. The Docker app runs on Unraid at `http://192.168.1.55:8001`. User-visible persistent data belongs under `\\TOWER\appdata\ahazi-against-darkness`.
4. Do not alter `game.db` directly without first making a timestamped backup beside it.

## Current Priority

Ask the user to deploy `v0.39.42`, force-refresh, and run only the short checks at the top of `docs/PLAYTEST_PLAN.md`:

1. At camp, use **Apply** beside Sir Benedict's Gremlin Repellant and protect one specific loose item or Bag.
2. Run one ordinary Invisible Gremlins event with save/resume while the theft count is pending.
3. Run a Disbelief reveal only if a disposable caster is available.

Campaign/Rumor Continuity and all Developer Grant/Two Bags checks are passed. Do not repeat them or reopen the broad EE, Abyss, Forsaken Depths, Citadel, or earlier Bofto/Star-Slayer suites. When the ordinary Gremlin check passes, stop adventure testing and resume modularisation in one small tested slice.

## Implemented In v0.39.42

Rules sources: Expanded Edition pp.38, 44-46, 62, 74, 87, 105, 107, 160, and 169; TAG pp.11, 13, 22, 29-31, and 65.

- Party Sheets place **Apply** beside each carried Gremlin Repellant. At camp it opens the printed p.87 item/Bag protection picker; when unavailable the button remains visible but disabled with the exact timing or eligibility reason.
- The generic character Actions copy of Repellant application is removed. Potions and scrolls remain unchanged pending a later reusable item-action slice.
- Party Sheets Bag packing no longer raises on stale transfer-only variables. The selected loose item is persisted in the selected Bag's stable container.
- The developer item dropdown no longer rebuilds and resets to the first search result when the player chooses another item. Filter rebuilds preserve the current selection when possible.
- Developer grants now honor both saved default supplements and the selected supplement snapshot of each character's unfinished sessions. This fixes TAG p.13 Bags being absent when TAG was selected for the live session but was not a saved default.
- Developer Playtest Preferences can expose a password-gated item grant panel sourced from enabled supplements. It grants only inventory-safe concrete items, enforces class/carry restrictions, creates real Bag identities, synchronizes active sessions, and logs the override.
- Campaign and Rumor Continuity passed on v0.39.37 and is removed from the remaining live plan.
- Bofto Scene 18/19 no longer disappears behind an immediate generic completion summary. Its named-character roll outcome remains in Narrative with a persisted **Continue** action; save/dashboard/resume preserves the acknowledgement state and only Continue opens normal closeout.
- `SessionState.campaign_id` pins a session to its campaign. Star-object recovery/effects and Rumor lifecycle records are stored in that `CampaignState`, so switching the active dashboard campaign cannot redirect an existing session's state.
- Rumors progress through heard, investigating, and resolved. Random Rumor generation rerolls resolved results within the same campaign; the fixed developer selector deliberately permits exact replay.
- Bofto Scene 14 uses the reusable typed action contract in `tag_scene_actions.py` for actor requirement, modifiers, L6 threshold, one-attempt rule, and automatic Scene 18/19 outcomes. Other TAG scenes are not guessed from prose; convert them source-by-source.
- Every Bag of Carrying has a stable id and explicit contents. Multiple Bags persist independently through character/session sync, save/resume, transfer, capture, death, and loss. A stolen/lost Bag loses its contents, Barbarians will not carry one, Bags cannot nest, cursed objects cannot be stored, and non-empty Bags cannot be sold accidentally.
- Invisible Gremlins are a persisted event rather than a normal foe. They roll `d6+3` theft slots, use the printed item priority, count once toward Major Foes, cannot be a Final Boss, and are rerolled as a Wandering Monster result.
- Gremlin Repellant protects one selected item for one adventure. Miners' Ointment remains the separate ignore-next-Wandering-Monsters/Gremlins effect. TAG Resurrection/Blessing tags and weapons under Temporary Weapon Enchantment are offered only as explicit voluntary choices during the ordinary event. Revealed Gremlins and Iron Eaters ask whether each temporarily enchanted weapon is eligible for their normal loss effect; the encounter choice persists through save/resume (TAG pp.11, 65).
- Disbelief reveals `d6+1` L3 Minions with Morale -1, one attack, and one group Treasure roll. A failed Defence steals an eligible item instead of causing Life loss.
- Rules Reference, Tables List, State Registry, Party Sheets, developer controls, modern campaign workflow summary, hover text, docs, and focused tests cover the new state.

## Persistence Model

Campaign and saved game remain separate records in the same user-facing `DATA_DIR/game.db`. The session stores `campaign_id`; campaign-owned effects and Rumor records live in the matching campaign record. Character Bags and their contents live on the character and are copied into/out of the active session by the existing roster sync. No second campaign-save file is required.

## Testing Boundary

Automated tests own campaign isolation and legacy migration, all twelve Rumors exhausted, exact Gremlin priority/Clue/Kukla/Clockwork Armor edges, Star-Slayer replacement, carrier death, total-party-kill recovery, and mixed-result split fleeing. Do not risk a valuable live party to force those dice.

After the `v0.39.42` gate, resume the item-disposition policy modularisation slice. Keep it narrow: consolidate eligibility and container-aware removal behavior without reorganising `random_dungeon.py`. Then migrate other generated TAG scenes onto typed action definitions one PDF-backed module at a time.

Temporary Weapon Enchantment's p.65 theft/destruction decision is automated. Its one-week or qualifying-use expiry remains on the existing manual **Guild marker** clear control and is a bounded later TAG spell task, not part of the release gate.

## Recent Releases

- `v0.39.42`: contextual Party Sheets Apply action for Gremlin Repellant; all Bag tests recorded passed.
- `v0.39.41`: Party Sheets persists item packing into the selected Bag of Carrying.
- `v0.39.40`: stable developer item dropdown selection after filtering.
- `v0.39.39`: developer grants honor active-session supplement snapshots as well as saved defaults.
- `v0.39.38`: enabled-supplement developer inventory grants with class/carry enforcement and live-session synchronization.
- `v0.39.37`: persisted readable Bofto Scene result with explicit Continue before adventure closeout.
- `v0.39.36`: campaign-scoped TAG effects/Rumors, typed Bofto action, explicit multi-Bag contents, and complete Invisible Gremlins procedure.
- `v0.39.35`: Bofto Scene 19 extraction/automation and persistent star-object curse lifecycle.
- `v0.39.34`: Scene 14 requires a selected thief on every UI/API path.
- `v0.39.33`: Scene 14 rolls the printed L6 theft Save and routes automatically.
- `v0.39.32`: scene-route debug chatter removed; Scene 17 receives player-facing choices.
- `v0.39.17` / `961dae0`: stable camp entrance identity and closeout repair.

## Verification And Delivery

Run focused and full Python tests, `node --check` for both UI scripts, JSON parsing, Python compilation, and `git diff --check`. Commit and push substantial Docker changes to `main`; report the exact release and only the remaining Unraid checks.
