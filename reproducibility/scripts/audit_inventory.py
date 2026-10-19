"""Genera auditoria/INVENTARIO_CAMPANAS.csv a partir de los archivos publicados (solo lectura)."""
import csv, json
from pathlib import Path
import pandas as pd
from repro_lib import EXP, ROOT

CAMP = [("N1", "oe_n1_2026-10-05", "OE1", None), ("N2", "oe_n2_2026-10-05", "OE2", "campaign"), ("N3", "oe_n3_2026-10-06", "OE3", None), ("N4", "oe_n4_2026-10-06", "OE4", "campaign"),
        ("N5", "oe_n5_2026-10-06", "OE5", None), ("N6", "oe_n6_2026-10-06", "integración", None), ("N7", "oe_n7_2026-10-06", "suite de pruebas", None),
        ("N8", "oe_n8_2026-10-13", "OE4", "campaign"), ("N9", "oe_n9_2026-10-13", "OE2 (abortada)", None), ("N9b", "oe_n9b_2026-10-14", "OE2", "campaign_final"),
        ("N8b", "oe_n10_2026-10-14_n20", "OE4", "campaign"), ("N11", "oe_n11_2026-10-14_3N", "OE4", "campaign")]
rows = []
for c, d, oe, sub in CAMP:
    r = dict(campana=c, directorio=d, objetivos_a_los_que_aporta=oe)
    if sub:
        b = EXP / d / sub
        df = pd.read_csv(b / "runs.csv", low_memory=False)
        pv = json.loads((b / "provenance.json").read_text(encoding="utf-8"))
        des = pv["design"]
        r.update(filas_planificadas=des["n_planned_runs"], filas_registradas=len(df), filas_ok=int((df.status == "ok").sum()), filas_no_ok=int((df.status != "ok").sum()),
                 sistemas=";".join(sorted(df.system.unique())), cargas=";".join(map(str, sorted(df.load.unique()))), tamanos_enjambre=";".join(map(str, sorted(df.swarm_N.dropna().unique().astype(int)))),
                 semillas_distintas=int(df.batch_seed.nunique()), runs_por_celda=des.get("runs_per_cell"), oficial=str(pv.get("official")), clase_entorno=pv.get("environment_class"),
                 commit_registrado=pv["code"].get("commit", "")[:8], codigo_sucio_registrado=str(pv["code"].get("dirty")), creada_utc=pv.get("created_utc"),
                 start_margin_s=des.get("start_margin_s"), persistencia=pv.get("persist_policy"))
    else:
        r.update(nota="campaña sin runs.csv HTTP (otro diseño o abortada): ver PROVENANCE.md")
    rows.append(r)
cols = sorted({k for r in rows for k in r}, key=lambda k: ["campana", "directorio", "objetivos_a_los_que_aporta"].index(k) if k in ("campana", "directorio", "objetivos_a_los_que_aporta") else 99)
with open(ROOT / "auditoria" / "INVENTARIO_CAMPANAS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
print(pd.DataFrame(rows)[["campana", "filas_planificadas", "filas_registradas", "filas_ok", "oficial", "clase_entorno", "creada_utc"]].to_string())
