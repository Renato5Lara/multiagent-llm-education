"""Herramienta de MANTENIMIENTO (no la usa el evaluador): copia, sin modificar su contenido, la evidencia mínima de
backend/experiments/ a reproducibility/data/experiments/ y registra qué se copió y qué se excluyó (y por qué).
Los archivos se copian byte a byte (shutil.copy2); no se redacta ni se edita nada, para no romper los hashes."""
import csv, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "backend" / "experiments"
DST = ROOT / "reproducibility" / "data" / "experiments"
if DST.exists():
    shutil.rmtree(DST)
CAMPAIGNS = ["oe_n1_2026-10-05", "oe_n2_2026-10-05", "oe_n3_2026-10-06", "oe_n4_2026-10-06", "oe_n5_2026-10-06", "oe_n6_2026-10-06", "oe_n7_2026-10-06",
             "oe_n8_2026-10-13", "oe_n9_2026-10-13", "oe_n9b_2026-10-14", "oe_n10_2026-10-14_n20", "oe_n11_2026-10-14_3N"]
EXCL_DIRS = {"raw": "registros por petición (Locust): volumen alto; se conservan localmente, sus hashes están en manifest.json de cada campaña",
             "campaign.tmp-raw": "ídem (campaña N9 abortada: se listan sus hashes en data/metadata/N9_tmp_raw_hashes.csv)",
             "inprocess": "observaciones in-process de gran tamaño (regenerables); no son entrada de las tablas HTTP del informe",
             "run": "observaciones N3 de gran tamaño (statistical_input.csv 45 MB); la entrada del análisis es runs_oe3.csv",
             "oe3_run": "observaciones N1 de gran tamaño", "oe4_run": "observaciones N1 de gran tamaño",
             "state_of_art": "metadatos bibliográficos de terceros con correos electrónicos; no son entrada de ningún cálculo", "d26_build": "constructor de DOCX; no es parte del análisis",
             "d27_build": "constructor de DOCX; no es parte del análisis", "d28_build": "constructor de DOCX; no es parte del análisis",
             "failed_attempt1_zerodiv": "intento fallido archivado localmente; no es entrada de ninguna tabla", "__pycache__": "caché"}
EXCL_SUFFIX = {".err": "salida de error (puede contener rutas locales)", ".pyc": "caché"}
EXCL_FILES = {n: "script de búsqueda bibliográfica que incorpora el correo personal del autor (privacidad); no es entrada de ningún cálculo"
              for n in ("audit_referencias.py", "busqueda_estructurada.py", "crossref_search.py", "fetch_metadata.py", "openalex_numeric.py", "openalex_search.py", "build_conciliacion.py")}
EXCL_FILES.update({n: "registro de pytest con rutas locales del equipo; no es entrada de ningún cálculo" for n in ("pytest_adaptation_swarm.log", "pytest_adaptation_swarm_continuacion.log", "pytest_adaptation_swarm_utf8.log")})
MAX_BYTES = 3_000_000
# Registros originales necesarios para auditar petición -> corrida -> tabla (se publican; anulan las exclusiones por tamaño/carpeta)
INCLUDE = ("oe_n2_2026-10-05/campaign/raw/", "oe_n4_2026-10-06/campaign/raw/", "oe_n8_2026-10-13/campaign/raw/", "oe_n10_2026-10-14_n20/campaign/raw/",
           "oe_n9b_2026-10-14/campaign/raw/", "oe_n9b_2026-10-14/campaign_final/raw/", "oe_n11_2026-10-14_3N/campaign/raw/",
           "oe_n1_2026-10-05/oe3_run/raw_observations.csv", "oe_n1_2026-10-05/oe4_run/raw_observations.csv", "oe_n3_2026-10-06/run/raw_observations.csv",
           "oe_n4_2026-10-06/inprocess/raw_observations.csv")
