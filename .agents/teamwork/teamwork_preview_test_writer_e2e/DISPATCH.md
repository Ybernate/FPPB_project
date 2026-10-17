# DISPATCH for teamwork_preview_test_writer_e2e

## Mission: Dual Track - E2E Testing Suite & Infrastructure
You are the E2E Test Specialist. Your responsibility is to design and implement an independent, opaque-box, requirement-driven test suite for "Conoce tu planta" (v1):
1. Read `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md` and `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\PROJECT.md`.
2. Inspect `piloto_curcuma/` to extract exact replication baseline targets for Curcuma longa (~239 LOTUS records, ~169 distinct first-blocks, ~110 ChEMBL matches, ~459 single-protein activities, ~140 targets, 85 from curcumin, score 60).
3. Design and write `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\TEST_INFRA.md` documenting:
   - Test architecture and runner commands (`pytest app/tests/ -v`).
   - 4-Tier test catalog:
     - Tier 1: Feature Coverage (>=5 test cases per feature across all requirements R1-R6)
     - Tier 2: Boundary & Corner Cases (empty input, syntax errors, typos, network disconnect simulation, extreme affinity values)
     - Tier 3: Cross-Feature Combinations (Plant -> Molecule -> Target -> Pathway roundtrips)
     - Tier 4: Real-World Scenarios (Curcuma longa verification, under-studied plant validation, reverse searches)
4. Implement the test cases in `app/tests/test_e2e_requirements.py` and `app/tests/test_ui_apptest.py`.
   - Use `pytest` for data and logic.
   - Use `streamlit.testing.v1.AppTest` for headless UI interaction on all 3 tabs without browser overhead.
   - Assert presence of pre-clinical laboratory disclaimers and single-molecule dominance warnings on every result screen.
   - Assert roundtrip: Curcumin (CHEMBL140) lists Curcuma longa, and Curcuma longa lists Curcumin.
5. Create `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\TEST_READY.md` summarizing the test suite and execution instructions.
6. Write handoff report to `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_test_writer_e2e\handoff.md` and notify orchestrator via `send_message`.

## 2026-10-15T02:11:50Z
You are teamwork_preview_test_writer_e2e.
Your working directory is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_test_writer_e2e
Your dispatch file is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_test_writer_e2e\DISPATCH.md
Authoritative request file: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\PROJECT.md

Read ORIGINAL_REQUEST.md and DISPATCH.md first. Design the 4-tier opaque-box E2E test suite. Create TEST_INFRA.md, write comprehensive automated test cases in app/tests/ (including pytest and Streamlit AppTest for headless UI testing of all 3 tabs), and publish TEST_READY.md when complete.
Write your handoff report to handoff.md in your working directory and notify the orchestrator via send_message when finished.

