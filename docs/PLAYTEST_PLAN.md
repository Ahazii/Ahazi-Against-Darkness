# Current Playtest Plan

Last updated: 2026-07-20. Target build: v0.39.36 campaign-scoped TAG state, explicit Bags of Carrying, and Invisible Gremlins.

This file contains only the remaining player checks. Earlier EE, Abyss, Forsaken Depths, Citadel, and Bofto Scene 9/14/17/19 passes are recorded in `docs/STATUS.md` and must not be repeated unless one of the checks below finds a regression.

## Do Next

### 1. Deploy And Refresh

1. Deploy `v0.39.36` from `main` to Unraid at `http://192.168.1.55:8001`.
2. Force-refresh until the app header reports `v0.39.36`.
3. Use a disposable party for the Gremlin checks. Enable Developer Playtest Controls and the fixed Adventures Guild lead selector only for these checks.

### 2. Campaign And Rumor Continuity

Rules source: `Tales_from_the_adventurers_guild.pdf`, Rumors Table and Rumor 1, printed pp.22 and 29-31.

1. In a campaign, generate fixed Rumor 1, **Bofto's Star-Shaped Find**. Confirm the Adventures Guild Workflow Summary records the rumor as heard, then investigating after the adventure starts.
2. Confirm Scene 14 still requires a named living thief, rolls that character's Save vs L6, and chooses Scene 18 or Scene 19 automatically. There must be no player-facing success/failure choice.
3. Finish either branch. Confirm the campaign records Rumor 1 as resolved only after its Scene has played, and the session closes normally.
4. Generate a random Rumor in that same campaign. It must reroll a resolved rumor instead of silently replaying it. The fixed developer selector may still replay an exact rumor for testing.

Campaign isolation and legacy-record migration are covered automatically; do not create or damage a second live campaign solely to test them.

### 3. Two Bags Of Carrying

Rules source: TAG p.13, **Bag of Carrying**.

1. Give one non-Barbarian two Bags of Carrying through the TAG settlement service. Put a different cheap item in each Bag using Party Sheets.
2. Save, return to the Dashboard, and resume. Confirm both Bags and their separate contents remain visible.
3. Transfer only the second Bag to another magic-item-eligible hero. Confirm only that Bag's contents move with it and the first Bag is unchanged.
4. Try to transfer a Bag to a Barbarian; it must be refused. Try to sell a non-empty Bag; the app must ask you to empty it first.

### 4. Ordinary Invisible Gremlins

Rules sources: Expanded Edition pp.87, 105, 107, 169, **Gremlin Repellant** and **Invisible Gremlins**; TAG p.11 temple tags; TAG p.13 Bag of Carrying; TAG p.65 **Temporary Weapon Enchantment**.

1. At camp before entering, apply one Gremlin Repellant dose to one specific Bag or loose item. Re-enter and force **TAG Invisible Gremlins curse encounter**. If the star-object choice appears, choose **Keep it** for this ordinary-theft check.
2. Confirm the app pauses with the rolled `d6+3` theft count and offers **Cast Disbelief**, eligible voluntary Resurrection/Blessing tags, and **Resolve Gremlin theft**. If the party happens to carry a temporarily enchanted weapon, confirm **Let Gremlins take [weapon]** also appears; ordinary resolution must keep it unless that explicit choice is used. Save/resume once while this choice is pending; the same count and controls must remain.
3. Resolve theft. Confirm the protected item survives, ordinary theft follows magic items -> scrolls -> potions -> weapons -> gems -> 10gp, and a stolen Bag loses everything inside it. Clockwork Armor consumes two theft slots if present.
4. Confirm the event increments the Major Foe tally once, cannot become the Final Boss, and creates no combat unless Disbelief is cast.

### 5. Disbelief Reveal

Rules source: Expanded Edition p.74, **Disbelief**, and p.169, **Invisible Gremlins**.

Run this only if the disposable party has a character with Disbelief.

1. Force another Invisible Gremlins event and cast **Disbelief** from the pending-event controls.
2. Confirm combat starts against `d6+1` L3 Minions with one attack, Morale -1, and one Treasure roll for the group. If a temporarily enchanted weapon is present, first choose whether it is eligible for theft; the choice must survive save/resume and must not itself remove the weapon.
3. A failed Defence must steal an eligible item instead of causing Life loss. This exact hit behavior also has automated coverage; do not repeat the fight merely to force a failed roll.

## Automated Coverage Only

Do not risk a valuable party to force campaign isolation, all twelve rumors being exhausted, exact random dice, Kukla secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item exhaustion/Clue creation, Star-Slayer replacement, carrier death, total-party-kill curse recovery, mixed-result split fleeing, or the Iron Eater's TAG p.65 temporary-weapon decision. Focused tests own those cases.

## Stop Gate

When sections 2-4 pass, the release gate is passed. Section 5 may be recorded as conditional if no disposable Disbelief caster is available. Stop adventure regression testing and resume modularisation in small tested slices. A failure reopens only that exact workflow.

The reusable typed scene-action contract is currently applied to Bofto's Scene 14. Other generated TAG modules must be converted source-by-source from their own PDF scenes; do not infer a generic procedure from prose or ask the player to choose a dice outcome.

## Reporting A Failure

Provide the campaign name, session id, current Scene/room, selected action, exact button pressed, visible result, expected PDF page/topic result, and a **Copy Narrative Report**. Include HTML only when visible controls disagree with the Narrative/debug report.
