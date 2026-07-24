"""Tests del Contrato de Generación de Recursos Pedagógicos (RFC-0011/1,
Parte A). Función pura, sin DB: valida determinismo, cobertura del
catálogo de PP4, parametrización (nunca hardcodea el curso/lenguaje), y
que `origen` sea una referencia y no una explicación fabricada.
"""

from app.services.resource_prompt_generation import (
    VERSION_PLANTILLA,
    _PLANTILLA_POR_FORMA,
    generar_prompt_recurso,
)

_FORMAS_PP4 = (
    "ejemplo_adicional",
    "animacion",
    "reto_mas_pequeno",
    "pista_progresiva",
    "audio",
    "codigo_guiado",
    "narracion_tutor",
)


def test_es_puro_y_deterministico():
    a = generar_prompt_recurso("animacion", "visual", "modalidad(variables)", "Variables")
    b = generar_prompt_recurso("animacion", "visual", "modalidad(variables)", "Variables")
    assert a == b


def test_cubre_el_catalogo_completo_de_formas_de_pp4():
    for forma in _FORMAS_PP4:
        assert forma in _PLANTILLA_POR_FORMA, forma


def test_forma_desconocida_usa_fallback_generico_sin_lanzar():
    recurso = generar_prompt_recurso("forma-inexistente", "visual", "asunto-x", "Concepto")
    assert "forma-inexistente" in recurso.texto_prompt


def test_sustituye_todas_las_variables_de_la_plantilla():
    recurso = generar_prompt_recurso(
        "animacion", "visual", "modalidad(variables)", "Variables",
        nivel="fundamentos", objetivo="reconocer una asignación",
    )
    assert "{{" not in recurso.texto_prompt
    assert "Variables" in recurso.texto_prompt
    assert "fundamentos" in recurso.texto_prompt
    assert "reconocer una asignación" in recurso.texto_prompt


def test_nunca_hardcodea_el_nombre_de_un_curso_o_lenguaje():
    for forma in _FORMAS_PP4:
        assert "Python" not in _PLANTILLA_POR_FORMA[forma]
        assert "Fundamentos de la Programación" not in _PLANTILLA_POR_FORMA[forma]


def test_version_plantilla_viaja_en_el_resultado():
    recurso = generar_prompt_recurso("audio", "audio", "modalidad(bucles)", "Bucles")
    assert recurso.version_plantilla == VERSION_PLANTILLA


def test_origen_es_referencia_no_explicacion_fabricada():
    alternativas = ({"modalidad": "textual", "razon": "x"},)
    recurso = generar_prompt_recurso(
        "reto_mas_pequeno", "kinesthetic", "modalidad(condicionales)", "Condicionales",
        alternativas_descartadas=alternativas,
    )
    # origen debe ser exactamente {asunto, alternativas_descartadas} —
    # nunca una lista de motivos/etiquetas inventada por esta capa.
    assert set(recurso.origen.keys()) == {"asunto", "alternativas_descartadas"}
    assert recurso.origen["asunto"] == "modalidad(condicionales)"
    assert recurso.origen["alternativas_descartadas"] == alternativas


def test_referencia_recurso_ausente_por_defecto():
    recurso = generar_prompt_recurso("audio", "audio", "modalidad(bucles)", "Bucles")
    assert recurso.referencia_recurso is None


def test_objetivo_por_defecto_menciona_el_concepto_no_el_curso():
    recurso = generar_prompt_recurso("ejemplo_adicional", "reading", "modalidad(arreglos)", "Arreglos")
    assert "Arreglos" in recurso.texto_prompt
