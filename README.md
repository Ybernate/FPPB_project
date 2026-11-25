# FitoEvidencia

> **Evidencia molecular abierta sobre plantas, compuestos, blancos y rutas**
> *Integración de datos abiertos: LOTUS, COCONUT, ChEMBL y Reactome*
> **Autor:** Yedidias Bernate
> **Proyecto Académico:** Farmacología y Fitoquímica / Biotecnología (FPPB 2026)

> **Modo demostración.** El repositorio se distribuye sin la base de datos; esta se
> construye con `scripts/prepare_data.py`. Sin los volcados de LOTUS/COCONUT, el único
> índice disponible es el de **demostración** (solo *Curcuma longa*, a partir del piloto
> real en `piloto_curcuma/`). La app lo indica con un aviso visible. Para el índice
> completo, ejecute `python scripts/prepare_data.py --download` donde Zenodo sea
> accesible (ver sección 3).

---

## 1. Resumen y Propósito Académico

El conocimiento tradicional y popular frecuentemente atribuye propiedades terapéuticas a diversas especies vegetales. Sin embargo, familiares, pacientes e investigadores se enfrentan a un vacío informativo crítico: la fragmentación de la evidencia científica abierta. Existen bases de datos botánicas y de productos naturales que recopilan qué metabolitos posee una planta, repositorios químicos que albergan bioactividades frente a proteínas humanas, y recursos biomédicos que mapean dichas proteínas a rutas celulares y cascadas de señalización. Históricamente, un estudiante o investigador debía consultar estas fuentes de forma aislada y manual.

**FitoEvidencia** surge como una solución computacional académica que unifica estos cuatro grandes repositorios abiertos (**LOTUS**, **COCONUT**, **ChEMBL** y **Reactome**) en una plataforma web ágil, rigurosa y transparente. La aplicación permite:
- Cruzar sistemáticamente desde la planta hasta sus compuestos, blancos proteicos humanos y vías biológicas enriquecidas.
- Realizar búsquedas inversas desde una molécula hacia las plantas que la contienen y sus blancos diana.
- Rastrear desde un blanco terapéutico (ej. `PTGS2` / COX-2) o proceso biológico ("inflamación", "apoptosis") hacia las moléculas bioactivas y especies vegetales de origen.
- Cuantificar objetivamente la completitud del conocimiento científico mediante el **Puntaje de Cobertura de Datos** (*Data Coverage Score*).
- Visibilizar con total honestidad científica los sesgos biológicos y de tamizaje experimental, manteniendo siempre una postura estricta de **evidencia preclínica molecular** (no clínica ni médica).

---

## 2. Arquitectura de Integración de Datos

El aplicativo implementa una arquitectura modular desacoplada en tres capas fundamentales:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FUENTES DE DATOS ABIERTAS                       │
├───────────────────┬───────────────────┬────────────────┬───────────────┤
│    LOTUS Dump     │   COCONUT Dump    │   ChEMBL REST  │ Reactome ORA  │
│ (Zenodo snapshot) │   (CSV Oficial)   │   (API + Cache)│ (API + Cache) │
└─────────┬─────────┴─────────┬─────────┴────────┬───────┴───────┬───────┘
          │                   │                  │               │
          ▼                   ▼                  │               │
┌───────────────────────────────────────┐        │               │
│         CAPA DE DATOS LOCAL           │        │               │
│  SQLite B-Tree Indexado               │        │               │
│  data/natural_products.db             │        │               │
│  (organismos, compuestos, ocurrencias)│        │               │
└───────────────────┬───────────────────┘        │               │
                    │                            │               │
                    ▼                            ▼               ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        NÚCLEO COMPUTACIONAL (app/core)                 │
