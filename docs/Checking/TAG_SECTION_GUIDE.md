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
- **Bank deposit**: in Adventures Guild Actions, choose a character, enter Amount gp, choose Finance -> Bank deposit. Normal bank deposits deduct the TAG p.9 one-time 10% fee. If **Guild members** is enabled and Guild coffers are above 0 gp, the app uses the TAG p.68 Guild ledger rule instead and stores excess coins for free.
- **Bank withdraw**: in Adventures Guild Actions, choose a character, enter Amount gp, choose Finance -> Bank withdraw. The app moves that much from the TAG account back to the character.
- **Inheritance note**: choose the account owner, put the heir name in Note, choose Finance -> Inheritance note.
- **Inheritance transfer**: choose the heir/recipient character and choose Finance -> Inheritance transfer. The app finds a matching heir note, transfers the account after 20% tax, zeroes the donor account, and logs the result.
- **Robbery risk/recovery**: TAG p.9 bank robbery recovery costs 3 Clues and sends the party to the Bandit Hideout lead. Hidden treasure trove recovery on TAG p.11 costs 4 Clues plus Interrogation vs L6; the app keeps that wording on hidden-trove risk entries.
- **Purchases**: the normal equipment shop and TAG Buyer section spend character gold. If a character wants to use TAG banked gold, withdraw or transfer it first so the spending step is explicit and auditable.
- **Guild discount**: TAG p.68 gives Guild members a 10% discount on mundane equipment. The app applies this to normal equipment-shop buys while the campaign is marked as Guild members and Guild coffers are above 0 gp.

The **Route / XP / Bank summary** under Services and Log shows recent bank balances and heirs.

## During a TAG Adventure

Use the normal Adventure section to play the generated module. The modern Go Adventure page is split into **Start**, **Resume**, **Generate**, **Guild Jobs**, and **Reference** tabs. The live adventure text is labelled **Narrative**. Header controls can show or hide **Current Objective**, **Text Commands**, **Exits**, and **Character Sheets** when the map needs more room. Generated Adventures Guild follow-up decisions should be handled by direct **Current Objective**, **Quest Details**, or room-prompt buttons whenever the app can infer the safe action. The **Current Objective** banner also reads the current generated-room prompt, surfaces the next likely action, and shows a lifecycle strip for Entry, Side lead, Complication, Finale, Route, Reward, XP, and Closeout. Generated Adventures Guild rooms now include a **Director** panel that names the current phase, links to Rules Reference/Tables, and explains what kind of decision matters now. **Diagnostics** shows prompt/action coverage and warnings, while **Copy Narrative Report** copies the exact player-facing Narrative first and debugging context afterwards. Its Party diagnostics label carried, banked, and total gold separately; copying the report does not change finance state. **Advanced / Manual Actions** is a fallback and should appear only when diagnostics say a missing prompt, missing branch target, or manual-only action needs it.

Generated Rumor entry prompts are a deliberate exception to the Current Objective workflow: TAG pp.22-24 gives all twelve one shared horizontal **Investigate** / **Not now — return to town** choice beneath Narrative. Investigate enters that result's explicit first numbered Scene; Not now retains the Rumor for later. The choices remain visible when Objective Details is hidden for every generated TAG quest subtype, and the strip must not display Director phases, lifecycle bookkeeping, or generic Rumor playbook prose.

The TAG pp.22-31 Rumors share one scene-host flow: start the Rumor, display its narrative, show the applicable player routes, enter the selected next Scene, attach the required typed procedure/combat/vendor/NPC/dungeon-handoff control, then resolve reward and completion. Narrative objective, **Relevant Now**, and room metadata use one special-action dispatcher; each Rumor's printed mechanics remain a registered plug-in rather than a second adventure engine. The printed audit confirms that none of the twelve is complete merely because its first Scene was reached.

