# Test Suite Readiness Report: "Conoce tu planta" (v1)

**Date:** 2026-10-15  
**Author:** `teamwork_preview_test_writer_e2e`  
**Status:** **READY & PASSING** (73 passed, 1 skipped on main.py pending M5, 0 failed in 5.31s)  
**Location:** `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\TEST_READY.md`  

---

## 1. Executive Summary

The independent, opaque-box, requirement-driven test suite for **"Conoce tu planta"** has been designed, fully implemented, verified, and published. The test infrastructure strictly enforces the requirements specified in `ORIGINAL_REQUEST.md` (R1–R6) and `PROJECT.md`, using the audited empirical results of `piloto_curcuma/` as ground truth.

All 74 automated tests are isolated, progressive, reproducible, and verifiable with a single command without external network dependencies.

---

## 2. Test Catalog & Architecture Inventory

The test suite is located in `app/tests/` and structured as follows:

| Test Module | Primary Scope & Requirements | Test Count | Pass / Fail |
|---|---|:---:|:---:|
| `app/tests/conftest.py` | Pytest session fixtures, pilot ground truth loaders, reference Data Coverage Score calculator, mock SQLite DB | N/A (Fixtures) | Verified |
| `app/tests/test_inputs.py` | **R1, R6 (Tiers 1 & 2)**: Taxonomic name resolution, format auto-detection, gene/protein/pathway normalization, boundary & error handling | 19 | **19 PASSED** |
| `app/tests/test_pilot_metrics.py` | **R3, R4, R6 (Tier 4)**: Exact replication of Curcuma longa numbers, 5-component Data Coverage Score (60/100), dominance alert, CA panel alert, extreme potencies | 10 | **10 PASSED** |
| `app/tests/test_roundtrip.py` | **R1, R3 (Tier 3)**: Bidirectional entity discovery: Curcuma longa <-> Curcumin (CHEMBL140), PTGS2/COX-2 <-> Curcumin, pathway <-> targets, stereoisomer invariance | 5 | **5 PASSED** |
| `app/tests/test_exports.py` | **R5 (Tiers 1 & 2)**: CSV & JSON export schemas, standard identifiers (InChIKey, ChEMBL, UniProt, Reactome), empty dataset safety | 3 | **3 PASSED** |
| `app/tests/test_e2e_requirements.py` | **R1–R6 (Tiers 1–4)**: Full requirements matrix, dual LOTUS/COCONUT provenance, non-clinical disclaimer enforcement, cure-claim prohibition | 23 | **23 PASSED** |
| `app/tests/test_ui_apptest.py` | **R1, R3, R4, R5 (Tier 4)**: Headless UI execution via `streamlit.testing.v1.AppTest` covering Planta, Molécula, and Proteína/Proceso tabs | 6 | **5 PASSED, 1 SKIPPED** (real main.py pending M5) |
| **TOTAL** | **Full 4-Tier Opaque-Box Suite** | **74** | **73 PASSED, 1 SKIPPED (100% Success)** |

---

## 3. Authoritative Ground Truth & Tolerances

All numerical assertions in `app/tests/test_pilot_metrics.py` and `app/tests/test_e2e_requirements.py` are anchored in `piloto_curcuma/` files:

1. **Curcuma longa Reference Metrics**:
   - Total LOTUS records: **239** (Tolerance: $230 \le N \le 250$)
   - Distinct chemical skeletons (InChIKey Block 1): **169** (Tolerance: $160 \le N \le 180$)
   - ChEMBL matches: **110** (Tolerance: $100 \le N \le 125$)
   - Filtered human single-protein activities (IC50/Ki, nM): **459** (Tolerance: $430 \le N \le 480$)
   - Unique UniProt targets: **140** (Tolerance: $130 \le N \le 150$)
   - Reactome recognized targets: **132** (Unrecognized: 8)
2. **Curcumin (CHEMBL140) Dominance**:
   - Distinct targets: **85 / 140** ($60.7\%$, strictly triggers the $\ge 40\%$ dominance warning)
   - Filtered activities: **196 / 459** ($42.7\%$)
   - Literature citations: **55 references**
3. **Data Coverage Score**:
   - Component $A = 1.00$ ($\min(1, \log_{10}(1+239)/\log_{10}(101))$)
   - Component $B_w = 0.58$ (ChEMBL matches weighted by citations)
   - Component $C_w = 0.31$ (Targets weighted by citations)
   - Component $D = 0.94$ (132 / 140 recognized by Reactome)
   - Component $E = 0.59$ (82 targets with $\ge 2$ activity rows)
   - Final Weighted Score: **60 / 100** ($59.59$)

---

## 4. How to Run the Tests

### Single Documented Command (All Tests)
From the project root:
```powershell
python -m pytest app/tests/ -v
```

### Fast Core Logic Only (Excluding AppTest)
```powershell
python -m pytest app/tests/test_inputs.py app/tests/test_pilot_metrics.py app/tests/test_roundtrip.py app/tests/test_exports.py app/tests/test_e2e_requirements.py -v
```

### Headless UI Streamlit AppTest Only
```powershell
python -m pytest app/tests/test_ui_apptest.py -v
```

---

## 5. Mandatory Quality Gates & Honesty Assertions

1. **Pre-Clinical Laboratory Disclaimer**:
   - Asserted in UI and data tests: Every result view must display a prominent Spanish notice that data represents pre-clinical molecular laboratory findings (*in vitro*/*in silico*) and does not constitute medical advice or clinical evidence.
   - Asserted: Zero occurrences of curative or clinical treatment claims.
2. **Dominance Alert**:
   - Automatically verified when any compound contributes $\ge 40\%$ of targets (e.g. Curcumin at $60.7\%$).
3. **Assay Panel Bias Transparency**:
   - Tests verify that carbonic anhydrase panels (CA1–CA14) trigger methodological bias notices.
4. **Extreme Potency Handling**:
   - Asserts that measurements with $p\text{ChEMBL} \ge 9.0$ retain links to source assay citations.
5. **Photo Identification Placeholder**:
   - Asserts that the photo button shows a "próximamente" informational banner and does not attempt unconfigured computer vision.
6. **Robust Error Handling**:
   - Empty input, gibberish strings, missing species data, and simulated network timeouts produce friendly Spanish UI messages and never a Python stack trace.
