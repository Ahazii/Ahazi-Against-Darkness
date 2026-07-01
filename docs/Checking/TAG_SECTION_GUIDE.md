# TAG Section Guide

This guide explains the whole Tales from the Adventurers' Guild section in the app: settlement downtime, TAG banking, troupe management, travel, Streetwise, storage, adventure generation, route tracking, scene rewards, XP markers, Guild spells, and after-adventure cleanup.

Source PDF: `Rules/Tales_from_the_adventurers_guild.pdf`. Page references below use the printed book page and, where useful, the PDF page in parentheses. The in-app guide link opens `TAG_SECTION_GUIDE.html`; this markdown file is the source/checking copy.

Use the TAG section from Home -> Adventure -> TAG Settlement. TAG p.1 says this supplement covers town/village activities between dungeon adventures and p.4 defines the party home base as a civilized settlement. This is separate from the app's Camp Outside Dungeon panel.

## Before an Adventure

1. Enable **Use Adventurers Guild banking** if you want the TAG settlement bank ledger available alongside the legacy camp bank.
2. Open **Settlement** and set the town name, size modifier, and notes. Use **Roll size** when the settlement is random.
3. Use **Troupe manager** to add roster heroes to the TAG troupe, remove members, list member status, and choose the active party. Mark Guild membership and coffers if the troupe belongs to the Adventurers Guild.
4. Use **Availability** to check special TAG items or services. The app rolls d6 plus settlement size and logs normal price, 20% surcharge, or unavailable.
5. Use **Bank transfers**, **Buyer**, **Storage**, **Magic Lockers**, and **Services** for explicit bank migration, purchases, storage, gambling, lockers, treasure maps, moneylenders, horns, oil, aspergillum, and similar downtime procedures.
6. Use **Maps and Adventure Leads** to create a Rumor Scene, Treasure Map, Thematic Dungeon, or Guild Job. The generated module appears in the normal Adventure section/dropdown.

## TAG Banking

TAG banking is separate from ordinary roster gold and the Camp Outside Dungeon bank.

- **Legacy camp bank remains available at camp**: the Camp Outside Dungeon Bank button still deposits and withdraws home-bank gold without TAG fees. This preserves old campaign workflows outside TAG settlement accounting.
- **TAG bank is available in any settlement size**: TAG p.9 (PDF p.13) says banks are available in any settlement size, with villages using a merchant or elders/treasury. The app therefore exposes TAG bank controls in the TAG settlement surface.
- **Banked money is available when needed**: TAG p.9 says banked money is available when needed. The app still keeps purchase spending explicit: withdraw from TAG bank before a shop/B buyer spend so the audit trail shows where the money moved.
- **Bank transfers**: open Bank transfers to convert one character or the whole roster into per-character TAG accounts. You can include legacy bank gold from matching active/saved session party members and choose whether the 10% deposit fee applies. The app logs the ruling either way.
- **Bank deposit**: in TAG Actions, choose a character, enter Amount gp, choose Finance -> Bank deposit. Normal bank deposits deduct the TAG p.9 one-time 10% fee. If **Guild members** is enabled and Guild coffers are above 0 gp, the app uses the TAG p.68 Guild ledger rule instead and stores excess coins for free.
- **Bank withdraw**: in TAG Actions, choose a character, enter Amount gp, choose Finance -> Bank withdraw. The app moves that much from the TAG account back to the character.
- **Inheritance note**: choose the account owner, put the heir name in Note, choose Finance -> Inheritance note.
- **Inheritance transfer**: choose the heir/recipient character and choose Finance -> Inheritance transfer. The app finds a matching heir note, transfers the account after 20% tax, zeroes the donor account, and logs the result.
- **Robbery risk/recovery**: TAG p.9 bank robbery recovery costs 3 Clues and sends the party to the Bandit Hideout lead. Hidden treasure trove recovery on TAG p.11 costs 4 Clues plus Interrogation vs L6; the app keeps that wording on hidden-trove risk entries.
- **Purchases**: the normal equipment shop and TAG Buyer section spend character gold. If a character wants to use TAG banked gold, withdraw or transfer it first so the spending step is explicit and auditable.
- **Guild discount**: TAG p.68 gives Guild members a 10% discount on mundane equipment. The app applies this to normal equipment-shop buys while the campaign is marked as Guild members and Guild coffers are above 0 gp.

The **Route / XP / Bank summary** under Services and Log shows recent bank balances and heirs.

## During a TAG Adventure

