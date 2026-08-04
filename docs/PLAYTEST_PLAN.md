# Current Playtest Plan

Last updated: 2026-08-04. Target build: v0.39.69.

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

## Completed So Far: Rumor 6 Opening And Purchases

Live v0.39.68 session `380ffb5e2c834195806027c898e3f55d` passed these
parts of Rumor 6:

- **Investigate** / **Not now — return to town** appeared before the service;
- Investigate entered TAG pp.25-26 Scene 2 without completing the adventure;
- three 200gp Shoes of Fast Walk purchases completed and stopped when funds ran
  out;
- the lesson price changed automatically to 0gp after the third pair; and
- save/dashboard/resume preserved all three purchases.

Do not start Rumor 6 again, rebuy any Shoes, dismiss a hireling, or alter this
saved state to repeat an already-passed check.

## Do Next: Resume Rumor 6 For Free Lesson And Closeout

Deploy v0.39.69, force-refresh, and resume session
`380ffb5e2c834195806027c898e3f55d`. Rules source: Rumor 6 on TAG p.23, Scene 2
on TAG pp.25-26, and EE p.76 Scrolls as applied by the player-confirmed campaign
interpretation.

1. Confirm the Blackbird Hill guided service either expands to fit or has a
   visible vertical scrollbar. Scroll through it and confirm the learner/spell
   controls and **Done — leave Blackbird Hill** are all reachable without
   changing browser zoom.
2. Confirm the header still says **Shoes bought: 3** and **Illusion lesson:
   0 gp**. Do not buy another pair.
3. Open the learner list. Sir Benedict, Sister Joyce, Faelar Sunshadow, and Sly
   Silas are all living non-Barbarians in this save, so each may receive a spell
   they do not already know; none should be rejected merely because it is outside
   a normal class list. A duplicate known spell may be omitted. A dead character
   or Barbarian remains ineligible; those negative cases are automated-only.
4. Choose one illusion spell and one learner. Choosing Sly Silas, if desired,
   directly checks the non-spellcaster branch: the result should explain that
   the retained spell has one use per adventure and is cast at +1. Confirm the
   lesson is free and records once without losing the three Shoe purchases.
5. Choose **Done — leave Blackbird Hill**. Confirm the service resolves exactly
   once and the normal **Continue — return to town and finish** action is
   visible and completes the adventure.

Stop and attach a Narrative Report if any learner is missing, the spell cannot
be selected, the controls/Done remain clipped, or Continue does not appear.

## After Rumor 6 Passes: Rumor 11 — Deoldyn's Range

Rules source: Rumor 11 on TAG p.24 and Scene 3 on TAG p.26.

1. Start a fresh Rumor 11 module. Confirm the first choice is again only
   **Investigate** / **Not now — return to town**; training appears only after
   Investigate reaches Scene 3, and arrival does not complete the adventure.
2. Select a small batch of living bow-capable trainees (two when the disposable
   party safely permits it). Confirm the review shows each `60gp × Level` cost
   before confirmation. If a normal/base Elf is present, confirm that Elf alone
   can choose ordinary level advancement instead of Deadly Accuracy or Dead
   Shot; variant Elves must not receive that option.
3. Confirm the batch once. The result must say every selected payment was taken
   before any automatic XP roll. If a roll fails naturally, confirm its payment
   is not refunded; do not force a failure. Refresh or save/resume and confirm
   the results persist without rerolling.
4. Confirm the host now says the simultaneous batch is closed and does not let
   an unselected or already trained character start a later batch after the
   results are known. Then choose **Done — finish training** and complete the
   normal shared closeout exactly once.

Stop after this bounded Rumor 11 module and attach a Narrative Report for any
mismatch. Do not mass-enable required scene completion: every remaining Rumor
still needs its own printed terminal routes.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
