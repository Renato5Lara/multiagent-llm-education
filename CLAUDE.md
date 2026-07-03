# CLAUDE.md — Autonomous Development Rules
# UPAO Multiagent LLM Education System

> READ FIRST: THESIS_SCOPE_FREEZE.md antes de cualquier implementación.
> READ SECOND: ROADMAP_THESIS_FOCUS.md para contexto de sprints.
> READ THIRD: RESEARCH_ITERATIONS.md — metodología y estado de las iteraciones de investigación.

---

## PRINCIPIO FUNDAMENTAL

**Optimizar para completar la tesis, no para expandir el producto.**

La pregunta obligatoria antes de cualquier implementación:

> ¿Esta funcionalidad ayuda a demostrar la adaptación multimodal en Fundamentos de la Programación?

Si la respuesta es NO: **no implementar.**

---

## METODOLOGÍA DE INVESTIGACIÓN (Fase 2+)

**Regla maestra — obliga a toda IA que trabaje en este proyecto (Claude, Antigravity, ChatGPT):**

> Ninguna funcionalidad nueva se implementa si antes no puede justificarse
> como evidencia de la hipótesis de investigación.

El trabajo se organiza en **Iteraciones de Investigación** (no "sprints").
Cada iteración responde UNA pregunta de investigación observable y produce
DOS entregables: el cambio en la plataforma + su documentación de
investigación en RESEARCH_ITERATIONS.md.

Antes de implementar cualquier cambio, responder obligatoriamente:

1. ¿Qué pregunta de investigación responde?
2. ¿Qué parte de la hipótesis fortalece?
3. ¿Qué variable afecta?
4. ¿Cómo se observará durante la demo?
5. ¿Cómo aparecerá luego en Resultados y Discusión?

Si no puede responder las cinco: **no se implementa.**

Los componentes marcados CONGELADO en RESEARCH_ITERATIONS.md no se
modifican salvo error crítico. "Tengo una idea mejor" no es razón válida.

---

## RESTRICCIONES DURAS

**Nunca introducir funcionalidades fuera de:**

- Asignatura Fundamentos de la Programación
- Aprendizaje adaptativo
- Sistema multiagente
- Inteligencia de enjambre
- Demostración de investigación

---

## NO IMPLEMENTAR NUNCA

- LMS universitario completo
- Soporte multi-asignatura activo
- Gestión curricular institucional
- Administración académica avanzada
- Prerrequisitos complejos entre carreras
- Analítica institucional
- Funcionalidades sin relación directa con la hipótesis de tesis

---

## AUTORIDAD AUTÓNOMA

Claude PUEDE sin pedir confirmación:

- Refactorizar componentes existentes
- Rediseñar UI/UX para mejorar claridad
- Mover o reorganizar componentes
- Simplificar flujos complejos
- Eliminar complejidad innecesaria
- Crear mocks y datos de demo
- Mejorar jerarquía visual
- Aplicar polish de diseño (espacio, tipografía, color)
- Corregir bugs
- Optimizar rendimiento
- Mejorar explicabilidad del sistema

Claude NO PUEDE sin confirmación explícita:

- Expandir el alcance a nuevas asignaturas
- Crear nuevos dominios académicos
- Añadir funcionalidades fuera del scope de tesis
- Rediseñar la arquitectura de sistema completa
- Modificar la base de datos en formas que afecten datos existentes de demo
- Eliminar funcionalidades ya completadas

---

## STACK TÉCNICO

### Backend

- Python 3.11 + FastAPI
- PostgreSQL + SQLAlchemy
- Redis (caché y cola de eventos)
- LangChain / LLM Integration

### Frontend

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Framer Motion
- shadcn/ui

### AI / Agents

- LangGraph o custom swarm orchestration
- Anthropic Claude API (principal)
- Embeddings para RAG

### DevOps

- Docker Compose (desarrollo)
- Render.com (producción)

---

## ESTÉTICA Y DISEÑO

**Paleta obligatoria:**

```
Background:   #0a0a0f (dark base)
Primary:      #06b6d4 (cyan)
Secondary:    #7c3aed (violeta)
Accent:       #8b5cf6 (lavender)
Surface:      rgba(255,255,255,0.05) (glass)
Border:       rgba(255,255,255,0.1)
Text:         #f8fafc
Muted:        #94a3b8
```

**Principios visuales:**

- Espacio vacío intencional (no llenar todo)
- Máximo 3-4 tarjetas por vista
- Una sola acción primaria por pantalla
- Jerarquía tipográfica clara
- Animaciones sutiles (Framer Motion)
- Glass morphism para paneles secundarios
- Hex/grid como elemento decorativo de fondo

**Referencia de estilo:** Swarm Academy (dashboard minimalista, foco único)

---

## PRIORIDAD DE TAREAS

```
P0: Estabilidad + bugs críticos + demo funcional
P1: Experiencia adaptativa del estudiante
P2: Explicabilidad multiagente
P3: Modo Evidencia (Swarm Monitor, Replay, Decision Trace)
P4: Polish visual
P5: Funcionalidades opcionales
```

---

## FLUJO ESTUDIANTE (Referencia Canónica)

```
Login
→ Dashboard (solo Fundamentos de la Programación)
→ Learning Path (módulos 1-9)
→ Módulo Adaptativo (pantalla estrella)
→ Tutor IA
→ Evaluación
→ Explicabilidad de la adaptación
```

---

## MODO EVIDENCIA (Referencia Canónica)

**No es un rol de usuario.** Es una capacidad de observabilidad del sistema,
destinada a visualizar el proceso interno de adaptación con fines de
evaluación y validación experimental durante la sustentación.

Los actores del sistema son tres: Estudiante (aprende), Docente (acompaña),
Administrador (administra). El Modo Evidencia demuestra científicamente
cómo el sistema tomó sus decisiones.

