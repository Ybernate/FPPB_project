# DISPATCH for teamwork_preview_worker_m0

## Mission: Milestone 0 Implementation (Data Acquisition & Local Indexing)
You are the Worker implementing Milestone 0 according to `PROJECT.md` and the blueprint in `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_m0\handoff.md`.

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may create/modify:
- `scripts/prepare_data.py`
- `scripts/download_dumps.py`
- `data/` (including `data/natural_products.db` and raw dump caches)
- `app/core/data_loader.py`
- `app/tests/test_data_index.py`
Do NOT modify existing files in `piloto_curcuma/` or `app/tests/test_e2e_requirements.py`.

### Required Tasks
1. Implement `scripts/download_dumps.py` and `scripts/prepare_data.py`:
   - Download or stream the LOTUS Zenodo frozen dump (`260413_frozen_metadata.csv.gz` from record `19360665`, using User-Agent `ConoceTuPlanta/1.0`).
   - Download or stream the COCONUT full CSV (`coconut_csv-10-2026.zip` from Uni-Jena S3).
   - In `prepare_data.py`, set `csv.field_size_limit(2147483647)` to prevent Windows 32-bit C long overflow.
   - Filter LOTUS land plants using `organism_taxonomy_02kingdom == 'Archaeplastida'` and `organism_taxonomy_03phylum == 'Streptophyta'`.
   - Build SQLite database `data/natural_products.db` with tables: `compounds`, `organisms`, `occurrences`, `synonyms`, `api_cache`, and B-Tree indexes on `inchikey_block1`, `canonical_name`, `clean_name`, `synonym`.
   - Provide an offline/demo mode or fast seed mode so that if network downloads take time or fail, the database is populated with verified records for Curcuma longa (~239 LOTUS records, 169 distinct first blocks, 508 references) plus key validation plants, matching pilot numbers 100%.
   - Full command: `python scripts/prepare_data.py` executes cleanly and outputs verification stats.
2. Implement `app/core/data_loader.py` with the complete interface contract:
   - `get_plant_compounds(scientific_name)`
   - `get_compound_plants(inchikey_block1)`
   - `search_plants_autocomplete(query, limit)`
   - `search_compounds_autocomplete(query, limit)`
3. Implement `app/tests/test_data_index.py`:
   - Asserts Curcuma longa yields 239 LOTUS records, 169 distinct first blocks, and 508 reference count sum.
   - Asserts Curcumin (VFLDPWHFBUODDF) is found and links to Curcuma longa.
   - Asserts query time for plant compounds and batch reverse lookups is < 50 ms.
   - Asserts dual provenance (LOTUS, COCONUT, LOTUS+COCONUT) is present.
4. Run tests:
   - `python -m pytest app/tests/test_data_index.py -v`
   - `python -m pytest app/tests/ -v`
   Ensure all tests pass.
5. Write handoff report to `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0\handoff.md` and notify orchestrator via `send_message`.


## 2026-10-15T02:31:56Z
You are teamwork_preview_worker_m0.
Your working directory is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0
Your dispatch file is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0\DISPATCH.md
Authoritative request file: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\PROJECT.md
Blueprint: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_m0\handoff.md

Read ORIGINAL_REQUEST.md and DISPATCH.md first. Implement scripts/download_dumps.py, scripts/prepare_data.py, data/natural_products.db, app/core/data_loader.py, and app/tests/test_data_index.py. Run the tests and ensure 100% pass rate.
Write your handoff report to handoff.md in your working directory and notify the orchestrator via send_message when finished.


## 2026-10-17T18:36:18Z
[From Orchestrator]
**Context**: Milestone 0 Implementation status
**Content**: Checking in on Milestone 0 implementation. progress.md was last visited at 02:35:00Z.
**Action**: Please report your current step, any blocking issues, or whether scripts/prepare_data.py and data/natural_products.db are ready.
