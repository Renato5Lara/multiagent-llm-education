"""Cargador de la reconstrucción PARCIAL de corrida-poc-1 (`tools/load_corrida_poc1_fixture.py`). Puras: SQLite en memoria; nunca se conectan
PostgreSQL, Redis ni la red, y no se ejecuta la carga real. Comprueban destino rechazado, hashes, append-only, transacción única con rollback,
reintento sin cambios, colisiones de ids y que las tablas no reconstruibles no se tocan. (Que el SQL funciona en PostgreSQL lo comprueba el ensayo
`--rehearse` contra la base aislada, que se ejecuta aparte.)"""

import ast
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool

from adaptation_swarm.tools import load_corrida_poc1_fixture as fx

BACK = Path(__file__).resolve().parents[2]
ISO_DB = "postgresql+psycopg://swarm_test:swarm_test_pw@127.0.0.1:55432/swarm_test"
LOADER = BACK / "adaptation_swarm" / "tools" / "load_corrida_poc1_fixture.py"


@pytest.fixture(scope="module")
def art() -> dict:
    return fx.load_artifacts()


@pytest.fixture
def engine():
    from app.models.swarm_adaptation import AgentMessage, MultimodalPackage, SwarmCycle, SwarmIteration, SwarmRun
    e = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    for m in (SwarmRun, SwarmCycle, SwarmIteration, AgentMessage, MultimodalPackage):
        m.__table__.create(e)
    fx._guard(e)                     # la misma guardia que usa la carga real; se instala después del DDL de la fixture
    yield e
    e.dispose()


def _snapshot(engine) -> dict:
    tables = fx._tables()
    with engine.connect() as c:
        return {t.name: sorted(map(tuple, c.execute(select(t)).all()), key=repr) for t in (tables[0], tables[1], *tables[2].values())}


def _counts(engine) -> dict:
    return {name: len(rows) for name, rows in _snapshot(engine).items()}


# ── 6. destino rechazado ────────────────────────────────────────────────────────────────────────────────────────────
def test_only_the_isolated_database_is_accepted_as_target():
    assert fx.check_target(ISO_DB) == "PostgreSQL 127.0.0.1:55432/swarm_test (usuario swarm_test)"
    rejected = {
        "desarrollo/producción (5432)": ISO_DB.replace("55432", "5432"),
        "host remoto": ISO_DB.replace("127.0.0.1", "db.ejemplo.com"),
        "otra base": ISO_DB.replace("/swarm_test", "/upao_mas_edu"),
        "otro usuario": ISO_DB.replace("swarm_test:swarm_test_pw", "upao_user:upao_pass"),
        "sin host (socket unix: pgdata)": "postgresql+psycopg://swarm_test:pw@/swarm_test",
        "no PostgreSQL": "sqlite:///swarm_test.db",
    }
    for why, url in rejected.items():
        with pytest.raises(SystemExit):
            fx.check_target(url)


def test_a_libpq_query_string_cannot_redirect_the_connection_to_pgdata_or_a_remote_host():
    for q in ("?host=/var/lib/postgresql/data", "?host=db.ejemplo.com", "?hostaddr=10.0.0.5", "?options=-csearch_path%3Dpublic"):
        with pytest.raises(fx.FixtureError, match="parámetros"):
            fx.check_target(ISO_DB + q)


