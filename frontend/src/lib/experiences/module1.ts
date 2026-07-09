// Módulo 1 · "El idioma de las máquinas" — instancia del Patrón de Experiencia.
// Contenido según la referencia funcional congelada (jul 2026).
// S1 incremento 1: apertura de curiosidad + Ciclo 1 (Instrucciones precisas).
// Los ciclos 2-3 y el reto integrador entran en los siguientes incrementos.

import type { ModuleExperienceDefinition } from '@/types/moduleExperience'

export const MODULE_1_EXPERIENCE: ModuleExperienceDefinition = {
  moduleNumber: 1,
  missionTitle: 'Misión 1 · El idioma de las máquinas',
  territory: 'Explorador',
  // "Fundamentos de Python" es el primer módulo de la ruta seedeada (IS301):
  // la experiencia del Módulo 1 se activa ahí. Los otros títulos cubren el
  // canon de 9 módulos de Fundamentos.
  matchTitles: ['introduccion a la programacion', 'fundamentos de python'],

  // ── Apertura: la curiosidad antes que el tema ────────────────────────────────
  opening: {
    questionLines: [
      'Tienes un robot en casa. Obedece absolutamente todo, al pie de la letra.',
      'Le dices: «prepárame un sándwich».',
      '¿Qué puede salir mal?',
    ],
    options: [
      'Nada — es un robot, sabe hacerlo',
      'No sabría por dónde empezar',
      'Haría algo absurdo',
    ],
    freeTextPrompt: '¿Qué crees que haría exactamente? (opcional)',
    revealHook:
      'Los robots no imaginan nada: ejecutan lo que dices, exactamente como lo dices. ' +
      'Decirle a una máquina qué hacer sin dejar nada a su imaginación es, precisamente, ' +
      'lo que resuelven los programadores.',
  },

  cycles: [
    // ── Ciclo 1: Instrucciones precisas ────────────────────────────────────────
    {
      id: 'ciclo-1',
      conceptId: 'instrucciones_precisas',
      conceptLabel: 'Instrucciones precisas',
      priorMastery: 0.2,
      concept: {
        title: '¿Qué hace precisa a una instrucción?',
        variants: {
          visual: {
            medium: 'infografia',
            mediumLabel: 'Infografía',
            sourceNote: 'Elegido para ti — tu perfil capta ideas más rápido cuando las ve.',
            body: [
              'VAGA: «Ponle mantequilla al pan» → ¿con qué? ¿cuánta? ¿en qué lado?',
              'PRECISA: «Toma el cuchillo. Unta 10 gramos de mantequilla sobre la cara superior de la rebanada.»',
              'La diferencia no es la cortesía ni el detalle decorativo: es que la instrucción precisa no deja NINGUNA decisión en manos del robot.',
              'Una instrucción es precisa cuando cualquier ejecutor — humano o máquina — produce exactamente el mismo resultado.',
            ],
          },
          reading: {
            medium: 'texto',
            mediumLabel: 'Texto estructurado',
            sourceNote: 'Elegido para ti — tu perfil profundiza mejor leyendo a su ritmo.',
            body: [
              'En 2018, un profesor pidió a sus estudiantes instrucciones escritas para preparar un sándwich, y las ejecutó al pie de la letra. Untó la mantequilla con la mano (nadie mencionó el cuchillo), apiló el pan sin abrir la bolsa y colocó el jamón sellado en su empaque.',
              'No estaba saboteando: estaba ejecutando. Cada instrucción que asumía algo — «unta la mantequilla», ¿con qué? — dejaba una decisión en manos del ejecutor. Y una máquina no decide: se detiene o hace algo absurdo.',
              'Una instrucción es precisa cuando no requiere que el ejecutor adivine nada: qué objeto usar, cuánto, dónde, en qué orden. Ese es el primer hábito mental de la programación.',
            ],
          },
          audio: {
            medium: 'clip_narrado',
            mediumLabel: 'Clip narrado',
            sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
            body: [
              '🎧 Guion del clip (60 s): «Imagina que le escribes instrucciones a alguien que jamás ha visto un sándwich… y que hará EXACTAMENTE lo que escribiste. "Pon mantequilla en el pan". ¿Con la mano? ¿Con el codo? Tú sabías que era con cuchillo — pero no lo dijiste, y el ejecutor no adivina.',
              'Esa es la regla de oro: si tu instrucción necesita que el otro adivine algo, no es una instrucción — es un deseo. Las máquinas no cumplen deseos. Ejecutan instrucciones.»',
            ],
          },
          kinesthetic: {
            medium: 'simulacion',
            mediumLabel: 'Simulación',
            sourceNote: 'Elegido para ti — tu perfil construye comprensión haciendo.',
            body: [
              '🤖 Antes de leer nada, predice: el robot recibe «pon la mantequilla en el pan». Tiene un cuchillo, una cuchara y sus pinzas metálicas. ¿Qué usará?',
              'Respuesta: ninguna de las tres — se detiene con error. La instrucción no dice QUÉ usar, y el robot no elige por ti.',
              'Ahora predice con esta otra: «toma el cuchillo con la pinza derecha y unta la mantequilla sobre la cara superior de la rebanada». ¿Se detiene? No: ejecuta. Nada quedó a su imaginación — eso es una instrucción precisa.',
            ],
          },
        },
      },
      practice: {
        kind: 'ordering',
        prompt:
          'El robot debe cruzar la habitación y abrir la puerta sin chocar. Construye la secuencia usando SOLO instrucciones precisas — una de la lista es ambigua y debes descartarla.',
        // Decisión PO (Opción A, jul 2026): "Ve hacia la puerta" se eliminó del
        // banco — admitía leerse como objetivo+detalle junto a "Avanza 4 pasos"
        // y esa ambigüedad interpretativa no es la que el ejercicio enseña.
        items: [
          { id: 'p3', text: 'Avanza 4 pasos', position: 3 },
          {
            id: 'd1',
            text: 'Camina hacia adelante',
            position: null,
            whyWrong: '«Camina hacia adelante» — ¿cuántos pasos? El robot no adivina: una instrucción sin cantidad es una instrucción ambigua.',
          },
          { id: 'p1', text: 'Ponte de pie frente a la mesa', position: 1 },
          { id: 'p5', text: 'Extiende la mano y gira la manija', position: 5 },
          { id: 'p2', text: 'Gira 90 grados a la izquierda', position: 2 },
          { id: 'p4', text: 'Detente frente a la puerta', position: 4 },
        ],
        successFeedback:
          'Exacto: cinco instrucciones sin espacio para la imaginación del robot. Y descartaste la ambigua — eso es pensar como programador.',
        orderFeedback:
          'El robot ejecuta EXACTAMENTE en la secuencia que le das: no puede girar la manija antes de llegar a la puerta.',
        generalHint:
          'El robot se detuvo: hay algo en tu secuencia que no puede ejecutar. Revisa si cada instrucción le dice exactamente qué hacer, cuánto y hacia dónde.',
        solutionExplanation: [
          'Cada paso responde las tres preguntas que un robot no puede adivinar: qué hacer, cuánto y hacia dónde. «Avanza 4 pasos» es ejecutable; «camina hacia adelante» no, porque el cuánto queda a su imaginación.',
          'Fíjate además en el orden: el robot no puede avanzar antes de girar, ni girar la manija antes de detenerse frente a la puerta. Una secuencia es un camino donde cada paso prepara el siguiente.',
        ],
      },
      decision: {
        question: 'Ya entiendes lo que hace precisa a una instrucción. ¿Cómo quieres reforzarlo?',
        reinforcements: [
          {
            kind: 'reto',
            label: 'Resolver un reto rápido',
            title: 'Reto: el robot riega una planta',
            body: ['Misma regla: solo instrucciones precisas, en orden. Hay un impostor.'],
            practice: {
              kind: 'ordering',
              prompt: 'Ordena las instrucciones para que el robot riegue la planta. Descarta la que sea ambigua.',
              items: [
                { id: 'r2', text: 'Llena la regadera con agua hasta la mitad', position: 2 },
                {
                  id: 'rd1',
                  text: 'Riega la planta',
                  position: null,
                  whyWrong: '«Riega la planta» es el objetivo, no una instrucción: no dice con qué, cuánta agua ni dónde verterla.',
                },
                { id: 'r1', text: 'Toma la regadera del estante', position: 1 },
                { id: 'r3', text: 'Vierte el agua sobre la tierra de la maceta grande', position: 3 },
              ],
              successFeedback: 'Perfecto — detectaste que el objetivo disfrazado de instrucción era el impostor.',
              orderFeedback: 'No puedes verter agua de una regadera que aún no has llenado.',
              generalHint:
                'Una de esas órdenes no es una instrucción: es un objetivo disfrazado. ¿Cuál no dice CÓMO hacerlo?',
              solutionExplanation: [
                '«Riega la planta» describe el resultado que quieres, no los pasos para lograrlo. Las otras tres sí son ejecutables: dicen qué objeto usar, cuánta agua y dónde verterla — y en un orden donde cada paso hace posible el siguiente.',
              ],
            },
          },
          {
            kind: 'ejemplo',
            label: 'Ver un ejemplo más',
            title: 'Ejemplo: el GPS de tu teléfono',
            medium: 'ejemplo_comentado',
            body: [
              'Tu GPS nunca dice «ve hacia el centro». Dice: «en 200 metros, gira a la derecha en la Av. América».',
              'Distancia exacta, acción exacta, lugar exacto. El GPS te habla como se le habla a una máquina — por eso cualquier conductor que siga sus instrucciones llega al mismo lugar.',
            ],
          },
          {
            kind: 'animacion',
            label: 'Ver una animación',
            title: 'Dos robots, dos destinos',
            medium: 'animacion',
            sceneId: 'dos-robots',
            body: [
              'Mismo robot, misma meta. El primero recibió «cruza la habitación» y terminó contra la mesa; el segundo recibió tres instrucciones precisas — y llegó. La única diferencia fue la precisión.',
            ],
          },
          {
            kind: 'audio',
            label: 'Escuchar otra explicación',
            title: 'Escúchalo de otra forma',
            medium: 'clip_narrado',
            narrationText:
              'Piensa en la última vez que le explicaste algo a alguien y te entendió mal. Seguro dijiste: pero era obvio. Para una máquina, nada es obvio. Una instrucción precisa dice qué hacer, con qué, cuánto y hacia dónde. Si falta una de esas piezas, el robot va a fallar.',
            body: [
              'Piensa en la última vez que le explicaste algo a alguien y te entendió mal. Seguro dijiste «¡pero era obvio!». Para una máquina nada es obvio: una instrucción precisa dice qué hacer, con qué, cuánto y hacia dónde. Si falta una de esas piezas, el robot va a fallar.',
            ],
          },
        ],
      },

      // ── Escalera de remediación ──────────────────────────────────────────────
      // Cada peldaño: otra explicación + otra experiencia + otra actividad, más
      // simple que la anterior. El Nivel 3 siempre deja continuar.
      remediation: {
        steps: [
          {
            level: 1,
            title: 'Volvamos sobre la regla, con un caso resuelto',
            conceptModality: 'same',
            body: [
              'Una instrucción es precisa cuando el robot no necesita decidir nada por su cuenta. Si al leerla te preguntas «¿cuánto?», «¿hacia dónde?» o «¿con qué?», entonces el robot también se lo pregunta — y ahí falla.',
            ],
            illustration: {
              medium: 'ejemplo_comentado',
              mediumLabel: 'Ejemplo resuelto paso a paso',
              body: [
                'Meta: que el robot apague la luz de la cocina.',
                '1. «Camina hasta el interruptor de la cocina» — dice hasta dónde. Precisa.',
                '2. «Levanta la mano derecha hasta el interruptor» — dice qué mano y hasta dónde. Precisa.',
                '3. «Presiona el interruptor hacia abajo» — dice la acción y la dirección. Precisa.',
                'Descartada: «apaga la luz». Es la META, no un paso. No dice cómo llegar ni qué mover. Fíjate en el patrón: cada paso deja al robot listo para el siguiente.',
              ],
            },
            practice: {
              kind: 'ordering',
              prompt: 'Ordena las instrucciones para que el robot encienda la lámpara del escritorio. Descarta la que sea ambigua.',
              items: [
                { id: 'l1', text: 'Camina hasta el escritorio', position: 1 },
                {
                  id: 'ld1',
                  text: 'Enciende la lámpara',
                  position: null,
                  whyWrong: '«Enciende la lámpara» es la meta, no una instrucción: no dice qué mover ni en qué dirección.',
                },
                { id: 'l2', text: 'Extiende la mano hasta el botón de la lámpara', position: 2 },
                { id: 'l3', text: 'Presiona el botón una vez', position: 3 },
              ],
              successFeedback: 'Eso es — separaste la meta («enciende la lámpara») de los pasos que la hacen posible.',
              orderFeedback: 'El robot no puede presionar un botón que todavía no alcanzó.',
              generalHint: 'Una de esas frases dice QUÉ quieres que pase, no QUÉ debe hacer el robot. Búscala.',
            },
          },
          {
            level: 2,
            title: 'Probemos con otra representación, y más despacio',
            conceptModality: 'alternate',
            body: [
              'Piensa en una receta de cocina. «Prepara la masa» no es un paso: es el título. Los pasos son «vierte 200 g de harina», «añade un huevo», «mezcla durante dos minutos».',
              'El robot solo entiende los pasos de la receta, nunca el título. Ahora practica con solo dos pasos y un impostor.',
            ],
            illustration: {
              medium: 'diagrama',
              mediumLabel: 'Analogía visual: título vs. pasos',
              body: [
                '📊 [ HACER UN CAFÉ ]  ← el título. El robot no sabe ejecutarlo.',
                '     ├── «Vierte 200 ml de agua en la jarra»   ← ejecutable',
                '     └── «Presiona el botón de encendido»      ← ejecutable',
                'Todo lo que esté en la caja de arriba es una meta. Todo lo que cuelga de ella son instrucciones.',
              ],
            },
            practice: {
              kind: 'ordering',
              prompt: 'Solo dos pasos y un impostor. Ordena para que el robot abra la ventana.',
              items: [
                { id: 'v1', text: 'Gira la manija de la ventana hacia abajo', position: 1 },
                {
                  id: 'vd1',
                  text: 'Ventila la habitación',
                  position: null,
                  whyWrong: '«Ventila la habitación» es el resultado que quieres, no una acción que el robot pueda ejecutar.',
                },
                { id: 'v2', text: 'Empuja el marco de la ventana hacia afuera', position: 2 },
              ],
              successFeedback: 'Exacto. Girar la manija primero, empujar después — y «ventilar» era la meta.',
              orderFeedback: 'No puedes empujar una ventana cuya manija sigue cerrada.',
              generalHint: 'Solo una de las tres frases NO le dice al robot qué mover.',
              solutionExplanation: [
                'Primero «gira la manija hacia abajo»: libera el cierre. Después «empuja el marco hacia afuera»: solo es posible con el cierre liberado.',
                '«Ventila la habitación» describe para qué lo haces, no qué hacer. Ese es el impostor, igual que «riega la planta» o «enciende la lámpara».',
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

  // ── Cierre: puente hacia la misión REAL que sigue en la ruta ─────────────────
  // La Misión 02 de la ruta es «Estructuras de control». El cierre debe apuntar
  // ahí, con la misma narrativa del robot — nunca a promesas internas del sprint.
  closing: {
    achievement:
      'Construiste «Instrucciones precisas» descartando las órdenes ambiguas — el error más común de quienes empiezan. Ya sabes cómo se le habla a una máquina: sin dejar nada a su imaginación.',
    nextMission: {
      title: 'Estructuras de control',
      hook: 'Tu robot ya obedece paso a paso. Pero ¿qué hace si la puerta está cerrada con llave? ¿Y si debe tocar 4 veces hasta que le abran? Enseñarle a decidir y a repetir es tu siguiente misión.',
    },
  },
}
