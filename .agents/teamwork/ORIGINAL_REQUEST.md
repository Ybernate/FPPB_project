# Original User Request

## 2026-10-15T01:48:48Z

Build the first version (v1) of a Spanish-language web application ("Conoce tu planta") that integrates the open databases LOTUS, COCONUT, ChEMBL and Reactome so a student or researcher can go from a plant to its compounds, targets and pathways, from a molecule to the plants that contain it, and from a protein or biological process to the molecules and plants linked to it. It will be demoed to a professor next week on the author's laptop; visuals, clarity, correctness and responsiveness matter.

Working directory: C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\app
Integrity mode: development

Reference material (already in the workspace; read it before starting):
- C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\piloto_curcuma\ — working pilot (piloto.py, analisis_extra.py, resumen.py, CSV outputs) for Curcuma longa: LOTUS (via Wikidata SPARQL) -> ChEMBL -> Reactome.
- C:\Users\yediy\.gemini\antigravity\brain\de2bb0f4-4760-4c91-8338-d948a1211513\webapp_plan.md — approved plan with decisions and milestones.
- C:\Users\yediy\.gemini\antigravity\brain\de2bb0f4-4760-4c91-8338-d948a1211513\diapositiva_curcuma.md — verified pilot numbers, known biases and the proposed Data Coverage Score.
- The original abstract (FPPB_202602_Anteproyecto_YedidiasBernate.pdf in the FPPB_Project folder).

Pilot facts to treat as the reference (as of 2026-10-12; tolerate small drift from database updates): Curcuma longa -> 239 LOTUS records = 169 distinct structures (first block of InChIKey); 110 match ChEMBL by full InChIKey; 34 compounds have >=1 human single-protein IC50/Ki measurement; 459 such activities; 140 unique targets (132 recognized by Reactome). Curcumin = CHEMBL140, InChIKey VFLDPWHFBUODDF-FCXRPNKRSA-N, contributes 85 of the 140 targets.

## Requirements

### R1. Three search modes with friendly, validated entry
The app has three tabs, each with its own search box and autocomplete: Plant, Molecule, Protein/Process. Entry must be easy for non-experts, not only researchers.
- Plant: accepts scientific or common names in Spanish and English; resolves synonyms to the accepted name; tolerates authorship, case and small typos; shows a confirmation card (accepted name, family, common names, and an image when available) before analysis; friendly message when no data exist, suggesting close species that do have data; clickable examples; a visible "identify by photo (coming soon)" placeholder without working photo identification.
- Molecule: accepts a common name or synonym, a SMILES, an InChIKey or a ChEMBL ID and detects the format automatically; suggestions show the drawn structure; matching across databases is by chemical structure (first block of InChIKey), not by name.
- Protein/Process: protein by name or gene symbol with suggestions; process through Reactome pathways (user types words such as "inflamación" or "apoptosis" and picks a pathway). No other process vocabulary.

### R2. Data integration (LOTUS and COCONUT both used)
LOTUS and COCONUT are used together as plant–compound sources, with the source of every record visible. COCONUT has no usable public API without a key, so it must be used from its official bulk download (CSV); the team should also evaluate a downloadable LOTUS dump and fall back to the live Wikidata query only where a local dump is not viable. Downloaded data goes into a git-ignored data folder inside the working directory and is turned into a fast local index by a reproducible script. ChEMBL and Reactome are queried through their public APIs with an on-disk cache. Network access is limited to public endpoints of these databases and of name-resolution services (e.g. GBIF); no other external services. Do not claim COCONUT column names or LOTUS dump availability without confirming them against the real files.

### R3. Results per mode
- Plant -> compounds: compounds table ordered by number of supporting references, with drug-likeness properties, ChEMBL match flag, structure drawings; human single-protein targets with measured affinities (IC50/Ki, exact measurements, normalized units); Reactome pathway enrichment; per-compound target counts so that dominance by one molecule is visible; and a Data Coverage Score with its component breakdown (compounds reported, ChEMBL match weighted by references, targets measured weighted by references, Reactome recognition, depth of evidence), as defined in the reference slide document.
- Molecule -> plants: plants (LOTUS/COCONUT) containing the molecule or its stereochemical variants, its ChEMBL targets and affinities, and pathways.
- Protein or pathway -> molecules and plants: by default only molecules with at least one plant source, with a toggle to include the rest of ChEMBL and an adjustable potency threshold (default pChEMBL >= 6, exact measurements). Results link molecules to plants.
- A coverage/evidence indicator analogous to the score in the two reverse modes.

