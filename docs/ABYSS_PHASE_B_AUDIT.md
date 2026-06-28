# Abyss Phase B Audit

Last updated: 2026-06-28

## Scope

Phase A (expert tier, skills, spells, secrets, hirelings) is complete per
[`ABYSS_COMPLIANCE_AUDIT.md`](ABYSS_COMPLIANCE_AUDIT.md).

Phase B now adds a playable Abyss random-dungeon profile on the EE rules base.
The profile routes room content, wandering monsters, treasure summaries, major
Abyss monster families, and the first exact long-form feature/event automation
through `data/rules/abyss_tables.json`.

The second tactical pass wires the Abyss minion reaction tables from p.53 into
the shared reaction engine. Trial of Champions now reaches the existing duel
resolver from Abyss minions, tagged leaders are preferred as the foe champion,
and bribes count the minions in the printed group rather than accidentally
charging for an attached boss leader.

The third tactical pass enforces Abyss combat targeting rules in the combat
engine and mirrors them in the UI. Leader-lock fights now redirect illegal
targets server-side, target selectors disable illegal leader/minion choices with
hover explanations, multiple-boss rooms spread unset party targets and apply the
lone-hero secondary-boss Defense penalty, and tagged hordes multiply attacks by
the number of living characters.

The item-use pass wires Abyss inventory actions from pp.51 and 61 into the
party sheet. Elven Bread, Blessed Horseshoe, Parchment of Banishing, Medallion
of Snake Charming, Philter of Fire Breathing, and Ring of Three Wishes have
server actions plus hover-text UI controls. Abyss passive equipment now feeds
the existing combat math for undead/vampire defenses, magic armor, silver
weapons, blessed stakes, and Baton of Righteousness healing.

The affliction pass wires the Abyss disease/transformation loop. Dark Plague
now uses the printed L10 save, ticks on room entry, spreads room-by-room to
non-immune party members, and grants adventure-long immunity after saving,
Blessing cure, or Elven Bread. Werewolf wounds queue an end-of-encounter
lycanthropy save, infected heroes drop silver/lantern gear, monastery treatment
is available from camp, and Madness-over-Level transformation spawns the former
hero as a werewolf foe. Vampire level drain can now produce a vampire-rise
pending state that blocks ordinary resurrection until the sire is destroyed.

The campaign-plot pass adds the six Abyss campaign plots as playable state:
Assassination evidence/finale saves, Rebellion funding and battle saves, Entity
artefact-piece tracking, Invasion clue spend and artefact carrier risks, Kidnap
chosen-one rescue with exit ambush, and Enchantment dragon-blood/lich finale.
The room panel exposes plot controls with hover hints, including vampire-sire
hunting after vampire escape or level-drain death. Large Abyss rooms now route
room-content roll 12 to the Dragon Lair branch instead of the regular boss
branch.

## Indexed tables

| Table key | Status | Notes |
|-----------|--------|-------|
| `abyss_room_content_table` | wired | 2d6 room/corridor routing from Abyss p.46 |
| `abyss_trap_table` | wired | d6 trap rows from Abyss p.47 resolve through Abyss-specific trap effects |
| `abyss_treasure_table` | wired | d8 treasure summaries create claimable treasure payloads and player choice keys |
| `abyss_magic_treasure_table` / `abyss_scroll_table` / `abyss_magical_defense_table` | indexed/wired | exact item rows exposed; treasure rolls produce printed item names |
| `abyss_special_feature_table` | wired | p.50 choices/effects for banquet, lava river, Room of Horrors, chained monster, repository, and puzzle room |
| `abyss_unique_event_table` | wired | p.59 Book, Plague, Swarm, Stairs, Gold Ghost, and Mana Sink effects/choices |
| `abyss_enchanted_banquet_table` / `abyss_useful_stuff_table` | indexed/wired | exact p.60-61 rows exposed; banquet and Useful Stuff outcomes resolve through existing UI |
| `abyss_vermin_table` / `abyss_minions_table` / `abyss_boss_table` / `abyss_weird_table` / `abyss_dragon_table` | wired | Spawn rows create `EnemyState` entries with Abyss tags, levels, attacks, Life, treasure metadata, and generalized on-hit/start hooks where available |
| Abyss minion reaction tables | wired | p.53 Hairy Goblins, Ghouls, Dark Dwarves, Flying Skulls, Chaotic Ratmen, and Chaos Fanatics use their printed flee/bribe/fight/trial outcomes |
| Abyss tactical targeting | wired | p.8 leader-lock targeting, p.10 multiple-boss target split / lone-hero penalty, and p.11 horde attacks are enforced by `abyss_tactics.py`, combat target selectors, and horde attack assignment |
| Abyss item use-actions | wired | p.51 magic treasure and p.61 Useful Stuff actions: Elven Bread, Blessed Horseshoe, Parchment, Medallion, Philter, Ring wishes; passive defenses/weapons are included in combat math |
| Abyss afflictions | wired | Dark Plague L10 exposure/spread/ticks/immunity, lycanthropy exposure/treatment/transformation, and vampire level-drain resurrection block |
| Abyss campaign plots | wired/playable | Six campaign plots track progress, finale triggers, rewards, UI controls, and key Clue/gold/Life/Madness costs |
| Vampire sire hunt | wired | Vampire escape and level-drain death can track the sire; Hunt spends Clues and forces the re-encounter |
| Large-room dragon lair | wired | Abyss roll 12 detects large generated rooms and routes to `abyss_dragon_table` |

## Remaining gaps

1. Manual PDF sign-off for all campaign plot edge cases, especially optional extended-campaign chaining.
2. Longer campaign persistence polish if campaign plots need to survive across separate saved sessions rather than the active adventure session.
3. Frontend decomposition: the new controls are intentionally wired into the existing room panel, but `app.js` still needs a broader split.

## Tests

- `tests/test_program_phase4.py::test_abyss_phase_b_room_content_table_indexed`
- `tests/test_abyss_runtime.py`
- `tests/test_abyss_items.py`
- `tests/test_abyss_afflictions.py`
- `tests/test_abyss_campaign.py`
