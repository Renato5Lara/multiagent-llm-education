// Módulo 1 · Ciclo 2 — Variables.
// Extraído de module1.ts (refactor mecánico, sin cambio de comportamiento).

import type { ConceptVariant, LearningCycle, PredictOutputPracticeDef } from '@/types/moduleExperience'
import { VARIABLES_PRIMER } from '../conceptPrimers'

// Experience Recipe — Etapa 2 del Experience Orchestrator (jul 2026): la
// experiencia "lectora" completa de Variables (teoría + práctica) se define
// UNA vez aquí y se referencia tanto desde concept.variants.reading (Etapa 1,
// piezas sueltas) como desde recipes.reading (Etapa 2, unidad completa) —
// nunca se duplica el contenido, solo se agrupa.
const READING_CONCEPT_VARIANT: ConceptVariant = {
  medium: 'texto',
  mediumLabel: 'Texto estructurado',
  sourceNote: 'Elegido para ti — tu perfil profundiza mejor leyendo a su ritmo.',
  body: [
    'Imagina un programa que usa la posición del robot tres veces: una para mostrarla en pantalla, otra para guardarla en el registro de recorrido, otra para avisar si ya llegó al destino. Si escribes la posición suelta las tres veces y la posición cambia, tienes que corregirla en las tres.',
    'Una variable resuelve exactamente ese problema: le pones nombre a un valor UNA vez — posicion = 4 — y usas ese nombre las veces que necesites. Si la posición cambia, cambias una sola línea.',
    'Por eso una variable no es solo «guardar un dato»: es guardar un dato con un nombre que el resto del programa puede reutilizar sin repetir el valor.',
  ],
}

