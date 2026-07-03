# FLOW_AUDIT.md — Auditoría de Recorridos

> **Regla de Congelamiento (2026-07-02):** la metodología ya está definida
> (hipótesis, arquitectura, alcance, recorridos, reglas de desarrollo,
> documentos canónicos). No se modifica ningún documento metodológico
> (CLAUDE.md, FLOW_AUDIT.md, RESEARCH_ITERATIONS.md,
> THESIS_SCOPE_FREEZE.md, ROADMAP) salvo que sea **imprescindible para
> defender la tesis o para corregir una contradicción**. Toda idea nueva
> que no cambie el código de hoy va a "Backlog post-sustentación" (abajo),
> no a una ronda de documentación. El repo crece en código y en checks de
> este tablero, no en documentos nuevos.

> Fase Final — modo Research Implementation.
> El objetivo de cada sesión de desarrollo es **reducir bloqueos y fricciones**,
> no añadir funcionalidades.
>
> **Regla de Desarrollo:** no se desarrolla por pantalla, se desarrolla por
> recorrido completo. La pregunta de cada sesión es "¿qué impide que el actor
> complete todo el flujo?" (ver CLAUDE.md § Regla de Desarrollo).
>
> Severidad: **Crítico** = impide terminar el recorrido · **Medio** = el
> recorrido termina pero genera confusión · **Bajo** = solo estética.
> Estado: 🟩 Funcional · 🟨 Tiene fricciones · 🟥 Bloqueado · ⬜ Sin validar.

## Resumen

| Recorrido | Estado | Bloqueos críticos | Fricciones | Última validación |
| --- | --- | --- | --- | --- |
| 1 — Estudiante nuevo | 🟩 | 1 (corregido) | 3 | 2026-07-02 (navegador real, e2e) |
| 2 — Estudiante existente | 🟩 | 0 | 4 | 2026-07-02 (navegador real, e2e) |
| 3 — Docente | 🟩 | 1 (corregido) | 3 | 2026-07-02 (navegador real, e2e) |
| 4 — Modo Evidencia | ⬜ | — | — | Pendiente (reorganizado 2026-07-02: dejó de ser rol de usuario) |
| 5 — Administrador | ⬜ | — | — | Pendiente (crear usuario ya validado 2026-07-02) |

## Tablero Etapa 2 — Cierres de recorrido

> Regla de Cierre: un recorrido no está terminado hasta que un usuario real
> pueda completarlo de principio a fin sin intervención del desarrollador
> (navegador real, stack completo). Pregunta diaria: **¿qué recorrido vamos
> a cerrar hoy?** Criterio de producto demostrable: ¿puede cualquier jurado
> usarla de principio a fin sin encontrar un bloqueo?

**CONGELADO (solo errores críticos):** Momento 1 · Journey 5E · Banner de
adaptación · Modelo pedagógico · CodeLab integrado · Modo Evidencia ·
Arquitectura del Swarm.

**Etapa 3 — producto demostrable.** La pregunta ya no es "¿cómo mejoro la
plataforma?" sino **"¿puede cualquier jurado usarla de principio a fin sin
encontrar un bloqueo?"**. Prioridad de bloques: Bloque 1 Estudiante
(CERRADO) → Bloque 2 Docente (siguiente) → Bloque 3 Administrador (mínimo)
→ Bloque 4 Modo Evidencia (laboratorio de evidencia). No se trabaja fuera
de orden salvo bloqueo crítico en un recorrido ya cerrado. La iteración de
investigación 2.2 (RESEARCH_ITERATIONS.md) queda **pausada** hasta cerrar
estos tres bloques.

**Recorrido 1-2 — Estudiante** (Bloque 1 — CERRADO, prioridad máxima)

- ☑ Login · ☑ Registro · ☑ Onboarding · ☑ Diagnóstico · ☑ Ruta
- ☑ Momento 1 · ☑ Journey
- ☑ CodeLab · ☑ Evaluación · ☑ Resultados · ☑ Siguiente módulo

**ESTUDIANTE FUNCIONALMENTE CERRADO** — cierre e2e 2026-07-02 (ver acta
"Cierre del Recorrido 1"). El recorrido cumple el objetivo de
investigación; los defectos restantes (F1, F12, F13) no impiden
completarlo. Cuatro bloqueos corregidos en la sesión de cierre: E1
(Evaluación huérfana), F2 (doble experiencia de módulo), C3 (deadlock que
congelaba el backend) y E2 (paso Code Lab nunca se generaba).

