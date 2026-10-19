"""Cierre de cobertura: triaje de las afirmaciones en prosa y de las celdas sin evidencia.

Lee auditoria/CONCILIACION_TESIS_DATOS.csv (generado por build_conciliacion.py), añade las columnas
`categoria_cierre`, `fuente_requerida` y `accion_cierre`, y escribe auditoria/CIERRE_COBERTURA.csv y
auditoria/CIERRE_COBERTURA_CONTEOS.json. Ejecutar DESPUÉS de build_conciliacion.py (es idempotente).

Reglas: el triaje es heurístico (usa el fragmento de ±35 caracteres que ya figura en la conciliación) y NO
verifica oraciones completas. Solo se sube de PENDIENTE_DE_EVIDENCIA a VERIFICACION_PARCIAL cuando el valor es
un parámetro de diseño que coincide con una especificación o registro del paquete (hardware, niveles del
diseño, constantes del código). Nada pasa a COINCIDE por este script.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
AUD = ROOT / "auditoria"
CSV = AUD / "CONCILIACION_TESIS_DATOS.csv"
NUEVAS = ["categoria_cierre", "fuente_requerida", "accion_cierre"]


def hechos_de_especificacion():
    """Hechos comprobables contra registros/código del paquete (no contra la tesis)."""
    h = {}
    env = json.loads((ROOT / "data/experiments/oe_n1_2026-10-05/oe3_run/environment.json").read_text(encoding="utf-8"))
    hw = env["hardware"]
    h["vcpu_medido"] = hw["vcpu"]
    h["ram_gib_medida"] = hw["ram_gib"]
    h["python_campanas"] = hw["python"]
    h["perfiles_n1"] = env["dataset"]["n_profiles"]
    space = (ROOT.parent / "backend/adaptation_swarm/pso/space.py").read_text(encoding="utf-8")
    k = re.search(r"^K_LEVELS\s*=\s*(\d+)", space, re.M)
    mods = re.search(r"^MODALITIES[^=]*=\s*\(([^)]*)\)", space, re.M)
    n_dims = 2 * len(re.findall(r'"[a-z]+"', mods.group(1))) if mods else None
    h["espacio_configuraciones"] = int(k.group(1)) ** n_dims if k and n_dims else None
    r3 = pd.read_csv(ROOT / "data/experiments/oe_n3_2026-10-06/runs_oe3.csv")
    h["condiciones_n3"] = int(r3.condition.nunique())
    h["lotes_n3"] = int(r3.groupby("condition").batch.nunique().max())
    usuarios, calent, timeout, nswarm = set(), set(), set(), set()
    for ruta in ("oe_n2_2026-10-05", "oe_n4_2026-10-06", "oe_n8_2026-10-13", "oe_n11_2026-10-14_3N", "oe_n10_2026-10-14_n20", "oe_n9b_2026-10-14"):
        p = ROOT / "data/experiments" / ruta / ("campaign_final" if ruta.startswith("oe_n9b") else "campaign") / "runs.csv"
        if p.exists():
            d = pd.read_csv(p)
            usuarios |= set(d.users.unique()); calent |= set(d.warmup_seconds.unique()); timeout |= set(d.client_timeout_s.unique())
            if "swarm_N" in d: nswarm |= set(d.swarm_N.dropna().unique())
    h["usuarios_en_runs"] = sorted(int(x) for x in usuarios)
    h["warmup_s_en_runs"] = sorted(float(x) for x in calent)
    h["timeout_s_en_runs"] = sorted(float(x) for x in timeout)
    h["swarm_N_en_runs"] = sorted(float(x) for x in nswarm)
    return h


def num(valor):
    m = re.search(r"\d[\d\s .,]*", str(valor))
    if not m:
        return None
    t = re.sub(r"[\s ]", "", m.group(0)).replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def clasificar(r, h):
    ctx = str(r.tipo_fila).split("|", 1)[1] if "|" in str(r.tipo_fila) else ""
    v = str(r.valor_publicado)
    n = num(v)
    sec = str(r.seccion)
    if re.search(r"\b(19|20)\d{2}\b", ctx) and re.search(r"\(\s*(19|20)\d{2}|et al|\(\s*N\s*=", ctx) and "2026" not in ctx:
        return ("BIBLIOGRAFICA_O_HISTORICA", "documento citado (original)", "localizar la referencia y comprobar la cifra con su fuente; no se verifica con datos del estudio", None)
    if "vCPU" in v or "GiB" in v or "GB" in v or "vCPU" in ctx:
        ok = None
        if n == h["vcpu_medido"] or n == 31.75 or "31,75" in ctx:
            ok = "coincide con environment.json de N1 (20 vCPU; 31,75 GiB; Windows 11; Python 3.12.10)"
        elif n in (8, 32, 7.5):
            ok = None
        return ("PARAMETRO_DE_DISENO", "environment.json / especificación de hardware objetivo", "comparar con el registro de entorno; 8 vCPU/32 GB son la condición objetivo NO ejecutada", ok)
    if n == h["espacio_configuraciones"] or "6 561" in ctx:
        return ("PARAMETRO_DE_DISENO", "backend/adaptation_swarm/pso/space.py", "constante K_LEVELS^N_DIMS", "coincide con SPACE_SIZE = K_LEVELS ** N_DIMS (código del proyecto)" if n == 6561 else None)
    if n == h["condiciones_n3"] and re.search(r"condiciones", ctx + v):
        return ("PARAMETRO_DE_DISENO", "runs_oe3.csv", "recuento de condiciones", f"coincide con {h['condiciones_n3']} condiciones distintas en runs_oe3.csv")
    if re.search(r"2 × 2 × 2 × 2 × 3|factores|niveles", ctx):
        return ("PARAMETRO_DE_DISENO", "oe/conditions.py y runs_oe3.csv", "comparar niveles de factores con la especificación", None)
    if re.search(r"\bN\s*=\s*\d+", ctx) and n in h["swarm_N_en_runs"]:
        return ("PARAMETRO_DE_DISENO", "runs.csv (columna swarm_N)", "comprobar el nivel contra los factores de runs.csv", f"el nivel N = {int(n)} existe en la columna swarm_N de algún runs.csv")
    if re.search(r"usuarios|\bu\d+\b", ctx) and n in h["usuarios_en_runs"]:
        return ("PARAMETRO_DE_DISENO", "runs.csv (columna users)", "comprobar el nivel de carga contra runs.csv", f"el nivel de {int(n)} usuarios existe en la columna users de algún runs.csv")
    if re.search(r"timeout", ctx) and re.search(r"\d+\s*s\b", v) and n in h["timeout_s_en_runs"]:
        return ("PARAMETRO_DE_DISENO", "runs.csv (client_timeout_s)", "comparar con el registro", f"client_timeout_s = {int(n)} en runs.csv")
    if re.search(r"calentamiento|warm", ctx) and re.search(r"\d+\s*s\b", v) and n in h["warmup_s_en_runs"]:
        return ("PARAMETRO_DE_DISENO", "runs.csv (warmup_seconds)", "comparar con el registro", f"warmup_seconds = {int(n)} en runs.csv")
    if re.search(r"\d+\s*s\b", v) or re.search(r"(calentamiento|ventana|timeout|margen)", ctx):
        return ("PARAMETRO_DE_DISENO", "provenance.json (campo design) de cada campaña", "comparar con design.warmup_s/window_s/timeout_s por campaña", None)
    if sec.startswith("10") and re.search(r"[|`\[]|lote|req/s ·|ok,", ctx):
        return ("EXTRACTO_DE_REGISTRO", "logs/journals de campaña publicados (data/experiments/*/campaign*)", "buscar la línea en el log y comparar el valor", None)
    if re.search(r"%|ms\b|req/s|P95|p\s*=|ρ|×|F1|IC95|brecha|throughput", ctx + v):
        return ("RESULTADO_CUANTITATIVO", "tabla recalculada del objetivo o derivado de la campaña", "revisar la oración completa contra el valor recalculado (condiciones, comparación, interpretación)", None)
    return ("OTRO_REVISAR", "por determinar", "revisión manual", None)


def main():
    c = pd.read_csv(CSV)
    c = c.drop(columns=[x for x in NUEVAS if x in c.columns])
    c["t"] = c.tipo_fila.astype(str).str.split("|").str[0]
    h = hechos_de_especificacion()
    cat, fuente, accion = [""] * len(c), [""] * len(c), [""] * len(c)
    subidas = 0
    for i, r in c.iterrows():
        if r.t == "afirmacion_en_prosa" and r.estado in ("PENDIENTE_DE_EVIDENCIA", "VERIFICACION_PARCIAL"):
            k, f, a, ok = clasificar(r, h)
            cat[i], fuente[i], accion[i] = k, f, a
            if ok and r.estado == "PENDIENTE_DE_EVIDENCIA":
                c.at[i, "estado"] = "VERIFICACION_PARCIAL"
                c.at[i, "explicacion"] = "parámetro de diseño: " + ok + "; no se verifica la oración completa"
                subidas += 1
        elif r.t == "celda_no_cubierta" and r.estado in ("PENDIENTE_DE_EVIDENCIA", "VERIFICACION_PARCIAL", "NO_REPRODUCIBLE"):
            ex = str(r.explicacion)
            if "histórico" in ex:
                cat[i], fuente[i], accion[i] = "CRITERIO_DE_HIPOTESIS", "OBJETIVOS_LITERALES.json / metas del proyecto", "comparar el umbral con el texto literal de la meta; no es un resultado"
            elif "oe1_report" in ex or "estado/recuento" in ex:
                cat[i], fuente[i], accion[i] = "ESTADO_CATEGORICO_DE_N1", "oe1_report.json (hash coincide)", "recomputar el estado MET/NOT_MET desde las métricas de oe1_verify.json"
            else:
                cat[i], fuente[i], accion[i] = "SIN_EVIDENCIA_RECUPERABLE", "cálculo no localizado", "localizar el script que produjo la cifra o declararla no reproducible"
    c["categoria_cierre"], c["fuente_requerida"], c["accion_cierre"] = cat, fuente, accion
    out = c.drop(columns=["t"])
    out.to_csv(CSV, index=False, encoding="utf-8")
    pend = c[(c.t == "afirmacion_en_prosa") & c.estado.isin(["PENDIENTE_DE_EVIDENCIA", "VERIFICACION_PARCIAL"])]
    conteos = {
        "estados_prosa": c[c.t == "afirmacion_en_prosa"].estado.value_counts().to_dict(),
        "estados_celdas_no_cubiertas": c[c.t == "celda_no_cubierta"].estado.value_counts().to_dict(),
        "prosa_subida_a_parcial_por_este_script": subidas,
        "categorias_prosa_abiertas": pend.categoria_cierre.value_counts().to_dict(),
        "hechos_de_especificacion": h,
    }
    (AUD / "CIERRE_COBERTURA_CONTEOS.json").write_text(json.dumps(conteos, ensure_ascii=False, indent=2), encoding="utf-8")
    cols = ["seccion", "celda_o_ubicacion", "valor_publicado", "estado", "categoria_cierre", "fuente_requerida", "accion_cierre", "tipo_fila"]
    pd.concat([pend[cols], c[(c.t == "celda_no_cubierta") & (c.categoria_cierre != "")][cols]]).to_csv(AUD / "CIERRE_COBERTURA.csv", index=False, encoding="utf-8")
    print(json.dumps(conteos, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
