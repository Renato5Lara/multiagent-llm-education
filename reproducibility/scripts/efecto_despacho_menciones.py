"""Inventario de todas las menciones del efecto del despacho por lotes sobre T_conv en la tesis (D2.9.7), con su respaldo por campaña.

La búsqueda en el DOCX se hizo con patrones («37 %», «60 %», 56,8 / 90,6, etc.) sobre los párrafos que mencionan despacho/lotes/secuencial/concurrente;
aquí se registra el resultado. Respaldo: outputs/oe3_despacho.json (una sola definición: 1 − 1/R, R = GM secuencial / GM por lotes)."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
d = json.loads((ROOT / "outputs/oe3_despacho.json").read_text(encoding="utf-8"))
resp = "N3 {:.1f} % (IC95 {:.1f}–{:.1f}); N3-R {:.1f} % ({:.1f}–{:.1f}); N3-S {:.1f} % ({:.1f}–{:.1f})".format(
    *[v for k in ("N3", "N3R", "N3S") for v in (d[k]["reduccion_por_lotes_pct"], *d[k]["reduccion_ic95_entre_lotes_pct"])])
FIL = [
 ("56", "resumen", "El despacho concurrente redujo el tiempo de convergencia en torno a 37 %", "valor de N3 sin calificar", "especificar «en N3» y añadir que en réplicas posteriores fue ≈ 32 %"),
 ("64", "abstract (inglés)", "Concurrent dispatch reduced convergence time by about 37 %", "valor de N3 sin calificar", "igual que el resumen"),
 ("1293", "§6.5.4", "el despacho secuencial aumentó el T_conv alrededor de 60 % (el despacho por lotes lo redujo cerca de 37 %)", "ambas cifras son de N3 (+59,7 % y −37,4 %; mismo efecto, distinto denominador)", "indicar «en N3» y que en N3-R/N3-S fueron +47–48 % y −32 %"),
 ("1332", "§6.5.5 (tabla)", "despacho por lotes 56,8 frente a secuencial 90,6 (T_conv, ms)", "medias geométricas de N3 (Tabla 13): coinciden", "ninguna (es el dato de N3)"),
 ("2009", "§6.5.6 (tabla)", "Despacho concurrente −37 % de T_conv", "valor de N3 sin calificar", "añadir «(N3)»"),
 ("2047", "§6.7 síntesis", "el despacho concurrente lo redujo en torno a 37 %", "valor de N3 sin calificar", "añadir «en N3; ≈ 32 % en las réplicas»"),
 ("2058", "§6.7 B2.2", "el despacho concurrente redujo el tiempo de convergencia en torno a 37 %", "valor de N3 sin calificar", "ídem"),
 ("2063", "§6.7 B3.2", "el despacho concurrente redujo el tiempo de convergencia en torno a 37 % (η² parcial = 0,98)", "valor y η² de N3 (Tabla 14) sin calificar", "ídem; el η² es de N3"),
 ("2093", "§7.1 OE3", "El despacho concurrente redujo el T_conv en torno a 37 % (η² parcial = 0,98)", "valor y η² de N3 sin calificar", "ídem (ver C1/C4)"),
 ("3229", "Anexo (matriz de objetivos)", "Despacho concurrente −37 % de T_conv", "valor de N3 sin calificar", "añadir «(N3)»"),
]
with open(ROOT / "auditoria/EFECTO_DESPACHO_MENCIONES.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["parrafo", "seccion", "texto_minimo", "respaldo", "efecto_por_campana", "limitacion_de_inferencia", "propuesta"])
    for p, sec, txt, resp_, prop in FIL:
        w.writerow([p, sec, txt, resp_, resp, "tres campañas exploratorias de un solo equipo; los IC son dentro de cada sesión; con dos sesiones distintas no se puede cuantificar la variación entre sesiones; no se promedian", prop])
print(len(FIL), "menciones")
