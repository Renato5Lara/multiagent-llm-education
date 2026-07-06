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
