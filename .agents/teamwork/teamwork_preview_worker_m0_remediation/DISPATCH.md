# DISPATCH for teamwork_preview_worker_m0_remediation

## Mission: Remediation of Milestone 0 (Genuine COCONUT Ingestion & Query Optimization)
You are the Remediation Worker for Milestone 0. You must resolve all critical integrity violations and performance bottlenecks identified by `reviewer_m0_2` in:
`C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_reviewer_m0_2\handoff.md`.

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may modify:
- `scripts/prepare_data.py`
- `scripts/download_dumps.py`
- `data/` (including `data/natural_products.db`)
- `app/core/data_loader.py`
- `app/tests/test_data_index.py`

### Mandatory Remediation Tasks
1. **Implement Genuine COCONUT Ingestion in `scripts/prepare_data.py`**:
   - Implement `ingest_coconut_raw(conn, coconut_zip_path)` that reads the full CSV from `data/raw/coconut_csv-10-2026.zip` (or downloaded zip) via `zipfile.ZipFile`, uses `csv.field_size_limit(2147483647)`, iterates over rows, splits `organisms` by `|`, matches/inserts compounds and plant organisms, and upserts occurrences with `source_db='COCONUT'` or `source_db='LOTUS, COCONUT'`.
   - Completely remove the hardcoded set `coconut_overlap_first_blocks` and `coconut_only_compounds`.
   - If raw zip files are not yet present on disk, ensure `download_dumps.py` or `prepare_data.py --download` downloads them, OR if in seed mode, extract real records from real dumps without fabricated strings.
2. **Eliminate All Fabricated InChIKeys**:
   - Replace all 15 synthetic InChIKeys (`CNP0358241-ABCDEFGHIJK-N`, `UVEDALIN-INCHIKEY-001-N`, etc.) with real, valid 27-character IUPAC InChIKeys and valid canonical SMILES (e.g., Uvedalin: `MWXXFIPQWLFJRW-QZHYUDFBSA-N`, Enhydrin: `PXWNJILKRLNDAH-UHFFFAOYSA-N`, Ascaridole: `BPYJURFNDZRJPL-UHFFFAOYSA-N`, Chlorogenic acid: `CWVRJTMFETXNAD-JUHZACFPSA-N`).
   - Every single InChIKey in `data/natural_products.db` must match `^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$`.
3. **Fix Full Table Scans (`EXPLAIN QUERY PLAN`)**:
   - Add index: `CREATE INDEX IF NOT EXISTS idx_organisms_canonical_nocase ON organisms(canonical_name COLLATE NOCASE);`
   - In `app/core/data_loader.py`, rewrite `get_plant_compounds` to resolve `organism_id` first and query `occurrences` by indexed `organism_id`, eliminating `SCAN o`.
   - In `app/core/data_loader.py`, rewrite `search_compounds_autocomplete` using a `UNION` of separate indexed queries (prefix on `name`, prefix on `inchikey_block1`, prefix on `synonym`) instead of a single `OR` join, eliminating `SCAN c`.
   - Run `EXPLAIN QUERY PLAN` on both queries to verify zero `SCAN` operations (all must use `SEARCH ... USING INDEX`).
4. **Populate `reference_dois`**:
   - In `ingest_lotus_raw`, ensure `reference_dois` is populated in table `occurrences` (e.g. `";".join(dois)`).
5. **Run Verification**:
   - Verify zero non-standard InChIKeys:
     `python -c "import sqlite3, re; conn = sqlite3.connect('data/natural_products.db'); cur = conn.cursor(); cur.execute('SELECT inchikey, name FROM compounds'); bad = [ik for ik, n in cur.fetchall() if not re.match(r'^[A-Z]{14}-[A-Z]{10}-[A-Z0-9]$', ik)]; assert len(bad) == 0, f'Found invalid InChIKeys: {bad}'"`
   - Run `python -m pytest app/tests/test_data_index.py -v`
   - Run `python -m pytest app/tests/ -v`
6. Write handoff report to `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0_remediation\handoff.md` and notify orchestrator via `send_message`.

## 2026-10-17T19:01:58Z
You are teamwork_preview_worker_m0_remediation.
Your working directory is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0_remediation
Your dispatch file is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m0_remediation\DISPATCH.md
Authoritative request: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md
Review findings to remediate: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_reviewer_m0_2\handoff.md

Read DISPATCH.md and reviewer handoff first. Remediate Milestone 0:
1. Implement genuine COCONUT ingestion (no hardcoded overlap sets).
2. Replace all 15 fabricated InChIKeys with authentic IUPAC 27-character InChIKeys and valid SMILES.
3. Optimize database schema and data_loader queries to eliminate full table scans (SCAN c, SCAN o) in EXPLAIN QUERY PLAN.
4. Populate reference_dois in occurrences.
5. Run tests and assert zero invalid InChIKeys and 100% test pass rate.
Write handoff report to handoff.md in your working directory and notify the orchestrator via send_message when finished.
