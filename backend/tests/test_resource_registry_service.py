"""Tests de reutilización del Registro de Recursos (RFC-0011/2, Parte B).

Usa la fixture `db` de conftest.py (SQLite en memoria, misma Base que
Postgres real). Cubre explícitamente los dos caminos que exige la ficha
de RFC-0011/2: primera generación (no existe -> genera y persiste) y
reutilización (existe -> no regenera).
"""

from unittest.mock import patch

from app.models.registro_recurso import RegistroRecurso
from app.services import resource_registry_service
from app.services.resource_registry_service import obtener_o_generar_recurso


def test_primera_generacion_persiste_sin_reutilizar(db):
    fila = obtener_o_generar_recurso(
        db, "animacion", "visual", "modalidad(variables)", "Variables",
    )
    assert fila.id is not None
    assert fila.veces_reutilizado == 0
    assert db.query(RegistroRecurso).count() == 1


def test_segunda_llamada_misma_clave_reutiliza_la_misma_fila(db):
    primera = obtener_o_generar_recurso(
        db, "animacion", "visual", "modalidad(variables)", "Variables",
    )
    segunda = obtener_o_generar_recurso(
        db, "animacion", "visual", "modalidad(variables)", "Variables",
    )
    assert segunda.id == primera.id
    assert segunda.veces_reutilizado == 1
    # Nunca una segunda fila para la misma clave.
    assert db.query(RegistroRecurso).count() == 1


def test_reutilizacion_nunca_vuelve_a_generar_el_prompt(db):
    obtener_o_generar_recurso(
        db, "animacion", "visual", "modalidad(variables)", "Variables",
    )
    with patch.object(
        resource_registry_service, "generar_prompt_recurso",
        side_effect=AssertionError("no debería regenerar en el camino de reutilización"),
    ):
        segunda = obtener_o_generar_recurso(
            db, "animacion", "visual", "modalidad(variables)", "Variables",
        )
    assert segunda.veces_reutilizado == 1


def test_claves_distintas_generan_filas_distintas(db):
    a = obtener_o_generar_recurso(
        db, "animacion", "visual", "modalidad(variables)", "Variables",
    )
    b = obtener_o_generar_recurso(
        db, "audio", "audio", "modalidad(bucles)", "Bucles",
    )
    assert a.id != b.id
    assert db.query(RegistroRecurso).count() == 2


def test_origen_persistido_es_referencia_no_explicacion_fabricada(db):
    alternativas = ({"modalidad": "textual", "razon": "x"},)
    fila = obtener_o_generar_recurso(
        db, "reto_mas_pequeno", "kinesthetic", "modalidad(condicionales)",
        "Condicionales", alternativas_descartadas=alternativas,
    )
    assert set(fila.origen.keys()) == {"asunto", "alternativas_descartadas"}
    assert fila.origen["asunto"] == "modalidad(condicionales)"


def test_race_concurrente_reutiliza_en_vez_de_fallar(db, monkeypatch):
    # Simula la ventana de carrera: dos peticiones consultan el Registro
    # casi a la vez y ambas ven "no existe" — una gana la inserción real
    # (UniqueConstraint), la otra debe reutilizarla sin lanzar excepción.
    ganador = obtener_o_generar_recurso(
        db, "animacion", "visual", "modalidad(bucles)", "Bucles",
    )

    original = resource_registry_service._buscar_existente
    llamadas = {"n": 0}

    def _buscar_simulando_ventana_de_carrera(db, asunto, forma, modalidad):
        llamadas["n"] += 1
        if llamadas["n"] == 1:
            return None  # la fila del "ganador" aún no era visible
        return original(db, asunto, forma, modalidad)

    monkeypatch.setattr(
        resource_registry_service, "_buscar_existente",
        _buscar_simulando_ventana_de_carrera,
    )

    perdedor = obtener_o_generar_recurso(
        db, "animacion", "visual", "modalidad(bucles)", "Bucles",
    )
    assert perdedor.id == ganador.id
    assert db.query(RegistroRecurso).count() == 1
