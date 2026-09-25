"""Inventario/verificación de la biblioteca (Decisión C): estados ausente / hash incorrecto / correcto, orden numérico de versiones y
coherencia con los manifiestos. Las bibliotecas sintéticas de estas pruebas viven en `tmp_path`; la real solo se LEE."""

import ast
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path

import pytest

from adaptation_swarm.config import SETTINGS
from adaptation_swarm.multimodal.versioning import format_version
from adaptation_swarm.tools import library_inventory as inv_mod

CONCEPT = "c0"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _make_version(root: Path, number: int, base: str | None = None) -> str:
    """Biblioteca mínima: 1 código, 1 texto, 1 SVG y 2 audios, con un manifiesto cuyo hash da nombre a la versión."""
    files = {"code_c0.py": b"print(1)\n", "text_t0.txt": b"hola", "svg_c0d0.svg": b"<svg/>", "audio_t0a0.mp3": b"ID3-A", "audio_t0a1.mp3": b"ID3-BB"}
    modality = {"code": "code", "text": "text", "svg": "svg", "audio": "audio"}
    entries = [{"path": f"artifacts/{CONCEPT}/{n}", "sha256": _sha(b), "size_bytes": len(b), "modality": modality[n.split('_')[0]]} for n, b in files.items()]
    manifest = {"base_version": base, "entries": entries, "anchors": {}, "changes": []}
    version = format_version(number, manifest)
    d = root / version
    (d / "artifacts" / CONCEPT).mkdir(parents=True)
    for n, b in files.items():
        (d / "artifacts" / CONCEPT / n).write_bytes(b)
    (d / "manifest.json").write_text(json.dumps({**manifest, "library_version": version}))
    return version


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "adaptation_library"
    root.mkdir()
    return root


def test_versions_are_ordered_numerically_and_latest_is_v10(lib):
    v2, v9, v10 = _make_version(lib, 2), _make_version(lib, 9), _make_version(lib, 10)
    inv = inv_mod.inventory(lib, results_dir=None)
    assert inv["versions_order"] == [v2, v9, v10] and inv["latest"] == v10
    assert [v["number"] for v in inv["versions"]] == [2, 9, 10]
    assert sorted(inv["versions_order"])[-1] == v9                     # el orden lexicográfico daría v9: NO se usa


def test_complete_library_is_present_and_hash_correct(lib):
    _make_version(lib, 1)
    v = inv_mod.inventory(lib, results_dir=None)["versions"][0]
    assert v["audio"] == {"count": 2, "bytes": 11, "presence": "completa", "integrity": "hash_correcto"}
    assert v["svg"]["presence"] == "completa" and v["counts"] == {"code": 1, "cpp": 0, "text": 1, "mmd": 0}
    assert v["manifest_id_ok"] and v["unlisted_files"] == [] and v["files_on_disk"] == 6 and v["manifest_entries"] == 5


def test_absent_audio_is_not_reported_as_a_hash_mismatch(lib):
    ver = _make_version(lib, 1)
    for mp3 in (lib / ver).rglob("*.mp3"):
        mp3.unlink()
    inv = inv_mod.inventory(lib, results_dir=None)
    a = inv["versions"][0]["audio"]
    assert a["presence"] == "ausente" and a["integrity"] == "no_verificable"
    assert inv["versions"][0]["by_modality"]["audio"]["hash_mismatch"] == 0 and inv["versions"][0]["by_modality"]["audio"]["absent"] == 2
    assert inv["summary"] == {"versions": 1, "any_hash_mismatch": False, "any_absent": True, "any_manifest_id_mismatch": False}
    assert inv["versions"][0]["svg"]["integrity"] == "hash_correcto"          # el resto de modalidades no se contamina


def test_present_audio_with_wrong_hash_is_a_hash_mismatch_not_absent(lib):
    ver = _make_version(lib, 1)
    with (lib / ver / "artifacts" / CONCEPT / "audio_t0a0.mp3").open("ab") as fh:
        fh.write(b"x")
    inv = inv_mod.inventory(lib, results_dir=None)
    c = inv["versions"][0]["by_modality"]["audio"]
    assert (c["ok"], c["absent"], c["hash_mismatch"]) == (1, 0, 1)
    assert inv["versions"][0]["audio"]["integrity"] == "hash_incorrecto" and inv["summary"]["any_hash_mismatch"] and not inv["summary"]["any_absent"]


