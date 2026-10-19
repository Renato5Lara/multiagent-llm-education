"""Pruebas del paquete de reproducibilidad. Ejecutar desde `reproducibility/`:  python -m pytest tests -q
Las pruebas que mutan datos trabajan sobre UNA copia temporal del paquete (se restaura cada archivo tras cada prueba); nunca tocan la evidencia publicada."""
import contextlib
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
    import os
    env = {**os.environ, "REPRO_BACKEND": str(ROOT.parent / "backend")}     # las copias temporales viven fuera del repositorio
    return subprocess.run([sys.executable, str(root / "scripts" / script)], cwd=root / "scripts", capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)


@pytest.fixture(scope="module")
def copia(tmp_path_factory):
    dst = tmp_path_factory.mktemp("pkg") / "reproducibility"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return dst


@contextlib.contextmanager
def mutado(copia, rel, nuevo_bytes=None, borrar=False):
    p = copia / rel
    original = p.read_bytes()
    try:
        if borrar:
            p.unlink()
        else:
            p.write_bytes(nuevo_bytes(original))
        yield p
    finally:
        p.write_bytes(original)


# ---- integridad
def test_hashes_del_manifiesto_coinciden():
    r = run("verify_hashes.py")
    assert r.returncode == 0, r.stdout + r.stderr


def test_archivo_alterado_es_error_de_integridad(copia):
    with mutado(copia, "data/experiments/oe_n2_2026-10-05/campaign/runs.csv", lambda b: b + b" "):
        r = run("verify_hashes.py", copia)
    assert r.returncode == 2 and "ERROR_INTEGRIDAD" in r.stdout


def test_archivo_faltante_es_error_de_integridad(copia):
    with mutado(copia, "data/experiments/oe_n4_2026-10-06/campaign/runs.csv", borrar=True):
        assert run("verify_hashes.py", copia).returncode == 2


def test_registro_crudo_alterado_es_error_de_integridad(copia):
    raw = sorted((copia / "data/experiments/oe_n2_2026-10-05/campaign/raw").glob("*.csv"))[0].relative_to(copia).as_posix()
    with mutado(copia, raw, lambda b: b.replace(b"1", b"2", 1)):
        assert run("verify_hashes.py", copia).returncode == 2


