# Current Playtest Plan

Last updated: 2026-07-27. Target build: v0.39.50.

## Adventure Test Gate: Passed

The remaining Disbelief and Invisible Gremlins checks passed in live session
`1996ab8f2fc940cc9605f82c88798d26`. The saved state is clean: no pending
Gremlin event, no pending cursed-object choice, no living foes, claimed
treasure, the used Scroll of Disbelief removed from Sir Benedict, and one
scroll retained by each other party member.

The Narrative exposed one final Expanded Edition p.94 **Damage / Foes**
discrepancy: an attack total of 11 against two remaining L3 revealed Gremlins
reported three kills but removed only the selected Gremlin. v0.39.45 caps the
quotient at the remaining group size and applies those kills across the
separately tracked group. Exact automated coverage reproduces the live
`11 / 3` case and proves both remaining Gremlins are removed.

Do not repeat the Gremlin fight or any earlier EE, Abyss, Forsaken Depths,
Citadel, Bofto, Bag, Repellant, treasure, foe, trap, entrance, or closeout
test. Reopen only an exact workflow if a later change produces a confirmed
regression.

## Do Next

### TAG Rumor 2: Resume The Stored Assassin Choice

This is the only open manual check. Deploy v0.39.50, force-refresh, and resume
session `de586c99ab51416197f543fead8614b9`; do not generate a new adventure or
repeat the group Stealth Save.

1. Confirm the stored result has been rewritten into plain language without
   rerolling. It must explain that TAG pp.6-8 use one party roll, list all four
   character modifiers, identify Sir Benedict's `-2` as the controlling
   modifier, show the stored `2 - 2 = 0` failure, and retain four agents.
   Current Objective must show two visually separate choices. The first is
   labelled **Who attempts the Streetwise Save?** with a character dropdown
   and **Roll Streetwise Save**. The second is **Fight the assassins** and
   states that the party acts first.
2. Choose **Fight the assassins**. Combat must start with the party acting
   first against four HCL+2 dagger minions. The alternate Streetwise route and
   agents-first failure path remain covered by focused automated tests.
3. After victory, exactly the staged total 4d6 gp must be claimable, followed
   by **Approach the cabin** and **Return to town**. This route counts as one
   minion encounter for XP purposes.
4. Choose **Approach the cabin**. Confirm the app moves to Scene 1 and shows
   only **Approach the cabin** with a character dropdown and **Shout out to the
   Medusa**. Stop there; Scene 1 combat, reaction, pendant, necros, and Luck
   handling are the next PDF-backed conversion slice and are not part of this
   release gate.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
