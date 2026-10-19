"""Pruebas del paquete de reproducibilidad. Ejecutar desde `reproducibility/`:  python -m pytest tests -q
Las pruebas que mutan datos trabajan sobre una copia temporal; nunca tocan la evidencia publicada."""
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from repro_lib import compare, parse_num  # noqa: E402


def run(script, root=ROOT):
    return subprocess.run([sys.executable, str(root / "scripts" / script)], cwd=root / "scripts", capture_output=True, text=True, encoding="utf-8", errors="replace")


@pytest.fixture()
def copia(tmp_path):
    dst = tmp_path / "reproducibility"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("__pycache__", "outputs", ".pytest_cache"))
    return dst


# ---- integridad
def test_hashes_del_manifiesto_coinciden():
    r = run("verify_hashes.py")
    assert r.returncode == 0, r.stdout + r.stderr


def test_archivo_alterado_es_error_de_integridad(copia):
    f = copia / "data/experiments/oe_n2_2026-10-05/campaign/runs.csv"
    f.write_bytes(f.read_bytes() + b" ")
    r = run("verify_hashes.py", copia)
    assert r.returncode == 2 and "ERROR_INTEGRIDAD" in r.stdout


def test_archivo_faltante_es_error_de_integridad(copia):
    (copia / "data/experiments/oe_n4_2026-10-06/campaign/runs.csv").unlink()
    assert run("verify_hashes.py", copia).returncode == 2


# ---- esquema y datos
def test_validacion_ok_y_exclusion_de_n11_declarada():
    assert run("validate_data.py").returncode == 0
    rep = json.loads((ROOT / "outputs/validation_report.json").read_text(encoding="utf-8"))
    assert rep["campanas"]["N11"]["filas"] == 180 and rep["campanas"]["N11"]["filas_ok"] == 179
    assert rep["campanas"]["N11"]["exclusiones"][0]["status"] == "no_requests"
    assert rep["campanas"]["N9b"]["filas"] == 160 and not rep["campanas"]["N9b"]["exclusiones"]


def _mutar_csv(copia, fn):
    p = copia / "data/experiments/oe_n2_2026-10-05/campaign/runs.csv"
    import pandas as pd
    d = pd.read_csv(p, low_memory=False)
    fn(d).to_csv(p, index=False)


def test_columna_obligatoria_ausente_es_error_de_esquema(copia):
    _mutar_csv(copia, lambda d: d.drop(columns=["p95_ms"]))
    assert run("validate_data.py", copia).returncode == 3


def test_run_id_duplicado_es_inconsistencia_de_datos(copia):
    import pandas as pd
    _mutar_csv(copia, lambda d: pd.concat([d, d.iloc[[0]]], ignore_index=True))
    assert run("validate_data.py", copia).returncode == 4


def test_valor_no_finito_se_detecta(copia):
    def f(d):
        d.loc[0, "p95_ms"] = float("inf")
        return d
    _mutar_csv(copia, f)
    assert run("validate_data.py", copia).returncode == 4


# ---- comparación numérica
def test_parse_cifras_del_informe():
    assert parse_num("1 401,4")[:2] == (1401.4, 1)
    assert parse_num("−56,7")[0] == -56.7
    v, dec, exp = parse_num("4,1 × 10⁻¹²")
    assert abs(v - 4.1e-12) < 1e-24 and exp == -12


@pytest.mark.parametrize("pub,rec,estado", [("119,9", 119.94, "COINCIDE"), ("119,9", 119.96, "DIFERENCIA_EXPLICABLE"), ("119,9", 121.0, "DISCREPANCIA"),
                                              ("4,1 × 10⁻¹²", 4.143e-12, "COINCIDE"), ("4,1 × 10⁻¹²", 5.0e-12, "DISCREPANCIA")])
def test_clasificacion_de_diferencias(pub, rec, estado):
    assert compare(pub, rec)["estado"] == estado


# ---- reproducción de cálculos deterministas y clasificación de pendientes
@pytest.fixture(scope="module")
def reproduccion():
    r = run("reproduce_results.py")
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((ROOT / "outputs/verification_report.json").read_text(encoding="utf-8"))


def test_scripts_del_proyecto_corren_y_derivados_son_byte_a_byte(reproduccion):
    assert all(v == 0 for v in reproduccion["scripts_del_proyecto_ejecutados"].values())
    assert {b["estado"] for b in reproduccion["derivados_byte_a_byte"]} == {"COINCIDE_BYTE_A_BYTE"}


def test_tabla_8_recalculada_desde_las_80_corridas(reproduccion):
    t8 = [c for c in reproduccion["comprobaciones"] if c["tabla"] == "Tabla 8"]
    assert len(t8) == 32 and all(c["estado"] == "COINCIDE" for c in t8)
    assert "80 corridas" in t8[0]["fuente_evidencia"]


def test_sin_discrepancias_y_pendientes_no_se_marcan_como_reproducidos(reproduccion):
    assert reproduccion["conteo_estados"].get("DISCREPANCIA", 0) == 0
    pend = [c for c in reproduccion["comprobaciones"] if c["id"].startswith("PEND-") or c["id"].endswith("k_stop")]
    assert pend and all(c["estado"] == "NO_REPRODUCIBLE" and c["motivo"] for c in pend)


def test_control_negativo_un_valor_publicado_alterado_es_discrepancia(copia):
    p = copia / "data/metadata/informe_D2.9.7_tablas.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    for t in d["tables"]:
        if t["caption_prev"].startswith("Tabla 8."):
            t["rows"][2][4] = "999,9"  # P95 de decision_table con 1 usuario... valor falso a propósito
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    r = run("reproduce_results.py", copia)
    assert r.returncode == 5, r.stdout + r.stderr


def test_n9_no_se_mezcla_con_n9b():
    with open(ROOT / "EVIDENCE_MANIFEST.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    n9 = [r for r in rows if r["campana"] == "N9"]
    assert n9 and all("ABORTADA" in r["estado_campana"] for r in n9)
    assert not any(r["rol"] == "dato_original" for r in n9)
    assert not any("oe_n9_2026" in c["fuente_evidencia"] for c in json.loads((ROOT / "outputs/verification_report.json").read_text(encoding="utf-8"))["comprobaciones"] if "fuente_evidencia" in c)
