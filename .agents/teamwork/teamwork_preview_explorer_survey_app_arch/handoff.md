# Reporte de Arquitectura de Aplicación: "Conoce tu planta" (R1, R3, R4, R5, R6)

**Agente:** `teamwork_preview_explorer_survey_app_arch`  
**Directorio de trabajo:** `C:\Users\yediy\OneDrive\Guías\Documents\FPPB\FPPB_Project\.agents\teamwork\teamwork_preview_explorer_survey_app_arch\`  
**Fecha:** 2026-10-15  

---

## 1. Observaciones Directas

1. **Requerimientos Autorizados (`ORIGINAL_REQUEST.md`):**
   - **R1 (Tres modos de búsqueda con entrada amigable y validada):** Tres pestañas (*Planta*, *Molécula*, *Proteína/Proceso*). Modo Planta acepta nombres científicos o comunes (español/inglés), resuelve sinónimos al nombre aceptado, tolera autores y mayúsculas, muestra tarjeta de confirmación previa al análisis, mensajes amables ante ausencia de datos sugiriendo especies cercanas del mismo género, ejemplos clicables y botón "identificar por foto (próximamente)" sin ejecución funcional de visión artificial. Modo Molécula acepta nombre común, sinónimo, SMILES, InChIKey o ChEMBL ID con detección automática y vista de estructura dibujada; el cruce inter-bases es por estructura química (primer bloque del InChIKey, 14 caracteres). Modo Proteína/Proceso acepta nombre o símbolo génico (UniProt/ChEMBL) y rutas Reactome por términos en lenguaje natural ("inflamación", "apoptosis").
   - **R3 (Resultados por modo y Puntaje de Cobertura):** Planta $\to$ compuestos ordenados por referencias con drug-likeness, match ChEMBL, estructuras dibujadas, blancos proteicos humanos individuales con afinidades medidas (IC50/Ki), enriquecimiento de rutas Reactome, conteo de blancos por compuesto (revelando dominancia), y Puntaje de Cobertura de Datos con desglose de 5 componentes (A, B, C, D, E). Modo Molécula $\to$ plantas fuente (LOTUS/COCONUT) con variantes estereoquímicas, blancos y afinidades ChEMBL, rutas e indicador análogo. Modo Proteína/Proceso $\to$ moléculas y plantas con filtro por defecto de solo moléculas con planta fuente, toggle para incluir todo ChEMBL, y control deslizante de umbral de potencia ($p\text{ChEMBL} \ge 6.0$, mediciones exactas).
   - **R4 (Honestidad y limitaciones visibles):** Hacer visibles los sesgos conocidos: dominancia de una sola molécula (curcumina aporta el 61% de los blancos), inflación de rutas por paneles de isoformas (ej. 11 isoformas de anhidrasa carbónica evaluadas simultáneamente en `piloto_curcuma/actividades.csv:4-14`), advertencia de valores extremos de potencia ($p\text{ChEMBL} \ge 9.0$) con enlace a la publicación fuente, y aclaración del agrupamiento de estereoisómeros por primer bloque de InChIKey. **Aviso mandatorio en todas las pantallas:** evidencia de laboratorio molecular preclínico (*in vitro*/*in silico*), no constituye evidencia clínica ni recomendación médica; ninguna pantalla puede afirmar que una planta cura o trata nada.
   - **R5 (Calidad visual y exportación):** Estilo botánico moderno: fondo claro (`#FAFCF8`), acento verde botánico (`#1B4332`, `#2D6A4F`), tarjetas con indicadores grandes, gráficos interactivos con Plotly (embudo de datos, red planta–molécula–proteína, barras horizontales de rutas Reactome), estructuras químicas dibujadas en 2D, legibilidad optimizada para proyector. Texto 100% en español. Exportación a CSV y JSON con identificadores estándar (InChIKey, UniProt, ChEMBL, Reactome). Ejecución local con comando único documentado.
   - **R6 (Calidad y reproducibilidad):** Pruebas automatizadas con `pytest` y `streamlit.testing.v1.AppTest`, README en español, lista de limitaciones conocidas, tiempo de respuesta en búsqueda fría con caché tibia menor a 10 segundos en *Curcuma longa*.

