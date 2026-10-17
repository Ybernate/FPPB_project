# BRIEFING — 2026-10-15T01:59:00Z

## Mission
Investigate and design the full application architecture for Streamlit webapp "Conoce tu planta" covering R1, R3, R4, R5, R6.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_app_arch
- Original parent: d5e4984c-f7f9-4829-92db-92d868cf7765
- Milestone: architecture-survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code in app/
- Scope: R1 (3 search modes/friendly entry), R3 (results per mode & Data Coverage Score), R4 (honesty/visible limitations), R5 (visual quality, botanical styling, Plotly charts, chemical drawings, export formats), R6 (testing with pytest and Streamlit AppTest)
- Output: handoff.md with 5 components (Observation, Logic Chain, Caveats, Conclusion, Verification Method)

## Current Parent
- Conversation ID: d5e4984c-f7f9-4829-92db-92d868cf7765
- Updated: 2026-10-15T01:52:36Z

## Investigation State
- **Explored paths**: ORIGINAL_REQUEST.md, webapp_plan.md, diapositiva_curcuma.md, piloto_curcuma/ (piloto.py, analisis_extra.py, resumen.py, CSV files), Python environment and package resolution checks
- **Key findings**:
  1. Python 3.11.9 on Windows cleanly resolves all required wheels (Streamlit 1.66.0, Plotly 7.1.0, RDKit 2026.9.1, Pandas 3.0.6, Requests 2.34.2, Pytest 9.1.1).
  2. Streamlit state management must handle tab switches, asynchronous API calls, and caching (@st.cache_data with disk persistence) so Curcuma longa warm-cache searches return in <10s.
  3. RDKit MolDraw2DSVG generates crisp vector depictions embedded via HTML in Streamlit cards/tables, with ChEMBL depiction API and SVG icons as robust fallbacks.
  4. Three Plotly visualizations specified: Data Funnel, Plant-Molecule-Protein Network (tripartite graph highlighting Curcumin dominance), and Reactome Pathway enrichment bars with FDR scaling.
  5. R4 honesty requirements specified with exact Spanish copy for: pre-clinical evidence disclaimer, single-compound dominance warning, carbonic anhydrase assay panel inflation warning, and extreme pChEMBL affinity alerts.
  6. Testing approach combines pytest for core algorithms and Streamlit AppTest for headless UI testing of all 3 tabs without browser overhead.
- **Unexplored areas**: none within R1, R3, R4, R5, R6 scope.

## Key Decisions Made
- Architecture structured into `app/components/` (tabs, cards, charts, chem_render, disclaimers, export) and `app/core/` (data_loader, chembl_client, reactome_client, name_resolver, scoring).
- Headless testing strategy validated using native `streamlit.testing.v1.AppTest`.
- Export formats specified for both flat tabular CSV and hierarchical JSON.

## Artifact Index
- DISPATCH.md — incoming dispatch instructions
- BRIEFING.md — situational awareness
- progress.md — liveness heartbeat
- handoff.md — final handoff report
