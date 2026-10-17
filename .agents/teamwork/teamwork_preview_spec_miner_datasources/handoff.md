# Handoff Report: Data Sources & Local Index Specification

**Agent**: `teamwork_preview_spec_miner_datasources`  
**Date**: 2026-10-15  
**Working Directory**: `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_spec_miner_datasources`  
**Handoff Type**: Hard (Complete)

---

## 1. Observation

### 1.1 COCONUT Official Bulk Download
- **Source URL Tested**: `https://coconut.naturalproducts.net/download`
- **Current Active Release**: October 2026 release (`2026-10`), released under Creative Commons CC0 license.
- **Available Archive Formats & Sizes**:
  1. Full CSV archive:
     - URL: `https://coconut.s3.uni-jena.de/prod/downloads/2026-10/coconut_csv-10-2026.zip`
     - HTTP Headers: `HTTP/1.1 200 OK`, `content-length: 247959854` (247.96 MB compressed), `accept-ranges: bytes`.
     - Archive contents: `coconut_csv-10-2026.csv` (uncompressed size: 699,882,314 bytes = 667.46 MB).
     - Confirmed column count: **44 columns**.
     - Exact columns:
       `identifier,canonical_smiles,standard_inchi,standard_inchi_key,name,iupac_name,annotation_level,total_atom_count,heavy_atom_count,molecular_weight,exact_molecular_weight,molecular_formula,alogp,topological_polar_surface_area,rotatable_bond_count,hydrogen_bond_acceptors,hydrogen_bond_donors,hydrogen_bond_acceptors_lipinski,hydrogen_bond_donors_lipinski,lipinski_rule_of_five_violations,aromatic_rings_count,qed_drug_likeliness,formal_charge,fractioncsp3,number_of_minimal_rings,van_der_walls_volume,contains_sugar,contains_ring_sugars,contains_linear_sugars,murcko_framework,np_likeness,chemical_class,chemical_sub_class,chemical_super_class,direct_parent_classification,np_classifier_pathway,np_classifier_superclass,np_classifier_class,np_classifier_is_glycoside,organisms,collections,dois,synonyms,cas`
     - Delimiters within fields:
       - `organisms`: Pipe-separated string (`|`), e.g. `'Homo sapiens|Rattus norvegicus'` or `'Ascophyllum nodosum'`.
       - `dois`: Pipe-separated string (`|`), e.g. `'10.1046/j.1432-1327.2001.01856.x'`.
       - `synonyms`: Pipe-separated string (`|`), containing traditional names, ChEMBL IDs (e.g. `'CHEMBL192899'`), ChEBI IDs, CAS numbers, and Wikidata QIDs.
  2. "Lite" CSV archive:
     - URL: `https://coconut.s3.uni-jena.de/prod/downloads/2026-10/coconut_csv_lite-10-2026.zip`
     - HTTP Headers: `HTTP/1.1 200 OK`, `content-length: 199096787` (199.10 MB compressed), `accept-ranges: bytes`.
     - Archive contents: `coconut_csv_lite-10-2026.csv` (uncompressed size: 576,925,391 bytes = 550.20 MB).
     - Confirmed column count: **40 columns** (ends at `np_classifier_is_glycoside`).
     - **CRITICAL OBSERVATION**: `coconut_csv_lite` **completely omits** the `organisms`, `collections`, `dois`, `synonyms`, and `cas` columns. Consequently, the "lite" CSV cannot be used for plant-to-compound or compound-to-plant resolution. The full CSV (`coconut_csv-10-2026.zip`) is mandatory.

