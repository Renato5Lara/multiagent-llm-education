"""
Invariantes del banco de diagnóstico v4 (solo Módulo 1).

Norma que implementan: docs/architecture/DESIGN-banco-diagnostico-m1.md — §7
(invariantes 1 a 14), §13 (tabla de mapeo), §4 (reglas de evidencia), §8 (la
versión vigente no toca las anteriores) y decisiones O = B (orden de servicio
global), M (sin modelos mentales) y P1 (Pre y Post con la misma versión).

`correct_index` (§4.7) y la longitud de las opciones (§4.8) son objetivos de
diseño con revisión manual, no invariantes automáticos: no se prueban aquí.
"""

import re
import uuid
from collections import Counter

import pytest

from tests.conftest import auth_header

from app.data.knowledge_test_bank import (
    BANK_COURSE_CODE,
    BANK_VERSION,
    COMP_0,
    COMP_2,
    COMP_3,
    COMP_5,
    COMPETENCY_LABELS,
    ITEM_MAPPING,
    MENTAL_MODELS_BY_COMPETENCY,
    QUESTION_BANK,
    mental_model_for,
    seed_knowledge_test_bank,
)
from app.models.knowledge_test import KnowledgeTestQuestion
from app.services.knowledge_test_service import get_bank_questions

# Bloom mínimo por concepto de M1 (§4.3): el ítem no puede ser más superficial
# que el concepto principal que evidencia (el primero de su mapeo).
BLOOM_MINIMO_CONCEPTO = {"M1.1": 2, "M1.2": 3, "M1.3": 2, "M1.4": 3, "M1.5": 3}
CONCEPTOS_DE_M1 = set(BLOOM_MINIMO_CONCEPTO)

# Fragmento que identifica a cada ítem aprobado por su NÚMERO de ítem (el que
# usan la especificación y el diseño), independiente de su `order` de servicio.
MARCADOR_DE_ITEM = {
    1: "bolsita de té",
    2: "escudo del colegio",
    3: "representaciones en pseudocódigo",
    4: "diagramas de flujo",
    5: 'print("Buenos días")',
    6: "# Saludo inicial",
    7: 'print("Gracias por venir)',
    8: 'print "Hasta luego"',
}


@pytest.fixture
def banco(db):
    seed_knowledge_test_bank(db)
    return db


def _numero_de_item(texto: str) -> int:
    coincidencias = [n for n, marca in MARCADOR_DE_ITEM.items() if marca in texto]
    assert len(coincidencias) == 1, f"el enunciado no identifica un único ítem: {texto[:60]!r}"
    return coincidencias[0]


def _clave(item: dict) -> tuple[str, int]:
    return (item["topic"], item["order"])


# ── §7.1 / §5: versión vigente y siembra ─────────────────────────────


def test_la_version_vigente_es_la_4():
    assert BANK_VERSION == 4


def test_el_seed_inserta_exactamente_los_8_items_de_la_v4_y_es_idempotente(db):
    """§7.1: exactamente 8 ítems activos de la versión 4; §5: el seed no duplica."""
    assert seed_knowledge_test_bank(db) == 8
    assert seed_knowledge_test_bank(db) == 0

    filas = db.query(KnowledgeTestQuestion).filter_by(version=4).all()
    assert len(filas) == 8
    assert all(f.is_active for f in filas)
    assert db.query(KnowledgeTestQuestion).count() == 8


def test_get_bank_questions_sirve_solo_los_8_items_de_la_v4(banco):
    assert len(get_bank_questions(banco)) == 8


# ── §7.2 a §7.11, §13: cobertura, mapeo y estructura ─────────────────


def test_todos_los_items_son_de_m1(banco):
    """§7.2 (D5)."""
    assert {q.module_number for q in get_bank_questions(banco)} == {1}


