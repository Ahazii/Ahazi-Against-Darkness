# Abyss Phase B Audit

Last updated: 2026-06-28

## Scope

Phase A (expert tier, skills, spells, secrets, hirelings) is complete per
[`ABYSS_COMPLIANCE_AUDIT.md`](ABYSS_COMPLIANCE_AUDIT.md).

Phase B now adds a playable Abyss random-dungeon profile on the EE rules base.
The profile routes room content, wandering monsters, treasure summaries, and
major Abyss monster families through `data/rules/abyss_tables.json`.

## Indexed tables

| Table key | Status | Notes |
|-----------|--------|-------|
| `abyss_room_content_table` | wired | 2d6 room/corridor routing from Abyss p.46 |
| `abyss_trap_table` | indexed | d6 trap summaries from Abyss p.47; detailed trap-resolution UI still generalized/manual |
| `abyss_treasure_table` | wired | d8 treasure summaries create claimable treasure payloads |
| `abyss_special_feature_table` | indexed | d6 feature summaries from Abyss p.50 |
| `abyss_unique_event_table` | indexed | d6 event summaries from Abyss p.59; long-tail effects remain log-guided |
| `abyss_vermin_table` / `abyss_minions_table` / `abyss_boss_table` / `abyss_weird_table` / `abyss_dragon_table` | wired | Spawn rows create `EnemyState` entries with Abyss tags, levels, attacks, Life, treasure metadata, and generalized on-hit/start hooks where available |

## Remaining gaps

1. Exact automation for every long-form trap, special feature, unique event, banquet/useful-stuff result, and magical defense item.
2. Full Trial of Champions, horde handling, and multiple-boss tactical targeting rules.
3. Campaign plot automation, including plot state and victory conditions.
4. Full disease/transformation lifecycle for vampirism, Dark Plague, and lycanthropy beyond current status/on-hit hooks.
5. Large-room dragon-lair detection should receive the actual generated room key rather than using the regular boss branch.

## Tests

- `tests/test_program_phase4.py::test_abyss_phase_b_room_content_table_indexed`
- `tests/test_abyss_runtime.py`