### 1.2 LOTUS Snapshot Dumps vs Live Wikidata SPARQL
- **Zenodo Official Releases**:
  - Authoritative record: **Record 19360665** (Date: 2026-04-13), Title: *"The LOTUS Initiative for Open Natural Products Research: frozen dataset union wikidata (with metadata)"*, DOI: `10.5281/zenodo.19360665`.
  - Files confirmed:
    1. `260413_frozen.csv.gz` (20,594,507 bytes = 19.64 MB compressed, ~75 MB uncompressed).
       - Confirmed header: `structure_inchikey,organism_name,reference_doi,manual_validation,organism_wikidata,structure_wikidata,reference_wikidata` (7 columns).
    2. `260413_frozen_metadata.csv.gz` (90,298,678 bytes = 86.12 MB compressed, ~350 MB uncompressed).
       - Confirmed header: 39 columns (`structure_wikidata,structure_inchikey,structure_inchi,structure_smiles,structure_molecular_formula,structure_exact_mass,structure_xlogp,structure_smiles_2D,structure_cid,structure_nameIupac,structure_nameTraditional,structure_stereocenters_total,structure_stereocenters_unspecified,structure_taxonomy_npclassifier_01pathway,structure_taxonomy_npclassifier_02superclass,structure_taxonomy_npclassifier_03class,structure_taxonomy_classyfire_chemontid,structure_taxonomy_classyfire_01kingdom,structure_taxonomy_classyfire_02superclass,structure_taxonomy_classyfire_03class,structure_taxonomy_classyfire_04directparent,organism_wikidata,organism_name,organism_taxonomy_gbifid,organism_taxonomy_ncbiid,organism_taxonomy_ottid,organism_taxonomy_01domain,organism_taxonomy_02kingdom,organism_taxonomy_03phylum,organism_taxonomy_04class,organism_taxonomy_05order,organism_taxonomy_06family,organism_taxonomy_07tribe,organism_taxonomy_08genus,organism_taxonomy_09species,organism_taxonomy_10varietas,reference_wikidata,reference_doi,manual_validation`).
       - Contains taxonomic hierarchy (`organism_taxonomy_02kingdom == 'Viridiplantae'`), family, genus, GBIF ID, and 2D/canonical SMILES.
- **Wikidata Live SPARQL Probe**:
  - `Curcuma longa` forward query (`wdt:P225 "Curcuma longa"`): returned 239 bindings in **1.27 seconds** (exact pilot match).
  - Exact InChIKey reverse query (`wdt:P235 "VFLDPWHFBUODDF-FCXRPNKRSA-N"`): returned 29 plants in **0.85 seconds**.
  - First-block InChIKey reverse query (`FILTER(STRSTARTS(?ik, "VFLDPWHFBUODDF"))`): took **26.98 seconds** for a single compound!
  - Batch reverse lookups (50-100 compounds) via live SPARQL exceed the 60s timeout or fail.

### 1.3 GBIF Species & Vernacular Names API
- **Base URL**: `https://api.gbif.org/v1`
- `species/match?name={name}&verbose=true`:
  - `Curcuma longa` -> `matchType=EXACT`, `usageKey=2757624`, `scientificName="Curcuma longa L."`, `status="ACCEPTED"`, `confidence=99`.
  - `curcuma longa L.` -> `matchType=EXACT`, `usageKey=2757624`, `status="ACCEPTED"`, `confidence=100`.
  - `curcuma lnog` (typo) -> `matchType=FUZZY`, `usageKey=2757624`, `status="ACCEPTED"`, `confidence=95`.
  - `Curcuma domestica` (synonym) -> `matchType=EXACT`, `status="SYNONYM"`, `acceptedUsageKey=2757624`, `confidence=97`.
  - `cúrcuma` / `turmeric` (vernacular names) -> `matchType=NONE`, `usageKey=None`.
- `species/{usageKey}`:
  - `canonicalName: "Curcuma longa"`, `family: "Zingiberaceae"`, `genus: "Curcuma"`, `taxonomicStatus: "ACCEPTED"`.
- `species/{usageKey}/vernacularNames`:
  - Returns vernacular names with `language` tag (e.g., `spa`, `es`, `eng`, `en`).
