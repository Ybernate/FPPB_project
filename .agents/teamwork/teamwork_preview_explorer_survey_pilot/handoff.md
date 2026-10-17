# Handoff Report: Pilot Implementation Survey & Reference Targets

**Author**: `teamwork_preview_explorer_survey_pilot`  
**Date**: 2026-10-15T01:58:00Z  
**Target Path**: `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_pilot\handoff.md`  

---

## 1. Observation

Direct observations extracted from:
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\piloto.py`
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\analisis_extra.py`
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\resumen.py`
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\resumen.json`
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\compuestos.csv`
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\actividades.csv`
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\rutas.csv`
- `C:\Users\yediy\.gemini\antigravity\brain\de2bb0f4-4760-4c91-8338-d948a1211513\diapositiva_curcuma.md`
- `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\ORIGINAL_REQUEST.md`

### 1.1 SPARQL Query for LOTUS / Wikidata
From `piloto.py` lines 34-43 and 47-60:
```sparql
SELECT ?c ?label ?ik ?smiles (COUNT(DISTINCT ?art) AS ?nref) WHERE {
  ?t wdt:P225 "%s".
  ?c p:P703 ?st. ?st ps:P703 ?t.
  ?c wdt:P235 ?ik.
  OPTIONAL { ?c wdt:P233 ?smiles. }
  OPTIONAL { ?c rdfs:label ?label. FILTER(lang(?label)="en") }
  OPTIONAL { ?st prov:wasDerivedFrom ?ref. ?ref pr:P248 ?art. }
} GROUP BY ?c ?label ?ik ?smiles
```
- Endpoint: `https://query.wikidata.org/sparql?format=json&query=` (URL-encoded).
- User-Agent: `{"User-Agent": "fppb-student-pilot/1.0 (academic project)"}`.
- Target taxon: `?t wdt:P225 "%s"` where `%s` is `"Curcuma longa"`.
- Properties used:
  - `wdt:P225`: Taxon scientific name.
  - `p:P703` / `ps:P703`: "Found in taxon" statement.
  - `wdt:P235`: Standard InChIKey.
  - `wdt:P233`: Canonical SMILES.
  - `rdfs:label`: English label (`FILTER(lang(?label)="en")`).
  - `prov:wasDerivedFrom ?ref. ?ref pr:P248 ?art.`: Literature reference citing the occurrence (`pr:P248` = "stated in").
- Processing logic in `piloto.py` (lines 50-59):
  - Iterates over `results.bindings`.
  - Grouped into dict `comp` keyed by InChIKey:
    ```python
    row = comp.setdefault(ik, {
        "inchikey": ik,
        "nombre": b.get("label", {}).get("value", ""),
        "smiles": b.get("smiles", {}).get("value", ""),
        "n_refs": 0,
        "qid": b["c"]["value"].rsplit("/", 1)[-1],
    })
    row["n_refs"] = max(row["n_refs"], int(b["nref"]["value"]))
    ```
  - Yields 239 unique InChIKeys.

### 1.2 ChEMBL API Queries, Parameters, and Filtering
From `piloto.py` lines 63-111, 140-150:
- Base URL: `https://www.ebi.ac.uk/chembl/api/data`
- Headers: User-Agent set; rate limit delay `time.sleep(0.3)` between requests.
- **Stage 1 (Molecule matching)**:
  - Batch size: 25 InChIKeys per request.
  - Endpoint:
    `{CHEMBL}/molecule.json?molecule_structures__standard_inchi_key__in={q}&limit=100&only=molecule_chembl_id,pref_name,molecule_structures,molecule_properties`
  - Match field: `(m.get("molecule_structures") or {}).get("standard_inchi_key")` matched against query InChIKey.
  - In pilot: 110 of 239 matched by full InChIKey.
- **Stage 2 (Activities query)**:
  - Queried per matched `molecule_chembl_id`:
    `{CHEMBL}/activity.json?molecule_chembl_id={cid}&standard_type__in=IC50,Ki&standard_units=nM&target_organism=Homo%20sapiens&limit=1000&only=molecule_chembl_id,target_chembl_id,target_pref_name,standard_type,standard_relation,standard_value,pchembl_value`
  - Parameters:
    - `standard_type__in=IC50,Ki`: restricted strictly to IC50 and Ki.
    - `standard_units=nM`: normalized to nM.
    - `target_organism=Homo%20sapiens`: restricted to human organism.
    - Pagination: Follows `page_meta.next` until exhausted.
  - Total raw activities returned: 1,132 activities.
