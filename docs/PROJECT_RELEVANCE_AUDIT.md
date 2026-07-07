# Project Relevance Audit

Date: 2026-07-07

Purpose: identify which documentation, data, local files, and support scripts are current, which should be rehomed or archived, and which are cleanup candidates before the Supplement/State architecture work begins.

This audit does not delete or move anything. It is a review list for the next cleanup pass.

## Executive Summary

The repo has a solid current core, but it also has several layers of accumulated support material:

- `docs/STATUS.md`, `docs/ROADMAP.md`, `docs/MASTER_RULE_COVERAGE.md`, `docs/ARCHITECTURE.md`, `docs/RULE_COVERAGE.md`, and the PDF/import docs are still current coordination documents.
- `data/rules/` and `data/adventures/` are active shipped data, not cleanup targets.
- `.data/`, top-level `Rules/`, top-level `Adventures/`, and `assets/rules_art/local/` are ignored local/runtime/private areas. They should be cleaned carefully outside source-control cleanup.
- Several tracked docs are generated or snapshot-like outputs and should be reclassified as archive/reference material.
- The largest maintainability pressure is not random loose files; it is large source modules such as `src/app/static/app.js`, `src/app/engine/random_dungeon.py`, `src/app/static/styles.css`, `src/app/engine/tag_campaign.py`, and `src/app/main.py`.
- The Supplement/State refactor should start after a conservative cleanup of docs and ignored runtime folders, not after a broad source-code purge.

## Current Git State During Audit

Pre-existing modified files were present and were not touched:

- `data/rules/rulebook_reference.json`
- `tests/test_frontend_map_interactions.py`
- `tests/test_rulebook_reference.py`

Only this audit document was added in this pass.

## Top-Level Classification

| Path | Classification | Recommendation | Notes |
|---|---|---|---|
| `src/` | Keep current | Keep | Active app code. Refactor later by feature boundary, not by deletion. |
| `tests/` | Keep current | Keep | Large but valuable rules locks. Refactor only with matching code slices. |
| `data/rules/` | Keep current | Keep | Packaged rules source loaded by the app and tests. Future candidate for `supplements/core-ee`. |
| `data/adventures/` | Keep current | Keep | Shipped adventure schemas/examples. Future candidate for supplement package schema. |
| `assets/` | Keep current with review | Keep | Runtime uses packaged assets and seeds user asset folders. Placeholder files are intentional guidance. |
| `docs/` | Mixed | Curate | Needs an index and archive split; many docs remain active. |
| `tools/` | Mixed | Curate | Some tools are current; some are one-off/debug helpers. |
| `scripts/` | Mixed | Curate | Courtship build scripts and spell repair script need status labels. |
| `.data/` | Ignored runtime/local | Clean outside git | Contains local DBs, smoke outputs, generated assets, imported packages, and logs. |
| `Rules/` | Ignored private PDF source | Keep local, consolidate conceptually | Private PDFs are source-of-truth inputs. Future runtime name should be Supplements, but do not delete. |
| `Adventures/` | Ignored private PDF source | Keep local, consolidate conceptually | Private adventure PDFs. One exact duplicate with `Rules/Lairs_Dens_and_Burrows.pdf`. |
| `.pytest_cache/`, `__pycache__/`, `*.pyc` | Ignored generated | Safe cleanup | Untracked generated files; can be removed when desired. |

## Documentation Classification

### Keep Current

| Document | Reason |
|---|---|
| `README.md` | Entry point and docs index. Should eventually link this audit and future Supplement/State doc. |
| `docs/STATUS.md` | Current living state log. Large, but actively referenced in planning. |
| `docs/ROADMAP.md` | Current sequencing doc. |
| `docs/MASTER_RULE_COVERAGE.md` | Program-level source for book/campaign coverage. |
| `docs/ARCHITECTURE.md` | Current app architecture reference. |
| `docs/RULE_COVERAGE.md` | Rule coverage checklist and compliance links. |
| `docs/ADVENTURE_MODULE_FORMAT.md` | Active user-facing package/adventure guide; already includes `states` and `rules`. |
| `docs/AI_ADVENTURE_MODE.md` | Active imported adventure design/reference. |
| `docs/CONTENT_PIPELINE.md` | Active PDF/content pipeline reference. |
| `docs/FORSAKEN_DEPTHS_ENGINE.md` | Active supplement-specific engine reference. |
| `docs/MAP_ELEMENT_EDITOR.md` | Active editor reference. |
| `docs/FD_MAP_ELEMENT_EDITOR.md` | Active FD editor reference. |
| `docs/Checking/RULEBOOK_CHECKING_GUIDE.md` | Active manual verification guide. |
| `docs/Checking/TAG_SECTION_GUIDE.md` | Source/checking copy for TAG guide. |
| `docs/Checking/TAG_SECTION_GUIDE.html` | Linked by UI and tests; keep while the app opens HTML directly. |

