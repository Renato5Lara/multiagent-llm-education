"""
Banco fijo del instrumento experimental de conocimiento (pre/post-test).

36 ítems MCQ = 4 por módulo (1 básica, 2 intermedias, 1 avanzada) sobre los
9 módulos de Fundamentos de la Programación. Mismo instrumento para todos
los estudiantes: la comparabilidad estadística pre→post exige que el banco
sea fijo y versionado (BANK_VERSION). El LLM no participa en su construcción.

El seed es idempotente: IDs deterministas (uuid5 por curso+versión+módulo+orden),
por lo que re-ejecutarlo nunca duplica filas.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.knowledge_test import KnowledgeTestQuestion

logger = logging.getLogger(__name__)

BANK_VERSION = 1
BANK_COURSE_CODE = "IS301"

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "upao-mas-edu.knowledge-test-bank")

# module_number → (1 Introducción, 2 Variables, 3 Operadores, 4 Condicionales,
# 5 Bucles, 6 Funciones, 7 Arreglos, 8 Recursividad, 9 POO básica)
QUESTION_BANK: list[dict] = [
    # ── Módulo 1: Introducción a la Programación ─────────────────────
    {
        "module_number": 1, "topic": "introduccion", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Qué es un algoritmo?",
        "options": [
            "Un lenguaje de programación de alto nivel",
            "Una secuencia finita y ordenada de pasos para resolver un problema",
            "Un programa que ya fue compilado y ejecutado",
            "Un error que ocurre durante la ejecución de un programa",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 1, "topic": "introduccion", "difficulty": "intermedio", "bloom_level": 2, "order": 1,
        "text": "¿Cuál es la función principal de un compilador?",
        "options": [
            "Ejecutar el programa línea por línea sin traducirlo",
            "Detectar errores lógicos del algoritmo",
            "Traducir el código fuente a código que la máquina puede ejecutar",
            "Diseñar el diagrama de flujo del programa",
        ],
        "correct_index": 2,
    },
    {
        "module_number": 1, "topic": "introduccion", "difficulty": "intermedio", "bloom_level": 3, "order": 2,
        "text": "En la resolución de un problema computacional, ¿cuál es el orden correcto de las etapas?",
        "options": [
            "Codificación → Análisis → Diseño → Prueba",
            "Diseño → Codificación → Análisis → Prueba",
            "Análisis → Diseño del algoritmo → Codificación → Prueba",
            "Prueba → Codificación → Diseño → Análisis",
        ],
        "correct_index": 2,
    },
    {
        "module_number": 1, "topic": "introduccion", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "Un programa recibe dos números y muestra el mayor de ellos. En el esquema Entrada-Proceso-Salida, ¿cuál es el PROCESO?",
        "options": [
            "Leer los dos números desde el teclado",
            "Comparar los dos números para determinar cuál es mayor",
            "Mostrar el número mayor en pantalla",
            "Declarar las variables donde se guardan los números",
        ],
        "correct_index": 1,
    },

    # ── Módulo 2: Variables y Tipos de Datos ─────────────────────────
    {
        "module_number": 2, "topic": "variables", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Qué es una variable en programación?",
        "options": [
            "Un valor que nunca puede cambiar durante el programa",
            "Un espacio de memoria con nombre que almacena un valor que puede cambiar",
            "Una instrucción que repite un bloque de código",
            "Un tipo de error de sintaxis",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 2, "topic": "variables", "difficulty": "intermedio", "bloom_level": 2, "order": 1,
        "text": "¿Qué tipo de dato es el más apropiado para almacenar la cantidad de estudiantes de un aula?",
        "options": [
            "Cadena de texto (string)",
            "Real (decimal)",
            "Entero (int)",
            "Lógico (booleano)",
        ],
        "correct_index": 2,
    },
    {
        "module_number": 2, "topic": "variables", "difficulty": "intermedio", "bloom_level": 3, "order": 2,
        "text": "Después de ejecutar:\n\nx = 5\nx = x + 2\n\n¿Cuál es el valor final de x?",
        "options": ["5", "2", "7", "52"],
        "correct_index": 2,
    },
    {
        "module_number": 2, "topic": "variables", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "Dadas las variables a = 3 y b = 8, ¿qué logra esta secuencia?\n\naux = a\na = b\nb = aux",
        "options": [
            "Deja ambas variables con el valor 8",
            "Intercambia los valores de a y b",
            "Suma los valores de a y b en aux",
            "Borra el contenido de las tres variables",
        ],
        "correct_index": 1,
    },

    # ── Módulo 3: Operadores y Expresiones ───────────────────────────
    {
        "module_number": 3, "topic": "operadores", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Qué devuelve el operador módulo (%) al aplicarse entre dos números enteros?",
        "options": [
            "El cociente de la división",
            "El resto de la división",
            "El producto de ambos números",
            "La mitad del primer número",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 3, "topic": "operadores", "difficulty": "intermedio", "bloom_level": 3, "order": 1,
        "text": "¿Cuál es el resultado de la expresión 2 + 3 * 4?",
        "options": ["20", "14", "24", "9"],
        "correct_index": 1,
    },
    {
        "module_number": 3, "topic": "operadores", "difficulty": "intermedio", "bloom_level": 3, "order": 2,
        "text": "¿Cuál es el valor de la expresión lógica (5 > 3) Y (2 > 4)?",
        "options": [
            "Verdadero, porque la primera comparación es verdadera",
            "Falso, porque ambas comparaciones deben ser verdaderas",
            "Verdadero, porque al menos una comparación es verdadera",
            "No se puede evaluar una expresión con dos comparaciones",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 3, "topic": "operadores", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "¿Cuál es el resultado de la expresión 17 % 5 + 10 / 2?",
        "options": ["7", "8.5", "12", "3"],
        "correct_index": 0,
    },

    # ── Módulo 4: Condicionales ──────────────────────────────────────
    {
        "module_number": 4, "topic": "condicionales", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Qué estructura permite ejecutar un bloque de código solo si se cumple una condición?",
        "options": [
            "La estructura condicional (si / if)",
            "La estructura repetitiva (mientras / while)",
            "La declaración de variables",
            "La función de impresión en pantalla",
        ],
        "correct_index": 0,
    },
    {
        "module_number": 4, "topic": "condicionales", "difficulty": "intermedio", "bloom_level": 3, "order": 1,
        "text": "Con edad = 18, ¿qué muestra este código?\n\nsi edad >= 18:\n    mostrar \"Mayor de edad\"\nsino:\n    mostrar \"Menor de edad\"",
        "options": [
            "\"Menor de edad\", porque 18 no es mayor que 18",
            "\"Mayor de edad\", porque la condición >= incluye el 18",
            "No muestra nada, porque la condición es ambigua",
            "Muestra ambos mensajes",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 4, "topic": "condicionales", "difficulty": "intermedio", "bloom_level": 2, "order": 2,
        "text": "¿Cuándo es necesario usar una estructura si–sino si–sino (if–elif–else) en lugar de un solo si–sino?",
        "options": [
            "Cuando el programa no tiene condiciones",
            "Cuando se debe clasificar un valor en más de dos casos posibles",
            "Cuando se quiere repetir un bloque varias veces",
            "Cuando solo hay dos resultados posibles",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 4, "topic": "condicionales", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "Con nota = 15, ¿qué categoría muestra este código?\n\nsi nota >= 20:\n    mostrar \"A\"\nsino si nota >= 14:\n    mostrar \"B\"\nsino:\n    mostrar \"C\"",
        "options": ["A", "B", "C", "No muestra nada"],
        "correct_index": 1,
    },

    # ── Módulo 5: Bucles ─────────────────────────────────────────────
    {
        "module_number": 5, "topic": "bucles", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Qué estructura repite un bloque de instrucciones mientras una condición sea verdadera?",
        "options": [
            "La estructura condicional (si / if)",
            "El bucle (mientras / while)",
            "La declaración de constantes",
            "El operador de asignación",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 5, "topic": "bucles", "difficulty": "intermedio", "bloom_level": 2, "order": 1,
        "text": "¿Cuántas veces se ejecuta el cuerpo de este bucle?\n\npara i desde 1 hasta 5:\n    mostrar i",
        "options": ["4 veces", "5 veces", "6 veces", "Infinitas veces"],
        "correct_index": 1,
    },
    {
        "module_number": 5, "topic": "bucles", "difficulty": "intermedio", "bloom_level": 3, "order": 2,
        "text": "¿Cuál es el valor final de suma?\n\nsuma = 0\npara i desde 1 hasta 3:\n    suma = suma + i",
        "options": ["3", "6", "9", "0"],
        "correct_index": 1,
    },
    {
        "module_number": 5, "topic": "bucles", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "Con x = 3, ¿qué ocurre al ejecutar este código?\n\nmientras x > 0:\n    mostrar x",
        "options": [
            "Muestra 3, 2, 1 y termina",
            "Muestra 3 una sola vez y termina",
            "Nunca termina, porque x no se modifica dentro del bucle",
            "No se ejecuta, porque la condición es falsa",
        ],
        "correct_index": 2,
    },

    # ── Módulo 6: Funciones ──────────────────────────────────────────
    {
        "module_number": 6, "topic": "funciones", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Cuál es la ventaja principal de organizar un programa en funciones?",
        "options": [
            "Hace que el programa se ejecute siempre más rápido",
            "Permite reutilizar código y dividir el problema en partes más simples",
            "Elimina la necesidad de usar variables",
            "Evita que el programa tenga errores",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 6, "topic": "funciones", "difficulty": "intermedio", "bloom_level": 2, "order": 1,
        "text": "¿Cuál es la diferencia entre parámetro y argumento?",
        "options": [
            "Son exactamente lo mismo en todos los contextos",
            "El parámetro se declara en la definición de la función; el argumento es el valor que se envía al llamarla",
            "El argumento se declara en la definición; el parámetro es el valor enviado",
            "Los parámetros solo existen en funciones que no retornan valor",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 6, "topic": "funciones", "difficulty": "intermedio", "bloom_level": 3, "order": 2,
        "text": "¿Qué muestra este código?\n\nfunción doble(n):\n    retornar n * 2\n\nmostrar doble(4)",
        "options": ["4", "6", "8", "n * 2"],
        "correct_index": 2,
    },
    {
        "module_number": 6, "topic": "funciones", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "Una variable declarada DENTRO de una función, ¿desde dónde puede utilizarse?",
        "options": [
            "Desde cualquier parte del programa",
            "Solo dentro de la función donde fue declarada (ámbito local)",
            "Solo fuera de la función que la declaró",
            "Solo si la función no recibe parámetros",
        ],
        "correct_index": 1,
    },

    # ── Módulo 7: Arreglos ───────────────────────────────────────────
    {
        "module_number": 7, "topic": "arreglos", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Qué es un arreglo (array)?",
        "options": [
            "Una colección de elementos del mismo tipo, accesibles por un índice",
            "Una función que ordena números automáticamente",
            "Una variable que solo puede guardar un valor a la vez",
            "Un tipo de bucle especializado en textos",
        ],
        "correct_index": 0,
    },
    {
        "module_number": 7, "topic": "arreglos", "difficulty": "intermedio", "bloom_level": 2, "order": 1,
        "text": "Dado el arreglo A = [4, 7, 1, 9] con índices desde 0, ¿cuál es el valor de A[2]?",
        "options": ["4", "7", "1", "9"],
        "correct_index": 2,
    },
    {
        "module_number": 7, "topic": "arreglos", "difficulty": "intermedio", "bloom_level": 3, "order": 2,
        "text": "Para hallar el MAYOR elemento de un arreglo recorriéndolo con un bucle, ¿cómo conviene inicializar la variable mayor?",
        "options": [
            "Con el valor 0 en todos los casos",
            "Con el primer elemento del arreglo",
            "Con el último elemento del arreglo",
            "No es necesario inicializarla",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 7, "topic": "arreglos", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "¿Cuál es el valor final de contador?\n\nA = [3, 6, 8, 5, 2]\ncontador = 0\npara cada x en A:\n    si x % 2 == 0:\n        contador = contador + 1",
        "options": ["2", "3", "5", "0"],
        "correct_index": 1,
    },

    # ── Módulo 8: Recursividad ───────────────────────────────────────
    {
        "module_number": 8, "topic": "recursividad", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "¿Qué es una función recursiva?",
        "options": [
            "Una función que se llama a sí misma para resolver el problema",
            "Una función que se ejecuta dentro de un bucle",
            "Una función que no recibe parámetros",
            "Una función que solo puede llamarse una vez",
        ],
        "correct_index": 0,
    },
    {
        "module_number": 8, "topic": "recursividad", "difficulty": "intermedio", "bloom_level": 2, "order": 1,
        "text": "¿Por qué es imprescindible el caso base en una función recursiva?",
        "options": [
            "Porque hace que la función retorne siempre cero",
            "Porque detiene las llamadas recursivas y evita que sean infinitas",
            "Porque permite que la función reciba más parámetros",
            "Porque convierte la recursión en un bucle automáticamente",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 8, "topic": "recursividad", "difficulty": "intermedio", "bloom_level": 3, "order": 2,
        "text": "¿Cuál es el resultado de factorial(3)?\n\nfunción factorial(n):\n    si n <= 1:\n        retornar 1\n    retornar n * factorial(n - 1)",
        "options": ["3", "6", "9", "1"],
        "correct_index": 1,
    },
    {
        "module_number": 8, "topic": "recursividad", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "¿Cuál es el valor de f(5)?\n\nfunción f(n):\n    si n == 0: retornar 0\n    si n == 1: retornar 1\n    retornar f(n-1) + f(n-2)",
        "options": ["8", "5", "3", "13"],
        "correct_index": 1,
    },

    # ── Módulo 9: POO básica ─────────────────────────────────────────
    {
        "module_number": 9, "topic": "poo", "difficulty": "basico", "bloom_level": 1, "order": 0,
        "text": "En Programación Orientada a Objetos, ¿qué es una clase?",
        "options": [
            "Una plantilla que define los atributos y métodos que tendrán sus objetos",
            "Un valor concreto almacenado en memoria",
            "Un bucle que recorre objetos",
            "Un archivo donde se guarda el programa",
        ],
        "correct_index": 0,
    },
    {
        "module_number": 9, "topic": "poo", "difficulty": "intermedio", "bloom_level": 2, "order": 1,
        "text": "¿Cuál es la relación correcta entre clase y objeto?",
        "options": [
            "La clase es una copia del objeto",
            "El objeto es una instancia concreta creada a partir de una clase",
            "Un objeto puede existir sin ninguna clase que lo defina",
            "Clase y objeto son sinónimos",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 9, "topic": "poo", "difficulty": "intermedio", "bloom_level": 2, "order": 2,
        "text": "¿En qué consiste el encapsulamiento?",
        "options": [
            "En que una clase herede los métodos de otra",
            "En ocultar los datos internos del objeto y exponer solo los métodos necesarios",
            "En crear múltiples objetos de una misma clase",
            "En dividir el programa en funciones sueltas",
        ],
        "correct_index": 1,
    },
    {
        "module_number": 9, "topic": "poo", "difficulty": "avanzado", "bloom_level": 4, "order": 3,
        "text": "Si la clase Perro hereda de la clase Animal, ¿qué implica la herencia?",
        "options": [
            "Perro reutiliza los atributos y métodos de Animal y puede añadir los suyos",
            "Animal deja de existir cuando se crea Perro",
            "Perro y Animal deben tener exactamente los mismos métodos",
            "Animal hereda automáticamente los métodos de Perro",
        ],
        "correct_index": 0,
    },
]


def _question_id(item: dict) -> str:
    """ID determinista por curso+versión+módulo+orden: re-seedear nunca duplica."""
    seed = f"{BANK_COURSE_CODE}:v{BANK_VERSION}:m{item['module_number']}:o{item['order']}"
    return str(uuid.uuid5(_NAMESPACE, seed))


def seed_knowledge_test_bank(db: Session) -> int:
    """Siembra el banco de forma idempotente. Devuelve cuántas preguntas insertó."""
    existing_ids = {
        row[0]
        for row in db.query(KnowledgeTestQuestion.id)
        .filter(
            KnowledgeTestQuestion.course_code == BANK_COURSE_CODE,
            KnowledgeTestQuestion.version == BANK_VERSION,
        )
        .all()
    }

    inserted = 0
    for item in QUESTION_BANK:
        qid = _question_id(item)
        if qid in existing_ids:
            continue
        db.add(
            KnowledgeTestQuestion(
                id=qid,
                course_code=BANK_COURSE_CODE,
                version=BANK_VERSION,
                **item,
            )
        )
        inserted += 1

    if inserted:
        db.commit()
        logger.info(
            "Banco de conocimiento seedeado: %d preguntas nuevas (v%d)",
            inserted,
            BANK_VERSION,
        )
    return inserted
