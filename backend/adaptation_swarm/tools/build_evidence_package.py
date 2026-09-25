"""Construye un paquete de evidencia experimental LIMPIO y verificable (solo COPIAS; no mueve ni borra nada):
datos de entrada, corridas congeladas (poc-1/poc-2), auditorías, cargas, biblioteca (inventario, manifiestos, mapa), configuración, entorno y un
MANIFEST.sha256.

    python -m adaptation_swarm.tools.build_evidence_package --out DIR --dry-run [--sealed-copy DIR]   # valida todo SIN escribir nada
    python -m adaptation_swarm.tools.build_evidence_package --out DIR --audit-dir DIR [--sealed-copy DIR]   # genera un paquete NUEVO
    python -m adaptation_swarm.tools.build_evidence_package --verify DIR        # comprueba MANIFEST.sha256
    python -m adaptation_swarm.tools.build_evidence_package --check DIR         # además comprueba los hechos (latest, corridas↔versión, head, F1, …)

`--out` es OBLIGATORIO (no hay destino por defecto) y jamás puede ser un paquete ya existente ni el paquete histórico `evidence_package_2026-09-23`.
"""

import argparse
import csv
import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.swarm_adaptation import SwarmCycle, SwarmRun

from adaptation_swarm.multimodal.versioning import latest_version
from adaptation_swarm.tools.library_inventory import inventory, to_markdown
from adaptation_swarm.tools.seal_audio import verify_sealed

ROOT = Path(__file__).resolve().parents[3]          # raíz del repo
BACK = ROOT / "backend"
FROZEN_RUNS = ("corrida-poc-1", "corrida-poc-2")
HISTORIC_PACKAGES = ("evidence_package_2026-09-23",)          # congelado: nunca se regenera ni se sobrescribe
EXPECTED_F1 = 0.8031415                                        # F1_adapt congelado de ambas corridas (--check)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def _run(*cmd: str) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd=ROOT).stdout.strip()
    except Exception as exc:
        return f"no disponible: {exc}"


def latest_library_version(lib: Path) -> str:
    """Última versión de la biblioteca por NÚMERO de versión (`lib-v10` > `lib-v9`; el orden lexicográfico las invertía).
    Exige que exista su `manifest.json`."""
    version = latest_version(lib)
    if version is None or not (lib / version / "manifest.json").is_file():
        raise SystemExit(f"no hay una versión de biblioteca con manifest.json en {lib}")
    return version


def alembic_head(back: Path = BACK) -> str:
    """Head REAL de Alembic, obtenido dinámicamente ejecutando `python -m alembic heads` desde `backend/` (donde vive
    `alembic.ini`). Si no se puede obtener, falla: nunca se registra un texto de error como si fuera el head."""
    res = subprocess.run([sys.executable, "-m", "alembic", "heads"], capture_output=True, text=True, timeout=120, cwd=back)
    heads = re.findall(r"^([0-9a-f]+) \(head\)", res.stdout, flags=re.MULTILINE)
    if res.returncode != 0 or len(heads) != 1:
        raise RuntimeError(f"no se pudo obtener el head de Alembic (rc={res.returncode}, heads={heads}): {res.stderr.strip()[-300:]}")
    return heads[0]


def collect_environment(library_latest: str) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(), "python": sys.version, "platform": platform.platform(),
        "podman": _run("podman", "--version"), "node": _run("node", "--version"), "gxx": _run("g++", "--version").splitlines()[:1],
        "chrome": _run("google-chrome", "--version"), "images": _run("podman", "images", "--format", "{{.Repository}}:{{.Tag}} {{.Digest}}"),
        "git_head": _run("git", "rev-parse", "HEAD"), "git_branch": _run("git", "branch", "--show-current"),
        "alembic_head": alembic_head(), "library_latest": library_latest,
    }


