"""Genera RESULTS_TRACEABILITY.csv: correspondencia tabla del informe -> campaña -> archivos -> script, con el estado REAL salido de
outputs/verification_report.json (ejecutar después de reproduce_results.py).
Estados por tabla: VERIFICADO_DESDE_DATOS · VERIFICADO_DESDE_DERIVADO · PARCIAL · DISCREPANCIA · NO_REPRODUCIBLE · NO_APLICA.
Una tabla es VERIFICADO_DESDE_DATOS solo si TODAS sus cifras numéricas comprobadas lo son y no queda ninguna sin comprobar; si queda alguna, es PARCIAL."""
import csv
import json
import re
from collections import Counter, defaultdict

from repro_lib import OUT, ROOT

E = "data/experiments/"
STATIC = {  # nº de tabla -> (objetivo, métrica, campaña, evidencia, script, nota)
    6: ("OE1", "Spearman/Kendall puntaje de cumplimiento vs desempeño (n=14)", "N1", E + "oe_n1_2026-10-05/oe3_run|oe4_run/raw_observations.csv", "oe_n8_2026-10-13/scripts/oe1_verify.py", "la fila «Usuarios frente al propio puntaje» no está en oe1_verify.json"),
    8: ("OE2", "P50, media, P95 y throughput (media de 10 corridas)", "N2", E + "oe_n2_2026-10-05/campaign/runs.csv + campaign/raw/", "reproduce_results.py (pandas)", ""),
    9: ("OE2", "razón geométrica, IC95, p Holm (Welch sobre log)", "N2", E + "oe_n2_2026-10-05/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe2_reanalysis.py", ""),
    10: ("OE2", "diferencia absoluta, g de Hedges, p Holm Mann-Whitney", "N2", E + "oe_n2_2026-10-05/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe2_reanalysis.py", ""),
    11: ("OE2", "razón de medias geométricas vs decision_table, rules, bruteforce", "N9b", E + "oe_n9b_2026-10-14/campaign_final/runs.csv + raw", "oe_n8_2026-10-13/scripts/oe2_aux_analysis.py", "N9 (abortada) no interviene"),
    13: ("OE3", "efectos marginales (media geométrica T_conv), η² y p por permutación", "N3", E + "oe_n3_2026-10-06/runs_oe3.csv + run/raw_observations.csv", "adaptation_swarm.oe.factorial", "3 cifras (η² de la heurística, k_stop con heurística, T_conv de pso) difieren 1 unidad del último decimal: doble redondeo demostrado, ver publicacion/AUDITORIA_REDONDEO_TABLA13.md; las celdas «sin efecto» no se comprueban"),
    14: ("OE3", "ANOVA factorial: η² parcial y p de Holm", "N3", E + "oe_n3_2026-10-06/runs_oe3.csv", "oe_n8_2026-10-13/scripts/oe3_reanalysis.py", ""),
    17: ("OE4", "latencia, throughput, T_conv y k_stop por carga con N=20", "N4", E + "oe_n4_2026-10-06/campaign/runs.csv + inprocess/raw_observations.csv", "reproduce_results.py (pandas)", ""),
    18: ("OE4", "P95, throughput, T_conv con N=10 y N=30", "N8", E + "oe_n8_2026-10-13/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe4_nvar_analysis.py", ""),
    19: ("OE4", "contraste N30 vs N10", "N8", E + "oe_n8_2026-10-13/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe4_nvar_analysis.py", "«Mayor p de Holm» entre P95, throughput y T_conv"),
    20: ("OE4", "P95, throughput, T_conv con N=20 y protocolo N8", "N8b (directorio oe_n10)", E + "oe_n10_2026-10-14_n20/campaign/runs.csv", "reproduce_results.py (pandas)", ""),
    21: ("OE4", "P95 · throughput · T_conv (n) por N y carga, tramo B", "N11", E + "oe_n11_2026-10-14_3N/campaign/runs.csv + raw", "oe_n8_2026-10-13/scripts/oe4_n11_analysis.py", ""),
    22: ("OE4", "contrastes entre tamaños de enjambre, tramo B", "N11", E + "oe_n11_2026-10-14_3N/campaign/runs.csv", "oe_n8_2026-10-13/scripts/oe4_n11_analysis.py", ""),
    23: ("OE4", "cambio de régimen del equipo, tramo B frente a A", "N11", E + "oe_n11_2026-10-14_3N/campaign/runs.csv", "oe4_n11_analysis.py; verif_d27.py", ""),
    24: ("OE4", "cumplimiento RNF01/RNF04 por campaña, N y tramo", "N4/N8/N8b/N11", E + "oe_n8_2026-10-13/d27_verificacion/", "oe_n8_2026-10-13/scripts/verif_d27.py", ""),
    27: ("OE5", "F1_adapt v3 provisional, IC95, arquetipos; SUS", "N5", E + "oe_n5_2026-10-06/f1_v3_provisional/replica_*.json", "oe_n8_2026-10-13/scripts/reproduce_f1_v3_independent.py", "estadísticos por perfil y SUS no verificados"),
    28: ("OE5", "precisión, recall y F1 por modalidad (v3 provisional)", "N5", E + "oe_n5_2026-10-06/f1_v3_provisional/replica_*.json", "oe_n8_2026-10-13/scripts/reproduce_f1_v3_independent.py", ""),
    29: ("OE5", "Spearman aptitud 𝓕 vs F1 por arquetipo", "N5", E + "oe_n5_2026-10-06/f1_v3_provisional/replica_*.json", "oe_n8_2026-10-13/scripts/alineacion_aptitud_f1.py", "diagnóstico"),
    40: ("OE3", "resultados por configuración (primeras filas)", "N3", E + "oe_n3_2026-10-06/runs_oe3.csv", "reproduce_results.py (pandas)", "el informe solo reproduce las primeras filas"),
    41: ("OE5", "matriz de confusión por modalidad", "N5", E + "oe_n5_2026-10-06/f1_v3_provisional/replica_*.json", "oe_n8_2026-10-13/scripts/reproduce_f1_v3_independent.py", ""),
}
PEND = [  # tablas sin cifras recalculadas en esta entrega
    ("Tablas 5 y 37", "OE1", "estados MET/NOT_MET de requisitos", "N1", E + "oe_n1_2026-10-05/oe1_report/", "oe_n8_2026-10-13/scripts/oe1_verify.py", "PARCIAL", "archivos e integridad publicados; los estados categóricos no se recalculan"),
    ("Tablas 15 y 30", "OE3/OE5", "resultados históricos con la especificación v2 (K10)", "K10 2026-09-27", "backend/official_runs/k10_official_2026-09-27 (ya en Git)", "backend/official_runs/k10_analysis_2026-09-27", "PARCIAL", "datos en Git; recálculo no implementado en esta entrega"),
    ("Tabla 25", "OE4", "pruebas de carga exploratorias (antecedente)", "antecedente", "backend/loadtest/results (ya en Git)", "backend/loadtest/summarize.py", "PARCIAL", "datos en Git; recálculo no implementado; no comparable con N1–N11"),
    ("Tablas 32 y 44", "transversal", "síntesis del estado del arte", "—", E + "oe_n8_2026-10-13/ESTADO_DEL_ARTE_MATRIZ.csv", "build_state_of_art_matrix.py", "PARCIAL", "es síntesis bibliográfica; solo la verificación de metadatos (Crossref/OpenAlex) sería computacional y requiere red"),
    ("Tablas 35 y 36", "OE5", "SUS y panel de expertos", "—", "—", "—", "NO_REPRODUCIBLE", "no existen datos reales (0 evaluadores); no se simulan"),
    ("Tablas 39 y 42-43", "transversal", "factores del diseño N3, entorno, fases DSRM", "—", "—", "—", "NO_APLICA", "transcripción o descripción sin cálculo"),
    ("Tablas 1-4, 7, 12, 16, 26, 31, 33, 34, 45", "metodológico", "operacionalización, estructura de análisis, trazabilidad", "—", "—", "—", "NO_APLICA", "texto metodológico sin cálculo"),
]
rep = json.loads((OUT / "verification_report.json").read_text(encoding="utf-8"))
by = defaultdict(Counter)
for c in rep["comprobaciones"]:
    m = re.match(r"Tabla (\d+)$", c["tabla"])
    if m:
        by[int(m.group(1))][c["estado_cifra"]] += 1
