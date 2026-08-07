# RESEARCH_ITERATIONS.md — Iteraciones de Investigación

> Registro vivo de las iteraciones de investigación de la Fase 2+.
> Este documento NO es documentación de software: es evidencia de investigación,
> redactada para poder trasladarse casi directamente al capítulo de
> Resultados y Discusión de la tesis.
>
> Obliga a toda IA que trabaje en este proyecto (Claude, Antigravity, ChatGPT).

---

## Regla maestra

> **Ninguna funcionalidad nueva se implementa si antes no puede justificarse
> como evidencia de la hipótesis de investigación.**

Hipótesis: una arquitectura de orquestación pedagógica multimodal basada en
enjambre de agentes — mediante memoria compartida, consenso determinista y
calibración taxonómica Bloom — genera instrucciones de contenido educativo
adaptadas al perfil del aprendiz con trazabilidad completa, logrando mayor
riqueza y adaptabilidad que un sistema de agente único.

## Puerta de entrada (antes de implementar cualquier cambio)

Responder obligatoriamente las cinco preguntas. Si alguna no tiene respuesta,
**no se implementa**:

1. ¿Qué pregunta de investigación responde?
2. ¿Qué parte de la hipótesis fortalece?
3. ¿Qué variable afecta?
4. ¿Cómo se observará durante la demo?
5. ¿Cómo aparecerá luego en Resultados y Discusión?

## Plantilla de iteración

```
ITERACIÓN DE INVESTIGACIÓN N.n — <nombre>

Pregunta de investigación   (observable, nunca subjetiva)
Hipótesis parcial           (si <intervención>, entonces <efecto observable>)
Implementación              (qué se construyó; commits)
Evidencia observable        (qué puede verse en la demo sin explicación verbal)
Variables fortalecidas      (independiente / dependiente)
Amenazas a la validez       (lo que esta iteración NO demuestra)
Evidencia que deberá recolectarse  (observables del diseño experimental)
Resultado
Estado                      (EN PREPARACIÓN / EN CONSTRUCCIÓN / EN VALIDACIÓN / CONSOLIDADO)
```

---

# ITERACIÓN DE INVESTIGACIÓN 2.1 — La hipótesis hecha visible

## Pregunta de investigación

¿El estudiante puede comprender, sin ayuda del expositor, por qué su
experiencia de aprendizaje es diferente y a qué se debe cada decisión
pedagógica del sistema?

## Hipótesis parcial

Si cada decisión adaptativa del sistema (secuencia, modalidad, momento de
evaluación) se explica en el lenguaje del estudiante y en el momento en que
puede preguntársela, entonces el estudiante comprenderá que su recorrido fue
organizado a partir de su perfil, sin necesidad de exponer la arquitectura
técnica del enjambre.

## Implementación

Commit `055080e` (más base de `d9eba07`, Fase 1):

- **FiveEProgressBar** — recorrido 5E narrado (Descubre → Explora → Comprende
  → Practica → Demuestra) con hilo conductor siempre visible que conecta la
  historia ("Ya construiste el concepto. Ahora se convierte en herramienta.").
- **Banner de modalidad** — origen → detección → beneficio, anclado al
  diagnóstico real (`dominantModality`), con badge de confianza. Lenguaje
  centrado en la adaptación, no en el actor.
- **PhaseTransitionOverlay** — ritual de cruce de fase con presencia discreta
  del enjambre.
- **AdaptationEcho** — causa → consecuencia tras cada paso interactivo, según
  tipo de paso y calidad de la respuesta.
- **StepContextTag** — "¿por qué ahora?" solo cuando agrega contexto,
  incluida la evaluación.
- **Milestones 25/50/75%** — checklist de logro del estudiante.

Reglas de diseño consolidadas: regla del 20% (máximo un quinto de la pantalla
es "meta"), cada mensaje responde exactamente una pregunta, protagonista el
estudiante, la IA como buen profesor y no como personaje.

## Evidencia observable

En los primeros 60 segundos de la demo, sin explicación verbal: el banner
declara el porqué de la organización del módulo; las pills 5E y el hilo
conductor sitúan la fase pedagógica; cada actividad se justifica al aparecer;
cada respuesta produce una consecuencia explicada.

## Variables fortalecidas

- Independiente: ✔ adaptación multimodal · ✔ arquitectura multiagente
  (presencia) · ✖ inteligencia de enjambre como proceso colectivo observable
  (pendiente, iteración 2.2).
- Dependiente: ✔ experiencia personalizada · ✔ percepción de adaptación ·
  ◐ comprensión del estudiante (habilitada; su medición corresponde a 2.3).

## Amenazas a la validez

Lo que esta iteración NO demuestra:

- No demuestra que el aprendizaje mejore.
- No demuestra mejor rendimiento académico ni retención.
- No demuestra que la adaptación continúe durante el recorrido (solo al inicio).
- El feed de agentes del overlay es presentacional, no trazabilidad en tiempo
  real (esa corresponde al Swarm Monitor del Modo Evidencia).

Solo demuestra que el estudiante puede comprender por qué su experiencia es
diferente.

## Evidencia que deberá recolectarse

Durante la experimentación se observará:

- □ Tiempo hasta identificar que el contenido fue personalizado.
- □ Capacidad del estudiante para explicar por qué está viendo esa secuencia.
- □ Diferenciación respecto a un LMS tradicional.
- □ Comprensión del modelo pedagógico sin ayuda del expositor.

## Resultado

La adaptación multimodal y el modelo 5E pasaron de afirmaciones documentales a
experiencias observables en la interfaz del estudiante. Ante la pregunta del
jurado "¿dónde se evidencia la adaptación?", la respuesta ya no requiere abrir
el Swarm Monitor.

## Estado

**CONSOLIDADO** (commit `055080e`). Validación observacional en navegador
pendiente con la checklist de "Evidencia que deberá recolectarse".

### Congelado tras esta iteración

No modificar salvo error crítico: Momento 1 · Banner de adaptación · Modelo 5E
(pills y fases) · Hilo conductor · StepContextTag · AdaptationEcho ·
Milestones · PhaseTransitionOverlay.

---

# ITERACIÓN DE INVESTIGACIÓN 2.2 — Evidencias de adaptación continua

## Pregunta de investigación

¿El estudiante puede percibir evidencias de que el sistema sigue adaptando el
aprendizaje durante el recorrido?

## Hipótesis parcial

Si el sistema hace visibles las decisiones adaptativas durante el recorrido,
entonces el estudiante reconocerá que la adaptación continúa durante el
aprendizaje y no solo al inicio del módulo.

## Criterio de éxito único

El estudiante debe poder responder, sin ayuda:

> "¿Cómo sabes que el sistema sigue adaptando tu aprendizaje?"

## Restricciones (contrato)

- No modificar nada de la iteración 2.1.
- No mejorar componentes existentes.
- No rediseñar interfaces.
- Solo añadir evidencias discretas de adaptación continua.

## Estado

**PAUSADA (2026-07-02)** — el proyecto entró en Etapa 3 (producto
demostrable, ver FLOW_AUDIT.md § Tablero Etapa 2): antes de retomar 2.2 se
deben cerrar los Bloques 2-4 (Docente, Administrador, Modo Evidencia) bajo
el criterio "¿puede cualquier jurado usarla de principio a fin sin
encontrar un bloqueo?". No se trabaja en paralelo. Se retoma cuando esos
tres bloques estén cerrados y, en todo caso, tras la validación
observacional de la iteración 2.1.

---

# REORGANIZACIÓN ARQUITECTÓNICA R1 — Modo Evidencia (2026-07-02)

No es una iteración de funcionalidad: es una depuración del modelo de
actores, aprobada explícitamente por el tesista. **No se implementó ni se
eliminó ninguna funcionalidad**; solo se reorganizó el acceso y la narrativa.

## Decisión

El rol **Investigador se elimina como usuario de negocio**. Todas sus
herramientas (Demo Multiagente, Replay Cognitivo, Decision Trace, consenso,
métricas) se conservan íntegras agrupadas bajo el **Modo Evidencia**: una
capacidad de observabilidad del sistema destinada a la evaluación y
validación experimental de la hipótesis durante la sustentación.

Modelo de actores resultante:

- **Estudiante** → aprende (protagonista).
- **Docente** → acompaña.
- **Administrador** → administra.
- **Modo Evidencia** → demuestra científicamente cómo el sistema decidió.

## Justificación (puerta de las 5 preguntas)

1. **Pregunta de investigación:** ¿puede el jurado observar cómo el sistema
   adaptó el aprendizaje y por qué tomó esas decisiones? (reemplaza a
   "¿funciona el panel del investigador?").
2. **Hipótesis:** fortalece la trazabilidad completa — la observabilidad
   pasa de "pantalla de un rol artificial" a propiedad de la arquitectura.
3. **Variable:** trazabilidad (dependiente); no altera la adaptación.
4. **Observable en demo:** durante el recorrido del estudiante se activa el
   Modo Evidencia ("Permítanme mostrar qué está ocurriendo internamente").
5. **En Resultados y Discusión:** "la plataforma incorpora un Modo Evidencia
   destinado a visualizar el proceso interno de adaptación con fines de
   evaluación y validación experimental".

## Hallazgo que motivó la decisión

La auditoría de código confirmó que el rol ya era una cáscara: su dashboard
solo enlazaba a /swarm-demo y /replay (rutas ya públicas), y el guard
backend `get_current_investigador` no protegía ningún endpoint.

## Cambios

- Frontend: ruta pública `/evidencia` (EvidenceHub + EvidenceLayout);
  acceso "Modo Evidencia" en sidebars de admin y docente; rol retirado de
  selectores de administración y redirecciones (usuarios legado aterrizan
  en /evidencia). Eliminados InvestigadorLayout y pages/investigador.
- Backend: guards muertos retirados de deps.py; `UserRole.INVESTIGADOR` se
  conserva en el enum solo por compatibilidad con filas existentes (sin
  migración destructiva).
- Documentos canónicos actualizados: CLAUDE.md, THESIS_SCOPE_FREEZE.md,
  ROADMAP_THESIS_FOCUS.md, FLOW_AUDIT.md (Recorrido 4 → Modo Evidencia).

## Estado

**CONSOLIDADO.** El Recorrido 4 (FLOW_AUDIT.md) valida el Modo Evidencia
con su nueva pregunta de investigación.

---

# FASE 3 — ARQUITECTURA v2: EVIDENCIA DE APRENDIZAJE (2026-07-04)

> Gobernada por **PRODUCT_ARCHITECTURE_V2.md** (aprobado como constitución
> conceptual el 2026-07-04). El aporte científico se formula en v2 como:
> *"un modelo continuo de construcción y validación de hipótesis pedagógicas
> basado en evidencia de aprendizaje, implementado mediante una arquitectura
> multiagente colaborativa"*. La arquitectura multiagente es el medio; el
> modelo de evidencia es el fin. Esta formulación complementa (no reemplaza)
> la hipótesis registrada arriba: la precisa.

## Triple especificación (obligatoria desde la Fase 3)

Ningún sprint entra al backlog sin declarar sus tres caras:

1. **Objetivo científico** — qué hipótesis o evidencia se valida.
2. **Objetivo de experiencia** — qué cambio concreto percibirá el estudiante.
3. **Evidencia esperada** — qué datos exactos se registrarán (diseñar la
   captura antes de diseñar la pantalla).

Y cada sprint declara **la frase del estudiante**: una única oración que un
estudiante real debería poder decir al terminar el sprint. Si ningún
estudiante podría decirla, el sprint no produjo experiencia perceptible.

## Puerta de cierre (además de la puerta de entrada de 5 preguntas)

Ningún sprint se cierra sin responder las tres:

1. ¿Qué evidencia nueva produce?
2. ¿Qué aprende el sistema?
3. **¿Qué hace que el estudiante quiera volver mañana?**

## Tablero de la Fase 3

| Sprint | Objetivo científico | Objetivo de experiencia | Frase del estudiante |
|---|---|---|---|
| 0 — Asegurar la base (operativo) | Base auditada y validada E2E | El estudiante nuevo entra sin fricción | — (operativo) |
| 3.1 — El sistema comienza a comprender al estudiante | Capturar evidencia multimodal del recorrido real | La plataforma le devuelve lo que observó de él | "Siento que la plataforma empezó a conocer cómo aprendo." |
| 3.2 — El estudiante entiende por qué | Las hipótesis cambian con la evidencia, de forma observable | Su forma de aprender, narrada y evolucionando | "Ahora entiendo por qué me recomienda ciertas actividades." |
| 3.3 — El contenido empieza a adaptarse | La hipótesis conductual gobierna el contenido servido | El contenido llega en la modalidad que le funciona, con el porqué | "El contenido ya no se siente igual para todos." |
| 3.4 — La plataforma también aprende | Fase 5 del ciclo: validar decisiones contra desempeño posterior | Su progreso como delta visible y reconocido | "Puedo ver que tanto yo como la plataforma hemos aprendido." |

Los sprints 3.2–3.4 son **backlog planificado**: se abren de a uno, tras el
cierre del anterior, y su especificación se revisará con la evidencia del
sprint previo (pueden cambiar; el Anexo D de la constitución sigue vivo).

---

## SPRINT 0 — Cerrar la baseline (operativo, no iteración de investigación)

```
Congelar arquitectura → Validar estado real → Eliminar deuda visible → Cerrar baseline
```

- **Congelar arquitectura** ✅ (2026-07-04): PRODUCT_ARCHITECTURE_V2.md
  congelado. No se crean más documentos de arquitectura ni principios;
  el trabajo pasa a implementación incremental. (La auditoría estática del
  corte OpenCode ya está hecha: diffs, build, imports, tests en verde.)
- **Validar estado real** — **la automatización no detectó anomalías durante
  el recorrido ejecutado; PENDIENTE de validación manual del tesista** (2026-07-04, navegador
  automatizado contra stack completo). Lo observado por la automatización:
  (1) estudiante NUEVO (`audit.fork`, 0 rutas, sin ciclo) → redirigido al
  onboarding de un clic → "Comenzar experiencia" → dashboard "Mi Aprendizaje"
  con la experiencia aprovisionada (ruta semanal creada), sin rebote;
  (2) nav "Ruta de Aprendizaje" resuelve por el flag `is_active_experience`
  del servidor; (3) Misión 1 → orquestación swarm real (POST orchestrate 200,
  18.9s, research 12 fuentes, confidence 0.613) → contenido generado, abre
  con tarjeta "¿Sabías que...?"; (4) estudiante EXISTENTE (`estudiante3`) →
  directo a su dashboard con progreso, sin rebote. La automatización no
  detectó anomalías de consola durante el recorrido ejecutado. El recorrido
  **aparenta ser correcto**; la Regla de Cierre exige el recorrido del
  tesista para darlo por validado.
- **Eliminar deuda visible** — la automatización no detectó anomalías que
  constituyan bloqueo durante el recorrido ejecutado; queda
  sujeto a lo que revele el recorrido manual. Única fricción observada:
  "Preparando fase de descubrimiento…" tarda ~19–30 s en la primera
  generación sin indicador de avance — registrada como observación para el
  Sprint 3.1 (que reconstruye ese recorrido), no como deuda de baseline.
- **Cerrar baseline** ⏳: bloqueado hasta (a) validación manual del tesista
  y (b) su OK para los commits atómicos del corte (una decisión por commit).

Regla de vuelo (permanente desde Fase 3): si durante un sprint aparece una
mejor idea arquitectónica, se registra como propuesta y se continúa; el
rumbo del sprint solo cambia con aprobación explícita.

---

# ITERACIÓN DE INVESTIGACIÓN 3.1 — El sistema comienza a comprender al estudiante

## Pregunta de investigación

¿El recorrido real del estudiante genera evidencia de aprendizaje de las
cuatro fuentes (observación, interacción, evaluación, preferencias
emergentes), observable con atribución, fecha y confianza?

## Hipótesis parcial

Si se instrumenta el recorrido real del estudiante sobre la memoria
compartida existente, entonces cada sesión de estudio producirá evidencia
nueva de al menos tres de las cuatro fuentes — hoy solo la fuente
*evaluación* se captura densamente; el resto llega disperso o inferido
a posteriori.

## Objetivo científico

Capturar evidencia multimodal del recorrido real (fase 1 del ciclo:
Capturar). Sin esta densidad de evidencia, ni la adaptación (3.3) ni la
validación (3.4) son demostrables.

## Objetivo de experiencia

El estudiante siente por primera vez que la plataforma empieza a conocer
cómo aprende: al cerrar su sesión recibe una observación narrada sobre
cómo trabajó hoy ("hoy avanzaste más fluido con los ejemplos visuales",
"volviste dos veces sobre los bucles — mañana empezamos por ahí").
La promesa del "mañana" debe cumplirse en la sesión siguiente.

## Frase del estudiante

> "Siento que la plataforma empezó a conocer cómo aprendo."

## Alcance de construcción (definido por el tesista, 2026-07-04)

El sprint construye ÚNICAMENTE el nuevo recorrido de aprendizaje —
el corazón del producto:

```
Landing → ¿Sabías qué? → Comenzar → Micro reto → Panel de consenso → Primer contenido
```

Nada más. **Sin dashboard nuevo** (el dashboard es consecuencia: primero el
estudiante debe decir "quiero seguir"; después las estadísticas). **Sin
memoria nueva. Sin multimodal completo. Sin métricas nuevas.** Solo ese
recorrido, y la evidencia que ese recorrido genera de forma natural:

- **¿Sabías qué? / Primer contenido** → permanencia, tiempo por bloque (observación).
- **Micro reto** → reintentos, resultado (evaluación + interacción).
- **Elecciones dentro del recorrido** → formato elegido (preferencias emergentes).
- **Panel de consenso** → la deliberación de los agentes, visible (deliberación).

## Evidencia esperada (diseño de captura, antes que la pantalla)

- Tiempo de interacción por bloque de contenido.
- Formato/modalidad elegida cuando hay alternativa.
- Reintentos (micro reto, ejercicios).
- Permanencia y abandono (dónde se detiene, dónde se va).
- Resultado (desempeño demostrado).

Cada pieza con las cuatro propiedades: atribuible, fechada, graduada
(confianza), trazable.

## Criterio de éxito único

Un estudiante nuevo recorre Landing → ¿Sabías qué? → Comenzar → Micro reto →
Panel de consenso → Primer contenido **en navegador real, sin intervención
del desarrollador, en menos de cinco minutos** — y el Modo Evidencia muestra
evidencia nueva de **al menos 3 de las 4 fuentes** generada por ese recorrido.

## Restricciones (contrato)

- ÚNICAMENTE el recorrido del alcance; toda idea fuera de él se registra
  como propuesta y se continúa (regla de vuelo).
- No se crean entidades nuevas (decisión D1 del Anexo D sigue abierta).
- No se tocan los call sites legados de activación (D2/D3 abiertas).
- Se usa la memoria compartida existente (publicación con confianza y TTL).
- El lenguaje visible del estudiante no cambia de registro: narración,
  nunca mecanismo.