│  - data_loader: consultas indexadas de organismos y fitoquímica        │
│  - name_resolver: normalización taxonómica, autorías y vernáculos      │
│  - chembl_client: filtrado estricto single-protein humana (IC50/Ki)    │
│  - reactome_client: análisis de sobre-representación (FDR, p-valor)    │
│  - scoring: cálculo del Puntaje de Cobertura (A, B_w, C_w, D, E)       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 INTERFAZ DE USUARIO Y VISUALIZACIÓN                    │
│  Streamlit + Plotly + RDKit (app/main.py, app/components/)             │
│  - Tema botánico de alto contraste para proyección en aula             │
│  - Embudo de datos, grafo tripartito de red, barras de enriquecimiento │
│  - Exportación estandarizada en formatos CSV y JSON                    │
└────────────────────────────────────────────────────────────────────────┘
```

1. **LOTUS & COCONUT (Almacenamiento Local Indexado)**:
   - Se procesan los volcados masivos oficiales de LOTUS y COCONUT, extrayendo las apariciones de productos naturales en especies vegetales (*Viridiplantae*), citas bibliográficas y descriptores moleculares (SMILES, InChIKey, peso molecular, LogP, TPSA, QED).
   - Se indexan en una base local SQLite (`data/natural_products.db`) con optimización B-Tree sobre `inchikey_block1`, `canonical_name`, `clean_name` y `synonym`.
2. **ChEMBL REST API (Bioactividades y Blancos)**:
   - Cliente REST con caché local persistente en disco (`api_cache`).
   - Filtrado estricto: mediciones exactas $IC_{50}$ y $K_i$ expresadas en nM, limitadas a proteínas humanas individuales (`SINGLE PROTEIN`, organismo *Homo sapiens*, con identificador UniProt unívoco).
   - Pre-caché de alta velocidad para la especie modelo de referencia (*Curcuma longa* / curcumina) que garantiza tiempos de respuesta en frío sub-segundo (< 0.3 s).
3. **Reactome Analysis & Content Services (Rutas Biológicas)**:
   - Envío de listas de identificadores UniProt para análisis de sobre-representación estadística (ORA).
   - Normalización automática de vocabulario de procesos biológicos en español ("inflamación" $\to$ "inflammation", "apoptosis" $\to$ "programmed cell death").

---

## 3. Instrucciones de Instalación y Ejecución

### Requisitos del Sistema
- Python 3.10 o superior (compatible con 3.11 y 3.12).
- Sistema operativo: Windows, macOS o Linux.

### Paso 1: Clonar el repositorio y preparar el entorno
```bash
# Clonar o ubicarse en la raíz del proyecto
cd FPPB_Project

# Crear y activar un entorno virtual (recomendado)
python -m venv venv

# En Windows:
venv\Scripts\activate
# En Linux / macOS:
# source venv/bin/activate

# Instalar dependencias verificadas
pip install -r requirements.txt
```

### Paso 2: Construir el índice de datos locales

La base `data/natural_products.db` **no** se versiona; se construye con el script de
preparación. Hay dos modos:

**(a) Índice completo (recomendado para uso real):**
```bash
python scripts/prepare_data.py --download
```
Descarga los volcados de LOTUS (Zenodo) y COCONUT, los ingiere y verifica el índice.
Requiere acceso de red a Zenodo y al bucket de COCONUT. Si los volcados faltan y no se
pasa `--download`, el script **falla de forma explícita** (no construye una base parcial
en silencio).

**(b) Índice de demostración (solo *Curcuma longa*):**
```bash
python scripts/prepare_data.py --demo
```
Construye un índice mínimo a partir del piloto real en `piloto_curcuma/`. Las demás
especies semilla quedan reconocidas pero **sin datos** (estado honesto: Puntaje 0). La
app muestra un aviso de "modo demostración".

Opcional, para traducir nombres de rutas de Reactome al español (capa asistida):
```bash
python scripts/build_pathways_es.py        # genera data/pathways_es.json
```

Comprobación rápida del índice construido:
```bash
python scripts/smoke_test_index.py
```

### Paso 3: Iniciar la aplicación web (Comando único)
```bash
streamlit run app/main.py
```
La aplicación abrirá automáticamente la interfaz web en su navegador predeterminado (típicamente en `http://localhost:8501`).

---

## 4. Modos de Búsqueda y Exploración

El aplicativo cuenta con tres pestañas especializadas orientadas a facilitar la exploración tanto para estudiantes y docentes como para investigadores fitoquímicos:

> **Nota sobre la interfaz (v1.1).** Los buscadores inician **vacíos** con texto guía;
> al escribir (desde 2 caracteres) aparecen **sugerencias de autocompletado** tomadas del
> índice real, de modo que elegir una sugerencia nunca lleva a un callejón sin datos. Se
> retiraron los botones de ejemplo y el botón de "identificación por foto".