Use the normal Adventure section to play the generated module. The modern Go Adventure page is split into **Start**, **Resume**, **Generate**, **Guild Jobs**, and **Reference** tabs. The live adventure text is labelled **Narrative**. Header controls can show or hide **Current Objective**, **Text Commands**, **Exits**, and **Character Sheets** when the map needs more room. TAG-specific follow-up decisions are handled from the **TAG Actions** button in the exploration side action bar, so the branch choice is made at the point of play without crowding the map/exits area. The **Current Objective** banner also reads the current generated-room prompt, surfaces the next likely action, and shows a lifecycle strip for Entry, Side lead, Complication, Finale, Route, Reward, XP, and Closeout. Generated TAG rooms now include a **Director** panel that names the current phase, links to Rules Reference/Tables, and explains what kind of decision matters now. Opening TAG Actions shows **Relevant Now** shortcuts before the full selectors; the top recommendation explains why that action matters now, the current action family is listed first, and the full toolbox stays behind **Advanced TAG controls**.

- **Branch** logs generic social choices, Clue spends, variable counts, capture-alive outcomes, and printed gp rewards.
- **Route** records the exact scene flow: parley success/failure, Clue-gated routes, peaceful/hostile branches, skipped or unlocked scenes, solo restrictions, and final routes. Route markers are saved in campaign state and also applied to the latest generated TAG module where safe.
- **Scene result** applies common printed rewards such as the Medusa pendant, gargoyle bounty, Gorungar rewards, bandit capture, Shaura reward, Daroc's cat, mutant-fish rations, Agaratha, Deoldyn training, and Dragon's Lair reveal.
- **XP** records pending scene XP, minor encounter counts, capture XP, training XP-roll markers, or immediate XP awards.
- **Trinket** consumes carried TAG trinkets when present and applies safe markers or healing.
- **Guild spell** consumes scrolls when present, logs known-spell casts, and applies safe markers. Speedy Recovery marks settlement healing at 2 Life per day, Look Tough is consumed on the next Streetwise roll, Wizard's Luck modifies the Gambling House workflow, and the optional spell target fields record the weapon/recipient/Stealth-swap target for Temporary Weapon Enchantment, Troupe Switch, and Silence of the Mouse.
- **Guild marker** clears a Guild spell marker after you use that timing window.

Use **Reference** for the scene/page/result note. Use **Amount** for Clue costs, reward gp, gargoyle counts, XP, or training override values depending on the selected action.

Current generated TAG prompt coverage includes specific buttons for Rumor scene procedures, Treasure Map destinations, Thematic Dungeon procedures, and Guild Job procedures. Go Adventure also has dedicated Rumor, Treasure Map, and Thematic Dungeon audit/signoff panels with Rules Reference and Tables links. Examples include Bofto theft/curse checks, Medusa approach/reaction, mutant fish hypnosis, white gargoyle count/surprise/skin, leprechaun Shoes of Fast Walk purchase and illusion-spell teaching, Treasure Map cave/temple/camp/structure/lich rolls, Giant's Lair boulder/treasure handling, Ghastly Mine tables, Fiendish Abyss prisoner table, Minotaur Maze checks, Bandit Hideout stolen goods, Castle pay, Griffin eggs, Portrait persuasion/snatch, Sewers disease/Clues, and Monoceros tracking/capture. Social/vendor finales should not spawn proxy foes unless the table deliberately turns the scene hostile; the complication room should carry narrative pressure and the finale should show the exact purchase/service/teaching buttons. In Treasure Map modules, ordinary room treasure remains a normal **Claim Treasure** action; Map Leads To procedures are separate TAG Action/signoff reminders such as **Underground caves room target**. Active Treasure Map Underground caves quests automate that target after it is rolled: the app stores the d6+3 target, counts explored rooms, turns the target room into the Treasure Map final Boss room with +2 Life, dead-ends unopened exits there, marks the route as recorded, and marks the objective complete when that Boss is defeated. Generated TAG quest cards also show a five-step closeout wizard for objective, route/reward, XP, Guild/banking/guidance, and signoff. Older generated modules can use **Repair guidance** to rebuild generic prompt metadata and normalize legacy log wording; this does not resolve printed rewards or replace PDF/player signoff. During exploration, the **Current Objective** banner should make the immediate step visible: resolve combat/traps first, claim ordinary room treasure with Claim Treasure, run/review the map procedure if it has not been recorded, explore while the app counts cave rooms, then claim the Treasure Map quest reward after the target Boss is defeated.

## Manual Test Generated TAG Adventures

Use this workflow when playtesting the generated TAG modules against `Tales_from_the_adventurers_guild.pdf`.

1. **Prepare a clean test party**: create or choose four living characters, enable TAG banking if you want finance prompts, and save the active party.
2. **Create the lead**: New Dashboard -> Go Adventure! -> Generate -> Create TAG Adventure Lead. Leave **Random** checked to let the app choose both the lead type and result, or uncheck it to choose the lead type and let the app roll that family's result. The legacy route still works from Home -> Adventure -> TAG Settlement -> Maps and Adventure Leads. For targeted legacy/testing calls, use these detail ranges:
   - Rumor Scene: 1-12.
   - Thematic Dungeon: 1-6.
   - Treasure Map destination: 1-6.
   - Guild Job: 1-6 or blank to roll.
