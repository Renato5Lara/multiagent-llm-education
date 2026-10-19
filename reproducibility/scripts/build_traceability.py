"""Genera RESULTS_TRACEABILITY.csv combinando (a) la correspondencia estática informe -> evidencia -> script y
(b) los resultados reales de outputs/verification_report.json. Ejecutar después de reproduce_results.py.
Estados: REPRODUCIDO (todas las comprobaciones COINCIDE/DIFERENCIA_EXPLICABLE), DISCREPANTE, PARCIAL, NO_REPRODUCIBLE, NO_APLICA."""
import csv
import json
from collections import Counter, defaultdict

from repro_lib import OUT, ROOT

STATIC = [  # tabla, objetivo, métrica, campaña, evidencia, script, nota
    ("Tabla 8", "OE2", "P50, media, P95 y throughput por sistema y carga (media de 10 corridas)", "N2", "data/experiments/oe_n2_2026-10-05/campaign/runs.csv", "scripts/reproduce_results.py (pandas)", ""),
    ("Tabla 9", "OE2", "razón geométrica P95/throughput, IC95, p Holm (Welch sobre log)", "N2", "data/experiments/oe_n2_2026-10-05/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe2_reanalysis.py", ""),
    ("Tabla 10", "OE2", "diferencia absoluta, g de Hedges, p Holm Mann-Whitney", "N2", "data/experiments/oe_n2_2026-10-05/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe2_reanalysis.py", ""),
    ("Tabla 11", "OE2", "razón de medias geométricas vs decision_table, rules, bruteforce", "N9b", "data/experiments/oe_n9b_2026-10-14/campaign_final/runs.csv", "oe_n8_2026-10-13/scripts/oe2_aux_analysis.py", "N9 (abortada) no interviene"),
    ("Tabla 17", "OE4", "latencia, throughput y T_conv por carga con N=20", "N4", "data/experiments/oe_n4_2026-10-06/campaign/runs.csv", "scripts/reproduce_results.py (pandas)", "k_stop no reproducible: viene de observaciones in-process no publicadas"),
    ("Tabla 18", "OE4", "P95, throughput, T_conv con N=10 y N=30", "N8", "data/experiments/oe_n8_2026-10-13/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe4_nvar_analysis.py", ""),
    ("Tabla 19", "OE4", "contraste N30 vs N10 (razón, IC95, p Holm)", "N8", "data/experiments/oe_n8_2026-10-13/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe4_nvar_analysis.py", "«Mayor p de Holm» se toma entre P95, throughput y T_conv"),
    ("Tabla 20", "OE4", "P95, throughput, T_conv con N=20 y protocolo N8", "N8b (directorio oe_n10)", "data/experiments/oe_n10_2026-10-14_n20/campaign/runs.csv", "scripts/reproduce_results.py (pandas)", ""),
]
PEND = [  # estados que no se calculan en esta entrega
    ("Tablas 5-7, 37", "OE1", "estado MET/NOT_MET y Spearman (n=14)", "N1", "data/experiments/oe_n1_2026-10-05/oe1_report/", "oe_n8_2026-10-13/scripts/oe1_verify.py", "PARCIAL", "archivos e integridad publicados; observaciones N1 no publicadas; no recalculado"),
    ("Tablas 13, 14, 39, 40", "OE3", "efectos marginales y ANOVA factorial", "N3", "data/experiments/oe_n3_2026-10-06/runs_oe3.csv", "oe_n8_2026-10-13/scripts/oe3_reanalysis.py", "PARCIAL", "oe3_anova.csv se regenera byte a byte; falta comparación celda a celda con la tabla del informe"),
    ("Tablas 21-24", "OE4", "N11: desempeño por N y carga, contrastes, cambio de régimen", "N11", "data/experiments/oe_n11_2026-10-14_3N/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe4_n11_analysis.py", "PARCIAL", "no implementado en esta entrega; 179/180 corridas ok (1 excluida: no_requests)"),
    ("Tabla 25", "OE4", "cumplimiento RNF01/RNF04 por campaña", "N4/N8/N8b/N11", "data/experiments/oe_n8_2026-10-13/d27_verificacion/", "oe_n8_2026-10-13/scripts/verif_d27.py", "PARCIAL", "no implementado en esta entrega"),
    ("Tablas 28-29, 41", "OE5", "precisión/recall/F1 v3 provisional; Spearman aptitud-F1", "N5", "data/experiments/oe_n5_2026-10-06/", "oe_n5_2026-10-06/analyze_f1_v3.py; scripts/reproduce_f1_v3_independent.py", "PARCIAL", "especificación v3 provisional (official=False); no recalculado"),
    ("Tablas 15, 30", "OE3/OE5", "resultados históricos con la especificación v2 (K10)", "K10 2026-09-27", "backend/official_runs/k10_official_2026-09-27 (ya en Git)", "backend/official_runs/k10_analysis_2026-09-27", "PARCIAL", "histórico; fuera de este paquete; no recalculado"),
    ("Tabla 26", "OE4", "pruebas de carga exploratorias (antecedente)", "antecedente", "backend/loadtest/results (ya en Git)", "backend/loadtest/summarize.py", "PARCIAL", "no recalculado; no comparable con N1-N11"),
    ("Tablas 27 (usabilidad), 35, 36", "OE5", "SUS, panel de expertos", "—", "—", "—", "NO_REPRODUCIBLE", "no existen datos reales (0 evaluadores); no se simulan"),
    ("Tablas 32, 44", "transversal", "estado del arte", "—", "data/experiments/oe_n8_2026-10-13/ESTADO_DEL_ARTE_MATRIZ.csv", "build_state_of_art_matrix.py", "PARCIAL", "depende de consultas externas; no determinista"),
    ("Tablas 1-4, 7, 12, 16, 31, 33, 34, 42, 43, 45", "metodológico", "operacionalización, estructura de análisis, entorno", "—", "—", "—", "NO_APLICA", "texto metodológico o descriptivo sin cálculo"),
]
rep = json.loads((OUT / "verification_report.json").read_text(encoding="utf-8"))
by = defaultdict(Counter)
for c in rep["comprobaciones"]:
    if not c["id"].startswith("PEND-"):
        by[c["tabla"]][c["estado"]] += 1