**Recorrido 3 — Docente** (Bloque 2 — SIGUIENTE)

La auditoría funcional de 2026-07-02 (ver sección "Recorrido 3 — Docente"
abajo) cerró la carga de datos y las métricas (🟩 en el Resumen), pero
**no** el criterio de cierre real de este bloque. Criterio de cierre: el
jurado entra como docente y responde estas cinco preguntas mirando la
pantalla, **sin que nadie hable**:

- ⬜ ¿Quién necesita ayuda?
- ⬜ ¿Quién está aprendiendo rápido?
- ⬜ ¿Por qué el sistema adaptó distinto a cada estudiante?
- ⬜ ¿Qué debo hacer como docente?
- ⬜ ¿Qué evidencia tengo para confiar en esa recomendación? (score real,
  modalidad detectada, dificultad puntual — no "la IA lo dice")

Hasta que las cinco estén ☑ el bloque no se considera cerrado, aunque la
auditoría técnica lo esté. (Drift de numeración corregido 2026-07-02: esta
sección se numeraba "Recorrido 2" aquí y "Recorrido 3" en el Resumen —
ahora ambas usan 3.)

**Recorrido 5 — Administrador** (Bloque 3 — mínimo, deliberadamente pequeño)

No administra cursos ni contenidos — solo:

- ⬜ Usuarios · ⬜ Roles · ⬜ Activación/reinicio de cuentas · ⬜ Configuración institucional

**Recorrido 4 — Modo Evidencia** (Bloque 4 — laboratorio de evidencia)

No es un dashboard de observabilidad: es donde se defiende la tesis. Debe
responder, sin que nadie hable:

- ⬜ ¿Por qué este estudiante recibió esta ruta?
- ⬜ ¿Qué agentes participaron?
- ⬜ ¿Qué modalidad detectó?
- ⬜ ¿Qué evidencia produjo?
- ⬜ ¿Cómo evolucionó?

Cuando todos los ítems de un recorrido estén ☑ se marca **COMPLETADO** aquí
y se registra la validación en su sección de acta.

---

## Recorrido 2 — Estudiante existente ✅ 2026-07-02

Validado con navegador real (estudiante3@upao.edu.pe), stack completo local.

| Etapa | Estado | Notas |
| --- | --- | --- |
| Login | 🟩 | Redirige a /estudiante según rol |
| Dashboard | 🟩 | Ruta de aprendizaje visible, botón "Continuar aprendizaje" funciona |
| Learning Path | 🟩 | Misiones con estados correctos (completada/disponible/bloqueada) |
| Entrar a módulo (Misión 02) | 🟩 | Navega a ModuleLearningView |
| Learning Journey 5E (17 pasos) | 🟩 | Pills 5E + hilo conductor + StepContextTag + predicción + concepto + micro-preguntas + mini-actividad + reflexiones — todo interactuable y avanza |
| Completar módulo | 🟩 | Vuelve al path, Misión 02 → Completada, Misión 03 desbloqueada |
| Dashboard actualizado | 🟩 | Progreso 2/4 reflejado, módulo 3/4 habilitado |
| Logout | 🟩 | Menú de usuario → Cerrar sesión → /login |

### Fricciones encontradas

| # | Severidad | Descripción |
| --- | --- | --- |
| F1 | Medio | La reflexión final (Demuestra) muestra **markdown crudo truncado** como título ("# Estructuras Básicas… ## Cargado por. Título y descripción mejorados con IA… para la se"). El contenido de misconception/corrección llega sucio desde el backend/seed. |
| F2 | Medio | **Dos experiencias de módulo distintas** según el título: Misión 02 → journey 5E (pantalla estrella); Misión 03 "Funciones y módulos" → `/estudiante/learn/functions` (vista "Módulo Adaptativo" por orden de contenido, sin 5E ni hilo conductor). Incoherente para la narrativa ante el jurado. Causa: `detectTopicSlug()` en LearningPath desvía 4 temas al AdaptiveLearnView. |
| F3 | Bajo | Menú de usuario: ítem "Perfil" deshabilitado (elemento muerto visible). |
| F4 | Bajo | QUICK_COMMANDS.md tiene credenciales seed desactualizadas (`estudiante.c3@upao.edu/estudiante123` vs. reales `estudiante3@upao.edu.pe/Student2026!`). |

