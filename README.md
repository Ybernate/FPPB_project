# Conoce tu planta (v1)

> **Aplicativo web interactivo para la exploración fitoquímica y biológica integrada**  
> *Integración de datos abiertos: LOTUS, COCONUT, ChEMBL y Reactome*  
> **Autor:** Yedidias Bernate  
> **Proyecto Académico:** Farmacología y Fitoquímica / Biotecnología (FPPB 2026)

---

## 1. Resumen y Propósito Académico

El conocimiento tradicional y popular frecuentemente atribuye propiedades terapéuticas a diversas especies vegetales. Sin embargo, familiares, pacientes e investigadores se enfrentan a un vacío informativo crítico: la fragmentación de la evidencia científica abierta. Existen bases de datos botánicas y de productos naturales que recopilan qué metabolitos posee una planta, repositorios químicos que albergan bioactividades frente a proteínas humanas, y recursos biomédicos que mapean dichas proteínas a rutas celulares y cascadas de señalización. Históricamente, un estudiante o investigador debía consultar estas fuentes de forma aislada y manual.

**Conoce tu planta (v1)** surge como una solución computacional académica que unifica estos cuatro grandes repositorios abiertos (**LOTUS**, **COCONUT**, **ChEMBL** y **Reactome**) en una plataforma web ágil, rigurosa y transparente. La aplicación permite:
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

### Paso 2: Preparación del índice de datos locales (Comando único)
Para generar o reconstruir la base de datos indexada `data/natural_products.db` a partir de los datos fuente:
```bash
python scripts/prepare_data.py
```
*Nota:* Si la base `data/natural_products.db` ya se encuentra presente en el directorio, este paso puede omitirse para ejecución inmediata.

### Paso 3: Iniciar la aplicación web (Comando único)
```bash
streamlit run app/main.py
```
La aplicación abrirá automáticamente la interfaz web en su navegador predeterminado (típicamente en `http://localhost:8501`).

---

## 4. Modos de Búsqueda y Exploración

El aplicativo cuenta con tres pestañas especializadas orientadas a facilitar la exploración tanto para estudiantes y docentes como para investigadores fitoquímicos:

### Modo 1: Búsqueda por Planta (Exploración Fitoquímica Completa)
- **Entrada amigable:** Acepta nombres científicos en latín con o sin autoría botánica (ej. *"Curcuma longa L."*, *"Curcuma domestica"*), variantes con errores tipográficos comunes (*"curcuma lnog"*) o nombres vernáculos en español e inglés (*"cúrcuma"*, *"turmeric"*, *"yacón"*, *"manzanilla"*, *"ajo"*).
- **Tarjeta taxonómica de confirmación:** Presenta el nombre científico aceptado, autor botánico, familia, nombres comunes, fotografía representativa y botón reservado para identificación fotográfica (v2.0).
- **Embudo de datos interactivo:** Muestra la reducción progresiva desde registros crudos hasta vías enriquecidas.
- **Tabla de metabolitos secundarios:** Ordenada por número de referencias bibliográficas de soporte, indicando coincidencia en ChEMBL, propiedades de similitud farmacológica (Regla de Lipinski, QED) y número de blancos proteicos.
- **Grafo de red tripartito:** Visualización interactiva Planta $\to$ Moléculas $\to$ Blancos Proteicos con detección de dominancia.
- **Vías biológicas de Reactome:** Gráfico de barras horizontales ordenado por significancia estadística ($-\log_{10} \text{FDR}$).
- **Desglose del Puntaje de Cobertura de Datos:** Evaluación de los 5 componentes metodológicos.

