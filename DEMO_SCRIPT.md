# DEMO SCRIPT — UPAO-MAS-EDU v1.0.0
## Sustentación Académica | 8–12 minutos | Sin improvisación

---

## CONDICIONES IDEALES

### Escenario
- **Curso:** Programación I (PRO201) — Ciclo 2, Ingeniería de Sistemas
- **Tema:** Estructuras de Control en Python (`if`/`else`, `for`, `while`)
- **Estudiante:** "Carlos Mendoza" — ciclo 3, estilo visual-kinaesthetic, ritmo lento, ansiedad diagnosticada en programación
- **Objetivos:** (1) Comprender condicionales anidados (Bloom 2), (2) Implementar bucles con propósito (Bloom 3), (3) Depurar errores lógicos (Bloom 4)

### Stack abierto
```
Frontend: http://localhost:5173
Backend:  http://localhost:8000
Docs:     http://localhost:8000/docs
Dashboard: http://localhost:8000/api/observability/dashboard
```

### Usuarios cargados (seed.py)
| Rol | Email | Password |
|-----|-------|----------|
| Docente | docente@upao.edu | docente123 |
| Estudiante | estudiante.c3@upao.edu | estudiante123 |

---

## SCRIPT PASO A PASO

> **Convención:** 🗣️ = lo que dices en voz alta | 💻 = lo que haces en pantalla | ⏱ = tiempo estimado

---

### [0] PRE-ROLL — Validación de Entorno (30s)

**Propósito:** Demostrar reproducibilidad — el sistema se auto-valida antes de cualquier operación.

> 💻 Abre terminal. Ejecuta:

```bash
python backend/scripts/validate_environment.py
```

> 💻 Muestra: ✅ 14 checks passed (Python 3.12, DB conectada, API keys presentes, dependencias correctas)

> 🗣️ _"Antes de cualquier operación, el sistema ejecuta 14 validaciones de entorno. Esto garantiza que la demo es reproducible: mismo código, mismas dependencias, mismo comportamiento. Es la base de la ingeniería de software responsable."_

---

### [1] Docente Define Temática Semanal (1 min)

**Propósito:** Mostrar entrada única del docente — el sistema hace el resto.

> 💻 Login como **docente@upao.edu**
> 💻 Navega a "Mis Cursos" → "Programación I (PRO201)" → "Orquestación Semanal"
> 💻 Completa el formulario:
```
Tema:            "Estructuras de Control en Python"
Objetivos:       "Comprender condicionales anidados",
                 "Implementar bucles for y while con propósito",
                 "Depurar errores lógicos en estructuras de control"
Intención:       "Que el estudiante pueda escribir programas que tomen
                  decisiones y repitan acciones de manera estructurada"
Estructura:      "Condicionales simples → Anidados → Bucles → Depuración"
Sílabo:          "PRO201: Semana 7 — Estructuras de Control"
Línea semanal:   "Semana 7: De condicionales a iteración controlada"
```

> 🗣️ _"El docente define SOLO el qué: tema, objetivos, intención pedagógica. No necesita diseñar actividades, buscar recursos, adaptar contenido. Eso lo hace el swarm. Un solo formulario, 30 segundos."_

> ⏱ 1:00

---

### [2] Swarm Investiga Contenido (1 min)

**Propósito:** ResearchAgent + Tavily buscan contenido actualizado automáticamente.

> 💻 En otra terminal, loguea el proceso:

```bash
curl -X POST http://localhost:8000/api/orchestrate/research \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(TOKEN)" \
  -d '{
    "topic": "Estructuras de Control en Python",
    "learning_objectives": ["Comprender condicionales anidados",
      "Implementar bucles for y while con propósito",
      "Depurar errores lógicos en estructuras de control"],
    "pedagogical_intention": "Que el estudiante pueda escribir programas
      que tomen decisiones y repitan acciones de manera estructurada",
    "syllabus": "PRO201: Semana 7 — Estructuras de Control"
  }' | python -m json.tool | head -40
```

> 🗣️ _"El ResearchAgent invoca Tavily Search API con 3 consultas paralelas: ejemplos reales, aplicaciones educativas, analogías pedagógicas. Tavily devuelve contenido fresco de la web — no usamos datos stale. Si Tavily falla, el agente degrada gracefulmente a generación LLM."_

> ⏱ 1:00

---

### [3] Retrieval Pedagógico (30s)

