"""Salvaguardas de los ejecutores (`run_experiment`, `run_slice`), los auditores (`analysis/f1_audit`, `analysis/pso_audit`) y `scripts/repro_db_bootstrap.sh`.
Puras: sin PostgreSQL, Redis, OpenAI ni ejecución de corridas; los flujos con base de datos se comprueban con dobles y los destinos con URLs que nunca se conectan."""

import ast
import hashlib
import importlib
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from adaptation_swarm.tools import isolated_env as iso

BACK = Path(__file__).resolve().parents[2]
RESULTS = BACK / "experiments" / "results"
ISO_DB = "postgresql+psycopg://swarm_test:swarm_test_pw@127.0.0.1:55432/swarm_test"
ISO_REDIS = "redis://127.0.0.1:56379/0"
DEV_DB = "postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu"
MODULES = ("adaptation_swarm.tools.isolated_env", "adaptation_swarm.run_experiment", "adaptation_swarm.run_slice",
           "adaptation_swarm.analysis.f1_audit", "adaptation_swarm.analysis.pso_audit")


def _results_fingerprint() -> dict:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(RESULTS.iterdir()) if p.is_file()}


@pytest.fixture(autouse=True)
def frozen_results_untouched():
    before = _results_fingerprint()
    yield
    assert _results_fingerprint() == before                      # ninguna prueba toca los resultados congelados


# ── destinos: solo el entorno aislado ───────────────────────────────────────────────────────────────────────────────
def test_only_the_isolated_database_is_accepted_and_the_password_is_never_shown():
    assert iso.check_database_url(ISO_DB) == "PostgreSQL 127.0.0.1:55432/swarm_test (usuario swarm_test)"
    assert "localhost:55432" in iso.check_database_url(ISO_DB.replace("127.0.0.1", "localhost")).replace("PostgreSQL ", "")
    bad = {DEV_DB: "5432", ISO_DB.replace("55432", "5432"): "5432", ISO_DB.replace("127.0.0.1", "db.ejemplo.com"): "host no local",
           ISO_DB.replace("/swarm_test", "/upao_mas_edu"): "base", ISO_DB.replace("swarm_test:", "upao_user:"): "usuario",
           "mysql://swarm_test:x@127.0.0.1:55432/swarm_test": "PostgreSQL", "sqlite:///x.db": "PostgreSQL"}
    for url, why in bad.items():
        with pytest.raises(SystemExit) as exc:
            iso.check_database_url(url)
        msg = str(exc.value)
        assert "RECHAZADA" in msg and why in msg and "upao_pass" not in msg and "swarm_test_pw" not in msg, (url, msg)


def test_only_the_isolated_redis_is_accepted():
    assert iso.check_redis_url(ISO_REDIS) == "Redis 127.0.0.1:56379"
    for url in ("redis://localhost:6379/0", "redis://127.0.0.1:6379/0", "redis://cache.ejemplo.com:56379/0", "http://127.0.0.1:56379"):
        with pytest.raises(SystemExit, match="RECHAZADA"):
            iso.check_redis_url(url)