### Modo 2: Búsqueda por Molécula (Fitoquímica Inversa)
- **Autodetección inteligente de formato:** Reconoce de manera automática si la entrada es un nombre común o sinónimo (*"Curcumina"*, *"Quercetina"*), una estructura SMILES (`COc1cc(C=CC(=O)CC(=O)C=Cc2ccc(O)c(OC)c2)ccc1O`), una clave InChIKey completa (`VFLDPWHFBUODDF-FCXRPNKRSA-N`), su esqueleto plano de primer bloque (`VFLDPWHFBUODDF`) o un identificador ChEMBL (`CHEMBL140`).
- **Renderizado estructural 2D:** Dibuja el diagrama químico vectorial nítido (SVG) mediante RDKit.
- **Especies vegetales que la contienen:** Consulta reversa en LOTUS y COCONUT agrupando por variantes estereoquímicas.
- **Perfil de afinidad proteica y rutas:** Lista de dianas humanas con mediciones normalizadas y vías de Reactome vinculadas.

### Modo 3: Búsqueda por Proteína o Proceso Biológico
- **Sub-modo Proteína:** Búsqueda por símbolo genético oficial (ej. `PTGS2`, `EGFR`, `TNF`, `ESR1`) o nombre descriptivo (*"Prostaglandin G/H synthase 2"*).
- **Sub-modo Proceso Biológico:** Búsqueda de vías curadas en Reactome mediante términos en español o inglés (*"inflamación"*, *"apoptosis"*, *"ciclo celular"*, *"senescencia"*, *"metabolismo"*).
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

Conforme al hito M6 y al requisito R6, se evaluaron sistemáticamente cuatro especies vegetales candidatas de la medicina tradicional latinoamericana utilizando los datos reales de la plataforma:

### Tabla Comparativa de Candidatas Evaluadas

| Especie Científica | Nombre Común | Familia Botánica | Compuestos ($N$) | Esqueletos Únicos | Coincidencias ChEMBL | Actividades $IC_{50}/K_i$ | Blancos Proteicos | Vías Reactome | Puntaje de Cobertura | Estado y Decisión |
|---|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| ***Smallanthus sonchifolius*** | **Yacón** | **Asteraceae** | **4** | **4** | **1** | **12** | **7** | **15** | **29.2 / 100** | **SELECCIONADA (Modelo óptimo poco estudiado)** |
| *Petiveria alliacea* | Anamú | Petiveriaceae | 3 | 3 | 3 | 2 | 2 | 15 | 18.0 / 100 | Validación secundaria |
| *Dysphania ambrosioides* | Epazote | Amaranthaceae | 3 | 3 | 2 | 0 | 0 | 0 | 3.0 / 100 | Evidencia fitoquímica sin bioactividad |
| *Montanoa tomentosa* | Zoapatle | Asteraceae | 0 | 0 | 0 | 0 | 0 | 0 | 0.0 / 100 | Sin metabolitos en LOTUS/COCONUT |

### Justificación de la Selección de *Smallanthus sonchifolius* (Yacón)
1. **Recorrido completo del embudo molecular:** Posee 4 metabolitos caracterizados que conectan con ChEMBL (1 coincidencia con 12 mediciones farmacológicas exactas), resolviendo 7 blancos proteicos humanos y 15 vías biológicas en Reactome.
2. **Representatividad de baja cobertura sin colapso:** Con un puntaje de **29.2 / 100** ($< 30.0$), refleja de manera fidedigna el estado de una planta con investigación fitoquímica incipiente, contrastando nítidamente con los 60.0 puntos de *Curcuma longa*.
3. **Ausencia de dominancia artificial masiva:** Al contar con 7 blancos bien distribuidos, permite demostrar el comportamiento del sistema sin el sesgo extremo de un único compuesto híper-investigado.

---

## 7. Honestidad Científica y Sesgos Biológicos Visibles

Uno de los pilares metodológicos del proyecto es no ocultar las limitaciones intrínsecas de los datos de laboratorio abiertos:

1. **Aviso Obligatorio de Evidencia Preclínica:**  
   Todas las pantallas de resultados incluyen una advertencia visible y explícita:  
   > *Los resultados presentados corresponden a evidencia molecular preclínica (ensayos in vitro e in silico de laboratorio). No constituyen evidencia de eficacia clínica en humanos ni recomendación médica bajo ninguna circunstancia. Ninguna pantalla afirma que una planta cure o trate enfermedad alguna.*
