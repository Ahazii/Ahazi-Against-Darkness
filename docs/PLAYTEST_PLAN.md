# Current Playtest Plan

Last updated: 2026-08-03. Target build: v0.39.62.

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

## Do Next: TAG Rumor 4 Scene 12

v0.39.59 implements the player-confirmed TAG p.29 interpretation:

- a rescued victim leaves the water even when the rescuer fails and becomes
  the new trapped hero;
- friendly terms with chaos cultists are persistent campaign state.

v0.39.62 repairs the shared TAG pp.22-24 Rumor opening in existing session
`436591f8127741a586f4d3eae4ab264c`. After deploying and force-refreshing,
resume that session; do not generate another Rumor 4:

1. Confirm horizontal **Investigate** and **Return to town** buttons appear
   immediately beneath Narrative. Their hover text must explain that Investigate
   enters the printed Scene and Return to town retains the Rumor for later.
2. Choose **Investigate**. The party must move directly to **The Bridge Pool**
   (Scene 12), and the opening choice buttons must be replaced by the typed
   Mutant Fish procedure.

Then check only this typed slice:

1. At **The Bridge Pool**, there must be one
   **Roll party hypnosis Saves** action, not separate manual hypnosis,
   ration, and XP buttons.
2. Confirm Narrative lists every living hero's L5 result. A chaos-tainted hero,
   if one is naturally present, must fail automatically; do not alter the live
   party merely to force this edge.
3. If anyone enters the water, confirm the panel clearly names trapped heroes
   and asks both **Who performs the rescue?** and
   **Who is pulled from the water?**
4. Resolve one rescue turn. Every hero who was in the water at the start of
   that turn loses 1 Life. The victim comes out; a failed rescuer enters the
   water. Save/dashboard/resume once during this sequence if rescue is needed.
5. On survival, confirm one persisted `d6+3` result and side-by-side
   **Keep** / **Sell** choices. Keeping adds exactly that many Food rations
   within carrying limits; selling pays 2gp each unless this campaign has
   already earned friendly chaos-cultist terms.
6. Confirm the session's minor-encounter progress increases by exactly two and
   the generated lead offers its normal readable Continue closeout.

Do not force an all-party failure on the valuable live party; automated tests
own total-party destruction, failed-rescuer role swaps, the 5gp friendship
rate, carrying-limit distribution, duplicate prevention, and XP rollover.

After this narrow gate passes, select the next exact PDF-backed TAG scene.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