### Keep As Engineering Reference, But Consider Rehoming Under `docs/audits/`

| Document | Recommendation | Reason |
|---|---|---|
| `docs/audits/EE_COMPLIANCE_AUDIT.md` | Rehomed | Useful historical compliance basis, but not a primary daily doc. |
| `docs/audits/ABYSS_COMPLIANCE_AUDIT.md` | Rehomed | Referenced by `docs/audits/ABYSS_PHASE_B_AUDIT.md` and still useful. |
| `docs/audits/ABYSS_PHASE_B_AUDIT.md` | Rehomed | Useful phase record. |
| `docs/audits/REACTIONS_AUDIT.md` | Rehomed | Referenced by coverage docs. |
| `docs/reference/REACTION_TABLES_LIST.txt` | Rehomed reference artifact | Referenced by UI text and coverage docs; candidate for generated reference with rebuild command. |
| `docs/reference/equipment-matrix.csv` | Rehomed reference artifact | README says it is dev reference and not app-loaded. |

### Archive Or Regenerate Candidates

| Path | Recommendation | Reason |
|---|---|---|
| `docs/archive/checking/signoff_280626/*.xlsx` | Archived | Tracked spreadsheet outputs are historical artifacts. |
| `docs/archive/mockups/dashboard-artwork-layout.html` | Archived | Mockup artifact; no active code reference found in this pass. |
| `docs/ARTWORK_IDEAS.md` | Keep short-term | Referenced by README, ROADMAP, and tests; still active until artwork placeholders are resolved. |

## Ignored Local/Private Areas

### `.data/`

`.data/` is ignored and currently contains local runtime state, generated packages, smoke-test databases, QA assets, logs, and PDF/import outputs. It is not source, but it may contain useful local work.

Observed examples:

- `.data/game.db`
- `.data/game-tower-copy.db`
- `.data/qa/game.db`
- `.data/codex-*`
- `.data/party-sheet-repro/`
- `.data/Adventures/`
- `.data/Adventure PDFs/`
- `.data/assets/`
- `.data/codex-uvicorn.*.log`

Recommendation:

1. Do not delete `.data/Adventure PDFs/` or `.data/Adventures/` without checking whether they contain user-reviewed package work.
2. Treat `.data/codex-*`, `.data/party-sheet-repro/`, and old smoke DB folders as cleanup candidates.
3. Keep current `.data/game.db` unless the user confirms it is disposable.
4. Before cleanup, export or copy any reviewed packages from `.data/Adventures/`.

### `Rules/` And `Adventures/`

Both folders are ignored by git and contain private source PDFs.

Important finding:

- `Adventures/Lairs_dens_and_burrows.pdf` and `Rules/Lairs_Dens_and_Burrows.pdf` have the same SHA-256 hash and are exact duplicates.

Recommendation:

- Keep these PDFs as local source-of-truth material for now.
- For the future architecture, stop thinking of these as separate kinds. Treat both as source PDFs for Supplements.
- De-duplicate only after deciding the new local folder convention, probably `Supplements/<supplement-id>/source.pdf` or `DATA_DIR/Supplements/<supplement-id>/`.

## Shipped Data Classification

### Keep Current