2. **Datos del Piloto (`piloto_curcuma/` y `diapositiva_curcuma.md`):**
   - *Curcuma longa* cuenta con 239 registros en LOTUS correspondientes a 169 estructuras únicas (primer bloque InChIKey).
   - 110 coinciden con ChEMBL por InChIKey exacto; 42 registros adicionales poseen variantes estereoquímicas en ChEMBL.
   - 34 compuestos presentan $\ge 1$ medición sobre proteína humana individual; 459 actividades IC50/Ki en nM sobre proteínas individuales; 140 blancos proteicos únicos (132 reconocidos por Reactome).
   - Dominancia: la curcumina (CHEMBL140, InChIKey `VFLDPWHFBUODDF-FCXRPNKRSA-N`) aporta 85 de los 140 blancos (60.7%) y 196 de las 459 actividades.
   - Fórmula del Puntaje de Cobertura de Datos:
     $$A = \min(1.0, \log_{10}(1 + N) / \log_{10}(101)), \quad N = 169 \implies A = 1.00$$
     $$B = \sum_{i \in \text{matched}} \text{refs}_i / \sum_i \text{refs}_i \implies B = 0.58$$
     $$C = \sum_{i \in \text{with\_target}} \text{refs}_i / \sum_i \text{refs}_i \implies C = 0.31$$
     $$D = \text{Blancos en Reactome} / \text{Blancos totales} = 132/140 \implies D = 0.94$$
     $$E = \text{Blancos con } \ge 2 \text{ mediciones} / \text{Blancos totales} = 83/140 \implies E = 0.59$$
     $$\text{Puntaje} = 100 \times (0.10 A + 0.20 B + 0.30 C + 0.15 D + 0.25 E) = 60/100$$

3. **Entorno de Ejecución:**
   - SO: Windows 11, Python 3.11.9 (`C:\Users\yediy\AppData\Local\Microsoft\WindowsApps\python.exe`).
   - Resolución de paquetes verificada exitosamente vía `pip install --dry-run`:
     - `streamlit==1.66.0` (incluye `streamlit.testing.v1.AppTest`)
     - `plotly==7.1.0`
     - `rdkit==2026.9.1` (wheel precompilado `rdkit-2026.9.1-cp311-cp311-win_amd64.whl` disponible sin compilación)
     - `pandas==3.0.6`
     - `requests==2.34.2`
     - `pytest==9.1.1`

---

## 2. Cadena Lógica y Diseño Arquitectónico

### A. Estructura del Proyecto y Separación de Responsabilidades
Para cumplir con las reglas de layout (código de aplicación en `app/`, datos e índices locales en `data/`, y cero código fuente en `.agents/teamwork/`), la arquitectura se estructura de la siguiente manera:

```text
FPPB_Project/
├── app/
│   ├── main.py                     # Punto de entrada principal (st.set_page_config, inyección CSS, pestañas)
│   ├── state.py                    # Gestión centralizada del st.session_state y eventos
│   ├── styles/
│   │   ├── botanical.css           # Hoja de estilos botánica (paleta, tipografía, tarjetas, responsive)
│   │   └── theme.py                # Inyector de CSS y helper de estilos
│   ├── components/
│   │   ├── __init__.py
│   │   ├── tab_plant.py            # Pestaña 1: Exploración por Planta (R1, R3, R4)
│   │   ├── tab_molecule.py         # Pestaña 2: Exploración por Molécula (R1, R3, R4)
│   │   ├── tab_target_process.py   # Pestaña 3: Exploración por Blanco / Proceso (R1, R3, R4)
│   │   ├── cards.py                # Tarjeta de confirmación taxonómica, KPI cards y desglose del score
│   │   ├── charts.py               # Gráficos Plotly: Embudo, Red interactiva y Barras de rutas
│   │   ├── chem_render.py          # Renderizado 2D de moléculas con RDKit SVG y fallbacks
│   │   ├── disclaimers.py          # Banners de honestidad, avisos preclínicos y alertas de sesgo
│   │   └── export.py               # Exportadores CSV / JSON y botones de descarga st.download_button
│   ├── core/                       # Núcleo de datos y lógica biológica
│   │   ├── __init__.py
│   │   ├── data_loader.py          # Consulta al índice local SQLite/DuckDB (LOTUS + COCONUT)
│   │   ├── chembl_client.py        # Cliente ChEMBL API con caché en disco (diskcache / SQLite)
│   │   ├── reactome_client.py      # Cliente Reactome API con caché en disco
│   │   ├── name_resolver.py        # Normalización taxonómica, sinónimos y autocompletado GBIF
│   │   └── scoring.py              # Cálculo exacto del Puntaje de Cobertura y variantes inversas
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # Fixtures de datos del piloto y mocks de red
│       ├── test_inputs.py          # Validación de entradas, sinónimos, regexes y typos
│       ├── test_pilot_metrics.py   # Aserción numérica del piloto y fórmula del Puntaje (60/100)
│       ├── test_roundtrip.py       # Pruebas de ida y vuelta (curcumina <-> Curcuma longa)
│       ├── test_exports.py         # Validación de integridad de esquemas CSV y JSON
│       └── test_ui_apptest.py      # Pruebas de interfaz headless con Streamlit AppTest
├── data/                           # Índices locales (git-ignored) generados por script reproducible
│   ├── local_index.db              # SQLite index de LOTUS + COCONUT
│   └── cache/                      # Directorio de caché persistente de APIs
└── piloto_curcuma/                 # Archivos originales del piloto (referencia inmutable)
```

