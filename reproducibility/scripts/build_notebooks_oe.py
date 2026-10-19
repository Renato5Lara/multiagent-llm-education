"""Construye un notebook de Colab por objetivo específico VIGENTE de la tesis (D2.9.7 declara cinco: OE1–OE5), sin salidas guardadas.
Estructura común A–I; el contenido propio de cada objetivo está en SPEC. Cada notebook se resuelve a sí mismo (clona, instala, verifica, recalcula, compara)."""
import json
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
OBJ = json.loads((ROOT / "auditoria" / "OBJETIVOS_LITERALES.json").read_text(encoding="utf-8"))
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
REF = "repro/auditoria-integral-2026-10-19"

SPEC = {
    "oe1": dict(
        archivo="objetivo_1_requisitos_y_desempeno", titulo="Objetivo específico 1: cumplimiento de requerimientos y desempeño", tablas="5, 6 y 37 (más las cifras en prosa de §6.5.3, §6.7 y §7.1)", camp="N1",
        pregunta="¿Qué requerimientos funcionales y no funcionales cumple la arquitectura y cómo se relaciona su cumplimiento con el desempeño?",
        hipotesis="H1 (general) no se contrasta en este objetivo. **Los objetivos 1, 2 y 3 no tienen hipótesis estadística formulada en la tesis** (formulación pendiente); la meta es la especificación formal de 6 RF y 5 RNF.",
        datos=["oe_n1_2026-10-05/oe3_run/raw_observations.csv (6 300 ciclos en proceso)", "oe_n1_2026-10-05/oe4_run/raw_observations.csv (3 200 ciclos en proceso)", "oe_n1_2026-10-05/oe1_report/oe1_report.json y .md (derivado del propio arnés)"],
        scripts=["oe_n8_2026-10-13/scripts/oe1_verify.py (re-análisis independiente de la asociación cumplimiento–desempeño)", "scripts/reproduce_results.py (recuentos y percentiles de las cifras en prosa)"],
        limites=["La asociación del puntaje de cumplimiento con el desempeño se calcula sobre **n = 14 condiciones**, está confundida con la carga y **no es causal**; el puntaje carece de una definición aprobada.",
                 "RNF01 se mide **en proceso (sin HTTP)** y solo en el agregado: el 82 % de las observaciones procede de 1 usuario; con 25 usuarios no se cumple.",
                 "RNF05 (SUS) **no se midió**; RNF03 no alcanza 0,85 (v2 histórico y v3 provisional).",
                 "Las Tablas 5 y 37 son estados categóricos (MET/NOT_MET) copiados del informe de N1: aquí solo se verifica la integridad del archivo que los contiene.",
                 "N1 es una campaña **no oficial** ejecutada en un único equipo local."],
        conclusion="Con los registros de N1 se reproducen los recuentos y percentiles en proceso que sostienen el estado de cada requerimiento (p. ej. RF03 solo con despacho concurrente y RNF01 solo en el agregado). Los datos **no** permiten afirmar causalidad entre cumplimiento y desempeño, ni que el OE1 esté completamente cumplido: la propia tesis lo califica como cumplimiento parcial.",
        tabla_principal=6, extra="oe1"),
    "oe2": dict(
        archivo="objetivo_2_enjambre_vs_convencional", titulo="Objetivo específico 2: propuesta de enjambre frente a un sistema convencional", tablas="8, 9, 10, 11 y 38", camp="N2 (80 corridas) y N9b (160 corridas)",
        pregunta="¿Cómo se compara el desempeño técnico (latencia P95 y throughput) de la propuesta con `decision_table` en condiciones equivalentes, y con `rules` y `bruteforce` como contrastes auxiliares?",
        hipotesis="El OE2 **no tiene hipótesis estadística formulada** (pendiente). Contribuye al componente L_resp de H1 al comparar la latencia con el sistema convencional (P95 < 2,0 s con hasta 25 usuarios).",
        datos=["oe_n2_2026-10-05/campaign/runs.csv + campaign/raw/ (80 corridas: 2 sistemas × 4 cargas × 10)", "oe_n9b_2026-10-14/campaign_final/runs.csv + campaign/raw/ y campaign_final/raw/ (160 corridas: 4 sistemas × 4 cargas × 10)"],
        scripts=["oe_n8_2026-10-13/scripts/oe2_reanalysis.py (Tablas 9–10)", "oe_n8_2026-10-13/scripts/oe2_aux_analysis.py (Tabla 11)", "scripts/reproduce_results.py (Tablas 8 y 38, recálculo directo con pandas)"],
        limites=["`decision_table` es un sistema convencional **definido operacionalmente dentro del estudio**, no un baseline externo formalmente validado; `rules` es una **ablación** del enjambre y `bruteforce` una **referencia de optimalidad**, no un baseline convencional.",
                 "N9 fue una campaña **abortada y descartada** (38 de 160 iniciadas); N9b es la réplica integrada y no se combina con N9.",
                 "El T_conv solo existe para la propuesta y no se compara con el tiempo de decisión del sistema convencional.",
                 "Medición HTTP con el generador de carga en el mismo equipo local; campañas **no oficiales** (clase de entorno `TECHNICALLY_COMPATIBLE_P6_PENDING`)."],
        conclusion="Los datos publicados permiten reproducir que, en estas condiciones, la propuesta tiene mayor latencia P95 y menor throughput que `decision_table` y `rules`, y que no se distingue de `bruteforce` en P95. **No** permiten afirmar superioridad frente a sistemas convencionales externos ni validan un benchmark comparativo.",
        tabla_principal=8, extra="oe2"),
    "oe3": dict(
        archivo="objetivo_3_configuracion_interna", titulo="Objetivo específico 3: efecto de la configuración interna de la arquitectura", tablas="13, 14, 15 y 40", camp="N3 (240 corridas) y K10 histórico (v2)",
        pregunta="¿Qué efecto tienen los roles de los agentes, los protocolos de comunicación y el mecanismo de enjambre sobre el tiempo de convergencia y la eficiencia de la adaptación?",
        hipotesis="El OE3 **no tiene hipótesis estadística formulada** (pendiente). La meta 3 es un modelo de 5 agentes con PSO discreto y una tasa de convergencia CR ≥ 98 %.",
        datos=["oe_n3_2026-10-06/run/raw_observations.csv (24 000 ciclos en proceso) → runs_oe3.csv (240 corridas = 48 condiciones × 5 lotes)", "backend/official_runs/k10_official_2026-09-27/replica_00..09.json (resultado histórico con la especificación v2; Tabla 15)"],
        scripts=["oe_n8_2026-10-13/scripts/oe3_reanalysis.py (Tabla 14)", "adaptation_swarm.oe.factorial (ANOVA tipo III con permutación Freedman–Lane; Tabla 13)", "scripts/reproduce_results.py (agregación de runs_oe3.csv, Tablas 13, 15 y 40)"],
        limites=["Se ejecutó un **ANOVA factorial** sobre la corrida como unidad; las pruebas planeadas en el plan de análisis (p. ej. Friedman con Holm) **no se ejecutaron**.",
                 "Mediciones **en proceso**, sin HTTP, en hardware local; campaña **no oficial**.",
                 "En la Tabla 13, tres cifras (η² de la heurística, `k_stop` con heurística y T_conv de PSO) difieren una unidad del último decimal por **doble redondeo del informe**: ver `auditoria/AUDITORIA_REDONDEO_TABLA13.md` (valores correctos 0,49 · 1,50 · 76,4).",
                 "Las celdas «sin efecto» de la Tabla 13 no se verifican numéricamente. La Tabla 15 es un resultado **histórico (v2)**, no de N3."],
        conclusion="Los registros de N3 reproducen los efectos marginales y el ANOVA factorial publicados (efecto grande de despacho, difusión de g_best, mecanismo y heurística sobre T_conv; el mecanismo y la heurística también sobre la brecha). **No** permiten inferir causalidad fuera del modelo en proceso ni estimar el desempeño en HTTP o en hardware objetivo.",
        tabla_principal=14, extra="oe3"),
    "oe4": dict(
        archivo="objetivo_4_carga_y_tamano_del_enjambre", titulo="Objetivo específico 4: desempeño computacional bajo distintas condiciones", tablas="17 a 25", camp="N4, N8, N8b (directorio oe_n10), N11 y la prueba de carga exploratoria de antecedente",
        pregunta="¿Cómo varían el tiempo de convergencia, la latencia y el throughput con el nivel de carga y el tamaño del enjambre, y se alcanzan las metas P95 < 2,0 s y ≥ 20 req/s?",
        hipotesis="Contribuye al componente L_resp de H1 (P95 < 2,0 s con hasta 25 usuarios). La meta 4 es T_conv ≤ 15 iteraciones (cumplida por construcción: k_max = 15), L_resp < 2,0 s y throughput ≥ 20 req/s. Sin hipótesis estadística formulada para el OE4.",
        datos=["oe_n4_2026-10-06/campaign/runs.csv + raw (60), oe_n8_2026-10-13/campaign/runs.csv + raw (120), oe_n10_2026-10-14_n20/campaign/runs.csv + raw (60), oe_n11_2026-10-14_3N/campaign/runs.csv + raw (180; 179 válidas)",
               "backend/loadtest/results/ (Tabla 25: Locust y JMeter, 2026-09-23, rastreado en Git)"],
        scripts=["oe_n8_2026-10-13/scripts/oe4_nvar_analysis.py (Tablas 18–19)", "oe_n8_2026-10-13/scripts/oe4_n11_analysis.py (Tablas 21–23)", "oe_n8_2026-10-13/scripts/verif_d27.py (Tablas 23–24, verificación independiente)", "scripts/reproduce_results.py (Tablas 17, 20 y 25)"],
        limites=["Todas las mediciones son en **un equipo local** (i7-12700K, 20 vCPU) con el generador en la misma máquina; la condición objetivo de **8 vCPU / 32 GB en la nube no se ejecutó**.",
                 "N11 tiene **dos tramos con régimen de rendimiento distinto** (el tramo B es ≈ 1,6 veces más rápido): no deben combinarse; una corrida (`u100|N10-r01`) quedó `no_requests` y se excluye por regla explícita.",
                 "RNF04 (≥ 20 req/s) solo se alcanza en 18 de 419 corridas, todas con N = 10 en un régimen del equipo; RNF01 con 25 usuarios solo con N = 10 en el tramo B.",
                 "La Tabla 25 es un **antecedente exploratorio** (no comparable con N1–N11); sus cifras de JMeter se verifican desde un resumen derivado del proyecto.",
                 "Campañas **no oficiales**."],
        conclusion="Los registros reproducen que la latencia crece con la carga y con N, que el throughput se estanca entre ≈ 8 y 20 req/s según N y régimen, y que RNF01 se cumple hasta 10 usuarios (y con 25 solo en un caso). **No** permiten afirmar el cumplimiento de las metas en las condiciones objetivo ni extrapolar al despliegue en la nube.",
        tabla_principal=17, extra="oe4"),
    "oe5": dict(
        archivo="objetivo_5_precision_y_usabilidad", titulo="Objetivo específico 5: precisión de la adaptación y usabilidad técnica", tablas="27, 28, 29, 30, 35 y 41", camp="N5 (F1 v3 provisional) y K10 histórico (v2)",
        pregunta="¿Cuál es el nivel de precisión de la adaptación (F1_adapt) y de usabilidad (SUS) frente a las metas F1_adapt ≥ 0,85 y SUS > 75?",
        hipotesis="H1 (general): F1_adapt ≥ 0,85 y puntaje SUS > 75,0 (media de al menos 10 evaluadores). El F1_adapt se contrasta con el IC95 % y una prueba unilateral; el SUS con la media de ≥ 10 evaluadores.",
        datos=["oe_n5_2026-10-06/f1_v3_provisional/replica_*.json (10 réplicas × 100 perfiles = 1 000 casos; especificación v3 PROVISIONAL, official=False)", "backend/official_runs/k10_official_2026-09-27/replica_*.json (K10 con la especificación v2, histórico)"],
        scripts=["oe_n8_2026-10-13/scripts/reproduce_f1_v3_independent.py (F1, precisión y recall por modalidad)", "oe_n8_2026-10-13/scripts/alineacion_aptitud_f1.py (Tabla 29)", "scripts/reproduce_results.py (Tablas 30 y parte de la 27)"],
        limites=["**No existen datos de usabilidad ni del panel de expertos: 0 evaluadores reales.** La parte SUS del OE5 **no se puede evaluar** y no se simula.",
                 "La especificación v3 del F1 es **provisional**; el resultado con v2 es histórico y corresponde a otra definición de la métrica. La matriz *gold* por arquetipo está pendiente de validación por el panel.",
                 "La evaluación usa perfiles **sintéticos** (4 arquetipos × 5 dificultades × réplicas), no estudiantes reales.",
                 "Las estadísticas por perfil de la Tabla 27 (mediana, desviación, rango) no se recalculan en esta entrega."],
        conclusion="Los datos reproducen el F1_adapt con v3 provisional (≈ 0,816; el límite superior del IC95 % queda **por debajo** de 0,85) y el valor histórico con v2 (≈ 0,641). Por tanto **la meta F1_adapt ≥ 0,85 no se alcanza con los datos disponibles**, y el componente de usabilidad (SUS > 75) **no puede evaluarse**: el OE5 solo está evidenciado parcialmente.",
        tabla_principal=28, extra="oe5"),
}