| Path | Reason |
|---|---|
| `data/rules/rulebook_reference.json` | Active Rules Reference source; currently modified before this audit. |
| `data/rules/monsters.json` | Active bestiary/reaction data. |
| `data/rules/dungeon_tables.json` | Active table source. |
| `data/rules/classes.json` | Active class source. |
| `data/rules/tiles.json` | Active EE room tile catalog. |
| `data/rules/forsaken_depths_tiles.json` | Active FD tile catalog. |
| `data/rules/forsaken_depths_rivers_tiles.json` | Active FD river tile catalog. |
| `data/rules/forsaken_depths_tables.json` | Active FD tables. |
| `data/rules/abyss_tables.json` | Active Abyss data. |
| `data/rules/courtship_*.json` | Active Courtship data. |
| `data/rules/tag_monsters.json` | Active TAG generated adventure support. |
| `data/adventures/schema/*.json` | Active import/package schemas. |
| `data/adventures/examples/*` | Active examples/tests. |
| `data/adventures/crypt-of-whispers/` | Shipped seed adventure. |
| `data/adventures/allowlists.json` | Snapshot generated by `tools/export_adventure_allowlists.py`; keep but mark as generated. |

Future direction:

- Do not delete these. Rehome them into a supplement-aware structure later.
- The first likely split is `core-expanded-edition`, `four-against-the-abyss`, `forsaken-depths`, `courtship`, and `tag`.

## Source Code And Test Relevance

No source files are deletion candidates from this pass. The useful finding is where modularization pressure is highest.

Largest source modules:

| File | Approx lines | Recommendation |
|---|---:|---|
| `src/app/static/app.js` | 31,225 | Refactor by UI surface after registry/supplement work starts. |
| `src/app/engine/random_dungeon.py` | 19,172 | Refactor gradually around rules hooks, state operations, terrain, and tile catalogs. |
| `src/app/static/styles.css` | 9,118 | Split by UI surface only after visual regression checks exist. |
| `src/app/engine/tag_campaign.py` | 6,706 | Keep for now; candidate for TAG supplement module boundary later. |
| `src/app/static/modern-pages.js` | 5,643 | Candidate for page/component split. |
| `src/app/main.py` | 5,160 | Candidate for router split after behavior is stable. |
| `src/app/engine/combat.py` | 3,288 | Candidate for state/rules hook integration, not immediate split. |
| `src/app/schemas.py` | 1,625 | Candidate for shared state/supplement schema additions. |

Largest test modules:

| File | Approx lines | Recommendation |
|---|---:|---|
| `tests/test_forsaken_depths_engine.py` | 2,963 | Keep; split only alongside FD module boundaries. |
| `tests/test_frontend_map_interactions.py` | 2,398 | Keep; currently modified before this audit. |
| `tests/test_tag_campaign.py` | 1,976 | Keep; split only alongside TAG module boundaries. |
| `tests/test_pdf_table_compliance.py` | 1,958 | Keep; likely important for PDF source-of-truth protection. |
| `tests/test_exploration.py` | 1,415 | Keep. |

## Tools And Scripts Classification

### Keep Current

| Path | Reason |
|---|---|
| `tools/export_adventure_allowlists.py` | Referenced by docs and active adventure workflow. |
| `tools/validate_adventure_manifest.py` | Referenced by docs and active import workflow. |
| `tools/validate_tiles.py` | Referenced by docs/UI validation. |
| `tools/validate_monsters.py` | Referenced by docs/compliance. |
| `tools/list_reaction_tables.py` | Referenced by coverage docs. |
| `tools/extract_rules_artwork.py` | Referenced by docs/tests; writes to `DATA_DIR/assets`. |
| `tools/repair_generated_adventure_modules.py` | Recently used by PDF/import workflow; keep until package importer stabilizes. |
| `tools/extract_class_assets.py` | Used by `tools/audit_class_profiles.py`; keep if class artwork pipeline remains. |
| `tools/extract_tcotfd_class_assets.py` | Keep while Courtship class art remains relevant. |
| `scripts/build_courtship_tables.py` | Keep until Courtship data is stable and reproducible. |
| `scripts/curate_courtship_tables.py` | Keep until Courtship data is stable and reproducible. |

### Review / Archive Candidates

