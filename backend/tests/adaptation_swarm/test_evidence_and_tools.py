"""Paquete de evidencia final congelado (`evidence_package_2026-09-24-final`) y herramientas de mantenimiento de la biblioteca.
Sin PostgreSQL, Redis, OpenAI, TTS ni red: solo se leen archivos versionados y la biblioteca (sin audio) y se usan subprocesos locales de solo lectura
(`alembic heads`, versiones de podman/node/g++)."""

import hashlib
from pathlib import Path

import pytest

from adaptation_swarm.tools import dedupe_library
from adaptation_swarm.tools.build_evidence_package import sha256, verify

BACK = Path(__file__).resolve().parents[2]
PKG = BACK / "experiments" / "evidence_package_2026-09-24-final"
HISTORIC = "evidence_package_2026-09-23"           # paquete histórico congelado: fuera de Git; el constructor jamás lo regenera ni lo sobrescribe
RESULTS = BACK / "experiments" / "results"


def test_evidence_package_hashes_all_match_the_manifest():
    assert PKG.exists() and (PKG / "MANIFEST.sha256").exists()
    assert verify(PKG) == []


def test_frozen_runs_in_the_package_are_byte_identical_to_the_live_results():
    for name in ("adaptation_swarm_corrida-poc-1.json", "adaptation_swarm_corrida-poc-1_cases.csv",
                 "adaptation_swarm_corrida-poc-2.json", "adaptation_swarm_corrida-poc-2_cases.csv"):
        assert sha256(PKG / "02_corridas_y_auditorias" / name) == sha256(RESULTS / name), name


def test_evidence_index_separates_demonstrated_open_and_human_dependent():
    idx = (PKG / "README_EVIDENCE_INDEX.md").read_text()
    for h in ("## 2. DEMOSTRADO", "## 3. ABIERTO", "## 4. DEPENDE DE PERSONAS", "PENDIENTE DE RECOLECCIÓN HUMANA"):
        assert h in idx
    assert "0.8031" in idx and "corrida-poc-1" in idx and "corrida-poc-2" in idx


def test_package_refuses_to_overwrite(tmp_path):
    from adaptation_swarm.tools.build_evidence_package import build
    with pytest.raises(SystemExit, match="ya existe"):
        build(PKG)


def test_builder_requires_an_audit_dir_and_never_defaults_to_a_personal_path(monkeypatch, tmp_path):
    from adaptation_swarm.tools import build_evidence_package as bep
    monkeypatch.setattr(bep, "preflight", lambda out, sealed=None: {})                    # las validaciones previas ya se prueban aparte
    with pytest.raises(SystemExit, match="--audit-dir es obligatorio"):
        bep.build(tmp_path / "evidence_package_nuevo")
    with pytest.raises(SystemExit, match="--audit-dir es obligatorio"):
        bep.build(tmp_path / "evidence_package_nuevo", audit_dir=tmp_path / "no_existe")
    assert not (tmp_path / "evidence_package_nuevo").exists()                              # nada se crea a medias
    assert not hasattr(bep, "AUDIT_DIR") and "/home/" not in Path(bep.__file__).read_text(encoding="utf-8")


def test_dedupe_plans_by_hash_and_apply_preserves_every_file(tmp_path):
    a, b, c = tmp_path / "v1" / "x.bin", tmp_path / "v2" / "x.bin", tmp_path / "v2" / "y.bin"
    for p, data in ((a, b"AAAA" * 1000), (b, b"AAAA" * 1000), (c, b"BBBB" * 1000)):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    r = dedupe_library.plan(tmp_path)
    assert r["files"] == 3 and r["unique_contents"] == 2 and len(r["links_to_create"]) == 1 and r["bytes_saved"] == 4000
    assert a.stat().st_ino != b.stat().st_ino                                     # la simulación no modificó nada
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b, c)}
    assert dedupe_library.apply(r["links_to_create"]) == 1
    assert a.stat().st_ino == b.stat().st_ino and c.stat().st_ino != a.stat().st_ino
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b, c)} == before   # mismos bytes en cada ruta
    assert dedupe_library.plan(tmp_path)["links_to_create"] == []                 # idempotente


