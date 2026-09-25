"""`loadtest/`: estructura, escenarios, aislamiento de destinos, dependencias y coherencia con los resultados archivados. Pura: NO ejecuta carga,
no levanta la API, PostgreSQL ni Redis y no usa red; solo lee archivos, analiza el código sin ejecutarlo y regenera los resúmenes de los resultados guardados."""

import ast
import csv
import hashlib
import re
import runpy
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

BACK = Path(__file__).resolve().parents[2]
LOAD = BACK / "loadtest"
RESULTS = LOAD / "results"
PKG_LOAD = BACK / "experiments" / "evidence_package_2026-09-24-final" / "04_carga"
PKG_MANIFEST = BACK / "experiments" / "evidence_package_2026-09-24-final" / "MANIFEST.sha256"
SCENARIOS = (1, 10, 25, 50, 100)
RUN_DIRS = ("20260923T230102_w1", "20260923T230739_w4", "jmeter_20260923T230346_w1", "jmeter_20260923T231024_w4")
SCRIPTS = sorted(p for p in LOAD.iterdir() if p.suffix in {".py", ".sh", ".jmx", ".md"})


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_the_declared_scenarios_are_1_10_25_50_and_100_users_everywhere():
    for sh in ("run_scenarios.sh", "run_jmeter_scenarios.sh"):
        assert re.search(r"for U in 1 10 25 50 100;", (LOAD / sh).read_text(encoding="utf-8")), sh
    for py in ("summarize.py", "summarize_jtl.py"):
        assert "(1, 10, 25, 50, 100)" in (LOAD / py).read_text(encoding="utf-8"), py
    for d in RUN_DIRS:
        names = {p.name for p in (RESULTS / d).iterdir()}
        for u in SCENARIOS:
            assert (f"u{u}.jtl" if d.startswith("jmeter") else f"u{u}_stats.csv") in names, (d, u)
        assert "warmup.jtl" in names or "warmup_stats.csv" in names                      # warm-up descartado, pero registrado
        assert "summary.md" in names


def test_default_destinations_are_local_and_never_a_production_environment():
    text = {p.name: p.read_text(encoding="utf-8") for p in SCRIPTS}
    for name, content in text.items():
        hosts = re.findall(r"https?://([A-Za-z0-9._-]+)", content)
        allowed = {"localhost", "127.0.0.1", "archive.apache.org"}                        # esta última: enlace de descarga de JMeter en un comentario
        assert set(hosts) <= allowed, (name, hosts)
        assert not re.search(r"upao_|postgres-dev|pgdata|render\.com|amazonaws|herokuapp|/home/|/var/home/", content), name
        assert not re.search(r"(?i)(api[_-]?key|secret|password|token)\s*[=:]\s*['\"]?[A-Za-z0-9]{6,}", content), name
    for sh in ("run_scenarios.sh", "run_jmeter_scenarios.sh"):
        assert "${SWARM_API_KEY:?" in text[sh]                                              # la clave es obligatoria y no tiene valor por defecto
    assert re.search(r'HOST="\$\{1:-http://localhost:8000\}"', text["run_scenarios.sh"])
    assert re.search(r'HOST="\$\{1:-http://localhost:8765\}"', text["run_jmeter_scenarios.sh"])
    assert 'KEY = os.environ.get("SWARM_API_KEY", "")' in text["locustfile.py"]
    assert 'os.environ.get("SWARM_REDIS_URL", "redis://localhost:6379/0")' in text["sample_resources.py"]   # el Redis medido es el del backend
    plan = ET.parse(LOAD / "plan.jmx").getroot()
    props = {e.text for e in plan.iter("stringProp")}
    assert "${__P(host,localhost)}" in props and "${__P(key)}" in props                   # host local por defecto; clave sin valor por defecto


def test_plan_jmx_is_well_formed_and_targets_the_adaptation_endpoint_with_the_declared_parameters():
    plan = ET.parse(LOAD / "plan.jmx").getroot()
    props = {e.get("name"): (e.text or "") for e in plan.iter("stringProp")}
    assert props["ThreadGroup.num_threads"] == "${__P(threads,1)}" and props["ThreadGroup.duration"] == "${__P(duration,60)}"
    assert props["HTTPSampler.method"] == "POST" and props["HTTPSampler.path"].startswith("/api/adaptation?batch_seed=20260923")
    assert '"chain_valid":true' in {e.text for e in plan.iter("stringProp")}               # el paquete completo se comprueba en cada respuesta