def test_targets_must_be_explicit_in_the_environment_and_match_the_effective_settings(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SWARM_REDIS_URL", raising=False)
    with pytest.raises(SystemExit, match="DATABASE_URL explícita requerida"):
        iso.require_isolated_database()
    with pytest.raises(SystemExit, match="SWARM_REDIS_URL explícita requerida"):
        iso.require_isolated_redis()
    monkeypatch.setenv("DATABASE_URL", DEV_DB)
    with pytest.raises(SystemExit, match="RECHAZADA"):
        iso.require_isolated_database()
    monkeypatch.setenv("DATABASE_URL", ISO_DB)                      # explícita y aislada, pero `settings` ya se fijó con otro valor al importarse
    from app.core.config import settings
    if settings.DATABASE_URL != ISO_DB:
        with pytest.raises(SystemExit, match="difiere"):
            iso.require_isolated_database()
    monkeypatch.setenv("SWARM_REDIS_URL", ISO_REDIS)
    from adaptation_swarm.config import SETTINGS
    if SETTINGS.redis_url != ISO_REDIS:
        with pytest.raises(SystemExit, match="difiere"):
            iso.require_isolated_redis()


def test_labels_and_output_targets_never_touch_frozen_results_packages_or_the_library(tmp_path):
    assert iso.check_label("repro-2026-09-25") == "repro-2026-09-25"
    for label in (None, "", "corrida poc", "../x", "a" * 65, "corrida-poc-1", "corrida-poc-2"):
        with pytest.raises(SystemExit):
            iso.check_label(label)
    with pytest.raises(SystemExit, match="obligatorio"):
        iso.require_out_dir(None)
    iso.check_output_targets([tmp_path / "nuevo.json"])
    for protected in (RESULTS / "nuevo.json", BACK / "experiments" / "evidence_package_2026-09-24-final" / "x.json",
                      BACK.parent / "datasets" / "adaptation_library" / "x.json", BACK.parent / "datasets" / "synthetic_profiles" / "x.json"):
        with pytest.raises(SystemExit, match="congelad"):
            iso.check_output_targets([protected])
    existing = tmp_path / "existe.json"
    existing.write_text("{}")
    with pytest.raises(SystemExit, match="ya existe"):
        iso.check_output_targets([existing])


# ── importar no ejecuta nada ────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("name", MODULES)
def test_modules_execute_nothing_at_import_time_statically_and_with_network_and_processes_blocked(name, monkeypatch):
    origin = Path(importlib.util.find_spec(name).origin)
    for node in ast.parse(origin.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.If) and "__name__" in ast.dump(node.test):
            continue
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)), \
            f"{origin.name}:{node.lineno} ejecuta código al importarse ({type(node).__name__})"
    attempts = []

    def blocked(*a, **k):
        attempts.append(1)
        raise ConnectionRefusedError("bloqueado")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(subprocess.Popen, "__init__", blocked)
    sys.modules.pop(name, None)
    importlib.import_module(name)
    assert attempts == []


# ── ejecutores: modo explícito, sin sobrescribir, separados de lo congelado ─────────────────────────────────────────
def _run_experiment(monkeypatch, *argv):
    from adaptation_swarm import run_experiment
    monkeypatch.setattr(sys, "argv", ["run_experiment", *argv])
    with pytest.raises(SystemExit) as exc:
        run_experiment.main()
    return str(exc.value)


def test_run_experiment_requires_an_explicit_mode_a_new_label_and_a_new_out_dir(monkeypatch, tmp_path):
    assert "modo obligatorio" in _run_experiment(monkeypatch, "--out-dir", str(tmp_path / "o"))
    assert "congelada" in _run_experiment(monkeypatch, "--run-label", "corrida-poc-1", "--out-dir", str(tmp_path / "o"))
    assert "--out-dir es obligatorio" in _run_experiment(monkeypatch, "--run-label", "repro-1")
    assert "congelados" in _run_experiment(monkeypatch, "--run-label", "repro-1", "--out-dir", str(RESULTS))
    assert "congelados" in _run_experiment(monkeypatch, "--sweep", "--out-dir", str(RESULTS))
    (tmp_path / "o").mkdir()
    (tmp_path / "o" / "adaptation_swarm_repro-1_cases.csv").write_text("x")
    assert "ya existe" in _run_experiment(monkeypatch, "--run-label", "repro-1", "--out-dir", str(tmp_path / "o"))
    (tmp_path / "o" / "adaptation_swarm_sensitivity.json").write_text("{}")
    assert "ya existe" in _run_experiment(monkeypatch, "--sweep", "--out-dir", str(tmp_path / "o"))