- **Stage 3 (Target details and single protein filtering)**:
  - Batch query of targets in batches of 25:
    `{CHEMBL}/target.json?target_chembl_id__in={q}&limit=100&only=target_chembl_id,pref_name,target_type,target_components`
  - UniProt extraction rule: `comps[0]["accession"] if len(comps) == 1 else None`
  - Single protein filter:
    ```python
    if t.get("tipo") != "SINGLE PROTEIN" or not t.get("uniprot"):
        continue
    ```
  - Total filtered activities on human single proteins: 459.
  - Unique UniProt IDs: 140.
  - Unique compounds with >= 1 filtered activity: 34.
- **Potency filtering (from `analisis_extra.py` lines 41-44)**:
  - `pot = [a for a in acts if a['relacion'] == '=' and a['pchembl'] and float(a['pchembl']) >= 6]`
  - Criteria: Exact relation (`relacion == '='`), `pchembl` present, `float(pchembl) >= 6` (potency <= 1 µM).
  - Yields: 54 activities, 27 targets, 14 compounds.

### 1.3 Reactome API Query and Pathway Enrichment
From `piloto.py` lines 114-127:
- Endpoint:
  `https://reactome.org/AnalysisService/identifiers/projection?pageSize=15&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL`
- Method: POST
- Content-Type: `text/plain`
- Body: `\n`.join(uniprots).encode() (newline-separated list of UniProt accessions, e.g. 140 IDs).
- Parameters:
  - `pageSize=15`: returns top 15 enriched pathways.
  - `page=1`
  - `sortBy=ENTITIES_FDR`: sorted by False Discovery Rate.
  - `order=ASC`: ascending (smallest FDR first).
  - `resource=TOTAL`
  - `projection`: projects non-human identifiers or isoforms to human reference entities.
- Response fields extracted:
  - `name`: pathway name (`ruta`)
  - `stId`: stable ID (`id`), e.g., `R-HSA-1475029`
  - `entities.found`: number of input proteins present in pathway (`entidades_encontradas`)
  - `entities.total`: total proteins in pathway (`entidades_total`)
  - `entities.pValue`: p-value (`p`)
  - `entities.fdr`: FDR-adjusted p-value (`fdr`)
  - `summary.token`: analysis token (e.g. `"MjAyNjEwMTMwMTIyMTFfMjUzNzA%3D"`)
  - `identifiersNotFound`: list/count of unrecognized UniProts (8 out of 140 not found -> 132 found).

### 1.4 Chemical Structure Normalization & Matching Logic
From `analisis_extra.py` lines 14-26 and `diapositiva_curcuma.md`:
- Standard InChIKey anatomy: `14-char skeleton (block 1) - 10-char stereochemistry (block 2) - 1-char charge (block 3)`.
  - Block 1 (`ik.split('-')[0]`): represents 2D molecular connectivity / graph skeleton.
  - Block 2: stereochemistry (chiral centers, cis/trans isomerism).
- In Curcuma longa dataset:
  - 239 total LOTUS records condense down to **169 distinct first blocks**.
  - 58 blocks have multiple variants (`sum(1 for v in by_fb.values() if len(v) > 1)`).
  - **42 records** in LOTUS that lack an exact 27-character ChEMBL match have a stereochemical variant in LOTUS that *does* match ChEMBL (`rescued` in `analisis_extra.py`).
  - Example: Desmethoxycurcumin:
    - `HJTVQHVGMGKONQ-LUZURFALSA-N`: has defined stereochemistry, matched `CHEMBL105360`, 4 targets, 20 refs.
    - `HJTVQHVGMGKONQ-UHFFFAOYSA-N`: undefined stereochemistry (`UHFFFAOY`), no ChEMBL match in pilot, 11 refs.
  - Example: Curcumin:
    - `VFLDPWHFBUODDF-FCXRPNKRSA-N`: matched `CHEMBL140`, 85 targets, 55 refs.
    - `VFLDPWHFBUODDF-UHFFFAOYSA-N`: labeled "turmeric", matched `CHEMBL3187799`, 0 targets, 17 refs.

