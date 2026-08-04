# Current Playtest Plan

Last updated: 2026-08-04. Target build: v0.39.70.

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

## Completed: TAG Rumor 2 Scene 10 Return

Live v0.39.60 verification passed in session
`9268a7158f41482d90d16f4ec3946f46`:

- **Approach the cabin** and **Return to town** appeared side by side;
- **Return to town** completed the adventure and opened the normal summary;
- no town-return delivery or returned-cargo line appeared because the party had
  no pending alchemist order or porter cargo.

The summary incorrectly described all seven prebuilt module rooms as explored,
although persisted visit tracking records only the rumor entry and Scene 10.
v0.39.61 reports the two visited map elements, repairs the stored summary when
the completed session is next opened, and retains the old map-size fallback
only for legacy sessions without visit tracking. This reporting fix is covered
automatically; do not replay Rumor 2.

## Completed: TAG Rumor 4 Closeout

Live v0.39.64 evidence in session `cee90d971b804c2f9c32d54caac040ab`
passes the Rumor opening and the full TAG p.29 Scene 12 procedure. Do not repeat
Investigate, the four initial Saves, five rescue turns, Life loss, ration roll,
Keep choice, or two-minion progress. The remaining defect was presentation:
Narrative said **Continue**, while the enabled closeout was a small differently
labelled chip and its full action panel was hidden with Objective Details.

The v0.39.65 force-refresh/resume check passed. In that same session:

1. the prominent **Continue — return to town and finish** action was visible
   beneath Narrative while Objective Details remained collapsed; and
2. choosing it opened the normal Adventure Complete summary.

Do not regenerate or replay Rumor 4. Automated tests own its remaining
diagnostic wording, total-party destruction, failed-rescuer role swaps, the 5gp
friendship rate, carrying-limit distribution, duplicate prevention, XP
rollover, saved collapsed-panel preferences, and shared closeout endpoint.

## Completed: Rumor 9 Presentation Check

The v0.39.67 non-mutating presentation gate passed. Scene 5 showed the
player-confirmed 200gp TAG p.24 offer, the copied Narrative Report separated
carried, banked, and total gold, and the inspection did not change the completed
Rumor state. Do not regenerate the module, repeat Streetwise searches, spend
more Clues, or replay its reward/XP path.

## Completed: Rumor 6 Blackbird Hill

Live session `380ffb5e2c834195806027c898e3f55d` passed the complete bounded
Rumor 6 gate on 2026-08-04:

- **Investigate** / **Not now — return to town** appeared before the service;
- Investigate entered TAG pp.25-26 Scene 2 without completing the adventure;
- three 200gp Shoes of Fast Walk purchases completed and stopped when funds ran
  out;
- the lesson price changed automatically to 0gp after the third pair; and
- save/dashboard/resume preserved all three purchases;
- the free illusion lesson worked under the player-confirmed learner ruling;
- the service controls and **Done — leave Blackbird Hill** were reachable; and
- Done exposed the normal Continue action and the adventure completed.

Do not start Rumor 6 again, rebuy any Shoes, dismiss a hireling, or alter this
saved state to repeat an already-passed check. Rumor 6 is closed unless a later
change produces a confirmed regression in that exact workflow.

## Do Next: Resume Rumor 11 — Deoldyn's Range

Rules source: Rumor 11 on TAG p.24 and Scene 3 on TAG p.26.

Live v0.39.69 session `fc741849402d46e096b2efa52368de8f` already passed
the shared **Investigate** / **Not now — return to town** opening and
Investigate reached Scene 3 without completing the adventure. Do not create a
new Rumor 11 module or repeat that opening. The live session exposed a layout
regression: the shared service host's imposed height prevented the horizontal
Narrative/map divider from resizing the row, leaving too little map visible.

After deploying the resize correction, force-refresh and resume that same
session:

1. Drag the horizontal divider in both directions. Confirm the map grows and
   shrinks with the user's selected row height; service content must not impose
   a competing minimum height. At a short Narrative height, confirm the service
   panel uses its own vertical scrollbar so training controls and **Done —
   finish training** remain reachable.
2. Confirm this preserved party's current eligibility remains unchanged: Sir
   Benedict shows 0/600gp, Faelar shows 0/540gp, and Sister Joyce/Sly Silas are
   class-ineligible. No training batch can safely be funded in this save. Do
   not grant, transfer, sell, or otherwise alter persistent resources merely to
   force the paid path.
3. Force-refresh or save/dashboard/resume once before finishing. Confirm the
   open Deoldyn service and selected divider height persist without a reroll or
   payment.
4. Choose **Done — finish training** with no trainees, then complete the normal
   shared Continue closeout exactly once. This validates the printed option to
   skip training. Automated tests own whole-batch validation, payment-before-
   roll ordering, failed-roll costs, later-batch rejection, and persistence;
   inspect paid training later only if a naturally eligible funded party reaches
   Scene 3.

Stop after this bounded Rumor 11 module and attach a Narrative Report for any
mismatch. A resize-only mismatch should not require replaying Investigate or
any completed training. Do not mass-enable required scene completion: every
remaining Rumor still needs its own printed terminal routes.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
