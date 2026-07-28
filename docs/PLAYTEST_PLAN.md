# Current Playtest Plan

Last updated: 2026-07-28. Target build: v0.39.53.

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

### TAG Rumor 2: Close The Already-Completed Quest

This is the only open adventure check. Deploy v0.39.53, force-refresh, and resume
session `1b417a50983c4329b4f2b1aead6cf76d`; do not generate a new adventure or
repeat Scene 10, its combat, Xasartha's reaction roll, Quest acceptance, the
200gp payment, or the Epic Reward roll.

1. Confirm the already-awarded Book of Skalitos remains in Sir Benedict's
   inventory and the party still has `9gp`; no reward or Quest roll repeats.
2. The useless **Generated lead** / Rumor playbook text must be gone. In its
   place, the objective must say that the Quest is complete, the Quest-giver
   accepts the result, the encounter remains peaceful, combat treasure is not
   awarded, and the Epic Reward in Narrative is the Quest reward.
3. Confirm the only relevant action is **Return to town and finish**. Use it
   and confirm the ordinary Adventure Complete summary opens.

The completed-Quest resume repair and Continue path are covered by focused
automation. Xasartha's bribe, fight/fight-to-the-death, pendant, necros, and
Luck procedures remain the next bounded TAG p.25-26 slice.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