**Propósito:** Los hallazgos crudos se transforman en contenido pedagógico estructurado.

> 🗣️ _"El StructuralPedagogicalAgent toma los hallazgos del ResearchAgent y los organiza en 6 secciones pedagógicas con progresión Bloom: Introducción (Bloom 1) → Explicación Conceptual (Bloom 2) → Ejemplo (Bloom 3) → Aplicación Práctica (Bloom 4) → Caso Real (Bloom 5) → Evaluación (Bloom 6). Cada sección tiene duración estimada, nivel cognitivo y modalidad recomendada."_

> 💻 Muestra pantalla: resultado con estructura pedagógica:

```json
{
  "sections": [
    {"title": "¿Qué son las estructuras de control?",
     "bloom_level": 1, "modality": "text"},
    {"title": "Condicionales: if, else, elif",
     "bloom_level": 2, "modality": "interactive"},
    {"title": "Depuración de errores lógicos",
     "bloom_level": 4, "modality": "interactive"}
  ]
}
```

> ⏱ 0:30

---

### [4] Tavily Sources (30s)

**Propósito:** Transparencia total — mostrar de dónde viene cada hallazgo.

> 🗣️ _"Cada hallazgo del ResearchAgent preserva su fuente original. El docente y el estudiante pueden verificar la procedencia de cada ejemplo, analogía o referencia. Esto es trazabilidad pedagógica: no hay contenido generado sin atribución."_

> 💻 Muestra respuesta de `/api/orchestrate/research` con campos `source`, `relevance`, `category`.

> ⏱ 0:30

---

### [5] Misconceptions Detection (45s)

**Propósito:** AdaptiveLearningAgent detecta conceptos erróneos del estudiante.

> 🗣️ _"El AdaptiveLearningAgent analiza el perfil del estudiante — su test diagnóstico, errores previos, ritmo de aprendizaje. Detecta conceptos erróneos específicos: por ejemplo, que el estudiante confunde `=` con `==`, o cree que `else` es obligatorio después de `if`. Estos misconceptions guían la adaptación."_

> 💻 Muestra perfil del estudiante:

```
Estudiante: Carlos Mendoza (C3)
Dificultades detectadas:
  - Confunde = (asignación) con == (comparación) → frecuencia: 4 errores
  - No usa elif, escribe if anidados innecesarios
  - Cree que break solo funciona en if
Ritmo: lento | Estilo: visual-kinaesthetic | Ansiedad: alta en programación
```

> ⏱ 0:45

---

### [6] Deliberación Multiagente (1 min)

**Propósito:** 7 agentes colaboran/deliberan para generar contenido adaptado.

> 🗣️ _"Aquí ocurre la magia del swarm. Siete agentes especializados ejecutan en pipeline orquestado: Research investiga, StructuralPedagogical estructura, AdaptiveLearning adapta al perfil, MultimodalPlanning decide formatos, PromptEngineering genera prompts especializados, ConsistencyAgent verifica coherencia, y ConsensusMediator consolida."_

> 💻 Ejecuta orquestación completa:

```bash
curl -X POST http://localhost:8000/api/orchestrate/full \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(TOKEN)" \
  -d '{
    "topic": "Estructuras de Control en Python",
    "learning_objectives": [
      "Comprender condicionales anidados",
      "Implementar bucles for y while",
      "Depurar errores lógicos"
    ],
    "pedagogical_intention": "Que el estudiante pueda escribir
      programas estructurados",
    "student_id": "ID_DEL_ESTUDIANTE"
  }' | python -m json.tool | grep -A5 '"execution_summary"'
```

> 💻 Muestra las fases completadas y sus timings:

```json
"phase_timings_ms": {
  "research": 3420,
  "pedagogical": 1250,
  "adaptive": 890,
  "multimodal_planning": 650,
  "prompt_engineering": 2100,
  "consistency": 780,
  "consensus_mediator": 340
}
```

> 🗣️ _"Cada agente ejecuta en su especialidad. La comunicación entre fases usa SharedMemoryStore persistido en PostgreSQL — trazabilidad completa de qué agente produjo qué, con TTL de propagación y prevención de loops (9 fases de lifecycle)."_

> ⏱ 1:00

---

### [7] Consensus (1 min)

**Propósito:** 4 voters deterministas evalúan y votan la ruta generada.

