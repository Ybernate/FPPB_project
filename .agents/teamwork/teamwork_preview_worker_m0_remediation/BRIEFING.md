# BRIEFING — 2026-10-17T19:02:00Z

## Mission
Remediate Milestone 0: genuine COCONUT ingestion, authentic IUPAC InChIKeys, query optimization (zero full-table scans), populate reference DOIs, and verify 100% test pass rate with zero invalid InChIKeys.

## 🔒 My Identity
- Archetype: implementer_qa_specialist
- Roles: implementer, qa, specialist
- Working directory: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0_remediation
- Original parent: d5e4984c-f7f9-4829-92db-92d868cf7765
- Milestone: Milestone 0 Remediation

## 🔒 Key Constraints
- DO NOT CHEAT: zero hardcoding of test outputs, zero fake/fabricated InChIKeys.
- All InChIKeys must strictly match IUPAC 27-character standard `^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$`.
- Genuine COCONUT ingestion logic must be implemented via zipfile and csv streaming.
- EXPLAIN QUERY PLAN must show zero SCAN c or SCAN o for compound autocomplete and plant compound queries.
- 100% test pass rate on test suite.

## Current Parent
- Conversation ID: d5e4984c-f7f9-4829-92db-92d868cf7765
- Updated: 2026-10-17T19:02:00Z

## Task Summary
- **What to build**: Genuine COCONUT ingestion in `scripts/prepare_data.py`, authentic InChIKeys replacement, SQL index and query optimization in `app/core/data_loader.py` and `scripts/prepare_data.py`, populate reference DOIs in occurrences, pass tests.
- **Success criteria**: Zero invalid InChIKeys in DB, all queries indexed (no table scans), genuine COCONUT ingestion logic, reference DOIs present, test suite passes.
- **Interface contracts**: `PROJECT.md`, `ORIGINAL_REQUEST.md`.
- **Code layout**: `scripts/`, `app/core/`, `app/tests/`, `data/`.

## Key Decisions Made
- Implemented streaming COCONUT ingestion from zip/csv without mock fallbacks or dummy data.
- Replaced all 15 fabricated InChIKeys and fake SMILES with authentic IUPAC identifiers verified via PubChem.
- Populated reference DOIs across all occurrences in LOTUS and COCONUT (100% citation coverage).
- Added composite and NOCASE indexes (`idx_occ_org_refs`, `idx_syn_compound_clean`, `idx_syn_plant_clean`) eliminating full table scans.
- Added decomposed Unicode (NFD/NFC) accent normalization in `data_loader.py:normalize_clean`.
- Implemented thread-safe caching and connection PRAGMA tuning in `data_loader.py` resolving multi-threaded query burst latency.
- Added UNIQUE constraint on `synonyms(entity_type, entity_key, synonym)` to ensure idempotent re-runs.

## Artifact Index
- `DISPATCH.md` — assignment and requirements
- `BRIEFING.md` — memory and state index
- `progress.md` — heartbeat and task progress
- `handoff.md` — final handoff report

## Change Tracker
- **Files modified**:
  - `scripts/prepare_data.py`: streaming COCONUT ingestion, authentic InChIKeys, DOI population, UNIQUE synonym constraint, composite index.
  - `app/core/data_loader.py`: Unicode accent normalization, lowercase InChIKey handling, thread-safe query caching, connection PRAGMA optimization, index-targeted queries.
- **Build status**: PASS (prepare_data.py exited 0, 185 tests passed, 1 skipped)
- **Pending issues**: None

## Quality Status
- **Build/test result**: 185 passed, 1 skipped in 11.71s (100% pass rate)
- **Lint status**: Clean (Python 3.11 typed)
- **Tests added/modified**: Full suite passing including adversarial stress tests, E2E requirements, input validation, export engine, and headless UI tests

## Loaded Skills
- None requested in dispatch.
