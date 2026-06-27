# Abyss Phase B Audit

Last updated: 2026-06-24

## Scope

Phase A (expert tier, skills, spells, secrets, hirelings) is complete per
[`ABYSS_COMPLIANCE_AUDIT.md`](ABYSS_COMPLIANCE_AUDIT.md).

Phase B adds indexed Abyss procedural tables before wiring a dedicated Abyss
ruleset profile or adventure mode.

## Indexed tables

| Table key | Status | Notes |
|-----------|--------|-------|
| `abyss_room_content_table` | indexed | Six row stubs in `data/rules/abyss_tables.json`; engine routing deferred |

## Next steps

1. PDF row-lock each Abyss table (vermin, minions, weird, traps, treasure, unique events).
2. Add `abyss` ruleset profile gated by `source_books: ["ee", "abyss"]`.
3. Route `_roll_content` / FD-equivalent placement through Abyss tables when profile active.
4. Extend bestiary spawn keys already present for Abyss foes.

## Tests

- `tests/test_program_phase4.py::test_abyss_phase_b_room_content_table_indexed`
