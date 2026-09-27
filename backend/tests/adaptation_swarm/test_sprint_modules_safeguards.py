"""Salvaguardas de los módulos nuevos del sprint post-asesor (`gold/labels_v2`, `gold/rubric_v2`, `gold/f1_multilabel`, `analysis/core_replay`, `analysis/replicas`,
`analysis/baseline_bruteforce`, `analysis/balanced_alternatives`). Puras: importar no ejecuta nada, y ningún módulo usa red, procesos, bases de datos ni servicios externos.
Solo los ejecutores con salida (`replicas`, `baseline_bruteforce`, `balanced_alternatives`) escriben, y únicamente en un directorio nuevo validado por `isolated_env`."""

import ast
import importlib
import importlib.util
import socket
import subprocess
import sys
from pathlib import Path

import pytest

MODULES = ("adaptation_swarm.gold.labels_v2", "adaptation_swarm.gold.rubric_v2", "adaptation_swarm.gold.f1_multilabel", "adaptation_swarm.analysis.core_replay",
           "adaptation_swarm.analysis.replicas", "adaptation_swarm.analysis.baseline_bruteforce", "adaptation_swarm.analysis.balanced_alternatives",
           "adaptation_swarm.analysis.inference", "adaptation_swarm.analysis.replica_evaluation", "adaptation_swarm.metrics.gold_panel",
           "adaptation_swarm.analysis.preregistration")
WRITERS = {"adaptation_swarm.analysis.replicas", "adaptation_swarm.analysis.preregistration", "adaptation_swarm.analysis.baseline_bruteforce", "adaptation_swarm.analysis.balanced_alternatives"}
FORBIDDEN = {"subprocess", "socket", "redis", "psycopg", "psycopg2", "sqlalchemy", "openai", "requests", "httpx", "urllib", "asyncio", "podman", "docker", "app"}


def _origin(name):
    return Path(importlib.util.find_spec(name).origin)


@pytest.mark.parametrize("name", MODULES)
def test_importing_executes_nothing_and_needs_no_network_or_processes(name, monkeypatch):
    for node in ast.parse(_origin(name).read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            continue
        if isinstance(node, ast.If) and "__name__" in ast.dump(node.test):
            continue
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.ClassDef)), f"{name}:{node.lineno} ejecuta código al importarse"
    attempts = []
    blocked = lambda *a, **k: attempts.append(1) or (_ for _ in ()).throw(ConnectionRefusedError("bloqueado"))
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(subprocess.Popen, "__init__", blocked)
    sys.modules.pop(name, None)
    importlib.import_module(name)
    assert attempts == []


