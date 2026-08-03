# Next Session Handoff

Current release is **v0.39.67**. The v0.39.66 Rumor 9 Streetwise, defer, reward,
XP, and closeout procedure passed; do not regenerate or replay it. v0.39.67 is a
bounded presentation correction: new and resumed Scene 5 narrative consistently
states the player-confirmed 200gp TAG p.24 offer, while copied Narrative Reports
label carried, banked, and total gold separately. The conflicting 100gp line in
Scene 5 on p.26 remains documented as the known source error. Deploy,
force-refresh, and perform only the non-mutating presentation check in
`docs/PLAYTEST_PLAN.md`.

Last updated: 2026-08-03. Repository branch: `main`. Latest release: `v0.39.67`.

## Start Here

1. Read `AGENTS.md`, `docs/STATUS.md`, `docs/PLAYTEST_PLAN.md`, and `docs/ROADMAP.md` before changing code.
2. Treat the owned Rules PDFs as the source of truth. Quote the PDF page/topic when a rule is ambiguous; do not infer dice procedures or branch results from generic prose.
3. The Docker app runs on Unraid at `http://192.168.1.55:8001`. User-visible persistent data belongs under `\\TOWER\appdata\ahazi-against-darkness`.
4. Do not alter `game.db` directly without first making a timestamped backup beside it.

## Current Priority

All earlier broad adventure test gates, including the v0.39.66 Rumor 9
procedure, are passed. The only open live check is v0.39.67's non-mutating
Scene 5/report presentation check. Do not ask the user to repeat the
Invisible Gremlins fight or reopen the broad EE, Abyss, Forsaken Depths,
Citadel, Bofto, Star-Slayer, Bag, Repellant, treasure, trap, entrance, or
closeout suites.

The v0.39.53 Rumor 2 Quest closeout gate passed. Session
`1b417a50983c4329b4f2b1aead6cf76d` is complete with `9gp`, no active Quest,
no pending generated closeout, and the roster saved. Do not repeat Scene 10,
the Xasartha Quest reaction, payment, Epic Reward, or closeout.

v0.39.54 completes the bounded TAG pp.25-27 Xasartha Scene 1/6 slice in
focused automation. v0.39.55 completes TAG p.65 Temporary Weapon Enchantment
timing without reopening the passed Gremlin/Iron Eater decisions. v0.39.56
introduced Daroc's typed town-Clue spend/reward resolver; v0.39.66 completes
its TAG pp.20, 24, and 26 search, defer, reward, and required-lifecycle flow.
v0.39.57 restores generated Rumor entry choices to the bottom of
Narrative without internal Director/playbook prose. v0.39.58 keeps multiple
Rumor entry choices side by side at normal app widths. v0.39.59 converts TAG
p.29 Scene 12 into one typed Mutant Fish hypnosis, rescue, ration, sale, and XP
procedure. Do not repeat the whole Rumor 2 module or any Gremlin fight.

## Implemented Through v0.39.67

Rules sources: Expanded Edition pp.38, 44-46, 62, 74, 87, 94, 101, 105, 107, 160, 162, and 169; TAG pp.6-8, 11, 13, 20, 22, 24-31, and 65.

