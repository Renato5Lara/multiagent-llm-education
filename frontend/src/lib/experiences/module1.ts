// Módulo 1 · "El idioma de las máquinas" — instancia del Patrón de Experiencia.
// Contenido según la referencia funcional congelada (jul 2026).
// S1 incremento 1: apertura de curiosidad + Ciclo 1 (Instrucciones precisas).
// Los ciclos 2-3 y el reto integrador entran en los siguientes incrementos.

import type { ModuleExperienceDefinition } from '@/types/moduleExperience'
import { CICLO_1_INSTRUCCIONES_PRECISAS } from './module1/ciclo1-instrucciones-precisas'
import { CICLO_2_VARIABLES } from './module1/ciclo2-variables'

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

  cycles: [CICLO_1_INSTRUCCIONES_PRECISAS, CICLO_2_VARIABLES],

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