- Toda pieza del sprint debe ser perceptible por el estudiante o por el
  investigador; lo imperceptible no aporta valor al sprint.

## Puerta de entrada (5 preguntas)

1. **Pregunta:** ¿el recorrido real genera evidencia de las 4 fuentes?
2. **Hipótesis:** fortalece la premisa base — sin evidencia conductual real
   no hay adaptación multimodal demostrable.
3. **Variable:** cobertura/densidad de captura de evidencia por interacción.
4. **Demo:** el Modo Evidencia muestra el flujo de evidencia mientras un
   estudiante usa un módulo en vivo.
5. **Resultados y Discusión:** tabla de cobertura de captura por fuente e
   interacción — la base de todos los análisis posteriores.

## Estado

**EN PREPARACIÓN.** Aprobada el 2026-07-04. Arranca al cierre del Sprint 0.

---

# ITERACIÓN DE INVESTIGACIÓN 4.1 — Research & Experiment Layer (2026-07-08)

## Pregunta de investigación

¿El sistema multiagente adaptativo produce una ganancia de aprendizaje
medible entre un pre-test y un post-test de conocimiento en Fundamentos
de la Programación?

## Hipótesis parcial

Si el perfil del estudiante incorpora su conocimiento previo real (pre-test)
además de su estilo, la ruta adaptativa parte del punto correcto y el
incremento pre→post se vuelve la evidencia cuantitativa central del
capítulo de Resultados.

## Diseño experimental

- **Diseño pre-experimental de un solo grupo** con pre-test y post-test.
  No existe grupo control; todos los estudiantes pertenecen al grupo
  "Experimental" (columna constante en la exportación, compatible SPSS).
- **Instrumento fijo**: banco de 36 ítems MCQ (4 por módulo × 9 módulos,
  1 básica / 2 intermedias / 1 avanzada), seedeado en BD y versionado
  (BANK_VERSION). El mismo instrumento para todos los estudiantes y para
  pre y post. **El LLM no participa en la construcción del instrumento**
  (su función sigue siendo adaptar contenido, no medir).
- **Clasificación automática**: <40% Básico, 40–70% Intermedio,
  ≥70% Avanzado (umbrales configurables en knowledge_test_service).
- **Ganancias calculadas**: incremento absoluto, porcentual y ganancia
  normalizada de Hake g = (post−pre)/(100−pre).

## Actualización de la decisión D1

La restricción "no se crean entidades nuevas (D1 abierta)" queda
**actualizada por orden del tesista (2026-07-07)**: se autorizan las
entidades del instrumento experimental (knowledge_test_questions,
knowledge_test_attempts, knowledge_test_answers, experiment_results,
research_metrics). D2/D3 siguen abiertas; la memoria compartida existente
sigue siendo el canal del swarm (esta capa solo la ESCRIBE con el formato
que el perfilador ya lee).

## Implementación (commits 12d0c03..7f7ac04)

1. `feat(db)` modelos + migración f6a7b8c9d0e1 (reversible, guarded) y
   seed idempotente del banco en el lifespan.
2. `feat(api)` endpoints /api/students/knowledge-test (status/start/submit/
   result/comparison); el pre se rinde una sola vez, el post exige pre.
3. `feat(agents)` el pre-test enriquece DiagnosticResult.profile
   (knowledge_assessment) y publica en shared memory el learning_profile
   que AdaptiveLearningAgent lee — el perfilador swarm deja de correr con
   defaults.
4. `feat(learning-path)` la generación de ruta desbloquea módulos dominados
   (≥75% por módulo): mismo estilo + distinto conocimiento ⇒ rutas distintas.
   Persiste knowledge_level y generation_duration_ms.
5. `feat(api)` métricas de investigación persistidas en el flujo real
   (ruta, orquestación IA, tutor, misión) + dashboard /api/research +
   exportación CSV/Excel.
6. `feat(ui)` pantallas Evaluación Diagnóstica/Post-Test/Resultado,
   PretestGuard sobre la ruta, CTAs de post-test y Dashboard del
   Investigador en /evidencia/investigacion.

## Evidencia observable

- Modo Evidencia → Dashboard del Investigador: n, promedios pre/post,
  incremento promedio, distribución de niveles, tiempos del sistema,
  estudiantes por perfil y tabla por estudiante — todo desde BD.
- Botón "Exportar resultados" (CSV con BOM UTF-8 / XLSX con hojas
  Resultados y Resumen) listo para SPSS, RStudio o Python.

## Compatibilidad (contrato de no-regresión)

- Estudiantes legacy con ruta y sin pre-test: nunca bloqueados (guard y
  gate fail-open); sin pre-test la generación reproduce el comportamiento
  histórico exacto.
- Banco no seedeado ⇒ toda la capa se desactiva sola (fail-open).
- Diagnóstico de estilo (secciones A/B), swarm, auth: intactos.

## Estado

**FUNCIONALMENTE VALIDADO por validación automatizada** (36 tests nuevos
en verde, baseline preexistente sin regresiones, build frontend limpio,
endpoints probados contra el stack real). **Pendiente de validación manual
del tesista** (recorrido completo en navegador: login → diagnóstico →
pre-test → ruta → misión → post-test → /evidencia/investigacion → exportar).

---

# ITERACIÓN DE INVESTIGACIÓN 5.1 — Sensibilidad de la dinámica de consenso ante el umbral de discriminación δ (H10)

## Pregunta de investigación

¿Cómo modifica el umbral de discriminación δ la dinámica observable del
consenso y el paisaje cognitivo ante una evidencia idéntica?

## Hipótesis parcial

- **H0**: δ no modifica significativamente (resultado, entropía,
  conflicto) ante evidencia idéntica.
- **H1**: δ > margen(evidencia) produce una transición observable
  Resuelta → Aplazada, acompañada de mayor densidad de claims vigentes,
  mayor entropía, conflicto preservado.

## Diseño experimental

**Antecedente.** Extiende ADR-0012 §3 y su adenda §3.1 (Escenario A,
`consenso_replay_v1_vs_v2.py`): esa corrida ya mostró, con dos ejecuciones
reales (v1 delta=0 vs v2 delta=0.10), que la misma evidencia (propuestas
rivales Remediar 0.82 / Orientar 0.75 sobre `siguiente-paso(sesion)`,
margen real 0.07) resuelve o aplaza según delta. Esta iteración generaliza
esa observación puntual (2 valores) a una curva (7 valores) sobre el mismo
escenario causal.

**Barrido paramétrico, no réplicas.** Bajo los productores de reglas
deterministas vigentes, el margen de la tensión canónica #1 es una
constante fija de la evidencia (0.07) — un diseño de "N réplicas" en el
sentido clásico (repetir la misma condición para estimar varianza) sería
estadísticamente vacío, porque no hay varianza que estimar: el mismo
escenario, corrido dos veces bajo la misma política, produce el mismo
margen exacto. Este es el mismo límite estructural documentado como
hallazgo D1 en la mini-épica de Consenso (RFC-0007 §2.2) — no se resuelve
aquí (fuera de alcance, ver Amenazas a la validez), se **diseña
alrededor** de él: en vez de repetir la condición, se **varía
sistemáticamente el parámetro** cuyo efecto se quiere caracterizar.

- **Variable independiente**: δ ∈ {0.00, 0.05, 0.07, 0.071, 0.10, 0.15,
  0.20}.
- **Variables NO variadas (diseño unifactorial)**: `pesos_asunto`,
  `asuntos_reservados`, confianza de productores (regla, determinista,
  sin red — mismo control de ADR-0012 §3 sobre el confusor LLM), y la
  evidencia inicial (mismo hecho evaluativo: 2 errores en competencia
  "bucles", mismas dos propuestas rivales). `theta` se mantiene en 0.5
  (mismo valor que `POLITICAS["v2"]`) para aislar δ como único parámetro
  en movimiento.
- **N = 1 escenario causal controlado.** No se pretende estimar varianza
  poblacional. Se pretende caracterizar la respuesta determinista del
  sistema ante variación controlada del parámetro δ.

## Resultados esperados (pre-registro, antes de ejecutar)

| δ | Esperado |
|---|---|
| 0.00 | Resuelta |
| 0.05 | Resuelta |
| 0.07 | Resuelta (igualdad permitida) |
| 0.071 | Aplazada |
| 0.10 | Aplazada |
| 0.15 | Aplazada |
| 0.20 | Aplazada |

Paisaje esperado sobre `siguiente-paso(sesion)`, antes vs. después del
umbral de transición:

| | Antes (δ ≤ 0.07) | Después (δ ≥ 0.071) |
|---|---|---|
| densidad | 1 | 2 |
| conflicto | `{}` | `latente` |
| entropía | → 0 | ≈ 1 bit |

## Amenazas a la validez

- **No generaliza a superioridad de política.** La transición observada
  identifica sensibilidad al parámetro δ, pero no permite concluir
  superioridad de v2 sobre v1 en términos educativos o adaptativos sin
  escenarios adicionales.
- **Hallazgo D1 (heredado, no resuelto aquí).** El margen es una
  propiedad de la evidencia declarada por los productores, no de la
  política — por eso el diseño es un barrido de δ y no una comparación
  de "réplicas"; ver la sección "Barrido paramétrico, no réplicas" arriba.
- **Un solo escenario causal.** Los 7 puntos de la curva comparten el
  mismo par de propuestas rivales (misma evidencia); no cubre otras
  tensiones D1/D2 del sistema ni otros márgenes posibles.

## Implementación

Script `backend/scripts/experimentos/consenso_barrido_delta.py`. Técnica:
una sola ejecución real de `ejecutar_walkthrough` (Postgres real,
productor regla, sin red — misma metodología de
`consenso_replay_v1_vs_v2.py`) hasta el punto causal exacto donde ambas
propuestas rivales ya existen y la deliberación aún no se registró
(reconstruido vía `reconstruir_con_replay`); desde ese único estado real,
7 ramas contrafactuales in-memory —nunca persistidas—, una por valor de
δ, cada una invocando `mecanica.convocar(estado, Politica(delta=...),
urgente=False)` directamente (mismo patrón ya validado en
`tests/runtime/reconstruction/test_RFC_0007_consenso.py`) y aplicando su
resultado con el reducer real `registrar_deliberacion`. Cada rama se
instrumenta con `derivar_paisaje`/`derivar_consenso` (RFC-0007 §2.2) sobre
el prefijo real + su propio paso sintético. No modifica
`kernel/deliberation/politica.py` (`POLITICAS` no se toca — cada `Politica`
del barrido se construye ad-hoc en el script, nunca se registra como
política de producción ni de experimento con nombre propio), no modifica
`mecanica.py` ni `confianza.py`, no persiste ninguna de las 7 ramas.

## Resultado

Barrido ejecutado contra Postgres real (`consenso_barrido_delta.py`,
run_id `20260802T005202`,
`backend/experiments/results/consenso_barrido_delta_20260802T005202.json`).
Un solo prefijo real (`ejecutar_walkthrough`, productor regla), 7 ramas
contrafactuales in-memory sobre `siguiente-paso(sesion)`:

| δ | Resultado | densidad | conflicto | entropía | margen |
|---|---|---|---|---|---|
| 0.00 | RESUELTA | 1 | — | 0.0 | 0.0700 |
| 0.05 | RESUELTA | 1 | — | 0.0 | 0.0700 |
| 0.07 | RESUELTA | 1 | — | 0.0 | 0.0700 |
| 0.071 | APLAZADA | 2 | latente | 0.9986 | 0.0700 |
| 0.10 | APLAZADA | 2 | latente | 0.9986 | 0.0700 |
| 0.15 | APLAZADA | 2 | latente | 0.9986 | 0.0700 |
| 0.20 | APLAZADA | 2 | latente | 0.9986 | 0.0700 |

**Coincide exactamente con la tabla pre-registrada** — H1 confirmada: la
transición Resuelta → Aplazada ocurre exactamente en el punto predicho
(δ = margen + ε), acompañada del salto de paisaje predicho (densidad
1→2, conflicto ∅→latente, entropía 0→≈1 bit). El margen recalculado
(0.0700) es idéntico en las 7 ramas — confirma, ahora sobre una curva
completa y no solo dos puntos, que el margen es una propiedad de la
evidencia declarada por los productores, no de la política que la
evalúa (mismo hallazgo de ADR-0012 §3.1, generalizado). H0 se rechaza:
δ sí modifica significativamente resultado, entropía y conflicto ante
evidencia idéntica — pero, consistente con la amenaza a la validez
declarada arriba, esto caracteriza la sensibilidad del mecanismo al
parámetro, no una comparación de superioridad pedagógica entre
políticas.

## Estado

**EJECUTADA — hipótesis H1 confirmada, curva completa coincide con el
pre-registro.** Pendiente de incorporación al capítulo de Resultados de
la tesis.

---

# ITERACIÓN DE INVESTIGACIÓN 5.2 — Sensibilidad del margen de consenso ante evidencia variable bajo productores adaptativos (H10, extensión LLM)

## Pregunta de investigación

¿La severidad de la evidencia diagnóstica modifica el margen de confianza
que declaran los productores LLM (Remediar, Orientar) sobre la tensión
canónica #1, y esa variación interactúa con el umbral de discriminación δ
para desplazar el punto de transición Resuelta→Aplazada — a diferencia de
los productores de regla (5.1), donde el margen es una constante fija de
la evidencia (0.07, independiente de su severidad)?

## Hipótesis parcial

- **H0**: bajo productores LLM, el margen entre Remediar-LLM y
  Orientar-LLM permanece aproximadamente constante entre niveles de
  severidad de evidencia — el LLM no usa la señal de severidad para
  modular su confianza declarada, pese a que el prompt ahora se la expone
  explícitamente (ver "Instrumento" abajo). El punto de transición en δ
  sería el mismo en las 4 evidencias, igual que bajo regla.
- **H1**: el margen varía con la severidad de la evidencia — a distinta
  evidencia, distinto margen —, **sin asumir monotonicidad ni dirección
  del efecto** (no afirma que más errores impliquen mayor margen, ni que
  impliquen menor margen — solo que el margen deja de ser constante) — y
  por tanto el punto de transición Resuelta→Aplazada en δ se desplaza
  entre niveles de evidencia (a diferencia de 5.1, donde el punto de
  transición fue idéntico —δ=0.071— para toda la curva porque el margen
  de la regla es constante).

## Instrumento (ya implementado, previo a este pre-registro)

Los prompts de Remediar-LLM y Orientar-LLM (`producir()`, ruta
`siguiente-paso(sesion)`) no incluían ninguna señal de severidad —
referenciaban solo el `claim.id` de la interpretación de Diagnosticar,
nunca su contenido. Bajo `temperature=0` (default de `OpenAIProvider`,
fijado en M3 PR-2 por reproducibilidad) y prompt idéntico entre niveles
de evidencia, el margen no podía variar con Factor A por construcción —
hallazgo de la auditoría previa a este pre-registro, no una suposición.

Corregido hoy, antes de este pre-registro (P13: cambia la implementación,
nunca el contrato — mismo tipo de claim, mismo asunto, mismo respaldo):
ambos prompts ahora interpolan `claim.afirmacion.get("errores")` —
dato ya disponible en el claim de Diagnosticar, sin plumbing nuevo.
Versionado explícito para no confundir corridas futuras con el
instrumento anterior: `_PROMPT_ID` pasa de `remediacion-siguiente-paso-v1`
a `remediacion-siguiente-paso-v2` (`backend/runtime/domain/remediar/
productor_llm.py`) y de `orientacion-siguiente-paso-v1` a
`orientacion-siguiente-paso-v2` (`backend/runtime/domain/orientar/
productor_llm.py`). No se tocó `_producir_por_objetivo` (ruta multi-
objetivo, fuera de alcance de esta iteración). Verificado sin regresión
contra la suite de guardianes P13 (`test_P13_remediar_reglas_vs_llm.py`,
`test_P13_orientar_reglas_vs_llm.py`, `test_orientar_remediar_por_
objetivo.py` — 18 passed, 0 failed; ninguno fija el texto del prompt ni
el `_PROMPT_ID`, solo el contrato). Este instrumento v2 **nunca ha sido
ejecutado contra un proveedor LLM real** — este pre-registro se escribe
antes de su primera ejecución real, precisamente para no ajustar la
hipótesis después de ver el dato.

## Diseño experimental

**Antecedente.** Extiende 5.1 (barrido de δ, productor regla, margen
constante 0.07) y el hallazgo exploratorio de ADR-0012 §3: una corrida
real con productores LLM (sin la propagación de severidad de hoy) obtuvo
confianzas 0.85/0.95 → margen 0.10 — documentada allí como inválida por
mezclar accidentalmente productor regla/LLM (confusor no controlado, no
por el valor del margen en sí). Ese margen 0.10 ya demuestra que el LLM
puede declarar un margen distinto de 0.07 — motiva, pero no prueba, H1.

**Corrección estructural encontrada en esta auditoría (bloqueante si no
se aplica).** El margen requiere que Remediar Y Orientar propongan ambos
sobre `siguiente-paso(sesion)`. `remediar/productor_llm.py` solo propone
cuando `claim.afirmacion.get("dominada") is False`; `orientar/
productor_llm.py` (ruta `siguiente-paso`) propone siempre que exista la
clave `"dominada"`, sin importar su valor. Con `_UMBRAL_ERRORES = 2`
(`diagnosticar/productor.py:22`), un hecho con **1** error clasifica
`dominada=True` → Remediar no compite, Orientar propone solo, no hay
tensión que medir. Por eso Factor A **no puede ser 1–4 errores** (como se
sugirió antes de esta auditoría): debe mantenerse dentro del régimen
`dominada=False`, es decir, `errores ≥ _UMBRAL_ERRORES`.

- **Factor A — severidad de evidencia** (variable independiente 1):
  `items_incorrectos` de longitud E1=2, E2=3, E3=4, E4=5, todos sobre la
  misma competencia que 5.1/ADR-0012 (`COMPETENCIA = "Bucles"`,
  `consenso_barrido_delta.py:73`) — mismo asunto, misma capacidad
  evaluativa, solo cambia la cardinalidad de la evidencia incorrecta.
  Los 4 niveles caen en el régimen `dominada=False` por construcción
  (todos ≥ 2), preservando la tensión canónica en los 4 casos.
- **Factor B — política** (variable independiente 2): δ ∈ {0.00, 0.05,
  0.10, 0.15} — subconjunto de la curva de 5.1 (no hacen falta los 7
  valores: 5.1 ya localizó el comportamiento frontera bajo regla; aquí
  el punto de interés es si el margen LLM, y por tanto el punto de
  transición, se mueve respecto a ese frontera conocido).
- **Variables dependientes**: resultado de la deliberación
  (`Resuelta`/`Aplazada`), margen recalculado, y las mismas proyecciones
  de RFC-0007 §2.2 usadas en 5.1 (`derivar_paisaje`/`derivar_consenso`:
  densidad, conflicto, entropía).
