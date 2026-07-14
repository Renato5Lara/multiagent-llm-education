// Módulo 2 · "Decisiones que la máquina entiende" — instancia del Patrón de
// Experiencia. Mismo patrón congelado que Módulo 1 (jul 2026): apertura de
// curiosidad + Ciclo 1. Los ciclos 2-3 (bucles, comprensiones) y el reto
// integrador entran en incrementos siguientes, igual que en Módulo 1.

import type { ModuleExperienceDefinition } from '@/types/moduleExperience'

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
      curiosityFact: {
        fact:
          'En 1883, Warren Johnson inventó el primer termostato eléctrico: una tira de dos metales que se dobla con el calor. Cuando se dobla lo suficiente (la condición), cierra un circuito y corta la calefacción — si no, la mantiene encendida.',
        connection:
          'Ese termostato de 1883 ya tenía exactamente la estructura que vas a construir hoy: una condición que se puede medir como SÍ o NO, y una acción distinta para cada resultado — sin escribir una sola línea de código.',
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
              'Respuesta: nada — se queda inmóvil con error. «Mal tiempo» no es una condición que pueda evaluar: no sabe qué medir.',
              'Ahora predice con esta otra: «si el sensor detecta gotas, abre el paraguas; si no, mantenlo cerrado». Empieza a llover. ¿Qué hace? Sí: abre el paraguas — el sensor respondió SÍ, y esa respuesta activa una acción exacta.',
              'Ese mismo robot mental es el que usarás con `if` en Python: una condición que se responde con SÍ o NO, y una acción para cada resultado.',
            ],
          },
        },
      },
      practice: {
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
      pythonBridge: {
        label: 'Esto ya es Python',
        code: 'if sensor_lluvia.detecta_gotas():\n    abrir_paraguas()\nelse:\n    mantener_cerrado()',
        explanation:
          'La condición que acabas de evaluar es exactamente lo que Python llama `if`: una pregunta que solo puede ser verdadera o falsa. `else` es lo que hiciste con «si el sensor marca NO» — la acción para el otro caso.',
      },
      decision: {
        question:
          'Ya entiendes qué hace evaluable a una condición — y por qué eso mismo aplica cuando programas con `if`. ¿Cómo quieres consolidarlo?',
        reinforcements: [
          {
            kind: 'reto',
            label: 'Resolver un reto rápido',
            title: 'Reto: la puerta automática',
            body: ['Misma regla: solo condiciones evaluables, en orden. Hay un impostor.'],
            practice: {
              kind: 'ordering',
              prompt: 'Ordena los pasos para que la puerta automática decida si abrirse. Descarta el que sea ambiguo.',
              items: [
                { id: 'a1', text: 'Consulta el sensor de peso frente a la puerta', position: 1 },
                { id: 'a2', text: 'Si detecta peso, abre la puerta', position: 2 },
                { id: 'a3', text: 'Si no detecta peso, mantén la puerta cerrada', position: 3 },
                {
                  id: 'ad1',
                  text: 'Abre cuando alguien quiera pasar',
                  position: null,
                  whyWrong:
                    '«Cuando alguien quiera pasar» no es medible por un sensor — no dice qué condición evaluar.',
                },
              ],
              successFeedback: 'Perfecto — detectaste que la condición vaga era el impostor.',
              orderFeedback: 'La puerta no puede decidir sin haber consultado antes el sensor de peso.',
              generalHint: 'Una de esas frases no dice qué puede medir un sensor. ¿Cuál?',
              solutionExplanation: [
                '«Abre cuando alguien quiera pasar» describe una intención, no algo medible. Las otras tres sí son evaluables: consultan un sensor real y responden SÍ o NO.',
              ],
            },
          },
          {
            kind: 'ejemplo',
            label: 'Ver un ejemplo más',
            title: 'Ejemplo: el semáforo peatonal',
            medium: 'ejemplo_comentado',
            body: [
              'Un semáforo peatonal nunca decide «cuando haya poco tráfico»: decide con un temporizador exacto — ¿pasaron 40 segundos? SÍ o NO.',
              'Si SÍ, cambia a verde peatonal. Si NO, sigue en rojo. Ninguna decisión queda a la imaginación del semáforo.',
              'Un programa en Python funciona igual: cada `if` compara algo medible — un número, un texto, un resultado — nunca una idea vaga. Ahora hazlo tú: arma la decisión del semáforo.',
            ],
            practice: {
              kind: 'ordering',
              prompt: 'Arma la decisión que toma el semáforo peatonal. Una de las frases no es evaluable — descártala.',
              items: [
                { id: 's1', text: 'Consulta el temporizador: ¿pasaron 40 segundos?', position: 1 },
                { id: 's2', text: 'Si pasaron 40 segundos, cambia a verde peatonal', position: 2 },
                { id: 's3', text: 'Si no pasaron 40 segundos, mantente en rojo', position: 3 },
                {
                  id: 'sd1',
                  text: 'Cambia cuando haya poco tráfico',
                  position: null,
                  whyWrong:
                    '«Poco tráfico» no tiene un umbral exacto — el semáforo no puede medirlo como SÍ o NO.',
                },
              ],
              successFeedback:
                'Exacto — armaste una decisión que cualquier semáforo (o programa) evalúa igual, sin ambigüedad.',
              orderFeedback: 'El semáforo no puede decidir el color antes de consultar el temporizador.',
              generalHint: 'Una de las frases no se puede medir con un número exacto. Esa no es una condición evaluable.',
              solutionExplanation: [
                'Primero se consulta el temporizador, después se decide el color según su resultado — «poco tráfico» era la condición vaga, igual que «mal tiempo» o «cuando alguien quiera pasar».',
              ],
            },
            pythonBridge: {
              label: 'Esto ya es Python',
              code: 'if temporizador.transcurrio(segundos=40):\n    cambiar_a_verde_peatonal()\nelse:\n    mantener_en_rojo()',
              explanation:
                'La decisión del semáforo que acabas de armar es exactamente este `if`/`else`: una condición medible (¿pasaron 40 segundos?) y una acción para cada resultado — sin "poco tráfico" en ninguna parte.',
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
              'Piensa en un examen con nota mínima para aprobar. «Aprobó si le fue bien» no sirve de regla: la regla real es «aprobó si su nota es 11 o más» — un número exacto, comparado con otro.',
              'Un `if` en Python es exactamente esa comparación: nunca «le fue bien», siempre un número o un valor exacto contra otro. Ahora practica con dos pasos y un impostor.',
            ],
            illustration: {
              medium: 'diagrama',
              mediumLabel: 'Analogía visual: idea vs. condición',
              body: [
                '📊 [ APROBÓ EL EXAMEN ]  ← la idea. La máquina no sabe evaluarla.',
                '     ├── «¿La nota es 11 o más?»   ← evaluable (SÍ/NO)',
                '     └── «Si SÍ: aprobó. Si NO: desaprobó»   ← acción exacta por caso',
                'Todo lo que esté en la caja de arriba es una idea. Todo lo que cuelga de ella es una condición evaluable.',
              ],
            },
            practice: {
              kind: 'ordering',
              prompt: 'Solo dos pasos y un impostor. Ordena para que el sistema decida si el estudiante aprobó.',
              items: [
                { id: 'e1', text: 'Consulta la nota final del estudiante', position: 1 },
                {
                  id: 'ed1',
                  text: 'Decide si le fue bien',
                  position: null,
                  whyWrong: '«Si le fue bien» no tiene un umbral exacto — no es una condición evaluable.',
                },
                { id: 'e2', text: 'Si la nota es 11 o más, márcalo como aprobado', position: 2 },
              ],
              successFeedback: 'Exacto. Consultar la nota primero, comparar con 11 después — y «le fue bien» era la idea vaga.',
              orderFeedback: 'No puedes comparar una nota que todavía no consultaste.',
              generalHint: 'Solo una de las frases NO se puede comparar con un número exacto.',
              solutionExplanation: [
                'Primero se obtiene el dato (la nota), después se compara con un umbral exacto (11). «Le fue bien» era la idea, igual que «hace frío» o «mal tiempo».',
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