def test_partial_svg_and_unlisted_files_are_reported(lib):
    ver = _make_version(lib, 1)
    (lib / ver / "artifacts" / CONCEPT / "svg_c0d0.svg").unlink()
    (lib / ver / "artifacts" / CONCEPT / "extra.txt").write_text("no listado")
    v = inv_mod.inventory(lib, results_dir=None)["versions"][0]
    assert v["svg"]["presence"] == "ausente" and v["unlisted_files"] == [f"artifacts/{CONCEPT}/extra.txt"]


def test_altered_manifest_is_detected(lib):
    ver = _make_version(lib, 1)
    m = json.loads((lib / ver / "manifest.json").read_text())
    m["changes"].append({"tampered": True})
    (lib / ver / "manifest.json").write_text(json.dumps(m))
    inv = inv_mod.inventory(lib, results_dir=None)
    assert inv["versions"][0]["manifest_id_ok"] is False and inv["summary"]["any_manifest_id_mismatch"]


def test_hardlinked_files_are_hashed_once_and_inventory_is_deterministic(lib):
    v1 = _make_version(lib, 1)
    v2 = _make_version(lib, 2, base=v1)
    for f in (lib / v2).rglob("*.mp3"):                              # v2 comparte inodos con v1
        twin = lib / v1 / f.relative_to(lib / v2)
        f.unlink()
        os.link(twin, f)
    calls = []
    real = inv_mod._sha256_file
    inv_mod._sha256_file = lambda p: (calls.append(p), real(p))[1]   # cuenta las lecturas de contenido
    try:
        a = inv_mod.inventory(lib, results_dir=None)
    finally:
        inv_mod._sha256_file = real
    mp3_reads = [p for p in calls if p.suffix == ".mp3"]
    assert len(mp3_reads) == 2                                        # 2 inodos únicos, no 4
    b = inv_mod.inventory(lib, results_dir=None)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_write_inventory_never_overwrites(lib, tmp_path):
    _make_version(lib, 1)
    inv = inv_mod.inventory(lib, results_dir=None)
    out = tmp_path / "out"
    assert {p.name for p in inv_mod.write_inventory(inv, out)} == {"library_inventory.json", "library_inventory.md"}
    assert json.loads((out / "library_inventory.json").read_text())["schema"] == inv_mod.SCHEMA
    with pytest.raises(SystemExit):
        inv_mod.write_inventory(inv, out)


def test_presence_summary_is_fast_and_separates_absent_from_present(lib):
    ver = _make_version(lib, 1)
    assert inv_mod.presence_summary(lib)[ver] == {"audio_entries": 2, "audio_absent": 0, "svg_entries": 1, "svg_absent": 0, "manifest_absent": 0}
    (lib / ver / "artifacts" / CONCEPT / "audio_t0a0.mp3").unlink()
    assert inv_mod.presence_summary(lib)[ver]["audio_absent"] == 1


def test_real_library_inventory_matches_the_manifests():
    """Sobre la biblioteca real (solo lectura, sin resultados experimentales): 10 versiones en orden numérico, latest = v10 y ningún hash
    incorrecto. Un clon sin mp3 da «ausente», nunca «hash incorrecto»."""
    inv = inv_mod.inventory(SETTINGS.library_root, results_dir=None)
    assert [v["number"] for v in inv["versions"]] == list(range(1, 11))
    assert inv["latest"].startswith("lib-v10-") and inv["versions"][-1]["is_latest"]
    assert not inv["summary"]["any_hash_mismatch"] and not inv["summary"]["any_manifest_id_mismatch"]
    for v in inv["versions"]:
        man = json.loads((SETTINGS.library_root / v["version"] / "manifest.json").read_text())
        assert v["manifest_entries"] == len(man["entries"]) and v["manifest_sha256"] == _sha(
            (SETTINGS.library_root / v["version"] / "manifest.json").read_bytes())
        assert v["unlisted_files"] == []


