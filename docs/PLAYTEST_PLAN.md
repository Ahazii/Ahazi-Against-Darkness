# Current Playtest Plan

Last updated: 2026-07-21. Target build: v0.39.41 functional two-Bag packing, explicit Bags of Carrying, and Invisible Gremlins.

This file contains only the remaining player checks. Earlier EE, Abyss, Forsaken Depths, Citadel, and Bofto Scene 9/14/17/19 passes are recorded in `docs/STATUS.md` and must not be repeated unless one of the checks below finds a regression.

## Do Next

### 1. Deploy And Refresh

1. Deploy `v0.39.41` from `main` to Unraid at `http://192.168.1.55:8001`.
2. Force-refresh until the app header reports `v0.39.41`.
3. Use a disposable party for the Gremlin checks. In the password-gated Developer Section, enable **Show developer item grant controls**. Enable dungeon playtest controls only when forcing the Gremlin event.

Campaign and Rumor Continuity passed on v0.39.37 and has been removed. Do not repeat it.

### 2. Developer Grant And Two Bags Of Carrying

Rules source: TAG p.13, **Bag of Carrying**.

1. In Developer Section, choose a non-Barbarian and grant **Bag of Carrying** twice. Grant two different cheap items. Confirm each grant reports a developer override and the active saved session receives the items without a restart.
2. In Party Sheets, put a different cheap item in each Bag. Save, return to the Dashboard, and resume. Confirm both Bags and their separate contents remain visible.
3. Transfer only the second Bag to another magic-item-eligible hero. Confirm only that Bag's contents move with it and the first Bag is unchanged.
4. Try to transfer a Bag to a Barbarian; it must be refused. Try to sell a non-empty Bag; the app must ask you to empty it first.
5. In Developer Section, select a Barbarian and search for Bag of Carrying. Confirm it is excluded by class eligibility and cannot be granted.

### 3. Ordinary Invisible Gremlins

Rules sources: Expanded Edition pp.87, 105, 107, 169, **Gremlin Repellant** and **Invisible Gremlins**; TAG p.11 temple tags; TAG p.13 Bag of Carrying; TAG p.65 **Temporary Weapon Enchantment**.

1. Use Developer Item Grant to give one party member **Gremlin repellant**. At camp before entering, apply that dose to one specific Bag or loose item. Confirm the dose disappears and the selected target is shown as protected. Re-enter and force **TAG Invisible Gremlins curse encounter**. If the star-object choice appears, choose **Keep it** for this ordinary-theft check.
2. Confirm the app pauses with the rolled `d6+3` theft count and offers **Cast Disbelief**, eligible voluntary Resurrection/Blessing tags, and **Resolve Gremlin theft**. If the party happens to carry a temporarily enchanted weapon, confirm **Let Gremlins take [weapon]** also appears; ordinary resolution must keep it unless that explicit choice is used. Save/resume once while this choice is pending; the same count and controls must remain.
3. Resolve theft. Confirm the protected item survives, ordinary theft follows magic items -> scrolls -> potions -> weapons -> gems -> 10gp, and a stolen Bag loses everything inside it. Clockwork Armor consumes two theft slots if present.
4. Confirm the event increments the Major Foe tally once, cannot become the Final Boss, and creates no combat unless Disbelief is cast.

### 4. Disbelief Reveal

Rules source: Expanded Edition p.74, **Disbelief**, and p.169, **Invisible Gremlins**.

Run this only if the disposable party has a character with Disbelief.

1. Force another Invisible Gremlins event and cast **Disbelief** from the pending-event controls.
2. Confirm combat starts against `d6+1` L3 Minions with one attack, Morale -1, and one Treasure roll for the group. If a temporarily enchanted weapon is present, first choose whether it is eligible for theft; the choice must survive save/resume and must not itself remove the weapon.
3. A failed Defence must steal an eligible item instead of causing Life loss. This exact hit behavior also has automated coverage; do not repeat the fight merely to force a failed roll.

## Automated Coverage Only

Do not risk a valuable party to force campaign isolation, all twelve rumors being exhausted, exact random dice, Kukla secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item exhaustion/Clue creation, Star-Slayer replacement, carrier death, total-party-kill curse recovery, mixed-result split fleeing, or the Iron Eater's TAG p.65 temporary-weapon decision. Focused tests own those cases.

## Stop Gate

When sections 2-3 pass, the release gate is passed. Section 4 may be recorded as conditional if no disposable Disbelief caster is available. Stop adventure regression testing and resume modularisation in small tested slices. A failure reopens only that exact workflow.

The reusable typed scene-action contract is currently applied to Bofto's Scene 14. Other generated TAG modules must be converted source-by-source from their own PDF scenes; do not infer a generic procedure from prose or ask the player to choose a dice outcome.

## Reporting A Failure

Provide the campaign name, session id, current Scene/room, selected action, exact button pressed, visible result, expected PDF page/topic result, and a **Copy Narrative Report**. Include HTML only when visible controls disagree with the Narrative/debug report.
