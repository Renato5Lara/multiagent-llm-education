"""
Banco del instrumento de diagnóstico de entrada (pre/post-test) — BANK_VERSION 4.

8 ítems MCQ que evalúan SOLO el Módulo 1 de Fundamentos, organizados por las tres
funciones nucleares de M1 (concebir 2 ítems, representar 2, ejecutar 4) sobre
cuatro competencias del modelo cognitivo: COMP-0, COMP-2, COMP-3 y COMP-5, con
dos ítems cada una. COMP-1 y COMP-4 dejan de medirse en esta versión. Pre-Test y
Post-Test usan el MISMO banco, el de la versión con que el estudiante rindió el
Pre-Test (comparabilidad → ganancia por competencia = post − pre). M1.6
(declarativo) queda fuera de la afirmación diagnóstica; ningún ítem evidencia M2+.

Especificación normativa: docs/architecture/DESIGN-banco-diagnostico-m1.md. Su
§13 es la tabla de mapeo que implementa ITEM_MAPPING, y su §7 son los invariantes
que comprueba tests/test_knowledge_test_bank_v4.py.

Dimensiones (campos existentes del modelo, sin tablas nuevas):
    topic         → competencia (comp_0, comp_2, comp_3, comp_5)
    module_number → 1 en todos los ítems (el banco es de M1)
    bloom_level   → profundidad cognitiva; OBLIGATORIO en v4
    order         → posición de servicio GLOBAL (0 a 7), única en el banco. Con
                    (topic, order) forma la identidad del ítem.

Sin modelos mentales: v4 no declara `mental_models` (cada ítem lleva `{}`); la
misconcepción de cada distractor se documenta como comentario. El catálogo
MENTAL_MODEL_CATALOG de versiones anteriores no se usa en v4.

Alternativas multilínea (pseudocódigo, diagramas de flujo, salida de programas):
el frontend las muestra con white-space: pre-line (KnowledgeTest.tsx), por lo que
este banco solo puede activarse con ese frontend ya desplegado.

El seed es idempotente: IDs deterministas (uuid5 por curso+versión+competencia+
orden). Las filas de versiones anteriores no se tocan. El LLM no participa en la
construcción del instrumento.

Changelog BANK_VERSION 3 → 4 (rediseño a M1, ver la especificación): los 12 ítems
de v3 quedaban atribuidos por `module_number` a M1, M2 y M4, y solo 4 evaluaban
realmente M1. v4 los reemplaza por 8 ítems 100 % de M1 con cobertura por función.
Ningún ítem de v3 se reutiliza.

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

BANK_VERSION = 4
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
#
# v4 NO declara modelos mentales (decisión M): cada ítem lleva `{}`. La
# misconcepción que evidencia cada distractor se documenta en el comentario de
# la opción. `order` es la posición de servicio GLOBAL (0 a 7, decisión O = B):
# el ítem 7 (sintaxis sin `print`) se sirve antes que los que muestran `print`.


def _pseudocodigo(*pasos: str) -> str:
    return "\n".join(["INICIO", *pasos, "FIN"])


def _diagrama(
    entrada: str = "/ Pedir una frase /",
    proceso: str = "[ Contar las palabras de la frase ]",
    con_fin: bool = True,
) -> str:
    """Diagrama de flujo textual: ( ) inicio/fin, [ ] acción, / / entrada o
    salida de datos, ↓ sentido del flujo. Cada variante cambia UN elemento."""
    lineas = ["( Inicio )", "↓", entrada, "↓", proceso, "↓", "/ Mostrar la cantidad de palabras /"]
    if con_fin:
        lineas += ["↓", "( Fin )"]
    return "\n".join(lineas)


_PROGRAMA_SALUDOS = (
    'print("Buenos días")\n'
    'print("Bienvenido al curso")\n'
    'print("Hasta pronto")'
)
_PROGRAMA_COMENTARIOS = (
    "# Saludo inicial\n"
    'print("Hola")\n'
    "\n"
    '# print("Este mensaje es de prueba")\n'
    'print("Adiós")'
)
_PROGRAMA_SIN_CIERRE = 'print("Gracias por venir)'
_PROGRAMA_SIN_PARENTESIS = 'print("Buenas tardes")\nprint "Hasta luego"'

DIAGNOSTIC_ITEMS: list[dict] = [
    # ══ Concebir la solución (COMP-0) · M1.1 y M1.2 ═══════════════════════════
    {   # Ítem 1 · Concebir · éxito evidencia M1.1
        "module_number": 1, "topic": COMP_0, "difficulty": "basico", "bloom_level": 2, "order": 0,
        "text": (
            "Tienes agua, una bolsita de té y una taza vacía, y quieres obtener "
            "una taza de té lista para tomar. ¿Cuál de estas descripciones es un "
            "algoritmo que resuelve ese problema?"
        ),
        "options": [
            # Describe el objetivo, no el procedimiento.
            "Lograr una taza de té con el sabor y la temperatura ideales, de "
            "modo que quede lista para quien la va a tomar.",
            # Pasos precisos pero sin fin: vuelve al paso 1.
            "1. Hervir 250 ml de agua. 2. Poner una bolsita de té en la taza. "
            "3. Verter el agua en la taza. 4. Volver al paso 1.",
            "1. Hervir 250 ml de agua. 2. Poner una bolsita de té en la taza. "
            "3. Verter el agua en la taza. 4. Esperar 3 minutos y sacar la bolsita.",
            # Pasos imprecisos y dependientes del criterio de quien los sigue.
            "1. Hervir agua. 2. Echar más o menos té en la taza. 3. Verter agua "
            "caliente, un poco. 4. Esperar un rato y retirar el té si parece listo.",
        ],
        "correct_index": 2,
        "mental_models": {},
    },
    {   # Ítem 2 · Concebir · éxito evidencia M1.2 (y M1.1)
        "module_number": 1, "topic": COMP_0, "difficulty": "intermedio", "bloom_level": 3, "order": 1,
        "text": (
            "Un colegio quiere una aplicación que, al abrirla, muestre a cada "
            "estudiante las clases que tiene ese día, de la primera a la última. "
            "Cada clase tiene su curso, su aula y su hora de inicio. Además, el "
            "escudo del colegio es azul y dorado. Antes de programar, un equipo "
            "divide el problema en estas partes: 1. Saber qué día es hoy. "
            "2. Reunir las clases que el estudiante tiene ese día. 3. Mostrar "
            "las clases en pantalla. Falta una parte necesaria para resolver el "
            "problema. ¿Cuál es?"
        ),
        "options": [
            # Repite una parte que ya está (la 3).
            "Volver a mostrar las clases del día en la pantalla.",
            # Detalle del enunciado que no interviene en la solución.
            "Elegir los colores azul y dorado del escudo para la pantalla.",
            # Confunde descomponer el problema con escribir el código.
            "Escribir el código del programa en el computador.",
            "Poner las clases del día en orden según su hora de inicio.",
        ],
        "correct_index": 3,
        "mental_models": {},
    },
    # ══ Representar la solución (COMP-2) · M1.3 ═══════════════════════════════
    {   # Ítem 3 · Representar (pseudocódigo) · alternativas multilínea
        "module_number": 1, "topic": COMP_2, "difficulty": "basico", "bloom_level": 2, "order": 2,
        "text": (
            "Un algoritmo debe pedirle su nombre a un estudiante y luego "
            "mostrarle un mensaje de bienvenida que incluya ese nombre. ¿Cuál "
            "de estas representaciones en pseudocódigo corresponde a ese "
            "algoritmo?"
        ),
        "options": [
            _pseudocodigo(
                "Pedir el nombre del estudiante",
                "Armar un mensaje de bienvenida con ese nombre",
                "Mostrar el mensaje",
            ),
            # Muestra el mensaje antes de tener el nombre (orden invertido).
            _pseudocodigo(
                "Mostrar el mensaje de bienvenida",
                "Pedir el nombre del estudiante",
                "Armar un mensaje de bienvenida con ese nombre",
            ),
            # Omite el paso de entrada: nunca pide el nombre.
            _pseudocodigo(
                "Armar un mensaje de bienvenida con el nombre",
                "Mostrar el mensaje",
            ),
            # Muestra el nombre en vez del mensaje de bienvenida.
            _pseudocodigo(
                "Pedir el nombre del estudiante",
                "Armar un mensaje de bienvenida con ese nombre",
                "Mostrar el nombre",
            ),
        ],
        "correct_index": 0,
        "mental_models": {},
    },
    {   # Ítem 4 · Representar (diagrama de flujo) · alternativas multilínea
        "module_number": 1, "topic": COMP_2, "difficulty": "intermedio", "bloom_level": 2, "order": 3,
        "text": (
            "Un algoritmo debe pedir una frase, contar cuántas palabras tiene y "
            "mostrar esa cantidad. En los diagramas de flujo de abajo, ( ) marca "
            "el inicio y el fin, / / indica una entrada o una salida de datos, "
            "[ ] indica una acción y ↓ indica el sentido del flujo. ¿Cuál de los "
            "diagramas representa correctamente ese algoritmo?"
        ),
        "options": [
            # El proceso no es el que pide el enunciado (ordena en vez de contar).
            _diagrama(proceso="[ Ordenar las palabras de la frase ]"),
            _diagrama(),
            # Usa el símbolo de acción para una entrada de datos.
            _diagrama(entrada="[ Pedir una frase ]"),
            # El diagrama no termina: falta el símbolo de fin.
            _diagrama(con_fin=False),
        ],
        "correct_index": 1,
        "mental_models": {},
    },
    # ══ Ejecutar la solución (COMP-5 y COMP-3) · M1.4 y M1.5 ══════════════════
    {   # Ítem 7 · Ejecutar · sintaxis sin depender de print · éxito evidencia M1.4
        "module_number": 1, "topic": COMP_5, "difficulty": "intermedio", "bloom_level": 3, "order": 4,
        "text": (
            "En Python, la instrucción print muestra en pantalla el texto que se "
            "le indica.\n\nEste programa da error al ejecutarse:\n\n"
            + _PROGRAMA_SIN_CIERRE
            + "\n\n¿Cuál es la causa del error?"
        ),
        "options": [
            # Cree que hay un límite de longitud del texto por línea.
            "El texto es demasiado largo para una sola línea.",
            # Cree que las instrucciones de Python llevan mayúscula inicial.
            "La palabra print debe empezar con mayúscula.",
            "Falta cerrar las comillas al final del texto.",
            # Traslada la sintaxis de otro lenguaje (C, Java) a Python.
            "Falta un punto y coma al final de la línea.",
        ],
        "correct_index": 2,
        "mental_models": {},
    },
    {   # Ítem 8 · Ejecutar · depuración a nivel programa
        "module_number": 1, "topic": COMP_5, "difficulty": "intermedio", "bloom_level": 3, "order": 5,
        "text": (
            "Este programa da error al ejecutarse:\n\n"
            + _PROGRAMA_SIN_PARENTESIS
            + "\n\n¿Cuál es la causa del error?"
        ),
        "options": [
            # Cree que print solo puede aparecer una vez en un programa.
            "No se puede usar print dos veces en el mismo programa.",
            "La segunda línea no lleva paréntesis después de print.",
            # Cree que hace falta una línea vacía para separar instrucciones.
            "Falta una línea vacía entre las dos instrucciones.",
            # Atribuye el error a unas comillas que están bien escritas.
            "La primera línea está mal escrita porque el texto lleva comillas.",
        ],
        "correct_index": 1,
        "mental_models": {},
    },
    {   # Ítem 5 · Ejecutar · predecir la salida de un programa multilínea
        "module_number": 1, "topic": COMP_3, "difficulty": "intermedio", "bloom_level": 3, "order": 6,
        "text": (
            "¿Qué muestra este programa de Python en la pantalla al ejecutarse?\n\n"
            + _PROGRAMA_SALUDOS
        ),
        "options": [
            # Cree que print también muestra las comillas del código.
            '"Buenos días"\n"Bienvenido al curso"\n"Hasta pronto"',
            # Cree que las salidas de print se muestran seguidas, en una línea.
            "Buenos días Bienvenido al curso Hasta pronto",
            # Cree que las instrucciones se ejecutan de la última a la primera.
            "Hasta pronto\nBienvenido al curso\nBuenos días",
            "Buenos días\nBienvenido al curso\nHasta pronto",
        ],
        "correct_index": 3,
        "mental_models": {},
    },
    {   # Ítem 6 · Ejecutar · comentarios y línea en blanco
        "module_number": 1, "topic": COMP_3, "difficulty": "intermedio", "bloom_level": 3, "order": 7,
        "text": (
            "¿Qué muestra este programa de Python en la pantalla al ejecutarse?\n\n"
            + _PROGRAMA_COMENTARIOS
        ),
        "options": [
            "Hola\nAdiós",
            # Cree que un comentario también se muestra en pantalla.
            "Saludo inicial\nHola\nAdiós",
            # Cree que un print comentado se ejecuta igualmente.
            "Hola\nEste mensaje es de prueba\nAdiós",
            # Cree que la línea vacía del código aparece en la salida.
            "Hola\n\nAdiós",
        ],
        "correct_index": 0,
        "mental_models": {},
    },
]

# Mapeo función/concepto por ítem (§13 de DESIGN-banco-diagnostico-m1.md), con
# la clave canónica (competencia, orden). El modelo no tiene columnas para esto:
# vive aquí, sin cambio de esquema, y los tests comprueban los invariantes de
# cobertura contra él. `conceptos`: conceptos de M1 cuyo ÉXITO evidencia el ítem;
# `fallo`: conceptos a los que se atribuye el FALLO (vacío = ninguno automático).
ITEM_MAPPING: dict[tuple[str, int], dict] = {
    (COMP_0, 0): {"funcion": "concebir", "conceptos": ("M1.1",), "fallo": ("M1.1",), "etiquetas": ()},
    (COMP_0, 1): {"funcion": "concebir", "conceptos": ("M1.2", "M1.1"), "fallo": (), "etiquetas": ()},
    (COMP_2, 2): {"funcion": "representar", "conceptos": ("M1.3", "M1.1"), "fallo": (), "etiquetas": ("opciones_multilinea",)},
    (COMP_2, 3): {"funcion": "representar", "conceptos": ("M1.3", "M1.1"), "fallo": (), "etiquetas": ("opciones_multilinea",)},
    (COMP_5, 4): {"funcion": "ejecutar", "conceptos": ("M1.4",), "fallo": ("M1.4",), "etiquetas": ("sintaxis_sin_print",)},
    (COMP_5, 5): {"funcion": "ejecutar", "conceptos": ("M1.4", "M1.5"), "fallo": (), "etiquetas": ("nivel_programa",)},
    (COMP_3, 6): {"funcion": "ejecutar", "conceptos": ("M1.4", "M1.5"), "fallo": (), "etiquetas": ("nivel_programa", "opciones_multilinea")},
    (COMP_3, 7): {"funcion": "ejecutar", "conceptos": ("M1.4", "M1.5"), "fallo": (), "etiquetas": ("nivel_programa", "opciones_multilinea")},
}

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
