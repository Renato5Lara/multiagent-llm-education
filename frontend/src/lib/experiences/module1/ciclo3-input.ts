// Módulo 1 · Ciclo 3 — Entrada de datos (input()).
// Mismo patrón pedagógico validado en Ciclo 1 (Instrucciones precisas) y
// Ciclo 2 (Variables): curiosidad → concepto multimodal → práctica de
// ordenamiento → puente a Python con micropráctica real en Pyodide →
// decisión → escalera de remediación.

import type { LearningCycle, PredictOutputPracticeDef } from '@/types/moduleExperience'

// Multimodalidad profunda (jul 2026, Sprint 3 — "consolidar antes de
// ampliar catálogo", mismo patrón ya probado en Ciclo 2/READING_PRACTICE):
// el lector no arrastra para ordenar — predice la ejecución completa,
// incluida la pausa real de input(), antes de ver el resultado.
const READING_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  prompt: '¿Qué muestra la pantalla completa? (el usuario escribe: Luna)',
  code: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
  options: [
    { id: 'a', text: '¿Cómo te llamas? Hola, nombre' },
    { id: 'b', text: 'Hola, Luna' },
    { id: 'c', text: '¿Cómo te llamas? Hola, Luna' },
    { id: 'd', text: 'nombre' },
  ],
  correctOptionId: 'c',
  successFeedback: 'Exacto — input() primero muestra su pregunta en pantalla y espera; recién cuando la persona responde, print() usa esa respuesta guardada, nunca la palabra "nombre" en sí.',
  wrongFeedback: 'Revisa dos cosas: la pregunta de input() SÍ aparece en pantalla (no se oculta), y lo que se guarda en nombre es la respuesta escrita, no la palabra "nombre".',
  solutionExplanation: [
    'Línea 1: input("¿Cómo te llamas? ") muestra la pregunta y se detiene. El usuario escribió Luna — ese texto queda guardado en nombre.',
    'Línea 2: print("Hola,", nombre) usa el valor guardado — Luna — no la palabra "nombre".',
    'La pantalla completa muestra ambas cosas en orden: primero la pregunta de input(), después el saludo de print().',
  ],
}