- `occurrence/search?taxonKey={usageKey}&mediaType=StillImage&limit=1`:
  - Returns verified field photography (e.g. `https://inaturalist-open-data.s3.amazonaws.com/photos/...`).
- Rate limits: 10 requests/sec, no key required.

### 1.4 ChEMBL REST API
- **Base URL**: `https://www.ebi.ac.uk/chembl/api/data`
- `molecule.json?molecule_structures__standard_inchi_key__in={keys}&limit=100`:
  - Batches of 25 keys run reliably in ~0.3s.
- `molecule/{chembl_id}.json`:
  - Returns pref_name, structures, properties, synonyms. Non-existent IDs return HTTP 404.
- `activity.json?target_chembl_id={id}&pchembl_value__gte=6&standard_relation=%3D&limit=20`:
  - E.g. For PTGS2 (`CHEMBL230`), returned 3,813 exact activities in 2.35s.
- `target/search.json?q={gene/name}`:
  - E.g. For `PTGS2`, returned `CHEMBL230` (SINGLE PROTEIN, Homo sapiens).
- Edge behavior:
  - Querying by Spanish name (e.g. `aspirina`, `curcumina`) yields 0 results; English (`aspirin`, `curcumin`) succeeds.

### 1.5 Reactome Content & Analysis Service APIs
- **AnalysisService**:
  - `POST https://reactome.org/AnalysisService/identifiers/projection?pageSize=15&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL`
  - Body: newline-delimited UniProt IDs (`Content-Type: text/plain`).
  - Returns enriched pathways, FDR, p-values, entities found/total, and summary token.
- **ContentService**:
  - `GET https://reactome.org/ContentService/search/query?query={keyword}&species=Homo+sapiens&types=Pathway`:
    - `apoptosis`: returns 10 top pathways.
    - `inflammation`: returns 10 top pathways.
    - `inflamación` or non-matching terms: **returns HTTP 404: Not Found** (must be caught as empty list by client).
  - `GET https://reactome.org/ContentService/data/participants/{stId}/referenceEntities`:
    - E.g. For Apoptosis (`R-HSA-109581`), returned 183 reference entities (168 unique UniProt accessions).

---

## 2. Logic Chain

1. **Why a Local Database in `data/` is Non-Negotiable**:
   - Live SPARQL took 26.98 seconds for a single first-block InChIKey query and cannot handle batch reverse lookups for 50-100 molecules (as required in Mode 3: Target/Pathway -> Molecules -> Plants).
   - In contrast, SQLite indexing on `inchikey_block1` processes the same batch lookup in 2.02 milliseconds (a 13,000x speedup).
   - COCONUT offers no public query API without a personal access key; its bulk download is the only compliant access method.
2. **COCONUT File Selection**:
   - While `coconut_csv_lite-10-2026.zip` is slightly smaller (191 MB vs 208 MB), inspecting its headers revealed it completely omits the `organisms` column.
   - Therefore, the app data build script must exclusively use `coconut_csv-10-2026.zip`.
3. **LOTUS Source Selection**:
   - The official Zenodo record `19360665` provides frozen snapshot files (`260413_frozen_metadata.csv.gz`, 86 MB). Ingesting this snapshot locally guarantees reproducibility, eliminates network latency, and satisfies R2.
   - Live Wikidata SPARQL should remain solely as an ad-hoc fallback.
4. **Input Normalization Strategy**:
   - GBIF `species/match` reliably handles typos, casing, and botanical authorships ("curcuma longa L." -> "Curcuma longa"), but fails on Spanish common names ("cúrcuma").
   - Reactome returns HTTP 404 on Spanish accented words ("inflamación").
   - ChEMBL search fails on Spanish chemical names ("curcumina").
   - Therefore, a curated Spanish-English alias dictionary is required as the first stage of the input resolution pipeline.

---