### Modo 1: Búsqueda por Planta (Exploración Fitoquímica Completa)
- **Entrada amigable con autocompletado:** Acepta nombres científicos en latín con o sin autoría botánica (ej. *"Curcuma longa L."*, *"Curcuma domestica"*), variantes con errores tipográficos y nombres vernáculos en español e inglés. Las sugerencias muestran familia y número de compuestos disponibles.
- **Tarjeta taxonómica de confirmación:** Presenta el nombre científico aceptado, familia y nombres comunes. (No se muestran fotografías: las URLs fijas anteriores podían corresponder a otra especie; una futura versión puede traerlas de GBIF en tiempo de ejecución con atribución.)
- **Estados vacíos honestos:** nombre no reconocido; planta reconocida pero sin compuestos en el índice (Puntaje 0 y el recordatorio "sin datos no significa sin efecto"); o compuestos hallados sin coincidencia en ChEMBL.
- **Embudo de datos interactivo:** Muestra la reducción progresiva desde registros crudos hasta vías enriquecidas.
- **Tabla de metabolitos secundarios:** Ordenada por número de referencias bibliográficas de soporte, indicando coincidencia en ChEMBL, propiedades de similitud farmacológica (Regla de Lipinski, QED) y número de blancos proteicos.
- **Grafo de red tripartito:** Visualización interactiva Planta $\to$ Moléculas $\to$ Blancos Proteicos con detección de dominancia.
- **Vías biológicas de Reactome:** Gráfico de barras horizontales ordenado por significancia estadística ($-\log_{10} \text{FDR}$).
- **Desglose del Puntaje de Cobertura de Datos:** Evaluación de los 5 componentes metodológicos.

### Modo 2: Búsqueda por Molécula (Fitoquímica Inversa)
- **Autodetección inteligente de formato:** Reconoce nombre o sinónimo, estructura SMILES (**validada y convertida a InChIKey con RDKit**), InChIKey completa (`VFLDPWHFBUODDF-FCXRPNKRSA-N`), esqueleto de primer bloque (`VFLDPWHFBUODDF`) o identificador ChEMBL (`CHEMBL140`). Las estructuras SMILES ahora sí se resuelven (antes se detectaban pero no se convertían).
- **Visualizaciones primero, tablas después:** gráficos de plantas fuente, de potencia por blanco (una marca por medición, sin promediar réplicas) y de rutas; las tablas completas quedan en un desplegable "Ver datos".
- **Renderizado estructural 2D:** Dibuja el diagrama químico vectorial nítido (SVG) mediante RDKit.
- **Especies vegetales que la contienen:** Consulta reversa en LOTUS y COCONUT agrupando por variantes estereoquímicas.
- **Perfil de afinidad proteica y rutas:** Lista de dianas humanas con mediciones normalizadas y vías de Reactome vinculadas.

### Modo 3: Búsqueda por Proteína o Proceso Biológico
- **Sub-modo Proteína:** Búsqueda por símbolo genético oficial (ej. `PTGS2`, `EGFR`, `TNF`, `ESR1`) o nombre descriptivo (*"Prostaglandin G/H synthase 2"*).
- **Sub-modo Proceso Biológico:** Búsqueda de vías de Reactome mediante términos en español o inglés (*"inflamación"*, *"apoptosis"*, *"ciclo celular"*). Si el término es una **enfermedad o condición clínica** (p. ej. "migraña"), la herramienta responde con honestidad que busca procesos biológicos, no enfermedades, y ofrece rutas de nombre cercano en vez de inventar un vínculo. Del proceso se recorre el pipeline real: ruta → participantes → blancos ChEMBL → moléculas → plantas del índice.
- **Filtro botánico:** Conmutador (*toggle*) para mostrar *"Solo moléculas con planta fuente reportada"*, excluyendo compuestos puramente sintéticos de laboratorio.
- **Control de potencia interactivo:** Deslizador dinámico de afinidad mínima ($p\text{ChEMBL} \ge 6.0$, equivalente a $IC_{50} \le 1\,\mu\text{M}$) para aislar moduladores moleculares de alta potencia.

---

## 5. El Puntaje de Cobertura de Datos (*Data Coverage Score*)

Para responder cuantitativamente a la pregunta académica *"¿Qué tan completa es la evidencia científica disponible para esta planta?"*, se formuló el **Puntaje de Cobertura de Datos** ($0 - 100$ puntos), estructurado en 5 componentes que siguen el embudo de integración:

$$\text{Puntaje} = 100 \times \left( 0.10\,A + 0.20\,B_w + 0.30\,C_w + 0.15\,D + 0.25\,E \right)$$