### 1.5 Data Coverage Score: Exact Formulas and Execution Results
From `analisis_extra.py` lines 58-81 and `diapositiva_curcuma.md` lines 71-95:
- Formula:
  $$\text{Score} = 100 \times (0.10 \cdot A + 0.20 \cdot B + 0.30 \cdot C + 0.15 \cdot D + 0.25 \cdot E)$$
  Where:
  - **A (Reported compounds)**:
    $$A = \min\left(1, \frac{\log_{10}(1 + N)}{\log_{10}(101)}\right)$$
    In `analisis_extra.py`: $N = 239 \implies \log_{10}(240)/\log_{10}(101) = 2.3802 / 2.0043 = 1.187 \implies A = 1.00$.  
    (Note: `diapositiva_curcuma.md` specifies $N$ as distinct structures: $N = 169 \implies \log_{10}(170)/\log_{10}(101) = 2.2304 / 2.0043 = 1.113 \implies A = 1.00$ as well).
  - **B (ChEMBL match coverage)**:
    - Weighted by references ($B_w$):
      $$B_w = \frac{\sum_{i \in \text{matched}} \text{refs}_i}{\sum_{\text{all}} \text{refs}_i} = 0.5768 \approx 0.58$$
    - Unweighted ($B$):
      $$B = \frac{\text{matched}}{N} = \frac{110}{239} = 0.4603 \approx 0.46$$
  - **C (Human single-protein target coverage)**:
    - Weighted by references ($C_w$):
      $$C_w = \frac{\sum_{i \in \text{with\_targets}} \text{refs}_i}{\sum_{\text{all}} \text{refs}_i} = 0.3091 \approx 0.31$$
    - Unweighted ($C$):
      $$C = \frac{\text{compounds with } \ge 1 \text{ target}}{N} = \frac{34}{239} = 0.1423 \approx 0.14$$
  - **D (Reactome target recognition)**:
    $$D = \frac{\text{targets found}}{\text{total unique targets}} = 1 - \frac{8}{140} = \frac{132}{140} = 0.9429 \approx 0.94$$
  - **E (Evidence depth / replication)**:
    $$E = \frac{\text{targets with } \ge 2 \text{ activity rows}}{\text{total unique targets}} = \frac{82}{140} = 0.5857 \approx 0.59$$
- **Score calculation for *Curcuma longa***:
  - Weighted:
    $$\text{Score} = 100 \times (0.10 \times 1.00 + 0.20 \times 0.5768 + 0.30 \times 0.3091 + 0.15 \times 0.9429 + 0.25 \times 0.5857) = 59.59 \approx 60$$
  - Unweighted:
    $$\text{Score}_{\text{unweighted}} = 100 \times (0.10 \times 1.00 + 0.20 \times 0.4603 + 0.30 \times 0.1423 + 0.15 \times 0.9429 + 0.25 \times 0.5857) = 52.26 \approx 52$$

### 1.6 Output Artifact Schema in Pilot
1. `compuestos.csv` (241 lines, 239 records):
   `inchikey,nombre,smiles,n_refs,qid,chembl_id,chembl_nombre,n_blancos_proteina`
2. `actividades.csv` (461 lines, 459 records):
   `chembl_mol,inchikey,target,uniprot,tipo,relacion,valor_nM,pchembl`
3. `rutas.csv` (17 lines, 15 pathways):
   `ruta,id,entidades_encontradas,entidades_total,p,fdr`
4. `resumen.json`:
   ```json
   {
     "especie": "Curcuma longa",
     "n_lotus": 239,
     "n_chembl": 110,
     "n_actividades_proteina": 459,
     "n_blancos": 140,
     "reactome_token": "MjAyNjEwMTMwMTIyMTFfMjUzNzA%3D",
     "reactome_not_found": 8
   }
   ```

---

## 2. Logic Chain

1. **SPARQL query design and LOTUS extraction**:
   - The SPARQL query directly queries Wikidata's copy of LOTUS (`p:P703` found in taxon `wdt:P225 "Curcuma longa"`).
   - Literature references are attached to the statement via `prov:wasDerivedFrom ?ref. ?ref pr:P248 ?art`, providing the literature citation count `nref`.
   - The query returns 239 records. Each record represents a distinct Wikidata compound entity associated with an InChIKey.
   - When resolving species names, scientific names must match Wikidata `wdt:P225`.

2. **Chemical structure normalization & deduplication**:
   - The 239 records contain stereoisomers and tautomers: when grouped by the first 14 characters of the InChIKey (block 1, representing chemical graph connectivity without stereocenters), there are only 169 unique molecular skeletons.
   - 42 LOTUS records that lack an exact ChEMBL match have a stereoisomer in LOTUS that *does* match ChEMBL.
   - Matching solely on full InChIKey discards 42 potentially relevant records; matching by first block connects them, but risks conflating enantiomers or diastereomers whose biological activities differ.
   - The app must index entities by the first block of InChIKey while recording the specific stereoisomer.

