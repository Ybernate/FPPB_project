# Flujo de presentación (10 min): aplicativo de evidencia molecular de plantas medicinales

**Audiencia:** profesor y compañeros de biología/biotecnología. Tono académico pero accesible.
**Entrada que se presenta:** nombre científico. La foto con Pl@ntNet solo se menciona como mejora futura.
**Visual del producto:** maqueta estática del panel con datos reales de *Curcuma longa* consultados a mano. No se promete demo en vivo.
**Tiempo total:** 9:30 de contenido, más 30 s de margen. Son 11 diapositivas, aproximadamente 1 por minuto.

| # | Diapositiva | Tiempo |
|---|---|---|
| 1 | Portada | 0:15 |
| 2 | Origen y problema | 0:50 |
| 3 | Pregunta y solución | 0:45 |
| 4 | Entrada → procesamiento → salida | 0:40 |
| 5 | Las 4 bases de datos | 1:45 |
| 6 | Cómo funciona la integración | 1:15 |
| 7 | Salida: maqueta del panel | 1:15 |
| 8 | Ventajas | 0:40 |
| 9 | Áreas de oportunidad | 1:00 |
| 10 | Plan de 8 semanas y validación | 0:40 |
| 11 | Cierre | 0:25 |

---

## 1. Portada (0:15)
- Título completo del PDF, tu nombre y la materia.
- **Decir:** "Voy a presentar una herramienta para saber qué evidencia molecular abierta existe sobre una planta y dónde faltan datos."

## 2. Origen y problema (0:50)
- **Imagen:** una pregunta cotidiana, por ejemplo "¿Esta planta sirve para X?", con un signo de interrogación.
- **Decir:**
  - Familiares y amigos preguntan si una planta ayuda con una condición, y las respuestas son creencias o resultados de buscadores sin respaldo verificable.
  - Esa pregunta clínica necesita ensayos de eficacia, que estas bases no tienen.
  - Sí se puede responder una pregunta previa: qué se sabe a nivel molecular.
- **Mensaje clave:** el proyecto no dice si una planta cura; muestra qué se sabe y qué no.

## 3. Pregunta y solución (0:45)
- **Pregunta en grande:** "¿Qué evidencia molecular abierta existe sobre una planta, qué compuestos podrían actuar sobre qué rutas humanas y qué tan completa es la información?"
- **Solución en una frase:** un aplicativo web que reúne cuatro bases abiertas, cruza sus datos y calcula un Puntaje de Cobertura de Datos.
- **Dato de fondo:** la información está fragmentada. Unas bases dicen qué compuestos tiene una planta, otras qué hacen sobre proteínas, otras en qué rutas participan. Hoy hay que consultarlas una por una.

## 4. Entrada → procesamiento → salida (0:40)
Diagrama de tres bloques:
- **Entrada:** nombre científico de la planta (con validación y autocompletado).
- **Procesamiento:** cruce de LOTUS/COCONUT → ChEMBL → Reactome.
- **Salida:** panel y reporte descargable (PDF/CSV) con 4 componentes: compuestos, blancos con afinidades, rutas y Puntaje de Cobertura.
- **Nota para ti:** el profesor pidió claridad en qué entra y qué sale, no en cómo se programa. No menciones Python ni librerías.

## 5. Las 4 bases de datos (1:45)
Una diapositiva con 4 tarjetas, de unos 25 segundos cada una:

| Base | Qué es | Qué aporta al proyecto |
|---|---|---|
| **LOTUS** | Pares producto natural–organismo con referencia bibliográfica. Se consulta vía Wikidata. | Qué compuestos se han reportado en la especie. |
| **COCONUT** | Colección abierta (CC0) de más de 400 mil productos naturales con estructuras y propiedades. | Complementa a LOTUS con estructuras y metadatos. |
| **ChEMBL** | Base curada de moléculas bioactivas con mediciones (IC50, Ki) frente a proteínas. | Blancos humanos y afinidades; además propiedades de similitud farmacológica (peso, logP, Lipinski). |
| **Reactome** | Rutas biológicas humanas curadas, con servicio de análisis de enriquecimiento. | Rutas en las que participan los blancos encontrados. |

- **Frase puente:** "Cada base responde una parte de la pregunta; ninguna la responde sola."
- **Hecho verificado:** ChEMBL devuelve peso molecular, ALogP, aceptores y donadores de enlaces de hidrógeno, violaciones de la regla de Lipinski y QED en la misma consulta, así que no hay que calcularlos aparte.

## 6. Cómo funciona la integración (1:15)
Diagrama de flujo con el identificador que une cada paso:

```
Nombre científico
   │  (LOTUS vía Wikidata, COCONUT como complemento)
   ▼
Compuestos de la especie  ──►  InChIKey (identificador de estructura)
   │  (búsqueda en ChEMBL por InChIKey)
   ▼
ID de molécula en ChEMBL  ──►  Actividades IC50/Ki sobre proteínas humanas
   │  (ChEMBL: target → acceso UniProt)
   ▼
Lista de proteínas (UniProt)  ──►  Reactome (enriquecimiento)
   ▼
Rutas + Puntaje de Cobertura de Datos
```

- **Idea central:** la estructura química (InChIKey) es el puente entre las bases de productos naturales y ChEMBL, porque ChEMBL no se consulta por especie. ChEMBL entrega el acceso UniProt de cada proteína, que Reactome entiende.
- **Detalle técnico útil:** comparar el primer bloque del InChIKey (14 caracteres) evita fallos por diferencias de estereoquímica. Es una buena práctica que deberás confirmar con datos reales.
- **Puntaje de Cobertura de Datos:** combina cuántos compuestos se reportan, qué proporción tiene mediciones en ChEMBL y cuántos blancos y rutas resultan. Aclara que la fórmula y los pesos se definirán en el desarrollo.