def test_run_experiment_refuses_missing_or_non_isolated_services_before_connecting(monkeypatch, tmp_path):
    monkeypatch.delenv("SWARM_REDIS_URL", raising=False)
    assert "SWARM_REDIS_URL explícita" in _run_experiment(monkeypatch, "--run-label", "repro-1", "--out-dir", str(tmp_path / "o"), "--dry-run")
    monkeypatch.setenv("SWARM_REDIS_URL", "redis://localhost:6379/0")
    assert "RECHAZADA" in _run_experiment(monkeypatch, "--run-label", "repro-1", "--out-dir", str(tmp_path / "o"))
    assert not (tmp_path / "o").exists()                                                # nada se creó


def test_write_reports_writes_only_in_the_given_dir_and_never_overwrites(tmp_path):
    from adaptation_swarm.run_experiment import report_paths, write_reports
    rows = [{"profile_id": "p", "g_best_S": [1, 2]}]
    path = write_reports("repro-1", {"run_label": "repro-1"}, {"n": 1}, rows, tmp_path / "nuevo")
    assert path.parent == tmp_path / "nuevo" and sorted(p.name for p in (tmp_path / "nuevo").iterdir()) == sorted(p.name for p in report_paths("repro-1", tmp_path / "nuevo"))
    original = {p.name: p.read_bytes() for p in (tmp_path / "nuevo").iterdir()}
    with pytest.raises(FileExistsError):
        write_reports("repro-1", {"run_label": "repro-1"}, {"n": 999}, [{"profile_id": "otro"}], tmp_path / "nuevo")
    assert {p.name: p.read_bytes() for p in (tmp_path / "nuevo").iterdir()} == original           # el intento rechazado no modificó nada
    (tmp_path / "nuevo" / "adaptation_swarm_repro-1_cases.csv").unlink()                            # solo queda el JSON: tampoco se pisa ni se completa a medias
    with pytest.raises(FileExistsError):
        write_reports("repro-1", {"run_label": "repro-1"}, {"n": 999}, [{"profile_id": "otro"}], tmp_path / "nuevo")
    assert (tmp_path / "nuevo" / "adaptation_swarm_repro-1.json").read_bytes() == original["adaptation_swarm_repro-1.json"]


def test_run_slice_requires_an_explicit_profile_and_a_new_json_path(monkeypatch, tmp_path):
    from adaptation_swarm import run_slice
    for argv, expected in (([], SystemExit), (["--profile", "p", "--json", str(RESULTS / "x.json")], SystemExit)):
        monkeypatch.setattr(sys, "argv", ["run_slice", *argv])
        with pytest.raises(expected):
            run_slice.main()
    monkeypatch.setenv("SWARM_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setattr(sys, "argv", ["run_slice", "--profile", "syn-visual_dominant-repetitive-r0"])
    with pytest.raises(SystemExit, match="RECHAZADA"):
        run_slice.main()


def test_executors_declare_which_services_they_need_and_where_they_write():
    text = {n: Path(importlib.util.find_spec(n).origin).read_text(encoding="utf-8") for n in MODULES[1:]}
    for name in ("adaptation_swarm.run_experiment", "adaptation_swarm.run_slice"):
        assert "Redis" in text[name] and "audio" in text[name] and "aislado" in text[name].lower() and "sobrescribe" in text[name]
    assert "PostgreSQL" in text["adaptation_swarm.run_experiment"] and "git rev-parse" in text["adaptation_swarm.run_experiment"]
    for name in ("adaptation_swarm.analysis.f1_audit", "adaptation_swarm.analysis.pso_audit"):
        assert "REQUIERE PostgreSQL" in text[name] and "READ ONLY" in text[name] and "--out-dir" in text[name] and "DATABASE_URL" in text[name]


# ── auditores: solo lectura, destino explícito y salida solo en la ruta indicada ────────────────────────────────────
class _Recorder:
    def __init__(self):
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, stmt, *a, **k):
        self.statements.append(str(stmt))

    def get(self, *a, **k):
        return None

    def scalars(self, *a, **k):
        return []