> 🗣️ _"El ConsensusEngine ejecuta 4 voters deterministas: MasteryVoter evalúa si el contenido cubre los niveles de dominio necesarios, PrereqVoter verifica prerrequisitos, SequenceVoter evalúa el orden pedagógico, TimeVoter estima si la duración es adecuada. Cada voter devuelve approve/reject/abstain con peso y confianza."_

> 💻 Abre observability dashboard en navegador:

```
http://localhost:8000/api/observability/dashboard
```

> 💻 Señala la sección "Consensus": approval rate, rejection reasons, voter stats.

> 🗣️ _"El consenso es determinista — mismos inputs producen mismo resultado. No hay aleatoriedad. Esto es fundamental para reproducibilidad académica y para que el docente entienda POR QUÉ se tomó cada decisión pedagógica."_

> ⏱ 1:00

---

### [8] Adaptación Pedagógica (45s)

**Propósito:** El contenido se adapta al perfil del estudiante en tiempo real.

> 🗣️ _"Basado en el perfil de Carlos — visual, ritmo lento, ansiedad — el AdaptiveLearningAgent ajusta: nivel de dificultad a beginner, profundidad de explicación a detailed, frecuencia de refuerzo a high, y secuencia de conceptos priorizando ejemplos visuales interactivos antes que teoría abstracta."_

> 💻 Muestra plan de adaptación generado:

```json
{
  "difficulty_level": "beginner",
  "pace_adjustment": "slow",
  "bloom_range": [1, 4],
  "explanation_depth": "detailed",
  "reinforcement_frequency": "high",
  "modality_preferences": ["visual", "interactive"]
}
```

> 🗣️ _"El docente no configuró nada de esto. El sistema lo inferió del test diagnóstico, historial de errores y patrones de aprendizaje del estudiante."_

> ⏱ 0:45

---

### [9] Prompts Multimodales (45s)

**Propósito:** Generación de prompts especializados para cada modalidad.

> 🗣️ _"El PromptEngineeringAgent genera prompts especializados para cada sección: prompt narrativo para la introducción, prompt visual para diagramas de flujo de control, prompt interactivo para ejercicios de depuración, prompt cinematográfico para el caso real. Cada prompt está optimizado para un modelo específico."_

> 💻 Muestra ejemplos de prompts generados:

```json
{
  "prompts": [
    {"type": "visual", "target_section": "Condicionales",
     "content": "Genera un diagrama de flujo interactivo...",
     "model_recommendation": "DALL-E 3"},
    {"type": "interactive", "target_section": "Depuración",
     "content": "Crea un ejercicio donde el estudiante...",
     "model_recommendation": "gpt-4o"}
  ]
}
```

> ⏱ 0:45

---

### [10] Consistency Validation (30s)

**Propósito:** ConsistencyAgent verifica coherencia narrativa y pedagógica.

> 🗣️ _"El ConsistencyAgent actúa como revisor de calidad. Verifica coherencia narrativa (el hilo conductor se mantiene), consistencia pedagógica (no hay saltos de Bloom injustificados), consistencia multimodal (texto e imagen no se contradicen), y continuidad visual. Si detecta problemas, los reporta con severidad y sugerencia."_

> 💻 Muestra reporte de consistencia:

```json
{
  "passed": true,
  "narrative_coherence_score": 0.94,
  "pedagogical_progression_score": 0.97,
  "multimodal_consistency_score": 0.91
}
```

> ⏱ 0:30

---

### [11] Sandbox Validation (30s)

**Propósito:** Validación de contenido generado antes de entrega al estudiante.

> 🗣️ _"Antes de que cualquier contenido llegue al estudiante, pasa por validación: los prompts se verifican contra contenido prohibido, los ejercicios se validan sintácticamente (código Python compila), las referencias se chequean contra fuentes conocidas."_

> 💻 Muestra el reporte de sandbox validation:

```
Sandbox Validation Report:
  - Code snippets: 3/3 compile OK
  - Prompts: 5/5 pass content safety
  - References: 4/4 verified
  - Score: 100%
```

> ⏱ 0:30

---

### [12] Explainability (45s)

**Propósito:** Cada decisión del sistema es explicable y trazable.

> 🗣️ _"No es una caja negra. Cada decisión pedagógica tiene un rastro: qué agente la produjo, qué datos usó, qué votos la respaldan, qué alternativas existían. El docente puede preguntar '¿por qué se recomendó esta actividad?' y el sistema responde con la cadena completa de razonamiento."_

> 💻 Abre timeline de decisiones:

```bash
curl http://localhost:8000/api/observability/timeline?student_id=ID_ESTUDIANTE
```

> 💻 Muestra entries del timeline con agent, decision, reasoning, confidence.

> 🗣️ _"Esto es crucial para sustentación académica: no solo mostramos que funciona, sino que podemos explicar cómo y por qué."_

> ⏱ 0:45

---

### [13] Replay Cognitivo (1:30)

**Propósito:** Visualizar la evolución pedagógica completa — 10 dimensiones cognitivas en tiempo real vía SSE con explicabilidad paso a paso.

> 🗣️ _"Cada sesión de orquestación queda registrada en el ReplayEngine: qué cambió, por qué cambió, qué señal lo causó, qué agente tomó la decisión y qué evidencia se usó. 10 tracks cognitivos: evolución Bloom, misconceptions, pacing, adaptación multimodal, confianza, consenso, narrativa, prompts, carga cognitiva y progresión semanal."_

> 💻 Abre el dashboard de replay cognitivo:
>
> ```
> http://localhost:8000/api/replay/dashboard
> ```
>
> 💻 Navega las 4 pestañas:
>
> **1. Evolución** — Muestra los tracks en tiempo real:
> - Gráfico de barras Bloom con distribución por nivel (Recordar → Crear)
> - Línea de confianza de voters
> - Doughnut de distribución multimodal
> - Barras de tipos de prompts
> - Línea de carga cognitiva estimada
> - Badges de pacing y misconceptions detectadas
>
> **2. Razonamiento** — Timeline vertical con cada frame del pipeline:
> - Cada paso muestra: agente (badge colorido), razonamiento, señal causal, decisión
> - Expandible para ver evidencia cruda
> - Scroll automático al último frame
>
> **3. Narrativa** — Hilo narrativo, score de coherencia, eventos de memoria
>
> **4. Consenso** — Línea de confianza de consenso, badge unánime/mayoría, doughnut de distribución

> 🗣️ _"Esto es lo que hace académicamente robusto al sistema: no solo ejecuta, sino que explica. Cada decisión pedagógica tiene trazabilidad completa. El jurado puede ver exactamente cómo y por qué el sistema adaptó el contenido para cada estudiante."_

> 💻 Comandos de respaldo:
>
> ```bash
> # Listar sesiones de replay
> curl -s http://localhost:8000/api/replay/sessions | python -m json.tool
>
> # Ver tracks cognitivos
> curl -s http://localhost:8000/api/replay/cognitive | python -m json.tool
>
> # Frames de una sesión específica
> curl -s http://localhost:8000/api/replay/frames/SESSION_ID | python -m json.tool
> ```

> ⏱ 1:30

---

### [14] Observabilidad SSE (30s)

**Propósito:** Monitoreo en tiempo real del sistema multiagente.

> 🗣️ _"Cerramos la demo mostrando el sistema vivo. El observability dashboard se actualiza en tiempo real vía SSE: métricas de consenso, anomalías detectadas, latencia de voters, cadenas de propagación activas."_

> 💻 Abre el dashboard embebido:

```
http://localhost:8000/api/observability/dashboard
```

> 🗣️ _"4 pestañas: Overview con consenso, activaciones y anomalías; Consensus con stats de voters y razones de rechazo; Resilience con circuit breakers y recovery rate; Propagation con cadenas activas. Todo en tiempo real, sin recargar la página."_

> ⏱ 0:30

---

### [CIERRE] Benchmark Final (30s)

> 🗣️ _"Para validar que el sistema funciona sistemáticamente, no solo en un caso ideal — ejecutamos un benchmark reproducible de 6 condiciones × 50 escenarios × 5 runs. 1500 evaluaciones que comparan swarm completo contra ablaciones. Los resultados demuestran que el swarm mejora pass@1 en 2%, reduce alucinaciones 21.4%, y aumenta personalización 60% — y todo es reproducible con un solo comando."_

> 💻 Muestra resultados del benchmark:

```bash
python backend/scripts/run_academic_benchmark.py --scenarios 50 --runs 5 --output /tmp/demo_benchmark
```

> 🗣️ _"UPAO-MAS-EDU v1.0.0: un sistema multiagente pedagógico, determinista, explicable y reproducible. Listo para producción académica."_

> ⏱ 0:30

---

## RESUMEN DE TIEMPOS

