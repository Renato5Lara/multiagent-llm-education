"""Construye el REGISTRO de certificación PX8 (`px8_certification_<fecha>.json`) a partir de la salida CRUDA de R (`r_irrCAC_results.json`, producida literalmente por `verify_with_R_irrCAC.R`; este script NO
ejecuta R ni la modifica) y del fixture (`ac1_reference_cases.json`). Añade lo que la salida de R no trae: el sha256 de `gold_panel.py` en el momento de certificar, la comparación caso a caso
(implementación Python ↔ fixture ↔ R) con su clasificación y el estado global. NO cambia ninguna decisión metodológica: es un documento de evidencia, análogo al addendum de Python 3.12.

Clasificación por caso (AC1, p_a, p_e): EXACTA (diferencia por debajo de 1e-9) · REDONDEO_DOCUMENTABLE (dentro de la tolerancia derivada de la precisión REAL que R devolvió para ese campo: media unidad de su
último decimal, específico de R, PASO 4/6) · DISCREPANCIA_REAL (fuera de esa tolerancia: no se corrige aquí, se reporta).

Uso:  python certify_px8.py r_irrCAC_results.json px8_certification_<fecha>.json  (rutas relativas a este directorio; requiere el backend en PYTHONPATH)
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))  # backend/
from adaptation_swarm.metrics import gold_panel as gp  # noqa: E402


def _decimals(v) -> int:
    return 0 if isinstance(v, int) else max(0, -v.as_tuple().exponent)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _votes(approvals: list[int], n: int) -> dict[str, list[bool]]:
    return {a: [True] * k + [False] * (n - k) for a, k in zip(gp.ARCHETYPES, approvals)}


def build(r_results_path: Path, fixture_path: Path = HERE / "ac1_reference_cases.json") -> dict:
    r = json.loads(r_results_path.read_text(encoding="utf-8"), parse_float=Decimal)
    fx_raw = fixture_path.read_bytes()
    fx = json.loads(fx_raw.decode("utf-8"), parse_float=Decimal)
    by_r = {c["id"]: c for c in r["cases"]}
    half = lambda d: Decimal(5) * Decimal(10) ** (-(d + 1))
    tol_r_by_field = {f: half(max(_decimals(c[f]) for c in by_r.values())) + Decimal("1e-12") for f in ("ac1", "pa", "pe")}   # precisión REAL de R, por campo (python vs R)
    tol_fx = half(max(_decimals(c["external"]["ac1"]) for c in fx["cases"])) + Decimal("1e-12")                                          # precisión del fixture (5 decimales; fixture vs R)

    cases = []
    overall_ok = True
    for c in fx["cases"]:
        mine = gp.gwet_ac1_binary_multi_rater(_votes([int(x) for x in c["approvals"]], int(c["n"])))
        rc = by_r[c["id"]]
        row = {"case_id": c["id"], "n": int(c["n"]), "approvals": [int(x) for x in c["approvals"]],
               "python_ac1": mine["ac1"], "fixture_ac1": float(c["external"]["ac1"]), "R_ac1": float(rc["ac1"]),
               "python_pa": mine["observed_agreement"], "fixture_pa": float(c["external"]["pa"]), "R_pa": float(rc["pa"]),
               "python_pe": mine["chance_agreement"], "fixture_pe": float(c["external"]["pe"]), "R_pe": float(rc["pe"])}
        diffs, statuses = {}, []
        for field, pk, fk, rk in (("ac1", "python_ac1", "fixture_ac1", "R_ac1"), ("pa", "python_pa", "fixture_pa", "R_pa"), ("pe", "python_pe", "fixture_pe", "R_pe")):
            d_py_r = abs(Decimal(repr(row[pk])) - Decimal(repr(row[rk])))
            d_fx_r = abs(Decimal(repr(row[fk])) - Decimal(repr(row[rk])))
            tol_py, tol_f = tol_r_by_field[field], max(tol_r_by_field[field], tol_fx)                     # python se compara con la precisión de R; el fixture además con SU PROPIA precisión (5 decimales)
            worst_status = lambda d, t: "EXACTA" if d < Decimal("1e-9") else ("REDONDEO_DOCUMENTABLE" if d <= t else "DISCREPANCIA_REAL")
            s_py, s_fx = worst_status(d_py_r, tol_py), worst_status(d_fx_r, tol_f)
            status = "DISCREPANCIA_REAL" if "DISCREPANCIA_REAL" in (s_py, s_fx) else ("REDONDEO_DOCUMENTABLE" if "REDONDEO_DOCUMENTABLE" in (s_py, s_fx) else "EXACTA")
            diffs[field] = {"python_vs_R": float(d_py_r), "fixture_vs_R": float(d_fx_r), "tolerance_python_vs_R": float(tol_py), "tolerance_fixture_vs_R": float(tol_f), "status": status}
            statuses.append(status)
        row["differences"] = diffs
        row["status"] = "DISCREPANCIA_REAL" if "DISCREPANCIA_REAL" in statuses else ("REDONDEO_DOCUMENTABLE" if "REDONDEO_DOCUMENTABLE" in statuses else "EXACTA")
        overall_ok &= row["status"] != "DISCREPANCIA_REAL"
        cases.append(row)

    gold_panel_path = HERE.parents[3] / "adaptation_swarm" / "metrics" / "gold_panel.py"
    return {"schema": "px8-certification-v1", "certification_status": "CERTIFICADO" if overall_ok else "NO_CERTIFICADO",
            "certification_date": date.today().isoformat(), "certified_at_utc": datetime.now(timezone.utc).isoformat(),
            "r_version": r["r_version"], "irrCAC_version": r["irrCAC_version"], "function_used": r["function_used"],
            "session_info": r["session_info"], "input_fixture_sha256": hashlib.sha256(fx_raw).hexdigest(),
            "gold_panel_path": "adaptation_swarm/metrics/gold_panel.py", "gold_panel_sha256": _sha256(gold_panel_path),
            "r_irrCAC_results_file": r_results_path.name, "r_irrCAC_results_sha256": _sha256(r_results_path),
            "number_of_cases": len(cases), "comparison_method": "implementación Python (gwet_ac1_binary_multi_rater) ↔ fixture (port en Python de irrCAC) ↔ R (paquete irrCAC original, gwet.ac1.raw)",
            "tolerance_derivation": {"rule": "media unidad del último decimal que R devolvió para CADA CAMPO por separado (ac1, pa, pe), + 1e-12; NO una tolerancia global ni supuesta",
                                     "note": "irrCAC::gwet.ac1.raw redondea coeff.val (AC1) a 5 decimales internamente; pa y pe se devuelven con precisión completa de double. Verificado por observación directa "
                                             "de la salida de R (no documentado explícitamente en la ayuda del paquete)", "tolerance_by_field": {k: float(v) for k, v in tol_r_by_field.items()}, "tolerance_fixture": float(tol_fx)},
            "cases": cases, "overall_status": "CERTIFICADO" if overall_ok else "NO_CERTIFICADO",
            "scope": "Certifica ÚNICAMENTE gwet_ac1_binary_multi_rater (PX5/PX8). No incluye resultados de K=10, del panel humano ni del SUS."}


def main(argv: list[str]) -> None:
    r_path, out_path = HERE / argv[0], HERE / argv[1]
    cert = build(r_path)
    with out_path.open("x", encoding="utf-8") as fh:
        fh.write(json.dumps(cert, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"{cert['overall_status']}: {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
