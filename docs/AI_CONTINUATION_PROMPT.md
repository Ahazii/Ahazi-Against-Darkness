# AI Continuation Prompt — Ahazi Against Darkness

Copy the prompt below into a new AI task when continuing this work.

```text
You are continuing the Ahazi Against Darkness project in C:\Coding\4AD on Windows/PowerShell. Work from the current repository and live playtest state; do not restart the investigation or broaden scope.

Read first, in this order:
1. AGENTS.md
2. docs/AI_CONTINUATION_PROMPT.md
3. docs/STATUS.md
4. docs/PLAYTEST_PLAN.md
5. docs/ROADMAP.md
6. docs/NEXT_SESSION_HANDOFF.md
7. docs/MASTER_RULE_COVERAGE.md
8. docs/Checking/RULEBOOK_CHECKING_GUIDE.md and docs/Checking/TAG_SECTION_GUIDE.md

Rules and working constraints:
- Use the owned Rules PDFs as the source of truth. For any rules ambiguity, quote the PDF page and topic before coding; do not infer procedures from app narrative.
- Reuse existing shared code before adding a Rumor-specific path. Generated TAG Rumors use one shared opening and typed scene plug-ins.
- Update the Dashboard Tables, Dashboard Rules Reference, checking guide, status, roadmap, handoff, playtest plan, and rule coverage whenever a rules-backed UI or procedure changes.
- Preserve existing user work. Do not touch unrelated .vscode/ or tmp/ files. Do not edit game.db directly; before any live deployment, create and checksum-verify a timestamped backup beside it in \\TOWER\appdata\ahazi-against-darkness.
- The Unraid host is 192.168.1.55. The container is AhaziAgainstDarkness and uses /mnt/user/appdata/ahazi-against-darkness => /data.
- Commit and push intentional changes. Deploy only after appropriate tests and a successful Docker image publish.

Current verified release and live state:
- The v0.39.73 implementation commit is 259013c; documentation may be a later commit on main. App version 0.39.73 is deployed and healthy on Unraid.
- v0.39.73 fixes the nested Narrative/service divider: it stays visible when a tall guided Rumor 6 or 11 service is visibly active even if Objective Details is collapsed.
- Frontend regression result for this fix: 150 passed, 2 skipped. The focused browser test reproduces the collapsed Objective Details state.
- Current live session: fc741849402d46e096b2efa52368de8f, Rumor 11 / Deoldyn's Archery Training.
- It is inside the adventure (camped_outside=false), at Deoldyn's open service; training_batch_resolved=false and the quest is not complete.
- Sir Benedict is the only currently eligible intended trainee: Level 10, 0 carried gp + 600 banked gp = 600 available gp; fee 600 gp. No payment or roll has occurred.
- Faelar has 125 carried + 300 banked = 425 gp and is short of the 540 gp fee. Sister Joyce and Sly Silas are class-ineligible.
- The latest safe backup before v0.39.73 deployment is \\TOWER\appdata\ahazi-against-darkness\game-before-v03973-deploy-20260804T150648Z.db.

Already passed — do not replay unless a confirmed regression occurs in that exact workflow:
- Rumor 6 complete Blackbird Hill gate, including three Shoes purchases, free lesson, Done, Continue, and completion.
- Rumor 11 shared Investigate/Not now opening, Scene 3 entry, outer Narrative/map divider correction, camp transfers, Return to dungeon repair, and route back to Deoldyn.
- Rumor 4, Rumor 9, and all other broad adventure gates recorded as passed in the playtest plan.

The only remaining bounded Rumor 11 live gate:
1. Ask the player to Ctrl+F5 on v0.39.73 at the existing Deoldyn service.
2. With Objective Details collapsed, verify the inner horizontal Narrative/service divider is visible; drag it both ways, double-click reset it, and confirm independent scrolling. Also verify the outer combined Narrative/service-to-map divider still works.
3. Verify Sir Benedict's visible funds line and hover explanation.
4. Select Sir Benedict, choose Deadly Accuracy or Dead Shot, and run the automatic batch. Confirm the exact 600 gp is spent from his bank before the automatic XP roll; a failed roll does not refund it.
5. Choose Done — finish training, then Continue — return to town and finish once.
6. Request a Narrative Debug Report after any mismatch. Do not repeat the passed opening, camp transfer, or route.

Rules evidence for the remaining test:
- TAG p.9: all money in a character's home bank is available when needed.
- TAG p.24: Rumor 11 lead.
- TAG p.26, Scene 3: Deoldyn training, 60 gp × Level, payment before XP resolution.

If the user reports another UI issue, first inspect the visible live DOM and current session state, then make the smallest reusable fix with a regression test. Do not alter a training selection, payment, roll, or completed-state action while diagnosing.

After Rumor 11 passes, update the playtest plan and handoff to mark its complete gate passed. The next implementation slice is not a broad refactor: select one exact PDF-backed generated TAG terminal, beginning with Rumor 3 Scene 11 only after inspecting its mandatory TAG pp.34-35 Riff-Raff / Outside of Town Ambush procedure.
```
