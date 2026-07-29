# Current Playtest Plan

Last updated: 2026-07-29. Target build: v0.39.57.

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

## Completed: TAG Rumor 2 Quest Closeout

Live v0.39.53 verification passed in session
`1b417a50983c4329b4f2b1aead6cf76d`:

- the existing Book of Skalitos reward and `9gp` remained unchanged on resume;
- generic Generated lead guidance was replaced by the peaceful Quest result;
- **Return to town and finish** completed the adventure;
- the saved session is `complete`, with no active Quest or pending generated
  closeout, and the roster save completed.

Do not repeat Scene 10, Xasartha's Quest reaction, the 200gp payment, or the
Epic Reward/closeout path.

## New Slice: TAG Xasartha Scene 1/6

v0.39.54 implements the remaining TAG pp.25-27 Xasartha paths:

- reaction `1` persists its `6d6` bribe and offers exact carried-gold, eligible
  15gp+ gem/jewel, or refuse-and-fight choices;
- reactions `3-5` fight normally and `6` suppresses Morale;
- defeating Xasartha awards the normal major-foe XP roll, persists one `2d6`
  necros roll, and offers **Wear the pendant** or **Sell without trying it on**;
- the pendant persists and uses the existing Luck controls, but its separate
  counter recharges only in a new adventure, not after camp/re-entry; it grants
  one point, or two additional points to a halfling;
- Barbarians may carry/sell the treasure but cannot wear the magic pendant.

Focused backend, endpoint, roster-sync, Luck/recharge, class-restriction, and
frontend-contract coverage owns the dice and state transitions. Do not replay
Scene 10, the Quest route, or another full Rumor 2 adventure.

After deploying v0.39.54 and force-refreshing, perform only a short visual check
if a new/generated test session naturally reaches one of the new pending
panels: confirm the bribe or reward choice is readable and survives one
save/dashboard/resume. Do not risk or modify the completed live party to force
the needed reaction.

## Do Next

v0.39.57 fixes the reported generated Rumor entry regression. After deploying
and force-refreshing, resume session `9268a7158f41482d90d16f4ec3946f46` and
confirm:

1. **Choose to investigate** and **Don't investigate** are immediately beneath
   Narrative, not inside a prose-heavy Current Objective box.
2. No visible player text contains `Entry`, `Rumor playbook`, `record the
   approach`, or other Director/workflow instructions.
3. The two choices remain visible with Objective Details hidden.

The disposable local clone already confirmed that **Choose to investigate**
advances to the exact Scene 10 Narrative and typed **Roll group Stealth Save**
control. Do not click through or replay Scene 10 merely to repeat that automated
check; the live check is placement/copy only.

After this narrow UI gate passes, return to the planned TAG p.29 Scene 12
Mutant Fish slice. Two source interpretations remain awaiting player ruling:
whether a failed rescuer Save still rescues the original hero while dragging
the rescuer into the water, and whether friendly chaos-cultist terms should be
a logged sale declaration or persistent campaign faction state.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
