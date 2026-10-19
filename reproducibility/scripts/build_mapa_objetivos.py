"""Genera auditoria/MAPA_OBJETIVOS_EVIDENCIAS.csv: objetivo literal -> indicador -> umbral -> campaña -> fuente -> script -> tabla -> estado. Estados tomados de outputs/verification_report.json."""
import csv
import json
import re
from collections import Counter

from repro_lib import ROOT

obj = json.loads((ROOT / "auditoria" / "OBJETIVOS_LITERALES.json").read_text(encoding="utf-8"))
rep = json.loads((ROOT / "outputs" / "verification_report.json").read_text(encoding="utf-8"))
st = {}
for c in rep["comprobaciones"]:
    for n in re.findall(r"\d+", c["tabla"]):
        st.setdefault(int(n), Counter())[c["estado_cifra"]] += 1


def estado(*tablas):
    c = Counter()
    for n in tablas:
        c.update(st.get(n, Counter()))
    tot = sum(c.values())
    if not tot:
        return "SIN_COMPROBACIONES"
    v = c["VERIFICADO_DESDE_DATOS"] + c["VERIFICADO_DESDE_DERIVADO"]
    return f"{v}/{tot} cifras verificadas" + (f" ({c['VERIFICADO_DESDE_DERIVADO']} desde derivado)" if c["VERIFICADO_DESDE_DERIVADO"] else "") + (f"; {c['NO_REPRODUCIBLE']} no reproducibles" if c["NO_REPRODUCIBLE"] else "") + (f"; {c['DISCREPANCIA']} DISCREPANTES" if c["DISCREPANCIA"] else "")


N8 = "oe_n8_2026-10-13/scripts/"
R = []   # oe, indicador, umbral, campaña, fuente, script, tablas, evidencia, estado, limitaciones, accion
R += [("OE1", "Estado MET/NOT_MET de RF01–RF06, REL-C, REL-D y RNF01–RNF05", "RF = 100 %; REL-C ≥ 99 %; RNF01 P95 < 2 000 ms; RNF02 k_stop ≤ 15 ∧ CR ≥ 98 %; RNF03 F1 ≥ 0,85; RNF04 ≥ 20 req/s ∧ error < 1 %; RNF05 SUS > 75", "N1",
       "oe_n1_2026-10-05/oe1_report/oe1_report.json; oe3_run|oe4_run/raw_observations.csv", f"adaptation_swarm.oe.oe1; {N8}oe1_verify.py", "Tablas 5 y 37", "estados categóricos copiados de oe1_report; integridad del archivo verificada (Tabla 36)",
       "VERIFICACION_PARCIAL (estados no recalculados; ver cifras en prosa)", "puntaje de cumplimiento sin definición aprobada; N1 no oficial", "recalcular cada estado desde las observaciones con una regla aprobada del puntaje"),
      ("OE1", "RNF01 (P95 en proceso), RF03, recuentos de ciclos", "RNF01 P95 < 2 000 ms", "N1", "oe_n1_2026-10-05/oe3_run|oe4_run/raw_observations.csv", "scripts/reproduce_results.py (prosa_oe1)", "§6.5.3, §6.7, §7.1 (prosa)",
       "8 cifras en prosa recalculadas: P95 1 319 ms (8 700 obs.), P95 2 214,8 ms con 25 usuarios, 82 %, 72 %, 9 500 ciclos, RF03 90,5 %, 8 600 ciclos", "VERIFICADO_DESDE_DATOS (8/8)", "RNF01 solo en proceso y en el agregado (82 % con 1 usuario)", "ninguna"),
      ("OE1", "Asociación entre puntaje de cumplimiento y desempeño (Spearman, Kendall)", "—", "N1", "oe_n1_2026-10-05/oe3_run|oe4_run/raw_observations.csv", f"{N8}oe1_verify.py", "Tabla 6", estado(6) + "; la fila «usuarios frente al propio puntaje» no está en oe1_verify.json",
       "PARCIAL", "n = 14 condiciones; confundida con la carga; no causal", "localizar el cálculo de la fila de usuarios")]