# ── Fase 3C: correcciones detectadas en la auditoría pre-commit ─────────────────────────────────────────────────

def test_latest_library_version_numeric_order(tmp_path):
    """lib-v10 debe ser posterior a lib-v9 (el orden lexicográfico anterior las invertía y dejó a v10 fuera del paquete)."""
    from adaptation_swarm.tools.build_evidence_package import latest_library_version
    for name in ("lib-v1-aaaaaaaa", "lib-v9-bbbbbbbb", "lib-v10-cccccccc", "lib-v2-dddddddd"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "manifest.json").write_text("{}")
    assert sorted(p.name for p in tmp_path.glob("lib-v*"))[-1].startswith("lib-v9")      # el comportamiento defectuoso anterior
    assert latest_library_version(tmp_path) == "lib-v10-cccccccc"
    (tmp_path / "lib-v10-cccccccc" / "manifest.json").unlink()                           # sin manifiesto no se acepta
    with pytest.raises(SystemExit):
        latest_library_version(tmp_path)


def test_latest_library_version_of_the_real_library_is_the_highest_number():
    from adaptation_swarm.config import SETTINGS
    from adaptation_swarm.tools.build_evidence_package import latest_library_version
    numbers = [int(p.name.split("-")[1][1:]) for p in SETTINGS.library_root.glob("lib-v*")]
    assert latest_library_version(SETTINGS.library_root).startswith(f"lib-v{max(numbers)}-")


def test_v10_semantic_audit_exists():
    """La afirmación sobre lib-v10 se apoya en un archivo generado por la herramienta real (guardado en el paquete), no en el de v9."""
    import json
    from adaptation_swarm.config import SETTINGS
    from adaptation_swarm.multimodal.extend import audit_library
    from adaptation_swarm.multimodal.library import LibraryStore
    v10 = "lib-v10-5dd83cd4"
    f = PKG / "02_corridas_y_auditorias" / f"library_semantic_audit_{v10}.json"
    assert f.exists()
    saved = json.loads(f.read_text())
    assert saved["library_version"] == v10 and saved["concepts"] == 30
    assert saved == audit_library(LibraryStore.open(SETTINGS.library_root, v10))          # coincide con una re-auditoría en vivo
    idx = (BACK / "adaptation_swarm" / "EVIDENCE_INDEX.md").read_text()
    assert f"library_semantic_audit_{v10}.json" in idx or "`extend --base lib-v10-5dd83cd4 --audit-only`" in idx
    assert "lib-v9/v10: 0/0/0" not in idx


def test_environment_json_reports_real_alembic_head(tmp_path):
    import re
    import subprocess
    import sys

    from adaptation_swarm.tools import build_evidence_package as bep
    real = subprocess.run([sys.executable, "-m", "alembic", "heads"], capture_output=True, text=True, cwd=BACK).stdout
    expected = re.search(r"^([0-9a-f]+) \(head\)", real, flags=re.MULTILINE).group(1)          # independiente de la función
    assert bep.alembic_head() == expected
    env = bep.collect_environment("lib-vX")
    assert env["alembic_head"] == expected and not env["alembic_head"].startswith("FAILED") and env["library_latest"] == "lib-vX"
    with pytest.raises(RuntimeError):                       # fuera de backend/ (sin alembic.ini) NO se registra texto de error como head
        bep.alembic_head(tmp_path)


# ── Fase 3E: constructor seguro y paquete final 2026-09-24 ──────────────────────────────────────────────────────────