def test_el_mapeo_coincide_exactamente_con_los_items_del_banco():
    """§7.3: la tabla de mapeo no tiene claves de más ni de menos que el banco."""
    assert set(ITEM_MAPPING) == {_clave(q) for q in QUESTION_BANK}
    for clave, fila in ITEM_MAPPING.items():
        assert fila["funcion"] in {"concebir", "representar", "ejecutar"}, clave
        assert fila["conceptos"], clave


def test_el_reparto_por_funcion_es_2_2_4():
    """§3 y §7.4: concebir 2, representar 2, ejecutar 4."""
    por_funcion = Counter(fila["funcion"] for fila in ITEM_MAPPING.values())
    assert por_funcion == {"concebir": 2, "representar": 2, "ejecutar": 4}


def test_ejecutar_tiene_un_item_de_sintaxis_sin_print_y_uno_a_nivel_programa():
    """§7.5 y §13: las etiquetas solo aparecen en ítems de Ejecutar."""
    ejecutar = [f for f in ITEM_MAPPING.values() if f["funcion"] == "ejecutar"]
    assert any("sintaxis_sin_print" in f["etiquetas"] for f in ejecutar)
    assert any("nivel_programa" in f["etiquetas"] for f in ejecutar)
    for fila in ITEM_MAPPING.values():
        if {"sintaxis_sin_print", "nivel_programa"} & set(fila["etiquetas"]):
            assert fila["funcion"] == "ejecutar"
    con_sintaxis = [c for c, f in ITEM_MAPPING.items() if "sintaxis_sin_print" in f["etiquetas"]]
    assert len(con_sintaxis) == 1


def test_ningun_item_se_atribuye_a_m1_6_ni_a_m2_o_posteriores():
    """§7.6 y §4: solo M1.1 a M1.5, tanto en el éxito como en el fallo."""
    for clave, fila in ITEM_MAPPING.items():
        atribuidos = set(fila["conceptos"]) | set(fila["fallo"])
        assert atribuidos <= CONCEPTOS_DE_M1, (clave, atribuidos - CONCEPTOS_DE_M1)
        assert set(fila["fallo"]) <= set(fila["conceptos"]), clave


def test_los_programas_de_los_items_no_usan_conceptos_de_m2_o_posteriores():
    """§4: el código de los ítems de Ejecutar solo usa print, comentarios y
    líneas en blanco — sin variables, números, operadores, condiciones,
    bucles ni input (que son de M2 en adelante)."""
    revisados = 0
    for q in QUESTION_BANK:
        codigo = [
            linea for linea in q["text"].split("\n")
            if linea.startswith(("print", "#"))
        ]
        if not codigo:
            continue
        revisados += 1
        for linea in codigo:
            sin_cadenas = re.sub(r'"[^"\n]*"?', '""', linea)
            sin_comentario = sin_cadenas.split("#")[0]
            assert not re.search(r"\d|[=+\-*/%<>]|\b(if|for|while|input|def|int|str)\b", sin_comentario), linea
    assert revisados == 4


def test_la_clave_topic_order_es_unica_y_order_es_global_de_0_a_7():
    """§7.7: (topic, order) único y `order` global único en 0 a 7."""
    assert len({_clave(q) for q in QUESTION_BANK}) == 8
    assert sorted(q["order"] for q in QUESTION_BANK) == list(range(8))


def test_los_ids_de_la_v4_son_unicos_y_estan_sembrados(banco):
    ids = [q.id for q in get_bank_questions(banco)]
    assert len(set(ids)) == 8


def test_las_competencias_usadas_son_comp_0_2_3_y_5_con_dos_items_cada_una():
    """§6, §7.8 y §7.11."""
    por_topic = Counter(q["topic"] for q in QUESTION_BANK)
    assert por_topic == {COMP_0: 2, COMP_2: 2, COMP_3: 2, COMP_5: 2}
    assert set(por_topic) <= set(COMPETENCY_LABELS)


def test_el_bloom_es_obligatorio_y_no_inferior_al_del_concepto_principal():
    """§4.3 y §7.9."""
    for q in QUESTION_BANK:
        assert q["bloom_level"] is not None, _clave(q)
        principal = ITEM_MAPPING[_clave(q)]["conceptos"][0]
        assert q["bloom_level"] >= BLOOM_MINIMO_CONCEPTO[principal], _clave(q)