3. **ChEMBL API querying & strict filtering rules**:
   - ChEMBL lookup occurs in two stages:
     a) Compound identifier lookup by InChIKey (`molecule.json?molecule_structures__standard_inchi_key__in=...`).
     b) Bioactivity lookup (`activity.json?molecule_chembl_id=...&standard_type__in=IC50,Ki&standard_units=nM&target_organism=Homo%20sapiens`).
   - A critical quality filter is applied: activities are kept only if the target is `SINGLE PROTEIN` and maps to a single UniProt accession (`target_components` length == 1). Complex targets, cell lines, and organisms are pruned out (reducing 1,132 raw activities to 459).
   - Potency filtering (for the high-confidence toggle) requires `standard_relation == '='` and `pchembl >= 6.0` (<= 1,000 nM).

4. **Reactome enrichment**:
   - Reactome's `/AnalysisService/identifiers/projection` endpoint receives the 140 unique UniProt IDs as a POST body.
   - Of 140 UniProt IDs, 132 are recognized by Reactome and 8 are not found (`identifiersNotFound: 8`).
   - Top pathway: `Reversible hydration of carbon dioxide` (12/17 entities found, FDR $1.14 \times 10^{-13}$).
   - This top pathway is heavily influenced by carbonic anhydrase assay panels (isoforms CA1 through CA14 tested against compound `CHEMBL66879` and others). The app must surface this bias warning.

5. **Single-molecule dominance bias**:
   - Curcumin (`CHEMBL140`, InChIKey `VFLDPWHFBUODDF-FCXRPNKRSA-N`) accounts for:
     - 85 of the 140 targets (60.7%).
     - 196 of the 459 activities (42.7%).
     - 55 LOTUS references (top compound).
   - Only 34 of the 239 compounds have any measured human protein activity. 86% of compounds have zero human protein targets reported.
   - This makes the Data Coverage Score and per-compound target breakdown essential to prevent misleading users into believing the entire plant has broad target coverage.

6. **Data Coverage Score mechanics**:
   - Component A caps at 100 compounds: $\log_{10}(1+N)/\log_{10}(101)$. For $N \ge 100$, $A = 1.00$.
   - Components B and C use citation weighting: compounds frequently cited in literature (like curcumin with 55 citations) contribute proportionally more to the score than single-citation trace metabolites.
   - This boosts $B$ from 0.46 (unweighted) to 0.58 (weighted) and $C$ from 0.14 (unweighted) to 0.31 (weighted), producing the final score of 60/100.
   - If a plant has no targets, $C=0, D=0, E=0$, capping the score at 30.

---

## 3. Caveats

1. **Live database drift**:
   - The pilot figures were generated on 2026-10-12. Subsequent updates to Wikidata/LOTUS, ChEMBL (e.g. ChEMBL 34+), or Reactome will introduce minor numerical drift (e.g., small shifts in activity counts or new references).
   - Test suites should check bounded ranges (e.g., $230 \le N \le 250$, $100 \le \text{matches} \le 125$, $440 \le \text{activities} \le 480$, $130 \le \text{targets} \le 150$) rather than strict equality.
2. **Definition of $N$ in Component A**:
   - `analisis_extra.py` uses $N = \text{len(comp)}$ (total LOTUS records = 239).
   - `diapositiva_curcuma.md` table describes $N$ as "estructuras distintas" (distinct first blocks = 169).
   - For *Curcuma longa*, both values exceed 100, so $A = 1.00$ in either case. However, for a plant with fewer compounds (e.g., 60 records representing 40 distinct structures), the choice between total records and distinct structures will affect $A$. The webapp specification should standardize on distinct structures ($N_{\text{distinct}}$) or total records.
3. **Component E depth proxy**:
   - Component E counts whether a UniProt target has $\ge 2$ rows in `actividades.csv`. Multiple activity rows can originate from the same scientific paper/assay. A stricter metric would count distinct ChEMBL documents, but the pilot implemented row count.
4. **COCONUT absence in pilot**:
   - The pilot only implemented LOTUS via Wikidata. It did not query or integrate COCONUT. COCONUT data integration will be a new addition for the app.
5. **Console encoding on Windows**:
   - Running Python scripts on Windows without setting `PYTHONIOENCODING=utf-8` caused a `UnicodeEncodeError` when printing the Greek character $\beta$ (`\u03b2`) in Reactome pathway names. The app must ensure UTF-8 encoding across all text handling.

---

## 4. Conclusion

