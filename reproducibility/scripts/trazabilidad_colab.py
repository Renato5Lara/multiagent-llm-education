"""Trazabilidad de las ejecuciones en Colab: rondas, hashes de los notebooks y matriz de cambios posteriores.

No ejecuta Colab ni inventa datos: lee el historial de Git y reproduce lo que consta en
outputs/registro_ejecucion/COLAB_EJECUCION_OE1_OE5.md y COLAB_EJECUCION_REAL.md.
Uso: python scripts/trazabilidad_colab.py [COMMIT_EJECUTADO]   (por defecto c68a746)
Genera auditoria/TRAZABILIDAD_COLAB_POR_RONDA.csv y auditoria/MATRIZ_CAMBIOS_POSTERIORES.csv.
"""
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GIT_TOP = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
PREFIJO = ROOT.relative_to(GIT_TOP).as_posix()          # "reproducibility"
EJECUTADO = next((a for a in sys.argv[1:] if not a.startswith("--")), "c68a746")

NOTEBOOKS = {
    "OE1": "objetivo_1_requisitos_y_desempeno.ipynb", "OE2": "objetivo_2_enjambre_vs_convencional.ipynb",
    "OE3": "objetivo_3_configuracion_interna.ipynb", "OE4": "objetivo_4_carga_y_tamano_del_enjambre.ipynb",
    "OE5": "objetivo_5_precision_y_usabilidad.ipynb", "TRANSVERSAL": "reproducibilidad_tesis.ipynb",
}
# (ronda, commit, notebooks ejecutados, origen del dato)
RONDAS = [
    ("T1", "13d5a09", ["TRANSVERSAL"], "COLAB_EJECUCION_REAL.md, ejecución 1"),
    ("T2", "3967a7c", ["TRANSVERSAL"], "COLAB_EJECUCION_REAL.md, ejecución 2"),
    ("T3", "439eb4c", ["TRANSVERSAL"], "COLAB_EJECUCION_REAL.md, ejecución 3"),
    ("R1", "2fb5c04", ["OE1", "OE2", "OE3", "OE4", "OE5"], "COLAB_EJECUCION_OE1_OE5.md, primera ronda"),
    ("R2", "2c2ae3e", ["OE1", "OE2", "OE3", "OE4", "OE5"], "segunda ronda"),
    ("R3", "acaa19c", ["OE1", "OE2", "OE3", "OE4", "OE5", "TRANSVERSAL"], "tercera ronda"),
    ("R4", "d986b75", ["OE1", "OE2", "OE3", "OE4", "OE5", "TRANSVERSAL"], "cuarta ronda"),
    ("R5", "793c58c", ["OE1"], "quinta ronda (OE1)"),
    ("R5", "14febc2", ["TRANSVERSAL"], "quinta ronda (transversal)"),
    ("R6", EJECUTADO, list(NOTEBOOKS), "sexta ronda"),
]


def git(*a):
    return subprocess.run(["git", *a], cwd=GIT_TOP, capture_output=True)


def sha_en(commit, ruta):
    r = git("show", f"{commit}:{PREFIJO}/{ruta}")
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else ""


def completo(c):
    return git("rev-parse", c).stdout.decode().strip()


def hora(c):
    return git("log", "-1", "--format=%ad", "--date=iso", c).stdout.decode().strip()


def sha_actual(ruta):
    return hashlib.sha256((ROOT / ruta).read_bytes()).hexdigest()


