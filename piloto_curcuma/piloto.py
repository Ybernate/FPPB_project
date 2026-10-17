"""Piloto: Curcuma longa -> LOTUS (Wikidata) -> ChEMBL -> Reactome.

Verifica con datos reales el flujo del aplicativo. Guarda resultados en CSV/JSON
en esta misma carpeta.
"""
import csv
import json
import time
import urllib.parse
import urllib.request
from collections import defaultdict

ESPECIE = "Curcuma longa"
UA = {"User-Agent": "fppb-student-pilot/1.0 (academic project)"}
CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"


def get_json(url, data=None, headers=None, retries=3):
    h = dict(UA)
    if headers:
        h.update(headers)
    for i in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


# ---------- 1. LOTUS via Wikidata ----------
SPARQL = """
SELECT ?c ?label ?ik ?smiles (COUNT(DISTINCT ?art) AS ?nref) WHERE {
  ?t wdt:P225 "%s".
  ?c p:P703 ?st. ?st ps:P703 ?t.
  ?c wdt:P235 ?ik.
  OPTIONAL { ?c wdt:P233 ?smiles. }
  OPTIONAL { ?c rdfs:label ?label. FILTER(lang(?label)="en") }
  OPTIONAL { ?st prov:wasDerivedFrom ?ref. ?ref pr:P248 ?art. }
} GROUP BY ?c ?label ?ik ?smiles
""" % ESPECIE


def lotus():
    url = "https://query.wikidata.org/sparql?format=json&query=" + urllib.parse.quote(SPARQL)
    res = get_json(url)["results"]["bindings"]
    comp = {}
    for b in res:
        ik = b["ik"]["value"]
        row = comp.setdefault(ik, {
            "inchikey": ik,
            "nombre": b.get("label", {}).get("value", ""),
            "smiles": b.get("smiles", {}).get("value", ""),
            "n_refs": 0,
            "qid": b["c"]["value"].rsplit("/", 1)[-1],
        })
        row["n_refs"] = max(row["n_refs"], int(b["nref"]["value"]))
    return comp


# ---------- 2. ChEMBL ----------
def chembl_match(comp):
    keys = list(comp)
    found = {}
    for i in range(0, len(keys), 25):
        batch = keys[i:i + 25]
        q = ",".join(batch)
        url = (f"{CHEMBL}/molecule.json?molecule_structures__standard_inchi_key__in={q}"
               "&limit=100&only=molecule_chembl_id,pref_name,molecule_structures,molecule_properties")
        for m in get_json(url)["molecules"]:
            ik = (m.get("molecule_structures") or {}).get("standard_inchi_key")
            if ik:
                found[ik] = m
        time.sleep(0.3)
    return found


def chembl_activities(chembl_ids):
    acts = []
    for cid in chembl_ids:
        url = (f"{CHEMBL}/activity.json?molecule_chembl_id={cid}&standard_type__in=IC50,Ki"
               "&standard_units=nM&target_organism=Homo%20sapiens&limit=1000"
               "&only=molecule_chembl_id,target_chembl_id,target_pref_name,standard_type,"
               "standard_relation,standard_value,pchembl_value")
        while url:
            d = get_json(url)
            acts.extend(d["activities"])
            nxt = d["page_meta"].get("next")
            url = "https://www.ebi.ac.uk" + nxt if nxt else None
        time.sleep(0.3)
    return acts


def chembl_targets(target_ids):
    info = {}
    ids = list(target_ids)
    for i in range(0, len(ids), 25):
        q = ",".join(ids[i:i + 25])
        url = (f"{CHEMBL}/target.json?target_chembl_id__in={q}&limit=100"
               "&only=target_chembl_id,pref_name,target_type,target_components")
        for t in get_json(url)["targets"]:
            comps = t.get("target_components") or []
            info[t["target_chembl_id"]] = {
                "tipo": t["target_type"],
                "nombre": t["pref_name"],
                "uniprot": comps[0]["accession"] if len(comps) == 1 else None,
            }
        time.sleep(0.3)
    return info


# ---------- 3. Reactome ----------
def reactome(uniprots):
    url = "https://reactome.org/AnalysisService/identifiers/projection?pageSize=15&page=1&sortBy=ENTITIES_FDR&order=ASC&resource=TOTAL"
    d = get_json(url, data="\n".join(uniprots).encode(), headers={"Content-Type": "text/plain"})
    out = []
    for p in d["pathways"]:
        out.append({
            "ruta": p["name"], "id": p["stId"],
            "entidades_encontradas": p["entities"]["found"],
            "entidades_total": p["entities"]["total"],
            "p": p["entities"]["pValue"], "fdr": p["entities"]["fdr"],
        })
    return out, d["summary"]["token"], d.get("identifiersNotFound")


def main():
    comp = lotus()
    print(f"LOTUS: {len(comp)} compuestos unicos (con InChIKey) para {ESPECIE}")
    matches = chembl_match(comp)
    print(f"ChEMBL: {len(matches)} coinciden por InChIKey completo")

    acts = chembl_activities([m["molecule_chembl_id"] for m in matches.values()])
    tinfo = chembl_targets({a["target_chembl_id"] for a in acts})
    ik_by_chembl = {m["molecule_chembl_id"]: ik for ik, m in matches.items()}

    rows = []
    for a in acts:
        t = tinfo.get(a["target_chembl_id"], {})
        if t.get("tipo") != "SINGLE PROTEIN" or not t.get("uniprot"):
            continue
        rows.append({
            "chembl_mol": a["molecule_chembl_id"],
            "inchikey": ik_by_chembl[a["molecule_chembl_id"]],
            "target": t["nombre"], "uniprot": t["uniprot"],
            "tipo": a["standard_type"], "relacion": a["standard_relation"],
            "valor_nM": a["standard_value"], "pchembl": a["pchembl_value"],
        })
    uniprots = sorted({r["uniprot"] for r in rows})
    print(f"Actividades humanas IC50/Ki en nM: {len(acts)}; sobre proteina individual: {len(rows)}; blancos unicos: {len(uniprots)}")

    paths, token, notfound = ([], None, None)
    if uniprots:
        paths, token, notfound = reactome(uniprots)

    # --- guardar ---
    def dump_csv(name, data):
        if not data:
            return
        with open(name, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)

    comp_rows = []
    for ik, c in comp.items():
        m = matches.get(ik)
        n_t = len({r["uniprot"] for r in rows if r["inchikey"] == ik})
        comp_rows.append({**c, "chembl_id": m["molecule_chembl_id"] if m else "",
                          "chembl_nombre": (m or {}).get("pref_name") or "",
                          "n_blancos_proteina": n_t})
    comp_rows.sort(key=lambda r: -r["n_refs"])
    dump_csv("compuestos.csv", comp_rows)
    dump_csv("actividades.csv", rows)
    dump_csv("rutas.csv", paths)
    with open("resumen.json", "w", encoding="utf-8") as f:
        json.dump({"especie": ESPECIE, "n_lotus": len(comp), "n_chembl": len(matches),
                   "n_actividades_proteina": len(rows), "n_blancos": len(uniprots),
                   "reactome_token": token, "reactome_not_found": notfound}, f, indent=2)


if __name__ == "__main__":
    main()
