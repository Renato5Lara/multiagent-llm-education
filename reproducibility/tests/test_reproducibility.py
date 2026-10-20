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


# ---- OE3: réplica independiente N3-R
def test_oe3_replica_n3r_cadena_y_efectos():
    r = run("oe3_replicacion.py")
    assert r.returncode == 0, r.stderr[-800:]
    out = json.loads((ROOT / "outputs" / "oe3_replicacion.json").read_text(encoding="utf-8"))
    assert out["cadena_N3R"]["observaciones"] == 24000 and out["cadena_N3R"]["corridas_recalculadas"] == 240 and out["cadena_N3R"]["coincide"]
    assert out["efectos_que_replican"] == out["efectos_evaluados"] == 21 and not out["no_replican"]


def test_oe3_control_negativo_observacion_alterada_rompe_la_cadena_de_n3r(copia):
    import pandas as pd
    rel = "data/experiments/oe_n3r_2026-10-19/run/raw_observations.csv"

    def alterar(b):
        import io
        d = pd.read_csv(io.BytesIO(b), low_memory=False)
        d.loc[0, "t_conv_ms"] = d.loc[0, "t_conv_ms"] + 50.0
        return d.to_csv(index=False).encode("utf-8")

    with mutado(copia, rel, alterar):
        r = run("oe3_replicacion.py", copia)
        assert r.returncode == 0, r.stderr[-800:]
        out = json.loads((copia / "outputs" / "oe3_replicacion.json").read_text(encoding="utf-8"))
        assert out["cadena_N3R"]["coincide"] is False


def test_todo_archivo_del_manifiesto_esta_versionado_en_git():
    """Un archivo ignorado por .gitignore (p. ej. logs/) existe en local pero faltaría en el clon de Colab."""
    r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        pytest.skip("sin repositorio git")
    tracked = set(r.stdout.split("\n"))
    with open(ROOT / "EVIDENCE_MANIFEST.csv", encoding="utf-8", newline="") as fh:
        faltan = [row["ruta"] for row in csv.DictReader(fh) if row["ruta"] not in tracked]
    assert not faltan, f"archivos del manifiesto sin versionar (¿.gitignore?): {faltan[:5]}"


# ---- OE3: control de sesión preregistrado (N3-S) y eficiencia con los indicadores de la tesis
def test_oe3_sesion_n3s_cadena_determinismo_y_veredicto_preregistrado():
    r = run("oe3_sesion.py")
    assert r.returncode == 0, r.stderr[-800:]
    out = json.loads((ROOT / "outputs" / "oe3_sesion.json").read_text(encoding="utf-8"))
    assert out["cadena_N3S"]["coincide"] and out["cadena_N3S"]["observaciones"] == 24000
    assert out["calidad_identica_con_mismas_semillas"] is True          # mismas semillas ⇒ brecha, k_stop, mensajes y F idénticos a N3
    assert out["veredicto_preregistrado"].startswith("H_sesión")        # intervalo [0,79; 0,89] fijado antes de ejecutar
    assert 0.79 <= out["cociente_N3S_sobre_N3"]["valor"] <= 0.89


def test_oe3_eficiencia_indicadores_de_la_tesis_y_veredictos_consistentes():
    r = run("oe3_eficiencia.py")
    assert r.returncode == 0, r.stderr[-800:]
    out = json.loads((ROOT / "outputs" / "oe3_eficiencia.json").read_text(encoding="utf-8"))
    assert all(c["CR"] >= 0.98 and c["k_stop_max"] <= 15 for c in out["convergencia"])
    assert out["contrastes_con_veredicto_igual_en_las_3_campanas"] == out["contrastes"] == 6


def test_oe3_control_negativo_semillas_cambiadas_no_dan_calidad_identica(copia):
    import pandas as pd
    rel = "data/experiments/oe_n3s_2026-10-19/runs_oe3.csv"

    def alterar(b):
        import io
        d = pd.read_csv(io.BytesIO(b))
        d.loc[0, "gap_vs_optimum"] = d.loc[0, "gap_vs_optimum"] + 0.01
        return d.to_csv(index=False).encode("utf-8")

    with mutado(copia, rel, alterar):
        r = run("oe3_sesion.py", copia)
        assert r.returncode == 0, r.stderr[-800:]
        out = json.loads((copia / "outputs" / "oe3_sesion.json").read_text(encoding="utf-8"))
        assert out["calidad_identica_con_mismas_semillas"] is False and out["cadena_N3S"]["coincide"] is False


