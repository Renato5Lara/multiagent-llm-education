"""Comprobación contra PostgreSQL de la carga RECONSTRUIDA (parcial) de corrida-poc-1. Opt-in explícito.

ADVERTENCIA: esto NO es una reproducción de la base original. Los artefactos congelados solo permiten reconstruir `swarm_runs` y
`swarm_cycles`; `swarm_iterations`, `agent_messages` y `multimodal_packages` no existen en ningún artefacto de corrida-poc-1 y NO se
reconstruyen. Estas pruebas verifican que la carga es coherente con los JSON congelados y que, además, declara esa limitación
(las tablas no reconstruibles siguen vacías para esta corrida). Por eso no se puede ejecutar `pso_audit` sobre ella.

Activación (`SWARM_POC1_RECONSTRUCTED_LOADED`), sin conexión a la base salvo en el modo 1:
- sin definir o `0` → se omiten sin tocar la base (una base vacía nunca las ejecuta por accidente);
- `1` → la carga está declarada OBLIGATORIA: si falta o difiere, las pruebas FALLAN (no se saltan).
La base a la que apunta `DATABASE_URL` debe ser la aislada donde se cargó la reconstrucción con
`adaptation_swarm/tools/load_corrida_poc1_fixture.py` (ver REPRODUCIBILITY.md §5.1)."""

import json
import os
from pathlib import Path

import pytest
from sqlalchemy import func, select

from adaptation_swarm.gold.f1 import f1_report

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("SWARM_POC1_RECONSTRUCTED_LOADED") != "1",
        reason="carga reconstruida de corrida-poc-1 no declarada (SWARM_POC1_RECONSTRUCTED_LOADED=1 la exige; no se toca la base)",
    ),
]

LABEL = "corrida-poc-1"
RESULTS = Path(__file__).resolve().parents[2] / "experiments" / "results"


@pytest.fixture(scope="module")
def session():
    from app.db.session import SessionLocal
    with SessionLocal() as s:
        yield s


@pytest.fixture(scope="module")
def frozen() -> dict:
    return json.loads((RESULTS / f"adaptation_swarm_{LABEL}.json").read_text(encoding="utf-8"))


def _models():
    from app.models.swarm_adaptation import AgentMessage, MultimodalPackage, SwarmCycle, SwarmIteration, SwarmRun
    return SwarmRun, SwarmCycle, SwarmIteration, AgentMessage, MultimodalPackage


def test_the_reconstructed_run_matches_the_frozen_configuration(session, frozen):
    SwarmRun, *_ = _models()
    run = session.get(SwarmRun, LABEL)
    assert run is not None, "corrida-poc-1 no está cargada en la base apuntada por DATABASE_URL (carga declarada obligatoria)"
    assert run.library_version == frozen["config"]["library_version"] == "lib-v5-9ae9ffdd" and run.batch_seed == 20260923
    assert run.config["fitness_weights"] == {"alpha": 0.4, "beta": 0.3, "gamma": 0.15, "delta": 0.15}
    assert run.config["pso"]["n_particles"] == 20 and run.config["pso"]["epsilon"] == 0.001 and run.config["pso"]["k_max"] == 15


def test_the_run_declares_itself_a_partial_reconstruction_not_the_original_database(session):
    from adaptation_swarm.tools.load_corrida_poc1_fixture import FIELDS, LIMITATIONS, NOT_RECONSTRUCTED_TABLES, SCHEMA
    SwarmRun, *_ = _models()
    run = session.get(SwarmRun, LABEL)
    assert run is not None, "corrida-poc-1 no está cargada en la base apuntada por DATABASE_URL (carga declarada obligatoria)"
    rec = run.config.get("reconstruction")
    assert rec is not None, "la fila no lleva la marca config.reconstruction: no fue cargada por el cargador de la reconstrucción parcial"
    assert rec["schema"] == SCHEMA and rec["partial"] is True and rec["fields"] == FIELDS
    assert rec["not_reconstructed_tables"] == list(NOT_RECONSTRUCTED_TABLES) and rec["limitations"] == list(LIMITATIONS)
    assert run.finished_at is None


def test_the_reconstructed_cycles_match_the_frozen_cases_and_recompute_the_same_f1(session, frozen):
    _, SwarmCycle, *_ = _models()
    rows = {r.profile_id: r for r in session.scalars(select(SwarmCycle).where(SwarmCycle.run_label == LABEL))}
    cases = frozen["cases"]
    assert len(rows) == len(cases) == 100 and set(rows) == {c["profile_id"] for c in cases}
    for c in cases:
        r = rows[c["profile_id"]]
        assert (r.stop_reason, r.k_stop, r.predicted_dominant, r.status) == (c["stop_reason"], c["k_stop"], c["predicted"], c["status"])
    assert {r.stop_reason for r in rows.values()} == {"epsilon"} and max(r.k_stop for r in rows.values()) == 4
    pairs = [(c["expected"], rows[c["profile_id"]].predicted_dominant) for c in cases]
    assert f1_report(pairs).f1_adapt == pytest.approx(frozen["summary"]["f1"]["f1_adapt"], abs=1e-9)


def test_the_load_is_partial_iterations_messages_and_packages_are_not_reconstructed(session):
    """Fija la limitación: si alguien las llenara con datos inventados, esta prueba fallaría y obligaría a revisar la afirmación."""
    _, SwarmCycle, SwarmIteration, AgentMessage, MultimodalPackage = _models()
    cycle_ids = select(SwarmCycle.id).where(SwarmCycle.run_label == LABEL)
    for model in (SwarmIteration, AgentMessage, MultimodalPackage):
        n = session.scalar(select(func.count()).select_from(model).where(model.cycle_id.in_(cycle_ids)))
        assert n == 0, f"{model.__tablename__} tiene {n} filas para {LABEL}: no existen artefactos originales; la carga es parcial"


def test_unrecoverable_fields_are_sql_null_and_not_json_null(session):
    """`IS NULL` a nivel SQL: SQLAlchemy lee `None` tanto de un NULL como de un JSON `null`, pero solo el primero significa «no recuperable»."""
    _, SwarmCycle, *_ = _models()
    cols = [SwarmCycle.W, SwarmCycle.g_best_x, SwarmCycle.g_best_breakdown, SwarmCycle.metrics, SwarmCycle.pso_diagnostics, SwarmCycle.error]
    for col in cols:
        n = session.scalar(select(func.count()).select_from(SwarmCycle).where(SwarmCycle.run_label == LABEL, col.is_(None)))
        assert n == 100, f"{col.key}: {n}/100 son SQL NULL (el resto es JSON null u otro valor)"
