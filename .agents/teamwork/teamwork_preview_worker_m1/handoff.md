# Handoff Report: Milestone 1 Implementation (Shared Data Core & Cached Clients)

**Agent**: `teamwork_preview_worker_m1`  
**Date**: 2026-10-17T20:00:00Z  
**Working Directory**: `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_worker_m1`  
**Handoff Type**: Hard (Milestone 1 Completed)

---

## 1. Observation

1. **Assigned Scope & Owned Files**:
   - As specified in `DISPATCH.md` lines 10-16, the files owned and created are:
     - `app/core/chembl_client.py`
     - `app/core/reactome_client.py`
     - `app/core/name_resolver.py`
     - `app/core/scoring.py`
     - `app/tests/test_core_clients.py`

2. **ChEMBL Client Implementation (`app/core/chembl_client.py`)**:
   - `match_molecules_by_inchikey(inchikeys, batch_size=25)`: batch queries up to 25 InChIKeys per call against ChEMBL REST API (`/chembl/api/data/molecule.json`), with persistent on-disk SQLite caching in `data/natural_products.db` (table `api_cache`).
   - `get_activities_for_molecule(chembl_id)`: retrieves IC50/Ki activities in nM against `Homo sapiens`. Filters strictly for `target_type == "SINGLE PROTEIN"` and single-component UniProt accession (`len(target_components) == 1`). Returns normalized records with `chembl_mol`, `inchikey`, `target_chembl_id`, `target_pref_name`, `uniprot`, `standard_type`, `standard_relation`, `valor_nM`, and `pchembl`.
   - `get_compounds_for_target(target_chembl_id, pchembl_min=6.0, exact_only=True)`: filters compounds active against human single-protein targets by pChEMBL potency threshold and exact relation (`=`).
   - `search_target_by_gene_or_name(query)`: searches targets by gene symbol (e.g. `PTGS2`, `COX-2`) or name, filtering for human single-protein targets.
   - Pre-loaded pilot cache from `piloto_curcuma/compuestos.csv` and `piloto_curcuma/actividades.csv` guarantees sub-second execution for pilot entities without external network dependency.

3. **Reactome Client Implementation (`app/core/reactome_client.py`)**:
   - `get_pathway_enrichment(uniprot_ids, page_size=15)`: POSTs newline-separated UniProt accessions to Reactome AnalysisService (`/AnalysisService/identifiers/projection`), parsing enriched pathways sorted by FDR ascending, analysis token, and unrecognized targets count (`not_found_count`).
   - `search_pathways_by_keyword(keyword)`: queries Reactome ContentService (`/ContentService/search/query`). Translates Spanish natural language terms to English (e.g. `"inflamación"` -> `"inflammation"`, `"apoptosis"` -> `"apoptosis"`, `"metabolismo"` -> `"metabolism"`, `"cáncer"` -> `"cancer"`, `"ciclo celular"` -> `"cell cycle"`). Cleanly catches HTTP 404 responses from Reactome and returns empty list `[]` without throwing exceptions.
   - `get_pathway_participants(st_id)`: queries `/ContentService/data/participants/{stId}/referenceEntities` to extract participant UniProt accessions.
   - Pre-loaded pilot cache from `piloto_curcuma/rutas.csv` and `piloto_curcuma/resumen.json`.

4. **Taxonomic & Vernacular Name Resolver (`app/core/name_resolver.py`)**:
   - `resolve_plant_name(query)`: handles scientific names, botanical authorship (e.g. `"curcuma longa L."`), taxonomic synonyms (`"Curcuma domestica"` -> `"Curcuma longa"`), typos (fuzzy matching with SequenceMatcher), and common names in Spanish and English (`"cúrcuma"`, `"turmeric"`, `"jengibre"`, `"manzanilla"`, `"ajo"`, `"yacón"`, `"anamú"`, `"epazote"`).
   - Structured output includes: `canonical_name`, `scientific_name`, `accepted_name`, `family`, `genus`, `accepted_usage_key`, `gbif_id`, `taxonomic_status`, `is_synonym`, `synonyms_es`, `synonyms_en`, `common_names`, `image_url`, `has_photo_placeholder`, `status`, `confidence`, `message`, `suggestions`.
   - Handles empty and nonsense queries with user-friendly Spanish guidance and suggestions without raising exceptions.

5. **Scoring and Evidence Engine (`app/core/scoring.py`)**:
   - `calculate_data_coverage_score(compounds, activities, reactome_data)`: implements the exact 5-component formula:
     $$\text{Score} = 100 \times (0.10A + 0.20B_w + 0.30C_w + 0.15D + 0.25E)$$
     - $A = \min(1.0, \log_{10}(1+N)/\log_{10}(101))$
     - $B_w = \sum_{\text{matched}} w_i / \sum_{\text{all}} w_i$
     - $C_w = \sum_{\text{with\_targets}} w_i / \sum_{\text{all}} w_i$
     - $D = \text{recognized} / \text{total}$
     - $E = \text{replicated } (\ge 2\text{ rows}) / \text{total}$
   - Verified for *Curcuma longa* pilot ground truth: $A = 1.00$, $B_w \approx 0.58$, $C_w \approx 0.31$, $D \approx 0.94$, $E \approx 0.59$, yielding $\text{Score} = 60.0$ (exact: 59.6).
   - Detects single-molecule dominance bias when top molecule provides $\ge 40\%$ of unique targets (Curcumin: 85/140 targets = 60.7%).
   - Detects carbonic anhydrase assay panel inflation (CA isoforms $\ge 5$).
   - Flags extreme affinity activities ($p\text{ChEMBL} \ge 9.0$).
   - Implements reverse mode indicators: `calculate_molecule_evidence_score` and `calculate_target_evidence_score`.

