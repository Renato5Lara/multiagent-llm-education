# Especificación — La Misión Activa del Estudiante

> Primer agregado del dominio de la experiencia adaptativa.
> Cierra las Auditorías I–III (continuidad del aprendizaje) y gobierna el Sprint 1.
> Esto es una especificación de dominio: no describe tablas, endpoints ni componentes.

---

## 1. ¿Qué es una misión?

Una **misión** es la unidad de aprendizaje adaptativo del recorrido del estudiante
(hoy: un módulo de Fundamentos de la Programación). Tiene tres estados de dominio:

```
DISPONIBLE  →  ACTIVA  →  COMPLETADA
```

La **misión activa** es el proceso vivo entre "disponible" y "completada".
Es donde ocurre toda la inteligencia del sistema — y por eso es la única
parte del dominio que hoy no estaba modelada.

**Invariante central (unidad indivisible):** una misión activa no existe sin sus
tres componentes, que nacen juntos y se invalidan juntos:

1. **Adaptación** — qué experiencia le generó el sistema (snapshot de orquestación).
2. **Posición** — dónde va el estudiante dentro de esa experiencia (cursor).
3. **Evidencia** — por qué el sistema decidió lo que decidió (puntero `session_id`
   hacia la cadena de trazas, que ya se persiste).

Un cursor sin su adaptación no significa nada; una adaptación sin evidencia
no es defendible ante el jurado; evidencia sin adaptación es huérfana.

## 2. ¿Cuándo inicia?

Una misión pasa de DISPONIBLE a ACTIVA **la primera vez** que el estudiante entra
y el sistema genera su adaptación (orquestación del swarm). Ese evento crea la
unidad completa: snapshot + cursor en paso 0 + puntero de evidencia.

**Volver a entrar no inicia nada: reabre.** Recargar la página, volver al
Dashboard, cerrar el navegador o regresar mañana son eventos de navegación,
no eventos de dominio. La misión activa les sobrevive a todos.

La fase Engage es la apertura de la misión activa y conserva su sesión propia
(`EngagementSession`), subordinada e intacta: ya cumple este contrato para su fase.

## 3. ¿Qué estado conserva?

Exactamente el Contrato de Persistencia (Auditoría II):

| Conserva | Contenido |
|---|---|
| Adaptación | Snapshot completo del contenido orquestado, tal como se mostró |
| Puntero de evidencia | `session_id` de la deliberación que lo produjo |
| Cursor | Paso actual + pasos completados |
| Huellas del estudiante | Nivel de conocimiento declarado, hipótesis, respuestas por paso |
| Hechos históricos | Modalidad con la que se construyó, timestamps, causa de cada intento |

Todo lo demás **se reconstruye** (estructura del journey, XP, decisión adaptativa,
fase de la UI — funciones puras de lo anterior) **o muere** (animaciones, teatro
de espera). Nada se copia de otra entidad: la modalidad vigente, el perfil y el
diagnóstico siguen teniendo un solo dueño.

## 4. ¿Cuándo termina? (definición de COMPLETADA) — DECISIÓN RATIFICADA

> Una misión se completa cuando el estudiante termina conscientemente el
> recorrido de aprendizaje y confirma el último paso. **La misión mide
> experiencia y evidencia generada, no dominio.** La demostración del
> aprendizaje pertenece a la fase de evaluación, que es independiente y
> puede ocurrir después.

Una misión pasa a COMPLETADA cuando el estudiante **confirma el último paso de su
journey**, incluido el cierre cognitivo si dejó hipótesis (contraste
hipótesis-descubrimiento). Es el evento que hoy dispara la finalización — la
diferencia es que ahora es la culminación de un proceso persistido, no el único
dato que existe.

Precisiones que cierran el modelo:

- **La evaluación NO forma parte de la misión.** Es la fase "Demuestra" a nivel
  de experiencia (EvaluationAttempt), con su propia entidad y su propio ciclo.
  Una misión se completa por recorrido, no por calificación.
- **Completar es unidireccional.** Una misión COMPLETADA nunca vuelve a ACTIVA.
- **"Repasar" es lectura.** Reabre el snapshot vivido en modo lectura; no crea
  proceso nuevo ni altera evidencia.
- Los pasos que requieren respuesta deben estar respondidos para avanzar
  (regla que la UI ya aplica); completar implica que el recorrido fue recorrido,
  no saltado.

## 5. ¿Cuándo se puede regenerar? — DECISIÓN RATIFICADA