rows = []
for t, obj, met, camp, ev, scr, nota in STATIC:
    cnt = by[t]
    n = sum(cnt.values())
    ok = cnt["COINCIDE"] + cnt["DIFERENCIA_EXPLICABLE"]
    estado = "DISCREPANTE" if cnt["DISCREPANCIA"] else "REPRODUCIDO" if ok == n - cnt["NO_REPRODUCIBLE"] and ok else "PARCIAL"
    if cnt["NO_REPRODUCIBLE"] and not cnt["DISCREPANCIA"]:
        estado = "PARCIAL"
    rows.append(dict(tabla_informe=t, objetivo=obj, metrica=met, campana=camp, archivo_evidencia=ev, script_analisis=scr, comprobaciones=n, coinciden=cnt["COINCIDE"],
                     diferencia_explicable=cnt["DIFERENCIA_EXPLICABLE"], discrepantes=cnt["DISCREPANCIA"], no_reproducibles=cnt["NO_REPRODUCIBLE"], estado=estado,
                     observacion=nota or "recalculado desde datos publicados; coincidencia a la precisión publicada"))
for t, obj, met, camp, ev, scr, estado, nota in PEND:
    rows.append(dict(tabla_informe=t, objetivo=obj, metrica=met, campana=camp, archivo_evidencia=ev, script_analisis=scr, comprobaciones=0, coinciden=0, diferencia_explicable=0,
                     discrepantes=0, no_reproducibles=0, estado=estado, observacion=nota))
with open(ROOT / "RESULTS_TRACEABILITY.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(Counter(r["estado"] for r in rows))