### Notas de diseño observadas funcionando (no tocar)

Banner Bloom + confianza, "¿Por qué veo esto?", TutorPresence, "Este módulo fue
preparado por 8 agentes de IA", "Debate entre agentes", overlay de transición de
fase, AdaptationEcho, milestones. XP acumulado visible (23 pts al cierre).

---

## Recorrido 1 — Estudiante nuevo ✅ 2026-07-02

Validado con navegador real y usuarios limpios creados vía panel admin
(`nuevo.r1@upao.edu.pe` con ciclo 3, `sin.ciclo@upao.edu.pe` sin ciclo,
ambos `Recorrido2026!`), stack completo local.

| Etapa | Estado | Notas |
| --- | --- | --- |
| Crear usuario (panel admin) | 🟩 | Formulario "Nuevo usuario" crea estudiante; aparece en tabla (valida parte del Recorrido 5) |
| Inscripción al curso (panel docente) | 🟩 | Curso IS301 → tab Estudiantes → checkbox → "Inscribir" (tras corregir C1; valida parte del Recorrido 3) |
| Onboarding | 🟩 | Solo aparece si el usuario no tiene ciclo (AcademicGuard). Bienvenida → selección de ciclo → "¡Ciclo asignado exitosamente!" → dashboard |
| Dashboard sin diagnóstico | 🟩 | Tarjeta IS301 con checklist (Diagnóstico/Ruta/Tutor) y una sola acción: "Comenzar diagnóstico" |
| Diagnóstico | 🟩 | 18 preguntas en 2 partes (8 conocimiento + 10 modalidad), Likert emoji con auto-avance, intersticial "Parte 1 completada" |
| Perfil adaptativo generado | 🟩 | Respuestas sesgadas a visual → badge "Perfil Visual" en la ruta + "Cómo aprenderás mejor" (diagramas, orden Teoría→Ejemplo→Diagrama→Video, introducción reforzada) |
| Ruta de aprendizaje | 🟩 | 4 misiones, Misión 01 "Fundamentos de Python" disponible |
| Momento 1 (EngageGateway) | 🟩 | ¿Sabías que...? narrativo con fuente/evidencia → pregunta detonante → hipótesis del estudiante + confianza → "Hipótesis registrada, guardada para el cierre del módulo" |
| Pantalla swarm ("Preparando tu experiencia") | 🟩 | Barras de progreso por agente + comunicación entre agentes |
| Journey 5E | 🟩 | Banner Bloom·Recordar + 65% conf., "¿Por qué veo esto?", TutorPresence, pills 5E, hilo conductor, 19 pasos; micro-pregunta interactiva verificada (resto ya validado en Recorrido 2) |

### Bloqueo crítico corregido

| # | Severidad | Descripción | Fix |
| --- | --- | --- | --- |
| C1 | Crítico | El docente no podía inscribir estudiantes: la sección "Inscribir nuevos estudiantes" quedaba en "Cargando estudiantes..." para siempre porque `GET /api/users?role=estudiante` era solo-admin (403). Sin inscripción, un estudiante nuevo ve "Sin curso asignado" y el recorrido muere en la primera pantalla. | `backend/app/api/routes/users.py`: `list_users` ahora permite a rol docente listar **solo** estudiantes; el resto sigue siendo admin-only. Verificado e2e + `tests/test_users.py` 13/13 |

### Fricciones encontradas

| # | Severidad | Descripción |
| --- | --- | --- |
| F5 | Medio | `CourseDetail` (docente): si la carga de candidatos falla, muestra "Cargando estudiantes..." indefinidamente en vez de un estado de error. El 403 fue invisible para el usuario. |
| F6 | Bajo | Overlay de transición post-swarm muestra "PERFIL: Adaptativa" (valor genérico) en lugar de la modalidad detectada ("Visual"). El banner del journey sí es correcto. Componente CONGELADO — no tocar sin aprobación. |
| F7 | Bajo | Warnings de React en consola: botón anidado en botón y prop `asChild` sin resolver (panel admin), `DialogContent` sin descripción aria. Cosmético. |

### Drift preexistente registrado (no tocado)

`tests/test_enrollment_lifecycle.py`: 10 tests fallan con y sin los cambios de
esta sesión — esperan `PENDING_ACTIVATION` + eventos + `educational_context`,
pero `enroll` crea la matrícula directamente en `ACTIVO`. Decidir en una sesión
futura si se actualizan los tests al comportamiento actual o viceversa.

