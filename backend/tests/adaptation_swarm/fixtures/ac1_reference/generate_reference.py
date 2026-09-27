"""Genera el FIXTURE de referencia EXTERNA para Gwet AC1 (`ac1_reference_cases.json`) con el paquete `irrCAC` (port en Python, A. Fergadis, del paquete R `irrCAC` de Gwet). NO usa la implementación del
proyecto: los valores «externos» del fixture salen únicamente de esa librería, con la misma entrada (ítems = 4 arquetipos, evaluadores = columnas, categorías 0 = Rechazar, 1 = Aprobar).

No se ejecuta en la suite (requiere `pip install irrCAC pandas`, no instalados en la venv del proyecto). Uso, fuera de la venv del proyecto:
    python generate_reference.py ac1_reference_cases.json
La librería redondea a 5 decimales (tolerancia de comparación: 2e-5). Verificación con el paquete R `irrCAC` original: PENDIENTE (R no disponible en el entorno); ver `verify_with_R_irrCAC.R`.
"""

import json
import sys
from datetime import date
from importlib import metadata

import pandas as pd
from irrCAC.raw import CAC

ARCHETYPES = ("visual_dominant", "logical_syntactic", "explanatory_conceptual", "balanced_multimodal")
CASES = [  # (id, n evaluadores, aprobaciones por arquetipo) — vectores de VERIFICACIÓN, no respuestas de evaluadores reales
    ("c01_one_reject", 10, (10, 10, 10, 9)), ("c02_six_of_ten", 10, (6, 10, 10, 10)), ("c03_four_of_ten", 10, (4, 10, 10, 10)), ("c04_tie", 10, (5, 10, 10, 10)),
    ("c05_mixed", 10, (8, 9, 7, 10)), ("c06_all_reject_one", 10, (0, 10, 10, 10)), ("c07_six_each", 10, (6, 6, 6, 6)), ("c08_n12", 12, (7, 12, 12, 12)),
    ("c09_n12_mixed", 12, (6, 11, 12, 12)), ("c10_all_approve", 10, (10, 10, 10, 10)), ("c11_n15", 15, (9, 10, 12, 15)), ("c12_all_reject", 10, (0, 0, 0, 0)),
    ("c13_n11", 11, (6, 7, 8, 9)), ("c14_n20", 20, (11, 14, 17, 20)), ("c15_balanced_split", 10, (10, 0, 10, 0)), ("c16_n10_seven", 10, (7, 8, 9, 10)),
]


FUTURE_CERTIFICATION = {
 "status": "PENDIENTE — R + irrCAC NO ejecutado (PX8)",
 "script": "verify_with_R_irrCAC.R",
 "command": "Rscript verify_with_R_irrCAC.R ac1_reference_cases.json r_irrCAC_results.json",
 "certifies": [
  "gold_panel.gwet_ac1_binary_multi_rater (implementación del proyecto)",
  "ac1_reference_cases.json (valores del port en Python)"
 ],
 "compares": "implementación ↔ fixture ↔ R, para AC1, p_a y p_e en los casos del fixture",
 "r_version_required": "no se exige una versión mínima; se registra la real (r_irrCAC_results.json: r_version)",
 "irrCAC_R_package_version_required": "no se fija de antemano; se registra la real (irrCAC_version)",
 "expected_fields": "gwet.ac1.raw(...)$est: coeff.val, pa, pe (según la documentación de irrCAC; el script aborta si faltan; NO verificado por ejecución)",
 "hash_inputs": [
  "ac1_reference_cases.json (sha256/md5 registrado por el script como input_hash)",
  "gold_panel.py al momento de certificar (registrar su sha256 junto con el resultado)"
 ],
 "hash_outputs": [
  "r_irrCAC_results.json (sha256 en el addendum de certificación)"
 ],
 "tolerance_rule": "half-unit of the last decimal literally returned by R (and of the fixture: 5 decimals) + 1e-12; derivada de la precisión real de R, no fijada por suposición",
 "evidence_to_keep": [
  "r_irrCAC_results.json",
  "versión de R e irrCAC y sessionInfo (dentro del JSON)",
  "sha256 del fixture y de gold_panel.py",
  "salida del test de certificación"
 ]
}


def main(out: str) -> None:
    rows = []
    for cid, n, ks in CASES:
        ratings = pd.DataFrame({f"r{j}": [1 if j < k else 0 for k in ks] for j in range(n)}, index=list(ARCHETYPES))
        est = CAC(ratings, categories=[0, 1]).gwet()["est"]
        rows.append({"id": cid, "n": n, "approvals": list(ks), "external": {"ac1": float(est["coefficient_value"]), "pa": float(est["pa"]), "pe": float(est["pe"])}})
    meta = {"source": "irrCAC (Python) — port del paquete R irrCAC de K. L. Gwet", "package_version": metadata.version("irrCAC"), "pandas_version": pd.__version__, "generated_on": date.today().isoformat(),
            "function": "irrCAC.raw.CAC(ratings, categories=[0, 1]).gwet()", "categories": {"0": "Rechazar", "1": "Aprobar"}, "items": list(ARCHETYPES), "rounding": "5 decimales (lo aplica la librería)",
            "tolerance": 2e-5, "r_irrCAC_verified": False,
            "verification_status": "CONTRASTE CRUZADO con un port independiente en Python; la verificación con R + irrCAC (referencia) está PENDIENTE",
            "future_certification": FUTURE_CERTIFICATION, "reference": "Gwet, K. L. (2008). Br. J. Math. Stat. Psychol. 61(1), 29-48"}
    with open(out, "x", encoding="utf-8") as fh:
        json.dump({"meta": meta, "cases": rows}, fh, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main(sys.argv[1])
