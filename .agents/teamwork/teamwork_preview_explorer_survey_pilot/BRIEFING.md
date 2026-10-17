# BRIEFING — 2026-10-15T01:58:30Z

## Mission
Survey the existing pilot implementation in piloto_curcuma/ and diapositiva_curcuma.md to extract query formats, data mappings, numerical metrics, pilot reproduction targets, and Data Coverage Score formulas.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey pilot implementation, extract queries, mappings, metrics, Data Coverage Score formulas
- Working directory: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_pilot
- Original parent: d5e4984c-f7f9-4829-92db-92d868cf7765
- Milestone: preview/survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Extract exact queries (SPARQL, ChEMBL, Reactome), parameters, and filtering logic
- Extract exact chemical structure normalization and matching logic
- Extract exact numbers produced by Curcuma longa pilot
- Extract formula and calculation details for Data Coverage Score (A, B, C, D, E)

## Current Parent
- Conversation ID: d5e4984c-f7f9-4829-92db-92d868cf7765
- Updated: not yet

## Investigation State
- **Explored paths**: `piloto_curcuma/piloto.py`, `piloto_curcuma/analisis_extra.py`, `piloto_curcuma/resumen.py`, `piloto_curcuma/resumen.json`, `compuestos.csv`, `actividades.csv`, `rutas.csv`, `diapositiva_curcuma.md`, `webapp_plan.md`, `ORIGINAL_REQUEST.md`.
- **Key findings**:
  - SPARQL query uses `wdt:P225`, `p:P703/ps:P703`, `wdt:P235`, `wdt:P233`, `rdfs:label`, and `prov:wasDerivedFrom` for citation counts (`nref`).
  - ChEMBL queries: matching by InChIKey (batches of 25); activities for IC50/Ki in nM on Homo sapiens; single protein filter (`target_type == 'SINGLE PROTEIN'` with 1 UniProt accession).
  - Reactome POST to `/AnalysisService/identifiers/projection?pageSize=15&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL`.
  - Structure normalization: 239 LOTUS records map to 169 distinct first blocks (skeletons); 42 records without exact ChEMBL match have stereoisomers that match.
  - Data Coverage Score: $100 \times (0.10 \cdot A + 0.20 \cdot B_w + 0.30 \cdot C_w + 0.15 \cdot D + 0.25 \cdot E) = 60$ ($B_w, C_w$ reference-weighted).
  - Biases: Curcumin contributes 61% of targets (85/140) and 43% of activities; Reversible hydration of CO2 route inflated by CA assay panels; 86% of compounds lack target data.
- **Unexplored areas**: None for pilot survey. All required files surveyed and extracted.

## Key Decisions Made
- Documented all exact formulas, query URLs, schemas, and metrics in `handoff.md`.
- Clarified difference between reference-weighted (60) vs unweighted (52) coverage score.

## Artifact Index
- DISPATCH.md — record of dispatch instructions
- BRIEFING.md — persistent working memory
- progress.md — liveness heartbeat
- handoff.md — final survey report
