# Adventure Modules

Structured adventure manifests live here. They power **imported** sessions (`SessionState.adventure_type === "imported"`), including modules authored by external AI and modules extracted from owned PDFs.

**Full specification:** [`docs/AI_ADVENTURE_MODE.md`](../../docs/AI_ADVENTURE_MODE.md)

---

## Directory layout

```
data/adventures/
  README.md                          ← this file
  allowlists.json                    ← generated; names the engine accepts (do not hand-edit)
  schema/
    adventure_manifest.v1.json       ← JSON Schema for validation
  examples/
    crypt-of-whispers/
      adventure.json                 ← golden example for authors and tests
  {adventure_id}/
    adventure.json                   ← installed playable module
    adventure.meta.json              ← optional import metadata (not required for play)
```

**Export (v1):** a single `{adventure_id}.json` file — the same bytes as `adventure.json`.  
**Export (future v2):** `.zip` containing `adventure.json` plus optional `assets/`.

---

## Quick start — playtest in the app

1. Home → Adventure → **Crypt of Whispers (imported)** (pre-installed under `crypt-of-whispers/`).
2. Select a party → **Start Session**.
3. Explore, complete the quest (slay the Wraith), leave via the dungeon exit on **Stairs to Daylight**.

To import your own module: **AI Adventure (build prompt)** → external LLM → paste JSON in **Import adventure JSON** → Validate → Import → select the module → Start Session.

See [`docs/AI_ADVENTURE_MODE.md`](../../docs/AI_ADVENTURE_MODE.md) §13 for the full playtest guide and MVP limits.

---

## Quick start for developers

1. Read [`docs/AI_ADVENTURE_MODE.md`](../../docs/AI_ADVENTURE_MODE.md).
2. Regenerate allowlists: `python tools/export_adventure_allowlists.py`
3. Validate: `python tools/validate_adventure_manifest.py data/adventures/examples/crypt-of-whispers/adventure.json`
4. Tests: `pytest tests/test_adventure_manifest.py tests/test_adventure_prompt.py tests/test_adventure_import_play.py`

---

## Quick start for adventure authors (AI or hand-written)

1. Use only **allowlisted** names (see `allowlists.json` or the in-app prompt).
2. Return **only JSON** — no markdown fences or commentary.
3. Define an **open branching graph**: rooms, exits, entrance, exit, quest.
4. Attach **triggers** (`on_enter`, `on_search`) with allowlisted mechanical references.
5. Import in the app or copy to `{adventure_id}/adventure.json` and run the validator.

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
| Allowlists | `tools/export_adventure_allowlists.py` → `allowlists.json` |
| Prompt builder | Home → **AI Adventure (build prompt)** |
| Import UI | Paste/upload → Validate → Import (same panel) |
| Play imported | `create_session_from_manifest()` + `POST /api/sessions` |
| Pre-installed example | `crypt-of-whispers/` |
| Export from UI | Not yet (Phase 7) |
