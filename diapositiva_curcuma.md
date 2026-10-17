# Diapositiva piloto: *Curcuma longa* (datos reales, 12-oct-2026)

Corrí el flujo completo con las APIs públicas: LOTUS (vía Wikidata) → ChEMBL → Reactome. Los scripts y los CSV están en `FPPB_Project/piloto_curcuma/` (`piloto.py`, `analisis_extra.py`, `compuestos.csv`, `actividades.csv`, `rutas.csv`). Las cifras cambiarán con las actualizaciones de las bases, así que repite `piloto.py` antes de presentar.

## 1. Resultados verificados

| Etapa | Resultado |
|---|---|
| **LOTUS: compuestos con estructura** | 239 registros, que corresponden a 169 estructuras distintas (primer bloque del InChIKey). El resto son variantes de estereoquímica o tautómeros. |
| **Coincidencia con ChEMBL (InChIKey completo)** | 110 de 239 (46 %) |
| **Coincidencia relajada (primer bloque)** | 42 registros más tienen una variante que sí está en ChEMBL. Sin duplicados por estereoquímica, el cruce subiría, pero habría que confirmarlo. |
| **Compuestos con ≥1 medición sobre una proteína humana individual** | 34 de 239 (14 %) |
| **Actividades IC50/Ki (en nM, humanas)** | 1.132 en total, 459 sobre proteínas individuales |
| **Blancos proteicos únicos** | 140 |
| **Blancos reconocidos por Reactome** | 132 de 140 (8 no se encontraron) |
| **Mediciones con pChEMBL** | 339 de 459 |

### Compuestos más reportados (referencias en LOTUS)
| Compuesto | Refs. | ChEMBL | Blancos |
|---|---|---|---|
| curcumina | 55 | CHEMBL140 | 85 |
| bisdemetoxicurcumina | 26 | CHEMBL105350 | 6 |
| desmetoxicurcumina | 20 | CHEMBL105360 | 4 |
| cúrcuma (entrada de mezcla) | 17 | CHEMBL3187799 | 0 |
| (+)-(S)-ar-turmerona | 10 | CHEMBL1668333 | 2 |

### Blancos de la curcumina con mejor afinidad medida
Son mediciones exactas (relación "=") con pChEMBL. De 85 blancos, 73 tienen este tipo de medición.

| Blanco | UniProt | pChEMBL máx. | Mediciones |
|---|---|---|---|
| Proteína precursora de amiloide β | P05067 | 9,68 | 38 |
| DYRK1A | Q92630 | 8,60 | 4 |
| Lactoilglutatión liasa | Q04760 | 8,30 | 3 |
| Factor tisular | P13726 | 7,88 | 3 |
| Prostaglandina E sintasa | O14684 | 6,70 | 5 |

### Rutas de Reactome más enriquecidas (todos los blancos)
Reversible hydration of carbon dioxide (12/17, FDR 1,1·10⁻¹³); Cellular response to hypoxia (8/73); STAT3 nuclear events downstream of ALK signaling (5/19); Adipogenesis (10/147); Xenobiotics (7/72); Biosynthesis of maresins (5/29).

## 2. Lo que encontré (importante para la presentación)

1. **Responde tu duda anterior:** LOTUS llama al compuesto principal **"curcumin"**, no "diferuloylmethane". El nombre "tetrahydrodiferuloylmethane" sí aparece, pero es otro compuesto (la tetrahidrocurcumina). Por eso buscar por nombre fallaba, y por eso el cruce se hace por estructura.
2. **Una sola molécula domina:** la curcumina aporta 85 de los 140 blancos (61 %) y 196 de las 459 actividades. Los resultados de "la planta" son, en gran parte, resultados de la curcumina. La app debe mostrarlo (blancos por compuesto) y no presentarlo como un perfil de la planta entera.
3. **Duplicados por estereoquímica:** 239 registros son solo 169 estructuras. Por ejemplo, la desmetoxicurcumina aparece dos veces, y solo una variante coincide en ChEMBL. Agrupar por primer bloque del InChIKey es una mejora necesaria, y habrá que decidir cuándo fusionar enantiómeros.
4. **Sesgo de los ensayos:** la ruta de anhidrasa carbónica (CA) sale arriba con FDR 10⁻¹³. Con un filtro de potencia (pChEMBL ≥ 6, relación "=": 54 actividades, 27 blancos, 14 compuestos) sigue siendo la primera, pero el FDR sube a 8,7·10⁻⁴. Mi hipótesis, sin comprobar en las fuentes, es que pocos artículos probaron familias enteras de isoformas, y eso infla la señal. Hay que mostrar el enriquecimiento con esta advertencia y ofrecer el filtro de potencia.
5. **Valores extremos:** un pChEMBL de 9,68 (aprox. 0,2 nM) para la curcumina frente a la proteína precursora de amiloide parece muy alto. No lo he revisado en el artículo de origen. La app puede enlazar a la fuente del ensayo.
6. **Cobertura realista:** solo 14 % de los compuestos tiene una medición sobre proteínas humanas. Es una planta muy estudiada, y aun así el 86 % de sus compuestos no tiene datos de blancos. Eso es lo que debe revelar el Puntaje.
7. **Dos grupos de resultados:** 54 blancos vienen solo de curcuminoides, 54 solo de otros compuestos y 32 de ambos.

