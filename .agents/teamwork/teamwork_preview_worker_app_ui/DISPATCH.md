# DISPATCH for teamwork_preview_worker_app_ui

## Mission: Implementation of Full Application UI & Search Modes (M2 - M5)
You are the Application UI Worker. You will implement the complete Streamlit web application "Conoce tu planta" (v1) according to `PROJECT.md` and the detailed specifications in `teamwork_preview_explorer_survey_app_arch\handoff.md`.

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may create/modify:
- `app/main.py`
- `app/state.py`
- `app/styles/botanical.css`
- `app/styles/theme.py`
- `app/components/tab_plant.py`
- `app/components/tab_molecule.py`
- `app/components/tab_target_process.py`
- `app/components/cards.py`
- `app/components/charts.py`
- `app/components/chem_render.py`
- `app/components/disclaimers.py`
- `app/components/export.py`

### Key Requirements to Implement
1. **App Entrypoint & Botanical Theme (`app/main.py`, `app/styles/`)**:
   - Clean, light scientific background (`#FAFCF8`), deep botanical green (`#1B4332`, `#2D6A4F`), large indicator cards, high-contrast readable typography for a projector demo.
   - 3 tabs: "🌿 Planta", "🧪 Molécula", "🎯 Proteína / Proceso".
   - Inject custom CSS from `app/styles/botanical.css`.

2. **Tab 1: Modo Planta (`app/components/tab_plant.py`) (R1, R3, R4)**:
   - Search box with autocompletion and synonym resolution (`name_resolver.resolve_plant_name`).
   - Clickable example pills: "Cúrcuma", "Manzanilla", "Ajo", "Yacón".
   - Taxonomic confirmation card: accepted scientific name, family, vernacular names (ES/EN), and image if available.
   - Button: "📷 Identificar por foto (próximamente)" displaying an informative modal explaining computer vision is planned for v2.0.
   - Compounds table ordered by reference count, with drug-likeness (MW, ALogP, TPSA, QED), ChEMBL match badge, structure drawings, and target counts.
   - Data Coverage Score card with full 5-component breakdown (A, B, C, D, E) and formula display ($Score = 60$ for Curcuma longa).
   - Mandatory disclaimers on every result screen (Pre-clinical laboratory evidence notice, no clinical/medical claims).
   - Dominance alert card: triggered when top molecule provides >= 40% of targets (Curcumin 60.7%).
   - Assay panel bias alert: triggered when carbonic anhydrase isoforms are present.
   - Links to ChEMBL assay cards for extreme affinities ($p\text{ChEMBL} \ge 9.0$).

3. **Tab 2: Modo Molécula (`app/components/tab_molecule.py`) (R1, R3, R4)**:
   - Search box accepting common name, synonym, SMILES, InChIKey (full or first block), or ChEMBL ID, with auto-detection of format.
   - Clickable example pills: "Curcumina", "Quercetina", "Ácido cafeico", "CHEMBL140".
   - 2D chemical structure drawing generated via RDKit SVG (`app/components/chem_render.py`) with transparent background and ChEMBL depiction fallback.
   - Results list: plant species containing the molecule or its stereochemical variants (grouped by InChIKey block 1), with source database indicators (LOTUS, COCONUT, LOTUS+COCONUT).
   - ChEMBL targets table with measured affinities (IC50/Ki in nM, relation, pChEMBL).
   - Reactome enriched pathways.
   - Molecule evidence indicator card.

4. **Tab 3: Modo Proteína / Proceso (`app/components/tab_target_process.py`) (R1, R3, R4)**:
   - Two sub-modes: "Proteína / Gen" (e.g. PTGS2, COX-2) and "Proceso Biológico (Reactome)" (e.g. "inflamación", "apoptosis").
   - Clickable examples.
   - Default filter: "Solo moléculas con planta fuente" (toggle switch to include all ChEMBL).
   - Potency slider for pChEMBL threshold (default: $p\text{ChEMBL} \ge 6.0$, exact measurements).
   - Results link targets and processes directly back to active molecules and their source plants.

5. **Plotly Interactive Charts (`app/components/charts.py`) (R5)**:
   - Data Funnel (`plotly.graph_objects.Funnel`): 6 stages from LOTUS/COCONUT to enriched pathways.
   - Tripartite Network Graph (`plotly.graph_objects.Scatter`): Plant -> Molecule -> Protein targets, visually highlighting Curcumin's 85 target connections.
   - Horizontal Pathway Bar Chart: Sorted by $-\log_{10}(\text{FDR})$ with interactive affinity filtering.

6. **Export Subsystem (`app/components/export.py`) (R5)**:
   - CSV export containing standard identifiers (InChIKey, InChIKey-Block1, SMILES, ChEMBL ID, UniProt ID, Reactome stId, references, source_db).
   - JSON export with structured metadata, score breakdown, compounds, activities, and pathways.
   - `st.download_button` for both formats in every mode.

7. **Verification**:
   - Run the complete test suite:
     `python -m pytest app/tests/ -v`
   - Ensure all 74+ tests pass (including `test_ui_apptest.py` against real `app/main.py`).
   - Run `python -c "import streamlit; from streamlit.testing.v1 import AppTest; at = AppTest.from_file('app/main.py'); at.run(); assert not at.exception; print('AppTest passed cleanly')"`

Write handoff report to `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_app_ui\handoff.md` and notify orchestrator via `send_message`.


## 2026-10-17T19:59:58Z
You are teamwork_preview_worker_app_ui.
Your working directory is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_app_ui
Your dispatch file is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_app_ui\DISPATCH.md
Authoritative request: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md
Project plan: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\PROJECT.md
App architecture report: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_app_arch\handoff.md

Read DISPATCH.md and reference reports first. Implement:
1. app/styles/botanical.css & app/styles/theme.py
2. app/state.py
3. app/components/cards.py, charts.py, chem_render.py, disclaimers.py, export.py
4. app/components/tab_plant.py, tab_molecule.py, tab_target_process.py
5. app/main.py
Run pytest across app/tests/ (including test_ui_apptest.py) and ensure 100% pass rate.
Write handoff report to handoff.md in your working directory and notify the orchestrator via send_message when done.
