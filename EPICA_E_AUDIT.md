# Épica E — Auditoría previa (sin código, sin rama)

> Responde las dos preguntas planteadas antes de escribir una sola
> línea de la Épica E. Punto de partida: tag `epica-d-complete`
> (`e5306aa`). Metodología: lectura directa de backend + frontend,
> `grep` dirigido, nunca supuesto.

---

## Pregunta 1 — ¿Qué porcentaje del flujo de Post-Test ya está implementado?

**Mucho más de lo esperado. Esto no es un "construir desde cero", es
un "terminar de exponer lo que ya existe".**

### Ya implementado y funcionando (backend)

| Pieza | Estado | Dónde |
|---|---|---|
| Generación del post-test | ✅ | `knowledge_test_service.start_attempt` (reutiliza el mismo banco, `kind="post"`) |
| Almacenamiento de respuestas | ✅ | `KnowledgeTestAnswer`, `submit_attempt` |
| Cálculo de puntaje/nivel | ✅ | `percentage`, `score`, `level`, `module_breakdown` |
| Comparación Pre vs Post | ✅ | Tabla `ExperimentResult` + `compute_experiment_result` — calcula `absolute_gain`, `percent_gain`, `normalized_gain`, `pre_level`/`post_level`, `pre_duration_seconds`/`post_duration_seconds` |
| Persistencia en BD | ✅ | `ExperimentResult` (upsert, no se recalcula desde cero cada vez) |
| Endpoint de comparación | ✅ | `GET /{course_id}/comparison` → `ExperimentComparisonOut` (9 campos) |
| Visualización de resultado | ✅ (parcial) | `KnowledgeTest.tsx` `ResultScreen` — pantalla real con tarjeta de comparación |

### Brechas reales encontradas (concretas, no genéricas)

1. **La tarjeta de comparación en el frontend solo muestra 3 de los 9
   campos que el backend ya calcula y expone**: `pre_percentage`,
   `post_percentage`, `absolute_gain`. Nunca se muestran
   `percent_gain`, `normalized_gain`, `pre_duration_seconds`/
   `post_duration_seconds`, `pre_level`/`post_level`. El dato ya
   existe — es un problema de exposición en la UI, no de cálculo.
   (`KnowledgeTest.tsx` línea ~676-701)

