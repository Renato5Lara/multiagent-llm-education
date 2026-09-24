"""Catálogo de plantillas deterministas por concepto — cobertura de los
32 `Concept` del currículo IS301 (migración
`d6e7f8a9b0c1_migrate_is301_to_8_modules.py`, catálogo cerrado).

Corrige el hallazgo real del primer E2E (Concept "Bucle while"): sin
esta pieza, `CMGGenerationService` caía en el fallback genérico de
`ProgrammerAgent` (`resolver()` / "Completar solucion") para cualquier
concepto fuera de "arreglo/array/lista" — código y ejercicio sin
relación con el concepto, causa real de que D1/D3 fallaran.

Estrategia (§FASE 2 del encargo): `Concept → plantilla parametrizada →
CMG`, no `Concept → fallback genérico`. Las 32 entradas están
codificadas explícitamente (nunca generadas a partir del título de
forma automática) — cada una usa realmente la construcción del
lenguaje que el concepto nombra (while/for/if/función/lista/
recursividad/...), nunca el nombre del concepto como texto decorativo.

Claves: el `title` EXACTO de `Concept.title` tal como lo sembró la
migración — un cambio de redacción en el currículo real exige
actualizar esta clave, a propósito (fail-fast: `obtener_plantilla`
devuelve `None`, nunca una coincidencia parcial adivinada).
"""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True, slots=True)
class PlantillaConcepto:
    modulo: str  # "M1".."M8" — para la auditoría de cobertura por módulo
    code: str
    tests: str
    exercise_title: str
    exercise_prompt: str
    exercise_expected_outcome: str
    exercise_scaffolding: tuple[str, ...]