def check_destination(out: Path) -> None:
    """El destino debe ser NUEVO y distinto del paquete histórico (por nombre y por ruta resuelta)."""
    historic = [(BACK / "experiments" / n).resolve() for n in HISTORIC_PACKAGES]
    if out.name in HISTORIC_PACKAGES or out.resolve() in historic:
        raise SystemExit(f"{out}: es el paquete histórico congelado; jamás se regenera ni se sobrescribe")
    if out.exists():
        raise SystemExit(f"{out} ya existe: los paquetes de evidencia no se sobrescriben")


def preflight(out: Path, sealed_copy: Path | None = None) -> dict:
    """Todas las validaciones previas, SIN escribir nada: destino, última versión (numérica), integridad de la biblioteca, corridas↔versión,
    head real de Alembic y (si se indica) la copia sellada del audio."""
    check_destination(out)
    lib = ROOT / "datasets" / "adaptation_library"
    latest = latest_library_version(lib)
    inv = inventory(lib, verify_hashes=True)
    if inv["latest"] != latest:
        raise SystemExit(f"inconsistencia: inventario latest={inv['latest']} ≠ {latest}")
    if inv["summary"]["any_hash_mismatch"] or inv["summary"]["any_manifest_id_mismatch"]:
        raise SystemExit("la biblioteca tiene hashes incorrectos o un manifiesto alterado: no se genera evidencia sobre ella")
    missing_runs = [r for r in FROZEN_RUNS if r not in inv["runs"]]
    if missing_runs:
        raise SystemExit(f"corridas sin versión de biblioteca identificable en experiments/results: {missing_runs}")
    sealed = None
    if sealed_copy is not None:
        sealed = verify_sealed(sealed_copy)
        if not sealed["ok"]:
            raise SystemExit(f"la copia sellada no verifica: {sealed}")
    env = collect_environment(latest)
    return {"lib": lib, "latest": latest, "inventory": inv, "env": env, "sealed": sealed}


