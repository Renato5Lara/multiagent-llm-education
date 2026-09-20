"""migrate_is301_to_8_modules

Transformación de datos de IS301 (4 -> 8 LearningObjective) y siembra de
los 32 Concept del catálogo cerrado en 4a.2/C, según:

- D14.1 (2C-3.14): elimina "Fundamentos de Python", "Estructuras de
  control" y "Programación orientada a objetos" (remanente legado dentro
  de IS301 -- la representación curricular real de POO es el curso
  independiente POO401, verificado en 2C-3.14-A y sin tocar aquí);
  transforma "Funciones y módulos" en "Funciones" (M6) conservando su
  mismo id.
- D1-D8 (2C-3.12): title/description/bloom_level de cada uno de los 8
  módulos.
- 2C-3.16: orden intramódulo de los 32 conceptos (M1 confirmado 1-6; M2
  con `input()` en 3 y `Conversión de tipos` en 4).
- 2C-3.13-BD: IDs reales verificados contra la base de datos del
  proyecto (no inventados) -- se preservan en el downgrade para que la
  reversión sea simétrica, no una recreación aproximada.

No toca ProgrammingConcept, CONCEPT_DEPENDENCY_GRAPH, POO401, Artifact,
ni ninguna tabla con historico real (path_modules, resource_objectives,
research_metrics, recursos_generados) -- ninguna de ellas tiene FK hacia
learning_objectives (confirmado en 2C-3.13-BD), por lo que esta
migracion no puede afectarlas.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-09-19 00:00:00.000000

"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


IS301_COURSE_ID = "0fbe4f4c-1520-4ecc-ac84-cf0fed353eb0"

# IDs reales verificados en 2C-3.13-BD -- se preservan aqui, no se
# regeneran, para que el downgrade pueda restaurarlos exactamente.
FUNDAMENTOS_PYTHON_ID = "f71448b7-01f3-45ba-9fc6-8d168f6a4517"
ESTRUCTURAS_CONTROL_ID = "d15bae53-e32d-4fc0-9341-1dc6f039344f"
FUNCIONES_MODULOS_ID = "6839a0cb-fd3b-4dc6-b7ae-309bd31a1247"
POO_LEGACY_ID = "8a68447a-9844-4ef3-81d8-0fe6db36d321"

# IDs de los 7 LearningObjective nuevos (M1-M5, M7, M8), fijos y
# deterministas -- no se generan al ejecutar, para que el downgrade
# pueda borrarlos exactamente por id.
LO_IDS = {
    "M1": "7bf31573-e7d9-4a44-ab9e-2b2f6e2793f2",
    "M2": "48c83ac5-591f-44c1-9ebd-829876d9a3da",
    "M3": "b4a98d92-9c51-44ff-a52c-b5605a036e15",
    "M4": "d90a398d-f8eb-4ef0-aade-3155528983c3",
    "M5": "4b300b0a-7470-42cf-856a-66b4a1c018b4",
    "M7": "87809311-8783-49d7-9b43-5d46dfef1340",
    "M8": "f39edcaf-b63b-4e50-b171-70b4bf0ddab1",
}

# (title, description, bloom_level, order) -- D1-D8, 2C-3.12.
MODULES = {
    "M1": (
        "Introducción a la Programación",
        "Este módulo introduce la lógica de resolución de problemas propia de la "
        "programación: cómo diseñar una solución antes de escribirla, cómo "
        "representarla de forma clara y comunicable, y cómo traducirla en un primer "
        "programa ejecutable capaz de producir un resultado observable. Su propósito "
        "es que el estudiante comprenda qué significa programar y sea capaz de "
        "construir y ejecutar soluciones simples en Python.",
        3,
        1,
    ),
    "M2": (
        "Variables y Tipos de Datos",
        "Este módulo amplía el primer programa construido en el módulo anterior "
        "para que pueda trabajar con información real: almacenarla, reconocer su "
        "naturaleza, transformarla cuando sea necesario y obtenerla directamente de "
        "quien lo utiliza. Al finalizar, el estudiante debe ser capaz de escribir "
        "programas que reciban datos del usuario y los empleen correctamente según "
        "el tipo de valor que representan.",
        3,
        2,
    ),
    "M3": (
        "Operadores y Expresiones",
        "Este módulo dota a los programas ya construidos de capacidad de cálculo y "
        "de decisión: realizar operaciones numéricas sobre los datos manejados "
        "hasta ahora, comparar valores entre sí, combinar esas comparaciones según "
        "distintas condiciones, y construir expresiones más elaboradas respetando "
        "el orden en que deben resolverse. Al finalizar, el estudiante debe poder "
        "calcular, comparar y componer expresiones correctas que sienten la base "
        "para que el programa decida qué hacer según la información que maneja.",
        3,
        3,
    ),
    "M4": (
        "Condicionales",
        "Este módulo permite que los programas dejen de ejecutar siempre la misma "
        "secuencia y empiecen a decidir su comportamiento según la información que "
        "manejan: a partir de los cálculos y comparaciones ya construidos, el "
        "programa evalúa una condición y elige entre distintos caminos de "
        "ejecución, incluyendo decisiones que dependen de otras decisiones ya "
        "tomadas. Al finalizar, el estudiante debe ser capaz de construir estas "
        "estructuras y determinar correctamente qué parte del programa se ejecuta "
        "según cada situación posible.",
        4,
        4,
    ),
    "M5": (
        "Bucles",
        "Además de decidir qué camino seguir, un programa necesita poder repetir "
        "una acción tantas veces como sea necesario, ya sea mientras se cumpla una "
        "condición o a lo largo de un rango de valores conocido. Este módulo "
        "desarrolla esa capacidad de repetición, incluyendo la posibilidad de "
        "combinar una repetición dentro de otra y de ajustar su curso deteniéndola "
        "o saltando a la siguiente vuelta cuando la situación lo requiera. Al "
        "finalizar, el estudiante debe ser capaz de construir programas que "
        "ejecuten tareas repetitivas de forma controlada.",
        3,
        5,
    ),
    "M6": (
        "Funciones",
        "Además de repetir una acción mediante bucles, un programa puede "
        "encapsular una operación completa para reutilizarla cuantas veces sea "
        "necesario sin reescribir su lógica cada vez: definirla una sola vez, "
        "ejecutarla con distintos valores de entrada, y aprovechar el resultado "
        "que produce en otras partes del código. Al finalizar, el estudiante debe "
        "ser capaz de construir y utilizar estas operaciones reutilizables, "
        "respetando que sus variables internas permanecen dentro de su ámbito y "
        "que solo el resultado que declara explícitamente sale de él hacia el "
        "resto del programa.",
        3,
        6,
    ),
    "M7": (
        "Arreglos",
        "Así como una función permite reutilizar una misma operación, una lista "
        "permite reunir varios datos relacionados en una sola estructura en lugar "
        "de manejarlos uno por uno: crearla, acceder a sus elementos según su "
        "posición, verificar si un valor se encuentra en ella, modificar su "
        "contenido agregando o quitando elementos, y extraer de ella el "
        "subconjunto que se necesite. Al finalizar, el estudiante debe ser capaz "
        "de construir y manipular estas colecciones de datos para resolver "
        "problemas que requieren trabajar con varios valores a la vez.",
        3,
        7,
    ),
    "M8": (
        "Recursividad",
        "Retomando las funciones ya construidas en un módulo anterior, este "
        "módulo introduce una forma distinta de resolver un problema: en lugar de "
        "repetirlo mediante un bucle, una función puede resolverlo llamándose a sí "
        "misma sobre una versión más pequeña del mismo problema, hasta llegar a un "
        "caso lo bastante simple como para resolverse directamente. Al finalizar, "
        "el estudiante debe ser capaz de construir estas soluciones identificando "
        "correctamente cuándo detenerse y cómo reducir el problema en cada paso, y "
        "de seguir la secuencia de llamadas que se generan para explicar cómo se "
        "obtiene el resultado final.",
        4,
        8,
    ),
}

# Los 32 conceptos, en el orden intramódulo cerrado (2C-3.16 para M1/M2;
# ya cerrado en 4a.2/C para M3-M8).
CONCEPTS_BY_MODULE = {
    "M1": [
        "Algoritmo",
        "Pensamiento computacional / proceso de resolución de problemas",
        "Representación de algoritmos",
        "Estructura y sintaxis básica de un programa en Python",
        "Salida básica (print)",
        "Qué es un lenguaje de programación",
    ],
    "M2": [
        "Variables",
        "Tipos de datos primitivos",
        "Entrada básica (input())",
        "Conversión de tipos",
    ],
    "M3": [
        "Operadores aritméticos básicos",
        "División entera y módulo",
        "Comparación y operadores relacionales",
        "Operadores lógicos",
        "Expresiones y precedencia",
    ],
    "M4": [
        "Condicionales básicos",
        "Condicionales anidados",
    ],
    "M5": [
        "Bucle while",
        "Bucle for",
        "Bucles anidados",
        "Flujo de bucles (break/continue)",
    ],
    "M6": [
        "Definición e invocación de funciones",
        "Parámetros y argumentos",
        "Valores de retorno",
        "Ámbito de variables",
    ],
    "M7": [
        "Creación y estructura de arreglos (listas)",
        "Indexación",
        "Búsqueda (in, .index())",
        "Modificación de tamaño (append, insert, remove, pop)",
        "Slicing",
    ],
    "M8": [
        "Recursividad",
        "Traza y pila de llamadas",
    ],
}


def _learning_objectives_table() -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        "learning_objectives",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36)),
        sa.Column("title", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("bloom_level", sa.Integer()),
        sa.Column("order", sa.Integer()),
    )


def _concepts_table() -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        "concepts",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(255)),
        sa.Column("learning_objective_id", sa.String(36)),
        sa.Column("order", sa.Integer()),
    )


def _module_id(key: str) -> str:
    return FUNCIONES_MODULOS_ID if key == "M6" else LO_IDS[key]


def upgrade() -> None:
    bind = op.get_bind()
    lo = _learning_objectives_table()
    concepts = _concepts_table()

    # 1. Eliminar los tres registros legacy que no pertenecen al núcleo
    #    de generación de 8 módulos (D14.1).
    bind.execute(
        lo.delete().where(
            lo.c.id.in_([FUNDAMENTOS_PYTHON_ID, ESTRUCTURAS_CONTROL_ID, POO_LEGACY_ID])
        )
    )

    # 2. Transformar "Funciones y módulos" -> "Funciones" (M6),
    #    conservando su id.
    title, description, bloom_level, order = MODULES["M6"]
    bind.execute(
        lo.update()
        .where(lo.c.id == FUNCIONES_MODULOS_ID)
        .values(title=title, description=description, bloom_level=bloom_level, order=order)
    )

    # 3. Crear los 7 LearningObjective nuevos (M1-M5, M7, M8).
    new_rows = []
    for key, lo_id in LO_IDS.items():
        title, description, bloom_level, order = MODULES[key]
        new_rows.append(
            {
                "id": lo_id,
                "course_id": IS301_COURSE_ID,
                "title": title,
                "description": description,
                "bloom_level": bloom_level,
                "order": order,
            }
        )
    bind.execute(lo.insert(), new_rows)

    # 4. Sembrar los 32 Concept.
    concept_rows = []
    for module_key, titles in CONCEPTS_BY_MODULE.items():
        objective_id = _module_id(module_key)
        for index, concept_title in enumerate(titles, start=1):
            concept_rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "title": concept_title,
                    "learning_objective_id": objective_id,
                    "order": index,
                }
            )
    bind.execute(concepts.insert(), concept_rows)


def downgrade() -> None:
    bind = op.get_bind()
    lo = _learning_objectives_table()
    concepts = _concepts_table()

    # 1. Borrar los 32 Concept sembrados.
    bind.execute(
        concepts.delete().where(
            concepts.c.learning_objective_id.in_(
                [FUNCIONES_MODULOS_ID] + list(LO_IDS.values())
            )
        )
    )

    # 2. Borrar los 7 LearningObjective nuevos.
    bind.execute(lo.delete().where(lo.c.id.in_(list(LO_IDS.values()))))

    # 3. Revertir "Funciones" -> "Funciones y módulos" (mismo id).
    bind.execute(
        lo.update()
        .where(lo.c.id == FUNCIONES_MODULOS_ID)
        .values(
            title="Funciones y módulos",
            description="Definición, parámetros, retorno, importación",
            bloom_level=3,
            order=3,
        )
    )

    # 4. Restaurar los tres registros legacy con sus valores e ids
    #    originales (verificados en 2C-3.13-BD) -- reversión simétrica,
    #    no una recreación aproximada. Si algún dato real llegó a
    #    depender de los 7 LearningObjective nuevos entre el upgrade y
    #    este downgrade, el paso 2 ya habría fallado por integridad
    #    referencial antes de llegar aquí -- este downgrade nunca
    #    corrompe datos silenciosamente.
    bind.execute(
        lo.insert(),
        [
            {
                "id": FUNDAMENTOS_PYTHON_ID,
                "course_id": IS301_COURSE_ID,
                "title": "Fundamentos de Python",
                "description": "Variables, tipos de datos, operadores",
                "bloom_level": 1,
                "order": 1,
            },
            {
                "id": ESTRUCTURAS_CONTROL_ID,
                "course_id": IS301_COURSE_ID,
                "title": "Estructuras de control",
                "description": "If, for, while, comprensiones",
                "bloom_level": 2,
                "order": 2,
            },
            {
                "id": POO_LEGACY_ID,
                "course_id": IS301_COURSE_ID,
                "title": "Programación orientada a objetos",
                "description": "Clases, objetos, herencia, polimorfismo",
                "bloom_level": 4,
                "order": 4,
            },
        ],
    )
