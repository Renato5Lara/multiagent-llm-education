"""Registro de las afirmaciones prioritarias de la tesis (resumen, conclusiones §7.1 y recomendaciones §8), una por fila, con tipo, fuente, método y estado.

Cada estado resulta de una comprobación manual hecha contra los resultados recalculados del paquete (verificación_report.json, VERIFICACION_MANUAL.csv, tablas de outputs/);
aquí solo se registra el resultado. Estados: COINCIDE_EXACTAMENTE | COINCIDE_CON_REDONDEO | DISCREPANCIA | NO_REPRODUCIBLE | PENDIENTE_DE_REVISION | NO_APLICA.
Un estado «COINCIDE» se refiere al VALOR o recuento; la columna `limitacion` dice qué parte de la oración no se verifica (condición, comparación, interpretación).
Los textos citados son fragmentos mínimos de identificación (no se publica el texto completo de la tesis).
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CE, CR, DI, NR, PE, NA = "COINCIDE_EXACTAMENTE", "COINCIDE_CON_REDONDEO", "DISCREPANCIA", "NO_REPRODUCIBLE", "PENDIENTE_DE_REVISION", "NO_APLICA"
DATO, DER, INT, COMP, MET = "dato observado", "cálculo derivado", "interpretación", "comparación", "afirmación metodológica"
V = "VERIFICACION_MANUAL.csv"
# (id, ubicación, fragmento, tipo, fuente y método, estado, limitación, acción)
R = [
 ("A01", "resumen, párr. 56", "no registró errores en 419 corridas HTTP válidas", DATO, f"{V} M1: runs.csv de N4, N8, N8b, N11 (status ok): 419 filas, 0 errores, 0 timeouts", CE, "solo campañas HTTP del OE4; N11 excluye 1 corrida no_requests por regla", "ninguna"),
 ("A02", "resumen, párr. 56", "cumplió los requerimientos funcionales y de confiabilidad en su configuración de referencia", INT, "Tabla 37 recalculada (N1): RF01, RF02, RF04, RF05, REL-C = 100 %; RF03 = 100 % con despacho concurrente (8 600/8 600); RF06 y REL-D no recalculables", PE, "RF02–RF05 se apoyan en banderas del arnés; RF06 (sonda de persistencia) y REL-D (sonda de determinismo) solo constan en el informe del propio arnés; RF03 no se cumple en el conjunto", "matizar: «con la salvedad de que RF06 y REL-D solo constan en el informe del arnés»"),
 ("A03", "resumen, párr. 56", "su P95 fue de 3,9 a 21,7 veces mayor y su throughput menor", COMP, f"{V} M11: razones de P95 propuesta/decision_table de N2 (Tabla 9) y N9b (Tabla 11): 3,92 a 21,74", CR, "unión de dos campañas (N2, N9b) que no se combinan estadísticamente; decision_table es un comparador definido por el estudio", "ninguna; mantener la salvedad del comparador"),
 ("A04", "resumen, párr. 56", "el P95 fue indistinguible y el throughput, de 1,13 a 1,51 veces mayor", COMP, f"{V} M13: razón de throughput propuesta/bruteforce 1,13–1,51; IC95 % del P95 incluye 1 en las 4 cargas", CR, "«indistinguible» = el IC95 % incluye 1, no equivalencia demostrada; sin calidad de la solución", "ninguna"),
 ("A05", "resumen, párr. 56", "El despacho concurrente redujo el tiempo de convergencia en torno a 37 %", DER, f"{V} M5: 1 − GM(T_conv por lotes)/GM(secuencial) = 37,4 % en N3 (razón secuencial/lotes 1,60); en N3-R 32,2 % (1,47) y en N3-S 32,5 % (1,48), con las mismas semillas que N3 (scripts/oe3_replicacion.py, oe3_sesion.py)", CR, "el 37 % corresponde a la sesión de N3; en la sesión posterior (N3-R y N3-S) el efecto es ≈ 32 %: la magnitud del efecto del despacho depende de la sesión, aunque su sentido y su dominio se mantienen; exploratorio, N = 20, 1 usuario", "especificar «en N3» y mencionar que una réplica con las mismas semillas dio ≈ 32 %"),
 ("A06", "resumen, párr. 56", "P95 inferior a 2 s hasta 10 usuarios y, con 25 usuarios, solo con un enjambre de 10 partículas", DATO, f"{V} M3 (210 corridas con ≤ 10 usuarios, máx. 1 954 ms) y M4 (25 usuarios: 8 de 9 corridas con N = 10 en el tramo B; 0 de 61 en el resto)", CE, "«en un régimen del equipo» es interpretación; hardware local", "ninguna"),
 ("A07", "resumen, párr. 56", "20 req/s se alcanzaron solo en 18 corridas aisladas", DATO, f"{V} M2: 18 de 419 corridas con throughput_rps ≥ 20, todas N = 10 del tramo B de N11", CE, "«aisladas» es interpretación", "ninguna"),
 ("A08", "resumen, párr. 56", "El F1_adapt con la especificación v3 provisional fue de 0,8156, inferior a 0,85", DER, "Tabla 27 recalculada desde las 10 réplicas de N5 (1 000 casos), reproducción independiente: 0,8156 (IC95 % 0,8111–0,8201)", CE, "especificación v3 provisional; perfiles sintéticos; gold sin validar por panel", "ninguna"),
 ("A09", "resumen, párr. 56", "la usabilidad no se midió por falta de evaluadores", MET, "Tablas 27/35: 0 respuestas SUS (no existen datos)", CE, "ninguna", "ninguna"),
 ("A10", "§7.1, párr. 2087", "El objetivo general se cumple de forma parcial", INT, "contraste con la meta de H1 (F1 ≥ 0,85; L_resp < 2,0 s; SUS > 75): F1 no alcanzado; P95 < 2 s solo hasta 10 usuarios; SUS no medido", CE, "«parcial» es un juicio; es coherente con los datos y no exagera", "ninguna"),
 ("A11", "§7.1, párr. 2087", "capacidad casi fija", DER, "throughput medio por carga (N4, N8, N8b, N11): estable desde 5 usuarios (≈ 11 / 16 / 19 req/s según N y campaña; ±5 %)", CR, "descriptivo; la causa de la capacidad fija no se investigó", "ninguna"),
 ("A12", "§7.1, párr. 2087", "La hipótesis general … no puede declararse confirmada", INT, "F1 0,8156 < 0,85; P95; SUS no medido", CE, "ninguna", "ninguna"),
 ("A13", "§7.1, párr. 2089 (OE1)", "RF03 se verificó en 8 600 de 8 600 ciclos con despacho concurrente y falló solo en la ablación secuencial (8 600 de 9 500 en el conjunto)", DATO, "Tabla 37 recalculada: RF03 = 0,9053 (8 600/9 500); 0/900 con despacho secuencial", CE, "banderas inflight_overlap del arnés", "ninguna"),
 ("A14", "§7.1, párr. 2089 (OE1)", "RNF01 se cumplió solo en el agregado en proceso (P95 de 1 319 ms, con el 82 % de las observaciones con 1 usuario) y no con 25 usuarios (2 214,8 ms)", DATO, "prosa recalculada del OE1 desde los 9 500 ciclos de N1 (reproduce_results.prosa_oe1)", CE, "en proceso, sin HTTP", "ninguna"),
 ("A15", "§7.1, párr. 2089 (OE1)", "RNF04 no se cumplió en proceso (14,98 req/s)", DATO, "no recalculable: no hay batches.json de N1 entre los datos publicados (T37-RNF04 no reproducible)", NR, "la cifra solo consta en el informe del arnés", "incorporar batches.json de N1 o declarar la cifra como transcrita"),
 ("A16", "§7.1, párr. 2089 (OE1)", "RNF03 no alcanza 0,85 (v2: 0,6407; v3 provisional: 0,8156)", DATO, "Tabla 37 (RNF03 desde el resumen K10) y Tabla 27 recalculadas", CE, "v2 es histórico; v3 provisional", "ninguna"),
 ("A17", "§7.1, párr. 2089 (OE1)", "ρ = −0,69; n = 14 … confundida con la carga y no es causal", DER, "Tabla 6 recalculada (oe1_verify): ρ = −0,6916; n = 14 condiciones; ρ usuarios–puntaje = −0,608", CE, "«confundida con la carga» es interpretación respaldada por la correlación con los usuarios", "ninguna"),
 ("A18", "§7.1, párr. 2091 (OE2)", "las ocho diferencias significativas tras Holm en cada una", DER, "Tablas 9 y 11 recalculadas: 8/8 con p de Holm < 0,05 en N2 y 8/8 en N9b (decision_table); también 8/8 frente a rules", CE, "significación estadística; no equivale a relevancia práctica", "ninguna"),
 ("A19", "§7.1, párr. 2091 (OE2)", "frente a rules, ablación del propio sistema, el resultado fue equivalente", COMP, "razones frente a rules (P95 3,87–14,71; throughput 0,084–0,216) similares a las de decision_table (3,92–14,68; 0,084–0,213); no se ejecutó una prueba de equivalencia", PE, "«equivalente» es más fuerte que «similar»; no hay prueba de equivalencia (TOST)", "cambiar «equivalente» por «similar» o ejecutar una prueba de equivalencia con margen aprobado"),
 ("A20", "§7.1, párr. 2091 (OE2)", "significativo con 5, 10 y 25 usuarios", DER, f"{V} M14: p de Holm del throughput frente a bruteforce < 0,05 en 5, 10 y 25 usuarios (0,019; 0,019; 0,032) y no en 1 (0,283)", CE, "exploratorio, campaña no oficial", "ninguna"),
 ("A21", "§7.1, párr. 2093 (OE3)", "El OE3 queda demostrado experimentalmente bajo las condiciones ejecutadas", INT, "evidencia: N3, N3-R y N3-S (efectos replicados, exploratorios; CR = 100 %); sin hipótesis aprobada, sin ejecución oficial, N = 20, 1 usuario, un equipo", DI, "la expresión «demostrado» excede la evidencia: campañas exploratorias y no oficiales, sin hipótesis formulada", "reformular (ver PROPUESTA_CORRECCIONES_CONCLUSIONES.md, C1)"),
 ("A22", "§7.1, párr. 2093 (OE3)", "el despacho concurrente redujo el T_conv en torno a 37 % (η² parcial = 0,98)", DER, "ANOVA de N3 (Tabla 14) y M5", CR, "η² = 0,98 es de N3; N3-R/N3-S no se incorporan a la tabla", "ninguna"),
 ("A23", "§7.1, párr. 2093 (OE3)", "la heurística de arranque de AG1 redujo las iteraciones y la brecha", DER, "scripts/oe3_eficiencia.py: k_stop −21 %, brecha −42 % en N3 (mismo veredicto «domina» en N3-R y N3-S)", CR, "descriptivo (cambio relativo de medias)", "ninguna"),
 ("A24", "§7.1, párr. 2093 (OE3)", "la difusión de g_best añadió unos 13 ms y 11 mensajes sin mejorar la calidad", DER, f"{V} M6 (12,94 ms; 10,83 mensajes) y oe3_eficiencia (brecha sin cambio, 0 %)", CR, "ninguna", "ninguna"),
 ("A25", "§7.1, párr. 2093 (OE3)", "las réplicas de consumidores tuvieron un efecto mínimo", DER, "oe3_eficiencia: T_conv −1,3 %; brecha y k_stop sin cambio; en pruebas por rangos pareadas el efecto es significativo pero ≈ 1 %", CE, "ninguna", "ninguna"),
 ("A26", "§7.1, párr. 2093 (OE3)", "el menor T_conv del mecanismo cognitivo corresponde a una búsqueda truncada con más del doble de brecha", DER, "oe3_eficiencia: cognitivo k_stop = 1 (−52 %), T_conv −17 %, brecha +123 % (2,23 ×)", CE, "ninguna", "ninguna"),
 ("A27", "§7.1, párr. 2095 (OE4)", "El OE4 queda demostrado experimentalmente bajo las condiciones ejecutadas", INT, "evidencia: N4, N8, N8b, N11 (491 cifras recalculadas); hardware local; condiciones objetivo no ejecutadas; no oficial", DI, "misma expresión que A21: «demostrado» excede la evidencia exploratoria y local", "reformular (C2)"),
 ("A28", "§7.1, párr. 2095 (OE4)", "El throughput se estabilizó desde 5 usuarios y la latencia creció en proporción a la carga", DER, "runs.csv: throughput medio por carga plano desde 5 usuarios (±5 %) y P95/usuarios ≈ 79–89 ms por usuario con N = 10 de N11 (u ≥ 5)", CR, "descriptivo; u = 1 no sigue la proporción", "ninguna"),
 ("A29", "§7.1, párr. 2095 (OE4)", "N = 30 frente a N = 10: P95 ×1,22–1,38; throughput ×0,68–0,79", COMP, "Tablas 21–22 recalculadas (N11, tramo B)", CE, "campaña única N11; tramo B", "ninguna"),
 ("A30", "§7.1, párr. 2095 (OE4)", "≈ ×1,62 en throughput … cambio de régimen del equipo … cuya causa no se aisló", DER, "Tabla 23 recalculada (tramo B/A); coherente con N3-S/N3 (la velocidad depende de la sesión; causa no identificada)", CR, "la causa sigue sin identificarse", "ninguna"),
 ("A31", "§7.1, párr. 2097 (OE5)", "F1_adapt … 0,8156 (IC95 %: 0,8111 a 0,8201), inferior a 0,85 … Se reprodujo de forma exacta", DER, "reproduce_f1_v3_independent.py: 1 000 casos, 0 discrepancias frente al F1 almacenado", CE, "v3 provisional; gold sin validar", "ninguna"),
 ("A32", "§7.1, párr. 2097 (OE5)", "no puede afirmarse que supere ni que no supere los 75 puntos", MET, "0 respuestas SUS", CE, "ninguna", "ninguna"),
 ("A33", "§8, párr. 2105 (OE3)", "sin difusión de g_best … ≈ 21 % … 16 % en promedio marginal", DER, f"{V} M7/M8: 20,9 % y 15,8 %", CR, "n = 5 lotes por configuración", "ninguna"),
 ("A34", "§8, párr. 2107 (OE4)", "N = 10 fue el más rápido pero la campaña HTTP no mide calidad", DATO, "runs.csv: N = 10 de N11 tiene el mayor throughput (≈ 19 req/s) y el menor P95; la campaña HTTP no calcula la brecha", CE, "ninguna", "ninguna"),
 ("A35", "§8, párr. 2109 (OE5)", "audio y texto concentran los falsos positivos (precisión de 0,38 y 0,61)", DATO, "Tabla 28 recalculada: audio 0,38; texto 0,61; FP 323 y 277", CE, "ninguna", "ninguna"),
 ("A36", "§8, párr. 2110", "Ejecuciones oficiales de los objetivos primero a cuarto en el hardware de 8 vCPU y 32 GB", MET, "declaración de trabajo pendiente; coincide con el estado (no ejecutadas)", CE, "ninguna", "ninguna"),
 ("A37", "§7.1, párr. 2087", "La comparación con el estado del arte es contextual y los resultados históricos no se combinan con los actuales", MET, "Tablas 32/44: bibliografía externa no verificable en el paquete", PE, "las cifras de terceros no se comprobaron contra sus fuentes", "verificar contra las fuentes originales o citar como declaradas por los autores"),
]


def main():
    out = ROOT / "auditoria" / "REGISTRO_AFIRMACIONES_PRIORITARIAS.csv"
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "ubicacion", "texto_minimo", "tipo", "fuente_y_metodo", "estado", "limitacion", "accion_recomendada"])
        w.writerows(R)
    from collections import Counter
    print(len(R), "afirmaciones;", dict(Counter(r[5] for r in R)))


if __name__ == "__main__":
    main()