def test_audits_are_read_only_at_database_level_and_contain_no_write_operations(monkeypatch):
    import app.db.session as db_session
    from adaptation_swarm.analysis import f1_audit, pso_audit
    rec = _Recorder()
    monkeypatch.setattr(db_session, "SessionLocal", lambda: rec)
    with pytest.raises(AttributeError):                                   # el doble no tiene corrida: basta con ver la primera sentencia
        f1_audit.load_cases("x")
    assert rec.statements[0] == "SET TRANSACTION READ ONLY"
    rec.statements.clear()
    pso_audit.audit("x")
    assert rec.statements[0] == "SET TRANSACTION READ ONLY"
    for mod in (f1_audit, pso_audit):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in (".commit(", ".add(", ".delete(", ".merge(", ".flush(", "insert(", "update(", "INSERT ", "UPDATE ", "DELETE ", "DROP ", "TRUNCATE"):
            assert forbidden not in src, (mod.__name__, forbidden)


@pytest.mark.parametrize("module", ("f1_audit", "pso_audit"))
def test_audits_write_only_new_files_in_the_given_out_dir_and_never_overwrite(module, monkeypatch, tmp_path, capsys):
    mod = importlib.import_module(f"adaptation_swarm.analysis.{module}")
    monkeypatch.setattr(mod.iso, "require_isolated_database", lambda: "aislada (doble)")
    monkeypatch.setattr(mod, "audit", lambda *a, **k: {"run_label": "corrida-poc-1", "resultado": "doble"})
    monkeypatch.setattr(mod, "to_markdown", lambda a: "# informe\n")

    def run(*argv):
        monkeypatch.setattr(sys, "argv", [module, "--run-label", "corrida-poc-1", *argv])
        mod.main()

    with pytest.raises(SystemExit, match="--out-dir es obligatorio"):
        run()
    with pytest.raises(SystemExit, match="congelados"):
        run("--out-dir", str(RESULTS))                                     # auditar una corrida congelada NO autoriza escribir junto a ella
    out = tmp_path / "auditoria"
    run("--out-dir", str(out), "--out-md", str(tmp_path / "informe.md"))
    assert sorted(p.name for p in out.iterdir()) == [f"adaptation_swarm_corrida-poc-1_{module}.json"] and (tmp_path / "informe.md").read_text() == "# informe\n"
    with pytest.raises(SystemExit, match="ya existe"):
        run("--out-dir", str(out))
    capsys.readouterr()


def test_audits_refuse_a_missing_or_non_isolated_database_before_reading_anything(monkeypatch, tmp_path):
    from adaptation_swarm.analysis import f1_audit
    called = []
    monkeypatch.setattr(f1_audit, "audit", lambda *a, **k: called.append(1) or {})
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(sys, "argv", ["f1_audit", "--run-label", "corrida-poc-1", "--out-dir", str(tmp_path / "o")])
    with pytest.raises(SystemExit, match="DATABASE_URL explícita"):
        f1_audit.main()
    monkeypatch.setenv("DATABASE_URL", DEV_DB)
    with pytest.raises(SystemExit, match="RECHAZADA"):
        f1_audit.main()
    assert called == [] and not (tmp_path / "o").exists()


# ── repro_db_bootstrap.sh ───────────────────────────────────────────────────────────────────────────────────────────
SCRIPT = BACK / "scripts" / "repro_db_bootstrap.sh"


def _bootstrap(*args):
    return subprocess.run([shutil.which("bash"), str(SCRIPT), *args], capture_output=True, text=True, cwd=BACK, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})


def test_bootstrap_script_has_valid_syntax_and_no_destructive_or_env_reading_commands():
    assert subprocess.run([shutil.which("bash"), "-n", str(SCRIPT)], capture_output=True).returncode == 0
    body = "\n".join(ln for ln in SCRIPT.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))
    import re
    for forbidden in (r"\brm\b", r"\bdropdb\b", r"\bDROP\b", r"\bTRUNCATE\b", r"\bpodman\b", r"\bdocker\b", r"\bvolume\b", r"\bcreatedb\b", r"\bpsql\b",
                      r"(?:^|\s)(?:source|\.)\s+\S*\.env\b", r"\bcat\s+\S*\.env\b", r"--env-file"):        # nada destructivo ni lectura de backend/.env
        assert not re.search(forbidden, body, flags=re.MULTILINE), forbidden
    assert 'URL="${1:?' in body and "isolated_env check-database" in body and "isolated_env verify-effective" in body    # URL explícita, guarda y destino efectivo
    assert body.index("check-database") < body.index("alembic upgrade")                                                     # la guarda va ANTES de cualquier migración