| Rumor | First Scene | Scene-host plug-in |
| --- | --- | --- |
| 1 Bofto | Scene 9 | Branch chain through Scenes 14/17/18/19; typed theft Save and persistent curse |
| 2 Medusa | Scene 10 | Group Stealth/assassin procedure, Scene 1 social/combat/reward choices |
| 3 Paladin's sword | Scene 11 | Red-herring procedure with a mandatory 2-in-6 ambush roll and encounter handoff when triggered |
| 4 Mutant fish | Scene 12 | Automatic per-character hypnosis on entry, rescue, ration sale/keep, and XP procedure |
| 5 Dragon in disguise | Scene 13 | True/false social decision and later Clue-gated Dragon's Lair handoff |
| 6 Leprechauns | Scene 2 | Persisted Shoes/illusion vendor host with explicit Done |
| 7 Tamas Zeya | Scene 15 | Seven-room temple-dungeon handoff |
| 8 Shaura | Scene 16 | Two-Clue gate and ten-room cult-dungeon handoff |
| 9 Daroc | Scene 5 | Repeatable selected-searcher Streetwise, defer, and reward procedure |
| 10 Gargoyles | Scene 8 | Count/surprise, combat/reaction, skin, and bounty handling |
| 11 Deoldyn | Scene 3 | One complete paid training batch with automatic XP rolls and explicit Done |
| 12 Shinta | Scene 4 | Champion choice, Scene 7 solo Bandit Hideout handoff, and Agaratha reward |

Rumor 4's final Scene is typed: entering the pool automatically rolls and persists one L5 hypnosis Save for every living hero. One Narrative panel then owns rescuer/victim choices, rescue turns, the `d6+3` ration result, Keep/Sell, and two-minion XP from TAG p.29. Its registered action declares both `auto_start` and `required_for_completion`; the shared lifecycle registry prevents arrival completion, all-party failure ends immediately, and successful Keep/Sell opens the explicit return-to-town finish action. Existing stale `room_reached` saves repair on resume without rerolling.

Rumor 9 is also typed and required. Scene 5 remains open while the player repeats an actor-selected TAG p.20 Streetwise search, claims the reward at the Clue threshold, or chooses the non-permanent Give up route. Both reward and Give up reach a terminal state for the current session; only the reward resolves the campaign Rumor. Search progress and eligible Town Streetwise Clues survive save/resume and Give up.

Rumors 6 and 11 now reuse one persisted repeatable-service contract but keep their printed mechanics separate. Rumor 6 shows only **Investigate** / **Not now — return to town** at entry. After Investigate reaches TAG pp.25-26 Scene 2, the Blackbird Hill host permits repeated 200gp Shoes of Fast Walk purchases, at most one pair per eligible wearer, and one normally eligible automatic illusion lesson for 100gp or free after three successful pairs. A living hireling may wear a party-owned pair and uses the party Tier; animal companions may not. **Done — leave Blackbird Hill** is the only terminal service action.

Rumor 11 has the same shared opening and does not expose training until Investigate reaches TAG p.26 Scene 3. The player selects the complete simultaneous batch of living bow-capable trainees and outcomes. The app validates every trainee and exact `60gp × Level` balance before mutation, commits all payments before any automatic XP roll, retains payment on failure, and blocks all later batches. Deadly Accuracy and Dead Shot are the ordinary outcomes; only the normal/base Elf may select normal level advancement under the usual consecutive-level, tier, and spell rules. Training may be skipped. **Done — finish training** resolves the visit.

The remaining migration order is deliberately staged so the shared gate cannot deadlock a Rumor with no terminal resolver: Rumors 6/11 now have their repeatable vendor/trainer host and explicit Done actions; Rumor 3 follows after its mandatory ambush procedure; Rumor 10 after dynamic count/surprise/reaction/combat/bounty handling; Rumor 8 after both child-dungeon routes; Rumors 5/7/12 after parent-child completion; and Medusa last. `required_for_completion` is a gate, not “one click means complete”: a multi-step procedure must reach its typed terminal state.