## 3. Qué debe tener la diapositiva

**Título:** *Curcuma longa* en cifras: de la especie a las rutas.

**Elementos (de izquierda a derecha, o de arriba abajo):**
1. **Embudo de datos** con barras horizontales:
   - 239 registros en LOTUS (169 estructuras distintas)
   - 110 con coincidencia en ChEMBL
   - 34 con medición sobre proteínas humanas
   - 140 blancos únicos
   - 132 reconocidos por Reactome
2. **Mini-tabla:** top 5 de compuestos por referencias, con su número de blancos.
3. **Gráfico de barras:** top 5 de rutas de Reactome (barras con −log₁₀ FDR).
4. **Indicador del Puntaje de Cobertura:** 60/100 y sus 5 componentes.
5. **Una advertencia visible:** "Resultados de laboratorio. No es evidencia clínica ni consejo médico."
6. **Una nota de sesgo:** "La curcumina aporta 61 % de los blancos."
7. **Pie de fuente:** LOTUS (Wikidata), ChEMBL, Reactome, con la fecha de consulta.

**Qué decir (30–45 s):** "Para la cúrcuma, LOTUS reporta 239 compuestos. Solo 110 tienen coincidencia en ChEMBL y 34 tienen mediciones sobre proteínas humanas. Esos 34 compuestos dan 140 blancos, de los cuales la curcumina aporta la mayoría. El Puntaje resume esa cobertura en un número."

## 4. Propuesta de Puntaje de Cobertura de Datos

**Idea:** sigue el recorrido de los datos (embudo) y pesa cada compuesto por cuánto se ha reportado en la planta, de modo que los compuestos poco relevantes no distorsionen el resultado.

| Componente | Qué mide | Cálculo |
|---|---|---|
| **A. Compuestos reportados** | Cuánto se ha caracterizado la planta | min(1, log₁₀(1+N) / log₁₀(101)), con N = estructuras distintas |
| **B. Con coincidencia en ChEMBL** | Cobertura de bioactividad | Σ refs. de compuestos con match / Σ refs. totales |
| **C. Con blanco proteico humano medido** | Cobertura de blancos | Σ refs. de compuestos con ≥1 medición / Σ refs. totales |
| **D. Blancos reconocidos en Reactome** | Mapeo a rutas | Blancos encontrados / blancos totales |
| **E. Profundidad de evidencia** | Replicación de mediciones | Blancos con ≥2 mediciones / blancos totales |

**Fórmula:**

Puntaje = 100 × (0,10·A + 0,20·B + 0,30·C + 0,15·D + 0,25·E)

**Ejemplo con *Curcuma longa*:**
A = 1,00; B = 0,58; C = 0,31; D = 0,94; E = 0,59
→ 100 × (0,10 + 0,116 + 0,093 + 0,141 + 0,148) = **60**
(Sin ponderar por referencias: B = 0,46 y C = 0,14, y el puntaje sería 52.)

**Casos límite:** si una planta no tiene blancos, C, D y E valen 0 y el puntaje queda bajo (A y B pueden aportar hasta 30 puntos). Es el comportamiento deseado, pero hay que mostrar que la causa es "sin datos de blancos".

**Salida visual:** el número más el desglose por componente (barras). Los rangos "alta / media / baja" no deben fijarse todavía.

> [!WARNING]
> Los pesos (0,10/0,20/0,30/0,15/0,25) son mi propuesta, no un resultado validado. Con una sola planta no se puede decir si 60 es alto o bajo.
> Plan: calcular el puntaje para 5–10 plantas (incluida la poco estudiada) y definir los rangos con esa distribución. También es una oportunidad de validación para el proyecto.

> [!NOTE]
> El componente E usa "≥2 filas de actividad" como proxy de replicación. No garantiza mediciones independientes, porque varias filas pueden venir del mismo artículo. Mejora posible: contar documentos distintos de ChEMBL.

## 5. Limitaciones de esta verificación
- Probé una sola planta. Los números de otra planta serán distintos.
- Cuento "referencias" como artículos distintos citados en LOTUS (Wikidata). No es una medida de calidad.
- No usé COCONUT. Su API pide registro y llave; la ruta alternativa es la descarga masiva. Las cifras de arriba vienen solo de LOTUS.
- La consulta relajada por primer bloque en ChEMBL era demasiado lenta como filtro, así que agrupé localmente. No confirmé que las 42 variantes "rescatadas" tengan la misma estructura en ChEMBL.
- Mi hipótesis sobre el sesgo de las anhidrasas carbónicas es una inferencia, no un hecho comprobado.