> La misión conserva su identidad y cada regeneración crea un **nuevo intento**
> asociado a esa misma misión, registrando explícitamente la causa
> (re-diagnóstico, cambio docente, petición del estudiante, degradación).
> La misión es el objetivo de aprendizaje; los intentos son las distintas
> estrategias pedagógicas que el swarm probó para alcanzarlo.

**Regla madre:** releer es el comportamiento por defecto. Regenerar es un evento
de dominio explícito, con causa registrada. **Navegar nunca regenera.**

| Causa | ¿Regenera? | Efecto |
|---|---|---|
| Volver mañana / recargar / navegar | **Nunca** | Reabre donde quedó |
| Re-diagnóstico (cambia modalidad) | Misiones futuras: sí. La activa: conserva su adaptación original (el cambio de perfil queda como evidencia longitudinal) | Nuevo intento solo si el estudiante lo pide |
| Docente cambia contenido del módulo | Intentos nuevos: sí | El intento en curso termina con su versión |
| Orquestación degradada | Sí — un snapshot degradado no se congela como "la experiencia" | Reintento permitido sin fricción |
| Estudiante pide otra explicación | Sí — re-adaptación pedagógica legítima | Nuevo intento; el anterior es evidencia de que la primera estrategia no bastó |

**Regenerar crea un intento nuevo; jamás sobreescribe.** La misión conserva su
identidad (el mismo módulo del path) y acumula su historial de intentos con
causas. Ese historial ES la evidencia longitudinal de la adaptación.

## 6. ¿Qué evidencia produce?

Cada misión deja, enlazado y recuperable:

1. La **cadena de deliberación** del swarm (trazas, debate, consenso, retrieval),
   ya persistida, enlazada por `session_id` — por fin con un dueño que no la deja huérfana.
2. El **contraste cognitivo**: hipótesis inicial vs cierre (SurpriseModal).
3. Las **respuestas por paso** — la captura del proceso, hoy inexistente
   (la fase "Capturar" del ciclo de la tesis, aplicada a la misión).
4. El **historial de intentos** con causas (por qué se regeneró, cuándo).
5. **Tiempo invertido acumulado** — que el motor de consenso ya sabe consumir.
6. Al completar: enriquecimiento de la memoria del estudiante
   (fortalezas/debilidades detectadas durante el recorrido).

Esto es lo que el Modo Evidencia (Replay, Decision Trace) muestra al jurado.

## 7. Implementación elegida

*(Un párrafo, por referencia — la decisión vive en la Auditoría III.)*

El dueño del estado es **`LearningSession` refundada**: se adopta el concepto y su
cableado ya existente (trazas y consenso apuntan a ella), se redefine su semántica
de "visita cronometrada" a "proceso de misión que sobrevive a múltiples visitas",
se escribe su primera migración real (tabla nueva, no toca datos de demo), y se
reescribe su servicio sin las dependencias de la era LMS. `EngagementSession`
permanece intacta como sesión de la fase de apertura.

---

## Deuda técnica registrada como entrada de este sprint

- **Aprovisionamiento dentro de un GET** (`student_service.get_student_learning_courses`,
  consumido por `GET /my-courses`): aprovisiona la experiencia y hace `commit`
  dentro de una lectura — herencia del patrón `activate_student`, no regresión.
  Con la Misión Activa existe por fin el evento explícito al que ese
  aprovisionamiento pertenece; moverlo ahí y dejar el GET como lectura pura.
  (Registrado 2026-07-06 al cierre del Sprint UX; marcado con TODO en el código.)

---

## Puerta metodológica (RESEARCH_ITERATIONS)

1. **Pregunta de investigación:** ¿puede el sistema sostener una experiencia
   adaptativa continua — recordar lo que sabe del estudiante y continuar donde
   quedó — a través de sesiones interrumpidas?
2. **Hipótesis que fortalece:** la adaptación multimodal como proceso persistente
   y con memoria, no como respuesta puntual.
3. **Variable que afecta:** continuidad (misma adaptación, misma posición
   entre visitas) + trazabilidad (evidencia enlazada por misión).
4. **Observable en la demo:** iniciar misión → avanzar → salir → volver →
   la experiencia continúa idéntica donde quedó, con su evidencia consultable.
5. **En Resultados y Discusión:** el historial de intentos y el contraste
   hipótesis-cierre como evidencia longitudinal de adaptación por estudiante.
