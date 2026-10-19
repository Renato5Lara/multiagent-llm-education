"""Construye notebooks/reproducibilidad_tesis.ipynb SIN salidas (las celdas se limpian antes de la entrega).
Uso (mantenimiento): python scripts/build_notebook.py"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = []

cells.append(md("""# Verificación reproducible de las cifras de la tesis

**Tesis:** *Validación de una arquitectura multiagente basada en inteligencia de enjambre para la adaptación multimodal en Programación.*
**Informe contrastado:** `D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS.docx` (versión editorial de cierre de brechas; no es la fuente de los datos).

## Qué hace este notebook
Descarga el paquete de evidencia, comprueba la **integridad** de sus archivos (SHA-256), **valida** los datos, **recalcula** las corridas desde los registros por petición, **regenera** los resultados derivados con los scripts del proyecto (sin modificarlos) y **compara** 1 017 comprobaciones numéricas con los valores publicados en el informe.

## Alcance y límites
- Campañas con datos aquí: **N1, N2, N3, N4, N5, N8, N8b** (directorio `oe_n10`), **N9b** y **N11** (el OE3 añade las réplicas exploratorias N3-R y N3-S en su notebook propio). Cubre las Tablas 6, 8–11, 13, 14, 17–24, 27–29, 40 y 41. Las Tablas 15/30 (K10 histórico) y 25 (antecedente) se contrastan con sus resultados derivados publicados. **No** se recalculan los estados categóricos de las Tablas 5/37 ni la síntesis bibliográfica de las Tablas 32/44 (síntesis bibliográfica) ni lo que requiere evaluadores humanos (ver sección H).
- **N9 fue una campaña abortada y descartada** (38 de 160 iniciadas). No se usa en ningún cálculo; N9b es la réplica integrada de 160/160 corridas.
- **Todas las campañas son experimentales y no oficiales.** Publicarlas no las vuelve oficiales.
- **Reproducir una cifra no demuestra que una hipótesis sea cierta.** Solo muestra que, con estos archivos y estos scripts, el cálculo da el valor del informe.
- No hay datos de usabilidad (SUS), de expertos ni de estudiantes: 0 evaluadores reales. No se simulan.
"""))

cells.append(md("## B. Preparación del entorno\nSe instalan **solo** las dependencias fijadas (las mismas versiones que cita el informe). No se necesitan tokens, claves ni archivos privados."))
cells.append(code("""%pip install -q numpy==2.5.4 pandas==3.0.6 scipy==1.18.1 statsmodels==0.15.0 matplotlib==3.11.2
import sys, platform, subprocess
# Los scripts se ejecutan en procesos nuevos: estas son las versiones que realmente usan (el kernel de Colab puede tener cargadas otras, p. ej. numpy preinstalado).
print(subprocess.run([sys.executable, "-c", "import platform, numpy, pandas, scipy, statsmodels, matplotlib as m; "
      "print('Python      ', platform.python_version()); "
      "[print(f'{n:12s}', mod.__version__) for n, mod in (('numpy', numpy), ('pandas', pandas), ('scipy', scipy), ('statsmodels', statsmodels), ('matplotlib', m))]"],
      capture_output=True, text=True).stdout)
# Nota: pip puede avisar de conflictos con paquetes preinstalados de Colab (google-colab, numba). No afectan a este análisis."""))

cells.append(md("""## C. Acceso a los datos
Por defecto el notebook **clona el repositorio público** `https://github.com/Renato5Lara/multiagent-llm-education` en la referencia `REF`.
Si ya tiene la carpeta `reproducibility/` (clonada o subida a Colab) se usa esa, o la que indique la variable de entorno `REPRO_LOCAL_ROOT`.
**Para repetir esto sin red:** copie `reproducibility/` al directorio de trabajo.

> `REF` debe existir en el remoto. Si todavía no se ha publicado esa rama, el clonado fallará con un mensaje claro: no es un error de los datos."""))
cells.append(code("""import os, subprocess, shutil
from pathlib import Path

REPO_URL = "https://github.com/Renato5Lara/multiagent-llm-education.git"
REF = "repro/auditoria-integral-2026-10-19"   # rama o etiqueta con el paquete; cámbiela por la etiqueta de la versión congelada

def localizar():
    env = os.environ.get("REPRO_LOCAL_ROOT")
    if env and (Path(env) / "EVIDENCE_MANIFEST.csv").exists():
        return Path(env), f"local (REPRO_LOCAL_ROOT={env})"
    for p in (Path.cwd(), Path.cwd() / "reproducibility", Path.cwd().parent):
        if (p / "EVIDENCE_MANIFEST.csv").exists():
            return p, f"local ({p})"
    dest = Path("/content/tesis_repo") if Path("/content").exists() else Path.cwd() / "tesis_repo"
    if dest.exists():
        shutil.rmtree(dest)
    # clon parcial: solo reproducibility/ y el código del proyecto necesario (backend/adaptation_swarm); el repositorio completo es mucho mayor
    r = subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "--branch", REF, REPO_URL, str(dest)], capture_output=True, text=True)
    if r.returncode == 0:
        r = subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", "reproducibility", "backend/adaptation_swarm", "backend/official_runs", "backend/loadtest"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"No se pudo clonar {REPO_URL} en la referencia {REF!r}.\\n{r.stderr.strip()}\\n"
                           "Compruebe que la rama/etiqueta existe en el remoto o copie reproducibility/ a mano.")
    return dest / "reproducibility", f"clonado de {REPO_URL} @ {REF}"

ROOT, origen = localizar()
print("Origen de los datos:", origen)
print("Raíz del paquete   :", ROOT)"""))