const READING_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  prompt: '¿Qué imprime este código?',
  code: 'edad = 20\nedad = edad + 1\nprint(edad)',
  options: [
    { id: 'a', text: '20' },
    { id: 'b', text: '21' },
    { id: 'c', text: 'edad' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'b',
  successFeedback: 'Exacto — «edad» empezó en 20, pero «edad = edad + 1» la reasignó antes del print(). La caja guarda lo último que se le pidió guardar.',
  wrongFeedback: 'Revisa: print(edad) muestra lo que HAY en la caja en ESE momento, no el valor con el que se creó.',
  solutionExplanation: [
    'Línea 1: edad = 20 — crea la caja con el valor 20.',
    'Línea 2: edad = edad + 1 — lee el 20 que había, le suma 1, y guarda 21 en la misma caja.',
    'Línea 3: print(edad) — muestra lo que hay AHORA en la caja: 21, no el 20 inicial.',
  ],
}

// Sprint "diversidad pedagógica" (jul 2026): antes de este sprint, la
// práctica PRINCIPAL de visual/audio/kinestésico repetía 'ordering' (arrastrar
// y ordenar) en TODOS los ciclos del módulo — el mismo patrón de interacción,
// ciclo tras ciclo, mientras solo 'reading' alternaba con 'predict_output'.
// Estas tres variantes le dan a cada perfil su PROPIA versión de "predecir la
// ejecución" — mismo componente ya existente (PredictOutputPractice, cero
// arquitectura nueva), mismo concepto evaluado (reasignación de variable),
// pero con su propio tema y voz — nunca el texto genérico de READING_PRACTICE
// reetiquetado. Los tres reemplazan el 'ordering' que este ciclo heredaría de
// `default`, rompiendo así la repetición Ciclo 1→Ciclo 2 para cada perfil.
const VISUAL_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  // Auditoría "diversidad pedagógica" (revisión post-sprint, jul 2026): copy
  // reforzado hacia "comparar visualmente el antes y el después de la caja",
  // no solo "leer código" — misma mecánica (predict_output), pero enmarca la
  // tarea como observar dos estados de la misma caja, coherente con la
  // metáfora visual de "caja" ya usada en la teoría de este ciclo.
  prompt: 'Observa la caja "tareas" en dos momentos: antes y después de la segunda línea. ¿Qué valor final muestra en pantalla?',
  code: 'tareas = 5\ntareas = tareas + 3\nprint(tareas)',
  options: [
    { id: 'a', text: '5' },
    { id: 'b', text: '8' },
    { id: 'c', text: 'tareas' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'b',
  successFeedback: 'Exacto — visualizando la caja «tareas»: empezó mostrando 5, pero «tareas = tareas + 3» la actualizó a 8 antes del print(). La caja siempre muestra su último valor, nunca el de arranque.',
  wrongFeedback: 'Compara las dos fotos de la caja: print(tareas) muestra lo que HAY en la caja en ESE momento, no el valor con el que se creó.',
  solutionExplanation: [
    'Línea 1: tareas = 5 — crea la caja con el valor 5.',
    'Línea 2: tareas = tareas + 3 — lee el 5 que había, le suma 3, y guarda 8 en la misma caja.',
    'Línea 3: print(tareas) — muestra lo que hay AHORA en la caja: 8, no el 5 inicial.',
  ],
}

const AUDIO_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  prompt: 'Después de escuchar la explicación, decide: ¿qué imprime este código?',
  code: 'temperatura = 18\ntemperatura = temperatura + 5\nprint(temperatura)',
  // Auditoría "diversidad pedagógica" (revisión post-sprint, jul 2026): antes
  // el prompt PROMETÍA audio ("después de escuchar...") sin reproducir nada.
  // Narra exactamente el código de arriba — el estudiante puede resolver
  // escuchando, sin necesitar leer el bloque de código en absoluto.
  narrationText:
    'Escucha con atención. Primera línea: temperatura es igual a dieciocho. Segunda línea: temperatura es igual a temperatura, más cinco. Tercera línea: imprime temperatura. ¿Qué número muestra la pantalla?',
  options: [
    { id: 'a', text: '18' },
    { id: 'b', text: '23' },
    { id: 'c', text: 'temperatura' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'b',
  successFeedback: 'Exacto — «temperatura» empezó en 18, pero «temperatura = temperatura + 5» la actualizó antes del print(). Escuchaste bien: la caja siempre guarda su último valor.',
  wrongFeedback: 'Revisa: print(temperatura) muestra lo que HAY en la caja en ESE momento, no el valor con el que se creó.',
  solutionExplanation: [
    'Línea 1: temperatura = 18 — crea la caja con el valor 18.',
    'Línea 2: temperatura = temperatura + 5 — lee el 18 que había, le suma 5, y guarda 23 en la misma caja.',
    'Línea 3: print(temperatura) — muestra lo que hay AHORA en la caja: 23, no el 18 inicial.',
  ],
}

// Mismo tema (baterías) que ya predijo mentalmente en la teoría kinestésica de
// este ciclo ("baterias = 3" / "baterias = baterias - 1") — pero con otros
// números, para que resolverlo exija aplicar la regla, no solo recordar la
// respuesta que la teoría ya reveló.
const KINESTHETIC_PRACTICE: PredictOutputPracticeDef = {
  kind: 'predict_output',
  // Auditoría "diversidad pedagógica" (revisión post-sprint, jul 2026): copy
  // reforzado hacia "actuar la resta antes de comprobarla" — misma mecánica
  // (predict_output), pero enmarca la predicción como algo que el estudiante
  // hace con los dedos (contar baterías restantes) antes de ver el resultado,
  // coherente con la escalera manipulable de PythonBridge que ya corre en
  // este ciclo para el perfil kinestésico.
  prompt: 'Cuenta con los dedos: el robot empieza con 5 baterías de repuesto y usa 2. Antes de revisar, predice: ¿qué imprime este código?',
  code: 'baterias = 5\nbaterias = baterias - 2\nprint(baterias)',
  options: [
    { id: 'a', text: '5' },
    { id: 'b', text: '3' },
    { id: 'c', text: 'baterias' },
    { id: 'd', text: 'Error' },
  ],
  correctOptionId: 'b',
  successFeedback: 'Exacto — igual que contar con los dedos, «baterias» empezó en 5 pero perdió 2 antes del print(). Se guarda el resultado, no el valor inicial. Tu cuenta física coincidió con la ejecución real.',
  wrongFeedback: 'Vuelve a contar con los dedos: print(baterias) muestra lo que HAY en la caja en ESE momento, no el valor con el que se creó.',
  solutionExplanation: [
    'Línea 1: baterias = 5 — crea la caja con el valor 5.',
    'Línea 2: baterias = baterias - 2 — lee el 5 que había, le resta 2, y guarda 3 en la misma caja.',
    'Línea 3: print(baterias) — muestra lo que hay AHORA en la caja: 3, no el 5 inicial.',
  ],
}

export const CICLO_2_VARIABLES: LearningCycle = {
  id: 'ciclo-2',
  conceptId: 'variables',
  conceptLabel: 'Variables',
  priorMastery: 0.2,
  conceptPrimers: [VARIABLES_PRIMER],
  // "¿Sabías qué?" solo vive en Ciclo 1 del módulo (Sprint "Auditoría
  // pedagógica", Hallazgo B) — CuriosityFactCard no dedupe entre ciclos por
  // su cuenta, así que definir curiosityFact aquí lo repetía una vez por
  // ciclo en vez de una vez por módulo. Se retira el campo, no el componente.
  concept: {
    title: '¿Qué es una variable?',
    quickRecap: {
      body: [
        'Recordatorio rápido: una variable es una caja con nombre que guarda un valor — nombre = valor — para que puedas reutilizarlo o cambiarlo después sin repetirlo. Leer el nombre siempre te da el último valor guardado.',
      ],
    },
    secondExample: {
      label: 'Otro caso — el compartimento de almacenamiento del robot',
      body: [
        'Un compartimento del robot no es útil por ser una caja: es útil porque tiene un nombre, y ese nombre siempre te lleva al mismo contenido, aunque lo que guardes adentro cambie con cada tarea.',
        'Una variable funciona igual: el NOMBRE (edad, mensaje, bateria) siempre te lleva al mismo valor guardado — hasta que tú decidas guardar uno distinto.',
      ],
    },
    pythonBridge: {
      label: 'Esto ya es Python',
      code: 'compartimento = "llave maestra"',
      explanation:
        '«compartimento» es el nombre; «llave maestra» es lo que guarda. En Python se escribe exactamente así: nombre = valor. Nada más que aprender todavía — solo ponerle nombre a algo que quieres recordar.',
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
      reading: READING_CONCEPT_VARIANT,
      audio: {
        medium: 'clip_narrado',
        mediumLabel: 'Clip narrado',
        sourceNote: 'Elegido para ti — tu perfil retiene mejor las ideas cuando las escucha.',
        narrationText:
          'Piensa en el compartimento de almacenamiento del robot. No te importa la caja en sí — te importa que ese nombre siempre te lleve al mismo contenido, y que puedas cambiar lo que hay adentro sin cambiar el nombre. Una variable es exactamente eso: un nombre que siempre te lleva al mismo valor guardado. Edad, igual, veinte. Ese signo igual no pregunta si son iguales — aquí significa: guarda esto aquí, con este nombre. Y una vez que lo guardaste, usar el nombre es exactamente lo mismo que usar el valor.',
        body: [
          'Piensa en el compartimento de almacenamiento del robot. No te importa la caja en sí — te importa que ese nombre siempre te lleve al mismo contenido, y que puedas cambiar lo que hay adentro sin cambiar el nombre.',
          'Una variable es exactamente eso: un nombre que siempre te lleva al mismo valor guardado. «edad = 20» significa: guarda 20 aquí, con el nombre edad.',
          'Una vez que lo guardaste, usar el nombre es exactamente lo mismo que usar el valor.',
        ],
      },
      kinesthetic: {
        medium: 'simulacion',
        mediumLabel: 'Simulación',
        sourceNote: 'Elegido para ti — tu perfil construye comprensión haciendo.',
        body: [
          '📦 Antes de leer nada, predice: el robot ejecuta «pasos = 0» y luego «pasos = pasos + 10». ¿Qué guarda la caja al final?',
          'Antes de revisar tu respuesta, predice también esta otra: el robot ejecuta «baterias = 3» y después «baterias = baterias - 1». ¿Qué guarda baterias al final?',
          'La primera caja guarda 10: crea la caja con 0 adentro, LEE lo que tenía, le suma 10, y guarda el resultado en la MISMA caja. La segunda guarda 2 — el robot gastó una batería de repuesto, y el nombre sigue siendo el mismo, listo para volver a llenarse cuando haga falta.',
        ],
      },
    },
  },
  // Multimodalidad profunda (jul 2026): la práctica PRINCIPAL, no solo el
  // refuerzo opcional, cambia de mecánica según la modalidad efectiva.
  // 'default' preserva exactamente el comportamiento previo (ordenar pasos);
  // 'reading' exige simular mentalmente la ejecución — otra forma genuina de
  // demostrar el mismo dominio de "variable como caja reasignable".
  practice: {
    default: {
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
    reading: READING_PRACTICE,
    // Sprint "diversidad pedagógica": los tres perfiles restantes también
    // predicen la ejecución en este ciclo (en vez de heredar 'ordering' de
    // `default`) — cada uno con su propio tema y voz, nunca el texto de
    // `reading` reetiquetado. `default` se conserva intacto como red de
    // seguridad (orderingFallbackOf) y por si una modalidad nueva se agrega.
    visual: VISUAL_PRACTICE,
    audio: AUDIO_PRACTICE,
    kinesthetic: KINESTHETIC_PRACTICE,
  },
  pythonBridge: {
    label: 'Esto ya es Python',
    code: 'edad = 20\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
    explanation:
      'Cada caja de tu secuencia es una variable en Python: «edad = 20» crea la caja y guarda el valor en un solo paso; «faltan_para_100 = 100 - edad» lee el valor de edad para calcular otro; print(...) lo muestra. Cada caja aparece exactamente una vez, tal como la armaste — ninguna de más, ninguna de menos.',
    // Andamiaje completo (jul 2026, consolidación Sprint 2): mismos seis
    // peldaños que Ciclo 1 (mismo campo `mode`, mismo componente
    // PythonBridge.tsx), continuando AQUÍ el cálculo que el estudiante ya
    // armó arriba (edad → cuántos años faltan para 100) — nunca un tema
    // nuevo sin relación, el error que auditamos en Ciclo 1.
    practice: {
      mode: 'observar',
      prompt: 'Obsérvalo: presiona Ejecutar y mira cuántos años le faltan al robot para llegar a 100.',
      starterCode: 'edad = 20\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)\n',
      expectedOutput: '80',
      hint: 'El código ya está completo — solo presiona Ejecutar para ver qué muestra.',
      resultExplanation: 'edad guardó 20, faltan_para_100 calculó 100 - edad, y print() mostró ese resultado: 80. Cada variable guarda un valor y la operación lo usa exactamente como quedó guardado.',
      solutionCode: 'edad = 20\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
      nextStage: {
        mode: 'manipular',
        prompt: 'Ahora tú: cambia SOLO el valor de edad a 30 para que el robot calcule cuántos años le faltan ahora',
        starterCode: 'edad = 20\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)\n',
        expectedOutput: '70',
        hint: 'Solo cambia el número junto a edad = — el resto de las líneas no necesita tocarse: edad = 30',
        hintsByCategory: {
          sintaxis: 'Revisa que el número siga sin comillas — es un valor numérico, no texto.',
          variables: 'No necesitas crear ninguna variable nueva — sigue siendo edad, solo con otro valor.',
          logica: 'Solo cambia el número junto a edad =; las otras dos líneas ya calculan y muestran solas.',
          salida: 'Revisa que el resultado sea exactamente 70 — 100 menos el nuevo valor de edad.',
        },
        workedExample: {
          code: 'edad = 45\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
          output: '55',
          explanation: 'Cambiar solo el número junto a edad = 45 hace que faltan_para_100 se recalcule solo — la fórmula no cambia, solo el dato de entrada. Fíjate en el patrón: tu edad debe ser 30, y el resultado 70.',
        },
        resultExplanation: 'Cambiaste solo el valor de edad a 30 y faltan_para_100 se recalculó solo — la fórmula 100 - edad no cambió, cambió el dato que entra en ella, y por eso el resultado ahora es 70.',
        solutionCode: 'edad = 30\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
        nextStage: {
          mode: 'completar',
          prompt: 'Completa el código: falta la función que muestra el resultado en pantalla. Reemplaza el espacio en blanco para que el robot calcule con edad = 40',
          starterCode: 'edad = 40\nfaltan_para_100 = 100 - edad\n_____(faltan_para_100)\n',
          expectedOutput: '60',
          hint: 'La función que muestra un valor en pantalla es print — reemplaza los guiones bajos por esa palabra exacta, sin dejar nada de ellos.',
          hintsByCategory: {
            sintaxis: 'Revisa que no queden guiones bajos ni espacios de más antes del paréntesis.',
            variables: 'faltan_para_100 ya existe — el hueco no es una variable, es el nombre de una función.',
            logica: 'Las dos primeras líneas ya calculan el valor; solo falta la función que lo muestra.',
            salida: 'Revisa que el resultado siga siendo exactamente 60.',
          },
          workedExample: {
            code: 'edad = 45\nfaltan_para_100 = 100 - edad\n_____(faltan_para_100)\n# se completa así:\nprint(faltan_para_100)',
            output: '55',
            explanation: 'El hueco siempre se completa con el nombre de una función que ya conoces — aquí, print. Fíjate en el patrón: el cálculo no cambia, solo el espacio en blanco.',
          },
          resultExplanation: 'Al completar el hueco con print, Python pudo mostrar faltan_para_100 — el cálculo (100 - edad) ya estaba correcto, solo faltaba la función que muestra el resultado en pantalla.',
          solutionCode: 'edad = 40\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
          nextStage: {
            mode: 'corregir',
            prompt: 'Este código tiene un error: escribieron mal el nombre de la variable edad. Encuéntralo y corrígelo para que calcule con edad = 40',
            starterCode: 'edad = 40\nfaltan_para_100 = 100 - eda\nprint(faltan_para_100)\n',
            expectedOutput: '60',
            hint: 'En la segunda línea dice "eda" en vez de "edad" — Python busca una variable que nunca se creó con ese nombre.',
            hintsByCategory: {
              sintaxis: 'La línea en sí está bien escrita — el problema es el nombre, no los signos.',
              variables: 'Python no encuentra "eda" porque la variable se llama edad, con "d" antes de la "a" final.',
              logica: 'La fórmula 100 - edad ya es correcta; solo hay que escribir bien el nombre de la variable.',
              salida: 'Una vez corregido, debe mostrar exactamente 60.',
            },
            workedExample: {
              code: 'edad = 45\nfaltan_para_100 = 100 - eda\nprint(faltan_para_100)\n# el error es el nombre incompleto:\nfaltan_para_100 = 100 - edad',
              output: '55',
              explanation: 'Python distingue "eda" de "edad" — son nombres distintos, y solo uno de ellos fue creado. Ese es el mismo error que debes corregir aquí.',
            },
            resultExplanation: 'Al corregir "eda" a "edad", faltan_para_100 = 100 - edad pudo por fin encontrar la variable correcta — Python nunca "adivina" un nombre parecido, necesita que coincida exactamente.',
            solutionCode: 'edad = 40\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
            nextStage: {
              mode: 'escribir_parcial',
              prompt: 'Ahora hazlo tú: calcula cuántos años le faltan a alguien de 50 años para llegar a 100. El comentario de abajo es solo un recordatorio del patrón, no se ejecuta.',
              starterCode: '# edad = ___\n# faltan_para_100 = 100 - edad\n# print(faltan_para_100)\n',
              expectedOutput: '50',
              hint: 'Escribe tus propias tres líneas con edad = 50, seguido de faltan_para_100 = 100 - edad, y print(faltan_para_100) — el comentario de arriba no cuenta como código.',
              hintsByCategory: {
                sintaxis: 'Revisa que tus líneas (no el comentario) tengan el signo = completo en cada una.',
                variables: 'Necesitas crear edad primero, y solo después faltan_para_100 puede leerla.',
                logica: 'El comentario que empieza con # no se ejecuta — necesitas escribir las tres líneas de nuevo, sin el #.',
                salida: 'Revisa que el resultado sea exactamente 50.',
              },
              workedExample: {
                code: '# edad = ___\n# faltan_para_100 = 100 - edad\n# print(faltan_para_100)\nedad = 45\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
                output: '55',
                explanation: 'El comentario (las líneas con #) es solo una nota para ti — Python la ignora. Las líneas reales que se ejecutan son las que escribes debajo, sin el #.',
              },
              resultExplanation: 'Escribiste tus propias tres líneas (edad = 50, el cálculo, y print) y Python las ejecutó en orden — por eso el resultado es 50, exactamente 100 menos la edad que guardaste.',
              solutionCode: 'edad = 50\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
              nextStage: {
                mode: 'escribir_completo',
                prompt: 'Ahora profundiza: escribe tú mismo, desde cero, el código que calcule cuántos años le faltan a alguien de 64 años para llegar a 100',
                starterCode: '',
                expectedOutput: '36',
                hint: 'Usa las mismas tres líneas de siempre: edad = 64, faltan_para_100 = 100 - edad, print(faltan_para_100)',
                hintsByCategory: {
                  sintaxis: 'Revisa que cada línea tenga su signo = completo, sin comillas — son números.',
                  variables: 'Necesitas crear edad primero; faltan_para_100 no puede leerla si no existe todavía.',
                  logica: 'El orden es: crear edad, calcular faltan_para_100, y solo después mostrarlo con print(...).',
                  salida: 'Revisa que el resultado sea exactamente 36 — 100 menos 64.',
                },
                workedExample: {
                  code: 'edad = 20\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
                  output: '80',
                  explanation: 'Las mismas tres líneas de siempre — solo cambia el valor de edad. Fíjate en el patrón, no copies el número: el tuyo es 64, y el resultado 36.',
                },
                resultExplanation: 'Desde cero, las mismas tres líneas de siempre (crear edad, calcular con 100 - edad, mostrar con print) volvieron a funcionar — 100 menos 64 es 36, y eso es justo lo que apareció.',
                solutionCode: 'edad = 64\nfaltan_para_100 = 100 - edad\nprint(faltan_para_100)',
              },
            },
          },
        },
      },
    },
  },
  decision: {
    question: 'Ya sabes crear y leer variables — y por qué eso te ahorra reescribir un programa entero. ¿Cómo quieres consolidarlo?',
    reinforcements: [
      {
        kind: 'reto',
        label: 'Resolver un reto rápido',
        title: 'Reto: el contador de recorridos del robot',
        body: ['Misma regla: crea la caja, guarda el valor, y solo entonces úsalo. Ahora en vez de ordenar los pasos, predice qué muestra la pantalla.'],
        // Multimodalidad profunda (jul 2026): mismo concepto (contador de
        // recorridos) que antes se practicaba ordenando pasos, ahora exige
        // simular mentalmente la ejecución — una mecánica de interacción
        // genuinamente distinta, no el mismo ejercicio con otro disfraz.
        practice: {
          kind: 'predict_output',
          prompt: '¿Qué imprime este código?',
          code: 'recorridos = 0\nrecorridos = recorridos + 10\nprint(recorridos)',
          options: [
            { id: 'a', text: '0' },
            { id: 'b', text: '10' },
            { id: 'c', text: 'recorridos' },
            { id: 'd', text: 'Error' },
          ],
          correctOptionId: 'b',
          successFeedback: 'Exacto — «recorridos» empezó en 0, pero «recorridos = recorridos + 10» lo actualizó antes del print().',
          wrongFeedback: 'Revisa: print(recorridos) muestra lo que HAY en la caja en ESE momento, no su valor inicial.',
          solutionExplanation: [
            'Línea 1: recorridos = 0 — crea la caja con el valor 0.',
            'Línea 2: recorridos = recorridos + 10 — lee el 0 que había, le suma 10, y guarda 10 en la misma caja.',
            'Línea 3: print(recorridos) — muestra lo que hay AHORA en la caja: 10, no el 0 inicial.',
          ],
        },
      },
      {
        kind: 'ejemplo',
        label: 'Ver un ejemplo más',
        title: 'Ejemplo: el nivel de batería del robot',
        medium: 'ejemplo_comentado',
        body: [
          'El robot no recalcula su batería revisando cada movimiento cada vez que lo consultas: guarda un número — bateria — y lo actualiza cada vez que se mueve o se recarga.',
          '«bateria = 50» crea la variable. «bateria = bateria - 12» la actualiza: lee lo que tenía, resta 12, guarda el resultado con el mismo nombre.',
          'Tu turno: ordena los pasos que actualizan la batería después de un recorrido.',
        ],
        practice: {
          kind: 'ordering',
          prompt: 'Arma la secuencia que actualiza la batería del robot después de un recorrido. Descarta la que sea la meta.',
          items: [
            { id: 's1', text: 'Crea una caja llamada bateria', position: 1 },
            { id: 's2', text: 'Guarda el número 50 dentro de la caja bateria', position: 2 },
            { id: 's3', text: 'Resta 12 al valor guardado en bateria', position: 3 },
            {
              id: 'sd1',
              text: 'Revisa cuánta batería le queda',
              position: null,
              whyWrong: '«Revisa cuánta batería le queda» pregunta el resultado, no dice qué hacer con la caja bateria.',
            },
          ],
          successFeedback: 'Exacto — así se actualiza una batería real: sin perder el nombre de la variable en ningún paso.',
          orderFeedback: 'Restar de una batería vacía no tiene sentido: primero debe existir el valor guardado.',
          generalHint: 'Una de las frases pregunta el resultado, no dice qué hacer con la caja bateria.',
          solutionExplanation: [
            'Crear la caja, guardar 50, y solo después restar 12 — el mismo orden que necesita cualquier actualización de batería real.',
          ],
        },
        pythonBridge: {
          label: 'Esto ya es Python',
          code: 'bateria = 50\nbateria = bateria - 12\nprint(bateria)',
          explanation:
            '«bateria» aparece tres veces, y las tres son la MISMA caja: se crea, se lee para restar, y se vuelve a guardar con el nuevo valor. Por eso «bateria = bateria - 12» no es una ecuación matemática — es «toma lo que hay en bateria, réstale 12, y guarda el resultado ahí mismo».',
          practice: {
            prompt: 'Ahora hazlo tú: crea una variable combustible con el valor 25, réstale 5 que el robot gastó en la última tarea, y muestra el resultado con print()',
            starterCode: '# escribe tu código aquí\n',
            expectedOutput: '20',
            hint: 'Usa el operador - para restar: primero combustible = 25, después combustible = combustible - 5, y recién ahí print(combustible).',
            hintsByCategory: {
              sintaxis: 'Revisa el signo = y que no falte ningún paréntesis en print(combustible).',
              variables: 'Python no encuentra combustible porque nunca se creó con = antes de restarle el gasto.',
              logica: 'Revisa el orden: primero se crea combustible con 25, y solo después se le resta 5 — igual que hiciste con bateria.',
              salida: 'print(combustible) debe mostrar el número 20 — revisa que estés restando 5, no otro valor.',
            },
            workedExample: {
              code: 'recorridos = 100\nrecorridos = recorridos + 30\nprint(recorridos)',
              output: '130',
              explanation: 'El operador + suma en vez de restar, pero la mecánica es la misma: se lee lo que había en recorridos, se le suma 30, y se guarda el resultado en la misma caja. Tu ejercicio resta en vez de sumar.',
            },
            solutionCode: 'combustible = 25\ncombustible = combustible - 5\nprint(combustible)',
          },
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
        title: 'Óyelo de otro modo',
        medium: 'clip_narrado',
        narrationText:
          'Piensa en el compartimento con una sola etiqueta que ya conoces del robot. Cada vez que guardas algo nuevo, lo que había antes desaparece y queda lo nuevo — pero el compartimento sigue siendo el mismo, con la misma etiqueta. Una variable funciona igual: el nombre no cambia, lo que guarda sí. Y leer el nombre siempre te da el último valor que guardaste, nunca los anteriores.',
        body: [
          'Piensa en el compartimento con una sola etiqueta que ya conoces del robot. Cada vez que guardas algo nuevo, lo que había antes desaparece y queda lo nuevo — pero el compartimento sigue siendo el mismo, con la misma etiqueta.',
          'Una variable funciona igual: el nombre no cambia, lo que guarda sí. Y leer el nombre siempre te da el último valor que guardaste, nunca los anteriores.',
        ],
      },
    ],
  },

  // ── Escalera de remediación ──────────────────────────────────────────────
  remediation: {
    steps: [
      {
        level: 1,
        title: 'Repasemos la idea con un ejemplo ya resuelto',
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
        title: 'Otra forma de verlo, con más calma',
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
          // Auditoría "infografías" (jul 2026, segunda vuelta): ver misma
          // nota en ciclo1-instrucciones-precisas.ts — `imageAsset` ya está
          // listo para resolver contra illustrationAssets.ts.
          imageAsset: 'm1-c2-l2-caja-vacia',
          imagePrompt:
            'Diagrama jerárquico minimalista para una app educativa de programación, modo oscuro.\n\n' +
            'COMPOSICIÓN: un nodo superior centrado con forma de CAJA/CONTENEDOR abierto y vacío (la variable sin inicializar), del que bajan dos líneas conectoras en "Y" invertida hacia dos nodos inferiores: uno muestra la misma caja con una ETIQUETA/nombre pegada, el otro muestra la caja con un VALOR numérico dentro.\n\n' +
            'ESTILO: interfaz "glassmorphism" oscura, paneles translúcidos con bordes finos luminosos, sin fotorrealismo — formas geométricas simples (la caja es un icono de contenedor/cubo en outline, no una ilustración realista), coherente con un diagrama de flujo de producto SaaS.\n\n' +
            'COLORES: fondo casi negro #0a0a0f. Nodo superior (caja vacía): borde PUNTEADO ámbar #f59e0b, relleno ámbar al 8% de opacidad. Nodos inferiores (caja con nombre / caja con valor): borde SÓLIDO verde esmeralda #10b981, relleno esmeralda al 8%. Líneas conectoras gris translúcido rgba(255,255,255,0.15). Texto principal blanco hueso #f8fafc, texto secundario gris azulado #94a3b8. Acento cian #06b6d4 en la etiqueta de nombre del nodo izquierdo.\n\n' +
            'ICONOS: la caja vacía es un icono de contenedor/cubo abierto en outline. En el nodo izquierdo, un pequeño icono de etiqueta/tag junto a la caja. En el nodo derecho, un pequeño icono de "+" o número dentro de la caja para indicar contenido.\n\n' +
            'DISTRIBUCIÓN: formato vertical 4:5. Caja vacía ocupa ~20% de la altura, centrada arriba. Los dos nodos inferiores ocupan la mitad inferior, con amplio espacio en blanco entre ellos y respecto a los bordes.\n\n' +
            'ELEMENTOS DE TEXTO (incluir literalmente):\n' +
            '— Nodo superior: "CAJA VACÍA" + subtítulo pequeño "todavía no es una variable, no tiene nombre ni valor"\n' +
            '— Nodo inferior izquierdo: "Crea una caja llamada temperatura" + etiqueta pequeña "ahora tiene nombre"\n' +
            '— Nodo inferior derecho: "Guarda el número 18 dentro" + etiqueta pequeña "ahora tiene valor"\n' +
            '— Leyenda inferior centrada, fuera de los nodos: "Sin el nombre, no hay dónde guardar nada. Sin el valor, no hay nada que leer."',
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
          'Este concepto necesitó el máximo de apoyo, y eso también es información valiosa: le indica al sistema dónde reforzar contigo en el camino.',
          'Revisa la secuencia resuelta con calma — la misión sigue.',
        ],
      },
    ],
  },
  // Experience Recipe — Etapa 2 (jul 2026): la experiencia "lectora" de
  // Variables como UNA unidad (teoría + práctica), no piezas resueltas por
  // separado. Primera receta real del sistema — reutiliza exactamente el
  // mismo contenido que concept.variants.reading/practice.reading (ver los
  // const al inicio del archivo), nunca lo duplica. La prioridad de refuerzo
  // reutiliza los mismos valores que ya tenía REINFORCEMENT_BY_MODALITY.reading
  // en el Orchestrator (Etapa 1) — formalizada aquí, no reinventada.
  recipes: {
    reading: {
      concept: READING_CONCEPT_VARIANT,
      practice: READING_PRACTICE,
      reinforcementPriority: ['ejemplo', 'animacion', 'reto', 'audio'],
    },
  },
}
