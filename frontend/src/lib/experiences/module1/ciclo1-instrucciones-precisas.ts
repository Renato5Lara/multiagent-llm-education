// Módulo 1 · Ciclo 1 — Instrucciones precisas.
// Extraído de module1.ts (refactor mecánico, sin cambio de comportamiento).

import type { LearningCycle } from '@/types/moduleExperience'
import { PRINT_PRIMER } from '../conceptPrimers'

export const CICLO_1_INSTRUCCIONES_PRECISAS: LearningCycle = {
  id: 'ciclo-1',
  conceptId: 'instrucciones_precisas',
  conceptLabel: 'Instrucciones precisas',
  priorMastery: 0.2,
  conceptPrimers: [PRINT_PRIMER],
  curiosityFact: {
    fact:
      'En 1801, el telar de Jacquard tejía patrones complejos usando tarjetas perforadas: cada agujero (o su ausencia) le decía a la máquina exactamente qué hilo levantar. Sin una tarjeta ambigua — el telar no sabía "interpretar", solo ejecutar.',
    connection:
      'Ese telar resolvía el mismo problema que vas a resolver hoy, más de un siglo antes de la primera computadora: cómo darle instrucciones a una máquina que no puede adivinar nada.',
    source: 'Computer History Museum',
  },
  concept: {
    title: '¿Qué hace precisa a una instrucción?',
    quickRecap: {
      body: [
        'Recordatorio rápido: una instrucción es precisa cuando no deja nada a la imaginación de quien la ejecuta — qué hacer, con qué, cuánto y hacia dónde. Una computadora funciona igual: Python ejecuta exactamente lo que escribes, ni más ni menos.',
      ],
    },
    secondExample: {
      label: 'Otro caso — el manual de calibración del robot',
      body: [
        'El manual de calibración del robot nunca dice «ajusta el brazo»: dice «gira el tornillo de la articulación del codo dos vueltas en sentido horario, hasta sentir resistencia». Qué pieza, cuánto, en qué dirección y hasta cuándo — nada queda a tu imaginación.',
        'Es la misma regla de la puerta, en un contexto completamente distinto: una instrucción precisa no cambia según la tarea, cambia según cuánto deja adivinar.',
      ],
    },
    pythonBridge: {
      label: 'Esto ya es Python',
      code: 'girar(grados=90, direccion="izquierda")',
      explanation:
        'Fíjate: la instrucción precisa del robot («gira 90 grados a la izquierda») y esta línea de Python dicen exactamente lo mismo — qué hacer, cuánto y hacia dónde. Una función en Python es, ni más ni menos, una instrucción precisa con nombre.',
    },
    variants: {
      visual: {
        medium: 'infografia',
        mediumLabel: 'Infografía',
        sourceNote: 'Elegido para ti — tu perfil capta ideas más rápido cuando las ve.',
        infographic: {
          vague: {
            instruction: 'Cruza la habitación',
            questions: ['¿cuántos pasos?', '¿hacia qué lado gira?', '¿qué hace al llegar?'],
          },
          precise: {
            instruction: 'Gira 90 grados a la izquierda. Avanza 4 pasos. Detente frente a la puerta.',
            parts: ['qué hacer', 'cuánto', 'hacia dónde'],
          },
          caption:
            'La diferencia no es el detalle decorativo: la instrucción precisa no deja NINGUNA decisión en manos del robot.',
        },
        // Auditoría "infografías" (jul 2026, tercera vuelta — cobertura
        // completa): esta era la infografía PRINCIPAL de teoría, la única
        // categoría que había quedado sin imagePrompt en la vuelta anterior
        // (solo remediación L2 lo tenía). `imageAsset` ya está listo para
        // resolver contra illustrationAssets.ts; hasta entonces se muestra
        // `infographic` (comparación de nodos) como hoy — compatibilidad total.
        imageAsset: 'm1-c1-teoria-cruza-habitacion',
        imagePrompt:
          'Infografía comparativa de dos paneles para una app educativa de programación, modo oscuro.\n\n' +
          'COMPOSICIÓN: dos paneles rectangulares del mismo ancho, apilados verticalmente. Panel superior = INSTRUCCIÓN VAGA. Panel inferior = INSTRUCCIÓN PRECISA. Entre ambos, una flecha corta apuntando hacia abajo con una etiqueta pequeña "hazla precisa".\n\n' +
          'ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo ni ilustración de personas — solo formas geométricas, texto e iconos vectoriales simples, como un diagrama de producto SaaS.\n\n' +
          'COLORES: fondo casi negro #0a0a0f. Panel vago (superior): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8% de opacidad. Panel preciso (inferior): borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Flecha central y su etiqueta en gris azulado #94a3b8. Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.\n\n' +
          'ICONOS: tres signos de interrogación (?) pequeños distribuidos junto a las preguntas del panel vago. Tres checks (✓) pequeños junto a las tres partes del panel preciso. Un ícono outline minimalista de robot, pequeño, como ancla temática, en la esquina superior del panel vago (sin volverse realista).\n\n' +
          'DISTRIBUCIÓN: formato vertical 4:5. Panel vago ocupa el 40% superior, panel preciso el 40% inferior, con la flecha y su etiqueta en el 10% central, y una leyenda final en el 10% inferior, fuera de ambos paneles.\n\n' +
          'ELEMENTOS DE TEXTO (incluir literalmente):\n' +
          '— Panel vago, título: "CRUZA LA HABITACIÓN" — debajo, en lista: "¿cuántos pasos?", "¿hacia qué lado gira?", "¿qué hace al llegar?"\n' +
          '— Panel preciso, título: "GIRA 90° A LA IZQUIERDA. AVANZA 4 PASOS. DETENTE FRENTE A LA PUERTA." — debajo, en lista: "qué hacer", "cuánto", "hacia dónde"\n' +
          '— Leyenda inferior centrada, fuera de los paneles: "La diferencia no es el detalle decorativo: la instrucción precisa no deja ninguna decisión en manos del robot."',
        body: [
          'Una instrucción es precisa cuando cualquier ejecutor — humano o máquina — produce exactamente el mismo resultado.',
          'Una computadora no imagina nada más. Python es el lenguaje con el que le escribes instrucciones precisas — igual que las que vas a construir para el robot.',
        ],
      },
      reading: {
        medium: 'texto',
        mediumLabel: 'Texto estructurado',
        sourceNote: 'Elegido para ti — tu perfil profundiza mejor leyendo a su ritmo.',
        body: [
          'Idea: una instrucción es precisa cuando no requiere que el ejecutor adivine nada — qué objeto usar, cuánto, dónde, en qué orden.',
          'Ejemplo: imagina una demostración de robótica de servicio. A un robot doméstico se le da la instrucción «cruza la habitación» y se queda inmóvil, con un error en pantalla. No está descompuesto: «cruza» no dice cuántos pasos, hacia qué lado gira ni qué hace al llegar — y un robot no adivina nada de eso.',
          'Explicación: el ingeniero no falló al diseñar el robot — escribió una instrucción incompleta. Cada palabra que asumía algo («cruza la habitación», ¿cuántos pasos?) dejaba una decisión en manos del robot. Y un robot no decide: se detiene o hace algo absurdo.',
          'En resumen: si tu instrucción necesita que alguien adivine algo, no es una instrucción — es un deseo. Python solo ejecuta instrucciones, nunca deseos. Ese es el primer hábito mental de la programación.',
        ],
      },
      audio: {
        medium: 'clip_narrado',
        mediumLabel: 'Clip narrado',
        sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
        narrationText:
          'Imagina que le das instrucciones a un robot doméstico que jamás ha hecho esta tarea antes, y que hará exactamente lo que le dijiste. Cruza la habitación. ¿Cuántos pasos? ¿Hacia qué lado giras? Tú lo tenías claro en tu cabeza, pero no lo dijiste, y el robot no adivina. Esa es la regla de oro: si tu instrucción necesita que el robot adivine algo, no es una instrucción, es un deseo. Las máquinas no cumplen deseos: ejecutan instrucciones. Y una computadora funciona exactamente igual. Python es la forma en que le escribes esas instrucciones. Si eres preciso, ejecuta. Si no lo eres, falla.',
        body: [
          'Imagina que le das instrucciones a un robot doméstico que jamás ha hecho esta tarea antes… y que hará EXACTAMENTE lo que le dijiste. «Cruza la habitación». ¿Cuántos pasos? ¿Hacia qué lado giras? Tú lo tenías claro en tu cabeza — pero no lo dijiste, y el robot no adivina.',
          'Esa es la regla de oro: si tu instrucción necesita que el robot adivine algo, no es una instrucción — es un deseo. Las máquinas no cumplen deseos. Ejecutan instrucciones.',
          'Y esa regla no es solo de este robot. Una computadora funciona exactamente igual. Python es la forma en que le escribes esas instrucciones. Si eres preciso, ejecuta. Si no lo eres, falla.',
        ],
      },
      kinesthetic: {
        medium: 'simulacion',
        mediumLabel: 'Manos a la obra',
        sourceNote: 'Elegido para ti — tu perfil aprende haciendo, no leyendo.',
        body: [
          'Nada de teoría por ahora: abajo tú mismo le vas a dar al robot la secuencia de instrucciones para cruzar la habitación. Si alguna es ambigua, el robot se detiene con error — pruébalo.',
        ],
      },
    },
  },
  practice: {
    kind: 'ordering',
    prompt:
      'Pon a prueba lo que acabas de leer: el robot debe cruzar la habitación y abrir la puerta sin chocar. Construye la secuencia usando SOLO instrucciones precisas — una de la lista es ambigua y debes descartarla.',
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
    code: 'girar(grados=90, direccion="izquierda")\navanzar(pasos=4)\ndetenerse()\nextender_mano()\ngirar_manija()',
    explanation:
      'La secuencia que acabas de construir es, literalmente, un programa: cada línea es una instrucción precisa que Python ejecuta de arriba hacia abajo, exactamente en el orden en que la escribiste — ni una línea más, ni una menos de lo que dijiste. Ahora vas a usar esa misma idea — una función con datos exactos — para que el propio robot te cuente lo que hizo.',
    // Andamiaje completo (jul 2026, Sprint 2; retemado jul 2026 — consolidación
    // Ciclo 1): la MISMA tarjeta encadena los seis peldaños reales — nunca
    // "Etapa X de 6", el estudiante solo ve una consigna que cambia. Los seis
    // peldaños reportan sobre la MISMA misión que el estudiante acaba de
    // resolver arriba (cruzar la habitación, abrir la puerta — "Territorio:
    // Explorador" de la apertura de la misión), nunca un tema nuevo sin
    // relación: antes decían "Robot listo"/"Sistema listo", una serie de
    // mensajes genéricos sin conexión con la práctica que los precede — la
    // ruptura de continuidad más visible del ciclo.
    practice: {
      mode: 'observar',
      prompt: 'Obsérvalo: el robot ya cruzó la habitación y abrió la puerta. Ejecuta esta línea y mira cómo te lo reporta.',
      starterCode: 'print("Puerta abierta")\n',
      expectedOutput: 'Puerta abierta',
      hint: 'El código ya está completo — solo presiona Ejecutar para ver qué muestra.',
      resultExplanation: 'print("Puerta abierta") le dijo a Python: muestra exactamente ese texto en pantalla. Por eso lo que ves arriba, "Puerta abierta", es lo que había entre las comillas — ni más, ni menos.',
      solutionCode: 'print("Puerta abierta")',
      nextStage: {
        mode: 'manipular',
        prompt: 'Ahora tú: cambia SOLO el texto entre comillas para que el robot reporte exactamente Misión cumplida',
        starterCode: 'print("Puerta abierta")\n',
        expectedOutput: 'Misión cumplida',
        hint: 'Solo cambia el texto entre comillas — el resto de la línea no necesita tocarse: print("Misión cumplida")',
        hintsByCategory: {
          sintaxis: 'Revisa que las comillas sigan completas después de cambiar el texto.',
          variables: 'Si borraste alguna comilla, Python deja de ver "Misión cumplida" como texto y busca variables llamadas Misión y cumplida — y ninguna existe.',
          logica: 'Solo cambia lo que está entre comillas; print() no cambia.',
          salida: 'Revisa que el texto sea exactamente "Misión cumplida" — mayúscula inicial, sin comillas de más.',
        },
        workedExample: {
          code: 'print("Camino libre")',
          output: 'Camino libre',
          explanation: 'Cambiar el reporte es escribir un texto distinto entre las mismas comillas — print() no cambia, solo lo que le pasas. Fíjate en el patrón: el tuyo debe decir "Misión cumplida".',
        },
        resultExplanation: 'Cambiaste el texto entre comillas y print() mostró exactamente ese texto nuevo — la función no cambió, solo el dato que le diste. Eso es lo que separa la instrucción (print) del valor exacto que reporta.',
        solutionCode: 'print("Misión cumplida")',
        nextStage: {
          mode: 'completar',
          prompt: 'Completa el código: falta la función que hace que el robot reporte su estado en pantalla. Reemplaza el espacio en blanco para que muestre exactamente Explorador listo',
          starterCode: '_____("Explorador listo")\n',
          expectedOutput: 'Explorador listo',
          hint: 'La función que reporta texto en pantalla es print — reemplaza los guiones bajos por esa palabra exacta, sin dejar nada de ellos.',
          hintsByCategory: {
            sintaxis: 'Revisa que no queden guiones bajos ni espacios de más antes del paréntesis.',
            variables: 'Python busca algo llamado "_____" porque todavía no reemplazaste el espacio en blanco por print.',
            logica: 'Solo falta el nombre de la función — el paréntesis y el texto entre comillas ya están completos.',
            salida: 'Revisa que el texto siga siendo exactamente "Explorador listo".',
          },
          workedExample: {
            code: '_____("Camino libre")\n# se completa así:\nprint("Camino libre")',
            output: 'Camino libre',
            explanation: 'El hueco siempre se completa con el nombre de una función que ya conoces — aquí, print. Fíjate en el patrón: el texto entre comillas no cambia, solo el espacio en blanco.',
          },
          resultExplanation: 'Al escribir print en el hueco, Python pudo por fin reconocer la instrucción — el texto entre comillas ya estaba bien, solo faltaba nombrar la función que lo muestra en pantalla.',
          solutionCode: 'print("Explorador listo")',
          nextStage: {
            mode: 'corregir',
            prompt: 'Este código tiene un error: le falta algo para que "Territorio cruzado" sea reconocido como texto. Encuéntralo y corrígelo.',
            starterCode: 'print(Territorio cruzado)\n',
            expectedOutput: 'Territorio cruzado',
            hint: 'A "Territorio cruzado" le faltan las comillas — sin ellas, Python cree que son nombres de variables que no existen.',
            hintsByCategory: {
              sintaxis: 'Python no reconoce Territorio cruzado como texto porque no está entre comillas.',
              variables: 'Sin comillas, Python busca dos variables llamadas Territorio y cruzado — y ninguna existe.',
              logica: 'La estructura print(...) ya es correcta; el problema es lo que hay dentro del paréntesis.',
              salida: 'Una vez corregido, debe mostrar exactamente "Territorio cruzado".',
            },
            workedExample: {
              code: 'print(Puerta abierta)\n# el error es la falta de comillas:\nprint("Puerta abierta")',
              output: 'Puerta abierta',
              explanation: 'Sin comillas, Python interpreta las palabras como nombres de variables — con comillas, las reconoce como texto. Ese es el mismo error que debes corregir aquí.',
            },
            resultExplanation: 'Agregar las comillas fue lo que arregló el código: sin ellas Python buscaba variables llamadas Territorio y cruzado; con ellas, reconoce el mismo texto como algo que solo hay que mostrar, no buscar.',
            solutionCode: 'print("Territorio cruzado")',
            nextStage: {
              mode: 'escribir_parcial',
              prompt: 'Ahora hazlo tú: usa print() para que el robot reporte exactamente Sala superada. El comentario de abajo es solo un recordatorio del patrón, no se ejecuta.',
              starterCode: '# print("texto entre comillas")\n',
              expectedOutput: 'Sala superada',
              hint: 'Escribe tu propia línea con print("Sala superada") — el comentario de arriba no cuenta como código, solo te recuerda el patrón.',
              hintsByCategory: {
                sintaxis: 'Revisa que tu línea (no el comentario) tenga comillas y paréntesis completos.',
                variables: 'Si escribes Sala superada sin comillas, Python busca variables llamadas Sala y superada — y ninguna existe.',
                logica: 'El comentario que empieza con # no se ejecuta — necesitas escribir una línea nueva sin el #.',
                salida: 'Revisa que el texto sea exactamente "Sala superada".',
              },
              workedExample: {
                code: '# print("texto entre comillas")\nprint("Ruta despejada")',
                output: 'Ruta despejada',
                explanation: 'El comentario (la línea con #) es solo una nota para ti — Python la ignora. La línea real que se ejecuta es la que escribes debajo, sin el #.',
              },
              resultExplanation: 'Escribiste tu propia línea con print("Sala superada") y Python la ejecutó tal cual — el comentario de arriba nunca corrió, solo tu línea real produjo esta salida.',
              solutionCode: 'print("Sala superada")',
              nextStage: {
                mode: 'escribir_completo',
                prompt: 'Ahora profundiza: escribe tú mismo, desde cero, una instrucción que haga que el robot reporte exactamente Recorrido terminado',
                starterCode: '',
                expectedOutput: 'Recorrido terminado',
                hint: 'Usa la función print() con el texto exacto entre comillas: print("Recorrido terminado")',
                hintsByCategory: {
                  sintaxis: 'Revisa que las comillas y los paréntesis estén completos: print("texto") necesita abrir y cerrar ambos.',
                  variables: 'Si escribes Recorrido terminado sin comillas, Python busca variables llamadas Recorrido y terminado — y ninguna existe.',
                  logica: 'print() solo necesita el texto entre paréntesis — no hace falta llamar a ninguna otra función.',
                  salida: 'Revisa mayúsculas, espacios y signos: debe coincidir letra por letra con "Recorrido terminado".',
                },
                workedExample: {
                  code: 'print("Puerta abierta")',
                  output: 'Puerta abierta',
                  explanation: 'print() siempre muestra exactamente el texto que le des entre comillas — ni más, ni menos. Fíjate en el patrón, no copies el mensaje: el tuyo es "Recorrido terminado".',
                },
                resultExplanation: 'Desde cero, print("Recorrido terminado") volvió a producir exactamente el texto entre comillas — la misma regla de los cinco peldaños anteriores, ahora escrita enteramente por ti.',
                solutionCode: 'print("Recorrido terminado")',
              },
            },
          },
        },
      },
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
        title: 'Ejemplo: el robot recorre otro pasillo',
        medium: 'ejemplo_comentado',
        body: [
          'Este mismo robot no solo cruza una habitación: puede recorrer cualquier pasillo de la casa, siempre que le des instrucciones igual de precisas.',
          'Distancia exacta, giro exacto, punto exacto donde detenerse. El robot no entiende «llega al final del pasillo» — solo entiende pasos, grados y un punto de parada.',
          'Un programa en Python es exactamente eso: una ruta de instrucciones precisas que la computadora sigue sin adivinar nada. Ahora hazlo tú: arma la ruta del robot por el pasillo.',
        ],
        // BUG-003 (C-52): el ejemplo también se PRACTICA, no solo se lee.
        practice: {
          kind: 'ordering',
          prompt: 'Arma la ruta que el robot debe seguir para cruzar el pasillo. Una de las frases no es una instrucción — descártala.',
          items: [
            { id: 'g2', text: 'Gira 90 grados a la derecha', position: 2 },
            {
              id: 'gd1',
              text: 'Llega al final del pasillo',
              position: null,
              whyWrong: '«Llega al final del pasillo» dice a dónde quieres llegar, no qué hacer ahora — es la meta disfrazada de paso, igual que «riega la planta».',
            },
            { id: 'g1', text: 'Avanza 6 pasos por el pasillo', position: 1 },
            { id: 'g3', text: 'Detente frente a la puerta del armario', position: 3 },
          ],
          successFeedback:
            'Exacto — armaste una ruta que el robot ejecuta exactamente igual cada vez. Así se ve un programa: pasos precisos, en orden, sin metas disfrazadas.',
          orderFeedback: 'El robot no puede girar a la derecha antes de haber avanzado los 6 pasos del pasillo.',
          generalHint: 'Una de las frases dice a DÓNDE llegar, no QUÉ hacer. Esa no es una instrucción.',
          solutionExplanation: [
            'Primero avanzar, después girar, después detenerse — cada paso deja al robot donde el siguiente lo necesita. «Llega al final del pasillo» era la meta: nunca se la das como paso.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'avanzar(pasos=6)\ngirar(grados=90, direccion="derecha")\ndetenerse()',
          explanation:
            'La ruta que acabas de armar es la misma secuencia, en Python: tres funciones, en orden, cada una con sus datos exactos — nada de "llega al final del pasillo".',
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
            'Meta: que el robot apague la luz del pasillo.',
            '1. «Camina hasta el interruptor del pasillo» — dice hasta dónde. Precisa.',
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
          'Piensa en el manual de tareas del robot. «Recarga la batería» no es un paso: es el título. Los pasos son «conecta el cable al puerto de carga», «espera a que la luz se ponga verde».',
          'El robot solo entiende los pasos del manual, nunca el título. Un programa en Python también es un manual: solo pasos ejecutables, nunca deseos. Ahora practica con solo dos pasos y un impostor.',
        ],
        illustration: {
          medium: 'diagrama',
          mediumLabel: 'Analogía visual: título vs. pasos',
          body: [
            '🔋 [ RECARGA LA BATERÍA ]  ← el título. El robot no sabe ejecutarlo.',
            '     ├── «Conecta el cable al puerto de carga»   ← ejecutable',
            '     └── «Espera hasta que la luz indicadora se ponga verde»   ← ejecutable',
            'Todo lo que esté en la caja de arriba es una meta. Todo lo que cuelga de ella son instrucciones.',
          ],
          // Auditoría "infografías" (jul 2026, segunda vuelta): `imageAsset`
          // ya está listo para resolver — solo falta agregar la entrada real
          // en lib/experiences/illustrationAssets.ts con esta misma clave.
          // Hasta entonces, se muestra `body` como hoy (compatibilidad total).
          imageAsset: 'm1-c1-l2-recarga-bateria',
          imagePrompt:
            'Diagrama jerárquico minimalista para una app educativa de programación, modo oscuro.\n\n' +
            'COMPOSICIÓN: un único nodo superior centrado (la META, ambigua) del que bajan dos líneas conectoras en forma de "Y" invertida hacia dos nodos inferiores (los PASOS, ejecutables), distribuidos simétricamente izquierda/derecha.\n\n' +
            'ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo ni ilustración de personas — solo formas geométricas, texto e iconos vectoriales simples, como un diagrama de flujo de producto SaaS.\n\n' +
            'COLORES: fondo casi negro #0a0a0f. Nodo superior: borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8% de opacidad. Nodos inferiores: borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8% de opacidad. Líneas conectoras gris translúcido rgba(255,255,255,0.15). Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8.\n\n' +
            'ICONOS: un signo de interrogación (?) pequeño junto al nodo superior (ambigüedad). Un check (✓) pequeño junto a cada nodo inferior (ejecutable). Un ícono outline minimalista de batería junto al robot, cerca del nodo superior, solo como ancla temática, sin volverse realista.\n\n' +
            'DISTRIBUCIÓN: formato vertical 4:5. Nodo meta ocupa ~20% de la altura, centrado arriba. Los dos nodos de pasos ocupan la mitad inferior, con amplio espacio en blanco entre ellos y respecto a los bordes.\n\n' +
            'ELEMENTOS DE TEXTO (incluir literalmente):\n' +
            '— Nodo superior: "RECARGA LA BATERÍA" + subtítulo pequeño "la meta — el robot no sabe ejecutarlo"\n' +
            '— Nodo inferior izquierdo: "Conecta el cable al puerto de carga"\n' +
            '— Nodo inferior derecho: "Espera hasta que la luz indicadora se ponga verde"\n' +
            '— Leyenda inferior centrada, fuera de los nodos: "Todo lo de arriba es una meta. Todo lo que cuelga de ella es una instrucción ejecutable."',
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
}