---

### B. Gestión del Estado en Streamlit (`st.session_state`)

Streamlit re-ejecuta el script completo en cada interacción. Para evitar la pérdida de parámetros, parpadeos de interfaz y consultas de red redundantes, el estado se aísla mediante el siguiente esquema:

```python
# Esquema de estado unificado en app/state.py
INITIAL_STATE = {
    # Navegación
    "active_tab_index": 0,          # 0: Planta, 1: Molécula, 2: Proteína/Proceso
    
    # Estado Modo Planta
    "plant_search_text": "",
    "plant_selected_species": None,  # Dict con taxon_id, scientific_name, accepted_name, family, vernacular_es, image_url
    "plant_confirmed": False,        # Controla la visualización previa a la ejecución pesada
    "plant_data": None,             # Resultados cacheados: compounds, activities, targets, pathways, score
    "plant_pchembl_threshold": 6.0,  # Filtro de potencia interactivo
    
    # Estado Modo Molécula
    "mol_search_text": "",
    "mol_detected_type": None,      # 'CHEMBL_ID' | 'INCHIKEY' | 'SMILES' | 'NAME'
    "mol_selected_entity": None,    # Dict con chembl_id, inchikey, inchikey_block1, smiles, pref_name
    "mol_data": None,               # Resultados cacheados: plants, activities, targets, pathways
    
    # Estado Modo Proteína / Proceso
    "target_submode": "protein",     # 'protein' | 'process'
    "protein_search_text": "",
    "protein_selected": None,       # Dict con uniprot, chembl_target_id, pref_name
    "process_search_text": "",
    "process_selected": None,       # Dict con stId, name, entities_count
    "target_only_plants": True,     # R3: por defecto solo moléculas con planta fuente
    "target_pchembl_threshold": 6.0,# R3: umbral por defecto pChEMBL >= 6
    "target_exact_only": True,      # R3: relación '='
    "target_data": None,
    
    # Modal / Placeholders
    "show_photo_dialog": False,     # Modal informativo para 'Identificar por foto (próximamente)'
    "error_message": None           # Captura de errores no fatales para visualización limpia
}
```

**Estrategia de Caché y Rendimiento ($< 10$ s):**
- Autocompletado taxonómico y de nombres químicos: `@st.cache_data(ttl=3600, show_spinner=False)`.
- Consultas bioactivas pesadas a ChEMBL y Reactome: decoradas con `@st.cache_data(persist="disk")` y respaldo en SQLite local.
- Primera búsqueda de *Curcuma longa* descarga o lee de caché; subsecuentes búsquedas resuelven de inmediato ($< 1$ segundo).

---

### C. Diseño Visual Botánico y CSS Personalizado (R5)

