# -*- coding: utf-8 -*-
"""Recálculo INDEPENDIENTE de los indicadores por corrida HTTP (OE1, OE2-B, OE4) desde el registro por petición del generador de carga.

No importa ningún módulo del artefacto ni del ejecutor: solo la biblioteca estándar. Implementa el procedimiento documentado en el diseño y en
`http_window.summarize_run` (ventana: desde `warmup` = 10 s después de la primera petición completada hasta la última; throughput = correctas / duración;
percentil por interpolación lineal; T_conv medio de las correctas) y compara cada campo con el registro guardado por el ejecutor (`intentos.jsonl`).

Solo lectura: no escribe en la carpeta de la campaña.

Uso: python recomputo_http.py <carpeta_campana> <salida.csv> [<salida_resumen.json>]
"""
import csv, json, math, os, sys

WARMUP_S = 10.0
CAMPOS = ["requests_total", "requests_ok", "errors", "timeouts", "duration_s", "throughput_rps", "latency_p50_ms",
          "latency_mean_ms", "latency_p95_ms", "t_conv_ms_mean", "window_start_epoch_s", "window_end_epoch_s"]


def percentil(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * (p / 100.0)
    lo = int(pos); hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def leer_raw(path):
    filas = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            filas.append({"t": float(r["t_end_epoch_s"]), "ms": float(r["response_ms"]), "ok": r["ok"] == "1", "to": r["timeout"] == "1",
                          "tc": float(r["t_conv_ms"]) if r.get("t_conv_ms") else None})
    return filas


def recalcular(filas):
    if not filas:
        return None
    t0 = min(f["t"] for f in filas); t1 = max(f["t"] for f in filas)
    ini = t0 + WARMUP_S
    win = [f for f in filas if ini <= f["t"] <= t1]
    dur = t1 - ini
    ok = [f for f in win if f["ok"]]
    lat = [f["ms"] for f in ok]
    tcs = [f["tc"] for f in ok if f["tc"] is not None]
    return {"requests_total": len(win), "requests_ok": len(ok), "errors": len(win) - len(ok), "timeouts": sum(f["to"] for f in win),
            "duration_s": dur, "throughput_rps": (len(ok) / dur) if dur > 0 else None,
            "latency_p50_ms": percentil(lat, 50), "latency_mean_ms": (sum(lat) / len(lat)) if lat else None,
            "latency_p95_ms": percentil(lat, 95), "t_conv_ms_mean": (sum(tcs) / len(tcs)) if tcs else None,
            "window_start_epoch_s": ini, "window_end_epoch_s": t1}


def main(camp, salida, resumen=None):
    reg = []
    with open(os.path.join(camp, "intentos.jsonl"), encoding="utf-8") as fh:
        for l in fh:
            if l.strip():
                reg.append(json.loads(l))
    finales = set()
    p = os.path.join(camp, "runs.jsonl")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            for l in fh:
                if l.strip():
                    r = json.loads(l)
                    if r.get("valid"):
                        finales.add(r["label"])
    filas_out = []
    maxabs = {c: 0.0 for c in CAMPOS}; maxrel = {c: 0.0 for c in CAMPOS}; peor = {c: None for c in CAMPOS}
    n_cmp = 0; sin_raw = 0; sin_indicadores = 0; n_fin = 0; n_fin_ok = 0
    for r in reg:
        lab = r.get("label")
        raw = os.path.join(camp, "raw_http", f"{lab}.csv")
        if "requests_total" not in r:
            sin_indicadores += 1
            continue
        if not os.path.exists(raw):
            sin_raw += 1
            continue
        rc = recalcular(leer_raw(raw))
        n_cmp += 1
        fila = {"label": lab, "status": r.get("status"), "valida_final": lab in finales}
        todos_iguales = True
        for c in CAMPOS:
            a, b = r.get(c), rc.get(c)
            if a is None or b is None:
                fila[c + "_guardado"] = a; fila[c + "_recalculado"] = b; fila[c + "_dif_abs"] = ""
                if a != b: todos_iguales = False
                continue
            d = abs(float(a) - float(b)); rel = d / max(abs(float(a)), 1e-12)
            fila[c + "_guardado"] = a; fila[c + "_recalculado"] = b; fila[c + "_dif_abs"] = d
            if d > maxabs[c]: maxabs[c] = d; peor[c] = (lab, a, b)
            if rel > maxrel[c]: maxrel[c] = rel
            if d > 1e-9 and rel > 1e-9: todos_iguales = False
        fila["todos_los_campos_coinciden"] = todos_iguales
        if lab in finales:
            n_fin += 1; n_fin_ok += todos_iguales
        filas_out.append(fila)
    cols = list(filas_out[0].keys()) if filas_out else []
    with open(salida, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(filas_out)
    res = {"campana": os.path.basename(os.path.normpath(camp)), "registros_en_intentos": len(reg), "intentos_con_raw_recalculados": n_cmp,
           "intentos_sin_indicadores_guardados": sin_indicadores, "intentos_con_indicadores_pero_sin_raw": sin_raw,
           "corridas_validas_finales_recalculadas": n_fin, "corridas_validas_finales_con_todos_los_campos_iguales": n_fin_ok,
           "intentos_con_todos_los_campos_iguales": sum(1 for f in filas_out if f["todos_los_campos_coinciden"]),
           "diferencia_abs_max_por_campo": maxabs, "diferencia_rel_max_por_campo": maxrel, "peor_caso_por_campo": peor}
    if resumen:
        with open(resumen, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("peor_caso_por_campo",)}, ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
