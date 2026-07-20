# Current Playtest Plan

Last updated: 2026-07-20. Target build: v0.39.35 Bofto Scene 19 and star-object curse.

This file contains only the remaining player checks. Earlier EE, Abyss, Forsaken Depths, Citadel, and Bofto Scene 9/14/17 passes are recorded in `docs/STATUS.md` and should not be repeated unless a later change reopens them.

## Do Next

### 1. Deploy And Refresh

1. Deploy `v0.39.35` from `main` to Unraid at `http://192.168.1.55:8001`.
2. Force-refresh until the app header reports `v0.39.35`.
3. Enable dungeon playtest controls and the TAG fixed-result selector only for these checks.

### 2. Fresh Bofto Success Route

Rules source: `Tales_from_the_adventurers_guild.pdf`, Rumor 1 and Scenes 9, 14, 18, and 19, printed pp.22 and 29-31.

1. Generate Rumor 1, **Bofto's Star-Shaped Find**, and start it with the intended party.
2. Choose to investigate, then choose the Scene 14 theft route. Confirm the theft control requires a named living character; there must be no characterless `d6+0` roll and no player choice between success and failure.
3. Select the thief and click **Roll theft Save**. The app must use the chosen character's printed L6 thievery modifier and route automatically. If this attempt fails, confirm Scene 18 closes the module cleanly, then generate Rumor 1 again to obtain the success route.
4. On success, confirm Scene 19 is resolved automatically for that same thief. The Narrative must stop after the star-object curse rules; it must not include **Following the Treasure Map Table**, Map Leads To, Riff-Raff, later book sections, or the old manual **Star Will save** / **Star-Slayer check** controls.
5. Confirm the Scene 19 Will Save is L8, spellcasters and clerics add +Level, and a halfling gets one reroll after failure. Failure adds 1 Madness; either result leaves **Bofto's Star-Shaped Cursed Object** and its curse on the thief.
6. Confirm the module reaches the ordinary adventure-complete summary and does not leave a resumable Bofto session.

### 3. Curse Restrictions

Rules source: TAG p.30, Scene 19. No magic or Blessing removes the curse; only explicitly letting Invisible Gremlins take the object ends it.

1. Start a normal dungeon with the cursed character's party.
2. In Party Sheets or the available item-management surfaces, attempt one voluntary transfer and one sell/store action for the cursed object. Each must be blocked with a clear TAG p.30 explanation; the item must remain with its carrier.
3. Do not spend a Blessing solely for this test. If one is used naturally, confirm it may heal Madness or another valid condition but does not remove the object or curse.

### 4. Star-Slayer Encounter

Rules source: TAG pp.30-31, **Star-slayer from Beyond**.

1. Use Developer Playtest Controls -> **TAG Star-Slayer curse encounter**.
2. Confirm the foe is a Weird demon at HCL+6, has HCL+5 Life, makes four attacks for Tier damage, has no ordinary treasure, and always fights to the death.
3. On sight, every living hero must Save vs HCL+1. A failed Save applies 1 Madness and 2 Life loss. If the party has mixed results, try to flee: successful savers may leave while heroes who gained Madness must remain. Do not repeat the encounter merely to manufacture mixed dice; automated coverage owns that edge case.
4. Defeat the Star-Slayer under the Classical XP system and confirm it awards exactly **2 XP rolls**. It must not add a third Final Boss XP roll and defeating it must not clear the curse.

### 5. Invisible Gremlins Cure

Rules source: TAG pp.30-31, Scene 19 curse-removal condition.

1. Use Developer Playtest Controls -> **TAG Invisible Gremlins curse encounter**.
2. Confirm the app asks whether to let the Gremlins take the cursed object; it must not decide silently.
3. Choose **Let them take the cursed object**. Confirm this bypasses Gremlin protection, removes the object and curse, and leaves no pending Gremlin choice.
4. A second run choosing **Keep the cursed object** is optional because the keep/protection path has automated coverage.

## Conditional Legacy Check

If the reported oversized Bofto session `b47cac2be0eb4977b52e5eb19172d4d5` still appears in Saved Games, resume it once. Its Scene 19 prompt and existing Narrative line should be trimmed before **Following the Treasure Map Table**, and stale manual Bofto controls should be absent. Skip this check if the session has already been completed or deleted.

## Automated Coverage Only

Do not risk a valuable party to force these cases. Focused tests cover automatic transfer when the carrier dies, campaign-persistent recovery after a total party kill, the future-treasure 1-in-6 recovery and character assignment, Final Boss treasure retention, split fleeing, generic item-loss protection, and the exact two-XP award.

## Stop Gate

When sections 2-5 pass, stop broad adventure regression testing and resume modularisation in small tested slices. A failure in one of those sections reopens only that exact workflow; it does not reopen the already-passed EE, Abyss, Forsaken Depths, or Citadel suites.

## Reporting A Failure

Provide the session id, current room, selected developer action, exact button pressed, visible result, expected TAG page/topic result, and a **Copy Narrative Report**. Include HTML only if the visible controls disagree with the Narrative/debug report.