1. **Tokens de Color y Atmósfera Visual:**
   - **Fondo de aplicación:** `#FAFCF8` (blanco herbal cálido; elimina el brillo fatigante de proyectores).
   - **Superficie de tarjetas (`cards`):** `#FFFFFF` con borde sutil `#D9E2D5` y sombra tenue `0 2px 8px rgba(27,67,50,0.06)`.
   - **Verde botánico primario:** `#1B4332` (verde bosque profundo; usado en botones principales, títulos y métricas clave).
   - **Verde botánico secundario:** `#2D6A4F` y acento `#40916C` (verde hoja; para insignias, enlaces y estados activos).
   - **Verde botánico de fondo:** `#E8F5E9` (para tags de fuentes LOTUS/COCONUT y fondos destacados).
   - **Texto principal:** `#1C2826` (contraste superior a 10:1, supera ampliamente WCAG AAA).
   - **Acento ámbar/terracota:** `#D97706` y fondo `#FEF3C7` (para moléculas y alertas de sesgo).
   - **Acento azul pizarra:** `#0284C7` y fondo `#F0F9FF` (para dianas proteicas y UniProt).

2. **Inyección CSS (`app/styles/botanical.css`):**
   - Personalización de `stTabs`: pestañas con fuente semibold, padding ergonómico y borde inferior verde botánico (`#1B4332`).
   - Personalización de `stMetric`: valor numérico grande (2.4rem), etiqueta clara en mayúsculas pequeñas.
   - Tarjetas personalizadas (`.botanical-card`): contenedor limpio para confirmación taxonómica y detalles moleculares.
   - Banners de notificación con estilo científico:
     - `.callout-preclinical`: franja lateral azul `#0284C7`, fondo `#F0F9FF`.
     - `.callout-bias`: franja lateral ámbar `#D97706`, fondo `#FFFBEB`.
     - `.callout-extreme`: franja lateral roja suave `#EF4444`, fondo `#FEF2F2`.

3. **Placeholder "Identificar por foto (próximamente)":**
   - Renderizado en la Pestaña Planta como un botón estilizado con icono de cámara: `st.button("📷 Identificar por foto (próximamente)", use_container_width=False)`.
   - Al pulsar, abre un diálogo informativo (`@st.dialog` o banner) con el texto: *"La identificación automatizada de especies botánicas a partir de fotografías mediante modelos de visión por computadora está programada para la versión 2.0. Por ahora, ingrese el nombre común o científico en el buscador."*

---

### D. Gráficos Interactivos con Plotly (R5)

1. **Embudo de Atrición de Datos (Data Funnel):**
   - Componente: `plotly.graph_objects.Funnel`.
   - Fases para *Curcuma longa*:
     1. LOTUS / COCONUT (239 registros)
     2. Estructuras distintas (primer bloque InChIKey) (169 estructuras)
     3. Coincidencia en ChEMBL (110 compuestos)
     4. Bioactividad humana medida (IC50/Ki) (34 compuestos)
     5. Blancos proteicos únicos medidos (140 proteínas)
     6. Reconocidos en Reactome (132 proteínas)
   - Paleta: Degradado botánico continuo (`['#1B4332', '#2D6A4F', '#40916C', '#52B788', '#74C69D', '#A3E4D7']`).
   - Etiquetas: Muestra el recuento absoluto y el porcentaje respecto a la fase previa.

2. **Red Interactiva Planta–Molécula–Proteína:**
   - Componente: `plotly.graph_objects.Scatter` (aristas + nodos) basado en grafo `networkx`.
   - Disposición visual (Layout Tripartito Guiado):
     - Capa Izquierda ($x=0$): Nodo Planta (*Curcuma longa*, verde grande `#1B4332`).
     - Capa Central ($x=1$): Nodos Moléculas (curcumina, bisdemetoxicurcumina, etc., ámbar `#D97706`, radio escalado por número de referencias y blancos).
     - Capa Derecha ($x=2$): Nodos Proteínas Blancos (UniProt targets, azul `#0284C7`).
   - Aristas:
     - Planta $\to$ Molécula: ancho proporcional a $\log(1 + \text{refs})$.
     - Molécula $\to$ Blanco: ancho proporcional a $p\text{ChEMBL}$, color verde translúcido.
   - Revelación de Dominancia: El nodo de Curcumina destaca visualmente al irradiar 85 conexiones hacia la columna de blancos, evidenciando de un solo vistazo el sesgo de investigación reportado en el piloto.