def build(oe):
    s = SPEC[oe]
    n = oe[-1]
    lit = OBJ["objetivos"][oe.upper()]
    meta = OBJ["metas"].get(oe.upper(), "")
    cells = []
    cells.append(md(f"""# {s['titulo']}

**Tesis:** *Validación de una arquitectura multiagente basada en inteligencia de enjambre para la adaptación multimodal en Programación.* Versión auditada: informe **D2.9.7-CIERRE-BRECHAS-CORRECCION-CUADROS** (sha256 `{OBJ['version']}…`).

## A. Identificación
**{oe.upper()} (literal de la tesis):** {lit}

**Meta de desempeño asociada:** {meta.split(': ', 1)[-1] if meta else '—'}

**Pregunta experimental.** {s['pregunta']}

**Hipótesis y contraste.** {s['hipotesis']}

**Tablas del informe que se concilian aquí:** {s['tablas']}. **Campañas:** {s['camp']}. Todas son **experimentales y no oficiales**.

**Datos que usa este notebook**
""" + "\n".join(f"- {d}" for d in s["datos"]) + "\n\n**Scripts**\n" + "\n".join(f"- {x}" for x in s["scripts"]) + "\n\n**Limitaciones**\n" + "\n".join(f"- {x}" for x in s["limites"]) + """

> Reproducir una cifra **no** demuestra que una hipótesis sea cierta, ni que los experimentos se hicieran en las condiciones declaradas, ni que los registros sean auténticos: solo que, con estos archivos y estos scripts, el cálculo da el valor del informe. Este notebook es **independiente** de los demás: resuelve sus propias dependencias."""))

    cells.append(md("## B. Entorno\nSe instalan **solo** las dependencias fijadas (las versiones que cita el informe). No se necesitan tokens, claves ni archivos privados."))
    cells.append(code("""%pip install -q numpy==2.5.4 pandas==3.0.6 scipy==1.18.1 statsmodels==0.15.0 matplotlib==3.11.2
import sys, platform, subprocess
# Los scripts corren en procesos nuevos: estas son las versiones que realmente usan (el kernel de Colab puede traer otras cargadas, p. ej. numpy).
print(subprocess.run([sys.executable, "-c", "import platform, numpy, pandas, scipy, statsmodels, matplotlib as m; "
      "print('Python      ', platform.python_version()); "
      "[print(f'{n:12s}', mod.__version__) for n, mod in (('numpy', numpy), ('pandas', pandas), ('scipy', scipy), ('statsmodels', statsmodels), ('matplotlib', m))]"],
      capture_output=True, text=True).stdout)
print("Sistema:", platform.platform())
# Nota: pip puede avisar de conflictos con paquetes preinstalados de Colab (google-colab, numba); no afectan a este análisis."""))

    cells.append(md(f"""## C. Fuentes de datos
El notebook clona el repositorio público en `REF` (clon parcial: `reproducibility/`, el código del proyecto necesario y los datos históricos rastreados en Git). Si ya tiene la carpeta `reproducibility/` se usa esa. Se calcula el SHA-256 de **cada archivo del manifiesto** y se **detiene** el análisis si alguno no coincide: un hash prueba la identidad del archivo frente a una referencia, no que su contenido sea verdadero. Los archivos sanitizados (rutas locales sustituidas) están identificados en `data/metadata/SANITIZACION.csv` y **no** son idénticos a los originales."""))
    cells.append(code(f"""import os, subprocess, shutil, json
from pathlib import Path
import pandas as pd
pd.set_option("display.width", 200); pd.set_option("display.max_colwidth", 80); pd.set_option("display.max_rows", 60)

REPO_URL = "https://github.com/Renato5Lara/multiagent-llm-education.git"
REF = "{REF}"   # rama o etiqueta con el paquete

def localizar():
    env = os.environ.get("REPRO_LOCAL_ROOT")
    if env and (Path(env) / "EVIDENCE_MANIFEST.csv").exists():
        return Path(env), f"local (REPRO_LOCAL_ROOT={{env}})"
    for p in (Path.cwd(), Path.cwd() / "reproducibility", Path.cwd().parent):
        if (p / "EVIDENCE_MANIFEST.csv").exists():
            return p, f"local ({{p}})"
    dest = Path("/content/tesis_repo") if Path("/content").exists() else Path.cwd() / "tesis_repo"
    if dest.exists():
        shutil.rmtree(dest)
    r = subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "--branch", REF, REPO_URL, str(dest)], capture_output=True, text=True)
    if r.returncode == 0:
        r = subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", "reproducibility", "backend/adaptation_swarm", "backend/official_runs", "backend/loadtest"], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"No se pudo clonar {{REPO_URL}} en {{REF!r}}.\\n{{r.stderr.strip()}}\\nCompruebe que la rama/etiqueta existe o copie reproducibility/ a mano.")
    return dest / "reproducibility", f"clonado de {{REPO_URL}} @ {{REF}}"

ROOT, origen = localizar()
commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() or "(sin git)"
print("Origen:", origen); print("Raíz  :", ROOT); print("Commit:", commit)

def run_script(name, *args):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / name), *args], cwd=ROOT / "scripts", capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(r.stdout[-3500:])
    if r.stderr.strip():
        print("[stderr]", r.stderr[-1500:])
    return r.returncode

rc = run_script("verify_hashes.py")
rep_h = json.loads((ROOT / "outputs" / "hash_report.json").read_text(encoding="utf-8"))
if rc != 0:
    raise RuntimeError("ERROR DE INTEGRIDAD: hay archivos alterados o ausentes. Se detiene el análisis (ver outputs/hash_report.json).")
print("Integridad OK:", rep_h["manifiesto"]["coinciden"], "de", rep_h["manifiesto"]["entradas"], "archivos del manifiesto coinciden.")"""))

    cells.append(md("## D. Preparación y validación de los datos\nSe leen los archivos reales, se comprueban esquema, tipos, duplicados, valores ausentes (distintos de cero), unidades y recuentos, y se declara cada exclusión con su regla. **No se elimina ninguna fila.**"))
    cells.append(code(VALID[oe]))

    cells.append(md(f"""## E. Reproducción del análisis
`reproduce_results.py --oe {oe}` comprueba, para este objetivo: (1) cuando existen, que cada fila de `runs.csv` se recalcula con el código del proyecto desde los **registros por petición**; (2) que los **scripts de análisis del proyecto**, ejecutados **sin modificar** sobre una copia en la que se borraron antes sus salidas, regeneran lo publicado; y (3) que las **cifras del informe** coinciden con lo recalculado a su precisión publicada. Tolerancias: media unidad del último decimal publicado para las cifras del informe; para comparar archivos regenerados, igualdad byte a byte o salvo finales de línea (los publicados son de Windows) o con ruido de punto flotante (relativa 1e-6, absoluta 1e-12)."""))
    cells.append(code(f"""rc = run_script("reproduce_results.py", "--oe", "{oe}")
ver = json.loads((ROOT / "outputs" / "verification_report_{oe}.json").read_text(encoding="utf-8"))
print("Entorno de los scripts:", ver["entorno"])
print("\\nEslabón 1 — peticiones → corrida:")
display(pd.DataFrame(ver["cadena_peticiones_a_corridas"]) if ver["cadena_peticiones_a_corridas"] else "no aplica a este objetivo (sin runs.csv HTTP; los datos son observaciones por ciclo)")
b = pd.DataFrame(ver["derivados_byte_a_byte"])
print("\\nEslabón 2 — derivados regenerados vs publicados:", b.estado.value_counts().to_dict() if len(b) else "no aplica")"""))

    cells.append(md(f"## F. Resultados y comparación con el informe\nTabla principal de este objetivo: **Tabla {s['tabla_principal']}**. Cada fila compara el valor **publicado** (transcrito de `data/metadata/informe_D2.9.7_tablas.json`, extraído del DOCX con su SHA-256) con el **recalculado**, con la celda exacta del informe."))
    cells.append(code(f"""comp = pd.DataFrame(ver["comprobaciones"])
comp["tabla_n"] = comp["tabla"].str.extract(r"(\\d+)")[0]
cols = ["etiqueta_fila", "encabezado", "publicado", "recalculado", "dif_abs", "tolerancia", "estado", "estado_cifra"]
for tb, g in comp.groupby("tabla"):
    print(f"\\n=== {{tb}}: {{len(g)}} cifras ===")
    display(g[g.estado != "NO_REPRODUCIBLE"][[c for c in cols if c in g]].head(12))
print("\\nCifras que NO se pueden reproducir y por qué:")
nr_df = comp[comp.estado == "NO_REPRODUCIBLE"].reindex(columns=["tabla", "id", "motivo"])
print("(ninguna)" if nr_df.empty else "")
display(nr_df)"""))
    if s["extra"] == "oe1":
        cells.append(md("**Cifras en prosa del OE1** (§6.5.3, §6.7, §7.1 y resumen) recalculadas desde los 9 500 ciclos de N1:"))
        cells.append(code("""display(pd.DataFrame(ver["prosa_recalculada"])[["pub", "unidad", "descripcion", "recalculado", "estado", "formula"]])"""))
    if s["extra"] == "oe3":
        cells.append(md("**Auditoría del redondeo de la Tabla 13.** Valor sin redondear, valor intermedio y valor correcto de las tres cifras que difieren una unidad:"))
        cells.append(code("""x = comp[comp.estado == "DIFERENCIA_EXPLICABLE"]
display(x[["id", "publicado", "valor_sin_redondear", "valor_intermedio", "detalle"]])"""))
    cells.append(md("## G. Verificación\nResumen de estados por cifra, **prueba negativa** del comparador (una cifra alterada a propósito debe detectarse) y pruebas unitarias rápidas."))
    cells.append(code(f"""cnt = ver["conteo_estado_cifra"]
print("Cifras por estado:", cnt)
print("Detalle de comparación:", ver["conteo_estados"])
# --- prueba negativa: alteramos una copia en memoria de una cifra publicada; el comparador debe marcar DISCREPANCIA
sys.path.insert(0, str(ROOT / "scripts"))
from repro_lib import compare
ok = comp[(comp.estado == "COINCIDE") & comp.recalculado.notna()].iloc[0]
alterada = compare(str(ok["publicado"]), float(ok["recalculado"]) * 1.5 + 1)
print("\\nPrueba negativa sobre", ok["id"], "(publicado", ok["publicado"], "; se compara contra un valor deliberadamente distinto):", alterada["estado"])
assert alterada["estado"] in ("DISCREPANCIA", "DIFERENCIA_SIN_EXPLICAR"), "el comparador NO detectó una diferencia real"
# --- pruebas unitarias rápidas del comparador y del clasificador de redondeo
%pip install -q pytest
r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(ROOT / "tests" / "test_reproducibility.py"), "-k", "comparar_archivos or clasificacion or parse or sanitizadas or rutas_locales"], capture_output=True, text=True, cwd=ROOT)
print(r.stdout[-600:])
nr = cnt.get("NO_REPRODUCIBLE", 0); disc = cnt.get("DISCREPANCIA", 0)
assert disc == 0, "hay discrepancias reales: revise la tabla de comparación"
print("\\nSin discrepancias." if disc == 0 else "")"""))
    cells.append(md(f"## H. Conclusión limitada a la evidencia\n{s['conclusion']}\n\n**Lo que este notebook no demuestra:** causalidad; autenticidad histórica de las mediciones (los hashes solo prueban identidad frente a una referencia); validación independiente de terceros (el re-análisis lo realizó el propio proyecto); desempeño en condiciones objetivo; evaluación por usuarios o expertos reales."))
    cells.append(md("## I. Exportación y resumen\nSe guardan el informe y las tablas de este objetivo en una carpeta **nueva** (los archivos originales no se sobrescriben) y se imprime una línea de resumen para el registro de ejecución."))
    cells.append(code(f"""import datetime, zipfile
dest = Path("verificacion_{oe}_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
dest.mkdir()
for f in [ROOT / "outputs" / f"verification_report_{oe}.json", ROOT / "outputs" / "hash_report.json"] + list((ROOT / "outputs" / "tables").glob("*_{oe}.csv")):
    shutil.copy2(f, dest / f.name)
zpath = shutil.make_archive(str(dest), "zip", dest)
print("Exportado en:", dest.resolve(), "\\nZIP:", zpath)
try:
    from google.colab import files
    files.download(zpath)
except ImportError:
    pass
resumen = {{"objetivo": "{oe.upper()}", "commit": commit[:8], "cifras": len(ver["comprobaciones"]), "estado_cifra": cnt, "discrepancias": disc, "no_reproducibles": nr,
           "cadena": {{c["campana"]: c["estado"] for c in ver["cadena_peticiones_a_corridas"]}}, "derivados": b.estado.value_counts().to_dict() if len(b) else {{}}}}
print("RESUMEN_COLAB", json.dumps(resumen, ensure_ascii=False))"""))
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python"}, "colab": {"name": s["archivo"] + ".ipynb", "provenance": []}})
    out = ROOT / "notebooks" / f"{s['archivo']}.ipynb"
    nbf.write(nb, out)
    return out