- Required generated-TAG terminal actions use the canonical **Continue — return to town and finish** wording across Narrative, diagnostics, compact header chip, and primary action. The full action remains visible when the optional Objective Details preference is collapsed, while save/resume normalizes legacy wording without changing or rerolling the resolved scene.
- Mutant Fish Under the Bridge runs as one persisted TAG p.29 Scene 12 procedure. Entering the pool automatically rolls every living hero's L5 hypnosis Save once; no player roll button remains. The required-resolution lifecycle prevents completion on arrival, automatically fails chaos-tainted heroes, owns rescue-turn Life loss and rescuer/victim role changes, destroys/persists an all-failed party, rolls `d6+3` Food rations once, records two minor encounters, and offers carrying-aware Keep or campaign-rate Sell choices. Keep/Sell opens the explicit shared closeout pause. `CampaignState.tag_friendly_chaos_cultists` persists the 5gp friendly sale rate for future applicable encounters.
- Existing generated TAG saves synchronize manifest completion policy, duplicated session completion policy, and active quest key on resume. The reported Rumor 4 session at the pool is conservatively reopened only when its earlier completion is the stale arrival marker and the procedure is not terminal; its automatic Saves then persist and cannot reroll.
- The TAG pp.22-31 audit confirms no Rumor is genuinely complete on arrival. Rumors 4 and 9 now use the shared required-scene lifecycle. Rumors 6/11 are next after a shared repeatable vendor/service host and explicit Done action; mandatory procedures, dynamic encounters, and child-dungeon returns must be implemented before enabling the same gate for their other profiles.
- Generated Rumor entry buttons render immediately beneath Narrative for both `tag_*` and manifest-owned `imported_*` quest records, remain visible when Objective Details is hidden, and exclude internal Director phase, lifecycle, and lead-family playbook prose. TAG pp.22-24 shares **Investigate** / **Not now — return to town** across all twelve Rumors; choices remain side by side at normal app widths and wrap only on narrow mobile layouts.
- Narrative objective, Relevant Now, and room metadata share one special-action dispatcher. Rumor-specific typed controls stay separate plug-ins inside the common scene host. Explicit `entry_scene` metadata prevents composite descriptions from misrouting older Rumor 1 modules past Scene 9.
- Daroc's Lost Familiar keeps the player in Scene 5 until a typed terminal result. **Search for Clues** lets the player select the acting character for each automatic TAG p.20 L6 Streetwise check, charges that searcher's `d6` bribe, and persists eligible Town Streetwise Clues and progress across repeat attempts and save/resume. The cost is two or one when the living party includes a Druid, Beastmaster, cat-like hero, or cat animal companion (TAG p.26). **Give up — return to town** is non-permanent: it preserves eligible Clues and returns Rumor 9 to `heard`. Success spends the eligible Clues, gives the separately selected living recipient 200gp, and creates exactly one pending XP roll. The amount follows the TAG p.24 Rumor offer by player ruling; Scene 5's 100gp line on p.26 is a known error. The XP can be assigned or banked during the shared closeout gate. Crucible of Classic Critters pp.11-15 remains the future source for full Beastmaster and animal-companion implementation.
- New and resumed Daroc Scene 5 narrative now states that same 200gp ruling consistently. Narrative Debug Reports list carried, banked, and total gold for every hero, so diagnostics expose bribe deductions even when the hero remains at the 200gp dungeon carry cap. This does not change finance or reward state.
- Temporary Weapon Enchantment records its cast and day-seven campaign expiry, functions as magic without an Attack bonus, and expires at encounter end after an attack against a strictly magic-only foe. The attack may hit or miss. Adventure completion and settlement travel advance the clock; legacy markers receive a full week from first advancement. Manual early clear is removed while the existing Gremlin/Iron Eater loss choice remains unchanged (TAG p.65).
- Xasartha reaction `1` persists its `6d6` demand and offers exact carried-gold, eligible 15gp+ gem/jewel, or refusal choices. Defeat persists `2d6` necros and a wear-or-sell pendant choice. The pendant is not consumed when Luck is spent; its separate counter survives camp/re-entry and recharges only with a new adventure. It grants one point, or two additional points to a halfling. Barbarians cannot wear it.
- Any normal core Quest completed inside a generated TAG adventure now resolves that lead through the existing readable terminal pause. It explains that the Quest-giver encounter remains peaceful and combat treasure is unavailable, then offers **Continue — return to town and finish**. Resume repairs already-completed rewards without rerolling or duplicating them.
- Accepted Xasartha Bring Gold Quests expose the stored requirement, party total, Quest-giver location, and direct turn-in. Core Quest rewards are no longer mistaken for generated TAG closeout; exact payment produces exactly one Epic Reward.
- Adventure View automatically shows one movable, non-closable Developer Options window whenever any developer preference is active. With all developer preferences off, it is absent.
- Xasartha's persisted TAG p.25 reaction `2 quest` is repaired on resume without rerolling. The player can accept the Expanded Edition p.101 Quest reaction, which rolls a concrete p.162 Quest Table result, or refuse and let Xasartha leave peacefully.
- Typed TAG choices render directly below Narrative in a compact row. The generic objective frame, duplicated prompt explanation, and lifecycle strip are hidden while a typed Medusa action owns the decision.
- Rumor 2 Scene 10 calculates the living party's worst TAG Stealth modifier, rolls one exploding L6 group Save, persists d3+2 agents on failure, and offers only actor-selected L5 Streetwise or immediate combat. Failed parley gives the HCL+2 dagger agents first action; immediate combat gives the party first action; their total 4d6 gp is staged for claim.
- Scene 10 Narrative/UI list every living hero's Stealth modifier, explain that TAG pp.6-8 use one party roll with the lowest modifier, and identify the controlling hero. The assassin response uses a labelled Streetwise actor selector and separate fight option; legacy saved result text is clarified without rerolling.
- Current Objective delegates Medusa Scene 10 and Scene 1 actions to their typed guided controls. Resuming the stored four-agent ambush exposes the actor selector and both printed responses instead of an inert generic prompt button.
- Resumed/new Rumor 2 manifests identify extracted Scene 10 and Scene 1 by scene text rather than generic generated-room role. Scene 10 repairs to its typed procedure and post-result route choices; Scene 1 repairs to a character-selected quiet approach or automatic reaction entry choice.
- Party Sheets place **Apply** beside each carried Gremlin Repellant. At camp it opens the printed p.87 item/Bag protection picker; when unavailable the button remains visible but disabled with the exact timing or eligibility reason.
- Adventure View keeps the current Major Foe tally visible. Invisible Gremlins still increment it exactly once and cannot become the Final Boss.
- The cursed-object Gremlin decision now offers Disbelief and eligible voluntary TAG items before the choice; **Keep it and resolve theft** immediately applies ordinary theft without a second Resolve button.
- Developer grants include a concrete Scroll of Disbelief and Small gemstone (25gp). The Gremlin control can burn a carried Disbelief scroll or use a prepared spell.
- Pending cursed-object and Gremlin guards allow Disbelief through all supported casting paths: prepared spell, carried scroll, or surgeon-assisted scroll. The selected source then reaches the normal Disbelief resolver.
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
- Revealed Gremlins are explicitly tracked as one Minor Foe damage group. Expanded Edition p.94 quotient damage is capped to the number remaining and removes that many tracked members; the exact live `11 / 3` against two remaining L3 Gremlins is covered.
- Item transfer, storage, sale, ordinary loss, destruction, sacrifice, confiscation, and theft share a typed item-disposition policy. Bag-aware removals still preserve exact container identity and report discarded contents; the Bofto object remains bound through ordinary paths.
- Rules Reference, Tables List, State Registry, Party Sheets, developer controls, modern campaign workflow summary, hover text, docs, and focused tests cover the new state.