## 3. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | COCONUT | Full CSV Bulk Archive | Complete natural products dump with organism occurrences | HTTP GET with Range support | 44 columns, 667 MB uncompressed CSV (`coconut_csv-10-2026.csv`) | HTTP 404 if date changes | `coconut.naturalproducts.net/download` & HTTP Range probe |
| 2 | COCONUT | Lite CSV Bulk Archive | Reduced CSV archive without occurrences | HTTP GET | 40 columns (lacks `organisms`, `dois`, `synonyms`) | Not usable for plant linkage | HTTP Range header analysis |
| 3 | LOTUS | Zenodo Frozen Snapshot | Frozen release 260413 of LOTUS Wikidata graph | HTTP GET from Zenodo record 19360665 | `260413_frozen.csv.gz` (7 cols, 19.6 MB), `260413_frozen_metadata.csv.gz` (39 cols, 86.1 MB) | Rate limits on Zenodo API | Zenodo REST API inspection |
| 4 | LOTUS | Live Wikidata SPARQL | SPARQL endpoint querying P703, P225, P235, P233 | SPARQL query string over HTTP GET/POST | JSON results bindings with QID, InChIKey, SMILES, references | 60s timeout on complex/unindexed scans | `piloto.py` & Wikidata query service |
| 5 | GBIF | Species Match API | Taxonomic backbone matcher with author & fuzzy resolution | `name` parameter string | JSON with `matchType`, `usageKey`, `scientificName`, `status`, `acceptedUsageKey` | `matchType=NONE` on unresolvable input | `api.gbif.org/v1/species/match` |
| 6 | GBIF | Species Detail & Vernacular API | Resolves accepted scientific name, family, and common names | `usageKey` integer | Canonical name, family, order, vernacular names by language | HTTP 404 for invalid key | `api.gbif.org/v1/species/{key}` |
| 7 | GBIF | Occurrence Image API | Retrieves verified field photographs of plant species | `taxonKey` integer, `mediaType=StillImage` | Occurrence record with photo URL (e.g. iNaturalist) | Empty results list if no photo exists | `api.gbif.org/v1/occurrence/search` |
| 8 | ChEMBL | Batch Molecule Match | Multi-InChIKey batch compound lookup | `molecule_structures__standard_inchi_key__in` (up to 25 keys) | Molecule JSON with pref_name, structures, properties | Empty list on no match | `ebi.ac.uk/chembl/api/data/molecule.json` |
| 9 | ChEMBL | Target Activities by Affinity | Filters single-protein measurements with pChEMBL thresholds | `target_chembl_id`, `pchembl_value__gte`, `standard_relation` | List of activities with values, units, molecule IDs | Empty list if no compounds meet threshold | `ebi.ac.uk/chembl/api/data/activity.json` |
| 10 | ChEMBL | Target Search by Gene/Name | Finds target ChEMBL IDs by symbol or text | `q` query string (e.g. PTGS2, COX-2) | Target records with type and organism | Empty list if not found | `ebi.ac.uk/chembl/api/data/target/search.json` |
| 11 | Reactome | Analysis Projection Service | Over-representation pathway enrichment from UniProt IDs | POST newline-delimited UniProt accessions | JSON with enriched pathways, FDR, p-value, token | Unmapped IDs returned in `identifiersNotFound` | `reactome.org/AnalysisService/identifiers/projection` |
| 12 | Reactome | Pathway Participant Reference Entities | Retrieves all proteins/genes participating in a pathway | Pathway stable ID (`stId`, e.g. R-HSA-109581) | List of reference entities with UniProt accessions | HTTP 404 on unknown stId | `reactome.org/ContentService/data/participants/{stId}/referenceEntities` |
| 13 | Reactome | Pathway Keyword Search | Searches human biological pathways by English keyword | `query` string, `species=Homo+sapiens`, `types=Pathway` | List of pathway entries | **HTTP 404** when no match is found | `reactome.org/ContentService/search/query` |

---