---

## Recorrido 3 — Docente ✅ 2026-07-02

Debe poder responder: ¿quién aprendió? · ¿quién está estancado? · ¿quién necesita ayuda?
Credenciales seed: docente@upao.edu.pe / Docente2026!

| Etapa | Estado | Notas |
| --- | --- | --- |
| Login → /docente | 🟩 | Redirige según rol |
| Dashboard docente | 🟩 | Carga sin errores (ver F8/F9 abajo) |
| Curso IS301 → tab Estudiantes | 🟩 | Tabla ahora responde el recorrido: nombre · email · código · **Modalidad detectada** (badge, "Sin diagnóstico" si falta) · **Progreso** (X/Y misiones + badge "En riesgo" si <30%) · estado |
| Inscribir estudiantes | 🟩 | Validado en Recorrido 1 (fix C1); F5 corregida: error visible si la carga de candidatos falla |
| Analítica IA | 🟩 | IS301 con progreso real (25%), 1 en riesgo, recomendación accionable por curso; alertas generales con datos reales |
| Comparación Swarm | 🟩 | Carga sin errores; estado vacío honesto ("No hay sesiones de replay") — las sesiones se generan al ejecutar orquestaciones (ver Recorrido 4) |

### Bloqueo crítico corregido

| # | Severidad | Descripción | Fix |
| --- | --- | --- | --- |
| C2 | Crítico | El docente no podía responder ninguna de sus tres preguntas: la analítica calculaba progreso sobre `Resource`+`StudentProgress`, pero el flujo real del estudiante avanza por `PathModule` y los cursos demo tienen 0 Resources → **todo estudiante aparecía con 0% de progreso para siempre** (Maria con 2/4 misiones completadas mostraba 0%). Además la tabla de inscritos no mostraba progreso ni modalidad. | `prerequisite_service.get_course_analytics_batched`: progreso desde `path_modules` en vivo (fallback a recursos); `course_service.get_enrolled_students` + `EnrolledStudentResponse` enriquecidos con modalidad del diagnóstico y progreso de ruta; columnas Modalidad/Progreso en la tabla existente de `CourseDetail`. Verificado e2e: Maria → Lectura · 2/4; Nuevo → Visual · 0/4 · En riesgo; analítica IS301 → 25%, 1 en riesgo |

### Fricciones corregidas

- **F5** (del Recorrido 1): la carga de candidatos ahora muestra error visible en vez de spinner infinito.
- **F8 (Medio→corregida):** títulos de página (`PageHeader`) invisibles en todo el panel docente/admin — `text-gray-900` sobre fondo oscuro (resto de tema claro). Ahora `text-neural-text`.
- Contador `learning_paths.completed_modules` desincronizado (Maria: 1 vs 2 reales; anomalía histórica de un code path antiguo, los writers actuales sí recomputan) — dato corregido en BD; la analítica ya no depende del contador (cuenta en vivo).
- Concordancia "1 estudiantes en riesgo" → singular/plural en `analytics_service`.

### Fricciones abiertas

| # | Severidad | Descripción |
| --- | --- | --- |
| F9 | Medio | Dashboard docente y Analítica muestran los **44 cursos de la malla** (10 ciclos); IS301 se pierde entre tarjetas con 0 inscritos. Coherencia con la narrativa no-LMS. Reducir el foco requiere decisión de alcance — no se tocó. |
| F10 | Bajo | Restos de tema claro en tarjetas/estadísticas y tabs del panel docente (fondos blancos `bg-blue-50`, `bg-green-50`, etc. sobre estética neural dark). Cosmético. |
| F11 | Bajo | Otro estudiante seed aparece "en riesgo" en Matemática Discreta (curso fuera del scope de tesis) e infla los KPIs globales (En Riesgo 7 · Tasa 54%). Consecuencia de F9/seed, no del código. |

---

## Cierre del Recorrido 1 — tramo final ✅ 2026-07-02

**Recorrido 1 funcionalmente cerrado.** El recorrido cumple el objetivo de
investigación y los defectos restantes no impiden completarlo.

**Objetivo de la sesión:** un estudiante nuevo puede completar desde la ruta
personalizada hasta la pantalla de resultados sin intervención del
desarrollador. **Cumplido.**