R += [("OE2", "Latencia (P50, media, P95) y throughput de la propuesta y de decision_table por carga", "P95 < 2,0 s (componente L_resp de H1)", "N2", "oe_n2_2026-10-05/campaign/runs.csv + raw", "scripts/reproduce_results.py; summarize_run", "Tablas 8 y 38", estado(8, 38), "VERIFICADO_DESDE_DATOS (hasta los registros por petición)",
       "decision_table es un sistema convencional definido operacionalmente en el estudio", "ninguna"),
      ("OE2", "Razón geométrica P95/throughput propuesta÷decision_table; Welch, Holm, Mann-Whitney, g de Hedges", "—", "N2", "oe_n2_2026-10-05/campaign/runs.csv", f"{N8}oe2_reanalysis.py", "Tablas 9 y 10", estado(9, 10), "VERIFICADO_DESDE_DATOS", "no oficial; hardware local", "ninguna"),
      ("OE2", "Razón enjambre÷{decision_table, rules, bruteforce}", "—", "N9b", "oe_n9b_2026-10-14/campaign_final/runs.csv + raw", f"{N8}oe2_aux_analysis.py", "Tabla 11", estado(11), "VERIFICADO_DESDE_DATOS", "rules = ablación; bruteforce = referencia de optimalidad; N9 abortada no usada", "ninguna")]
R += [("OE3", "T_conv, k_stop, brecha y mensajes por factor (despacho, difusión de g_best, heurística, réplicas, mecanismo)", "meta: CR ≥ 98 %", "N3", "oe_n3_2026-10-06/run/raw_observations.csv → runs_oe3.csv", "adaptation_swarm.oe.factorial; scripts/reproduce_results.py", "Tablas 13 y 40", estado(13, 40) + "; 3 cifras con doble redondeo en el informe",
       "VERIFICADO_DESDE_DATOS (con 3 diferencias de 1 unidad explicadas)", "ANOVA ejecutado; Friedman/Holm planeado no ejecutado; celdas «sin efecto» no verificadas", "corregir 0,50→0,49; 1,51→1,50; 76,5→76,4 (REGISTRO_CAMBIOS_TESIS.csv)"),
      ("OE3", "ANOVA factorial: η² parcial y p de Holm por término", "—", "N3", "oe_n3_2026-10-06/runs_oe3.csv", f"{N8}oe3_reanalysis.py", "Tabla 14", estado(14), "VERIFICADO_DESDE_DATOS", "en proceso; no oficial", "ninguna"),
      ("OE3", "Convergencia del enjambre (CR, k_stop) con la especificación v2", "CR ≥ 98 % (Meta 3); k_stop ≤ 15 (Meta 4)", "K10 (2026-09-27)", "backend/official_runs/k10_official_2026-09-27/replica_*.json", "scripts/reproduce_results.py", "Tabla 15", estado(15), "VERIFICADO_DESDE_DATOS", "resultado histórico (v2); regla de agregación de CR sin definir; T_conv no reportado", "definir la regla de agregación de CR")]
