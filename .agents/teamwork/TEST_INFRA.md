# Test Infrastructure & Specification: "Conoce tu planta" (v1)

**Document Version:** 1.0.0  
**Author:** `teamwork_preview_test_writer_e2e`  
**Target Path:** `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\TEST_INFRA.md`  
**Test Suite Directory:** `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\app\tests\`  

---

## 1. Overview & Testing Philosophy

The test infrastructure for **"Conoce tu planta"** follows an **independent, opaque-box, requirement-driven** methodology. Tests are written against authoritative requirements specified in `ORIGINAL_REQUEST.md` and `PROJECT.md`, anchored in the verified empirical ground truth of `piloto_curcuma/` and `diapositiva_curcuma.md`.

### Core Principles
1. **Opaque-Box Independence**: Tests evaluate behavioral contracts, expected inputs/outputs, error states, and UI presentations rather than private internal implementation details.
2. **Deterministic Ground Truth**: All numerical assertions for the reference species (*Curcuma longa*) and compounds (e.g., Curcumin `CHEMBL140`) are derived directly from the audited pilot outputs. Tolerances are strictly bounded to prevent regressions while allowing minor live database drift.
3. **Dual-Track Verification**:
   - **Data & Core Logic**: Fast, deterministic test cases utilizing `pytest`, local SQLite fixtures, and offline mocks/cache.
   - **Headless UI Testing**: Automated browserless end-to-end user journeys across all 3 Streamlit tabs (*Planta*, *Molécula*, *Proteína/Proceso*) utilizing `streamlit.testing.v1.AppTest`.
4. **Mandatory Scientific Honesty Gates**: Automated assertions verify that no result page ever omits the pre-clinical laboratory disclaimer, that single-molecule dominance warnings trigger accurately ($\ge 40\%$ of targets), and that no clinical or curative claims are presented.
5. **Graceful Degradation**: Network outages, syntax errors, and empty queries must yield friendly Spanish error messages without unhandled stack traces.

---

## 2. Test Architecture & Runner Commands

### 2.1 File Organization in `app/tests/`

```text
app/tests/
├── __init__.py                  # Package marker
├── conftest.py                  # Pytest fixtures: mock DB, pilot ground truth, sample entities, AppTest helpers
├── test_inputs.py               # Tier 1 & Tier 2: Taxonomic, chemical, and biological input validation & parsing
├── test_pilot_metrics.py        # Tier 4: Exact pilot replication for Curcuma longa & Data Coverage Score (60/100)
├── test_roundtrip.py            # Tier 3: Bidirectional entity discovery (Plant <-> Molecule <-> Target)
├── test_exports.py              # Tier 1 & Tier 2: CSV/JSON export schema validation & download integrity
├── test_e2e_requirements.py     # Tiers 1-4: Comprehensive requirement catalog assertions across R1-R6
└── test_ui_apptest.py           # Streamlit AppTest: Headless UI execution of all 3 tabs, widgets, and banners
```

### 2.2 Runner Commands

- **Run complete test suite:**
  ```powershell
  python -m pytest app/tests/ -v
  ```

- **Run core logic and requirement tests (offline, fast):**
  ```powershell
  python -m pytest app/tests/test_inputs.py app/tests/test_pilot_metrics.py app/tests/test_roundtrip.py app/tests/test_exports.py app/tests/test_e2e_requirements.py -v
  ```

- **Run headless UI tests (Streamlit AppTest):**
  ```powershell
  python -m pytest app/tests/test_ui_apptest.py -v
  ```

- **Run specific tier with markers:**
  ```powershell
  python -m pytest -m "tier1" app/tests/ -v
  python -m pytest -m "tier2" app/tests/ -v
  python -m pytest -m "tier3" app/tests/ -v
  python -m pytest -m "tier4" app/tests/ -v
  ```

---

## 3. The 4-Tier Test Catalog

The test catalog guarantees exhaustive coverage across all requirements (R1–R6), edge cases, cross-module interactions, and empirical real-world scenarios.

### Tier 1: Feature Coverage (>=5 Test Cases per Feature across R1–R6)

| ID | Feature Under Test | Requirement | Test Cases (>=5) |
|---|-------------------|-------------|------------------|
| **T1.1** | Taxonomic Name Resolution | R1 | 1. Exact scientific name (`"Curcuma longa"`).<br>2. Scientific name with botanical authorship (`"Curcuma longa L."`).<br>3. Case variation (`"curcuma LONGA"`).<br>4. Spanish common name (`"cúrcuma"`).<br>5. English common name (`"turmeric"`).<br>6. Taxonomic synonym (`"Curcuma domestica"`). |
| **T1.2** | Plant Confirmation Card & Photo Placeholder | R1 | 1. Card extracts accepted scientific name.<br>2. Card extracts taxonomic family (Zingiberaceae).<br>3. Card extracts common names list.<br>4. Card displays species image URL when available.<br>5. Photo button displays "identificar por foto (próximamente)" placeholder banner without executing computer vision. |
| **T1.3** | Molecule Format Auto-Detection | R1 | 1. Valid Canonical SMILES (e.g. `"COc1cc(C=CC(=O)CC(=O)C=Cc2ccc(O)c(OC)c2)ccc1O"`).<br>2. Valid Standard InChIKey (e.g. `"VFLDPWHFBUODDF-FCXRPNKRSA-N"`).<br>3. Valid ChEMBL ID (e.g. `"CHEMBL140"`).<br>4. English molecule name (`"curcumin"`).<br>5. Spanish molecule synonym (`"curcumina"`). |
| **T1.4** | 2D Chemical Structure Depiction & First-Block Grouping | R1, R5 | 1. Valid RDKit SVG depiction generated with transparent background.<br>2. Handling of stereochemical stereoisomer grouping via InChIKey Block 1 (`"VFLDPWHFBUODDF"`).<br>3. Rescued stereoisomer matching (e.g. `HJTVQHVGMGKONQ`).<br>4. Graceful depiction fallback on complex/macrocyclic structures.<br>5. Display of stereochemical grouping notice. |
| **T1.5** | Protein & Pathway Search Resolution | R1 | 1. Human gene symbol query (`"PTGS2"`).<br>2. Common protein alias (`"COX-2"`).<br>3. UniProt accession query (`"P35354"`).<br>4. Spanish Reactome keyword (`"inflamación"` -> inflammation).<br>5. English Reactome keyword (`"apoptosis"`). |
| **T1.6** | Dual-Source Provenance & Indexing | R2 | 1. LOTUS-only compound record retains source tag `LOTUS`.<br>2. COCONUT-only compound record retains source tag `COCONUT`.<br>3. Overlapping compound contains dual source tags (`LOTUS`, `COCONUT`).<br>4. Reference counts (`n_refs` / DOIs) are preserved.<br>5. Fast SQLite B-tree query execution on `inchikey_block1`. |
| **T1.7** | ChEMBL REST Client Filtering & Caching | R2 | 1. IC50 activity filter verification.<br>2. Ki activity filter verification.<br>3. Strict single-protein target filter (`len(components) == 1`).<br>4. Multi-subunit complex target exclusion.<br>5. Disk cache hit prevents redundant network calls. |
| **T1.8** | Reactome Analysis Service Client & Caching | R2 | 1. Over-representation analysis POST body formatted correctly.<br>2. Pathway ranking strictly by ascending FDR (`sortBy=ENTITIES_FDR`).<br>3. Unrecognized UniProt IDs reported in `identifiersNotFound`.<br>4. Translation of Spanish query terms to English.<br>5. Disk cache hit returns cached pathway set. |
| **T1.9** | Data Coverage Score Calculation | R3 | 1. Component A logarithmic scaling ($\min(1, \log_{10}(1+N)/\log_{10}(101))$).<br>2. Component $B_w$ citation weighting of ChEMBL matches.<br>3. Component $C_w$ citation weighting of measured single-protein targets.<br>4. Component D Reactome mapping fraction.<br>5. Component E replication depth ($\ge 2$ measurement rows). |
| **T1.10** | Reverse Mode Filtering (Target/Process -> Plants) | R3 | 1. Default toggle "Solo moléculas con planta fuente" filters out synthetic molecules.<br>2. Disabling plant toggle reveals full ChEMBL bioactives.<br>3. Potency slider filter ($p\text{ChEMBL} \ge 6.0$).<br>4. Exact measurement constraint (`standard_relation == '='`).<br>5. Reverse evidence indicator computed and presented. |
| **T1.11** | Disclaimers & Bias Transparency | R4 | 1. Pre-clinical laboratory disclaimer present on Plant results.<br>2. Pre-clinical laboratory disclaimer present on Molecule results.<br>3. Pre-clinical laboratory disclaimer present on Target/Process results.<br>4. Single-molecule dominance warning fires when top compound $\ge 40\%$ targets.<br>5. Assay panel inflation alert displayed for multi-isoform targets (e.g. CA1-CA14). |
| **T1.12** | Export Engine Schema & Integrity | R5 | 1. CSV export for Plant mode contains `inchikey`, `name`, `n_refs`, `chembl_id`, `n_blancos`.<br>2. JSON export for Plant mode mirrors data model with metadata.<br>3. CSV export for Molecule mode contains plant occurrences and targets.<br>4. CSV export for Target mode contains active molecules and plant sources.<br>5. Standard identifiers (InChIKey, UniProt, ChEMBL, Reactome) present in all exports. |

---

### Tier 2: Boundary & Corner Cases

| ID | Category | Scenario / Input | Expected Behavior |
|---|----------|------------------|-------------------|
| **T2.1** | Empty & Whitespace | Empty string `""` or whitespace `"   "` in Plant, Molecule, or Target inputs | Input rejected cleanly; prompt user for input; zero crashes; zero stack traces. |
| **T2.2** | Nonsense Input | Gibberish string `"xyz987_qwerty_nonexistent"` | Friendly Spanish warning displayed: *"No se encontraron resultados para '...'"*. |
| **T2.3** | Typo Tolerance | One-letter spelling mistake: `"curcuma lnog"` | Fuzzy resolution catches species and suggests or resolves to `"Curcuma longa"`. |
| **T2.4** | Malformed Chemical | Invalid SMILES string `"CC(=O)O(Cl)(Br)(I)@@@@"` | Format detector returns error or invalid status; UI informs user to check chemical structure without crashing. |
| **T2.5** | Non-existent ChEMBL ID | `"CHEMBL999999999999"` | Returns clean 404 handler; Spanish notification: *"Identificador ChEMBL no encontrado"*. |
| **T2.6** | Network Disconnect Simulation | Simulated HTTP 500 / Timeout / ConnectionError on ChEMBL, Reactome, or GBIF | Intercepted by client try/except; UI displays warning banner: *"Servicio externo no disponible temporalmente"*; no unhandled exception. |
| **T2.7** | Extreme Potency Values | Activity with $p\text{ChEMBL} \ge 11.0$ ($< 0.01\text{ nM}$) or $p\text{ChEMBL} \le 3.0$ | Tagged with extreme affinity alert linking to source assay publication. |
| **T2.8** | Species with Zero Compounds | Known plant species with 0 natural product records in LOTUS/COCONUT | Friendly message: *"No se registran compuestos en LOTUS o COCONUT para esta especie"*, suggesting sister species of the same genus. |
| **T2.9** | Plant with No ChEMBL Targets | Species with reported compounds, but 0 ChEMBL bioactivities | Score components $C=0, D=0, E=0$; score caps at $\le 30$; clean table rendered with 0 targets. |
| **T2.10** | Reactome Accented Word Query | Search `"inflamación"` on ContentService (which returns 404 natively) | Client catches 404, maps to `"inflammation"`, and retrieves relevant pathways without error. |

---

### Tier 3: Cross-Feature Combinations & Roundtrips

| ID | Name | Sequence / Interaction | Assertion |
|---|------|------------------------|-----------|
| **T3.1** | Curcumin <-> Curcuma longa Roundtrip | 1. Query Plant mode for `"Curcuma longa"`.<br>2. Extract top compound (`CHEMBL140` / Curcumin).<br>3. Query Molecule mode with `"CHEMBL140"` or `"VFLDPWHFBUODDF-FCXRPNKRSA-N"`. | `Curcuma longa` MUST appear in the list of plants containing Curcumin. |
| **T3.2** | Target <-> Plant Roundtrip | 1. Query Target mode for `"PTGS2"` / `"COX-2"`.<br>2. Extract active plant-derived molecules.<br>3. Verify Curcumin is listed.<br>4. Follow plant source link. | Links resolve back to `Curcuma longa`. |
| **T3.3** | Pathway <-> Target <-> Molecule Linkage | 1. Query Process mode for `"apoptosis"`.<br>2. Retrieve participating UniProt targets.<br>3. Retrieve potent plant-derived molecules with $p\text{ChEMBL} \ge 6.0$. | Validates tripartite graph traversal: Pathway $\to$ Targets $\to$ Molecules $\to$ Plants. |
| **T3.4** | Potency Slider Filtering Monotonicity | 1. Target mode for `"PTGS2"` with $p\text{ChEMBL} \ge 6.0$.<br>2. Slide threshold to $p\text{ChEMBL} \ge 7.0$ and $\ge 8.0$. | Count of returning molecules must monotonically decrease ($N_{8.0} \le N_{7.0} \le N_{6.0}$). |
| **T3.5** | Only-Plants Toggle Filter | 1. Target mode for `"PTGS2"` with toggle ON.<br>2. Toggle OFF to include all ChEMBL bioactives. | $N_{\text{all\_chembl}} \ge N_{\text{plant\_only}}$, and 100% of molecules in plant-only have $\ge 1$ verified plant source. |

---

### Tier 4: Real-World Scenarios & Pilot Validation

| ID | Scenario | Dataset / Species | Authoritative Expected Metric Bounds |
|---|----------|-------------------|--------------------------------------|
| **T4.1** | *Curcuma longa* Pilot Replication | Curcuma longa (Wikidata/LOTUS + ChEMBL + Reactome) | - LOTUS records: $230 \le N \le 250$ (Pilot: 239)<br>- Distinct skeletons (Block 1): $160 \le N_{\text{struct}} \le 180$ (Pilot: 169)<br>- ChEMBL matches: $100 \le N_{\text{match}} \le 125$ (Pilot: 110)<br>- Filtered single-protein activities: $430 \le N_{\text{act}} \le 480$ (Pilot: 459)<br>- Unique UniProt targets: $130 \le N_{\text{target}} \le 150$ (Pilot: 140)<br>- Curcumin target contribution: $80 \le N_{\text{curcumin}} \le 90$ targets (~61% dominance)<br>- Reactome recognized targets: $125 \le N_{\text{reactome}} \le 138$ (Pilot: 132)<br>- Data Coverage Score: $58.0 \le \text{Score} \le 62.0$ (Pilot: 60/100) |
| **T4.2** | Under-Studied Plant Evaluation | Sparse plant species (e.g. *Smallanthus sonchifolius* / Yacón) | - Identifies low data regime.<br>- Data Coverage Score $\le 40/100$.<br>- Displays low-evidence notice.<br>- No crashes despite missing bioactivities or pathways. |
| **T4.3** | Headless UI Execution (Tab 1: Planta) | `streamlit.testing.v1.AppTest` | - App initializes without exception.<br>- Tab 1 selected; inputs `"Curcuma longa"`.<br>- Confirmation card renders.<br>- Analyses trigger; disclaimers & dominance alerts visible.<br>- Download buttons present. |
| **T4.4** | Headless UI Execution (Tab 2: Molécula) | `streamlit.testing.v1.AppTest` | - Tab 2 selected; inputs `"CHEMBL140"`.<br>- Auto-detector identifies `'CHEMBL_ID'`.<br>- Depiction card renders.<br>- Plant occurrences table renders.<br>- Disclaimer banner present. |
| **T4.5** | Headless UI Execution (Tab 3: Proteína/Proceso) | `streamlit.testing.v1.AppTest` | - Tab 3 selected; searches `"PTGS2"`.<br>- Potency slider interacts.<br>- Only-plants toggle interacts.<br>- Pathway keyword search executes.<br>- Disclaimer banner present. |

---

## 4. Authoritative Output Derivation

For every numerical assertion in the test suite, the authoritative source is audited as follows:

1. **Curcuma longa Reference**:
   - `piloto_curcuma/resumen.json`: `{"n_lotus": 239, "n_chembl": 110, "n_actividades_proteina": 459, "n_blancos": 140, "reactome_not_found": 8}`
   - `piloto_curcuma/compuestos.csv`: 239 compound rows, 169 distinct first blocks (`ik.split('-')[0]`).
   - `piloto_curcuma/actividades.csv`: 459 filtered human single-protein rows. Curcumin (`CHEMBL140`) contributes 196 activity rows across 85 distinct UniProt targets.
   - `diapositiva_curcuma.md`:
     $$A = 1.00, \quad B_w = 0.58, \quad C_w = 0.31, \quad D = 0.94, \quad E = 0.59$$
     $$\text{Score} = 100 \times (0.10 \times 1.00 + 0.20 \times 0.58 + 0.30 \times 0.31 + 0.15 \times 0.94 + 0.25 \times 0.59) = 59.59 \approx 60$$
2. **Curcumin Structure**:
   - ChEMBL ID: `CHEMBL140`
   - InChIKey: `VFLDPWHFBUODDF-FCXRPNKRSA-N`
   - Block 1: `VFLDPWHFBUODDF`
3. **PTGS2 / COX-2 Target**:
   - ChEMBL Target ID: `CHEMBL230`
   - UniProt ID: `P35354`
   - Organism: `Homo sapiens`
   - Target Type: `SINGLE PROTEIN`

---

## 5. Execution Environment & Dependencies

- **Python**: `>= 3.11`
- **Testing Packages**:
  - `pytest >= 8.0`
  - `streamlit >= 1.35.0` (with `streamlit.testing.v1.AppTest`)
  - `pandas >= 2.0`
  - `requests >= 2.31`
- **Isolation Guarantee**: Tests do NOT modify `piloto_curcuma/` or production databases; temporary databases or in-memory SQLite fixtures are utilized for dynamic test state.