cells.append(code("""import json
import pandas as pd
pd.set_option("display.width", 200); pd.set_option("display.max_colwidth", 90)

def run_script(name):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT / "scripts", capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-4000:])
    if r.stderr.strip():
        print("[stderr]", r.stderr[-1500:])
    return r.returncode"""))

cells.append(md("""## D. Integridad de los archivos
Se recalcula el SHA-256 de **cada archivo del manifiesto** (`EVIDENCE_MANIFEST.csv`) y de los `SHA256SUMS` propios de cada campaña. Un hash prueba que el archivo es idéntico a la referencia, **no** que su contenido sea verdadero. Si algo no coincide, el análisis se detiene."""))
cells.append(code("""rc = run_script("verify_hashes.py")
rep = json.loads((ROOT / "outputs" / "hash_report.json").read_text(encoding="utf-8"))
print(pd.DataFrame(rep["sha256sums_de_campana"])[["archivo", "entradas", "coinciden", "no_publicado", "difieren"]].to_string(index=False))
if rc != 0:
    raise RuntimeError("ERROR DE INTEGRIDAD: hay archivos alterados o ausentes. Se detiene el análisis (ver outputs/hash_report.json).")
print("\\nIntegridad OK:", rep["manifiesto"]["coinciden"], "de", rep["manifiesto"]["entradas"], "archivos del manifiesto coinciden.")"""))

cells.append(md("""## E. Validación de los datos
Comprueba columnas obligatorias, tipos, duplicados de `run_id`, valores no finitos y que el número de filas sea el planificado. **No se elimina ninguna fila.** Regla de inclusión explícita: una corrida entra al análisis solo si `status == "ok"`; las demás se informan aquí con su motivo. Se distingue dato faltante (vacío) de cero."""))
cells.append(code("""rc = run_script("validate_data.py")
val = json.loads((ROOT / "outputs" / "validation_report.json").read_text(encoding="utf-8"))
print(val["regla_de_inclusion"])
tab = pd.DataFrame([{"campaña": k, "filas": v["filas"], "planificadas": v["filas_planificadas"], "ok (aceptadas)": v["filas_ok"], "excluidas": len(v["exclusiones"]),
                     "hallazgos": len(v["hallazgos"])} for k, v in val["campanas"].items()])
display(tab)
for k, v in val["campanas"].items():
    for e in v["exclusiones"]:
        print(f"Excluida en {k}: {e['run_id']} (status = {e['status']})")
if rc != 0:
    raise RuntimeError(f"Validación fallida: {val['estado']}")"""))

cells.append(md("""## F. Reproducción de resultados
`reproduce_results.py` comprueba tres eslabones:
1. **Peticiones → corrida.** Cada fila de `runs.csv` se recalcula con el código del proyecto (`http_window.summarize_run`) a partir de los registros por petición `raw/*.csv`.
2. **Corridas → derivados.** Se ejecutan **sin modificar** los scripts de análisis del proyecto sobre una copia temporal **en la que antes se han borrado todas las salidas**, y se comprueba que lo regenerado sea idéntico a lo publicado (byte a byte; en Linux/Colab, salvo los finales de línea, porque los archivos publicados se generaron en Windows con CRLF).
3. **Derivados → tablas.** Se comparan las cifras del informe con lo recalculado.

**Ejemplo guiado, Tabla 8 (campaña N2):** las 80 corridas originales (`oe_n2_2026-10-05/campaign/runs.csv`: 2 sistemas × 4 cargas × 10 corridas) → media por sistema y carga → comparación con las 8 filas × 4 métricas del informe."""))
cells.append(code("""rc = run_script("reproduce_results.py")
ver = json.loads((ROOT / "outputs" / "verification_report.json").read_text(encoding="utf-8"))
print("Entorno:", ver["entorno"])
print("\\nEslabón 1 (peticiones -> corrida):")
display(pd.DataFrame(ver["cadena_peticiones_a_corridas"])[["campana", "filas_runs_csv", "recalculadas_desde_peticiones_y_coinciden", "no_coinciden", "sin_registro_crudo", "diferencia_maxima", "estado"]])
b = pd.DataFrame(ver["derivados_byte_a_byte"])
print("\\nEslabón 2 (derivados regenerados vs publicados):", b.estado.value_counts().to_dict())
display(b.head(8))"""))
cells.append(code("""# Tabla 8 recalculada desde las 80 corridas de N2 (aquí, a la vista)
n2 = pd.read_csv(ROOT / "data/experiments/oe_n2_2026-10-05/campaign/runs.csv", low_memory=False)
print("Corridas en N2:", len(n2), "| status ok:", int((n2.status == "ok").sum()), "| sistemas:", sorted(n2.system.unique()), "| cargas:", sorted(n2.load.unique()))
t8 = n2[n2.status == "ok"].groupby(["system", "load"])[["p50_ms", "mean_ms", "p95_ms", "throughput_rps"]].mean().round(1)
display(t8)"""))

