# Documentation Index

This folder is split between current project guidance, rule coverage, checking guides, historical audits, generated/reference artifacts, and archived outputs.

## Current Project Docs

| Document | Purpose |
|---|---|
| `STATUS.md` | Current implementation state and recent changes. |
| `ROADMAP.md` | Planned phases and next implementation direction. |
| `ARCHITECTURE.md` | Current FastAPI/static-browser architecture and major subsystems. |
| `SUPPLEMENTS_AND_STATES.md` | Target architecture for supplements, states, terrain, maps, room tiles, and rule hooks. |
| `PROJECT_RELEVANCE_AUDIT.md` | Cleanup/relevance audit used before the supplement/state refactor. |

## Rules And Coverage

| Document | Purpose |
|---|---|
| `MASTER_RULE_COVERAGE.md` | Program-level progress across books/supplements. |
| `RULE_COVERAGE.md` | Detailed rule implementation coverage and remaining gaps. |
| `FORSAKEN_DEPTHS_ENGINE.md` | Forsaken Depths engine behavior and implementation notes. |

## Import And Content Pipeline

| Document | Purpose |
|---|---|
| `CONTENT_PIPELINE.md` | PDF/content workflow and source handling. |
| `ADVENTURE_MODULE_FORMAT.md` | User-facing adventure/package folder and JSON format. |
| `AI_ADVENTURE_MODE.md` | AI/imported adventure design and implementation plan. |

## Editors And Artwork

| Document | Purpose |
|---|---|
| `MAP_ELEMENT_EDITOR.md` | Map element editor and grid paint tools. |
| `FD_MAP_ELEMENT_EDITOR.md` | Forsaken Depths map element editor notes. |
| `ARTWORK_IDEAS.md` | Dashboard and gameplay artwork placement ideas. |

## Checking Docs

| Folder | Purpose |
|---|---|
| `Checking/` | Player-actionable/manual checking guides linked by the app. |
| `audits/` | Historical engineering compliance audits and phase audits. |
| `reference/` | Generated or reference artifacts such as reaction table lists and equipment matrix. |
| `archive/` | Historical outputs and mockups that are not primary working docs. |

## Cleanup Rule

Before moving or deleting any documentation, run `rg` for the exact filename and update links in docs, UI, and tests.
