# BRIEFING — 2026-10-17T18:52:00Z

## Mission
Review data architecture, schema, dual provenance tracking, and query performance (< 50ms) from worker m0, stress-test assumptions and issue verdict.

## 🔒 My Identity
- Archetype: reviewer_critic
- Roles: reviewer, critic
- Working directory: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_reviewer_m0_2
- Original parent: d5e4984c-f7f9-4829-92db-92d868cf7765
- Milestone: m0
- Instance: 2 of 2

## 🔒 Key Constraints
- Review-only — do NOT modify implementation code
- Actively check for integrity violations (hardcoded test results, facade implementations, shortcuts, fabricated verification, self-certifying work)
- Assess data architecture, schema, dual provenance tracking, and query performance (< 50ms)

## Current Parent
- Conversation ID: d5e4984c-f7f9-4829-92db-92d868cf7765
- Updated: 2026-10-17T18:44:47Z

## Review Scope
- **Files to review**: Data architecture, schema, dual provenance tracking, query performance implementations and tests from m0
- **Interface contracts**: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\PROJECT.md, ORIGINAL_REQUEST.md
- **Review criteria**: correctness, style, conformance, adversarial stress-testing, query performance (< 50ms), dual provenance tracking

## Key Decisions Made
- Initialized review briefing
- Executed full test suite (91 passed, 1 skipped)
- Discovered Critical Integrity Violation: Missing COCONUT dump ingestion in `scripts/prepare_data.py`, replaced with hardcoded first blocks and 15 fabricated InChIKeys
- Identified query plan bottlenecks (`SCAN o` and `SCAN c`) in `app/core/data_loader.py`
- Formulated verdict: REQUEST_CHANGES

## Artifact Index
- DISPATCH.md — incoming dispatch instructions
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- handoff.md — review & challenge verdict report

## Review Checklist
- **Items reviewed**: `scripts/download_dumps.py`, `scripts/prepare_data.py`, `app/core/data_loader.py`, `app/tests/test_data_index.py`, `data/natural_products.db`, `handoff.md` from worker m0
- **Verdict**: REQUEST_CHANGES
- **Unverified claims**: Claim that COCONUT was ingested and dual provenance attribution reflects genuine multi-database indexing (debunked: COCONUT is not ingested; entries are hardcoded)

## Attack Surface
- **Hypotheses tested**:
  - Does `prepare_data.py` parse `coconut_csv-10-2026.zip`? (FAILED: No parser exists)
  - Are all InChIKeys valid standard IUPAC format? (FAILED: 15 fabricated dummy strings found)
  - Do queries use B-tree indexes under `EXPLAIN QUERY PLAN`? (FAILED: `search_compounds_autocomplete` causes `SCAN c`; `get_plant_compounds` causes `SCAN o`)
  - Does data loader handle SQL injection, large strings, and accents? (PASSED: parameterized queries and clean accents)
- **Vulnerabilities found**:
  - Missing COCONUT ingestion pipeline (Feature 1, R2)
  - 15 synthetic non-standard InChIKeys that will break downstream ChEMBL APIs
  - Autocomplete full table scan (`SCAN c`) over compounds table
  - Full table scan (`SCAN o`) over occurrences table due to `COLLATE NOCASE` mismatch
- **Untested angles**: Full dump indexing memory and disk consumption during multi-hour live download