1. **Reference Target Metrics for Acceptance Testing**:
   - **LOTUS records**: ~239
   - **Distinct structures (first block)**: ~169
   - **ChEMBL matches (full InChIKey)**: ~110
   - **ChEMBL rescued variants (first block)**: ~42
   - **Compounds with human single-protein activity**: ~34
   - **Total human IC50/Ki activities**: ~1,132
   - **Activities on human single proteins**: ~459
   - **Unique UniProt targets**: ~140
   - **Targets recognized by Reactome**: ~132 (8 not found)
   - **Curcumin target contribution**: 85 targets (60.7%)
   - **Data Coverage Score**: 60 / 100 (weighted), 52 / 100 (unweighted)

2. **Core Query Specifications**:
   - **Wikidata SPARQL**: Queries `wdt:P225`, extracts `?c`, `?label` (English), `?ik`, `?smiles`, and `(COUNT(DISTINCT ?art) AS ?nref)`.
   - **ChEMBL Match**: Batch of 25 InChIKeys via `molecule.json?molecule_structures__standard_inchi_key__in={keys}&only=molecule_chembl_id,pref_name,molecule_structures,molecule_properties`.
   - **ChEMBL Activities**: `activity.json?molecule_chembl_id={cid}&standard_type__in=IC50,Ki&standard_units=nM&target_organism=Homo%20sapiens&limit=1000`.
   - **ChEMBL Targets**: Batch of 25 via `target.json?target_chembl_id__in={tids}&limit=100`, filtering for `target_type == "SINGLE PROTEIN"` and single component UniProt accession.
   - **Reactome Enrichment**: POST to `/AnalysisService/identifiers/projection?pageSize=15&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL`.

3. **Data Coverage Score Implementation**:
   - Component A: $\min(1, \log_{10}(1+N)/\log_{10}(101))$
   - Component B: Reference-weighted ChEMBL match fraction
   - Component C: Reference-weighted human single-protein target fraction
   - Component D: Reactome recognition fraction ($\text{recognized} / \text{total}$)
   - Component E: Replication depth fraction ($\text{targets with } \ge 2 \text{ activities} / \text{total}$)
   - Linear combination: $100 \times (0.10 \cdot A + 0.20 \cdot B + 0.30 \cdot C + 0.15 \cdot D + 0.25 \cdot E) = 60$.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify reference numbers from pilot artifacts**:
   - Inspect `piloto_curcuma/resumen.json`:
     `{"especie": "Curcuma longa", "n_lotus": 239, "n_chembl": 110, "n_actividades_proteina": 459, "n_blancos": 140, "reactome_not_found": 8}`
   - Inspect `piloto_curcuma/compuestos.csv` row count: 239 data rows.
   - Inspect `piloto_curcuma/actividades.csv` row count: 459 data rows.
   - Inspect `piloto_curcuma/rutas.csv` row count: 15 pathway rows.

2. **Verify score calculation**:
   Execute the following Python snippet in `piloto_curcuma/` with Python 3:
   ```python
   import csv, math
   from collections import defaultdict

   comp = list(csv.DictReader(open('compuestos.csv', encoding='utf-8')))
   acts = list(csv.DictReader(open('actividades.csv', encoding='utf-8')))

   N = len(comp)
   w = [int(c['n_refs']) for c in comp]
   matched = [bool(c['chembl_id']) for c in comp]
   with_t = [int(c['n_blancos_proteina']) > 0 for c in comp]

   A = min(1, math.log10(1 + N) / math.log10(1 + 100))
   Bw = sum(x for x, m in zip(w, matched) if m) / sum(w)
   Cw = sum(x for x, m in zip(w, with_t) if m) / sum(w)

   targets_by = defaultdict(set)
   for a in acts:
       targets_by[a['uniprot']].add(a['chembl_mol'])
   all_t = len(targets_by)
   reactome_ok = 1 - (8 / all_t)
   depth = sum(1 for u in targets_by if sum(1 for a in acts if a['uniprot'] == u) >= 2) / all_t

   score = 100 * (0.10 * A + 0.20 * Bw + 0.30 * Cw + 0.15 * reactome_ok + 0.25 * depth)
   print(f"Calculated Score: {score:.2f} (Expected: ~59.59 -> 60)")
   ```

3. **Invalidation conditions**:
   - If a test asserts that `n_chembl` must equal exactly 110 without tolerance, database updates will cause test failure.
   - If the score formula uses unweighted B and C instead of reference-weighted Bw and Cw, the resulting score will be 52 instead of 60.