def test_cada_item_tiene_cuatro_opciones_distintas_y_un_correct_index_valido():
    """§7.10."""
    for q in QUESTION_BANK:
        assert len(q["options"]) == 4, _clave(q)
        assert len(set(q["options"])) == 4, _clave(q)
        assert 0 <= q["correct_index"] < 4, _clave(q)
        assert q["difficulty"] in {"basico", "intermedio", "avanzado"}, _clave(q)


# ── §7.13 (C3): secuencia de servicio ────────────────────────────────


def test_get_bank_questions_sirve_los_items_en_la_secuencia_1_2_3_4_7_8_5_6(banco):
    """§7.13, §6 y §9.10 (decisión O = B): `order` 0 a 7 es la posición de
    servicio; el ítem 7 (sintaxis sin print) va antes de los que muestran print."""
    servidas = get_bank_questions(banco)

    assert [q.order for q in servidas] == [0, 1, 2, 3, 4, 5, 6, 7]
    assert [_numero_de_item(q.text) for q in servidas] == [1, 2, 3, 4, 7, 8, 5, 6]


def test_el_correct_index_final_de_cada_item_apunta_a_su_opcion_correcta(banco):
    """Valores aprobados por número de ítem, verificados contra el texto de la
    opción correcta (no solo contra el índice)."""
    correctas = {
        1: "1. Hervir 250 ml de agua. 2. Poner una bolsita de té en la taza. "
           "3. Verter el agua en la taza. 4. Esperar 3 minutos y sacar la bolsita.",
        2: "Poner las clases del día en orden según su hora de inicio.",
        3: "INICIO\nPedir el nombre del estudiante\n"
           "Armar un mensaje de bienvenida con ese nombre\nMostrar el mensaje\nFIN",
        4: "( Inicio )\n↓\n/ Pedir una frase /\n↓\n[ Contar las palabras de la frase ]\n"
           "↓\n/ Mostrar la cantidad de palabras /\n↓\n( Fin )",
        5: "Buenos días\nBienvenido al curso\nHasta pronto",
        6: "Hola\nAdiós",
        7: "Falta cerrar las comillas al final del texto.",
        8: "La segunda línea no lleva paréntesis después de print.",
    }
    indices = {1: 2, 2: 3, 3: 0, 4: 1, 5: 3, 6: 0, 7: 2, 8: 1}

    for q in get_bank_questions(banco):
        n = _numero_de_item(q.text)
        assert q.correct_index == indices[n], n
        assert q.options[q.correct_index] == correctas[n], n


# ── §4.9 y §7.14: alternativas ───────────────────────────────────────


def test_ninguna_cadena_literal_de_un_item_aparece_en_otro():
    """§4.9: un ítem no debe dar la respuesta de otro (p. ej. los textos que
    imprimen los programas de los ítems 5 a 8)."""
    literales = {
        5: ["Buenos días", "Bienvenido al curso", "Hasta pronto"],
        6: ["Hola", "Adiós", "Este mensaje es de prueba", "Saludo inicial"],
        7: ["Gracias por venir"],
        8: ["Buenas tardes", "Hasta luego"],
    }
    por_numero = {_numero_de_item(q["text"]): q for q in QUESTION_BANK}
    for n, cadenas in literales.items():
        for otro, q in por_numero.items():
            if otro == n:
                continue
            contenido = (q["text"] + " " + " ".join(q["options"])).lower()
            for cadena in cadenas:
                assert cadena.lower() not in contenido, (n, cadena, otro)


def test_con_pre_line_ninguna_pareja_de_opciones_de_un_item_se_ve_igual():
    """§7.14 (decisión T2): `white-space: pre-line` colapsa los espacios y
    conserva los saltos de línea; dos opciones que difieran solo en espacios
    se verían idénticas al estudiante."""
    for q in QUESTION_BANK:
        vistas = ["\n".join(" ".join(l.split()) for l in o.split("\n")) for o in q["options"]]
        assert len(set(vistas)) == 4, _clave(q)


