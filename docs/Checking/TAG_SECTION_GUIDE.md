# TAG Section Guide

This guide explains the whole Tales from the Adventurers' Guild section in the app: settlement downtime, TAG banking, troupe management, travel, Streetwise, storage, adventure generation, route tracking, scene rewards, XP markers, Guild spells, and after-adventure cleanup.

Use the TAG section from Home -> Adventure -> TAG Settlement. It is a town or village downtime surface, not the Camp Outside Dungeon panel. The in-app guide link opens `TAG_SECTION_GUIDE.html`; this markdown file is the source/checking copy.

## Before an Adventure

1. Enable **Use Adventurers Guild banking** if you want the TAG settlement bank ledger available alongside the legacy camp bank.
2. Open **Settlement** and set the town name, size modifier, and notes. Use **Roll size** when the settlement is random.
3. Use **Troupe manager** to add roster heroes to the TAG troupe, remove members, list member status, and choose the active party. Mark Guild membership and coffers if the troupe belongs to the Adventurers Guild.
4. Use **Availability** to check special TAG items or services. The app rolls d6 plus settlement size and logs normal price, 20% surcharge, or unavailable.
5. Use **Bank transfers**, **Buyer**, **Storage**, **Magic Lockers**, and **Services** for explicit bank migration, purchases, storage, gambling, lockers, treasure maps, moneylenders, horns, oil, aspergillum, and similar downtime procedures.
6. Use **Maps and Adventure Leads** to create a Rumor Scene, Treasure Map, Thematic Dungeon, or Guild Job. The generated module appears in the normal Adventure section/dropdown.

## TAG Banking

TAG banking is separate from ordinary roster gold and the Camp Outside Dungeon bank.

- **Legacy camp bank remains available at camp**: the Camp Outside Dungeon Bank button still deposits and withdraws home-bank gold without TAG fees. This preserves old campaign workflows.
- **TAG bank is a settlement ledger**: TAG bank accounts are handled from the TAG settlement panel and TAG actions dialog. The local app references cite TAG banking and settlement services on TAG pp.9-15; the owned PDF should be checked before treating the TAG bank as available away from settlements.
- **Bank transfers**: open Bank transfers to convert one character or the whole roster into per-character TAG accounts. You can include legacy bank gold from matching active/saved session party members and choose whether the 10% deposit fee applies. The app logs the ruling either way.
- **Bank deposit**: in TAG Actions, choose a character, enter Amount gp, choose Finance -> Bank deposit. The app deducts the deposit plus a 10% fee and stores the deposit in that character's TAG bank account.
- **Bank withdraw**: in TAG Actions, choose a character, enter Amount gp, choose Finance -> Bank withdraw. The app moves that much from the TAG account back to the character.
- **Inheritance note**: choose the account owner, put the heir name in Note, choose Finance -> Inheritance note.
- **Inheritance transfer**: choose the heir/recipient character and choose Finance -> Inheritance transfer. The app finds a matching heir note, transfers the account after 20% tax, zeroes the donor account, and logs the result.
- **Robbery risk/recovery**: use Finance for hidden-storage robbery risk and recovery logging.
- **Purchases**: the normal equipment shop and TAG Buyer section spend character gold. If a character wants to use TAG banked gold, withdraw or transfer it first so the spending step is explicit and auditable.

The **Route / XP / Bank summary** under Services and Log shows recent bank balances and heirs.

## During a TAG Adventure

Use the normal Adventure section to play the generated module. TAG-specific follow-up decisions are handled from the **TAG Actions** button in the exploration side action bar, so the branch choice is made at the point of play without crowding the map/exits area.

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
