// Módulo 1 · Ciclo 3 — Entrada de datos (input()).
// Mismo patrón pedagógico validado en Ciclo 1 (Instrucciones precisas) y
// Ciclo 2 (Variables): curiosidad → concepto multimodal → práctica de
// ordenamiento → puente a Python con micropráctica real en Pyodide →
// decisión → escalera de remediación.

import type { LearningCycle } from '@/types/moduleExperience'
import { INPUT_PRIMER } from '../conceptPrimers'

export const CICLO_3_INPUT: LearningCycle = {
  id: 'ciclo-3',
  conceptId: 'input',
  conceptLabel: 'Entrada de datos (input)',
  priorMastery: 0.2,
  conceptPrimers: [INPUT_PRIMER],
  // "¿Sabías qué?" solo vive en Ciclo 1 del módulo (Sprint "Auditoría
  // pedagógica", Hallazgo B) — ver la misma nota en ciclo2-variables.ts.
  concept: {
    title: '¿Cómo escucha un programa a quien lo usa?',
    quickRecap: {
      body: [
        'Recordatorio rápido: input() pausa el programa, muestra una pregunta, y guarda lo que la persona responde en una variable — el mismo mecanismo de nombre = valor que ya dominas, solo que ahora el valor lo decide quien usa el programa, no tú en el código.',
      ],
    },
    secondExample: {
      label: 'Otro caso — el robot que hace una pausa real',
      body: [
        'Este mismo robot no siempre actúa de inmediato: cuando necesita un dato que no tiene, se detiene, muestra «¿Cuántos pasos quieres que avance?», y espera. No continúa hasta que tú escribes algo y confirmas.',
        'Esa pausa — preguntar y esperar — es exactamente lo que hace un programa cuando necesita un dato que solo tú tienes. La misma regla de siempre aplica: si el robot no puede adivinarlo, tiene que preguntarlo.',
      ],
      // Sprint UX-06 "Perfil visual real" (jul 2026): misma analogía, visualizada.
      visualMediumLabel: 'Analogía visual',
      imageAsset: 'm1-c3-analogia-pausa-real',
      provenance: 'propia',
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
        // Auditoría "infografías" (jul 2026, tercera vuelta): ver misma nota
        // en ciclo1-instrucciones-precisas.ts — `imageAsset` ya está listo
        // para resolver contra illustrationAssets.ts.
        imageAsset: 'm1-c3-teoria-pregunta-input',
        imagePrompt:
          'Infografía comparativa de dos paneles para una app educativa de programación, modo oscuro.\n\n' +
          'COMPOSICIÓN: dos paneles rectangulares del mismo ancho, apilados verticalmente. Panel superior = LLAMADA SIN PREGUNTAR (vago). Panel inferior = PREGUNTA, ESPERA Y GUARDA (preciso, dos líneas de código). Entre ambos, una flecha corta apuntando hacia abajo con una etiqueta pequeña "pregúntale al usuario".\n\n' +
          'ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo — iconografía plana tipo robot/pantalla, coherente con un diagrama de producto SaaS.\n\n' +
          'COLORES: fondo casi negro #0a0a0f. Panel vago (superior): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Panel preciso (inferior): borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Flecha central y su etiqueta en gris azulado #94a3b8. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.\n\n' +
          'ICONOS: tres signos de interrogación (?) pequeños junto a las preguntas del panel vago. En el panel preciso, tres iconos pequeños en línea junto a cada parte: un globo de diálogo (pregunta), un reloj/pausa (espera), una caja con check (guarda).\n\n' +
          'DISTRIBUCIÓN: formato vertical 4:5. Panel vago ocupa el 40% superior, panel preciso el 40% inferior (con las dos líneas de código en fuente monoespaciada), con la flecha y su etiqueta en el 10% central, y una leyenda final en el 10% inferior, fuera de ambos paneles.\n\n' +
          'ELEMENTOS DE TEXTO (incluir literalmente):\n' +
          '— Panel vago, título: "SALUDAR()" — debajo, en lista: "¿a quién saluda?", "¿de dónde saca el nombre?", "¿qué hace si no lo sabe?"\n' +
          '— Panel preciso, título (dos líneas, monoespaciado): "NOMBRE = INPUT(\\"¿CÓMO TE LLAMAS?\\")" y "SALUDAR(NOMBRE)" — debajo, en lista: "pregunta: qué muestra en pantalla", "espera: se detiene hasta que respondes", "guarda: la respuesta queda en la variable"\n' +
          '— Leyenda inferior centrada, fuera de los paneles: "Sin preguntar, el programa tendría que adivinar quién eres. input() reemplaza esa adivinanza por una pregunta real, y una espera real."',
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
          'input() resuelve exactamente eso: pausa el programa, pregunta, y guarda la respuesta en una variable — la misma que ya sabes crear y leer. Por eso trabajan juntos: input() consigue el dato, la variable lo recuerda para el resto del programa.',
        ],
      },
      audio: {
        medium: 'clip_narrado',
        mediumLabel: 'Clip narrado',
        sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
        narrationAudioAsset: 'm1-c3-teoria-audio',
        narrationText:
          'Piensa en un robot guía que nunca pregunta a dónde quieres ir: simplemente te lleva siempre al mismo lugar. Funciona una vez, por casualidad, y falla con la siguiente persona. Un buen robot guía pregunta, y ESPERA tu respuesta antes de moverse. input() es exactamente ese robot: muestra la pregunta, se detiene, y solo continúa cuando tú respondiste. Lo que respondiste queda guardado, listo para usarse, igual que una variable normal — porque, de hecho, es exactamente eso.',
        body: [
          'Piensa en un robot guía que nunca pregunta a dónde quieres ir: simplemente te lleva siempre al mismo lugar. Funciona una vez, por casualidad, y falla con la siguiente persona.',
          'Un buen robot guía pregunta, y ESPERA tu respuesta antes de moverse. input() es exactamente ese robot: muestra la pregunta, se detiene, y solo continúa cuando tú respondiste.',
          'Lo que respondiste queda guardado, listo para usarse, igual que una variable normal — porque, de hecho, es exactamente eso.',
        ],
      },
      kinesthetic: {
        medium: 'simulacion',
        mediumLabel: 'Simulación',
        sourceNote: 'Elegido para ti — tu perfil construye comprensión haciendo.',
        body: [
          '🎤 Nada de leer todavía: predice qué hace el robot, y comprueba al instante.',
        ],
        // Sprint UX-01: las dos predicciones que antes vivían en párrafos
        // auto-respondidos ahora exigen elegir antes de ver la respuesta.
        interactions: [
          {
            question: 'El robot pregunta «¿Cuántas cajas quieres que cargue?» y espera. Respondes «3». ¿Qué hace el robot con tu respuesta?',
            options: [
              'La repite en voz alta y la olvida',
              'La guarda en una caja para usarla después',
              'Empieza a cargar cajas sin guardar nada',
            ],
            correctIndex: 1,
            reveal:
              'Guarda tu «3» en una caja — igual que en el ciclo anterior — y recién ahí puede usarlo, por ejemplo para calcular cuántos viajes le faltan.',
          },
          {
            question: 'Otro programa pregunta «¿Cómo te llamas?», pero NO tiene ninguna caja donde guardar la respuesta. ¿Qué pasa con lo que escribiste?',
            options: [
              'Se guarda solo, en una caja automática',
              'Se pierde apenas el programa sigue',
              'El programa se detiene para siempre',
            ],
            correctIndex: 1,
            reveal:
              'Sin una caja donde guardarse, la respuesta desaparece apenas el programa continúa. Por eso input() casi siempre aparece junto a una variable: nombre = input(...) — la pregunta y la caja, en la misma línea.',
          },
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
        'Sin haber preguntado ni guardado nada, el robot no tiene con qué saludarte.',
      generalHint:
        'El robot se detuvo: una de las frases no dice qué hacer con la respuesta de la persona — dice el resultado que quieres.',
      solutionExplanation: [
        'Preguntar, esperar, guardar y usar — cuatro pasos, cada uno necesitando que el anterior ya haya ocurrido. «Saluda a la persona por su nombre» era la meta: no dice cómo conseguir ese nombre.',
        'Fíjate en el paso «espera»: sin él, el robot seguiría de inmediato sin darle tiempo a la persona de responder. Un programa real hace lo mismo — input() se detiene hasta que llega una respuesta.',
        'Eso es exactamente lo que hace input(): pregunta, espera, y guarda la respuesta en una variable — la misma variable que ya sabes crear y leer desde el ciclo anterior.',
      ],
    },
    // Sprint "diversidad pedagógica" (jul 2026): antes, 'reading' predecía
    // aquí (predict_output) justo después de haber predicho en Ciclo 2 —
    // dos ciclos seguidos con la misma dinámica para ese perfil. Sin
    // override, 'reading' cae a `default` (ordering) — retoma la secuencia
    // igual que las demás modalidades, y el Ciclo 4 (Módulo 2) vuelve a
    // alternar a predict_output para las cuatro.
  },
  pythonBridge: {
    label: 'Esto ya es Python',
    code: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
    explanation:
      'Cada paso de tu secuencia es esta línea de Python: input("¿Cómo te llamas? ") muestra la pregunta y espera; lo que la persona escribe queda guardado en nombre; print("Hola,", nombre) lo usa para saludar. La secuencia se ejecuta completa, sin saltarse ni repetir ningún paso de los que armaste.',
    // Andamiaje completo (jul 2026, consolidación Sprint 2): mismos seis
    // peldaños que Ciclo 1 y Ciclo 2 (mismo campo `mode`, mismo componente
    // PythonBridge.tsx), continuando AQUÍ la misma pregunta-y-saludo que el
    // estudiante ya armó arriba — nunca un tema nuevo sin relación.
    practice: {
      mode: 'observar',
      prompt: 'Obsérvalo: ejecuta este código — el usuario simulado escribe Ana — y mira cómo el robot saluda.',
      starterCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)\n',
      expectedOutput: '¿Cómo te llamas? Hola, Ana',
      simulatedInputs: ['Ana'],
      hint: 'El código ya está completo — solo presiona Ejecutar para ver qué pasa.',
      resultExplanation: 'input() pausó el programa, guardó "Ana" en nombre, y print("Hola,", nombre) usó ese valor para saludar — por eso ves la pregunta seguida de "Hola, Ana", nunca solo uno de los dos.',
      solutionCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
      nextStage: {
        mode: 'manipular',
        prompt: 'Ahora tú: cambia SOLO la palabra de saludo para que el robot diga Bienvenido en vez de Hola — desde aquí input() ya es real: la respuesta la escribes tú, no un valor ya fijado.',
        starterCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)\n',
        // Épica C, Commit 1: sin simulatedInputs, input() real —
        // {input1} se sustituye por lo que el estudiante escriba
        // (ENGINEERING-GATE-EPICA-C.md, mismo modelo del Commit 6 de
        // Épica B).
        expectedOutput: '¿Cómo te llamas? Bienvenido, {input1}',
        hint: 'Solo cambia la palabra "Hola" por "Bienvenido" — la coma y el resto de la línea no necesitan tocarse: print("Bienvenido,", nombre)',
        hintsByCategory: {
          sintaxis: 'Revisa que las comillas alrededor de "Bienvenido," sigan completas.',
          variables: 'No necesitas ninguna variable nueva — nombre ya guarda la respuesta.',
          logica: 'Solo cambia el texto fijo antes de la coma; nombre no cambia.',
          salida: 'Revisa que tu saludo diga exactamente "Bienvenido, " seguido de lo que escribiste cuando Python te lo pidió, con mayúscula inicial en "Bienvenido".',
        },
        workedExample: {
          code: 'ciudad = input("¿En qué ciudad vives? ")\nprint("Vives en", ciudad)',
          output: '¿En qué ciudad vives? Vives en Trujillo',
          explanation: 'Cambiar el saludo es escribir un texto distinto antes de la coma — print() no cambia, solo lo que le pasas. Fíjate en el patrón: el tuyo debe decir "Bienvenido,".',
        },
        resultExplanation: 'Cambiaste solo el texto fijo antes de la coma — nombre siguió guardando lo que escribiste, y print() combinó tu nuevo saludo con ese valor.',
        solutionCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Bienvenido,", nombre)',
        nextStage: {
          mode: 'completar',
          prompt: 'Completa el código: falta la función que pausa el programa y espera tu respuesta. Reemplaza el espacio en blanco',
          starterCode: 'nombre = _____("¿Cómo te llamas? ")\nprint("Hola,", nombre)\n',
          // Épica C, Commit 2: sin simulatedInputs, input() real —
          // {input1} se sustituye por lo que el estudiante escriba
          // (ENGINEERING-GATE-EPICA-C.md, mismo modelo del Commit 6 de
          // Épica B).
          expectedOutput: '¿Cómo te llamas? Hola, {input1}',
          hint: 'La función que pregunta y espera una respuesta es input — reemplaza los guiones bajos por esa palabra exacta.',
          hintsByCategory: {
            sintaxis: 'Revisa que no queden guiones bajos ni espacios de más antes del paréntesis.',
            variables: 'nombre no puede guardar nada todavía porque la función que pregunta y espera sigue sin nombre.',
            logica: 'La pregunta y las comillas ya están completas; solo falta el nombre de la función.',
            salida: 'Una vez completado, debe mostrar exactamente "¿Cómo te llamas? Hola, " seguido de lo que escribiste cuando Python te lo pidió.',
          },
          workedExample: {
            code: 'ciudad = _____("¿En qué ciudad vives? ")\nprint("Vives en", ciudad)\n# se completa así:\nciudad = input("¿En qué ciudad vives? ")',
            output: '¿En qué ciudad vives? Vives en Trujillo',
            explanation: 'El hueco siempre se completa con el nombre de una función que ya conoces — aquí, input. Fíjate en el patrón: la pregunta entre comillas no cambia, solo el espacio en blanco.',
          },
          resultExplanation: 'Al completar el hueco con input, Python pudo por fin pausar y preguntar — antes no existía ninguna función ahí, así que nombre nunca tenía dónde guardar la respuesta.',
          solutionCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
          nextStage: {
            mode: 'corregir',
            prompt: 'Este código tiene un error: a la pregunta de input() le faltan las comillas. Encuéntralo y corrígelo.',
            starterCode: 'nombre = input(¿Cómo te llamas? )\nprint("Hola,", nombre)\n',
            // Épica C, Commit 3: sin simulatedInputs, input() real —
            // {input1} se sustituye por lo que el estudiante escriba
            // (ENGINEERING-GATE-EPICA-C.md, mismo modelo del Commit 6 de
            // Épica B).
            expectedOutput: '¿Cómo te llamas? Hola, {input1}',
            hint: 'A la pregunta ¿Cómo te llamas? le faltan las comillas — sin ellas, Python no puede leerla como texto.',
            hintsByCategory: {
              sintaxis: 'Python no reconoce ¿Cómo te llamas? como texto porque no está entre comillas — por eso ni siquiera puede ejecutar la línea.',
              variables: 'El problema no es una variable — es que la pregunta de input() necesita comillas para ser texto.',
              logica: 'La estructura input(...) ya es correcta; el problema es lo que hay dentro del paréntesis.',
              salida: 'Una vez corregido, debe mostrar exactamente "¿Cómo te llamas? Hola, " seguido de lo que escribiste cuando Python te lo pidió.',
            },
            workedExample: {
              code: 'ciudad = input(¿En qué ciudad vives? )\nprint("Vives en", ciudad)\n# el error es la falta de comillas:\nciudad = input("¿En qué ciudad vives? ")',
              output: '¿En qué ciudad vives? Vives en Trujillo',
              explanation: 'Sin comillas, Python no puede interpretar la pregunta como texto — con comillas, la reconoce y la muestra. Ese es el mismo error que debes corregir aquí.',
            },
            resultExplanation: 'Al agregar las comillas, input() pudo reconocer "¿Cómo te llamas? " como el texto de la pregunta — sin ellas, Python ni siquiera lograba ejecutar la línea.',
            solutionCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
            nextStage: {
              mode: 'escribir_parcial',
              prompt: 'Ahora hazlo tú: pregunta ¿Cuál es tu apodo? con input() y saluda con el patrón exacto Hola, <apodo>. El comentario de abajo es solo un recordatorio del patrón, no se ejecuta.',
              starterCode: '# apodo = input("texto de la pregunta")\n# print("Hola,", apodo)\n',
              // Épica C, Commit 4: sin simulatedInputs, input() real —
              // {input1} se sustituye por lo que el estudiante escriba
              // (ENGINEERING-GATE-EPICA-C.md, mismo modelo del Commit 6 de
              // Épica B).
              expectedOutput: '¿Cuál es tu apodo? Hola, {input1}',
              hint: 'Escribe tus propias dos líneas con apodo = input("¿Cuál es tu apodo? ") y print("Hola,", apodo) — el comentario de arriba no cuenta como código.',
              hintsByCategory: {
                sintaxis: 'Revisa que tus líneas (no el comentario) tengan comillas y paréntesis completos.',
                variables: 'Necesitas crear apodo con input() antes de que print() pueda usarla.',
                logica: 'El comentario que empieza con # no se ejecuta — necesitas escribir tus propias líneas, sin el #.',
                salida: 'Revisa que el resultado sea exactamente "¿Cuál es tu apodo? Hola, " seguido de lo que escribiste cuando Python te lo pidió.',
              },
              workedExample: {
                code: '# apodo = input("texto de la pregunta")\n# print("Hola,", apodo)\nciudad = input("¿En qué ciudad vives? ")\nprint("Vives en", ciudad)',
                output: '¿En qué ciudad vives? Vives en Trujillo',
                explanation: 'El comentario (las líneas con #) es solo una nota para ti — Python la ignora. Las líneas reales que se ejecutan son las que escribes debajo, sin el #.',
              },
              resultExplanation: 'Escribiste tus propias dos líneas (apodo = input(...) y print("Hola,", apodo)) y Python las ejecutó tal cual — por eso ves tu propia pregunta seguida de tu propio saludo, con lo que escribiste en el lugar de apodo.',
              solutionCode: 'apodo = input("¿Cuál es tu apodo? ")\nprint("Hola,", apodo)',
              nextStage: {
                mode: 'escribir_completo',
                prompt: 'Ahora profundiza: escribe tú mismo, desde cero, el código que pregunte ¿Cómo te llamas? y salude exactamente con el patrón Mucho gusto, <nombre> — esta vez input() es real: la respuesta la escribes tú, no un valor ya fijado.',
                starterCode: '',
                // Commit 6, Épica B: sin simulatedInputs, input() real —
                // {input1} se sustituye por lo que el estudiante escriba
                // (ENGINEERING-GATE-EPICA-B.md §9, moduleExperience.ts).
                expectedOutput: '¿Cómo te llamas? Mucho gusto, {input1}',
                hint: 'Usa las mismas dos líneas de siempre: nombre = input("¿Cómo te llamas? ") y print("Mucho gusto,", nombre)',
                hintsByCategory: {
                  sintaxis: 'Revisa que input() y print() tengan sus paréntesis y comillas completos.',
                  variables: 'Necesitas crear nombre con input() antes de que print() pueda usarla.',
                  logica: 'El orden es: primero input() pregunta y guarda, y solo después print() saluda.',
                  salida: 'Revisa que tu saludo siga exactamente el patrón "Mucho gusto, " seguido de lo que escribiste cuando Python te lo pidió.',
                },
                workedExample: {
                  code: 'nombre = input("¿Cómo te llamas? ")\nprint("Hola,", nombre)',
                  output: '¿Cómo te llamas? Hola, Ana',
                  explanation: 'Las mismas dos líneas de siempre — solo cambia la palabra de saludo. Fíjate en el patrón, no copies el mensaje: el tuyo dice "Mucho gusto,".',
                },
                resultExplanation: 'Desde cero, input() y print() volvieron a trabajar juntos: uno pregunta y guarda, el otro usa lo guardado para saludar — el mismo patrón de todo el ciclo, ahora escrito enteramente por ti.',
                solutionCode: 'nombre = input("¿Cómo te llamas? ")\nprint("Mucho gusto,", nombre)',
              },
            },
          },
        },
      },
    },
  },
  decision: {
    question: 'Ya sabes hacer que un programa pregunte y espere una respuesta — y por qué eso lo vuelve realmente interactivo. ¿Cómo quieres consolidarlo?',
    reinforcements: [
      {
        kind: 'reto',
        label: 'Resolver un reto rápido',
        title: 'Reto: cuánta batería reservar para la vuelta',
        body: ['Misma regla: pregunta, guarda y recién entonces usa la respuesta. Hay un impostor.'],
        practice: {
          kind: 'ordering',
          prompt: 'Ordena las instrucciones para que el robot calcule cuánta batería reservar para el regreso. Descarta la que sea la meta, no un paso.',
          items: [
            { id: 't1', text: 'Muestra la pregunta ¿Cuánta batería tienes ahora?', position: 1 },
            { id: 't2', text: 'Guarda la respuesta en la caja llamada bateria', position: 2 },
            { id: 't3', text: 'Calcula el 10% del valor guardado en bateria', position: 3 },
            {
              id: 'td1',
              text: 'Decide cuánta batería reservar',
              position: null,
              whyWrong: '«Decide cuánta batería reservar» es el resultado que quieres, no una instrucción sobre la caja bateria.',
            },
          ],
          successFeedback: 'Exacto — preguntaste, guardaste y recién ahí calculaste. Así funciona cualquier programa que depende de lo que el usuario responde.',
          orderFeedback: 'El 10% de una batería vacía no existe — primero hay que guardar el valor.',
          generalHint: 'Una de las frases describe el resultado que quieres, no un paso con la caja bateria.',
          solutionExplanation: [
            'Preguntar, guardar y solo después calcular — el mismo orden que necesita cualquier input() real. «Decide cuánta batería reservar» era la meta, no una instrucción sobre la caja.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'bateria = float(input("¿Cuánta batería tienes ahora? "))\nreserva = bateria * 0.10\nprint(reserva)',
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
              code: 'bateria = float(input("¿Cuánta batería tienes ahora? "))\nreserva = bateria * 0.10\nprint(reserva)',
              output: '¿Cuánta batería tienes ahora? 5.0',
              explanation: 'float(input(...)) convierte el texto "50" en el número 50.0 antes de multiplicarlo por 0.10. Sin float(...), Python no puede multiplicar un texto por un decimal. Tu ejercicio usa int() y resta, no float() y multiplica.',
            },
            solutionCode: 'edad = int(input("¿Cuántos años tienes? "))\nfaltan = 100 - edad\nprint(faltan)',
          },
        },
      },
      {
        kind: 'ejemplo',
        label: 'Ver un ejemplo más',
        title: 'Ejemplo: el robot que pregunta antes de actuar',
        medium: 'ejemplo_comentado',
        body: [
          'Este robot no repite siempre la misma acción: pregunta «¿Qué tarea hago ahora?», espera lo que escribes, y solo entonces actúa.',
          'tarea = input("¿Qué tarea hago ahora? ") guarda tu respuesta. ejecutar(tarea) la usa. Sin esa pregunta, el robot no tendría ninguna tarea que hacer.',
          'Tu turno: ordena los pasos que sigue el robot antes de ejecutar la tarea.',
        ],
        practice: {
          kind: 'ordering',
          prompt: 'Arma la secuencia que sigue el robot antes de ejecutar la tarea. Descarta la que sea la meta.',
          items: [
            { id: 'b1', text: 'Muestra la pregunta ¿Qué tarea hago ahora?', position: 1 },
            { id: 'b2', text: 'Guarda lo que escribiste en la caja tarea', position: 2 },
            { id: 'b3', text: 'Ejecuta usando el valor guardado en tarea', position: 3 },
            {
              id: 'bd1',
              text: 'Haz lo que necesito',
              position: null,
              whyWrong: '«Haz lo que necesito» describe el resultado, no dice qué hacer con la caja tarea.',
            },
          ],
          successFeedback: 'Exacto — sin la pregunta inicial, el robot no tendría ninguna tarea que ejecutar.',
          orderFeedback: 'Ejecutar sin haber guardado la tarea no tiene con qué trabajar.',
          generalHint: 'Una de las frases describe el resultado, no un paso con la caja tarea.',
          solutionExplanation: [
            'Preguntar, guardar y solo después ejecutar — el mismo orden que necesita cualquier programa que depende del usuario.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'tarea = input("¿Qué tarea hago ahora? ")\nejecutar(tarea)',
          explanation:
            'La secuencia que armaste es, en Python, dos líneas: input() pregunta y guarda; ejecutar(tarea) usa esa respuesta. Nada de "haz lo que necesito" — eso no es una instrucción.',
          practice: {
            prompt: 'Ahora hazlo tú: pide el color favorito con input("¿Cuál es tu color favorito? ") y únelo al texto "Tu color favorito es " usando el operador + antes de mostrarlo con print()',
            starterCode: '# escribe tu código aquí\n',
            expectedOutput: '¿Cuál es tu color favorito? Tu color favorito es azul',
            simulatedInputs: ['azul'],
            hint: 'El operador + une dos textos en uno solo: "Tu color favorito es " + color — recuerda dejar el espacio antes de la comilla final.',
            hintsByCategory: {
              sintaxis: 'Revisa las comillas y el signo + entre los dos textos: "Tu color favorito es " + color',
              variables: 'Python no encuentra color porque nunca se creó con input() antes de usarla con +.',
              logica: 'Revisa el orden: primero input() guarda la respuesta, y solo después + puede unirla al texto fijo.',
              salida: '+ une los textos exactamente como están escritos — revisa que el espacio quede antes de la comilla final, no después.',
            },
            workedExample: {
              code: 'apodo = input("¿Cuál es tu apodo? ")\nprint("Tu apodo es " + apodo)',
              output: '¿Cuál es tu apodo? Tu apodo es Nico',
              explanation: '+ pegó "Tu apodo es " con el valor de apodo, sin espacio de más ni de menos porque el espacio ya estaba dentro de las comillas del texto fijo. Tu ejercicio une color, no apodo.',
            },
            solutionCode: 'color = input("¿Cuál es tu color favorito? ")\nprint("Tu color favorito es " + color)',
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
        title: 'Una última explicación',
        medium: 'clip_narrado',
        narrationAudioAsset: 'm1-c3-refuerzo-audio',
        narrationText:
          '¿Sabes lo incómodo que es cuando le preguntas algo a un robot y, sin esperar tu respuesta, sigue haciendo otra cosa? Un programa sin input() hace exactamente eso: muestra una pregunta y sigue de largo, sin escuchar nada. input() es lo que le enseña a un programa a esperar — a detenerse hasta que tú realmente respondas. Y esa respuesta no se pierde: queda guardada en una variable, lista para usarse el resto del programa.',
        body: [
          '¿Sabes lo incómodo que es cuando le preguntas algo a un robot y, sin esperar tu respuesta, sigue haciendo otra cosa? Se siente raro, ¿verdad?',
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
        title: 'Un paso atrás: veamos un caso ya resuelto',
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
          orderFeedback: 'Guardar una respuesta que nunca llegó no es posible — primero hace falta preguntarla y esperarla.',
          generalHint: 'Una de esas frases dice QUÉ quieres que pase, no qué debe hacer el robot paso a paso.',
        },
      },
      {
        level: 2,
        title: 'Vamos más despacio, con otra imagen',
        conceptModality: 'alternate',
        body: [
          'Piensa en el robot con un cartel donde muestra una pregunta. Primero aparece la pregunta en el cartel («Nombre: _____»); recién cuando TÚ le respondes, el robot tiene un dato. Sin tu respuesta, el cartel sigue en blanco.',
          'input() es ese cartel en blanco: existe la pregunta, pero el valor solo aparece cuando alguien responde. Ahora practica con solo dos pasos y un impostor.',
        ],
        illustration: {
          medium: 'diagrama',
          mediumLabel: 'Analogía visual: pregunta impresa → respuesta → dato',
          body: [
            '🤖 [ CARTEL DEL ROBOT ]  ← la pregunta impresa, todavía sin respuesta.',
            '     ├── «Muestra la pregunta ¿Cuántos años tienes?»   ← el robot pregunta',
            '     └── «Guarda la respuesta en la caja edad»           ← recién aquí hay un dato',
            'Sin la pregunta, nadie sabe qué escribir. Sin guardar la respuesta, se pierde apenas el programa sigue.',
          ],
          // Auditoría "infografías" (jul 2026, segunda vuelta): ver misma
          // nota en ciclo1-instrucciones-precisas.ts — `imageAsset` ya está
          // listo para resolver contra illustrationAssets.ts.
          imageAsset: 'm1-c3-l2-cartel-robot',
          imagePrompt:
            'Diagrama jerárquico minimalista para una app educativa de programación, modo oscuro.\n\n' +
            'COMPOSICIÓN: un nodo superior centrado con forma de PANTALLA/CARTEL de un robot (un rectángulo con una línea de pregunta mostrada y un espacio en blanco debajo, todavía sin respuesta), del que bajan dos líneas conectoras en "Y" invertida hacia dos nodos inferiores: uno muestra al robot MOSTRANDO la pregunta en su pantalla, el otro muestra una CAJA/contenedor guardando la respuesta.\n\n' +
            'ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo — iconografía plana tipo robot/pantalla y contenedor, coherente con un diagrama de flujo de producto SaaS.\n\n' +
            'COLORES: fondo casi negro #0a0a0f. Nodo superior (cartel sin responder): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8%. Nodos inferiores: borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Líneas conectoras gris translúcido rgba(255,255,255,0.15). Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.\n\n' +
            'ICONOS: icono outline de un robot con una pantalla mostrando una línea punteada donde iría la respuesta, en el nodo superior. En el nodo inferior izquierdo, un icono de globo de diálogo (la pregunta se muestra). En el nodo inferior derecho, un icono de caja/contenedor con un check dentro (el dato quedó guardado).\n\n' +
            'DISTRIBUCIÓN: formato vertical 4:5. Cartel del robot ocupa ~20% de la altura, centrado arriba. Los dos nodos inferiores ocupan la mitad inferior, con amplio espacio en blanco entre ellos y respecto a los bordes.\n\n' +
            'ELEMENTOS DE TEXTO (incluir literalmente):\n' +
            '— Nodo superior: "CARTEL DEL ROBOT" + subtítulo pequeño "la pregunta impresa, todavía sin respuesta"\n' +
            '— Nodo inferior izquierdo: "Muestra la pregunta ¿Cuántos años tienes?" + etiqueta pequeña "el robot pregunta"\n' +
            '— Nodo inferior derecho: "Guarda la respuesta en la caja edad" + etiqueta pequeña "recién aquí hay un dato"\n' +
            '— Leyenda inferior centrada, fuera de los nodos: "Sin la pregunta, nadie sabe qué escribir. Sin guardar la respuesta, se pierde apenas el programa sigue."',
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
          orderFeedback: 'Sin preguntar primero, no hay ninguna respuesta que guardar.',
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
          'Llegaste hasta el final de esta ayuda, y eso no es un tropiezo: es una señal que el sistema usará para acompañarte mejor más adelante.',
          'Repasa la secuencia resuelta y continúa cuando estés listo.',
        ],
      },
    ],
  },
}