## Persistence Model

Campaign and saved game remain separate records in the same user-facing `DATA_DIR/game.db`. The session stores `campaign_id`; campaign-owned effects and Rumor records live in the matching campaign record. Character Bags and their contents live on the character and are copied into/out of the active session by the existing roster sync. No second campaign-save file is required.

## Testing Boundary

Automated tests own campaign isolation and legacy migration, all twelve Rumors exhausted, exact Gremlin priority/Clue/Kukla/Clockwork Armor edges, Star-Slayer replacement, carrier death, total-party-kill recovery, and mixed-result split fleeing. Do not risk a valuable live party to force those dice.

Migrate other generated TAG scenes onto typed action definitions one PDF-backed module at a time. Select and inspect one exact scene before coding; keep the slice narrow.

Temporary Weapon Enchantment's full p.65 lifecycle is automated. Do not repeat its Gremlin/Iron Eater loss tests; focused coverage owns day timing, magic-only use, encounter-end expiry, and legacy markers.

## Recent Releases

- `v0.39.67`: normalize new/resumed Daroc Scene 5 narrative to 200gp and distinguish carried, banked, and total gold in Narrative Debug Reports.
- `v0.39.66`: complete Rumor 9's selected-searcher Streetwise loop, persisted Town Clue progress, non-permanent Give up route, required lifecycle, 200gp reward, and one-XP closeout.
- `v0.39.65`: keep required generated-TAG closeout visible with Objective Details collapsed and align Narrative/UI/diagnostics on **Continue — return to town and finish**.
- `v0.39.64`: add the shared required-scene lifecycle and automatically start/persist every Rumor 4 Scene 12 hypnosis Save.
- `v0.39.59`: automate TAG p.29 Scene 12 hypnosis, rescue turns, ration disposition, campaign sale rate, and two-minion XP progress.
- `v0.39.58`: keep multiple generated Rumor entry choices side by side at normal app widths.
- `v0.39.57`: restore generated Rumor entry decisions beneath Narrative and suppress internal objective prose.
- `v0.39.56`: introduce Daroc's Lost Familiar town-Clue cost, selected recipient, and one pending XP roll; v0.39.66 corrects the reward and completes its in-scene lifecycle.
- `v0.39.55`: automate Temporary Weapon Enchantment's seven-day and qualifying magic-only encounter expiry.
- `v0.39.54`: complete typed Xasartha bribe, combat treasure, wear/sell pendant, necros, and rechargeable Luck paths.
- `v0.39.53`: turn a completed generated-TAG core Quest into a readable peaceful closeout, including resume repair for already-awarded saves.
- `v0.39.52`: restore concrete Xasartha core-Quest turn-in and move enabled developer controls into an automatic non-closable floating window.
- `v0.39.51`: persist and resolve Xasartha's Quest reaction, and compact the typed Current Objective UI beneath Narrative.
- `v0.39.50`: clarify Scene 10's one-roll modifier breakdown and separate the labelled Streetwise and immediate-fight choices.
- `v0.39.49`: make Current Objective render the persisted Medusa Scene 10/1 typed controls, including the post-Stealth assassin decision.
- `v0.39.48`: repair Rumor 2 Scene 10/1 identity, replace extracted sentence-fragment buttons, restore post-encounter routing, and remove the exploding-d6 helper collision.
- `v0.39.47`: automate and persist TAG Rumor 2 Scene 10's group Stealth, assassin response, initiative, and treasure procedure.
- `v0.39.46`: extract shared item-disposition eligibility and Bag-aware removal policy with behavior-parity coverage.
- `v0.39.45`: close the adventure-test gate and apply p.94 Minor Foe quotient damage across the remaining revealed-Gremlin group.
- `v0.39.44`: allow Disbelief scroll use through the pending cursed-object and Gremlin guards.
- `v0.39.43`: automatic post-Keep Gremlin theft, visible Major Foe tally, and Scroll of Disbelief test support.
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
