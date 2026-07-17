"""
D4.2 — Biblioteca de contenido multimodal para Fundamentos de la Programación.
MVP: 4 temas × 5 tipos de contenido.
Temas: variables, conditionals, loops, functions.
Tipos: theory, example, exercise, game*, simulation*
(*) game y simulation son placeholders para Code Lab D4.3.
"""

# Orden de render por modalidad — tabla de PRESENTACIÓN, no de decisión
# (heredada del motor D4.1 al retirarlo): la modalidad la decide el
# Runtime; esto solo dice en qué orden se muestran los bloques.
# "visual"/"mixta" son el vocabulario del Runtime (DISENO_POR_ACCION);
# las claves VARK se conservan para contenido histórico.
MODALITY_CONTENT_ORDER: dict[str, list[str]] = {
    "visual": ["diagram", "example", "video", "theory", "exercise", "simulation", "game"],
    "mixta": ["theory", "diagram", "example", "exercise", "video", "simulation", "game"],
    "reading": ["theory", "example", "exercise", "diagram", "video", "simulation", "game"],
    "audio": ["video", "theory", "example", "exercise", "diagram", "simulation", "game"],
    "kinesthetic": ["game", "simulation", "exercise", "example", "theory", "video", "diagram"],
}

# ── Contenido educativo ────────────────────────────────────────────────────────

