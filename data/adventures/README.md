# Adventure Modules

Structured adventure manifests live here. They power **imported** sessions (`SessionState.adventure_type === "imported"`), including modules authored by external AI and modules extracted from owned PDFs.

**Full specification:** [`docs/AI_ADVENTURE_MODE.md`](../../docs/AI_ADVENTURE_MODE.md)

---

## Directory layout

```
data/adventures/
  README.md                          ← this file
  allowlists.json                    ← exported snapshot (regenerate with tools/export_adventure_allowlists.py); runtime prompts use live rules, not this file
  schema/
    adventure_manifest.v1.json       ← JSON Schema for validation
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
    adventure.meta.json
```

**Export (v1):** a single `{adventure_id}.json` file — the same bytes as `adventure.json`.  
**Export (future v2):** `.zip` containing `adventure.json` plus optional `assets/`.

---

## Quick start — playtest in the app

1. Home → Adventure → **Crypt of Whispers (imported)** (pre-installed under `crypt-of-whispers/`).
2. Select a party → **Start Session**.
3. Explore, complete the quest (slay the Wraith), leave via the dungeon exit on **Stairs to Daylight**.

To import your own module: **AI Adventure (build prompt)** → external LLM → paste JSON in **Import adventure JSON** → Validate → Import → select the module → Start Session.

To uninstall a module you imported: Home → adventure list → **Remove** on that module (or `DELETE /api/adventures/{adventure_id}`). This deletes `DATA_DIR/Adventures/{id}/` only. End in-progress sessions first. Shipped defaults (e.g. crypt-of-whispers) may still appear from `data/adventures/` after removal and can be re-seeded on restart.

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

Owned PDFs stay in the local `Adventures/` folder (not committed). Human reviewers extract data into the **same manifest format** ([`docs/CONTENT_PIPELINE.md`](../../docs/CONTENT_PIPELINE.md)). Set `source.type` to `"pdf"`.

First PDF target: `caves-of-the-kobold-slave-masters.pdf`.

---

## Play status

| Item | Status |
|------|--------|
| Manifest schema | `data/adventures/schema/adventure_manifest.v1.json` |
| Validator | `adventure_manifest.py` + `tools/validate_adventure_manifest.py` |
| Allowlists | `build_adventure_allowlists()` + `tools/export_adventure_allowlists.py` → snapshot `allowlists.json` |
| Prompt builder | Home → **AI Adventure (build prompt)** |
| Import UI | Paste/upload → Validate → Import (same panel) |
| Remove installed | Adventure list **Remove** button or `DELETE /api/adventures/{id}` |
| Play imported | `create_session_from_manifest()` + `POST /api/sessions` |
| Pre-installed example | `crypt-of-whispers/` |
| Export from UI | Not yet (Phase 7) |
