// Módulo 1 · "El idioma de las máquinas" — instancia del Patrón de Experiencia.
// Contenido según la referencia funcional congelada (jul 2026).
// S1 incremento 1: apertura de curiosidad + Ciclo 1 (Instrucciones precisas).
// Los ciclos 2-3 y el reto integrador entran en los siguientes incrementos.

import type { ModuleExperienceDefinition } from '@/types/moduleExperience'

export const MODULE_1_EXPERIENCE: ModuleExperienceDefinition = {
  moduleNumber: 1,
  missionTitle: 'Misión 1 · El idioma de las máquinas',
  // m-6: la ruta presenta el módulo con este título; la revelación lo cita
  // para que el estudiante entienda que la misión temática ES ese módulo.
  routeTitle: 'Fundamentos de Python',
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
      'Decirle a una máquina qué hacer sin dejar nada a su imaginación es exactamente lo ' +
      'que hace un programador. Y una computadora funciona igual que ese robot: ejecuta lo ' +
      'que le dices, al pie de la letra, sin imaginar nada. En esta misión vas a entender ' +
      'por qué eso importa — antes de escribir tu primera línea.',
  },

  cycles: [
    // ── Ciclo 1: Instrucciones precisas ────────────────────────────────────────
    {
      id: 'ciclo-1',
      conceptId: 'instrucciones_precisas',
      conceptLabel: 'Instrucciones precisas',
      priorMastery: 0.2,
      curiosityFact: {
        fact:
          'En 1801, el telar de Jacquard tejía patrones complejos usando tarjetas perforadas: cada agujero (o su ausencia) le decía a la máquina exactamente qué hilo levantar. Sin una tarjeta ambigua — el telar no sabía "interpretar", solo ejecutar.',
        connection:
          'Ese telar resolvía el mismo problema que vas a resolver hoy, más de un siglo antes de la primera computadora: cómo darle instrucciones a una máquina que no puede adivinar nada.',
      },
      concept: {
        title: '¿Qué hace precisa a una instrucción?',
        secondExample: {
          label: 'Otro caso — el manual de una silla',
          body: [
            'Un manual de ensamblaje nunca dice «arma la silla»: dice «atornilla la pata en la esquina inferior izquierda con el tornillo A, hasta que quede firme». Qué pieza, dónde, con qué tornillo y hasta cuándo — nada queda a tu imaginación.',
            'Es la misma regla del pan, en un contexto completamente distinto: una instrucción precisa no cambia según el tema, cambia según cuánto deja adivinar.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'untar(herramienta="cuchillo", ingrediente="mantequilla", gramos=10, lado="superior")',
          explanation:
            'Fíjate: la instrucción precisa del pan («toma el cuchillo, unta 10 gramos...») y esta línea de Python dicen exactamente lo mismo — qué hacer, con qué, cuánto y dónde. Una función en Python es, ni más ni menos, una instrucción precisa con nombre.',
        },
        variants: {
          visual: {
            medium: 'infografia',
            mediumLabel: 'Infografía',
            sourceNote: 'Elegido para ti — tu perfil capta ideas más rápido cuando las ve.',
            infographic: {
              vague: {
                instruction: 'Ponle mantequilla al pan',
                questions: ['¿con qué?', '¿cuánta?', '¿en qué lado?'],
              },
              precise: {
                instruction: 'Toma el cuchillo. Unta 10 gramos de mantequilla sobre la cara superior de la rebanada.',
                parts: ['qué hacer', 'con qué', 'cuánto', 'dónde'],
              },
              caption:
                'La diferencia no es el detalle decorativo: la instrucción precisa no deja NINGUNA decisión en manos del robot.',
            },
            body: [
              'Una instrucción es precisa cuando cualquier ejecutor — humano o máquina — produce exactamente el mismo resultado.',
              'Una computadora no imagina nada más. Python es el lenguaje con el que le escribes instrucciones precisas — igual que las que acabas de construir para el robot.',
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
              'Una computadora funciona exactamente igual que este robot: ejecuta lo que le dices, ni más ni menos. Python es una forma de escribir esas instrucciones — y la misma regla aplica: si tu instrucción asume algo que la computadora no puede adivinar, falla.',
            ],
          },
          audio: {
            medium: 'clip_narrado',
            mediumLabel: 'Clip narrado',
            sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
            narrationText:
              'Imagina que le escribes instrucciones a alguien que jamás ha visto un sándwich, y que hará exactamente lo que escribiste. Pon mantequilla en el pan. ¿Con la mano? ¿Con el codo? Tú sabías que era con cuchillo, pero no lo dijiste, y el ejecutor no adivina. Esa es la regla de oro: si tu instrucción necesita que el otro adivine algo, no es una instrucción, es un deseo. Las máquinas no cumplen deseos: ejecutan instrucciones. Y una computadora funciona exactamente igual. Python es la forma en que le escribes esas instrucciones. Si eres preciso, ejecuta. Si no lo eres, falla.',
            body: [
              'Imagina que le escribes instrucciones a alguien que jamás ha visto un sándwich… y que hará EXACTAMENTE lo que escribiste. «Pon mantequilla en el pan». ¿Con la mano? ¿Con el codo? Tú sabías que era con cuchillo — pero no lo dijiste, y el ejecutor no adivina.',
              'Esa es la regla de oro: si tu instrucción necesita que el otro adivine algo, no es una instrucción — es un deseo. Las máquinas no cumplen deseos. Ejecutan instrucciones.',
              'Y esa regla no es solo del robot. Una computadora funciona exactamente igual. Python es la forma en que le escribes esas instrucciones. Si eres preciso, ejecuta. Si no lo eres, falla.',
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
              'Ese mismo robot mental es el modelo que usarás cuando programes. Una computadora recibe instrucciones escritas — Python es el lenguaje en que las escribes — y las ejecuta exactamente como tú las escribiste.',
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
          'Exacto. Cinco instrucciones sin espacio para la imaginación. Descartaste la ambigua — eso es pensar como programador. Una computadora opera con la misma regla: recibe lo que le dices, y nada más. Pronto escribirás instrucciones así, pero para un computador real.',
        orderFeedback:
          'El robot ejecuta EXACTAMENTE en la secuencia que le das: no puede girar la manija antes de llegar a la puerta.',
        generalHint:
          'El robot se detuvo: hay algo en tu secuencia que no puede ejecutar. Revisa si cada instrucción le dice exactamente qué hacer, cuánto y hacia dónde.',
        solutionExplanation: [
          'Cada paso responde las tres preguntas que un robot no puede adivinar: qué hacer, cuánto y hacia dónde. «Avanza 4 pasos» es ejecutable; «camina hacia adelante» no, porque el cuánto queda a su imaginación.',
          'Fíjate además en el orden: el robot no puede avanzar antes de girar, ni girar la manija antes de detenerse frente a la puerta. Una secuencia es un camino donde cada paso prepara el siguiente.',
          'Acabas de descubrir una idea central: una máquina hace exactamente lo que le indicas — ni más, ni menos. Cuando escribas tus primeras líneas en Python, estarás haciendo lo mismo que hiciste aquí: darle instrucciones claras para que pueda ejecutarlas.',
        ],
      },
      pythonBridge: {
        label: 'Esto ya es Python',
        code: 'avanzar(pasos=4)\ngirar(grados=90, direccion="izquierda")\ndetenerse()\nextender_mano()\ngirar_manija()',
        explanation:
          'La secuencia que acabas de construir es, literalmente, un programa: cada línea es una instrucción precisa que Python ejecuta de arriba hacia abajo, exactamente en el orden en que la escribiste — ni una línea más, ni una menos de lo que dijiste.',
        practice: {
          prompt: 'Ahora hazlo tú: escribe una instrucción precisa en Python real para que la consola muestre exactamente Robot listo',
          starterCode: '# escribe tu instrucción aquí\n',
          expectedOutput: 'Robot listo',
          hint: 'Usa la función print() con el texto exacto entre comillas: print("Robot listo")',
          hintsByCategory: {
            sintaxis: 'Revisa que las comillas y los paréntesis estén completos: print("texto") necesita abrir y cerrar ambos.',
            variables: 'No necesitas ninguna variable aquí — escribe el texto directamente entre comillas, dentro de print(...).',
            logica: 'print() solo necesita el texto entre paréntesis — no hace falta llamar a ninguna otra función.',
            salida: 'Revisa mayúsculas, espacios y signos: debe coincidir letra por letra con "Robot listo".',
          },
          workedExample: {
            code: 'print("Hola")',
            output: 'Hola',
            explanation: 'print() siempre muestra exactamente el texto que le des entre comillas — ni más, ni menos. Fíjate en el patrón, no copies el mensaje: el tuyo es "Robot listo".',
          },
          solutionCode: 'print("Robot listo")',
        },
      },
      decision: {
        question: 'Ya entiendes lo que hace precisa una instrucción — y por qué eso mismo aplica cuando programas. ¿Cómo quieres consolidarlo?',
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
              'Un programa en Python es exactamente eso: una ruta de instrucciones precisas que la computadora sigue sin adivinar nada. Ahora hazlo tú: arma la ruta del GPS.',
            ],
            // BUG-003 (C-52): el ejemplo también se PRACTICA, no solo se lee.
            practice: {
              kind: 'ordering',
              prompt: 'Arma la ruta que el GPS le daría a un conductor. Una de las frases no es una instrucción — descártala.',
              items: [
                { id: 'g2', text: 'En 200 metros, gira a la derecha en la Av. América', position: 2 },
                {
                  id: 'gd1',
                  text: 'Dirígete al centro de la ciudad',
                  position: null,
                  whyWrong: '«Dirígete al centro» dice a dónde quieres llegar, no qué hacer ahora — es la meta disfrazada de paso, igual que «riega la planta».',
                },
                { id: 'g1', text: 'Avanza 400 metros por la Av. Larco', position: 1 },
                { id: 'g3', text: 'Detente frente al edificio de la esquina', position: 3 },
              ],
              successFeedback:
                'Exacto — armaste una ruta que cualquier conductor (o máquina) ejecuta igual. Así se ve un programa: pasos precisos, en orden, sin metas disfrazadas.',
              orderFeedback: 'El conductor no puede girar en la Av. América antes de haber avanzado por la Av. Larco.',
              generalHint: 'Una de las frases dice a DÓNDE llegar, no QUÉ hacer. Esa no es una instrucción.',
              solutionExplanation: [
                'Primero avanzar, después girar, después detenerse — cada paso deja al conductor donde el siguiente lo necesita. «Dirígete al centro» era la meta: el GPS nunca te la dicta como paso.',
              ],
            },
            pythonBridge: {
              label: 'Esto ya es Python',
              code: 'avanzar(metros=400, calle="Av. Larco")\ngirar(direccion="derecha", calle="Av. America")\ndetenerse(lugar="edificio de la esquina")',
              explanation:
                'La ruta del GPS que acabas de armar es la misma secuencia, en Python: tres funciones, en orden, cada una con sus datos exactos — nada de "dirígete al centro".',
            },
          },
          {
            kind: 'animacion',
            label: 'Ver una animación',
            title: 'Dos robots, dos destinos',
            medium: 'animacion',
            sceneId: 'dos-robots',
            body: [
              'Mismo robot, misma meta. El primero recibió «cruza la habitación» y terminó contra la mesa; el segundo recibió tres instrucciones precisas — y llegó. La única diferencia fue la precisión.',
              'Cuando programes en Python harás exactamente lo del segundo robot: instrucciones exactas, en orden, sin dejar nada a la imaginación de la máquina.',
            ],
          },
          {
            kind: 'audio',
            label: 'Escuchar otra explicación',
            title: 'Escúchalo de otra forma',
            medium: 'clip_narrado',
            narrationText:
              'Piensa en la última vez que le explicaste algo a alguien y te entendió mal. Seguro dijiste: pero era obvio. Para una máquina, nada es obvio. Una instrucción precisa dice qué hacer, con qué, cuánto y hacia dónde. Si falta una de esas piezas, el robot va a fallar. Y Python es, simplemente, el idioma en que le escribirás esas instrucciones a tu computadora.',
            body: [
              'Piensa en la última vez que le explicaste algo a alguien y te entendió mal. Seguro dijiste «¡pero era obvio!». Para una máquina nada es obvio: una instrucción precisa dice qué hacer, con qué, cuánto y hacia dónde. Si falta una de esas piezas, el robot va a fallar.',
              'Python es, simplemente, el idioma en que le escribirás esas instrucciones a tu computadora.',
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
              'Una instrucción es precisa cuando el robot no necesita decidir nada por su cuenta. Si al leerla te preguntas «¿cuánto?», «¿hacia dónde?» o «¿con qué?», entonces el robot también se lo pregunta — y ahí falla. Python te exigirá exactamente lo mismo: cada línea debe decirlo todo.',
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
              'El robot solo entiende los pasos de la receta, nunca el título. Un programa en Python también es una receta: solo pasos ejecutables, nunca deseos. Ahora practica con solo dos pasos y un impostor.',
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

    // ── Ciclo 2: Variables ──────────────────────────────────────────────────────
    {
      id: 'ciclo-2',
      conceptId: 'variables',
      conceptLabel: 'Variables',
      priorMastery: 0.2,
      curiosityFact: {
        fact:
          'En sus notas de 1843 sobre la máquina analítica de Babbage, Ada Lovelace ya usaba columnas numeradas para guardar resultados intermedios de un cálculo — cada columna tenía un valor que se podía leer y actualizar más adelante.',
        connection:
          'Casi 200 años antes de Python, ya existía la idea central de este ciclo: ponerle un nombre a un valor para poder reusarlo después, sin recalcularlo ni repetirlo.',
      },
      concept: {
        title: '¿Qué es una variable?',
        secondExample: {
          label: 'Otro caso — el casillero del gimnasio',
          body: [
            'Un casillero de gimnasio no es útil por ser una caja: es útil porque tiene un número, y ese número siempre te lleva al mismo contenido, aunque lo que guardes adentro cambie día a día.',
            'Una variable funciona igual: el NOMBRE (edad, mensaje, saldo) siempre te lleva al mismo valor guardado — hasta que tú decidas guardar uno distinto.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'casillero = "mochila azul"',
          explanation:
            '«casillero» es el nombre; «mochila azul» es lo que guarda. En Python se escribe exactamente así: nombre = valor. Nada más que aprender todavía — solo ponerle nombre a algo que quieres recordar.',
        },
        variants: {
          visual: {
            medium: 'infografia',
            mediumLabel: 'Infografía',
            sourceNote: 'Elegido para ti — tu perfil capta ideas más rápido cuando las ve.',
            infographic: {
              vague: {
                instruction: '20',
                questions: ['¿20 qué cosa?', '¿por qué aparece varias veces en el programa?', '¿qué pasa si cambia?'],
              },
              precise: {
                instruction: 'edad = 20',
                parts: ['nombre: edad', 'valor: 20', 'se puede leer y actualizar donde haga falta'],
              },
              caption:
                'Un número suelto no dice nada de sí mismo. El mismo número con nombre se puede leer, reutilizar y cambiar sin reescribir el programa entero.',
            },
            body: [
              'Una variable es una caja con nombre que guarda un valor — un número, un texto, lo que sea — para que puedas leerlo o cambiarlo más adelante sin repetirlo.',
              'Python crea esa caja con una sola línea: nombre = valor. Después de esa línea, escribir el nombre es exactamente lo mismo que escribir el valor que guarda.',
            ],
          },
          reading: {
            medium: 'texto',
            mediumLabel: 'Texto estructurado',
            sourceNote: 'Elegido para ti — tu perfil profundiza mejor leyendo a su ritmo.',
            body: [
              'Imagina un programa que usa el precio de una compra tres veces: una para mostrarlo, otra para guardarlo en el recibo, otra para avisar si alcanza el saldo. Si escribes el precio suelto las tres veces y el precio cambia, tienes que corregirlo en las tres.',
              'Una variable resuelve exactamente ese problema: le pones nombre a un valor UNA vez — precio = 4.50 — y usas ese nombre las veces que necesites. Si el precio cambia, cambias una sola línea.',
              'Por eso una variable no es solo «guardar un dato»: es guardar un dato con un nombre que el resto del programa puede reutilizar sin repetir el valor.',
              'Python usa la forma más simple posible para esto: nombre = valor. A la izquierda, el nombre que eliges; a la derecha, lo que guarda.',
            ],
          },
          audio: {
            medium: 'clip_narrado',
            mediumLabel: 'Clip narrado',
            sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
            narrationText:
              'Piensa en un casillero de gimnasio. No te importa la caja en sí — te importa que ese número siempre te lleve al mismo contenido, y que puedas cambiar lo que hay adentro sin cambiar el número. Una variable es exactamente eso: un nombre que siempre te lleva al mismo valor guardado. Edad, igual, veinte. Ese signo igual no pregunta si son iguales — aquí significa: guarda esto aquí, con este nombre. Y una vez que lo guardaste, usar el nombre es exactamente lo mismo que usar el valor.',
            body: [
              'Piensa en un casillero de gimnasio. No te importa la caja en sí — te importa que ese número siempre te lleve al mismo contenido, y que puedas cambiar lo que hay adentro sin cambiar el número.',
              'Una variable es exactamente eso: un nombre que siempre te lleva al mismo valor guardado. «edad = 20» significa: guarda 20 aquí, con el nombre edad.',
              'Una vez que lo guardaste, usar el nombre es exactamente lo mismo que usar el valor.',
            ],
          },
          kinesthetic: {
            medium: 'simulacion',
            mediumLabel: 'Simulación',
            sourceNote: 'Elegido para ti — tu perfil construye comprensión haciendo.',
            body: [
              '📦 Antes de leer nada, predice: el robot ejecuta «caja_puntos = 0» y luego «caja_puntos = caja_puntos + 10». ¿Qué guarda la caja al final?',
              'Respuesta: 10. Primero crea la caja con 0 adentro; después LEE lo que tenía (0), le suma 10, y guarda el resultado en la MISMA caja.',
              'Ahora predice con esto: «vidas = 3» y después «vidas = vidas - 1». ¿Qué guarda vidas al final? Respuesta: 2 — perdiste una vida, y el nombre sigue siendo el mismo.',
              'Ese es el modelo que usarás siempre: una variable no es un valor fijo, es una caja con nombre que puedes volver a llenar — leyendo primero lo que tenía, si hace falta.',
            ],
          },
        },
      },
      practice: {
        kind: 'ordering',
        prompt:
          'El robot necesita recordar tu edad para calcular en cuántos años cumplirás 100. Construye la secuencia usando SOLO instrucciones precisas sobre la caja — una de la lista es la meta, no un paso.',
        items: [
          { id: 'v1', text: 'Crea una caja llamada edad', position: 1 },
          { id: 'v2', text: 'Guarda el número 20 dentro de la caja edad', position: 2 },
          { id: 'v3', text: 'Lee el valor guardado en la caja edad', position: 3 },
          { id: 'v4', text: 'Usa ese valor para calcular 100 menos edad', position: 4 },
          {
            id: 'vd1',
            text: 'Recuerda cuántos años tienes',
            position: null,
            whyWrong: '«Recuerda cuántos años tienes» es la meta, no una instrucción: no dice cómo crear la caja, ni cómo guardar o leer el valor.',
          },
        ],
        successFeedback:
          'Exacto. Le diste al robot una caja con nombre para guardar un valor y volver a usarlo — eso es exactamente lo que hace una variable. Pronto escribirás esta misma secuencia en Python, en una sola línea por paso.',
        orderFeedback:
          'El robot no puede leer una caja que todavía no llenaste, ni calcular con un valor que no leyó.',
        generalHint:
          'El robot se detuvo: una de las frases describe el resultado que quieres, no un paso sobre la caja edad.',
        solutionExplanation: [
          'Crear la caja, guardar el valor, leer el valor y usarlo — cuatro pasos, cada uno dejando al robot listo para el siguiente. «Recuerda cuántos años tienes» era la meta: no dice cómo guardar ni cómo leer nada.',
          'Fíjate en el patrón: primero se crea el lugar donde vivirá el valor, después se guarda algo ahí, y solo entonces se puede leer o usar. Sin ese orden, no hay nada que leer.',
          'Eso es exactamente una variable: una caja con nombre que guarda un valor, y que puedes volver a leer o cambiar más adelante — sin tener que reescribir el valor cada vez.',
        ],
      },
      pythonBridge: {
        label: 'Esto ya es Python',
        code: 'edad = 20\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
        explanation:
          'Cada caja de tu secuencia es una variable en Python: «edad = 20» crea la caja y guarda el valor en un solo paso; «faltan_para_100 = 100 - edad» lee el valor de edad para calcular otro; print(...) lo muestra. Ni una caja más, ni una menos de las que armaste.',
        practice: {
          prompt: 'Ahora hazlo tú: crea una variable llamada mensaje que guarde el texto Hola Python, y muéstrala con print()',
          starterCode: '# escribe tu código aquí\n',
          expectedOutput: 'Hola Python',
          hint: 'Primero crea la variable con mensaje = "Hola Python", y en otra línea usa print(mensaje) — sin comillas alrededor del nombre.',
          hintsByCategory: {
            sintaxis: 'Revisa el signo = y que el texto tenga sus comillas completas: mensaje = "Hola Python"',
            variables: 'Python no encuentra esa variable porque nunca se creó con = antes de usarla, o el nombre no coincide exactamente.',
            logica: 'Revisa el orden: primero se crea la variable con =, y solo después se puede mostrar con print(...).',
            // «print("mensaje")» corre sin errores pero muestra la palabra
            // literal, no el valor guardado — un error de SALIDA (sin
            // excepción), no de sintaxis ni de lógica: por eso la pista sobre
            // comillas vive aquí, donde el clasificador realmente la usa.
            salida: 'print(mensaje) muestra el VALOR de la variable — nunca escribas print("mensaje") entre comillas: eso muestra la palabra "mensaje", no lo que guardaste. Revisa también mayúsculas y espacios.',
          },
          workedExample: {
            code: 'nombre = "Ana"\nprint(nombre)',
            output: 'Ana',
            explanation: 'nombre = "Ana" crea la variable y guarda el texto. print(nombre) — SIN comillas alrededor de nombre — muestra lo que guarda. Con comillas, print("nombre"), Python mostraría literalmente la palabra nombre.',
          },
          solutionCode: 'mensaje = "Hola Python"\nprint(mensaje)',
        },
      },
      decision: {
        question: 'Ya sabes crear y leer variables — y por qué eso te ahorra reescribir un programa entero. ¿Cómo quieres consolidarlo?',
        reinforcements: [
          {
            kind: 'reto',
            label: 'Resolver un reto rápido',
            title: 'Reto: el marcador del videojuego',
            body: ['Misma regla: crea la caja, guarda el valor, y solo entonces úsalo. Hay un impostor.'],
            practice: {
              kind: 'ordering',
              prompt: 'Ordena las instrucciones para que el robot lleve el marcador de un videojuego. Descarta la que sea la meta, no un paso.',
              items: [
                { id: 'm1', text: 'Crea una caja llamada puntos', position: 1 },
                { id: 'm2', text: 'Guarda el número 0 dentro de la caja puntos', position: 2 },
                { id: 'm3', text: 'Súmale 10 al valor guardado en puntos', position: 3 },
                {
                  id: 'md1',
                  text: 'Gana la partida',
                  position: null,
                  whyWrong: '«Gana la partida» es el resultado que quieres, no una instrucción sobre la caja puntos.',
                },
              ],
              successFeedback: 'Exacto — actualizaste el marcador sin perder su nombre. Así funciona un contador en cualquier programa.',
              orderFeedback: 'No puedes sumarle puntos a una caja que todavía no existe.',
              generalHint: 'Una de las frases describe el resultado que quieres, no un paso con la caja puntos.',
              solutionExplanation: [
                'Crear, guardar y solo después sumar — cada paso necesita que el anterior ya haya ocurrido. «Gana la partida» era la meta, no una instrucción sobre la caja.',
              ],
            },
          },
          {
            kind: 'ejemplo',
            label: 'Ver un ejemplo más',
            title: 'Ejemplo: el saldo de una billetera digital',
            medium: 'ejemplo_comentado',
            body: [
              'Tu billetera digital no recalcula tu saldo revisando cada transacción cada vez que abres la app: guarda un número — saldo — y lo actualiza cada vez que compras o recibes dinero.',
              '«saldo = 50» crea la variable. «saldo = saldo - 12» la actualiza: lee lo que tenía, resta 12, guarda el resultado con el mismo nombre.',
              'Ahora hazlo tú: arma la secuencia que actualiza el saldo después de una compra.',
            ],
            practice: {
              kind: 'ordering',
              prompt: 'Arma la secuencia que actualiza el saldo de la billetera después de una compra. Descarta la que sea la meta.',
              items: [
                { id: 's1', text: 'Crea una caja llamada saldo', position: 1 },
                { id: 's2', text: 'Guarda el número 50 dentro de la caja saldo', position: 2 },
                { id: 's3', text: 'Resta 12 al valor guardado en saldo', position: 3 },
                {
                  id: 'sd1',
                  text: 'Revisa cuánto dinero tienes',
                  position: null,
                  whyWrong: '«Revisa cuánto dinero tienes» pregunta el resultado, no dice qué hacer con la caja saldo.',
                },
              ],
              successFeedback: 'Exacto — así se actualiza un saldo real: sin perder el nombre de la variable en ningún paso.',
              orderFeedback: 'No puedes restarle a un saldo que todavía no guardaste.',
              generalHint: 'Una de las frases pregunta el resultado, no dice qué hacer con la caja saldo.',
              solutionExplanation: [
                'Crear la caja, guardar 50, y solo después restar 12 — el mismo orden que necesita cualquier actualización de saldo real.',
              ],
            },
            pythonBridge: {
              label: 'Esto ya es Python',
              code: 'saldo = 50\nsaldo = saldo - 12\nprint(saldo)',
              explanation:
                '«saldo» aparece tres veces, y las tres son la MISMA caja: se crea, se lee para restar, y se vuelve a guardar con el nuevo valor. Por eso «saldo = saldo - 12» no es una ecuación matemática — es «toma lo que hay en saldo, réstale 12, y guarda el resultado ahí mismo».',
            },
          },
          {
            kind: 'animacion',
            label: 'Ver una animación',
            title: 'La misma caja, dos valores distintos',
            medium: 'animacion',
            sceneId: 'caja-variable',
            body: [
              'La caja se llama «edad» y guarda 20. Cuando el programa ejecuta «edad = edad + 1», la caja no cambia de nombre — cambia lo que guarda: ahora 21.',
              'Eso es lo que hace distinta a una variable de un número fijo: puedes volver a llenarla, leyendo primero lo que tenía si hace falta.',
            ],
          },
          {
            kind: 'audio',
            label: 'Escuchar otra explicación',
            title: 'Escúchalo de otra forma',
            medium: 'clip_narrado',
            narrationText:
              'Piensa en una libreta con una sola hoja con tu nombre escrito arriba. Cada vez que anotas algo nuevo, tachas lo anterior y escribes el valor nuevo — pero la hoja sigue siendo tuya, con el mismo nombre arriba. Una variable funciona igual: el nombre no cambia, lo que guarda sí. Y leer el nombre siempre te da el último valor que anotaste, nunca los anteriores.',
            body: [
              'Piensa en una libreta con una sola hoja con tu nombre escrito arriba. Cada vez que anotas algo nuevo, tachas lo anterior y escribes el valor nuevo — pero la hoja sigue siendo tuya, con el mismo nombre arriba.',
              'Una variable funciona igual: el nombre no cambia, lo que guarda sí. Y leer el nombre siempre te da el último valor que anotaste, nunca los anteriores.',
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
              'Una variable es una caja con nombre. Crear la caja, guardar un valor y leerlo son tres pasos distintos — y el robot no puede leer una caja que todavía no llenaste. Python te exigirá el mismo orden.',
            ],
            illustration: {
              medium: 'ejemplo_comentado',
              mediumLabel: 'Ejemplo resuelto paso a paso',
              body: [
                'Meta: que el robot recuerde tu color favorito y lo muestre.',
                '1. «Crea una caja llamada color» — le da nombre al lugar donde vivirá el valor.',
                '2. «Guarda el texto azul dentro de la caja color» — recién ahora la caja tiene algo.',
                '3. «Muestra el valor guardado en color» — solo se puede leer lo que ya se guardó.',
                'Descartada: «recuerda tu color favorito». Es la META, no un paso: no dice cómo crear la caja ni cómo guardar nada.',
              ],
            },
            practice: {
              kind: 'ordering',
              prompt: 'Ordena las instrucciones para que el robot recuerde y muestre tu color favorito. Descarta la que sea la meta.',
              items: [
                { id: 'c1', text: 'Crea una caja llamada color', position: 1 },
                { id: 'c2', text: 'Guarda el texto azul dentro de la caja color', position: 2 },
                { id: 'c3', text: 'Muestra el valor guardado en color', position: 3 },
                {
                  id: 'cd1',
                  text: 'Recuerda tu color favorito',
                  position: null,
                  whyWrong: '«Recuerda tu color favorito» es la meta, no una instrucción: no dice cómo crear la caja ni qué guardar en ella.',
                },
              ],
              successFeedback: 'Eso es — separaste la meta de los pasos que la hacen posible, en el mismo orden que necesita una variable.',
              orderFeedback: 'El robot no puede mostrar el valor de una caja que todavía no llenaste.',
              generalHint: 'Una de esas frases dice QUÉ quieres que pase, no qué debe hacer el robot con la caja.',
            },
          },
          {
            level: 2,
            title: 'Probemos con otra representación, y más despacio',
            conceptModality: 'alternate',
            body: [
              'Piensa en una etiqueta pegada a una caja vacía. Primero pegas la etiqueta (el nombre); después metes algo adentro (el valor). Sin la etiqueta, no sabrías qué caja es; sin el valor, la caja está vacía y no hay nada que leer.',
              'Un programa en Python sigue exactamente ese orden. Ahora practica con solo dos pasos y un impostor.',
            ],
            illustration: {
              medium: 'diagrama',
              mediumLabel: 'Analogía visual: caja vacía → nombre → valor',
              body: [
                '📦 [ CAJA VACÍA ]  ← todavía no es una variable, no tiene nombre ni valor.',
                '     ├── «Crea una caja llamada temperatura»   ← ahora tiene nombre',
                '     └── «Guarda el número 18 dentro»           ← ahora tiene valor',
                'Sin el nombre, no hay dónde guardar nada. Sin el valor, no hay nada que leer.',
              ],
            },
            practice: {
              kind: 'ordering',
              prompt: 'Solo dos pasos y un impostor. Ordena para que el robot guarde la temperatura del termostato.',
              items: [
                { id: 't1', text: 'Crea una caja llamada temperatura', position: 1 },
                { id: 't2', text: 'Guarda el número 18 dentro de la caja temperatura', position: 2 },
                {
                  id: 'td1',
                  text: 'Ajusta la temperatura',
                  position: null,
                  whyWrong: '«Ajusta la temperatura» es el resultado que quieres, no una acción que el robot pueda ejecutar sobre la caja.',
                },
              ],
              successFeedback: 'Exacto. Primero el nombre, después el valor — y «ajusta la temperatura» era la meta.',
              orderFeedback: 'No puedes guardar un valor en una caja que todavía no existe.',
              generalHint: 'Solo una de las frases NO le dice al robot qué hacer con la caja.',
              solutionExplanation: [
                'Primero «crea la caja»: le da nombre al lugar. Después «guarda el número 18»: recién ahí hay algo que leer.',
                '«Ajusta la temperatura» describe para qué lo haces, no qué hacer. Ese es el impostor, igual que «recuerda tu color favorito» o «gana la partida».',
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
  // Módulo 2 ("Estructuras de control") ya tiene experiencia propia (PED-004
  // deja de aplicarle el modo de referencia): el cierre anuncia la siguiente
  // misión real de la ruta.
  closing: {
    achievement:
      'Construiste «Instrucciones precisas» descartando los objetivos disfrazados de pasos, y después «Variables» — cajas con nombre que guardan un valor y te ahorran repetirlo. Ya sabes cómo se le habla a una máquina y cómo hacer que recuerde algo por ti. Esas dos reglas son la base de todo lo que escribirás en Python.',

    // LEARN-002 — la hipótesis de la apertura se responde aquí: qué pensaste,
    // si estabas en lo cierto y por qué ahora entiendes más. Las claves son el
    // texto EXACTO de opening.options.
    hypothesis: {
      verdicts: {
        'Nada — es un robot, sabe hacerlo': {
          label: 'Ahora lo sabes',
          text:
            'Pensaste que el robot sabría prepararlo solo. Hoy comprobaste lo contrario: un robot no sabe nada que no le digas. «Prepárame un sándwich» no es ejecutable — le faltan el qué, el con qué y el cuánto. Que tu idea haya cambiado no es un error: es la prueba de que aprendiste.',
        },
        'No sabría por dónde empezar': {
          label: 'Te acercaste',
          text:
            'Intuiste que el robot se quedaría sin saber qué hacer — muy cerca de la verdad. Hoy comprobaste POR QUÉ: sin un primer paso preciso no puede ni empezar, porque no imagina nada. Tu intuición ahora tiene una regla que la explica.',
        },
        'Haría algo absurdo': {
          label: 'Acertaste',
          text:
            'Predijiste que haría algo absurdo — y eso es exactamente lo que pasa: ejecuta lo que dices al pie de la letra, aunque el resultado sea ridículo. Hoy comprobaste por qué: para la máquina no existe nada que no le hayas dicho. Tu hipótesis quedó confirmada por el experimento.',
        },
      },
      coda:
        'Cuando escribas tu primera línea de Python le hablarás a un ejecutor igual de literal que este robot. La hipótesis que pusiste a prueba hoy será tu ventaja.',
    },

    nextMission: {
      title: 'Misión 2 · Decisiones que la máquina entiende',
      hook:
        'Ya sabes darle instrucciones precisas a una máquina. La siguiente pregunta es qué pasa cuando esa máquina debe decidir — y para eso necesita condiciones tan precisas como las instrucciones que acabas de dominar.',
    },
  },
}
