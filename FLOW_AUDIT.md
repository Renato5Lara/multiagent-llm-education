# FLOW_AUDIT.md — Auditoría de Recorridos

> Fase Final — modo Research Implementation.
> El objetivo de cada sesión de desarrollo es **reducir bloqueos y fricciones**,
> no añadir funcionalidades.
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

## Recorrido 4 — Modo Evidencia (antes "Investigador")

**Reorganización 2026-07-02:** el investigador dejó de existir como rol de
usuario; sus herramientas se conservan íntegras bajo el Modo Evidencia,
una capacidad de observabilidad del sistema accesible desde los sidebars
de admin/docente o directamente por URL.
Rutas: /evidencia (hub), /swarm-demo, /replay.

La pregunta que debe responder este recorrido no es "¿funciona el panel?"
sino: **¿puede el jurado observar cómo el sistema adaptó el aprendizaje
y por qué tomó esas decisiones?**

*(pendiente)*

---

## Recorrido 5 — Administrador

Mínimo: usuarios, módulos, estado del sistema, configuración.
Credenciales seed: admin@upao.edu.pe / Admin2026!

*(pendiente)*

---

## Registro de bloqueos corregidos

| Fecha | Severidad | Descripción | Fix |
| --- | --- | --- | --- |
| 2026-07-02 | Crítico | Build roto: `milestoneTimer`/`xpTimer` sin declarar + `useRef` tras early return en LearningJourney.tsx | `1a48d46` |
| 2026-07-02 | Crítico | Docente sin permiso para listar estudiantes → imposible inscribir → estudiante nuevo bloqueado en "Sin curso asignado" (C1, Recorrido 1) | `users.py` list_users: docente puede listar solo estudiantes |
| 2026-07-02 | Crítico | Analítica docente calculaba progreso sobre Resources (0 en cursos demo) → todos los estudiantes con 0% siempre; sin modalidad ni riesgo por estudiante (C2, Recorrido 3) | progreso desde `path_modules` en vivo + tabla de inscritos con modalidad/progreso/riesgo |

## Notas operativas

- Verificación válida: `npm run build` en `frontend/` (`rtk tsc` no usa el tsconfig del proyecto y da falsos "sin errores").
- Stack local: backend ya corre en :8000 (podman `upao_postgres` + uvicorn local); frontend `npm run dev` → :5173.
- Los fallos de clic vistos en automatización fueron artefactos de viewport (elemento fuera de pantalla), no bugs de usuario — verificado con `elementFromPoint` y clic real tras `scrollIntoView`. Reconfirmado en el Recorrido 1 (botón "Inscribir" y "Continuar" del Momento 1).
- Usuarios de prueba del Recorrido 1: `nuevo.r1@upao.edu.pe` (ciclo 3, diagnóstico completado, perfil Visual) y `sin.ciclo@upao.edu.pe` (onboarding completado, sin curso) — ambos `Recorrido2026!`.
- `POST /api/auth/login` usa el campo `identifier` (no `email`).
