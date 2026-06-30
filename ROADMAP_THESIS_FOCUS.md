# UPAO-MAS-EDU — Thesis Focus Roadmap

> Antes de cualquier sprint, leer THESIS_SCOPE_FREEZE.md.

---

## Objetivo Principal

La investigación NO busca construir un LMS universitario completo.

La investigación busca demostrar:

> "Efecto de una arquitectura multiagente basada en inteligencia de enjambre en la adaptación de contenido multimodal en estudiantes de Fundamentos de la Programación."

Toda decisión de desarrollo debe responder a esta pregunta:

**¿Esto ayuda a demostrar la adaptación multimodal en Fundamentos de la Programación?**

Si la respuesta es NO, no debe implementarse.

---

## Scope Freeze

### Curso Único

**Fundamentos de la Programación.**

Eliminado permanentemente:

- Matemática Discreta
- Base de Datos
- Sistemas Operativos
- Estadística
- Investigación Académica
- Malla curricular institucional
- Recomendación de siguientes cursos

Estas funcionalidades quedan catalogadas como:

> "Trabajo futuro y escalabilidad del sistema."

---

## Flujos de Producto

### Estudiante

```
Login
↓
Dashboard (solo Fundamentos de la Programación)
↓
Ruta de aprendizaje
↓
Módulo adaptativo
↓
Tutor IA
↓
Evaluación
```

### Investigador

```
Login (rol investigador)
↓
Dashboard investigador
↓
Swarm Monitor
↓
Replay Cognitivo
↓
Agent Lab (opcional)
```

---

## Arquitectura Visual

**Inspiración:** Swarm Academy

**Mantener:**
- Neural dark como base
- Cyan (#06b6d4) y violeta (#7c3aed) como acentos
- Glass panels
- Hex / grid background
- Espacio vacío intencional

**Eliminar:**
- Dashboards sobrecargados con 9+ tarjetas
- Exceso de información simultánea
- Sección de cursos universitarios completos

---

## Dashboard Estudiante (Rediseño)

Mostrar únicamente:

- Bienvenida personalizada
- Progreso en Fundamentos de la Programación (%)
- Ruta de aprendizaje (módulos secuenciales)
- Adaptación actual (perfil + confianza de agentes)
- Recomendación IA del día

NO mostrar:

- Grid de 9 cursos
- Estadísticas institucionales
- Siguientes asignaturas de carrera
- Malla curricular completa

---

## Ruta de Aprendizaje

Módulos en orden:

1. Introducción a la Programación
2. Variables y Tipos de Datos
3. Operadores y Expresiones
4. Condicionales
5. Bucles
6. Funciones
7. Arreglos
8. Recursividad
9. POO básica

Cada módulo incluye:

- Diagnóstico inicial
- Contenido adaptativo multimodal
- Tutor IA
- Evaluación

---

## Módulo Adaptativo (Pantalla Estrella)

Esta debe ser la pantalla más impresionante para la sustentación.

Componentes obligatorios:

- Indicador de adaptación actual (perfil + Bloom)
- Confianza de agentes (%)
- Progreso dentro del módulo
- Contenido teórico adaptado
- Diagramas visuales
- Ejemplos de código interactivos
- Feedback del swarm
- Explicación del porqué de la adaptación

---

## Sprints

### M1 — LLM Content Generation

**Objetivo:** Eliminar contenido hardcodeado.

El backend genera dinámicamente:

```
ConceptBlock:
  explanation
  analogy
  curiosity
  prediction_question
  reflection_question
  mini_activity
  media_prompt
```

Eliminar dominios hardcodeados cuando M1 esté estable.

---

### N1 — Polish Visual

**Objetivo:** Parecer un producto terminado.

- Dashboard estudiante rediseñado (Swarm Academy style)
- Dashboard investigador con Swarm Monitor
- Sidebar expandido y funcional
- Header limpio con búsqueda
- Eliminación de cursos no relacionados con la tesis

---

### N2 — Swarm Monitor

**Objetivo:** Demostración visual para el jurado.

Puede incluir:

- Datos simulados
- Métricas mockeadas
- Eventos de swarm en tiempo real (o fake-real-time)

Propósito: que el jurado pueda ver el swarm "funcionando".

---

### N3 — Agent Lab (Opcional)

Solo implementar si:

- M1 terminado
- Dashboard completamente estable
- ModuleLearningView terminado

---

## Fuera de Alcance Permanente

❌ LMS institucional completo
❌ Gestión de carreras
❌ Soporte multi-facultad
❌ Múltiples asignaturas activas
❌ Sistema de prerrequisitos complejos
❌ Motor de recomendación de cursos
❌ Analítica institucional avanzada
❌ Marketplace de cursos
❌ Administración académica

---

## Prioridades

| Nivel | Descripción                       |
|-------|-----------------------------------|
| P0    | Estabilidad + demo funcional      |
| P1    | Experiencia estudiante + adaptación |
| P2    | Herramientas del investigador     |
| P3    | Funcionalidades futuras           |

---

## Criterio de Aceptación Final

El sistema debe poder demostrar en vivo:

1. Diagnóstico.
2. Perfil de aprendizaje.
3. Adaptación multimodal.
4. Generación de contenido con IA.
5. Explicabilidad de agentes.
6. Evidencia visual del swarm.

**Nada más.**

---

## Trabajo Futuro (Para el Capítulo de Conclusiones)

- Escalabilidad a otras asignaturas de Ingeniería de Sistemas
- Integración con sistemas institucionales reales
- App móvil nativa
- Análisis longitudinal del aprendizaje
- Transferencia de conocimiento entre asignaturas