3. **Confirm installation**: the generated module should appear in Adventure/module as an Imported Adventure Module and should be selected automatically. The title should name the TAG lead.
4. **Start the adventure**: choose your party and start the selected generated module.
5. **Check every room prompt**: in exploration, inspect the room detail panel. For new generated modules you should see a **TAG scene prompt** with source pages, target/procedure/check notes, and shortcut buttons.
6. **Hover every prompt button**: each shortcut should have a tooltip explaining what it will prefill or run. Safe procedure buttons may record a known roll/result directly; choice, purchase, reward, route, XP, finance, and character-specific buttons should open **TAG Actions** with the relevant fields prefilled.
7. **Check TAG Actions prefill**: after clicking a prompt button, confirm Branch/Route/Scene/XP is set correctly, Reference is meaningful, Amount is correct when the PDF has a known cost/count, and the Branch helper row explains Reference/Amount.
8. **Apply only when the PDF says so**: if the prompt is a bookkeeping roll, press the matching action and compare the log text to the PDF. If the prompt is a route marker, press it only after you choose that printed branch.
9. **Check module rewrites**: for Route actions that should alter the generated module, confirm the log/status mentions the rewrite. Examples: Clue gates insert an unlocked scene, skipped side scene removes the optional room, peaceful routes suppress proxy combat, Dragon's Lair reveal updates the finale title/reference.
10. **Finish and close out**: complete the adventure, then check the generated TAG closeout panel, modern Guild page, and Banking page for closeout prompts. Resolve Guild loot share/upkeep, hidden-trove risk, robbed-account recovery, guidance items, and pending XP markers as applicable. If you sign off while work remains, the app records warnings in the lead state and session log.

Suggested coverage order:

| Group | What to generate | What to check |
|---|---|---|
| Rumors | Details 1-12 | Scene title/pages, final prompt, social/vendor mode where present, printed reward or purchase action, route/Clue prompt where present |
| Thematic dungeons | Details 1-6 | Dragon reveal, Ghastly Mine rolls, Giant boulder/treasure handling, Fiendish prisoner table, Minotaur Maze rolls, Bandit stolen goods, Go Adventure Thematic Dungeon audit/signoff panels |
| Guild Jobs | Details 1-6 | Castle pay, Gorungar rewards, Griffin eggs, Portrait persuasion/snatch, Sewers disease/Clues, Monoceros tracking/capture |
| Treasure Maps | Details 1-6 | Map Leads To notes, generated target, cave/temple/camp/structure/lich prompt behavior, TAG reference metadata, Go Adventure Treasure Map audit/signoff panels |

Record failures with four details: generated lead, room name, button/action used, and the mismatch against the PDF. If the UI has no button for a printed decision, record the exact PDF page and expected action.

## After an Adventure

1. Resolve ordinary adventure closeout in the normal session flow.
2. Open the modern **Guild Management** and **Banking and Finance** pages. The app creates TAG closeout prompts when an adventure completes.
3. In **Guild Closeout**, resolve 50% monetary loot share, Guild upkeep, used availability-reroll reset, and Guild leaving-restriction signoff. The real Guild buttons clear matching prompts automatically; use **Mark Done** only for manual signoff.
4. In **Finance Closeout**, roll hidden-trove risk, recover stolen troves, or recover bank robbery leads where prompted.
5. Return to TAG Settlement and check **Route / XP / Bank summary**.
6. Use **XP** to award any pending printed scene XP that was marked during play, then mark the closeout prompt done.
7. Use **Scene result** for rewards that were deferred until the finale.
8. Use **Finance** for bank deposits, inheritance, loan enforcement, or storage robbery procedures not already handled by the closeout prompts.
9. Update **Settlement notes** with rulings, unresolved route markers, and anything you need to check against the PDF.

## Troupe Management

The TAG troupe is now a proper roster surface rather than only an active-party picker.

- **Add member** adds a roster hero to the persistent troupe list.
- **Remove member** removes a hero from the TAG troupe list without deleting the character.
- **List members** shows each member's home/active/dead status, roster gold, current session legacy bank gold when available, and TAG bank balance.
- **Active party** is chosen from troupe members only and is capped at four selected adventurers.
- **Guild membership and coffers** remain troupe-level campaign state. Coffers are distinct from individual TAG bank accounts.
- **Travel** changes the troupe's home settlement focus and logs travel days/route math; it does not model separate locations for every roster member.

## Signoff Workflow

For PDF checking, use [Rulebook Checking Guide](RULEBOOK_CHECKING_GUIDE.md). The spreadsheet signoff files are in `docs/Checking/Outputs/signoff_280626/`.

Internal compliance audits such as `EE_COMPLIANCE_AUDIT.md`, `ABYSS_COMPLIANCE_AUDIT.md`, and `REACTIONS_AUDIT.md` remain in `docs/` because they are engineering reference documents, not player action checklists.