| Path | Reason |
|---|---|
| `tools/_abyss_expert_skills_extract.txt` | Looks like a one-off extraction artifact. Archive or delete after confirming no needed source notes. |
| `tools/_dump_session_keys.py` | Debug helper; candidate for `tools/debug/` or deletion. |
| `tools/_dump_session_log.py` | Debug helper; candidate for `tools/debug/` or deletion. |
| `tools/_watch_split_party.py` | Debug helper; candidate for `tools/debug/` or deletion. |
| `tools/dump_session_anomalies.py` | Local DB inspection helper; candidate for `tools/debug/`. |
| `tools/dump_session_party.py` | Local DB inspection helper; candidate for `tools/debug/`. |
| `tools/inspect_session.py` | Local DB inspection helper; candidate for `tools/debug/`. |
| `tools/inspect_sessions.py` | Local DB inspection helper; candidate for `tools/debug/`. |
| `tools/inspect_tower_session.py` | Local DB inspection helper; candidate for `tools/debug/`; likely useful with Unraid debugging. |
| `tools/repro_camped_party_sheets.py` | Repro helper; move to `tools/repro/` or delete after issue is closed. |
| `tools/repro_party_sheet_browser.py` | Repro helper; move to `tools/repro/` or delete after issue is closed. |
| `scripts/patch_character_spells.py` | Repair script; keep only if still needed for existing saves. |
| `tools/refactor_rulebook_reference.py` | One-off migration/refactor helper; archive if no longer needed. |
| `tools/repair_final_boss_treasure.py` | One-off repair helper; archive if no longer needed. |
| `tools/repair_imported_session.py` | One-off repair helper; archive if no longer needed. |

## Asset Classification

### Keep Current

| Path | Reason |
|---|---|
| `assets/tiles/` | Packaged EE tile images. |
| `assets/tiles/forsaken_depths/` | Packaged FD tile images. |
| `assets/classes/` | Packaged class portraits used by UI. |
| `assets/icons/user/` | Seed source for user-facing icon folder. |
| `assets/Application Artwork/` | Seed placeholders for user-facing artwork slots. |
| `assets/artwork/user/` | Seed placeholders for user-facing artwork slots. |
| `assets/rules_art/README.md` | Guidance for rules artwork. |

### Review

| Path | Reason |
|---|---|
| `assets/rules_art/local/` | Ignored in `.gitignore`, but tests explicitly allowlisted current local PNG names. Confirm whether any files are accidentally staged/tracked before cleanup. |
| `assets/Application Artwork/*_REPLACE_WITH_GIF.txt` | Intentional placeholders; not junk while the app guides users to DATA_DIR assets. |
| `assets/artwork/user/**/*_REPLACE_WITH_PNG.txt` | Intentional placeholders; not junk while the app guides users to DATA_DIR assets. |

## Immediate Cleanup Plan

Do these in order, with a small commit after each approved batch:

1. Keep `docs/SUPPLEMENTS_AND_STATES.md` as the target architecture note and update it as decisions settle.
2. Keep `docs/README.md` updated so active/current docs are obvious.
3. Keep historical compliance audits in `docs/audits/`, with links updated.
4. Keep spreadsheet and HTML/mockup outputs in `docs/archive/` unless they become regenerated artifacts.
5. Move debug/repro helpers under `tools/debug/` and `tools/repro/`, or delete only after confirming no active reference.
6. Clean ignored generated files: `__pycache__/`, `*.pyc`, `.pytest_cache/`.
7. Review `.data/` manually and remove old smoke/repro DB folders after exporting useful packages.
8. Decide the local private PDF convention for the future Supplement model, then de-duplicate `Lairs Dens and Burrows`.

## Cleanup Rules

- Do not delete private PDFs without explicit confirmation.
- Do not delete `.data/game.db` or `.data/Adventures/` without checking for user-created/reviewed content.
- Do not remove tracked docs that are linked by UI/tests until links are updated.
- Do not split large source files just for size; split only along Supplement/State boundaries with tests.
- For 4AD rules behavior, the PDFs remain the source of truth.
- Before moving any doc, run `rg` for the exact filename and update links in docs, UI, and tests.

## Recommended Next Step

With `docs/SUPPLEMENTS_AND_STATES.md` and `docs/README.md` in place, the next conservative cleanup batch is:

1. Decide whether `docs/reference/REACTION_TABLES_LIST.txt` should be regenerated by command instead of hand-maintained.
2. Decide whether debug/repro tools should move under `tools/debug/` and `tools/repro/`.
3. Review ignored `.data/` smoke/repro folders after exporting useful packages.

After that, introduce the read-only supplement registry without changing gameplay.