| Paso | Duración | Acumulado |
|------|----------|-----------|
| 0. Pre-roll | 30s | 0:30 |
| 1. Docente define | 1:00 | 1:30 |
| 2. Swarm investiga | 1:00 | 2:30 |
| 3. Retrieval pedagógico | 0:30 | 3:00 |
| 4. Tavily sources | 0:30 | 3:30 |
| 5. Misconceptions | 0:45 | 4:15 |
| 6. Deliberación multiagente | 1:00 | 5:15 |
| 7. Consensus | 1:00 | 6:15 |
| 8. Adaptación pedagógica | 0:45 | 7:00 |
| 9. Prompts multimodales | 0:45 | 7:45 |
| 10. Consistency | 0:30 | 8:15 |
| 11. Sandbox validation | 0:30 | 8:45 |
| 12. Explainability | 0:45 | 9:30 |
| 13. Replay cognitivo | 1:30 | 11:00 |
| 14. Observabilidad SSE | 0:30 | 11:30 |
| Cierre. Benchmark | 0:30 | 12:00 |

**Total: ~11-12 minutos** (margen para transiciones = 8-12 min)

---

## NARRATIVA TRANSVERSAL (para hilvanar la demo)

**Problema:** La educación personalizada no escala — un docente con 30+ estudiantes no puede adaptar contenido a cada perfil individual.

**Solución multiagente:** En lugar de un monolito, especializamos. 7 agentes, cada uno experto en una dimensión pedagógica, colaboran como un equipo docente ideal.

**Por qué retrieval:** El conocimiento no es estático. Tavily trae contenido fresco. Pero retrieval solo no basta — hay que estructurarlo pedagógicamente.

**Por qué memoria:** El sistema aprende del estudiante con cada interacción. No empieza de cero cada sesión.

**Por qué explainability:** En educación, no basta con dar la respuesta correcta. Hay que explicar el razonamiento. Para el estudiante y para el docente.

**Por qué sandbox:** El contenido generado por IA puede ser incorrecto o inapropiado. Validamos antes de entregar.

**Por qué benchmarking:** La ingeniería de software académico requiere evidencia. No mostramos solo un demo bonito — mostramos 1500 evaluaciones controladas.

---

## IDEAL DATASET / STUDENT / SCENARIO / REPLAY / BENCHMARK

### Dataset Ideal
- **Curso:** Programación I (PRO201) — Ingeniería de Sistemas, Ciclo 2
- **Tema semanal:** 7 semanas de estructuras de control progresando de condicionales a recursión
- **Recursos:** 3 videos, 2 PDFs, 1 repositorio GitHub con ejercicios
- **Evaluaciones:** 1 diagnóstica (12 preguntas), 2 formativas, 1 sumativa

### Estudiante Ideal
- **Nombre:** Carlos Mendoza
- **Ciclo:** 3 (repitió Programación I, cambió de metodología)
- **Estilo:** Visual-Kinaesthetic (80% visual, 60% kinestésico)
- **Ritmo:** Lento (necesita 2x tiempo promedio)
- **Ansiedad:** Alta con evaluación de código (registrada en test diagnóstico)
- **Fortalezas:** Lógica matemática, trabajo en equipo
- **Debilidades:** Sintaxis Python, depuración, confunde = con ==

### Escenario Ideal
- **Setup:**
  1. Docente define tema semanal (Estructuras de Control)
  2. Swarm investiga y adapta para Carlos
  3. Se genera ruta con 6 secciones, priorizando interactividad visual
  4. Carlos interactúa con tutor streaming, recibe explicaciones detalladas
  5. Sistema detecta patrón de error en = vs == y refuerza con ejercicio específico
  6. Evaluación adaptativa ajusta dificultad basada en progreso

### Replay Ideal
- **Seed:** 42 (benchmark base)
- **Condiciones:** swarm_full (mostrar máxima capacidad)
- **Escenario:** scn_3c84d1760475 (el del benchmark, con biases de adaptación)
- **Replay:**
  - `python scripts/run_academic_benchmark.py --conditions swarm_full --scenarios 1 --runs 1`

### Benchmark Ideal
- **Comando:** `python scripts/run_academic_benchmark.py --scenarios 50 --runs 5 --output /tmp/demo_benchmark`
- **Qué mostrar durante ejecución:**
  1. Condiciones ejecutándose (progreso)
  2. Tabla comparativa de resultados
  3. Gráfico de reducción de alucinaciones
  4. Tabla estadística con Mann-Whitney U significativo
