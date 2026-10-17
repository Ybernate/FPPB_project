# Progress — Milestone 0 Remediation

Last visited: 2026-10-17T19:46:00Z

## Status
Milestone 0 remediation completed successfully. All 185 tests passing with 0 failures.

## Checklist
- [x] Investigate current `scripts/prepare_data.py`, `scripts/download_dumps.py`, `app/core/data_loader.py`, `app/tests/test_data_index.py`.
- [x] Check raw data availability (`data/raw/` or download script).
- [x] Design genuine COCONUT ingestion streaming logic (`ingest_coconut_raw`).
- [x] Identify authentic IUPAC InChIKeys and canonical SMILES for Curculonol A/B, Zedoarondiol, Procurcumenol, Curcumenone, and candidate plant compounds (Uvedalin, Enhydrin, Sonchifolin, Chlorogenic acid, Dibenzyl trisulfide, Petivericin, Leridal, Ascaridole, Isoascaridole, Pinocarvone).
- [x] Optimize database schema: `idx_organisms_canonical_nocase`, update compound autocomplete with indexed UNION queries, update `get_plant_compounds` to eliminate `SCAN o`.
- [x] Populate `reference_dois` in occurrences insertion for LOTUS and COCONUT.
- [x] Rebuild database with `prepare_data.py` and verify zero table scans via `EXPLAIN QUERY PLAN`.
- [x] Verify zero invalid InChIKeys in DB.
- [x] Run full test suite and confirm 100% pass rate.
- [x] Write handoff report and notify orchestrator.
