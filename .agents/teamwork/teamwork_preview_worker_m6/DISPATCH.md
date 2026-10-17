# DISPATCH for teamwork_preview_worker_m6

## Mission: Milestone 6 (Final Integration, Pilot Verification, Under-Studied Plant Evaluation, and Spanish Documentation)
You are the Final Integration Worker. You will complete Milestone 6 according to `ORIGINAL_REQUEST.md` (R6 and Acceptance Criteria) and `PROJECT.md`:

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may create/modify:
- `README.md` (Spanish documentation)
- `requirements.txt`
- `app/tests/test_under_studied_plant.py`
- `app/tests/test_performance.py`
- Documentation files in `docs/` (if needed)

### Required Tasks
1. **Under-Studied Plant Evaluation & Selection (R6)**:
   - Systematically compare 3–4 candidate species using real data from `data/natural_products.db` and the core pipeline:
     - Candidate 1: *Smallanthus sonchifolius* (Yacón)
     - Candidate 2: *Petiveria alliacea* (Anamú)
     - Candidate 3: *Dysphania ambrosioides* (Epazote)
     - Candidate 4: *Montanoa tomentosa* (Zoapatle)
   - Compute and document for each candidate:
     - Number of reported compounds ($N$)
     - Number of distinct chemical skeletons (InChIKey Block 1)
     - ChEMBL matches
     - Human single-protein targets ($IC_{50}/K_i$)
     - Reactome recognized pathways
     - Data Coverage Score (5 components: A, B, C, D, E)
   - Select the optimal under-studied validation plant (e.g. *Smallanthus sonchifolius* or *Petiveria alliacea*) and write a dedicated test `app/tests/test_under_studied_plant.py` asserting its real metrics.

2. **Cold Search Performance Verification**:
   - Write a benchmark test `app/tests/test_performance.py` measuring the cold search execution time for *Curcuma longa* with warm cache.
   - Assert that search and data resolution complete in under 10.0 seconds (target: < 3.0s).

3. **Complete Spanish Documentation (`README.md`)**:
   - Comprehensive, polished Spanish `README.md`:
     - Título: **Conoce tu planta (v1)** — Aplicativo web para exploración fitoquímica y biológica.
     - Resumen y propósito académico para la presentación al profesor.
     - Arquitectura de integración: LOTUS + COCONUT (locales) -> ChEMBL -> Reactome.
     - Instrucciones de instalación paso a paso:
       - Requisitos (`requirements.txt`).
       - Comando único de preparación de datos: `python scripts/prepare_data.py`.
       - Comando único de ejecución de la app: `streamlit run app/main.py`.
     - Explicación de los 3 modos de búsqueda (Planta, Molécula, Proteína/Proceso) con ejemplos.
     - Detalle de la fórmula del Puntaje de Cobertura de Datos (componentes A, B, C, D, E) y su significado.
     - Documentación de la planta poco estudiada elegida, con tabla comparativa de las 4 candidatas.
     - Lista honesta de limitaciones conocidas y sesgos biológicos (dominancia de curcumina 60.7%, sesgo de paneles de anhidrasa carbónica, afinidades extremas, agrupación por bloque 1 de InChIKey, aviso de no eficacia clínica / no consejo médico, placeholder de foto para v2.0).
     - Ejecución de la suite completa de pruebas: `python -m pytest app/tests/ -v`.

4. **Verify Requirements & Tests**:
   - Create `requirements.txt` with verified compatible versions (`streamlit`, `plotly`, `rdkit`, `pandas`, `requests`, `pytest`).
   - Run full test suite:
     `python -m pytest app/tests/ -v`
     Ensure 100% pass rate.
   - Run lint check (`python -m py_compile app/main.py scripts/prepare_data.py app/core/*.py`).

Write your handoff report to `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m6\handoff.md` and notify the orchestrator via `send_message`.


## 2026-10-17T21:00:11Z
You are teamwork_preview_worker_m6.
Your working directory is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m6
Your dispatch file is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m6\DISPATCH.md
Authoritative request: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\PROJECT.md

Read DISPATCH.md first. Complete Milestone 6:
1. Evaluate 3-4 candidate under-studied species using real data and document the choice in app/tests/test_under_studied_plant.py.
2. Measure and assert cold search latency for Curcuma longa (< 10s) in app/tests/test_performance.py.
3. Write complete, high-quality Spanish README.md and requirements.txt.
4. Run full test suite across app/tests/ and verify clean compile/lint.
Write handoff report to handoff.md in your working directory and notify the orchestrator via send_message when done.
