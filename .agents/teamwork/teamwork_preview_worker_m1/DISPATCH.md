# DISPATCH for teamwork_preview_worker_m1

## Mission: Milestone 1 Implementation (Shared Data Core & Cached Clients)
You are the Worker implementing Milestone 1 according to `PROJECT.md`, the pilot specifications in `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_pilot\handoff.md`, and data sources in `teamwork_preview_spec_miner_datasources\handoff.md`.

### MANDATORY INTEGRITY WARNING
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may create/modify:
- `app/core/chembl_client.py`
- `app/core/reactome_client.py`
- `app/core/name_resolver.py`
- `app/core/scoring.py`
- `app/tests/test_core_clients.py`

### Required Tasks
1. Implement `app/core/chembl_client.py`:
   - `match_molecules_by_inchikey(inchikeys: list[str]) -> dict[str, dict]`
     Batch query up to 25 InChIKeys per call against ChEMBL REST API (`/chembl/api/data/molecule.json`), disk cache in SQLite `api_cache`.
   - `get_activities_for_molecule(chembl_id: str) -> list[dict]`
     Retrieves IC50/Ki activities in nM against `Homo sapiens`. Filters for `target_type == "SINGLE PROTEIN"` and single component UniProt accession. Extracts `pchembl`.
   - `get_compounds_for_target(target_chembl_id: str, pchembl_min: float = 6.0, exact_only: bool = True) -> list[dict]`
     Retrieves compounds active against a target with configurable pChEMBL threshold.
   - `search_target_by_gene_or_name(query: str) -> list[dict]`
     Searches human single-protein targets by gene symbol or protein name (e.g., PTGS2, COX-2).
   - All network calls must be cached on disk (using `data/natural_products.db` `api_cache` table) with graceful offline fallback. Pre-load pilot cache for Curcuma longa/Curcumin so tests and demo run in < 1s without network latency.

2. Implement `app/core/reactome_client.py`:
   - `get_pathway_enrichment(uniprot_ids: list[str], page_size: int = 15) -> dict`
     POST to `https://reactome.org/AnalysisService/identifiers/projection?pageSize={page_size}&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL`. Parses pathway name, stId, entities found/total, pValue, FDR, and token.
   - `search_pathways_by_keyword(keyword: str) -> list[dict]`
     Queries Reactome ContentService. Translates common Spanish terms ("inflamación" -> "inflammation", "apoptosis" -> "apoptosis", "cáncer" -> "cancer", "metabolismo" -> "metabolism"). Catches HTTP 404 cleanly and returns empty list.
   - `get_pathway_participants(st_id: str) -> list[str]`
     Retrieves participant UniProt accessions for a pathway stId.
   - On-disk caching in `api_cache` with pre-cached Curcuma longa Reactome analysis.

3. Implement `app/core/name_resolver.py`:
   - `resolve_plant_name(query: str) -> dict`
     Resolves scientific names, authorship (e.g. "curcuma longa L."), typos (fuzzy match via GBIF API `species/match`), and Spanish/English common names ("cúrcuma", "turmeric", "manzanilla", "ajo") to accepted canonical scientific name, family, and GBIF ID.
   - Returns structured dict: `canonical_name`, `family`, `accepted_usage_key`, `synonyms_es`, `synonyms_en`, `image_url`.
   - Handles empty/nonsense input with friendly Spanish messages.

4. Implement `app/core/scoring.py`:
   - `calculate_data_coverage_score(compounds: list[dict], activities: list[dict], reactome_data: dict) -> dict`
     Exact implementation of the 5-component formula:
     $A = \min(1.0, \log_{10}(1+N)/\log_{10}(101))$ where $N$ is distinct structures.
     $B_w = \sum_{match} w_i / \sum_{all} w_i$
     $C_w = \sum_{with\_target} w_i / \sum_{all} w_i$
     $D = \text{recognized} / \text{total}$
     $E = \text{targets with } \ge 2 \text{ activities} / \text{total}$
     $\text{Score} = 100 \times (0.10A + 0.20B_w + 0.30C_w + 0.15D + 0.25E)$
     Asserts Score == 60 for Curcuma longa ground truth.
     Detects single-molecule dominance (when top molecule provides >= 40% of targets, e.g. Curcumin 60.7%).
     Detects carbonic anhydrase assay panel inflation.

5. Implement `app/tests/test_core_clients.py`:
   - Tests ChEMBL client filtering, UniProt extraction, and caching.
   - Tests Reactome enrichment parsing and Spanish keyword resolution.
   - Tests Name resolver with authors, typos, common names.
   - Tests Scoring function against pilot ground truth and under-studied plant edge cases.

6. Run the full test suite:
   - `python -m pytest app/tests/test_core_clients.py -v`
   - `python -m pytest app/tests/ -v`
   Ensure 100% pass rate.

Write handoff report to `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m1\handoff.md` and notify orchestrator via `send_message`.