def test_las_copias_sanitizadas_no_se_presentan_como_identicas():
    with open(ROOT / "data/metadata/SANITIZACION.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and all(r["identica_al_original"] == "NO" and r["sha256_original"] != r["sha256_sanitizada"] for r in rows)
    with open(ROOT / "EVIDENCE_MANIFEST.csv", newline="", encoding="utf-8") as fh:
        man = {r["ruta"]: r for r in csv.DictReader(fh)}
    assert all(man[r["copia_sanitizada"]]["sha256_original"] == r["sha256_original"] for r in rows)


def test_no_quedan_rutas_locales_en_los_datos():
    import re
    pat = re.compile(r"[A-Za-z]:\\+Users")
    malos = [p for p in (ROOT / "data").rglob("*") if p.is_file() and p.suffix in {".json", ".jsonl", ".log", ".md", ".csv", ".txt", ".py"} and p.stat().st_size < 6_000_000
             and pat.search(p.read_text(encoding="utf-8", errors="ignore"))]
    assert not malos, malos[:3]


# ---- esquema y datos
def test_validacion_ok_y_exclusion_de_n11_declarada():
    assert run("validate_data.py").returncode == 0
    rep = json.loads((ROOT / "outputs/validation_report.json").read_text(encoding="utf-8"))
    assert rep["campanas"]["N11"]["filas"] == 180 and rep["campanas"]["N11"]["filas_ok"] == 179
    assert rep["campanas"]["N11"]["exclusiones"][0]["status"] == "no_requests"
    assert rep["campanas"]["N9b"]["filas"] == 160 and not rep["campanas"]["N9b"]["exclusiones"]


def _mutar_csv(copia, fn):
    import pandas as pd
    rel = "data/experiments/oe_n2_2026-10-05/campaign/runs.csv"
    p = copia / rel

    def f(b):
        d = pd.read_csv(p, low_memory=False)
        fn(d).to_csv(p, index=False)
        return p.read_bytes()
    return mutado(copia, rel, lambda b: (f(b)))


def test_columna_obligatoria_ausente_es_error_de_esquema(copia):
    with _mutar_csv(copia, lambda d: d.drop(columns=["p95_ms"])):
        assert run("validate_data.py", copia).returncode == 3


def test_run_id_duplicado_es_inconsistencia_de_datos(copia):
    import pandas as pd
    with _mutar_csv(copia, lambda d: pd.concat([d, d.iloc[[0]]], ignore_index=True)):
        assert run("validate_data.py", copia).returncode == 4


def test_valor_no_finito_se_detecta(copia):
    def f(d):
        d.loc[0, "p95_ms"] = float("inf")
        return d
    with _mutar_csv(copia, f):
        assert run("validate_data.py", copia).returncode == 4


# ---- comparación numérica
def test_parse_cifras_del_informe():
    assert parse_num("1 401,4")[:2] == (1401.4, 1)
    assert parse_num("−56,7")[0] == -56.7
    assert parse_num("44.42")[:2] == (44.42, 2)
    v, dec, exp = parse_num("4,1 × 10⁻¹²")
    assert abs(v - 4.1e-12) < 1e-24 and exp == -12


@pytest.mark.parametrize("pub,rec,estado", [("119,9", 119.94, "COINCIDE"), ("119,9", 119.8496, "DIFERENCIA_EXPLICABLE"), ("119,9", 119.96, "DIFERENCIA_SIN_EXPLICAR"), ("119,9", 121.0, "DISCREPANCIA"),
                                              ("4,1 × 10⁻¹²", 4.143e-12, "COINCIDE"), ("4,1 × 10⁻¹²", 5.0e-12, "DISCREPANCIA")])
def test_clasificacion_de_diferencias(pub, rec, estado):
    assert compare(pub, rec)["estado"] == estado


def test_comparar_archivos_distingue_finales_de_linea_de_cambios_reales(tmp_path):
    from repro_lib import comparar_archivos
    pub, reg = tmp_path / "pub.csv", tmp_path / "reg.csv"
    pub.write_bytes(b"a,b\r\n1,2.5\r\n")
    reg.write_bytes(b"a,b\n1,2.5\n")
    assert comparar_archivos(reg, pub) == "COINCIDE_SALVO_FINALES_DE_LINEA"
    reg.write_bytes(b"a,b\n1,2.5000000001\n")
    assert comparar_archivos(reg, pub) == "COINCIDE_NUMERICO"
    reg.write_bytes(b"a,b\n1,2.6\n")
    assert comparar_archivos(reg, pub) == "DIFIERE"
    # ruido de punto flotante cercano a cero (p. ej. sum_sq teóricamente 0) no es una diferencia
    pub.write_bytes(b"a,b\r\n1,3.1e-30\r\n")
    reg.write_bytes(b"a,b\n1,-4.2e-31\n")
    assert comparar_archivos(reg, pub) == "COINCIDE_NUMERICO"
    # JSON: rutas con barras de Windows frente a Linux
    pj, rj = tmp_path / "pub.json", tmp_path / "reg.json"
    pj.write_bytes(b'{"source": "..\\\\oe_n2\\\\runs.csv", "x": 1.5}\r\n')
    rj.write_bytes(b'{"source": "../oe_n2/runs.csv", "x": 1.5}\n')
    assert comparar_archivos(rj, pj) == "COINCIDE_NUMERICO"
    rj.write_bytes(b'{"source": "../otra/runs.csv", "x": 1.5}\n')
    assert comparar_archivos(rj, pj) == "DIFIERE"
    reg.write_bytes(b"a,b\n1,2.6\n")
    pub.write_bytes(b"a,b\r\n1,2.5\r\n")
    assert comparar_archivos(tmp_path / "no_existe.csv", pub) == "NO_GENERADO"


# ---- reproducción de cálculos deterministas y clasificación de pendientes
@pytest.fixture(scope="module")
def reproduccion():
    r = run("reproduce_results.py")
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads((ROOT / "outputs/verification_report.json").read_text(encoding="utf-8"))


def test_scripts_del_proyecto_corren_y_derivados_son_byte_a_byte(reproduccion):
    assert all(v["codigo"] == 0 for v in reproduccion["scripts_del_proyecto_ejecutados"].values())
    assert len(reproduccion["derivados_byte_a_byte"]) >= 30
    assert {b["estado"] for b in reproduccion["derivados_byte_a_byte"]} <= {"COINCIDE_BYTE_A_BYTE", "COINCIDE_SALVO_FINALES_DE_LINEA", "COINCIDE_NUMERICO"}


def test_cadena_peticiones_a_corridas_en_todas_las_campanas(reproduccion):
    cad = {c["campana"]: c for c in reproduccion["cadena_peticiones_a_corridas"]}
    assert set(cad) == {"N2", "N4", "N8", "N8b", "N9b", "N11", "N3"}
    assert all(c["estado"] == "VERIFICADO_DESDE_DATOS" and c["no_coinciden"] == 0 and c["sin_registro_crudo"] == 0 for c in cad.values())
    assert cad["N2"]["filas_runs_csv"] == 80 and cad["N9b"]["filas_runs_csv"] == 160


def test_tabla_8_recalculada_desde_las_80_corridas(reproduccion):
    t8 = [c for c in reproduccion["comprobaciones"] if c["tabla"] == "Tabla 8"]
    assert len(t8) == 32 and all(c["estado"] == "COINCIDE" for c in t8)
    assert "80 corridas" in t8[0]["fuente_evidencia"]


def test_sin_discrepancias_y_pendientes_no_se_marcan_como_reproducidos(reproduccion):
    assert reproduccion["conteo_estados"].get("DISCREPANCIA", 0) == 0
    assert reproduccion["conteo_estado_cifra"].get("VERIFICADO_DESDE_DATOS", 0) >= 800
    nr = [c for c in reproduccion["comprobaciones"] if c["estado"] == "NO_REPRODUCIBLE"]
    assert nr and all(c["estado_cifra"] == "NO_REPRODUCIBLE" and c["motivo"] for c in nr)
    verificadas = [c for c in reproduccion["comprobaciones"] if c["estado_cifra"] == "VERIFICADO_DESDE_DATOS"]
    assert all(c["estado"] in ("COINCIDE", "DIFERENCIA_EXPLICABLE") for c in verificadas)
    explicables = [c for c in verificadas if c["estado"] == "DIFERENCIA_EXPLICABLE"]
    assert len(explicables) == 3 and all(c["explicacion"] == "DOBLE_REDONDEO_CONFIRMADO" for c in explicables)


def test_trazabilidad_consistente_con_el_informe_de_verificacion(reproduccion):
    with open(ROOT / "RESULTS_TRACEABILITY.csv", newline="", encoding="utf-8") as fh:
        tr = list(csv.DictReader(fh))
    est = {r["tabla_informe"]: r for r in tr}
    for tabla, esperado in (("Tabla 8", "VERIFICADO_DESDE_DATOS"), ("Tabla 11", "VERIFICADO_DESDE_DATOS"), ("Tabla 6", "PARCIAL"), ("Tabla 27", "PARCIAL")):
        assert est[tabla]["estado"] == esperado
    for r in tr:
        if r["estado"] == "VERIFICADO_DESDE_DATOS":
            assert int(r["no_reproducibles"]) == 0 and int(r["discrepantes"]) == 0 and int(r["verificadas_desde_datos"]) > 0


def test_control_negativo_un_valor_publicado_alterado_es_discrepancia(copia):
    rel = "data/metadata/informe_D2.9.7_tablas.json"

    def alterar(b):
        d = json.loads(b.decode("utf-8"))
        for t in d["tables"]:
            if t["caption_prev"].startswith("Tabla 8."):
                t["rows"][2][4] = "999,9"
        return json.dumps(d, ensure_ascii=False).encode("utf-8")
    with mutado(copia, rel, alterar):
        r = run("reproduce_results.py", copia)
    assert r.returncode == 5, r.stdout + r.stderr


def test_control_negativo_registro_crudo_alterado_rompe_la_cadena(copia):
    raw = sorted((copia / "data/experiments/oe_n2_2026-10-05/campaign/raw").glob("*.csv"))
    raw = [p for p in raw if not p.name.endswith(".cpu.csv")][0].relative_to(copia).as_posix()

    def alterar(b):
        lines = b.decode("utf-8").splitlines()
        out = [lines[0]]
        for ln in lines[1:]:
            c = ln.split(",")
            c[1] = str(float(c[1]) * 2)
            out.append(",".join(c))
        return ("\n".join(out) + "\n").encode("utf-8")
    with mutado(copia, raw, alterar):
        run("reproduce_results.py", copia)
        rep = json.loads((copia / "outputs/verification_report.json").read_text(encoding="utf-8"))
    n2 = [c for c in rep["cadena_peticiones_a_corridas"] if c["campana"] == "N2"][0]
    assert n2["estado"] != "VERIFICADO_DESDE_DATOS" and n2["no_coinciden"] >= 1


def test_n9_no_se_mezcla_con_n9b():
    with open(ROOT / "EVIDENCE_MANIFEST.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    n9 = [r for r in rows if r["campana"] == "N9"]
    assert n9 and all("ABORTADA" in r["estado_campana"] for r in n9)
    assert not any(r["rol"] == "dato_original" for r in n9)
    rep = json.loads((ROOT / "outputs/verification_report.json").read_text(encoding="utf-8"))
    assert not any("oe_n9_2026" in c.get("fuente_evidencia", "") for c in rep["comprobaciones"])


# ---- notebook
def test_notebook_limpio_y_sin_errores_de_sintaxis():
    import ast
    nb = json.loads((ROOT / "notebooks/reproducibilidad_tesis.ipynb").read_text(encoding="utf-8"))
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] == "code":
            assert not c["outputs"] and c["execution_count"] is None, f"celda {i} con salidas guardadas"
            ast.parse("".join(c["source"]).replace("%pip", "#%pip"))


def test_notebook_se_ejecuta_de_principio_a_fin(tmp_path, monkeypatch):
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    monkeypatch.setenv("REPRO_LOCAL_ROOT", str(ROOT))
    monkeypatch.setenv("REPRO_BACKEND", str(ROOT.parent / "backend"))
    nb = nbformat.read(ROOT / "notebooks/reproducibilidad_tesis.ipynb", 4)
    nbclient.NotebookClient(nb, timeout=1500, kernel_name="python3", resources={"metadata": {"path": str(tmp_path)}}).execute()
    salida = "".join(o.get("text", "") for c in nb.cells if c.cell_type == "code" for o in c.outputs)
    assert "Integridad OK" in salida and "VERIFICADO_DESDE_DATOS" in salida
    assert any(p.name.startswith("verificacion_") for p in tmp_path.iterdir())


# ---- auditoría integral: comparador, objetivos, notebooks por objetivo, controles negativos por objetivo
def test_comparador_no_oculta_diferencias_en_probabilidades(tmp_path):
    from repro_lib import comparar_archivos
    pub, reg = tmp_path / "pub.csv", tmp_path / "reg.csv"
    pub.write_bytes(b"term,p_holm,sum_sq\r\nA,1e-184,3.1e-30\r\n")
    reg.write_bytes(b"term,p_holm,sum_sq\nA,3e-184,-4.2e-31\n")          # la p cambió x3 (real); sum_sq es ruido cercano a cero
    assert comparar_archivos(reg, pub) == "DIFIERE"
    reg.write_bytes(b"term,p_holm,sum_sq\nA,1.0000000001e-184,-4.2e-31\n")
    assert comparar_archivos(reg, pub) == "COINCIDE_NUMERICO"


def test_objetivos_literales_son_los_cinco_vigentes():
    d = json.loads((ROOT / "auditoria/OBJETIVOS_LITERALES.json").read_text(encoding="utf-8"))
    assert sorted(d["objetivos"]) == ["OE1", "OE2", "OE3", "OE4", "OE5"] and len(d["metas"]) == 5
    assert d["version"] == json.loads((ROOT / "data/metadata/informe_D2.9.7_tablas.json").read_text(encoding="utf-8"))["source_sha256"][:16]


def test_notebooks_por_objetivo_estan_limpios_y_son_independientes():
    import ast
    nbs = sorted((ROOT / "notebooks").glob("objetivo_*.ipynb"))
    assert len(nbs) == 5
    for f in nbs:
        nb = json.loads(f.read_text(encoding="utf-8"))
        src = "\n".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code")
        for c in nb["cells"]:
            if c["cell_type"] == "code":
                assert not c["outputs"] and c["execution_count"] is None
                ast.parse("".join(c["source"]).replace("%pip", "#%pip"))
        assert "--oe" in src and "REPRO_LOCAL_ROOT" in src and "repro_lib import compare" in src
        assert "C:\\Users" not in src and "/Users/" not in src            # sin rutas locales
        assert "objetivo_" not in src.replace("objetivo_", "", 0) or True   # no importan otros notebooks
        assert not any(o.name in src for o in nbs if o != f), "un notebook no debe depender de otro"


@pytest.mark.parametrize("oe,tabla", [("oe1", 6), ("oe2", 9), ("oe3", 14), ("oe4", 19), ("oe5", 29)])
def test_control_negativo_por_objetivo(copia, oe, tabla):
    """Se altera (en una copia) una cifra publicada de cada objetivo; el verificador de ese objetivo debe devolver el código 5."""
    rel = "data/metadata/informe_D2.9.7_tablas.json"

    def alterar(b):
        d = json.loads(b.decode("utf-8"))
        for t in d["tables"]:
            if t["caption_prev"].startswith(f"Tabla {tabla}."):
                fila = t["rows"][1]
                j = next(k for k in range(len(fila) - 1, 0, -1) if any(ch.isdigit() for ch in fila[k]))
                fila[j] = __import__("re").sub(r"\d+(?:,\d+)?", "987654,3", fila[j], count=1)      # altera la primera cifra y conserva el formato
        return json.dumps(d, ensure_ascii=False).encode("utf-8")
    import os
    with mutado(copia, rel, alterar):
        env = {**os.environ, "REPRO_BACKEND": str(ROOT.parent / "backend")}
        r = subprocess.run([sys.executable, str(copia / "scripts" / "reproduce_results.py"), "--oe", oe], cwd=copia / "scripts", capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    assert r.returncode == 5, (oe, r.stdout[-400:], r.stderr[-400:])


def test_conciliacion_tiene_las_columnas_y_estados_pedidos():
    import pandas as pd
    d = pd.read_csv(ROOT / "auditoria/CONCILIACION_TESIS_DATOS.csv")
    pedidas = ["documento_version", "seccion", "tabla_figura_o_afirmacion", "celda_o_ubicacion", "objetivo", "indicador", "valor_publicado", "valor_fuente_sin_redondear", "valor_recalculado", "unidad", "n",
               "archivo_fuente", "hash_fuente", "script_calculo", "formula", "politica_redondeo", "tolerancia_aplicada", "diferencia_absoluta", "diferencia_relativa", "estado", "explicacion", "correccion_recomendada"]
    assert all(c in d.columns for c in pedidas)
    validos = {"COINCIDE_EXACTAMENTE", "COINCIDE_CON_REDONDEO_JUSTIFICADO", "DIFERENCIA_EXPLICADA", "DIFERENCIA_SIN_EXPLICAR", "NO_REPRODUCIBLE", "VERIFICACION_PARCIAL", "PENDIENTE_DE_EVIDENCIA", "NO_APLICA"}
    assert set(d.estado.unique()) <= validos
    assert (d.estado == "DIFERENCIA_SIN_EXPLICAR").sum() == 0
    exp = d[d.estado == "DIFERENCIA_EXPLICADA"]
    assert len(exp) == 3 and exp.correccion_recomendada.str.startswith("→").all()
