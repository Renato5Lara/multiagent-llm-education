"""Valida los CSV de corridas publicados. No altera ni elimina filas: informa. Cada exclusión se declara con su regla.
Clases de hallazgo: ESQUEMA (columnas/tipos), DATOS (duplicados, no finitos, conteo ≠ plan), EXCLUSION (corrida con status ≠ ok; regla explícita).
Salida: outputs/validation_report.json. Código de salida 3 = error de esquema, 4 = inconsistencia de datos."""
import json, sys
import numpy as np, pandas as pd
from repro_lib import EXP, OUT, EXIT_OK, EXIT_ESQUEMA, EXIT_DATOS

CAMPAIGN_RUNS = {  # campaña → (ruta del runs.csv, ruta del provenance.json)
    "N2": "oe_n2_2026-10-05/campaign", "N4": "oe_n4_2026-10-06/campaign", "N8": "oe_n8_2026-10-13/campaign", "N8b": "oe_n10_2026-10-14_n20/campaign",
    "N9b": "oe_n9b_2026-10-14/campaign_final", "N11": "oe_n11_2026-10-14_3N/campaign"}
REQUIRED = ["campaign_id", "system", "run_id", "batch_seed", "load", "p50_ms", "mean_ms", "p95_ms", "throughput_rps", "errors", "timeouts", "official", "status"]
NUMERIC = ["batch_seed", "load", "p50_ms", "mean_ms", "p95_ms", "throughput_rps", "errors", "timeouts"]
RULE = "Una corrida entra al análisis solo si status == 'ok' (corrida con ventana estacionaria analizable). Las demás se informan, no se borran."


def main() -> int:
    rep, schema_err, data_err = {"regla_de_inclusion": RULE, "campanas": {}}, 0, 0
    for camp, d in CAMPAIGN_RUNS.items():
        df = pd.read_csv(EXP / d / "runs.csv", low_memory=False)
        prov = json.loads((EXP / d / "provenance.json").read_text(encoding="utf-8"))
        c = {"filas": len(df), "filas_planificadas": prov["design"]["n_planned_runs"], "hallazgos": []}
        miss = [k for k in REQUIRED if k not in df.columns]
        if miss:
            c["hallazgos"].append({"clase": "ESQUEMA", "detalle": f"faltan columnas {miss}"}); schema_err += 1
        else:
            bad = [k for k in NUMERIC if not pd.api.types.is_numeric_dtype(df[k])]
            if bad:
                c["hallazgos"].append({"clase": "ESQUEMA", "detalle": f"no numéricas: {bad}"}); schema_err += 1
            ok = df[df.status == "ok"]
            c["filas_ok"] = len(ok)
            c["exclusiones"] = [{"run_id": r.run_id, "status": r.status, "regla": RULE} for r in df[df.status != "ok"].itertuples()]
            if df.run_id.duplicated().any():
                c["hallazgos"].append({"clase": "DATOS", "detalle": f"run_id duplicados: {int(df.run_id.duplicated().sum())}"}); data_err += 1
            if len(df) != c["filas_planificadas"]:
                c["hallazgos"].append({"clase": "DATOS", "detalle": f"filas {len(df)} ≠ plan {c['filas_planificadas']}"}); data_err += 1
            nf = int((~np.isfinite(ok[NUMERIC].to_numpy(dtype=float))).sum())
            if nf:
                c["hallazgos"].append({"clase": "DATOS", "detalle": f"{nf} valores no finitos o nulos en métricas de corridas ok"}); data_err += 1
            c["nulos_en_corridas_no_ok_son_faltantes_no_ceros"] = bool(df[df.status != "ok"][["p95_ms", "throughput_rps"]].isna().all().all()) if (df.status != "ok").any() else None
            c["official_valores"] = sorted(map(str, df.official.unique()))
            c["errores_totales"], c["timeouts_totales"] = int(ok.errors.sum()), int(ok.timeouts.sum())
            c["semillas_distintas"], c["sistemas"] = int(df.batch_seed.nunique()), sorted(df.system.unique().tolist())
            c["celdas_sin_division_por_cero"] = bool((ok.throughput_rps > 0).all() and (ok.p95_ms > 0).all())
        rep["campanas"][camp] = c
    rep["estado"] = "ERROR_ESQUEMA" if schema_err else "INCONSISTENCIA_DATOS" if data_err else "OK"
    rep["limitaciones"] = ["No se imponen rangos plausibles: no hay umbrales de validez definidos para ellos en el protocolo.",
                           "Los datos son resúmenes por corrida del arnés; los registros por petición (Locust) no se publican por tamaño (hashes en manifest.json de cada campaña)."]
    OUT.mkdir(exist_ok=True)
    (OUT / "validation_report.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    for k, c in rep["campanas"].items():
        print(f"{k}: {c['filas']} filas (plan {c['filas_planificadas']}), ok={c.get('filas_ok')}, exclusiones={len(c.get('exclusiones', []))}, hallazgos={len(c['hallazgos'])}")
    print(rep["estado"])
    return EXIT_ESQUEMA if schema_err else EXIT_DATOS if data_err else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