- **Variables NO variadas**: `theta = 0.5` (igual que `POLITICAS["v2"]`),
  `pesos_asunto`/`asuntos_reservados` en su valor neutro v1 (mismo
  control que ADR-0012 §2), mismo modelo (`gpt-4o-mini`, default de
  `OpenAIProvider`), `temperature=0` (default), mismo `_PROMPT_ID` v2 en
  las 4 severidades — el único dato que cambia en el texto del prompt es
  el número de errores.
- **N = 4 escenarios de evidencia, cada uno con 1 ejecución real.** Por
  cada nivel de evidencia: 3 llamadas LLM reales (Diagnosticar → Remediar
  → Orientar, productores explícitos, nunca la selección automática del
  Boundary — mismo control que el confusor de ADR-0012 §3), hasta el
  estado exacto con ambas propuestas rivales vigentes y la deliberación
  aún no registrada. Desde cada uno de esos 4 estados reales, el eje δ
  sigue la misma técnica in-memory de 5.1 (ramas contrafactuales vía
  `mecanica.convocar` + `registrar_deliberacion`, nunca persistidas) — no
  son réplicas de δ, son el mismo barrido paramétrico ya validado. En este
  diseño esto implica 12 llamadas LLM reales (4 evidencias × 3
  capacidades) — cifra ilustrativa del diseño actual, no un criterio de
  aceptación: si una capacidad auxiliar se agrega más adelante, el número
  cambia sin que el diseño experimental deje de ser válido.

## Resultados esperados (pre-registro, antes de ejecutar)

| Evidencia | errores | Margen esperado si H0 | Margen esperado si H1 |
|---|---|---|---|
| E1 | 2 | ≈ 0.07 (igual a regla) | distinto de 0.07 |
| E2 | 3 | ≈ 0.07 | distinto de E1 |
| E3 | 4 | ≈ 0.07 | distinto de E1/E2 |
| E4 | 5 | ≈ 0.07 | distinto de E1/E2/E3 |

Si H1 se confirma, el punto de transición Resuelta→Aplazada dentro de la
curva δ ∈ {0.00, 0.05, 0.10, 0.15} debería **diferir entre al menos dos
niveles de evidencia** (a diferencia de 5.1, donde el punto de transición
—δ=0.071— fue idéntico en las 7 réplicas paramétricas porque el margen
regla es una constante). Si H0 se confirma, el punto de transición sería
el mismo en las 4 evidencias — resultado igual de válido: documentaría
que el LLM, aun con la señal de severidad expuesta explícitamente en el
prompt v2, no la usa para modular su confianza declarada.

**Ningún resultado se considera un fracaso experimental.** La
confirmación de H0 también constituye un resultado científicamente
válido, pues evidenciaría que la incorporación explícita de la severidad
al prompt no modifica el comportamiento del productor LLM bajo las
condiciones evaluadas.

## Amenazas a la validez

- **Instrumento nunca antes ejecutado contra LLM real.** Los prompts v2
  se crearon el mismo día de este pre-registro — no hay corridas previas
  que informen si el LLM real efectivamente lee y usa el dato de
  severidad recién expuesto; ese es precisamente el objeto de prueba.
- **Confusor regla/LLM (heredado de ADR-0012 §3).** Debe controlarse
  llamando `ejecutar_walkthrough` con productores LLM explícitos, nunca
  dependiendo de `productores.py: productor_*_activo()`.
- **No-determinismo residual del proveedor real.** `temperature=0` reduce
  pero no garantiza reproducibilidad exacta entre llamadas del SDK de
  OpenAI; mitigado capturando prompt + respuesta cruda + timestamp por
  llamada (ver "Reproducibilidad" abajo).
- **N=1 por celda de evidencia — no estima varianza intra-nivel.** Una
  sola llamada real por nivel de severidad caracteriza el efecto de la
  severidad sobre el margen, no la varianza del LLM ante el mismo prompt
  repetido (eso sería un experimento de réplicas puras, fuera de alcance
  aquí, igual que 5.1 declaró N=1 para δ).
- **Rango de evidencia acotado al régimen `dominada=False`.** No cubre el
  caso `dominada=True` (1 error): ahí Remediar no compite por diseño
  estructural (no es una limitación de esta iteración, es el
  comportamiento correcto de la capacidad — ver "Corrección estructural"
  arriba).
- **No generaliza a superioridad de política ni de proveedor.** Igual
  amenaza que 5.1: caracteriza sensibilidad del mecanismo, no superioridad
  pedagógica de LLM sobre regla.

## Reproducibilidad

Ningún campo nuevo en `Provenance` ni en el Kernel (evitaría RFC nuevo
sin necesidad — RFC-0003 §3.1 ya cubre `modelo`/`version`/`prompt_id`).
La captura de prompt completo + respuesta cruda + timestamp por llamada
se hace **dentro del script del experimento**, envolviendo
`OpenAIProvider` con un decorador local — mismo patrón ya usado por
`consenso_barrido_delta.py`/`consenso_replay_v1_vs_v2.py` (scripts
aislados que no tocan `runtime/` ni la selección global de política).
Cada corrida exporta su JSON de resultados con esos datos adicionales,
igual que las corridas de 5.1 y ADR-0012 §3.

## Criterios de aceptación

- Prompts v2 verificados sin regresión de contrato (ya cumplido, ver
  "Instrumento" arriba).
- Se ejecutan todas las llamadas LLM necesarias para obtener las cuatro
  condiciones experimentales definidas, cada una registrada (prompt,
  respuesta cruda, confianza extraída, timestamp) en el JSON de
  resultados.
- Margen recalculado para las 4 evidencias, con
  `derivar_paisaje`/`derivar_consenso` aplicado a cada rama δ.
- Tabla de resultados comparada explícitamente contra esta tabla de
  pre-registro — coincida o no, se reporta como está, sin ajustar H0/H1
  después de ver el dato.
- `POLITICAS`, `mecanica.py`, `confianza.py`, `kernel/deliberation/`
  intactos — verificado por `git diff` y por la suite completa de
  deliberación, igual criterio que ADR-0012 §4.

## Alcance explícitamente fuera de esta iteración

- Ruta multi-objetivo (`_producir_por_objetivo`) — sigue sin tocarse.
- Multi-tensión / Parte G — sigue sin tocarse.
- Hallazgo D1 (margen como propiedad de la evidencia bajo regla) — ya
  cerrado en 5.1, no se reabre.
- Cualquier comparación de "calidad" LLM vs. regla — la hipótesis es
  sobre variabilidad del margen, no sobre superioridad.

## Resultado

Script `backend/scripts/experimentos/consenso_barrido_evidencia_llm.py`
ejecutado contra Postgres real y OpenAI real (`gpt-4o-mini`,
`temperature=0`), run_id `20260803T102508`,
`backend/experiments/results/consenso_barrido_evidencia_llm_20260803T102508.json`.
4 evidencias reales (2/3/4/5 errores) × 4 ramas δ in-memory cada una:

| Evidencia (errores) | Propuesta Remediar | Propuesta Orientar | Margen |
|---|---|---|---|
| 2 | reforzar : 0.9500 | avanzar-con-andamiaje : 0.8500 | 0.1000 |
| 3 | reforzar : 0.9500 | avanzar-con-andamiaje : 0.8500 | 0.1000 |
| 4 | reforzar : 0.9500 | avanzar-con-andamiaje : 0.8500 | 0.1000 |
| 5 | reforzar : 0.9500 | avanzar-con-andamiaje : 0.8500 | 0.1000 |

Las confianzas declaradas por Remediar-LLM y Orientar-LLM son **idénticas
byte a byte en las 4 evidencias** (0.9500/0.8500, margen 0.1000) — el
mismo margen que el punto exploratorio de ADR-0012 §3 (0.85/0.95, margen
0.10), ahora confirmado como estable, no un accidente de una sola
corrida. La curva δ ∈ {0.00, 0.05, 0.10, 0.15} es también idéntica en
las 4 evidencias: RESUELTA en δ ≤ 0.10, APLAZADA en δ=0.15, sin
excepción.

**H0 confirmada, H1 rechazada.** Pese a que el instrumento v2 expone
explícitamente el número de errores en el prompt de Remediar-LLM y
Orientar-LLM (`errores` interpolado en el texto), el modelo (bajo
`temperature=0`) no usa esa señal para modular su confianza declarada
sobre la propuesta — responde con el mismo par de valores
independientemente de si la evidencia es "2 items incorrectos" o "5
items incorrectos". Consistente con la amenaza a la validez declarada en
el pre-registro (instrumento nunca antes probado contra LLM real) y con
la cláusula de que ningún resultado es un fracaso experimental: el
hallazgo es que la severidad, tal como se propagó en el prompt v2 (un
número aislado sin contexto adicional), no es una señal que el modelo
trate como relevante para su confianza — a diferencia de Diagnosticar-
LLM, que sí usa `errores` para decidir el booleano `dominada` (ese uso
no se puso en duda aquí, solo si Remediar/Orientar lo usan para su
propia confianza).

## Estado

**EJECUTADA — H0 confirmada (margen y curva δ idénticos en las 4
evidencias), H1 rechazada bajo las condiciones evaluadas.** Verificado
sin regresión contra la suite de guardianes P13 (21 passed contra
Postgres real: `test_P13_remediar_reglas_vs_llm.py`,
`test_P13_orientar_reglas_vs_llm.py`, `test_orientar_remediar_por_
objetivo.py`). Pendiente de incorporación al capítulo de Resultados de
la tesis — hallazgo relevante para la discusión: exponer una señal en el
prompt no garantiza que el LLM la use, distinción que solo esta
iteración deja medida.

---

# ITERACIÓN DE INVESTIGACIÓN 5.3 — Calibración de confianza de Diagnosticar (H10, contrato pendiente)

## Origen — auditoría causal de adaptación por nivel (2026-08-03)