def test_main_rejects_missing_or_wrong_target_and_missing_confirmation_before_creating_any_engine(monkeypatch, tmp_path):
    monkeypatch.setattr(fx, "create_engine", lambda *a, **k: (_ for _ in ()).throw(AssertionError("se intentó crear un engine")))
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(SystemExit, match="DATABASE_URL explícita"):
        fx.main(["--rehearse", "--out-dir", str(tmp_path)])
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu")
    with pytest.raises(SystemExit, match="RECHAZADA"):
        fx.main(["--commit", "--confirm", fx.CONFIRMATION, "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit, match="--confirm"):
        fx.main(["--commit", "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit, match="--confirm"):
        fx.main(["--commit", "--confirm", "si", "--out-dir", str(tmp_path)])
    with pytest.raises(SystemExit, match="--confirm solo"):
        fx.main(["--rehearse", "--confirm", fx.CONFIRMATION, "--out-dir", str(tmp_path)])
    assert list(tmp_path.iterdir()) == []                      # nada se escribió


def test_the_loader_never_touches_volumes_or_processes():
    """El cargador solo habla SQL por TCP con la base aislada: sin subprocess/os.system, podman/docker ni rutas de volúmenes (pgdata)."""
    tree = ast.parse(LOADER.read_text(encoding="utf-8"))
    imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)} | \
               {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & {"subprocess", "shutil", "socket", "redis", "openai", "httpx", "requests"}
    code = "\n".join(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) < 200)
    assert not any(w in code for w in ("podman", "docker", "/var/lib", "os.system"))


# ── hashes: antes de tocar la base ──────────────────────────────────────────────────────────────────────────────────
def test_a_tampered_artifact_is_rejected_before_any_database_is_involved(tmp_path):
    for name in ("adaptation_swarm_frozen_runs.md", "adaptation_swarm_corrida-poc-1.json", "adaptation_swarm_corrida-poc-1_cases.csv",
                 "adaptation_swarm_corrida-poc-1_f1_audit.json", "adaptation_swarm_corrida-poc-1_pso_audit.json",
                 "adaptation_swarm_corrida-poc-2.json", "adaptation_swarm_corrida-poc-2_cases.csv", "adaptation_swarm_corrida-poc-2_f1_audit.json"):
        if (fx.RESULTS / name).exists():
            shutil.copy(fx.RESULTS / name, tmp_path / name)
    assert fx.load_artifacts(tmp_path)["run"]["config"]["run_label"] == fx.LABEL            # copia íntegra: pasa
    j = tmp_path / "adaptation_swarm_corrida-poc-1.json"
    j.write_text(j.read_text(encoding="utf-8").replace('"predicted": "diagram"', '"predicted": "code"', 1), encoding="utf-8")
    with pytest.raises(fx.FixtureError, match="hash congelado"):
        fx.load_artifacts(tmp_path)


# ── 4. rollback ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_rehearsal_inserts_and_verifies_but_leaves_the_database_untouched(engine, art):
    report = fx.load(engine, art, commit=False)
    assert report["outcome"] == "rolled_back" and report["inserted_in_transaction"]["swarm_cycles"] == 100
    assert report["inserted_in_transaction"]["f1_adapt_recomputed"] == pytest.approx(0.8031415252818244)
    assert set(_counts(engine).values()) == {0}


def test_a_failure_halfway_rolls_back_everything_including_the_run_and_earlier_cycles(engine, art, monkeypatch):
    real = fx.build_rows

    def broken(a, when):
        run, cycles = real(a, when)
        cycles[60]["total_ms"] = None                          # NOT NULL: falla a mitad de la inserción, con 60 ciclos ya "aceptados" en el lote
        return run, cycles
    monkeypatch.setattr(fx, "build_rows", broken)
    with pytest.raises(IntegrityError):
        fx.load(engine, art, commit=True)
    assert set(_counts(engine).values()) == {0}


def test_a_failed_verification_after_inserting_rolls_back_and_commits_nothing(engine, art, monkeypatch):
    monkeypatch.setattr(fx, "_verify", lambda *a, **k: (_ for _ in ()).throw(fx.FixtureError("verificación fallida")))
    with pytest.raises(fx.FixtureError, match="verificación"):
        fx.load(engine, art, commit=True)
    assert set(_counts(engine).values()) == {0}


# ── 3. carga real y qué contiene ────────────────────────────────────────────────────────────────────────────────────
def test_commit_inserts_one_run_and_one_hundred_cycles_and_nothing_else(engine, art):
    report = fx.load(engine, art, commit=True)
    assert report["outcome"] == "committed" and report["left_in_database"] == {"swarm_runs": 1, "swarm_cycles": 100}
    assert _counts(engine) == {"swarm_runs": 1, "swarm_cycles": 100, "swarm_iterations": 0, "agent_messages": 0, "multimodal_packages": 0}
    runs, cyc, _ = fx._tables()
    with engine.connect() as c:
        run = c.execute(select(runs)).one()
        cycles = c.execute(select(cyc)).all()
    assert run.run_label == "corrida-poc-1" and run.library_version == "lib-v5-9ae9ffdd" and run.batch_seed == 20260923
    assert run.config["fitness_weights"] == {"alpha": 0.4, "beta": 0.3, "gamma": 0.15, "delta": 0.15} and run.config["pso"]["k_max"] == 15
    assert run.finished_at is None and run.summary == art["run"]["summary"] and run.config_hash == cycles[0].config_hash
    rec = run.config["reconstruction"]
    assert rec["schema"] == fx.SCHEMA and rec["partial"] is True and rec["not_reconstructed_tables"] == list(fx.NOT_RECONSTRUCTED_TABLES)
    assert rec["fields"] == fx.FIELDS and rec["source_sha256"] == art["checked_sha256"] and rec["limitations"]
    assert {c.replicate for c in cycles} == {0} and {c.stop_reason for c in cycles} == {"epsilon"} and len({c.id for c in cycles}) == 100
    from adaptation_swarm.schemas.ids import derive_seed
    assert all(c.seed == str(derive_seed(20260923, c.profile_id, 0)) for c in cycles)


def test_unrecoverable_fields_are_sql_null_not_json_null(engine, art):
    """SQLAlchemy guarda `None` en una columna JSON como el JSON `null` (que no es NULL) y al leer devuelve None en ambos casos: solo `IS NULL` a
    nivel SQL distingue. Regresión hallada al validar contra PostgreSQL real, donde las 100 filas tenían JSON null."""
    fx.load(engine, art, commit=True)
    _, cyc, _ = fx._tables()
    cols = [cyc.c.W, cyc.c.g_best_x, cyc.c.g_best_breakdown, cyc.c.metrics, cyc.c.pso_diagnostics, cyc.c.error]
    with engine.connect() as c:
        assert [c.scalar(select(func.count()).select_from(cyc).where(col.is_(None))) for col in cols] == [100] * 6


def test_explicit_nones_in_json_columns_are_rejected_by_the_load_itself_and_rolled_back(engine, art, monkeypatch):
    real = fx.build_rows
    monkeypatch.setattr(fx, "build_rows", lambda a, when: (lambda r, cs: (r, [dict(x, W=None) for x in cs]))(*real(a, when)))
    with pytest.raises(fx.FixtureError, match="SQL NULL"):
        fx.load(engine, art, commit=True)
    assert set(_counts(engine).values()) == {0}


def test_the_reconstruction_is_deterministic_apart_from_the_load_timestamps(art):
    from datetime import datetime, timezone
    a = fx.build_rows(art, datetime(2026, 1, 1, tzinfo=timezone.utc))
    b = fx.build_rows(art, datetime(2030, 6, 6, tzinfo=timezone.utc))
    strip = lambda rows: [{k: v for k, v in r.items() if k not in ("created_at", "started_at")} for r in rows]
    assert strip([a[0]]) == strip([b[0]]) and strip(a[1]) == strip(b[1])


# ── 5. reintento ────────────────────────────────────────────────────────────────────────────────────────────────────
def test_retrying_after_a_commit_is_rejected_and_changes_nothing(engine, art):
    fx.load(engine, art, commit=True)
    before = _snapshot(engine)
    for commit in (True, False):
        with pytest.raises(fx.FixtureError, match="ya existe"):
            fx.load(engine, art, commit=commit)
        assert _snapshot(engine) == before                     # ni una fila, ni un valor, cambiaron


def test_a_rehearsal_can_be_repeated_and_a_commit_still_works_afterwards(engine, art):
    fx.load(engine, art, commit=False)
    fx.load(engine, art, commit=False)
    assert set(_counts(engine).values()) == {0}
    assert fx.load(engine, art, commit=True)["outcome"] == "committed" and _counts(engine)["swarm_cycles"] == 100


# ── colisiones ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_an_existing_cycle_id_is_rejected_without_writing(engine, art):
    from datetime import datetime, timezone
    _, cycles = fx.build_rows(art, datetime.now(timezone.utc))
    _, cyc, _ = fx._tables()
    with engine.begin() as c:
        c.execute(insert(cyc), [dict(cycles[5], run_label=None)])            # mismo id determinista, de otra corrida/sin etiqueta
    before = _snapshot(engine)
    with pytest.raises(fx.FixtureError, match="colisión de ids"):
        fx.load(engine, art, commit=True)
    assert _snapshot(engine) == before


def test_orphan_cycles_carrying_the_label_are_rejected_without_writing(engine, art):
    from datetime import datetime, timezone
    _, cycles = fx.build_rows(art, datetime.now(timezone.utc))
    _, cyc, _ = fx._tables()
    with engine.begin() as c:
        c.execute(insert(cyc), [dict(cycles[7], id="00000000-0000-0000-0000-00000000dead")])     # ciclo con la etiqueta pero sin fila en swarm_runs
    before = _snapshot(engine)
    with pytest.raises(fx.FixtureError, match="huérfanos"):
        fx.load(engine, art, commit=True)
    assert _snapshot(engine) == before


# ── append-only ─────────────────────────────────────────────────────────────────────────────────────────────────────
def test_the_guard_refuses_anything_but_select_and_insert_into_the_two_tables(engine):
    for sql in ("UPDATE swarm_runs SET spec_version='x'", "DELETE FROM swarm_cycles", "DROP TABLE swarm_runs", "ALTER TABLE swarm_runs ADD COLUMN x int",
                "INSERT INTO swarm_iterations (id) VALUES ('x')", "INSERT INTO agent_messages (message_id) VALUES ('x')",
                "INSERT INTO multimodal_packages (package_id) VALUES ('x')", "TRUNCATE swarm_cycles", "PRAGMA writable_schema=1"):
        with engine.connect() as c, pytest.raises(fx.FixtureError, match="no permitida"):
            c.execute(text(sql))
    assert set(_counts(engine).values()) == {0}


def test_a_full_load_only_ever_issues_select_and_insert_into_swarm_runs_and_swarm_cycles(engine, art):
    import re
    from sqlalchemy import event
    seen = []
    event.listen(engine, "before_cursor_execute", lambda conn, cur, stmt, *a: seen.append(stmt))
    fx.load(engine, art, commit=True)
    kinds = {("SELECT",) if st.lstrip().upper().startswith("SELECT") else ("INSERT", re.match(r"\s*INSERT\s+INTO\s+\"?(\w+)", st, re.I).group(1))
             for st in seen}
    assert kinds == {("SELECT",), ("INSERT", "swarm_runs"), ("INSERT", "swarm_cycles")}, kinds
