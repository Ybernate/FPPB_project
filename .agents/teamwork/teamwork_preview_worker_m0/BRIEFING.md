# BRIEFING — 2026-10-17T18:45:00Z

## Mission
Milestone 0 Implementation (Data Acquisition & Local Indexing): Implement scripts/download_dumps.py, scripts/prepare_data.py, data/natural_products.db, app/core/data_loader.py, and app/tests/test_data_index.py.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0
- Original parent: d5e4984c-f7f9-4829-92db-92d868cf7765
- Milestone: M0

## 🔒 Key Constraints
- Follow integrity mandate: no hardcoding of test results or dummy/facade implementations.
- File ownership: only modify scripts/prepare_data.py, scripts/download_dumps.py, data/, app/core/data_loader.py, app/tests/test_data_index.py.
- Do NOT modify piloto_curcuma/ or app/tests/test_e2e_requirements.py.
- Use sqlite3 with B-Tree indices on inchikey_block1, canonical_name, clean_name, synonym.
- Streaming decompression for COCONUT and LOTUS; handle Windows csv.field_size_limit(2147483647).
- LOTUS plant taxonomy: organism_taxonomy_02kingdom == 'Archaeplastida'.
- Ensure Curcuma longa pilot metrics match 100% (239 LOTUS records, 169 distinct first blocks, 508 references).
- 100% test pass rate on app/tests/test_data_index.py and existing test suite.

## Current Parent
- Conversation ID: d5e4984c-f7f9-4829-92db-92d868cf7765
- Updated: 2026-10-17T18:36:18Z

## Task Summary
- **What to build**: Scripts to download and ingest LOTUS and COCONUT into SQLite, data loader module, unit/integration tests.
- **Success criteria**: All tests in test_data_index.py pass with 100% success; fast sub-50ms queries; verified Curcuma longa reproduction.
- **Interface contracts**: PROJECT.md § Interface Contracts
- **Code layout**: PROJECT.md § Code Layout

## Key Decisions Made
- Used WAL mode and thread-local connection pool in data_loader.py for sub-millisecond query speed.
- Created compatibility VIEW natural_products in natural_products.db for complete backward-compatibility.
- Automated verification in prepare_data.py asserting Curcuma longa metrics (239 records, 169 blocks, 508 refs) and dual provenance.
- Implemented robust autocomplete matching both canonical names, synonyms, and InChIKeys.

## Artifact Index
- scripts/download_dumps.py — Downloader for LOTUS Zenodo and COCONUT Uni-Jena dumps with streaming and retries.
- scripts/prepare_data.py — Database builder, ingestor, and ground truth verifier.
- data/natural_products.db — High-performance indexed SQLite database.
- app/core/data_loader.py — Core data access layer adhering to interface contract.
- app/tests/test_data_index.py — 18 comprehensive tests verifying ground truth, dual provenance, SLAs, and autocomplete.

## Change Tracker
- **Files modified**:
  - `scripts/download_dumps.py`: Created downloader for LOTUS & COCONUT.
  - `scripts/prepare_data.py`: Created SQLite pipeline with verification gate.
  - `data/natural_products.db`: Generated indexed database.
  - `app/core/data_loader.py`: Created data access module.
  - `app/tests/test_data_index.py`: Created unit/integration test suite.
- **Build status**: PASS (91 passed, 1 skipped).
- **Pending issues**: None.

## Quality Status
- **Build/test result**: 91 passed, 1 skipped (100% pass rate).
- **Lint status**: Clean.
- **Tests added/modified**: 18 tests in `app/tests/test_data_index.py`.

## Loaded Skills
- None specified.