def test_runs_are_mapped_to_library_versions_from_run_files_in_tmp(lib, tmp_path):
    """La relación corrida ↔ versión se lee de `config.library_version` de cada JSON de corrida; aquí con archivos sintéticos."""
    v1, v2 = _make_version(lib, 1), _make_version(lib, 2)
    res = tmp_path / "results"
    res.mkdir()
    (res / "adaptation_swarm_corrida-poc-1.json").write_text(json.dumps({"config": {"library_version": v1}}))
    (res / "adaptation_swarm_corrida-poc-2.json").write_text(json.dumps({"config": {"library_version": v2}}))
    (res / "adaptation_swarm_corrida-poc-x.json").write_text("no es json")           # nombre fuera del patrón: se ignora sin leerlo
    assert inv_mod.runs_by_library_version(res) == {v1: ["corrida-poc-1"], v2: ["corrida-poc-2"]}
    inv = inv_mod.inventory(lib, results_dir=res)
    assert inv["runs"] == {"corrida-poc-1": v1, "corrida-poc-2": v2}
    assert [v["used_by_runs"] for v in inv["versions"]] == [["corrida-poc-1"], ["corrida-poc-2"]]
    assert inv_mod.inventory(lib, results_dir=None)["runs"] == {} and inv_mod.runs_by_library_version(tmp_path / "no_existe") == {}


_FROZEN_RUNS = [inv_mod.DEFAULT_RESULTS / f"adaptation_swarm_corrida-poc-{n}.json" for n in (1, 2)]


@pytest.mark.skipif(not all(p.is_file() for p in _FROZEN_RUNS),
                    reason="resultados congelados (corrida-poc-1/2) ausentes: la biblioteca no depende de ellos; se omite sin ocultar fallos")
def test_frozen_runs_map_to_their_library_versions_when_results_are_present():
    inv = inv_mod.inventory(SETTINGS.library_root, verify_hashes=False)
    assert inv["runs"] == {"corrida-poc-1": "lib-v5-9ae9ffdd", "corrida-poc-2": "lib-v9-a0231e9b"}


def _check_exit_code(monkeypatch, lib, *flags) -> int:
    monkeypatch.setattr("sys.argv", ["library_inventory", "--root", str(lib), "--check", *flags])
    with pytest.raises(SystemExit) as exc:
        inv_mod.main()
    return exc.value.code


def test_cli_check_exit_codes_for_complete_absent_audio_and_wrong_hash(lib, monkeypatch, capsys):
    ver = _make_version(lib, 1)
    assert _check_exit_code(monkeypatch, lib) == 0 and _check_exit_code(monkeypatch, lib, "--require-complete") == 0     # biblioteca completa
    mp3 = lib / ver / "artifacts" / CONCEPT / "audio_t0a0.mp3"
    mp3.unlink()
    assert _check_exit_code(monkeypatch, lib) == 0                                       # audio ausente: no es un hash incorrecto
    assert _check_exit_code(monkeypatch, lib, "--require-complete") == 1                 # …pero sí incumple «completa»
    mp3.write_bytes(b"corrupto")
    assert _check_exit_code(monkeypatch, lib) == 1 and _check_exit_code(monkeypatch, lib, "--require-complete") == 1    # hash incorrecto
    capsys.readouterr()


def _library_module_names() -> list[str]:
    tools = sorted(p.stem for p in Path(inv_mod.__file__).parent.glob("*.py") if p.stem != "__init__")
    return [f"adaptation_swarm.tools.{n}" for n in tools] + [f"adaptation_swarm.multimodal.{n}" for n in ("builder", "extend", "verify")]


@pytest.mark.parametrize("name", _library_module_names())
def test_library_modules_execute_nothing_when_imported(name):
    """Importar el tooling de biblioteca no abre conexiones ni escribe: en el nivel superior solo hay imports, asignaciones,
    definiciones y el bloque `__main__`. Se comprueba el AST ANTES de importar, para no ejecutar un módulo que actúe al importarse."""
    origin = Path(importlib.util.find_spec(name).origin)
    for node in ast.parse(origin.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):         # docstring
            continue
        if isinstance(node, ast.If) and "__name__" in ast.dump(node.test):              # if __name__ == "__main__"
            continue
        assert isinstance(node, (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)), \
            f"{origin.name}:{node.lineno} ejecuta código al importarse ({type(node).__name__})"
    importlib.import_module(name)


def test_bootstrap_preconditions_touches_the_database_only_when_main_runs(monkeypatch, capsys):
    from adaptation_swarm.tools import bootstrap_preconditions as bp

    class _Session:
        def __init__(self):
            self.statements, self.commits = [], 0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, stmt, params=None):
            self.statements.append(str(stmt))

        def commit(self):
            self.commits += 1

    session = _Session()
    monkeypatch.setattr(bp, "SessionLocal", lambda: session)
    assert session.statements == [] and session.commits == 0                  # importar no ejecutó nada
    bp.main()
    assert len(session.statements) == 1 + len(bp.LEGACY) and session.commits == 1
    assert "IS301" in session.statements[0] and all("on conflict do nothing" in s for s in session.statements)
    capsys.readouterr()


