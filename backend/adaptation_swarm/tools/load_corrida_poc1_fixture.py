"""Cargador de FIXTURE: reconstrucción PARCIAL de `corrida-poc-1` en el entorno aislado de pruebas.

NO reproduce la base original. Los artefactos congelados solo alcanzan para `swarm_runs` (1 fila) y `swarm_cycles` (100 filas). No existe ningún
artefacto de `swarm_iterations`, `agent_messages` ni `multimodal_packages` de esta corrida, y este cargador NO los inventa (una guardia en tiempo de
ejecución lo impide). Por eso `analysis/pso_audit` no se puede ejecutar sobre lo cargado. Campos exactos, derivados, regenerados y nulos: ver
`FIELDS` y la sección «Reconstrucción parcial de corrida-poc-1» de `adaptation_swarm/REPRODUCIBILITY.md`.

Garantías (todas comprobadas por `tests/adaptation_swarm/test_corrida_poc_1_loader.py`):
- destino: `DATABASE_URL` explícita del entorno (sin valores por defecto ni `backend/.env`) que sea EXACTAMENTE 127.0.0.1:55432/swarm_test (usuario `swarm_test`),
  sin query string (un `?host=...` de libpq redirigiría la conexión); dentro de la transacción, `current_database()`/`current_user` deben ser `swarm_test`;
- solo se ejecutan `SELECT` e `INSERT` sobre `swarm_runs` y `swarm_cycles`: nunca UPDATE, DELETE, TRUNCATE ni DDL, ni inserciones en otras tablas;
- los hashes de JSON, CSV, auditorías, manifiesto de biblioteca y dataset se verifican contra el manifiesto congelado ANTES de tocar la base;
- se rechaza si la etiqueta ya existe, si hay ciclos huérfanos con esa etiqueta o si algún id determinista ya existe;
- una sola transacción: cualquier error hace rollback completo; `--rehearse` inserta, verifica y hace rollback; `--commit` exige `--confirm`;
- el resumen de la carga se escribe en `--out-dir` (nunca dentro de resultados congelados, datasets ni paquetes de evidencia; nunca sobre un archivo existente).

    export DATABASE_URL=postgresql+psycopg://swarm_test:...@127.0.0.1:55432/swarm_test
    python -m adaptation_swarm.tools.load_corrida_poc1_fixture --rehearse --out-dir /ruta/fuera/del/repo
    python -m adaptation_swarm.tools.load_corrida_poc1_fixture --commit --confirm corrida-poc-1-reconstruccion-parcial --out-dir /ruta/fuera/del/repo
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, event, func, insert, or_, select, text
from sqlalchemy.engine import Connection, Engine

from adaptation_swarm.gold.f1 import f1_report
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.schemas.ids import derive_seed
from adaptation_swarm.tools import isolated_env as iso

LABEL = "corrida-poc-1"
CONFIRMATION = "corrida-poc-1-reconstruccion-parcial"
SCHEMA = "corrida-poc-1-partial-reconstruction-v1"
_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "urn:upao-mas-edu:adaptation-swarm:fixture:corrida-poc-1")
WRITABLE_TABLES = ("swarm_runs", "swarm_cycles")
NOT_RECONSTRUCTED_TABLES = ("swarm_iterations", "agent_messages", "multimodal_packages")     # por cycle_id; sin artefactos originales
RESULTS = iso.BACK / "experiments" / "results"
DOC = RESULTS / "adaptation_swarm_frozen_runs.md"

FIELDS = {
    "swarm_runs": {
        "exact": ["run_label", "spec_version", "dataset_version", "library_version", "batch_seed", "git_commit", "summary", "config.pso",
                  "config.fitness_weights"],
        "derived": ["config_hash (PSOParams(config.pso).config_hash())"],
        "regenerated": ["started_at (instante de la carga, NO de la ejecución original)"],
        "added": ["config.reconstruction (marca de reconstrucción parcial)"],
        "null": ["finished_at (no se registró; SQL NULL)"],
    },
    "swarm_cycles": {
        "exact": ["run_label", "profile_id", "status", "stop_reason", "k_stop", "t_conv_ms", "total_ms", "g_best_S", "g_best_F",
                  "predicted_dominant", "library_version", "error (null en el artefacto: se guarda SQL NULL)"],
        "derived": ["concept_id (profiles-v1.jsonl por profile_id)", "seed (derive_seed(batch_seed, profile_id, 0))",
                    "replicate (=0: run_experiment invoca run_cycle sin replicate)", "config_hash"],
        "regenerated": ["id (uuid5 determinista; el cycle_id original no se conserva)", "correlation_id (uuid5 determinista; ídem)",
                        "created_at (instante de la carga)"],
        "null": ["W", "g_best_x", "g_best_breakdown", "metrics", "pso_diagnostics (SQL NULL, no JSON null)"],
    },
}
LIMITATIONS = (
    "reconstrucción parcial: NO es la base original de corrida-poc-1",
    "swarm_iterations, agent_messages y multimodal_packages no se reconstruyen: no existen artefactos originales",
    "pso_audit no es ejecutable sobre lo cargado (requiere swarm_iterations)",
    "t_conv_ms y total_ms provienen del JSON, que los guarda redondeados a 2 decimales",
    "los ids de ciclo y correlación, y los timestamps, son regenerados; no coinciden con los de la ejecución original",
)


class FixtureError(RuntimeError):
    """Rechazo del cargador (destino, hashes, colisiones o verificación): la transacción, si existía, ya hizo rollback."""


# ── artefactos congelados ───────────────────────────────────────────────────────────────────────────────────────────
def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_artifacts(results: Path = RESULTS, repo: Path = iso.REPO) -> dict:
    """Lee el manifiesto congelado y VERIFICA los hashes de todo lo que se va a usar; no toca la base de datos."""
    doc = results / "adaptation_swarm_frozen_runs.md"
    manifest = json.loads(re.search(r"```json\n(.*?)\n```", doc.read_text(encoding="utf-8"), re.S).group(1))
    info = manifest["runs"][LABEL]
    checked: dict[str, str] = {}
    for name, sha in info["artifacts"].items():
        if _sha(results / name) != sha:
            raise FixtureError(f"{name} no coincide con el hash congelado: no se carga")
        checked[name] = sha
    d = manifest["dataset"]
    for key in ("profiles", "gold"):
        if _sha(repo / d[f"{key}_file"]) != d[f"{key}_sha256"]:
            raise FixtureError(f"{d[f'{key}_file']} no coincide con el hash congelado: no se carga")
        checked[d[f"{key}_file"]] = d[f"{key}_sha256"]
    lib = repo / info["library_manifest"]
    if _sha(lib) != info["library_manifest_sha256"]:
        raise FixtureError(f"{info['library_manifest']} no coincide con el hash congelado: no se carga")
    checked[info["library_manifest"]] = info["library_manifest_sha256"]
    run = json.loads((results / f"adaptation_swarm_{LABEL}.json").read_text(encoding="utf-8"))
    with (results / f"adaptation_swarm_{LABEL}_cases.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    cases = run["cases"]
    if len(cases) != 100 or len(rows) != 100 or [c["profile_id"] for c in cases] != [r["profile_id"] for r in rows]:
        raise FixtureError("el JSON y el CSV de casos no coinciden (se esperaban 100 casos en el mismo orden)")
    profiles = {}
    for line in (repo / d["profiles_file"]).read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        profiles[p["profile_id"]] = p["concept_id"]
    return {"manifest": manifest, "run": run, "profiles": profiles, "checked_sha256": checked}


def build_rows(art: dict, loaded_at: datetime) -> tuple[dict, list[dict]]:
    """Filas de `swarm_runs` y `swarm_cycles` (puro, sin base de datos). Lo que no existe en los artefactos queda NULL: nada se inventa."""
    run, man = art["run"], art["manifest"]
    cfg = run["config"]
    params = PSOParams(**cfg["pso"])
    if cfg["run_label"] != LABEL or cfg["library_version"] != man["runs"][LABEL]["library_version"]:
        raise FixtureError("la configuración del JSON no corresponde a corrida-poc-1 / a la biblioteca del manifiesto")
    run_row = {
        "run_label": LABEL, "spec_version": cfg["spec_version"], "dataset_version": man["dataset"]["version"],
        "library_version": cfg["library_version"], "batch_seed": cfg["batch_seed"], "git_commit": cfg["git"]["commit"],
        "config": {"pso": cfg["pso"], "fitness_weights": cfg["fitness_weights"],
                   "reconstruction": {"schema": SCHEMA, "partial": True, "source_sha256": art["checked_sha256"], "fields": FIELDS,
                                      "not_reconstructed_tables": list(NOT_RECONSTRUCTED_TABLES), "limitations": list(LIMITATIONS)}},
        "config_hash": params.config_hash(), "summary": run["summary"], "started_at": loaded_at, "finished_at": None,
    }
    cycles = []
    for c in run["cases"]:
        pid = c["profile_id"]
        cycles.append({
            "id": str(uuid.uuid5(_NAMESPACE, f"{LABEL}|{pid}|cycle")), "correlation_id": str(uuid.uuid5(_NAMESPACE, f"{LABEL}|{pid}|correlation")),
            "run_label": LABEL, "profile_id": pid, "concept_id": art["profiles"][pid], "replicate": 0, "status": c["status"],
            "stop_reason": c["stop_reason"], "k_stop": c["k_stop"], "t_conv_ms": c["t_conv_ms"], "total_ms": c["total_ms"],
            "seed": str(derive_seed(cfg["batch_seed"], pid, 0)), "config_hash": run_row["config_hash"],
            "library_version": cfg["library_version"], "W": None, "g_best_x": None, "g_best_S": c["g_best_S"], "g_best_F": c["g_best_F"],
            "g_best_breakdown": None, "predicted_dominant": c["predicted"], "metrics": None, "pso_diagnostics": None, "error": c["error"],
            "created_at": loaded_at})
    return _absent_as_sql_null(run_row, cycles)


def _absent_as_sql_null(run_row: dict, cycles: list[dict]) -> tuple[dict, list[dict]]:
    """Un valor ausente es SQL NULL. SQLAlchemy persiste `None` en una columna JSON como el JSON `null` (que NO es NULL): se omite la clave."""
    run_row = {k: v for k, v in run_row.items() if v is not None}
    cycles = [{k: v for k, v in c.items() if v is not None} for c in cycles]
    if len({tuple(sorted(c)) for c in cycles}) != 1:
        raise FixtureError("los ciclos no tienen las mismas columnas ausentes: la inserción por lotes exige filas uniformes")
    return run_row, cycles


# ── destino y transacción ───────────────────────────────────────────────────────────────────────────────────────────
def check_target(url: str) -> str:
    """El destino aceptado es SOLO la base aislada. Además de `isolated_env.check_database_url`, se rechaza cualquier query string."""
    target = iso.check_database_url(url)                 # SystemExit si no es 127.0.0.1:55432/swarm_test (usuario swarm_test)
    if urlsplit(url).query:
        raise FixtureError(f"la URL no puede llevar parámetros (p. ej. host=/socket redirigiría la conexión): {iso.mask(url)}")
    return target


def _guard(engine: Engine) -> None:
    """Append-only en tiempo de ejecución: solo SELECT y INSERT en `WRITABLE_TABLES`."""
    @event.listens_for(engine, "before_cursor_execute")
    def _only_select_and_insert(conn, cursor, statement, parameters, context, executemany):
        head = statement.lstrip().split(None, 1)[0].upper()
        if head == "SELECT":
            return
        m = re.match(r"\s*INSERT\s+INTO\s+\"?(\w+)\"?", statement, re.I)
        if head == "INSERT" and m and m.group(1) in WRITABLE_TABLES:
            return
        raise FixtureError(f"sentencia no permitida (solo SELECT e INSERT en {WRITABLE_TABLES}): {statement[:60]!r}")


def _tables():
    from app.models.swarm_adaptation import AgentMessage, MultimodalPackage, SwarmCycle, SwarmIteration, SwarmRun
    return SwarmRun.__table__, SwarmCycle.__table__, {"swarm_iterations": SwarmIteration.__table__, "agent_messages": AgentMessage.__table__,
                                                      "multimodal_packages": MultimodalPackage.__table__}


def _precheck(conn: Connection, cycles: list[dict]) -> None:
    runs, cyc, _ = _tables()
    if conn.dialect.name == "postgresql":
        db, user = conn.execute(text("SELECT current_database(), current_user")).one()
        if (db, user) != (iso.DB_NAME, iso.DB_USER):
            raise FixtureError(f"el servidor conectado es {db}/{user}, no {iso.DB_NAME}/{iso.DB_USER}")
    if conn.scalar(select(func.count()).select_from(runs).where(runs.c.run_label == LABEL)):
        raise FixtureError(f"la etiqueta {LABEL} ya existe en swarm_runs: no se sobrescribe ni se completa")
    if conn.scalar(select(func.count()).select_from(cyc).where(cyc.c.run_label == LABEL)):
        raise FixtureError(f"ya hay swarm_cycles con run_label={LABEL} (huérfanos): no se carga")
    taken = conn.scalars(select(cyc.c.id).where(cyc.c.id.in_([c["id"] for c in cycles]))).all()
    if taken:
        raise FixtureError(f"colisión de ids de ciclo ya existentes ({len(taken)}, p. ej. {taken[0]}): no se carga")


def _verify(conn: Connection, art: dict, cycles: list[dict]) -> dict:
    """Dentro de la transacción y antes de decidir commit/rollback: lo insertado coincide con los artefactos y el F1 se recalcula igual."""
    runs, cyc, empty = _tables()
    if conn.scalar(select(func.count()).select_from(runs).where(runs.c.run_label == LABEL)) != 1:
        raise FixtureError("swarm_runs no contiene exactamente 1 fila de la corrida tras insertar")
    rows = {r.profile_id: r for r in conn.execute(select(cyc).where(cyc.c.run_label == LABEL))}
    if len(rows) != 100:
        raise FixtureError(f"swarm_cycles contiene {len(rows)} filas de la corrida, se esperaban 100")
    absent = [cyc.c.W, cyc.c.g_best_x, cyc.c.g_best_breakdown, cyc.c.metrics, cyc.c.pso_diagnostics, cyc.c.error]
    not_null = conn.scalar(select(func.count()).select_from(cyc).where(cyc.c.run_label == LABEL, or_(*[c.is_not(None) for c in absent])))
    if not_null or conn.scalar(select(runs.c.finished_at).where(runs.c.run_label == LABEL)) is not None:
        raise FixtureError(f"{not_null} ciclos tienen valores donde debe haber SQL NULL (¿JSON null?), o finished_at no es NULL")
    counts = {}
    for name, table in empty.items():
        counts[name] = conn.scalar(select(func.count()).select_from(table).where(table.c.cycle_id.in_([c["id"] for c in cycles])))
        if counts[name]:
            raise FixtureError(f"{name} tiene {counts[name]} filas para la corrida: esas tablas no se reconstruyen")
    pairs = []
    for c in art["run"]["cases"]:
        r = rows[c["profile_id"]]
        if (r.stop_reason, r.k_stop, r.status, r.predicted_dominant, r.g_best_S) != (c["stop_reason"], c["k_stop"], c["status"], c["predicted"], c["g_best_S"]):
            raise FixtureError(f"el ciclo {c['profile_id']} insertado difiere del caso congelado")
        pairs.append((c["expected"], r.predicted_dominant))
    f1 = f1_report(pairs).f1_adapt
    if abs(f1 - art["run"]["summary"]["f1"]["f1_adapt"]) > 1e-9:
        raise FixtureError(f"el F1 recalculado desde la base ({f1}) difiere del congelado")
    return {"swarm_runs": 1, "swarm_cycles": len(rows), **counts, "f1_adapt_recomputed": f1}


def load(engine: Engine, art: dict, *, commit: bool, loaded_at: datetime | None = None) -> dict:
    """Una sola transacción. `commit=False` (ensayo): inserta, verifica y hace ROLLBACK. Cualquier error: rollback completo y se relanza."""
    loaded_at = loaded_at or datetime.now(timezone.utc)
    run_row, cycles = build_rows(art, loaded_at)
    runs, cyc, _ = _tables()
    conn = engine.connect()
    try:
        _precheck(conn, cycles)
        conn.execute(insert(runs), [run_row])
        conn.execute(insert(cyc), cycles)
        report = _verify(conn, art, cycles)
        if commit:
            conn.commit()
        else:
            conn.rollback()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()
    with engine.connect() as check:         # el estado final se lee desde una conexión nueva
        present = check.scalar(select(func.count()).select_from(runs).where(runs.c.run_label == LABEL))
    if present != (1 if commit else 0):
        raise FixtureError(f"estado final inesperado: {present} filas de swarm_runs tras {'commit' if commit else 'rollback'}")
    return {"schema": SCHEMA, "run_label": LABEL, "mode": "commit" if commit else "rehearse", "outcome": "committed" if commit else "rolled_back",
            "loaded_at": loaded_at.isoformat(), "inserted_in_transaction": report, "left_in_database": {"swarm_runs": present, "swarm_cycles": 100 if commit else 0},
            "source_sha256": art["checked_sha256"], "fields": FIELDS, "not_reconstructed_tables": list(NOT_RECONSTRUCTED_TABLES),
            "limitations": list(LIMITATIONS)}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--rehearse", action="store_true", help="ensayo: inserta, verifica y hace rollback")
    mode.add_argument("--commit", action="store_true", help=f"carga real; exige --confirm {CONFIRMATION}")
    ap.add_argument("--confirm", help="confirmación explícita para --commit")
    ap.add_argument("--out-dir", help="directorio (fuera de resultados congelados) donde escribir el resumen de la carga")
    args = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if args.commit and args.confirm != CONFIRMATION:
        raise SystemExit(f"--commit exige --confirm {CONFIRMATION}")
    if args.rehearse and args.confirm:
        raise SystemExit("--confirm solo se acepta con --commit")
    try:
        target = iso.require_isolated_database()                       # DATABASE_URL explícita y efectiva; 127.0.0.1:55432/swarm_test
        url = os.environ["DATABASE_URL"]
        check_target(url)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = iso.require_out_dir(args.out_dir) / f"{LABEL}_reconstruction_{'commit' if args.commit else 'rehearse'}_{stamp}.json"
        iso.check_output_targets([out])
        out.parent.mkdir(parents=True, exist_ok=True)
        art = load_artifacts()
        engine = create_engine(url)
        _guard(engine)
        try:
            summary = load(engine, art, commit=args.commit)
        finally:
            engine.dispose()
        summary["target"] = target
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    except FixtureError as e:
        raise SystemExit(f"ERROR: {e}") from e
    print(f"{summary['outcome']}: {summary['inserted_in_transaction']}\nresumen: {out}")


if __name__ == "__main__":
    main()