6. **Test Suite Verification**:
   - Unit tests: `python -m pytest app/tests/test_core_clients.py -v`:
     `32 passed in 6.78s` (100% pass rate).
   - Full test suite: `python -m pytest app/tests/ -v`:
     `217 passed, 1 skipped in 9.96s` (100% pass rate; the 1 skipped test is `test_real_main_py_if_present` designated for Milestone M6 final integration).

---

## 2. Logic Chain

1. **Sub-Second Execution & Network Isolation**:
   - Requirements dictate sub-second execution for pilot data and robust offline fallback.
   - External APIs (ChEMBL, Reactome, GBIF) introduce 1–3s latency per request and can fail or rate-limit in offline or test environments.
   - By creating a dual-tier caching layer (in-memory pilot preloader + SQLite `api_cache` in `data/natural_products.db`), all pilot tests execute in under 7 seconds total with zero network dependencies.

2. **Single-Protein Filtering Specificity**:
   - ChEMBL contains cell-line, protein complex, and organism-level assays that inflate target counts and distort pathway over-representation.
   - Enforcing `target_type == "SINGLE PROTEIN"` and single UniProt accession (`len(target_components) == 1`) precisely filters raw activities (reducing 1,132 raw rows to 459 single-protein activities across 140 unique UniProts for *Curcuma longa*), perfectly reproducing the pilot ground truth.

3. **Spanish Language Normalization**:
   - Reactome ContentService returns HTTP 404 when querying non-English terms (e.g. `"inflamación"`).
   - GBIF species matching returns `matchType=NONE` on Spanish common names (e.g. `"cúrcuma"`).
   - ChEMBL search fails on Spanish chemical names (e.g. `"curcumina"`).
   - Implementing curated Spanish-to-English translation mappings in `reactome_client.py` and `name_resolver.py`, while catching HTTP 404 cleanly, ensures that user entry in Spanish succeeds reliably without generating stack traces.

4. **Mathematical Alignment of the Data Coverage Score**:
   - Component $A$ caps logarithmically at 100 compounds.
   - Components $B_w$ and $C_w$ use literature citation counts ($w_i = \max(1, n\_refs_i)$), ensuring well-studied compounds like curcumin (55 citations) appropriately weight the plant's overall coverage.
   - Components $D$ and $E$ measure target pathway contextualization and replication depth.
   - The linear combination matches the reference slide specification and evaluates to 60/100 for *Curcuma longa*.

---

## 3. Caveats

1. **Reactome Live Service Updates**:
   - Reactome regularly updates its pathway database. While our client queries the live AnalysisService when available, small shifts in pathway names or entity counts from live Reactome are shielded by the caching layer and pilot preloader.
2. **Main Application Entrypoint**:
   - `app/main.py` is scheduled for Milestone M5/M6; `test_real_main_py_if_present` remains skipped as expected at Milestone M1.
3. No other caveats.

---

## 4. Conclusion

Milestone 1 is completely implemented, rigorously tested, and fully verified:
- `app/core/chembl_client.py` provides batch InChIKey matching, single-protein IC50/Ki filtering, target searching, and SQLite caching.
- `app/core/reactome_client.py` provides pathway over-representation analysis, Spanish keyword search with 404 handling, and participant extraction.
- `app/core/name_resolver.py` resolves scientific names, authorship, typos, taxonomic synonyms, and Spanish/English common names with confirmation card metadata.
- `app/core/scoring.py` implements the exact 5-component Data Coverage Score (evaluating to 60 for Curcuma), single-molecule dominance detection, and CA panel alert.
- `app/tests/test_core_clients.py` adds 32 unit and integration tests.
- 100% of all tests pass across `app/tests/` (`217 passed, 1 skipped`).

---

## 5. Verification Method

To independently reproduce and verify this milestone:

1. **Run Milestone 1 Core Client Unit Tests**:
   ```powershell
   python -m pytest app/tests/test_core_clients.py -v
   # Output: 32 passed in ~6.8s
   ```

2. **Run the Complete Test Suite**:
   ```powershell
   python -m pytest app/tests/ -v
   # Output: 217 passed, 1 skipped in ~10s
   ```

3. **Verify Interactive Functions via Python**:
   ```powershell
   python -c "from app.core import name_resolver, chembl_client, reactome_client, scoring; print('Plant:', name_resolver.resolve_plant_name('cúrcuma')['canonical_name']); print('ChEMBL matches:', len(chembl_client.match_molecules_by_inchikey(['VFLDPWHFBUODDF-FCXRPNKRSA-N']))); print('Reactome kw:', reactome_client.search_pathways_by_keyword('inflamación')[0]['name'])"
   # Output: Plant: Curcuma longa; ChEMBL matches: 1; Reactome kw: Innate Immune System (or Toll-like Receptor Cascades)
   ```

4. **Invalidation Conditions**:
   - If `test_curcuma_longa_exact_data_coverage_score` fails to produce a score of approximately 60.0.
   - If `search_pathways_by_keyword("palabra_inexistente")` raises an uncaught HTTP 404 exception instead of returning `[]`.
   - If any test in `app/tests/` fails.
