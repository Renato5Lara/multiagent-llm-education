"""Contexto de cálculo por tabla del informe: fuente, script, fórmula, política de redondeo, unidad y tamaño de muestra.
Todo está derivado de los scripts y datos publicados (no inventado): cada entrada indica el archivo y la función que produce el valor."""
import re

N8 = "oe_n8_2026-10-13"
CTX = {  # tabla -> dict
    6: dict(oe="OE1", camp="N1", archivos=[f"{N8}/oe1_verify/oe1_verify.json", "oe_n1_2026-10-05/oe3_run/raw_observations.csv", "oe_n1_2026-10-05/oe4_run/raw_observations.csv"],
            script=f"{N8}/scripts/oe1_verify.py", formula="Spearman ρ y Kendall τb entre el puntaje de cumplimiento y la variable de desempeño, por condición (n = 14 condiciones); p bilateral", n="14 condiciones"),
    8: dict(oe="OE2", camp="N2", archivos=["oe_n2_2026-10-05/campaign/runs.csv"], script="scripts/reproduce_results.py (pandas)", formula="media aritmética de la columna indicada sobre las corridas status=ok de cada sistema×carga", n="10 corridas por celda"),
    9: dict(oe="OE2", camp="N2", archivos=["oe_n2_2026-10-05/campaign/runs.csv"], script=f"{N8}/scripts/oe2_reanalysis.py", formula="Welch sobre log(x) por carga y métrica; razón = exp(diferencia de medias log); IC95 con gl de Welch; p ajustado por Holm (m = 8)", n="10 vs 10 corridas"),
    10: dict(oe="OE2", camp="N2", archivos=["oe_n2_2026-10-05/campaign/runs.csv"], script=f"{N8}/scripts/oe2_reanalysis.py", formula="diferencia absoluta de medias; g de Hedges sobre log; Mann-Whitney bilateral con Holm (m = 8)", n="10 vs 10 corridas"),
    11: dict(oe="OE2", camp="N9b", archivos=["oe_n9b_2026-10-14/campaign_final/runs.csv"], script=f"{N8}/scripts/oe2_aux_analysis.py", formula="Welch sobre log por comparador, carga y métrica; razón, IC95 y p de Holm (m = 8)", n="10 vs 10 corridas"),
    13: dict(oe="OE3", camp="N3", archivos=["oe_n3_2026-10-06/runs_oe3.csv"], script="adaptation_swarm.oe.factorial (ANOVA tipo III, permutación Freedman–Lane)", formula="T_conv: media geométrica por nivel; k_stop, brecha y mensajes: media aritmética; η² parcial y p por permutación del ANOVA 2×2×2×2×3", n="240 corridas (48 condiciones × 5 lotes)"),
    14: dict(oe="OE3", camp="N3", archivos=["oe_n3_2026-10-06/runs_oe3.csv"], script=f"{N8}/scripts/oe3_reanalysis.py", formula="ANOVA factorial (statsmodels) sobre log(T_conv) y sobre la brecha: η² parcial y p de Holm por término", n="240 corridas"),
    17: dict(oe="OE4", camp="N4", archivos=["oe_n4_2026-10-06/campaign/runs.csv", "oe_n4_2026-10-06/inprocess/raw_observations.csv"], script="scripts/reproduce_results.py (pandas)", formula="media aritmética por carga sobre corridas status=ok; k_stop = media de las 3000 observaciones in-process", n="10 corridas por carga"),
    18: dict(oe="OE4", camp="N8", archivos=["oe_n8_2026-10-13/campaign/runs.csv"], script=f"{N8}/scripts/oe4_nvar_analysis.py", formula="media aritmética por N y carga", n="10 corridas por celda"),
    19: dict(oe="OE4", camp="N8", archivos=["oe_n8_2026-10-13/campaign/runs.csv"], script=f"{N8}/scripts/oe4_nvar_analysis.py", formula="Welch sobre log, N=30 vs N=10 por carga; Holm (m = 6 por métrica)", n="10 vs 10 corridas"),
    20: dict(oe="OE4", camp="N8b", archivos=["oe_n10_2026-10-14_n20/campaign/runs.csv"], script="scripts/reproduce_results.py (pandas)", formula="media aritmética por carga sobre corridas status=ok", n="10 corridas por carga"),
    21: dict(oe="OE4", camp="N11", archivos=["oe_n11_2026-10-14_3N/campaign/runs.csv"], script=f"{N8}/scripts/oe4_n11_analysis.py", formula="media por N y carga en el tramo B; entre paréntesis, número de corridas válidas", n="8–10 corridas por celda"),
    22: dict(oe="OE4", camp="N11", archivos=["oe_n11_2026-10-14_3N/campaign/runs.csv"], script=f"{N8}/scripts/oe4_n11_analysis.py", formula="Welch sobre log entre tamaños de enjambre, tramo B; Holm (m = 18 por métrica)", n="8–10 vs 8–10 corridas"),
    23: dict(oe="OE4", camp="N11", archivos=["oe_n11_2026-10-14_3N/campaign/runs.csv"], script=f"{N8}/scripts/oe4_n11_analysis.py; {N8}/scripts/verif_d27.py", formula="razón de medias geométricas tramo B / tramo A (por N y todos los N) y p de Welch", n="5–6 (tramo A) vs 53–55 (tramo B)"),
    24: dict(oe="OE4", camp="N4/N8/N8b/N11", archivos=["oe_n4_2026-10-06/campaign/runs.csv", "oe_n8_2026-10-13/campaign/runs.csv", "oe_n10_2026-10-14_n20/campaign/runs.csv", "oe_n11_2026-10-14_3N/campaign/runs.csv"], script=f"{N8}/scripts/verif_d27.py", formula="recuento de corridas con throughput ≥ 20 req/s y con P95 < 2 s, y cargas cuya media los cumple (RNF04 y RNF01)", n="corridas HTTP válidas por campaña, N y tramo"),
    27: dict(oe="OE5", camp="N5", archivos=["oe_n5_2026-10-06/f1_v3_provisional/replica_*.json"], script=f"{N8}/scripts/reproduce_f1_v3_independent.py", formula="F1_adapt = media de las medias por réplica (K = 10); IC95 con t de 9 gl; F1 por arquetipo", n="10 réplicas × 100 perfiles = 1000 casos"),
    28: dict(oe="OE5", camp="N5", archivos=["oe_n5_2026-10-06/f1_v3_provisional/replica_*.json"], script=f"{N8}/scripts/reproduce_f1_v3_independent.py", formula="precisión = TP/(TP+FP); recall = TP/(TP+FN); F1 = 2PR/(P+R), uno-contra-resto por modalidad", n="1000 casos"),
    29: dict(oe="OE5", camp="N5", archivos=["oe_n5_2026-10-06/f1_v3_provisional/replica_*.json"], script=f"{N8}/scripts/alineacion_aptitud_f1.py", formula="Spearman entre la aptitud F del mejor global y el F1 por caso", n="1000 casos (≈250 por arquetipo)"),
    40: dict(oe="OE3", camp="N3", archivos=["oe_n3_2026-10-06/runs_oe3.csv"], script="scripts/reproduce_results.py (pandas)", formula="media y desviación (ddof=1) de las 5 corridas por condición", n="5 corridas por condición"),
    41: dict(oe="OE5", camp="N5", archivos=["oe_n5_2026-10-06/f1_v3_provisional/replica_*.json"], script=f"{N8}/scripts/reproduce_f1_v3_independent.py", formula="matriz de confusión uno-contra-resto por modalidad (VP, FP, FN, VN = 1000 − VP − FP − FN)", n="1000 casos"),
}