3. **Barras Horizontales de Rutas Reactome:**
   - Componente: `plotly.graph_objects.Bar(orientation='h')`.
   - Eje X: $-\log_{10}(\text{FDR})$ (magnitud de significancia estadística).
   - Eje Y: Nombre de la ruta (ordenado descendentemente).
   - Interactividad con el filtro de potencia: Al mover el slider de potencia ($p\text{ChEMBL} \ge 6.0$), la gráfica se actualiza dinámicamente recalculando el subconjunto de dianas y re-consultando o filtrando el enriquecimiento.
   - Resaltado de sesgo: Marcado diferenciado para rutas infladas por paneles de isoformas (*Reversible hydration of carbon dioxide*).

---

### E. Renderizado de Estructuras Químicas en 2D (R5)

1. **Motor Primario (RDKit Local):**
   - Utiliza `rdkit.Chem.Draw.rdMolDraw2D.MolDraw2DSVG` para generar SVGs vectoriales nítidos, escalables y con fondo transparente:
     ```python
     def smiles_to_svg(smiles: str, width: int = 240, height: int = 160) -> str:
         mol = Chem.MolFromSmiles(smiles)
         if not mol:
             return ""
         drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
         drawer.drawOptions().clearBackground = True
         drawer.drawOptions().backgroundColor = (0, 0, 0, 0)
         drawer.drawOptions().bondLineWidth = 2
         drawer.DrawMolecule(mol)
         drawer.FinishDrawing()
         return drawer.GetDrawingText()
     ```
   - Integración en Streamlit: Renderizado directo mediante `st.markdown(svg_text, unsafe_allow_html=True)` o en columnas de tablas/tarjetas.

2. **Mecanismo de Fallback:**
   - Si una cadena SMILES no puede ser parseada por RDKit o falla localmente:
     - Fallback 1: Consulta directa a la API de imágenes de ChEMBL (`https://www.ebi.ac.uk/chembl/api/data/image/{chembl_id}.svg`).
     - Fallback 2: SVG estático local que muestra la fórmula condensada o el icono molecular botánico con el texto *"Estructura 2D no disponible"*.

---

### F. Transparencia, Avisos de Honestidad y Sesgos (R4)

La aplicación integra de forma obligatoria y visible los siguientes avisos redactados rigurosamente en español:

1. **Aviso de Evidencia Preclínica de Laboratorio (En TODAS las pantallas de resultados):**
   ```html
   <div class="callout-preclinical">
     <strong>⚠️ Aviso de evidencia científica de laboratorio:</strong><br>
     Los datos presentados corresponden exclusivamente a mediciones moleculares <em>in vitro</em>, 
     <em>in silico</em> y bioquímicas recopiladas en bases de datos abiertas (LOTUS, COCONUT, ChEMBL y Reactome). 
     <strong>No constituyen evidencia clínica, farmacológica en humanos ni recomendación médica.</strong> 
     Esta plataforma tiene fines exclusivamente académicos y de exploración biomolecular; 
     no afirma ni respalda que ninguna planta cure, prevenga o trate enfermedad alguna.
   </div>
   ```

2. **Sesgo de Dominancia por Compuesto Único (Gatillado en Planta cuando $\text{blancos}(\text{top}) / \text{total} \ge 0.40$):**
   ```html
   <div class="callout-bias">
     <strong>ℹ️ Sesgo de investigación — Dominancia molecular:</strong><br>
     En <em>Curcuma longa</em>, un único metabolito (<strong>curcumina</strong>, CHEMBL140) aporta 
     <strong>85 de los 140 blancos proteicos identificados (60.7%)</strong> y 196 de las 459 mediciones de afinidad. 
     El perfil biológico resultante refleja principalmente el volumen histórico de publicaciones sobre este compuesto aislado, 
     y no la acción integral del fitocomplejo o extracto vegetal completo.
   </div>
   ```

