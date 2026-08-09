# THESIS_SCOPE_FREEZE
Version: 1.0
Status: LOCKED
Date: 2026-06-29

---

# Título de Tesis

"Efecto de una arquitectura multiagente basada en inteligencia de enjambre en la adaptación de contenido multimodal en estudiantes de Fundamentos de la Programación."

---

# OBJETIVO PRINCIPAL DE INVESTIGACIÓN

Demostrar que una arquitectura multiagente basada en swarm intelligence puede adaptar contenido educativo según el perfil del estudiante y mejorar la experiencia de aprendizaje en Fundamentos de la Programación.

Este proyecto NO está pensado para convertirse en:

- un LMS completo,
- un sistema de gestión universitaria,
- una plataforma de administración curricular,
- un ecosistema educativo multi-asignatura.

---

# REGLA DE ORO

Cada decisión de implementación debe responder:

> ¿Esta funcionalidad ayuda a demostrar la adaptación multimodal en Fundamentos de la Programación?

Si la respuesta es NO:

NO IMPLEMENTAR.

---

# ALCANCE DEL SISTEMA

El sistema existe para demostrar:

1. Diagnóstico del estudiante.
2. Identificación del perfil de aprendizaje.
3. Razonamiento multiagente.
4. Inteligencia de enjambre.
5. Generación de contenido adaptativo.
6. Aprendizaje multimodal.
7. Explicabilidad de las recomendaciones.

Nada más.

---

# FUNCIONALIDADES EN ALCANCE

## Autenticación

- Login
- Gestión de roles (estudiante / docente / admin)
- Gestión de sesión

---

## Experiencia Estudiante

- Dashboard (foco único: Fundamentos de la Programación)
- Learning Path (ruta de módulos)
- Módulos Adaptativos
- Tutor IA
- Seguimiento de progreso

---

## Aprendizaje Adaptativo

- Test de diagnóstico
- Generación de perfil de aprendizaje
- Adaptación de contenido
- Recomendaciones personalizadas
- Explicabilidad de adaptaciones

---

## Sistema Multiagente

- Orquestación de swarm
- Coordinación de agentes
- Motor de consenso
- Memoria compartida
- Trazas de agentes
- Observabilidad

---

## Herramientas de Investigación

- Swarm Monitor
- Replay cognitivo
- Visualización de métricas
- Logs de experimentos
- Dashboards de explicabilidad

---

## Alcance de Asignatura

ÚNICO CURSO:

### Fundamentos de la Programación

Módulos:

1. Introducción a la Programación
2. Variables y Tipos de Datos
3. Operadores y Expresiones
4. Condicionales
5. Bucles
6. Funciones
7. Arreglos
8. Recursividad
9. Programación Orientada a Objetos (básica)

---

# FUERA DE ALCANCE

Las siguientes funcionalidades están explícitamente prohibidas.

## Gestión Académica

❌ Gestión de carreras
❌ Gestión de facultades
❌ Administración institucional
❌ Calendario académico
❌ Sistema de matrícula
❌ Pagos y certificados
❌ Gestión de calificaciones
❌ Historial académico del estudiante

---

## Expansión de LMS

❌ Plataforma multi-asignatura
❌ Currículo universitario completo
❌ Prerequisitos complejos
❌ Motor de recomendación de cursos
❌ Progresión de carrera
❌ Analítica institucional
❌ Soporte multi-departamento
❌ Marketplace de cursos

---

## Expansión de Producto

❌ App móvil
❌ Plataforma de notificaciones
❌ Funcionalidades de red social
❌ Sistema de chat general
❌ Foros
❌ Plataforma de gamificación
❌ Colaboración en tiempo real

---

# METAS DE DISEÑO VISUAL

La aplicación debe sentirse como:

> "Un sistema de aprendizaje adaptativo inteligente."

La aplicación NO debe sentirse como:

> "Un ERP universitario."

Estética objetivo:

- Neural dark
- Cyan + violeta como acentos
- Glass panels
- Hex/grid background
- Espacio vacío intencional
- Jerarquía visual clara
- Pocas tarjetas, gran impacto

---

# FLUJO DEMO PRINCIPAL — ESTUDIANTE

```
Login
↓
Diagnóstico
↓
Perfil de Aprendizaje
↓
Dashboard (Fundamentos de la Programación)
↓
Learning Path
↓
Módulo Adaptativo
↓
Tutor IA
↓
Evaluación
↓
Explicabilidad
```

---

# FLUJO DEMO — MODO EVIDENCIA

El Modo Evidencia no es un rol de usuario: es la capacidad de
observabilidad del sistema, activada durante la sustentación para
demostrar cómo y por qué el swarm adaptó el aprendizaje.

```
Activar Modo Evidencia (/evidencia)
↓
Demo Multiagente (swarm en vivo)
↓
Replay Cognitivo
↓
Explicación de Agentes / Decision Trace
↓
Métricas
```

