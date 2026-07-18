"""
Banco del instrumento de diagnóstico competencial (pre/post-test) — BANK_VERSION 3.

12 ítems MCQ basados en RESOLUCIÓN DE PROBLEMAS (no percepción), organizados por
las 6 competencias del modelo cognitivo COMP-0…COMP-5 (2 ítems por competencia).
Pre-Test y Post-Test usan EXACTAMENTE el mismo banco (comparabilidad → ganancia
por competencia = post − pre). Alcance: Módulo 1 de Fundamentos (variables,
tipos, E/S, algoritmo, un condicional simple). SIN bucles: el aprendizaje de
bucles se evidencia en las actividades adaptativas, no en el instrumento.

Dimensiones (campos existentes del modelo, sin tablas nuevas):
    topic         → competencia (comp_0…comp_5)  — dimensión cognitiva (perfil)
    module_number → contenido del curso           — cobertura (1 intro/algoritmo,
                    2 variables/tipos/E-S, 4 condicional simple)
    bloom_level   → profundidad cognitiva

Distractores diagnósticos (RDD/REU/REA): cada distractor evidencia UN único
modelo mental erróneo real del principiante, distinto dentro del ítem. El mapeo
opción→mental_model_id vive en MENTAL_MODELS; el catálogo MENTAL_MODEL_CATALOG
(nombre, descripción, explicación, remediación) lo consulta el agente evaluador
para explicar el diagnóstico y elegir la remediación. Invisible al estudiante.

El seed es idempotente: IDs deterministas (uuid5 por curso+versión+módulo+orden).
El LLM no participa en la construcción del instrumento.

Nota sobre difficulty vs. bloom_level (auditoría jul 2026): las dos dimensiones
son independientes por diseño en las competencias de secuenciación/ejecución
(COMP_3, COMP_4) — dentro de una misma competencia, el par order 0→1 mantiene el
MISMO bloom_level pese a subir de difficulty, porque el tipo de operación
cognitiva (simular una ejecución; ordenar un procedimiento) no cambia entre el
ítem más simple y el más complejo de esa competencia — solo cambia cuánto
contenido hay que procesar. En el resto de las competencias sí se corrigió para
que difficulty y bloom_level progresen juntos (ver BANK_VERSION 3 changelog más
abajo).

Changelog BANK_VERSION 2 → 3 (auditoría pedagógica jul 2026, sin cambios de
Runtime/adaptación — solo contenido de este archivo):
1. COMP-2.1: opción distractora reescrita — "Guarda tres precios distintos del
   mismo producto" podía leerse como literalmente cierta (sí quedan 3 variables
   con 3 valores). Ahora dice que son independientes entre sí, lo cual sí es
   inequívocamente falso (están encadenadas).
2. 8 ítems con fragmentos de código (COMP-1.1, 1.2, 2.1, 2.2, 3.1, 3.2, 5.1, 5.2)
   ahora declaran explícitamente "Python" en el enunciado — antes ninguno lo
   hacía, y en COMP-5.1 esa omisión hacía que un distractor (falta de punto y
   coma) dependiera de una suposición no declarada sobre el lenguaje.
3. COMP-1.2: el distractor "mayúscula/minúscula" no era un modelo mental
   plausible (un dígito no tiene mayúscula/minúscula) — se reemplazó por una
   confusión real y distinta de las otras tres opciones.
4. COMP-1.2 pasa de "intermedio" a "básico" (coincide con su bloom_level real,
   igual al de COMP-1.1). COMP-5.1 y COMP-5.2 pasan de "intermedio" a
   "avanzado" (tienen bloom_level 4, el más alto del banco — más que los ítems
   ya etiquetados "avanzado" en otras competencias).
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models.knowledge_test import KnowledgeTestQuestion

logger = logging.getLogger(__name__)

BANK_VERSION = 3
BANK_COURSE_CODE = "IS301"

_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "upao-mas-edu.knowledge-test-bank")

# Competencias (valores del campo `topic`)
COMP_0 = "comp_0_problema"        # Comprensión del problema
COMP_1 = "comp_1_conceptos"       # Comprensión computacional
COMP_2 = "comp_2_interpretacion"  # Interpretación de código
COMP_3 = "comp_3_simulacion"      # Simulación mental
COMP_4 = "comp_4_construccion"    # Construcción algorítmica
COMP_5 = "comp_5_razonamiento"    # Razonamiento computacional

# Etiquetas legibles de competencia (para el dashboard / perfil)
COMPETENCY_LABELS: dict[str, str] = {
    COMP_0: "Comprensión del problema",
    COMP_1: "Comprensión computacional",
    COMP_2: "Interpretación de código",
    COMP_3: "Simulación mental",
    COMP_4: "Construcción algorítmica",
    COMP_5: "Razonamiento computacional",
}

# Prioridad por competencia (ponderación metodológica, no numérica en la tesis).
# Interno: Crítica=1.0, Alta=0.8, Media-Alta=0.6. Uso: urgencia=(1−score)×peso.
COMPETENCY_PRIORITY: dict[str, str] = {
    COMP_0: "critica",
    COMP_1: "alta",
    COMP_2: "critica",
    COMP_3: "critica",
    COMP_4: "alta",
    COMP_5: "media_alta",
}
PRIORITY_WEIGHT: dict[str, float] = {"critica": 1.0, "alta": 0.8, "media_alta": 0.6}

# Orden de la progresión cognitiva (para presentar el perfil).
COMPETENCY_ORDER: list[str] = [COMP_0, COMP_1, COMP_2, COMP_3, COMP_4, COMP_5]


# ── Ítems del diagnóstico ────────────────────────────────────────────────────
# Cada ítem: campos del modelo + "mental_models" (opción_index → mental_model_id;
# la opción correcta no lleva etiqueta). QUESTION_BANK se deriva quitando
# "mental_models" para que el seed inserte solo columnas válidas.

DIAGNOSTIC_ITEMS: list[dict] = [
    # ══ COMP-0 · Comprensión del problema (enunciados, sin código) ═══════════
    {
        "module_number": 1, "topic": COMP_0, "difficulty": "basico", "bloom_level": 2, "order": 0,
        "text": (
            "Quieres un programa que calcule cuántos años tiene una persona a "
            "partir del año en que nació. ¿Cuál es el conjunto mínimo de datos "
            "que el programa necesita para resolverlo?"
        ),
        "options": [
            "El nombre y la ciudad de la persona",
            "El año actual y el año de nacimiento",
            "Solo el año de nacimiento",
            "El día y la hora exacta",
        ],
        "correct_index": 1,
        "mental_models": {0: "datos_irrelevantes", 2: "analisis_incompleto", 3: "sobre_especificacion"},
    },
    {
        "module_number": 1, "topic": COMP_0, "difficulty": "intermedio", "bloom_level": 3, "order": 1,
        "text": (
            "Un profesor quiere calcular el promedio final de un estudiante a "
            "partir de sus tres notas. En términos de Entrada → Proceso → Salida, "
            "¿cuál es el PROCESO?"
        ),
        "options": [
            "Pedir las tres notas del estudiante",
            "Sumar las tres notas y dividir entre 3",
            "Mostrar el promedio en pantalla",
            "Registrar el nombre del estudiante",
        ],
        "correct_index": 1,
        "mental_models": {0: "confunde_entrada_proceso", 2: "confunde_salida_proceso", 3: "no_identifica_proceso"},
    },

    # ══ COMP-1 · Comprensión computacional (conceptos base aplicados) ════════
    {
        "module_number": 2, "topic": COMP_1, "difficulty": "basico", "bloom_level": 2, "order": 0,
        "text": (
            "En un programa de Python escribes  nombre = \"Ana\"  y más adelante  "
            "nombre = \"Luis\" . ¿Qué ocurrió con el valor de la variable nombre?"
        ),
        "options": [
            "Ahora contiene dos valores a la vez: \"Ana\" y \"Luis\"",
            "Su valor cambió: ahora contiene \"Luis\"",
            "El programa da error porque una variable no puede cambiar",
            "Se creó una segunda variable llamada nombre",
        ],
        "correct_index": 1,
        "mental_models": {0: "variable_acumula", 2: "variable_inmutable", 3: "reasignacion_crea_variable"},
    },
    {
        "module_number": 2, "topic": COMP_1, "difficulty": "basico", "bloom_level": 2, "order": 1,
        "text": (
            "Un estudiante escribe un programa en Python donde aparecen  \"5\"  (con comillas) "
            "y también  5  (sin comillas). El profesor le dice que el programa los "
            "interpreta de forma distinta. ¿Cuál es la razón?"
        ),
        "options": [
            "Son idénticos, las comillas no importan",
            "\"5\" es texto y 5 es un número; el programa los trata distinto",
            "\"5\" es un número y 5 es texto",
            "La diferencia depende del orden en que aparecen escritos, no de las comillas",
        ],
        "correct_index": 1,
        "mental_models": {0: "sin_distincion_tipos", 2: "tipo_invertido", 3: "diferencia_superficial"},
    },

    # ══ COMP-2 · Interpretación de código (¿qué HACE?, no la salida exacta) ══
    {
        "module_number": 2, "topic": COMP_2, "difficulty": "intermedio", "bloom_level": 2, "order": 0,
        "text": (
            "¿Qué hace este código de Python?\n\n"
            "    precio = 100\n"
            "    descuento = precio * 0.2\n"
            "    final = precio - descuento"
        ),
        "options": [
            "Calcula el precio final aplicando un 20% de descuento",
            "Muestra el precio en pantalla",
            "Guarda tres precios independientes, sin relación entre sí",
            "Da error porque usa la variable precio dos veces",
        ],
        "correct_index": 0,
        "mental_models": {1: "confunde_calcular_mostrar", 2: "no_sigue_flujo", 3: "reuso_variable_es_error"},
    },
    {
        "module_number": 4, "topic": COMP_2, "difficulty": "avanzado", "bloom_level": 3, "order": 1,
        "text": (
            "¿Qué hace este código de Python?\n\n"
            "    edad = 20\n"
            "    if edad >= 18:\n"
            "        mensaje = \"Puede votar\"\n"
            "    else:\n"
            "        mensaje = \"No puede votar\""
        ),
        "options": [
            "Decide el mensaje según si la edad es 18 o más",
            "Siempre asigna \"Puede votar\"",
            "Compara la edad con 18 y las suma",
            "Muestra los dos mensajes en pantalla",
        ],
        "correct_index": 0,
        "mental_models": {1: "ignora_condicion", 2: "confunde_comparacion_operacion", 3: "ambas_ramas_ejecutan"},
    },

    # ══ COMP-3 · Simulación mental (predecir la salida/valor exacto) ═════════
    {
        "module_number": 2, "topic": COMP_3, "difficulty": "intermedio", "bloom_level": 3, "order": 0,
        "text": (
            "¿Qué imprime este código de Python?\n\n"
            "    x = 5\n"
            "    y = 3\n"
            "    x = x + y\n"
            "    print(x)"
        ),
        "options": ["8", "5", "53", "15"],
        "correct_index": 0,
        "mental_models": {1: "no_actualiza_variable", 2: "suma_es_concatenacion", 3: "confunde_operador"},
    },
    {
        "module_number": 2, "topic": COMP_3, "difficulty": "avanzado", "bloom_level": 3, "order": 1,
        "text": (
            "¿Qué imprime este código de Python?\n\n"
            "    a = \"5\"\n"
            "    b = \"5\"\n"
            "    print(a + b)"
        ),
        "options": ["55", "10", "Da error", "5"],
        "correct_index": 0,
        "mental_models": {1: "texto_como_numero", 2: "concatenacion_texto_es_error", 3: "ignora_segunda_variable"},
    },

    # ══ COMP-4 · Construcción algorítmica (ordenar pasos) ════════════════════
    {
        "module_number": 1, "topic": COMP_4, "difficulty": "basico", "bloom_level": 3, "order": 0,
        "text": (
            "Estos pasos para retirar dinero de un cajero están desordenados:\n\n"
            "    1. Ingresar el monto a retirar\n"
            "    2. Insertar la tarjeta\n"
            "    3. Ingresar el PIN\n"
            "    4. Retirar el dinero\n\n"
            "¿Cuál es el orden correcto?"
        ),
        "options": [
            "2 → 3 → 1 → 4",
            "1 → 2 → 3 → 4",
            "2 → 1 → 3 → 4",
            "3 → 2 → 1 → 4",
        ],
        "correct_index": 0,
        "mental_models": {1: "ignora_prerrequisitos", 2: "orden_parcial_incorrecto", 3: "inicio_incorrecto"},
    },
    {
        "module_number": 1, "topic": COMP_4, "difficulty": "intermedio", "bloom_level": 3, "order": 1,
        "text": (
            "Un programa debe calcular y mostrar el promedio de dos notas. "
            "Estos pasos están desordenados:\n\n"
            "    1. Mostrar el promedio\n"
            "    2. Pedir las dos notas\n"
            "    3. Sumar las notas y dividir entre 2\n\n"
            "¿Cuál es el orden correcto?"
        ),
        "options": [
            "2 → 3 → 1",
            "3 → 2 → 1",
            "2 → 1 → 3",
            "1 → 2 → 3",
        ],
        "correct_index": 0,
        "mental_models": {1: "procesa_sin_datos", 2: "muestra_antes_de_calcular", 3: "orden_invertido"},
    },

    # ══ COMP-5 · Razonamiento computacional (solo errores simples) ═══════════
    {
        "module_number": 2, "topic": COMP_5, "difficulty": "avanzado", "bloom_level": 4, "order": 0,
        "text": (
            "Este programa de Python da error. ¿Por qué?\n\n"
            "    precio = 100\n"
            "    print(precioo)"
        ),
        "options": [
            "Se escribió precioo (con doble o): una variable que no existe",
            "Falta un punto y coma al final de la línea",
            "No se puede usar print con variables",
            "El número 100 debería ir entre comillas",
        ],
        "correct_index": 0,
        "mental_models": {1: "sintaxis_de_otro_lenguaje", 2: "print_solo_texto", 3: "numeros_necesitan_comillas"},
    },
    {
        "module_number": 4, "topic": COMP_5, "difficulty": "avanzado", "bloom_level": 4, "order": 1,
        "text": (
            "Se esperaba que una persona de 18 años se considerara \"Adulto\", "
            "pero el programa de Python no lo muestra. ¿Cuál es el error?\n\n"
            "    edad = 18\n"
            "    if edad > 18:\n"
            "        print(\"Adulto\")"
        ),
        "options": [
            "La condición usa > (mayor que) en vez de >= (mayor o igual): 18 no es mayor que 18",
            "Falta un else después del if",
            "La variable edad debería llamarse Edad con mayúscula",
            "El print debería ir antes del if",
        ],
        "correct_index": 0,
        "mental_models": {1: "requiere_else", 2: "nombre_irrelevante", 3: "orden_print_if"},
    },
]

# QUESTION_BANK: solo columnas del modelo (el seed hace **item).
QUESTION_BANK: list[dict] = [
    {k: v for k, v in item.items() if k != "mental_models"} for item in DIAGNOSTIC_ITEMS
]

# Mapeo opción→mental_model_id por ítem, con clave canónica (competencia, orden)
# — única y estable (varias competencias comparten module_number como contenido).
MENTAL_MODELS_BY_COMPETENCY: dict[tuple[str, int], dict[int, str]] = {
    (item["topic"], item["order"]): item["mental_models"]  # type: ignore[index]
    for item in DIAGNOSTIC_ITEMS
}


# ── Catálogo de modelos mentales (base de conocimiento del evaluador) ─────────
# Cada entrada: nombre, descripcion (qué cree el estudiante), explicacion (la
# corrección conceptual), remediacion (estrategia/actividad sugerida).

MENTAL_MODEL_CATALOG: dict[str, dict[str, str]] = {
    # COMP-0.1
    "datos_irrelevantes": {
        "nombre": "Confunde datos descriptivos con datos necesarios",
        "descripcion": "Cree que cualquier dato de la persona sirve para el cálculo.",
        "explicacion": "Solo los datos que intervienen en la operación son necesarios; el nombre o la ciudad no lo son.",
        "remediacion": "Actividad de análisis: dado un problema, separar datos necesarios de datos irrelevantes.",
    },
    "analisis_incompleto": {
        "nombre": "Análisis incompleto del problema",
        "descripcion": "Omite un dato imprescindible (el año actual) para resolver el problema.",
        "explicacion": "La edad requiere DOS datos: el año actual y el de nacimiento; con uno solo no se puede calcular.",
        "remediacion": "Ejercicios de identificación de TODOS los datos necesarios antes de resolver.",
    },
    "sobre_especificacion": {
        "nombre": "Sobre-especificación del problema",
        "descripcion": "Cree que aportar más detalle (día, hora) siempre mejora la solución.",
        "explicacion": "Un buen análisis usa el conjunto MÍNIMO de datos; el exceso no aporta y complica.",
        "remediacion": "Actividad de 'dato mínimo suficiente': quitar datos hasta el conjunto necesario.",
    },
    # COMP-0.2
    "confunde_entrada_proceso": {
        "nombre": "Confunde entrada con proceso",
        "descripcion": "Cree que pedir los datos es el proceso.",
        "explicacion": "Pedir datos es la ENTRADA; el proceso es la operación que transforma esos datos.",
        "remediacion": "Descomponer varios problemas en Entrada / Proceso / Salida etiquetando cada paso.",
    },
    "confunde_salida_proceso": {
        "nombre": "Confunde salida con proceso",
        "descripcion": "Cree que mostrar el resultado es el proceso.",
        "explicacion": "Mostrar es la SALIDA; el proceso es el cálculo previo a mostrar.",
        "remediacion": "Diagramas E-P-S donde el estudiante ubica dónde termina el proceso y empieza la salida.",
    },
    "no_identifica_proceso": {
        "nombre": "No identifica la operación que resuelve el problema",
        "descripcion": "Elige un dato irrelevante como si fuera el proceso.",
        "explicacion": "El proceso es la operación central (sumar y dividir); registrar el nombre no resuelve nada.",
        "remediacion": "Actividad: '¿qué operación produce el resultado pedido?' en varios problemas.",
    },
    # COMP-1.1
    "variable_acumula": {
        "nombre": "La variable acumula sus valores",
        "descripcion": "Interpreta la variable como un contenedor histórico de todos sus valores.",
        "explicacion": "Una variable conserva SOLO su último valor asignado; el anterior se pierde.",
        "remediacion": "Animación donde la variable cambia de valor y el anterior desaparece.",
    },
    "variable_inmutable": {
        "nombre": "La variable no puede cambiar",
        "descripcion": "Cree que una variable es constante una vez asignada.",
        "explicacion": "Una variable puede reasignarse cuantas veces se quiera durante el programa.",
        "remediacion": "Ejemplos de reasignación paso a paso mostrando el valor actualizándose.",
    },
    "reasignacion_crea_variable": {
        "nombre": "Reasignar crea una variable nueva",
        "descripcion": "Cree que volver a asignar el mismo nombre genera otra variable.",
        "explicacion": "Es la MISMA variable; solo cambia su valor, no se crea otra.",
        "remediacion": "Visualizar la memoria: una sola 'caja' con nombre cuyo contenido cambia.",
    },
    # COMP-1.2
    "sin_distincion_tipos": {
        "nombre": "No distingue tipos de dato",
        "descripcion": "Cree que texto y número son lo mismo; las comillas no importan.",
        "explicacion": "\"5\" (texto) y 5 (número) son tipos distintos y el programa los opera distinto.",
        "remediacion": "Ejemplos contrastados de operaciones con texto vs. con número.",
    },
    "tipo_invertido": {
        "nombre": "Invierte la noción de tipo",
        "descripcion": "Cree que las comillas convierten en número y su ausencia en texto.",
        "explicacion": "Es al revés: las comillas indican TEXTO; sin comillas, un número es NÚMERO.",
        "remediacion": "Tarjetas de clasificación: marcar cuáles valores son texto y cuáles número.",
    },
    "diferencia_superficial": {
        "nombre": "Atribuye la diferencia a un detalle superficial",
        "descripcion": "Cree que la diferencia depende de dónde aparece cada valor en la línea, no de las comillas.",
        "explicacion": "La diferencia es de TIPO de dato, no de la posición en que se escribe.",
        "remediacion": "Comparar pares valor-texto / valor-número y nombrar la diferencia real.",
    },
    # COMP-2.1
    "confunde_calcular_mostrar": {
        "nombre": "Confunde calcular con mostrar",
        "descripcion": "Cree que un código que calcula también muestra en pantalla.",
        "explicacion": "Calcular guarda un valor; mostrar requiere print. Aquí no hay print.",
        "remediacion": "Contrastar código que solo calcula vs. código que además imprime.",
    },
    "no_sigue_flujo": {
        "nombre": "No sigue el flujo del código",
        "descripcion": "Lee las líneas sueltas sin ver que se encadenan.",
        "explicacion": "Cada línea usa el resultado de la anterior: es un solo cálculo, no tres precios.",
        "remediacion": "Trazado guiado línea por línea siguiendo el valor de cada variable.",
    },
    "reuso_variable_es_error": {
        "nombre": "Reusar una variable es error",
        "descripcion": "Cree que usar la misma variable varias veces provoca un error.",
        "explicacion": "Una variable puede leerse y reutilizarse tantas veces como haga falta.",
        "remediacion": "Ejemplos donde una variable se reutiliza correctamente en varios cálculos.",
    },
    # COMP-2.2
    "ignora_condicion": {
        "nombre": "Ignora la condición",
        "descripcion": "Cree que siempre se ejecuta la primera rama, sin evaluar el if.",
        "explicacion": "El if elige la rama según la condición; no siempre corre la primera.",
        "remediacion": "Trazar el if con distintos valores de la variable y ver qué rama se toma.",
    },
    "confunde_comparacion_operacion": {
        "nombre": "Confunde comparación con operación aritmética",
        "descripcion": "Interpreta 'edad >= 18' como una suma o cálculo.",
        "explicacion": "Los comparadores (>=, >, ==) devuelven verdadero/falso, no un número.",
        "remediacion": "Actividad de comparadores: evaluar comparaciones a Verdadero/Falso.",
    },
    "ambas_ramas_ejecutan": {
        "nombre": "Cree que if y else se ejecutan ambos",
        "descripcion": "Piensa que se muestran los dos mensajes.",
        "explicacion": "Solo se ejecuta UNA rama: la del if o la del else, nunca las dos.",
        "remediacion": "Simulación visual: resaltar la única rama tomada según la condición.",
    },
    # COMP-3.1
    "no_actualiza_variable": {
        "nombre": "No actualiza el valor de la variable",
        "descripcion": "Cree que x conserva su valor original tras x = x + y.",
        "explicacion": "x = x + y reemplaza x por el nuevo valor (8), no mantiene el 5.",
        "remediacion": "Trazado de reasignación con acumulador mostrando el valor que cambia.",
    },
    "suma_es_concatenacion": {
        "nombre": "Suma como si fueran textos",
        "descripcion": "Cree que 5 + 3 pega los dígitos y da 53.",
        "explicacion": "Con números, + suma; solo con texto pega. 5 y 3 son números → 8.",
        "remediacion": "Contrastar 5 + 3 (números) vs. \"5\" + \"3\" (textos).",
    },
    "confunde_operador": {
        "nombre": "Confunde el operador",
        "descripcion": "Interpreta + como multiplicación (5 × 3 = 15).",
        "explicacion": "+ es suma; la multiplicación se escribe con *.",
        "remediacion": "Repaso de operadores con ejemplos de + y * lado a lado.",
    },
    # COMP-3.2
    "texto_como_numero": {
        "nombre": "Trata el texto como número",
        "descripcion": "Cree que \"5\" + \"5\" suma y da 10.",
        "explicacion": "Con texto, + concatena: \"5\" + \"5\" produce \"55\", no 10.",
        "remediacion": "Ejemplos de concatenación de textos y su contraste con suma de números.",
    },
    "concatenacion_texto_es_error": {
        "nombre": "Sumar textos es error",
        "descripcion": "Cree que \"5\" + \"5\" da error.",
        "explicacion": "Sumar dos textos es válido: los une (concatena) en \"55\".",
        "remediacion": "Actividad de concatenación de palabras y números-texto.",
    },
    "ignora_segunda_variable": {
        "nombre": "Ignora una de las variables",
        "descripcion": "Solo considera la primera variable y responde 5.",
        "explicacion": "La operación usa a Y b; el resultado combina ambas: \"55\".",
        "remediacion": "Trazado que resalta el uso de todas las variables en la expresión.",
    },
    # COMP-4.1
    "ignora_prerrequisitos": {
        "nombre": "Ignora los prerrequisitos del orden",
        "descripcion": "Pide el monto antes de insertar la tarjeta.",
        "explicacion": "No se puede operar sin insertar primero la tarjeta: hay pasos previos obligatorios.",
        "remediacion": "Ordenar algoritmos donde cada paso depende de uno anterior.",
    },
    "orden_parcial_incorrecto": {
        "nombre": "Invierte pasos de autenticación y operación",
        "descripcion": "Pone el monto antes del PIN.",
        "explicacion": "Primero se autentica (PIN) y luego se opera (monto); el orden importa.",
        "remediacion": "Actividades de secuenciación con dependencias explícitas.",
    },
    "inicio_incorrecto": {
        "nombre": "Empieza por un paso que no es el inicial",
        "descripcion": "Empieza por el PIN sin haber insertado la tarjeta.",
        "explicacion": "Todo algoritmo tiene un primer paso obligatorio; aquí es insertar la tarjeta.",
        "remediacion": "Identificar el paso inicial correcto antes de ordenar el resto.",
    },
    # COMP-4.2
    "procesa_sin_datos": {
        "nombre": "Procesa antes de tener los datos",
        "descripcion": "Calcula el promedio antes de pedir las notas.",
        "explicacion": "No se puede calcular sin datos: primero la entrada, luego el proceso.",
        "remediacion": "Ordenar algoritmos siguiendo el flujo Entrada → Proceso → Salida.",
    },
    "muestra_antes_de_calcular": {
        "nombre": "Muestra antes de calcular",
        "descripcion": "Muestra el promedio antes de haberlo calculado.",
        "explicacion": "La salida va al final: no se puede mostrar un resultado que aún no existe.",
        "remediacion": "Actividad: ubicar la salida siempre después del proceso.",
    },
    "orden_invertido": {
        "nombre": "Invierte todo el flujo",
        "descripcion": "Empieza mostrando y termina pidiendo datos.",
        "explicacion": "El flujo natural es Entrada → Proceso → Salida, no al revés.",
        "remediacion": "Reordenar de cero varios algoritmos con el esquema E-P-S.",
    },
    # COMP-5.1
    "sintaxis_de_otro_lenguaje": {
        "nombre": "Aplica sintaxis de otro lenguaje",
        "descripcion": "Cree que falta un punto y coma como en C o Java.",
        "explicacion": "Python no usa ; al final de línea; el error es otro (variable inexistente).",
        "remediacion": "Repaso de la sintaxis básica de Python vs. otros lenguajes.",
    },
    "print_solo_texto": {
        "nombre": "print solo muestra texto literal",
        "descripcion": "Cree que print no puede usar variables.",
        "explicacion": "print sí muestra variables; el error es que la variable estaba mal escrita.",
        "remediacion": "Ejemplos de print con variables correctamente escritas.",
    },
    "numeros_necesitan_comillas": {
        "nombre": "Los números necesitan comillas",
        "descripcion": "Cree que 100 debería ir entre comillas.",
        "explicacion": "Los números van SIN comillas; las comillas son para texto.",
        "remediacion": "Clasificar valores en texto (con comillas) y números (sin comillas).",
    },
    # COMP-5.2
    "requiere_else": {
        "nombre": "Todo if necesita else",
        "descripcion": "Cree que el error es la falta de un else.",
        "explicacion": "Un if puede existir sin else; el error real es el comparador (> en vez de >=).",
        "remediacion": "Ejemplos de if sin else válidos y foco en los límites del comparador.",
    },
    "nombre_irrelevante": {
        "nombre": "Atribuye el error al nombre de la variable",
        "descripcion": "Cree que edad debería llevar mayúscula.",
        "explicacion": "El nombre es correcto; el error está en la condición, no en el nombre.",
        "remediacion": "Depurar centrando la atención en la lógica de la condición.",
    },
    "orden_print_if": {
        "nombre": "No entiende que el print depende de la condición",
        "descripcion": "Cree que el print debería ir antes del if.",
        "explicacion": "El print está dentro del if a propósito: solo corre si la condición es verdadera.",
        "remediacion": "Trazar el if con valores límite (18) y ver por qué no entra.",
    },
}


def _question_id(item: dict) -> str:
    """ID determinista por curso+versión+competencia+orden: re-seedear nunca
    duplica. La clave única es (topic, order): en v2 el module_number es el
    contenido y lo comparten varias competencias, por eso no sirve como clave."""
    seed = f"{BANK_COURSE_CODE}:v{BANK_VERSION}:{item['topic']}:o{item['order']}"
    return str(uuid.uuid5(_NAMESPACE, seed))


def mental_model_for(topic: str, order: int, selected_index: int) -> dict | None:
    """Devuelve la entrada del catálogo para la opción elegida en un ítem, o None
    si la opción es la correcta / no tiene modelo mental. Lo usa el evaluador."""
    mapping = MENTAL_MODELS_BY_COMPETENCY.get((topic, order))
    if not mapping:
        return None
    model_id = mapping.get(selected_index)
    if model_id is None:
        return None
    entry = MENTAL_MODEL_CATALOG.get(model_id)
    if entry is None:
        return None
    return {"mental_model_id": model_id, **entry}


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
