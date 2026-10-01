"""R24 — MICRO-PILOTO ADVERSARIAL del instrumento D1 graduado candidato
(R22/R23). INSTRUMENT VALIDATION ONLY.

Objetivo único: comprobar el límite de constructo que R23 dejó
explícitamente abierto — "D1 es una medida de cobertura léxica, no de
calidad pedagógica completa" — construyendo, para los 2 mismos pares
Concept/LearningObjective ya usados en R23, un CASO D adversarial:
contiene deliberadamente TODAS las palabras clave (concepto + objetivo)
pero de forma circular/tautológica, sin explicar nada realmente.

No reimplementa el instrumento: importa `evaluar_d1_graduado` de
`experiments/d1_graduado_piloto.py` (R23) tal cual — cero lógica de
evaluación duplicada. No se importa desde ningún módulo productivo, no
se usa desde Corrida 2.
"""

from __future__ import annotations

import dataclasses
import json

from experiments.d1_graduado_piloto import evaluar_d1_graduado

CASOS = [
    {
        "par": "Traza y pila de llamadas / Recursividad",
        "concept_title": "Traza y pila de llamadas",
        "learning_objective_title": "Recursividad",
        "explicaciones": {
            "A_baja": (
                "un bucle while repite una accion mientras se cumpla una "
                "condicion, evaluada antes de cada iteracion del ciclo."
            ),
            "B_media": (
                "cada vez que una funcion se invoca a si misma se agrega un "
                "nuevo marco a la pila de llamadas del programa, y ese marco "
                "se retira cuando la funcion retorna."
            ),
            "C_alta_legitima": (
                "la recursividad ocurre cuando una funcion se invoca a si "
                "misma; cada llamada agrega un nuevo marco a la pila de "
                "llamadas, y la traza de ejecucion muestra como esos marcos "
                "se acumulan hasta alcanzar el caso base."
            ),
            "D_adversarial": (
                "la recursividad tiene traza, pila y llamadas. traza es "
                "traza, pila es pila, llamadas son llamadas. recursividad "
                "significa recursividad, y asi funciona la recursividad."
            ),
        },
    },
    {
        "par": "Valores de retorno / Funciones",
        "concept_title": "Valores de retorno",
        "learning_objective_title": "Funciones",
        "explicaciones": {
            "A_baja": (
                "una lista en python puede crearse con corchetes y contener "
                "varios elementos separados por comas, accesibles por su "
                "posicion."
            ),
            "B_media": (
                "cuando el flujo de ejecucion llega a la instruccion return, "
                "el valor indicado se entrega de inmediato a quien haya "
                "iniciado esa ejecucion."
            ),
            "C_alta_legitima": (
                "una funcion puede terminar su ejecucion con la instruccion "
                "return, que entrega un valor de retorno al punto donde esa "
                "funcion fue invocada."
            ),
            "D_adversarial": (
                "las funciones tienen valores y retorno. valores son "
                "valores, retorno es retorno. las funciones tienen "
                "funciones con valores de retorno que retornan valores de "
                "las funciones."
            ),
        },
    },
]

NIVEL_ESPERADO = {"A_baja": 0, "B_media": 1, "C_alta_legitima": 2, "D_adversarial": None}


def _texto_contiene_todas_las_claves(texto: str, claves: tuple[str, ...]) -> bool:
    from experiments.d1_graduado_piloto import _contiene_alguna_forma, _normalizar

    normalizado = _normalizar(texto)
    return all(_contiene_alguna_forma(normalizado, k) for k in claves)


def main() -> dict:
    resultado = {
        "label": "INSTRUMENT VALIDATION ONLY",
        "descripcion": (
            "Micro-piloto adversarial del instrumento D1 graduado candidato "
            "(R24). Comprueba el límite de constructo identificado en R23: "
            "si una explicación circular/tautológica que solo MENCIONA las "
            "palabras clave (sin explicar nada) recibe el mismo nivel 2 que "
            "una explicación legítima. NO es Corrida 2. NO se insertó en "
            "experiment_cmg_results."
        ),
        "instrumento": "experiments.d1_graduado_piloto.evaluar_d1_graduado",
        "casos": [],
        "limite_de_constructo_confirmado": None,
    }

    limite_confirmado_en_ambos = True

    for caso in CASOS:
        entrada = {"par": caso["par"], "resultados": {}}
        for variante, texto in caso["explicaciones"].items():
            r = evaluar_d1_graduado(caso["concept_title"], caso["learning_objective_title"], texto)
            todas_las_claves = caso_claves = tuple(r.claves_concepto) + tuple(r.claves_objetivo)
            contiene_todas = _texto_contiene_todas_las_claves(texto, todas_las_claves)
            entrada["resultados"][variante] = {
                "explicacion": texto,
                "nivel_esperado": NIVEL_ESPERADO[variante],
                "nivel_obtenido": r.nivel,
                "contiene_todas_las_palabras_clave": contiene_todas,
                "detalle": dataclasses.asdict(r),
            }
        nivel_d = entrada["resultados"]["D_adversarial"]["nivel_obtenido"]
        entrada["caso_D_obtuvo_nivel_2"] = nivel_d == 2
        limite_confirmado_en_ambos = limite_confirmado_en_ambos and (nivel_d == 2)
        resultado["casos"].append(entrada)

    resultado["limite_de_constructo_confirmado"] = limite_confirmado_en_ambos
    if limite_confirmado_en_ambos:
        resultado["conclusion"] = (
            "El instrumento D1 presenta un límite de constructo conocido: "
            "puede otorgar cobertura alta (nivel 2) ante presencia léxica "
            "de las palabras clave sin verificar por sí mismo la calidad "
            "semántica/pedagógica de la explicación."
        )
    else:
        resultado["conclusion"] = (
            "El caso D (adversarial) NO alcanzó nivel 2 en al menos un par "
            "— ver 'resultados' por caso para la condición léxica exacta "
            "que lo impidió."
        )

    return resultado


if __name__ == "__main__":
    r = main()
    print(json.dumps(r, ensure_ascii=False, indent=2))
