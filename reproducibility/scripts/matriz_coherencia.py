"""Matriz de coherencia de limitaciones y afirmaciones clave entre resultados, discusión, conclusiones, resumen y abstract (fase 16).

Para cada tema se busca, con una expresión regular en español y otra en inglés, si el bloque lo menciona. «SI» = el bloque dice lo que hay que decir
(limitación o cautela); «NO» = no lo dice. No mide la calidad de la redacción: una celda «SI» solo indica que el término aparece. Las celdas «NO» donde el
tema debería aparecer son los candidatos a incoherencia entre bloques.
Uso: python scripts/matriz_coherencia.py <texto_plano_de_la_copia_de_revision.txt>   (una línea por párrafo; no se publica)
Salida: auditoria/MATRIZ_COHERENCIA_ES_EN.csv
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# bloques: (nombre, líneas 1-based del texto plano; se unen todas las líneas de prosa del rango)
BLOQUES = [
    ("Resultados (6.1–6.5, presentación e interpretación)", [(417, 483), (484, 570), (571, 635), (636, 775), (776, 855)]),
    ("Discusión (6.x.6 y 6.7)", [(481, 483), (568, 570), (633, 635), (773, 775), (844, 847), (856, 907)]),
    ("Conclusiones (cap. 7)", [(908, 921)]),
    ("Resumen (ES)", [(55, 58)]),
    ("Abstract (EN)", [(63, 66)]),
]
# (tema, patrón ES, patrón EN, ¿debería estar en todos los bloques?)
TEMAS = [
    ("Campañas experimentales no oficiales", r"no oficial|experimental", r"non-official|experimental", True),
    ("Equipo distinto del hardware objetivo", r"hardware objetivo|distinto del hardware", r"target hardware|equipment other than", True),
    ("RF06 y REL-D solo según el informe del arnés (sondas no conservadas)", r"informe del arnés|sonda", r"harness report|probe", False),
    ("RF07 y RF08 no evaluados como requisitos", r"RF07|RF08", r"RF07|RF08", False),
    ("Un único comparador convencional definido por el estudio", r"único comparador|decision_table|definid[oa]s? por el estudio", r"defined by the study|static decision table", True),
    ("Sin prueba de equivalencia (similar, no equivalente)", r"sin prueba de equivalencia|similar", r"similar|equivalence", False),
    ("N3-R / N3-S (réplicas del OE3) mencionadas", r"N3-R|N3-S|réplica exploratoria", r"N3-R|N3-S", False),
    ("OE3 sin hipótesis estadística aprobada", r"sin hip[oó]tesis|no tienen hip[oó]tesis|hip[oó]tesis estad[ií]stica", r"hypothes", False),
    ("«Demostrado»/«demonstrated» aplicado a OE3 y OE4", r"demostr", r"demonstrat", False),
    ("F1_adapt v3 provisional y por debajo de 0,85", r"0,8156", r"0\.8156", True),
    ("Usabilidad (SUS) no medida; sin evaluadores", r"sin evaluadores|no hubo evaluadores|no se midi|sin respuestas|0 evaluadores|no pudo determinarse", r"lack of evaluators|not measured|no evaluators|could not", True),
    ("P95 < 2 s con 25 usuarios solo con N = 10 en un régimen del equipo", r"solo con N = 10|solo con un enjambre de 10", r"only with a 10-particle|only with N = 10", True),
    ("Cifra «8 de 9 corridas»", r"8 de 9", r"8 of 9", False),
    ("Análisis «independiente del código del artefacto, realizado por el propio proyecto»", r"realizado por el propio proyecto", r"carried out by the project itself", False),
    ("Prerregistro / sellado descrito como procedimiento oficial, no como lo ejecutado", r"prerregistro|sellad", r"preregist|seal", False),
    ("Variabilidad de T_conv (entre corridas) cuantificada", r"2,6 ms|unos 2 ms", r"2\.6 ms|about 2 ms", False),
]


def es_prosa(l):
    s = l.strip()
    return bool(s) and " | " not in s and s != "[/TABLA]"


def main(texto):
    L = Path(texto).read_text(encoding="utf-8").split("\n")
    filas = []
    for tema, pes, pen, todos in TEMAS:
        fila = [tema]
        for nombre, rangos in BLOQUES:
            txt = " ".join(L[i - 1] for a, b in rangos for i in range(a, b + 1) if es_prosa(L[i - 1]))
            pat = pen if nombre.startswith("Abstract") else pes
            n = len(re.findall(pat, txt, flags=re.I))
            fila.append(f"SI ({n})" if n else "NO")
        obs = ""
        if todos and "NO" in fila[1:]:
            obs = "debería figurar en todos los bloques: revisar los «NO»"
        filas.append(fila + [obs])
    with open(ROOT / "auditoria/MATRIZ_COHERENCIA_ES_EN.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\r\n")
        w.writerow(["tema"] + [b[0] for b in BLOQUES] + ["observacion"])
        w.writerows(filas)
    for f_ in filas:
        print(" | ".join(x[:28] for x in f_))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(sys.argv[1])
