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
| 1 — Estudiante nuevo | ⬜ | — | — | Pendiente (requiere usuario sin diagnóstico) |
| 2 — Estudiante existente | 🟩 | 0 | 4 | 2026-07-02 (navegador real, e2e) |
| 3 — Docente | ⬜ | — | — | Pendiente |
| 4 — Investigador | ⬜ | — | — | Pendiente |
| 5 — Administrador | ⬜ | — | — | Pendiente |

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

## Recorrido 1 — Estudiante nuevo (prioridad absoluta)

Pregunta única: **¿puede hacerlo sin romper nada?**

Las etapas compartidas con el Recorrido 2 (login, path, journey, completar,
dashboard, logout) ya están validadas 🟩. Falta validar con un usuario limpio:

| Etapa | Estado | Notas |
| --- | --- | --- |
| Onboarding | ⬜ | `/estudiante/onboarding` |
| Diagnóstico | ⬜ | `/estudiante/diagnostic/:courseId` (12 preguntas) |
| Perfil adaptativo generado | ⬜ | dominantModality detectada |
| Momento 1 (engage) en primer módulo | ⬜ | EngageGateway |

Plan: crear estudiante de prueba vía panel admin (valida de paso el Recorrido 5)
y recorrer desde cero.

---

## Recorrido 3 — Docente

Debe poder responder: ¿quién aprendió? · ¿quién está estancado? · ¿quién necesita ayuda?
Credenciales seed: docente@upao.edu.pe / Docente2026!

*(pendiente)*

---

## Recorrido 4 — Investigador

Adaptación, consenso, swarm y evidencia sin tocar la experiencia del estudiante.
Rutas: /investigador, /replay, /swarm-demo.

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

## Notas operativas

- Verificación válida: `npm run build` en `frontend/` (`rtk tsc` no usa el tsconfig del proyecto y da falsos "sin errores").
- Stack local: backend ya corre en :8000 (podman `upao_postgres` + uvicorn local); frontend `npm run dev` → :5173.
- Los fallos de clic vistos en automatización fueron artefactos de viewport (elemento fuera de pantalla), no bugs de usuario — verificado con `elementFromPoint` y clic real tras `scrollIntoView`.