R += [("OE4", "Latencia, throughput y T_conv por carga con N = 20", "P95 < 2,0 s; ≥ 20 req/s", "N4", "oe_n4_2026-10-06/campaign/runs.csv + raw; inprocess/raw_observations.csv", "scripts/reproduce_results.py", "Tabla 17", estado(17), "VERIFICADO_DESDE_DATOS", "hardware local; no oficial", "ninguna"),
      ("OE4", "Efecto del tamaño del enjambre (N = 10, 20, 30) por carga", "—", "N8, N8b, N11", "oe_n8_2026-10-13/campaign/runs.csv; oe_n10_2026-10-14_n20; oe_n11_2026-10-14_3N", f"{N8}oe4_nvar_analysis.py; oe4_n11_analysis.py", "Tablas 18–23", estado(18, 19, 20, 21, 22, 23),
       "VERIFICADO_DESDE_DATOS", "N11 con dos tramos de régimen distinto; 1 corrida no_requests excluida; no oficial", "ninguna"),
      ("OE4", "Cumplimiento de RNF01 (P95 < 2 s) y RNF04 (≥ 20 req/s) por campaña, N y tramo", "P95 < 2 s; ≥ 20 req/s", "N4, N8, N8b, N11", "runs.csv de las cuatro campañas", f"{N8}verif_d27.py", "Tabla 24", estado(24), "VERIFICADO_DESDE_DATOS", "condiciones objetivo (8 vCPU / 32 GB en la nube) no ejecutadas", "ejecutar en condiciones objetivo"),
      ("OE4", "Pruebas de carga exploratorias de antecedente (Locust y JMeter)", "—", "antecedente 2026-09-23", "backend/loadtest/results", "scripts/reproduce_results.py (tabla_25)", "Tabla 25", estado(25), "VERIFICADO_DESDE_DATOS (Locust) y DESDE_DERIVADO (JMeter)", "no comparable con N1–N11", "ninguna")]
R += [("OE5", "F1_adapt, precisión, recall por modalidad y arquetipo (especificación v3 PROVISIONAL)", "F1_adapt ≥ 0,85 (límite inferior del IC95 %)", "N5", "oe_n5_2026-10-06/f1_v3_provisional/replica_*.json", f"{N8}reproduce_f1_v3_independent.py; alineacion_aptitud_f1.py", "Tablas 27–29 y 41", estado(27, 28, 29, 41),
       "VERIFICADO_DESDE_DATOS (la meta 0,85 no se alcanza)", "v3 provisional; perfiles sintéticos; estadísticas por perfil de la Tabla 27 no recalculadas", "validar la matriz gold con el panel de expertos"),
      ("OE5", "F1_adapt con la especificación v2 (histórico K10)", "F1_adapt ≥ 0,85", "K10", "backend/official_runs/k10_official_2026-09-27/replica_*.json", "scripts/reproduce_results.py", "Tabla 30", estado(30), "VERIFICADO_DESDE_DATOS (modalidades desde derivado)", "otra definición de la métrica", "ninguna"),
      ("OE5", "Usabilidad SUS (> 75, n ≥ 10) y acuerdo del panel (AC1)", "SUS > 75; n ≥ 10 evaluadores", "—", "—", "—", "Tablas 27 (fila SUS), 35", "0 evaluadores reales: no existen datos", "NO_REPRODUCIBLE / PENDIENTE_DE_EVIDENCIA",
       "no se simulan respuestas SUS ni evaluaciones de expertos", "aplicar el cuestionario SUS y el panel con evaluadores reales")]
with open(ROOT / "auditoria" / "MAPA_OBJETIVOS_EVIDENCIAS.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["codigo_objetivo", "formulacion_literal", "problema_e_hipotesis", "variable_indicador", "umbral_o_criterio_aprobado", "campana", "archivo_fuente", "script_calculo", "tabla_o_figura_tesis", "evidencia_disponible", "estado_reproducibilidad", "limitaciones", "accion_necesaria"])
    for oe, ind, um, camp, fu, sc, tb, ev, es, lim, acc in R:
        hip = "H1 general: F1 ≥ 0,85, L_resp < 2,0 s, SUS > 75 (OE5 contrasta F1 y SUS; OE4 mide L_resp; OE2 la compara con el convencional)" if oe in ("OE2", "OE4", "OE5") else "sin hipótesis estadística formulada (pendiente)"
        w.writerow([oe, obj["objetivos"][oe], hip, ind, um, camp, fu, sc, tb, ev, es, lim, acc])
print(len(R), "filas")