3. **Sesgo de Paneles de Ensayo en Rutas Reactome:**
   ```html
   <div class="callout-bias">
     <strong>ℹ️ Sesgo metodológico en rutas biológicas:</strong><br>
     Rutas como <em>"Reversible hydration of carbon dioxide"</em> presentan un enriquecimiento artificialmente elevado 
     (FDR &lt; 10⁻¹³) debido a que ensayos de laboratorio evaluaron compuestos individuales (ej. ácido cafeico) frente 
     a paneles completos de isoformas de anhidrasa carbónica (CA1 a CA14). Aplique el filtro de potencia farmacológica 
     (pChEMBL ≥ 6.0) para discriminar blancos con afinidad sub-micromolar relevante.
   </div>
   ```

4. **Advertencia de Afinidad Extrema ($p\text{ChEMBL} \ge 9.0$, sub-nanomolar):**
   - Resalta mediciones con afinidad $< 1\,\text{nM}$ (ej. curcumina frente a proteína precursora de amiloide $\beta$, $p\text{ChEMBL} = 9.68 \approx 0.2\,\text{nM}$) con enlace directo a la ficha del ensayo en ChEMBL: `https://www.ebi.ac.uk/chembl/compound_report_card/{chembl_id}/`.

5. **Agrupamiento por Estereoisómeros (InChIKey Bloque 1):**
   - Nota explicativa en tablas: el cruce por los primeros 14 caracteres del InChIKey consolida variantes estereoquímicas y enantiómeros en una misma entidad de conectividad molecular.

---

### G. Arquitectura de Exportación (CSV y JSON) (R5)

Ambos formatos se generan en memoria usando `io.StringIO` y se descargan mediante `st.download_button`:

1. **Esquema de Exportación CSV:**
   - Tabla plana desnormalizada que incluye todas las dimensiones analíticas con identificadores estándar:
     - `modo_busqueda`: 'planta' | 'molecula' | 'proteina_proceso'
     - `termino_consulta`: texto introducido por el usuario
     - `especie_nombre_cientifico`: nombre aceptado
     - `compuesto_nombre`: nombre común o IUPAC
     - `inchikey`: clave InChIKey completa (27 caracteres)
     - `inchikey_bloque1`: conectividad (14 caracteres)
     - `smiles`: notación canónica SMILES
     - `chembl_id`: identificador de molécula ChEMBL
     - `n_referencias`: número de citas bibliográficas en LOTUS/COCONUT
     - `fuente_registro`: 'LOTUS', 'COCONUT', o 'AMBOS'
     - `blanco_nombre`: nombre del blanco proteico
     - `uniprot_id`: accesión UniProt de la proteína humana individual
     - `tipo_medicion`: 'IC50' o 'Ki'
     - `relacion_medicion`: '='
     - `valor_nM`: concentración en nanomolar
     - `pchembl`: valor negativo del logaritmo molar
     - `ruta_reactome_id`: identificador de ruta (ej. 'R-HSA-1234174')
     - `ruta_reactome_nombre`: nombre de la ruta biológica
     - `ruta_reactome_fdr`: tasa de falso descubrimiento (FDR)
   - Nombre de archivo: `conoce_tu_planta_{modo}_{timestamp}.csv`.

2. **Esquema de Exportación JSON:**
   - Documento jerárquico estructurado con trazabilidad y proveniencia:
     ```json
     {
       "metadatos": {
         "aplicacion": "Conoce tu planta",
         "version": "1.0.0",
         "fecha_consulta_utc": "2026-10-15T02:00:00Z",
         "modo": "planta",
         "consulta": "Curcuma longa",
         "bases_datos": {
           "LOTUS": "Wikidata SPARQL / Dump oficial",
           "COCONUT": "Bulk CSV v2026",
           "ChEMBL": "REST API v2.0",
           "Reactome": "Analysis Service v7.0"
         }
       },
       "puntaje_cobertura": {
         "puntaje_total": 60.0,
         "componentes": {
           "A_compuestos_reportados": 1.00,
           "B_coincidencia_chembl_ponderada": 0.58,
           "C_blancos_medidos_ponderados": 0.31,
           "D_reconocimiento_reactome": 0.94,
           "E_profundidad_evidencia": 0.59
         }
       },
       "resumen": {
         "n_compuestos_totales": 239,
         "n_estructuras_unicas": 169,
         "n_chembl_matches": 110,
         "n_blancos_unicos": 140,
         "n_rutas_enriquecidas": 15
       },
       "compuestos": [ ... ],
       "actividades": [ ... ],
       "rutas": [ ... ],
       "sesgos_detectados": [
         {
           "tipo": "dominancia_compuesto",
           "descripcion": "La curcumina aporta 85 de los 140 blancos (60.7%)."
         }
       ],
       "aviso_legal": "Resultados de laboratorio preclínico. No es evidencia médica ni clínica."
     }
     ```
   - Nombre de archivo: `conoce_tu_planta_{modo}_{timestamp}.json`.