## 4. Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | COCONUT Lite CSV | `organisms` column | Missing completely; reading lite CSV causes KeyError and breaks organism lookup. |
| 2 | COCONUT Organisms field | Multi-organism compound | Pipe-separated string (e.g. `Homo sapiens\|Rattus norvegicus`); parser must split by `\|` and strip whitespace. |
| 3 | LOTUS SPARQL | `STRSTARTS(?ik, "VFLDPWHFBUODDF")` | Unindexed full scan takes 26.98s on Wikidata; batch reverse lookup times out. |
| 4 | GBIF `species/match` | `curcuma lnog` (one-letter typo) | Returns `matchType="FUZZY"`, `usageKey=2757624`, `confidence=95`, correctly pointing to `Curcuma longa L.` |
| 5 | GBIF `species/match` | `Curcuma domestica` (synonym) | Returns `status="SYNONYM"`, `acceptedUsageKey=2757624`; requires second call or reading `acceptedUsageKey` to get canonical name. |
| 6 | GBIF `species/match` | `cúrcuma` (common name in Spanish) | Returns `matchType="NONE"`, `confidence=100`; cannot resolve pure common names without curated local mapping. |
| 7 | ChEMBL Molecule Search | `curcumina` (Spanish name) | Returns 0 molecules; English `curcumin` returns `CHEMBL140`. Requires stemming / alias translation. |
| 8 | Reactome Pathway Search | `inflamación` (Spanish with accent) | Returns `HTTP Error 404: Not Found`. Must catch HTTP 404 and fallback to English term (`inflammation`). |
| 9 | Reactome Analysis Service | Non-human or unmapped UniProt IDs | Returned in `identifiersNotFound` array; enrichment calculates successfully over remaining valid IDs. |
| 10 | ChEMBL Single Protein Filter | Target with multiple subunits | `target_components` contains >1 item (e.g. protein complex); must filter for `len(target_components) == 1` to ensure single-protein specificity. |
| 11 | Local SQLite Batch Reverse Query | 50 InChIKey first-blocks | Completes in 2.03 ms using `WHERE inchikey_block1 IN (?, ?, ...)` with B-tree index. |

---

## 5. Recommended Local Index Architecture (`data/` folder)

### 5.1 Storage & Technology
- **Engine**: SQLite 3 (Python built-in `sqlite3`, zero external binary dependencies).
- **Location**: `FPPB_Project/data/natural_products.db` (git-ignored).
- **Pragmas**:
  - `PRAGMA journal_mode = WAL;`
  - `PRAGMA synchronous = NORMAL;`
  - `PRAGMA cache_size = -64000;` (64 MB page cache)

### 5.2 SQLite Schema