Validado en navegador real con: `estudiante3@upao.edu.pe` (María, llegó a
4/4 · 100% · 200 pts), `kines.r1@upao.edu.pe` y `kines.r2@upao.edu.pe`
(nuevos, perfil **kinestésico** detectado con 80% conf., creados vía panel
admin + inscritos vía docente). Contraseña de los nuevos: `Recorrido2026!`.

| Etapa | Estado | Evidencia |
| --- | --- | --- |
| Ruta → Evaluación | 🟩 | Tarjeta "Demuestra lo aprendido" visible con ≥1 misión completada |
| Evaluación → Resultados | 🟩 | Pregunta adaptada al módulo activo → "¡Aprobado! 1/1" → botón "Volver a la ruta" |
| Resultados → Siguiente módulo | 🟩 | Aprobar completa la misión activa y desbloquea la siguiente (por diseño) |
| Journey → Code Lab | 🟩 | Estudiante kinestésico: paso "Práctica en Code Lab: Funciones y módulos" en fase Practica → `/estudiante/codelab/functions` → desafío de bloques resuelto → "¡Desafíos completados!" → vuelve a la misión |
| Una sola experiencia de módulo | 🟩 | Toda misión entra por el Journey 5E (Momento 1 → pills → completar) |

### Bloqueos corregidos en esta sesión

| # | Severidad | Descripción | Fix |
| --- | --- | --- | --- |
| E1 | Crítico | La Evaluación (`/estudiante/evaluation/:courseId`, completa con score y resultados) era **inalcanzable**: ninguna pantalla navegaba a ella. | Tarjeta "Evaluación · Demuestra lo aprendido" en `LearningPath.tsx`, visible al completar ≥1 misión. |
| F2 | Medio | Dos experiencias de módulo según el título: 4 temas se desviaban a `AdaptiveLearnView` (sin 5E). | Eliminado `detectTopicSlug()`; toda misión entra por `/estudiante/module/:id` (Journey 5E). |
| C3 | Crítico | Orquestar "Funciones y módulos" **congelaba todo el backend** (ni /health respondía): `publish_observation_sync` (shared_memory.py) hace un INSERT síncrono sobre el event loop; con dos orquestaciones concurrentes del mismo módulo (doble efecto React en dev) la espera del lock de fila bloqueaba el loop → deadlock; el `asyncio.wait_for(60s)` nunca dispara sobre código síncrono. Diagnóstico por `py-spy dump`. | `research_agent.analyze`: `_publish_memory` ahora corre en `asyncio.to_thread` — la espera del lock ya no bloquea el loop; la primera orquestación termina y libera. Verificado: orquestaciones sucesivas y concurrentes sin congelamiento. |
| E2 | Crítico | El paso "Práctica en Code Lab" **nunca se generaba para ningún estudiante**, por dos capas: (a) `codeLabSelector.ts` buscaba fragmentos semánticos en el `module_id`, que es un UUID — match imposible; (b) `ModuleLearningView` pasaba al builder como `dominantModality` la modalidad del primer *prompt de medios* (`image`/`video`/`audio`), nunca la del aprendiz, así que la puerta `=== 'kinesthetic'` (matriz modalidad×fase congelada) jamás abría. | (a) el selector matchea palabras clave en id+título (es/en); (b) `ModuleLearningView` obtiene la modalidad real del aprendiz de `useLearningPath(courseId).dominant_modality` y la pasa al builder y al overlay de fase (esto además corrige F6: el overlay ya recibe la modalidad detectada, no "Adaptativa"). |

### Fricciones nuevas (no bloquean)

| # | Severidad | Descripción |
| --- | --- | --- |
| F12 | Bajo | Toast del docente: "1 estudiantes inscritos" (concordancia singular/plural, punto distinto al ya corregido en analytics). |
| F13 | Medio | Salir del Journey hacia Code Lab y volver **reinicia el journey desde el paso 1** (el progreso de pasos no se persiste al desmontar). El estudiante puede re-avanzar, pero es fricción notable para la demo. |

### Nota metodológica

La validación fue con navegador real y gestos de usuario (clics, scroll,
drag & drop en Code Lab, formularios). El comportamiento "aprobar la
evaluación completa la misión activa" es de diseño (backend
`evaluation_service`) y encaja con el flujo canónico Evaluación →
Resultados → Siguiente módulo. Los journeys varían de 14 a 19 pasos según
la orquestación — variabilidad esperada del swarm.

