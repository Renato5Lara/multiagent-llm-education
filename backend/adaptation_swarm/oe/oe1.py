"""OE1 — relación entre el cumplimiento de los requerimientos funcionales y no funcionales (RF01–RF06, RNF01–RNF05) y el desempeño de la adaptación, con indicadores CUANTIFICABLES de
funcionalidad, confiabilidad, eficiencia y calidad de adaptación.

Qué hace este módulo (no ejecuta experimentos propios salvo dos sondas pequeñas):
  1. `REQUIREMENTS`: registro legible por máquina de cada requisito → dimensión (funcionalidad | confiabilidad | eficiencia | calidad) → indicador → umbral → fuente de la evidencia.
  2. `requirement_table`: evalúa cada requisito contra datos MEDIDOS (observaciones y lotes de `oe/runner.py`, sonda de persistencia, sonda de determinismo, resultado oficial de F1, SUS). Estados:
        MET · NOT_MET · NOT_MEASURED (con la razón). Nada se infiere: lo que ninguna fuente mide queda NOT_MEASURED, nunca MET.
  3. `relationship`: cumplimiento vs. desempeño. Por CONDICIÓN experimental: puntaje de cumplimiento (requisitos cumplidos / aplicables) frente a la brecha de calidad, el tiempo de convergencia, la
     latencia P95 y el throughput (Spearman); por PETICIÓN: cumplimiento funcional (RF01–RF05) frente a la brecha (Mann-Whitney/Welch). Si el cumplimiento no varía, la relación es INDEFINIDA y se dice
     (todas las condiciones cumplen igual: no hay variación que relacionar), no se fabrica una correlación.
  4. Sondas: `determinism_probe` (misma semilla ⇒ mismo resultado; confiabilidad/reproducibilidad) y `persistence_probe` (RF06: el ciclo, sus iteraciones, mensajes y paquete quedan en PostgreSQL).

Definición operativa por confirmar con el asesor: cómo se agregan los requisitos en un «puntaje de cumplimiento» y qué indicadores representan cada dimensión (ver `PENDING`).
    python -m adaptation_swarm.oe.oe1 --runs DIR [DIR ...] --out-dir NUEVO [--probe-n 20] [--persistence-probe] [--f1-json F] [--sus-from-db]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from adaptation_swarm.analysis import comparison as cmp
from adaptation_swarm.metrics.performance import latency_report

MET, NOT_MET, NOT_MEASURED = "MET", "NOT_MET", "NOT_MEASURED"
RNF01_P95_MS, RNF01_MAX_USERS = 2000.0, 25
RNF02_KMAX, RNF02_CR = 15, 0.98
RNF03_F1 = 0.85
RNF04_RPS, RNF04_ERROR = 20.0, 0.01
RNF05_SUS, RNF05_MIN_N = 75.0, 10
RELIABILITY_COMPLETION = 0.99
COMPLIANCE_SCORE_STATE = "BLOCKED_DEFINITION"
COMPLIANCE_SCORE_NOTE = ("No existe una definición aprobada del «puntaje de cumplimiento» (ver `oe/definitions.py`: compliance_score_oe1 PENDING). `compliance_score` por condición es una razón EXPLORATORIA "
                         "(requisitos cumplidos / aplicables, con numerador, denominador e ids) y NO se usa para declarar ningún resultado oficial de OE1.")
PENDING = ["Agregación de los requisitos en un «puntaje de cumplimiento» por condición y mapa requisito→dimensión: definición operativa de este estudio, por confirmar con el asesor.",
           "Latencia en proceso (sin HTTP): sustituto exploratorio de RNF01; la medición oficial es HTTP (Locust/JMeter) en el hardware objetivo.",
           "RNF03 (F1_adapt) depende de la regla v3, cuyo pre-registro no está sellado (PENDING_ADVISOR); RNF05 depende del panel humano."]


@dataclass(frozen=True)
class Requirement:
    id: str
    kind: str                 # RF | RNF
    dimension: str            # funcionalidad | confiabilidad | eficiencia | calidad
    statement: str
    indicator: str
    threshold: str
    source: str               # de dónde sale el dato
    evidence_kind: str = "automated"   # automated (por petición) | probe (sonda dirigida) | benchmark (medición de carga) | external (resultado oficial / humano)


REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("RF01", "RF", "funcionalidad", "Perfil JSON estandarizado", "proporción de peticiones cuyo perfil es aceptado y validado", "= 100 %", "observaciones (error_code ≠ ProfileError)"),
    Requirement("RF02", "RF", "funcionalidad", "AG1 asigna el vector W", "proporción de ciclos con W normalizada (Σ = 1)", "= 100 %", "observaciones (w_valid)"),
    Requirement("RF03", "RF", "funcionalidad", "Despacho concurrente a AG2–AG4 con trazas", "proporción de ciclos con peticiones en vuelo solapadas (inflight_overlap)", "= 100 %", "observaciones (inflight_overlap)"),
    Requirement("RF04", "RF", "funcionalidad", "AG0 ejecuta PSO y 𝓕 con log de iteraciones", "proporción de ciclos con iteraciones registradas = k_stop + 1", "= 100 %", "observaciones (iterations_logged)"),
    Requirement("RF05", "RF", "funcionalidad", "Paquete con las 4 modalidades válidas", "proporción de peticiones con paquete válido y cadena de hashes íntegra", "= 100 %", "observaciones (package_valid)"),
    Requirement("RF06", "RF", "funcionalidad", "Métricas de cada ciclo en PostgreSQL", "proporción de ciclos persistidos completos (ciclo, iteraciones, mensajes, paquete)", "= 100 %", "sonda de persistencia", evidence_kind="probe"),
    Requirement("REL-C", "RNF", "confiabilidad", "Los ciclos terminan sin error", "tasa de ciclos completados", f"≥ {RELIABILITY_COMPLETION:.0%}", "observaciones (status)"),
    Requirement("REL-D", "RNF", "confiabilidad", "Reproducibilidad: misma semilla ⇒ mismo resultado", "proporción de pares idénticos (S, 𝓕, k_stop, motivo)", "= 100 %", "sonda de determinismo", evidence_kind="probe"),
    Requirement("RNF01", "RNF", "eficiencia", "Latencia L_resp < 2.0 s (P95, ≤ 25 usuarios)", "P95 de la latencia por petición (EN PROCESO, sin HTTP)", f"< {RNF01_P95_MS:.0f} ms", "observaciones (latency_ms)"),
    Requirement("RNF02", "RNF", "eficiencia", "Convergencia: T_conv ≤ 15 iteraciones y CR ≥ 98 %", "máx. k_stop y proporción de paradas por ε", f"k_stop ≤ {RNF02_KMAX} ∧ CR ≥ {RNF02_CR:.0%}", "observaciones (k_stop, stop_reason)"),
    Requirement("RNF04", "RNF", "eficiencia", "Throughput ≥ 20 req/s con error < 1 %", "mediana del throughput por lote y tasa de error", f"≥ {RNF04_RPS:.0f} req/s ∧ error < {RNF04_ERROR:.0%}", "lotes (throughput_rps)", evidence_kind="benchmark"),
    Requirement("RNF03", "RNF", "calidad", "F1_adapt ≥ 0.85", "F1_adapt oficial (regla v3, K = 10)", f"≥ {RNF03_F1}", "resultado oficial de F1", evidence_kind="external"),
    Requirement("RNF05", "RNF", "calidad", "Usabilidad SUS > 75 (n ≥ 10)", "media SUS y contraste contra 75", f"media > {RNF05_SUS:.0f} ∧ p < 0.05 ∧ n ≥ {RNF05_MIN_N}", "SUS (panel humano)", evidence_kind="external"),
)
DIMENSIONS = ("funcionalidad", "confiabilidad", "eficiencia", "calidad")


def _swarm(obs: Sequence[Mapping]) -> list[Mapping]:
    return [r for r in obs if r.get("f_system", "swarm") == "swarm"]


def _share(rows: Sequence[Mapping], pred) -> tuple[float | None, int]:
    vals = [pred(r) for r in rows]
    vals = [v for v in vals if v is not None]
    return (sum(1 for v in vals if v) / len(vals) if vals else None), len(vals)


def _status(value: float | None, ok: bool | None, **extra) -> dict:
    return {"value": value, "status": NOT_MEASURED if ok is None else (MET if ok else NOT_MET), **extra}


def requirement_table(obs: Sequence[Mapping], bat: Sequence[Mapping], *, persistence: Mapping | None = None, determinism: Mapping | None = None,
                      f1: Mapping | None = None, sus: Mapping | None = None) -> list[dict]:
    """Una fila por requisito. Las observaciones deben ser de la PROPUESTA (los sistemas convencionales no tienen RF02–RF04)."""
    rows = _swarm(obs)
    ok = [r for r in rows if r["status"] == "completed"]
    out: dict[str, dict] = {}

    def share_req(rid: str, pred, subset) -> None:
        v, n = _share(subset, pred)
        out[rid] = _status(v, None if v is None else v == 1.0, n=n, numerator=None if v is None else round(v * n), denominator=n)

    share_req("RF01", lambda r: r.get("error_code") != "ProfileError", rows)
    share_req("RF02", lambda r: r.get("w_valid"), ok)
    share_req("RF03", lambda r: r.get("inflight_overlap"), ok)
    share_req("RF04", lambda r: r.get("iterations_logged"), ok)
    share_req("RF05", lambda r: bool(r.get("package_valid")) if r["status"] == "completed" else False, rows)
    out["RF06"] = _status(None if not persistence else persistence["rate"], None if not persistence else persistence["rate"] == 1.0, n=0 if not persistence else persistence["n"],
                          reason=None if persistence else "no se ejecutó la sonda de persistencia (--persistence-probe)")
    comp = (len(ok) / len(rows)) if rows else None
    out["REL-C"] = _status(comp, None if comp is None else comp >= RELIABILITY_COMPLETION, n=len(rows))
    out["REL-D"] = _status(None if not determinism else determinism["rate"], None if not determinism else determinism["rate"] == 1.0, n=0 if not determinism else determinism["n"],
                           reason=None if determinism else "no se ejecutó la sonda de determinismo (--probe-n)")
    lat = [r["latency_ms"] for r in ok if r.get("f_concurrency", 1) <= RNF01_MAX_USERS and r.get("latency_ms") is not None]
    p95 = latency_report(lat)["p95_ms"] if lat else None
    out["RNF01"] = _status(p95, None if p95 is None else p95 < RNF01_P95_MS, n=len(lat), scope="en proceso, sin HTTP; ≤ 25 usuarios")
    ks = [r["k_stop"] for r in ok if r.get("k_stop") is not None]
    cr, _ = _share(ok, lambda r: r.get("stop_reason") == "epsilon")
    out["RNF02"] = _status(max(ks) if ks else None, None if not ks else (max(ks) <= RNF02_KMAX and cr >= RNF02_CR), n=len(ks), CR=cr)
    thr = sorted(b["throughput_rps"] for b in bat if b.get("throughput_rps") is not None and b["condition"] in {r["condition"] for r in rows})
    err = 1 - comp if comp is not None else None
    med = thr[len(thr) // 2] if thr else None
    out["RNF04"] = _status(med, None if not thr else (med >= RNF04_RPS and err < RNF04_ERROR), n=len(thr), error_rate=err,
                           note="mediana sobre todos los lotes de todas las condiciones de la propuesta (incluye cargas bajas); ver la relación por condición")
    out["RNF03"] = _status(None if not f1 else f1.get("f1_adapt"), None if not f1 else bool(f1["f1_adapt"] >= RNF03_F1), reason=None if f1 else "sin resultado oficial de F1 (K = 10 v3 no ejecutado)")
    sus_ok = None if not sus or sus.get("mean") is None else bool(sus["mean"] > RNF05_SUS and sus["test_p"] < 0.05 and sus["n"] >= RNF05_MIN_N)
    out["RNF05"] = _status(None if not sus else sus.get("mean"), sus_ok, n=0 if not sus else sus.get("n"), reason=None if sus_ok is not None else "sin SUS con n ≥ 10 (panel humano pendiente)")
    return [{"evidence_kind": r.evidence_kind, "id": r.id, "kind": r.kind, "dimension": r.dimension, "statement": r.statement, "indicator": r.indicator, "threshold": r.threshold, "source": r.source, **out[r.id]}
            for r in REQUIREMENTS]


def dimension_summary(table: Sequence[Mapping]) -> dict[str, dict]:
    out = {}
    for d in DIMENSIONS:
        rows = [r for r in table if r["dimension"] == d]
        out[d] = {"requirements": [r["id"] for r in rows], "met": sum(r["status"] == MET for r in rows), "not_met": sum(r["status"] == NOT_MET for r in rows),
                  "not_measured": sum(r["status"] == NOT_MEASURED for r in rows)}
    return out


def condition_compliance(obs: Sequence[Mapping], bat: Sequence[Mapping]) -> dict[str, dict]:
    """Por condición de la propuesta: requisitos medibles por condición, cumplidos y puntaje = cumplidos / aplicables; más los indicadores de desempeño."""
    by: dict[str, list[Mapping]] = {}
    for r in _swarm(obs):
        by.setdefault(r["condition"], []).append(r)
    out = {}
    for cond, rows in by.items():
        t = requirement_table(rows, [b for b in bat if b["condition"] == cond])
        applicable = [r for r in t if r["status"] != NOT_MEASURED and r["id"] in {"RF01", "RF02", "RF03", "RF04", "RF05", "REL-C", "RNF01", "RNF02", "RNF04"}]
        ok = [r for r in rows if r["status"] == "completed"]
        thr = sorted(b["throughput_rps"] for b in bat if b["condition"] == cond and b.get("throughput_rps") is not None)
        gaps = [r["gap_vs_optimum"] for r in ok if r.get("gap_vs_optimum") is not None]
        tc = [r["t_conv_ms"] for r in ok if r.get("t_conv_ms") is not None]
        lat = [r["latency_ms"] for r in ok if r.get("latency_ms") is not None]
        out[cond] = {"compliance_score": (sum(r["status"] == MET for r in applicable) / len(applicable)) if applicable else None, "n_applicable": len(applicable),
                     "n_met": sum(r["status"] == MET for r in applicable), "applicable_ids": [r["id"] for r in applicable],
                     "not_met": [r["id"] for r in applicable if r["status"] == NOT_MET], "gap_vs_optimum": sum(gaps) / len(gaps) if gaps else None,
                     "t_conv_ms_median": sorted(tc)[len(tc) // 2] if tc else None, "latency_p95_ms": latency_report(lat)["p95_ms"] if lat else None,
                     "throughput_median_rps": thr[len(thr) // 2] if thr else None}
    return out


def relationship(obs: Sequence[Mapping], bat: Sequence[Mapping]) -> dict:
    per = condition_compliance(obs, bat)
    scores = {c: v["compliance_score"] for c, v in per.items() if v["compliance_score"] is not None}
    res: dict = {"OE1_COMPLIANCE_SCORE": COMPLIANCE_SCORE_STATE, "compliance_score_note": COMPLIANCE_SCORE_NOTE,
                 "per_condition": per, "n_conditions": len(scores)}
    names = sorted(scores)
    rel: dict = {}
    for ind in ("gap_vs_optimum", "t_conv_ms_median", "latency_p95_ms", "throughput_median_rps"):
        pairs = [(scores[c], per[c][ind]) for c in names if per[c][ind] is not None]
        if len(pairs) < 3:
            rel[ind] = {"status": "not_testable_fewer_than_3_conditions", "n": len(pairs)}
        else:
            rel[ind] = cmp.spearman([p[0] for p in pairs], [p[1] for p in pairs])
            if rel[ind]["status"] != "ok":
                rel[ind]["note"] = "el cumplimiento no varía entre condiciones: no hay variación que relacionar"
    res["spearman_compliance_vs_performance"] = rel
    ok = [r for r in _swarm(obs) if r["status"] == "completed" and r.get("gap_vs_optimum") is not None]
    flags = [bool(r.get("w_valid") and r.get("iterations_logged") and r.get("inflight_overlap") and r.get("package_valid")) for r in ok]
    a = [r["gap_vs_optimum"] for r, f in zip(ok, flags) if f]
    b = [r["gap_vs_optimum"] for r, f in zip(ok, flags) if not f]
    res["request_level_functional_compliance_vs_gap"] = {"n_compliant": len(a), "n_non_compliant": len(b), **(cmp.independent_comparison(a, b) if len(b) >= 3 else {"status": "not_testable_fewer_than_3_non_compliant"})}
    return res


# ── sondas ──────────────────────────────────────────────────────────────────────────────────────────────
async def _purge(prefix: str) -> None:
    """Limpia las claves de Redis DESPUÉS de detener los agentes (si no, sus consumidores pierden el grupo y registran «bus caído»)."""
    from adaptation_swarm.bus.redis_bus import RedisBus
    bus = await RedisBus(prefix=prefix).connect()
    await bus.purge_prefix()
    await bus.close()


async def determinism_probe(store, profiles, n: int, batch_seed: int) -> dict:
    """Cada perfil se ejecuta DOS veces con la misma semilla en la pila real; deben coincidir S, 𝓕, k_stop y motivo de parada."""
    from adaptation_swarm.stack import SwarmStack
    same, mismatches = 0, []
    prefix = f"swarm-oe1-{uuid.uuid4().hex[:8]}:"
    try:
        async with SwarmStack(library_version=store.version, prefix=prefix) as st:
            for p in profiles[:n]:
                a = await st.orchestrator.run_cycle(p, batch_seed=batch_seed)
                b = await st.orchestrator.run_cycle(p, batch_seed=batch_seed)
                key = lambda r: (r.status, r.g_best_S, r.g_best_F, r.k_stop, r.stop_reason)
                if key(a) == key(b):
                    same += 1
                else:
                    mismatches.append(p.profile_id)
    finally:
        await _purge(prefix)
    return {"n": min(n, len(profiles)), "identical": same, "rate": same / min(n, len(profiles)), "mismatches": mismatches, "batch_seed": batch_seed}


async def persistence_probe(store, profiles, n: int, batch_seed: int) -> dict:
    """RF06: `n` ciclos reales con el repositorio PostgreSQL; por ciclo se comprueba que quedaron la fila del ciclo, k_stop + 1 iteraciones, todos los mensajes del bus y el paquete íntegro."""
    from sqlalchemy import func, select
    from adaptation_swarm.persistence.repository import PostgresCycleRepository
    from adaptation_swarm.stack import SwarmStack
    from app.db.session import SessionLocal
    from app.models.swarm_adaptation import AgentMessage, MultimodalPackage, SwarmCycle, SwarmIteration
    label = f"oe1-probe-{uuid.uuid4().hex[:8]}"
    repo = PostgresCycleRepository(run_label=label)
    repo.start_run(label, batch_seed=batch_seed, config={"probe": "rf06"}, config_hash="oe1-probe", dataset_version="v1", library_version=store.version)
    repo.save_profiles(profiles[:n], "v1")
    repo.sync_library(store)
    complete, failures = 0, []
    prefix = f"swarm-oe1-{uuid.uuid4().hex[:8]}:"
    try:
        async with SwarmStack(library_version=store.version, prefix=prefix, repository=repo) as st:
            for p in profiles[:n]:
                r = await st.orchestrator.run_cycle(p, batch_seed=batch_seed)
                with SessionLocal() as s:
                    cyc = s.get(SwarmCycle, r.cycle_id)
                    n_it = s.scalar(select(func.count()).select_from(SwarmIteration).where(SwarmIteration.cycle_id == r.cycle_id))
                    n_msg = s.scalar(select(func.count()).select_from(AgentMessage).where(AgentMessage.cycle_id == r.cycle_id))
                    pkg = s.scalars(select(MultimodalPackage).where(MultimodalPackage.cycle_id == r.cycle_id)).first()
                ok = bool(cyc is not None and r.status == "completed" and cyc.status == "completed" and n_it == r.k_stop + 1 and n_msg == r.metrics.n_messages
                          and pkg is not None and pkg.chain_valid)
                complete += ok
                if not ok:
                    failures.append({"profile_id": p.profile_id, "cycle_row": cyc is not None, "iterations": n_it, "expected_iterations": (r.k_stop or 0) + 1, "messages": n_msg,
                                     "expected_messages": r.metrics.n_messages, "package": pkg is not None})
    finally:
        await _purge(prefix)
        repo.delete_run(label)
    return {"n": min(n, len(profiles)), "complete": complete, "rate": complete / min(n, len(profiles)), "failures": failures}


def render_markdown(table: Sequence[Mapping], dims: Mapping, rel: Mapping) -> str:
    lines = ["# OE1 — cumplimiento de requisitos e indicadores", "", "| Requisito | Dimensión | Indicador | Umbral | Valor | Estado |", "|---|---|---|---|---|---|"]
    for r in table:
        v = "—" if r["value"] is None else (f"{r['value']:.4g}" if isinstance(r["value"], float) else str(r["value"]))
        lines.append(f"| {r['id']} | {r['dimension']} | {r['indicator']} | {r['threshold']} | {v} | {r['status']}{'' if not r.get('reason') else ' — ' + r['reason']} |")
    lines += ["", "| Dimensión | Cumplidos | No cumplidos | No medidos |", "|---|---|---|---|"]
    lines += [f"| {d} | {v['met']} | {v['not_met']} | {v['not_measured']} |" for d, v in dims.items()]
    lines += ["", "Relación cumplimiento–desempeño (Spearman por condición):", ""]
    lines += [f"- {k}: {json.dumps(v, default=str)}" for k, v in rel["spearman_compliance_vs_performance"].items()]
    return "\n".join(lines) + "\n"


def _load_runs(dirs: Sequence[Path]) -> tuple[list[dict], list[dict], list[str]]:
    obs, bat, labels = [], [], []
    for d in dirs:
        obs += [json.loads(l) for l in (d / "observations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        bat += json.loads((d / "batches.json").read_text(encoding="utf-8"))
        labels.append(json.loads((d / "provenance.json").read_text(encoding="utf-8"))["label"])
    return obs, bat, labels


def main(argv: list[str] | None = None) -> None:
    from adaptation_swarm.config import SETTINGS
    from adaptation_swarm.multimodal.library import LibraryStore
    from adaptation_swarm.oe.runner import DEFAULT_BATCH_SEED, DEFAULT_PROFILES, _sha_bytes
    from adaptation_swarm.profiles.generator import read_dataset
    from adaptation_swarm.tools import isolated_env as iso
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs", type=Path, nargs="+", required=True, help="directorios de corridas de oe/runner.py (oe3 y/o oe4)")
    ap.add_argument("--out-dir")
    ap.add_argument("--probe-n", type=int, default=0, help="perfiles para la sonda de determinismo (0 = no se ejecuta)")
    ap.add_argument("--persistence-probe", type=int, default=0, metavar="N", help="ciclos para la sonda de persistencia RF06 (requiere PostgreSQL aislado)")
    ap.add_argument("--f1-json", type=Path, help="resultado oficial de F1 (JSON con la clave f1_adapt); sin él RNF03 queda NOT_MEASURED")
    ap.add_argument("--batch-seed", type=int, default=DEFAULT_BATCH_SEED)
    a = ap.parse_args(argv)
    out_dir = iso.require_out_dir(a.out_dir)
    iso.check_new_output_targets([out_dir])
    obs, bat, labels = _load_runs(a.runs)
    determinism = persistence = None
    if a.probe_n or a.persistence_probe:
        iso.require_isolated_redis()
        store = LibraryStore.open(SETTINGS.library_root)
        profiles = read_dataset(DEFAULT_PROFILES)
        if a.persistence_probe:
            iso.require_isolated_database()
        if a.probe_n:
            determinism = asyncio.run(determinism_probe(store, profiles, a.probe_n, a.batch_seed))
        if a.persistence_probe:
            persistence = asyncio.run(persistence_probe(store, profiles, a.persistence_probe, a.batch_seed))
    f1 = json.loads(a.f1_json.read_text(encoding="utf-8")) if a.f1_json else None
    table = requirement_table(obs, bat, persistence=persistence, determinism=determinism, f1=f1)
    dims, rel = dimension_summary(table), relationship(obs, bat)
    from adaptation_swarm.oe import definitions as defs
    report = {"schema": "oe1-report-v2", "OE1_COMPLIANCE_SCORE": COMPLIANCE_SCORE_STATE, "requirements_version": defs.REQUIREMENTS_VERSION,
              "requirements_universe": [r.id for r in REQUIREMENTS], "evaluated_ids": [r["id"] for r in table if r["status"] != NOT_MEASURED],
              "evidence_by_requirement": {r["id"]: {"kind": r["evidence_kind"], "source": r["source"], "status": r["status"], "numerator": r.get("numerator"), "denominator": r.get("denominator")} for r in table},
              "runs": [str(p) for p in a.runs], "run_labels": labels, "table": table, "dimensions": dims, "relationship": rel,
              "determinism": determinism, "persistence": persistence, "pending_decisions": PENDING}
    out_dir.mkdir(parents=True, exist_ok=False)
    files = {"oe1_report.json": json.dumps(report, indent=2, sort_keys=True, default=str), "oe1_report.md": render_markdown(table, dims, rel)}
    for n, t in files.items():
        with (out_dir / n).open("x", encoding="utf-8") as fh:
            fh.write(t)
    with (out_dir / "manifest.json").open("x", encoding="utf-8") as fh:
        fh.write(json.dumps({"schema": "oe1-report-v2", "files": {n: _sha_bytes((out_dir / n).read_bytes()) for n in files}}, indent=2, sort_keys=True))
    print(files["oe1_report.md"])


if __name__ == "__main__":
    main()
