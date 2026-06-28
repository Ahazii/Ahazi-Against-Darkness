# Abyss Phase B Audit

Last updated: 2026-06-28

## Scope

Phase A (expert tier, skills, spells, secrets, hirelings) is complete per
[`ABYSS_COMPLIANCE_AUDIT.md`](ABYSS_COMPLIANCE_AUDIT.md).

Phase B now adds a playable Abyss random-dungeon profile on the EE rules base.
The profile routes room content, wandering monsters, treasure summaries, major
Abyss monster families, and the first exact long-form feature/event automation
through `data/rules/abyss_tables.json`.

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

## Remaining gaps

1. Full Trial of Champions, horde handling, and multiple-boss tactical targeting rules.
2. Campaign plot automation, including plot state and victory conditions.
3. Full disease/transformation lifecycle for vampirism, Dark Plague, and lycanthropy beyond current status/on-hit/status hooks.
4. Large-room dragon-lair detection should receive the actual generated room key rather than using the regular boss branch.
5. Exact use-action automation for every Abyss magic/defense/useful item after it enters inventory; item names and loot choices are now present.

## Tests

- `tests/test_program_phase4.py::test_abyss_phase_b_room_content_table_indexed`
- `tests/test_abyss_runtime.py`