```
Acceso (/evidencia — desde sidebar admin/docente o directo)
→ Demo Multiagente (swarm en vivo, deliberación, consenso)
→ Replay Cognitivo (sesiones, evolución longitudinal)
→ Decision Trace / Métricas / Timeline de adaptación
```

---

## MÓDULOS DE FUNDAMENTOS (Referencia)

1. Introducción a la Programación
2. Variables y Tipos de Datos
3. Operadores y Expresiones
4. Condicionales
5. Bucles
6. Funciones
7. Arreglos
8. Recursividad
9. POO básica

---

## CONVENCIONES DE CÓDIGO

### Commits

```
feat(scope): descripción
fix(scope): descripción
refactor(scope): descripción
style(scope): descripción
```

Scopes válidos:
- `dashboard`, `learning-path`, `module`, `tutor`, `swarm`, `agents`, `auth`, `api`, `db`, `ui`

**Disciplina de tipo (Etapa 3 — producto demostrable):**
- `feat` solo cuando aparece una capacidad completamente nueva.
- `fix` cuando se elimina un bloqueo (crítico o fricción).
- `refactor` cuando cambia la estructura sin alterar comportamiento.
- `docs` cuando el cambio es únicamente documentación.
- No mezclar tipos en un mismo commit. Un commit = una decisión.

### Archivos Frontend

```
/frontend/src/
├── app/                    # Next.js App Router
├── components/
│   ├── ui/                 # shadcn primitivos
│   ├── dashboard/          # Dashboard components
│   ├── learning/           # Learning path + módulos
│   ├── swarm/              # Swarm monitor + replay
│   └── shared/             # Reutilizables
├── lib/                    # Utils y configuración
└── types/                  # TypeScript types
```

### Archivos Backend

```
/backend/
├── app/
│   ├── api/                # Endpoints FastAPI
│   ├── models/             # SQLAlchemy models
│   ├── services/           # Business logic
│   ├── agents/             # Swarm agents
│   └── core/               # Config, DB, Redis
```

---

## CRITERIO DE DONE

Una tarea está completa cuando:

1. Funciona sin errores en consola.
2. El flujo demo puede ejecutarse de inicio a fin.
3. La UI es visualmente coherente con la estética neural dark.
4. El jurado puede entenderlo en menos de 5 minutos.

---

## SHORTCUTS PERMITIDOS

Para velocidad de entrega son aceptables:

✅ Mock data para demos
✅ Métricas simuladas de swarm
✅ Escenarios hardcodeados para sustentación
✅ Eventos fake de agentes si ayudan a explicar el sistema
✅ Visualizaciones simplificadas que comuniquen la arquitectura

**El objetivo es demostrar la hipótesis, no construir producción.**

---

## GESTIÓN DE TOKENS (RTK)

Usar siempre `rtk` como prefijo:

```bash
rtk git status
rtk git diff
rtk tsc
rtk lint
rtk vitest
rtk next build
rtk pnpm install
```

---

## MEMORIA PERSISTENTE

Directorio de memoria:
`/home/rlara/.claude/projects/-var-home-rlara-Documentos-Proyecto-multiagent-llm-education/memory/`

Archivos clave de memoria:
- `MEMORY.md` — índice
- `project_stabilization_audit.md` — bugs P0/P1/P2
- `forensic_audit_jun2026_boot_failure.md` — historia de boot failure

---

## RECORDATORIO FINAL

Este sistema es:

**UN SISTEMA DE APRENDIZAJE ADAPTATIVO MULTIAGENTE PARA FUNDAMENTOS DE LA PROGRAMACIÓN.**

No es una plataforma universitaria completa.

Cada decisión debe acercar el proyecto a una sustentación exitosa.

---

## REGLA DE ORO

Si una propuesta mejora la plataforma pero no fortalece la hipótesis,
**se rechaza.**

La tesis tiene prioridad absoluta sobre el producto.

No estamos construyendo la plataforma más grande.

**Estamos construyendo la evidencia científica más sólida.**

---

## REGLA DE DESARROLLO (Etapa 2 — Plataforma funcional)

> **No se desarrolla por pantalla. Se desarrolla por recorrido completo.**

Desde el commit `bfec134` (Modo Evidencia), la arquitectura de investigación
está consolidada y la pregunta de trabajo cambió:

- ❌ "¿Qué otra idea mejora la plataforma?"
- ✅ "¿Qué impide que un estudiante complete todo el flujo de aprendizaje?"

El ciclo de trabajo es el de un equipo de producto:

```
Abrir la aplicación
→ Recorrerla como el actor (estudiante / docente / admin / jurado)
→ Encontrar un bloqueo
→ Corregir ese bloqueo
→ Commit (una decisión por commit)
→ Repetir
```

Orden de prioridad de los recorridos: **Estudiante (es el 70% de la tesis)
→ Docente (sus 4 preguntas) → Administrador (mínimo) → Modo Evidencia
(preparación de la sustentación)**. Los bloqueos se registran en
FLOW_AUDIT.md. Nunca "hoy mejoraré una pantalla"; siempre "hoy el actor
podrá llegar de X a Y sin interrupciones".

---

## REGLA DE CIERRE

> **Un recorrido no se considera terminado hasta que un usuario real pueda
> completarlo de principio a fin sin intervención del desarrollador.**

No basta con que compile ni con que los tests pasen. Cada recorrido se
prueba como lo haría su actor correspondiente (estudiante, docente,
administrador o jurado), en navegador real y contra el stack completo.
La unidad de trabajo no es el sprint: es el **cierre de recorrido**.
El tablero de cierres vive en FLOW_AUDIT.md § Tablero Etapa 2.