- **Branch** logs generic social choices, Clue spends, variable counts, capture-alive outcomes, and printed gp rewards.
- **Route** records the exact scene flow: parley success/failure, Clue-gated routes, peaceful/hostile branches, skipped or unlocked scenes, solo restrictions, and final routes. Route markers are saved in campaign state and also applied to the latest generated Adventures Guild module where safe.
- **Scene result** applies common printed rewards such as the Medusa pendant, gargoyle bounty, Gorungar rewards, bandit capture, Shaura reward, Agaratha, and Dragon's Lair reveal. Daroc, Mutant Fish, and Deoldyn use their dedicated typed generated-Rumor hosts; their old generic selector entries are legacy/manual diagnostics only.
- **XP** records pending scene XP, minor encounter counts, capture XP, training XP-roll markers, or immediate XP awards.
- **Trinket** consumes carried TAG trinkets when present and applies safe markers or healing.
- **Guild spell** consumes scrolls when present, logs known-spell casts, and applies safe markers. Speedy Recovery marks settlement healing at 2 Life per day, Look Tough is consumed on the next Streetwise roll, Wizard's Luck modifies the Gambling House workflow, and the optional spell target fields record the weapon/recipient/Stealth-swap target for Temporary Weapon Enchantment, Troupe Switch, and Silence of the Mouse. Temporary Weapon Enchantment stores its seven-day campaign expiry, functions as a no-bonus magic weapon, expires after qualifying magic-only use, and retains the TAG p.65 player choice when Invisible Gremlins, revealed Gremlins, or an Iron Eater could take or destroy it.
- **Guild marker** clears supported Guild spell markers after their manual timing windows. Temporary Weapon Enchantment is excluded because its TAG p.65 expiry is automatic.

Use **Reference** for the scene/page/result note. Use **Amount** for Clue costs, reward gp, gargoyle counts, XP, or another manual-only action that explicitly asks for it. Active Rumor 6 and 11 hosts derive their exact prices from persisted state; do not enter a manual shoe, lesson, or training override.

Current generated Adventures Guild prompt coverage includes specific buttons for Rumor scene procedures, Treasure Map destinations, Thematic Dungeon procedures, and Guild Job procedures. Go Adventure also has dedicated Rumor, Treasure Map, and Thematic Dungeon audit/signoff panels with Rules Reference and Tables links. Examples include Bofto theft/curse checks, Medusa Scene 10 approach and Scene 1 stealth/reaction choices, mutant fish hypnosis, white gargoyle count/surprise/skin, leprechaun Shoes of Fast Walk purchase and illusion-spell teaching, Treasure Map cave/temple/camp/structure/lich rolls, Giant's Lair boulder/treasure handling, Ghastly Mine tables, Fiendish Abyss prisoner table, Minotaur Maze checks, Bandit Hideout stolen goods, Castle pay, Griffin eggs, Portrait persuasion/snatch, Sewers disease/Clues, and Monoceros tracking/capture. Choice, procedure, service, and vendor finales should not spawn proxy foes unless the table deliberately turns the scene hostile; the complication room should carry narrative pressure and the finale should show the exact choice, purchase, service, teaching, or procedure buttons. Scene-chain leads with local `scene_graph` data create real target Scene rooms from the extracted PDF text: reaching the first choice scene does not complete the quest, and branch buttons such as Scene 14 / Scene 17 run directly from Current Objective/Relevant Now. Printed outcome branches are automated rather than shown as player choices. Bofto Scene 14 asks who steals the object and rolls the printed thievery Save vs L6 with class modifiers; failure resolves Scene 18, while success assigns Scene 19's object to the same thief, rolls the printed L8 Will Save, applies the persistent TAG pp.30-31 curse, and closes the module. The curse then drives automatic Boss/Weird Star-Slayer checks, explicit Invisible Gremlin keep/release choice, death transfer, and campaign recovery. Rumor 2 defers Xasartha until the printed cabin approach/reaction starts combat; its `6d6` gold-or-gem bribe, Quest route, fight/fight-to-the-death routing, one major-foe XP roll, `2d6` necros, 260gp sell-untried choice, and rechargeable Scene 6 pendant Luck are typed and persistent. Generated Adventures Guild imports must not pay from the core **Epic Rewards** table; use the scene reward/action buttons and closeout signoff instead. In Treasure Map modules, ordinary room treasure remains a normal **Claim Treasure** action; Map Leads To procedures are separate generated-adventure procedure/signoff reminders such as **Underground caves room target**. Active Treasure Map Underground caves quests automate that target after it is rolled: the app stores the d6+3 target, counts explored rooms, turns the target room into the Treasure Map final Boss room with +2 Life, dead-ends unopened exits there, marks the route as recorded, and marks the objective complete when that Boss is defeated. Generated Adventures Guild quest cards also show a five-step closeout wizard for objective, route/reward, XP, Guild/banking/guidance, and signoff. Older generated modules auto-refresh compatible metadata on resume and can use **Refresh narrative** to rebuild prompt metadata, trim the former Scene 19 PDF overrun, and normalize legacy log wording. During exploration, the **Current Objective** banner should make the immediate step visible: resolve combat/traps first, claim ordinary room treasure with Claim Treasure, run/review the map procedure if it has not been recorded, explore while the app counts cave rooms, then use generated lead closeout rather than a core Epic Reward claim.