VALID = {
    "oe1": '''import numpy as np
a = pd.read_csv(ROOT / "data/experiments/oe_n1_2026-10-05/oe3_run/raw_observations.csv", low_memory=False)
b = pd.read_csv(ROOT / "data/experiments/oe_n1_2026-10-05/oe4_run/raw_observations.csv", low_memory=False)
d = pd.concat([a.assign(origen="oe3_run"), b.assign(origen="oe4_run")], ignore_index=True)
print("Ciclos en proceso:", len(d), "| oe3_run:", len(a), "| oe4_run:", len(b))
print("Estados:", d.status.value_counts().to_dict(), "| duplicados exactos:", int(d.duplicated().sum()))
print("Niveles de concurrencia:", d.f_concurrency.value_counts().sort_index().to_dict())
print("Valores ausentes (columnas con faltantes estructurales, no ceros):", {k: int(v) for k, v in d[["latency_ms", "t_conv_ms", "decision_ms", "error_code"]].isna().sum().items() if v})
print("Latencia (ms): mín", round(d.latency_ms.min(), 3), "máx", round(d.latency_ms.max(), 1), "| finita:", bool(np.isfinite(d.latency_ms.dropna()).all()))''',
    "oe2": '''rc = run_script("validate_data.py")
val = json.loads((ROOT / "outputs" / "validation_report.json").read_text(encoding="utf-8"))
print(val["regla_de_inclusion"])
tab = pd.DataFrame([{"campaña": k, "filas": v["filas"], "planificadas": v["filas_planificadas"], "ok": v["filas_ok"], "excluidas": len(v["exclusiones"]), "hallazgos": len(v["hallazgos"])}
                    for k, v in val["campanas"].items() if k in ("N2", "N9b")])
display(tab)
n9 = (ROOT / "data/metadata/N9_ABORTADA.md").read_text(encoding="utf-8")
print("\\nN9 (NO usada en ningún cálculo):", n9.split("\\n")[2][:230])''',
    "oe3": '''import numpy as np
r = pd.read_csv(ROOT / "data/experiments/oe_n3_2026-10-06/runs_oe3.csv")
print("Corridas:", len(r), "| condiciones:", r.condition.nunique(), "| lotes por condición:", r.groupby("condition").batch.nunique().unique().tolist(), "| duplicados (condición, lote):", int(r.duplicated(["condition", "batch"]).sum()))
print("Valores ausentes:", int(r.isna().sum().sum()), "| T_conv finito y > 0:", bool((r.t_conv_ms > 0).all() and np.isfinite(r.t_conv_ms).all()))
print("Factores:", {c: sorted(r[c].astype(str).unique().tolist()) for c in r.columns if c.startswith("f_")})
raw = pd.read_csv(ROOT / "data/experiments/oe_n3_2026-10-06/run/raw_observations.csv", low_memory=False)
print("Ciclos en proceso:", len(raw), "| estados:", raw.status.value_counts().to_dict())''',
    "oe4": '''rc = run_script("validate_data.py")
val = json.loads((ROOT / "outputs" / "validation_report.json").read_text(encoding="utf-8"))
print(val["regla_de_inclusion"])
tab = pd.DataFrame([{"campaña": k, "filas": v["filas"], "planificadas": v["filas_planificadas"], "ok": v["filas_ok"], "excluidas": len(v["exclusiones"]), "hallazgos": len(v["hallazgos"])}
                    for k, v in val["campanas"].items() if k in ("N4", "N8", "N8b", "N11")])
display(tab)
for k in ("N11",):
    for e in val["campanas"][k]["exclusiones"]:
        print(f"Excluida en {k}: {e['run_id']} (status = {e['status']})")''',
    "oe5": '''import glob, numpy as np
fs = sorted(glob.glob(str(ROOT / "data/experiments/oe_n5_2026-10-06/f1_v3_provisional/replica_*.json")))
reps = [json.load(open(f, encoding="utf-8")) for f in fs]
casos = [c for r in reps for c in r["cases"]]
print("Réplicas:", len(reps), "| casos:", len(casos), "| perfiles distintos:", len({c["profile_id"] for c in casos}))
f1 = np.array([c["f1"] for c in casos])
print("F1 por caso: finito:", bool(np.isfinite(f1).all()), "| rango", f1.min(), "a", f1.max(), "| valores ausentes: 0")
print("Especificación:", json.load(open(ROOT / "data/experiments/oe_n5_2026-10-06/f1_v3_summary.json", encoding="utf-8"))["definition"])
print("Evaluadores humanos con datos reales (SUS / panel):", 0, "— no hay datos y no se simulan")''',
}

if __name__ == "__main__":
    for oe in SPEC:
        print(build(oe))