def test_shell_scripts_have_valid_syntax_without_running_them():
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash no disponible")
    for sh in ("run_scenarios.sh", "run_jmeter_scenarios.sh"):
        r = subprocess.run([bash, "-n", str(LOAD / sh)], capture_output=True, text=True)                    # -n: solo analiza, no ejecuta
        assert r.returncode == 0, (sh, r.stderr)


def test_locustfile_targets_the_endpoint_with_the_versioned_dataset_without_importing_locust():
    src = (LOAD / "locustfile.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AdaptationUser")
    assert "constant(0)" in ast.unparse(cls)                                                # sin think-time, como declara el README
    assert "/api/adaptation?batch_seed=" in src and 'name="POST /api/adaptation"' in src
    assert (BACK.parent / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl").is_file()   # DATASET = parents[2] / datasets / … existe en Git


def test_every_third_party_import_of_loadtest_is_declared_in_the_requirements():
    declared = set()
    for req in (BACK / "requirements-loadtest.txt", BACK / "requirements.txt"):
        declared |= {re.split(r"[=<>\[ ]", ln.strip(), maxsplit=1)[0].lower().replace("_", "-")
                     for ln in req.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")}
    used = set()
    for py in LOAD.glob("*.py"):
        for node in ast.walk(ast.parse(py.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                used |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                used.add(node.module.split(".")[0])
    third_party = {m for m in used if m not in sys.stdlib_module_names}
    assert third_party == {"locust", "psutil", "redis"}, third_party
    assert third_party <= declared
    lt = {ln.split("==")[0]: ln.split("==")[1] for ln in (BACK / "requirements-loadtest.txt").read_text(encoding="utf-8").splitlines() if "==" in ln}
    main = {ln.split("==")[0]: ln.split("==")[1] for ln in (BACK / "requirements.txt").read_text(encoding="utf-8").splitlines() if "==" in ln}
    assert lt["redis"] == main["redis"] and lt["locust"] == "2.46.6" and lt["psutil"] == "7.2.2"          # mismo pin que el resto del proyecto
    try:
        from importlib.metadata import requires
        assert any(r.lower().startswith("gevent") for r in (requires("locust") or []))                   # gevent llega como dependencia de locust
    except ModuleNotFoundError:
        pass


def test_archived_results_are_byte_identical_to_the_final_evidence_package_and_its_manifest():
    """Los resultados de `loadtest/results/` no se modifican: coinciden con `04_carga/` del paquete final y con los hashes de su `MANIFEST.sha256`."""
    manifest = dict(reversed(ln.split("  ", 1)) for ln in PKG_MANIFEST.read_text(encoding="utf-8").splitlines())
    pkg_files = sorted(p for p in PKG_LOAD.rglob("*") if p.is_file())
    assert len(pkg_files) == 85
    for p in pkg_files:
        rel = p.relative_to(PKG_LOAD).as_posix()
        assert _sha(RESULTS / rel) == _sha(p) == manifest[f"04_carga/{rel}"], rel
    on_disk = {p.relative_to(RESULTS).as_posix() for p in RESULTS.rglob("*") if p.is_file() and ".impeccable" not in p.parts}
    assert on_disk == {p.relative_to(PKG_LOAD).as_posix() for p in pkg_files}                # ni sobra ni falta ningún resultado


@pytest.mark.parametrize("run_dir", RUN_DIRS)
def test_summarize_scripts_regenerate_each_stored_summary_exactly(run_dir, monkeypatch, capsys):
    script = "summarize_jtl.py" if run_dir.startswith("jmeter") else "summarize.py"
    monkeypatch.setattr(sys, "argv", [script, str(RESULTS / run_dir)])
    runpy.run_path(str(LOAD / script), run_name="__main__")
    assert capsys.readouterr().out == (RESULTS / run_dir / "summary.md").read_text(encoding="utf-8")


def test_stored_locust_numbers_match_what_the_evidence_index_reports_and_claim_no_compliance():
    def agg(d):
        rows = [r for r in csv.DictReader((RESULTS / d / "u25_stats.csv").open(encoding="utf-8")) if r["Name"] == "Aggregated"]
        return float(rows[0]["Requests/s"]), int(rows[0]["95%"]), int(rows[0]["Failure Count"])
    (rps1, p95_1, f1), (rps4, p95_4, f4) = agg("20260923T230102_w1"), agg("20260923T230739_w4")
    assert (round(rps1), p95_1, f1) == (16, 2200, 0) and (round(rps4), p95_4, f4) == (40, 1100, 0)     # 1 worker: P95 2.2 s, ≈16 req/s; 4 workers: 1.1 s, ≈40 req/s
    assert "Nada de esto declara cumplimiento" in (LOAD / "README.md").read_text(encoding="utf-8")
