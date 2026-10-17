import csv, json, statistics
from collections import Counter

c = list(csv.DictReader(open('compuestos.csv', encoding='utf-8')))
print('total', len(c), '| sin nombre:', sum(1 for r in c if not r['nombre']),
      '| refs>0:', sum(1 for r in c if int(r['n_refs']) > 0),
      '| con SMILES:', sum(1 for r in c if r['smiles']))
print('\nTop 15 por referencias:')
for r in c[:15]:
    print(f"{r['nombre'][:34]:34} refs={r['n_refs']:>3} chembl={r['chembl_id']:12} blancos={r['n_blancos_proteina']}")
print('\ncon ChEMBL:', sum(1 for r in c if r['chembl_id']),
      '| con >=1 blanco proteina:', sum(1 for r in c if int(r['n_blancos_proteina']) > 0))
print('\nCurcuminoides / curcumina:')
for r in c:
    if 'urcumin' in r['nombre'] or 'urcumin' in r['chembl_nombre'].lower():
        print(f"{r['nombre'][:40]:40} refs={r['n_refs']} chembl={r['chembl_id']} {r['chembl_nombre']} blancos={r['n_blancos_proteina']}")

a = list(csv.DictReader(open('actividades.csv', encoding='utf-8')))
print('\nTop blancos por # actividades:')
for t, n in Counter(r['target'] for r in a).most_common(12):
    print(' ', n, t)
print('\nActividades por compuesto (top 8):')
mol = Counter(r['chembl_mol'] for r in a)
name = {r['chembl_id']: (r['nombre'] or r['chembl_nombre']) for r in c if r['chembl_id']}
for m, n in mol.most_common(8):
    print(' ', n, m, name.get(m, ''))
vals = [float(r['valor_nM']) for r in a if r['valor_nM']]
print('\nvalor_nM mediana', statistics.median(vals), 'min', min(vals), 'max', max(vals))
print('relaciones:', Counter(r['relacion'] for r in a))
print('con pChEMBL:', sum(1 for r in a if r['pchembl']), 'de', len(a))

print('\nRutas Reactome (top):')
for r in csv.DictReader(open('rutas.csv', encoding='utf-8')):
    print(f"{r['ruta'][:55]:55} {r['entidades_encontradas']}/{r['entidades_total']} fdr={float(r['fdr']):.2e}")
print(open('resumen.json').read())
