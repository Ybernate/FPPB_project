# Reglas del Proyecto: FitoEvidencia (FPPB)

Estas reglas aplican a todo el código y documentación dentro de `FPPB_Project`:

0. **Sin datos fabricados ni ramas por entidad del piloto:**
   - Prohibido escribir a mano compuestos, actividades, participantes de rutas,
     InChIKeys, DOIs o puntajes "de referencia" en el código de producción
     (`app/components`, `app/core`) o en `data/natural_products.db`. Los datos de demo
     provienen del piloto real (`piloto_curcuma/`) vía `scripts/prepare_data.py`.
   - Prohibido tratar de forma especial a una entidad concreta del piloto (p. ej.
     ramas `== "CHEMBL140"` / `== "VFLDPWHFBUODDF"`). Todo debe pasar por el mismo
     pipeline. `app/tests/test_honesty_gate.py` hace cumplir esto.
   - Los estados vacíos son honestos: nombre no reconocido; planta reconocida sin datos
     (Puntaje 0); o compuestos sin coincidencia en ChEMBL. Nunca ocultar un resultado vacío.

1. **Cruce Químico por Estructura (InChIKey Block 1):**
   - Nunca cruces compuestos entre LOTUS, COCONUT y ChEMBL usando nombres en texto libre.
   - Usa siempre el InChIKey completo para coincidencias exactas y el primer bloque del InChIKey (primeros 14 caracteres, `inchikey_block1`) para agrupar variantes estereoquímicas y tautómeros.

2. **Filtrado Estricto de Bioactividad en ChEMBL:**
   - Filtra exclusivamente blancos con `target_type == "SINGLE PROTEIN"`, organismo `Homo sapiens` y acceso UniProt válido (excluyendo líneas celulares, tejidos u organismos completos).
   - Usa mediciones cuantitativas normalizadas (`IC50`, `Ki` en `nM` y `pchembl_value`).

3. **Honestidad Científica y Visibilidad de Sesgos:**
   - Está prohibido incluir afirmaciones de eficacia clínica, curación o recomendación médica en la interfaz, reportes o documentación.
   - Toda pantalla de resultados debe incluir el aviso de evidencia preclínica molecular (`render_preclinical_disclaimer()`) y mantener activos los detectores de sesgo: dominancia por una sola molécula (>= 40% de blancos), inflación por paneles de ensayo (anhidrasa carbónica) y valores extremos (pChEMBL >= 9.0).

4. **Rendimiento e Índices Locales:**
   - No utilices consultas remotas en vivo para cruzar listas masivas de estructuras contra LOTUS o COCONUT ni filtros `startswith` remotos en ChEMBL.
   - Toda consulta de organismos, compuestos y sinónimos debe resolverse contra `data/natural_products.db` usando índices B-Tree (sin `SCAN TABLE`) y la caché en disco (`api_cache`) para ChEMBL y Reactome.

5. **Nombres de rutas en español:**
   - Traducir en tiempo de construcción (`scripts/build_pathways_es.py` → `data/pathways_es.json`), nunca con servicios externos en tiempo de ejecución (R2). Conservar el nombre original en inglés y el `stId`. Mantener intactos los símbolos de genes/proteínas y los nombres químicos.
   - Detectar el sesgo del panel de anhidrasa carbónica por `stId` (`R-HSA-1475029`), no por texto, para que siga funcionando tras traducir.

6. **Verificación antes de cerrar cambios:**
   - Ejecuta `python -m pytest app/tests/ -m "not network"` (y, con red, la suite completa).
   - No fijes puntajes "de referencia" para especies poco estudiadas: su validación (R6) requiere el índice completo (`--download`). Un índice de demostración no sustituye esa validación.