---

### H. Estrategia de Pruebas Automatizadas (R6)

La suite de pruebas se divide en dos niveles complementarios: pruebas unitarias/integración con `pytest` y pruebas de interfaz headless con `Streamlit AppTest`.

1. **Nivel 1: Pruebas de Núcleo y Validación (`pytest`):**
   - `test_inputs.py`:
     - Normalización y resolución de: `"curcuma longa L."`, `"Curcuma Longa"`, `"cúrcuma"`, `"turmeric"`, y typo `"curcuma lnga"`.
     - Detección de formatos químicos: SMILES, InChIKey, InChIKey-Bloque1, ChEMBL ID (`CHEMBL140`), nombres comunes.
     - Casos de borde: entrada vacía, caracteres extraños (`"$$$###"`), especie sin datos (`"Arabidopsis thaliana"` si no tiene bioactividad en el índice) $\to$ mensajes amables sin excepciones ni trazas de error (`stack traces`).
     - Simulación de corte de red o API lenta $\to$ degradación elegante con datos cacheados y aviso al usuario.
   - `test_pilot_metrics.py`:
     - Reproducción numérica del piloto de *Curcuma longa*: aserción de rangos tolerantes (~239 registros LOTUS, ~169 estructuras distintas, ~110 ChEMBL matches, ~459 actividades humanas IC50/Ki sobre proteínas individuales, ~140 blancos únicos).
     - Validación de la fórmula de Puntaje de Cobertura ($60 \pm 2$).
   - `test_roundtrip.py`:
     - Prueba de ida y vuelta: *Curcuma longa* en Modo Planta contiene curcumina (CHEMBL140); curcumina en Modo Molécula lista a *Curcuma longa* entre sus plantas fuente.
     - Búsqueda de COX-2 / PTGS2 retorna curcumina y vincula a *Curcuma longa*.
   - `test_exports.py`:
     - Verifica generación correcta de buffers CSV y JSON con todas las columnas obligatorias y metadatos válidos.

2. **Nivel 2: Pruebas Headless de Interfaz (`Streamlit AppTest`):**
   - Utiliza `from streamlit.testing.v1 import AppTest`. Permite instanciar la aplicación completa en memoria, simular clics en pestañas, escribir en campos de texto, pulsar botones y validar el DOM resultante sin necesidad de levantar un navegador Chromium:
     ```python
     def test_e2e_plant_mode_apptest():
         at = AppTest.from_file("app/main.py", default_timeout=30)
         at.run()
         assert not at.exception
         
         # Seleccionar pestaña Planta e ingresar búsqueda
         at.text_input(key="plant_input").input("Curcuma longa").run()
         assert not at.exception
         
         # Verificar confirmación taxonómica
         assert any("Zingiberaceae" in m.value for m in at.markdown)
         
         # Pulsar botón de análisis
         at.button(key="btn_analyze_plant").click().run()
         assert not at.exception
         
         # Aserciones de requerimientos de honestidad y UI
         assert any("evidencia científica de laboratorio" in m.value.lower() for m in at.markdown)
         assert any("sesgo de investigación" in m.value.lower() for m in at.markdown)
         assert len(at.download_button) >= 2  # CSV y JSON presentes
         
     def test_photo_button_placeholder():
         at = AppTest.from_file("app/main.py", default_timeout=30)
         at.run()
         at.button(key="btn_photo_placeholder").click().run()
         assert not at.exception
         assert any("próximamente" in m.value.lower() for m in at.markdown or at.info)
     ```

---

## 3. Advertencias y Limitaciones Consideradas (Caveats)