cells.append(md("""## G. Comparación con el informe
Cada fila compara un valor **publicado** (transcrito de `data/metadata/informe_D2.9.7_tablas.json`, extraído del DOCX con SHA-256 registrado) con el **recalculado**.
- Tolerancia: media unidad del último decimal publicado (redondeo). `COINCIDE` ≤ ½ unidad; `DIFERENCIA_EXPLICABLE` ≤ 1 unidad; `DISCREPANCIA` > 1 unidad.
- `NO_REPRODUCIBLE` indica que falta archivo, variable o procedimiento, y dice cuál."""))
cells.append(code("""comp = pd.DataFrame(ver["comprobaciones"])
print(ver["conteo_estados"])
resumen = comp.groupby(["tabla", "estado"]).size().unstack(fill_value=0)
display(resumen)
cols = ["id", "publicado", "recalculado", "dif_abs", "dif_rel", "tolerancia", "estado", "fuente_evidencia"]
display(comp[comp.estado != "NO_REPRODUCIBLE"][cols].head(12))
print("\\nNo reproducibles y motivo:")
display(comp[comp.estado == "NO_REPRODUCIBLE"][["id", "campana", "motivo"]])"""))

cells.append(md("""## H. Limitaciones y conclusión"""))
cells.append(code("""c = ver["conteo_estados"]
tr = pd.read_csv(ROOT / "RESULTS_TRACEABILITY.csv")
print("Cifras por estado:", ver["conteo_estado_cifra"])
print(f"  (de ellas, {c.get('DIFERENCIA_EXPLICABLE', 0)} difieren una unidad del último decimal por doble redondeo del informe)")
print("Tablas del informe por estado:", tr.estado.value_counts().to_dict())
display(tr[["tabla_informe", "campana", "estado", "cifras_comprobadas", "verificadas_desde_datos", "no_reproducibles", "observacion"]])"""))
cells.append(md("""**Qué sí y qué no demuestra esta ejecución**
- Con estos archivos y estos scripts, las cifras de las tablas marcadas `VERIFICADO_DESDE_DATOS` **se recalculan** a la precisión publicada desde `runs.csv`, `raw_observations.csv` o las réplicas guardadas, y para N2, N3, N4, N8, N8b, N9b y N11 también se comprobó que `runs.csv` sale de los registros por petición. Lo que queda sin comprobar está en la tabla anterior (`PARCIAL`, `NO_REPRODUCIBLE`): estados categóricos de N1, K10 histórico, pruebas de carga exploratorias, síntesis bibliográfica, SUS y expertos.
- La reproducibilidad computacional **no equivale a autenticidad experimental**: un hash acredita la identidad de un archivo frente a una referencia, no que su contenido sea verdadero. Que los registros por petición sean reales (y no fabricados) no se puede demostrar con este cómputo: solo que las métricas salen de ellos.
- Los resultados son **experimentales y no oficiales**; los de N5 usan la especificación v3 provisional del F1; los de K10 son históricos (v2).
- La métrica de usabilidad y la validación con expertos requieren evaluadores humanos y **no existen**; no se simulan.
- Esta ejecución no prueba causalidad ni confirma hipótesis."""))

cells.append(md("## I. Exportación\nSe guardan el informe de verificación y las tablas en una carpeta **nueva** con marca de tiempo; los archivos originales del paquete no se sobrescriben."))
cells.append(code("""import datetime, zipfile
dest = Path("verificacion_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
(dest).mkdir()
for f in [ROOT / "outputs" / n for n in ("verification_report.json", "hash_report.json", "validation_report.json")] + list((ROOT / "outputs" / "tables").glob("*.csv")):
    shutil.copy2(f, dest / f.name)
zpath = shutil.make_archive(str(dest), "zip", dest)
print("Exportado en:", dest.resolve(), "\\nZIP:", zpath)
try:
    from google.colab import files
    files.download(zpath)
except ImportError:
    pass"""))

nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"},
                                              "colab": {"name": "reproducibilidad_tesis.ipynb", "provenance": []}})
out = ROOT / "notebooks" / "reproducibilidad_tesis.ipynb"
nbf.write(nb, out)
print("escrito", out, len(cells), "celdas")
