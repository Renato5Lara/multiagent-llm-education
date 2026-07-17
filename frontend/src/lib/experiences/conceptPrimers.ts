// Microexplicaciones de términos de Python (sprint "mejora pedagógica", jul
// 2026) — una tarjeta corta por término, reutilizable desde cualquier ciclo
// que lo introduzca por primera vez (ver ConceptPrimer en moduleExperience.ts
// y ConceptPrimerCard.tsx). Contenido puro: ningún archivo de ciclo repite
// esta definición, solo la referencia.
//
// Wiring actual (jul 2026): PRINT_PRIMER → Módulo 1 Ciclo 1, VARIABLES_PRIMER
// → Módulo 1 Ciclo 2, INPUT_PRIMER → Módulo 1 Ciclo 3, IF_PRIMER +
// ELSE_PRIMER → Módulo 2 Ciclo 1 (el único ciclo existente que usa if/else,
// y los introduce juntos). FOR_PRIMER y WHILE_PRIMER quedan autorados y
// listos, pero SIN adjuntar a ningún ciclo: hoy no existe ningún ciclo de
// bucles en el contenido (module1.ts tiene 3 ciclos, module2.ts tiene 1) —
// adjuntarlos sería inventar una aparición que el recorrido real no tiene.

import type { ConceptPrimer } from '@/types/moduleExperience'

export const PRINT_PRIMER: ConceptPrimer = {
  term: 'print',
  whatIsIt: 'print es una función de Python: le pides algo y hace ese algo por ti.',
  whatFor: 'Sirve para mostrar información en pantalla — es la forma en que un programa "habla".',
  example: {
    code: 'print("Hola")',
    result: 'Hola',
  },
}

export const VARIABLES_PRIMER: ConceptPrimer = {
  term: 'una variable',
  whatIsIt: 'Una variable es una caja con nombre que guarda un valor para usarlo después.',
  whatFor: 'Sirve para que un programa recuerde algo — un número, un texto — sin tener que repetirlo cada vez.',
  example: {
    code: 'edad = 20\nprint(edad)',
    result: '20',
  },
}

export const INPUT_PRIMER: ConceptPrimer = {
  term: 'input',
  whatIsIt: 'input() es una función que detiene el programa y espera a que la persona escriba algo.',
  whatFor: 'Sirve para que un programa pregunte y reciba una respuesta real, en vez de trabajar solo con datos fijos.',
  example: {
    code: 'nombre = input("¿Cómo te llamas? ")\nprint(nombre)',
    result: '(espera tu respuesta, y luego la muestra)',
  },
}

export const IF_PRIMER: ConceptPrimer = {
  term: 'if',
  whatIsIt: 'if es la palabra con la que Python pregunta "¿esto es cierto?" antes de actuar.',
  whatFor: 'Sirve para que el programa haga algo SOLO cuando se cumple una condición.',
  example: {
    code: 'edad = 20\nif edad >= 18:\n    print("Puede votar")',
    result: 'Puede votar',
  },
}

export const ELSE_PRIMER: ConceptPrimer = {
  term: 'else',
  whatIsIt: 'else es lo que Python hace cuando la condición del if NO se cumplió.',
  whatFor: 'Sirve para darle al programa un segundo camino — qué hacer si la respuesta fue "no".',
  example: {
    code: 'edad = 15\nif edad >= 18:\n    print("Puede votar")\nelse:\n    print("Todavía no")',
    result: 'Todavía no',
  },
}

export const FOR_PRIMER: ConceptPrimer = {
  term: 'for',
  whatIsIt: 'for es la palabra con la que Python repite una acción, una vez por cada elemento de una lista.',
  whatFor: 'Sirve para no escribir la misma instrucción muchas veces cuando hay varios elementos que tratar igual.',
  example: {
    code: 'for color in ["rojo", "verde"]:\n    print(color)',
    result: 'rojo\nverde',
  },
}

export const WHILE_PRIMER: ConceptPrimer = {
  term: 'while',
  whatIsIt: 'while es la palabra con la que Python repite una acción MIENTRAS una condición siga siendo cierta.',
  whatFor: 'Sirve para repetir algo un número de veces que no se sabe de antemano — hasta que la condición cambie.',
  example: {
    code: 'vidas = 2\nwhile vidas > 0:\n    print("Jugando")\n    vidas = vidas - 1',
    result: 'Jugando\nJugando',
  },
}