def test_builder_requires_explicit_out_and_never_targets_the_historic_package(tmp_path):
    import subprocess
    import sys

    from adaptation_swarm.tools import build_evidence_package as bep
    r = subprocess.run([sys.executable, "-m", "adaptation_swarm.tools.build_evidence_package"], capture_output=True, text=True, cwd=BACK)
    assert r.returncode == 2 and "--out es obligatorio" in r.stderr                      # sin destino por defecto
    for target in (BACK / "experiments" / HISTORIC, BACK / "experiments" / ".." / "experiments" / HISTORIC, tmp_path / HISTORIC):
        with pytest.raises(SystemExit, match="histórico"):
            bep.check_destination(target)
        with pytest.raises(SystemExit):
            bep.preflight(target)
    with pytest.raises(SystemExit, match="ya existe"):
        bep.check_destination(tmp_path)                                                   # un directorio existente no se sobrescribe
    bep.check_destination(tmp_path / "evidence_package_nuevo")                            # un destino nuevo es válido


def test_dry_run_preflight_validates_everything_and_writes_nothing(tmp_path):
    from adaptation_swarm.tools import build_evidence_package as bep
    out = tmp_path / "evidence_package_dry"
    pre = bep.preflight(out)
    assert not out.exists() and list(tmp_path.iterdir()) == []
    assert pre["latest"].startswith("lib-v10-") and pre["inventory"]["latest"] == pre["latest"]
    assert pre["inventory"]["runs"] == {"corrida-poc-1": "lib-v5-9ae9ffdd", "corrida-poc-2": "lib-v9-a0231e9b"}
    assert pre["env"]["alembic_head"] and not pre["env"]["alembic_head"].startswith("FAILED")


def test_final_evidence_package_is_consistent_without_audio_and_without_personal_paths():
    import json

    from adaptation_swarm.tools import build_evidence_package as bep
    assert PKG.exists() and bep.validate_package(PKG) == []
    lmap = json.loads((PKG / "07_biblioteca" / "library_map.json").read_text())
    assert lmap["latest"].startswith("lib-v10-") and lmap["runs"] == {"corrida-poc-1": "lib-v5-9ae9ffdd", "corrida-poc-2": "lib-v9-a0231e9b"}
    assert lmap["audio_in_git"] is False and lmap["audio_in_this_package"] is False and not list(PKG.rglob("*.mp3"))
    env = json.loads((PKG / "06_entorno" / "environment.json").read_text())
    assert env["alembic_head"] in bep.alembic_lineage() and env["library_latest"] == lmap["latest"]
    he = json.loads((PKG / "06_entorno" / "human_eval_status.json").read_text())
    assert he["participants"] == 0 and he["sus_responses"] == 0 and he["gold_panel"]["n_evaluators"] == 0           # SUS y panel: sin respuestas
    for f in PKG.rglob("*"):
        if f.is_file():
            text = f.read_text(encoding="utf-8", errors="ignore")
            assert "/home/" not in text, f"ruta personal en {f.relative_to(PKG)}"                # cubre también /var/home/


def test_the_package_reports_the_observed_f1_and_does_not_claim_the_target_is_met():
    import json
    for n in (1, 2):
        f1 = json.loads((PKG / "02_corridas_y_auditorias" / f"adaptation_swarm_corrida-poc-{n}.json").read_text())["summary"]["f1"]["f1_adapt"]
        assert f1 == pytest.approx(0.8031, abs=1e-4) and f1 < 0.85
    sens = json.loads((PKG / "02_corridas_y_auditorias" / "adaptation_swarm_sensitivity.json").read_text())["results"]
    best = max(r["f1_adapt"] for r in sens.values())
    assert best == pytest.approx(0.8164, abs=1e-4) and best < 0.85
    assert "0.8031" in (PKG / "README_EVIDENCE_INDEX.md").read_text() and "no alcanza el umbral" in (PKG / "README_EVIDENCE_INDEX.md").read_text()


def test_validate_package_detects_a_tampered_fact(tmp_path):
    import json
    import shutil

    from adaptation_swarm.tools import build_evidence_package as bep
    bad = tmp_path / "pkg"
    shutil.copytree(PKG, bad)
    env_path = bad / "06_entorno" / "environment.json"
    env = json.loads(env_path.read_text())
    env["alembic_head"] = "FAILED: x"
    env_path.write_text(json.dumps(env))
    problems = bep.validate_package(bad)
    assert any("hash:" in p for p in problems) and any("alembic_head" in p for p in problems)
