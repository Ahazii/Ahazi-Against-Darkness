# Adventure Modules

Structured adventure manifests live here. They power **imported** sessions (`SessionState.adventure_type === "imported"`), including modules authored by external AI and modules extracted from owned PDFs.

**Full specification:** [`docs/AI_ADVENTURE_MODE.md`](../../docs/AI_ADVENTURE_MODE.md)
**User-editing guide:** [`docs/ADVENTURE_MODULE_FORMAT.md`](../../docs/ADVENTURE_MODULE_FORMAT.md)

---

## Directory layout

```
data/adventures/
  README.md                          ← this file
  allowlists.json                    ← exported snapshot (regenerate with tools/export_adventure_allowlists.py); runtime prompts use live rules, not this file
  schema/
    adventure_manifest.v1.json       ← JSON Schema for validation
    adventure_package.v1.json        ← Declarative package schema for module-local maps, pins, tables, foes, classes, trackers, and procedures
  examples/
    crypt-of-whispers/
      adventure.json                 ← golden example for authors and tests
    blackmere-chapel/
      adventure.json                 ← second example (12-room branching chapel)
  crypt-of-whispers/                 ← shipped copy (seeded to DATA_DIR on first run)
    adventure.json

DATA_DIR/Adventures/                 ← runtime install location (beside game.db)
  {adventure_id}/
    adventure.json
    package.json
    maps/
    artwork/
    tables/
    notes/
    adventure.meta.json
```

**Export JSON:** a single `adventure.json` file (same schema as installed modules).
**Export ZIP:** the full `DATA_DIR/Adventures/<adventure_id>/` folder, including `adventure.json`, optional `package.json`, maps, artwork, tables, and notes.

**Do not** add test or personal modules under `data/adventures/{id}/` — only shipped examples and `examples/` belong here. User imports install to `DATA_DIR/Adventures/` beside `game.db`.

---

## Quick start — playtest in the app

1. Home → Adventure → **Crypt of Whispers (imported)** (pre-installed under `crypt-of-whispers/`).
2. Select a party → **Start Session**.
3. Explore, complete the quest (slay the Wraith), leave via the dungeon exit on **Stairs to Daylight**.

To import your own module: **AI Adventure (build prompt)** → external LLM → paste JSON in **Import adventure JSON** → Validate → Import → select the module → Start Session.

To uninstall a module you imported: Home → adventure list → **Remove** on that module (or `DELETE /api/adventures/{adventure_id}`). This deletes `DATA_DIR/Adventures/{id}/` only. End in-progress sessions first. Shipped defaults (e.g. crypt-of-whispers) may still appear from `data/adventures/` after removal and can be re-seeded on restart.

To export a module: Home → adventure list → **Export** (or `GET /api/adventures/{adventure_id}/export`). Downloads `adventure.json` for backup or re-import elsewhere.

**Play tips:** Use the command bar below the log (`look`, `go north 1`, `open east 2`, `search`, `claim`). After combat the log repeats the room description. On imported adventures, **search before claim** when a room has hidden treasure — combat no longer adds procedural loot.

See [`docs/AI_ADVENTURE_MODE.md`](../../docs/AI_ADVENTURE_MODE.md) §13 for the full playtest guide and MVP limits.

---

## Quick start for developers

1. Read [`docs/AI_ADVENTURE_MODE.md`](../../docs/AI_ADVENTURE_MODE.md).
2. Regenerate allowlists: `python tools/export_adventure_allowlists.py`
3. Validate: `python tools/validate_adventure_manifest.py data/adventures/examples/crypt-of-whispers/adventure.json`
4. Tests: `pytest tests/test_adventure_manifest.py tests/test_adventure_prompt.py tests/test_adventure_import_play.py`

---

## Quick start for adventure authors (AI or hand-written)

1. Use only **allowlisted** names — copy from the in-app **Generate prompt** output or `GET /api/adventures/allowlists` (live rules). The packaged `allowlists.json` is a snapshot only.
2. Return **only JSON** — no markdown fences or commentary.
3. Define an **open branching graph**: rooms, exits, entrance, exit, quest.
4. Use **cardinal exit directions only** (`north`, `south`, `east`, `west`).
5. Attach **triggers** (`on_enter`, `on_search`) with allowlisted mechanical references.
6. Import in the app or copy to `{adventure_id}/adventure.json` and run the validator.

Template: `examples/crypt-of-whispers/adventure.json`

---

## PDF-authored adventures

Owned PDFs stay in `DATA_DIR/Adventure PDFs` or the local `Adventures/` folder (not committed). Use Adventure Management -> PDF Module Importer -> **Scan new PDFs** to assess the source before conversion. Human reviewers extract playable room/scene data into the **same manifest format** ([`docs/CONTENT_PIPELINE.md`](../../docs/CONTENT_PIPELINE.md)). Set `source.type` to `"pdf"`.

Use Adventure Management -> PDF Module Importer -> **Create / Update Package from PDF** when the PDF adds module-local material that does not belong in the base manifest. Packages use `schema/adventure_package.v1.json` and live inside the adventure folder as `DATA_DIR/Adventures/<adventure_id>/package.json`. Package assets belong in that same adventure folder, for example `DATA_DIR/Adventures/<adventure_id>/maps/`. The PDF Import Review Workspace can extract candidate lists for locations, tables, foes, items, classes, and procedures, then lets you click through records, edit reviewed nodes, branches, notes, local tables, foes, items, trackers, procedures, and map pins before conversion to a playable manifest.

First PDF target: `caves-of-the-kobold-slave-masters.pdf`.

---

## Play status

| Item | Status |
|------|--------|
| Manifest schema | `data/adventures/schema/adventure_manifest.v1.json` |
| Package schema | `data/adventures/schema/adventure_package.v1.json` |
| User module guide | `docs/ADVENTURE_MODULE_FORMAT.md` |
| Validator | `adventure_manifest.py` + `tools/validate_adventure_manifest.py` |
| Allowlists | `build_adventure_allowlists()` + `tools/export_adventure_allowlists.py` → snapshot `allowlists.json` |
| Prompt builder | Home → **AI Adventure (build prompt)** |
| Import UI | Paste/upload → Validate → Import (same panel) |
| Remove installed | Adventure list **Remove** button or `DELETE /api/adventures/{id}` |
| Play imported | `create_session_from_manifest()` + `POST /api/sessions` |
| Pre-installed example | `crypt-of-whispers/` |
| Export from UI | Not yet (Phase 7) |
