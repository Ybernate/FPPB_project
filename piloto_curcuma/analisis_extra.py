"""Analisis adicional del piloto:
 1) Cruce relajado por primer bloque del InChIKey (14 caracteres).
 2) Sesgo: blancos que vienen solo de metabolitos ubicuos vs curcuminoides.
 3) Enriquecimiento Reactome con filtro de potencia (pChEMBL >= 6, relacion '=').
 4) Puntaje de Cobertura de Datos propuesto.
"""
import csv, json, math, time
from collections import defaultdict
from piloto import get_json, CHEMBL, reactome, chembl_targets

comp = list(csv.DictReader(open('compuestos.csv', encoding='utf-8')))
acts = list(csv.DictReader(open('actividades.csv', encoding='utf-8')))

# ---- 1) agrupar por primer bloque del InChIKey (conectividad, sin estereoquimica)
by_fb = defaultdict(list)
for c in comp:
    by_fb[c['inchikey'].split('-')[0]].append(c)
n_blocks = len(by_fb)
dup_blocks = sum(1 for v in by_fb.values() if len(v) > 1)
rescued = [c for v in by_fb.values() if any(x['chembl_id'] for x in v)
           for c in v if not c['chembl_id']]
print(f"Compuestos LOTUS: {len(comp)} | estructuras distintas (1er bloque): {n_blocks} | bloques con variantes: {dup_blocks}")
print(f"Sin match exacto pero con variante estereoquimica que si esta en ChEMBL: {len(rescued)}")
for c in rescued[:8]:
    print('   ', c['nombre'][:50], c['inchikey'])

# ---- 2) sesgo por tipo de compuesto
curc_ids = {c['chembl_id'] for c in comp
            if c['chembl_id'] and ('urcumin' in (c['nombre'] + c['chembl_nombre']).lower()
                                   or 'diferuloylmethane' in c['nombre'].lower())}
targets_by = defaultdict(set)
for a in acts:
    targets_by[a['uniprot']].add(a['chembl_mol'])
only_curc = [u for u, ms in targets_by.items() if ms <= curc_ids]
only_other = [u for u, ms in targets_by.items() if not (ms & curc_ids)]
print(f"Blancos totales {len(targets_by)} | solo curcuminoides {len(only_curc)} | solo otros compuestos {len(only_other)} "
      f"| ambos {len(targets_by) - len(only_curc) - len(only_other)}")
n_mols_with_t = len({a['chembl_mol'] for a in acts})
print("Compuestos con >=1 actividad sobre proteina:", n_mols_with_t)

# ---- 3) enriquecimiento con filtro de potencia
pot = [a for a in acts if a['relacion'] == '=' and a['pchembl'] and float(a['pchembl']) >= 6]
pot_t = sorted({a['uniprot'] for a in pot})
print(f"Potentes (pChEMBL>=6, '='): {len(pot)} actividades, {len(pot_t)} blancos, {len({a['chembl_mol'] for a in pot})} compuestos")
paths, token, nf = reactome(pot_t)
print("Top rutas (filtro de potencia):")
for p in paths[:10]:
    print(f"  {p['ruta'][:55]:55} {p['entidades_encontradas']}/{p['entidades_total']} fdr={p['fdr']:.2e}")

# solo curcuminoides
cur_acts = [a for a in acts if a['chembl_mol'] in curc_ids]
cur_t = sorted({a['uniprot'] for a in cur_acts})
paths_c, _, _ = reactome(cur_t)
print(f"\nSolo curcuminoides: {len(cur_acts)} actividades, {len(cur_t)} blancos. Top rutas:")
for p in paths_c[:10]:
    print(f"  {p['ruta'][:55]:55} {p['entidades_encontradas']}/{p['entidades_total']} fdr={p['fdr']:.2e}")

# ---- 4) puntaje
N = len(comp)
w = [int(c['n_refs']) for c in comp]
matched = [bool(c['chembl_id']) for c in comp]
with_t = [int(c['n_blancos_proteina']) > 0 for c in comp]
A = min(1, math.log10(1 + N) / math.log10(1 + 100))
B = sum(matched) / N
C = sum(with_t) / N
Bw = sum(x for x, m in zip(w, matched) if m) / sum(w)
Cw = sum(x for x, m in zip(w, with_t) if m) / sum(w)
all_t = len(targets_by)
reactome_ok = 1 - (8 / all_t)  # 8 identificadores no encontrados (resumen.json)
depth = sum(1 for u, ms in targets_by.items()
            if sum(1 for a in acts if a['uniprot'] == u) >= 2) / all_t
print("\n--- Componentes ---")
print(f"A cantidad de compuestos reportados (N={N}): {A:.2f}")
print(f"B compuestos con match ChEMBL: {B:.2f} (ponderado por referencias {Bw:.2f})")
print(f"C compuestos con >=1 blanco proteico humano: {C:.2f} (ponderado {Cw:.2f})")
print(f"D blancos reconocidos por Reactome: {reactome_ok:.2f}")
print(f"E profundidad (blancos con >=2 mediciones): {depth:.2f}")
for name, ws in [("pesos A.10 B.20 C.30 D.15 E.25", (.10, .20, .30, .15, .25))]:
    s = 100 * (ws[0] * A + ws[1] * Bw + ws[2] * Cw + ws[3] * reactome_ok + ws[4] * depth)
    s_un = 100 * (ws[0] * A + ws[1] * B + ws[2] * C + ws[3] * reactome_ok + ws[4] * depth)
    print(f"Puntaje ({name}): ponderado por refs = {s:.0f} | sin ponderar = {s_un:.0f}")