_CATALOGO: dict[str, PlantillaConcepto] = {
    # ── M1 — Introducción a la Programación ──────────────────────────
    "Algoritmo": PlantillaConcepto(
        modulo="M1",
        code=(
            "def suma_hasta(n):\n"
            "    total = 0\n"
            "    for numero in range(1, n + 1):\n"
            "        total += numero\n"
            "    return total\n"
        ),
        tests="assert suma_hasta(5) == 15\nassert suma_hasta(1) == 1\n",
        exercise_title="Diseñar el algoritmo antes de programar",
        exercise_prompt="Describe, paso a paso, el algoritmo que suma los números del 1 al n, antes de mirar el código.",
        exercise_expected_outcome="Una secuencia de pasos ordenada que termina en el total correcto.",
        exercise_scaffolding=("identificar la entrada", "identificar la salida esperada", "ordenar los pasos"),
    ),
    "Pensamiento computacional / proceso de resolución de problemas": PlantillaConcepto(
        modulo="M1",
        code=(
            "def encontrar_mayor(numeros):\n"
            "    mayor = numeros[0]\n"
            "    for numero in numeros[1:]:\n"
            "        if numero > mayor:\n"
            "            mayor = numero\n"
            "    return mayor\n"
        ),
        tests="assert encontrar_mayor([3, 7, 2]) == 7\nassert encontrar_mayor([-1, -5, -2]) == -1\n",
        exercise_title="Descomponer el problema",
        exercise_prompt="Aplica pensamiento computacional: divide el problema 'encontrar el mayor de una lista' en sub-pasos antes de escribir código.",
        exercise_expected_outcome="Sub-pasos: tomar un candidato inicial, comparar, actualizar, repetir.",
        exercise_scaffolding=("identificar el caso base", "identificar la comparación", "repetir hasta el final"),
    ),
    "Representación de algoritmos": PlantillaConcepto(
        modulo="M1",
        code=(
            "def procesar_promedio(notas):\n"
            "    # Paso 1: los datos ya llegan como lista\n"
            "    total = sum(notas)\n"
            "    # Paso 2: calcular el promedio\n"
            "    promedio = total / len(notas)\n"
            "    # Paso 3: devolver el resultado\n"
            "    return promedio\n"
        ),
        tests="assert procesar_promedio([10, 20, 30]) == 20\n",
        exercise_title="Traducir pasos a código",
        exercise_prompt="Escribe la representación en pseudocódigo del algoritmo que calcula un promedio, antes de traducirla a Python.",
        exercise_expected_outcome="3 pasos numerados que corresponden 1:1 con las líneas de código.",
        exercise_scaffolding=("escribir el pseudocódigo", "traducir cada paso", "verificar con un ejemplo"),
    ),
    "Estructura y sintaxis básica de un programa en Python": PlantillaConcepto(
        modulo="M1",
        code=(
            "def saludar(nombre):\n"
            "    mensaje = \"Hola, \" + nombre\n"
            "    return mensaje\n\n"
            "resultado = saludar(\"Ana\")\n"
        ),
        tests="assert saludar(\"Ana\") == \"Hola, Ana\"\nassert saludar(\"Luis\") == \"Hola, Luis\"\n",
        exercise_title="Identificar la estructura de un programa",
        exercise_prompt="Señala en la estructura de este programa Python: dónde está la sintaxis básica de la definición de función, dónde el cuerpo indentado y dónde la invocación.",
        exercise_expected_outcome="def marca el inicio, el bloque indentado es el cuerpo, saludar(\"Ana\") es la invocación.",
        exercise_scaffolding=("ubicar la definición", "ubicar el cuerpo indentado", "ubicar la invocación"),
    ),
    "Salida básica (print)": PlantillaConcepto(
        modulo="M1",
        code=(
            "def formatear_reporte(nombre, nota):\n"
            "    linea = f\"Estudiante: {nombre} - Nota: {nota}\"\n"
            "    print(linea)\n"
            "    return linea\n"
        ),
        tests="assert formatear_reporte(\"Ana\", 18) == \"Estudiante: Ana - Nota: 18\"\n",
        exercise_title="Formatear una salida con print",
        exercise_prompt="Usa print() con un f-string para mostrar el nombre y la nota de un estudiante.",
        exercise_expected_outcome="'Estudiante: Ana - Nota: 18' impreso en pantalla.",
        exercise_scaffolding=("armar el f-string", "llamar a print()"),
    ),
    "Qué es un lenguaje de programación": PlantillaConcepto(
        modulo="M1",
        code=(
            "def ejecutar_instrucciones(instrucciones):\n"
            "    resultado = 0\n"
            "    for instruccion in instrucciones:\n"
            "        if instruccion == \"sumar1\":\n"
            "            resultado += 1\n"
            "        elif instruccion == \"duplicar\":\n"
            "            resultado *= 2\n"
            "    return resultado\n"
        ),
        tests="assert ejecutar_instrucciones([\"sumar1\", \"sumar1\", \"duplicar\"]) == 4\n",
        exercise_title="Un programa es una secuencia de instrucciones",
        exercise_prompt="En este lenguaje de programación, predice el resultado de ejecutar [\"sumar1\", \"duplicar\", \"sumar1\"] instrucción por instrucción.",
        exercise_expected_outcome="0 -> 1 (sumar1) -> 2 (duplicar) -> 3 (sumar1) = 3",
        exercise_scaffolding=("ejecutar instrucción por instrucción", "llevar el resultado acumulado"),
    ),
    # ── M2 — Variables y Tipos de Datos ───────────────────────────────
    "Variables": PlantillaConcepto(
        modulo="M2",
        code=(
            "def actualizar_saldo(saldo_inicial, deposito):\n"
            "    saldo = saldo_inicial\n"
            "    saldo = saldo + deposito\n"
            "    return saldo\n"
        ),
        tests="assert actualizar_saldo(100, 50) == 150\n",
        exercise_title="Reasignar una variable",
        exercise_prompt="Explica qué valor tiene la variable 'saldo' antes y después de cada línea de la función.",
        exercise_expected_outcome="Antes: 100. Después de la suma: 150.",
        exercise_scaffolding=("identificar el valor inicial", "rastrear la reasignación"),
    ),
    "Tipos de datos primitivos": PlantillaConcepto(
        modulo="M2",
        code=(
            "def describir_tipo(valor):\n"
            "    if isinstance(valor, bool):\n"
            "        return \"bool\"\n"
            "    if isinstance(valor, int):\n"
            "        return \"int\"\n"
            "    if isinstance(valor, float):\n"
            "        return \"float\"\n"
            "    if isinstance(valor, str):\n"
            "        return \"str\"\n"
            "    return \"otro\"\n"
        ),
        tests=(
            "assert describir_tipo(5) == \"int\"\n"
            "assert describir_tipo(5.0) == \"float\"\n"
            "assert describir_tipo(\"cinco\") == \"str\"\n"
            "assert describir_tipo(True) == \"bool\"\n"
        ),
        exercise_title="Reconocer tipos de datos primitivos",
        exercise_prompt="Clasifica 5, 5.0, \"cinco\" y True según su tipo de dato primitivo.",
        exercise_expected_outcome="int, float, str, bool respectivamente.",
        exercise_scaffolding=("observar la forma del valor", "distinguir int de float", "distinguir bool de int"),
    ),
    "Entrada básica (input())": PlantillaConcepto(
        modulo="M2",
        code=(
            "def leer_edad(texto_ingresado):\n"
            "    # texto_ingresado representa lo que input() devolvería como string\n"
            "    edad = int(texto_ingresado)\n"
            "    return edad\n"
        ),
        tests="assert leer_edad(\"18\") == 18\nassert leer_edad(\"25\") == 25\n",
        exercise_title="input() siempre devuelve texto",
        exercise_prompt="Explica por qué int(input()) es necesario si se quiere sumar la edad ingresada.",
        exercise_expected_outcome="input() devuelve str; sin convertir, sumar produciría un error o concatenación.",
        exercise_scaffolding=("recordar que input() devuelve str", "convertir con int()"),
    ),
    "Conversión de tipos": PlantillaConcepto(
        modulo="M2",
        code=(
            "def convertir_a_numero(texto):\n"
            "    if \".\" in texto:\n"
            "        return float(texto)\n"
            "    return int(texto)\n"
        ),
        tests="assert convertir_a_numero(\"10\") == 10\nassert convertir_a_numero(\"3.5\") == 3.5\n",
        exercise_title="Elegir la conversión correcta",
        exercise_prompt="Decide qué conversión de tipos aplicar a \"10\" y \"3.5\": int() o float(), y por qué.",
        exercise_expected_outcome="\"10\" -> int(); \"3.5\" -> float() (tiene punto decimal).",
        exercise_scaffolding=("revisar si el texto tiene punto decimal", "elegir int() o float()"),
    ),
    # ── M3 — Operadores y Expresiones ─────────────────────────────────
    "Operadores aritméticos básicos": PlantillaConcepto(
        modulo="M3",
        code="def calcular_area_rectangulo(base, altura):\n    return base * altura\n",
        tests="assert calcular_area_rectangulo(4, 5) == 20\n",
        exercise_title="Aplicar operadores aritméticos",
        exercise_prompt="Calcula el área de un rectángulo de base 6 y altura 3 usando el operador *.",
        exercise_expected_outcome="18",
        exercise_scaffolding=("identificar la fórmula", "aplicar el operador *"),
    ),
    "División entera y módulo": PlantillaConcepto(
        modulo="M3",
        code=(
            "def es_par(numero):\n"
            "    return numero % 2 == 0\n\n"
            "def repartir_exacto(total, personas):\n"
            "    return total // personas\n"
        ),
        tests="assert es_par(4) is True\nassert es_par(7) is False\nassert repartir_exacto(10, 3) == 3\n",
        exercise_title="Distinguir // de %",
        exercise_prompt="Calcula la división entera (10 // 3) y el módulo (10 % 3) por separado, y explica qué representa cada resultado.",
        exercise_expected_outcome="10 // 3 = 3 (cociente entero); 10 % 3 = 1 (residuo).",
        exercise_scaffolding=("calcular el cociente entero", "calcular el residuo"),
    ),
    "Comparación y operadores relacionales": PlantillaConcepto(
        modulo="M3",
        code="def aprobo(nota):\n    return nota >= 11\n",
        tests="assert aprobo(11) is True\nassert aprobo(10) is False\n",
        exercise_title="Usar un operador relacional",
        exercise_prompt="Escribe la comparación (operador relacional) que determina si una nota de 11 o más está aprobada.",
        exercise_expected_outcome="nota >= 11",
        exercise_scaffolding=("identificar el umbral", "elegir el operador correcto"),
    ),
    "Operadores lógicos": PlantillaConcepto(
        modulo="M3",
        code="def puede_matricularse(tiene_requisitos, sin_deuda):\n    return tiene_requisitos and sin_deuda\n",
        tests="assert puede_matricularse(True, True) is True\nassert puede_matricularse(True, False) is False\n",
        exercise_title="Combinar condiciones con and",
        exercise_prompt="Con el operador lógico and, explica por qué se necesitan AMBAS condiciones verdaderas para poder matricularse.",
        exercise_expected_outcome="and exige que las dos condiciones sean True simultáneamente.",
        exercise_scaffolding=("evaluar cada condición por separado", "combinar con and"),
    ),
    "Expresiones y precedencia": PlantillaConcepto(
        modulo="M3",
        code="def calcular_promedio_ponderado(n1, n2, n3):\n    return (n1 * 2 + n2 * 3 + n3 * 5) / (2 + 3 + 5)\n",
        tests="assert calcular_promedio_ponderado(10, 10, 10) == 10\n",
        exercise_title="Precedencia de operadores",
        exercise_prompt="Explica por qué los paréntesis alrededor de (2 + 3 + 5) son necesarios en esta expresión.",
        exercise_expected_outcome="Sin paréntesis, la división ocurriría antes que la última suma, cambiando el resultado.",
        exercise_scaffolding=("identificar qué se ejecuta primero sin paréntesis", "verificar con paréntesis"),
    ),
    # ── M4 — Condicionales ─────────────────────────────────────────────
    "Condicionales básicos": PlantillaConcepto(
        modulo="M4",
        code="def clasificar_nota(nota):\n    if nota >= 17:\n        return \"excelente\"\n    else:\n        return \"regular\"\n",
        tests="assert clasificar_nota(18) == \"excelente\"\nassert clasificar_nota(12) == \"regular\"\n",
        exercise_title="Escribir un if/else",
        exercise_prompt="Escribe el condicional básico que separa las notas 'excelente' (>=17) de las 'regulares'.",
        exercise_expected_outcome="if nota >= 17: ... else: ...",
        exercise_scaffolding=("identificar la condición", "escribir la rama else"),
    ),
    "Condicionales anidados": PlantillaConcepto(
        modulo="M4",
        code=(
            "def clasificar_estudiante(nota, asistencia):\n"
            "    if nota >= 11:\n"
            "        if asistencia >= 70:\n"
            "            return \"aprobado\"\n"
            "        else:\n"
            "            return \"aprobado sin certificado\"\n"
            "    else:\n"
            "        return \"desaprobado\"\n"
        ),
        tests=(
            "assert clasificar_estudiante(15, 80) == \"aprobado\"\n"
            "assert clasificar_estudiante(15, 50) == \"aprobado sin certificado\"\n"
            "assert clasificar_estudiante(8, 90) == \"desaprobado\"\n"
        ),
        exercise_title="Anidar condicionales",
        exercise_prompt="En este condicional anidado, traza el camino que sigue el código para nota=15, asistencia=50.",
        exercise_expected_outcome="nota>=11 (sí) -> asistencia>=70 (no) -> 'aprobado sin certificado'.",
        exercise_scaffolding=("evaluar el if externo", "evaluar el if interno solo si el externo es verdadero"),
    ),
    # ── M5 — Bucles ─────────────────────────────────────────────────────
    "Bucle while": PlantillaConcepto(
        modulo="M5",
        code=(
            "def contar_hasta(n):\n"
            "    contador = 0\n"
            "    resultado = []\n"
            "    while contador < n:\n"
            "        contador += 1\n"
            "        resultado.append(contador)\n"
            "    return resultado\n"
        ),
        tests="assert contar_hasta(3) == [1, 2, 3]\n",
        exercise_title="Controlar un bucle while",
        exercise_prompt="Explica qué pasaría si se olvidara la línea 'contador += 1' dentro del while.",
        exercise_expected_outcome="El bucle nunca terminaría (bucle infinito): la condición jamás deja de cumplirse.",
        exercise_scaffolding=("identificar la condición de parada", "identificar qué actualiza esa condición"),
    ),
    "Bucle for": PlantillaConcepto(
        modulo="M5",
        code="def sumar_lista(numeros):\n    total = 0\n    for numero in numeros:\n        total += numero\n    return total\n",
        tests="assert sumar_lista([1, 2, 3]) == 6\n",
        exercise_title="Recorrer con for",
        exercise_prompt="En este bucle for, traza el valor de 'total' en cada vuelta para la lista [1, 2, 3].",
        exercise_expected_outcome="total: 0 -> 1 -> 3 -> 6",
        exercise_scaffolding=("identificar el valor inicial", "seguir cada vuelta"),
    ),
    "Bucles anidados": PlantillaConcepto(
        modulo="M5",
        code=(
            "def tabla_multiplicar(n):\n"
            "    filas = []\n"
            "    for i in range(1, n + 1):\n"
            "        fila = []\n"
            "        for j in range(1, n + 1):\n"
            "            fila.append(i * j)\n"
            "        filas.append(fila)\n"
            "    return filas\n"
        ),
        tests="assert tabla_multiplicar(2) == [[1, 2], [2, 4]]\n",
        exercise_title="Bucle dentro de otro bucle",
        exercise_prompt="En estos bucles anidados, explica cuántas veces se ejecuta el for interno completo si n=3.",
        exercise_expected_outcome="El for interno completa sus 3 vueltas por cada una de las 3 vueltas del externo (9 en total).",
        exercise_scaffolding=("identificar el bucle externo", "identificar el bucle interno", "contar repeticiones"),
    ),
    "Flujo de bucles (break/continue)": PlantillaConcepto(
        modulo="M5",
        code=(
            "def primer_multiplo_de_tres(numeros):\n"
            "    for numero in numeros:\n"
            "        if numero % 3 != 0:\n"
            "            continue\n"
            "        return numero\n"
            "    return None\n\n"
            "def detener_en_negativo(numeros):\n"
            "    resultado = []\n"
            "    for numero in numeros:\n"
            "        if numero < 0:\n"
            "            break\n"
            "        resultado.append(numero)\n"
            "    return resultado\n"
        ),
        tests=(
            "assert primer_multiplo_de_tres([1, 2, 4, 9]) == 9\n"
            "assert detener_en_negativo([1, 2, -1, 3]) == [1, 2]\n"
        ),
        exercise_title="Diferenciar break de continue",
        exercise_prompt="Explica la diferencia de efecto entre 'continue' (saltar esta vuelta) y 'break' (terminar el bucle).",
        exercise_expected_outcome="continue salta al siguiente elemento; break termina el bucle por completo.",
        exercise_scaffolding=("rastrear qué hace continue", "rastrear qué hace break"),
    ),
    # ── M6 — Funciones ────────────────────────────────────────────────
    "Definición e invocación de funciones": PlantillaConcepto(
        modulo="M6",
        code="def calcular_iva(precio):\n    return precio * 0.18\n\ntotal = calcular_iva(100)\n",
        tests="assert calcular_iva(100) == 18.0\n",
        exercise_title="Definir e invocar una función",
        exercise_prompt="Señala la definición de la función calcular_iva y su invocación en el código.",
        exercise_expected_outcome="def calcular_iva(...) es la definición; calcular_iva(100) es la invocación.",
        exercise_scaffolding=("ubicar la palabra def", "ubicar la llamada con paréntesis"),
    ),
    "Parámetros y argumentos": PlantillaConcepto(
        modulo="M6",
        code="def crear_saludo(nombre, saludo=\"Hola\"):\n    return f\"{saludo}, {nombre}\"\n",
        tests="assert crear_saludo(\"Ana\") == \"Hola, Ana\"\nassert crear_saludo(\"Ana\", saludo=\"Buenas\") == \"Buenas, Ana\"\n",
        exercise_title="Parámetro con valor por defecto",
        exercise_prompt="Este parámetro tiene un argumento por defecto: explica qué pasa si se llama crear_saludo(\"Ana\") sin especificar 'saludo'.",
        exercise_expected_outcome="Usa el valor por defecto \"Hola\" porque no se pasó un argumento para ese parámetro.",
        exercise_scaffolding=("identificar el parámetro con default", "identificar cuándo se usa el default"),
    ),
    "Valores de retorno": PlantillaConcepto(
        modulo="M6",
        code="def dividir_con_resto(a, b):\n    cociente = a // b\n    resto = a % b\n    return cociente, resto\n",
        tests="assert dividir_con_resto(10, 3) == (3, 1)\n",
        exercise_title="Una función puede retornar varios valores",
        exercise_prompt="Explica qué valores de retorno produce 'return cociente, resto' en Python.",
        exercise_expected_outcome="Una tupla con ambos valores: (cociente, resto).",
        exercise_scaffolding=("identificar los dos valores", "reconocer que return los empaqueta en tupla"),
    ),
    "Ámbito de variables": PlantillaConcepto(
        modulo="M6",
        code=(
            "contador_global = 0\n\n"
            "def incrementar_local():\n"
            "    contador_local = 1\n"
            "    contador_local += 1\n"
            "    return contador_local\n\n"
            "def incrementar_global():\n"
            "    global contador_global\n"
            "    contador_global += 1\n"
            "    return contador_global\n"
        ),
        tests=(
            "assert incrementar_local() == 2\n"
            "assert incrementar_global() == 1\n"
            "assert incrementar_global() == 2\n"
        ),
        exercise_title="Variable local vs. global",
        exercise_prompt="Sobre el ámbito de estas variables, explica por qué incrementar_local() siempre devuelve 2, pero incrementar_global() acumula entre llamadas.",
        exercise_expected_outcome="contador_local se reinicia en cada llamada; contador_global persiste porque es global.",
        exercise_scaffolding=("identificar la variable local", "identificar la variable global con 'global'"),
    ),
    # ── M7 — Arreglos ────────────────────────────────────────────────
    "Creación y estructura de arreglos (listas)": PlantillaConcepto(
        modulo="M7",
        code="def crear_lista_de_notas():\n    notas = [12, 15, 18, 9]\n    return notas\n",
        tests="assert crear_lista_de_notas() == [12, 15, 18, 9]\n",
        exercise_title="Crear una lista",
        exercise_prompt="Crea una lista con 4 notas de estudiantes, en el orden en que fueron registradas.",
        exercise_expected_outcome="Una lista de 4 elementos numéricos, en orden.",
        exercise_scaffolding=("usar corchetes []", "separar elementos con comas"),
    ),
    "Indexación": PlantillaConcepto(
        modulo="M7",
        code="def obtener_primero_y_ultimo(lista):\n    return lista[0], lista[-1]\n",
        tests="assert obtener_primero_y_ultimo([10, 20, 30]) == (10, 30)\n",
        exercise_title="Acceder por índice",
        exercise_prompt="Con indexación negativa, explica por qué lista[-1] devuelve el último elemento sin conocer la longitud de la lista.",
        exercise_expected_outcome="Los índices negativos cuentan desde el final: -1 es siempre el último.",
        exercise_scaffolding=("indexar desde el inicio (0)", "indexar desde el final (-1)"),
    ),
    "Búsqueda (in, .index())": PlantillaConcepto(
        modulo="M7",
        code=(
            "def buscar_estudiante(lista, nombre):\n"
            "    if nombre in lista:\n"
            "        return lista.index(nombre)\n"
            "    return -1\n"
        ),
        tests="assert buscar_estudiante([\"Ana\", \"Luis\"], \"Luis\") == 1\nassert buscar_estudiante([\"Ana\", \"Luis\"], \"Marco\") == -1\n",
        exercise_title="Buscar en una lista",
        exercise_prompt="Explica por qué se verifica 'in' ANTES de llamar a .index().",
        exercise_expected_outcome="Sin verificar 'in' primero, .index() lanzaría un error si el valor no está.",
        exercise_scaffolding=("verificar pertenencia con in", "obtener la posición con .index()"),
    ),
    "Modificación de tamaño (append, insert, remove, pop)": PlantillaConcepto(
        modulo="M7",
        code=(
            "def actualizar_lista(lista):\n"
            "    lista.append(40)\n"
            "    lista.insert(0, 5)\n"
            "    lista.remove(20)\n"
            "    lista.pop()\n"
            "    return lista\n"
        ),
        tests="assert actualizar_lista([10, 20, 30]) == [5, 10, 30]\n",
        exercise_title="Modificar una lista en el lugar",
        exercise_prompt="Traza el contenido de la lista después de cada operación: append, insert, remove, pop.",
        exercise_expected_outcome="[10,20,30]->[10,20,30,40]->[5,10,20,30,40]->[5,10,30,40]->[5,10,30]",
        exercise_scaffolding=("append agrega al final", "insert agrega en una posición", "remove quita por valor", "pop quita el último"),
    ),
    "Slicing": PlantillaConcepto(
        modulo="M7",
        code="def obtener_primeros_tres(lista):\n    return lista[:3]\n",
        tests="assert obtener_primeros_tres([1, 2, 3, 4, 5]) == [1, 2, 3]\n",
        exercise_title="Extraer un sub-arreglo con slicing",
        exercise_prompt="En este slicing, explica qué significa lista[:3] y en qué se diferencia de lista[3:].",
        exercise_expected_outcome="lista[:3] toma los primeros 3 elementos; lista[3:] toma desde el índice 3 hasta el final.",
        exercise_scaffolding=("identificar el límite antes de los dos puntos", "identificar el límite después"),
    ),
    # ── M8 — Recursividad ────────────────────────────────────────────
    "Recursividad": PlantillaConcepto(
        modulo="M8",
        code="def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n - 1)\n",
        tests="assert factorial(0) == 1\nassert factorial(5) == 120\n",
        exercise_title="Identificar el caso base",
        exercise_prompt="En esta recursividad, explica qué pasaría si la función factorial no tuviera el caso base 'if n <= 1'.",
        exercise_expected_outcome="La recursión nunca terminaría (recursión infinita, error de profundidad máxima).",
        exercise_scaffolding=("identificar el caso base", "identificar la llamada recursiva"),
    ),
    "Traza y pila de llamadas": PlantillaConcepto(
        modulo="M8",
        code=(
            "def factorial_con_traza(n, traza=None):\n"
            "    if traza is None:\n"
            "        traza = []\n"
            "    traza.append(n)\n"
            "    if n <= 1:\n"
            "        return 1, traza\n"
            "    resultado, traza = factorial_con_traza(n - 1, traza)\n"
            "    return n * resultado, traza\n"
        ),
        tests=(
            "resultado, traza = factorial_con_traza(4)\n"
            "assert resultado == 24\n"
            "assert traza == [4, 3, 2, 1]\n"
        ),
        exercise_title="Seguir la pila de llamadas",
        exercise_prompt="Escribe el orden exacto en que se apilan las llamadas para factorial_con_traza(4).",
        exercise_expected_outcome="Se apilan en orden 4, 3, 2, 1 — y se resuelven en orden inverso al desapilar.",
        exercise_scaffolding=("seguir cada llamada recursiva", "identificar el orden de resolución al volver"),
    ),
}

MODULOS_CUBIERTOS: tuple[str, ...] = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8")


def obtener_plantilla(concept_title: str) -> PlantillaConcepto | None:
    """`None` si el título no está en el catálogo cerrado — nunca una
    coincidencia parcial adivinada (fail-fast, ver docstring del
    módulo). El llamador (`cmg_generation_service.generar_cmg`) decide
    el fallback y lo marca explícitamente en `CMG.code_source`."""
    return _CATALOGO.get(concept_title)


def conceptos_cubiertos() -> tuple[str, ...]:
    return tuple(_CATALOGO.keys())