### R4. Honesty and visible limitations
Make known biases visible rather than hidden: one molecule can dominate a plant's targets; assay panels can inflate pathways (e.g. carbonic anhydrase); extreme potency values should link to their source assay; first-block matching merges stereoisomers. Every screen with results carries a clear notice that results are molecular laboratory evidence, not clinical evidence or medical advice. No screen may claim that a plant treats or cures anything.

### R5. Visual quality and export
Modern, clean scientific look: light background, botanical green accent, large indicator cards, interactive charts (data funnel, plant–molecule–protein network, pathway bars), drawn chemical structures, readable on a projector. All text in Spanish. Results can be exported as CSV and JSON with standard identifiers (InChIKey, UniProt, ChEMBL, Reactome) and links to the source records. The app is built in Python with Streamlit and Plotly with custom CSS and runs locally with a documented one-command start.

### R6. Quality and reproducibility
Automated tests for the data core and input validation, a README (in Spanish) explaining setup, data preparation and how to run, and a short list of known limitations. Pick the under-studied validation plant by comparing 3–4 candidates using real data and document the choice.

## Acceptance Criteria

### Data core and reproducibility
- [ ] A single documented command prepares the local data index from the downloaded COCONUT (and LOTUS if used) files, and a single command starts the app.
- [ ] Plant mode for Curcuma longa reproduces the pilot within tolerance (~239 LOTUS records / ~169 structures; ~110 ChEMBL matches; ~459 single-protein activities; ~140 targets) and the test suite asserts these ranges.
- [ ] Round trip: curcumin (CHEMBL140) in Molecule mode lists Curcuma longa among its plants, and Curcuma longa in Plant mode lists curcumin among its compounds (asserted in tests).
- [ ] Protein mode for a well-known target (e.g. COX-2/PTGS2) and Process mode for a Reactome pathway each return molecules with plant sources and link them to plants (asserted in tests).
- [ ] Both LOTUS and COCONUT contribute records and every record shows its source.

### Input validation
- [ ] Automated tests pass for: "curcuma longa L.", "Curcuma Longa", "cúrcuma", "turmeric", a one-letter typo of the scientific name, a SMILES, an InChIKey, a ChEMBL ID, a protein name and gene symbol, and a Reactome-pathway search by word; each lands on the intended entity or a clear suggestion list.
- [ ] Empty input, nonsense input, a species with no data and a simulated network failure each produce a clear Spanish message and never a stack trace.

### Interface and honesty
- [ ] The three tabs run end to end in a headless UI test (Streamlit AppTest or equivalent) without exceptions for the cases above.
- [ ] Each results screen displays the non-clinical-evidence notice, the source of the data, and at least the dominance-by-one-molecule indicator in Plant mode.
- [ ] Exports (CSV and JSON) are produced for each mode and contain the standard identifiers.
- [ ] The photo option appears only as a "coming soon" placeholder.

### Quality gates
- [ ] Test suite passes with a single command; lint passes.
- [ ] A cold plant search for Curcuma longa with a warm cache returns in under 10 seconds on the author's machine, and the first (cold) run shows a progress indicator.
- [ ] An independent reviewer agent, using a written rubric (clarity of entry, correctness against the pilot numbers, absence of clinical claims, visual consistency, Spanish text quality), checks the final app and reports pass/fail per item.

## 2026-10-17T18:58:10Z

El sistema detuvo temporalmente los subagentes y tareas en segundo plano por una cancelación forzada. Por favor:
1. Revisa el estado actual del proyecto y del orquestador (`d5e4984c-f7f9-4829-92db-92d868cf7765`), verifica en qué quedó la compuerta de verificación de M0 y reactiva los subagentes o crons de monitoreo que hayan quedado detenidos.
2. Envía un reporte del progreso actual.
3. Continúa inmediatamente con la ejecución de los hitos restantes (M0 cierre -> M1 -> M2 -> M3 -> M4 -> M5 -> M6 y auditoría final) hasta completar todos los criterios de aceptación de la aplicación web "Conoce tu planta" (v1).