only_log_n9 = {"oe_n9_2026-10-13": {"campaign.log"}}
rows = []
for camp in CAMPAIGNS:
    base = SRC / camp
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(SRC)
        parts = set(rel.parts[1:-1])
        why = None
        if camp in only_log_n9 and p.name not in only_log_n9[camp] and "campaign.tmp-raw" not in parts:
            why = "N9 abortada: solo se publica campaign.log"
        for d in parts:
            if d in EXCL_DIRS and camp not in only_log_n9:
                why = EXCL_DIRS[d]
            elif d in EXCL_DIRS and d != "campaign.tmp-raw":
                why = EXCL_DIRS[d]
        if "campaign.tmp-raw" in parts:
            why = EXCL_DIRS["campaign.tmp-raw"]
        if rel.as_posix() in ("oe_n9_2026-10-13/campaign.log",):
            why = "contiene rutas locales (se publica la copia sanitizada)"
        if p.name in EXCL_FILES:
            why = EXCL_FILES[p.name]
        if p.suffix in EXCL_SUFFIX:
            why = EXCL_SUFFIX[p.suffix]
        if p.name == "runs.jsonl":
            why = "redundante con runs.csv (misma información anidada); hash en manifest.json"
        if p.suffix == ".jsonl" and p.name != "runs.journal.jsonl" and p.name != "runs.jsonl":
            why = "observaciones de gran tamaño"
        if why and rel.as_posix().startswith(INCLUDE) and p.suffix != ".err" and p.name not in EXCL_FILES:
            why = None
        if why is None and p.stat().st_size > MAX_BYTES and not rel.as_posix().startswith(INCLUDE):
            why = f"supera {MAX_BYTES} bytes"
        if why is None:
            out = DST / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)
        rows.append({"ruta_origen": str(Path("backend/experiments") / rel).replace("\\", "/"), "bytes": p.stat().st_size, "accion": "copiado" if why is None else "excluido", "motivo": why or ""})
# --- copias sanitizadas para publicación (el original NO se toca y NO se publica; el sanitizado tiene otro nombre y otro hash)
import hashlib, re
SANITIZE = {"oe_n9_2026-10-13/campaign.log": "oe_n9_2026-10-13/campaign.sanitizado.log"}
RULES = [(r"[A-Za-z]:(\\+)Users\1[^\r\n'\"]*?\1mas-run", "<RAIZ_REPO>", "ruta local hasta la raíz del repositorio (cualquier nivel de escape de barras)"),
         (r"[A-Za-z]:(\\+)Users\1[^\\\s'\",]+", "<RUTA_USUARIO>", "ruta bajo el perfil de usuario de Windows (nombre de usuario)")]
TEXT_SUFFIX = {".json", ".jsonl", ".log", ".md", ".csv", ".txt", ".py"}


def sanitize_text(txt):
    n_tot = 0
    for pat, rep, _ in RULES:
        txt, n = re.subn(pat, lambda m, r=rep: r, txt)
        n_tot += n
    return txt, n_tot


san = []
for src_rel, dst_rel in SANITIZE.items():
    raw = (SRC / src_rel).read_bytes()
    txt, n_tot = sanitize_text(raw.decode("utf-8"))
    out = DST / dst_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(txt.encode("utf-8"))
    for r in rows:
        if r["ruta_origen"].endswith(src_rel):
            r["motivo"] = "contiene rutas locales; se publica solo la copia sanitizada " + dst_rel
    san.append({"original(no_publicado)": "backend/experiments/" + src_rel, "sha256_original": hashlib.sha256(raw).hexdigest(), "copia_sanitizada": "data/experiments/" + dst_rel,
                "sha256_sanitizada": hashlib.sha256(out.read_bytes()).hexdigest(), "sustituciones": n_tot, "reglas": " | ".join(f"{a} -> {b} ({c})" for a, b, c in RULES),
                "identica_al_original": "NO"})
for f in sorted(DST.rglob("*")):
    if f.is_file() and f.suffix in TEXT_SUFFIX and f.name != "campaign.sanitizado.log":
        raw = f.read_bytes()
        try:
            txt, n = sanitize_text(raw.decode("utf-8"))
        except UnicodeDecodeError:
            continue
        if n:
            f.write_bytes(txt.encode("utf-8"))
            san.append({"original(no_publicado)": "backend/experiments/" + f.relative_to(DST).as_posix(), "sha256_original": hashlib.sha256(raw).hexdigest(),
                        "copia_sanitizada": "data/experiments/" + f.relative_to(DST).as_posix(), "sha256_sanitizada": hashlib.sha256(f.read_bytes()).hexdigest(), "sustituciones": n,
                        "reglas": " | ".join(f"{a} -> {b}" for a, b, _ in RULES), "identica_al_original": "NO"})
            for r in rows:
                if r["ruta_origen"] == "backend/experiments/" + f.relative_to(DST).as_posix():
                    r["motivo"] = "copiado con rutas locales sustituidas (ver SANITIZACION.csv)"
with open(ROOT / "reproducibility" / "data" / "metadata" / "SANITIZACION.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(san[0])); w.writeheader(); w.writerows(san)
with open(ROOT / "reproducibility" / "data" / "metadata" / "STAGING_REPORT.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
c = [r for r in rows if r["accion"] == "copiado"]
print(len(c), "copiados", round(sum(r["bytes"] for r in c) / 1e6, 1), "MB;", len(rows) - len(c), "excluidos")
