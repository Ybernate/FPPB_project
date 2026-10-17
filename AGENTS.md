# Reglas del Proyecto: Conoce tu planta (FPPB)

Estas reglas aplican a todo el código y documentación dentro de `FPPB_Project`:

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

5. **Verificación antes de cerrar cambios:**
   - Ejecuta `python -m pytest app/tests/ -v` y verifica que las métricas de referencia de *Curcuma longa* (Puntaje 60.0/100) y *Smallanthus sonchifolius* (Yacón, Puntaje 29.2/100) se mantengan íntegras.