| Componente | Qué Mide | Fórmula de Cálculo | Ponderación |
|---|---|---|---|
| **A. Compuestos Reportados** | Grado de caracterización fitoquímica básica de la especie | $\min\left(1.0, \frac{\log_{10}(1+N)}{\log_{10}(101)}\right)$ con $N$ = estructuras químicas distintas | 10% |
| **B. Cobertura ChEMBL Ponderada ($B_w$)** | Fracción de fitoquímica evaluable en repositorios bioactivos | $\frac{\sum \text{referencias de compuestos con coincidencia ChEMBL}}{\sum \text{referencias totales de la planta}}$ | 20% |
| **C. Blancos Proteicos Medidos ($C_w$)** | Fracción de fitoquímica con ensayos cuantitativos sobre proteínas humanas | $\frac{\sum \text{referencias de compuestos con } \ge 1 \text{ medición } IC_{50}/K_i}{\sum \text{referencias totales de la planta}}$ | 30% |
| **D. Mapeo en Reactome** | Proporción de blancos proteicos humanos reconocidos en rutas funcionales | $\frac{\text{Blancos con UniProt en Reactome}}{\text{Total de blancos proteicos de la planta}}$ | 15% |
| **E. Profundidad de Evidencia** | Robustez y replicación experimental de las bioactividades | $\frac{\text{Blancos con } \ge 2 \text{ mediciones de actividad}}{\text{Total de blancos proteicos de la planta}}$ | 25% |

### Caso de Validación Modelo: *Curcuma longa* (Cúrcuma)
En la especie de referencia extensamente estudiada:
- $N = 169$ estructuras distintas ($239$ registros) $\implies A = 1.00$
- Cobertura de ChEMBL ponderada por citas $\implies B_w = 0.58$
- Cobertura de blancos proteicos ponderada $\implies C_w = 0.31$
- Reconocimiento de dianas en Reactome ($132/140$) $\implies D = 0.94$
- Profundidad de bioactividades replicadas $\implies E = 0.59$

$$\text{Puntaje}(Curcuma) = 100 \times (0.10\cdot 1.00 + 0.20\cdot 0.58 + 0.30\cdot 0.31 + 0.15\cdot 0.94 + 0.25\cdot 0.59) = \mathbf{60.0\,/\,100}$$

*Interpretación:* Incluso en una planta modelo de renombre mundial como la cúrcuma, el 86% de sus metabolitos secundarios carecen de ensayos cuantitativos sobre proteínas humanas. El puntaje de 60 refleja con realismo que existe una cobertura sólida de los compuestos principales, pero una gran brecha en el metaboloma secundario.

---

## 6. Evaluación y Selección de la Planta Poco Estudiada

El requisito R6 pide validar la plataforma con una planta bien estudiada y otra poco
estudiada, **usando datos reales**. La versión v1 incluía una tabla con un puntaje de
29.2 para *Smallanthus sonchifolius* (Yacón) calculado a partir de **4 compuestos
escritos a mano**, no reales. Esas filas fabricadas se eliminaron (ver la revisión).

Por tanto, **la selección definitiva de la planta poco estudiada queda pendiente** hasta
construir el índice completo (`python scripts/prepare_data.py --download`). En el índice
de demostración, las especies candidatas (*Smallanthus sonchifolius*, *Petiveria
alliacea*, *Dysphania ambrosioides*) aparecen como **organismos reconocidos sin datos**
(Puntaje 0), que es el estado honesto previsto por el diseño.

Procedimiento reproducible una vez ingeridos los datos reales:
```bash
python scripts/prepare_data.py --download
python scripts/smoke_test_index.py   # reporta compuestos por especie
```
Con esos números reales se actualizará esta tabla, `AGENTS.md` y
`app/tests/test_under_studied_plant.py`.

---

## 7. Honestidad Científica y Sesgos Biológicos Visibles

Uno de los pilares metodológicos del proyecto es no ocultar las limitaciones intrínsecas de los datos de laboratorio abiertos:

1. **Aviso Obligatorio de Evidencia Preclínica:**  
   Todas las pantallas de resultados incluyen una advertencia visible y explícita:  
   > *Los resultados presentados corresponden a evidencia molecular preclínica (ensayos in vitro e in silico de laboratorio). No constituyen evidencia de eficacia clínica en humanos ni recomendación médica bajo ninguna circunstancia. Ninguna pantalla afirma que una planta cure o trate enfermedad alguna.*