2. **La recomendación del Tutor IA ya se calcula para el post-test,
   pero nunca se muestra.** `compute_competency_profile` (que produce
   `competency_profile.recommendation`, un texto tipo "Tu fortaleza es
   X, tu ruta comenzará por Y") se ejecuta sin distinguir `pre`/`post`
   — el backend lo devuelve igual en ambos casos. El frontend, sin
   embargo, **solo renderiza `competency_profile.recommendation`
   cuando `kind === 'pre'`** (línea 202); en el resultado del
   post-test ese texto nunca aparece.
   **Matiz importante:** el texto actual está redactado para el
   contexto de PRE-test ("tu ruta empezará por…", "tu ruta comenzará
   reforzando…") — mostrarlo tal cual después del post-test sería
   incoherente (el estudiante ya no va a "empezar" una ruta). EP-01
   necesita una función de recomendación con redacción propia para
   `post`, no solo destapar el mismo componente.

3. **"Tiempo invertido" y "misiones completadas" del wishlist no
   están en esta pantalla.** `pre_duration_seconds`/
   `post_duration_seconds` ya existen en el backend (ver punto 1);
   "misiones completadas" vive hoy solo en el Dashboard — decisión de
   alcance pendiente: ¿se duplica aquí o se enlaza desde ahí?

4. **Integración con el motor adaptativo:** el pre-test SÍ alimenta
   el Runtime (`registrar_evidencia_evaluacion`, línea 337). El
   post-test **deliberadamente no lo hace** — solo materializa
   `ExperimentResult` (línea 330-334). Esto es coherente con el
   propósito del post-test (medir el resultado del experimento, no
   disparar más adaptación sobre un recorrido que ya terminó) — **no
   es una brecha, es una decisión de diseño ya vigente**; se cita
   aquí para que EP-01 no la reabra sin querer.

### Conclusión Pregunta 1

El post-test **funciona de punta a punta hoy** (un estudiante puede
rendirlo y ver un resultado real). Lo que falta es exclusivamente
**enriquecer la pantalla de resultado** con datos que el backend ya
tiene, más una recomendación del tutor con redacción propia para
post-test. Alcance mucho más chico y de mucho menor riesgo que
"construir el Post-Test" — es "terminar de mostrar el Post-Test".

---

## Pregunta 2 — ¿Qué pantallas no adoptaron el Design System de Épica D?

### Hallazgo específico: el bug real de "fondo blanco, texto blanco"

Localizado con precisión — **no es una inconsistencia difusa, son 2
componentes primitivos compartidos**:

- **`components/ui/tabs.tsx`** (línea 79): la pestaña activa usa
  `bg-white text-foreground`. `--foreground` en modo oscuro vale
  `233 20% 90%` (un color CLARO, pensado para texto sobre fondo
  oscuro). Resultado: **fondo blanco + texto casi blanco → la
  etiqueta de la pestaña activa es invisible**. Coincide exactamente
  con el síntoma reportado. Alcanza `pages/admin/Users.tsx` (Admin) y
  también `docente/WeeklyPedagogicalPlanner.tsx` y
  `estudiante/StudentWeeklyLearningView.tsx` — mismo bug, 3 pantallas,
  una sola causa raíz.
- **`components/ui/dropdown-menu.tsx`** (línea 111): panel `bg-white`
  con ítems en `text-gray-700`/`text-gray-900` (explícito, no
  `text-foreground`) — **este SÍ es legible**, pero es un menú
  desplegable con estética de tema claro apareciendo sobre una
  aplicación 100% oscura — inconsistencia visual real, no invisible.
  Alcanza `UserDropdown.tsx` (el menú de cuenta del header, presente
  en TODAS las pantallas autenticadas, incluyendo Admin).
- **`components/ui/toaster.tsx`** (línea 17): mismo patrón que el
  dropdown — `bg-white border-gray-200 text-gray-900`, legible pero
  fuera de tema. Cualquier notificación toast del sistema completo
  aparece como un recuadro claro.

**Tutor:** revisé `TutorWidget.tsx`, `TutorInsightsPanel.tsx` y
`TutorPresence.tsx` directamente — **los tres ya usan los tokens del
Design System correctamente, sin `bg-white` ni colores hardcodeados**.
Lo que probablemente se percibe como "el Tutor se ve roto" es el
toaster/dropdown de arriba apareciendo ENCIMA de la UI del tutor
(ambos son overlays globales, no parte del componente del tutor en
sí) — no un problema del propio Tutor.

**Conclusión práctica:** arreglar 2 archivos (`tabs.tsx`,
`dropdown-menu.tsx`) resuelve el bug de invisibilidad en Admin,
Docente y Estudiante a la vez (son primitivos compartidos). Arreglar
`toaster.tsx` de paso resuelve la inconsistencia visual del toast en
toda la plataforma. **3 archivos, no una auditoría por rol.**

### El hallazgo grande: un sistema visual paralelo, mucho más amplio

Además de los 3 primitivos, hay **~60 archivos con `bg-white` sólido**
(no las variantes `bg-white/[0.0X]`, que son overlays de vidrio
legítimos ya usados en el Design System) concentrados casi
enteramente en:

- `components/swarm/*` (24 archivos)
- `components/observability/*` (7 archivos)
- `components/module/*`, `components/learningJourney/*`,
  `components/engage/*` (el sistema de fallback para los 7 módulos
  sin `ModuleExperienceDefinition`, ya identificado como fuera de
  alcance durante Épica D)

Estos NO están confinados a Modo Evidencia: páginas reales del flujo
de estudiante los importan (`DiagnosticTest.tsx`, `Evaluation.tsx`,
`KnowledgeTest.tsx`, `LearningPath.tsx`, `ModuleLearningView.tsx` —
vía `AgentActivityPanel` durante la deliberación del swarm al generar
la ruta). Es decir: **el mismo estudiante que ya vive en la UI oscura
de Épica D puede toparse con una tarjeta de deliberación en tema
claro** en momentos puntuales (generar ruta, ver resultado). Esto es
mucho más grande que "Admin y Tutor" — es una segunda identidad
visual completa, preexistente a Épica D, coexistiendo con la nueva.

### Login

`pages/Login.tsx`: el único `bg-white` real es un overlay de hover al
0-20% de opacidad (efecto de brillo, no un fondo sólido) — **no es un
bug**. Login ya está en tema oscuro.

---

## Recomendación de alcance para Épica E (a confirmar con el tesista)

Dado lo encontrado, propondría dividir distinto a lo esbozado
originalmente — no por desacuerdo con el objetivo, sino porque la
auditoría cambia dónde está el riesgo real:

- **EP-01 — Enriquecer el resultado del Post-Test** (bajo riesgo,
  alto valor de tesis): mostrar los 6 campos ya calculados que faltan
  + recomendación del tutor con redacción propia para post-test.
  Ningún cambio de backend necesario salvo, quizás, una función de
  recomendación nueva para `kind="post"`.
- **EP-02 — Fix de los 3 primitivos compartidos** (`tabs.tsx`,
  `dropdown-menu.tsx`, `toaster.tsx`): resuelve el bug de
  invisibilidad reportado en Admin/Docente/Estudiante de una sola vez.
  Muy acotado, build+QA rápido.
- **EP-03 — Decisión sobre el sistema visual paralelo** (`swarm/`,
  `observability/`, y los ya conocidos `module/`/`learningJourney/`/
  `engage/`): esto es demasiado grande para "una auditoría visual
  más" — antes de tocar código haría falta decidir SI se migra (~60
  archivos, varias semanas) o si se acota su alcance real (¿siguen
  vivos todos, o algunos ya son código muerto de una iteración
  anterior del proyecto?). Recomendaría una sub-auditoría de
  alcance/vida útil antes de comprometer trabajo aquí — candidato a
  quedar fuera de Épica E y convertirse en su propia épica futura.

No creé ninguna rama todavía — quedo a la espera de que confirmes el
alcance antes de abrir `feature/epica-e-...`.
