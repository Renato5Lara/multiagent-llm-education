"""Genera EVIDENCE_MANIFEST.csv: SHA-256 recalculado sobre los archivos reales publicados (nunca copiado de registros previos).
Uso (mantenimiento): python scripts/build_manifest.py"""
import csv, re
SAN = {}
from repro_lib import ROOT, EXP, META, MANIFEST, sha256

CAMP = {  # directorio → (campaña, objetivo, nota de estado)
    "oe_n1_2026-10-05": ("N1", "OE1", "no oficial"), "oe_n2_2026-10-05": ("N2", "OE2", "no oficial"), "oe_n3_2026-10-06": ("N3", "OE3", "no oficial"), "oe_n3r_2026-10-19": ("N3-R", "OE3", "réplica independiente de N3 (semillas nuevas), 2026-10-19; exploratoria, no oficial"),
    "oe_n4_2026-10-06": ("N4", "OE4", "no oficial"), "oe_n5_2026-10-06": ("N5", "OE5", "provisional (especificación v3; official=False)"),
    "oe_n6_2026-10-06": ("N6", "transversal", "consolidación; no oficial"), "oe_n7_2026-10-06": ("N7", "transversal", "estudio final / pruebas; no oficial"),
    "oe_n8_2026-10-13": ("N8", "OE4", "no oficial; contiene además los scripts y salidas de re-análisis (D2.7)"),
    "oe_n9_2026-10-13": ("N9", "OE2", "ABORTADA Y DESCARTADA tras 38 de 160 ejecuciones; no usar para ningún resultado"),
    "oe_n9b_2026-10-14": ("N9b", "OE2", "réplica integrada 160/160; no oficial"),
    "oe_n10_2026-10-14_n20": ("N8b", "OE4", "el informe la llama N8b; el directorio se llama oe_n10; no oficial"),
    "oe_n11_2026-10-14_3N": ("N11", "OE4", "no oficial; dos tramos con régimen de equipo distinto"),
}
DERIVED_DIRS = ("oe2_reanalysis", "oe3_reanalysis", "oe4_nvar", "oe4_n11", "oe2_aux", "oe5_f1_repro", "oe1_verify", "d27_verificacion", "state_of_art")
RAW_RUN_FILES = ("campaign/runs.csv", "campaign_final/runs.csv", "runs_oe3.csv")


def classify(rel: str):
    p = rel.split("/", 1)[1]
    name = p.rsplit("/", 1)[-1]
    if name.endswith(".sanitizado.log"):
        return "log_sanitizado", "copia SANITIZADA del log original (rutas locales sustituidas); NO es idéntica al original: ver data/metadata/SANITIZACION.csv", ""
    if p in RAW_RUN_FILES:
        return "dato_original", "resumen por corrida producido por el arnés de campaña (una fila por corrida real)", "adaptation_swarm.oe.http_campaign / runner"
    if p.startswith("scripts/") or name.endswith(".py"):
        return "codigo", "script de análisis del proyecto (sin modificar)", ""
    if name in ("SHA256SUMS",) or name.startswith("SHA256SUMS"):
        return "metadatos", "hashes registrados por el proyecto al cerrar la campaña", ""
    if name in ("manifest.json", "provenance.json", "plan.json", "environment.json", "journal_summary.json") or p.endswith("runs.journal.jsonl"):
        return "metadatos", "procedencia/plan/entorno/diario registrados por el arnés durante la ejecución", "adaptation_swarm.oe.http_campaign"
    if any(p.startswith(d + "/") for d in DERIVED_DIRS) or name in ("tabla_por_carga.csv", "tabla_por_configuracion.csv", "analysis.json"):
        return "derivado", "salida de análisis calculada a partir de los datos originales", ""
    if name.endswith((".md",)):
        return "documentacion", "documento del proyecto", ""
    if name.endswith(".log"):
        return "log", "registro de ejecución", ""
    if name.endswith(".png"):
        return "derivado", "figura generada por el proyecto", ""
    return "otro", "", ""


_s = META / "SANITIZACION.csv"
if _s.exists():
    SAN = {r["copia_sanitizada"]: r["sha256_original"] for r in csv.DictReader(open(_s, encoding="utf-8"))}
rows = []
for i, f in enumerate(sorted(p for p in EXP.rglob("*") if p.is_file()), 1):
    rel = f.relative_to(EXP).as_posix()
    d = rel.split("/")[0]
    camp, obj, nota = CAMP[d]
    rol, desc, gen = classify(rel)
    date = re.search(r"(\d{4}-\d{2}-\d{2})", d)
    if "data/experiments/" + rel in SAN and not rel.endswith(".sanitizado.log"):
        desc += " [SANITIZADO: rutas locales sustituidas; no idéntico al original, ver data/metadata/SANITIZACION.csv]"
    rows.append(dict(id=f"EV-{i:04d}", ruta="data/experiments/" + rel, campana=camp, objetivo=obj, rol=rol, descripcion=desc,
                     procedencia="backend/experiments/" + rel + " (copia byte a byte; ver data/metadata/STAGING_REPORT.csv)", bytes=f.stat().st_size, sha256=sha256(f),
                     fecha_documentada=(date.group(1) if date else "") + " (nombre del directorio; no es la fecha del archivo)", script_generador=gen,
                     estado_campana=nota, sha256_original=SAN.get("data/experiments/" + rel, "")))
META_DESC = {"informe_D2.9.7_tablas.json": ("informe", "transcripcion_documental", "Tablas del informe D2.9.7 extraídas del DOCX (SHA-256 del DOCX fuente dentro del JSON). NO es un registro experimental.", "valores publicados de referencia"),
             "N9_tmp_raw_hashes.csv": ("N9", "metadatos", "Tamaño y SHA-256 de los 76 CSV por petición de la campaña N9 abortada (no publicados).", CAMP["oe_n9_2026-10-13"][2]),
             "N9_ABORTADA.md": ("N9", "documentacion", "Explicación del estado real de N9 (38 ejecuciones iniciadas de 160; descartada).", CAMP["oe_n9_2026-10-13"][2]),
             "STAGING_REPORT.csv": ("transversal", "metadatos", "Qué archivos de backend/experiments se copiaron y cuáles se excluyeron, con el motivo.", ""),
             "SANITIZACION.csv": ("transversal", "metadatos", "Hash del original (no publicado) y de la copia sanitizada, con las reglas aplicadas.", "")}
for f in sorted((META).glob("*")):
    camp, rol, desc, nota = META_DESC.get(f.name, ("transversal", "metadatos", "", ""))
    rows.append(dict(id=f"EV-{len(rows)+1:04d}", ruta="data/metadata/" + f.name, campana=camp, objetivo="transversal", rol=rol, descripcion=desc,
                     procedencia="creado para esta publicación" if f.name != "informe_D2.9.7_tablas.json" else "extracción automática del DOCX D2.9.7", bytes=f.stat().st_size,
                     sha256=sha256(f), fecha_documentada="", script_generador="stage_evidence.py" if f.name in ("STAGING_REPORT.csv", "SANITIZACION.csv") else "", estado_campana=nota, sha256_original=""))
with open(MANIFEST, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
print(len(rows), "entradas")
