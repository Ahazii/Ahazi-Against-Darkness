# Current Playtest Plan

Last updated: 2026-07-28. Target build: v0.39.52.

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

### TAG Rumor 2: Complete Xasartha's Stored Gold Quest

This is the only open adventure check. Deploy v0.39.52, force-refresh, and resume
session `1b417a50983c4329b4f2b1aead6cf76d`; do not generate a new adventure or
repeat Scene 10, its combat, Xasartha's reaction roll, or Quest acceptance.

1. Confirm the compact objective states **Give 200gp and claim the Epic
   Reward**, says that the party has `209gp`, and identifies Xasartha's Cabin
   as the turn-in location. The generic **Generated Adventures Guild
   closeout** panel must not appear.
2. Open Quest Details. Confirm progress is `209/200gp` and there is a direct
   **Give 200gp and claim Epic Reward** action.
3. Use the action. Exactly `200gp` must be deducted, leaving `9gp` total; the
   Quest must clear and exactly one Expanded Edition p.101 Epic Reward must be
   awarded and described in Narrative.
4. With any Developer Playtest Preference enabled in Settings, confirm a
   **Developer Options** window appears automatically in Adventure View. It
   must be movable by its title bar, have no close button, and no longer consume
   Action Rail height. Disable every developer preference and confirm the
   window disappears.

The acceptance/refusal and save/resume paths are covered by focused automation.
Xasartha's bribe, fight/fight-to-the-death, pendant, necros, and Luck
procedures remain the next bounded TAG p.25-26 slice.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