After any typed generated TAG terminal resolves, app-owned closeout presentation uses one required **Continue — return to town and finish** action. The same wording appears in Narrative, diagnostics, the compact Narrative-header control, and the prominent primary action beneath Narrative. Optional Objective Details preferences cannot hide this terminal control; save/resume preserves the result and normalizes legacy wording without replaying the printed procedure.

Daroc's Lost Familiar combines TAG p.20 Streetwise, the p.24 Rumor offer, and p.26 Scene 5. The scene displays progress and **Search for Clues**; the player chooses the acting character for each automatic L6 Streetwise attempt, and that hero pays the `d6` bribe. Successful town searches mark their Clues as Town Streetwise Clues, and only those markers count. The cost falls from two to one for a Druid, Beastmaster, cat-like hero, or cat animal companion. A separate selector chooses the living reward recipient. **Give up — return to town** ends the current adventure but returns Rumor 9 to `heard` and preserves eligible Clues, so it can be attempted later. Success spends the eligible Clues, awards the selected recipient 200gp plus one pending XP roll, and resolves the required scene once. The 200gp amount follows the Rumor offer on p.24 by player ruling; Scene 5's 100gp line on p.26 is a known error. New and resumed runtime narrative must say 200gp consistently. Narrative Debug Reports distinguish carried, banked, and total gold, which makes Streetwise bribe deductions visible even when a hero's carried coins remain at the 200gp cap. Beastmaster and companion systems themselves remain governed by the future Crucible of Classic Critters pp.11-15 implementation.

Some Adventures Guild results are not dungeons. Use the lead-structure classification before editing or playtesting a profile: **dungeon** for true room exploration, **scene_chain** for choose/go-to Scene branches, **procedure** for compact checks/red herrings/escorts that should not become fake room crawls, **vendor** for purchases or spell lessons, **trainer** for paid skill/spell training, and **handoff** for results that tell the table to generate or play a separate dungeon. Blackbird Hill is the vendor reference: keep the common Rumor opening first, then expose the persisted Shoes/lesson host and explicit Done only in Scene 2. Deoldyn's Scene 3 is the trainer reference: keep the common opening first, then select one complete bow-capable batch, validate and commit all exact `60gp × Level` payments, make all XP rolls automatically, offer normal advancement only to a base Elf, block later additions, and require Done. Shinta/Agaratha is the handoff reference case: Scene 4 chooses one eligible champion, then Scene 7 points to a solo ten-room Bandit Hideout procedure rather than a normal party room crawl. The dashboard table `tag_generated_lead_structure_table` is the editing/checking guide for these profile types.

## Manual Test Generated Adventures Guild Modules

Use this workflow when playtesting the generated Adventures Guild modules against `Tales_from_the_adventurers_guild.pdf`.

Before generating fresh modules, use **Developer > Rules PDF Import** to extract your owned Adventures Guild PDF into `DATA_DIR/tag_scene_narrative_overrides.json`. The extraction status should show 12 Rumors, 19 Scenes, and 0 suspected cut-off warnings. If warnings appear, inspect or repair the named local override entries before using them for playtesting. For repeatable targeted tests, unlock Developer and enable **Show Adventures Guild fixed-result selector**; leave it off for normal rules play so the app rolls from the printed tables.

