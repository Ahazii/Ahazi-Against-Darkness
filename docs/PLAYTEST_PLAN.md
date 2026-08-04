# Current Playtest Plan

Last updated: 2026-08-04. Target build: v0.39.72.

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

## Do Next: Resume Rumor 11 — Return Retry, Bank-Funded Training And Nested Layout

Rules source: Rumor 11 on TAG p.24 and Scene 3 on TAG p.26.

Live session `fc741849402d46e096b2efa52368de8f` already passed the shared
**Investigate** / **Not now — return to town** opening, its initial Scene 3
entry, camp transfers, and the v0.39.70 outer Narrative/map divider correction.
The v0.39.71 repair is deployed and passes automation, but the current live API
still reports `camped_outside=true`; current tile and stable entrance are both
`89a663cb06844bea96f0ccc2fc458d1f`. Deoldyn's service state is still open.
Those transfers persist: Sir Benedict has 0gp carried + 600gp banked = 600gp
and is eligible; Faelar has 125gp carried + 300gp banked = 425gp; Sister Joyce
and Sly Silas remain class-ineligible.

Deoldyn's existing backend already validates the selected trainee against that
hero's combined home-bank and carried gold and spends home-bank gold first. The
live screenshot exposed that the UI did not show that split clearly and that a
long generated service could leave Narrative only a tiny strip. v0.39.72 adds
the explicit carried + bank = available display and a second saved horizontal
divider between Narrative and the active service. The inner split defaults to
40/60, preserves a 96px Narrative minimum, and gives both regions independent
vertical scrollbars without replacing the outer Narrative/service-to-map
divider.

After deploying v0.39.72, force-refresh and resume that same session:

1. Confirm the save is still at Camp Outside Dungeon, then choose **Return to
   dungeon** once. Confirm camp closes, the party reaches the stable entrance,
   and the original Investigate / Not now choice does not reappear.
2. Open **Exits** and follow the already-explored route to Deoldyn's Range if
   the service is not immediately visible. Do not repeat Investigate or the
   fund transfers.
3. Confirm Sir Benedict's training row explicitly shows `Carried 0gp + Bank
   600gp = 600gp available`, remains eligible for the 600gp Level 10 fee, and
   explains bank-first payment in hover help.
4. Drag the new Narrative/service divider in both directions. Confirm Narrative
   never shrinks below 96px, Narrative and the service each scroll vertically,
   and double-click resets the inner split to about 40/60. Then confirm the
   existing combined Narrative/service-to-map divider still reveals more map,
   and the Exits and party-sheet side dividers still resize independently.
5. Select Sir Benedict as the one trainee, choose Deadly Accuracy or Dead Shot,
   and run the batch. Confirm exactly 600gp is taken from his bank before one
   automatic XP roll and that success/failure is narrated without a refund.
6. Choose **Done — finish training**, then complete the normal shared
   **Continue — return to town and finish** closeout exactly once.

Stop after this bounded Rumor 11 module and attach a Narrative Report for any
mismatch. Do not replay its passed opening, transfers, or Rumor 6; the one
return retry and movement along the already-explored route are part of this
gate. Do not mass-enable required scene completion: every remaining Rumor still
needs its own printed terminal routes.

Convert generated TAG scenes onto typed action definitions one PDF-backed
scene at a time. Inspect and cite the owned PDF scene before coding. Do not
infer procedures from prose or ask the player to choose a dice outcome.

## Automated Coverage Only

Campaign isolation, all Rumors exhausted, exact random dice, Kukla
secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item
exhaustion/Clue creation, Star-Slayer replacement, carrier death,
total-party-kill recovery, mixed-result split fleeing, and the Iron Eater's
temporary-weapon decision remain automated-only checks.