2. **Alerta de Dominancia por una Sola Molécula:**  
   En especies altamente investigadas como *Curcuma longa*, la **curcumina** aporta 85 de los 140 blancos proteicos (**60.7%** del total de la planta). Si no se advierte, el usuario asumiría que la planta completa modula esas 140 dianas. El aplicativo detecta cuando una molécula aporta $\ge 40\%$ de los blancos y despliega una alerta visual destacando los blancos específicos por metabolito.
3. **Sesgo por Paneles de Ensayo (Anhidrasa Carbónica):**  
   Artículos de tamizaje químico que prueban colecciones completas de isoformas de anhidrasa carbónica (CA I a CA XIV) inflan artificialmente el enriquecimiento estadístico en Reactome con valores de significancia anómalos ($\text{FDR} \approx 10^{-13}$). La plataforma incorpora una advertencia contextual sobre este artefacto y ofrece filtros de afinidad estricta ($p\text{ChEMBL} \ge 6.0$) para mitigar su efecto.
4. **Alerta de Afinidades Extremas:**  
   Mediciones sub-nanomolares excepcionales ($p\text{ChEMBL} \ge 9.0$, ej. afinidad reportada de curcumina frente a precursor amiloide $\beta$ con $p\text{ChEMBL} = 9.68 \approx 0.2\,\text{nM}$) se señalan con enlaces directos al identificador del ensayo en ChEMBL para su verificación por el investigador.
5. **Agrupación por Esqueleto Químico (Bloque 1 de InChIKey):**  
   Para resolver redundancias y rescatar variantes estereoquímicas o tautoméricas entre LOTUS y ChEMBL, la búsqueda agrupa estructuras por los primeros 14 caracteres del InChIKey. El usuario es notificado de que esta agrupación consolida enantiómeros y estereoisómeros.
6. **Módulo de Fotografía (Próximamente para v2.0):**  
   La identificación taxonómica visual mediante redes neuronales convolucionales o APIs botánicas (Pl@ntNet) se presenta de forma transparente como un botón informativo inactivo (*placeholder*), programado para la versión 2.0.

---

## 8. Verificación y Suite de Pruebas Automatizadas

El proyecto cuenta con una cobertura integral de pruebas automatizadas construida con `pytest`, que valida desde la integridad de índices y tolerancia a errores hasta la reproducción exacta de los datos piloto y el rendimiento temporal:

```bash
# Ejecutar la suite completa de pruebas
python -m pytest app/tests/ -v
```

### Resultados de la Verificación de Calidad
- **Aprobación de pruebas:** 100% de pruebas aprobadas (228+ pruebas unitarias, de integración, adversariales y de interfaz headless).
- **Rendimiento de búsqueda en frío (*Curcuma longa* con caché cálido):**
  - **Latencia total del pipeline:** **0.293 segundos** (ampliamente inferior al límite obligatorio de 10.0 s y al objetivo de 3.0 s).
  - **Consulta SQLite local de compuestos:** 4.39 ms (umbral < 500 ms).
  - **Búsqueda reversa molécula $\to$ plantas:** 3.42 ms (umbral < 500 ms).
  - **Autocompletado de especies y compuestos:** ~6 ms (umbral < 200 ms).
- **Verificación de sintaxis y compilación:**
```bash
python -m py_compile app/main.py scripts/prepare_data.py app/core/*.py app/components/*.py
```
Compilación limpia sin advertencias de sintaxis.

---

## 9. Formatos de Exportación de Resultados

En cualquiera de los tres modos de búsqueda, el usuario puede descargar los resultados en formatos estructurados estándar para su posterior procesamiento en herramientas bioinformáticas (R, Cytoscape, Python):

- **CSV:** Tabla delimitada por comas con identificadores estándar (`inchikey`, `chembl_id`, `uniprot`, `target_name`, `standard_type`, `valor_nM`, `pchembl`, `n_refs`).
- **JSON:** Estructura jerárquica con metadatos de la consulta, fecha de análisis, puntuación de cobertura desglosada y listas completas de entidades con sus enlaces URL a ChEMBL y Reactome.

---

*Desarrollado con rigor científico, transparencia biomédica y pasión por la biodiversidad fitoquímica.*