def test_la_etiqueta_opciones_multilinea_coincide_con_los_items_que_la_necesitan():
    """§13: la etiqueta marca exactamente los ítems con saltos de línea en
    alguna alternativa, que el frontend (C1) muestra con font-mono."""
    for q in QUESTION_BANK:
        etiquetado = "opciones_multilinea" in ITEM_MAPPING[_clave(q)]["etiquetas"]
        multilinea = any("\n" in o for o in q["options"])
        assert etiquetado == multilinea, _clave(q)


# ── Decisión M: sin modelos mentales ─────────────────────────────────


def test_la_v4_no_declara_modelos_mentales():
    assert all(m == {} for m in MENTAL_MODELS_BY_COMPETENCY.values())
    for q in QUESTION_BANK:
        for indice in range(4):
            assert mental_model_for(q["topic"], q["order"], indice) is None


# ── §8: las versiones anteriores no se tocan ─────────────────────────


def _id_de_version(version: int, topic: str, order: int) -> str:
    espacio = uuid.uuid5(uuid.NAMESPACE_DNS, "upao-mas-edu.knowledge-test-bank")
    return str(uuid.uuid5(espacio, f"{BANK_COURSE_CODE}:v{version}:{topic}:o{order}"))


def _foto(db, version: int) -> list[tuple]:
    filas = (
        db.query(KnowledgeTestQuestion)
        .filter_by(version=version)
        .order_by(KnowledgeTestQuestion.id)
        .all()
    )
    return [
        (f.id, f.module_number, f.topic, f.text, f.options, f.correct_index,
         f.difficulty, f.bloom_level, f.order, f.is_active, f.version)
        for f in filas
    ]


def test_sembrar_la_v4_no_altera_ni_desactiva_las_versiones_anteriores(db):
    """§5 y §8: las filas de v1/v2/v3 quedan intactas y siguen activas, aun
    cuando comparten (topic, order) con ítems de v4."""
    for version in (2, 3):
        for topic, order in ((COMP_0, 0), (COMP_2, 1), (COMP_3, 0)):
            db.add(
                KnowledgeTestQuestion(
                    id=_id_de_version(version, topic, order),
                    course_code=BANK_COURSE_CODE,
                    module_number=2,
                    topic=topic,
                    text=f"Pregunta histórica v{version} {topic} {order}",
                    options=["a", "b", "c", "d"],
                    correct_index=1,
                    difficulty="basico",
                    bloom_level=2,
                    order=order,
                    is_active=True,
                    version=version,
                )
            )
    db.commit()
    antes = {v: _foto(db, v) for v in (2, 3)}

    assert seed_knowledge_test_bank(db) == 8
    assert seed_knowledge_test_bank(db) == 0

    assert {v: _foto(db, v) for v in (2, 3)} == antes
    assert len(get_bank_questions(db, version=3)) == 3
    assert len(get_bank_questions(db, version=2)) == 3
    assert len(get_bank_questions(db, version=4)) == 8
    ids_v4 = {q.id for q in get_bank_questions(db, version=4)}
    assert not ids_v4 & {f[0] for v in (2, 3) for f in antes[v]}


# ── §8 / P1: el Pre-Test sirve la v4 por HTTP ────────────────────────


def test_el_pretest_sirve_los_8_items_en_orden_y_sin_la_respuesta(
    client, estudiante_token, curso_publicado, banco
):
    resp = client.post(
        f"/api/students/knowledge-test/{curso_publicado.id}/start",
        headers=auth_header(estudiante_token),
        json={"kind": "pre"},
    )

    assert resp.status_code == 200
    cuerpo = resp.json()
    assert cuerpo["total_questions"] == 8
    assert [_numero_de_item(q["text"]) for q in cuerpo["questions"]] == [1, 2, 3, 4, 7, 8, 5, 6]
    assert all("correct_index" not in q for q in cuerpo["questions"])