def unidad(encabezado: str) -> str:
    m = re.search(r"\(([^)]*(?:ms|req/s|s|%|puntos)[^)]*)\)", encabezado or "")
    if m:
        return m.group(1)
    h = (encabezado or "").lower()
    for k, u in (("throughput", "req/s"), ("p95", "ms"), ("p50", "ms"), ("media", "ms"), ("t_conv", "ms"), ("razón", "razón adimensional"), ("p de", "probabilidad"), ("p ajustado", "probabilidad"),
                 ("η²", "proporción de varianza"), ("hedges", "tamaño de efecto (g)"), ("precisión", "proporción"), ("recall", "proporción"), ("f1", "proporción"), ("spearman", "coeficiente de correlación")):
        if k in h:
            return u
    return ""


def politica(valor: str) -> str:
    """Política de redondeo inferida de la propia cifra publicada: decimales del informe, mitad hacia arriba sobre el valor sin redondear."""
    if "×" in valor:
        return "notación científica, 2 cifras significativas, mitad hacia arriba"
    m = re.search(r",(\d+)|\.(\d+)", valor)
    d = len((m.group(1) or m.group(2))) if m else 0
    return f"{d} decimales, mitad hacia arriba sobre el valor sin redondear" if d else "entero (recuento o redondeo a la unidad), mitad hacia arriba"