def main():
    filas = []
    for ronda, c, objs, origen in RONDAS:
        for o in objs:
            ruta = "notebooks/" + NOTEBOOKS[o]
            h_c, h_a = sha_en(c, ruta), sha_actual(ruta)
            filas.append({
                "ronda": ronda, "objetivo": o, "notebook": NOTEBOOKS[o], "commit_ejecutado": completo(c),
                "fecha_documentada": "2026-10-19",
                "hora_del_commit_ejecutado": hora(c),
                "sha256_notebook_en_ese_commit": h_c, "sha256_notebook_actual": h_a,
                "notebook_igual_al_actual": "SI" if h_c and h_c == h_a else ("NO" if h_c else "NO_EXISTIA"),
                "sha256_notebook_ejecutado": "NO_VERIFICABLE (el .ipynb ejecutado no se guardó)",
                "evidencia": f"transcripción manual de la pantalla de Colab ({origen}); capturas no conservadas en el repositorio",
                "nivel_certeza": "PARCIAL: ejecución documentada por transcripción; commit y hora de ejecución no verificables de forma independiente",
            })
    with open(ROOT / "auditoria/TRAZABILIDAD_COLAB_POR_RONDA.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    print("rondas:", len(filas))


SCRIPTS_EJECUTADOS = {"verify_hashes.py", "validate_data.py", "reproduce_results.py", "repro_lib.py",
                      "oe3_robustez.py", "oe3_replicacion.py", "oe3_sesion.py", "oe3_eficiencia.py"}
FILTRO_PRUEBAS = ("comparar_archivos", "clasificacion", "parse", "sanitizadas", "rutas_locales")   # pytest -k de los notebooks por objetivo
ENTRADAS = ("data/", "datasets/", "notebooks/", "EVIDENCE_MANIFEST.csv", "RESULTS_TRACEABILITY.csv", "environment/")
OBJ_DE_DATOS = {"oe_n1": "OE1", "oe_n2": "OE2", "oe_n3": "OE3", "oe_n4": "OE4", "oe_n5": "OE5"}


def funciones_cambiadas(destino, ruta):
    """Nombres de las funciones de prueba tocadas, según el contexto de los hunks de git diff."""
    args = ["--cached", EJECUTADO] if destino == ["--cached"] else [EJECUTADO, *destino]
    r = git("diff", "-U0", *args, "--", f"{PREFIJO}/{ruta}").stdout.decode("utf-8", "replace")
    nombres = set()
    for linea in r.splitlines():
        if linea.startswith("@@") and "def " in linea:
            nombres.add(linea.split("def ", 1)[1].split("(")[0])
    return nombres


def matriz(destino):
    """destino: [] (árbol de trabajo) o ['--cached'] / ['HEAD'] según el momento."""
    num = git("diff", "--numstat", *destino, EJECUTADO).stdout.decode().splitlines() if destino == ["--cached"] else \
        git("diff", "--numstat", EJECUTADO, *destino).stdout.decode().splitlines()
    filas = []
    for linea in num:
        a, b, ruta = linea.split("\t", 2)
        rel = ruta[len(PREFIJO) + 1:] if ruta.startswith(PREFIJO + "/") else ruta
        existia = git("cat-file", "-e", f"{EJECUTADO}:{ruta}").returncode == 0
        estado = "MODIFICADO" if existia else "NUEVO"
        afectados, reej, verif = "ninguno", "NO", ""
        if rel.startswith("auditoria/") or rel.startswith("outputs/registro_ejecucion/") or rel == "README.md":
            cat, cons = "DOCUMENTACION_O_REGISTRO_DE_AUDITORIA", "NO"
            verif = "ningún script que ejecutan los notebooks abre archivos de auditoria/ (búsqueda en scripts/*.py de los ocho scripts invocados)"
        elif rel.startswith("scripts/"):
            nombre = rel.split("/")[-1]
            if nombre in SCRIPTS_EJECUTADOS:
                cat, cons, afectados, reej = "CODIGO_EJECUTADO_POR_NOTEBOOKS", "SI", "verificar", "SI"
                verif = "cambia un script que invocan los notebooks"
            else:
                cat, cons = "CODIGO_AUXILIAR_NO_EJECUTADO_POR_NOTEBOOKS", "NO"
                verif = "no figura entre los scripts que invocan los notebooks ni se importa desde ellos (repro_lib es el único módulo importado)"
        elif rel.startswith("tests/"):
            fs = funciones_cambiadas(destino, rel)
            sel = sorted(f for f in fs if any(k in f for k in FILTRO_PRUEBAS))
            if sel:
                cat, cons, afectados, reej = "PRUEBAS_EJECUTADAS_POR_NOTEBOOKS", "SI", "OE1-OE5", "SI"
                verif = "cambia pruebas seleccionadas por -k: " + ", ".join(sel)
            else:
                cat, cons = "PRUEBAS_NO_SELECCIONADAS_POR_LOS_NOTEBOOKS", "NO"
                verif = "funciones tocadas: " + (", ".join(sorted(fs)) or "(solo finales de línea)") + "; ninguna coincide con el filtro -k de los notebooks"
        elif rel.startswith(ENTRADAS):
            cat, cons, afectados, reej = "DATOS_O_ENTRADA_O_NOTEBOOK", "SI", "verificar", "SI"
            verif = "cambia una entrada de los notebooks"
        else:
            cat, cons, verif = "OTRO", "NO", "revisar manualmente"
        filas.append({"archivo": ruta, "estado_git": estado, "lineas_anadidas": a, "lineas_borradas": b, "categoria": cat,
                      "consumido_por_notebooks": cons, "notebooks_afectados": afectados, "requiere_reejecucion": reej, "verificacion": verif})
    return filas


def escribir_matriz(destino):
    filas = matriz(destino)
    with open(ROOT / "auditoria/MATRIZ_CAMBIOS_POSTERIORES.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader(); w.writerows(filas)
    print("archivos cambiados desde", EJECUTADO, ":", len(filas), "| consumidos por notebooks:", sum(r["consumido_por_notebooks"] == "SI" for r in filas))


if __name__ == "__main__":
    main()
    escribir_matriz(["--cached"] if "--cached" in sys.argv else ["HEAD"])
