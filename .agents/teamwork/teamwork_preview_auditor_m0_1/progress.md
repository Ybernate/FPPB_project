# Audit Progress - Milestone 0 Forensic Audit

Last visited: 2026-10-17T18:45:50Z

## Audit Plan
1. [x] Dispatch & Baseline Context setup (ORIGINAL_REQUEST.md, PROJECT.md)
2. [ ] Phase 1: Source code inspection of `scripts/download_dumps.py`, `scripts/prepare_data.py`, `app/core/data_loader.py`
   - Hardcoded pilot/test values detection
   - Facade detection (dummy returns, stub methods)
   - Pre-populated/synthetic artifact detection
3. [ ] Database inspection of `data/natural_products.db`
   - Schema validation
   - Record counts and distributions (LOTUS vs COCONUT)
   - Curcuma longa presence and real data integrity (vs pilot reference ~239 LOTUS records)
   - Synthetic data bypass check (e.g. only curcuma inserted or real full dumps)
4. [ ] Behavioral verification
   - Script runnability / reproducible pipeline execution checks
   - Unit tests execution if present (`pytest`)
   - Query execution via `app/core/data_loader.py`
5. [ ] Adversarial stress-testing (edge cases, non-pilot plants, molecules, SQL injection, robustness)
6. [ ] Audit Report and Verdict generation (`handoff.md`, notify orchestrator)
