// Módulo 2 · "Decisiones que la máquina entiende" — instancia del Patrón de
// Experiencia. Mismo patrón congelado que Módulo 1 (jul 2026): apertura de
// curiosidad + Ciclo 1. Los ciclos 2-3 (bucles, comprensiones) y el reto
// integrador entran en incrementos siguientes, igual que en Módulo 1.

import type { ModuleExperienceDefinition, PredictOutputPracticeDef } from '@/types/moduleExperience'
import { ELSE_PRIMER, IF_PRIMER } from './conceptPrimers'

// Sprint "diversidad pedagógica" (jul 2026): Ciclo 3 (Módulo 1) cerró con
// 'ordering' para las cuatro modalidades — este ciclo (el que sigue
// inmediatamente en el recorrido real, Misión 1 → Misión 2) rompe esa
// repetición dándoles a las cuatro su propia versión de "predecir la
// ejecución" de un if/else — mismo componente ya existente
// (PredictOutputPractice), mismo concepto evaluado (condición evaluable +
// rama if/else), temas nuevos que no repiten ni el `concept.pythonBridge`
// (temperatura > 24) ni el `cycle.pythonBridge` (sensor_lluvia) de este
// mismo ciclo, para no adelantar ninguna de esas dos revelaciones.
const VISUAL_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  // Auditoría "diversidad pedagógica" (revisión post-sprint, jul 2026): copy
  // reforzado hacia "comparar visualmente dos valores", no solo "leer código"
  // — misma mecánica (predict_output), pero enmarca la tarea como una
  // comparación de magnitudes que el estudiante puede visualizar en una
  // recta numérica (30 vs 24), coherente con las variantes visuales ya
  // existentes de este ciclo (que sí usan infografía).
  prompt: 'Compara los dos valores a simple vista: temperatura (30) frente al umbral (24). ¿Qué rama del if se enciende?',
  code: 'temperatura = 30\nif temperatura > 24:\n    print("Enciende el aire acondicionado")\nelse:\n    print("Temperatura agradable")',
  options: [
    { id: 'a', text: 'Enciende el aire acondicionado' },
    { id: 'b', text: 'Temperatura agradable' },
    { id: 'c', text: 'temperatura' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'a',
  successFeedback: 'Exacto — visualizando 30 a la derecha de 24 en la recta numérica, la comparación temperatura > 24 es verdadera, así que Python tomó la rama del if y mostró "Enciende el aire acondicionado".',
  wrongFeedback: 'Compara visualmente los dos números: temperatura vale 30. ¿Está a la derecha de 24 en la recta numérica?',
  solutionExplanation: [
    'Línea 1: temperatura = 30 — crea la variable con el valor 30.',
    'Línea 2: if temperatura > 24: — 30 > 24 es verdadero, así que Python entra a esta rama.',
    'Como la condición fue verdadera, se ejecuta print("Enciende el aire acondicionado") — la rama de else nunca corre.',
  ],
}

const READING_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  prompt: 'Lee el código con calma y predice qué imprime.',
  code: 'humo = 620\nif humo > 500:\n    print("Suena la alarma")\nelse:\n    print("Todo en orden")',
  options: [
    { id: 'a', text: 'Suena la alarma' },
    { id: 'b', text: 'Todo en orden' },
    { id: 'c', text: 'humo' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'a',
  successFeedback: 'Exacto — humo vale 620, y 620 > 500 es verdadero, así que Python tomó la rama del if y mostró "Suena la alarma".',
  wrongFeedback: 'Revisa la condición: humo vale 620. ¿620 es mayor a 500?',
  solutionExplanation: [
    'Línea 1: humo = 620 — crea la variable con el valor 620.',
    'Línea 2: if humo > 500: — 620 > 500 es verdadero, así que Python entra a esta rama.',
    'Como la condición fue verdadera, se ejecuta print("Suena la alarma") — igual que la alarma contra incendios que leíste arriba, la rama de else nunca corre.',
  ],
}

const AUDIO_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  prompt: 'Después de escuchar la explicación, decide: ¿qué imprime este código?',
  code: 'hora = 19\nif hora >= 18:\n    print("Enciende las luces")\nelse:\n    print("Deja las luces apagadas")',
  // Auditoría "diversidad pedagógica" (revisión post-sprint, jul 2026): antes
  // el prompt PROMETÍA audio ("después de escuchar...") sin reproducir nada.
  // Narra exactamente el código de arriba — el estudiante puede resolver
  // escuchando, sin necesitar leer el bloque de código en absoluto.
  narrationText:
    'Escucha con atención. Primera línea: hora es igual a diecinueve. Segunda línea: si hora es mayor o igual a dieciocho, imprime "enciende las luces". De lo contrario, imprime "deja las luces apagadas". ¿Qué mensaje se muestra?',
  options: [
    { id: 'a', text: 'Enciende las luces' },
    { id: 'b', text: 'Deja las luces apagadas' },
    { id: 'c', text: 'hora' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'a',
  successFeedback: 'Exacto — hora vale 19, y 19 >= 18 es verdadero, así que Python tomó la rama del if y mostró "Enciende las luces".',
  wrongFeedback: 'Revisa la condición: hora vale 19. ¿19 es mayor o igual a 18?',
  solutionExplanation: [
    'Línea 1: hora = 19 — crea la variable con el valor 19.',
    'Línea 2: if hora >= 18: — 19 >= 18 es verdadero, así que Python entra a esta rama.',
    'Como la condición fue verdadera, se ejecuta print("Enciende las luces") — la rama de else nunca corre.',
  ],
}

const KINESTHETIC_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  // Auditoría "diversidad pedagógica" (revisión post-sprint, jul 2026): copy
  // reforzado hacia "actuar la condición antes de ver el resultado" — misma
  // mecánica (predict_output), pero enmarca la predicción como una apuesta
  // física que el estudiante hace con su propia edad antes de comprobarla,
  // coherente con la escalera manipulable de PythonBridge que ya corre en
  // este ciclo para el perfil kinestésico.
  prompt: 'Antes de revisar, decide con tu propia mano (arriba = sí sigue la ronda, abajo = no): ¿qué imprime este código?',
  code: 'bateria = 20\nif bateria >= 20:\n    print("Sigue la ronda")\nelse:\n    print("Vuelve a cargar")',
  options: [
    { id: 'a', text: 'Sigue la ronda' },
    { id: 'b', text: 'Vuelve a cargar' },
    { id: 'c', text: 'bateria' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'a',
  successFeedback: 'Exacto — bateria vale 20, y 20 >= 20 es verdadero, así que Python tomó la rama del if y mostró "Sigue la ronda". Tu predicción física coincidió con la ejecución real.',
  wrongFeedback: 'Revisa la condición: bateria vale 20. ¿20 es mayor o igual a 20?',
  solutionExplanation: [
    'Línea 1: bateria = 20 — crea la variable con el valor 20.',
    'Línea 2: if bateria >= 20: — 20 >= 20 es verdadero, así que Python entra a esta rama.',
    'Como la condición fue verdadera, se ejecuta print("Sigue la ronda") — la rama de else nunca corre.',
  ],
}

export const MODULE_2_EXPERIENCE: ModuleExperienceDefinition = {
  moduleNumber: 2,
  missionTitle: 'Misión 2 · Decisiones que la máquina entiende',
  // m-6: la ruta presenta el módulo con este título exacto (seed IS301).
  routeTitle: 'Estructuras de control',
  territory: 'Estratega',
  matchTitles: ['estructuras de control'],

  // ── Apertura: la curiosidad antes que el tema ────────────────────────────────
  opening: {
    questionLines: [
      'Tu robot ahora tiene un paraguas y un sensor de lluvia.',
      'Le dices: «si hace mal tiempo, abre el paraguas».',
      '¿Qué puede salir mal?',
    ],
    options: [
      'Nada — sabrá cuándo hace mal tiempo',
      'No sabría cuándo activarse',
      'Abriría o cerraría el paraguas al azar',
    ],
    freeTextPrompt: '¿Qué crees que haría exactamente? (opcional)',
    revealHook:
      'Un robot no entiende «mal tiempo»: necesita una condición que pueda responder con SÍ o NO, ' +
      'como «¿el sensor detecta gotas?». Esa es la base de una estructura de control: SI se cumple ' +
      'una condición exacta, ENTONCES ejecuta una acción — SI NO, otra distinta. En esta misión vas a ' +
      'construir tu primera decisión real para una máquina — antes de escribir tu primer `if` en Python.',
  },

  cycles: [
    // ── Ciclo 1: Condiciones evaluables ────────────────────────────────────────
    {
      id: 'ciclo-1',
      conceptId: 'condiciones_evaluables',
      conceptLabel: 'Condiciones evaluables',
      priorMastery: 0.2,
      conceptPrimers: [IF_PRIMER, ELSE_PRIMER],
      curiosityFact: {
        fact:
          'En 1883, Warren Johnson inventó el primer termostato eléctrico: una tira de dos metales que se dobla con el calor. Cuando se dobla lo suficiente (la condición), cierra un circuito y corta la calefacción — si no, la mantiene encendida.',
        connection:
          'Ese termostato de 1883 ya tenía exactamente la estructura que vas a construir hoy: una condición que se puede medir como SÍ o NO, y una acción distinta para cada resultado — sin escribir una sola línea de código.',
        source: 'National Inventors Hall of Fame',
      },
      concept: {
        title: '¿Qué hace evaluable a una condición?',
        secondExample: {
          label: 'Otro caso — la alarma contra incendios',
          body: [
            'Una alarma contra incendios no decide «si hay mucho humo»: decide con un sensor que mide partículas de humo por metro cúbico — ¿supera las 500? Si SÍ, suena la alarma. Si NO, permanece en silencio.',
            'Es la misma estructura del paraguas y el termostato, en un contexto donde el error cuesta caro: por eso el sensor nunca usa una idea vaga como «mucho humo».',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'if temperatura > 24:\n    apagar_calefaccion()\nelse:\n    mantener_calefaccion()',
          explanation:
            'El termostato de 1883 que acabas de leer y el paraguas de esta lección resuelven el mismo problema que esta línea: una condición medible (temperatura > 24) y una acción para cada resultado. Eso es un `if`/`else` — nada más.',
        },
        variants: {
          visual: {
            medium: 'infografia',
            mediumLabel: 'Infografía',
            sourceNote: 'Elegido para ti — tu perfil capta ideas más rápido cuando las ve.',
            infographic: {
              vague: {
                instruction: 'Si hace mal tiempo, abre el paraguas',
                questions: ['¿qué cuenta como mal tiempo?', '¿lluvia? ¿viento? ¿nublado?', '¿quién decide?'],
              },
              precise: {
                instruction:
                  'Si el sensor de lluvia detecta gotas (SÍ), abre el paraguas. Si no detecta gotas (NO), mantenlo cerrado.',
                parts: ['la condición', 'la acción si es SÍ', 'la acción si es NO'],
              },
              caption:
                'La diferencia no es el detalle: una condición evaluable siempre puede responderse con SÍ o NO — nunca "depende".',
            },
            body: [
              'Una estructura SI/ENTONCES necesita una condición que la máquina pueda evaluar como verdadera o falsa — nunca una idea vaga como "mal tiempo".',
              'Python usa exactamente esta lógica: `if condición:` seguido de qué hacer si es verdadera, y `else:` para cuando no lo es. La condición siempre se reduce a SÍ o NO.',
            ],
          },
          reading: {
            medium: 'texto',
            mediumLabel: 'Texto estructurado',
            sourceNote: 'Elegido para ti — tu perfil profundiza mejor leyendo a su ritmo.',
            body: [
              'Un fabricante de robots domésticos programó una vez: «si el ambiente está incómodo, ajusta la temperatura». El robot se quedó inmóvil para siempre — «incómodo» no es algo que un sensor pueda medir.',
              'No era un robot defectuoso: estaba esperando una condición que pudiera evaluar. «Incómodo» admite mil respuestas distintas; un sensor solo entiende números y comparaciones: ¿la temperatura es mayor a 28°C? Eso sí tiene una única respuesta: SÍ o NO.',
              'Una condición es evaluable cuando se reduce a verdadero o falso, sin ambigüedad: «¿el sensor detecta gotas?», «¿la temperatura supera 28°C?», «¿el usuario presionó el botón?». Ese es el segundo hábito mental de la programación, después de las instrucciones precisas.',
              'Python expresa esta misma idea con `if` y `else`: una condición evaluable, una acción para cuando es verdadera, otra para cuando es falsa. Si tu condición no puede responderse con SÍ o NO, el programa no sabe qué camino tomar.',
            ],
          },
          audio: {
            medium: 'clip_narrado',
            mediumLabel: 'Clip narrado',
            sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
            narrationText:
              'Imagina que le dices a un robot: si hace mal tiempo, abre el paraguas. Suena razonable para una persona, pero el robot se queda congelado. ¿Qué es mal tiempo? ¿Lluvia? ¿Viento? ¿Nublado? Tú lo sabías, pero no lo dijiste de forma que un sensor pudiera medirlo. La regla es esta: una condición solo sirve si se puede responder con sí o no. El sensor detecta gotas, sí o no. La temperatura supera veintiocho grados, sí o no. Eso es una condición evaluable. Y así es exactamente como funciona un if en Python: una condición que se puede responder con sí o no, una acción para cada caso.',
            body: [
              'Imagina que le dices a un robot: «si hace mal tiempo, abre el paraguas». Suena razonable para una persona, pero el robot se queda congelado — ¿qué es «mal tiempo»? ¿Lluvia? ¿Viento? ¿Nublado?',
              'Tú lo sabías, pero no lo dijiste de forma que un sensor pudiera medirlo. La regla es esta: una condición solo sirve si se puede responder con SÍ o NO.',
              'Y así es exactamente como funciona un `if` en Python: una condición que se puede responder con SÍ o NO, y una acción para cada caso.',
            ],
          },
          kinesthetic: {
            medium: 'simulacion',
            mediumLabel: 'Simulación',
            sourceNote: 'Elegido para ti — tu perfil construye comprensión haciendo.',
            body: [
              '🤖 Antes de leer nada, predice: le dices al robot «si hace mal tiempo, abre el paraguas». Empieza a llover. ¿Qué hace?',
              'Antes de revisar tu respuesta, predice también esta otra: le dices «si el sensor detecta gotas, abre el paraguas; si no, mantenlo cerrado». Empieza a llover. ¿Qué hace?',
              'Con «mal tiempo» el robot no hace nada — se queda inmóvil con error, porque no es una condición que pueda evaluar: no sabe qué medir. Con el sensor, en cambio, abre el paraguas: el sensor respondió SÍ, y esa respuesta activa una acción exacta.',
            ],
          },
        },
      },
      practice: {
        // `default` conserva exactamente el ejercicio original (sin cambios)
        // como red de seguridad de orderingFallbackOf — ya no se resuelve
        // directamente para ninguna modalidad, porque las cuatro tienen
        // override explícito abajo (ver el comentario "diversidad
        // pedagógica" junto a los const al inicio del archivo).
        default: {
          kind: 'ordering',
          prompt:
            'El robot debe decidir si abrir o cerrar el paraguas según la lluvia. Construye la secuencia usando SOLO pasos evaluables — uno de la lista es ambiguo y debes descartarlo.',
          items: [
            { id: 'p1', text: 'Consulta el sensor de lluvia', position: 1 },
            { id: 'p2', text: 'Si el sensor marca SÍ, extiende el paraguas', position: 2 },
            { id: 'p3', text: 'Si el sensor marca NO, mantén el paraguas plegado', position: 3 },
            {
              id: 'd1',
              text: 'Actúa según el clima',
              position: null,
              whyWrong:
                '«Actúa según el clima» no dice qué condición evaluar ni qué hacer en cada caso — es la meta, no una instrucción evaluable.',
            },
          ],
          successFeedback:
            'Exacto. Una condición evaluable y una acción distinta para cada resultado posible — eso es una estructura de control real. Cuando escribas `if` en Python, esa misma claridad será exigida por el lenguaje.',
          orderFeedback:
            'El robot necesita el resultado del sensor ANTES de decidir qué hacer con el paraguas: no puede reaccionar a una condición que todavía no consultó.',
          generalHint:
            'El robot se detuvo: revisa si cada paso depende de una condición que sí se puede responder con SÍ o NO.',
          solutionExplanation: [
            'Primero se consulta la condición (el sensor). Después, una acción distinta para cada resultado posible: SÍ abre, NO mantiene cerrado.',
            'Fíjate en el orden: no puedes decidir qué hacer con el paraguas antes de conocer el resultado del sensor — la condición siempre se evalúa primero.',
            'Acabas de construir tu primera estructura de control: una condición evaluable con una acción para cada resultado. Eso es exactamente un `if`/`else` en Python.',
          ],
        },
        visual: VISUAL_PRACTICE,
        reading: READING_PRACTICE,
        audio: AUDIO_PRACTICE,
        kinesthetic: KINESTHETIC_PRACTICE,
      },
      pythonBridge: {
        label: 'Esto ya es Python',
        code: 'if sensor_lluvia.detecta_gotas():\n    abrir_paraguas()\nelse:\n    mantener_cerrado()',
        explanation:
          'La condición que acabas de evaluar es exactamente lo que Python llama `if`: una pregunta que solo puede ser verdadera o falsa. `else` es lo que hiciste con «si el sensor marca NO» — la acción para el otro caso. Ahora vas a escribir tú mismo ese `if`/`else`, paso a paso.',
        practice: {
          mode: 'observar',
          prompt: 'Obsérvalo: el sensor detectó lluvia (llueve = True). Ejecuta esta línea y mira qué decide el paraguas.',
          starterCode: 'llueve = True\nif llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")\n',
          expectedOutput: 'Abre el paraguas',
          hint: 'El código ya está completo — solo presiona Ejecutar para ver qué muestra.',
          resultExplanation: 'llueve valía True, así que Python evaluó la condición del if como verdadera y ejecutó la rama de arriba — por eso ves "Abre el paraguas", no la de else.',
          solutionCode: 'llueve = True\nif llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")',
          nextStage: {
            mode: 'manipular',
            prompt: 'Ahora tú: cambia SOLO el valor de llueve a False para que el paraguas se quede cerrado.',
            starterCode: 'llueve = True\nif llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")\n',
            expectedOutput: 'Deja el paraguas cerrado',
            hint: 'Solo cambia True por False en la primera línea: llueve = False',
            hintsByCategory: {
              sintaxis: 'Revisa que True siga escrito con mayúscula inicial al cambiarlo por False.',
              variables: 'No necesitas crear ninguna variable nueva — solo cambiar el valor de llueve, que ya existe.',
              logica: 'Solo cambia el valor de llueve; el if/else no cambia.',
              salida: 'Revisa que el texto sea exactamente "Deja el paraguas cerrado".',
            },
            workedExample: {
              code: 'hay_sol = False\nif hay_sol:\n    print("Usa lentes")\nelse:\n    print("No hacen falta lentes")',
              output: 'No hacen falta lentes',
              explanation: 'Cambiar el valor de la variable cambia qué rama del if/else se ejecuta — el código no se toca, solo el dato de entrada.',
            },
            resultExplanation: 'Cambiaste llueve a False, así que el if evaluó la condición como falsa y saltó directo a la rama de else — el código no cambió, solo el valor que la condición evaluó.',
            solutionCode: 'llueve = False\nif llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")',
            nextStage: {
              mode: 'completar',
              prompt: 'Completa el código: falta la palabra que evalúa la condición. Reemplaza el espacio en blanco para que el paraguas se abra.',
              starterCode: 'llueve = True\n_____ llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")\n',
              expectedOutput: 'Abre el paraguas',
              hint: 'La palabra que evalúa una condición en Python es if — reemplaza los guiones bajos por esa palabra exacta.',
              hintsByCategory: {
                sintaxis: 'Revisa que no queden guiones bajos ni espacios de más antes de "llueve".',
                variables: 'Python no reconoce "_____ llueve" como una instrucción válida — falta el nombre de la palabra clave.',
                logica: 'Solo falta la palabra que abre la condición; el resto del if/else ya está completo.',
                salida: 'Revisa que el texto siga siendo exactamente "Abre el paraguas".',
              },
              workedExample: {
                code: '_____ hay_sol:\n    print("Usa lentes")\nelse:\n    print("No hacen falta lentes")\n# se completa así:\nif hay_sol:\n    print("Usa lentes")\nelse:\n    print("No hacen falta lentes")',
                output: 'Usa lentes',
                explanation: 'El hueco siempre se completa con la palabra clave que evalúa la condición: if.',
              },
              resultExplanation: 'Al completar el hueco con if, Python pudo por fin reconocer la condición — llueve ya valía True, solo faltaba la palabra clave que le dice a Python "evalúa esto".',
              solutionCode: 'llueve = True\nif llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")',
              nextStage: {
                mode: 'corregir',
                prompt: 'Este código tiene un error: al if le falta algo para que Python lo reconozca como una condición. Encuéntralo y corrígelo.',
                starterCode: 'llueve = True\nif llueve\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")\n',
                expectedOutput: 'Abre el paraguas',
                hint: 'A "if llueve" le faltan los dos puntos (:) al final — Python siempre los exige después de la condición.',
                hintsByCategory: {
                  sintaxis: 'Python no reconoce "if llueve" sin dos puntos al final como una condición válida.',
                  variables: 'El problema no es una variable — llueve ya existe y ya tiene un valor.',
                  logica: 'La estructura if/else ya es correcta; solo falta un signo de puntuación.',
                  salida: 'Una vez corregido, debe mostrar exactamente "Abre el paraguas".',
                },
                workedExample: {
                  code: 'if hay_sol\n    print("Usa lentes")\n# el error es la falta de dos puntos:\nif hay_sol:\n    print("Usa lentes")',
                  output: 'Usa lentes',
                  explanation: 'Python exige dos puntos (:) después de toda condición if — sin ellos, no reconoce dónde empieza el bloque que sigue.',
                },
                resultExplanation: 'Al agregar los dos puntos, Python pudo reconocer "if llueve:" como una condición completa — sin ellos, ni siquiera lograba ejecutar la línea, sin importar que llueve ya valiera True.',
                solutionCode: 'llueve = True\nif llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")',
                nextStage: {
                  mode: 'escribir_parcial',
                  prompt: 'Ahora hazlo tú: escribe un if/else que muestre "Lleva paraguas" si mm_lluvia es mayor a 0, o "No hace falta paraguas" si no. Usa mm_lluvia = 5. El comentario de abajo es solo un recordatorio del patrón, no se ejecuta.',
                  starterCode: '# if condicion:\n#     print("...")\n# else:\n#     print("...")\nmm_lluvia = 5\n',
                  expectedOutput: 'Lleva paraguas',
                  hint: 'Escribe: if mm_lluvia > 0:\n    print("Lleva paraguas")\nelse:\n    print("No hace falta paraguas")',
                  hintsByCategory: {
                    sintaxis: 'Revisa que tu if y tu else (no el comentario) tengan dos puntos al final de cada línea.',
                    variables: 'mm_lluvia ya existe — no necesitas crear ninguna variable nueva, solo comparar su valor.',
                    logica: 'El comentario que empieza con # no se ejecuta — necesitas escribir tu propio if/else debajo, sin el #.',
                    salida: 'Revisa que el texto sea exactamente "Lleva paraguas".',
                  },
                  workedExample: {
                    code: '# if condicion:\n#     print("...")\ntemperatura = 30\nif temperatura > 25:\n    print("Hace calor")\nelse:\n    print("Clima templado")',
                    output: 'Hace calor',
                    explanation: 'El comentario (la línea con #) es solo una nota para ti — Python la ignora. Tu if/else real va debajo, sin el #.',
                  },
                  resultExplanation: 'Escribiste tu propio if/else comparando mm_lluvia > 0 — como mm_lluvia vale 5, la condición fue verdadera y Python ejecutó "Lleva paraguas", la rama del if.',
                  solutionCode: 'mm_lluvia = 5\nif mm_lluvia > 0:\n    print("Lleva paraguas")\nelse:\n    print("No hace falta paraguas")',
                  nextStage: {
                    mode: 'escribir_completo',
                    prompt: 'Ahora profundiza: escribe tú mismo, desde cero, un if/else que muestre "Frío, lleva abrigo" si temperatura es menor a 15, o "Clima templado" si no. Usa temperatura = 12.',
                    starterCode: '',
                    expectedOutput: 'Frío, lleva abrigo',
                    hint: 'Usa: temperatura = 12\nif temperatura < 15:\n    print("Frío, lleva abrigo")\nelse:\n    print("Clima templado")',
                    hintsByCategory: {
                      sintaxis: 'Revisa que if y else tengan dos puntos al final, y que las líneas de print() estén indentadas.',
                      variables: 'Python no encuentra temperatura si no la creaste primero, antes del if.',
                      logica: 'if/else solo necesita la condición y una acción para cada resultado — no hace falta ninguna otra estructura.',
                      salida: 'Revisa mayúsculas, espacios y signos: debe coincidir letra por letra con "Frío, lleva abrigo".',
                    },
                    workedExample: {
                      code: 'llueve = True\nif llueve:\n    print("Abre el paraguas")\nelse:\n    print("Deja el paraguas cerrado")',
                      output: 'Abre el paraguas',
                      explanation: 'Mismo patrón de siempre: crea la variable, compara con if, una acción para cada resultado con else. Fíjate en el patrón, no copies el mensaje: el tuyo es "Frío, lleva abrigo".',
                    },
                    resultExplanation: 'Desde cero, if/else volvió a decidir entre dos caminos: como temperatura (12) es menor a 15, Python tomó la rama del if y mostró "Frío, lleva abrigo".',
                    solutionCode: 'temperatura = 12\nif temperatura < 15:\n    print("Frío, lleva abrigo")\nelse:\n    print("Clima templado")',
                  },
                },
              },
            },
          },
        },
      },
      decision: {
        question:
          'Ya entiendes qué hace evaluable a una condición — y por qué eso mismo aplica cuando programas con `if`. ¿Cómo quieres consolidarlo?',
        reinforcements: [
          {
            kind: 'reto',
            label: 'Resolver un reto rápido',
            title: 'Reto: la puerta del garaje',
            body: ['Misma regla: solo condiciones evaluables, en orden. Hay un impostor.'],
            practice: {
              kind: 'ordering',
              prompt: 'Ordena los pasos para que la puerta del garaje decida si abrirse. Descarta el que sea ambiguo.',
              items: [
                { id: 'a1', text: 'Consulta el sensor de peso frente a la puerta del garaje', position: 1 },
                { id: 'a2', text: 'Si detecta peso, abre la puerta', position: 2 },
                { id: 'a3', text: 'Si no detecta peso, mantén la puerta cerrada', position: 3 },
                {
                  id: 'ad1',
                  text: 'Abre cuando el robot quiera pasar',
                  position: null,
                  whyWrong:
                    '«Cuando el robot quiera pasar» no es medible por un sensor — no dice qué condición evaluar.',
                },
              ],
              successFeedback: 'Perfecto — detectaste que la condición vaga era el impostor.',
              orderFeedback: 'La puerta no puede decidir sin haber consultado antes el sensor de peso.',
              generalHint: 'Una de esas frases no dice qué puede medir un sensor. ¿Cuál?',
              solutionExplanation: [
                '«Abre cuando el robot quiera pasar» describe una intención, no algo medible. Las otras tres sí son evaluables: consultan un sensor real y responden SÍ o NO.',
              ],
            },
          },
          {
            kind: 'ejemplo',
            label: 'Ver un ejemplo más',
            title: 'Ejemplo: el riego automático del jardín',
            medium: 'ejemplo_comentado',
            body: [
              'El riego del jardín nunca decide «cuando la tierra se vea seca»: decide con un temporizador exacto — ¿pasaron 40 minutos desde el último riego? SÍ o NO.',
              'Si SÍ, abre la válvula de riego. Si NO, sigue cerrada. Ninguna decisión queda a la imaginación del sistema.',
              'Un programa en Python funciona igual: cada `if` compara algo medible — un número, un texto, un resultado — nunca una idea vaga. Ahora hazlo tú: arma la decisión del riego.',
            ],
            practice: {
              kind: 'ordering',
              prompt: 'Arma la decisión que toma el riego del jardín. Una de las frases no es evaluable — descártala.',
              items: [
                { id: 's1', text: 'Consulta el temporizador: ¿pasaron 40 minutos?', position: 1 },
                { id: 's2', text: 'Si pasaron 40 minutos, abre la válvula de riego', position: 2 },
                { id: 's3', text: 'Si no pasaron 40 minutos, mantén la válvula cerrada', position: 3 },
                {
                  id: 'sd1',
                  text: 'Riega cuando la tierra se vea seca',
                  position: null,
                  whyWrong:
                    '«Se vea seca» no tiene un umbral exacto — el sistema no puede medirlo como SÍ o NO.',
                },
              ],
              successFeedback:
                'Exacto — armaste una decisión que cualquier sistema de riego (o programa) evalúa igual, sin ambigüedad.',
              orderFeedback: 'El sistema no puede decidir sin consultar antes el temporizador.',
              generalHint: 'Una de las frases no se puede medir con un número exacto. Esa no es una condición evaluable.',
              solutionExplanation: [
                'Primero se consulta el temporizador, después se decide según su resultado — «se vea seca» era la condición vaga, igual que «mal tiempo» o «cuando el robot quiera pasar».',
              ],
            },
            pythonBridge: {
              label: 'Esto ya es Python',
              code: 'if temporizador.transcurrio(minutos=40):\n    abrir_valvula_riego()\nelse:\n    mantener_valvula_cerrada()',
              explanation:
                'La decisión de riego que acabas de armar es exactamente este `if`/`else`: una condición medible (¿pasaron 40 minutos?) y una acción para cada resultado — sin "se vea seca" en ninguna parte.',
            },
          },
          {
            kind: 'audio',
            label: 'Escuchar otra explicación',
            title: 'Escúchalo de otra forma',
            medium: 'clip_narrado',
            narrationText:
              'Piensa en una regla que sigues todos los días, como: si hace frío, me pongo casaca. Para ti, frío es obvio. Para una máquina no existe frío: existe una temperatura, un número, y una comparación exacta con ese número. Una condición evaluable siempre se puede responder con sí o no. Si no puedes responder sí o no de inmediato, todavía no es una condición: es una idea. Y Python, con if y else, solo entiende condiciones, nunca ideas.',
            body: [
              'Piensa en una regla que sigues todos los días, como «si hace frío, me pongo casaca». Para ti, «frío» es obvio. Para una máquina no existe «frío»: existe una temperatura, un número, y una comparación exacta.',
              'Una condición evaluable siempre se puede responder con SÍ o NO. Si no puedes responder de inmediato, todavía no es una condición: es una idea.',
              'Python, con `if` y `else`, solo entiende condiciones — nunca ideas.',
            ],
          },
        ],
      },

      // ── Escalera de remediación ──────────────────────────────────────────────
      remediation: {
        steps: [
          {
            level: 1,
            title: 'Volvamos sobre la regla, con un caso resuelto',
            conceptModality: 'same',
            body: [
              'Una condición es evaluable cuando se reduce a SÍ o NO, sin que quede ninguna duda de cómo medirla. Si al leerla te preguntas «¿y eso cuánto es?» o «¿quién decide?», entonces la máquina también se lo pregunta — y ahí falla. Python te exigirá exactamente lo mismo en cada `if`.',
            ],
            illustration: {
              medium: 'ejemplo_comentado',
              mediumLabel: 'Ejemplo resuelto paso a paso',
              body: [
                'Meta: que una alarma decida si sonar por exceso de temperatura.',
                '1. «Consulta el termómetro» — obtiene un número. Evaluable.',
                '2. «Si el número supera 40°C, activa la alarma» — comparación exacta. Evaluable.',
                '3. «Si el número no supera 40°C, mantén la alarma apagada» — cubre el otro caso. Evaluable.',
                'Descartada: «suena si hace mucho calor». Es una idea, no una condición: no dice qué número ni qué umbral. Fíjate en el patrón: toda condición evaluable se puede responder con SÍ o NO.',
              ],
            },
            practice: {
              kind: 'ordering',
              prompt: 'Ordena los pasos para que un termostato decida si encender la calefacción. Descarta el que sea ambiguo.',
              items: [
                { id: 't1', text: 'Consulta el termómetro', position: 1 },
                {
                  id: 'td1',
                  text: 'Enciende si hace frío',
                  position: null,
                  whyWrong: '«Si hace frío» es una idea, no una condición: no dice qué temperatura exacta activa el cambio.',
                },
                { id: 't2', text: 'Si la temperatura es menor a 18°C, enciende la calefacción', position: 2 },
                { id: 't3', text: 'Si la temperatura es 18°C o más, mantenla apagada', position: 3 },
              ],
              successFeedback: 'Eso es — separaste la idea vaga («hace frío») de una condición realmente evaluable.',
              orderFeedback: 'El termostato no puede decidir sin haber consultado antes el termómetro.',
              generalHint: 'Una de esas frases no dice qué número exacto activa la decisión. Búscala.',
            },
          },
          {
            level: 2,
            title: 'Probemos con otra representación, y más despacio',
            conceptModality: 'alternate',
            body: [
              'Piensa en un sensor de calidad de aire con un umbral exacto. «El aire está mal» no sirve de regla: la regla real es «el aire está mal si el CO2 supera 800 ppm» — un número exacto, comparado con otro.',
              'Un `if` en Python es exactamente esa comparación: nunca «está mal», siempre un número o un valor exacto contra otro. Ahora practica con dos pasos y un impostor.',
            ],
            illustration: {
              medium: 'diagrama',
              mediumLabel: 'Analogía visual: idea vs. condición',
              body: [
                '📊 [ EL AIRE ESTÁ MAL ]  ← la idea. La máquina no sabe evaluarla.',
                '     ├── «¿El CO2 supera 800 ppm?»   ← evaluable (SÍ/NO)',
                '     └── «Si SÍ: enciende el ventilador. Si NO: lo mantiene apagado»   ← acción exacta por caso',
                'Todo lo que esté en la caja de arriba es una idea. Todo lo que cuelga de ella es una condición evaluable.',
              ],
              // Auditoría "infografías" (jul 2026): ver misma nota en
              // module1/ciclo1-instrucciones-precisas.ts (segunda vuelta) —
              // `imageAsset` ya está listo para resolver contra
              // illustrationAssets.ts. A diferencia de los otros tres
              // (siempre 2 ramas rectangulares), este SÍ es una condición
              // booleana real — el prompt usa el rombo de decisión estándar
              // de diagramas de flujo, coherente con el concepto if/else.
              imageAsset: 'm2-c1-l2-aire-mal',
              imagePrompt:
                'Mini diagrama de flujo para una app educativa de programación, modo oscuro.\n\n' +
                'COMPOSICIÓN: un nodo superior centrado (rectángulo, la IDEA vaga "el aire está mal"), que baja a un ROMBO de decisión (la condición evaluable "¿el CO2 supera 800 ppm?"), del que salen dos ramas etiquetadas SÍ / NO hacia dos nodos rectangulares finales (los resultados "enciende el ventilador" / "lo mantiene apagado"). Es un flujo vertical de arriba hacia abajo: idea → condición → dos resultados posibles.\n\n' +
                'ESTILO: interfaz "glassmorphism" oscura, iconografía plana de diagrama de flujo real (rombo = decisión, rectángulo = proceso/resultado), sin fotorrealismo, coherente con un producto SaaS educativo.\n\n' +
                'COLORES: fondo casi negro #0a0a0f. Nodo superior (idea vaga): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Rombo de decisión: borde SÓLIDO cian #06b6d4, relleno cian al 8%. Los dos nodos de resultado: borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Líneas conectoras gris translúcido rgba(255,255,255,0.15), con las etiquetas "SÍ" y "NO" en violeta #7c3aed junto a cada rama. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.\n\n' +
                'ICONOS: signo de interrogación pequeño junto al nodo superior (idea, ambigua). Un pequeño ícono de sensor/medidor dentro del rombo (evaluación). Un ícono de ventilador junto al resultado "enciende el ventilador" y un ícono de ventilador apagado (sutil, mismo tamaño) junto a "lo mantiene apagado" — ambos igual de neutrales en tamaño, ningún resultado debe verse "más importante" que el otro.\n\n' +
                'DISTRIBUCIÓN: formato vertical 4:5 o 3:4. Nodo idea arriba (~15% de la altura), rombo de decisión al centro (~25%), los dos resultados abajo distribuidos simétricamente izquierda/derecha (~30%), con espacio en blanco generoso entre cada nivel.\n\n' +
                'ELEMENTOS DE TEXTO (incluir literalmente):\n' +
                '— Nodo superior: "EL AIRE ESTÁ MAL" + subtítulo pequeño "la idea — la máquina no sabe evaluarla"\n' +
                '— Rombo: "¿El CO2 supera 800 ppm?"\n' +
                '— Resultado izquierdo (rama SÍ): "Enciende el ventilador"\n' +
                '— Resultado derecho (rama NO): "Lo mantiene apagado"\n' +
                '— Leyenda inferior centrada, fuera de los nodos: "Todo lo de arriba es una idea. Todo lo que cuelga de ella es una condición evaluable."',
            },
            practice: {
              kind: 'ordering',
              prompt: 'Solo dos pasos y un impostor. Ordena para que el sistema decida si encender el ventilador.',
              items: [
                { id: 'e1', text: 'Consulta el sensor de CO2', position: 1 },
                {
                  id: 'ed1',
                  text: 'Decide si el aire está mal',
                  position: null,
                  whyWrong: '«Si el aire está mal» no tiene un umbral exacto — no es una condición evaluable.',
                },
                { id: 'e2', text: 'Si el CO2 es 800 ppm o más, enciende el ventilador', position: 2 },
              ],
              successFeedback: 'Exacto. Consultar el sensor primero, comparar con 800 después — y «el aire está mal» era la idea vaga.',
              orderFeedback: 'No puedes comparar un valor de CO2 que todavía no consultaste.',
              generalHint: 'Solo una de las frases NO se puede comparar con un número exacto.',
              solutionExplanation: [
                'Primero se obtiene el dato (el CO2), después se compara con un umbral exacto (800). «El aire está mal» era la idea, igual que «hace frío» o «mal tiempo».',
              ],
            },
          },
          {
            level: 3,
            title: 'Te acompaño con la solución completa',
            conceptModality: 'alternate',
            body: [
              'Necesitaste ayuda máxima en este concepto, y eso queda registrado — no como una falta, sino para que el sistema sepa qué reforzar contigo más adelante.',
              'Revisa la secuencia resuelta y su explicación. La misión continúa.',
            ],
          },
        ],
      },
    },
  ],

  // ── Cierre ─────────────────────────────────────────────────────────────────
  // Módulo 3 ("Funciones y módulos") sigue en modo legacy (sin experiencia
  // propia): por PED-004, el cierre no anuncia una misión externa todavía.
  closing: {
    achievement:
      'Construiste tu primera condición evaluable, separándola de una idea vaga disfrazada de decisión — la base de toda estructura de control. Esa misma exigencia es la que Python aplicará a cada `if`, `elif` y `else` que escribas.',

    hypothesis: {
      verdicts: {
        'Nada — sabrá cuándo hace mal tiempo': {
          label: 'Ahora lo sabes',
          text:
            'Pensaste que el robot reconocería el mal tiempo por su cuenta. Hoy comprobaste lo contrario: sin una condición medible, no tiene forma de decidir. «Si hace mal tiempo» no es evaluable — le falta el umbral exacto. Que tu idea haya cambiado no es un error: es la prueba de que aprendiste.',
        },
        'No sabría cuándo activarse': {
          label: 'Acertaste',
          text:
            'Predijiste que el robot no sabría cuándo activarse — y eso es exactamente lo que pasa sin una condición evaluable: se queda sin criterio. Hoy comprobaste por qué: la máquina solo reacciona a SÍ o NO, nunca a una idea. Tu hipótesis quedó confirmada por el experimento.',
        },
        'Abriría o cerraría el paraguas al azar': {
          label: 'Te acercaste',
          text:
            'Intuiste que el resultado sería impredecible — muy cerca de la verdad. Hoy comprobaste POR QUÉ: sin una condición exacta, no hay ningún criterio consistente que seguir. Tu intuición ahora tiene una regla que la explica.',
        },
      },
      coda:
        'Cuando escribas tu primer `if` en Python, el lenguaje exigirá exactamente esta claridad: una condición evaluable y una acción para cada resultado posible.',
    },
  },
}