1. **Prepare a clean test party**: create or choose four living characters, enable TAG banking if you want finance prompts, and save the active party.
2. **Create the lead**: New Dashboard -> Adventure Management -> The Adventures Guild -> Create Adventures Guild Module. Use **Random lead family** for normal rules play, or disable Random and choose a numbered **Fixed result** when the Developer playtest preference is enabled and you are retesting a specific PDF branch. The legacy route still works from Home -> Adventure -> TAG Settlement -> Maps and Adventure Leads. For targeted testing, use these result ranges:
   - Rumor Scene: 1-12.
   - Thematic Dungeon: 1-6.
   - Treasure Map destination: 1-6.
   - Guild Job: 1-6 or blank to roll.
3. **Confirm installation**: the generated module should appear in Adventure/module as an Imported Adventure Module and should be selected automatically. The title should name the TAG lead.
4. **Start the adventure**: choose your party and start the selected generated module.
5. **Check every room prompt**: in exploration, inspect the room detail panel. For new generated modules you should see a **Adventures Guild scene prompt** with source pages, target/procedure/check notes, and shortcut buttons.
6. **Hover every prompt button**: each shortcut should have a tooltip explaining what it will run, record, purchase, teach, or ask the player to choose. Safe procedure buttons may record a known roll/result directly; choice, purchase, reward, route, XP, finance, and character-specific buttons should use direct guided controls where possible.
7. **Check fallback visibility**: use **Diagnostics** and **Copy Narrative Report** when a room feels wrong. **Advanced / Manual Actions** should stay hidden unless diagnostics report missing prompt metadata, a missing scene branch target, or a manual-only action.
8. **Check reward policy**: each generated module should show No loot, Scene reward button, Purchase/service only, No automatic room loot, or Handoff dungeon loot. Compact imported modules do not roll ordinary 4AD combat treasure automatically; if the PDF grants treasure, there should be a scene/procedure button or a handoff note.
9. **Check generated-module drift**: regression coverage now walks all 30 generated module cases for scene-specific prompt actions and duplicate/stale generated prose. If a module still shows repeated contact/guidance text, use **Copy Narrative Report** so the exact save/module can be repaired.
10. **Apply only when the PDF says so**: if the prompt is a bookkeeping roll, press the matching action and compare the log text to the PDF. If the prompt is a route marker, press it only after you choose that printed branch.
11. **Check module rewrites**: for Route actions that should alter the generated module, confirm the log/status mentions the rewrite. Examples: Clue gates insert an unlocked scene, skipped side scene removes the optional room, peaceful routes suppress proxy combat, Dragon's Lair reveal updates the finale title/reference.
12. **Finish and close out**: complete the adventure, then check the generated Adventures Guild closeout panel, modern Guild page, and Banking page for closeout prompts. Resolve Guild loot share/upkeep, hidden-trove risk, robbed-account recovery, guidance items, and pending XP markers as applicable. If you sign off while work remains, the app records warnings in the lead state and session log.

Suggested coverage order:

| Group | What to generate | What to check |
|---|---|---|
| Rumors | Results 1-12 | Scene title/pages, final prompt, choice/procedure/service/vendor/handoff mode for 1/3/4/6/9/11/12, printed reward or purchase action, route/Clue prompt where present. Rumor 4 is a hypnosis/rescue/ration procedure; do not spawn a proxy Final Boss because the printed fish have no combat stats. |
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

For PDF checking, use [Rulebook Checking Guide](RULEBOOK_CHECKING_GUIDE.md). The archived spreadsheet signoff files are in `docs/archive/checking/signoff_280626/`.

Internal compliance audits such as `EE_COMPLIANCE_AUDIT.md`, `ABYSS_COMPLIANCE_AUDIT.md`, and `REACTIONS_AUDIT.md` live in `docs/audits/` because they are engineering reference documents, not player action checklists.
