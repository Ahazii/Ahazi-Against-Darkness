# Current Playtest Plan

Last updated: 2026-08-03. Target build: v0.39.65.

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

## Do Next: TAG Rumor 4 Closeout Only

Live v0.39.64 evidence in session `cee90d971b804c2f9c32d54caac040ab`
passes the Rumor opening and the full TAG p.29 Scene 12 procedure. Do not repeat
Investigate, the four initial Saves, five rescue turns, Life loss, ration roll,
Keep choice, or two-minion progress. The remaining defect was presentation:
Narrative said **Continue**, while the enabled closeout was a small differently
labelled chip and its full action panel was hidden with Objective Details.

After deploying v0.39.65 and force-refreshing, resume that same session; do not
generate another Rumor 4. Confirm only that:

1. the prominent **Continue — return to town and finish** action is visible
   beneath Narrative even while Objective Details is otherwise collapsed;
2. the compact Narrative-header action uses the same wording;
3. Copy Narrative Report names that pending closeout action; and
4. choosing the prominent action opens the normal Adventure Complete summary.

Do not force an all-party failure on the valuable live party. Automated tests
own total-party destruction, failed-rescuer role swaps, the 5gp friendship
rate, carrying-limit distribution, duplicate prevention, XP rollover, saved
collapsed-panel preferences, and the shared closeout endpoint.

After this narrow gate passes, migrate Rumor 9's already-typed Daroc terminal
onto the same required-resolution metadata. Do not mass-enable the gate: the
pp.22-31 audit found that every Rumor needs a terminal result, but several still
need vendor/service Done actions or child-dungeon return wiring first.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