2. **Alerta de Dominancia por una Sola Molécula:**
   El aplicativo detecta cuando un único compuesto aporta $\ge 40\%$ de los blancos medidos de la planta y despliega una alerta ("Aviso de dominancia") con el porcentaje real calculado al vuelo. Por ejemplo, en *Curcuma longa* la curcumina concentra la mayoría de las dianas; el porcentaje exacto lo computa el sistema sobre los datos cargados, no un valor fijo escrito en el código.
3. **Sesgo por Paneles de Ensayo (Anhidrasa Carbónica):**  
   Artículos de tamizaje químico que prueban colecciones completas de isoformas de anhidrasa carbónica (CA I a CA XIV) inflan artificialmente el enriquecimiento estadístico en Reactome con valores de significancia anómalos ($\text{FDR} \approx 10^{-13}$). La plataforma incorpora una advertencia contextual sobre este artefacto y ofrece filtros de afinidad estricta ($p\text{ChEMBL} \ge 6.0$) para mitigar su efecto.
4. **Alerta de Afinidades Extremas:**  
   Mediciones sub-nanomolares excepcionales ($p\text{ChEMBL} \ge 9.0$, ej. afinidad reportada de curcumina frente a precursor amiloide $\beta$ con $p\text{ChEMBL} = 9.68 \approx 0.2\,\text{nM}$) se señalan con enlaces directos al identificador del ensayo en ChEMBL para su verificación por el investigador.
5. **Agrupación por Esqueleto Químico (Bloque 1 de InChIKey):**  
   Para resolver redundancias y rescatar variantes estereoquímicas o tautoméricas entre LOTUS y ChEMBL, la búsqueda agrupa estructuras por los primeros 14 caracteres del InChIKey. El usuario es notificado de que esta agrupación consolida enantiómeros y estereoisómeros.
6. **Nombres de rutas en español (traducción asistida):**
   Reactome publica los nombres solo en inglés y R2 prohíbe servicios externos en tiempo de ejecución, por lo que la traducción se genera en tiempo de construcción (`scripts/build_pathways_es.py` → `data/pathways_es.json`) y se marca como "traducción asistida". El nombre original en inglés y el `stId` se conservan y aparecen en el detalle y en las exportaciones. El sesgo del panel de anhidrasa carbónica se detecta por `stId` (R-HSA-1475029), de modo que la alerta sigue funcionando tras traducir.

---

## 8. Verificación y Suite de Pruebas Automatizadas

El proyecto cuenta con una cobertura integral de pruebas automatizadas construida con `pytest`, que valida desde la integridad de índices y tolerancia a errores hasta la reproducción exacta de los datos piloto y el rendimiento temporal:

```bash
# Suite completa sin red (rápida)
python -m pytest app/tests/ -m "not network"

# Incluir las pruebas que consultan ChEMBL / Reactome / GBIF
python -m pytest app/tests/
```

### Enfoque de pruebas (reescrito)
Las pruebas ahora **importan y ejecutan las funciones reales de la app** y corren
`app/main.py` mediante `AppTest`, en vez de validar implementaciones de referencia
copiadas dentro de los propios tests. Puntos clave:
- Una **compuerta de honestidad** (`test_honesty_gate.py`) falla si reaparece contenido
  fijo/fabricado o ramas que tratan de forma especial a una entidad del piloto
  (CHEMBL140, VFLDPWHFBUODDF, etc.) dentro de `app/components` o `app/core`.
- Las pruebas que tocan red llevan la marca `network` (desactívelas con `-m "not network"`).
- Un índice en modo demostración no se reporta como validación completa: las pruebas de
  planta poco estudiada verifican el **estado vacío honesto**, no un puntaje fabricado.

Verificación de compilación:
```bash
python -m py_compile app/main.py scripts/*.py app/core/*.py app/components/*.py
```

---

## 9. Formatos de Exportación de Resultados

En cualquiera de los tres modos de búsqueda, el usuario puede descargar los resultados en formatos estructurados estándar para su posterior procesamiento en herramientas bioinformáticas (R, Cytoscape, Python):

- **CSV:** Tabla delimitada por comas con identificadores estándar (`inchikey`, `chembl_id`, `uniprot`, `target_name`, `standard_type`, `valor_nM`, `pchembl`, `n_refs`).
- **JSON:** Estructura jerárquica con metadatos de la consulta, fecha de análisis, puntuación de cobertura desglosada y listas completas de entidades con sus enlaces URL a ChEMBL y Reactome.

---

*Desarrollado con rigor científico, transparencia biomédica y pasión por la biodiversidad fitoquímica.*
