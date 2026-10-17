# DISPATCH for teamwork_preview_explorer_survey_pilot

## Mission
Survey the existing pilot implementation in `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\` and related documents to extract:
1. Exact SPARQL query used for LOTUS/Wikidata and how results are processed.
2. Exact ChEMBL API queries, parameters, filtering logic (e.g. human, single protein, IC50/Ki, exact relation "=").
3. Exact Reactome API queries and pathway enrichment logic.
4. Chemical structure normalization and matching logic (InChIKey first block vs full InChIKey).
5. Exact numbers produced by the pilot for Curcuma longa and how they match the acceptance criteria and diapositiva_curcuma.md.
6. Formula and calculation details for the Data Coverage Score (components A, B, C, D, E).

## Relevant Files to Read:
- C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md
- C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\piloto.py
- C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\analisis_extra.py
- C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\resumen.py
- C:\Users\yediy\.gemini\antigravity\brain\de2bb0f4-4760-4c91-8338-d948a1211513\diapositiva_curcuma.md

Write your complete findings and report to:
`C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_pilot\handoff.md`
and notify the orchestrator via `send_message`.


## 2026-10-15T01:52:36Z
You are teamwork_preview_explorer_survey_pilot.
Your working directory is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_pilot
Your dispatch file is: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_pilot\DISPATCH.md
Authoritative request file: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md

Read ORIGINAL_REQUEST.md and DISPATCH.md first. Survey piloto_curcuma/ (piloto.py, analisis_extra.py, resumen.py, CSV files) and diapositiva_curcuma.md to extract the exact query formats, data mappings, numerical metrics, pilot reproduction targets, and Data Coverage Score formulas.
Write your complete structured findings to handoff.md in your working directory and notify the orchestrator via send_message when finished.