def build(out: Path, sealed_copy: Path | None = None, audit_dir: Path | None = None) -> dict:
    """`audit_dir`: carpeta (fuera del repo) con los informes `.md` que se copian a `03_informes/`; sin valor por defecto."""
    pre = preflight(out, sealed_copy)          # antes de crear nada: si algo falla, no queda un paquete a medias
    if audit_dir is None or not audit_dir.is_dir():
        raise SystemExit("--audit-dir es obligatorio para generar: carpeta con los informes .md de 03_informes/")
    lib, latest, inv, env = pre["lib"], pre["latest"], pre["inventory"], pre["env"]
    out.mkdir(parents=True)
    copied: list[str] = []

    def cp(src: Path, dst_rel: str) -> None:
        if not src.exists():
            return
        dst = out / dst_rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst_rel)

    ds = ROOT / "datasets" / "synthetic_profiles"
    for f in sorted(ds.glob("*")):
        cp(f, f"01_datos_de_entrada/synthetic_profiles/{f.name}")
    _write_library_section(out, lib, inv, latest, pre["sealed"], sealed_copy)
    res = BACK / "experiments" / "results"
    for f in sorted(res.glob("adaptation_swarm_*")) + sorted(res.glob("library_semantic_audit_*")):
        cp(f, f"02_corridas_y_auditorias/{f.name}")
    for f in sorted(audit_dir.glob("*")):
        if f.suffix == ".md":
            cp(f, f"03_informes/{f.name}")
    lt = BACK / "loadtest" / "results"
    for f in sorted(lt.rglob("*")):
        if f.is_file() and f.suffix in {".csv", ".md", ".json", ".jtl"} and f.stat().st_size < 30_000_000:
            cp(f, f"04_carga/{f.relative_to(lt).as_posix()}")
    cp(BACK / "adaptation_swarm" / "EVIDENCE_INDEX.md", "README_EVIDENCE_INDEX.md")
    for name in ("REPRODUCIBILITY.md", "README.md"):
        cp(BACK / "adaptation_swarm" / name, f"05_documentacion/{name}")
    cp(ROOT / "docs" / "architecture" / "ADR" / "ADR-0019-poc-adaptacion-multimodal-enjambre-pso.md", "05_documentacion/ADR-0019.md")
    cp(BACK / "loadtest" / "README.md", "05_documentacion/loadtest_README.md")
    cp(BACK / "tests" / "adaptation_swarm" / "LIBRARY_TESTS.md", "05_documentacion/LIBRARY_TESTS.md")
    for f in sorted((BACK / "adaptation_swarm" / "human_eval").rglob("*")):
        if f.is_file():
            cp(f, f"05_documentacion/human_eval/{f.relative_to(BACK / 'adaptation_swarm' / 'human_eval').as_posix()}")

    # exportación de las corridas congeladas desde PostgreSQL (una fila por ciclo)
    with SessionLocal() as s:
        for label in FROZEN_RUNS:
            run = s.get(SwarmRun, label)
            if run is None:
                continue
            (out / "02_corridas_y_auditorias").mkdir(exist_ok=True)
            (out / f"02_corridas_y_auditorias/db_{label}_run.json").write_text(json.dumps(
                {"run_label": label, "spec_version": run.spec_version, "dataset_version": run.dataset_version,
                 "library_version": run.library_version, "batch_seed": run.batch_seed, "config": run.config,
                 "config_hash": run.config_hash, "git_commit": run.git_commit, "summary": run.summary}, indent=2, default=str), encoding="utf-8")
            rows = list(s.scalars(select(SwarmCycle).where(SwarmCycle.run_label == label).order_by(SwarmCycle.profile_id)))
            with (out / f"02_corridas_y_auditorias/db_{label}_cycles.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["profile_id", "cycle_id", "status", "stop_reason", "k_stop", "t_conv_ms", "g_best_F", "predicted_dominant",
                            "g_best_S", "seed", "config_hash", "library_version"])
                for r in rows:
                    w.writerow([r.profile_id, r.id, r.status, r.stop_reason, r.k_stop, r.t_conv_ms, r.g_best_F, r.predicted_dominant,
                                json.dumps(r.g_best_S), r.seed, r.config_hash, r.library_version])
            copied += [f"02_corridas_y_auditorias/db_{label}_run.json", f"02_corridas_y_auditorias/db_{label}_cycles.csv"]

    # entorno y estado de Git
    (out / "06_entorno").mkdir()
    from adaptation_swarm.persistence.human_eval import HumanEvalRepository
    (out / "06_entorno/human_eval_status.json").write_text(json.dumps(HumanEvalRepository(SessionLocal).status_report(), indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "06_entorno/environment.json").write_text(json.dumps(env, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "06_entorno/pip_freeze.txt").write_text(_run(sys.executable, "-m", "pip", "freeze"), encoding="utf-8")
    (out / "06_entorno/git_status.txt").write_text(_run("git", "status", "--short"), encoding="utf-8")
    (out / "06_entorno/requirements.txt").write_text((BACK / "requirements.txt").read_text(), encoding="utf-8")
    copied += ["06_entorno/human_eval_status.json", "06_entorno/environment.json", "06_entorno/pip_freeze.txt", "06_entorno/git_status.txt", "06_entorno/requirements.txt"]

    files = sorted(p for p in out.rglob("*") if p.is_file() and p.name != "MANIFEST.sha256")
    (out / "MANIFEST.sha256").write_text("".join(f"{sha256(p)}  {p.relative_to(out).as_posix()}\n" for p in files), encoding="utf-8")
    return {"files": len(files), "out": str(out)}


def _write_library_section(out: Path, lib: Path, inv: dict, latest: str, sealed: dict | None, sealed_copy: Path | None) -> None:
    """07_biblioteca/: inventario, mapa corrida→versión, manifiestos de las versiones de las corridas y la última, y listas sha256 del audio
    (derivadas de los manifiestos: el audio NO va en Git ni en el paquete)."""
    d = out / "07_biblioteca"
    (d / "manifests").mkdir(parents=True)
    (d / "library_inventory.json").write_text(json.dumps(inv, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    (d / "library_inventory.md").write_text(to_markdown(inv), encoding="utf-8")
    featured = list(dict.fromkeys([*(inv["runs"][r] for r in FROZEN_RUNS), latest]))
    by_version = {v["version"]: v for v in inv["versions"]}
    for v in featured:
        shutil.copy2(lib / v / "manifest.json", d / "manifests" / f"{v}.manifest.json")
        man = json.loads((lib / v / "manifest.json").read_text(encoding="utf-8"))
        lines = sorted(f"{e['sha256']}  {v}/{e['path']}\n" for e in man["entries"] if e["modality"] == "audio")
        (d / f"audio_sha256_{v}.txt").write_text("".join(lines), encoding="utf-8")
    (d / "library_map.json").write_text(json.dumps({
        "estrategia": "Decisión C = D híbrida (DECISION-CLOSURE §14): en Git manifiestos + código/C++/.mmd/texto/SVG; fuera de Git audio (mp3) y _tts_cache/",
        "runs": {r: inv["runs"][r] for r in FROZEN_RUNS}, "latest": latest, "versions_order": inv["versions_order"],
        "featured_versions": featured,
        "audio_presence_on_this_machine": {v: by_version[v]["audio"] for v in featured},
        "svg_presence_on_this_machine": {v: by_version[v]["svg"] for v in featured},
        "audio_in_git": False, "audio_in_this_package": False,
        "external_audio_mechanism": "PENDIENTE (requisitos del asesor/jurado, almacenamiento, Git LFS/cuota, términos de OpenAI, retención v1-v4/v6-v8)",
        "verify_frozen_results_needs_library": False, "rerun_cycles_needs_audio_and_svg": True,
    }, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    if sealed_copy is not None and sealed is not None:
        (d / "sealed_copy").mkdir()
        shutil.copy2(sealed_copy / "SHA256SUMS", d / "sealed_copy" / "SHA256SUMS")
        shutil.copy2(sealed_copy / "README-SEALED.md", d / "sealed_copy" / "README-SEALED.md")
        (d / "sealed_copy" / "sealed_copy.json").write_text(json.dumps({
            "kind": "copia sellada LOCAL; NO constituye todavía almacenamiento externo de preservación institucional",
            "location_on_owner_machine": str(sealed_copy), "verified_at_package_build": sealed,
            "SHA256SUMS_sha256": sha256(sealed_copy / "SHA256SUMS"),
            "versions": sorted(p.name for p in sealed_copy.glob("lib-v*")),
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_package(out: Path, *, expected_f1: float = EXPECTED_F1, expect_no_humans: bool = True) -> list[str]:
    """Comprobación de HECHOS de un paquete generado (además de `verify`): devuelve la lista de problemas (vacía = consistente)."""
    problems = [f"hash: {b}" for b in verify(out)]
    env = json.loads((out / "06_entorno/environment.json").read_text())
    lmap = json.loads((out / "07_biblioteca/library_map.json").read_text())
    inv = json.loads((out / "07_biblioteca/library_inventory.json").read_text())
    numbers = {v: int(v.split("-")[1][1:]) for v in inv["versions_order"]}
    top = max(numbers, key=numbers.get)
    if lmap["latest"] != top or env["library_latest"] != top or inv["latest"] != top:
        problems.append(f"latest inconsistente: mapa={lmap['latest']} env={env['library_latest']} inventario={inv['latest']} máximo numérico={top}")
    if env.get("alembic_head") != alembic_head() or str(env.get("alembic_head", "")).startswith("FAILED"):
        problems.append(f"alembic_head del paquete ({env.get('alembic_head')}) ≠ head real ({alembic_head()})")
    for label in FROZEN_RUNS:
        run = json.loads((out / f"02_corridas_y_auditorias/adaptation_swarm_{label}.json").read_text())
        if run["config"]["library_version"] != lmap["runs"][label]:
            problems.append(f"{label}: config usa {run['config']['library_version']} pero el mapa dice {lmap['runs'][label]}")
        if abs(run["summary"]["f1"]["f1_adapt"] - expected_f1) > 1e-6:
            problems.append(f"{label}: F1_adapt {run['summary']['f1']['f1_adapt']} ≠ {expected_f1}")
        live = BACK / "experiments" / "results" / f"adaptation_swarm_{label}.json"
        if sha256(live) != sha256(out / f"02_corridas_y_auditorias/adaptation_swarm_{label}.json"):
            problems.append(f"{label}: el resultado vivo difiere del copiado")
        if not (out / f"07_biblioteca/manifests/{lmap['runs'][label]}.manifest.json").is_file():
            problems.append(f"falta el manifiesto de {lmap['runs'][label]}")
    if not (out / f"07_biblioteca/manifests/{top}.manifest.json").is_file():
        problems.append(f"falta el manifiesto de la última versión {top}")
    if inv["summary"]["any_hash_mismatch"] or inv["summary"]["any_manifest_id_mismatch"]:
        problems.append("el inventario del paquete registra hashes incorrectos")
    if lmap["audio_in_git"] or lmap["audio_in_this_package"] or any(out.rglob("*.mp3")):
        problems.append("el paquete no debe contener audio")
    he = json.loads((out / "06_entorno/human_eval_status.json").read_text())
    if expect_no_humans and (he["participants"] or he["sus_responses"] or he["gold_panel"].get("n_evaluators")):
        problems.append(f"se esperaban 0 participantes humanos: {he['participants']}/{he['sus_responses']}")
    return problems


def verify(out: Path) -> list[str]:
    bad = []
    for ln in (out / "MANIFEST.sha256").read_text().splitlines():
        h, rel = ln.split("  ", 1)
        p = out / rel
        if not p.exists() or sha256(p) != h:
            bad.append(rel)
    return bad


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="directorio NUEVO del paquete (obligatorio para generar o para --dry-run)")
    ap.add_argument("--dry-run", action="store_true", help="valida destino, biblioteca, corridas, Alembic y copia sellada sin escribir nada")
    ap.add_argument("--sealed-copy", help="directorio de la copia sellada local del audio (se verifica antes de generar)")
    ap.add_argument("--audit-dir", help="carpeta con los informes .md que se copian a 03_informes/ (obligatorio para generar; sin valor por defecto)")
    ap.add_argument("--verify")
    ap.add_argument("--check")
    a = ap.parse_args()
    if a.verify:
        bad = verify(Path(a.verify))
        print("VERIFICADO: todos los hashes coinciden" if not bad else f"DISCREPANCIAS: {bad}")
        sys.exit(1 if bad else 0)
    if a.check:
        problems = validate_package(Path(a.check))
        print("CONSISTENTE: hashes y hechos verificados" if not problems else "PROBLEMAS:\n- " + "\n- ".join(problems))
        sys.exit(1 if problems else 0)
    if not a.out:
        ap.error("--out es obligatorio: no hay destino por defecto")
    sealed = Path(a.sealed_copy) if a.sealed_copy else None
    if a.dry_run:
        pre = preflight(Path(a.out), sealed)
        print(json.dumps({"dry_run": True, "out": a.out, "latest": pre["latest"], "runs": pre["inventory"]["runs"],
                          "alembic_head": pre["env"]["alembic_head"], "library_hashes_ok": not pre["inventory"]["summary"]["any_hash_mismatch"],
                          "sealed_copy_verified": bool(pre["sealed"] and pre["sealed"]["ok"]), "would_write": "nada (dry-run)"}, indent=2))
        sys.exit(0)
    print(build(Path(a.out), sealed, Path(a.audit_dir) if a.audit_dir else None))
