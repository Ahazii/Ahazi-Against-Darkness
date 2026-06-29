# TAG Section Guide

This guide explains the whole Tales from the Adventurers' Guild section in the app: settlement downtime, TAG banking, troupe management, travel, Streetwise, storage, adventure generation, route tracking, scene rewards, XP markers, Guild spells, and after-adventure cleanup.

Use the TAG section from Home -> Adventure -> TAG Settlement. It is a town or village downtime surface, not the Camp Outside Dungeon panel. The in-app guide link opens `TAG_SECTION_GUIDE.html`; this markdown file is the source/checking copy.

## Before an Adventure

1. Enable **Use Adventurers Guild banking** if you want TAG banking rules instead of the legacy free home bank.
2. Open **Settlement** and set the town name, size modifier, and notes. Use **Roll size** when the settlement is random.
3. Open **Troupe** and choose the active party. Mark Guild membership and coffers if the troupe belongs to the Adventurers Guild.
4. Use **Availability** to check special TAG items or services. The app rolls d6 plus settlement size and logs normal price, 20% surcharge, or unavailable.
5. Use **Buyer**, **Storage**, **Magic Lockers**, and **Services** for purchases, storage, gambling, lockers, treasure maps, moneylenders, horns, oil, aspergillum, and similar downtime procedures.
6. Use **Maps and Adventure Leads** to create a Rumor Scene, Treasure Map, Thematic Dungeon, or Guild Job. The generated module appears in the normal Adventure section/dropdown.

## TAG Banking

TAG banking is separate from ordinary roster gold.

- **Bank deposit**: choose a character, enter Amount gp, choose Finance -> Bank deposit. The app deducts the deposit plus a 10% fee and stores the deposit in that character's TAG bank account.
- **Bank withdraw**: choose a character, enter Amount gp, choose Finance -> Bank withdraw. The app moves that much from the TAG account back to the character.
- **Inheritance note**: choose the account owner, put the heir name in Note, choose Finance -> Inheritance note.
- **Inheritance transfer**: choose the heir/recipient character and choose Finance -> Inheritance transfer. The app finds a matching heir note, transfers the account after 20% tax, zeroes the donor account, and logs the result.
- **Robbery risk/recovery**: use Finance for hidden-storage robbery risk and recovery logging.

The **Route / XP / Bank summary** under Services and Log shows recent bank balances and heirs.

## During a TAG Adventure

Use the normal Adventure section to play the generated module. TAG-specific follow-up decisions are currently handled from Home -> Adventure -> TAG Settlement -> TAG Actions. Moving the scene-branch controls into exploration mode is a planned UI improvement because those choices happen during the adventure.

- **Branch** logs generic social choices, Clue spends, variable counts, capture-alive outcomes, and printed gp rewards.
- **Route** records the exact scene flow: parley success/failure, Clue-gated routes, peaceful/hostile branches, skipped or unlocked scenes, solo restrictions, and final routes. Route markers are saved in campaign state and also applied to the latest generated TAG module where safe.
- **Scene result** applies common printed rewards such as the Medusa pendant, gargoyle bounty, Gorungar rewards, bandit capture, Shaura reward, Daroc's cat, mutant-fish rations, Agaratha, Deoldyn training, and Dragon's Lair reveal.
- **XP** records pending scene XP, minor encounter counts, capture XP, training XP-roll markers, or immediate XP awards.
- **Trinket** consumes carried TAG trinkets when present and applies safe markers or healing.
- **Guild spell** consumes scrolls when present, logs known-spell casts, and applies safe markers. Speedy Recovery heals the selected character to full Life.
- **Guild marker** clears a Guild spell marker after you use that timing window.

Use **Reference** for the scene/page/result note. Use **Amount** for Clue costs, reward gp, gargoyle counts, XP, or training override values depending on the selected action.

## After an Adventure

1. Resolve ordinary adventure closeout in the normal session flow.
2. Return to TAG Settlement and check **Route / XP / Bank summary**.
3. Use **XP** to award any pending printed scene XP that was marked during play.
4. Use **Scene result** for rewards that were deferred until the finale.
5. Use **Finance** for bank deposits, inheritance, guild upkeep, loan enforcement, or storage robbery procedures.
6. Update **Settlement notes** with rulings, unresolved route markers, and anything you need to check against the PDF.

## Signoff Workflow

For PDF checking, use [Rulebook Checking Guide](RULEBOOK_CHECKING_GUIDE.md). The spreadsheet signoff files are in `docs/Checking/Outputs/signoff_280626/`.

Internal compliance audits such as `EE_COMPLIANCE_AUDIT.md`, `ABYSS_COMPLIANCE_AUDIT.md`, and `REACTIONS_AUDIT.md` remain in `docs/` because they are engineering reference documents, not player action checklists.