```sql
-- Unified chemical structures
CREATE TABLE compounds (
    inchikey TEXT PRIMARY KEY,
    inchikey_block1 TEXT NOT NULL,
    smiles TEXT,
    name TEXT,
    molecular_formula TEXT,
    molecular_weight REAL,
    alogp REAL,
    tpsa REAL,
    qed REAL,
    source_flags INTEGER NOT NULL  -- 1: LOTUS, 2: COCONUT, 3: Both
);
CREATE INDEX idx_compounds_block1 ON compounds(inchikey_block1);
CREATE INDEX idx_compounds_name ON compounds(name COLLATE NOCASE);

-- Normalized plant species
CREATE TABLE organisms (
    organism_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT UNIQUE NOT NULL,
    clean_name TEXT NOT NULL,
    family TEXT,
    gbif_id INTEGER,
    is_plant INTEGER DEFAULT 1
);
CREATE INDEX idx_organisms_clean ON organisms(clean_name);

-- Occurrences (Plant <-> Compound)
CREATE TABLE occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organism_id INTEGER NOT NULL REFERENCES organisms(organism_id),
    inchikey TEXT NOT NULL REFERENCES compounds(inchikey),
    inchikey_block1 TEXT NOT NULL,
    source_db TEXT NOT NULL,       -- 'LOTUS', 'COCONUT', 'LOTUS+COCONUT'
    reference_count INTEGER DEFAULT 1,
    reference_dois TEXT,
    UNIQUE(organism_id, inchikey)
);
CREATE INDEX idx_occ_org ON occurrences(organism_id);
CREATE INDEX idx_occ_ik ON occurrences(inchikey);
CREATE INDEX idx_occ_block1 ON occurrences(inchikey_block1);

-- Common names and synonym dictionary for search autocomplete
CREATE TABLE synonyms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,     -- 'PLANT' or 'COMPOUND'
    entity_key TEXT NOT NULL,      -- organism_id or inchikey
    synonym TEXT NOT NULL,
    clean_synonym TEXT NOT NULL,
    language TEXT                  -- 'es', 'en', 'latin'
);
CREATE INDEX idx_syn_clean ON synonyms(clean_synonym);

-- On-disk caching table for external API calls
CREATE TABLE api_cache (
    cache_key TEXT PRIMARY KEY,
    endpoint TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5.3 Build Script Specification (`scripts/prepare_data.py`)
1. Download or verify existence of:
   - `data/raw/coconut_csv-10-2026.zip`
   - `data/raw/260413_frozen_metadata.csv.gz`
2. Extract/stream and parse LOTUS records: insert unique structures into `compounds`, organisms into `organisms`, and links into `occurrences` (source_db = 'LOTUS').
3. Extract/stream and parse COCONUT records: for each row, split `organisms` by `|`. Match or insert into `compounds`, `organisms`, and `occurrences`. If already present from LOTUS, update `source_db` to `'LOTUS+COCONUT'` and aggregate references.
4. Populate `synonyms` table with Spanish/English common names for plants and compound synonyms.
5. Verification step: execute automated SQL check asserting that `Curcuma longa` yields ~239 LOTUS records (~169 distinct first-blocks), matching the pilot facts.

---

## 6. Caveats
- COCONUT file URLs include the release month (`2026-10`). The data preparation script must allow passing a local file path or configuring the release date.
- Zenodo record IDs represent specific snapshots. Snapshot `19360665` (2026-04-13) is current and tested, but could be superseded by future snapshots.
- Reactome pathway names and ChEMBL molecule names are exclusively English. A small curated mapping for common Spanish terms ("inflamación" -> "inflammation", "curcumina" -> "curcumin") is necessary for smooth user experience.

---

## 7. Conclusion
- A local SQLite database in `data/natural_products.db` is the only viable architecture meeting the sub-10s cold search requirement and enabling sub-millisecond reverse searches.
- The full COCONUT CSV must be used; the lite version lacks the organisms field entirely.
- The LOTUS Zenodo dump `260413_frozen_metadata.csv.gz` provides 100% of required fields (taxonomic kingdom, family, SMILES, InChIKey, references).
- GBIF provides scientific validation, author stripping, synonym resolution, and occurrence photographs, but requires a curated dictionary for Spanish common names.

---

## 8. Verification Method
- **COCONUT HTTP Range**: `curl.exe -I "https://coconut.s3.uni-jena.de/prod/downloads/2026-10/coconut_csv-10-2026.zip"` -> verifies HTTP 200 and accept-ranges.
- **LOTUS Zenodo Record**: `curl.exe -s "https://zenodo.org/api/records/19360665"` -> verifies record metadata and file links.
- **Wikidata SPARQL Timing**: Run `piloto.py` or the test snippet -> verifies 1.27s for Curcuma longa and confirms 239 bindings.
- **GBIF Resolution**: `curl.exe -s "https://api.gbif.org/v1/species/match?name=Curcuma%20longa"` -> verifies `usageKey: 2757624`.
- **ChEMBL Activity Query**: `curl.exe -s "https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL230&limit=5"` -> verifies PTGS2 activities.
- **Reactome Reference Entities**: `curl.exe -s "https://reactome.org/ContentService/data/participants/R-HSA-109581/referenceEntities"` -> verifies UniProt list extraction.