Esta iteración no nace de una hipótesis abstracta: nace de una
verificación de suficiencia con datos reales (misma sesión, mismo día)
sobre si el ciclo de adaptación continua (`0799840`, "ciclo adaptativo
continuo", 2026-07-13) sostiene tanto el avance como el retroceso ante
evidencia nueva.

**Avance — confirmado con evidencia real.** Cuenta `estudiante.novato2`,
objetivo "Fundamentos de Python": evaluación real 0/2 → `reforzar` →
evaluación real 2/2 → tensión D1 (`tension_bloqueante`) → deliberación
(`mayor-confianza-declarada`) → cascada → `avanzar` → Adaptar cambia de
`visual/fundamentos` a `mixta/aplicacion`. Cadena verificada entrada por
entrada contra Postgres real (`T-000050…T-000060`, ver detalle en
memoria `adaptacion_por_nivel_cerrada_2026_08_03.md`).

**Retroceso — el mecanismo se activó pero no revirtió la decisión.**
Misma cuenta, misma sesión: una tercera evidencia (0/2, mismo objetivo
ya avanzado) sí produjo una nueva interpretación de Diagnosticar-LLM
(`dominada=False`) y sí abrió una nueva tensión D1 y una nueva
deliberación — la maquinaria de consenso funcionó exactamente igual que
en el avance. Pero la deliberación resolvió a favor de la interpretación
vieja: `confianza declarada = 1.0000` (dominada=True, evidencia de 2/2
correctas) venció a `confianza declarada = 0.9500` (dominada=False,
evidencia de 0/2 correctas). El proveedor confirmado como LLM real (no
`FakeLLMProvider`, que declara `0.80` fijo — ver
`runtime/domain/diagnosticar/provider.py:32-37`).

**Por qué esto no es un bug del kernel.** `palabra_en_pie`, la cascada
(`cascada_supersede`), `registrar_decision` y `calcular_confianza_efectiva`
hicieron exactamente lo que RFC-0006 A1–A8 exige — comparar confianzas
efectivas y resolver por margen. El problema está aguas arriba: en qué
significa y cómo se calcula la `confianza` que Diagnosticar declara al
crear el claim.

## Pregunta de investigación

¿Cómo debe calcularse la confianza declarada de una interpretación de
Diagnosticar para que represente la fuerza real de la evidencia del
estudiante (no solo la seguridad expresada por el LLM), de forma que la
readaptación continua pueda avanzar y retroceder correctamente ante
evidencia nueva?

## Auditoría del contrato actual (hecha hoy, sin tocar código)

**¿La confianza viene del LLM o del dominio?** Enteramente del LLM. El
prompt de `diagnosticar/productor_llm.py:56-67` pasa `competencia` y
`items_incorrectos` — **nunca `items_totales`**: el LLM no tiene forma
de distinguir "2 errores de 2 preguntas" de "2 errores de 20 preguntas".
`ejecutar_roundtrip` (`runtime/domain/shared/llm_roundtrip.py:21-41`) no
normaliza, escala ni acota el valor devuelto — solo exige que el campo
exista. El único límite es el de validez genérico de `ClaimEntry.
__post_init__` (`[0,1]`, ADR-0001 §4), no una regla de calibración.

**¿Existe ponderación por evidencia en la deliberación?** No, para D1.
`kernel/deliberation/mecanica.py:205`: `peso = pesos_asunto.get(asunto, 1)
if tipo == "D2" else 1` — el peso de política solo aplica a D2
(propuestas rivales), nunca a D1 (interpretaciones rivales, el caso de
Diagnosticar). Confirmado además por 5.2: incluso cuando el prompt SÍ
expone la severidad explícitamente (Remediar-LLM, Orientar-LLM), el
modelo declaró confianzas idénticas byte a byte en 4 niveles de
evidencia distintos — la exposición de la señal no garantiza su uso.

**¿La deliberación considera recencia?** Existe un mecanismo real y
deliberado (A6/A7, `kernel/deliberation/confianza.py:115-146`), pero
ancla la "edad lógica" a la **última validación de Validar en la cadena
causal del claim** — nunca a la recencia cruda de la interpretación.
Sin un ciclo de Validar de por medio (el caso de las tres evidencias de
esta auditoría, demasiado próximas entre sí), `edad_logica=0` para
ambos claims y `ce` se reduce exactamente a la confianza declarada — la
recencia estructural existe pero no tuvo nada que decaer todavía.

**¿Qué dice la documentación original sobre qué debía representar
`confianza`?** RFC-0002 §"Registro — hipótesis arquitectónica" (línea
176-186) — la hipótesis original de Knowledge Claim (2026-07-10, previa
a RFC-0006) ya daba el ejemplo canónico: *"el estudiante domina COMP-2
con confianza 0.81 ← respuestas 3, 4 y 8, tiempos, intentos"* — es
decir, confianza derivada de evidencia concreta, no de la introspección
libre de un modelo. RFC-0006 A2 ("Anclaje: en el estado en que el claim
fue aplicado, ce = confianza declarada") acepta la confianza declarada
como dato de entrada sin prescribir su origen — el álgebra congela qué
pasa con ella DESPUÉS de declarada, no cómo se calcula. **La brecha
entre la hipótesis original (evidencia → confianza) y la implementación
actual (LLM → confianza, sin evidencia estructurada) nunca fue cerrada
por ningún RFC/ADR — es un vacío normativo real, no una regresión.**

## Alternativas a evaluar (ninguna decidida todavía)

**A — Confianza híbrida dominio + LLM.** `confianza_final = w·evidencia_objetiva + (1-w)·confianza_llm`,
con `evidencia_objetiva` derivada de `items_incorrectos`/`items_totales`
(y, si se declara en alcance, dificultad/histórico). Más estable, menos
dependiente del LLM; reduce el margen interpretativo del agente.

**B — El LLM interpreta, el dominio calibra (postprocesado).** El LLM
mantiene su rol interpretativo (`dominada`, `razonamiento`); un
calibrador de dominio, puro y determinista (P13: cambia la
implementación, nunca el contrato), acota la confianza declarada según
el tamaño de muestra — p. ej. un techo que crece con `items_totales`
(2/2 no puede declarar lo mismo que 20/20). Conserva la interpretación
del agente; evita sobreconfianza estructural.

**C — Ponderación D1 en la política de deliberación.** Extender
`pesos_asunto`/una función equivalente para que D1 también pese por
fuerza de evidencia (tamaño de muestra, tipo de instrumento — pretest
vs. evaluación real), no solo D2. Preserva la arquitectura de
deliberación tal cual; el riesgo es que una interpretación mal calibrada
siga entrando al paisaje sin corregirse en el origen, solo se le resta
peso después.

Ninguna de las tres introduce un concepto nuevo de dominio (todas caen
dentro de "cómo se calcula `confianza_declarada`" o "cómo pesa `ce`",
ambos ya nombrados por RFC-0002/RFC-0006) — la decisión entre ellas es
de diseño pedagógico/experimental, no arquitectónica, y pertenece al
tesista.

## Alcance explícitamente fuera de esta iteración

- No se toca `kernel/`, `deliberation/`, `palabra_en_pie`, Orientar,
  Remediar ni Adaptar — la auditoría de hoy ya confirmó que funcionan
  correctamente dado el `confianza` que reciben.
- No se elige todavía entre A/B/C.
- No se modifica ningún prompt ni productor.
- La ruta multi-objetivo (`_producir_por_objetivo`) fue exactamente
  donde se hizo la verificación de hoy — no queda fuera de alcance como
  en 5.1/5.2, es el escenario que motivó esta iteración.

## Estado

**DECIDIDA — alternativa B (LLM interpreta, dominio calibra), refinada a
"evidencia objetiva × relevancia contextual" tras la comprobación
aritmética que descartó un techo fijo por instrumento (ver
[[iteracion 5.4]] a continuación).** No bloquea el cierre de "adaptación
por nivel" (F0/F1/F3, ver memoria
`adaptacion_por_nivel_cerrada_2026_08_03.md`) ni el cierre de
"adaptación continua" arquitectónica (mecanismo verificado y funcional)
— es una brecha de calidad de señal, con causa raíz ya localizada, no un
bloqueo estructural.

---

# ITERACIÓN DE INVESTIGACIÓN 5.4 — Contrato de confianza calibrada de Knowledge Claims (H10, propuesta pre-implementación)

## Pregunta de investigación

¿Qué función de calibración permite que los Knowledge Claims de
Diagnosticar representen la fuerza real de la evidencia — preservando la
capacidad del sistema para avanzar y retroceder — sin que instrumentos
de distinta naturaleza (pretest amplio vs. evaluación real dirigida a un
objetivo) compitan en una escala incompatible?

## Decisión de alternativa

Se descarta **C** (ponderar D1 en la política de deliberación): corrige
el síntoma, no la causa — la interpretación mal calibrada seguiría
entrando al paisaje. Se descarta también la primera forma de **B**
(techo fijo por tipo de instrumento: "pretest ≤ 0.70, evaluación real ≤
0.98") — la comprobación de abajo muestra que produce una regla rígida
falsa ("toda evaluación real vale más que todo pretest", sin importar
tamaño ni consistencia). Se adopta una forma refinada de B: **evidencia
objetiva (resultado × tamaño de muestra) ponderada por relevancia
contextual del instrumento (peso, no techo)**, combinada con la
confianza que el LLM declara vía `min()` — nunca vía promedio ponderado
con el LLM, para que una sobreconfianza del LLM nunca pueda superar lo
que la evidencia misma sostiene.

## Definición de `confidence` (contrato)

`confidence` de un Knowledge Claim de Diagnosticar **no** significa "qué
tan seguro está el LLM de su propia interpretación". Significa: **la
fuerza de la evidencia disponible para sostener esa interpretación**,
determinada por el resultado, el tamaño de la muestra y la relevancia
pedagógica del instrumento que la produjo — nunca por la introspección
libre del modelo. Orden de autoridad: **evidencia > contexto > LLM**. El
LLM puede interpretar (`dominada`, `razonamiento`) y declarar su propia
certeza, pero no define la fuerza estadística de la evidencia — el
dominio puede invalidar (recortar) esa declaración; jamás amplificarla.

## Fórmula propuesta

```
techo_muestra(n)        = 1 - k / n                    (k = 0.40)
confianza_evidencia_max = techo_muestra(n) × relevancia(tipo_evaluacion)
confianza_final         = min(confianza_llm, confianza_evidencia_max)
```

`k = 0.40` es la misma constante que ya validaba el ejemplo original
(n=2 → techo 0.80; n=20 → techo 0.98) — no se introduce un segundo
parámetro sin justificación. `relevancia(tipo_evaluacion)` son valores
representativos dentro de los rangos ya propuestos: `pretest = 0.75`,
`evaluación_módulo = 0.95` — parámetros de política, no constantes de
dominio (mismo reparto de responsabilidades que RFC-0006 §1 ya
establece para `ce`: el álgebra se congela, la política elige pesos).
`min()`, nunca promedio ponderado: una confianza LLM de 1.0 nunca puede
superar lo que la evidencia sostiene, pero una confianza LLM baja SÍ
puede recortar hacia abajo una evidencia fuerte (el LLM solo resta,
nunca amplifica).

**Variable diferida explícitamente — "consistencia"/historial.**
Requiere leer los claims previos de Diagnosticar sobre el mismo asunto,
algo que ningún productor consulta hoy. Queda fuera de esta primera
versión del contrato como extensión futura documentada, no como
pendiente silencioso — evita meter una segunda pieza de scope sin datos
que la justifiquen todavía.

## Restricción cuantitativa derivada (no estaba en la propuesta original)

Para que el Caso A (avance) se preserve frente a un pretest de muestra
mayor que la evaluación real, se requiere:

```
relevancia(evaluación_módulo) / relevancia(pretest) > techo_muestra(n_pretest) / techo_muestra(n_evaluación)
```

Con los tamaños de muestra reales de hoy (pretest n=12, evaluación
real n=2): el lado derecho es **1.2083**. Los valores representativos
elegidos (0.95 / 0.75 = **1.2667**) cumplen la restricción con margen
— pero NO cualquier combinación dentro de los rangos propuestos la
cumple (p. ej. pretest=0.85 / evaluación=0.90 → 1.06, no cumple). Esta
restricción es un criterio de aceptación cuantitativo para fijar las
constantes finales de política, no una sugerencia.

## Verificación contra datos reales ya recolectados (sin código nuevo)

Réplica aritmética de los tres claims reales de la sesión de hoy
(`T-000050`, `T-000056`, `T-000063`, cuenta `estudiante.novato2`,
confianzas ya declaradas por el LLM real, `gpt-4o-mini`):

| Claim | Instrumento | n | confianza LLM | confianza_evidencia_max | confianza final |
|---|---|---|---|---|---|
| T-000050 | Pretest | 12 | 0.95 | 0.7250 | **0.7250** |
| T-000056 | Evaluación real (2/2) | 2 | 1.00 | 0.7600 | **0.7600** |
| T-000063 | Re-evaluación real (0/2) | 2 | 0.95 | 0.7600 | **0.7600** |

- **Caso A (avance) — supera la comprobación:** T-000056 (0.7600) >
  T-000050 (0.7250) → la evaluación real de 2/2 sigue venciendo al
  pretest, exactamente como ocurrió hoy con el sistema sin calibrar.
- **Caso B (retroceso) — supera la comprobación:** T-000063 (0.7600)
  empata con T-000056 (0.7600) — incluso con evidencia igual de
  "fuerte" en magnitud, el desempate por recencia que YA EXISTE en el
  kernel (`sorted(claims, key=lambda c: (puntaje, str(c.id)), reverse=True)`,
  sin modificar) favorece al claim más nuevo → el retroceso sí ocurriría.

**A diferencia del techo fijo por instrumento (descartado), esta fórmula
no le da la victoria automática a "toda evaluación real" — se la da
porque, en este caso concreto, la evaluación real (n=2, dirigida) supera
al pretest (n=12, amplio) por el margen que la restricción cuantitativa
exige, no por ser de un tipo distinto.**

## Caso C — ejecutado con datos reales; la fórmula NO lo supera

**Ajuste de alcance frente al banco de preguntas real.** El banco de
pretest tiene 12 ítems (`banco v3`), no 30 como en el ejemplo
ilustrativo — se documenta la escala real usada, sin inflar el dato:
cuenta fresca `estudiante.casoc2`, pretest 11/12 correctas (91.7%, solo
1 error — dentro del régimen `dominada=True`, `_UMBRAL_ERRORES=2`),
seguido de una evaluación real del mismo objetivo con 0/2 (ambas
incorrectas). Vía HTTP real, Postgres real, LLM real (`gpt-4o-mini`).

| Claim | Instrumento | n | correctos | confianza LLM | dominada |
|---|---|---|---|---|---|
| T-000024 | Pretest | 12 | 11 | 0.9500 | **True** |
| T-000058 | Evaluación real | 2 | 0 | 0.9500 | **False** |

**Resultado sin calibrar (sistema actual):** empate en confianza
declarada (0.9500 ambos) → desempate por recencia → gana la evaluación
trivial de 2 preguntas → decisión final `reforzar/visual/fundamentos`,
descartando una evaluación amplia y consistente de 11/12. Exactamente el
fallo que Caso C buscaba exponer.

**Resultado con la fórmula propuesta (`k=0.40`, relevancia 0.75/0.95):**
`pretest_final = min(0.95, techo(12)×0.75) = 0.7250`;
`evaluación_final = min(0.95, techo(2)×0.95) = 0.7600`. **La evaluación
trivial sigue ganando (0.7600 > 0.7250) — la fórmula NO corrige Caso C.**

**Contradicción matemática con Caso A (no es un problema de constantes,
es de forma funcional).** Caso A exige
`relevancia_evaluación / relevancia_pretest > 1.2083` (para que la
evaluación real de 2/2 venza al pretest débil de 12 con 12 errores).
Caso C exige exactamente la desigualdad **inversa**,
`< 1.2083` (para que el pretest fuerte de 11/12 venza a la evaluación
trivial de 0/2) — **mismos tamaños de muestra (12 y 2) en ambos casos,
direcciones opuestas.** Ningún par fijo de pesos `relevancia(tipo)`
satisface las dos restricciones a la vez; el punto de cruce exacto
(1.2083) tampoco sirve, porque en ambos casos el reclamante más reciente
es distinto y el desempate por recencia fallaría igual para uno de los
dos.

**Causa raíz identificada: `confianza_llm` es casi degenerada — no
codifica la proporción de aciertos.** Tabulando TODAS las confianzas
reales recolectadas hoy por Diagnosticar-LLM:

| n | correctos | % correcto | confianza LLM |
|---|---|---|---|
| 12 | 0 (0%) | 0% | 0.9500 |
| 12 | 10 (83%) | 83% | 0.9500 |
| 12 | 11 (92%) | 92% | 0.9500 |
| 2 | 2 (100%) | 100% | 1.0000 |
| 2 | 0 (0%) | 0% | 0.9500 |
| 2 | 0 (0%), otra cuenta | 0% | 0.9500 |

Para n=12, la confianza declarada es **idéntica (0.9500) en las tres
observaciones**, sin importar si el resultado fue 0%, 83% o 92% de
aciertos — el mismo patrón que 5.2 ya encontró en Remediar/Orientar-LLM,
ahora confirmado también en Diagnosticar. La fórmula propuesta usa
`min(confianza_llm, techo×relevancia)` — pero si `confianza_llm` no
varía con el resultado, el `min()` casi nunca la deja actuar como señal
real: el techo termina siendo la única variable que decide, y el techo
(`techo_muestra(n)×relevancia(tipo)`) nunca incorporó la **proporción de
aciertos** — solo el tamaño de muestra y el tipo de instrumento. Por
eso Caso A y Caso C, que difieren únicamente en qué tan bueno fue el
resultado (no en n ni en tipo), no pueden distinguirse: la fórmula
actual es ciega precisamente a la variable que los diferencia.

**Implicación para el contrato — pendiente de decisión, no resuelta
aquí.** La pieza que falta no es ajustar `k` o `relevancia`: es incluir
una `confianza_evidencia` que dependa explícitamente de
`items_correctos/items_totales` (proporción), no solo de `n`. Un
candidato con respaldo estadístico (no arbitrario) es el límite
inferior de un intervalo de Wilson sobre la proporción observada — crece
con n y con la proporción de aciertos a la vez, exactamente lo que
`techo_muestra(n)` no hace hoy. `relevancia(tipo_evaluacion)` seguiría
existiendo, pero como modificador secundario sobre esa fuerza
estadística, no como el factor que decide junto a un `n` desnudo. No se
elige esta vía todavía — es una opción a evaluar, con esta comprobación
como evidencia de por qué la forma actual es insuficiente.

## Ubicación arquitectónica (si se implementa)

Función pura nueva, local a `runtime/domain/diagnosticar/` (p. ej.
`calibracion.py`), invocada por `productor_llm.py` **antes** de
construir el `TransitionIntent` — transforma `confianza_llm` en
`confianza_final` antes de que el claim exista. No toca `kernel/`, no
toca `deliberation/`, no añade campos a `Provenance` ni al contrato de
`ClaimEntry` (P13: mismo tipo de claim, mismo asunto, mismo reducer;
cambia únicamente cómo se calcula un valor que el productor ya
declaraba). `relevancia(tipo_evaluacion)` y `k` viven como parámetros de
una política versionada local a Diagnosticar — mismo patrón de "reparto
de responsabilidades" que `Politica` ya usa para `delta`/`theta`/
`pesos_asunto` en la deliberación, sin fusionarse con ella.

## Estado

**PROPUESTA REFUTADA EN SU FORMA ACTUAL — Caso C ejecutado con datos
reales y la fórmula `min(confianza_llm, techo_muestra(n)×relevancia(tipo))`
no lo supera.** Caso A y Caso B siguen superando la comprobación (ver
arriba), pero Caso C demuestra que ningún par fijo de pesos
`relevancia(tipo)` puede satisfacer las tres condiciones a la vez —
contradicción matemática derivada, no una cuestión de afinar constantes.
Causa raíz identificada con datos reales: `confianza_llm` no varía con
la proporción de aciertos (0.9500 idéntico para n=12 con 0%, 83% y 92%
de aciertos), así que la fórmula nunca tuvo acceso a la señal que Caso A
y Caso C necesitan para diferenciarse. **Este es exactamente el tipo de
hallazgo que justificaba no congelar parámetros todavía — evitó
implementar una fórmula que habría fallado en producción.**

Pendiente, en orden: (1) decisión del tesista sobre si incorporar una
`confianza_evidencia` basada en proporción de aciertos (p. ej. límite
inferior de Wilson u otra función con esa propiedad) en vez de, o además
de, `relevancia(tipo)`; (2) verificar la fórmula revisada contra los
mismos tres casos reales ya recolectados (Caso A, B, C — sin necesidad
de nuevas cuentas, los datos ya existen); (3) pre-registro de hipótesis
H0/H1 al estilo de 5.1/5.2; (4) recién entonces, implementación. Sin
código tocado — ni kernel, ni deliberación, ni ningún prompt. Cuentas de
prueba creadas hoy para esta verificación: `estudiante.novato2`,
`estudiante.conocedor2`, `estudiante.casoc`, `estudiante.casoc2` — datos
reales conservados en Postgres para reanalizar sin repetir las
llamadas LLM.

---

# ITERACIÓN DE INVESTIGACIÓN 5.5 — Wilson score lower bound sobre los Casos A/B/C (H10, pre-registro ejecutado sobre datos ya recolectados)

## Pregunta de investigación (pre-registrada antes de calcular)

¿El límite inferior de un intervalo de Wilson sobre la proporción de
aciertos ordena correctamente los tres escenarios reales A/B/C (Caso A:
avance debe ganar; Caso B: retroceso debe poder ganar; Caso C: pretest
fuerte debe ganar sobre evaluación trivial), sin necesidad de ninguna
llamada LLM nueva — reutilizando los claims ya almacenados en Postgres
de 5.4?

## Hipótesis parcial

- **H0**: Wilson por sí solo NO ordena correctamente los tres casos —
  al menos uno falla, revelando que hace falta una variable adicional
  (más allá de fuerza estadística pura).
- **H1**: Wilson por sí solo ordena correctamente los tres casos — la
  fuerza estadística de la proporción observada es suficiente como
  `confianza_evidencia`, sin necesitar ningún término adicional de
  recencia o relevancia.

## Método

Sin llamadas LLM nuevas — reutiliza los `confianza`/`items_incorrectos`/
`items_totales` ya persistidos en Postgres de 5.4. Corrección de
semántica frente al primer intento (importante, documentada porque casi
produce una conclusión equivocada): el límite de Wilson debe calcularse
sobre el conteo que **sostiene la afirmación propia de cada claim** —
`correctos` cuando `dominada=True`, `incorrectos` cuando `dominada=False`
— no siempre sobre `correctos`. Calcular Wilson sobre `correctos` para
un claim `dominada=False` mide la fuerza equivocada (la de la hipótesis
contraria). Fórmula estándar, `z=1.96` (95%):

```
p = k/n
centro = (p + z²/2n) / (1 + z²/n)
margen = z·√(p(1−p)/n + z²/4n²) / (1 + z²/n)
Wilson_LB = max(0, centro − margen)
```

## Resultado

| Comparación | Claim A | Wilson_LB | Claim B | Wilson_LB | Gana |
|---|---|---|---|---|---|
| Caso A | T-000056 (eval. 2/2, dominada=True) | 0.3424 | T-000050 (pretest 0/12, dominada=False) | 0.7575 | **T-000050 (pretest viejo)** |
| Caso B | T-000063 (re-eval. 0/2, dominada=False) | 0.3424 | T-000056 (eval. 2/2, dominada=True) | 0.3424 | **empate exacto** |
| Caso C | T-000024 (pretest 11/12, dominada=True) | 0.6461 | T-000058 (eval. 0/2, dominada=False) | 0.3424 | **T-000024 (pretest)** ✓ |

**H0 confirmada, H1 rechazada.** Wilson ordena correctamente Caso C
(razón por la que se propuso), pero **falla Caso A**: el pretest viejo
(0/12, una negativa muy grande y estadísticamente decisiva) vence a la
evaluación real nueva (2/2, una muestra pequeña) — el avance real que
el sistema sin calibrar SÍ registra hoy dejaría de registrarse. Caso B
queda en el mismo empate que sin calibrar — Wilson no lo mejora ni lo
empeora, sigue dependiendo del desempate por recencia ya existente en
el kernel.

## Por qué falla — no es un error de fórmula, es un desajuste de modelo

El límite de Wilson responde correctamente a la pregunta *"¿cuánto
puedo confiar en esta proporción como estimador de un parámetro fijo,
dado el tamaño de muestra?"* — es exactamente el instrumento correcto
para inferir un parámetro **estático**. Pero el parámetro que
Diagnosticar interpreta (el dominio del estudiante sobre un objetivo)
**no es estático por diseño**: la adaptación continua existe
precisamente porque se espera que cambie con el aprendizaje. Comparar
dos observaciones separadas en el tiempo como si fueran dos muestras
independientes del mismo parámetro fijo — que es lo que Wilson asume —
penaliza exactamente la señal que el sistema necesita detectar: que el
estudiante mejoró. 0/12 es, en efecto, evidencia estadística muy fuerte
de que un estudiante NO domina un objetivo — pero solo si asumimos que
su dominio no cambió desde entonces. Esa suposición es la que rompe
Caso A.

## Conclusión — dos ejes ortogonales, ninguno sustituye al otro

Caso C y Caso A/B están señalando **dos variables distintas**, no la
misma:

1. **Fuerza estadística de una observación individual** (cuántas
   preguntas, qué proporción) — Wilson la resuelve correctamente (Caso
   C).
2. **Peso por recencia/cambio en el tiempo** (una observación más
   reciente debe poder pesar más que una más antigua y estadísticamente
   más "fuerte", precisamente porque el parámetro cambia) — Wilson no
   la captura, y ninguna de las fórmulas probadas hasta ahora
   (`techo_muestra(n)`, `relevancia(tipo)`, Wilson puro) la incluye
   como eje independiente.

El kernel ya tiene un mecanismo de recencia (`edad_logica`, A6/A7,
`calcular_confianza_efectiva`) — pero solo decae un claim después de un
ciclo de Validar, no en cada nueva interpretación de Diagnosticar; no
resuelve por sí solo Caso A/B tal como se presentaron hoy (sin Validar
de por medio entre las evidencias).

**Ninguna fórmula de un solo eje (ni tamaño de muestra, ni tipo de
instrumento, ni fuerza estadística Wilson) supera los tres casos a la
vez.** El contrato de confianza calibrada necesita combinar **fuerza
estadística de la observación × peso por recencia** como dos factores
independientes — no una sustituyendo a la otra. Definir ese segundo eje
(qué tan rápido debe decaer la relevancia de una observación anterior
frente a una nueva) es una decisión de diseño pedagógico nueva, todavía
sin explorar, y es el bloqueante real para cerrar el contrato.

## Estado

**EJECUTADA — H0 confirmada, H1 rechazada.** Wilson puro no basta: gana
Caso C, pierde Caso A, empata Caso B. Hallazgo estructural: la
calibración necesita un eje de recencia/cambio temporal además de un
eje de fuerza estadística — ninguna fórmula probada hasta ahora (5.4,
5.5) lo tiene. No se implementa nada. Sin código tocado. Próximo paso
propuesto (no iniciado): diseñar el eje de recencia antes de intentar
una nueva fórmula combinada — candidatos a explorar incluyen reutilizar
`edad_logica` de forma más agresiva (decaer también sin Validar) o un
peso explícito por antigüedad de la evidencia dentro de la propia
`confianza_evidencia`, ninguno decidido todavía.

---

# ITERACIÓN DE INVESTIGACIÓN 5.6 — Modelo de vigencia temporal de Knowledge Claims (H10, eje de recencia)

## Pregunta de investigación

¿Qué modelo permite que evidencia nueva pueda superar evidencia
histórica estadísticamente más fuerte cuando corresponde (Caso A), sin
permitir que evidencia nueva trivial derrote evidencia histórica fuerte
cuando NO corresponde (Caso C) — usando los tres casos reales A/B/C ya
recolectados, sin llamadas LLM nuevas?

## Por qué `edad_logica` (A6/A7) no se reutiliza directamente

Confirmado por revisión de `kernel/deliberation/confianza.py:122-131`:
`edad_logica` se ancla a la **última validación de Validar en la cadena
causal DEL PROPIO claim** — mide "¿este claim sigue recibiendo
mantenimiento?", no "¿sigue representando el estado actual del
estudiante?". Un claim puede tener `edad_logica=0` (nunca validado) y
aun así estar pedagógicamente obsoleto porque aparecieron varias
interpretaciones rivales nuevas después — ningún evento rival lo toca,
por diseño (A7, localidad causal: solo la cadena causal PROPIA cuenta).
Son dos preguntas distintas; extender A6/A7 para responder la segunda
mezclaría dos conceptos que el RFC-0006 mantiene deliberadamente
separados.

## Candidato descartado por cálculo — recencia pura (decaimiento simétrico)

Antes de diseñar candidatos nuevos, se prueba si un decaimiento por
recencia simétrico (`peso = e^(−λ·edad)`, sin distinguir dirección del
cambio) resuelve los tres casos, reutilizando los mismos `Wilson_LB` de
5.5:

```
Caso A necesita: e^(−λ) < Wilson(nuevo)/Wilson(viejo) = 0.3424/0.7575 = 0.4520
Caso C necesita: e^(−λ) > Wilson(nuevo)/Wilson(viejo) = 0.3424/0.6461 = 0.5299
```

**Mismo tipo de contradicción que `relevancia(tipo)` en 5.4: un único
`λ` simétrico no puede satisfacer ambas desigualdades a la vez** — la
recencia pura, sin importar cómo se calibre, tiene el mismo problema
estructural. Esto descarta el Candidato A (decaimiento exponencial
simple) y, por la misma lógica, el Candidato B (ventana de N más
recientes con corte binario: si solo la última evaluación contara,
Caso C fallaría exactamente igual que con recencia pura, porque
"ignorar todo lo anterior" es el caso límite de un decaimiento muy
agresivo).

## Por qué el problema no es simétrico — la dirección del cambio importa

Caso A y Caso C tienen la misma topología (claim viejo con `n` grande
vs. claim nuevo con `n` pequeño) pero necesitan ganadores opuestos —
porque no son la misma situación: Caso A es una interpretación
**mejora** (`dominada`: False→True) y Caso C es una interpretación
**retroceso** (`dominada`: True→False). Ningún factor simétrico
(recencia, tipo de instrumento, tamaño de muestra) puede distinguir
"mejorar" de "empeorar" porque ninguno de esos factores conoce la
dirección del cambio — solo la magnitud. La variable que faltaba en
todos los intentos anteriores (5.4, 5.5, y el candidato de recencia
pura de arriba) no es una variable adicional del mismo tipo: es una
**asimetría de política** entre creer una mejora y creer un retroceso.

## Candidato evaluado — regla asimétrica mejora/retroceso (cercana en espíritu al Candidato C, "cambio de estado explícito")

**Regla:** cuando la nueva interpretación de Diagnosticar contradice a
la vigente sobre el mismo asunto —

- Si la nueva propone **mejora** (`dominada`: False→True): se acepta si
  `Wilson_LB(nueva)` supera un umbral bajo absoluto (evidencia mínima de
  que la mejora no es puro ruido — p. ej. `> 0`, dado al menos una
  observación positiva).
- Si la nueva propone **retroceso** (`dominada`: True→False): se acepta
  solo si `Wilson_LB(nueva) ≥ Wilson_LB(vigente)` — debe igualar o
  superar la fuerza estadística de lo que intenta revertir. El empate
  se resuelve por el desempate de recencia que YA EXISTE en el kernel
  (`sorted(..., key=str(id), reverse=True)`), sin tocarlo.

**Verificación contra los tres casos reales (sin código, misma
aritmética Wilson de 5.5):**

| Caso | Dirección | Regla aplicada | Resultado |
|---|---|---|---|
| A | mejora (False→True) | `Wilson(nuevo)=0.3424 > 0`? | ✅ acepta mejora — el avance real se registra |
| B | retroceso (True→False) | `Wilson(nuevo)=0.3424 ≥ Wilson(viejo)=0.3424`? | ✅ empate entra por `≥`, desempate de recencia (ya existente) resuelve a favor del retroceso |
| C | retroceso (True→False) | `Wilson(nuevo)=0.3424 ≥ Wilson(viejo)=0.6461`? | ✅ rechaza — el pretest fuerte no cae ante una evaluación trivial |

**Los tres casos reales se satisfacen simultáneamente por primera vez en
la cadena H10** — ninguna fórmula anterior (confianza LLM cruda,
`techo_muestra(n)×relevancia(tipo)`, Wilson puro, recencia simétrica
pura) lo había logrado.

**Por qué es defendible pedagógicamente, no solo aritméticamente.** La
asimetría no es arbitraria: hipotetizar que un estudiante mejoró y
avanzar contenido es de bajo costo si resulta incorrecto (el estudiante
ve contenido algo más avanzado de lo ideal, recuperable); hipotetizar
que un estudiante retrocedió y remediar contenido ya dominado tiene un
costo distinto (tiempo del estudiante en contenido que ya domina,
riesgo de desmotivación) — de ahí que el retroceso exija evidencia al
menos tan fuerte como lo que revierte, mientras el avance no. Esta
asimetría de costos de error (falso avance vs. falso retroceso) es
citable en la tesis como una decisión de diseño pedagógico explícita,
no un artefacto matemático.

## Alcance explícitamente no decidido aquí

- El umbral exacto para "mejora" (`> 0` es el mínimo defendible —
  cualquier evidencia positiva no nula — pero podría ajustarse a un
  valor mayor).
- Si `Wilson_LB` es la función de fuerza estadística final, o si el
  tesista prefiere otra (5.5 solo estableció que ALGUNA función
  sensible a la proporción es necesaria).
- Casos con más de dos claims rivales simultáneos (fuera del alcance de
  A/B/C, que son siempre pares).
- La ubicación exacta de esta regla (¿vive en el calibrador de
  Diagnosticar, como 5.4 propuso, o necesita tocar la política de
  deliberación D1? — dado que la regla depende de comparar CONTRA el
  claim vigente, no es puramente local a Diagnosticar como 5.4 asumía;
  esto es una diferencia arquitectónica real pendiente de resolver
  antes de implementar).

## Estado

**EJECUTADA — candidato encontrado que supera los tres casos reales
simultáneamente por primera vez, pendiente de aprobación del tesista y
de resolver su ubicación arquitectónica (nota final de "Alcance").** No
se implementa nada. Sin código tocado. Próximo paso, si se aprueba:
pre-registro de hipótesis H0/H1 al estilo de 5.1/5.2 sobre esta regla
específica, luego implementación en un solo commit pequeño (Engineering
Gate: define su propio Diseño→Boundary→HTTP si aplica, pero esta pieza
vive enteramente en `runtime/domain/diagnosticar/` y posiblemente
`kernel/deliberation/`, a confirmar).

---

# ITERACIÓN DE INVESTIGACIÓN 5.7 — Ubicación arquitectónica de la política de revisión de Knowledge Claims (H10, Engineering Review dirigida)

## Pregunta de investigación

¿Debe la regla asimétrica de aceptación mejora/retroceso (5.6) vivir en
el productor Diagnosticar, en la resolución D1 de la deliberación, o en
un componente de política independiente — sin violar P13, sin
contaminar el kernel con semántica pedagógica, preservando que
Diagnosticar solo propone interpretaciones y que la deliberación
resuelve conflictos?

## Método — auditoría documental, no implementación

Se responde leyendo RFC-0006 y el código del kernel tal como existen
hoy, no por preferencia de diseño. Esta es una Engineering Review
dirigida (CLAUDE.md, actualización 2026-07-12): aplica porque aparece
una posible modificación de un RFC ya aceptado — exactamente el
disparador que la vuelve obligatoria.

## Opción B (dentro de D1) — descartada, requiere modificar RFC-0006

RFC-0006 §4 ("Resolución por tipo") no deja la regla de D1 como
parámetro de política — la fija explícitamente:

> **"D1 (interpretativo) — gana la evidencia: se acepta el claim con
> mayor confianza efectiva si el margen sobre el rival supera el umbral
> de discriminación δ (política)."**

Nótese el contraste con D2, en la misma sección: *"los pesos son
configuración versionada"* — esa cláusula de "versionable" existe
explícitamente para D2 y está **ausente** para D1. D1 es "mayor ce
gana", punto — una regla simétrica, normativa, sin excepción declarada
por dirección del cambio. Una regla que trate mejora y retroceso
distinto **es, por definición, una regla distinta de "mayor ce gana"**
— cambiarla es enmendar RFC-0006 §4, no elegir una política dentro de
él.

**Tampoco puede rodearse empujando la asimetría dentro de `ce`
(`calcular_confianza_efectiva`, que SÍ es explícitamente versionable
por política, RFC-0006 §1).** A7 ("localidad causal") acota
exactamente qué puede leer `ce`: *"la cadena causal del claim (su
respaldo hacia atrás; las decisiones y validaciones derivadas hacia
adelante) y los facts de su asunto"* — un **claim rival** (el vigente,
contra el que se compararía para saber si esto es mejora o retroceso)
no es un fact, no es el propio respaldo, no es una decisión ni
validación derivada del claim: leerlo violaría A7 tal como está escrito
hoy. **Opción B queda descartada por dos vías independientes** (regla
de D1 explícita en RFC-0006 §4; A7 impide que `ce` conozca al rival) —
no es una preferencia de diseño, es una contradicción documental real.
Engineering Gate pregunta 4 ("¿requiere modificar un RFC?"): si la
respuesta fuera Opción B, sí — **DETENERSE**, que es exactamente lo que
esta entrada hace.