export const CICLO_3_INPUT: LearningCycle = {
  id: 'ciclo-3',
  conceptId: 'input',
  conceptLabel: 'Entrada de datos (input)',
  priorMastery: 0.2,
  curiosityFact: {
    fact:
      'En 1966, en el MIT, Joseph Weizenbaum creó ELIZA, uno de los primeros programas capaces de sostener una "conversación": nunca decía lo mismo dos veces, porque cada respuesta dependía de lo que la persona escribía primero. Sin ese texto de entrada, ELIZA no tenía nada de qué hablar.',
    connection:
      'Hasta ahora tu robot solo ejecutó lo que TÚ decidiste de antemano, en el código o en las cajas. Hoy le vas a dar la misma capacidad que tenía ELIZA hace más de 55 años: la de esperar lo que el USUARIO escribe, y recién entonces continuar.',
  },
  concept: {
    title: '¿Cómo escucha un programa a quien lo usa?',
    quickRecap: {
      body: [
        'Recordatorio rápido: input() pausa el programa, muestra una pregunta, y guarda lo que la persona responde en una variable — el mismo mecanismo de nombre = valor que ya dominas, solo que ahora el valor lo decide quien usa el programa, no tú en el código.',
      ],
    },
    secondExample: {
      label: 'Otro caso — el cajero automático',
      body: [
        'Un cajero automático no imprime siempre el mismo monto: se detiene, muestra «¿Cuánto deseas retirar?», y espera. No continúa hasta que tú escribes algo y confirmas.',
        'Esa pausa — preguntar y esperar — es exactamente lo que hace un programa cuando necesita un dato que solo tú tienes. La misma regla del robot aplica: si no puede adivinarlo, tiene que preguntarlo.',
      ],
    },
    pythonBridge: {
      label: 'Esto ya es Python',
      code: 'nombre = input("¿Cómo te llamas? ")',
      explanation:
        'input() hace dos cosas en una sola línea: muestra el texto entre paréntesis como pregunta, y DETIENE el programa — no sigue hasta que alguien escribe algo y presiona Enter. Lo que la persona escribió queda guardado en la variable nombre, lista para usarse, igual que aprendiste en el ciclo anterior.',
    },
    variants: {
      visual: {
        medium: 'infografia',
        mediumLabel: 'Infografía',
        sourceNote: 'Elegido para ti — tu perfil capta ideas más rápido cuando las ve.',
        infographic: {
          vague: {
            instruction: 'saludar()',
            questions: ['¿a quién saluda?', '¿de dónde saca el nombre?', '¿qué hace si no lo sabe?'],
          },
          precise: {
            instruction: 'nombre = input("¿Cómo te llamas? ")\nsaludar(nombre)',
            parts: ['pregunta: qué muestra en pantalla', 'espera: se detiene hasta que respondes', 'guarda: la respuesta queda en la variable'],
          },
          caption:
            'Sin preguntar, el programa tendría que adivinar quién eres — y ya sabes que una máquina no adivina nada. input() reemplaza esa adivinanza por una pregunta real, y una espera real.',
        },
        body: [
          'input() no es un tipo de dato nuevo ni una caja nueva: es la forma en que un programa pausa, pregunta, y deja que el USUARIO decida qué valor llega a la variable.',
          'Antes, tú escribías el valor directamente en el código (edad = 20). Con input(), el valor lo escribe la persona que usa el programa, en el momento en que lo usa.',
        ],
      },
      reading: {
        medium: 'texto',
        mediumLabel: 'Texto estructurado',
        sourceNote: 'Elegido para ti — tu perfil profundiza mejor leyendo a su ritmo.',
        body: [
          'Imagina un programa que saluda a quien lo use. Si escribes print("Hola, Ana") el programa SIEMPRE saluda a Ana, sin importar quién lo ejecute — porque "Ana" quedó fijo en el código.',
          'Eso no sirve para un programa real: la próxima persona que lo use no se llama Ana. Necesitas que el programa PREGUNTE el nombre, en lugar de asumirlo.',
          'input() resuelve exactamente eso: pausa el programa, muestra una pregunta, y guarda lo que la persona responde en una variable — la misma variable que ya sabes crear y leer.',
          'Por eso input() y las variables trabajan juntos: input() consigue el dato, la variable lo recuerda para el resto del programa.',
        ],
      },
      audio: {
        medium: 'clip_narrado',
        mediumLabel: 'Clip narrado',
        sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
        narrationText:
          'Piensa en un mesero que nunca pregunta qué quieres comer: simplemente trae siempre el mismo plato. Funciona una vez, por casualidad, y falla con el siguiente cliente. Un buen mesero pregunta, y ESPERA tu respuesta antes de anotar el pedido. input() es exactamente ese mesero: muestra la pregunta, se detiene, y solo continúa cuando tú respondiste. Lo que respondiste queda guardado, listo para usarse, igual que una variable normal — porque, de hecho, es exactamente eso.',
        body: [
          'Piensa en un mesero que nunca pregunta qué quieres comer: simplemente trae siempre el mismo plato. Funciona una vez, por casualidad, y falla con el siguiente cliente.',
          'Un buen mesero pregunta, y ESPERA tu respuesta antes de anotar el pedido. input() es exactamente ese mesero: muestra la pregunta, se detiene, y solo continúa cuando tú respondiste.',
          'Lo que respondiste queda guardado, listo para usarse, igual que una variable normal — porque, de hecho, es exactamente eso.',
        ],
      },
      kinesthetic: {
        medium: 'simulacion',
        mediumLabel: 'Simulación',
        sourceNote: 'Elegido para ti — tu perfil construye comprensión haciendo.',
        body: [
          '🎤 Antes de leer nada, predice: el robot pregunta «¿Cuántas manzanas quieres?» y espera. Tú respondes «3». ¿Qué hace el robot con ese 3?',
          'Respuesta: lo guarda en una caja — igual que en el ciclo anterior — y recién ahí puede usarlo, por ejemplo para calcular el precio o confirmar el pedido.',
          'Ahora predice con esto: el robot pregunta «¿Cómo te llamas?» pero el programa NO tiene ninguna caja donde guardar tu respuesta. ¿Qué pasa con lo que escribiste?',
          'Respuesta: se pierde — una respuesta sin caja donde guardarse desaparece apenas el programa sigue. Por eso input() casi siempre aparece junto a una variable: nombre = input(...) — la pregunta y la caja, en la misma línea.',
        ],
      },
    },
  },
  practice: {
    default: {
      kind: 'ordering',
      prompt:
        'El robot debe saludar a quien tiene enfrente, pero no sabe su nombre todavía. Construye la secuencia usando SOLO instrucciones precisas — una de la lista es la meta, no un paso.',
      items: [
        { id: 'i1', text: 'Muestra la pregunta ¿Cómo te llamas?', position: 1 },
        { id: 'i2', text: 'Espera a que la persona escriba su respuesta', position: 2 },
        { id: 'i3', text: 'Guarda la respuesta en la caja llamada nombre', position: 3 },
        { id: 'i4', text: 'Usa el valor guardado en nombre para saludar', position: 4 },
        {
          id: 'id1',
          text: 'Saluda a la persona por su nombre',
          position: null,
          whyWrong: '«Saluda a la persona por su nombre» es la meta, no una instrucción: no dice cómo el robot se entera de cuál es ese nombre.',
        },
      ],
      successFeedback:
        'Exacto. Preguntar, esperar, guardar y recién ahí usar la respuesta — eso es exactamente lo que hace input() en Python. Pronto escribirás esta misma secuencia en una sola línea.',
      orderFeedback:
        'El robot no puede saludarte con un nombre que todavía no escribiste, ni guardar una respuesta que todavía no diste.',
      generalHint:
        'El robot se detuvo: una de las frases no dice qué hacer con la respuesta de la persona — dice el resultado que quieres.',
      solutionExplanation: [
        'Preguntar, esperar, guardar y usar — cuatro pasos, cada uno necesitando que el anterior ya haya ocurrido. «Saluda a la persona por su nombre» era la meta: no dice cómo conseguir ese nombre.',
        'Fíjate en el paso «espera»: sin él, el robot seguiría de inmediato sin darle tiempo a la persona de responder. Un programa real hace lo mismo — input() se detiene hasta que llega una respuesta.',
        'Eso es exactamente lo que hace input(): pregunta, espera, y guarda la respuesta en una variable — la misma variable que ya sabes crear y leer desde el ciclo anterior.',
      ],
    },
    reading: READING_PRACTICE,
  },
  pythonBridge: {
    label: 'Esto ya es Python',
    code: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
    explanation:
      'Cada paso de tu secuencia es esta línea de Python: input("¿Cómo te llamas? ") muestra la pregunta y espera; lo que la persona escribe queda guardado en nombre; print("Hola,", nombre) lo usa para saludar. Ni un paso más, ni uno menos de los que armaste.',
    practice: {
      prompt: 'Ahora hazlo tú: pide el nombre con input() y saluda con el patrón exacto Hola, <nombre>',
      starterCode: '# escribe tu código aquí\n',
      expectedOutput: '¿Cómo te llamas? Hola, Ana',
      // Sin terminal real en el navegador: el usuario simulado "escribe" Ana,
      // y ese valor se muestra explícitamente en la UI antes de ejecutar
      // (ver PythonBridge.tsx) — nunca es un dato que aparece de la nada.
      simulatedInputs: ['Ana'],
      hint: 'Usa input() para preguntar y guardar la respuesta en una variable, y print() para saludar con esa variable: nombre = input("¿Cómo te llamas? ") y luego print("Hola,", nombre)',
      hintsByCategory: {
        sintaxis: 'Revisa que input() tenga sus paréntesis y comillas completos, igual que print(): input("¿Cómo te llamas? ")',
        variables: 'Python no encuentra esa variable porque nunca se creó — recuerda: nombre = input(...) crea la variable Y guarda la respuesta en el mismo paso.',
        logica: 'Revisa el orden: primero input() pregunta y guarda la respuesta, y solo después print() puede usar esa variable.',
        salida: 'print("Hola,", nombre) debe mostrar exactamente Hola, seguido del nombre que escribió el usuario simulado — revisa la coma y el espacio.',
      },
      workedExample: {
        code: 'ciudad = input("¿En qué ciudad vives? ")\nprint("Vives en", ciudad)',
        output: '¿En qué ciudad vives? Vives en Trujillo',
        explanation: 'input() muestra la pregunta y espera — el usuario simulado escribió Trujillo. Esa respuesta quedó guardada en ciudad, y print("Vives en", ciudad) la usó de inmediato. Fíjate en el patrón, no copies el mensaje: el tuyo pregunta el nombre, no la ciudad.',
      },
      solutionCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
    },
  },
  decision: {
    question: 'Ya sabes hacer que un programa pregunte y espere una respuesta — y por qué eso lo vuelve realmente interactivo. ¿Cómo quieres consolidarlo?',
    reinforcements: [
      {
        kind: 'reto',
        label: 'Resolver un reto rápido',
        title: 'Reto: la calculadora de propinas',
        body: ['Misma regla: pregunta, guarda y recién entonces usa la respuesta. Hay un impostor.'],
        practice: {
          kind: 'ordering',
          prompt: 'Ordena las instrucciones para que el robot calcule cuánta propina dejar. Descarta la que sea la meta, no un paso.',
          items: [
            { id: 't1', text: 'Muestra la pregunta ¿Cuánto fue la cuenta?', position: 1 },
            { id: 't2', text: 'Guarda la respuesta en la caja llamada cuenta', position: 2 },
            { id: 't3', text: 'Calcula el 10% del valor guardado en cuenta', position: 3 },
            {
              id: 'td1',
              text: 'Decide cuánta propina dejar',
              position: null,
              whyWrong: '«Decide cuánta propina dejar» es el resultado que quieres, no una instrucción sobre la caja cuenta.',
            },
          ],
          successFeedback: 'Exacto — preguntaste, guardaste y recién ahí calculaste. Así funciona cualquier programa que depende de lo que el usuario responde.',
          orderFeedback: 'No puedes calcular el 10% de una cuenta que todavía no guardaste.',
          generalHint: 'Una de las frases describe el resultado que quieres, no un paso con la caja cuenta.',
          solutionExplanation: [
            'Preguntar, guardar y solo después calcular — el mismo orden que necesita cualquier input() real. «Decide cuánta propina dejar» era la meta, no una instrucción sobre la caja.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'cuenta = float(input("¿Cuánto fue la cuenta? "))\npropina = cuenta * 0.10\nprint(propina)',
          explanation:
            'input() SIEMPRE entrega texto, incluso si escribes un número — por eso hace falta float(...) para convertirlo antes de multiplicarlo. Sin ese casting, Python no puede calcular el 10% de un texto.',
          practice: {
            prompt: 'Ahora hazlo tú: pide la edad con input("¿Cuántos años tienes? "), conviértela a número entero con int(), y muestra cuántos años faltan para llegar a 100',
            starterCode: '# escribe tu código aquí\n',
            expectedOutput: '¿Cuántos años tienes? 80',
            simulatedInputs: ['20'],
            hint: 'input() siempre entrega texto — usa int(input(...)) para convertirlo a número antes de restarlo: edad = int(input("¿Cuántos años tienes? "))',
            hintsByCategory: {
              sintaxis: 'Revisa que int() e input() tengan sus paréntesis completos: int(input("¿Cuántos años tienes? "))',
              variables: 'Python no encuentra edad porque nunca se creó con int(input(...)) antes de restarla de 100.',
              logica: 'Si ves "unsupported operand type(s) for -: \'int\' and \'str\'", olvidaste envolver input() con int() — sin el casting, edad sigue siendo texto y no se puede restar.',
              salida: 'print(faltan) debe mostrar el número 80 — revisa que estés restando edad de 100, no al revés.',
            },
            workedExample: {
              code: 'cuenta = float(input("¿Cuánto fue la cuenta? "))\npropina = cuenta * 0.10\nprint(propina)',
              output: '¿Cuánto fue la cuenta? 5.0',
              explanation: 'float(input(...)) convierte el texto "50" en el número 50.0 antes de multiplicarlo por 0.10. Sin float(...), Python no puede multiplicar un texto por un decimal. Tu ejercicio usa int() y resta, no float() y multiplica.',
            },
            solutionCode: 'edad = int(input("¿Cuántos años tienes? "))\nfaltan = 100 - edad\nprint(faltan)',
          },
        },
      },
      {
        kind: 'ejemplo',
        label: 'Ver un ejemplo más',
        title: 'Ejemplo: el buscador que pregunta qué buscas',
        medium: 'ejemplo_comentado',
        body: [
          'Un buscador no muestra siempre los mismos resultados: pregunta «¿Qué buscas?», espera lo que escribes, y solo entonces busca.',
          'termino = input("¿Qué buscas? ") guarda tu búsqueda. buscar(termino) la usa. Sin esa pregunta, el buscador no tendría nada que buscar.',
          'Ahora hazlo tú: arma la secuencia que sigue el buscador.',
        ],
        practice: {
          kind: 'ordering',
          prompt: 'Arma la secuencia que sigue el buscador antes de mostrar resultados. Descarta la que sea la meta.',
          items: [
            { id: 'b1', text: 'Muestra la pregunta ¿Qué buscas?', position: 1 },
            { id: 'b2', text: 'Guarda lo que escribiste en la caja termino', position: 2 },
            { id: 'b3', text: 'Busca usando el valor guardado en termino', position: 3 },
            {
              id: 'bd1',
              text: 'Encuentra lo que buscas',
              position: null,
              whyWrong: '«Encuentra lo que buscas» describe el resultado, no dice qué hacer con la caja termino.',
            },
          ],
          successFeedback: 'Exacto — sin la pregunta inicial, el buscador no tendría ningún término que usar.',
          orderFeedback: 'No puedes buscar con un término que todavía no guardaste.',
          generalHint: 'Una de las frases describe el resultado, no un paso con la caja termino.',
          solutionExplanation: [
            'Preguntar, guardar y solo después buscar — el mismo orden que necesita cualquier programa que depende del usuario.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'termino = input("¿Qué buscas? ")\nbuscar(termino)',
          explanation:
            'La secuencia que armaste es, en Python, dos líneas: input() pregunta y guarda; buscar(termino) usa esa respuesta. Nada de "encuentra lo que buscas" — eso no es una instrucción.',
          practice: {
            prompt: 'Ahora hazlo tú: pide la comida favorita con input("¿Cuál es tu comida favorita? ") y únela al texto "Tu comida favorita es " usando el operador + antes de mostrarla con print()',
            starterCode: '# escribe tu código aquí\n',
            expectedOutput: '¿Cuál es tu comida favorita? Tu comida favorita es pizza',
            simulatedInputs: ['pizza'],
            hint: 'El operador + une dos textos en uno solo: "Tu comida favorita es " + comida — recuerda dejar el espacio antes de la comilla final.',
            hintsByCategory: {
              sintaxis: 'Revisa las comillas y el signo + entre los dos textos: "Tu comida favorita es " + comida',
              variables: 'Python no encuentra comida porque nunca se creó con input() antes de usarla con +.',
              logica: 'Revisa el orden: primero input() guarda la respuesta, y solo después + puede unirla al texto fijo.',
              salida: '+ une los textos exactamente como están escritos — revisa que el espacio quede antes de la comilla final, no después.',
            },
            workedExample: {
              code: 'color = input("¿Cuál es tu color favorito? ")\nprint("Tu color favorito es " + color)',
              output: '¿Cuál es tu color favorito? Tu color favorito es azul',
              explanation: '+ pegó "Tu color favorito es " con el valor de color, sin espacio de más ni de menos porque el espacio ya estaba dentro de las comillas del texto fijo. Tu ejercicio une comida, no color.',
            },
            solutionCode: 'comida = input("¿Cuál es tu comida favorita? ")\nprint("Tu comida favorita es " + comida)',
          },
        },
      },
      {
        kind: 'animacion',
        label: 'Ver una animación',
        title: 'El programa que espera, y el que no',
        medium: 'animacion',
        sceneId: 'espera-input',
        body: [
          'El primer programa muestra «¿Cómo te llamas?» y sigue de inmediato sin darte tiempo de responder — termina saludando a nadie.',
          'El segundo muestra la misma pregunta, pero se DETIENE. Solo cuando escribes tu respuesta y confirmas, continúa. La diferencia es esa pausa: input().',
        ],
      },
      {
        kind: 'audio',
        label: 'Escuchar otra explicación',
        title: 'Escúchalo de otra forma',
        medium: 'clip_narrado',
        narrationText:
          'Piensa en cuando alguien te hace una pregunta y, sin esperar tu respuesta, sigue hablando de otra cosa. Se siente raro, ¿verdad? Un programa sin input() hace exactamente eso: muestra una pregunta y sigue de largo, sin escuchar nada. input() es lo que le enseña a un programa a esperar — a detenerse hasta que tú realmente respondas. Y esa respuesta no se pierde: queda guardada en una variable, lista para usarse el resto del programa.',
        body: [
          'Piensa en cuando alguien te hace una pregunta y, sin esperar tu respuesta, sigue hablando de otra cosa. Se siente raro, ¿verdad?',
          'Un programa sin input() hace exactamente eso: muestra una pregunta y sigue de largo, sin escuchar nada. input() es lo que le enseña a un programa a esperar — a detenerse hasta que tú realmente respondas.',
          'Y esa respuesta no se pierde: queda guardada en una variable, lista para usarse el resto del programa.',
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
          'input() tiene tres momentos: pregunta, espera y guarda. Si te saltas alguno, el robot no tiene con qué continuar. Python exige exactamente ese orden.',
        ],
        illustration: {
          medium: 'ejemplo_comentado',
          mediumLabel: 'Ejemplo resuelto paso a paso',
          body: [
            'Meta: que el robot pregunte tu color favorito y lo repita.',
            '1. «Muestra la pregunta ¿Cuál es tu color favorito?» — dice qué mostrar.',
            '2. «Espera tu respuesta» — dice que se detiene hasta que respondes.',
            '3. «Guarda la respuesta en la caja color» — recién ahí hay algo guardado.',
            'Descartada: «Averigua tu color favorito». Es la META, no un paso: no dice cómo preguntar ni cómo guardar nada.',
          ],
        },
        practice: {
          kind: 'ordering',
          prompt: 'Ordena las instrucciones para que el robot pregunte y repita tu color favorito. Descarta la que sea la meta.',
          items: [
            { id: 'l1', text: 'Muestra la pregunta ¿Cuál es tu color favorito?', position: 1 },
            { id: 'l2', text: 'Espera tu respuesta', position: 2 },
            { id: 'l3', text: 'Guarda la respuesta en la caja color', position: 3 },
            {
              id: 'ld1',
              text: 'Averigua tu color favorito',
              position: null,
              whyWrong: '«Averigua tu color favorito» es la meta, no una instrucción: no dice cómo preguntar ni cómo guardar la respuesta.',
            },
          ],
          successFeedback: 'Eso es — separaste la meta de los pasos que la hacen posible, en el mismo orden que necesita input().',
          orderFeedback: 'El robot no puede guardar una respuesta que todavía no diste.',
          generalHint: 'Una de esas frases dice QUÉ quieres que pase, no qué debe hacer el robot paso a paso.',
        },
      },
      {
        level: 2,
        title: 'Probemos con otra representación, y más despacio',
        conceptModality: 'alternate',
        body: [
          'Piensa en un formulario en papel. Primero hay una pregunta impresa («Nombre: _____»); recién cuando TÚ escribes algo en la línea, el formulario tiene un dato. Sin tu letra, la línea sigue vacía.',
          'input() es esa línea en blanco: existe la pregunta, pero el valor solo aparece cuando alguien responde. Ahora practica con solo dos pasos y un impostor.',
        ],
        illustration: {
          medium: 'diagrama',
          mediumLabel: 'Analogía visual: pregunta impresa → respuesta → dato',
          body: [
            '📋 [ FORMULARIO ]  ← la pregunta impresa, todavía sin respuesta.',
            '     ├── «Muestra la pregunta ¿Cuántos años tienes?»   ← el formulario pregunta',
            '     └── «Guarda la respuesta en la caja edad»           ← recién aquí hay un dato',
            'Sin la pregunta, nadie sabe qué escribir. Sin guardar la respuesta, se pierde apenas el programa sigue.',
          ],
        },
        practice: {
          kind: 'ordering',
          prompt: 'Solo dos pasos y un impostor. Ordena para que el robot registre tu edad.',
          items: [
            { id: 'e1', text: 'Muestra la pregunta ¿Cuántos años tienes?', position: 1 },
            { id: 'e2', text: 'Guarda la respuesta en la caja edad', position: 2 },
            {
              id: 'ed1',
              text: 'Registra tu edad',
              position: null,
              whyWrong: '«Registra tu edad» es el resultado que quieres, no una acción que el robot pueda ejecutar sobre la pregunta o la caja.',
            },
          ],
          successFeedback: 'Exacto. Primero la pregunta, después la caja — y «registra tu edad» era la meta.',
          orderFeedback: 'No puedes guardar una respuesta que todavía no preguntaste.',
          generalHint: 'Solo una de las frases NO le dice al robot qué hacer con la pregunta o la caja.',
          solutionExplanation: [
            'Primero «muestra la pregunta»: sin ella nadie sabe qué responder. Después «guarda la respuesta»: recién ahí hay algo que usar.',
            '«Registra tu edad» describe para qué lo haces, no qué hacer — el mismo tipo de impostor que ya descartaste en ciclos anteriores.',
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
}