def test_verify_reports_missing_files_separately_from_hash_mismatches(tmp_path, monkeypatch):
    """`multimodal.verify` sobre una copia de symlinks de v10 SIN mp3: archivos ausentes ≠ hashes incorrectos."""
    from types import SimpleNamespace

    from adaptation_swarm.multimodal import verify as verify_mod
    src = next(SETTINGS.library_root.glob("lib-v10-*"))
    dst = tmp_path / src.name
    dst.mkdir()
    (dst / "manifest.json").symlink_to(src / "manifest.json")
    for e in json.loads((src / "manifest.json").read_text())["entries"]:
        if e["modality"] == "audio":
            continue
        t = dst / e["path"]
        t.parent.mkdir(parents=True, exist_ok=True)
        if not t.exists():
            t.symlink_to(src / e["path"])
    monkeypatch.setattr(verify_mod, "SETTINGS", SimpleNamespace(library_root=tmp_path))
    r = verify_mod.verify(src.name)
    assert r["sha256_mismatches"] == [] and len(r["missing_files"]) == 270 and all(p.endswith(".mp3") for p in r["missing_files"])


# ── copia sellada del audio ────────────────────────────────────────────────────────────────────────────────────────
def test_seal_audio_is_an_independent_additive_copy_and_verifiable(lib, tmp_path):
    from adaptation_swarm.tools import seal_audio
    ver = _make_version(lib, 1)
    before = {p.relative_to(lib).as_posix(): (p.stat().st_ino, _sha(p.read_bytes())) for p in lib.rglob("*") if p.is_file()}
    dest = tmp_path / "sellada"
    r = seal_audio.seal(dest, root=lib)
    assert r["mp3"] == 2 and r["versions"] == [ver]
    assert {p.relative_to(lib).as_posix(): (p.stat().st_ino, _sha(p.read_bytes())) for p in lib.rglob("*") if p.is_file()} == before   # originales intactos
    for mp3 in (dest / ver).rglob("*.mp3"):
        original = lib / ver / mp3.relative_to(dest / ver)
        assert mp3.stat().st_ino != original.stat().st_ino and mp3.read_bytes() == original.read_bytes() and not os.access(mp3, os.W_OK)
    assert (dest / "SHA256SUMS").is_file() and (dest / "README-SEALED.md").read_text().count("NO constituye todavía almacenamiento externo") == 1
    assert seal_audio.verify_sealed(dest) == {"listed": r["files"] - 1, "missing": [], "hash_mismatch": [], "manifest_missing": [],
                                              "manifest_hash_mismatch": [], "ok": True}
    with pytest.raises(SystemExit):
        seal_audio.seal(dest, root=lib)                                                                  # no sobrescribe


def test_seal_audio_refuses_incomplete_or_tampered_audio_and_repo_destinations(lib, tmp_path):
    from adaptation_swarm.tools import seal_audio
    ver = _make_version(lib, 1)
    with pytest.raises(SystemExit, match="FUERA"):
        seal_audio.seal(seal_audio.REPO / "no_debe_crearse", root=lib)
    assert not (seal_audio.REPO / "no_debe_crearse").exists()
    (lib / ver / "artifacts" / CONCEPT / "audio_t0a0.mp3").write_bytes(b"corrupto")
    with pytest.raises(SystemExit, match="hash_incorrecto"):
        seal_audio.seal(tmp_path / "s1", root=lib)
    (lib / ver / "artifacts" / CONCEPT / "audio_t0a0.mp3").unlink()
    with pytest.raises(SystemExit, match="parcial"):
        seal_audio.seal(tmp_path / "s2", root=lib)
    assert not (tmp_path / "s1").exists() and not (tmp_path / "s2").exists()


def test_verify_sealed_separates_missing_from_mismatch(lib, tmp_path):
    from adaptation_swarm.tools import seal_audio
    _make_version(lib, 1)
    dest = tmp_path / "sellada"
    seal_audio.seal(dest, root=lib)
    a, b = sorted(dest.rglob("*.mp3"))
    a.chmod(0o644); a.write_bytes(b"alterado")
    b.chmod(0o644); b.unlink()
    r = seal_audio.verify_sealed(dest)
    assert r["ok"] is False and len(r["hash_mismatch"]) == 1 and len(r["missing"]) == 1
    assert len(r["manifest_hash_mismatch"]) == 1 and len(r["manifest_missing"]) == 1