---

# PRIORIDADES DE DESARROLLO

| Prioridad | Área                                |
|-----------|-------------------------------------|
| P0        | Estabilidad y demo funcional        |
| P1        | Experiencia adaptativa del estudiante |
| P2        | Explicabilidad multiagente          |
| P3        | Modo Evidencia (observabilidad)     |
| P4        | Polish visual                       |
| P5        | Funcionalidades opcionales          |

---

# MARCO DE DECISIÓN

Antes de implementar cualquier funcionalidad:

**Pregunta 1:** ¿Contribuye directamente a la hipótesis de tesis?
**Pregunta 2:** ¿Se mostrará durante la sustentación?
**Pregunta 3:** ¿Mejora la experiencia adaptativa del estudiante?
**Pregunta 4:** ¿Mejora la demostración de investigación?

Si todas las respuestas son NO: **NO IMPLEMENTAR.**

---

# ATAJOS ACEPTABLES

Los siguientes enfoques están permitidos:

✅ Mock data para demos
✅ Métricas simuladas
✅ Dashboards simplificados
✅ Eventos de swarm fake
✅ Visualizaciones solo para demo
✅ Escenarios hardcodeados para sustentación

siempre que ayuden a explicar la arquitectura al jurado.

---

# PRINCIPIO NO NEGOCIABLE

Un sistema pequeño que demuestra perfectamente la hipótesis es mejor que un sistema grande que intenta resolver problemas no relacionados.

---

# CRITERIOS DE ÉXITO

El jurado debe entender el sistema en menos de cinco minutos.

El jurado debe ver claramente:

1. Diagnóstico.
2. Adaptación.
3. Razonamiento multiagente.
4. Inteligencia de enjambre.
5. Contenido personalizado.
6. Explicabilidad.

Todo lo demás es secundario.

---

# REMEDIACIÓN — C5 (2026-08-08)

La auditoría forense consolidada de 2026-08-08 confirmó que este alcance
venía siendo violado en la práctica, no solo en riesgo teórico (hallazgo
C5, ya señalado por la auditoría externa de 2026-08-06 como "18 catálogos
de cursos fuera de alcance").

**Lo que existía:** `backend/seed.py` sembraba por defecto una malla
curricular institucional completa de Ingeniería de Sistemas e IA — 44
`Course` (10 ciclos) + 50 `InstitutionalCourse` (10 ciclos, con su propia
tabla de prerrequisitos) — más un curso de demostración `SWA101` ajeno al
alcance. Esto no era solo dato inerte: `/docente/courses` tenía una
pestaña real **"Malla Curricular"** donde el docente podía autoasignarse
("Asignarme") cualquiera de los 50 cursos institucionales de cualquier
ciclo/carrera y crear un `Course` nuevo desde ahí, respaldado por 4
endpoints en vivo (`GET/POST /api/curriculum/cycles`, `/courses`,
`/teacher-assignments`). Es decir: una funcionalidad completa de gestión
curricular institucional, exactamente lo que la sección "Expansión de
LMS" de este documento prohíbe.

**Lo que se hizo:**
- Se retiró la pestaña "Malla Curricular" y el tab "De la malla" de
  `CourseForm`, junto con los 4 endpoints `/api/curriculum/*` que solo
  esa UI consumía y los hooks/tipos frontend asociados
  (`useCurriculumCycles`, `useCurriculumCourses`, `useTeacherAssignments`,
  `useAssignTeacherCourse`). `GET /api/curriculum/academic-audit` se
  conservó — no depende del catálogo de 50 cursos y no tiene UI que lo
  consuma.
- `curriculum_service.py` se redujo a las funciones de las que sí depende
  un flujo real del producto (auto-inscripción → activación →
  `EducationalContext`, cubierto por
  `tests/test_enrollment_lifecycle.py`) — no se re-expone ningún endpoint
  sobre ellas.
- `backend/seed.py` siembra por defecto **únicamente** IS301 (Fundamentos
  de la Programación) — la malla institucional completa (`Course` +
  `InstitutionalCourse`) y `SWA101` quedan disponibles solo con
  `SEED_FULL_MESH=1`, para desarrollo/pruebas explícitas, sin borrar el
  dato ni el código que los siembra.
- Verificado sin regresiones: mismo conjunto exacto de fallos
  pre-existentes en `test_enrollment_lifecycle.py`/`test_query_counts.py`
  antes y después (comparado byte a byte contra `git stash`), `tsc
  --noEmit` limpio, cero referencias colgantes en todo el repo.

---

# DECLARACIÓN FINAL

Este proyecto es:

**UN SISTEMA DE APRENDIZAJE ADAPTATIVO MULTIAGENTE PARA FUNDAMENTOS DE LA PROGRAMACIÓN.**

Este proyecto NO es:

**UNA PLATAFORMA UNIVERSITARIA COMPLETA.**