## Opción A (dentro de Diagnosticar), en su forma original — también descartada

La primera lectura de Opción A ("Diagnosticar decide aceptar/rechazar
el cambio antes de producir el claim") choca con un precedente histórico
real y ya documentado en el propio código: el commit `504e09d`
("mapa completo — el Runtime interpreta TODA la evidencia del
diagnóstico", 2026-07-13) corrigió exactamente el bug de que
*"la guardia global anterior dejaba 7 de 8 competencias de un
diagnóstico sin interpretar"* — el contrato vigente de Diagnosticar
(`runtime/domain/diagnosticar/productor.py:28-35`) es interpretar
**cada** hecho evaluativo nuevo, siempre, sin excepción condicional. Si
Diagnosticar decidiera "no producir claim" cuando la evidencia nueva no
alcanza el umbral asimétrico, estaría regresando exactamente ese bug ya
cerrado — evidencia real que simplemente deja de interpretarse.

## Opción A refinada — la que sí funciona, sin tocar kernel ni RFC-0006

La distinción que resuelve el conflicto: Diagnosticar **siempre**
produce un claim (mapa completo intacto) — lo que la regla asimétrica
decide no es *si* produce el claim, sino **qué `confianza` declara al
producirlo**. Concretamente:

```
Diagnosticar, al interpretar un hecho nuevo sobre un asunto que ya
tiene un claim vigente contradictorio:

  fuerza_nueva = Wilson_LB(soporte de la nueva interpretación)
  fuerza_vigente = calcular_confianza_efectiva(claim_vigente, estado, politica)
                   # función YA existente, importada sin modificar

  si la nueva interpretación es MEJORA (False→True):
      confianza_declarada = fuerza_nueva          # umbral bajo, se declara tal cual
  si la nueva interpretación es RETROCESO (True→False):
      confianza_declarada = fuerza_nueva si fuerza_nueva >= fuerza_vigente
                             si no, un valor que D1 "mayor ce gana" no puede ganar
                             (p. ej. 0, o la misma fuerza_nueva sin más —
                             el punto es que la comparación estándar decidirá)

  registrar_claim(..., confianza=confianza_declarada)   # reducer SIN modificar
```

Esto **no toca `kernel/`, no toca `deliberation/mecanica.py`, no toca
`confianza.py`, no enmienda RFC-0006 §4** — D1 sigue resolviendo "mayor
ce gana" exactamente como está escrito; la asimetría vive enteramente
en qué `confianza` declara Diagnosticar ANTES de que exista el claim
(A2: "en el estado en que el claim fue aplicado, ce = confianza
declarada" — ninguna norma restringe qué puede declarar un productor,
solo cómo evoluciona `ce` después). Diagnosticar SÍ necesita leer el
claim vigente rival y llamar `calcular_confianza_efectiva` sobre él —
pero eso ocurre dentro del **productor** (que siempre ha podido leer
todo `estado.claims` libremente; A7 acota `ce`, no a los productores),
nunca dentro del kernel.

## Opción C, reconsiderada

Empaquetar esta lógica en un módulo propio (`runtime/domain/
diagnosticar/calibracion.py`, tal como 5.4 ya proponía) es una decisión
de organización de código, no una ubicación arquitectónica distinta: el
único llamador sigue siendo el productor de Diagnosticar, antes de
`registrar_claim`. Opción C, bien entendida, **es Opción A refinada con
buen factoring** — no una tercera capa nueva del sistema.

## Respuesta a los 4 criterios del tesista

1. **P13 (mínima modificación del contrato):** cumplido — mismo tipo de
   claim, mismo asunto, mismo reducer; cambia solo cómo se calcula un
   valor que el productor ya declaraba.
2. **No contaminar el kernel con semántica pedagógica:** cumplido —
   cero cambios en `kernel/`.
3. **Diagnosticar solo propone interpretaciones:** preservado — sigue
   proponiendo una interpretación por hecho, siempre: la asimetría
   ajusta la confianza de la propuesta, no si se hace o no.
4. **Deliberación resuelve conflictos:** preservado sin cambios — D1
   sigue siendo "mayor ce gana", tal como RFC-0006 §4 lo fija; la
   asimetría ya viene resuelta en los números que llegan a competir.

## Estado

**EJECUTADA — Opción B descartada por contradicción documental directa
(RFC-0006 §4 + A7); Opción A original descartada por precedente
histórico (`504e09d`, mapa completo); Opción A refinada (calibrar la
`confianza` declarada por Diagnosticar, comparando contra
`calcular_confianza_efectiva` del claim vigente, sin tocar kernel ni
RFC) queda como la única opción que supera los 4 criterios sin requerir
enmienda de ningún RFC.** Aprobada por el tesista — ver pre-registro
formal en la Iteración 5.8, a continuación. Sin código tocado.

---

# ITERACIÓN DE INVESTIGACIÓN 5.8 — Pre-registro H0/H1: política asimétrica de revisión de confianza declarada (H10, previo a implementación)

## Pregunta de investigación

¿Una política de calibración asimétrica de confianza declarada —basada
en fuerza estadística de la evidencia y comparación contra el claim
vigente— permite que el sistema de adaptación continua acepte mejoras
reales y rechace retrocesos espurios, sin modificar la deliberación D1
ni ningún RFC?

## Hipótesis parcial

**H0 (nula):** la política propuesta no mejora la resolución de
conflictos entre Knowledge Claims respecto al mecanismo actual
(confianza declarada por LLM sin calibrar). Se considera confirmada si
falla al menos uno de los tres patrones:

- Caso A: evidencia nueva positiva NO logra superar evidencia histórica
  negativa.
- Caso B: evidencia nueva negativa equivalente NO logra revertir la
  evidencia vigente.
- Caso C: evidencia nueva negativa pequeña SÍ derrota evidencia
  histórica fuerte (falso retroceso).

**H1 (alternativa):** la política resuelve correctamente los tres
patrones de cambio:

| Patrón | Dirección | Condición | Resultado esperado |
|---|---|---|---|
| Mejora | `False→True` | `fuerza_nueva > theta_mejora` | el nuevo claim puede superar al anterior |
| Retroceso equivalente | `True→False` | `fuerza_nueva ≥ fuerza_vigente` | el nuevo claim puede revertir |
| Retroceso débil | `True→False` | `fuerza_nueva < fuerza_vigente` | el nuevo claim pierde ante el vigente |

## Variables que se congelan en este pre-registro (antes de escribir código)

**1. `evidence_strength()` como abstracción, no como compromiso con
Wilson por nombre.** 5.5 solo demostró que hace falta una función
sensible a la proporción de aciertos — no que Wilson sea la única
válida. Se congela la interfaz:

```
evidence_strength(k_soporte: int, n: int) -> Decimal en [0, 1]
```

con implementación inicial `evidence_strength = Wilson_LB` (z=1.96).
Cualquier cambio futuro de función es una nueva versión de política,
igual que `Politica` ya versiona `delta`/`theta`/`pesos_asunto`
(RFC-0006 §1) — nunca una edición silenciosa de la misma versión.

**2. `theta_mejora` como parámetro de política versionado, no
constante de dominio.** Valor inicial `theta_mejora = Decimal("0")` —
matemáticamente suficiente para Caso A (`Wilson_LB(2,2)=0.3424 > 0`),
pero es una decisión pedagógica (qué tan poco basta para creer una
mejora), no una necesidad matemática — vive en la política, versionada,
igual que `theta` de D3 ya vive en `Politica` (RFC-0006 §3).

**3. Definición exacta de "claim vigente".** Es **el claim de
`TipoClaim.INTERPRETACION` con el mismo asunto y `vigencia.vigente ==
True`** en el momento en que Diagnosticar procesa el nuevo hecho —
nunca "el último creado", "el de mayor confianza histórica" ni "todos
los claims del asunto". **Verificado hoy, sin código nuevo, que esta
definición es inambigua por construcción:** el orden de `enrutar()`
(`walkthrough.py:322-344`) comprueba `tension_bloqueante` (línea 336)
**antes** que `_evidencia_pendiente_de_diagnosticar` (línea 340) — por
lo tanto, cualquier tensión D1 pendiente sobre CUALQUIER asunto se
resuelve antes de que el grafo vuelva a rutear hacia "diagnosticar". En
el momento en que el productor de Diagnosticar se ejecuta, nunca puede
haber más de un claim `INTERPRETACION` vigente para el mismo asunto —
la consulta `next(c for c in estado.claims if c.tipo is
TipoClaim.INTERPRETACION and c.asunto == mi_asunto and
c.vigencia.vigente)` siempre devuelve 0 o 1 resultado, nunca ambiguo.

## Lo que este pre-registro NO modifica

`ClaimEntry`, `Provenance`, `TransitionIntent`, ningún reducer
(`registrar_claim` sin cambios), `mecanica.py` (D1 sigue "mayor ce
gana"), `confianza.py` (A6/A7 intactos), RFC-0006 (ninguna sección
enmendada). Confirmado por el análisis de 5.7, no reafirmado aquí de
nuevo salvo esta lista de cierre.

## Diseño experimental (para cuando se implemente)

Reutiliza los tres casos reales ya recolectados en Postgres (5.4/5.5/
5.6 — cuentas `estudiante.novato2`, `estudiante.casoc2`) como los tres
escenarios de aceptación — **sin necesidad de nuevas llamadas LLM para
la verificación aritmética**, pero la implementación real sí debe
ejecutarse contra el walkthrough completo (Postgres real) para
confirmar que el resultado observado en producción coincide con la
réplica aritmética ya hecha, igual criterio que 5.1/5.2 (réplica
in-memory primero, corrida real después). N=3 (A, B, C) — mismo criterio
de N=1 por escenario ya declarado como fortaleza metodológica, no
debilidad, en 5.1.

## Criterios de aceptación

- `evidence_strength()` y `theta_mejora` implementados como funciones/
  parámetros puros en `runtime/domain/diagnosticar/calibracion.py`
  (módulo nuevo) — ninguna llamada a LLM, reloj de pared ni azar (mismo
  criterio que las "transformaciones prohibidas" de RFC-0006 §1,
  aplicado aquí por analogía aunque esta pieza no sea `ce`).
- `productor_llm.py` de Diagnosticar importa `calibracion.py` y calcula
  `confianza` antes de construir el `TransitionIntent` — mismo
  contrato de `registrar_claim` (P13).
- Los tres casos (A, B, C) reproducidos contra Postgres real producen
  el resultado de la tabla de H1 — si alguno falla, se reporta como
  está, sin ajustar el umbral después de ver el dato (mismo criterio de
  pre-registro que 5.2).
- Suite `tests/runtime/` completa sin regresión (mismo umbral que
  iteraciones anteriores: 0 fallos nuevos).
- `git diff` confirma que `kernel/`, `deliberation/`, y
  `docs/architecture/RFC-0006*.md` quedan sin tocar.

## Alcance explícitamente fuera de esta iteración

- Elegir una `evidence_strength()` distinta de Wilson (queda como
  extensión futura, la abstracción ya lo permite).
- Ajustar `theta_mejora` a un valor distinto de 0 (decisión pedagógica
  posterior, informada por más datos).
- Consistencia/historial más allá del claim vigente inmediato (diferido
  desde 5.4, sigue diferido).
- Relación instrumento↔objetivo ("alineación", mencionada por el
  tesista en la discusión de 5.4) — no forma parte de esta política.

## Estado

**IMPLEMENTADA — con un bug encontrado y corregido en la primera
validación E2E real, y una pregunta semántica abierta descubierta en la
segunda (ver Iteración 5.9, a continuación).** `runtime/domain/
diagnosticar/calibracion.py` (nuevo, puro) + integración mínima en
`productor_llm.py` + `tests/runtime/domain/diagnosticar/
test_calibracion.py` (12 tests). Cero cambios en `kernel/`,
`deliberation/`, reducers, RFC-0006. Suite completa `tests/runtime/`:
416 passed, 0 failed.

**Bug encontrado y corregido (cuenta real `estudiante.calib1`):** la
regla de "mejora" original declaraba `fuerza_nueva` tal cual al
aceptar — pero D1 sigue siendo "mayor ce gana" sin modificar, así que
una mejora con evidencia pequeña (2/2, Wilson≈0.34) perdía de todos
modos contra un vigente con `ce` mayor (pretest 0/12, Wilson≈0.76),
pese a "aceptarse". Corregido: al aceptar, se declara `max(fuerza_nueva,
fuerza_vigente)` — empata con el vigente y gana por el desempate de
recencia ya existente en el kernel. Verificado con cuenta fresca
`estudiante.calib2`: avanza correctamente, tie exacto confirmado en
Postgres (0.3906 = 0.3906).

**Pregunta semántica abierta (misma cuenta, encadenando A→B en la
sesión real):** ver Iteración 5.9.

---

# ITERACIÓN DE INVESTIGACIÓN 5.9 — Persistencia de confianza tras una transición aceptada (H10, decisión semántica abierta)

## Pregunta de investigación

¿La confianza declarada de un claim debe representar únicamente la
fuerza estadística de la observación que lo originó (`evidence_
strength`), o el estado actual de creencia del sistema — que puede
heredar resistencia de la transición que superó para llegar a ser
vigente?

## Cómo apareció — no en la aritmética, en el encadenamiento real

5.6/5.8 verificaron Caso A y Caso B como transiciones **aisladas**,
cada una partiendo de un estado inicial fresco. Un estudiante real no
reinicia entre evidencias: la implementación de 5.8, corrida en cadena
sobre la MISMA cuenta (`estudiante.calib2`, real, Postgres real, LLM
real), reveló un efecto que ningún caso aislado podía mostrar.

## Ejecución real completa (misma cuenta, en orden, sin reiniciar)

| Paso | Evidencia | n | dominada | confianza declarada | vs. fuerza cruda |
|---|---|---|---|---|---|
| 1 | Pretest, 8/12 mal | 12 | False | 0.3906 | = cruda (primera evidencia, sin vigente) |
| 2 | Evaluación real, 2/2 bien (**mejora**) | 2 | True | **0.3906** | cruda=0.3424, **heredada** del vigente (fix de Caso A) |
| 3 | Re-evaluación real, 2/2 mal (**retroceso débil**) | 2 | False | **0.0000** | cruda=0.3424 — **rechazado**: 0.3424 < 0.3906 |
| 4 | Evidencia adicional, 3/3 mal (**retroceso más fuerte**) | 3 | False | **0.4385** | cruda=0.4385 = declarada — **aceptado**: 0.4385 ≥ 0.3906, ahora vigente |

**El sistema se comportó como histéresis real, no como un bug: una
evidencia débil (paso 3) no logró revertir la mejora; una evidencia más
fuerte (paso 4) sí lo logró.** El paso 4 fue necesario precisamente
porque el paso 2 "heredó" 0.3906 en vez de declarar su propia fuerza
cruda (0.3424) — el comportamiento es internamente consistente, pero es
una consecuencia real del fix de Caso A que 5.8 no anticipó ni
pre-registró.

## Hallazgo práctico concreto — no solo teórico

**Todas las evaluaciones reales del producto tienen exactamente `n=2`
preguntas** (`evaluation_service.py`, `max_score` fijo). El techo
absoluto de `evidence_strength` para CUALQUIER resultado de una
evaluación de `n=2` es `Wilson_LB(2,2) ≈ 0.3424` — tanto para un 2/2
perfecto como para un 0/2 total. **Consecuencia directa: una vez que un
claim hereda una confianza declarada por encima de 0.3424 (lo que
ocurre en cualquier "mejora" o "retroceso fuerte" cuyo vigente previo
tenía más fuerza que eso — exactamente el paso 2 de la tabla), ninguna
evaluación real futura de 2 preguntas podrá jamás revertirlo,
sin importar cuántas veces el estudiante falle.** Esto no es hipotético
— es el estado exacto de `estudiante.calib2` tras el paso 2, antes de
que el paso 4 (una evidencia simulada de n=3, mayor que lo que el
producto genera hoy) lo revirtiera.

## Dos hipótesis, ninguna decidida

**H0 — separar `confidence` de `evidence_strength`.** La confianza
declarada del claim (la que D1 compara) debe representar SOLO la
evidencia que lo originó — nunca heredar de una transición anterior.
Requiere persistir la fuerza cruda por separado (¿un campo nuevo en
`afirmacion` — sin tocar el contrato de `ClaimEntry` — o en
`Provenance`?) para que la calibración pueda leerla en vez de la
confianza declarada del vigente. Respeta literalmente el Caso B
pre-registrado en 5.8. Requiere decidir dónde vive ese dato nuevo.

**H1 — la confianza declarada ES el estado actual de creencia
(comportamiento ya implementado).** Una transición aceptada gana
estabilidad proporcional a la resistencia que superó — análogo a la
fuerza de un prior en actualización bayesiana secuencial. No requiere
ningún cambio de contrato (ya implementado, ya probado, 416 verdes).
Protege contra oscilación rápida (`domina→no domina→domina→no domina`)
con evidencia débil repetida. Su costo es el hallazgo práctico de
arriba: con instrumentos de evaluación de `n=2` fijos, el candado es
efectivamente permanente una vez cruzado el umbral.

## Lo que esta iteración NO decide

No elige entre H0 y H1 — es una decisión de diseño pedagógico real,
con el mismo peso que 5.7 le dio a la ubicación arquitectónica. Si se
elige H1, el hallazgo práctico (instrumentos de `n=2`) sugiere una
acción complementaria fuera del alcance de H10: ampliar el tamaño de
las evaluaciones reales de módulo — no una decisión de esta iteración,
solo la consecuencia que la deja visible.

## Pregunta de investigación derivada (pendiente)

¿Qué nivel de autoridad pedagógica debe tener una reevaluación breve
(n=2) para modificar el estado de dominio de una competencia? Esta
pregunta pertenece al diseño del instrumento de evaluación y es
conceptualmente independiente de la política de calibración de
confianza estudiada en H10. Su respuesta puede requerir una
investigación específica sobre el tamaño del instrumento, la
acumulación de evidencia o los criterios de reversión, y no debe
resolverse modificando la calibración sin evidencia adicional.

No es todavía una nueva iteración de investigación — no hay hipótesis
ni experimento definidos — es una pregunta derivada de 5.9 que se deja
registrada para no perderla. Si se investiga más adelante, esa cadena
(p. ej. H11) parte de aquí como origen, en vez de aparecer como una
modificación de H10.

## Decisión del tesista (2026-08-03)

**H10 adopta H1.** La confianza declarada representa el estado actual
de creencia del sistema — no únicamente la fuerza estadística aislada
de la última observación. Razón: H0 elimina la protección contra
oscilación rápida (`domina→no domina→domina→no domina`) ante evidencia
débil repetida, exactamente el riesgo que la histéresis de H1 existe
para prevenir; el problema observado en 5.9 no es un defecto de la
política de calibración, sino la interacción entre H1 (correcta) y un
instrumento de evaluación pequeño (`n=2` fijo). Separar la causa
(tamaño del instrumento) de la política que la expone evita corregir
en el lugar equivocado.

No se modifica código: H1 ya es el comportamiento implementado (416
tests verdes, validado E2E en Postgres real). La limitación de `n=2`
queda registrada como origen de la pregunta de investigación derivada
de la sección anterior — candidata a una futura H11 sobre autoridad
pedagógica de reevaluaciones breves — sin abrirla todavía como
iteración con hipótesis propia.

## Estado

**CERRADA — H1 adoptada (decisión del tesista, 2026-08-03).** Cadena
real completa (4 pasos, misma cuenta, Postgres real, LLM real)
documentada; sin cambios de código. Cadena completa H10: 5.1 → 5.2 →
5.3 → 5.4 (refutada) → 5.5 (refutada) → 5.6 (candidato encontrado) →
5.7 (ubicación resuelta) → 5.8 (implementada, un bug corregido en E2E
real) → 5.9 (esta, CERRADA — H1 adoptada, 2026-08-03).

---

# ITERACIÓN DE INVESTIGACIÓN 6.1 — Validez del instrumento experimental frente a la arquitectura final (2026-08-04)

> Abre una nueva serie (6.x): distinta pregunta de la familia 5.x (H10,
> calibración de confianza de RFC-0006). Ver `ADR-0016` y
> `ROADMAP-RFC-0006.md §8` para la cadena que motiva esta iteración —
> cerrada la misma sesión, commits `4fd6ed8`→`82df22b`.

## Puerta de entrada (Regla maestra)

1. **¿Qué pregunta de investigación responde?** Ver más abajo.
2. **¿Qué parte de la hipótesis fortalece?** La validez del método de
   medición de la hipótesis central (`THESIS_SCOPE_FREEZE.md`:
   *"una arquitectura multiagente basada en swarm intelligence puede
   adaptar contenido educativo... y mejorar la experiencia de
   aprendizaje"*) — sin esta iteración, cualquier ganancia pre→post
   medida sería inauditable frente a la pregunta "¿esa ganancia vino
   del swarm real, o de un componente ya retirado?".
3. **¿Qué variable afecta?** Ninguna variable pedagógica nueva —
   valida que las variables YA capturadas por `ExperimentResult`
   (ganancia pre→post, nivel, tiempo) se originan en la cadena
   `evidencia → deliberación real (POLITICAS["v2"]) → Entrega →
   contenido adaptado`, no en un artefacto de un pipeline anterior.
4. **¿Cómo se observará durante la demo?** Recorrido real en
   navegador: pre-test → módulo con adaptación visible (modalidad
   decidida por el swarm, citando su propio razonamiento) → post-test
   → comparación pre/post → exportación CSV/XLSX desde
   `/evidencia/investigacion`.
5. **¿Cómo aparecerá en Resultados y Discusión?** Como la sección que
   responde "amenazas a la validez de instrumentación" — la ganancia
   medida en cualquier `ExperimentResult` reportado en la tesis queda
   trazada hasta una deliberación real bajo `v2`, con `session_id` y
   margen citables, no solo un número agregado.

## Pregunta de investigación

¿El instrumento experimental construido en julio (`ExperimentResult`,
pre-test/post-test, `research_export_service`) mide correctamente el
efecto de una adaptación producida por la arquitectura multiagente
**tal como existe hoy** — `runtime/` LangGraph, sin `BaseAgent`
(`ADR-0011`, 2026-08-01), bajo `POLITICAS["v2"]` (`ADR-0012`/
`ADR-0016`, 2026-08-04) — o mide un pipeline que en el momento de su
construcción (`RESEARCH_LAYER_TECHNICAL_REPORT.md`, 2026-07-08) corría
bajo una arquitectura distinta?

## Hipótesis parcial

Si se ejecuta el recorrido completo pre-test → adaptación → post-test
con una cuenta real, entonces `ExperimentResult` debe poder trazarse,
sesión por sesión, hasta una `Entrega` producida por una deliberación
real del kernel bajo `v2` (`identidad.version_politica == "v2"`,
`estado.deliberaciones`/`decisiones` con contenido verificable) — no
solo hasta un registro numérico sin origen auditable.

## Por qué esta pregunta, no otra (decisión ya tomada, no reabrir)

Se descartó abrir esta iteración directamente con estadística
inferencial (ANOVA/Cohen's d, `app/experiment/analysis.py`, ya
construido pero nunca conectado al dashboard — ítem #2 de "mejoras
futuras" del informe de julio) precisamente porque esa estadística
sería sobre datos cuya procedencia arquitectónica todavía no estaba
confirmada tras `ADR-0011`/`ADR-0016`. Primero validez del
instrumento, después análisis — no al revés.

## Alcance de esta iteración (deliberado)

- **No agrega infraestructura nueva.** `ExperimentResult`, el banco de
  preguntas, `research_export_service` y los endpoints de
  `/api/students/knowledge-test/*` y `/api/research/*` ya existen y
  están probados (36 tests, `RESEARCH_LAYER_TECHNICAL_REPORT.md §7`).
- **No conecta la estadística inferencial** — queda para una iteración
  posterior (candidata a `6.2`), solo si esta se cierra con el
  instrumento confirmado válido.
- **No modifica `ExperimentResult` ni ningún reducer del kernel.**

## Implementación

Ninguna todavía — esta iteración es de **validación**, no de
construcción. El "qué se construye" es la ejecución documentada del
recorrido real, no código nuevo.

## Evidencia observable

- `estado.identidad.version_politica == "v2"` para la sesión de
  runtime asociada al estudiante de la corrida.
- Al menos una deliberación real (`estado.deliberaciones`) o una
  decisión directa D3 con confianza ≥ θ, citada por `session_id` y
  transición.
- `ExperimentResult` de esa misma cuenta con ganancia pre→post
  materializada.
- Exportación CSV/XLSX desde `/api/research/export` incluyendo esa
  fila.

## Variables fortalecidas

- **Independiente:** arquitectura de adaptación (`runtime/` LangGraph
  + `POLITICAS["v2"]`, ya fijada — no varía dentro de esta iteración).
- **Dependiente (validada, no medida todavía):** validez de
  instrumentación de `ExperimentResult` como proxy de la ganancia
  atribuible a la adaptación real del swarm.

## Amenazas a la validez (lo que esta iteración NO demuestra)

- No demuestra que la adaptación **mejora** el aprendizaje — solo que
  el instrumento que mediría esa mejora está midiendo el sistema
  correcto. La pregunta de efecto pedagógico (¿mejora medible?) queda
  para una iteración posterior, con N suficiente, no con una sola
  cuenta de validación.
- Con N=1 (o N pequeño) no hay poder estadístico — el objetivo es
  trazabilidad del instrumento, no significancia.

## Evidencia que deberá recolectarse

Recorrido E2E real, navegador real, cuenta de estudiante real:
login → diagnóstico (perfil VARK) → pre-test → al menos un ciclo de
evidencia real (`cycle-evidence`, dispara deliberación bajo `v2`,
confirmado alcanzable en `ADR-0016 §5/§9` de esta misma sesión) →
post-test → `/evidencia/investigacion` (comparación + exportación).

## Resultado (Capa 1 — trazabilidad arquitectónica, ejecutada)

Recorrido real ejecutado en navegador (backend + frontend reales,
`VERSION_POLITICA="v2"` sin overrides — mismo pre-check que
`ADR-0016` Fase 4.4, incluida la misma lección aplicada de entrada:
se encontraron y mataron dos procesos `vite` obsoletos de sesiones
anteriores antes de levantar los servidores limpios). Estudiante real
sembrado (`iteracion.6.1@upao.test`), login real, diagnóstico VARK
(18 preguntas) real, pre-test (12 preguntas) real, ruta generada por
el swarm ("Estrategia decidida... modalidad visual"), Misión 1 con
tres ciclos de práctica reales (`cycle-evidence` × 5 llamadas HTTP,
todas `200`) incluyendo un recurso pedagógico generado citando
`Origen: decisión pedagógica existente (modalidad(algorithms))`.

**Verificación directa contra Postgres real** (no inferida de la UI —
mismo criterio que exigió `ADR-0016 §9` tras el hallazgo del proceso
obsoleto):

```
session_id:        curso:0fbe4f4c...:estudiante:0cbdbe25...
version_politica:   v2
facts:              42       claims: 25
deliberaciones:     6 — todas Resuelta, márgenes reales:
                     0.1131, 0.0000×4 (empates D1/D2 reales), 0.2320
decisión vigente:    siguiente-paso(sesion), confianza=0.2307
```

**Conclusión de la Capa 1 (la pregunta de investigación central):**
el instrumento SÍ traza correctamente hasta una deliberación real
producida por `runtime/` LangGraph bajo `POLITICAS["v2"]` — no hay
indicio de que esté midiendo un pipeline retirado. La cadena completa
`evidencia real → deliberación real → decisión real → Entrega →
contenido adaptado visible en pantalla` quedó verificada de punta a
punta, con evidencia en Postgres, no solo en la UI.

## Hallazgo real (Capa 2, no anticipado)

El post-test tiene un gate real no documentado en
`RESEARCH_LAYER_TECHNICAL_REPORT.md`: **exige completar el 100% de la
Ruta de Aprendizaje (2/2 misiones), no solo el pre-test completado**
(que es lo único que exige `knowledge_test_service.start_attempt` a
nivel de servicio — el gate adicional vive en otra capa, confirmado
por el mensaje real del sistema: *"Debes completar toda la Ruta de
Aprendizaje antes de rendir el Post-Test"*). Decisión explícita del
tesista: no forzar el recorrido completo en esta sesión — mezclar el
cierre de una validación arquitectónica con una recolección
pedagógica extensa (2 misiones completas) arriesga tanto la calidad
de la evidencia como el objetivo original de la sesión. Este gate es
una condición experimental real del instrumento y debe respetarse al
diseñar la recolección de la Capa 2, no un obstáculo a saltarse.

## Bug real encontrado y corregido durante la validación (fuera de la hipótesis de investigación)

Al retomar la Capa 2 en la sesión siguiente para completar el recorrido
(Misión 1 + Misión Final → post-test), el gate de "ruta completa" del
hallazgo anterior resultó ser **estructuralmente inalcanzable para
cualquier estudiante**, no solo una condición a respetar. Root cause
verificado directo en Postgres (no en la UI), dos causas
independientes que se enmascaraban entre sí:

1. `knowledge_test_service.start_attempt` comparaba contra
   `LearningPath.total_modules`, que cuenta TODOS los
   `LearningObjective` del curso (4: Fundamentos de Python, Estructuras
   de control, Funciones y módulos, POO). Pero PED-004
   (`frontend/src/lib/experiences/index.ts`, `REFERENCE_MODULE_MODE`)
   ya documentaba — sin mencionar al Post-Test — que ningún estudiante
   puede alcanzar el Objetivo 3+ desde la Ruta real (`module3.ts`/
   `module4.ts` sin autorar todavía).
2. El gate leía `LearningPath.completed_modules`, un contador cacheado
   que solo escribe `update_module_progress`. Confirmado en Postgres
   real: tras completar Misión 1 Y Misión Final (2 `PathModule` con
   `status='completed'`), el contador seguía en 1 — desincronizado.
   `student_service.py` (~L384-405) ya documenta por qué el resto del
   producto (Ruta, analítica docente) dejó de confiar en ese contador
   y deriva en vivo desde `PathModule.status`; este gate era el último
   lugar que aún confiaba en el valor cacheado.

Verificado contra los 64 `learning_paths` reales de producción: bajo
la regla anterior, los 64 estaban bloqueados — nadie podía completar
`completed_modules == total_modules` jamás. Fix aplicado (commit
`c2aae28`, acotado a `knowledge_test_service.py` + su test): el
requisito real es `min(total_modules, POST_TEST_REFERENCE_MODULE_LIMIT)`
módulos, derivados en vivo desde `PathModule`. Cambio puramente
relajante — de los 64 paths reales, los 4 que ya habían completado sus
módulos de referencia quedaron correctamente desbloqueados; los 60
restantes no cambiaron de estado. Backend reiniciado (sin `--reload`,
lección ya conocida de `ADR-0016` Fase 4.4) para servir el fix antes de
reintentar. Este bug es un hallazgo de la validación E2E de esta
iteración, no evidencia de la hipótesis de tesis — registrado aquí por
disciplina de continuidad documental, con su propio commit y tests de
regresión, no como parte del resultado experimental.

## Resultado (Capa 2 — ciclo completo pre→post→ExperimentResult, ejecutada)

Con el gate corregido, recorrido real completado hasta el final:
Misión 1 (3 ciclos, incluidos los pasos de `input()` real — bloqueados
en este entorno de desarrollo por falta de cabeceras COOP/COEP,
`crossOriginIsolated=false` confirmado con JS real; resueltos con el
propio flujo "Ver solución" del producto, diseñado exactamente para
esta situación, no un atajo del tesista) → Misión Final ("Estructuras
de control", 1 ciclo) → Ruta 2/2 misiones (100%) → Post-Test real (12
preguntas, verificado que el intento se creó de verdad en Postgres
antes de responder) → resultado materializado.

**Verificado directo en Postgres** (tabla `experiment_results`, no
inferido de la UI):

```
pre_percentage:     66.67   (pre-test, sesión anterior)
post_percentage:    100.0
absolute_gain:       33.33
normalized_gain:      1.00   (Hake's g — "alta efectividad")
pre_level → post_level:  intermedio → avanzado
group_label:         Experimental
```

Confirmado también que `research_dashboard_service.
get_student_result_rows()` — la función real detrás de
`GET /api/research/export` (CSV/XLSX) — incluye esta fila junto a las
otras 18 del curso: el dato está listo para exportación real, no solo
materializado en la tabla.

## Estado

**CERRADA — Capa 1 y Capa 2 ejecutadas con evidencia real.** La
pregunta de investigación central (¿el instrumento mide la
arquitectura final o un pipeline retirado?) queda respondida: **mide
la arquitectura final**, de punta a punta, incluida la materialización
real de `ExperimentResult` y su disponibilidad para exportación. La
validación E2E encontró además un bug de producto P0 (gate del
Post-Test estructuralmente inalcanzable) que los tests unitarios
existentes no cubrían — corregido con su propio commit y tests de
regresión, documentado arriba como hallazgo de validación, no como
parte del resultado de investigación. Con N=1, esta iteración no
produce significancia estadística — esa es la pregunta de una
iteración posterior (candidata `6.2`: conectar `app/experiment/
analysis.py`, ANOVA/Cohen's d, al dashboard, cuando exista N
suficiente), no de esta.

---

# ITERACIÓN DE INVESTIGACIÓN 6.2 — Robustez del pipeline de medición a escala (N>1) (2026-08-05)

> Continúa la serie 6.x abierta por la Iteración 6.1. No reabre esa
> iteración (CERRADA) — construye sobre su resultado: el instrumento ya
> probó medir la arquitectura final con N=1; esta iteración prueba que
> el pipeline completo (`ExperimentResult` → exportación → análisis
> estadístico) sigue siendo correcto cuando N>1, antes de acercarse a
> la pregunta de significancia real de la hipótesis de tesis.

## Puerta de entrada (Regla maestra)

1. **¿Qué pregunta de investigación responde?** Ver más abajo.
2. **¿Qué parte de la hipótesis fortalece?** La validez del método de
   medición a escala — si el pipeline se rompe o pierde datos con más
   de un estudiante (duplicados, filas perdidas en la exportación,
   `analysis.py` fallando ante N>1), cualquier resultado agregado que
   la tesis reporte más adelante sería inauditable, igual que en 6.1
   con la trazabilidad de una sola cuenta.
3. **¿Qué variable afecta?** Ninguna variable pedagógica nueva —
   valida que el pipeline de medición (no la adaptación en sí) es
   correcto cuando opera sobre varios `ExperimentResult` a la vez.
4. **¿Cómo se observará durante la demo?** Tabla de `ExperimentResult`
   con N≥2 filas reales, exportación CSV/XLSX mostrando esas mismas
   filas 1:1, y una corrida real de `app/experiment/analysis.py`
   contra ese conjunto con salida visible (sin pretender significancia
   con N pequeño).
5. **¿Cómo aparecerá en Resultados y Discusión?** Como la sección que
   responde "el pipeline de análisis estadístico está construido,
   probado y listo para producir resultados en cuanto exista N real
   suficiente" — distinto de reportar los resultados mismos, que
   dependen de tráfico real todavía no disponible (`ADR-0016`
   post-cierre: `v1: 790` vs `v2: 6` sesiones, las 6 generadas por
   validación, no orgánicas).

## Pregunta de investigación

Con N>1 estudiantes reales (no solo la cuenta única de la Iteración
6.1), ¿el pipeline completo — `ExperimentResult` materializado por
cada uno, `research_dashboard_service.get_student_result_rows()`,
exportación CSV/XLSX, y `app/experiment/analysis.py` (ANOVA/Cohen's d,
construido en julio pero nunca ejercitado contra datos reales) — sigue
siendo correcto y consistente, o aparecen errores de escala que un
N=1 no puede revelar (filas duplicadas o perdidas, cálculo estadístico
que falla o produce valores sin sentido, dashboard leyendo datos
intermedios en vez de `ExperimentResult`)?

## Hipótesis parcial

Si se generan N>1 `ExperimentResult` reales (múltiples cuentas, mismo
curso, mismo criterio de evidencia sintética-pero-etiquetada que 6.1 —
ninguna se presenta como tráfico orgánico), entonces (a) cada fila
exportada por CSV/XLSX corresponde 1:1 con su fila en Postgres, sin
pérdida ni duplicación; (b) `app/experiment/analysis.py` puede
ejecutarse sobre ese conjunto y producir una salida numérica válida
(aunque sin poder estadístico interpretable, por N pequeño); y (c) el
dashboard de investigación (`ResearchDashboard.tsx` y las rutas
`/api/research/*`) consume únicamente `ExperimentResult`, nunca
`KnowledgeTestAttempt` u otro dato intermedio directamente.

> **Qué significa "N>1" en esta iteración** (precisión del tesista,
> 2026-08-05): múltiples recorridos experimentales **controlados**
> (cuentas de validación, navegador real, mismo criterio que la cuenta
> única de 6.1), no una muestra estadísticamente representativa del
> curso. El objetivo es validar la robustez del pipeline de medición
> — que no pierda, duplique ni corrompa datos al operar con más de un
> registro — no estimar el efecto pedagógico de la intervención. Esa
> estimación pertenece a `6.3`, con N real de producción.

## Por qué esta pregunta, no otra (decisión ya tomada, no reabrir)

Se descartó abrir esta iteración interpretando ya significancia
estadística de la hipótesis central, por la misma razón que motivó la
verificación de observabilidad post-`ADR-0016`: no existe todavía
tráfico real suficiente (6 sesiones `v2`, todas de validación, no
producción orgánica) — cualquier ANOVA/Cohen's d calculado hoy sería
sobre datos que no representan estudiantes reales. Primero robustez
del pipeline a escala pequeña controlada, después significancia con N
real — no al revés. La pregunta de significancia real queda para una
iteración posterior (candidata `6.3`), condicionada a que exista
tráfico orgánico suficiente.

## Alcance de esta iteración (deliberado)

- **No espera tráfico real de producción.** Genera N>1 cuentas de
  prueba reales (mismo criterio que la cuenta de 6.1: navegador real,
  Postgres real, etiquetadas como validación, nunca presentadas como
  evidencia orgánica) — suficientes para ejercitar el pipeline a
  escala, no para inferencia estadística.
- **No implementa gráficos ni UI nueva.** El dashboard de investigación
  ya existe (`ResearchDashboard.tsx`); esta iteración verifica que
  consume `ExperimentResult` correctamente, no lo rediseña.
- **No modifica `ExperimentResult` ni ningún reducer del kernel** — ni
  el contrato de `app/experiment/analysis.py`, que ya existe.
- **No interpreta significancia estadística** de la hipótesis central
  — solo que el cálculo se ejecuta correctamente sobre datos reales.

## Implementación

Ninguna todavía — como 6.1, esta iteración empieza en validación, no
en construcción. Si la ejecución revela que `app/experiment/
analysis.py` necesita wiring real hacia una ruta HTTP para poder
ejercitarse desde la demo (hoy es un módulo sin endpoint, según
`RESEARCH_LAYER_TECHNICAL_REPORT.md`), ese wiring sería la única pieza
de construcción nueva de esta iteración — acotada, no una capacidad
adicional.

## Evidencia observable

- N≥2 filas de `ExperimentResult` reales en Postgres, cada una
  trazable a un recorrido real (mismo nivel de evidencia que 6.1).
- La exportación CSV/XLSX (`GET /api/research/export`) mostrando esas
  mismas N filas, verificado 1:1 contra Postgres.
- Una salida real (no mockeada) de `app/experiment/analysis.py`
  ejecutada contra ese conjunto.
- Cita del código del dashboard de investigación mostrando que lee
  `ExperimentResult`, no `KnowledgeTestAttempt` ni otro intermedio.

## Variables fortalecidas

- **Independiente:** ninguna nueva — la arquitectura de adaptación
  (`runtime/` LangGraph + `POLITICAS["v2"]`) ya está fijada desde 6.1.
- **Dependiente (validada, no medida todavía):** robustez del pipeline
  de medición y análisis a escala — no la ganancia pedagógica en sí,
  que requiere N real (candidata `6.3`).

## Amenazas a la validez

Lo que esta iteración NO demuestra:

- No demuestra significancia estadística de la hipótesis central — N
  seguirá siendo pequeño y de prueba, no producción real.
- No demuestra que la adaptación multimodal mejora el aprendizaje —
  esa es la pregunta de `6.3`, condicionada a N real.
- No valida el pipeline bajo carga ni concurrencia — solo corrección
  funcional con varios registros secuenciales.

## Evidencia que deberá recolectarse

- □ N≥2 recorridos reales completos (pre→ruta→post→`ExperimentResult`).
- □ Cada `ExperimentResult` corresponde exactamente a un estudiante
  (`student_id` único por fila, sin ambigüedad de curso/sesión).
- □ No existen filas duplicadas (mismo `student_id`+`course_id` con
  más de un `ExperimentResult` vigente).
- □ No existen filas huérfanas (`pre_attempt_id`/`post_attempt_id` sin
  su `KnowledgeTestAttempt` correspondiente en Postgres).
- □ La exportación CSV/XLSX conserva el mismo orden y contenido que
  Postgres (diff fila por fila, no solo conteo de filas).
- □ `app/experiment/analysis.py` produce su resultado usando
  exactamente esas filas — log real de la ejecución, con su salida
  completa.
- □ Cita exacta (archivo + línea) del dashboard confirmando que solo
  consume `ExperimentResult`.

## Resultado

Ejecutada con N=3 recorridos reales completos (excede el N=2
planeado — el tercer registro ya existía en Postgres de una sesión
previa, `dad74e9a...`, y se incluyó en la verificación por ser real y
del mismo curso). Cuenta nueva creada para esta iteración
(`iteracion.6.2@upao.test`, distinta de `iteracion.6.1@upao.test`,
mismo criterio de evidencia real — navegador real, Postgres real,
etiquetada como validación) y llevada de punta a punta:
diagnóstico → pre-test (100%, techo — dato real, no forzado) → Misión
1 + Misión Final (ambas completadas, incluidos los pasos de `input()`
real, que en esta sesión sí funcionaron de extremo a extremo —
a diferencia de la Iteración 6.1, donde el mismo paso estuvo
bloqueado por falta de cabeceras COOP/COEP; la causa exacta de la
diferencia entre sesiones no se investigó, por estar fuera del
alcance de esta iteración) → Ruta 2/2 (100%) → Post-Test real (100%).

**Verificación fila por fila, directa en Postgres** (`experiment_results`,
tabla completa del curso, N=3):

```
student            pre%     post%    abs_gain   norm_gain   pre_level    post_level
dad74e9a...        0.00     33.33    33.33      0.3333      basico       basico
0cbdbe25... (6.1)  66.67    100.0    33.33      1.0000      intermedio   avanzado
8bc6e940... (6.2)  100.0    100.0    0.00       None        avanzado    avanzado
```

- **Un `ExperimentResult` por estudiante**: confirmado, 3 `student_id`
  distintos, sin ambigüedad de curso/sesión.
- **Sin duplicados**: consulta `GROUP BY student_id, course_id HAVING
  COUNT(*) > 1` sobre las 3 filas → vacío.
- **Sin filas huérfanas**: los 3 `pre_attempt_id`/`post_attempt_id`
  existen realmente en `knowledge_test_attempts` — verificado con
  `NOT EXISTS`, vacío.
- **Exportación = Postgres**: `research_dashboard_service.
  get_student_result_rows()` (la función real detrás de `GET
  /api/research/export`) devuelve 20 filas para el curso (todas las
  cuentas con pre-test completado, no solo las de esta validación);
  las 3 filas de esta iteración calzan 1:1 contra Postgres
  (`pre_pct`/`post_pct`/`absolute_gain`) — verificado
  programáticamente, sin discrepancias.
- **`app/experiment/analysis.py` ejecutado contra datos reales**
  (nunca antes ejercitado contra `ExperimentResult` real, según
  `RESEARCH_LAYER_TECHNICAL_REPORT.md`): `compute_anova({"pre": [...],
  "post": [...]})` → `F(1,4)=0.3635, p=0.816, ns` — correctamente NO
  significativo, como corresponde a N=3 de validación, no de
  producción. `cohens_d(pre, post) = -0.492`. `generate_statistical_
  report()` produjo un reporte completo (descriptivos, ANOVA,
  comparaciones pareadas, matriz de significancia) sin errores. El
  caso `8bc6e940` (`pre=100%`) probó además que el pipeline maneja el
  efecto techo sin romperse: `normalized_gain=None` en vez de una
  división por cero.

**Hallazgo real, más preciso que la formulación original de la
pregunta** — el dashboard/exportación **no** lee "únicamente
`ExperimentResult`": `research_dashboard_service.
get_student_result_rows()` (`backend/app/services/
research_dashboard_service.py:163-260`) toma `pre_pct`/`post_pct`
en vivo desde `KnowledgeTestAttempt.percentage` (la fuente real,
evita el mismo tipo de dato-cacheado-obsoleto que causó el bug de
[[bug_post_test_gate_ped004_stale_counter]] en 6.1) y solo
`absolute_gain`/`normalized_gain` — el cómputo agregado que requiere
ambos extremos y un instante de materialización — viene de
`ExperimentResult`. Esto es arquitectónicamente correcto (Regla de
derivación del propio `CLAUDE.md`: derivar de la fuente, no copiar
salvo razón explícita), no un defecto — pero contradice la redacción
literal de "consume únicamente ExperimentResult" de la Puerta de
entrada. Se registra como precisión del hallazgo, no como bug.

## Estado

**CERRADA.** Las cinco verificaciones de la Evidencia que deberá
recolectarse quedaron satisfechas con evidencia real (N=3, excede el
N=2 planeado): integridad (sin huérfanas), unicidad (sin duplicados),
correspondencia exportación↔Postgres, `analysis.py` ejecutado sin
fallos sobre datos reales (incluido un caso de efecto techo real que
no rompió el pipeline), y el origen exacto de cada campo del dataset
exportable quedó documentado con precisión (línea por línea, no solo
"ExperimentResult"). El pipeline de medición está construido, probado
contra N>1 real, y listo para producir resultados en cuanto exista
tráfico orgánico suficiente. La pregunta de significancia real de la
hipótesis de tesis queda para la candidata `6.3`, todavía sin abrir.

---

# ITERACIÓN DE INVESTIGACIÓN 6.4 — Pre-registro: pesos de refuerzo/refutación/decaimiento en la confianza efectiva (C6, previo a calibración empírica)

## Pregunta de investigación

¿Los pesos de refuerzo/refutación/decaimiento en cero de la política
`"v2"` vigente (`runtime/kernel/deliberation/politica.py`) suprimen por
completo cualquier efecto de evidencia colectiva acumulada y de
vigencia temporal sobre la confianza efectiva (`ce`), y si se activan
pesos no-cero calibrados, cambian de forma medible las decisiones
D1/D3 del kernel de deliberación respecto a las mismas sesiones bajo
`"v2"`?

**Origen:** hallazgo C1 de la Auditoría Externa 2026-08-06 — el auditor
señaló `peso_refuerzo = peso_decaimiento = 0` en producción como una
posible debilidad de la narrativa de "inteligencia de enjambre" de la
tesis. El tesista eligió "investigar antes de decidir" en vez de
activar pesos no-cero directamente o descartar el hallazgo.

## Hipótesis parcial

**H0 (nula):** activar `peso_refuerzo`/`peso_refutacion`/`peso_decaimiento`
no-cero no produce ningún cambio medible en las decisiones D1/D3
respecto a `"v2"` sobre el mismo conjunto de sesiones — el efecto es
indistinguible de ruido, o las magnitudes elegidas caen fuera del rango
real de `refuerzos`/`refutaciones`/`edad_logica` que ocurre en
producción.

**H1 (alternativa):** al menos uno de los candidatos `v3` produce una
divergencia medible y atribuible entre `ce` y `confianza_declarada`
(matemáticamente imposible bajo `"v2"` por A2 + pesos=0 —
`calcular_confianza_efectiva` se reduce exactamente a la identidad), y
esa divergencia cambia el resultado de al menos una decisión D1/D3 en
el conjunto de sesiones comparado.

## Candidatos de política (configuraciones experimentales — ninguna es la `"v3"` de producción todavía)

| Candidato | `peso_refuerzo` | `peso_refutacion` | `peso_decaimiento` | Aísla |
|---|---|---|---|---|
| **v3a** | 0.10 | 0.10 | 0.0 | eje de evidencia (positiva/negativa) |
| **v3b** | 0.0 | 0.0 | 0.02 | eje temporal (vigencia/olvido) |
| **v3c** | 0.10 | 0.10 | 0.02 | combinado — ancla ya validada en código |

Ninguno inventado desde cero: `0.10`/`0.10`/`0.02` es precedente de
código ya revisado y comprometido
(`tests/runtime/deliberation/test_A1_A7_confianza_efectiva.py`), ya
ejercido contra `range(20)` refuerzos sin desbordar el clamp de A1.
v3a/v3b descomponen ese mismo ancla en sus dos ejes por separado —
mismo criterio de una-sola-variable que ya usó `"v1"→"v2"` (Escenario
A: solo `delta`/`theta`, `peso_refuerzo/refutacion/decaimiento` sin
tocar).

**Razonamiento mecánico de por qué `peso_decaimiento` usa un orden de
magnitud menos** (`confianza.py:64-146`): `refuerzos`/`refutaciones` son
conteos enteros pequeños y acotados por cuántas veces `Validar` referencia
decisiones de este claim (típicamente unas pocas por sesión);
`edad_logica` es un conteo entero de transiciones desde la última
validación en la cadena causal del claim, sin cota superior dentro de
una sesión. Un `peso_decaimiento` de la misma magnitud que
`peso_refuerzo` haría que el término de decaimiento domine casi
cualquier claim poco visitado. No hay riesgo de conflicto de signo
entre refuerzo y decaimiento en el mismo tick, sea cual sea la
magnitud: `politica.py` documenta que la edad lógica se ancla a la
última validación dentro de la cadena causal (A7), así que un refuerzo
recién aplicado tiene edad lógica exactamente 0 en el instante en que
se cuenta.

## Variables que se congelan en este pre-registro (antes de calibrar con datos reales)

- Los tres candidatos v3a/v3b/v3c quedan fijos como configuraciones a
  probar — no se ajustan "a ojo" después de ver los primeros
  resultados (mismo criterio de pre-registro que 5.2/5.8).
- Ningún candidato se activa como `POLITICAS["v3"]` de producción en
  esta iteración — eso, si corresponde, es una decisión posterior con
  su propio ADR (mismo patrón que ADR-0015/0016 con `"v2"`).
- Ningún cambio a `confianza.py`, `mecanica.py`, ni a ningún reducer —
  una política nueva es únicamente una entrada más en `POLITICAS`,
  mismo patrón que `"v1"→"v2"`.

## Lo que este pre-registro NO modifica

`kernel/`, `deliberation/mecanica.py`, `confianza.py`, RFC-0006, ningún
reducer, ninguna política de producción existente (`"v1"`/`"v2"`
intactas).

## Diseño experimental (para cuando se ejecute)

**Primer paso de ejecución (fuera del alcance de este pre-registro):**
levantar Postgres real y, vía
`runtime/engine/checkpoint/reconstruccion.py::reconstruir_con_traza`
(ya usado por `app/replay/session_replay.py`, RFC-0008), reconstruir un
conjunto fijo de sesiones reales y observar la distribución real de
`refuerzos`/`refutaciones`/`edad_logica` bajo `"v2"` — estos conteos ya
se calculan hoy en cada llamada a `calcular_confianza_efectiva`, solo
su contribución a `ce` está multiplicada por 0, así que no hace falta
ningún cambio de política para observarlos. Esto valida o corrige las
magnitudes de v3a/v3b/v3c **antes** de ejecutar la comparación, nunca
después de ver el resultado.

**Segundo paso:** sobre el mismo conjunto de sesiones, recalcular `ce`
bajo cada candidato y comparar contra `"v2"`: (a) divergencia `ce` vs
`confianza_declarada`, (b) cambios en el resultado de decisiones
D1/D3, (c) aplazamientos/escaladas nuevos que `"v2"` no puede producir
por construcción matemática.

**Orden de ejecución recomendado:** v3a y v3b primero, aislados, un eje
cada uno. v3c solo si alguno de los dos muestra efecto individual que
valga la pena combinar — no como candidato de igual peso desde el
arranque (mismo criterio que llevó a fusionar ADR-0017 Fases 4+5 solo
tras evidencia, nunca por conveniencia).

## Amenazas a la validez

- Sesiones reales disponibles pueden ser pocas o no representativas del
  rango completo de `edad_logica` — mitigado parcialmente por poder
  complementar con escenarios sintéticos, mismo recurso que 5.1/5.2.
- Elegir los pesos manualmente introduce riesgo de ajuste arbitrario de
  hiperparámetros — mitigado por anclar a precedente de código ya
  revisado en vez de valores inventados, y por descomponer en ejes
  aislados antes de combinar.
- v3c mezcla dos mecanismos (evidencia + tiempo) — dificulta atribuir
  causalidad si se ejecuta antes que v3a/v3b por separado; el orden de
  ejecución recomendado lo pospone por este motivo exacto.

## Criterios de aceptación (de este pre-registro, no de una política v3 final)

- La calibración empírica (Postgres real) confirma o corrige los rangos
  plausibles de `refuerzos`/`refutaciones`/`edad_logica` antes de correr
  la comparación — si los datos reales sugieren que 0.10/0.02 saturan o
  son indetectables, se documenta y se ajustan los candidatos ANTES de
  comparar contra `"v2"`, nunca después de ver el resultado.
- v3a y v3b se comparan contra `"v2"` por separado, sobre el mismo
  conjunto de sesiones, antes de correr v3c.
- Ningún cambio de código fuera de una nueva entrada en `POLITICAS`
  (ningún reducer, `kernel/`, ni RFC-0006 tocados).
- El resultado (H0 confirmada o refutada) se reporta tal como sale, sin
  ajustar los pesos después de ver el dato — mismo criterio de
  pre-registro que 5.2/5.8.

## Alcance explícitamente fuera de esta iteración

- Activar cualquier candidato como política de producción
  (`POLITICAS["v3"]` real) — decisión posterior, con su propio ADR si
  corresponde.
- Elegir pesos distintos a los tres candidatos ya congelados aquí.
- DOC-001/DOC-002 (Experimentos B/C, `agent_health_monitoring.md`) —
  fuera de alcance, tareas independientes sin relación con C6.
- Levantar Postgres real y ejecutar la calibración — ese es el primer
  paso de EJECUCIÓN, no de este pre-registro de diseño.

## Calibración empírica (primer paso de ejecución, separado del experimento)

Ejecutada tras aprobación explícita del tesista. Script `backend/
scripts/calibracion_pesos_confianza.py` — 100% lectura (`AlmacenTransiciones
.identidad_existente()`/`.leer()`, ambos `SELECT`), reconstruye cada
sesión real vía `reconstruir()` (mismo camino que usa el Boundary en
`traza_sesion.py` para S3) y observa los conteos que `calcular_confianza
_efectiva` ya calcula hoy — su contribución a `ce` está multiplicada por
0 bajo `"v1"`/`"v2"`, pero los conteos mismos no dependen de la política.

**Resultado — 902/966 sesiones reales reconstruidas (64 vacías, 0
errores), 6638 claims vigentes evaluados, políticas vistas `v1`=740/
`v2`=162:**

| Variable | min | max | media | mediana | P90 | P95 |
|---|---|---|---|---|---|---|
| `refuerzos` | 0 | 0 | 0 | 0 | 0 | 0 |
| `refutaciones` | 0 | 0 | 0 | 0 | 0 | 0 |
| `edad_logica` | 0 | 0 | 0 | 0 | 0 | 0 |

Decisiones: 610 directas (sin tensión), 514 resueltas por deliberación.

**Hallazgo crítico, verificado por dos vías independientes antes de
reportarlo (no es un artefacto del script de calibración):**

1. Cero ocurrencias de "validar" en los 19,412 `payload` de
   `runtime_transitions` — `Capacidad.VALIDAR` nunca produjo un claim en
   ninguna de las 902 sesiones reales de esta base.
2. `Validar` **sí está viva y enrutada** (`walkthrough.py:416`, nodo
   real del grafo, no código muerto). Su guardia de disparo
   (`_decision_lista_para_validar`, línea 135) exige que una decisión ya
   aplicada tenga evidencia posterior de Evaluar antes de rutear a
   "validar" — un ciclo completo *decidir→adaptar→evaluar→validar*. Las
   902 sesiones reales disponibles, aparentemente, nunca lo completan.

**Consecuencia directa:** con `refuerzos=refutaciones=edad_logica=0` en
el 100% de los datos disponibles, v3a/v3b/v3c producirían resultados
matemáticamente idénticos a `"v2"` si se compararan contra estas
sesiones reales ahora mismo — no por pesos mal calibrados, sino porque
el mecanismo que esos pesos multiplican nunca se activa en este
dataset. Exactamente el escenario que este paso de calibración estaba
diseñado para atrapar antes de comparar, no después.

## Experimento C6 — validación MECÁNICA/EXPERIMENTAL con escenarios sintéticos

**Etiqueta metodológica explícita, a pedido del tesista: esto es
validación mecánica, NO evidencia de comportamiento real de
estudiantes.** Responde la pregunta causal "cuando SÍ existe evidencia
colectiva acumulada y/o envejecimiento temporal de claims, ¿los pesos
no-cero modifican `ce` y las decisiones derivadas respecto a `"v2"`?" —
no mide impacto poblacional real. La validación ecológica con datos
reales queda pendiente de tráfico orgánico suficiente (mismo criterio
que Iteración 6.2/6.3).

Script `backend/scripts/experimentos/c6_pesos_confianza_sinteticos.py`
— mismo patrón que `test_A1_A7_confianza_efectiva.py` (`LearningState`
a mano, reducers puros, sin Postgres) y que `consenso_barrido_delta.py`
(ramas in-memory nunca persistidas, `POLITICAS` no se toca). Pesos de
v3a/v3b/v3c exactamente los congelados arriba — sin ajustar.

**Hallazgo arquitectónico encontrado al construir el escenario de
tensión, no previsto en el diseño original:** un primer intento usó dos
claims `INTERPRETACION` rivales (D1) y falló — `registrar_decision`
rechaza por INV-6 ("las decisiones derivan de propuestas") cualquier
origen que no sea `TipoClaim.PROPUESTA`, y `derivar_decision`
(`mecanica.py`) lo confirma en su propio docstring: *"Una resolución D1
(interpretaciones en tensión) refina el paisaje, JAMÁS deriva
decisión"*. **Consecuencia estructural, no una limitación del script:
ningún claim `INTERPRETACION` puede tener nunca refuerzos, refutaciones
ni decaimiento — su `ce` es, por construcción del sistema, siempre
exactamente su confianza declarada, sea cual sea la política.**
`peso_refuerzo`/`refutacion`/`decaimiento` solo pueden alcanzar claims
`PROPUESTA` (D2/D3) — nunca D1. El escenario de tensión se rehízo con
dos `PROPUESTA` rivales.

**Resultado — divergencia `ce` vs `confianza_declarada` (4 escenarios de un solo eje):**

| Escenario | v2 | v3a (solo evidencia) | v3b (solo tiempo) | v3c (combinado) |
|---|---|---|---|---|
| refuerzo×3 | 0.70 (Δ0) | 1.00 (Δ+0.30) | 0.70 (Δ0) | 1.00 (Δ+0.30) |
| refutación×3 | 0.70 (Δ0) | 0.40 (Δ−0.30) | 0.70 (Δ0) | 0.40 (Δ−0.30) |
| decaimiento (1 refuerzo-ancla + 50 transiciones ajenas) | 0.70 (Δ0) | 0.80 (Δ+0.10) | 0.00 (Δ−0.70, saturado por A1) | 0.00 (Δ−0.70, saturado) |
| combinado (2 refuerzos + 30 transiciones ajenas) | 0.70 (Δ0) | 0.90 (Δ+0.20) | 0.10 (Δ−0.60) | 0.30 (Δ−0.40) |

El escenario de decaimiento satura `ce` a 0 (clamp de A1) bajo v3b/v3c
— confirma en código real la "amenaza a la validez" ya anticipada en el
pre-registro (`peso_decaimiento` sin cota superior de `edad_logica`
puede colapsar un claim genuinamente bien fundado).

**Resultado — escenario de tensión D2 (dos `PROPUESTA` rivales, A con
confianza declarada menor pero 3 refuerzos, B con confianza mayor y sin
refuerzos):**

| Política | ce(A) | ce(B) | Ganador |
|---|---|---|---|
| v2 | 0.55 | 0.65 | **B** |
| v3a (solo evidencia) | 0.85 | 0.65 | **A** |
| v3b (solo tiempo) | 0.55 | 0.65 | **B** |
| v3c (combinado) | 0.85 | 0.65 | **A** |

**El ganador de la tensión cambia (B→A) bajo v3a/v3c** — evidencia
mecánica directa de que activar `peso_refuerzo` no solo mueve `ce` en
el margen: puede voltear una decisión D2 real cuando hay evidencia
colectiva acumulada suficiente. v3b (solo decaimiento, sin refuerzo) no
cambia el ganador en este escenario porque la tensión se evalúa antes
de que transcurra tiempo sin validar — consistente con la mecánica
(edad lógica congelada en 0 hasta la primera validación).

**H1 confirmada, H0 rechazada** (pre-registro): al menos un candidato
(de hecho v3a y v3c) produce divergencia `ce` medible y atribuible, y
esa divergencia cambia el resultado de al menos una decisión (la
tensión D2 sintética). Resultado completo en JSON:
`backend/experiments/results/c6_pesos_confianza_sinteticos_20260807T024511.json`.

## Estado

**CALIBRACIÓN Y EXPERIMENTO MECÁNICO EJECUTADOS. Ninguna decisión de
adopción tomada — deliberadamente separada, como pidió el tesista.**
Tres decisiones independientes, en tres momentos distintos:

1. **Calibración** (¿son plausibles los pesos?) — ejecutada. Datos
   reales actuales no ejercitan el mecanismo (refuerzos/refutaciones/
   edad_logica ≡ 0) — limitación de datos, no de los candidatos.
2. **Experimento C6** (¿los pesos modifican algo, mecánicamente?) —
   ejecutado sobre escenarios sintéticos. Sí: divergencia `ce` medible
   en los 4 escenarios de un solo eje, y un cambio real de ganador en
   la tensión D2 sintética. Hallazgo adicional: `peso_refuerzo/
   refutacion/decaimiento` son estructuralmente inertes para claims D1
   (`INTERPRETACION`) — solo alcanzan D2/D3 (`PROPUESTA`).
3. **ADR de adopción** (¿algún candidato reemplaza `"v2"` en
   producción?) — **NO iniciado, fuera de esta iteración.** Ningún
   candidato se registró en `POLITICAS`, ningún código de producción
   cambió. Si corresponde, es una decisión posterior con su propio ADR
   (mismo patrón que ADR-0015/0016), condicionada además a la
   validación ecológica pendiente (tráfico orgánico real que sí
   ejercite Validar).

Sin código de producción tocado (aparte de la corrección independiente
de `politica.py`, commit `5faf2c7`, no parte de esta iteración).

## Cierre — decisión explícita del tesista, no inferida

**`"v2"` se mantiene como política de producción. C6 se cierra como
evidencia experimental — no se abre ADR de adopción.** El resultado
positivo del experimento mecánico (H1 confirmada) no se convierte
automáticamente en una migración de producción: son dos fases
distintas y mezclarlas perdería trazabilidad, igual criterio que ya
protegió la separación Fase 4/5 de ADR-0017.

**Conclusión citable para la tesis** (redactada explícitamente para el
capítulo de Resultados/Discusión):

> La política v3 demuestra capacidad mecánica superior bajo escenarios
> donde existe evidencia colectiva acumulada; sin embargo, la política
> v2 permanece como baseline productivo debido a que el dataset real
> disponible aún no ejercita el ciclo completo requerido para validar
> el impacto ecológico.

**Lo que C6 sí demostró** (fortalece la narrativa de arquitectura
multiagente): `"v2"` en producción equivale, en la práctica, a usar
únicamente `confianza_declarada` — v3a/v3c introducen comportamiento
emergente medible en cuanto existen señales colectivas, sin tocar
reducers ni kernel (la arquitectura ya soportaba esta extensión, RFC-
0006 §1 la declaró versionable desde el diseño original). Hay evidencia
causal directa de que los pesos tienen efecto, incluyendo un cambio de
decisión D2 real.

**Lo que falta para activar v3 — condiciones explícitas, no un "tal vez
después" vago:**
1. Que las señales (refuerzos/refutaciones/edad_logica > 0) aparezcan
   en uso real — depende de tráfico orgánico que complete
   decidir→adaptar→evaluar→validar (mismo bloqueo que Iteración 6.2/6.3).
2. Evidencia de que no degradan decisiones, no generan sobreconfianza,
   ni producen aplazamientos/escaladas excesivos (el riesgo de
   saturación de `peso_decaimiento` ya observado en el escenario
   sintético debe volver a medirse contra datos reales antes de
   confiar en cualquier magnitud).
3. Mejora medible en métricas pedagógicas reales, no solo en `ce`.
4. Un ADR de adopción independiente, con sus propios criterios de
   aceptación y validación de regresión — mismo patrón que
   ADR-0015/0016 con `"v2"` misma.

**Para la discusión de tesis, específicamente:** el hallazgo de que
`peso_refuerzo/refutacion/decaimiento` son estructuralmente inertes
para D1 (`INTERPRETACION`, INV-6) y solo alcanzan D2/D3 (`PROPUESTA`)
delimita con precisión matemática **dónde** existe "inteligencia de
enjambre" en la arquitectura actual — en la capa prescriptiva, no en la
interpretativa. Esa delimitación es en sí misma un resultado de la
investigación, no un efecto secundario a omitir.