def test_tabla6_usuarios_y_tabla27_por_perfil_se_recalculan():
    r = run("reproduce_results.py")
    assert r.returncode == 0, r.stderr[-800:]
    ver = json.loads((ROOT / "outputs" / "verification_report.json").read_text(encoding="utf-8"))
    ids = {c["id"]: c["estado"] for c in ver["comprobaciones"]}
    for i in ("T6-usuarios-rho", "T6-usuarios-rho_p", "T27-perfil-media", "T27-perfil-mediana", "T27-perfil-sd", "T27-perfil-min", "T27-perfil-max"):
        assert ids.get(i) == "COINCIDE", (i, ids.get(i))


def test_estados_de_requisitos_de_la_tabla_37_se_recalculan_y_detectan_alteraciones(copia):
    import io
    import pandas as pd
    r = run("reproduce_results.py")
    assert r.returncode == 0, r.stderr[-800:]
    ver = json.loads((ROOT / "outputs" / "verification_report.json").read_text(encoding="utf-8"))
    est = {c["id"]: c["estado"] for c in ver["comprobaciones"] if c["id"].startswith("T37-")}
    for rid in ("RF01", "RF02", "RF03", "RF04", "RF05", "REL-C", "RNF01", "RNF02", "RNF03", "RNF04"):
        assert est[f"T37-{rid}-valor"] == "COINCIDE" and est[f"T37-{rid}-estado"] == "COINCIDE", rid
    assert all(est[f"T37-{k}"] == "NO_REPRODUCIBLE" for k in ("RF06", "REL-D", "RNF05"))

    def alterar(b):
        d = pd.read_csv(io.BytesIO(b), low_memory=False)
        d.loc[d.index[:3000], "w_valid"] = False                 # RF02 pasaría de 100 % a < 100 %: el estado MET ya no se sostiene
        return d.to_csv(index=False).encode("utf-8")

    with mutado(copia, "data/experiments/oe_n1_2026-10-05/oe3_run/raw_observations.csv", alterar):
        r2 = run("reproduce_results.py", copia)
        assert r2.returncode == 5, (r2.returncode, r2.stderr[-400:])   # 5 = hay discrepancia


# ---- reconciliaciones estadísticas (usuarios: Spearman frente a Kendall; despacho: 37 % frente a 32 %)
def test_ficha_usuarios_spearman_y_kendall_son_la_misma_pregunta_con_estadisticos_distintos():
    r = run("oe1_usuarios_ficha.py")
    assert r.returncode == 0, r.stderr[-800:]
    f = json.loads((ROOT / "outputs" / "oe1_usuarios_ficha.json").read_text(encoding="utf-8"))
    assert f["n_condiciones"] == 14
    assert abs(f["spearman"]["rho"] - (-0.6084)) < 5e-4 and abs(f["spearman"]["p"] - 0.0210) < 5e-4
    assert abs(f["kendall_tau_b"]["tau"] - (-0.5062)) < 5e-4 and abs(f["kendall_tau_b"]["p"] - 0.0428) < 5e-4
    assert f["medida_publicada_en_tabla_6"]["coincide_spearman_con_oe1_verify"] is True
    assert f["medida_publicada_en_tabla_6"]["kendall_publicado"] == "no calculado"


def test_efecto_del_despacho_misma_definicion_direccion_estable_y_magnitud_dependiente_de_la_sesion():
    r = run("oe3_despacho.py")
    assert r.returncode == 0, r.stderr[-800:]
    d = json.loads((ROOT / "outputs" / "oe3_despacho.json").read_text(encoding="utf-8"))
    for c in ("N3", "N3R", "N3S"):
        assert d[c]["pares_con_secuencial_mas_lento_pct"] == 100.0           # dirección estable en todos los pares
        assert abs(d[c]["reduccion_por_lotes_pct"] - 100 * (1 - 1 / d[c]["R_media_geometrica"])) < 1e-9   # una sola definición
    assert abs(d["N3"]["reduccion_por_lotes_pct"] - 37.4) < 0.1 and abs(d["N3R"]["reduccion_por_lotes_pct"] - 32.2) < 0.1 and abs(d["N3S"]["reduccion_por_lotes_pct"] - 32.5) < 0.1
    assert d["sesion_N3S_frente_a_N3"]["lotes_con_razon_menor_en_N3S"] == 5


