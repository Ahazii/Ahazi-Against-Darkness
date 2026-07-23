# Current Playtest Plan

Last updated: 2026-07-23. Target build: v0.39.43 Invisible Gremlins sequencing, visible tally, and Disbelief scroll test.

This file contains only the remaining player checks. Earlier EE, Abyss, Forsaken Depths, Citadel, and Bofto Scene 9/14/17/19 passes are recorded in `docs/STATUS.md` and must not be repeated unless one of the checks below finds a regression.

## Do Next

### 1. Deploy And Refresh

1. Deploy `v0.39.43` from `main` to Unraid at `http://192.168.1.55:8001`.
2. Force-refresh until the app header reports `v0.39.43`.
3. Resume session `1996ab8f2fc940cc9605f82c88798d26`. Confirm Adventure View visibly shows **Major Foes: 1** without opening room details.

Campaign and Rumor Continuity passed on v0.39.37 and has been removed. Do not repeat it.

Developer Grant and Two Bags of Carrying passed completely on v0.39.41 and has been removed. Do not repeat it.

### 2. Disbelief Reveal

Rules source: Expanded Edition p.74, **Disbelief**, and p.169, **Invisible Gremlins**.

1. Confirm each party member carries one **Scroll of Disbelief**. Force another **TAG Invisible Gremlins curse encounter**.
2. Before choosing what happens to the cursed object, confirm **Cast Disbelief** is available and its dropdown lists scroll holders as `(scroll)`. Cast from one scroll.
3. Confirm combat starts against `d6+1` L3 Minions with one attack, Morale -1, and one Treasure roll for the group. If a temporarily enchanted weapon is present, first choose whether it is eligible for theft; the choice must survive save/resume and must not itself remove the weapon.
4. A failed Defence must steal an eligible item instead of causing Life loss. This exact hit behavior also has automated coverage; do not repeat the fight merely to force a failed roll.

The ordinary Invisible Gremlins theft passed on v0.39.42: Repellant was consumed, both protected items survived, nine theft slots followed printed priority, Bags lost their contents, and the event counted once as a Major Foe. Do not repeat that destructive theft. v0.39.43 has automated coverage that **Keep it and resolve theft** commits that already-passed procedure immediately without showing a second Resolve button.

## Automated Coverage Only

Do not risk a valuable party to force campaign isolation, all twelve rumors being exhausted, exact random dice, Kukla secret-compartment exposure, Clockwork Armor's two-slot edge, full-party item exhaustion/Clue creation, Star-Slayer replacement, carrier death, total-party-kill curse recovery, mixed-result split fleeing, or the Iron Eater's TAG p.65 temporary-weapon decision. Focused tests own those cases.

## Stop Gate

When section 2 passes, stop adventure regression testing and resume modularisation in small tested slices. A failure reopens only that exact workflow.

The reusable typed scene-action contract is currently applied to Bofto's Scene 14. Other generated TAG modules must be converted source-by-source from their own PDF scenes; do not infer a generic procedure from prose or ask the player to choose a dice outcome.

## Reporting A Failure

Provide the campaign name, session id, current Scene/room, selected action, exact button pressed, visible result, expected PDF page/topic result, and a **Copy Narrative Report**. Include HTML only when visible controls disagree with the Narrative/debug report.