@pytest.mark.parametrize("name", MODULES)
def test_modules_use_no_network_process_database_or_service_imports(name):
    tree = ast.parse(_origin(name).read_text(encoding="utf-8"))
    imported = {n.names[0].name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)} | \
               {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & FORBIDDEN, imported & FORBIDDEN
    src = _origin(name).read_text(encoding="utf-8")
    if name not in WRITERS:
        assert "write_text" not in src and "write_bytes" not in src and ".open(" not in src        # solo los ejecutores escriben
    else:
        assert "check_new_output_targets" in src and "isolated_env" in src                          # y lo hacen a través de la guardia de destinos de los analizadores
        assert "iso.check_output_targets(" not in src                                               # (la variante estricta; nunca la básica)


def test_writers_never_default_to_a_destination_and_never_overwrite():
    import re
    for name in WRITERS:
        src = _origin(name).read_text(encoding="utf-8")
        assert '"--out-dir"' in src and "required=True" in src.split('"--out-dir"', 1)[1].split(")", 1)[0], name      # sin destino por defecto
        assert "exist_ok=True" not in src, name                                                                    # nunca reutilizan un directorio existente
        assert not re.search(r"open\([^)]*[\"']w[\"']", src), name                                                # ni abren en modo «w» (sobrescribir); solo «x» (exclusivo)


# ── C: salidas protegidas de los analizadores nuevos (loadtest/results y el paquete adaptation_swarm) ────────────────
import json as _json

from adaptation_swarm.analysis import balanced_alternatives as _ba
from adaptation_swarm.analysis import baseline_bruteforce as _bb
from adaptation_swarm.analysis import replicas as _rp
from adaptation_swarm.tools import isolated_env as _iso

_LOADTEST = _iso.BACK / "loadtest" / "results"
_PACKAGE = _iso.BACK / "adaptation_swarm"


def _listing(root: Path) -> list[str]:
    return sorted(str(p.relative_to(root)) for p in root.rglob("*")) if root.exists() else []


def _forbidden_targets(tmp_path: Path) -> dict[str, Path]:
    link = tmp_path / "enlace_a_loadtest"
    link.symlink_to(_LOADTEST, target_is_directory=True)
    return {"loadtest/results": _LOADTEST / "nueva_salida", "adaptation_swarm raíz": _PACKAGE / "nueva_salida", "adaptation_swarm/analysis": _PACKAGE / "analysis" / "nueva_salida",
            "recorrido con ..": _iso.BACK / "experiments" / ".." / "loadtest" / "results" / "nueva_salida", "enlace simbólico": link / "nueva_salida"}


def test_new_analyzer_guard_rejects_loadtest_results_and_the_package_but_is_not_global(tmp_path):
    for label, bad in _forbidden_targets(tmp_path).items():
        with pytest.raises(SystemExit, match="no admite salidas"):
            _iso.check_new_output_targets([bad / "x.json"])
    _iso.check_new_output_targets([tmp_path / "nuevo" / "x.json"])                                         # un destino legítimo nuevo
    _iso.check_new_output_targets([_iso.BACK / "experiments" / "replicas_nuevas" / "x.json"])              # ni una carpeta nueva junto a los resultados congelados
    _iso.check_output_targets([_LOADTEST / "2099-01-01_hw" / "x.json"])                                    # la guardia básica NO cambió: no hay protección global sobre loadtest/results
    for frozen in (_iso.BACK / "experiments" / "results" / "nueva", _iso.REPO / "datasets" / "nueva"):
        with pytest.raises(SystemExit):
            _iso.check_new_output_targets([frozen / "x.json"])                                             # y las protecciones anteriores siguen vigentes


def test_writers_refuse_to_write_outside_the_allowed_output(tmp_path):
    before = _listing(_LOADTEST)
    plan = _rp.build_plan(master_seed=1, k=2, library_version="lib-v5-9ae9ffdd", provisional=True, limit_profiles=1)
    rep_bb, rep_ba = {"x": 1}, {"x": 1}
    for label, bad in _forbidden_targets(tmp_path).items():
        for what, call in (("replicas.write_plan", lambda b=bad: _rp.write_plan(plan, b)), ("replicas.run", lambda b=bad: _rp.run(plan, b)),
                           ("baseline.write_report", lambda b=bad: _bb.write_report(rep_bb, b)), ("alternativas.write_report", lambda b=bad: _ba.write_report(rep_ba, b))):
            with pytest.raises(SystemExit):
                call()
            assert not bad.exists(), f"{what} creó {bad} ({label})"
    assert _listing(_LOADTEST) == before                                                                   # loadtest/results quedó exactamente igual


def test_cli_entry_points_refuse_forbidden_out_dirs_before_doing_any_work(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(_bb, "run_baseline", lambda *a, **k: calls.append("medición"))
    monkeypatch.setattr(_ba, "build_report", lambda *a, **k: calls.append("informe"))
    for label, bad in _forbidden_targets(tmp_path).items():
        with pytest.raises(SystemExit):
            _bb.main(["--library-version", "lib-v5-9ae9ffdd", "--batch-seed", "1", "--out-dir", str(bad)])
        with pytest.raises(SystemExit):
            _ba.main(["--out-dir", str(bad)])
        with pytest.raises(SystemExit):
            _rp.main(["plan", "--master-seed", "1", "--library-version", "lib-v5-9ae9ffdd", "--provisional", "--limit-profiles", "1", "--out-dir", str(bad)])
        assert not bad.exists()
    assert calls == []                                                                                     # rechazan ANTES de medir o calcular