@pytest.mark.skipif(not (BACK / ".venv" / "bin" / "python").exists(), reason="el script usa .venv/bin/python (desde backend/)")
def test_bootstrap_script_accepts_only_the_isolated_database_and_shows_the_target():
    ok = _bootstrap(ISO_DB, "--check-only")
    assert ok.returncode == 0 and "destino: PostgreSQL 127.0.0.1:55432/swarm_test" in ok.stdout and "swarm_test_pw" not in ok.stdout + ok.stderr
    for url in (DEV_DB, ISO_DB.replace("55432", "5432"), ISO_DB.replace("127.0.0.1", "db.ejemplo.com"), ISO_DB.replace("/swarm_test", "/upao_mas_edu")):
        bad = _bootstrap(url, "--check-only")
        assert bad.returncode != 0 and "RECHAZADA" in bad.stderr and "upao_pass" not in bad.stdout + bad.stderr and "swarm_test_pw" not in bad.stdout + bad.stderr
    assert _bootstrap().returncode != 0                                    # sin URL explícita no hay valor por defecto
    assert _bootstrap(ISO_DB, "--otra-cosa").returncode == 2               # argumento desconocido


# ── --help y --dry-run: sin conexión ni escritura ───────────────────────────────────────────────────────────────────
def _cli(*args, env_extra=None, remove=()):
    env = {k: v for k, v in os.environ.items() if k not in remove}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", **(env_extra or {})})
    return subprocess.run([sys.executable, "-m", *args], capture_output=True, text=True, cwd=BACK, env=env, timeout=120)


@pytest.mark.parametrize("module", ("run_experiment", "run_slice", "analysis.f1_audit", "analysis.pso_audit"))
def test_help_works_without_any_service_or_destination_and_writes_nothing(module):
    r = _cli(f"adaptation_swarm.{module}", "--help", remove=("DATABASE_URL", "SWARM_REDIS_URL"))
    output_option = "--json" if module == "run_slice" else "--out-dir"                  # única vía de escritura de cada herramienta
    assert r.returncode == 0 and "usage:" in r.stdout and output_option in r.stdout and "Traceback" not in r.stderr


def test_dry_run_validates_plan_library_and_destinations_without_connecting_or_writing(tmp_path):
    env = {"DATABASE_URL": ISO_DB, "SWARM_REDIS_URL": ISO_REDIS}                       # destinos aislados EXPLÍCITOS; los servicios no están: no se conecta
    out = tmp_path / "salida"
    r = _cli("adaptation_swarm.run_experiment", "--run-label", "repro-1", "--out-dir", str(out), "--dry-run", env_extra=env)
    assert r.returncode == 0 and "DRY-RUN OK" in r.stdout and "no se conectó ni se escribió nada" in r.stdout and not out.exists(), r.stderr[-400:]
    r = _cli("adaptation_swarm.run_experiment", "--sweep", "--out-dir", str(out), "--dry-run", env_extra=env)
    assert r.returncode == 0 and "sensibilidad" in r.stdout and not out.exists()
    r = _cli("adaptation_swarm.run_experiment", "--run-label", "repro-1", "--out-dir", str(out), "--dry-run", "--no-persist", env_extra={"SWARM_REDIS_URL": ISO_REDIS}, remove=("DATABASE_URL",))
    assert r.returncode == 0 and "PostgreSQL: no" in r.stdout                           # sin persistencia no se exige base de datos
    r = _cli("adaptation_swarm.run_slice", "--profile", "syn-visual_dominant-repetitive-r0", "--dry-run", env_extra={"SWARM_REDIS_URL": ISO_REDIS})
    assert r.returncode == 0 and "DRY-RUN OK" in r.stdout
