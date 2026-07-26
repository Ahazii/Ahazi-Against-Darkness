# Current Playtest Plan

Last updated: 2026-07-26. Target build: v0.39.47.

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

### TAG Rumor 2: Scene 10 Cabin Approach

This is the only newly opened manual check. Generate fixed **Rumor 2: Medusa
in the Hunter's Cabin**, begin it, and reach Scene 10.

1. Confirm the current-room action says **Approach the cabin** and shows one
   group Stealth Save using the living party member with the worst modifier.
   It must include TAG pp.6-8 class bonuses and the -1 Shield / -1 Heavy Armor
   penalties; there must be no manual Amount or success/failure choice.
2. Click **Roll group Stealth Save**. Save, return to the dashboard, and resume.
   The result and exact Scene 10 stage must still be present; the Save must not
   reroll.
3. If the Save succeeded, confirm the party can continue to Scene 1 or return
   to town. If it failed, confirm the rolled d3+2 agent count remains visible
   and the only responses are **Try to convince them** or **Fight the
   assassins**.
4. On **Try to convince them**, choose the acting character. The app must roll
   the L5 Streetwise Save. Success returns the party to town; failure starts
   HCL+2 dagger-minion combat with the agents acting first.
5. On **Fight the assassins**, combat must start with the party acting first.
   After victory, exactly the staged total 4d6 gp must be claimable. This route
   counts as one minion encounter for XP purposes.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
