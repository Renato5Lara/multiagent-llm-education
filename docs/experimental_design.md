# Diseño Experimental — Tesis: Arquitectura Multiagente basada en Inteligencia de Enjambre para Educación en Programación

---

## Tabla de Contenidos

1. [Hipótesis Central y Sub-hipótesis](#1-hipótesis-central-y-sub-hipótesis)
2. [Población, Muestra y Variables](#2-población-muestra-y-variables)
3. [Experimento A — Adaptación Educativa Multinivel](#3-experimento-a--adaptación-educativa-multinivel)
4. [Experimento B — Coordinación Colectiva entre Agentes](#4-experimento-b--coordinación-colectiva-entre-agentes)
5. [Experimento C — Resiliencia del Enjambre ante Fallos](#5-experimento-c--resiliencia-del-enjambre-ante-fallos)
6. [Experimento D — Precisión del Consenso Multiagente](#6-experimento-d--precisión-del-consenso-multiagente)
7. [Experimento E — Efecto del Aprendizaje Adaptativo (Longitudinal)](#7-experimento-e--efecto-del-aprendizaje-adaptativo-longitudinal)
8. [Experimento F — Propagación Cognitiva en la Cadena de Agentes](#8-experimento-f--propagación-cognitiva-en-la-cadena-de-agentes)
9. [Experimento G — Efectividad de la Memoria Compartida](#9-experimento-g--efectividad-de-la-memoria-compartida)
10. [Análisis Estadístico y Criterios de Evaluación](#10-análisis-estadístico-y-criterios-de-evaluación)
11. [Instrumentos de Recolección](#11-instrumentos-de-recolección)
12. [Plan de Reproducibilidad y Open Science](#12-plan-de-reproducibilidad-y-open-science)

---

## 1. Hipótesis Central y Sub-hipótesis

### Hipótesis Central (H₀ / H₁)

> **H₁**: Una arquitectura multiagente basada en inteligencia de enjambre mejora significativamente la adaptación, coordinación, resiliencia y efectividad del aprendizaje en cursos de fundamentos de programación, comparado con un sistema educativo monolítico tradicional.

> **H₀**: No existe diferencia significativa entre la arquitectura swarm y un sistema monolítico para educación en programación.

### Sub-hipótesis

| ID | Sub-hipótesis | Experimento |
|----|--------------|-------------|
| SH1 | La ruta pedagógica generada por el enjambre produce mayor ganancia de aprendizaje que un plan de estudios fijo | A |
| SH2 | Los agentes del swarm muestran acoplamiento informacional medible a través de la memoria compartida | B |
| SH3 | El swarm mantiene operatividad >80% ante fallos de hasta 2 agentes simultáneos | C |
| SH4 | El consenso multiagente supera en precisión al voto individual de cualquier agente aislado | D |
| SH5 | La adaptación continua del swarm reduce la tasa de abandono en ≥15% frente a ruta fija | E |
| SH6 | La etapa cognitiva detectada por el agente pedagógico predice significativamente la ruta seleccionada por el agente adaptativo | F |
| SH7 | La memoria compartida reduce la divergencia entre agentes en ≥30% comparado con agentes aislados | G |

---

## 2. Población, Muestra y Variables

### Población Objetivo
Estudiantes universitarios de primer año cursando "Fundamentos de Programación" (cursos PRO201, ALG401, IS301).

### Muestra Requerida
- **Mínimo**: n = 60 estudiantes (30 control, 30 experimental)
  - Cálculo: prueba t de Student para diferencias entre grupos, α = 0.05, β = 0.80, effect size esperado d = 0.7
- **Óptimo**: n = 120 (60 control, 60 experimental)
- **Criterios de inclusión**: Sin experiencia previa en programación (autoreporte), matriculados en primer curso de programación

### Variables

#### Variables Independientes (manipuladas)

| Variable | Descripción | Niveles |
|----------|-------------|---------|
| **Arquitectura del sistema** | Tipo de motor educativo | Swarm (experimental) vs Monolítico (control) |
| **Fallo inducido** | Agente desconectado o con timeout (experimento C) | 0, 1, 2, 3 agentes caídos |
| **Modo de consenso** | Tipo de votación usado (experimento D) | Individual vs multiagente |
| **Modo de memoria** | Memoria compartida habilitada/deshabilitada (experimento G) | On / Off |

#### Variables Dependientes (medidas)

| Variable | Instrumento | Unidad |
|----------|-------------|--------|
| **Ganancia de aprendizaje normalizada** (g) | Pre-test y post-test (Hake, 1998) | [0, 1] |
| **Tasa de finalización** | Logros del curso | % |
| **Tiempo por concepto** | Registro de plataforma | minutos |
| **Precisión del consenso** | Comparación contra expertos | % de acierto |
| **Tiempo de recuperación ante fallo** | Logs del swarm | segundos |
| **Divergencia entre agentes** | SharedMemory records | desviación intra-agente |
| **Coeficiente de acoplamiento** | Frecuencia de lecturas/escrituras en shared memory | count / ciclo |
| **Satisfacción del estudiante** | SUS (System Usability Scale) + cuestionario ad-hoc | [0, 100] |
| **Tasa de acierto en debugging** | Ejercicios de depuración calificados | % |

#### Variables Controladas

| Variable | Estrategia de control |
|----------|-----------------------|
| Contenido del curso | Mismos 26 conceptos, mismos ejercicios base |
| Instructor | Mismo profesor para ambos grupos |
| Duración | 16 semanas ambos grupos |
| Idioma | Pseudocódigo en español (mismo dialecto) |
| Evaluación | Mismos instrumentos de medición (pre/post-test) |
| Sistema operativo / hardware | Entorno de laboratorio estandarizado |

---

## 3. Experimento A — Adaptación Educativa Multinivel

### Objetivo
Demostrar que la ruta generada por el swarm (vía `ProgrammingPathwayEngine` + `PedagogicalAgent` + `AdaptiveAgent`) produce mayor ganancia de aprendizaje que un plan de estudios fijo secuencial.

### Hipótesis asociada
**SH1**: La ruta pedagógica generada por el enjambre produce mayor ganancia de aprendizaje que un plan de estudios fijo.

### Diseño
**Tipo**: Ensayo controlado aleatorizado (RCT), post-test únicamente con pre-test como covariable.

**Grupos**:
- **G_swarm** (n=30): Recibe rutas generadas por `ProgrammingPathwayEngine.build_pathway_plan()` con selección entre 4 pathways (standard, accelerated, reinforced, visual_first). El pathway se re-evalúa cada 2 semanas.
- **G_fijo** (n=30): Recibe el orden fijo de conceptos definido en el silabo secuencial del curso (variables → tipos → expresiones → condicionales → booleanos → ciclos → arreglos → funciones → etc.).

### Protocolo

```
Semana 0:  Pre-test de conceptos (26 preguntas, 1 por concepto)
           Asignación aleatoria a G_swarm o G_fijo
           ---
Semana 1:  Tema 1 (variables, tipos de datos)
Semana 2:  Tema 2 (expresiones, entrada/salida)
Semana 3:  Tema 3 (condicionales, lógica booleana)
Semana 4:  Tema 4 (ciclos básicos)
Semana 5:  Tema 5 (ciclos anidados, patrones)
Semana 6:  Tema 6 (arreglos, strings)
Semana 7:  Tema 7 (funciones, parámetros)
Semana 8:  Post-test parcial + re-evaluación de ruta (solo G_swarm)
           ---
Semana 9:  Tema 8 (ámbito, retorno)
Semana 10: Tema 9 (algoritmos básicos: búsqueda)
Semana 11: Tema 10 (algoritmos: ordenamiento)
Semana 12: Tema 11 (recursión)
Semana 13: Tema 12 (debugging, manejo de errores)
Semana 14: Tema 13 (CT: descomposición, abstracción)
Semana 15: Repaso integrador
Semana 16: Post-test final + SUS
```

El grupo G_swarm recibe los mismos temas pero el orden semanal se ajusta dinámicamente según:
- Etapa cognitiva detectada (`CognitiveStageDetector.detect()`)
- Conceptos dominados/débiles (`StrengthRecord`, `WeaknessRecord`)
- Perfil de aprendizaje (`DiagnosticResult.dominant_modality`)
- Puntuación CT (`ct_progression_service`)

### Instrumentos específicos

**Pre-test / Post-test de Fundamentos de Programación (PFPT)**

26 ítems, 1 por concepto `ProgrammingConcept`. Cada ítem tiene 3 partes:
1. **Conocimiento declarativo**: "¿Qué es una variable?" (opción múltiple)
2. **Aplicación en pseudocódigo**: dado un problema, seleccionar/ escribir el fragmento correcto
3. **Depuración**: identificar el error en código dado

Ejemplo (ítem 3 — CONDITIONALS):
```
Declarativo: ¿Qué operador se usa para evaluar "diferente de" en pseudocódigo?
  a) !=   b) <>   c) ¬=   d) /=

Aplicación: Dado un número, escribe pseudocódigo que imprima "Par" si es divisible por 2.

Depuración: Encuentra el error:
  SI edad >= 18 ENTONCES
      ESCRIBIR "Mayor"
  SINO SI edad > 0 ENTONCES
      ESCRIBIR "Menor"
  FIN_SI
```

Cada ítem se califica 0-3 (1 punto por parte). Puntaje máximo: 78.

**Validez del instrumento**: Validación por 3 expertos en educación en programación (V de Aiken ≥ 0.80). Confiabilidad: α de Cronbach en prueba piloto (n=20) ≥ 0.75.

### Métricas específicas

| Métrica | Fórmula | Interpretación |
|---------|---------|----------------|
| Ganancia normalizada de Hake | g = (post% - pre%) / (100% - pre%) | g > 0.7 = alta |
| Efecto por concepto | Δc = post_aciertos_c - pre_aciertos_c | Por concepto individual |
| Tiempo hasta dominio | Semanas hasta mastery_threshold para cada concepto | Menor = mejor |
| Tasa de retrocesos | Veces que un concepto "dominado" vuelve a estado débil | Menor = mejor |

### Criterios de evaluación

- **SH1 aceptada si**: g_swarm > g_fijo con p < 0.05 y d de Cohen ≥ 0.5
- **Aceptación parcial si**: g_swarm > g_fijo pero solo en subconjunto de conceptos (ej. condicionales anidados, funciones)
- **Rechazo si**: p ≥ 0.05 o d < 0.2

### Variables de confusión identificadas

| Confusor | Mitigación |
|----------|------------|
| Efecto Hawthorne (saber que está en grupo experimental) | Cegamiento: ambos grupos usan la misma plataforma, no saben su asignación |
| Diferencia inicial en habilidad | ANCOVA con pre-test como covariable |
| Abandono diferencial entre grupos | Análisis por intención de tratar (ITT) |

---

## 4. Experimento B — Coordinación Colectiva entre Agentes

### Objetivo
Demostrar que existe acoplamiento informacional medible entre los 4 agentes del swarm a través del `SharedMemoryStore`, y que este acoplamiento produce decisiones más coherentes que agentes aislados.

### Hipótesis asociada
**SH2**: Los agentes del swarm muestran acoplamiento informacional medible a través de la memoria compartida.

### Diseño
**Tipo**: Experimento intra-sujeto (within-subject) con 3 condiciones, usando el mismo conjunto de 50 casos de estudiantes sintéticos (generados con perfiles diversos).

### Casos de prueba sintéticos

Generar 50 perfiles de estudiante cubriendo combinatoria de:

| Variable | Valores |
|----------|---------|
| Etapa cognitiva | 6 etapas (pre_algorithmic a creative_computing) |
| Conceptos débiles | 0–5 conceptos aleatorios |
| Modalidad de aprendizaje | visual, auditiva, kinestésica, lectura/escritura |
| Nivel CT | 4 niveles × 4 dimensiones |
| Puntaje diagnóstico | 20–100 (uniforme) |

### Protocolo

Para cada uno de los 50 perfiles, ejecutar el swarm completo (`SwarmOrchestrator.activate()`) en 3 modos:

| Condición | Descripción |
|-----------|-------------|
| **C1: Aislado** | Cada agente se ejecuta sin shared memory. Las decisiones se toman independientemente y se concatenan al final. |
| **C2: Secuencial** | Los agentes se ejecutan en secuencia (pedagógico → adaptativo → riesgo → evaluación) pero sin shared memory. Cada uno recibe el output del anterior como input directo. |
| **C3: Swarm completo** | Los 4 agentes usan `SharedMemoryStore.publish_observation()` y `query_memory()`. El `CollectiveInferenceEngine` integra patrones. |

### Métricas específicas

| Métrica | Fórmula | Instrumento |
|---------|---------|-------------|
| **Coeficiente de acoplamiento (Ca)** | `Ca = (escrituras_shared + lecturas_shared) / (total_operaciones_agente)` | Contadores en agentes (publish_observation / query_memory calls) |
| **Consistencia interna (Ci)** | 1 - (desviación estándar de outputs entre agentes para misma variable) | SharedMemory records |
| **Coherencia de ruta** | ¿La ruta final es consistente con la etapa cognitiva y el perfil de riesgo? Evaluado por experto en escala 1-5 | Revisión por 2 expertos |
| **Tiempo de convergencia** | ms desde que el primer agente publica hasta que el último agente lee y ajusta | Timestamps en SwarmEventBus |
| **Volumen de intercambio** | Número de observaciones publicadas por ciclo de activación | SharedMemoryStore.count() |

### Instrumento de evaluación por expertos

Rúbrica para evaluar coherencia de ruta (escala 1-5):

| Criterio | 1 | 3 | 5 |
|----------|---|---|---|
| Consistencia etapa-ruta | La ruta ignora la etapa cognitiva | La ruta considera parcialmente la etapa | La ruta está perfectamente alineada con la etapa |
| Atención a debilidades | Ignora conceptos débiles | Aborda algunas debilidades | Prioriza explícitamente conceptos débiles |
| Gestión de riesgo | Sin ajuste por riesgo alto | Reduce velocidad si riesgo alto | Adapta contenido, ritmo y soporte |
| Dificultad progresiva | Saltos bruscos de dificultad | Progresión parcial | Bloom range calibrado finamente |

### Criterios de evaluación

- **SH2 aceptada si**: Ca(C3) > Ca(C2) > Ca(C1) con p < 0.01 y consistencia interna Ci(C3) > Ci(C2) > Ci(C1)
- **Aceptación parcial si**: Ca(C3) > Ca(C1) pero no hay diferencia significativa entre C2 y C3
- **Rechazo si**: No hay diferencias significativas en Ca ni Ci entre condiciones

### Análisis específico

```python
# Datos: 50 perfiles × 3 condiciones = 150 observaciones
# Prueba: ANOVA de medidas repetidas con post-hoc Bonferroni
# Variable dependiente: consistencia_interna
from scipy.stats import f_oneway
from statsmodels.stats.anova import AnovaRM

# Hipótesis: mean(Ci_C3) > mean(Ci_C2) > mean(Ci_C1)
```

---

## 5. Experimento C — Resiliencia del Enjambre ante Fallos

### Objetivo
Cuantificar la capacidad del swarm para mantener operatividad y calidad de decisión cuando uno o más agentes fallan (timeout, caída, datos corruptos).

### Hipótesis asociada
**SH3**: El swarm mantiene operatividad >80% ante fallos de hasta 2 agentes simultáneos.

### Diseño
**Tipo**: Experimento de inyección de fallos (chaos engineering), intra-sujeto.

### Protocolo

Para cada uno de los 20 perfiles de estudiante (subconjunto representativo de los 50), ejecutar `SwarmOrchestrator.activate()` bajo diferentes escenarios de fallo:

| Escenario | Fallo inducido | Fase donde ocurre |
|-----------|----------------|-------------------|
| **F0: Baseline** | Sin fallos | — |
| **F1: Timeout pedagógico** | PedagogicalAgent no responde en 20s | PEDAGOGICAL_ANALYSIS |
| **F2: Caída adaptativo** | AdaptiveAgent lanza excepción no recuperable | ADAPTIVE_ADJUSTMENT |
| **F3: Timeout riesgo + caída evaluación** | RiskAgent timeout + EvaluationAgent exception | RISK_ASSESSMENT + CONTENT_PRODUCTION |
| **F4: Fallo en cascada** | ContextLoading falla → toda la activación debe rollback | CONTEXT_LOADING |
| **F5: Fallo de consenso** | ConsensusEngine recibe 3/5 votos REJECT | CONSENSUS |
| **F6: Caída de shared memory** | SharedMemoryStore no disponible | MEMORY_INIT |

### Métricas específicas

| Métrica | Fórmula |
|---------|---------|
| **Tasa de activación exitosa** | activaciones_completadas / activaciones_intentadas |
| **Tiempo de recuperación (RTO)** | ms desde detección de fallo hasta fase completada o rollback |
| **Degradación de calidad** | coherencia_ruta(Fx) / coherencia_ruta(F0) |
| **Precisión de rollback** | ¿El sistema vuelve al estado anterior correcto? Verificar EducationalContext.status |
| **Número de reintentos** | Veces que `fail_phase()` → `retry()` antes de éxito o rollback |
| **Propagación del fallo** | ¿El fallo en fase X se propaga a fases Y, Z? Medido por SwarmEventBus |
| **Completitud de datos** | % de observaciones en shared memory comparado con F0 |

### Criterios de evaluación

| Escenario | Criterio mínimo | Criterio óptimo |
|-----------|-----------------|------------------|
| F1 (1 agente timeout) | Activación exitosa ≥90% | ≥95% con degradación <10% |
| F2 (1 agente caído) | Activación exitosa ≥85% | ≥90% con degradación <15% |
| F3 (2 agentes fallando) | Activación exitosa ≥70% | ≥80% con degradación <25% |
| F4 (rollback completo) | Rollback correcto 100% | Rollback y reactivación exitosa |
| F5 (consenso rechazado) | Decisión final documentada 100% | Re-evaluación automática con nuevos datos |
| F6 (shared memory caída) | Degradación graceful, sin crash | Operación en modo degradado con log |

- **SH3 aceptada si**: Tasa de éxito en F1+F2+F3 ≥ 80% y rollback correcto en F4

### Variables registradas por el swarm

```python
# De SwarmLifecycle.phase_history
{
    "phase": "pedagogical_analysis",
    "status": "failed",
    "started_at": "...",
    "completed_at": "...",
    "attempt": 1,
    "error": "AgentPedagogicalError: timeout after 20000ms"
}

# De SwarmEventBus events
{
    "event_type": "phase_failed",
    "context_key": "ctx:s42:c1",
    "causation_id": "parent_event_id",
    "payload": {
        "phase": "pedagogical_analysis",
        "error": "timeout",
        "action": "retry"
    }
}
```

---

## 6. Experimento D — Precisión del Consenso Multiagente

### Objetivo
Demostrar que la decisión combinada del `ConsensusEngine` (con `CodeMasteryVoter`, `ProgressionVoter`, `MasteryVoter`, `PrereqVoter`, `SequenceVoter`, `TimeVoter`) es más precisa y robusta que la decisión de cualquier votante individual.

### Hipótesis asociada
**SH4**: El consenso multiagente supera en precisión al voto individual de cualquier agente aislado.

### Diseño
**Tipo**: Experimento de validación contra ground truth (juicio experto).

### Protocolo

1. Seleccionar 100 situaciones de decisión educativa extraídas de interacciones reales de semestres anteriores
2. Cada situación incluye: perfil del estudiante, progreso actual, historial de intentos, próxima decisión a tomar (avanzar/reforzar/retroceder)
3. 3 instructores expertos (profesores con ≥5 años enseñando programación) clasifican cada situación como: APROBAR, RECHAZAR, ABSTENERSE
4. El ground truth para cada situación se define por mayoría de votos de los 3 expertos (kappa de Fleiss ≥ 0.70 para ser incluido en el dataset)
5. Ejecutar cada votante individual y el `ConsensusEngine` completo sobre las 100 situaciones

### Votantes evaluados

| Votante | Decisión esperada |
|---------|-------------------|
| CodeMasteryVoter | Evalúa 0.6×code_correctness + 0.4×ct_score |
| ProgressionVoter | Verifica prerequisitos en CONCEPT_DEPENDENCY_GRAPH |
| MasteryVoter | score ≥ 0.6 → approve |
| PrereqVoter | ¿PathModules inferiores completados? |
| ConsensusEngine (completo) | Regla de mayoría + pesos adaptativos |

### Ejemplo de situación de decisión

```
Caso #42:
Estudiante: s42
Curso: PRO201 - Fundamentos de Programación
Semana: 5
Etapa cognitiva: structured
Puntaje actual: 72/100
Conceptos dominados: variables, data_types, expressions, input_output, conditionals
Concepto actual: boolean_logic (prerrequisitos: expressions ✓, conditionals ✓)
Intentos en boolean_logic: 2 (fallo en operador AND vs OR)
Código más reciente:
  SI edad > 18 Y ingresos > 1000 ENTONCES
    ESCRIBIR "Aprobado"
  SINO
    ESCRIBIR "Rechazado"
  FIN_SI
  (Error: lógico - debe ser edad >= 18)

Decisión esperada (expertos): APROBAR con refuerzo en operadores de comparación
```

### Métricas específicas

| Métrica | Fórmula |
|---------|---------|
| **Precisión** | (VP + VN) / (VP + VN + FP + FN) |
| **Sensibilidad (recall)** | VP / (VP + FN) |
| **Especificidad** | VN / (VN + FP) |
| **F1-score** | 2 × (precisión × sensibilidad) / (precisión + sensibilidad) |
| **Exactitud por nivel de dificultad** | Precisión estratificada por: fácil (score > 75), medio (50-75), difícil (< 50) |
| **Área bajo la curva ROC (AUC)** | Para decisiones binarias approve/reject |
| **Precisión por tipo de error** | Tasa de acierto separada para: errores de sintaxis, lógica, semántica |

### Criterios de evaluación

- **SH4 aceptada si**: Precisión(ConsensusEngine) > Precisión(mejor_votante_individual) con prueba de McNemar p < 0.05
- **Aceptación parcial si**: ConsensusEngine iguala al mejor votante pero con menor varianza (más robusto)
- **Análisis adicional**: Matriz de confusión por votante para identificar complementariedad

### Matriz de confusión esperada (ejemplo)

```
Votante: CodeMasteryVoter
            Experto: Sí  No
Sistema Sí     23     7
Sistema No      8    62
Precisión: 0.85, F1: 0.75

Votante: ConsensusEngine
            Experto: Sí  No
Sistema Sí     28     3
Sistema No      3    66
Precisión: 0.94, F1: 0.90
```

---

## 7. Experimento E — Efecto del Aprendizaje Adaptativo (Longitudinal)

### Objetivo
Demostrar que el sistema swarm reduce la tasa de abandono y mejora la retención de conceptos de programación a lo largo de un semestre completo, comparado con un sistema no adaptativo.

### Hipótesis asociada
**SH5**: La adaptación continua del swarm reduce la tasa de abandono en ≥15% frente a ruta fija.

### Diseño
**Tipo**: Estudio longitudinal con 2 grupos paralelos, mediciones en 4 momentos.

### Protocolo

**Grupos** (mismos que Experimento A):
- G_swarm (n=30): Ruta adaptativa swarm
- G_fijo (n=30): Ruta secuencial fija

**Momentos de medición**:

| Momento | Semana | Instrumento |
|---------|--------|-------------|
| T0 | 0 | Pre-test PFPT + Cuestionario demográfico |
| T1 | 4 | Mini-test parcial (conceptos 1-6) |
| T2 | 8 | Post-test parcial + Cuestionario de carga cognitiva (NASA-TLX) |
| T3 | 16 | Post-test final + SUS + Cuestionario de motivación (IMMS) |

### Métricas específicas

| Métrica | Fórmula / Instrumento |
|---------|----------------------|
| **Tasa de abandono** | (inscritos - completaron) / inscritos × 100 |
| **Retención a 4 semanas** | Puntaje en T3 - puntaje en T2 (conceptos compartidos) |
| **Carga cognitiva** | NASA Raw-TLX (promedio de 6 dimensiones, 0-100) |
| **Motivación** | IMMS (Instructional Materials Motivation Survey): atención, relevancia, confianza, satisfacción |
| **Tiempo hasta primer abandono** | Días desde inicio hasta que el estudiante deja de acceder (>14 días sin actividad) |
| **Curva de aprendizaje por concepto** | Parámetros de la curva: tasa de acierto vs intentos (modelo power-law de Newell & Rosenbloom) |

### Análisis de curvas de aprendizaje

Para cada estudiante y cada concepto, modelar:

```
P(t) = a - b × t^(-c)
donde:
  P(t) = probabilidad de acierto en el intento t
  a = asíntota superior (dominio máximo)
  b = rango de mejora
  c = tasa de aprendizaje
```

Comparar parámetros entre G_swarm y G_fijo:
- `c_swarm > c_fijo` → aprendizaje más rápido
- `a_swarm > a_fijo` → mayor dominio final

### Criterios de evaluación

- **SH5 aceptada si**: Abandono(G_swarm) ≤ Abandono(G_fijo) - 15% con p < 0.05
  - Ejemplo: G_fijo abandono 40%, G_swarm ≤ 25%
- **Aceptación parcial si**: Diferencia ≥ 10% pero p < 0.10
- **Análisis secundario**: Supervivencia Kaplan-Meier con prueba log-rank

### Análisis de supervivencia

```python
from lifelines import KaplanMeierFitter

kmf_swarm = KaplanMeierFitter()
kmf_fijo = KaplanMeierFitter()

# Tiempo hasta abandono (días)
kmf_swarm.fit(durations_swarm, event_observed=abandono_swarm, label="Swarm")
kmf_fijo.fit(durations_fijo, event_observed=abandono_fijo, label="Fijo")

from lifelines.statistics import logrank_test
results = logrank_test(durations_swarm, durations_fijo,
                       abandono_swarm, abandono_fijo)
# p < 0.05 → diferencia significativa en supervivencia
```

---

## 8. Experimento F — Propagación Cognitiva en la Cadena de Agentes

### Objetivo
Demostrar que la etapa cognitiva detectada por `PedagogicalAgent` se propaga correctamente a través del swarm, influyendo en la selección de ruta (`AdaptiveAgent`), la evaluación de riesgo (`RiskAgent`) y la generación de contenido (`EvaluationAgent`).

### Hipótesis asociada
**SH6**: La etapa cognitiva detectada por el agente pedagógico predice significativamente la ruta seleccionada por el agente adaptativo.

### Diseño
**Tipo**: Experimento de rastreo causal con análisis de mediación.

### Protocolo

1. Generar 60 casos sintéticos (10 por cada etapa cognitiva × 6 etapas)
2. Para cada caso, ejecutar el swarm completo y registrar outputs de cada agente
3. Analizar la cadena causal: etapa_cognitiva → pathway → bloom_range → pace → risk_score → exercises

### Variables del modelo de mediación

```
Variable independiente (X): etapa cognitiva detectada por PedagogicalAgent
                               [pre_algorithmic, sequential, structured, modular, abstract, creative_computing]
                                    |
                                    ▼
Mediador 1 (M1): pathway seleccionado por AdaptiveAgent
                    [standard, accelerated, reinforced, visual_first]
                                    |
                                    ▼
Mediador 2 (M2): bloom_range ajustado
                    [ (1,1), (1,2), (2,3), (3,4), (4,5), (5,6) ]
                                    |
                                    ▼
Mediador 3 (M3): risk_score calculado por RiskAgent
                    [0.0 - 1.0]
                                    |
                                    ▼
Variable dependiente (Y): tipo de ejercicios generados por EvaluationAgent
                            [nivel Bloom de los ejercicios, cantidad]
```

### Métricas específicas

| Métrica | Fórmula |
|---------|---------|
| **Coeficiente de correlación etapa → pathway** | V de Cramér (variables categóricas ordinales) |
| **Efecto directo vs indirecto** | Descomposición de la mediación (bootstrapping, 5000 muestras) |
| **Proporción mediada** | Efecto indirecto / efecto total |
| **Concordancia etapa-bloom** | ¿Bloom_range(AdaptiveAgent) ⊆ Bloom_range(ProgrammingStage)? |
| **Fidelidad de propagación** | ¿La información de PedagogicalAgent llega íntegra a EvaluationAgent? Medir pérdida de información |

### Matriz de confusión etapa → pathway esperada

| Etapa | Standard | Accelerated | Reinforced | Visual First |
|-------|----------|-------------|------------|--------------|
| PRE_ALGORITHMIC | **0.80** | 0.00 | 0.10 | 0.10 |
| SEQUENTIAL | **0.60** | 0.05 | 0.20 | 0.15 |
| STRUCTURED | 0.30 | 0.20 | 0.30 | 0.20 |
| MODULAR | 0.20 | **0.40** | 0.20 | 0.20 |
| ABSTRACT | 0.10 | **0.60** | 0.10 | 0.20 |
| CREATIVE_COMPUTING | 0.05 | **0.70** | 0.05 | 0.20 |

### Criterios de evaluación

- **SH6 aceptada si**: V de Cramér ≥ 0.5 (asociación fuerte entre etapa y pathway) y proporción mediada ≥ 0.3
- **Aceptación parcial si**: V de Cramér ≥ 0.3 pero mediación no significativa
- **Aceptación rechazada si**: V de Cramér < 0.2 (etapa no influye en ruta)

---

## 9. Experimento G — Efectividad de la Memoria Compartida

### Objetivo
Demostrar que el `SharedMemoryStore` reduce la divergencia entre agentes, mejora la coherencia de las decisiones y evita decisiones contradictorias.

### Hipótesis asociada
**SH7**: La memoria compartida reduce la divergencia entre agentes en ≥30% comparado con agentes aislados.

### Diseño
**Tipo**: Experimento intra-sujeto (within-subject) con 2 condiciones.

### Protocolo

Ejecutar el swarm sobre 40 casos sintéticos en 2 condiciones:

| Condición | Descripción |
|-----------|-------------|
| **SM_ON** | SharedMemoryStore habilitado. Agentes publican y consultan observaciones. Patrones detectados por `PatternDetector`. Conflictos resueltos por `resolve_conflicts()`. |
| **SM_OFF** | SharedMemoryStore deshabilitado. Cada agente opera con su propio estado interno. No hay publicación ni consulta entre agentes. |

### Métricas específicas

| Métrica | Fórmula | Descripción |
|---------|---------|-------------|
| **Divergencia entre agentes (DA)** | `DA = 1 - (2 × acuerdos / (acuerdos + desacuerdos))` para decisiones pareadas | 0 = completo acuerdo, 1 = completo desacuerdo |
| **Tasa de contradicción** | `contradicciones / total_decisiones_pareadas` × 100 | Decisiones opuestas entre agentes sobre mismo concepto |
| **Tiempo de resolución de conflictos** | ms desde que se publica el primer valor contradictorio hasta que `resolve_conflicts()` finaliza | SharedMemory timestamps |
| **Precisión con memoria** | `(SM_ON_accuracy / SM_OFF_accuracy) - 1` × 100 | Mejora relativa |
| **Cobertura informacional** | `observaciones_unicas / total_observaciones_posibles` | Qué tan completa es la información |
| **Redundancia** | `1 - (observaciones_unicas / total_observaciones)` | Grado de repetición útil |

### Análisis de contradicciones

Para cada caso, identificar pares de agentes que producen decisiones contradictorias:

```
Caso #18 (SM_OFF):
  PedagogicalAgent: mastered_concepts = [variables, expressions, conditionals]
  AdaptiveAgent: concept_sequence = [variables, data_types, expressions, conditionals, loops]
  Riesgo: NO se detecta que data_types no está en mastered → posible contradicción

Caso #18 (SM_ON):
  PedagogicalAgent → shared memory: mastered_concepts = [variables, expressions, conditionals]
  AdaptiveAgent ← shared memory: mastered_concepts = [variables, expressions, conditionals]
  AdaptiveAgent: concept_sequence = [variables, data_types, expressions, conditionals, loops]
  → data_types reconocido como nuevo, se genera refuerzo ✓
```

### Criterios de evaluación

- **SH7 aceptada si**: DA(SM_ON) ≤ DA(SM_OFF) × 0.7 (reducción ≥30%) y tasa de contradicción reduce en ≥40%
- **Aceptación parcial si**: Reducción de divergencia ≥15% pero <30%
- **Rechazo si**: No hay diferencia significativa o SM_ON empeora la divergencia

### Análisis específico

```python
# Datos pareados: 40 casos × 2 condiciones
from scipy.stats import wilcoxon

divergencias_on = [...]  # DA por caso con SM_ON
divergencias_off = [...]  # DA por caso con SM_OFF

stat, p = wilcoxon(divergencias_on, divergencias_off, alternative='less')
# p < 0.05 → SM_ON reduce significativamente la divergencia

mejora = (np.mean(divergencias_off) - np.mean(divergencias_on)) / np.mean(divergencias_off) * 100
```

---

## 10. Análisis Estadístico y Criterios de Evaluación

### Resumen de pruebas estadísticas por experimento

| Exp | Variable dependiente | Tipo | Prueba | Tamaño del efecto |
|-----|---------------------|------|--------|-------------------|
| A | Ganancia de Hake g | Continua | ANCOVA (grupo + pre-test) | d de Cohen, η² parcial |
| B | Consistencia interna Ci | Continua (medidas repetidas) | ANOVA medidas repetidas | η² parcial |
| C | Tasa de éxito | Proporción | χ² o Fisher exacto | V de Cramér |
| D | Precisión de consenso | Proporción pareada | McNemar | g de Test de McNemar |
| E | Tasa de abandono | Proporción (tiempo hasta evento) | Log-rank (Kaplan-Meier) | Hazard ratio |
| F | Asociación etapa→ruta | Categórica ordinal | V de Cramér + mediación bootstrapping | V de Cramér |
| G | Divergencia entre agentes | Continua pareada | Wilcoxon signed-rank | r de correlación biserial |

### Corrección por comparaciones múltiples

- Aplicar corrección de Bonferroni-Holm para los 7 experimentos
- α_ajustado para el experimento más significativo: 0.05 / 7 = 0.0071
- Reportar tanto p-valores crudos como ajustados

### Criterios de aceptación de tesis

| Nivel | Requisito |
|-------|-----------|
| **TESIS APROBADA** | SH1, SH3, SH4, SH7 aceptadas (4 de 7, incluyendo la principal) |
| **APROBADA CON DISTINCIÓN** | SH1-SH7 aceptadas (todas) o SH1-SH4 aceptadas con d > 0.8 |
| **APROBADA CON MENCIÓN HONORÍFICA** | SH1-SH7 aceptadas + efecto grande (d > 0.8, η² > 0.14) en AL MENOS 5 experimentos |
| **APROBACIÓN PARCIAL** | SH1 aceptada + al menos 2 adicionales |

---

## 11. Instrumentos de Recolección

### Instrumentos digitales (integrados en la plataforma)

| Instrumento | Descripción | Output |
|-------------|-------------|--------|
| **Logger de eventos swarm** | Captura todos los eventos del `SwarmEventBus` | JSON Lines |
| **Shared Memory Snapshot** | Estado completo del `SharedMemoryStore` en cada ciclo | JSON |
| **SwarmActivationMetrics** | Métricas agregadas por activación: duración, éxito, anomalías | JSON |
| **HealthSnapshot** | Reporte de salud de `SwarmDiagnosticsEngine` | JSON |
| **Registro de interacción** | Cada ejercicio, respuesta, hint solicitado, tiempo por sesión | SQL + JSON |

### Instrumentos de evaluación humana

| Instrumento | Cuándo | Qué mide |
|-------------|--------|----------|
| **PFPT** (Programming Fundamentals Pretest/Posttest) | T0, T3 | Conocimiento de 26 conceptos |
| **SUS** (System Usability Scale) | T3 | Usabilidad del sistema (0-100) |
| **NASA Raw-TLX** | T2 | Carga cognitiva (6 dimensiones) |
| **IMMS** (Instructional Materials Motivation Survey) | T3 | Motivación: atención, relevancia, confianza, satisfacción |
| **Rúbrica de coherencia de ruta** | Evaluación por expertos | Calidad de la ruta generada (1-5) |
| **Cuestionario demográfico** | T0 | Edad, género, experiencia previa, carrera |

### Formato de datos para análisis

```python
# Estructura de datos unificada (DataFrame principal)
columnas = [
    "student_id", "grupo", "semana",
    "pre_test_score", "post_test_score", "g_hake",
    "etapa_cognitiva", "pathway", "bloom_range",
    "conceptos_dominados", "conceptos_debiles",
    "risk_score", "risk_level",
    "ejercicios_completados", "tasa_acierto",
    "tiempo_total", "abandono", "sesiones",
    "sus_score", "tlx_score", "imms_score",
    "divergencia_agentes", "contradicciones",
    "tiempo_recuperacion", "fallos_inducidos"
]
```

---

## 12. Plan de Reproducibilidad y Open Science

### Repositorio de experimentos
Todos los scripts, datos anonimizados y análisis deben publicarse en:

```
experimentos/
├── 01_adaptacion/
│   ├── generate_cases.py        # Generación de casos sintéticos
│   ├── run_experiment.py        # Ejecuta swarm sobre casos
│   ├── analyze_results.py       # ANCOVA, gráficos
│   └── data/                    # Outputs (CSV, JSON)
├── 02_coordinacion/
│   ├── ...
├── 03_resiliencia/
│   ├── inject_faults.py         # Inyección programática de fallos
│   └── ...
├── 04_consenso/
│   ├── ground_truth_experts.csv  # 100 casos etiquetados por expertos
│   └── ...
├── 05_longitudinal/
│   ├── ...
├── 06_propagacion/
│   ├── mediation_analysis.py    # Modelo de mediación
│   └── ...
├── 07_memoria_compartida/
│   ├── run_without_memory.py    # Modo SM_OFF
│   └── ...
├── shared/
│   ├── metrics.py               # Definiciones de métricas compartidas
│   ├── statistical_tests.py     # Funciones de análisis reutilizables
│   ├── synthetic_profiles.py    # Generador de perfiles sintéticos
│   └── visualization.py         # Gráficos estandarizados
└── results/
    ├── experiment_summary.tex    # Tabla resumen para la tesis
    └── figures/                  # Figuras publicables
```

### Semilla de aleatoriedad
Cada experimento debe fijar `random.seed(42)` y `np.random.seed(42)` para garantizar reproducibilidad exacta.

### Requisitos de software

```
Python ≥ 3.11
pandas, numpy, scipy, statsmodels, scikit-learn
lifelines (análisis de supervivencia)
pytest (validación de experimentos)
matplotlib, seaborn (visualización)
Jupyter Lab (análisis interactivo)
openpyxl (exportación a Excel para revisores)
```

### Criterios de reproducibilidad

1. **Determinismo**: Misma semilla → mismos resultados exactos
2. **Portabilidad**: Docker o conda environment con dependencias fijas
3. **Automatización**: `python run_all_experiments.py --seed 42` ejecuta todo
4. **Validación**: Tests unitarios para cada métrica: `pytest tests/experiments/`
5. **Auditabilidad**: Cada resultado incluye hash del código fuente que lo generó

---

## Apéndice A: Script de validación de integridad experimental

```python
#!/usr/bin/env python3
"""Valida que todos los experimentos estén correctamente configurados."""

import pytest

def test_experimento_A_tamano_muestra():
    assert n_swarm >= 30 and n_fijo >= 30, "Muestra insuficiente"

def test_experimento_B_casos_sinteticos():
    assert len(perfiles) == 50, "Deben ser 50 perfiles"

def test_experimento_C_escenarios_fallo():
    assert len(escenarios_fallo) >= 7, "Mínimo 7 escenarios de fallo"

def test_experimento_D_ground_truth():
    assert len(ground_truth) == 100, "Deben ser 100 casos etiquetados"
    assert kappa_fleiss >= 0.70, "Acuerdo entre expertos insuficiente"

def test_experimento_E_mediciones_longitudinales():
    assert len(momentos_medicion) == 4, "Mínimo 4 momentos T0-T3"

def test_experimento_F_casos_por_etapa():
    assert all(len(casos_por_etapa[e]) == 10 for e in etapas), "10 casos por etapa"

def test_experimento_G_condiciones_memoria():
    assert "SM_ON" in condiciones and "SM_OFF" in condiciones
```

---

## Apéndice B: Glosario de términos

| Término | Definición |
|---------|------------|
| Ganancia normalizada de Hake (g) | (post% - pre%) / (100% - pre%). Mide cuánto del potencial de mejora se logró. |
| d de Cohen | Tamaño del efecto: 0.2 = pequeño, 0.5 = mediano, 0.8 = grande |
| η² parcial | Proporción de varianza explicada: 0.01 = pequeño, 0.06 = mediano, 0.14 = grande |
| V de Cramér | Asociación entre variables categóricas: 0.1 = débil, 0.3 = moderada, 0.5 = fuerte |
| Hazard ratio | Riesgo relativo de abandono entre grupos |
| Kappa de Fleiss | Acuerdo entre múltiples evaluadores (>3): ≥0.70 = acuerdo sustancial |
| NASA-TLX | Índice de carga de trabajo: demanda mental, física, temporal, esfuerzo, desempeño, frustración |
| IMMS | Instructional Materials Motivation Survey: 36 ítems, 4 dimensiones (ARCS) |
| EWMA | Exponentially Weighted Moving Average: promedio móvil con ponderación exponencial |
| Kahn's algorithm | Ordenamiento topológico de DAG usado por ProgrammingPathGenerator |
| Bloom range | Rango de niveles de Bloom (1-6) que un estudiante puede abordar en su etapa actual |
| RO (RTO) | Recovery Time Objective: tiempo máximo aceptable para recuperarse de un fallo |