_LIBRARY: dict[str, dict[str, dict]] = {

    "variables": {
        "theory": {
            "type": "theory",
            "title": "¿Qué es una variable?",
            "body": (
                "Una variable es un espacio en la memoria del computador que guarda un valor con un nombre. "
                "En Python declaras una variable simplemente asignándole un valor: `edad = 18`. "
                "Python detecta el tipo automáticamente.\n\n"
                "**Tipos de datos básicos:**\n"
                "- `int` — números enteros: `edad = 18`\n"
                "- `float` — decimales: `precio = 9.99`\n"
                "- `str` — texto: `nombre = \"Ana\"`\n"
                "- `bool` — verdadero/falso: `activo = True`\n\n"
                "**Reglas para nombres:**\n"
                "- Deben comenzar con letra o guión bajo\n"
                "- Sin espacios (usa guión bajo: `nombre_completo`)\n"
                "- Sensibles a mayúsculas: `Edad` ≠ `edad`"
            ),
            "language": None,
            "code": None,
            "estimated_minutes": 5,
        },
        "example": {
            "type": "example",
            "title": "Variables en acción",
            "body": "Observa cómo se declaran y usan variables de distintos tipos en Python.",
            "code": (
                "# Declaración de variables\n"
                "nombre = \"María\"\n"
                "edad = 20\n"
                "promedio = 14.5\n"
                "aprobado = True\n\n"
                "# Usando f-strings para mostrar valores\n"
                "print(f\"Estudiante: {nombre}\")\n"
                "print(f\"Edad: {edad} años\")\n"
                "print(f\"Promedio: {promedio}\")\n"
                "print(f\"¿Aprobó?: {aprobado}\")\n\n"
                "# Reasignación — el valor puede cambiar\n"
                "promedio = 15.0\n"
                "print(f\"Nuevo promedio: {promedio}\")\n\n"
                "# Intercambio de valores en una línea (Python)\n"
                "a, b = 5, 10\n"
                "a, b = b, a\n"
                "print(f\"a={a}, b={b}\")  # a=10, b=5"
            ),
            "language": "python",
            "estimated_minutes": 7,
        },
        "exercise": {
            "type": "exercise",
            "title": "Practica: tus propias variables",
            "body": (
                "**Desafío 1 — Tus datos:**\n"
                "Declara 4 variables: `nombre`, `edad`, `carrera` y `aprobado`. "
                "Imprime un mensaje con todas ellas usando una sola línea con f-string.\n\n"
                "**Desafío 2 — Tipos correctos:**\n"
                "Para cada caso indica qué tipo de variable usarías (int, float, str, bool):\n"
                "a) El precio de un producto en soles\n"
                "b) El nombre de una ciudad\n"
                "c) La cantidad de alumnos en el salón\n"
                "d) Si hoy es lunes\n\n"
                "**Desafío 3 — Intercambio:**\n"
                "Tienes `a = 5` y `b = 10`. Intercambia sus valores usando una sola línea. "
                "Luego hazlo usando una variable temporal para entender por qué la forma de Python es elegante."
            ),
            "code": None,
            "language": None,
            "estimated_minutes": 10,
        },
        "game": {
            "type": "game",
            "title": "Captura el tipo correcto",
            "body": (
                "Arrastra cada valor hacia el contenedor del tipo de dato correcto: "
                "`int`, `float`, `str` o `bool`.\n\n"
                "💡 Este ejercicio interactivo estará disponible en el Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 8,
        },
        "simulation": {
            "type": "simulation",
            "title": "Simulador de memoria",
            "body": (
                "Visualiza en tiempo real cómo Python reserva espacio en memoria "
                "cuando declaras una variable y cómo cambia al reasignarla.\n\n"
                "💡 Esta simulación visual estará disponible en el Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 8,
        },
    },

    "conditionals": {
        "theory": {
            "type": "theory",
            "title": "Tomando decisiones con if / elif / else",
            "body": (
                "Las condicionales permiten que tu programa ejecute bloques de código "
                "solo si se cumple una condición.\n\n"
                "**Estructura básica:**\n"
                "```\n"
                "if condición:\n"
                "    # bloque si es verdadero\n"
                "elif otra_condición:\n"
                "    # bloque alternativo\n"
                "else:\n"
                "    # bloque si todo lo anterior es falso\n"
                "```\n\n"
                "**Operadores de comparación:** `==`, `!=`, `>`, `<`, `>=`, `<=`\n\n"
                "**Operadores lógicos:**\n"
                "- `and` — ambas condiciones deben ser verdaderas\n"
                "- `or` — al menos una debe ser verdadera\n"
                "- `not` — invierte la condición"
            ),
            "code": None,
            "language": None,
            "estimated_minutes": 5,
        },
        "example": {
            "type": "example",
            "title": "Clasificando notas",
            "body": "Ejemplo completo de condicionales encadenadas para clasificar notas del sistema vigesimal.",
            "code": (
                "nota = 14\n\n"
                "# Condicional simple\n"
                "if nota >= 11:\n"
                "    print(\"Aprobado ✓\")\n"
                "else:\n"
                "    print(\"Desaprobado ✗\")\n\n"
                "# Múltiples condiciones con elif\n"
                "if nota >= 18:\n"
                "    calificacion = \"Excelente\"\n"
                "elif nota >= 14:\n"
                "    calificacion = \"Bueno\"\n"
                "elif nota >= 11:\n"
                "    calificacion = \"Suficiente\"\n"
                "else:\n"
                "    calificacion = \"Desaprobado\"\n\n"
                "print(f\"Calificación: {calificacion}\")\n\n"
                "# Condición compuesta con and\n"
                "edad = 20\n"
                "tiene_dni = True\n\n"
                "if edad >= 18 and tiene_dni:\n"
                "    print(\"Puede votar\")\n"
                "else:\n"
                "    print(\"No cumple los requisitos\")"
            ),
            "language": "python",
            "estimated_minutes": 7,
        },
        "exercise": {
            "type": "exercise",
            "title": "Practica: decisiones en código",
            "body": (
                "**Desafío 1 — Clasificador de notas:**\n"
                "Escribe un programa que pida una nota (0-20) y la clasifique como:\n"
                "Excelente (18-20), Muy bueno (15-17), Bueno (11-14), Desaprobado (0-10).\n\n"
                "**Desafío 2 — Par o impar:**\n"
                "Dado un número entero, determina si es par o impar. "
                "Pista: usa el operador módulo `%`.\n\n"
                "**Desafío 3 — Calculadora de descuento:**\n"
                "Un cliente obtiene 20% de descuento si su compra supera S/. 100 "
                "O si tiene tarjeta VIP. Escribe el código para calcular el precio final."
            ),
            "code": None,
            "language": None,
            "estimated_minutes": 12,
        },
        "game": {
            "type": "game",
            "title": "El árbol de decisiones",
            "body": (
                "Construye un árbol de decisiones visual arrastrando condiciones `if`/`elif`/`else`. "
                "El sistema valida si el flujo lógico es correcto.\n\n"
                "💡 Disponible próximamente en Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 10,
        },
        "simulation": {
            "type": "simulation",
            "title": "Traza de ejecución condicional",
            "body": (
                "Paso a paso: observa qué rama del `if` se ejecuta según el valor de entrada "
                "y cómo el intérprete salta las ramas que no se cumplen.\n\n"
                "💡 Disponible próximamente en Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 8,
        },
    },

    "loops": {
        "theory": {
            "type": "theory",
            "title": "Bucles: repite sin repetirte",
            "body": (
                "Un bucle ejecuta el mismo bloque de código múltiples veces sin que lo escribas de nuevo.\n\n"
                "**for** — cuando sabes cuántas veces repetir:\n"
                "```python\n"
                "for i in range(5):   # 0, 1, 2, 3, 4\n"
                "    print(i)\n"
                "```\n\n"
                "**while** — mientras una condición sea verdadera:\n"
                "```python\n"
                "while condición:\n"
                "    # bloque que se repite\n"
                "```\n\n"
                "**Control de bucles:**\n"
                "- `break` — sale del bucle inmediatamente\n"
                "- `continue` — salta a la siguiente iteración\n"
                "- `range(inicio, fin, paso)` — genera secuencias de números\n\n"
                "**Patrón acumulador:** declara una variable antes del bucle y actualízala en cada vuelta."
            ),
            "code": None,
            "language": None,
            "estimated_minutes": 6,
        },
        "example": {
            "type": "example",
            "title": "Patrones con for y while",
            "body": "Ejemplos clave: recorrer listas, acumuladores y control de flujo con break/continue.",
            "code": (
                "# for con range — del 1 al 5\n"
                "for i in range(1, 6):\n"
                "    print(i)\n\n"
                "# for con lista\n"
                "frutas = [\"manzana\", \"pera\", \"uva\"]\n"
                "for fruta in frutas:\n"
                "    print(f\"Fruta: {fruta}\")\n\n"
                "# Acumulador: suma del 1 al 10\n"
                "suma = 0\n"
                "for n in range(1, 11):\n"
                "    suma += n\n"
                "print(f\"Suma: {suma}\")  # 55\n\n"
                "# while con contador\n"
                "intentos = 0\n"
                "while intentos < 3:\n"
                "    print(f\"Intento {intentos + 1}\")\n"
                "    intentos += 1\n\n"
                "# break y continue\n"
                "for i in range(10):\n"
                "    if i == 3:\n"
                "        continue   # salta el 3\n"
                "    if i == 7:\n"
                "        break      # detiene en 7\n"
                "    print(i)       # imprime 0,1,2,4,5,6"
            ),
            "language": "python",
            "estimated_minutes": 8,
        },
        "exercise": {
            "type": "exercise",
            "title": "Practica: bucles en problemas reales",
            "body": (
                "**Desafío 1 — Tabla de multiplicar:**\n"
                "Muestra la tabla de multiplicar de cualquier número (del 1 al 12) "
                "usando un `for` y `range`.\n\n"
                "**Desafío 2 — Suma de impares:**\n"
                "Calcula la suma de todos los números impares entre 1 y 100. "
                "Usa `range` con el parámetro `step`.\n\n"
                "**Desafío 3 — Adivina el número:**\n"
                "El programa tiene el número secreto 42. El usuario adivina con `while` "
                "e intentos ilimitados. Muestra 'Mayor' o 'Menor' en cada intento "
                "y felicita cuando acierta."
            ),
            "code": None,
            "language": None,
            "estimated_minutes": 15,
        },
        "simulation": {
            "type": "simulation",
            "title": "Visualizador de bucles",
            "body": (
                "Observa frame a frame cómo el contador del bucle cambia de valor "
                "y cuándo se ejecuta cada instrucción. Ajusta `range` con sliders "
                "y ve el resultado en tiempo real.\n\n"
                "💡 Disponible próximamente en Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 10,
        },
        "game": {
            "type": "game",
            "title": "Laberinto de bucles",
            "body": (
                "Programa un robot para que recorra un laberinto usando `for` y `while`. "
                "Cada celda que pisar equivale a una iteración. "
                "Encuentra la salida con el menor número de pasos.\n\n"
                "💡 Disponible próximamente en Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 12,
        },
    },

    "functions": {
        "theory": {
            "type": "theory",
            "title": "Funciones: código reutilizable",
            "body": (
                "Una función es un bloque de código con nombre. Lo defines una vez, "
                "lo llamas las veces que necesites.\n\n"
                "**Definición:**\n"
                "```python\n"
                "def nombre(parámetros):\n"
                "    # cuerpo\n"
                "    return resultado\n"
                "```\n\n"
                "**Conceptos clave:**\n"
                "- **Parámetros**: variables que la función recibe al ser llamada\n"
                "- **Argumentos**: los valores reales que le pasas\n"
                "- **return**: valor que devuelve la función (sin `return` devuelve `None`)\n"
                "- **Alcance**: las variables dentro de una función no existen fuera\n\n"
                "**Por qué usar funciones:**\n"
                "- Evitas repetir código (principio DRY: Don't Repeat Yourself)\n"
                "- Divides un problema grande en piezas pequeñas\n"
                "- El código es más fácil de leer y probar"
            ),
            "code": None,
            "language": None,
            "estimated_minutes": 6,
        },
        "example": {
            "type": "example",
            "title": "Funciones en Fundamentos",
            "body": "Desde funciones simples sin parámetros hasta funciones que llaman a otras funciones.",
            "code": (
                "# Función sin parámetros\n"
                "def saludar():\n"
                "    print(\"¡Hola, estudiante!\")\n\n"
                "saludar()   # llamada\n\n"
                "# Función con parámetros y return\n"
                "def calcular_promedio(nota1, nota2, nota3):\n"
                "    suma = nota1 + nota2 + nota3\n"
                "    return suma / 3\n\n"
                "resultado = calcular_promedio(14, 16, 18)\n"
                "print(f\"Promedio: {resultado:.1f}\")\n\n"
                "# Parámetro con valor por defecto\n"
                "def describir_nota(nota, sistema=\"vigesimal\"):\n"
                "    if sistema == \"vigesimal\":\n"
                "        return \"Aprobado\" if nota >= 11 else \"Desaprobado\"\n"
                "    return \"Aprobado\" if nota >= 60 else \"Desaprobado\"\n\n"
                "print(describir_nota(14))              # vigesimal\n"
                "print(describir_nota(65, \"centesimal\"))\n\n"
                "# Función que llama a otra función\n"
                "def es_primo(n):\n"
                "    if n < 2:\n"
                "        return False\n"
                "    for i in range(2, int(n**0.5) + 1):\n"
                "        if n % i == 0:\n"
                "            return False\n"
                "    return True\n\n"
                "primos = [n for n in range(2, 20) if es_primo(n)]\n"
                "print(f\"Primos hasta 20: {primos}\")"
            ),
            "language": "python",
            "estimated_minutes": 8,
        },
        "exercise": {
            "type": "exercise",
            "title": "Practica: escribe tus funciones",
            "body": (
                "**Desafío 1 — Convertidor de temperatura:**\n"
                "Define `celsius_a_fahrenheit(celsius)` que retorne la temperatura convertida. "
                "Fórmula: `F = (C × 9/5) + 32`. Pruébala con 0°C, 100°C y 37°C.\n\n"
                "**Desafío 2 — Factorial:**\n"
                "Define `factorial(n)` que calcule n! usando un bucle `for` (sin recursión todavía). "
                "Ejemplo: `factorial(5)` → 120.\n\n"
                "**Desafío 3 — Calculadora modular:**\n"
                "Define 4 funciones: `sumar`, `restar`, `multiplicar`, `dividir`. "
                "Cada una recibe dos números y retorna el resultado. "
                "`dividir` debe retornar `None` y mostrar un mensaje si el divisor es cero."
            ),
            "code": None,
            "language": None,
            "estimated_minutes": 15,
        },
        "game": {
            "type": "game",
            "title": "Constructor de funciones",
            "body": (
                "Arma una función arrastrando piezas: nombre, parámetros, cuerpo y return. "
                "El sistema verifica que la función resuelva el problema planteado.\n\n"
                "💡 Disponible próximamente en Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 12,
        },
        "simulation": {
            "type": "simulation",
            "title": "Pila de llamadas (call stack)",
            "body": (
                "Visualiza cómo Python apila y desapila funciones en memoria cuando "
                "una función llama a otra. Observa el flujo de parámetros y valores de retorno.\n\n"
                "💡 Disponible próximamente en Code Lab."
            ),
            "code": None,
            "language": None,
            "is_placeholder": True,
            "placeholder_sprint": "D4.3 — Code Lab",
            "estimated_minutes": 10,
        },
    },
}

# ── Función principal ──────────────────────────────────────────────────────────

AVAILABLE_TOPICS = list(_LIBRARY.keys())

CONTENT_TYPE_LABELS_ES = {
    "theory":     "Teoría",
    "example":    "Ejemplo",
    "exercise":   "Ejercicio",
    "game":       "Juego",
    "simulation": "Simulación",
}


def get_adaptive_content(topic_slug: str, modality: str) -> list[dict]:
    """
    Returns the content blocks for a topic, ordered by the student's dominant modality.
    Blocks not in content_order are appended at the end.
    """
    topic_content = _LIBRARY.get(topic_slug)
    if not topic_content:
        return []

    order = MODALITY_CONTENT_ORDER.get(modality, MODALITY_CONTENT_ORDER["mixta"])
    ordered_blocks = []
    for content_type in order:
        block = topic_content.get(content_type)
        if block:
            ordered_blocks.append(block)

    # Append any types not in the modality order (shouldn't happen with 5 canonical types,
    # but guards against future additions)
    seen = set(order)
    for content_type, block in topic_content.items():
        if content_type not in seen:
            ordered_blocks.append(block)

    return ordered_blocks