## 7. Salida: maqueta del panel (1:15)
Maqueta estática (PowerPoint o Figma) con *Curcuma longa*. Datos que ya verifiqué en la API de ChEMBL:
- **Compuesto de ejemplo:** curcumina (CHEMBL140). Peso 368,39; ALogP 3,37; 6 aceptores y 2 donadores de H; 0 violaciones de Lipinski; QED 0,55.
- **Afinidad de ejemplo:** la prostaglandina G/H sintasa 2 (COX-2) tiene un IC50 de 11,06 µM (pChEMBL 4,96) para la curcumina. Es una sola medición recuperada, no un resultado de validación.
- Los otros paneles (rutas de Reactome y Puntaje) pueden ser maqueta con datos ilustrativos. **Rotúlalos como "ilustrativo"** o consúltalos a mano antes de la presentación.
- **Recorrido en voz alta (30 s):** "Aquí el usuario ve cuatro cosas: compuestos, blancos con afinidades, rutas y qué tan completa es la información."
- **Decir también:** "Esta es una maqueta; el aplicativo se construirá en las 8 semanas."

## 8. Ventajas (0:40)
- Ahorra consultar cuatro bases por separado.
- Todo es abierto y verificable (fuentes y referencias trazables).
- El Puntaje de Cobertura es el diferenciador: distingue "no tiene efecto" de "no se ha estudiado".
- Alcance realista para un proyecto individual: las bases tienen API o descarga abierta.
- Útil para estudiantes e investigadores como punto de partida de una búsqueda bibliográfica o de una hipótesis.

## 9. Áreas de oportunidad (1:00)
Preséntalas como "puntos en los que me enfocaré durante el desarrollo". Cada una lleva una línea de acción.

| Área de oportunidad | Qué haré |
|---|---|
| No todos los compuestos naturales están en ChEMBL | Hacer visible esa ausencia: alimenta el Puntaje de Cobertura. |
| ChEMBL mezcla proteínas con líneas celulares y otros objetivos | Filtrar a proteínas individuales humanas. |
| Unidades y tipos de medición heterogéneos | Normalizar a nM o usar pChEMBL. |
| Pocos blancos limitan el análisis de enriquecimiento | Reportar el número de blancos y advertir cuando sea bajo. |
| Nombres científicos con sinónimos | Validar y normalizar el nombre antes de consultar. |
| Dependencia de servicios externos y velocidad | Guardar consultas en caché y preparar plantas ejemplo. |
| Resultados de laboratorio no son eficacia clínica | Aviso permanente de que son hipótesis moleculares, no consejo médico. |

- **Opcional (mejora futura):** entrada por fotografía con Pl@ntNet, con paso de confirmación.

## 10. Plan de 8 semanas y validación (0:40)
Línea de tiempo simple:
- **Semanas 1–2:** consultas a las bases con una planta ejemplo y un puente de identificadores.
- **Semanas 3–4:** panel de compuestos y blancos con afinidades.
- **Semanas 5–6:** enriquecimiento en Reactome y Puntaje de Cobertura.
- **Semana 7:** reporte descargable y validación.
- **Semana 8:** pruebas y preparación de la presentación final.
- **Validación:** una planta muy estudiada (cúrcuma), para contrastar con la literatura, y una poco estudiada (por definir al revisar LOTUS), para comprobar que el puntaje muestre los vacíos.

## 11. Cierre (0:25)
- Recapitula en una frase: "Un solo lugar para ver qué se sabe, qué no se sabe y qué tan confiable es esa información sobre una planta".
- Aviso: son hipótesis moleculares, no consejo médico.
- Pregunta final: "¿Preguntas?"

---

## Preguntas probables y respuestas cortas
1. **¿Esto me dice si una planta sirve para una enfermedad?** No. Muestra la evidencia molecular y sus vacíos. Responder eficacia requiere estudios clínicos.
2. **¿Cómo se calcula el Puntaje?** Combina cuántos compuestos se reportan, qué proporción tiene mediciones en ChEMBL y cuántos blancos y rutas resultan. La fórmula y los pesos se definirán y documentarán durante el desarrollo.
3. **¿Y si la planta no tiene datos?** El resultado es un puntaje bajo y un mensaje de "evidencia insuficiente". Es un resultado válido.
4. **¿Por qué estas cuatro bases?** Cubren los eslabones planta → compuesto → proteína → ruta, y son abiertas y con acceso programático.
5. **¿Es factible en 8 semanas?** Sí, porque no hay que construir bases ni modelos; se consulta, se cruza y se visualiza.
6. **¿Cómo validas?** Con dos plantas, una muy estudiada y una poco estudiada.
7. **¿Quién lo usaría?** Estudiantes e investigadores de biología y farmacia como punto de partida. No lo he validado como mercado.

## Preparación
- Ensaya tres veces con cronómetro. Si pasas de 9:30, recorta primero la diapositiva 5 o la 9.
- Una idea por diapositiva y poco texto. Usa los diagramas de las diapositivas 4 y 6 como centro visual.
- Antes de presentar, repite a mano las consultas de la cúrcuma para confirmar los valores de la maqueta y rotula lo ilustrativo.
- Lleva el PDF del anteproyecto a mano por si piden detalle.
- Dos erratas del PDF entregado para corregir si presentas una versión nueva: en OBJETIVOS falta una palabra ("a partir del nombre científico de una planta y reúna…"), y en RESULTADOS dice "confirma la especie propuesta" aunque ya no hay foto que identificar.