1. **Disponibilidad de RDKit en entornos restringidos:**
   Aunque se verificó que el wheel oficial de RDKit para Windows x64 Python 3.11 (`rdkit-2026.9.1-cp311-cp311-win_amd64.whl`) se resuelve sin problemas, la arquitectura contempla una arquitectura defensiva: si RDKit fallara al inicializarse en tiempo de ejecución, la función `smiles_to_svg` conmuta de forma transparente a la API de renderizado de ChEMBL o a un SVG vectorial prefabricado, impidiendo que la UI falle.
2. **Dependencia de Red para APIs Vivas (ChEMBL y Reactome):**
   Para satisfacer el criterio de tiempo de respuesta ($< 10$ s) y resiliencia ante cortes de red en la presentación del profesor, las respuestas de ChEMBL y Reactome para las especies de demostración (*Curcuma longa* y la especie poco estudiada) deben persistirse en disco (`data/cache/` o SQLite).
3. **Puntaje de Cobertura en Modos Inversos:**
   En los modos Molécula y Proteína/Proceso, el indicador análogo debe adaptar los componentes B y C (ya que el punto de partida es la molécula o el blanco). Se define un indicador de "Nivel de Respaldo Fitoquímico" basado en número de especies botánicas confirmadas, consistencia entre LOTUS y COCONUT, y afinidad farmacológica confirmada ($p\text{ChEMBL} \ge 6.0$).

---

## 4. Conclusión

El diseño arquitectónico propuesto resuelve de forma exhaustiva, modular y rigurosa los requerimientos R1, R3, R4, R5 y R6:
1. **Flujo de Usuario y Validación (R1):** Pestañas desacopladas con autocompletado tolerante a fallos, confirmación taxonómica visual, detección automática de formatos moleculares y enlace bidireccional entre plantas, moléculas y procesos.
2. **Integridad de Resultados y Métricas (R3):** Presentación completa de tablas ordenadas, drug-likeness, cálculo exacto del Puntaje de Cobertura de Datos (60/100 en Curcuma longa) y filtros interactivos de afinidad.
3. **Honestidad Científica Intransigente (R4):** Identificación y exposición visible de los sesgos de dominancia (curcumina 61%), inflación metodológica de paneles de ensayo (anhidrasa carbónica), valores extremos de afinidad ($p\text{ChEMBL} \ge 9.0$) y el aviso mandatorio de evidencia preclínica no médica.
4. **Excelencia Visual y Exportación (R5):** Identidad visual botánica limpia y legible en proyector con Plotly (embudo, red interactiva tripartita, barras de rutas), renderizado químico RDKit SVG, y exportación completa a CSV y JSON con identificadores estándar.
5. **Garantía de Calidad y Reproducibilidad (R6):** Conjunto integral de pruebas automatizadas que combina `pytest` para lógica analítica y `Streamlit AppTest` para pruebas de interfaz de usuario sin navegador externo.

---

## 5. Método de Verificación Independiente

Para verificar de forma autónoma los postulados de este reporte arquitectónico:

1. **Verificación de Entorno y Paquetes:**
   Ejecutar en la terminal de PowerShell:
   ```powershell
   python -m pip install --dry-run streamlit plotly pandas requests rdkit pytest
   ```
   *Condición de éxito:* La salida muestra resolución limpia de todos los paquetes para Python 3.11 en Windows sin errores de compilación ni conflictos de dependencias.

2. **Verificación de Reproducción del Piloto:**
   Ejecutar en `piloto_curcuma/`:
   ```powershell
   python piloto_curcuma/analisis_extra.py
   ```
   *Condición de éxito:* Se imprimen las métricas de Curcuma longa ($N=169$ estructuras, coincidencia ChEMBL con variantes rescued, curcumina aportando la mayoría de los blancos, y Puntaje ponderado $= 60$).

3. **Verificación del Esquema de Pruebas de Interfaz:**
   Verificar que `streamlit.testing.v1.AppTest` esté disponible una vez instalado Streamlit:
   ```powershell
   python -c "from streamlit.testing.v1 import AppTest; print('AppTest available')"
   ```
   *Condición de éxito:* Se imprime `AppTest available` sin errores de importación.

4. **Condiciones de Invalidación:**
   - La arquitectura se invalidaría si Streamlit requiriese dependencias incompatibles con Python 3.11 en Windows.
   - Se invalidaría si el cálculo de puntaje o números del piloto difirieran de las métricas verificadas en `diapositiva_curcuma.md` ($60/100$).
