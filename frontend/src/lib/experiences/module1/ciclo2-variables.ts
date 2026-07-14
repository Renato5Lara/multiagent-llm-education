// Módulo 1 · Ciclo 2 — Variables.
// Extraído de module1.ts (refactor mecánico, sin cambio de comportamiento).

import type { LearningCycle } from '@/types/moduleExperience'

export const CICLO_2_VARIABLES: LearningCycle = {
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
          practice: {
            prompt: 'Ahora hazlo tú: crea una variable precio con el valor 25, réstale un descuento de 5, y muestra el resultado con print()',
            starterCode: '# escribe tu código aquí\n',
            expectedOutput: '20',
            hint: 'Usa el operador - para restar: primero precio = 25, después precio = precio - 5, y recién ahí print(precio).',
            hintsByCategory: {
              sintaxis: 'Revisa el signo = y que no falte ningún paréntesis en print(precio).',
              variables: 'Python no encuentra precio porque nunca se creó con = antes de restarle el descuento.',
              logica: 'Revisa el orden: primero se crea precio con 25, y solo después se le resta 5 — igual que hiciste con saldo.',
              salida: 'print(precio) debe mostrar el número 20 — revisa que estés restando 5, no otro valor.',
            },
            workedExample: {
              code: 'puntos = 100\npuntos = puntos + 30\nprint(puntos)',
              output: '130',
              explanation: 'El operador + suma en vez de restar, pero la mecánica es la misma: se lee lo que había en puntos, se le suma 30, y se guarda el resultado en la misma caja. Tu ejercicio resta en vez de sumar.',
            },
            solutionCode: 'precio = 25\nprecio = precio - 5\nprint(precio)',
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
}
