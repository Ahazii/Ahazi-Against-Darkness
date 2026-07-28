# Current Playtest Plan

Last updated: 2026-07-28. Target build: v0.39.51.

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

### TAG Rumor 2: Resume Xasartha's Stored Quest Choice

This is the only open manual check. Deploy v0.39.51, force-refresh, and resume
session `1b417a50983c4329b4f2b1aead6cf76d`; do not generate a new adventure or
repeat Scene 10, its combat, or Xasartha's reaction roll.

1. Confirm resume does not reroll the stored TAG p.25 result `d6=2 quest`.
   Narrative must say that Xasartha offers a Quest and the compact action row
   directly below it must show only **Accept Xasartha's quest** and
   **Refuse and let Xasartha leave**.
2. Confirm the old generated-objective box, repeated objective explanation,
   lifecycle badges, and internal `Adventures Guild procedure:` wording are
   absent. Narrative must retain a useful readable area and its own scrollbar.
3. Choose **Accept Xasartha's quest**. The app must roll once on the Expanded
   Edition p.162 Quest Table, show the concrete new core Quest, let Xasartha
   leave peacefully, and award no pendant, necros, or immediate Epic Reward.
   The Epic Reward belongs only to successful completion of that new Quest
   (Expanded Edition p.101).
4. Save, return to the dashboard, and resume once. Confirm the generated core
   Quest and its exact rolled requirement persist. Stop there; do not complete
   or deliberately fail the new Quest in this gate.

The refusal path is covered by focused automation: it lets Xasartha leave,
resolves the Rumor module, and creates no core Quest. Xasartha's bribe,
fight/fight-to-the-death, pendant, necros, and Luck procedures remain the next
bounded TAG p.25-26 slice.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