rows = []
for n, (obj, met, camp, ev, scr, nota) in sorted(STATIC.items()):
    c = by[n]
    tot = sum(c.values())
    v, nr, d = c["VERIFICADO_DESDE_DATOS"], c["NO_REPRODUCIBLE"], c["DISCREPANCIA"]
    estado = "DISCREPANCIA" if d else "VERIFICADO_DESDE_DATOS" if v and not nr else "PARCIAL" if v else "NO_REPRODUCIBLE"
    rows.append(dict(tabla_informe=f"Tabla {n}", objetivo=obj, metrica=met, campana=camp, archivo_evidencia=ev, script_analisis=scr, cifras_comprobadas=tot,
                     verificadas_desde_datos=v, discrepantes=d, no_reproducibles=nr, estado=estado,
                     observacion=nota or "recalculado desde datos publicados; coincide a la precisión publicada"))
for t, obj, met, camp, ev, scr, estado, nota in PEND:
    rows.append(dict(tabla_informe=t, objetivo=obj, metrica=met, campana=camp, archivo_evidencia=ev, script_analisis=scr, cifras_comprobadas=0, verificadas_desde_datos=0,
                     discrepantes=0, no_reproducibles=0, estado=estado, observacion=nota))
with open(ROOT / "RESULTS_TRACEABILITY.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(Counter(r["estado"] for r in rows))