def test_registro_de_afirmaciones_prioritarias_es_consistente():
    with open(ROOT / "auditoria" / "REGISTRO_AFIRMACIONES_PRIORITARIAS.csv", encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    ids = [f["id"] for f in filas]
    assert len(ids) == len(set(ids)) and len(ids) >= 156                        # identificadores estables y sin duplicados
    validos = {"COINCIDE_EXACTAMENTE", "COINCIDE_CON_REDONDEO", "DISCREPANCIA", "NO_REPRODUCIBLE", "PENDIENTE_DE_REVISION", "NO_APLICA"}
    assert all(f["estado"] in validos for f in filas)
    assert all(f["fuente_y_metodo"].strip() and f["texto_minimo"].strip() for f in filas)
    assert all(f["limitacion"].strip() for f in filas if f["estado"] != "COINCIDE_EXACTAMENTE")   # toda no-exacta declara su limitación
    with open(ROOT / "auditoria" / "EFECTO_DESPACHO_MENCIONES.csv", encoding="utf-8", newline="") as fh:
        m = list(csv.DictReader(fh))
    assert len(m) == 10 and all("N3-R" in r["efecto_por_campana"] and "N3-S" in r["efecto_por_campana"] for r in m)


def test_medias_aritmeticas_frente_a_geometricas_explican_la_diferencia_de_la_seccion_6_5_5():
    r = run("oe3_medias_aritmeticas_vs_geometricas.py")
    assert r.returncode == 0, r.stderr[-800:]
    d = json.loads((ROOT / "outputs" / "oe3_medias.json").read_text(encoding="utf-8"))
    assert d["medias_del_reanalisis_son_aritmeticas"] is True
    assert d["niveles"] == 11 and d["niveles_que_superan_1_3_pct"] == 10 and 3.7 < d["maximo_dif_rel_sin_redondear_pct"] < 3.9
    desp = {r_["nivel"]: r_["dif_rel_sin_redondear_pct"] for r_ in d["despacho"]}
    assert abs(desp["despacho por lotes"] - 1.388) < 0.01 and abs(desp["despacho secuencial"] - 0.587) < 0.01


def test_cambios_de_la_copia_de_revision_son_exactos_y_estan_justificados():
    with open(ROOT / "auditoria" / "REGISTRO_CAMBIOS_REVISION_FACTUAL.csv", encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    assert len(filas) == 12 and len({f["id_cambio"] for f in filas}) == 12
    for f in filas:
        assert f["texto_original_exacto"] != f["texto_corregido_exacto"] and f["evidencia"].strip()
    assert {f["propuesta"] for f in filas} == {"C3", "C6", "C7", "C8", "C9", "C11", "C12"}       # solo correcciones factuales (clase A)
    clas = (ROOT / "auditoria" / "CLASIFICACION_CORRECCIONES.md").read_text(encoding="utf-8")
    for c in ("C1", "C2", "C4", "C5", "C10"):
        assert f"| {c} |" in clas and "no aplicada" in clas


def test_estado_de_los_notebooks_coincide_con_los_archivos_actuales():
    """El registro de ejecución de Colab no puede quedar desfasado respecto de los notebooks ni de sus entradas."""
    import hashlib
    with open(ROOT / "auditoria" / "ESTADO_NOTEBOOKS_COLAB.csv", encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    assert len(filas) == 6
    for f in filas:
        assert f["commit_completo_ejecutado"].startswith(f["commit_ejecutado"]) and len(f["commit_completo_ejecutado"]) == 40
        actual = hashlib.sha256((ROOT / "notebooks" / f["notebook"]).read_bytes()).hexdigest()
        assert f["sha256_notebook_actual"] == actual, f["notebook"]            # si cambia un notebook, hay que reejecutar y reregistrar
        assert f["nivel_certeza"].startswith("PARCIAL") and f["commit_ejecutado_anterior_registrado"]
    with open(ROOT / "auditoria" / "MATRIZ_CAMBIOS_POSTERIORES.csv", encoding="utf-8", newline="") as fh:
        m = list(csv.DictReader(fh))
    assert m and all(r["consumido_por_notebooks"] == "NO" and r["requiere_reejecucion"] == "NO" for r in m)


def test_los_scripts_de_los_notebooks_no_leen_la_carpeta_de_auditoria():
    for s in ("verify_hashes", "validate_data", "reproduce_results", "repro_lib", "oe3_robustez", "oe3_replicacion", "oe3_sesion", "oe3_eficiencia"):
        codigo = (ROOT / "scripts" / f"{s}.py").read_text(encoding="utf-8")
        for patron in ('/ "auditoria"', "/ 'auditoria'", 'Path("auditoria', "Path('auditoria"):
            assert patron not in codigo, (s, patron)


def test_cambios_v2_de_la_copia_de_revision_son_exactos_y_estan_justificados():
    with open(ROOT / "auditoria" / "REGISTRO_CAMBIOS_REVISION_FACTUAL_V2.csv", encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    assert len(filas) == 13 and [f["id_cambio"] for f in filas] == [f"R{i}" for i in range(13, 26)]
    for f in filas:
        assert f["texto_original_exacto"] != f["texto_corregido_exacto"] and f["evidencia"].strip()
    assert {f["propuesta"] for f in filas} == {f"C{i}" for i in range(13, 22)}       # solo correcciones factuales (clase A)
    clas = (ROOT / "auditoria" / "CLASIFICACION_CORRECCIONES.md").read_text(encoding="utf-8")
    for c in ("C1", "C2", "C4", "C5", "C10", "C22", "C23", "C24"):
        assert f"| {c} |" in clas
    assert all("no aplicada" in l for l in clas.splitlines() if l.startswith(("| C22 |", "| C23 |", "| C24 |")))


def test_matriz_de_evidencia_de_las_conclusiones():
    import re
    with open(ROOT / "auditoria" / "REGISTRO_AFIRMACIONES_PRIORITARIAS.csv", encoding="utf-8", newline="") as fh:
        ids = {r["id"] for r in csv.DictReader(fh)}
    with open(ROOT / "auditoria" / "MATRIZ_EVIDENCIA_CONCLUSIONES.csv", encoding="utf-8", newline="") as fh:
        m = list(csv.DictReader(fh))
    assert {r["objetivo"] for r in m} == {"GENERAL", "OE1", "OE2", "OE3", "OE4", "OE5", "RESUMEN"}
    assert len({r["id"] for r in m}) == len(m) >= 40
    for r in m:
        assert r["respaldo"] in {"RESPALDADA", "PARCIAL", "NO_RESPALDADA", "NO_VERIFICABLE"}
        assert r["tipo"] in {"OBSERVADO", "META", "HIPOTESIS", "INTERPRETACION", "ALCANCE"}
        assert set(re.findall(r"A\d+", r["registro"])) <= ids, r["id"]            # toda referencia existe en el registro
        if r["respaldo"] == "NO_RESPALDADA":
            assert r["clase_correccion"] == "C" and r["excede_la_evidencia"] == "SI"       # solo el autor decide los verbos de las conclusiones


def test_las_salidas_versionadas_coinciden_con_lo_que_genera_el_codigo():
    """Antes de la fase 15 el informe de OE1 conservaba RNF03/RNF04 como no reproducibles y el de OE5 la Tabla 27 por perfil sin recalcular."""
    import json
    oe1 = {c["id"]: c for c in json.loads((ROOT / "outputs" / "verification_report_oe1.json").read_text(encoding="utf-8"))["comprobaciones"]}
    assert oe1["T37-RNF04-estado"]["estado"] == "COINCIDE" and "T37-RNF04" not in oe1
    oe5 = {c["id"] for c in json.loads((ROOT / "outputs" / "verification_report_oe5.json").read_text(encoding="utf-8"))["comprobaciones"]}
    assert "T27-perfil-media" in oe5 and "T27-perfil" not in oe5


def test_variabilidad_de_t_conv_separa_las_tres_fuentes():
    import json
    v = json.loads((ROOT / "outputs" / "oe3_variabilidad_tconv.json").read_text(encoding="utf-8"))
    assert 2.5 < v["N3"]["A_sd_entre_corridas_por_condicion_ms"]["media"] < 2.8          # «unos 2 ms» no describe N3
    assert v["N3-R"]["A_sd_entre_corridas_por_condicion_ms"]["media"] < 1.5
    assert v["C_entre_campanas"]["sd_entre_las_3_campanas_por_condicion_ms"]["media"] > v["N3"]["A_sd_entre_corridas_por_condicion_ms"]["media"]


def test_cambios_v3_de_la_copia_de_revision_son_exactos_y_estan_justificados():
    with open(ROOT / "auditoria" / "REGISTRO_CAMBIOS_REVISION_FACTUAL_V3.csv", encoding="utf-8", newline="") as fh:
        filas = list(csv.DictReader(fh))
    assert [f["id_cambio"] for f in filas] == [f"R{i}" for i in range(26, 32)]
    for f in filas:
        assert f["texto_original_exacto"] != f["texto_corregido_exacto"] and f["evidencia"].strip()
    assert {f["propuesta"] for f in filas} == {"C25", "C26", "C20", "C21"}                 # solo correcciones factuales o de formato
    clas = (ROOT / "auditoria" / "CLASIFICACION_CORRECCIONES.md").read_text(encoding="utf-8")
    for c in ("C25", "C26", "C27", "C28", "C29", "C30"):
        assert f"| {c} |" in clas
    assert all("no aplicada" in l or "pendiente" in l for l in clas.splitlines() if l.startswith(("| C27 |", "| C28 |", "| C29 |", "| C30 |")))


def test_comprobacion_numerica_de_la_prosa_del_capitulo_6():
    import json
    r = json.loads((ROOT / "outputs" / "verificacion_prosa_cap6.json").read_text(encoding="utf-8"))
    assert len(r) >= 70 and not [x for x in r if x["estado"] == "ERROR"]
    difieren = {x["id"] for x in r if x["estado"] == "DIFIERE"}
    assert difieren == {"P4-06"}, difieren                                                    # la única frase de prosa que contradice sus datos (corregida en V3)
    assert next(x for x in r if x["id"] == "P4-06b")["estado"] == "COINCIDE"                 # la Tabla 19 sí se reproduce


def test_matriz_de_verificacion_bibliografica():
    with open(ROOT / "auditoria" / "MATRIZ_VERIFICACION_BIBLIOGRAFICA.csv", encoding="utf-8", newline="") as fh:
        m = list(csv.DictReader(fh))
    assert len(m) == 120 and len({r["id"] for r in m}) == 120
    est = {r["verificacion_de_metadatos"] for r in m}
    assert est <= {"VERIFICADO", "VERIFICADO_SOLO_EN_OPENALEX", "NO_VERIFICABLE", "PARCIAL", "DISCREPANTE"}
    assert sum(r["verificacion_de_metadatos"] == "VERIFICADO" for r in m) >= 105
    assert all(not r["doi"] for r in m if r["verificacion_de_metadatos"] == "NO_VERIFICABLE" and "sin DOI" in r["detalle"])
    assert not [r for r in m if r["verificacion_de_metadatos"] == "DISCREPANTE"]


def test_cobertura_de_la_prosa_es_coherente():
    with open(ROOT / "auditoria" / "COBERTURA_PROSA_POR_SECCION.csv", encoding="utf-8", newline="") as fh:
        s = list(csv.reader(fh))[1:]
    total = s[-1]
    assert total[0].startswith("TOTAL")
    assert sum(int(r[1]) for r in s[:-1]) == int(total[1]) and sum(int(r[2]) for r in s[:-1]) == int(total[2])
    assert all(int(r[2]) <= int(r[1]) and int(r[3]) <= int(r[1]) for r in s)
    m3 = next(r for r in s if r[0].startswith("3 Marco te"))
    assert m3[2] == m3[1] and len(m3) == 10                                              # el capítulo 3 se leyó completo en la fase 17
    assert all(int(r[4]) <= int(r[1]) and int(r[6]) <= int(r[1]) for r in s)


def test_hashes_de_los_documentos_de_tesis():
    with open(ROOT / "auditoria" / "HASHES_DOCUMENTOS.csv", encoding="utf-8", newline="") as fh:
        h = list(csv.DictReader(fh))
    assert len(h) == 7 and h[0]["sha256"].startswith("a6bb2934de7fd512") and h[0]["estado"] == "INTACTO"
    est = {r["documento"].split()[-1]: r for r in h}
    assert est["V2"]["estado"] == "SUPERADA" and est["V2"]["paginas_con_word"] == "268"
    assert est["V3"]["estado"] == "INTACTA" and est["V3"]["paginas_con_word"] == "267"
    assert est["V4"]["estado"] == "INTACTA" and est["V4"]["paginas_con_word"] == "267"
    assert est["V5"]["estado"].startswith("VIGENTE") and est["V5"]["paginas_con_word"] == "267"
    assert len({r["sha256"] for r in h}) == 7


def test_matriz_de_coherencia_es_en():
    with open(ROOT / "auditoria" / "MATRIZ_COHERENCIA_ES_EN.csv", encoding="utf-8", newline="") as fh:
        m = list(csv.DictReader(fh))
    assert len(m) == 16 and len(m[0]) == 7
    n3r = next(r for r in m if r["tema"].startswith("N3-R"))
    assert all(v == "NO" for k, v in n3r.items() if k not in ("tema", "observacion"))      # N3-R y N3-S no figuran en ningún bloque (C4, C5)


def test_auditoria_holm_dos_implementaciones_coinciden():
    with open(ROOT / "auditoria" / "HOLM_AUDITORIA.csv", encoding="utf-8", newline="") as fh:
        h = list(csv.DictReader(fh))
    assert len(h) == 84
    assert all(r["A_igual_a_B"] == "SI" for r in h if r["estado"] != "INFORMATIVO" and r["p_recalculado_metodo_B"])
    assert sum(r["estado"] == "DIFIERE" for r in h) == 2 and all(r["ubicacion"] != "Tabla 14" for r in h if r["estado"] == "DIFIERE")


def test_fuentes_texto_completo_estados_permitidos():
    with open(ROOT / "auditoria" / "FUENTES_TEXTO_COMPLETO.csv", encoding="utf-8", newline="") as fh:
        f = list(csv.DictReader(fh))
    assert sum(r["estado"].startswith("ENCONTRADA") for r in f) >= 100
    assert sum("SALVEDAD" in r["estado"] for r in f) >= 4


def test_registro_cambios_v4():
    with open(ROOT / "auditoria" / "REGISTRO_CAMBIOS_REVISION_FACTUAL_V4.csv", encoding="utf-8", newline="") as fh:
        c = list(csv.DictReader(fh))
    assert [r["id_cambio"] for r in c] == [f"R{i}" for i in range(32, 42)]
    assert all(r["texto_original_exacto"] != r["texto_corregido_exacto"] and r["evidencia"] for r in c)


def test_tabla14_y_tablas_13_16_se_reproducen_con_dos_analisis_distintos():
    with open(ROOT / "auditoria" / "TABLA14_REPRODUCCION.csv", encoding="utf-8", newline="") as fh:
        t = list(csv.DictReader(fh))
    filas = [r for r in t if not r["termino"].startswith("(resumen)")]
    assert len(filas) == 9 and all(r["T14_coincide_con_B"] == "SI" for r in filas)
    assert all(r["T13_T16_coinciden_con_A"] == "SI" for r in filas if r["T13_T16_coinciden_con_A"])
    assert {r["A_g_l_residuales"] for r in filas} == {"192"} and {r["B_g_l_residuales"] for r in filas} == {"219"}      # son modelos distintos
    assert t[-1]["T13_T16_coinciden_con_A"] == "SI"


def test_revision_de_parrafos_fase_18():
    with open(ROOT / "auditoria" / "REVISION_PARRAFOS_FASE18.csv", encoding="utf-8", newline="") as fh:
        r = list(csv.DictReader(fh))
    assert len(r) == 105 and len({x["linea_del_texto_plano"] for x in r}) == 105
    permitidos = {"VERIFICADO_CON_DATOS", "COHERENTE_CON_EL_PROYECTO", "CONTRASTADO_CON_FUENTE_EXTERNA", "METADATOS_VERIFICADOS_SIN_CONTRASTE_DE_CONTENIDO",
                  "TEXTO_FORMAL_SIN_AFIRMACIONES_VERIFICABLES", "AFIRMACION_PROSPECTIVA_O_NORMATIVA", "INTERPRETACION_EXAMINADA_CON_OBSERVACION", "HALLAZGO"}
    assert {x["estado_de_la_revision"] for x in r} <= permitidos
    assert all(x["metodo_y_evidencia"] for x in r)
    assert not [x for x in r if x["estado_de_la_revision"] == "HALLAZGO" and not x["hallazgo"]]                       # todo hallazgo tiene identificador


def test_registro_de_cambios_v5_y_fuentes_pendientes():
    with open(ROOT / "auditoria" / "REGISTRO_CAMBIOS_REVISION_FACTUAL_V5.csv", encoding="utf-8", newline="") as fh:
        c = list(csv.DictReader(fh))
    assert [x["id_cambio"] for x in c] == [f"R{i}" for i in range(42, 48)]
    assert all(x["texto_original_exacto"] != x["texto_corregido_exacto"] and x["evidencia"] for x in c)
    with open(ROOT / "auditoria" / "FUENTES_PENDIENTES_FASE18.csv", encoding="utf-8", newline="") as fh:
        f = list(csv.DictReader(fh))
    assert len(f) == 5 and all(x["la_fuente_existe"] and x["la_fuente_respalda_la_afirmacion"] for x in f)
