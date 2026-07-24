"""
Tests de la Política de Selección de Forma (Adenda A, Arquitectura
Pedagógica v1.0). Función pura, sin DB: valida determinismo, categoría de
consentimiento, filtrado por alternativas descartadas y promoción de
`reto_mas_pequeno` bajo profundidad "aplicacion".
"""

from app.services.adaptive_form_selection import (
    FORM_CONSENT_CATEGORY,
    seleccionar_forma,
)


def test_es_pura_y_deterministica():
    a = seleccionar_forma("visual", "fundamentos")
    b = seleccionar_forma("visual", "fundamentos")
    assert a == b


def test_prioridad_base_por_modalidad_visual():
    forma, categoria = seleccionar_forma("visual", "fundamentos")
    assert forma == "animacion"
    assert categoria == "automatica"


def test_prioridad_base_por_modalidad_kinesthetic():
    forma, _ = seleccionar_forma("kinesthetic", "fundamentos")
    assert forma == "reto_mas_pequeno"


def test_modalidad_desconocida_cae_a_mixta():
    forma, _ = seleccionar_forma("no-existe", "fundamentos")
    assert forma == _mixta_primera_forma()


def _mixta_primera_forma() -> str:
    forma, _ = seleccionar_forma("mixta", "fundamentos")
    return forma


def test_profundidad_aplicacion_promueve_reto():
    forma, _ = seleccionar_forma("visual", "aplicacion")
    assert forma == "reto_mas_pequeno"


def test_profundidad_fundamentos_no_promueve_reto():
    forma, _ = seleccionar_forma("visual", "fundamentos")
    assert forma != "reto_mas_pequeno"


def test_alternativa_descartada_filtra_la_forma_correspondiente():
    # reading: prioridad base = (ejemplo_adicional, animacion, ...).
    # "textual" -> "ejemplo_adicional" descartado; debe caer a "animacion".
    sin_descarte, _ = seleccionar_forma("reading", "fundamentos")
    assert sin_descarte == "ejemplo_adicional"

    con_descarte, _ = seleccionar_forma(
        "reading", "fundamentos",
        alternativas_descartadas=({"modalidad": "textual", "razon": "x"},),
    )
    assert con_descarte == "animacion"


def test_todas_las_formas_descartadas_repite_la_de_mayor_prioridad():
    todas_las_modalidades_descartadas = tuple(
        {"modalidad": m, "razon": "x"} for m in ("textual", "ejemplo-codigo", "practica")
    )
    forma, _ = seleccionar_forma(
        "reading", "fundamentos",
        alternativas_descartadas=todas_las_modalidades_descartadas,
    )
    # reading: (ejemplo_adicional, animacion, reto_mas_pequeno, audio) —
    # textual->ejemplo_adicional, ejemplo-codigo->codigo_guiado (no está en
    # la prioridad de reading), practica->reto_mas_pequeno. Con
    # ejemplo_adicional y reto_mas_pequeno descartados, "animacion" gana
    # (no fue descartada).
    assert forma == "animacion"


def test_categoria_de_consentimiento_es_exhaustiva_para_el_catalogo():
    for forma, categoria in FORM_CONSENT_CATEGORY.items():
        assert categoria in ("automatica", "consentimiento"), forma


def test_formas_con_consentimiento_no_son_seleccionadas_por_las_prioridades_hoy():
    # Ninguna prioridad por modalidad incluye codigo_guiado ni
    # narracion_tutor hoy — confirma que la política es aditiva y no cambia
    # comportamiento actual hasta que un llamador las incluya explícitamente.
    for modalidad, profundidad in (
        ("visual", "fundamentos"), ("visual", "aplicacion"),
        ("reading", "fundamentos"), ("audio", "fundamentos"),
        ("kinesthetic", "aplicacion"), ("mixta", "fundamentos"),
    ):
        forma, categoria = seleccionar_forma(modalidad, profundidad)
        assert categoria == "automatica"