---

## Recorrido 4 — Modo Evidencia (antes "Investigador")

**Reorganización 2026-07-02:** el investigador dejó de existir como rol de
usuario; sus herramientas se conservan íntegras bajo el Modo Evidencia,
una capacidad de observabilidad del sistema accesible desde los sidebars
de admin/docente o directamente por URL.
Rutas: /evidencia (hub), /swarm-demo, /replay.

La pregunta que debe responder este recorrido no es "¿funciona el panel?"
sino: **¿puede el jurado observar cómo el sistema adaptó el aprendizaje
y por qué tomó esas decisiones?** Contrato de cierre (5 preguntas, sin que
nadie hable): ¿por qué este estudiante recibió esta ruta? · ¿qué agentes
participaron? · ¿qué modalidad detectó? · ¿qué evidencia produjo? · ¿cómo
evolucionó?

*(pendiente — Bloque 4, después de Docente y Administrador)*

---

## Recorrido 5 — Administrador

Alcance mínimo y deliberado (Bloque 3): usuarios, roles,
activación/reinicio de cuentas, configuración institucional. No administra
cursos ni contenidos — eso vive en el recorrido Docente.
Credenciales seed: admin@upao.edu.pe / Admin2026!

*(pendiente — Bloque 3, después de Docente)*

---

## Registro de bloqueos corregidos

| Fecha | Severidad | Descripción | Fix |
| --- | --- | --- | --- |
| 2026-07-02 | Crítico | Build roto: `milestoneTimer`/`xpTimer` sin declarar + `useRef` tras early return en LearningJourney.tsx | `1a48d46` |
| 2026-07-02 | Crítico | Docente sin permiso para listar estudiantes → imposible inscribir → estudiante nuevo bloqueado en "Sin curso asignado" (C1, Recorrido 1) | `users.py` list_users: docente puede listar solo estudiantes |
| 2026-07-02 | Crítico | Analítica docente calculaba progreso sobre Resources (0 en cursos demo) → todos los estudiantes con 0% siempre; sin modalidad ni riesgo por estudiante (C2, Recorrido 3) | progreso desde `path_modules` en vivo + tabla de inscritos con modalidad/progreso/riesgo |
| 2026-07-02 | Crítico | Evaluación inalcanzable: ninguna pantalla navegaba a `/estudiante/evaluation` (E1, cierre R1) | tarjeta de evaluación en `LearningPath.tsx` |
| 2026-07-02 | Medio | Doble experiencia de módulo: 4 temas desviados a la vista sin 5E (F2, cierre R1) | eliminado `detectTopicSlug()`; todo entra por el Journey |
| 2026-07-02 | Crítico | Backend entero congelado al orquestar con concurrencia: INSERT síncrono de memoria compartida sobre el event loop → deadlock con el lock de fila (C3, cierre R1) | `_publish_memory` vía `asyncio.to_thread` en `research_agent.py` |
| 2026-07-02 | Crítico | Paso Code Lab nunca generado: selector sobre UUID + modalidad de medios confundida con modalidad del aprendiz (E2, cierre R1) | selector por título + `dominant_modality` del learning path en `ModuleLearningView` |

## Notas operativas

- Verificación válida: `npm run build` en `frontend/` (`rtk tsc` no usa el tsconfig del proyecto y da falsos "sin errores").
- Stack local: backend ya corre en :8000 (podman `upao_postgres` + uvicorn local); frontend `npm run dev` → :5173.
- Los fallos de clic vistos en automatización fueron artefactos de viewport (elemento fuera de pantalla), no bugs de usuario — verificado con `elementFromPoint` y clic real tras `scrollIntoView`. Reconfirmado en el Recorrido 1 (botón "Inscribir" y "Continuar" del Momento 1).
- Usuarios de prueba del Recorrido 1: `nuevo.r1@upao.edu.pe` (ciclo 3, diagnóstico completado, perfil Visual) y `sin.ciclo@upao.edu.pe` (onboarding completado, sin curso) — ambos `Recorrido2026!`.
- `POST /api/auth/login` usa el campo `identifier` (no `email`).

## Backlog post-sustentación

> Ideas válidas que NO cambian el código de hoy. Se anotan aquí y se
> siguen — no generan discusión de metodología ni edición de otros
> documentos hasta después de cerrar los Bloques 2-4.

*(vacío)*
